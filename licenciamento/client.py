from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from datetime import timedelta
from typing import Any

from licenciamento import APP_NAME
from licenciamento.machine import machine_summary
from licenciamento.paths import CONFIG_FILE, candidate_config_paths, get_writable_path, read_json, write_json_atomic
from licenciamento.store import clear_license_state, iso_utc, save_license_state, utcnow, validate_state

DEFAULT_SERVER_URL = "https://sistema-guimma-licencas.sistemaguimma.workers.dev"

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "server_url": DEFAULT_SERVER_URL,
    "customer_email": "",
    "license_key": "",
    "poll_interval_minutes": 1440,
    "request_timeout_seconds": 10,
    "grace_days_when_paid": 3,
    "open_license_app_when_invalid": True,
}


def normalize_config(data: dict[str, Any] | None) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if data:
        if isinstance(data.get("license"), dict):
            config.update(data["license"])
        else:
            config.update(data)
    config["enabled"] = bool(config.get("enabled"))
    config["server_url"] = str(config.get("server_url") or DEFAULT_SERVER_URL).strip().rstrip("/")
    config["customer_email"] = str(
        config.get("customer_email")
        or config.get("email_cliente")
        or config.get("cliente_email")
        or config.get("email")
        or ""
    ).strip().lower()
    config["license_key"] = str(config.get("license_key") or "").strip()
    return config


def load_config() -> dict[str, Any]:
    for path in candidate_config_paths():
        try:
            if path.is_file():
                return normalize_config(read_json(path))
        except Exception:
            continue
    return normalize_config(None)


def save_config(config: dict[str, Any]) -> None:
    write_json_atomic(get_writable_path(CONFIG_FILE), normalize_config(config))


def mask_license_key(value: str) -> str:
    clean = (value or "").strip()
    if len(clean) <= 4:
        return "*" * len(clean)
    return f"{'*' * max(len(clean) - 4, 0)}{clean[-4:]}"


def mask_email(value: str) -> str:
    clean = (value or "").strip().lower()
    if "@" not in clean:
        return clean
    user, domain = clean.split("@", 1)
    if len(user) <= 2:
        masked_user = user[:1] + "*"
    else:
        masked_user = user[:2] + ("*" * max(len(user) - 2, 1))
    return f"{masked_user}@{domain}"


def _base_server_url(server_url: str) -> str:
    value = server_url.rstrip("/")
    for suffix in ("/api/licenses/check", "/api/licenses/deactivate"):
        if value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def _endpoint(server_url: str, action: str = "check") -> str:
    return _base_server_url(server_url).rstrip("/") + f"/api/licenses/{action}"


def _ssl_context():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _post_license_request(config: dict[str, Any], action: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        _endpoint(config["server_url"], action),
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SistemaGuimmaLicenca/1.0",
        },
        method="POST",
    )

    timeout = int(config.get("request_timeout_seconds") or 10)
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            raw_error = exc.read().decode("utf-8")
        except Exception:
            raw_error = str(exc)
        raise RuntimeError(f"Servidor recusou a licenca: {raw_error}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Nao foi possivel conectar ao servidor de licencas: {exc}") from exc

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("Resposta invalida do servidor de licencas.")
    return data


def sync_once(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = normalize_config(config or load_config())
    if not cfg.get("server_url"):
        raise RuntimeError("URL do servidor de licencas nao configurada.")
    if not cfg.get("customer_email"):
        raise RuntimeError("Email do cliente nao configurado.")

    payload = {
        "app": APP_NAME,
        "customer_email": cfg["customer_email"],
        "machine": machine_summary(),
    }
    if cfg.get("license_key"):
        payload["license_key"] = cfg["license_key"]
    data = _post_license_request(cfg, "check", payload)

    status = str(data.get("status") or "inactive").lower()
    valid_until = data.get("valid_until")
    grace_until = data.get("grace_until")
    if status == "active" and valid_until and not grace_until:
        try:
            grace_days = int(cfg.get("grace_days_when_paid") or 0)
        except Exception:
            grace_days = 0
        if grace_days > 0:
            from licenciamento.store import parse_datetime

            valid_dt = parse_datetime(valid_until)
            if valid_dt:
                grace_until = iso_utc(valid_dt + timedelta(days=grace_days))

    state = {
        "status": status,
        "valid_until": valid_until,
        "grace_until": grace_until,
        "customer_email": str(data.get("customer_email") or cfg["customer_email"]).strip().lower(),
        "customer_email_masked": mask_email(str(data.get("customer_email") or cfg["customer_email"])),
        "customer_name": data.get("customer_name") or data.get("customer") or "",
        "plan": data.get("plan") or "",
        "license_key_masked": mask_license_key(cfg["license_key"]) if cfg.get("license_key") else "",
        "last_checked_at": iso_utc(utcnow()),
        "server_message": data.get("message") or "",
        "activation": data.get("activation") or {},
        "source": "server",
    }
    state.update(machine_summary())
    save_license_state(state)
    return state


def deactivate_current(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = normalize_config(config or load_config())
    if not cfg.get("server_url"):
        raise RuntimeError("URL do servidor de licencas nao configurada.")
    if not cfg.get("customer_email"):
        raise RuntimeError("Email do cliente nao configurado.")

    payload = {
        "app": APP_NAME,
        "customer_email": cfg["customer_email"],
        "machine": machine_summary(),
    }
    data = _post_license_request(cfg, "deactivate", payload)
    status = str(data.get("status") or "").lower()
    if status != "deactivated":
        raise RuntimeError(data.get("message") or "Licenca nao foi desativada.")

    clear_license_state()
    return {
        "status": status,
        "customer_email": str(data.get("customer_email") or cfg["customer_email"]).strip().lower(),
        "message": data.get("message") or "Licenca desativada neste computador.",
    }


def current_status_text() -> str:
    validation = validate_state()
    if validation.ok:
        suffix = ""
        if validation.expires_at:
            suffix = f" Ate {validation.expires_at.strftime('%d/%m/%Y %H:%M')}"
        if validation.grace:
            return "Licenca em tolerancia." + suffix
        return "Licenca valida." + suffix
    return validation.message
