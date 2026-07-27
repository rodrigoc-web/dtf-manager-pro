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
from core.constants import APP_NOME, VERSAO
from core import session
from ui import icons

ITENS = [
    ("dashboard", icons.GRADE,     "Dashboard"),
    ("pedidos",   icons.CLIPBOARD, "Pedidos"),
    ("modelos",   icons.CAMADAS,   "Modelos"),
    ("historico", icons.HISTORICO, "Histórico"),
    ("erros",     icons.AVISO,     "Erros"),
    ("config",    icons.ENGRENAGEM,"Configurações"),
    ("ajuda",     icons.AJUDA,     "Ajuda"),
]


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

        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.pack(fill="x", pady=(22, 20), padx=18)

        icone = self._carregar_icone()
        linha_topo = ctk.CTkFrame(cabecalho, fg_color="transparent")
        linha_topo.pack(anchor="w")
        if icone:
            ctk.CTkLabel(linha_topo, image=icone, text="").pack(side="left", padx=(0, 10))
        textos = ctk.CTkFrame(linha_topo, fg_color="transparent")
        textos.pack(side="left")
        ctk.CTkLabel(textos, text="DTF MANAGER",
                     font=ctk.CTkFont("Segoe UI", 15, "bold"),
                     text_color=BRANCO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(textos, text="PRO",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color=SIDEBAR_ATIVO, anchor="w").pack(anchor="w")

        for chave, ico, titulo in ITENS:
            img_inativo = icons.imagem(ico, tam=17, cor=SIDEBAR_TEXTO)
            img_ativo   = icons.imagem(ico, tam=17, cor=SIDEBAR_TEXTO_ATIVO)
            self._img_inativo[chave] = img_inativo
            self._img_ativo[chave]   = img_ativo
            btn = ctk.CTkButton(
                self, text=f"  {titulo}", image=img_inativo, compound="left",
                font=ctk.CTkFont("Segoe UI", 12),
                anchor="w", height=44, corner_radius=10,
                fg_color="transparent", text_color=SIDEBAR_TEXTO,
                hover_color=SIDEBAR_HOVER,
                command=lambda c=chave: self._on_navegar(c))
            btn.pack(fill="x", padx=14, pady=3)
            self._botoes[chave] = btn

        ctk.CTkLabel(self, text=f"v{VERSAO}",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=SIDEBAR_TEXTO).pack(side="bottom", pady=(0, 10))

        divisor = ctk.CTkFrame(self, fg_color=SIDEBAR_HOVER, height=1, corner_radius=0)
        divisor.pack(side="bottom", fill="x", padx=14, pady=(10, 4))

        bloco_operador = ctk.CTkFrame(self, fg_color="transparent")
        bloco_operador.pack(side="bottom", fill="x", padx=18, pady=(4, 0))
        self._lbl_operador = ctk.CTkLabel(
            bloco_operador, text="", font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=BRANCO, anchor="w")
        self._lbl_operador.pack(anchor="w")
        ctk.CTkButton(
            bloco_operador, text="Trocar operador", height=20,
            font=ctk.CTkFont("Segoe UI", 9), fg_color="transparent",
            text_color=VERDE_GLOW, hover_color=SIDEBAR_HOVER, anchor="w",
            command=self._trocar_operador).pack(anchor="w", pady=(0, 6))
        self.atualizar_operador()

    def atualizar_operador(self):
        nome = session.operador_atual or "Não identificado"
        self._lbl_operador.configure(text=nome)

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

    def _carregar_icone(self):
        try:
            from PIL import Image
            from infrastructure.filesystem import sistema_dir
            caminho = sistema_dir() / "assets" / "icon.png"
            if not caminho.exists():
                return None
            img = Image.open(caminho)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(72, 72))
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
