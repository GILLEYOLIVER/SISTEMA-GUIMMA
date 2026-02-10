# SISTEMA OPERA

Estrutura do projeto reorganizada para facilitar manutenção e build (Windows/macOS).

## Estrutura

```
SISTEMA-GUIMMA/
  src/
    PAGINAS_DO_SISTEMA/   # código e assets do app
  data/
    BANCO_DE_DADOS/
    INSTAL_BANCO_APP/
    RECIBOS_DE_PAGAMENTOS/
  packaging/             # scripts de build/instalador
  icons/
  COMMIT (não empacotado)
```

## Build (macOS / Windows)

### Pré-requisitos

- Python 3.x
- PyInstaller instalado no venv
- Consulte `packaging/BUILD_GUIDE.md` para fluxo completo (imports faltantes, requirements, hidden-imports).

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

#### Instalador com configuração de banco (IP + porta)

O script `SISTEMA_OPERA.iss` já possui uma etapa no assistente para configurar o banco durante a instalação:

- Campo de **IP/Host** (localhost ou rede)
- Campo de **Porta**
- Botão **Buscar porta** (testa portas comuns do PostgreSQL)
- Botão **Testar conexão**
- Campos de banco, usuário, senha e schema

Ao concluir a instalação, o instalador grava automaticamente o `config.json` em:

- `%APPDATA%\SistemaOpera\config.json`
- `{app}\INSTALAÇÃO\config.json` (pasta de instalação)

Fluxo recomendado:

1. Gere o executável com `python packaging/build.py --platform windows`.
2. Abra `packaging/windows/SISTEMA_OPERA.iss` no Inno Setup Compiler.
3. Compile o instalador.
4. Durante a instalação, informe o IP e a porta do banco e use **Testar conexão** antes de avançar.

## Observações

- Assets seguem empacotados via PyInstaller (pasta `PAGINAS_DO_SISTEMA`)
- Caminhos internos resolvidos via `OPERA_PATHS` para pasta gravável do usuário
