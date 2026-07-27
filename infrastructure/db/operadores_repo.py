"""
infrastructure/db/operadores_repo.py — CRUD de operadores (login local por
máquina, sem senha — ferramenta interna, acesso já é por posse física do
computador na fábrica).
"""
from __future__ import annotations
from core.exceptions import DBError
from core.utils import agora_str
from .database import get_connection


def listar_operadores(db_path: str, apenas_ativos: bool = True) -> list[str]:
    conn = get_connection(db_path)
    try:
        sql = "SELECT nome FROM operadores"
        if apenas_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome"
        return [l["nome"] for l in conn.execute(sql).fetchall()]
    finally:
        conn.close()


def buscar_por_nome(db_path: str, nome: str) -> int | None:
    conn = get_connection(db_path)
    try:
        linha = conn.execute(
            "SELECT id FROM operadores WHERE nome = ?", (nome,)).fetchone()
        return linha["id"] if linha else None
    finally:
        conn.close()


def inserir_operador(db_path: str, nome: str) -> int:
    """Idempotente — se o nome já existir (mesmo desativado), reativa e retorna o id."""
    conn = get_connection(db_path)
    try:
        existente = conn.execute(
            "SELECT id FROM operadores WHERE nome = ?", (nome,)).fetchone()
        if existente:
            conn.execute("UPDATE operadores SET ativo = 1 WHERE id = ?", (existente["id"],))
            conn.commit()
            return existente["id"]
        cur = conn.execute(
            "INSERT INTO operadores (nome, ativo, criado_em) VALUES (?, 1, ?)",
            (nome, agora_str()))
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        raise DBError(f"Erro ao cadastrar operador '{nome}': {e}")
    finally:
        conn.close()


def remover_operador(db_path: str, operador_id: int) -> None:
    """Desativa (soft delete) — pedidos/auditoria antigos continuam com o nome."""
    conn = get_connection(db_path)
    try:
        conn.execute("UPDATE operadores SET ativo = 0 WHERE id = ?", (operador_id,))
        conn.commit()
    finally:
        conn.close()
