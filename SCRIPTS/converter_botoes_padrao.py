#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Converte construtores ctk.CTkButton(...) para BotaoPadronizado.criar_botao(...)
em páginas do sistema (exceto MENU_PRINCIPAL.py e TEMAS.py).
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "PAGINAS_DO_SISTEMA"
REPORT = PAGES_DIR / "RELATORIO_CONVERSAO_BOTOES.md"
IMPORT_LINE = "from PAGINAS_DO_SISTEMA.TEMAS import BotaoPadronizado"


def _insert_import_if_needed(text: str) -> str:
    if IMPORT_LINE in text:
        return text

    lines = text.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            insert_at = i + 1
            continue
        if s == "" and insert_at > 0:
            insert_at = i + 1
            continue
        break

    lines.insert(insert_at, IMPORT_LINE)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def main() -> None:
    files = sorted(PAGES_DIR.glob("*.py"))
    changed: list[tuple[str, int]] = []
    total = 0
    pattern = re.compile(r"\bctk\.CTkButton\s*\(")

    for f in files:
        if f.name in {"MENU_PRINCIPAL.py", "TEMAS.py", "__init__.py"}:
            continue
        original = f.read_text(encoding="utf-8", errors="ignore")
        matches = len(pattern.findall(original))
        if matches == 0:
            continue

        updated = pattern.sub("BotaoPadronizado.criar_botao(", original)
        updated = _insert_import_if_needed(updated)

        if updated != original:
            f.write_text(updated, encoding="utf-8")
            changed.append((f.name, matches))
            total += matches

    lines = [
        "# Relatório de Conversão de Botões",
        "",
        f"- Arquivos alterados: **{len(changed)}**",
        f"- Conversões `ctk.CTkButton(` -> `BotaoPadronizado.criar_botao(`: **{total}**",
        "",
        "| Arquivo | Conversões |",
        "|---|---:|",
    ]
    for name, qtd in changed:
        lines.append(f"| `{name}` | {qtd} |")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Conversão concluída. Relatório: {REPORT}")


if __name__ == "__main__":
    main()

