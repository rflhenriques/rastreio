import json
from pathlib import Path

import click
from flask import current_app

from app.extensions import db
from app.filtros import FUSO_BRASILIA
from app.models import Usuario
from app.provedores import ErroProvedor, obter_provedor
from app.provedores.correios_cliente import criar_cliente_correios
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

    @app.cli.command("testar-correios")
    @click.argument("codigo", required=False)
    @click.option(
        "--salvar",
        is_flag=True,
        help="Salva a resposta bruta em instance/resposta_correios.json",
    )
    def testar_correios(codigo, salvar):
        """Testa a conexão com os Correios. Não grava nada no banco."""
        try:
            cliente = criar_cliente_correios(current_app.config)

            if cliente.usa_chave_de_acesso:
                click.echo(
                    f"Modo: chave de acesso {cliente.chave_mascarada} "
                    f"({cliente.tamanho_da_chave} caracteres). Ambiente: {cliente.ambiente}"
                )
            else:
                cliente.gerar_token()
                validade = cliente.token_expira_em.astimezone(FUSO_BRASILIA)
                click.echo(f"Token gerado. Ambiente: {cliente.info_token.get('ambiente')}")
                click.echo(f"Válido até (Brasília): {validade:%d/%m/%Y %H:%M}")
                click.echo(f"APIs liberadas (ids): {cliente.info_token.get('apis')}")

            if not codigo:
                click.echo(
                    "Configuração lida. Rode de novo com um código de rastreio "
                    "para validar de verdade."
                )
                return

            dados = cliente.consultar_objeto(codigo.strip().upper())
        except ErroProvedor as erro:
            raise click.ClickException(str(erro))

        corpo = dados if isinstance(dados, dict) else {}
        objetos = corpo.get("objetos") or []
        objeto = objetos[0] if objetos else {}
        eventos = objeto.get("eventos") or []

        click.echo(f"Objeto: {objeto.get('codObjeto', codigo)}")
        if objeto.get("mensagem"):
            click.echo(f"Mensagem dos Correios: {objeto['mensagem']}")
        click.echo(f"Eventos: {len(eventos)}")
        for evento in eventos[:5]:
            click.echo(
                f"  {evento.get('dtHrCriado')} | {evento.get('codigo')} | "
                f"{evento.get('descricao')}"
            )
        click.echo(f"Data prevista de entrega (dtPrevista): {objeto.get('dtPrevista')}")

        if salvar:
            caminho = Path(current_app.instance_path) / "resposta_correios.json"
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text(
                json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            click.echo(f"Resposta salva em {caminho}")