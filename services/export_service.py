"""
services/export_service.py — Monta a folha final e exporta PNG + PDF.

Times usam a MESMA disposição de 2 colunas de largura fixa do DTF MANAGER
original (`montar_folha_times`) — pedido explícito do usuário, já que
uniformes têm tamanho uniforme e essa é a medida testada em produção lá.
Profissão continua no empacotamento por LINHAS (`montar_folha`): as artes de
profissão variam muito de largura, então cada linha acumula artes lado a
lado até não caber mais espaço útil do rolo, então pula pra próxima linha —
como um "fluxo" de texto, não uma grade fixa (não faria sentido usar a
grade de 2 colunas fixas aqui). Quando um lote tem os dois tipos,
`montar_folha_combinada` empilha as duas folhas (Times em cima, Profissão
embaixo) num único PNG/PDF final.
"""
from __future__ import annotations
import os
from PIL import Image
from core.constants import CANVAS_W, MARGEM_LATERAL, COL_OFFSET, DPI
from core.utils import timestamp_arquivo
from core.exceptions import ExportError
import core.logger as log

GAP_ENTRE_ARTES = 40   # respiro entre artes na mesma linha e entre linhas


def montar_folha(artes: list[tuple[object, Image.Image]]) -> Image.Image:
    """
    Empacota as artes em linhas dentro da largura útil do rolo (57cm).
    Se uma arte sozinha for mais larga que o rolo inteiro, ela ainda é
    posicionada (a folha cresce para acomodá-la) e um aviso é logado —
    isso indica que o PSD cadastrado não está no tamanho de impressão
    correto e deve ser revisado em Gerenciar Modelos.
    """
    usavel = CANVAS_W - 2 * MARGEM_LATERAL
    linhas: list[list[Image.Image]] = []
    linha_atual: list[Image.Image] = []
    largura_atual = 0

    for _, img in artes:
        if img.width > usavel:
            log.aviso(f"Arte de {img.width}px é mais larga que o rolo útil "
                      f"({usavel}px) — revise o PSD cadastrado.")
        precisa_de_espaco = img.width + (GAP_ENTRE_ARTES if linha_atual else 0)
        if linha_atual and largura_atual + precisa_de_espaco > usavel:
            linhas.append(linha_atual)
            linha_atual, largura_atual = [], 0
        if linha_atual:
            largura_atual += GAP_ENTRE_ARTES
        linha_atual.append(img)
        largura_atual += img.width

    if linha_atual:
        linhas.append(linha_atual)

    if not linhas:
        return Image.new("RGBA", (CANVAS_W, 1), (0, 0, 0, 0))

    largura_maxima_linha = max(
        sum(im.width for im in linha) + GAP_ENTRE_ARTES * (len(linha) - 1)
        for linha in linhas
    ) + 2 * MARGEM_LATERAL
    largura_folha = max(CANVAS_W, largura_maxima_linha)

    altura_total = (sum(max(im.height for im in linha) for linha in linhas)
                    + GAP_ENTRE_ARTES * (len(linhas) - 1))

    folha = Image.new("RGBA", (largura_folha, altura_total), (0, 0, 0, 0))
    y = 0
    for linha in linhas:
        altura_linha = max(im.height for im in linha)
        x = MARGEM_LATERAL
        for im in linha:
            folha.paste(im, (x, y), im)
            x += im.width + GAP_ENTRE_ARTES
        y += altura_linha + GAP_ENTRE_ARTES

    return folha


def montar_folha_times(artes: list[tuple[object, Image.Image]]) -> Image.Image:
    """
    Monta em 2 colunas de largura fixa dentro do rolo (57cm) — a mesma
    disposição do DTF MANAGER original, usada aqui só para pedidos de Time
    (uniformes têm tamanho uniforme, então a grade fixa faz sentido de novo).
    """
    imagens = [img for _, img in artes]
    pares = [(imagens[i], imagens[i + 1] if i + 1 < len(imagens) else None)
             for i in range(0, len(imagens), 2)]
    alturas = [max(esq.height, dir_.height if dir_ else 0) for esq, dir_ in pares]

    folha = Image.new("RGBA", (CANVAS_W, sum(alturas)), (0, 0, 0, 0))
    y = 0
    for (esq, dir_), h in zip(pares, alturas):
        folha.paste(esq, (MARGEM_LATERAL, y), esq)
        if dir_:
            folha.paste(dir_, (COL_OFFSET + MARGEM_LATERAL, y), dir_)
        y += h
    return folha


def montar_folha_combinada(
        artes_profissao: list[tuple[object, Image.Image]],
        artes_time: list[tuple[object, Image.Image]]) -> Image.Image:
    """
    Ponto de entrada usado pelo pipeline de produção: monta a folha de Times
    (2 colunas fixas) e a de Profissão (empacotada por linha) separadamente
    e empilha as duas num único PNG/PDF final quando o lote tem os dois
    tipos — cada categoria mantém sua própria disposição.
    """
    partes = []
    if artes_time:
        partes.append(montar_folha_times(artes_time))
    if artes_profissao:
        partes.append(montar_folha(artes_profissao))

    if not partes:
        return Image.new("RGBA", (CANVAS_W, 1), (0, 0, 0, 0))
    if len(partes) == 1:
        return partes[0]

    largura = max(im.width for im in partes)
    altura_total = sum(im.height for im in partes) + GAP_ENTRE_ARTES * (len(partes) - 1)
    combinada = Image.new("RGBA", (largura, altura_total), (0, 0, 0, 0))
    y = 0
    for im in partes:
        combinada.paste(im, (0, y), im)
        y += im.height + GAP_ENTRE_ARTES
    return combinada


def salvar_png(folha: Image.Image, pasta: str, lote_id: str) -> str:
    try:
        ts   = timestamp_arquivo()
        nome = f"FOLHA_{lote_id}_{ts}.png"
        path = os.path.join(pasta, nome)
        folha.save(path, dpi=(DPI, DPI))
        from core.utils import px_para_cm
        log.ok(f"PNG salvo: {nome} "
               f"({px_para_cm(folha.width)}cm x {px_para_cm(folha.height)}cm)")
        from domain.events import EventBus, TipoEvento
        EventBus.get().publish(TipoEvento.ARTE_SALVA, nome)
        return path
    except Exception as e:
        raise ExportError(f"Erro ao salvar PNG: {e}")


def salvar_pdf(png_path: str, pasta: str, lote_id: str) -> str:
    """PDF de alta resolução com fundo branco (PDF não suporta transparência)."""
    try:
        img = Image.open(png_path).convert("RGBA")
        bg  = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, (0, 0), img)
        nome = f"FOLHA_{lote_id}.pdf"
        path = os.path.join(pasta, nome)
        bg.save(path, "PDF", resolution=DPI, save_all=False)
        log.ok(f"PDF salvo: {nome}")
        from domain.events import EventBus, TipoEvento
        EventBus.get().publish(TipoEvento.PDF_SALVO, nome)
        return path
    except Exception as e:
        raise ExportError(f"Erro ao salvar PDF: {e}")
