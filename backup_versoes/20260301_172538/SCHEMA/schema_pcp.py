"""Schema do módulo de PCP / MRP."""

from __future__ import annotations

from schema_utils import comentar



def garantir_schema_pcp(conn, schema="opera", versao_atual=0, versao_alvo=1, logger=print):
    comentar(logger, "[pcp] módulo preparado para receber migrações")
    conn.commit()
