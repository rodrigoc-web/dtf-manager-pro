"""
ui/dialogs/login_dialog.py — Abertura do programa: splash de marca (~1.6s,
automático) seguido da identificação do operador. Sem senha: ferramenta
interna da fábrica, o acesso já é controlado por posse física do
computador — o login aqui serve só pra saber QUEM está usando esta
instância, pra atribuir pedidos/produção/auditoria ao nome certo.

A tela de login segue à risca o mockup de referência do usuário
("POP UP INICIAL.png"): logo grande no topo, "Bem-vindo!" + título +
subtítulo, campo com ícone de pessoa, botão "Entrar", 3 destaques no
rodapé e a impressora como ilustração na coluna direita — conteúdo
ancorado no topo (não centralizado verticalmente), exatamente como no
mockup.

Janela com tamanho FIXO (1000x680 — o mesmo canvas em que o mockup foi
desenhado), não o tamanho da janela principal: usar o tamanho do app
(bem maior, proporção diferente) foi o que fez o conteúdo ficar pequeno
e sobrando espaço morto preto ao redor — o oposto de "idêntico ao
mockup". Só encolhe (proporcionalmente) se a tela do usuário for menor
que 1000x680 + uma folga pequena; na grande maioria das telas reais
(inclusive notebook comum) isso nunca dispara — abre no tamanho exato do
mockup, sem escala nenhuma.

IDENTIFICAÇÃO OBRIGATÓRIA: fechar esta janela sem escolher um operador
(X, Alt+F4) não deixa passar batido — quem chama este dialog no 1º login
(ui/app.py) confere se um operador foi definido depois que a janela
fecha, e encerra o programa se não foi. "Trocar operador" (já dentro do
app) é a única chamada que tolera fechar sem trocar — aí mantém quem já
estava logado.
"""
from __future__ import annotations
import customtkinter as ctk
from tkinter import messagebox

from core import session
from ui.theme import (SIDEBAR_BG, SIDEBAR_TEXTO, SIDEBAR_HOVER, CARD_ESCURO, BORDA_ESCURA,
                      BRANCO, VERDE_GLOW, VERDE, VERDE_HOVER, VERDE_PRESSIONADO, VERDE_ESCURO)
from ui import icons


def _clarear(cor_hex: str, alpha: float) -> str:
    """Clareia cor_hex misturando branco na proporção alpha (0-1) -- usado só
    pra gerar a variante "hover" do gradiente do botão Entrar."""
    r, g, b = (int(cor_hex[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (round(c + (255 - c) * alpha) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"

RECURSOS = [
    ("login_icon_auditoria.png", "Auditoria completa", "Todas as ações são\nregistradas"),
    ("login_icon_historico.png", "Histórico por operador", "Consulte atividades e\nproduções realizadas"),
    ("login_icon_producao.png", "Produção rastreável", "Mais controle e eficiência\nno seu dia a dia"),
]

LARGURA_ALVO = 1000
# 680 era o canvas exato do mockup original, mas com fontes/DPI reais o
# conteúdo (logo + textos + pill + botão + rodapé de 2 linhas) passa disso
# -- a 2ª linha de cada descrição no rodapé ficava cortada fora da janela.
# 40px a mais é o suficiente pra caber tudo sem cortar nada.
ALTURA_ALVO = 720
DURACAO_SPLASH_MS = 1600


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

        self._conteudo: ctk.CTkFrame | None = None
        self._montar_splash()
        self.grab_set()
        self.after(50, self._focar)
        self.after(DURACAO_SPLASH_MS, self._montar_login)

    def _centralizar(self) -> tuple[int, int]:
        # Folga pequena (não os 15% usados na janela principal) — o alvo já
        # é um tamanho compacto de propósito; só entra em jogo em telas
        # genuinamente pequenas, não deveria disparar em nenhum notebook comum.
        FOLGA_PX = 60
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = max(760, min(LARGURA_ALVO, sw - FOLGA_PX))
        h = max(520, min(ALTURA_ALVO, sh - FOLGA_PX))
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        return w, h

    def _focar(self):
        self.lift()
        self.focus_force()

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

    # ── Login (identificação do operador) — layout fiel ao mockup, ancorado
    # no topo (não centralizado verticalmente). ─────────────────────────────

    def _montar_login(self):
        if not self.winfo_exists():
            return   # fechado durante o splash — nada a fazer
        raiz = self._limpar_conteudo()
        raiz.grid_columnconfigure(0, weight=3)
        raiz.grid_columnconfigure(1, weight=2)
        raiz.grid_rowconfigure(0, weight=1)

        esquerda = ctk.CTkFrame(raiz, fg_color="transparent")
        esquerda.grid(row=0, column=0, sticky="nsew",
                      padx=(self._px(56), self._px(24)), pady=(self._px(32), self._px(26)))
        esquerda.grid_columnconfigure(0, weight=1)

        self._montar_logo(esquerda)
        self._montar_boas_vindas(esquerda)
        self._montar_form(esquerda)
        self._montar_recursos(esquerda)

        self._montar_ilustracao(raiz)

        self.after(80, lambda: self._combo.focus_set() if hasattr(self, "_combo") else None)

    def _montar_logo(self, master):
        # Logo = a IMAGEM de verdade (assets/logo_completo.png), não texto
        # recriado com fonte de sistema — nenhuma fonte instalada reproduz a
        # tipografia customizada do logo original, então só a imagem garante
        # ficar idêntico ao arquivo que o usuário forneceu.
        logo = self._carregar_logo_completo(self._px(280))
        if logo:
            ctk.CTkLabel(master, image=logo, text="").pack(
                anchor="w", pady=(0, self._px(34)))

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

    def _carregar_logo_completo(self, largura: int):
        try:
            from infrastructure.filesystem import assets_dir
            from PIL import Image
            caminho = assets_dir() / "logo_completo.png"
            if not caminho.exists():
                return None
            img = Image.open(caminho)
            altura = round(largura * img.height / img.width)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(largura, altura))
        except Exception:
            return None

    def _montar_boas_vindas(self, master):
        ctk.CTkLabel(master, text="Bem-vindo!", font=self._fnt(12, True),
                     text_color=VERDE_GLOW, anchor="w").pack(anchor="w")
        ctk.CTkLabel(master, text="Identifique o operador",
                     font=self._fnt(27, True),
                     text_color=BRANCO, anchor="w").pack(anchor="w", pady=(2, self._px(10)))
        ctk.CTkLabel(master,
                     text="Informe seu nome para iniciar o sistema.\n"
                          "Todas as ações serão registradas e vinculadas a este operador.",
                     font=self._fnt(11), justify="left",
                     text_color=SIDEBAR_TEXTO, anchor="w").pack(anchor="w", pady=(0, self._px(26)))

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
            dropdown_hover_color=SIDEBAR_HOVER,
            font=self._fnt(13))
        self._combo.set(ultimo if ultimo else (nomes[0] if nomes else ""))
        self._combo.pack(side="left", fill="both", expand=True, padx=(0, self._px(8)))
        self._combo.bind("<Return>", lambda e: self._confirmar())

        ctk.CTkLabel(master, text="Novo por aqui? Só digitar o nome e confirmar.",
                     font=self._fnt(9), text_color=SIDEBAR_TEXTO,
                     anchor="w").pack(anchor="w", pady=(self._px(6), self._px(22)))

        self._montar_botao_entrar(master)

        ctk.CTkFrame(master, fg_color=BORDA_ESCURA, height=1, corner_radius=0).pack(
            fill="x", pady=(0, self._px(22)))

    def _montar_botao_entrar(self, master):
        """Botão "Entrar" com gradiente horizontal (hover→verde→pressionado→
        escuro, os 4 tons oficiais da marca) em vez de preenchimento sólido —
        CTkButton não tem parâmetro de gradiente, então isso é um CTkLabel
        com uma única imagem PIL (fundo + ícone + texto já desenhados juntos)
        como conteúdo. Um CTkFrame "transparent" sobreposto a um CTkLabel de
        imagem NÃO fica transparente de verdade (vira um retângulo sólido
        cobrindo o gradiente) -- por isso ícone e texto são desenhados DENTRO
        da mesma imagem, não como widgets-filho por cima. Como o diálogo é de
        tamanho FIXO (resizable(False, False)), dá pra gerar a imagem uma
        única vez, logo depois do primeiro layout, sem recalcular em resize."""
        altura = self._px(52)
        raio = self._px(10)
        botao = ctk.CTkLabel(master, text="", height=altura, corner_radius=0)
        botao.pack(fill="x", pady=(0, self._px(26)))

        def _aplicar_gradiente():
            largura = botao.winfo_width()
            if largura <= 1:
                self.after(10, _aplicar_gradiente)
                return
            self._img_entrar_normal = self._imagem_botao_entrar(largura, altura, raio, hover=False)
            self._img_entrar_hover  = self._imagem_botao_entrar(largura, altura, raio, hover=True)
            botao.configure(image=self._img_entrar_normal)
        self.after(1, _aplicar_gradiente)

        botao.configure(cursor="hand2")
        botao.bind("<Button-1>", lambda e: self._confirmar())
        botao.bind("<Enter>", lambda e: botao.configure(image=self._img_entrar_hover))
        botao.bind("<Leave>", lambda e: botao.configure(image=self._img_entrar_normal))

    def _imagem_botao_entrar(self, largura: int, altura: int, raio: int, hover: bool) -> "ctk.CTkImage":
        from PIL import Image, ImageDraw, ImageFont
        escala = 3
        w, h, r = largura * escala, altura * escala, raio * escala

        paradas = [VERDE_HOVER, VERDE, VERDE_PRESSIONADO, VERDE_ESCURO]
        if hover:
            paradas = [_clarear(c, 0.12) for c in paradas]
        cores = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in paradas]
        n = len(cores) - 1
        linha = Image.new("RGB", (w, 1))
        for x in range(w):
            pos = x / max(1, w - 1) * n
            i = min(int(pos), n - 1)
            t = pos - i
            c0, c1 = cores[i], cores[i + 1]
            linha.putpixel((x, 0), tuple(round(c0[k] + (c1[k] - c0[k]) * t) for k in range(3)))
        gradiente = linha.resize((w, h))
        mascara = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mascara).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
        saida = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        saida.paste(gradiente, (0, 0), mascara)

        draw = ImageDraw.Draw(saida)
        tam_fonte_texto = int(self._px(13) * escala)
        fonte_texto = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", tam_fonte_texto)
        fonte_icone = ImageFont.truetype(icons._FONTE_PATH, int(self._px(16) * escala))
        texto = "Entrar"
        bbox_texto = draw.textbbox((0, 0), texto, font=fonte_texto)
        bbox_icone = draw.textbbox((0, 0), icons.ENTRAR, font=fonte_icone)
        largura_texto = bbox_texto[2] - bbox_texto[0]
        largura_icone = bbox_icone[2] - bbox_icone[0]
        espaco = self._px(8) * escala
        largura_total = largura_icone + espaco + largura_texto
        x_icone = (w - largura_total) // 2
        x_texto = x_icone + largura_icone + espaco
        # Branco, não TEXTO_SOBRE_VERDE (escuro) -- o asset de referência do
        # usuário ("icon botao entrar.png") mostra texto branco sobre esse
        # gradiente específico; diferente dos outros botões verdes do app
        # (fundo chapado no lima vibrante, aí sim precisa de texto escuro),
        # esse gradiente é mais escuro na média e o branco tem contraste bom.
        draw.text((x_icone, h // 2), icons.ENTRAR, font=fonte_icone,
                  fill=BRANCO, anchor="lm")
        draw.text((x_texto, h // 2), texto, font=fonte_texto,
                  fill=BRANCO, anchor="lm")

        saida = saida.resize((largura, altura), Image.LANCZOS)
        return ctk.CTkImage(light_image=saida, dark_image=saida, size=(largura, altura))

    def _montar_recursos(self, master):
        linha = ctk.CTkFrame(master, fg_color="transparent")
        linha.pack(fill="x")
        for col, (arquivo_icone, titulo, desc) in enumerate(RECURSOS):
            linha.grid_columnconfigure(col, weight=1)
            bloco = ctk.CTkFrame(linha, fg_color="transparent")
            bloco.grid(row=0, column=col, sticky="nw", padx=(0 if col == 0 else self._px(14), 0))
            icone = self._carregar_icone_recurso(arquivo_icone, self._px(32))
            if icone:
                ctk.CTkLabel(bloco, image=icone, text="").pack(anchor="w", pady=(0, self._px(8)))
            ctk.CTkLabel(bloco, text=titulo, font=self._fnt(11, True),
                         text_color=BRANCO, anchor="w", justify="left",
                         wraplength=self._px(150)).pack(anchor="w")
            ctk.CTkLabel(bloco, text=desc, font=self._fnt(9),
                         text_color=SIDEBAR_TEXTO, anchor="w", justify="left").pack(anchor="w", pady=(self._px(2), 0))

    def _carregar_icone_recurso(self, nome_arquivo: str, tam: int):
        try:
            from infrastructure.filesystem import assets_dir
            from PIL import Image
            caminho = assets_dir() / nome_arquivo
            if not caminho.exists():
                return None
            img = Image.open(caminho)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(tam, tam))
        except Exception:
            return None

    def _montar_ilustracao(self, raiz):
        direita = ctk.CTkFrame(raiz, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="nsew")
        try:
            from infrastructure.filesystem import assets_dir
            from PIL import Image
            caminho = assets_dir() / "login_ilustracao.png"
            if caminho.exists():
                img = Image.open(caminho)
                # Contain-fit (preserva proporção) dentro de uma caixa de
                # tam×tam -- forçar um CTkImage quadrado direto distorcia
                # qualquer imagem que não fosse exatamente 1:1 (só não dava
                # pra notar antes porque o asset antigo era 738×738).
                tam = self._px(440)
                escala = min(tam / img.width, tam / img.height)
                largura = round(img.width * escala)
                altura = round(img.height * escala)
                self._img_ilustracao = ctk.CTkImage(light_image=img, dark_image=img,
                                                    size=(largura, altura))
                ctk.CTkLabel(direita, image=self._img_ilustracao, text="").place(
                    relx=0.5, rely=0.5, anchor="center")
        except Exception:
            pass

    # ── Ações ────────────────────────────────────────────────────────────────

    def _confirmar(self):
        nome = self._combo.get().strip()
        if not nome:
            messagebox.showwarning("Campo obrigatório", "Digite ou escolha seu nome.", parent=self)
            return

        from infrastructure.db import operadores_repo, config_repo, eventos_repo
        operadores_repo.inserir_operador(self._db, nome)
        config_repo.definir(self._db, "ultimo_operador", nome)
        session.definir_operador(nome)
        eventos_repo.registrar(self._db, "LOGIN", nome)

        if self._on_confirmado:
            self._on_confirmado(nome)
        self.destroy()

    def _fechar(self):
        # Fechar sem escolher mantém o operador atual (troca) ou vazio (1º
        # login) — nunca fabrica um nome, só segue sem identificação. É
        # ui/app.py quem decide o que fazer com isso: no 1º login, fechar
        # sem identificar encerra o programa inteiro (identificação é
        # obrigatória); em "trocar operador", só mantém quem já estava logado.
        self.destroy()
