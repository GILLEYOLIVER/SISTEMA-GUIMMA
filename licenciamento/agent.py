from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from licenciamento.autorun import install_autostart, uninstall_autostart
from licenciamento.client import deactivate_current, load_config, save_config, sync_once
from licenciamento.paths import LOG_FILE, get_writable_path
from licenciamento.store import validate_state

_STOP = False


def _handle_stop(_signum, _frame) -> None:
    global _STOP
    _STOP = True


def _log(message: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S") + " " + message
    print(line)
    try:
        path = get_writable_path(LOG_FILE)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass


def apply_overrides(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    updated = dict(config)
    if args.server_url:
        updated["server_url"] = args.server_url
    if args.customer_email:
        updated["customer_email"] = args.customer_email.strip().lower()
    if args.license_key:
        updated["license_key"] = args.license_key
    if args.enable:
        updated["enabled"] = True
    if args.disable:
        updated["enabled"] = False
    if args.interval_minutes:
        updated["poll_interval_minutes"] = int(args.interval_minutes)
    return updated


def run_sync(config: dict[str, Any], force: bool = False) -> int:
    if not force:
        validation = validate_state()
        if validation.ok:
            validade = ""
            if validation.expires_at:
                validade = validation.expires_at.strftime("%d/%m/%Y %H:%M")
            detalhe = f" ate {validade}" if validade else ""
            _log(f"Licenca local ainda valida{detalhe}. Consulta online adiada.")
            return 0

    try:
        state = sync_once(config)
        _log("Licenca sincronizada com sucesso.")
        print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        _log(f"Falha na sincronizacao: {exc}")
        validation = validate_state()
        if validation.ok:
            _log("Usando licenca local ainda valida.")
            return 0
        return 2


def daemon_loop(config: dict[str, Any]) -> int:
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    interval = max(int(config.get("poll_interval_minutes") or 360), 5) * 60
    _log(f"Agente iniciado. Intervalo: {interval // 60} minutos.")
    while not _STOP:
        run_sync(config, force=True)
        slept = 0
        while slept < interval and not _STOP:
            time.sleep(min(5, interval - slept))
            slept += 5
    _log("Agente finalizado.")
    return 0


def run_deactivate(config: dict[str, Any]) -> int:
    try:
        result = deactivate_current(config)
        _log(result.get("message") or "Licenca desativada neste computador.")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        _log(f"Falha ao desativar licenca: {exc}")
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agente de licenciamento do Sistema Guimma")
    parser.add_argument("--daemon", action="store_true", help="Roda em segundo plano validando periodicamente.")
    parser.add_argument("--sync-once", action="store_true", help="Valida a licenca uma vez e encerra.")
    parser.add_argument("--status", action="store_true", help="Mostra o estado local da licenca.")
    parser.add_argument("--install-autostart", action="store_true", help="Instala inicializacao automatica.")
    parser.add_argument("--uninstall-autostart", action="store_true", help="Remove inicializacao automatica.")
    parser.add_argument("--deactivate", action="store_true", help="Desativa a licenca deste computador.")
    parser.add_argument("--server-url", default="", help="URL base do servidor de licencas.")
    parser.add_argument("--customer-email", "--email", default="", help="Email do cliente usado como identificador.")
    parser.add_argument("--license-key", default="", help="Campo legado/opcional de chave de licenca.")
    parser.add_argument("--interval-minutes", type=int, default=0, help="Intervalo de sincronizacao.")
    parser.add_argument("--enable", action="store_true", help="Ativa exigencia de licenca no computador.")
    parser.add_argument("--disable", action="store_true", help="Desativa exigencia de licenca no computador.")
    args = parser.parse_args(argv)

    config = apply_overrides(load_config(), args)
    if args.server_url or args.customer_email or args.license_key or args.enable or args.disable or args.interval_minutes:
        save_config(config)

    if args.install_autostart:
        print(install_autostart())
        return 0
    if args.uninstall_autostart:
        print(uninstall_autostart())
        return 0
    if args.status:
        validation = validate_state()
        print(validation.message)
        if validation.state:
            print(json.dumps(validation.state, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if validation.ok else 1
    if args.deactivate:
        return run_deactivate(config)
    if args.daemon:
        return daemon_loop(config)
    if args.sync_once:
        return run_sync(config, force=True)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
