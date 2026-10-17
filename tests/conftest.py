import pytest

from app import create_app
from app.extensions import db as _db
from app.models import TipoEnvio
from app.servicos.pedidos import criar_pedido
from config import TestConfig


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


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