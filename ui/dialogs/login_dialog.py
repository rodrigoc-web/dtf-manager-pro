"""
ui/dialogs/login_dialog.py — Abertura do programa: splash de marca (~1.6s,
automático) seguido da identificação do operador. Sem senha: ferramenta
interna da fábrica, o acesso já é controlado por posse física do
computador — o login aqui serve só pra saber QUEM está usando esta
instância, pra atribuir pedidos/produção/auditoria ao nome certo.

Abre no MESMO tamanho da janela principal (mesma conta de ui/app.py —
min(1200, sw*0.85) x min(800, sh*0.85)), não como popup pequeno: é a
primeira coisa que qualquer operador vê, então tem o mesmo porte da
janela que vem em seguida (sem salto visual na transição, igual ao
padrão de abertura de Photoshop/Illustrator/Figma/JetBrains).

Só o FUNDO é imagem estática (gradiente quase-preto + impressora como
"luz de fundo", bem grande e desfocada, ~8% opacidade — gerada por
scripts/gerar_login_bg.py); todo o resto — logo, textos, campo, botão,
rodapé — é desenhado pelo próprio CustomTkinter, então continua nítido em
qualquer resolução (só a imagem de fundo é esticada pra acompanhar).
"""
from __future__ import annotations
import customtkinter as ctk
from tkinter import messagebox

from core import session
from ui.theme import (SIDEBAR_BG, SIDEBAR_TEXTO, CARD_ESCURO, BORDA_ESCURA,
                      BRANCO, VERDE_GLOW, VERDE, VERDE_HOVER)
from ui import icons

RECURSOS = [
    (icons.ESCUDO, "Auditoria", "Todas as ações são registradas"),
    (icons.GRAFICO_CIMA, "Histórico", "Consulte atividades e produções realizadas"),
    (icons.ALVO, "Produção rastreável", "Mais controle e eficiência no seu dia a dia"),
]

LARGURA_ALVO = 1200
ALTURA_ALVO = 800
DURACAO_SPLASH_MS = 1600
MARGEM_ESQUERDA = 120


class LoginDialog(ctk.CTkToplevel):
    def __init__(self, master, db_path: str, on_confirmado=None, **kw):
        super().__init__(master, **kw)
        self._db = db_path
        self._on_confirmado = on_confirmado

        self.title("DTF MANAGER PRO")
        # NUNCA usar self._w/self._h como nome de atributo -- Tkinter já usa
        # `_w` internamente como o path name do widget; sobrescrever quebra
        # qualquer chamada nativa depois (TclError "bad window path name").
        self._largura, self._altura = self._centralizar()
        self._escala = min(self._largura / LARGURA_ALVO, self._altura / ALTURA_ALVO)
        self._escala_ui = max(self._escala, 0.85)   # piso p/ texto/controles não ficarem ilegíveis
        self.resizable(False, False)
        self.configure(fg_color=SIDEBAR_BG)
        from ui.components.titlebar import aplicar_padrao_janela
        aplicar_padrao_janela(self)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        self._img_fundo = self._carregar_fundo()
        if self._img_fundo:
            ctk.CTkLabel(self, image=self._img_fundo, text="").place(
                x=0, y=0, relwidth=1, relheight=1)

        self._conteudo: ctk.CTkFrame | None = None
        self._montar_splash()
        self.grab_set()
        self.after(50, self._focar)
        self.after(DURACAO_SPLASH_MS, self._montar_login)

    def _centralizar(self) -> tuple[int, int]:
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = max(1000, min(LARGURA_ALVO, int(sw * 0.85)))
        h = max(650, min(ALTURA_ALVO, int(sh * 0.85)))
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        return w, h

    def _focar(self):
        self.lift()
        self.focus_force()

    def _carregar_fundo(self):
        try:
            from infrastructure.filesystem import assets_dir
            from PIL import Image
            caminho = assets_dir() / "login_bg.png"
            if not caminho.exists():
                return None
            img = Image.open(caminho)
            return ctk.CTkImage(light_image=img, dark_image=img,
                                size=(self._largura, self._altura))
        except Exception:
            return None

    # ── px()/fnt() — tamanhos escalam com a janela; texto/controles têm
    # piso (escala_ui) pra não ficarem pequenos demais numa tela menor. ──────

    def _px(self, valor: float) -> int:
        return max(1, round(valor * self._escala_ui))

    def _fnt(self, tam: int, negrito: bool = False) -> ctk.CTkFont:
        return ctk.CTkFont("Segoe UI", max(9, round(tam * self._escala_ui)),
                           "bold" if negrito else "normal")

    def _limpar_conteudo(self):
        if self._conteudo is not None:
            self._conteudo.destroy()
        self._conteudo = ctk.CTkFrame(self, fg_color="transparent")
        self._conteudo.place(x=0, y=0, relwidth=1, relheight=1)
        return self._conteudo

    # ── Splash (logo grande centralizado + barra de carregamento) ───────────

    def _montar_splash(self):
        raiz = self._limpar_conteudo()
        raiz.grid_columnconfigure(0, weight=1)
        raiz.grid_rowconfigure(0, weight=1)
        raiz.grid_rowconfigure(2, weight=1)

        centro = ctk.CTkFrame(raiz, fg_color="transparent")
        centro.grid(row=1, column=0)

        icone = self._carregar_icone(self._px(72))
        if icone:
            ctk.CTkLabel(centro, image=icone, text="").pack(pady=(0, self._px(18)))
        ctk.CTkLabel(centro, text="DTF MANAGER PRO", font=self._fnt(30, True),
                     text_color=BRANCO).pack()
        ctk.CTkLabel(centro, text="Sistema de gestão para produção DTF",
                     font=self._fnt(13), text_color=SIDEBAR_TEXTO).pack(pady=(self._px(4), self._px(34)))

        largura_barra = self._px(320)
        self._barra_splash = ctk.CTkProgressBar(
            centro, width=largura_barra, height=self._px(4),
            progress_color=VERDE_GLOW, fg_color=BORDA_ESCURA, corner_radius=2)
        self._barra_splash.set(0)
        self._barra_splash.pack()
        ctk.CTkLabel(centro, text="Carregando...", font=self._fnt(10),
                     text_color=SIDEBAR_TEXTO).pack(pady=(self._px(8), 0))

        self._animar_splash(0)

    def _animar_splash(self, passo: int):
        # Fechar a janela durante os ~1.6s do splash é um caso real (usuário
        # pode clicar no X a qualquer momento) — sem essa guarda, o after()
        # reagendado dispara contra um Toplevel já destruído e derruba com
        # TclError. self.winfo_exists() cobre a janela inteira; o resto cobre
        # o caso de já ter trocado pra tela de login antes do fim da animação.
        if not self.winfo_exists() or self._conteudo is None or not self._barra_splash.winfo_exists():
            return
        total_passos = 32
        self._barra_splash.set(min(1.0, passo / total_passos))
        if passo < total_passos:
            self.after(DURACAO_SPLASH_MS // total_passos, lambda: self._animar_splash(passo + 1))

    # ── Login (identificação do operador) ────────────────────────────────────

    def _montar_login(self):
        if not self.winfo_exists():
            return   # fechado durante o splash — nada a fazer
        raiz = self._limpar_conteudo()
        raiz.grid_columnconfigure(0, weight=1)
        raiz.grid_rowconfigure(0, weight=1)   # espaçador de cima
        raiz.grid_rowconfigure(1, weight=0)   # bloco de conteúdo (centralizado)
        raiz.grid_rowconfigure(2, weight=1)   # espaçador de baixo

        # Sem width fixo + grid_propagate(False) aqui: isso trava também a
        # ALTURA (o frame não teria como crescer pra caber os filhos, ficaria
        # colapsado a ~1px). A largura de ~480px vem de baixo pra cima — o
        # pill/botão dentro é que têm width fixo; o frame só acompanha.
        form = ctk.CTkFrame(raiz, fg_color="transparent")
        form.grid(row=1, column=0, sticky="w", padx=(self._px(MARGEM_ESQUERDA), 0))

        self._montar_logo(form)
        self._montar_boas_vindas(form)
        self._montar_campo(form)

        rodape = ctk.CTkFrame(raiz, fg_color="transparent")
        rodape.grid(row=3, column=0, sticky="ew")
        raiz.grid_rowconfigure(3, weight=0)
        self._montar_rodape(rodape)

        self.after(80, lambda: self._combo.focus_set() if hasattr(self, "_combo") else None)

    def _montar_logo(self, master):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(anchor="w", pady=(0, self._px(30)))

        icone = self._carregar_icone(self._px(60))
        if icone:
            ctk.CTkLabel(linha, image=icone, text="").pack(side="left", padx=(0, self._px(14)))
        textos = ctk.CTkFrame(linha, fg_color="transparent")
        textos.pack(side="left")
        ctk.CTkLabel(textos, text="DTF MANAGER", font=self._fnt(24, True),
                     text_color=BRANCO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(textos, text="PRO", font=self._fnt(14, True),
                     text_color=VERDE_GLOW, anchor="w").pack(anchor="w")

    def _carregar_icone(self, tam: int):
        try:
            from infrastructure.filesystem import assets_dir
            from PIL import Image
            caminho = assets_dir() / "icon.png"
            if not caminho.exists():
                return None
            img = Image.open(caminho)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(tam, tam))
        except Exception:
            return None

    def _montar_boas_vindas(self, master):
        ctk.CTkLabel(master, text="Identifique o operador",
                     font=self._fnt(34, True),
                     text_color=BRANCO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(master,
                     text="Informe seu nome para iniciar o sistema.\n"
                          "Todas as ações serão registradas e vinculadas a este operador.",
                     font=self._fnt(15), justify="left",
                     text_color=SIDEBAR_TEXTO, anchor="w").pack(anchor="w", pady=(self._px(10), self._px(28)))

    def _montar_campo(self, master):
        from infrastructure.db import operadores_repo, config_repo
        nomes = operadores_repo.listar_operadores(self._db)
        ultimo = config_repo.obter(self._db, "ultimo_operador", "")

        # width fixo nos DOIS (pill e botão, abaixo) -- é o que dá a largura
        # de ~480px consistente ao formulário; o frame "master" que os
        # envolve não tem width próprio, só acompanha o filho mais largo.
        largura_campo = self._px(480)
        altura_pill = self._px(52)
        pill = ctk.CTkFrame(master, fg_color=CARD_ESCURO, corner_radius=self._px(10),
                            border_width=1, border_color=BORDA_ESCURA,
                            width=largura_campo, height=altura_pill)
        pill.pack(anchor="w")
        pill.pack_propagate(False)
        ctk.CTkLabel(pill, text=icons.CONTATO, font=icons.fonte(self._px(17)),
                     text_color=SIDEBAR_TEXTO).pack(side="left", padx=(self._px(16), self._px(8)))
        self._combo = ctk.CTkComboBox(
            pill, height=altura_pill - self._px(4), values=nomes, border_width=0,
            corner_radius=self._px(8),
            fg_color=CARD_ESCURO, text_color=BRANCO,
            button_color=VERDE_GLOW, button_hover_color=VERDE,
            dropdown_fg_color=CARD_ESCURO, dropdown_text_color=BRANCO,
            dropdown_hover_color=SIDEBAR_BG,
            font=self._fnt(14))
        self._combo.set(ultimo if ultimo else (nomes[0] if nomes else ""))
        self._combo.pack(side="left", fill="both", expand=True, padx=(0, self._px(10)))
        self._combo.bind("<Return>", lambda e: self._confirmar())

        ctk.CTkLabel(master, text="Novo por aqui? Só digitar o nome e confirmar.",
                     font=self._fnt(10), text_color=SIDEBAR_TEXTO,
                     anchor="w").pack(anchor="w", pady=(self._px(8), self._px(22)))

        ctk.CTkButton(master, text="  Entrar", width=largura_campo, height=self._px(52),
                     corner_radius=self._px(10),
                     image=icons.imagem(icons.ENTRAR, tam=self._px(17), cor=BRANCO), compound="left",
                     font=self._fnt(14, True),
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
                     command=self._confirmar).pack(anchor="w")

    def _montar_rodape(self, master):
        ctk.CTkFrame(master, fg_color=BORDA_ESCURA, height=1, corner_radius=0).pack(fill="x")

        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x", padx=self._px(MARGEM_ESQUERDA), pady=self._px(20))
        for col, (ico, titulo, desc) in enumerate(RECURSOS):
            linha.grid_columnconfigure(col * 2, weight=1)
            if col > 0:
                ctk.CTkFrame(linha, fg_color=BORDA_ESCURA, width=1).grid(
                    row=0, column=col * 2 - 1, sticky="ns", padx=self._px(24))
            bloco = ctk.CTkFrame(linha, fg_color="transparent")
            bloco.grid(row=0, column=col * 2, sticky="w")
            icons.rotulo(bloco, ico, titulo, tam_icone=self._px(16), tam_texto=self._px(12),
                        negrito=True, cor_icone=VERDE_GLOW, cor_texto=BRANCO).pack(anchor="w")
            ctk.CTkLabel(bloco, text=desc, font=self._fnt(10), text_color=SIDEBAR_TEXTO,
                         anchor="w", justify="left").pack(anchor="w", pady=(self._px(3), 0))

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
