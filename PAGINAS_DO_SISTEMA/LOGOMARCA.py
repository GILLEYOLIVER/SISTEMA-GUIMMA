# -*- coding: utf-8 -*-
"""
Centraliza a logomarca do sistema.

A imagem escolhida pelo usuario fica em pasta gravavel do sistema, o que funciona
tambem no macOS empacotado, onde a pasta do aplicativo pode ser somente leitura.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Iterable

from PAGINAS_DO_SISTEMA.OPERA_PATHS import ensure_dir, path_in_data

CONFIG_DIR_NAME = "CONFIGURACOES"
LOGO_SETTINGS_FILE = "sistema_visual.json"
LOGO_FILE_STEM = "logomarca_sistema"
DB_KEY = "logomarca_sistema"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}


def _settings_path() -> Path:
    ensure_dir(CONFIG_DIR_NAME)
    return Path(path_in_data(CONFIG_DIR_NAME, LOGO_SETTINGS_FILE))


def load_visual_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_visual_settings(settings: dict) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings or {}, ensure_ascii=False, indent=2), encoding="utf-8")


def _saved_logo_files() -> Iterable[Path]:
    base = Path(path_in_data(CONFIG_DIR_NAME))
    for ext in sorted(SUPPORTED_EXTENSIONS):
        yield base / f"{LOGO_FILE_STEM}{ext}"


def _quote_ident(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _db_available():
    try:
        from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_schema, get_conn_cursor, get_read_cursor
        return get_schema, get_conn_cursor, get_read_cursor
    except Exception:
        return None


def _ensure_db_table() -> None:
    funcs = _db_available()
    if not funcs:
        return
    get_schema, get_conn_cursor, _ = funcs
    schema = _quote_ident(get_schema())
    with get_conn_cursor() as (_conn, cur):
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {schema}.sistema_configuracoes (
                chave TEXT PRIMARY KEY,
                valor_json JSONB,
                valor_binario BYTEA,
                atualizado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )


def _cache_logo_bytes(data: bytes, extension: str, settings: dict | None = None) -> str:
    ext = extension.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        ext = ".png"
    target_dir = ensure_dir(CONFIG_DIR_NAME)
    for old_file in _saved_logo_files():
        try:
            if old_file.exists() and old_file.suffix.lower() != ext:
                old_file.unlink()
        except Exception:
            pass
    target = target_dir / f"{LOGO_FILE_STEM}{ext}"
    target.write_bytes(data)
    current_settings = load_visual_settings()
    if settings:
        current_settings.update(settings)
    current_settings["logo_path"] = str(target)
    current_settings["logo_source"] = "database"
    save_visual_settings(current_settings)
    return str(target)


def _load_logo_from_db_to_cache() -> str:
    funcs = _db_available()
    if not funcs:
        return ""
    get_schema, _, get_read_cursor = funcs
    schema = _quote_ident(get_schema())
    try:
        _ensure_db_table()
        with get_read_cursor() as (_conn, cur):
            cur.execute(
                f"""
                SELECT valor_json, valor_binario
                  FROM {schema}.sistema_configuracoes
                 WHERE chave = %s
                """,
                (DB_KEY,),
            )
            row = cur.fetchone()
        if not row or not row["valor_binario"]:
            return ""
        meta = row["valor_json"] or {}
        if not isinstance(meta, dict):
            meta = {}
        ext = str(meta.get("extension") or ".png").lower()
        data = bytes(row["valor_binario"])
        return _cache_logo_bytes(data, ext, meta)
    except Exception:
        return ""


def _save_logo_to_db(source: Path, data: bytes) -> None:
    funcs = _db_available()
    if not funcs:
        raise RuntimeError("Banco de dados indisponivel para salvar a logomarca.")
    get_schema, get_conn_cursor, _ = funcs
    _ensure_db_table()
    schema = _quote_ident(get_schema())
    ext = source.suffix.lower()
    mime = mimetypes.guess_type(str(source))[0] or ("image/jpeg" if ext in {".jpg", ".jpeg"} else "image/png")
    meta = {
        "filename": source.name,
        "extension": ext,
        "mime": mime,
        "size": len(data),
    }
    with get_conn_cursor() as (_conn, cur):
        cur.execute(
            f"""
            INSERT INTO {schema}.sistema_configuracoes
                (chave, valor_json, valor_binario, atualizado_em)
            VALUES
                (%s, %s::jsonb, %s, NOW())
            ON CONFLICT (chave) DO UPDATE SET
                valor_json = EXCLUDED.valor_json,
                valor_binario = EXCLUDED.valor_binario,
                atualizado_em = NOW()
            """,
            (DB_KEY, json.dumps(meta, ensure_ascii=False), data),
        )


def _delete_logo_from_db() -> None:
    funcs = _db_available()
    if not funcs:
        return
    get_schema, get_conn_cursor, _ = funcs
    try:
        _ensure_db_table()
        schema = _quote_ident(get_schema())
        with get_conn_cursor() as (_conn, cur):
            cur.execute(f"DELETE FROM {schema}.sistema_configuracoes WHERE chave = %s", (DB_KEY,))
    except Exception:
        pass


def get_logo_path(default: str | None = None) -> str:
    env_path = os.environ.get("GUIMMA_LOGO_PATH", "").strip()
    if env_path and Path(env_path).expanduser().is_file():
        return str(Path(env_path).expanduser())

    db_logo = _load_logo_from_db_to_cache()
    if db_logo:
        return db_logo

    for path in _saved_logo_files():
        if path.is_file():
            return str(path)

    return ""


def set_logo_from_file(source_path: str, *, copy_to_app_data: bool = True) -> str:
    source = Path(source_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"Arquivo nao encontrado: {source}")
    ext = source.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError("Use uma imagem PNG, JPG, JPEG, BMP ou GIF.")

    data = source.read_bytes()
    _save_logo_to_db(source, data)
    return _cache_logo_bytes(
        data,
        ext,
        {
            "logo_original_path": str(source),
            "logo_filename": source.name,
        },
    )


def clear_custom_logo() -> None:
    _delete_logo_from_db()
    settings = load_visual_settings()
    settings.pop("logo_path", None)
    settings.pop("logo_original_path", None)
    save_visual_settings(settings)
    for old_file in _saved_logo_files():
        try:
            if old_file.exists():
                old_file.unlink()
        except Exception:
            pass


def get_logo_data_uri(default: str | None = None) -> str:
    path = get_logo_path(default)
    if not path:
        return ""
    try:
        mime = mimetypes.guess_type(path)[0] or "image/png"
        encoded = base64.b64encode(Path(path).read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""
