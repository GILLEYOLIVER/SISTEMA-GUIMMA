"""Schema do módulo de clientes e compras."""

from __future__ import annotations

from schema_utils import comentar



def garantir_schema_clientes_compras(conn, schema="opera", versao_atual=0, versao_alvo=1, logger=print):
    comentar(logger, "[clientes_compras] módulo preparado para receber migrações")
    conn.commit()
