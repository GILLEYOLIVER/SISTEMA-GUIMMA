--
-- PostgreSQL database dump
--

\restrict F4fm52NQX4Vjnr8PEOgemkxyIc5UH7728Vd2uFXCizUseTmpSC6SOSjmZUdPvTS

-- Dumped from database version 18.0
-- Dumped by pg_dump version 18.0

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: opera; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA opera;


ALTER SCHEMA opera OWNER TO postgres;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: limpar_logs_antigos(integer); Type: FUNCTION; Schema: opera; Owner: postgres
--

CREATE FUNCTION opera.limpar_logs_antigos(p_dias_manter integer DEFAULT 90) RETURNS integer
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION opera.limpar_logs_antigos(p_dias_manter integer) OWNER TO postgres;

--
-- Name: FUNCTION limpar_logs_antigos(p_dias_manter integer); Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON FUNCTION opera.limpar_logs_antigos(p_dias_manter integer) IS 'Remove logs antigos para manter o desempenho do sistema.';


--
-- Name: log_login_usuario(); Type: FUNCTION; Schema: opera; Owner: postgres
--

CREATE FUNCTION opera.log_login_usuario() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Atualiza último login
    NEW.ultimo_login = NOW();

    -- Registra log de login
    PERFORM opera.registrar_log_usuario(
        NEW.usuario,
        'Login no sistema',
        'Dashboard',
        'Usuário acessou o sistema'
    );

    RETURN NEW;
END;
$$;


ALTER FUNCTION opera.log_login_usuario() OWNER TO postgres;

--
-- Name: migrar_tema_antigo_para_novo(integer); Type: FUNCTION; Schema: opera; Owner: postgres
--

CREATE FUNCTION opera.migrar_tema_antigo_para_novo(p_usuario_id integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION opera.migrar_tema_antigo_para_novo(p_usuario_id integer) OWNER TO postgres;

--
-- Name: registrar_log_usuario(character varying, text, text, text); Type: FUNCTION; Schema: opera; Owner: postgres
--

CREATE FUNCTION opera.registrar_log_usuario(p_usuario character varying, p_acao text, p_pagina text DEFAULT NULL::text, p_detalhe text DEFAULT NULL::text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    INSERT INTO opera.usuario_logs (usuario, acao, pagina, detalhe)
    VALUES (p_usuario, p_acao, p_pagina, p_detalhe);
END;
$$;


ALTER FUNCTION opera.registrar_log_usuario(p_usuario character varying, p_acao text, p_pagina text, p_detalhe text) OWNER TO postgres;

--
-- Name: FUNCTION registrar_log_usuario(p_usuario character varying, p_acao text, p_pagina text, p_detalhe text); Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON FUNCTION opera.registrar_log_usuario(p_usuario character varying, p_acao text, p_pagina text, p_detalhe text) IS 'Registra ações dos usuários no sistema para auditoria e histórico.';


--
-- Name: validar_cores_tema(); Type: FUNCTION; Schema: opera; Owner: postgres
--

CREATE FUNCTION opera.validar_cores_tema() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION opera.validar_cores_tema() OWNER TO postgres;

--
-- Name: validar_senha(text, text); Type: FUNCTION; Schema: opera; Owner: postgres
--

CREATE FUNCTION opera.validar_senha(p_usuario text, p_senha text) RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER
    AS $_$
DECLARE
    v_hash TEXT;
    v_bcrypt_ok BOOLEAN := FALSE;
    v_sha256_ok BOOLEAN := FALSE;
BEGIN
    -- ------------------------------------------------------------------------
    -- Buscar hash da tabela de usuários
    -- ------------------------------------------------------------------------
    SELECT senha_hash INTO v_hash
    FROM opera.usuarios
    WHERE usuario = p_usuario
    LIMIT 1;

    IF v_hash IS NULL THEN
        RETURN FALSE;
    END IF;

    -- ------------------------------------------------------------------------
    -- Validação bcrypt ($2a$, $2b$, $2y$)
    -- ------------------------------------------------------------------------
    IF v_hash LIKE '$2%' THEN
        BEGIN
            IF crypt(p_senha, v_hash) = v_hash THEN
                v_bcrypt_ok := TRUE;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            v_bcrypt_ok := FALSE;
        END;
    END IF;

    -- ------------------------------------------------------------------------
    -- Validação SHA256 com salt igual ao da aplicação
    -- ------------------------------------------------------------------------
    IF NOT v_bcrypt_ok THEN
        v_sha256_ok :=
            encode(
                digest('sistema_profissional_v2.2' || p_senha, 'sha256'),
                'hex'
            ) = v_hash;
    END IF;

    RETURN v_bcrypt_ok OR v_sha256_ok;
END;
$_$;


ALTER FUNCTION opera.validar_senha(p_usuario text, p_senha text) OWNER TO postgres;

--
-- Name: FUNCTION validar_senha(p_usuario text, p_senha text); Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON FUNCTION opera.validar_senha(p_usuario text, p_senha text) IS 'Valida senha de usuário usando bcrypt e SHA256 com salt. Compatível com o login do sistema OPERA.';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: _schema_info; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera._schema_info (
    id integer NOT NULL,
    schema_name text DEFAULT 'opera'::text,
    versao text DEFAULT '1.0'::text,
    criado_em timestamp without time zone DEFAULT now(),
    atualizado_em timestamp without time zone DEFAULT now()
);


ALTER TABLE opera._schema_info OWNER TO postgres;

--
-- Name: _schema_info_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera._schema_info_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera._schema_info_id_seq OWNER TO postgres;

--
-- Name: _schema_info_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera._schema_info_id_seq OWNED BY opera._schema_info.id;


--
-- Name: adiantamento_faccao; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.adiantamento_faccao (
    id integer NOT NULL,
    corte_id integer,
    codigo_modelo character varying(100),
    faccao character varying(200),
    valor numeric(12,2) NOT NULL,
    forma_pagamento character varying(50),
    parcelas integer DEFAULT 1,
    data_hora timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE opera.adiantamento_faccao OWNER TO postgres;

--
-- Name: adiantamento_faccao_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.adiantamento_faccao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.adiantamento_faccao_id_seq OWNER TO postgres;

--
-- Name: adiantamento_faccao_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.adiantamento_faccao_id_seq OWNED BY opera.adiantamento_faccao.id;


--
-- Name: cadastro_de_corte; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_de_corte (
    id integer NOT NULL,
    numero_ordem character varying(50),
    ordem_corte character varying(50),
    codigo character varying(100),
    descricao text,
    descricao_corte text,
    data date,
    data_envio date,
    comprimento_matriz numeric(12,3),
    largura_matriz numeric(12,3),
    cortador character varying(100),
    ajudante character varying(100),
    auxiliar character varying(100),
    total_folhas integer,
    metros_utilizados numeric(12,3),
    bobinas_utilizadas numeric(12,3),
    composicao_tecido character varying(100),
    pp integer DEFAULT 0 NOT NULL,
    p integer DEFAULT 0 NOT NULL,
    m integer DEFAULT 0 NOT NULL,
    g integer DEFAULT 0 NOT NULL,
    gg integer DEFAULT 0 NOT NULL,
    g1 integer DEFAULT 0 NOT NULL,
    g2 integer DEFAULT 0 NOT NULL,
    g3 integer DEFAULT 0 NOT NULL,
    total_pecas integer DEFAULT 0 NOT NULL,
    rendimento numeric(12,4),
    observacoes text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.cadastro_de_corte OWNER TO postgres;

--
-- Name: cadastro_de_corte_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cadastro_de_corte_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cadastro_de_corte_id_seq OWNER TO postgres;

--
-- Name: cadastro_de_corte_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_de_corte_id_seq OWNED BY opera.cadastro_de_corte.id;


--
-- Name: cadastro_de_corte_lotes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_de_corte_lotes (
    id integer NOT NULL,
    cadastro_id integer NOT NULL,
    lote character varying(100),
    tecido character varying(200),
    cor character varying(50),
    composicao character varying(100),
    bobinas numeric(12,3),
    folhas numeric(12,3),
    pp integer,
    p integer,
    m integer,
    g integer,
    gg integer,
    g1 integer,
    g2 integer,
    g3 integer,
    total_lote integer
);


ALTER TABLE opera.cadastro_de_corte_lotes OWNER TO postgres;

--
-- Name: cadastro_de_corte_lotes_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cadastro_de_corte_lotes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cadastro_de_corte_lotes_id_seq OWNER TO postgres;

--
-- Name: cadastro_de_corte_lotes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_de_corte_lotes_id_seq OWNED BY opera.cadastro_de_corte_lotes.id;


--
-- Name: cadastro_de_corte_tecidos; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_de_corte_tecidos (
    id integer NOT NULL,
    cadastro_id integer NOT NULL,
    tecido character varying(200),
    cor character varying(50),
    composicao character varying(100),
    bobinas numeric(12,3),
    folhas numeric(12,3),
    pp integer,
    p integer,
    m integer,
    g integer,
    gg integer,
    g1 integer,
    g2 integer,
    g3 integer,
    total_pecas integer
);


ALTER TABLE opera.cadastro_de_corte_tecidos OWNER TO postgres;

--
-- Name: cadastro_de_corte_tecidos_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cadastro_de_corte_tecidos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cadastro_de_corte_tecidos_id_seq OWNER TO postgres;

--
-- Name: cadastro_de_corte_tecidos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_de_corte_tecidos_id_seq OWNED BY opera.cadastro_de_corte_tecidos.id;


--
-- Name: cadastro_faccoes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_faccoes (
    id integer NOT NULL,
    codigo character varying(10) NOT NULL,
    nome character varying(200) NOT NULL,
    tipo_prestador character varying(50) DEFAULT 'Facção'::character varying,
    telefone character varying(50),
    endereco text,
    titular_da_conta character varying(200),
    cpf character varying(20),
    banco character varying(50),
    agencia character varying(20),
    conta character varying(30),
    pix character varying(100),
    data date,
    data_atualizacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ativo boolean DEFAULT true
);


ALTER TABLE opera.cadastro_faccoes OWNER TO postgres;

--
-- Name: cadastro_faccoes_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cadastro_faccoes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cadastro_faccoes_id_seq OWNER TO postgres;

--
-- Name: cadastro_faccoes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_faccoes_id_seq OWNED BY opera.cadastro_faccoes.id;


--
-- Name: cadastro_modelos_aviamentos; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_modelos_aviamentos (
    id integer NOT NULL,
    codigo_modelo character varying(100) NOT NULL,
    cadastro_id integer,
    codigo_aviamento character varying(100),
    descricao text,
    cor character varying(50),
    fornecedor character varying(100),
    quantidade numeric(12,4) DEFAULT 0,
    valor_unidade numeric(12,2) DEFAULT 0,
    valor_total numeric(12,2) DEFAULT 0,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.cadastro_modelos_aviamentos OWNER TO postgres;

--
-- Name: cadastro_modelos_aviamentos_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cadastro_modelos_aviamentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cadastro_modelos_aviamentos_id_seq OWNER TO postgres;

--
-- Name: cadastro_modelos_aviamentos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_aviamentos_id_seq OWNED BY opera.cadastro_modelos_aviamentos.id;


--
-- Name: cadastro_modelos_cabecalho; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_modelos_cabecalho (
    id integer NOT NULL,
    codigo character varying(100) NOT NULL,
    descricao text,
    colecao character varying(100),
    tamanho_base character varying(10),
    dificuldade character varying(50),
    modelista character varying(100),
    pilotista character varying(100),
    custo_total numeric(12,2) DEFAULT 0,
    pronto_producao boolean DEFAULT false,
    grade_disponivel text,
    data_criacao timestamp without time zone DEFAULT now(),
    data_atualizacao timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.cadastro_modelos_cabecalho OWNER TO postgres;

--
-- Name: cadastro_modelos_cabecalho_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cadastro_modelos_cabecalho_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cadastro_modelos_cabecalho_id_seq OWNER TO postgres;

--
-- Name: cadastro_modelos_cabecalho_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_cabecalho_id_seq OWNED BY opera.cadastro_modelos_cabecalho.id;


--
-- Name: cadastro_modelos_grade; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_modelos_grade (
    id integer NOT NULL,
    modelo_id integer NOT NULL,
    tamanho character varying(10) NOT NULL,
    disponivel boolean DEFAULT true
);


ALTER TABLE opera.cadastro_modelos_grade OWNER TO postgres;

--
-- Name: cadastro_modelos_grade_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cadastro_modelos_grade_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cadastro_modelos_grade_id_seq OWNER TO postgres;

--
-- Name: cadastro_modelos_grade_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_grade_id_seq OWNED BY opera.cadastro_modelos_grade.id;


--
-- Name: cadastro_modelos_imagens; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_modelos_imagens (
    id integer NOT NULL,
    codigo_modelo character varying(100) NOT NULL,
    cadastro_id integer,
    tipo_imagem character varying(20),
    caminho_imagem text,
    descricao text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.cadastro_modelos_imagens OWNER TO postgres;

--
-- Name: cadastro_modelos_imagens_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cadastro_modelos_imagens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cadastro_modelos_imagens_id_seq OWNER TO postgres;

--
-- Name: cadastro_modelos_imagens_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_imagens_id_seq OWNED BY opera.cadastro_modelos_imagens.id;


--
-- Name: cadastro_modelos_outros; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_modelos_outros (
    id integer NOT NULL,
    codigo_modelo character varying(100) NOT NULL,
    cadastro_id integer,
    codigo character varying(100),
    descricao text,
    cor character varying(50),
    fornecedor character varying(100),
    unidade character varying(20),
    quantidade numeric(12,4) DEFAULT 0,
    preco numeric(12,2) DEFAULT 0,
    total numeric(12,2) DEFAULT 0,
    observacoes text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.cadastro_modelos_outros OWNER TO postgres;

--
-- Name: cadastro_modelos_outros_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cadastro_modelos_outros_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cadastro_modelos_outros_id_seq OWNER TO postgres;

--
-- Name: cadastro_modelos_outros_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_outros_id_seq OWNED BY opera.cadastro_modelos_outros.id;


--
-- Name: cadastro_modelos_outros_servicos; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_modelos_outros_servicos (
    id integer NOT NULL,
    codigo_modelo character varying(100) NOT NULL,
    cadastro_id integer,
    codigo_servico character varying(100),
    descricao text,
    tipo_servico character varying(100),
    fornecedor character varying(100),
    unidade character varying(20),
    quantidade numeric(12,4) DEFAULT 0,
    valor_unidade numeric(12,2) DEFAULT 0,
    valor_total numeric(12,2) DEFAULT 0,
    observacoes text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.cadastro_modelos_outros_servicos OWNER TO postgres;

--
-- Name: cadastro_modelos_outros_servicos_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cadastro_modelos_outros_servicos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cadastro_modelos_outros_servicos_id_seq OWNER TO postgres;

--
-- Name: cadastro_modelos_outros_servicos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_outros_servicos_id_seq OWNED BY opera.cadastro_modelos_outros_servicos.id;


--
-- Name: cadastro_modelos_tecidos; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_modelos_tecidos (
    id integer NOT NULL,
    codigo_modelo character varying(100) NOT NULL,
    cadastro_id integer,
    codigo_tecido character varying(100),
    descricao text,
    cor character varying(50),
    fornecedor character varying(100),
    composicao character varying(100),
    metros_peca numeric(12,4) DEFAULT 0,
    valor_metro numeric(12,2) DEFAULT 0,
    valor_total numeric(12,2) DEFAULT 0,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.cadastro_modelos_tecidos OWNER TO postgres;

--
-- Name: cadastro_modelos_tecidos_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cadastro_modelos_tecidos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cadastro_modelos_tecidos_id_seq OWNER TO postgres;

--
-- Name: cadastro_modelos_tecidos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_tecidos_id_seq OWNED BY opera.cadastro_modelos_tecidos.id;


--
-- Name: controle_envio_cortes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.controle_envio_cortes (
    id integer NOT NULL,
    data_envio date,
    servico character varying(100),
    corte_id integer,
    ordem_corte character varying(50),
    codigo_corte character varying(100),
    descricao_corte text,
    destino character varying(200),
    costureira character varying(200),
    faccao character varying(200),
    quantidade_total integer,
    valor_peca numeric(12,2),
    valor_total numeric(12,2),
    status character varying(50) DEFAULT 'Em Conferência'::character varying,
    observacao text,
    pp integer,
    p integer,
    m integer,
    g integer,
    gg integer,
    g1 integer,
    g2 integer,
    g3 integer
);


ALTER TABLE opera.controle_envio_cortes OWNER TO postgres;

--
-- Name: controle_envio_cortes_detalhes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.controle_envio_cortes_detalhes (
    id integer NOT NULL,
    envio_id integer NOT NULL,
    prestador_servico character varying(200),
    tipo_servico character varying(100),
    valor_pp numeric(12,2) DEFAULT 0,
    valor_p numeric(12,2) DEFAULT 0,
    valor_m numeric(12,2) DEFAULT 0,
    valor_g numeric(12,2) DEFAULT 0,
    valor_gg numeric(12,2) DEFAULT 0,
    valor_g1 numeric(12,2) DEFAULT 0,
    valor_g2 numeric(12,2) DEFAULT 0,
    valor_g3 numeric(12,2) DEFAULT 0,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.controle_envio_cortes_detalhes OWNER TO postgres;

--
-- Name: controle_envio_cortes_detalhes_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.controle_envio_cortes_detalhes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.controle_envio_cortes_detalhes_id_seq OWNER TO postgres;

--
-- Name: controle_envio_cortes_detalhes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.controle_envio_cortes_detalhes_id_seq OWNED BY opera.controle_envio_cortes_detalhes.id;


--
-- Name: controle_envio_cortes_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.controle_envio_cortes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.controle_envio_cortes_id_seq OWNER TO postgres;

--
-- Name: controle_envio_cortes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.controle_envio_cortes_id_seq OWNED BY opera.controle_envio_cortes.id;


--
-- Name: controle_retorno_cortes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.controle_retorno_cortes (
    id integer NOT NULL,
    envio_id integer NOT NULL,
    data_chegada date NOT NULL,
    telefone_encarregado text,
    telefone_acabamento text,
    resumo_piloto text,
    aviamentos_recebidos text,
    outros_recebidos text,
    observacoes_gerais text,
    total_entregue integer DEFAULT 0,
    total_copias integer DEFAULT 0,
    total_defeitos integer DEFAULT 0,
    total_faltantes integer DEFAULT 0,
    total_regulares integer DEFAULT 0,
    valor_total numeric(12,2) DEFAULT 0,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.controle_retorno_cortes OWNER TO postgres;

--
-- Name: controle_retorno_cortes_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.controle_retorno_cortes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.controle_retorno_cortes_id_seq OWNER TO postgres;

--
-- Name: controle_retorno_cortes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.controle_retorno_cortes_id_seq OWNED BY opera.controle_retorno_cortes.id;


--
-- Name: cortes_finalizados; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cortes_finalizados (
    id integer NOT NULL,
    corte_id integer,
    entrada_id integer,
    codigo character varying(100),
    descricao text,
    costureira character varying(200),
    data_envio date,
    data_chegada date,
    data_final date,
    qtd_enviada integer,
    total_pecas integer,
    quantidade_finalizada integer,
    observacao text,
    status character varying(50),
    data_conferencia timestamp without time zone,
    valor_peca numeric(12,2),
    bonificacao boolean DEFAULT false,
    pago boolean DEFAULT false,
    data_pagamento date,
    qtd_pp integer DEFAULT 0,
    qtd_p integer DEFAULT 0,
    qtd_m integer DEFAULT 0,
    qtd_g integer DEFAULT 0,
    qtd_gg integer DEFAULT 0,
    qtd_g1 integer DEFAULT 0,
    qtd_g2 integer DEFAULT 0,
    qtd_g3 integer DEFAULT 0,
    qtd_defeito_pp integer DEFAULT 0,
    qtd_defeito_p integer DEFAULT 0,
    qtd_defeito_m integer DEFAULT 0,
    qtd_defeito_g integer DEFAULT 0,
    qtd_defeito_gg integer DEFAULT 0,
    qtd_defeito_g1 integer DEFAULT 0,
    qtd_defeito_g2 integer DEFAULT 0,
    qtd_defeito_g3 integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.cortes_finalizados OWNER TO postgres;

--
-- Name: cortes_finalizados_completo; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cortes_finalizados_completo (
    id integer NOT NULL,
    entrada_id integer,
    corte_id integer,
    codigo character varying(100),
    descricao text,
    costureira character varying(200),
    servico character varying(100),
    data_envio date,
    data_chegada date,
    data_conferencia timestamp without time zone,
    qtd_enviada integer DEFAULT 0,
    total_entregue integer DEFAULT 0,
    total_copias integer DEFAULT 0,
    total_defeitos integer DEFAULT 0,
    total_faltantes integer DEFAULT 0,
    total_regulares integer DEFAULT 0,
    valor_peca numeric(12,2) DEFAULT 0,
    valor_total numeric(12,2) DEFAULT 0,
    bonificacao boolean DEFAULT false,
    valor_bonificacao numeric(12,2) DEFAULT 0,
    qtd_pp integer DEFAULT 0,
    qtd_p integer DEFAULT 0,
    qtd_m integer DEFAULT 0,
    qtd_g integer DEFAULT 0,
    qtd_gg integer DEFAULT 0,
    qtd_g1 integer DEFAULT 0,
    qtd_g2 integer DEFAULT 0,
    qtd_g3 integer DEFAULT 0,
    qtd_defeito_pp integer DEFAULT 0,
    qtd_defeito_p integer DEFAULT 0,
    qtd_defeito_m integer DEFAULT 0,
    qtd_defeito_g integer DEFAULT 0,
    qtd_defeito_gg integer DEFAULT 0,
    qtd_defeito_g1 integer DEFAULT 0,
    qtd_defeito_g2 integer DEFAULT 0,
    qtd_defeito_g3 integer DEFAULT 0,
    qtd_regular_pp integer DEFAULT 0,
    qtd_regular_p integer DEFAULT 0,
    qtd_regular_m integer DEFAULT 0,
    qtd_regular_g integer DEFAULT 0,
    qtd_regular_gg integer DEFAULT 0,
    qtd_regular_g1 integer DEFAULT 0,
    qtd_regular_g2 integer DEFAULT 0,
    qtd_regular_g3 integer DEFAULT 0,
    status character varying(50) DEFAULT 'Finalizado'::character varying,
    observacoes text,
    usuario_finalizacao character varying(100),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.cortes_finalizados_completo OWNER TO postgres;

--
-- Name: cortes_finalizados_completo_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cortes_finalizados_completo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cortes_finalizados_completo_id_seq OWNER TO postgres;

--
-- Name: cortes_finalizados_completo_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cortes_finalizados_completo_id_seq OWNED BY opera.cortes_finalizados_completo.id;


--
-- Name: cortes_finalizados_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.cortes_finalizados_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.cortes_finalizados_id_seq OWNER TO postgres;

--
-- Name: cortes_finalizados_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cortes_finalizados_id_seq OWNED BY opera.cortes_finalizados.id;


--
-- Name: entrada_acabamento; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.entrada_acabamento (
    id integer NOT NULL,
    envio_id integer NOT NULL,
    data_chegada date,
    total_entregue integer,
    total_defeitos integer,
    total_faltantes integer,
    total_regulares integer,
    valor_total numeric(12,2),
    pago boolean DEFAULT false,
    data_pagamento date
);


ALTER TABLE opera.entrada_acabamento OWNER TO postgres;

--
-- Name: entrada_acabamento_detalhes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.entrada_acabamento_detalhes (
    id integer NOT NULL,
    entrada_id integer NOT NULL,
    observacoes_finalizacao text,
    bonificacao_aplicada boolean DEFAULT false,
    usuario_conferencia character varying(100),
    total_entregue integer DEFAULT 0,
    total_copias integer DEFAULT 0,
    total_defeitos integer DEFAULT 0,
    total_faltantes integer DEFAULT 0,
    total_regulares integer DEFAULT 0,
    valor_total_pagar numeric(12,2) DEFAULT 0,
    status_finalizacao character varying(20) DEFAULT 'Pendente'::character varying,
    data_conferencia timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.entrada_acabamento_detalhes OWNER TO postgres;

--
-- Name: entrada_acabamento_detalhes_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.entrada_acabamento_detalhes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.entrada_acabamento_detalhes_id_seq OWNER TO postgres;

--
-- Name: entrada_acabamento_detalhes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.entrada_acabamento_detalhes_id_seq OWNED BY opera.entrada_acabamento_detalhes.id;


--
-- Name: entrada_acabamento_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.entrada_acabamento_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.entrada_acabamento_id_seq OWNER TO postgres;

--
-- Name: entrada_acabamento_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.entrada_acabamento_id_seq OWNED BY opera.entrada_acabamento.id;


--
-- Name: envio_detalhes_tamanho; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.envio_detalhes_tamanho (
    envio_id integer NOT NULL,
    tamanho character varying(10) NOT NULL,
    quantidade integer DEFAULT 0,
    quantidade_pilotos integer DEFAULT 0,
    valor_peca numeric(12,2) DEFAULT 0
);


ALTER TABLE opera.envio_detalhes_tamanho OWNER TO postgres;

--
-- Name: envios_cortes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.envios_cortes (
    id integer NOT NULL,
    data_envio date NOT NULL,
    prestador_id integer,
    tipo_servico text,
    corte_id integer,
    qtd_pp integer DEFAULT 0,
    qtd_p integer DEFAULT 0,
    qtd_m integer DEFAULT 0,
    qtd_g integer DEFAULT 0,
    qtd_gg integer DEFAULT 0,
    qtd_g1 integer DEFAULT 0,
    qtd_g2 integer DEFAULT 0,
    qtd_g3 integer DEFAULT 0,
    piloto_pp integer DEFAULT 0,
    piloto_p integer DEFAULT 0,
    piloto_m integer DEFAULT 0,
    piloto_g integer DEFAULT 0,
    piloto_gg integer DEFAULT 0,
    piloto_g1 integer DEFAULT 0,
    piloto_g2 integer DEFAULT 0,
    piloto_g3 integer DEFAULT 0,
    valor_pp numeric(10,2) DEFAULT 0,
    valor_p numeric(10,2) DEFAULT 0,
    valor_m numeric(10,2) DEFAULT 0,
    valor_g numeric(10,2) DEFAULT 0,
    valor_gg numeric(10,2) DEFAULT 0,
    valor_g1 numeric(10,2) DEFAULT 0,
    valor_g2 numeric(10,2) DEFAULT 0,
    valor_g3 numeric(10,2) DEFAULT 0,
    aviamentos text,
    outros text,
    observacoes text,
    tel_encarregado text,
    tel_acabamento text,
    previsao_entrega date,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.envios_cortes OWNER TO postgres;

--
-- Name: envios_cortes_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.envios_cortes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.envios_cortes_id_seq OWNER TO postgres;

--
-- Name: envios_cortes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.envios_cortes_id_seq OWNED BY opera.envios_cortes.id;


--
-- Name: estoque_aviamentos; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.estoque_aviamentos (
    id integer NOT NULL,
    codigo character varying(100) NOT NULL,
    descricao text,
    cor character varying(50) NOT NULL,
    fornecedor character varying(100),
    quantidade numeric(12,3) DEFAULT 0,
    unidade character varying(50) DEFAULT 'unidades'::character varying,
    valor_unidade numeric(12,2) DEFAULT 0,
    observacoes text,
    localizacao character varying(100),
    data_entrada date DEFAULT CURRENT_DATE,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.estoque_aviamentos OWNER TO postgres;

--
-- Name: estoque_aviamentos_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.estoque_aviamentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.estoque_aviamentos_id_seq OWNER TO postgres;

--
-- Name: estoque_aviamentos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_aviamentos_id_seq OWNED BY opera.estoque_aviamentos.id;


--
-- Name: estoque_escritorio; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.estoque_escritorio (
    id integer NOT NULL,
    codigo character varying(100) NOT NULL,
    descricao text,
    fornecedor character varying(100),
    cor character varying(50) NOT NULL,
    quantidade numeric(12,3) DEFAULT 0,
    unidade character varying(50) DEFAULT 'unidades'::character varying,
    valor_unidade numeric(12,2) DEFAULT 0,
    tipo character varying(100),
    categoria character varying(100),
    observacoes text,
    localizacao character varying(100),
    data_entrada date DEFAULT CURRENT_DATE,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.estoque_escritorio OWNER TO postgres;

--
-- Name: estoque_escritorio_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.estoque_escritorio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.estoque_escritorio_id_seq OWNER TO postgres;

--
-- Name: estoque_escritorio_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_escritorio_id_seq OWNED BY opera.estoque_escritorio.id;


--
-- Name: estoque_insumos; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.estoque_insumos (
    id integer NOT NULL,
    codigo character varying(100) NOT NULL,
    descricao text,
    fornecedor character varying(100),
    cor character varying(50) NOT NULL,
    quantidade numeric(12,3) DEFAULT 0,
    unidade character varying(50) DEFAULT 'unidades'::character varying,
    valor_unidade numeric(12,2) DEFAULT 0,
    tipo character varying(100),
    categoria character varying(100),
    observacoes text,
    localizacao character varying(100),
    data_entrada date DEFAULT CURRENT_DATE,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.estoque_insumos OWNER TO postgres;

--
-- Name: estoque_insumos_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.estoque_insumos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.estoque_insumos_id_seq OWNER TO postgres;

--
-- Name: estoque_insumos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_insumos_id_seq OWNED BY opera.estoque_insumos.id;


--
-- Name: estoque_limpeza; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.estoque_limpeza (
    id integer NOT NULL,
    codigo character varying(100) NOT NULL,
    descricao text,
    fornecedor character varying(100),
    cor character varying(50) NOT NULL,
    quantidade numeric(12,3) DEFAULT 0,
    unidade character varying(50) DEFAULT 'unidades'::character varying,
    valor_unidade numeric(12,2) DEFAULT 0,
    tipo character varying(100),
    categoria character varying(100),
    observacoes text,
    localizacao character varying(100),
    data_entrada date DEFAULT CURRENT_DATE,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.estoque_limpeza OWNER TO postgres;

--
-- Name: estoque_limpeza_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.estoque_limpeza_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.estoque_limpeza_id_seq OWNER TO postgres;

--
-- Name: estoque_limpeza_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_limpeza_id_seq OWNED BY opera.estoque_limpeza.id;


--
-- Name: estoque_outros; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.estoque_outros (
    id integer NOT NULL,
    codigo character varying(100) NOT NULL,
    descricao text,
    fornecedor character varying(100),
    cor character varying(50) NOT NULL,
    quantidade numeric(12,3) DEFAULT 0,
    unidade character varying(50) DEFAULT 'unidades'::character varying,
    valor_unidade numeric(12,2) DEFAULT 0,
    tipo character varying(100),
    categoria character varying(100),
    observacoes text,
    localizacao character varying(100),
    data_entrada date DEFAULT CURRENT_DATE,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.estoque_outros OWNER TO postgres;

--
-- Name: estoque_outros_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.estoque_outros_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.estoque_outros_id_seq OWNER TO postgres;

--
-- Name: estoque_outros_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_outros_id_seq OWNED BY opera.estoque_outros.id;


--
-- Name: estoque_saida_log; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.estoque_saida_log (
    id bigint NOT NULL,
    data_hora timestamp without time zone DEFAULT now() NOT NULL,
    tipo_estoque character varying(30) NOT NULL,
    item_id bigint NOT NULL,
    codigo character varying(100),
    descricao text,
    cor character varying(50),
    quantidade numeric(10,3) NOT NULL,
    unidade character varying(20),
    motivo character varying(100),
    observacoes text,
    usuario character varying(100)
);


ALTER TABLE opera.estoque_saida_log OWNER TO postgres;

--
-- Name: estoque_saida_log_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.estoque_saida_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.estoque_saida_log_id_seq OWNER TO postgres;

--
-- Name: estoque_saida_log_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_saida_log_id_seq OWNED BY opera.estoque_saida_log.id;


--
-- Name: estoque_tecidos; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.estoque_tecidos (
    id integer NOT NULL,
    codigo character varying(100) NOT NULL,
    descricao text,
    cor character varying(50) NOT NULL,
    composicao character varying(100),
    fornecedor character varying(100),
    metros numeric(12,3) DEFAULT 0,
    kilos numeric(12,3) DEFAULT 0,
    valor_metro numeric(12,2) DEFAULT 0,
    valor_kilo numeric(12,2) DEFAULT 0,
    unidade character varying(50) DEFAULT 'metros'::character varying,
    observacoes text,
    localizacao character varying(100),
    data_entrada date DEFAULT CURRENT_DATE,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.estoque_tecidos OWNER TO postgres;

--
-- Name: estoque_tecidos_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.estoque_tecidos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.estoque_tecidos_id_seq OWNER TO postgres;

--
-- Name: estoque_tecidos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_tecidos_id_seq OWNED BY opera.estoque_tecidos.id;


--
-- Name: ficha_tecnica_cabecalho; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.ficha_tecnica_cabecalho (
    id integer NOT NULL,
    codigo character varying(100) NOT NULL,
    descricao text,
    colecao character varying(100),
    tamanho_base character varying(10),
    dificuldade character varying(50),
    modelista character varying(100),
    pilotista character varying(100),
    custo numeric(12,2),
    pronto_producao boolean DEFAULT false,
    grade_disponivel text,
    data_criacao date,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.ficha_tecnica_cabecalho OWNER TO postgres;

--
-- Name: ficha_tecnica_cabecalho_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.ficha_tecnica_cabecalho_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.ficha_tecnica_cabecalho_id_seq OWNER TO postgres;

--
-- Name: ficha_tecnica_cabecalho_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.ficha_tecnica_cabecalho_id_seq OWNED BY opera.ficha_tecnica_cabecalho.id;


--
-- Name: historico_de_servico; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.historico_de_servico (
    id bigint NOT NULL,
    envio_id integer NOT NULL,
    entrada_id integer,
    pagamento_id bigint,
    tipo_servico character varying(50),
    status character varying(50) DEFAULT 'Em Andamento'::character varying,
    data_atualizacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE opera.historico_de_servico OWNER TO postgres;

--
-- Name: historico_de_servico_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.historico_de_servico_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.historico_de_servico_id_seq OWNER TO postgres;

--
-- Name: historico_de_servico_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.historico_de_servico_id_seq OWNED BY opera.historico_de_servico.id;


--
-- Name: historico_servicos; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.historico_servicos (
    id integer NOT NULL,
    servico_id integer,
    data_evento timestamp without time zone DEFAULT now() NOT NULL,
    acao character varying(100),
    observacoes text
);


ALTER TABLE opera.historico_servicos OWNER TO postgres;

--
-- Name: historico_servicos_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.historico_servicos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.historico_servicos_id_seq OWNER TO postgres;

--
-- Name: historico_servicos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.historico_servicos_id_seq OWNED BY opera.historico_servicos.id;


--
-- Name: log_finalizacoes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.log_finalizacoes (
    id integer NOT NULL,
    entrada_id integer,
    acao character varying(50) NOT NULL,
    dados_antes jsonb,
    dados_depois jsonb,
    usuario character varying(100),
    data_hora timestamp without time zone DEFAULT now(),
    observacoes text
);


ALTER TABLE opera.log_finalizacoes OWNER TO postgres;

--
-- Name: log_finalizacoes_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.log_finalizacoes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.log_finalizacoes_id_seq OWNER TO postgres;

--
-- Name: log_finalizacoes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.log_finalizacoes_id_seq OWNED BY opera.log_finalizacoes.id;


--
-- Name: ordem_corte_ficha; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.ordem_corte_ficha (
    id integer NOT NULL,
    codigo_modelo character varying(100) NOT NULL,
    descricao_modelo text,
    cortador character varying(100),
    auxiliar character varying(100),
    ajudante character varying(100),
    data_registro timestamp without time zone DEFAULT now(),
    data_final date,
    dias_estimados numeric(12,4),
    horas_estimadas numeric(12,4),
    porcentagens jsonb,
    consumo_peca numeric(12,4),
    quantidade_desejada integer,
    total_pecas integer,
    observacoes text,
    status character varying(50) DEFAULT 'Em Andamento'::character varying,
    usuario_registro character varying(100),
    data_atualizacao timestamp without time zone DEFAULT now(),
    ativo boolean DEFAULT true
);


ALTER TABLE opera.ordem_corte_ficha OWNER TO postgres;

--
-- Name: ordem_corte_ficha_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.ordem_corte_ficha_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.ordem_corte_ficha_id_seq OWNER TO postgres;

--
-- Name: ordem_corte_ficha_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.ordem_corte_ficha_id_seq OWNED BY opera.ordem_corte_ficha.id;


--
-- Name: ordem_corte_lotes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.ordem_corte_lotes (
    id bigint NOT NULL,
    ordem_id integer NOT NULL,
    lote_numero character varying(50),
    tamanho character varying(10) NOT NULL,
    quantidade integer DEFAULT 0 NOT NULL
);


ALTER TABLE opera.ordem_corte_lotes OWNER TO postgres;

--
-- Name: ordem_corte_lotes_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.ordem_corte_lotes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.ordem_corte_lotes_id_seq OWNER TO postgres;

--
-- Name: ordem_corte_lotes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.ordem_corte_lotes_id_seq OWNED BY opera.ordem_corte_lotes.id;


--
-- Name: ordem_grade_preferencias; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.ordem_grade_preferencias (
    id integer NOT NULL,
    usuario_id integer NOT NULL,
    nome character varying(100) NOT NULL,
    porcent_1 numeric(12,4) DEFAULT 0,
    porcent_2 numeric(12,4) DEFAULT 0,
    porcent_3 numeric(12,4) DEFAULT 0,
    porcent_4 numeric(12,4) DEFAULT 0,
    porcent_5 numeric(12,4) DEFAULT 0,
    porcent_6 numeric(12,4) DEFAULT 0,
    porcent_7 numeric(12,4) DEFAULT 0,
    porcent_8 numeric(12,4) DEFAULT 0,
    criado_em timestamp without time zone DEFAULT now(),
    atualizado_em timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.ordem_grade_preferencias OWNER TO postgres;

--
-- Name: ordem_grade_preferencias_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.ordem_grade_preferencias_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.ordem_grade_preferencias_id_seq OWNER TO postgres;

--
-- Name: ordem_grade_preferencias_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.ordem_grade_preferencias_id_seq OWNED BY opera.ordem_grade_preferencias.id;


--
-- Name: pagamento_corte_acabamento; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.pagamento_corte_acabamento (
    id integer NOT NULL,
    costureira character varying(200),
    tipo_servico character varying(100),
    codigo character varying(100),
    descricao text,
    data_envio date,
    data_chegada date,
    quantidade_finalizada integer,
    valor_por_peca numeric(12,2),
    adiantamento numeric(12,2) DEFAULT 0,
    ajuda_custo numeric(12,2) DEFAULT 0,
    bonificacao numeric(12,2) DEFAULT 0,
    pecas_faltantes integer DEFAULT 0,
    pecas_estragadas integer DEFAULT 0,
    desconto_pecas numeric(12,2) DEFAULT 0,
    total_pago numeric(12,2) DEFAULT 0,
    cpf character varying(20),
    banco character varying(50),
    agencia character varying(20),
    conta character varying(30),
    pix character varying(100),
    data_pagamento date,
    estornado boolean DEFAULT false,
    pecas_com_defeito integer DEFAULT 0,
    valor_defeito numeric(12,2) DEFAULT 0
);


ALTER TABLE opera.pagamento_corte_acabamento OWNER TO postgres;

--
-- Name: pagamento_corte_acabamento_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.pagamento_corte_acabamento_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.pagamento_corte_acabamento_id_seq OWNER TO postgres;

--
-- Name: pagamento_corte_acabamento_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.pagamento_corte_acabamento_id_seq OWNED BY opera.pagamento_corte_acabamento.id;


--
-- Name: pagamento_servicos; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.pagamento_servicos (
    id bigint NOT NULL,
    prestador_id integer,
    nome_prestador character varying(100),
    data_pagamento date NOT NULL,
    valor_total numeric(10,2) NOT NULL,
    valor_adiantamento_abatido numeric(10,2) DEFAULT 0.00,
    valor_liquido numeric(10,2) NOT NULL,
    mes_referencia character varying(10),
    observacoes text,
    usuario_pagamento character varying(100),
    data_registro timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE opera.pagamento_servicos OWNER TO postgres;

--
-- Name: pagamento_servicos_detalhe; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.pagamento_servicos_detalhe (
    pagamento_id bigint NOT NULL,
    entrada_acabamento_id integer NOT NULL,
    valor_servico numeric(10,2) NOT NULL
);


ALTER TABLE opera.pagamento_servicos_detalhe OWNER TO postgres;

--
-- Name: pagamento_servicos_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.pagamento_servicos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.pagamento_servicos_id_seq OWNER TO postgres;

--
-- Name: pagamento_servicos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.pagamento_servicos_id_seq OWNED BY opera.pagamento_servicos.id;


--
-- Name: pecas_finalizadas; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.pecas_finalizadas (
    id integer NOT NULL,
    corte_id integer,
    entrada_id integer,
    codigo character varying(100),
    descricao text,
    costureira character varying(200),
    data_envio date,
    data_chegada date,
    qtd_enviada integer,
    observacao text,
    status character varying(50),
    data_conferencia timestamp without time zone,
    valor_peca numeric(12,2),
    bonificacao numeric(12,2),
    qtd_pp integer,
    qtd_p integer,
    qtd_m integer,
    qtd_g integer,
    qtd_gg integer,
    qtd_g1 integer,
    qtd_g2 integer,
    qtd_g3 integer,
    qtd_defeito_pp integer,
    qtd_defeito_p integer,
    qtd_defeito_m integer,
    qtd_defeito_g integer,
    qtd_defeito_gg integer,
    qtd_defeito_g1 integer,
    qtd_defeito_g2 integer,
    qtd_defeito_g3 integer,
    pago boolean DEFAULT false,
    pagamento_id integer,
    valor_pago numeric(12,2),
    data_pagamento date
);


ALTER TABLE opera.pecas_finalizadas OWNER TO postgres;

--
-- Name: pecas_finalizadas_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.pecas_finalizadas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.pecas_finalizadas_id_seq OWNER TO postgres;

--
-- Name: pecas_finalizadas_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.pecas_finalizadas_id_seq OWNED BY opera.pecas_finalizadas.id;


--
-- Name: usuario_permissoes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.usuario_permissoes (
    usuario_id integer NOT NULL,
    codigo character varying(100) NOT NULL,
    pode_ver boolean DEFAULT false,
    pode_editar boolean DEFAULT false,
    pode_imprimir boolean DEFAULT false,
    pode_excluir boolean DEFAULT false,
    pode_administrar boolean DEFAULT false
);


ALTER TABLE opera.usuario_permissoes OWNER TO postgres;

--
-- Name: TABLE usuario_permissoes; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON TABLE opera.usuario_permissoes IS 'Permissões de acesso por usuário e módulo do sistema.';


--
-- Name: permissoes; Type: VIEW; Schema: opera; Owner: postgres
--

CREATE VIEW opera.permissoes AS
 SELECT usuario_id,
    codigo AS pagina,
    pode_ver,
    pode_editar,
    pode_imprimir,
    pode_excluir,
    pode_administrar
   FROM opera.usuario_permissoes;


ALTER VIEW opera.permissoes OWNER TO postgres;

--
-- Name: VIEW permissoes; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON VIEW opera.permissoes IS 'View usada pelo sistema Opera para permissões de usuário.';


--
-- Name: permissoes_catalogo; Type: VIEW; Schema: opera; Owner: postgres
--

CREATE VIEW opera.permissoes_catalogo AS
 SELECT 'usuarios'::text AS codigo,
    'Usuários'::text AS nome
UNION ALL
 SELECT 'cadastro_modelos'::text AS codigo,
    'Cadastro de Modelos'::text AS nome
UNION ALL
 SELECT 'cadastro_de_corte'::text AS codigo,
    'Cadastro de Corte'::text AS nome
UNION ALL
 SELECT 'controle_envio_cortes'::text AS codigo,
    'Envio de Cortes'::text AS nome
UNION ALL
 SELECT 'estoque_tecidos'::text AS codigo,
    'Estoque de Tecidos'::text AS nome
UNION ALL
 SELECT 'estoque_aviamentos'::text AS codigo,
    'Estoque de Aviamentos'::text AS nome;


ALTER VIEW opera.permissoes_catalogo OWNER TO postgres;

--
-- Name: pricing_profiles; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.pricing_profiles (
    nome character varying(100) NOT NULL,
    impostos numeric(12,4),
    comissao numeric(12,4),
    cartao numeric(12,4),
    margem numeric(12,4),
    perdas numeric(12,4),
    defeito numeric(12,4),
    fixos numeric(12,2),
    capacidade numeric(12,2),
    variaveis numeric(12,2),
    frete numeric(12,2),
    arredondamento character varying(20),
    canal character varying(100),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.pricing_profiles OWNER TO postgres;

--
-- Name: relatorios_finalizacao; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.relatorios_finalizacao (
    id integer NOT NULL,
    entrada_id integer,
    usuario_geracao character varying(100),
    data_geracao timestamp without time zone DEFAULT now(),
    tipo_relatorio character varying(50),
    html_content text,
    pdf_path text,
    parametros jsonb,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.relatorios_finalizacao OWNER TO postgres;

--
-- Name: relatorios_finalizacao_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.relatorios_finalizacao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.relatorios_finalizacao_id_seq OWNER TO postgres;

--
-- Name: relatorios_finalizacao_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.relatorios_finalizacao_id_seq OWNED BY opera.relatorios_finalizacao.id;


--
-- Name: retorno_detalhes_tamanho; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.retorno_detalhes_tamanho (
    id integer NOT NULL,
    envio_id integer NOT NULL,
    tamanho character varying(10) NOT NULL,
    entregue integer DEFAULT 0,
    copias integer DEFAULT 0,
    defeitos integer DEFAULT 0,
    faltantes integer DEFAULT 0,
    regulares integer DEFAULT 0,
    subtotal numeric(12,2) DEFAULT 0
);


ALTER TABLE opera.retorno_detalhes_tamanho OWNER TO postgres;

--
-- Name: retorno_detalhes_tamanho_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.retorno_detalhes_tamanho_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.retorno_detalhes_tamanho_id_seq OWNER TO postgres;

--
-- Name: retorno_detalhes_tamanho_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.retorno_detalhes_tamanho_id_seq OWNED BY opera.retorno_detalhes_tamanho.id;


--
-- Name: servicos; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.servicos (
    id integer NOT NULL,
    nome character varying(200) NOT NULL,
    descricao text,
    prestador character varying(200),
    data_inicio date,
    data_fim date,
    valor_unitario numeric(12,2),
    quantidade integer,
    valor_total numeric(12,2),
    status character varying(50),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.servicos OWNER TO postgres;

--
-- Name: servicos_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.servicos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.servicos_id_seq OWNER TO postgres;

--
-- Name: servicos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.servicos_id_seq OWNED BY opera.servicos.id;


--
-- Name: usuarios; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.usuarios (
    id integer NOT NULL,
    usuario character varying(100) NOT NULL,
    senha_hash text,
    hierarquia character varying(50) NOT NULL,
    email character varying(255),
    data_criacao timestamp without time zone DEFAULT now(),
    ativo boolean DEFAULT true NOT NULL,
    dica_senha text,
    ultimo_login timestamp without time zone,
    telefone character varying(50),
    departamento character varying(100),
    tema_preferido character varying(50) DEFAULT 'Noite Urbana'::character varying
);


ALTER TABLE opera.usuarios OWNER TO postgres;

--
-- Name: TABLE usuarios; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON TABLE opera.usuarios IS 'Tabela principal de usuários do sistema.';


--
-- Name: usuario; Type: VIEW; Schema: opera; Owner: postgres
--

CREATE VIEW opera.usuario AS
 SELECT id,
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


ALTER VIEW opera.usuario OWNER TO postgres;

--
-- Name: usuario_logs; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.usuario_logs (
    id integer NOT NULL,
    data_hora timestamp without time zone DEFAULT now() NOT NULL,
    usuario character varying(100) NOT NULL,
    acao text,
    pagina text,
    detalhe text
);


ALTER TABLE opera.usuario_logs OWNER TO postgres;

--
-- Name: usuario_logs_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.usuario_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.usuario_logs_id_seq OWNER TO postgres;

--
-- Name: usuario_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.usuario_logs_id_seq OWNED BY opera.usuario_logs.id;


--
-- Name: usuario_preferencias; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.usuario_preferencias (
    usuario_id integer NOT NULL,
    tema_nome character varying(50) DEFAULT 'Noite Urbana'::character varying,
    usar_tema_personalizado boolean DEFAULT false,
    tema_personalizado text,
    layout_compacto boolean DEFAULT false,
    sidebar_recolhida boolean DEFAULT false,
    usar_animacoes boolean DEFAULT true,
    mostrar_dicas boolean DEFAULT true,
    idioma character varying(20) DEFAULT 'pt-BR'::character varying,
    notificacoes boolean DEFAULT true,
    atualizado_em timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.usuario_preferencias OWNER TO postgres;

--
-- Name: TABLE usuario_preferencias; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON TABLE opera.usuario_preferencias IS 'Preferências e configurações individuais de cada usuário.';


--
-- Name: COLUMN usuario_preferencias.tema_personalizado; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON COLUMN opera.usuario_preferencias.tema_personalizado IS 'Paleta de cores personalizada em formato JSON (método antigo - um tema por usuário).';


--
-- Name: usuario_temas_personalizados; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.usuario_temas_personalizados (
    id integer NOT NULL,
    usuario_id integer NOT NULL,
    nome_tema character varying(100) NOT NULL,
    cores_tema jsonb NOT NULL,
    data_criacao timestamp without time zone DEFAULT now(),
    atualizado_em timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.usuario_temas_personalizados OWNER TO postgres;

--
-- Name: TABLE usuario_temas_personalizados; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON TABLE opera.usuario_temas_personalizados IS 'Temas personalizados de cada usuário (múltiplos temas por usuário).';


--
-- Name: COLUMN usuario_temas_personalizados.cores_tema; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON COLUMN opera.usuario_temas_personalizados.cores_tema IS 'Paleta de cores personalizada em formato JSONB com estrutura completa do tema.';


--
-- Name: COLUMN usuario_temas_personalizados.atualizado_em; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON COLUMN opera.usuario_temas_personalizados.atualizado_em IS 'Data e hora da última modificação do tema personalizado.';


--
-- Name: usuario_temas_personalizados_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.usuario_temas_personalizados_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.usuario_temas_personalizados_id_seq OWNER TO postgres;

--
-- Name: usuario_temas_personalizados_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.usuario_temas_personalizados_id_seq OWNED BY opera.usuario_temas_personalizados.id;


--
-- Name: usuarios_id_seq; Type: SEQUENCE; Schema: opera; Owner: postgres
--

CREATE SEQUENCE opera.usuarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE opera.usuarios_id_seq OWNER TO postgres;

--
-- Name: usuarios_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.usuarios_id_seq OWNED BY opera.usuarios.id;


--
-- Name: v_logs_usuarios; Type: VIEW; Schema: opera; Owner: postgres
--

CREATE VIEW opera.v_logs_usuarios AS
 SELECT ul.id,
    ul.data_hora,
    ul.usuario,
    u.hierarquia,
    ul.acao,
    ul.pagina,
    ul.detalhe,
    EXTRACT(epoch FROM (now() - (ul.data_hora)::timestamp with time zone)) AS segundos_atras
   FROM (opera.usuario_logs ul
     LEFT JOIN opera.usuarios u ON (((ul.usuario)::text = (u.usuario)::text)))
  ORDER BY ul.data_hora DESC;


ALTER VIEW opera.v_logs_usuarios OWNER TO postgres;

--
-- Name: VIEW v_logs_usuarios; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON VIEW opera.v_logs_usuarios IS 'View para consulta ordenada dos logs de atividades dos usuários.';


--
-- Name: v_temas_por_usuario; Type: VIEW; Schema: opera; Owner: postgres
--

CREATE VIEW opera.v_temas_por_usuario AS
 SELECT u.id AS usuario_id,
    u.usuario,
    utp.nome_tema,
    utp.cores_tema,
    utp.data_criacao,
    ((utp.nome_tema)::text = (up.tema_nome)::text) AS tema_ativo
   FROM ((opera.usuarios u
     LEFT JOIN opera.usuario_temas_personalizados utp ON ((u.id = utp.usuario_id)))
     LEFT JOIN opera.usuario_preferencias up ON ((u.id = up.usuario_id)));


ALTER VIEW opera.v_temas_por_usuario OWNER TO postgres;

--
-- Name: VIEW v_temas_por_usuario; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON VIEW opera.v_temas_por_usuario IS 'View com todos os temas personalizados organizados por usuário.';


--
-- Name: v_usuarios_com_preferencias; Type: VIEW; Schema: opera; Owner: postgres
--

CREATE VIEW opera.v_usuarios_com_preferencias AS
 SELECT u.id,
    u.usuario,
    u.email,
    u.hierarquia,
    u.tema_preferido,
    up.tema_nome AS tema_ativado,
    up.usar_tema_personalizado,
    ( SELECT count(*) AS count
           FROM opera.usuario_temas_personalizados utp
          WHERE (utp.usuario_id = u.id)) AS total_temas_personalizados,
    u.ultimo_login,
    u.ativo
   FROM (opera.usuarios u
     LEFT JOIN opera.usuario_preferencias up ON ((u.id = up.usuario_id)));


ALTER VIEW opera.v_usuarios_com_preferencias OWNER TO postgres;

--
-- Name: VIEW v_usuarios_com_preferencias; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON VIEW opera.v_usuarios_com_preferencias IS 'View com informações completas de usuários e suas preferências.';


--
-- Name: _schema_info id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera._schema_info ALTER COLUMN id SET DEFAULT nextval('opera._schema_info_id_seq'::regclass);


--
-- Name: adiantamento_faccao id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.adiantamento_faccao ALTER COLUMN id SET DEFAULT nextval('opera.adiantamento_faccao_id_seq'::regclass);


--
-- Name: cadastro_de_corte id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_de_corte_id_seq'::regclass);


--
-- Name: cadastro_de_corte_lotes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_lotes ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_de_corte_lotes_id_seq'::regclass);


--
-- Name: cadastro_de_corte_tecidos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_tecidos ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_de_corte_tecidos_id_seq'::regclass);


--
-- Name: cadastro_faccoes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_faccoes ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_faccoes_id_seq'::regclass);


--
-- Name: cadastro_modelos_aviamentos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_aviamentos ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_aviamentos_id_seq'::regclass);


--
-- Name: cadastro_modelos_cabecalho id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_cabecalho ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_cabecalho_id_seq'::regclass);


--
-- Name: cadastro_modelos_grade id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_grade ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_grade_id_seq'::regclass);


--
-- Name: cadastro_modelos_imagens id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_imagens ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_imagens_id_seq'::regclass);


--
-- Name: cadastro_modelos_outros id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_outros_id_seq'::regclass);


--
-- Name: cadastro_modelos_outros_servicos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros_servicos ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_outros_servicos_id_seq'::regclass);


--
-- Name: cadastro_modelos_tecidos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_tecidos ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_tecidos_id_seq'::regclass);


--
-- Name: controle_envio_cortes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_envio_cortes ALTER COLUMN id SET DEFAULT nextval('opera.controle_envio_cortes_id_seq'::regclass);


--
-- Name: controle_envio_cortes_detalhes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_envio_cortes_detalhes ALTER COLUMN id SET DEFAULT nextval('opera.controle_envio_cortes_detalhes_id_seq'::regclass);


--
-- Name: controle_retorno_cortes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_retorno_cortes ALTER COLUMN id SET DEFAULT nextval('opera.controle_retorno_cortes_id_seq'::regclass);


--
-- Name: cortes_finalizados id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados ALTER COLUMN id SET DEFAULT nextval('opera.cortes_finalizados_id_seq'::regclass);


--
-- Name: cortes_finalizados_completo id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo ALTER COLUMN id SET DEFAULT nextval('opera.cortes_finalizados_completo_id_seq'::regclass);


--
-- Name: entrada_acabamento id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento ALTER COLUMN id SET DEFAULT nextval('opera.entrada_acabamento_id_seq'::regclass);


--
-- Name: entrada_acabamento_detalhes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento_detalhes ALTER COLUMN id SET DEFAULT nextval('opera.entrada_acabamento_detalhes_id_seq'::regclass);


--
-- Name: envios_cortes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envios_cortes ALTER COLUMN id SET DEFAULT nextval('opera.envios_cortes_id_seq'::regclass);


--
-- Name: estoque_aviamentos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_aviamentos ALTER COLUMN id SET DEFAULT nextval('opera.estoque_aviamentos_id_seq'::regclass);


--
-- Name: estoque_escritorio id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_escritorio ALTER COLUMN id SET DEFAULT nextval('opera.estoque_escritorio_id_seq'::regclass);


--
-- Name: estoque_insumos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_insumos ALTER COLUMN id SET DEFAULT nextval('opera.estoque_insumos_id_seq'::regclass);


--
-- Name: estoque_limpeza id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_limpeza ALTER COLUMN id SET DEFAULT nextval('opera.estoque_limpeza_id_seq'::regclass);


--
-- Name: estoque_outros id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_outros ALTER COLUMN id SET DEFAULT nextval('opera.estoque_outros_id_seq'::regclass);


--
-- Name: estoque_saida_log id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_saida_log ALTER COLUMN id SET DEFAULT nextval('opera.estoque_saida_log_id_seq'::regclass);


--
-- Name: estoque_tecidos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_tecidos ALTER COLUMN id SET DEFAULT nextval('opera.estoque_tecidos_id_seq'::regclass);


--
-- Name: ficha_tecnica_cabecalho id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ficha_tecnica_cabecalho ALTER COLUMN id SET DEFAULT nextval('opera.ficha_tecnica_cabecalho_id_seq'::regclass);


--
-- Name: historico_de_servico id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_de_servico ALTER COLUMN id SET DEFAULT nextval('opera.historico_de_servico_id_seq'::regclass);


--
-- Name: historico_servicos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_servicos ALTER COLUMN id SET DEFAULT nextval('opera.historico_servicos_id_seq'::regclass);


--
-- Name: log_finalizacoes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.log_finalizacoes ALTER COLUMN id SET DEFAULT nextval('opera.log_finalizacoes_id_seq'::regclass);


--
-- Name: ordem_corte_ficha id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_ficha ALTER COLUMN id SET DEFAULT nextval('opera.ordem_corte_ficha_id_seq'::regclass);


--
-- Name: ordem_corte_lotes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_lotes ALTER COLUMN id SET DEFAULT nextval('opera.ordem_corte_lotes_id_seq'::regclass);


--
-- Name: ordem_grade_preferencias id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_grade_preferencias ALTER COLUMN id SET DEFAULT nextval('opera.ordem_grade_preferencias_id_seq'::regclass);


--
-- Name: pagamento_corte_acabamento id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_corte_acabamento ALTER COLUMN id SET DEFAULT nextval('opera.pagamento_corte_acabamento_id_seq'::regclass);


--
-- Name: pagamento_servicos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_servicos ALTER COLUMN id SET DEFAULT nextval('opera.pagamento_servicos_id_seq'::regclass);


--
-- Name: pecas_finalizadas id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pecas_finalizadas ALTER COLUMN id SET DEFAULT nextval('opera.pecas_finalizadas_id_seq'::regclass);


--
-- Name: relatorios_finalizacao id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.relatorios_finalizacao ALTER COLUMN id SET DEFAULT nextval('opera.relatorios_finalizacao_id_seq'::regclass);


--
-- Name: retorno_detalhes_tamanho id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.retorno_detalhes_tamanho ALTER COLUMN id SET DEFAULT nextval('opera.retorno_detalhes_tamanho_id_seq'::regclass);


--
-- Name: servicos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.servicos ALTER COLUMN id SET DEFAULT nextval('opera.servicos_id_seq'::regclass);


--
-- Name: usuario_logs id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_logs ALTER COLUMN id SET DEFAULT nextval('opera.usuario_logs_id_seq'::regclass);


--
-- Name: usuario_temas_personalizados id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_temas_personalizados ALTER COLUMN id SET DEFAULT nextval('opera.usuario_temas_personalizados_id_seq'::regclass);


--
-- Name: usuarios id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuarios ALTER COLUMN id SET DEFAULT nextval('opera.usuarios_id_seq'::regclass);


--
-- Data for Name: _schema_info; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera._schema_info (id, schema_name, versao, criado_em, atualizado_em) FROM stdin;
1	opera	1.0	2025-12-01 17:39:32.338972	2025-12-01 17:39:32.338972
\.


--
-- Data for Name: adiantamento_faccao; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.adiantamento_faccao (id, corte_id, codigo_modelo, faccao, valor, forma_pagamento, parcelas, data_hora) FROM stdin;
\.


--
-- Data for Name: cadastro_de_corte; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_de_corte (id, numero_ordem, ordem_corte, codigo, descricao, descricao_corte, data, data_envio, comprimento_matriz, largura_matriz, cortador, ajudante, auxiliar, total_folhas, metros_utilizados, bobinas_utilizadas, composicao_tecido, pp, p, m, g, gg, g1, g2, g3, total_pecas, rendimento, observacoes, created_at, updated_at) FROM stdin;
1	OC0001	\N	1111	vestido alfaiataria	\N	2025-12-06	\N	7.350	1.480	asadf	asdf	\N	6	44.100	6.000		143	143	143	143	143	143	143	143	1144	0.0400	sdfsdfsdf	2025-12-06 13:10:50.140964	2025-12-06 13:10:50.140964
\.


--
-- Data for Name: cadastro_de_corte_lotes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_de_corte_lotes (id, cadastro_id, lote, tecido, cor, composicao, bobinas, folhas, pp, p, m, g, gg, g1, g2, g3, total_lote) FROM stdin;
1	1	LOTE 1	asdf	preto	asdf	1.000	1.000	45	45	45	45	45	45	45	45	360
2	1	LOTE 2	asdf	azul	asdf	5.000	5.000	98	98	98	98	98	98	98	98	784
\.


--
-- Data for Name: cadastro_de_corte_tecidos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_de_corte_tecidos (id, cadastro_id, tecido, cor, composicao, bobinas, folhas, pp, p, m, g, gg, g1, g2, g3, total_pecas) FROM stdin;
1	1	asdf	preto	asdf	1.000	1.000	45	45	45	45	45	45	45	45	360
2	1	asdf	azul	asdf	5.000	5.000	98	98	98	98	98	98	98	98	784
\.


--
-- Data for Name: cadastro_faccoes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_faccoes (id, codigo, nome, tipo_prestador, telefone, endereco, titular_da_conta, cpf, banco, agencia, conta, pix, data, data_atualizacao, ativo) FROM stdin;
1	001	asdfa	Facção	df	asdf	54545	4545	4545	45454	54545	454545	2025-01-12	2025-12-01 17:42:49.642204	t
\.


--
-- Data for Name: cadastro_modelos_aviamentos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_aviamentos (id, codigo_modelo, cadastro_id, codigo_aviamento, descricao, cor, fornecedor, quantidade, valor_unidade, valor_total, created_at) FROM stdin;
\.


--
-- Data for Name: cadastro_modelos_cabecalho; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_cabecalho (id, codigo, descricao, colecao, tamanho_base, dificuldade, modelista, pilotista, custo_total, pronto_producao, grade_disponivel, data_criacao, data_atualizacao, created_at, updated_at) FROM stdin;
1	1111	vestido alfaiataria	dezembro	M	Médio		li	33.00	f	PP,P,M,G,GG,G1,G2,G3	2025-12-01 17:41:02.020489	2025-12-01 17:45:47.812873	2025-12-01 17:41:02.020489	2025-12-01 17:41:02.020489
\.


--
-- Data for Name: cadastro_modelos_grade; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_grade (id, modelo_id, tamanho, disponivel) FROM stdin;
\.


--
-- Data for Name: cadastro_modelos_imagens; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_imagens (id, codigo_modelo, cadastro_id, tipo_imagem, caminho_imagem, descricao, created_at) FROM stdin;
3	1111	1	frente	BANCO_DE_DADOS/IMAGENS_FRENTE_COSTAS/1111_frente.jpg	Imagem frente do modelo	2025-12-01 17:45:47.812873
4	1111	1	costas	BANCO_DE_DADOS/IMAGENS_FRENTE_COSTAS/1111_costas.jpg	Imagem costas do modelo	2025-12-01 17:45:47.812873
\.


--
-- Data for Name: cadastro_modelos_outros; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_outros (id, codigo_modelo, cadastro_id, codigo, descricao, cor, fornecedor, unidade, quantidade, preco, total, observacoes, created_at) FROM stdin;
\.


--
-- Data for Name: cadastro_modelos_outros_servicos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_outros_servicos (id, codigo_modelo, cadastro_id, codigo_servico, descricao, tipo_servico, fornecedor, unidade, quantidade, valor_unidade, valor_total, observacoes, created_at) FROM stdin;
\.


--
-- Data for Name: cadastro_modelos_tecidos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_tecidos (id, codigo_modelo, cadastro_id, codigo_tecido, descricao, cor, fornecedor, composicao, metros_peca, valor_metro, valor_total, created_at) FROM stdin;
1	1111	1	0000	asdf	asdf	asdf	asdf	1.6500	20.00	33.00	2025-12-01 17:45:47.812873
\.


--
-- Data for Name: controle_envio_cortes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.controle_envio_cortes (id, data_envio, servico, corte_id, ordem_corte, codigo_corte, descricao_corte, destino, costureira, faccao, quantidade_total, valor_peca, valor_total, status, observacao, pp, p, m, g, gg, g1, g2, g3) FROM stdin;
\.


--
-- Data for Name: controle_envio_cortes_detalhes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.controle_envio_cortes_detalhes (id, envio_id, prestador_servico, tipo_servico, valor_pp, valor_p, valor_m, valor_g, valor_gg, valor_g1, valor_g2, valor_g3, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: controle_retorno_cortes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.controle_retorno_cortes (id, envio_id, data_chegada, telefone_encarregado, telefone_acabamento, resumo_piloto, aviamentos_recebidos, outros_recebidos, observacoes_gerais, total_entregue, total_copias, total_defeitos, total_faltantes, total_regulares, valor_total, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: cortes_finalizados; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cortes_finalizados (id, corte_id, entrada_id, codigo, descricao, costureira, data_envio, data_chegada, data_final, qtd_enviada, total_pecas, quantidade_finalizada, observacao, status, data_conferencia, valor_peca, bonificacao, pago, data_pagamento, qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3, qtd_defeito_pp, qtd_defeito_p, qtd_defeito_m, qtd_defeito_g, qtd_defeito_gg, qtd_defeito_g1, qtd_defeito_g2, qtd_defeito_g3, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: cortes_finalizados_completo; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cortes_finalizados_completo (id, entrada_id, corte_id, codigo, descricao, costureira, servico, data_envio, data_chegada, data_conferencia, qtd_enviada, total_entregue, total_copias, total_defeitos, total_faltantes, total_regulares, valor_peca, valor_total, bonificacao, valor_bonificacao, qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3, qtd_defeito_pp, qtd_defeito_p, qtd_defeito_m, qtd_defeito_g, qtd_defeito_gg, qtd_defeito_g1, qtd_defeito_g2, qtd_defeito_g3, qtd_regular_pp, qtd_regular_p, qtd_regular_m, qtd_regular_g, qtd_regular_gg, qtd_regular_g1, qtd_regular_g2, qtd_regular_g3, status, observacoes, usuario_finalizacao, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: entrada_acabamento; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.entrada_acabamento (id, envio_id, data_chegada, total_entregue, total_defeitos, total_faltantes, total_regulares, valor_total, pago, data_pagamento) FROM stdin;
\.


--
-- Data for Name: entrada_acabamento_detalhes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.entrada_acabamento_detalhes (id, entrada_id, observacoes_finalizacao, bonificacao_aplicada, usuario_conferencia, total_entregue, total_copias, total_defeitos, total_faltantes, total_regulares, valor_total_pagar, status_finalizacao, data_conferencia, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: envio_detalhes_tamanho; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.envio_detalhes_tamanho (envio_id, tamanho, quantidade, quantidade_pilotos, valor_peca) FROM stdin;
\.


--
-- Data for Name: envios_cortes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.envios_cortes (id, data_envio, prestador_id, tipo_servico, corte_id, qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3, piloto_pp, piloto_p, piloto_m, piloto_g, piloto_gg, piloto_g1, piloto_g2, piloto_g3, valor_pp, valor_p, valor_m, valor_g, valor_gg, valor_g1, valor_g2, valor_g3, aviamentos, outros, observacoes, tel_encarregado, tel_acabamento, previsao_entrega, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: estoque_aviamentos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_aviamentos (id, codigo, descricao, cor, fornecedor, quantidade, unidade, valor_unidade, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: estoque_escritorio; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_escritorio (id, codigo, descricao, fornecedor, cor, quantidade, unidade, valor_unidade, tipo, categoria, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: estoque_insumos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_insumos (id, codigo, descricao, fornecedor, cor, quantidade, unidade, valor_unidade, tipo, categoria, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: estoque_limpeza; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_limpeza (id, codigo, descricao, fornecedor, cor, quantidade, unidade, valor_unidade, tipo, categoria, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: estoque_outros; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_outros (id, codigo, descricao, fornecedor, cor, quantidade, unidade, valor_unidade, tipo, categoria, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: estoque_saida_log; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_saida_log (id, data_hora, tipo_estoque, item_id, codigo, descricao, cor, quantidade, unidade, motivo, observacoes, usuario) FROM stdin;
\.


--
-- Data for Name: estoque_tecidos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_tecidos (id, codigo, descricao, cor, composicao, fornecedor, metros, kilos, valor_metro, valor_kilo, unidade, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
5	2222	asdf	preto	asdf	asdf	9625.150	0.000	0.00	0.00	metros	asdfasdf	\N	2025-12-01	2025-12-01 23:11:53.721552	2025-12-01 23:11:53.721552
3	0000	asdf	preto	asdf	asdf	9617.800	0.000	0.00	0.00	metros	asdfasdf	\N	2025-01-12	2025-12-01 22:42:07.17992	2025-12-01 22:42:07.17992
4	0000	asdf	azul	asdf	asdffrf	6288.250	0.000	0.00	0.00	metros	asdfasdf	\N	2025-12-01	2025-12-01 22:42:30.826674	2025-12-01 22:42:30.826674
\.


--
-- Data for Name: ficha_tecnica_cabecalho; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.ficha_tecnica_cabecalho (id, codigo, descricao, colecao, tamanho_base, dificuldade, modelista, pilotista, custo, pronto_producao, grade_disponivel, data_criacao, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: historico_de_servico; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.historico_de_servico (id, envio_id, entrada_id, pagamento_id, tipo_servico, status, data_atualizacao) FROM stdin;
\.


--
-- Data for Name: historico_servicos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.historico_servicos (id, servico_id, data_evento, acao, observacoes) FROM stdin;
\.


--
-- Data for Name: log_finalizacoes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.log_finalizacoes (id, entrada_id, acao, dados_antes, dados_depois, usuario, data_hora, observacoes) FROM stdin;
\.


--
-- Data for Name: ordem_corte_ficha; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.ordem_corte_ficha (id, codigo_modelo, descricao_modelo, cortador, auxiliar, ajudante, data_registro, data_final, dias_estimados, horas_estimadas, porcentagens, consumo_peca, quantidade_desejada, total_pecas, observacoes, status, usuario_registro, data_atualizacao, ativo) FROM stdin;
1	1111	vestido alfaiataria	asadf	asdf	\N	2025-12-01 17:41:36.928025	2025-12-01	0.0417	1.0000	{"porcent_1": 50.0, "porcent_2": 50.0, "porcent_3": 50.0, "porcent_4": 50.0, "porcent_5": 50.0, "porcent_6": 50.0, "porcent_7": 50.0, "porcent_8": 50.0}	1.6500	\N	\N	\N	Em Andamento	\N	2025-12-01 17:41:36.928025	t
\.


--
-- Data for Name: ordem_corte_lotes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.ordem_corte_lotes (id, ordem_id, lote_numero, tamanho, quantidade) FROM stdin;
\.


--
-- Data for Name: ordem_grade_preferencias; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.ordem_grade_preferencias (id, usuario_id, nome, porcent_1, porcent_2, porcent_3, porcent_4, porcent_5, porcent_6, porcent_7, porcent_8, criado_em, atualizado_em) FROM stdin;
\.


--
-- Data for Name: pagamento_corte_acabamento; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.pagamento_corte_acabamento (id, costureira, tipo_servico, codigo, descricao, data_envio, data_chegada, quantidade_finalizada, valor_por_peca, adiantamento, ajuda_custo, bonificacao, pecas_faltantes, pecas_estragadas, desconto_pecas, total_pago, cpf, banco, agencia, conta, pix, data_pagamento, estornado, pecas_com_defeito, valor_defeito) FROM stdin;
\.


--
-- Data for Name: pagamento_servicos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.pagamento_servicos (id, prestador_id, nome_prestador, data_pagamento, valor_total, valor_adiantamento_abatido, valor_liquido, mes_referencia, observacoes, usuario_pagamento, data_registro) FROM stdin;
\.


--
-- Data for Name: pagamento_servicos_detalhe; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.pagamento_servicos_detalhe (pagamento_id, entrada_acabamento_id, valor_servico) FROM stdin;
\.


--
-- Data for Name: pecas_finalizadas; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.pecas_finalizadas (id, corte_id, entrada_id, codigo, descricao, costureira, data_envio, data_chegada, qtd_enviada, observacao, status, data_conferencia, valor_peca, bonificacao, qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3, qtd_defeito_pp, qtd_defeito_p, qtd_defeito_m, qtd_defeito_g, qtd_defeito_gg, qtd_defeito_g1, qtd_defeito_g2, qtd_defeito_g3, pago, pagamento_id, valor_pago, data_pagamento) FROM stdin;
\.


--
-- Data for Name: pricing_profiles; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.pricing_profiles (nome, impostos, comissao, cartao, margem, perdas, defeito, fixos, capacidade, variaveis, frete, arredondamento, canal, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: relatorios_finalizacao; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.relatorios_finalizacao (id, entrada_id, usuario_geracao, data_geracao, tipo_relatorio, html_content, pdf_path, parametros, created_at) FROM stdin;
\.


--
-- Data for Name: retorno_detalhes_tamanho; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.retorno_detalhes_tamanho (id, envio_id, tamanho, entregue, copias, defeitos, faltantes, regulares, subtotal) FROM stdin;
\.


--
-- Data for Name: servicos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.servicos (id, nome, descricao, prestador, data_inicio, data_fim, valor_unitario, quantidade, valor_total, status, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: usuario_logs; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuario_logs (id, data_hora, usuario, acao, pagina, detalhe) FROM stdin;
1	2025-12-01 17:40:10.562367	Administrador Local	Acessou: Cadastrar Modelo	Navegação	Usuário: Administrador Local | Página: Cadastrar Modelo
2	2025-12-01 17:41:08.087066	Administrador Local	Acessou: Nova Ordem	Navegação	Usuário: Administrador Local | Página: Nova Ordem
3	2025-12-01 17:42:09.26958	Administrador Local	Acessou: Nova Ordem	Navegação	Usuário: Administrador Local | Página: Nova Ordem
4	2025-12-01 17:42:12.229351	Administrador Local	Acessou: Cadastrar Corte	Navegação	Usuário: Administrador Local | Página: Cadastrar Corte
5	2025-12-01 17:42:20.948522	Administrador Local	Acessou: Entrada de Estoque	Navegação	Usuário: Administrador Local | Página: Entrada de Estoque
6	2025-12-01 17:42:36.030033	Administrador Local	Acessou: Cadastro de Facções	Navegação	Usuário: Administrador Local | Página: Cadastro de Facções
7	2025-12-01 17:42:57.081969	Administrador Local	Acessou: Cadastrar Corte	Navegação	Usuário: Administrador Local | Página: Cadastrar Corte
8	2025-12-01 17:43:37.566136	Administrador Local	Acessou: Entrada de Estoque	Navegação	Usuário: Administrador Local | Página: Entrada de Estoque
9	2025-12-01 17:43:57.638891	Administrador Local	Acessou: Cadastrar Corte	Navegação	Usuário: Administrador Local | Página: Cadastrar Corte
10	2025-12-01 17:44:11.799155	Administrador Local	Acessou: Entrada de Estoque	Navegação	Usuário: Administrador Local | Página: Entrada de Estoque
11	2025-12-01 17:44:21.783606	Administrador Local	Acessou: Cadastrar Corte	Navegação	Usuário: Administrador Local | Página: Cadastrar Corte
12	2025-12-01 17:45:01.435869	Administrador Local	Acessou: Entrada de Estoque	Navegação	Usuário: Administrador Local | Página: Entrada de Estoque
13	2025-12-01 17:45:19.484566	Administrador Local	Acessou: Cadastrar Modelo	Navegação	Usuário: Administrador Local | Página: Cadastrar Modelo
14	2025-12-01 17:45:51.80084	Administrador Local	Acessou: Cadastrar Corte	Navegação	Usuário: Administrador Local | Página: Cadastrar Corte
15	2025-12-04 22:54:51.644712	Administrador Local	Acessou: Cadastrar Modelo	Navegação	Usuário: Administrador Local | Página: Cadastrar Modelo
16	2025-12-05 21:32:05.866035	Administrador Local	Acessou: Ordens de Corte Impressão	Navegação	Usuário: Administrador Local | Página: Ordens de Corte Impressão
17	2025-12-05 21:32:19.816826	Administrador Local	Acessou: Cadastrar Modelo	Navegação	Usuário: Administrador Local | Página: Cadastrar Modelo
18	2025-12-05 21:32:49.401636	Administrador Local	Acessou: Nova Ordem	Navegação	Usuário: Administrador Local | Página: Nova Ordem
19	2025-12-05 21:33:34.891001	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
20	2025-12-05 21:33:42.530154	Administrador Local	Acessou: Produção	Navegação	Usuário: Administrador Local | Página: Produção
21	2025-12-05 21:33:46.736908	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
22	2025-12-05 21:33:51.500728	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
23	2025-12-05 21:34:03.440253	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
24	2025-12-05 21:34:12.639994	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
25	2025-12-05 21:34:17.538232	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
26	2025-12-05 22:03:35.059114	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
27	2025-12-05 22:36:25.990883	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
28	2025-12-05 22:50:12.56326	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
29	2025-12-05 22:58:32.300543	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
30	2025-12-05 22:58:45.794968	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
31	2025-12-05 22:58:51.183859	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
32	2025-12-05 22:58:52.971188	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
33	2025-12-05 23:01:29.075787	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
34	2025-12-05 23:08:17.541402	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
35	2025-12-05 23:20:50.555662	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
36	2025-12-05 23:32:59.490499	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
37	2025-12-05 23:39:18.755475	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
38	2025-12-05 23:42:36.663278	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
39	2025-12-05 23:50:24.226107	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
40	2025-12-05 23:51:23.954966	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
41	2025-12-05 23:54:02.862306	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
42	2025-12-05 23:56:29.004075	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
43	2025-12-05 23:58:17.127001	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
44	2025-12-06 00:01:25.564002	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
45	2025-12-06 00:04:25.40162	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
46	2025-12-06 00:05:09.850808	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
47	2025-12-06 00:09:52.588752	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
48	2025-12-06 00:10:19.384344	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
49	2025-12-06 00:11:41.599548	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
50	2025-12-06 00:25:38.650713	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
51	2025-12-06 00:26:21.121109	Gil de Oliveira	Acessou: Temas	Navegação	Usuário: Gil de Oliveira | Página: Temas
52	2025-12-06 10:52:51.992312	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
53	2025-12-06 10:52:58.331946	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
54	2025-12-06 10:53:14.113804	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
55	2025-12-06 11:03:06.958791	Administrador Local	Acessou: Controle de Mão de Obra	Navegação	Usuário: Administrador Local | Página: Controle de Mão de Obra
56	2025-12-06 11:42:32.63559	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
57	2025-12-06 11:42:38.866594	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
58	2025-12-06 11:42:56.880975	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
59	2025-12-06 11:43:01.358784	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
60	2025-12-06 11:46:23.268368	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
61	2025-12-06 11:46:27.124735	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
62	2025-12-06 11:46:53.209728	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
63	2025-12-06 11:50:20.570636	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
64	2025-12-06 11:50:24.556766	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
65	2025-12-06 11:54:20.392427	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
66	2025-12-06 11:54:25.176628	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
67	2025-12-06 11:56:40.165739	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
68	2025-12-06 11:56:44.937808	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
69	2025-12-06 11:57:15.29097	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
70	2025-12-06 11:57:35.338436	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
71	2025-12-06 11:59:14.496333	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
72	2025-12-06 11:59:23.45694	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
73	2025-12-06 11:59:38.452259	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
74	2025-12-06 12:02:25.128344	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
75	2025-12-06 12:02:29.869379	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
76	2025-12-06 12:03:23.845353	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
77	2025-12-06 12:03:30.203299	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
78	2025-12-06 12:03:43.455895	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
79	2025-12-06 12:03:47.944948	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
80	2025-12-06 12:08:58.539425	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
81	2025-12-06 12:09:02.871477	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
82	2025-12-06 12:19:24.884832	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
83	2025-12-06 12:19:29.099778	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
84	2025-12-06 12:57:36.257501	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
85	2025-12-06 12:57:40.190035	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
86	2025-12-06 12:58:01.51038	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
87	2025-12-06 12:58:05.497953	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
88	2025-12-06 12:58:32.075817	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
89	2025-12-06 12:58:35.939534	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
90	2025-12-06 12:59:22.698255	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
91	2025-12-06 12:59:26.332422	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
92	2025-12-06 12:59:38.814982	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
93	2025-12-06 12:59:42.964582	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
94	2025-12-06 13:00:00.597901	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
95	2025-12-06 13:00:04.394681	Administrador Local	Acessou: Temas	Navegação	Usuário: Administrador Local | Página: Temas
96	2025-12-06 13:02:47.401512	Administrador Local	Acessou: Cadastrar Modelo	Navegação	Usuário: Administrador Local | Página: Cadastrar Modelo
97	2025-12-06 13:02:58.560474	Administrador Local	Acessou: Nova Ordem	Navegação	Usuário: Administrador Local | Página: Nova Ordem
98	2025-12-06 13:03:11.50144	Administrador Local	Acessou: Usuários	Navegação	Usuário: Administrador Local | Página: Usuários
99	2025-12-06 13:03:48.714233	Administrador Local	Acessou: Ordens de Corte Impressão	Navegação	Usuário: Administrador Local | Página: Ordens de Corte Impressão
100	2025-12-06 13:05:30.863171	Administrador Local	Acessou: Cadastrar Corte	Navegação	Usuário: Administrador Local | Página: Cadastrar Corte
101	2025-12-06 13:10:05.688312	Administrador Local	Acessou: Cadastrar Corte	Navegação	Usuário: Administrador Local | Página: Cadastrar Corte
102	2025-12-06 13:11:16.966591	Administrador Local	Acessou: Controle de Mão de Obra	Navegação	Usuário: Administrador Local | Página: Controle de Mão de Obra
103	2025-12-06 13:19:46.909395	Administrador Local	Acessou: Controle de Mão de Obra	Navegação	Usuário: Administrador Local | Página: Controle de Mão de Obra
104	2025-12-06 13:24:16.411587	Administrador Local	Acessou: Controle de Mão de Obra	Navegação	Usuário: Administrador Local | Página: Controle de Mão de Obra
105	2025-12-06 13:26:17.879618	Administrador Local	Acessou: Controle de Mão de Obra	Navegação	Usuário: Administrador Local | Página: Controle de Mão de Obra
\.


--
-- Data for Name: usuario_permissoes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuario_permissoes (usuario_id, codigo, pode_ver, pode_editar, pode_imprimir, pode_excluir, pode_administrar) FROM stdin;
1	dashboard	t	t	t	t	t
1	cadastro_modelos	t	t	t	t	t
1	editar_modelo	t	t	t	t	t
1	excluir_modelo	t	t	t	t	t
1	consultar_modelos	t	t	t	t	t
1	ficha_tecnica	t	t	t	t	t
1	importar_modelos	t	t	t	t	t
1	nova_ordem_corte	t	t	t	t	t
1	editar_ordem_corte	t	t	t	t	t
1	excluir_ordem_corte	t	t	t	t	t
1	consultar_ordens_corte	t	t	t	t	t
1	imprimir_ordem_corte	t	t	t	t	t
1	cadastro_corte	t	t	t	t	t
1	editar_corte	t	t	t	t	t
1	excluir_corte	t	t	t	t	t
1	consultar_cortes	t	t	t	t	t
1	controle_cortes	t	t	t	t	t
1	estoque_tecidos_entrada	t	t	t	t	t
1	estoque_tecidos_saida	t	t	t	t	t
1	estoque_tecidos_ajuste	t	t	t	t	t
1	estoque_tecidos_consultar	t	t	t	t	t
1	estoque_aviamentos_entrada	t	t	t	t	t
1	estoque_aviamentos_saida	t	t	t	t	t
1	estoque_aviamentos_consultar	t	t	t	t	t
1	estoque_insumos_entrada	t	t	t	t	t
1	estoque_insumos_saida	t	t	t	t	t
1	estoque_insumos_consultar	t	t	t	t	t
1	estoque_relatorios_geral	t	t	t	t	t
1	estoque_relatorios_movimentacao	t	t	t	t	t
1	estoque_relatorios_inventario	t	t	t	t	t
1	cadastro_faccoes	t	t	t	t	t
1	editar_faccao	t	t	t	t	t
1	excluir_faccao	t	t	t	t	t
1	consultar_faccoes	t	t	t	t	t
1	pesquisar_servico	t	t	t	t	t
1	controle_mao_obra	t	t	t	t	t
1	registro_producao	t	t	t	t	t
1	relatorio_produtividade	t	t	t	t	t
1	controle_horas	t	t	t	t	t
1	controle_producao	t	t	t	t	t
1	acompanhamento_ordens	t	t	t	t	t
1	planejamento_producao	t	t	t	t	t
1	controle_qualidade	t	t	t	t	t
1	registro_acabamento	t	t	t	t	t
1	controle_acabamento	t	t	t	t	t
1	finalizar_corte	t	t	t	t	t
1	qualidade_acabamento	t	t	t	t	t
1	pagamento_servicos	t	t	t	t	t
1	historico_pagamentos	t	t	t	t	t
1	custo_produto	t	t	t	t	t
1	analise_custos	t	t	t	t	t
1	folha_pagamento	t	t	t	t	t
1	registro_ponto	t	t	t	t	t
1	fechamento_mensal	t	t	t	t	t
1	fechamento_anual	t	t	t	t	t
1	contas_pagar	t	t	t	t	t
1	contas_receber	t	t	t	t	t
1	adiantamento	t	t	t	t	t
1	adiantamentos_pendentes	t	t	t	t	t
1	aprovar_adiantamento	t	t	t	t	t
1	relatorio_producao	t	t	t	t	t
1	relatorio_servicos_externos	t	t	t	t	t
1	relatorio_modelos_produzidos	t	t	t	t	t
1	relatorio_acabamento	t	t	t	t	t
1	relatorio_financeiro	t	t	t	t	t
1	relatorio_estoque	t	t	t	t	t
1	relatorio_cortes	t	t	t	t	t
1	relatorio_faccoes	t	t	t	t	t
1	config_usuarios	t	t	t	t	t
1	config_permissoes	t	t	t	t	t
1	config_backup	t	t	t	t	t
1	config_restore	t	t	t	t	t
1	config_temas	t	t	t	t	t
1	config_empresa	t	t	t	t	t
1	config_parametros	t	t	t	t	t
1	banco_dados	t	t	t	t	t
1	backup_automatico	t	t	t	t	t
1	otimizacao_bd	t	t	t	t	t
1	consultas_bd	t	t	t	t	t
1	sistema_admin	t	t	t	t	t
1	sistema_logs	t	t	t	t	t
1	sistema_backup	t	t	t	t	t
1	sistema_monitoramento	t	t	t	t	t
1	sistema_auditoria	t	t	t	t	t
\.


--
-- Data for Name: usuario_preferencias; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuario_preferencias (usuario_id, tema_nome, usar_tema_personalizado, tema_personalizado, layout_compacto, sidebar_recolhida, usar_animacoes, mostrar_dicas, idioma, notificacoes, atualizado_em) FROM stdin;
1	Cobalto Pro	f	\N	f	f	t	t	pt-BR	t	2025-12-05 22:47:38.044278
\.


--
-- Data for Name: usuario_temas_personalizados; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuario_temas_personalizados (id, usuario_id, nome_tema, cores_tema, data_criacao, atualizado_em) FROM stdin;
\.


--
-- Data for Name: usuarios; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuarios (id, usuario, senha_hash, hierarquia, email, data_criacao, ativo, dica_senha, ultimo_login, telefone, departamento, tema_preferido) FROM stdin;
1	Gil de Oliveira	$2a$06$aZYtnqaL2vqNWuFcBalan.SAD2ymIw4QQ0xP7L72xrVAFbzSkzHee	Administrador	opera@gil.com	2025-12-01 17:39:35.05019	t	25	\N	\N	\N	Cinza Oceano Claro
\.


--
-- Name: _schema_info_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera._schema_info_id_seq', 1, true);


--
-- Name: adiantamento_faccao_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.adiantamento_faccao_id_seq', 1, false);


--
-- Name: cadastro_de_corte_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_de_corte_id_seq', 1, true);


--
-- Name: cadastro_de_corte_lotes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_de_corte_lotes_id_seq', 2, true);


--
-- Name: cadastro_de_corte_tecidos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_de_corte_tecidos_id_seq', 2, true);


--
-- Name: cadastro_faccoes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_faccoes_id_seq', 1, true);


--
-- Name: cadastro_modelos_aviamentos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_aviamentos_id_seq', 1, false);


--
-- Name: cadastro_modelos_cabecalho_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_cabecalho_id_seq', 1, true);


--
-- Name: cadastro_modelos_grade_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_grade_id_seq', 1, false);


--
-- Name: cadastro_modelos_imagens_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_imagens_id_seq', 4, true);


--
-- Name: cadastro_modelos_outros_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_outros_id_seq', 1, false);


--
-- Name: cadastro_modelos_outros_servicos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_outros_servicos_id_seq', 1, false);


--
-- Name: cadastro_modelos_tecidos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_tecidos_id_seq', 1, true);


--
-- Name: controle_envio_cortes_detalhes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.controle_envio_cortes_detalhes_id_seq', 1, false);


--
-- Name: controle_envio_cortes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.controle_envio_cortes_id_seq', 1, false);


--
-- Name: controle_retorno_cortes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.controle_retorno_cortes_id_seq', 1, false);


--
-- Name: cortes_finalizados_completo_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cortes_finalizados_completo_id_seq', 1, false);


--
-- Name: cortes_finalizados_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cortes_finalizados_id_seq', 1, false);


--
-- Name: entrada_acabamento_detalhes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.entrada_acabamento_detalhes_id_seq', 1, false);


--
-- Name: entrada_acabamento_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.entrada_acabamento_id_seq', 1, false);


--
-- Name: envios_cortes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.envios_cortes_id_seq', 1, false);


--
-- Name: estoque_aviamentos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_aviamentos_id_seq', 1, false);


--
-- Name: estoque_escritorio_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_escritorio_id_seq', 1, false);


--
-- Name: estoque_insumos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_insumos_id_seq', 1, false);


--
-- Name: estoque_limpeza_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_limpeza_id_seq', 1, false);


--
-- Name: estoque_outros_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_outros_id_seq', 1, false);


--
-- Name: estoque_saida_log_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_saida_log_id_seq', 1, false);


--
-- Name: estoque_tecidos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_tecidos_id_seq', 5, true);


--
-- Name: ficha_tecnica_cabecalho_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.ficha_tecnica_cabecalho_id_seq', 1, false);


--
-- Name: historico_de_servico_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.historico_de_servico_id_seq', 1, false);


--
-- Name: historico_servicos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.historico_servicos_id_seq', 1, false);


--
-- Name: log_finalizacoes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.log_finalizacoes_id_seq', 1, false);


--
-- Name: ordem_corte_ficha_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.ordem_corte_ficha_id_seq', 1, true);


--
-- Name: ordem_corte_lotes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.ordem_corte_lotes_id_seq', 1, false);


--
-- Name: ordem_grade_preferencias_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.ordem_grade_preferencias_id_seq', 1, false);


--
-- Name: pagamento_corte_acabamento_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.pagamento_corte_acabamento_id_seq', 1, false);


--
-- Name: pagamento_servicos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.pagamento_servicos_id_seq', 1, false);


--
-- Name: pecas_finalizadas_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.pecas_finalizadas_id_seq', 1, false);


--
-- Name: relatorios_finalizacao_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.relatorios_finalizacao_id_seq', 1, false);


--
-- Name: retorno_detalhes_tamanho_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.retorno_detalhes_tamanho_id_seq', 1, false);


--
-- Name: servicos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.servicos_id_seq', 1, false);


--
-- Name: usuario_logs_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.usuario_logs_id_seq', 105, true);


--
-- Name: usuario_temas_personalizados_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.usuario_temas_personalizados_id_seq', 1, false);


--
-- Name: usuarios_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.usuarios_id_seq', 1, true);


--
-- Name: _schema_info _schema_info_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera._schema_info
    ADD CONSTRAINT _schema_info_pkey PRIMARY KEY (id);


--
-- Name: adiantamento_faccao adiantamento_faccao_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.adiantamento_faccao
    ADD CONSTRAINT adiantamento_faccao_pkey PRIMARY KEY (id);


--
-- Name: cadastro_de_corte_lotes cadastro_de_corte_lotes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_lotes
    ADD CONSTRAINT cadastro_de_corte_lotes_pkey PRIMARY KEY (id);


--
-- Name: cadastro_de_corte cadastro_de_corte_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte
    ADD CONSTRAINT cadastro_de_corte_pkey PRIMARY KEY (id);


--
-- Name: cadastro_de_corte_tecidos cadastro_de_corte_tecidos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_tecidos
    ADD CONSTRAINT cadastro_de_corte_tecidos_pkey PRIMARY KEY (id);


--
-- Name: cadastro_faccoes cadastro_faccoes_codigo_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_faccoes
    ADD CONSTRAINT cadastro_faccoes_codigo_key UNIQUE (codigo);


--
-- Name: cadastro_faccoes cadastro_faccoes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_faccoes
    ADD CONSTRAINT cadastro_faccoes_pkey PRIMARY KEY (id);


--
-- Name: cadastro_modelos_aviamentos cadastro_modelos_aviamentos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_aviamentos
    ADD CONSTRAINT cadastro_modelos_aviamentos_pkey PRIMARY KEY (id);


--
-- Name: cadastro_modelos_cabecalho cadastro_modelos_cabecalho_codigo_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_cabecalho
    ADD CONSTRAINT cadastro_modelos_cabecalho_codigo_key UNIQUE (codigo);


--
-- Name: cadastro_modelos_cabecalho cadastro_modelos_cabecalho_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_cabecalho
    ADD CONSTRAINT cadastro_modelos_cabecalho_pkey PRIMARY KEY (id);


--
-- Name: cadastro_modelos_grade cadastro_modelos_grade_modelo_id_tamanho_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_grade
    ADD CONSTRAINT cadastro_modelos_grade_modelo_id_tamanho_key UNIQUE (modelo_id, tamanho);


--
-- Name: cadastro_modelos_grade cadastro_modelos_grade_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_grade
    ADD CONSTRAINT cadastro_modelos_grade_pkey PRIMARY KEY (id);


--
-- Name: cadastro_modelos_imagens cadastro_modelos_imagens_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_imagens
    ADD CONSTRAINT cadastro_modelos_imagens_pkey PRIMARY KEY (id);


--
-- Name: cadastro_modelos_outros cadastro_modelos_outros_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros
    ADD CONSTRAINT cadastro_modelos_outros_pkey PRIMARY KEY (id);


--
-- Name: cadastro_modelos_outros_servicos cadastro_modelos_outros_servicos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros_servicos
    ADD CONSTRAINT cadastro_modelos_outros_servicos_pkey PRIMARY KEY (id);


--
-- Name: cadastro_modelos_tecidos cadastro_modelos_tecidos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_tecidos
    ADD CONSTRAINT cadastro_modelos_tecidos_pkey PRIMARY KEY (id);


--
-- Name: controle_envio_cortes_detalhes controle_envio_cortes_detalhes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_envio_cortes_detalhes
    ADD CONSTRAINT controle_envio_cortes_detalhes_pkey PRIMARY KEY (id);


--
-- Name: controle_envio_cortes controle_envio_cortes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_envio_cortes
    ADD CONSTRAINT controle_envio_cortes_pkey PRIMARY KEY (id);


--
-- Name: controle_retorno_cortes controle_retorno_cortes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_retorno_cortes
    ADD CONSTRAINT controle_retorno_cortes_pkey PRIMARY KEY (id);


--
-- Name: cortes_finalizados_completo cortes_finalizados_completo_entrada_id_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo
    ADD CONSTRAINT cortes_finalizados_completo_entrada_id_key UNIQUE (entrada_id);


--
-- Name: cortes_finalizados_completo cortes_finalizados_completo_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo
    ADD CONSTRAINT cortes_finalizados_completo_pkey PRIMARY KEY (id);


--
-- Name: cortes_finalizados cortes_finalizados_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados
    ADD CONSTRAINT cortes_finalizados_pkey PRIMARY KEY (id);


--
-- Name: entrada_acabamento_detalhes entrada_acabamento_detalhes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento_detalhes
    ADD CONSTRAINT entrada_acabamento_detalhes_pkey PRIMARY KEY (id);


--
-- Name: entrada_acabamento entrada_acabamento_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento
    ADD CONSTRAINT entrada_acabamento_pkey PRIMARY KEY (id);


--
-- Name: envio_detalhes_tamanho envio_detalhes_tamanho_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envio_detalhes_tamanho
    ADD CONSTRAINT envio_detalhes_tamanho_pkey PRIMARY KEY (envio_id, tamanho);


--
-- Name: envios_cortes envios_cortes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envios_cortes
    ADD CONSTRAINT envios_cortes_pkey PRIMARY KEY (id);


--
-- Name: estoque_aviamentos estoque_aviamentos_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_aviamentos
    ADD CONSTRAINT estoque_aviamentos_codigo_cor_key UNIQUE (codigo, cor);


--
-- Name: estoque_aviamentos estoque_aviamentos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_aviamentos
    ADD CONSTRAINT estoque_aviamentos_pkey PRIMARY KEY (id);


--
-- Name: estoque_escritorio estoque_escritorio_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_escritorio
    ADD CONSTRAINT estoque_escritorio_codigo_cor_key UNIQUE (codigo, cor);


--
-- Name: estoque_escritorio estoque_escritorio_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_escritorio
    ADD CONSTRAINT estoque_escritorio_pkey PRIMARY KEY (id);


--
-- Name: estoque_insumos estoque_insumos_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_insumos
    ADD CONSTRAINT estoque_insumos_codigo_cor_key UNIQUE (codigo, cor);


--
-- Name: estoque_insumos estoque_insumos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_insumos
    ADD CONSTRAINT estoque_insumos_pkey PRIMARY KEY (id);


--
-- Name: estoque_limpeza estoque_limpeza_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_limpeza
    ADD CONSTRAINT estoque_limpeza_codigo_cor_key UNIQUE (codigo, cor);


--
-- Name: estoque_limpeza estoque_limpeza_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_limpeza
    ADD CONSTRAINT estoque_limpeza_pkey PRIMARY KEY (id);


--
-- Name: estoque_outros estoque_outros_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_outros
    ADD CONSTRAINT estoque_outros_codigo_cor_key UNIQUE (codigo, cor);


--
-- Name: estoque_outros estoque_outros_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_outros
    ADD CONSTRAINT estoque_outros_pkey PRIMARY KEY (id);


--
-- Name: estoque_saida_log estoque_saida_log_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_saida_log
    ADD CONSTRAINT estoque_saida_log_pkey PRIMARY KEY (id);


--
-- Name: estoque_tecidos estoque_tecidos_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_tecidos
    ADD CONSTRAINT estoque_tecidos_codigo_cor_key UNIQUE (codigo, cor);


--
-- Name: estoque_tecidos estoque_tecidos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_tecidos
    ADD CONSTRAINT estoque_tecidos_pkey PRIMARY KEY (id);


--
-- Name: ficha_tecnica_cabecalho ficha_tecnica_cabecalho_codigo_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ficha_tecnica_cabecalho
    ADD CONSTRAINT ficha_tecnica_cabecalho_codigo_key UNIQUE (codigo);


--
-- Name: ficha_tecnica_cabecalho ficha_tecnica_cabecalho_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ficha_tecnica_cabecalho
    ADD CONSTRAINT ficha_tecnica_cabecalho_pkey PRIMARY KEY (id);


--
-- Name: historico_de_servico historico_de_servico_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_de_servico
    ADD CONSTRAINT historico_de_servico_pkey PRIMARY KEY (id);


--
-- Name: historico_servicos historico_servicos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_servicos
    ADD CONSTRAINT historico_servicos_pkey PRIMARY KEY (id);


--
-- Name: log_finalizacoes log_finalizacoes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.log_finalizacoes
    ADD CONSTRAINT log_finalizacoes_pkey PRIMARY KEY (id);


--
-- Name: ordem_corte_ficha ordem_corte_ficha_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_ficha
    ADD CONSTRAINT ordem_corte_ficha_pkey PRIMARY KEY (id);


--
-- Name: ordem_corte_lotes ordem_corte_lotes_ordem_id_lote_numero_tamanho_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_lotes
    ADD CONSTRAINT ordem_corte_lotes_ordem_id_lote_numero_tamanho_key UNIQUE (ordem_id, lote_numero, tamanho);


--
-- Name: ordem_corte_lotes ordem_corte_lotes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_lotes
    ADD CONSTRAINT ordem_corte_lotes_pkey PRIMARY KEY (id);


--
-- Name: ordem_grade_preferencias ordem_grade_preferencias_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_grade_preferencias
    ADD CONSTRAINT ordem_grade_preferencias_pkey PRIMARY KEY (id);


--
-- Name: ordem_grade_preferencias ordem_grade_preferencias_usuario_id_nome_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_grade_preferencias
    ADD CONSTRAINT ordem_grade_preferencias_usuario_id_nome_key UNIQUE (usuario_id, nome);


--
-- Name: pagamento_corte_acabamento pagamento_corte_acabamento_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_corte_acabamento
    ADD CONSTRAINT pagamento_corte_acabamento_pkey PRIMARY KEY (id);


--
-- Name: pagamento_servicos_detalhe pagamento_servicos_detalhe_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_servicos_detalhe
    ADD CONSTRAINT pagamento_servicos_detalhe_pkey PRIMARY KEY (pagamento_id, entrada_acabamento_id);


--
-- Name: pagamento_servicos pagamento_servicos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_servicos
    ADD CONSTRAINT pagamento_servicos_pkey PRIMARY KEY (id);


--
-- Name: pecas_finalizadas pecas_finalizadas_entrada_id_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pecas_finalizadas
    ADD CONSTRAINT pecas_finalizadas_entrada_id_key UNIQUE (entrada_id);


--
-- Name: pecas_finalizadas pecas_finalizadas_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pecas_finalizadas
    ADD CONSTRAINT pecas_finalizadas_pkey PRIMARY KEY (id);


--
-- Name: pricing_profiles pricing_profiles_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pricing_profiles
    ADD CONSTRAINT pricing_profiles_pkey PRIMARY KEY (nome);


--
-- Name: relatorios_finalizacao relatorios_finalizacao_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.relatorios_finalizacao
    ADD CONSTRAINT relatorios_finalizacao_pkey PRIMARY KEY (id);


--
-- Name: retorno_detalhes_tamanho retorno_detalhes_tamanho_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.retorno_detalhes_tamanho
    ADD CONSTRAINT retorno_detalhes_tamanho_pkey PRIMARY KEY (id);


--
-- Name: servicos servicos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.servicos
    ADD CONSTRAINT servicos_pkey PRIMARY KEY (id);


--
-- Name: usuario_logs usuario_logs_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_logs
    ADD CONSTRAINT usuario_logs_pkey PRIMARY KEY (id);


--
-- Name: usuario_permissoes usuario_permissoes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_permissoes
    ADD CONSTRAINT usuario_permissoes_pkey PRIMARY KEY (usuario_id, codigo);


--
-- Name: usuario_preferencias usuario_preferencias_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_preferencias
    ADD CONSTRAINT usuario_preferencias_pkey PRIMARY KEY (usuario_id);


--
-- Name: usuario_temas_personalizados usuario_temas_personalizados_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_temas_personalizados
    ADD CONSTRAINT usuario_temas_personalizados_pkey PRIMARY KEY (id);


--
-- Name: usuario_temas_personalizados usuario_temas_personalizados_usuario_id_nome_tema_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_temas_personalizados
    ADD CONSTRAINT usuario_temas_personalizados_usuario_id_nome_tema_key UNIQUE (usuario_id, nome_tema);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: usuarios usuarios_usuario_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuarios
    ADD CONSTRAINT usuarios_usuario_key UNIQUE (usuario);


--
-- Name: idx_adiantamento_corte; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_adiantamento_corte ON opera.adiantamento_faccao USING btree (corte_id);


--
-- Name: idx_adiantamento_faccao; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_adiantamento_faccao ON opera.adiantamento_faccao USING btree (faccao);


--
-- Name: idx_cadastro_corte_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cadastro_corte_codigo ON opera.cadastro_de_corte USING btree (codigo);


--
-- Name: idx_cadastro_corte_cortador; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cadastro_corte_cortador ON opera.cadastro_de_corte USING btree (cortador);


--
-- Name: idx_cadastro_corte_data; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cadastro_corte_data ON opera.cadastro_de_corte USING btree (data);


--
-- Name: idx_cadastro_corte_numero_ordem; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cadastro_corte_numero_ordem ON opera.cadastro_de_corte USING btree (numero_ordem);


--
-- Name: idx_cadastro_modelos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cadastro_modelos_codigo ON opera.cadastro_modelos_cabecalho USING btree (codigo);


--
-- Name: idx_cadastro_modelos_descricao; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cadastro_modelos_descricao ON opera.cadastro_modelos_cabecalho USING btree (descricao);


--
-- Name: idx_corte_lotes_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_corte_lotes_cadastro ON opera.cadastro_de_corte_lotes USING btree (cadastro_id);


--
-- Name: idx_corte_tecidos_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_corte_tecidos_cadastro ON opera.cadastro_de_corte_tecidos USING btree (cadastro_id);


--
-- Name: idx_cortes_finalizados_completo_corte; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cortes_finalizados_completo_corte ON opera.cortes_finalizados_completo USING btree (corte_id);


--
-- Name: idx_cortes_finalizados_completo_entrada; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cortes_finalizados_completo_entrada ON opera.cortes_finalizados_completo USING btree (entrada_id);


--
-- Name: idx_cortes_finalizados_completo_status; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cortes_finalizados_completo_status ON opera.cortes_finalizados_completo USING btree (status);


--
-- Name: idx_cortes_finalizados_corte; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cortes_finalizados_corte ON opera.cortes_finalizados USING btree (corte_id);


--
-- Name: idx_cortes_finalizados_data_chegada; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cortes_finalizados_data_chegada ON opera.cortes_finalizados USING btree (data_chegada);


--
-- Name: idx_cortes_finalizados_entrada; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cortes_finalizados_entrada ON opera.cortes_finalizados USING btree (entrada_id);


--
-- Name: idx_ctrl_retorno_data; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ctrl_retorno_data ON opera.controle_retorno_cortes USING btree (data_chegada);


--
-- Name: idx_ctrl_retorno_envio; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ctrl_retorno_envio ON opera.controle_retorno_cortes USING btree (envio_id);


--
-- Name: idx_entrada_acabamento_data; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_entrada_acabamento_data ON opera.entrada_acabamento USING btree (data_chegada);


--
-- Name: idx_entrada_acabamento_envio; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_entrada_acabamento_envio ON opera.entrada_acabamento USING btree (envio_id);


--
-- Name: idx_entrada_det_entrada; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_entrada_det_entrada ON opera.entrada_acabamento_detalhes USING btree (entrada_id);


--
-- Name: idx_entrada_det_status; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_entrada_det_status ON opera.entrada_acabamento_detalhes USING btree (status_finalizacao);


--
-- Name: idx_envio_cortes_costureira; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_cortes_costureira ON opera.controle_envio_cortes USING btree (costureira);


--
-- Name: idx_envio_cortes_data_envio; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_cortes_data_envio ON opera.controle_envio_cortes USING btree (data_envio);


--
-- Name: idx_envio_cortes_ordem_corte; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_cortes_ordem_corte ON opera.controle_envio_cortes USING btree (ordem_corte);


--
-- Name: idx_envio_cortes_servico; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_cortes_servico ON opera.controle_envio_cortes USING btree (servico);


--
-- Name: idx_envio_cortes_status; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_cortes_status ON opera.controle_envio_cortes USING btree (status);


--
-- Name: idx_envio_det_envio; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_det_envio ON opera.controle_envio_cortes_detalhes USING btree (envio_id);


--
-- Name: idx_envio_det_tamanho; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_det_tamanho ON opera.envio_detalhes_tamanho USING btree (tamanho);


--
-- Name: idx_envio_det_tamanho_envio; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_det_tamanho_envio ON opera.envio_detalhes_tamanho USING btree (envio_id);


--
-- Name: idx_envios_cortes_corte; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envios_cortes_corte ON opera.envios_cortes USING btree (corte_id);


--
-- Name: idx_envios_cortes_data; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envios_cortes_data ON opera.envios_cortes USING btree (data_envio);


--
-- Name: idx_envios_cortes_prestador; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envios_cortes_prestador ON opera.envios_cortes USING btree (prestador_id);


--
-- Name: idx_estoque_aviamentos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_aviamentos_codigo ON opera.estoque_aviamentos USING btree (codigo);


--
-- Name: idx_estoque_aviamentos_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_aviamentos_cor ON opera.estoque_aviamentos USING btree (cor);


--
-- Name: idx_estoque_escritorio_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_escritorio_codigo ON opera.estoque_escritorio USING btree (codigo);


--
-- Name: idx_estoque_escritorio_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_escritorio_cor ON opera.estoque_escritorio USING btree (cor);


--
-- Name: idx_estoque_insumos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_insumos_codigo ON opera.estoque_insumos USING btree (codigo);


--
-- Name: idx_estoque_insumos_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_insumos_cor ON opera.estoque_insumos USING btree (cor);


--
-- Name: idx_estoque_limpeza_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_limpeza_codigo ON opera.estoque_limpeza USING btree (codigo);


--
-- Name: idx_estoque_limpeza_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_limpeza_cor ON opera.estoque_limpeza USING btree (cor);


--
-- Name: idx_estoque_outros_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_outros_codigo ON opera.estoque_outros USING btree (codigo);


--
-- Name: idx_estoque_outros_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_outros_cor ON opera.estoque_outros USING btree (cor);


--
-- Name: idx_estoque_tecidos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_tecidos_codigo ON opera.estoque_tecidos USING btree (codigo);


--
-- Name: idx_estoque_tecidos_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_tecidos_cor ON opera.estoque_tecidos USING btree (cor);


--
-- Name: idx_faccoes_ativo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_faccoes_ativo ON opera.cadastro_faccoes USING btree (ativo);


--
-- Name: idx_faccoes_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_faccoes_codigo ON opera.cadastro_faccoes USING btree (codigo);


--
-- Name: idx_faccoes_nome; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_faccoes_nome ON opera.cadastro_faccoes USING btree (nome);


--
-- Name: idx_faccoes_tipo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_faccoes_tipo ON opera.cadastro_faccoes USING btree (tipo_prestador);


--
-- Name: idx_faccoes_tipo_ativo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_faccoes_tipo_ativo ON opera.cadastro_faccoes USING btree (tipo_prestador, ativo);


--
-- Name: idx_ficha_tecnica_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ficha_tecnica_codigo ON opera.ficha_tecnica_cabecalho USING btree (codigo);


--
-- Name: idx_hist_servico_id; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_hist_servico_id ON opera.historico_servicos USING btree (servico_id);


--
-- Name: idx_log_finalizacoes_data; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_log_finalizacoes_data ON opera.log_finalizacoes USING btree (data_hora);


--
-- Name: idx_log_finalizacoes_entrada; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_log_finalizacoes_entrada ON opera.log_finalizacoes USING btree (entrada_id);


--
-- Name: idx_log_finalizacoes_usuario; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_log_finalizacoes_usuario ON opera.log_finalizacoes USING btree (usuario);


--
-- Name: idx_modelos_aviamentos_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_aviamentos_cadastro ON opera.cadastro_modelos_aviamentos USING btree (cadastro_id);


--
-- Name: idx_modelos_aviamentos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_aviamentos_codigo ON opera.cadastro_modelos_aviamentos USING btree (codigo_modelo);


--
-- Name: idx_modelos_imagens_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_imagens_cadastro ON opera.cadastro_modelos_imagens USING btree (cadastro_id);


--
-- Name: idx_modelos_imagens_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_imagens_codigo ON opera.cadastro_modelos_imagens USING btree (codigo_modelo);


--
-- Name: idx_modelos_outros_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_outros_cadastro ON opera.cadastro_modelos_outros USING btree (cadastro_id);


--
-- Name: idx_modelos_outros_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_outros_codigo ON opera.cadastro_modelos_outros USING btree (codigo_modelo);


--
-- Name: idx_modelos_tecidos_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_tecidos_cadastro ON opera.cadastro_modelos_tecidos USING btree (cadastro_id);


--
-- Name: idx_modelos_tecidos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_tecidos_codigo ON opera.cadastro_modelos_tecidos USING btree (codigo_modelo);


--
-- Name: idx_ordem_corte_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ordem_corte_codigo ON opera.ordem_corte_ficha USING btree (codigo_modelo);


--
-- Name: idx_ordem_corte_codigo_modelo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ordem_corte_codigo_modelo ON opera.ordem_corte_ficha USING btree (codigo_modelo);


--
-- Name: idx_ordem_corte_data; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ordem_corte_data ON opera.ordem_corte_ficha USING btree (data_registro);


--
-- Name: idx_ordem_corte_data_final; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ordem_corte_data_final ON opera.ordem_corte_ficha USING btree (data_final);


--
-- Name: idx_ordem_corte_status; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ordem_corte_status ON opera.ordem_corte_ficha USING btree (status);


--
-- Name: idx_pagamento_corte_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_pagamento_corte_codigo ON opera.pagamento_corte_acabamento USING btree (codigo);


--
-- Name: idx_pagamento_corte_costureira; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_pagamento_corte_costureira ON opera.pagamento_corte_acabamento USING btree (costureira);


--
-- Name: idx_pagamento_corte_data_pagamento; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_pagamento_corte_data_pagamento ON opera.pagamento_corte_acabamento USING btree (data_pagamento);


--
-- Name: idx_pecas_finalizadas_corte; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_pecas_finalizadas_corte ON opera.pecas_finalizadas USING btree (corte_id);


--
-- Name: idx_pecas_finalizadas_costureira; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_pecas_finalizadas_costureira ON opera.pecas_finalizadas USING btree (costureira);


--
-- Name: idx_pecas_finalizadas_data_chegada; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_pecas_finalizadas_data_chegada ON opera.pecas_finalizadas USING btree (data_chegada);


--
-- Name: idx_pecas_finalizadas_status; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_pecas_finalizadas_status ON opera.pecas_finalizadas USING btree (status);


--
-- Name: idx_relatorios_data; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_relatorios_data ON opera.relatorios_finalizacao USING btree (data_geracao);


--
-- Name: idx_relatorios_entrada; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_relatorios_entrada ON opera.relatorios_finalizacao USING btree (entrada_id);


--
-- Name: idx_relatorios_usuario; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_relatorios_usuario ON opera.relatorios_finalizacao USING btree (usuario_geracao);


--
-- Name: idx_retorno_tam_envio; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_retorno_tam_envio ON opera.retorno_detalhes_tamanho USING btree (envio_id);


--
-- Name: idx_retorno_tam_tamanho; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_retorno_tam_tamanho ON opera.retorno_detalhes_tamanho USING btree (tamanho);


--
-- Name: idx_servicos_data_inicio; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_servicos_data_inicio ON opera.servicos USING btree (data_inicio);


--
-- Name: idx_servicos_prestador; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_servicos_prestador ON opera.servicos USING btree (prestador);


--
-- Name: idx_usuario_logs_data_hora; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_logs_data_hora ON opera.usuario_logs USING btree (data_hora);


--
-- Name: idx_usuario_logs_usuario; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_logs_usuario ON opera.usuario_logs USING btree (usuario);


--
-- Name: idx_usuario_permissoes_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_permissoes_codigo ON opera.usuario_permissoes USING btree (codigo);


--
-- Name: idx_usuario_preferencias_tema; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_preferencias_tema ON opera.usuario_preferencias USING btree (tema_nome);


--
-- Name: idx_usuario_temas_nome; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_temas_nome ON opera.usuario_temas_personalizados USING btree (nome_tema);


--
-- Name: idx_usuario_temas_usuario; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_temas_usuario ON opera.usuario_temas_personalizados USING btree (usuario_id);


--
-- Name: idx_usuarios_ativo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuarios_ativo ON opera.usuarios USING btree (ativo);


--
-- Name: idx_usuarios_hierarquia; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuarios_hierarquia ON opera.usuarios USING btree (hierarquia);


--
-- Name: usuarios tr_log_login; Type: TRIGGER; Schema: opera; Owner: postgres
--

CREATE TRIGGER tr_log_login BEFORE UPDATE OF ultimo_login ON opera.usuarios FOR EACH ROW WHEN ((new.ultimo_login IS DISTINCT FROM old.ultimo_login)) EXECUTE FUNCTION opera.log_login_usuario();


--
-- Name: usuario_temas_personalizados tr_validar_cores_tema; Type: TRIGGER; Schema: opera; Owner: postgres
--

CREATE TRIGGER tr_validar_cores_tema BEFORE INSERT OR UPDATE ON opera.usuario_temas_personalizados FOR EACH ROW EXECUTE FUNCTION opera.validar_cores_tema();


--
-- Name: cadastro_de_corte_lotes cadastro_de_corte_lotes_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_lotes
    ADD CONSTRAINT cadastro_de_corte_lotes_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE;


--
-- Name: cadastro_de_corte_tecidos cadastro_de_corte_tecidos_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_tecidos
    ADD CONSTRAINT cadastro_de_corte_tecidos_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE;


--
-- Name: cadastro_modelos_aviamentos cadastro_modelos_aviamentos_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_aviamentos
    ADD CONSTRAINT cadastro_modelos_aviamentos_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- Name: cadastro_modelos_grade cadastro_modelos_grade_modelo_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_grade
    ADD CONSTRAINT cadastro_modelos_grade_modelo_id_fkey FOREIGN KEY (modelo_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- Name: cadastro_modelos_imagens cadastro_modelos_imagens_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_imagens
    ADD CONSTRAINT cadastro_modelos_imagens_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- Name: cadastro_modelos_outros cadastro_modelos_outros_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros
    ADD CONSTRAINT cadastro_modelos_outros_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- Name: cadastro_modelos_outros_servicos cadastro_modelos_outros_servicos_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros_servicos
    ADD CONSTRAINT cadastro_modelos_outros_servicos_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- Name: cadastro_modelos_tecidos cadastro_modelos_tecidos_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_tecidos
    ADD CONSTRAINT cadastro_modelos_tecidos_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- Name: controle_envio_cortes controle_envio_cortes_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_envio_cortes
    ADD CONSTRAINT controle_envio_cortes_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL;


--
-- Name: controle_envio_cortes_detalhes controle_envio_cortes_detalhes_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_envio_cortes_detalhes
    ADD CONSTRAINT controle_envio_cortes_detalhes_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE;


--
-- Name: controle_retorno_cortes controle_retorno_cortes_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_retorno_cortes
    ADD CONSTRAINT controle_retorno_cortes_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.envios_cortes(id) ON DELETE CASCADE;


--
-- Name: cortes_finalizados_completo cortes_finalizados_completo_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo
    ADD CONSTRAINT cortes_finalizados_completo_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.controle_envio_cortes(id);


--
-- Name: cortes_finalizados_completo cortes_finalizados_completo_entrada_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo
    ADD CONSTRAINT cortes_finalizados_completo_entrada_id_fkey FOREIGN KEY (entrada_id) REFERENCES opera.entrada_acabamento(id);


--
-- Name: entrada_acabamento_detalhes entrada_acabamento_detalhes_entrada_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento_detalhes
    ADD CONSTRAINT entrada_acabamento_detalhes_entrada_id_fkey FOREIGN KEY (entrada_id) REFERENCES opera.entrada_acabamento(id) ON DELETE CASCADE;


--
-- Name: entrada_acabamento entrada_acabamento_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento
    ADD CONSTRAINT entrada_acabamento_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE;


--
-- Name: envio_detalhes_tamanho envio_detalhes_tamanho_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envio_detalhes_tamanho
    ADD CONSTRAINT envio_detalhes_tamanho_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE;


--
-- Name: envios_cortes envios_cortes_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envios_cortes
    ADD CONSTRAINT envios_cortes_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE RESTRICT;


--
-- Name: envios_cortes envios_cortes_prestador_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envios_cortes
    ADD CONSTRAINT envios_cortes_prestador_id_fkey FOREIGN KEY (prestador_id) REFERENCES opera.cadastro_faccoes(id) ON DELETE RESTRICT;


--
-- Name: historico_de_servico historico_de_servico_entrada_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_de_servico
    ADD CONSTRAINT historico_de_servico_entrada_id_fkey FOREIGN KEY (entrada_id) REFERENCES opera.entrada_acabamento(id) ON DELETE SET NULL;


--
-- Name: historico_de_servico historico_de_servico_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_de_servico
    ADD CONSTRAINT historico_de_servico_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE;


--
-- Name: historico_de_servico historico_de_servico_pagamento_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_de_servico
    ADD CONSTRAINT historico_de_servico_pagamento_id_fkey FOREIGN KEY (pagamento_id) REFERENCES opera.pagamento_servicos(id) ON DELETE SET NULL;


--
-- Name: historico_servicos historico_servicos_servico_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_servicos
    ADD CONSTRAINT historico_servicos_servico_id_fkey FOREIGN KEY (servico_id) REFERENCES opera.servicos(id) ON DELETE CASCADE;


--
-- Name: log_finalizacoes log_finalizacoes_entrada_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.log_finalizacoes
    ADD CONSTRAINT log_finalizacoes_entrada_id_fkey FOREIGN KEY (entrada_id) REFERENCES opera.entrada_acabamento(id);


--
-- Name: ordem_corte_lotes ordem_corte_lotes_ordem_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_lotes
    ADD CONSTRAINT ordem_corte_lotes_ordem_id_fkey FOREIGN KEY (ordem_id) REFERENCES opera.ordem_corte_ficha(id) ON DELETE CASCADE;


--
-- Name: ordem_grade_preferencias ordem_grade_preferencias_usuario_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_grade_preferencias
    ADD CONSTRAINT ordem_grade_preferencias_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES opera.usuarios(id) ON DELETE CASCADE;


--
-- Name: pagamento_servicos_detalhe pagamento_servicos_detalhe_entrada_acabamento_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_servicos_detalhe
    ADD CONSTRAINT pagamento_servicos_detalhe_entrada_acabamento_id_fkey FOREIGN KEY (entrada_acabamento_id) REFERENCES opera.entrada_acabamento(id) ON DELETE CASCADE;


--
-- Name: pagamento_servicos_detalhe pagamento_servicos_detalhe_pagamento_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_servicos_detalhe
    ADD CONSTRAINT pagamento_servicos_detalhe_pagamento_id_fkey FOREIGN KEY (pagamento_id) REFERENCES opera.pagamento_servicos(id) ON DELETE CASCADE;


--
-- Name: pagamento_servicos pagamento_servicos_prestador_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_servicos
    ADD CONSTRAINT pagamento_servicos_prestador_id_fkey FOREIGN KEY (prestador_id) REFERENCES opera.cadastro_faccoes(id) ON DELETE SET NULL;


--
-- Name: pecas_finalizadas pecas_finalizadas_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pecas_finalizadas
    ADD CONSTRAINT pecas_finalizadas_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL;


--
-- Name: relatorios_finalizacao relatorios_finalizacao_entrada_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.relatorios_finalizacao
    ADD CONSTRAINT relatorios_finalizacao_entrada_id_fkey FOREIGN KEY (entrada_id) REFERENCES opera.entrada_acabamento(id);


--
-- Name: retorno_detalhes_tamanho retorno_detalhes_tamanho_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.retorno_detalhes_tamanho
    ADD CONSTRAINT retorno_detalhes_tamanho_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.envios_cortes(id) ON DELETE CASCADE;


--
-- Name: usuario_permissoes usuario_permissoes_usuario_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_permissoes
    ADD CONSTRAINT usuario_permissoes_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES opera.usuarios(id) ON DELETE CASCADE;


--
-- Name: usuario_preferencias usuario_preferencias_usuario_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_preferencias
    ADD CONSTRAINT usuario_preferencias_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES opera.usuarios(id) ON DELETE CASCADE;


--
-- Name: usuario_temas_personalizados usuario_temas_personalizados_usuario_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_temas_personalizados
    ADD CONSTRAINT usuario_temas_personalizados_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES opera.usuarios(id) ON DELETE CASCADE;


--
-- Name: SCHEMA opera; Type: ACL; Schema: -; Owner: postgres
--

GRANT ALL ON SCHEMA opera TO opera_app;


--
-- PostgreSQL database dump complete
--

\unrestrict F4fm52NQX4Vjnr8PEOgemkxyIc5UH7728Vd2uFXCizUseTmpSC6SOSjmZUdPvTS

