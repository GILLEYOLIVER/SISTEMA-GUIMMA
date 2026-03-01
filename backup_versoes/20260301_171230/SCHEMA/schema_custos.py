"""Schema do módulo de custos."""

from __future__ import annotations

from schema_utils import comentar



def garantir_schema_custos(conn, schema="opera", versao_atual=0, versao_alvo=1, logger=print):
    comentar(logger, "[custos] módulo preparado para receber migrações")
    conn.commit()
