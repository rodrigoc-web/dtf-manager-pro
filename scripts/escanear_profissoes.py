"""
scripts/escanear_profissoes.py — Varre o acervo de profissões e cadastra
o máximo possível automaticamente, copiando o PSD para dentro do projeto.

Quando há mais de um arquivo candidato (padrão comum: design original +
uma redesign numerada "002"/"02"), escolhe o modificado mais recentemente
— sinal objetivo de "versão atual" — e marca claramente no relatório como
RESOLVIDO POR DATA, para revisão rápida depois via Gerenciar Modelos →
Editar → Pré-visualizar. Só fica de fora quando não há NENHUM arquivo
com 'fone'/'telefone' no nome, ou quando o único candidato não tem
nenhuma camada reconhecível como telefone — nesses casos não há nada
para escolher, então não adivinhamos.

Uso:
    python scripts/escanear_profissoes.py "\\\\SERVIDOR\\Pasta\\PROFISSOES"
"""
from __future__ import annotations
import sys
import re
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PROFUNDIDADE_MAXIMA = 4          # niveis de subpasta pesquisados dentro de cada profissao
PALAVRAS_ARQUIVO_FONE = ["fone", "telefone"]
EXTENSOES_PSD = {".psd", ".psb"}


def _normalizar(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode()
    return txt.lower()


def _candidatos_psd(pasta_profissao: Path) -> list[Path]:
    """Lista .psd/.psb cujo NOME contenha 'fone'/'telefone', até PROFUNDIDADE_MAXIMA."""
    candidatos = []
    base_partes = len(pasta_profissao.parts)
    for arq in pasta_profissao.rglob("*"):
        if arq.suffix.lower() not in EXTENSOES_PSD:
            continue
        if len(arq.parts) - base_partes > PROFUNDIDADE_MAXIMA:
            continue
        if any(p in _normalizar(arq.stem) for p in PALAVRAS_ARQUIVO_FONE):
            candidatos.append(arq)
    return candidatos


def escanear(pasta_raiz: str, db_path: str) -> dict:
    from infrastructure.psd.reader import listar_camadas, construir_modelo
    from infrastructure.filesystem import copiar_psd_local
    from infrastructure.db import modelos_repo
    from core.exceptions import DTFError

    raiz = Path(pasta_raiz)
    ja_cadastradas = {m.profissao for m in modelos_repo.listar_modelos(db_path, apenas_ativos=False)}

    resultado = {"registradas": [], "resolvidas_por_data": [], "ja_existiam": [],
                 "revisar": [], "erros": []}

    pastas_profissao = sorted(
        p for p in raiz.iterdir()
        if p.is_dir() and not p.name.lower().startswith("thumbs"))

    for pasta in pastas_profissao:
        nome_profissao = pasta.name.strip()

        if nome_profissao in ja_cadastradas:
            resultado["ja_existiam"].append(nome_profissao)
            continue

        candidatos = _candidatos_psd(pasta)

        if len(candidatos) == 0:
            resultado["revisar"].append(
                (nome_profissao, "Nenhum arquivo com 'fone'/'telefone' no nome encontrado — "
                                  "essa profissão ainda não tem uma arte de telefone."))
            continue

        ambiguo = len(candidatos) > 1
        # Tenta os candidatos do mais recente ao mais antigo — o mais recente
        # modificado é o sinal objetivo de "versão atual" quando há mais de um.
        candidatos_ordenados = sorted(candidatos, key=lambda p: p.stat().st_mtime, reverse=True)

        psd_path = None
        nomes_telefone: list[str] = []
        erro_abertura = None
        for candidato in candidatos_ordenados:
            try:
                camadas = listar_camadas(str(candidato))
            except DTFError as e:
                erro_abertura = str(e)
                continue
            nomes = [c["nome"] for c in camadas if c["candidata_telefone"]]
            if nomes:
                psd_path, nomes_telefone = candidato, nomes
                break

        if psd_path is None:
            motivo = (erro_abertura or
                      f"nenhum dos {len(candidatos)} candidato(s) tem camada "
                      f"reconhecível como telefone")
            resultado["revisar"].append((nome_profissao, f"{motivo} — confirme manualmente."))
            continue

        try:
            psd_local = copiar_psd_local(str(psd_path), nome_profissao)
            modelo = construir_modelo(nome_profissao, psd_local, nomes_telefone)
            modelos_repo.inserir_modelo(db_path, modelo)
            entrada = (nome_profissao, psd_path.name, len(nomes_telefone))
            if ambiguo:
                alternativas = "; ".join(
                    str(c.relative_to(pasta)) for c in candidatos_ordenados if c != psd_path)
                resultado["resolvidas_por_data"].append((*entrada, alternativas))
            else:
                resultado["registradas"].append(entrada)
        except DTFError as e:
            resultado["erros"].append((nome_profissao, str(e)))

    return resultado


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/escanear_profissoes.py <pasta_raiz_das_profissoes>")
        sys.exit(1)

    from infrastructure.db.database import inicializar_banco
    from infrastructure.filesystem import db_path as db_path_fn

    db = str(db_path_fn())
    inicializar_banco(db)

    r = escanear(sys.argv[1], db)

    print("=" * 70)
    print("  RESULTADO DO ESCANEAMENTO")
    print("=" * 70)
    print(f"\n✅ Cadastradas automaticamente — arquivo único ({len(r['registradas'])}):")
    for nome, arq, n_camadas in r["registradas"]:
        print(f"   {nome}  ←  {arq}  ({n_camadas} camada(s) de telefone)")

    print(f"\n🕘 Cadastradas escolhendo o arquivo mais recente — REVISAR "
          f"({len(r['resolvidas_por_data'])}):")
    for nome, arq, n_camadas, alternativas in r["resolvidas_por_data"]:
        print(f"   {nome}  ←  {arq}  ({n_camadas} camada(s))  "
              f"[não usado: {alternativas}]")

    print(f"\n↷  Já estavam cadastradas ({len(r['ja_existiam'])}):")
    for nome in r["ja_existiam"]:
        print(f"   {nome}")

    print(f"\n⚠️  Precisam de cadastro manual em Gerenciar Modelos ({len(r['revisar'])}):")
    for nome, motivo in r["revisar"]:
        print(f"   {nome}: {motivo}")

    if r["erros"]:
        print(f"\n❌ Erros ({len(r['erros'])}):")
        for nome, motivo in r["erros"]:
            print(f"   {nome}: {motivo}")

    total = (len(r["registradas"]) + len(r["resolvidas_por_data"]) +
              len(r["ja_existiam"]) + len(r["revisar"]) + len(r["erros"]))
    print(f"\n{'='*70}\nTotal de pastas de profissão analisadas: {total}\n{'='*70}")


if __name__ == "__main__":
    main()
