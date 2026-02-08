# SISTEMA OPERA

Estrutura do projeto reorganizada para facilitar manutenção e build (Windows/macOS).

## Estrutura

```
SISTEMA-GUIMMA/
  src/
    PAGINAS_DO_SISTEMA/   # código e assets do app
  data/
    BANCO_DE_DADOS/
    COMMIT/
    INSTAL_BANCO_APP/
    RECIBOS_DE_PAGAMENTOS/
  packaging/             # scripts de build/instalador
  icons/
```

## Build (macOS / Windows)

### Pré-requisitos

- Python 3.x
- PyInstaller instalado no venv

### Build macOS

```bash
python packaging/build.py --platform macos
```

Saída: `dist/SistemaOpera.app`

### Build Windows

```bash
python packaging/build.py --platform windows
```

Saída: `dist/SistemaOpera/SistemaOpera.exe`

### Instalador Windows (Inno Setup)

Use o script em `packaging/windows/SISTEMA_OPERA.iss` após gerar o build.

## Observações

- Assets seguem empacotados via PyInstaller (pasta `PAGINAS_DO_SISTEMA`)
- Caminhos internos resolvidos via `OPERA_PATHS` para pasta gravável do usuário
