"""
ui/telas/pedidos_screen.py — Tela "Pedidos": categoria (Profissão/Time) com
cascata Seleção → Variação para Times, marketplace, formulário dinâmico,
importação em lote (Excel/CSV) e os botões de produção (Gerar Produção /
Modo teste), com barra de progresso e log ao vivo.

Sem campo de operador aqui de propósito — vai voltar futuramente via login
de acesso por operador (cada um só acessa seu próprio programa/instância),
não como texto livre digitado na hora de criar o pedido.
"""
from __future__ import annotations
import queue
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from domain.models import Pedido
from domain.enums import Prioridade, ModoExecucao, TipoModelo, EstadoPedido
from domain.events import EventBus, TipoEvento
from core.constants import CAMPOS_POR_TIPO
from core.exceptions import DTFError
from core import session
from ui.theme import (FUNDO, VERDE, VERDE_HOVER, VERDE_CLARO, CARD, BORDA,
                      TEXTO, SUB, BRANCO, VERMELHO, VERMELHO_BG)
from ui.components.log_area import LogArea
from ui import icons

_ETAPAS = {
    TipoEvento.PRODUCAO_INICIADA:  (5,   "Iniciando..."),
    TipoEvento.PEDIDO_VALIDADO:    (30,  "Validando pedidos..."),
    TipoEvento.RENDER_CONCLUIDO:   (65,  "Renderizando artes..."),
    TipoEvento.ARTE_SALVA:         (85,  "Salvando arquivos..."),
    TipoEvento.PDF_SALVO:          (95,  "Gerando PDF..."),
    TipoEvento.PRODUCAO_CONCLUIDA: (100, "Concluído!"),
    TipoEvento.PRODUCAO_ERRO:      (0,   ""),
}


class PedidosScreen(ctk.CTkFrame):
    _PLACEHOLDER_PROFISSAO = "Selecione a profissão"
    _PLACEHOLDER_SELECAO = "Selecione a seleção/time"
    _PLACEHOLDER_VARIACAO = "Selecione o modelo"
    _SENTINELA_ADICIONAR = "+  Adicionar novo..."

    def __init__(self, master, db_path: str, on_concluido=None, on_pedir_novo_modelo=None, **kw):
        super().__init__(master, fg_color=FUNDO, corner_radius=0, **kw)
        self._db = db_path
        self._modelos = []
        self._categoria = TipoModelo.PROFISSAO
        self._grupo_selecionado: str | None = None
        self._modelo_selecionado = None
        self._rodando = False
        self._on_concluido = on_concluido
        self._on_pedir_novo_modelo = on_pedir_novo_modelo

        # Resumo ao vivo da fila durante uma produção — os eventos chegam de
        # uma thread de background (production_service roda em thread), então
        # só empilham numa fila; quem drena e toca widget é o polling na
        # thread principal (mesmo padrão já usado pra geração de miniatura).
        self._fila_estados: queue.Queue = queue.Queue()
        self._fila_progresso: queue.Queue = queue.Queue()
        self._estados_pedidos: dict[int, EstadoPedido] = {}
        self._total_fila_atual = 0

        self.grid_columnconfigure(0, weight=1)
        # minsize garante a tabela visível de verdade mesmo numa janela baixa —
        # um height= direto no CTkScrollableFrame NÃO é suficiente aqui: com
        # sticky="nsew" + weight=1, o grid estica/encolhe o widget pro tamanho
        # da linha calculada, ignorando o height pedido na criação (foi assim
        # que a tabela sumiu por completo — 0px — na janela real do app).
        self.grid_rowconfigure(3, weight=1, minsize=140)

        icons.rotulo(self, icons.CLIPBOARD, "Pedidos", tam_icone=16, tam_texto=15,
                    negrito=True, cor_icone=TEXTO, cor_texto=TEXTO).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self._montar_form()
        self._montar_progresso()

        # Tabela dos pedidos adicionados (Pedido / Quantidade / Detalhes) —
        # fica ACIMA do log, é a base de dados que "Gerar Produção" processa.
        # height= é um MÍNIMO garantido: numa janela baixa, o formulário (que
        # cresceu bastante) podia espremer essa linha até sumir por completo
        # (0px, sem borda nem cabeçalho visíveis) — via de regra teste sempre
        # no tamanho de janela real do app (até 800px de altura), não numa
        # janela grande de teste que mascara esse tipo de colapso.
        self._lista = ctk.CTkScrollableFrame(
            self, fg_color=CARD, corner_radius=10, height=140,
            border_width=1, border_color=BORDA)
        self._lista.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 8))
        self._lista.grid_columnconfigure(0, weight=1)

        self._log = LogArea(self)
        self._log.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))

        self._registrar_progresso()
        self.atualizar()

    # ── Formulário ────────────────────────────────────────────────────────────

    def _montar_form(self):
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10,
                            border_width=1, border_color=BORDA)
        card.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)

        # Linha 0: categoria (Profissão / Time)
        linha_cat = ctk.CTkFrame(card, fg_color=FUNDO, corner_radius=8,
                                 border_width=1, border_color=BORDA, height=42)
        linha_cat.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))
        linha_cat.grid_propagate(False)
        self._botoes_categoria: dict[TipoModelo, ctk.CTkButton] = {}
        for tipo, texto in ((TipoModelo.PROFISSAO, "Profissão"), (TipoModelo.TIME, "Time")):
            btn = ctk.CTkButton(
                linha_cat, text=texto, height=32, width=110, corner_radius=8,
                font=ctk.CTkFont("Segoe UI", 11, "bold"),
                fg_color="transparent", text_color=SUB, hover_color=VERDE_CLARO,
                command=lambda t=tipo: self._trocar_categoria(t))
            btn.pack(side="left", padx=5, pady=5)
            self._botoes_categoria[tipo] = btn
        self._marcar_categoria_ativa()

        # Linha 1: marketplace (lista suspensa) + prioridade
        # (operador removido — vai voltar via login de acesso por operador no
        # futuro, não como campo digitado aqui)
        linha1 = ctk.CTkFrame(card, fg_color="transparent")
        linha1.grid(row=1, column=0, sticky="ew", padx=12)
        linha1.grid_columnconfigure(0, weight=1)

        bloco_mkt = ctk.CTkFrame(linha1, fg_color="transparent")
        bloco_mkt.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(bloco_mkt, text="Marketplace (origem do pedido)",
                     font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB, anchor="w").pack(anchor="w")
        self._combo_marketplace = ctk.CTkComboBox(
            bloco_mkt, values=self._com_adicionar(self._nomes_marketplaces()), height=34,
            command=self._on_selecionar_marketplace_combo)
        self._combo_marketplace.set("")
        self._combo_marketplace.pack(fill="x", pady=(2, 10))

        bloco_prio = ctk.CTkFrame(linha1, fg_color="transparent")
        bloco_prio.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(bloco_prio, text="Prioridade", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB, anchor="w").pack(anchor="w")
        self._combo_prioridade = ctk.CTkComboBox(
            bloco_prio, values=[Prioridade.NORMAL.value, Prioridade.URGENTE.value],
            height=34, width=120)
        self._combo_prioridade.pack(pady=(2, 10))

        # Linha 2: seleção de modelo — dinâmica conforme categoria (Profissão:
        # dropdown + telefone; Time: cascata Seleção -> Variação)
        self._frame_selecao = ctk.CTkFrame(card, fg_color="transparent")
        self._frame_selecao.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 4))
        self._montar_selecao_modelo()

        # Linha 3: botões de ação
        botoes = ctk.CTkFrame(card, fg_color="transparent")
        botoes.grid(row=3, column=0, sticky="ew", padx=12, pady=(10, 10))
        ctk.CTkButton(botoes, text=" Adicionar pedido", height=34,
                     image=icons.imagem(icons.MAIS, tam=13, cor=BRANCO), compound="left",
                     fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
                     command=self._adicionar_rapido).pack(side="left")
        ctk.CTkButton(botoes, text=" Importar planilha", height=34,
                     image=icons.imagem(icons.IMPORTAR, tam=13, cor=TEXTO), compound="left",
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self._importar_planilha).pack(side="left", padx=8)
        ctk.CTkButton(botoes, text="Modo teste", height=34,
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self._confirmar_teste).pack(side="left", padx=(0, 8))
        ctk.CTkButton(botoes, text=" Abrir pasta de saída", height=34,
                     image=icons.imagem(icons.CAIXA, tam=13, cor=TEXTO), compound="left",
                     fg_color=CARD, text_color=TEXTO, hover_color=VERDE_CLARO,
                     border_color=BORDA, border_width=1,
                     command=self._abrir_pasta_saida).pack(side="left")

        # Linha 4: Gerar Produção — botão compacto (estilo Adobe), alinhado à
        # direita, não precisa gritar pra ser o principal. Fica cinza quando
        # não há nada pra produzir, verde quando há pedidos na fila.
        self._btn_gerar = ctk.CTkButton(
            card, text="▶  Gerar Produção", height=36, width=180, corner_radius=8,
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            fg_color=VERDE, hover_color=VERDE_HOVER, text_color=BRANCO,
            command=self._confirmar_gerar)
        self._btn_gerar.grid(row=4, column=0, sticky="e", padx=12, pady=(0, 12))

    def _com_adicionar(self, valores: list[str]) -> list[str]:
        """Acrescenta a opção '+ Adicionar novo...' ao final de uma lista
        suspensa — selecioná-la abre o cadastro do item correspondente
        (modelo/marketplace) sem precisar sair da tela de Pedidos."""
        return list(valores) + [self._SENTINELA_ADICIONAR]

    def _marcar_categoria_ativa(self):
        for tipo, btn in self._botoes_categoria.items():
            if tipo == self._categoria:
                btn.configure(fg_color=VERDE, text_color=BRANCO)
            else:
                btn.configure(fg_color="transparent", text_color=SUB)

    def _trocar_categoria(self, tipo: TipoModelo):
        if tipo == self._categoria:
            return
        self._categoria = tipo
        self._grupo_selecionado = None
        self._modelo_selecionado = None
        self._marcar_categoria_ativa()
        self._montar_selecao_modelo()

    # ── Seleção de modelo (dinâmica: Profissão direta, ou Time em cascata) ──

    def _montar_selecao_modelo(self):
        for w in self._frame_selecao.winfo_children():
            w.destroy()

        if self._categoria == TipoModelo.PROFISSAO:
            linha = ctk.CTkFrame(self._frame_selecao, fg_color="transparent")
            linha.pack(fill="x")
            bloco_prof = ctk.CTkFrame(linha, fg_color="transparent")
            bloco_prof.pack(side="left", fill="x", expand=True, padx=(0, 8))
            ctk.CTkLabel(bloco_prof, text="Profissão",
                         font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=SUB, anchor="w").pack(anchor="w")
            self._combo_profissao = ctk.CTkComboBox(
                bloco_prof, values=self._com_adicionar(self._nomes_profissoes()), height=34,
                command=self._on_selecionar_profissao_combo)
            self._combo_profissao.set(self._PLACEHOLDER_PROFISSAO)
            self._combo_profissao.pack(fill="x", pady=(2, 0))

            bloco_qtd = ctk.CTkFrame(linha, fg_color="transparent")
            bloco_qtd.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(bloco_qtd, text="Qtd.", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=SUB, anchor="w").pack(anchor="w")
            self._entry_qtd = ctk.CTkEntry(bloco_qtd, height=34, width=60)
            self._entry_qtd.insert(0, "1")
            self._entry_qtd.pack(pady=(2, 0))

            bloco_tel = ctk.CTkFrame(linha, fg_color="transparent")
            bloco_tel.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(bloco_tel, text="Telefone",
                         font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=SUB, anchor="w").pack(anchor="w")
            self._entry_telefone = ctk.CTkEntry(bloco_tel, height=34, placeholder_text="Ex.: (11) 91234-5678")
            self._entry_telefone.pack(fill="x", pady=(2, 0))
            return

        # TIME — Seleção e Modelo lado a lado (as duas em lista suspensa); a
        # tabela de jogadores abaixo usa esse MESMO modelo pra todas as
        # linhas -- serve pra gerar N nomes diferentes de UM modelo de cada
        # vez, igual à planilha do DTF MANAGER original.
        linha_a = ctk.CTkFrame(self._frame_selecao, fg_color="transparent")
        linha_a.pack(fill="x")

        bloco_selecao = ctk.CTkFrame(linha_a, fg_color="transparent")
        bloco_selecao.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(bloco_selecao, text="Seleção / time",
                     font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB, anchor="w").pack(anchor="w")
        self._combo_selecao = ctk.CTkComboBox(
            bloco_selecao, values=self._com_adicionar(self._nomes_selecoes()), height=34,
            command=self._on_selecionar_selecao_combo)
        self._combo_selecao.set(self._PLACEHOLDER_SELECAO)
        self._combo_selecao.pack(fill="x", pady=(2, 8))

        bloco_modelo = ctk.CTkFrame(linha_a, fg_color="transparent")
        bloco_modelo.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(bloco_modelo, text="Modelo",
                     font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB, anchor="w").pack(anchor="w")
        self._combo_variacao = ctk.CTkComboBox(
            bloco_modelo, values=self._com_adicionar(self._nomes_variacoes()), height=34,
            command=self._on_selecionar_variacao_combo)
        self._combo_variacao.set(self._PLACEHOLDER_VARIACAO)
        self._combo_variacao.pack(fill="x", pady=(2, 8))

        self._frame_variacao = ctk.CTkFrame(self._frame_selecao, fg_color="transparent")
        self._frame_variacao.pack(fill="x")
        if self._grupo_selecionado:
            self._montar_linha_variacao()

    def _montar_linha_variacao(self):
        for w in self._frame_variacao.winfo_children():
            w.destroy()
        self._linhas_time: list[dict[str, ctk.CTkBaseClass]] = []

        # Tabela em lote (Nome / Nº Peito / Nº Costas / Qtd) — todas as
        # linhas usam o modelo escolhido acima; preenche vários jogadores de
        # uma vez e "Adicionar pedido" cria todos juntos, sem repetir a
        # seleção do modelo pra cada um (igual à planilha do DTF MANAGER
        # original: nome / número frente / número costas por linha).
        ctk.CTkLabel(self._frame_variacao, text="Jogadores (preencha quantas linhas precisar)",
                     font=ctk.CTkFont("Segoe UI", 9, "bold"),
                     text_color=SUB, anchor="w").pack(anchor="w")

        cabecalho = ctk.CTkFrame(self._frame_variacao, fg_color="transparent")
        cabecalho.pack(fill="x", padx=2, pady=(4, 2))
        for col, texto, peso in ((0, "Nome", 2), (1, "Nº Peito", 1), (2, "Nº Costas", 1), (3, "Qtd.", 0)):
            cabecalho.grid_columnconfigure(col, weight=peso)
            ctk.CTkLabel(cabecalho, text=texto, font=ctk.CTkFont("Segoe UI", 9, "bold"),
                         text_color=SUB, anchor="w").grid(row=0, column=col, sticky="w", padx=(4, 6))

        self._painel_jogadores = ctk.CTkScrollableFrame(
            self._frame_variacao, fg_color=FUNDO, corner_radius=8, height=130,
            border_width=1, border_color=BORDA)
        self._painel_jogadores.pack(fill="x", pady=(0, 6))
        for col, peso in ((0, 2), (1, 1), (2, 1), (3, 0), (4, 0)):
            self._painel_jogadores.grid_columnconfigure(col, weight=peso)

        self._adicionar_linha_jogador()

        ctk.CTkButton(self._frame_variacao, text=" Adicionar linha", height=26,
                     image=icons.imagem(icons.MAIS, tam=11, cor=VERDE), compound="left",
                     fg_color="transparent", text_color=VERDE, hover_color=VERDE_CLARO,
                     command=self._adicionar_linha_jogador).pack(anchor="w")

    def _adicionar_linha_jogador(self):
        i = len(self._linhas_time)
        entry_nome = ctk.CTkEntry(self._painel_jogadores, height=30, placeholder_text="Nome")
        entry_nome.grid(row=i, column=0, sticky="ew", padx=(4, 4), pady=3)
        entry_peito = ctk.CTkEntry(self._painel_jogadores, height=30, placeholder_text="10")
        entry_peito.grid(row=i, column=1, sticky="ew", padx=(0, 4), pady=3)
        entry_costas = ctk.CTkEntry(self._painel_jogadores, height=30, placeholder_text="10")
        entry_costas.grid(row=i, column=2, sticky="ew", padx=(0, 4), pady=3)
        entry_qtd = ctk.CTkEntry(self._painel_jogadores, height=30, width=44)
        entry_qtd.insert(0, "1")
        entry_qtd.grid(row=i, column=3, sticky="ew", padx=(0, 4), pady=3)

        linha = {"nome": entry_nome, "peito": entry_peito, "costas": entry_costas, "qtd": entry_qtd}
        btn_limpar = ctk.CTkButton(
            self._painel_jogadores, text="✕", width=26, height=26,
            fg_color="transparent", text_color=VERMELHO, hover_color=VERMELHO_BG,
            command=lambda ld=linha: self._limpar_linha_jogador(ld))
        btn_limpar.grid(row=i, column=4, padx=(0, 4), pady=3)
        self._linhas_time.append(linha)

    def _limpar_linha_jogador(self, linha: dict[str, ctk.CTkBaseClass]):
        """'Remover' só limpa os campos (nunca reindexar linhas no meio da
        tabela) — linhas totalmente em branco são simplesmente ignoradas na
        hora de adicionar os pedidos em lote."""
        linha["nome"].delete(0, "end")
        linha["peito"].delete(0, "end")
        linha["costas"].delete(0, "end")
        linha["qtd"].delete(0, "end")
        linha["qtd"].insert(0, "1")

    def _abrir_novo_modelo_time(self):
        if self._on_pedir_novo_modelo:
            self._on_pedir_novo_modelo(TipoModelo.TIME, self._grupo_selecionado)

    def _carregar_modelos(self):
        from infrastructure.db import modelos_repo
        self._modelos = modelos_repo.listar_modelos(self._db, apenas_ativos=True)

    # ── Profissão (dropdown simples — sem busca, telefone é sempre fixo) ────

    def _nomes_profissoes(self) -> list[str]:
        nomes = sorted(m.profissao for m in self._modelos if m.tipo == TipoModelo.PROFISSAO)
        return nomes or ["Nenhuma profissão cadastrada"]

    def _on_selecionar_profissao_combo(self, nome: str):
        if nome == self._SENTINELA_ADICIONAR:
            self._combo_profissao.set(self._PLACEHOLDER_PROFISSAO)
            if self._on_pedir_novo_modelo:
                self._on_pedir_novo_modelo(TipoModelo.PROFISSAO, None)
            return
        if nome == self._PLACEHOLDER_PROFISSAO:
            self._modelo_selecionado = None
            return
        self._modelo_selecionado = next(
            (m for m in self._modelos if m.tipo == TipoModelo.PROFISSAO and m.profissao == nome), None)

    # ── Marketplace (lista suspensa — sugestões + digitação livre p/ novos) ──

    _MARKETPLACES_PADRAO = ["Shopee", "Mercado Livre", "Instagram", "WhatsApp", "TikTok Shop", "Kwai"]

    def _nomes_marketplaces(self) -> list[str]:
        from infrastructure.db import pedidos_repo
        usados = pedidos_repo.marketplaces_recentes(self._db)
        vistos, resultado = set(), []
        for nome in usados + self._MARKETPLACES_PADRAO:
            if nome.lower() not in vistos:
                vistos.add(nome.lower())
                resultado.append(nome)
        return resultado

    def _on_selecionar_marketplace_combo(self, nome: str):
        # O campo já aceita digitação livre (basta digitar e sair) — o item
        # "+ Adicionar novo..." só limpa o campo e deixa o cursor pronto pra
        # digitar, servindo de atalho visível pra quem não percebeu que dá
        # pra digitar direto.
        if nome == self._SENTINELA_ADICIONAR:
            self._combo_marketplace.set("")
            self._combo_marketplace.focus_set()

    # ── Seleção/time (Time — 1º passo da cascata, dropdown) ─────────────────

    def _nomes_selecoes(self) -> list[str]:
        from infrastructure.db import modelos_repo
        grupos = modelos_repo.listar_grupos_time(self._db)
        return grupos or ["Nenhuma seleção cadastrada"]

    def _on_selecionar_selecao_combo(self, grupo: str):
        if grupo == self._SENTINELA_ADICIONAR:
            self._combo_selecao.set(self._PLACEHOLDER_SELECAO)
            self._abrir_novo_modelo_time()
            return
        from infrastructure.db import modelos_repo
        if grupo not in modelos_repo.listar_grupos_time(self._db):
            self._grupo_selecionado = None
            self._modelo_selecionado = None
            self._combo_variacao.configure(values=self._com_adicionar(self._nomes_variacoes()))
            self._combo_variacao.set(self._PLACEHOLDER_VARIACAO)
            for w in self._frame_variacao.winfo_children():
                w.destroy()
            return
        self._grupo_selecionado = grupo
        self._modelo_selecionado = None
        self._combo_variacao.configure(values=self._com_adicionar(self._nomes_variacoes()))
        self._combo_variacao.set(self._PLACEHOLDER_VARIACAO)
        self._montar_linha_variacao()

    # ── Modelo cadastrado / variação (Time — 2º passo da cascata, dropdown) ─

    def _nomes_variacoes(self) -> list[str]:
        nomes = sorted(m.profissao for m in self._modelos
                       if m.tipo == TipoModelo.TIME and m.grupo == self._grupo_selecionado)
        return nomes or ["Nenhum modelo cadastrado"]

    def _resolver_modelo_time(self, nome: str):
        return next(
            (m for m in self._modelos if m.tipo == TipoModelo.TIME
             and m.grupo == self._grupo_selecionado and m.profissao == nome), None)

    def _on_selecionar_variacao_combo(self, nome: str):
        if nome == self._SENTINELA_ADICIONAR:
            self._combo_variacao.set(self._PLACEHOLDER_VARIACAO)
            self._abrir_novo_modelo_time()
            return
        if nome == self._PLACEHOLDER_VARIACAO:
            self._modelo_selecionado = None
            return
        self._modelo_selecionado = self._resolver_modelo_time(nome)

    # ── Adicionar pedido ──────────────────────────────────────────────────────

    def _adicionar_rapido(self):
        if self._categoria == TipoModelo.TIME:
            self._adicionar_lote_time()
            return

        from infrastructure.db import pedidos_repo

        modelo = self._modelo_selecionado
        if not modelo:
            if not self._modelos:
                messagebox.showwarning("Nenhum modelo cadastrado",
                    "Cadastre um modelo em 'Modelos' antes de criar pedidos.")
            else:
                messagebox.showwarning("Profissão não escolhida",
                    "Escolha uma profissão na lista suspensa.")
            return

        dados = {"telefone": self._entry_telefone.get().strip()}
        faltando = [rotulo for chave, rotulo in CAMPOS_POR_TIPO[modelo.tipo.value]
                    if not dados.get(chave)]
        if faltando:
            messagebox.showwarning("Campos obrigatórios",
                f"Preencha: {', '.join(faltando)}.")
            return

        try:
            quantidade = max(1, int(self._entry_qtd.get().strip() or "1"))
        except ValueError:
            quantidade = 1

        pedido = Pedido(
            id=None, modelo_id=modelo.id, profissao=modelo.profissao,
            dados=dados, operador=session.operador_atual,
            marketplace=self._combo_marketplace.get().strip(),
            quantidade=quantidade, prioridade=Prioridade(self._combo_prioridade.get()))
        try:
            pedidos_repo.inserir_pedido(self._db, pedido)
        except DTFError as e:
            messagebox.showerror("Erro ao adicionar pedido", str(e))
            return

        self._combo_marketplace.configure(values=self._nomes_marketplaces())
        self._modelo_selecionado = None
        self._combo_profissao.set(self._PLACEHOLDER_PROFISSAO)
        self._entry_telefone.delete(0, "end")
        self._entry_qtd.delete(0, "end")
        self._entry_qtd.insert(0, "1")
        self.atualizar()

    def _adicionar_lote_time(self):
        """Cria um pedido por LINHA preenchida da tabela de jogadores, todos
        de uma vez, todos usando o MESMO modelo escolhido acima — evita
        repetir Seleção/Modelo pedido por pedido, que seria inviável pra um
        time inteiro (era assim que a planilha do DTF MANAGER original
        funcionava: nome / número frente / número costas por linha)."""
        from infrastructure.db import pedidos_repo

        modelo = self._modelo_selecionado
        if not modelo:
            if not self._grupo_selecionado:
                messagebox.showwarning("Seleção não escolhida",
                    "Escolha a seleção/time e depois o modelo cadastrado dela.")
            else:
                messagebox.showwarning("Modelo não escolhido",
                    "Escolha o modelo cadastrado na lista suspensa.")
            return

        marketplace = self._combo_marketplace.get().strip()
        prioridade = Prioridade(self._combo_prioridade.get())
        pedidos_prontos: list[Pedido] = []
        linhas_incompletas: list[int] = []

        for i, linha in enumerate(self._linhas_time, start=1):
            nome = linha["nome"].get().strip()
            peito = linha["peito"].get().strip()
            costas = linha["costas"].get().strip()
            if not nome and not peito and not costas:
                continue   # linha em branco — ignora, não é erro
            if not (nome and peito and costas):
                linhas_incompletas.append(i)
                continue
            try:
                qtd = max(1, int(linha["qtd"].get().strip() or "1"))
            except ValueError:
                qtd = 1
            pedidos_prontos.append(Pedido(
                id=None, modelo_id=modelo.id, profissao=modelo.profissao,
                dados={"nome": nome, "numero_peito": peito, "numero_costas": costas},
                operador=session.operador_atual,
                marketplace=marketplace, quantidade=qtd, prioridade=prioridade))

        if linhas_incompletas:
            messagebox.showwarning(
                "Linhas incompletas",
                "Preencha Nome, Nº Peito e Nº Costas nas linhas: "
                f"{', '.join(map(str, linhas_incompletas))}.\n"
                "(ou deixe a linha totalmente em branco pra ignorá-la)")
            return
        if not pedidos_prontos:
            messagebox.showwarning("Nenhum jogador preenchido",
                "Preencha ao menos uma linha com Nome, Nº Peito e Nº Costas.")
            return

        try:
            pedidos_repo.inserir_pedidos_em_lote(self._db, pedidos_prontos)
        except DTFError as e:
            messagebox.showerror("Erro ao adicionar pedidos", str(e))
            return

        self._combo_marketplace.configure(values=self._nomes_marketplaces())
        for linha in self._linhas_time:
            self._limpar_linha_jogador(linha)
        self.atualizar()

    # ── Importação em lote ───────────────────────────────────────────────────

    def _importar_planilha(self):
        from infrastructure.db import pedidos_repo
        from services import import_service

        path = filedialog.askopenfilename(
            title="Importar planilha de pedidos",
            filetypes=[("Planilhas", "*.csv *.xlsx *.xlsm")])
        if not path:
            return

        try:
            linhas = import_service.importar_arquivo(path)
            if not linhas:
                messagebox.showwarning("Planilha vazia", "O arquivo não tem linhas de dados.")
                return
            mapeamento = import_service.detectar_mapeamento(linhas[0].keys())
            pedidos, erros = import_service.converter_para_pedidos(
                linhas, mapeamento, self._modelos)
        except DTFError as e:
            messagebox.showerror("Erro na importação", str(e))
            return

        if pedidos:
            pedidos_repo.inserir_pedidos_em_lote(self._db, pedidos)

        resumo = f"{len(pedidos)} pedido(s) importado(s) com sucesso."
        if erros:
            resumo += f"\n\n{len(erros)} linha(s) com problema:\n" + "\n".join(erros[:15])
            if len(erros) > 15:
                resumo += f"\n... e mais {len(erros) - 15}."
        messagebox.showinfo("Importação concluída", resumo)
        self.atualizar()

    # ── Abrir pasta de saída (onde os PNG/PDF gerados ficam salvos) ─────────

    def _abrir_pasta_saida(self):
        import os
        from infrastructure.filesystem import output_dir
        try:
            os.startfile(str(output_dir()))
        except Exception as e:
            messagebox.showerror("Erro ao abrir pasta", str(e))

    # ── Progresso e execução da produção ─────────────────────────────────────

    def _montar_progresso(self):
        prog = ctk.CTkFrame(self, fg_color="transparent")
        prog.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 0))
        prog.grid_columnconfigure(0, weight=1)
        self._lbl_fila = ctk.CTkLabel(prog, text="", font=ctk.CTkFont("Segoe UI", 10, "bold"),
                                      text_color=TEXTO, anchor="w")
        self._lbl_fila.grid(row=0, column=0, sticky="w", pady=(0, 3))
        self._prog_bar = ctk.CTkProgressBar(prog, height=6, progress_color=VERDE,
                                            fg_color=BORDA, corner_radius=3)
        self._prog_bar.grid(row=1, column=0, sticky="ew")
        self._prog_bar.set(0)
        self._lbl_status = ctk.CTkLabel(prog, text="", font=ctk.CTkFont("Segoe UI", 9),
                                        text_color=SUB, anchor="w")
        self._lbl_status.grid(row=2, column=0, sticky="w", pady=(4, 0))

    def _registrar_progresso(self):
        # Os dois handlers abaixo são chamados pela thread de produção
        # (production_service roda em background) — nenhum dos dois pode
        # tocar widget/self.after direto de lá (RuntimeError "main thread
        # is not in main loop", já visto antes na geração de miniatura).
        # Os dois só empilham; quem drena e atualiza a UI é o polling único
        # abaixo, sempre na thread principal.
        bus = EventBus.get()
        for tipo, (pct, status) in _ETAPAS.items():
            bus.subscribe(tipo, lambda e, p=pct, s=status: self._fila_progresso.put((p, s)))
        bus.subscribe(TipoEvento.PEDIDO_ESTADO_MUDOU,
                      lambda e: self._fila_estados.put(e.dados))
        self._drenar_filas()

    def _set_progresso(self, pct: float, status: str):
        try:
            self._prog_bar.set(pct / 100)
            self._lbl_status.configure(text=status)
        except Exception:
            pass

    def _drenar_filas(self):
        # Drena as DUAS filas por completo — inclusive a de estados — ANTES
        # de reagir ao sinal de conclusão. Se `_restaurar()` fosse chamado no
        # meio do drenar (como era antes) e lançasse qualquer exceção, o
        # resto do método (a outra fila + o reagendamento do polling) nunca
        # rodava — os últimos eventos (EXPORTADO/FINALIZADO) ficavam presos
        # pra sempre e o resumo nunca fechava certo.
        concluido = False
        try:
            while True:
                pct, status = self._fila_progresso.get_nowait()
                if pct == "__concluido__":
                    concluido = True
                else:
                    self._set_progresso(pct, status)
        except queue.Empty:
            pass

        houve_novo = False
        try:
            while True:
                pedido_id, estado = self._fila_estados.get_nowait()
                self._estados_pedidos[pedido_id] = estado
                houve_novo = True
        except queue.Empty:
            pass
        if houve_novo:
            self._atualizar_resumo_fila()

        if concluido:
            self._restaurar()

        try:
            self.after(150, self._drenar_filas)
        except Exception:
            pass   # tela já foi destruída

    def _atualizar_resumo_fila(self):
        tocados = self._estados_pedidos
        concluidos = sum(1 for e in tocados.values() if e == EstadoPedido.FINALIZADO)
        erros = sum(1 for e in tocados.values() if e == EstadoPedido.ERRO)
        processando = len(tocados) - concluidos - erros
        aguardando = max(0, self._total_fila_atual - len(tocados))

        partes = [f"{aguardando} aguardando", f"{processando} processando", f"{concluidos} concluído(s)"]
        if erros:
            partes.append(f"{erros} erro(s)")
        self._lbl_fila.configure(text="  ·  ".join(partes))

    def _confirmar_gerar(self):
        if self._rodando:
            return
        if messagebox.askyesno("Confirmar produção",
            "Iniciar geração?\n\n"
            "• Pedidos PENDENTES serão processados\n"
            "• Status será alterado para PRODUZIDO", icon="question"):
            self._run(ModoExecucao.PRODUCAO)

    def _confirmar_teste(self):
        if self._rodando:
            return
        if messagebox.askyesno("Modo Teste",
            "Gerar artes em MODO TESTE?\n\n"
            "✅ Gera PNG, PDF e RELATÓRIO\n"
            "❌ NÃO altera o banco de pedidos", icon="info"):
            self._run(ModoExecucao.TESTE)

    def _run(self, modo: ModoExecucao):
        from infrastructure.db import pedidos_repo
        self._rodando = True
        self._btn_gerar.configure(state="disabled", text="⏳   Aguarde...")

        # Reseta o resumo ao vivo pra essa execução — número real de pedidos
        # que vão entrar na fila, sem inventar nada antes do primeiro evento.
        self._estados_pedidos = {}
        self._total_fila_atual = len(pedidos_repo.listar_pendentes(self._db))
        self._atualizar_resumo_fila()

        def _worker():
            from services.production_service import executar
            import core.logger as log
            try:
                executar(modo)
            except Exception as e:
                log.erro(f"Erro inesperado: {e}")
            finally:
                # Mesmo cuidado de sempre: essa thread não pode chamar
                # self.after()/_restaurar() direto — só sinaliza via fila,
                # o polling (_drenar_filas) já rodando é quem chama de verdade.
                self._fila_progresso.put(("__concluido__", None))

        threading.Thread(target=_worker, daemon=True).start()

    def _restaurar(self):
        self._rodando = False
        self._btn_gerar.configure(state="normal", text="▶  Gerar Produção")
        self._prog_bar.set(0)
        self._lbl_status.configure(text="")
        self.atualizar()
        if self._on_concluido:
            self._on_concluido()

    # ── Tabela de pedidos (Pedido / Quantidade / Detalhes) ──────────────────
    # É essa lista (pedidos com status PENDENTE) que "Gerar Produção" processa
    # inteira, de uma vez, independente de quantidade ou profissão.

    def atualizar(self):
        from infrastructure.db import pedidos_repo
        self._carregar_modelos()
        if self._categoria == TipoModelo.PROFISSAO and hasattr(self, "_combo_profissao"):
            self._combo_profissao.configure(values=self._com_adicionar(self._nomes_profissoes()))
        if self._categoria == TipoModelo.TIME and hasattr(self, "_combo_selecao"):
            self._combo_selecao.configure(values=self._com_adicionar(self._nomes_selecoes()))
            if hasattr(self, "_combo_variacao"):
                self._combo_variacao.configure(values=self._com_adicionar(self._nomes_variacoes()))
        if hasattr(self, "_combo_marketplace"):
            self._combo_marketplace.configure(values=self._com_adicionar(self._nomes_marketplaces()))

        for w in self._lista.winfo_children():
            w.destroy()

        cabecalho = ctk.CTkFrame(self._lista, fg_color="transparent")
        cabecalho.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        cabecalho.grid_columnconfigure(0, weight=2)
        cabecalho.grid_columnconfigure(1, weight=2)
        cabecalho.grid_columnconfigure(2, weight=0)
        cabecalho.grid_columnconfigure(3, weight=0)
        for col, texto in ((0, "Pedido"), (1, "Detalhes"), (2, "Qtd."), (3, "Prioridade")):
            ctk.CTkLabel(cabecalho, text=texto, font=ctk.CTkFont("Segoe UI", 11, "bold"),
                         text_color=SUB, anchor="w").grid(row=0, column=col, sticky="w", padx=(0, 12))
        ctk.CTkFrame(self._lista, fg_color=BORDA, height=1, corner_radius=0).grid(
            row=1, column=0, sticky="ew", padx=10)

        pendentes = pedidos_repo.listar_pendentes(self._db)
        self._atualizar_estado_btn_gerar(len(pendentes))
        if not pendentes:
            ctk.CTkLabel(self._lista, text="Nenhum pedido pendente.",
                         text_color=SUB).grid(row=2, column=0, padx=14, pady=14, sticky="w")
            return

        for i, p in enumerate(pendentes):
            linha = ctk.CTkFrame(self._lista, fg_color="transparent")
            linha.grid(row=i + 2, column=0, sticky="ew", padx=10, pady=6)
            linha.grid_columnconfigure(0, weight=2)
            linha.grid_columnconfigure(1, weight=2)

            ctk.CTkLabel(linha, text=p.profissao, font=ctk.CTkFont("Segoe UI", 11),
                         text_color=TEXTO, anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 12))
            ctk.CTkLabel(linha, text=p.resumo, font=ctk.CTkFont("Segoe UI", 11),
                         text_color=TEXTO, anchor="w").grid(row=0, column=1, sticky="w", padx=(0, 12))
            ctk.CTkLabel(linha, text=str(p.quantidade), font=ctk.CTkFont("Segoe UI", 11),
                         text_color=TEXTO, anchor="w").grid(row=0, column=2, sticky="w", padx=(0, 12))

            if p.prioridade == Prioridade.URGENTE:
                chip = ctk.CTkLabel(linha, text=" URGENTE ", font=ctk.CTkFont("Segoe UI", 9, "bold"),
                                    text_color=VERMELHO, fg_color=VERMELHO_BG, corner_radius=6)
            else:
                chip = ctk.CTkLabel(linha, text="Normal", font=ctk.CTkFont("Segoe UI", 10),
                                    text_color=SUB)
            chip.grid(row=0, column=3, sticky="w", padx=(0, 12))

            botoes = ctk.CTkFrame(linha, fg_color="transparent")
            botoes.grid(row=0, column=4, sticky="e")
            ctk.CTkButton(botoes, text="▲", width=24, height=26,
                         font=ctk.CTkFont("Segoe UI", 10),
                         fg_color=CARD, text_color=SUB, hover_color=VERDE_CLARO,
                         border_color=BORDA, border_width=1,
                         command=lambda p=p: self._mover(p, "cima")).pack(side="left", padx=(0, 2))
            ctk.CTkButton(botoes, text="▼", width=24, height=26,
                         font=ctk.CTkFont("Segoe UI", 10),
                         fg_color=CARD, text_color=SUB, hover_color=VERDE_CLARO,
                         border_color=BORDA, border_width=1,
                         command=lambda p=p: self._mover(p, "baixo")).pack(side="left", padx=(0, 6))
            ctk.CTkButton(botoes, text=" Remover", width=80, height=26,
                         image=icons.imagem(icons.LIXEIRA, tam=12, cor=VERMELHO), compound="left",
                         fg_color=CARD, text_color=VERMELHO, hover_color=VERMELHO_BG,
                         border_color=BORDA, border_width=1,
                         command=lambda p=p: self._remover(p)).pack(side="left")

    def _atualizar_estado_btn_gerar(self, quantidade_pendentes: int):
        """Cinza quando não há nada pra produzir, verde quando há fila."""
        if quantidade_pendentes > 0:
            self._btn_gerar.configure(fg_color=VERDE, hover_color=VERDE_HOVER, state="normal")
        else:
            self._btn_gerar.configure(fg_color=BORDA, hover_color=BORDA, state="disabled")

    def _remover(self, pedido: Pedido):
        from infrastructure.db import pedidos_repo
        pedidos_repo.remover_pedido(self._db, pedido.id)
        self.atualizar()

    def _mover(self, pedido: Pedido, direcao: str):
        from infrastructure.db import pedidos_repo
        pedidos_repo.mover_pedido(self._db, pedido.id, direcao)
        self.atualizar()
