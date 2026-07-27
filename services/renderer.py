"""
services/renderer.py — Pipeline de renderização de uma arte DTF PRO completa.

Diferente do DTF MANAGER original (que monta a arte do zero colando nome/
número/escudo sobre um tile transparente), aqui a arte de base já existe
inteira dentro do PSD da profissão (fundo, ilustração, texto fixo). O
pipeline então:
  1. compõe o PSD inteiro ESCONDENDO as camadas de telefone (para não
     aparecer o número de exemplo que veio no design original);
  2. desenha o telefone do pedido em cada camada cadastrada, na posição/
     tamanho/cor exatos extraídos do PSD (reaproveita render_text.py).
"""
from __future__ import annotations
from PIL import Image
from domain.models import Modelo, Pedido
from core.constants import RESPIRO_CROP
from core.exceptions import RenderError
import core.logger as log
from services.render_text import render_numero, render_nome_adulto, render_nome_infantil

PRETO = (0, 0, 0, 255)


def _renderizar_campo(camada, valor: str, fonte_path: str, cor) -> Image.Image:
    if camada.campo == "nome":
        fn = render_nome_infantil if camada.vertical else render_nome_adulto
        return fn(valor, camada, fonte_path, cor)
    if camada.campo == "telefone":
        # A princípio (pode virar configurável por modelo depois): telefone
        # sempre em preto + Roboto, independente da cor extraída do PSD.
        from infrastructure.filesystem import roboto_path
        return render_numero(valor, camada, str(roboto_path()), PRETO)
    return render_numero(valor, camada, fonte_path, cor)


def renderizar_arte(pedido: Pedido, modelo: Modelo, fonte_path: str) -> Image.Image:
    """
    Pipeline completo: compõe o PSD escondendo as camadas de personalização,
    depois escreve o valor de cada campo do pedido na camada correspondente.
    Levanta RenderError se algo falhar.
    """
    try:
        from psd_tools import PSDImage
        psd = PSDImage.open(modelo.psd_path)
        nomes_camadas = {c.nome for c in modelo.camadas}

        def filtro(layer):
            if str(layer.name).strip() in nomes_camadas:
                return False
            return layer.visible

        tile = psd.composite(layer_filter=filtro).convert("RGBA")
        cor  = modelo.text_color

        for camada in modelo.camadas:
            valor = pedido.dados.get(camada.campo, "")
            if not valor:
                continue
            img_campo = _renderizar_campo(camada, valor, fonte_path, cor)
            tile.paste(img_campo, (camada.x, camada.y), img_campo)

        # Crop inteligente — remove espaço vazio nos 4 lados (não só embaixo,
        # como no sistema de camisas): os PSDs de profissão costumam ter
        # canvas bem maior que o conteúdo real, e cada pixel vazio impresso
        # é filme DTF desperdiçado.
        import numpy as np
        arr  = np.array(tile)
        mask = arr[:, :, 3] > 10
        if mask.any():
            ys, xs = np.where(mask)
            x0 = max(0, int(xs.min()) - RESPIRO_CROP)
            y0 = max(0, int(ys.min()) - RESPIRO_CROP)
            x1 = min(tile.width,  int(xs.max()) + RESPIRO_CROP)
            y1 = min(tile.height, int(ys.max()) + RESPIRO_CROP)
            tile = tile.crop((x0, y0, x1, y1))

        log.render_concluido(f"{modelo.profissao} — {pedido.resumo}")
        return tile

    except Exception as e:
        if isinstance(e, RenderError):
            raise
        raise RenderError(pedido.id, str(e)) from e
