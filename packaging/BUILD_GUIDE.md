# Pacote de build completo (PyInstaller + requirements)

Este guia descreve um fluxo completo para:

1. **Descobrir imports faltantes**.
2. **Travar dependências em `requirements.txt`**.
3. **Ajustar PyInstaller** com `hidden-import`/`collect_submodules`.

## 1) Descobrir imports faltantes

O PyInstaller gera um arquivo `warn-*.txt` com módulos ausentes. Use o build com
debug de imports:

```bash
python packaging/build.py --platform macos --pyinstaller-args --debug=imports
```

> Dica: também funciona no Windows (`--platform windows`).

Isso cria `build/SistemaOpera/warn-SistemaOpera.txt` (nome pode variar).

Para extrair os imports ausentes e gerar sugestões:

```bash
python packaging/parse_pyinstaller_warnings.py build/SistemaOpera/warn-SistemaOpera.txt
```

O script imprime:

- `--hidden-import` (para uso direto na CLI).
- `collect_submodules` (para uso no `SistemaOpera.spec`).

## 2) Travar dependências em `requirements.txt`

O arquivo `requirements.txt` na raiz do repo mantém as versões fixas. Para atualizar:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
pip freeze > requirements.txt
```

> Use esse fluxo sempre que adicionar/remover bibliotecas.

## 3) Ajustar PyInstaller (hidden-import/collect)

Você tem duas opções:

### Opção A — Usar o `SistemaOpera.spec` (recomendado para builds completos)

1. Adicione os módulos ausentes em `hiddenimports` dentro do `SistemaOpera.spec`.
2. Execute:

```bash
python packaging/build.py --platform macos --spec SistemaOpera.spec
```

### Opção B — Usar argumentos diretos no build.py

Você pode passar `--hidden-import` diretamente:

```bash
python packaging/build.py --platform windows --pyinstaller-args --hidden-import=fitz --hidden-import=PyQt5
```

> Se o app usa imports dinâmicos, prefira `collect_submodules` no spec.


> Importante: artefatos binários (`dist/`, `build/`, `.dmg`, `.exe`, `.zip`) não devem ser versionados no Git; publique-os apenas como artefatos de release.

## Checklist rápido

- [ ] Rodar build com `--debug=imports` e revisar `warn-*.txt`.
- [ ] Atualizar `SistemaOpera.spec` com `collect_submodules`.
- [ ] Manter `requirements.txt` travado.
- [ ] Repetir o build limpo (`--clean`) até não haver warnings relevantes.


## Pacote completo (macOS + Windows no mesmo ZIP)

No macOS/Linux, use:

```bash
bash packaging/release/build_release.sh 1.0.0 --require-windows
```

Se o `.exe` do Windows foi gerado em outra máquina, informe o caminho:

```bash
OPERA_WINDOWS_EXE=/caminho/SISTEMA_OPERA_1.0.0_setup.exe \
  bash packaging/release/build_release.sh 1.0.0 --require-windows
```

O script aborta com erro se `--require-windows` estiver ativo e nenhum `.exe` for encontrado.
