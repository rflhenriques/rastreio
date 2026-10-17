import enum
import secrets
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class TipoEnvio(enum.Enum):
    PECA_NOVA = "peca_nova"
    REPOSICAO = "reposicao"


class Status(enum.Enum):
    RECEBIDO = "recebido"
    EM_PREPARACAO = "em_preparacao"
    PRONTO_POSTAGEM = "pronto_postagem"
    POSTADO = "postado"
    EM_TRANSITO = "em_transito"
    SAIU_ENTREGA = "saiu_entrega"
    ENTREGUE = "entregue"


class Origem(enum.Enum):
    INTERNA = "interna"
    CORREIOS = "correios"

def agora_utc():
    return datetime.now(timezone.utc)

def _como_utc(momento):
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def gerar_token():
    return secrets.token_urlsafe(24)


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @login_manager.user_loader
    def carregar_usuario(user_id):
        return db.session.get(Usuario, int(user_id))

ROTULOS_STATUS = {
    Status.EM_PREPARACAO: "Em preparação",
    Status.PRONTO_POSTAGEM: "Pronto para postagem",
    Status.POSTADO: "Objeto postado",
    Status.EM_TRANSITO: "Em trânsito",
    Status.SAIU_ENTREGA: "Saiu para entrega",
    Status.ENTREGUE: "Entregue",
}

def rotulo_do_status(status, tipo_envio):
    if status == Status.RECEBIDO:
        if tipo_envio == TipoEnvio.PECA_NOVA:
            return "Contrato fechado"
        return "Pedido recebido"
    return ROTULOS_STATUS[status]

ROTULOS_TIPO = {
    TipoEnvio.PECA_NOVA: "Peça nova",
    TipoEnvio.REPOSICAO: "Reposição",
}

class Pedido(db.Model):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=gerar_token
    )
    tipo_envio: Mapped[TipoEnvio] = mapped_column(Enum(TipoEnvio, native_enum=False))
    nome_cliente: Mapped[str] = mapped_column(String(150))
    codigo_rastreio: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[Status] = mapped_column(
        Enum(Status, native_enum=False), default=Status.RECEBIDO, index=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora_utc
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora_utc, onupdate=agora_utc
    )

    eventos: Mapped[list["Evento"]] = relationship(
        back_populates="pedido",
        cascade="all, delete-orphan",
        order_by="Evento.ocorrido_em",
    )

    @property
    def rotulo_status(self):
        if self.status == Status.RECEBIDO:
            if self.tipo_envio == TipoEnvio.PECA_NOVA:
                return "Contrato fechado"
            return "Pedido recebido"
        return ROTULOS_STATUS[self.status]

    @property
    def rotulo_tipo(self):
        return ROTULOS_TIPO[self.tipo_envio]

    @property
    def rotulo_status(self):
        if self.status == Status.RECEBIDO:
            if self.tipo_envio == TipoEnvio.PECA_NOVA:
                return "Contrato fechado"
            return "Pedido recebido"
        return ROTULOS_STATUS[self.status]

    @property
    def rotulo_tipo(self):
        return ROTULOS_TIPO[self.tipo_envio]

    @property
    def tem_eventos_correios(self):
        return any(evento.origem == Origem.CORREIOS for evento in self.eventos)

    @property
    def entregue(self):
        return self.status == Status.ENTREGUE

    @property
    def rotulo_status(self):
        return rotulo_do_status(self.status, self.tipo_envio)

    @property
    def rotulo_tipo(self):
        return ROTULOS_TIPO[self.tipo_envio]

    @property
    def tem_eventos_correios(self):
        return any(evento.origem == Origem.CORREIOS for evento in self.eventos)

    @property
    def entregue(self):
        return self.status == Status.ENTREGUE

    @property
    def historico(self):
        return sorted(
            self.eventos,
            key=lambda evento: (_como_utc(evento.ocorrido_em), evento.id or 0),
            reverse=True,
        )

class Evento(db.Model):
    __tablename__ = "eventos"
    __table_args__ = (
        UniqueConstraint(
            "pedido_id", "origem", "ocorrido_em", "descricao", name="uq_evento_unico"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), index=True)
    origem: Mapped[Origem] = mapped_column(Enum(Origem, native_enum=False))
    descricao: Mapped[str] = mapped_column(String(255))
    local: Mapped[str | None] = mapped_column(String(150))
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    pedido: Mapped["Pedido"] = relationship(back_populates="eventos")