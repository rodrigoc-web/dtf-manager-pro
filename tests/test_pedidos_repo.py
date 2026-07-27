from domain.models import Modelo, Pedido
from domain.enums import TipoModelo, Prioridade
from infrastructure.db import modelos_repo, pedidos_repo


def _modelo_id(db):
    modelo = Modelo(id=None, profissao="ELETRICISTA", psd_path="x.psd",
                     canvas_w=100, canvas_h=100, text_color=(0, 0, 0, 255))
    return modelos_repo.inserir_modelo(db, modelo)


def test_inserir_e_listar_pendentes(db):
    mid = _modelo_id(db)
    pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "119"}))
    pendentes = pedidos_repo.listar_pendentes(db)
    assert len(pendentes) == 1
    assert pendentes[0].dados["telefone"] == "119"


def test_prioridade_urgente_vem_primeiro(db):
    mid = _modelo_id(db)
    pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "1"},
        prioridade=Prioridade.NORMAL))
    pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "2"},
        prioridade=Prioridade.URGENTE))
    pendentes = pedidos_repo.listar_pendentes(db)
    assert pendentes[0].prioridade == Prioridade.URGENTE


def test_marcar_erro_grava_mensagem(db):
    mid = _modelo_id(db)
    pid = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "119"}))
    pedidos_repo.marcar_erro(db, pid, "PSD não encontrado")
    erros = pedidos_repo.listar_erros(db)
    assert len(erros) == 1
    assert erros[0].mensagem_erro == "PSD não encontrado"
    assert not pedidos_repo.listar_pendentes(db)


def test_reenviar_para_fila_limpa_mensagem(db):
    mid = _modelo_id(db)
    pid = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "119"}))
    pedidos_repo.marcar_erro(db, pid, "falhou")
    pedidos_repo.reenviar_para_fila(db, pid)
    assert not pedidos_repo.listar_erros(db)
    pendente = pedidos_repo.listar_pendentes(db)[0]
    assert pendente.mensagem_erro == ""


def test_remover_pedido_erro_nao_afeta_pendente(db):
    mid = _modelo_id(db)
    pid_pendente = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "1"}))
    pid_erro = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "2"}))
    pedidos_repo.marcar_erro(db, pid_erro, "falhou")

    # remover_pedido_erro não deve remover um PENDENTE
    pedidos_repo.remover_pedido_erro(db, pid_pendente)
    assert len(pedidos_repo.listar_pendentes(db)) == 1

    pedidos_repo.remover_pedido_erro(db, pid_erro)
    assert not pedidos_repo.listar_erros(db)


def test_inserir_em_lote(db):
    mid = _modelo_id(db)
    pedidos = [
        Pedido(id=None, modelo_id=mid, profissao="ELETRICISTA",
               dados={"nome": "SILVA", "numero_peito": "10", "numero_costas": "10"}, quantidade=1),
        Pedido(id=None, modelo_id=mid, profissao="ELETRICISTA",
               dados={"nome": "SOUZA", "numero_peito": "7", "numero_costas": "7"}, quantidade=2),
    ]
    ids = pedidos_repo.inserir_pedidos_em_lote(db, pedidos)
    assert len(ids) == 2
    assert len(pedidos_repo.listar_pendentes(db)) == 2


# ── ordem / mover_pedido ──────────────────────────────────────────────────

def _inserir_tres(db, mid):
    a = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "1"}))
    b = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "2"}))
    c = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "3"}))
    return a, b, c


def test_ordem_inicial_e_a_de_criacao(db):
    mid = _modelo_id(db)
    a, b, c = _inserir_tres(db, mid)
    assert [p.id for p in pedidos_repo.listar_pendentes(db)] == [a, b, c]


def test_mover_pedido_para_cima(db):
    mid = _modelo_id(db)
    a, b, c = _inserir_tres(db, mid)
    pedidos_repo.mover_pedido(db, c, "cima")
    assert [p.id for p in pedidos_repo.listar_pendentes(db)] == [a, c, b]


def test_mover_pedido_para_baixo(db):
    mid = _modelo_id(db)
    a, b, c = _inserir_tres(db, mid)
    pedidos_repo.mover_pedido(db, a, "baixo")
    assert [p.id for p in pedidos_repo.listar_pendentes(db)] == [b, a, c]


def test_mover_pedido_nas_bordas_nao_faz_nada(db):
    mid = _modelo_id(db)
    a, b, c = _inserir_tres(db, mid)
    pedidos_repo.mover_pedido(db, a, "cima")    # já é o primeiro
    pedidos_repo.mover_pedido(db, c, "baixo")   # já é o último
    assert [p.id for p in pedidos_repo.listar_pendentes(db)] == [a, b, c]


def test_mover_pedido_nao_cruza_nivel_de_prioridade(db):
    """Um Normal nunca pode pular na frente de um Urgente via reordenação manual."""
    mid = _modelo_id(db)
    normal = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "1"},
        prioridade=Prioridade.NORMAL))
    urgente = pedidos_repo.inserir_pedido(db, Pedido(
        id=None, modelo_id=mid, profissao="ELETRICISTA", dados={"telefone": "2"},
        prioridade=Prioridade.URGENTE))
    # urgente já vem primeiro (por prioridade); tentar mover o normal pra cima
    # não deve trocar de nivel de prioridade
    pedidos_repo.mover_pedido(db, normal, "cima")
    assert [p.id for p in pedidos_repo.listar_pendentes(db)] == [urgente, normal]
