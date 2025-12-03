-- ================================================================
-- LIMPA DADOS MAS MANT√âM ESTRUTURA
-- ================================================================

SET search_path TO opera;

DO $$ 
BEGIN
    -- Limpar todas as tabelas (cuidado: sem WHERE!)
    TRUNCATE TABLE 
        usuarios, 
        usuario_permissoes, 
        usuario_logs,
        cadastro_modelos_cabecalho,
        cadastro_modelos_tecidos,
        cadastro_modelos_aviamentos,
        cadastro_de_corte,
        controle_envio_cortes,
        estoque_tecidos,
        estoque_aviamentos,
        estoque_insumos
    RESTART IDENTITY CASCADE;

    RAISE NOTICE 'üßπ TODOS OS DADOS FORAM LIMPOS!';
    RAISE NOTICE 'üèóÔ∏è ESTRUTURA DE TABELAS MANTIDA!';
END $$;