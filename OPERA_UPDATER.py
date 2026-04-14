# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import importlib
import json
import shutil
import socket
import sys
from datetime import datetime
from pathlib import Path

EXCLUDE_DIRS = {
    '__pycache__', '.git', '.idea', '.venv', 'venv', 'backup_versoes',
    'releases_cache', 'logs_update', 'dist', 'build'
}
EXCLUDE_FILES = {'update_result.json'}


def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _now_iso() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _load_manifest(package_root: Path) -> dict:
    manifest_path = package_root / 'manifest.json'
    if manifest_path.exists():
        data = _read_json(manifest_path, {})
        return data if isinstance(data, dict) else {}
    return {}


def _detect_app_source(package_root: Path) -> Path:
    app_dir = package_root / 'APP'
    if app_dir.exists() and app_dir.is_dir():
        return app_dir
    return package_root


def _backup_app(app_root: Path, current_version: str) -> Path:
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_root = app_root / 'backup_versoes'
    backup_dir = backup_root / f'{stamp}_{current_version or "sem_versao"}'
    backup_dir.mkdir(parents=True, exist_ok=True)

    for item in app_root.iterdir():
        if item.name in EXCLUDE_DIRS or item.name.startswith('.git'):
            continue
        dest = backup_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            if item.name not in EXCLUDE_FILES:
                shutil.copy2(item, dest)

    _write_json(backup_dir / 'restore_info.json', {
        'created_at': _now_iso(),
        'version': current_version,
        'app_root': str(app_root),
    })
    return backup_dir


def _restore_backup(backup_dir: Path, app_root: Path):
    for item in backup_dir.iterdir():
        if item.name == 'restore_info.json':
            continue
        dest = app_root / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def _copy_release_to_app(source_root: Path, app_root: Path):
    for item in source_root.iterdir():
        if item.name in {'manifest.json', 'CHANGELOG.txt', 'MIGRATIONS'}:
            continue
        if item.name in EXCLUDE_DIRS:
            continue
        dest = app_root / item.name
        if item.is_dir():
            if dest.exists() and not dest.is_dir():
                dest.unlink(missing_ok=True)
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)


def _run_python_script(script_path: Path, cwd: Path) -> tuple[bool, str]:
    import subprocess
    proc = subprocess.run([sys.executable, str(script_path)], cwd=str(cwd), capture_output=True, text=True)
    out = (proc.stdout or '').strip()
    err = (proc.stderr or '').strip()
    msg = '\n'.join([x for x in (out, err) if x]).strip()
    return proc.returncode == 0, msg


def _apply_migrations(app_root: Path) -> tuple[bool, str]:
    migrations_dir = app_root / 'MIGRATIONS'
    logs: list[str] = []

    if migrations_dir.exists() and migrations_dir.is_dir():
        for script in sorted(migrations_dir.glob('*.py')):
            ok, msg = _run_python_script(script, app_root)
            logs.append(f'{script.name}: {msg or ("OK" if ok else "FALHOU")}')
            if not ok:
                return False, '\n'.join(logs)

    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))

    candidates = ['SCHEMA.SCHEMA_MANAGER', 'SCHEMA_MANAGER']
    for mod_name in candidates:
        try:
            module = importlib.import_module(mod_name)
            fn = getattr(module, 'aplicar_migracoes_pendentes', None)
            if callable(fn):
                fn()
                logs.append(f'{mod_name}: aplicar_migracoes_pendentes executada com sucesso.')
                return True, '\n'.join(logs)
        except Exception as exc:
            logs.append(f'{mod_name}: {exc}')

    if migrations_dir.exists() and migrations_dir.is_dir():
        return True, '\n'.join(logs) or 'Migrações python executadas.'

    return True, 'Nenhuma migração pendente encontrada.'


def _write_result(app_root: Path, payload: dict):
    _write_json(app_root / 'update_result.json', payload)


def _write_state(app_root: Path, payload: dict):
    _write_json(app_root / 'update_state.json', payload)


def apply_package(package_root: Path, app_root: Path, current_version: str, user_id: str = '', user_name: str = '') -> int:
    manifest = _load_manifest(package_root)
    target_version = str(manifest.get('version') or manifest.get('versao') or current_version or '1.0').strip()
    source_root = _detect_app_source(package_root)

    state = {
        'current_version': current_version,
        'target_version': target_version,
        'status': 'starting',
        'started_at': _now_iso(),
        'user_id': user_id,
        'user_name': user_name,
        'machine': socket.gethostname(),
    }
    _write_state(app_root, state)

    backup_dir = _backup_app(app_root, current_version)
    state['backup_dir'] = str(backup_dir)
    state['status'] = 'copying_files'
    _write_state(app_root, state)

    try:
        _copy_release_to_app(source_root, app_root)
        state['status'] = 'running_migrations'
        _write_state(app_root, state)
        ok, mig_msg = _apply_migrations(app_root)
        if not ok:
            raise RuntimeError(mig_msg or 'Falha ao aplicar migrações.')

        state['status'] = 'completed'
        state['current_version'] = target_version
        state['completed_at'] = _now_iso()
        _write_state(app_root, state)
        _write_result(app_root, {
            'ok': True,
            'version': target_version,
            'message': f'Atualização concluída com sucesso. Nova versão: {target_version}.',
            'backup_dir': str(backup_dir),
            'migration_log': mig_msg,
        })
        return 0
    except Exception as exc:
        _restore_backup(backup_dir, app_root)
        state['status'] = 'restored_after_failure'
        state['completed_at'] = _now_iso()
        state['error'] = str(exc)
        _write_state(app_root, state)
        _write_result(app_root, {
            'ok': False,
            'version': current_version,
            'message': f'Falha na atualização. Backup restaurado. Detalhes: {exc}',
            'backup_dir': str(backup_dir),
        })
        return 1


def restore_latest(app_root: Path) -> int:
    backup_root = app_root / 'backup_versoes'
    backups = sorted([p for p in backup_root.iterdir() if p.is_dir()], reverse=True) if backup_root.exists() else []
    if not backups:
        _write_result(app_root, {'ok': False, 'message': 'Nenhum backup encontrado para restauração.'})
        return 1
    backup_dir = backups[0]
    _restore_backup(backup_dir, app_root)
    meta = _read_json(backup_dir / 'restore_info.json', {}) or {}
    _write_result(app_root, {
        'ok': True,
        'message': f'Restauração concluída com sucesso a partir de {backup_dir.name}.',
        'restored_version': meta.get('version'),
        'backup_dir': str(backup_dir),
    })
    return 0


def main():
    parser = argparse.ArgumentParser(description='Atualizador externo do OPERA')
    parser.add_argument('--apply', dest='package_root')
    parser.add_argument('--restore-latest', action='store_true')
    parser.add_argument('--app-root', required=True)
    parser.add_argument('--current-version', default='1.0')
    parser.add_argument('--user-id', default='')
    parser.add_argument('--user-name', default='')
    args = parser.parse_args()

    app_root = Path(args.app_root).resolve()
    if args.restore_latest:
        raise SystemExit(restore_latest(app_root))
    if not args.package_root:
        raise SystemExit('Pacote de atualização não informado.')
    package_root = Path(args.package_root).resolve()
    raise SystemExit(apply_package(package_root, app_root, args.current_version, args.user_id, args.user_name))


if __name__ == '__main__':
    main()
