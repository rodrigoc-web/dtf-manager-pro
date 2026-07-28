"""
services/export_service.py — Monta a folha final e exporta PNG + PDF.

Times e Profissão usam a MESMA grade de N colunas configurável
(`montar_folha_grade`) — número de colunas, tamanho de cada coluna e
largura do rolo vêm da tela Configurações (infrastructure/db/config_repo),
não são mais fixos no código. Cada arte é redimensionada proporcionalmente
(contain-fit, sem distorcer) pra caber dentro da célula da coluna, ampliando
ou encolhendo conforme necessário — antes isso exigia calibrar o tamanho
arte por arte no PSD. Quando um lote tem os dois tipos, `montar_folha_combinada`
empilha as duas folhas (Times em cima, Profissão embaixo) num único PNG/PDF
final — cada categoria usa a mesma configuração de grade.
"""
from __future__ import annotations
import os
from PIL import Image
from core.constants import MARGEM_LATERAL, DPI
from core.utils import timestamp_arquivo
from core.exceptions import ExportError
import core.logger as log

GAP_ENTRE_ARTES = 40   # respiro entre artes na mesma linha e entre linhas


def _ajustar_para_celula(img: Image.Image, largura_max: int, altura_max: int) -> Image.Image:
    """Redimensiona proporcionalmente (contain-fit, sem distorcer) pra caber
    dentro de largura_max × altura_max — encolhe OU amplia, conforme o caso."""
    escala = min(largura_max / img.width, altura_max / img.height)
    novo_tam = (max(1, round(img.width * escala)), max(1, round(img.height * escala)))
    return img.resize(novo_tam, Image.LANCZOS)


def montar_folha_grade(
        artes: list[tuple[object, Image.Image]],
        num_colunas: int,
        largura_coluna: int,
        altura_coluna: int,
        largura_rolo: int,
        margem_lateral: int = MARGEM_LATERAL,
        gap: int = GAP_ENTRE_ARTES,
        gap_colunas: int | None = None) -> Image.Image:
    """
    Organiza as artes numa grade de `num_colunas` colunas (preenche por
    linha, esquerda→direita, depois desce uma linha), redimensionando cada
    arte proporcionalmente pra caber dentro da célula (largura_coluna ×
    altura_coluna) e centralizando o resultado nela. Como toda célula tem
    tamanho fixo, todas as linhas têm a mesma altura (mais simples que o
    empacotamento antigo, que calculava altura máxima por linha).

    `gap_colunas` é o respiro HORIZONTAL entre colunas — separado de `gap`
    (que continua só pro respiro vertical entre linhas), porque o usuário
    pediu especificamente pra poder controlar a distância entre colunas na
    tela Configurações (as artes vinham grudadas, ficando "apertado"/
    amador com pouco espaço de corte entre uma pessoa e outra). Se não for
    passado, cai no mesmo valor de `gap` — preserva o comportamento antigo
    pra quem não mexer na configuração nova.
    """
    num_colunas    = max(1, num_colunas)
    largura_coluna = max(1, largura_coluna)
    altura_coluna  = max(1, altura_coluna)
    gap_colunas    = gap if gap_colunas is None else max(0, gap_colunas)

    if not artes:
        return Image.new("RGBA", (max(1, largura_rolo), 1), (0, 0, 0, 0))

    largura_necessaria = (num_colunas * largura_coluna + (num_colunas - 1) * gap_colunas
                          + 2 * margem_lateral)
    if largura_necessaria > largura_rolo:
        log.aviso(
            f"{num_colunas} coluna(s) de {largura_coluna}px não cabem na largura "
            f"do rolo configurada ({largura_rolo}px) — revise em Configurações.")
    largura_folha = max(largura_rolo, largura_necessaria)

    num_linhas = -(-len(artes) // num_colunas)   # ceil sem importar math
    altura_folha = num_linhas * altura_coluna + (num_linhas - 1) * gap

    folha = Image.new("RGBA", (largura_folha, altura_folha), (0, 0, 0, 0))
    for i, (_, img) in enumerate(artes):
        linha, col = divmod(i, num_colunas)
        ajustada = _ajustar_para_celula(img, largura_coluna, altura_coluna)
        x_celula = margem_lateral + col * (largura_coluna + gap_colunas)
        y_celula = linha * (altura_coluna + gap)
        x = x_celula + (largura_coluna - ajustada.width) // 2
        y = y_celula + (altura_coluna - ajustada.height) // 2
        folha.paste(ajustada, (x, y), ajustada)

    return folha


def montar_folha_combinada(
        artes_profissao: list[tuple[object, Image.Image]],
        artes_time: list[tuple[object, Image.Image]],
        num_colunas: int, largura_coluna: int, altura_coluna: int, largura_rolo: int,
        gap_colunas: int | None = None
) -> Image.Image:
    """
    Ponto de entrada usado pelo pipeline de produção: monta a folha de Times
    e a de Profissão separadamente (mesma configuração de grade pras duas) e
    empilha as duas num único PNG/PDF final quando o lote tem os dois tipos.
    """
    partes = []
    if artes_time:
        partes.append(montar_folha_grade(
            artes_time, num_colunas, largura_coluna, altura_coluna, largura_rolo,
            gap_colunas=gap_colunas))
    if artes_profissao:
        partes.append(montar_folha_grade(
            artes_profissao, num_colunas, largura_coluna, altura_coluna, largura_rolo,
            gap_colunas=gap_colunas))

    if not partes:
        return Image.new("RGBA", (max(1, largura_rolo), 1), (0, 0, 0, 0))
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
