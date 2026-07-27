"""
infrastructure/db/estoque_repo.py — controle de estoque do rolo de filme DTF.
Estoque atual = soma de `metros` em estoque_rolo_movimentos (positivo para
reabastecimento, negativo para baixa por produção) — sem contador separado
pra não correr risco de dessincronizar do histórico.
"""
from __future__ import annotations
from core.utils import agora_str
from . import config_repo
from .database import get_connection

_CHAVE_ALERTA = "estoque_alerta_metros"
_ALERTA_PADRAO = 20.0


def estoque_atual_metros(db_path: str) -> float:
    conn = get_connection(db_path)
    try:
        linha = conn.execute(
            "SELECT COALESCE(SUM(metros), 0) AS total FROM estoque_rolo_movimentos").fetchone()
        return round(linha["total"], 2)
    finally:
        conn.close()


def registrar_reabastecimento(db_path: str, metros: float, motivo: str = "") -> None:
    _registrar(db_path, "REABASTECIMENTO", abs(metros), motivo)


def registrar_baixa(db_path: str, metros: float, motivo: str = "") -> None:
    _registrar(db_path, "BAIXA", -abs(metros), motivo)


def _registrar(db_path: str, tipo: str, metros: float, motivo: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO estoque_rolo_movimentos (tipo, metros, motivo, criado_em) "
            "VALUES (?, ?, ?, ?)",
            (tipo, metros, motivo, agora_str()))
        conn.commit()
    finally:
        conn.close()


def listar_movimentos(db_path: str, limite: int = 50) -> list[dict]:
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT tipo, metros, motivo, criado_em FROM estoque_rolo_movimentos "
            "ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        return [dict(l) for l in linhas]
    finally:
        conn.close()


def limite_alerta_metros(db_path: str) -> float:
    return config_repo.obter_float(db_path, _CHAVE_ALERTA, _ALERTA_PADRAO)


def definir_limite_alerta(db_path: str, metros: float) -> None:
    config_repo.definir(db_path, _CHAVE_ALERTA, str(metros))
