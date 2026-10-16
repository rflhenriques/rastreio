from urllib.parse import urlsplit

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import Pedido, TipoEnvio, Usuario
from app.painel import bp
from app.painel.forms import LoginForm, PedidoForm
from app.servicos.mensagens import link_publico, montar_mensagem_whatsapp


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
    consulta = db.select(Pedido).order_by(Pedido.criado_em.desc())
    pedidos = db.session.scalars(consulta).all()
    return render_template("painel/inicio.html", pedidos=pedidos)


@bp.route("/pedidos/novo", methods=["GET", "POST"])
@login_required
def novo_pedido():
    form = PedidoForm()
    if form.validate_on_submit():
        pedido = Pedido(
            nome_cliente=form.nome_cliente.data.strip(),
            tipo_envio=TipoEnvio[form.tipo_envio.data],
        )
        db.session.add(pedido)
        db.session.commit()
        flash("Pedido criado. Copie a mensagem abaixo e envie ao cliente.", "sucesso")
        return redirect(url_for("painel.detalhe_pedido", pedido_id=pedido.id))
    return render_template("painel/novo_pedido.html", form=form)


@bp.get("/pedidos/<int:pedido_id>")
@login_required
def detalhe_pedido(pedido_id):
    pedido = db.get_or_404(Pedido, pedido_id)
    return render_template(
        "painel/detalhe_pedido.html",
        pedido=pedido,
        link=link_publico(pedido),
        mensagem=montar_mensagem_whatsapp(pedido),
    )