from flask import render_template

from app.extensions import db
from app.models import Pedido
from app.publico import bp
from app.servicos.linha_do_tempo import montar_etapas


@bp.after_request
def cabecalhos_de_seguranca(resposta):
    resposta.headers["Cache-Control"] = "no-store"
    resposta.headers["Referrer-Policy"] = "no-referrer"
    resposta.headers["X-Robots-Tag"] = "noindex, nofollow"
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    return resposta


@bp.get("/<token>")
def rastreio(token):
    pedido = db.session.scalar(db.select(Pedido).where(Pedido.token == token))
    if pedido is None:
        return render_template("publico/nao_encontrado.html"), 404

    historico = pedido.historico
    return render_template(
        "publico/rastreio.html",
        pedido=pedido,
        etapas=montar_etapas(pedido),
        historico=historico,
        ultimo=historico[0] if historico else None,
    )