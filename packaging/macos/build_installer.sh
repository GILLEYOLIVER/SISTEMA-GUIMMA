#!/bin/bash
# packaging/macos/build_installer.sh
# Script para construir instalador macOS do Sistema Guimma

set -euo pipefail  # Sai no primeiro erro e falha em variáveis não definidas

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_BIN=()
PYINSTALLER_BIN=()
HAS_FITZ="no"
HAS_PYMUPDF_PACKAGE="no"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

CREATE_DMG="yes"
CREATE_PKG="yes"
INTERACTIVE_MODE="no"
APP_VERSION="${GUIMMA_VERSION:-1.0.0}"
APP_DISPLAY_NAME="Sistema Guimma"
APP_INTERNAL_NAME="SistemaGuimma"
APP_BUNDLE_NAME="Sistema Guimma"
LICENSE_APP_BUNDLE_NAME="Sistema Guimma Licenca"
DB_CONFIG_APP_BUNDLE_NAME="CONFIGURAR_BANCO"
APP_SUPPORT_DIR_NAME="SistemaGuimma"

ensure_macos() {
    if [[ "${OSTYPE:-}" != darwin* ]]; then
        log_error "Este script deve ser executado no macOS"
        exit 1
    fi
}

print_usage() {
    cat <<'USAGE'
Uso: ./packaging/macos/build_installer.sh [opções]

Opções:
  --version <v>    Versão usada nos nomes dos instaladores
  --with-dmg       Gera DMG automaticamente (sem pergunta)
  --no-dmg         Não gera DMG automaticamente (sem pergunta)
  --with-pkg       Gera PKG automaticamente (sem pergunta)
  --no-pkg         Não gera PKG automaticamente (sem pergunta)
  --interactive    Pergunta no terminal se deve criar DMG/PKG
  --help           Exibe esta ajuda

Exemplo (gerar tudo sem interação):
  ./packaging/macos/build_installer.sh --version 1.0.0 --with-dmg --with-pkg
USAGE
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --version)
                shift
                if [[ $# -eq 0 || -z "${1:-}" ]]; then
                    log_error "Informe a versão após --version"
                    exit 1
                fi
                APP_VERSION="$1"
                ;;
            --with-dmg)
                CREATE_DMG="yes"
                ;;
            --no-dmg)
                CREATE_DMG="no"
                ;;
            --with-pkg)
                CREATE_PKG="yes"
                ;;
            --no-pkg)
                CREATE_PKG="no"
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            --interactive)
                INTERACTIVE_MODE="yes"
                CREATE_DMG=""
                CREATE_PKG=""
                ;;
            [0-9]*)
                APP_VERSION="$1"
                ;;
            *)
                log_error "Opção inválida: $1"
                print_usage
                exit 1
                ;;
        esac
        shift
    done
}

# Verificar dependências
check_dependencies() {
    print_header "VERIFICANDO DEPENDÊNCIAS"

    # Verificar Python
    if ! command -v "$PYTHON_BIN" &> /dev/null; then
        log_error "Python3 não encontrado"
        exit 1
    fi
    log_info "Python: $($PYTHON_BIN --version 2>&1)"

    if "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
        PIP_BIN=("$PYTHON_BIN" -m pip)
    elif command -v pip3 >/dev/null 2>&1; then
        PIP_BIN=(pip3)
    else
        log_error "pip não encontrado para o Python selecionado"
        exit 1
    fi
    log_info "pip: disponível"

    # Verificar PyInstaller
    if ! "$PYTHON_BIN" -c "import PyInstaller" &> /dev/null; then
        log_warning "PyInstaller não instalado. Instalando..."
        "${PIP_BIN[@]}" install pyinstaller
    fi
    if "$PYTHON_BIN" -m PyInstaller --version >/dev/null 2>&1; then
        PYINSTALLER_BIN=("$PYTHON_BIN" -m PyInstaller)
    elif command -v pyinstaller >/dev/null 2>&1; then
        PYINSTALLER_BIN=(pyinstaller)
    else
        log_error "PyInstaller não disponível"
        exit 1
    fi
    log_info "PyInstaller: disponível"

    # Verificar psycopg2
    if ! "$PYTHON_BIN" -c "import psycopg2" &> /dev/null; then
        log_warning "psycopg2 não instalado. Instalando..."
        "${PIP_BIN[@]}" install psycopg2-binary
    fi
    log_info "psycopg2: disponível"

    # Verificar Pillow
    if ! "$PYTHON_BIN" -c "import PIL" &> /dev/null; then
        log_warning "Pillow não instalado. Instalando..."
        "${PIP_BIN[@]}" install pillow
    fi
    log_info "Pillow: disponível"

    # Verificar FPDF2
    if ! "$PYTHON_BIN" -c "import fpdf" &> /dev/null; then
        log_warning "fpdf2 não instalado. Instalando..."
        "${PIP_BIN[@]}" install fpdf2
    fi
    log_info "fpdf/fpdf2: disponível"

    # Verificar ReportLab
    if ! "$PYTHON_BIN" -c "import reportlab" &> /dev/null; then
        log_warning "reportlab não instalado. Instalando..."
        "${PIP_BIN[@]}" install reportlab
    fi
    log_info "reportlab: disponível"

    # Verificar Matplotlib
    if ! "$PYTHON_BIN" -c "import matplotlib" &> /dev/null; then
        log_warning "matplotlib não instalado. Instalando..."
        "${PIP_BIN[@]}" install matplotlib
    fi
    log_info "matplotlib: disponível"

    # Verificar PyMuPDF (módulo pode existir como fitz e/ou pymupdf)
    if "$PYTHON_BIN" -c "import fitz" &> /dev/null; then
        HAS_FITZ="yes"
    fi
    if "$PYTHON_BIN" -c "import pymupdf" &> /dev/null; then
        HAS_PYMUPDF_PACKAGE="yes"
    fi

    if [[ "$HAS_FITZ" == "no" && "$HAS_PYMUPDF_PACKAGE" == "no" ]]; then
        log_warning "pymupdf não instalado. Instalando..."
        "${PIP_BIN[@]}" install pymupdf
        if "$PYTHON_BIN" -c "import fitz" &> /dev/null; then
            HAS_FITZ="yes"
        fi
        if "$PYTHON_BIN" -c "import pymupdf" &> /dev/null; then
            HAS_PYMUPDF_PACKAGE="yes"
        fi
    fi
    if [[ "$HAS_FITZ" == "yes" || "$HAS_PYMUPDF_PACKAGE" == "yes" ]]; then
        log_info "pymupdf/fitz: disponível"
    else
        log_warning "pymupdf/fitz não detectado; build seguirá sem coletar pacote pymupdf"
    fi
}

# Preparar ícone para macOS
prepare_icon() {
    print_header "PREPARANDO ÍCONE"

    # Caminhos
    PNG_ICON="icons/ICONE_SISTEMA.png"
    ICNS_ICON="icons/ICONE_SISTEMA.icns"

    if [ -f "$PNG_ICON" ]; then
        log_info "Convertendo PNG para ICNS..."

        # Criar ícone .icns (apenas tamanhos válidos para iconutil)
        ICONSET_DIR="icons/ICONE_SISTEMA.iconset"
        rm -rf "$ICONSET_DIR"
        mkdir -p "$ICONSET_DIR"

        sips -z 16 16 "$PNG_ICON" --out "$ICONSET_DIR/icon_16x16.png" > /dev/null
        sips -z 32 32 "$PNG_ICON" --out "$ICONSET_DIR/icon_16x16@2x.png" > /dev/null
        sips -z 32 32 "$PNG_ICON" --out "$ICONSET_DIR/icon_32x32.png" > /dev/null
        sips -z 64 64 "$PNG_ICON" --out "$ICONSET_DIR/icon_32x32@2x.png" > /dev/null
        sips -z 128 128 "$PNG_ICON" --out "$ICONSET_DIR/icon_128x128.png" > /dev/null
        sips -z 256 256 "$PNG_ICON" --out "$ICONSET_DIR/icon_128x128@2x.png" > /dev/null
        sips -z 256 256 "$PNG_ICON" --out "$ICONSET_DIR/icon_256x256.png" > /dev/null
        sips -z 512 512 "$PNG_ICON" --out "$ICONSET_DIR/icon_256x256@2x.png" > /dev/null
        sips -z 512 512 "$PNG_ICON" --out "$ICONSET_DIR/icon_512x512.png" > /dev/null
        cp "$PNG_ICON" "$ICONSET_DIR/icon_512x512@2x.png"

        # Criar .icns
        iconutil -c icns "$ICONSET_DIR" -o "$ICNS_ICON"

        # Limpar pasta temporária
        rm -rf "$ICONSET_DIR"

        if [ -f "$ICNS_ICON" ]; then
            log_success "Ícone ICNS criado: $ICNS_ICON"
        else
            log_error "Falha ao criar ícone ICNS"
            return 1
        fi
    else
        log_warning "Ícone PNG não encontrado: $PNG_ICON"
        log_info "Procurando em locais alternativos..."

        # Procurar em locais alternativos
        alt_locations=(
            "PAGINAS_DO_SISTEMA/ICONE_SISTEMA.png"
            "PAGINAS_DO_SISTEMA/ICONE_SISTEMA.icns"
            "ICONE_SISTEMA.png"
            "src/ICONE_SISTEMA.png"
        )

        for location in "${alt_locations[@]}"; do
            if [ -f "$location" ]; then
                log_info "Ícone encontrado em: $location"
                cp "$location" "icons/"
                if [[ "$location" == *.icns ]]; then
                    ICNS_ICON="icons/ICONE_SISTEMA.icns"
                    cp "$location" "$ICNS_ICON"
                else
                    PNG_ICON="icons/ICONE_SISTEMA.png"
                    cp "$location" "$PNG_ICON"
                    # Converter para ICNS
                    prepare_icon
                fi
                return 0
            fi
        done

        log_error "Nenhum ícone encontrado"
        return 1
    fi
}

# Construir aplicativo
build_app() {
    print_header "CONSTRUINDO APLICATIVO"

    # Verificar se o script principal existe
    MAIN_SCRIPT="PAGINAS_DO_SISTEMA/MAIN.py"
    if [ ! -f "$MAIN_SCRIPT" ]; then
        log_error "Script principal não encontrado: $MAIN_SCRIPT"
        exit 1
    fi

    # Verificar ícone
    ICON_PATH="$ROOT_DIR/icons/ICONE_SISTEMA.icns"
    if [ ! -f "$ICON_PATH" ]; then
        log_warning "Ícone ICNS não encontrado, usando padrão"
        ICON_ARG=""
    else
        ICON_ARG="--icon=$ICON_PATH"
        log_info "Usando ícone: $ICON_PATH"
    fi

    # Limpar builds anteriores
    if [ -d "dist" ]; then
        log_info "Limpando builds anteriores..."
        rm -rf dist/*
    fi

    if [ -d "build" ]; then
        rm -rf build/*
    fi
    mkdir -p "build/generated_specs"

    cmd=(
      "${PYINSTALLER_BIN[@]}"
      --windowed
      --noconsole
      --name "$APP_INTERNAL_NAME"
      --specpath "build/generated_specs"
      --osx-bundle-identifier "com.sistemaguimma.app"
      --add-data "$ROOT_DIR/PAGINAS_DO_SISTEMA:PAGINAS_DO_SISTEMA"
      --add-data "$ROOT_DIR/icons:icons"
      --add-data "$ROOT_DIR/data:data"
      --add-data "$ROOT_DIR/licenciamento:licenciamento"
      --hidden-import psycopg2
      --hidden-import psycopg2.extras
      --hidden-import licenciamento
      --hidden-import licenciamento.runtime
      --hidden-import licenciamento.client
      --hidden-import licenciamento.store
      --hidden-import licenciamento.machine
      --hidden-import licenciamento.agent
      --hidden-import licenciamento.app
      --hidden-import PIL
      --hidden-import PIL._imaging
      --hidden-import PIL.Image
      --hidden-import PIL.ImageFile
      --hidden-import PIL.ImageOps
      --hidden-import PIL.ImageDraw
      --hidden-import PIL.ImageFont
      --hidden-import PIL.ImageTk
      --hidden-import tkinter
      --hidden-import tkinter.ttk
      --hidden-import certifi
      --hidden-import fpdf
      --hidden-import fpdf.enums
      --hidden-import reportlab
      --hidden-import reportlab.pdfgen
      --hidden-import reportlab.pdfbase
      --hidden-import reportlab.lib
      --hidden-import reportlab.graphics
      --hidden-import matplotlib
      --hidden-import matplotlib.pyplot
      --hidden-import matplotlib.backends.backend_tkagg
      --hidden-import numpy
      --hidden-import fitz
      --collect-all fpdf
      --collect-all reportlab
      --collect-all matplotlib
    )

    if [[ "$HAS_PYMUPDF_PACKAGE" == "yes" ]]; then
        cmd+=(--collect-all pymupdf)
    fi

    if [ -n "$ICON_ARG" ]; then
        cmd+=("$ICON_ARG")
    fi

    cmd+=("$MAIN_SCRIPT")

    log_info "Executando build com PyInstaller..."
    "${cmd[@]}"

    # Verificar se o app foi criado
    BUILD_APP_PATH="dist/${APP_INTERNAL_NAME}.app"
    APP_PATH="dist/${APP_BUNDLE_NAME}.app"
    if [ -d "$BUILD_APP_PATH" ]; then
        rm -rf "$APP_PATH"
        mv "$BUILD_APP_PATH" "$APP_PATH"
    fi
    if [ -d "$APP_PATH" ]; then
        if command -v plutil >/dev/null 2>&1; then
            plutil -replace CFBundleDisplayName -string "$APP_DISPLAY_NAME" "$APP_PATH/Contents/Info.plist" >/dev/null 2>&1 || true
            plutil -replace CFBundleName -string "$APP_DISPLAY_NAME" "$APP_PATH/Contents/Info.plist" >/dev/null 2>&1 || true
            plutil -replace CFBundleShortVersionString -string "$APP_VERSION" "$APP_PATH/Contents/Info.plist" >/dev/null 2>&1 || true
            plutil -replace CFBundleVersion -string "$APP_VERSION" "$APP_PATH/Contents/Info.plist" >/dev/null 2>&1 || true
        fi
        if command -v codesign >/dev/null 2>&1; then
            codesign --force --deep --sign - "$APP_PATH" >/dev/null 2>&1 || true
        fi
        log_success "Aplicativo criado: $APP_PATH"

        # Exibir informações
        APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
        log_info "Tamanho do aplicativo: $APP_SIZE"

        # Listar conteúdo
        log_info "Conteúdo do aplicativo:"
        find "$APP_PATH" -type f \( -name "*.so" -o -name "*.dylib" \) | awk 'NR <= 10 { print }' | while read file; do
            log_info "  - $(basename "$file")"
        done
    else
        log_error "Aplicativo não foi criado"
        exit 1
    fi
}

# Construir app separado de licenciamento
build_license_app() {
    print_header "CONSTRUINDO APP DE LICENCIAMENTO"

    LICENSE_SPEC="SistemaGuimmaLicenca.spec"
    LICENSE_APP_PATH="dist/${LICENSE_APP_BUNDLE_NAME}.app"

    if [ ! -f "$LICENSE_SPEC" ]; then
        log_error "Spec do app de licenciamento não encontrado: $LICENSE_SPEC"
        return 1
    fi

    log_info "Executando build do app de licenciamento..."
    "${PYINSTALLER_BIN[@]}" --clean --noconfirm "$LICENSE_SPEC"

    if [ ! -d "$LICENSE_APP_PATH" ]; then
        log_error "App de licenciamento não foi criado: $LICENSE_APP_PATH"
        return 1
    fi

    if command -v codesign >/dev/null 2>&1; then
        codesign --force --deep --sign - "$LICENSE_APP_PATH" >/dev/null 2>&1 || true
    fi

    LICENSE_SIZE=$(du -sh "$LICENSE_APP_PATH" | cut -f1)
    log_success "App de licenciamento criado: $LICENSE_APP_PATH ($LICENSE_SIZE)"
}

# Construir app separado de configuracao de banco
build_db_config_app() {
    print_header "CONSTRUINDO CONFIGURADOR DE BANCO"

    if [ ! -x "packaging/macos/build_db_config.sh" ]; then
        log_warning "Script do configurador de banco não encontrado ou sem permissão de execução"
        return 0
    fi

    PYTHON_BIN="$PYTHON_BIN" bash "packaging/macos/build_db_config.sh"
}

# Criar DMG
create_dmg() {
    print_header "CRIANDO INSTALADOR DMG"

    APP_PATH="dist/${APP_BUNDLE_NAME}.app"
    DMG_PATH="dist/${APP_BUNDLE_NAME}.dmg"
    INSTALLER_DIR="dist/installers/macos"
    VERSIONED_DMG_PATH="$INSTALLER_DIR/${APP_BUNDLE_NAME} ${APP_VERSION} macOS.dmg"

    if [ ! -d "$APP_PATH" ]; then
        log_error "Aplicativo não encontrado: $APP_PATH"
        return 1
    fi

    log_info "Criando imagem DMG..."

    # Criar pasta temporária para DMG
    TEMP_DIR="dist/dmg_temp"
    mkdir -p "$TEMP_DIR"

    # Copiar aplicativo
    cp -R "$APP_PATH" "$TEMP_DIR/"
    if [ -d "dist/${LICENSE_APP_BUNDLE_NAME}.app" ]; then
        cp -R "dist/${LICENSE_APP_BUNDLE_NAME}.app" "$TEMP_DIR/"
    fi
    if [ -d "dist/SistemaGuimma/${DB_CONFIG_APP_BUNDLE_NAME}.app" ]; then
        cp -R "dist/SistemaGuimma/${DB_CONFIG_APP_BUNDLE_NAME}.app" "$TEMP_DIR/"
    fi

    # Criar link para Applications
    ln -s /Applications "$TEMP_DIR/Applications"

    # Configurações do DMG
    VOLUME_NAME="$APP_BUNDLE_NAME"

    # Criar DMG
    hdiutil create -volname "$VOLUME_NAME" \
        -srcfolder "$TEMP_DIR" \
        -ov -format UDZO \
        "$DMG_PATH"

    # Limpar pasta temporária
    rm -rf "$TEMP_DIR"

    if [ -f "$DMG_PATH" ]; then
        mkdir -p "$INSTALLER_DIR"
        cp -f "$DMG_PATH" "$VERSIONED_DMG_PATH"
        DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
        log_success "DMG criado: $DMG_PATH ($DMG_SIZE)"
        log_success "DMG versionado: $VERSIONED_DMG_PATH"

        # Verificar DMG
        log_info "Verificando DMG..."
        hdiutil verify "$DMG_PATH"
    else
        log_error "Falha ao criar DMG"
        return 1
    fi
}


# Criar instalador PKG (duplo clique)
create_pkg() {
    print_header "CRIANDO INSTALADOR PKG"

    APP_PATH="dist/${APP_BUNDLE_NAME}.app"
    LICENSE_APP_PATH="dist/${LICENSE_APP_BUNDLE_NAME}.app"
    DB_CONFIG_APP_PATH="dist/SistemaGuimma/${DB_CONFIG_APP_BUNDLE_NAME}.app"
    PKG_PATH="dist/${APP_BUNDLE_NAME}.pkg"
    PKG_SCRIPTS="dist/pkg_scripts"
    PKG_ROOT="dist/pkg_root"
    PKG_COMPONENTS="dist/pkg_components.plist"
    INSTALLER_DIR="dist/installers/macos"
    VERSIONED_PKG_PATH="$INSTALLER_DIR/${APP_BUNDLE_NAME} ${APP_VERSION} macOS.pkg"

    if [ ! -d "$APP_PATH" ]; then
        log_error "Aplicativo não encontrado: $APP_PATH"
        return 1
    fi

    if ! command -v pkgbuild &> /dev/null; then
        log_error "pkgbuild não encontrado (Xcode Command Line Tools necessário)"
        return 1
    fi

    rm -rf "$PKG_SCRIPTS" "$PKG_ROOT" "$PKG_COMPONENTS"
    mkdir -p "$PKG_SCRIPTS" "$PKG_ROOT/Applications"
    ditto "$APP_PATH" "$PKG_ROOT/Applications/${APP_BUNDLE_NAME}.app"
    if [ -d "$LICENSE_APP_PATH" ]; then
        ditto "$LICENSE_APP_PATH" "$PKG_ROOT/Applications/${LICENSE_APP_BUNDLE_NAME}.app"
    else
        log_error "App de licenciamento não encontrado: $LICENSE_APP_PATH"
        return 1
    fi
    if [ -d "$DB_CONFIG_APP_PATH" ]; then
        ditto "$DB_CONFIG_APP_PATH" "$PKG_ROOT/Applications/${DB_CONFIG_APP_BUNDLE_NAME}.app"
    else
        log_warning "Configurador de banco não encontrado: $DB_CONFIG_APP_PATH"
    fi

cat > "$PKG_SCRIPTS/postinstall" <<'POSTINSTALL'
#!/bin/bash
set +e

write_uninstaller() {
  local target_path="$1"
  mkdir -p "$(dirname "$target_path")"
  cat > "$target_path" <<'UNINSTALLER'
#!/bin/bash
set -e

if [[ "$EUID" -ne 0 ]]; then
  echo "Solicitando permissão de administrador para desinstalar o Sistema Guimma..."
  exec sudo "$0" "$@"
fi

echo "Iniciando desinstalação completa do Sistema Guimma..."

pkill -f "SistemaGuimma" 2>/dev/null || true

rm -rf "/Applications/Sistema Guimma.app"
rm -rf "/Applications/Sistema Guimma Licenca.app"

rm -rf "/Library/Application Support/SistemaGuimma"
rm -rf "/Library/Logs/SistemaGuimma"
rm -f "/Library/Preferences/com.sistemaguimma.app.plist"

for home in /Users/*; do
  user_name=$(basename "$home")
  if [[ "$user_name" == "Shared" ]]; then
    continue
  fi
  if [[ -d "$home" ]]; then
    rm -rf "$home/Library/Application Support/SistemaGuimma"
    rm -rf "$home/Library/Caches/SistemaGuimma"
    rm -rf "$home/Library/Logs/SistemaGuimma"
    rm -f "$home/Library/Preferences/com.sistemaguimma.app.plist"
    rm -f "$home/Library/LaunchAgents/com.sistemaguimma.licenca.plist"
    rm -rf "$home/Library/Saved Application State/com.sistemaguimma.app.savedState"
    rm -rf "$home/Applications/Sistema Guimma.app"
  fi
done

rm -f /tmp/sistemaguimma_db_setup_result.json /tmp/sistemaguimma_db_setup_gui.py 2>/dev/null || true

pkgutil --forget com.sistemaguimma.app >/dev/null 2>&1 || true

SCRIPT_PATH="$0"
(
  sleep 1
  rm -f "$SCRIPT_PATH"
) >/dev/null 2>&1 &

echo "Desinstalação concluída."
osascript -e 'display dialog "Sistema Guimma removido com sucesso (app + arquivos de configuração)." buttons {"OK"} default button "OK" with icon note' 2>/dev/null || true
exit 0
UNINSTALLER

  chmod +x "$target_path"
}

CURRENT_USER=$(stat -f%Su /dev/console 2>/dev/null || echo "")
if [[ -z "$CURRENT_USER" || "$CURRENT_USER" == "root" ]]; then
  CURRENT_USER=$(ls -l /dev/console | awk '{print $3}')
fi

USER_HOME=$(dscl . -read /Users/"$CURRENT_USER" NFSHomeDirectory 2>/dev/null | awk '{print $2}')
if [[ -z "$USER_HOME" ]]; then
  USER_HOME="/Users/$CURRENT_USER"
fi

TARGET_LOCATION="${2:-/}"
TARGET_VOLUME="${3:-/}"
SYSTEM_APP_PATH="/Applications/Sistema Guimma.app"
LICENSE_APP_PATH="/Applications/Sistema Guimma Licenca.app"
DB_CONFIG_APP_PATH="/Applications/CONFIGURAR_BANCO.app"

write_uninstaller "/Applications/Desinstalar Sistema Guimma.command"
if [[ -n "$USER_HOME" && -d "$USER_HOME" ]]; then
  write_uninstaller "$USER_HOME/Applications/Desinstalar Sistema Guimma.command"
  chown "$CURRENT_USER":staff "$USER_HOME/Applications/Desinstalar Sistema Guimma.command" 2>/dev/null || true
fi

RESULT_JSON="/tmp/sistemaguimma_db_setup_result.json"
GUI_SCRIPT="/tmp/sistemaguimma_db_setup_gui.py"
rm -f "$RESULT_JSON" "$GUI_SCRIPT"

cat > "$GUI_SCRIPT" <<'PYGUI'
import json
import os
import shutil
import socket
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

result_path = os.environ.get("RESULT_JSON", "/tmp/sistemaguimma_db_setup_result.json")
assets_base = os.environ.get("APP_ASSETS_DIR", "")


def psql_local_encontrado() -> str:
    candidatos = [
        "/Library/PostgreSQL/18/bin/psql",
        "/Library/PostgreSQL/17/bin/psql",
        "/opt/homebrew/bin/psql",
        "/usr/local/bin/psql",
        shutil.which("psql") or "",
    ]
    for caminho in candidatos:
        if caminho and os.path.exists(caminho):
            return caminho
    return ""


def postgres_local_instalado() -> bool:
    if psql_local_encontrado():
        return True
    candidatos = [
        "/Library/PostgreSQL/18/data/postgresql.conf",
        "/Library/PostgreSQL/17/data/postgresql.conf",
        "/opt/homebrew/var/postgresql@18/postgresql.conf",
        "/usr/local/var/postgresql@18/postgresql.conf",
        "/opt/homebrew/var/postgres/postgresql.conf",
        "/usr/local/var/postgres/postgresql.conf",
    ]
    return any(os.path.exists(caminho) for caminho in candidatos)


def porta_aberta(host: str, porta: int, timeout: float = 1.2) -> bool:
    try:
        with socket.create_connection((host, int(porta)), timeout=timeout):
            return True
    except Exception:
        return False


def gravar_config_usuario(data: dict) -> None:
    h = str(data.get("host") or "").strip()
    p = int(data.get("port") or 5432)
    db = str(data.get("dbname") or "BANCO_OPERA").strip()
    u = str(data.get("user") or "postgres").strip()
    pw = str(data.get("password") or "")
    sc = str(data.get("schema") or "opera").strip() or "opera"
    dsn = f"postgresql://{u}:{pw}@{h}:{p}/{db}"
    payload = {
        "validated_ok": True,
        "mode": str(data.get("mode") or "local"),
        "host": h,
        "port": p,
        "dbname": db,
        "user": u,
        "password": pw,
        "schema": sc,
        "pg_schema": sc,
        "dsn": dsn,
        "pg_dsn": dsn,
        "appname": "SistemaGuimma",
        "defaults": {"dbname": db, "user": u, "password": pw},
        "hosts": [h],
        "ports": [p],
        "connect_timeout": 8,
        "auto_detect_ports": True,
        "fallback_to_postgres": True,
    }
    destinos = [
        Path.home() / "Library" / "Application Support" / "SistemaGuimma" / "config.json",
        Path.home() / "Library" / "Application Support" / "SistemaGuimma" / "PAGINAS_DO_SISTEMA" / "config.json",
    ]
    for destino in destinos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


root = tk.Tk()
root.title("Configuração do Banco - Sistema Guimma")
root.resizable(False, False)

bg = "#0B1320"
panel = "#0E1A2E"
fg = "#EAF2FF"
muted = "#9FB3C8"
root.configure(bg=bg)

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
win_w = min(980, max(860, screen_w - 120))
win_h = min(620, max(540, screen_h - 140))
pos_x = max(0, (screen_w - win_w) // 2)
pos_y = max(0, (screen_h - win_h) // 2)
root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
root.lift()
root.attributes("-topmost", True)
root.after(2500, lambda: root.attributes("-topmost", False))
root.after(300, root.focus_force)

canvas = tk.Canvas(root, width=win_w, height=win_h, highlightthickness=0, bd=0)
canvas.pack(fill="both", expand=True)
canvas.configure(bg=bg)

bg_img = None
icon_img = None
icon_mark = None

# Fundo com FUNDO_LOGUIN.jpg (preferência com PIL para redimensionar corretamente)
try:
    if assets_base:
        fundo = os.path.join(assets_base, "FUNDO_LOGUIN.jpg")
        if os.path.exists(fundo):
            if Image is not None:
                im = Image.open(fundo).convert("RGB").resize((win_w, win_h), Image.Resampling.LANCZOS)
                bg_img = ImageTk.PhotoImage(im)
            else:
                bg_img = tk.PhotoImage(file=fundo)
            canvas.create_image(0, 0, image=bg_img, anchor="nw")
except Exception:
    pass

# Borda colorida inspirada no FUNDO_LOGUIN (azul/laranja)
margin = 18
canvas.create_rectangle(margin, margin, win_w - margin, win_h - margin, outline="#1CC8FF", width=2)
canvas.create_rectangle(margin + 6, margin + 6, win_w - margin - 6, win_h - margin - 6, outline="#FF7A18", width=1)
canvas.create_line(margin + 10, margin + 10, win_w - margin - 10, margin + 10, fill="#34D4FF", width=2)
canvas.create_line(margin + 10, win_h - margin - 10, win_w - margin - 10, win_h - margin - 10, fill="#FF8E2A", width=2)

panel_m = 34
panel_x1, panel_y1 = panel_m, panel_m
panel_x2, panel_y2 = win_w - panel_m, win_h - panel_m
canvas.create_rectangle(panel_x1, panel_y1, panel_x2, panel_y2, fill=panel, outline="#2B3950", width=2)

content = tk.Frame(root, bg=panel)
content_w = panel_x2 - panel_x1 - 24
content_h = panel_y2 - panel_y1 - 24
canvas.create_window((panel_x1 + panel_x2)//2, (panel_y1 + panel_y2)//2, window=content, width=content_w, height=content_h)

header = tk.Frame(content, bg=panel)
header.pack(fill="x", pady=(6, 8))

try:
    if assets_base:
        icon_path = os.path.join(assets_base, "ICONE_SISTEMA.png")
        if os.path.exists(icon_path):
            if Image is not None:
                ico = Image.open(icon_path).convert("RGBA")
                ico_head = ico.resize((42, 42), Image.Resampling.LANCZOS)
                icon_img = ImageTk.PhotoImage(ico_head)

                wm = ico.resize((200, 200), Image.Resampling.LANCZOS)
                alpha = wm.split()[-1].point(lambda a: int(a * 0.10))
                wm.putalpha(alpha)
                icon_mark = ImageTk.PhotoImage(wm)
            else:
                # Sem PIL: usa somente ícone pequeno no cabeçalho para evitar sobreposição visual
                icon_img = tk.PhotoImage(file=icon_path)
                try:
                    icon_img = icon_img.subsample(max(1, icon_img.width() // 42), max(1, icon_img.height() // 42))
                except Exception:
                    pass
                icon_mark = None

            tk.Label(header, image=icon_img, bg=panel).pack(side="left", padx=(8, 12))
except Exception:
    pass

# Marca d'água com ícone do sistema no cartão (no canvas, atrás dos campos)
if icon_mark is not None:
    canvas.create_image(panel_x2 - 120, panel_y2 - 120, image=icon_mark, anchor="center")

text_hdr = tk.Frame(header, bg=panel)
text_hdr.pack(side="left", fill="x", expand=True)



# mantém referências de imagens para evitar garbage collection
root._bg_img = bg_img
root._icon_img = icon_img
root._icon_mark = icon_mark
tk.Label(text_hdr, text="Configuração do Banco de Dados", font=("Segoe UI", 16, "bold"), fg=fg, bg=panel).pack(anchor="w")
tk.Label(text_hdr, text="Instalação do Sistema Guimma • Configure local/rede, teste conexão e conclua.", font=("Segoe UI", 10), fg=muted, bg=panel).pack(anchor="w", pady=(2, 0))

form = tk.Frame(content, bg=panel)
form.pack(fill="x", padx=12, pady=8)

modo = tk.StringVar(value="local")
host = tk.StringVar(value="localhost")
porta = tk.StringVar(value="5432")
dbname = tk.StringVar(value="BANCO_OPERA")
usuario = tk.StringVar(value="postgres")
senha = tk.StringVar(value="")
schema = tk.StringVar(value="opera")
status = tk.StringVar(value="Aguardando validação.")
aviso_banco = tk.StringVar(value="")
validado = {"ok": False}


def invalida(*_):
    validado["ok"] = False
    status.set("Dados alterados. Clique em Testar conexão.")

for v in (host, porta, dbname, usuario, senha, schema):
    v.trace_add("write", invalida)


def set_modo_local():
    if modo.get() == "local":
        host.set("localhost")
    atualizar_aviso_banco()


def set_modo_rede():
    atualizar_aviso_banco()


def atualizar_aviso_banco():
    if modo.get() == "local":
        if postgres_local_instalado():
            aviso_banco.set("Servidor/local: PostgreSQL detectado neste Mac. Teste a porta antes de concluir.")
        else:
            aviso_banco.set(
                "Servidor/local: PostgreSQL não encontrado neste Mac. "
                "Instale o banco no servidor antes de concluir, ou escolha Cliente/rede."
            )
    else:
        aviso_banco.set(
            "Cliente/rede: informe o IP do servidor onde o PostgreSQL e o banco do Sistema Guimma já estão prontos."
        )

linha_modo = tk.Frame(form, bg=panel)
linha_modo.grid(row=0, column=0, columnspan=4, sticky="w", pady=(2, 10))

tk.Label(linha_modo, text="Tipo de instalação:", font=("Segoe UI", 10, "bold"), fg=fg, bg=panel).pack(side="left", padx=(0, 8))
tk.Radiobutton(linha_modo, text="Servidor/local", variable=modo, value="local", command=set_modo_local, fg=fg, bg=panel, selectcolor=panel, activebackground=panel).pack(side="left")
tk.Radiobutton(linha_modo, text="Cliente/rede", variable=modo, value="rede", command=set_modo_rede, fg=fg, bg=panel, selectcolor=panel, activebackground=panel).pack(side="left", padx=(12,0))

tk.Label(
    form,
    textvariable=aviso_banco,
    fg="#FFD08A",
    bg=panel,
    font=("Segoe UI", 10),
    wraplength=820,
    justify="left",
).grid(row=1, column=0, columnspan=4, sticky="w", padx=6, pady=(0, 8))


def campo(r, c, titulo, var, show=""):
    tk.Label(form, text=titulo, fg=fg, bg=panel, font=("Segoe UI", 10)).grid(row=r, column=c, sticky="w", padx=6, pady=(4,2))
    e = tk.Entry(form, textvariable=var, show=show, bg="#1A2332", fg="#F5F8FF", insertbackground="#F5F8FF", relief="flat", font=("Segoe UI", 11))
    e.grid(row=r+1, column=c, sticky="ew", padx=6, pady=(0,8), ipady=6)
    return e

for col in range(4):
    form.grid_columnconfigure(col, weight=1)

campo(2, 0, "Host/IP", host)
campo(2, 1, "Porta", porta)
campo(2, 2, "Banco", dbname)
campo(2, 3, "Schema", schema)
campo(4, 0, "Usuário", usuario)
entry_senha = campo(4, 1, "Senha", senha, show="•")

mostrar_senha = tk.BooleanVar(value=False)

def toggle_senha():
    entry_senha.configure(show="" if mostrar_senha.get() else "•")

chk_senha = tk.Checkbutton(
    form,
    text="Mostrar senha",
    variable=mostrar_senha,
    command=toggle_senha,
    fg=muted,
    bg=panel,
    selectcolor=panel,
    activebackground=panel,
)
chk_senha.grid(row=6, column=1, sticky="w", padx=6, pady=(0, 8))
atualizar_aviso_banco()


def detectar_porta():
    h = host.get().strip()
    if not h:
        messagebox.showerror("Erro", "Informe o Host/IP para detectar a porta.", parent=root)
        return
    if modo.get() == "local" and not postgres_local_instalado():
        messagebox.showwarning(
            "PostgreSQL não encontrado",
            "Não encontrei PostgreSQL instalado neste Mac.\n\n"
            "Para usar este Mac como servidor/local, instale o PostgreSQL no servidor e rode a criação do banco.\n"
            "Para uma estação cliente, escolha Cliente/rede e informe o IP do servidor.",
            parent=root,
        )
        status.set("PostgreSQL local não encontrado.")
        atualizar_aviso_banco()
        return
    for p in (5432, 5433, 5434, 5435, 5436):
        if porta_aberta(h, p):
            porta.set(str(p))
            status.set(f"Porta detectada: {p}")
            return
    messagebox.showwarning("Atenção", "Não foi possível detectar porta automaticamente.", parent=root)


def testar_conexao():
    h = host.get().strip()
    ptxt = porta.get().strip()
    if not h or not ptxt:
        messagebox.showerror("Erro", "Informe Host/IP e Porta.", parent=root)
        return
    try:
        p = int(ptxt)
    except ValueError:
        messagebox.showerror("Erro", "Porta deve ser numérica.", parent=root)
        return
    if modo.get() == "local" and not postgres_local_instalado() and not porta_aberta(h, p):
        validado["ok"] = False
        status.set("PostgreSQL local não encontrado.")
        messagebox.showerror(
            "PostgreSQL não encontrado",
            "Não encontrei PostgreSQL ativo neste Mac.\n\n"
            "Em instalação de servidor/local, primeiro instale o PostgreSQL e crie o banco BANCO_OPERA.\n"
            "Em instalação de cliente/rede, selecione Cliente/rede e informe o IP do servidor.",
            parent=root,
        )
        atualizar_aviso_banco()
        return
    if porta_aberta(h, p):
        validado["ok"] = True
        status.set("Conexão host/porta validada. Pode salvar.")
        messagebox.showinfo("Conexão OK", "Host/porta responderam com sucesso.", parent=root)
    else:
        validado["ok"] = False
        status.set("Falha na conexão host/porta.")
        messagebox.showerror("Falha", "Não foi possível conectar no host/porta informados.", parent=root)


def salvar():
    h = host.get().strip()
    ptxt = porta.get().strip()
    db = dbname.get().strip()
    u = usuario.get().strip()
    pw = senha.get()
    sc = schema.get().strip() or "opera"

    if not h or not ptxt or not db or not u:
        messagebox.showerror("Erro", "Preencha host, porta, banco e usuário.", parent=root)
        return
    try:
        p = int(ptxt)
    except ValueError:
        messagebox.showerror("Erro", "Porta deve ser numérica.", parent=root)
        return
    if not validado["ok"]:
        messagebox.showerror("Erro", "Clique em Testar conexão antes de salvar.", parent=root)
        return

    data = {
        "host": h,
        "port": p,
        "dbname": db,
        "user": u,
        "password": pw,
        "schema": sc,
        "mode": modo.get(),
    }
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    try:
        gravar_config_usuario(data)
        messagebox.showinfo("Configuração salva", "Banco configurado para este usuário.", parent=root)
    except Exception as exc:
        messagebox.showerror("Erro ao salvar", f"Não foi possível salvar a configuração local.\n\n{exc}", parent=root)
        return
    root.destroy()


barr = tk.Frame(content, bg=panel)
barr.pack(fill="x", padx=12, pady=(8,0))

tk.Label(barr, textvariable=status, fg="#B8CCE0", bg=panel, font=("Segoe UI", 10)).pack(side="left")

btns = tk.Frame(content, bg=panel)
btns.pack(fill="x", padx=12, pady=(12, 6))

ttk.Style().configure("Guimma.TButton", padding=8)

ttk.Button(btns, text="Detectar porta", command=detectar_porta).pack(side="left")
ttk.Button(btns, text="Testar conexão", command=testar_conexao).pack(side="left", padx=(10,0))
ttk.Button(btns, text="Salvar e concluir instalação", command=salvar).pack(side="right")

root.mainloop()
PYGUI

chmod +x "$GUI_SCRIPT"

if [[ -n "$CURRENT_USER" && "$CURRENT_USER" != "root" ]]; then
  su -l "$CURRENT_USER" -c "APP_ASSETS_DIR='/Applications/Sistema Guimma.app/Contents/Resources/PAGINAS_DO_SISTEMA' RESULT_JSON='$RESULT_JSON' nohup python3 '$GUI_SCRIPT' >/tmp/sistemaguimma_db_setup_gui.log 2>&1 &" || true
else
  APP_ASSETS_DIR='/Applications/Sistema Guimma.app/Contents/Resources/PAGINAS_DO_SISTEMA' RESULT_JSON="$RESULT_JSON" nohup python3 "$GUI_SCRIPT" >/tmp/sistemaguimma_db_setup_gui.log 2>&1 &
fi

echo "Assistente de banco iniciado em segundo plano. A instalação do app seguirá sem aguardar a configuração." >&2

install_license_launch_agent() {
  if [[ -z "$CURRENT_USER" || "$CURRENT_USER" == "root" || ! -d "$USER_HOME" ]]; then
    return 0
  fi
  if [[ ! -x "$LICENSE_APP_PATH/Contents/MacOS/SistemaGuimmaLicenca" ]]; then
    return 0
  fi

  local launch_dir="$USER_HOME/Library/LaunchAgents"
  local plist="$launch_dir/com.sistemaguimma.licenca.plist"
  mkdir -p "$launch_dir"
  cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.sistemaguimma.licenca</string>
  <key>ProgramArguments</key>
  <array>
    <string>$LICENSE_APP_PATH/Contents/MacOS/SistemaGuimmaLicenca</string>
    <string>--daemon</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StartInterval</key>
  <integer>3600</integer>
  <key>KeepAlive</key>
  <false/>
</dict>
</plist>
PLIST
  chown "$CURRENT_USER":staff "$plist" 2>/dev/null || true
  chmod 644 "$plist" 2>/dev/null || true
  su -l "$CURRENT_USER" -c "launchctl unload '$plist' >/dev/null 2>&1 || true; launchctl load '$plist' >/dev/null 2>&1 || true" 2>/dev/null || true
}

# Ajusta permissões e força refresh visual do Finder/LaunchServices
if [[ -d "$SYSTEM_APP_PATH" ]]; then
  chown -R root:wheel "$SYSTEM_APP_PATH" 2>/dev/null || true
  chmod -R a+rX "$SYSTEM_APP_PATH" 2>/dev/null || true
  if [[ -d "$LICENSE_APP_PATH" ]]; then
    chown -R root:wheel "$LICENSE_APP_PATH" 2>/dev/null || true
    chmod -R a+rX "$LICENSE_APP_PATH" 2>/dev/null || true
    touch "$LICENSE_APP_PATH" 2>/dev/null || true
    install_license_launch_agent
  fi
  if [[ -d "$DB_CONFIG_APP_PATH" ]]; then
    chown -R root:wheel "$DB_CONFIG_APP_PATH" 2>/dev/null || true
    chmod -R a+rX "$DB_CONFIG_APP_PATH" 2>/dev/null || true
    touch "$DB_CONFIG_APP_PATH" 2>/dev/null || true
  fi
  touch /Applications 2>/dev/null || true
  touch "$SYSTEM_APP_PATH" 2>/dev/null || true
  LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
  if [[ -x "$LSREGISTER" ]]; then
    "$LSREGISTER" -f "$SYSTEM_APP_PATH" >/dev/null 2>&1 || true
    if [[ -d "$LICENSE_APP_PATH" ]]; then
      "$LSREGISTER" -f "$LICENSE_APP_PATH" >/dev/null 2>&1 || true
    fi
    if [[ -d "$DB_CONFIG_APP_PATH" ]]; then
      "$LSREGISTER" -f "$DB_CONFIG_APP_PATH" >/dev/null 2>&1 || true
    fi
    "$LSREGISTER" -r -domain local -domain system -domain user >/dev/null 2>&1 || true
  fi
  killall Finder >/dev/null 2>&1 || true
  killall Dock >/dev/null 2>&1 || true
else
  echo "ERRO: Sistema Guimma.app não foi encontrado em /Applications após a instalação." >&2
fi

# Não abortar instalação por falhas tardias do postinstall
exit 0
POSTINSTALL
    chmod +x "$PKG_SCRIPTS/postinstall"

    log_info "Gerando PKG com instalação em /Applications + assistente de banco..."
    pkgbuild --analyze --root "$PKG_ROOT" "$PKG_COMPONENTS"
    python3 - "$PKG_COMPONENTS" <<'PYPLIST'
import plistlib
import sys

path = sys.argv[1]
with open(path, "rb") as f:
    components = plistlib.load(f)

for component in components:
    if isinstance(component, dict):
        component["BundleIsRelocatable"] = False

with open(path, "wb") as f:
    plistlib.dump(components, f)
PYPLIST
    pkgbuild \
      --root "$PKG_ROOT" \
      --component-plist "$PKG_COMPONENTS" \
      --scripts "$PKG_SCRIPTS" \
      --identifier "com.sistemaguimma.app" \
      --version "$APP_VERSION" \
      --install-location "/" \
      "$PKG_PATH"

    rm -rf "$PKG_SCRIPTS" "$PKG_ROOT" "$PKG_COMPONENTS"

    if [ -f "$PKG_PATH" ]; then
        mkdir -p "$INSTALLER_DIR"
        cp -f "$PKG_PATH" "$VERSIONED_PKG_PATH"
        PKG_SIZE=$(du -sh "$PKG_PATH" | cut -f1)
        log_success "PKG criado: $PKG_PATH ($PKG_SIZE)"
        log_success "PKG versionado: $VERSIONED_PKG_PATH"
    else
        log_error "Falha ao criar PKG"
        return 1
    fi
}

# Função principal
main() {
    parse_args "$@"
    ensure_macos

    print_header "SISTEMA GUIMMA - INSTALADOR macOS"
    log_info "Data: $(date)"
    log_info "Diretório: $(pwd)"
    log_info "Versão: $APP_VERSION"

    # Verificar dependências
    check_dependencies

    # Preparar ícone
    if ! prepare_icon; then
        log_warning "Continuando sem ícone personalizado"
    fi

    # Construir aplicativo
    build_app
    build_license_app
    build_db_config_app

    # DMG: padrão sempre gera; pergunta apenas se --interactive
    if [[ "$INTERACTIVE_MODE" == "yes" && "$CREATE_DMG" == "" ]]; then
        echo ""
        read -p "Deseja criar um instalador DMG? (s/n): " -n 1 -r
        echo ""
        [[ $REPLY =~ ^[Ss]$ ]] && CREATE_DMG="yes" || CREATE_DMG="no"
    fi

    if [[ "$CREATE_DMG" == "yes" ]]; then
        create_dmg
    else
        log_info "Pulando criação do DMG"
    fi

    # PKG: padrão sempre gera; pergunta apenas se --interactive
    if [[ "$INTERACTIVE_MODE" == "yes" && "$CREATE_PKG" == "" ]]; then
        echo ""
        read -p "Deseja criar um instalador PKG (duplo clique)? (s/n): " -n 1 -r
        echo ""
        [[ $REPLY =~ ^[Ss]$ ]] && CREATE_PKG="yes" || CREATE_PKG="no"
    fi

    if [[ "$CREATE_PKG" == "yes" ]]; then
        create_pkg
    else
        log_info "Pulando criação do PKG"
    fi

    print_header "INSTALAÇÃO CONCLUÍDA"
    log_success "Processo finalizado com sucesso!"
    echo ""
    log_info "📦 Aplicativo criado em: dist/${APP_BUNDLE_NAME}.app"
    if [ -f "dist/${APP_BUNDLE_NAME}.dmg" ]; then
        log_info "📀 Instalador DMG em: dist/${APP_BUNDLE_NAME}.dmg"
    fi
    if [ -f "dist/${APP_BUNDLE_NAME}.pkg" ]; then
        log_info "📦 Instalador PKG em: dist/${APP_BUNDLE_NAME}.pkg"
    fi
    if [ -f "dist/installers/macos/${APP_BUNDLE_NAME} ${APP_VERSION} macOS.dmg" ]; then
        log_info "📀 DMG final: dist/installers/macos/${APP_BUNDLE_NAME} ${APP_VERSION} macOS.dmg"
    fi
    if [ -f "dist/installers/macos/${APP_BUNDLE_NAME} ${APP_VERSION} macOS.pkg" ]; then
        log_info "📦 PKG final: dist/installers/macos/${APP_BUNDLE_NAME} ${APP_VERSION} macOS.pkg"
    fi
    echo ""
    log_info "Para testar o aplicativo:"
    log_info "  open \"dist/${APP_BUNDLE_NAME}.app\""
    echo ""
}

# Executar função principal
main "$@"
