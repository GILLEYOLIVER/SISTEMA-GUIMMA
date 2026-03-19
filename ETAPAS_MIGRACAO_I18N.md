# Migração i18n por etapas (para facilitar edição no navegador)

## Etapa 1 (este commit)
- Restaurar páginas mais conflituosas para o formato original (sem shim), mantendo os arquivos `_usa-es-pt.py` como referência.
- Arquivos restaurados:
  - `ATUALIZAR_SISTEMA.py`
  - `BACKUP.py`
  - `BANCO_DADOS_FABRICA.py`
  - `CADASTRAR_MODELO.py`
  - `CADASTRO_CLIENTES.py`
  - `CADASTRO_DE_CORTE.py`

## Etapa 2
- Migrar somente páginas de baixo risco (até 3 por PR), com conflitos pequenos e revisáveis no editor web.
- Regra: não misturar menu/rotas com refatoração de páginas pesadas no mesmo PR.

## Etapa 3
- Após validar cada bloco, atualizar `route_map.json` e `MENU_PRINCIPAL.py` em PR separado.

## Etapa 4
- Opcional: substituir shims dinâmicos por wrappers estáticos simples (`from ... import *`) nos módulos que precisarem compatibilidade.
