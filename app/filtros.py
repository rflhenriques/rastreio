from datetime import timezone
from zoneinfo import ZoneInfo

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


def data_br(momento):
    if momento is None:
        return "—"
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(FUSO_BRASILIA).strftime("%d/%m/%Y %H:%M")


def data_curta(valor):
    return valor.strftime("%d/%m/%Y") if valor else "—"


def registrar_filtros(app):
    app.add_template_filter(data_br, "data_br")
    app.add_template_filter(data_curta, "data_curta")