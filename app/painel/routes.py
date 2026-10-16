from urllib.parse import urlsplit

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import Usuario
from app.painel import bp
from app.painel.forms import LoginForm


def _destino_seguro(destino):
    if not destino or "\\" in destino:
        return False
    partes = urlsplit(destino)
    return (
        not partes.scheme
        and not partes.netloc
        and destino.startswith("/")
        and not destino.startswith("//")
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("painel.inicio"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        usuario = db.session.scalar(db.select(Usuario).where(Usuario.email == email))

        if usuario is None or not usuario.verificar_senha(form.senha.data):
            flash("E-mail ou senha incorretos.", "erro")
        else:
            login_user(usuario, remember=form.lembrar.data)
            destino = request.args.get("next")
            if _destino_seguro(destino):
                return redirect(destino)
            return redirect(url_for("painel.inicio"))

    return render_template("painel/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do painel.", "sucesso")
    return redirect(url_for("painel.login"))


@bp.get("/")
@login_required
def inicio():
    return render_template("painel/inicio.html")