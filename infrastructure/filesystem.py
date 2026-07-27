"""
infrastructure/filesystem.py — Caminhos e operações de arquivo do sistema.
Único lugar que conhece a estrutura de pastas do programa.
"""
from __future__ import annotations
import sys
from pathlib import Path


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def sistema_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


def output_dir() -> Path:
    d = base_dir() / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def logs_dir() -> Path:
    d = base_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def historico_csv() -> Path:
    """Export legível em CSV do histórico (fonte de verdade é o SQLite)."""
    return logs_dir() / "historico.csv"


def db_path() -> Path:
    return base_dir() / "dtf_pro.db"


def config_app_json() -> Path:
    return base_dir() / "config_app.json"


def version_json() -> Path:
    return base_dir() / "version.json"


def assets_dir() -> Path:
    return sistema_dir() / "assets"


def psds_dir() -> Path:
    """
    Pasta local onde os PSDs de produção são copiados no cadastro de um
    modelo (Gerenciar Modelos) — nunca referenciamos o caminho de rede
    diretamente, para a produção não depender do computador/rede que
    hospeda o acervo original estar ligado e acessível.
    """
    d = base_dir() / "assets" / "psds"
    d.mkdir(parents=True, exist_ok=True)
    return d


def copiar_psd_local(origem: str, profissao: str) -> str:
    """
    Copia o PSD escolhido para assets/psds/<PROFISSAO>/ e retorna o
    caminho local. Se o destino já existir com o mesmo tamanho, não
    copia de novo (evita recopiar ao só editar as camadas de um modelo
    já cadastrado).
    """
    import re, shutil
    origem_path = Path(origem)
    nome_seguro = re.sub(r'[<>:"/\\|?*]', "_", profissao.strip().upper())
    pasta_destino = psds_dir() / nome_seguro
    pasta_destino.mkdir(parents=True, exist_ok=True)
    destino = pasta_destino / origem_path.name

    if not destino.exists() or destino.stat().st_size != origem_path.stat().st_size:
        shutil.copy2(origem_path, destino)
    return str(destino)


def thumbs_dir() -> Path:
    """
    Miniaturas de Modelos cacheadas em disco (PNG pequeno) — geradas 1x no
    cadastro/edição do modelo. Renderizar o PSD é pesado (psd-tools/numpy em
    canvas grandes); sem esse cache em disco, toda vez que a tela Modelos
    abre (ou o app reinicia) todos os modelos seriam re-renderizados do
    zero — foi isso que deixou o app pesado/travando.
    """
    d = base_dir() / "assets" / "thumbs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def thumb_path(modelo_id: int) -> Path:
    return thumbs_dir() / f"{modelo_id}.png"


def fonte_path() -> Path:
    """Retorna o path da fonte — delega para infrastructure/fonts/finder."""
    from infrastructure.fonts.finder import encontrar
    return Path(encontrar(str(sistema_dir())))


def roboto_path() -> Path:
    """
    Fonte usada especificamente para o número de telefone nas artes de
    Profissão (preto + Roboto, a pedido do usuário — "a princípio", ou
    seja, pode virar configurável por modelo no futuro). Empacotada dentro
    do próprio projeto (assets/fonts/Roboto-Regular.ttf) em vez de depender
    de o Photoshop estar instalado na máquina que roda o programa.
    """
    return sistema_dir() / "assets" / "fonts" / "Roboto-Regular.ttf"


def criar_pasta_lote(lote_id: str) -> Path:
    pasta = output_dir() / lote_id
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta
