#!/usr/bin/env python3
"""Varredura de fluxo (smoke) para o Sistema Opera.

Objetivo:
- Validar compilação Python de todas as páginas;
- Validar integridade do route_map (rotas -> arquivos);
- Verificar pré-requisitos do banco (psycopg2 e psql);
- Gerar relatório em Markdown para acompanhamento.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

BASE_DIR = Path(__file__).resolve().parent
ROUTE_MAP = BASE_DIR / "route_map.json"


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str


def check_compile() -> CheckResult:
    cmd = [sys.executable, "-m", "compileall", "-q", str(BASE_DIR)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return CheckResult("Compilação Python", True, "Todos os módulos compilaram sem erro.")
    raw = (proc.stdout or "") + (proc.stderr or "")
    return CheckResult("Compilação Python", False, raw.strip() or "Falha sem saída capturada.")


def check_route_map() -> CheckResult:
    if not ROUTE_MAP.exists():
        return CheckResult("Integridade de rotas", False, f"Arquivo ausente: {ROUTE_MAP}")

    try:
        data = json.loads(ROUTE_MAP.read_text(encoding="utf-8"))
    except Exception as exc:
        return CheckResult("Integridade de rotas", False, f"Falha ao ler JSON: {exc}")

    missing: List[Tuple[str, str]] = []
    malformed: List[str] = []

    for route_name, route_cfg in data.items():
        if not isinstance(route_cfg, dict):
            malformed.append(route_name)
            continue
        file_name = route_cfg.get("file")
        action_name = route_cfg.get("action")

        # Algumas rotas são ações internas (ex.: trocar usuário) e não apontam para arquivo.
        if not file_name and action_name:
            continue

        if not file_name and not action_name:
            malformed.append(route_name)
            continue
        route_file = BASE_DIR / file_name
        if not route_file.exists():
            missing.append((route_name, file_name))

    if malformed or missing:
        parts: List[str] = []
        if malformed:
            parts.append(f"Rotas malformadas/sem arquivo: {', '.join(sorted(malformed))}")
        if missing:
            miss = "; ".join([f"{name} -> {f}" for name, f in missing])
            parts.append(f"Arquivos ausentes: {miss}")
        return CheckResult("Integridade de rotas", False, " | ".join(parts))

    return CheckResult(
        "Integridade de rotas",
        True,
        f"{len(data)} rotas válidas e todos os arquivos referenciados existem.",
    )


def check_psycopg2() -> CheckResult:
    try:
        import psycopg2  # type: ignore

        version = getattr(psycopg2, "__version__", "desconhecida")
        return CheckResult("Driver PostgreSQL (psycopg2)", True, f"Disponível: {version}")
    except Exception as exc:
        return CheckResult("Driver PostgreSQL (psycopg2)", False, f"Indisponível: {exc}")


def check_psql_cli() -> CheckResult:
    try:
        proc = subprocess.run(["psql", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        return CheckResult("Cliente psql", False, "Comando `psql` não encontrado no PATH.")

    if proc.returncode == 0:
        return CheckResult("Cliente psql", True, (proc.stdout or proc.stderr).strip())
    return CheckResult("Cliente psql", False, (proc.stdout or proc.stderr).strip() or "Falha ao executar psql.")


def build_report(results: List[CheckResult]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Relatório automático de varredura de fluxo",
        "",
        f"Gerado em: **{now}**",
        "",
        "## Resultado dos checks",
    ]

    for r in results:
        icon = "✅" if r.ok else "❌"
        lines.append(f"- {icon} **{r.name}**: {r.details}")

    blocked_db = any(r.name in {"Driver PostgreSQL (psycopg2)", "Cliente psql"} and not r.ok for r in results)
    lines += ["", "## Conclusão"]
    if blocked_db:
        lines.append(
            "- O smoke de fluxo foi executado, porém os testes E2E de leitura/gravação em banco ficam bloqueados até regularizar driver/cliente PostgreSQL no ambiente."
        )
    else:
        lines.append("- Ambiente apto para avançar com testes E2E reais de leitura/gravação no PostgreSQL.")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa varredura de fluxo (smoke) e gera relatório.")
    parser.add_argument(
        "--output",
        default=str(BASE_DIR / "TEST_REPORT_AUTO.md"),
        help="Caminho do relatório Markdown de saída.",
    )
    args = parser.parse_args()

    checks = [
        check_compile(),
        check_route_map(),
        check_psycopg2(),
        check_psql_cli(),
    ]

    report = build_report(checks)
    out_path = Path(args.output)
    out_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"Relatório salvo em: {out_path}")

    return 0 if all(c.ok for c in checks[:2]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
