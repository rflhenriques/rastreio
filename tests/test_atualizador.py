from datetime import date
from app.extensions import db
from app.models import Origem, Status
from app.provedores import ErroProvedor
from app.provedores.base import EventoRastreio, Rastreio
from app.servicos.atualizador import atualizar_pedido, atualizar_todos
from falsos import BASE, ProvedorFalso, evento

CODIGO = "AA000000001BR"
OUTRO = "BB000000002BR"


def eventos_dos_correios(pedido):
    return [e for e in pedido.eventos if e.origem == Origem.CORREIOS]


def test_grava_os_eventos_e_avanca_o_status(fabrica_pedido):
    pedido = fabrica_pedido(codigo=CODIGO)
    provedor = ProvedorFalso(
        {CODIGO: [evento(0, Status.POSTADO), evento(30, Status.EM_TRANSITO)]}
    )

    novos = atualizar_pedido(pedido, provedor)
    db.session.commit()

    assert novos == 2
    assert len(eventos_dos_correios(pedido)) == 2
    assert pedido.status == Status.EM_TRANSITO


def test_rodar_duas_vezes_nao_duplica_eventos(fabrica_pedido):
    pedido = fabrica_pedido(codigo=CODIGO)
    provedor = ProvedorFalso({CODIGO: [evento(0, Status.POSTADO)]})

    assert atualizar_pedido(pedido, provedor) == 1
    db.session.commit()

    assert atualizar_pedido(pedido, provedor) == 0
    assert len(eventos_dos_correios(pedido)) == 1


def test_so_grava_os_eventos_novos(fabrica_pedido):
    pedido = fabrica_pedido(codigo=CODIGO)
    provedor = ProvedorFalso({CODIGO: [evento(0, Status.POSTADO)]})
    atualizar_pedido(pedido, provedor)
    db.session.commit()

    provedor.respostas[CODIGO] = [
        evento(0, Status.POSTADO),
        evento(60, Status.EM_TRANSITO),
    ]
    novos = atualizar_pedido(pedido, provedor)
    db.session.commit()

    assert novos == 1
    assert len(eventos_dos_correios(pedido)) == 2
    assert pedido.status == Status.EM_TRANSITO


def test_status_nunca_retrocede(fabrica_pedido):
    pedido = fabrica_pedido(codigo=CODIGO, status=Status.SAIU_ENTREGA)
    provedor = ProvedorFalso({CODIGO: [evento(0, Status.POSTADO)]})

    atualizar_pedido(pedido, provedor)

    assert pedido.status == Status.SAIU_ENTREGA


def test_status_vem_da_etapa_mais_avancada_mesmo_fora_de_ordem(fabrica_pedido):
    pedido = fabrica_pedido(codigo=CODIGO)
    provedor = ProvedorFalso(
        {CODIGO: [evento(60, Status.EM_TRANSITO), evento(0, Status.POSTADO)]}
    )

    atualizar_pedido(pedido, provedor)

    assert pedido.status == Status.EM_TRANSITO



def test_atualizar_todos_ignora_pedidos_sem_codigo_e_entregues(fabrica_pedido):
    fabrica_pedido(nome="Sem código")
    fabrica_pedido(nome="Entregue", codigo=OUTRO, status=Status.ENTREGUE)
    fabrica_pedido(nome="Ativo", codigo=CODIGO)
    provedor = ProvedorFalso({CODIGO: [evento(0, Status.POSTADO)]})

    resumo = atualizar_todos(provedor)

    assert resumo.pedidos == 1
    assert resumo.eventos_novos == 1
    assert [codigo for codigo, _ in provedor.chamadas] == [CODIGO]


def test_falha_em_um_pedido_nao_impede_os_outros(fabrica_pedido):
    fabrica_pedido(nome="Com falha", codigo=OUTRO)
    bom = fabrica_pedido(nome="Bom", codigo=CODIGO)
    provedor = ProvedorFalso(
        {
            OUTRO: ErroProvedor("API fora do ar"),
            CODIGO: [evento(0, Status.POSTADO)],
        }
    )

    resumo = atualizar_todos(provedor)

    assert resumo.pedidos == 2
    assert resumo.erros == 1
    assert resumo.eventos_novos == 1
    assert bom.status == Status.POSTADO


def test_provedor_recebe_o_momento_do_ultimo_evento_interno(fabrica_pedido):
    pedido = fabrica_pedido(codigo=CODIGO)
    provedor = ProvedorFalso({CODIGO: []})

    atualizar_pedido(pedido, provedor)

    _, referencia = provedor.chamadas[0]
    ultimo_interno = max(
        e.ocorrido_em for e in pedido.eventos if e.origem == Origem.INTERNA
    )
    assert referencia.tzinfo is not None
    assert referencia.replace(tzinfo=None) == ultimo_interno.replace(tzinfo=None)

def test_etapa_mais_avancada_vale_mesmo_se_o_ultimo_evento_for_anterior(fabrica_pedido):
    pedido = fabrica_pedido(codigo=CODIGO)
    provedor = ProvedorFalso(
        {
            CODIGO: [
                evento(0, Status.POSTADO),
                evento(30, Status.SAIU_ENTREGA),
                evento(60, Status.EM_TRANSITO),
            ]
        }
    )

    atualizar_pedido(pedido, provedor)

    assert pedido.status == Status.SAIU_ENTREGA


class ProvedorComPrevisao(ProvedorFalso):
    def __init__(self, respostas, previsao):
        super().__init__(respostas)
        self.previsao = previsao

    def consultar(self, codigo, referencia):
        rastreio = super().consultar(codigo, referencia)
        return Rastreio(eventos=rastreio.eventos, previsao_entrega=self.previsao)


def test_grava_o_detalhe_do_evento(fabrica_pedido):
    pedido = fabrica_pedido(codigo=CODIGO)
    com_detalhe = EventoRastreio(
        descricao="Objeto aguardando retirada",
        ocorrido_em=BASE,
        status=Status.EM_TRANSITO,
        detalhe="Leve um documento",
    )
    atualizar_pedido(pedido, ProvedorFalso({CODIGO: [com_detalhe]}))
    assert [e.detalhe for e in eventos_dos_correios(pedido)] == ["Leve um documento"]


def test_grava_a_previsao_de_entrega(fabrica_pedido):
    pedido = fabrica_pedido(codigo=CODIGO)
    provedor = ProvedorComPrevisao({CODIGO: [evento(0, Status.POSTADO)]}, date(2026, 10, 20))
    atualizar_pedido(pedido, provedor)
    assert pedido.previsao_entrega == date(2026, 10, 20)


def test_previsao_nao_e_apagada_quando_o_provedor_nao_informa(fabrica_pedido):
    pedido = fabrica_pedido(codigo=CODIGO)
    atualizar_pedido(pedido, ProvedorComPrevisao({CODIGO: []}, date(2026, 10, 20)))
    db.session.commit()
    atualizar_pedido(pedido, ProvedorFalso({CODIGO: []}))
    assert pedido.previsao_entrega == date(2026, 10, 20)