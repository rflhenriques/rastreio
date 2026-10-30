from datetime import datetime, timedelta, timezone

from app.models import Status
from app.provedores.base import EventoRastreio, ProvedorRastreio, Rastreio

MINUTOS_ENTRE_EVENTOS = 2
DESLOCAMENTO_INICIAL = timedelta(seconds=1)
PRAZO_PREVISTO = timedelta(days=3)

# (descrição, local, status, detalhe)
ROTEIRO = [
    ("Objeto postado", "Agência dos Correios", Status.POSTADO, None),
    (
        "Objeto em transferência - por favor aguarde",
        "Unidade de Tratamento",
        Status.EM_TRANSITO,
        None,
    ),
    (
        "Objeto chegou à unidade de distribuição",
        "Unidade de Distribuição",
        Status.EM_TRANSITO,
        None,
    ),
    (
        "Objeto saiu para entrega ao destinatário",
        "Unidade de Distribuição",
        Status.SAIU_ENTREGA,
        "É preciso ter alguém no endereço para receber o carteiro",
    ),
    ("Objeto entregue ao destinatário", "Endereço do destinatário", Status.ENTREGUE, None),
]


class ProvedorSimulado(ProvedorRastreio):
    def buscar_eventos(self, codigo, referencia):
        agora = datetime.now(timezone.utc)
        semente = sum(ord(letra) for letra in codigo)
        limite = semente % len(ROTEIRO) + 1

        eventos = []
        for passo, (descricao, local, status, detalhe) in enumerate(ROTEIRO[:limite]):
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
                    detalhe=detalhe,
                )
            )
        return eventos

    def consultar(self, codigo, referencia):
        return Rastreio(
            eventos=self.buscar_eventos(codigo, referencia),
            previsao_entrega=(referencia + PRAZO_PREVISTO).date(),
        )