#!/usr/bin/env python3
"""Create a Windows .ico from the sistema icon if Pillow is available."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ICON_DIR = ROOT / "PAGINAS_DO_SISTEMA"
SOURCE_PNG = ICON_DIR / "ICONE_SISTEMA.png"
TARGET_ICO = ICON_DIR / "ICONE_SISTEMA.ico"


def main() -> None:
    if TARGET_ICO.exists():
        return
    if not SOURCE_PNG.exists():
        return
    try:
        from PIL import Image
    except Exception:
        print("Pillow não encontrado; instale com: pip install pillow")
        return

    image = Image.open(SOURCE_PNG)
    image.save(
        TARGET_ICO,
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"Ícone .ico criado em {TARGET_ICO}")


if __name__ == "__main__":
    main()
