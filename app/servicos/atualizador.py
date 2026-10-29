from dataclasses import dataclass
from datetime import timezone

from flask import current_app

from app.extensions import db
from app.models import Evento, Origem, Pedido, Status, como_utc
from app.provedores import ErroProvedor

ORDEM_STATUS = list(Status)


@dataclass
class ResumoAtualizacao:
    pedidos: int = 0
    eventos_novos: int = 0
    erros: int = 0


def _como_utc_ingenuo(momento):
    if momento.tzinfo is not None:
        momento = momento.astimezone(timezone.utc).replace(tzinfo=None)
    return momento


def _momento_referencia(pedido):
    internos = [
        como_utc(e.ocorrido_em) for e in pedido.eventos if e.origem == Origem.INTERNA
    ]
    return max(internos) if internos else como_utc(pedido.criado_em)


def atualizar_pedido(pedido, provedor):
    eventos = provedor.buscar_eventos(
        pedido.codigo_rastreio, _momento_referencia(pedido)
    )

    ja_gravados = {
        (_como_utc_ingenuo(e.ocorrido_em), e.descricao)
        for e in pedido.eventos
        if e.origem == Origem.CORREIOS
    }

    novos = 0
    for evento in eventos:
        chave = (_como_utc_ingenuo(evento.ocorrido_em), evento.descricao)
        if chave in ja_gravados:
            continue
        pedido.eventos.append(
            Evento(
                origem=Origem.CORREIOS,
                descricao=evento.descricao,
                local=evento.local,
                ocorrido_em=evento.ocorrido_em,
            )
        )
        ja_gravados.add(chave)
        novos += 1

    if eventos:
        mais_avancado = max(eventos, key=lambda e: ORDEM_STATUS.index(e.status))
        if ORDEM_STATUS.index(mais_avancado.status) > ORDEM_STATUS.index(pedido.status):
            pedido.status = mais_avancado.status

    return novos


def atualizar_todos(provedor):
    resumo = ResumoAtualizacao()

    consulta = db.select(Pedido).where(
        Pedido.codigo_rastreio.is_not(None),
        Pedido.status != Status.ENTREGUE,
    )

    for pedido in db.session.scalars(consulta).all():
        pedido_id = pedido.id
        resumo.pedidos += 1
        try:
            resumo.eventos_novos += atualizar_pedido(pedido, provedor)
            db.session.commit()
        except ErroProvedor as erro:
            db.session.rollback()
            resumo.erros += 1
            current_app.logger.warning(
                "Falha ao atualizar o pedido %s: %s", pedido_id, erro
            )

    return resumo