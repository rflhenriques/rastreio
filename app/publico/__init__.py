from flask import Blueprint

bp = Blueprint("publico", __name__, url_prefix="/rastreio")

from app.publico import routes  # noqa: E402,F401