"""
ui/telas/auditoria_screen.py — Central de Auditoria: "quem fez o quê, quando
e em qual computador" pro sistema inteiro (diferente do Histórico, que só
responde "o que foi produzido"). Busca por texto livre + filtros (Operador,
Computador, Tipo, Período); clicar num evento abre o detalhe completo.
"""
from __future__ import annotations
import datetime
import customtkinter as ctk
from ui.theme import (FUNDO, CARD, BORDA, TEXTO, SUB, BRANCO, VERDE, VERDE_CLARO,
                      VERDE_BG, VERMELHO)
from ui import icons

_PLACEHOLDER = "Todos"
_PERIODOS = {
    "Tudo": None,
    "Hoje": 0,
    "Últimos 7 dias": 7,
    "Últimos 30 dias": 30,
}


class AuditoriaScreen(ctk.CTkFrame):
    def __init__(self, master, db_path: str, **kw):
        super().__init__(master, fg_color=FUNDO, corner_radius=0, **kw)
        self._db = db_path

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        topo.grid_columnconfigure(0, weight=1)
        icons.rotulo(topo, icons.ESCUDO, "Auditoria", tam_icone=16, tam_texto=15,
                    negrito=True, cor_icone=TEXTO, cor_texto=TEXTO).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(topo, text=" Atualizar", height=32, width=110,
                     image=icons.imagem(icons.ATUALIZAR, tam=13, cor=TEXTO), compound="left",
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self.atualizar).grid(row=0, column=1, sticky="e")

        self._montar_filtros()

        self._lista = ctk.CTkScrollableFrame(
            self, fg_color=CARD, corner_radius=10,
            border_width=1, border_color=BORDA)
        self._lista.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self._lista.grid_columnconfigure(0, weight=1)

        self.atualizar()

    # ── Busca + filtros ──────────────────────────────────────────────────────

    def _montar_filtros(self):
        bloco = ctk.CTkFrame(self, fg_color="transparent")
        bloco.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        bloco.grid_columnconfigure(0, weight=1)

        pill = ctk.CTkFrame(bloco, fg_color=CARD, corner_radius=18,
                            border_width=1, border_color=BORDA, height=40)
        pill.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        pill.grid_propagate(False)
        pill.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(pill, text=icons.BUSCAR, font=icons.fonte(13),
                     text_color=SUB, fg_color="transparent").grid(row=0, column=0, padx=(14, 4), pady=6)
        self._busca = ctk.CTkEntry(
            pill, height=36, fg_color="transparent", border_width=0,
            placeholder_text="Pesquisar por operador, tipo ou detalhe...",
            font=ctk.CTkFont("Segoe UI", 11))
        self._busca.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=2)
        self._busca.bind("<KeyRelease>", lambda e: self.atualizar())

        for col in range(4):
            bloco.grid_columnconfigure(col, weight=1, uniform="filtros")

        self._combo_operador = self._filtro(bloco, "Operador", 0)
        self._combo_periodo = self._filtro(bloco, "Período", 1, valores=list(_PERIODOS.keys()),
                                           inicial="Tudo")
        self._combo_computador = self._filtro(bloco, "Computador", 2)
        self._combo_tipo = self._filtro(bloco, "Tipo", 3)

    def _filtro(self, master, rotulo: str, col: int, valores=None, inicial=None) -> ctk.CTkComboBox:
        bloco = ctk.CTkFrame(master, fg_color="transparent")
        bloco.grid(row=1, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
        ctk.CTkLabel(bloco, text=rotulo.upper(), font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB, anchor="w").pack(anchor="w")
        combo = ctk.CTkComboBox(
            bloco, height=32, values=valores or [_PLACEHOLDER],
            fg_color=CARD, text_color=TEXTO, border_color=BORDA,
            button_color=VERDE, button_hover_color=VERDE_CLARO,
            dropdown_fg_color=CARD, font=ctk.CTkFont("Segoe UI", 10),
            command=lambda _v: self.atualizar())
        combo.set(inicial or (valores[0] if valores else _PLACEHOLDER))
        combo.pack(fill="x", pady=(2, 0))
        return combo

    def _atualizar_opcoes_filtro(self):
        from infrastructure.db import eventos_repo
        from core.constants import ROTULOS_EVENTO

        operadores = [_PLACEHOLDER] + eventos_repo.listar_operadores_distintos(self._db)
        atual = self._combo_operador.get()
        self._combo_operador.configure(values=operadores)
        self._combo_operador.set(atual if atual in operadores else _PLACEHOLDER)

        computadores = [_PLACEHOLDER] + eventos_repo.listar_computadores_distintos(self._db)
        atual = self._combo_computador.get()
        self._combo_computador.configure(values=computadores)
        self._combo_computador.set(atual if atual in computadores else _PLACEHOLDER)

        tipos_brutos = eventos_repo.listar_tipos_distintos(self._db)
        self._mapa_tipo_rotulo = {ROTULOS_EVENTO.get(t, t): t for t in tipos_brutos}
        tipos = [_PLACEHOLDER] + sorted(self._mapa_tipo_rotulo.keys())
        atual = self._combo_tipo.get()
        self._combo_tipo.configure(values=tipos)
        self._combo_tipo.set(atual if atual in tipos else _PLACEHOLDER)

    # ── Lista ────────────────────────────────────────────────────────────────

    def atualizar(self):
        from infrastructure.db import eventos_repo
        self._atualizar_opcoes_filtro()

        for w in self._lista.winfo_children():
            w.destroy()

        operador = self._combo_operador.get()
        computador = self._combo_computador.get()
        tipo_rotulo = self._combo_tipo.get()
        periodo = self._combo_periodo.get()

        desde = ""
        dias = _PERIODOS.get(periodo)
        if dias is not None:
            data_desde = datetime.date.today() - datetime.timedelta(days=dias)
            desde = data_desde.strftime("%d/%m/%Y")

        eventos = eventos_repo.listar(
            self._db,
            operador="" if operador == _PLACEHOLDER else operador,
            computador="" if computador == _PLACEHOLDER else computador,
            tipo="" if tipo_rotulo == _PLACEHOLDER else self._mapa_tipo_rotulo.get(tipo_rotulo, ""),
            termo=self._busca.get().strip(),
            desde=desde)

        if not eventos:
            ctk.CTkLabel(self._lista, text="Nenhum evento encontrado com esses filtros.",
                         text_color=SUB).grid(padx=14, pady=14, sticky="w")
            return

        from core.constants import ROTULOS_EVENTO
        for i, e in enumerate(eventos):
            rotulo = ROTULOS_EVENTO.get(e["tipo"], e["tipo"])
            linha = ctk.CTkFrame(self._lista, fg_color="transparent", cursor="hand2")
            linha.grid(row=i, column=0, sticky="ew", padx=8, pady=3)
            linha.grid_columnconfigure(2, weight=1)

            ctk.CTkFrame(linha, fg_color=VERDE, width=3, corner_radius=0).grid(
                row=0, column=0, sticky="ns", padx=(0, 10))
            ctk.CTkLabel(linha, text=e["criado_em"], font=ctk.CTkFont("Segoe UI", 9),
                         text_color=SUB, width=110, anchor="w").grid(row=0, column=1, sticky="w")

            operador_txt = e["operador"] or "Não identificado"
            computador_txt = f"  ·  {e['computador']}" if e["computador"] else ""
            detalhes_txt = f"  ·  {e['detalhes']}" if e["detalhes"] else ""
            texto = f"{rotulo}  ·  {operador_txt}{computador_txt}{detalhes_txt}"
            lbl = ctk.CTkLabel(linha, text=texto, font=ctk.CTkFont("Segoe UI", 11),
                              text_color=TEXTO, anchor="w", cursor="hand2")
            lbl.grid(row=0, column=2, sticky="w", padx=(0, 8))

            for widget in (linha, lbl):
                widget.bind("<Button-1>", lambda _ev, ev=e: self._abrir_detalhe(ev))

    def _abrir_detalhe(self, evento: dict):
        from ui.dialogs.evento_dialog import EventoDialog
        EventoDialog(self, evento)
