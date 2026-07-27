"""
core/logger.py — Logger estruturado via EventBus.
Use este módulo em vez de print() em qualquer parte do sistema.
"""
from __future__ import annotations
from domain.events import EventBus, TipoEvento


def info(msg: str):
    EventBus.get().publish(TipoEvento.LOG_INFO, msg)


def ok(msg: str):
    EventBus.get().publish(TipoEvento.LOG_OK, msg)


def erro(msg: str):
    EventBus.get().publish(TipoEvento.LOG_ERRO, msg)


def aviso(msg: str):
    EventBus.get().publish(TipoEvento.LOG_AVISO, msg)


def producao_iniciada(msg: str = ""):
    EventBus.get().publish(TipoEvento.PRODUCAO_INICIADA, msg)


def producao_concluida(msg: str = "", dados=None):
    EventBus.get().publish(TipoEvento.PRODUCAO_CONCLUIDA, msg, dados)


def producao_erro(msg: str = ""):
    EventBus.get().publish(TipoEvento.PRODUCAO_ERRO, msg)


def render_concluido(msg: str = ""):
    EventBus.get().publish(TipoEvento.RENDER_CONCLUIDO, msg)


def pedido_validado(msg: str = "", dados=None):
    EventBus.get().publish(TipoEvento.PEDIDO_VALIDADO, msg, dados)


def pedido_invalido(msg: str = "", dados=None):
    EventBus.get().publish(TipoEvento.PEDIDO_INVALIDO, msg, dados)
