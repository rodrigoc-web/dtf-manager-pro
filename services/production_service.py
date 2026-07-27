"""
services/production_service.py — Orquestrador do pipeline de produção do PRO.
Coordena os serviços. Não contém lógica de negócio própria.

Fluxo:
  1. Buscar pedidos PENDENTES no SQLite local
  2. Carregar/relidar o modelo (PSD) de cada pedido
  3. Validar (telefone presente, modelo com camadas válidas)
  4. Renderizar as artes (uma por unidade de quantidade)
  5. Montar a folha e exportar PNG + PDF + relatório
  6. Registrar histórico + marcar PRODUZIDO no SQLite
"""
from __future__ import annotations
from domain.models import Pedido, Lote, ResultadoProducao, Modelo
from domain.enums import ModoExecucao, EstadoPedido, TipoModelo
from core.exceptions import DTFError
import core.logger as log


def executar(modo: ModoExecucao) -> ResultadoProducao:
    from infrastructure.filesystem import (
        db_path, historico_csv, criar_pasta_lote, fonte_path)
    from infrastructure.db import modelos_repo, pedidos_repo, lotes_repo
    from infrastructure.psd.reader import recarregar_modelo
    from services import renderer as rend
    from services.export_service import montar_folha_combinada, salvar_png, salvar_pdf
    from services.history_service import registrar_historico, gerar_relatorio

    log.producao_iniciada(f"Modo: {modo.name}")
    erros: list[str] = []
    db = str(db_path())

    # ── 1. Pedidos pendentes ────────────────────────────────────────────────
    log.info("[1/4] Buscando pedidos pendentes...")
    pendentes = pedidos_repo.listar_pendentes(db)
    if not pendentes:
        log.aviso("Nenhum pedido pendente encontrado.")
        return ResultadoProducao(sucesso=True)

    # ── 2. Modelos (com cache por modelo_id) ────────────────────────────────
    log.info("[2/4] Carregando modelos cadastrados...")
    modelos_cache: dict[int, Modelo] = {}
    validos: list[Pedido] = []

    for p in pendentes:
        if not p.completo:
            msg = f"Pedido {p.id} ({p.profissao}): dados de personalização vazios."
            log.aviso(msg)
            erros.append(msg)
            log.pedido_invalido(msg, p)
            if modo == ModoExecucao.PRODUCAO:
                try:
                    pedidos_repo.marcar_erro(db, p.id, "Dados de personalização vazios")
                except Exception:
                    pass
            continue

        if p.modelo_id not in modelos_cache:
            m = modelos_repo.buscar_modelo(db, p.modelo_id)
            if m is None:
                msg = f"Pedido {p.id}: modelo '{p.profissao}' não encontrado (removido?)."
                log.aviso(msg)
                erros.append(msg)
                continue
            try:
                modelos_cache[p.modelo_id] = recarregar_modelo(m)
            except DTFError as e:
                log.erro(str(e))
                erros.append(str(e))
                if modo == ModoExecucao.PRODUCAO:
                    try:
                        pedidos_repo.marcar_erro(db, p.id, str(e))
                    except Exception:
                        pass
                continue

        p.estado = EstadoPedido.VALIDADO
        validos.append(p)
        log.pedido_validado(f"{p.profissao} — {p.resumo}", p)

    if not validos:
        log.erro("Nenhum pedido válido para produzir.")
        return ResultadoProducao(sucesso=False, erros=erros)

    # ── 3. Renderização ──────────────────────────────────────────────────────
    log.info(f"[3/4] Renderizando {len(validos)} pedido(s)...")
    num, lote_id = lotes_repo.proximo_lote(db)
    pasta_lote   = str(criar_pasta_lote(lote_id))
    lote  = Lote(id=lote_id, numero=num, pedidos=validos, pasta=pasta_lote)
    # Times e Profissão vão em folhas separadas (Times: 2 colunas fixas, igual
    # ao DTF MANAGER original; Profissão: empacotado por linha) e depois
    # combinadas num único PNG/PDF — ver services/export_service.py.
    artes_profissao: list[tuple[Pedido, object]] = []
    artes_time: list[tuple[Pedido, object]] = []
    fp    = str(fonte_path())

    for p in validos:
        p.estado = EstadoPedido.RENDERIZANDO
        modelo = modelos_cache[p.modelo_id]
        try:
            tile = rend.renderizar_arte(p, modelo, fp)
            destino = artes_time if modelo.tipo == TipoModelo.TIME else artes_profissao
            for _ in range(max(1, p.quantidade)):
                destino.append((p, tile))
            p.estado = EstadoPedido.ARTE_GERADA
        except DTFError as e:
            log.erro(str(e))
            erros.append(str(e))
            if modo == ModoExecucao.PRODUCAO:
                try:
                    pedidos_repo.marcar_erro(db, p.id, str(e))
                except Exception:
                    pass

    if not artes_profissao and not artes_time:
        return ResultadoProducao(sucesso=False, lote=lote, erros=erros)

    # ── 4. Exportação ─────────────────────────────────────────────────────────
    log.info("[4/4] Exportando arquivos...")
    folha    = montar_folha_combinada(artes_profissao, artes_time)
    png      = salvar_png(folha, pasta_lote, lote_id)
    pdf      = salvar_pdf(png, pasta_lote, lote_id)
    try:
        relatorio = gerar_relatorio(lote, pasta_lote)
    except Exception as e:
        log.aviso(f"Relatório não gerado: {e}")
        relatorio = ""

    for p in validos:
        p.estado = EstadoPedido.EXPORTADO

    # ── 5. Histórico + banco (apenas em produção real) ─────────────────────
    if modo == ModoExecucao.PRODUCAO:
        registrar_historico(lote, str(historico_csv()))
        try:
            ids = [p.id for p in validos]
            pedidos_repo.marcar_produzidos(db, ids, lote_id)
        except DTFError as e:
            log.aviso(f"Pedidos não marcados como produzidos: {e}")

        # Baixa do estoque de rolo DTF — só em produção real (Modo Teste não
        # consome rolo de verdade). Comprimento impresso = altura da folha.
        try:
            from infrastructure.db import estoque_repo
            from core.utils import px_para_cm
            metros = px_para_cm(folha.height) / 100
            if metros > 0:
                estoque_repo.registrar_baixa(db, metros, f"Lote {lote_id}")
        except Exception as e:
            log.aviso(f"Estoque de rolo não atualizado: {e}")
    else:
        log.info("Modo teste — banco e histórico não alterados.")

    for p in validos:
        p.estado = EstadoPedido.FINALIZADO

    log.producao_concluida(
        f"Lote {lote_id} | {len(validos)} pedido(s), "
        f"{len(artes_profissao) + len(artes_time)} arte(s)", lote)

    return ResultadoProducao(
        sucesso=True, lote=lote,
        arquivo_png=png, arquivo_pdf=pdf, arquivo_relatorio=relatorio,
        erros=erros, modo_teste=(modo == ModoExecucao.TESTE),
    )
