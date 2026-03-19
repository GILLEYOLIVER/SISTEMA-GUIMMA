# Migração i18n por etapas (para facilitar edição no navegador)

## Etapa 1 (um arquivo por PR)
- Restaurar **somente 1 página conflituosa por PR** para o formato original (sem shim), mantendo o arquivo `_usa-es-pt.py` como referência.
- Neste PR: `ATUALIZAR_SISTEMA.py`.

## Etapa 1b, 1c, 1d...
- Repetir o mesmo padrão em PRs separados para:
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
