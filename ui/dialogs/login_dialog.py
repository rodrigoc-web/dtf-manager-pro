"""
ui/dialogs/login_dialog.py — Identificação do operador ao abrir o programa
(ou ao trocar, pelo link na sidebar). Sem senha: ferramenta interna da
fábrica, o acesso já é controlado por posse física do computador — o login
aqui serve só pra saber QUEM está usando esta instância, pra atribuir
pedidos/produção/auditoria ao nome certo.
"""
from __future__ import annotations
import customtkinter as ctk
from tkinter import messagebox

from core import session
from ui.theme import FUNDO, VERDE, VERDE_HOVER, CARD, BORDA, TEXTO, SUB, BRANCO
from ui import icons


class LoginDialog(ctk.CTkToplevel):
    def __init__(self, master, db_path: str, on_confirmado=None, **kw):
        super().__init__(master, **kw)
        self._db = db_path
        self._on_confirmado = on_confirmado

        self.title("Identificação do operador")
        self.geometry("380x260")
        self.resizable(False, False)
        self.configure(fg_color=FUNDO)
        from ui.components.titlebar import aplicar_padrao_janela
        aplicar_padrao_janela(self)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        self._montar()
        self.grab_set()
        self.after(50, self._focar)

    def _focar(self):
        self.lift()
        self.focus_force()

    def _montar(self):
        self.grid_columnconfigure(0, weight=1)

        topo = ctk.CTkFrame(self, fg_color=VERDE, corner_radius=0, height=54)
        topo.grid(row=0, column=0, sticky="ew")
        topo.grid_propagate(False)
        icons.rotulo(topo, icons.ESTRELA, "Quem está produzindo?",
                    tam_icone=14, tam_texto=13, negrito=True,
                    cor_icone=BRANCO, cor_texto=BRANCO).pack(side="left", padx=16, pady=14)

        corpo = ctk.CTkFrame(self, fg_color=FUNDO, corner_radius=0)
        corpo.grid(row=1, column=0, sticky="nsew", padx=18, pady=16)
        corpo.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(corpo, text="Nome do operador",
                     font=ctk.CTkFont("Segoe UI", 10, "bold"),
                     text_color=SUB, anchor="w").grid(row=0, column=0, sticky="w")

        from infrastructure.db import operadores_repo, config_repo
        nomes = operadores_repo.listar_operadores(self._db)
        ultimo = config_repo.obter(self._db, "ultimo_operador", "")

        self._combo = ctk.CTkComboBox(
            corpo, height=36, values=nomes,
            fg_color=CARD, text_color=TEXTO, border_color=BORDA,
            button_color=VERDE, button_hover_color=VERDE_HOVER,
            dropdown_fg_color=CARD)
        self._combo.set(ultimo if ultimo else (nomes[0] if nomes else ""))
        self._combo.grid(row=1, column=0, sticky="ew", pady=(4, 4))

        ctk.CTkLabel(corpo, text="Novo por aqui? Só digitar o nome e confirmar.",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=SUB, anchor="w").grid(row=2, column=0, sticky="w", pady=(0, 12))

        ctk.CTkButton(corpo, text="Entrar", height=38,
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
                     command=self._confirmar).grid(row=3, column=0, sticky="ew")
        self._combo.bind("<Return>", lambda e: self._confirmar())

    def _confirmar(self):
        nome = self._combo.get().strip()
        if not nome:
            messagebox.showwarning("Campo obrigatório", "Digite ou escolha seu nome.", parent=self)
            return

        from infrastructure.db import operadores_repo, config_repo
        operadores_repo.inserir_operador(self._db, nome)
        config_repo.definir(self._db, "ultimo_operador", nome)
        session.definir_operador(nome)

        if self._on_confirmado:
            self._on_confirmado(nome)
        self.destroy()

    def _fechar(self):
        # Fechar sem escolher mantém o operador atual (troca) ou vazio (1º login) —
        # nunca fabrica um nome, só segue sem identificação.
        self.destroy()
