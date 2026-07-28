"""
ui/dialogs/evento_dialog.py — Detalhe de um evento da Central de Auditoria:
todos os campos (operador, computador, data/hora, tipo, versão, entidade),
aberto ao clicar numa linha da tela de Auditoria.
"""
from __future__ import annotations
import customtkinter as ctk
from ui.theme import FUNDO, VERDE, CARD, BORDA, TEXTO, SUB, BRANCO
from ui import icons


class EventoDialog(ctk.CTkToplevel):
    def __init__(self, master, evento: dict, **kw):
        super().__init__(master, **kw)
        self._evento = evento

        from core.constants import ROTULOS_EVENTO
        rotulo = ROTULOS_EVENTO.get(evento["tipo"], evento["tipo"])

        self.title(f"Evento #{evento['id']}")
        self.geometry("420x460")
        self.minsize(380, 400)
        self.configure(fg_color=FUNDO)
        from ui.components.titlebar import aplicar_padrao_janela
        aplicar_padrao_janela(self)
        self.grab_set()

        topo = ctk.CTkFrame(self, fg_color=VERDE, corner_radius=0, height=54)
        topo.pack(fill="x")
        topo.pack_propagate(False)
        icons.rotulo(topo, icons.ESCUDO, rotulo, tam_icone=14, tam_texto=13,
                    negrito=True, cor_icone=BRANCO, cor_texto=BRANCO).pack(side="left", padx=16, pady=14)

        corpo = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10,
                             border_width=1, border_color=BORDA)
        corpo.pack(fill="both", expand=True, padx=16, pady=16)

        campos = [
            ("Evento", f"#{evento['id']:06d}"),
            ("Tipo", rotulo),
            ("Operador", evento["operador"] or "Não identificado"),
            ("Computador", evento["computador"] or "—"),
            ("Data / Hora", evento["criado_em"]),
            ("Versão", evento["versao_app"] or "—"),
        ]
        if evento["entidade_tipo"]:
            campos.append((evento["entidade_tipo"].capitalize(), evento["entidade_id"] or "—"))
        campos.append(("Resultado", "Sucesso"))

        for rot, valor in campos:
            linha = ctk.CTkFrame(corpo, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=(10, 0))
            ctk.CTkLabel(linha, text=rot.upper(), font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=SUB, anchor="w").pack(anchor="w")
            ctk.CTkLabel(linha, text=str(valor), font=ctk.CTkFont("Segoe UI", 12),
                         text_color=TEXTO, anchor="w", wraplength=360,
                         justify="left").pack(anchor="w")

        if evento["detalhes"]:
            linha = ctk.CTkFrame(corpo, fg_color="transparent")
            linha.pack(fill="x", padx=16, pady=(10, 14))
            ctk.CTkLabel(linha, text="DETALHES", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=SUB, anchor="w").pack(anchor="w")
            ctk.CTkLabel(linha, text=evento["detalhes"], font=ctk.CTkFont("Segoe UI", 11),
                         text_color=TEXTO, anchor="w", wraplength=360,
                         justify="left").pack(anchor="w")
        else:
            ctk.CTkFrame(corpo, fg_color="transparent", height=4).pack()
