"""
ui/theme.py — Paleta e fontes da interface do DTF MANAGER PRO.
Visual definido pela logo/ícone oficiais (verde-limão) + mockup de
referência: sidebar preta, conteúdo claro (cards brancos, fundo cinza
bem claro). Altere aqui para mudar qualquer aspecto visual do programa.
"""
import customtkinter as ctk

# ── Acento (verde-limão da marca, calibrado p/ contraste em fundo claro) ────
VERDE        = "#6B9E00"   # verde-limão principal — bom contraste em branco
VERDE_HOVER  = "#597F00"   # mais escuro — hover de botões cheios
VERDE_CLARO  = "#EEF7DA"   # tint claro — hover de botões "outline"/cards
VERDE_GLOW   = "#93CC00"   # verde mais vibrante — usado sobre fundo preto (sidebar)

# ── Conteúdo (claro) ──────────────────────────────────────────────────────────
FUNDO        = "#F5F6F7"
CARD         = "#FFFFFF"
BORDA        = "#E4E6E8"
TEXTO        = "#14181A"
SUB          = "#6B7280"
BRANCO       = "#FFFFFF"
PRETO        = "#000000"

# ── Sidebar (preta, como na logo) ──────────────────────────────────────────────
SIDEBAR_BG          = "#000000"
SIDEBAR_HOVER       = "#1A1C1A"
SIDEBAR_TEXTO       = "#8A908C"
SIDEBAR_TEXTO_ATIVO = "#FFFFFF"
SIDEBAR_ATIVO       = VERDE   # bloco sólido — item ativo da sidebar

# ── Superfícies escuras (diálogos "vitrine" sobre fundo preto, ex.: login) ───
CARD_ESCURO   = "#141614"
BORDA_ESCURA  = "#2A2D2A"

# ── Status (cor sólida + tint claro de fundo, pra badges/chips) ──────────────
VERMELHO     = "#DC2626"
VERMELHO_BG  = "#FEE2E2"
AMARELO      = "#D97706"
AMARELO_BG   = "#FEF3E2"
VERDE_BG     = VERDE_CLARO   # reaproveita o tint já existente (badge "produzido")

# ── Categórica (gráficos — paleta validada p/ modo claro, ordem fixa) ────────
# Fonte: skill dataviz/references/palette.md — 8 matizes que passam o teste de
# daltonismo em pares adjacentes (donut/barras). "Outros" usa MUTED (cinza).
CATEGORICA = [
    "#2a78d6",  # 1 azul
    "#eb6834",  # 2 laranja
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 amarelo
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 verde
    "#4a3aa7",  # 7 violeta
    "#e34948",  # 8 vermelho
]
MUTED = "#898781"


def font(size: int, bold: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont("Segoe UI", size, "bold" if bold else "normal")
