"""
Testa backup_service isolado do projeto real — nunca aponta pro
`dtf_pro.db`/`assets` de verdade (que tem ~1GB de PSDs reais e levaria
dezenas de segundos pra zipar). `base_dir`/`db_path` são substituídos por
um diretório temporário via monkeypatch.
"""
import zipfile
import infrastructure.filesystem as filesystem
from services import backup_service


def _preparar_projeto_fake(tmp_path, monkeypatch):
    base = tmp_path / "projeto"
    (base / "assets" / "psds").mkdir(parents=True)
    (base / "assets" / "psds" / "modelo.psd").write_bytes(b"conteudo falso de psd")
    db = base / "dtf_pro.db"
    db.write_bytes(b"banco falso")

    monkeypatch.setattr(filesystem, "base_dir", lambda: base)
    monkeypatch.setattr(filesystem, "db_path", lambda: db)
    return base


def test_criar_backup_inclui_db_e_assets(tmp_path, monkeypatch):
    _preparar_projeto_fake(tmp_path, monkeypatch)
    caminho = backup_service.criar_backup()
    assert caminho.exists()

    with zipfile.ZipFile(caminho) as zf:
        nomes = zf.namelist()
    assert "dtf_pro.db" in nomes
    assert any(n.endswith("modelo.psd") for n in nomes)


def test_listar_backups_mais_recente_primeiro(tmp_path, monkeypatch):
    _preparar_projeto_fake(tmp_path, monkeypatch)
    primeiro = backup_service.criar_backup()
    segundo = backup_service.criar_backup()
    backups = backup_service.listar_backups()
    assert backups[0] in (primeiro, segundo)
    assert len(backups) == 2


def test_backup_se_necessario_nao_duplica_no_mesmo_dia(tmp_path, monkeypatch):
    _preparar_projeto_fake(tmp_path, monkeypatch)
    primeiro = backup_service.backup_se_necessario()
    segundo = backup_service.backup_se_necessario()
    assert primeiro is not None
    assert segundo is None  # já tem um recente, não duplica
    assert len(backup_service.listar_backups()) == 1


def test_backup_interrompido_nao_deixa_zip_corrompido(tmp_path, monkeypatch):
    """Reproduz um bug real encontrado nesta rodada: um processo morto no meio
    do zip (timeout, crash) deixava um .zip truncado que listar_backups()
    contava como válido. criar_backup() agora escreve num .tmp e só promove
    pro nome final se terminar sem erro."""
    _preparar_projeto_fake(tmp_path, monkeypatch)
    original_write = zipfile.ZipFile.write

    def write_e_falha(self, *a, **kw):
        original_write(self, *a, **kw)
        raise OSError("falha simulada no meio do backup")

    monkeypatch.setattr(zipfile.ZipFile, "write", write_e_falha)
    try:
        backup_service.criar_backup()
        assert False, "deveria ter propagado o erro simulado"
    except OSError:
        pass

    assert backup_service.listar_backups() == []
    pasta = backup_service.pasta_backups()
    assert not any(pasta.glob("*.tmp")), "arquivo temporário não foi limpo"


def test_limpar_antigos_mantem_so_os_recentes(tmp_path, monkeypatch):
    _preparar_projeto_fake(tmp_path, monkeypatch)
    for _ in range(5):
        backup_service.criar_backup()
    backup_service.limpar_antigos(manter=2)
    assert len(backup_service.listar_backups()) == 2
