from app.extensions import db
from app.models import Usuario


def invocar(app, *argumentos):
    return app.test_cli_runner().invoke(args=list(argumentos))


def criar_usuario(app, senha="senha-segura-123", email="MARIA@Exemplo.com"):
    return invocar(
        app, "criar-usuario", "--nome", "Maria", "--email", email, "--senha", senha
    )


def test_criar_usuario_normaliza_o_email_e_guarda_hash(app):
    resultado = criar_usuario(app)

    assert resultado.exit_code == 0
    usuario = db.session.scalar(db.select(Usuario))
    assert usuario.email == "maria@exemplo.com"
    assert usuario.verificar_senha("senha-segura-123")


def test_criar_usuario_recusa_senha_curta(app):
    resultado = criar_usuario(app, senha="curta")

    assert resultado.exit_code == 1
    assert "pelo menos 8 caracteres" in resultado.output
    assert db.session.scalar(db.select(db.func.count(Usuario.id))) == 0


def test_criar_usuario_recusa_email_repetido(app):
    criar_usuario(app)

    resultado = criar_usuario(app)

    assert resultado.exit_code == 1
    assert "Já existe um usuário" in resultado.output


def test_atualizar_rastreios_sem_pedidos(app):
    resultado = invocar(app, "atualizar-rastreios")

    assert resultado.exit_code == 0
    assert "Pedidos consultados: 0 | Eventos novos: 0 | Erros: 0" in resultado.output


def test_atualizar_rastreios_com_provedor_desconhecido(app):
    app.config["PROVEDOR_RASTREIO"] = "xyz"

    resultado = invocar(app, "atualizar-rastreios")

    assert resultado.exit_code == 1
    assert "desconhecido" in resultado.output