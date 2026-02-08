# Guia de instaladores (Windows e macOS)

Este guia descreve como gerar o executável e o instalador do SISTEMA OPERA para **Windows** e **macOS**.

## Pré-requisitos

1. **Python 3.10+** instalado.
2. Dependências do projeto e ferramentas de build:

```bash
pip install -r requirements.txt
pip install pyinstaller
```

3. O ícone deve existir em:

```
PAGINAS_DO_SISTEMA/ICONE_SISTEMA.png
```

> No Windows, é recomendado ter também `Pillow` para gerar automaticamente o `.ico`:

```bash
pip install pillow
```

## Windows (PyInstaller + Inno Setup)

### 1) Gerar executável com PyInstaller

```powershell
python packaging/build.py --platform windows
```

Saída esperada:

```
dist/SistemaOpera/SistemaOpera.exe
```

### 2) Gerar instalador com Inno Setup

- Instale o **Inno Setup** (precisa do `iscc.exe` disponível no PATH).
- Execute:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/windows/build_installer.ps1
```

O instalador será gerado **na raiz do repositório** com o nome:

```
Instalador_SISTEMA OPERA.exe
```

## macOS (PyInstaller + dmgbuild)

### 1) Gerar o app com PyInstaller

```bash
python3 packaging/build.py --platform macos
```

Saída esperada:

```
dist/SistemaOpera.app
```

### 2) Gerar o DMG

```bash
pip install dmgbuild
bash packaging/macos/build_installer.sh
```

O DMG será gerado **na raiz do repositório** com o nome:

```
SISTEMA_OPERA.dmg
```

## Dicas

- Se o instalador não incluir o ícone no Windows, verifique se o arquivo `.ico` foi criado em:

```
PAGINAS_DO_SISTEMA/ICONE_SISTEMA.ico
```

- Se ocorrerem erros no PyInstaller, rode com `--clean` (já está embutido no `build.py`).
