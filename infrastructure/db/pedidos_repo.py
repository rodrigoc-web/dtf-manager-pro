"""
infrastructure/db/pedidos_repo.py — CRUD de pedidos. Substitui services/sheets_service.py.
"""
from __future__ import annotations
import json
from domain.models import Pedido
from domain.enums import Status, Prioridade
from core.exceptions import DBError
from core.utils import agora_str
from .database import get_connection

ORDEM_PRIORIDADE = {"URGENTE": 0, "NORMAL": 1}


def _linha_para_pedido(linha) -> Pedido:
    return Pedido(
        id=linha["id"],
        modelo_id=linha["modelo_id"],
        profissao=linha["profissao"],
        dados=json.loads(linha["dados_json"]) if linha["dados_json"] else {},
        operador=linha["operador"] if "operador" in linha.keys() else "",
        marketplace=linha["marketplace"] if "marketplace" in linha.keys() else "",
        quantidade=linha["quantidade"],
        prioridade=Prioridade(linha["prioridade"]),
        status=Status(linha["status"]),
        criado_em=linha["criado_em"],
        produzido_em=linha["produzido_em"] if "produzido_em" in linha.keys() else "",
        lote_id=linha["lote_id"],
        mensagem_erro=linha["mensagem_erro"] if "mensagem_erro" in linha.keys() else "",
        ordem=linha["ordem"] if "ordem" in linha.keys() else 0,
    )


def inserir_pedido(db_path: str, pedido: Pedido) -> int:
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO pedidos "
            "(modelo_id, profissao, dados_json, operador, marketplace, quantidade, prioridade, "
            " status, criado_em, lote_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (pedido.modelo_id, pedido.profissao, json.dumps(pedido.dados), pedido.operador,
             pedido.marketplace, pedido.quantidade, pedido.prioridade.value, pedido.status.value,
             pedido.criado_em or agora_str(), pedido.lote_id))
        novo_id = cur.lastrowid
        # ordem inicial = id (mesma ordem de criação de sempre) — só serve
        # de ponto de partida, o operador pode reordenar depois com mover_pedido.
        conn.execute("UPDATE pedidos SET ordem = ? WHERE id = ?", (novo_id, novo_id))
        conn.commit()
        return novo_id
    except Exception as e:
        raise DBError(f"Erro ao criar pedido: {e}")
    finally:
        conn.close()


def inserir_pedidos_em_lote(db_path: str, pedidos: list[Pedido]) -> list[int]:
    """Usado pela importação de planilha (Excel/CSV) — uma única transação."""
    conn = get_connection(db_path)
    ids = []
    try:
        for p in pedidos:
            cur = conn.execute(
                "INSERT INTO pedidos "
                "(modelo_id, profissao, dados_json, operador, marketplace, quantidade, prioridade, "
                " status, criado_em, lote_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (p.modelo_id, p.profissao, json.dumps(p.dados), p.operador, p.marketplace,
                 p.quantidade, p.prioridade.value, p.status.value, p.criado_em or agora_str(),
                 p.lote_id))
            novo_id = cur.lastrowid
            conn.execute("UPDATE pedidos SET ordem = ? WHERE id = ?", (novo_id, novo_id))
            ids.append(novo_id)
        conn.commit()
        return ids
    except Exception as e:
        conn.rollback()
        raise DBError(f"Erro ao importar pedidos: {e}")
    finally:
        conn.close()


def listar_pendentes(db_path: str) -> list[Pedido]:
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT * FROM pedidos WHERE status = ?", (Status.PENDENTE.value,)
        ).fetchall()
        pedidos = [_linha_para_pedido(l) for l in linhas]
        pedidos.sort(key=lambda p: (ORDEM_PRIORIDADE.get(p.prioridade.value, 1), p.ordem))
        return pedidos
    finally:
        conn.close()


def mover_pedido(db_path: str, pedido_id: int, direcao: str) -> None:
    """Reordena manualmente dentro da fila de pendentes. `direcao` é "cima"
    ou "baixo" — só troca de posição com o vizinho no MESMO nível de
    prioridade, pra um pedido Normal nunca conseguir pular na frente de um
    Urgente por engano."""
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT * FROM pedidos WHERE status = ?", (Status.PENDENTE.value,)).fetchall()
        pendentes = [_linha_para_pedido(l) for l in linhas]
        pendentes.sort(key=lambda p: (ORDEM_PRIORIDADE.get(p.prioridade.value, 1), p.ordem))

        idx = next((i for i, p in enumerate(pendentes) if p.id == pedido_id), None)
        if idx is None:
            return
        vizinho_idx = idx - 1 if direcao == "cima" else idx + 1
        if vizinho_idx < 0 or vizinho_idx >= len(pendentes):
            return
        atual, vizinho = pendentes[idx], pendentes[vizinho_idx]
        if atual.prioridade != vizinho.prioridade:
            return

        conn.execute("UPDATE pedidos SET ordem = ? WHERE id = ?", (vizinho.ordem, atual.id))
        conn.execute("UPDATE pedidos SET ordem = ? WHERE id = ?", (atual.ordem, vizinho.id))
        conn.commit()
    finally:
        conn.close()


def listar_historico(db_path: str, limite: int = 500) -> list[Pedido]:
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT * FROM pedidos WHERE status != ? ORDER BY id DESC LIMIT ?",
            (Status.PENDENTE.value, limite)).fetchall()
        return [_linha_para_pedido(l) for l in linhas]
    finally:
        conn.close()


def contagem_por_profissao(db_path: str) -> list[tuple[str, int]]:
    """
    Total de peças PRODUZIDAS (histórico completo) agrupado por profissão,
    do maior para o menor — alimenta o donut e os cards de mais/menos produzido.
    """
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT profissao, COALESCE(SUM(quantidade), 0) AS total "
            "FROM pedidos WHERE status = ? "
            "GROUP BY profissao ORDER BY total DESC",
            (Status.PRODUZIDO.value,)).fetchall()
        return [(l["profissao"], l["total"]) for l in linhas]
    finally:
        conn.close()


def operador_do_mes(db_path: str) -> tuple[str, int] | None:
    """Operador com mais peças PRODUZIDAS no mês corrente, ou None se não houver dados."""
    import datetime
    mes_atual = datetime.date.today().strftime("%m/%Y")
    conn = get_connection(db_path)
    try:
        linha = conn.execute(
            "SELECT operador, SUM(quantidade) AS total FROM pedidos "
            "WHERE status = ? AND operador != '' "
            "AND substr(produzido_em, 4, 7) = ? "
            "GROUP BY operador ORDER BY total DESC LIMIT 1",
            (Status.PRODUZIDO.value, mes_atual)).fetchone()
        return (linha["operador"], linha["total"]) if linha else None
    finally:
        conn.close()


def operadores_recentes(db_path: str, limite: int = 20) -> list[str]:
    """Nomes de operador distintos já usados — para autocomplete no formulário."""
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT DISTINCT operador FROM pedidos "
            "WHERE operador != '' ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        vistos, resultado = set(), []
        for l in linhas:
            if l["operador"] not in vistos:
                vistos.add(l["operador"])
                resultado.append(l["operador"])
        return resultado
    finally:
        conn.close()


def marketplaces_recentes(db_path: str, limite: int = 20) -> list[str]:
    """Nomes de marketplace distintos já usados — para autocomplete no formulário."""
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT DISTINCT marketplace FROM pedidos "
            "WHERE marketplace != '' ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        vistos, resultado = set(), []
        for l in linhas:
            if l["marketplace"] not in vistos:
                vistos.add(l["marketplace"])
                resultado.append(l["marketplace"])
        return resultado
    finally:
        conn.close()


def contar_produzidos_hoje(db_path: str) -> int:
    """Soma a quantidade de pedidos PRODUZIDO cuja produção foi hoje."""
    import datetime
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    conn = get_connection(db_path)
    try:
        linha = conn.execute(
            "SELECT COALESCE(SUM(quantidade), 0) AS total FROM pedidos "
            "WHERE status = ? AND produzido_em LIKE ?",
            (Status.PRODUZIDO.value, f"{hoje}%")).fetchone()
        return linha["total"]
    finally:
        conn.close()


def producao_ultimos_dias(db_path: str, dias: int = 7) -> list[int]:
    """Peças produzidas por dia, dos últimos `dias` dias (mais antigo primeiro)."""
    import datetime
    hoje = datetime.date.today()
    conn = get_connection(db_path)
    try:
        totais = []
        for i in range(dias - 1, -1, -1):
            data = (hoje - datetime.timedelta(days=i)).strftime("%d/%m/%Y")
            linha = conn.execute(
                "SELECT COALESCE(SUM(quantidade), 0) AS total FROM pedidos "
                "WHERE status = ? AND produzido_em LIKE ?",
                (Status.PRODUZIDO.value, f"{data}%")).fetchone()
            totais.append(linha["total"])
        return totais
    finally:
        conn.close()


def producao_periodo_anterior(db_path: str, dias: int = 7) -> list[int]:
    """Mesma coisa que `producao_ultimos_dias`, mas pro período de `dias`
    dias ANTERIOR ao mais recente (ex.: dias=7 -> dos 8 aos 14 dias atrás) —
    dá a base de comparação real pro badge de tendência do card "Produção",
    igual ao "vs últimos 7 dias" do mockup, sem inventar percentual."""
    import datetime
    hoje = datetime.date.today()
    conn = get_connection(db_path)
    try:
        totais = []
        for i in range(2 * dias - 1, dias - 1, -1):
            data = (hoje - datetime.timedelta(days=i)).strftime("%d/%m/%Y")
            linha = conn.execute(
                "SELECT COALESCE(SUM(quantidade), 0) AS total FROM pedidos "
                "WHERE status = ? AND produzido_em LIKE ?",
                (Status.PRODUZIDO.value, f"{data}%")).fetchone()
            totais.append(linha["total"])
        return totais
    finally:
        conn.close()


def variacao_hoje_ontem(db_path: str, campo_data: str) -> tuple[int, int]:
    """
    (quantidade hoje, quantidade ontem) somando `quantidade` dos pedidos cujo
    `campo_data` ("criado_em" ou "produzido_em") cai em cada dia — alimenta os
    badges de tendência do dashboard com números reais, nunca inventados.
    """
    import datetime
    hoje  = datetime.date.today()
    ontem = hoje - datetime.timedelta(days=1)
    conn = get_connection(db_path)
    try:
        def contar(data_str: str) -> int:
            linha = conn.execute(
                f"SELECT COALESCE(SUM(quantidade), 0) AS total FROM pedidos "
                f"WHERE {campo_data} LIKE ?", (f"{data_str}%",)).fetchone()
            return linha["total"]
        return contar(hoje.strftime("%d/%m/%Y")), contar(ontem.strftime("%d/%m/%Y"))
    finally:
        conn.close()


def marcar_produzidos(db_path: str, ids: list[int], lote_id: str) -> None:
    conn = get_connection(db_path)
    try:
        agora = agora_str()
        conn.executemany(
            "UPDATE pedidos SET status = ?, lote_id = ?, produzido_em = ? WHERE id = ?",
            [(Status.PRODUZIDO.value, lote_id, agora, pid) for pid in ids])
        conn.commit()
    except Exception as e:
        raise DBError(f"Erro ao marcar pedidos como produzidos: {e}")
    finally:
        conn.close()


def marcar_erro(db_path: str, pedido_id: int, mensagem: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE pedidos SET status = ?, mensagem_erro = ? WHERE id = ?",
            (Status.ERRO.value, mensagem, pedido_id))
        conn.commit()
    except Exception as e:
        raise DBError(f"Erro ao marcar pedido {pedido_id} como erro: {e}")
    finally:
        conn.close()


def listar_erros(db_path: str) -> list[Pedido]:
    """Pedidos com status ERRO — base da tela de recuperação de erros."""
    conn = get_connection(db_path)
    try:
        linhas = conn.execute(
            "SELECT * FROM pedidos WHERE status = ? ORDER BY id DESC",
            (Status.ERRO.value,)).fetchall()
        return [_linha_para_pedido(l) for l in linhas]
    finally:
        conn.close()


def reenviar_para_fila(db_path: str, pedido_id: int) -> None:
    """Volta um pedido ERRO pra fila (PENDENTE), limpando a mensagem — pra reprocessar."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE pedidos SET status = ?, mensagem_erro = '' WHERE id = ? AND status = ?",
            (Status.PENDENTE.value, pedido_id, Status.ERRO.value))
        conn.commit()
    finally:
        conn.close()


def remover_pedido_erro(db_path: str, pedido_id: int) -> None:
    """Descarta definitivamente um pedido ERRO (não afeta a guarda de remover_pedido
    para PENDENTE — são caminhos separados de propósito)."""
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM pedidos WHERE id = ? AND status = 'ERRO'", (pedido_id,))
        conn.commit()
    finally:
        conn.close()


def remover_pedido(db_path: str, pedido_id: int) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM pedidos WHERE id = ? AND status = 'PENDENTE'", (pedido_id,))
        conn.commit()
    finally:
        conn.close()
