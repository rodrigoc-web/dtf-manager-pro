"""
ui/dialogs/login_dialog.py — Identificação do operador ao abrir o programa
(ou ao trocar, pelo link na sidebar). Sem senha: ferramenta interna da
fábrica, o acesso já é controlado por posse física do computador — o login
aqui serve só pra saber QUEM está usando esta instância, pra atribuir
pedidos/produção/auditoria ao nome certo.

Vitrine de boas-vindas (fundo preto, logo grande, ilustração da impressora)
em vez de um popup pequeno e genérico — é a primeira tela que qualquer
operador vê ao abrir o programa, então carrega a identidade visual da marca
igual ao mockup de referência do usuário.
"""
from __future__ import annotations
import customtkinter as ctk
from tkinter import messagebox

from core import session
from ui.theme import (SIDEBAR_BG, SIDEBAR_TEXTO, CARD_ESCURO, BORDA_ESCURA,
                      BRANCO, VERDE_GLOW, VERDE, VERDE_HOVER)
from ui import icons

RECURSOS = [
    (icons.ESCUDO, "Auditoria completa", "Todas as ações são\nregistradas"),
    (icons.GRAFICO_CIMA, "Histórico por operador", "Consulte atividades e\nproduções realizadas"),
    (icons.ALVO, "Produção rastreável", "Mais controle e eficiência\nno seu dia a dia"),
]


class LoginDialog(ctk.CTkToplevel):
    def __init__(self, master, db_path: str, on_confirmado=None, **kw):
        super().__init__(master, **kw)
        self._db = db_path
        self._on_confirmado = on_confirmado

        self.title("Identificação do operador")
        self._centralizar(1000, 680)
        self.resizable(False, False)
        self.configure(fg_color=SIDEBAR_BG)
        from ui.components.titlebar import aplicar_padrao_janela
        aplicar_padrao_janela(self)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        self._montar()
        self.grab_set()
        self.after(50, self._focar)

    def _centralizar(self, w: int, h: int):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _focar(self):
        self.lift()
        self.focus_force()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _montar(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        esquerda = ctk.CTkFrame(self, fg_color="transparent")
        esquerda.grid(row=0, column=0, sticky="nsew", padx=(56, 24), pady=(32, 26))
        esquerda.grid_columnconfigure(0, weight=1)

        self._montar_logo(esquerda)
        self._montar_boas_vindas(esquerda)
        self._montar_form(esquerda)
        self._montar_recursos(esquerda)

        self._montar_ilustracao()

    def _montar_logo(self, master):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(anchor="w", pady=(0, 34))

        icone = self._carregar_icone()
        if icone:
            ctk.CTkLabel(linha, image=icone, text="").pack(side="left", padx=(0, 12))
        textos = ctk.CTkFrame(linha, fg_color="transparent")
        textos.pack(side="left")
        ctk.CTkLabel(textos, text="DTF MANAGER", font=ctk.CTkFont("Segoe UI", 20, "bold"),
                     text_color=BRANCO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(textos, text="PRO", font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=VERDE_GLOW, anchor="w").pack(anchor="w")

    def _carregar_icone(self):
        try:
            from infrastructure.filesystem import assets_dir
            from PIL import Image
            caminho = assets_dir() / "icon.png"
            if not caminho.exists():
                return None
            img = Image.open(caminho)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(56, 56))
        except Exception:
            return None

    def _montar_boas_vindas(self, master):
        ctk.CTkLabel(master, text="Bem-vindo!", font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=VERDE_GLOW, anchor="w").pack(anchor="w")
        ctk.CTkLabel(master, text="Identifique o operador",
                     font=ctk.CTkFont("Segoe UI", 27, "bold"),
                     text_color=BRANCO, anchor="w").pack(anchor="w", pady=(2, 10))
        ctk.CTkLabel(master,
                     text="Informe seu nome para iniciar o sistema.\n"
                          "Todas as ações serão registradas e vinculadas a este operador.",
                     font=ctk.CTkFont("Segoe UI", 11), justify="left",
                     text_color=SIDEBAR_TEXTO, anchor="w").pack(anchor="w", pady=(0, 26))

    def _montar_form(self, master):
        ctk.CTkLabel(master, text="NOME DO OPERADOR",
                     font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SIDEBAR_TEXTO, anchor="w").pack(anchor="w", pady=(0, 6))

        from infrastructure.db import operadores_repo, config_repo
        nomes = operadores_repo.listar_operadores(self._db)
        ultimo = config_repo.obter(self._db, "ultimo_operador", "")

        pill = ctk.CTkFrame(master, fg_color=CARD_ESCURO, corner_radius=10,
                            border_width=1, border_color=BORDA_ESCURA, height=52)
        pill.pack(fill="x")
        pill.pack_propagate(False)
        ctk.CTkLabel(pill, text=icons.CONTATO, font=icons.fonte(16),
                     text_color=SIDEBAR_TEXTO).pack(side="left", padx=(14, 6))
        self._combo = ctk.CTkComboBox(
            pill, height=48, values=nomes, border_width=0, corner_radius=8,
            fg_color=CARD_ESCURO, text_color=BRANCO,
            button_color=VERDE_GLOW, button_hover_color=VERDE,
            dropdown_fg_color=CARD_ESCURO, dropdown_text_color=BRANCO,
            dropdown_hover_color=SIDEBAR_BG,
            font=ctk.CTkFont("Segoe UI", 13))
        self._combo.set(ultimo if ultimo else (nomes[0] if nomes else ""))
        self._combo.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self._combo.bind("<Return>", lambda e: self._confirmar())

        ctk.CTkLabel(master, text="Novo por aqui? Só digitar o nome e confirmar.",
                     font=ctk.CTkFont("Segoe UI", 9), text_color=SIDEBAR_TEXTO,
                     anchor="w").pack(anchor="w", pady=(6, 22))

        ctk.CTkButton(master, text="  Entrar", height=52, corner_radius=10,
                     image=icons.imagem(icons.ENTRAR, tam=16, cor=BRANCO), compound="left",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
                     command=self._confirmar).pack(fill="x", pady=(0, 26))

        ctk.CTkFrame(master, fg_color=BORDA_ESCURA, height=1, corner_radius=0).pack(
            fill="x", pady=(0, 22))

    def _montar_recursos(self, master):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x")
        for col, (ico, titulo, desc) in enumerate(RECURSOS):
            linha.grid_columnconfigure(col, weight=1)
            bloco = ctk.CTkFrame(linha, fg_color="transparent")
            bloco.grid(row=0, column=col, sticky="nw", padx=(0 if col == 0 else 14, 0))
            ctk.CTkLabel(bloco, text=ico, font=icons.fonte(20),
                         text_color=VERDE_GLOW).pack(anchor="w", pady=(0, 8))
            ctk.CTkLabel(bloco, text=titulo, font=ctk.CTkFont("Segoe UI", 11, "bold"),
                         text_color=BRANCO, anchor="w", justify="left",
                         wraplength=150).pack(anchor="w")
            ctk.CTkLabel(bloco, text=desc, font=ctk.CTkFont("Segoe UI", 9),
                         text_color=SIDEBAR_TEXTO, anchor="w", justify="left").pack(anchor="w", pady=(2, 0))

    def _montar_ilustracao(self):
        direita = ctk.CTkFrame(self, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="nsew")
        try:
            from infrastructure.filesystem import assets_dir
            from PIL import Image
            caminho = assets_dir() / "login_ilustracao.png"
            if caminho.exists():
                img = Image.open(caminho)
                tam = 440
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(tam, tam))
                ctk.CTkLabel(direita, image=ctk_img, text="").place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            pass

    # ── Ações ────────────────────────────────────────────────────────────────

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
