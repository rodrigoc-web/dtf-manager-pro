from infrastructure.db import eventos_repo


def test_registrar_e_listar(db):
    eventos_repo.registrar(db, "LOGIN", "RODRIGO")
    eventos = eventos_repo.listar(db)
    assert len(eventos) == 1
    assert eventos[0]["tipo"] == "LOGIN"
    assert eventos[0]["operador"] == "RODRIGO"
    assert eventos[0]["computador"]   # preenchido automaticamente (nome da máquina)
    assert eventos[0]["versao_app"]


def test_listar_ordena_mais_recente_primeiro(db):
    eventos_repo.registrar(db, "LOGIN", "A")
    eventos_repo.registrar(db, "LOGIN", "B")
    eventos_repo.registrar(db, "LOGIN", "C")
    eventos = eventos_repo.listar(db)
    assert [e["operador"] for e in eventos] == ["C", "B", "A"]


def test_filtro_por_operador(db):
    eventos_repo.registrar(db, "LOGIN", "RODRIGO")
    eventos_repo.registrar(db, "LOGIN", "CARLOS")
    eventos = eventos_repo.listar(db, operador="RODRIGO")
    assert len(eventos) == 1
    assert eventos[0]["operador"] == "RODRIGO"


def test_filtro_por_tipo(db):
    eventos_repo.registrar(db, "LOGIN", "RODRIGO")
    eventos_repo.registrar(db, "MODELO_CRIADO", "RODRIGO", entidade_tipo="modelo", entidade_id=1)
    eventos = eventos_repo.listar(db, tipo="MODELO_CRIADO")
    assert len(eventos) == 1
    assert eventos[0]["tipo"] == "MODELO_CRIADO"


def test_filtro_por_entidade(db):
    eventos_repo.registrar(db, "MODELO_CRIADO", "RODRIGO", entidade_tipo="modelo", entidade_id=5)
    eventos_repo.registrar(db, "MODELO_CRIADO", "RODRIGO", entidade_tipo="modelo", entidade_id=9)
    eventos = eventos_repo.listar(db, entidade_tipo="modelo", entidade_id=5)
    assert len(eventos) == 1
    assert eventos[0]["entidade_id"] == "5"


def test_busca_por_termo_livre(db):
    eventos_repo.registrar(db, "MODELO_CRIADO", "RODRIGO", detalhes="BARBEARIA — PSD: x.psd")
    eventos_repo.registrar(db, "MODELO_CRIADO", "RODRIGO", detalhes="ELETRICISTA — PSD: y.psd")
    eventos = eventos_repo.listar(db, termo="barbearia")
    assert len(eventos) == 1
    assert "BARBEARIA" in eventos[0]["detalhes"]


def test_listar_distintos(db):
    eventos_repo.registrar(db, "LOGIN", "RODRIGO")
    eventos_repo.registrar(db, "MODELO_CRIADO", "CARLOS", entidade_tipo="modelo", entidade_id=1)
    assert set(eventos_repo.listar_operadores_distintos(db)) == {"RODRIGO", "CARLOS"}
    assert set(eventos_repo.listar_tipos_distintos(db)) == {"LOGIN", "MODELO_CRIADO"}
    assert eventos_repo.listar_computadores_distintos(db)   # pelo menos a máquina local


def test_ultimo_evento(db):
    assert eventos_repo.ultimo_evento(db) is None
    eventos_repo.registrar(db, "LOGIN", "RODRIGO")
    eventos_repo.registrar(db, "MODELO_CRIADO", "CARLOS", entidade_tipo="modelo", entidade_id=1)
    ultimo = eventos_repo.ultimo_evento(db)
    assert ultimo["tipo"] == "MODELO_CRIADO"
    assert ultimo["operador"] == "CARLOS"
