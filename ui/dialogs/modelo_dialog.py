"""
ui/dialogs/modelo_dialog.py — Wizard de cadastro/edição de um Modelo
(Profissão ou Time).

Fluxo: usuário digita o nome, escolhe o PSD de produção, o app lista as
camadas do PSD (marcando candidatas por heurística de nome) e o usuário
confirma o mapeamento de campos. Antes de salvar, pode pré-visualizar a
arte com dados de exemplo — a única forma confiável de confirmar a
calibração, já que o acervo de PSDs não segue um padrão fixo de camadas.

Profissão: cada camada marcada vira campo "telefone" (checkbox simples).
Time: cada camada marcada escolhe um campo (Nome/Número Peito/Número
Costas) num dropdown; "Nome" ganha um toggle extra "Vertical" (girar 90°).
"""
from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

from domain.models import Modelo, Pedido
from domain.enums import Prioridade, TipoModelo
from core.constants import CAMPOS_POR_TIPO
from core.exceptions import DTFError
from ui.theme import FUNDO, VERDE, VERDE_HOVER, VERDE_CLARO, CARD, BORDA, TEXTO, SUB, BRANCO, TEXTO_SOBRE_VERDE
from ui import icons

DADOS_EXEMPLO = {
    "telefone": "(11) 91234-5678",
    "nome": "SILVA",
    "numero_peito": "10",
    "numero_costas": "10",
}
PREVIEW_MAX_W = 480


class ModeloDialog(ctk.CTkToplevel):
    def __init__(self, master, db_path: str, fonte_path: str,
                 tipo: TipoModelo = TipoModelo.PROFISSAO,
                 modelo: Modelo | None = None, grupo_sugerido: str | None = None,
                 on_saved=None, **kw):
        super().__init__(master, **kw)
        self._db      = db_path
        self._fonte   = fonte_path
        self._modelo  = modelo          # None = cadastro novo
        self._tipo    = modelo.tipo if modelo else tipo
        self._on_saved = on_saved
        self._psd_path: str | None = modelo.psd_path if modelo else None
        self._camadas: list[dict] = []       # saída de listar_camadas()
        self._preview_img = None             # referência viva do CTkImage

        # Estado por camada (linha da lista)
        self._usar: dict[str, ctk.BooleanVar] = {}
        self._campo_var: dict[str, ctk.StringVar] = {}   # só Time
        self._vertical_var: dict[str, ctk.BooleanVar] = {}  # só Time + campo "nome"
        self._linha_vertical: dict[str, ctk.CTkCheckBox] = {}

        rotulo_tipo = "profissão" if self._tipo == TipoModelo.PROFISSAO else "time"
        self.title(f"Editar modelo ({rotulo_tipo})" if modelo else f"Novo modelo ({rotulo_tipo})")
        self.geometry("640x700")
        self.minsize(580, 580)
        self.configure(fg_color=FUNDO)
        from ui.components.titlebar import aplicar_padrao_janela
        aplicar_padrao_janela(self)
        self.grab_set()

        self._montar()
        if modelo:
            self._entry_nome.insert(0, modelo.profissao)
            if self._combo_selecao is not None:
                self._combo_selecao.set(modelo.grupo)
            self._lbl_psd.configure(text=self._nome_curto(modelo.psd_path))
            mapa_existente = {c.nome: c for c in modelo.camadas}
            self._carregar_camadas(modelo.psd_path, mapa_existente=mapa_existente)
        elif grupo_sugerido and self._combo_selecao is not None:
            self._combo_selecao.set(grupo_sugerido)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _montar(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        rotulo_tipo = "Profissão" if self._tipo == TipoModelo.PROFISSAO else "Time"
        topo = ctk.CTkFrame(self, fg_color=VERDE, corner_radius=0, height=54)
        topo.grid(row=0, column=0, sticky="ew")
        topo.grid_propagate(False)
        icone_tipo = icons.CAMADAS if self._tipo == TipoModelo.PROFISSAO else icons.PECA
        icons.rotulo(topo, icone_tipo, f"Cadastro de modelo ({rotulo_tipo})",
                    tam_icone=14, tam_texto=13, negrito=True,
                    cor_icone=TEXTO_SOBRE_VERDE, cor_texto=TEXTO_SOBRE_VERDE).pack(side="left", padx=16, pady=14)

        corpo = ctk.CTkFrame(self, fg_color=FUNDO, corner_radius=0)
        corpo.grid(row=1, column=0, sticky="ew", padx=16, pady=(12, 4))
        corpo.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(corpo, text=f"Nome d{'a' if self._tipo == TipoModelo.PROFISSAO else 'a'} "
                                  f"{'profissão' if self._tipo == TipoModelo.PROFISSAO else 'variação'}",
                     font=ctk.CTkFont("Segoe UI", 10, "bold"),
                     text_color=SUB, anchor="w").grid(row=0, column=0, sticky="w")
        placeholder = "Ex.: ELETRICISTA" if self._tipo == TipoModelo.PROFISSAO else "Ex.: ADULTO VERDE COM ESCUDO"
        self._entry_nome = ctk.CTkEntry(corpo, height=34, placeholder_text=placeholder)
        self._entry_nome.grid(row=1, column=0, sticky="ew", pady=(2, 10))

        linha_psd_row = 2
        self._combo_selecao = None
        if self._tipo == TipoModelo.TIME:
            ctk.CTkLabel(corpo, text="Seleção (país/time)",
                         font=ctk.CTkFont("Segoe UI", 10, "bold"),
                         text_color=SUB, anchor="w").grid(row=2, column=0, sticky="w")
            from infrastructure.db import modelos_repo
            grupos = modelos_repo.listar_grupos_time(self._db)
            self._combo_selecao = ctk.CTkComboBox(
                corpo, height=34, values=grupos or ["BRASIL"],
                fg_color=CARD, text_color=TEXTO, border_color=BORDA,
                button_color=VERDE_CLARO, button_hover_color=VERDE_CLARO,
                dropdown_fg_color=CARD)
            self._combo_selecao.set("")
            self._combo_selecao.grid(row=3, column=0, sticky="ew", pady=(2, 10))
            linha_psd_row = 4

        linha_psd = ctk.CTkFrame(corpo, fg_color="transparent")
        linha_psd.grid(row=linha_psd_row, column=0, sticky="ew")
        linha_psd.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(linha_psd, text="Selecionar PSD...", height=34,
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self._selecionar_psd).grid(row=0, column=0)
        self._lbl_psd = ctk.CTkLabel(linha_psd, text="Nenhum arquivo selecionado",
                                     font=ctk.CTkFont("Segoe UI", 10),
                                     text_color=SUB, anchor="w")
        self._lbl_psd.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        # Camadas
        instrucao = ("Camadas do PSD — marque quais recebem o telefone"
                     if self._tipo == TipoModelo.PROFISSAO else
                     "Camadas do PSD — marque e escolha o campo de cada uma")
        ctk.CTkLabel(self, text=instrucao,
                     font=ctk.CTkFont("Segoe UI", 10, "bold"),
                     text_color=SUB, anchor="w").grid(
            row=2, column=0, sticky="w", padx=16, pady=(10, 2))

        self._lista = ctk.CTkScrollableFrame(
            self, fg_color=CARD, corner_radius=10,
            border_width=1, border_color=BORDA)
        self._lista.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 8))
        self._lista.grid_columnconfigure(0, weight=1)

        # Preview + ações
        rodape = ctk.CTkFrame(self, fg_color=FUNDO, corner_radius=0)
        rodape.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 14))
        rodape.grid_columnconfigure(0, weight=1)

        self._lbl_preview = ctk.CTkLabel(rodape, text="", fg_color=CARD,
                                         corner_radius=10, height=140)
        self._lbl_preview.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        ctk.CTkButton(rodape, text=" Pré-visualizar", height=36,
                     image=icons.imagem(icons.OLHO, tam=14, cor=TEXTO), compound="left",
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self._pre_visualizar).grid(row=1, column=0, sticky="w")
        ctk.CTkButton(rodape, text="Cancelar", height=36,
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self.destroy).grid(row=1, column=1, padx=8)
        ctk.CTkButton(rodape, text=" Salvar", height=36,
                     image=icons.imagem(icons.SALVAR, tam=14, cor=TEXTO_SOBRE_VERDE), compound="left",
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=TEXTO_SOBRE_VERDE,
                     command=self._salvar).grid(row=1, column=2, sticky="e")

    @staticmethod
    def _nome_curto(path: str, max_len: int = 60) -> str:
        return path if len(path) <= max_len else "..." + path[-(max_len - 3):]

    # ── Ações ─────────────────────────────────────────────────────────────────

    def _selecionar_psd(self):
        path = filedialog.askopenfilename(
            title="Selecionar PSD de produção",
            filetypes=[("Arquivo Photoshop", "*.psd *.psb")])
        if not path:
            return
        self._lbl_psd.configure(text=self._nome_curto(path))
        self._carregar_camadas(path)

    def _rotulos_campo(self) -> list[str]:
        return [rotulo for _, rotulo in CAMPOS_POR_TIPO[self._tipo.value]]

    def _chave_para_rotulo(self, chave: str) -> str:
        for k, rotulo in CAMPOS_POR_TIPO[self._tipo.value]:
            if k == chave:
                return rotulo
        return self._rotulos_campo()[0]

    def _rotulo_para_chave(self, rotulo: str) -> str:
        for k, r in CAMPOS_POR_TIPO[self._tipo.value]:
            if r == rotulo:
                return k
        return CAMPOS_POR_TIPO[self._tipo.value][0][0]

    def _carregar_camadas(self, psd_path: str, mapa_existente: dict | None = None):
        from infrastructure.psd.reader import listar_camadas
        for w in self._lista.winfo_children():
            w.destroy()
        self._usar.clear()
        self._campo_var.clear()
        self._vertical_var.clear()
        self._linha_vertical.clear()

        try:
            self._camadas = listar_camadas(psd_path)
        except DTFError as e:
            messagebox.showerror("Erro ao abrir PSD", str(e))
            return

        self._psd_path = psd_path
        # Candidatas primeiro, maior área primeiro (heurística: número maior = costas)
        camadas_ordenadas = sorted(
            self._camadas,
            key=lambda c: (not c["candidata_telefone"], -(c["w"] * c["h"])))

        # Contador pra sugerir numero_costas (maior) antes de numero_peito (menor)
        candidatas_numericas_vistas = 0

        for c in camadas_ordenadas:
            existente = mapa_existente.get(c["nome"]) if mapa_existente else None
            if existente is not None:
                marcado = True
                campo_sugerido = existente.campo
                vertical_sugerido = existente.vertical
            elif self._tipo == TipoModelo.PROFISSAO:
                marcado = c["candidata_telefone"]
                campo_sugerido = "telefone"
                vertical_sugerido = False
            else:
                nome_upper = c["nome"].upper()
                if "NOME" in nome_upper:
                    marcado, campo_sugerido = True, "nome"
                elif c["candidata_telefone"]:
                    marcado = True
                    campo_sugerido = ("numero_costas" if candidatas_numericas_vistas == 0
                                      else "numero_peito")
                    candidatas_numericas_vistas += 1
                else:
                    marcado, campo_sugerido = False, CAMPOS_POR_TIPO["TIME"][1][0]
                vertical_sugerido = False

            self._criar_linha(c, marcado, campo_sugerido, vertical_sugerido)

        if not self._camadas:
            ctk.CTkLabel(self._lista, text="Nenhuma camada visível encontrada no PSD.",
                         text_color=SUB).grid(padx=10, pady=10)

    def _criar_linha(self, c: dict, marcado: bool, campo_sugerido: str, vertical_sugerido: bool):
        nome = c["nome"]
        linha = ctk.CTkFrame(self._lista, fg_color="transparent")
        linha.grid(sticky="ew", padx=6, pady=3)

        usar_var = ctk.BooleanVar(value=marcado)
        self._usar[nome] = usar_var
        destaque = " 📱" if c["candidata_telefone"] else ""
        texto = f"{nome}{destaque}   ({c['w']}×{c['h']}px, pos {c['x']},{c['y']})"

        if self._tipo == TipoModelo.PROFISSAO:
            ctk.CTkCheckBox(
                linha, variable=usar_var, text=texto,
                font=ctk.CTkFont("Segoe UI", 10), text_color=TEXTO,
                fg_color=VERDE, hover_color=VERDE_HOVER).pack(side="left", anchor="w")
            return

        # Time: checkbox + dropdown de campo + toggle vertical (só quando Nome)
        ctk.CTkCheckBox(
            linha, variable=usar_var, text=texto,
            font=ctk.CTkFont("Segoe UI", 10), text_color=TEXTO,
            fg_color=VERDE, hover_color=VERDE_HOVER, width=1).pack(side="left", anchor="w")

        campo_var = ctk.StringVar(value=self._chave_para_rotulo(campo_sugerido))
        self._campo_var[nome] = campo_var
        menu = ctk.CTkOptionMenu(
            linha, variable=campo_var, values=self._rotulos_campo(),
            width=140, height=26, fg_color=CARD, text_color=TEXTO,
            button_color=VERDE_CLARO, button_hover_color=VERDE_CLARO,
            dropdown_fg_color=CARD,
            command=lambda _v, n=nome: self._atualizar_vertical_visivel(n))
        menu.pack(side="left", padx=(10, 6))

        vertical_var = ctk.BooleanVar(value=vertical_sugerido)
        self._vertical_var[nome] = vertical_var
        chk_vertical = ctk.CTkCheckBox(
            linha, variable=vertical_var, text="Vertical (girar 90°)",
            font=ctk.CTkFont("Segoe UI", 9), text_color=SUB,
            fg_color=VERDE, hover_color=VERDE_HOVER)
        chk_vertical.pack(side="left")
        self._linha_vertical[nome] = chk_vertical
        self._atualizar_vertical_visivel(nome)

    def _atualizar_vertical_visivel(self, nome: str):
        chk = self._linha_vertical.get(nome)
        if not chk:
            return
        eh_nome = self._rotulo_para_chave(self._campo_var[nome].get()) == "nome"
        if eh_nome:
            chk.pack(side="left")
        else:
            chk.pack_forget()

    def _mapeamento_selecionado(self) -> dict[str, dict]:
        """{nome_da_camada: {"campo": ..., "vertical": bool}} das camadas marcadas."""
        resultado = {}
        for nome, var in self._usar.items():
            if not var.get():
                continue
            if self._tipo == TipoModelo.PROFISSAO:
                resultado[nome] = {"campo": "telefone", "vertical": False}
            else:
                campo = self._rotulo_para_chave(self._campo_var[nome].get())
                vertical = self._vertical_var[nome].get() if campo == "nome" else False
                resultado[nome] = {"campo": campo, "vertical": vertical}
        return resultado

    def _pre_visualizar(self):
        mapeamento = self._mapeamento_selecionado()
        if not self._psd_path or not mapeamento:
            messagebox.showinfo("Pré-visualização",
                "Selecione um PSD e ao menos uma camada primeiro.")
            return
        try:
            from infrastructure.psd.reader import construir_modelo
            from services.renderer import renderizar_arte
            modelo_tmp = construir_modelo(
                self._entry_nome.get().strip() or "PREVIEW", self._tipo,
                self._psd_path, mapeamento)
            dados_exemplo = {campo: DADOS_EXEMPLO[campo]
                             for campo in {v["campo"] for v in mapeamento.values()}}
            pedido_tmp = Pedido(id=0, modelo_id=0, profissao=modelo_tmp.profissao,
                                 dados=dados_exemplo, prioridade=Prioridade.NORMAL)
            img = renderizar_arte(pedido_tmp, modelo_tmp, self._fonte)
        except DTFError as e:
            messagebox.showerror("Erro na pré-visualização", str(e))
            return

        escala = min(PREVIEW_MAX_W / img.width, 1.0)
        miniatura = img.resize(
            (max(1, int(img.width * escala)), max(1, int(img.height * escala))),
            Image.LANCZOS)
        # Fundo branco só para visualização (a arte real é exportada transparente)
        fundo = Image.new("RGB", miniatura.size, (245, 245, 245))
        fundo.paste(miniatura, (0, 0), miniatura)
        self._preview_img = ctk.CTkImage(light_image=fundo, dark_image=fundo,
                                         size=miniatura.size)
        self._lbl_preview.configure(image=self._preview_img, text="",
                                    height=miniatura.height + 10)

    def _salvar(self):
        from infrastructure.db import modelos_repo
        from infrastructure.psd.reader import construir_modelo
        from infrastructure.filesystem import copiar_psd_local

        nome_modelo = self._entry_nome.get().strip()
        mapeamento  = self._mapeamento_selecionado()

        if not nome_modelo:
            messagebox.showwarning("Campo obrigatório", "Digite o nome.")
            return
        if not self._psd_path:
            messagebox.showwarning("Campo obrigatório", "Selecione o PSD de produção.")
            return
        if not mapeamento:
            messagebox.showwarning("Camadas obrigatórias",
                "Marque ao menos uma camada de personalização.")
            return

        try:
            psd_local = copiar_psd_local(self._psd_path, nome_modelo)
            modelo_novo = construir_modelo(nome_modelo, self._tipo, psd_local, mapeamento)
            if self._combo_selecao is not None:
                modelo_novo.grupo = self._combo_selecao.get().strip().upper()
            if self._modelo:
                modelo_novo.id = self._modelo.id
                modelos_repo.atualizar_modelo(self._db, modelo_novo)
                acao_auditoria = "EDITADO"
            else:
                modelo_novo.id = modelos_repo.inserir_modelo(self._db, modelo_novo)
                acao_auditoria = "CRIADO"
        except DTFError as e:
            messagebox.showerror("Erro ao salvar modelo", str(e))
            return

        from infrastructure.db import eventos_repo
        from core import session
        eventos_repo.registrar(
            self._db, f"MODELO_{acao_auditoria}", session.operador_atual,
            entidade_tipo="modelo", entidade_id=modelo_novo.id,
            detalhes=f"{modelo_novo.profissao} — PSD: {self._nome_curto(psd_local, 50)}")

        # Miniatura da lista de Modelos é gerada aqui (1x) e cacheada em disco —
        # a tela de listagem só lê esse PNG depois, nunca re-renderiza o PSD.
        # Melhor esforço: se falhar, a lista mostra "—" e não trava o cadastro.
        try:
            from services import thumbnail_service
            thumbnail_service.gerar_e_salvar(modelo_novo, self._fonte)
        except Exception:
            pass

        messagebox.showinfo("Modelo salvo", f"'{nome_modelo}' cadastrado com sucesso.")
        if self._on_saved:
            self._on_saved()
        self.destroy()
