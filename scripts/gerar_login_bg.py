"""
scripts/gerar_login_bg.py — Gera assets/login_bg.png: o FUNDO (só o fundo)
da tela de login, em 16:9 (1600x900). Todo o resto (logo, textos, campo,
botão, rodapé) é desenhado pelo próprio CustomTkinter em cima — só a
imagem de fundo é arte estática, pro texto continuar nítido em qualquer
resolução (mesma abordagem de softwares desktop profissionais).

Conteúdo do fundo:
  - gradiente escuro suave (quase preto, com leve variação)
  - brilho verde bem sutil atrás de onde a impressora fica
  - marca d'água da impressora (extraída do logo novo): 57% da largura
    do canvas, 70% da altura útil, opacidade ~10%, alinhada à direita e
    parcialmente cortada pela borda (efeito mais moderno)

Rodar de novo sempre que o logo.png mudar: python scripts/gerar_login_bg.py
"""
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

LOGO_ORIGEM = r"C:\DTF MANAGER PRO\logo.png"
SAIDA = r"C:\DTF MANAGER PRO\dev\assets\login_bg.png"

W, H = 1600, 900
TOPO_PCT, RODAPE_PCT = 0.06, 0.10   # faixas reservadas (fora da "altura útil")


def _extrair_impressora(alpha_max: int) -> Image.Image:
    """Mesmo recorte usado no ícone/ilustração do popup antigo, mas aqui
    com o alpha já limitado ao teto pedido (opacidade final da marca d'água)."""
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
    # 1) gradiente de base — quase preto, variação bem leve (evita "banding"
    # perceptível numa área tão escura: gera em float e faz dither leve)
    fundo = np.zeros((H, W, 3), dtype=float)
    for y in range(H):
        t = y / (H - 1)
        # centro um pouco mais claro que as bordas (vinheta suave)
        base = 4 + 3 * (1 - abs(t - 0.5) * 2)
        fundo[y, :, 0] = base * 0.9
        fundo[y, :, 1] = base
        fundo[y, :, 2] = base * 0.85
    ruido = (np.random.default_rng(7).random((H, W, 1)) - 0.5) * 1.5
    fundo = np.clip(fundo + ruido, 0, 255)

    # 2) brilho verde sutil atrás da impressora (lado direito, altura útil)
    cx, cy = int(W * 0.78), int(H * (TOPO_PCT + (1 - TOPO_PCT - RODAPE_PCT) / 2))
    yy, xx = np.mgrid[0:H, 0:W]
    raio = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 1.4) ** 2)
    raio_max = W * 0.42
    intensidade = np.clip(1 - raio / raio_max, 0, 1) ** 2
    fundo[:, :, 0] += intensidade * 4
    fundo[:, :, 1] += intensidade * 14
    fundo[:, :, 2] += intensidade * 2
    fundo = np.clip(fundo, 0, 255)

    base_img = Image.fromarray(fundo.astype("uint8"), "RGB").convert("RGBA")

    # 3) marca d'água da impressora — 57% da largura do canvas, 70% da
    # altura útil, opacidade ~10% (alpha 255*0.10 ≈ 26), alinhada à
    # direita e parcialmente cortada pela borda direita.
    alpha_alvo = int(255 * 0.10)
    impressora = _extrair_impressora(alpha_alvo)
    alt_util = int(H * (1 - TOPO_PCT - RODAPE_PCT))
    alvo_w = int(W * 0.57)
    alvo_h = int(alt_util * 0.70)
    escala = min(alvo_w / impressora.width, alvo_h / impressora.height)
    novo_tam = (int(impressora.width * escala), int(impressora.height * escala))
    impressora = impressora.resize(novo_tam, Image.LANCZOS)

    # leve desfoque só na marca d'água (reforça a sensação de "atrás de vidro")
    impressora = impressora.filter(ImageFilter.GaussianBlur(0.6))

    corte_borda = int(novo_tam[0] * 0.12)   # ~12% cortado pela borda direita
    pos_x = W - novo_tam[0] + corte_borda
    pos_y = int(TOPO_PCT * H + (alt_util - novo_tam[1]) / 2)

    base_img.alpha_composite(impressora, (pos_x, pos_y))

    base_img.convert("RGB").save(SAIDA, optimize=True)
    print(f"salvo: {SAIDA} ({W}x{H})")


if __name__ == "__main__":
    gerar()
