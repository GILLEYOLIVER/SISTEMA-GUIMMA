--
-- PostgreSQL database dump
--

\restrict rx2EQYoKdDYmvsgAnXUIOkJ9HxLyr9gbN4lyCLjXXPi3E0tzn4uJlzCQshg3SMq

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
-- Name: registrar_log_usuario(character varying, text, text, text); Type: FUNCTION; Schema: opera; Owner: postgres
--

CREATE FUNCTION opera.registrar_log_usuario(p_usuario character varying, p_acao text, p_pagina text DEFAULT NULL::text, p_detalhe text DEFAULT NULL::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION opera.registrar_log_usuario(p_usuario character varying, p_acao text, p_pagina text, p_detalhe text) OWNER TO postgres;

--
-- Name: validar_cores_tema(); Type: FUNCTION; Schema: opera; Owner: postgres
--

CREATE FUNCTION opera.validar_cores_tema() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.cores_tema IS NULL OR jsonb_typeof(NEW.cores_tema) != 'object' THEN
        RAISE EXCEPTION 'Estrutura de cores do tema inválida. Deve ser um objeto JSON.';
    END IF;

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
$_$;


ALTER FUNCTION opera.validar_senha(p_usuario text, p_senha text) OWNER TO postgres;

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
    tipo_prestador character varying(50) DEFAULT 'Faccao'::character varying,
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
    gasto_por_peca text DEFAULT ''::text,
    gasto_total_por_peca numeric(12,4) DEFAULT 0,
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
    valor_unidade numeric(12,2) DEFAULT 0,
    valor_total numeric(12,2) DEFAULT 0,
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
    status character varying(50) DEFAULT 'Em Conferencia'::character varying,
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
    envio_id integer,
    retorno_id integer,
    tipo_servico character varying(100),
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
    bonificacao numeric(12,2) DEFAULT 0.00,
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
    valor_total numeric(12,2) DEFAULT 0.00,
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
    envio_id integer,
    corte_id integer,
    descricao text,
    ordem_corte character varying(100),
    codigo_corte character varying(100),
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
    copias_do_corte integer DEFAULT 0,
    quantidade_pilotos integer DEFAULT 0,
    valor_peca numeric(12,2) DEFAULT 0
);


ALTER TABLE opera.envio_detalhes_tamanho OWNER TO postgres;

--
-- Name: envios_cortes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.envios_cortes (
    id integer NOT NULL,
    remessa_id uuid,
    data_envio date NOT NULL,
    hora_envio time without time zone,
    prestador_id integer,
    tipo_servico text,
    corte_id integer,
    ordem_corte character varying(50),
    codigo_corte character varying(100),
    descricao_corte text,
    colecao character varying(100),
    material character varying(100),
    cliente character varying(200),
    cores text,
    prioridade character varying(30),
    forma_pagamento character varying(50),
    status_envio character varying(30) DEFAULT 'Enviado'::character varying,
    qtd_pp integer DEFAULT 0,
    qtd_p integer DEFAULT 0,
    qtd_m integer DEFAULT 0,
    qtd_g integer DEFAULT 0,
    qtd_gg integer DEFAULT 0,
    qtd_g1 integer DEFAULT 0,
    qtd_g2 integer DEFAULT 0,
    qtd_g3 integer DEFAULT 0,
    copias_pp integer DEFAULT 0,
    copias_p integer DEFAULT 0,
    copias_m integer DEFAULT 0,
    copias_g integer DEFAULT 0,
    copias_gg integer DEFAULT 0,
    copias_g1 integer DEFAULT 0,
    copias_g2 integer DEFAULT 0,
    copias_g3 integer DEFAULT 0,
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
    total_pecas integer DEFAULT 0,
    total_pilotos integer DEFAULT 0,
    valor_total_envio numeric(12,2) DEFAULT 0,
    resumo_pilotos text,
    copias_do_corte text,
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
    usuario_id integer,
    acao text,
    pagina text,
    detalhe text,
    detalhes text,
    data_hora timestamp without time zone DEFAULT now()
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
-- Name: vw_usuario_logs; Type: VIEW; Schema: opera; Owner: postgres
--

CREATE VIEW opera.vw_usuario_logs AS
 SELECT ul.id,
    ul.data_hora,
    u.usuario,
    ul.acao,
    ul.pagina,
    ul.detalhe,
    ul.detalhes AS observacoes
   FROM (opera.usuario_logs ul
     LEFT JOIN opera.usuarios u ON ((ul.usuario_id = u.id)));


ALTER VIEW opera.vw_usuario_logs OWNER TO postgres;

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
1	opera	1.0	2026-01-30 19:11:59.254529	2026-01-30 19:11:59.254529
2	opera	1.0	2026-01-30 19:12:01.822602	2026-01-30 19:12:01.822602
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
1	OC0001	\N	1313	vestido alfaiataria longo	\N	2026-01-30	\N	7.350	1.480	SILVIO	LEANDRO	\N	23	169.050	24.000		1500	1500	1500	1500	1500	1500	1500	1500	12000	0.0100	erggdsfgsdfgsdfgsdfgsdfgsdf sdfg sedfg sdfg sdfg s	2026-01-30 19:58:50.791021	2026-01-30 19:58:50.791021
\.


--
-- Data for Name: cadastro_de_corte_lotes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_de_corte_lotes (id, cadastro_id, lote, tecido, cor, composicao, bobinas, folhas, pp, p, m, g, gg, g1, g2, g3, total_lote) FROM stdin;
1	1	LOTE 1	ALFAIATARIA	AZUL	98% ALGOD 2%ELASTA	6.000	6.000	500	500	500	500	500	500	500	500	4000
2	1	LOTE 2	ALFAIATARIA	VERMELHO	98% ALGOD 2%ELASTA	18.000	17.000	1000	1000	1000	1000	1000	1000	1000	1000	8000
\.


--
-- Data for Name: cadastro_de_corte_tecidos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_de_corte_tecidos (id, cadastro_id, tecido, cor, composicao, bobinas, folhas, pp, p, m, g, gg, g1, g2, g3, total_pecas) FROM stdin;
1	1	ALFAIATARIA	AZUL	98% ALGOD 2%ELASTA	6.000	6.000	500	500	500	500	500	500	500	500	4000
2	1	ALFAIATARIA	VERMELHO	98% ALGOD 2%ELASTA	3.000	8.000	500	500	500	500	500	500	500	500	4000
3	1	ALFAIATARIA	VERMELHO	98% ALGOD 2%ELASTA	15.000	9.000	500	500	500	500	500	500	500	500	4000
\.


--
-- Data for Name: cadastro_faccoes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_faccoes (id, codigo, nome, tipo_prestador, telefone, endereco, titular_da_conta, cpf, banco, agencia, conta, pix, data, data_atualizacao, ativo) FROM stdin;
1	001	AMANDA CARLA NUNES	Faccao	62985455669	RUA AFONÇO DE BRITO N102 QD 56 MARIA ELISW	AMANDA	65544875855	CAIXA ECONOMICA	25544458	245566-455	6554487585565544875855	2026-01-30	2026-01-30 19:49:46.347434	t
2	002	ANTONIA	Faccao	254564564655656666	``54654654654654654564	SDFGSDFGSDFG	465463546356465	BANCO INTER	242354324132143	32132132132123	3214534565456	2026-01-30	2026-01-30 19:51:05.758466	t
3	003	HJJLHFKJ	Tingimento	MJHGJKGJKH	JHFGLJLHJGL	JJHGFHFHGhgfkhfhk	jkyfljhfgjhkjfhj	hgfkhfkhjfgkjhf	jhgfljhfljfljfhg	jhgljgljgjh	jfgjlggljg	2026-01-30	2026-01-30 20:43:35.939872	t
\.


--
-- Data for Name: cadastro_modelos_aviamentos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_aviamentos (id, codigo_modelo, cadastro_id, codigo_aviamento, descricao, cor, fornecedor, quantidade, valor_unidade, valor_total, created_at) FROM stdin;
2	1313	2	111A	ARGOLA METAL	DOURADO	JANAINA	2.0000	1.65	3.30	2026-01-30 19:54:39.864827
\.


--
-- Data for Name: cadastro_modelos_cabecalho; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_cabecalho (id, codigo, descricao, colecao, tamanho_base, dificuldade, modelista, pilotista, custo_total, gasto_por_peca, gasto_total_por_peca, pronto_producao, grade_disponivel, data_criacao, data_atualizacao, created_at, updated_at) FROM stdin;
1	1212	vestido alfaiataria longo	janeira	M	Médio	GIL	LUCIANA	0.00		0.0000	t	PP,P,M,G,GG,G1,G2,G3	2026-01-30 19:13:26.963216	2026-01-30 19:51:41.776269	2026-01-30 19:13:26.963216	2026-01-30 19:13:26.963216
2	1313	vestido alfaiataria longo	janeira	M	Médio	GIL	LUCIANA	39.60	(T1 - 1,65)	0.0000	t	PP,P,M,G,GG,G1,G2,G3	2026-01-30 19:53:07.204751	2026-01-30 19:54:39.864827	2026-01-30 19:53:07.204751	2026-01-30 19:53:07.204751
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
3	1212	1	frente	BANCO_DE_DADOS/IMAGENS_FRENTE_COSTAS/1212_frente.png	Imagem frente do modelo	2026-01-30 19:51:41.776269
4	1212	1	costas	BANCO_DE_DADOS/IMAGENS_FRENTE_COSTAS/1212_costas.png	Imagem costas do modelo	2026-01-30 19:51:41.776269
5	1212	1	tecido_0	BANCO_DE_DADOS/IMAGENS_TECIDOS/1212_tecido_3.png	Imagem tecido 0	2026-01-30 19:51:41.776269
6	1212	1	tecido_1	BANCO_DE_DADOS/IMAGENS_TECIDOS/1212_tecido_2.png	Imagem tecido 1	2026-01-30 19:51:41.776269
7	1212	1	tecido_2	BANCO_DE_DADOS/IMAGENS_TECIDOS/1212_tecido_0.png	Imagem tecido 2	2026-01-30 19:51:41.776269
8	1212	1	tecido_3	BANCO_DE_DADOS/IMAGENS_TECIDOS/1212_tecido_1.png	Imagem tecido 3	2026-01-30 19:51:41.776269
11	1313	2	frente	/Users/gilleydeoliveiraguimaraes/Downloads/1768441044759.png	Imagem frente do modelo	2026-01-30 19:54:39.864827
12	1313	2	costas	/Users/gilleydeoliveiraguimaraes/Downloads/1768578851687.png	Imagem costas do modelo	2026-01-30 19:54:39.864827
13	1313	2	tecido_0	/Users/gilleydeoliveiraguimaraes/Downloads/1768578783177.png	Imagem tecido 0	2026-01-30 19:54:39.864827
14	1313	2	aviamento_0	/Users/gilleydeoliveiraguimaraes/Downloads/1768441031143.png	Imagem aviamento 0	2026-01-30 19:54:39.864827
\.


--
-- Data for Name: cadastro_modelos_outros; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_outros (id, codigo_modelo, cadastro_id, codigo, descricao, cor, fornecedor, unidade, quantidade, valor_unidade, valor_total, observacoes, created_at) FROM stdin;
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
2	1313	2	1111	ALFAIATARIA	AZUL	ROBERTO	98% ALGOD 2%ELASTA	1.6500	22.00	36.30	2026-01-30 19:54:39.864827
\.


--
-- Data for Name: controle_envio_cortes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.controle_envio_cortes (id, data_envio, servico, corte_id, ordem_corte, codigo_corte, descricao_corte, destino, costureira, faccao, quantidade_total, valor_peca, valor_total, status, observacao, pp, p, m, g, gg, g1, g2, g3) FROM stdin;
\.


--
-- Data for Name: controle_retorno_cortes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.controle_retorno_cortes (id, envio_id, data_chegada, telefone_encarregado, telefone_acabamento, resumo_piloto, aviamentos_recebidos, outros_recebidos, observacoes_gerais, total_entregue, total_copias, total_defeitos, total_faltantes, total_regulares, valor_total, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: cortes_finalizados; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cortes_finalizados (id, corte_id, entrada_id, envio_id, retorno_id, tipo_servico, codigo, descricao, costureira, data_envio, data_chegada, data_final, qtd_enviada, total_pecas, quantidade_finalizada, observacao, status, data_conferencia, valor_peca, bonificacao, pago, data_pagamento, qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3, qtd_defeito_pp, qtd_defeito_p, qtd_defeito_m, qtd_defeito_g, qtd_defeito_gg, qtd_defeito_g1, qtd_defeito_g2, qtd_defeito_g3, valor_total, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: cortes_finalizados_completo; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cortes_finalizados_completo (id, entrada_id, envio_id, corte_id, descricao, ordem_corte, codigo_corte, qtd_regular_pp, qtd_regular_p, qtd_regular_m, qtd_regular_g, qtd_regular_gg, qtd_regular_g1, qtd_regular_g2, qtd_regular_g3, status, observacoes, usuario_finalizacao, created_at, updated_at) FROM stdin;
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

COPY opera.envio_detalhes_tamanho (envio_id, tamanho, quantidade, copias_do_corte, quantidade_pilotos, valor_peca) FROM stdin;
\.


--
-- Data for Name: envios_cortes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.envios_cortes (id, remessa_id, data_envio, hora_envio, prestador_id, tipo_servico, corte_id, ordem_corte, codigo_corte, descricao_corte, colecao, material, cliente, cores, prioridade, forma_pagamento, status_envio, qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3, copias_pp, copias_p, copias_m, copias_g, copias_gg, copias_g1, copias_g2, copias_g3, piloto_pp, piloto_p, piloto_m, piloto_g, piloto_gg, piloto_g1, piloto_g2, piloto_g3, valor_pp, valor_p, valor_m, valor_g, valor_gg, valor_g1, valor_g2, valor_g3, total_pecas, total_pilotos, valor_total_envio, resumo_pilotos, copias_do_corte, aviamentos, outros, observacoes, tel_encarregado, tel_acabamento, previsao_entrega, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: estoque_aviamentos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_aviamentos (id, codigo, descricao, cor, fornecedor, quantidade, unidade, valor_unidade, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
1	111A	ARGOLA METAL	DOURADO	JANAINA	200.000	unidades	0.00	FOLIADA	\N	2026-01-30	2026-01-30 19:16:13.031741	2026-01-30 19:16:13.031741
2	111F	FIVELA DE METAL	DOURADO	FABIO	200.000	unidades	0.00	POLIDA	\N	2026-01-30	2026-01-30 19:16:46.927087	2026-01-30 19:16:46.927087
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
1	1111	ALFAIATARIA	PRETO	98% ALGOD 2%ELASTA	ROBERTO	10000.000	0.000	0.00	0.00	metros	PREMIO	\N	2026-01-30	2026-01-30 19:14:57.411516	2026-01-30 19:14:57.411516
4	1111	ALFAIATARIA	VERDE	98% ALGOD 2%ELASTA	ROBERTO	10000.000	0.000	0.00	0.00	metros	PREMIO	\N	2026-01-30	2026-01-30 19:15:32.191616	2026-01-30 19:15:32.191616
3	1111	ALFAIATARIA	AZUL	98% ALGOD 2%ELASTA	ROBERTO	9955.900	0.000	0.00	0.00	metros	PREMIO	\N	2026-01-30	2026-01-30 19:15:22.342591	2026-01-30 19:15:22.342591
2	1111	ALFAIATARIA	VERMELHO	98% ALGOD 2%ELASTA	ROBERTO	9875.050	0.000	0.00	0.00	metros	PREMIO	\N	2026-01-30	2026-01-30 19:15:08.911036	2026-01-30 19:15:08.911036
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
1	1313	vestido alfaiataria longo	SILVIO	LEANDRO	\N	2026-01-30 19:56:35.157154	2026-01-30	0.0417	1.0000	{"porcent_1": 50.0, "porcent_2": 50.0, "porcent_3": 100.0, "porcent_4": 100.0, "porcent_5": 100.0, "porcent_6": 50.0, "porcent_7": 25.0, "porcent_8": 25.0}	\N	\N	\N	\N	Em Andamento	\N	2026-01-30 19:56:35.157154	t
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
1	1	srghsdfghsdf	50.0000	50.0000	100.0000	100.0000	100.0000	50.0000	25.0000	25.0000	2026-01-30 19:56:24.549547	2026-01-30 19:56:24.549547
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

COPY opera.usuario_logs (id, usuario_id, acao, pagina, detalhe, detalhes, data_hora) FROM stdin;
\.


--
-- Data for Name: usuario_permissoes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuario_permissoes (usuario_id, codigo, pode_ver, pode_editar, pode_imprimir, pode_excluir, pode_administrar) FROM stdin;
1	dashboard	t	t	t	t	t
1	cadastro_modelos	t	t	t	t	t
1	cadastro_de_corte	t	t	t	t	t
1	controle_envio_cortes	t	t	t	t	t
1	controle_retorno_cortes	t	t	t	t	t
1	finalizar_corte	t	t	t	t	t
1	estoque_tecidos	t	t	t	t	t
1	estoque_aviamentos	t	t	t	t	t
1	estoque_insumos	t	t	t	t	t
1	sistema_admin	t	t	t	t	t
1	sistema_logs	t	t	t	t	t
1	sistema_backup	t	t	t	t	t
1	sistema_auditoria	t	t	t	t	t
\.


--
-- Data for Name: usuario_preferencias; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuario_preferencias (usuario_id, tema_nome, usar_tema_personalizado, tema_personalizado, layout_compacto, sidebar_recolhida, usar_animacoes, mostrar_dicas, idioma, notificacoes, atualizado_em) FROM stdin;
1	CLÁSSICO ESCURO	f	\N	f	f	t	t	pt-BR	t	2026-01-30 19:12:01.78899
\.


--
-- Data for Name: usuario_temas_personalizados; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuario_temas_personalizados (id, usuario_id, nome_tema, cores_tema, data_criacao, atualizado_em) FROM stdin;
1	1	AZUL_NOTURNO	{"borda": "#334155", "fundo": "#0F172A", "hover": "#1E293B", "texto": "#F1F5F9", "alerta": "#F59E0B", "selecao": "#3B82F6", "sucesso": "#10B981", "destaque": "#6366F1", "primaria": "#1E3A8A", "botao_pdf": "#EF4444", "terciaria": "#60A5FA", "botao_novo": "#8B5CF6", "secundaria": "#3B82F6", "botao_ajuda": "#06B6D4", "botao_buscar": "#3B82F6", "botao_editar": "#06B6D4", "botao_limpar": "#F59E0B", "botao_salvar": "#10B981", "botao_voltar": "#6B7280", "botao_avancar": "#3B82F6", "botao_excluir": "#EF4444", "botao_filtrar": "#8B5CF6", "botao_cancelar": "#6B7280", "botao_exportar": "#10B981", "botao_importar": "#3B82F6", "botao_imprimir": "#F59E0B", "botao_confirmar": "#22C55E", "botao_configurar": "#6B7280", "botao_export_csv": "#3B82F6", "botao_export_pdf": "#F59E0B", "botao_visualizar": "#6366F1", "botao_comprovante": "#8B5CF6", "botao_adiantamento": "#10B981"}	2026-01-30 19:12:01.78899	2026-01-30 19:12:01.78899
\.


--
-- Data for Name: usuarios; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuarios (id, usuario, senha_hash, hierarquia, email, data_criacao, ativo, dica_senha, ultimo_login, telefone, departamento, tema_preferido) FROM stdin;
1	Gil de Oliveira	$2a$06$ao4NgQlOSXITaQa7tO0gHeCQFqTcmVuD5/SF2SDmJaW9RIH47tsji	Administrador	opera@gil.com	2026-01-30 19:12:01.78899	t	25	2026-01-30 21:09:00.308346	\N	\N	AZUL_NOTURNO
\.


--
-- Name: _schema_info_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera._schema_info_id_seq', 2, true);


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

SELECT pg_catalog.setval('opera.cadastro_de_corte_tecidos_id_seq', 3, true);


--
-- Name: cadastro_faccoes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_faccoes_id_seq', 3, true);


--
-- Name: cadastro_modelos_aviamentos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_aviamentos_id_seq', 2, true);


--
-- Name: cadastro_modelos_cabecalho_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_cabecalho_id_seq', 2, true);


--
-- Name: cadastro_modelos_grade_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_grade_id_seq', 1, false);


--
-- Name: cadastro_modelos_imagens_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_imagens_id_seq', 14, true);


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

SELECT pg_catalog.setval('opera.cadastro_modelos_tecidos_id_seq', 2, true);


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

SELECT pg_catalog.setval('opera.estoque_aviamentos_id_seq', 2, true);


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

SELECT pg_catalog.setval('opera.estoque_tecidos_id_seq', 4, true);


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

SELECT pg_catalog.setval('opera.ordem_grade_preferencias_id_seq', 1, true);


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

SELECT pg_catalog.setval('opera.usuario_logs_id_seq', 1, false);


--
-- Name: usuario_temas_personalizados_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.usuario_temas_personalizados_id_seq', 1, true);


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
-- Name: idx_envios_cortes_data; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envios_cortes_data ON opera.envios_cortes USING btree (data_envio);


--
-- Name: idx_envios_cortes_status; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envios_cortes_status ON opera.envios_cortes USING btree (status_envio);


--
-- Name: idx_estoque_aviamentos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_aviamentos_codigo ON opera.estoque_aviamentos USING btree (codigo);


--
-- Name: idx_estoque_aviamentos_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_aviamentos_cor ON opera.estoque_aviamentos USING btree (cor);


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
-- Name: idx_modelos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_codigo ON opera.cadastro_modelos_cabecalho USING btree (codigo);


--
-- Name: idx_modelos_descricao; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_descricao ON opera.cadastro_modelos_cabecalho USING btree (descricao);


--
-- Name: idx_usuario_logs_data_hora; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_logs_data_hora ON opera.usuario_logs USING btree (data_hora);


--
-- Name: idx_usuario_logs_usuario; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_logs_usuario ON opera.usuario_logs USING btree (usuario_id);


--
-- Name: idx_usuarios_ativo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuarios_ativo ON opera.usuarios USING btree (ativo);


--
-- Name: idx_usuarios_hierarquia; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuarios_hierarquia ON opera.usuarios USING btree (hierarquia);


--
-- Name: usuario_temas_personalizados tr_validar_cores_tema; Type: TRIGGER; Schema: opera; Owner: postgres
--

CREATE TRIGGER tr_validar_cores_tema BEFORE INSERT OR UPDATE ON opera.usuario_temas_personalizados FOR EACH ROW EXECUTE FUNCTION opera.validar_cores_tema();


--
-- Name: adiantamento_faccao adiantamento_faccao_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.adiantamento_faccao
    ADD CONSTRAINT adiantamento_faccao_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.cadastro_de_corte(id);


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
-- Name: controle_retorno_cortes controle_retorno_cortes_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_retorno_cortes
    ADD CONSTRAINT controle_retorno_cortes_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.envios_cortes(id) ON DELETE CASCADE;


--
-- Name: cortes_finalizados_completo cortes_finalizados_completo_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo
    ADD CONSTRAINT cortes_finalizados_completo_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL;


--
-- Name: cortes_finalizados_completo cortes_finalizados_completo_entrada_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo
    ADD CONSTRAINT cortes_finalizados_completo_entrada_id_fkey FOREIGN KEY (entrada_id) REFERENCES opera.entrada_acabamento(id) ON DELETE SET NULL;


--
-- Name: cortes_finalizados_completo cortes_finalizados_completo_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo
    ADD CONSTRAINT cortes_finalizados_completo_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.controle_envio_cortes(id) ON DELETE SET NULL;


--
-- Name: cortes_finalizados cortes_finalizados_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados
    ADD CONSTRAINT cortes_finalizados_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.cadastro_de_corte(id);


--
-- Name: cortes_finalizados cortes_finalizados_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados
    ADD CONSTRAINT cortes_finalizados_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.envios_cortes(id) ON DELETE SET NULL;


--
-- Name: cortes_finalizados cortes_finalizados_retorno_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados
    ADD CONSTRAINT cortes_finalizados_retorno_id_fkey FOREIGN KEY (retorno_id) REFERENCES opera.controle_retorno_cortes(id) ON DELETE SET NULL;


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
    ADD CONSTRAINT envio_detalhes_tamanho_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.envios_cortes(id) ON DELETE CASCADE;


--
-- Name: envios_cortes envios_cortes_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envios_cortes
    ADD CONSTRAINT envios_cortes_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.cadastro_de_corte(id);


--
-- Name: envios_cortes envios_cortes_prestador_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envios_cortes
    ADD CONSTRAINT envios_cortes_prestador_id_fkey FOREIGN KEY (prestador_id) REFERENCES opera.cadastro_faccoes(id);


--
-- Name: cortes_finalizados fk_cortes_finalizados_envio; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados
    ADD CONSTRAINT fk_cortes_finalizados_envio FOREIGN KEY (envio_id) REFERENCES opera.envios_cortes(id) ON DELETE SET NULL;


--
-- Name: cortes_finalizados fk_cortes_finalizados_retorno; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados
    ADD CONSTRAINT fk_cortes_finalizados_retorno FOREIGN KEY (retorno_id) REFERENCES opera.controle_retorno_cortes(id) ON DELETE SET NULL;


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
-- Name: usuario_logs usuario_logs_usuario_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_logs
    ADD CONSTRAINT usuario_logs_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES opera.usuarios(id);


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
-- Name: FUNCTION registrar_log_usuario(p_usuario character varying, p_acao text, p_pagina text, p_detalhe text); Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON FUNCTION opera.registrar_log_usuario(p_usuario character varying, p_acao text, p_pagina text, p_detalhe text) TO opera_app;


--
-- Name: FUNCTION validar_cores_tema(); Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON FUNCTION opera.validar_cores_tema() TO opera_app;


--
-- Name: FUNCTION validar_senha(p_usuario text, p_senha text); Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON FUNCTION opera.validar_senha(p_usuario text, p_senha text) TO opera_app;


--
-- Name: TABLE _schema_info; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera._schema_info TO opera_app;


--
-- Name: SEQUENCE _schema_info_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera._schema_info_id_seq TO opera_app;


--
-- Name: TABLE adiantamento_faccao; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.adiantamento_faccao TO opera_app;


--
-- Name: SEQUENCE adiantamento_faccao_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.adiantamento_faccao_id_seq TO opera_app;


--
-- Name: TABLE cadastro_de_corte; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cadastro_de_corte TO opera_app;


--
-- Name: SEQUENCE cadastro_de_corte_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cadastro_de_corte_id_seq TO opera_app;


--
-- Name: TABLE cadastro_de_corte_lotes; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cadastro_de_corte_lotes TO opera_app;


--
-- Name: SEQUENCE cadastro_de_corte_lotes_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cadastro_de_corte_lotes_id_seq TO opera_app;


--
-- Name: TABLE cadastro_de_corte_tecidos; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cadastro_de_corte_tecidos TO opera_app;


--
-- Name: SEQUENCE cadastro_de_corte_tecidos_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cadastro_de_corte_tecidos_id_seq TO opera_app;


--
-- Name: TABLE cadastro_faccoes; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cadastro_faccoes TO opera_app;


--
-- Name: SEQUENCE cadastro_faccoes_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cadastro_faccoes_id_seq TO opera_app;


--
-- Name: TABLE cadastro_modelos_aviamentos; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cadastro_modelos_aviamentos TO opera_app;


--
-- Name: SEQUENCE cadastro_modelos_aviamentos_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cadastro_modelos_aviamentos_id_seq TO opera_app;


--
-- Name: TABLE cadastro_modelos_cabecalho; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cadastro_modelos_cabecalho TO opera_app;


--
-- Name: SEQUENCE cadastro_modelos_cabecalho_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cadastro_modelos_cabecalho_id_seq TO opera_app;


--
-- Name: TABLE cadastro_modelos_grade; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cadastro_modelos_grade TO opera_app;


--
-- Name: SEQUENCE cadastro_modelos_grade_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cadastro_modelos_grade_id_seq TO opera_app;


--
-- Name: TABLE cadastro_modelos_imagens; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cadastro_modelos_imagens TO opera_app;


--
-- Name: SEQUENCE cadastro_modelos_imagens_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cadastro_modelos_imagens_id_seq TO opera_app;


--
-- Name: TABLE cadastro_modelos_outros; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cadastro_modelos_outros TO opera_app;


--
-- Name: SEQUENCE cadastro_modelos_outros_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cadastro_modelos_outros_id_seq TO opera_app;


--
-- Name: TABLE cadastro_modelos_outros_servicos; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cadastro_modelos_outros_servicos TO opera_app;


--
-- Name: SEQUENCE cadastro_modelos_outros_servicos_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cadastro_modelos_outros_servicos_id_seq TO opera_app;


--
-- Name: TABLE cadastro_modelos_tecidos; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cadastro_modelos_tecidos TO opera_app;


--
-- Name: SEQUENCE cadastro_modelos_tecidos_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cadastro_modelos_tecidos_id_seq TO opera_app;


--
-- Name: TABLE controle_envio_cortes; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.controle_envio_cortes TO opera_app;


--
-- Name: SEQUENCE controle_envio_cortes_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.controle_envio_cortes_id_seq TO opera_app;


--
-- Name: TABLE controle_retorno_cortes; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.controle_retorno_cortes TO opera_app;


--
-- Name: SEQUENCE controle_retorno_cortes_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.controle_retorno_cortes_id_seq TO opera_app;


--
-- Name: TABLE cortes_finalizados; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cortes_finalizados TO opera_app;


--
-- Name: TABLE cortes_finalizados_completo; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.cortes_finalizados_completo TO opera_app;


--
-- Name: SEQUENCE cortes_finalizados_completo_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cortes_finalizados_completo_id_seq TO opera_app;


--
-- Name: SEQUENCE cortes_finalizados_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.cortes_finalizados_id_seq TO opera_app;


--
-- Name: TABLE entrada_acabamento; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.entrada_acabamento TO opera_app;


--
-- Name: TABLE entrada_acabamento_detalhes; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.entrada_acabamento_detalhes TO opera_app;


--
-- Name: SEQUENCE entrada_acabamento_detalhes_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.entrada_acabamento_detalhes_id_seq TO opera_app;


--
-- Name: SEQUENCE entrada_acabamento_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.entrada_acabamento_id_seq TO opera_app;


--
-- Name: TABLE envio_detalhes_tamanho; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.envio_detalhes_tamanho TO opera_app;


--
-- Name: TABLE envios_cortes; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.envios_cortes TO opera_app;


--
-- Name: SEQUENCE envios_cortes_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.envios_cortes_id_seq TO opera_app;


--
-- Name: TABLE estoque_aviamentos; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.estoque_aviamentos TO opera_app;


--
-- Name: SEQUENCE estoque_aviamentos_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.estoque_aviamentos_id_seq TO opera_app;


--
-- Name: TABLE estoque_escritorio; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.estoque_escritorio TO opera_app;


--
-- Name: SEQUENCE estoque_escritorio_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.estoque_escritorio_id_seq TO opera_app;


--
-- Name: TABLE estoque_insumos; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.estoque_insumos TO opera_app;


--
-- Name: SEQUENCE estoque_insumos_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.estoque_insumos_id_seq TO opera_app;


--
-- Name: TABLE estoque_limpeza; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.estoque_limpeza TO opera_app;


--
-- Name: SEQUENCE estoque_limpeza_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.estoque_limpeza_id_seq TO opera_app;


--
-- Name: TABLE estoque_outros; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.estoque_outros TO opera_app;


--
-- Name: SEQUENCE estoque_outros_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.estoque_outros_id_seq TO opera_app;


--
-- Name: TABLE estoque_saida_log; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.estoque_saida_log TO opera_app;


--
-- Name: SEQUENCE estoque_saida_log_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.estoque_saida_log_id_seq TO opera_app;


--
-- Name: TABLE estoque_tecidos; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.estoque_tecidos TO opera_app;


--
-- Name: SEQUENCE estoque_tecidos_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.estoque_tecidos_id_seq TO opera_app;


--
-- Name: TABLE historico_de_servico; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.historico_de_servico TO opera_app;


--
-- Name: SEQUENCE historico_de_servico_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.historico_de_servico_id_seq TO opera_app;


--
-- Name: TABLE historico_servicos; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.historico_servicos TO opera_app;


--
-- Name: SEQUENCE historico_servicos_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.historico_servicos_id_seq TO opera_app;


--
-- Name: TABLE log_finalizacoes; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.log_finalizacoes TO opera_app;


--
-- Name: SEQUENCE log_finalizacoes_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.log_finalizacoes_id_seq TO opera_app;


--
-- Name: TABLE ordem_corte_ficha; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.ordem_corte_ficha TO opera_app;


--
-- Name: SEQUENCE ordem_corte_ficha_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.ordem_corte_ficha_id_seq TO opera_app;


--
-- Name: TABLE ordem_corte_lotes; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.ordem_corte_lotes TO opera_app;


--
-- Name: SEQUENCE ordem_corte_lotes_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.ordem_corte_lotes_id_seq TO opera_app;


--
-- Name: TABLE ordem_grade_preferencias; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.ordem_grade_preferencias TO opera_app;


--
-- Name: SEQUENCE ordem_grade_preferencias_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.ordem_grade_preferencias_id_seq TO opera_app;


--
-- Name: TABLE pagamento_corte_acabamento; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.pagamento_corte_acabamento TO opera_app;


--
-- Name: SEQUENCE pagamento_corte_acabamento_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.pagamento_corte_acabamento_id_seq TO opera_app;


--
-- Name: TABLE pagamento_servicos; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.pagamento_servicos TO opera_app;


--
-- Name: TABLE pagamento_servicos_detalhe; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.pagamento_servicos_detalhe TO opera_app;


--
-- Name: SEQUENCE pagamento_servicos_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.pagamento_servicos_id_seq TO opera_app;


--
-- Name: TABLE pecas_finalizadas; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.pecas_finalizadas TO opera_app;


--
-- Name: SEQUENCE pecas_finalizadas_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.pecas_finalizadas_id_seq TO opera_app;


--
-- Name: TABLE usuario_permissoes; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.usuario_permissoes TO opera_app;


--
-- Name: TABLE permissoes; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.permissoes TO opera_app;


--
-- Name: TABLE pricing_profiles; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.pricing_profiles TO opera_app;


--
-- Name: TABLE relatorios_finalizacao; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.relatorios_finalizacao TO opera_app;


--
-- Name: SEQUENCE relatorios_finalizacao_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.relatorios_finalizacao_id_seq TO opera_app;


--
-- Name: TABLE retorno_detalhes_tamanho; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.retorno_detalhes_tamanho TO opera_app;


--
-- Name: SEQUENCE retorno_detalhes_tamanho_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.retorno_detalhes_tamanho_id_seq TO opera_app;


--
-- Name: TABLE servicos; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.servicos TO opera_app;


--
-- Name: SEQUENCE servicos_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.servicos_id_seq TO opera_app;


--
-- Name: TABLE usuarios; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.usuarios TO opera_app;


--
-- Name: TABLE usuario; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.usuario TO opera_app;


--
-- Name: TABLE usuario_logs; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.usuario_logs TO opera_app;


--
-- Name: SEQUENCE usuario_logs_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.usuario_logs_id_seq TO opera_app;


--
-- Name: TABLE usuario_preferencias; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.usuario_preferencias TO opera_app;


--
-- Name: TABLE usuario_temas_personalizados; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.usuario_temas_personalizados TO opera_app;


--
-- Name: SEQUENCE usuario_temas_personalizados_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.usuario_temas_personalizados_id_seq TO opera_app;


--
-- Name: SEQUENCE usuarios_id_seq; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON SEQUENCE opera.usuarios_id_seq TO opera_app;


--
-- Name: TABLE vw_usuario_logs; Type: ACL; Schema: opera; Owner: postgres
--

GRANT ALL ON TABLE opera.vw_usuario_logs TO opera_app;


--
-- PostgreSQL database dump complete
--

\unrestrict rx2EQYoKdDYmvsgAnXUIOkJ9HxLyr9gbN4lyCLjXXPi3E0tzn4uJlzCQshg3SMq

