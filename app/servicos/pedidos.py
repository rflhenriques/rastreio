from app.extensions import db
from app.models import (
    ROTULOS_STATUS,
    Evento,
    Origem,
    Pedido,
    Status,
    agora_utc,
)

PADRAO_CODIGO = r"^[A-Z]{2}\d{9}[A-Z]{2}$"

PROXIMA_ETAPA = {
    Status.RECEBIDO: Status.EM_PREPARACAO,
    Status.EM_PREPARACAO: Status.PRONTO_POSTAGEM,
}


class ErroDeRegra(Exception):
    """A operação não é permitida pelas regras do pedido."""


def registrar_evento_interno(pedido, descricao):
    pedido.eventos.append(
        Evento(origem=Origem.INTERNA, descricao=descricao, ocorrido_em=agora_utc())
    )


def criar_pedido(nome_cliente, tipo_envio):
    pedido = Pedido(
        nome_cliente=nome_cliente,
        tipo_envio=tipo_envio,
        status=Status.RECEBIDO,
    )
    registrar_evento_interno(pedido, pedido.rotulo_status)
    db.session.add(pedido)
    return pedido


def proxima_etapa_interna(pedido):
    proxima = PROXIMA_ETAPA.get(pedido.status)
    return ROTULOS_STATUS[proxima] if proxima else None


def avancar_etapa(pedido, etapa_esperada):
    if pedido.status.name != etapa_esperada:
        raise ErroDeRegra(
            "O pedido já mudou de etapa. Atualize a página e confira o status atual."
        )

    proxima = PROXIMA_ETAPA.get(pedido.status)
    if proxima is None:
        raise ErroDeRegra("Este pedido não tem uma próxima etapa interna.")

    pedido.status = proxima
    registrar_evento_interno(pedido, pedido.rotulo_status)


def cadastrar_codigo(pedido, codigo):
    import re

    if not re.fullmatch(PADRAO_CODIGO, codigo):
        raise ErroDeRegra("Código inválido. Use 2 letras, 9 números e 2 letras.")

    if pedido.entregue:
        raise ErroDeRegra("O pedido já foi entregue.")

    if pedido.tem_eventos_correios:
        raise ErroDeRegra(
            "Já existem eventos dos Correios para este pedido; "
            "o código não pode mais ser trocado."
        )

    outro = db.session.scalar(
        db.select(Pedido).where(
            Pedido.codigo_rastreio == codigo, Pedido.id != pedido.id
        )
    )
    if outro:
        raise ErroDeRegra(
            f"Este código já está cadastrado no pedido de {outro.nome_cliente}."
        )

    pedido.codigo_rastreio = codigo