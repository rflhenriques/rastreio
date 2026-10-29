from datetime import datetime, timedelta, timezone

import pytest
import requests

from app.provedores.base import ErroProvedor
from app.provedores.correios_cliente import ClienteCorreios, criar_cliente_correios

CODIGO = "XX000000000BR"
TOKEN_OK = {
    "token": "token-de-teste",
    "expiraEm": "2099-01-01T00:00:00",
    "ambiente": "PRODUCAO",
    "api": [87],
}
TOKEN_VENCIDO = {**TOKEN_OK, "expiraEm": "2000-01-01T00:00:00"}
OBJETO_OK = {"objetos": [{"codObjeto": CODIGO, "eventos": []}]}


class RespostaFalsa:
    def __init__(self, status=200, dados=None, texto=""):
        self.status_code = status
        self._dados = dados
        self.text = texto or ("" if dados is None else str(dados))

    def json(self):
        if self._dados is None:
            raise ValueError("sem JSON")
        return self._dados


class SessaoFalsa:
    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def request(self, metodo, url, **opcoes):
        self.chamadas.append((metodo, url, opcoes))
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


def cliente_com_chave(*respostas):
    sessao = SessaoFalsa(*respostas)
    cliente = ClienteCorreios("producao", chave_acesso="cws-chave-de-teste", sessao=sessao)
    return cliente, sessao


def cliente_com_codigo(*respostas):
    sessao = SessaoFalsa(*respostas)
    cliente = ClienteCorreios(
        "producao",
        usuario="usuario",
        codigo_acesso="codigo",
        cartao_postagem="0012345678",
        sessao=sessao,
    )
    return cliente, sessao


def metodos(sessao):
    return [chamada[0] for chamada in sessao.chamadas]


# ---------- modo chave de acesso ----------


def test_chave_vai_como_bearer_sem_gerar_token():
    cliente, sessao = cliente_com_chave(RespostaFalsa(200, OBJETO_OK))

    dados = cliente.consultar_objeto(CODIGO)

    assert dados == OBJETO_OK
    assert len(sessao.chamadas) == 1
    metodo, url, opcoes = sessao.chamadas[0]
    assert metodo == "get"
    assert url == f"https://api.correios.com.br/srorastro/v1/objetos/{CODIGO}"
    assert opcoes["headers"]["Authorization"] == "Bearer cws-chave-de-teste"
    assert opcoes["params"] == {"resultado": "T"}
    assert opcoes["timeout"] == 15


@pytest.mark.parametrize(
    "ambiente, base",
    [
        ("producao", "https://api.correios.com.br"),
        ("homologacao", "https://apihom.correios.com.br"),
    ],
)
def test_ambiente_define_a_url_base(ambiente, base):
    sessao = SessaoFalsa(RespostaFalsa(200, OBJETO_OK))
    cliente = ClienteCorreios(ambiente, chave_acesso="cws-x", sessao=sessao)

    cliente.consultar_objeto(CODIGO)

    assert sessao.chamadas[0][1].startswith(base)


def test_codigo_estranho_nao_altera_o_caminho():
    cliente, sessao = cliente_com_chave(RespostaFalsa(200, OBJETO_OK))

    cliente.consultar_objeto("../token")

    assert sessao.chamadas[0][1].endswith("/objetos/..%2Ftoken")


def test_401_com_chave_nao_tenta_de_novo():
    cliente, sessao = cliente_com_chave(RespostaFalsa(401))

    with pytest.raises(ErroProvedor, match="chave de acesso foi recusada"):
        cliente.consultar_objeto(CODIGO)

    assert len(sessao.chamadas) == 1


def test_403_vira_erro_de_permissao():
    cliente, _ = cliente_com_chave(RespostaFalsa(403))

    with pytest.raises(ErroProvedor, match="Sem permissão"):
        cliente.consultar_objeto(CODIGO)


def test_outros_status_mostram_o_codigo_e_um_trecho():
    cliente, _ = cliente_com_chave(RespostaFalsa(500, None, "falha interna"))

    with pytest.raises(ErroProvedor) as erro:
        cliente.consultar_objeto(CODIGO)

    assert "HTTP 500" in str(erro.value)
    assert "falha interna" in str(erro.value)


def test_resposta_que_nao_e_json_vira_erro():
    cliente, _ = cliente_com_chave(RespostaFalsa(200, None))

    with pytest.raises(ErroProvedor, match="não é um JSON válido"):
        cliente.consultar_objeto(CODIGO)


def test_falha_de_rede_nao_vaza_detalhes():
    sessao = SessaoFalsa(requests.ConnectionError("detalhe interno sensivel"))
    cliente = ClienteCorreios("producao", chave_acesso="cws-x", sessao=sessao)

    with pytest.raises(ErroProvedor) as erro:
        cliente.consultar_objeto(CODIGO)

    mensagem = str(erro.value)
    assert "Falha de rede" in mensagem
    assert "ConnectionError" in mensagem
    assert "sensivel" not in mensagem


# ---------- modo código de acesso (token) ----------


def test_token_e_gerado_com_basic_auth_e_cartao():
    cliente, sessao = cliente_com_codigo(
        RespostaFalsa(201, TOKEN_OK), RespostaFalsa(200, OBJETO_OK)
    )

    cliente.consultar_objeto(CODIGO)

    (metodo1, url1, opcoes1), (_, _, opcoes2) = sessao.chamadas
    assert metodo1 == "post"
    assert url1 == "https://api.correios.com.br/token/v1/autentica/cartaopostagem"
    assert opcoes1["auth"] == ("usuario", "codigo")
    assert opcoes1["json"] == {"numero": "0012345678"}
    assert opcoes2["headers"]["Authorization"] == "Bearer token-de-teste"


def test_token_e_reaproveitado_entre_consultas():
    cliente, sessao = cliente_com_codigo(
        RespostaFalsa(201, TOKEN_OK),
        RespostaFalsa(200, OBJETO_OK),
        RespostaFalsa(200, OBJETO_OK),
    )

    cliente.consultar_objeto(CODIGO)
    cliente.consultar_objeto(CODIGO)

    assert metodos(sessao) == ["post", "get", "get"]


def test_401_com_token_gera_outro_e_repete_uma_vez():
    cliente, sessao = cliente_com_codigo(
        RespostaFalsa(201, TOKEN_OK),
        RespostaFalsa(401),
        RespostaFalsa(201, TOKEN_OK),
        RespostaFalsa(200, OBJETO_OK),
    )

    assert cliente.consultar_objeto(CODIGO) == OBJETO_OK
    assert metodos(sessao) == ["post", "get", "post", "get"]


def test_401_persistente_com_token_vira_erro():
    cliente, sessao = cliente_com_codigo(
        RespostaFalsa(201, TOKEN_OK),
        RespostaFalsa(401),
        RespostaFalsa(201, TOKEN_OK),
        RespostaFalsa(401),
    )

    with pytest.raises(ErroProvedor, match="recusaram o token"):
        cliente.consultar_objeto(CODIGO)

    assert len(sessao.chamadas) == 4


def test_geracao_de_token_recusada_mostra_status_e_trecho():
    cliente, _ = cliente_com_codigo(RespostaFalsa(401, None, "usuario invalido"))

    with pytest.raises(ErroProvedor) as erro:
        cliente.gerar_token()

    assert "recusaram a geração do token" in str(erro.value)
    assert "HTTP 401" in str(erro.value)
    assert "usuario invalido" in str(erro.value)


def test_token_vencido_e_renovado_na_consulta_seguinte():
    cliente, sessao = cliente_com_codigo(
        RespostaFalsa(201, TOKEN_VENCIDO),
        RespostaFalsa(200, OBJETO_OK),
        RespostaFalsa(201, TOKEN_OK),
        RespostaFalsa(200, OBJETO_OK),
    )

    cliente.consultar_objeto(CODIGO)
    cliente.consultar_objeto(CODIGO)

    assert metodos(sessao) == ["post", "get", "post", "get"]


def test_expiracao_sem_fuso_e_lida_como_horario_de_brasilia():
    esperado = datetime(2026, 10, 27, 13, 0, tzinfo=timezone.utc)

    assert ClienteCorreios._ler_expiracao("2026-10-27T10:00:00") == esperado


def test_expiracao_ilegivel_usa_a_validade_padrao():
    antes = datetime.now(timezone.utc)

    expira = ClienteCorreios._ler_expiracao("lixo")

    assert timedelta(minutes=29) < expira - antes < timedelta(minutes=31)


# ---------- configuração ----------


def test_faltam_variaveis_sao_listadas():
    with pytest.raises(ErroProvedor) as erro:
        ClienteCorreios("producao")

    texto = str(erro.value)
    for nome in (
        "CORREIOS_USUARIO",
        "CORREIOS_CODIGO_ACESSO",
        "CORREIOS_CARTAO_POSTAGEM",
        "CORREIOS_CHAVE_ACESSO",
    ):
        assert nome in texto


def test_ambiente_invalido_e_recusado():
    with pytest.raises(ErroProvedor, match="CORREIOS_AMBIENTE inválido"):
        ClienteCorreios("teste", chave_acesso="cws-x")


def test_chave_mascarada_nao_revela_a_chave():
    chave = "cws-" + "a" * 60 + "WXYZ"
    cliente = ClienteCorreios("producao", chave_acesso=chave)
    curta = ClienteCorreios("producao", chave_acesso="curta")

    assert cliente.chave_mascarada == "cws-...WXYZ"
    assert cliente.tamanho_da_chave == len(chave)
    assert curta.chave_mascarada == "***"


def test_criar_cliente_limpa_espacos_e_quebras_de_linha():
    config = {
        "CORREIOS_AMBIENTE": "producao",
        "CORREIOS_CHAVE_ACESSO": "  cws-abcdefghijkl  \n",
        "CORREIOS_TIMEOUT": 7,
    }

    cliente = criar_cliente_correios(config)

    assert cliente.usa_chave_de_acesso
    assert cliente.tamanho_da_chave == len("cws-abcdefghijkl")