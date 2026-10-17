from datetime import datetime, timedelta, timezone

from app.models import Status
from app.provedores.base import EventoRastreio, ProvedorRastreio

MINUTOS_ENTRE_EVENTOS = 2
DESLOCAMENTO_INICIAL = timedelta(seconds=1)

ROTEIRO = [
    ("Objeto postado", "Agência dos Correios", Status.POSTADO),
    ("Objeto em transferência - por favor aguarde",
     "Unidade de Tratamento", Status.EM_TRANSITO),
    ("Objeto chegou à unidade de distribuição",
     "Unidade de Distribuição", Status.EM_TRANSITO),
    ("Objeto saiu para entrega ao destinatário",
     "Unidade de Distribuição", Status.SAIU_ENTREGA),
    ("Objeto entregue ao destinatário",
     "Endereço do destinatário", Status.ENTREGUE),
]


class ProvedorSimulado(ProvedorRastreio):
    def buscar_eventos(self, codigo, referencia):
        agora = datetime.now(timezone.utc)
        semente = sum(ord(letra) for letra in codigo)
        limite = semente % len(ROTEIRO) + 1

        eventos = []
        for passo, (descricao, local, status) in enumerate(ROTEIRO[:limite]):
            momento = (
                referencia
                + DESLOCAMENTO_INICIAL
                + timedelta(minutes=passo * MINUTOS_ENTRE_EVENTOS)
            )
            if momento > agora:
                break
            eventos.append(
                EventoRastreio(
                    descricao=descricao,
                    local=local,
                    ocorrido_em=momento,
                    status=status,
                )
            )
        return eventos