from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email


class LoginForm(FlaskForm):
    email = EmailField(
        "E-mail",
        validators=[DataRequired("Informe o e-mail."), Email("E-mail inválido.")],
    )
    senha = PasswordField("Senha", validators=[DataRequired("Informe a senha.")])
    lembrar = BooleanField("Manter conectado")
    enviar = SubmitField("Entrar")