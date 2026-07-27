"""
ui/icons.py — Ícones vetoriais nítidos via Segoe MDL2 Assets (fonte já
instalada no Windows) — substitui emoji, que renderizam pequenos e
inconsistentes no Tkinter nativo. Codepoints conferidos visualmente
(renderizados offscreen e comparados) antes de usar, não são "chute".
"""
from __future__ import annotations
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

FAMILIA = "Segoe MDL2 Assets"
_FONTE_PATH = r"C:\Windows\Fonts\segmdl2.ttf"

MENU          = chr(0xE700)   # hamburger
BUSCAR        = chr(0xE721)   # lupa
SINO          = chr(0xEA8F)   # notificação
CALENDARIO    = chr(0xE787)
CAIXA         = chr(0xE7B8)   # pacote/lote
CLIPBOARD     = chr(0xF0E3)   # pedidos pendentes
IMPRESSORA    = chr(0xE749)   # produzidos
CAMADAS       = chr(0xE81E)   # modelos (templates empilhados)
BANDEIRA      = chr(0xE7C1)   # meta
GRAFICO_CIMA  = chr(0xE9D2)   # mais produzidos
SETA_BAIXO    = chr(0xE80C)   # menos produzidos
ESTRELA       = chr(0xE735)   # operador do mês (destaque)
ESTRELA_VAZIA = chr(0xE734)
GRADE         = chr(0xF0E2)   # dashboard (nav)
HISTORICO     = chr(0xE81C)   # histórico (nav)
MAIS          = chr(0xE710)   # adicionar
LIXEIRA       = chr(0xE74D)   # remover
LAPIS         = chr(0xE70F)   # editar
OLHO           = chr(0xE890)   # pré-visualizar
ENGRENAGEM    = chr(0xE713)   # configurações
FECHAR        = chr(0xE711)   # x / cancelar
PECA          = chr(0xE71A)   # peça/time (quadrado)
ATUALIZAR     = chr(0xE895)   # recarregar
IMPORTAR      = chr(0xE896)   # seta pra baixo com barra (importar arquivo)
SALVAR        = chr(0xE74E)   # disquete
AVISO         = chr(0xE7BA)   # triângulo de alerta (erros/estoque baixo)
AJUDA         = chr(0xE9CE)   # interrogação em círculo (ajuda/sobre)


def fonte(size: int, bold: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family=FAMILIA, size=size, weight="bold" if bold else "normal")


def rotulo(master, char: str, texto: str, *, tam_icone: int = 13, tam_texto: int = 11,
          cor_icone: str | None = None, cor_texto: str | None = None,
          negrito: bool = False, espaco: int = 6, **kw) -> ctk.CTkFrame:
    """Frame com ícone (MDL2) + texto (Segoe UI) lado a lado — substitui
    o antigo padrão `f"{emoji}  {texto}"` numa única label."""
    frame = ctk.CTkFrame(master, fg_color=kw.pop("fg_color", "transparent"), **kw)
    ctk.CTkLabel(frame, text=char, font=fonte(tam_icone),
                 text_color=cor_icone or cor_texto).pack(side="left", padx=(0, espaco))
    ctk.CTkLabel(frame, text=texto,
                 font=ctk.CTkFont("Segoe UI", tam_texto, "bold" if negrito else "normal"),
                 text_color=cor_texto).pack(side="left")
    return frame


_cache_imagem: dict[tuple, "ctk.CTkImage"] = {}


def imagem(char: str, tam: int = 16, cor: str = "#000000") -> "ctk.CTkImage":
    """
    Renderiza um glifo MDL2 como CTkImage (PNG com transparência) — usado em
    CTkButton(image=...), que não aceita fonte customizada só no `text`.
    Cacheado por (char, tam, cor).
    """
    chave = (char, tam, cor)
    if chave in _cache_imagem:
        return _cache_imagem[chave]
    escala = 4
    tam_render = tam * escala
    img = Image.new("RGBA", (tam_render, tam_render), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fonte_pil = ImageFont.truetype(_FONTE_PATH, int(tam_render * 0.8))
    draw.text((tam_render // 2, tam_render // 2), char, font=fonte_pil, fill=cor, anchor="mm")
    img = img.resize((tam, tam), Image.LANCZOS)
    resultado = ctk.CTkImage(light_image=img, dark_image=img, size=(tam, tam))
    _cache_imagem[chave] = resultado
    return resultado
