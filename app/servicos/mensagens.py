from flask import current_app

from app.models import TipoEnvio

MODELOS_MENSAGEM = {
    TipoEnvio.PECA_NOVA: (
        "Olá! Seu contrato foi fechado e já preparamos o acompanhamento "
        "da sua entrega. Você pode ver cada etapa por este link:\n{link}"
    ),
    TipoEnvio.REPOSICAO: (
        "Olá! Recebemos o seu pedido de reposição de peças. "
        "Acompanhe cada etapa da entrega por este link:\n{link}"
    ),
}


def link_publico(pedido):
    base = current_app.config["URL_BASE_PUBLICA"].rstrip("/")
    return f"{base}/rastreio/{pedido.token}"


def montar_mensagem_whatsapp(pedido):
    return MODELOS_MENSAGEM[pedido.tipo_envio].format(link=link_publico(pedido))