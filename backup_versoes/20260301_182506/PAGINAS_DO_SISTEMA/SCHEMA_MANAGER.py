# -*- coding: utf-8 -*-
import os
import sys
from contextlib import contextmanager

# Garante que a pasta PAGINAS_DO_SISTEMA está no path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# Usa o módulo REAL de acesso ao banco do sistema
from BANCO_DE_DADOS_PG import get_connection

SCHEMA_NAME = (os.environ.get("OPERA_PG_SCHEMA") or "opera").strip() or "opera"

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


@contextmanager
def conectar():
    """
    Usa a conexão oficial do sistema, respeitando:
    - OPERA_PG_DSN
    - config.json
    - fallback/autodetect do BANCO_DE_DADOS_PG
    """
    conn = get_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _exec(conn, sql: str, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())


def _fetchone(conn, sql: str, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def garantir_schema_base(conn, schema: str = SCHEMA_NAME):
    _exec(conn, f"CREATE SCHEMA IF NOT EXISTS {schema};")

    _exec(conn, f"""
        CREATE TABLE IF NOT EXISTS {schema}.schema_version (
            modulo        VARCHAR(100) PRIMARY KEY,
            versao        INTEGER NOT NULL DEFAULT 0,
            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()


def obter_versao_modulo(conn, modulo: str, schema: str = SCHEMA_NAME) -> int:
    row = _fetchone(
        conn,
        f"SELECT versao FROM {schema}.schema_version WHERE modulo = %s;",
        (modulo,)
    )
    return int(row[0]) if row else 0


def definir_versao_modulo(conn, modulo: str, versao: int, schema: str = SCHEMA_NAME):
    _exec(conn, f"""
        INSERT INTO {schema}.schema_version (modulo, versao, atualizado_em)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (modulo)
        DO UPDATE SET
            versao = EXCLUDED.versao,
            atualizado_em = CURRENT_TIMESTAMP;
    """, (modulo, versao))
    conn.commit()


def _import_callable(module_name: str, func_name: str):
    """
    Importa módulos de schema que estão na mesma pasta PAGINAS_DO_SISTEMA.
    """
    module = __import__(module_name, fromlist=[func_name])
    fn = getattr(module, func_name, None)
    if not callable(fn):
        raise RuntimeError(f"Função {func_name} não encontrada em {module_name}.")
    return fn


def aplicar_migracoes_pendentes(schema: str = SCHEMA_NAME, logger=print):
    with conectar() as conn:
        garantir_schema_base(conn, schema)

        for modulo, module_name, func_name, target_version in MODULES:
            versao_atual = obter_versao_modulo(conn, modulo, schema)

            if versao_atual >= target_version:
                logger(f"[SCHEMA] {modulo}: já está na versão {versao_atual}")
                continue

            logger(f"[SCHEMA] {modulo}: aplicando {versao_atual} -> {target_version}")

            fn = _import_callable(module_name, func_name)

            try:
                fn(
                    conn=conn,
                    schema=schema,
                    versao_atual=versao_atual,
                    versao_alvo=target_version,
                    logger=logger
                )
                definir_versao_modulo(conn, modulo, target_version, schema)
                logger(f"[SCHEMA] {modulo}: OK")
            except Exception:
                conn.rollback()
                raise


def aplicar_migracoes(schema: str = SCHEMA_NAME, logger=print):
    return aplicar_migracoes_pendentes(schema=schema, logger=logger)


def run_pending_migrations(schema: str = SCHEMA_NAME, logger=print):
    return aplicar_migracoes_pendentes(schema=schema, logger=logger)


if __name__ == "__main__":
    aplicar_migracoes_pendentes()