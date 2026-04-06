# Relatório automático de varredura de fluxo

Gerado em: **2026-04-06 17:27:24 UTC**

## Resultado dos checks
- ✅ **Compilação Python**: Todos os módulos compilaram sem erro.
- ✅ **Integridade de rotas**: 46 rotas válidas e todos os arquivos referenciados existem.
- ❌ **Driver PostgreSQL (psycopg2)**: Indisponível: No module named 'psycopg2'
- ❌ **Cliente psql**: Comando `psql` não encontrado no PATH.

## Conclusão
- O smoke de fluxo foi executado, porém os testes E2E de leitura/gravação em banco ficam bloqueados até regularizar driver/cliente PostgreSQL no ambiente.
