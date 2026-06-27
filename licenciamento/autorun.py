from __future__ import annotations

import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path

LABEL = "com.sistemaguimma.licenca"


def _program_arguments() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--daemon"]
    return [sys.executable, "-m", "licenciamento.agent", "--daemon"]


def install_autostart() -> str:
    if sys.platform == "darwin":
        folder = Path.home() / "Library" / "LaunchAgents"
        folder.mkdir(parents=True, exist_ok=True)
        plist_path = folder / f"{LABEL}.plist"
        payload = {
            "Label": LABEL,
            "ProgramArguments": _program_arguments(),
            "RunAtLoad": True,
            "StartInterval": 3600,
            "KeepAlive": False,
        }
        with plist_path.open("wb") as handle:
            plistlib.dump(payload, handle)
        subprocess.run(["launchctl", "unload", str(plist_path)], check=False, capture_output=True)
        subprocess.run(["launchctl", "load", str(plist_path)], check=False, capture_output=True)
        return f"Inicializacao automatica instalada: {plist_path}"

    if os.name == "nt":
        import winreg

        command = " ".join(f'"{part}"' if " " in part else part for part in _program_arguments())
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "SistemaGuimmaLicenca", 0, winreg.REG_SZ, command)
        return "Inicializacao automatica instalada no Windows."

    folder = Path.home() / ".config" / "autostart"
    folder.mkdir(parents=True, exist_ok=True)
    desktop = folder / "sistema-guimma-licenca.desktop"
    command = " ".join(shlex.quote(part) for part in _program_arguments())
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Sistema Guimma Licenca\n"
        f"Exec={command}\n"
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )
    return f"Inicializacao automatica instalada: {desktop}"


def uninstall_autostart() -> str:
    if sys.platform == "darwin":
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
        subprocess.run(["launchctl", "unload", str(plist_path)], check=False, capture_output=True)
        if plist_path.exists():
            plist_path.unlink()
        return "Inicializacao automatica removida do macOS."

    if os.name == "nt":
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, "SistemaGuimmaLicenca")
            except FileNotFoundError:
                pass
        return "Inicializacao automatica removida do Windows."

    desktop = Path.home() / ".config" / "autostart" / "sistema-guimma-licenca.desktop"
    if desktop.exists():
        desktop.unlink()
    return "Inicializacao automatica removida."
