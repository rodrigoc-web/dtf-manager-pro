from infrastructure.db import config_repo


def test_obter_com_padrao_quando_nao_existe(db):
    assert config_repo.obter(db, "meta_dia", "300") == "300"


def test_definir_e_obter(db):
    config_repo.definir(db, "meta_dia", "450")
    assert config_repo.obter(db, "meta_dia") == "450"


def test_definir_upsert_nao_duplica(db):
    config_repo.definir(db, "meta_dia", "450")
    config_repo.definir(db, "meta_dia", "500")
    assert config_repo.obter(db, "meta_dia") == "500"


def test_obter_int_e_float(db):
    config_repo.definir(db, "estoque_alerta_metros", "20.5")
    assert config_repo.obter_float(db, "estoque_alerta_metros") == 20.5
    assert config_repo.obter_int(db, "meta_dia", 300) == 300  # nao definido, usa padrao
