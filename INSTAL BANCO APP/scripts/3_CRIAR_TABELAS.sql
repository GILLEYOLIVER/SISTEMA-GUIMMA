-- ================================================================
-- [TABELA 01] USUÁRIOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.usuarios (
    id             SERIAL PRIMARY KEY,
    usuario        VARCHAR(100) NOT NULL UNIQUE,
    senha_hash     TEXT,
    hierarquia     VARCHAR(50) NOT NULL,
    email          VARCHAR(255),
    data_criacao   TIMESTAMP DEFAULT NOW(),
    ativo          BOOLEAN NOT NULL DEFAULT TRUE,
    dica_senha     TEXT,
    ultimo_login   TIMESTAMP,
    telefone       VARCHAR(50),
    departamento   VARCHAR(100),
    tema_preferido VARCHAR(50) DEFAULT 'Noite Urbana'
);

ALTER TABLE opera.usuarios
    ADD COLUMN IF NOT EXISTS senha_hash     TEXT,
    ADD COLUMN IF NOT EXISTS hierarquia     VARCHAR(50),
    ADD COLUMN IF NOT EXISTS email          VARCHAR(255),
    ADD COLUMN IF NOT EXISTS data_criacao   TIMESTAMP DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS ativo          BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS dica_senha     TEXT,
    ADD COLUMN IF NOT EXISTS ultimo_login   TIMESTAMP,
    ADD COLUMN IF NOT EXISTS telefone       VARCHAR(50),
    ADD COLUMN IF NOT EXISTS departamento   VARCHAR(100),
    ADD COLUMN IF NOT EXISTS tema_preferido VARCHAR(50) DEFAULT 'Noite Urbana';

CREATE INDEX IF NOT EXISTS idx_usuarios_hierarquia ON opera.usuarios (hierarquia);
CREATE INDEX IF NOT EXISTS idx_usuarios_ativo      ON opera.usuarios (ativo);

COMMENT ON TABLE opera.usuarios IS
'TABELA 01 - Registro dos usuários do sistema OPERA.';

-- ================================================================
-- [TABELA 02] USUÁRIO – PREFERÊNCIAS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.usuario_preferencias (
    usuario_id               INTEGER PRIMARY KEY REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    tema_nome                VARCHAR(50) DEFAULT 'Noite Urbana',
    usar_tema_personalizado  BOOLEAN DEFAULT FALSE,
    tema_personalizado       TEXT,
    layout_compacto          BOOLEAN DEFAULT FALSE,
    sidebar_recolhida        BOOLEAN DEFAULT FALSE,
    usar_animacoes           BOOLEAN DEFAULT TRUE,
    mostrar_dicas            BOOLEAN DEFAULT TRUE,
    idioma                   VARCHAR(20) DEFAULT 'pt-BR',
    notificacoes             BOOLEAN DEFAULT TRUE,
    atualizado_em            TIMESTAMP DEFAULT NOW()
);

ALTER TABLE opera.usuario_preferencias
    ADD COLUMN IF NOT EXISTS tema_nome               VARCHAR(50) DEFAULT 'Noite Urbana',
    ADD COLUMN IF NOT EXISTS usar_tema_personalizado BOOLEAN     DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS tema_personalizado      TEXT,
    ADD COLUMN IF NOT EXISTS layout_compacto         BOOLEAN     DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS sidebar_recolhida       BOOLEAN     DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS usar_animacoes          BOOLEAN     DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS mostrar_dicas           BOOLEAN     DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS idioma                  VARCHAR(20) DEFAULT 'pt-BR',
    ADD COLUMN IF NOT EXISTS notificacoes            BOOLEAN     DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS atualizado_em           TIMESTAMP   DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_usuario_preferencias_tema
    ON opera.usuario_preferencias (tema_nome);

COMMENT ON TABLE opera.usuario_preferencias IS
'TABELA 02 - Preferências gerais do usuário.';

-- ================================================================
-- [TABELA 03] TEMAS PERSONALIZADOS DO USUÁRIO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.usuario_temas_personalizados (
    id             SERIAL PRIMARY KEY,
    usuario_id     INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    nome_tema      VARCHAR(100) NOT NULL,
    cores_tema     JSONB NOT NULL,
    data_criacao   TIMESTAMP DEFAULT NOW(),
    atualizado_em  TIMESTAMP DEFAULT NOW(),
    UNIQUE (usuario_id, nome_tema)
);

ALTER TABLE opera.usuario_temas_personalizados
    ADD COLUMN IF NOT EXISTS usuario_id    INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS nome_tema     VARCHAR(100) NOT NULL,
    ADD COLUMN IF NOT EXISTS cores_tema    JSONB       NOT NULL,
    ADD COLUMN IF NOT EXISTS data_criacao  TIMESTAMP   DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP   DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_usuario_temas_usuario
    ON opera.usuario_temas_personalizados (usuario_id);

CREATE INDEX IF NOT EXISTS idx_usuario_temas_nome
    ON opera.usuario_temas_personalizados (nome_tema);

COMMENT ON TABLE opera.usuario_temas_personalizados IS
'TABELA 03 - Temas customizados criados pelos usuários.';

-- ================================================================
-- [TABELA 04] PERMISSÕES DO USUÁRIO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.usuario_permissoes (
    usuario_id        INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    codigo            VARCHAR(100) NOT NULL,
    pode_ver          BOOLEAN DEFAULT FALSE,
    pode_editar       BOOLEAN DEFAULT FALSE,
    pode_imprimir     BOOLEAN DEFAULT FALSE,
    pode_excluir      BOOLEAN DEFAULT FALSE,
    pode_administrar  BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (usuario_id, codigo)
);

ALTER TABLE opera.usuario_permissoes
    ADD COLUMN IF NOT EXISTS pode_ver         BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS pode_editar      BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS pode_imprimir    BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS pode_excluir     BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS pode_administrar BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_usuario_permissoes_codigo
    ON opera.usuario_permissoes (codigo);

COMMENT ON TABLE opera.usuario_permissoes IS
'TABELA 04 - Permissões de acesso às funções do sistema OPERA.';

-- ================================================================
-- [TABELA 05] LOGS DO USUÁRIO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.usuario_logs (
    id          SERIAL PRIMARY KEY,
    usuario_id  INTEGER REFERENCES opera.usuarios(id),
    acao        TEXT,
    detalhes    TEXT,
    data_hora   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usuario_logs_usuario
    ON opera.usuario_logs (usuario_id);

CREATE INDEX IF NOT EXISTS idx_usuario_logs_data_hora
    ON opera.usuario_logs (data_hora);

COMMENT ON TABLE opera.usuario_logs IS
'TABELA 05 - Histórico de ações realizadas pelos usuários.';

-- ================================================================
-- USUÁRIO MESTRE "GIL DE OLIVEIRA"
-- ================================================================
DO $$
DECLARE
    v_user_id INTEGER;
BEGIN
    -- Verifica se o usuário já existe
    SELECT id INTO v_user_id
    FROM opera.usuarios
    WHERE usuario = 'Gil de Oliveira'
    LIMIT 1;

    -- Se não existir, cria
    IF v_user_id IS NULL THEN
        INSERT INTO opera.usuarios
            (usuario, senha_hash, hierarquia, email, dica_senha, tema_preferido)
        VALUES (
            'Gil de Oliveira',
            crypt('2580', gen_salt('bf')),
            'Administrador',
            'opera@gil.com',
            '25',
            'Cinza Oceano Claro'
        )
        RETURNING id INTO v_user_id;

        INSERT INTO opera.usuario_preferencias (usuario_id, tema_nome)
        VALUES (v_user_id, 'Cinza Oceano Claro');
    END IF;

    -- Permissões totais
    INSERT INTO opera.usuario_permissoes
        (usuario_id, codigo, pode_ver, pode_editar, pode_imprimir, pode_excluir, pode_administrar)
    SELECT v_user_id, c.codigo, TRUE, TRUE, TRUE, TRUE, TRUE
    FROM (
        VALUES
            ('dashboard'),
            ('cadastro_modelos'),
            ('cadastro_de_corte'),
            ('controle_envio_cortes'),
            ('controle_retorno_cortes'),
            ('finalizar_corte'),
            ('estoque_tecidos'),
            ('estoque_aviamentos'),
            ('estoque_insumos'),
            ('sistema_admin'),
            ('sistema_logs'),
            ('sistema_backup'),
            ('sistema_auditoria')
    ) AS c(codigo)
    ON CONFLICT (usuario_id, codigo) DO NOTHING;

    RAISE NOTICE 'Usuario mestre garantido: %', v_user_id;
END $$;

-- ================================================================
-- [TABELA 06] CADASTRO DE MODELOS (CABEÇALHO)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_cabecalho (
    id               SERIAL PRIMARY KEY,
    codigo           VARCHAR(100) NOT NULL UNIQUE,
    descricao        TEXT,
    colecao          VARCHAR(100),
    tamanho_base     VARCHAR(10),
    dificuldade      VARCHAR(50),
    modelista        VARCHAR(100),
    pilotista        VARCHAR(100),
    custo_total      NUMERIC(12,2) DEFAULT 0,
    pronto_producao  BOOLEAN DEFAULT FALSE,
    grade_disponivel TEXT,
    data_criacao     TIMESTAMP DEFAULT NOW(),
    data_atualizacao TIMESTAMP DEFAULT NOW(),
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_modelos_codigo
    ON opera.cadastro_modelos_cabecalho (codigo);
CREATE INDEX IF NOT EXISTS idx_modelos_descricao
    ON opera.cadastro_modelos_cabecalho (descricao);

-- ================================================================
-- [TABELA 07] TECIDOS POR MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_tecidos (
    id            SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id   INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo_tecido VARCHAR(100),
    descricao     TEXT,
    cor           VARCHAR(50),
    fornecedor    VARCHAR(100),
    composicao    VARCHAR(100),
    metros_peca   NUMERIC(12,4) DEFAULT 0,
    valor_metro   NUMERIC(12,2) DEFAULT 0,
    valor_total   NUMERIC(12,2) DEFAULT 0,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_modelos_tecidos_cadastro
    ON opera.cadastro_modelos_tecidos (cadastro_id);
CREATE INDEX IF NOT EXISTS idx_modelos_tecidos_codigo
    ON opera.cadastro_modelos_tecidos (codigo_modelo);

-- ================================================================
-- [TABELA 08] AVIAMENTOS POR MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_aviamentos (
    id               SERIAL PRIMARY KEY,
    codigo_modelo    VARCHAR(100) NOT NULL,
    cadastro_id      INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo_aviamento VARCHAR(100),
    descricao        TEXT,
    cor              VARCHAR(50),
    fornecedor       VARCHAR(100),
    quantidade       NUMERIC(12,4) DEFAULT 0,
    valor_unidade    NUMERIC(12,2) DEFAULT 0,
    valor_total      NUMERIC(12,2) DEFAULT 0,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_modelos_aviamentos_cadastro
    ON opera.cadastro_modelos_aviamentos (cadastro_id);
CREATE INDEX IF NOT EXISTS idx_modelos_aviamentos_codigo
    ON opera.cadastro_modelos_aviamentos (codigo_modelo);

-- ================================================================
-- [TABELA 09] OUTROS ITENS POR MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_outros (
    id            SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id   INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo        VARCHAR(100),
    descricao     TEXT,
    cor           VARCHAR(50),
    fornecedor    VARCHAR(100),
    unidade       VARCHAR(20),
    quantidade    NUMERIC(12,4) DEFAULT 0,
    preco         NUMERIC(12,2) DEFAULT 0,
    total         NUMERIC(12,2) DEFAULT 0,
    observacoes   TEXT,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_modelos_outros_cadastro
    ON opera.cadastro_modelos_outros (cadastro_id);
CREATE INDEX IF NOT EXISTS idx_modelos_outros_codigo
    ON opera.cadastro_modelos_outros (codigo_modelo);

-- ================================================================
-- [TABELA 10] IMAGENS DO MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_imagens (
    id            SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id   INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    tipo_imagem   VARCHAR(20),
    caminho_imagem TEXT,
    descricao     TEXT,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_modelos_imagens_cadastro
    ON opera.cadastro_modelos_imagens (cadastro_id);
CREATE INDEX IF NOT EXISTS idx_modelos_imagens_codigo
    ON opera.cadastro_modelos_imagens (codigo_modelo);

-- ================================================================
-- [TABELA 11] GRADE POR MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_grade (
    id         SERIAL PRIMARY KEY,
    modelo_id  INTEGER NOT NULL REFERENCES opera.cadastro_modelos_cabecalho (id) ON DELETE CASCADE,
    tamanho    VARCHAR(10) NOT NULL,
    disponivel BOOLEAN DEFAULT TRUE,
    UNIQUE (modelo_id, tamanho)
);

-- ================================================================
-- [TABELA 12] CADASTRO DE FACÇÕES / PRESTADORES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_faccoes (
    id               SERIAL PRIMARY KEY,
    codigo           VARCHAR(10) UNIQUE NOT NULL,
    nome             VARCHAR(200) NOT NULL,
    tipo_prestador   VARCHAR(50) DEFAULT 'Facção',
    telefone         VARCHAR(50),
    endereco         TEXT,
    titular_da_conta VARCHAR(200),
    cpf              VARCHAR(20),
    banco            VARCHAR(50),
    agencia          VARCHAR(20),
    conta            VARCHAR(30),
    pix              VARCHAR(100),
    data             DATE,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ativo            BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_faccoes_nome
    ON opera.cadastro_faccoes (nome);
CREATE INDEX IF NOT EXISTS idx_faccoes_codigo
    ON opera.cadastro_faccoes (codigo);
CREATE INDEX IF NOT EXISTS idx_faccoes_tipo
    ON opera.cadastro_faccoes (tipo_prestador);
CREATE INDEX IF NOT EXISTS idx_faccoes_ativo
    ON opera.cadastro_faccoes (ativo);

-- ================================================================
-- [TABELA 13] PAGAMENTO DE SERVIÇOS (CABECALHO)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.pagamento_servicos (
    id                        BIGSERIAL PRIMARY KEY,
    prestador_id              INTEGER REFERENCES opera.cadastro_faccoes(id) ON DELETE SET NULL,
    nome_prestador            VARCHAR(100),
    data_pagamento            DATE NOT NULL,
    valor_total               NUMERIC(10, 2) NOT NULL,
    valor_adiantamento_abatido NUMERIC(10, 2) DEFAULT 0.00,
    valor_liquido             NUMERIC(10, 2) NOT NULL,
    mes_referencia            VARCHAR(10),
    observacoes               TEXT,
    usuario_pagamento         VARCHAR(100),
    data_registro             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- [TABELA 14] DETALHE DO PAGAMENTO DE SERVIÇOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.pagamento_servicos_detalhe (
    pagamento_id          BIGINT NOT NULL REFERENCES opera.pagamento_servicos (id) ON DELETE CASCADE,
    entrada_acabamento_id INTEGER NOT NULL,
    valor_servico         NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (pagamento_id, entrada_acabamento_id)
);

-- ================================================================
-- [TABELA 15] ADIANTAMENTOS PARA FACÇÕES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.adiantamento_faccao (
    id              SERIAL PRIMARY KEY,
    corte_id        INTEGER,
    codigo_modelo   VARCHAR(100),
    faccao          VARCHAR(200),
    valor           NUMERIC(12,2) NOT NULL,
    forma_pagamento VARCHAR(50),
    parcelas        INTEGER DEFAULT 1,
    data_hora       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_adiantamento_corte
    ON opera.adiantamento_faccao (corte_id);
CREATE INDEX IF NOT EXISTS idx_adiantamento_faccao
    ON opera.adiantamento_faccao (faccao);

-- ================================================================
-- [TABELA 16] PERFIS DE PRECIFICAÇÃO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.pricing_profiles (
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
);

-- ================================================================
-- [TABELA 17] CADASTRO DE CORTE - CABEÇALHO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte (
    id                 SERIAL PRIMARY KEY,
    numero_ordem       VARCHAR(50),
    ordem_corte        VARCHAR(50),
    codigo             VARCHAR(100),
    descricao          TEXT,
    descricao_corte    TEXT,
    data               DATE,
    data_envio         DATE,
    comprimento_matriz NUMERIC(12,3),
    largura_matriz     NUMERIC(12,3),
    cortador           VARCHAR(100),
    ajudante           VARCHAR(100),
    auxiliar           VARCHAR(100),
    total_folhas       INTEGER,
    metros_utilizados  NUMERIC(12,3),
    bobinas_utilizadas NUMERIC(12,3),
    composicao_tecido  VARCHAR(100),

    pp                 INTEGER NOT NULL DEFAULT 0,
    p                  INTEGER NOT NULL DEFAULT 0,
    m                  INTEGER NOT NULL DEFAULT 0,
    g                  INTEGER NOT NULL DEFAULT 0,
    gg                 INTEGER NOT NULL DEFAULT 0,
    g1                 INTEGER NOT NULL DEFAULT 0,
    g2                 INTEGER NOT NULL DEFAULT 0,
    g3                 INTEGER NOT NULL DEFAULT 0,

    total_pecas        INTEGER NOT NULL DEFAULT 0,
    rendimento         NUMERIC(12,4),
    observacoes        TEXT,
    created_at         TIMESTAMP DEFAULT NOW(),
    updated_at         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cadastro_corte_codigo
    ON opera.cadastro_de_corte (codigo);
CREATE INDEX IF NOT EXISTS idx_cadastro_corte_data
    ON opera.cadastro_de_corte (data);
CREATE INDEX IF NOT EXISTS idx_cadastro_corte_cortador
    ON opera.cadastro_de_corte (cortador);
CREATE INDEX IF NOT EXISTS idx_cadastro_corte_numero_ordem
    ON opera.cadastro_de_corte (numero_ordem);

-- ================================================================
-- [TABELA 18] TECIDOS UTILIZADOS NO CORTE
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte_tecidos (
    id          SERIAL PRIMARY KEY,
    cadastro_id INTEGER NOT NULL REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE,
    tecido      VARCHAR(200),
    cor         VARCHAR(50),
    composicao  VARCHAR(100),
    bobinas     NUMERIC(12,3),
    folhas      NUMERIC(12,3),
    pp          INTEGER,
    p           INTEGER,
    m           INTEGER,
    g           INTEGER,
    gg          INTEGER,
    g1          INTEGER,
    g2          INTEGER,
    g3          INTEGER,
    total_pecas INTEGER
);

CREATE INDEX IF NOT EXISTS idx_corte_tecidos_cadastro
    ON opera.cadastro_de_corte_tecidos (cadastro_id);

-- ================================================================
-- [TABELA 19] LOTES DE CORTE
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte_lotes (
    id          SERIAL PRIMARY KEY,
    cadastro_id INTEGER NOT NULL REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE,
    lote        VARCHAR(100),
    tecido      VARCHAR(200),
    cor         VARCHAR(50),
    composicao  VARCHAR(100),
    bobinas     NUMERIC(12,3),
    folhas      NUMERIC(12,3),
    pp          INTEGER,
    p           INTEGER,
    m           INTEGER,
    g           INTEGER,
    gg          INTEGER,
    g1          INTEGER,
    g2          INTEGER,
    g3          INTEGER,
    total_lote  INTEGER
);

CREATE INDEX IF NOT EXISTS idx_corte_lotes_cadastro
    ON opera.cadastro_de_corte_lotes (cadastro_id);

-- ================================================================
-- [TABELA 20] ORDEM DE CORTE - FICHA
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.ordem_corte_ficha (
    id                  SERIAL PRIMARY KEY,
    codigo_modelo       VARCHAR(100) NOT NULL,
    descricao_modelo    TEXT,
    cortador            VARCHAR(100),
    auxiliar            VARCHAR(100),
    ajudante            VARCHAR(100),
    data_registro       TIMESTAMP DEFAULT NOW(),
    data_final          DATE,
    dias_estimados      NUMERIC(12,4),
    horas_estimadas     NUMERIC(12,4),
    porcentagens        JSONB,
    consumo_peca        NUMERIC(12,4),
    quantidade_desejada INTEGER,
    total_pecas         INTEGER,
    observacoes         TEXT,
    status              VARCHAR(50) DEFAULT 'Em Andamento',
    usuario_registro    VARCHAR(100),
    data_atualizacao    TIMESTAMP DEFAULT NOW(),
    ativo               BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_ordem_corte_codigo_modelo
    ON opera.ordem_corte_ficha (codigo_modelo);
CREATE INDEX IF NOT EXISTS idx_ordem_corte_status
    ON opera.ordem_corte_ficha (status);

-- ================================================================
-- [TABELA 21] ORDEM DE CORTE - LOTES / GRADES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.ordem_corte_lotes (
    id          BIGSERIAL PRIMARY KEY,
    ordem_id    INTEGER NOT NULL REFERENCES opera.ordem_corte_ficha (id) ON DELETE CASCADE,
    lote_numero VARCHAR(50),
    tamanho     VARCHAR(10) NOT NULL,
    quantidade  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (ordem_id, lote_numero, tamanho)
);

-- ================================================================
-- [TABELA 22] ENVIO DE CORTES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.envios_cortes (
    id               SERIAL PRIMARY KEY,
    data_envio       DATE NOT NULL,
    hora_envio       TIME,
    prestador_id     INTEGER REFERENCES opera.cadastro_faccoes(id) ON DELETE RESTRICT,
    tipo_servico     TEXT,
    corte_id         INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE RESTRICT,
    ordem_corte      VARCHAR(50),
    codigo_corte     VARCHAR(100),
    descricao_corte  TEXT,
    colecao          VARCHAR(100),
    material         VARCHAR(100),
    cliente          VARCHAR(200),
    cores            TEXT,
    prioridade       VARCHAR(30),
    forma_pagamento  VARCHAR(50),
    status_envio     VARCHAR(30) DEFAULT 'Enviado',

    qtd_pp           INTEGER DEFAULT 0,
    qtd_p            INTEGER DEFAULT 0,
    qtd_m            INTEGER DEFAULT 0,
    qtd_g            INTEGER DEFAULT 0,
    qtd_gg           INTEGER DEFAULT 0,
    qtd_g1           INTEGER DEFAULT 0,
    qtd_g2           INTEGER DEFAULT 0,
    qtd_g3           INTEGER DEFAULT 0,

    piloto_pp        INTEGER DEFAULT 0,
    piloto_p         INTEGER DEFAULT 0,
    piloto_m         INTEGER DEFAULT 0,
    piloto_g         INTEGER DEFAULT 0,
    piloto_gg        INTEGER DEFAULT 0,
    piloto_g1        INTEGER DEFAULT 0,
    piloto_g2        INTEGER DEFAULT 0,
    piloto_g3        INTEGER DEFAULT 0,

    valor_pp         NUMERIC(10,2) DEFAULT 0,
    valor_p          NUMERIC(10,2) DEFAULT 0,
    valor_m          NUMERIC(10,2) DEFAULT 0,
    valor_g          NUMERIC(10,2) DEFAULT 0,
    valor_gg         NUMERIC(10,2) DEFAULT 0,
    valor_g1         NUMERIC(10,2) DEFAULT 0,
    valor_g2         NUMERIC(10,2) DEFAULT 0,
    valor_g3         NUMERIC(10,2) DEFAULT 0,

    total_pecas         INTEGER       DEFAULT 0,
    total_pilotos       INTEGER       DEFAULT 0,
    valor_total_envio   NUMERIC(12,2) DEFAULT 0,

    resumo_pilotos   TEXT,
    aviamentos       TEXT,
    outros           TEXT,
    observacoes      TEXT,
    tel_encarregado  TEXT,
    tel_acabamento   TEXT,
    previsao_entrega DATE,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_envios_cortes_data
    ON opera.envios_cortes (data_envio);
CREATE INDEX IF NOT EXISTS idx_envios_cortes_prestador
    ON opera.envios_cortes (prestador_id);
CREATE INDEX IF NOT EXISTS idx_envios_cortes_status
    ON opera.envios_cortes (status_envio);

-- ================================================================
-- [TABELA 23] CONTROLE DE ENVIO DE CORTES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.controle_envio_cortes (
    id                SERIAL PRIMARY KEY,
    data_envio        DATE,
    servico           VARCHAR(100),
    corte_id          INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,
    ordem_corte       VARCHAR(50),
    codigo_corte      VARCHAR(100),
    descricao_corte   TEXT,
    destino           VARCHAR(200),
    costureira        VARCHAR(200),
    faccao            VARCHAR(200),
    quantidade_total  INTEGER,
    valor_peca        NUMERIC(12,2),
    valor_total       NUMERIC(12,2),
    status            VARCHAR(50) DEFAULT 'Em Conferência',
    observacao        TEXT,

    pp                INTEGER,
    p                 INTEGER,
    m                 INTEGER,
    g                 INTEGER,
    gg                INTEGER,
    g1                INTEGER,
    g2                INTEGER,
    g3                INTEGER
);

CREATE INDEX IF NOT EXISTS idx_envio_cortes_data_envio
    ON opera.controle_envio_cortes (data_envio);
CREATE INDEX IF NOT EXISTS idx_envio_cortes_status
    ON opera.controle_envio_cortes (status);

-- ================================================================
-- [TABELA 24] ENTRADA DE ACABAMENTO (CABECALHO)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.entrada_acabamento (
    id              SERIAL PRIMARY KEY,
    envio_id        INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    data_chegada    DATE,
    total_entregue  INTEGER,
    total_defeitos  INTEGER,
    total_faltantes INTEGER,
    total_regulares INTEGER,
    valor_total     NUMERIC(12,2),
    pago            BOOLEAN DEFAULT FALSE,
    data_pagamento  DATE
);

-- ================================================================
-- [TABELA 25] HISTÓRICO DE SERVIÇO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.historico_de_servico (
    id           BIGSERIAL PRIMARY KEY,
    envio_id     INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    entrada_id   INTEGER REFERENCES opera.entrada_acabamento(id) ON DELETE SET NULL,
    pagamento_id BIGINT REFERENCES opera.pagamento_servicos(id) ON DELETE SET NULL,
    tipo_servico VARCHAR(50),
    status       VARCHAR(50) DEFAULT 'Em Andamento',
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- [TABELA 26] CONTROLE DE RETORNO DE CORTES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.controle_retorno_cortes (
    id                    SERIAL PRIMARY KEY,
    envio_id              INTEGER NOT NULL
                           REFERENCES opera.envios_cortes(id)
                           ON DELETE CASCADE,

    data_chegada          DATE NOT NULL,

    telefone_encarregado  TEXT,
    telefone_acabamento   TEXT,

    resumo_piloto         TEXT,
    aviamentos_recebidos  TEXT,
    outros_recebidos      TEXT,
    observacoes_gerais    TEXT,

    total_entregue        INTEGER DEFAULT 0,
    total_copias          INTEGER DEFAULT 0,
    total_defeitos        INTEGER DEFAULT 0,
    total_faltantes       INTEGER DEFAULT 0,
    total_regulares       INTEGER DEFAULT 0,
    valor_total           NUMERIC(12,2) DEFAULT 0,

    created_at            TIMESTAMP DEFAULT NOW(),
    updated_at            TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ctrl_retorno_envio
    ON opera.controle_retorno_cortes (envio_id);
CREATE INDEX IF NOT EXISTS idx_ctrl_retorno_data
    ON opera.controle_retorno_cortes (data_chegada);

-- ================================================================
-- [TABELA 27] CORTES FINALIZADOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cortes_finalizados (
    id                    SERIAL PRIMARY KEY,
    corte_id              INTEGER,
    entrada_id            INTEGER,
    codigo                VARCHAR(100),
    descricao             TEXT,
    costureira            VARCHAR(200),
    data_envio            DATE,
    data_chegada          DATE,
    data_final            DATE,
    qtd_enviada           INTEGER,
    total_pecas           INTEGER,
    quantidade_finalizada INTEGER,
    observacao            TEXT,
    status                VARCHAR(50),
    data_conferencia      TIMESTAMP,
    valor_peca            NUMERIC(12,2),
    bonificacao           BOOLEAN DEFAULT FALSE,
    pago                  BOOLEAN DEFAULT FALSE,
    data_pagamento        DATE,

    qtd_pp                INTEGER DEFAULT 0,
    qtd_p                 INTEGER DEFAULT 0,
    qtd_m                 INTEGER DEFAULT 0,
    qtd_g                 INTEGER DEFAULT 0,
    qtd_gg                INTEGER DEFAULT 0,
    qtd_g1                INTEGER DEFAULT 0,
    qtd_g2                INTEGER DEFAULT 0,
    qtd_g3                INTEGER DEFAULT 0,

    qtd_defeito_pp        INTEGER DEFAULT 0,
    qtd_defeito_p         INTEGER DEFAULT 0,
    qtd_defeito_m         INTEGER DEFAULT 0,
    qtd_defeito_g         INTEGER DEFAULT 0,
    qtd_defeito_gg        INTEGER DEFAULT 0,
    qtd_defeito_g1        INTEGER DEFAULT 0,
    qtd_defeito_g2        INTEGER DEFAULT 0,
    qtd_defeito_g3        INTEGER DEFAULT 0,

    created_at            TIMESTAMP DEFAULT NOW(),
    updated_at            TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_corte
    ON opera.cortes_finalizados (corte_id);

-- ================================================================
-- [TABELA 28] PAGAMENTO CORTE / ACABAMENTO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.pagamento_corte_acabamento (
    id                     SERIAL PRIMARY KEY,
    costureira             VARCHAR(200),
    tipo_servico           VARCHAR(100),
    codigo                 VARCHAR(100),
    descricao              TEXT,
    data_envio             DATE,
    data_chegada           DATE,
    quantidade_finalizada  INTEGER,
    valor_por_peca         NUMERIC(12,2),
    adiantamento           NUMERIC(12,2) DEFAULT 0,
    ajuda_custo            NUMERIC(12,2) DEFAULT 0,
    bonificacao            NUMERIC(12,2) DEFAULT 0,
    pecas_faltantes        INTEGER DEFAULT 0,
    pecas_estragadas       INTEGER DEFAULT 0,
    desconto_pecas         NUMERIC(12,2) DEFAULT 0,
    total_pago             NUMERIC(12,2) DEFAULT 0,
    cpf                    VARCHAR(20),
    banco                  VARCHAR(50),
    agencia                VARCHAR(20),
    conta                  VARCHAR(30),
    pix                    VARCHAR(100),
    data_pagamento         DATE,
    estornado              BOOLEAN DEFAULT FALSE,
    pecas_com_defeito      INTEGER DEFAULT 0,
    valor_defeito          NUMERIC(12,2) DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_pag_corte_codigo
    ON opera.pagamento_corte_acabamento (codigo);
CREATE INDEX IF NOT EXISTS idx_pag_corte_costureira
    ON opera.pagamento_corte_acabamento (costureira);

-- ================================================================
-- [TABELA 29] DETALHES DO ENVIO POR TAMANHO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.envio_detalhes_tamanho (
    envio_id           INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    tamanho            VARCHAR(10) NOT NULL,
    quantidade         INTEGER DEFAULT 0,
    quantidade_pilotos INTEGER DEFAULT 0,
    valor_peca         NUMERIC(12,2) DEFAULT 0,
    PRIMARY KEY (envio_id, tamanho)
);

CREATE INDEX IF NOT EXISTS idx_envio_det_tamanho_envio
    ON opera.envio_detalhes_tamanho (envio_id);
CREATE INDEX IF NOT EXISTS idx_envio_det_tamanho
    ON opera.envio_detalhes_tamanho (tamanho);

-- ================================================================
-- [TABELA 30] RETORNO DETALHES POR TAMANHO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.retorno_detalhes_tamanho (
    id        SERIAL PRIMARY KEY,
    envio_id  INTEGER NOT NULL
              REFERENCES opera.envios_cortes(id)
              ON DELETE CASCADE,
    tamanho   VARCHAR(10) NOT NULL,
    entregue  INTEGER DEFAULT 0,
    copias    INTEGER DEFAULT 0,
    defeitos  INTEGER DEFAULT 0,
    faltantes INTEGER DEFAULT 0,
    regulares INTEGER DEFAULT 0,
    subtotal  NUMERIC(12,2) DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_retorno_tam_envio
    ON opera.retorno_detalhes_tamanho (envio_id);
CREATE INDEX IF NOT EXISTS idx_retorno_tam_tamanho
    ON opera.retorno_detalhes_tamanho (tamanho);

-- ================================================================
-- [TABELA 31] CORTES FINALIZADOS COMPLETO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cortes_finalizados_completo (
    id                    SERIAL PRIMARY KEY,
    entrada_id            INTEGER REFERENCES opera.entrada_acabamento(id) ON DELETE SET NULL,
    envio_id              INTEGER REFERENCES opera.controle_envio_cortes(id) ON DELETE SET NULL,
    corte_id              INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,

    descricao             TEXT,
    ordem_corte           VARCHAR(100),
    codigo_corte          VARCHAR(100),

    qtd_regular_pp        INTEGER DEFAULT 0,
    qtd_regular_p         INTEGER DEFAULT 0,
    qtd_regular_m         INTEGER DEFAULT 0,
    qtd_regular_g         INTEGER DEFAULT 0,
    qtd_regular_gg        INTEGER DEFAULT 0,
    qtd_regular_g1        INTEGER DEFAULT 0,
    qtd_regular_g2        INTEGER DEFAULT 0,
    qtd_regular_g3        INTEGER DEFAULT 0,

    status                VARCHAR(50) DEFAULT 'Finalizado',
    observacoes           TEXT,
    usuario_finalizacao   VARCHAR(100),

    created_at            TIMESTAMP DEFAULT NOW(),
    updated_at            TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_comp_entrada
    ON opera.cortes_finalizados_completo (entrada_id);

-- ================================================================
-- [TABELA 32] ENTRADA ACABAMENTO - DETALHES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.entrada_acabamento_detalhes (
    id                     SERIAL PRIMARY KEY,
    entrada_id             INTEGER NOT NULL REFERENCES opera.entrada_acabamento(id) ON DELETE CASCADE,

    observacoes_finalizacao TEXT,
    bonificacao_aplicada   BOOLEAN DEFAULT FALSE,
    usuario_conferencia    VARCHAR(100),

    total_entregue         INTEGER DEFAULT 0,
    total_copias           INTEGER DEFAULT 0,
    total_defeitos         INTEGER DEFAULT 0,
    total_faltantes        INTEGER DEFAULT 0,
    total_regulares        INTEGER DEFAULT 0,

    valor_total_pagar      NUMERIC(12,2) DEFAULT 0,
    status_finalizacao     VARCHAR(20) DEFAULT 'Pendente',

    data_conferencia       TIMESTAMP,
    created_at             TIMESTAMP DEFAULT NOW(),
    updated_at             TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entrada_det_entrada
    ON opera.entrada_acabamento_detalhes (entrada_id);

-- ================================================================
-- [TABELA 33] LOG DE FINALIZAÇÕES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.log_finalizacoes (
    id             SERIAL PRIMARY KEY,
    entrada_id     INTEGER REFERENCES opera.entrada_acabamento(id),
    acao           VARCHAR(50) NOT NULL,
    dados_antes    JSONB,
    dados_depois   JSONB,
    usuario        VARCHAR(100),
    data_hora      TIMESTAMP DEFAULT NOW(),
    observacoes    TEXT
);

CREATE INDEX IF NOT EXISTS idx_log_finalizacoes_entrada
    ON opera.log_finalizacoes (entrada_id);

-- ================================================================
-- [TABELA 34] PEÇAS FINALIZADAS (HISTÓRICO)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.pecas_finalizadas (
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
);

CREATE INDEX IF NOT EXISTS idx_pecas_finalizadas_corte
    ON opera.pecas_finalizadas (corte_id);

-- ================================================================
-- [TABELA 35] ESTOQUE DE TECIDOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_tecidos (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    cor           VARCHAR(50) NOT NULL,
    composicao    VARCHAR(100),
    fornecedor    VARCHAR(100),
    metros        NUMERIC(12,3) DEFAULT 0,
    kilos         NUMERIC(12,3) DEFAULT 0,
    valor_metro   NUMERIC(12,2) DEFAULT 0,
    valor_kilo    NUMERIC(12,2) DEFAULT 0,
    unidade       VARCHAR(50)   DEFAULT 'metros',
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE          DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP     DEFAULT NOW(),
    updated_at    TIMESTAMP     DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_tecidos_codigo
    ON opera.estoque_tecidos (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_tecidos_cor
    ON opera.estoque_tecidos (cor);

-- ================================================================
-- [TABELA 36] ESTOQUE DE AVIAMENTOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_aviamentos (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    cor           VARCHAR(50) NOT NULL,
    fornecedor    VARCHAR(100),
    quantidade    NUMERIC(12,3) DEFAULT 0,
    unidade       VARCHAR(50)   DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE          DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP     DEFAULT NOW(),
    updated_at    TIMESTAMP     DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_aviamentos_codigo
    ON opera.estoque_aviamentos (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_aviamentos_cor
    ON opera.estoque_aviamentos (cor);

-- ================================================================
-- [TABELA 37] ESTOQUE DE INSUMOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_insumos (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    fornecedor    VARCHAR(100),
    cor           VARCHAR(50) NOT NULL,
    quantidade    NUMERIC(12,3) DEFAULT 0,
    unidade       VARCHAR(50)   DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo          VARCHAR(100),
    categoria     VARCHAR(100),
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE          DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP     DEFAULT NOW(),
    updated_at    TIMESTAMP     DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_insumos_codigo
    ON opera.estoque_insumos (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_insumos_cor
    ON opera.estoque_insumos (cor);

-- ================================================================
-- [TABELA 38] ESTOQUE DE ESCRITÓRIO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_escritorio (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    fornecedor    VARCHAR(100),
    cor           VARCHAR(50) NOT NULL,
    quantidade    NUMERIC(12,3) DEFAULT 0,
    unidade       VARCHAR(50)   DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo          VARCHAR(100),
    categoria     VARCHAR(100),
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE          DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP     DEFAULT NOW(),
    updated_at    TIMESTAMP     DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_escritorio_codigo
    ON opera.estoque_escritorio (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_escritorio_cor
    ON opera.estoque_escritorio (cor);

-- ================================================================
-- [TABELA 39] ESTOQUE DE LIMPEZA
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_limpeza (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    fornecedor    VARCHAR(100),
    cor           VARCHAR(50) NOT NULL,
    quantidade    NUMERIC(12,3) DEFAULT 0,
    unidade       VARCHAR(50)   DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo          VARCHAR(100),
    categoria     VARCHAR(100),
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE          DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP     DEFAULT NOW(),
    updated_at    TIMESTAMP     DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_limpeza_codigo
    ON opera.estoque_limpeza (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_limpeza_cor
    ON opera.estoque_limpeza (cor);

-- ================================================================
-- [TABELA 40] ESTOQUE - OUTROS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_outros (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    fornecedor    VARCHAR(100),
    cor           VARCHAR(50) NOT NULL,
    quantidade    NUMERIC(12,3) DEFAULT 0,
    unidade       VARCHAR(50)   DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo          VARCHAR(100),
    categoria     VARCHAR(100),
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE          DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP     DEFAULT NOW(),
    updated_at    TIMESTAMP     DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_outros_codigo
    ON opera.estoque_outros (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_outros_cor
    ON opera.estoque_outros (cor);

-- ================================================================
-- [TABELA 41] ESTOQUE - LOG DE SAÍDA
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_saida_log (
    id           BIGSERIAL PRIMARY KEY,
    data_hora    TIMESTAMP NOT NULL DEFAULT NOW(),
    tipo_estoque VARCHAR(30) NOT NULL,
    item_id      BIGINT NOT NULL,
    codigo       VARCHAR(100),
    descricao    TEXT,
    cor          VARCHAR(50),
    quantidade   NUMERIC(10, 3) NOT NULL,
    unidade      VARCHAR(20),
    motivo       VARCHAR(100),
    observacoes  TEXT,
    usuario      VARCHAR(100)
);

-- ================================================================
-- [TABELA 42] CADASTRO DE SERVIÇOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.servicos (
    id            SERIAL PRIMARY KEY,
    nome          VARCHAR(200) NOT NULL,
    descricao     TEXT,
    prestador     VARCHAR(200),
    data_inicio   DATE,
    data_fim      DATE,
    valor_unitario NUMERIC(12,2),
    quantidade    INTEGER,
    valor_total   NUMERIC(12,2),
    status        VARCHAR(50),
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_servicos_prestador
    ON opera.servicos (prestador);

-- ================================================================
-- [TABELA 43] HISTÓRICO DE SERVIÇOS GERAIS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.historico_servicos (
    id           SERIAL PRIMARY KEY,
    servico_id   INTEGER REFERENCES opera.servicos(id) ON DELETE CASCADE,
    data_evento  TIMESTAMP NOT NULL DEFAULT NOW(),
    acao         VARCHAR(100),
    observacoes  TEXT
);

CREATE INDEX IF NOT EXISTS idx_hist_servico_id
    ON opera.historico_servicos (servico_id);

-- ================================================================
-- [TABELA 44] RELATÓRIOS DE FINALIZAÇÃO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.relatorios_finalizacao (
    id              SERIAL PRIMARY KEY,
    entrada_id      INTEGER REFERENCES opera.entrada_acabamento(id),
    usuario_geracao VARCHAR(100),
    data_geracao    TIMESTAMP DEFAULT NOW(),
    tipo_relatorio  VARCHAR(50),
    html_content    TEXT,
    pdf_path        TEXT,
    parametros      JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_relatorios_entrada
    ON opera.relatorios_finalizacao (entrada_id);

-- ================================================================
-- [TABELA 45] ORDEM DE CORTE - PREFERÊNCIAS DE GRADE
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.ordem_grade_preferencias (
    id            SERIAL PRIMARY KEY,
    usuario_id    INTEGER NOT NULL
                  REFERENCES opera.usuarios(id)
                  ON DELETE CASCADE,
    nome          VARCHAR(100) NOT NULL,
    porcent_1     NUMERIC(12,4) DEFAULT 0,
    porcent_2     NUMERIC(12,4) DEFAULT 0,
    porcent_3     NUMERIC(12,4) DEFAULT 0,
    porcent_4     NUMERIC(12,4) DEFAULT 0,
    porcent_5     NUMERIC(12,4) DEFAULT 0,
    porcent_6     NUMERIC(12,4) DEFAULT 0,
    porcent_7     NUMERIC(12,4) DEFAULT 0,
    porcent_8     NUMERIC(12,4) DEFAULT 0,
    criado_em     TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    UNIQUE (usuario_id, nome)
);

CREATE INDEX IF NOT EXISTS idx_ordem_grade_pref_usuario
    ON opera.ordem_grade_preferencias (usuario_id);
CREATE INDEX IF NOT EXISTS idx_ordem_grade_pref_nome
    ON opera.ordem_grade_preferencias (nome);

COMMENT ON TABLE opera.ordem_grade_preferencias IS
'TABELA 45 - ORDEM DE CORTE: Preferências de grade por usuário.';

-- ================================================================
-- [TABELA 46] OUTROS SERVIÇOS POR MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_outros_servicos (
    id            SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id   INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo        VARCHAR(100),
    descricao     TEXT,
    cor           VARCHAR(50),
    fornecedor    VARCHAR(100),
    unidade       VARCHAR(20),
    quantidade    NUMERIC(12,4) DEFAULT 0,
    preco         NUMERIC(12,2) DEFAULT 0,
    total         NUMERIC(12,2) DEFAULT 0,
    observacoes   TEXT,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_modelos_outros_servicos_cadastro
    ON opera.cadastro_modelos_outros_servicos (cadastro_id);

CREATE INDEX IF NOT EXISTS idx_modelos_outros_servicos_codigo
    ON opera.cadastro_modelos_outros_servicos (codigo_modelo);


-- ================================================================
--    FUNÇÕES, TRIGGERS E VIEWS (SEM NUMERAÇÃO)
-- ================================================================

-- View de compatibilidade de permissões
CREATE OR REPLACE VIEW opera.permissoes AS
SELECT
    usuario_id,
    codigo AS pagina,
    pode_ver,
    pode_editar,
    pode_imprimir,
    pode_excluir,
    pode_administrar
FROM opera.usuario_permissoes;

-- View simples de usuários (compatibilidade)
CREATE OR REPLACE VIEW opera.usuario AS
SELECT * FROM opera.usuarios;

-- Função de validação de tema
CREATE OR REPLACE FUNCTION opera.validar_cores_tema()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.cores_tema IS NULL OR jsonb_typeof(NEW.cores_tema) != 'object' THEN
        RAISE EXCEPTION 'Estrutura de cores do tema inválida. Deve ser um objeto JSON.';
    END IF;

    IF NOT (NEW.cores_tema ? 'primaria' AND NEW.cores_tema ? 'fundo' AND NEW.cores_tema ? 'texto') THEN
        RAISE EXCEPTION 'Tema deve conter pelo menos as cores: primaria, fundo e texto.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_validar_cores_tema
    ON opera.usuario_temas_personalizados;

CREATE TRIGGER tr_validar_cores_tema
    BEFORE INSERT OR UPDATE ON opera.usuario_temas_personalizados
    FOR EACH ROW EXECUTE FUNCTION opera.validar_cores_tema();

-- Função de log genérico
CREATE OR REPLACE FUNCTION opera.registrar_log_usuario(
    p_usuario VARCHAR(100),
    p_acao TEXT,
    p_pagina TEXT DEFAULT NULL,
    p_detalhe TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO opera.usuario_logs (usuario, acao, pagina, detalhe)
    VALUES (p_usuario, p_acao, p_pagina, p_detalhe);
END;
$$ LANGUAGE plpgsql;

-- Função validar_senha (bcrypt + SHA256 com salt)
CREATE OR REPLACE FUNCTION opera.validar_senha(p_usuario TEXT, p_senha TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_hash TEXT;
    v_bcrypt_ok BOOLEAN := FALSE;
    v_sha256_ok BOOLEAN := FALSE;
BEGIN
    SELECT senha_hash INTO v_hash
    FROM opera.usuarios
    WHERE usuario = p_usuario
    LIMIT 1;

    IF v_hash IS NULL THEN
        RETURN FALSE;
    END IF;

    IF v_hash LIKE '$2%' THEN
        BEGIN
            IF crypt(p_senha, v_hash) = v_hash THEN
                v_bcrypt_ok := TRUE;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            v_bcrypt_ok := FALSE;
        END;
    END IF;

    IF NOT v_bcrypt_ok THEN
        v_sha256_ok :=
            encode(
                digest('sistema_profissional_v2.2' || p_senha, 'sha256'),
                'hex'
            ) = v_hash;
    END IF;

    RETURN v_bcrypt_ok OR v_sha256_ok;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;



-- Resumo final
DO $$
DECLARE
    total_tabelas INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_tabelas
    FROM information_schema.tables
    WHERE table_schema = 'opera';

    RAISE NOTICE '=========================================================';
    RAISE NOTICE '✅ Estrutura do banco OPERA criada/atualizada com sucesso!';
    RAISE NOTICE '📊 Total de tabelas no schema opera: %', total_tabelas;
    RAISE NOTICE '=========================================================';
END $$;