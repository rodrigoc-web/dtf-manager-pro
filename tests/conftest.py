"""
tests/conftest.py — fixtures compartilhadas. Requer `pip install pytest`
(o projeto não usa um gerenciador de dependências formal — ver GERAR_EXE.bat
para a lista de pacotes de runtime; pytest é só uma dependência de dev).

Todo banco usado nos testes é criado do zero num arquivo temporário
(`tmp_path` do pytest) — nunca no `dtf_pro.db` real do usuário.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from infrastructure.db.database import inicializar_banco


@pytest.fixture
def db(tmp_path) -> str:
    caminho = str(tmp_path / "teste.db")
    inicializar_banco(caminho)
    return caminho
