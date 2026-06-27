# -*- mode: python ; coding: utf-8 -*-
import sys

datas = [('licenciamento', 'licenciamento'), ('icons', 'icons')]
binaries = []
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'certifi',
    'licenciamento',
    'licenciamento.app',
    'licenciamento.agent',
    'licenciamento.autorun',
    'licenciamento.client',
    'licenciamento.machine',
    'licenciamento.paths',
    'licenciamento.runtime',
    'licenciamento.store',
]

a = Analysis(
    ['licenciamento/app.py'],
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

if sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='SistemaGuimmaLicenca',
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
        icon=['icons/ICONE_LICENCIADOR.icns'],
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='SistemaGuimmaLicenca',
    )
    app = BUNDLE(
        coll,
        name='Sistema Guimma Licenca.app',
        icon='icons/ICONE_LICENCIADOR.icns',
        bundle_identifier='com.sistemaguimma.licenca',
        info_plist={
            'CFBundleDisplayName': 'Sistema Guimma Licenca',
            'CFBundleName': 'Sistema Guimma Licenca',
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='SistemaGuimmaLicenca',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=['icons/ICONE_LICENCIADOR.ico'],
    )
