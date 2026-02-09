#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VERSION="${OPERA_VERSION:-${1:-1.0.0}}"

# 1) Gera DMG
bash packaging/macos/build_installer.sh "$VERSION"

# 2) Monta pasta release com os 2 (se o Windows já existir, ele entra também)
REL_DIR="$ROOT_DIR/dist/release/SISTEMA_OPERA_${VERSION}"
MAC_DIR="$REL_DIR/macos"
WIN_DIR="$REL_DIR/windows"

rm -rf "$REL_DIR"
mkdir -p "$MAC_DIR" "$WIN_DIR"

# Copia DMG
cp -f "$ROOT_DIR/dist/installers/macos/SISTEMA_OPERA_${VERSION}_macOS.dmg" "$MAC_DIR/"

# Copia Windows EXE se já existir (por exemplo, você rodou no Windows e trouxe o arquivo)
if compgen -G "$ROOT_DIR/dist/installers/windows/*.exe" > /dev/null; then
  cp -f "$ROOT_DIR/dist/installers/windows/"*.exe "$WIN_DIR/"
fi

# 3) Cria ZIP único
ZIP_OUT="$ROOT_DIR/dist/SISTEMA_OPERA_${VERSION}_INSTALLER.zip"
rm -f "$ZIP_OUT"

# ditto preserva recursos no mac
ditto -c -k --sequesterRsrc --keepParent "$REL_DIR" "$ZIP_OUT"

echo "✅ Pacote único gerado: $ZIP_OUT"
echo "   - DMG: dist/installers/macos/"
echo "   - EXE: dist/installers/windows/ (se existir)"
