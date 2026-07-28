"""
ui/theme.py — Paleta e fontes da interface do DTF MANAGER PRO.
Fonte de verdade: DTF_Manager_Pro_Design_System_v2_Light_Dark.pdf — o tema
oficial é Light Premium (Linear/Stripe/Vercel/Notion Light) com SIDEBAR
ESCURA FIXA nos dois temas — só a área de conteúdo troca entre claro e
escuro. O verde de marca, porém, é fixo (correção do usuário sobre o v2:
usar um esmeralda diferente no claro quebrava a identidade visual — o
logo é sempre lima) — os 4 tons oficiais (#9EF01A/#B7FF3A/#78D900/#5DBA00)
valem nos dois temas, e o texto sobre ele é sempre escuro (o lima é
vibrante demais pro branco ter contraste, em claro ou escuro).

A escolha do usuário (claro/escuro) fica salva em `configuracoes` (chave
"tema") e é lida uma única vez, na importação deste módulo — trocar de
tema exige reiniciar o app (ui/telas/config_screen.py faz o self-relaunch).
Não dá pra trocar "ao vivo": logo, ícones e gráficos são bitmaps gerados a
partir dessas constantes e não se redesenham sozinhos quando elas mudam.

Altere aqui para mudar qualquer aspecto visual do programa — todas as
telas herdam daqui.
"""
import customtkinter as ctk

TEMAS_DISPONIVEIS = ("light", "dark")
TEMA_PADRAO = "light"


def _ler_tema_salvo() -> str:
    try:
        from infrastructure.filesystem import db_path
        from infrastructure.db import config_repo
        tema = config_repo.obter(str(db_path()), "tema", TEMA_PADRAO)
        return tema if tema in TEMAS_DISPONIVEIS else TEMA_PADRAO
    except Exception:
        return TEMA_PADRAO


def _blend(fg_hex: str, bg_hex: str, alpha: float) -> str:
    """Mistura fg_hex em bg_hex na proporção alpha (0-1) -- pra tints de
    badge sem precisar adivinhar hex (ex.: fundo do chip "Produzido")."""
    fg = tuple(int(fg_hex[i:i + 2], 16) for i in (1, 3, 5))
    bg = tuple(int(bg_hex[i:i + 2], 16) for i in (1, 3, 5))
    mistura = tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg))
    return "#{:02X}{:02X}{:02X}".format(*mistura)


TEMA_ATUAL = _ler_tema_salvo()
ESCURO = TEMA_ATUAL == "dark"

BRANCO = "#FFFFFF"
PRETO  = "#000000"

# ── Sidebar — SEMPRE escura, nos dois temas (guia: "sidebar escura fixa
# para reforçar identidade"), só o tom exato varia um pouco por tema. ────────
SIDEBAR_BG    = "#131A24" if ESCURO else "#12161F"
SIDEBAR_HOVER = _blend(BRANCO, SIDEBAR_BG, 0.08)
SIDEBAR_TEXTO = "#7A8595"          # sempre um cinza claro (fundo sempre escuro)
# SIDEBAR_TEXTO_ATIVO / SIDEBAR_ATIVO são definidos mais abaixo, depois de
# TEXTO_SOBRE_VERDE e VERDE existirem.

# Superfícies "escuras" fixas (não seguem o tema) — usadas só pelo diálogo
# de login/splash, que continua um painel de marca escuro independente do
# tema escolhido pro resto do app (igual telas de login de Linear/Notion,
# que têm identidade visual própria e não seguem o tema do produto).
CARD_ESCURO  = "#1E242D"
BORDA_ESCURA = "#2C3643"

# ── Acento de marca — FIXO nos dois temas (o logo é sempre lima; um verde
# diferente por tema quebraria o reconhecimento imediato da marca ao trocar
# de tema). Os 4 tons oficiais bastam pro sistema inteiro. ───────────────────
VERDE             = "#9EF01A"
VERDE_HOVER       = "#B7FF3A"
VERDE_PRESSIONADO = "#78D900"
VERDE_ESCURO      = "#5DBA00"
VERDE_GLOW        = VERDE   # mantido por compatibilidade

# Texto escrito SOBRE um preenchimento verde (botões primários, chip ativo)
# -- sempre escuro: o lima é vibrante demais pro branco ter contraste, em
# claro ou escuro.
TEXTO_SOBRE_VERDE = "#111827"

# Status -- distintos do verde de marca (guia ainda diferencia por tema).
if ESCURO:
    SUCESSO  = "#4ADE80"
    VERMELHO = "#F43F5E"
else:
    SUCESSO  = "#22C55E"
    VERMELHO = "#EF4444"
AMARELO      = "#FBBF24"           # "Atenção" -- guia não especifica por tema
INFORMACAO   = "#3B82F6"           # igual nos dois temas (guia)

SIDEBAR_TEXTO_ATIVO = TEXTO_SOBRE_VERDE   # item ativo tem fundo verde sólido
SIDEBAR_ATIVO        = VERDE

# ── Fundo/superfícies/texto (guia: Background/Surface/Surface Elevada) ──────
if ESCURO:
    FUNDO              = "#0F1115"   # Background
    FUNDO_SECUNDARIO   = "#171B22"   # Surface
    CARD               = "#1E242D"   # Surface Elevada
    CARD_HOVER         = "#262E39"
    BORDA              = "#2C3643"
    TEXTO              = "#F5F7FA"
    SUB                = "#B7BEC9"
    TEXTO_DESABILITADO = "#7A8595"
    PLACEHOLDER        = "#616D7E"
else:
    FUNDO              = "#F6F8FB"   # Background
    FUNDO_SECUNDARIO   = "#FFFFFF"   # Surface
    CARD               = "#FFFFFF"   # Surface Elevada -- "cards totalmente brancos"
    CARD_HOVER         = "#F3F4F6"
    BORDA              = "#E7ECF2"
    TEXTO              = "#111827"
    SUB                = "#6B7280"
    TEXTO_DESABILITADO = "#9CA3AF"
    PLACEHOLDER        = "#9CA3AF"

# ── Tints de badge/chip (status a 14% sobre o Surface Elevada do tema
# ativo) — mesma fórmula nos dois temas, então o resultado já sai correto
# tanto no claro (tint pastel) quanto no escuro (tint escuro), sem precisar
# de valores hardcoded por tema. ─────────────────────────────────────────────
_ALPHA_TINT = 0.14
SUCESSO_BG    = _blend(SUCESSO, CARD, _ALPHA_TINT)
VERMELHO_BG   = _blend(VERMELHO, CARD, _ALPHA_TINT)
AMARELO_BG    = _blend(AMARELO, CARD, _ALPHA_TINT)
INFORMACAO_BG = _blend(INFORMACAO, CARD, _ALPHA_TINT)
VERDE_CLARO   = _blend(VERDE, CARD, _ALPHA_TINT)
VERDE_BG      = SUCESSO_BG

# ── Categórica (gráficos) ─────────────────────────────────────────────────────
# Fonte: skill dataviz/references/palette.md — 8 matizes que passam o teste de
# daltonismo em pares adjacentes (donut/barras). "Outros" usa MUTED (cinza).
# Iguais nos dois temas (guia não pede variação aqui).
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

# ── Raio de canto por tipo de componente (guia — igual nos dois temas) ───────
RAIO_CARD    = 20
RAIO_BOTAO   = 14
RAIO_INPUT   = 14
RAIO_SIDEBAR = 24
RAIO_MODAL   = 26


def font(size: int, bold: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont("Segoe UI", size, "bold" if bold else "normal")
