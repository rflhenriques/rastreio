from app.provedores.base import ErroProvedor, EventoRastreio, ProvedorRastreio
from app.provedores.correios import ProvedorCorreios
from app.provedores.simulado import ProvedorSimulado

PROVEDORES = {
    "simulado": ProvedorSimulado,
    "correios": ProvedorCorreios,
}


def obter_provedor(nome):
    classe = PROVEDORES.get(nome)
    if classe is None:
        disponiveis = ", ".join(PROVEDORES)
        raise ValueError(f"Provedor '{nome}' desconhecido. Disponíveis: {disponiveis}")
    return classe()