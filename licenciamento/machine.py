from __future__ import annotations

import hashlib
import os
import platform
import re
import socket
import subprocess
import uuid
from pathlib import Path

from licenciamento import APP_NAME


def _run_quiet(command: list[str], timeout: float = 2.0) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return (result.stdout or "").strip()
    except Exception:
        return ""


def _mac_platform_uuid() -> str:
    output = _run_quiet(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"])
    match = re.search(r'"IOPlatformUUID"\s=\s"([^"]+)"', output)
    return match.group(1).strip() if match else ""


def _windows_machine_uuid() -> str:
    output = _run_quiet(["wmic", "csproduct", "get", "uuid"], timeout=3.0)
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) >= 2 and "uuid" in lines[0].lower():
        return lines[1]
    return ""


def _linux_machine_id() -> str:
    for path in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
        try:
            if path.is_file():
                value = path.read_text(encoding="utf-8").strip()
                if value:
                    return value
        except Exception:
            pass
    return ""


def machine_components() -> dict[str, str]:
    system = platform.system()
    components = {
        "app": APP_NAME,
        "system": system,
        "release": platform.release(),
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
        "node": str(uuid.getnode()),
    }

    if system == "Darwin":
        components["platform_uuid"] = _mac_platform_uuid()
    elif system == "Windows":
        components["platform_uuid"] = _windows_machine_uuid()
    else:
        components["platform_uuid"] = _linux_machine_id()

    user_hint = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME")
    if user_hint:
        components["host_hint"] = user_hint
    return components


def machine_id() -> str:
    components = machine_components()
    raw = "|".join(f"{key}={components[key]}" for key in sorted(components) if components[key])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def machine_summary() -> dict[str, str]:
    return {
        "machine_id": machine_id(),
        "hostname": socket.gethostname(),
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
    }
