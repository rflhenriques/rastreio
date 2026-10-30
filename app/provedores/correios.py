import logging
from datetime import datetime, timezone

from flask import current_app

from app.models import Status
from app.provedores.base import ErroProvedor, EventoRastreio, ProvedorRastreio, Rastreio
from app.provedores.correios_cliente import FUSO_BRASILIA, criar_cliente_correios

log = logging.getLogger(__name__)

CODIGOS_CONHECIDOS = {"PO", "RO", "DO", "FC", "OEC", "BDE", "BDI", "BDR", "LDI"}
CODIGOS_DE_BAIXA = {"BDE", "BDI", "BDR"}
PREPOSICOES = {"de", "da", "do", "das", "dos", "e"}


def classificar(codigo, descricao):
    texto = (descricao or "").strip().lower()

    if codigo == "PO":
        return Status.POSTADO
    if codigo == "OEC":
        return Status.SAIU_ENTREGA
    if codigo in CODIGOS_DE_BAIXA and texto.startswith("objeto entregue ao destinat"):
        return Status.ENTREGUE
    return Status.EM_TRANSITO


def nome_proprio(texto):
    palavras = texto.lower().split()
    return " ".join(
        palavra if posicao and palavra in PREPOSICOES else palavra.capitalize()
        for posicao, palavra in enumerate(palavras)
    )


def _descrever_unidade(unidade):
    if not isinstance(unidade, dict):
        return None

    endereco = unidade.get("endereco") or {}
    cidade = endereco.get("cidade")
    uf = endereco.get("uf")
    lugar = "/".join(
        parte for parte in (nome_proprio(cidade) if cidade else None, uf) if parte
    )
    partes = [parte for parte in (unidade.get("tipo"), lugar) if parte]
    return " - ".join(partes) or None


def _local(bruto):
    origem = _descrever_unidade(bruto.get("unidade"))
    destino = _descrever_unidade(bruto.get("unidadeDestino"))
    if origem and destino:
        return f"{origem} → {destino}"
    return origem or destino


def _ler_data(texto):
    momento = datetime.fromisoformat(texto)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=FUSO_BRASILIA)
    return momento.astimezone(timezone.utc)


def traduzir_resposta(dados):
    objetos = dados.get("objetos") if isinstance(dados, dict) else None
    if not objetos:
        return []

    objeto = objetos[0]
    brutos = objeto.get("eventos") or []
    if not brutos:
        mensagem = objeto.get("mensagem")
        if mensagem:
            raise ErroProvedor(f"Os Correios informaram: {mensagem}")
        return []

    eventos = []
    for bruto in brutos:
        codigo = bruto.get("codigo")
        descricao = bruto.get("descricao")
        if not codigo or not descricao:
            continue

        try:
            momento = _ler_data(bruto.get("dtHrCriado"))
        except (TypeError, ValueError):
            log.warning("Evento dos Correios ignorado (data inválida): %s", codigo)
            continue

        if codigo not in CODIGOS_CONHECIDOS:
            log.warning(
                "Código de evento dos Correios sem mapeamento: %s (%s)", codigo, descricao
            )

        detalhe = (bruto.get("detalhe") or "").strip() or None
        eventos.append(
            EventoRastreio(
                descricao=descricao,
                ocorrido_em=momento,
                status=classificar(codigo, descricao),
                local=_local(bruto),
                detalhe=detalhe,
            )
        )
    return eventos


def extrair_previsao(dados):
    objetos = dados.get("objetos") if isinstance(dados, dict) else None
    if not objetos or not isinstance(objetos[0], dict):
        return None
    try:
        return datetime.fromisoformat(objetos[0].get("dtPrevista")).date()
    except (TypeError, ValueError):
        return None


class ProvedorCorreios(ProvedorRastreio):
    def __init__(self, cliente=None):
        self._cliente = cliente

    def _cliente_correios(self):
        if self._cliente is None:
            self._cliente = criar_cliente_correios(current_app.config)
        return self._cliente

    def consultar(self, codigo, referencia):
        dados = self._cliente_correios().consultar_objeto(codigo)
        return Rastreio(
            eventos=traduzir_resposta(dados),
            previsao_entrega=extrair_previsao(dados),
        )

    def buscar_eventos(self, codigo, referencia):
        return self.consultar(codigo, referencia).eventos