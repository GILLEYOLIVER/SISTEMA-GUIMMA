"""Schema do módulo de corte e produção.
Preencha este arquivo com as tabelas de corte, envios, retornos e acabamento.
"""

from __future__ import annotations

from schema_utils import comentar



def garantir_schema_corte_producao(conn, schema="opera", versao_atual=0, versao_alvo=1, logger=print):
    comentar(logger, "[corte_producao] módulo preparado para receber migrações")
    conn.commit()
