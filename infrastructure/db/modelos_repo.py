"""
infrastructure/db/modelos_repo.py — CRUD de modelos (Profissões e Times cadastrados).
"""
from __future__ import annotations
import json
from domain.models import Modelo, Camada
from domain.enums import TipoModelo
from core.exceptions import DBError
from core.utils import agora_str
from .database import get_connection


def _linha_para_modelo(linha) -> Modelo:
    # .get com default cobre modelos cadastrados antes de "campo"/"vertical"
    # existirem (Rodada 1 — todas as camadas eram implicitamente telefone).
    camadas = [
        Camada(nome=c["nome"], campo=c.get("campo", "telefone"),
               x=c["x"], y=c["y"], w=c["w"], h=c["h"],
               vertical=c.get("vertical", False))
        for c in json.loads(linha["camadas_json"])
    ]
    return Modelo(
        id=linha["id"],
        profissao=linha["profissao"],
        psd_path=linha["psd_path"],
        canvas_w=linha["canvas_w"],
        canvas_h=linha["canvas_h"],
        text_color=(linha["cor_r"], linha["cor_g"], linha["cor_b"], linha["cor_a"]),
        tipo=TipoModelo(linha["tipo"] if "tipo" in linha.keys() else "PROFISSAO"),
        grupo=linha["grupo"] if "grupo" in linha.keys() else "",
        camadas=camadas,
        ativo=bool(linha["ativo"]),
        criado_em=linha["criado_em"] if "criado_em" in linha.keys() else "",
    )


def _camadas_json(modelo: Modelo) -> str:
    return json.dumps([
        {"nome": c.nome, "campo": c.campo, "x": c.x, "y": c.y,
         "w": c.w, "h": c.h, "vertical": c.vertical}
        for c in modelo.camadas
    ])


def inserir_modelo(db_path: str, modelo: Modelo) -> int:
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO modelos "
            "(profissao, psd_path, canvas_w, canvas_h, cor_r, cor_g, cor_b, cor_a, "
            " tipo, grupo, camadas_json, ativo, criado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (modelo.profissao, modelo.psd_path, modelo.canvas_w, modelo.canvas_h,
             *modelo.text_color, modelo.tipo.value, modelo.grupo, _camadas_json(modelo),
             int(modelo.ativo), modelo.criado_em or agora_str()))
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        raise DBError(f"Erro ao cadastrar modelo '{modelo.profissao}': {e}")
    finally:
        conn.close()


def atualizar_modelo(db_path: str, modelo: Modelo) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE modelos SET profissao=?, psd_path=?, canvas_w=?, canvas_h=?, "
            "cor_r=?, cor_g=?, cor_b=?, cor_a=?, tipo=?, grupo=?, camadas_json=?, ativo=? WHERE id=?",
            (modelo.profissao, modelo.psd_path, modelo.canvas_w, modelo.canvas_h,
             *modelo.text_color, modelo.tipo.value, modelo.grupo, _camadas_json(modelo),
             int(modelo.ativo), modelo.id))
        conn.commit()
    except Exception as e:
        raise DBError(f"Erro ao atualizar modelo '{modelo.profissao}': {e}")
    finally:
        conn.close()


def listar_modelos(db_path: str, tipo: TipoModelo | None = None,
                   apenas_ativos: bool = True) -> list[Modelo]:
    conn = get_connection(db_path)
    try:
        sql = "SELECT * FROM modelos WHERE 1=1"
        params: list = []
        if apenas_ativos:
            sql += " AND ativo = 1"
        if tipo is not None:
            sql += " AND tipo = ?"
            params.append(tipo.value)
        sql += " ORDER BY profissao"
        return [_linha_para_modelo(l) for l in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def buscar_modelo(db_path: str, modelo_id: int) -> Modelo | None:
    conn = get_connection(db_path)
    try:
        linha = conn.execute(
            "SELECT * FROM modelos WHERE id = ?", (modelo_id,)).fetchone()
        return _linha_para_modelo(linha) if linha else None
    finally:
        conn.close()


def listar_grupos_time(db_path: str) -> list[str]:
    """Nomes de seleção/time distintos já cadastrados (grupo de TIME) — p/ autocomplete."""
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT DISTINCT grupo FROM modelos "
            "WHERE tipo = 'TIME' AND grupo != '' ORDER BY grupo").fetchall()
        return [l["grupo"] for l in linhas]
    finally:
        conn.close()


def contar_criados_no_mes(db_path: str) -> int:
    """Modelos (qualquer tipo) cadastrados no mês corrente — dado real p/ o dashboard."""
    import datetime
    mes_atual = datetime.date.today().strftime("%m/%Y")
    conn = get_connection(db_path)
    try:
        linha = conn.execute(
            "SELECT COUNT(*) AS total FROM modelos "
            "WHERE ativo = 1 AND substr(criado_em, 4, 7) = ?", (mes_atual,)).fetchone()
        return linha["total"]
    finally:
        conn.close()


def remover_modelo(db_path: str, modelo_id: int) -> None:
    """Desativa (soft delete) — pedidos antigos continuam referenciando o modelo."""
    conn = get_connection(db_path)
    try:
        conn.execute("UPDATE modelos SET ativo = 0 WHERE id = ?", (modelo_id,))
        conn.commit()
    finally:
        conn.close()
