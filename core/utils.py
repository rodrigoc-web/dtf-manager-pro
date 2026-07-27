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
