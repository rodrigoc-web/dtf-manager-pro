"""
infrastructure/fonts/finder.py — Localiza a fonte tipográfica do sistema.

A fonte real do projeto (FFF Internacional 2017 / fonte.otf) deve estar
em um dos caminhos abaixo. NUNCA cai silenciosamente em uma fonte
aleatória do Windows — isso gerava artes com fonte errada (Agency FB)
sem nenhum aviso visível ao operador.
"""
from __future__ import annotations
import os
from pathlib import Path
from core.exceptions import FonteNaoEncontrada


NOMES_FONTE = ["fonte.otf", "fonte.ttf", "FFF_Internacional_2017.otf"]


def encontrar(sistema_dir: str) -> str:
    """
    Localiza a fonte tipográfica oficial do projeto.
    Procura em, nesta ordem:
      1. sistema_dir/fonte.otf (raiz do projeto / pasta do .exe)
      2. sistema_dir/infrastructure/fonts/fonte.otf
      3. base_dir (pasta de instalação) e variações acima

    Levanta FonteNaoEncontrada se não achar — NUNCA usa fallback
    silencioso para fontes do Windows, pois isso gera artes com
    proporções erradas sem nenhum aviso.
    """
    candidatos = []
    base = Path(sistema_dir)

    for nome in NOMES_FONTE:
        candidatos.append(base / nome)
        candidatos.append(base / "infrastructure" / "fonts" / nome)
        candidatos.append(base / "assets" / "fonts" / nome)

    # Também tenta a partir do diretório base do programa (.exe),
    # que pode ser diferente do sistema_dir quando empacotado
    try:
        from infrastructure.filesystem import base_dir
        bd = base_dir()
        for nome in NOMES_FONTE:
            candidatos.append(bd / nome)
            candidatos.append(bd / "infrastructure" / "fonts" / nome)
    except Exception:
        pass

    for path in candidatos:
        if path.exists():
            return str(path)

    caminhos_tentados = "\n".join(f"  - {c}" for c in candidatos[:8])
    raise FonteNaoEncontrada(
        "Fonte 'fonte.otf' não encontrada em nenhum dos caminhos "
        "esperados:\n" + caminhos_tentados +
        "\n\nColoque o arquivo fonte.otf em "
        "infrastructure/fonts/fonte.otf")
