from __future__ import annotations

import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from licenciamento.machine import machine_id
from licenciamento.paths import SECRET_FILE, STATE_FILE, candidate_state_paths, get_writable_path, read_json, write_json_atomic


@dataclass(frozen=True)
class StateValidation:
    ok: bool
    message: str
    state: dict[str, Any] | None = None
    expires_at: datetime | None = None
    grace: bool = False


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(moment: datetime | None = None) -> str:
    value = moment or utcnow()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(str(value), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _canonical(data: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in data.items() if key != "seal"}
    return json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _secret_path_for(state_path: Path | None = None) -> Path:
    if state_path is not None:
        return state_path.parent / SECRET_FILE
    return get_writable_path(SECRET_FILE)


def _read_or_create_secret() -> bytes:
    path = _secret_path_for()
    if path.is_file():
        return path.read_bytes().strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_hex(32).encode("ascii")
    path.write_bytes(secret)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    return secret


def _read_existing_secret(state_path: Path) -> bytes | None:
    path = _secret_path_for(state_path)
    try:
        if path.is_file():
            return path.read_bytes().strip()
    except Exception:
        pass
    return None


def _seal(data: dict[str, Any], secret: bytes) -> str:
    return hmac.new(secret, _canonical(data), sha256).hexdigest()


def seal_state(data: dict[str, Any]) -> dict[str, Any]:
    state = dict(data)
    state.setdefault("machine_id", machine_id())
    state["sealed_at"] = iso_utc()
    state["seal"] = _seal(state, _read_or_create_secret())
    return state


def save_license_state(data: dict[str, Any]) -> Path:
    state = seal_state(data)
    path = get_writable_path(STATE_FILE)
    write_json_atomic(path, state)
    return path


def clear_license_state() -> int:
    removed = 0
    for path in candidate_state_paths():
        try:
            if path.is_file():
                path.unlink()
                removed += 1
        except Exception:
            pass
    return removed


def _load_state_from(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        state = read_json(path)
    except Exception as exc:
        return None, f"Nao foi possivel ler a licenca local: {exc}"

    seal = str(state.get("seal") or "")
    if not seal:
        return None, "Arquivo de licenca sem assinatura local."

    secret = _read_existing_secret(path)
    if not secret:
        return None, "Chave local da licenca nao encontrada."

    expected = _seal(state, secret)
    if not hmac.compare_digest(seal, expected):
        return None, "Arquivo de licenca foi alterado fora do app."
    return state, "OK"


def load_license_state() -> tuple[dict[str, Any] | None, str]:
    for path in candidate_state_paths():
        if path.is_file():
            return _load_state_from(path)
    return None, "Nenhuma licenca local encontrada."


def validate_state(now: datetime | None = None) -> StateValidation:
    state, message = load_license_state()
    if not state:
        return StateValidation(False, message)

    current_machine = machine_id()
    licensed_machine = str(state.get("machine_id") or "")
    if licensed_machine and licensed_machine != current_machine:
        return StateValidation(False, "Licenca pertence a outro computador.", state)

    status = str(state.get("status") or "").lower()
    if status not in {"active", "trial", "grace"}:
        readable = state.get("server_message") or state.get("message") or "Licenca inativa."
        return StateValidation(False, str(readable), state)

    valid_until = parse_datetime(state.get("valid_until"))
    if not valid_until:
        return StateValidation(False, "Licenca sem data de validade.", state)

    current = now or utcnow()
    if current <= valid_until:
        return StateValidation(True, "Licenca valida.", state, expires_at=valid_until)

    grace_until = parse_datetime(state.get("grace_until"))
    if grace_until and current <= grace_until:
        return StateValidation(True, "Licenca em periodo de tolerancia.", state, expires_at=grace_until, grace=True)

    return StateValidation(False, "Licenca expirada.", state, expires_at=valid_until)
