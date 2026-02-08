#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
packaging/build.py — Build oficial do SISTEMA OPERA (macOS/Windows)

✅ Build "blindado": inclui tudo do requirements.txt (via --collect-all)
✅ NÃO usa .spec automaticamente (só se você passar --spec)
✅ Detecta layout com/sem pasta src
✅ Inclui assets (PAGINAS_DO_SISTEMA + icons + data/*)
✅ Evita sobrescrever SistemaOpera.spec gerado automaticamente (usa --specpath build/specs)
✅ Usa o Python do venv atual (sys.executable)
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "SistemaOpera"

# Alguns pacotes do requirements têm nome diferente do módulo de import.
REQ_TO_IMPORT: dict[str, str | None] = {
    "charset-normalizer": "charset_normalizer",
    "fpdf2": "fpdf",
    "pillow": "PIL",
    "python-dateutil": "dateutil",
    "pymupdf": "fitz",
    "fonttools": "fontTools",
    "pyqt5-qt5": None,  # distribuição binária (não é importável)
    "pyinstaller-hooks-contrib": None,  # ferramenta/hook (não precisa coletar no app)
    "pyinstaller": None,  # ferramenta de build (não precisa coletar no app)
    "dmgbuild": None,  # ferramenta de build (não precisa coletar no app)
    "setuptools": None,  # ferramenta de build
    "wheel": None,  # ferramenta de build
}

_OP_RE = re.compile(r"(?P<name>[A-Za-z0-9_.\-]+)(?:\[.*\])?\s*(?:==|>=|<=|~=|!=|>|<).*")


def _detect_layout(root: Path) -> tuple[Path, Path]:
    """
    Retorna (SRC_BASE, PACKAGE_DIR).
    SRC_BASE vai em --paths.
    PACKAGE_DIR é onde fica PAGINAS_DO_SISTEMA.
    """
    a = root / "PAGINAS_DO_SISTEMA" / "MAIN.py"
    if a.exists():
        return root, root / "PAGINAS_DO_SISTEMA"

    b = root / "src" / "PAGINAS_DO_SISTEMA" / "MAIN.py"
    if b.exists():
        return root / "src", root / "src" / "PAGINAS_DO_SISTEMA"

    raise FileNotFoundError(
        "Não encontrei MAIN.py em:\n"
        f"- {a}\n"
        f"- {b}\n"
        "Ajuste a estrutura ou atualize o build."
    )


def _run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("\n>>>", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True, cwd=str(cwd) if cwd else None, env=env)


def _parse_requirements(req_path: Path) -> list[str]:
    """Extrai nomes de pacotes do requirements.txt (sem versões)."""
    if not req_path.exists():
        return []
    names: list[str] = []
    for raw in req_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _OP_RE.match(line)
        if m:
            names.append(m.group("name"))
        else:
            # linha sem operador (ex: "customtkinter")
            names.append(line)
    return names


def _req_to_import_name(req_name: str) -> str | None:
    key = req_name.strip()
    low = key.lower()
    if low in REQ_TO_IMPORT:
        return REQ_TO_IMPORT[low]
    # nomes com hífen geralmente viram underscore no import
    return key.replace("-", "_")


def _collect_all_args_from_requirements(req_path: Path) -> tuple[list[str], list[str]]:
    """
    Retorna:
      - args: lista de args '--collect-all' já prontos
      - skipped: lista de pacotes ignorados por não serem importáveis/serem ferramenta
    """
    reqs = _parse_requirements(req_path)
    args: list[str] = []
    skipped: list[str] = []
    seen: set[str] = set()

    for pkg in reqs:
        mod = _req_to_import_name(pkg)
        if not mod:
            skipped.append(pkg)
            continue
        if mod in seen:
            continue
        seen.add(mod)
        args += ["--collect-all", mod]
    return args, skipped


def build_pyinstaller(platform_name: str, spec_file: Path | None, extra_pyinstaller_args: list[str]) -> None:
    src_base, package_dir = _detect_layout(ROOT)
    entrypoint = package_dir / "MAIN.py"

    # Ícone do macOS
    icon_path = package_dir / "ICONE_SISTEMA.icns"

    data_dir = ROOT / "data"
    asset_dirs = [
        (ROOT / "icons", "icons"),
        (data_dir / "BANCO_DE_DADOS", "BANCO_DE_DADOS"),
        (package_dir, "PAGINAS_DO_SISTEMA"),
        (data_dir / "INSTAL_BANCO_APP", "INSTAL BANCO APP"),
        (data_dir / "RECIBOS_DE_PAGAMENTOS", "RECIBOS_DE_PAGAMENTOS"),
    ]

    dist = ROOT / "dist"
    build = ROOT / "build"
    specs_dir = build / "specs"  # ✅ evita sobrescrever o SistemaOpera.spec na raiz

    if dist.exists():
        shutil.rmtree(dist, ignore_errors=True)
    if build.exists():
        shutil.rmtree(build, ignore_errors=True)

    specs_dir.mkdir(parents=True, exist_ok=True)

    sep = ";" if platform_name == "windows" else ":"

    # ✅ Só usa spec se você passar --spec (não usa automaticamente)
    if spec_file:
        cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean"]
        cmd += extra_pyinstaller_args
        cmd.append(str(spec_file))
        env = os.environ.copy()
        env["OPERA_SPEC_ROOT"] = str(ROOT)
        _run(cmd, cwd=ROOT, env=env)
        return

    # ✅ "Compilar tudo" do requirements.txt
    req_path = ROOT / "requirements.txt"
    collect_all_args, skipped = _collect_all_args_from_requirements(req_path)
    if skipped:
        print("⚠️ Pacotes ignorados (não importáveis / ferramentas de build):", ", ".join(skipped))

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(dist),
        "--workpath",
        str(build),
        "--specpath",
        str(specs_dir),  # ✅ aqui evita sobrescrever o spec na raiz
        "--paths",
        str(src_base),

        # ✅ páginas/imports dinâmicos
        "--collect-submodules",
        "PAGINAS_DO_SISTEMA",
    ]

    # ✅ inclui tudo do requirements via collect-all
    cmd += collect_all_args

    if platform_name == "macos" and icon_path.exists():
        cmd += ["--icon", str(icon_path)]

    for src, dest in asset_dirs:
        if src.exists():
            cmd += ["--add-data", f"{src}{sep}{dest}"]

    cmd += extra_pyinstaller_args
    cmd.append(str(entrypoint))

    env = os.environ.copy()
    env["OPERA_SPEC_ROOT"] = str(ROOT)
    _run(cmd, cwd=ROOT, env=env)

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
    parser.add_argument("--platform", choices=["macos", "windows"], default="macos")
    parser.add_argument("--spec", type=Path, default=None, help="Usa um arquivo .spec (opcional).")
    parser.add_argument("--pyinstaller-args", nargs=argparse.REMAINDER, default=[], help="Args extras pro PyInstaller.")
    args = parser.parse_args()
    build_pyinstaller(args.platform, args.spec, args.pyinstaller_args)


if __name__ == "__main__":
    main()
