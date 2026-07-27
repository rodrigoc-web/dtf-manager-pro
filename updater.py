"""
updater.py — DTF MANAGER Auto-Update v6.0
==========================================
Suporta dois modos:
  tipo = "exe"  → baixa e substitui o .exe diretamente
  tipo = "zip"  → baixa .zip, extrai o .exe, substitui

O Apps Script informa o tipo no version.json via campo "tipo".
"""

import os
import sys
import json
import time
import shutil
import zipfile
import threading
import subprocess
import tempfile
import http.cookiejar
import re
from datetime import date
from pathlib import Path
from urllib import request, error as url_error

# ── Globais ───────────────────────────────────────────────────────────────────

SISTEMA_DIR          : Path = None
BASE_DIR             : Path = None
VERSION_URL          : str  = ""
AUTO_CHECK           : bool = True
BACKUP_BEFORE_UPDATE : bool = True
TIMEOUT              : int  = 60


# ── Inicialização ─────────────────────────────────────────────────────────────

def init_updater(exe_dir: Path, config_file: Path):
    global SISTEMA_DIR, BASE_DIR, VERSION_URL, AUTO_CHECK, BACKUP_BEFORE_UPDATE
    SISTEMA_DIR = exe_dir
    BASE_DIR    = exe_dir
    try:
        if config_file.exists():
            cfg = json.loads(config_file.read_text(encoding="utf-8"))
            VERSION_URL          = cfg.get("update_url", "")
            AUTO_CHECK           = cfg.get("auto_check", True)
            BACKUP_BEFORE_UPDATE = cfg.get("backup_before_update", True)
    except Exception:
        pass
    # Criar version.json se não existir — sempre em BASE_DIR (gravável)
    vf = BASE_DIR / "version.json"
    if vf and not vf.exists():
        try:
            vf.write_text(
                json.dumps({"versao": "1.0.0",
                            "data": date.today().isoformat()},
                           indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass


# ── Versão ────────────────────────────────────────────────────────────────────

def versao_local() -> str:
    try:
        vf = BASE_DIR / "version.json"
        if vf and vf.exists():
            return json.loads(vf.read_text(encoding="utf-8")).get("versao", "0.0.0")
    except Exception:
        pass
    return "0.0.0"


def _versao_tuple(v: str) -> tuple:
    try:
        v = v.strip().lstrip("v").lstrip("V")
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0, 0, 0)


def historico_local() -> list:
    historico = []
    backup_dir = BASE_DIR / "backup" if BASE_DIR else None
    if not backup_dir or not backup_dir.exists():
        return historico
    try:
        for pasta in sorted(backup_dir.iterdir(), reverse=True):
            if not pasta.is_dir():
                continue
            vf = pasta / "version.json"
            if vf.exists():
                dados = json.loads(vf.read_text(encoding="utf-8"))
                historico.append({
                    "versao": dados.get("versao", pasta.name),
                    "data":   dados.get("data", ""),
                    "notas":  dados.get("notas", ""),
                })
    except Exception:
        pass
    return historico


# ── Resultado ─────────────────────────────────────────────────────────────────

class ResultadoUpdate:
    def __init__(self, disponivel: bool = False, versao_remota: str = "",
                 url: str = "", notas: str = "", erro: str = "",
                 tipo: str = "exe"):
        self.disponivel    = disponivel
        self.versao_remota = versao_remota
        self.url           = url
        self.notas         = notas
        self.erro          = erro
        self.tipo          = tipo   # "exe" ou "zip"


# ── Verificação ───────────────────────────────────────────────────────────────

def verificar_atualizacao() -> ResultadoUpdate:
    if not VERSION_URL:
        return ResultadoUpdate(
            erro="URL de atualização não configurada.\n"
                 "Configure em: Configurações → URL de Atualização."
        )
    try:
        req = request.Request(
            VERSION_URL,
            headers={"User-Agent": "DTF-Manager-Updater/6.0",
                     "Cache-Control": "no-cache"}
        )
        with request.urlopen(req, timeout=TIMEOUT) as resp:
            dados = json.loads(resp.read().decode("utf-8"))

        if "erro" in dados:
            return ResultadoUpdate(erro=f"Erro no servidor: {dados['erro']}")

        v_remota   = dados.get("versao", "0.0.0")
        v_local    = versao_local()
        url        = dados.get("url", "")
        notas      = dados.get("notas", "")
        tipo       = dados.get("tipo", "exe")
        disponivel = _versao_tuple(v_remota) > _versao_tuple(v_local)
        return ResultadoUpdate(disponivel, v_remota, url, notas, tipo=tipo)

    except url_error.URLError as e:
        return ResultadoUpdate(erro=f"Sem conexão:\n{getattr(e,'reason',str(e))}")
    except json.JSONDecodeError:
        return ResultadoUpdate(erro="Resposta inválida do servidor.")
    except Exception as e:
        return ResultadoUpdate(erro=f"Erro: {e}")


def checar_na_inicializacao(callback_nova_versao: callable):
    if not AUTO_CHECK or not VERSION_URL:
        return
    def _run():
        time.sleep(2)
        resultado = verificar_atualizacao()
        if resultado.disponivel:
            callback_nova_versao(resultado)
    threading.Thread(target=_run, daemon=True).start()


# ── Backup ────────────────────────────────────────────────────────────────────

def _criar_backup(versao_atual: str) -> Path:
    backup_dir = BASE_DIR / "backup" / f"v{versao_atual}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable)
        if exe.exists():
            shutil.copy2(exe, backup_dir / exe.name)
    vf = BASE_DIR / "version.json"
    return backup_dir


def _restaurar_backup(backup_dir: Path) -> bool:
    try:
        if not getattr(sys, "frozen", False):
            return False
        exe_destino = Path(sys.executable)
        for arq in backup_dir.iterdir():
            if arq.suffix.lower() == ".exe":
                shutil.copy2(arq, exe_destino)
                return True
        return False
    except Exception as e:
        print(f"[Updater] Erro ao restaurar: {e}")
        return False


# ── Download ──────────────────────────────────────────────────────────────────

def _baixar_arquivo(url: str, destino: Path, cb_progresso=None) -> bool:
    """
    Baixa arquivo do Google Drive usando usercontent diretamente.
    Bypassa a página de confirmação de vírus do Drive.
    """
    # Converter URL do Drive para usercontent (bypass confirmação)
    m = re.search(r'[?&]id=([^&]+)', url)
    if m:
        file_id = m.group(1)
        url = (f"https://drive.usercontent.google.com/download"
               f"?id={file_id}&export=download&confirm=t&authuser=0")

    print(f"[Updater] Baixando: {url[:80]}")

    try:
        cookie_jar = http.cookiejar.CookieJar()
        opener = request.build_opener(
            request.HTTPCookieProcessor(cookie_jar),
            request.HTTPRedirectHandler()
        )
        req = request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        })
        with opener.open(req, timeout=TIMEOUT) as resp:
            ct = resp.headers.get("Content-Type", "")
            cl = resp.headers.get("Content-Length", "?")
            print(f"[Updater] Content-Type: {ct} | Size: {cl}")

            if "text/html" in ct:
                print("[Updater] Recebeu HTML — tentando cookie...")
                html = resp.read().decode("utf-8", errors="ignore")
                for cookie in cookie_jar:
                    if "download_warning" in cookie.name:
                        url2 = url + "&confirm=" + cookie.value
                        return _baixar_confirmado(url2, destino,
                                                   opener, cb_progresso)
                print("[Updater] Nenhum cookie encontrado")
                return False

            return _gravar(resp, destino, cb_progresso)

    except Exception as e:
        print(f"[Updater] Erro: {type(e).__name__}: {e}")
        return False


def _baixar_confirmado(url: str, destino: Path, opener,
                        cb_progresso=None) -> bool:
    try:
        req = request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        })
        with opener.open(req, timeout=TIMEOUT) as resp:
            ct = resp.headers.get("Content-Type", "")
            print(f"[Updater] Confirmado Content-Type: {ct}")
            if "text/html" in ct:
                print("[Updater] Ainda HTML após confirmação — abortando")
                return False
            return _gravar(resp, destino, cb_progresso)
    except Exception as e:
        print(f"[Updater] Erro confirmação: {e}")
        return False


def _gravar(resp, destino: Path, cb_progresso=None) -> bool:
    try:
        total   = int(resp.headers.get("Content-Length", 0))
        baixado = 0
        with open(destino, "wb") as f:
            while True:
                chunk = resp.read(131072)
                if not chunk:
                    break
                f.write(chunk)
                baixado += len(chunk)
                if cb_progresso and total > 0:
                    cb_progresso(min(baixado / total * 100, 99))
        if cb_progresso:
            cb_progresso(100.0)
        tam = destino.stat().st_size if destino.exists() else 0
        print(f"[Updater] Gravado: {tam // 1024} KB")
        return tam > 10000   # mínimo 10KB para ser válido
    except Exception as e:
        print(f"[Updater] Erro ao gravar: {e}")
        return False


# ── Substituição via batch ────────────────────────────────────────────────────

def _substituir_exe(novo_exe: Path, cb_status=None) -> bool:
    try:
        if getattr(sys, "frozen", False):
            exe_atual = Path(sys.executable)
        else:
            exe_atual = BASE_DIR / "DTF MANAGER.exe"

        if cb_status:
            cb_status("Preparando substituição...")

        bat = BASE_DIR / "_dtf_update.bat"
        bat.write_text(
            f"@echo off\n"
            f"taskkill /f /im \"DTF MANAGER.exe\" > nul 2>&1\n"
            f"timeout /t 6 /nobreak > nul\n"
            f":retry\n"
            f"rename \"{exe_atual}\" \"DTF MANAGER.old\" > nul 2>&1\n"
            f"if exist \"{exe_atual}\" (\n"
            f"    timeout /t 2 /nobreak > nul\n"
            f"    goto retry\n"
            f")\n"
            f"move /y \"{novo_exe}\" \"{exe_atual}\"\n"
            f"del /f /q \"{exe_atual.parent / 'DTF MANAGER.old'}\" > nul 2>&1\n"
            f"start \"\" \"{exe_atual}\"\n"
            f"del /f /q \"%~f0\"\n",
            encoding="utf-8"
        )
        subprocess.Popen(
            ["cmd", "/c", str(bat)],
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True
        )
        return True
    except Exception as e:
        print(f"[Updater] Erro substituição: {e}")
        return False


def _salvar_versao_local(versao: str, notas: str = ""):
    try:
        vf = BASE_DIR / "version.json"
        vf.write_text(json.dumps({
            "versao": versao,
            "data":   date.today().isoformat(),
            "notas":  notas,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[Updater] Erro ao salvar versão: {e}")


def reiniciar():
    sys.exit(0)


# ── Classe principal ──────────────────────────────────────────────────────────

class Updater:

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def verificar_async(self, callback: callable):
        threading.Thread(
            target=lambda: callback(verificar_atualizacao()),
            daemon=True
        ).start()

    def instalar_async(self, resultado, cb_status, cb_progresso,
                       cb_concluido, cb_erro):
        def _run():
            backup_dir = None
            v_atual    = versao_local()
            tmp_dir    = Path(tempfile.mkdtemp(prefix="dtf_upd_"))

            try:
                # 1. BACKUP
                if BACKUP_BEFORE_UPDATE:
                    cb_status("Criando backup de segurança...")
                    try:
                        backup_dir = _criar_backup(v_atual)
                        cb_status(f"Backup: backup/v{v_atual}/")
                    except Exception as e:
                        cb_erro(f"Falha no backup:\n{e}\n\nAtualização cancelada.")
                        return

                # 2. DOWNLOAD
                cb_status("Baixando atualização...")
                tipo = getattr(resultado, "tipo", "exe")
                url  = resultado.url

                if tipo == "zip":
                    # Baixar zip e extrair exe
                    zip_path = tmp_dir / "update.zip"
                    ok = _baixar_arquivo(url, zip_path, cb_progresso)
                    if not ok or not zip_path.exists():
                        raise RuntimeError(
                            "Falha no download do arquivo.\n"
                            "Verifique a conexão e tente novamente."
                        )
                    cb_status("Extraindo arquivos...")
                    cb_progresso(100.0)
                    with zipfile.ZipFile(zip_path, "r") as zf:
                        exes = [n for n in zf.namelist()
                                if n.lower().endswith(".exe")]
                        if not exes:
                            raise RuntimeError("Nenhum .exe encontrado no zip.")
                        # Pegar o maior .exe
                        exes.sort(key=lambda n: zf.getinfo(n).file_size, reverse=True)
                        # Extrair TUDO (exe + _internal)
                        zf.extractall(tmp_dir)
                        novo_exe = tmp_dir / exes[0]

                        # _internal pode estar junto ao exe ou na raiz do tmp
                        internal_src = novo_exe.parent / "_internal"
                        if not internal_src.exists():
                            internal_src = tmp_dir / "_internal"
                else:
                    # Baixar exe diretamente
                    novo_exe = tmp_dir / "DTF MANAGER.exe"
                    ok = _baixar_arquivo(url, novo_exe, cb_progresso)
                    if not ok or not novo_exe.exists():
                        raise RuntimeError(
                            "Falha no download do arquivo.\n"
                            "Verifique a conexão e tente novamente."
                        )
                    cb_progresso(100.0)

                tam_mb = novo_exe.stat().st_size // 1024 // 1024
                cb_status(f"Download OK: {tam_mb} MB")

                # 3. SALVAR VERSÃO
                _salvar_versao_local(resultado.versao_remota,
                                     notas=resultado.notas)

                # 4. Manter novo exe na pasta temp — não copiar para pasta em uso
                novo_tmp = novo_exe

                # 5. SUBSTITUIR via batch — roda depois que o processo fechar
                bat = BASE_DIR / "_dtf_update.bat"
                exe_atual    = BASE_DIR / "DTF MANAGER.exe"
                version_json = BASE_DIR / "version.json"
                # _internal pode estar junto ao exe ou na raiz do tmp
                internal_src = novo_exe.parent / "_internal"
                if not internal_src.exists():
                    internal_src = tmp_dir / "_internal"
                internal_dst = BASE_DIR / "_internal"
                pid = os.getpid()
                bat.write_text(
                    f"@echo off\n"
                    f":wait\n"
                    f"tasklist /fi \"PID eq {pid}\" 2>nul | find \"{pid}\" >nul\n"
                    f"if not errorlevel 1 (\n"
                    f"    timeout /t 1 /nobreak > nul\n"
                    f"    goto wait\n"
                    f")\n"
                    f"move /y \"{exe_atual}\" \"{exe_atual}.old\" > nul 2>&1\n"
                    f"copy /y \"{novo_tmp}\" \"{exe_atual}\"\n"
                    f"del /f /q \"{exe_atual}.old\" > nul 2>&1\n"
                    f"if exist \"{internal_src}\" (\n"
                    f"    robocopy \"{internal_src}\" \"{internal_dst}\" /e /purge /nfl /ndl /njh /njs > nul 2>&1\n"
                    f")\n"
                    f"rmdir /s /q \"{tmp_dir}\" > nul 2>&1\n"
                    f"taskkill /f /im explorer.exe > nul 2>&1\n"
                    f"del /f /q \"%localappdata%\\IconCache.db\" > nul 2>&1\n"
                    f"del /f /q \"%localappdata%\\Microsoft\\Windows\\Explorer\\iconcache*.db\" > nul 2>&1\n"
                    f"start explorer.exe\n"
                    f"timeout /t 2 /nobreak > nul\n"
                    f"start \"DTF MANAGER\" /d \"{exe_atual.parent}\" \"{exe_atual}\"\n"
                    f"del /f /q \"%~f0\"\n",
                    encoding="utf-8"
                )
                subprocess.Popen(
                    ["cmd", "/c", str(bat)],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    close_fds=True
                )

                # Salvar versão APÓS lançar o bat e ANTES de fechar
                # O bat aguarda 6s antes de mover o exe, tempo suficiente
                _salvar_versao_local(resultado.versao_remota, notas=resultado.notas)

                # NÃO deletar tmp_dir aqui — o batch faz isso depois
                cb_concluido(resultado.versao_remota)

            except Exception as exc:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                if backup_dir and backup_dir.exists():
                    cb_status("Erro — restaurando versão anterior...")
                    if _restaurar_backup(backup_dir):
                        cb_erro(f"{exc}\n\n✅ Versão anterior ({v_atual}) restaurada.")
                    else:
                        cb_erro(f"{exc}\n\nBackup em: backup/v{v_atual}/")
                else:
                    cb_erro(str(exc))

        threading.Thread(target=_run, daemon=True).start()
