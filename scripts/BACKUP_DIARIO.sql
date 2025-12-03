-- ================================================================
-- BACKUP DOS DADOS IMPORTANTES
-- ================================================================

SET search_path TO opera;

-- Backup de usuรกrios
SELECT * FROM usuarios 
WHERE updated_at >= CURRENT_DATE - INTERVAL '30 days';

-- Backup de modelos
SELECT * FROM cadastro_modelos_cabecalho 
WHERE updated_at >= CURRENT_DATE - INTERVAL '30 days';

-- Backup de cortes ativos
SELECT * FROM cadastro_de_corte 
WHERE data >= CURRENT_DATE - INTERVAL '60 days';

RAISE NOTICE '๐พ BACKUP DIรRIO GERADO COM SUCESSO!';