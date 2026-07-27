"""
domain/models.py — Entidades do domínio DTF MANAGER PRO.
Sem dependência de infraestrutura, UI ou serviços externos.

Cada "Modelo" (Profissão ou Time) é calibrado uma vez pelo usuário na tela
Gerenciar Modelos, e guarda sua própria lista de camadas — por isso `Camada`
carrega o nome E o campo que representa (telefone / nome / número peito /
número costas), em vez de ter slots fixos como no sistema de camisas original.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .enums import Status, Prioridade, EstadoPedido, TipoModelo


@dataclass(frozen=True, slots=True)
class Camada:
    """Uma camada do PSD onde um campo de personalização deve ser escrito."""
    nome: str            # nome da camada no PSD (ex.: "NÚMERO copiar 2")
    campo: str            # "telefone" | "nome" | "numero_peito" | "numero_costas"
    x: int
    y: int
    w: int
    h: int
    vertical: bool = False   # só relevante pra campo "nome" (girar 90°)

    @property
    def text_bbox(self) -> tuple[int, int, int, int]:
        return (0, 0, self.w, self.h)


@dataclass
class Modelo:
    """
    Um modelo cadastrado (Profissão ou Time): aponta para o PSD de produção
    escolhido pelo usuário e a lista de camadas de personalização.
    """
    id:          Optional[int]
    profissao:   str
    psd_path:    str
    canvas_w:    int
    canvas_h:    int
    text_color:  tuple[int, int, int, int]
    tipo:        TipoModelo = TipoModelo.PROFISSAO
    grupo:       str = ""        # só p/ TIME: nome da seleção/país (ex.: "BRASIL")
    camadas:     list[Camada] = field(default_factory=list)
    ativo:       bool = True
    criado_em:   str  = ""

    @property
    def valido(self) -> bool:
        return bool(self.camadas) and self.canvas_w > 0 and self.canvas_h > 0


@dataclass
class Pedido:
    id:           Optional[int]
    modelo_id:    int
    profissao:    str          # nome do modelo, desnormalizado p/ exibição sem join
    dados:        dict[str, str] = field(default_factory=dict)
    operador:     str          = ""
    marketplace:  str          = ""
    quantidade:   int          = 1
    prioridade:   Prioridade   = Prioridade.NORMAL
    status:       Status       = Status.PENDENTE
    criado_em:    str          = ""
    produzido_em: str          = ""
    lote_id:      str          = ""
    mensagem_erro: str         = ""
    ordem:        int          = 0
    estado:       EstadoPedido = field(default=EstadoPedido.NOVO, compare=False)

    @property
    def resumo(self) -> str:
        """Texto curto do pedido para listas — telefone (Profissão) ou nome+números (Time)."""
        if "telefone" in self.dados:
            return self.dados["telefone"]
        partes = [self.dados.get("nome", "")]
        if self.dados.get("numero_peito"):
            partes.append(f"P:{self.dados['numero_peito']}")
        if self.dados.get("numero_costas"):
            partes.append(f"C:{self.dados['numero_costas']}")
        return " ".join(p for p in partes if p) or "—"

    @property
    def completo(self) -> bool:
        return bool(self.profissao.strip()) and any(v.strip() for v in self.dados.values())


@dataclass
class Lote:
    id:       str
    numero:   int
    pedidos:  list[Pedido] = field(default_factory=list)
    pasta:    str          = ""

    @property
    def total(self) -> int:
        return sum(p.quantidade for p in self.pedidos)

    def contagem_por_profissao(self) -> dict[str, int]:
        from collections import Counter
        c: Counter = Counter()
        for p in self.pedidos:
            c[p.profissao] += p.quantidade
        return dict(c)


@dataclass
class ResultadoProducao:
    sucesso:           bool
    lote:              Optional[Lote] = None
    arquivo_png:       str            = ""
    arquivo_pdf:       str            = ""
    arquivo_relatorio: str            = ""
    erros:             list[str]      = field(default_factory=list)
    modo_teste:        bool           = False
