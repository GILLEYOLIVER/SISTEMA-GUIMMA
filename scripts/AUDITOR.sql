DO $$
DECLARE
BEGIN

        -- Garantir tabela opera.usuarios
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'usuarios'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.usuarios';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.usuarios (
    id            SERIAL PRIMARY KEY,
    usuario       VARCHAR(100) NOT NULL UNIQUE,
    senha_hash    TEXT,
    hierarquia    VARCHAR(50) NOT NULL,
    email         VARCHAR(255),
    ativo         BOOLEAN NOT NULL DEFAULT TRUE,
    dica_senha    TEXT,
    telefone      VARCHAR(50),
    departamento  VARCHAR(100),
    ultimo_login  TIMESTAMP
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuarios'
       AND column_name = 'usuario'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuarios.usuario';
    EXECUTE $SQL$ ALTER TABLE opera.usuarios ADD COLUMN usuario       VARCHAR(100) NOT NULL UNIQUE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuarios'
       AND column_name = 'senha_hash'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuarios.senha_hash';
    EXECUTE $SQL$ ALTER TABLE opera.usuarios ADD COLUMN senha_hash    TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuarios'
       AND column_name = 'hierarquia'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuarios.hierarquia';
    EXECUTE $SQL$ ALTER TABLE opera.usuarios ADD COLUMN hierarquia    VARCHAR(50) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuarios'
       AND column_name = 'email'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuarios.email';
    EXECUTE $SQL$ ALTER TABLE opera.usuarios ADD COLUMN email         VARCHAR(255); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuarios'
       AND column_name = 'ativo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuarios.ativo';
    EXECUTE $SQL$ ALTER TABLE opera.usuarios ADD COLUMN ativo         BOOLEAN NOT NULL DEFAULT TRUE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuarios'
       AND column_name = 'dica_senha'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuarios.dica_senha';
    EXECUTE $SQL$ ALTER TABLE opera.usuarios ADD COLUMN dica_senha    TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuarios'
       AND column_name = 'telefone'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuarios.telefone';
    EXECUTE $SQL$ ALTER TABLE opera.usuarios ADD COLUMN telefone      VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuarios'
       AND column_name = 'departamento'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuarios.departamento';
    EXECUTE $SQL$ ALTER TABLE opera.usuarios ADD COLUMN departamento  VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuarios'
       AND column_name = 'ultimo_login'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuarios.ultimo_login';
    EXECUTE $SQL$ ALTER TABLE opera.usuarios ADD COLUMN ultimo_login  TIMESTAMP; $SQL$;
END IF;

        -- Garantir tabela opera.usuario_permissoes
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'usuario_permissoes'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.usuario_permissoes';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.usuario_permissoes (
    usuario_id     INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    codigo         VARCHAR(100) NOT NULL,
    pode_ver       BOOLEAN DEFAULT FALSE,
    pode_editar    BOOLEAN DEFAULT FALSE,
    pode_imprimir  BOOLEAN DEFAULT FALSE,
    excluir        BOOLEAN DEFAULT FALSE,
    administrar    BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (usuario_id, codigo)
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_permissoes'
       AND column_name = 'usuario_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_permissoes.usuario_id';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_permissoes ADD COLUMN usuario_id     INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_permissoes'
       AND column_name = 'codigo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_permissoes.codigo';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_permissoes ADD COLUMN codigo         VARCHAR(100) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_permissoes'
       AND column_name = 'pode_ver'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_permissoes.pode_ver';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_permissoes ADD COLUMN pode_ver       BOOLEAN DEFAULT FALSE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_permissoes'
       AND column_name = 'pode_editar'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_permissoes.pode_editar';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_permissoes ADD COLUMN pode_editar    BOOLEAN DEFAULT FALSE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_permissoes'
       AND column_name = 'pode_imprimir'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_permissoes.pode_imprimir';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_permissoes ADD COLUMN pode_imprimir  BOOLEAN DEFAULT FALSE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_permissoes'
       AND column_name = 'excluir'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_permissoes.excluir';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_permissoes ADD COLUMN excluir        BOOLEAN DEFAULT FALSE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_permissoes'
       AND column_name = 'administrar'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_permissoes.administrar';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_permissoes ADD COLUMN administrar    BOOLEAN DEFAULT FALSE; $SQL$;
END IF;

        -- Garantir tabela opera.usuario_logs
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'usuario_logs'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.usuario_logs';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.usuario_logs (
    id         SERIAL PRIMARY KEY,
    data_hora  TIMESTAMP NOT NULL DEFAULT NOW(),
    usuario    VARCHAR(100) NOT NULL,
    acao       TEXT,
    pagina     TEXT,
    detalhe    TEXT
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_logs'
       AND column_name = 'data_hora'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_logs.data_hora';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_logs ADD COLUMN data_hora  TIMESTAMP NOT NULL DEFAULT NOW(); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_logs'
       AND column_name = 'usuario'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_logs.usuario';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_logs ADD COLUMN usuario    VARCHAR(100) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_logs'
       AND column_name = 'acao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_logs.acao';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_logs ADD COLUMN acao       TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_logs'
       AND column_name = 'pagina'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_logs.pagina';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_logs ADD COLUMN pagina     TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_logs'
       AND column_name = 'detalhe'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_logs.detalhe';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_logs ADD COLUMN detalhe    TEXT; $SQL$;
END IF;

        -- Garantir tabela opera.usuario_preferencias
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'usuario_preferencias'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.usuario_preferencias';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.usuario_preferencias (
    usuario_id    INTEGER PRIMARY KEY REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    tema_nome     VARCHAR(100),
    custom_json   JSONB,
    atualizado_em TIMESTAMP NOT NULL DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_preferencias'
       AND column_name = 'usuario_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_preferencias.usuario_id';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_preferencias ADD COLUMN usuario_id    INTEGER PRIMARY KEY REFERENCES opera.usuarios(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_preferencias'
       AND column_name = 'tema_nome'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_preferencias.tema_nome';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_preferencias ADD COLUMN tema_nome     VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_preferencias'
       AND column_name = 'custom_json'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_preferencias.custom_json';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_preferencias ADD COLUMN custom_json   JSONB; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'usuario_preferencias'
       AND column_name = 'atualizado_em'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.usuario_preferencias.atualizado_em';
    EXECUTE $SQL$ ALTER TABLE opera.usuario_preferencias ADD COLUMN atualizado_em TIMESTAMP NOT NULL DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.cadastro_modelos_cabecalho
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'cadastro_modelos_cabecalho'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.cadastro_modelos_cabecalho';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_cabecalho (
    id              SERIAL PRIMARY KEY,
    codigo          VARCHAR(100) NOT NULL UNIQUE,
    descricao       TEXT,
    colecao         VARCHAR(100),
    tamanho_base    VARCHAR(10),
    dificuldade     VARCHAR(50),
    modelista       VARCHAR(100),
    pilotista       VARCHAR(100),
    custo_total     NUMERIC(12,2) DEFAULT 0,
    pronto_producao BOOLEAN DEFAULT FALSE,
    grade_disponivel TEXT,
    data_criacao    TIMESTAMP DEFAULT NOW(),
    data_atualizacao TIMESTAMP DEFAULT NOW(),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'codigo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.codigo';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN codigo          VARCHAR(100) NOT NULL UNIQUE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN descricao       TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'colecao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.colecao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN colecao         VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'tamanho_base'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.tamanho_base';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN tamanho_base    VARCHAR(10); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'dificuldade'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.dificuldade';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN dificuldade     VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'modelista'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.modelista';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN modelista       VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'pilotista'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.pilotista';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN pilotista       VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'custo_total'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.custo_total';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN custo_total     NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'pronto_producao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.pronto_producao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN pronto_producao BOOLEAN DEFAULT FALSE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'grade_disponivel'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.grade_disponivel';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN grade_disponivel TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'data_criacao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.data_criacao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN data_criacao    TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'data_atualizacao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.data_atualizacao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN data_atualizacao TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'created_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.created_at';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN created_at      TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_cabecalho'
       AND column_name = 'updated_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_cabecalho.updated_at';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_cabecalho ADD COLUMN updated_at      TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.cadastro_modelos_tecidos
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'cadastro_modelos_tecidos'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.cadastro_modelos_tecidos';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_tecidos (
    id              SERIAL PRIMARY KEY,
    codigo_modelo   VARCHAR(100) NOT NULL,
    cadastro_id     INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo_tecido   VARCHAR(100),
    descricao       TEXT,
    cor             VARCHAR(50),
    fornecedor      VARCHAR(100),
    composicao      VARCHAR(100),
    metros_peca     NUMERIC(12,4) DEFAULT 0,
    valor_metro     NUMERIC(12,2) DEFAULT 0,
    valor_total     NUMERIC(12,2) DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_tecidos'
       AND column_name = 'codigo_modelo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_tecidos.codigo_modelo';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_tecidos ADD COLUMN codigo_modelo   VARCHAR(100) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_tecidos'
       AND column_name = 'cadastro_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_tecidos.cadastro_id';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_tecidos ADD COLUMN cadastro_id     INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_tecidos'
       AND column_name = 'codigo_tecido'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_tecidos.codigo_tecido';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_tecidos ADD COLUMN codigo_tecido   VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_tecidos'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_tecidos.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_tecidos ADD COLUMN descricao       TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_tecidos'
       AND column_name = 'cor'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_tecidos.cor';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_tecidos ADD COLUMN cor             VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_tecidos'
       AND column_name = 'fornecedor'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_tecidos.fornecedor';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_tecidos ADD COLUMN fornecedor      VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_tecidos'
       AND column_name = 'composicao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_tecidos.composicao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_tecidos ADD COLUMN composicao      VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_tecidos'
       AND column_name = 'metros_peca'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_tecidos.metros_peca';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_tecidos ADD COLUMN metros_peca     NUMERIC(12,4) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_tecidos'
       AND column_name = 'valor_metro'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_tecidos.valor_metro';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_tecidos ADD COLUMN valor_metro     NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_tecidos'
       AND column_name = 'valor_total'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_tecidos.valor_total';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_tecidos ADD COLUMN valor_total     NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_tecidos'
       AND column_name = 'created_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_tecidos.created_at';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_tecidos ADD COLUMN created_at      TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.cadastro_modelos_aviamentos
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'cadastro_modelos_aviamentos'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.cadastro_modelos_aviamentos';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_aviamentos (
    id              SERIAL PRIMARY KEY,
    codigo_modelo   VARCHAR(100) NOT NULL,
    cadastro_id     INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo_aviamento VARCHAR(100),
    descricao       TEXT,
    cor             VARCHAR(50),
    fornecedor      VARCHAR(100),
    quantidade      NUMERIC(12,4) DEFAULT 0,
    valor_unidade   NUMERIC(12,2) DEFAULT 0,
    valor_total     NUMERIC(12,2) DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_aviamentos'
       AND column_name = 'codigo_modelo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_aviamentos.codigo_modelo';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_aviamentos ADD COLUMN codigo_modelo   VARCHAR(100) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_aviamentos'
       AND column_name = 'cadastro_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_aviamentos.cadastro_id';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_aviamentos ADD COLUMN cadastro_id     INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_aviamentos'
       AND column_name = 'codigo_aviamento'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_aviamentos.codigo_aviamento';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_aviamentos ADD COLUMN codigo_aviamento VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_aviamentos'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_aviamentos.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_aviamentos ADD COLUMN descricao       TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_aviamentos'
       AND column_name = 'cor'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_aviamentos.cor';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_aviamentos ADD COLUMN cor             VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_aviamentos'
       AND column_name = 'fornecedor'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_aviamentos.fornecedor';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_aviamentos ADD COLUMN fornecedor      VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_aviamentos'
       AND column_name = 'quantidade'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_aviamentos.quantidade';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_aviamentos ADD COLUMN quantidade      NUMERIC(12,4) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_aviamentos'
       AND column_name = 'valor_unidade'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_aviamentos.valor_unidade';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_aviamentos ADD COLUMN valor_unidade   NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_aviamentos'
       AND column_name = 'valor_total'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_aviamentos.valor_total';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_aviamentos ADD COLUMN valor_total     NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_aviamentos'
       AND column_name = 'created_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_aviamentos.created_at';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_aviamentos ADD COLUMN created_at      TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.cadastro_modelos_outros_servicos
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'cadastro_modelos_outros_servicos'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.cadastro_modelos_outros_servicos';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_outros_servicos (
    id              SERIAL PRIMARY KEY,
    codigo_modelo   VARCHAR(100) NOT NULL,
    cadastro_id     INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo_servico  VARCHAR(100),
    descricao       TEXT,
    tipo_servico    VARCHAR(100),
    fornecedor      VARCHAR(100),
    unidade         VARCHAR(20),
    quantidade      NUMERIC(12,4) DEFAULT 0,
    valor_unidade   NUMERIC(12,2) DEFAULT 0,
    valor_total     NUMERIC(12,2) DEFAULT 0,
    observacoes     TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'codigo_modelo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.codigo_modelo';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN codigo_modelo   VARCHAR(100) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'cadastro_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.cadastro_id';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN cadastro_id     INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'codigo_servico'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.codigo_servico';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN codigo_servico  VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN descricao       TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'tipo_servico'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.tipo_servico';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN tipo_servico    VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'fornecedor'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.fornecedor';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN fornecedor      VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'unidade'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.unidade';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN unidade         VARCHAR(20); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'quantidade'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.quantidade';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN quantidade      NUMERIC(12,4) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'valor_unidade'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.valor_unidade';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN valor_unidade   NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'valor_total'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.valor_total';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN valor_total     NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'observacoes'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.observacoes';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN observacoes     TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros_servicos'
       AND column_name = 'created_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros_servicos.created_at';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros_servicos ADD COLUMN created_at      TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.cadastro_modelos_outros
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'cadastro_modelos_outros'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.cadastro_modelos_outros';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_outros (
    id              SERIAL PRIMARY KEY,
    codigo_modelo   VARCHAR(100) NOT NULL,
    cadastro_id     INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo          VARCHAR(100),
    descricao       TEXT,
    cor             VARCHAR(50),
    fornecedor      VARCHAR(100),
    unidade         VARCHAR(20),
    quantidade      NUMERIC(12,4) DEFAULT 0,
    preco           NUMERIC(12,2) DEFAULT 0,
    total           NUMERIC(12,2) DEFAULT 0,
    observacoes     TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'codigo_modelo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.codigo_modelo';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN codigo_modelo   VARCHAR(100) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'cadastro_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.cadastro_id';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN cadastro_id     INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'codigo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.codigo';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN codigo          VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN descricao       TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'cor'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.cor';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN cor             VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'fornecedor'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.fornecedor';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN fornecedor      VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'unidade'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.unidade';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN unidade         VARCHAR(20); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'quantidade'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.quantidade';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN quantidade      NUMERIC(12,4) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'preco'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.preco';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN preco           NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'total'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.total';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN total           NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'observacoes'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.observacoes';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN observacoes     TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_outros'
       AND column_name = 'created_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_outros.created_at';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_outros ADD COLUMN created_at      TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.cadastro_modelos_imagens
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'cadastro_modelos_imagens'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.cadastro_modelos_imagens';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_imagens (
    id              SERIAL PRIMARY KEY,
    codigo_modelo   VARCHAR(100) NOT NULL,
    cadastro_id     INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    tipo_imagem     VARCHAR(20), -- 'frente', 'costas', 'tecido', 'aviamento', 'outro'
    caminho_imagem  TEXT,
    descricao       TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_imagens'
       AND column_name = 'codigo_modelo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_imagens.codigo_modelo';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_imagens ADD COLUMN codigo_modelo   VARCHAR(100) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_imagens'
       AND column_name = 'cadastro_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_imagens.cadastro_id';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_imagens ADD COLUMN cadastro_id     INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_imagens'
       AND column_name = 'tipo_imagem'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_imagens.tipo_imagem';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_imagens ADD COLUMN tipo_imagem     VARCHAR(20); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_imagens'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_imagens.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_imagens ADD COLUMN descricao       TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_modelos_imagens'
       AND column_name = 'created_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_modelos_imagens.created_at';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_modelos_imagens ADD COLUMN created_at      TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.cadastro_faccoes
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'cadastro_faccoes'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.cadastro_faccoes';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.cadastro_faccoes (
    codigo            VARCHAR(10) PRIMARY KEY,
    nome              VARCHAR(200) NOT NULL,
    telefone          VARCHAR(50),
    endereco          TEXT,
    titular_da_conta  VARCHAR(200),
    cpf               VARCHAR(20),
    banco             VARCHAR(50),
    agencia           VARCHAR(20),
    conta             VARCHAR(30),
    pix               VARCHAR(100),
    data              DATE,
    data_atualizacao  DATE
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'codigo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.codigo';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN codigo            VARCHAR(10) PRIMARY KEY; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'nome'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.nome';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN nome              VARCHAR(200) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'telefone'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.telefone';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN telefone          VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'endereco'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.endereco';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN endereco          TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'titular_da_conta'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.titular_da_conta';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN titular_da_conta  VARCHAR(200); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'cpf'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.cpf';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN cpf               VARCHAR(20); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'banco'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.banco';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN banco             VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'agencia'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.agencia';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN agencia           VARCHAR(20); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'conta'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.conta';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN conta             VARCHAR(30); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'pix'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.pix';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN pix               VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'data'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.data';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN data              DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_faccoes'
       AND column_name = 'data_atualizacao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_faccoes.data_atualizacao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_faccoes ADD COLUMN data_atualizacao  DATE; $SQL$;
END IF;

        -- Garantir tabela opera.adiantamento_faccao
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'adiantamento_faccao'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.adiantamento_faccao';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.adiantamento_faccao (
    id              SERIAL PRIMARY KEY,
    corte_id        INTEGER,
    codigo_modelo   VARCHAR(100),
    faccao          VARCHAR(200),
    valor           NUMERIC(12,2) NOT NULL,
    forma_pagamento VARCHAR(50),
    parcelas        INTEGER DEFAULT 1,
    data_hora       TIMESTAMP NOT NULL DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'adiantamento_faccao'
       AND column_name = 'corte_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.adiantamento_faccao.corte_id';
    EXECUTE $SQL$ ALTER TABLE opera.adiantamento_faccao ADD COLUMN corte_id        INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'adiantamento_faccao'
       AND column_name = 'codigo_modelo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.adiantamento_faccao.codigo_modelo';
    EXECUTE $SQL$ ALTER TABLE opera.adiantamento_faccao ADD COLUMN codigo_modelo   VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'adiantamento_faccao'
       AND column_name = 'faccao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.adiantamento_faccao.faccao';
    EXECUTE $SQL$ ALTER TABLE opera.adiantamento_faccao ADD COLUMN faccao          VARCHAR(200); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'adiantamento_faccao'
       AND column_name = 'valor'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.adiantamento_faccao.valor';
    EXECUTE $SQL$ ALTER TABLE opera.adiantamento_faccao ADD COLUMN valor           NUMERIC(12,2) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'adiantamento_faccao'
       AND column_name = 'forma_pagamento'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.adiantamento_faccao.forma_pagamento';
    EXECUTE $SQL$ ALTER TABLE opera.adiantamento_faccao ADD COLUMN forma_pagamento VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'adiantamento_faccao'
       AND column_name = 'parcelas'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.adiantamento_faccao.parcelas';
    EXECUTE $SQL$ ALTER TABLE opera.adiantamento_faccao ADD COLUMN parcelas        INTEGER DEFAULT 1; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'adiantamento_faccao'
       AND column_name = 'data_hora'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.adiantamento_faccao.data_hora';
    EXECUTE $SQL$ ALTER TABLE opera.adiantamento_faccao ADD COLUMN data_hora       TIMESTAMP NOT NULL DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.pricing_profiles
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'pricing_profiles'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.pricing_profiles';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.pricing_profiles (
    nome           VARCHAR(100) PRIMARY KEY,
    impostos       NUMERIC(12,4),
    comissao       NUMERIC(12,4),
    cartao         NUMERIC(12,4),
    margem         NUMERIC(12,4),
    perdas         NUMERIC(12,4),
    defeito        NUMERIC(12,4),
    fixos          NUMERIC(12,2),
    capacidade     NUMERIC(12,2),
    variaveis      NUMERIC(12,2),
    frete          NUMERIC(12,2),
    arredondamento VARCHAR(20),
    canal          VARCHAR(100),
    created_at     TIMESTAMP DEFAULT NOW(),
    updated_at     TIMESTAMP DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'nome'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.nome';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN nome           VARCHAR(100) PRIMARY KEY; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'impostos'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.impostos';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN impostos       NUMERIC(12,4); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'comissao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.comissao';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN comissao       NUMERIC(12,4); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'cartao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.cartao';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN cartao         NUMERIC(12,4); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'margem'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.margem';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN margem         NUMERIC(12,4); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'perdas'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.perdas';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN perdas         NUMERIC(12,4); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'defeito'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.defeito';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN defeito        NUMERIC(12,4); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'fixos'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.fixos';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN fixos          NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'capacidade'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.capacidade';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN capacidade     NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'variaveis'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.variaveis';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN variaveis      NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'frete'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.frete';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN frete          NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'arredondamento'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.arredondamento';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN arredondamento VARCHAR(20); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'canal'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.canal';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN canal          VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'created_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.created_at';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN created_at     TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pricing_profiles'
       AND column_name = 'updated_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pricing_profiles.updated_at';
    EXECUTE $SQL$ ALTER TABLE opera.pricing_profiles ADD COLUMN updated_at     TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.cadastro_de_corte
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'cadastro_de_corte'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.cadastro_de_corte';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte (
    id                   SERIAL PRIMARY KEY,
    numero_ordem         VARCHAR(50),
    ordem_corte          VARCHAR(50),
    codigo               VARCHAR(100),
    descricao            TEXT,
    data                 DATE,
    comprimento_matriz   NUMERIC(12,3),
    largura_matriz       NUMERIC(12,3),
    cortador             VARCHAR(100),
    ajudante             VARCHAR(100),
    total_folhas         INTEGER,
    metros_utilizados    NUMERIC(12,3),
    bobinas_utilizadas   NUMERIC(12,3),
    composicao_tecido    VARCHAR(100),
    total_pecas          INTEGER,
    rendimento           NUMERIC(12,4),
    observacoes          TEXT,
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'numero_ordem'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.numero_ordem';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN numero_ordem         VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'ordem_corte'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.ordem_corte';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN ordem_corte          VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'codigo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.codigo';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN codigo               VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN descricao            TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'data'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.data';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN data                 DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'comprimento_matriz'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.comprimento_matriz';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN comprimento_matriz   NUMERIC(12,3); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'largura_matriz'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.largura_matriz';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN largura_matriz       NUMERIC(12,3); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'cortador'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.cortador';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN cortador             VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'ajudante'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.ajudante';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN ajudante             VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'total_folhas'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.total_folhas';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN total_folhas         INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'metros_utilizados'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.metros_utilizados';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN metros_utilizados    NUMERIC(12,3); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'bobinas_utilizadas'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.bobinas_utilizadas';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN bobinas_utilizadas   NUMERIC(12,3); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'composicao_tecido'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.composicao_tecido';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN composicao_tecido    VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'total_pecas'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.total_pecas';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN total_pecas          INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'rendimento'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.rendimento';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN rendimento           NUMERIC(12,4); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'observacoes'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.observacoes';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN observacoes          TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'created_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.created_at';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN created_at           TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte'
       AND column_name = 'updated_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte.updated_at';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte ADD COLUMN updated_at           TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.cadastro_de_corte_tecidos
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'cadastro_de_corte_tecidos'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.cadastro_de_corte_tecidos';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte_tecidos (
    id            SERIAL PRIMARY KEY,
    cadastro_id   INTEGER NOT NULL REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE,
    tecido        VARCHAR(200),
    cor           VARCHAR(50),
    composicao    VARCHAR(100),
    bobinas       NUMERIC(12,3),
    folhas        NUMERIC(12,3),
    pp            INTEGER,
    p             INTEGER,
    m             INTEGER,
    g             INTEGER,
    gg            INTEGER,
    g1            INTEGER,
    g2            INTEGER,
    g3            INTEGER,
    total_pecas   INTEGER
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'cadastro_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.cadastro_id';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN cadastro_id   INTEGER NOT NULL REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'tecido'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.tecido';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN tecido        VARCHAR(200); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'cor'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.cor';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN cor           VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'composicao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.composicao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN composicao    VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'bobinas'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.bobinas';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN bobinas       NUMERIC(12,3); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'folhas'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.folhas';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN folhas        NUMERIC(12,3); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'pp'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.pp';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN pp            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'p'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.p';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN p             INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'm'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.m';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN m             INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'g'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.g';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN g             INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'gg'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.gg';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN gg            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'g1'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.g1';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN g1            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'g2'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.g2';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN g2            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'g3'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.g3';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN g3            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_tecidos'
       AND column_name = 'total_pecas'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_tecidos.total_pecas';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_tecidos ADD COLUMN total_pecas   INTEGER; $SQL$;
END IF;

        -- Garantir tabela opera.cadastro_de_corte_lotes
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'cadastro_de_corte_lotes'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.cadastro_de_corte_lotes';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte_lotes (
    id            SERIAL PRIMARY KEY,
    cadastro_id   INTEGER NOT NULL REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE,
    lote          VARCHAR(100),
    tecido        VARCHAR(200),
    cor           VARCHAR(50),
    composicao    VARCHAR(100),
    bobinas       NUMERIC(12,3),
    folhas        NUMERIC(12,3),
    pp            INTEGER,
    p             INTEGER,
    m             INTEGER,
    g             INTEGER,
    gg            INTEGER,
    g1            INTEGER,
    g2            INTEGER,
    g3            INTEGER,
    total_lote    INTEGER
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'cadastro_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.cadastro_id';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN cadastro_id   INTEGER NOT NULL REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'lote'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.lote';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN lote          VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'tecido'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.tecido';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN tecido        VARCHAR(200); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'cor'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.cor';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN cor           VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'composicao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.composicao';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN composicao    VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'bobinas'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.bobinas';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN bobinas       NUMERIC(12,3); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'folhas'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.folhas';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN folhas        NUMERIC(12,3); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'pp'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.pp';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN pp            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'p'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.p';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN p             INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'm'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.m';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN m             INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'g'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.g';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN g             INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'gg'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.gg';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN gg            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'g1'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.g1';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN g1            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'g2'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.g2';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN g2            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'g3'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.g3';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN g3            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cadastro_de_corte_lotes'
       AND column_name = 'total_lote'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cadastro_de_corte_lotes.total_lote';
    EXECUTE $SQL$ ALTER TABLE opera.cadastro_de_corte_lotes ADD COLUMN total_lote    INTEGER; $SQL$;
END IF;

        -- Garantir tabela opera.ordem_corte_ficha
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'ordem_corte_ficha'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.ordem_corte_ficha';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.ordem_corte_ficha (
    id                 SERIAL PRIMARY KEY,
    codigo_modelo      VARCHAR(100),
    descricao_modelo   TEXT,
    cortador           VARCHAR(100),
    auxiliar           VARCHAR(100),
    data_final         DATE,
    dias_estimados     INTEGER,
    porcentagens       JSONB,
    consumo_peca       NUMERIC(12,4),
    quantidade_desejada INTEGER,
    total_pecas        INTEGER,
    data_registro      TIMESTAMP DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ordem_corte_ficha'
       AND column_name = 'codigo_modelo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ordem_corte_ficha.codigo_modelo';
    EXECUTE $SQL$ ALTER TABLE opera.ordem_corte_ficha ADD COLUMN codigo_modelo      VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ordem_corte_ficha'
       AND column_name = 'descricao_modelo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ordem_corte_ficha.descricao_modelo';
    EXECUTE $SQL$ ALTER TABLE opera.ordem_corte_ficha ADD COLUMN descricao_modelo   TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ordem_corte_ficha'
       AND column_name = 'cortador'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ordem_corte_ficha.cortador';
    EXECUTE $SQL$ ALTER TABLE opera.ordem_corte_ficha ADD COLUMN cortador           VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ordem_corte_ficha'
       AND column_name = 'auxiliar'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ordem_corte_ficha.auxiliar';
    EXECUTE $SQL$ ALTER TABLE opera.ordem_corte_ficha ADD COLUMN auxiliar           VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ordem_corte_ficha'
       AND column_name = 'data_final'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ordem_corte_ficha.data_final';
    EXECUTE $SQL$ ALTER TABLE opera.ordem_corte_ficha ADD COLUMN data_final         DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ordem_corte_ficha'
       AND column_name = 'dias_estimados'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ordem_corte_ficha.dias_estimados';
    EXECUTE $SQL$ ALTER TABLE opera.ordem_corte_ficha ADD COLUMN dias_estimados     INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ordem_corte_ficha'
       AND column_name = 'porcentagens'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ordem_corte_ficha.porcentagens';
    EXECUTE $SQL$ ALTER TABLE opera.ordem_corte_ficha ADD COLUMN porcentagens       JSONB; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ordem_corte_ficha'
       AND column_name = 'consumo_peca'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ordem_corte_ficha.consumo_peca';
    EXECUTE $SQL$ ALTER TABLE opera.ordem_corte_ficha ADD COLUMN consumo_peca       NUMERIC(12,4); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ordem_corte_ficha'
       AND column_name = 'quantidade_desejada'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ordem_corte_ficha.quantidade_desejada';
    EXECUTE $SQL$ ALTER TABLE opera.ordem_corte_ficha ADD COLUMN quantidade_desejada INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ordem_corte_ficha'
       AND column_name = 'total_pecas'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ordem_corte_ficha.total_pecas';
    EXECUTE $SQL$ ALTER TABLE opera.ordem_corte_ficha ADD COLUMN total_pecas        INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ordem_corte_ficha'
       AND column_name = 'data_registro'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ordem_corte_ficha.data_registro';
    EXECUTE $SQL$ ALTER TABLE opera.ordem_corte_ficha ADD COLUMN data_registro      TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.envios_cortes
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'envios_cortes'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.envios_cortes';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.envios_cortes (
    id             SERIAL PRIMARY KEY,
    data_envio     DATE,
    prestador_id   INTEGER,
    tipo_servico   VARCHAR(100),
    corte_id       INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,
    qtd_pp         INTEGER DEFAULT 0,
    qtd_p          INTEGER DEFAULT 0,
    qtd_m          INTEGER DEFAULT 0,
    qtd_g          INTEGER DEFAULT 0,
    qtd_gg         INTEGER DEFAULT 0,
    qtd_g1         INTEGER DEFAULT 0,
    qtd_g2         INTEGER DEFAULT 0,
    qtd_g3         INTEGER DEFAULT 0,
    valor_pp       NUMERIC(12,2) DEFAULT 0,
    valor_p        NUMERIC(12,2) DEFAULT 0,
    valor_m        NUMERIC(12,2) DEFAULT 0,
    valor_g        NUMERIC(12,2) DEFAULT 0,
    valor_gg       NUMERIC(12,2) DEFAULT 0,
    valor_g1       NUMERIC(12,2) DEFAULT 0,
    valor_g2       NUMERIC(12,2) DEFAULT 0,
    valor_g3       NUMERIC(12,2) DEFAULT 0,
    observacoes    TEXT,
    previsao_entrega DATE
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'data_envio'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.data_envio';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN data_envio     DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'prestador_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.prestador_id';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN prestador_id   INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'tipo_servico'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.tipo_servico';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN tipo_servico   VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'corte_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.corte_id';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN corte_id       INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'qtd_pp'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.qtd_pp';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN qtd_pp         INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'qtd_p'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.qtd_p';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN qtd_p          INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'qtd_m'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.qtd_m';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN qtd_m          INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'qtd_g'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.qtd_g';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN qtd_g          INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'qtd_gg'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.qtd_gg';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN qtd_gg         INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'qtd_g1'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.qtd_g1';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN qtd_g1         INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'qtd_g2'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.qtd_g2';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN qtd_g2         INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'qtd_g3'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.qtd_g3';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN qtd_g3         INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'valor_pp'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.valor_pp';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN valor_pp       NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'valor_p'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.valor_p';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN valor_p        NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'valor_m'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.valor_m';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN valor_m        NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'valor_g'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.valor_g';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN valor_g        NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'valor_gg'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.valor_gg';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN valor_gg       NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'valor_g1'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.valor_g1';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN valor_g1       NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'valor_g2'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.valor_g2';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN valor_g2       NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'valor_g3'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.valor_g3';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN valor_g3       NUMERIC(12,2) DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'observacoes'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.observacoes';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN observacoes    TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envios_cortes'
       AND column_name = 'previsao_entrega'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envios_cortes.previsao_entrega';
    EXECUTE $SQL$ ALTER TABLE opera.envios_cortes ADD COLUMN previsao_entrega DATE; $SQL$;
END IF;

        -- Garantir tabela opera.controle_envio_cortes
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'controle_envio_cortes'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.controle_envio_cortes';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.controle_envio_cortes (
    id                SERIAL PRIMARY KEY,
    data_envio        DATE,
    servico           VARCHAR(100),
    corte_id          INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,
    codigo_corte      VARCHAR(100),
    descricao_corte   TEXT,
    destino           VARCHAR(200),
    costureira        VARCHAR(200),
    faccao            VARCHAR(200),
    quantidade_total  INTEGER,
    valor_peca        NUMERIC(12,2),
    valor_total       NUMERIC(12,2),
    status            VARCHAR(50),
    observacao        TEXT,
    pp                INTEGER,
    p                 INTEGER,
    m                 INTEGER,
    g                 INTEGER,
    gg                INTEGER,
    g1                INTEGER,
    g2                INTEGER,
    g3                INTEGER
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'data_envio'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.data_envio';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN data_envio        DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'servico'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.servico';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN servico           VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'corte_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.corte_id';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN corte_id          INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'codigo_corte'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.codigo_corte';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN codigo_corte      VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'descricao_corte'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.descricao_corte';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN descricao_corte   TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'destino'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.destino';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN destino           VARCHAR(200); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'costureira'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.costureira';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN costureira        VARCHAR(200); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'faccao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.faccao';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN faccao            VARCHAR(200); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'quantidade_total'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.quantidade_total';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN quantidade_total  INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'valor_peca'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.valor_peca';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN valor_peca        NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'valor_total'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.valor_total';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN valor_total       NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'status'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.status';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN status            VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'observacao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.observacao';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN observacao        TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'pp'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.pp';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN pp                INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'p'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.p';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN p                 INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'm'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.m';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN m                 INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'g'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.g';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN g                 INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'gg'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.gg';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN gg                INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'g1'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.g1';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN g1                INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'g2'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.g2';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN g2                INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_envio_cortes'
       AND column_name = 'g3'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_envio_cortes.g3';
    EXECUTE $SQL$ ALTER TABLE opera.controle_envio_cortes ADD COLUMN g3                INTEGER; $SQL$;
END IF;

        -- Garantir tabela opera.entrada_acabamento
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'entrada_acabamento'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.entrada_acabamento';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.entrada_acabamento (
    id                  SERIAL PRIMARY KEY,
    envio_id            INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    data_chegada        DATE,
    total_entregue      INTEGER,
    total_defeitos      INTEGER,
    total_faltantes     INTEGER,
    total_regulares     INTEGER,
    valor_total         NUMERIC(12,2),
    pago                BOOLEAN DEFAULT FALSE,
    data_pagamento      DATE
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'entrada_acabamento'
       AND column_name = 'envio_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.entrada_acabamento.envio_id';
    EXECUTE $SQL$ ALTER TABLE opera.entrada_acabamento ADD COLUMN envio_id            INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'entrada_acabamento'
       AND column_name = 'data_chegada'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.entrada_acabamento.data_chegada';
    EXECUTE $SQL$ ALTER TABLE opera.entrada_acabamento ADD COLUMN data_chegada        DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'entrada_acabamento'
       AND column_name = 'total_entregue'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.entrada_acabamento.total_entregue';
    EXECUTE $SQL$ ALTER TABLE opera.entrada_acabamento ADD COLUMN total_entregue      INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'entrada_acabamento'
       AND column_name = 'total_defeitos'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.entrada_acabamento.total_defeitos';
    EXECUTE $SQL$ ALTER TABLE opera.entrada_acabamento ADD COLUMN total_defeitos      INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'entrada_acabamento'
       AND column_name = 'total_faltantes'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.entrada_acabamento.total_faltantes';
    EXECUTE $SQL$ ALTER TABLE opera.entrada_acabamento ADD COLUMN total_faltantes     INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'entrada_acabamento'
       AND column_name = 'total_regulares'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.entrada_acabamento.total_regulares';
    EXECUTE $SQL$ ALTER TABLE opera.entrada_acabamento ADD COLUMN total_regulares     INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'entrada_acabamento'
       AND column_name = 'valor_total'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.entrada_acabamento.valor_total';
    EXECUTE $SQL$ ALTER TABLE opera.entrada_acabamento ADD COLUMN valor_total         NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'entrada_acabamento'
       AND column_name = 'pago'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.entrada_acabamento.pago';
    EXECUTE $SQL$ ALTER TABLE opera.entrada_acabamento ADD COLUMN pago                BOOLEAN DEFAULT FALSE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'entrada_acabamento'
       AND column_name = 'data_pagamento'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.entrada_acabamento.data_pagamento';
    EXECUTE $SQL$ ALTER TABLE opera.entrada_acabamento ADD COLUMN data_pagamento      DATE; $SQL$;
END IF;

        -- Garantir tabela opera.controle_retorno_cortes
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'controle_retorno_cortes'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.controle_retorno_cortes';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.controle_retorno_cortes (
    id                   SERIAL PRIMARY KEY,
    envio_id             INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    data_chegada         DATE,
    total_entregue       INTEGER,
    total_defeitos       INTEGER,
    total_faltantes      INTEGER,
    total_regulares      INTEGER,
    valor_total          NUMERIC(12,2)
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_retorno_cortes'
       AND column_name = 'envio_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_retorno_cortes.envio_id';
    EXECUTE $SQL$ ALTER TABLE opera.controle_retorno_cortes ADD COLUMN envio_id             INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_retorno_cortes'
       AND column_name = 'data_chegada'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_retorno_cortes.data_chegada';
    EXECUTE $SQL$ ALTER TABLE opera.controle_retorno_cortes ADD COLUMN data_chegada         DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_retorno_cortes'
       AND column_name = 'total_entregue'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_retorno_cortes.total_entregue';
    EXECUTE $SQL$ ALTER TABLE opera.controle_retorno_cortes ADD COLUMN total_entregue       INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_retorno_cortes'
       AND column_name = 'total_defeitos'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_retorno_cortes.total_defeitos';
    EXECUTE $SQL$ ALTER TABLE opera.controle_retorno_cortes ADD COLUMN total_defeitos       INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_retorno_cortes'
       AND column_name = 'total_faltantes'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_retorno_cortes.total_faltantes';
    EXECUTE $SQL$ ALTER TABLE opera.controle_retorno_cortes ADD COLUMN total_faltantes      INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_retorno_cortes'
       AND column_name = 'total_regulares'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_retorno_cortes.total_regulares';
    EXECUTE $SQL$ ALTER TABLE opera.controle_retorno_cortes ADD COLUMN total_regulares      INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'controle_retorno_cortes'
       AND column_name = 'valor_total'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.controle_retorno_cortes.valor_total';
    EXECUTE $SQL$ ALTER TABLE opera.controle_retorno_cortes ADD COLUMN valor_total          NUMERIC(12,2); $SQL$;
END IF;

        -- Garantir tabela opera.cortes_finalizados
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'cortes_finalizados'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.cortes_finalizados';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.cortes_finalizados (
    id               SERIAL PRIMARY KEY,
    corte_id         INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,
    codigo           VARCHAR(100),
    descricao        TEXT,
    costureira       VARCHAR(200),
    data_envio       DATE,
    data_chegada     DATE,
    qtd_enviada      INTEGER,
    status           VARCHAR(50),
    valor_peca       NUMERIC(12,2),
    pago             BOOLEAN DEFAULT FALSE,
    data_pagamento   DATE
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cortes_finalizados'
       AND column_name = 'corte_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cortes_finalizados.corte_id';
    EXECUTE $SQL$ ALTER TABLE opera.cortes_finalizados ADD COLUMN corte_id         INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cortes_finalizados'
       AND column_name = 'codigo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cortes_finalizados.codigo';
    EXECUTE $SQL$ ALTER TABLE opera.cortes_finalizados ADD COLUMN codigo           VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cortes_finalizados'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cortes_finalizados.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.cortes_finalizados ADD COLUMN descricao        TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cortes_finalizados'
       AND column_name = 'costureira'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cortes_finalizados.costureira';
    EXECUTE $SQL$ ALTER TABLE opera.cortes_finalizados ADD COLUMN costureira       VARCHAR(200); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cortes_finalizados'
       AND column_name = 'data_envio'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cortes_finalizados.data_envio';
    EXECUTE $SQL$ ALTER TABLE opera.cortes_finalizados ADD COLUMN data_envio       DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cortes_finalizados'
       AND column_name = 'data_chegada'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cortes_finalizados.data_chegada';
    EXECUTE $SQL$ ALTER TABLE opera.cortes_finalizados ADD COLUMN data_chegada     DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cortes_finalizados'
       AND column_name = 'qtd_enviada'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cortes_finalizados.qtd_enviada';
    EXECUTE $SQL$ ALTER TABLE opera.cortes_finalizados ADD COLUMN qtd_enviada      INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cortes_finalizados'
       AND column_name = 'status'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cortes_finalizados.status';
    EXECUTE $SQL$ ALTER TABLE opera.cortes_finalizados ADD COLUMN status           VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cortes_finalizados'
       AND column_name = 'valor_peca'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cortes_finalizados.valor_peca';
    EXECUTE $SQL$ ALTER TABLE opera.cortes_finalizados ADD COLUMN valor_peca       NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cortes_finalizados'
       AND column_name = 'pago'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cortes_finalizados.pago';
    EXECUTE $SQL$ ALTER TABLE opera.cortes_finalizados ADD COLUMN pago             BOOLEAN DEFAULT FALSE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'cortes_finalizados'
       AND column_name = 'data_pagamento'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.cortes_finalizados.data_pagamento';
    EXECUTE $SQL$ ALTER TABLE opera.cortes_finalizados ADD COLUMN data_pagamento   DATE; $SQL$;
END IF;

        -- Garantir tabela opera.pagamento_corte_acabamento
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'pagamento_corte_acabamento'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.pagamento_corte_acabamento';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.pagamento_corte_acabamento (
    id                     SERIAL PRIMARY KEY,
    tipo_servico           VARCHAR(100),
    codigo                 VARCHAR(100),
    descricao              TEXT,
    costureira             VARCHAR(200),
    data_envio             DATE,
    data_chegada           DATE,
    quantidade_finalizada  INTEGER,
    valor_por_peca         NUMERIC(12,2),
    total_pago             NUMERIC(12,2),
    data_pagamento         TIMESTAMP
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pagamento_corte_acabamento'
       AND column_name = 'tipo_servico'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pagamento_corte_acabamento.tipo_servico';
    EXECUTE $SQL$ ALTER TABLE opera.pagamento_corte_acabamento ADD COLUMN tipo_servico           VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pagamento_corte_acabamento'
       AND column_name = 'codigo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pagamento_corte_acabamento.codigo';
    EXECUTE $SQL$ ALTER TABLE opera.pagamento_corte_acabamento ADD COLUMN codigo                 VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pagamento_corte_acabamento'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pagamento_corte_acabamento.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.pagamento_corte_acabamento ADD COLUMN descricao              TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pagamento_corte_acabamento'
       AND column_name = 'costureira'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pagamento_corte_acabamento.costureira';
    EXECUTE $SQL$ ALTER TABLE opera.pagamento_corte_acabamento ADD COLUMN costureira             VARCHAR(200); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pagamento_corte_acabamento'
       AND column_name = 'data_envio'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pagamento_corte_acabamento.data_envio';
    EXECUTE $SQL$ ALTER TABLE opera.pagamento_corte_acabamento ADD COLUMN data_envio             DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pagamento_corte_acabamento'
       AND column_name = 'data_chegada'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pagamento_corte_acabamento.data_chegada';
    EXECUTE $SQL$ ALTER TABLE opera.pagamento_corte_acabamento ADD COLUMN data_chegada           DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pagamento_corte_acabamento'
       AND column_name = 'quantidade_finalizada'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pagamento_corte_acabamento.quantidade_finalizada';
    EXECUTE $SQL$ ALTER TABLE opera.pagamento_corte_acabamento ADD COLUMN quantidade_finalizada  INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pagamento_corte_acabamento'
       AND column_name = 'valor_por_peca'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pagamento_corte_acabamento.valor_por_peca';
    EXECUTE $SQL$ ALTER TABLE opera.pagamento_corte_acabamento ADD COLUMN valor_por_peca         NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pagamento_corte_acabamento'
       AND column_name = 'total_pago'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pagamento_corte_acabamento.total_pago';
    EXECUTE $SQL$ ALTER TABLE opera.pagamento_corte_acabamento ADD COLUMN total_pago             NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pagamento_corte_acabamento'
       AND column_name = 'data_pagamento'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pagamento_corte_acabamento.data_pagamento';
    EXECUTE $SQL$ ALTER TABLE opera.pagamento_corte_acabamento ADD COLUMN data_pagamento         TIMESTAMP; $SQL$;
END IF;

        -- Garantir tabela opera.envio_detalhes_tamanho
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'envio_detalhes_tamanho'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.envio_detalhes_tamanho';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.envio_detalhes_tamanho (
    envio_id          INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    tamanho           VARCHAR(10) NOT NULL,
    quantidade_pilotos INTEGER DEFAULT 0,
    PRIMARY KEY (envio_id, tamanho)
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envio_detalhes_tamanho'
       AND column_name = 'envio_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envio_detalhes_tamanho.envio_id';
    EXECUTE $SQL$ ALTER TABLE opera.envio_detalhes_tamanho ADD COLUMN envio_id          INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envio_detalhes_tamanho'
       AND column_name = 'tamanho'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envio_detalhes_tamanho.tamanho';
    EXECUTE $SQL$ ALTER TABLE opera.envio_detalhes_tamanho ADD COLUMN tamanho           VARCHAR(10) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'envio_detalhes_tamanho'
       AND column_name = 'quantidade_pilotos'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.envio_detalhes_tamanho.quantidade_pilotos';
    EXECUTE $SQL$ ALTER TABLE opera.envio_detalhes_tamanho ADD COLUMN quantidade_pilotos INTEGER DEFAULT 0; $SQL$;
END IF;

        -- Garantir tabela opera.retorno_detalhes_tamanho
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'retorno_detalhes_tamanho'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.retorno_detalhes_tamanho';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.retorno_detalhes_tamanho (
    id                SERIAL PRIMARY KEY,
    retorno_id        INTEGER REFERENCES opera.controle_retorno_cortes(id) ON DELETE CASCADE,
    envio_id          INTEGER REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    tamanho           VARCHAR(10) NOT NULL,
    quantidade_entregue INTEGER DEFAULT 0,
    quantidade_copias INTEGER DEFAULT 0,
    quantidade_defeito INTEGER DEFAULT 0,
    quantidade_faltante INTEGER DEFAULT 0,
    regulares         INTEGER DEFAULT 0,
    subtotal          NUMERIC(12,2)
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'retorno_detalhes_tamanho'
       AND column_name = 'retorno_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.retorno_detalhes_tamanho.retorno_id';
    EXECUTE $SQL$ ALTER TABLE opera.retorno_detalhes_tamanho ADD COLUMN retorno_id        INTEGER REFERENCES opera.controle_retorno_cortes(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'retorno_detalhes_tamanho'
       AND column_name = 'envio_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.retorno_detalhes_tamanho.envio_id';
    EXECUTE $SQL$ ALTER TABLE opera.retorno_detalhes_tamanho ADD COLUMN envio_id          INTEGER REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'retorno_detalhes_tamanho'
       AND column_name = 'tamanho'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.retorno_detalhes_tamanho.tamanho';
    EXECUTE $SQL$ ALTER TABLE opera.retorno_detalhes_tamanho ADD COLUMN tamanho           VARCHAR(10) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'retorno_detalhes_tamanho'
       AND column_name = 'quantidade_entregue'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.retorno_detalhes_tamanho.quantidade_entregue';
    EXECUTE $SQL$ ALTER TABLE opera.retorno_detalhes_tamanho ADD COLUMN quantidade_entregue INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'retorno_detalhes_tamanho'
       AND column_name = 'quantidade_copias'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.retorno_detalhes_tamanho.quantidade_copias';
    EXECUTE $SQL$ ALTER TABLE opera.retorno_detalhes_tamanho ADD COLUMN quantidade_copias INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'retorno_detalhes_tamanho'
       AND column_name = 'quantidade_defeito'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.retorno_detalhes_tamanho.quantidade_defeito';
    EXECUTE $SQL$ ALTER TABLE opera.retorno_detalhes_tamanho ADD COLUMN quantidade_defeito INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'retorno_detalhes_tamanho'
       AND column_name = 'quantidade_faltante'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.retorno_detalhes_tamanho.quantidade_faltante';
    EXECUTE $SQL$ ALTER TABLE opera.retorno_detalhes_tamanho ADD COLUMN quantidade_faltante INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'retorno_detalhes_tamanho'
       AND column_name = 'regulares'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.retorno_detalhes_tamanho.regulares';
    EXECUTE $SQL$ ALTER TABLE opera.retorno_detalhes_tamanho ADD COLUMN regulares         INTEGER DEFAULT 0; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'retorno_detalhes_tamanho'
       AND column_name = 'subtotal'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.retorno_detalhes_tamanho.subtotal';
    EXECUTE $SQL$ ALTER TABLE opera.retorno_detalhes_tamanho ADD COLUMN subtotal          NUMERIC(12,2); $SQL$;
END IF;

        -- Garantir tabela opera.ficha_tecnica_cabecalho
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'ficha_tecnica_cabecalho'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.ficha_tecnica_cabecalho';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.ficha_tecnica_cabecalho (
    id              SERIAL PRIMARY KEY,
    codigo          VARCHAR(100) NOT NULL UNIQUE,
    descricao       TEXT,
    colecao         VARCHAR(100),
    tamanho_base    VARCHAR(10),
    dificuldade     VARCHAR(50),
    modelista       VARCHAR(100),
    pilotista       VARCHAR(100),
    custo           NUMERIC(12,2),
    pronto_producao BOOLEAN DEFAULT FALSE,
    grade_disponivel TEXT,
    data_criacao    DATE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'codigo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.codigo';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN codigo          VARCHAR(100) NOT NULL UNIQUE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN descricao       TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'colecao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.colecao';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN colecao         VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'tamanho_base'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.tamanho_base';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN tamanho_base    VARCHAR(10); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'dificuldade'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.dificuldade';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN dificuldade     VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'modelista'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.modelista';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN modelista       VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'pilotista'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.pilotista';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN pilotista       VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'custo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.custo';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN custo           NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'pronto_producao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.pronto_producao';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN pronto_producao BOOLEAN DEFAULT FALSE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'grade_disponivel'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.grade_disponivel';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN grade_disponivel TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'data_criacao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.data_criacao';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN data_criacao    DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'created_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.created_at';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN created_at      TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'ficha_tecnica_cabecalho'
       AND column_name = 'updated_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.ficha_tecnica_cabecalho.updated_at';
    EXECUTE $SQL$ ALTER TABLE opera.ficha_tecnica_cabecalho ADD COLUMN updated_at      TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.servicos
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'servicos'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.servicos';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.servicos (
    id           SERIAL PRIMARY KEY,
    nome         VARCHAR(200) NOT NULL,
    descricao    TEXT,
    prestador    VARCHAR(200),
    data_inicio  DATE,
    data_fim     DATE,
    valor_unitario NUMERIC(12,2),
    quantidade   INTEGER,
    valor_total  NUMERIC(12,2),
    status       VARCHAR(50),
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'servicos'
       AND column_name = 'nome'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.servicos.nome';
    EXECUTE $SQL$ ALTER TABLE opera.servicos ADD COLUMN nome         VARCHAR(200) NOT NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'servicos'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.servicos.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.servicos ADD COLUMN descricao    TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'servicos'
       AND column_name = 'prestador'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.servicos.prestador';
    EXECUTE $SQL$ ALTER TABLE opera.servicos ADD COLUMN prestador    VARCHAR(200); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'servicos'
       AND column_name = 'data_inicio'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.servicos.data_inicio';
    EXECUTE $SQL$ ALTER TABLE opera.servicos ADD COLUMN data_inicio  DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'servicos'
       AND column_name = 'data_fim'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.servicos.data_fim';
    EXECUTE $SQL$ ALTER TABLE opera.servicos ADD COLUMN data_fim     DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'servicos'
       AND column_name = 'valor_unitario'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.servicos.valor_unitario';
    EXECUTE $SQL$ ALTER TABLE opera.servicos ADD COLUMN valor_unitario NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'servicos'
       AND column_name = 'quantidade'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.servicos.quantidade';
    EXECUTE $SQL$ ALTER TABLE opera.servicos ADD COLUMN quantidade   INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'servicos'
       AND column_name = 'valor_total'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.servicos.valor_total';
    EXECUTE $SQL$ ALTER TABLE opera.servicos ADD COLUMN valor_total  NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'servicos'
       AND column_name = 'status'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.servicos.status';
    EXECUTE $SQL$ ALTER TABLE opera.servicos ADD COLUMN status       VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'servicos'
       AND column_name = 'created_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.servicos.created_at';
    EXECUTE $SQL$ ALTER TABLE opera.servicos ADD COLUMN created_at   TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'servicos'
       AND column_name = 'updated_at'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.servicos.updated_at';
    EXECUTE $SQL$ ALTER TABLE opera.servicos ADD COLUMN updated_at   TIMESTAMP DEFAULT NOW(); $SQL$;
END IF;

        -- Garantir tabela opera.historico_servicos
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'historico_servicos'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.historico_servicos';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.historico_servicos (
    id            SERIAL PRIMARY KEY,
    servico_id    INTEGER REFERENCES opera.servicos(id) ON DELETE CASCADE,
    data_evento   TIMESTAMP NOT NULL DEFAULT NOW(),
    acao          VARCHAR(100),
    observacoes   TEXT
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'historico_servicos'
       AND column_name = 'servico_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.historico_servicos.servico_id';
    EXECUTE $SQL$ ALTER TABLE opera.historico_servicos ADD COLUMN servico_id    INTEGER REFERENCES opera.servicos(id) ON DELETE CASCADE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'historico_servicos'
       AND column_name = 'data_evento'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.historico_servicos.data_evento';
    EXECUTE $SQL$ ALTER TABLE opera.historico_servicos ADD COLUMN data_evento   TIMESTAMP NOT NULL DEFAULT NOW(); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'historico_servicos'
       AND column_name = 'acao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.historico_servicos.acao';
    EXECUTE $SQL$ ALTER TABLE opera.historico_servicos ADD COLUMN acao          VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'historico_servicos'
       AND column_name = 'observacoes'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.historico_servicos.observacoes';
    EXECUTE $SQL$ ALTER TABLE opera.historico_servicos ADD COLUMN observacoes   TEXT; $SQL$;
END IF;

        -- Garantir tabela opera.pecas_finalizadas
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'opera' AND table_name = 'pecas_finalizadas'
        ) THEN
            RAISE NOTICE 'Criando tabela ausente: opera.pecas_finalizadas';
            EXECUTE $SQL$CREATE TABLE IF NOT EXISTS opera.pecas_finalizadas (
    id               SERIAL PRIMARY KEY,
    corte_id         INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,
    entrada_id       INTEGER UNIQUE,
    codigo           VARCHAR(100),
    descricao        TEXT,
    costureira       VARCHAR(200),
    data_envio       DATE,
    data_chegada     DATE,
    qtd_enviada      INTEGER,
    observacao       TEXT,
    status           VARCHAR(50),
    data_conferencia TIMESTAMP,
    valor_peca       NUMERIC(12,2),
    bonificacao      NUMERIC(12,2),
    qtd_pp           INTEGER,
    qtd_p            INTEGER,
    qtd_m            INTEGER,
    qtd_g            INTEGER,
    qtd_gg           INTEGER,
    qtd_g1           INTEGER,
    qtd_g2           INTEGER,
    qtd_g3           INTEGER,
    qtd_defeito_pp   INTEGER,
    qtd_defeito_p    INTEGER,
    qtd_defeito_m    INTEGER,
    qtd_defeito_g    INTEGER,
    qtd_defeito_gg   INTEGER,
    qtd_defeito_g1   INTEGER,
    qtd_defeito_g2   INTEGER,
    qtd_defeito_g3   INTEGER,
    pago             BOOLEAN DEFAULT FALSE,
    pagamento_id     INTEGER,
    valor_pago       NUMERIC(12,2),
    data_pagamento   DATE
);$SQL$;
        END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'corte_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.corte_id';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN corte_id         INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'entrada_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.entrada_id';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN entrada_id       INTEGER UNIQUE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'codigo'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.codigo';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN codigo           VARCHAR(100); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'descricao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.descricao';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN descricao        TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'costureira'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.costureira';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN costureira       VARCHAR(200); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'data_envio'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.data_envio';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN data_envio       DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'data_chegada'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.data_chegada';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN data_chegada     DATE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_enviada'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_enviada';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_enviada      INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'observacao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.observacao';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN observacao       TEXT; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'status'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.status';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN status           VARCHAR(50); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'data_conferencia'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.data_conferencia';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN data_conferencia TIMESTAMP; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'valor_peca'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.valor_peca';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN valor_peca       NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'bonificacao'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.bonificacao';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN bonificacao      NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_pp'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_pp';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_pp           INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_p'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_p';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_p            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_m'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_m';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_m            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_g'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_g';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_g            INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_gg'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_gg';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_gg           INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_g1'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_g1';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_g1           INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_g2'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_g2';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_g2           INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_g3'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_g3';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_g3           INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_defeito_pp'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_defeito_pp';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_defeito_pp   INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_defeito_p'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_defeito_p';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_defeito_p    INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_defeito_m'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_defeito_m';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_defeito_m    INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_defeito_g'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_defeito_g';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_defeito_g    INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_defeito_gg'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_defeito_gg';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_defeito_gg   INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_defeito_g1'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_defeito_g1';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_defeito_g1   INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_defeito_g2'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_defeito_g2';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_defeito_g2   INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'qtd_defeito_g3'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.qtd_defeito_g3';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN qtd_defeito_g3   INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'pago'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.pago';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN pago             BOOLEAN DEFAULT FALSE; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'pagamento_id'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.pagamento_id';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN pagamento_id     INTEGER; $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'valor_pago'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.valor_pago';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN valor_pago       NUMERIC(12,2); $SQL$;
END IF;

IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'opera'
       AND table_name  = 'pecas_finalizadas'
       AND column_name = 'data_pagamento'
) THEN
    RAISE NOTICE 'Adicionando coluna ausente: opera.pecas_finalizadas.data_pagamento';
    EXECUTE $SQL$ ALTER TABLE opera.pecas_finalizadas ADD COLUMN data_pagamento   DATE; $SQL$;
END IF;
END $$;