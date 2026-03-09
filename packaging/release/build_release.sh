#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VERSION="${OPERA_VERSION:-${1:-1.0.0}}"
ARCHITECTURE="${OPERA_ARCH:-${2:-x64}}"
REQUIRE_WINDOWS="${OPERA_REQUIRE_WINDOWS:-0}"
WINDOWS_EXE_PATH="${OPERA_WINDOWS_EXE:-}"

if [[ "$ARCHITECTURE" != "x64" && "$ARCHITECTURE" != "x86" ]]; then
  echo "ERRO: Arquitetura invalida: $ARCHITECTURE (use x64 ou x86)"
  exit 4
fi

if [[ "${3:-}" == "--require-windows" ]]; then
  REQUIRE_WINDOWS="1"
fi

# 1) Gera DMG
bash packaging/macos/build_installer.sh "$VERSION"

REL_DIR="$ROOT_DIR/dist/release/SISTEMA_OPERA_${VERSION}"
MAC_DIR="$REL_DIR/macos"
WIN_DIR="$REL_DIR/windows"

rm -rf "$REL_DIR"
mkdir -p "$MAC_DIR" "$WIN_DIR"

# WINDOWS: installer oficial
if [[ -n "$WINDOWS_EXE_PATH" && -f "$WINDOWS_EXE_PATH" ]]; then
  cp -f "$WINDOWS_EXE_PATH" "$WIN_DIR/"
elif [[ -f "$ROOT_DIR/dist/SistemaOpera_Setup_${ARCHITECTURE}.exe" ]]; then
  cp -f "$ROOT_DIR/dist/SistemaOpera_Setup_${ARCHITECTURE}.exe" "$WIN_DIR/"
elif [[ -f "$ROOT_DIR/dist/SistemaOpera_Setup.exe" ]]; then
  cp -f "$ROOT_DIR/dist/SistemaOpera_Setup.exe" "$WIN_DIR/"
elif compgen -G "$ROOT_DIR/dist/installers/windows/*.exe" > /dev/null; then
  cp -f "$ROOT_DIR/dist/installers/windows/"*.exe "$WIN_DIR/"
fi

if [[ "$REQUIRE_WINDOWS" == "1" ]] && ! compgen -G "$WIN_DIR/*.exe" > /dev/null; then
  echo "ERRO: Nenhum instalador Windows (.exe) encontrado."
  exit 2
fi

# WINDOWS: CONFIGURAR_BANCO.exe
if [[ -f "$ROOT_DIR/dist/SistemaOpera/CONFIGURAR_BANCO.exe" ]]; then
  cp -f "$ROOT_DIR/dist/SistemaOpera/CONFIGURAR_BANCO.exe" "$WIN_DIR/"
elif [[ -f "$ROOT_DIR/dist/windows/CONFIGURAR_BANCO.exe" ]]; then
  cp -f "$ROOT_DIR/dist/windows/CONFIGURAR_BANCO.exe" "$WIN_DIR/"
else
  echo "ERRO: CONFIGURAR_BANCO.exe nao encontrado."
  exit 6
fi

# WINDOWS: CONFIGURAR_POSTGRES.exe
CONFIG_POSTGRES_EXE=""
for c in \
  "$ROOT_DIR/dist/SISTEMA_OPERA_${VERSION}_${ARCHITECTURE}/CONFIGURAR_POSTGRES.exe" \
  "$ROOT_DIR/dist/installers/unified/SISTEMA_OPERA_${VERSION}_${ARCHITECTURE}/CONFIGURAR_POSTGRES.exe" \
  "$ROOT_DIR/dist/SistemaOpera/CONFIGURAR_POSTGRES.exe"
do
  if [[ -f "$c" ]]; then
    CONFIG_POSTGRES_EXE="$c"
    break
  fi
done

if [[ -z "$CONFIG_POSTGRES_EXE" ]]; then
  echo "ERRO: CONFIGURAR_POSTGRES.exe nao encontrado. Gere antes com:"
  echo "   powershell -ExecutionPolicy Bypass -File packaging/windows/build_unified_package.ps1 -Python python -Version ${VERSION} -Architecture ${ARCHITECTURE} -SkipInstallerBuild"
  exit 5
fi
cp -f "$CONFIG_POSTGRES_EXE" "$WIN_DIR/"

# SCRIPTS em ambas as pastas
if [[ ! -d "$ROOT_DIR/SCRIPTS" ]]; then
  echo "ERRO: Pasta SCRIPTS nao encontrada."
  exit 7
fi
cp -R "$ROOT_DIR/SCRIPTS" "$WIN_DIR/SCRIPTS"
cp -R "$ROOT_DIR/SCRIPTS" "$MAC_DIR/SCRIPTS"

# MAC: artefatos similares
if [[ -f "$ROOT_DIR/dist/installers/macos/SISTEMA_OPERA_${VERSION}_macOS.dmg" ]]; then
  cp -f "$ROOT_DIR/dist/installers/macos/SISTEMA_OPERA_${VERSION}_macOS.dmg" "$MAC_DIR/"
fi

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

ZIP_OUT="$ROOT_DIR/dist/SISTEMA_OPERA_${VERSION}_INSTALLER.zip"
rm -f "$ZIP_OUT"

# ZIP must mirror exactly the WINDOWS folder contents
ROOT_DIR="$ROOT_DIR" VERSION="$VERSION" python - <<'PYZIP'
from pathlib import Path
import os, zipfile
root = Path(os.environ['ROOT_DIR'])
version = os.environ['VERSION']
win_dir = root / 'dist' / 'release' / f'SISTEMA_OPERA_{version}' / 'windows'
zip_out = root / 'dist' / f'SISTEMA_OPERA_{version}_INSTALLER.zip'
if not win_dir.exists():
    raise SystemExit(f"Windows folder not found: {win_dir}")
with zipfile.ZipFile(zip_out, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for p in win_dir.rglob('*'):
        if p.is_file():
            zf.write(p, p.relative_to(win_dir))
print(zip_out)
PYZIP

echo "OK: Pacote unico gerado: $ZIP_OUT"
echo "ZIP espelha exatamente o conteudo da pasta windows"
echo "Windows: SCRIPTS + CONFIGURAR_BANCO.exe + CONFIGURAR_POSTGRES.exe + instalador oficial"
echo "macos:   SCRIPTS + CONFIGURAR_BANCO.command + CONFIGURAR_POSTGRES.command (+ dmg quando existir)"
