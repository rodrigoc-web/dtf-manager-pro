"""
Testa a leitura da API de Releases do GitHub em updater.py — nunca bate na
internet de verdade, sempre com urlopen simulado (unittest.mock).
"""
import io
import json
from unittest.mock import patch
import updater


def _resposta_falsa(dados: dict, status: int = 200):
    """Simula o objeto retornado por urllib.request.urlopen (context manager)."""
    class RespostaFalsa(io.BytesIO):
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
    return RespostaFalsa(json.dumps(dados).encode("utf-8"))


def _preparar(tmp_path):
    updater.init_updater(tmp_path, tmp_path / "config_app.json")
    (tmp_path / "version.json").write_text(json.dumps({"versao": "1.0.0"}), encoding="utf-8")
    updater.VERSION_URL = "https://api.github.com/repos/rodrigoc-web/dtf-manager-pro/releases/latest"


def test_versao_nova_disponivel(tmp_path):
    _preparar(tmp_path)
    release = {
        "tag_name": "v1.1.0",
        "body": "Corrigiu bug X, adicionou Y.",
        "assets": [{"name": "DTF_MANAGER_PRO.zip",
                    "browser_download_url": "https://github.com/x/releases/download/v1.1.0/DTF_MANAGER_PRO.zip"}],
    }
    with patch("updater.request.urlopen", return_value=_resposta_falsa(release)):
        resultado = updater.verificar_atualizacao()

    assert resultado.erro == ""
    assert resultado.disponivel is True
    assert resultado.versao_remota == "v1.1.0"
    assert resultado.tipo == "zip"
    assert resultado.url.endswith("DTF_MANAGER_PRO.zip")
    assert "Corrigiu bug X" in resultado.notas


def test_versao_igual_nao_disponivel(tmp_path):
    _preparar(tmp_path)
    release = {
        "tag_name": "v1.0.0",
        "body": "",
        "assets": [{"name": "pacote.zip", "browser_download_url": "https://x/pacote.zip"}],
    }
    with patch("updater.request.urlopen", return_value=_resposta_falsa(release)):
        resultado = updater.verificar_atualizacao()
    assert resultado.disponivel is False


def test_sem_releases_publicadas_da_404(tmp_path):
    from urllib import error as url_error
    _preparar(tmp_path)
    with patch("updater.request.urlopen",
               side_effect=url_error.HTTPError("url", 404, "Not Found", {}, None)):
        resultado = updater.verificar_atualizacao()
    assert resultado.disponivel is False
    assert "Nenhuma release" in resultado.erro


def test_release_sem_asset_da_erro_claro(tmp_path):
    _preparar(tmp_path)
    release = {"tag_name": "v1.1.0", "body": "", "assets": []}
    with patch("updater.request.urlopen", return_value=_resposta_falsa(release)):
        resultado = updater.verificar_atualizacao()
    assert resultado.disponivel is False
    assert "nenhum arquivo anexado" in resultado.erro


def test_escolhe_o_asset_zip_entre_varios(tmp_path):
    _preparar(tmp_path)
    release = {
        "tag_name": "v1.1.0",
        "body": "",
        "assets": [
            {"name": "checksums.txt", "browser_download_url": "https://x/checksums.txt"},
            {"name": "DTF_MANAGER_PRO.zip", "browser_download_url": "https://x/DTF_MANAGER_PRO.zip"},
        ],
    }
    with patch("updater.request.urlopen", return_value=_resposta_falsa(release)):
        resultado = updater.verificar_atualizacao()
    assert resultado.url.endswith(".zip")


def test_sem_url_configurada_da_erro_amigavel(tmp_path):
    updater.init_updater(tmp_path, tmp_path / "config_app.json")
    updater.VERSION_URL = ""
    resultado = updater.verificar_atualizacao()
    assert "não configurada" in resultado.erro
