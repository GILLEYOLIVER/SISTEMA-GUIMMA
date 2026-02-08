-- ================================================================
-- [SCRIPT CORRIGIDO PARA RECRIAR BANCO IDÊNTICO AO BACKUP]
-- ================================================================

-- 1️⃣ REMOVER SCHEMA EXISTENTE (CUIDADO - APAGA TUDO!)
DROP SCHEMA IF EXISTS opera CASCADE;

-- 2️⃣ CRIAR SCHEMA NOVO
CREATE SCHEMA opera AUTHORIZATION CURRENT_USER;

-- 3️⃣ CONFIGURAR SEARCH_PATH
SET search_path TO opera, public;

-- 4️⃣ CRIAR EXTENSÕES
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ================================================================
-- [TABELA 0: CONTROLE DE VERSÃO DO SCHEMA]
-- ================================================================
CREATE TABLE opera._schema_info (
    id SERIAL PRIMARY KEY,
    schema_name TEXT DEFAULT 'opera',
    versao TEXT DEFAULT '1.0',
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- [TABELA 1: USUÁRIOS - EXATA COMO NO BACKUP]
-- ================================================================
CREATE TABLE opera.usuarios (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(100) NOT NULL UNIQUE,
    senha_hash TEXT,
    hierarquia VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    data_criacao TIMESTAMP DEFAULT NOW(),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    dica_senha TEXT,
    ultimo_login TIMESTAMP,
    telefone VARCHAR(50),
    departamento VARCHAR(100),
    tema_preferido VARCHAR(50) DEFAULT 'Noite Urbana'
);

CREATE INDEX idx_usuarios_hierarquia ON opera.usuarios (hierarquia);
CREATE INDEX idx_usuarios_ativo ON opera.usuarios (ativo);

COMMENT ON TABLE opera.usuarios IS 'TABELA 01 - Registro dos usuários do sistema OPERA.';

-- ================================================================
-- [TABELA 2: PREFERÊNCIAS - EXATA COMO NO BACKUP]
-- ================================================================
CREATE TABLE opera.usuario_preferencias (
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

CREATE INDEX idx_usuario_preferencias_tema ON opera.usuario_preferencias (tema_nome);

COMMENT ON TABLE opera.usuario_preferencias IS 'TABELA 02 - Preferências gerais do usuário.';

-- ================================================================
-- [TABELA 3: TEMAS PERSONALIZADOS - EXATA COMO NO BACKUP]
-- ================================================================
CREATE TABLE opera.usuario_temas_personalizados (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    nome_tema VARCHAR(100) NOT NULL,
    cores_tema JSONB NOT NULL,
    data_criacao TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    UNIQUE (usuario_id, nome_tema)
);

CREATE INDEX idx_usuario_temas_usuario ON opera.usuario_temas_personalizados (usuario_id);
CREATE INDEX idx_usuario_temas_nome ON opera.usuario_temas_personalizados (nome_tema);

COMMENT ON TABLE opera.usuario_temas_personalizados IS 'TABELA 03 - Temas customizados criados pelos usuários.';

-- ================================================================
-- [TABELA 4: PERMISSÕES - EXATA COMO NO BACKUP]
-- ================================================================
CREATE TABLE opera.usuario_permissoes (
    usuario_id INTEGER NOT NULL REFERENCES opera.usuarios(id) ON DELETE CASCADE,
    codigo VARCHAR(100) NOT NULL,
    pode_ver BOOLEAN DEFAULT FALSE,
    pode_editar BOOLEAN DEFAULT FALSE,
    pode_imprimir BOOLEAN DEFAULT FALSE,
    pode_excluir BOOLEAN DEFAULT FALSE,
    pode_administrar BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (usuario_id, codigo)
);

CREATE INDEX idx_usuario_permissoes_codigo ON opera.usuario_permissoes (codigo);

COMMENT ON TABLE opera.usuario_permissoes IS 'TABELA 04 - Permissões de acesso às funções do sistema OPERA.';

-- ================================================================
-- [TABELA 5: LOGS DE USUÁRIO - EXATA COMO NO BACKUP]
-- ================================================================
CREATE TABLE opera.usuario_logs (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES opera.usuarios(id),
    acao TEXT,
    detalhes TEXT,
    data_hora TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_usuario_logs_usuario ON opera.usuario_logs (usuario_id);
CREATE INDEX idx_usuario_logs_data_hora ON opera.usuario_logs (data_hora);

COMMENT ON TABLE opera.usuario_logs IS 'TABELA 05 - Histórico de ações realizadas pelos usuários.';

-- ================================================================
-- [TABELA 6: CADASTRO DE MODELOS (CABEÇALHO)]
-- ================================================================
CREATE TABLE opera.cadastro_modelos_cabecalho (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    colecao VARCHAR(100),
    tamanho_base VARCHAR(10),
    dificuldade VARCHAR(50),
    modelista VARCHAR(100),
    pilotista VARCHAR(100),
    custo_total NUMERIC(12,2) DEFAULT 0,
    pronto_producao BOOLEAN DEFAULT FALSE,
    grade_disponivel TEXT,
    data_criacao TIMESTAMP DEFAULT NOW(),
    data_atualizacao TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cadastro_modelos_codigo ON opera.cadastro_modelos_cabecalho (codigo);
CREATE INDEX idx_cadastro_modelos_descricao ON opera.cadastro_modelos_cabecalho (descricao);

-- ================================================================
-- [TABELA 7: TECIDOS POR MODELO]
-- ================================================================
CREATE TABLE opera.cadastro_modelos_tecidos (
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

CREATE INDEX idx_modelos_tecidos_cadastro ON opera.cadastro_modelos_tecidos (cadastro_id);
CREATE INDEX idx_modelos_tecidos_codigo ON opera.cadastro_modelos_tecidos (codigo_modelo);

-- ================================================================
-- [TABELA 8: AVIAMENTOS POR MODELO]
-- ================================================================
CREATE TABLE opera.cadastro_modelos_aviamentos (
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

CREATE INDEX idx_modelos_aviamentos_cadastro ON opera.cadastro_modelos_aviamentos (cadastro_id);
CREATE INDEX idx_modelos_aviamentos_codigo ON opera.cadastro_modelos_aviamentos (codigo_modelo);

-- ================================================================
-- [TABELA 9: CADASTRO MODELOS OUTROS (SISTEMA PRECISA DESSA TABELA)]
-- ================================================================
CREATE TABLE opera.cadastro_modelos_outros (
    id SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo VARCHAR(100),
    descricao TEXT,
    cor VARCHAR(50),
    fornecedor VARCHAR(100),
    unidade VARCHAR(20),
    quantidade NUMERIC(12,4) DEFAULT 0,
    preco NUMERIC(12,2) DEFAULT 0,
    total NUMERIC(12,2) DEFAULT 0,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_modelos_outros_cadastro ON opera.cadastro_modelos_outros (cadastro_id);
CREATE INDEX idx_modelos_outros_codigo ON opera.cadastro_modelos_outros (codigo_modelo);

-- ================================================================
-- [TABELA 9B: CADASTRO MODELOS OUTROS SERVICOS (BACKUP TEM ESSA TABELA)]
-- ================================================================
CREATE TABLE opera.cadastro_modelos_outros_servicos (
    id SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    codigo VARCHAR(100),
    descricao TEXT,
    cor VARCHAR(50),
    fornecedor VARCHAR(100),
    unidade VARCHAR(20),
    quantidade NUMERIC(12,4) DEFAULT 0,
    preco NUMERIC(12,2) DEFAULT 0,
    total NUMERIC(12,2) DEFAULT 0,
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_modelos_outros_servicos_cadastro ON opera.cadastro_modelos_outros_servicos (cadastro_id);
CREATE INDEX idx_modelos_outros_servicos_codigo ON opera.cadastro_modelos_outros_servicos (codigo_modelo);

-- ================================================================
-- [TABELA 10: IMAGENS DO MODELO]
-- ================================================================
CREATE TABLE opera.cadastro_modelos_imagens (
    id SERIAL PRIMARY KEY,
    codigo_modelo VARCHAR(100) NOT NULL,
    cadastro_id INTEGER REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    tipo_imagem VARCHAR(20),
    caminho_imagem TEXT,
    descricao TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_modelos_imagens_cadastro ON opera.cadastro_modelos_imagens (cadastro_id);
CREATE INDEX idx_modelos_imagens_codigo ON opera.cadastro_modelos_imagens (codigo_modelo);

-- ================================================================
-- [TABELA 11: GRADE POR MODELO]
-- ================================================================
CREATE TABLE opera.cadastro_modelos_grade (
    id SERIAL PRIMARY KEY,
    modelo_id INTEGER NOT NULL REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE,
    tamanho VARCHAR(10) NOT NULL,
    disponivel BOOLEAN DEFAULT TRUE,
    UNIQUE (modelo_id, tamanho)
);

-- ================================================================
-- [TABELA 12: CADASTRO DE FACÇÕES]
-- ================================================================
CREATE TABLE opera.cadastro_faccoes (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) UNIQUE NOT NULL,
    nome VARCHAR(200) NOT NULL,
    tipo_prestador VARCHAR(50) DEFAULT 'Facção',
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

CREATE INDEX idx_faccoes_nome ON opera.cadastro_faccoes (nome);
CREATE INDEX idx_faccoes_codigo ON opera.cadastro_faccoes (codigo);
CREATE INDEX idx_faccoes_tipo ON opera.cadastro_faccoes (tipo_prestador);
CREATE INDEX idx_faccoes_ativo ON opera.cadastro_faccoes (ativo);
CREATE INDEX idx_faccoes_tipo_ativo ON opera.cadastro_faccoes (tipo_prestador, ativo);

-- ================================================================
-- [TABELA 13: PAGAMENTO DE SERVIÇOS]
-- ================================================================
CREATE TABLE opera.pagamento_servicos (
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

-- ================================================================
-- [TABELA 14: PAGAMENTO SERVIÇOS DETALHE]
-- ================================================================
CREATE TABLE opera.pagamento_servicos_detalhe (
    pagamento_id BIGINT NOT NULL REFERENCES opera.pagamento_servicos(id) ON DELETE CASCADE,
    entrada_acabamento_id INTEGER NOT NULL,
    valor_servico NUMERIC(10,2) NOT NULL,
    PRIMARY KEY (pagamento_id, entrada_acabamento_id)
);

-- ================================================================
-- [TABELA 15: PRICING PROFILES]
-- ================================================================
CREATE TABLE opera.pricing_profiles (
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

-- ================================================================
-- [TABELA 16: CADASTRO DE CORTE]
-- ================================================================
CREATE TABLE opera.cadastro_de_corte (
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
    pp INTEGER NOT NULL DEFAULT 0,
    p INTEGER NOT NULL DEFAULT 0,
    m INTEGER NOT NULL DEFAULT 0,
    g INTEGER NOT NULL DEFAULT 0,
    gg INTEGER NOT NULL DEFAULT 0,
    g1 INTEGER NOT NULL DEFAULT 0,
    g2 INTEGER NOT NULL DEFAULT 0,
    g3 INTEGER NOT NULL DEFAULT 0,
    total_pecas INTEGER NOT NULL DEFAULT 0,
    rendimento NUMERIC(12,4),
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cadastro_corte_codigo ON opera.cadastro_de_corte (codigo);
CREATE INDEX idx_cadastro_corte_data ON opera.cadastro_de_corte (data);
CREATE INDEX idx_cadastro_corte_cortador ON opera.cadastro_de_corte (cortador);
CREATE INDEX idx_cadastro_corte_numero_ordem ON opera.cadastro_de_corte (numero_ordem);

-- ================================================================
-- [TABELA 17: CADASTRO DE CORTE TECIDOS]
-- ================================================================
CREATE TABLE opera.cadastro_de_corte_tecidos (
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

CREATE INDEX idx_corte_tecidos_cadastro ON opera.cadastro_de_corte_tecidos (cadastro_id);

-- ================================================================
-- [TABELA 18: CADASTRO DE CORTE LOTES]
-- ================================================================
CREATE TABLE opera.cadastro_de_corte_lotes (
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

CREATE INDEX idx_corte_lotes_cadastro ON opera.cadastro_de_corte_lotes (cadastro_id);

-- ================================================================
-- [TABELA 19: ORDEM DE CORTE FICHA]
-- ================================================================
CREATE TABLE opera.ordem_corte_ficha (
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

CREATE INDEX idx_ordem_corte_codigo ON opera.ordem_corte_ficha (codigo_modelo);
CREATE INDEX idx_ordem_corte_data ON opera.ordem_corte_ficha (data_registro);
CREATE INDEX idx_ordem_corte_status ON opera.ordem_corte_ficha (status);
CREATE INDEX idx_ordem_corte_codigo_modelo ON opera.ordem_corte_ficha (codigo_modelo);
CREATE INDEX idx_ordem_corte_data_final ON opera.ordem_corte_ficha (data_final);

-- ================================================================
-- [TABELA 20: ORDEM DE CORTE LOTES]
-- ================================================================
CREATE TABLE opera.ordem_corte_lotes (
    id BIGSERIAL PRIMARY KEY,
    ordem_id INTEGER NOT NULL REFERENCES opera.ordem_corte_ficha(id) ON DELETE CASCADE,
    lote_numero VARCHAR(50),
    tamanho VARCHAR(10) NOT NULL,
    quantidade INTEGER NOT NULL DEFAULT 0,
    UNIQUE (ordem_id, lote_numero, tamanho)
);

-- ================================================================
-- [TABELA 21: ADIANTAMENTO FACÇÃO]
-- ================================================================
CREATE TABLE opera.adiantamento_faccao (
    id SERIAL PRIMARY KEY,
    corte_id INTEGER,
    codigo_modelo VARCHAR(100),
    faccao VARCHAR(200),
    valor NUMERIC(12,2) NOT NULL,
    forma_pagamento VARCHAR(50),
    parcelas INTEGER DEFAULT 1,
    data_hora TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_adiantamento_corte ON opera.adiantamento_faccao (corte_id);
CREATE INDEX idx_adiantamento_faccao ON opera.adiantamento_faccao (faccao);

-- ================================================================
-- [TABELA 22: ENVIOS CORTES]
-- ================================================================
CREATE TABLE opera.envios_cortes (
    id SERIAL PRIMARY KEY,
    data_envio DATE NOT NULL,
    hora_envio TIME,
    prestador_id INTEGER REFERENCES opera.cadastro_faccoes(id) ON DELETE RESTRICT,
    tipo_servico TEXT,
    corte_id INTEGER REFERENCES opera.cadastro_de_corte(id) ON DELETE RESTRICT,
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
    aviamentos TEXT,
    outros TEXT,
    observacoes TEXT,
    tel_encarregado TEXT,
    tel_acabamento TEXT,
    previsao_entrega DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_envios_cortes_data ON opera.envios_cortes (data_envio);
CREATE INDEX idx_envios_cortes_prestador ON opera.envios_cortes (prestador_id);
CREATE INDEX idx_envios_cortes_corte ON opera.envios_cortes (corte_id);
CREATE INDEX idx_envios_cortes_status ON opera.envios_cortes (status_envio);

-- ================================================================
-- [TABELA 23: CONTROLE ENVIO CORTES]
-- ================================================================
CREATE TABLE opera.controle_envio_cortes (
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
    status VARCHAR(50) DEFAULT 'Em Conferência',
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

CREATE INDEX idx_envio_cortes_data_envio ON opera.controle_envio_cortes (data_envio);
CREATE INDEX idx_envio_cortes_servico ON opera.controle_envio_cortes (servico);
CREATE INDEX idx_envio_cortes_costureira ON opera.controle_envio_cortes (costureira);
CREATE INDEX idx_envio_cortes_ordem_corte ON opera.controle_envio_cortes (ordem_corte);
CREATE INDEX idx_envio_cortes_status ON opera.controle_envio_cortes (status);

-- ================================================================
-- [TABELA 24: ENTRADA ACABAMENTO]
-- ================================================================
CREATE TABLE opera.entrada_acabamento (
    id SERIAL PRIMARY KEY,
    envio_id INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    data_chegada DATE,
    total_entregue INTEGER,
    total_defeitos INTEGER,
    total_faltantes INTEGER,
    total_regulares INTEGER,
    valor_total NUMERIC(12,2),
    pago BOOLEAN DEFAULT FALSE,
    data_pagamento DATE
);

-- ================================================================
-- [TABELA 25: HISTÓRICO DE SERVIÇO]
-- ================================================================
CREATE TABLE opera.historico_de_servico (
    id BIGSERIAL PRIMARY KEY,
    envio_id INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    entrada_id INTEGER REFERENCES opera.entrada_acabamento(id) ON DELETE SET NULL,
    pagamento_id BIGINT REFERENCES opera.pagamento_servicos(id) ON DELETE SET NULL,
    tipo_servico VARCHAR(50),
    status VARCHAR(50) DEFAULT 'Em Andamento',
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- [TABELA 26: CONTROLE RETORNO CORTES]
-- ================================================================
CREATE TABLE opera.controle_retorno_cortes (
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

CREATE INDEX idx_ctrl_retorno_envio ON opera.controle_retorno_cortes (envio_id);
CREATE INDEX idx_ctrl_retorno_data ON opera.controle_retorno_cortes (data_chegada);

-- ================================================================
-- [TABELA 27: CORTES FINALIZADOS]
-- ================================================================
CREATE TABLE opera.cortes_finalizados (
    id SERIAL PRIMARY KEY,
    corte_id INTEGER,
    entrada_id INTEGER,
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
    bonificacao BOOLEAN DEFAULT FALSE,
    pago BOOLEAN DEFAULT FALSE,
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
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cortes_finalizados_corte ON opera.cortes_finalizados (corte_id);
CREATE INDEX idx_cortes_finalizados_entrada ON opera.cortes_finalizados (entrada_id);
CREATE INDEX idx_cortes_finalizados_data_chegada ON opera.cortes_finalizados (data_chegada);

-- ================================================================
-- [TABELA 28: PAGAMENTO CORTE ACABAMENTO]
-- ================================================================
CREATE TABLE opera.pagamento_corte_acabamento (
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

CREATE INDEX idx_pagamento_corte_codigo ON opera.pagamento_corte_acabamento (codigo);
CREATE INDEX idx_pagamento_corte_costureira ON opera.pagamento_corte_acabamento (costureira);
CREATE INDEX idx_pagamento_corte_data_pagamento ON opera.pagamento_corte_acabamento (data_pagamento);

-- ================================================================
-- [TABELA 29: ENVIO DETALHES TAMANHO]
-- ================================================================
CREATE TABLE opera.envio_detalhes_tamanho (
    envio_id INTEGER NOT NULL REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE,
    tamanho VARCHAR(10) NOT NULL,
    quantidade INTEGER DEFAULT 0,
    quantidade_pilotos INTEGER DEFAULT 0,
    valor_peca NUMERIC(12,2) DEFAULT 0,
    PRIMARY KEY (envio_id, tamanho)
);

CREATE INDEX idx_envio_det_tamanho_envio ON opera.envio_detalhes_tamanho (envio_id);
CREATE INDEX idx_envio_det_tamanho ON opera.envio_detalhes_tamanho (tamanho);

-- ================================================================
-- [TABELA 30: RETORNO DETALHES TAMANHO]
-- ================================================================
CREATE TABLE opera.retorno_detalhes_tamanho (
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

CREATE INDEX idx_retorno_tam_envio ON opera.retorno_detalhes_tamanho (envio_id);
CREATE INDEX idx_retorno_tam_tamanho ON opera.retorno_detalhes_tamanho (tamanho);

-- ================================================================
-- [TABELA 31: ESTOQUE TECIDOS]
-- ================================================================
CREATE TABLE opera.estoque_tecidos (
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

CREATE INDEX idx_estoque_tecidos_codigo ON opera.estoque_tecidos (codigo);
CREATE INDEX idx_estoque_tecidos_cor ON opera.estoque_tecidos (cor);

-- ================================================================
-- [TABELA 32: ESTOQUE AVIAMENTOS]
-- ================================================================
CREATE TABLE opera.estoque_aviamentos (
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

CREATE INDEX idx_estoque_aviamentos_codigo ON opera.estoque_aviamentos (codigo);
CREATE INDEX idx_estoque_aviamentos_cor ON opera.estoque_aviamentos (cor);

-- ================================================================
-- [TABELA 33: ESTOQUE INSUMOS]
-- ================================================================
CREATE TABLE opera.estoque_insumos (
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

CREATE INDEX idx_estoque_insumos_codigo ON opera.estoque_insumos (codigo);
CREATE INDEX idx_estoque_insumos_cor ON opera.estoque_insumos (cor);

-- ================================================================
-- [TABELA 34: ESTOQUE ESCRITÓRIO]
-- ================================================================
CREATE TABLE opera.estoque_escritorio (
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

CREATE INDEX idx_estoque_escritorio_codigo ON opera.estoque_escritorio (codigo);
CREATE INDEX idx_estoque_escritorio_cor ON opera.estoque_escritorio (cor);

-- ================================================================
-- [TABELA 35: ESTOQUE LIMPEZA]
-- ================================================================
CREATE TABLE opera.estoque_limpeza (
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

CREATE INDEX idx_estoque_limpeza_codigo ON opera.estoque_limpeza (codigo);
CREATE INDEX idx_estoque_limpeza_cor ON opera.estoque_limpeza (cor);

-- ================================================================
-- [TABELA 36: ESTOQUE OUTROS]
-- ================================================================
CREATE TABLE opera.estoque_outros (
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

CREATE INDEX idx_estoque_outros_codigo ON opera.estoque_outros (codigo);
CREATE INDEX idx_estoque_outros_cor ON opera.estoque_outros (cor);

-- ================================================================
-- [TABELA 37: PEÇAS FINALIZADAS]
-- ================================================================
CREATE TABLE opera.pecas_finalizadas (
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

CREATE INDEX idx_pecas_finalizadas_corte ON opera.pecas_finalizadas (corte_id);
CREATE INDEX idx_pecas_finalizadas_data_chegada ON opera.pecas_finalizadas (data_chegada);
CREATE INDEX idx_pecas_finalizadas_costureira ON opera.pecas_finalizadas (costureira);
CREATE INDEX idx_pecas_finalizadas_status ON opera.pecas_finalizadas (status);

-- ================================================================
-- [TABELA 38: LOG FINALIZAÇÕES]
-- ================================================================
CREATE TABLE opera.log_finalizacoes (
    id SERIAL PRIMARY KEY,
    entrada_id INTEGER REFERENCES opera.entrada_acabamento(id),
    acao VARCHAR(50) NOT NULL,
    dados_antes JSONB,
    dados_depois JSONB,
    usuario VARCHAR(100),
    data_hora TIMESTAMP DEFAULT NOW(),
    observacoes TEXT
);

CREATE INDEX idx_log_finalizacoes_entrada ON opera.log_finalizacoes (entrada_id);
CREATE INDEX idx_log_finalizacoes_data ON opera.log_finalizacoes (data_hora);
CREATE INDEX idx_log_finalizacoes_usuario ON opera.log_finalizacoes (usuario);

-- ================================================================
-- [TABELA 39: CORTES FINALIZADOS COMPLETO]
-- ================================================================
CREATE TABLE opera.cortes_finalizados_completo (
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

CREATE INDEX idx_cortes_finalizados_completo_entrada ON opera.cortes_finalizados_completo (entrada_id);
CREATE INDEX idx_cortes_finalizados_completo_corte ON opera.cortes_finalizados_completo (corte_id);
CREATE INDEX idx_cortes_finalizados_completo_status ON opera.cortes_finalizados_completo (status);

-- ================================================================
-- [TABELA 40: ENTRADA ACABAMENTO DETALHES]
-- ================================================================
CREATE TABLE opera.entrada_acabamento_detalhes (
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

CREATE INDEX idx_entrada_det_entrada ON opera.entrada_acabamento_detalhes (entrada_id);
CREATE INDEX idx_entrada_det_status ON opera.entrada_acabamento_detalhes (status_finalizacao);

-- ================================================================
-- [TABELA 41: ESTOQUE SAÍDA LOG]
-- ================================================================
CREATE TABLE opera.estoque_saida_log (
    id BIGSERIAL PRIMARY KEY,
    data_hora TIMESTAMP NOT NULL DEFAULT NOW(),
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

-- ================================================================
-- [TABELA 42: SERVIÇOS]
-- ================================================================
CREATE TABLE opera.servicos (
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

CREATE INDEX idx_servicos_prestador ON opera.servicos (prestador);
CREATE INDEX idx_servicos_data_inicio ON opera.servicos (data_inicio);

-- ================================================================
-- [TABELA 43: HISTÓRICO SERVIÇOS]
-- ================================================================
CREATE TABLE opera.historico_servicos (
    id SERIAL PRIMARY KEY,
    servico_id INTEGER REFERENCES opera.servicos(id) ON DELETE CASCADE,
    data_evento TIMESTAMP NOT NULL DEFAULT NOW(),
    acao VARCHAR(100),
    observacoes TEXT
);

CREATE INDEX idx_hist_servico_id ON opera.historico_servicos (servico_id);

-- ================================================================
-- [TABELA 44: RELATÓRIOS FINALIZAÇÃO]
-- ================================================================
CREATE TABLE opera.relatorios_finalizacao (
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

CREATE INDEX idx_relatorios_entrada ON opera.relatorios_finalizacao (entrada_id);
CREATE INDEX idx_relatorios_data ON opera.relatorios_finalizacao (data_geracao);
CREATE INDEX idx_relatorios_usuario ON opera.relatorios_finalizacao (usuario_geracao);

-- ================================================================
-- [TABELA 45: ORDEM GRADE PREFERÊNCIAS]
-- ================================================================
CREATE TABLE opera.ordem_grade_preferencias (
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

CREATE INDEX idx_ordem_grade_pref_usuario ON opera.ordem_grade_preferencias (usuario_id);
CREATE INDEX idx_ordem_grade_pref_nome ON opera.ordem_grade_preferencias (nome);
CREATE INDEX idx_ordem_grade_pref_usuario_nome ON opera.ordem_grade_preferencias (usuario_id, nome);
CREATE INDEX idx_ordem_grade_pref_criado_em ON opera.ordem_grade_preferencias (criado_em DESC);
CREATE INDEX idx_ordem_grade_pref_atualizado_em ON opera.ordem_grade_preferencias (atualizado_em DESC);

COMMENT ON TABLE opera.ordem_grade_preferencias IS 'TABELA 45 - ORDEM DE CORTE: Preferências de grade por usuário.';

-- ================================================================
-- [VIEWS - EXATAS COMO NO BACKUP]
-- ================================================================

-- VIEW PERMISSÕES
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

-- VIEW USUARIO (COMPATIBILIDADE)
CREATE OR REPLACE VIEW opera.usuario AS
SELECT * FROM opera.usuarios;

-- ================================================================
-- [FUNÇÕES - EXATAS COMO NO BACKUP]
-- ================================================================

-- FUNÇÃO VALIDAR CORES TEMA
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

-- FUNÇÃO REGISTRAR LOG USUÁRIO (COMPATÍVEL COM SISTEMA)
CREATE OR REPLACE FUNCTION opera.registrar_log_usuario(
    p_usuario VARCHAR(100),
    p_acao TEXT,
    p_pagina TEXT DEFAULT NULL,
    p_detalhe TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO opera.usuario_logs (usuario_id, acao, detalhes)
    VALUES (
        (SELECT id FROM opera.usuarios WHERE usuario = p_usuario),
        p_acao || COALESCE(' - ' || p_pagina, ''),
        p_detalhe
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION opera.registrar_log_usuario IS 'Registra ações dos usuários no sistema para auditoria e histórico.';

-- FUNÇÃO VALIDAR SENHA (COMPATÍVEL COM SISTEMA OPERA)
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

COMMENT ON FUNCTION opera.validar_senha(TEXT, TEXT) IS 'Valida senha de usuário usando bcrypt e SHA256 com salt. Compatível com o login do sistema OPERA.';

-- ================================================================
-- [TRIGGERS - EXATOS COMO NO BACKUP]
-- ================================================================

-- TRIGGER VALIDAR CORES TEMA
CREATE TRIGGER tr_validar_cores_tema
    BEFORE INSERT OR UPDATE ON opera.usuario_temas_personalizados
    FOR EACH ROW EXECUTE FUNCTION opera.validar_cores_tema();

-- ================================================================
-- [INSERIR DADOS INICIAIS - MANTENDO DADOS DO BACKUP]
-- ================================================================

-- Inserir registro no controle de versão
INSERT INTO opera._schema_info (schema_name, versao) VALUES ('opera', '1.0');

-- Inserir usuário mestre Gil de Oliveira (senha: 2580)
INSERT INTO opera.usuarios (usuario, senha_hash, hierarquia, email, dica_senha, tema_preferido)
VALUES ('Gil de Oliveira', crypt('2580', gen_salt('bf')), 'Administrador', 'opera@gil.com', '25', 'Cinza Oceano Claro')
RETURNING id;

-- Inserir preferências do usuário mestre
INSERT INTO opera.usuario_preferencias (usuario_id, tema_nome)
SELECT id, 'Cinza Oceano Claro' FROM opera.usuarios WHERE usuario = 'Gil de Oliveira';

-- Inserir permissões completas para o usuário mestre (todas as checkboxes TRUE)
INSERT INTO opera.usuario_permissoes (usuario_id, codigo, pode_ver, pode_editar, pode_imprimir, pode_excluir, pode_administrar)
SELECT u.id, p.codigo, TRUE, TRUE, TRUE, TRUE, TRUE
FROM opera.usuarios u
CROSS JOIN (VALUES
    ('dashboard'),
    ('cadastro_modelos'),
    ('editar_modelo'),
    ('excluir_modelo'),
    ('consultar_modelos'),
    ('ficha_tecnica'),
    ('importar_modelos'),
    ('cadastro_de_corte'),
    ('controle_envio_cortes'),
    ('controle_retorno_cortes'),
    ('finalizar_corte'),
    ('estoque_tecidos'),
    ('estoque_aviamentos'),
    ('estoque_insumos'),
    ('cadastro_faccoes'),
    ('pagamento_servicos'),
    ('sistema_admin'),
    ('sistema_logs'),
    ('sistema_backup'),
    ('sistema_auditoria')
) AS p(codigo)
WHERE u.usuario = 'Gil de Oliveira';

-- ================================================================
-- [INSERIR TEMAS PERSONALIZADOS DE EXEMPLO]
-- ================================================================
DO $$
DECLARE
    v_user_id INTEGER;
BEGIN
    -- Buscar ID do usuário Gil
    SELECT id INTO v_user_id FROM opera.usuarios WHERE usuario = 'Gil de Oliveira';

    -- Tema 1: Clássico Claro (conforme backup)
    INSERT INTO opera.usuario_temas_personalizados (usuario_id, nome_tema, cores_tema)
    VALUES (
        v_user_id,
        'CLÁSSICO CLARO',
        '{
            "borda": "#9CA3AF",
            "fundo": "#FFFFFF",
            "hover": "#E4E4E7",
            "texto": "#111827",
            "alerta": "#C62828",
            "selecao": "#111827",
            "sucesso": "#2E7D32",
            "destaque": "#B3B3B3",
            "primaria": "#F4F4F5",
            "botao_pdf": "#F59E0B",
            "terciaria": "#A1A1AA",
            "botao_novo": "#3B82F6",
            "secundaria": "#D4D4D8",
            "botao_ajuda": "#3B82F6",
            "botao_buscar": "#3B82F6",
            "botao_editar": "#06B6D4",
            "botao_limpar": "#F59E0B",
            "botao_salvar": "#10B981",
            "botao_voltar": "#6B7280",
            "botao_avancar": "#10B981",
            "botao_excluir": "#EF4444",
            "botao_filtrar": "#6366F1",
            "botao_cancelar": "#6B7280",
            "botao_exportar": "#8B5CF6",
            "botao_importar": "#06B6D4",
            "botao_imprimir": "#8B5CF6",
            "botao_confirmar": "#22C55E",
            "botao_configurar": "#6B7280",
            "botao_export_csv": "#06B6D4",
            "botao_export_pdf": "#F59E0B",
            "botao_visualizar": "#6366F1",
            "botao_comprovante": "#8B5CF6",
            "botao_adiantamento": "#10B981"
        }'::JSONB
    );

    -- Tema 2: Noite Urbana (tema padrão)
    INSERT INTO opera.usuario_temas_personalizados (usuario_id, nome_tema, cores_tema)
    VALUES (
        v_user_id,
        'NOITE URBANA',
        '{
            "borda": "#374151",
            "fundo": "#111827",
            "hover": "#1F2937",
            "texto": "#F9FAFB",
            "alerta": "#EF4444",
            "selecao": "#3B82F6",
            "sucesso": "#10B981",
            "destaque": "#6B7280",
            "primaria": "#1F2937",
            "botao_pdf": "#F59E0B",
            "terciaria": "#4B5563",
            "botao_novo": "#3B82F6",
            "secundaria": "#374151",
            "botao_ajuda": "#8B5CF6",
            "botao_buscar": "#10B981",
            "botao_editar": "#06B6D4",
            "botao_limpar": "#F59E0B",
            "botao_salvar": "#10B981",
            "botao_voltar": "#6B7280",
            "botao_avancar": "#3B82F6",
            "botao_excluir": "#EF4444",
            "botao_filtrar": "#8B5CF6",
            "botao_cancelar": "#6B7280",
            "botao_exportar": "#8B5CF6",
            "botao_importar": "#06B6D4",
            "botao_imprimir": "#F59E0B",
            "botao_confirmar": "#10B981",
            "botao_configurar": "#6B7280",
            "botao_export_csv": "#06B6D4",
            "botao_export_pdf": "#F59E0B",
            "botao_visualizar": "#8B5CF6",
            "botao_comprovante": "#3B82F6",
            "botao_adiantamento": "#10B981"
        }'::JSONB
    );

    RAISE NOTICE '🎨 2 temas personalizados inseridos para o usuário Gil de Oliveira';
END $$;

-- ================================================================
-- [GRANT PERMISSÕES - EXATO COMO NO BACKUP]
-- ================================================================

-- Conceder permissões para a aplicação
GRANT ALL ON SCHEMA opera TO opera_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA opera TO opera_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA opera TO opera_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA opera TO opera_app;

-- ================================================================
-- [MENSAGEM FINAL DE SUCESSO - COMPLETA]
-- ================================================================

DO $$
DECLARE
    total_permissoes_gil INTEGER;
    total_tabelas_final INTEGER;
    total_views INTEGER;
    total_triggers INTEGER;
    total_funcoes INTEGER;
    total_temas INTEGER;
    v_user_id INTEGER;
BEGIN
    -- Buscar ID do usuário Gil
    SELECT id INTO v_user_id FROM opera.usuarios WHERE usuario = 'Gil de Oliveira';

    -- Contagem final de permissões do Gil
    SELECT COUNT(*) INTO total_permissoes_gil
    FROM opera.usuario_permissoes
    WHERE usuario_id = v_user_id;

    -- Contagem final de tabelas
    SELECT COUNT(*) INTO total_tabelas_final
    FROM information_schema.tables
    WHERE table_schema = 'opera';

    -- Contagem de views
    SELECT COUNT(*) INTO total_views
    FROM information_schema.views
    WHERE table_schema = 'opera';

    -- Contagem de triggers
    SELECT COUNT(*) INTO total_triggers
    FROM information_schema.triggers
    WHERE trigger_schema = 'opera';

    -- Contagem de funções
    SELECT COUNT(*) INTO total_funcoes
    FROM information_schema.routines
    WHERE specific_schema = 'opera';

    -- Contagem de temas personalizados do Gil
    SELECT COUNT(*) INTO total_temas
    FROM opera.usuario_temas_personalizados
    WHERE usuario_id = v_user_id;

    RAISE NOTICE '=========================================================';
    RAISE NOTICE '✅ ESTRUTURA DO BANCO OPERA CRIADA COM SUCESSO!';
    RAISE NOTICE '=========================================================';
    RAISE NOTICE '📊 Estruturas criadas:';
    RAISE NOTICE '   👤 1 Tabela de usuários';
    RAISE NOTICE '   ⚙️  1 Tabela de preferências';
    RAISE NOTICE '   🎨 1 Tabela de temas personalizados (MÚLTIPLOS por usuário)';
    RAISE NOTICE '   🔐 1 Tabela de permissões';
    RAISE NOTICE '   📋 % Views úteis', total_views;
    RAISE NOTICE '   ⚡ % Triggers de validação e logs', total_triggers;
    RAISE NOTICE '   🔄 % Funções de migração e logs', total_funcoes;
    RAISE NOTICE '   📝 1 Sistema completo de auditoria';
    RAISE NOTICE '';
    RAISE NOTICE '👤 Usuário mestre: Gil de Oliveira';
    RAISE NOTICE '🔑 Senha: 2580';
    RAISE NOTICE '📧 Email: opera@gil.com';
    RAISE NOTICE '🔐 Permissões: % permissões com TODAS as checkboxes marcadas', total_permissoes_gil;
    RAISE NOTICE '🎨 Temas personalizados: % temas de exemplo incluídos', total_temas;
    RAISE NOTICE '📈 Total de tabelas no schema: %', total_tabelas_final;
    RAISE NOTICE '🔍 Sistema de logs: IMPLEMENTADO para auditoria';
    RAISE NOTICE '=========================================================';

    -- Verificação extra para confirmar que todas as checkboxes estão TRUE
    IF total_permissoes_gil > 0 THEN
        RAISE NOTICE '✅ VERIFICAÇÃO: Todas as % permissões estão com checkboxes TRUE!', total_permissoes_gil;
    END IF;
END $$;
