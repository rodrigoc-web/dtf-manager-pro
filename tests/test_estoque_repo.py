from infrastructure.db import estoque_repo


def test_estoque_inicial_zero(db):
    assert estoque_repo.estoque_atual_metros(db) == 0


def test_reabastecimento_soma(db):
    estoque_repo.registrar_reabastecimento(db, 100, "rolo novo")
    assert estoque_repo.estoque_atual_metros(db) == 100.0


def test_baixa_subtrai(db):
    estoque_repo.registrar_reabastecimento(db, 100)
    estoque_repo.registrar_baixa(db, 15.5, "lote DTF_000001")
    assert estoque_repo.estoque_atual_metros(db) == 84.5


def test_limite_alerta_padrao_e_customizado(db):
    assert estoque_repo.limite_alerta_metros(db) == 20.0
    estoque_repo.definir_limite_alerta(db, 50)
    assert estoque_repo.limite_alerta_metros(db) == 50.0


def test_listar_movimentos_mais_recente_primeiro(db):
    estoque_repo.registrar_reabastecimento(db, 100, "primeiro")
    estoque_repo.registrar_baixa(db, 10, "segundo")
    movimentos = estoque_repo.listar_movimentos(db)
    assert movimentos[0]["motivo"] == "segundo"
    assert movimentos[1]["motivo"] == "primeiro"
