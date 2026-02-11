#!/bin/bash
# packaging/macos/build_installer.sh
# Script para construir instalador macOS do Sistema Opera

set -e  # Sai no primeiro erro

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

# Verificar se estamos no macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    log_error "Este script deve ser executado no macOS"
    exit 1
fi

# Verificar dependências
check_dependencies() {
    print_header "VERIFICANDO DEPENDÊNCIAS"

    # Verificar Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 não encontrado"
        exit 1
    fi
    log_info "Python3: $(python3 --version)"

    # Verificar pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 não encontrado"
        exit 1
    fi
    log_info "pip3: disponível"

    # Verificar PyInstaller
    if ! python3 -c "import PyInstaller" &> /dev/null; then
        log_warning "PyInstaller não instalado. Instalando..."
        pip3 install pyinstaller
    fi
    log_info "PyInstaller: disponível"

    # Verificar psycopg2
    if ! python3 -c "import psycopg2" &> /dev/null; then
        log_warning "psycopg2 não instalado. Instalando..."
        pip3 install psycopg2-binary
    fi
    log_info "psycopg2: disponível"

    # Verificar Pillow
    if ! python3 -c "import PIL" &> /dev/null; then
        log_warning "Pillow não instalado. Instalando..."
        pip3 install pillow
    fi
    log_info "Pillow: disponível"

    # Verificar FPDF2
    if ! python3 -c "import fpdf" &> /dev/null; then
        log_warning "fpdf2 não instalado. Instalando..."
        pip3 install fpdf2
    fi
    log_info "fpdf/fpdf2: disponível"

    # Verificar ReportLab
    if ! python3 -c "import reportlab" &> /dev/null; then
        log_warning "reportlab não instalado. Instalando..."
        pip3 install reportlab
    fi
    log_info "reportlab: disponível"

    # Verificar Matplotlib
    if ! python3 -c "import matplotlib" &> /dev/null; then
        log_warning "matplotlib não instalado. Instalando..."
        pip3 install matplotlib
    fi
    log_info "matplotlib: disponível"
}

# Preparar ícone para macOS
prepare_icon() {
    print_header "PREPARANDO ÍCONE"

    # Caminhos
    PNG_ICON="icons/ICONE_SISTEMA.png"
    ICNS_ICON="icons/ICONE_SISTEMA.icns"

    if [ -f "$PNG_ICON" ]; then
        log_info "Convertendo PNG para ICNS..."

        # Criar ícone .icns
        mkdir -p "icons/ICONE_SISTEMA.iconset"

        # Gerar múltiplos tamanhos
        sizes=(16 32 64 128 256 512 1024)
        for size in "${sizes[@]}"; do
            sips -z $size $size "$PNG_ICON" --out "icons/ICONE_SISTEMA.iconset/icon_${size}x${size}.png" > /dev/null
            sips -z $((size*2)) $((size*2)) "$PNG_ICON" --out "icons/ICONE_SISTEMA.iconset/icon_${size}x${size}@2x.png" > /dev/null
        done

        # Criar .icns
        iconutil -c icns "icons/ICONE_SISTEMA.iconset" -o "$ICNS_ICON"

        # Limpar pasta temporária
        rm -rf "icons/ICONE_SISTEMA.iconset"

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
    ICON_PATH="icons/ICONE_SISTEMA.icns"
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

    # Comando PyInstaller
    cmd="pyinstaller --windowed --noconsole --name SistemaOpera \
        --add-data 'PAGINAS_DO_SISTEMA:PAGINAS_DO_SISTEMA' \
        --add-data 'icons:icons' \
        --add-data 'data:data' \
        --hidden-import psycopg2 \
        --hidden-import psycopg2.extras \
        --hidden-import PIL \
        --hidden-import PIL._imaging \
        --hidden-import PIL.Image \
        --hidden-import PIL.ImageFile \
        --hidden-import PIL.ImageOps \
        --hidden-import PIL.ImageDraw \
        --hidden-import PIL.ImageFont \
        --hidden-import PIL.ImageTk \
        --hidden-import tkinter \
        --hidden-import tkinter.ttk \
        --hidden-import fpdf \
        --hidden-import fpdf.enums \
        --hidden-import reportlab \
        --hidden-import reportlab.pdfgen \
        --hidden-import reportlab.pdfbase \
        --hidden-import reportlab.lib \
        --hidden-import reportlab.graphics \
        --hidden-import matplotlib \
        --hidden-import matplotlib.pyplot \
        --hidden-import matplotlib.backends.backend_tkagg \
        --hidden-import numpy \
        --collect-all fpdf \
        --collect-all reportlab \
        --collect-all matplotlib \
        $ICON_ARG \
        '$MAIN_SCRIPT'"

    log_info "Executando: $cmd"
    eval $cmd

    # Verificar se o app foi criado
    APP_PATH="dist/SistemaOpera.app"
    if [ -d "$APP_PATH" ]; then
        log_success "Aplicativo criado: $APP_PATH"

        # Exibir informações
        APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
        log_info "Tamanho do aplicativo: $APP_SIZE"

        # Listar conteúdo
        log_info "Conteúdo do aplicativo:"
        find "$APP_PATH" -type f -name "*.so" -o -name "*.dylib" | head -10 | while read file; do
            log_info "  - $(basename "$file")"
        done
    else
        log_error "Aplicativo não foi criado"
        exit 1
    fi
}

# Criar DMG
create_dmg() {
    print_header "CRIANDO INSTALADOR DMG"

    APP_PATH="dist/SistemaOpera.app"
    DMG_PATH="dist/SistemaOpera.dmg"

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

    # Criar link para Applications
    ln -s /Applications "$TEMP_DIR/Applications"

    # Configurações do DMG
    VOLUME_NAME="SistemaOpera"

    # Criar DMG
    hdiutil create -volname "$VOLUME_NAME" \
        -srcfolder "$TEMP_DIR" \
        -ov -format UDZO \
        "$DMG_PATH"

    # Limpar pasta temporária
    rm -rf "$TEMP_DIR"

    if [ -f "$DMG_PATH" ]; then
        DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
        log_success "DMG criado: $DMG_PATH ($DMG_SIZE)"

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

    APP_PATH="dist/SistemaOpera.app"
    PKG_PATH="dist/SistemaOpera.pkg"
    PKG_ROOT="dist/pkg_root"
    PKG_SCRIPTS="dist/pkg_scripts"

    if [ ! -d "$APP_PATH" ]; then
        log_error "Aplicativo não encontrado: $APP_PATH"
        return 1
    fi

    if ! command -v pkgbuild &> /dev/null; then
        log_error "pkgbuild não encontrado (Xcode Command Line Tools necessário)"
        return 1
    fi

    rm -rf "$PKG_ROOT" "$PKG_SCRIPTS"
    mkdir -p "$PKG_ROOT/Applications" "$PKG_SCRIPTS"
    cp -R "$APP_PATH" "$PKG_ROOT/Applications/"

    cat > "$PKG_SCRIPTS/postinstall" <<'POSTINSTALL'
#!/bin/bash
set -e

CURRENT_USER=$(stat -f%Su /dev/console 2>/dev/null || echo "")
if [[ -z "$CURRENT_USER" || "$CURRENT_USER" == "root" ]]; then
  CURRENT_USER=$(ls -l /dev/console | awk '{print $3}')
fi

run_as_user() {
  local script="$1"
  if [[ -n "$CURRENT_USER" && "$CURRENT_USER" != "root" ]]; then
    su -l "$CURRENT_USER" -c "osascript -e '$script'"
  else
    osascript -e "$script"
  fi
}

ask_value() {
  local prompt="$1"
  local default="$2"
  run_as_user "text returned of (display dialog \"$prompt\" default answer \"$default\" with icon note buttons {\"Cancelar\",\"OK\"} default button \"OK\")"
}

HOST=$(ask_value "Informe o Host/IP do banco:" "localhost")
[[ -z "$HOST" ]] && exit 1

DETECT=$(run_as_user 'button returned of (display dialog "Deseja detectar a porta automaticamente?" buttons {"Não","Sim"} default button "Sim")')
if [[ "$DETECT" == "Sim" ]]; then
  PORT=""
  for p in 5432 5433 5434 5435 5436; do
    if nc -z -G 2 "$HOST" "$p" >/dev/null 2>&1; then
      PORT="$p"
      break
    fi
  done
  if [[ -z "$PORT" ]]; then
    PORT=$(ask_value "Não foi possível detectar a porta. Informe manualmente:" "5432")
  fi
else
  PORT=$(ask_value "Informe a porta do banco:" "5432")
fi

[[ "$PORT" =~ ^[0-9]+$ ]] || exit 1
DBNAME=$(ask_value "Informe o nome do banco:" "BANCO_OPERA")
USER_DB=$(ask_value "Informe o usuário do banco:" "postgres")
PASSWORD=$(ask_value "Informe a senha do banco:" "")
SCHEMA=$(ask_value "Informe o schema:" "opera")

if nc -z -G 2 "$HOST" "$PORT" >/dev/null 2>&1; then
  run_as_user 'display dialog "Conexão host/porta OK." buttons {"Continuar"} default button "Continuar" with icon note'
else
  BTN=$(run_as_user 'button returned of (display dialog "Não foi possível validar host/porta. Deseja continuar mesmo assim?" buttons {"Cancelar","Continuar"} default button "Continuar" with icon caution)')
  [[ "$BTN" == "Continuar" ]] || exit 1
fi

export HOST PORT DBNAME USER_DB PASSWORD SCHEMA CURRENT_USER
python3 - <<'PYCFG'
import json, os
host=os.environ['HOST']
port=int(os.environ['PORT'])
db=os.environ['DBNAME']
user=os.environ['USER_DB']
pwd=os.environ['PASSWORD']
schema=os.environ['SCHEMA'] or 'opera'
paths=['/Library/Application Support/SistemaOpera/config.json']
cu=os.environ.get('CURRENT_USER','').strip()
if cu and cu!='root':
  paths.append(f'/Users/{cu}/Library/Application Support/SistemaOpera/config.json')

dsn=f'postgresql://{user}:{pwd}@{host}:{port}/{db}'
obj={
  'schema': schema,
  'pg_schema': schema,
  'appname': 'OPERA_APP',
  'pg_dsn': dsn,
  'defaults': {'dbname': db, 'user': user, 'password': pwd},
  'hosts': [host],
  'ports': [port],
  'connect_timeout': 10,
  'auto_detect_ports': True,
  'fallback_to_postgres': True,
}
for p in paths:
  os.makedirs(os.path.dirname(p), exist_ok=True)
  with open(p,'w',encoding='utf-8') as f:
    json.dump(obj,f,ensure_ascii=False,indent=2)
PYCFG

if [[ -n "$CURRENT_USER" && "$CURRENT_USER" != "root" ]]; then
  chown "$CURRENT_USER":staff "/Users/$CURRENT_USER/Library/Application Support/SistemaOpera/config.json" 2>/dev/null || true
fi

run_as_user 'display dialog "Configuração do banco salva. Instalação concluída." buttons {"OK"} default button "OK" with icon note'
exit 0
POSTINSTALL
    chmod +x "$PKG_SCRIPTS/postinstall"

    log_info "Gerando PKG com instalação em /Applications + assistente de banco..."
    pkgbuild \
      --root "$PKG_ROOT" \
      --scripts "$PKG_SCRIPTS" \
      --identifier "com.operafashion.sistemaopera" \
      --version "1.0.0" \
      --install-location "/" \
      "$PKG_PATH"

    rm -rf "$PKG_ROOT" "$PKG_SCRIPTS"

    if [ -f "$PKG_PATH" ]; then
        PKG_SIZE=$(du -sh "$PKG_PATH" | cut -f1)
        log_success "PKG criado: $PKG_PATH ($PKG_SIZE)"
    else
        log_error "Falha ao criar PKG"
        return 1
    fi
}

# Função principal
main() {
    print_header "SISTEMA OPERA - INSTALADOR macOS"
    log_info "Data: $(date)"
    log_info "Diretório: $(pwd)"

    # Verificar dependências
    check_dependencies

    # Preparar ícone
    if ! prepare_icon; then
        log_warning "Continuando sem ícone personalizado"
    fi

    # Construir aplicativo
    build_app

    # Perguntar se deve criar DMG
    echo ""
    read -p "Deseja criar um instalador DMG? (s/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        create_dmg
    else
        log_info "Pulando criação do DMG"
    fi

    # Perguntar se deve criar PKG (duplo clique)
    echo ""
    read -p "Deseja criar um instalador PKG (duplo clique)? (s/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        create_pkg
    else
        log_info "Pulando criação do PKG"
    fi

    print_header "INSTALAÇÃO CONCLUÍDA"
    log_success "Processo finalizado com sucesso!"
    echo ""
    log_info "📦 Aplicativo criado em: dist/SistemaOpera.app"
    if [ -f "dist/SistemaOpera.dmg" ]; then
        log_info "📀 Instalador DMG em: dist/SistemaOpera.dmg"
    fi
    if [ -f "dist/SistemaOpera.pkg" ]; then
        log_info "📦 Instalador PKG em: dist/SistemaOpera.pkg"
    fi
    echo ""
    log_info "Para testar o aplicativo:"
    log_info "  open dist/SistemaOpera.app"
    echo ""
}

# Executar função principal
main "$@"