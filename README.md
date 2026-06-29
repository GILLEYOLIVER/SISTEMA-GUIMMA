# Sistema Guimma

Aplicacao desktop para gestao de producao de moda/confeccao: modelos, estoque, prestadores, ordens de corte, envio/retorno de servicos, pagamentos, relatorios, banco PostgreSQL e licenciamento mensal por cliente.

## Estrutura Principal

```text
SISTEMA-GUIMMA/
├── PAGINAS_DO_SISTEMA/          # Telas e regras principais do sistema
├── SCRIPTS/                     # SQL oficial: 1 banco, 2 schema, 3 tabelas
├── licenciamento/               # Licenciador do cliente, agente e admin privado
├── servidor_licencas_cloudflare/# Worker/API/painel web de licencas
├── packaging/                   # Scripts de build macOS/Windows/release
├── MANUAIS_DO_SISTEMA/          # Manuais de instalacao, licenca e entrega
├── icons/                       # Icones oficiais dos apps
├── data/                        # Dados auxiliares empacotados
└── arquivos_obsoletos/          # Itens antigos fora do fluxo atual
```

`build/`, `dist/`, caches, logs e instaladores gerados localmente nao sao versionados.

## Apps Gerados

- `Sistema Guimma`: app principal.
- `Sistema Guimma Licenca`: licenciador do cliente, instalado junto com o sistema.
- `CONFIGURAR_BANCO`: configurador de conexao local/rede.
- `CONFIGURAR_POSTGRES`: preparador do PostgreSQL e dos scripts `1 -> 2 -> 3`.
- `Sistema Guimma Licencas Admin`: app privado, somente para administracao interna.

Icones oficiais:

- Sistema: `icons/ICONE_SISTEMA.icns` e `icons/ICONE_SISTEMA.ico`.
- Licenciador cliente: `icons/ICONE_LICENCIADOR.icns` e `icons/ICONE_LICENCIADOR.ico`.
- Admin licencas: `icons/ICONE_LICENCA_ADMIN.icns` e `icons/ICONE_LICENCA_ADMIN.ico`.
- PostgreSQL: `icons/PG_ICON.ico`.

## Banco de Dados

Banco padrao:

```text
BANCO_OPERA
```

Schema padrao:

```text
opera
```

Scripts oficiais:

```text
SCRIPTS/1_CRIAR_BANCO.sql
SCRIPTS/2_CRIAR_SCHEMA.sql
SCRIPTS/3_CRIAR_TABELAS.sql
SCRIPTS/APAGAR_TUDO.sql
```

Em instalacao servidor/local, use o `CONFIGURAR_POSTGRES` para instalar/preparar PostgreSQL e executar os scripts na sequencia `1 -> 2 -> 3`.

## Licenciamento

O cliente usa email como identificacao. A licenca fica ativa em apenas 1 computador por vez. Para trocar de maquina, o cliente desativa no computador antigo ou o administrador usa `Liberar computador` no painel web.

Painel administrativo:

```text
https://sistema-guimma-licencas.sistemaguimma.workers.dev/admin
```

Credenciais/tokens administrativos nunca devem ser enviados para clientes.

## Build Rapido

### macOS

```bash
cd /Users/gilleydeoliveiraguimaraes/PycharmProjects/SISTEMA-GUIMMA
PYTHON_BIN=.venv/bin/python ./packaging/macos/build_installer.sh --version 1.1.1 --with-dmg --with-pkg
```

Saidas principais:

```text
dist/Sistema Guimma.app
dist/Sistema Guimma Licenca.app
dist/SistemaGuimma/CONFIGURAR_BANCO.app
dist/SistemaGuimma/CONFIGURAR_POSTGRES.app
dist/installers/macos/Sistema Guimma 1.1.1 macOS.pkg
dist/installers/macos/Sistema Guimma 1.1.1 macOS.dmg
```

Para entrega ao cliente, use o `.pkg` ou `.dmg`. Nao entregue `.app` solto
fora de `/Applications`.

### Windows

Rodar em um computador Windows com Python da arquitetura desejada e Inno Setup 6 instalado.

```powershell
cd C:\CAMINHO\PARA\SISTEMA-GUIMMA
powershell -ExecutionPolicy Bypass -File packaging\windows\build_installer.ps1 -Python python -Version 1.1.1 -Architecture x64
```

Saida principal:

```text
dist\Sistema_Guimma_Setup_x64.exe
```

Pacote unificado Windows:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build_unified_package.ps1 -Python python -Version 1.1.1 -Architecture x64
```

## Manuais Importantes

- `MANUAIS_DO_SISTEMA/00_LEIA_PRIMEIRO.txt`
- `MANUAIS_DO_SISTEMA/01_INSTALAR_SISTEMA_MAC.txt`
- `MANUAIS_DO_SISTEMA/02_INSTALAR_SISTEMA_WINDOWS.txt`
- `MANUAIS_DO_SISTEMA/03_INSTALAR_POSTGRESQL_SERVIDOR.txt`
- `MANUAIS_DO_SISTEMA/06_USAR_LICENCIADOR_DO_CLIENTE.txt`
- `MANUAIS_DO_SISTEMA/07_USAR_PAINEL_WEB_DE_LICENCAS.txt`
- `MANUAIS_DO_SISTEMA/09_GERAR_INSTALADORES.txt`
- `MANUAIS_DO_SISTEMA/13_SCRIPTS_GERAR_INSTALADORES_TODOS_APPS.txt`

## Estado de Maquina Limpa

Para simular computador de cliente no Mac, remova apps, dados locais, agente de licenca, instaladores da Mesa e PostgreSQL local. O projeto em `PycharmProjects/SISTEMA-GUIMMA` nao deve ser apagado.

O roteiro completo fica em:

```text
MANUAIS_DO_SISTEMA/14_LIMPEZA_TESTE_MAQUINA_CLIENTE_MAC.txt
```
