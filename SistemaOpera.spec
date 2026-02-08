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
hiddenimports += collect_submodules("CTkMessagebox")
hiddenimports += collect_submodules("PyMuPDF")
hiddenimports += collect_submodules("fitz")
hiddenimports += collect_submodules("PyQt5")
hiddenimports += collect_submodules("bcrypt")
hiddenimports += collect_submodules("charset_normalizer")
hiddenimports += collect_submodules("contourpy")
hiddenimports += collect_submodules("cycler")
hiddenimports += collect_submodules("darkdetect")
hiddenimports += collect_submodules("defusedxml")
hiddenimports += collect_submodules("fonttools")
hiddenimports += collect_submodules("fpdf")
hiddenimports += collect_submodules("kiwisolver")
hiddenimports += collect_submodules("matplotlib")
hiddenimports += collect_submodules("numpy")
hiddenimports += collect_submodules("packaging")
hiddenimports += collect_submodules("PIL")
hiddenimports += collect_submodules("psycopg2")
hiddenimports += collect_submodules("pyparsing")
hiddenimports += collect_submodules("dateutil")
hiddenimports += collect_submodules("reportlab")
hiddenimports += collect_submodules("six")
hiddenimports += collect_submodules("sqlparse")


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
