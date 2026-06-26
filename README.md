# SISTEMA GUIMMA

Aplicação desktop para gestão de produção (modelos, corte, estoque, pagamentos, relatórios e administração), com interface em CustomTkinter e persistência em PostgreSQL.

---

## Últimas mudanças identificadas (Git)

Levantamento feito a partir dos commits mais recentes da branch `work`:

### 2026-03-26 — `894c74f` — Sincronização local/GitHub
- Evolução importante no relatório de estoque com grande refatoração de `PAGINAS_DO_SISTEMA/RELATORIO_ESTOQUE.py`.
- Inclusão do novo módulo `PAGINAS_DO_SISTEMA/RELATORIO_ESTOQUE_IA.py` para recursos de análise assistida por IA no contexto de estoque.
- Ajustes em `PAGINAS_DO_SISTEMA/ENTRADA_ESTOQUE.py` (fluxos de entrada e consistência de dados).
- Revisões de setup/conexão em `PAGINAS_DO_SISTEMA/SETUP_BANCO.py` e `configurar_postgres.py`.
- Sincronização de arquivos de configuração (`config.json` em diferentes pontos do projeto).

### 2026-03-25 — `95a043f` — Sincronização local/GitHub
- Iterações extensas de protótipos de relatório em:
  - `PAGINAS_DO_SISTEMA/NOVO RELATORIO.py`
  - `PAGINAS_DO_SISTEMA/NOVO RELATORIO QUASE BOM.py`
- Atualização significativa de `PAGINAS_DO_SISTEMA/RELATORIO_ESTOQUE.py`.
- Ajustes em `PAGINAS_DO_SISTEMA/ENTRADA_ESTOQUE.py`.
- Inclusão de memória de contexto IA em `PAGINAS_DO_SISTEMA/ia_memory.json`.
- Mudanças de estrutura SQL em `SCRIPTS/3_CRIAR_TABELAS.sql`.

### 2026-03-24 — `be2840e` — Melhoria de experiência no assistente
- Humanização das respostas do assistente na interface principal.
- Redução de fallback “seco” de banco nas respostas.
- Arquivos centrais alterados:
  - `PAGINAS_DO_SISTEMA/MENU_PRINCIPAL.py`
  - `PAGINAS_DO_SISTEMA/RELATORIO_ESTOQUE.py`

> Nota: os commits de merge de PR entre 2026-03-24 e 2026-03-25 foram excluídos do resumo por serem integrações de branch.

---

## Estrutura real do repositório (atualizada)

```text
SISTEMA-GUIMMA/
├── README.md
├── requirements.txt
├── SistemaOpera.spec
├── OPERA_CONFIG_POSTGRES.spec
├── PAGINAS_DO_SISTEMA/          # Código principal da aplicação
├── SCRIPTS/                     # Scripts SQL de criação/manutenção do banco
├── data/                        # Ferramentas e artefatos auxiliares (instalador de banco, recibos etc.)
├── icons/                       # Ícones usados na interface
├── packaging/                   # Build e instaladores (Windows/macOS)
├── installer_scripts/           # Scripts auxiliares de instalação
├── installer_root/              # Estrutura de apoio para instalador
├── OPERA_SYSTEM/                # Estrutura de runtime/logs
├── logs/                        # Logs da aplicação
├── Versao do Sistema/           # Pacotes de versão/atualização
├── backup_banco/
└── backup_versoes/
```

> Observação: não existe `src/PAGINAS_DO_SISTEMA` neste repositório; a pasta canônica é `PAGINAS_DO_SISTEMA/` na raiz.

---

## Pasta principal: `PAGINAS_DO_SISTEMA/`

### Núcleo e inicialização
- `MAIN.py`
- `MENU_PRINCIPAL.py`
- `LOGUIN.py`
- `SPLASH.py`
- `OPERA_PATHS.py`
- `ATUALIZAR_SISTEMA.py`

### Banco e administração
- `BANCO_DE_DADOS_PG.py`
- `SCHEMA_MANAGER.py`
- `USUARIOS.py`
- `BACKUP.py`
- `database_logger.py`

### Produção, ordens e planejamento
- `NOVA_ORDEM.py`
- `ORDENS_PLANEJADAS.py`
- `PLANEJAMENTO_PRODUCAO.py`
- `CADASTRO_DE_CORTE.py`
- `CONTROLE_ENVIO_CORTES.py`
- `CONTROLE_RETORNO_CORTE.py`
- `FINALIZAR_CORTE_ACABAMENTO.py`
- `RETRABALHO_DEFEITOS.py`

### Cadastros, estoque e financeiro
- `CADASTRAR_MODELO.py`
- `CADASTRO_CLIENTES.py`
- `CADASTRO_FACCOES.py`
- `ENTRADA_ESTOQUE.py`
- `SAIDA_ESTOQUE.py`
- `COMPRAS.py`
- `CONTAS_A_PAGAR.py`
- `PAGAMENTO_SERVICOS.py`
- `FOLHA_PAGAMENTO_SERVICOS.py`
- `FECHAMENTO_MENSAL.py`
- `PRECIFICACAO_PRODUTO.py`

### Relatórios e utilitários de UI
- `DASHBOARD.py`
- `RELATORIO_ESTOQUE.py`
- `RELATORIO_ESTOQUE_IA.py`  ← cérebro/engine de IA separado da tela
- `RELATORIO_ACABAMENTO.py`
- `RELATORIO_ENVIO_DETALHADO.py`
- `RELATORIO_MODELOS_PRODUZIDOS.py`
- `RELATORIO_CUSTOS_REAIS.py`
- `RELATORIO_SERVICOS_EXTERNOS.py`
- `IMPRIMIR_FICHAS_TECNICAS.py`
- `RECIBOS_PAGAMENTOS.py`
- `UI_TREEVIEW_OPERA.py`
- `TEMAS.py`
- `I18N_PAGE_ADAPTER.py`
- `route_map.json`

---

## Arquitetura atual do Relatório de Estoque com IA

Sim — agora o “cérebro” de IA do relatório de estoque está desacoplado da página principal:

- `RELATORIO_ESTOQUE.py`: responsável por UI, filtros, eventos da tela e integração com os componentes visuais.
- `RELATORIO_ESTOQUE_IA.py`: responsável por lógica de IA, interpretação de perguntas/comandos e geração de respostas/contexto do relatório.

Esse desacoplamento melhora manutenção, testes e evolução do assistente sem poluir o arquivo da tela.

---

## Banco de dados

Scripts SQL principais na raiz em `SCRIPTS/`:
- `1_CRIAR_BANCO.sql`
- `2_CRIAR_SCHEMA.sql`
- `3_CRIAR_TABELAS.sql`
- `APAGAR_TUDO.sql`

`3_CRIAR_TABELAS.sql` contém criação de tabelas, índices e objetos auxiliares do sistema (usuários, produção, estoque, serviços, planejamento e relatórios).

---

## Build e empacotamento

### Pré-requisitos
- Python 3.x
- Dependências em `requirements.txt`
- PyInstaller

### Build Windows
```bash
python packaging/build.py --platform windows
```

### Build macOS
```bash
python packaging/build.py --platform macos
```

### Instaladores
- Windows: `packaging/windows/SISTEMA_OPERA.iss`
- macOS: `packaging/macos/build_installer.sh`

---

## Observações de manutenção

- Os nomes dos módulos em rotas seguem padrão canônico `*.py` (sem sufixos legados de localidade).
- Após atualização de arquivos Python, reinicie a aplicação para recarregar módulos em memória.
- Para mudanças de banco, mantenha sincronizados:
  1. `SCRIPTS/3_CRIAR_TABELAS.sql`
  2. scripts de instalação em `data/INSTAL_BANCO_APP/scripts/`
