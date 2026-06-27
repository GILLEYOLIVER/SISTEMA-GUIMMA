# -*- mode: python ; coding: utf-8 -*-
import sys

datas = [('licenciamento', 'licenciamento'), ('icons', 'icons')]
binaries = []
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'certifi',
    'licenciamento',
    'licenciamento.admin_app',
    'licenciamento.admin_client',
    'licenciamento.client',
    'licenciamento.paths',
]

a = Analysis(
    ['licenciamento/admin_app.py'],
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
        name='SistemaGuimmaLicencasAdmin',
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
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='SistemaGuimmaLicencasAdmin',
    )
    app = BUNDLE(
        coll,
        name='Sistema Guimma Licencas Admin.app',
        icon='icons/ICONE_SISTEMA.icns',
        bundle_identifier='com.sistemaguimma.licencasadmin',
        info_plist={
            'CFBundleDisplayName': 'Sistema Guimma Licencas Admin',
            'CFBundleName': 'Sistema Guimma Licencas Admin',
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
        name='SistemaGuimmaLicencasAdmin',
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
        icon=['icons/ICONE_SISTEMA.ico'],
    )
