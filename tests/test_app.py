import pytest

from app import create_app
from config import TestConfig


def test_rota_de_saude_responde_ok(client):
    resposta = client.get("/saude")

    assert resposta.status_code == 200
    assert resposta.get_json() == {"status": "ok"}


def test_app_se_recusa_a_subir_sem_secret_key():
    class SemChave(TestConfig):
        SECRET_KEY = None

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(SemChave)