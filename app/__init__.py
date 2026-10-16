from flask import Flask

from app.extensions import db, login_manager, migrate
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY não definida. Configure o arquivo .env.")
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app import models

    @app.get("/saude")
    def saude():
        return {"status": "ok"}

    return app