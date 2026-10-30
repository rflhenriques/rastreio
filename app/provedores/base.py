from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from app.models import Status


@dataclass(frozen=True)
class EventoRastreio:
    descricao: str
    ocorrido_em: datetime
    status: Status
    local: str | None = None
    detalhe: str | None = None


@dataclass(frozen=True)
class Rastreio:
    eventos: list[EventoRastreio]
    previsao_entrega: date | None = None


class ErroProvedor(Exception):
    """Falha ao consultar o provedor (rede, credencial, resposta inválida)."""


class ProvedorRastreio(ABC):
    @abstractmethod
    def buscar_eventos(self, codigo: str, referencia: datetime) -> list[EventoRastreio]:
        """Devolve os eventos de rastreio do código, em qualquer ordem.

        `referencia` é o momento (em UTC, com fuso) em que o pedido ficou pronto
        para postagem. Provedores reais podem ignorá-lo; o simulado o usa para
        gerar eventos coerentes com o histórico interno.
        """

    def consultar(self, codigo: str, referencia: datetime) -> Rastreio:
        """Devolve os eventos e, se o provedor souber, a previsão de entrega.

        A versão padrão só repassa os eventos. Provedores que trazem a previsão
        (como o dos Correios) sobrescrevem este método.
        """
        return Rastreio(eventos=self.buscar_eventos(codigo, referencia))