from infrastructure.db import operadores_repo


def test_inserir_e_listar(db):
    operadores_repo.inserir_operador(db, "RODRIGO")
    assert operadores_repo.listar_operadores(db) == ["RODRIGO"]


def test_inserir_e_idempotente(db):
    oid1 = operadores_repo.inserir_operador(db, "RODRIGO")
    oid2 = operadores_repo.inserir_operador(db, "RODRIGO")
    assert oid1 == oid2
    assert len(operadores_repo.listar_operadores(db)) == 1


def test_soft_delete_e_reativacao(db):
    oid = operadores_repo.inserir_operador(db, "RODRIGO")
    operadores_repo.remover_operador(db, oid)
    assert operadores_repo.listar_operadores(db) == []
    assert operadores_repo.listar_operadores(db, apenas_ativos=False) == ["RODRIGO"]
    # inserir de novo com o mesmo nome reativa em vez de duplicar
    operadores_repo.inserir_operador(db, "RODRIGO")
    assert operadores_repo.listar_operadores(db) == ["RODRIGO"]


def test_buscar_por_nome(db):
    oid = operadores_repo.inserir_operador(db, "RODRIGO")
    assert operadores_repo.buscar_por_nome(db, "RODRIGO") == oid
    assert operadores_repo.buscar_por_nome(db, "INEXISTENTE") is None
