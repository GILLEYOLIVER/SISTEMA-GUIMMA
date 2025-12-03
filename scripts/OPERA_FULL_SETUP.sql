-- ================================================================
-- [ZERAR ESTRUTURAS ANTIGAS DO BANCO OPERA]
-- ================================================================
CREATE SCHEMA IF NOT EXISTS opera AUTHORIZATION CURRENT_USER;

DROP VIEW IF EXISTS opera.permissoes CASCADE;
DROP VIEW IF EXISTS opera.usuario CASCADE;
DROP VIEW IF EXISTS opera.v_usuario_permissoes_norm CASCADE;
DROP TABLE IF EXISTS opera.usuario_temas_personalizados CASCADE;
DROP TABLE IF EXISTS opera.usuario_permissoes CASCADE;
DROP TABLE IF EXISTS opera.usuario_preferencias CASCADE;
DROP TABLE IF EXISTS opera.usuarios CASCADE;
-- ================================================================
-- [INICIALIZAÇÃO]
-- ================================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    RAISE NOTICE '🎬 Iniciando criação das estruturas principais (usuários, preferências, temas personalizados e permissões)...';
END $$;

SET search_path TO opera, public;

-- ================================================================
-- [1️⃣ TABELA DE USUÁRIOS]
-- ================================================================
CREATE TABLE opera.usuarios (
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

CREATE INDEX idx_usuarios_hierarquia ON opera.usuarios (hierarquia);
CREATE INDEX idx_usuarios_ativo ON opera.usuarios (ativo);

COMMENT ON TABLE opera.usuarios IS
    'Tabela principal de usuários do sistema.';

-- ================================================================
-- [2️⃣ PREFERÊNCIAS DO USUÁRIO]
-- ================================================================
CREATE TABLE opera.usuario_preferencias (
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

CREATE INDEX idx_usuario_preferencias_tema ON opera.usuario_preferencias (tema_nome);

COMMENT ON TABLE opera.usuario_preferencias IS
    'Preferências e configurações individuais de cada usuário.';
COMMENT ON COLUMN opera.usuario_preferencias.tema_personalizado IS
    'Paleta de cores personalizada em formato JSON (método antigo - um tema por usuário).';

-- ================================================================
-- [3️⃣ TEMAS PERSONALIZADOS POR USUÁRIO]
-- ================================================================
CREATE TABLE opera.usuario_temas_personalizados (
    id             SERIAL PRIMARY KEY,
    usuario_id     INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    nome_tema      VARCHAR(100) NOT NULL,
    cores_tema     JSONB NOT NULL,
    data_criacao   TIMESTAMP DEFAULT NOW(),
    UNIQUE(usuario_id, nome_tema)
);

CREATE INDEX idx_usuario_temas_usuario ON opera.usuario_temas_personalizados (usuario_id);
CREATE INDEX idx_usuario_temas_nome ON opera.usuario_temas_personalizados (nome_tema);

COMMENT ON TABLE opera.usuario_temas_personalizados IS
    'Temas personalizados de cada usuário (múltiplos temas por usuário).';
COMMENT ON COLUMN opera.usuario_temas_personalizados.cores_tema IS
    'Paleta de cores personalizada em formato JSONB com estrutura completa do tema.';

-- ================================================================
-- [4️⃣ PERMISSÕES POR USUÁRIO]
-- ================================================================
CREATE TABLE opera.usuario_permissoes (
    usuario_id        INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    codigo            VARCHAR(100) NOT NULL,
    pode_ver          BOOLEAN DEFAULT FALSE,
    pode_editar       BOOLEAN DEFAULT FALSE,
    pode_imprimir     BOOLEAN DEFAULT FALSE,
    pode_excluir      BOOLEAN DEFAULT FALSE,
    pode_administrar  BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (usuario_id, codigo)
);

CREATE INDEX idx_usuario_permissoes_codigo ON opera.usuario_permissoes (codigo);

COMMENT ON TABLE opera.usuario_permissoes IS
    'Permissões de acesso por usuário e módulo do sistema.';

-- ================================================================
-- [5️⃣ VIEW DE COMPATIBILIDADE COM O SISTEMA]
-- ================================================================
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

COMMENT ON VIEW opera.permissoes IS
    'View usada pelo sistema Opera para permissões de usuário.';

-- ================================================================
-- [6️⃣ FUNÇÕES E TRIGGERS PARA TEMAS PERSONALIZADOS]
-- ================================================================
CREATE OR REPLACE FUNCTION opera.validar_cores_tema()
RETURNS TRIGGER AS $$
BEGIN
    -- Verifica se o JSON tem a estrutura básica esperada
    IF NEW.cores_tema IS NULL OR jsonb_typeof(NEW.cores_tema) != 'object' THEN
        RAISE EXCEPTION 'Estrutura de cores do tema inválida. Deve ser um objeto JSON.';
    END IF;

    -- Campos obrigatórios mínimos
    IF NOT (NEW.cores_tema ? 'primaria' AND NEW.cores_tema ? 'fundo' AND NEW.cores_tema ? 'texto') THEN
        RAISE EXCEPTION 'Tema deve conter pelo menos as cores: primaria, fundo e texto.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_validar_cores_tema
    BEFORE INSERT OR UPDATE ON opera.usuario_temas_personalizados
    FOR EACH ROW EXECUTE FUNCTION opera.validar_cores_tema();

-- Função para migrar tema antigo para nova estrutura
CREATE OR REPLACE FUNCTION opera.migrar_tema_antigo_para_novo(p_usuario_id INTEGER)
RETURNS VOID AS $$
DECLARE
    v_tema_antigo TEXT;
    v_tema_nome VARCHAR(100);
BEGIN
    -- Busca tema antigo
    SELECT tema_personalizado
    INTO v_tema_antigo
    FROM opera.usuario_preferencias
    WHERE usuario_id = p_usuario_id
    AND tema_personalizado IS NOT NULL;

    IF v_tema_antigo IS NOT NULL THEN
        -- Verifica se já existe um tema com nome padrão
        SELECT COUNT(*) INTO v_tema_nome
        FROM opera.usuario_temas_personalizados
        WHERE usuario_id = p_usuario_id AND nome_tema = 'Meu Tema Personalizado';

        IF v_tema_nome = 0 THEN
            -- Insere na nova tabela
            INSERT INTO opera.usuario_temas_personalizados
            (usuario_id, nome_tema, cores_tema, data_criacao)
            VALUES (p_usuario_id, 'Meu Tema Personalizado', v_tema_antigo::JSONB, NOW());

            RAISE NOTICE 'Tema antigo migrado para nova estrutura para usuário %', p_usuario_id;
        END IF;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- [7️⃣ USUÁRIO MESTRE GIL DE OLIVEIRA]
-- ================================================================
DO $$
DECLARE
    v_user_id INTEGER;
BEGIN
    -- Insere usuário mestre
    INSERT INTO opera.usuarios (usuario, senha_hash, hierarquia, email, dica_senha, tema_preferido)
    VALUES ('Gil de Oliveira', crypt('2580', gen_salt('bf')), 'Administrador', 'opera@gil.com', '25', 'Azul Oceano')
    RETURNING id INTO v_user_id;

    -- Insere preferências
    INSERT INTO opera.usuario_preferencias (usuario_id, tema_nome)
    VALUES (v_user_id, 'Azul Oceano');

    -- Insere permissões completas
    INSERT INTO opera.usuario_permissoes (usuario_id, codigo, pode_ver, pode_editar, pode_imprimir, pode_excluir, pode_administrar)
    SELECT v_user_id, c.codigo, TRUE, TRUE, TRUE, TRUE, TRUE
    FROM (
        VALUES
            ('Dashboard'),
            ('Usuários'),
            ('Temas'),
            ('Relatórios'),
            ('Produção'),
            ('Corte'),
            ('Estoque'),
            ('Financeiro'),
            ('Facções'),
            ('Modelos'),
            ('Backup'),
            ('Configurações'),
            ('Preferências')
    ) AS c(codigo);

    -- Insere alguns temas personalizados de exemplo para o usuário mestre
    INSERT INTO opera.usuario_temas_personalizados (usuario_id, nome_tema, cores_tema) VALUES
    (
        v_user_id,
        'Meu Tema Escuro',
        '{
            "primaria": "#1A1A1A",
            "secundaria": "#2D2D2D",
            "terciaria": "#3A3A3A",
            "fundo": "#121212",
            "texto": "#FFFFFF",
            "destaque": "#3A86FF",
            "sucesso": "#4CAF50",
            "alerta": "#F44336",
            "borda": "#333333",
            "hover": "#2A2A2A",
            "selecao": "#3A86FF"
        }'::JSONB
    ),
    (
        v_user_id,
        'Tema Verde Profissional',
        '{
            "primaria": "#0F241D",
            "secundaria": "#15342A",
            "terciaria": "#1F4D3D",
            "fundo": "#0B1A15",
            "texto": "#E8F5E9",
            "destaque": "#26A69A",
            "sucesso": "#66BB6A",
            "alerta": "#FF7043",
            "borda": "#1A3A2F",
            "hover": "#17362D",
            "selecao": "#26A69A"
        }'::JSONB
    );

    RAISE NOTICE '👤 Usuário mestre Gil de Oliveira criado com ID: %', v_user_id;
    RAISE NOTICE '🎨 2 temas personalizados de exemplo inseridos para o usuário mestre';
END $$;

-- ================================================================
-- [8️⃣ VIEWS ÚTEIS PARA O SISTEMA]
-- ================================================================
CREATE OR REPLACE VIEW opera.v_usuarios_com_preferencias AS
SELECT
    u.id,
    u.usuario,
    u.email,
    u.hierarquia,
    u.tema_preferido,
    up.tema_nome as tema_ativado,
    up.usar_tema_personalizado,
    (SELECT COUNT(*) FROM opera.usuario_temas_personalizados utp WHERE utp.usuario_id = u.id) as total_temas_personalizados,
    u.ultimo_login,
    u.ativo
FROM opera.usuarios u
LEFT JOIN opera.usuario_preferencias up ON u.id = up.usuario_id;

COMMENT ON VIEW opera.v_usuarios_com_preferencias IS
    'View com informações completas de usuários e suas preferências.';

CREATE OR REPLACE VIEW opera.v_temas_por_usuario AS
SELECT
    u.id as usuario_id,
    u.usuario,
    utp.nome_tema,
    utp.cores_tema,
    utp.data_criacao,
    (utp.nome_tema = up.tema_nome) as tema_ativo
FROM opera.usuarios u
LEFT JOIN opera.usuario_temas_personalizados utp ON u.id = utp.usuario_id
LEFT JOIN opera.usuario_preferencias up ON u.id = up.usuario_id;

COMMENT ON VIEW opera.v_temas_por_usuario IS
    'View com todos os temas personalizados organizados por usuário.';

-- ================================================================
-- [9️⃣ MENSAGEM FINAL DE SUCESSO]
-- ================================================================
DO $$
BEGIN
    RAISE NOTICE '=========================================================';
    RAISE NOTICE '✅ ESTRUTURA DO BANCO OPERA CRIADA COM SUCESSO!';
    RAISE NOTICE '=========================================================';
    RAISE NOTICE '📊 Estruturas criadas:';
    RAISE NOTICE '   👤 1 Tabela de usuários';
    RAISE NOTICE '   ⚙️  1 Tabela de preferências';
    RAISE NOTICE '   🎨 1 Tabela de temas personalizados (MÚLTIPLOS por usuário)';
    RAISE NOTICE '   🔐 1 Tabela de permissões';
    RAISE NOTICE '   📋 2 Views úteis';
    RAISE NOTICE '   ⚡ 1 Trigger de validação';
    RAISE NOTICE '   🔄 1 Função de migração';
    RAISE NOTICE '';
    RAISE NOTICE '👤 Usuário mestre: Gil de Oliveira';
    RAISE NOTICE '🔑 Senha: 2580';
    RAISE NOTICE '📧 Email: opera@gil.com';
    RAISE NOTICE '🎨 Temas personalizados: 2 temas de exemplo incluídos';
    RAISE NOTICE '=========================================================';
END $$;

-- ================================================================
-- [TABELA 4] LOGS DE AÇÕES DOS USUÁRIOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.usuario_logs (
    id         SERIAL PRIMARY KEY,
    data_hora  TIMESTAMP NOT NULL DEFAULT NOW(),
    usuario    VARCHAR(100) NOT NULL,
    acao       TEXT,
    pagina     TEXT,
    detalhe    TEXT
);

CREATE INDEX IF NOT EXISTS idx_usuario_logs_usuario ON opera.usuario_logs (usuario);
CREATE INDEX IF NOT EXISTS idx_usuario_logs_data_hora ON opera.usuario_logs (data_hora);

-- ================================================================
-- [TABELA 5] CADASTRO DE MODELOS (CABEÇALHO)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_cabecalho (
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
);

-- ================================================================
-- [TABELA 6] TECIDOS POR MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_tecidos (
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
);

-- ================================================================
-- [TABELA 7] AVIAMENTOS POR MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_aviamentos (
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
);

-- ================================================================
-- [TABELA 8] OUTROS SERVIÇOS POR MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_outros_servicos (
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
);

-- ================================================================
-- [TABELA 9] OUTROS ITENS POR MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_outros (
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
);

CREATE INDEX IF NOT EXISTS idx_modelos_outros_cadastro ON opera.cadastro_modelos_outros (cadastro_id);
CREATE INDEX IF NOT EXISTS idx_modelos_outros_codigo ON opera.cadastro_modelos_outros (codigo_modelo);

-- ================================================================
-- [TABELA 10] IMAGENS DO MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_imagens (
    id              SERIAL PRIMARY KEY,
    codigo_modelo   VARCHAR(100) NOT NULL,
    cadastro_id     INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    tipo_imagem     VARCHAR(20),
    caminho_imagem  TEXT,
    descricao       TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- [TABELA 11] TABELA DE GRADE POR MODELO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_grade (
    id SERIAL PRIMARY KEY,
    modelo_id INTEGER NOT NULL REFERENCES opera.cadastro_modelos_cabecalho (id) ON DELETE CASCADE,
    tamanho VARCHAR(10) NOT NULL,
    disponivel BOOLEAN DEFAULT TRUE,
    UNIQUE (modelo_id, tamanho)
);

-- ================================================================
-- [TABELA 12] CADASTRO DE FACÇÕES E OUTROS PRESTADORES DE SERVIÇO
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

CREATE INDEX IF NOT EXISTS idx_faccoes_nome ON opera.cadastro_faccoes (nome);
CREATE INDEX IF NOT EXISTS idx_faccoes_codigo ON opera.cadastro_faccoes (codigo);
CREATE INDEX IF NOT EXISTS idx_faccoes_tipo ON opera.cadastro_faccoes (tipo_prestador);
CREATE INDEX IF NOT EXISTS idx_faccoes_ativo ON opera.cadastro_faccoes (ativo);
CREATE INDEX IF NOT EXISTS idx_faccoes_tipo_ativo ON opera.cadastro_faccoes (tipo_prestador, ativo);

-- ================================================================
-- [TABELA 13] PAGAMENTO DE SERVIÇOS (FOLHA)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.pagamento_servicos (
    id BIGSERIAL PRIMARY KEY,
    prestador_id INTEGER REFERENCES opera.cadastro_faccoes(id) ON DELETE SET NULL,
    nome_prestador VARCHAR(100),
    data_pagamento DATE NOT NULL,
    valor_total NUMERIC(10, 2) NOT NULL,
    valor_adiantamento_abatido NUMERIC(10, 2) DEFAULT 0.00,
    valor_liquido NUMERIC(10, 2) NOT NULL,
    mes_referencia VARCHAR(10),
    observacoes TEXT,
    usuario_pagamento VARCHAR(100),
    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- [TABELA 14] ADIANTAMENTOS PARA FACÇÕES
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

CREATE INDEX IF NOT EXISTS idx_adiantamento_corte ON opera.adiantamento_faccao (corte_id);
CREATE INDEX IF NOT EXISTS idx_adiantamento_faccao ON opera.adiantamento_faccao (faccao);

-- ================================================================
-- [TABELA 15] PERFIS DE PRECIFICAÇÃO
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
-- [TABELA 16] CADASTRO DE CORTE - CABEÇALHO DA ORDEM
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte (
    id                   SERIAL PRIMARY KEY,
    numero_ordem         VARCHAR(50),
    ordem_corte          VARCHAR(50),
    codigo               VARCHAR(100),
    descricao            TEXT,
    descricao_corte      TEXT,
    data                 DATE,
    data_envio           DATE,
    comprimento_matriz   NUMERIC(12,3),
    largura_matriz       NUMERIC(12,3),
    cortador             VARCHAR(100),
    ajudante             VARCHAR(100),
    auxiliar             VARCHAR(100),
    total_folhas         INTEGER,
    metros_utilizados    NUMERIC(12,3),
    bobinas_utilizadas   NUMERIC(12,3),
    composicao_tecido    VARCHAR(100),
    total_pecas          INTEGER,
    rendimento           NUMERIC(12,4),
    observacoes          TEXT,
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cadastro_corte_codigo ON opera.cadastro_de_corte (codigo);
CREATE INDEX IF NOT EXISTS idx_cadastro_corte_data ON opera.cadastro_de_corte (data);
CREATE INDEX IF NOT EXISTS idx_cadastro_corte_cortador ON opera.cadastro_de_corte (cortador);
CREATE INDEX IF NOT EXISTS idx_cadastro_corte_numero_ordem ON opera.cadastro_de_corte (numero_ordem);

-- ================================================================
-- [TABELA 17] MATERIAIS DE CORTE - TECIDOS UTILIZADOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte_tecidos (
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
);

CREATE INDEX IF NOT EXISTS idx_corte_tecidos_cadastro ON opera.cadastro_de_corte_tecidos (cadastro_id);

-- ================================================================
-- [TABELA 18] LOTES DE CORTE - AGRUPAMENTO POR LOTE
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte_lotes (
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
);

CREATE INDEX IF NOT EXISTS idx_corte_lotes_cadastro ON opera.cadastro_de_corte_lotes (cadastro_id);

-- ================================================================
-- [TABELA 19] ORDEM DE CORTE FICHA (versão completa e corrigida)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.ordem_corte_ficha (
    id                   SERIAL PRIMARY KEY,
    codigo_modelo        VARCHAR(100) NOT NULL,
    descricao_modelo     TEXT,
    cortador             VARCHAR(100),
    auxiliar             VARCHAR(100),
    ajudante             VARCHAR(100),
    data_registro        TIMESTAMP DEFAULT NOW(),
    data_final           DATE,
    dias_estimados       NUMERIC(12,4),
    horas_estimadas      NUMERIC(12,4),
    porcentagens         JSONB,
    consumo_peca         NUMERIC(12,4),
    quantidade_desejada  INTEGER,
    total_pecas          INTEGER,
    observacoes          TEXT,
    status               VARCHAR(50) DEFAULT 'Em Andamento',
    usuario_registro     VARCHAR(100),
    data_atualizacao     TIMESTAMP DEFAULT NOW(),
    ativo                BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_ordem_corte_codigo ON opera.ordem_corte_ficha (codigo_modelo);
CREATE INDEX IF NOT EXISTS idx_ordem_corte_data ON opera.ordem_corte_ficha (data_registro);
CREATE INDEX IF NOT EXISTS idx_ordem_corte_status ON opera.ordem_corte_ficha (status);

-- ================================================================
-- [TABELA 20] LOTES/GRADES DA ORDEM DE CORTE
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.ordem_corte_lotes (
    id BIGSERIAL PRIMARY KEY,
    ordem_id INTEGER NOT NULL REFERENCES opera.ordem_corte_ficha (id) ON DELETE CASCADE,
    lote_numero VARCHAR(50),
    tamanho VARCHAR(10) NOT NULL,
    quantidade INTEGER NOT NULL DEFAULT 0,
    UNIQUE (ordem_id, lote_numero, tamanho)
);

CREATE INDEX IF NOT EXISTS idx_ordem_corte_codigo_modelo ON opera.ordem_corte_ficha (codigo_modelo);
CREATE INDEX IF NOT EXISTS idx_ordem_corte_data_final ON opera.ordem_corte_ficha (data_final);

-- ================================================================
-- [TABELA 21] ENVIO DE CORTES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.envios_cortes (
    id             SERIAL PRIMARY KEY,
    data_envio     DATE,
    prestador_id   INTEGER REFERENCES opera.cadastro_faccoes(id) ON DELETE SET NULL,
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
);

CREATE INDEX IF NOT EXISTS idx_envios_corte_data_envio ON opera.envios_cortes (data_envio);
CREATE INDEX IF NOT EXISTS idx_envios_corte_corte_id ON opera.envios_cortes (corte_id);

-- ================================================================
-- [TABELA 22] CONTROLE DE ENVIO DE CORTES (ATUALIZADA)
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

CREATE INDEX IF NOT EXISTS idx_envio_cortes_data_envio ON opera.controle_envio_cortes (data_envio);
CREATE INDEX IF NOT EXISTS idx_envio_cortes_servico ON opera.controle_envio_cortes (servico);
CREATE INDEX IF NOT EXISTS idx_envio_cortes_costureira ON opera.controle_envio_cortes (costureira);
CREATE INDEX IF NOT EXISTS idx_envio_cortes_ordem_corte ON opera.controle_envio_cortes (ordem_corte);
CREATE INDEX IF NOT EXISTS idx_envio_cortes_status ON opera.controle_envio_cortes (status);

-- ================================================================
-- [TABELA 23] ENTRADA DE ACABAMENTO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.entrada_acabamento (
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
);

-- ================================================================
-- [TABELA 24] HISTÓRICO DE SERVIÇO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.historico_de_servico (
    id BIGSERIAL PRIMARY KEY,
    envio_id INTEGER NOT NULL REFERENCES opera.controle_envio_cortes (id) ON DELETE CASCADE,
    entrada_id INTEGER REFERENCES opera.entrada_acabamento (id) ON DELETE SET NULL,
    pagamento_id BIGINT REFERENCES opera.pagamento_servicos (id) ON DELETE SET NULL,
    tipo_servico VARCHAR(50),
    status VARCHAR(50) DEFAULT 'Em Andamento',
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entrada_acabamento_envio ON opera.entrada_acabamento (envio_id);
CREATE INDEX IF NOT EXISTS idx_entrada_acabamento_data ON opera.entrada_acabamento (data_chegada);

-- ================================================================
-- [TABELA 25] CONTROLE DE RETORNO DE CORTES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.controle_retorno_cortes (
    id                   SERIAL PRIMARY KEY,
    envio_id             INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    data_chegada         DATE,
    ordem_corte          VARCHAR(50),
    codigo_corte         VARCHAR(100),
    descricao_corte      TEXT,
    servico              VARCHAR(100),
    destino              VARCHAR(200),
    costureira           VARCHAR(200),
    faccao               VARCHAR(200),
    quantidade_total     INTEGER,
    valor_peca           NUMERIC(12,2),
    valor_total          NUMERIC(12,2),
    status               VARCHAR(50),
    observacao           TEXT,
    total_entregue       INTEGER,
    total_defeitos       INTEGER,
    total_faltantes      INTEGER,
    total_regulares      INTEGER
);

CREATE INDEX IF NOT EXISTS idx_ctrl_retorno_envio ON opera.controle_retorno_cortes (envio_id);
CREATE INDEX IF NOT EXISTS idx_ctrl_retorno_ordem_corte ON opera.controle_retorno_cortes (ordem_corte);

-- ================================================================
-- [TABELA 26] CORTES FINALIZADOS (COMPLETA E COMPATÍVEL)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cortes_finalizados (
    id                   SERIAL PRIMARY KEY,
    corte_id             INTEGER,
    entrada_id           INTEGER,
    codigo               VARCHAR(100),
    descricao            TEXT,
    costureira           VARCHAR(200),
    data_envio           DATE,
    data_chegada         DATE,
    data_final           DATE,
    qtd_enviada          INTEGER,
    total_pecas          INTEGER,
    quantidade_finalizada INTEGER,
    observacao           TEXT,
    status               VARCHAR(50),
    data_conferencia     TIMESTAMP,
    valor_peca           NUMERIC(12,2),
    bonificacao          BOOLEAN DEFAULT FALSE,
    pago                 BOOLEAN DEFAULT FALSE,
    data_pagamento       DATE,
    qtd_pp               INTEGER DEFAULT 0,
    qtd_p                INTEGER DEFAULT 0,
    qtd_m                INTEGER DEFAULT 0,
    qtd_g                INTEGER DEFAULT 0,
    qtd_gg               INTEGER DEFAULT 0,
    qtd_g1               INTEGER DEFAULT 0,
    qtd_g2               INTEGER DEFAULT 0,
    qtd_g3               INTEGER DEFAULT 0,
    qtd_defeito_pp       INTEGER DEFAULT 0,
    qtd_defeito_p        INTEGER DEFAULT 0,
    qtd_defeito_m        INTEGER DEFAULT 0,
    qtd_defeito_g        INTEGER DEFAULT 0,
    qtd_defeito_gg       INTEGER DEFAULT 0,
    qtd_defeito_g1       INTEGER DEFAULT 0,
    qtd_defeito_g2       INTEGER DEFAULT 0,
    qtd_defeito_g3       INTEGER DEFAULT 0,
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_corte ON opera.cortes_finalizados (corte_id);
CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_entrada ON opera.cortes_finalizados (entrada_id);
CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_data_chegada ON opera.cortes_finalizados (data_chegada);

-- ================================================================
-- [TABELA 27] PAGAMENTO CORTE ACABAMENTO (COMPLETA/CORRIGIDA)
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

CREATE INDEX IF NOT EXISTS idx_pagamento_corte_codigo ON opera.pagamento_corte_acabamento (codigo);
CREATE INDEX IF NOT EXISTS idx_pagamento_corte_costureira ON opera.pagamento_corte_acabamento (costureira);
CREATE INDEX IF NOT EXISTS idx_pagamento_corte_data_pagamento ON opera.pagamento_corte_acabamento (data_pagamento);

-- ================================================================
-- [TABELA 28] ESTOQUE DE TECIDOS
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
    unidade       VARCHAR(50) DEFAULT 'metros',
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_tecidos_codigo ON opera.estoque_tecidos (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_tecidos_cor ON opera.estoque_tecidos (cor);

-- ================================================================
-- [TABELA 29] ESTOQUE DE AVIAMENTOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_aviamentos (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    cor           VARCHAR(50) NOT NULL,
    fornecedor    VARCHAR(100),
    quantidade    NUMERIC(12,3) DEFAULT 0,
    unidade       VARCHAR(50) DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_aviamentos_codigo ON opera.estoque_aviamentos (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_aviamentos_cor ON opera.estoque_aviamentos (cor);

-- ================================================================
-- [TABELA 30] ESTOQUE DE INSUMOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_insumos (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    fornecedor    VARCHAR(100),
    cor           VARCHAR(50) NOT NULL,
    quantidade    NUMERIC(12,3) DEFAULT 0,
    unidade       VARCHAR(50) DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo          VARCHAR(100),
    categoria     VARCHAR(100),
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_insumos_codigo ON opera.estoque_insumos (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_insumos_cor ON opera.estoque_insumos (cor);

-- ================================================================
-- [TABELA 31] ESTOQUE DE ESCRITÓRIO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_escritorio (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    fornecedor    VARCHAR(100),
    cor           VARCHAR(50) NOT NULL,
    quantidade    NUMERIC(12,3) DEFAULT 0,
    unidade       VARCHAR(50) DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo          VARCHAR(100),
    categoria     VARCHAR(100),
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_escritorio_codigo ON opera.estoque_escritorio (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_escritorio_cor ON opera.estoque_escritorio (cor);

-- ================================================================
-- [TABELA 32] ESTOQUE DE LIMPEZA
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_limpeza (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    fornecedor    VARCHAR(100),
    cor           VARCHAR(50) NOT NULL,
    quantidade    NUMERIC(12,3) DEFAULT 0,
    unidade       VARCHAR(50) DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo          VARCHAR(100),
    categoria     VARCHAR(100),
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_limpeza_codigo ON opera.estoque_limpeza (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_limpeza_cor ON opera.estoque_limpeza (cor);

-- ================================================================
-- [TABELA 33] ESTOQUE DE OUTROS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_outros (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    fornecedor    VARCHAR(100),
    cor           VARCHAR(50) NOT NULL,
    quantidade    NUMERIC(12,3) DEFAULT 0,
    unidade       VARCHAR(50) DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo          VARCHAR(100),
    categoria     VARCHAR(100),
    observacoes   TEXT,
    localizacao   VARCHAR(100),
    data_entrada  DATE DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_outros_codigo ON opera.estoque_outros (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_outros_cor ON opera.estoque_outros (cor);

-- ================================================================
-- [TABELA 34] ENVIO DETALHES TAMANHO (CORRIGIDA)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.envio_detalhes_tamanho (
    envio_id            INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    tamanho             VARCHAR(10) NOT NULL,
    quantidade          INTEGER DEFAULT 0,
    quantidade_pilotos  INTEGER DEFAULT 0,
    valor_peca          NUMERIC(12,2) DEFAULT 0,
    PRIMARY KEY (envio_id, tamanho)
);

CREATE INDEX IF NOT EXISTS idx_envio_det_tamanho_envio ON opera.envio_detalhes_tamanho (envio_id);
CREATE INDEX IF NOT EXISTS idx_envio_det_tamanho ON opera.envio_detalhes_tamanho (tamanho);

-- ================================================================
-- [TABELA 35] RETORNO DETALHES TAMANHO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.retorno_detalhes_tamanho (
    id                   SERIAL PRIMARY KEY,
    retorno_id           INTEGER NOT NULL REFERENCES opera.entrada_acabamento(id) ON DELETE CASCADE,
    envio_id             INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    tamanho              VARCHAR(10) NOT NULL,
    quantidade_enviada   INTEGER NOT NULL DEFAULT 0,
    valor_peca_original  NUMERIC(12,2) DEFAULT 0,
    pilotos_enviados     INTEGER DEFAULT 0,
    quantidade_entregue  INTEGER NOT NULL DEFAULT 0,
    quantidade_copias    INTEGER NOT NULL DEFAULT 0,
    quantidade_defeito   INTEGER NOT NULL DEFAULT 0,
    quantidade_faltante  INTEGER NOT NULL DEFAULT 0,
    quantidade_regular   INTEGER NOT NULL DEFAULT 0,
    subtotal             NUMERIC(12,2) DEFAULT 0,
    motivo_defeito       VARCHAR(100),
    observacoes_tamanho  TEXT,
    data_registro        TIMESTAMP DEFAULT NOW(),
    data_atualizacao     TIMESTAMP DEFAULT NOW(),
    UNIQUE(retorno_id, tamanho)
);

CREATE INDEX IF NOT EXISTS idx_retorno_det_retorno ON opera.retorno_detalhes_tamanho (retorno_id);
CREATE INDEX IF NOT EXISTS idx_retorno_det_envio ON opera.retorno_detalhes_tamanho (envio_id);
CREATE INDEX IF NOT EXISTS idx_retorno_det_tamanho ON opera.retorno_detalhes_tamanho (tamanho);

-- ================================================================
-- [TABELA 36] FICHA TÉCNICA
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.ficha_tecnica_cabecalho (
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
);

CREATE INDEX IF NOT EXISTS idx_ficha_tecnica_codigo ON opera.ficha_tecnica_cabecalho (codigo);

-- ================================================================
-- [TABELA 37] CADASTRO DE SERVIÇOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.servicos (
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
);

CREATE INDEX IF NOT EXISTS idx_servicos_prestador ON opera.servicos (prestador);
CREATE INDEX IF NOT EXISTS idx_servicos_data_inicio ON opera.servicos (data_inicio);

-- ================================================================
-- [TABELA 38] HISTÓRICO DE SERVIÇOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.historico_servicos (
    id            SERIAL PRIMARY KEY,
    servico_id    INTEGER REFERENCES opera.servicos(id) ON DELETE CASCADE,
    data_evento   TIMESTAMP NOT NULL DEFAULT NOW(),
    acao          VARCHAR(100),
    observacoes   TEXT
);

CREATE INDEX IF NOT EXISTS idx_hist_servico_id ON opera.historico_servicos (servico_id);

-- ================================================================
-- [TABELA 39] PEÇAS FINALIZADAS
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

CREATE INDEX IF NOT EXISTS idx_pecas_finalizadas_corte ON opera.pecas_finalizadas (corte_id);
CREATE INDEX IF NOT EXISTS idx_pecas_finalizadas_data_chegada ON opera.pecas_finalizadas (data_chegada);
CREATE INDEX IF NOT EXISTS idx_pecas_finalizadas_costureira ON opera.pecas_finalizadas (costureira);
CREATE INDEX IF NOT EXISTS idx_pecas_finalizadas_status ON opera.pecas_finalizadas (status);

-- ================================================================
-- [TABELA 40] DETALHE DO PAGAMENTO DE SERVIÇOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.pagamento_servicos_detalhe (
    pagamento_id BIGINT NOT NULL REFERENCES opera.pagamento_servicos (id) ON DELETE CASCADE,
    entrada_acabamento_id INTEGER NOT NULL REFERENCES opera.entrada_acabamento (id) ON DELETE CASCADE,
    valor_servico NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (pagamento_id, entrada_acabamento_id)
);

-- ================================================================
-- [TABELA 41] ESTOQUE - LOG DE SAÍDA
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_saida_log (
    id            BIGSERIAL PRIMARY KEY,
    data_hora     TIMESTAMP NOT NULL DEFAULT NOW(),
    tipo_estoque  VARCHAR(30) NOT NULL,
    item_id       BIGINT NOT NULL,
    codigo        VARCHAR(100),
    descricao     TEXT,
    cor           VARCHAR(50),
    quantidade    NUMERIC(10, 3) NOT NULL,
    unidade       VARCHAR(20),
    motivo        VARCHAR(100),
    observacoes   TEXT,
    usuario       VARCHAR(100)
);

-- ================================================================
-- [TABELA 42] CORTES FINALIZADOS COMPLETO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cortes_finalizados_completo (
    id                   SERIAL PRIMARY KEY,
    entrada_id           INTEGER UNIQUE REFERENCES opera.entrada_acabamento(id),
    corte_id             INTEGER REFERENCES opera.controle_envio_cortes(id),
    codigo               VARCHAR(100),
    descricao            TEXT,
    costureira           VARCHAR(200),
    servico              VARCHAR(100),
    data_envio           DATE,
    data_chegada         DATE,
    data_conferencia     TIMESTAMP,
    qtd_enviada          INTEGER DEFAULT 0,
    total_entregue       INTEGER DEFAULT 0,
    total_copias         INTEGER DEFAULT 0,
    total_defeitos       INTEGER DEFAULT 0,
    total_faltantes      INTEGER DEFAULT 0,
    total_regulares      INTEGER DEFAULT 0,
    valor_peca           NUMERIC(12,2) DEFAULT 0,
    valor_total          NUMERIC(12,2) DEFAULT 0,
    bonificacao          BOOLEAN DEFAULT FALSE,
    valor_bonificacao    NUMERIC(12,2) DEFAULT 0,
    qtd_pp               INTEGER DEFAULT 0,
    qtd_p                INTEGER DEFAULT 0,
    qtd_m                INTEGER DEFAULT 0,
    qtd_g                INTEGER DEFAULT 0,
    qtd_gg               INTEGER DEFAULT 0,
    qtd_g1               INTEGER DEFAULT 0,
    qtd_g2               INTEGER DEFAULT 0,
    qtd_g3               INTEGER DEFAULT 0,
    qtd_defeito_pp       INTEGER DEFAULT 0,
    qtd_defeito_p        INTEGER DEFAULT 0,
    qtd_defeito_m        INTEGER DEFAULT 0,
    qtd_defeito_g        INTEGER DEFAULT 0,
    qtd_defeito_gg       INTEGER DEFAULT 0,
    qtd_defeito_g1       INTEGER DEFAULT 0,
    qtd_defeito_g2       INTEGER DEFAULT 0,
    qtd_defeito_g3       INTEGER DEFAULT 0,
    qtd_regular_pp       INTEGER DEFAULT 0,
    qtd_regular_p        INTEGER DEFAULT 0,
    qtd_regular_m        INTEGER DEFAULT 0,
    qtd_regular_g        INTEGER DEFAULT 0,
    qtd_regular_gg       INTEGER DEFAULT 0,
    qtd_regular_g1       INTEGER DEFAULT 0,
    qtd_regular_g2       INTEGER DEFAULT 0,
    qtd_regular_g3       INTEGER DEFAULT 0,
    status               VARCHAR(50) DEFAULT 'Finalizado',
    observacoes          TEXT,
    usuario_finalizacao  VARCHAR(100),
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_completo_entrada ON opera.cortes_finalizados_completo (entrada_id);
CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_completo_corte ON opera.cortes_finalizados_completo (corte_id);
CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_completo_status ON opera.cortes_finalizados_completo (status);

-- ================================================================
-- [TABELA 43] LOG DE FINALIZAÇÕES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.log_finalizacoes (
    id                   SERIAL PRIMARY KEY,
    entrada_id           INTEGER REFERENCES opera.entrada_acabamento(id),
    acao                 VARCHAR(50) NOT NULL,
    dados_antes          JSONB,
    dados_depois         JSONB,
    usuario              VARCHAR(100),
    data_hora            TIMESTAMP DEFAULT NOW(),
    observacoes          TEXT
);

CREATE INDEX IF NOT EXISTS idx_log_finalizacoes_entrada ON opera.log_finalizacoes (entrada_id);
CREATE INDEX IF NOT EXISTS idx_log_finalizacoes_data ON opera.log_finalizacoes (data_hora);
CREATE INDEX IF NOT EXISTS idx_log_finalizacoes_usuario ON opera.log_finalizacoes (usuario);

-- ================================================================
-- [TABELA 44] ENTRADA ACABAMENTO DETALHES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.entrada_acabamento_detalhes (
    id                   SERIAL PRIMARY KEY,
    entrada_id           INTEGER NOT NULL REFERENCES opera.entrada_acabamento(id) ON DELETE CASCADE,
    observacoes_finalizacao TEXT,
    bonificacao_aplicada BOOLEAN DEFAULT FALSE,
    usuario_conferencia  VARCHAR(100),
    total_entregue       INTEGER DEFAULT 0,
    total_copias         INTEGER DEFAULT 0,
    total_defeitos       INTEGER DEFAULT 0,
    total_faltantes      INTEGER DEFAULT 0,
    total_regulares      INTEGER DEFAULT 0,
    valor_total_pagar    NUMERIC(12,2) DEFAULT 0,
    status_finalizacao   VARCHAR(20) DEFAULT 'Pendente',
    data_conferencia     TIMESTAMP,
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entrada_det_entrada ON opera.entrada_acabamento_detalhes (entrada_id);
CREATE INDEX IF NOT EXISTS idx_entrada_det_status ON opera.entrada_acabamento_detalhes (status_finalizacao);

-- ================================================================
-- [TABELA 45] CONTROLE ENVIO CORTES DETALHES
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.controle_envio_cortes_detalhes (
    id                   SERIAL PRIMARY KEY,
    envio_id             INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    prestador_servico    VARCHAR(200),
    tipo_servico         VARCHAR(100),
    valor_pp             NUMERIC(12,2) DEFAULT 0,
    valor_p              NUMERIC(12,2) DEFAULT 0,
    valor_m              NUMERIC(12,2) DEFAULT 0,
    valor_g              NUMERIC(12,2) DEFAULT 0,
    valor_gg             NUMERIC(12,2) DEFAULT 0,
    valor_g1             NUMERIC(12,2) DEFAULT 0,
    valor_g2             NUMERIC(12,2) DEFAULT 0,
    valor_g3             NUMERIC(12,2) DEFAULT 0,
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_envio_det_envio ON opera.controle_envio_cortes_detalhes (envio_id);

-- ================================================================
-- [TABELA 46] RELATÓRIOS FINALIZAÇÃO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.relatorios_finalizacao (
    id                   SERIAL PRIMARY KEY,
    entrada_id           INTEGER REFERENCES opera.entrada_acabamento(id),
    usuario_geracao      VARCHAR(100),
    data_geracao         TIMESTAMP DEFAULT NOW(),
    tipo_relatorio       VARCHAR(50),
    html_content         TEXT,
    pdf_path             TEXT,
    parametros           JSONB,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_relatorios_entrada ON opera.relatorios_finalizacao (entrada_id);
CREATE INDEX IF NOT EXISTS idx_relatorios_data ON opera.relatorios_finalizacao (data_geracao);
CREATE INDEX IF NOT EXISTS idx_relatorios_usuario ON opera.relatorios_finalizacao (usuario_geracao);

-- ================================================================
--  ÍNDICES PARA PERFORMANCE
-- ================================================================
CREATE INDEX IF NOT EXISTS idx_cadastro_modelos_codigo ON opera.cadastro_modelos_cabecalho (codigo);
CREATE INDEX IF NOT EXISTS idx_cadastro_modelos_descricao ON opera.cadastro_modelos_cabecalho (descricao);
CREATE INDEX IF NOT EXISTS idx_modelos_tecidos_cadastro ON opera.cadastro_modelos_tecidos (cadastro_id);
CREATE INDEX IF NOT EXISTS idx_modelos_tecidos_codigo ON opera.cadastro_modelos_tecidos (codigo_modelo);
CREATE INDEX IF NOT EXISTS idx_modelos_aviamentos_cadastro ON opera.cadastro_modelos_aviamentos (cadastro_id);
CREATE INDEX IF NOT EXISTS idx_modelos_aviamentos_codigo ON opera.cadastro_modelos_aviamentos (codigo_modelo);
CREATE INDEX IF NOT EXISTS idx_modelos_outros_cadastro ON opera.cadastro_modelos_outros_servicos (cadastro_id);
CREATE INDEX IF NOT EXISTS idx_modelos_outros_codigo ON opera.cadastro_modelos_outros_servicos (codigo_modelo);
CREATE INDEX IF NOT EXISTS idx_modelos_imagens_cadastro ON opera.cadastro_modelos_imagens (cadastro_id);
CREATE INDEX IF NOT EXISTS idx_modelos_imagens_codigo ON opera.cadastro_modelos_imagens (codigo_modelo);

-- ================================================================
--  VIEW DE COMPATIBILIDADE usuario
-- ================================================================
CREATE OR REPLACE VIEW opera.usuario AS
SELECT * FROM opera.usuarios;

-- ================================================================
--  VIEW DE PERMISSÕES DO SISTEMA
-- ================================================================
CREATE OR REPLACE VIEW opera.permissoes_catalogo AS
SELECT 'usuarios' AS codigo, 'Usuários' AS nome UNION ALL
SELECT 'cadastro_modelos', 'Cadastro de Modelos' UNION ALL
SELECT 'cadastro_de_corte', 'Cadastro de Corte' UNION ALL
SELECT 'controle_envio_cortes', 'Envio de Cortes' UNION ALL
SELECT 'estoque_tecidos', 'Estoque de Tecidos' UNION ALL
SELECT 'estoque_aviamentos', 'Estoque de Aviamentos';

-- ================================================================
--  PERMISSÕES PARA O ADMIN (CORRIGIDO)
-- ================================================================
INSERT INTO opera.usuario_permissoes
(usuario_id, codigo, pode_ver, pode_editar, pode_imprimir, pode_excluir, pode_administrar)
SELECT
    u.id,
    p.codigo,
    TRUE, TRUE, TRUE, TRUE, TRUE
FROM opera.usuarios u, opera.permissoes_catalogo p
WHERE u.usuario = 'Gil de Oliveira'
ON CONFLICT (usuario_id, codigo) DO NOTHING;

-- ================================================================
--  VIEW DE PERMISSÕES NORMALIZADA (CORRIGIDA)
-- ================================================================
CREATE OR REPLACE VIEW opera.v_usuario_permissoes_norm AS
SELECT
    up.usuario_id,
    up.codigo AS permissao_codigo,
    COALESCE(up.pode_ver, FALSE) AS pode_ver,
    COALESCE(up.pode_editar, FALSE) AS pode_editar,
    COALESCE(up.pode_imprimir, FALSE) AS pode_imprimir,
    COALESCE(up.pode_excluir, FALSE) AS pode_excluir,
    COALESCE(up.pode_administrar, FALSE) AS pode_administrar,
    (COALESCE(up.pode_ver, FALSE) OR
     COALESCE(up.pode_editar, FALSE) OR
     COALESCE(up.pode_imprimir, FALSE) OR
     COALESCE(up.pode_excluir, FALSE) OR
     COALESCE(up.pode_administrar, FALSE)) AS permitido
FROM opera.usuario_permissoes up;

-- ================================================================
--  VERIFICAÇÃO FINAL E CONTAGEM DE TABELAS
-- ================================================================
DO $$
DECLARE
    total_tabelas INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_tabelas
    FROM information_schema.tables
    WHERE table_schema = 'opera';
    RAISE NOTICE 'Total de tabelas criadas no schema opera: %', total_tabelas;
    IF total_tabelas >= 46 THEN
        RAISE NOTICE '✅ TODAS AS 46 TABELAS, ÍNDICES E VIEWS CRIADAS COM SUCESSO!';
    ELSE
        RAISE NOTICE '⚠️ ALGUMAS TABELAS PODEM NÃO TER SIDO CRIADAS (verifique o log).';
    END IF;
END $$;

-- ================================================================
--  FIM DO SCRIPT
-- ================================================================

DO $$
DECLARE
    total_tabelas INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_tabelas
    FROM information_schema.tables
    WHERE table_schema = 'opera';

    RAISE NOTICE '✅ Total de tabelas criadas no schema opera: %', total_tabelas;
END $$;

SELECT
    current_database() AS banco_atual,
    COUNT(*) as total_tabelas,
    '✅ TABELAS criadas com sucesso no banco_opera.schema_opera!' AS status
FROM information_schema.tables
WHERE table_schema = 'opera';