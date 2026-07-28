"""
ui/theme.py — Paleta e fontes da interface do DTF MANAGER PRO.
Fonte de verdade: Guia_Identidade_Visual_DTF_Manager_Pro.pdf (fornecido
pelo usuário) — tema escuro em TODA a aplicação (não só a sidebar), verde-
limão como cor de destaque, estilo premium inspirado em Adobe/Linear/
Raycast/Arc. Altere aqui para mudar qualquer aspecto visual do programa —
todas as telas herdam daqui.
"""
import customtkinter as ctk

# ── Acento (verde-limão da marca — guia: "Verde Oficial") ────────────────────
VERDE            = "#9EF01A"   # verde principal — cor de destaque, não de fundo
VERDE_ESCURO     = "#6CCF00"
VERDE_HOVER      = "#B7FF3A"   # mais claro no hover (tema escuro: hover clareia)
VERDE_PRESSIONADO = "#5DBA00"
VERDE_GLOW       = VERDE       # mantido por compatibilidade (usos antigos "sobre preto")

# ── Fundo/superfícies (guia: "Paleta Principal") ─────────────────────────────
FUNDO             = "#0F1115"   # fundo principal
FUNDO_SECUNDARIO  = "#171B22"
CARD              = "#1E242D"
CARD_HOVER        = "#262E39"
BORDA             = "#2C3643"
BRANCO            = "#FFFFFF"
PRETO             = "#000000"

# Texto escrito SOBRE um preenchimento verde (botões primários, chip ativo) —
# branco não tem contraste suficiente em cima do verde-limão vibrante; o
# guia especifica texto escuro (a própria cor de fundo principal) nesse caso.
TEXTO_SOBRE_VERDE = FUNDO

# ── Texto (guia: "Tons de Texto") ─────────────────────────────────────────────
TEXTO              = "#F5F7FA"   # texto principal
SUB                = "#B7BEC9"   # texto secundário
TEXTO_DESABILITADO = "#7A8595"
PLACEHOLDER        = "#616D7E"

# ── Sidebar (tom próprio, distinto do fundo principal — guia) ────────────────
SIDEBAR_BG          = "#131A24"
SIDEBAR_HOVER       = "#1C2430"
SIDEBAR_TEXTO       = TEXTO_DESABILITADO
SIDEBAR_TEXTO_ATIVO = TEXTO
SIDEBAR_ATIVO       = VERDE   # bloco sólido — item ativo da sidebar

# ── Superfícies "escuras" — mantido por compatibilidade com código existente
# (ex.: diálogo de login); agora o app inteiro já é escuro, então isso só
# reaproveita CARD/BORDA em vez de ter uma paleta paralela. ───────────────────
CARD_ESCURO   = CARD
BORDA_ESCURA  = BORDA

# ── Status (cor sólida + tint escuro de fundo, pra badges/chips — guia) ──────
# Distintos do Verde Oficial (marca/botões): "Sucesso" é um verde mais
# esverdeado/teal, usado em badges de status (ex.: "Produzido"), enquanto
# VERDE é reservado pra ações/destaque (botões, item ativo da sidebar).
SUCESSO      = "#4ADE80"
SUCESSO_BG   = "#243E39"
VERMELHO     = "#F43F5E"   # "Erro"
VERMELHO_BG  = "#3C2834"
AMARELO      = "#FBBF24"   # "Atenção"
AMARELO_BG   = "#3D3A2C"
INFORMACAO   = "#3B82F6"
INFORMACAO_BG = "#223149"
VERDE_CLARO  = "#30412A"   # tint escuro do verde — badges/hover "outline" (era tint CLARO no tema antigo)
VERDE_BG     = SUCESSO_BG  # reaproveita o tint de sucesso (era alias de VERDE_CLARO no tema antigo)

# ── Categórica (gráficos) ─────────────────────────────────────────────────────
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

# ── Raio de canto por tipo de componente (guia) ──────────────────────────────
RAIO_CARD   = 20
RAIO_BOTAO  = 14
RAIO_INPUT  = 14
RAIO_SIDEBAR = 24
RAIO_MODAL  = 26


def font(size: int, bold: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont("Segoe UI", size, "bold" if bold else "normal")
