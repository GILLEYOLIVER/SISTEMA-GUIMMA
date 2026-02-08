# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('PAGINAS_DO_SISTEMA')
hiddenimports += collect_submodules('customtkinter')


a = Analysis(
    ['/Users/gilleydeoliveiraguimaraes/PycharmProjects/SISTEMA-GUIMMA/PAGINAS_DO_SISTEMA/MAIN.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/gilleydeoliveiraguimaraes/PycharmProjects/SISTEMA-GUIMMA/icons', 'icons'), ('/Users/gilleydeoliveiraguimaraes/PycharmProjects/SISTEMA-GUIMMA/BANCO_DE_DADOS', 'BANCO_DE_DADOS'), ('/Users/gilleydeoliveiraguimaraes/PycharmProjects/SISTEMA-GUIMMA/COMMIT', 'COMMIT'), ('/Users/gilleydeoliveiraguimaraes/PycharmProjects/SISTEMA-GUIMMA/PAGINAS_DO_SISTEMA', 'PAGINAS_DO_SISTEMA'), ('/Users/gilleydeoliveiraguimaraes/PycharmProjects/SISTEMA-GUIMMA/INSTAL BANCO APP', 'INSTAL BANCO APP'), ('/Users/gilleydeoliveiraguimaraes/PycharmProjects/SISTEMA-GUIMMA/RECIBOS_DE_PAGAMENTOS', 'RECIBOS_DE_PAGAMENTOS')],
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
    icon=['/Users/gilleydeoliveiraguimaraes/PycharmProjects/SISTEMA-GUIMMA/PAGINAS_DO_SISTEMA/ICONE_SISTEMA.icns'],
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
    icon='/Users/gilleydeoliveiraguimaraes/PycharmProjects/SISTEMA-GUIMMA/PAGINAS_DO_SISTEMA/ICONE_SISTEMA.icns',
    bundle_identifier=None,
)
