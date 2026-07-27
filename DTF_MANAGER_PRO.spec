# -*- mode: python ; coding: utf-8 -*-
# DTF_MANAGER_PRO.spec — build do DTF MANAGER PRO.
#
# Diferente do DTF MANAGER original: SEM gspread/google-auth/cryptography
# (não há mais Google Sheets), COM psd-tools/numpy (leitura de PSD) e
# openpyxl (importação de planilhas .xlsx).
#
# templates/PSDs NÃO são empacotados aqui — cada modelo é cadastrado pelo
# usuário em tempo de execução (tela Gerenciar Modelos) e copiado para
# assets/psds/ na pasta de instalação, não faz parte do build.

from PyInstaller.utils.hooks import collect_all

datas_ctk,   binaries_ctk,   hi_ctk   = collect_all('customtkinter')
datas_pil,   binaries_pil,   hi_pil   = collect_all('PIL')
datas_psd,   binaries_psd,   hi_psd   = collect_all('psd_tools')
datas_numpy, binaries_numpy, hi_numpy = collect_all('numpy')
datas_fpdf,  binaries_fpdf,  hi_fpdf  = collect_all('fpdf')
datas_oxl,   binaries_oxl,   hi_oxl   = collect_all('openpyxl')

PACOTES_PROPRIOS = [
    ('domain',         'domain'),
    ('core',           'core'),
    ('infrastructure', 'infrastructure'),
    ('services',       'services'),
    ('ui',             'ui'),
]

all_datas = (
    datas_ctk + datas_pil + datas_psd + datas_numpy + datas_fpdf + datas_oxl +
    PACOTES_PROPRIOS +
    [
        ('config_app.json', '.'),
        ('version.json',    '.'),
        ('dtf_manager.ico', '.'),
        ('updater.py',      '.'),
        ('infrastructure/fonts/fonte.otf', '.'),
        ('assets/icon.png', 'assets'),
        ('assets/fonts/Roboto-Regular.ttf', 'assets/fonts'),
    ]
)

all_binaries = binaries_ctk + binaries_pil + binaries_psd + binaries_numpy + binaries_fpdf + binaries_oxl

all_hiddenimports = (
    hi_ctk + hi_pil + hi_psd + hi_numpy + hi_fpdf + hi_oxl +
    [
        'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont',
        'psd_tools', 'numpy', 'customtkinter', 'darkdetect', 'fpdf', 'openpyxl',
        'domain', 'core', 'infrastructure', 'services', 'ui', 'updater',
        'sqlite3',
    ]
)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DTF MANAGER PRO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='dtf_manager.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DTF MANAGER PRO',
)
