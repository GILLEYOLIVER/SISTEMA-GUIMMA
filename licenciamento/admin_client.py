from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from licenciamento.client import DEFAULT_SERVER_URL
from licenciamento.paths import get_writable_path, project_root, read_json, write_json_atomic

ADMIN_CONFIG_FILE = "admin_config.json"


def _ssl_context():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _read_dev_vars(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        if not path.is_file():
            return data
        for line in path.read_text(encoding="utf-8").splitlines():
            clean = line.strip()
            if not clean or clean.startswith("#") or "=" not in clean:
                continue
            key, value = clean.split("=", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
    except Exception:
        return {}
    return data


def _candidate_dev_var_paths() -> list[Path]:
    root = project_root()
    home = Path.home()
    return [
        root / "servidor_licencas_cloudflare" / ".dev.vars",
        Path.cwd() / "servidor_licencas_cloudflare" / ".dev.vars",
        home / "PycharmProjects" / "SISTEMA-GUIMMA" / "servidor_licencas_cloudflare" / ".dev.vars",
    ]


def load_admin_config() -> dict[str, Any]:
    config = {
        "server_url": DEFAULT_SERVER_URL,
        "admin_token": "",
        "default_days": 30,
    }

    stored_path = get_writable_path(ADMIN_CONFIG_FILE)
    try:
        if stored_path.is_file():
            data = read_json(stored_path)
            config.update(data)
    except Exception:
        pass

    env_url = os.environ.get("GUIMMA_LICENSE_ADMIN_URL", "").strip()
    env_token = os.environ.get("GUIMMA_LICENSE_ADMIN_TOKEN", "").strip()
    if env_url:
        config["server_url"] = env_url
    if env_token:
        config["admin_token"] = env_token

    if not str(config.get("admin_token") or "").strip():
        for path in _candidate_dev_var_paths():
            dev_vars = _read_dev_vars(path)
            token = dev_vars.get("ADMIN_TOKEN", "").strip()
            if token:
                config["admin_token"] = token
                break

    config["server_url"] = str(config.get("server_url") or DEFAULT_SERVER_URL).strip().rstrip("/")
    config["admin_token"] = str(config.get("admin_token") or "").strip()
    try:
        config["default_days"] = max(int(config.get("default_days") or 30), 1)
    except Exception:
        config["default_days"] = 30
    return config


def save_admin_config(config: dict[str, Any]) -> None:
    cleaned = {
        "server_url": str(config.get("server_url") or DEFAULT_SERVER_URL).strip().rstrip("/"),
        "admin_token": str(config.get("admin_token") or "").strip(),
        "default_days": max(int(config.get("default_days") or 30), 1),
    }
    write_json_atomic(get_writable_path(ADMIN_CONFIG_FILE), cleaned)


def normalize_email(value: str) -> str:
    return str(value or "").strip().lower()


def _require_config(config: dict[str, Any]) -> tuple[str, str]:
    server_url = str(config.get("server_url") or DEFAULT_SERVER_URL).strip().rstrip("/")
    token = str(config.get("admin_token") or "").strip()
    if not server_url:
        raise RuntimeError("URL do servidor nao configurada.")
    if not token:
        raise RuntimeError("Token administrativo nao encontrado. Abra Configurar e informe o token.")
    return server_url, token


def _admin_request(
    method: str,
    path: str,
    config: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    server_url, token = _require_config(config)
    body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        server_url.rstrip("/") + path,
        data=body,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "SistemaGuimmaLicencasAdmin/1.0",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=12, context=_ssl_context()) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        try:
            raw_error = exc.read().decode("utf-8")
        except Exception:
            raw_error = str(exc)
        raise RuntimeError(f"Servidor recusou a operacao: {raw_error}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Nao foi possivel conectar ao servidor: {exc}") from exc

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("Resposta invalida do servidor.")
    return data


def get_customer(email: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or load_admin_config()
    clean_email = normalize_email(email)
    if not clean_email or "@" not in clean_email:
        raise RuntimeError("Informe um email valido.")
    query = urllib.parse.urlencode({"email": clean_email})
    return _admin_request("GET", f"/api/admin/customers/get?{query}", cfg)


def upsert_license(
    email: str,
    status: str,
    config: dict[str, Any] | None = None,
    customer_name: str = "",
    days: int = 30,
    plan: str = "mensal",
) -> dict[str, Any]:
    cfg = config or load_admin_config()
    clean_email = normalize_email(email)
    if not clean_email or "@" not in clean_email:
        raise RuntimeError("Informe um email valido.")
    payload = {
        "customer_email": clean_email,
        "customer_name": customer_name.strip(),
        "plan": plan.strip() or "mensal",
        "status": status.strip().lower(),
        "days": max(int(days or 30), 1),
    }
    return _admin_request("POST", "/api/admin/customers/upsert", cfg, payload)


def extend_license(email: str, config: dict[str, Any] | None = None, days: int = 30) -> dict[str, Any]:
    cfg = config or load_admin_config()
    clean_email = normalize_email(email)
    if not clean_email or "@" not in clean_email:
        raise RuntimeError("Informe um email valido.")
    payload = {"customer_email": clean_email, "days": max(int(days or 30), 1)}
    return _admin_request("POST", "/api/admin/customers/extend", cfg, payload)


def release_activation(email: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or load_admin_config()
    clean_email = normalize_email(email)
    if not clean_email or "@" not in clean_email:
        raise RuntimeError("Informe um email valido.")
    return _admin_request("POST", "/api/admin/customers/release", cfg, {"customer_email": clean_email})


def format_customer_summary(data: dict[str, Any]) -> str:
    customer = data.get("customer") or {}
    activation = data.get("activation") or {}
    if not customer:
        return "Cliente nao encontrado."

    lines = [
        f"Email: {customer.get('email') or ''}",
        f"Nome: {customer.get('customer_name') or '-'}",
        f"Plano: {customer.get('plan') or '-'}",
        f"Status: {customer.get('status') or '-'}",
        f"Validade: {customer.get('valid_until') or '-'}",
    ]
    if activation:
        lines.extend(
            [
                "",
                "Computador ativo:",
                f"ID: {activation.get('machine_id') or '-'}",
                f"Nome: {activation.get('hostname') or '-'}",
                f"Sistema: {activation.get('system') or '-'}",
                f"Ativado em: {activation.get('activated_at') or '-'}",
                f"Ultimo uso: {activation.get('last_seen_at') or '-'}",
            ]
        )
    else:
        lines.extend(["", "Computador ativo: nenhum"])
    return "\n".join(lines)
