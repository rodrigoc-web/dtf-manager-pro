"""
ui/dialogs/login_dialog.py — Identificação do operador ao abrir o programa
(ou ao trocar, pelo link na sidebar). Sem senha: ferramenta interna da
fábrica, o acesso já é controlado por posse física do computador — o login
aqui serve só pra saber QUEM está usando esta instância, pra atribuir
pedidos/produção/auditoria ao nome certo.

Vitrine de boas-vindas em 16:9 (like software desktop premium, não site):
canvas fixo 1600x900 redimensionado PROPORCIONALMENTE conforme a tela
(nunca maior que isso, só encolhe em telas pequenas — mesma lógica de
ui/app.py). Só o FUNDO é uma imagem estática (gradiente + marca d'água da
impressora a ~10% de opacidade, gerada por scripts/gerar_login_bg.py);
todo o resto — logo, textos, campo, botão, rodapé — é desenhado pelo
próprio CustomTkinter em cima, então continua nítido em qualquer
resolução. Faixas: 6% topo / 84% conteúdo (42% login + 58% marca d'água) /
10% rodapé com os 3 destaques.
"""
from __future__ import annotations
import customtkinter as ctk
from tkinter import messagebox

from core import session
from ui.theme import (SIDEBAR_BG, SIDEBAR_TEXTO, CARD_ESCURO, BORDA_ESCURA,
                      BRANCO, VERDE_GLOW, VERDE, VERDE_HOVER)
from ui import icons

RECURSOS = [
    (icons.ESCUDO, "Auditoria completa", "Todas as ações são registradas"),
    (icons.GRAFICO_CIMA, "Histórico por operador", "Consulte atividades e produções realizadas"),
    (icons.ALVO, "Produção rastreável", "Mais controle e eficiência no seu dia a dia"),
]

LARGURA_ALVO = 1600
ALTURA_ALVO = 900
TOPO_PCT = 0.06
RODAPE_PCT = 0.10
COL_ESQUERDA_PCT = 0.42
LARGURA_FORM_ALVO = 500   # "480 a 520px" — teto pra continuar elegante em monitor grande


class LoginDialog(ctk.CTkToplevel):
    def __init__(self, master, db_path: str, on_confirmado=None, **kw):
        super().__init__(master, **kw)
        self._db = db_path
        self._on_confirmado = on_confirmado

        self.title("Identificação do operador")
        # NUNCA usar self._w/self._h aqui -- Tkinter já usa `_w` internamente
        # como o path name do widget (não é "width"); sobrescrever quebra
        # qualquer chamada nativa depois (foi exatamente o que aconteceu:
        # TclError "bad window path name" no primeiro resizable() seguinte).
        self._largura, self._altura = self._centralizar(LARGURA_ALVO, ALTURA_ALVO)
        self._escala = self._largura / LARGURA_ALVO
        self.resizable(False, False)
        self.configure(fg_color=SIDEBAR_BG)
        from ui.components.titlebar import aplicar_padrao_janela
        aplicar_padrao_janela(self)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        self._montar()
        self.grab_set()
        self.after(50, self._focar)

    def _centralizar(self, w_alvo: int, h_alvo: int) -> tuple[int, int]:
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        escala = min(1.0, (sw * 0.85) / w_alvo, (sh * 0.85) / h_alvo)
        w, h = int(w_alvo * escala), int(h_alvo * escala)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        return w, h

    def _focar(self):
        self.lift()
        self.focus_force()

    # ── px()/fnt() — todo tamanho fixo passa por aqui, pra escalar junto
    # com a janela quando a tela é menor que o alvo 1600x900. ─────────────────

    def _px(self, valor: float) -> int:
        return max(1, round(valor * self._escala))

    def _fnt(self, tam: int, negrito: bool = False) -> ctk.CTkFont:
        return ctk.CTkFont("Segoe UI", max(8, round(tam * self._escala)),
                           "bold" if negrito else "normal")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _montar(self):
        fundo = self._carregar_fundo()
        if fundo:
            self._img_fundo = fundo   # referência viva (senão o GC recolhe e a imagem some)
            ctk.CTkLabel(self, image=fundo, text="").place(x=0, y=0, relwidth=1, relheight=1)

        # Painel esquerdo (login) — opaco, cobre a parte do fundo atrás dele
        # (que ali é só preto liso mesmo, a marca d'água fica só à direita).
        painel = ctk.CTkFrame(self, fg_color=SIDEBAR_BG, corner_radius=0)
        painel.place(relx=0, rely=TOPO_PCT, relwidth=COL_ESQUERDA_PCT,
                    relheight=1 - TOPO_PCT - RODAPE_PCT)

        form = ctk.CTkFrame(painel, fg_color="transparent", width=self._px(LARGURA_FORM_ALVO))
        form.pack(anchor="w", padx=self._px(56), pady=(self._px(4), 0))
        form.pack_propagate(False)

        self._montar_logo(form)
        self._montar_boas_vindas(form)
        self._montar_form(form)

        # Rodapé — faixa opaca, largura total, com separador fino acima.
        rodape = ctk.CTkFrame(self, fg_color=SIDEBAR_BG, corner_radius=0)
        rodape.place(relx=0, rely=1 - RODAPE_PCT, relwidth=1, relheight=RODAPE_PCT)
        self._montar_rodape(rodape)

    def _carregar_fundo(self):
        try:
            from infrastructure.filesystem import assets_dir
            from PIL import Image
            caminho = assets_dir() / "login_bg.png"
            if not caminho.exists():
                return None
            img = Image.open(caminho)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(self._largura, self._altura))
        except Exception:
            return None

    def _montar_logo(self, master):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(anchor="w", pady=(0, self._px(28)))

        icone = self._carregar_icone()
        if icone:
            ctk.CTkLabel(linha, image=icone, text="").pack(side="left", padx=(0, self._px(12)))
        textos = ctk.CTkFrame(linha, fg_color="transparent")
        textos.pack(side="left")
        ctk.CTkLabel(textos, text="DTF MANAGER", font=self._fnt(20, True),
                     text_color=BRANCO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(textos, text="PRO", font=self._fnt(12, True),
                     text_color=VERDE_GLOW, anchor="w").pack(anchor="w")

    def _carregar_icone(self):
        try:
            from infrastructure.filesystem import assets_dir
            from PIL import Image
            caminho = assets_dir() / "icon.png"
            if not caminho.exists():
                return None
            img = Image.open(caminho)
            tam = self._px(52)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(tam, tam))
        except Exception:
            return None

    def _montar_boas_vindas(self, master):
        ctk.CTkLabel(master, text="Bem-vindo!", font=self._fnt(12, True),
                     text_color=VERDE_GLOW, anchor="w").pack(anchor="w")
        ctk.CTkLabel(master, text="Identifique o operador",
                     font=self._fnt(26, True),
                     text_color=BRANCO, anchor="w").pack(anchor="w", pady=(2, self._px(10)))
        ctk.CTkLabel(master,
                     text="Informe seu nome para iniciar o sistema.\n"
                          "Todas as ações serão registradas e vinculadas a este operador.",
                     font=self._fnt(11), justify="left",
                     text_color=SIDEBAR_TEXTO, anchor="w").pack(anchor="w", pady=(0, self._px(24)))

    def _montar_form(self, master):
        ctk.CTkLabel(master, text="NOME DO OPERADOR",
                     font=self._fnt(9, True),
                     text_color=SIDEBAR_TEXTO, anchor="w").pack(anchor="w", pady=(0, self._px(6)))

        from infrastructure.db import operadores_repo, config_repo
        nomes = operadores_repo.listar_operadores(self._db)
        ultimo = config_repo.obter(self._db, "ultimo_operador", "")

        altura_pill = self._px(52)
        pill = ctk.CTkFrame(master, fg_color=CARD_ESCURO, corner_radius=self._px(10),
                            border_width=1, border_color=BORDA_ESCURA, height=altura_pill)
        pill.pack(fill="x")
        pill.pack_propagate(False)
        ctk.CTkLabel(pill, text=icons.CONTATO, font=icons.fonte(self._px(16)),
                     text_color=SIDEBAR_TEXTO).pack(side="left", padx=(self._px(14), self._px(6)))
        self._combo = ctk.CTkComboBox(
            pill, height=altura_pill - self._px(4), values=nomes, border_width=0,
            corner_radius=self._px(8),
            fg_color=CARD_ESCURO, text_color=BRANCO,
            button_color=VERDE_GLOW, button_hover_color=VERDE,
            dropdown_fg_color=CARD_ESCURO, dropdown_text_color=BRANCO,
            dropdown_hover_color=SIDEBAR_BG,
            font=self._fnt(13))
        self._combo.set(ultimo if ultimo else (nomes[0] if nomes else ""))
        self._combo.pack(side="left", fill="both", expand=True, padx=(0, self._px(8)))
        self._combo.bind("<Return>", lambda e: self._confirmar())

        ctk.CTkLabel(master, text="Novo por aqui? Só digitar o nome e confirmar.",
                     font=self._fnt(9), text_color=SIDEBAR_TEXTO,
                     anchor="w").pack(anchor="w", pady=(self._px(6), self._px(20)))

        ctk.CTkButton(master, text="  Entrar", height=self._px(52), corner_radius=self._px(10),
                     image=icons.imagem(icons.ENTRAR, tam=self._px(16), cor=BRANCO), compound="left",
                     font=self._fnt(13, True),
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
                     command=self._confirmar).pack(fill="x")

    def _montar_rodape(self, master):
        ctk.CTkFrame(master, fg_color=BORDA_ESCURA, height=1, corner_radius=0).pack(
            fill="x", side="top")

        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="both", expand=True, padx=self._px(56))
        for col, (ico, titulo, desc) in enumerate(RECURSOS):
            linha.grid_columnconfigure(col, weight=1)
            bloco = ctk.CTkFrame(linha, fg_color="transparent")
            bloco.grid(row=0, column=col, sticky="w", padx=(0 if col == 0 else self._px(20), 0))
            icons.rotulo(bloco, ico, titulo, tam_icone=self._px(14), tam_texto=self._px(11),
                        negrito=True, cor_icone=VERDE_GLOW, cor_texto=BRANCO).pack(anchor="w")
            ctk.CTkLabel(bloco, text=desc, font=self._fnt(9), text_color=SIDEBAR_TEXTO,
                         anchor="w", justify="left").pack(anchor="w", pady=(self._px(2), 0))

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
