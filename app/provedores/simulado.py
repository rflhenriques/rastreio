from datetime import datetime, timedelta, timezone

from app.models import Status
from app.provedores.base import EventoRastreio, ProvedorRastreio

# (horas após a postagem, descrição, local, status)
ROTEIRO = [
    (0, "Objeto postado", "Agência dos Correios", Status.POSTADO),
    (20, "Objeto em transferência - por favor aguarde",
     "Unidade de Tratamento", Status.EM_TRANSITO),
    (44, "Objeto chegou à unidade de distribuição",
     "Unidade de Distribuição", Status.EM_TRANSITO),
    (68, "Objeto saiu para entrega ao destinatário",
     "Unidade de Distribuição", Status.SAIU_ENTREGA),
    (74, "Objeto entregue ao destinatário",
     "Endereço do destinatário", Status.ENTREGUE),
]

ANCORA = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


class ProvedorSimulado(ProvedorRastreio):
    def buscar_eventos(self, codigo):
        semente = sum(ord(letra) for letra in codigo)
        postagem = ANCORA + timedelta(hours=semente % 48)
        quantidade = semente % len(ROTEIRO) + 1

        return [
            EventoRastreio(
                descricao=descricao,
                local=local,
                ocorrido_em=postagem + timedelta(hours=horas),
                status=status,
            )
            for horas, descricao, local, status in ROTEIRO[:quantidade]
        ]