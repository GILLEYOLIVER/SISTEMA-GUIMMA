# SISTEMA OPERA

Aplicação desktop para gestão de produção (modelos, corte, estoque, pagamentos, relatórios e administração), com interface em CustomTkinter e persistência em PostgreSQL.

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

