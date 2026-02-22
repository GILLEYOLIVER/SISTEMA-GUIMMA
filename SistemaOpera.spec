# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('PAGINAS_DO_SISTEMA', 'PAGINAS_DO_SISTEMA'), ('icons', 'icons'), ('data', 'data')]
binaries = []
hiddenimports = ['psycopg2', 'psycopg2.extras', 'PIL', 'PIL._imaging', 'PIL.Image', 'PIL.ImageFile', 'PIL.ImageOps', 'PIL.ImageDraw', 'PIL.ImageFont', 'PIL.ImageTk', 'tkinter', 'tkinter.ttk', 'fpdf', 'fpdf.enums', 'reportlab', 'reportlab.pdfgen', 'reportlab.pdfbase', 'reportlab.lib', 'reportlab.graphics', 'matplotlib', 'matplotlib.pyplot', 'matplotlib.backends.backend_tkagg', 'numpy', 'fitz', 'pymupdf']
tmp_ret = collect_all('fpdf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('reportlab')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('matplotlib')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pymupdf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['PAGINAS_DO_SISTEMA/MAIN.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SistemaOpera',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons/ICONE_SISTEMA.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SistemaOpera',
)
app = BUNDLE(
    coll,
    name='SistemaOpera.app',
    icon='icons/ICONE_SISTEMA.icns',
    bundle_identifier=None,
)
