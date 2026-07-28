"""
infrastructure/db/eventos_repo.py — Central de Auditoria: log de eventos
unificado (quem fez o quê, quando, em qual computador) para o sistema
inteiro — não só Modelos (isso era `modelos_auditoria`, migrada pra cá
uma única vez em database.py). Um mesmo evento serve tanto pra:
  - a tela global de Auditoria (busca com filtros), quanto
  - o histórico de UM objeto específico (ex.: aba Atividade de um modelo),
    que é só esta mesma lista filtrada por entidade_tipo/entidade_id.
"""
from __future__ import annotations
from core.utils import agora_str
from core.constants import VERSAO
from core.maquina import nome_computador
from .database import get_connection


def registrar(db_path: str, tipo: str, operador: str = "",
             entidade_tipo: str = "", entidade_id: str | int = "",
             detalhes: str = "") -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO eventos "
            "(tipo, operador, computador, entidade_tipo, entidade_id, detalhes, versao_app, criado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (tipo, operador, nome_computador(), entidade_tipo, str(entidade_id),
             detalhes, VERSAO, agora_str()))
        conn.commit()
    finally:
        conn.close()


def listar(db_path: str, *, operador: str = "", tipo: str = "", computador: str = "",
          entidade_tipo: str = "", entidade_id: str | int | None = None,
          desde: str = "", termo: str = "", limite: int = 500) -> list[dict]:
    """Busca com filtros pra Central de Auditoria (todos opcionais — sem
    nenhum, lista os mais recentes). `desde` já vem no formato armazenado
    (dd/mm/AAAA) pronto pra comparar como string, já que `criado_em` sempre
    tem essa mesma máscara de largura fixa (comparação lexicográfica só
    funciona por ANO por causa da ordem dd/mm/AAAA — por isso `desde` aqui é
    resolvido pelo chamador a partir de uma data absoluta, ver auditoria_screen).
    """
    condicoes, params = [], []
    if operador:
        condicoes.append("operador = ?")
        params.append(operador)
    if tipo:
        condicoes.append("tipo = ?")
        params.append(tipo)
    if computador:
        condicoes.append("computador = ?")
        params.append(computador)
    if entidade_tipo:
        condicoes.append("entidade_tipo = ?")
        params.append(entidade_tipo)
    if entidade_id is not None:
        condicoes.append("entidade_id = ?")
        params.append(str(entidade_id))
    if termo:
        condicoes.append("(detalhes LIKE ? OR tipo LIKE ? OR operador LIKE ?)")
        params.extend([f"%{termo}%", f"%{termo}%", f"%{termo}%"])

    where = f"WHERE {' AND '.join(condicoes)}" if condicoes else ""
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            f"SELECT * FROM eventos {where} ORDER BY id DESC LIMIT ?",
            (*params, limite)).fetchall()
        resultado = [dict(l) for l in linhas]
    finally:
        conn.close()

    if desde:
        # dd/mm/AAAA -> AAAAmmdd, pra comparar cronologicamente de verdade
        def chave(data_str: str) -> str:
            try:
                d, m, a = data_str.split("/")
                return f"{a}{m}{d}"
            except Exception:
                return "00000000"
        desde_chave = chave(desde)
        resultado = [e for e in resultado if chave(e["criado_em"].split(" ")[0]) >= desde_chave]

    return resultado


def listar_operadores_distintos(db_path: str) -> list[str]:
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT DISTINCT operador FROM eventos WHERE operador != '' ORDER BY operador").fetchall()
        return [l["operador"] for l in linhas]
    finally:
        conn.close()


def listar_computadores_distintos(db_path: str) -> list[str]:
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT DISTINCT computador FROM eventos WHERE computador != '' ORDER BY computador").fetchall()
        return [l["computador"] for l in linhas]
    finally:
        conn.close()


def listar_tipos_distintos(db_path: str) -> list[str]:
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT DISTINCT tipo FROM eventos ORDER BY tipo").fetchall()
        return [l["tipo"] for l in linhas]
    finally:
        conn.close()


def ultimo_evento(db_path: str) -> dict | None:
    conn = get_connection(db_path)
    try:
        linha = conn.execute("SELECT * FROM eventos ORDER BY id DESC LIMIT 1").fetchone()
        return dict(linha) if linha else None
    finally:
        conn.close()
