from urllib.parse import urlsplit

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import Pedido, TipoEnvio, Usuario
from app.painel import bp
from app.painel.forms import CodigoForm, LoginForm, PedidoForm
from app.provedores import ErroProvedor, obter_provedor
from app.servicos.atualizador import atualizar_pedido
from app.servicos.mensagens import link_publico, montar_mensagem_whatsapp
from app.servicos.pedidos import (
    ErroDeRegra,
    avancar_etapa,
    cadastrar_codigo,
    criar_pedido,
    proxima_etapa_interna,
)


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
        pedido = criar_pedido(
            nome_cliente=form.nome_cliente.data.strip(),
            tipo_envio=TipoEnvio[form.tipo_envio.data],
        )
        db.session.commit()
        flash("Pedido criado. Copie a mensagem abaixo e envie ao cliente.", "sucesso")
        return redirect(url_for("painel.detalhe_pedido", pedido_id=pedido.id))
    return render_template("painel/novo_pedido.html", form=form)


def _pagina_detalhe(pedido, form_codigo):
    return render_template(
        "painel/detalhe_pedido.html",
        pedido=pedido,
        form_codigo=form_codigo,
        proxima_etapa=proxima_etapa_interna(pedido),
        link=link_publico(pedido),
        mensagem=montar_mensagem_whatsapp(pedido),
    )


def _voltar_ao_detalhe(pedido_id):
    return redirect(url_for("painel.detalhe_pedido", pedido_id=pedido_id))


def _consultar_correios(pedido):
    provedor = obter_provedor(current_app.config["PROVEDOR_RASTREIO"])
    try:
        novos = atualizar_pedido(pedido, provedor)
        db.session.commit()
    except ErroProvedor as erro:
        db.session.rollback()
        flash(f"Não foi possível consultar os Correios agora: {erro}", "erro")
        return

    if novos:
        flash(f"{novos} novo(s) evento(s) dos Correios.", "sucesso")
    else:
        flash("Consulta feita. Ainda não há novos eventos.", "aviso")


@bp.get("/pedidos/<int:pedido_id>")
@login_required
def detalhe_pedido(pedido_id):
    pedido = db.get_or_404(Pedido, pedido_id)
    return _pagina_detalhe(pedido, CodigoForm(codigo=pedido.codigo_rastreio))


@bp.post("/pedidos/<int:pedido_id>/avancar")
@login_required
def avancar_pedido(pedido_id):
    pedido = db.get_or_404(Pedido, pedido_id)
    try:
        avancar_etapa(pedido, request.form.get("etapa_atual"))
        db.session.commit()
        flash(f"Pedido avançado para: {pedido.rotulo_status}.", "sucesso")
    except ErroDeRegra as erro:
        db.session.rollback()
        flash(str(erro), "erro")
    return _voltar_ao_detalhe(pedido_id)


@bp.post("/pedidos/<int:pedido_id>/codigo")
@login_required
def cadastrar_codigo_pedido(pedido_id):
    pedido = db.get_or_404(Pedido, pedido_id)
    form = CodigoForm()
    if not form.validate_on_submit():
        return _pagina_detalhe(pedido, form)

    try:
        cadastrar_codigo(pedido, form.codigo.data)
        db.session.commit()
    except ErroDeRegra as erro:
        db.session.rollback()
        flash(str(erro), "erro")
        return _voltar_ao_detalhe(pedido_id)

    flash("Código cadastrado.", "sucesso")
    _consultar_correios(pedido)
    return _voltar_ao_detalhe(pedido_id)


@bp.post("/pedidos/<int:pedido_id>/consultar")
@login_required
def consultar_pedido(pedido_id):
    pedido = db.get_or_404(Pedido, pedido_id)
    if not pedido.codigo_rastreio:
        flash("Cadastre o código dos Correios antes de consultar.", "erro")
    else:
        _consultar_correios(pedido)
    return _voltar_ao_detalhe(pedido_id)