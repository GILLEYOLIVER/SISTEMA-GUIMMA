from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from licenciamento.client import load_config, sync_once
from licenciamento.store import validate_state


@dataclass(frozen=True)
class LicenseDecision:
    allowed: bool
    title: str
    message: str
    state: dict[str, Any] | None = None


def _env_enforces_license() -> bool:
    value = os.environ.get("SISTEMA_GUIMMA_LICENSE_ENFORCE", "")
    return value.strip().lower() in {"1", "true", "yes", "sim", "on"}


def check_application_access(try_online: bool = True) -> LicenseDecision:
    config = load_config()
    enabled = bool(config.get("enabled")) or _env_enforces_license()
    if not enabled:
        return LicenseDecision(True, "Licenciamento", "Licenciamento ainda nao obrigatorio neste ambiente.")

    validation = validate_state()
    if validation.ok:
        return LicenseDecision(True, "Licenca valida", validation.message, validation.state)

    if try_online and config.get("server_url") and config.get("license_key"):
        try:
            sync_once(config)
            validation = validate_state()
            if validation.ok:
                return LicenseDecision(True, "Licenca valida", validation.message, validation.state)
        except Exception as exc:
            return LicenseDecision(
                False,
                "Licenca nao validada",
                f"{validation.message}\n\nFalha ao consultar o servidor de licencas:\n{exc}",
                validation.state,
            )

    return LicenseDecision(
        False,
        "Licenca bloqueada",
        validation.message
        + "\n\nAbra o aplicativo Sistema Guimma Licenca para ativar ou renovar a assinatura.",
        validation.state,
    )


def open_license_app() -> bool:
    candidates: list[list[str]] = []
    exe_path = Path(sys.executable).resolve()
    system = sys.platform

    if system == "darwin":
        app_candidates = [
            Path("/Applications/Sistema Guimma Licenca.app"),
            exe_path.parent / "Sistema Guimma Licenca.app",
            exe_path.parent.parent / "Sistema Guimma Licenca.app",
            exe_path.parent.parent.parent / "Sistema Guimma Licenca.app",
        ]
        for app_path in app_candidates:
            if app_path.exists():
                candidates.append(["open", str(app_path)])
    elif os.name == "nt":
        exe_candidates = [
            exe_path.parent / "SistemaGuimmaLicenca.exe",
            exe_path.parent / "LicenciamentoGuimma.exe",
        ]
        for item in exe_candidates:
            if item.exists():
                candidates.append([str(item)])

    project_app = Path(__file__).resolve().parent / "app.py"
    if project_app.is_file():
        candidates.append([sys.executable, str(project_app)])

    for command in candidates:
        try:
            subprocess.Popen(command)
            return True
        except Exception:
            continue
    return False
