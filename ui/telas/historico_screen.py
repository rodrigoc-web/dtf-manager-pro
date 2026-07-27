"""
ui/telas/historico_screen.py — Histórico completo de produção: donut
"Produção por profissão" (portado da antiga tela Produção) + lista de
pedidos já produzidos/erro, com operador, data de produção e resumo
(telefone ou nome+números, conforme o tipo do modelo).
"""
from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from domain.enums import Status
from ui.theme import (FUNDO, CARD, BORDA, TEXTO, SUB, VERDE, VERDE_CLARO,
                      VERMELHO, CATEGORICA, MUTED)
from ui import icons

FATIAS_DONUT = 5   # top N profissões — o resto agrupa em "Outros"


class HistoricoScreen(ctk.CTkFrame):
    def __init__(self, master, db_path: str, **kw):
        super().__init__(master, fg_color=FUNDO, corner_radius=0, **kw)
        self._db = db_path

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        topo.grid_columnconfigure(0, weight=1)
        icons.rotulo(topo, icons.HISTORICO, "Histórico", tam_icone=16, tam_texto=15,
                    negrito=True, cor_icone=TEXTO, cor_texto=TEXTO).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(topo, text=" Atualizar", height=32, width=110,
                     image=icons.imagem(icons.ATUALIZAR, tam=13, cor=TEXTO), compound="left",
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self.atualizar).grid(row=0, column=1, sticky="e")

        self._montar_donut()

        self._lista = ctk.CTkScrollableFrame(
            self, fg_color=CARD, corner_radius=10,
            border_width=1, border_color=BORDA)
        self._lista.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self._lista.grid_columnconfigure(0, weight=1)

        self.atualizar()

    # ── Donut "Produção por profissão" ──────────────────────────────────────

    def _montar_donut(self):
        donut = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12,
                             border_width=1, border_color=BORDA, height=170)
        donut.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        donut.grid_propagate(False)
        icons.rotulo(donut, icons.GRAFICO_CIMA, "PRODUÇÃO POR PROFISSÃO/TIME (total)",
                    tam_icone=12, tam_texto=9, negrito=True,
                    cor_icone=SUB, cor_texto=SUB).pack(anchor="w", padx=14, pady=(10, 2))
        corpo = ctk.CTkFrame(donut, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=10)
        self._cv_donut = tk.Canvas(corpo, width=100, height=100, bg=CARD, highlightthickness=0)
        self._cv_donut.pack(side="left", padx=(4, 8))
        self._legenda_donut = ctk.CTkFrame(corpo, fg_color="transparent")
        self._legenda_donut.pack(side="left", fill="both", expand=True)

    def _desenhar_donut(self, dados: list[tuple[str, int]]):
        c = self._cv_donut
        c.delete("all")
        for w in self._legenda_donut.winfo_children():
            w.destroy()

        total_geral = sum(n for _, n in dados)
        if total_geral == 0:
            c.create_oval(10, 10, 90, 90, outline=BORDA, width=16)
            c.create_text(50, 50, text="0", font=("Segoe UI", 13, "bold"), fill=SUB)
            ctk.CTkLabel(self._legenda_donut, text="Nenhuma produção ainda.",
                         font=ctk.CTkFont("Segoe UI", 10), text_color=SUB).pack(anchor="w")
            return

        principais = dados[:FATIAS_DONUT]
        outros = sum(n for _, n in dados[FATIAS_DONUT:])
        fatias = [(nome, n, CATEGORICA[i]) for i, (nome, n) in enumerate(principais)]
        if outros > 0:
            fatias.append(("Outros", outros, MUTED))

        cx, cy, r, largura = 50, 50, 38, 15
        angulo = 90.0
        for _, n, cor in fatias:
            extensao = n / total_geral * 360
            if extensao <= 0:
                continue
            extensao_desenho = max(extensao, 2)
            c.create_arc(cx - r, cy - r, cx + r, cy + r,
                        start=angulo, extent=-extensao_desenho,
                        outline=cor, width=largura, style="arc")
            angulo -= extensao

        c.create_text(cx, cy - 6, text=str(total_geral), font=("Segoe UI", 14, "bold"),
                      fill=TEXTO)
        c.create_text(cx, cy + 10, text="peças", font=("Segoe UI", 8), fill=SUB)

        for nome, n, cor in fatias:
            pct = n / total_geral * 100
            linha = ctk.CTkFrame(self._legenda_donut, fg_color="transparent")
            linha.pack(fill="x", anchor="w", pady=1)
            ctk.CTkFrame(linha, fg_color=cor, width=10, height=10,
                        corner_radius=2).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(linha, text=f"{nome}  ·  {pct:.0f}%",
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=TEXTO, anchor="w").pack(side="left")

    # ── Lista de pedidos já produzidos/erro ─────────────────────────────────

    def atualizar(self):
        from infrastructure.db import pedidos_repo
        for w in self._lista.winfo_children():
            w.destroy()

        historico = pedidos_repo.listar_historico(self._db, limite=300)
        if not historico:
            ctk.CTkLabel(self._lista, text="Nenhum pedido produzido ainda.",
                         text_color=SUB).grid(padx=14, pady=14, sticky="w")
        else:
            for i, p in enumerate(historico):
                cor = VERDE if p.status == Status.PRODUZIDO else VERMELHO
                marca = "✅" if p.status == Status.PRODUZIDO else "❌"
                quando = p.produzido_em or p.criado_em
                operador = f" · {p.operador}" if p.operador else ""
                linha = ctk.CTkFrame(self._lista, fg_color="transparent")
                linha.grid(row=i, column=0, sticky="ew", padx=8, pady=3)
                ctk.CTkLabel(linha,
                             text=f"{marca}  {p.profissao}  ·  {p.resumo}  ·  qtd {p.quantidade}"
                                  f"{operador}  ·  {quando}  ·  lote {p.lote_id or '—'}",
                             font=ctk.CTkFont("Segoe UI", 10),
                             text_color=TEXTO, anchor="w").pack(side="left")
                ctk.CTkLabel(linha, text=p.status.value,
                             font=ctk.CTkFont("Segoe UI", 9, "bold"),
                             text_color=cor).pack(side="right")

        self._desenhar_donut(pedidos_repo.contagem_por_profissao(self._db))
