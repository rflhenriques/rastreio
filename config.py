import os

from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

SESSION_COOKIE_SAMESITE = "Lax"
REMEMBER_COOKIE_DURATION = timedelta(days=7)
REMEMBER_COOKIE_SAMESITE = "Lax"

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///rastreio.db")
    PROVEDOR_RASTREIO = os.environ.get("PROVEDOR_RASTREIO", "simulado")
    URL_BASE_PUBLICA = os.environ.get("URL_BASE_PUBLICA", "http://127.0.0.1:5000")
    NOME_EMPRESA = os.environ.get("NOME_EMPRESA", "Lance Replay")

class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "chave-de-teste"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False