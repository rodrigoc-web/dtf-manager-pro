"""
ui/telas/modelos_screen.py — Tela "Modelos": lista os modelos cadastrados
(Profissões ou Times, em abas separadas) e permite cadastrar/editar/
remover via ModeloDialog.

Miniaturas da lista vêm de um PNG pequeno cacheado em disco (gerado 1x no
cadastro/edição, ver services/thumbnail_service.py) — a tela aqui só LÊ
esse arquivo, nunca re-renderiza o PSD sozinha. Modelo sem PNG ainda
(cadastrado antes desse cache existir) mostra "—" na lista e SÓ é
renderizado quando o usuário efetivamente passa o mouse (1 de cada vez,
sob demanda) — nunca em lote. Já existiu uma versão que tentava gerar
todos os pendentes em background assim que a tela abria: mesmo limitando
a 2 threads, isso deixava o app pesado de verdade (PSD real é grande,
psd-tools/numpy são pesados) — sob demanda é o único jeito de manter isso
leve com muitos modelos cadastrados.

A pré-visualização ao passar o mouse é um PAINEL FIXO ao lado da lista,
não um popup flutuante (`ctk.CTkToplevel`) — uma versão anterior usava
popup e, numa lista longa com imagens grandes, o popup ficava sobreposto
às linhas abaixo dele; isso confundia os eventos <Enter>/<Leave> do Tk
(o popup, sendo uma janela do SO separada por cima, "rouba" os eventos de
mouse das linhas por baixo) e os popups se acumulavam na tela sem fechar.
Um painel fixo dentro da própria janela não tem esse problema — é só um
widget normal, os eventos de hover da lista continuam funcionando normal.
"""
from __future__ import annotations
import queue
import concurrent.futures
import customtkinter as ctk
from tkinter import messagebox

from domain.enums import TipoModelo
from ui.theme import (FUNDO, VERDE, VERDE_HOVER, VERDE_CLARO, CARD, BORDA,
                      TEXTO, SUB, BRANCO, VERMELHO, VERMELHO_BG)
from ui.dialogs.modelo_dialog import ModeloDialog
from ui import icons

ABAS = [(TipoModelo.PROFISSAO, icons.CAMADAS, "Profissões"), (TipoModelo.TIME, icons.PECA, "Times")]


class ModelosScreen(ctk.CTkFrame):
    TAM_MINIATURA = 56
    TAM_PREVIEW = 300
    LARGURA_PAINEL = 340

    def __init__(self, master, db_path: str, fonte_path: str, **kw):
        super().__init__(master, fg_color=FUNDO, corner_radius=0, **kw)
        self._db      = db_path
        self._fonte   = fonte_path
        self._modelos = []
        self._aba_ativa = TipoModelo.PROFISSAO
        self._modelo_preview_pendente: int | None = None   # id em geração, se o painel está esperando

        # Memoização em memória do CTkImage já decodificado do PNG em disco —
        # evita reler/redecodificar o arquivo a cada tecla digitada na busca.
        # None = já tentou ler e não tem miniatura em disco ainda.
        self._cache_imagem: dict[int, "ctk.CTkImage | None"] = {}
        self._em_geracao: set[int] = set()   # ids sendo gerados agora (no máx. 1, por hover)

        # Geração sob demanda (hover num modelo sem PNG ainda) roda numa
        # thread só — nunca em lote — pra não pesar o app.
        self._fila_geracao: queue.Queue = queue.Queue()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.bind("<Destroy>", self._ao_destruir)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(3, weight=1)

        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(14, 8))
        topo.grid_columnconfigure(0, weight=1)
        self._lbl_titulo = ctk.CTkLabel(topo, text="Modelos",
                     font=ctk.CTkFont("Segoe UI", 15, "bold"),
                     text_color=TEXTO)
        self._lbl_titulo.grid(row=0, column=0, sticky="w")
        self._btn_novo = ctk.CTkButton(topo, text="+  Novo modelo", height=36,
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
                     command=self._novo_modelo)
        self._btn_novo.grid(row=0, column=1, sticky="e")

        self._montar_abas()
        self._montar_busca()

        self._lista = ctk.CTkScrollableFrame(
            self, fg_color=CARD, corner_radius=10,
            border_width=1, border_color=BORDA)
        self._lista.grid(row=3, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        self._lista.grid_columnconfigure(0, weight=1)

        self._montar_painel_preview()

        self.atualizar()
        self._drenar_fila_geracao()

    def _ao_destruir(self, event):
        if event.widget is self:
            self._executor.shutdown(wait=False, cancel_futures=True)

    # ── Abas Profissões / Times ─────────────────────────────────────────────

    def _montar_abas(self):
        abas = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10,
                            border_width=1, border_color=BORDA, height=44)
        abas.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))
        abas.grid_propagate(False)
        self._botoes_aba: dict[TipoModelo, ctk.CTkButton] = {}
        self._img_aba_inativa: dict[TipoModelo, "ctk.CTkImage"] = {}
        self._img_aba_ativa:   dict[TipoModelo, "ctk.CTkImage"] = {}
        for tipo, ico, titulo in ABAS:
            self._img_aba_inativa[tipo] = icons.imagem(ico, tam=14, cor=SUB)
            self._img_aba_ativa[tipo]   = icons.imagem(ico, tam=14, cor=BRANCO)
            btn = ctk.CTkButton(
                abas, text=f"  {titulo}", image=self._img_aba_inativa[tipo], compound="left",
                height=34, corner_radius=8,
                fg_color="transparent", text_color=SUB, hover_color=VERDE_CLARO,
                font=ctk.CTkFont("Segoe UI", 11, "bold"),
                command=lambda t=tipo: self._trocar_aba(t))
            btn.pack(side="left", padx=6, pady=5)
            self._botoes_aba[tipo] = btn
        self._marcar_aba_ativa()

    def _marcar_aba_ativa(self):
        for tipo, btn in self._botoes_aba.items():
            if tipo == self._aba_ativa:
                btn.configure(fg_color=VERDE, text_color=BRANCO, image=self._img_aba_ativa[tipo])
            else:
                btn.configure(fg_color="transparent", text_color=SUB,
                             image=self._img_aba_inativa[tipo])

    def _trocar_aba(self, tipo: TipoModelo):
        if tipo == self._aba_ativa:
            return
        self._aba_ativa = tipo
        self._marcar_aba_ativa()
        self._busca.delete(0, "end")
        self.atualizar()

    # ── Busca (visual "pill" moderno) ────────────────────────────────────────

    def _montar_busca(self):
        pill = ctk.CTkFrame(self, fg_color=CARD, corner_radius=18,
                            border_width=1, border_color=BORDA, height=40)
        pill.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))
        pill.grid_propagate(False)
        pill.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(pill, text=icons.BUSCAR, font=icons.fonte(13),
                     text_color=SUB, fg_color="transparent").grid(
            row=0, column=0, padx=(14, 4), pady=6)
        self._busca = ctk.CTkEntry(
            pill, height=36, fg_color="transparent", border_width=0,
            placeholder_text="Buscar por nome...",
            font=ctk.CTkFont("Segoe UI", 11))
        self._busca.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=2)
        self._busca.bind("<KeyRelease>", lambda e: self._renderizar())

    # ── Painel de pré-visualização (fixo, ao lado da lista) ─────────────────

    def _montar_painel_preview(self):
        painel = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10,
                              border_width=1, border_color=BORDA, width=self.LARGURA_PAINEL)
        painel.grid(row=3, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        painel.grid_propagate(False)

        self._lbl_preview_nome = ctk.CTkLabel(
            painel, text="Pré-visualização", font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=TEXTO, wraplength=self.LARGURA_PAINEL - 32)
        self._lbl_preview_nome.pack(padx=16, pady=(18, 10))

        self._lbl_preview_img = ctk.CTkLabel(
            painel, text="Passe o mouse sobre\num modelo na lista",
            font=ctk.CTkFont("Segoe UI", 10), text_color=SUB,
            fg_color=FUNDO, corner_radius=8,
            width=self.TAM_PREVIEW, height=self.TAM_PREVIEW)
        self._lbl_preview_img.pack(padx=16, pady=(0, 18))

    def atualizar(self):
        from infrastructure.db import modelos_repo
        self._modelos = modelos_repo.listar_modelos(
            self._db, tipo=self._aba_ativa, apenas_ativos=True)
        self._renderizar()

    def _renderizar(self):
        for w in self._lista.winfo_children():
            w.destroy()

        eh_time = self._aba_ativa == TipoModelo.TIME
        rotulo_aba = "profissões" if not eh_time else "times"
        termo = self._busca.get().strip().lower()
        modelos = [m for m in self._modelos if termo in m.profissao.lower()] if termo else self._modelos
        if eh_time:
            modelos = sorted(modelos, key=lambda m: (m.grupo or "~SEM SELEÇÃO", m.profissao))

        self._lbl_titulo.configure(
            text=f"Modelos  ·  {len(self._modelos)} {rotulo_aba} cadastrada(s)")

        if not self._modelos:
            ctk.CTkLabel(self._lista,
                         text=f"Nenhum modelo de {rotulo_aba} cadastrado ainda. "
                              f"Clique em '+ Novo modelo' para começar.",
                         text_color=SUB).grid(padx=14, pady=14, sticky="w")
            return
        if not modelos:
            ctk.CTkLabel(self._lista, text=f"Nenhum resultado contém '{termo}'.",
                         text_color=SUB).grid(padx=14, pady=14, sticky="w")
            return

        linha_grid = 0
        grupo_atual = object()  # sentinela — nunca bate com o 1º grupo real
        for m in modelos:
            if eh_time and m.grupo != grupo_atual:
                grupo_atual = m.grupo
                ctk.CTkLabel(self._lista,
                             text=(grupo_atual or "SEM SELEÇÃO").upper(),
                             font=ctk.CTkFont("Segoe UI", 10, "bold"),
                             text_color=VERDE, anchor="w").grid(
                    row=linha_grid, column=0, sticky="w", padx=10, pady=(12, 2))
                linha_grid += 1

            linha = ctk.CTkFrame(self._lista, fg_color="transparent")
            linha.grid(row=linha_grid, column=0, sticky="ew", padx=8, pady=4)
            linha.grid_columnconfigure(1, weight=1)
            linha_grid += 1

            self._montar_miniatura(linha, m)

            info = ctk.CTkFrame(linha, fg_color="transparent")
            info.grid(row=0, column=1, sticky="w", padx=(10, 0))
            ctk.CTkLabel(info, text=m.profissao,
                         font=ctk.CTkFont("Segoe UI", 12, "bold"),
                         text_color=TEXTO, anchor="w").pack(anchor="w")
            ctk.CTkLabel(info,
                         text=f"{len(m.camadas)} camada(s) · {m.canvas_w}×{m.canvas_h}px",
                         font=ctk.CTkFont("Segoe UI", 9),
                         text_color=SUB, anchor="w").pack(anchor="w")

            botoes = ctk.CTkFrame(linha, fg_color="transparent")
            botoes.grid(row=0, column=2, sticky="e")
            ctk.CTkButton(botoes, text=" Editar", width=80, height=28,
                         image=icons.imagem(icons.LAPIS, tam=13, cor=TEXTO), compound="left",
                         fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                         border_color=BORDA, border_width=1,
                         command=lambda m=m: self._editar_modelo(m)).pack(side="left", padx=4)
            ctk.CTkButton(botoes, text=" Remover", width=90, height=28,
                         image=icons.imagem(icons.LIXEIRA, tam=13, cor=VERMELHO), compound="left",
                         fg_color=CARD, text_color=VERMELHO, hover_color=VERMELHO_BG,
                         border_color=BORDA, border_width=1,
                         command=lambda m=m: self._remover_modelo(m)).pack(side="left", padx=(4, 0))
            ctk.CTkButton(botoes, text="", width=28, height=28,
                         image=icons.imagem(icons.HISTORICO, tam=13, cor=SUB),
                         fg_color=CARD, hover_color=VERDE_CLARO,
                         border_color=BORDA, border_width=1,
                         command=lambda m=m: self._ver_auditoria(m)).pack(side="left", padx=(4, 0))

            ctk.CTkFrame(self._lista, fg_color=BORDA, height=1,
                        corner_radius=0).grid(row=linha_grid - 1, column=0, sticky="ews", pady=(38, 0))

    def _novo_modelo(self):
        ModeloDialog(self, self._db, self._fonte, tipo=self._aba_ativa, on_saved=self.atualizar)

    def _editar_modelo(self, modelo):
        modelo_id = modelo.id
        ModeloDialog(self, self._db, self._fonte, modelo=modelo,
                     on_saved=lambda: (self._cache_imagem.pop(modelo_id, None), self.atualizar()))

    def _remover_modelo(self, modelo):
        from infrastructure.db import modelos_repo, auditoria_repo
        from core import session
        if messagebox.askyesno("Remover modelo",
            f"Remover '{modelo.profissao}'?\n\n"
            "Pedidos já produzidos com este modelo continuam no histórico."):
            modelos_repo.remover_modelo(self._db, modelo.id)
            auditoria_repo.registrar(self._db, modelo.id, session.operador_atual, "REMOVIDO")
            self._cache_imagem.pop(modelo.id, None)
            self.atualizar()

    def _ver_auditoria(self, modelo):
        from ui.dialogs.auditoria_dialog import AuditoriaDialog
        AuditoriaDialog(self, self._db, modelo)

    # ── Miniatura + painel de pré-visualização (vitrine, estilo card) ───────
    # Modelo sem PNG em disco mostra "—" na lista — NUNCA gera automático,
    # só quando o usuário efetivamente passa o mouse (1 de cada vez). O
    # preview em si atualiza o painel fixo (não um popup — ver nota no topo
    # do arquivo sobre por que popup causava sobreposição na lista).

    def _montar_miniatura(self, linha, modelo):
        img_ctk = self._obter_imagem(modelo)

        if img_ctk is not None:
            lbl = ctk.CTkLabel(linha, image=img_ctk, text="", fg_color=FUNDO,
                               corner_radius=8, width=self.TAM_MINIATURA, height=self.TAM_MINIATURA)
            lbl.image = img_ctk
        else:
            lbl = ctk.CTkLabel(linha, text="—", width=self.TAM_MINIATURA, height=self.TAM_MINIATURA,
                               fg_color=FUNDO, corner_radius=8, text_color=SUB,
                               font=ctk.CTkFont("Segoe UI", 14))

        lbl.grid(row=0, column=0)
        lbl.bind("<Enter>", lambda e, m=modelo: self._atualizar_preview(m))

    def _obter_imagem(self, modelo) -> "ctk.CTkImage | None":
        """Só lê o PNG já cacheado em disco — nunca abre o PSD aqui."""
        if modelo.id in self._cache_imagem:
            return self._cache_imagem[modelo.id]

        from services import thumbnail_service
        pil_img = thumbnail_service.carregar(modelo.id)
        img_ctk = None
        if pil_img is not None:
            escala = min(self.TAM_MINIATURA / pil_img.width, self.TAM_MINIATURA / pil_img.height)
            tam = (max(1, int(pil_img.width * escala)), max(1, int(pil_img.height * escala)))
            img_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=tam)
        self._cache_imagem[modelo.id] = img_ctk
        return img_ctk

    def _atualizar_preview(self, modelo):
        from services import thumbnail_service
        self._lbl_preview_nome.configure(text=modelo.profissao)
        pil_img = thumbnail_service.carregar(modelo.id)

        if pil_img is None:
            self._modelo_preview_pendente = modelo.id
            self._lbl_preview_img.configure(image=None, text="Gerando pré-visualização...")
            if modelo.id not in self._em_geracao:
                self._agendar_geracao_sob_demanda(modelo)
            return

        self._modelo_preview_pendente = None
        self._exibir_preview(pil_img)

    def _exibir_preview(self, pil_img):
        escala = min(self.TAM_PREVIEW / pil_img.width, self.TAM_PREVIEW / pil_img.height, 1.0)
        tam = (max(1, int(pil_img.width * escala)), max(1, int(pil_img.height * escala)))
        img_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=tam)
        self._lbl_preview_img.configure(image=img_ctk, text="")
        self._lbl_preview_img.image = img_ctk

    def _agendar_geracao_sob_demanda(self, modelo):
        """Só roda quando o usuário passa o mouse num modelo sem PNG ainda —
        no máximo 1 de cada vez (1 worker só), nunca em lote."""
        self._em_geracao.add(modelo.id)

        def worker():
            from services import thumbnail_service
            thumbnail_service.gerar_e_salvar(modelo, self._fonte)
            self._fila_geracao.put(modelo.id)

        self._executor.submit(worker)

    def _drenar_fila_geracao(self):
        houve_novo = False
        try:
            while True:
                modelo_id = self._fila_geracao.get_nowait()
                self._em_geracao.discard(modelo_id)
                self._cache_imagem.pop(modelo_id, None)
                houve_novo = True

                # Se o painel ainda estiver esperando esse modelo (usuário
                # ainda com o mouse em cima ou não mudou de item), atualiza.
                if self._modelo_preview_pendente == modelo_id:
                    from services import thumbnail_service
                    pil_img = thumbnail_service.carregar(modelo_id)
                    self._modelo_preview_pendente = None
                    if pil_img is not None:
                        self._exibir_preview(pil_img)
                    else:
                        self._lbl_preview_img.configure(
                            image=None, text="Não foi possível gerar\na pré-visualização.")
        except queue.Empty:
            pass
        if houve_novo:
            self._renderizar()   # atualiza a miniatura inline — raro, 1 modelo por vez
        try:
            self.after(200, self._drenar_fila_geracao)
        except Exception:
            pass   # tela já foi destruída
