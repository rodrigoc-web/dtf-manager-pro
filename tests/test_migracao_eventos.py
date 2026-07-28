"""
Cobre o backfill único de modelos_auditoria -> eventos (Central de
Auditoria) em database.py: simula um banco já existente (de antes da
tabela `eventos` existir) e confere que reabrir o app migra o histórico
sem duplicar em reaberturas seguintes.
"""
import sqlite3
from infrastructure.db.database import inicializar_banco, get_connection
from infrastructure.db import eventos_repo


def test_backfill_migra_modelos_auditoria_uma_vez(db):
    # `db` (fixture) já rodou inicializar_banco uma vez -- simula dados
    # "antigos" inserindo direto na tabela legada, como se o modelo tivesse
    # sido cadastrado numa versão anterior a essa funcionalidade existir.
    conn = get_connection(db)
    conn.execute(
        "INSERT INTO modelos_auditoria (modelo_id, operador, acao, detalhes, criado_em) "
        "VALUES (1, 'RODRIGO', 'CRIADO', 'PSD: x.psd', '01/01/2026 10:00')")
    conn.commit()
    conn.close()

    assert eventos_repo.listar(db) == []   # ainda nao migrado

    inicializar_banco(db)   # simula reabrir o app numa versao mais nova

    eventos = eventos_repo.listar(db)
    assert len(eventos) == 1
    assert eventos[0]["tipo"] == "MODELO_CRIADO"
    assert eventos[0]["operador"] == "RODRIGO"
    assert eventos[0]["entidade_tipo"] == "modelo"
    assert eventos[0]["entidade_id"] == "1"

    # reabrir de novo NAO deve duplicar (eventos ja nao esta mais vazia)
    inicializar_banco(db)
    assert len(eventos_repo.listar(db)) == 1


def test_backfill_nao_roda_se_ja_havia_eventos_reais(db):
    eventos_repo.registrar(db, "LOGIN", "RODRIGO")

    conn = get_connection(db)
    conn.execute(
        "INSERT INTO modelos_auditoria (modelo_id, operador, acao, detalhes, criado_em) "
        "VALUES (2, 'CARLOS', 'CRIADO', '', '02/02/2026 11:00')")
    conn.commit()
    conn.close()

    inicializar_banco(db)

    # eventos ja nao estava vazia (tinha o LOGIN) -- backfill nao deveria
    # ter rodado, entao o registro antigo de modelos_auditoria NAO aparece
    eventos = eventos_repo.listar(db)
    assert len(eventos) == 1
    assert eventos[0]["tipo"] == "LOGIN"
