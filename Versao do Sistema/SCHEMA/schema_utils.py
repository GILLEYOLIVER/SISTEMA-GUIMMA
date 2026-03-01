"""Utilitários para migrações e garantia de schema do OPERA."""

from __future__ import annotations


def _exec(conn, sql: str, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())


def tabela_existe(conn, schema: str, tabela: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name = %s
            LIMIT 1;
            """,
            (schema, tabela),
        )
        return cur.fetchone() is not None


def coluna_existe(conn, schema: str, tabela: str, coluna: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
              AND column_name = %s
            LIMIT 1;
            """,
            (schema, tabela, coluna),
        )
        return cur.fetchone() is not None


def adicionar_coluna_se_faltar(conn, schema: str, tabela: str, coluna: str, definicao: str):
    if not coluna_existe(conn, schema, tabela, coluna):
        _exec(conn, f"ALTER TABLE {schema}.{tabela} ADD COLUMN {coluna} {definicao};")


def indice_existe(conn, schema: str, nome_indice: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = %s
              AND indexname = %s
            LIMIT 1;
            """,
            (schema, nome_indice),
        )
        return cur.fetchone() is not None


def criar_indice_se_faltar(conn, schema: str, nome_indice: str, sql_create_index: str):
    if not indice_existe(conn, schema, nome_indice):
        _exec(conn, sql_create_index)


def comentar(logger, msg: str):
    if callable(logger):
        logger(msg)
