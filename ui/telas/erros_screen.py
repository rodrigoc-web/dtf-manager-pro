"""
ui/telas/erros_screen.py — Tela "Erros": recuperação de pedidos que falharam
na produção. Antes disso, um pedido ERRO ficava misturado no Histórico sem
mensagem nenhuma (marcar_erro descartava o motivo) e sem jeito de tentar de
novo a não ser recriar o pedido do zero.
"""
from __future__ import annotations
import customtkinter as ctk
from tkinter import messagebox
from ui.theme import (FUNDO, CARD, BORDA, TEXTO, SUB, BRANCO, VERDE, VERDE_HOVER, VERDE_CLARO,
                      VERMELHO, VERMELHO_BG, AMARELO_BG, TEXTO_SOBRE_VERDE)
from ui import icons


class ErrosScreen(ctk.CTkFrame):
    def __init__(self, master, db_path: str, **kw):
        super().__init__(master, fg_color=FUNDO, corner_radius=0, **kw)
        self._db = db_path

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        topo.grid_columnconfigure(0, weight=1)
        icons.rotulo(topo, icons.AVISO, "Pedidos com erro", tam_icone=16, tam_texto=15,
                    negrito=True, cor_icone=TEXTO, cor_texto=TEXTO).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(topo, text=" Atualizar", height=32, width=110,
                     image=icons.imagem(icons.ATUALIZAR, tam=13, cor=TEXTO), compound="left",
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self.atualizar).grid(row=0, column=1, sticky="e")

        self._lista = ctk.CTkScrollableFrame(
            self, fg_color=CARD, corner_radius=10,
            border_width=1, border_color=BORDA)
        self._lista.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self._lista.grid_columnconfigure(0, weight=1)

        self.atualizar()

    def atualizar(self):
        from infrastructure.db import pedidos_repo
        for w in self._lista.winfo_children():
            w.destroy()

        erros = pedidos_repo.listar_erros(self._db)
        if not erros:
            ctk.CTkLabel(self._lista, text="Nenhum pedido com erro. Tudo certo!",
                         text_color=SUB).grid(padx=14, pady=14, sticky="w")
            return

        for i, p in enumerate(erros):
            linha = ctk.CTkFrame(self._lista, fg_color=FUNDO, corner_radius=8,
                                 border_width=1, border_color=BORDA)
            linha.grid(row=i, column=0, sticky="ew", padx=8, pady=4)
            linha.grid_columnconfigure(1, weight=1)

            selo = ctk.CTkFrame(linha, fg_color=AMARELO_BG, corner_radius=18, width=36, height=36)
            selo.grid(row=0, column=0, padx=(12, 10), pady=8)
            selo.grid_propagate(False)
            ctk.CTkLabel(selo, text=icons.AVISO, font=icons.fonte(15),
                         text_color=VERMELHO, fg_color="transparent").place(relx=0.5, rely=0.5, anchor="center")

            info = ctk.CTkFrame(linha, fg_color="transparent")
            info.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=8)
            ctk.CTkLabel(info,
                         text=f"{p.profissao}  ·  {p.resumo}  ·  qtd {p.quantidade}"
                              f"{'  ·  ' + p.operador if p.operador else ''}  ·  {p.criado_em}",
                         font=ctk.CTkFont("Segoe UI", 12, "bold"),
                         text_color=TEXTO, anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=p.mensagem_erro or "Sem detalhes do erro.",
                         font=ctk.CTkFont("Segoe UI", 10), text_color=VERMELHO,
                         anchor="w", wraplength=560, justify="left").pack(anchor="w", pady=(2, 0))

            botoes = ctk.CTkFrame(linha, fg_color="transparent")
            botoes.grid(row=0, column=2, padx=10, pady=8, sticky="e")
            ctk.CTkButton(botoes, text=" Reprocessar", height=30, width=120,
                         image=icons.imagem(icons.ATUALIZAR, tam=12, cor=TEXTO_SOBRE_VERDE), compound="left",
                         fg_color=VERDE, hover_color=VERDE_HOVER, text_color=TEXTO_SOBRE_VERDE,
                         command=lambda p=p: self._reprocessar(p)).pack(side="left", padx=(0, 6))
            ctk.CTkButton(botoes, text=" Descartar", height=30, width=100,
                         image=icons.imagem(icons.LIXEIRA, tam=12, cor=VERMELHO), compound="left",
                         fg_color=CARD, text_color=VERMELHO, hover_color=VERMELHO_BG,
                         border_color=BORDA, border_width=1,
                         command=lambda p=p: self._descartar(p)).pack(side="left")

    def _reprocessar(self, pedido):
        from infrastructure.db import pedidos_repo
        pedidos_repo.reenviar_para_fila(self._db, pedido.id)
        self.atualizar()

    def _descartar(self, pedido):
        from infrastructure.db import pedidos_repo
        if messagebox.askyesno("Descartar pedido",
            f"Descartar definitivamente o pedido de '{pedido.profissao}' ({pedido.resumo})?",
            icon="warning"):
            pedidos_repo.remover_pedido_erro(self._db, pedido.id)
            self.atualizar()
