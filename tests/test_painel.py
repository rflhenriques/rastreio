import pytest

from app.extensions import db
from app.models import Pedido, Status, TipoEnvio
from app.provedores import ErroProvedor
from falsos import EMAIL, SENHA, ProvedorFalso, evento

CODIGO = "AA000000001BR"


def entrar(client, email=EMAIL, senha=SENHA):
    return client.post("/painel/login", data={"email": email, "senha": senha})


def usar_provedor(monkeypatch, provedor):
    monkeypatch.setattr("app.painel.routes.obter_provedor", lambda nome: provedor)


def pagina(resposta):
    return resposta.get_data(as_text=True)


# ---------- Proteção por login ----------


@pytest.mark.parametrize(
    "caminho", ["/painel/", "/painel/pedidos/novo", "/painel/pedidos/1"]
)
def test_paginas_do_painel_exigem_login(client, caminho):
    resposta = client.get(caminho)

    assert resposta.status_code == 302
    assert "/painel/login" in resposta.headers["Location"]


@pytest.mark.parametrize(
    "caminho",
    [
        "/painel/pedidos/1/avancar",
        "/painel/pedidos/1/codigo",
        "/painel/pedidos/1/consultar",
        "/painel/logout",
    ],
)
def test_acoes_do_painel_exigem_login(client, caminho):
    resposta = client.post(caminho)

    assert resposta.status_code == 302
    assert "/painel/login" in resposta.headers["Location"]


# ---------- Login e logout ----------


def test_login_correto_leva_ao_painel(client, usuario):
    resposta = entrar(client)

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/painel/")


@pytest.mark.parametrize(
    "email, senha",
    [(EMAIL, "senha-errada"), ("outro@exemplo.com", SENHA)],
)
def test_login_invalido_mostra_a_mesma_mensagem(client, usuario, email, senha):
    resposta = entrar(client, email=email, senha=senha)

    assert resposta.status_code == 200
    assert "E-mail ou senha incorretos." in pagina(resposta)


def test_login_aceita_o_email_em_maiusculas(client, usuario):
    resposta = entrar(client, email=EMAIL.upper())

    assert resposta.status_code == 302


@pytest.mark.parametrize(
    "destino, esperado",
    [
        ("https://example.com", "/painel/"),
        ("//example.com", "/painel/"),
        ("/\\example.com", "/painel/"),
        ("/painel/pedidos/novo", "/painel/pedidos/novo"),
    ],
)
def test_login_so_redireciona_para_destinos_internos(
    client, usuario, destino, esperado
):
    resposta = client.post(
        "/painel/login",
        query_string={"next": destino},
        data={"email": EMAIL, "senha": SENHA},
    )

    assert resposta.headers["Location"].endswith(esperado)


def test_logout_exige_post_e_encerra_a_sessao(cliente_logado):
    assert cliente_logado.get("/painel/logout").status_code == 405

    resposta = cliente_logado.post("/painel/logout")

    assert resposta.status_code == 302
    assert cliente_logado.get("/painel/").status_code == 302
    

def test_usuario_logado_que_abre_o_login_vai_direto_ao_painel(cliente_logado):
    resposta = cliente_logado.get("/painel/login")

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/painel/")


# ---------- Pedidos ----------


def test_lista_mostra_os_pedidos(cliente_logado, fabrica_pedido):
    fabrica_pedido(nome="Arena Alfa")
    fabrica_pedido(nome="Arena Beta")

    html = pagina(cliente_logado.get("/painel/"))

    assert "Arena Alfa" in html
    assert "Arena Beta" in html


def test_criar_pedido_pelo_painel(cliente_logado):
    resposta = cliente_logado.post(
        "/painel/pedidos/novo",
        data={"nome_cliente": "Arena Silva", "tipo_envio": "PECA_NOVA"},
    )

    pedido = db.session.scalar(db.select(Pedido))
    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith(f"/painel/pedidos/{pedido.id}")
    assert pedido.nome_cliente == "Arena Silva"
    assert pedido.tipo_envio == TipoEnvio.PECA_NOVA
    assert [e.descricao for e in pedido.eventos] == ["Contrato fechado"]


def test_pedido_sem_nome_nao_e_criado(cliente_logado):
    resposta = cliente_logado.post(
        "/painel/pedidos/novo",
        data={"nome_cliente": "   ", "tipo_envio": "PECA_NOVA"},
    )

    assert resposta.status_code == 200
    assert "Informe o nome do cliente." in pagina(resposta)
    assert db.session.scalar(db.select(db.func.count(Pedido.id))) == 0


def test_detalhe_mostra_o_link_do_cliente(cliente_logado, fabrica_pedido):
    pedido = fabrica_pedido(nome="Arena Silva")

    html = pagina(cliente_logado.get(f"/painel/pedidos/{pedido.id}"))

    assert "Arena Silva" in html
    assert f"/rastreio/{pedido.token}" in html


def test_detalhe_de_pedido_inexistente_devolve_404(cliente_logado):
    assert cliente_logado.get("/painel/pedidos/9999").status_code == 404


# ---------- Ações do pedido ----------


def test_avancar_com_a_etapa_correta(cliente_logado, fabrica_pedido):
    pedido = fabrica_pedido()

    cliente_logado.post(
        f"/painel/pedidos/{pedido.id}/avancar", data={"etapa_atual": "RECEBIDO"}
    )

    assert pedido.status == Status.EM_PREPARACAO


def test_avancar_com_etapa_desatualizada_nao_muda_o_pedido(
    cliente_logado, fabrica_pedido
):
    pedido = fabrica_pedido(status=Status.EM_PREPARACAO)

    resposta = cliente_logado.post(
        f"/painel/pedidos/{pedido.id}/avancar",
        data={"etapa_atual": "RECEBIDO"},
        follow_redirects=True,
    )

    assert "já mudou de etapa" in pagina(resposta)
    assert pedido.status == Status.EM_PREPARACAO


def test_cadastrar_codigo_grava_e_consulta_os_correios(
    cliente_logado, fabrica_pedido, monkeypatch
):
    pedido = fabrica_pedido()
    usar_provedor(monkeypatch, ProvedorFalso({CODIGO: [evento(0, Status.POSTADO)]}))

    resposta = cliente_logado.post(
        f"/painel/pedidos/{pedido.id}/codigo",
        data={"codigo": "aa 000000001 br"},
        follow_redirects=True,
    )

    html = pagina(resposta)
    assert "Código cadastrado." in html
    assert "1 novo(s) evento(s) dos Correios." in html
    assert pedido.codigo_rastreio == CODIGO
    assert pedido.status == Status.POSTADO


def test_codigo_fica_salvo_mesmo_se_a_consulta_falhar(
    cliente_logado, fabrica_pedido, monkeypatch
):
    pedido = fabrica_pedido()
    usar_provedor(monkeypatch, ProvedorFalso({CODIGO: ErroProvedor("API fora do ar")}))

    resposta = cliente_logado.post(
        f"/painel/pedidos/{pedido.id}/codigo",
        data={"codigo": CODIGO},
        follow_redirects=True,
    )

    assert "Não foi possível consultar os Correios" in pagina(resposta)
    assert pedido.codigo_rastreio == CODIGO


def test_codigo_invalido_mostra_o_erro_no_formulario(cliente_logado, fabrica_pedido):
    pedido = fabrica_pedido()

    resposta = cliente_logado.post(
        f"/painel/pedidos/{pedido.id}/codigo", data={"codigo": "123"}
    )

    assert resposta.status_code == 200
    assert "Código inválido" in pagina(resposta)
    assert pedido.codigo_rastreio is None


def test_codigo_duplicado_mostra_aviso(cliente_logado, fabrica_pedido):
    fabrica_pedido(nome="Arena A", codigo=CODIGO)
    outro = fabrica_pedido(nome="Arena B")

    resposta = cliente_logado.post(
        f"/painel/pedidos/{outro.id}/codigo",
        data={"codigo": CODIGO},
        follow_redirects=True,
    )

    assert "já está cadastrado no pedido de Arena A" in pagina(resposta)
    assert outro.codigo_rastreio is None


def test_consultar_sem_codigo_e_recusado(cliente_logado, fabrica_pedido):
    pedido = fabrica_pedido()

    resposta = cliente_logado.post(
        f"/painel/pedidos/{pedido.id}/consultar", follow_redirects=True
    )

    assert "Cadastre o código dos Correios antes de consultar." in pagina(resposta)


def test_consultar_sem_novidade_avisa(cliente_logado, fabrica_pedido, monkeypatch):
    pedido = fabrica_pedido(codigo=CODIGO)
    usar_provedor(monkeypatch, ProvedorFalso({CODIGO: []}))

    resposta = cliente_logado.post(
        f"/painel/pedidos/{pedido.id}/consultar", follow_redirects=True
    )

    assert "Ainda não há novos eventos." in pagina(resposta)


# ---------- CSRF ----------


def test_post_sem_token_csrf_e_recusado(app, cliente_logado, fabrica_pedido):
    pedido = fabrica_pedido()
    app.config["WTF_CSRF_ENABLED"] = True

    resposta = cliente_logado.post(
        f"/painel/pedidos/{pedido.id}/avancar", data={"etapa_atual": "RECEBIDO"}
    )

    assert resposta.status_code == 400
    assert pedido.status == Status.RECEBIDO