#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera executável do auto_server_setup.py para uso no instalador Windows."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    base_dir = Path(__file__).resolve().parents[2]
    script_path = base_dir / "auto_server_setup.py"
    build_dir = base_dir / "build"
    output_dir = base_dir / "dist" / "SistemaOpera"

    build_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not script_path.exists():
        print(f"Script não encontrado: {script_path}")
        return 1

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--console",
        "--name",
        "AUTO_SERVER_SETUP",
        "--distpath",
        str(output_dir),
        "--workpath",
        str(build_dir / "pyi_server_setup"),
        "--specpath",
        str(build_dir),
        "--hidden-import",
        "psycopg2",
        "--hidden-import",
        "psycopg2.extras",
        "--clean",
        "--noconfirm",
        str(script_path),
    ]

    print("Executando PyInstaller para AUTO_SERVER_SETUP...")
    subprocess.run(cmd, check=True)

    exe_path = output_dir / "AUTO_SERVER_SETUP.exe"
    if not exe_path.exists():
        print("Executável AUTO_SERVER_SETUP.exe não foi gerado.")
        return 1

    print(f"OK: {exe_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
