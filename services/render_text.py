"""
services/render_text.py — Primitivas de renderização tipográfica.

Calibrado a partir do DTF MANAGER original (v5.0, validada em produção):
  NOME adulto    : glifo REAL preenche 100% da altura da camada (getbbox).
                   Alinhamento ESQUERDA. Nomes longos comprimem só a largura.
  NOME vertical  : igual ao adulto, mas rotacionado 90° (glifo preenche
                   100% da altura pós-rotação) — usado quando a camada de
                   Time é marcada como "Vertical" no cadastro do modelo.
  NÚMEROS/TELEFONE: glifo REAL preenche 100% da altura da camada (getbbox).
                   Centralizado horizontalmente. Comprime largura se preciso.
"""
from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
from domain.models import Camada


def _fonte(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def render_nome_adulto(texto: str, camada: Camada,
                       fonte_path: str, color: tuple) -> Image.Image:
    """
    Glifo real preenche 100% da altura da camada.
    Alinhamento à esquerda. Nomes longos comprimem só a largura.
    """
    w, h = camada.w, camada.h
    img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    size = h * 2
    while size > 20:
        f  = _fonte(fonte_path, size)
        bb = f.getbbox(texto)
        if (bb[3] - bb[1]) <= h:
            break
        size -= 2

    f  = _fonte(fonte_path, size)
    bb = f.getbbox(texto)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]

    if tw > w:
        tmp = Image.new("RGBA", (tw + 20, h), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((10 - bb[0], -bb[1]),
                                  texto, font=f, fill=color)
        comp = tmp.resize((w, h), Image.LANCZOS)
        img.paste(comp, (0, 0), comp)
    else:
        x = -bb[0]
        y = (h - th) // 2 - bb[1]
        draw.text((x, y), texto, font=f, fill=color)

    return img


def render_nome_infantil(texto: str, camada: Camada,
                         fonte_path: str, color: tuple) -> Image.Image:
    """
    Rotação 90°. Glifo real preenche 100% da altura pós-rotação.
    """
    w, h = camada.w, camada.h
    area_larg = h
    area_alt  = w

    size = area_alt * 2
    while size > 20:
        f  = _fonte(fonte_path, size)
        bb = f.getbbox(texto)
        if (bb[3] - bb[1]) <= area_alt:
            break
        size -= 2

    f  = _fonte(fonte_path, size)
    bb = f.getbbox(texto)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]

    tmp = Image.new("RGBA", (area_larg, area_alt), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tmp)

    if tw > area_larg:
        tmp2 = Image.new("RGBA", (tw + 20, area_alt), (0, 0, 0, 0))
        ImageDraw.Draw(tmp2).text((10 - bb[0], -bb[1]),
                                   texto, font=f, fill=color)
        comp = tmp2.resize((area_larg, area_alt), Image.LANCZOS)
        tmp.paste(comp, (0, 0), comp)
    else:
        x = -bb[0]
        y = (area_alt - th) // 2 - bb[1]
        draw.text((x, y), texto, font=f, fill=color)

    rot = tmp.rotate(90, expand=True)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.paste(rot, ((w - rot.width) // 2,
                    (h - rot.height) // 2), rot)
    return img


def render_numero(texto: str, camada: Camada,
                  fonte_path: str, color: tuple) -> Image.Image:
    """
    Glifo real preenche 100% da altura da camada.
    Centralizado horizontalmente. Comprime largura se necessário.
    """
    w, h = camada.w, camada.h
    img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    size = h * 2
    while size > 20:
        f  = _fonte(fonte_path, size)
        bb = f.getbbox(texto)
        if (bb[3] - bb[1]) <= h:
            break
        size -= 2

    f  = _fonte(fonte_path, size)
    bb = f.getbbox(texto)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]

    if tw > w:
        tmp = Image.new("RGBA", (tw + 20, h), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((10 - bb[0], -bb[1]),
                                  texto, font=f, fill=color)
        comp = tmp.resize((w, h), Image.LANCZOS)
        img.paste(comp, (0, 0), comp)
    else:
        x = (w - tw) // 2 - bb[0]
        y = (h - th) // 2 - bb[1]
        draw.text((x, y), texto, font=f, fill=color)

    return img
