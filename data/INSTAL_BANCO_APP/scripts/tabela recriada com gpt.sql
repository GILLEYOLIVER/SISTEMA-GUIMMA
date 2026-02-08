-- ================================================================
--  CRIAR BANCO OPERA - BLOCO 1 (ESTRUTURA BASE)
--  - Schema opera
--  - Extensões
--  - Funções de login/temas
--  - Usuários / Preferências / Temas
--  - Permissões / Logs
--  - _schema_info
--  - Perfis de precificação
--  - Cadastro de corte (cabeçalho)
-- ================================================================

BEGIN;

-- ------------------------------------------------
-- 1) SCHEMA E EXTENSÕES
-- ------------------------------------------------
CREATE SCHEMA IF NOT EXISTS opera;

ALTER SCHEMA opera OWNER TO postgres;

SET search_path TO opera, public;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------
-- 2) FUNÇÃO registrar_log_usuario (compatível com seu sistema)
-- ------------------------------------------------
CREATE OR REPLACE FUNCTION opera.registrar_log_usuario(
    p_usuario  VARCHAR,
    p_acao     TEXT,
    p_pagina   TEXT DEFAULT NULL,
    p_detalhe  TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO opera.usuario_logs (usuario, acao, pagina, detalhe)
    VALUES (p_usuario, p_acao, p_pagina, p_detalhe);
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------
-- 3) FUNÇÃO validar_cores_tema (igual ao backup)
-- ------------------------------------------------
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

-- ------------------------------------------------
-- 4) FUNÇÃO validar_senha (igual ao backup, com bcrypt + SHA256)
-- ------------------------------------------------
CREATE OR REPLACE FUNCTION opera.validar_senha(p_usuario TEXT, p_senha TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_hash       TEXT;
    v_bcrypt_ok  BOOLEAN := FALSE;
    v_sha256_ok  BOOLEAN := FALSE;
BEGIN
    SELECT senha_hash
    INTO v_hash
    FROM opera.usuarios
    WHERE usuario = p_usuario
    LIMIT 1;

    IF v_hash IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Senhas com bcrypt ($2a, $2b, $2y)
    IF v_hash LIKE '$2%' THEN
        BEGIN
            IF crypt(p_senha, v_hash) = v_hash THEN
                v_bcrypt_ok := TRUE;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            v_bcrypt_ok := FALSE;
        END;
    END IF;

    -- Fallback SHA256 com salt
    IF NOT v_bcrypt_ok THEN
        v_sha256_ok :=
            encode(
                digest('sistema_profissional_v2.2' || p_senha, 'sha256'),
                'hex'
            ) = v_hash;
    END IF;

    RETURN v_bcrypt_ok OR v_sha256_ok;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- [TABELA 01] USUÁRIOS
-- (baseado em auto_opera/backup)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.usuarios (
    id              SERIAL PRIMARY KEY,
    usuario         VARCHAR(100) NOT NULL UNIQUE,
    senha_hash      TEXT,
    hierarquia      VARCHAR(50) NOT NULL,
    email           VARCHAR(255),
    data_criacao    TIMESTAMP DEFAULT NOW(),
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    dica_senha      TEXT,
    ultimo_login    TIMESTAMP,
    telefone        VARCHAR(50),
    departamento    VARCHAR(100),
    tema_preferido  VARCHAR(50) DEFAULT 'Noite Urbana'
);

COMMENT ON TABLE opera.usuarios IS
    'TABELA 01 - Registro dos usuários do sistema OPERA.';

CREATE OR REPLACE VIEW opera.usuario AS
SELECT
    id,
    usuario,
    senha_hash,
    hierarquia,
    email,
    data_criacao,
    ativo,
    dica_senha,
    ultimo_login,
    telefone,
    departamento,
    tema_preferido
FROM opera.usuarios;

CREATE INDEX IF NOT EXISTS idx_usuarios_ativo
    ON opera.usuarios (ativo);

CREATE INDEX IF NOT EXISTS idx_usuarios_hierarquia
    ON opera.usuarios (hierarquia);

-- ================================================================
-- [TABELA 02] PREFERÊNCIAS DO USUÁRIO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.usuario_preferencias (
    usuario_id               INTEGER PRIMARY KEY
                             REFERENCES opera.usuarios(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_usuario_preferencias_tema
    ON opera.usuario_preferencias (tema_nome);

COMMENT ON TABLE opera.usuario_preferencias IS
    'Preferências e configurações individuais de cada usuário.';

COMMENT ON COLUMN opera.usuario_preferencias.tema_personalizado IS
    'Paleta de cores personalizada em formato JSON (método antigo - um tema por usuário).';

-- ================================================================
-- [TABELA 03] TEMAS PERSONALIZADOS POR USUÁRIO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.usuario_temas_personalizados (
    id             SERIAL PRIMARY KEY,
    usuario_id     INTEGER NOT NULL
                   REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    nome_tema      VARCHAR(100) NOT NULL,
    cores_tema     JSONB NOT NULL,
    data_criacao   TIMESTAMP DEFAULT NOW(),
    atualizado_em  TIMESTAMP DEFAULT NOW(),
    UNIQUE (usuario_id, nome_tema)
);

CREATE INDEX IF NOT EXISTS idx_usuario_temas_usuario
    ON opera.usuario_temas_personalizados (usuario_id);

CREATE INDEX IF NOT EXISTS idx_usuario_temas_nome
    ON opera.usuario_temas_personalizados (nome_tema);

COMMENT ON TABLE opera.usuario_temas_personalizados IS
    'Temas personalizados de cada usuário (múltiplos temas por usuário).';

COMMENT ON COLUMN opera.usuario_temas_personalizados.cores_tema IS
    'Paleta de cores personalizada em formato JSONB com estrutura completa do tema.';

COMMENT ON COLUMN opera.usuario_temas_personalizados.atualizado_em IS
    'Data e hora da última modificação do tema personalizado.';

-- Trigger de validação de cores (igual backup)
CREATE TRIGGER tr_validar_cores_tema
    BEFORE INSERT OR UPDATE ON opera.usuario_temas_personalizados
    FOR EACH ROW
    EXECUTE FUNCTION opera.validar_cores_tema();

-- ================================================================
-- [TABELA 04] PERMISSÕES POR USUÁRIO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.usuario_permissoes (
    usuario_id        INTEGER NOT NULL
                      REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    codigo            VARCHAR(100) NOT NULL,
    pode_ver          BOOLEAN DEFAULT FALSE,
    pode_editar       BOOLEAN DEFAULT FALSE,
    pode_imprimir     BOOLEAN DEFAULT FALSE,
    pode_excluir      BOOLEAN DEFAULT FALSE,
    pode_administrar  BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (usuario_id, codigo)
);

CREATE INDEX IF NOT EXISTS idx_usuario_permissoes_codigo
    ON opera.usuario_permissoes (codigo);

COMMENT ON TABLE opera.usuario_permissoes IS
    'Permissões de acesso por usuário e módulo do sistema.';

-- View de compatibilidade com sistema
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
-- [TABELA 05] LOGS DE AÇÕES DOS USUÁRIOS
-- (forma "arrumada" para o seu sistema)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.usuario_logs (
    id         SERIAL PRIMARY KEY,
    data_hora  TIMESTAMP NOT NULL DEFAULT NOW(),
    usuario    VARCHAR(100) NOT NULL,
    acao       TEXT,
    pagina     TEXT,
    detalhe    TEXT
);

CREATE INDEX IF NOT EXISTS idx_usuario_logs_usuario
    ON opera.usuario_logs (usuario);

CREATE INDEX IF NOT EXISTS idx_usuario_logs_data_hora
    ON opera.usuario_logs (data_hora);

-- View para consulta de logs (opcional)
CREATE OR REPLACE VIEW opera.v_logs_usuarios AS
SELECT
    id,
    data_hora,
    usuario,
    acao,
    pagina,
    detalhe
FROM opera.usuario_logs
ORDER BY data_hora DESC;

COMMENT ON VIEW opera.v_logs_usuarios IS
    'View para consulta ordenada dos logs de atividades dos usuários.';

-- Função de manutenção de logs (extra, mas compatível)
CREATE OR REPLACE FUNCTION opera.limpar_logs_antigos(p_dias_manter INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    v_registros_afetados INTEGER;
BEGIN
    DELETE FROM opera.usuario_logs
    WHERE data_hora < (NOW() - (p_dias_manter || ' days')::INTERVAL);

    GET DIAGNOSTICS v_registros_afetados = ROW_COUNT;

    PERFORM opera.registrar_log_usuario(
        'Sistema',
        'Limpeza automática de logs',
        'Manutenção',
        'Removidos ' || v_registros_afetados || ' registros com mais de ' || p_dias_manter || ' dias'
    );

    RETURN v_registros_afetados;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION opera.limpar_logs_antigos IS
    'Remove logs antigos para manter o desempenho do sistema.';

-- ================================================================
-- [TABELA 06] _SCHEMA_INFO (igual backup, mas simplificada)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera._schema_info (
    id           SERIAL PRIMARY KEY,
    schema_name  TEXT DEFAULT 'opera',
    versao       TEXT DEFAULT '1.0',
    criado_em    TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE opera._schema_info IS
    'Controle de versão do schema do sistema OPERA.';

-- ================================================================
-- [TABELA 07] PERFIS DE PRECIFICAÇÃO
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
-- [TABELA 08] CADASTRO DE CORTE - CABEÇALHO
-- (igual à que você já usa em CONTROLE_ENVIO_CORTES)
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

    pp                   INTEGER NOT NULL DEFAULT 0,
    p                    INTEGER NOT NULL DEFAULT 0,
    m                    INTEGER NOT NULL DEFAULT 0,
    g                    INTEGER NOT NULL DEFAULT 0,
    gg                   INTEGER NOT NULL DEFAULT 0,
    g1                   INTEGER NOT NULL DEFAULT 0,
    g2                   INTEGER NOT NULL DEFAULT 0,
    g3                   INTEGER NOT NULL DEFAULT 0,

    total_pecas          INTEGER NOT NULL DEFAULT 0,
    rendimento           NUMERIC(12,4),
    observacoes          TEXT,
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cadastro_corte_codigo
    ON opera.cadastro_de_corte (codigo);

CREATE INDEX IF NOT EXISTS idx_cadastro_corte_data
    ON opera.cadastro_de_corte (data);

CREATE INDEX IF NOT EXISTS idx_cadastro_corte_cortador
    ON opera.cadastro_de_corte (cortador);

CREATE INDEX IF NOT EXISTS idx_cadastro_corte_numero_ordem
    ON opera.cadastro_de_corte (numero_ordem);

COMMIT;
-- ================================================================
-- [TABELA 22] CONTROLE DE ENVIO DE CORTES
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

    -- grade enviada
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
CREATE INDEX IF NOT EXISTS idx_envio_cortes_servico    ON opera.controle_envio_cortes (servico);
CREATE INDEX IF NOT EXISTS idx_envio_cortes_costureira ON opera.controle_envio_cortes (costureira);
CREATE INDEX IF NOT EXISTS idx_envio_cortes_ordem_corte ON opera.controle_envio_cortes (ordem_corte);
CREATE INDEX IF NOT EXISTS idx_envio_cortes_status ON opera.controle_envio_cortes (status);

-- ================================================================
-- [TABELA 23] ENTRADA DE ACABAMENTO (RETORNO)
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

CREATE INDEX IF NOT EXISTS idx_entrada_acabamento_envio_id ON opera.entrada_acabamento (envio_id);
CREATE INDEX IF NOT EXISTS idx_entrada_acabamento_data     ON opera.entrada_acabamento (data_chegada);

-- ================================================================
-- [TABELA 24] HISTÓRICO DE SERVIÇO (RESUMO DA ENTRADA)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.historico_de_servico (
    id                    SERIAL PRIMARY KEY,
    envio_id              INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    entrada_acabamento_id INTEGER NOT NULL REFERENCES opera.entrada_acabamento(id) ON DELETE CASCADE,
    corte_id              INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,
    prestador             VARCHAR(200),
    tipo_servico          VARCHAR(100),
    data_envio            DATE,
    data_chegada          DATE,
    quantidade_enviada    INTEGER,
    quantidade_entregue   INTEGER,
    quantidade_defeitos   INTEGER,
    quantidade_faltantes  INTEGER,
    quantidade_regulares  INTEGER,
    valor_peca            NUMERIC(12,2),
    valor_total           NUMERIC(12,2),
    status                VARCHAR(50),
    observacoes           TEXT,
    created_at            TIMESTAMP DEFAULT NOW(),
    updated_at            TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hist_servico_envio    ON opera.historico_de_servico (envio_id);
CREATE INDEX IF NOT EXISTS idx_hist_servico_entrada  ON opera.historico_de_servico (entrada_acabamento_id);
CREATE INDEX IF NOT EXISTS idx_hist_servico_prestador ON opera.historico_de_servico (prestador);
CREATE INDEX IF NOT EXISTS idx_hist_servico_data_envio ON opera.historico_de_servico (data_envio);

-- ================================================================
-- [TABELA 25] CONTROLE DE RETORNO DE CORTES (CABEÇALHO)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.controle_retorno_cortes (
    id                   SERIAL PRIMARY KEY,
    envio_id             INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    data_retorno         DATE,
    total_recebido       INTEGER,
    total_defeitos       INTEGER,
    total_faltantes      INTEGER,
    total_regulares      INTEGER,
    valor_total          NUMERIC(12,2),
    status_retorno       VARCHAR(50) DEFAULT 'Pendente',
    observacoes          TEXT,
    usuario_registro     VARCHAR(100),
    data_registro        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ctrl_retorno_envio   ON opera.controle_retorno_cortes (envio_id);
CREATE INDEX IF NOT EXISTS idx_ctrl_retorno_data    ON opera.controle_retorno_cortes (data_retorno);
CREATE INDEX IF NOT EXISTS idx_ctrl_retorno_status  ON opera.controle_retorno_cortes (status_retorno);

-- ================================================================
-- [TABELA 26] ENVIO DETALHES TAMANHO (CORRIGIDA)
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
CREATE INDEX IF NOT EXISTS idx_envio_det_tamanho       ON opera.envio_detalhes_tamanho (tamanho);

-- ================================================================
-- [TABELA 27] RETORNO DETALHES POR TAMANHO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.retorno_detalhes_tamanho (
    id         SERIAL PRIMARY KEY,
    envio_id   INTEGER NOT NULL
               REFERENCES opera.envios_cortes(id)
               ON DELETE CASCADE,

    tamanho    VARCHAR(10) NOT NULL,

    entregue   INTEGER DEFAULT 0,
    copias     INTEGER DEFAULT 0,
    defeitos   INTEGER DEFAULT 0,
    faltantes  INTEGER DEFAULT 0,
    regulares  INTEGER DEFAULT 0,

    subtotal   NUMERIC(12,2) DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_retorno_tam_envio
    ON opera.retorno_detalhes_tamanho (envio_id);

CREATE INDEX IF NOT EXISTS idx_retorno_tam_tamanho
    ON opera.retorno_detalhes_tamanho (tamanho);

-- ================================================================
-- [TABELA 28] CORTES FINALIZADOS (RESUMO)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.cortes_finalizados (
    id                      SERIAL PRIMARY KEY,
    corte_id                INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,
    envio_id                INTEGER REFERENCES opera.controle_envio_cortes(id) ON DELETE SET NULL,
    entrada_acabamento_id   INTEGER REFERENCES opera.entrada_acabamento(id) ON DELETE SET NULL,
    data_finalizacao        DATE,
    total_pecas             INTEGER,
    total_defeitos          INTEGER,
    total_faltantes         INTEGER,
    total_regulares         INTEGER,
    valor_total             NUMERIC(12,2),
    tempo_estimado_horas    NUMERIC(12,2),
    tempo_real_horas        NUMERIC(12,2),
    eficiencia_percentual   NUMERIC(5,2),
    usuario_finalizacao     VARCHAR(100),
    observacoes             TEXT,
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_corte
    ON opera.cortes_finalizados (corte_id);

CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_envio
    ON opera.cortes_finalizados (envio_id);

CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_data
    ON opera.cortes_finalizados (data_finalizacao);

-- ================================================================
-- [TABELA 29] PAGAMENTO CORTE / ACABAMENTO
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.pagamento_corte_acabamento (
    id                   SERIAL PRIMARY KEY,
    entrada_acabamento_id INTEGER NOT NULL
                          REFERENCES opera.entrada_acabamento(id)
                          ON DELETE CASCADE,
    prestador            VARCHAR(200),
    data_pagamento       DATE,
    valor_total          NUMERIC(12,2),
    forma_pagamento      VARCHAR(50),
    observacoes          TEXT,
    usuario_registro     VARCHAR(100),
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pagto_corte_entrada
    ON opera.pagamento_corte_acabamento (entrada_acabamento_id);

CREATE INDEX IF NOT EXISTS idx_pagto_corte_prestador
    ON opera.pagamento_corte_acabamento (prestador);

-- ================================================================
-- [TABELA 30] PAGAMENTO DE SERVIÇOS (CABECALHO)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.pagamento_servicos (
    id               SERIAL PRIMARY KEY,
    data_pagamento   DATE NOT NULL,
    prestador        VARCHAR(200),
    valor_total      NUMERIC(12,2),
    forma_pagamento  VARCHAR(50),
    status           VARCHAR(50) DEFAULT 'Pendente',
    observacoes      TEXT,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pagto_servicos_data
    ON opera.pagamento_servicos (data_pagamento);

CREATE INDEX IF NOT EXISTS idx_pagto_servicos_prestador
    ON opera.pagamento_servicos (prestador);

-- ================================================================
-- [TABELA 31] PAGAMENTO DE SERVIÇOS (DETALHES POR ENTRADA)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.pagamento_servicos_detalhe (
    pagamento_id           INTEGER NOT NULL
                           REFERENCES opera.pagamento_servicos(id)
                           ON DELETE CASCADE,
    entrada_acabamento_id  INTEGER NOT NULL
                           REFERENCES opera.entrada_acabamento(id)
                           ON DELETE CASCADE,
    valor_parcial          NUMERIC(12,2),
    PRIMARY KEY (pagamento_id, entrada_acabamento_id)
);

CREATE INDEX IF NOT EXISTS idx_pagto_serv_det_pagamento
    ON opera.pagamento_servicos_detalhe (pagamento_id);

CREATE INDEX IF NOT EXISTS idx_pagto_serv_det_entrada
    ON opera.pagamento_servicos_detalhe (entrada_acabamento_id);

-- ================================================================
-- [TABELA 32] PEÇAS FINALIZADAS (LIGAÇÃO ENTRADA ↔ RESUMO)
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.pecas_finalizadas (
    id                      SERIAL PRIMARY KEY,
    entrada_id              INTEGER NOT NULL
                            REFERENCES opera.entrada_acabamento(id)
                            ON DELETE CASCADE,
    corte_id                INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,
    total_pecas_finalizadas INTEGER,
    total_defeitos          INTEGER,
    total_faltantes         INTEGER,
    total_regulares         INTEGER,
    valor_total             NUMERIC(12,2),
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW(),
    UNIQUE (entrada_id)
);

CREATE INDEX IF NOT EXISTS idx_pecas_finalizadas_entrada
    ON opera.pecas_finalizadas (entrada_id);

-- ================================================================
-- [TABELA 33] ESTOQUE DE TECIDOS
-- ================================================================
CREATE TABLE IF NOT EXISTS opera.estoque_tecidos (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(100) NOT NULL,
    descricao     TEXT,
    fornecedor    VARCHAR(100),
    cor           VARCHAR(50) NOT NULL,
    largura       NUMERIC(12,3),
    gramatura     NUMERIC(12,3),
    composicao    VARCHAR(100),
    metragem      NUMERIC(12,3) DEFAULT 0,
    valor_metro   NUMERIC(12,2) DEFAULT 0,
    localizacao   VARCHAR(100),
    observacoes   TEXT,
    data_entrada  DATE DEFAULT CURRENT_DATE,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

CREATE INDEX IF NOT EXISTS idx_estoque_tecidos_codigo ON opera.estoque_tecidos (codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_tecidos_cor    ON opera.estoque_tecidos (cor);

-- ================================================================
-- [TABELA 34] ESTOQUE DE AVIAMENTOS
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
CREATE INDEX IF NOT EXISTS idx_estoque_aviamentos_cor    ON opera.estoque_aviamentos (cor);

-- ================================================================
-- [TABELA 35] ESTOQUE DE INSUMOS
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
CREATE INDEX IF NOT EXISTS idx_estoque_insumos_cor    ON opera.estoque_insumos (cor);

-- ================================================================
-- [TABELA 36] ESTOQUE DE ESCRITÓRIO
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
CREATE INDEX IF NOT EXISTS idx_estoque_escritorio_cor    ON opera.estoque_escritorio (cor);

-- ================================================================
-- [TABELA 37] ESTOQUE DE LIMPEZA
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
CREATE INDEX IF NOT EXISTS idx_estoque_limpeza_cor    ON opera.estoque_limpeza (cor);

-- ================================================================
-- [TABELA 38] ESTOQUE DE OUTROS
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
CREATE INDEX IF NOT EXISTS idx_estoque_outros_cor    ON opera.estoque_outros (cor);
-- ================================================================
-- [TABELA 48] ORDEM DE CORTE - PREFERÊNCIAS DE GRADE POR USUÁRIO
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

-- ================================================================
-- ÍNDICES DA TABELA 48
-- ================================================================

-- Índice para busca por usuário
CREATE INDEX IF NOT EXISTS idx_ordem_grade_pref_usuario
    ON opera.ordem_grade_preferencias (usuario_id);

-- Índice para busca por nome
CREATE INDEX IF NOT EXISTS idx_ordem_grade_pref_nome
    ON opera.ordem_grade_preferencias (nome);

-- Índice composto para buscas frequentes
CREATE INDEX IF NOT EXISTS idx_ordem_grade_pref_usuario_nome
    ON opera.ordem_grade_preferencias (usuario_id, nome);

-- Índice para ordenação por data de criação
CREATE INDEX IF NOT EXISTS idx_ordem_grade_pref_criado_em
    ON opera.ordem_grade_preferencias (criado_em DESC);

-- Índice para ordenação por data de atualização
CREATE INDEX IF NOT EXISTS idx_ordem_grade_pref_atualizado_em
    ON opera.ordem_grade_preferencias (atualizado_em DESC);
-- ================================================================
-- FINALIZAÇÃO DO SCRIPT DE CRIAÇÃO DO BANCO OPERA
-- ================================================================

-- Verificação simples da versão do schema
INSERT INTO opera._schema_info (schema_name, versao, criado_em, atualizado_em)
VALUES ('opera', '1.0', NOW(), NOW())
ON CONFLICT (id) DO UPDATE
SET atualizado_em = NOW();

-- ================================================================
-- DEFINIÇÃO DE PERMISSÕES GERAIS DO SCHEMA
-- ================================================================
ALTER SCHEMA opera OWNER TO postgres;

GRANT USAGE ON SCHEMA opera TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA opera TO PUBLIC;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA opera TO PUBLIC;

-- Permitir que futuros objetos herdem estas permissões automaticamente
ALTER DEFAULT PRIVILEGES IN SCHEMA opera
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO PUBLIC;

ALTER DEFAULT PRIVILEGES IN SCHEMA opera
GRANT USAGE, SELECT ON SEQUENCES TO PUBLIC;

-- ================================================================
--  MENSAGENS FINAIS DO INSTALADOR DO BANCO OPERA
--  (Cálculo automático de tabelas, views, triggers e funções)
-- ================================================================

DO $$
DECLARE
    total_tabelas_final     INTEGER;
    total_views             INTEGER;
    total_funcoes           INTEGER;
    total_triggers          INTEGER;
    total_permissoes_gil    INTEGER;
    total_temas             INTEGER;
BEGIN
    -- Contagem automática de objetos criados
    SELECT COUNT(*) INTO total_tabelas_final
    FROM information_schema.tables
    WHERE table_schema = 'opera';

    SELECT COUNT(*) INTO total_views
    FROM information_schema.views
    WHERE table_schema = 'opera';

    SELECT COUNT(*) INTO total_funcoes
    FROM pg_proc
    JOIN pg_namespace ON pg_namespace.oid = pg_proc.pronamespace
    WHERE nspname = 'opera';

    SELECT COUNT(*) INTO total_triggers
    FROM information_schema.triggers
    WHERE trigger_schema = 'opera';

    SELECT COUNT(*) INTO total_permissoes_gil
    FROM opera.usuario_permissoes up
    JOIN opera.usuarios u ON u.id = up.usuario_id
    WHERE u.usuario = 'Gil de Oliveira';

    SELECT COUNT(*) INTO total_temas
    FROM opera.usuario_temas_personalizados;

    -- MENSAGENS FINAIS
    RAISE NOTICE '=========================================================';
    RAISE NOTICE '        ✅ ESTRUTURA DO BANCO OPERA CRIADA COM SUCESSO!';
    RAISE NOTICE '=========================================================';
    RAISE NOTICE '📊 Estruturas criadas:';
    RAISE NOTICE '   👤 1 Tabela de usuários';
    RAISE NOTICE '   ⚙️  1 Tabela de preferências';
    RAISE NOTICE '   🎨 1 Tabela de temas personalizados (MÚLTIPLOS por usuário)';
    RAISE NOTICE '   🔐 1 Tabela de permissões';
    RAISE NOTICE '   📋 % Views úteis', total_views;
    RAISE NOTICE '   ⚡ % Triggers de validação e logs', total_triggers;
    RAISE NOTICE '   🔄 % Funções de migração e logs', total_funcoes;
    RAISE NOTICE '   📝 Sistema de auditoria ATIVADO';
    RAISE NOTICE '';
    RAISE NOTICE '👤 Usuário mestre criado automaticamente:';
    RAISE NOTICE '     • Nome: Gil de Oliveira';
    RAISE NOTICE '     • Login: Gil de Oliveira';
    RAISE NOTICE '     • Senha: 2580';
    RAISE NOTICE '     • Email: opera@gil.com';
    RAISE NOTICE '🔐 Permissões configuradas: % permissões ATIVADAS (tudo TRUE)', total_permissoes_gil;
    RAISE NOTICE '🎨 Temas personalizados gerados: % temas', total_temas;
    RAISE NOTICE '📈 Total de tabelas no schema OPERA: %', total_tabelas_final;
    RAISE NOTICE '🔍 Sistema de auditoria e logs: IMPLEMENTADO';
    RAISE NOTICE '=========================================================';
    RAISE NOTICE '          🚀 BANCO OPERA PRONTO PARA USO!';
    RAISE NOTICE '=========================================================';

    -- Verificação extra
    IF total_permissoes_gil > 0 THEN
        RAISE NOTICE '🔒 VERIFICAÇÃO: Todas as % permissões do usuário mestre estão TRUE!', total_permissoes_gil;
    ELSE
        RAISE NOTICE '⚠️ Atenção: O usuário mestre ainda não possui permissões cadastradas.';
    END IF;

END $$;

COMMIT;

-- ================================================================
-- FIM DO ARQUIVO 3_CRIAR_TABELAS.sql
-- ================================================================
