"""
infrastructure/db/auditoria_repo.py — trilha de auditoria de Modelos (quem
criou/editou/removeu, e quando) — nenhuma ferramenta assim existia antes,
toda alteração era silenciosa.
"""
from __future__ import annotations
from core.utils import agora_str
from .database import get_connection


def registrar(db_path: str, modelo_id: int, operador: str, acao: str, detalhes: str = "") -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO modelos_auditoria (modelo_id, operador, acao, detalhes, criado_em) "
            "VALUES (?, ?, ?, ?, ?)",
            (modelo_id, operador, acao, detalhes, agora_str()))
        conn.commit()
    finally:
        conn.close()


def listar_por_modelo(db_path: str, modelo_id: int) -> list[dict]:
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT operador, acao, detalhes, criado_em FROM modelos_auditoria "
            "WHERE modelo_id = ? ORDER BY id DESC", (modelo_id,)).fetchall()
        return [dict(l) for l in linhas]
    finally:
        conn.close()


def listar_recentes(db_path: str, limite: int = 100) -> list[dict]:
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT modelo_id, operador, acao, detalhes, criado_em FROM modelos_auditoria "
            "ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        return [dict(l) for l in linhas]
    finally:
        conn.close()
