"""
ui/components/titlebar.py — Cor da barra de título nativa do Windows via DWM.
Sem titlebar customizada — usa a barra nativa do SO com cor aplicada, igual
ao DTF MANAGER original (`DWMWA_CAPTION_COLOR`), pra não destoar da sidebar
preta logo abaixo dela (o padrão do Windows é branco).
"""


def aplicar_cor_barra(hwnd_id: int, cor_hex: str = "#000000"):
    """Aplica `cor_hex` na barra de título nativa da janela `hwnd_id`."""
    try:
        import ctypes
        DWMWA_CAPTION_COLOR = 35
        r = int(cor_hex[1:3], 16)
        g = int(cor_hex[3:5], 16)
        b = int(cor_hex[5:7], 16)
        color_bgr = (b << 16) | (g << 8) | r
        hwnd = ctypes.windll.user32.GetParent(hwnd_id)
        if not hwnd:
            hwnd = hwnd_id
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_CAPTION_COLOR,
            ctypes.byref(ctypes.c_int(color_bgr)),
            ctypes.sizeof(ctypes.c_int)
        )
    except Exception:
        pass
