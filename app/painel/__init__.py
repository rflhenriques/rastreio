from flask import Blueprint

bp = Blueprint("painel", __name__, url_prefix="/painel")

from app.painel import routes  # noqa: E402,F401