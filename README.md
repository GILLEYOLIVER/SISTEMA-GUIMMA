# SISTEMA OPERA

Este repositório contém o aplicativo desktop **Sistema Opera**, scripts de build/instalador e dados auxiliares.

> **Importante sobre estrutura:** a imagem de referência mostra `src/PAGINAS_DO_SISTEMA`, porém neste repositório a pasta de código está atualmente em `PAGINAS_DO_SISTEMA/` (na raiz).

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
- `BANCO_DADOS_FABRICA.py`: rotinas de banco vinculadas ao contexto de fábrica.
- `USUARIOS.py`: cadastro/gestão de usuários.
- `ATUALIZAR_SISTEMA.py`: rotinas de atualização do sistema.
- `BACKUP.py`: rotinas de backup.

#### Cadastros e produção
- `CADASTRAR_MODELO.py`: cadastro de modelos.
- `NOVA CADASTRO MODELOS.py`: versão/fluxo alternativo de cadastro de modelos.
- `CADASTRO_CLIENTES.py`: cadastro de clientes.
- `CADASTRO_FACCOES.py`: cadastro de facções.
- `CADASTRO_DE_CORTE.py`: cadastro de ordens/informações de corte.
- `NOVA_ORDEM.py`: criação de nova ordem.
- `PLANEJAMENTO_PRODUCAO.py`: planejamento de produção.
- `MRP_PLANEJAMENTO.py`: MRP e planejamento de materiais.
- `FINALIZAR_CORTE_ACABAMENTO.py`: finalização de corte/acabamento.
- `CONTROLE_ENVIO_CORTES.py`: controle de envio de cortes.
- `CONTROLE_RETORNO_CORTE.py`: controle de retorno de cortes.
- `RETRABALHO_DEFEITOS.py`: gestão de retrabalho e defeitos.

#### Estoque, compras e financeiro
- `ENTRADA_ESTOQUE.py`: entradas de estoque.
- `SAIDA_ESTOQUE.py`: saídas de estoque.
- `RELATORIO_ESTOQUE.py`: relatórios de estoque.
- `COMPRAS.py`: processo de compras.
- `CONTAS_A_PAGAR.py`: contas a pagar.
- `ADIANTAMENTO_PAGE.py`: registro/controle de adiantamentos.
- `ADIANTAMENTO_PENDENTE.py`: pendências de adiantamentos.
- `PAGAMENTO_SERVICOS.py`: pagamento de serviços.
- `FOLHA_PAGAMENTO_SERVICOS.py`: folha/pagamentos de serviços.
- `FECHAMENTO_MENSAL.py`: fechamento mensal financeiro.
- `PRECIFICACAO_PRODUTO.py`: precificação de produto.

#### Consultas, relatórios e impressão
- `CONSULTAR_ORDENS.py`: consulta de ordens.
- `CONSULTAR_SERVICOS.py`: consulta de serviços.
- `RELATORIO_ACABAMENTO.py`: relatório de acabamento.
- `RELATORIO_CUSTOS_REAIS.py`: relatório de custos reais.
- `RELATORIO_ENVIO_DETALHADO.py`: relatório detalhado de envios.
- `RELATORIO_MODELOS_PRODUZIDOS.py`: relatório de modelos produzidos.
- `RELATORIO_SERVICOS_EXTERNOS.py`: relatório de serviços externos.
- `IMPRIMIR_FICHAS_TECNICAS.py`: impressão de fichas técnicas.
- `REIMPRIMIR-ORDENS-DE-CORTE.py`: reimpressão de ordens de corte.
- `RECIBOS_PAGAMENTOS.py`: emissão/controle de recibos de pagamentos.
- `UI_TREEVIEW_OPERA.py`: componente de visualização em árvore (treeview).
- `DASHBOARD.py`: painel/indicadores do sistema.

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

Sem perguntas (automático):

```bash
./packaging/macos/build_installer.sh --with-dmg --with-pkg
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
