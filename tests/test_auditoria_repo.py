from domain.models import Modelo
from infrastructure.db import modelos_repo, auditoria_repo


def _modelo_id(db):
    modelo = Modelo(id=None, profissao="ELETRICISTA", psd_path="x.psd",
                     canvas_w=100, canvas_h=100, text_color=(0, 0, 0, 255))
    return modelos_repo.inserir_modelo(db, modelo)


def test_registrar_e_listar_por_modelo(db):
    mid = _modelo_id(db)
    auditoria_repo.registrar(db, mid, "RODRIGO", "CRIADO", "PSD: x.psd")
    entradas = auditoria_repo.listar_por_modelo(db, mid)
    assert len(entradas) == 1
    assert entradas[0]["acao"] == "CRIADO"
    assert entradas[0]["operador"] == "RODRIGO"


def test_ordem_mais_recente_primeiro(db):
    mid = _modelo_id(db)
    auditoria_repo.registrar(db, mid, "RODRIGO", "CRIADO")
    auditoria_repo.registrar(db, mid, "RODRIGO", "EDITADO")
    entradas = auditoria_repo.listar_por_modelo(db, mid)
    assert entradas[0]["acao"] == "EDITADO"
    assert entradas[1]["acao"] == "CRIADO"


def test_listar_recentes_entre_modelos(db):
    mid1 = _modelo_id(db)
    mid2 = modelos_repo.inserir_modelo(db, Modelo(
        id=None, profissao="PEDREIRO", psd_path="y.psd",
        canvas_w=100, canvas_h=100, text_color=(0, 0, 0, 255)))
    auditoria_repo.registrar(db, mid1, "RODRIGO", "CRIADO")
    auditoria_repo.registrar(db, mid2, "RODRIGO", "CRIADO")
    assert len(auditoria_repo.listar_recentes(db)) == 2
