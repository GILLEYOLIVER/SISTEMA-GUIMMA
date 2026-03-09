#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VERSION="${OPERA_VERSION:-${1:-1.0.0}}"
ARCHITECTURE="${OPERA_ARCH:-${2:-x64}}"
REQUIRE_WINDOWS="${OPERA_REQUIRE_WINDOWS:-0}"
WINDOWS_EXE_PATH="${OPERA_WINDOWS_EXE:-}"

if [[ "$ARCHITECTURE" != "x64" && "$ARCHITECTURE" != "x86" ]]; then
  echo "❌ Arquitetura inválida: $ARCHITECTURE (use x64 ou x86)"
  exit 4
fi

if [[ "${3:-}" == "--require-windows" ]]; then
  REQUIRE_WINDOWS="1"
fi

# 1) Gera DMG
bash packaging/macos/build_installer.sh "$VERSION"

# 2) Monta pasta release com os 2 (macOS + windows)
REL_DIR="$ROOT_DIR/dist/release/SISTEMA_OPERA_${VERSION}"
MAC_DIR="$REL_DIR/macos"
WIN_DIR="$REL_DIR/windows"
CONFIG_PY="$ROOT_DIR/configurar_postgres.py"

rm -rf "$REL_DIR"
mkdir -p "$MAC_DIR" "$WIN_DIR"


# Copia DMG
cp -f "$ROOT_DIR/dist/installers/macos/SISTEMA_OPERA_${VERSION}_macOS.dmg" "$MAC_DIR/"

# Copia Windows EXE (prioriza OPERA_WINDOWS_EXE)
if [[ -n "$WINDOWS_EXE_PATH" && -f "$WINDOWS_EXE_PATH" ]]; then
  cp -f "$WINDOWS_EXE_PATH" "$WIN_DIR/"
elif [[ -f "$ROOT_DIR/dist/SistemaOpera_Setup_${ARCHITECTURE}.exe" ]]; then
  cp -f "$ROOT_DIR/dist/SistemaOpera_Setup_${ARCHITECTURE}.exe" "$WIN_DIR/"
elif compgen -G "$ROOT_DIR/dist/installers/windows/*.exe" > /dev/null; then
  cp -f "$ROOT_DIR/dist/installers/windows/"*.exe "$WIN_DIR/"
fi

if [[ "$REQUIRE_WINDOWS" == "1" ]] && ! compgen -G "$WIN_DIR/*.exe" > /dev/null; then
  echo "❌ Nenhum instalador Windows (.exe) encontrado para compor pacote completo."
  echo "   - Informe OPERA_WINDOWS_EXE=/caminho/arquivo.exe"
  echo "   - ou gere dist/SistemaOpera_Setup_${ARCHITECTURE}.exe"
  exit 2
fi

# Copia o executavel CONFIGURAR_POSTGRES.exe para pasta windows
CONFIG_EXE_CANDIDATES=(
  "$ROOT_DIR/dist/installers/unified/SISTEMA_OPERA_${VERSION}_${ARCHITECTURE}/CONFIGURAR_POSTGRES.exe"
  "$ROOT_DIR/dist/SistemaOpera/CONFIGURAR_POSTGRES.exe"
)

CONFIG_EXE=""
for c in "${CONFIG_EXE_CANDIDATES[@]}"; do
  if [[ -f "$c" ]]; then
    CONFIG_EXE="$c"
    break
  fi
done

if [[ -z "$CONFIG_EXE" ]]; then
  echo "❌ CONFIGURAR_POSTGRES.exe nao encontrado. Gere antes com:"
  echo "   powershell -ExecutionPolicy Bypass -File packaging/windows/build_unified_package.ps1 -Python python -Version ${VERSION} -Architecture ${ARCHITECTURE} -SkipInstallerBuild"
  exit 5
fi
cp -f "$CONFIG_EXE" "$WIN_DIR/"

# 3) Cria ZIP único
ZIP_OUT="$ROOT_DIR/dist/SISTEMA_OPERA_${VERSION}_INSTALLER.zip"
rm -f "$ZIP_OUT"

if command -v ditto >/dev/null 2>&1; then
  ditto -c -k --sequesterRsrc --keepParent "$REL_DIR" "$ZIP_OUT"
else
  ROOT_DIR="$ROOT_DIR" VERSION="$VERSION" python - <<'PYZIP'
from pathlib import Path
import os
import zipfile
root = Path(os.environ['ROOT_DIR'])
version = os.environ['VERSION']
rel_dir = root / 'dist' / 'release' / f'SISTEMA_OPERA_{version}'
zip_out = root / 'dist' / f'SISTEMA_OPERA_{version}_INSTALLER.zip'
with zipfile.ZipFile(zip_out, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for p in rel_dir.rglob('*'):
        if p.is_file():
            zf.write(p, p.relative_to(rel_dir.parent))
print(zip_out)
PYZIP
fi

echo "✅ Pacote único gerado: $ZIP_OUT"
echo "Windows inclui: instalador oficial + CONFIGURAR_POSTGRES.exe"
echo "Comando: bash packaging/release/build_release.sh ${VERSION} ${ARCHITECTURE}"
