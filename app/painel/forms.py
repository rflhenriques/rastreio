from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    EmailField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Email, Length

from app.models import ROTULOS_TIPO


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