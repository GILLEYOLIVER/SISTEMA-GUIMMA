"""Schema base do sistema OPERA."""

from __future__ import annotations

from schema_utils import _exec, comentar



def garantir_schema_core(conn, schema="opera", versao_atual=0, versao_alvo=1, logger=print):
    comentar(logger, "[core] garantindo tabelas-base")

    _exec(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}._schema_info (
            chave        VARCHAR(100) PRIMARY KEY,
            valor        TEXT,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
    )

    conn.commit()
