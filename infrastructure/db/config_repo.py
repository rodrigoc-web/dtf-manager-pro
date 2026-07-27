"""
infrastructure/db/config_repo.py — chave/valor de configurações editáveis
pelo usuário (meta diária, estoque de rolo, último operador etc.), no mesmo
formato simples da tabela `contador` já existente.
"""
from __future__ import annotations
from .database import get_connection


def obter(db_path: str, chave: str, padrao: str = "") -> str:
    conn = get_connection(db_path)
    try:
        linha = conn.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?", (chave,)).fetchone()
        return linha["valor"] if linha else padrao
    finally:
        conn.close()


def obter_int(db_path: str, chave: str, padrao: int = 0) -> int:
    valor = obter(db_path, chave, "")
    try:
        return int(valor)
    except ValueError:
        return padrao


def obter_float(db_path: str, chave: str, padrao: float = 0.0) -> float:
    valor = obter(db_path, chave, "")
    try:
        return float(valor)
    except ValueError:
        return padrao


def definir(db_path: str, chave: str, valor: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO configuracoes (chave, valor) VALUES (?, ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
            (chave, str(valor)))
        conn.commit()
    finally:
        conn.close()
