"""Gerenciador central de schema do OPERA."""

from __future__ import annotations

import os
from contextlib import contextmanager

try:
    import psycopg2
except ImportError:
    psycopg2 = None


SCHEMA_NAME = os.getenv("OPERA_PG_SCHEMA", "opera")
DEFAULT_DSN = os.getenv(
    "OPERA_PG_DSN",
    "host=localhost port=5432 dbname=BANCO_OPERA user=postgres password=postgres",
)

MODULES = [
    ("core", "schema_core", "garantir_schema_core", 1),
    ("usuarios", "schema_usuarios", "garantir_schema_usuarios", 1),
    ("modelos", "schema_modelos", "garantir_schema_modelos", 1),
    ("faccoes", "schema_faccoes", "garantir_schema_faccoes", 1),
    ("corte_producao", "schema_corte_producao", "garantir_schema_corte_producao", 1),
    ("pagamentos", "schema_pagamentos", "garantir_schema_pagamentos", 1),
    ("servicos", "schema_servicos", "garantir_schema_servicos", 1),
    ("estoque", "schema_estoque", "garantir_schema_estoque", 1),
    ("clientes_compras", "schema_clientes_compras", "garantir_schema_clientes_compras", 1),
    ("pcp", "schema_pcp", "garantir_schema_pcp", 1),
    ("custos", "schema_custos", "garantir_schema_custos", 1),
    ("relatorios", "schema_relatorios", "garantir_schema_relatorios", 1),
]


class SchemaManagerError(RuntimeError):
    pass



def _require_psycopg2():
    if psycopg2 is None:
        raise SchemaManagerError("psycopg2 não está instalado no ambiente.")


@contextmanager
def conectar(dsn: str | None = None):
    _require_psycopg2()
    conn = psycopg2.connect(dsn or DEFAULT_DSN)
    try:
        yield conn
    finally:
        conn.close()



def _exec(conn, sql: str, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())



def _fetchone(conn, sql: str, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()



def garantir_schema_base(conn, schema: str = SCHEMA_NAME):
    _exec(conn, f"CREATE SCHEMA IF NOT EXISTS {schema};")
    _exec(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.schema_version (
            modulo        VARCHAR(100) PRIMARY KEY,
            versao        INTEGER NOT NULL DEFAULT 0,
            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    )
    conn.commit()



def obter_versao_modulo(conn, modulo: str, schema: str = SCHEMA_NAME) -> int:
    row = _fetchone(
        conn,
        f"SELECT versao FROM {schema}.schema_version WHERE modulo = %s;",
        (modulo,),
    )
    return int(row[0]) if row else 0



def definir_versao_modulo(conn, modulo: str, versao: int, schema: str = SCHEMA_NAME):
    _exec(
        conn,
        f"""
        INSERT INTO {schema}.schema_version (modulo, versao, atualizado_em)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (modulo)
        DO UPDATE SET
            versao = EXCLUDED.versao,
            atualizado_em = CURRENT_TIMESTAMP;
        """,
        (modulo, versao),
    )
    conn.commit()



def _import_callable(module_name: str, func_name: str):
    module = __import__(module_name, fromlist=[func_name])
    fn = getattr(module, func_name, None)
    if not callable(fn):
        raise SchemaManagerError(f"Função {func_name} não encontrada em {module_name}.")
    return fn



def aplicar_migracoes_pendentes(dsn: str | None = None, schema: str = SCHEMA_NAME, logger=print):
    with conectar(dsn) as conn:
        garantir_schema_base(conn, schema)

        for modulo, module_name, func_name, target_version in MODULES:
            versao_atual = obter_versao_modulo(conn, modulo, schema)

            if versao_atual >= target_version:
                if callable(logger):
                    logger(f"[SCHEMA] {modulo}: já está na versão {versao_atual}")
                continue

            if callable(logger):
                logger(f"[SCHEMA] {modulo}: aplicando {versao_atual} -> {target_version}")

            fn = _import_callable(module_name, func_name)

            try:
                fn(conn=conn, schema=schema, versao_atual=versao_atual, versao_alvo=target_version, logger=logger)
                definir_versao_modulo(conn, modulo, target_version, schema)
                if callable(logger):
                    logger(f"[SCHEMA] {modulo}: OK")
            except Exception:
                conn.rollback()
                raise



def aplicar_migracoes(dsn: str | None = None, schema: str = SCHEMA_NAME, logger=print):
    return aplicar_migracoes_pendentes(dsn=dsn, schema=schema, logger=logger)



def run_pending_migrations(dsn: str | None = None, schema: str = SCHEMA_NAME, logger=print):
    return aplicar_migracoes_pendentes(dsn=dsn, schema=schema, logger=logger)


if __name__ == "__main__":
    aplicar_migracoes_pendentes()
