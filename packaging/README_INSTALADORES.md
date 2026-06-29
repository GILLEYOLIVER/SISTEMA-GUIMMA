# Instaladores do Sistema Guimma

Esta pasta centraliza o fluxo atual de build, empacotamento e release.

## Modelo de Entrega

Em clientes com rede, existem dois papeis:

- Servidor: recebe PostgreSQL, banco `BANCO_OPERA`, schema `opera`, regras de rede e backup.
- Cliente/estacao: recebe o Sistema Guimma e aponta para o IP/porta do servidor.

Apps do pacote:

- `Sistema Guimma`
- `Sistema Guimma Licenca`
- `CONFIGURAR_BANCO`
- `CONFIGURAR_POSTGRES`

O app `Sistema Guimma Licencas Admin` e privado e nao entra no instalador de cliente.

## Icones Oficiais

- Sistema: `icons/ICONE_SISTEMA.icns` e `icons/ICONE_SISTEMA.ico`.
- Licenciador cliente: `icons/ICONE_LICENCIADOR.icns` e `icons/ICONE_LICENCIADOR.ico`.
- Admin licencas: `icons/ICONE_LICENCA_ADMIN.icns` e `icons/ICONE_LICENCA_ADMIN.ico`.
- PostgreSQL: `icons/PG_ICON.ico`.

## macOS

```bash
cd /Users/gilleydeoliveiraguimaraes/PycharmProjects/SISTEMA-GUIMMA
PYTHON_BIN=.venv/bin/python ./packaging/macos/build_installer.sh --version 1.1.1 --with-dmg --with-pkg
```

Saidas:

```text
dist/Sistema Guimma.app
dist/Sistema Guimma Licenca.app
dist/SistemaGuimma/CONFIGURAR_BANCO.app
dist/SistemaGuimma/CONFIGURAR_POSTGRES.app
dist/installers/macos/Sistema Guimma 1.1.1 macOS.pkg
dist/installers/macos/Sistema Guimma 1.1.1 macOS.dmg
```

O PKG instala todos os apps em `/Applications`.

## Windows

Rodar no Windows com Python e Inno Setup 6.

```powershell
cd C:\CAMINHO\PARA\SISTEMA-GUIMMA
powershell -ExecutionPolicy Bypass -File packaging\windows\build_installer.ps1 -Python python -Version 1.1.1 -Architecture x64
```

Saida:

```text
dist\Sistema_Guimma_Setup_x64.exe
```

O instalador Windows inclui:

- `SistemaGuimma.exe`
- `SistemaGuimmaLicenca.exe`
- `CONFIGURAR_BANCO.exe`
- `CONFIGURAR_POSTGRES.exe`
- `SCRIPTS\`
- icones oficiais

Pacote unificado:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build_unified_package.ps1 -Python python -Version 1.1.1 -Architecture x64
```

Saida:

```text
dist\Sistema_Guimma_1.1.1_x64\
```

## Release

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\release\build_release.ps1 -Python python -Version 1.1.1 -Architecture x64
```

Mac:

```bash
GUIMMA_VERSION=1.1.1 GUIMMA_REQUIRE_WINDOWS=0 ./packaging/release/build_release.sh
```

## Cuidados

- Nao enviar `Sistema Guimma Licencas Admin` para cliente.
- Nao enviar `.dev.vars`.
- Nao enviar token Cloudflare.
- Nao versionar `build/` e `dist/`.
- Testar instalador em maquina limpa quando possivel.
