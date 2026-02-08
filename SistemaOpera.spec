# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DATA = ROOT / "data"
PACKAGE_DIR = SRC / "PAGINAS_DO_SISTEMA"

hiddenimports = []
hiddenimports += collect_submodules("PAGINAS_DO_SISTEMA")
hiddenimports += collect_submodules("customtkinter")


a = Analysis(
    [str(PACKAGE_DIR / "MAIN.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        (str(ROOT / "icons"), "icons"),
        (str(DATA / "BANCO_DE_DADOS"), "BANCO_DE_DADOS"),
        (str(PACKAGE_DIR), "PAGINAS_DO_SISTEMA"),
        (str(DATA / "INSTAL_BANCO_APP"), "INSTAL BANCO APP"),
        (str(DATA / "RECIBOS_DE_PAGAMENTOS"), "RECIBOS_DE_PAGAMENTOS"),
    ],
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
    name="SistemaOpera",
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
    icon=[str(PACKAGE_DIR / "ICONE_SISTEMA.icns")],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SistemaOpera",
)
app = BUNDLE(
    coll,
    name="SistemaOpera.app",
    icon=str(PACKAGE_DIR / "ICONE_SISTEMA.icns"),
    bundle_identifier=None,
)
