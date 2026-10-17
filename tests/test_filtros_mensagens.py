from datetime import datetime, timezone

from app.filtros import data_br
from app.models import TipoEnvio
from app.servicos.mensagens import link_publico, montar_mensagem_whatsapp


def test_data_br_converte_utc_para_o_horario_de_brasilia():
    sem_fuso = datetime(2026, 10, 3, 2, 0)  # o banco devolve UTC sem fuso
    com_fuso = datetime(2026, 10, 3, 2, 0, tzinfo=timezone.utc)

    assert data_br(sem_fuso) == "02/10/2026 23:00"
    assert data_br(com_fuso) == "02/10/2026 23:00"
    assert data_br(None) == "—"


def test_link_publico_usa_a_url_base_e_o_token(app, fabrica_pedido):
    app.config["URL_BASE_PUBLICA"] = "https://exemplo.com.br/"
    pedido = fabrica_pedido()

    assert link_publico(pedido) == f"https://exemplo.com.br/rastreio/{pedido.token}"


def test_mensagem_do_whatsapp_inclui_o_link_e_muda_com_o_tipo(fabrica_pedido):
    nova = fabrica_pedido(tipo=TipoEnvio.PECA_NOVA)
    reposicao = fabrica_pedido(tipo=TipoEnvio.REPOSICAO)

    mensagem_nova = montar_mensagem_whatsapp(nova)
    mensagem_reposicao = montar_mensagem_whatsapp(reposicao)

    assert link_publico(nova) in mensagem_nova
    assert "contrato foi fechado" in mensagem_nova
    assert link_publico(reposicao) in mensagem_reposicao
    assert "reposição" in mensagem_reposicao