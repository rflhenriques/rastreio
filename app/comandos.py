import click
from flask import current_app

from app.provedores import obter_provedor
from app.servicos.atualizador import atualizar_todos


def registrar_comandos(app):
    @app.cli.command("atualizar-rastreios")
    def atualizar_rastreios():
        """Consulta o provedor e atualiza os pedidos em andamento."""
        provedor = obter_provedor(current_app.config["PROVEDOR_RASTREIO"])
        resumo = atualizar_todos(provedor)
        click.echo(
            f"Pedidos consultados: {resumo.pedidos} | "
            f"Eventos novos: {resumo.eventos_novos} | "
            f"Erros: {resumo.erros}"
        )