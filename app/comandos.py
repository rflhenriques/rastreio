import click
from flask import current_app

from app.extensions import db
from app.models import Usuario
from app.provedores import obter_provedor
from app.servicos.atualizador import atualizar_todos


def registrar_comandos(app):
    @app.cli.command("atualizar-rastreios")
    def atualizar_rastreios():
        """Consulta o provedor e atualiza os pedidos em andamento."""
        try:
            provedor = obter_provedor(current_app.config["PROVEDOR_RASTREIO"])
        except ValueError as erro:
            raise click.ClickException(str(erro))

        resumo = atualizar_todos(provedor)
        click.echo(
            f"Pedidos consultados: {resumo.pedidos} | "
            f"Eventos novos: {resumo.eventos_novos} | "
            f"Erros: {resumo.erros}"
        )

    @app.cli.command("criar-usuario")
    @click.option("--nome", prompt="Nome")
    @click.option("--email", prompt="E-mail")
    @click.password_option(
        "--senha", prompt="Senha", confirmation_prompt="Confirme a senha"
    )
    def criar_usuario(nome, email, senha):
        """Cria um usuário do painel."""
        email = email.strip().lower()

        if len(senha) < 8:
            raise click.ClickException("A senha precisa ter pelo menos 8 caracteres.")

        existente = db.session.scalar(db.select(Usuario).where(Usuario.email == email))
        if existente:
            raise click.ClickException("Já existe um usuário com esse e-mail.")

        usuario = Usuario(nome=nome.strip(), email=email)
        usuario.definir_senha(senha)
        db.session.add(usuario)
        db.session.commit()
        click.echo(f"Usuário {usuario.email} criado.")