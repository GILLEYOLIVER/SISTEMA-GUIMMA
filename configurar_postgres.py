import os
import re
import sys
import time
import json
import queue
import shlex
import shutil
import ctypes
import tempfile
import ipaddress
import threading
import subprocess
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox, filedialog

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = (not IS_WINDOWS) and (not IS_MAC)

if IS_WINDOWS:
    import winreg
else:
    winreg = None


APP_TITLE = "Sistema Guimma • Configurador PostgreSQL"
DEFAULT_PORT = "5432"
TAG_HBA = "# --- Sistema Guimma: acesso rede (adicionado automaticamente) ---"
DB_NAME_DEFAULT = "BANCO_OPERA"
MODO_LOCAL = "local"
MODO_REDE = "rede"
PG_MAJOR_VERSION = "18"
PG_INSTALLER_VERSION = "18.4-1"
PG_MAC_DMG_URL = f"https://get.enterprisedb.com/postgresql/postgresql-{PG_INSTALLER_VERSION}-osx.dmg"


# ------------------ ADMIN ------------------

def is_admin() -> bool:
    try:
        if IS_WINDOWS:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        if hasattr(os, "geteuid"):
            return os.geteuid() == 0
        return False
    except Exception:
        return False


def relaunch_as_admin_silent():
    """
    Reabre o app elevado.
    Usado apenas em ações administrativas específicas para evitar abrir a janela inteira
    como administrador e atrapalhar captura de tela.
    """
    if not IS_WINDOWS:
        return False

    try:
        params = " ".join([f'"{a}"' for a in sys.argv])
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        return rc > 32
    except Exception:
        return False


# ------------------ subprocess / utils ------------------

def run_powershell(ps_command: str, timeout: int = 30) -> str:
    if not IS_WINDOWS:
        raise RuntimeError("PowerShell só está disponível no Windows.")

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    if completed.returncode != 0:
        err = (completed.stderr or "").strip()
        out = (completed.stdout or "").strip()
        raise RuntimeError(f"PowerShell falhou.\nCMD: {ps_command}\nSTDOUT: {out}\nSTDERR: {err}")
    return (completed.stdout or "").strip()


def run_cmd(cmd_list, timeout: int = 60, env=None) -> tuple[int, str, str]:
    p = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def run_admin_shell_script(script_content: str, args: list[str], logger, timeout: int = 2400) -> tuple[int, str, str]:
    if not IS_MAC:
        raise RuntimeError("Execução administrativa automática disponível apenas no macOS nesta etapa.")

    workdir = tempfile.mkdtemp(prefix="sistemaguimma_admin_")
    script_path = os.path.join(workdir, "run.sh")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    os.chmod(script_path, 0o700)

    command = " ".join([shlex.quote(script_path), *[shlex.quote(str(a)) for a in args]])
    osa = ["osascript", "-e", f"do shell script {json.dumps(command)} with administrator privileges"]
    logger("macOS pedira a senha de administrador para concluir a etapa do servidor.")
    return run_cmd(osa, timeout=timeout)


def download_file(url: str, destination: str, logger) -> None:
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    tmp = f"{destination}.part"

    logger(f"Baixando PostgreSQL oficial: {url}")
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = ssl.create_default_context()

    request = urllib.request.Request(url, headers={"User-Agent": "SistemaGuimmaInstaller/1.0"})
    last_report = -1
    downloaded = 0
    with urllib.request.urlopen(request, context=context, timeout=60) as response, open(tmp, "wb") as out:
        total_size = int(response.headers.get("Content-Length") or 0)
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                pct = int(min(100, downloaded * 100 / total_size))
                if pct >= last_report + 10:
                    last_report = pct
                    logger(f"Download PostgreSQL: {pct}%")

    os.replace(tmp, destination)
    logger(f"Download concluído: {destination}")


def save_system_db_config(host: str, port: str, dbname: str, user: str, password: str, schema: str, logger=None) -> None:
    host = (host or "localhost").strip()
    port = str(port or DEFAULT_PORT).strip()
    dbname = (dbname or DB_NAME_DEFAULT).strip()
    user = (user or "postgres").strip()
    schema = (schema or "opera").strip() or "opera"
    dsn = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    payload = {
        "validated_ok": True,
        "mode": MODO_LOCAL if host in ("localhost", "127.0.0.1") else MODO_REDE,
        "host": host,
        "port": int(port),
        "dbname": dbname,
        "user": user,
        "password": password or "",
        "schema": schema,
        "pg_schema": schema,
        "dsn": dsn,
        "pg_dsn": dsn,
        "appname": "SistemaGuimma",
        "defaults": {"dbname": dbname, "user": user, "password": password or ""},
        "hosts": [host],
        "ports": [int(port)],
        "connect_timeout": 8,
        "auto_detect_ports": True,
        "fallback_to_postgres": False,
    }

    if IS_MAC:
        base = Path.home() / "Library" / "Application Support" / "SistemaGuimma"
    elif IS_WINDOWS:
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")) / "SistemaGuimma"
    else:
        base = Path.home() / ".config" / "SistemaGuimma"

    destinos = [
        base / "config.json",
        base / "PAGINAS_DO_SISTEMA" / "config.json",
    ]

    for destino in destinos:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if logger:
            logger(f"Configuração salva: {destino}")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_file(path: str) -> str:
    bak = f"{path}.bak_{now_stamp()}"
    shutil.copy2(path, bak)
    return bak


def which_or_empty(cmd_name: str) -> str:
    return shutil.which(cmd_name) or ""


# ------------------ scripts -> Desktop (blindado) ------------------

SQL_SCRIPT_NAMES = {
    "1_CRIAR_BANCO.sql": "banco",
    "2_CRIAR_SCHEMA.sql": "schema",
    "3_CRIAR_TABELAS.sql": "tabelas",
    "APAGAR_TUDO.sql": "apagar",
}


def _script_source_candidates(base_exe: str) -> list[str]:
    meipass = getattr(sys, "_MEIPASS", "")
    cwd = os.getcwd()
    candidates = []

    for base in (base_exe, meipass, cwd):
        if not base:
            continue
        candidates.extend([
            os.path.join(base, "scripts"),
            os.path.join(base, "SCRIPTS"),
        ])

    if getattr(sys, "frozen", False) and IS_MAC:
        # PyInstaller .app keeps --add-data files under Contents/Resources.
        app_root = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", "Resources"))
        candidates.extend([
            os.path.join(app_root, "scripts"),
            os.path.join(app_root, "SCRIPTS"),
        ])

    repo_scripts = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SCRIPTS")
    candidates.extend([
        repo_scripts,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"),
    ])

    seen = set()
    unique = []
    for candidate in candidates:
        norm = os.path.abspath(candidate)
        if norm not in seen:
            seen.add(norm)
            unique.append(candidate)
    return unique


def _folder_has_default_scripts(folder: str) -> bool:
    return bool(folder and os.path.isdir(folder) and all(
        os.path.exists(os.path.join(folder, name))
        for name in ("1_CRIAR_BANCO.sql", "2_CRIAR_SCHEMA.sql", "3_CRIAR_TABELAS.sql")
    ))

def garantir_scripts_na_area_de_trabalho(logger=None) -> str:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    dst = os.path.join(desktop, "scripts")

    if os.path.isdir(dst):
        if logger:
            logger(f"Scripts já existem no Desktop: {dst}")
        return dst

    if getattr(sys, "frozen", False):
        base_exe = os.path.dirname(sys.executable)
    else:
        base_exe = os.path.dirname(os.path.abspath(__file__))

    src_candidates = _script_source_candidates(base_exe)

    src = ""
    for c in src_candidates:
        if _folder_has_default_scripts(c):
            src = c
            break

    if not src:
        if logger:
            logger("Não achei a pasta SCRIPTS/scripts com 1_CRIAR_BANCO, 2_CRIAR_SCHEMA e 3_CRIAR_TABELAS.")
            logger(f"DEBUG frozen={getattr(sys, 'frozen', False)} exe={sys.executable}")
            logger(f"DEBUG _MEIPASS={getattr(sys, '_MEIPASS', '')}")
            logger(f"DEBUG cwd={os.getcwd()}")
        return dst

    try:
        os.makedirs(dst, exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=True)
        if logger:
            logger(f"Scripts copiados para o Desktop: {dst}")
    except Exception as e:
        if logger:
            logger(f"Falha ao copiar scripts para Desktop: {e}")

    return dst


# ------------------ SQL parsing ------------------

def extrair_nome_banco_do_sql(sql_path: str) -> str:
    if not sql_path or not os.path.exists(sql_path):
        return ""

    with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    content = re.sub(r"--.*?$", "", content, flags=re.MULTILINE)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    m = re.search(
        r"\bCREATE\s+DATABASE\s+((?:\"[^\"]+\")|(?:[A-Za-z_][A-Za-z0-9_]*))",
        content,
        flags=re.IGNORECASE,
    )
    if not m:
        return ""

    raw = m.group(1).strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    return raw.strip()


def extrair_encoding_do_sql(sql_path: str) -> str:
    if not sql_path or not os.path.exists(sql_path):
        return ""

    with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    content = re.sub(r"--.*?$", "", content, flags=re.MULTILINE)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    m = re.search(r"\bENCODING\s+['\"]?([A-Za-z0-9_\-]+)['\"]?", content, flags=re.IGNORECASE)
    return (m.group(1).upper().strip() if m else "")


# ------------------ PostgreSQL detection ------------------

def _get_service_imagepath(service_name: str) -> str:
    if not IS_WINDOWS or winreg is None:
        return ""

    key_path = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
        image_path, _ = winreg.QueryValueEx(k, "ImagePath")
    return image_path


def _extract_datadir_from_imagepath(image_path: str) -> str:
    if not image_path:
        return ""

    m = re.search(r'-D\s+"([^"]+)"', image_path)
    if m:
        return m.group(1)

    m2 = re.search(r"-D\s+([^\s]+)", image_path)
    if m2:
        return m2.group(1)

    return ""


def _windows_detect_postgres_service_and_datadir() -> tuple[str, str]:
    candidates = ["postgresql-x64-18", "postgresql-18"]
    for svc in candidates:
        try:
            img = _get_service_imagepath(svc)
            datadir = _extract_datadir_from_imagepath(img)
            if datadir:
                return svc, datadir
        except FileNotFoundError:
            continue
        except Exception:
            continue

    try:
        out = run_powershell(
            r"Get-Service | Where-Object { $_.Name -match 'postgres' -and $_.Name -match '18' } | "
            r"Select-Object -First 1 -ExpandProperty Name",
            timeout=15,
        ).strip()
        if out:
            img = _get_service_imagepath(out)
            datadir = _extract_datadir_from_imagepath(img)
            if datadir:
                return out, datadir
    except Exception:
        pass

    return "", ""


def _mac_detect_postgres_service_and_datadir() -> tuple[str, str]:
    candidates = [
        "/Library/PostgreSQL/18/data",
        "/opt/homebrew/var/postgresql@18",
        "/usr/local/var/postgresql@18",
        "/opt/homebrew/var/postgres",
        "/usr/local/var/postgres",
    ]

    for p in candidates:
        conf = os.path.join(p, "postgresql.conf")
        hba = os.path.join(p, "pg_hba.conf")
        if os.path.isdir(p):
            return "postgresql-18", p

    for brew_name in ("postgresql@18", "postgresql"):
        rc, out, _ = run_cmd(["brew", "services", "list"], timeout=20)
        if rc == 0 and brew_name in out:
            if brew_name == "postgresql@18":
                for p in ("/opt/homebrew/var/postgresql@18", "/usr/local/var/postgresql@18"):
                    conf = os.path.join(p, "postgresql.conf")
                    hba = os.path.join(p, "pg_hba.conf")
                    if os.path.isdir(p) and (os.path.exists(conf) or os.path.exists(hba)):
                        return brew_name, p

    return "", ""


def _linux_detect_postgres_service_and_datadir() -> tuple[str, str]:
    candidates = [
        "/etc/postgresql/18/main",
        "/var/lib/postgresql/18/main",
    ]

    for p in candidates:
        conf = os.path.join(p, "postgresql.conf")
        hba = os.path.join(p, "pg_hba.conf")
        if os.path.isdir(p) and (os.path.exists(conf) or os.path.exists(hba)):
            return "postgresql-18", p

    return "", ""


def detectar_postgres_service_and_datadir() -> tuple[str, str]:
    if IS_WINDOWS:
        return _windows_detect_postgres_service_and_datadir()
    if IS_MAC:
        return _mac_detect_postgres_service_and_datadir()
    return _linux_detect_postgres_service_and_datadir()


def infer_install_root_from_datadir(datadir: str) -> str:
    if not datadir:
        return ""
    return os.path.dirname(os.path.normpath(datadir))


def find_psql_exe(datadir: str) -> str:
    candidates = []

    if IS_WINDOWS:
        root = infer_install_root_from_datadir(datadir)
        if root:
            candidates.append(os.path.join(root, "bin", "psql.exe"))
        candidates.extend([
            r"C:\Program Files\PostgreSQL\18\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
            which_or_empty("psql"),
        ])
    elif IS_MAC:
        candidates.extend([
            "/Library/PostgreSQL/18/bin/psql",
            "/opt/homebrew/bin/psql",
            "/usr/local/bin/psql",
            which_or_empty("psql"),
        ])
    else:
        candidates.extend([
            "/usr/bin/psql",
            "/usr/local/bin/psql",
            which_or_empty("psql"),
        ])

    for p in candidates:
        if p and os.path.exists(p):
            return p

    return ""


def postgres_detectado_completo() -> bool:
    svc, datadir = detectar_postgres_service_and_datadir()
    psql = find_psql_exe(datadir)
    return bool(datadir and psql)


def install_postgres_macos_if_missing(superpassword: str, port: str, logger) -> None:
    if not IS_MAC:
        raise RuntimeError("Instalação automática do PostgreSQL foi implementada para macOS neste pacote.")

    if postgres_detectado_completo():
        logger("PostgreSQL já detectado. Pulando instalação do motor.")
        return

    if not superpassword or len(superpassword) < 6:
        raise RuntimeError("Informe uma senha do PostgreSQL com pelo menos 6 caracteres.")

    download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "SistemaGuimma")
    dmg_path = os.path.join(download_dir, f"postgresql-{PG_INSTALLER_VERSION}-osx.dmg")

    if not os.path.exists(dmg_path) or os.path.getsize(dmg_path) < 100_000_000:
        download_file(PG_MAC_DMG_URL, dmg_path, logger)
    else:
        logger(f"Instalador PostgreSQL já baixado: {dmg_path}")

    secure_dir = tempfile.mkdtemp(prefix="sistemaguimma_pg_")
    pw_file = os.path.join(secure_dir, "pg_password.txt")
    with open(pw_file, "w", encoding="utf-8") as f:
        f.write(superpassword)
    os.chmod(pw_file, 0o600)

    log_file = os.path.join(tempfile.gettempdir(), "sistemaguimma_postgres_install.log")
    script = r'''#!/bin/bash
set -euo pipefail

DMG_PATH="$1"
PW_FILE="$2"
LOG_FILE="$3"
PORT="${4:-5432}"
PG_PREFIX="/Library/PostgreSQL/18"
PG_BIN="$PG_PREFIX/bin"
PG_DATA="$PG_PREFIX/data"

exec >>"$LOG_FILE" 2>&1
echo "==== Sistema Guimma PostgreSQL install $(date) ===="

if [[ -x "$PG_BIN/psql" && -f "$PG_DATA/postgresql.conf" ]]; then
  echo "PostgreSQL 18 já existe em $PG_PREFIX"
  rm -f "$PW_FILE"
  exit 0
fi

SUPERPASSWORD="$(cat "$PW_FILE")"
rm -f "$PW_FILE"

MOUNT_DIR="$(mktemp -d /tmp/sistemaguimma_pg_mount.XXXXXX)"
cleanup() {
  hdiutil detach "$MOUNT_DIR" -quiet >/dev/null 2>&1 || true
  rm -rf "$MOUNT_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Montando DMG: $DMG_PATH"
hdiutil attach "$DMG_PATH" -nobrowse -quiet -mountpoint "$MOUNT_DIR"

INSTALLER="$(find "$MOUNT_DIR" -path "*/Contents/MacOS/installbuilder.sh" -type f -perm -111 2>/dev/null | head -n 1 || true)"
if [[ -z "$INSTALLER" ]]; then
  INSTALLER="$(find "$MOUNT_DIR" -type f -perm -111 -name "postgresql-*osx*" 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "$INSTALLER" ]]; then
  INSTALLER="$(find "$MOUNT_DIR" -type f -perm -111 2>/dev/null | grep -i 'postgresql' | head -n 1 || true)"
fi
if [[ -z "$INSTALLER" ]]; then
  echo "Conteúdo do DMG:"
  find "$MOUNT_DIR" -maxdepth 4 -print
  echo "Instalador PostgreSQL não encontrado dentro do DMG."
  exit 20
fi

echo "Instalador localizado: $INSTALLER"
"$INSTALLER" \
  --mode unattended \
  --unattendedmodeui minimal \
  --superaccount postgres \
  --superpassword "$SUPERPASSWORD" \
  --serverport "$PORT" \
  --servicename postgresql-18 \
  --prefix "$PG_PREFIX" || {
    rc=$?
    echo "Primeira tentativa falhou com rc=$rc; tentando sem parâmetros opcionais."
    "$INSTALLER" \
      --mode unattended \
      --superpassword "$SUPERPASSWORD" \
      --serverport "$PORT" \
      --prefix "$PG_PREFIX"
  }

if [[ -x "$PG_BIN/pg_ctl" && -f "$PG_DATA/postgresql.conf" ]]; then
  "$PG_BIN/pg_ctl" -D "$PG_DATA" -l "$PG_DATA/server.log" start >/dev/null 2>&1 || true
fi

sleep 4
if [[ ! -x "$PG_BIN/psql" ]]; then
  echo "psql não encontrado após instalação em $PG_BIN/psql"
  exit 21
fi

echo "PostgreSQL instalado com sucesso."
'''

    rc, out, err = run_admin_shell_script(script, [dmg_path, pw_file, log_file, str(port or DEFAULT_PORT)], logger)
    if out.strip():
        logger(out.strip())
    if err.strip():
        logger(err.strip())
    if rc != 0:
        raise RuntimeError(f"Falha ao instalar PostgreSQL automaticamente. Veja o log: {log_file}")

    logger(f"PostgreSQL instalado. Log: {log_file}")


def configure_postgres_network_macos(datadir: str, cidr: str, port: str, logger) -> None:
    if not IS_MAC:
        return
    if not datadir or datadir.startswith("(") or not os.path.isdir(datadir):
        raise RuntimeError("DataDir inválido para configurar rede do PostgreSQL.")
    if not cidr or cidr.startswith("(") or "/" not in cidr:
        raise RuntimeError("Rede CIDR inválida para configurar acesso em rede.")

    log_file = os.path.join(tempfile.gettempdir(), "sistemaguimma_postgres_network.log")
    script = r'''#!/bin/bash
set -euo pipefail

DATADIR="$1"
CIDR="$2"
PORT="${3:-5432}"
LOG_FILE="$4"
CONF="$DATADIR/postgresql.conf"
HBA="$DATADIR/pg_hba.conf"

exec >>"$LOG_FILE" 2>&1
echo "==== Sistema Guimma PostgreSQL network $(date) ===="

if [[ ! -f "$CONF" || ! -f "$HBA" ]]; then
  echo "Arquivos não encontrados: $CONF / $HBA"
  exit 30
fi

cp "$CONF" "$CONF.bak_sistemaguimma_$(date +%Y%m%d_%H%M%S)"
cp "$HBA" "$HBA.bak_sistemaguimma_$(date +%Y%m%d_%H%M%S)"

python3 - "$CONF" "$HBA" "$CIDR" <<'PY'
from pathlib import Path
import re
import sys

conf = Path(sys.argv[1])
hba = Path(sys.argv[2])
cidr = sys.argv[3]

lines = conf.read_text(encoding="utf-8", errors="replace").splitlines()
target = "listen_addresses = '*'"
pattern = re.compile(r"^\s*#?\s*listen_addresses\s*=")
for i, line in enumerate(lines):
    if pattern.search(line):
        lines[i] = target
        break
else:
    lines.extend(["", "# --- Sistema Guimma: habilita conexao local e via rede ---", target])
conf.write_text("\n".join(lines) + "\n", encoding="utf-8")

rule = f"host    all             all             {cidr}            scram-sha-256"
tag = "# --- Sistema Guimma: acesso rede (adicionado automaticamente) ---"
lines = hba.read_text(encoding="utf-8", errors="replace").splitlines()
norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
if not any(norm(line) == norm(rule) for line in lines):
    if tag not in lines:
        lines.extend(["", tag])
    lines.append(rule)
hba.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

PG_CTL="/Library/PostgreSQL/18/bin/pg_ctl"
if [[ -x "$PG_CTL" ]]; then
  "$PG_CTL" -D "$DATADIR" restart -m fast >/dev/null 2>&1 || "$PG_CTL" -D "$DATADIR" start >/dev/null 2>&1 || true
fi

echo "Rede configurada para $CIDR na porta $PORT."
'''

    rc, out, err = run_admin_shell_script(script, [datadir, cidr, str(port or DEFAULT_PORT), log_file], logger)
    if out.strip():
        logger(out.strip())
    if err.strip():
        logger(err.strip())
    if rc != 0:
        raise RuntimeError(f"Falha ao configurar rede do PostgreSQL. Veja o log: {log_file}")
    logger(f"Rede PostgreSQL configurada. Log: {log_file}")


# ------------------ Network detection ------------------

def detectar_ip() -> str:
    s = None
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "Não detectado"
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass


def detectar_rede_cidr(ip_alvo: str) -> str:
    if not ip_alvo or ip_alvo == "Não detectado":
        return ""

    if IS_WINDOWS:
        try:
            ps = (
                "Get-NetIPAddress -AddressFamily IPv4 | "
                f"Where-Object {{ $_.IPAddress -eq '{ip_alvo}' }} | "
                "Select-Object -First 1 -ExpandProperty PrefixLength"
            )
            out = run_powershell(ps, timeout=15).strip()
            if out:
                prefix = int(out)
                net = ipaddress.IPv4Network(f"{ip_alvo}/{prefix}", strict=False)
                return f"{net.network_address}/{prefix}"
        except Exception:
            pass

    try:
        net = ipaddress.IPv4Network(f"{ip_alvo}/24", strict=False)
        return f"{net.network_address}/24"
    except Exception:
        return ""


# ------------------ Postgres config changes ------------------

def set_listen_addresses(conf_path: str, logger) -> None:
    with open(conf_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    target = "listen_addresses = '*'"
    pattern = re.compile(r"^\s*#?\s*listen_addresses\s*=")

    changed = False
    for i, line in enumerate(lines):
        if pattern.search(line):
            lines[i] = target
            changed = True
            break

    if not changed:
        lines.append("")
        lines.append("# --- Sistema Guimma: habilita conexao local e via rede ---")
        lines.append(target)

    with open(conf_path, "w", encoding="utf-8", errors="replace") as f:
        f.write("\n".join(lines) + "\n")

    logger(f"postgresql.conf: {target} OK")


def ensure_pg_hba_rule(hba_path: str, network_cidr: str, logger) -> None:
    if not network_cidr:
        raise RuntimeError("Rede CIDR vazia. Não é possível atualizar pg_hba.conf.")

    with open(hba_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()

    rule = f"host    all             all             {network_cidr}            scram-sha-256"
    norm_rule = re.sub(r"\s+", " ", rule).strip().lower()

    for l in lines:
        if re.sub(r"\s+", " ", l).strip().lower() == norm_rule:
            logger(f"pg_hba.conf: regra já existe ({network_cidr})")
            return

    if TAG_HBA not in lines:
        lines.append("")
        lines.append(TAG_HBA)

    lines.append(rule)

    with open(hba_path, "w", encoding="utf-8", errors="replace") as f:
        f.write("\n".join(lines) + "\n")

    logger(f"pg_hba.conf: regra adicionada ({network_cidr})")


def ensure_firewall_rule(port: str, logger) -> None:
    if not IS_WINDOWS:
        logger("Firewall: ajuste automático ignorado neste sistema.")
        return

    rule_name = f"PostgreSQL 18 (Sistema Guimma) - TCP {port}"
    try:
        out = run_powershell(
            f"Get-NetFirewallRule -DisplayName '{rule_name}' -ErrorAction SilentlyContinue | "
            "Select-Object -First 1 -ExpandProperty DisplayName",
            timeout=15,
        )
        if out.strip():
            logger(f"Firewall: regra já existe ({rule_name})")
            return
    except Exception:
        pass

    run_powershell(
        "New-NetFirewallRule "
        f"-DisplayName '{rule_name}' "
        "-Direction Inbound -Action Allow -Protocol TCP "
        f"-LocalPort {port} "
        "-Profile Private | Out-Null",
        timeout=20,
    )
    logger(f"Firewall: regra criada (TCP {port}, Private)")


def restart_service(service_name: str, datadir: str, logger) -> None:
    if IS_WINDOWS:
        run_powershell(f"Restart-Service -Name '{service_name}' -Force", timeout=60)
        time.sleep(2)
        status = run_powershell(f"(Get-Service -Name '{service_name}').Status", timeout=10).strip()
        logger(f"Serviço {service_name}: {status}")
        return

    if IS_MAC:
        for svc in ("postgresql@18", "postgresql"):
            rc, out, err = run_cmd(["brew", "services", "restart", svc], timeout=60)
            if rc == 0:
                logger(f"Serviço reiniciado via brew: {svc}")
                if out.strip():
                    logger(out.strip())
                return

        pg_ctl = ""
        for c in [
            "/Library/PostgreSQL/18/bin/pg_ctl",
            "/opt/homebrew/bin/pg_ctl",
            "/usr/local/bin/pg_ctl",
            which_or_empty("pg_ctl"),
        ]:
            if c and os.path.exists(c):
                pg_ctl = c
                break

        if pg_ctl and datadir:
            rc, out, err = run_cmd([pg_ctl, "-D", datadir, "restart"], timeout=60)
            if rc == 0:
                logger("Serviço reiniciado via pg_ctl.")
                if out.strip():
                    logger(out.strip())
                return

        logger("Não consegui reiniciar automaticamente no macOS. Reinicie o PostgreSQL manualmente.")
        return

    for cmd in (["systemctl", "restart", "postgresql"], ["service", "postgresql", "restart"]):
        rc, out, err = run_cmd(cmd, timeout=60)
        if rc == 0:
            logger(f"Serviço reiniciado: {' '.join(cmd)}")
            return

    logger("Não consegui reiniciar automaticamente no Linux. Reinicie o PostgreSQL manualmente.")


# ------------------ SQL execution ------------------

def run_psql_file(psql_exe: str, host: str, port: str, user: str, password: str,
                  dbname: str, sql_file: str, logger) -> None:
    if not psql_exe or not os.path.exists(psql_exe):
        raise RuntimeError("psql não encontrado (não consigo executar scripts).")
    if not sql_file or not os.path.exists(sql_file):
        raise RuntimeError(f"Arquivo SQL não encontrado: {sql_file}")

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    env["PGCLIENTENCODING"] = "UTF8"

    cmd = [
        psql_exe,
        "-v", "ON_ERROR_STOP=1",
        "-h", host,
        "-p", str(port),
        "-U", user,
        "-d", dbname,
        "-f", sql_file,
    ]

    logger(f"Executando: {os.path.basename(sql_file)} (db={dbname}) ...")
    rc, out, err = run_cmd(cmd, timeout=300, env=env)

    if out.strip():
        logger(out.strip())
    if err.strip():
        logger(err.strip())

    if rc != 0:
        raise RuntimeError(f"Falha ao executar {os.path.basename(sql_file)} (rc={rc}). Veja o log.")


def database_exists(psql_exe: str, host: str, port: str, user: str, password: str,
                    dbname: str, logger) -> bool:
    if not psql_exe or not os.path.exists(psql_exe):
        raise RuntimeError("psql não encontrado (não consigo consultar bancos).")

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    env["PGCLIENTENCODING"] = "UTF8"

    safe_dbname = dbname.replace("'", "''")
    cmd = [
        psql_exe,
        "-v", "ON_ERROR_STOP=1",
        "-h", host,
        "-p", str(port),
        "-U", user,
        "-d", "postgres",
        "-tAc", f"SELECT 1 FROM pg_database WHERE datname = '{safe_dbname}';",
    ]

    logger(f"Verificando se o banco {dbname} já existe...")
    rc, out, err = run_cmd(cmd, timeout=60, env=env)
    if err.strip():
        logger(err.strip())
    if rc != 0:
        raise RuntimeError(f"Não consegui consultar bancos no PostgreSQL (rc={rc}). Veja o log.")

    return out.strip() == "1"


def run_create_database_if_needed(psql_exe: str, host: str, port: str, user: str,
                                  password: str, dbname: str, sql_file: str, logger) -> None:
    if database_exists(psql_exe, host, port, user, password, dbname, logger):
        logger(f"Banco {dbname} já existe. Pulando {os.path.basename(sql_file)}.")
        return

    run_psql_file(psql_exe, host, port, user, password, "postgres", sql_file, logger)


# ------------------ UI helpers ------------------

def centralizar_janela(win: ctk.CTk, width: int, height: int):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = int((sw / 2) - (width / 2))
    y = int((sh / 2) - (height / 2))
    win.geometry(f"{width}x{height}+{x}+{y}")


class ConfigurarPostgresApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.win_width = 1450
        self.win_height = 1020
        centralizar_janela(self, self.win_width, self.win_height)
        self.resizable(True, True)

        self.log_q = queue.Queue()

        self.modo_var = ctk.StringVar(value=MODO_LOCAL)
        self.detected_ip = detectar_ip()
        self.detected_cidr = ""
        self.ip_var = ctk.StringVar(value=self.detected_ip)
        self.port_var = ctk.StringVar(value=DEFAULT_PORT)
        self.net_var = ctk.StringVar(value="(não detectado)")
        self.svc_var = ctk.StringVar(value="(não detectado)")
        self.datadir_var = ctk.StringVar(value="(não detectado)")
        self.psql_var = ctk.StringVar(value="(não detectado)")

        self.user_var = ctk.StringVar(value="postgres")
        self.pass_var = ctk.StringVar(value="")
        self.dbname_var = ctk.StringVar(value=DB_NAME_DEFAULT)

        self.sql_banco_var = ctk.StringVar(value="")
        self.sql_schema_var = ctk.StringVar(value="")
        self.sql_tabelas_var = ctk.StringVar(value="")
        self.sql_apagar_var = ctk.StringVar(value="")

        self._build_ui()
        self._pump_logs()

        self.detect_all(silent=True)
        self._load_default_scripts()
        self._update_mode_ui()

    # ---------- UI ----------
    def _build_ui(self):
        wrapper = ctk.CTkFrame(self, corner_radius=14)
        wrapper.pack(fill="both", expand=True, padx=16, pady=16)

        header = ctk.CTkFrame(wrapper, corner_radius=14)
        header.pack(fill="x", padx=14, pady=(14, 10))

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(fill="x", padx=14, pady=(12, 6))
        title_row.grid_columnconfigure(0, weight=1)
        title_row.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            title_row,
            text="Configuração do PostgreSQL",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            title_row,
            text="Modo Local ou Rede",
            font=ctk.CTkFont(size=13),
        ).grid(row=0, column=1, sticky="e")

        self.hint_lbl = ctk.CTkLabel(
            header,
            text="Fluxo Local: 1) Detectar  •  2) Scripts  •  3) Executar (1→2→3)",
            font=ctk.CTkFont(size=12),
        )
        self.hint_lbl.pack(anchor="w", padx=14, pady=(0, 12))

        content = ctk.CTkFrame(wrapper, corner_radius=14)
        content.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(content, corner_radius=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(14, 7), pady=14)

        right = ctk.CTkFrame(content, corner_radius=14)
        right.grid(row=0, column=1, sticky="nsew", padx=(7, 14), pady=14)

        log_frame = ctk.CTkFrame(wrapper, corner_radius=14)
        log_frame.pack(fill="x", padx=14, pady=(0, 14))

        ctk.CTkLabel(log_frame, text="Log (tempo real)", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=14, pady=(12, 6)
        )
        self.logbox = ctk.CTkTextbox(log_frame, corner_radius=10, height=220)
        self.logbox.pack(fill="both", expand=False, padx=14, pady=(0, 10))
        self.logbox.configure(state="disabled")
        self.status_lbl = ctk.CTkLabel(log_frame, text="Status: pronto", font=ctk.CTkFont(size=12))
        self.status_lbl.pack(anchor="w", padx=14, pady=(0, 12))

        ctk.CTkLabel(left, text="Modo de uso", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=14, pady=(14, 10)
        )

        mode_frame = ctk.CTkFrame(left, corner_radius=12)
        mode_frame.pack(fill="x", padx=14, pady=(0, 14))
        mode_frame.grid_columnconfigure(0, weight=1)
        mode_frame.grid_columnconfigure(1, weight=1)

        self.rb_local = ctk.CTkRadioButton(
            mode_frame,
            text="Banco Local (esta máquina)",
            value=MODO_LOCAL,
            variable=self.modo_var,
            command=self.on_change_mode,
        )
        self.rb_local.grid(row=0, column=0, sticky="w", padx=12, pady=12)

        self.rb_rede = ctk.CTkRadioButton(
            mode_frame,
            text="Servidor / Rede",
            value=MODO_REDE,
            variable=self.modo_var,
            command=self.on_change_mode,
        )
        self.rb_rede.grid(row=0, column=1, sticky="w", padx=12, pady=12)

        self.mode_info_lbl = ctk.CTkLabel(
            mode_frame,
            text="No modo local, o app cria o banco e as tabelas em localhost. No modo rede, também libera acesso externo.",
            justify="left",
            wraplength=560,
        )
        self.mode_info_lbl.grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12))

        ctk.CTkLabel(left, text="Detecção / Ambiente", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=14, pady=(0, 10)
        )

        det = ctk.CTkFrame(left, corner_radius=12)
        det.pack(fill="x", padx=14, pady=(0, 14))
        det.grid_columnconfigure(0, weight=1)
        det.grid_columnconfigure(1, weight=1)

        self.ip_label, self.ip_entry = self._row_entry(det, 0, 0, "IP detectado:", self.ip_var)
        self.port_label, self.port_entry = self._row_entry(det, 0, 1, "Porta:", self.port_var)
        self.net_label, self.net_entry = self._row_entry(det, 2, 0, "Rede (CIDR):", self.net_var)
        self.svc_label, self.svc_entry = self._row_entry(det, 2, 1, "Serviço:", self.svc_var)
        self.datadir_label, self.datadir_entry = self._row_entry(det, 4, 0, "DataDir (-D):", self.datadir_var)
        self.psql_label, self.psql_entry = self._row_entry(det, 4, 1, "psql:", self.psql_var)

        btns = ctk.CTkFrame(left, fg_color="transparent")
        btns.pack(fill="x", padx=14, pady=(0, 14))
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)

        self.btn_detect = ctk.CTkButton(btns, text="Detectar tudo", height=44, command=self.on_detect)
        self.btn_detect.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.btn_config = ctk.CTkButton(
            btns,
            text="Configurar Rede (admin)",
            height=44,
            command=self.on_configure_real,
        )
        self.btn_config.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        quick = ctk.CTkFrame(left, fg_color="transparent")
        quick.pack(fill="x", padx=14, pady=(0, 14))
        quick.grid_columnconfigure(0, weight=1)
        quick.grid_columnconfigure(1, weight=1)

        self.btn_copy = ctk.CTkButton(
            quick,
            text="Copiar conexão",
            height=44,
            fg_color="transparent",
            border_width=2,
            command=self.on_copy,
        )
        self.btn_copy.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.btn_drop = ctk.CTkButton(
            quick,
            text="APAGAR TUDO (PERIGOSO)",
            height=44,
            fg_color="#8B0000",
            command=self.on_run_drop_all,
        )
        self.btn_drop.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        ctk.CTkLabel(right, text="Scripts SQL (deixar pronto para o Sistema Guimma)", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=14, pady=(14, 10)
        )

        scripts = ctk.CTkFrame(right, corner_radius=12)
        scripts.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        scripts.grid_columnconfigure(0, weight=1)
        scripts.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            scripts,
            text="DB alvo (auto pelo 1_CRIAR_BANCO.sql):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 2))

        ctk.CTkEntry(scripts, textvariable=self.dbname_var, height=34).grid(
            row=1, column=0, sticky="ew", padx=12, pady=(0, 10)
        )

        creds = ctk.CTkFrame(scripts, fg_color="transparent")
        creds.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        creds.grid_columnconfigure(0, weight=1)
        creds.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(creds, text="Usuário:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 2)
        )
        ctk.CTkEntry(creds, textvariable=self.user_var, height=34).grid(
            row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 6)
        )

        ctk.CTkLabel(creds, text="Senha:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 2)
        )
        ctk.CTkEntry(creds, textvariable=self.pass_var, show="*", height=34).grid(
            row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 6)
        )

        self._file_picker_row(scripts, 3, "1) Criar Banco (.sql):", self.sql_banco_var, self.pick_sql_banco)
        self._file_picker_row(scripts, 5, "2) Criar Schema (.sql):", self.sql_schema_var, self.pick_sql_schema)
        self._file_picker_row(scripts, 7, "3) Criar Tabelas (.sql):", self.sql_tabelas_var, self.pick_sql_tabelas)
        self._file_picker_row(scripts, 9, "APAGAR TUDO (.sql):", self.sql_apagar_var, self.pick_sql_apagar)

        actions = ctk.CTkFrame(right, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 14))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

        self.btn_folder = ctk.CTkButton(actions, text="Buscar pasta dos scripts", height=44, command=self.pick_scripts_folder)
        self.btn_folder.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.btn_run_all = ctk.CTkButton(
            actions,
            text="EXECUTAR CRIAÇÃO LOCAL (1→2→3)",
            height=44,
            fg_color="#1f8b4c",
            hover_color="#176b3a",
            text_color="white",
            command=self.on_run_create_all,
        )
        self.btn_run_all.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self.btn_auto_server = ctk.CTkButton(
            actions,
            text="INSTALAR POSTGRESQL + CRIAR BANCO",
            height=44,
            fg_color="#0f5f9f",
            hover_color="#0b4b7e",
            text_color="white",
            command=self.on_install_postgres_and_create_all,
        )
        self.btn_auto_server.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=(10, 0))

    def _row_entry(self, parent, row, col, label, var):
        lbl = ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=12, weight="bold"))
        lbl.grid(
            row=row,
            column=col,
            sticky="w",
            padx=(12, 6) if col == 0 else (6, 12),
            pady=(8 if row == 0 else 4, 2),
        )
        ent = ctk.CTkEntry(parent, textvariable=var, height=34)
        ent.grid(
            row=row + 1,
            column=col,
            sticky="ew",
            padx=(12, 6) if col == 0 else (6, 12),
            pady=(0, 6),
        )
        return lbl, ent

    def _file_picker_row(self, parent, row, label, var, cmd_pick):
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=row, column=0, sticky="w", padx=12, pady=(6, 2)
        )
        ctk.CTkEntry(parent, textvariable=var, height=34).grid(
            row=row + 1, column=0, sticky="ew", padx=12, pady=(0, 6)
        )
        ctk.CTkButton(parent, text="Buscar", width=110, height=34, command=cmd_pick).grid(
            row=row + 1, column=1, sticky="e", padx=12, pady=(0, 6)
        )

    # ---------- logging ----------
    def log(self, msg: str):
        self.log_q.put(msg)

    def _pump_logs(self):
        try:
            while True:
                msg = self.log_q.get_nowait()
                self.logbox.configure(state="normal")
                self.logbox.insert("end", msg + "\n")
                self.logbox.see("end")
                self.logbox.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(80, self._pump_logs)

    def set_status(self, text: str):
        self.status_lbl.configure(text=f"Status: {text}")

    def set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        for b in (self.btn_detect, self.btn_config, self.btn_folder, self.btn_run_all, self.btn_auto_server, self.btn_copy, self.btn_drop):
            b.configure(state=state)
        self.rb_local.configure(state=state)
        self.rb_rede.configure(state=state)

    # ---------- mode ----------
    def get_modo(self) -> str:
        modo = (self.modo_var.get() or MODO_LOCAL).strip().lower()
        return MODO_REDE if modo == MODO_REDE else MODO_LOCAL

    def on_change_mode(self):
        self._update_mode_ui()

    def _update_mode_ui(self):
        modo = self.get_modo()
        if modo == MODO_LOCAL:
            self.hint_lbl.configure(text="Fluxo Local: 1) Detectar  •  2) Scripts  •  3) Executar (1→2→3)")
            self.mode_info_lbl.configure(text="Modo Local: usa localhost nesta própria máquina para criar o banco, schema e tabelas. Não exige liberar rede.")
            self.btn_config.configure(state="disabled", text="Rede não necessária no modo local")
            self.btn_run_all.configure(text="EXECUTAR CRIAÇÃO LOCAL (1→2→3)")
            self.ip_label.configure(text="Host local:")
            self.ip_var.set("localhost")
            self.net_var.set("Não se aplica no modo local")
            self.net_entry.configure(state="disabled")
        else:
            self.hint_lbl.configure(text="Fluxo Rede: 1) Detectar  •  2) Configurar Rede  •  3) Scripts  •  4) Executar (1→2→3)")
            self.mode_info_lbl.configure(text="Modo Rede: além de criar o banco, também ajusta listen_addresses, pg_hba.conf e firewall para aceitar conexões de outras máquinas.")
            self.btn_config.configure(state="normal", text="Configurar Rede (admin)")
            self.btn_run_all.configure(text="EXECUTAR CRIAÇÃO NO SERVIDOR (1→2→3)")
            self.ip_label.configure(text="IP detectado:")
            self.ip_var.set(self.detected_ip or detectar_ip())
            self.net_var.set(self.detected_cidr or "(não detectado)")
            self.net_entry.configure(state="normal")

    # ---------- detect ----------
    def detect_all(self, silent: bool = False):
        ip = detectar_ip()
        self.detected_ip = ip

        try:
            cidr = detectar_rede_cidr(ip)
        except Exception:
            cidr = ""
        self.detected_cidr = cidr if cidr else "(não detectado)"

        if self.get_modo() == MODO_LOCAL:
            self.ip_var.set("localhost")
            self.net_var.set("Não se aplica no modo local")
        else:
            self.ip_var.set(ip)
            self.net_var.set(self.detected_cidr)

        svc, datadir = ("", "")
        try:
            svc, datadir = detectar_postgres_service_and_datadir()
        except Exception:
            pass

        self.svc_var.set(svc if svc else "(não detectado)")
        self.datadir_var.set(datadir if datadir else "(não detectado)")

        psql = find_psql_exe(datadir) if datadir else ""
        self.psql_var.set(psql if psql else "(não detectado)")

        if not silent:
            messagebox.showinfo(
                "Detecção",
                f"IP: {self.ip_var.get()}\n"
                f"Rede: {self.net_var.get()}\n"
                f"Serviço: {self.svc_var.get()}\n"
                f"DataDir: {self.datadir_var.get()}\n"
                f"psql: {self.psql_var.get()}",
            )

    def on_detect(self):
        self.detect_all(silent=False)

    # ---------- network ----------
    def on_configure_real(self):
        if self.get_modo() != MODO_REDE:
            messagebox.showinfo(
                "Modo Local",
                "Você está no modo local.\n\nPara criar o banco nesta máquina, use apenas 'EXECUTAR CRIAÇÃO LOCAL (1→2→3)'.",
            )
            return

        self.detect_all(silent=True)

        svc = self.svc_var.get().strip()
        datadir = self.datadir_var.get().strip()
        cidr = self.net_var.get().strip()
        port = self.port_var.get().strip() or DEFAULT_PORT

        if svc.startswith("(") or not svc:
            messagebox.showerror("Erro", "Não detectei o serviço do PostgreSQL 18.")
            return

        if datadir.startswith("(") or not datadir or not os.path.isdir(datadir):
            messagebox.showerror("Erro", "Data Directory (-D) inválido. Instale o PostgreSQL 18 e tente novamente.")
            return

        if cidr.startswith("(") or not cidr or "/" not in cidr:
            messagebox.showerror("Erro", "Não consegui detectar a rede (CIDR). Verifique e tente novamente.")
            return

        conf = os.path.join(datadir, "postgresql.conf")
        hba = os.path.join(datadir, "pg_hba.conf")
        if not os.path.exists(conf) or not os.path.exists(hba):
            messagebox.showerror("Erro", f"Não encontrei:\n{conf}\n{hba}")
            return

        if not messagebox.askyesno(
            "Confirmar",
            "Vou configurar o PostgreSQL para aceitar conexões na rede.\n\n"
            f"Serviço: {svc}\n"
            f"Rede: {cidr}\n"
            f"Porta: {port}\n\n"
            "Continuar?",
        ):
            return

        def worker():
            self.set_busy(True)
            self.set_status("configurando rede...")
            try:
                self.log("=== CONFIGURAÇÃO REAL (REDE) ===")
                self.log(f"Serviço: {svc}")
                self.log(f"DataDir: {datadir}")
                self.log(f"Rede: {cidr}")
                self.log(f"Porta: {port}")
                self.log("")

                self.log("Backups...")
                bak_conf = backup_file(conf)
                bak_hba = backup_file(hba)
                self.log(f"Backup conf: {bak_conf}")
                self.log(f"Backup hba : {bak_hba}")
                self.log("")

                set_listen_addresses(conf, self.log)
                ensure_pg_hba_rule(hba, cidr, self.log)
                ensure_firewall_rule(port, self.log)
                restart_service(svc, datadir, self.log)

                self.set_status("servidor pronto ✅")
                messagebox.showinfo("OK", "Servidor PostgreSQL pronto para rede ✅\nAgora execute os scripts (1→2→3).")
            except Exception as e:
                self.set_status("erro ❌")
                self.log(f"ERRO: {e}")
                messagebox.showerror("Erro", str(e))
            finally:
                self.set_busy(False)
                self._update_mode_ui()

        threading.Thread(target=worker, daemon=True).start()

    # ---------- script helpers ----------
    def _pick_sql_file(self) -> str:
        path = filedialog.askopenfilename(
            title="Selecione um arquivo .sql",
            filetypes=[("SQL", "*.sql"), ("Todos", "*.*")],
        )
        return path or ""

    def _apply_auto_db_from_1(self):
        p_banco = self.sql_banco_var.get().strip()
        if p_banco and os.path.exists(p_banco):
            db = extrair_nome_banco_do_sql(p_banco)
            if db:
                self.dbname_var.set(db)
                self.log(f"Auto-detect DB pelo SQL: {db}")

            enc = extrair_encoding_do_sql(p_banco)
            if enc:
                self.log(f"Encoding detectado no SQL: {enc}")

    def _load_default_scripts(self):
        try:
            desktop_scripts = garantir_scripts_na_area_de_trabalho(logger=self.log)
            mapping = self._script_mapping()

            found_any = False
            for fname, var in mapping.items():
                p = os.path.join(desktop_scripts, fname)
                if os.path.exists(p):
                    var.set(p)
                    found_any = True

            if found_any:
                self._apply_auto_db_from_1()
                self.log("Scripts detectados no Desktop e preenchidos automaticamente ✅")
            else:
                self.log("Não encontrei scripts padrão no Desktop/scripts (use 'Buscar pasta dos scripts').")
        except Exception as e:
            self.log(f"Falha ao preparar scripts no Desktop: {e}")

    def pick_sql_banco(self):
        p = self._pick_sql_file()
        if p:
            self.sql_banco_var.set(p)
            self._apply_auto_db_from_1()

    def pick_sql_schema(self):
        p = self._pick_sql_file()
        if p:
            self.sql_schema_var.set(p)

    def pick_sql_tabelas(self):
        p = self._pick_sql_file()
        if p:
            self.sql_tabelas_var.set(p)

    def pick_sql_apagar(self):
        p = self._pick_sql_file()
        if p:
            self.sql_apagar_var.set(p)

    def pick_scripts_folder(self):
        folder = filedialog.askdirectory(title="Selecione a pasta onde estão os scripts .sql")
        if not folder:
            return

        mapping = self._script_mapping()

        found_any = False
        for fname, var in mapping.items():
            p = os.path.join(folder, fname)
            if os.path.exists(p):
                var.set(p)
                found_any = True

        if found_any:
            self._apply_auto_db_from_1()
            messagebox.showinfo("Scripts", "Scripts detectados e preenchidos automaticamente ✅")
        else:
            messagebox.showwarning("Scripts", "Não encontrei os nomes padrão nessa pasta.\nUse os botões 'Buscar'.")

    def _script_mapping(self):
        return {
            "1_CRIAR_BANCO.sql": self.sql_banco_var,
            "2_CRIAR_SCHEMA.sql": self.sql_schema_var,
            "3_CRIAR_TABELAS.sql": self.sql_tabelas_var,
            "APAGAR_TUDO.sql": self.sql_apagar_var,
        }

    def _get_execution_host(self) -> str:
        return "localhost"

    def _get_connection_text(self) -> str:
        port = self.port_var.get().strip() or DEFAULT_PORT
        dbname = self.dbname_var.get().strip() or DB_NAME_DEFAULT
        modo = self.get_modo()
        host = "localhost" if modo == MODO_LOCAL else (self.ip_var.get().strip() or "localhost")
        return f"host={host} port={port} dbname={dbname}"

    # ---------- execute scripts ----------
    def _validate_create_scripts(self):
        f1 = self.sql_banco_var.get().strip()
        f2 = self.sql_schema_var.get().strip()
        f3 = self.sql_tabelas_var.get().strip()

        if not f1 or not os.path.exists(f1):
            messagebox.showerror("Scripts", "Selecione o 1_CRIAR_BANCO.sql")
            return None
        if not f2 or not os.path.exists(f2):
            messagebox.showerror("Scripts", "Selecione o 2_CRIAR_SCHEMA.sql")
            return None
        if not f3 or not os.path.exists(f3):
            messagebox.showerror("Scripts", "Selecione o 3_CRIAR_TABELAS.sql")
            return None
        return f1, f2, f3

    def on_install_postgres_and_create_all(self):
        if not IS_MAC:
            messagebox.showinfo(
                "Instalação automática",
                "Esta automação completa foi preparada para macOS. No Windows, use o pacote unificado com o instalador PostgreSQL e CONFIGURAR_POSTGRES.exe.",
            )
            return

        scripts = self._validate_create_scripts()
        if not scripts:
            return

        pwd = self.pass_var.get()
        if not pwd or len(pwd) < 6:
            messagebox.showerror("Senha do PostgreSQL", "Informe a senha que será usada no usuário postgres (mínimo 6 caracteres).")
            return

        port = self.port_var.get().strip() or DEFAULT_PORT
        user = self.user_var.get().strip() or "postgres"
        dbname = self.dbname_var.get().strip() or DB_NAME_DEFAULT
        modo = self.get_modo()
        texto_modo = "LOCAL (esta máquina)" if modo == MODO_LOCAL else "REDE / SERVIDOR"

        if user.lower() != "postgres":
            messagebox.showwarning(
                "Usuário postgres",
                "A instalação automática do PostgreSQL cria/configura o superusuário postgres. Vou ajustar o usuário para postgres.",
            )
            self.user_var.set("postgres")
            user = "postgres"

        if not messagebox.askyesno(
            "Confirmar instalação do servidor",
            "Vou preparar o servidor automaticamente:\n\n"
            "1. Baixar o PostgreSQL oficial, se ainda não existir.\n"
            "2. Instalar PostgreSQL 18 na porta informada.\n"
            "3. Configurar acesso de rede, se o modo for Servidor/Rede.\n"
            "4. Executar 1_CRIAR_BANCO.sql.\n"
            "5. Executar 2_CRIAR_SCHEMA.sql.\n"
            "6. Executar 3_CRIAR_TABELAS.sql.\n"
            "7. Salvar a conexão do Sistema Guimma.\n\n"
            f"Modo: {texto_modo}\n"
            f"Porta: {port}\n"
            f"Banco: {dbname}\n\n"
            "O macOS pedirá a senha de administrador do computador.\nContinuar?",
        ):
            return

        f1, f2, f3 = scripts

        def worker():
            self.set_busy(True)
            self.set_status("instalando PostgreSQL...")
            try:
                self.log("")
                self.log("=== INSTALAÇÃO AUTOMÁTICA SERVIDOR SISTEMA GUIMMA ===")
                self.log(f"Modo: {texto_modo}")
                self.log(f"Porta PostgreSQL: {port}")
                self.log(f"DB alvo: {dbname}")
                self.log("")

                install_postgres_macos_if_missing(pwd, port, self.log)

                self.set_status("detectando PostgreSQL...")
                self.detect_all(silent=True)
                svc = self.svc_var.get().strip()
                datadir = self.datadir_var.get().strip()
                psql = self.psql_var.get().strip()

                if not psql or psql.startswith("(") or not os.path.exists(psql):
                    psql = find_psql_exe(datadir if datadir and not datadir.startswith("(") else "")
                    if psql:
                        self.psql_var.set(psql)
                if not psql or not os.path.exists(psql):
                    raise RuntimeError("PostgreSQL instalado, mas não consegui localizar o psql.")

                self.log(f"Serviço detectado: {svc}")
                self.log(f"DataDir detectado: {datadir}")
                self.log(f"psql detectado: {psql}")

                if modo == MODO_REDE:
                    cidr = self.net_var.get().strip()
                    if not cidr or cidr.startswith("(") or "/" not in cidr:
                        ip = detectar_ip()
                        cidr = detectar_rede_cidr(ip)
                        self.net_var.set(cidr or "(não detectado)")
                    configure_postgres_network_macos(datadir, cidr, port, self.log)

                self.set_status("executando scripts 1→2→3...")
                self.log("")
                self.log("=== EXECUÇÃO SCRIPTS (1→2→3) ===")
                run_create_database_if_needed(psql, "localhost", port, "postgres", pwd, dbname, f1, self.log)
                self.log("✅ 1_CRIAR_BANCO concluído ou já existia.\n")
                run_psql_file(psql, "localhost", port, "postgres", pwd, dbname, f2, self.log)
                self.log("✅ 2_CRIAR_SCHEMA concluído.\n")
                run_psql_file(psql, "localhost", port, "postgres", pwd, dbname, f3, self.log)
                self.log("✅ 3_CRIAR_TABELAS concluído.\n")

                host_config = "localhost" if modo == MODO_LOCAL else (self.ip_var.get().strip() or detectar_ip())
                save_system_db_config(host_config, port, dbname, "postgres", pwd, "opera", self.log)
                self.set_status("servidor pronto ✅")

                messagebox.showinfo(
                    "Sistema Guimma • Servidor pronto",
                    "PostgreSQL instalado/configurado e banco criado com sucesso.\n\n"
                    f"Host: {host_config}\n"
                    f"Porta: {port}\n"
                    f"Banco: {dbname}\n"
                    "Usuário: postgres\n\n"
                    "O Sistema Guimma já recebeu a configuração local.",
                )
            except Exception as e:
                self.set_status("erro ❌")
                self.log(f"ERRO: {e}")
                messagebox.showerror("Erro na instalação automática", str(e))
            finally:
                self.set_busy(False)
                self._update_mode_ui()

        threading.Thread(target=worker, daemon=True).start()

    def on_run_create_all(self):
        self.detect_all(silent=True)

        psql = self.psql_var.get().strip()
        host = self._get_execution_host()
        port = self.port_var.get().strip() or DEFAULT_PORT
        user = self.user_var.get().strip() or "postgres"
        pwd = self.pass_var.get()
        dbname = self.dbname_var.get().strip() or DB_NAME_DEFAULT
        modo = self.get_modo()

        scripts = self._validate_create_scripts()
        if not scripts:
            return
        f1, f2, f3 = scripts

        texto_modo = "LOCAL (esta máquina)" if modo == MODO_LOCAL else "REDE / SERVIDOR"
        host_final = "localhost" if modo == MODO_LOCAL else (self.ip_var.get().strip() or "localhost")

        if not messagebox.askyesno(
            "Confirmar",
            "Vou executar os scripts em sequência (1→2→3).\n\n"
            f"Modo: {texto_modo}\n"
            f"DB: {dbname}\n"
            f"Usuário: {user}\n"
            f"Host de execução: {host}\n"
            f"Porta: {port}\n\n"
            "Continuar?",
        ):
            return

        def worker():
            self.set_busy(True)
            self.set_status("executando scripts...")
            try:
                self.log("")
                self.log("=== EXECUÇÃO SCRIPTS (1→2→3) ===")
                self.log(f"Modo: {texto_modo}")
                self.log(f"psql: {psql}")
                self.log(f"user: {user} host_execucao: {host} port: {port}")
                self.log(f"DB alvo: {dbname}")
                self.log("")

                run_create_database_if_needed(psql, host, port, user, pwd, dbname, f1, self.log)
                self.log("✅ 1_CRIAR_BANCO concluído ou já existia.\n")

                run_psql_file(psql, host, port, user, pwd, dbname, f2, self.log)
                self.log("✅ 2_CRIAR_SCHEMA concluído.\n")

                run_psql_file(psql, host, port, user, pwd, dbname, f3, self.log)
                self.log("✅ 3_CRIAR_TABELAS concluído.\n")

                save_system_db_config(host_final, port, dbname, user, pwd, "opera", self.log)
                self.set_status("banco pronto ✅")

                if modo == MODO_LOCAL:
                    msg = (
                        "BANCO LOCAL PRONTO PARA O SISTEMA GUIMMA ✅\n\n"
                        f"Host: localhost\n"
                        f"Porta: {port}\n"
                        f"Banco: {dbname}\n"
                        f"Usuário: {user}\n\n"
                        f"host=localhost port={port} dbname={dbname}"
                    )
                else:
                    msg = (
                        "BANCO / SERVIDOR PRONTO PARA O SISTEMA GUIMMA ✅\n\n"
                        f"IP do servidor: {host_final}\n"
                        f"Porta: {port}\n"
                        f"Banco: {dbname}\n"
                        f"Usuário: {user}\n\n"
                        f"host={host_final} port={port} dbname={dbname}"
                    )
                messagebox.showinfo("Sistema Guimma • Pronto", msg)
            except Exception as e:
                self.set_status("erro ❌")
                self.log(f"ERRO: {e}")
                messagebox.showerror("Erro ao executar scripts", str(e))
            finally:
                self.set_busy(False)
                self._update_mode_ui()

        threading.Thread(target=worker, daemon=True).start()

    def on_run_drop_all(self):
        self.detect_all(silent=True)

        psql = self.psql_var.get().strip()
        host = "localhost"
        port = self.port_var.get().strip() or DEFAULT_PORT
        user = self.user_var.get().strip() or "postgres"
        pwd = self.pass_var.get()
        dbname = self.dbname_var.get().strip() or DB_NAME_DEFAULT

        fdrop = self.sql_apagar_var.get().strip()
        if not fdrop or not os.path.exists(fdrop):
            messagebox.showerror("Scripts", "Selecione o APAGAR_TUDO.sql")
            return

        if not messagebox.askyesno("⚠️ CONFIRMAÇÃO", f"Isso vai APAGAR o banco '{dbname}'.\n\nTem certeza?"):
            return
        if not messagebox.askyesno("⚠️ CONFIRMAÇÃO FINAL", "Última confirmação: deseja realmente APAGAR TUDO?"):
            return

        def worker():
            self.set_busy(True)
            self.set_status("apagando banco...")
            try:
                self.log("")
                self.log("=== APAGAR TUDO ===")
                run_psql_file(psql, host, port, user, pwd, "postgres", fdrop, self.log)
                self.set_status("apagado ✅")
                messagebox.showinfo("OK", f"Banco {dbname} removido ✅")
            except Exception as e:
                self.set_status("erro ❌")
                self.log(f"ERRO: {e}")
                messagebox.showerror("Erro", str(e))
            finally:
                self.set_busy(False)
                self._update_mode_ui()

        threading.Thread(target=worker, daemon=True).start()

    def on_copy(self):
        text = self._get_connection_text()
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copiado", f"Copiado:\n\n{text}")


if __name__ == "__main__":
    app = ConfigurarPostgresApp()
    app.mainloop()
