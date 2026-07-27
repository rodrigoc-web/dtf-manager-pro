"""
Testa que `_migrar()` aplica as novas colunas/tabelas num banco de uma versão
anterior sem perder dados existentes — a mesma preocupação de cada rodada
aditiva desse projeto, agora coberta automaticamente em vez de só manual.
"""
import sqlite3
from infrastructure.db.database import inicializar_banco, get_connection

_SCHEMA_ANTIGO = """
CREATE TABLE modelos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    profissao     TEXT NOT NULL UNIQUE,
    psd_path      TEXT NOT NULL,
    canvas_w      INTEGER NOT NULL,
    canvas_h      INTEGER NOT NULL,
    cor_r         INTEGER NOT NULL,
    cor_g         INTEGER NOT NULL,
    cor_b         INTEGER NOT NULL,
    cor_a         INTEGER NOT NULL DEFAULT 255,
    camadas_json  TEXT NOT NULL,
    ativo         INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE pedidos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    modelo_id     INTEGER NOT NULL REFERENCES modelos(id),
    profissao     TEXT NOT NULL,
    quantidade    INTEGER NOT NULL DEFAULT 1,
    prioridade    TEXT NOT NULL DEFAULT 'NORMAL',
    status        TEXT NOT NULL DEFAULT 'PENDENTE',
    criado_em     TEXT NOT NULL,
    produzido_em  TEXT NOT NULL DEFAULT '',
    lote_id       TEXT NOT NULL DEFAULT ''
);
CREATE TABLE contador (chave TEXT PRIMARY KEY, valor INTEGER NOT NULL);
"""


def test_migra_banco_de_versao_anterior_preserva_dados(tmp_path):
    caminho = str(tmp_path / "antigo.db")
    conn = sqlite3.connect(caminho)
    conn.executescript(_SCHEMA_ANTIGO)
    conn.execute(
        "INSERT INTO modelos (profissao, psd_path, canvas_w, canvas_h, cor_r, cor_g, cor_b, camadas_json) "
        "VALUES ('ELETRICISTA', 'x.psd', 100, 100, 0, 0, 0, '[]')")
    conn.execute(
        "INSERT INTO pedidos (modelo_id, profissao, criado_em) VALUES (1, 'ELETRICISTA', '01/01/2026 10:00')")
    conn.commit()
    conn.close()

    inicializar_banco(caminho)  # roda _migrar() num banco já existente

    conn = get_connection(caminho)
    try:
        # dados antigos preservados
        modelo = conn.execute("SELECT * FROM modelos WHERE profissao = 'ELETRICISTA'").fetchone()
        assert modelo is not None
        assert modelo["tipo"] == "PROFISSAO"   # coluna nova, com default
        assert modelo["grupo"] == ""

        pedido = conn.execute("SELECT * FROM pedidos WHERE profissao = 'ELETRICISTA'").fetchone()
        assert pedido is not None
        assert pedido["marketplace"] == ""
        assert pedido["mensagem_erro"] == ""

        # tabelas novas existem
        tabelas = {l["name"] for l in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        for t in ("operadores", "configuracoes", "modelos_auditoria", "estoque_rolo_movimentos"):
            assert t in tabelas
    finally:
        conn.close()


def test_migrar_e_idempotente(tmp_path):
    """Rodar inicializar_banco() várias vezes seguidas não deve quebrar nada."""
    caminho = str(tmp_path / "novo.db")
    inicializar_banco(caminho)
    inicializar_banco(caminho)
    inicializar_banco(caminho)
    conn = get_connection(caminho)
    try:
        conn.execute("SELECT * FROM pedidos").fetchall()
        conn.execute("SELECT * FROM modelos").fetchall()
    finally:
        conn.close()
