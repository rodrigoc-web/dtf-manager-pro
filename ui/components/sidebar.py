"""
ui/components/sidebar.py — Navegação lateral do DTF MANAGER PRO.
Substitui o popup "Ferramentas" do DTF MANAGER original: agora há várias
seções (Dashboard, Modelos, Pedidos, Histórico), então a navegação vira
uma sidebar fixa em vez de um menu.
"""
from __future__ import annotations
import customtkinter as ctk
from ui.theme import (SIDEBAR_BG, SIDEBAR_HOVER, SIDEBAR_TEXTO,
                       SIDEBAR_TEXTO_ATIVO, SIDEBAR_ATIVO, BRANCO, VERDE_GLOW)
import datetime
from core.constants import APP_NOME, VERSAO, AUTOR
from core import session
from ui import icons

# Agrupado em seções (com um rótulo pequeno acima de cada bloco) — só isso já
# ajuda muito a navegação numa sidebar com 7 itens, em vez de uma lista única.
SECOES = [
    ("PRODUÇÃO", [
        ("dashboard", icons.GRADE,     "Dashboard"),
        ("pedidos",   icons.CLIPBOARD, "Pedidos"),
        ("modelos",   icons.CAMADAS,   "Modelos"),
    ]),
    ("RELATÓRIOS", [
        ("historico",  icons.HISTORICO, "Histórico"),
        ("auditoria",  icons.ESCUDO,    "Auditoria"),
        ("erros",      icons.AVISO,     "Erros"),
    ]),
    ("SISTEMA", [
        ("config",    icons.ENGRENAGEM, "Configurações"),
        ("ajuda",     icons.AJUDA,      "Ajuda"),
    ]),
]
# Lista plana derivada — usada só onde a divisão em seções não importa
# (ex.: achar o título de um item pelo chave).
ITENS = [item for _, itens in SECOES for item in itens]


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navegar, on_trocar_operador=None, **kw):
        super().__init__(master, fg_color=SIDEBAR_BG, corner_radius=0, width=224, **kw)
        self.grid_propagate(False)
        self._on_navegar = on_navegar
        self._on_trocar_operador = on_trocar_operador
        self._botoes: dict[str, ctk.CTkButton] = {}
        self._img_inativo: dict[str, "ctk.CTkImage"] = {}
        self._img_ativo:   dict[str, "ctk.CTkImage"] = {}
        self._ativo: str | None = None

        # Logo = a IMAGEM de verdade (assets/logo_completo.png, recortada do
        # arquivo que o usuário forneceu), não texto recriado com fonte de
        # sistema — nenhuma fonte instalada reproduz a tipografia customizada
        # do logo (o "F" cortado, o traço fino ao redor de "PRO"), então só a
        # imagem garante ficar IDÊNTICO ao original.
        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", pady=(24, 18), padx=18)

        logo = self._carregar_logo_completo()
        if logo:
            ctk.CTkLabel(cabecalho, image=logo, text="").pack()

        for nome_secao, itens in SECOES:
            ctk.CTkLabel(self, text=nome_secao, font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=SIDEBAR_TEXTO, anchor="w").pack(
                fill="x", padx=22, pady=(12, 4))
            for chave, ico, titulo in itens:
                img_inativo = icons.imagem(ico, tam=17, cor=SIDEBAR_TEXTO)
                img_ativo   = icons.imagem(ico, tam=17, cor=SIDEBAR_TEXTO_ATIVO)
                self._img_inativo[chave] = img_inativo
                self._img_ativo[chave]   = img_ativo
                btn = ctk.CTkButton(
                    self, text=f"  {titulo}", image=img_inativo, compound="left",
                    font=ctk.CTkFont("Segoe UI", 12),
                    anchor="w", height=40, corner_radius=10,
                    fg_color="transparent", text_color=SIDEBAR_TEXTO,
                    hover_color=SIDEBAR_HOVER,
                    command=lambda c=chave: self._on_navegar(c))
                btn.pack(fill="x", padx=14, pady=2)
                self._botoes[chave] = btn

        ctk.CTkLabel(self, text=f"© {datetime.date.today().year} {AUTOR}",
                     font=ctk.CTkFont("Segoe UI", 8),
                     text_color=SIDEBAR_TEXTO).pack(side="bottom", pady=(0, 2))
        ctk.CTkLabel(self, text=f"v{VERSAO}",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=SIDEBAR_TEXTO).pack(side="bottom", pady=(0, 4))

        divisor = ctk.CTkFrame(self, fg_color=SIDEBAR_HOVER, height=1, corner_radius=0)
        divisor.pack(side="bottom", fill="x", padx=14, pady=(10, 4))

        # Avatar (iniciais) + nome + trocar operador — igual ao rodapé do
        # mockup (ali era "AD / Administrator / e-mail"; aqui não há e-mail,
        # então o link "Trocar operador" ocupa esse lugar).
        bloco_operador = ctk.CTkFrame(self, fg_color="transparent")
        bloco_operador.pack(side="bottom", fill="x", padx=14, pady=(4, 2))
        linha_op = ctk.CTkFrame(bloco_operador, fg_color="transparent")
        linha_op.pack(fill="x")

        avatar = ctk.CTkFrame(linha_op, fg_color=SIDEBAR_HOVER, corner_radius=18,
                              width=36, height=36)
        avatar.pack(side="left", padx=(4, 10))
        avatar.pack_propagate(False)
        self._lbl_avatar = ctk.CTkLabel(avatar, text="", font=ctk.CTkFont("Segoe UI", 12, "bold"),
                                        text_color=BRANCO)
        self._lbl_avatar.place(relx=0.5, rely=0.5, anchor="center")

        textos_op = ctk.CTkFrame(linha_op, fg_color="transparent")
        textos_op.pack(side="left", fill="x", expand=True)
        self._lbl_operador = ctk.CTkLabel(
            textos_op, text="", font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=BRANCO, anchor="w")
        self._lbl_operador.pack(anchor="w")
        ctk.CTkButton(
            textos_op, text="Trocar operador", height=16,
            font=ctk.CTkFont("Segoe UI", 9), fg_color="transparent",
            text_color=VERDE_GLOW, hover_color=SIDEBAR_HOVER, anchor="w",
            command=self._trocar_operador).pack(anchor="w")
        self.atualizar_operador()

    def atualizar_operador(self):
        nome = session.operador_atual or "Não identificado"
        self._lbl_operador.configure(text=nome)
        partes = nome.split() if nome and nome != "Não identificado" else []
        iniciais = "".join(p[0] for p in partes[:2]).upper() if partes else "?"
        self._lbl_avatar.configure(text=iniciais)

    def _trocar_operador(self):
        if self._on_trocar_operador:
            self._on_trocar_operador()

    def atualizar_contagem_erros(self, quantidade: int):
        chave = "erros"
        if chave not in self._botoes:
            return
        titulo = next(t for c, _, t in ITENS if c == chave)
        texto = f"  {titulo}" + (f"  ({quantidade})" if quantidade > 0 else "")
        self._botoes[chave].configure(text=texto)

    def _carregar_logo_completo(self):
        try:
            from PIL import Image
            from infrastructure.filesystem import sistema_dir
            caminho = sistema_dir() / "assets" / "logo_completo.png"
            if not caminho.exists():
                return None
            img = Image.open(caminho)
            largura_alvo = 188   # largura da sidebar (224) menos os 18px de padx dos dois lados
            altura_alvo = round(largura_alvo * img.height / img.width)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(largura_alvo, altura_alvo))
        except Exception:
            return None

    def marcar_ativo(self, chave: str):
        if self._ativo:
            self._botoes[self._ativo].configure(
                fg_color="transparent", text_color=SIDEBAR_TEXTO,
                image=self._img_inativo[self._ativo])
        self._botoes[chave].configure(
            fg_color=SIDEBAR_ATIVO, text_color=SIDEBAR_TEXTO_ATIVO,
            image=self._img_ativo[chave])
        self._ativo = chave
