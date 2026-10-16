from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    EmailField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Email, Length, Regexp

from app.models import ROTULOS_TIPO
from app.servicos.pedidos import PADRAO_CODIGO


class LoginForm(FlaskForm):
    email = EmailField(
        "E-mail",
        validators=[DataRequired("Informe o e-mail."), Email("E-mail inválido.")],
    )
    senha = PasswordField("Senha", validators=[DataRequired("Informe a senha.")])
    lembrar = BooleanField("Manter conectado")
    enviar = SubmitField("Entrar")


class PedidoForm(FlaskForm):
    nome_cliente = StringField(
        "Nome do cliente",
        validators=[
            DataRequired("Informe o nome do cliente."),
            Length(max=150, message="Use no máximo 150 caracteres."),
        ],
    )
    tipo_envio = SelectField(
        "Tipo de envio",
        choices=[(tipo.name, rotulo) for tipo, rotulo in ROTULOS_TIPO.items()],
    )
    enviar = SubmitField("Criar pedido")

def _normalizar_codigo(valor):
    return valor.replace(" ", "").upper() if valor else valor


class CodigoForm(FlaskForm):
    codigo = StringField(
        "Código de rastreio dos Correios",
        filters=[_normalizar_codigo],
        validators=[
            DataRequired("Informe o código."),
            Regexp(
                PADRAO_CODIGO,
                message="Código inválido. Use 2 letras, 9 números e 2 letras "
                "(exemplo: AA123456789BR).",
            ),
        ],
    )
    enviar = SubmitField("Salvar código")