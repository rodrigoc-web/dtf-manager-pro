"""
domain/enums.py — Tipos enumerados do domínio DTF MANAGER PRO.
Sem strings mágicas em nenhum outro arquivo do projeto.
"""
from enum import Enum, auto


class Status(str, Enum):
    PENDENTE  = "PENDENTE"
    PRODUZIDO = "PRODUZIDO"
    ERRO      = "ERRO"


class Prioridade(str, Enum):
    NORMAL  = "NORMAL"
    URGENTE = "URGENTE"


class TipoModelo(str, Enum):
    """Categoria de modelo — decide quais campos de personalização existem."""
    PROFISSAO = "PROFISSAO"   # personalização: telefone
    TIME      = "TIME"        # personalização: nome, número peito, número costas


class ModoExecucao(Enum):
    PRODUCAO = auto()
    TESTE    = auto()


class EstadoPedido(Enum):
    """Máquina de estados de um pedido durante a produção. Cada transição é rastreável no log."""
    NOVO         = auto()
    VALIDADO     = auto()
    RENDERIZANDO = auto()
    ARTE_GERADA  = auto()
    EXPORTADO    = auto()
    FINALIZADO   = auto()
    ERRO         = auto()
