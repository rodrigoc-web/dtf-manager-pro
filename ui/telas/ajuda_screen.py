"""
ui/telas/ajuda_screen.py — Tela "Ajuda": versão do programa e dicas rápidas
de uso, mais um atalho para a pasta de logs (útil pra suporte remoto sem
precisar caçar o arquivo manualmente).
"""
from __future__ import annotations
import os
import customtkinter as ctk
from tkinter import messagebox
from core.constants import APP_NOME, VERSAO, AUTOR
from ui.theme import FUNDO, CARD, BORDA, TEXTO, SUB, BRANCO, VERDE, VERDE_HOVER, VERDE_CLARO
from ui import icons

_DICAS = [
    "Pedidos: escolha Profissão ou Time, preencha os dados e clique em "
    "\"Adicionar pedido\" quantas vezes precisar antes de gerar a produção.",
    "Times: preencha várias linhas na tabela de jogadores e adicione todas de "
    "uma vez — não precisa repetir a seleção do modelo a cada jogador.",
    "\"Modo teste\" gera as artes e o PDF sem alterar o status dos pedidos — "
    "use pra conferir antes de rodar a produção de verdade.",
    "Modelos: cadastre o PSD uma vez e use \"Pré-visualizar\" pra confirmar o "
    "posicionamento do texto antes de salvar.",
    "Erros de produção aparecem na tela \"Erros\", com o motivo e opção de "
    "reprocessar sem precisar recriar o pedido.",
    "Configurações reúne meta diária, estoque do rolo DTF, operadores e backup.",
]


class AjudaScreen(ctk.CTkFrame):
    def __init__(self, master, db_path: str, on_verificar_atualizacao=None, **kw):
        super().__init__(master, fg_color=FUNDO, corner_radius=0, **kw)
        self._db = db_path
        self._on_verificar_atualizacao = on_verificar_atualizacao

        self.grid_columnconfigure(0, weight=1)

        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        icons.rotulo(topo, icons.AJUDA, "Ajuda", tam_icone=16, tam_texto=15,
                    negrito=True, cor_icone=TEXTO, cor_texto=TEXTO).pack(anchor="w")

        sobre = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12,
                             border_width=1, border_color=BORDA)
        sobre.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        ctk.CTkLabel(sobre, text=APP_NOME, font=ctk.CTkFont("Segoe UI", 15, "bold"),
                     text_color=TEXTO, anchor="w").pack(anchor="w", padx=16, pady=(14, 0))
        ctk.CTkLabel(sobre, text=f"Versão {VERSAO}  ·  {AUTOR}",
                     font=ctk.CTkFont("Segoe UI", 10), text_color=SUB,
                     anchor="w").pack(anchor="w", padx=16, pady=(2, 12))

        dicas = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12,
                             border_width=1, border_color=BORDA)
        dicas.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        ctk.CTkLabel(dicas, text="DICAS RÁPIDAS", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB, anchor="w").pack(anchor="w", padx=16, pady=(14, 6))
        for dica in _DICAS:
            linha = ctk.CTkFrame(dicas, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(linha, text="•", font=ctk.CTkFont("Segoe UI", 11),
                         text_color=VERDE, anchor="nw", width=14).pack(side="left")
            ctk.CTkLabel(linha, text=dica, font=ctk.CTkFont("Segoe UI", 10),
                         text_color=TEXTO, anchor="w", justify="left",
                         wraplength=760).pack(side="left", fill="x", expand=True)
        ctk.CTkFrame(dicas, fg_color="transparent", height=8).pack()

        suporte = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12,
                               border_width=1, border_color=BORDA)
        suporte.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
        ctk.CTkLabel(suporte, text="SUPORTE", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB, anchor="w").pack(anchor="w", padx=16, pady=(14, 6))
        ctk.CTkButton(suporte, text=" Abrir pasta de logs", height=34,
                     image=icons.imagem(icons.CAIXA, tam=13, cor=BRANCO), compound="left",
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
                     command=self._abrir_logs).pack(anchor="w", padx=16, pady=(0, 16))

        atualizacoes = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12,
                                    border_width=1, border_color=BORDA)
        atualizacoes.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        ctk.CTkLabel(atualizacoes, text="ATUALIZAÇÕES", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB, anchor="w").pack(anchor="w", padx=16, pady=(14, 6))
        ctk.CTkButton(atualizacoes, text=" Verificar atualização agora", height=34,
                     image=icons.imagem(icons.ATUALIZAR, tam=13, cor=TEXTO), compound="left",
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self._verificar_atualizacao).pack(anchor="w", padx=16, pady=(0, 16))

    def _abrir_logs(self):
        from infrastructure.filesystem import logs_dir
        try:
            os.startfile(str(logs_dir()))
        except Exception as e:
            messagebox.showerror("Erro ao abrir pasta", str(e))

    def _verificar_atualizacao(self):
        if self._on_verificar_atualizacao:
            self._on_verificar_atualizacao()
