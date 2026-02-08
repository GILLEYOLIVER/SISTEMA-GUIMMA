#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrai imports ausentes do arquivo warn-*.txt do PyInstaller e
gera sugestões de hidden-import/collect_submodules.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


MISSING_RE = re.compile(r"missing module named ['\"]?([A-Za-z0-9_\.]+)['\"]?")


def _normalize_module(module_name: str) -> str:
    if module_name.startswith("."):
        module_name = module_name.lstrip(".")
    return module_name


def _top_level(module_name: str) -> str:
    return module_name.split(".")[0]


def parse_missing_modules(warn_file: Path) -> list[str]:
    missing = set()
    for line in warn_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = MISSING_RE.search(line)
        if not match:
            continue
        module_name = _normalize_module(match.group(1))
        if module_name:
            missing.add(module_name)
    return sorted(missing)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "warn_file",
        type=Path,
        help="Caminho para o warn-*.txt gerado pelo PyInstaller.",
    )
    args = parser.parse_args()

    missing = parse_missing_modules(args.warn_file)
    if not missing:
        print("Nenhum import ausente encontrado.")
        return

    top_level = sorted({_top_level(name) for name in missing})

    print("# --hidden-import (CLI)")
    for name in missing:
        print(f"--hidden-import={name}")

    print("\n# collect_submodules (SistemaOpera.spec)")
    for name in top_level:
        print(f'hiddenimports += collect_submodules("{name}")')


if __name__ == "__main__":
    main()
