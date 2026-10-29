import pytest

from app.extensions import db
from app.models import Evento, Origem, Status, TipoEnvio, agora_utc
from app.servicos.pedidos import (
    ErroDeRegra,
    avancar_etapa,
    cadastrar_codigo,
    proxima_etapa_interna,
)


@pytest.mark.parametrize(
    "tipo, descricao",
    [
        (TipoEnvio.PECA_NOVA, "Contrato fechado"),
        (TipoEnvio.REPOSICAO, "Pedido recebido"),
    ],
)
def test_pedido_novo_nasce_com_evento_inicial(fabrica_pedido, tipo, descricao):
    pedido = fabrica_pedido(tipo=tipo)

    assert pedido.status == Status.RECEBIDO
    assert len(pedido.eventos) == 1
    assert pedido.eventos[0].origem == Origem.INTERNA
    assert pedido.eventos[0].descricao == descricao


def test_avancar_percorre_as_etapas_internas(fabrica_pedido):
    pedido = fabrica_pedido()

    avancar_etapa(pedido, "RECEBIDO")
    assert pedido.status == Status.EM_PREPARACAO

    avancar_etapa(pedido, "EM_PREPARACAO")
    assert pedido.status == Status.PRONTO_POSTAGEM

    descricoes = [e.descricao for e in pedido.eventos]
    assert descricoes == ["Contrato fechado", "Em preparação", "Pronto para postagem"]


def test_avancar_recusa_etapa_desatualizada(fabrica_pedido):
    pedido = fabrica_pedido(status=Status.EM_PREPARACAO)

    with pytest.raises(ErroDeRegra, match="já mudou de etapa"):
        avancar_etapa(pedido, "RECEBIDO")

    assert pedido.status == Status.EM_PREPARACAO


def test_avancar_recusa_quando_nao_ha_proxima_etapa_interna(fabrica_pedido):
    pedido = fabrica_pedido(status=Status.PRONTO_POSTAGEM)

    with pytest.raises(ErroDeRegra, match="próxima etapa"):
        avancar_etapa(pedido, "PRONTO_POSTAGEM")


def test_etapas_internas_se_encerram_quando_ha_codigo(fabrica_pedido):
    pedido = fabrica_pedido(status=Status.EM_PREPARACAO, codigo="AA000000001BR")

    assert proxima_etapa_interna(pedido) is None
    with pytest.raises(ErroDeRegra):
        avancar_etapa(pedido, "EM_PREPARACAO")


@pytest.mark.parametrize(
    "codigo",
    ["123", "aa000000001br", "AA00000001BR", "AA0000000011BR", ""],
)
def test_codigo_com_formato_invalido_e_recusado(fabrica_pedido, codigo):
    pedido = fabrica_pedido()

    with pytest.raises(ErroDeRegra, match="inválido"):
        cadastrar_codigo(pedido, codigo)


def test_codigo_valido_e_cadastrado(fabrica_pedido):
    pedido = fabrica_pedido()

    cadastrar_codigo(pedido, "AA000000001BR")

    assert pedido.codigo_rastreio == "AA000000001BR"


def test_codigo_ja_usado_por_outro_pedido_e_recusado(fabrica_pedido):
    fabrica_pedido(nome="Cliente A", codigo="AA000000001BR")
    outro = fabrica_pedido(nome="Cliente B")

    with pytest.raises(ErroDeRegra, match="Cliente A"):
        cadastrar_codigo(outro, "AA000000001BR")


def test_codigo_nao_pode_ser_trocado_depois_de_eventos_dos_correios(fabrica_pedido):
    pedido = fabrica_pedido(codigo="AA000000001BR")
    pedido.eventos.append(
        Evento(origem=Origem.CORREIOS, descricao="Objeto postado", ocorrido_em=agora_utc())
    )
    db.session.commit()

    with pytest.raises(ErroDeRegra, match="Já existem eventos"):
        cadastrar_codigo(pedido, "BB000000002BR")


def test_codigo_e_recusado_em_pedido_entregue(fabrica_pedido):
    pedido = fabrica_pedido(status=Status.ENTREGUE)

    with pytest.raises(ErroDeRegra, match="entregue"):
        cadastrar_codigo(pedido, "AA000000001BR")

def test_historico_mantem_os_eventos_internos_do_mais_novo_para_o_mais_antigo(
    fabrica_pedido,
):
    pedido = fabrica_pedido()
    avancar_etapa(pedido, "RECEBIDO")
    avancar_etapa(pedido, "EM_PREPARACAO")
    db.session.commit()

    descricoes = [e.descricao for e in pedido.historico]

    assert descricoes == ["Pronto para postagem", "Em preparação", "Contrato fechado"]