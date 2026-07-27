"""
infrastructure/db/lotes_repo.py — Contador de lotes. Substitui contador.json
do DTF MANAGER original. O "quem produziu" agora vive em Pedido.operador
(definido na criação do pedido, não mais por lote) — ver pedidos_repo.py.
"""
from __future__ import annotations
from core.utils import formatar_lote_id, agora_str
from core.exceptions import DBError
from .database import get_connection


def proximo_lote(db_path: str) -> tuple[int, str]:
    """Incrementa o contador e retorna (numero, 'DTF_000001')."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute("SELECT valor FROM contador WHERE chave = 'ultimo_lote'")
        linha = cur.fetchone()
        ultimo = linha["valor"] if linha else 0
        proximo = ultimo + 1
        conn.execute(
            "UPDATE contador SET valor = ? WHERE chave = 'ultimo_lote'", (proximo,))
        lote_id = formatar_lote_id(proximo)
        conn.execute(
            "INSERT INTO lotes (id, numero, criado_em) VALUES (?, ?, ?)",
            (lote_id, proximo, agora_str()))
        conn.commit()
        return proximo, lote_id
    except Exception as e:
        raise DBError(f"Erro ao gerar próximo lote: {e}")
    finally:
        conn.close()


def ultimo_lote_numero(db_path: str) -> int:
    conn = get_connection(db_path)
    try:
        linha = conn.execute(
            "SELECT valor FROM contador WHERE chave = 'ultimo_lote'").fetchone()
        return linha["valor"] if linha else 0
    finally:
        conn.close()
