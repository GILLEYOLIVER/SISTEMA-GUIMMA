"""Schema do módulo de facções."""

from __future__ import annotations

from schema_utils import _exec, adicionar_coluna_se_faltar, criar_indice_se_faltar, comentar



def garantir_schema_faccoes(conn, schema="opera", versao_atual=0, versao_alvo=1, logger=print):
    comentar(logger, "[faccoes] garantindo cadastro de facções")

    _exec(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.cadastro_faccoes (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(30),
            nome VARCHAR(150) NOT NULL,
            responsavel VARCHAR(150),
            telefone VARCHAR(30),
            cidade VARCHAR(100),
            uf VARCHAR(2),
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    )

    # Exemplo de evolução futura de schema: se faltar, adiciona sem quebrar banco antigo.
    adicionar_coluna_se_faltar(conn, schema, "cadastro_faccoes", "telefone_secundario", "VARCHAR(30)")
    adicionar_coluna_se_faltar(conn, schema, "cadastro_faccoes", "observacoes", "TEXT")

    criar_indice_se_faltar(
        conn,
        schema,
        "idx_cadastro_faccoes_nome",
        f"CREATE INDEX idx_cadastro_faccoes_nome ON {schema}.cadastro_faccoes(nome);",
    )

    criar_indice_se_faltar(
        conn,
        schema,
        "idx_cadastro_faccoes_codigo",
        f"CREATE INDEX idx_cadastro_faccoes_codigo ON {schema}.cadastro_faccoes(codigo);",
    )

    conn.commit()
