#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

python3 "$ROOT_DIR/packaging/build.py" --platform macos

if ! command -v dmgbuild >/dev/null 2>&1; then
  echo "dmgbuild não encontrado. Instale com: pip install dmgbuild" >&2
  exit 0
fi

DMG_OUTPUT="$ROOT_DIR/dist/SISTEMA_OPERA.dmg"
SETTINGS_FILE="$ROOT_DIR/packaging/macos/dmg_settings.py"
APP_PATH="$ROOT_DIR/dist/SistemaOpera.app"

dmgbuild -s "$SETTINGS_FILE" "SISTEMA OPERA" "$DMG_OUTPUT" -D app="$APP_PATH"
