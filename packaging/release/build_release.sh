#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VERSION="${OPERA_VERSION:-${1:-1.0.0}}"
REQUIRE_WINDOWS="${OPERA_REQUIRE_WINDOWS:-0}"
WINDOWS_EXE_PATH="${OPERA_WINDOWS_EXE:-}"

if [[ "${2:-}" == "--require-windows" ]]; then
  REQUIRE_WINDOWS="1"
fi

# 1) Gera DMG
bash packaging/macos/build_installer.sh "$VERSION"

# 2) Monta pasta release com os 2 (macOS + windows)
REL_DIR="$ROOT_DIR/dist/release/SISTEMA_OPERA_${VERSION}"
MAC_DIR="$REL_DIR/macos"
WIN_DIR="$REL_DIR/windows"

rm -rf "$REL_DIR"
mkdir -p "$MAC_DIR" "$WIN_DIR"

# Copia DMG
cp -f "$ROOT_DIR/dist/installers/macos/SISTEMA_OPERA_${VERSION}_macOS.dmg" "$MAC_DIR/"

# Copia Windows EXE (prioriza OPERA_WINDOWS_EXE)
if [[ -n "$WINDOWS_EXE_PATH" && -f "$WINDOWS_EXE_PATH" ]]; then
  cp -f "$WINDOWS_EXE_PATH" "$WIN_DIR/"
elif compgen -G "$ROOT_DIR/dist/installers/windows/*.exe" > /dev/null; then
  cp -f "$ROOT_DIR/dist/installers/windows/"*.exe "$WIN_DIR/"
fi

if [[ "$REQUIRE_WINDOWS" == "1" ]] && ! compgen -G "$WIN_DIR/*.exe" > /dev/null; then
  echo "❌ Nenhum instalador Windows (.exe) encontrado para compor pacote completo."
  echo "   - Informe OPERA_WINDOWS_EXE=/caminho/arquivo.exe"
  echo "   - ou coloque o .exe em dist/installers/windows/"
  exit 2
fi

# 3) Cria ZIP único
ZIP_OUT="$ROOT_DIR/dist/SISTEMA_OPERA_${VERSION}_INSTALLER.zip"
rm -f "$ZIP_OUT"

# ditto preserva recursos no mac
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
echo "   - DMG: dist/installers/macos/"
echo "   - EXE: dist/installers/windows/ (ou OPERA_WINDOWS_EXE)"
