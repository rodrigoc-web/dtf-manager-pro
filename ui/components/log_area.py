"""
ui/components/log_area.py — Log em tempo real consumindo o EventBus.
Thread-safe: recebe eventos de qualquer thread via fila interna.
"""
from __future__ import annotations
import datetime
import customtkinter as ctk
from domain.events import EventBus, TipoEvento, Evento
from ui.theme import CARD, BORDA, SUB, TEXTO, VERDE, VERMELHO, AMARELO

_TAG: dict[TipoEvento, str] = {
    TipoEvento.LOG_OK:            "ok",
    TipoEvento.LOG_ERRO:          "erro",
    TipoEvento.LOG_AVISO:         "aviso",
    TipoEvento.LOG_INFO:          "info",
    TipoEvento.PRODUCAO_INICIADA: "info",
    TipoEvento.PRODUCAO_CONCLUIDA:"ok",
    TipoEvento.PRODUCAO_ERRO:     "erro",
    TipoEvento.RENDER_CONCLUIDO:  "ok",
    TipoEvento.PEDIDO_INVALIDO:   "aviso",
    TipoEvento.SHEETS_ERRO:       "erro",
    TipoEvento.SHEETS_CONECTADO:  "ok",
}
_ICO = {"ok":"✅","erro":"❌","aviso":"⚠️","info":"ℹ️","dim":"·"}
_COR = {
    "ok": VERDE, "erro": VERMELHO, "aviso": AMARELO,
    "info": "#1D4ED8", "dim": SUB, "ts": SUB,
}


class LogArea(ctk.CTkFrame):
    def __init__(self, master, altura_total: int = 150, **kw):
        # altura fixa (grid_propagate desligado) — sem isso, a área de log
        # crescia conforme mensagens iam sendo adicionadas (sem limite),
        # espremendo a tabela de pedidos acima dela até ela sumir da tela
        # numa janela de altura normal (~800px).
        super().__init__(master, fg_color="transparent",
                         corner_radius=0, height=altura_total, **kw)
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._widgets: list = []
        self._fila:    list = []

        hdr = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="LOG DE EXECUÇÃO",
                     font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(hdr, text="🗑  Limpar",
                      font=ctk.CTkFont("Segoe UI", 9),
                      fg_color="transparent", text_color=SUB,
                      hover_color=BORDA, width=70, height=22,
                      corner_radius=6, command=self.limpar).grid(
            row=0, column=1, sticky="e")

        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=CARD, corner_radius=10,
            border_width=1, border_color=BORDA)
        self._scroll.grid(row=1, column=0, sticky="nsew", pady=(1, 0))
        self._scroll.grid_columnconfigure(0, weight=1)

        # Registrar no EventBus
        bus = EventBus.get()
        for tipo in TipoEvento:
            bus.subscribe(tipo, self._enfileirar)
        self.after(100, self._poll)

    def _enfileirar(self, ev: Evento):
        if ev.mensagem:
            self._fila.append(ev)

    def _poll(self):
        while self._fila:
            self._render(self._fila.pop(0))
        self.after(100, self._poll)

    def _render(self, ev: Evento):
        tag = _TAG.get(ev.tipo, "info")
        ts  = datetime.datetime.now().strftime("%H:%M:%S")
        cor = _COR.get(tag, TEXTO)
        ico = _ICO.get(tag, "")

        row = ctk.CTkFrame(self._scroll, fg_color=CARD, corner_radius=0)
        row.pack(fill="x", pady=(2, 0))
        main = ctk.CTkFrame(row, fg_color="transparent")
        main.pack(fill="x", padx=12, pady=(4, 0))
        ctk.CTkLabel(main, text=f"{ico} {ev.mensagem}",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=cor, anchor="w",
                     wraplength=380).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(main, text=ts,
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=_COR["ts"]).pack(side="right")
        ctk.CTkFrame(row, fg_color=BORDA, height=1,
                     corner_radius=0).pack(fill="x", padx=12, pady=(4, 0))
        self._widgets.append(row)
        self.after(50, lambda: self._scroll._parent_canvas.yview_moveto(1.0))

    def limpar(self):
        for w in self._widgets:
            w.destroy()
        self._widgets.clear()
