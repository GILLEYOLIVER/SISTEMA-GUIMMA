-- ================================================================
-- [CRIAR USUÁRIOS PADRÃO - MULTINÍVEIS]
-- ================================================================
DO $$
DECLARE
    v_hash TEXT;
    v_id   INTEGER;
BEGIN
    ----------------------------------------------------------------
    -- 1️⃣  GIL DE OLIVEIRA  → Administrador total
    ----------------------------------------------------------------
    v_hash := encode(digest('sistema_profissional_v2.2' || '2580', 'sha256'), 'hex');
    SELECT id INTO v_id FROM opera.usuarios WHERE LOWER(TRIM(usuario)) = LOWER('GIL DE OLIVEIRA');
    IF v_id IS NULL THEN
        INSERT INTO opera.usuarios (usuario, senha_hash, hierarquia, ativo, dica_senha, tema_preferido)
        VALUES ('GIL DE OLIVEIRA', v_hash, 'admin', TRUE, '25', 'Azul Oceano')
        RETURNING id INTO v_id;
        RAISE NOTICE '✅ Usuário GIL DE OLIVEIRA criado (id=%).', v_id;
    ELSE
        UPDATE opera.usuarios
        SET senha_hash=v_hash, hierarquia='admin', ativo=TRUE, dica_senha='25', tema_preferido='Azul Oceano'
        WHERE id=v_id;
        RAISE NOTICE '🔄 Usuário GIL DE OLIVEIRA atualizado (id=%).', v_id;
    END IF;
    INSERT INTO opera.usuario_preferencias (usuario_id, tema_nome)
    VALUES (v_id, 'Azul Oceano')
    ON CONFLICT (usuario_id) DO UPDATE SET tema_nome = EXCLUDED.tema_nome;

    ----------------------------------------------------------------
    -- 2️⃣  MARIA FONSECA  → Supervisora (acesso amplo, sem admin)
    ----------------------------------------------------------------
    v_hash := encode(digest('sistema_profissional_v2.2' || '12345', 'sha256'), 'hex');
    SELECT id INTO v_id FROM opera.usuarios WHERE LOWER(TRIM(usuario)) = LOWER('MARIA FONSECA');
    IF v_id IS NULL THEN
        INSERT INTO opera.usuarios (usuario, senha_hash, hierarquia, ativo, dica_senha, tema_preferido)
        VALUES ('MARIA FONSECA', v_hash, 'supervisor', TRUE, 'senha 123', 'Verde Esmeralda')
        RETURNING id INTO v_id;
        RAISE NOTICE '✅ Usuário MARIA FONSECA criado (id=%).', v_id;
    ELSE
        UPDATE opera.usuarios
        SET senha_hash=v_hash, hierarquia='supervisor', ativo=TRUE, dica_senha='senha 123', tema_preferido='Verde Esmeralda'
        WHERE id=v_id;
        RAISE NOTICE '🔄 Usuário MARIA FONSECA atualizado (id=%).', v_id;
    END IF;
    INSERT INTO opera.usuario_preferencias (usuario_id, tema_nome)
    VALUES (v_id, 'Verde Esmeralda')
    ON CONFLICT (usuario_id) DO UPDATE SET tema_nome = EXCLUDED.tema_nome;

    ----------------------------------------------------------------
    -- 3️⃣  JOÃO CARVALHO  → Operador de produção (acesso restrito)
    ----------------------------------------------------------------
    v_hash := encode(digest('sistema_profissional_v2.2' || '9876', 'sha256'), 'hex');
    SELECT id INTO v_id FROM opera.usuarios WHERE LOWER(TRIM(usuario)) = LOWER('JOÃO CARVALHO');
    IF v_id IS NULL THEN
        INSERT INTO opera.usuarios (usuario, senha_hash, hierarquia, ativo, dica_senha, tema_preferido)
        VALUES ('JOÃO CARVALHO', v_hash, 'operador', TRUE, '98', 'Cinza Urbano')
        RETURNING id INTO v_id;
        RAISE NOTICE '✅ Usuário JOÃO CARVALHO criado (id=%).', v_id;
    ELSE
        UPDATE opera.usuarios
        SET senha_hash=v_hash, hierarquia='operador', ativo=TRUE, dica_senha='98', tema_preferido='Cinza Urbano'
        WHERE id=v_id;
        RAISE NOTICE '🔄 Usuário JOÃO CARVALHO atualizado (id=%).', v_id;
    END IF;
    INSERT INTO opera.usuario_preferencias (usuario_id, tema_nome)
    VALUES (v_id, 'Cinza Urbano')
    ON CONFLICT (usuario_id) DO UPDATE SET tema_nome = EXCLUDED.tema_nome;

    ----------------------------------------------------------------
    -- 4️⃣  ANA PAULA  → Financeiro (acesso a relatórios e contas)
    ----------------------------------------------------------------
    v_hash := encode(digest('sistema_profissional_v2.2' || '4321', 'sha256'), 'hex');
    SELECT id INTO v_id FROM opera.usuarios WHERE LOWER(TRIM(usuario)) = LOWER('ANA PAULA');
    IF v_id IS NULL THEN
        INSERT INTO opera.usuarios (usuario, senha_hash, hierarquia, ativo, dica_senha, tema_preferido)
        VALUES ('ANA PAULA', v_hash, 'financeiro', TRUE, '43', 'Dourado Clássico')
        RETURNING id INTO v_id;
        RAISE NOTICE '✅ Usuário ANA PAULA criado (id=%).', v_id;
    ELSE
        UPDATE opera.usuarios
        SET senha_hash=v_hash, hierarquia='financeiro', ativo=TRUE, dica_senha='43', tema_preferido='Dourado Clássico'
        WHERE id=v_id;
        RAISE NOTICE '🔄 Usuário ANA PAULA atualizado (id=%).', v_id;
    END IF;
    INSERT INTO opera.usuario_preferencias (usuario_id, tema_nome)
    VALUES (v_id, 'Dourado Clássico')
    ON CONFLICT (usuario_id) DO UPDATE SET tema_nome = EXCLUDED.tema_nome;

    ----------------------------------------------------------------
    RAISE NOTICE '🏁 Todos os usuários padrão foram verificados/criados com sucesso.';
END $$;
