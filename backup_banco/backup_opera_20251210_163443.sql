--
-- PostgreSQL database dump
--

\restrict I3QixhyQALtE6ISqaY10FLpAPLO9NrWzpfSsFVVeTKcXEaBYrPDfGAoWvDzFNjJ

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

-- Started on 2025-12-10 16:34:43

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'WIN1252';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 8 (class 2615 OID 187127)
-- Name: opera; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA opera;


ALTER SCHEMA opera OWNER TO postgres;

--
-- TOC entry 3 (class 3079 OID 187089)
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- TOC entry 5885 (class 0 OID 0)
-- Dependencies: 3
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- TOC entry 2 (class 3079 OID 187078)
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- TOC entry 5886 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- TOC entry 372 (class 1255 OID 188117)
-- Name: registrar_log_usuario(character varying, text, text, text); Type: FUNCTION; Schema: opera; Owner: postgres
--

CREATE FUNCTION opera.registrar_log_usuario(p_usuario character varying, p_acao text, p_pagina text DEFAULT NULL::text, p_detalhe text DEFAULT NULL::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO opera.usuario_logs (usuario, acao, pagina, detalhe)
    VALUES (p_usuario, p_acao, p_pagina, p_detalhe);
END;
$$;


ALTER FUNCTION opera.registrar_log_usuario(p_usuario character varying, p_acao text, p_pagina text, p_detalhe text) OWNER TO postgres;

--
-- TOC entry 370 (class 1255 OID 188115)
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
-- TOC entry 373 (class 1255 OID 188118)
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
$_$;


ALTER FUNCTION opera.validar_senha(p_usuario text, p_senha text) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 223 (class 1259 OID 187129)
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
-- TOC entry 222 (class 1259 OID 187128)
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
-- TOC entry 5887 (class 0 OID 0)
-- Dependencies: 222
-- Name: _schema_info_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera._schema_info_id_seq OWNED BY opera._schema_info.id;


--
-- TOC entry 250 (class 1259 OID 187424)
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
-- TOC entry 249 (class 1259 OID 187423)
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
-- TOC entry 5888 (class 0 OID 0)
-- Dependencies: 249
-- Name: adiantamento_faccao_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.adiantamento_faccao_id_seq OWNED BY opera.adiantamento_faccao.id;


--
-- TOC entry 253 (class 1259 OID 187446)
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
-- TOC entry 252 (class 1259 OID 187445)
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
-- TOC entry 5889 (class 0 OID 0)
-- Dependencies: 252
-- Name: cadastro_de_corte_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_de_corte_id_seq OWNED BY opera.cadastro_de_corte.id;


--
-- TOC entry 257 (class 1259 OID 187495)
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
-- TOC entry 256 (class 1259 OID 187494)
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
-- TOC entry 5890 (class 0 OID 0)
-- Dependencies: 256
-- Name: cadastro_de_corte_lotes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_de_corte_lotes_id_seq OWNED BY opera.cadastro_de_corte_lotes.id;


--
-- TOC entry 255 (class 1259 OID 187480)
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
-- TOC entry 254 (class 1259 OID 187479)
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
-- TOC entry 5891 (class 0 OID 0)
-- Dependencies: 254
-- Name: cadastro_de_corte_tecidos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_de_corte_tecidos_id_seq OWNED BY opera.cadastro_de_corte_tecidos.id;


--
-- TOC entry 245 (class 1259 OID 187370)
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
-- TOC entry 244 (class 1259 OID 187369)
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
-- TOC entry 5892 (class 0 OID 0)
-- Dependencies: 244
-- Name: cadastro_faccoes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_faccoes_id_seq OWNED BY opera.cadastro_faccoes.id;


--
-- TOC entry 237 (class 1259 OID 187289)
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
-- TOC entry 236 (class 1259 OID 187288)
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
-- TOC entry 5893 (class 0 OID 0)
-- Dependencies: 236
-- Name: cadastro_modelos_aviamentos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_aviamentos_id_seq OWNED BY opera.cadastro_modelos_aviamentos.id;


--
-- TOC entry 233 (class 1259 OID 187246)
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
-- TOC entry 232 (class 1259 OID 187245)
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
-- TOC entry 5894 (class 0 OID 0)
-- Dependencies: 232
-- Name: cadastro_modelos_cabecalho_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_cabecalho_id_seq OWNED BY opera.cadastro_modelos_cabecalho.id;


--
-- TOC entry 243 (class 1259 OID 187352)
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
-- TOC entry 242 (class 1259 OID 187351)
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
-- TOC entry 5895 (class 0 OID 0)
-- Dependencies: 242
-- Name: cadastro_modelos_grade_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_grade_id_seq OWNED BY opera.cadastro_modelos_grade.id;


--
-- TOC entry 241 (class 1259 OID 187333)
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
-- TOC entry 240 (class 1259 OID 187332)
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
-- TOC entry 5896 (class 0 OID 0)
-- Dependencies: 240
-- Name: cadastro_modelos_imagens_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_imagens_id_seq OWNED BY opera.cadastro_modelos_imagens.id;


--
-- TOC entry 239 (class 1259 OID 187311)
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
-- TOC entry 238 (class 1259 OID 187310)
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
-- TOC entry 5897 (class 0 OID 0)
-- Dependencies: 238
-- Name: cadastro_modelos_outros_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_outros_id_seq OWNED BY opera.cadastro_modelos_outros.id;


--
-- TOC entry 312 (class 1259 OID 188121)
-- Name: cadastro_modelos_outros_servicos; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.cadastro_modelos_outros_servicos (
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


ALTER TABLE opera.cadastro_modelos_outros_servicos OWNER TO postgres;

--
-- TOC entry 311 (class 1259 OID 188120)
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
-- TOC entry 5898 (class 0 OID 0)
-- Dependencies: 311
-- Name: cadastro_modelos_outros_servicos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_outros_servicos_id_seq OWNED BY opera.cadastro_modelos_outros_servicos.id;


--
-- TOC entry 235 (class 1259 OID 187267)
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
-- TOC entry 234 (class 1259 OID 187266)
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
-- TOC entry 5899 (class 0 OID 0)
-- Dependencies: 234
-- Name: cadastro_modelos_tecidos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cadastro_modelos_tecidos_id_seq OWNED BY opera.cadastro_modelos_tecidos.id;


--
-- TOC entry 265 (class 1259 OID 187600)
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
-- TOC entry 264 (class 1259 OID 187599)
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
-- TOC entry 5900 (class 0 OID 0)
-- Dependencies: 264
-- Name: controle_envio_cortes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.controle_envio_cortes_id_seq OWNED BY opera.controle_envio_cortes.id;


--
-- TOC entry 271 (class 1259 OID 187659)
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
-- TOC entry 270 (class 1259 OID 187658)
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
-- TOC entry 5901 (class 0 OID 0)
-- Dependencies: 270
-- Name: controle_retorno_cortes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.controle_retorno_cortes_id_seq OWNED BY opera.controle_retorno_cortes.id;


--
-- TOC entry 273 (class 1259 OID 187686)
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
-- TOC entry 280 (class 1259 OID 187779)
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
-- TOC entry 279 (class 1259 OID 187778)
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
-- TOC entry 5902 (class 0 OID 0)
-- Dependencies: 279
-- Name: cortes_finalizados_completo_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cortes_finalizados_completo_id_seq OWNED BY opera.cortes_finalizados_completo.id;


--
-- TOC entry 272 (class 1259 OID 187685)
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
-- TOC entry 5903 (class 0 OID 0)
-- Dependencies: 272
-- Name: cortes_finalizados_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.cortes_finalizados_id_seq OWNED BY opera.cortes_finalizados.id;


--
-- TOC entry 267 (class 1259 OID 187618)
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
-- TOC entry 282 (class 1259 OID 187816)
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
-- TOC entry 281 (class 1259 OID 187815)
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
-- TOC entry 5904 (class 0 OID 0)
-- Dependencies: 281
-- Name: entrada_acabamento_detalhes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.entrada_acabamento_detalhes_id_seq OWNED BY opera.entrada_acabamento_detalhes.id;


--
-- TOC entry 266 (class 1259 OID 187617)
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
-- TOC entry 5905 (class 0 OID 0)
-- Dependencies: 266
-- Name: entrada_acabamento_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.entrada_acabamento_id_seq OWNED BY opera.entrada_acabamento.id;


--
-- TOC entry 276 (class 1259 OID 187738)
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
-- TOC entry 263 (class 1259 OID 187546)
-- Name: envios_cortes; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.envios_cortes (
    id integer NOT NULL,
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
-- TOC entry 262 (class 1259 OID 187545)
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
-- TOC entry 5906 (class 0 OID 0)
-- Dependencies: 262
-- Name: envios_cortes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.envios_cortes_id_seq OWNED BY opera.envios_cortes.id;


--
-- TOC entry 290 (class 1259 OID 187904)
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
-- TOC entry 289 (class 1259 OID 187903)
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
-- TOC entry 5907 (class 0 OID 0)
-- Dependencies: 289
-- Name: estoque_aviamentos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_aviamentos_id_seq OWNED BY opera.estoque_aviamentos.id;


--
-- TOC entry 294 (class 1259 OID 187948)
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
-- TOC entry 293 (class 1259 OID 187947)
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
-- TOC entry 5908 (class 0 OID 0)
-- Dependencies: 293
-- Name: estoque_escritorio_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_escritorio_id_seq OWNED BY opera.estoque_escritorio.id;


--
-- TOC entry 292 (class 1259 OID 187926)
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
-- TOC entry 291 (class 1259 OID 187925)
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
-- TOC entry 5909 (class 0 OID 0)
-- Dependencies: 291
-- Name: estoque_insumos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_insumos_id_seq OWNED BY opera.estoque_insumos.id;


--
-- TOC entry 296 (class 1259 OID 187970)
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
-- TOC entry 295 (class 1259 OID 187969)
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
-- TOC entry 5910 (class 0 OID 0)
-- Dependencies: 295
-- Name: estoque_limpeza_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_limpeza_id_seq OWNED BY opera.estoque_limpeza.id;


--
-- TOC entry 298 (class 1259 OID 187992)
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
-- TOC entry 297 (class 1259 OID 187991)
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
-- TOC entry 5911 (class 0 OID 0)
-- Dependencies: 297
-- Name: estoque_outros_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_outros_id_seq OWNED BY opera.estoque_outros.id;


--
-- TOC entry 300 (class 1259 OID 188014)
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
-- TOC entry 299 (class 1259 OID 188013)
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
-- TOC entry 5912 (class 0 OID 0)
-- Dependencies: 299
-- Name: estoque_saida_log_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_saida_log_id_seq OWNED BY opera.estoque_saida_log.id;


--
-- TOC entry 288 (class 1259 OID 187880)
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
-- TOC entry 287 (class 1259 OID 187879)
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
-- TOC entry 5913 (class 0 OID 0)
-- Dependencies: 287
-- Name: estoque_tecidos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.estoque_tecidos_id_seq OWNED BY opera.estoque_tecidos.id;


--
-- TOC entry 269 (class 1259 OID 187633)
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
-- TOC entry 268 (class 1259 OID 187632)
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
-- TOC entry 5914 (class 0 OID 0)
-- Dependencies: 268
-- Name: historico_de_servico_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.historico_de_servico_id_seq OWNED BY opera.historico_de_servico.id;


--
-- TOC entry 304 (class 1259 OID 188043)
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
-- TOC entry 303 (class 1259 OID 188042)
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
-- TOC entry 5915 (class 0 OID 0)
-- Dependencies: 303
-- Name: historico_servicos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.historico_servicos_id_seq OWNED BY opera.historico_servicos.id;


--
-- TOC entry 284 (class 1259 OID 187843)
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
-- TOC entry 283 (class 1259 OID 187842)
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
-- TOC entry 5916 (class 0 OID 0)
-- Dependencies: 283
-- Name: log_finalizacoes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.log_finalizacoes_id_seq OWNED BY opera.log_finalizacoes.id;


--
-- TOC entry 259 (class 1259 OID 187510)
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
-- TOC entry 258 (class 1259 OID 187509)
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
-- TOC entry 5917 (class 0 OID 0)
-- Dependencies: 258
-- Name: ordem_corte_ficha_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.ordem_corte_ficha_id_seq OWNED BY opera.ordem_corte_ficha.id;


--
-- TOC entry 261 (class 1259 OID 187527)
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
-- TOC entry 260 (class 1259 OID 187526)
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
-- TOC entry 5918 (class 0 OID 0)
-- Dependencies: 260
-- Name: ordem_corte_lotes_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.ordem_corte_lotes_id_seq OWNED BY opera.ordem_corte_lotes.id;


--
-- TOC entry 308 (class 1259 OID 188079)
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
-- TOC entry 5919 (class 0 OID 0)
-- Dependencies: 308
-- Name: TABLE ordem_grade_preferencias; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON TABLE opera.ordem_grade_preferencias IS 'TABELA 45 - ORDEM DE CORTE: Preferências de grade por usuário.';


--
-- TOC entry 307 (class 1259 OID 188078)
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
-- TOC entry 5920 (class 0 OID 0)
-- Dependencies: 307
-- Name: ordem_grade_preferencias_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.ordem_grade_preferencias_id_seq OWNED BY opera.ordem_grade_preferencias.id;


--
-- TOC entry 275 (class 1259 OID 187717)
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
-- TOC entry 274 (class 1259 OID 187716)
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
-- TOC entry 5921 (class 0 OID 0)
-- Dependencies: 274
-- Name: pagamento_corte_acabamento_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.pagamento_corte_acabamento_id_seq OWNED BY opera.pagamento_corte_acabamento.id;


--
-- TOC entry 247 (class 1259 OID 187391)
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
-- TOC entry 248 (class 1259 OID 187410)
-- Name: pagamento_servicos_detalhe; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.pagamento_servicos_detalhe (
    pagamento_id bigint NOT NULL,
    entrada_acabamento_id integer NOT NULL,
    valor_servico numeric(10,2) NOT NULL
);


ALTER TABLE opera.pagamento_servicos_detalhe OWNER TO postgres;

--
-- TOC entry 246 (class 1259 OID 187390)
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
-- TOC entry 5922 (class 0 OID 0)
-- Dependencies: 246
-- Name: pagamento_servicos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.pagamento_servicos_id_seq OWNED BY opera.pagamento_servicos.id;


--
-- TOC entry 286 (class 1259 OID 187861)
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
-- TOC entry 285 (class 1259 OID 187860)
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
-- TOC entry 5923 (class 0 OID 0)
-- Dependencies: 285
-- Name: pecas_finalizadas_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.pecas_finalizadas_id_seq OWNED BY opera.pecas_finalizadas.id;


--
-- TOC entry 229 (class 1259 OID 187209)
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
-- TOC entry 5924 (class 0 OID 0)
-- Dependencies: 229
-- Name: TABLE usuario_permissoes; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON TABLE opera.usuario_permissoes IS 'TABELA 04 - Permissões de acesso às funções do sistema OPERA.';


--
-- TOC entry 309 (class 1259 OID 188107)
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
-- TOC entry 251 (class 1259 OID 187437)
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
-- TOC entry 306 (class 1259 OID 188061)
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
-- TOC entry 305 (class 1259 OID 188060)
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
-- TOC entry 5925 (class 0 OID 0)
-- Dependencies: 305
-- Name: relatorios_finalizacao_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.relatorios_finalizacao_id_seq OWNED BY opera.relatorios_finalizacao.id;


--
-- TOC entry 278 (class 1259 OID 187756)
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
-- TOC entry 277 (class 1259 OID 187755)
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
-- TOC entry 5926 (class 0 OID 0)
-- Dependencies: 277
-- Name: retorno_detalhes_tamanho_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.retorno_detalhes_tamanho_id_seq OWNED BY opera.retorno_detalhes_tamanho.id;


--
-- TOC entry 302 (class 1259 OID 188029)
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
-- TOC entry 301 (class 1259 OID 188028)
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
-- TOC entry 5927 (class 0 OID 0)
-- Dependencies: 301
-- Name: servicos_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.servicos_id_seq OWNED BY opera.servicos.id;


--
-- TOC entry 225 (class 1259 OID 187143)
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
-- TOC entry 5928 (class 0 OID 0)
-- Dependencies: 225
-- Name: TABLE usuarios; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON TABLE opera.usuarios IS 'TABELA 01 - Registro dos usuários do sistema OPERA.';


--
-- TOC entry 310 (class 1259 OID 188111)
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
-- TOC entry 231 (class 1259 OID 187228)
-- Name: usuario_logs; Type: TABLE; Schema: opera; Owner: postgres
--

CREATE TABLE opera.usuario_logs (
    id integer NOT NULL,
    usuario_id integer,
    acao text,
    detalhes text,
    data_hora timestamp without time zone DEFAULT now()
);


ALTER TABLE opera.usuario_logs OWNER TO postgres;

--
-- TOC entry 5929 (class 0 OID 0)
-- Dependencies: 231
-- Name: TABLE usuario_logs; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON TABLE opera.usuario_logs IS 'TABELA 05 - Histórico de ações realizadas pelos usuários.';


--
-- TOC entry 230 (class 1259 OID 187227)
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
-- TOC entry 5930 (class 0 OID 0)
-- Dependencies: 230
-- Name: usuario_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.usuario_logs_id_seq OWNED BY opera.usuario_logs.id;


--
-- TOC entry 226 (class 1259 OID 187162)
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
-- TOC entry 5931 (class 0 OID 0)
-- Dependencies: 226
-- Name: TABLE usuario_preferencias; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON TABLE opera.usuario_preferencias IS 'TABELA 02 - Preferências gerais do usuário.';


--
-- TOC entry 228 (class 1259 OID 187186)
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
-- TOC entry 5932 (class 0 OID 0)
-- Dependencies: 228
-- Name: TABLE usuario_temas_personalizados; Type: COMMENT; Schema: opera; Owner: postgres
--

COMMENT ON TABLE opera.usuario_temas_personalizados IS 'TABELA 03 - Temas customizados criados pelos usuários.';


--
-- TOC entry 227 (class 1259 OID 187185)
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
-- TOC entry 5933 (class 0 OID 0)
-- Dependencies: 227
-- Name: usuario_temas_personalizados_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.usuario_temas_personalizados_id_seq OWNED BY opera.usuario_temas_personalizados.id;


--
-- TOC entry 224 (class 1259 OID 187142)
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
-- TOC entry 5934 (class 0 OID 0)
-- Dependencies: 224
-- Name: usuarios_id_seq; Type: SEQUENCE OWNED BY; Schema: opera; Owner: postgres
--

ALTER SEQUENCE opera.usuarios_id_seq OWNED BY opera.usuarios.id;


--
-- TOC entry 5142 (class 2604 OID 187132)
-- Name: _schema_info id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera._schema_info ALTER COLUMN id SET DEFAULT nextval('opera._schema_info_id_seq'::regclass);


--
-- TOC entry 5203 (class 2604 OID 187427)
-- Name: adiantamento_faccao id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.adiantamento_faccao ALTER COLUMN id SET DEFAULT nextval('opera.adiantamento_faccao_id_seq'::regclass);


--
-- TOC entry 5208 (class 2604 OID 187449)
-- Name: cadastro_de_corte id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_de_corte_id_seq'::regclass);


--
-- TOC entry 5221 (class 2604 OID 187498)
-- Name: cadastro_de_corte_lotes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_lotes ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_de_corte_lotes_id_seq'::regclass);


--
-- TOC entry 5220 (class 2604 OID 187483)
-- Name: cadastro_de_corte_tecidos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_tecidos ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_de_corte_tecidos_id_seq'::regclass);


--
-- TOC entry 5196 (class 2604 OID 187373)
-- Name: cadastro_faccoes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_faccoes ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_faccoes_id_seq'::regclass);


--
-- TOC entry 5182 (class 2604 OID 187292)
-- Name: cadastro_modelos_aviamentos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_aviamentos ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_aviamentos_id_seq'::regclass);


--
-- TOC entry 5170 (class 2604 OID 187249)
-- Name: cadastro_modelos_cabecalho id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_cabecalho ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_cabecalho_id_seq'::regclass);


--
-- TOC entry 5194 (class 2604 OID 187355)
-- Name: cadastro_modelos_grade id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_grade ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_grade_id_seq'::regclass);


--
-- TOC entry 5192 (class 2604 OID 187336)
-- Name: cadastro_modelos_imagens id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_imagens ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_imagens_id_seq'::regclass);


--
-- TOC entry 5187 (class 2604 OID 187314)
-- Name: cadastro_modelos_outros id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_outros_id_seq'::regclass);


--
-- TOC entry 5410 (class 2604 OID 188124)
-- Name: cadastro_modelos_outros_servicos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros_servicos ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_outros_servicos_id_seq'::regclass);


--
-- TOC entry 5177 (class 2604 OID 187270)
-- Name: cadastro_modelos_tecidos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_tecidos ALTER COLUMN id SET DEFAULT nextval('opera.cadastro_modelos_tecidos_id_seq'::regclass);


--
-- TOC entry 5260 (class 2604 OID 187603)
-- Name: controle_envio_cortes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_envio_cortes ALTER COLUMN id SET DEFAULT nextval('opera.controle_envio_cortes_id_seq'::regclass);


--
-- TOC entry 5267 (class 2604 OID 187662)
-- Name: controle_retorno_cortes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_retorno_cortes ALTER COLUMN id SET DEFAULT nextval('opera.controle_retorno_cortes_id_seq'::regclass);


--
-- TOC entry 5276 (class 2604 OID 187689)
-- Name: cortes_finalizados id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados ALTER COLUMN id SET DEFAULT nextval('opera.cortes_finalizados_id_seq'::regclass);


--
-- TOC entry 5318 (class 2604 OID 187782)
-- Name: cortes_finalizados_completo id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo ALTER COLUMN id SET DEFAULT nextval('opera.cortes_finalizados_completo_id_seq'::regclass);


--
-- TOC entry 5262 (class 2604 OID 187621)
-- Name: entrada_acabamento id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento ALTER COLUMN id SET DEFAULT nextval('opera.entrada_acabamento_id_seq'::regclass);


--
-- TOC entry 5330 (class 2604 OID 187819)
-- Name: entrada_acabamento_detalhes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento_detalhes ALTER COLUMN id SET DEFAULT nextval('opera.entrada_acabamento_detalhes_id_seq'::regclass);


--
-- TOC entry 5229 (class 2604 OID 187549)
-- Name: envios_cortes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envios_cortes ALTER COLUMN id SET DEFAULT nextval('opera.envios_cortes_id_seq'::regclass);


--
-- TOC entry 5354 (class 2604 OID 187907)
-- Name: estoque_aviamentos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_aviamentos ALTER COLUMN id SET DEFAULT nextval('opera.estoque_aviamentos_id_seq'::regclass);


--
-- TOC entry 5368 (class 2604 OID 187951)
-- Name: estoque_escritorio id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_escritorio ALTER COLUMN id SET DEFAULT nextval('opera.estoque_escritorio_id_seq'::regclass);


--
-- TOC entry 5361 (class 2604 OID 187929)
-- Name: estoque_insumos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_insumos ALTER COLUMN id SET DEFAULT nextval('opera.estoque_insumos_id_seq'::regclass);


--
-- TOC entry 5375 (class 2604 OID 187973)
-- Name: estoque_limpeza id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_limpeza ALTER COLUMN id SET DEFAULT nextval('opera.estoque_limpeza_id_seq'::regclass);


--
-- TOC entry 5382 (class 2604 OID 187995)
-- Name: estoque_outros id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_outros ALTER COLUMN id SET DEFAULT nextval('opera.estoque_outros_id_seq'::regclass);


--
-- TOC entry 5389 (class 2604 OID 188017)
-- Name: estoque_saida_log id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_saida_log ALTER COLUMN id SET DEFAULT nextval('opera.estoque_saida_log_id_seq'::regclass);


--
-- TOC entry 5345 (class 2604 OID 187883)
-- Name: estoque_tecidos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_tecidos ALTER COLUMN id SET DEFAULT nextval('opera.estoque_tecidos_id_seq'::regclass);


--
-- TOC entry 5264 (class 2604 OID 187636)
-- Name: historico_de_servico id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_de_servico ALTER COLUMN id SET DEFAULT nextval('opera.historico_de_servico_id_seq'::regclass);


--
-- TOC entry 5394 (class 2604 OID 188046)
-- Name: historico_servicos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_servicos ALTER COLUMN id SET DEFAULT nextval('opera.historico_servicos_id_seq'::regclass);


--
-- TOC entry 5341 (class 2604 OID 187846)
-- Name: log_finalizacoes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.log_finalizacoes ALTER COLUMN id SET DEFAULT nextval('opera.log_finalizacoes_id_seq'::regclass);


--
-- TOC entry 5222 (class 2604 OID 187513)
-- Name: ordem_corte_ficha id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_ficha ALTER COLUMN id SET DEFAULT nextval('opera.ordem_corte_ficha_id_seq'::regclass);


--
-- TOC entry 5227 (class 2604 OID 187530)
-- Name: ordem_corte_lotes id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_lotes ALTER COLUMN id SET DEFAULT nextval('opera.ordem_corte_lotes_id_seq'::regclass);


--
-- TOC entry 5399 (class 2604 OID 188082)
-- Name: ordem_grade_preferencias id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_grade_preferencias ALTER COLUMN id SET DEFAULT nextval('opera.ordem_grade_preferencias_id_seq'::regclass);


--
-- TOC entry 5297 (class 2604 OID 187720)
-- Name: pagamento_corte_acabamento id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_corte_acabamento ALTER COLUMN id SET DEFAULT nextval('opera.pagamento_corte_acabamento_id_seq'::regclass);


--
-- TOC entry 5200 (class 2604 OID 187394)
-- Name: pagamento_servicos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_servicos ALTER COLUMN id SET DEFAULT nextval('opera.pagamento_servicos_id_seq'::regclass);


--
-- TOC entry 5343 (class 2604 OID 187864)
-- Name: pecas_finalizadas id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pecas_finalizadas ALTER COLUMN id SET DEFAULT nextval('opera.pecas_finalizadas_id_seq'::regclass);


--
-- TOC entry 5396 (class 2604 OID 188064)
-- Name: relatorios_finalizacao id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.relatorios_finalizacao ALTER COLUMN id SET DEFAULT nextval('opera.relatorios_finalizacao_id_seq'::regclass);


--
-- TOC entry 5311 (class 2604 OID 187759)
-- Name: retorno_detalhes_tamanho id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.retorno_detalhes_tamanho ALTER COLUMN id SET DEFAULT nextval('opera.retorno_detalhes_tamanho_id_seq'::regclass);


--
-- TOC entry 5391 (class 2604 OID 188032)
-- Name: servicos id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.servicos ALTER COLUMN id SET DEFAULT nextval('opera.servicos_id_seq'::regclass);


--
-- TOC entry 5168 (class 2604 OID 187231)
-- Name: usuario_logs id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_logs ALTER COLUMN id SET DEFAULT nextval('opera.usuario_logs_id_seq'::regclass);


--
-- TOC entry 5160 (class 2604 OID 187189)
-- Name: usuario_temas_personalizados id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_temas_personalizados ALTER COLUMN id SET DEFAULT nextval('opera.usuario_temas_personalizados_id_seq'::regclass);


--
-- TOC entry 5147 (class 2604 OID 187146)
-- Name: usuarios id; Type: DEFAULT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuarios ALTER COLUMN id SET DEFAULT nextval('opera.usuarios_id_seq'::regclass);


--
-- TOC entry 5791 (class 0 OID 187129)
-- Dependencies: 223
-- Data for Name: _schema_info; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera._schema_info (id, schema_name, versao, criado_em, atualizado_em) FROM stdin;
1	opera	1.0	2025-12-09 10:38:30.20526	2025-12-09 10:38:30.20526
\.


--
-- TOC entry 5818 (class 0 OID 187424)
-- Dependencies: 250
-- Data for Name: adiantamento_faccao; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.adiantamento_faccao (id, corte_id, codigo_modelo, faccao, valor, forma_pagamento, parcelas, data_hora) FROM stdin;
\.


--
-- TOC entry 5821 (class 0 OID 187446)
-- Dependencies: 253
-- Data for Name: cadastro_de_corte; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_de_corte (id, numero_ordem, ordem_corte, codigo, descricao, descricao_corte, data, data_envio, comprimento_matriz, largura_matriz, cortador, ajudante, auxiliar, total_folhas, metros_utilizados, bobinas_utilizadas, composicao_tecido, pp, p, m, g, gg, g1, g2, g3, total_pecas, rendimento, observacoes, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5825 (class 0 OID 187495)
-- Dependencies: 257
-- Data for Name: cadastro_de_corte_lotes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_de_corte_lotes (id, cadastro_id, lote, tecido, cor, composicao, bobinas, folhas, pp, p, m, g, gg, g1, g2, g3, total_lote) FROM stdin;
\.


--
-- TOC entry 5823 (class 0 OID 187480)
-- Dependencies: 255
-- Data for Name: cadastro_de_corte_tecidos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_de_corte_tecidos (id, cadastro_id, tecido, cor, composicao, bobinas, folhas, pp, p, m, g, gg, g1, g2, g3, total_pecas) FROM stdin;
\.


--
-- TOC entry 5813 (class 0 OID 187370)
-- Dependencies: 245
-- Data for Name: cadastro_faccoes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_faccoes (id, codigo, nome, tipo_prestador, telefone, endereco, titular_da_conta, cpf, banco, agencia, conta, pix, data, data_atualizacao, ativo) FROM stdin;
1	001	MICHAEL JACSON	Facção	14255554855	RUA D CHALES DEM FLORIADA	MICHAEL JACSON	4545454548	NUBANK	45454-8	454454	4545454548	2025-12-09	2025-12-09 11:04:54.848659	t
2	002	LUCIANA FINHOUD	Facção	6565656655	RU DAS ANDRADAS 105,4	LUCIANA FINHOUD	154545445445	BADRESCO	55855-4	546545	154545445445	2025-12-09	2025-12-09 11:07:39.385286	t
\.


--
-- TOC entry 5805 (class 0 OID 187289)
-- Dependencies: 237
-- Data for Name: cadastro_modelos_aviamentos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_aviamentos (id, codigo_modelo, cadastro_id, codigo_aviamento, descricao, cor, fornecedor, quantidade, valor_unidade, valor_total, created_at) FROM stdin;
\.


--
-- TOC entry 5801 (class 0 OID 187246)
-- Dependencies: 233
-- Data for Name: cadastro_modelos_cabecalho; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_cabecalho (id, codigo, descricao, colecao, tamanho_base, dificuldade, modelista, pilotista, custo_total, pronto_producao, grade_disponivel, data_criacao, data_atualizacao, created_at, updated_at) FROM stdin;
3	SADF	ASDFAS	DFAS	M	Médio	DFASDF		10.78	t	PP,P,M,G,GG,G1,G2,G3	2025-12-09 11:41:26.267745	2025-12-09 11:41:26.267745	2025-12-09 11:41:26.267745	2025-12-09 11:41:26.267745
\.


--
-- TOC entry 5811 (class 0 OID 187352)
-- Dependencies: 243
-- Data for Name: cadastro_modelos_grade; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_grade (id, modelo_id, tamanho, disponivel) FROM stdin;
\.


--
-- TOC entry 5809 (class 0 OID 187333)
-- Dependencies: 241
-- Data for Name: cadastro_modelos_imagens; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_imagens (id, codigo_modelo, cadastro_id, tipo_imagem, caminho_imagem, descricao, created_at) FROM stdin;
1	SADF	3	frente	C:/Users/User/Desktop/MODELO/ChatGPT Image 12_06_2025, 11_57_02 - Copia.png	Imagem frente do modelo	2025-12-09 11:41:26.267745
2	SADF	3	costas	C:/Users/User/Desktop/MODELO/ChatGPT Image 12_06_2025, 11_57_02 - Copia.png	Imagem costas do modelo	2025-12-09 11:41:26.267745
\.


--
-- TOC entry 5807 (class 0 OID 187311)
-- Dependencies: 239
-- Data for Name: cadastro_modelos_outros; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_outros (id, codigo_modelo, cadastro_id, codigo, descricao, cor, fornecedor, unidade, quantidade, preco, total, observacoes, created_at) FROM stdin;
\.


--
-- TOC entry 5878 (class 0 OID 188121)
-- Dependencies: 312
-- Data for Name: cadastro_modelos_outros_servicos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_outros_servicos (id, codigo_modelo, cadastro_id, codigo, descricao, cor, fornecedor, unidade, quantidade, preco, total, observacoes, created_at) FROM stdin;
\.


--
-- TOC entry 5803 (class 0 OID 187267)
-- Dependencies: 235
-- Data for Name: cadastro_modelos_tecidos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cadastro_modelos_tecidos (id, codigo_modelo, cadastro_id, codigo_tecido, descricao, cor, fornecedor, composicao, metros_peca, valor_metro, valor_total, created_at) FROM stdin;
1	SADF	3	1111	ALFAIATARIA	VERDE	MATEUS	98% ASDF21%ADSFG	1.5400	7.00	10.78	2025-12-09 11:41:26.267745
\.


--
-- TOC entry 5833 (class 0 OID 187600)
-- Dependencies: 265
-- Data for Name: controle_envio_cortes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.controle_envio_cortes (id, data_envio, servico, corte_id, ordem_corte, codigo_corte, descricao_corte, destino, costureira, faccao, quantidade_total, valor_peca, valor_total, status, observacao, pp, p, m, g, gg, g1, g2, g3) FROM stdin;
\.


--
-- TOC entry 5839 (class 0 OID 187659)
-- Dependencies: 271
-- Data for Name: controle_retorno_cortes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.controle_retorno_cortes (id, envio_id, data_chegada, telefone_encarregado, telefone_acabamento, resumo_piloto, aviamentos_recebidos, outros_recebidos, observacoes_gerais, total_entregue, total_copias, total_defeitos, total_faltantes, total_regulares, valor_total, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5841 (class 0 OID 187686)
-- Dependencies: 273
-- Data for Name: cortes_finalizados; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cortes_finalizados (id, corte_id, entrada_id, codigo, descricao, costureira, data_envio, data_chegada, data_final, qtd_enviada, total_pecas, quantidade_finalizada, observacao, status, data_conferencia, valor_peca, bonificacao, pago, data_pagamento, qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3, qtd_defeito_pp, qtd_defeito_p, qtd_defeito_m, qtd_defeito_g, qtd_defeito_gg, qtd_defeito_g1, qtd_defeito_g2, qtd_defeito_g3, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5848 (class 0 OID 187779)
-- Dependencies: 280
-- Data for Name: cortes_finalizados_completo; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.cortes_finalizados_completo (id, entrada_id, envio_id, corte_id, descricao, ordem_corte, codigo_corte, qtd_regular_pp, qtd_regular_p, qtd_regular_m, qtd_regular_g, qtd_regular_gg, qtd_regular_g1, qtd_regular_g2, qtd_regular_g3, status, observacoes, usuario_finalizacao, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5835 (class 0 OID 187618)
-- Dependencies: 267
-- Data for Name: entrada_acabamento; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.entrada_acabamento (id, envio_id, data_chegada, total_entregue, total_defeitos, total_faltantes, total_regulares, valor_total, pago, data_pagamento) FROM stdin;
\.


--
-- TOC entry 5850 (class 0 OID 187816)
-- Dependencies: 282
-- Data for Name: entrada_acabamento_detalhes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.entrada_acabamento_detalhes (id, entrada_id, observacoes_finalizacao, bonificacao_aplicada, usuario_conferencia, total_entregue, total_copias, total_defeitos, total_faltantes, total_regulares, valor_total_pagar, status_finalizacao, data_conferencia, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5844 (class 0 OID 187738)
-- Dependencies: 276
-- Data for Name: envio_detalhes_tamanho; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.envio_detalhes_tamanho (envio_id, tamanho, quantidade, quantidade_pilotos, valor_peca) FROM stdin;
\.


--
-- TOC entry 5831 (class 0 OID 187546)
-- Dependencies: 263
-- Data for Name: envios_cortes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.envios_cortes (id, data_envio, hora_envio, prestador_id, tipo_servico, corte_id, ordem_corte, codigo_corte, descricao_corte, colecao, material, cliente, cores, prioridade, forma_pagamento, status_envio, qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3, piloto_pp, piloto_p, piloto_m, piloto_g, piloto_gg, piloto_g1, piloto_g2, piloto_g3, valor_pp, valor_p, valor_m, valor_g, valor_gg, valor_g1, valor_g2, valor_g3, total_pecas, total_pilotos, valor_total_envio, resumo_pilotos, aviamentos, outros, observacoes, tel_encarregado, tel_acabamento, previsao_entrega, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5858 (class 0 OID 187904)
-- Dependencies: 290
-- Data for Name: estoque_aviamentos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_aviamentos (id, codigo, descricao, cor, fornecedor, quantidade, unidade, valor_unidade, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5862 (class 0 OID 187948)
-- Dependencies: 294
-- Data for Name: estoque_escritorio; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_escritorio (id, codigo, descricao, fornecedor, cor, quantidade, unidade, valor_unidade, tipo, categoria, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5860 (class 0 OID 187926)
-- Dependencies: 292
-- Data for Name: estoque_insumos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_insumos (id, codigo, descricao, fornecedor, cor, quantidade, unidade, valor_unidade, tipo, categoria, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5864 (class 0 OID 187970)
-- Dependencies: 296
-- Data for Name: estoque_limpeza; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_limpeza (id, codigo, descricao, fornecedor, cor, quantidade, unidade, valor_unidade, tipo, categoria, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5866 (class 0 OID 187992)
-- Dependencies: 298
-- Data for Name: estoque_outros; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_outros (id, codigo, descricao, fornecedor, cor, quantidade, unidade, valor_unidade, tipo, categoria, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5868 (class 0 OID 188014)
-- Dependencies: 300
-- Data for Name: estoque_saida_log; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_saida_log (id, data_hora, tipo_estoque, item_id, codigo, descricao, cor, quantidade, unidade, motivo, observacoes, usuario) FROM stdin;
\.


--
-- TOC entry 5856 (class 0 OID 187880)
-- Dependencies: 288
-- Data for Name: estoque_tecidos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.estoque_tecidos (id, codigo, descricao, cor, composicao, fornecedor, metros, kilos, valor_metro, valor_kilo, unidade, observacoes, localizacao, data_entrada, created_at, updated_at) FROM stdin;
1	1111	ALFAIATARIA	AZUL	98% ASDF21%ADSFG	MATEUS	5000.000	0.000	0.00	0.00	metros	ASDFASDFASDF	\N	2025-12-09	2025-12-09 11:02:42.35603	2025-12-09 11:02:42.35603
2	1111	ALFAIATARIA	PRETO	98% ASDF21%ADSFG	MATEUS	5000.000	0.000	0.00	0.00	metros	ASDFASDFASDF	\N	2025-12-09	2025-12-09 11:02:51.753375	2025-12-09 11:02:51.753375
3	1111	ALFAIATARIA	VERDE	98% ASDF21%ADSFG	MATEUS	5000.000	0.000	0.00	0.00	metros	ASDFASDFASDF	\N	2025-12-09	2025-12-09 11:03:03.86195	2025-12-09 11:03:03.86195
\.


--
-- TOC entry 5837 (class 0 OID 187633)
-- Dependencies: 269
-- Data for Name: historico_de_servico; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.historico_de_servico (id, envio_id, entrada_id, pagamento_id, tipo_servico, status, data_atualizacao) FROM stdin;
\.


--
-- TOC entry 5872 (class 0 OID 188043)
-- Dependencies: 304
-- Data for Name: historico_servicos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.historico_servicos (id, servico_id, data_evento, acao, observacoes) FROM stdin;
\.


--
-- TOC entry 5852 (class 0 OID 187843)
-- Dependencies: 284
-- Data for Name: log_finalizacoes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.log_finalizacoes (id, entrada_id, acao, dados_antes, dados_depois, usuario, data_hora, observacoes) FROM stdin;
\.


--
-- TOC entry 5827 (class 0 OID 187510)
-- Dependencies: 259
-- Data for Name: ordem_corte_ficha; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.ordem_corte_ficha (id, codigo_modelo, descricao_modelo, cortador, auxiliar, ajudante, data_registro, data_final, dias_estimados, horas_estimadas, porcentagens, consumo_peca, quantidade_desejada, total_pecas, observacoes, status, usuario_registro, data_atualizacao, ativo) FROM stdin;
1	SADF	ASDFAS	SILVIO	LEANDRO	\N	2025-12-09 11:42:23.758268	2025-12-09	0.0417	1.0000	{"porcent_1": 15.0, "porcent_2": 15.0, "porcent_3": 15.0, "porcent_4": 15.0, "porcent_5": 15.0, "porcent_6": 15.0, "porcent_7": 15.0, "porcent_8": 15.0}	1.6500	\N	\N	\N	Em Andamento	\N	2025-12-09 11:42:23.758268	t
\.


--
-- TOC entry 5829 (class 0 OID 187527)
-- Dependencies: 261
-- Data for Name: ordem_corte_lotes; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.ordem_corte_lotes (id, ordem_id, lote_numero, tamanho, quantidade) FROM stdin;
\.


--
-- TOC entry 5876 (class 0 OID 188079)
-- Dependencies: 308
-- Data for Name: ordem_grade_preferencias; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.ordem_grade_preferencias (id, usuario_id, nome, porcent_1, porcent_2, porcent_3, porcent_4, porcent_5, porcent_6, porcent_7, porcent_8, criado_em, atualizado_em) FROM stdin;
\.


--
-- TOC entry 5843 (class 0 OID 187717)
-- Dependencies: 275
-- Data for Name: pagamento_corte_acabamento; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.pagamento_corte_acabamento (id, costureira, tipo_servico, codigo, descricao, data_envio, data_chegada, quantidade_finalizada, valor_por_peca, adiantamento, ajuda_custo, bonificacao, pecas_faltantes, pecas_estragadas, desconto_pecas, total_pago, cpf, banco, agencia, conta, pix, data_pagamento, estornado, pecas_com_defeito, valor_defeito) FROM stdin;
\.


--
-- TOC entry 5815 (class 0 OID 187391)
-- Dependencies: 247
-- Data for Name: pagamento_servicos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.pagamento_servicos (id, prestador_id, nome_prestador, data_pagamento, valor_total, valor_adiantamento_abatido, valor_liquido, mes_referencia, observacoes, usuario_pagamento, data_registro) FROM stdin;
\.


--
-- TOC entry 5816 (class 0 OID 187410)
-- Dependencies: 248
-- Data for Name: pagamento_servicos_detalhe; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.pagamento_servicos_detalhe (pagamento_id, entrada_acabamento_id, valor_servico) FROM stdin;
\.


--
-- TOC entry 5854 (class 0 OID 187861)
-- Dependencies: 286
-- Data for Name: pecas_finalizadas; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.pecas_finalizadas (id, corte_id, entrada_id, codigo, descricao, costureira, data_envio, data_chegada, qtd_enviada, observacao, status, data_conferencia, valor_peca, bonificacao, qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3, qtd_defeito_pp, qtd_defeito_p, qtd_defeito_m, qtd_defeito_g, qtd_defeito_gg, qtd_defeito_g1, qtd_defeito_g2, qtd_defeito_g3, pago, pagamento_id, valor_pago, data_pagamento) FROM stdin;
\.


--
-- TOC entry 5819 (class 0 OID 187437)
-- Dependencies: 251
-- Data for Name: pricing_profiles; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.pricing_profiles (nome, impostos, comissao, cartao, margem, perdas, defeito, fixos, capacidade, variaveis, frete, arredondamento, canal, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5874 (class 0 OID 188061)
-- Dependencies: 306
-- Data for Name: relatorios_finalizacao; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.relatorios_finalizacao (id, entrada_id, usuario_geracao, data_geracao, tipo_relatorio, html_content, pdf_path, parametros, created_at) FROM stdin;
\.


--
-- TOC entry 5846 (class 0 OID 187756)
-- Dependencies: 278
-- Data for Name: retorno_detalhes_tamanho; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.retorno_detalhes_tamanho (id, envio_id, tamanho, entregue, copias, defeitos, faltantes, regulares, subtotal) FROM stdin;
\.


--
-- TOC entry 5870 (class 0 OID 188029)
-- Dependencies: 302
-- Data for Name: servicos; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.servicos (id, nome, descricao, prestador, data_inicio, data_fim, valor_unitario, quantidade, valor_total, status, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5799 (class 0 OID 187228)
-- Dependencies: 231
-- Data for Name: usuario_logs; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuario_logs (id, usuario_id, acao, detalhes, data_hora) FROM stdin;
\.


--
-- TOC entry 5797 (class 0 OID 187209)
-- Dependencies: 229
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
-- TOC entry 5794 (class 0 OID 187162)
-- Dependencies: 226
-- Data for Name: usuario_preferencias; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuario_preferencias (usuario_id, tema_nome, usar_tema_personalizado, tema_personalizado, layout_compacto, sidebar_recolhida, usar_animacoes, mostrar_dicas, idioma, notificacoes, atualizado_em) FROM stdin;
1	CLÁSSICO CLARO	t	\N	f	f	t	t	pt-BR	t	2025-12-10 16:01:12.33408
\.


--
-- TOC entry 5796 (class 0 OID 187186)
-- Dependencies: 228
-- Data for Name: usuario_temas_personalizados; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuario_temas_personalizados (id, usuario_id, nome_tema, cores_tema, data_criacao, atualizado_em) FROM stdin;
1	1	CLÁSSICO CLARO	{"borda": "#9CA3AF", "fundo": "#FFFFFF", "hover": "#E4E4E7", "texto": "#111827", "alerta": "#C62828", "selecao": "#111827", "sucesso": "#2E7D32", "destaque": "#B3B3B3", "primaria": "#F4F4F5", "botao_pdf": "#F59E0B", "terciaria": "#A1A1AA", "botao_novo": "#3B82F6", "secundaria": "#D4D4D8", "botao_ajuda": "#3B82F6", "botao_buscar": "#3B82F6", "botao_editar": "#06B6D4", "botao_limpar": "#F59E0B", "botao_salvar": "#10B981", "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_excluir": "#EF4444", "botao_filtrar": "#6366F1", "botao_cancelar": "#6B7280", "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_imprimir": "#8B5CF6", "botao_confirmar": "#22C55E", "botao_configurar": "#6B7280", "botao_export_csv": "#06B6D4", "botao_export_pdf": "#F59E0B", "botao_visualizar": "#6366F1", "botao_comprovante": "#8B5CF6", "botao_adiantamento": "#10B981"}	2025-12-10 16:01:10.861266	2025-12-10 16:01:10.861266
\.


--
-- TOC entry 5793 (class 0 OID 187143)
-- Dependencies: 225
-- Data for Name: usuarios; Type: TABLE DATA; Schema: opera; Owner: postgres
--

COPY opera.usuarios (id, usuario, senha_hash, hierarquia, email, data_criacao, ativo, dica_senha, ultimo_login, telefone, departamento, tema_preferido) FROM stdin;
1	Gil de Oliveira	$2a$06$ao4NgQlOSXITaQa7tO0gHeCQFqTcmVuD5/SF2SDmJaW9RIH47tsji	Administrador	opera@gil.com	2025-12-09 10:38:34.54333	t	25	\N	\N	\N	Cinza Oceano Claro
\.


--
-- TOC entry 5935 (class 0 OID 0)
-- Dependencies: 222
-- Name: _schema_info_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera._schema_info_id_seq', 1, true);


--
-- TOC entry 5936 (class 0 OID 0)
-- Dependencies: 249
-- Name: adiantamento_faccao_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.adiantamento_faccao_id_seq', 1, false);


--
-- TOC entry 5937 (class 0 OID 0)
-- Dependencies: 252
-- Name: cadastro_de_corte_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_de_corte_id_seq', 1, false);


--
-- TOC entry 5938 (class 0 OID 0)
-- Dependencies: 256
-- Name: cadastro_de_corte_lotes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_de_corte_lotes_id_seq', 1, false);


--
-- TOC entry 5939 (class 0 OID 0)
-- Dependencies: 254
-- Name: cadastro_de_corte_tecidos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_de_corte_tecidos_id_seq', 1, false);


--
-- TOC entry 5940 (class 0 OID 0)
-- Dependencies: 244
-- Name: cadastro_faccoes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_faccoes_id_seq', 2, true);


--
-- TOC entry 5941 (class 0 OID 0)
-- Dependencies: 236
-- Name: cadastro_modelos_aviamentos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_aviamentos_id_seq', 1, false);


--
-- TOC entry 5942 (class 0 OID 0)
-- Dependencies: 232
-- Name: cadastro_modelos_cabecalho_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_cabecalho_id_seq', 3, true);


--
-- TOC entry 5943 (class 0 OID 0)
-- Dependencies: 242
-- Name: cadastro_modelos_grade_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_grade_id_seq', 1, false);


--
-- TOC entry 5944 (class 0 OID 0)
-- Dependencies: 240
-- Name: cadastro_modelos_imagens_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_imagens_id_seq', 2, true);


--
-- TOC entry 5945 (class 0 OID 0)
-- Dependencies: 238
-- Name: cadastro_modelos_outros_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_outros_id_seq', 1, false);


--
-- TOC entry 5946 (class 0 OID 0)
-- Dependencies: 311
-- Name: cadastro_modelos_outros_servicos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_outros_servicos_id_seq', 1, false);


--
-- TOC entry 5947 (class 0 OID 0)
-- Dependencies: 234
-- Name: cadastro_modelos_tecidos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cadastro_modelos_tecidos_id_seq', 1, true);


--
-- TOC entry 5948 (class 0 OID 0)
-- Dependencies: 264
-- Name: controle_envio_cortes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.controle_envio_cortes_id_seq', 1, false);


--
-- TOC entry 5949 (class 0 OID 0)
-- Dependencies: 270
-- Name: controle_retorno_cortes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.controle_retorno_cortes_id_seq', 1, false);


--
-- TOC entry 5950 (class 0 OID 0)
-- Dependencies: 279
-- Name: cortes_finalizados_completo_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cortes_finalizados_completo_id_seq', 1, false);


--
-- TOC entry 5951 (class 0 OID 0)
-- Dependencies: 272
-- Name: cortes_finalizados_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.cortes_finalizados_id_seq', 1, false);


--
-- TOC entry 5952 (class 0 OID 0)
-- Dependencies: 281
-- Name: entrada_acabamento_detalhes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.entrada_acabamento_detalhes_id_seq', 1, false);


--
-- TOC entry 5953 (class 0 OID 0)
-- Dependencies: 266
-- Name: entrada_acabamento_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.entrada_acabamento_id_seq', 1, false);


--
-- TOC entry 5954 (class 0 OID 0)
-- Dependencies: 262
-- Name: envios_cortes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.envios_cortes_id_seq', 1, false);


--
-- TOC entry 5955 (class 0 OID 0)
-- Dependencies: 289
-- Name: estoque_aviamentos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_aviamentos_id_seq', 1, false);


--
-- TOC entry 5956 (class 0 OID 0)
-- Dependencies: 293
-- Name: estoque_escritorio_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_escritorio_id_seq', 1, false);


--
-- TOC entry 5957 (class 0 OID 0)
-- Dependencies: 291
-- Name: estoque_insumos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_insumos_id_seq', 1, false);


--
-- TOC entry 5958 (class 0 OID 0)
-- Dependencies: 295
-- Name: estoque_limpeza_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_limpeza_id_seq', 1, false);


--
-- TOC entry 5959 (class 0 OID 0)
-- Dependencies: 297
-- Name: estoque_outros_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_outros_id_seq', 1, false);


--
-- TOC entry 5960 (class 0 OID 0)
-- Dependencies: 299
-- Name: estoque_saida_log_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_saida_log_id_seq', 1, false);


--
-- TOC entry 5961 (class 0 OID 0)
-- Dependencies: 287
-- Name: estoque_tecidos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.estoque_tecidos_id_seq', 3, true);


--
-- TOC entry 5962 (class 0 OID 0)
-- Dependencies: 268
-- Name: historico_de_servico_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.historico_de_servico_id_seq', 1, false);


--
-- TOC entry 5963 (class 0 OID 0)
-- Dependencies: 303
-- Name: historico_servicos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.historico_servicos_id_seq', 1, false);


--
-- TOC entry 5964 (class 0 OID 0)
-- Dependencies: 283
-- Name: log_finalizacoes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.log_finalizacoes_id_seq', 1, false);


--
-- TOC entry 5965 (class 0 OID 0)
-- Dependencies: 258
-- Name: ordem_corte_ficha_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.ordem_corte_ficha_id_seq', 1, true);


--
-- TOC entry 5966 (class 0 OID 0)
-- Dependencies: 260
-- Name: ordem_corte_lotes_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.ordem_corte_lotes_id_seq', 1, false);


--
-- TOC entry 5967 (class 0 OID 0)
-- Dependencies: 307
-- Name: ordem_grade_preferencias_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.ordem_grade_preferencias_id_seq', 1, false);


--
-- TOC entry 5968 (class 0 OID 0)
-- Dependencies: 274
-- Name: pagamento_corte_acabamento_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.pagamento_corte_acabamento_id_seq', 1, false);


--
-- TOC entry 5969 (class 0 OID 0)
-- Dependencies: 246
-- Name: pagamento_servicos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.pagamento_servicos_id_seq', 1, false);


--
-- TOC entry 5970 (class 0 OID 0)
-- Dependencies: 285
-- Name: pecas_finalizadas_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.pecas_finalizadas_id_seq', 1, false);


--
-- TOC entry 5971 (class 0 OID 0)
-- Dependencies: 305
-- Name: relatorios_finalizacao_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.relatorios_finalizacao_id_seq', 1, false);


--
-- TOC entry 5972 (class 0 OID 0)
-- Dependencies: 277
-- Name: retorno_detalhes_tamanho_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.retorno_detalhes_tamanho_id_seq', 1, false);


--
-- TOC entry 5973 (class 0 OID 0)
-- Dependencies: 301
-- Name: servicos_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.servicos_id_seq', 1, false);


--
-- TOC entry 5974 (class 0 OID 0)
-- Dependencies: 230
-- Name: usuario_logs_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.usuario_logs_id_seq', 1, false);


--
-- TOC entry 5975 (class 0 OID 0)
-- Dependencies: 227
-- Name: usuario_temas_personalizados_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.usuario_temas_personalizados_id_seq', 1, true);


--
-- TOC entry 5976 (class 0 OID 0)
-- Dependencies: 224
-- Name: usuarios_id_seq; Type: SEQUENCE SET; Schema: opera; Owner: postgres
--

SELECT pg_catalog.setval('opera.usuarios_id_seq', 1, true);


--
-- TOC entry 5416 (class 2606 OID 187141)
-- Name: _schema_info _schema_info_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera._schema_info
    ADD CONSTRAINT _schema_info_pkey PRIMARY KEY (id);


--
-- TOC entry 5478 (class 2606 OID 187434)
-- Name: adiantamento_faccao adiantamento_faccao_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.adiantamento_faccao
    ADD CONSTRAINT adiantamento_faccao_pkey PRIMARY KEY (id);


--
-- TOC entry 5493 (class 2606 OID 187502)
-- Name: cadastro_de_corte_lotes cadastro_de_corte_lotes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_lotes
    ADD CONSTRAINT cadastro_de_corte_lotes_pkey PRIMARY KEY (id);


--
-- TOC entry 5484 (class 2606 OID 187474)
-- Name: cadastro_de_corte cadastro_de_corte_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte
    ADD CONSTRAINT cadastro_de_corte_pkey PRIMARY KEY (id);


--
-- TOC entry 5490 (class 2606 OID 187487)
-- Name: cadastro_de_corte_tecidos cadastro_de_corte_tecidos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_tecidos
    ADD CONSTRAINT cadastro_de_corte_tecidos_pkey PRIMARY KEY (id);


--
-- TOC entry 5466 (class 2606 OID 187385)
-- Name: cadastro_faccoes cadastro_faccoes_codigo_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_faccoes
    ADD CONSTRAINT cadastro_faccoes_codigo_key UNIQUE (codigo);


--
-- TOC entry 5468 (class 2606 OID 187383)
-- Name: cadastro_faccoes cadastro_faccoes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_faccoes
    ADD CONSTRAINT cadastro_faccoes_pkey PRIMARY KEY (id);


--
-- TOC entry 5450 (class 2606 OID 187302)
-- Name: cadastro_modelos_aviamentos cadastro_modelos_aviamentos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_aviamentos
    ADD CONSTRAINT cadastro_modelos_aviamentos_pkey PRIMARY KEY (id);


--
-- TOC entry 5440 (class 2606 OID 187263)
-- Name: cadastro_modelos_cabecalho cadastro_modelos_cabecalho_codigo_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_cabecalho
    ADD CONSTRAINT cadastro_modelos_cabecalho_codigo_key UNIQUE (codigo);


--
-- TOC entry 5442 (class 2606 OID 187261)
-- Name: cadastro_modelos_cabecalho cadastro_modelos_cabecalho_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_cabecalho
    ADD CONSTRAINT cadastro_modelos_cabecalho_pkey PRIMARY KEY (id);


--
-- TOC entry 5462 (class 2606 OID 187363)
-- Name: cadastro_modelos_grade cadastro_modelos_grade_modelo_id_tamanho_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_grade
    ADD CONSTRAINT cadastro_modelos_grade_modelo_id_tamanho_key UNIQUE (modelo_id, tamanho);


--
-- TOC entry 5464 (class 2606 OID 187361)
-- Name: cadastro_modelos_grade cadastro_modelos_grade_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_grade
    ADD CONSTRAINT cadastro_modelos_grade_pkey PRIMARY KEY (id);


--
-- TOC entry 5458 (class 2606 OID 187343)
-- Name: cadastro_modelos_imagens cadastro_modelos_imagens_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_imagens
    ADD CONSTRAINT cadastro_modelos_imagens_pkey PRIMARY KEY (id);


--
-- TOC entry 5454 (class 2606 OID 187324)
-- Name: cadastro_modelos_outros cadastro_modelos_outros_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros
    ADD CONSTRAINT cadastro_modelos_outros_pkey PRIMARY KEY (id);


--
-- TOC entry 5603 (class 2606 OID 188134)
-- Name: cadastro_modelos_outros_servicos cadastro_modelos_outros_servicos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros_servicos
    ADD CONSTRAINT cadastro_modelos_outros_servicos_pkey PRIMARY KEY (id);


--
-- TOC entry 5446 (class 2606 OID 187280)
-- Name: cadastro_modelos_tecidos cadastro_modelos_tecidos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_tecidos
    ADD CONSTRAINT cadastro_modelos_tecidos_pkey PRIMARY KEY (id);


--
-- TOC entry 5509 (class 2606 OID 187609)
-- Name: controle_envio_cortes controle_envio_cortes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_envio_cortes
    ADD CONSTRAINT controle_envio_cortes_pkey PRIMARY KEY (id);


--
-- TOC entry 5517 (class 2606 OID 187677)
-- Name: controle_retorno_cortes controle_retorno_cortes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_retorno_cortes
    ADD CONSTRAINT controle_retorno_cortes_pkey PRIMARY KEY (id);


--
-- TOC entry 5536 (class 2606 OID 187798)
-- Name: cortes_finalizados_completo cortes_finalizados_completo_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo
    ADD CONSTRAINT cortes_finalizados_completo_pkey PRIMARY KEY (id);


--
-- TOC entry 5521 (class 2606 OID 187714)
-- Name: cortes_finalizados cortes_finalizados_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados
    ADD CONSTRAINT cortes_finalizados_pkey PRIMARY KEY (id);


--
-- TOC entry 5539 (class 2606 OID 187835)
-- Name: entrada_acabamento_detalhes entrada_acabamento_detalhes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento_detalhes
    ADD CONSTRAINT entrada_acabamento_detalhes_pkey PRIMARY KEY (id);


--
-- TOC entry 5513 (class 2606 OID 187626)
-- Name: entrada_acabamento entrada_acabamento_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento
    ADD CONSTRAINT entrada_acabamento_pkey PRIMARY KEY (id);


--
-- TOC entry 5528 (class 2606 OID 187747)
-- Name: envio_detalhes_tamanho envio_detalhes_tamanho_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envio_detalhes_tamanho
    ADD CONSTRAINT envio_detalhes_tamanho_pkey PRIMARY KEY (envio_id, tamanho);


--
-- TOC entry 5504 (class 2606 OID 187585)
-- Name: envios_cortes envios_cortes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envios_cortes
    ADD CONSTRAINT envios_cortes_pkey PRIMARY KEY (id);


--
-- TOC entry 5556 (class 2606 OID 187922)
-- Name: estoque_aviamentos estoque_aviamentos_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_aviamentos
    ADD CONSTRAINT estoque_aviamentos_codigo_cor_key UNIQUE (codigo, cor);


--
-- TOC entry 5558 (class 2606 OID 187920)
-- Name: estoque_aviamentos estoque_aviamentos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_aviamentos
    ADD CONSTRAINT estoque_aviamentos_pkey PRIMARY KEY (id);


--
-- TOC entry 5568 (class 2606 OID 187966)
-- Name: estoque_escritorio estoque_escritorio_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_escritorio
    ADD CONSTRAINT estoque_escritorio_codigo_cor_key UNIQUE (codigo, cor);


--
-- TOC entry 5570 (class 2606 OID 187964)
-- Name: estoque_escritorio estoque_escritorio_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_escritorio
    ADD CONSTRAINT estoque_escritorio_pkey PRIMARY KEY (id);


--
-- TOC entry 5562 (class 2606 OID 187944)
-- Name: estoque_insumos estoque_insumos_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_insumos
    ADD CONSTRAINT estoque_insumos_codigo_cor_key UNIQUE (codigo, cor);


--
-- TOC entry 5564 (class 2606 OID 187942)
-- Name: estoque_insumos estoque_insumos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_insumos
    ADD CONSTRAINT estoque_insumos_pkey PRIMARY KEY (id);


--
-- TOC entry 5574 (class 2606 OID 187988)
-- Name: estoque_limpeza estoque_limpeza_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_limpeza
    ADD CONSTRAINT estoque_limpeza_codigo_cor_key UNIQUE (codigo, cor);


--
-- TOC entry 5576 (class 2606 OID 187986)
-- Name: estoque_limpeza estoque_limpeza_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_limpeza
    ADD CONSTRAINT estoque_limpeza_pkey PRIMARY KEY (id);


--
-- TOC entry 5580 (class 2606 OID 188010)
-- Name: estoque_outros estoque_outros_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_outros
    ADD CONSTRAINT estoque_outros_codigo_cor_key UNIQUE (codigo, cor);


--
-- TOC entry 5582 (class 2606 OID 188008)
-- Name: estoque_outros estoque_outros_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_outros
    ADD CONSTRAINT estoque_outros_pkey PRIMARY KEY (id);


--
-- TOC entry 5586 (class 2606 OID 188027)
-- Name: estoque_saida_log estoque_saida_log_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_saida_log
    ADD CONSTRAINT estoque_saida_log_pkey PRIMARY KEY (id);


--
-- TOC entry 5550 (class 2606 OID 187900)
-- Name: estoque_tecidos estoque_tecidos_codigo_cor_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_tecidos
    ADD CONSTRAINT estoque_tecidos_codigo_cor_key UNIQUE (codigo, cor);


--
-- TOC entry 5552 (class 2606 OID 187898)
-- Name: estoque_tecidos estoque_tecidos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.estoque_tecidos
    ADD CONSTRAINT estoque_tecidos_pkey PRIMARY KEY (id);


--
-- TOC entry 5515 (class 2606 OID 187642)
-- Name: historico_de_servico historico_de_servico_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_de_servico
    ADD CONSTRAINT historico_de_servico_pkey PRIMARY KEY (id);


--
-- TOC entry 5591 (class 2606 OID 188053)
-- Name: historico_servicos historico_servicos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_servicos
    ADD CONSTRAINT historico_servicos_pkey PRIMARY KEY (id);


--
-- TOC entry 5543 (class 2606 OID 187853)
-- Name: log_finalizacoes log_finalizacoes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.log_finalizacoes
    ADD CONSTRAINT log_finalizacoes_pkey PRIMARY KEY (id);


--
-- TOC entry 5498 (class 2606 OID 187523)
-- Name: ordem_corte_ficha ordem_corte_ficha_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_ficha
    ADD CONSTRAINT ordem_corte_ficha_pkey PRIMARY KEY (id);


--
-- TOC entry 5500 (class 2606 OID 187539)
-- Name: ordem_corte_lotes ordem_corte_lotes_ordem_id_lote_numero_tamanho_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_lotes
    ADD CONSTRAINT ordem_corte_lotes_ordem_id_lote_numero_tamanho_key UNIQUE (ordem_id, lote_numero, tamanho);


--
-- TOC entry 5502 (class 2606 OID 187537)
-- Name: ordem_corte_lotes ordem_corte_lotes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_lotes
    ADD CONSTRAINT ordem_corte_lotes_pkey PRIMARY KEY (id);


--
-- TOC entry 5599 (class 2606 OID 188097)
-- Name: ordem_grade_preferencias ordem_grade_preferencias_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_grade_preferencias
    ADD CONSTRAINT ordem_grade_preferencias_pkey PRIMARY KEY (id);


--
-- TOC entry 5601 (class 2606 OID 188099)
-- Name: ordem_grade_preferencias ordem_grade_preferencias_usuario_id_nome_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_grade_preferencias
    ADD CONSTRAINT ordem_grade_preferencias_usuario_id_nome_key UNIQUE (usuario_id, nome);


--
-- TOC entry 5526 (class 2606 OID 187735)
-- Name: pagamento_corte_acabamento pagamento_corte_acabamento_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_corte_acabamento
    ADD CONSTRAINT pagamento_corte_acabamento_pkey PRIMARY KEY (id);


--
-- TOC entry 5476 (class 2606 OID 187417)
-- Name: pagamento_servicos_detalhe pagamento_servicos_detalhe_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_servicos_detalhe
    ADD CONSTRAINT pagamento_servicos_detalhe_pkey PRIMARY KEY (pagamento_id, entrada_acabamento_id);


--
-- TOC entry 5474 (class 2606 OID 187404)
-- Name: pagamento_servicos pagamento_servicos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_servicos
    ADD CONSTRAINT pagamento_servicos_pkey PRIMARY KEY (id);


--
-- TOC entry 5546 (class 2606 OID 187872)
-- Name: pecas_finalizadas pecas_finalizadas_entrada_id_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pecas_finalizadas
    ADD CONSTRAINT pecas_finalizadas_entrada_id_key UNIQUE (entrada_id);


--
-- TOC entry 5548 (class 2606 OID 187870)
-- Name: pecas_finalizadas pecas_finalizadas_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pecas_finalizadas
    ADD CONSTRAINT pecas_finalizadas_pkey PRIMARY KEY (id);


--
-- TOC entry 5482 (class 2606 OID 187444)
-- Name: pricing_profiles pricing_profiles_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pricing_profiles
    ADD CONSTRAINT pricing_profiles_pkey PRIMARY KEY (nome);


--
-- TOC entry 5595 (class 2606 OID 188071)
-- Name: relatorios_finalizacao relatorios_finalizacao_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.relatorios_finalizacao
    ADD CONSTRAINT relatorios_finalizacao_pkey PRIMARY KEY (id);


--
-- TOC entry 5534 (class 2606 OID 187770)
-- Name: retorno_detalhes_tamanho retorno_detalhes_tamanho_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.retorno_detalhes_tamanho
    ADD CONSTRAINT retorno_detalhes_tamanho_pkey PRIMARY KEY (id);


--
-- TOC entry 5589 (class 2606 OID 188040)
-- Name: servicos servicos_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.servicos
    ADD CONSTRAINT servicos_pkey PRIMARY KEY (id);


--
-- TOC entry 5438 (class 2606 OID 187237)
-- Name: usuario_logs usuario_logs_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_logs
    ADD CONSTRAINT usuario_logs_pkey PRIMARY KEY (id);


--
-- TOC entry 5434 (class 2606 OID 187220)
-- Name: usuario_permissoes usuario_permissoes_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_permissoes
    ADD CONSTRAINT usuario_permissoes_pkey PRIMARY KEY (usuario_id, codigo);


--
-- TOC entry 5425 (class 2606 OID 187178)
-- Name: usuario_preferencias usuario_preferencias_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_preferencias
    ADD CONSTRAINT usuario_preferencias_pkey PRIMARY KEY (usuario_id);


--
-- TOC entry 5429 (class 2606 OID 187199)
-- Name: usuario_temas_personalizados usuario_temas_personalizados_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_temas_personalizados
    ADD CONSTRAINT usuario_temas_personalizados_pkey PRIMARY KEY (id);


--
-- TOC entry 5431 (class 2606 OID 187201)
-- Name: usuario_temas_personalizados usuario_temas_personalizados_usuario_id_nome_tema_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_temas_personalizados
    ADD CONSTRAINT usuario_temas_personalizados_usuario_id_nome_tema_key UNIQUE (usuario_id, nome_tema);


--
-- TOC entry 5420 (class 2606 OID 187157)
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- TOC entry 5422 (class 2606 OID 187159)
-- Name: usuarios usuarios_usuario_key; Type: CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuarios
    ADD CONSTRAINT usuarios_usuario_key UNIQUE (usuario);


--
-- TOC entry 5479 (class 1259 OID 187435)
-- Name: idx_adiantamento_corte; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_adiantamento_corte ON opera.adiantamento_faccao USING btree (corte_id);


--
-- TOC entry 5480 (class 1259 OID 187436)
-- Name: idx_adiantamento_faccao; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_adiantamento_faccao ON opera.adiantamento_faccao USING btree (faccao);


--
-- TOC entry 5485 (class 1259 OID 187475)
-- Name: idx_cadastro_corte_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cadastro_corte_codigo ON opera.cadastro_de_corte USING btree (codigo);


--
-- TOC entry 5486 (class 1259 OID 187477)
-- Name: idx_cadastro_corte_cortador; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cadastro_corte_cortador ON opera.cadastro_de_corte USING btree (cortador);


--
-- TOC entry 5487 (class 1259 OID 187476)
-- Name: idx_cadastro_corte_data; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cadastro_corte_data ON opera.cadastro_de_corte USING btree (data);


--
-- TOC entry 5488 (class 1259 OID 187478)
-- Name: idx_cadastro_corte_numero_ordem; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cadastro_corte_numero_ordem ON opera.cadastro_de_corte USING btree (numero_ordem);


--
-- TOC entry 5494 (class 1259 OID 187508)
-- Name: idx_corte_lotes_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_corte_lotes_cadastro ON opera.cadastro_de_corte_lotes USING btree (cadastro_id);


--
-- TOC entry 5491 (class 1259 OID 187493)
-- Name: idx_corte_tecidos_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_corte_tecidos_cadastro ON opera.cadastro_de_corte_tecidos USING btree (cadastro_id);


--
-- TOC entry 5537 (class 1259 OID 187814)
-- Name: idx_cortes_finalizados_comp_entrada; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cortes_finalizados_comp_entrada ON opera.cortes_finalizados_completo USING btree (entrada_id);


--
-- TOC entry 5522 (class 1259 OID 187715)
-- Name: idx_cortes_finalizados_corte; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_cortes_finalizados_corte ON opera.cortes_finalizados USING btree (corte_id);


--
-- TOC entry 5518 (class 1259 OID 187684)
-- Name: idx_ctrl_retorno_data; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ctrl_retorno_data ON opera.controle_retorno_cortes USING btree (data_chegada);


--
-- TOC entry 5519 (class 1259 OID 187683)
-- Name: idx_ctrl_retorno_envio; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ctrl_retorno_envio ON opera.controle_retorno_cortes USING btree (envio_id);


--
-- TOC entry 5540 (class 1259 OID 187841)
-- Name: idx_entrada_det_entrada; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_entrada_det_entrada ON opera.entrada_acabamento_detalhes USING btree (entrada_id);


--
-- TOC entry 5510 (class 1259 OID 187615)
-- Name: idx_envio_cortes_data_envio; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_cortes_data_envio ON opera.controle_envio_cortes USING btree (data_envio);


--
-- TOC entry 5511 (class 1259 OID 187616)
-- Name: idx_envio_cortes_status; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_cortes_status ON opera.controle_envio_cortes USING btree (status);


--
-- TOC entry 5529 (class 1259 OID 187754)
-- Name: idx_envio_det_tamanho; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_det_tamanho ON opera.envio_detalhes_tamanho USING btree (tamanho);


--
-- TOC entry 5530 (class 1259 OID 187753)
-- Name: idx_envio_det_tamanho_envio; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envio_det_tamanho_envio ON opera.envio_detalhes_tamanho USING btree (envio_id);


--
-- TOC entry 5505 (class 1259 OID 187596)
-- Name: idx_envios_cortes_data; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envios_cortes_data ON opera.envios_cortes USING btree (data_envio);


--
-- TOC entry 5506 (class 1259 OID 187597)
-- Name: idx_envios_cortes_prestador; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envios_cortes_prestador ON opera.envios_cortes USING btree (prestador_id);


--
-- TOC entry 5507 (class 1259 OID 187598)
-- Name: idx_envios_cortes_status; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_envios_cortes_status ON opera.envios_cortes USING btree (status_envio);


--
-- TOC entry 5559 (class 1259 OID 187923)
-- Name: idx_estoque_aviamentos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_aviamentos_codigo ON opera.estoque_aviamentos USING btree (codigo);


--
-- TOC entry 5560 (class 1259 OID 187924)
-- Name: idx_estoque_aviamentos_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_aviamentos_cor ON opera.estoque_aviamentos USING btree (cor);


--
-- TOC entry 5571 (class 1259 OID 187967)
-- Name: idx_estoque_escritorio_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_escritorio_codigo ON opera.estoque_escritorio USING btree (codigo);


--
-- TOC entry 5572 (class 1259 OID 187968)
-- Name: idx_estoque_escritorio_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_escritorio_cor ON opera.estoque_escritorio USING btree (cor);


--
-- TOC entry 5565 (class 1259 OID 187945)
-- Name: idx_estoque_insumos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_insumos_codigo ON opera.estoque_insumos USING btree (codigo);


--
-- TOC entry 5566 (class 1259 OID 187946)
-- Name: idx_estoque_insumos_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_insumos_cor ON opera.estoque_insumos USING btree (cor);


--
-- TOC entry 5577 (class 1259 OID 187989)
-- Name: idx_estoque_limpeza_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_limpeza_codigo ON opera.estoque_limpeza USING btree (codigo);


--
-- TOC entry 5578 (class 1259 OID 187990)
-- Name: idx_estoque_limpeza_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_limpeza_cor ON opera.estoque_limpeza USING btree (cor);


--
-- TOC entry 5583 (class 1259 OID 188011)
-- Name: idx_estoque_outros_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_outros_codigo ON opera.estoque_outros USING btree (codigo);


--
-- TOC entry 5584 (class 1259 OID 188012)
-- Name: idx_estoque_outros_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_outros_cor ON opera.estoque_outros USING btree (cor);


--
-- TOC entry 5553 (class 1259 OID 187901)
-- Name: idx_estoque_tecidos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_tecidos_codigo ON opera.estoque_tecidos USING btree (codigo);


--
-- TOC entry 5554 (class 1259 OID 187902)
-- Name: idx_estoque_tecidos_cor; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_estoque_tecidos_cor ON opera.estoque_tecidos USING btree (cor);


--
-- TOC entry 5469 (class 1259 OID 187389)
-- Name: idx_faccoes_ativo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_faccoes_ativo ON opera.cadastro_faccoes USING btree (ativo);


--
-- TOC entry 5470 (class 1259 OID 187387)
-- Name: idx_faccoes_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_faccoes_codigo ON opera.cadastro_faccoes USING btree (codigo);


--
-- TOC entry 5471 (class 1259 OID 187386)
-- Name: idx_faccoes_nome; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_faccoes_nome ON opera.cadastro_faccoes USING btree (nome);


--
-- TOC entry 5472 (class 1259 OID 187388)
-- Name: idx_faccoes_tipo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_faccoes_tipo ON opera.cadastro_faccoes USING btree (tipo_prestador);


--
-- TOC entry 5592 (class 1259 OID 188059)
-- Name: idx_hist_servico_id; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_hist_servico_id ON opera.historico_servicos USING btree (servico_id);


--
-- TOC entry 5541 (class 1259 OID 187859)
-- Name: idx_log_finalizacoes_entrada; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_log_finalizacoes_entrada ON opera.log_finalizacoes USING btree (entrada_id);


--
-- TOC entry 5451 (class 1259 OID 187308)
-- Name: idx_modelos_aviamentos_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_aviamentos_cadastro ON opera.cadastro_modelos_aviamentos USING btree (cadastro_id);


--
-- TOC entry 5452 (class 1259 OID 187309)
-- Name: idx_modelos_aviamentos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_aviamentos_codigo ON opera.cadastro_modelos_aviamentos USING btree (codigo_modelo);


--
-- TOC entry 5443 (class 1259 OID 187264)
-- Name: idx_modelos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_codigo ON opera.cadastro_modelos_cabecalho USING btree (codigo);


--
-- TOC entry 5444 (class 1259 OID 187265)
-- Name: idx_modelos_descricao; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_descricao ON opera.cadastro_modelos_cabecalho USING btree (descricao);


--
-- TOC entry 5459 (class 1259 OID 187349)
-- Name: idx_modelos_imagens_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_imagens_cadastro ON opera.cadastro_modelos_imagens USING btree (cadastro_id);


--
-- TOC entry 5460 (class 1259 OID 187350)
-- Name: idx_modelos_imagens_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_imagens_codigo ON opera.cadastro_modelos_imagens USING btree (codigo_modelo);


--
-- TOC entry 5455 (class 1259 OID 187330)
-- Name: idx_modelos_outros_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_outros_cadastro ON opera.cadastro_modelos_outros USING btree (cadastro_id);


--
-- TOC entry 5456 (class 1259 OID 187331)
-- Name: idx_modelos_outros_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_outros_codigo ON opera.cadastro_modelos_outros USING btree (codigo_modelo);


--
-- TOC entry 5604 (class 1259 OID 188140)
-- Name: idx_modelos_outros_servicos_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_outros_servicos_cadastro ON opera.cadastro_modelos_outros_servicos USING btree (cadastro_id);


--
-- TOC entry 5605 (class 1259 OID 188141)
-- Name: idx_modelos_outros_servicos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_outros_servicos_codigo ON opera.cadastro_modelos_outros_servicos USING btree (codigo_modelo);


--
-- TOC entry 5447 (class 1259 OID 187286)
-- Name: idx_modelos_tecidos_cadastro; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_tecidos_cadastro ON opera.cadastro_modelos_tecidos USING btree (cadastro_id);


--
-- TOC entry 5448 (class 1259 OID 187287)
-- Name: idx_modelos_tecidos_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_modelos_tecidos_codigo ON opera.cadastro_modelos_tecidos USING btree (codigo_modelo);


--
-- TOC entry 5495 (class 1259 OID 187524)
-- Name: idx_ordem_corte_codigo_modelo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ordem_corte_codigo_modelo ON opera.ordem_corte_ficha USING btree (codigo_modelo);


--
-- TOC entry 5496 (class 1259 OID 187525)
-- Name: idx_ordem_corte_status; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ordem_corte_status ON opera.ordem_corte_ficha USING btree (status);


--
-- TOC entry 5596 (class 1259 OID 188106)
-- Name: idx_ordem_grade_pref_nome; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ordem_grade_pref_nome ON opera.ordem_grade_preferencias USING btree (nome);


--
-- TOC entry 5597 (class 1259 OID 188105)
-- Name: idx_ordem_grade_pref_usuario; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_ordem_grade_pref_usuario ON opera.ordem_grade_preferencias USING btree (usuario_id);


--
-- TOC entry 5523 (class 1259 OID 187736)
-- Name: idx_pag_corte_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_pag_corte_codigo ON opera.pagamento_corte_acabamento USING btree (codigo);


--
-- TOC entry 5524 (class 1259 OID 187737)
-- Name: idx_pag_corte_costureira; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_pag_corte_costureira ON opera.pagamento_corte_acabamento USING btree (costureira);


--
-- TOC entry 5544 (class 1259 OID 187878)
-- Name: idx_pecas_finalizadas_corte; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_pecas_finalizadas_corte ON opera.pecas_finalizadas USING btree (corte_id);


--
-- TOC entry 5593 (class 1259 OID 188077)
-- Name: idx_relatorios_entrada; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_relatorios_entrada ON opera.relatorios_finalizacao USING btree (entrada_id);


--
-- TOC entry 5531 (class 1259 OID 187776)
-- Name: idx_retorno_tam_envio; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_retorno_tam_envio ON opera.retorno_detalhes_tamanho USING btree (envio_id);


--
-- TOC entry 5532 (class 1259 OID 187777)
-- Name: idx_retorno_tam_tamanho; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_retorno_tam_tamanho ON opera.retorno_detalhes_tamanho USING btree (tamanho);


--
-- TOC entry 5587 (class 1259 OID 188041)
-- Name: idx_servicos_prestador; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_servicos_prestador ON opera.servicos USING btree (prestador);


--
-- TOC entry 5435 (class 1259 OID 187244)
-- Name: idx_usuario_logs_data_hora; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_logs_data_hora ON opera.usuario_logs USING btree (data_hora);


--
-- TOC entry 5436 (class 1259 OID 187243)
-- Name: idx_usuario_logs_usuario; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_logs_usuario ON opera.usuario_logs USING btree (usuario_id);


--
-- TOC entry 5432 (class 1259 OID 187226)
-- Name: idx_usuario_permissoes_codigo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_permissoes_codigo ON opera.usuario_permissoes USING btree (codigo);


--
-- TOC entry 5423 (class 1259 OID 187184)
-- Name: idx_usuario_preferencias_tema; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_preferencias_tema ON opera.usuario_preferencias USING btree (tema_nome);


--
-- TOC entry 5426 (class 1259 OID 187208)
-- Name: idx_usuario_temas_nome; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_temas_nome ON opera.usuario_temas_personalizados USING btree (nome_tema);


--
-- TOC entry 5427 (class 1259 OID 187207)
-- Name: idx_usuario_temas_usuario; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuario_temas_usuario ON opera.usuario_temas_personalizados USING btree (usuario_id);


--
-- TOC entry 5417 (class 1259 OID 187161)
-- Name: idx_usuarios_ativo; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuarios_ativo ON opera.usuarios USING btree (ativo);


--
-- TOC entry 5418 (class 1259 OID 187160)
-- Name: idx_usuarios_hierarquia; Type: INDEX; Schema: opera; Owner: postgres
--

CREATE INDEX idx_usuarios_hierarquia ON opera.usuarios USING btree (hierarquia);


--
-- TOC entry 5640 (class 2620 OID 188142)
-- Name: usuario_temas_personalizados tr_validar_cores_tema; Type: TRIGGER; Schema: opera; Owner: postgres
--

CREATE TRIGGER tr_validar_cores_tema BEFORE INSERT OR UPDATE ON opera.usuario_temas_personalizados FOR EACH ROW EXECUTE FUNCTION opera.validar_cores_tema();


--
-- TOC entry 5618 (class 2606 OID 187503)
-- Name: cadastro_de_corte_lotes cadastro_de_corte_lotes_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_lotes
    ADD CONSTRAINT cadastro_de_corte_lotes_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE;


--
-- TOC entry 5617 (class 2606 OID 187488)
-- Name: cadastro_de_corte_tecidos cadastro_de_corte_tecidos_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_de_corte_tecidos
    ADD CONSTRAINT cadastro_de_corte_tecidos_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE CASCADE;


--
-- TOC entry 5611 (class 2606 OID 187303)
-- Name: cadastro_modelos_aviamentos cadastro_modelos_aviamentos_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_aviamentos
    ADD CONSTRAINT cadastro_modelos_aviamentos_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- TOC entry 5614 (class 2606 OID 187364)
-- Name: cadastro_modelos_grade cadastro_modelos_grade_modelo_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_grade
    ADD CONSTRAINT cadastro_modelos_grade_modelo_id_fkey FOREIGN KEY (modelo_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- TOC entry 5613 (class 2606 OID 187344)
-- Name: cadastro_modelos_imagens cadastro_modelos_imagens_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_imagens
    ADD CONSTRAINT cadastro_modelos_imagens_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- TOC entry 5612 (class 2606 OID 187325)
-- Name: cadastro_modelos_outros cadastro_modelos_outros_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros
    ADD CONSTRAINT cadastro_modelos_outros_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- TOC entry 5639 (class 2606 OID 188135)
-- Name: cadastro_modelos_outros_servicos cadastro_modelos_outros_servicos_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_outros_servicos
    ADD CONSTRAINT cadastro_modelos_outros_servicos_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- TOC entry 5610 (class 2606 OID 187281)
-- Name: cadastro_modelos_tecidos cadastro_modelos_tecidos_cadastro_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cadastro_modelos_tecidos
    ADD CONSTRAINT cadastro_modelos_tecidos_cadastro_id_fkey FOREIGN KEY (cadastro_id) REFERENCES opera.cadastro_modelos_cabecalho(id) ON DELETE CASCADE;


--
-- TOC entry 5622 (class 2606 OID 187610)
-- Name: controle_envio_cortes controle_envio_cortes_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_envio_cortes
    ADD CONSTRAINT controle_envio_cortes_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL;


--
-- TOC entry 5627 (class 2606 OID 187678)
-- Name: controle_retorno_cortes controle_retorno_cortes_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.controle_retorno_cortes
    ADD CONSTRAINT controle_retorno_cortes_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.envios_cortes(id) ON DELETE CASCADE;


--
-- TOC entry 5630 (class 2606 OID 187809)
-- Name: cortes_finalizados_completo cortes_finalizados_completo_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo
    ADD CONSTRAINT cortes_finalizados_completo_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL;


--
-- TOC entry 5631 (class 2606 OID 187799)
-- Name: cortes_finalizados_completo cortes_finalizados_completo_entrada_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo
    ADD CONSTRAINT cortes_finalizados_completo_entrada_id_fkey FOREIGN KEY (entrada_id) REFERENCES opera.entrada_acabamento(id) ON DELETE SET NULL;


--
-- TOC entry 5632 (class 2606 OID 187804)
-- Name: cortes_finalizados_completo cortes_finalizados_completo_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.cortes_finalizados_completo
    ADD CONSTRAINT cortes_finalizados_completo_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.controle_envio_cortes(id) ON DELETE SET NULL;


--
-- TOC entry 5633 (class 2606 OID 187836)
-- Name: entrada_acabamento_detalhes entrada_acabamento_detalhes_entrada_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento_detalhes
    ADD CONSTRAINT entrada_acabamento_detalhes_entrada_id_fkey FOREIGN KEY (entrada_id) REFERENCES opera.entrada_acabamento(id) ON DELETE CASCADE;


--
-- TOC entry 5623 (class 2606 OID 187627)
-- Name: entrada_acabamento entrada_acabamento_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.entrada_acabamento
    ADD CONSTRAINT entrada_acabamento_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE;


--
-- TOC entry 5628 (class 2606 OID 187748)
-- Name: envio_detalhes_tamanho envio_detalhes_tamanho_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envio_detalhes_tamanho
    ADD CONSTRAINT envio_detalhes_tamanho_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE;


--
-- TOC entry 5620 (class 2606 OID 187591)
-- Name: envios_cortes envios_cortes_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envios_cortes
    ADD CONSTRAINT envios_cortes_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE RESTRICT;


--
-- TOC entry 5621 (class 2606 OID 187586)
-- Name: envios_cortes envios_cortes_prestador_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.envios_cortes
    ADD CONSTRAINT envios_cortes_prestador_id_fkey FOREIGN KEY (prestador_id) REFERENCES opera.cadastro_faccoes(id) ON DELETE RESTRICT;


--
-- TOC entry 5624 (class 2606 OID 187648)
-- Name: historico_de_servico historico_de_servico_entrada_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_de_servico
    ADD CONSTRAINT historico_de_servico_entrada_id_fkey FOREIGN KEY (entrada_id) REFERENCES opera.entrada_acabamento(id) ON DELETE SET NULL;


--
-- TOC entry 5625 (class 2606 OID 187643)
-- Name: historico_de_servico historico_de_servico_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_de_servico
    ADD CONSTRAINT historico_de_servico_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.controle_envio_cortes(id) ON DELETE CASCADE;


--
-- TOC entry 5626 (class 2606 OID 187653)
-- Name: historico_de_servico historico_de_servico_pagamento_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_de_servico
    ADD CONSTRAINT historico_de_servico_pagamento_id_fkey FOREIGN KEY (pagamento_id) REFERENCES opera.pagamento_servicos(id) ON DELETE SET NULL;


--
-- TOC entry 5636 (class 2606 OID 188054)
-- Name: historico_servicos historico_servicos_servico_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.historico_servicos
    ADD CONSTRAINT historico_servicos_servico_id_fkey FOREIGN KEY (servico_id) REFERENCES opera.servicos(id) ON DELETE CASCADE;


--
-- TOC entry 5634 (class 2606 OID 187854)
-- Name: log_finalizacoes log_finalizacoes_entrada_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.log_finalizacoes
    ADD CONSTRAINT log_finalizacoes_entrada_id_fkey FOREIGN KEY (entrada_id) REFERENCES opera.entrada_acabamento(id);


--
-- TOC entry 5619 (class 2606 OID 187540)
-- Name: ordem_corte_lotes ordem_corte_lotes_ordem_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_corte_lotes
    ADD CONSTRAINT ordem_corte_lotes_ordem_id_fkey FOREIGN KEY (ordem_id) REFERENCES opera.ordem_corte_ficha(id) ON DELETE CASCADE;


--
-- TOC entry 5638 (class 2606 OID 188100)
-- Name: ordem_grade_preferencias ordem_grade_preferencias_usuario_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.ordem_grade_preferencias
    ADD CONSTRAINT ordem_grade_preferencias_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES opera.usuarios(id) ON DELETE CASCADE;


--
-- TOC entry 5616 (class 2606 OID 187418)
-- Name: pagamento_servicos_detalhe pagamento_servicos_detalhe_pagamento_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_servicos_detalhe
    ADD CONSTRAINT pagamento_servicos_detalhe_pagamento_id_fkey FOREIGN KEY (pagamento_id) REFERENCES opera.pagamento_servicos(id) ON DELETE CASCADE;


--
-- TOC entry 5615 (class 2606 OID 187405)
-- Name: pagamento_servicos pagamento_servicos_prestador_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pagamento_servicos
    ADD CONSTRAINT pagamento_servicos_prestador_id_fkey FOREIGN KEY (prestador_id) REFERENCES opera.cadastro_faccoes(id) ON DELETE SET NULL;


--
-- TOC entry 5635 (class 2606 OID 187873)
-- Name: pecas_finalizadas pecas_finalizadas_corte_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.pecas_finalizadas
    ADD CONSTRAINT pecas_finalizadas_corte_id_fkey FOREIGN KEY (corte_id) REFERENCES opera.cadastro_de_corte(id) ON DELETE SET NULL;


--
-- TOC entry 5637 (class 2606 OID 188072)
-- Name: relatorios_finalizacao relatorios_finalizacao_entrada_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.relatorios_finalizacao
    ADD CONSTRAINT relatorios_finalizacao_entrada_id_fkey FOREIGN KEY (entrada_id) REFERENCES opera.entrada_acabamento(id);


--
-- TOC entry 5629 (class 2606 OID 187771)
-- Name: retorno_detalhes_tamanho retorno_detalhes_tamanho_envio_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.retorno_detalhes_tamanho
    ADD CONSTRAINT retorno_detalhes_tamanho_envio_id_fkey FOREIGN KEY (envio_id) REFERENCES opera.envios_cortes(id) ON DELETE CASCADE;


--
-- TOC entry 5609 (class 2606 OID 187238)
-- Name: usuario_logs usuario_logs_usuario_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_logs
    ADD CONSTRAINT usuario_logs_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES opera.usuarios(id);


--
-- TOC entry 5608 (class 2606 OID 187221)
-- Name: usuario_permissoes usuario_permissoes_usuario_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_permissoes
    ADD CONSTRAINT usuario_permissoes_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES opera.usuarios(id) ON DELETE CASCADE;


--
-- TOC entry 5606 (class 2606 OID 187179)
-- Name: usuario_preferencias usuario_preferencias_usuario_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_preferencias
    ADD CONSTRAINT usuario_preferencias_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES opera.usuarios(id) ON DELETE CASCADE;


--
-- TOC entry 5607 (class 2606 OID 187202)
-- Name: usuario_temas_personalizados usuario_temas_personalizados_usuario_id_fkey; Type: FK CONSTRAINT; Schema: opera; Owner: postgres
--

ALTER TABLE ONLY opera.usuario_temas_personalizados
    ADD CONSTRAINT usuario_temas_personalizados_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES opera.usuarios(id) ON DELETE CASCADE;


--
-- TOC entry 5884 (class 0 OID 0)
-- Dependencies: 8
-- Name: SCHEMA opera; Type: ACL; Schema: -; Owner: postgres
--

GRANT ALL ON SCHEMA opera TO opera_app;


-- Completed on 2025-12-10 16:34:43

--
-- PostgreSQL database dump complete
--

\unrestrict I3QixhyQALtE6ISqaY10FLpAPLO9NrWzpfSsFVVeTKcXEaBYrPDfGAoWvDzFNjJ

