"""
core/session.py — Operador logado nesta instância/máquina. Estado simples de
processo (sem framework de auth) — cada computador da fábrica roda seu
próprio processo, então isso já isola por máquina; quando o backend
compartilhado existir, esse mesmo nome de operador vira o identificador
enviado ao servidor.
"""
from __future__ import annotations

operador_atual: str = ""


def definir_operador(nome: str) -> None:
    global operador_atual
    operador_atual = nome.strip()


def limpar() -> None:
    global operador_atual
    operador_atual = ""
