from datetime import timedelta

import pytest

from app.extensions import db
from app.models import Evento, Origem, Status
from app.servicos.linha_do_tempo import montar_etapas
from falsos import BASE


def abrir(client, pedido):
    return client.get(f"/rastreio/{pedido.token}")


def pagina(resposta):
    return resposta.get_data(as_text=True)


def test_pagina_publica_abre_sem_login_e_mostra_o_pedido(client, fabrica_pedido):
    pedido = fabrica_pedido(nome="Arena Silva")

    resposta = abrir(client, pedido)

    html = pagina(resposta)
    assert resposta.status_code == 200
    assert "Arena Silva" in html
    assert "Contrato fechado" in html


def test_nome_do_cliente_e_escapado(client, fabrica_pedido):
    pedido = fabrica_pedido(nome="<script>alert(1)</script>")

    html = pagina(abrir(client, pedido))

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_token_inexistente_devolve_404_generico(client):
    resposta = client.get("/rastreio/token-que-nao-existe")

    assert resposta.status_code == 404
    assert "Link não encontrado" in pagina(resposta)


def test_cabecalhos_de_seguranca_valem_para_pagina_e_para_404(client, fabrica_pedido):
    pedido = fabrica_pedido()

    for caminho in (f"/rastreio/{pedido.token}", "/rastreio/invalido"):
        resposta = client.get(caminho)

        assert resposta.headers["Cache-Control"] == "no-store"
        assert resposta.headers["Referrer-Policy"] == "no-referrer"
        assert "noindex" in resposta.headers["X-Robots-Tag"]


def test_andamento_marca_etapas_concluidas_atual_e_pendentes(client, fabrica_pedido):
    pedido = fabrica_pedido(status=Status.EM_TRANSITO)

    html = pagina(abrir(client, pedido))

    assert html.count("etapa-feita") == 4
    assert html.count("etapa-atual") == 1
    assert html.count("etapa-pendente") == 2


def test_pedido_entregue_mostra_todas_as_etapas_concluidas(client, fabrica_pedido):
    pedido = fabrica_pedido(status=Status.ENTREGUE)

    html = pagina(abrir(client, pedido))

    assert html.count("etapa-feita") == 7
    assert "etapa-atual" not in html


def test_historico_publico_mostra_o_mais_recente_primeiro(client, fabrica_pedido):
    pedido = fabrica_pedido()
    pedido.eventos.append(
        Evento(origem=Origem.CORREIOS, descricao="Evento antigo ABC", ocorrido_em=BASE)
    )
    pedido.eventos.append(
        Evento(
            origem=Origem.CORREIOS,
            descricao="Evento recente XYZ",
            ocorrido_em=BASE + timedelta(hours=1),
        )
    )
    db.session.commit()

    html = pagina(abrir(client, pedido))

    assert html.index("Evento recente XYZ") < html.index("Evento antigo ABC")


def test_pagina_traz_codigo_e_ultima_atualizacao(client, fabrica_pedido):
    pedido = fabrica_pedido(codigo="AA000000001BR")

    html = pagina(abrir(client, pedido))

    assert "AA000000001BR" in html
    assert "Última atualização" in html


def test_pagina_traz_a_marca_e_a_imagem_de_compartilhamento(client, fabrica_pedido):
    pedido = fabrica_pedido()

    html = pagina(abrir(client, pedido))

    assert "Lance Replay" in html
    assert 'property="og:image"' in html
    assert "/static/img/og.png" in html


@pytest.mark.parametrize(
    "status, feitas, atuais, pendentes",
    [
        (Status.RECEBIDO, 0, 1, 6),
        (Status.EM_TRANSITO, 4, 1, 2),
        (Status.ENTREGUE, 7, 0, 0),
    ],
)
def test_montar_etapas(fabrica_pedido, status, feitas, atuais, pendentes):
    etapas = montar_etapas(fabrica_pedido(status=status))
    estados = [etapa.estado for etapa in etapas]

    assert len(etapas) == 7
    assert etapas[0].rotulo == "Contrato fechado"
    assert estados.count("feita") == feitas
    assert estados.count("atual") == atuais
    assert estados.count("pendente") == pendentes

def test_historico_publico_coloca_os_correios_acima_dos_eventos_internos(
    client, fabrica_pedido
):
    pedido = fabrica_pedido()
    pedido.eventos.append(
        Evento(origem=Origem.CORREIOS, descricao="Evento dos Correios XYZ", ocorrido_em=BASE)
    )
    db.session.commit()

    html = pagina(abrir(client, pedido))
    historico = html.split("<h2>Histórico</h2>")[1]

    assert historico.index("Evento dos Correios XYZ") < historico.index("Contrato fechado")