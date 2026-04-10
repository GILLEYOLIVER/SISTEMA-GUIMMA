#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera um relatório de rastreio de botões CTkButton no projeto.

Uso:
    python SCRIPTS/auditar_botoes_ctk.py
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "PAGINAS_DO_SISTEMA"
OUT = PAGES_DIR / "RELATORIO_BOTOES_CTK.md"


def main() -> None:
    pattern = re.compile(r"\bCTkButton\s*\(")
    files = sorted(PAGES_DIR.glob("*.py"))

    rows: list[tuple[str, int]] = []
    total = 0

    for f in files:
        if f.name.upper() == "MENU_PRINCIPAL.PY":
            continue
        content = f.read_text(encoding="utf-8", errors="ignore")
        count = len(pattern.findall(content))
        if count > 0:
            rows.append((f.name, count))
            total += count

    lines = [
        "# Relatório de Botões CTkButton",
        "",
        f"- Total de arquivos com CTkButton: **{len(rows)}**",
        f"- Total de ocorrências CTkButton(...): **{total}**",
        "",
        "| Arquivo | Ocorrências |",
        "|---|---:|",
    ]
    for name, count in rows:
        lines.append(f"| `{name}` | {count} |")

    lines.extend(
        [
            "",
            "## Observação",
            "",
            "A padronização visual global está centralizada em `TEMAS.py` e aplicada em runtime pelo `MENU_PRINCIPAL.py`.",
            "Por isso, não é obrigatório alterar manualmente todos os arquivos de página para obter padrão único de botões.",
        ]
    )

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Relatório gerado em: {OUT}")


if __name__ == "__main__":
    main()

