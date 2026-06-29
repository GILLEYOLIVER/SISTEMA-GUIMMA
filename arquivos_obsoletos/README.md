# Arquivos obsoletos

Esta pasta guarda arquivos retirados da raiz porque eram gerados, antigos, duplicados ou substituidos pelo fluxo atual de `packaging/`.

Nada daqui deve ser usado pelo app em producao. Se algum arquivo precisar voltar, revise primeiro as referencias no codigo e nos scripts de build.

Artefatos gerados localmente, como `build/`, `dist/`, caches e instaladores
temporarios, devem continuar fora do Git. Eles podem ser apagados para um
teste limpo e recriados pelos scripts em `packaging/`.

## Categorias

- `builds_antigos/`: saidas antigas de build e instaladores ja gerados.
- `caches_python/`: `__pycache__` e arquivos `.pyc`.
- `logs_antigos/`: logs antigos de execucao local.
- `instaladores_legados/`: rotinas antigas substituidas por `PAGINAS_DO_SISTEMA/SETUP_BANCO.py`, `configurar_postgres.py` e `packaging/`.
- `backups_versoes_antigos/`: copias geradas pela rotina antiga de atualizacao.
- `testes_codex/`: evidencias e screenshots de testes manuais/automatizados feitos durante ajustes.
