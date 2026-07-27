"""
services/thumbnail_service.py — Miniatura de um modelo (Modelos → lista),
cacheada em disco (PNG pequeno). Renderizar o PSD de verdade é pesado
(psd-tools/numpy sobre canvas grandes) — por isso isso roda 1x, no
cadastro/edição do modelo (`gerar_e_salvar`), e a tela de listagem só
faz `carregar`, que é uma leitura de PNG pequeno (rápida e leve).
"""
from __future__ import annotations
from PIL import Image
from domain.models import Modelo, Pedido
from domain.enums import Prioridade
from core.exceptions import DTFError
from infrastructure.filesystem import thumb_path

DADOS_EXEMPLO = {
    "telefone": "(11) 91234-5678",
    "nome": "SILVA",
    "numero_peito": "10",
    "numero_costas": "10",
}
TAM_MAX = 400   # bom o bastante pra miniatura pequena E o zoom no hover


def gerar_e_salvar(modelo: Modelo, fonte_path: str) -> bool:
    """Renderiza a arte de exemplo e salva um PNG pequeno em disco.
    True se deu certo, False se o modelo não pôde ser renderizado (PSD
    inválido, camada removida etc — nesse caso nada é salvo)."""
    from services.renderer import renderizar_arte

    try:
        campos = {c.campo for c in modelo.camadas}
        dados = {campo: DADOS_EXEMPLO[campo] for campo in campos}
        pedido = Pedido(id=0, modelo_id=modelo.id or 0, profissao=modelo.profissao,
                         dados=dados, prioridade=Prioridade.NORMAL)
        img = renderizar_arte(pedido, modelo, fonte_path)
    except DTFError:
        return False

    escala = min(TAM_MAX / img.width, TAM_MAX / img.height, 1.0)
    miniatura = img.resize(
        (max(1, int(img.width * escala)), max(1, int(img.height * escala))), Image.LANCZOS)
    fundo = Image.new("RGB", miniatura.size, (245, 245, 245))
    fundo.paste(miniatura, (0, 0), miniatura)
    try:
        fundo.save(thumb_path(modelo.id), "PNG")
    except Exception:
        return False
    return True


def carregar(modelo_id: int) -> "Image.Image | None":
    """Leitura rápida do PNG cacheado — nunca toca no PSD nem no numpy."""
    caminho = thumb_path(modelo_id)
    if not caminho.exists():
        return None
    try:
        img = Image.open(caminho)
        img.load()
        return img.convert("RGB")
    except Exception:
        return None


def invalidar(modelo_id: int) -> None:
    caminho = thumb_path(modelo_id)
    if caminho.exists():
        try:
            caminho.unlink()
        except Exception:
            pass
