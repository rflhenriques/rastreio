from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests

from app.provedores.base import ErroProvedor

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")

URLS_BASE = {
    "producao": "https://api.correios.com.br",
    "homologacao": "https://apihom.correios.com.br",
}

MARGEM_RENOVACAO = timedelta(minutes=5)
VALIDADE_PADRAO = timedelta(minutes=30)


def _trecho(resposta, limite=200):
    return (resposta.text or "").strip().replace("\n", " ")[:limite]


def _limpo(valor):
    return (valor or "").strip() or None


class ClienteCorreios:
    def __init__(
        self,
        ambiente,
        usuario=None,
        codigo_acesso=None,
        cartao_postagem=None,
        chave_acesso=None,
        timeout=15,
        sessao=None,
    ):
        if ambiente not in URLS_BASE:
            opcoes = ", ".join(URLS_BASE)
            raise ErroProvedor(f"CORREIOS_AMBIENTE inválido: '{ambiente}'. Use: {opcoes}.")

        if not chave_acesso:
            ausentes = [
                nome
                for nome, valor in (
                    ("CORREIOS_USUARIO", usuario),
                    ("CORREIOS_CODIGO_ACESSO", codigo_acesso),
                    ("CORREIOS_CARTAO_POSTAGEM", cartao_postagem),
                )
                if not valor
            ]
            if ausentes:
                raise ErroProvedor(
                    "Faltam no .env: " + ", ".join(ausentes)
                    + " (ou defina CORREIOS_CHAVE_ACESSO)."
                )

        self.ambiente = ambiente
        self.base = URLS_BASE[ambiente]
        self.token_expira_em = None
        self.info_token = {}

        self._chave = chave_acesso or None
        self._credenciais = (usuario, codigo_acesso)
        self._cartao = cartao_postagem
        self._timeout = timeout
        self._sessao = sessao or requests.Session()
        self._token = None

    @property
    def usa_chave_de_acesso(self):
        return bool(self._chave)

    @property
    def tamanho_da_chave(self):
        return len(self._chave or "")

    @property
    def chave_mascarada(self):
        chave = self._chave or ""
        if len(chave) <= 10:
            return "***"
        return f"{chave[:4]}...{chave[-4:]}"

    # ----- token (somente no modo código de acesso) -----

    def gerar_token(self):
        if self._chave:
            raise ErroProvedor("Com chave de acesso não há token para gerar.")

        resposta = self._enviar(
            "post",
            f"{self.base}/token/v1/autentica/cartaopostagem",
            auth=self._credenciais,
            json={"numero": self._cartao},
            headers={"Accept": "application/json"},
        )
        if resposta.status_code not in (200, 201):
            raise ErroProvedor(
                f"Os Correios recusaram a geração do token "
                f"(HTTP {resposta.status_code}): {_trecho(resposta)}"
            )

        try:
            dados = resposta.json()
            token = dados["token"]
        except (ValueError, KeyError, TypeError) as erro:
            raise ErroProvedor("Resposta inesperada ao gerar o token.") from erro

        self._token = token
        self.token_expira_em = self._ler_expiracao(dados.get("expiraEm"))
        self.info_token = {
            "ambiente": dados.get("ambiente"),
            "apis": dados.get("api"),
            "expiraEm": dados.get("expiraEm"),
        }

    @staticmethod
    def _ler_expiracao(texto):
        try:
            momento = datetime.fromisoformat(texto)
        except (TypeError, ValueError):
            return datetime.now(timezone.utc) + VALIDADE_PADRAO
        if momento.tzinfo is None:
            momento = momento.replace(tzinfo=FUSO_BRASILIA)
        return momento.astimezone(timezone.utc)

    def token_valido(self):
        if not self._token or self.token_expira_em is None:
            return False
        return datetime.now(timezone.utc) < self.token_expira_em - MARGEM_RENOVACAO

    def _cabecalhos(self):
        if self._chave:
            return {"Authorization": f"Bearer {self._chave}", "Accept": "application/json"}
        if not self.token_valido():
            self.gerar_token()
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    # ----- consulta -----

    def consultar_objeto(self, codigo):
        url = f"{self.base}/srorastro/v1/objetos/{quote(codigo, safe='')}"

        for tentativa in (1, 2):
            resposta = self._enviar(
                "get", url, headers=self._cabecalhos(), params={"resultado": "T"}
            )
            pode_renovar = tentativa == 1 and not self._chave
            if resposta.status_code == 401 and pode_renovar:
                self._token = None  # força um token novo e repete uma vez
                continue
            break

        if resposta.status_code == 401:
            if self._chave:
                raise ErroProvedor(
                    "A chave de acesso foi recusada (HTTP 401): pode ter expirado, "
                    "sido revogada ou ser de outro ambiente. Crie uma nova no CWS."
                )
            raise ErroProvedor("Os Correios recusaram o token (HTTP 401).")
        if resposta.status_code == 403:
            raise ErroProvedor(
                "Sem permissão para consultar este objeto (HTTP 403): a API Rastro "
                "pode não estar liberada para esta credencial, ou o objeto é de outro contrato."
            )
        if resposta.status_code != 200:
            raise ErroProvedor(
                f"Os Correios responderam HTTP {resposta.status_code}: {_trecho(resposta)}"
            )

        try:
            return resposta.json()
        except ValueError as erro:
            raise ErroProvedor("A resposta dos Correios não é um JSON válido.") from erro

    # ----- rede -----

    def _enviar(self, metodo, url, **opcoes):
        try:
            return self._sessao.request(metodo, url, timeout=self._timeout, **opcoes)
        except requests.RequestException as erro:
            raise ErroProvedor(
                f"Falha de rede ao falar com os Correios ({erro.__class__.__name__})."
            ) from erro


def criar_cliente_correios(config):
    return ClienteCorreios(
        ambiente=config["CORREIOS_AMBIENTE"],
        usuario=_limpo(config.get("CORREIOS_USUARIO")),
        codigo_acesso=_limpo(config.get("CORREIOS_CODIGO_ACESSO")),
        cartao_postagem=_limpo(config.get("CORREIOS_CARTAO_POSTAGEM")),
        chave_acesso=_limpo(config.get("CORREIOS_CHAVE_ACESSO")),
        timeout=config["CORREIOS_TIMEOUT"],
    )