from core.config import semear_arquivo_gravavel


def test_semeia_quando_destino_nao_existe(tmp_path):
    origem = tmp_path / "internal" / "config_app.json"
    origem.parent.mkdir()
    origem.write_text('{"update_url": "https://x"}', encoding="utf-8")
    destino = tmp_path / "config_app.json"

    assert semear_arquivo_gravavel(destino, origem) is True
    assert destino.read_text(encoding="utf-8") == origem.read_text(encoding="utf-8")


def test_nao_sobrescreve_destino_existente(tmp_path):
    """Edição manual local (ex.: auto_check desligado) não pode ser perdida."""
    origem = tmp_path / "internal" / "config_app.json"
    origem.parent.mkdir()
    origem.write_text('{"update_url": "https://x-do-build-novo"}', encoding="utf-8")
    destino = tmp_path / "config_app.json"
    destino.write_text('{"update_url": "https://x-editado-a-mao"}', encoding="utf-8")

    assert semear_arquivo_gravavel(destino, origem) is False
    assert "editado-a-mao" in destino.read_text(encoding="utf-8")


def test_nao_faz_nada_se_origem_nao_existe(tmp_path):
    origem = tmp_path / "internal" / "nao_existe.json"
    destino = tmp_path / "config_app.json"
    assert semear_arquivo_gravavel(destino, origem) is False
    assert not destino.exists()


def test_nao_faz_nada_se_origem_e_destino_sao_o_mesmo_arquivo(tmp_path):
    """Caso dev (sem frozen): sistema_dir() == base_dir(), mesmo arquivo."""
    arquivo = tmp_path / "config_app.json"
    arquivo.write_text("{}", encoding="utf-8")
    assert semear_arquivo_gravavel(arquivo, arquivo) is False
