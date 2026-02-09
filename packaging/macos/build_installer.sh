#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# Você pode passar a versão assim:
#   OPERA_VERSION=1.0.0 bash packaging/macos/build_installer.sh
VERSION="${OPERA_VERSION:-${1:-1.0.0}}"

PYTHON_BIN="${PYTHON_BIN:-python3}"

# 1) Build PyInstaller (usa o .spec se existir, conforme seu build.py)
"$PYTHON_BIN" "$ROOT_DIR/packaging/build.py" --platform macos --spec "$ROOT_DIR/SistemaOpera.spec"

# 2) Gera DMG
if ! command -v dmgbuild >/dev/null 2>&1; then
  echo "dmgbuild não encontrado. Instale com: pip install dmgbuild" >&2
  exit 1
fi

OUT_DIR="$ROOT_DIR/dist/installers/macos"
mkdir -p "$OUT_DIR"

APP_PATH="$ROOT_DIR/dist/SistemaOpera.app"
SETTINGS_FILE="$ROOT_DIR/packaging/macos/dmg_settings.py"
DMG_OUTPUT="$OUT_DIR/SISTEMA_OPERA_${VERSION}_macOS.dmg"

dmgbuild -s "$SETTINGS_FILE" "SISTEMA OPERA" "$DMG_OUTPUT" -D app="$APP_PATH"

echo "✅ DMG gerado em: $DMG_OUTPUT"
