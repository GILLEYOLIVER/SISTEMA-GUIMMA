#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VERSION="${GUIMMA_VERSION:-${1:-1.1.1}}"
ARCHITECTURE="${GUIMMA_ARCH:-${2:-x64}}"
REQUIRE_WINDOWS="${GUIMMA_REQUIRE_WINDOWS:-0}"
WINDOWS_EXE_PATH="${GUIMMA_WINDOWS_EXE:-}"

if [[ "$ARCHITECTURE" != "x64" && "$ARCHITECTURE" != "x86" ]]; then
  echo "ERRO: Arquitetura invalida: $ARCHITECTURE (use x64 ou x86)"
  exit 4
fi

if [[ "${3:-}" == "--require-windows" ]]; then
  REQUIRE_WINDOWS="1"
fi

# 1) Gera app + instaladores macOS com nome versionado em dist/installers/macos
bash packaging/macos/build_installer.sh --version "$VERSION" --with-dmg --with-pkg

REL_DIR="$ROOT_DIR/dist/release/Sistema_Guimma_${VERSION}"
MAC_DIR="$REL_DIR/macos"
WIN_DIR="$REL_DIR/windows"
CONFIG_PY="$ROOT_DIR/configurar_postgres.py"

rm -rf "$REL_DIR"
mkdir -p "$MAC_DIR" "$WIN_DIR"

# WINDOWS: installer oficial
WINDOWS_EXE_FOUND=0
if [[ -n "$WINDOWS_EXE_PATH" && -f "$WINDOWS_EXE_PATH" ]]; then
  cp -f "$WINDOWS_EXE_PATH" "$WIN_DIR/"
  WINDOWS_EXE_FOUND=1
elif [[ -f "$ROOT_DIR/dist/Sistema_Guimma_Setup_${ARCHITECTURE}.exe" ]]; then
  cp -f "$ROOT_DIR/dist/Sistema_Guimma_Setup_${ARCHITECTURE}.exe" "$WIN_DIR/"
  WINDOWS_EXE_FOUND=1
elif [[ -f "$ROOT_DIR/dist/Sistema_Guimma_Setup.exe" ]]; then
  cp -f "$ROOT_DIR/dist/Sistema_Guimma_Setup.exe" "$WIN_DIR/"
  WINDOWS_EXE_FOUND=1
elif compgen -G "$ROOT_DIR/dist/installers/windows/*.exe" > /dev/null; then
  cp -f "$ROOT_DIR/dist/installers/windows/"*.exe "$WIN_DIR/"
  WINDOWS_EXE_FOUND=1
fi

if [[ "$REQUIRE_WINDOWS" == "1" ]] && ! compgen -G "$WIN_DIR/*.exe" > /dev/null; then
  echo "ERRO: Nenhum instalador Windows (.exe) encontrado."
  exit 2
fi

# WINDOWS: CONFIGURAR_BANCO.exe
if [[ -f "$ROOT_DIR/dist/SistemaGuimma/CONFIGURAR_BANCO.exe" ]]; then
  cp -f "$ROOT_DIR/dist/SistemaGuimma/CONFIGURAR_BANCO.exe" "$WIN_DIR/"
elif [[ -f "$ROOT_DIR/dist/windows/CONFIGURAR_BANCO.exe" ]]; then
  cp -f "$ROOT_DIR/dist/windows/CONFIGURAR_BANCO.exe" "$WIN_DIR/"
else
  if [[ "$REQUIRE_WINDOWS" == "1" || "$WINDOWS_EXE_FOUND" == "1" ]]; then
    echo "ERRO: CONFIGURAR_BANCO.exe nao encontrado."
    exit 6
  fi
  echo "AVISO: CONFIGURAR_BANCO.exe nao encontrado; release macOS seguira sem executaveis Windows."
fi

# WINDOWS: CONFIGURAR_POSTGRES.exe
CONFIG_POSTGRES_EXE=""
for c in \
  "$ROOT_DIR/dist/Sistema_Guimma_${VERSION}_${ARCHITECTURE}/CONFIGURAR_POSTGRES.exe" \
  "$ROOT_DIR/dist/installers/unified/Sistema_Guimma_${VERSION}_${ARCHITECTURE}/CONFIGURAR_POSTGRES.exe" \
  "$ROOT_DIR/dist/SistemaGuimma/CONFIGURAR_POSTGRES.exe"
do
  if [[ -f "$c" ]]; then
    CONFIG_POSTGRES_EXE="$c"
    break
  fi
done

if [[ -z "$CONFIG_POSTGRES_EXE" ]]; then
  if [[ "$REQUIRE_WINDOWS" == "1" || "$WINDOWS_EXE_FOUND" == "1" ]]; then
    echo "ERRO: CONFIGURAR_POSTGRES.exe nao encontrado. Gere antes com:"
    echo "   powershell -ExecutionPolicy Bypass -File packaging/windows/build_unified_package.ps1 -Python python -Version ${VERSION} -Architecture ${ARCHITECTURE} -SkipInstallerBuild"
    exit 5
  fi
  echo "AVISO: CONFIGURAR_POSTGRES.exe nao encontrado; release macOS seguira sem executaveis Windows."
else
  cp -f "$CONFIG_POSTGRES_EXE" "$WIN_DIR/"
fi

# SCRIPTS em ambas as pastas
if [[ ! -d "$ROOT_DIR/SCRIPTS" ]]; then
  echo "ERRO: Pasta SCRIPTS nao encontrada."
  exit 7
fi
cp -R "$ROOT_DIR/SCRIPTS" "$WIN_DIR/SCRIPTS"
cp -R "$ROOT_DIR/SCRIPTS" "$MAC_DIR/SCRIPTS"

# MAC: artefatos similares
if [[ -f "$ROOT_DIR/dist/installers/macos/Sistema Guimma ${VERSION} macOS.dmg" ]]; then
  cp -f "$ROOT_DIR/dist/installers/macos/Sistema Guimma ${VERSION} macOS.dmg" "$MAC_DIR/"
fi
if [[ -f "$ROOT_DIR/dist/installers/macos/Sistema Guimma ${VERSION} macOS.pkg" ]]; then
  cp -f "$ROOT_DIR/dist/installers/macos/Sistema Guimma ${VERSION} macOS.pkg" "$MAC_DIR/"
fi

for app in \
  "$ROOT_DIR/dist/Sistema Guimma.app" \
  "$ROOT_DIR/dist/Sistema Guimma Licenca.app" \
  "$ROOT_DIR/dist/SistemaGuimma/CONFIGURAR_BANCO.app" \
  "$ROOT_DIR/dist/SistemaGuimma/CONFIGURAR_POSTGRES.app"
do
  if [[ -d "$app" ]]; then
    cp -R "$app" "$MAC_DIR/"
  fi
done

if [[ -f "$ROOT_DIR/PAGINAS_DO_SISTEMA/SETUP_BANCO.py" ]]; then
  cp -f "$ROOT_DIR/PAGINAS_DO_SISTEMA/SETUP_BANCO.py" "$MAC_DIR/CONFIGURAR_BANCO.py"
fi
if [[ -f "$ROOT_DIR/configurar_postgres.py" ]]; then
  cp -f "$ROOT_DIR/configurar_postgres.py" "$MAC_DIR/CONFIGURAR_POSTGRES.py"
fi

cat > "$MAC_DIR/CONFIGURAR_BANCO.command" <<'CMD'
#!/usr/bin/env bash
cd "$(dirname "$0")"
python3 CONFIGURAR_BANCO.py
CMD

cat > "$MAC_DIR/CONFIGURAR_POSTGRES.command" <<'CMD'
#!/usr/bin/env bash
cd "$(dirname "$0")"
python3 CONFIGURAR_POSTGRES.py
CMD
chmod +x "$MAC_DIR/CONFIGURAR_BANCO.command" "$MAC_DIR/CONFIGURAR_POSTGRES.command"

ZIP_OUT="$ROOT_DIR/dist/Sistema_Guimma_${VERSION}_INSTALLER.zip"
rm -f "$ZIP_OUT"

# ZIP espelha a pasta Windows quando houver executaveis Windows.
if compgen -G "$WIN_DIR/*.exe" > /dev/null; then
ROOT_DIR="$ROOT_DIR" VERSION="$VERSION" python - <<'PYZIP'
from pathlib import Path
import os, zipfile
root = Path(os.environ['ROOT_DIR'])
version = os.environ['VERSION']
win_dir = root / 'dist' / 'release' / f'Sistema_Guimma_{version}' / 'windows'
zip_out = root / 'dist' / f'Sistema_Guimma_{version}_INSTALLER.zip'
if not win_dir.exists():
    raise SystemExit(f"Windows folder not found: {win_dir}")
with zipfile.ZipFile(zip_out, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for p in win_dir.rglob('*'):
        if p.is_file():
            zf.write(p, p.relative_to(win_dir))
print(zip_out)
PYZIP
else
  echo "AVISO: ZIP Windows nao gerado porque nao ha executaveis Windows em $WIN_DIR."
fi

if [[ -f "$ZIP_OUT" ]]; then
  echo "OK: Pacote unico gerado: $ZIP_OUT"
  echo "ZIP espelha exatamente o conteudo da pasta windows"
fi
echo "Windows: SCRIPTS + CONFIGURAR_BANCO.exe + CONFIGURAR_POSTGRES.exe + instalador oficial"
echo "macos:   PKG/DMG + apps compilados + SCRIPTS + comandos auxiliares"
