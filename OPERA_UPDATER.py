# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import socket
import subprocess
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

PAGES_DIR = Path(__file__).resolve().parent / 'PAGINAS_DO_SISTEMA'
if str(PAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PAGES_DIR))

EXCLUDE_DIRS = {
    '__pycache__', '.git', '.idea', '.venv', 'venv', 'backup_versoes',
    'releases_cache', 'logs_update', 'dist', 'build'
}
EXCLUDE_FILES = {'update_result.json'}
LOCK_NAME = 'OPERA_SYSTEM_UPDATE'
VALID_UPDATE_STATUS = (
    'PENDENTE', 'BAIXANDO', 'VALIDANDO', 'APLICANDO', 'MIGRANDO',
    'CONCLUIDO', 'FALHOU', 'RESTAURADO'
)
VALID_MIGRATION_STATUS = ('EXECUTANDO', 'SUCESSO', 'ERRO')

def _get_db_connection():
    from BANCO_DE_DADOS_PG import get_connection
    return get_connection()


@dataclass
class UpdateDbContext:
    schema: str
    history_id: int | None = None
    lock_acquired: bool = False


def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _now_iso() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _sha256_tree(path: Path) -> str:
    h = hashlib.sha256()
    files = sorted([p for p in path.rglob('*') if p.is_file()])
    for fp in files:
        rel = fp.relative_to(path).as_posix().encode('utf-8', 'ignore')
        h.update(rel)
        h.update(b'\0')
        with fp.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        h.update(b'\0')
    return h.hexdigest()


def _parse_version(v: str) -> tuple[int, ...]:
    clean = ''.join(ch if (ch.isdigit() or ch == '.') else '' for ch in (v or '').strip())
    if not clean:
        return (0,)
    return tuple(int(p) for p in clean.split('.') if p.isdigit()) or (0,)


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


def _db_schema_name() -> str:
    return (os.environ.get('OPERA_PG_SCHEMA') or 'opera').strip() or 'opera'


def _with_db_cursor(conn):
    cur = conn.cursor()
    try:
        yield cur
    finally:
        cur.close()


def _ensure_update_tables(conn, schema: str):
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS {schema};')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {schema}._schema_info (
                schema_name VARCHAR(120) PRIMARY KEY,
                versao VARCHAR(40) NOT NULL,
                atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {schema}.schema_version (
                modulo VARCHAR(100) PRIMARY KEY,
                versao INTEGER NOT NULL DEFAULT 0,
                atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {schema}.schema_migrations (
                id BIGSERIAL PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                modulo VARCHAR(100) NOT NULL DEFAULT 'core_update',
                versao_alvo VARCHAR(40),
                checksum_sha256 VARCHAR(64),
                app_version VARCHAR(40),
                status VARCHAR(20) NOT NULL CHECK (status IN {VALID_MIGRATION_STATUS}),
                iniciado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finalizado_em TIMESTAMP,
                erro TEXT,
                usuario_id VARCHAR(120),
                usuario_nome VARCHAR(180),
                detalhes JSONB
            );
        ''')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {schema}.app_update_history (
                id BIGSERIAL PRIMARY KEY,
                app_name VARCHAR(80) NOT NULL DEFAULT 'OPERA',
                version_from VARCHAR(40) NOT NULL,
                version_to VARCHAR(40) NOT NULL,
                status VARCHAR(20) NOT NULL CHECK (status IN {VALID_UPDATE_STATUS}),
                etapa_atual VARCHAR(80),
                error_message TEXT,
                rollback_executado BOOLEAN NOT NULL DEFAULT FALSE,
                rollback_sucesso BOOLEAN,
                backup_id BIGINT,
                machine_name VARCHAR(180),
                process_id INTEGER,
                usuario_id VARCHAR(120),
                usuario_nome VARCHAR(180),
                iniciado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                concluido_em TIMESTAMP,
                detalhes JSONB
            );
        ''')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {schema}.app_backups (
                id BIGSERIAL PRIMARY KEY,
                backup_nome VARCHAR(200) UNIQUE NOT NULL,
                version_origem VARCHAR(40) NOT NULL,
                schema_origem VARCHAR(40),
                caminho_arquivos TEXT NOT NULL,
                caminho_dump_banco TEXT,
                backup_sha256 VARCHAR(64),
                status VARCHAR(30) NOT NULL DEFAULT 'CRIADO',
                restore_usado BOOLEAN NOT NULL DEFAULT FALSE,
                criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                criado_por VARCHAR(180)
            );
        ''')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {schema}.app_update_lock (
                lock_name VARCHAR(80) PRIMARY KEY,
                locked BOOLEAN NOT NULL DEFAULT FALSE,
                locked_by VARCHAR(180),
                machine_name VARCHAR(180),
                process_id INTEGER,
                version_target VARCHAR(40),
                acquired_at TIMESTAMP,
                expires_at TIMESTAMP
            );
        ''')
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {schema}.app_releases (
                id BIGSERIAL PRIMARY KEY,
                app_name VARCHAR(80) NOT NULL DEFAULT 'OPERA',
                channel VARCHAR(30) NOT NULL DEFAULT 'stable',
                version VARCHAR(40) NOT NULL,
                requires_schema BOOLEAN NOT NULL DEFAULT FALSE,
                min_supported_version VARCHAR(40),
                package_sha256 VARCHAR(64),
                manifest_json JSONB,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (app_name, channel, version)
            );
        ''')
    conn.commit()


def _insert_release_if_needed(conn, schema: str, manifest: dict):
    version = str(manifest.get('version') or manifest.get('versao') or '').strip()
    if not version:
        return
    channel = str(manifest.get('channel') or 'stable').strip() or 'stable'
    requires_schema = bool(manifest.get('requires_schema', False))
    min_supported_version = str(manifest.get('min_supported_version') or '').strip() or None
    package_sha = str(manifest.get('package_sha256') or '').strip() or None

    with conn.cursor() as cur:
        cur.execute(
            f'''
            INSERT INTO {schema}.app_releases
                (app_name, channel, version, requires_schema, min_supported_version, package_sha256, manifest_json)
            VALUES ('OPERA', %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (app_name, channel, version)
            DO UPDATE SET
                requires_schema = EXCLUDED.requires_schema,
                min_supported_version = EXCLUDED.min_supported_version,
                package_sha256 = EXCLUDED.package_sha256,
                manifest_json = EXCLUDED.manifest_json;
            ''',
            (channel, version, requires_schema, min_supported_version, package_sha, json.dumps(manifest, ensure_ascii=False)),
        )
    conn.commit()


def _create_history(conn, schema: str, version_from: str, version_to: str, user_id: str, user_name: str, details: dict) -> int:
    with conn.cursor() as cur:
        cur.execute(
            f'''
            INSERT INTO {schema}.app_update_history
                (version_from, version_to, status, etapa_atual, machine_name, process_id, usuario_id, usuario_nome, detalhes)
            VALUES
                (%s, %s, 'PENDENTE', 'INICIANDO', %s, %s, %s, %s, %s::jsonb)
            RETURNING id;
            ''',
            (version_from, version_to, socket.gethostname(), os.getpid(), user_id or None, user_name or None, json.dumps(details, ensure_ascii=False)),
        )
        history_id = int(cur.fetchone()[0])
    conn.commit()
    return history_id


def _update_history(conn, schema: str, history_id: int, status: str, stage: str, error: str | None = None, extra: dict | None = None):
    with conn.cursor() as cur:
        cur.execute(
            f'''
            UPDATE {schema}.app_update_history
               SET status = %s,
                   etapa_atual = %s,
                   error_message = COALESCE(%s, error_message),
                   detalhes = CASE WHEN %s IS NULL THEN detalhes ELSE COALESCE(detalhes, '{{}}'::jsonb) || %s::jsonb END,
                   concluido_em = CASE WHEN %s IN ('CONCLUIDO', 'FALHOU', 'RESTAURADO') THEN CURRENT_TIMESTAMP ELSE concluido_em END
             WHERE id = %s;
            ''',
            (status, stage, error, json.dumps(extra, ensure_ascii=False) if extra else None, json.dumps(extra, ensure_ascii=False) if extra else None, status, history_id),
        )
    conn.commit()


def _set_history_backup(conn, schema: str, history_id: int, backup_id: int):
    with conn.cursor() as cur:
        cur.execute(f'UPDATE {schema}.app_update_history SET backup_id = %s WHERE id = %s;', (backup_id, history_id))
    conn.commit()


def _set_history_rollback(conn, schema: str, history_id: int, success: bool):
    with conn.cursor() as cur:
        cur.execute(
            f'''UPDATE {schema}.app_update_history
                   SET rollback_executado = TRUE,
                       rollback_sucesso = %s
                 WHERE id = %s;''',
            (success, history_id),
        )
    conn.commit()


def _acquire_lock(conn, schema: str, version_target: str, user_name: str):
    now = datetime.now()
    expires_at = now + timedelta(minutes=45)
    with conn.cursor() as cur:
        cur.execute(
            f'''
            INSERT INTO {schema}.app_update_lock
                (lock_name, locked, locked_by, machine_name, process_id, version_target, acquired_at, expires_at)
            VALUES
                (%s, TRUE, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            ON CONFLICT (lock_name)
            DO NOTHING;
            ''',
            (LOCK_NAME, user_name or 'system', socket.gethostname(), os.getpid(), version_target, expires_at),
        )

        cur.execute(
            f'SELECT locked, expires_at, machine_name, process_id FROM {schema}.app_update_lock WHERE lock_name = %s FOR UPDATE;',
            (LOCK_NAME,),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError('Não foi possível inicializar lock de atualização.')

        locked, lock_expires_at, machine_name, process_id = row
        if locked and lock_expires_at and lock_expires_at > now and (machine_name != socket.gethostname() or process_id != os.getpid()):
            raise RuntimeError('Já existe atualização em andamento por outro processo.')

        cur.execute(
            f'''
            UPDATE {schema}.app_update_lock
               SET locked = TRUE,
                   locked_by = %s,
                   machine_name = %s,
                   process_id = %s,
                   version_target = %s,
                   acquired_at = CURRENT_TIMESTAMP,
                   expires_at = %s
             WHERE lock_name = %s;
            ''',
            (user_name or 'system', socket.gethostname(), os.getpid(), version_target, expires_at, LOCK_NAME),
        )
    conn.commit()


def _release_lock(conn, schema: str):
    with conn.cursor() as cur:
        cur.execute(
            f'''
            UPDATE {schema}.app_update_lock
               SET locked = FALSE,
                   expires_at = NULL,
                   acquired_at = NULL
             WHERE lock_name = %s;
            ''',
            (LOCK_NAME,),
        )
    conn.commit()


def _register_backup(conn, schema: str, backup_name: str, version_from: str, backup_dir: Path, backup_hash: str, user_name: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            f'''
            INSERT INTO {schema}.app_backups
                (backup_nome, version_origem, schema_origem, caminho_arquivos, backup_sha256, criado_por)
            VALUES
                (%s, %s, %s, %s, %s, %s)
            RETURNING id;
            ''',
            (backup_name, version_from, schema, str(backup_dir), backup_hash, user_name or 'system'),
        )
        backup_id = int(cur.fetchone()[0])
    conn.commit()
    return backup_id


def _set_backup_restored(conn, schema: str, backup_name: str):
    with conn.cursor() as cur:
        cur.execute(f'UPDATE {schema}.app_backups SET restore_usado = TRUE, status = %s WHERE backup_nome = %s;', ('RESTAURADO', backup_name))
    conn.commit()


def _register_migration_start(conn, schema: str, migration_name: str, target_version: str, checksum: str, user_id: str, user_name: str):
    with conn.cursor() as cur:
        cur.execute(
            f'''
            INSERT INTO {schema}.schema_migrations
                (migration_name, modulo, versao_alvo, checksum_sha256, app_version, status, usuario_id, usuario_nome)
            VALUES
                (%s, 'core_update', %s, %s, %s, 'EXECUTANDO', %s, %s)
            ON CONFLICT (migration_name)
            DO UPDATE SET
                status = 'EXECUTANDO',
                erro = NULL,
                finalizado_em = NULL,
                checksum_sha256 = EXCLUDED.checksum_sha256,
                app_version = EXCLUDED.app_version,
                usuario_id = EXCLUDED.usuario_id,
                usuario_nome = EXCLUDED.usuario_nome,
                iniciado_em = CURRENT_TIMESTAMP;
            ''',
            (migration_name, target_version, checksum, target_version, user_id or None, user_name or None),
        )
    conn.commit()


def _register_migration_end(conn, schema: str, migration_name: str, ok: bool, error: str | None = None):
    with conn.cursor() as cur:
        cur.execute(
            f'''
            UPDATE {schema}.schema_migrations
               SET status = %s,
                   erro = %s,
                   finalizado_em = CURRENT_TIMESTAMP
             WHERE migration_name = %s;
            ''',
            ('SUCESSO' if ok else 'ERRO', error, migration_name),
        )
    conn.commit()


def _update_schema_info(conn, schema: str, target_version: str):
    with conn.cursor() as cur:
        cur.execute(
            f'''
            INSERT INTO {schema}._schema_info (schema_name, versao, atualizado_em)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (schema_name)
            DO UPDATE SET versao = EXCLUDED.versao, atualizado_em = CURRENT_TIMESTAMP;
            ''',
            (schema, target_version),
        )
    conn.commit()


def _validate_package(package_root: Path, manifest: dict, current_version: str):
    if not package_root.exists() or not package_root.is_dir():
        raise RuntimeError('Pacote de atualização não encontrado ou inválido.')

    source_root = _detect_app_source(package_root)
    if not source_root.exists() or not source_root.is_dir():
        raise RuntimeError('Estrutura inválida: pasta APP não encontrada.')

    target_version = str(manifest.get('version') or manifest.get('versao') or '').strip()
    if not target_version:
        raise RuntimeError('manifest.json inválido: versão de destino não informada.')

    min_supported = str(manifest.get('min_supported_version') or '').strip()
    if min_supported and _parse_version(current_version) < _parse_version(min_supported):
        raise RuntimeError(
            f'Versão atual ({current_version}) é menor que a mínima suportada ({min_supported}).'
        )

    expected_hash = str(manifest.get('package_sha256') or '').strip().lower()
    if expected_hash:
        package_hash = _sha256_tree(package_root)
        if package_hash != expected_hash:
            raise RuntimeError('Integridade do pacote inválida (SHA256 divergente).')

    requires_schema = bool(manifest.get('requires_schema', False))
    if requires_schema:
        mig_root = package_root / 'MIGRATIONS'
        if not mig_root.exists() or not mig_root.is_dir():
            raise RuntimeError('Pacote requer schema, mas pasta MIGRATIONS está ausente.')


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
    proc = subprocess.run([sys.executable, str(script_path)], cwd=str(cwd), capture_output=True, text=True)
    out = (proc.stdout or '').strip()
    err = (proc.stderr or '').strip()
    msg = '\n'.join([x for x in (out, err) if x]).strip()
    return proc.returncode == 0, msg


def _apply_migrations(app_root: Path, package_root: Path, target_version: str, db_conn, db_ctx: UpdateDbContext, user_id: str, user_name: str) -> tuple[bool, str]:
    migration_root = package_root / 'MIGRATIONS'
    logs: list[str] = []

    migration_scripts = sorted(migration_root.glob('*.py')) if migration_root.exists() else []
    for script in migration_scripts:
        checksum = _sha256_file(script)
        _register_migration_start(db_conn, db_ctx.schema, script.name, target_version, checksum, user_id, user_name)
        ok, msg = _run_python_script(script, app_root)
        logs.append(f'{script.name}: {msg or ("OK" if ok else "FALHOU")}')
        _register_migration_end(db_conn, db_ctx.schema, script.name, ok, None if ok else msg)
        if not ok:
            return False, '\n'.join(logs)

    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))

    for mod_name in ['SCHEMA.SCHEMA_MANAGER', 'SCHEMA_MANAGER']:
        try:
            module = importlib.import_module(mod_name)
            fn = getattr(module, 'aplicar_migracoes_pendentes', None)
            if callable(fn):
                fn()
                logs.append(f'{mod_name}: aplicar_migracoes_pendentes executada com sucesso.')
                break
        except Exception as exc:
            logs.append(f'{mod_name}: {exc}')

    _update_schema_info(db_conn, db_ctx.schema, target_version)
    return True, '\n'.join(logs) if logs else 'Nenhuma migração pendente encontrada.'


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

    db_conn = _get_db_connection()
    db_schema = _db_schema_name()
    db_ctx = UpdateDbContext(schema=db_schema)

    backup_dir: Path | None = None
    backup_name = ''

    try:
        _ensure_update_tables(db_conn, db_schema)
        _insert_release_if_needed(db_conn, db_schema, manifest)
        db_ctx.history_id = _create_history(
            db_conn,
            db_schema,
            current_version,
            target_version,
            user_id,
            user_name,
            {'manifest': manifest, 'package_root': str(package_root)},
        )

        _update_history(db_conn, db_schema, db_ctx.history_id, 'VALIDANDO', 'VALIDANDO_PACOTE')
        _validate_package(package_root, manifest, current_version)

        _acquire_lock(db_conn, db_schema, target_version, user_name)
        db_ctx.lock_acquired = True

        _update_history(db_conn, db_schema, db_ctx.history_id, 'APLICANDO', 'CRIANDO_BACKUP')
        backup_dir = _backup_app(app_root, current_version)
        backup_name = backup_dir.name
        backup_hash = _sha256_tree(backup_dir)
        backup_id = _register_backup(db_conn, db_schema, backup_name, current_version, backup_dir, backup_hash, user_name)
        _set_history_backup(db_conn, db_schema, db_ctx.history_id, backup_id)

        state['backup_dir'] = str(backup_dir)
        state['status'] = 'copying_files'
        _write_state(app_root, state)
        _update_history(db_conn, db_schema, db_ctx.history_id, 'APLICANDO', 'COPIANDO_ARQUIVOS')

        _copy_release_to_app(source_root, app_root)

        state['status'] = 'running_migrations'
        _write_state(app_root, state)
        _update_history(db_conn, db_schema, db_ctx.history_id, 'MIGRANDO', 'APLICANDO_MIGRACOES')

        ok, mig_msg = _apply_migrations(app_root, package_root, target_version, db_conn, db_ctx, user_id, user_name)
        if not ok:
            raise RuntimeError(mig_msg or 'Falha ao aplicar migrações.')

        state['status'] = 'completed'
        state['current_version'] = target_version
        state['completed_at'] = _now_iso()
        _write_state(app_root, state)

        _update_history(db_conn, db_schema, db_ctx.history_id, 'CONCLUIDO', 'FINALIZADO', extra={'migration_log': mig_msg})
        if db_ctx.lock_acquired:
            _release_lock(db_conn, db_schema)
            db_ctx.lock_acquired = False

        _write_result(app_root, {
            'ok': True,
            'version': target_version,
            'message': f'Atualização concluída com sucesso. Nova versão: {target_version}.',
            'backup_dir': str(backup_dir),
            'migration_log': mig_msg,
        })
        return 0
    except Exception as exc:
        err_txt = str(exc)
        trace_txt = traceback.format_exc(limit=8)
        rollback_ok = False

        if backup_dir and backup_dir.exists():
            try:
                _restore_backup(backup_dir, app_root)
                rollback_ok = True
            except Exception:
                rollback_ok = False

        state['status'] = 'restored_after_failure' if rollback_ok else 'failed'
        state['completed_at'] = _now_iso()
        state['error'] = err_txt
        _write_state(app_root, state)

        if db_ctx.history_id:
            final_status = 'RESTAURADO' if rollback_ok else 'FALHOU'
            _update_history(db_conn, db_schema, db_ctx.history_id, final_status, 'ERRO', error=err_txt, extra={'traceback': trace_txt})
            _set_history_rollback(db_conn, db_schema, db_ctx.history_id, rollback_ok)

        if db_ctx.lock_acquired:
            _release_lock(db_conn, db_schema)

        if rollback_ok and backup_name:
            _set_backup_restored(db_conn, db_schema, backup_name)

        rollback_txt = 'executado' if rollback_ok else 'não executado'
        _write_result(app_root, {
            'ok': False,
            'version': current_version,
            'message': f'Falha na atualização. Rollback {rollback_txt}. Detalhes: {err_txt}',
            'backup_dir': str(backup_dir) if backup_dir else None,
            'traceback': trace_txt,
        })
        return 1


def restore_latest(app_root: Path) -> int:
    db_conn = _get_db_connection()
    db_schema = _db_schema_name()
    _ensure_update_tables(db_conn, db_schema)

    backup_root = app_root / 'backup_versoes'
    backups = sorted([p for p in backup_root.iterdir() if p.is_dir()], reverse=True) if backup_root.exists() else []
    if not backups:
        _write_result(app_root, {'ok': False, 'message': 'Nenhum backup encontrado para restauração.'})
        return 1

    backup_dir = backups[0]
    try:
        _restore_backup(backup_dir, app_root)
        _set_backup_restored(db_conn, db_schema, backup_dir.name)

        meta = _read_json(backup_dir / 'restore_info.json', {}) or {}
        history_id = _create_history(
            db_conn,
            db_schema,
            str(meta.get('version') or 'desconhecida'),
            str(meta.get('version') or 'desconhecida'),
            '',
            'system_restore',
            {'restore_backup': backup_dir.name},
        )
        _set_history_rollback(db_conn, db_schema, history_id, True)
        _update_history(db_conn, db_schema, history_id, 'RESTAURADO', 'RESTAURACAO_MANUAL')

        _write_result(app_root, {
            'ok': True,
            'message': f'Restauração concluída com sucesso a partir de {backup_dir.name}.',
            'restored_version': meta.get('version'),
            'backup_dir': str(backup_dir),
        })
        return 0
    except Exception as exc:
        _write_result(app_root, {
            'ok': False,
            'message': f'Falha ao restaurar backup {backup_dir.name}: {exc}',
            'backup_dir': str(backup_dir),
        })
        return 1


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
