\connect postgres

SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'BANCO_OPERA' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS "BANCO_OPERA";

SELECT '✅ BANCO_OPERA removido com sucesso!' AS status;