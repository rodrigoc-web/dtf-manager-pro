"""
infrastructure/db/database.py — Conexão e schema do SQLite local (dtf_pro.db).
Substitui inteiramente o Google Sheets: modelos, pedidos e lotes vivem aqui.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS modelos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    profissao     TEXT NOT NULL UNIQUE,
    psd_path      TEXT NOT NULL,
    canvas_w      INTEGER NOT NULL,
    canvas_h      INTEGER NOT NULL,
    cor_r         INTEGER NOT NULL,
    cor_g         INTEGER NOT NULL,
    cor_b         INTEGER NOT NULL,
    cor_a         INTEGER NOT NULL DEFAULT 255,
    tipo          TEXT NOT NULL DEFAULT 'PROFISSAO',
    camadas_json  TEXT NOT NULL,
    ativo         INTEGER NOT NULL DEFAULT 1,
    criado_em     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS pedidos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    modelo_id     INTEGER NOT NULL REFERENCES modelos(id),
    profissao     TEXT NOT NULL,
    dados_json    TEXT NOT NULL DEFAULT '{}',
    operador      TEXT NOT NULL DEFAULT '',
    quantidade    INTEGER NOT NULL DEFAULT 1,
    prioridade    TEXT NOT NULL DEFAULT 'NORMAL',
    status        TEXT NOT NULL DEFAULT 'PENDENTE',
    criado_em     TEXT NOT NULL,
    produzido_em  TEXT NOT NULL DEFAULT '',
    lote_id       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS lotes (
    id         TEXT PRIMARY KEY,
    numero     INTEGER NOT NULL,
    criado_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contador (
    chave  TEXT PRIMARY KEY,
    valor  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS operadores (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL UNIQUE,
    ativo      INTEGER NOT NULL DEFAULT 1,
    criado_em  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS configuracoes (
    chave  TEXT PRIMARY KEY,
    valor  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS modelos_auditoria (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    modelo_id  INTEGER NOT NULL,
    operador   TEXT NOT NULL DEFAULT '',
    acao       TEXT NOT NULL,
    detalhes   TEXT NOT NULL DEFAULT '',
    criado_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS estoque_rolo_movimentos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo       TEXT NOT NULL,
    metros     REAL NOT NULL,
    motivo     TEXT NOT NULL DEFAULT '',
    criado_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eventos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo           TEXT NOT NULL,
    operador       TEXT NOT NULL DEFAULT '',
    computador     TEXT NOT NULL DEFAULT '',
    entidade_tipo  TEXT NOT NULL DEFAULT '',
    entidade_id    TEXT NOT NULL DEFAULT '',
    detalhes       TEXT NOT NULL DEFAULT '',
    versao_app     TEXT NOT NULL DEFAULT '',
    criado_em      TEXT NOT NULL
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrar(conn: sqlite3.Connection) -> None:
    """
    Ajustes de schema em bancos já existentes — sempre preservando dados.
    `lotes.operador` (não mais usado, operador agora é por pedido) fica
    órfã mas inofensiva. Já `pedidos.telefone` (NOT NULL sem default, de
    antes do campo genérico `dados_json` existir) PRECISA ser removida —
    quebrava todo INSERT novo com IntegrityError — então essa reconstrói
    a tabela sem ela, preservando as linhas existentes.
    """
    colunas_modelos = {l["name"] for l in conn.execute("PRAGMA table_info(modelos)")}
    if "tipo" not in colunas_modelos:
        conn.execute("ALTER TABLE modelos ADD COLUMN tipo TEXT NOT NULL DEFAULT 'PROFISSAO'")
    if "criado_em" not in colunas_modelos:
        conn.execute("ALTER TABLE modelos ADD COLUMN criado_em TEXT NOT NULL DEFAULT ''")
    if "grupo" not in colunas_modelos:
        conn.execute("ALTER TABLE modelos ADD COLUMN grupo TEXT NOT NULL DEFAULT ''")

    colunas_pedidos = {l["name"] for l in conn.execute("PRAGMA table_info(pedidos)")}
    if "dados_json" not in colunas_pedidos:
        conn.execute("ALTER TABLE pedidos ADD COLUMN dados_json TEXT NOT NULL DEFAULT '{}'")
    if "operador" not in colunas_pedidos:
        conn.execute("ALTER TABLE pedidos ADD COLUMN operador TEXT NOT NULL DEFAULT ''")
    if "produzido_em" not in colunas_pedidos:
        conn.execute("ALTER TABLE pedidos ADD COLUMN produzido_em TEXT NOT NULL DEFAULT ''")
    if "marketplace" not in colunas_pedidos:
        conn.execute("ALTER TABLE pedidos ADD COLUMN marketplace TEXT NOT NULL DEFAULT ''")
    if "mensagem_erro" not in colunas_pedidos:
        conn.execute("ALTER TABLE pedidos ADD COLUMN mensagem_erro TEXT NOT NULL DEFAULT ''")
    if "ordem" not in colunas_pedidos:
        conn.execute("ALTER TABLE pedidos ADD COLUMN ordem INTEGER NOT NULL DEFAULT 0")
        # Pedidos já existentes ganham a própria ordem de criação como ordem
        # inicial (id crescente já reflete isso) — sem essa migração, todos
        # ficariam empatados em 0 e a ordenação dependeria de sorte do SQLite.
        conn.execute("UPDATE pedidos SET ordem = id WHERE ordem = 0")
    if "telefone" in colunas_pedidos:
        # Migra pedidos antigos (telefone em coluna própria) para dados_json,
        # só quando dados_json ainda não foi preenchido para aquela linha.
        import json
        antigos = conn.execute(
            "SELECT id, telefone FROM pedidos WHERE dados_json = '{}' "
            "AND telefone IS NOT NULL AND telefone != ''").fetchall()
        for linha in antigos:
            conn.execute("UPDATE pedidos SET dados_json = ? WHERE id = ?",
                        (json.dumps({"telefone": linha["telefone"]}), linha["id"]))

        # A coluna `telefone` original era NOT NULL sem default — qualquer
        # INSERT novo (que não a preenche mais) quebra com IntegrityError.
        # Reconstrói a tabela sem essa coluna (SQLite não suporta remover
        # NOT NULL via ALTER TABLE direto). Preserva todas as linhas.
        conn.executescript("""
            CREATE TABLE pedidos_novo (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                modelo_id     INTEGER NOT NULL REFERENCES modelos(id),
                profissao     TEXT NOT NULL,
                dados_json    TEXT NOT NULL DEFAULT '{}',
                operador      TEXT NOT NULL DEFAULT '',
                quantidade    INTEGER NOT NULL DEFAULT 1,
                prioridade    TEXT NOT NULL DEFAULT 'NORMAL',
                status        TEXT NOT NULL DEFAULT 'PENDENTE',
                criado_em     TEXT NOT NULL,
                produzido_em  TEXT NOT NULL DEFAULT '',
                lote_id       TEXT NOT NULL DEFAULT '',
                marketplace   TEXT NOT NULL DEFAULT '',
                mensagem_erro TEXT NOT NULL DEFAULT '',
                ordem         INTEGER NOT NULL DEFAULT 0
            );
            INSERT INTO pedidos_novo
                (id, modelo_id, profissao, dados_json, operador, quantidade,
                 prioridade, status, criado_em, produzido_em, lote_id, ordem)
            SELECT id, modelo_id, profissao, dados_json, operador, quantidade,
                   prioridade, status, criado_em, produzido_em, lote_id, id
            FROM pedidos;
            DROP TABLE pedidos;
            ALTER TABLE pedidos_novo RENAME TO pedidos;
        """)

    # Backfill único de modelos_auditoria -> eventos (Central de Auditoria).
    # `eventos` só existe a partir desta versão, então "está vazia" é sinal
    # confiável de que ainda não rodou — depois do 1º evento real, a tabela
    # nunca mais fica vazia, então essa checagem não repete o backfill.
    ja_tem_eventos = conn.execute("SELECT 1 FROM eventos LIMIT 1").fetchone()
    if not ja_tem_eventos:
        antigos = conn.execute(
            "SELECT modelo_id, operador, acao, detalhes, criado_em FROM modelos_auditoria "
            "ORDER BY id").fetchall()
        for l in antigos:
            conn.execute(
                "INSERT INTO eventos (tipo, operador, entidade_tipo, entidade_id, detalhes, criado_em) "
                "VALUES (?, ?, 'modelo', ?, ?, ?)",
                (f"MODELO_{l['acao']}", l["operador"], str(l["modelo_id"]),
                 l["detalhes"], l["criado_em"]))


def inicializar_banco(db_path: str) -> None:
    """Cria o schema se ainda não existir. Idempotente — seguro chamar toda inicialização."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    try:
        conn.executescript(_SCHEMA)
        _migrar(conn)
        conn.execute(
            "INSERT OR IGNORE INTO contador (chave, valor) VALUES ('ultimo_lote', 0)")
        conn.commit()
    finally:
        conn.close()
