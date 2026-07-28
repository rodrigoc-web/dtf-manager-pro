"""
scripts/gerar_login_bg.py — Gera assets/login_bg.png: o FUNDO (só o fundo)
da tela de login/splash. Canvas de referência 1200x800 (mesmo teto de
tamanho da janela principal, ver ui/app.py — a janela de login usa
exatamente a mesma conta, pra abrir do mesmo tamanho que o app real, sem
salto visual na transição). Todo o resto (logo, textos, campo, botão,
rodapé) é desenhado pelo CustomTkinter em cima — só o fundo é arte
estática, pro texto continuar nítido em qualquer resolução.

Conteúdo do fundo:
  - gradiente quase-preto (#080808 no topo -> #121212 no centro -> #080808
    embaixo), bem discreto
  - impressora como "elemento de iluminação": grande (ocupa quase toda a
    direita), bem desfocada e a ~8% de opacidade — mais textura/luz de
    fundo do que um ícone reconhecível de cara
"""
from PIL import Image, ImageFilter
import numpy as np

LOGO_ORIGEM = r"C:\DTF MANAGER PRO\logo.png"
SAIDA = r"C:\DTF MANAGER PRO\dev\assets\login_bg.png"

W, H = 1200, 800
TOPO_PCT, RODAPE_PCT = 0.0, 0.0   # marca d'água pode ocupar a altura toda agora


def _extrair_impressora(alpha_max: int) -> Image.Image:
    im = Image.open(LOGO_ORIGEM).convert("RGB")
    x0, y0, x1, y1 = 493, 213, 1051, 589
    pad_lr, pad_top, pad_bottom = 60, 60, 20
    x0, y0 = max(0, x0 - pad_lr), max(0, y0 - pad_top)
    x1, y1 = min(im.width, x1 + pad_lr), min(im.height, y1 + pad_bottom)
    corte = im.crop((x0, y0, x1, y1))

    arr = np.array(corte.convert("RGBA")).astype(float)
    soma = arr[:, :, 0] + arr[:, :, 1] + arr[:, :, 2]
    preto = soma < 18
    arr[:, :, 3] = alpha_max
    arr[preto, 3] = 0
    return Image.fromarray(arr.astype("uint8"), "RGBA")


def gerar():
    # 1) gradiente #080808 -> #121212 -> #080808 (vertical, bem sutil)
    topo = np.array([0x08, 0x08, 0x08], dtype=float)
    centro = np.array([0x12, 0x12, 0x12], dtype=float)
    fundo = np.zeros((H, W, 3), dtype=float)
    for y in range(H):
        t = y / (H - 1)
        mistura = 1 - abs(t - 0.5) * 2   # 0 nas bordas, 1 no centro
        fundo[y, :, :] = topo + (centro - topo) * mistura
    ruido = (np.random.default_rng(7).random((H, W, 1)) - 0.5) * 1.2
    fundo = np.clip(fundo + ruido, 0, 255)
    base_img = Image.fromarray(fundo.astype("uint8"), "RGB").convert("RGBA")

    # 2) impressora como "luz de fundo" — grande, bem desfocada, ~8% opacidade,
    # ocupando quase toda a metade direita, cortada pela borda.
    alpha_alvo = int(255 * 0.08)
    impressora = _extrair_impressora(alpha_alvo)
    alvo_w = int(W * 0.62)
    alvo_h = int(H * 0.92)
    escala = min(alvo_w / impressora.width, alvo_h / impressora.height)
    novo_tam = (int(impressora.width * escala), int(impressora.height * escala))
    impressora = impressora.resize(novo_tam, Image.LANCZOS)
    impressora = impressora.filter(ImageFilter.GaussianBlur(3.5))

    corte_borda = int(novo_tam[0] * 0.16)
    pos_x = W - novo_tam[0] + corte_borda
    pos_y = (H - novo_tam[1]) // 2

    base_img.alpha_composite(impressora, (pos_x, pos_y))

    base_img.convert("RGB").save(SAIDA, optimize=True)
    print(f"salvo: {SAIDA} ({W}x{H})")


if __name__ == "__main__":
    gerar()
