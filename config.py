import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///rastreio.db")
    PROVEDOR_RASTREIO = os.environ.get("PROVEDOR_RASTREIO", "simulado")
    URL_BASE_PUBLICA = os.environ.get("URL_BASE_PUBLICA", "http://127.0.0.1:5000")
    NOME_EMPRESA = os.environ.get("NOME_EMPRESA", "Lance Replay")

    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_SAMESITE = "Lax"

    CORREIOS_AMBIENTE = os.environ.get("CORREIOS_AMBIENTE", "producao")
    CORREIOS_CHAVE_ACESSO = os.environ.get("CORREIOS_CHAVE_ACESSO")
    CORREIOS_USUARIO = os.environ.get("CORREIOS_USUARIO")
    CORREIOS_CODIGO_ACESSO = os.environ.get("CORREIOS_CODIGO_ACESSO")
    CORREIOS_CARTAO_POSTAGEM = os.environ.get("CORREIOS_CARTAO_POSTAGEM")
    CORREIOS_TIMEOUT = int(os.environ.get("CORREIOS_TIMEOUT", "15"))


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "chave-de-teste"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False