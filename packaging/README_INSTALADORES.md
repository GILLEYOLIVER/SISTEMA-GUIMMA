# Instaladores do Sistema Guimma

Esta pasta centraliza o fluxo atual de build e instalacao.

## Modelo de entrega

Para clientes com rede, o ideal e trabalhar com dois papeis:

- Servidor: maquina que recebe PostgreSQL, banco `BANCO_OPERA`, schema `opera`, regras de acesso de rede e backup.
- Cliente/estacao: maquinas da rede que recebem apenas o Sistema Guimma e apontam para o IP/porta do servidor pelo configurador.

O configurador visual atual fica em `PAGINAS_DO_SISTEMA/SETUP_BANCO.py`. Ele valida conexao local/rede e grava o `config.json` correto para o usuario. A rotina `configurar_postgres.py` continua sendo a ferramenta administrativa para preparar PostgreSQL no servidor.

## Saidas esperadas

```text
dist/
├── Sistema Guimma.app
├── Sistema Guimma.dmg
├── Sistema Guimma.pkg
├── installers/
│   ├── macos/
│   │   ├── Sistema Guimma <versao> macOS.dmg
│   │   └── Sistema Guimma <versao> macOS.pkg
│   └── windows/
└── release/
```

No Windows, o pacote final deve conter:

- `Sistema_Guimma_Setup_x64.exe` ou `Sistema_Guimma_Setup_x86.exe`
- `CONFIGURAR_BANCO.exe`
- `CONFIGURAR_POSTGRES.exe`
- pasta `SCRIPTS/`
- icones em `icons/`

## Comandos

macOS:

```bash
PYTHON_BIN=.venv/bin/python ./packaging/macos/build_installer.sh --version 1.0.0 --with-dmg --with-pkg
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build_installer.ps1 -Python python -Version 1.0.0 -Architecture x64
powershell -ExecutionPolicy Bypass -File packaging\windows\build_unified_package.ps1 -Python python -Version 1.0.0 -Architecture x64
```

Release:

```bash
GUIMMA_VERSION=1.0.0 GUIMMA_REQUIRE_WINDOWS=0 ./packaging/release/build_release.sh
```

O build Windows completo deve ser executado no Windows, pois depende do Inno Setup.
