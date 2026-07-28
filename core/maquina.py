"""
core/maquina.py — Nome do computador local, pra Central de Auditoria saber
EM QUAL máquina cada evento aconteceu (fábrica com vários postos/operadores,
cada um no seu próprio computador).
"""
from __future__ import annotations
import os
import socket


def nome_computador() -> str:
    return os.environ.get("COMPUTERNAME") or socket.gethostname() or ""
