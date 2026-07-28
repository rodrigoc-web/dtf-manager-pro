"""
core/utils.py — Funções utilitárias sem dependência de camada específica.
"""
from __future__ import annotations
import datetime


def formatar_lote_id(numero: int) -> str:
    """DTF_000001, DTF_000002, ..."""
    return f"DTF_{numero:06d}"


def agora_str() -> str:
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")


def data_hoje() -> str:
    return datetime.date.today().strftime("%d/%m/%Y")


def timestamp_arquivo() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def cm_para_px(cm: float, dpi: int = 300) -> int:
    """Converte centímetros em pixels a uma dada resolução."""
    return round(cm * dpi / 2.54)


def px_para_cm(px: int, dpi: int = 300) -> float:
    """Converte pixels em centímetros."""
    return round(px * 2.54 / dpi, 2)


def truncar(texto: str, max_len: int, sufixo: str = "...") -> str:
    """Trunca texto longo para exibição em tabelas e logs."""
    if len(texto) <= max_len:
        return texto
    return texto[:max_len - len(sufixo)] + sufixo


def normalizar_nome(nome: str) -> str:
    """Normaliza nome do jogador: strip + upper."""
    return nome.strip().upper()


def tempo_relativo(data_str: str) -> str:
    """"27/07/2026 14:03" -> "há 2 minutos" / "há 3h" / "27/07" (mesmo
    formato de `agora_str()`) — usado no card "Última atividade" do
    Dashboard, pra ficar óbvio o quão recente é sem precisar ler a hora."""
    try:
        quando = datetime.datetime.strptime(data_str, "%d/%m/%Y %H:%M")
    except ValueError:
        return data_str
    delta = datetime.datetime.now() - quando
    segundos = delta.total_seconds()
    if segundos < 0:
        return "agora"
    if segundos < 60:
        return "agora mesmo"
    if segundos < 3600:
        minutos = int(segundos // 60)
        return f"há {minutos} minuto{'s' if minutos != 1 else ''}"
    if segundos < 86400 and quando.date() == datetime.date.today():
        horas = int(segundos // 3600)
        return f"há {horas}h"
    if quando.date() == datetime.date.today() - datetime.timedelta(days=1):
        return f"ontem, {quando.strftime('%H:%M')}"
    return quando.strftime("%d/%m, %H:%M")
