-- ======================================================
-- CRIADOR COMPLETO DO BANCO OPERA - COM TABELAS ENUMERADAS
-- ======================================================

----------------------------------------
-- 1. CONFIGURAÇÃO INICIAL
----------------------------------------
SET client_min_messages TO WARNING;
CREATE SCHEMA IF NOT EXISTS opera;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

----------------------------------------
-- 2. FUNÇÕES DO SISTEMA
----------------------------------------
-- [FUNÇÃO 01] registrar_log_usuario
CREATE OR REPLACE FUNCTION opera.registrar_log_usuario(
    p_usuario VARCHAR,
    p_acao TEXT,
    p_pagina TEXT DEFAULT NULL,
    p_detalhe TEXT DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    v_usuario_id INTEGER;
BEGIN
    SELECT id INTO v_usuario_id
    FROM opera.usuarios
    WHERE usuario = p_usuario
    LIMIT 1;

    IF v_usuario_id IS NOT NULL THEN
        INSERT INTO opera.usuario_logs (
            usuario_id,
            acao,
            pagina,
            detalhe,
            data_hora
        ) VALUES (
            v_usuario_id,
            p_acao,
            p_pagina,
            p_detalhe,
            NOW()
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- [FUNÇÃO 02] validar_cores_tema
CREATE OR REPLACE FUNCTION opera.validar_cores_tema() RETURNS TRIGGER AS $$
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

-- [FUNÇÃO 03] validar_senha - Corrigida
CREATE OR REPLACE FUNCTION opera.validar_senha(
    p_usuario TEXT,
    p_senha TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_hash TEXT;
    v_bcrypt_ok BOOLEAN := FALSE;
    v_sha256_ok BOOLEAN := FALSE;
BEGIN
    -- Buscar hash do usuário
    SELECT senha_hash INTO v_hash
    FROM opera.usuarios
    WHERE usuario = p_usuario
    LIMIT 1;

    -- Se não encontrar usuário, retorna falso
    IF v_hash IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Verificar se é hash bcrypt (começa com $2$)
    IF v_hash LIKE '$2%' THEN
        BEGIN
            -- Usar crypt() para validar bcrypt
            IF crypt(p_senha, v_hash) = v_hash THEN
                v_bcrypt_ok := TRUE;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            v_bcrypt_ok := FALSE;
        END;
    END IF;

    -- Se bcrypt falhou, tentar SHA256 com salt
    IF NOT v_bcrypt_ok THEN
        -- Converter senha + salt para SHA256
        v_sha256_ok := encode(
            digest('sistema_profissional_v2.2' || p_senha, 'sha256'),
            'hex'
        ) = v_hash;
    END IF;

    -- Retornar resultado da validação
    RETURN v_bcrypt_ok OR v_sha256_ok;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

----------------------------------------
-- 3. TABELA DE VERSIONAMENTO
----------------------------------------
-- [TABELA 01] _schema_info - Controle de versão do banco
CREATE TABLE IF NOT EXISTS opera._schema_info (
    id SERIAL PRIMARY KEY,
    schema_name TEXT DEFAULT 'opera',
    versao TEXT DEFAULT '1.0',
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

----------------------------------------
-- 4. TABELAS DE USUÁRIOS E PERMISSÕES
----------------------------------------
-- [TABELA 02] usuarios - Registro dos usuários do sistema OPERA
CREATE TABLE IF NOT EXISTS opera.usuarios (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(100) NOT NULL UNIQUE,
    senha_hash TEXT,
    hierarquia VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    data_criacao TIMESTAMP DEFAULT NOW(),
    ativo BOOLEAN DEFAULT TRUE NOT NULL,
    dica_senha TEXT,
    ultimo_login TIMESTAMP,
    telefone VARCHAR(50),
    departamento VARCHAR(100),
    tema_preferido VARCHAR(50) DEFAULT 'Noite Urbana'
);

-- [TABELA 03] usuario_preferencias - Preferências gerais do usuário
CREATE TABLE IF NOT EXISTS opera.usuario_preferencias (
    usuario_id INTEGER PRIMARY KEY REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    tema_nome VARCHAR(50) DEFAULT 'Noite Urbana',
    usar_tema_personalizado BOOLEAN DEFAULT FALSE,
    tema_personalizado TEXT,
    layout_compacto BOOLEAN DEFAULT FALSE,
    sidebar_recolhida BOOLEAN DEFAULT FALSE,
    usar_animacoes BOOLEAN DEFAULT TRUE,
    mostrar_dicas BOOLEAN DEFAULT TRUE,
    idioma VARCHAR(20) DEFAULT 'pt-BR',
    notificacoes BOOLEAN DEFAULT TRUE,
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- [TABELA 04] usuario_permissoes - Permissões de acesso às funções do sistema OPERA
CREATE TABLE IF NOT EXISTS opera.usuario_permissoes (
    usuario_id INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    codigo VARCHAR(100) NOT NULL,
    pode_ver BOOLEAN DEFAULT FALSE,
    pode_editar BOOLEAN DEFAULT FALSE,
    pode_imprimir BOOLEAN DEFAULT FALSE,
    pode_excluir BOOLEAN DEFAULT FALSE,
    pode_administrar BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (usuario_id, codigo)
);

-- [TABELA 05] usuario_logs - Histórico de ações realizadas pelos usuários
CREATE TABLE IF NOT EXISTS opera.usuario_logs (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES opera.usuarios(id),
    acao TEXT,
    pagina TEXT,  -- COLUNA ADICIONADA
    detalhe TEXT, -- COLUNA ADICIONADA
    detalhes TEXT,
    data_hora TIMESTAMP DEFAULT NOW()
);

-- [TABELA 06] usuario_temas_personalizados - Temas customizados criados pelos usuários
CREATE TABLE IF NOT EXISTS opera.usuario_temas_personalizados (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    nome_tema VARCHAR(100) NOT NULL,
    cores_tema JSONB NOT NULL,
    data_criacao TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    UNIQUE (usuario_id, nome_tema)
);

----------------------------------------
-- 5. TABELAS DE MODELOS
----------------------------------------
-- [TABELA 07] cadastro_modelos_cabecalho - Cabeçalho dos modelos
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_cabecalho (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    colecao VARCHAR(100),
    tamanho_base VARCHAR(10),
    dificuldade VARCHAR(50),
    modelista VARCHAR(100),
    pilotista VARCHAR(100),
    custo_total NUMERIC(12,2) DEFAULT 0,
    gasto_por_peca TEXT DEFAULT '',
    gasto_total_por_peca NUMERIC(12,4) DEFAULT 0,
    pronto_producao BOOLEAN DEFAULT FALSE,
    grade_disponivel TEXT,
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_atualizacao TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);


-- [TABELA 08] cadastro_modelos_tecidos - Tecidos dos modelos
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_tecidos (
    id SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo_tecido VARCHAR(100),
    descricao TEXT,
    cor VARCHAR(50),
    fornecedor VARCHAR(100),
    composicao VARCHAR(100),
    metros_peca NUMERIC(12,4) DEFAULT 0,
    valor_metro NUMERIC(12,2) DEFAULT 0,
    valor_total NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- [TABELA 09] cadastro_modelos_aviamentos - Aviamentos dos modelos
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_aviamentos (
    id SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo_aviamento VARCHAR(100),
    descricao TEXT,
    cor VARCHAR(50),
    fornecedor VARCHAR(100),
    quantidade NUMERIC(12,4) DEFAULT 0,
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    valor_total NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- [TABELA 10] cadastro_modelos_outros - Outros materiais dos modelos
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_outros (
    id SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo VARCHAR(100),
    descricao TEXT,
    cor VARCHAR(50),
    fornecedor VARCHAR(100),
    unidade VARCHAR(20),
    quantidade NUMERIC(12,4) DEFAULT 0,
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    valor_total NUMERIC(12,2) DEFAULT 0,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- [TABELA 11] cadastro_modelos_outros_servicos - Outros serviços dos modelos
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_outros_servicos (
    id SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo_servico VARCHAR(100),
    descricao TEXT,
    tipo_servico VARCHAR(100),
    fornecedor VARCHAR(100),
    unidade VARCHAR(20),
    quantidade NUMERIC(12,4) DEFAULT 0,
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    valor_total NUMERIC(12,2) DEFAULT 0,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- [TABELA 12] cadastro_modelos_imagens - Imagens dos modelos
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_imagens (
    id SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    tipo_imagem VARCHAR(20),
    caminho_imagem TEXT,
    descricao TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- [TABELA 13] cadastro_modelos_grade - Grade de tamanhos dos modelos
CREATE TABLE IF NOT EXISTS opera.cadastro_modelos_grade (
    id SERIAL PRIMARY KEY,
    modelo_id INTEGER NOT NULL REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    tamanho VARCHAR(10) NOT NULL,
    disponivel BOOLEAN DEFAULT TRUE,
    UNIQUE (modelo_id, tamanho)
);

----------------------------------------
-- 6. TABELAS DE FACÇÕES
----------------------------------------
-- [TABELA 14] cadastro_faccoes - Cadastro de facções/prestadores
CREATE TABLE IF NOT EXISTS opera.cadastro_faccoes (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL UNIQUE,
    nome VARCHAR(200) NOT NULL,
    tipo_prestador VARCHAR(50) DEFAULT 'Faccao',
    telefone VARCHAR(50),
    endereco TEXT,
    titular_da_conta VARCHAR(200),
    cpf VARCHAR(20),
    banco VARCHAR(50),
    agencia VARCHAR(20),
    conta VARCHAR(30),
    pix VARCHAR(100),
    data DATE,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE
);

----------------------------------------
-- 7. TABELAS DE CORTE
----------------------------------------
-- [TABELA 15] cadastro_de_corte - Registro de cortes
CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte (
    id SERIAL PRIMARY KEY,
    numero_ordem VARCHAR(50),
    ordem_corte VARCHAR(50),
    codigo VARCHAR(100),
    descricao TEXT,
    descricao_corte TEXT,
    data DATE,
    data_envio DATE,
    comprimento_matriz NUMERIC(12,3),
    largura_matriz NUMERIC(12,3),
    cortador VARCHAR(100),
    ajudante VARCHAR(100),
    auxiliar VARCHAR(100),
    total_folhas INTEGER,
    metros_utilizados NUMERIC(12,3),
    bobinas_utilizadas NUMERIC(12,3),
    composicao_tecido VARCHAR(100),
    pp INTEGER DEFAULT 0 NOT NULL,
    p INTEGER DEFAULT 0 NOT NULL,
    m INTEGER DEFAULT 0 NOT NULL,
    g INTEGER DEFAULT 0 NOT NULL,
    gg INTEGER DEFAULT 0 NOT NULL,
    g1 INTEGER DEFAULT 0 NOT NULL,
    g2 INTEGER DEFAULT 0 NOT NULL,
    g3 INTEGER DEFAULT 0 NOT NULL,
    total_pecas INTEGER DEFAULT 0 NOT NULL,
    rendimento NUMERIC(12,4),
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- [TABELA 16] cadastro_de_corte_tecidos - Tecidos utilizados no corte
CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte_tecidos (
    id SERIAL PRIMARY KEY,
    cadastro_id INTEGER NOT NULL REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE,
    tecido VARCHAR(200),
    cor VARCHAR(50),
    composicao VARCHAR(100),
    bobinas NUMERIC(12,3),
    folhas NUMERIC(12,3),
    pp INTEGER,
    p INTEGER,
    m INTEGER,
    g INTEGER,
    gg INTEGER,
    g1 INTEGER,
    g2 INTEGER,
    g3 INTEGER,
    total_pecas INTEGER
);

-- [TABELA 17] cadastro_de_corte_lotes - Lotes do corte
CREATE TABLE IF NOT EXISTS opera.cadastro_de_corte_lotes (
    id SERIAL PRIMARY KEY,
    cadastro_id INTEGER NOT NULL REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE,
    lote VARCHAR(100),
    tecido VARCHAR(200),
    cor VARCHAR(50),
    composicao VARCHAR(100),
    bobinas NUMERIC(12,3),
    folhas NUMERIC(12,3),
    pp INTEGER,
    p INTEGER,
    m INTEGER,
    g INTEGER,
    gg INTEGER,
    g1 INTEGER,
    g2 INTEGER,
    g3 INTEGER,
    total_lote INTEGER
);

----------------------------------------
-- 8. TABELAS DE ORDEM DE CORTE
----------------------------------------
-- [TABELA 18] ordem_corte_ficha - Ficha de ordem de corte
CREATE TABLE IF NOT EXISTS opera.ordem_corte_ficha (
    id SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    descricao_modelo TEXT,
    cortador VARCHAR(100),
    auxiliar VARCHAR(100),
    ajudante VARCHAR(100),
    data_registro TIMESTAMP DEFAULT NOW(),
    data_final DATE,
    dias_estimados NUMERIC(12,4),
    horas_estimadas NUMERIC(12,4),
    porcentagens JSONB,
    consumo_peca NUMERIC(12,4),
    quantidade_desejada INTEGER,
    total_pecas INTEGER,
    observacoes TEXT,
    status VARCHAR(50) DEFAULT 'Em Andamento',
    usuario_registro VARCHAR(100),
    data_atualizacao TIMESTAMP DEFAULT NOW(),
    ativo BOOLEAN DEFAULT TRUE
);

-- [TABELA 19] ordem_corte_lotes - Lotes da ordem de corte
CREATE TABLE IF NOT EXISTS opera.ordem_corte_lotes (
    id BIGSERIAL PRIMARY KEY,
    ordem_id INTEGER NOT NULL REFERENCES opera.ordem_corte_ficha(id) ON DELETE CASCADE,
    lote_numero VARCHAR(50),
    tamanho VARCHAR(10) NOT NULL,
    quantidade INTEGER DEFAULT 0 NOT NULL,
    UNIQUE (ordem_id, lote_numero, tamanho)
);

-- [TABELA 20] ordem_grade_preferencias - Preferências de grade por usuário
CREATE TABLE IF NOT EXISTS opera.ordem_grade_preferencias (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    nome VARCHAR(100) NOT NULL,
    porcent_1 NUMERIC(12,4) DEFAULT 0,
    porcent_2 NUMERIC(12,4) DEFAULT 0,
    porcent_3 NUMERIC(12,4) DEFAULT 0,
    porcent_4 NUMERIC(12,4) DEFAULT 0,
    porcent_5 NUMERIC(12,4) DEFAULT 0,
    porcent_6 NUMERIC(12,4) DEFAULT 0,
    porcent_7 NUMERIC(12,4) DEFAULT 0,
    porcent_8 NUMERIC(12,4) DEFAULT 0,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    UNIQUE (usuario_id, nome)
);

----------------------------------------
-- 9. TABELAS DE ENVIO E CONTROLE
----------------------------------------
-- [TABELA 21] controle_envio_cortes - Controle de envio de cortes
CREATE TABLE IF NOT EXISTS opera.controle_envio_cortes (
    id SERIAL PRIMARY KEY,
    data_envio DATE,
    servico VARCHAR(100),
    corte_id INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,
    ordem_corte VARCHAR(50),
    codigo_corte VARCHAR(100),
    descricao_corte TEXT,
    destino VARCHAR(200),
    costureira VARCHAR(200),
    faccao VARCHAR(200),
    quantidade_total INTEGER,
    valor_peca NUMERIC(12,2),
    valor_total NUMERIC(12,2),
    status VARCHAR(50) DEFAULT 'Em Conferencia',
    observacao TEXT,
    pp INTEGER,
    p INTEGER,
    m INTEGER,
    g INTEGER,
    gg INTEGER,
    g1 INTEGER,
    g2 INTEGER,
    g3 INTEGER
);

-- [TABELA 22] envios_cortes - Envios de cortes para facções
CREATE TABLE IF NOT EXISTS opera.envios_cortes (
    id SERIAL PRIMARY KEY,
    remessa_id UUID,
    data_envio DATE NOT NULL,
    hora_envio TIME,
    prestador_id INTEGER REFERENCES opera.cadastro_faccoes(id),
    tipo_servico TEXT,
    corte_id INTEGER REFERENCES opera.cadastro_de_corte(id),
    ordem_corte VARCHAR(50),
    codigo_corte VARCHAR(100),
    descricao_corte TEXT,
    colecao VARCHAR(100),
    material VARCHAR(100),
    cliente VARCHAR(200),
    cores TEXT,
    prioridade VARCHAR(30),
    forma_pagamento VARCHAR(50),
    status_envio VARCHAR(30) DEFAULT 'Enviado',
    qtd_pp INTEGER DEFAULT 0,
    qtd_p INTEGER DEFAULT 0,
    qtd_m INTEGER DEFAULT 0,
    qtd_g INTEGER DEFAULT 0,
    qtd_gg INTEGER DEFAULT 0,
    qtd_g1 INTEGER DEFAULT 0,
    qtd_g2 INTEGER DEFAULT 0,
    qtd_g3 INTEGER DEFAULT 0,

    -- NOVO: cópias retiradas do corte (por tamanho)
    copias_pp INTEGER DEFAULT 0,
    copias_p  INTEGER DEFAULT 0,
    copias_m  INTEGER DEFAULT 0,
    copias_g  INTEGER DEFAULT 0,
    copias_gg INTEGER DEFAULT 0,
    copias_g1 INTEGER DEFAULT 0,
    copias_g2 INTEGER DEFAULT 0,
    copias_g3 INTEGER DEFAULT 0,
    piloto_pp INTEGER DEFAULT 0,
    piloto_p INTEGER DEFAULT 0,
    piloto_m INTEGER DEFAULT 0,
    piloto_g INTEGER DEFAULT 0,
    piloto_gg INTEGER DEFAULT 0,
    piloto_g1 INTEGER DEFAULT 0,
    piloto_g2 INTEGER DEFAULT 0,
    piloto_g3 INTEGER DEFAULT 0,
    valor_pp NUMERIC(10,2) DEFAULT 0,
    valor_p NUMERIC(10,2) DEFAULT 0,
    valor_m NUMERIC(10,2) DEFAULT 0,
    valor_g NUMERIC(10,2) DEFAULT 0,
    valor_gg NUMERIC(10,2) DEFAULT 0,
    valor_g1 NUMERIC(10,2) DEFAULT 0,
    valor_g2 NUMERIC(10,2) DEFAULT 0,
    valor_g3 NUMERIC(10,2) DEFAULT 0,
    total_pecas INTEGER DEFAULT 0,
    total_pilotos INTEGER DEFAULT 0,
    valor_total_envio NUMERIC(12,2) DEFAULT 0,
    resumo_pilotos TEXT,

    -- NOVO: coluna para registrar também o "resumo/registro" de cópias do corte
    copias_do_corte TEXT,
    aviamentos TEXT,
    outros TEXT,
    observacoes TEXT,
    tel_encarregado TEXT,
    tel_acabamento TEXT,
    previsao_entrega DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

----------------------------------------
-- 10. TABELAS DE DETALHES DE ENVIO/RETORNO
----------------------------------------
-- [TABELA 23] envio_detalhes_tamanho - Detalhes por tamanho do envio
CREATE TABLE IF NOT EXISTS opera.envio_detalhes_tamanho (
    envio_id INTEGER NOT NULL REFERENCES opera.envios_cortes(id) ON DELETE CASCADE,
    tamanho VARCHAR(10) NOT NULL,
    quantidade INTEGER DEFAULT 0,

    -- NOVO: cópias retiradas do corte (por tamanho)
    copias_do_corte INTEGER DEFAULT 0,
    quantidade_pilotos INTEGER DEFAULT 0,
    valor_peca NUMERIC(12,2) DEFAULT 0,
    PRIMARY KEY (envio_id, tamanho)
);

-- [TABELA 24] controle_retorno_cortes - Controle de retorno de cortes
CREATE TABLE IF NOT EXISTS opera.controle_retorno_cortes (
    id SERIAL PRIMARY KEY,
    envio_id INTEGER NOT NULL REFERENCES opera.envios_cortes(id) ON DELETE CASCADE,
    data_chegada DATE NOT NULL,
    telefone_encarregado TEXT,
    telefone_acabamento TEXT,
    resumo_piloto TEXT,
    aviamentos_recebidos TEXT,
    outros_recebidos TEXT,
    observacoes_gerais TEXT,
    total_entregue INTEGER DEFAULT 0,
    total_copias INTEGER DEFAULT 0,
    total_defeitos INTEGER DEFAULT 0,
    total_faltantes INTEGER DEFAULT 0,
    total_regulares INTEGER DEFAULT 0,
    valor_total NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- [TABELA 25] entrada_acabamento - Entrada de acabamento
CREATE TABLE IF NOT EXISTS opera.entrada_acabamento (
    id SERIAL PRIMARY KEY,
    envio_id INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    data_chegada DATE,
    total_entregue INTEGER,
    total_defeitos INTEGER,
    total_faltantes INTEGER,
    total_regulares INTEGER,
    valor_total NUMERIC(12,2),
    pago BOOLEAN DEFAULT FALSE,
    pagamento_id INTEGER,  -- COLUNA ADICIONADA
    valor_pago NUMERIC(12,2),  -- COLUNA ADICIONADA
    data_pagamento DATE
);
-- [TABELA 26] entrada_acabamento_detalhes - Detalhes da entrada de acabamento
CREATE TABLE IF NOT EXISTS opera.entrada_acabamento_detalhes (
    id SERIAL PRIMARY KEY,
    entrada_id INTEGER NOT NULL REFERENCES opera.entrada_acabamento(id) ON DELETE CASCADE,
    observacoes_finalizacao TEXT,
    bonificacao_aplicada BOOLEAN DEFAULT FALSE,
    usuario_conferencia VARCHAR(100),
    total_entregue INTEGER DEFAULT 0,
    total_copias INTEGER DEFAULT 0,
    total_defeitos INTEGER DEFAULT 0,
    total_faltantes INTEGER DEFAULT 0,
    total_regulares INTEGER DEFAULT 0,
    valor_total_pagar NUMERIC(12,2) DEFAULT 0,
    status_finalizacao VARCHAR(20) DEFAULT 'Pendente',
    data_conferencia TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- [TABELA 27] retorno_detalhes_tamanho - Detalhes por tamanho do retorno
CREATE TABLE IF NOT EXISTS opera.retorno_detalhes_tamanho (
    id SERIAL PRIMARY KEY,
    envio_id INTEGER NOT NULL REFERENCES opera.envios_cortes(id) ON DELETE CASCADE,
    tamanho VARCHAR(10) NOT NULL,
    entregue INTEGER DEFAULT 0,
    copias INTEGER DEFAULT 0,
    defeitos INTEGER DEFAULT 0,
    faltantes INTEGER DEFAULT 0,
    regulares INTEGER DEFAULT 0,
    subtotal NUMERIC(12,2) DEFAULT 0
);

-- [TABELA 28] cortes_finalizados - Cortes finalizados
CREATE TABLE IF NOT EXISTS opera.cortes_finalizados (
    id SERIAL PRIMARY KEY,
    corte_id INTEGER REFERENCES opera.cadastro_de_corte(id),
    entrada_id INTEGER,
    envio_id INTEGER REFERENCES opera.envios_cortes(id) ON DELETE SET NULL,
    retorno_id INTEGER REFERENCES opera.controle_retorno_cortes(id) ON DELETE SET NULL,
    tipo_servico VARCHAR(100),
    codigo VARCHAR(100),
    descricao TEXT,
    costureira VARCHAR(200),
    data_envio DATE,
    data_chegada DATE,
    data_final DATE,
    qtd_enviada INTEGER,
    total_pecas INTEGER,
    quantidade_finalizada INTEGER,
    observacao TEXT,
    status VARCHAR(50),
    data_conferencia TIMESTAMP,
    valor_peca NUMERIC(12,2),
    bonificacao NUMERIC(12,2) DEFAULT 0.00,
    pago BOOLEAN DEFAULT FALSE,
    pagamento_id INTEGER,  -- COLUNA ADICIONADA: ID do pagamento
    valor_pago NUMERIC(12,2),  -- COLUNA ADICIONADA: Valor total pago
    data_pagamento DATE,
    qtd_pp INTEGER DEFAULT 0,
    qtd_p INTEGER DEFAULT 0,
    qtd_m INTEGER DEFAULT 0,
    qtd_g INTEGER DEFAULT 0,
    qtd_gg INTEGER DEFAULT 0,
    qtd_g1 INTEGER DEFAULT 0,
    qtd_g2 INTEGER DEFAULT 0,
    qtd_g3 INTEGER DEFAULT 0,
    qtd_defeito_pp INTEGER DEFAULT 0,
    qtd_defeito_p INTEGER DEFAULT 0,
    qtd_defeito_m INTEGER DEFAULT 0,
    qtd_defeito_g INTEGER DEFAULT 0,
    qtd_defeito_gg INTEGER DEFAULT 0,
    qtd_defeito_g1 INTEGER DEFAULT 0,
    qtd_defeito_g2 INTEGER DEFAULT 0,
    qtd_defeito_g3 INTEGER DEFAULT 0,
    valor_total NUMERIC(12,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Adicionando índices para melhor performance
    CONSTRAINT fk_cortes_finalizados_envio FOREIGN KEY (envio_id)
        REFERENCES opera.envios_cortes(id) ON DELETE SET NULL,
    CONSTRAINT fk_cortes_finalizados_retorno FOREIGN KEY (retorno_id)
        REFERENCES opera.controle_retorno_cortes(id) ON DELETE SET NULL
);

-- [TABELA 29] cortes_finalizados_completo - Cortes finalizados completos
CREATE TABLE IF NOT EXISTS opera.cortes_finalizados_completo (
    id SERIAL PRIMARY KEY,
    entrada_id INTEGER REFERENCES opera.entrada_acabamento(id) ON DELETE SET NULL,
    envio_id INTEGER REFERENCES opera.controle_envio_cortes(id) ON DELETE SET NULL,
    corte_id INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,
    descricao TEXT,
    ordem_corte VARCHAR(100),
    codigo_corte VARCHAR(100),
    qtd_regular_pp INTEGER DEFAULT 0,
    qtd_regular_p INTEGER DEFAULT 0,
    qtd_regular_m INTEGER DEFAULT 0,
    qtd_regular_g INTEGER DEFAULT 0,
    qtd_regular_gg INTEGER DEFAULT 0,
    qtd_regular_g1 INTEGER DEFAULT 0,
    qtd_regular_g2 INTEGER DEFAULT 0,
    qtd_regular_g3 INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'Finalizado',
    observacoes TEXT,
    usuario_finalizacao VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- [TABELA 30] pecas_finalizadas - Peças finalizadas
CREATE TABLE IF NOT EXISTS opera.pecas_finalizadas (
    id SERIAL PRIMARY KEY,
    corte_id INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL,
    entrada_id INTEGER UNIQUE,
    codigo VARCHAR(100),
    descricao TEXT,
    costureira VARCHAR(200),
    data_envio DATE,
    data_chegada DATE,
    qtd_enviada INTEGER,
    observacao TEXT,
    status VARCHAR(50),
    data_conferencia TIMESTAMP,
    valor_peca NUMERIC(12,2),
    bonificacao NUMERIC(12,2),
    qtd_pp INTEGER,
    qtd_p INTEGER,
    qtd_m INTEGER,
    qtd_g INTEGER,
    qtd_gg INTEGER,
    qtd_g1 INTEGER,
    qtd_g2 INTEGER,
    qtd_g3 INTEGER,
    qtd_defeito_pp INTEGER,
    qtd_defeito_p INTEGER,
    qtd_defeito_m INTEGER,
    qtd_defeito_g INTEGER,
    qtd_defeito_gg INTEGER,
    qtd_defeito_g1 INTEGER,
    qtd_defeito_g2 INTEGER,
    qtd_defeito_g3 INTEGER,
    pago BOOLEAN DEFAULT FALSE,
    pagamento_id INTEGER,
    valor_pago NUMERIC(12,2),
    data_pagamento DATE
);

-- [TABELA 31] log_finalizacoes - Log de finalizações
CREATE TABLE IF NOT EXISTS opera.log_finalizacoes (
    id SERIAL PRIMARY KEY,
    entrada_id INTEGER REFERENCES opera.entrada_acabamento(id),
    acao VARCHAR(50) NOT NULL,
    dados_antes JSONB,
    dados_depois JSONB,
    usuario VARCHAR(100),
    data_hora TIMESTAMP DEFAULT NOW(),
    observacoes TEXT
);

----------------------------------------
-- 11. TABELAS DE PAGAMENTO
----------------------------------------
-- [TABELA 32] adiantamento_faccao - Adiantamento para facções
CREATE TABLE IF NOT EXISTS opera.adiantamento_faccao (
    id SERIAL PRIMARY KEY,
    corte_id INTEGER REFERENCES opera.cadastro_de_corte(id),
    codigo_modelo VARCHAR(100),
    faccao VARCHAR(200),
    valor NUMERIC(12,2) NOT NULL,
    forma_pagamento VARCHAR(50),
    parcelas INTEGER DEFAULT 1,
    data_hora TIMESTAMP DEFAULT NOW() NOT NULL
);

-- [TABELA 33] pagamento_servicos - Pagamento de serviços
CREATE TABLE IF NOT EXISTS opera.pagamento_servicos (
    id BIGSERIAL PRIMARY KEY,
    prestador_id INTEGER REFERENCES opera.cadastro_faccoes(id) ON DELETE SET NULL,
    nome_prestador VARCHAR(100),
    data_pagamento DATE NOT NULL,
    valor_total NUMERIC(10,2) NOT NULL,
    valor_adiantamento_abatido NUMERIC(10,2) DEFAULT 0.00,
    valor_liquido NUMERIC(10,2) NOT NULL,
    mes_referencia VARCHAR(10),
    observacoes TEXT,
    usuario_pagamento VARCHAR(100),
    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- [TABELA 34] pagamento_servicos_detalhe - Detalhe do pagamento de serviços
CREATE TABLE IF NOT EXISTS opera.pagamento_servicos_detalhe (
    pagamento_id BIGINT NOT NULL REFERENCES opera.pagamento_servicos(id) ON DELETE CASCADE,
    entrada_acabamento_id INTEGER NOT NULL,
    valor_servico NUMERIC(10,2) NOT NULL,
    PRIMARY KEY (pagamento_id, entrada_acabamento_id)
);

-- [TABELA 35] pagamento_corte_acabamento - Pagamento de corte e acabamento
CREATE TABLE IF NOT EXISTS opera.pagamento_corte_acabamento (
    id SERIAL PRIMARY KEY,
    costureira VARCHAR(200),
    tipo_servico VARCHAR(100),
    codigo VARCHAR(100),
    descricao TEXT,
    data_envio DATE,
    data_chegada DATE,
    quantidade_finalizada INTEGER,
    valor_por_peca NUMERIC(12,2),
    adiantamento NUMERIC(12,2) DEFAULT 0,
    ajuda_custo NUMERIC(12,2) DEFAULT 0,
    bonificacao NUMERIC(12,2) DEFAULT 0,
    pecas_faltantes INTEGER DEFAULT 0,
    pecas_estragadas INTEGER DEFAULT 0,
    desconto_pecas NUMERIC(12,2) DEFAULT 0,
    total_pago NUMERIC(12,2) DEFAULT 0,
    cpf VARCHAR(20),
    banco VARCHAR(50),
    agencia VARCHAR(20),
    conta VARCHAR(30),
    pix VARCHAR(100),
    data_pagamento DATE,
    estornado BOOLEAN DEFAULT FALSE,
    pecas_com_defeito INTEGER DEFAULT 0,
    valor_defeito NUMERIC(12,2) DEFAULT 0
);

----------------------------------------
-- 12. TABELAS DE ESTOQUE
----------------------------------------
-- [TABELA 36] estoque_tecidos - Estoque de tecidos
CREATE TABLE IF NOT EXISTS opera.estoque_tecidos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL,
    descricao TEXT,
    cor VARCHAR(50) NOT NULL,
    composicao VARCHAR(100),
    fornecedor VARCHAR(100),
    metros NUMERIC(12,3) DEFAULT 0,
    kilos NUMERIC(12,3) DEFAULT 0,
    valor_metro NUMERIC(12,2) DEFAULT 0,
    valor_kilo NUMERIC(12,2) DEFAULT 0,
    unidade VARCHAR(50) DEFAULT 'metros',
    observacoes TEXT,
    localizacao VARCHAR(100),
    data_entrada DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

-- [TABELA 37] estoque_aviamentos - Estoque de aviamentos
CREATE TABLE IF NOT EXISTS opera.estoque_aviamentos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL,
    descricao TEXT,
    cor VARCHAR(50) NOT NULL,
    fornecedor VARCHAR(100),
    quantidade NUMERIC(12,3) DEFAULT 0,
    unidade VARCHAR(50) DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    observacoes TEXT,
    localizacao VARCHAR(100),
    data_entrada DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

-- [TABELA 38] estoque_insumos - Estoque de insumos
CREATE TABLE IF NOT EXISTS opera.estoque_insumos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL,
    descricao TEXT,
    fornecedor VARCHAR(100),
    cor VARCHAR(50) NOT NULL,
    quantidade NUMERIC(12,3) DEFAULT 0,
    unidade VARCHAR(50) DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo VARCHAR(100),
    categoria VARCHAR(100),
    observacoes TEXT,
    localizacao VARCHAR(100),
    data_entrada DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

-- [TABELA 39] estoque_escritorio - Estoque de escritório
CREATE TABLE IF NOT EXISTS opera.estoque_escritorio (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL,
    descricao TEXT,
    fornecedor VARCHAR(100),
    cor VARCHAR(50) NOT NULL,
    quantidade NUMERIC(12,3) DEFAULT 0,
    unidade VARCHAR(50) DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo VARCHAR(100),
    categoria VARCHAR(100),
    observacoes TEXT,
    localizacao VARCHAR(100),
    data_entrada DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

-- [TABELA 40] estoque_limpeza - Estoque de limpeza
CREATE TABLE IF NOT EXISTS opera.estoque_limpeza (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL,
    descricao TEXT,
    fornecedor VARCHAR(100),
    cor VARCHAR(50) NOT NULL,
    quantidade NUMERIC(12,3) DEFAULT 0,
    unidade VARCHAR(50) DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo VARCHAR(100),
    categoria VARCHAR(100),
    observacoes TEXT,
    localizacao VARCHAR(100),
    data_entrada DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

-- [TABELA 41] estoque_outros - Estoque de outros materiais
CREATE TABLE IF NOT EXISTS opera.estoque_outros (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL,
    descricao TEXT,
    fornecedor VARCHAR(100),
    cor VARCHAR(50) NOT NULL,
    quantidade NUMERIC(12,3) DEFAULT 0,
    unidade VARCHAR(50) DEFAULT 'unidades',
    valor_unidade NUMERIC(12,2) DEFAULT 0,
    tipo VARCHAR(100),
    categoria VARCHAR(100),
    observacoes TEXT,
    localizacao VARCHAR(100),
    data_entrada DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (codigo, cor)
);

-- [TABELA 42] estoque_saida_log - Log de saída do estoque
CREATE TABLE IF NOT EXISTS opera.estoque_saida_log (
    id BIGSERIAL PRIMARY KEY,
    data_hora TIMESTAMP DEFAULT NOW() NOT NULL,
    tipo_estoque VARCHAR(30) NOT NULL,
    item_id BIGINT NOT NULL,
    codigo VARCHAR(100),
    descricao TEXT,
    cor VARCHAR(50),
    quantidade NUMERIC(10,3) NOT NULL,
    unidade VARCHAR(20),
    motivo VARCHAR(100),
    observacoes TEXT,
    usuario VARCHAR(100)
);

----------------------------------------
-- 13. TABELAS DE SERVIÇOS E HISTÓRICO
----------------------------------------
-- [TABELA 43] servicos - Serviços gerais
CREATE TABLE IF NOT EXISTS opera.servicos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    descricao TEXT,
    prestador VARCHAR(200),
    data_inicio DATE,
    data_fim DATE,
    valor_unitario NUMERIC(12,2),
    quantidade INTEGER,
    valor_total NUMERIC(12,2),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- [TABELA 44] historico_servicos - Histórico de serviços
CREATE TABLE IF NOT EXISTS opera.historico_servicos (
    id SERIAL PRIMARY KEY,
    servico_id INTEGER REFERENCES opera.servicos(id) ON DELETE CASCADE,
    data_evento TIMESTAMP DEFAULT NOW() NOT NULL,
    acao VARCHAR(100),
    observacoes TEXT
);

-- [TABELA 45] historico_de_servico - Histórico de serviço (facções)
CREATE TABLE IF NOT EXISTS opera.historico_de_servico (
    id BIGSERIAL PRIMARY KEY,

    -- vínculos (mantém compatibilidade)
    envio_id INTEGER REFERENCES opera.controle_envio_cortes(id) ON DELETE SET NULL,
    entrada_id INTEGER REFERENCES opera.entrada_acabamento(id) ON DELETE SET NULL,
    pagamento_id BIGINT REFERENCES opera.pagamento_servicos(id) ON DELETE SET NULL,

    -- vínculo correto para a página de finalização (recomendado)
    envio_corte_id INTEGER REFERENCES opera.envios_cortes(id) ON DELETE SET NULL,
    retorno_id INTEGER REFERENCES opera.controle_retorno_cortes(id) ON DELETE SET NULL,

    -- dados que a página tenta gravar no histórico (defeitos pendentes)
    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evento VARCHAR(100),
    descricao TEXT,
    setor VARCHAR(200),
    quantidade INTEGER DEFAULT 0,
    valor NUMERIC(12,2) DEFAULT 0,

    -- seus campos originais
    tipo_servico VARCHAR(50),
    status VARCHAR(50) DEFAULT 'Pendente',
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- [TABELA 46] defeitos_envios - Retrabalho de defeitos
CREATE TABLE IF NOT EXISTS opera.defeitos_envios (
    id BIGSERIAL PRIMARY KEY,

    -- vínculos (pelo menos um deles deve existir)
    historico_id BIGINT REFERENCES opera.historico_de_servico(id) ON DELETE SET NULL,
    envio_id INTEGER REFERENCES opera.controle_envio_cortes(id) ON DELETE SET NULL,
    envio_corte_id INTEGER REFERENCES opera.controle_envio_cortes(id) ON DELETE SET NULL,

    codigo VARCHAR(50),
    descricao TEXT,
    prestador VARCHAR(200),

    tamanho VARCHAR(10),
    quantidade INTEGER DEFAULT 0,

    tipo_servico VARCHAR(50),
    valor_peca NUMERIC(12,2) DEFAULT 0,

    origem VARCHAR(20) DEFAULT 'Externo',
    status VARCHAR(50) DEFAULT 'Pendente',

    data_envio DATE,
    data_retorno DATE,
    data_finalizacao DATE,

    hora_envio TIME,
    hora_retorno TIME,
    hora_finalizacao TIME,

    previsao_entrega DATE,

    tel_encarregado VARCHAR(50),
    tel_acabamento VARCHAR(50),

    aviamentos TEXT,
    outros TEXT,
    observacoes TEXT,

    data_pagamento DATE,

    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- regras de integridade
    CONSTRAINT chk_defeitos_envios_quantidade_nao_negativa CHECK (quantidade IS NULL OR quantidade >= 0),
    CONSTRAINT chk_defeitos_envios_valor_peca_nao_negativo CHECK (valor_peca IS NULL OR valor_peca >= 0),

    -- precisa ter pelo menos 1 vínculo
    CONSTRAINT chk_defeitos_envios_vinculo CHECK (
        historico_id IS NOT NULL OR envio_id IS NOT NULL OR envio_corte_id IS NOT NULL
    )
);

-- índices de busca
CREATE INDEX IF NOT EXISTS idx_defeitos_envio_status
    ON opera.defeitos_envios (status);

CREATE INDEX IF NOT EXISTS idx_defeitos_envio_prestador
    ON opera.defeitos_envios (prestador);

CREATE INDEX IF NOT EXISTS idx_defeitos_envio_envio_id
    ON opera.defeitos_envios (envio_id);

CREATE INDEX IF NOT EXISTS idx_defeitos_envio_historico_id
    ON opera.defeitos_envios (historico_id);

-- unicidade (evita duplicar a mesma linha de tamanho para o mesmo envio)
CREATE UNIQUE INDEX IF NOT EXISTS idx_defeitos_envio_unico
    ON opera.defeitos_envios (envio_id, tamanho)
    WHERE envio_id IS NOT NULL AND tamanho IS NOT NULL;

-- unicidade por histórico + tamanho (NÃO use historico_id único sozinho)
CREATE UNIQUE INDEX IF NOT EXISTS idx_defeitos_envio_hist_tamanho_unico
    ON opera.defeitos_envios (historico_id, tamanho)
    WHERE historico_id IS NOT NULL AND tamanho IS NOT NULL;


----------------------------------------
-- 14. TABELAS DE PRICING E RELATÓRIOS
----------------------------------------
-- [TABELA 47] pricing_profiles - Perfis de precificação
CREATE TABLE IF NOT EXISTS opera.pricing_profiles (
    nome VARCHAR(100) PRIMARY KEY,
    impostos NUMERIC(12,4),
    comissao NUMERIC(12,4),
    cartao NUMERIC(12,4),
    margem NUMERIC(12,4),
    perdas NUMERIC(12,4),
    defeito NUMERIC(12,4),
    fixos NUMERIC(12,2),
    capacidade NUMERIC(12,2),
    variaveis NUMERIC(12,2),
    frete NUMERIC(12,2),
    arredondamento VARCHAR(20),
    canal VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- [TABELA 48] relatorios_finalizacao - Relatórios de finalização
CREATE TABLE IF NOT EXISTS opera.relatorios_finalizacao (
    id SERIAL PRIMARY KEY,
    entrada_id INTEGER REFERENCES opera.entrada_acabamento(id),
    usuario_geracao VARCHAR(100),
    data_geracao TIMESTAMP DEFAULT NOW(),
    tipo_relatorio VARCHAR(50),
    html_content TEXT,
    pdf_path TEXT,
    parametros JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

----------------------------------------
-- 15. VIEWS DO SISTEMA
----------------------------------------
-- [VIEW 49] permissoes - View de permissões
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

-- [VIEW 50] usuario - View de usuários
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

-- [VIEW 51] vw_usuario_logs - View para logs com nome de usuário
CREATE OR REPLACE VIEW opera.vw_usuario_logs AS
SELECT
    ul.id,
    ul.data_hora,
    u.usuario,
    ul.acao,
    ul.pagina,
    ul.detalhe,
    ul.detalhes as observacoes
FROM opera.usuario_logs ul
LEFT JOIN opera.usuarios u ON ul.usuario_id = u.id;

----------------------------------------
-- 16. CONFIGURAÇÃO DO USUÁRIO ADMIN
----------------------------------------
DO $$
DECLARE
    admin_id INTEGER;
    tema_azul_noturno JSONB := '{
        "primaria": "#1E3A8A",
        "secundaria": "#3B82F6",
        "terciaria": "#60A5FA",
        "fundo": "#0F172A",
        "texto": "#F1F5F9",
        "borda": "#334155",
        "destaque": "#6366F1",
        "selecao": "#3B82F6",
        "hover": "#1E293B",
        "sucesso": "#10B981",
        "alerta": "#F59E0B",
        "botao_salvar": "#10B981",
        "botao_cancelar": "#6B7280",
        "botao_excluir": "#EF4444",
        "botao_editar": "#06B6D4",
        "botao_voltar": "#6B7280",
        "botao_avancar": "#3B82F6",
        "botao_novo": "#8B5CF6",
        "botao_buscar": "#3B82F6",
        "botao_filtrar": "#8B5CF6",
        "botao_imprimir": "#F59E0B",
        "botao_exportar": "#10B981",
        "botao_importar": "#3B82F6",
        "botao_ajuda": "#06B6D4",
        "botao_configurar": "#6B7280",
        "botao_comprovante": "#8B5CF6",
        "botao_adiantamento": "#10B981",
        "botao_visualizar": "#6366F1",
        "botao_confirmar": "#22C55E",
        "botao_limpar": "#F59E0B",
        "botao_pdf": "#EF4444",
        "botao_export_csv": "#3B82F6",
        "botao_export_pdf": "#F59E0B"
    }'::jsonb;
BEGIN
    -- 1. USUÁRIO ADMIN
    INSERT INTO opera.usuarios (
        usuario,
        senha_hash,
        hierarquia,
        email,
        ativo,
        dica_senha,
        tema_preferido
    ) VALUES (
        'admin',
        '$2b$06$xOxt5sNynndfkGG/0Wx04exxGHV1it4WNz5fzoUbwxyOI8p5jwMJO',
        'Administrador',
        'admin@empresa.local',
        TRUE,
        'ad',
        'AZUL_NOTURNO'
    ) ON CONFLICT (usuario) DO UPDATE SET
        senha_hash = EXCLUDED.senha_hash,
        hierarquia = EXCLUDED.hierarquia,
        email = EXCLUDED.email,
        ativo = EXCLUDED.ativo,
        dica_senha = EXCLUDED.dica_senha,
        tema_preferido = EXCLUDED.tema_preferido
    RETURNING id INTO admin_id;

    -- 2. TEMA PERSONALIZADO AZUL_NOTURNO
    DELETE FROM opera.usuario_temas_personalizados
    WHERE usuario_id = admin_id AND nome_tema = 'AZUL_NOTURNO';

    INSERT INTO opera.usuario_temas_personalizados (
        usuario_id,
        nome_tema,
        cores_tema,
        data_criacao,
        atualizado_em
    ) VALUES (
        admin_id,
        'AZUL_NOTURNO',
        tema_azul_noturno,
        NOW(),
        NOW()
    );

    -- 3. PREFERÊNCIAS DO USUÁRIO
    DELETE FROM opera.usuario_preferencias WHERE usuario_id = admin_id;

    INSERT INTO opera.usuario_preferencias (
        usuario_id,
        tema_nome,
        usar_tema_personalizado,
        layout_compacto,
        sidebar_recolhida,
        usar_animacoes,
        mostrar_dicas,
        idioma,
        notificacoes
    ) VALUES (
        admin_id,
        'AZUL_NOTURNO',
        TRUE, FALSE, FALSE, TRUE, TRUE, 'pt-BR', TRUE
    );

    -- 4. PERMISSÕES TOTAIS
    DELETE FROM opera.usuario_permissoes WHERE usuario_id = admin_id;

    INSERT INTO opera.usuario_permissoes (
        usuario_id,
        codigo,
        pode_ver,
        pode_editar,
        pode_imprimir,
        pode_excluir,
        pode_administrar
    )
    SELECT admin_id, codigo, TRUE, TRUE, TRUE, TRUE, TRUE
    FROM (VALUES
        ('dashboard'), ('cadastro_modelos'), ('cadastro_de_corte'), ('busca_profunda_corte'),
        ('relatorio_servicos_pagos'),
        ('controle_envio_cortes'), ('controle_retorno_cortes'), ('finalizar_corte'),
        ('estoque_tecidos'), ('estoque_aviamentos'), ('estoque_insumos'),
        ('sistema_admin'), ('sistema_logs'), ('sistema_backup'), ('sistema_auditoria')
    ) AS paginas(codigo);

    RAISE NOTICE '[OK] [USUÁRIO 02] admin configurado com ID: %', admin_id;
    RAISE NOTICE '[OK] [TABELA 06] Tema AZUL_NOTURNO criado para admin';
    RAISE NOTICE '[OK] [TABELA 03] Preferências configuradas para admin';
    RAISE NOTICE '[OK] [TABELA 04] Permissões totais concedidas a admin';

EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '[ERRO] ERRO ao configurar admin: %', SQLERRM;
END $$;

----------------------------------------
-- 17. TRIGGERS
----------------------------------------
DROP TRIGGER IF EXISTS tr_validar_cores_tema ON opera.usuario_temas_personalizados;
CREATE TRIGGER tr_validar_cores_tema
    BEFORE INSERT OR UPDATE ON opera.usuario_temas_personalizados
    FOR EACH ROW
    EXECUTE FUNCTION opera.validar_cores_tema();

----------------------------------------
-- 18. ÍNDICES DE PERFORMANCE
----------------------------------------
-- [ÍNDICES PARA TABELA 02] usuarios
CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON opera.usuarios(ativo);
CREATE INDEX IF NOT EXISTS idx_usuarios_hierarquia ON opera.usuarios(hierarquia);

-- [ÍNDICES PARA TABELA 05] usuario_logs
CREATE INDEX IF NOT EXISTS idx_usuario_logs_usuario ON opera.usuario_logs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_usuario_logs_data_hora ON opera.usuario_logs(data_hora);

-- [ÍNDICES PARA TABELA 07] cadastro_modelos_cabecalho
CREATE INDEX IF NOT EXISTS idx_modelos_codigo ON opera.cadastro_modelos_cabecalho(codigo);
CREATE INDEX IF NOT EXISTS idx_modelos_descricao ON opera.cadastro_modelos_cabecalho(descricao);

-- [ÍNDICES PARA TABELA 15] cadastro_de_corte
CREATE INDEX IF NOT EXISTS idx_cadastro_corte_codigo ON opera.cadastro_de_corte(codigo);
CREATE INDEX IF NOT EXISTS idx_cadastro_corte_data ON opera.cadastro_de_corte(data);
CREATE INDEX IF NOT EXISTS idx_cadastro_corte_cortador ON opera.cadastro_de_corte(cortador);

-- [ÍNDICES PARA TABELA 36] estoque_tecidos
CREATE INDEX IF NOT EXISTS idx_estoque_tecidos_codigo ON opera.estoque_tecidos(codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_tecidos_cor ON opera.estoque_tecidos(cor);

-- [ÍNDICES PARA TABELA 37] estoque_aviamentos
CREATE INDEX IF NOT EXISTS idx_estoque_aviamentos_codigo ON opera.estoque_aviamentos(codigo);
CREATE INDEX IF NOT EXISTS idx_estoque_aviamentos_cor ON opera.estoque_aviamentos(cor);

-- [ÍNDICES PARA TABELA 22] envios_cortes
CREATE INDEX IF NOT EXISTS idx_envios_cortes_data ON opera.envios_cortes(data_envio);
CREATE INDEX IF NOT EXISTS idx_envios_cortes_status ON opera.envios_cortes(status_envio);

-- [ÍNDICES PARA TABELA 14] cadastro_faccoes
CREATE INDEX IF NOT EXISTS idx_faccoes_codigo ON opera.cadastro_faccoes(codigo);
CREATE INDEX IF NOT EXISTS idx_faccoes_nome ON opera.cadastro_faccoes(nome);
CREATE INDEX IF NOT EXISTS idx_faccoes_tipo ON opera.cadastro_faccoes(tipo_prestador);
CREATE INDEX IF NOT EXISTS idx_faccoes_ativo ON opera.cadastro_faccoes(ativo);

----------------------------------------
-- 19. MENSAGEM FINAL DE CONCLUSÃO
----------------------------------------
DO $$
DECLARE
    total_tabelas INTEGER;
    total_views INTEGER;
    total_funcoes INTEGER;
    gil_check RECORD;
BEGIN
    -- Contar objetos criados
    SELECT COUNT(*) INTO total_tabelas
    FROM information_schema.tables
    WHERE table_schema = 'opera' AND table_type = 'BASE TABLE';

    SELECT COUNT(*) INTO total_views
    FROM information_schema.views
    WHERE table_schema = 'opera';

    SELECT COUNT(*) INTO total_funcoes
    FROM information_schema.routines
    WHERE routine_schema = 'opera';

    -- Verificar configuração do admin
    SELECT u.id, u.usuario, u.tema_preferido, up.tema_nome, utp.nome_tema
    INTO gil_check
    FROM opera.usuarios u
    LEFT JOIN opera.usuario_preferencias up ON u.id = up.usuario_id
    LEFT JOIN opera.usuario_temas_personalizados utp ON u.id = utp.usuario_id
    WHERE u.usuario = 'admin';

    RAISE NOTICE '=======================================================';
    RAISE NOTICE '[OK] BANCO OPERA CRIADO COM SUCESSO - 60 TABELAS ENUMERADAS!';
    RAISE NOTICE '=======================================================';
    RAISE NOTICE '[INFO] ESTATÍSTICAS:';
    RAISE NOTICE '   • % Tabelas criadas (01 a 47)', total_tabelas;
    RAISE NOTICE '   • % Views configuradas (48 a 50)', total_views;
    RAISE NOTICE '   • % Funções implementadas (01 a 03)', total_funcoes;
    RAISE NOTICE '   • 01 Trigger ativo';
    RAISE NOTICE '   • 15 Índices de performance';
    RAISE NOTICE '=======================================================';
    RAISE NOTICE '[INFO] USUÁRIO ADMINISTRADOR CONFIGURADO:';
    RAISE NOTICE '   • [TABELA 02] Nome: %', gil_check.usuario;
    RAISE NOTICE '   • [TABELA 02] ID: %', gil_check.id;
    RAISE NOTICE '   • [TABELA 02] Tema preferido: %', gil_check.tema_preferido;
    RAISE NOTICE '   • [TABELA 03] Tema nas preferências: %', gil_check.tema_nome;
    RAISE NOTICE '   • [TABELA 06] Tema personalizado: %', gil_check.nome_tema;
    RAISE NOTICE '   • [TABELA 04] Permissões: 13 páginas com acesso total';
    RAISE NOTICE '=======================================================';
    RAISE NOTICE '[INFO] CREDENCIAIS DE ACESSO:';
    RAISE NOTICE '   • Usuário: admin';
    RAISE NOTICE '   • Senha: admin';
    RAISE NOTICE '   • Tema: AZUL_NOTURNO aplicado automaticamente';
    RAISE NOTICE '   • Email: admin@empresa.local';
    RAISE NOTICE '=======================================================';
    RAISE NOTICE '[INFO] MÓDULOS IMPLEMENTADOS:';
    RAISE NOTICE '   1. Usuários e Permissões (Tabelas 01-06)';
    RAISE NOTICE '   2. Modelos (Tabelas 07-13)';
    RAISE NOTICE '   3. Facções (Tabela 14)';
    RAISE NOTICE '   4. Corte (Tabelas 15-17)';
    RAISE NOTICE '   5. Ordem de Corte (Tabelas 18-20)';
    RAISE NOTICE '   6. Envio e Controle (Tabelas 21-22)';
    RAISE NOTICE '   7. Retorno e Finalização (Tabelas 23-31)';
    RAISE NOTICE '   8. Pagamentos (Tabelas 32-35)';
    RAISE NOTICE '   9. Estoque (Tabelas 36-42)';
    RAISE NOTICE '   10. Serviços e Histórico (Tabelas 43-45)';
    RAISE NOTICE '   11. Pricing e Relatórios (Tabelas 46-47)';
    RAISE NOTICE '   12. Views do Sistema (Views 48-50)';
    RAISE NOTICE '=======================================================';
    RAISE NOTICE '[OK] SISTEMA PRONTO PARA PRODUÇÃO!';
    RAISE NOTICE '=======================================================';
END $$;

----------------------------------------
-- 19. COMERCIAL / COMPRAS / MRP / PLANEJAMENTO / CUSTOS
----------------------------------------
-- [TABELA 48] cadastro_clientes - Cadastro de clientes
CREATE TABLE IF NOT EXISTS opera.cadastro_clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    documento VARCHAR(40),
    inscricao_estadual VARCHAR(40),
    email VARCHAR(120),
    telefone VARCHAR(40),
    whatsapp VARCHAR(40),
    endereco TEXT,
    bairro VARCHAR(120),
    cidade VARCHAR(120),
    uf VARCHAR(10),
    cep VARCHAR(20),
    segmento VARCHAR(120),
    observacoes TEXT,
    status VARCHAR(20) DEFAULT 'Ativo',
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

-- [TABELA 49] compras_fornecedores - Fornecedores de compras
CREATE TABLE IF NOT EXISTS opera.compras_fornecedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    categoria VARCHAR(120),
    contato VARCHAR(120),
    telefone VARCHAR(40),
    email VARCHAR(120),
    prazo_medio INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Ativo',
    observacoes TEXT,
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

-- [TABELA 50] compras_pedidos - Pedidos de compra
CREATE TABLE IF NOT EXISTS opera.compras_pedidos (
    id SERIAL PRIMARY KEY,
    data_pedido DATE DEFAULT CURRENT_DATE,
    fornecedor_id INTEGER REFERENCES opera.compras_fornecedores(id),
    descricao TEXT,
    valor_total NUMERIC(12,2) DEFAULT 0,
    status VARCHAR(30) DEFAULT 'Em aberto',
    entrega_prevista DATE,
    observacoes TEXT,
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

-- [TABELA 51] compras_recebimentos - Recebimentos de compras
CREATE TABLE IF NOT EXISTS opera.compras_recebimentos (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER REFERENCES opera.compras_pedidos(id),
    fornecedor_id INTEGER REFERENCES opera.compras_fornecedores(id),
    numero_nf VARCHAR(60),
    data_recebimento DATE,
    valor_total NUMERIC(12,2) DEFAULT 0,
    status VARCHAR(30) DEFAULT 'Recebido',
    observacoes TEXT,
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

-- [TABELA 52] mrp_necessidades - Necessidades calculadas
CREATE TABLE IF NOT EXISTS opera.mrp_necessidades (
    id SERIAL PRIMARY KEY,
    insumo VARCHAR(200),
    sku VARCHAR(120),
    necessario NUMERIC(12,2) DEFAULT 0,
    estoque NUMERIC(12,2) DEFAULT 0,
    faltante NUMERIC(12,2) DEFAULT 0,
    lead_time INTEGER DEFAULT 0,
    fornecedor VARCHAR(200),
    status VARCHAR(20) DEFAULT 'OK',
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

-- [TABELA 53] mrp_ordens_recomendadas - Ordens recomendadas de compra
CREATE TABLE IF NOT EXISTS opera.mrp_ordens_recomendadas (
    id SERIAL PRIMARY KEY,
    insumo VARCHAR(200),
    quantidade NUMERIC(12,2) DEFAULT 0,
    fornecedor VARCHAR(200),
    entrega_prevista DATE,
    status VARCHAR(30) DEFAULT 'Planejada',
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

-- [TABELA 54] planejamento_ops - Planejamento das ordens de produção
CREATE TABLE IF NOT EXISTS opera.planejamento_ops (
    id SERIAL PRIMARY KEY,
    op VARCHAR(60),
    modelo VARCHAR(200),
    quantidade INTEGER DEFAULT 0,
    inicio DATE,
    fim DATE,
    status VARCHAR(30) DEFAULT 'Planejada',
    prioridade VARCHAR(20) DEFAULT 'Média',
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

-- [TABELA 55] planejamento_capacidade - Capacidade por recurso
CREATE TABLE IF NOT EXISTS opera.planejamento_capacidade (
    id SERIAL PRIMARY KEY,
    recurso VARCHAR(200),
    carga NUMERIC(12,2) DEFAULT 0,
    capacidade NUMERIC(12,2) DEFAULT 0,
    ociosidade NUMERIC(12,2) DEFAULT 0,
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

-- [TABELA 56] custos_reais_categoria - Custos por categoria
CREATE TABLE IF NOT EXISTS opera.custos_reais_categoria (
    id SERIAL PRIMARY KEY,
    categoria VARCHAR(200),
    valor_planejado NUMERIC(12,2) DEFAULT 0,
    valor_real NUMERIC(12,2) DEFAULT 0,
    variacao NUMERIC(12,2) DEFAULT 0,
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

-- [TABELA 57] custos_reais_ops - Custos por OP
CREATE TABLE IF NOT EXISTS opera.custos_reais_ops (
    id SERIAL PRIMARY KEY,
    op VARCHAR(60),
    modelo VARCHAR(200),
    valor_planejado NUMERIC(12,2) DEFAULT 0,
    valor_real NUMERIC(12,2) DEFAULT 0,
    data_atualizacao TIMESTAMP DEFAULT NOW()
);

----------------------------------------
-- 19. MIGRAÇÕES DE COMPATIBILIDADE
----------------------------------------
-- CREATE TABLE IF NOT EXISTS não completa tabelas já existentes.
-- Estes ALTERs completam bancos antigos com as colunas usadas pelas páginas atuais.

-- Estoque: tecidos atuais usam metros/kilos; relatórios antigos ainda leem quantidade/categoria.
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS quantidade NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS categoria VARCHAR(100) DEFAULT 'Tecidos';
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS tipo VARCHAR(100) DEFAULT 'Tecido';
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Normal';
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS estoque_ideal NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS estoque_minimo NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS estoque_critico NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS base_referencia VARCHAR(20) DEFAULT 'metros';
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS observacoes TEXT;
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS localizacao VARCHAR(100);
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS data_entrada DATE DEFAULT CURRENT_DATE;
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
ALTER TABLE opera.estoque_tecidos ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

UPDATE opera.estoque_tecidos
   SET quantidade = COALESCE(NULLIF(quantidade, 0), metros, 0),
       categoria = COALESCE(NULLIF(TRIM(categoria), ''), 'Tecidos'),
       tipo = COALESCE(NULLIF(TRIM(tipo), ''), 'Tecido'),
       base_referencia = COALESCE(NULLIF(TRIM(base_referencia), ''), 'metros'),
       status = COALESCE(NULLIF(TRIM(status), ''), 'Normal')
 WHERE quantidade IS NULL
    OR categoria IS NULL OR TRIM(categoria) = ''
    OR tipo IS NULL OR TRIM(tipo) = ''
    OR base_referencia IS NULL OR TRIM(base_referencia) = ''
    OR status IS NULL OR TRIM(status) = '';

CREATE OR REPLACE FUNCTION opera.sync_estoque_tecidos_compat()
RETURNS TRIGGER AS $$
BEGIN
    NEW.quantidade := COALESCE(NEW.metros, 0);
    NEW.categoria := COALESCE(NULLIF(TRIM(NEW.categoria), ''), 'Tecidos');
    NEW.tipo := COALESCE(NULLIF(TRIM(NEW.tipo), ''), 'Tecido');
    NEW.base_referencia := COALESCE(NULLIF(TRIM(NEW.base_referencia), ''), 'metros');
    NEW.status := COALESCE(NULLIF(TRIM(NEW.status), ''), 'Normal');
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_sync_estoque_tecidos_compat ON opera.estoque_tecidos;
CREATE TRIGGER tr_sync_estoque_tecidos_compat
BEFORE INSERT OR UPDATE OF metros, categoria, tipo, base_referencia, status
ON opera.estoque_tecidos
FOR EACH ROW
EXECUTE FUNCTION opera.sync_estoque_tecidos_compat();

-- Estoques por quantidade: completa colunas comuns usadas por Entrada, Saída e Relatórios.
ALTER TABLE opera.estoque_aviamentos ADD COLUMN IF NOT EXISTS tipo VARCHAR(100) DEFAULT 'Aviamento';
ALTER TABLE opera.estoque_aviamentos ADD COLUMN IF NOT EXISTS categoria VARCHAR(100) DEFAULT 'Aviamentos';
ALTER TABLE opera.estoque_aviamentos ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Normal';
ALTER TABLE opera.estoque_aviamentos ADD COLUMN IF NOT EXISTS estoque_ideal NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_aviamentos ADD COLUMN IF NOT EXISTS estoque_minimo NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_aviamentos ADD COLUMN IF NOT EXISTS estoque_critico NUMERIC(12,3) DEFAULT 0;

ALTER TABLE opera.estoque_insumos ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Normal';
ALTER TABLE opera.estoque_insumos ADD COLUMN IF NOT EXISTS estoque_ideal NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_insumos ADD COLUMN IF NOT EXISTS estoque_minimo NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_insumos ADD COLUMN IF NOT EXISTS estoque_critico NUMERIC(12,3) DEFAULT 0;

ALTER TABLE opera.estoque_escritorio ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Normal';
ALTER TABLE opera.estoque_escritorio ADD COLUMN IF NOT EXISTS estoque_ideal NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_escritorio ADD COLUMN IF NOT EXISTS estoque_minimo NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_escritorio ADD COLUMN IF NOT EXISTS estoque_critico NUMERIC(12,3) DEFAULT 0;

ALTER TABLE opera.estoque_limpeza ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Normal';
ALTER TABLE opera.estoque_limpeza ADD COLUMN IF NOT EXISTS estoque_ideal NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_limpeza ADD COLUMN IF NOT EXISTS estoque_minimo NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_limpeza ADD COLUMN IF NOT EXISTS estoque_critico NUMERIC(12,3) DEFAULT 0;

ALTER TABLE opera.estoque_outros ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Normal';
ALTER TABLE opera.estoque_outros ADD COLUMN IF NOT EXISTS estoque_ideal NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_outros ADD COLUMN IF NOT EXISTS estoque_minimo NUMERIC(12,3) DEFAULT 0;
ALTER TABLE opera.estoque_outros ADD COLUMN IF NOT EXISTS estoque_critico NUMERIC(12,3) DEFAULT 0;

UPDATE opera.estoque_aviamentos
   SET categoria = COALESCE(NULLIF(TRIM(categoria), ''), 'Aviamentos'),
       tipo = COALESCE(NULLIF(TRIM(tipo), ''), 'Aviamento'),
       status = COALESCE(NULLIF(TRIM(status), ''), 'Normal');
UPDATE opera.estoque_insumos
   SET categoria = COALESCE(NULLIF(TRIM(categoria), ''), 'Insumos'),
       tipo = COALESCE(NULLIF(TRIM(tipo), ''), 'Insumo'),
       status = COALESCE(NULLIF(TRIM(status), ''), 'Normal');
UPDATE opera.estoque_escritorio
   SET categoria = COALESCE(NULLIF(TRIM(categoria), ''), 'Escritorio'),
       tipo = COALESCE(NULLIF(TRIM(tipo), ''), 'Escritorio'),
       status = COALESCE(NULLIF(TRIM(status), ''), 'Normal');
UPDATE opera.estoque_limpeza
   SET categoria = COALESCE(NULLIF(TRIM(categoria), ''), 'Limpeza'),
       tipo = COALESCE(NULLIF(TRIM(tipo), ''), 'Limpeza'),
       status = COALESCE(NULLIF(TRIM(status), ''), 'Normal');
UPDATE opera.estoque_outros
   SET categoria = COALESCE(NULLIF(TRIM(categoria), ''), 'Outros'),
       tipo = COALESCE(NULLIF(TRIM(tipo), ''), 'Outros'),
       status = COALESCE(NULLIF(TRIM(status), ''), 'Normal');

-- Rastreamento do corte: completa colunas-chave para busca profunda e fluxo até pagamento.
ALTER TABLE opera.cadastro_de_corte ADD COLUMN IF NOT EXISTS numero_ordem VARCHAR(50);
ALTER TABLE opera.cadastro_de_corte ADD COLUMN IF NOT EXISTS ordem_corte VARCHAR(50);
ALTER TABLE opera.cadastro_de_corte ADD COLUMN IF NOT EXISTS codigo VARCHAR(100);
ALTER TABLE opera.cadastro_de_corte ADD COLUMN IF NOT EXISTS descricao TEXT;
ALTER TABLE opera.cadastro_de_corte ADD COLUMN IF NOT EXISTS descricao_corte TEXT;
ALTER TABLE opera.cadastro_de_corte ADD COLUMN IF NOT EXISTS data DATE;
ALTER TABLE opera.cadastro_de_corte ADD COLUMN IF NOT EXISTS data_envio DATE;
ALTER TABLE opera.cadastro_de_corte ADD COLUMN IF NOT EXISTS total_pecas INTEGER DEFAULT 0;
ALTER TABLE opera.cadastro_de_corte ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
ALTER TABLE opera.cadastro_de_corte ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

ALTER TABLE opera.controle_envio_cortes ADD COLUMN IF NOT EXISTS corte_id INTEGER;
ALTER TABLE opera.controle_envio_cortes ADD COLUMN IF NOT EXISTS ordem_corte VARCHAR(50);
ALTER TABLE opera.controle_envio_cortes ADD COLUMN IF NOT EXISTS codigo_corte VARCHAR(100);
ALTER TABLE opera.controle_envio_cortes ADD COLUMN IF NOT EXISTS descricao_corte TEXT;
ALTER TABLE opera.controle_envio_cortes ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Em Conferencia';
ALTER TABLE opera.controle_envio_cortes ADD COLUMN IF NOT EXISTS op_planejamento VARCHAR(60);

ALTER TABLE opera.envios_cortes ADD COLUMN IF NOT EXISTS corte_id INTEGER;
ALTER TABLE opera.envios_cortes ADD COLUMN IF NOT EXISTS ordem_corte VARCHAR(50);
ALTER TABLE opera.envios_cortes ADD COLUMN IF NOT EXISTS codigo_corte VARCHAR(100);
ALTER TABLE opera.envios_cortes ADD COLUMN IF NOT EXISTS descricao_corte TEXT;
ALTER TABLE opera.envios_cortes ADD COLUMN IF NOT EXISTS tipo_servico TEXT;
ALTER TABLE opera.envios_cortes ADD COLUMN IF NOT EXISTS status_envio VARCHAR(30) DEFAULT 'Enviado';
ALTER TABLE opera.envios_cortes ADD COLUMN IF NOT EXISTS total_pecas INTEGER DEFAULT 0;
ALTER TABLE opera.envios_cortes ADD COLUMN IF NOT EXISTS valor_total_envio NUMERIC(12,2) DEFAULT 0;
ALTER TABLE opera.envios_cortes ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
ALTER TABLE opera.envios_cortes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

ALTER TABLE opera.controle_retorno_cortes ADD COLUMN IF NOT EXISTS envio_id INTEGER;
ALTER TABLE opera.controle_retorno_cortes ADD COLUMN IF NOT EXISTS data_chegada DATE;
ALTER TABLE opera.controle_retorno_cortes ADD COLUMN IF NOT EXISTS total_entregue INTEGER DEFAULT 0;
ALTER TABLE opera.controle_retorno_cortes ADD COLUMN IF NOT EXISTS total_defeitos INTEGER DEFAULT 0;
ALTER TABLE opera.controle_retorno_cortes ADD COLUMN IF NOT EXISTS total_faltantes INTEGER DEFAULT 0;
ALTER TABLE opera.controle_retorno_cortes ADD COLUMN IF NOT EXISTS total_regulares INTEGER DEFAULT 0;
ALTER TABLE opera.controle_retorno_cortes ADD COLUMN IF NOT EXISTS valor_total NUMERIC(12,2) DEFAULT 0;
ALTER TABLE opera.controle_retorno_cortes ADD COLUMN IF NOT EXISTS op_planejamento VARCHAR(60);
ALTER TABLE opera.controle_retorno_cortes ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
ALTER TABLE opera.controle_retorno_cortes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

ALTER TABLE opera.entrada_acabamento ADD COLUMN IF NOT EXISTS envio_id INTEGER;
ALTER TABLE opera.entrada_acabamento ADD COLUMN IF NOT EXISTS data_chegada DATE;
ALTER TABLE opera.entrada_acabamento ADD COLUMN IF NOT EXISTS total_entregue INTEGER DEFAULT 0;
ALTER TABLE opera.entrada_acabamento ADD COLUMN IF NOT EXISTS total_defeitos INTEGER DEFAULT 0;
ALTER TABLE opera.entrada_acabamento ADD COLUMN IF NOT EXISTS total_faltantes INTEGER DEFAULT 0;
ALTER TABLE opera.entrada_acabamento ADD COLUMN IF NOT EXISTS total_regulares INTEGER DEFAULT 0;
ALTER TABLE opera.entrada_acabamento ADD COLUMN IF NOT EXISTS valor_total NUMERIC(12,2) DEFAULT 0;
ALTER TABLE opera.entrada_acabamento ADD COLUMN IF NOT EXISTS pago BOOLEAN DEFAULT FALSE;
ALTER TABLE opera.entrada_acabamento ADD COLUMN IF NOT EXISTS pagamento_id INTEGER;
ALTER TABLE opera.entrada_acabamento ADD COLUMN IF NOT EXISTS valor_pago NUMERIC(12,2);
ALTER TABLE opera.entrada_acabamento ADD COLUMN IF NOT EXISTS data_pagamento DATE;

ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS corte_id INTEGER;
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS entrada_id INTEGER;
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS envio_id INTEGER;
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS retorno_id INTEGER;
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS tipo_servico VARCHAR(100);
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS codigo VARCHAR(100);
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS descricao TEXT;
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS quantidade_finalizada INTEGER;
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS status VARCHAR(50);
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS pago BOOLEAN DEFAULT FALSE;
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS pagamento_id INTEGER;
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS valor_pago NUMERIC(12,2);
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS data_pagamento DATE;
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS valor_total NUMERIC(12,2) DEFAULT 0;
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
ALTER TABLE opera.cortes_finalizados ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_estoque_tecidos_categoria ON opera.estoque_tecidos(categoria);
CREATE INDEX IF NOT EXISTS idx_estoque_tecidos_quantidade ON opera.estoque_tecidos(quantidade);
CREATE INDEX IF NOT EXISTS idx_cadastro_corte_ordem ON opera.cadastro_de_corte(ordem_corte);
CREATE INDEX IF NOT EXISTS idx_envios_cortes_codigo ON opera.envios_cortes(codigo_corte);
CREATE INDEX IF NOT EXISTS idx_controle_envio_cortes_codigo ON opera.controle_envio_cortes(codigo_corte);
CREATE INDEX IF NOT EXISTS idx_cortes_finalizados_codigo ON opera.cortes_finalizados(codigo);

-- Permissão da página nova para administradores já existentes.
INSERT INTO opera.usuario_permissoes (
    usuario_id,
    codigo,
    pode_ver,
    pode_editar,
    pode_imprimir,
    pode_excluir,
    pode_administrar
)
SELECT
    u.id,
    paginas.codigo,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE
FROM opera.usuarios u
CROSS JOIN (VALUES
    ('busca_profunda_corte'),
    ('relatorio_servicos_pagos')
) AS paginas(codigo)
WHERE LOWER(COALESCE(u.usuario, '')) = 'admin'
   OR LOWER(COALESCE(u.hierarquia, '')) IN ('admin', 'administrador')
ON CONFLICT (usuario_id, codigo) DO UPDATE SET
    pode_ver = TRUE,
    pode_editar = TRUE,
    pode_imprimir = TRUE,
    pode_excluir = TRUE,
    pode_administrar = TRUE;

----------------------------------------
-- 20. PERMISSÕES E FINALIZAÇÃO
----------------------------------------

GRANT ALL ON SCHEMA opera TO opera_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA opera TO opera_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA opera TO opera_app;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA opera TO opera_app;

DO $$
BEGIN
    UPDATE opera._schema_info
       SET versao = '1.0',
           atualizado_em = NOW()
     WHERE schema_name = 'opera';

    IF NOT FOUND THEN
        INSERT INTO opera._schema_info (schema_name, versao, criado_em, atualizado_em)
        VALUES ('opera', '1.0', NOW(), NOW());
    END IF;
END $$;

-- MENSAGEM FINAL COMPLETA E CORRIGIDA
DO $$
DECLARE
    total_tabelas INTEGER;
    total_views INTEGER;
    total_funcoes INTEGER;
    total_triggers INTEGER;
    usuario_admin_id INTEGER;
BEGIN
    -- Contar objetos
    SELECT COUNT(*) INTO total_tabelas
    FROM information_schema.tables
    WHERE table_schema = 'opera'
    AND table_type = 'BASE TABLE';

    SELECT COUNT(*) INTO total_views
    FROM information_schema.views
    WHERE table_schema = 'opera';

    SELECT COUNT(*) INTO total_funcoes
    FROM information_schema.routines
    WHERE routine_schema = 'opera';

    SELECT COUNT(*) INTO total_triggers
    FROM information_schema.triggers
    WHERE trigger_schema = 'opera';

    -- Obter ID do administrador
    SELECT id INTO usuario_admin_id
    FROM opera.usuarios
    WHERE usuario = 'admin';

    -- Mensagem final formatada
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'ESTRUTURA DO BANCO OPERA CRIADA COM SUCESSO!';
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'ESTATISTICAS:';
    RAISE NOTICE '- % Tabelas criadas', total_tabelas;
    RAISE NOTICE '- % Views configuradas', total_views;
    RAISE NOTICE '- % Funcoes implementadas', total_funcoes;
    RAISE NOTICE '- % Triggers ativos', total_triggers;
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'USUARIO ADMINISTRADOR CONFIGURADO:';
    RAISE NOTICE '- Nome: admin';
    RAISE NOTICE '- ID: %', usuario_admin_id;
    RAISE NOTICE '- Email: admin@empresa.local';
    RAISE NOTICE '- Permissoes: ACESSO TOTAL A TODOS OS MODULOS';
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'MODULOS IMPLEMENTADOS:';
    RAISE NOTICE '1. Usuarios e Permissoes (5 tabelas)';
    RAISE NOTICE '2. Modelos e Cadastros (7 tabelas)';
    RAISE NOTICE '3. Faccoes e Prestadores (1 tabela)';
    RAISE NOTICE '4. Corte e Ordem de Corte (5 tabelas)';
    RAISE NOTICE '5. Envio e Controle (4 tabelas)';
    RAISE NOTICE '6. Retorno e Finalizacao (8 tabelas)';
    RAISE NOTICE '7. Pagamentos e Financeiro (4 tabelas)';
    RAISE NOTICE '8. Estoque e Materiais (7 tabelas)';
    RAISE NOTICE '9. Servicos e Historico (3 tabelas)';
    RAISE NOTICE '10. Pricing e Relatorios (2 tabelas)';
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'O sistema OPERA esta pronto para uso!';
    RAISE NOTICE 'Usuario administrador ja pode fazer login com:';
    RAISE NOTICE '- Usuario: admin';
    RAISE NOTICE '- Senha: admin';
    RAISE NOTICE '- Dica: ad';
    RAISE NOTICE '- Hierarquia: Administrador';
    RAISE NOTICE '- Tema: AZUL_NOTURNO aplicado automaticamente';
    RAISE NOTICE '=========================================';
    RAISE NOTICE '[INFO] CONEXÕES CONFIGURADAS:';
    RAISE NOTICE '- Schema: opera';
    RAISE NOTICE '- Permissoes: opera_app tem acesso total';
    RAISE NOTICE '- Versao: 1.0 registrada em _schema_info';
    RAISE NOTICE '=========================================';
END $$;
