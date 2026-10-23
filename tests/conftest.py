import pytest

from app import create_app
from app.extensions import db as _db
from app.models import TipoEnvio, Usuario
from app.servicos.pedidos import criar_pedido
from config import TestConfig
from falsos import EMAIL, SENHA


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()
        _db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def fabrica_pedido(app):
    def criar(nome="Cliente Teste", tipo=TipoEnvio.PECA_NOVA, status=None, codigo=None):
        pedido = criar_pedido(nome, tipo)
        if status is not None:
            pedido.status = status
        if codigo is not None:
            pedido.codigo_rastreio = codigo
        _db.session.commit()
        return pedido

    return criar


@pytest.fixture()
def usuario(app):
    usuario = Usuario(nome="Teste", email=EMAIL)
    usuario.definir_senha(SENHA)
    _db.session.add(usuario)
    _db.session.commit()
    return usuario


@pytest.fixture()
def cliente_logado(client, usuario):
    resposta = client.post("/painel/login", data={"email": EMAIL, "senha": SENHA})
    assert resposta.status_code == 302
    return client