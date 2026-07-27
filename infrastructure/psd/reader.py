"""
infrastructure/psd/reader.py — Leitura genérica de PSD para o DTF MANAGER PRO.

Diferente do DTF MANAGER original (camadas fixas NOME/NUMERO COSTAS/NUMERO
FRENTE/ESCUDO), aqui QUALQUER PSD pode ser cadastrado: o usuário escolhe,
na tela Gerenciar Modelos, quais camadas (por nome) recebem o telefone.
Este módulo:
  1. lista as camadas do PSD para a tela de calibração (`listar_camadas`),
     sugerindo candidatas por heurística de nome;
  2. constrói o `Modelo` a partir das camadas confirmadas pelo usuário
     (`construir_modelo`), extraindo posição/tamanho/cor real do PSD;
  3. relê o mesmo PSD no momento da produção para confirmar que as camadas
     cadastradas ainda existem (`recarregar_modelo`) — o PSD pode ter sido
     editado no Photoshop depois do cadastro.
"""
from __future__ import annotations
from pathlib import Path
from domain.models import Modelo, Camada
from domain.enums import TipoModelo
from core.constants import PALAVRAS_CHAVE_TELEFONE
from core.exceptions import PSDAusente, CamadaPSDNaoEncontrada
import core.logger as log


def _extrair_cor_isolada(psd, layer) -> tuple[int, int, int, int] | None:
    """
    Extrai a cor dominante de UMA camada isolada: compõe o PSD escondendo
    todas as outras camadas (layer_filter), então o alpha da composição
    já diz exatamente quais pixels pertencem ao glifo do texto — sem
    contaminação do fundo por trás. Diferente do sistema de camisas
    (PSD transparente), aqui o fundo é real e o texto pode legitimamente
    ser branco ou preto, então NÃO rejeitamos por brilho — só pela
    presença de alpha.
    """
    try:
        import numpy as np

        iso = psd.composite(layer_filter=lambda l, alvo=layer: l is alvo)

        x0 = max(0, layer.left)
        y0 = max(0, layer.top)
        x1 = min(iso.width,  layer.left + layer.width)
        y1 = min(iso.height, layer.top  + layer.height)
        if x1 <= x0 or y1 <= y0:
            return None

        regiao = iso.crop((x0, y0, x1, y1)).convert("RGBA")
        arr    = np.array(regiao)

        mask   = arr[:, :, 3] > 200
        pixels = arr[mask]
        if len(pixels) == 0:
            mask   = arr[:, :, 3] > 50
            pixels = arr[mask]
        if len(pixels) == 0:
            return None

        cores, contagens = np.unique(
            pixels[:, :3].reshape(-1, 3), axis=0, return_counts=True)
        cor = cores[np.argmax(contagens)]
        r, g, b = int(cor[0]), int(cor[1]), int(cor[2])
        return (r, g, b, 255)
    except Exception:
        return None


def _abrir(psd_path: str):
    from psd_tools import PSDImage
    path = Path(psd_path)
    if not path.exists():
        raise PSDAusente(f"PSD não encontrado: {psd_path}")
    return PSDImage.open(str(path))


def listar_camadas(psd_path: str) -> list[dict]:
    """
    Lista todas as camadas visíveis (não-grupo) do PSD, para a tela de
    calibração. Cada item: {nome, x, y, w, h, candidata_telefone}.
    """
    psd = _abrir(psd_path)
    resultado = []
    for layer in psd.descendants():
        if layer.is_group() or not layer.visible:
            continue
        nome = str(layer.name).strip()
        candidata = any(p in nome.upper() for p in PALAVRAS_CHAVE_TELEFONE)
        resultado.append({
            "nome": nome, "x": layer.left, "y": layer.top,
            "w": layer.width, "h": layer.height,
            "candidata_telefone": candidata,
        })
    return resultado


def info_canvas(psd_path: str) -> tuple[int, int]:
    psd = _abrir(psd_path)
    return psd.width, psd.height


def construir_modelo(profissao: str, tipo: TipoModelo, psd_path: str,
                      mapeamento: dict[str, dict]) -> Modelo:
    """
    Constrói o Modelo a partir das camadas confirmadas pelo usuário na tela
    de calibração. `mapeamento` é {nome_da_camada: {"campo": ..., "vertical": bool}}
    — para Profissão só existe o campo "telefone"; para Time, "nome"
    (+ vertical opcional), "numero_peito", "numero_costas".
    Levanta CamadaPSDNaoEncontrada se algum nome não existir mais no PSD
    (arquivo foi alterado nesse meio-tempo).
    """
    psd = _abrir(psd_path)
    encontrado: dict[str, object] = {}
    for layer in psd.descendants():
        if layer.is_group() or not layer.visible:
            continue
        nome = str(layer.name).strip()
        if nome in mapeamento:
            encontrado[nome] = layer

    faltando = set(mapeamento) - set(encontrado)
    if faltando:
        raise CamadaPSDNaoEncontrada(", ".join(sorted(faltando)), profissao)

    cor = None
    for nome in mapeamento:
        cor = _extrair_cor_isolada(psd, encontrado[nome])
        if cor is not None:
            break
    if cor is None:
        cor = (0, 0, 0, 255)
        log.aviso(f"Não foi possível extrair cor de '{profissao}' — usando preto")

    camadas = [
        Camada(nome=nome, campo=info["campo"],
               x=layer.left, y=layer.top, w=layer.width, h=layer.height,
               vertical=info.get("vertical", False))
        for nome, layer in encontrado.items()
        for info in [mapeamento[nome]]
    ]

    log.ok(f"'{profissao}' cadastrado ({tipo.value}): {psd.width}x{psd.height}px, "
           f"{len(camadas)} camada(s), cor=RGB{cor[:3]}")

    return Modelo(
        id=None, profissao=profissao, psd_path=psd_path,
        canvas_w=psd.width, canvas_h=psd.height,
        text_color=cor, tipo=tipo, camadas=camadas,
    )


def recarregar_modelo(modelo: Modelo) -> Modelo:
    """
    Relê o PSD no momento da produção, garantindo que as camadas cadastradas
    ainda existem (o arquivo pode ter sido editado no Photoshop depois do
    cadastro). Mantém o mesmo id do modelo original.
    """
    mapeamento = {c.nome: {"campo": c.campo, "vertical": c.vertical}
                  for c in modelo.camadas}
    atualizado = construir_modelo(
        modelo.profissao, modelo.tipo, modelo.psd_path, mapeamento)
    atualizado.id = modelo.id
    return atualizado
