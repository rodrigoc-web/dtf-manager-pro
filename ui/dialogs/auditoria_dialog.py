"""
ui/dialogs/auditoria_dialog.py — Histórico de alterações de um Modelo
(quem criou/editou/removeu, e quando). Aberto pelo ícone de histórico ao
lado de cada linha em Modelos.
"""
from __future__ import annotations
import customtkinter as ctk
from ui.theme import FUNDO, VERDE, CARD, BORDA, TEXTO, SUB, BRANCO
from ui import icons


class AuditoriaDialog(ctk.CTkToplevel):
    def __init__(self, master, db_path: str, modelo, **kw):
        super().__init__(master, **kw)
        self._db = db_path
        self._modelo = modelo

        self.title(f"Histórico — {modelo.profissao}")
        self.geometry("480x420")
        self.minsize(420, 320)
        self.configure(fg_color=FUNDO)
        self.grab_set()

        topo = ctk.CTkFrame(self, fg_color=VERDE, corner_radius=0, height=50)
        topo.pack(fill="x")
        topo.pack_propagate(False)
        icons.rotulo(topo, icons.HISTORICO, f"Alterações em '{modelo.profissao}'",
                    tam_icone=13, tam_texto=12, negrito=True,
                    cor_icone=BRANCO, cor_texto=BRANCO).pack(side="left", padx=14, pady=12)

        self._lista = ctk.CTkScrollableFrame(
            self, fg_color=CARD, corner_radius=10,
            border_width=1, border_color=BORDA)
        self._lista.pack(fill="both", expand=True, padx=16, pady=14)

        self._carregar()

    def _carregar(self):
        from infrastructure.db import auditoria_repo
        entradas = auditoria_repo.listar_por_modelo(self._db, self._modelo.id)
        if not entradas:
            ctk.CTkLabel(self._lista, text="Nenhum registro de auditoria ainda "
                                            "(modelo cadastrado antes dessa funcionalidade existir).",
                         text_color=SUB, wraplength=380, justify="left").pack(padx=10, pady=10, anchor="w")
            return
        for e in entradas:
            linha = ctk.CTkFrame(self._lista, fg_color="transparent")
            linha.pack(fill="x", padx=8, pady=5)
            ctk.CTkLabel(linha, text=f"{e['acao']}  ·  {e['operador'] or 'Não identificado'}",
                         font=ctk.CTkFont("Segoe UI", 11, "bold"),
                         text_color=TEXTO, anchor="w").pack(anchor="w")
            sub = e["criado_em"] + (f"  ·  {e['detalhes']}" if e["detalhes"] else "")
            ctk.CTkLabel(linha, text=sub, font=ctk.CTkFont("Segoe UI", 9),
                         text_color=SUB, anchor="w", wraplength=400,
                         justify="left").pack(anchor="w")
            ctk.CTkFrame(self._lista, fg_color=BORDA, height=1, corner_radius=0).pack(fill="x", padx=8)
