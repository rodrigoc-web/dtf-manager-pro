"""
core/config.py — Leitura e gravação de config_app.json (updater, preferências).
Diferente do DTF MANAGER original, o PRO não tem config.json de planilha —
todo o estado de dados vive em dtf_pro.db (SQLite).
"""
from __future__ import annotations
import json
from pathlib import Path


def carregar_config_app(config_app_path: str) -> dict:
    """Lê config_app.json (update_url, auto_check). Retorna {} se ainda não existir."""
    path = Path(config_app_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def salvar_config_app(config_app_path: str, dados: dict):
    """Salva config_app.json preservando campos existentes."""
    from core.exceptions import ConfigError
    path = Path(config_app_path)
    try:
        existente = carregar_config_app(config_app_path)
        existente.update(dados)
        path.write_text(
            json.dumps(existente, indent=2, ensure_ascii=False),
            encoding="utf-8")
    except Exception as e:
        raise ConfigError(f"Erro ao salvar configurações: {e}")
