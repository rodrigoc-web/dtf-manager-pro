from domain.models import Modelo
from domain.enums import TipoModelo
from infrastructure.db import modelos_repo


def _modelo(profissao="ELETRICISTA", tipo=TipoModelo.PROFISSAO, grupo=""):
    return Modelo(id=None, profissao=profissao, psd_path="x.psd",
                  canvas_w=100, canvas_h=100, text_color=(0, 0, 0, 255),
                  tipo=tipo, grupo=grupo)


def test_inserir_e_buscar(db):
    mid = modelos_repo.inserir_modelo(db, _modelo())
    encontrado = modelos_repo.buscar_modelo(db, mid)
    assert encontrado is not None
    assert encontrado.profissao == "ELETRICISTA"
    assert encontrado.ativo is True


def test_listar_filtra_por_tipo(db):
    modelos_repo.inserir_modelo(db, _modelo("ELETRICISTA", TipoModelo.PROFISSAO))
    modelos_repo.inserir_modelo(db, _modelo("ADULTO VERDE", TipoModelo.TIME, grupo="BRASIL"))

    profissoes = modelos_repo.listar_modelos(db, tipo=TipoModelo.PROFISSAO)
    times = modelos_repo.listar_modelos(db, tipo=TipoModelo.TIME)
    assert [m.profissao for m in profissoes] == ["ELETRICISTA"]
    assert [m.profissao for m in times] == ["ADULTO VERDE"]


def test_listar_grupos_time(db):
    modelos_repo.inserir_modelo(db, _modelo("ADULTO VERDE", TipoModelo.TIME, grupo="BRASIL"))
    modelos_repo.inserir_modelo(db, _modelo("INFANTIL AMARELO", TipoModelo.TIME, grupo="BRASIL"))
    modelos_repo.inserir_modelo(db, _modelo("ADULTO AZUL", TipoModelo.TIME, grupo="ARGENTINA"))
    assert modelos_repo.listar_grupos_time(db) == ["ARGENTINA", "BRASIL"]


def test_remover_e_soft_delete(db):
    mid = modelos_repo.inserir_modelo(db, _modelo())
    modelos_repo.remover_modelo(db, mid)
    assert modelos_repo.listar_modelos(db) == []
    assert len(modelos_repo.listar_modelos(db, apenas_ativos=False)) == 1
    assert modelos_repo.buscar_modelo(db, mid).ativo is False


def test_atualizar_modelo(db):
    modelo = _modelo()
    modelo.id = modelos_repo.inserir_modelo(db, modelo)
    modelo.profissao = "ELETRICISTA INDUSTRIAL"
    modelos_repo.atualizar_modelo(db, modelo)
    assert modelos_repo.buscar_modelo(db, modelo.id).profissao == "ELETRICISTA INDUSTRIAL"
