from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models import Status


@dataclass(frozen=True)
class EventoRastreio:
    descricao: str
    ocorrido_em: datetime
    status: Status
    local: str | None = None


class ErroProvedor(Exception):
    """Falha ao consultar o provedor (rede, credencial, resposta inválida)."""


class ProvedorRastreio(ABC):
    @abstractmethod
    def buscar_eventos(self, codigo: str) -> list[EventoRastreio]:
        """Devolve os eventos de rastreio do código, em qualquer ordem."""