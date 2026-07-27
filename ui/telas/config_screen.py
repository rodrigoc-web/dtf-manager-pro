"""
ui/telas/config_screen.py — Tela "Configurações": operadores, meta diária de
produção, estoque de rolo DTF e backup manual. Tudo que antes só dava pra
mudar editando `core/constants.py` (e reconstruindo o .exe) agora fica
editável em tempo real, guardado em `configuracoes` (infrastructure/db).
"""
from __future__ import annotations
import datetime
import threading
import customtkinter as ctk
from tkinter import messagebox
from core.constants import META_DIA
from ui.theme import (FUNDO, CARD, BORDA, TEXTO, SUB, BRANCO,
                      VERDE, VERDE_HOVER, VERDE_CLARO, VERMELHO, VERMELHO_BG)
from ui import icons


class ConfigScreen(ctk.CTkFrame):
    def __init__(self, master, db_path: str, **kw):
        super().__init__(master, fg_color=FUNDO, corner_radius=0, **kw)
        self._db = db_path

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        icons.rotulo(topo, icons.ENGRENAGEM, "Configurações", tam_icone=16, tam_texto=15,
                    negrito=True, cor_icone=TEXTO, cor_texto=TEXTO).pack(anchor="w")

        self._corpo = ctk.CTkScrollableFrame(self, fg_color=FUNDO, corner_radius=0)
        self._corpo.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self._corpo.grid_columnconfigure(0, weight=1)

        self._montar_operadores()
        self._montar_meta_dia()
        self._montar_estoque()
        self._montar_backup()
        self.atualizar()

    def _card(self, titulo_icone, titulo_texto, row) -> ctk.CTkFrame:
        card = ctk.CTkFrame(self._corpo, fg_color=CARD, corner_radius=12,
                            border_width=1, border_color=BORDA)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        icons.rotulo(card, titulo_icone, titulo_texto, tam_icone=13, tam_texto=11,
                    negrito=True, cor_icone=TEXTO, cor_texto=TEXTO).pack(anchor="w", padx=16, pady=(14, 8))
        return card

    # ── Operadores ───────────────────────────────────────────────────────────

    def _montar_operadores(self):
        card = self._card(icons.ESTRELA, "OPERADORES", 0)
        self._lista_operadores = ctk.CTkFrame(card, fg_color="transparent")
        self._lista_operadores.pack(fill="x", padx=16)

        linha_add = ctk.CTkFrame(card, fg_color="transparent")
        linha_add.pack(fill="x", padx=16, pady=(6, 14))
        self._entry_operador = ctk.CTkEntry(linha_add, height=32, placeholder_text="Nome do operador")
        self._entry_operador.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(linha_add, text=" Adicionar", height=32, width=110,
                     image=icons.imagem(icons.MAIS, tam=12, cor=BRANCO), compound="left",
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
                     command=self._adicionar_operador).pack(side="left")

    def _adicionar_operador(self):
        from infrastructure.db import operadores_repo
        nome = self._entry_operador.get().strip()
        if not nome:
            messagebox.showwarning("Campo obrigatório", "Digite o nome do operador.")
            return
        operadores_repo.inserir_operador(self._db, nome)
        self._entry_operador.delete(0, "end")
        self.atualizar()

    def _desativar_operador(self, nome: str):
        from infrastructure.db import operadores_repo
        oid = operadores_repo.buscar_por_nome(self._db, nome)
        if oid is not None:
            operadores_repo.remover_operador(self._db, oid)
        self.atualizar()

    # ── Meta diária ──────────────────────────────────────────────────────────

    def _montar_meta_dia(self):
        card = self._card(icons.BANDEIRA, "META DIÁRIA DE PRODUÇÃO", 1)
        linha = ctk.CTkFrame(card, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=(0, 14))
        self._entry_meta = ctk.CTkEntry(linha, height=32, width=100)
        self._entry_meta.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(linha, text="peças por dia", font=ctk.CTkFont("Segoe UI", 10),
                     text_color=SUB).pack(side="left", padx=(0, 12))
        ctk.CTkButton(linha, text="Salvar", height=32, width=90,
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
                     command=self._salvar_meta).pack(side="left")

    def _salvar_meta(self):
        from infrastructure.db import config_repo
        try:
            valor = max(1, int(self._entry_meta.get().strip()))
        except ValueError:
            messagebox.showwarning("Valor inválido", "Digite um número inteiro maior que zero.")
            return
        config_repo.definir(self._db, "meta_dia", str(valor))
        messagebox.showinfo("Meta atualizada", f"Meta diária definida em {valor} peças.")

    # ── Estoque de rolo DTF ──────────────────────────────────────────────────

    def _montar_estoque(self):
        card = self._card(icons.CAIXA, "ESTOQUE DE ROLO DTF", 2)
        self._lbl_estoque_atual = ctk.CTkLabel(
            card, text="", font=ctk.CTkFont("Segoe UI", 20, "bold"), text_color=TEXTO, anchor="w")
        self._lbl_estoque_atual.pack(anchor="w", padx=16)

        linha_limite = ctk.CTkFrame(card, fg_color="transparent")
        linha_limite.pack(fill="x", padx=16, pady=(8, 8))
        ctk.CTkLabel(linha_limite, text="Avisar quando o estoque cair abaixo de (metros):",
                     font=ctk.CTkFont("Segoe UI", 10), text_color=SUB).pack(side="left", padx=(0, 8))
        self._entry_limite = ctk.CTkEntry(linha_limite, height=30, width=80)
        self._entry_limite.pack(side="left", padx=(0, 8))
        ctk.CTkButton(linha_limite, text="Salvar", height=30, width=80,
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
                     command=self._salvar_limite_estoque).pack(side="left")

        ctk.CTkButton(card, text=" Registrar reabastecimento", height=32,
                     image=icons.imagem(icons.MAIS, tam=12, cor=BRANCO), compound="left",
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
                     command=self._registrar_reabastecimento).pack(anchor="w", padx=16, pady=(0, 10))

        ctk.CTkLabel(card, text="Últimos movimentos", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB, anchor="w").pack(anchor="w", padx=16)
        self._lista_movimentos = ctk.CTkFrame(card, fg_color="transparent")
        self._lista_movimentos.pack(fill="x", padx=16, pady=(2, 14))

    def _salvar_limite_estoque(self):
        from infrastructure.db import estoque_repo
        try:
            valor = float(self._entry_limite.get().strip().replace(",", "."))
        except ValueError:
            messagebox.showwarning("Valor inválido", "Digite um número (ex.: 20 ou 20.5).")
            return
        estoque_repo.definir_limite_alerta(self._db, valor)
        self.atualizar()

    def _registrar_reabastecimento(self):
        from infrastructure.db import estoque_repo
        dialog = ctk.CTkInputDialog(text="Quantos metros de rolo foram adicionados?",
                                     title="Registrar reabastecimento")
        resposta = dialog.get_input()
        if not resposta:
            return
        try:
            metros = float(resposta.strip().replace(",", "."))
        except ValueError:
            messagebox.showwarning("Valor inválido", "Digite um número (ex.: 100 ou 100.5).")
            return
        estoque_repo.registrar_reabastecimento(self._db, metros, "Reabastecimento manual")
        self.atualizar()

    # ── Backup ───────────────────────────────────────────────────────────────

    def _montar_backup(self):
        card = self._card(icons.SALVAR, "BACKUP", 3)
        self._lbl_ultimo_backup = ctk.CTkLabel(
            card, text="", font=ctk.CTkFont("Segoe UI", 10), text_color=SUB, anchor="w")
        self._lbl_ultimo_backup.pack(anchor="w", padx=16)

        self._btn_backup = ctk.CTkButton(
            card, text=" Fazer backup agora", height=32,
            image=icons.imagem(icons.SALVAR, tam=12, cor=BRANCO), compound="left",
            fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
            command=self._backup_agora)
        self._btn_backup.pack(anchor="w", padx=16, pady=(8, 10))

        ctk.CTkLabel(card, text="Backups recentes", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB, anchor="w").pack(anchor="w", padx=16)
        self._lista_backups = ctk.CTkFrame(card, fg_color="transparent")
        self._lista_backups.pack(fill="x", padx=16, pady=(2, 14))

    def _backup_agora(self):
        # Zipar PSDs/miniaturas reais pode levar dezenas de segundos — roda numa
        # thread separada pra não congelar a tela (nunca tocar Tkinter direto
        # de dentro da thread, só via self.after no resultado).
        self._btn_backup.configure(state="disabled", text=" Fazendo backup...")

        def _worker():
            from services import backup_service
            try:
                caminho = backup_service.criar_backup()
                erro = None
            except Exception as e:
                caminho, erro = None, str(e)
            self.after(0, lambda: self._apos_backup(caminho, erro))

        threading.Thread(target=_worker, daemon=True).start()

    def _apos_backup(self, caminho, erro):
        self._btn_backup.configure(state="normal", text=" Fazer backup agora")
        if erro:
            messagebox.showerror("Erro ao fazer backup", erro)
            return
        messagebox.showinfo("Backup concluído", f"Backup salvo em:\n{caminho}")
        self.atualizar()

    def _abrir_pasta_backups(self):
        import os
        from services import backup_service
        try:
            os.startfile(str(backup_service.pasta_backups()))
        except Exception as e:
            messagebox.showerror("Erro ao abrir pasta", str(e))

    # ── Atualizar (dados) ────────────────────────────────────────────────────

    def atualizar(self):
        from infrastructure.db import operadores_repo, config_repo, estoque_repo
        from services import backup_service

        for w in self._lista_operadores.winfo_children():
            w.destroy()
        nomes = operadores_repo.listar_operadores(self._db)
        if not nomes:
            ctk.CTkLabel(self._lista_operadores, text="Nenhum operador cadastrado ainda.",
                         text_color=SUB).pack(anchor="w", pady=4)
        for nome in nomes:
            linha = ctk.CTkFrame(self._lista_operadores, fg_color="transparent")
            linha.pack(fill="x", pady=2)
            ctk.CTkLabel(linha, text=nome, font=ctk.CTkFont("Segoe UI", 11),
                         text_color=TEXTO, anchor="w").pack(side="left")
            ctk.CTkButton(linha, text="Desativar", height=24, width=90,
                         fg_color=CARD, text_color=VERMELHO, hover_color=VERMELHO_BG,
                         border_color=BORDA, border_width=1,
                         command=lambda n=nome: self._desativar_operador(n)).pack(side="right")

        meta_atual = config_repo.obter_int(self._db, "meta_dia", META_DIA)
        self._entry_meta.delete(0, "end")
        self._entry_meta.insert(0, str(meta_atual))

        estoque_atual = estoque_repo.estoque_atual_metros(self._db)
        self._lbl_estoque_atual.configure(text=f"{estoque_atual:.1f} m em estoque")
        self._entry_limite.delete(0, "end")
        self._entry_limite.insert(0, str(estoque_repo.limite_alerta_metros(self._db)))

        for w in self._lista_movimentos.winfo_children():
            w.destroy()
        movimentos = estoque_repo.listar_movimentos(self._db, limite=8)
        if not movimentos:
            ctk.CTkLabel(self._lista_movimentos, text="Nenhum movimento registrado ainda.",
                         text_color=SUB, font=ctk.CTkFont("Segoe UI", 9)).pack(anchor="w")
        for mov in movimentos:
            cor = VERDE if mov["metros"] >= 0 else VERMELHO
            sinal = "+" if mov["metros"] >= 0 else ""
            linha = ctk.CTkFrame(self._lista_movimentos, fg_color="transparent")
            linha.pack(fill="x", pady=1)
            ctk.CTkLabel(linha, text=f"{sinal}{mov['metros']:.1f}m", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=cor, width=70, anchor="w").pack(side="left")
            ctk.CTkLabel(linha, text=f"{mov['motivo'] or mov['tipo']}  ·  {mov['criado_em']}",
                         font=ctk.CTkFont("Segoe UI", 9), text_color=SUB, anchor="w").pack(side="left")

        backups = backup_service.listar_backups()
        for w in self._lista_backups.winfo_children():
            w.destroy()
        if not backups:
            self._lbl_ultimo_backup.configure(text="Nenhum backup feito ainda.")
            ctk.CTkLabel(self._lista_backups, text="—", text_color=SUB,
                         font=ctk.CTkFont("Segoe UI", 9)).pack(anchor="w")
        else:
            ultimo = backups[0]
            quando = datetime.datetime.fromtimestamp(ultimo.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
            self._lbl_ultimo_backup.configure(text=f"Último backup: {quando}")
            for b in backups[:5]:
                tam_mb = b.stat().st_size / (1024 * 1024)
                ctk.CTkLabel(self._lista_backups, text=f"{b.name}  ·  {tam_mb:.1f} MB",
                             font=ctk.CTkFont("Segoe UI", 9), text_color=SUB,
                             anchor="w").pack(anchor="w")
            ctk.CTkButton(self._lista_backups, text=" Abrir pasta de backups", height=26,
                         image=icons.imagem(icons.CAIXA, tam=11, cor=TEXTO), compound="left",
                         fg_color="transparent", text_color=TEXTO, hover_color=VERDE_CLARO,
                         command=self._abrir_pasta_backups).pack(anchor="w", pady=(4, 0))
