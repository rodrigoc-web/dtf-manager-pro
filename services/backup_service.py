"""
services/backup_service.py — backup do banco (dtf_pro.db) + assets graváveis
(PSDs copiados, miniaturas, fontes) num .zip. Sem essa proteção, qualquer
problema no disco/máquina perdia o cadastro inteiro de modelos e o histórico
de pedidos — nada disso existia antes.
"""
from __future__ import annotations
import datetime
import zipfile
from pathlib import Path


def _timestamp_unico() -> str:
    """Com microssegundos — evita colidir o nome do arquivo se dois backups
    forem criados dentro do mesmo segundo (timestamp_arquivo() só tem
    resolução de segundo, o suficiente pros outros usos mas não aqui)."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def pasta_backups() -> Path:
    from infrastructure.filesystem import base_dir
    pasta = base_dir() / "backups"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def listar_backups() -> list[Path]:
    """Mais recente primeiro."""
    pasta = pasta_backups()
    return sorted(pasta.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)


def criar_backup() -> Path:
    """Escreve num arquivo `.tmp` e só renomeia pro nome final `.zip` se
    terminar sem erro — assim um backup interrompido (processo morto, disco
    cheio) nunca deixa um .zip corrompido se passando por válido pra
    listar_backups()/backup_se_necessario()."""
    from infrastructure.filesystem import db_path, base_dir
    destino = pasta_backups() / f"backup_{_timestamp_unico()}.zip"
    provisorio = destino.with_suffix(".zip.tmp")

    try:
        with zipfile.ZipFile(provisorio, "w", zipfile.ZIP_DEFLATED) as zf:
            db = Path(db_path())
            if db.exists():
                zf.write(db, arcname=db.name)

            assets = base_dir() / "assets"
            if assets.exists():
                for arquivo in assets.rglob("*"):
                    if arquivo.is_file():
                        zf.write(arquivo, arcname=str(Path("assets") / arquivo.relative_to(assets)))
        provisorio.replace(destino)
    except BaseException:
        provisorio.unlink(missing_ok=True)
        raise

    try:
        from infrastructure.db import eventos_repo
        from core import session
        eventos_repo.registrar(str(db_path()), "BACKUP", session.operador_atual,
                               detalhes=destino.name)
    except Exception:
        pass   # log de auditoria nunca pode impedir o backup em si de ter funcionado

    return destino


def limpar_antigos(manter: int = 10) -> None:
    """Mantém só os `manter` backups mais recentes — evita crescer disco indefinidamente."""
    backups = listar_backups()
    for antigo in backups[manter:]:
        try:
            antigo.unlink()
        except OSError:
            pass


def backup_se_necessario(intervalo_horas: int = 24) -> Path | None:
    """Chamado no startup do app — só cria um novo backup se o mais recente
    tiver mais de `intervalo_horas` (ou não existir nenhum ainda)."""
    backups = listar_backups()
    if backups:
        idade = datetime.datetime.now() - datetime.datetime.fromtimestamp(backups[0].stat().st_mtime)
        if idade < datetime.timedelta(hours=intervalo_horas):
            return None
    caminho = criar_backup()
    limpar_antigos()
    return caminho
