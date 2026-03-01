"""Schema do módulo de estoque."""

from __future__ import annotations

from schema_utils import comentar



def garantir_schema_estoque(conn, schema="opera", versao_atual=0, versao_alvo=1, logger=print):
    comentar(logger, "[estoque] módulo preparado para receber migrações")
    conn.commit()
