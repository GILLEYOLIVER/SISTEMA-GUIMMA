from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any, Iterable

from licenciamento import APP_NAME

CONFIG_FILE = "license_config.json"
STATE_FILE = "license_state.json"
SECRET_FILE = "license_secret.key"
LOG_FILE = "licenciamento.log"


def _home_license_dir() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME / "Licenciamento"
    if system == "Windows":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_NAME / "Licenciamento"
        return Path.home() / "AppData" / "Roaming" / APP_NAME / "Licenciamento"
    return Path.home() / ".config" / APP_NAME / "Licenciamento"


def _system_license_dir() -> Path | None:
    system = platform.system()
    if system == "Darwin":
        return Path("/Library/Application Support") / APP_NAME / "Licenciamento"
    if system == "Windows":
        base = os.environ.get("ProgramData")
        if base:
            return Path(base) / APP_NAME / "Licenciamento"
    return None


def get_license_dir(create: bool = True) -> Path:
    override = os.environ.get("GUIMMA_LICENSE_DIR")
    path = Path(override).expanduser() if override else _home_license_dir()
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_writable_path(filename: str) -> Path:
    folder = get_license_dir(create=True)
    return folder / filename


def candidate_license_dirs() -> list[Path]:
    dirs: list[Path] = []
    override = os.environ.get("GUIMMA_LICENSE_DIR")
    if override:
        return _dedupe([Path(override).expanduser()])
    system_dir = _system_license_dir()
    if system_dir is not None:
        dirs.append(system_dir)
    dirs.append(_home_license_dir())

    unique: list[Path] = []
    seen: set[str] = set()
    for item in dirs:
        key = str(item)
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def candidate_config_paths() -> list[Path]:
    paths: list[Path] = []
    explicit = os.environ.get("SISTEMA_GUIMMA_LICENSE_CONFIG")
    if explicit:
        paths.append(Path(explicit).expanduser())

    for folder in candidate_license_dirs():
        paths.append(folder / CONFIG_FILE)

    root = project_root()
    paths.extend(
        [
            root / "config.json",
            root / "PAGINAS_DO_SISTEMA" / "config.json",
            root / "licenciamento" / CONFIG_FILE,
        ]
    )
    return _dedupe(paths)


def candidate_state_paths() -> list[Path]:
    return _dedupe([folder / STATE_FILE for folder in candidate_license_dirs()])


def _dedupe(paths: Iterable[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON invalido em {path}")
    return data


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)
