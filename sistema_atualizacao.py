from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from typing import Iterable


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_DIR = os.path.join(BASE_DIR, "Versao do Sistema")
BACKUP_ROOT = os.path.join(BASE_DIR, "BACKUP_ATUALIZACAO")


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _log_writer(log_path: str):
    def _write(message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
        print(line)

    return _write


def _iter_version_files() -> Iterable[tuple[str, str]]:
    for root, _, files in os.walk(VERSION_DIR):
        for name in files:
            src_path = os.path.join(root, name)
            rel_path = os.path.relpath(src_path, VERSION_DIR)
            yield src_path, rel_path


def _load_manifest(backup_dir: str) -> dict:
    manifest_path = os.path.join(backup_dir, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as manifest_file:
        return json.load(manifest_file)


def _save_manifest(backup_dir: str, manifest: dict) -> None:
    manifest_path = os.path.join(backup_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, ensure_ascii=False, indent=2)


def _update_last_backup(backup_dir: str) -> None:
    _ensure_dir(BACKUP_ROOT)
    last_backup_path = os.path.join(BACKUP_ROOT, "ultimo_backup.json")
    with open(last_backup_path, "w", encoding="utf-8") as last_backup_file:
        json.dump({"backup_dir": backup_dir}, last_backup_file, ensure_ascii=False, indent=2)


def _load_last_backup() -> str:
    last_backup_path = os.path.join(BACKUP_ROOT, "ultimo_backup.json")
    if not os.path.exists(last_backup_path):
        raise FileNotFoundError("Nenhum backup de atualização encontrado.")
    with open(last_backup_path, "r", encoding="utf-8") as last_backup_file:
        data = json.load(last_backup_file)
    backup_dir = data.get("backup_dir")
    if not backup_dir:
        raise FileNotFoundError("Backup de atualização inválido.")
    return backup_dir


def atualizar_sistema() -> str:
    if not os.path.isdir(VERSION_DIR):
        raise FileNotFoundError("A pasta 'Versao do Sistema' não foi encontrada.")

    version_files = list(_iter_version_files())
    if not version_files:
        raise FileNotFoundError("A pasta 'Versao do Sistema' está vazia.")

    _ensure_dir(BACKUP_ROOT)
    log_dir = os.path.join(BACKUP_ROOT, "logs")
    _ensure_dir(log_dir)
    log_path = os.path.join(log_dir, f"atualizacao_{_timestamp()}.log")
    log = _log_writer(log_path)

    backup_dir = os.path.join(BACKUP_ROOT, f"backup_{_timestamp()}")
    _ensure_dir(backup_dir)

    manifest = {
        "created_at": datetime.now().isoformat(),
        "backup_dir": backup_dir,
        "version_dir": VERSION_DIR,
        "files": [],
    }

    log("🚀 Iniciando atualização do sistema.")
    updated_files: list[dict] = []

    try:
        for src_path, rel_path in version_files:
            dest_path = os.path.join(BASE_DIR, rel_path)
            backup_path = os.path.join(backup_dir, rel_path)
            had_original = os.path.exists(dest_path)

            manifest_entry = {
                "rel_path": rel_path,
                "had_original": had_original,
                "updated": False,
            }
            manifest["files"].append(manifest_entry)

            if had_original:
                _ensure_dir(os.path.dirname(backup_path))
                shutil.copy2(dest_path, backup_path)
                log(f"📦 Backup criado: {rel_path}")

            _ensure_dir(os.path.dirname(dest_path))
            shutil.copy2(src_path, dest_path)
            manifest_entry["updated"] = True
            updated_files.append(manifest_entry)
            log(f"✅ Arquivo atualizado: {rel_path}")

        _save_manifest(backup_dir, manifest)
        _update_last_backup(backup_dir)
        log("🎉 Atualização concluída com sucesso.")
        return log_path

    except Exception as exc:
        log(f"❌ Erro durante atualização: {exc}")
        _rollback_update(updated_files, backup_dir, log)
        raise


def _rollback_update(entries: Iterable[dict], backup_dir: str, log) -> None:
    log("↩️ Iniciando rollback automático.")
    for entry in entries:
        rel_path = entry["rel_path"]
        had_original = entry["had_original"]
        dest_path = os.path.join(BASE_DIR, rel_path)
        backup_path = os.path.join(backup_dir, rel_path)

        try:
            if had_original and os.path.exists(backup_path):
                _ensure_dir(os.path.dirname(dest_path))
                shutil.copy2(backup_path, dest_path)
                log(f"🔄 Restaurado: {rel_path}")
            elif not had_original and os.path.exists(dest_path):
                os.remove(dest_path)
                log(f"🧹 Removido arquivo novo: {rel_path}")
        except Exception as rollback_error:
            log(f"⚠️ Falha ao restaurar {rel_path}: {rollback_error}")

    log("✅ Rollback concluído.")


def downgrade_sistema() -> str:
    _ensure_dir(BACKUP_ROOT)
    log_dir = os.path.join(BACKUP_ROOT, "logs")
    _ensure_dir(log_dir)
    log_path = os.path.join(log_dir, f"downgrade_{_timestamp()}.log")
    log = _log_writer(log_path)

    log("↩️ Iniciando downgrade do sistema.")

    backup_dir = _load_last_backup()
    manifest = _load_manifest(backup_dir)

    for entry in manifest.get("files", []):
        rel_path = entry["rel_path"]
        had_original = entry["had_original"]
        dest_path = os.path.join(BASE_DIR, rel_path)
        backup_path = os.path.join(backup_dir, rel_path)

        if had_original and os.path.exists(backup_path):
            _ensure_dir(os.path.dirname(dest_path))
            shutil.copy2(backup_path, dest_path)
            log(f"🔄 Restaurado: {rel_path}")
        elif not had_original and os.path.exists(dest_path):
            os.remove(dest_path)
            log(f"🧹 Removido arquivo atualizado: {rel_path}")

    log("✅ Downgrade concluído com sucesso.")
    return log_path
