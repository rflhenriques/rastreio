from flask import Flask

from app.extensions import csrf, db, login_manager, migrate
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY não definida. Configure o arquivo .env.")
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app import models  # noqa: F401

    from app.comandos import registrar_comandos

    registrar_comandos(app)

    from app.filtros import registrar_filtros

    registrar_filtros(app)

    @app.context_processor
    def dados_da_marca():
        base = app.config["URL_BASE_PUBLICA"].rstrip("/")
        return {
            "marca": {
                "nome": app.config["NOME_EMPRESA"],
                "imagem_compartilhamento": f"{base}/static/img/og.png",
            }
        }

    from app.painel import bp as painel_bp

    app.register_blueprint(painel_bp)

    from app.publico import bp as publico_bp

    app.register_blueprint(publico_bp)
    
    csrf.init_app(app)

    @app.get("/saude")
    def saude():
        return {"status": "ok"}

    return app