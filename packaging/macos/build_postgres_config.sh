#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

echo "=============================================="
echo " Build configurador PostgreSQL (macOS)"
echo "=============================================="

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python3 nao encontrado"
  exit 1
fi

if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  echo "pip nao encontrado para o Python selecionado"
  exit 1
fi

if ! "$PYTHON_BIN" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "PyInstaller nao encontrado. Instalando..."
  "$PYTHON_BIN" -m pip install pyinstaller
fi

if ! "$PYTHON_BIN" -c "import customtkinter" >/dev/null 2>&1; then
  echo "customtkinter nao encontrado. Instalando..."
  "$PYTHON_BIN" -m pip install customtkinter
fi

if ! "$PYTHON_BIN" -c "import PIL" >/dev/null 2>&1; then
  echo "Pillow nao encontrado. Instalando..."
  "$PYTHON_BIN" -m pip install pillow
fi

ENTRYPOINT="configurar_postgres.py"
if [ ! -f "$ENTRYPOINT" ]; then
  echo "Entrypoint nao encontrado: $ENTRYPOINT"
  exit 1
fi

if [ ! -d "$ROOT_DIR/SCRIPTS" ]; then
  echo "Pasta SCRIPTS nao encontrada"
  exit 1
fi

mkdir -p "$ROOT_DIR/build" "$ROOT_DIR/dist/SistemaGuimma"

ICON_TMP_PNG="$ROOT_DIR/build/configurar_postgres_icon.png"
ICON_ICNS="$ROOT_DIR/build/configurar_postgres.icns"
ICONSET_DIR="$ROOT_DIR/build/configurar_postgres.iconset"
ICON_ARG=()

if [ -f "$ROOT_DIR/icons/PG_ICON.ico" ]; then
  "$PYTHON_BIN" - "$ROOT_DIR/icons/PG_ICON.ico" "$ICON_TMP_PNG" <<'PYICON'
from pathlib import Path
import sys
from PIL import Image

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
img = Image.open(src)
frames = []
try:
    while True:
        frames.append(img.copy().convert("RGBA"))
        img.seek(img.tell() + 1)
except EOFError:
    pass

best = max(frames or [img.convert("RGBA")], key=lambda im: im.size[0] * im.size[1])
best.save(dst)
PYICON
elif [ -f "$ROOT_DIR/icons/BANCO DE DADOS.png" ]; then
  cp "$ROOT_DIR/icons/BANCO DE DADOS.png" "$ICON_TMP_PNG"
elif [ -f "$ROOT_DIR/icons/ICONE_SISTEMA.png" ]; then
  cp "$ROOT_DIR/icons/ICONE_SISTEMA.png" "$ICON_TMP_PNG"
fi

if [ -f "$ICON_TMP_PNG" ] && command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
  rm -rf "$ICONSET_DIR"
  mkdir -p "$ICONSET_DIR"
  sips -z 16 16 "$ICON_TMP_PNG" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
  sips -z 32 32 "$ICON_TMP_PNG" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
  sips -z 32 32 "$ICON_TMP_PNG" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
  sips -z 64 64 "$ICON_TMP_PNG" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
  sips -z 128 128 "$ICON_TMP_PNG" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
  sips -z 256 256 "$ICON_TMP_PNG" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
  sips -z 256 256 "$ICON_TMP_PNG" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
  sips -z 512 512 "$ICON_TMP_PNG" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
  sips -z 512 512 "$ICON_TMP_PNG" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
  sips -z 1024 1024 "$ICON_TMP_PNG" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null
  iconutil -c icns "$ICONSET_DIR" -o "$ICON_ICNS"
  rm -rf "$ICONSET_DIR"
  if [ -f "$ICON_ICNS" ]; then
    ICON_ARG=(--icon "$ICON_ICNS")
  fi
fi

"$PYTHON_BIN" -m PyInstaller \
  --windowed \
  --noconfirm \
  --clean \
  --name CONFIGURAR_POSTGRES \
  --distpath "$ROOT_DIR/dist/SistemaGuimma" \
  --workpath "$ROOT_DIR/build/pyi_configurar_postgres_mac" \
  --specpath "$ROOT_DIR/build" \
  "${ICON_ARG[@]}" \
  --add-data "$ROOT_DIR/SCRIPTS:scripts" \
  --hidden-import tkinter \
  --hidden-import customtkinter \
  --hidden-import ctypes \
  --hidden-import certifi \
  --collect-all certifi \
  "$ENTRYPOINT"

APP_PATH="dist/SistemaGuimma/CONFIGURAR_POSTGRES.app"
if [ -d "$APP_PATH" ]; then
  if command -v plutil >/dev/null 2>&1; then
    plutil -replace CFBundleDisplayName -string "Configurar PostgreSQL" "$APP_PATH/Contents/Info.plist" >/dev/null 2>&1 || true
    plutil -replace CFBundleName -string "Configurar PostgreSQL" "$APP_PATH/Contents/Info.plist" >/dev/null 2>&1 || true
    plutil -replace CFBundleIdentifier -string "com.sistemaguimma.configurarpostgres" "$APP_PATH/Contents/Info.plist" >/dev/null 2>&1 || true
  fi
  if command -v codesign >/dev/null 2>&1; then
    codesign --force --deep --sign - "$APP_PATH" >/dev/null 2>&1 || true
  fi
  echo "Configurador PostgreSQL criado: $APP_PATH"
else
  echo "Falha ao gerar configurador PostgreSQL no macOS"
  exit 1
fi
