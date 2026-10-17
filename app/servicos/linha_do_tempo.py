from dataclasses import dataclass

from app.models import Status, rotulo_do_status

ORDEM = list(Status)


@dataclass(frozen=True)
class Etapa:
    rotulo: str
    estado: str  # "feita", "atual" ou "pendente"


def montar_etapas(pedido):
    posicao_atual = ORDEM.index(pedido.status)
    etapas = []

    for posicao, status in enumerate(ORDEM):
        if pedido.entregue or posicao < posicao_atual:
            estado = "feita"
        elif posicao == posicao_atual:
            estado = "atual"
        else:
            estado = "pendente"
        etapas.append(Etapa(rotulo_do_status(status, pedido.tipo_envio), estado))

    return etapas