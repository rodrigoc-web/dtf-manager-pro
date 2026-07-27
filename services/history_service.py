"""
services/history_service.py — Histórico CSV e relatório PDF do lote.
O contador de lotes agora vive em infrastructure/db/lotes_repo.py (SQLite);
este módulo cuida só do export legível em CSV e do relatório do lote.
"""
from __future__ import annotations
import os, csv
from pathlib import Path
from domain.models import Lote
from core.utils import agora_str
import core.logger as log

COLUNAS = ["lote", "data", "hora", "operador", "total", "profissoes"]


def _operadores_do_lote(lote: Lote) -> str:
    """Um lote pode conter pedidos de operadores diferentes (cada um definido
    na criação do pedido, não mais por lote) — junta os distintos pro CSV."""
    vistos = []
    for p in lote.pedidos:
        if p.operador and p.operador not in vistos:
            vistos.append(p.operador)
    return ", ".join(vistos) if vistos else "—"


def registrar_historico(lote: Lote, historico_path: str):
    import datetime
    agora    = datetime.datetime.now()
    contagem = lote.contagem_por_profissao()
    linha    = {
        "lote":       lote.id,
        "data":       agora.strftime("%d/%m/%Y"),
        "hora":       agora.strftime("%H:%M"),
        "operador":   _operadores_do_lote(lote),
        "total":      lote.total,
        "profissoes": "; ".join(f"{k}:{v}" for k, v in contagem.items()),
    }
    novo = not Path(historico_path).exists()
    with open(historico_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        if novo:
            w.writeheader()
        w.writerow(linha)
    log.ok("historico.csv atualizado.")


def gerar_relatorio(lote: Lote, pasta: str) -> str:
    try:
        from fpdf import FPDF
        return _fpdf(lote, pasta)
    except ImportError:
        return _txt(lote, pasta)


def _fpdf(lote: Lote, pasta: str) -> str:
    from fpdf import FPDF

    def s(texto: str) -> str:
        return (str(texto).replace("_", " ").replace("—", "-")
                .encode("latin-1", errors="replace").decode("latin-1"))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 12, s(f"DTF MANAGER PRO - {lote.id}"), fill=True, ln=True, align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, s(f"Gerado em: {agora_str()}  |  Total: {lote.total}  |  "
                     f"Operador(es): {_operadores_do_lote(lote)}"), ln=True)
    pdf.ln(4)

    cols   = ["#", "Profissão", "Dados", "Operador", "Qtd.", "Prioridade"]
    widths = [10, 55, 45, 35, 15, 25]
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    for c, w in zip(cols, widths):
        pdf.cell(w, 7, c, border=1, fill=True, align="C")
    pdf.ln()

    for i, p in enumerate(lote.pedidos):
        fill = i % 2 == 0
        pdf.set_fill_color(240, 244, 248 if fill else 255)
        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "", 8)
        vals = [str(i + 1), s(p.profissao[:28]), s(p.resumo[:26]),
                s(p.operador or "—"), str(p.quantidade), s(p.prioridade.value)]
        for v, w in zip(vals, widths):
            pdf.cell(w, 6, v, border=1, fill=fill)
        pdf.ln()

    nome = f"RELATORIO_{lote.id}.pdf"
    pdf.output(os.path.join(pasta, nome))
    log.ok(f"Relatório salvo: {nome}")
    return os.path.join(pasta, nome)


def _txt(lote: Lote, pasta: str) -> str:
    nome = f"RELATORIO_{lote.id}.txt"
    path = os.path.join(pasta, nome)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"DTF MANAGER PRO — {lote.id}\n")
        f.write(f"Total: {lote.total}\n\n")
        for i, p in enumerate(lote.pedidos, 1):
            f.write(f"{i}. {p.profissao} | {p.resumo} | "
                    f"operador {p.operador or '—'} | qtd {p.quantidade}\n")
    return path
