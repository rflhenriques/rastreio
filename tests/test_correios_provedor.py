from datetime import datetime, timezone

import pytest

from app.extensions import db
from app.models import Status
from app.provedores import ErroProvedor, obter_provedor
from app.provedores.correios import (
    ProvedorCorreios,
    classificar,
    nome_proprio,
    traduzir_resposta,
)
from app.servicos.atualizador import atualizar_pedido


def bruto(codigo, descricao, quando, cidade="JUIZ DE FORA", uf="MG", **extras):
    evento = {
        "codigo": codigo,
        "tipo": "01",
        "dtHrCriado": quando,
        "descricao": descricao,
        "unidade": {
            "tipo": "Agência dos Correios",
            "endereco": {"cidade": cidade, "uf": uf},
        },
    }
    evento.update(extras)
    return evento


def resposta(*eventos):
    return {
        "versao": "3.8.3",
        "quantidade": 1,
        "objetos": [{"codObjeto": "XX000000000BR", "eventos": list(eventos)}],
    }


class ClienteFalso:
    def __init__(self, dados):
        self.dados = dados
        self.consultas = []

    def consultar_objeto(self, codigo):
        self.consultas.append(codigo)
        return self.dados


# Do mais novo para o mais antigo, como a API devolve (estrutura de um envio real)
HISTORICO_COM_TENTATIVAS = [
    bruto("LDI", "Objeto aguardando retirada no endereço indicado", "2026-10-26T13:45:34"),
    bruto("BDE", "Saída para entrega cancelada", "2026-10-24T10:13:44"),
    bruto("OEC", "Objeto saiu para entrega ao destinatário", "2026-10-24T07:24:24"),
    bruto("BDE", "Objeto não entregue - carteiro não atendido", "2026-10-23T11:20:37"),
    bruto("OEC", "Objeto saiu para entrega ao destinatário", "2026-10-23T09:34:36"),
    bruto("DO", "Objeto em transferência - por favor aguarde", "2026-10-19T07:21:26"),
    bruto("RO", "Objeto em transferência - por favor aguarde", "2026-10-14T17:25:23"),
    bruto("PO", "Objeto postado", "2026-10-14T11:14:06"),
]

HISTORICO_ENTREGUE = [
    bruto("BDE", "Objeto entregue ao destinatário", "2026-10-27T16:48:33"),
    bruto("OEC", "Objeto saiu para entrega ao destinatário", "2026-10-27T14:22:40"),
    bruto("FC", "Objeto recebido na unidade de distribuição", "2026-10-27T14:06:52"),
    bruto("DO", "Objeto em transferência - por favor aguarde", "2026-10-27T05:32:56"),
]


# ---------- classificar ----------


@pytest.mark.parametrize(
    "codigo, descricao, esperado",
    [
        ("PO", "Objeto postado", Status.POSTADO),
        ("PO", "Objeto postado após o horário limite da unidade", Status.POSTADO),
        ("RO", "Objeto em transferência - por favor aguarde", Status.EM_TRANSITO),
        ("DO", "Objeto em transferência - por favor aguarde", Status.EM_TRANSITO),
        ("FC", "Objeto recebido na unidade de distribuição", Status.EM_TRANSITO),
        ("OEC", "Objeto saiu para entrega ao destinatário", Status.SAIU_ENTREGA),
        ("BDE", "Objeto entregue ao destinatário", Status.ENTREGUE),
        ("BDE", "Objeto não entregue - carteiro não atendido", Status.EM_TRANSITO),
        ("BDE", "Saída para entrega cancelada", Status.EM_TRANSITO),
        ("BDE", "Objeto entregue ao remetente", Status.EM_TRANSITO),
        ("LDI", "Objeto aguardando retirada no endereço indicado", Status.EM_TRANSITO),
        ("XYZ", "Algo que ainda não conhecemos", Status.EM_TRANSITO),
    ],
)
def test_classificar(codigo, descricao, esperado):
    assert classificar(codigo, descricao) == esperado


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("JUIZ DE FORA", "Juiz de Fora"),
        ("PALMEIRA DOS INDIOS", "Palmeira dos Indios"),
        ("RECIFE", "Recife"),
    ],
)
def test_nome_proprio(texto, esperado):
    assert nome_proprio(texto) == esperado


# ---------- traduzir_resposta ----------


def test_horario_dos_correios_e_lido_como_brasilia_e_guardado_em_utc():
    dados = resposta(bruto("PO", "Objeto postado", "2026-10-14T11:14:06"))

    evento = traduzir_resposta(dados)[0]

    assert evento.ocorrido_em == datetime(2026, 10, 14, 14, 14, 6, tzinfo=timezone.utc)


def test_local_mostra_tipo_cidade_e_uf():
    dados = resposta(bruto("PO", "Objeto postado", "2026-10-14T11:14:06"))

    assert traduzir_resposta(dados)[0].local == "Agência dos Correios - Juiz de Fora/MG"


def test_local_de_transferencia_mostra_origem_e_destino():
    destino = {
        "tipo": "Unidade de Tratamento",
        "endereco": {"cidade": "BELO HORIZONTE", "uf": "MG"},
    }
    dados = resposta(
        bruto("RO", "Objeto em transferência", "2026-10-14T17:25:23", unidadeDestino=destino)
    )

    assert traduzir_resposta(dados)[0].local == (
        "Agência dos Correios - Juiz de Fora/MG → Unidade de Tratamento - Belo Horizonte/MG"
    )


@pytest.mark.parametrize(
    "dados", [{}, {"objetos": []}, resposta(), None, "texto estranho"]
)
def test_resposta_sem_eventos_devolve_lista_vazia(dados):
    assert traduzir_resposta(dados) == []


def test_mensagem_dos_correios_sem_eventos_vira_erro():
    dados = {"objetos": [{"codObjeto": "X", "mensagem": "SRO-020: Objeto não encontrado"}]}

    with pytest.raises(ErroProvedor, match="Objeto não encontrado"):
        traduzir_resposta(dados)


def test_evento_com_data_invalida_e_ignorado():
    dados = resposta(
        bruto("RO", "Objeto em transferência", "data-quebrada"),
        bruto("PO", "Objeto postado", "2026-10-14T11:14:06"),
    )

    eventos = traduzir_resposta(dados)

    assert [e.descricao for e in eventos] == ["Objeto postado"]


# ---------- provedor completo, com o atualizador ----------


def test_pacote_com_tentativas_falhas_nao_vira_entregue(fabrica_pedido):
    pedido = fabrica_pedido(codigo="XX000000000BR")
    cliente = ClienteFalso(resposta(*HISTORICO_COM_TENTATIVAS))
    provedor = ProvedorCorreios(cliente=cliente)

    assert atualizar_pedido(pedido, provedor) == 8
    db.session.commit()

    assert pedido.status == Status.SAIU_ENTREGA
    assert atualizar_pedido(pedido, provedor) == 0
    assert cliente.consultas == ["XX000000000BR", "XX000000000BR"]


def test_pacote_entregue_vira_entregue(fabrica_pedido):
    pedido = fabrica_pedido(codigo="XX000000000BR")
    provedor = ProvedorCorreios(cliente=ClienteFalso(resposta(*HISTORICO_ENTREGUE)))

    atualizar_pedido(pedido, provedor)

    assert pedido.status == Status.ENTREGUE


def test_correios_e_um_provedor_registrado():
    assert isinstance(obter_provedor("correios"), ProvedorCorreios)


def test_sem_credenciais_o_erro_aparece_na_consulta(app):
    provedor = ProvedorCorreios()  # criar o provedor não deve falhar

    with pytest.raises(ErroProvedor, match="Faltam no .env"):
        provedor.buscar_eventos("XX000000000BR", None)