CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS opera;
ALTER SCHEMA opera OWNER TO postgres;

ALTER DATABASE "BANCO_OPERA" SET search_path TO opera, public;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'opera_app') THEN
        CREATE ROLE opera_app LOGIN PASSWORD 'opera_app' NOSUPERUSER NOCREATEDB NOCREATEROLE;
    END IF;
END $$;

GRANT CONNECT ON DATABASE "BANCO_OPERA" TO opera_app;
GRANT USAGE, CREATE ON SCHEMA opera TO opera_app;

ALTER DATABASE "BANCO_OPERA" OWNER TO postgres;

CREATE TABLE IF NOT EXISTS opera._schema_info (
    id SERIAL PRIMARY KEY,
    schema_name TEXT DEFAULT 'opera',
    versao TEXT DEFAULT '1.0',
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

INSERT INTO opera._schema_info (schema_name, versao)
SELECT 'opera', '1.0'
WHERE NOT EXISTS (SELECT 1 FROM opera._schema_info);

SELECT current_database() AS banco, current_schema() AS schema_atual;