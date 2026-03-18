# SISTEMA OPERA

Este repositório contém o aplicativo desktop **Sistema Opera**, scripts de build/instalador e dados auxiliares.

> **Importante sobre estrutura:** a imagem de referência mostra `src/PAGINAS_DO_SISTEMA`, porém neste repositório a pasta de código está atualmente em `PAGINAS_DO_SISTEMA/` (na raiz).


## Atualizações recentes do projeto (março/2026)

Com base nos commits mais recentes da branch `work` (especialmente os de **2026-03-17** e **2026-03-18**), os principais avanços foram:

- **Evolução do fluxo de planejamento/OP**:
  - criação/uso da tela **Ordens Planejadas** (`ORDENS_PLANEJADAS_usa-es-pt.py`);
  - ajuste de KPI de execução e correção de avanço indevido de OP;
  - cálculo de progresso por etapas do processo e destaque visual de ordens concluídas.
- **Padronização de arquivos funcionais para sufixo `*_usa-es-pt.py`** em módulos críticos (ex.: planejamento, nova ordem, pagamentos, MRP, entrada/saída de estoque e adiantamentos).
- **Atualização do roteamento de telas** em `PAGINAS_DO_SISTEMA/route_map.json` para refletir os novos nomes de arquivo.
- **Fortalecimento do banco para o planejamento** em `SCRIPTS/3_CRIAR_TABELAS.sql` (e espelho em `data/INSTAL_BANCO_APP/scripts/3_CRIAR_TABELAS.sql`), com campos como `etapa_atual`, `percentual_progresso` e tabelas auxiliares de planejamento (grade, tecidos, aviamentos e vínculo com ordens geradas).

> Resumo prático: o sistema passou a ter um controle mais confiável do ciclo de produção, com progresso de OP mais consistente e melhor integração entre planejamento, execução e dados persistidos no PostgreSQL.

## Estrutura detalhada do projeto (ramificações principais)

```text
SISTEMA-GUIMMA/
├── README.md
├── requirements.txt
├── SistemaOpera.spec
├── PAGINAS_DO_SISTEMA/
├── data/
│   ├── BANCO_DE_DADOS/
│   ├── INSTAL_BANCO_APP/
│   ├── RECIBOS_DE_PAGAMENTOS/
│   └── COMMIT
├── packaging/
│   ├── BUILD_GUIDE.md
│   ├── build.py
│   ├── parse_pyinstaller_warnings.py
│   ├── windows/
│   │   ├── SISTEMA_OPERA.iss
│   │   ├── build_installer.ps1
│   │   └── prepare_icon.py
│   ├── macos/
│   │   ├── build_installer.sh
│   │   └── dmg_settings.py
│   └── release/
│       ├── build_release.ps1
│       └── build_release.sh
└── icons/
```

## Detalhamento por pasta e arquivos

### 1) Raiz do projeto

- `README.md`: documentação principal (build, instalador e estrutura).
- `requirements.txt`: dependências Python fixadas para desenvolvimento/build.
- `SistemaOpera.spec`: spec do PyInstaller para empacotar o executável.

### 2) `PAGINAS_DO_SISTEMA/` (código principal da aplicação)

#### Núcleo, inicialização e utilitários
- `MAIN.py`: ponto principal de execução do app.
- `MENU_PRINCIPAL.py`: tela/menu central de navegação.
- `SPLASH.py`: tela de splash inicial.
- `LOGUIN.py`: autenticação/login.
- `OPERA_PATHS.py`: resolução de caminhos (dados/logs/configuração).
- `database_logger.py`: logging relacionado a operações de banco.
- `LOG_SISTEMA.py`: visualização/gerência de logs do sistema.
- `ui_after_guard.py`: lógica de UI pós-validações/guards.
- `__init__.py`: marcação de pacote Python.

#### Banco, usuários e administração
- `BANCO_DE_DADOS_PG.py`: conexão/operações com PostgreSQL.
- `BANCO_DADOS_FABRICA_usa-es-pt.py`: rotinas de banco vinculadas ao contexto de fábrica.
- `USUARIOS.py`: cadastro/gestão de usuários.
- `ATUALIZAR_SISTEMA_usa-es-pt.py`: rotinas de atualização do sistema.
- `BACKUP_usa-es-pt.py`: rotinas de backup.

#### Cadastros e produção
- `CADASTRAR_MODELO_usa-es-pt.py`: cadastro de modelos.
- `NOVA CADASTRO MODELOS.py`: versão/fluxo alternativo de cadastro de modelos.
- `CADASTRO_CLIENTES_usa-es-pt.py`: cadastro de clientes.
- `CADASTRO_FACCOES_usa-es-pt.py`: cadastro de facções.
- `CADASTRO_DE_CORTE_usa-es-pt.py`: cadastro de ordens/informações de corte.
- `NOVA_ORDEM_usa-es-pt.py`: criação de nova ordem.
- `ORDENS_PLANEJADAS_usa-es-pt.py`: painel de ordens planejadas com filtros de período/modelo/coleção e atalho para geração da Nova Ordem.
- `PLANEJAMENTO_PRODUCAO_usa-es-pt.py`: planejamento de produção.
- `MRP_PLANEJAMENTO_usa-es-pt.py`: MRP e planejamento de materiais.
- `FINALIZAR_CORTE_ACABAMENTO_usa-es-pt.py`: finalização de corte/acabamento.
- `CONTROLE_ENVIO_CORTES_usa-es-pt.py`: controle de envio de cortes.
- `CONTROLE_RETORNO_CORTE_usa-es-pt.py`: controle de retorno de cortes.
- `RETRABALHO_DEFEITOS.py`: gestão de retrabalho e defeitos.

#### Estoque, compras e financeiro
- `ENTRADA_ESTOQUE_usa-es-pt.py`: entradas de estoque.
- `SAIDA_ESTOQUE_usa-es-pt.py`: saídas de estoque.
- `RELATORIO_ESTOQUE.py`: relatórios de estoque.
- `COMPRAS_usa-es-pt.py`: processo de compras.
- `CONTAS_A_PAGAR_usa-es-pt.py`: contas a pagar.
- `ADIANTAMENTO_PAGE_usa-es-pt.py`: registro/controle de adiantamentos.
- `ADIANTAMENTO_PENDENTE_usa-es-pt.py`: pendências de adiantamentos.
- `PAGAMENTO_SERVICOS_usa-es-pt.py`: pagamento de serviços.
- `FOLHA_PAGAMENTO_SERVICOS_usa-es-pt.py`: folha/pagamentos de serviços.
- `FECHAMENTO_MENSAL_usa-es-pt.py`: fechamento mensal financeiro.
- `PRECIFICACAO_PRODUTO_usa-es-pt.py`: precificação de produto.

#### Consultas, relatórios e impressão
- `CONSULTAR_ORDENS_usa-es-pt.py`: consulta de ordens.
- `CONSULTAR_SERVICOS_usa-es-pt.py`: consulta de serviços.
- `RELATORIO_ACABAMENTO.py`: relatório de acabamento.
- `RELATORIO_CUSTOS_REAIS.py`: relatório de custos reais.
- `RELATORIO_ENVIO_DETALHADO.py`: relatório detalhado de envios.
- `RELATORIO_MODELOS_PRODUZIDOS.py`: relatório de modelos produzidos.
- `RELATORIO_SERVICOS_EXTERNOS.py`: relatório de serviços externos.
- `IMPRIMIR_FICHAS_TECNICAS_usa-es-pt.py`: impressão de fichas técnicas.
- `REIMPRIMIR-ORDENS-DE-CORTE.py`: reimpressão de ordens de corte.
- `RECIBOS_PAGAMENTOS.py`: emissão/controle de recibos de pagamentos.
- `UI_TREEVIEW_OPERA.py`: componente de visualização em árvore (treeview).
- `DASHBOARD_usa-es-pt.py`: painel/indicadores do sistema.

#### Tema, aparência e configuração
- `TEMAS.py`: temas ativos da interface.
- `TEMAS-anterior.py`: versão anterior de temas.
- `tema_database.py`: tema/estilo aplicado a telas de banco.
- `route_map.json`: mapeamento de rotas/telas.
- `app_config.json`: configuração geral da aplicação.
- `app_settings.json`: preferências/configurações de execução.
- `config.json`: configuração local de conexão/parametrização.

#### Arquivos auxiliares, legados e testes
- `README.md`: documentação interna da pasta de páginas.
- `TEST_REPORT.md`: relatório de testes.
- `GSDGASDFASDF.py`: arquivo auxiliar/protótipo (nome não funcional).
- `cadastro de corte antes.py`: versão legada de cadastro de corte.
- `.gitignore`: regras de versionamento locais da pasta.

#### Assets (imagens, fontes e ícones usados pela aplicação)
- `DejaVuSans.ttf`
- `FUNDO_INSTALADOR.jpg`
- `FUNDO_LOGUIN.jpg`
- `FUNDO_SPLASH.jpg`
- `ICONE_SISTEMA.icns`
- `ICONE_SISTEMA.png`
- `LOGO.jpg`
- `OPERA.jpg`

#### Artefatos gerados em runtime (podem aparecer nesta pasta)
- `compras_*.pdf`
- `mrp_*.pdf`
- `planejamento_*.pdf`

### 3) `data/`

- `data/COMMIT`: marcador interno usado no fluxo atual de empacotamento/controle.

#### `data/BANCO_DE_DADOS/`
- Função: dados de apoio e arquivos gerados para banco/documentos.
- Arquivos de exemplo no nível raiz:
  - `NOTAS CONSERTO`
  - `cadastro_modelo_1111.pdf`
  - `cadastro_modelo_3333.pdf`
  - `cadastro_modelo_555.pdf`
  - `cadastro_modelo_6356.pdf`
  - `cadastro_modelo_SADF.pdf`
- Subpastas:
  - `IMAGENS_AVIAMENTOS/`
  - `IMAGENS_FRENTE_COSTAS/`
  - `IMAGENS_OUTROS/`
  - `IMAGENS_TECIDOS/`
  - `PDFs/`

#### `data/INSTAL_BANCO_APP/`
- `main.py`: entrada do app/ferramenta de instalação de banco.
- `interface.py`: interface da ferramenta de instalação.
- `database_manager.py`: lógica de criação/gestão do banco.
- `config.json`: configuração padrão da ferramenta.
- `start_clean.py`: inicialização em modo limpo.
- `dmg_settings.py`: configurações de empacotamento DMG.
- `scripts/`:
  - `1_CRIAR_BANCO.sql`
  - `2_CRIAR_SCHEMA.sql`
  - `3_CRIAR_TABELAS.sql`
  - `APAGAR_TUDO.sql`
  - `AUDITOR.sql`
  - `BACKUP_DIARIO.sql`
  - `CRIAR USUARIOS FAKS.sql`
  - `LIMPAR_DADOS.sql`
  - `OPERA_FULL_SETUP.sql`
  - `TABELA RECRIADA BACKUP.sql`
  - `drop estoque.sql`
  - `tabela recriada com gpt.sql`
  - `asdfasdfasd.sql`

#### `data/RECIBOS_DE_PAGAMENTOS/`
- Função: armazenamento de recibos PDF gerados pelo sistema.
- Conteúdo: arquivos `RECIBO_*.pdf` (dinâmicos por operação).

### 4) `packaging/` (build e instalador)

- `build.py`: script principal de build (Windows/macOS).
- `BUILD_GUIDE.md`: guia completo de build com PyInstaller.
- `parse_pyinstaller_warnings.py`: parser de warnings do PyInstaller.

#### `packaging/windows/`
- `SISTEMA_OPERA.iss`: script Inno Setup do instalador Windows.
- `build_installer.ps1`: automação PowerShell para compilar instalador.
- `prepare_icon.py`: preparo/conversão de ícone para instalador/build.

#### `packaging/macos/`
- `build_installer.sh`: build de instalador para macOS.
- `dmg_settings.py`: parâmetros de geração do DMG.

#### `packaging/release/`
- `build_release.sh`: fluxo de release em shell (Unix/macOS).
- `build_release.ps1`: fluxo de release em PowerShell (Windows).

### 5) `icons/`

Pasta de ícones PNG utilizados em menus e ações da aplicação.

Arquivos presentes:
- `ACABAMENTO.png`
- `BACKUP.png`
- `BANCO DE DADOS.png`
- `CADASTRO_CORTE.png`
- `CALENDARIO.png`
- `CONFIGURACAO.png`
- `CONSULTAR ORDENS.png`
- `DASHBORD.png`
- `DINHEIRO.png`
- `ENGRENAGEM.png`
- `ESTOQUE.png`
- `FABRICA.png`
- `FACÇAO.png`
- `FERRAMENTAS.png`
- `FINALIZAR CORTE.png`
- `FOLHA DE PAPEL.png`
- `IMPRESSORA.png`
- `LUPA.png`
- `MAO DE OBRA.png`
- `MODELOS PRODUZIDOS.png`
- `NOVA_ORDEM.png`
- `ORDEM_CORTE.png`
- `PALETA DE CORES.png`
- `PESSOAS.png`
- `PRODUÇAO.png`
- `RELATORIO 2.png`
- `RELATORIO.png`
- `ROUPA.png`
- `SERVIÇOS EXTERNOS.png`
- `SETA ENTRADA.png`
- `SETA SAIDA.png`
- `TESOURA.png`
- `TROCAR_USUARIO.png`
- `USUARIO.png`
- `USUARIOS.png`

## Build (macOS / Windows)

### Pré-requisitos

- Python 3.x
- PyInstaller instalado no venv
- Consulte `packaging/BUILD_GUIDE.md` para fluxo completo (imports faltantes, requirements, hidden-imports)

### Build macOS

```bash
python packaging/build.py --platform macos
```

Saída: `dist/SistemaOpera.app`

Instalador macOS (duplo clique): `dist/SistemaOpera.pkg` (gerado pelo script `packaging/macos/build_installer.sh`).


### Instalador macOS (duplo clique)

```bash
chmod +x packaging/macos/build_installer.sh
./packaging/macos/build_installer.sh
```

> Agora o padrão do script é **gerar DMG e PKG automaticamente** (sem pular).

Sem perguntas (automático):

```bash
./packaging/macos/build_installer.sh --with-dmg --with-pkg
```

Modo com perguntas (opcional):

```bash
./packaging/macos/build_installer.sh --interactive
```

No final, escolha gerar o **PKG** para ter instalador de dois cliques (`dist/SistemaOpera.pkg`), que instala o app em `/Applications`.
No PKG novo, ao final da instalação aparece **uma janela única** de configuração (visual) para definir **local/rede, host/IP, porta com detecção, banco, usuário, senha e schema**, com botão de **Testar conexão** antes de salvar; o instalador grava `config.json` em `/Library/Application Support/SistemaOpera/` e também no usuário logado.

Desinstalador: o PKG também instala `/Applications/Desinstalar SistemaOpera.command` para remoção completa (app + pastas de configuração).

### Build Windows

```bash
python packaging/build.py --platform windows
```

Saída: `dist/SistemaOpera/SistemaOpera.exe`

### Instalador Windows (Inno Setup)

Use o script em `packaging/windows/SISTEMA_OPERA.iss` após gerar o build.

#### Instalador com configuração de banco (IP + porta)

O script `SISTEMA_OPERA.iss` possui etapa no wizard para configurar o banco:

- Campo de **IP/Host** (localhost ou rede)
- Campo de **Porta**
- Botão **Buscar porta** (testa portas comuns do PostgreSQL)
- Botão **Testar conexão**
- Campos de banco, usuário, senha e schema

Ao concluir a instalação, o instalador grava automaticamente o `config.json` em:

- `%APPDATA%\SistemaOpera\config.json`
- `{app}\INSTALAÇÃO\config.json`

Fluxo recomendado:

1. Gere o executável com `python packaging/build.py --platform windows`.
2. Abra `packaging/windows/SISTEMA_OPERA.iss` no Inno Setup Compiler.
3. Compile o instalador.
4. No assistente, informe IP/porta do banco e clique em **Testar conexão** antes de avançar.

## Arquitetura de atualizacao e migracao

A estrutura atual do projeto passou a separar explicitamente a atualizacao de codigo da aplicacao da atualizacao de estrutura do banco. Alem de `PAGINAS_DO_SISTEMA/`, o projeto agora considera uma pasta dedicada `SCHEMA/` na raiz para concentrar os modulos de schema e migracao.

### Pasta `SCHEMA/`

A pasta `SCHEMA/` deve ficar na raiz do projeto e concentrar os modulos de estrutura do banco, organizados por dominio funcional (e nao por tabela isolada). Estrutura recomendada:

```text
SISTEMA-GUIMMA/
├── SCHEMA/
│   ├── __init__.py
│   ├── SCHEMA_MANAGER.py
│   ├── schema_utils.py
│   ├── schema_core.py
│   ├── schema_usuarios.py
│   ├── schema_modelos.py
│   ├── schema_faccoes.py
│   ├── schema_corte_producao.py
│   ├── schema_pagamentos.py
│   ├── schema_servicos.py
│   ├── schema_estoque.py
│   ├── schema_clientes_compras.py
│   ├── schema_pcp.py
│   ├── schema_custos.py
│   └── schema_relatorios.py
```

Papeis principais:

- `SCHEMA_MANAGER.py`: orquestra a aplicacao de migracoes e chama os modulos de schema.
- `schema_utils.py`: helpers compartilhados (checagem de coluna, indice, SQL utilitario).
- `schema_core.py`: estrutura base do schema e tabela de versionamento.
- Demais `schema_*.py`: tabelas, colunas, indices e ajustes por modulo de negocio.

### Conexao de banco

O acesso ao PostgreSQL continua centralizado em `PAGINAS_DO_SISTEMA/BANCO_DE_DADOS_PG.py`, que ja possui a ordem de conexao por `OPERA_PG_DSN`, `config.json` e fallback por host/porta com autodeteccao. O fluxo de migracao deve reutilizar esse modulo de acesso, e nao um DSN fixo, para manter consistencia com a configuracao real do cliente. Isso se alinha com a logica atual de conexao, que prioriza `OPERA_PG_DSN`, depois `CONFIG["dsn"]`, e por fim host/porta definidos em configuracao. fileciteturn14file7turn14file15

### `schema_version`

A tabela `schema_version` e o registro central da versao aplicada por modulo. O `SCHEMA_MANAGER` deve garantir a existencia dessa tabela e registrar a versao de cada modulo apos a execucao da migracao. A implementacao atual ja contempla essa tabela e o controle de versao por modulo. fileciteturn14file4

## Fluxo de atualizacao do sistema

A tela `PAGINAS_DO_SISTEMA/ATUALIZAR_SISTEMA_usa-es-pt.py` passou a ser tratada como um atualizador hibrido, com duas origens de pacote:

- **Local**: selecao de uma pasta no computador.
- **Online**: pacote ZIP hospedado no Google Drive.

### Estrutura esperada do pacote de atualizacao

O pacote de atualizacao deve ser montado com a seguinte estrutura:

```text
Versao do Sistema/
├── manifest.json
├── PAGINAS_DO_SISTEMA/
│   └── arquivos .py alterados
└── SCHEMA/
    └── arquivos .py de schema alterados
```

Observacoes:

- `PAGINAS_DO_SISTEMA/` e opcional quando a atualizacao for apenas de schema.
- `SCHEMA/` e opcional quando a atualizacao for apenas de telas/logica.
- `manifest.json` e recomendado para informar versao, descricao, data e observacoes.

### Comportamento esperado da tela de atualizacao

A tela de atualizacao deve:

1. Ler a fonte salva anteriormente, quando existir.
2. Fazer a varredura automatica ao abrir a pagina.
3. Listar os arquivos encontrados em uma visualizacao hierarquica.
4. Informar claramente quando faltarem as pastas `PAGINAS_DO_SISTEMA` e/ou `SCHEMA`.
5. Permitir:
   - duplo clique em um arquivo para atualizar apenas aquele item;
   - clique com o botao direito em uma pasta para atualizar a pasta inteira;
   - atualizacao do pacote completo.

Quando houver atualizacao de `SCHEMA/`, o sistema deve chamar `SCHEMA/SCHEMA_MANAGER.py` ao final da copia de arquivos.

### Rollback automatico

Se a copia de arquivos ou a migracao de banco falhar, o atualizador deve restaurar automaticamente o backup da versao anterior. Esse comportamento evita deixar o cliente com arquivos parcialmente atualizados.

## Versionamento de atualizacao

O versionamento do sistema deve ser controlado por dois arquivos:

### `manifest.json`

Fica dentro do pacote de atualizacao e representa a versao que esta chegando.

Exemplo recomendado:

```json
{
  "version": "1.0.1",
  "description": "Correcoes visuais e ajustes de logica",
  "created_at": "2026-03-01 17:45:00",
  "requires_schema": false,
  "notes": [
    "Ajuste de layout em Faccoes",
    "Correcao de botao em Pagamento de Servicos"
  ]
}
```

Campos suportados:

- `version`: versao do pacote.
- `description`: resumo da entrega.
- `created_at`: data/hora de geracao do pacote.
- `requires_schema`: se ha mudanca de estrutura de banco.
- `notes`: observacoes adicionais.

### `update_state.json`

Fica na raiz do sistema instalado e representa a versao atualmente instalada naquela maquina.

Exemplo:

```json
{
  "current_version": "1.0.1"
}
```

### Regra de versao

A versao nao deve ser alterada pela quantidade de arquivos modificados, e sim pelo impacto da mudanca:

- `1.0.x`: correcoes pequenas, ajustes visuais, textos, bugs e melhorias leves.
- `1.1.0`, `1.2.0`, etc.: novas funcionalidades e melhorias funcionais perceptiveis.
- `2.0.0`: mudancas grandes de arquitetura, fluxo ou compatibilidade.

## Instalacao limpa e evolucao do banco

Para instalacao limpa, o fluxo recomendado e:

1. Instalar/configurar o PostgreSQL.
2. Garantir que o banco e o schema existam.
3. Rodar o `SCHEMA_MANAGER` para criar/ajustar a estrutura.
4. Instalar o aplicativo nos clientes.
5. Configurar conexao com o banco em rede.

O app/ferramenta de instalacao de banco em `data/INSTAL_BANCO_APP/` ja trabalha com a selecao automatica dos scripts SQL `1_CRIAR_BANCO.sql`, `2_CRIAR_SCHEMA.sql` e `3_CRIAR_TABELAS.sql`, podendo servir como base para o fluxo inicial de provisionamento do banco. fileciteturn14file10turn14file11

## Observacao operacional importante

Trocar arquivos `.py` no disco nao recarrega automaticamente as telas que ja estao abertas em memoria. Depois de uma atualizacao concluida, o recomendado e orientar o usuario a fechar e reabrir o sistema para carregar a nova versao da interface e das rotinas alteradas.
