from datetime import datetime, timedelta, timezone

from app.models import Status
from app.provedores.simulado import ProvedorSimulado

CHEGA_ATE_ENTREGUE = "AA000000004BR"  # a soma dos caracteres leva ao 5º evento
FICA_EM_POSTADO = "AA000000005BR"  # a soma dos caracteres leva ao 1º evento


def agora():
    return datetime.now(timezone.utc)


def test_mesmo_codigo_e_mesma_referencia_dao_o_mesmo_resultado():
    referencia = agora() - timedelta(hours=1)

    primeiro = ProvedorSimulado().buscar_eventos(CHEGA_ATE_ENTREGUE, referencia)
    segundo = ProvedorSimulado().buscar_eventos(CHEGA_ATE_ENTREGUE, referencia)

    assert primeiro == segundo


def test_so_devolve_eventos_que_ja_aconteceram():
    referencia = agora() - timedelta(seconds=30)

    eventos = ProvedorSimulado().buscar_eventos(CHEGA_ATE_ENTREGUE, referencia)

    assert [e.status for e in eventos] == [Status.POSTADO]


def test_o_codigo_define_ate_onde_o_pacote_chega():
    referencia = agora() - timedelta(days=1)

    entregue = ProvedorSimulado().buscar_eventos(CHEGA_ATE_ENTREGUE, referencia)
    parado = ProvedorSimulado().buscar_eventos(FICA_EM_POSTADO, referencia)

    assert len(entregue) == 5
    assert entregue[-1].status == Status.ENTREGUE
    assert len(parado) == 1
    assert parado[0].status == Status.POSTADO


def test_eventos_vem_em_ordem_cronologica_e_depois_da_referencia():
    referencia = agora() - timedelta(days=1)

    eventos = ProvedorSimulado().buscar_eventos(CHEGA_ATE_ENTREGUE, referencia)

    momentos = [e.ocorrido_em for e in eventos]
    assert momentos == sorted(momentos)
    assert all(momento > referencia for momento in momentos)