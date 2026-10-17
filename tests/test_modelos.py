from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Evento, Origem, Status, TipoEnvio, Usuario, rotulo_do_status


def test_token_e_gerado_automaticamente_e_e_unico(fabrica_pedido):
    a = fabrica_pedido(nome="A")
    b = fabrica_pedido(nome="B")

    assert len(a.token) >= 32
    assert a.token != b.token


@pytest.mark.parametrize(
    "tipo, status, esperado",
    [
        (TipoEnvio.PECA_NOVA, Status.RECEBIDO, "Contrato fechado"),
        (TipoEnvio.REPOSICAO, Status.RECEBIDO, "Pedido recebido"),
        (TipoEnvio.REPOSICAO, Status.EM_TRANSITO, "Em trânsito"),
        (TipoEnvio.PECA_NOVA, Status.ENTREGUE, "Entregue"),
    ],
)
def test_rotulo_do_status(tipo, status, esperado):
    assert rotulo_do_status(status, tipo) == esperado


def test_historico_vai_do_mais_recente_para_o_mais_antigo(fabrica_pedido):
    pedido = fabrica_pedido()
    base = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    for minutos, texto in [(10, "segundo"), (0, "primeiro"), (20, "terceiro")]:
        pedido.eventos.append(
            Evento(
                origem=Origem.CORREIOS,
                descricao=texto,
                ocorrido_em=base + timedelta(minutes=minutos),
            )
        )
    db.session.commit()

    textos = [e.descricao for e in pedido.historico if e.origem == Origem.CORREIOS]

    assert textos == ["terceiro", "segundo", "primeiro"]


def test_historico_desempata_eventos_simultaneos_pelo_id(fabrica_pedido):
    pedido = fabrica_pedido()
    momento = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    for texto in ("primeiro", "segundo"):
        pedido.eventos.append(
            Evento(origem=Origem.CORREIOS, descricao=texto, ocorrido_em=momento)
        )
    db.session.commit()

    textos = [e.descricao for e in pedido.historico if e.origem == Origem.CORREIOS]

    assert textos == ["segundo", "primeiro"]


def test_banco_recusa_evento_duplicado(fabrica_pedido):
    pedido = fabrica_pedido()
    momento = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    for _ in range(2):
        pedido.eventos.append(
            Evento(origem=Origem.CORREIOS, descricao="Objeto postado", ocorrido_em=momento)
        )

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_senha_e_guardada_como_hash():
    usuario = Usuario(nome="Teste", email="teste@exemplo.com")
    usuario.definir_senha("segredo-123")

    assert "segredo-123" not in usuario.senha_hash
    assert usuario.verificar_senha("segredo-123")
    assert not usuario.verificar_senha("outra-senha")