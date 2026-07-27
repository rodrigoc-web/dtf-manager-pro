"""
core/constants.py — Constantes globais do DTF MANAGER PRO.
Único lugar para alterar valores que afetam todo o projeto.
"""

# ── Impressão ─────────────────────────────────────────────────────────────────
# CANVAS_W é só o valor de fallback caso a configuração de grade (tela
# Configurações → "Grade de impressão") ainda não tenha sido definida — a
# fonte de verdade em produção é o que está salvo em `configuracoes`
# (grade_largura_rolo_cm etc.), não mais essa constante.
CANVAS_W        = 6729   # largura do rolo (57cm @ 300dpi) — valor de fallback
MARGEM_LATERAL  =  120   # ~1cm de margem em cada lado (dentro do canvas)
DPI             =  300

# ── Heurística de detecção de camada de telefone (tela Gerenciar Modelos) ─────
# Usada só para SUGERIR candidatas ao usuário — a confirmação final é sempre
# manual, porque o acervo de PSDs de profissão não segue nome fixo de camada.
PALAVRAS_CHAVE_TELEFONE = ["NUMERO", "NÚMERO", "TELEFONE", "FONE"]

# ── Campos de personalização por categoria de modelo ──────────────────────────
# (chave interna, rótulo pra UI) — usado no cadastro de modelo (dropdown de
# campo por camada) e no formulário de pedido (quais campos pedir).
CAMPOS_POR_TIPO = {
    "PROFISSAO": [("telefone", "Telefone")],
    "TIME": [
        ("nome", "Nome"),
        ("numero_peito", "Número Peito"),
        ("numero_costas", "Número Costas"),
    ],
}

# ── Produção ──────────────────────────────────────────────────────────────────
META_DIA        = 300     # meta de artes por dia (dashboard)
RESPIRO_CROP    = 50      # pixels de respiro abaixo do último pixel visível

# ── Sistema ───────────────────────────────────────────────────────────────────
VERSAO          = "1.0.0"
AUTOR           = "RodrigoCesar"
APP_NOME        = "DTF MANAGER PRO"
