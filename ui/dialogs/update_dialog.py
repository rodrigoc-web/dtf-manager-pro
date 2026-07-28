"""
ui/dialogs/update_dialog.py — Avisa quando há uma versão nova disponível
(checada 1x na abertura do programa, via updater.py + GitHub Releases) e
deixa o operador escolher "Atualizar agora" ou "Depois" — nunca atualiza
sozinho sem perguntar, pra não interromper alguém no meio de um pedido.
"""
from __future__ import annotations
import queue
import customtkinter as ctk
from ui.theme import FUNDO, VERDE, VERDE_HOVER, VERDE_CLARO, CARD, BORDA, TEXTO, SUB, BRANCO, VERMELHO, TEXTO_SOBRE_VERDE
from ui import icons


class UpdateDialog(ctk.CTkToplevel):
    def __init__(self, master, base_dir, resultado, on_reiniciar=None, **kw):
        super().__init__(master, **kw)
        self._base_dir = base_dir
        self._resultado = resultado
        self._on_reiniciar = on_reiniciar

        self.title("Atualização disponível")
        self.geometry("440x380")
        self.minsize(400, 320)
        self.configure(fg_color=FUNDO)
        from ui.components.titlebar import aplicar_padrao_janela
        aplicar_padrao_janela(self)
        self.protocol("WM_DELETE_WINDOW", self._fechar_se_nao_rodando)

        self._rodando = False
        self._montar_aviso()
        self.grab_set()

    # ── Tela 1: aviso + notas de lançamento ─────────────────────────────────

    def _montar_aviso(self):
        for w in self.winfo_children():
            w.destroy()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        topo = ctk.CTkFrame(self, fg_color=VERDE, corner_radius=0, height=54)
        topo.grid(row=0, column=0, sticky="ew")
        topo.grid_propagate(False)
        icons.rotulo(topo, icons.ATUALIZAR, f"Nova versão: {self._resultado.versao_remota}",
                    tam_icone=14, tam_texto=13, negrito=True,
                    cor_icone=TEXTO_SOBRE_VERDE, cor_texto=TEXTO_SOBRE_VERDE).pack(side="left", padx=16, pady=14)

        ctk.CTkLabel(self, text="O que mudou nessa versão:",
                     font=ctk.CTkFont("Segoe UI", 10, "bold"),
                     text_color=SUB, anchor="w").grid(row=1, column=0, sticky="w", padx=16, pady=(14, 4))

        notas = ctk.CTkTextbox(self, fg_color=CARD, border_width=1, border_color=BORDA,
                               text_color=TEXTO, font=ctk.CTkFont("Segoe UI", 11), wrap="word")
        notas.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 12))
        notas.insert("1.0", self._resultado.notas or "(sem notas de lançamento)")
        notas.configure(state="disabled")

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
        ctk.CTkButton(rodape, text="Depois", height=36,
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self.destroy).pack(side="left")
        ctk.CTkButton(rodape, text=" Atualizar agora", height=36,
                     image=icons.imagem(icons.ATUALIZAR, tam=13, cor=TEXTO_SOBRE_VERDE), compound="left",
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=TEXTO_SOBRE_VERDE,
                     command=self._iniciar_atualizacao).pack(side="right")

    def _fechar_se_nao_rodando(self):
        if not self._rodando:
            self.destroy()

    # ── Tela 2: progresso da instalação ──────────────────────────────────────

    def _iniciar_atualizacao(self):
        self._rodando = True
        for w in self.winfo_children():
            w.destroy()
        self.grid_columnconfigure(0, weight=1)

        topo = ctk.CTkFrame(self, fg_color=VERDE, corner_radius=0, height=54)
        topo.grid(row=0, column=0, sticky="ew")
        topo.grid_propagate(False)
        icons.rotulo(topo, icons.ATUALIZAR, "Atualizando...", tam_icone=14, tam_texto=13,
                    negrito=True, cor_icone=TEXTO_SOBRE_VERDE, cor_texto=TEXTO_SOBRE_VERDE).pack(side="left", padx=16, pady=14)

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=1, column=0, sticky="ew", padx=20, pady=30)
        corpo.grid_columnconfigure(0, weight=1)

        self._lbl_status = ctk.CTkLabel(corpo, text="Preparando...",
                                        font=ctk.CTkFont("Segoe UI", 11), text_color=TEXTO)
        self._lbl_status.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self._barra = ctk.CTkProgressBar(corpo, height=8, progress_color=VERDE,
                                         fg_color=BORDA, corner_radius=4)
        self._barra.grid(row=1, column=0, sticky="ew")
        self._barra.set(0)

        # Os callbacks do Updater rodam numa thread de background — nunca
        # tocar widget/self.after direto de lá (mesmo RuntimeError já visto
        # na geração de miniatura). Só empilha na fila; quem drena é o
        # polling na thread principal (_drenar_fila).
        self._fila: queue.Queue = queue.Queue()
        from updater import Updater
        Updater(self._base_dir).instalar_async(
            self._resultado,
            cb_status=lambda s: self._fila.put(("status", s)),
            cb_progresso=lambda p: self._fila.put(("progresso", p)),
            cb_concluido=lambda v: self._fila.put(("concluido", v)),
            cb_erro=lambda e: self._fila.put(("erro", e)),
        )
        self._drenar_fila()

    def _drenar_fila(self):
        try:
            while True:
                tipo, valor = self._fila.get_nowait()
                if tipo == "status":
                    self._lbl_status.configure(text=valor)
                elif tipo == "progresso":
                    self._barra.set(valor / 100)
                elif tipo == "concluido":
                    self._concluido(valor)
                    return   # não reagenda — a instalação terminou
                elif tipo == "erro":
                    self._erro(valor)
                    return
        except queue.Empty:
            pass
        try:
            self.after(150, self._drenar_fila)
        except Exception:
            pass   # dialog já foi destruído

    def _concluido(self, versao_nova: str):
        self._lbl_status.configure(text=f"Instalado! Reiniciando para v{versao_nova}...")
        self._barra.set(1.0)
        self.after(1200, self._reiniciar)

    def _reiniciar(self):
        self.destroy()
        if self._on_reiniciar:
            self._on_reiniciar()

    def _erro(self, mensagem: str):
        self._rodando = False
        for w in self.winfo_children():
            w.destroy()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        topo = ctk.CTkFrame(self, fg_color=VERMELHO, corner_radius=0, height=54)
        topo.grid(row=0, column=0, sticky="ew")
        topo.grid_propagate(False)
        icons.rotulo(topo, icons.AVISO, "Erro na atualização", tam_icone=14, tam_texto=13,
                    negrito=True, cor_icone=BRANCO, cor_texto=BRANCO).pack(side="left", padx=16, pady=14)

        ctk.CTkLabel(self, text=mensagem, font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TEXTO, wraplength=380, justify="left").grid(
            row=1, column=0, sticky="nw", padx=16, pady=16)

        ctk.CTkButton(self, text="Fechar", height=36,
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self.destroy).grid(row=2, column=0, sticky="e", padx=16, pady=(0, 16))
