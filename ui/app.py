"""
ui/app.py — Janela principal do DTF MANAGER PRO.
Sidebar de navegação (grafite) + área de conteúdo (dashboard-like). O botão
de gerar produção vive dentro de Pedidos — não há uma seção "Produção"
separada; o que era o dashboard de produção (últimas produções, donut) foi
incorporado ao Histórico.
"""
from __future__ import annotations
import customtkinter as ctk
from ui.theme import FUNDO
from ui.components.sidebar import Sidebar

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class DTFProApp(ctk.CTk):
    def __init__(self, base_dir: str, sistema_dir: str):
        super().__init__()
        self._base = base_dir
        self._sis  = sistema_dir

        from infrastructure.filesystem import db_path, fonte_path
        self._db    = str(db_path())
        self._fonte = str(fonte_path())

        self._telas: dict[str, ctk.CTkFrame] = {}
        self._tela_atual: str | None = None

        self._setup()
        self._login()
        self._montar()
        self.navegar("dashboard")
        self._backup_automatico()
        self._iniciar_updater()

    def _setup(self):
        from core.constants import APP_NOME, VERSAO
        self.title(f"{APP_NOME} v{VERSAO}")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(1200, int(sw * 0.85)), min(800, int(sh * 0.85))
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.minsize(900, 600)
        self.configure(fg_color=FUNDO)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        from ui.components.titlebar import aplicar_padrao_janela
        aplicar_padrao_janela(self)

    def _login(self):
        from ui.dialogs.login_dialog import LoginDialog
        from core import session
        dialog = LoginDialog(self, self._db)
        self.wait_window(dialog)

        # Identificação é obrigatória nesse 1º login — fechar a janela sem
        # escolher um operador (X, Alt+F4) não deixa passar batido, encerra
        # o programa inteiro em vez de abrir sem saber quem está usando.
        if not session.operador_atual:
            self.destroy()
            import sys
            sys.exit(0)

    def trocar_operador(self):
        from ui.dialogs.login_dialog import LoginDialog
        dialog = LoginDialog(self, self._db, on_confirmado=lambda nome: self._sidebar.atualizar_operador())
        self.wait_window(dialog)
        self._sidebar.atualizar_operador()

    def _backup_automatico(self):
        """Dispara um backup em background se o último tiver mais de 24h (ou não existir) —
        nunca bloqueia a UI, roda em thread separada e nunca toca Tkinter direto."""
        def _worker():
            try:
                from services import backup_service
                backup_service.backup_se_necessario()
            except Exception:
                pass
        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def _iniciar_updater(self):
        """Checa por atualização só nessa abertura do programa (nunca fica
        checando periodicamente enquanto está aberto). A checagem roda em
        thread separada (dentro de updater.py); o resultado só chega até a
        UI por fila — nunca chamar .after()/widget direto de dentro de uma
        thread, já vimos esse RuntimeError antes (geração de miniatura)."""
        import queue
        import updater
        from core.config import semear_arquivo_gravavel
        from infrastructure.filesystem import config_app_json, version_json, sistema_dir

        self._fila_updates: queue.Queue = queue.Queue()

        # config_app.json e version.json (a update_url e a versão real do
        # build) são empacotados dentro de _internal/ (sistema_dir) pelo
        # PyInstaller — não ficam ao lado do .exe. Semeia cópias GRAVÁVEIS
        # em base_dir() na 1ª execução, pra sobreviver a updates futuros
        # (que só substituem o conteúdo de _internal) e ainda permitir
        # edição manual local sem perder o valor original do build.
        semear_arquivo_gravavel(config_app_json(), sistema_dir() / "config_app.json")
        semear_arquivo_gravavel(version_json(), sistema_dir() / "version.json")

        updater.init_updater(config_app_json().parent, config_app_json())
        updater.checar_na_inicializacao(
            lambda resultado: self._fila_updates.put(("auto", resultado)))
        self._drenar_fila_updates()

    def _drenar_fila_updates(self):
        import queue
        try:
            while True:
                origem, resultado = self._fila_updates.get_nowait()
                self._tratar_resultado_update(origem, resultado)
        except queue.Empty:
            pass
        self.after(300, self._drenar_fila_updates)

    def _tratar_resultado_update(self, origem: str, resultado):
        from tkinter import messagebox
        if origem == "manual":
            if resultado.erro:
                messagebox.showerror("Verificar atualização", resultado.erro)
                return
            if not resultado.disponivel:
                messagebox.showinfo("Verificar atualização",
                                     "Você já está na versão mais recente.")
                return
        if resultado.disponivel:
            self._mostrar_atualizacao(resultado)

    def _mostrar_atualizacao(self, resultado):
        from ui.dialogs.update_dialog import UpdateDialog
        UpdateDialog(self, self._base, resultado, on_reiniciar=self._reiniciar_para_atualizar)

    def verificar_atualizacao_manual(self):
        """Chamado pelo botão "Verificar atualização" da tela Ajuda — mesma
        checagem, mas disparada na hora em vez de só na abertura."""
        import threading
        import updater

        def _worker():
            resultado = updater.verificar_atualizacao()
            self._fila_updates.put(("manual", resultado))

        threading.Thread(target=_worker, daemon=True).start()

    def _reiniciar_para_atualizar(self):
        self.destroy()
        import sys
        sys.exit(0)

    def _montar(self):
        self._sidebar = Sidebar(self, on_navegar=self.navegar, on_trocar_operador=self.trocar_operador)
        self._sidebar.grid(row=0, column=0, sticky="ns")

        self._conteudo = ctk.CTkFrame(self, fg_color=FUNDO, corner_radius=0)
        self._conteudo.grid(row=0, column=1, sticky="nsew")
        self._conteudo.grid_columnconfigure(0, weight=1)
        self._conteudo.grid_rowconfigure(0, weight=1)

    def navegar(self, chave: str):
        if self._tela_atual == chave:
            return
        for tela in self._telas.values():
            tela.grid_remove()

        if chave not in self._telas:
            self._telas[chave] = self._criar_tela(chave)

        self._telas[chave].grid(row=0, column=0, sticky="nsew")
        self._sidebar.marcar_ativo(chave)
        self._tela_atual = chave

        if hasattr(self._telas[chave], "atualizar"):
            self._telas[chave].atualizar()

    def _criar_tela(self, chave: str) -> ctk.CTkFrame:
        if chave == "dashboard":
            from ui.telas.dashboard_screen import DashboardScreen
            return DashboardScreen(self._conteudo, self._db, on_navegar=self.navegar)
        if chave == "modelos":
            from ui.telas.modelos_screen import ModelosScreen
            return ModelosScreen(self._conteudo, self._db, self._fonte)
        if chave == "pedidos":
            from ui.telas.pedidos_screen import PedidosScreen
            return PedidosScreen(self._conteudo, self._db, on_concluido=self._apos_producao,
                                 on_pedir_novo_modelo=self.abrir_modelos_para_novo)
        if chave == "historico":
            from ui.telas.historico_screen import HistoricoScreen
            return HistoricoScreen(self._conteudo, self._db)
        if chave == "auditoria":
            from ui.telas.auditoria_screen import AuditoriaScreen
            return AuditoriaScreen(self._conteudo, self._db)
        if chave == "erros":
            from ui.telas.erros_screen import ErrosScreen
            return ErrosScreen(self._conteudo, self._db)
        if chave == "config":
            from ui.telas.config_screen import ConfigScreen
            return ConfigScreen(self._conteudo, self._db)
        if chave == "ajuda":
            from ui.telas.ajuda_screen import AjudaScreen
            return AjudaScreen(self._conteudo, self._db,
                               on_verificar_atualizacao=self.verificar_atualizacao_manual)
        raise ValueError(f"Tela desconhecida: {chave}")

    def abrir_modelos_para_novo(self, tipo, grupo_sugerido=None):
        """Chamado pelo item '+ Adicionar novo...' das listas suspensas de
        Pedidos (Modelo/Profissão) — leva direto pro cadastro em Modelos,
        já na aba certa e (pra Time) com a seleção pré-preenchida."""
        self.navegar("modelos")
        self._telas["modelos"].abrir_novo(tipo, grupo_sugerido)

    def _apos_producao(self):
        if "dashboard" in self._telas:
            self._telas["dashboard"].atualizar()
        if "pedidos" in self._telas:
            self._telas["pedidos"].atualizar()
        if "historico" in self._telas:
            self._telas["historico"].atualizar()
