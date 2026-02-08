#!/usr/bin/env python3
"""Build helper for SISTEMA OPERA installers."""
from __future__ import annotations

import argparse
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "MAIN.py"

ASSET_EXTENSIONS = {".json", ".jpg", ".png", ".icns", ".ttf"}
ASSET_DIRS = ["icons", "BANCO_DE_DADOS", "COMMIT"]


def detect_platform(requested: str | None) -> str:
    if requested:
        return requested
    system = platform.system().lower()
    if system.startswith("win"):
        return "windows"
    if system == "darwin":
        return "macos"
    return "linux"


def build_add_data(platform_name: str) -> list[str]:
    separator = ";" if platform_name == "windows" else ":"
    args: list[str] = []

    for directory in ASSET_DIRS:
        path = ROOT / directory
        if path.exists():
            args.extend(["--add-data", f"{path}{separator}{directory}"])

    for item in ROOT.iterdir():
        if item.is_file() and item.suffix.lower() in ASSET_EXTENSIONS:
            args.extend(["--add-data", f"{item}{separator}."])

    return args


def build_pyinstaller(platform_name: str) -> None:
    icon = None
    if platform_name == "macos":
        icon = ROOT / "ICONE_SISTEMA.icns"
    elif platform_name == "windows":
        ico = ROOT / "ICONE_SISTEMA.ico"
        png = ROOT / "ICONE_SISTEMA.png"
        icon = ico if ico.exists() else png

    command = [
        "python",
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "SistemaOpera",
        "--collect-submodules",
        "PAGINAS_DO_SISTEMA",
        "--collect-submodules",
        "customtkinter",
    ]

    if icon and icon.exists():
        command.extend(["--icon", str(icon)])

    command.extend(build_add_data(platform_name))
    command.append(str(ENTRYPOINT))

    subprocess.run(command, check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SISTEMA OPERA binaries.")
    parser.add_argument(
        "--platform",
        choices=["windows", "macos", "linux"],
        help="Override detected platform.",
    )
    args = parser.parse_args()

    platform_name = detect_platform(args.platform)
    build_pyinstaller(platform_name)


if __name__ == "__main__":
    main()
