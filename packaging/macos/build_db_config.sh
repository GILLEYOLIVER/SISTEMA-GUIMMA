#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

echo "=============================================="
echo " Build configurador de banco (macOS)"
echo "=============================================="

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "❌ python3 não encontrado"
  exit 1
fi

if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  echo "❌ pip não encontrado para o Python selecionado"
  exit 1
fi

if ! "$PYTHON_BIN" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "⚠️ PyInstaller não encontrado. Instalando..."
  "$PYTHON_BIN" -m pip install pyinstaller
fi

ICON_PNG="icons/icon_config.png"
ICON_ICNS="build/configurador.icns"
mkdir -p build dist/SistemaOpera

if [ -f "$ICON_PNG" ] && command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
  echo "🖼️ Gerando .icns para o configurador..."
  ICONSET_DIR="build/configurador.iconset"
  rm -rf "$ICONSET_DIR"
  mkdir -p "$ICONSET_DIR"

  sips -z 16 16 "$ICON_PNG" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
  sips -z 32 32 "$ICON_PNG" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
  sips -z 32 32 "$ICON_PNG" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
  sips -z 64 64 "$ICON_PNG" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
  sips -z 128 128 "$ICON_PNG" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
  sips -z 256 256 "$ICON_PNG" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
  sips -z 256 256 "$ICON_PNG" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
  sips -z 512 512 "$ICON_PNG" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
  sips -z 512 512 "$ICON_PNG" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
  cp "$ICON_PNG" "$ICONSET_DIR/icon_512x512@2x.png"

  iconutil -c icns "$ICONSET_DIR" -o "$ICON_ICNS"
  rm -rf "$ICONSET_DIR"
  ICON_ARG=(--icon "$ICON_ICNS")
else
  echo "⚠️ Ícone customizado não gerado; build seguirá sem --icon"
  ICON_ARG=()
fi

ENTRYPOINT="packaging/SETUP_BANCO.py"
if [ ! -f "$ENTRYPOINT" ]; then
  echo "❌ Entrypoint não encontrado: $ENTRYPOINT"
  exit 1
fi

"$PYTHON_BIN" -m PyInstaller \
  --windowed \
  --noconfirm \
  --clean \
  --name CONFIGURAR_BANCO \
  --distpath dist/SistemaOpera \
  --workpath build/pyi_config_mac \
  --specpath build \
  "${ICON_ARG[@]}" \
  --hidden-import tkinter \
  --hidden-import customtkinter \
  --hidden-import psycopg2 \
  --hidden-import PIL \
  --hidden-import PIL._imaging \
  --collect-all PIL \
  "$ENTRYPOINT"

APP_PATH="dist/SistemaOpera/CONFIGURAR_BANCO.app"
if [ -d "$APP_PATH" ]; then
  echo "✅ Configurador criado: $APP_PATH"
else
  echo "❌ Falha ao gerar configurador no macOS"
  exit 1
fi
