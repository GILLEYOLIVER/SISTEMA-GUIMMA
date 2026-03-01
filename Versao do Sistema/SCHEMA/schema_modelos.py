"""Schema do módulo de modelos.
Preencha este arquivo com a estrutura real das tabelas cadastro_modelos_*.
"""

from __future__ import annotations

from schema_utils import comentar



def garantir_schema_modelos(conn, schema="opera", versao_atual=0, versao_alvo=1, logger=print):
    comentar(logger, "[modelos] módulo preparado para receber migrações")
    conn.commit()
