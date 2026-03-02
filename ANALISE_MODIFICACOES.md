# Análise das modificações recentes

Este documento resume as principais mudanças observadas nos commits recentes do repositório.

## Mudanças centrais identificadas

1. **Fluxo de setup do banco voltou a usar a interface original (`SETUP_BANCO.py`)**
   - O script `auto_server_setup.py` agora abre a interface original de setup antes de continuar a automação.
   - Após o setup, ele procura um `config.json` com `validated_ok=true` e usa esses dados para criar role/database/schema e rodar SQLs.

2. **Login com tratamento de indisponibilidade de banco**
   - Em `PAGINAS_DO_SISTEMA/LOGUIN.py`, quando `ready_check()` falha, o sistema exibe erro centralizado e tenta abrir automaticamente o `SETUP_BANCO.py`.
   - Isso reduz travamento silencioso no primeiro uso/ambiente sem banco configurado.

3. **Estratégia de migrações por módulos (schema versionado)**
   - `PAGINAS_DO_SISTEMA/SCHEMA_MANAGER.py` define uma tabela `schema_version` e aplica migrações por módulo (`core`, `usuarios`, `modelos`, etc.).
   - A execução compara versão atual vs alvo e aplica apenas o pendente.

4. **Padronização de configuração local**
   - `config.json` (raiz e pasta de páginas) está com estrutura mais completa: `validated_ok`, `defaults`, listas de `hosts`/`ports`, `appname`, `connect_timeout`.

5. **Documentação de estrutura e build expandida**
   - `README.md` recebeu um mapeamento amplo da estrutura do projeto e orientações de build/instalador.

## Impacto funcional esperado

- Melhora de experiência de instalação/configuração de banco em máquinas novas.
- Menor risco de usuário ficar preso na tela de login sem orientação quando o banco não está pronto.
- Evolução do schema com controle de versão por módulo, reduzindo risco de divergência entre ambientes.
- Maior clareza operacional para manutenção e empacotamento.

## Pontos de atenção

- O `config.json` atual contém senha em texto plano. Para produção, recomenda-se proteger segredo via variável de ambiente/secret manager.
- Em `auto_server_setup.py`, há uso de SQL formatado com f-string para identificadores; ideal blindar nomes dinâmicos de role/schema.
