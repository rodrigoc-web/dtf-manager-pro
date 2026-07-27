"""
scripts/identificar_base_designs.py — Para as profissões SEM nenhum arquivo
de telefone, lista qualquer PSD/PSB existente na pasta (logo, mockup,
kit etc.) como ponto de partida para um designer adicionar a camada de
telefone. Não cadastra nada — é só um levantamento para revisão humana.

Uso:
    python scripts/identificar_base_designs.py "\\\\SERVIDOR\\Pasta\\PROFISSOES"
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PROFUNDIDADE_MAXIMA = 4
EXTENSOES_PSD = {".psd", ".psb"}

PROFISSOES_SEM_ARTE = [
    "ADESTRADOR", "APOIO", "ASSISTENCIA TECNICA", "ASSISTENTE-FEM",
    "AÇOUGUE", "AÇOUGUEIRO", "CANTINA-FEM", "CASA DE CARNES",
    "EDUCADOR", "EDUCADORA", "ENERGIA SOLAR", "ENFERMAGEM", "ENGENHEIRO",
    "FRETES", "FUNILARIA E PINTURA", "INSPETOR - masc", "INSPETORA-FEM",
    "INSTRUTOR DE TRANSITO", "INSULFILM AUTOMOTIVO", "LIMPEZA-FEM",
    "MECÂNICO DE MOTOS", "Mecânico Sublimada", "MERENDEIRA.FEM",
    "MONITOR ESCOLAR", "MOTOBOY", "NAMORADOS", "PADEIRO", "POSSO AJUDAR",
    "PRODUÇÃO", "PROFESSOR", "PROFESSORA", "SALVA VIDAS", "STAFF",
    "TÉCNICO EM ENFERMAGEM", "TÉCNICO EM INFORMÁTICA",
]


def _psds_da_pasta(pasta: Path) -> list[Path]:
    achados = []
    base_partes = len(pasta.parts)
    for arq in pasta.rglob("*"):
        if arq.suffix.lower() not in EXTENSOES_PSD:
            continue
        if len(arq.parts) - base_partes > PROFUNDIDADE_MAXIMA:
            continue
        achados.append(arq)
    return sorted(achados, key=lambda p: p.stat().st_mtime, reverse=True)


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/identificar_base_designs.py <pasta_raiz_das_profissoes>")
        sys.exit(1)

    raiz = Path(sys.argv[1])
    print("=" * 70)
    print("  BASE PARA DESIGN — profissões sem arte de telefone ainda")
    print("=" * 70)

    com_psd, sem_nada = [], []

    for nome in PROFISSOES_SEM_ARTE:
        pasta = raiz / nome
        if not pasta.is_dir():
            sem_nada.append((nome, "pasta não encontrada"))
            continue
        psds = _psds_da_pasta(pasta)
        if psds:
            com_psd.append((nome, psds))
        else:
            sem_nada.append((nome, "pasta existe, mas nenhum .psd/.psb dentro"))

    print(f"\n🎨 Têm PSD/logo existente — dá pra partir de um deles para "
          f"adicionar a camada de telefone ({len(com_psd)}):")
    for nome, psds in com_psd:
        print(f"\n  {nome}:")
        for p in psds[:5]:
            tam_mb = p.stat().st_size / 1_048_576
            print(f"     - {p.relative_to(raiz / nome)}  ({tam_mb:.1f} MB)")
        if len(psds) > 5:
            print(f"     ... e mais {len(psds) - 5} arquivo(s)")

    print(f"\n🚫 Sem nenhum PSD na pasta — precisa de arte 100% nova "
          f"({len(sem_nada)}):")
    for nome, motivo in sem_nada:
        print(f"   {nome}: {motivo}")

    print(f"\n{'='*70}")
    print(f"Resumo: {len(com_psd)} com base pra adaptar, {len(sem_nada)} do zero.")
    print("=" * 70)


if __name__ == "__main__":
    main()
