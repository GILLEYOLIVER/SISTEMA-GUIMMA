#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
packaging/build.py — Build oficial do SISTEMA OPERA (macOS/Windows)

✅ Agora dá pra apertar PLAY (sem argumentos): padrão = macos
✅ EntryPoint: src/PAGINAS_DO_SISTEMA/MAIN.py
✅ Inclui assets (inclui PAGINAS_DO_SISTEMA com imagens/fonts)
✅ Usa o Python do venv atual (sys.executable)
✅ Gera dist/SistemaOpera.app (macOS) ou dist/SistemaOpera/SistemaOpera.exe (Windows)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PACKAGE_DIR = SRC / "PAGINAS_DO_SISTEMA"
DATA_DIR = ROOT / "data"

# ✅ EntryPoint real
ENTRYPOINT = PACKAGE_DIR / "MAIN.py"

APP_NAME = "SistemaOpera"

# ✅ Ícone do macOS
ICON_PATH = PACKAGE_DIR / "ICONE_SISTEMA.icns"

# ✅ Pastas que devem ir junto (inclui imagens/fundos/fontes dentro de PAGINAS_DO_SISTEMA)
ASSET_DIRS = [
    (ROOT / "icons", "icons"),
    (DATA_DIR / "BANCO_DE_DADOS", "BANCO_DE_DADOS"),
    (PACKAGE_DIR, "PAGINAS_DO_SISTEMA"),
    (DATA_DIR / "INSTAL_BANCO_APP", "INSTAL BANCO APP"),
    (DATA_DIR / "RECIBOS_DE_PAGAMENTOS", "RECIBOS_DE_PAGAMENTOS"),
]


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    print("\n>>>", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True, cwd=str(cwd) if cwd else None)


def build_pyinstaller(
    platform_name: str,
    spec_file: Path | None,
    extra_pyinstaller_args: list[str],
) -> None:
    if not ENTRYPOINT.exists():
        raise FileNotFoundError(f"ENTRYPOINT não encontrado: {ENTRYPOINT}")

    dist = ROOT / "dist"
    build = ROOT / "build"

    # Build limpo (evita lixo antigo)
    if dist.exists():
        shutil.rmtree(dist, ignore_errors=True)
    if build.exists():
        shutil.rmtree(build, ignore_errors=True)

    # Windows usa ; / macOS usa :
    sep = ";" if platform_name == "windows" else ":"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",  # ✅ sempre o python do venv atual
        "--noconfirm",
        "--clean",
    ]

    default_spec = ROOT / "SistemaOpera.spec"
    resolved_spec = spec_file or (default_spec if default_spec.exists() else None)
    if resolved_spec:
        cmd += extra_pyinstaller_args
        cmd.append(str(resolved_spec))
        _run(cmd, cwd=ROOT)
        return

    cmd += [
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist),
        "--workpath",
        str(build),
        "--paths",
        str(SRC),

        # imports comuns em apps CTk
        "--collect-submodules",
        "PAGINAS_DO_SISTEMA",
        "--collect-submodules",
        "customtkinter",
        "--collect-submodules",
        "fpdf",
    ]

    # Ícone só no macOS
    if platform_name == "macos" and ICON_PATH.exists():
        cmd += ["--icon", str(ICON_PATH)]

    # Assets/pastas
    for src, dest in ASSET_DIRS:
        if src.exists():
            cmd += ["--add-data", f"{src}{sep}{dest}"]

    cmd += extra_pyinstaller_args

    # EntryPoint por último
    cmd.append(str(ENTRYPOINT))

    _run(cmd, cwd=ROOT)

    # Checagem final
    if platform_name == "macos":
        app_path = dist / f"{APP_NAME}.app"
        if not app_path.exists():
            raise RuntimeError(f"Build falhou: não gerou {app_path}")
        print(f"\n✅ App gerada: {app_path}")
    else:
        exe_path = dist / APP_NAME / f"{APP_NAME}.exe"
        print(f"\n✅ Build concluído. Verifique: {exe_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    # ✅ agora não é mais obrigatório passar argumento -> Play funciona
    parser.add_argument("--platform", choices=["macos", "windows"], default="macos")
    parser.add_argument(
        "--spec",
        type=Path,
        default=None,
        help="Usa um arquivo .spec (ex: SistemaOpera.spec) no lugar dos args padrão.",
    )
    parser.add_argument(
        "--pyinstaller-args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Args adicionais passadas para o PyInstaller (ex: --debug=imports).",
    )
    args = parser.parse_args()

    build_pyinstaller(args.platform, args.spec, args.pyinstaller_args)


if __name__ == "__main__":
    main()
