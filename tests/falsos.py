from datetime import datetime, timedelta, timezone

from app.provedores.base import EventoRastreio, ProvedorRastreio

EMAIL = "teste@exemplo.com"
SENHA = "senha-de-teste"

BASE = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def evento(minutos, status, descricao=None):
    return EventoRastreio(
        descricao=descricao or f"Evento {minutos}",
        ocorrido_em=BASE + timedelta(minutes=minutos),
        status=status,
    )


class ProvedorFalso(ProvedorRastreio):
    def __init__(self, respostas=None):
        self.respostas = respostas or {}
        self.chamadas = []

    def buscar_eventos(self, codigo, referencia):
        self.chamadas.append((codigo, referencia))
        resposta = self.respostas.get(codigo, [])
        if isinstance(resposta, Exception):
            raise resposta
        return list(resposta)