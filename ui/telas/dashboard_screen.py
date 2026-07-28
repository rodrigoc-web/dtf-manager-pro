"""
ui/telas/dashboard_screen.py — KPIs do dia (próximo lote, pedidos pendentes,
produções hoje, modelos cadastrados) + meta do dia + atividade recente +
gráfico de produção dos últimos dias + ranking (mais/menos produzidos,
operador do mês) + ações rápidas.

Visual fiel ao mockup de referência do usuário (dashboard2.png, deixado na
pasta do projeto): barra superior com busca/sino/data, cards com badge de
tendência e seta, linha central com Meta do dia / Atividade Recente /
Gráfico de produção lado a lado. Mas todo número mostrado é real, calculado
do banco — onde uma comparação não tem dado histórico suficiente pra ser
honesta (ex.: modelos cadastrados vs mês passado sem snapshot antigo), o
badge de tendência simplesmente não aparece em vez de mostrar um percentual
inventado.
"""
from __future__ import annotations
import datetime
import tkinter as tk
import customtkinter as ctk
from ui.theme import (CARD, BORDA, VERDE, VERDE_CLARO, TEXTO, SUB, FUNDO, BRANCO,
                      AMARELO, AMARELO_BG, VERMELHO, VERMELHO_BG, CATEGORICA, TEXTO_SOBRE_VERDE)
from core.constants import META_DIA
from ui import icons

TOP_N = 3   # quantos itens mostrar em "mais/menos produzidos"
DIAS_GRAFICO = 7
LIMITE_ATIVIDADE = 5   # quantos eventos recentes listar no card "Atividade Recente"

_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]

# (ícone, cor) por tipo de evento — mesma linguagem visual do card "Atividade
# Recente" do mockup (cada tipo de evento com um selo colorido próprio).
_ICONE_COR_EVENTO = {
    "LOGIN":           (icons.CONTATO, CATEGORICA[0]),
    "PEDIDO_CRIADO":   (icons.CLIPBOARD, VERDE),
    "PEDIDO_REMOVIDO": (icons.LIXEIRA, VERMELHO),
    "MODELO_CRIADO":   (icons.CAMADAS, CATEGORICA[6]),
    "MODELO_EDITADO":  (icons.CAMADAS, CATEGORICA[6]),
    "MODELO_REMOVIDO": (icons.LIXEIRA, VERMELHO),
    "PRODUCAO_GERADA": (icons.IMPRESSORA, VERDE),
    "BACKUP":          (icons.SALVAR, SUB),
}
_ICONE_COR_PADRAO = (icons.ESCUDO, SUB)


def _variacao_pct(hoje: int, ontem: int) -> tuple[str, str] | None:
    """Retorna (seta, texto) com base em dado real, ou None se não houver base de comparação."""
    if ontem == 0 and hoje == 0:
        return None
    if ontem == 0:
        return ("↗", "novo")
    pct = (hoje - ontem) / ontem * 100
    seta = "↗" if pct >= 0 else "↘"
    return (seta, f"{abs(pct):.0f}%")


class DashboardScreen(ctk.CTkFrame):
    def __init__(self, master, db_path: str, on_navegar=None, **kw):
        super().__init__(master, fg_color=FUNDO, corner_radius=0, **kw)
        self._db = db_path
        self._on_navegar = on_navegar
        self.grid_columnconfigure(0, weight=1)

        self._montar_topo()
        self._montar_alertas()

        # Conteúdo rolável — evita que os cards fiquem cortados em silêncio em
        # janelas mais baixas (a mesma lição do formulário de Pedidos: nunca
        # confiar em altura fixa numa janela que pode variar por máquina).
        self._corpo = ctk.CTkScrollableFrame(self, fg_color=FUNDO, corner_radius=0)
        self._corpo.grid(row=2, column=0, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)
        self._corpo.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._kpis = {
            "proximo":   self._card_kpi(0, 0, icons.CAIXA, "PRÓXIMO LOTE", "pedidos"),
            "pendentes": self._card_kpi(0, 1, icons.CLIPBOARD, "PEDIDOS PENDENTES", "pedidos"),
            "hoje":      self._card_kpi(0, 2, icons.IMPRESSORA, "PRODUZIDOS HOJE", "historico",
                                       sparkline=True),
            "modelos":   self._card_kpi(0, 3, icons.CAMADAS, "MODELOS CADASTRADOS", "modelos"),
        }

        self._montar_linha_central()
        self._montar_ranking_mensal()
        self._montar_acoes_rapidas()
        self.atualizar()

    # ── Alertas (erros de produção + estoque de rolo baixo) ─────────────────
    # Só aparece quando há algo real a mostrar — nunca fabrica um alerta vazio.

    def _montar_alertas(self):
        self._banner_alertas = ctk.CTkFrame(
            self, fg_color=AMARELO_BG, corner_radius=10,
            border_width=1, border_color=AMARELO)
        self._banner_alertas.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 3))
        self._banner_alertas.grid_columnconfigure(0, weight=1)
        conteudo = ctk.CTkFrame(self._banner_alertas, fg_color="transparent")
        conteudo.grid(row=0, column=0, sticky="ew", padx=12, pady=4)
        conteudo.grid_columnconfigure(0, weight=1)
        self._lbl_alerta = ctk.CTkLabel(
            conteudo, text="", font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=AMARELO, anchor="w")
        self._lbl_alerta.grid(row=0, column=0, sticky="w")
        self._btn_alerta_erros = ctk.CTkButton(
            conteudo, text="Ver erros  →", height=24, width=90,
            fg_color="transparent", text_color=AMARELO, hover_color=AMARELO_BG,
            font=ctk.CTkFont("Segoe UI", 9, "bold"),
            command=lambda: self._navegar("erros"))
        self._btn_alerta_erros.grid(row=0, column=1, padx=(8, 0))
        self._banner_alertas.grid_remove()

    # ── Barra superior ───────────────────────────────────────────────────────

    def _montar_topo(self):
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, columnspan=4, sticky="ew", padx=16, pady=(8, 4))
        topo.grid_columnconfigure(1, weight=1)

        menu = ctk.CTkFrame(topo, fg_color=CARD, corner_radius=10,
                            border_width=1, border_color=BORDA, width=40, height=40)
        menu.grid(row=0, column=0, rowspan=2, padx=(0, 12))
        menu.grid_propagate(False)
        ctk.CTkLabel(menu, text=icons.MENU, font=icons.fonte(15),
                     text_color=TEXTO).place(relx=0.5, rely=0.5, anchor="center")

        titulos = ctk.CTkFrame(topo, fg_color="transparent")
        titulos.grid(row=0, column=1, rowspan=2, sticky="w")
        ctk.CTkLabel(titulos, text="Dashboard", font=ctk.CTkFont("Segoe UI", 18, "bold"),
                     text_color=TEXTO, anchor="w").pack(anchor="w")
        sub = ctk.CTkFrame(titulos, fg_color="transparent")
        sub.pack(anchor="w")
        ctk.CTkLabel(sub, text="Visão geral da ", font=ctk.CTkFont("Segoe UI", 10),
                     text_color=SUB).pack(side="left")
        ctk.CTkLabel(sub, text="produção", font=ctk.CTkFont("Segoe UI", 10, "bold"),
                     text_color=VERDE).pack(side="left")

        direita = ctk.CTkFrame(topo, fg_color="transparent")
        direita.grid(row=0, column=2, rowspan=2, sticky="e")

        busca = ctk.CTkFrame(direita, fg_color=CARD, corner_radius=10,
                             border_width=1, border_color=BORDA, height=40)
        busca.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(busca, text=icons.BUSCAR, font=icons.fonte(11),
                     text_color=SUB).pack(side="left", padx=(12, 4), pady=8)
        ctk.CTkEntry(busca, width=140, height=28, fg_color="transparent",
                     border_width=0, placeholder_text="Buscar...",
                     font=ctk.CTkFont("Segoe UI", 10)).pack(side="left", pady=6)
        ctk.CTkLabel(busca, text="Ctrl+K", font=ctk.CTkFont("Segoe UI", 8),
                     text_color=SUB).pack(side="left", padx=(2, 12))

        sino = ctk.CTkFrame(direita, fg_color=CARD, corner_radius=10,
                            border_width=1, border_color=BORDA, width=40, height=40)
        sino.pack(side="left", padx=(0, 10))
        sino.pack_propagate(False)
        ctk.CTkLabel(sino, text=icons.SINO, font=icons.fonte(14),
                     text_color=TEXTO).place(relx=0.5, rely=0.5, anchor="center")
        self._badge_sino = ctk.CTkLabel(
            sino, text="0", font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color=TEXTO_SOBRE_VERDE, fg_color=VERDE, corner_radius=8, width=16, height=16)
        self._badge_sino.place(relx=1.0, rely=0.0, anchor="ne")

        hoje = datetime.date.today()
        data_str = f"{hoje.day} de {_MESES[hoje.month - 1].capitalize()}, {hoje.year}"
        data = ctk.CTkFrame(direita, fg_color=CARD, corner_radius=10,
                            border_width=1, border_color=BORDA, height=40)
        data.pack(side="left")
        conteudo_data = ctk.CTkFrame(data, fg_color="transparent")
        conteudo_data.pack(padx=14, pady=8)
        ctk.CTkLabel(conteudo_data, text=icons.CALENDARIO, font=icons.fonte(12),
                     text_color=TEXTO).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(conteudo_data, text=f"{data_str}  ▾", font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TEXTO).pack(side="left")

    # ── Cards KPI ─────────────────────────────────────────────────────────────

    def _card_kpi(self, row, col, icone_char, titulo, destino: str, sparkline: bool = False) -> dict:
        c = ctk.CTkFrame(self._corpo, fg_color=CARD, corner_radius=14,
                         border_width=1, border_color=BORDA, height=70)
        c.grid(row=row, column=col, padx=(16 if col == 0 else 8, 8 if col < 3 else 16),
               pady=(0, 4), sticky="nsew")
        c.grid_propagate(False)

        cabecalho = ctk.CTkFrame(c, fg_color="transparent")
        cabecalho.pack(fill="x", padx=14, pady=(10, 0))
        ico = ctk.CTkFrame(cabecalho, fg_color=VERDE_CLARO, corner_radius=8, width=28, height=28)
        ico.pack(side="left")
        ico.pack_propagate(False)
        ctk.CTkLabel(ico, text=icone_char, font=icons.fonte(13),
                     text_color=VERDE, fg_color="transparent").place(relx=0.5, rely=0.5, anchor="center")
        lbl_badge = ctk.CTkLabel(cabecalho, text="", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                                 text_color=VERDE)
        lbl_badge.pack(side="right")

        # Número em destaque (estilo Notion) — é o que o operador bate o olho
        # primeiro, o resto do card é só contexto. "Próximo lote" é um texto
        # (DTF_000004), bem mais longo que os outros cards (só dígitos) — por
        # isso uma fonte menor aqui, senão corta na largura fixa do card.
        tam_fonte = 19 if titulo == "PRÓXIMO LOTE" else 24
        lbl_numero = ctk.CTkLabel(c, text="...", font=ctk.CTkFont("Segoe UI", tam_fonte, "bold"),
                                  text_color=TEXTO)
        lbl_numero.pack(anchor="w", padx=14, pady=(4, 0))
        ctk.CTkLabel(c, text=titulo, font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB).pack(anchor="w", padx=14, pady=(0, 1))

        linha_sub = ctk.CTkButton(
            c, fg_color="transparent", hover_color=VERDE_CLARO, corner_radius=6,
            height=16, anchor="w", text="", command=lambda: self._navegar(destino))
        linha_sub.pack(fill="x", padx=8, pady=(0, 3))
        lbl_sub = ctk.CTkLabel(linha_sub, text="", font=ctk.CTkFont("Segoe UI", 8), text_color=SUB)
        lbl_sub.place(relx=0, rely=0.5, anchor="w", x=6)
        ctk.CTkLabel(linha_sub, text="→", font=ctk.CTkFont("Segoe UI", 9), text_color=SUB).place(
            relx=1.0, rely=0.5, anchor="e", x=-6)

        cv_spark = None
        if sparkline:
            cv_spark = tk.Canvas(c, height=14, bg=CARD, highlightthickness=0)
            cv_spark.pack(fill="x", padx=14, pady=(0, 4))

        return {"numero": lbl_numero, "sub": lbl_sub, "badge": lbl_badge, "spark": cv_spark}

    def _set_kpi(self, chave: str, numero: str, sub: str, variacao=None):
        k = self._kpis[chave]
        k["numero"].configure(text=numero)
        k["sub"].configure(text=sub)
        if variacao:
            seta, texto = variacao
            k["badge"].configure(text=f"{seta} {texto}")
        else:
            k["badge"].configure(text="")

    def _desenhar_sparkline(self, canvas: tk.Canvas, valores: list[int], h: int = 18):
        """Linha fina com os últimos N dias de produção real — nunca decoração
        inventada, só os mesmos números que já aparecem no card e no histórico.
        Sem produção real ainda (tudo zero), não desenha nada — uma linha reta
        de zeros ficaria parecendo uma barra cheia, enganoso."""
        canvas.delete("all")
        if not valores or sum(valores) == 0:
            return
        canvas.update_idletasks()
        w = max(canvas.winfo_width(), 10)
        maximo = max(valores)
        n = len(valores)
        if n < 2:
            return
        pontos = []
        for i, v in enumerate(valores):
            x = i / (n - 1) * (w - 4) + 2
            y = h - 3 - (v / maximo) * (h - 7)
            pontos.append((x, y))
        for (x0, y0), (x1, y1) in zip(pontos, pontos[1:]):
            canvas.create_line(x0, y0, x1, y1, fill=VERDE, width=2, smooth=True)

    # ── Linha central: Meta do dia / Atividade Recente / Produção (período) ──

    def _montar_linha_central(self):
        linha = ctk.CTkFrame(self._corpo, fg_color="transparent")
        linha.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=16, pady=(0, 4))
        linha.grid_columnconfigure(0, weight=3)
        linha.grid_columnconfigure(1, weight=4)
        linha.grid_columnconfigure(2, weight=4)
        linha.grid_rowconfigure(0, weight=1)

        self._montar_meta_dia(linha)
        self._montar_atividade_recente(linha)
        self._montar_producao_periodo(linha)

    def _montar_meta_dia(self, master):
        meta = ctk.CTkFrame(master, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDA)
        meta.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        icons.rotulo(meta, icons.BANDEIRA, "META DO DIA", tam_icone=12, tam_texto=10,
                    negrito=True, cor_icone=SUB, cor_texto=SUB).pack(anchor="w", padx=14, pady=(10, 2))
        self._cv = tk.Canvas(meta, width=90, height=90, bg=CARD, highlightthickness=0)
        self._cv.pack(pady=(6, 4))
        self.lbl_meta_sub = ctk.CTkLabel(meta, text=f"0 de {META_DIA}",
                                         font=ctk.CTkFont("Segoe UI", 10),
                                         text_color=SUB)
        self.lbl_meta_sub.pack()
        ctk.CTkLabel(meta, text="peças produzidas", font=ctk.CTkFont("Segoe UI", 9),
                     text_color=SUB).pack(pady=(0, 8))

        divisor = ctk.CTkFrame(meta, fg_color=BORDA, height=1, corner_radius=0)
        divisor.pack(fill="x", padx=14)
        bloco_faltam = ctk.CTkFrame(meta, fg_color="transparent")
        bloco_faltam.pack(fill="x", padx=14, pady=(8, 4))
        ctk.CTkLabel(bloco_faltam, text="Faltam para concluir", font=ctk.CTkFont("Segoe UI", 9),
                     text_color=SUB, anchor="w").pack(anchor="w")
        self._lbl_faltam = ctk.CTkLabel(bloco_faltam, text=f"{META_DIA} peças",
                                        font=ctk.CTkFont("Segoe UI", 13, "bold"), text_color=TEXTO)
        self._lbl_faltam.pack(anchor="w")

        ctk.CTkButton(meta, text=" Ver detalhes da meta  →", height=26,
                     fg_color="transparent", text_color=VERDE, hover_color=VERDE_CLARO,
                     font=ctk.CTkFont("Segoe UI", 9),
                     command=lambda: self._navegar("historico")).pack(pady=(4, 10))

    def _montar_atividade_recente(self, master):
        card = ctk.CTkFrame(master, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDA)
        card.grid(row=0, column=1, sticky="nsew", padx=8)

        cabecalho = ctk.CTkFrame(card, fg_color="transparent")
        cabecalho.pack(fill="x", padx=14, pady=(10, 4))
        icons.rotulo(cabecalho, icons.HISTORICO, "ATIVIDADE RECENTE", tam_icone=12, tam_texto=10,
                    negrito=True, cor_icone=SUB, cor_texto=SUB).pack(side="left")
        ctk.CTkButton(cabecalho, text="Ver todas  →", height=18, width=70,
                     fg_color="transparent", text_color=VERDE, hover_color=CARD,
                     font=ctk.CTkFont("Segoe UI", 9),
                     command=lambda: self._navegar("auditoria")).pack(side="right")

        self._lista_atividade = ctk.CTkFrame(card, fg_color="transparent")
        self._lista_atividade.pack(fill="both", expand=True, padx=6, pady=(0, 8))

    def _atualizar_atividade_recente(self):
        from infrastructure.db import eventos_repo
        from core.constants import ROTULOS_EVENTO
        from core.utils import tempo_relativo

        for w in self._lista_atividade.winfo_children():
            w.destroy()

        eventos = eventos_repo.listar(self._db, limite=LIMITE_ATIVIDADE)
        if not eventos:
            ctk.CTkLabel(self._lista_atividade, text="Nenhuma atividade registrada ainda.",
                         font=ctk.CTkFont("Segoe UI", 10), text_color=SUB).pack(
                anchor="w", padx=8, pady=8)
            return

        for i, evento in enumerate(eventos):
            ico, cor = _ICONE_COR_EVENTO.get(evento["tipo"], _ICONE_COR_PADRAO)
            rotulo = ROTULOS_EVENTO.get(evento["tipo"], evento["tipo"])
            operador = evento["operador"] or "Não identificado"

            linha = ctk.CTkFrame(self._lista_atividade, fg_color="transparent", cursor="hand2")
            linha.pack(fill="x", padx=8, pady=3)
            linha.bind("<Button-1>", lambda e: self._navegar("auditoria"))

            # Selo VERDE (marca) precisa de ícone escuro pra ter contraste —
            # os outros (azul, vermelho, violeta, cinza) continuam com
            # ícone branco normalmente.
            cor_icone_selo = TEXTO_SOBRE_VERDE if cor == VERDE else BRANCO
            selo = ctk.CTkFrame(linha, fg_color=cor, corner_radius=13, width=26, height=26)
            selo.pack(side="left", padx=(0, 8))
            selo.pack_propagate(False)
            ctk.CTkLabel(selo, text=ico, font=icons.fonte(11), text_color=cor_icone_selo,
                        fg_color="transparent").place(relx=0.5, rely=0.5, anchor="center")

            textos = ctk.CTkFrame(linha, fg_color="transparent")
            textos.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(textos, text=rotulo, font=ctk.CTkFont("Segoe UI", 10, "bold"),
                        text_color=TEXTO, anchor="w").pack(anchor="w")
            detalhe = evento["detalhes"] or operador
            ctk.CTkLabel(textos, text=detalhe, font=ctk.CTkFont("Segoe UI", 8),
                        text_color=SUB, anchor="w", wraplength=220,
                        justify="left").pack(anchor="w")

            ctk.CTkLabel(linha, text=tempo_relativo(evento["criado_em"]),
                        font=ctk.CTkFont("Segoe UI", 8), text_color=SUB).pack(side="right", padx=(4, 0))

            for widget in (linha, selo, textos):
                widget.bind("<Button-1>", lambda e: self._navegar("auditoria"))
            if i < len(eventos) - 1:
                ctk.CTkFrame(self._lista_atividade, fg_color=BORDA, height=1,
                            corner_radius=0).pack(fill="x", padx=8)

    def _montar_producao_periodo(self, master):
        card = ctk.CTkFrame(master, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDA)
        card.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        cabecalho = ctk.CTkFrame(card, fg_color="transparent")
        cabecalho.pack(fill="x", padx=14, pady=(10, 2))
        icons.rotulo(cabecalho, icons.GRAFICO_CIMA, f"PRODUÇÃO — ÚLTIMOS {DIAS_GRAFICO} DIAS",
                    tam_icone=12, tam_texto=10, negrito=True,
                    cor_icone=SUB, cor_texto=SUB).pack(side="left")

        self._cv_producao = tk.Canvas(card, height=110, bg=CARD, highlightthickness=0)
        self._cv_producao.pack(fill="x", padx=10, pady=(2, 6))

        divisor = ctk.CTkFrame(card, fg_color=BORDA, height=1, corner_radius=0)
        divisor.pack(fill="x", padx=14)
        rodape = ctk.CTkFrame(card, fg_color="transparent")
        rodape.pack(fill="x", padx=14, pady=8)
        esquerda = ctk.CTkFrame(rodape, fg_color="transparent")
        esquerda.pack(side="left")
        ctk.CTkLabel(esquerda, text="Total produzido", font=ctk.CTkFont("Segoe UI", 9),
                     text_color=SUB, anchor="w").pack(anchor="w")
        self._lbl_total_periodo = ctk.CTkLabel(esquerda, text="0 peças",
                                               font=ctk.CTkFont("Segoe UI", 15, "bold"),
                                               text_color=TEXTO, anchor="w")
        self._lbl_total_periodo.pack(anchor="w")
        self._lbl_trend_periodo = ctk.CTkLabel(rodape, text="", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                                               text_color=VERDE)
        self._lbl_trend_periodo.pack(side="right", anchor="s", pady=(0, 2))

    def _desenhar_grafico_producao(self, valores: list[int]):
        """Barras de verdade (não sparkline fina) com rótulo do dia embaixo
        e algumas linhas de grade horizontais — mesma linguagem visual do
        card "Produção" do mockup. Zero produção ainda desenha as barras
        vazias mesmo assim (diferente da sparkline dos KPIs): aqui já tem
        rótulo de eixo, então uma grade "zerada" não engana ninguém."""
        c = self._cv_producao
        c.delete("all")
        c.update_idletasks()
        w = max(c.winfo_width(), 100)
        h = c.winfo_height() or 110
        n = len(valores)
        if n == 0:
            return

        margem_baixo = 16
        margem_topo = 6
        area_h = h - margem_baixo - margem_topo
        maximo = max(valores) if max(valores) > 0 else 1

        # grade horizontal (3 linhas leves) — só decoração de referência
        for frac in (0.0, 0.5, 1.0):
            y = margem_topo + area_h * (1 - frac)
            c.create_line(0, y, w, y, fill=BORDA, width=1)

        hoje = datetime.date.today()
        largura_slot = w / n
        largura_barra = largura_slot * 0.5
        for i, v in enumerate(valores):
            cx = (i + 0.5) * largura_slot
            altura_barra = (v / maximo) * area_h if maximo else 0
            y0 = margem_topo + area_h - altura_barra
            y1 = margem_topo + area_h
            cor = VERDE if v > 0 else BORDA
            if altura_barra > 0:
                c.create_rectangle(cx - largura_barra / 2, y0, cx + largura_barra / 2, y1,
                                   fill=cor, outline="")
            dia = hoje - datetime.timedelta(days=(n - 1 - i))
            c.create_text(cx, h - margem_baixo / 2 + 2, text=f"{dia.day:02d}/{dia.month:02d}",
                         font=("Segoe UI", 7), fill=SUB)

    def _atualizar_producao_periodo(self):
        from infrastructure.db import pedidos_repo
        valores = pedidos_repo.producao_ultimos_dias(self._db, DIAS_GRAFICO)
        self.after(50, lambda: self._desenhar_grafico_producao(valores))

        total = sum(valores)
        self._lbl_total_periodo.configure(text=f"{total} peça{'s' if total != 1 else ''}")

        # período anterior de mesmo tamanho, pra comparar (ex.: 7 dias vs os 7 anteriores)
        anterior = pedidos_repo.producao_periodo_anterior(self._db, DIAS_GRAFICO)
        variacao = _variacao_pct(total, sum(anterior))
        if variacao:
            seta, texto = variacao
            self._lbl_trend_periodo.configure(text=f"{seta} {texto}")
        else:
            self._lbl_trend_periodo.configure(text="")

    # ── Ranking mensal: mais/menos produzidos, operador do mês ──────────────

    def _montar_ranking_mensal(self):
        linha = ctk.CTkFrame(self._corpo, fg_color="transparent")
        linha.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=16, pady=(0, 4))
        linha.grid_columnconfigure((0, 1, 2), weight=1)
        linha.grid_rowconfigure(0, weight=1)

        self._corpo_mais  = self._card_lista(linha, 0, icons.GRAFICO_CIMA, "MAIS PRODUZIDOS")
        self._corpo_menos = self._card_lista(linha, 1, icons.SETA_BAIXO, "MENOS PRODUZIDOS")

        op = ctk.CTkFrame(linha, fg_color=CARD, corner_radius=14,
                          border_width=1, border_color=BORDA)
        op.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        icons.rotulo(op, icons.ESTRELA, "OPERADOR DO MÊS", tam_icone=12, tam_texto=10,
                    negrito=True, cor_icone=SUB, cor_texto=SUB).pack(anchor="w", padx=14, pady=(7, 1))
        self.lbl_operador_nome = ctk.CTkLabel(op, text="—",
                                              font=ctk.CTkFont("Segoe UI", 15, "bold"),
                                              text_color=TEXTO)
        self.lbl_operador_nome.pack(anchor="w", padx=14, pady=(4, 0))
        self.lbl_operador_qtd = ctk.CTkLabel(op, text="Nenhuma produção este mês",
                                             font=ctk.CTkFont("Segoe UI", 10),
                                             text_color=SUB)
        self.lbl_operador_qtd.pack(anchor="w", padx=14, pady=(0, 5))

    def _card_lista(self, master, col, icone_char, titulo) -> ctk.CTkFrame:
        c = ctk.CTkFrame(master, fg_color=CARD, corner_radius=14,
                         border_width=1, border_color=BORDA)
        c.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 8 if col < 2 else 0))
        icons.rotulo(c, icone_char, titulo, tam_icone=12, tam_texto=10,
                    negrito=True, cor_icone=SUB, cor_texto=SUB).pack(anchor="w", padx=14, pady=(7, 1))
        corpo = ctk.CTkFrame(c, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=14, pady=(0, 5))
        return corpo

    def _preencher_lista(self, corpo: ctk.CTkFrame, itens: list[tuple[str, int]]):
        for w in corpo.winfo_children():
            w.destroy()
        if not itens:
            ctk.CTkLabel(corpo, text="Sem dados ainda.", font=ctk.CTkFont("Segoe UI", 10),
                         text_color=SUB).pack(anchor="w")
            return
        for nome, qtd in itens:
            linha = ctk.CTkFrame(corpo, fg_color="transparent")
            linha.pack(fill="x", pady=2)
            ctk.CTkLabel(linha, text=nome, font=ctk.CTkFont("Segoe UI", 10),
                         text_color=TEXTO, anchor="w").pack(side="left")
            ctk.CTkLabel(linha, text=str(qtd), font=ctk.CTkFont("Segoe UI", 10, "bold"),
                         text_color=VERDE).pack(side="right")

    def _desenhar_circulo(self, pct: float):
        # Coordenadas calculadas a partir do tamanho REAL do canvas — nunca
        # mais fixas (já causou um círculo cortado numa rodada anterior,
        # quando o canvas mudou de tamanho e o desenho não acompanhou).
        c = self._cv
        c.delete("all")
        c.update_idletasks()
        largura = c.winfo_width() or 90
        altura = c.winfo_height() or 90
        traco = 9
        cx, cy = largura / 2, altura / 2
        r = min(cx, cy) - traco / 2 - 1
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=BORDA, width=traco)
        if pct > 0:
            c.create_arc(cx - r, cy - r, cx + r, cy + r,
                        start=90, extent=-(pct / 100 * 360),
                        outline=VERDE, width=traco, style="arc")
        c.create_text(cx, cy, text=f"{pct:.0f}%", font=("Segoe UI", 16, "bold"),
                      fill=VERDE if pct > 0 else SUB)

    # ── Ações rápidas ─────────────────────────────────────────────────────────

    def _montar_acoes_rapidas(self):
        card = ctk.CTkFrame(self._corpo, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDA)
        card.grid(row=3, column=0, columnspan=4, sticky="ew", padx=16, pady=(0, 4))
        ctk.CTkLabel(card, text="AÇÕES RÁPIDAS",
                     font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB).pack(anchor="w", padx=16, pady=(6, 3))
        linha = ctk.CTkFrame(card, fg_color="transparent")
        linha.pack(fill="x", padx=12, pady=(0, 6))

        acoes = [
            (icons.MAIS, "Novo Pedido", "Criar um novo pedido", "pedidos"),
            (icons.CAMADAS, "Novo Modelo", "Cadastrar novo modelo", "modelos"),
            (icons.HISTORICO, "Ver Histórico", "Acessar produções passadas", "historico"),
            (icons.ESCUDO, "Ver Auditoria", "Quem fez o quê e quando", "auditoria"),
            (icons.ENGRENAGEM, "Configurações", "Ajustar grade e metas", "config"),
        ]
        for ico, titulo, sub, destino in acoes:
            btn = ctk.CTkFrame(linha, fg_color=FUNDO, corner_radius=10,
                               border_width=1, border_color=BORDA, cursor="hand2")
            btn.pack(side="left", fill="x", expand=True, padx=4)
            conteudo = ctk.CTkFrame(btn, fg_color="transparent")
            conteudo.pack(fill="x", padx=12, pady=5)
            selo = ctk.CTkFrame(conteudo, fg_color=VERDE_CLARO, corner_radius=8,
                                width=32, height=32)
            selo.pack(side="left", padx=(0, 10))
            selo.pack_propagate(False)
            ctk.CTkLabel(selo, text=ico, font=icons.fonte(14), text_color=VERDE,
                        fg_color="transparent").place(relx=0.5, rely=0.5, anchor="center")
            textos = ctk.CTkFrame(conteudo, fg_color="transparent")
            textos.pack(side="left")
            ctk.CTkLabel(textos, text=titulo, font=ctk.CTkFont("Segoe UI", 11, "bold"),
                        text_color=TEXTO, anchor="w").pack(anchor="w")
            ctk.CTkLabel(textos, text=sub, font=ctk.CTkFont("Segoe UI", 8),
                        text_color=SUB, anchor="w").pack(anchor="w")

            for widget in (btn, conteudo, selo, textos):
                widget.bind("<Button-1>", lambda e, d=destino: self._navegar(d))
            for filho in conteudo.winfo_children():
                for neto in filho.winfo_children():
                    neto.bind("<Button-1>", lambda e, d=destino: self._navegar(d))

    def _navegar(self, destino: str):
        if self._on_navegar:
            self._on_navegar(destino)

    # ── Dados ─────────────────────────────────────────────────────────────────

    def atualizar(self):
        from infrastructure.db import pedidos_repo, lotes_repo, modelos_repo, config_repo, estoque_repo

        meta_dia = config_repo.obter_int(self._db, "meta_dia", META_DIA)

        erros = pedidos_repo.listar_erros(self._db)
        estoque_atual = estoque_repo.estoque_atual_metros(self._db)
        limite_estoque = estoque_repo.limite_alerta_metros(self._db)
        avisos = []
        if erros:
            avisos.append(f"{len(erros)} pedido(s) com erro precisam de atenção.")
        if estoque_atual < limite_estoque:
            avisos.append(f"Estoque de rolo DTF baixo: {estoque_atual:.1f}m restantes.")
        if avisos:
            self._lbl_alerta.configure(text="  ⚠  " + "   ·   ".join(avisos))
            self._btn_alerta_erros.grid() if erros else self._btn_alerta_erros.grid_remove()
            self._banner_alertas.grid()
        else:
            self._banner_alertas.grid_remove()

        proximo = lotes_repo.ultimo_lote_numero(self._db) + 1
        self._set_kpi("proximo", f"DTF_{proximo:06d}", "Próximo a ser gerado")

        pendentes = pedidos_repo.listar_pendentes(self._db)
        self._badge_sino.configure(text=str(len(pendentes)))
        criados_hoje, criados_ontem = pedidos_repo.variacao_hoje_ontem(self._db, "criado_em")
        self._set_kpi("pendentes", str(len(pendentes)), "Aguardando produção",
                      _variacao_pct(criados_hoje, criados_ontem))

        produzidos_hoje, produzidos_ontem = pedidos_repo.variacao_hoje_ontem(self._db, "produzido_em")
        self._set_kpi("hoje", str(produzidos_hoje), "Peças produzidas",
                      _variacao_pct(produzidos_hoje, produzidos_ontem))
        spark = self._kpis["hoje"]["spark"]
        if spark is not None:
            self.after(50, lambda: self._desenhar_sparkline(
                spark, pedidos_repo.producao_ultimos_dias(self._db, 7)))

        total_modelos = len(modelos_repo.listar_modelos(self._db))
        novos_no_mes = modelos_repo.contar_criados_no_mes(self._db)
        sub_modelos = f"{novos_no_mes} cadastrado(s) este mês" if novos_no_mes else "Total de modelos"
        self._set_kpi("modelos", str(total_modelos), sub_modelos)

        pct = min(produzidos_hoje / meta_dia * 100, 100) if produzidos_hoje > 0 else 0
        self._desenhar_circulo(pct)
        self.lbl_meta_sub.configure(text=f"{produzidos_hoje} de {meta_dia}")
        faltam = max(0, meta_dia - produzidos_hoje)
        self._lbl_faltam.configure(text=f"{faltam} peça{'s' if faltam != 1 else ''}"
                                        if faltam > 0 else "Meta batida! 🎉")

        self._atualizar_producao_periodo()

        ranking = pedidos_repo.contagem_por_profissao(self._db)
        self._preencher_lista(self._corpo_mais, ranking[:TOP_N])
        piores = list(reversed(ranking))[:TOP_N]
        self._preencher_lista(self._corpo_menos, piores)

        operador = pedidos_repo.operador_do_mes(self._db)
        if operador:
            self.lbl_operador_nome.configure(text=operador[0])
            self.lbl_operador_qtd.configure(text=f"{operador[1]} peça(s) este mês")
        else:
            self.lbl_operador_nome.configure(text="—")
            self.lbl_operador_qtd.configure(text="Nenhuma produção este mês")

        self._atualizar_atividade_recente()
