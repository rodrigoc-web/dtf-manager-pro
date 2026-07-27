"""
Testa o pipeline de producao_service.executar() sem precisar de PSDs reais
(recarregar_modelo e renderizar_arte sao substituidos) e sem tocar em
output/logs do projeto real (db_path/historico_csv/criar_pasta_lote/
fonte_path apontam pra tmp_path).

Cobre principalmente uma regressao real encontrada nesta rodada: um pedido
que falha durante a renderizacao ficava marcado ERRO corretamente, mas
`marcar_produzidos` (chamado no fim do lote com a lista `validos` inteira,
sem filtrar) sobrescrevia o status de volta pra PRODUZIDO.
"""
from pathlib import Path
from PIL import Image

import infrastructure.filesystem as filesystem
import infrastructure.psd.reader as psd_reader
import services.renderer as renderer
from domain.enums import ModoExecucao, Status
from domain.models import Modelo, Pedido
from infrastructure.db import modelos_repo, pedidos_repo
from services import production_service
from core.exceptions import RenderError


def _preparar_ambiente(tmp_path, monkeypatch, db):
    (tmp_path / "output").mkdir()
    (tmp_path / "logs").mkdir()

    monkeypatch.setattr(filesystem, "db_path", lambda: Path(db))
    monkeypatch.setattr(filesystem, "historico_csv", lambda: tmp_path / "logs" / "historico.csv")
    monkeypatch.setattr(filesystem, "criar_pasta_lote",
                        lambda lote_id: (tmp_path / "output" / lote_id).mkdir(parents=True, exist_ok=True)
                        or (tmp_path / "output" / lote_id))
    monkeypatch.setattr(filesystem, "fonte_path", lambda: tmp_path / "fonte.ttf")

    # recarregar_modelo normalmente reabre o PSD de verdade -- aqui so
    # devolve o mesmo modelo, sem tocar em disco.
    monkeypatch.setattr(psd_reader, "recarregar_modelo", lambda m: m)


def test_pedido_com_erro_na_renderizacao_nao_vira_produzido(tmp_path, monkeypatch, db):
    _preparar_ambiente(tmp_path, monkeypatch, db)

    modelo = Modelo(id=None, profissao="ELETRICISTA", psd_path="x.psd",
                     canvas_w=100, canvas_h=100, text_color=(0, 0, 0, 255))
    modelo.id = modelos_repo.inserir_modelo(db, modelo)

    pid_ok = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=modelo.id, profissao="ELETRICISTA", dados={"telefone": "111"}))
    pid_falha = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=modelo.id, profissao="ELETRICISTA", dados={"telefone": "222"}))

    def renderizar_fake(pedido, modelo, fonte_path):
        if pedido.id == pid_falha:
            raise RenderError(pedido.id, "falha simulada")
        return Image.new("RGBA", (50, 50), (255, 0, 0, 255))

    monkeypatch.setattr(renderer, "renderizar_arte", renderizar_fake)

    resultado = production_service.executar(ModoExecucao.PRODUCAO)

    assert resultado.sucesso is True

    pedido_ok = next(p for p in pedidos_repo.listar_historico(db) if p.id == pid_ok)
    pedido_falha = next(p for p in pedidos_repo.listar_historico(db) if p.id == pid_falha)
    assert pedido_ok.status == Status.PRODUZIDO
    assert pedido_falha.status == Status.ERRO, (
        "regressao: pedido que falhou na renderizacao nao pode virar PRODUZIDO")
    assert pedido_falha.mensagem_erro

    # o lote/relatorio tambem nao pode listar o pedido que falhou
    ids_no_lote = [p.id for p in resultado.lote.pedidos]
    assert pid_ok in ids_no_lote
    assert pid_falha not in ids_no_lote


def test_modo_teste_nao_marca_produzido_nem_erro_no_banco(tmp_path, monkeypatch, db):
    _preparar_ambiente(tmp_path, monkeypatch, db)

    modelo = Modelo(id=None, profissao="ELETRICISTA", psd_path="x.psd",
                     canvas_w=100, canvas_h=100, text_color=(0, 0, 0, 255))
    modelo.id = modelos_repo.inserir_modelo(db, modelo)
    pid = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=modelo.id, profissao="ELETRICISTA", dados={"telefone": "111"}))

    monkeypatch.setattr(renderer, "renderizar_arte",
                        lambda pedido, modelo, fonte_path: Image.new("RGBA", (50, 50), (255, 0, 0, 255)))

    resultado = production_service.executar(ModoExecucao.TESTE)

    assert resultado.sucesso is True
    assert resultado.modo_teste is True
    pendente = pedidos_repo.listar_pendentes(db)
    assert len(pendente) == 1 and pendente[0].id == pid   # continua PENDENTE
