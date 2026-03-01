"""Schema do módulo de usuários."""

from __future__ import annotations

from schema_utils import _exec, criar_indice_se_faltar, comentar



def garantir_schema_usuarios(conn, schema="opera", versao_atual=0, versao_alvo=1, logger=print):
    comentar(logger, "[usuarios] garantindo tabelas de usuários")

    _exec(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.usuarios (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(150) NOT NULL,
            login VARCHAR(80) NOT NULL,
            senha_hash TEXT,
            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    )

    _exec(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.usuario_preferencias (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES {schema}.usuarios(id) ON DELETE CASCADE,
            chave VARCHAR(100) NOT NULL,
            valor TEXT,
            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    )

    _exec(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.usuario_permissoes (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES {schema}.usuarios(id) ON DELETE CASCADE,
            pagina VARCHAR(100) NOT NULL,
            pode_ver BOOLEAN NOT NULL DEFAULT FALSE,
            pode_editar BOOLEAN NOT NULL DEFAULT FALSE,
            pode_imprimir BOOLEAN NOT NULL DEFAULT FALSE,
            pode_excluir BOOLEAN NOT NULL DEFAULT FALSE,
            pode_administrar BOOLEAN NOT NULL DEFAULT FALSE
        );
        """,
    )

    _exec(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.usuario_logs (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER REFERENCES {schema}.usuarios(id) ON DELETE SET NULL,
            acao TEXT NOT NULL,
            detalhes TEXT,
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    )

    _exec(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS {schema}.usuario_temas_personalizados (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES {schema}.usuarios(id) ON DELETE CASCADE,
            nome_tema VARCHAR(100) NOT NULL,
            configuracao_json TEXT,
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
    )

    criar_indice_se_faltar(
        conn,
        schema,
        "idx_usuarios_login",
        f"CREATE UNIQUE INDEX idx_usuarios_login ON {schema}.usuarios(login);",
    )

    conn.commit()
