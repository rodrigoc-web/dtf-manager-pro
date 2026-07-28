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
                      BRANCO, PRETO, VERDE_GLOW, VERDE, VERDE_HOVER, VERDE_PRESSIONADO, VERDE_ESCURO)
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
# 40px a mais é o suficiente pra caber tudo sem cortar nada. Só usado como
# referência de proporção (LARGURA_ALVO/ALTURA_ALVO) pro cálculo de escala
# -- o tamanho real da janela agora vem de FRACAO_LARGURA_TELA, não daqui.
ALTURA_ALVO = 850
# A janela era um tamanho fixo em pixels (1000×720) igual em qualquer
# monitor -- ficava enorme numa tela de notebook comum (ex.: 1366×768,
# ocupava quase a tela toda). Agora o tamanho é uma fração da tela do
# usuário, preservando a mesma proporção do design (720/1000).
FRACAO_LARGURA_TELA = 0.4   # simples/pequena-média (sem ilustração de fundo)
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
        # Piso bem mais baixo que antes (era 0.85): a janela agora É PRA SER
        # menor de propósito (proporcional à tela do usuário), então nada
        # deveria forçar o conteúdo de volta a um tamanho quase original --
        # só existe pra evitar texto ilegível em telas realmente minúsculas.
        self._escala_ui = max(self._escala, 0.6)
        # Habilita maximizar/redimensionar (pedido do usuário) -- o Windows
        # só libera o botão de maximizar no title bar quando resizable=True
        # nos dois eixos, não tem como ligar só o botão sem também liberar
        # arrastar a borda. NOTA: o conteúdo (fontes, ícones, paddings) usa
        # tamanhos fixos em px calculados uma única vez em _centralizar/
        # _escala -- maximizar/redimensionar NÃO recalcula esses tamanhos,
        # só estica a grade (colunas ficam mais largas, mais espaço vazio
        # em volta do conteúdo). Não é um layout responsivo de verdade;
        # isso exigiria reconstruir os widgets a cada resize.
        self.resizable(True, True)
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
        # Tamanho proporcional à tela do usuário (metade da largura), não
        # mais um pixel fixo -- num notebook pequeno a janela fica pequena
        # também, num monitor grande ela cresce junto, sempre na mesma
        # proporção do design (720/1000). Pisos (640×460) só entram em jogo
        # em telas realmente minúsculas, pra não ficar ilegível.
        FOLGA_PX = 60
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = round(sw * FRACAO_LARGURA_TELA)
        h = round(w * (ALTURA_ALVO / LARGURA_ALVO))
        w = max(640, min(w, sw - FOLGA_PX))
        h = max(460, min(h, sh - FOLGA_PX))
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
        # Versão simplificada TEMPORÁRIA (pedido do usuário) -- sem rodapé
        # de recursos e sem ilustração de fundo, só uma coluna, até ele
        # montar o design de verdade no Photoshop. _montar_recursos e
        # _montar_ilustracao continuam definidos (não apagados) pra
        # religar rápido quando o PSD chegar.
        raiz.grid_columnconfigure(0, weight=1)
        raiz.grid_rowconfigure(0, weight=1)

        esquerda = ctk.CTkFrame(raiz, fg_color="transparent")
        esquerda.grid(row=0, column=0, sticky="nsew",
                      padx=(self._px(48), self._px(48)), pady=(self._px(32), self._px(26)))
        esquerda.grid_columnconfigure(0, weight=1)
        self._esquerda = esquerda   # usado por _ajustar_altura_se_necessario

        # Cabeçalho: boas-vindas à esquerda, logo à direita, lado a lado --
        # não mais logo empilhada em cima do texto (pedido do usuário,
        # visto ao redimensionar a janela).
        topo = ctk.CTkFrame(esquerda, fg_color="transparent")
        topo.pack(fill="x", pady=(0, self._px(26)))
        topo.grid_columnconfigure(0, weight=1)

        bloco_boas_vindas = ctk.CTkFrame(topo, fg_color="transparent")
        bloco_boas_vindas.grid(row=0, column=0, sticky="w")
        self._montar_boas_vindas(bloco_boas_vindas)

        # _montar_logo empacota (.pack) dentro do master que recebe -- não
        # dá pra chamar direto com `topo` (já tem um filho gerenciado por
        # .grid, misturar pack/grid no mesmo container derruba com TclError).
        # Por isso um frame dedicado só pro logo, esse sim posicionado via
        # grid ao lado do bloco de boas-vindas.
        bloco_logo = ctk.CTkFrame(topo, fg_color="transparent")
        bloco_logo.grid(row=0, column=1, sticky="e", padx=(self._px(20), 0))
        self._montar_logo(bloco_logo)

        self._montar_form(esquerda)

        self.after(80, lambda: self._combo.focus_set() if hasattr(self, "_combo") else None)
        self.after(50, lambda: self._ajustar_altura_se_necessario(tentativas=4))

    def _ajustar_altura_se_necessario(self, tentativas: int):
        """Ajusta a altura da janela pro tamanho REAL do conteúdo, pra cima
        OU pra baixo -- não só uma rede de segurança contra corte (já
        aconteceu duas vezes: altura fixa 680px insuficiente; depois a
        fração de tela combinada com o piso de fonte de 9pt não encolhendo
        junto), mas também contra o oposto, sobra de espaço morto embaixo
        quando ALTURA_ALVO é mais generoso que o necessário. Em vez de
        caçar mais um número mágico, mede a posição real do widget mais
        baixo depois do layout e faz a janela abraçar exatamente esse
        conteúdo (+ uma margem pequena) -- funciona em qualquer tela, com
        qualquer combinação de fontes/paddings.

        Título com wraplength (ex.: "Histórico por operador" quebrando pra
        2 linhas) só termina de reajustar a própria altura depois de mais
        um ciclo do event loop -- por isso mede de novo (até `tentativas`
        vezes) depois de cada correção, em vez de confiar numa única medição.

        Mede só a coluna ESQUERDA (conteúdo de tamanho fixo), nunca a
        janela inteira -- a ilustração da direita é "elástica" (contain-fit
        dentro da altura que a coluna dela receber), então seu próprio
        fundo sempre acompanha a altura atual da janela. Medir a janela
        inteira criava um loop: aumenta a janela -> ilustração cresce
        junto -> "conteúdo mais baixo" sobe de novo -> aumenta de novo,
        sem nunca convergir num tamanho estável."""
        if not self.winfo_exists() or tentativas <= 0:
            return
        self.update_idletasks()

        def _mais_baixo(widget) -> int:
            y1 = widget.winfo_rooty() + widget.winfo_height()
            for filho in widget.winfo_children():
                y1 = max(y1, _mais_baixo(filho))
            return y1

        topo_janela = self.winfo_rooty()
        fundo_conteudo = _mais_baixo(self._esquerda)
        margem = self._px(20)
        altura_ideal = fundo_conteudo - topo_janela + margem

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        altura_ideal = max(460, min(altura_ideal, sh - 60))
        if abs(altura_ideal - self._altura) > 2:
            self._altura = altura_ideal
            x = self.winfo_x()
            y = max(10, (sh - altura_ideal) // 2)
            self.geometry(f"{self._largura}x{altura_ideal}+{x}+{y}")
        self.after(50, lambda: self._ajustar_altura_se_necessario(tentativas - 1))

    def _montar_logo(self, master):
        # Logo = a IMAGEM de verdade (assets/logo_completo.png), não texto
        # recriado com fonte de sistema — nenhuma fonte instalada reproduz a
        # tipografia customizada do logo original, então só a imagem garante
        # ficar idêntico ao arquivo que o usuário forneceu.
        logo = self._carregar_logo_completo(self._px(200))
        if logo:
            ctk.CTkLabel(master, image=logo, text="").pack(anchor="e")

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
                     text_color=SIDEBAR_TEXTO, anchor="w").pack(anchor="w")

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
            button_color=CARD_ESCURO, button_hover_color=SIDEBAR_HOVER,
            dropdown_fg_color=CARD_ESCURO, dropdown_text_color=BRANCO,
            dropdown_hover_color=SIDEBAR_HOVER,
            font=self._fnt(13))
        self._combo.set(ultimo if ultimo else (nomes[0] if nomes else ""))
        self._combo.pack(side="left", fill="both", expand=True, padx=(0, self._px(8)))
        self._combo.bind("<Return>", lambda e: self._confirmar())
        self._sobrepor_seta_dropdown(altura_pill - self._px(4))

        ctk.CTkLabel(master, text="Novo por aqui? Só digitar o nome e confirmar.",
                     font=self._fnt(9), text_color=SIDEBAR_TEXTO,
                     anchor="w").pack(anchor="w", pady=(self._px(6), self._px(22)))

        self._montar_botao_entrar(master)

        ctk.CTkFrame(master, fg_color=BORDA_ESCURA, height=1, corner_radius=0).pack(
            fill="x", pady=(0, self._px(22)))

    def _sobrepor_seta_dropdown(self, lado_botao: int):
        """CTkComboBox desenha a própria seta internamente num Canvas (não
        aceita uma imagem customizada por parâmetro) -- o botão quadrado do
        lado direito tem sempre lado == altura do combo. Em vez de mexer no
        widget nativo, sobrepõe um label com o ícone de verdade do usuário
        por cima dessa área, e repassa o clique pro método interno que abre
        o dropdown (mesmo efeito de clicar na seta original, agora escondida
        atrás do nosso ícone). O ícone do usuário já É verde (um chevron
        fino) -- pensado pra ficar sobre um fundo escuro, não sobre um
        quadrado verde sólido (o botão nativo virou CARD_ESCURO por isso,
        senão verde-sobre-verde ficava invisível). Fundo do próprio ícone é
        preto (pedido explícito do usuário), não o CARD_ESCURO usado no
        resto do pill."""
        icone = self._carregar_icone_dropdown(self._px(18))
        if not icone:
            return
        overlay = ctk.CTkLabel(self._combo, image=icone, text="",
                               fg_color=PRETO, corner_radius=self._px(8),
                               width=lado_botao, height=lado_botao)
        overlay.place(relx=1.0, rely=0.5, anchor="e")
        overlay.configure(cursor="hand2")
        overlay.bind("<Button-1>", lambda e: self._combo._open_dropdown_menu())
        overlay.bind("<Enter>", lambda e: overlay.configure(fg_color=SIDEBAR_HOVER))
        overlay.bind("<Leave>", lambda e: overlay.configure(fg_color=PRETO))

    def _carregar_icone_dropdown(self, tam: int):
        try:
            from infrastructure.filesystem import assets_dir
            from PIL import Image
            caminho = assets_dir() / "login_icon_dropdown.png"
            if not caminho.exists():
                return None
            img = Image.open(caminho)
            escala = min(tam / img.width, tam / img.height)
            largura = round(img.width * escala)
            altura = round(img.height * escala)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(largura, altura))
        except Exception:
            return None

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
        n = len(RECURSOS)
        for col, (arquivo_icone, titulo, desc) in enumerate(RECURSOS):
            # Colunas pares = conteúdo, ímpares = linha divisora fina entre
            # os blocos -- bate com a referência (linha vertical separando
            # "Auditoria completa" / "Histórico por operador" / "Produção
            # rastreável").
            col_grid = col * 2
            linha.grid_columnconfigure(col_grid, weight=1)
            bloco = ctk.CTkFrame(linha, fg_color="transparent")
            bloco.grid(row=0, column=col_grid, sticky="nw", padx=(0, self._px(14)))
            # Ícone ao lado do texto (não empilhado em cima) -- bate com o
            # mockup de referência: ícone à esquerda, título+descrição
            # empilhados à direita dele, os dois verticalmente centralizados
            # um em relação ao outro.
            icone = self._carregar_icone_recurso(arquivo_icone, self._px(30))
            if icone:
                ctk.CTkLabel(bloco, image=icone, text="").pack(side="left", anchor="n", padx=(0, self._px(10)))
            textos = ctk.CTkFrame(bloco, fg_color="transparent")
            textos.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(textos, text=titulo, font=self._fnt(11, True),
                         text_color=BRANCO, anchor="w", justify="left",
                         wraplength=self._px(95)).pack(anchor="w")
            ctk.CTkLabel(textos, text=desc, font=self._fnt(9),
                         text_color=SIDEBAR_TEXTO, anchor="w", justify="left").pack(anchor="w", pady=(self._px(2), 0))
            if col < n - 1:
                divisor = ctk.CTkFrame(linha, fg_color=BORDA_ESCURA, width=1)
                divisor.grid(row=0, column=col_grid + 1, sticky="ns", padx=(0, self._px(14)))

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

        def _carregar():
            # Precisa do tamanho REAL da coluna "direita" já renderizado --
            # um tam fixo (self._px(440)) podia passar da largura de verdade
            # dessa coluna (mais estreita que os 2/5 do grid sugerem, com os
            # paddings), cortando a imagem na borda da janela. Contain-fit
            # dentro do tamanho real da coluna garante a imagem inteira
            # sempre visível, sem cortar nada.
            largura_col = direita.winfo_width()
            altura_col = direita.winfo_height()
            if largura_col <= 1 or altura_col <= 1:
                self.after(10, _carregar)
                return
            try:
                from infrastructure.filesystem import assets_dir
                from PIL import Image
                caminho = assets_dir() / "login_ilustracao.png"
                if not caminho.exists():
                    return
                img = Image.open(caminho)
                # Sangra quase até a borda (referência do usuário: a
                # ilustração vai até bem perto do limite do painel, não
                # centralizada com respiro grande em volta).
                margem_v = self._px(8)
                caixa_w = max(1, largura_col - self._px(4))
                caixa_h = max(1, altura_col - margem_v * 2)
                escala = min(caixa_w / img.width, caixa_h / img.height)
                largura = round(img.width * escala)
                altura = round(img.height * escala)
                self._img_ilustracao = ctk.CTkImage(light_image=img, dark_image=img,
                                                    size=(largura, altura))
                ctk.CTkLabel(direita, image=self._img_ilustracao, text="").place(
                    relx=1.0, rely=0.5, anchor="e", x=-self._px(2))
            except Exception:
                pass
        self.after(1, _carregar)

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
