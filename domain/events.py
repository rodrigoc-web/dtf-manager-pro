"""
domain/events.py — EventBus para comunicação desacoplada entre camadas.
A UI e o log são consumidores. O core e os services nunca dependem da UI.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any
from enum import Enum, auto


class TipoEvento(Enum):
    PRODUCAO_INICIADA   = auto()
    PEDIDO_VALIDADO     = auto()
    PEDIDO_INVALIDO     = auto()
    RENDER_CONCLUIDO    = auto()
    ARTE_SALVA          = auto()
    PDF_SALVO           = auto()
    PRODUCAO_CONCLUIDA  = auto()
    PRODUCAO_ERRO       = auto()
    LOG_INFO            = auto()
    LOG_OK              = auto()
    LOG_ERRO            = auto()
    LOG_AVISO           = auto()
    SHEETS_CONECTADO    = auto()
    SHEETS_ERRO         = auto()
    UPDATE_DISPONIVEL   = auto()


@dataclass
class Evento:
    tipo:     TipoEvento
    mensagem: str = ""
    dados:    Any = None


class EventBus:
    _inst: "EventBus | None" = None

    def __init__(self):
        self._handlers: dict[TipoEvento, list[Callable]] = {}

    @classmethod
    def get(cls) -> "EventBus":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def subscribe(self, tipo: TipoEvento, fn: Callable[[Evento], None]):
        self._handlers.setdefault(tipo, []).append(fn)

    def subscribe_all(self, fn: Callable[[Evento], None]):
        for tipo in TipoEvento:
            self.subscribe(tipo, fn)

    def publish(self, tipo: TipoEvento,
                mensagem: str = "", dados: Any = None):
        ev = Evento(tipo=tipo, mensagem=mensagem, dados=dados)
        for fn in self._handlers.get(tipo, []):
            try:
                fn(ev)
            except Exception as e:
                print(f"[EventBus] erro em handler: {e}")

    def reset(self):
        self._handlers.clear()
        self.__class__._inst = None
