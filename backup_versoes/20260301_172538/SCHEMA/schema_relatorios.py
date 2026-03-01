"""Schema do módulo de relatórios e pricing."""

from __future__ import annotations

from schema_utils import comentar



def garantir_schema_relatorios(conn, schema="opera", versao_atual=0, versao_alvo=1, logger=print):
    comentar(logger, "[relatorios] módulo preparado para receber migrações")
    conn.commit()
