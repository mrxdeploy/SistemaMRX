from datetime import datetime
import pytz

_tz_br = pytz.timezone('America/Sao_Paulo')

def now_brasilia():
    """Retorna datetime atual no fuso horário de Brasília (naive, sem tzinfo)."""
    return datetime.now(_tz_br).replace(tzinfo=None)
