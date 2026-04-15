-- TESTE RÁPIDO - MONITORAR EXECUÇÃO DE ATUALIZAÇÃO OPERA
-- Execute após rodar o OPERA_UPDATER.py

-- 1) Últimas execuções de atualização
SELECT id,
       status,
       etapa_atual,
       version_from,
       version_to,
       rollback_executado,
       rollback_sucesso,
       iniciado_em,
       concluido_em
FROM opera.app_update_history
ORDER BY id DESC
LIMIT 10;

-- 2) Estado atual do lock
SELECT lock_name,
       locked,
       locked_by,
       machine_name,
       process_id,
       version_target,
       acquired_at,
       expires_at
FROM opera.app_update_lock
WHERE lock_name = 'OPERA_SYSTEM_UPDATE';

-- 3) Backups gerados
SELECT id,
       backup_nome,
       version_origem,
       status,
       restore_usado,
       criado_em,
       criado_por
FROM opera.app_backups
ORDER BY id DESC
LIMIT 10;

-- 4) Auditoria de migrações
SELECT id,
       migration_name,
       status,
       erro,
       iniciado_em,
       finalizado_em,
       app_version
FROM opera.schema_migrations
ORDER BY id DESC
LIMIT 30;

-- 5) Versão registrada do schema
SELECT schema_name,
       versao,
       atualizado_em
FROM opera._schema_info;
