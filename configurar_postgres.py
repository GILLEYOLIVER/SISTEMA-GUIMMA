import os
import re
import sys
import time
import queue
import shutil
import ctypes
import ipaddress
import threading
import subprocess
from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox, filedialog

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = (not IS_WINDOWS) and (not IS_MAC)

if IS_WINDOWS:
    import winreg
else:
    winreg = None


APP_TITLE = "OPERA • Configurador PostgreSQL (Servidor)"
DEFAULT_PORT = "5432"
TAG_HBA = "# --- OPERA: acesso rede (adicionado automaticamente) ---"

DB_NAME_DEFAULT = "BANCO_OPERA"


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
    - Windows: UAC
    - macOS/Linux: não força relaunch automático para evitar problemas com app GUI
    """
    if not IS_WINDOWS:
        return

    try:
        params = " ".join([f'"{a}"' for a in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    except Exception:
        pass


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


def run_shell(command: str, timeout: int = 60, env=None) -> tuple[int, str, str]:
    p = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env=env, shell=True)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_file(path: str) -> str:
    bak = f"{path}.bak_{now_stamp()}"
    shutil.copy2(path, bak)
    return bak


def which_or_empty(cmd_name: str) -> str:
    return shutil.which(cmd_name) or ""


# ------------------ scripts -> Desktop (blindado) ------------------

def garantir_scripts_na_area_de_trabalho(logger=None) -> str:
    """
    Copia a pasta scripts para ~/Desktop/scripts.
    Funciona em:
      - DEV (rodando .py)
      - PyInstaller --onedir (scripts ao lado do exe)
      - PyInstaller --onefile (scripts extraídos em sys._MEIPASS)
    Retorna o caminho final ~/Desktop/scripts.
    """
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

    src_candidates = [
        os.path.join(base_exe, "scripts"),
        os.path.join(getattr(sys, "_MEIPASS", ""), "scripts"),
        os.path.join(os.getcwd(), "scripts"),
    ]

    src = ""
    for c in src_candidates:
        if os.path.isdir(c):
            src = c
            break

    if not src:
        if logger:
            logger("Não achei a pasta 'scripts' (exe/_MEIPASS/cwd). Sem origem para copiar.")
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


# ------------------ SQL parsing (auto DB name) ------------------

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
        flags=re.IGNORECASE
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
            timeout=15
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
        if os.path.isdir(p) and (os.path.exists(conf) or os.path.exists(hba)):
            return "postgresql-18", p

    for brew_name in ("postgresql@18", "postgresql"):
        rc, out, _ = run_cmd(["brew", "services", "list"], timeout=20)
        if rc == 0 and brew_name in out:
            # tenta achar o data dir padrão do brew
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
    p = os.path.normpath(datadir)
    return os.path.dirname(p)


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

    # fallback simples e seguro para macOS/Linux
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
        lines.append("# --- OPERA: habilita conexao local e via rede ---")
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

    rule_name = f"PostgreSQL 18 (OPERA) - TCP {port}"
    try:
        out = run_powershell(
            f"Get-NetFirewallRule -DisplayName '{rule_name}' -ErrorAction SilentlyContinue | "
            "Select-Object -First 1 -ExpandProperty DisplayName",
            timeout=15
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
        timeout=20
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
        # tenta Homebrew primeiro
        for svc in ("postgresql@18", "postgresql"):
            rc, out, err = run_cmd(["brew", "services", "restart", svc], timeout=60)
            if rc == 0:
                logger(f"Serviço reiniciado via brew: {svc}")
                if out.strip():
                    logger(out.strip())
                return

        # fallback com pg_ctl
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

    # Linux fallback
    for cmd in (
        ["systemctl", "restart", "postgresql"],
        ["service", "postgresql", "restart"],
    ):
        rc, out, err = run_cmd(cmd, timeout=60)
        if rc == 0:
            logger(f"Serviço reiniciado: {' '.join(cmd)}")
            return

    logger("Não consegui reiniciar automaticamente no Linux. Reinicie o PostgreSQL manualmente.")


# ------------------ SQL execution via psql ------------------

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
        "-f", sql_file
    ]

    logger(f"Executando: {os.path.basename(sql_file)} (db={dbname}) ...")
    rc, out, err = run_cmd(cmd, timeout=300, env=env)

    if out.strip():
        logger(out.strip())
    if err.strip():
        logger(err.strip())

    if rc != 0:
        raise RuntimeError(f"Falha ao executar {os.path.basename(sql_file)} (rc={rc}). Veja o log.")


# ------------------ UI helpers ------------------

def centralizar_janela(win: ctk.CTk, width: int, height: int):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = int((sw / 2) - (width / 2))
    y = int((sh / 2) - (height / 2))
    win.geometry(f"{width}x{height}+{x}+{y}")


# ------------------ App ------------------

class ConfigurarPostgresApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)

        self.win_width = 1400
        self.win_height = 1000
        centralizar_janela(self, self.win_width, self.win_height)
        self.resizable(True, True)

        self.log_q = queue.Queue()

        self.ip_var = ctk.StringVar(value=detectar_ip())
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

        try:
            desktop_scripts = garantir_scripts_na_area_de_trabalho(logger=self.log)

            mapping = {
                "1_CRIAR_BANCO.sql": self.sql_banco_var,
                "2_CRIAR_SCHEMA.sql": self.sql_schema_var,
                "3_CRIAR_TABELAS.sql": self.sql_tabelas_var,
                "APAGAR_TUDO.sql": self.sql_apagar_var,
            }

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
            text="Configuração do PostgreSQL (Servidor)",
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            title_row,
            text="Rede + Banco/Tabelas",
            font=ctk.CTkFont(size=13)
        ).grid(row=0, column=1, sticky="e")

        hint = ctk.CTkLabel(
            header,
            text="Fluxo: 1) Detectar  •  2) Configurar Rede  •  3) Scripts  •  4) Executar (1→2→3)",
            font=ctk.CTkFont(size=12)
        )
        hint.pack(anchor="w", padx=14, pady=(0, 12))

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

        # LEFT
        ctk.CTkLabel(left, text="Detecção / Rede", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=14, pady=(14, 10)
        )

        det = ctk.CTkFrame(left, corner_radius=12)
        det.pack(fill="x", padx=14, pady=(0, 14))
        det.grid_columnconfigure(0, weight=1)
        det.grid_columnconfigure(1, weight=1)

        self._row_entry(det, 0, 0, "IP do servidor:", self.ip_var)
        self._row_entry(det, 0, 1, "Porta:", self.port_var)
        self._row_entry(det, 2, 0, "Rede (CIDR):", self.net_var)
        self._row_entry(det, 2, 1, "Serviço:", self.svc_var)
        self._row_entry(det, 4, 0, "DataDir (-D):", self.datadir_var)
        self._row_entry(det, 4, 1, "psql:", self.psql_var)

        btns = ctk.CTkFrame(left, fg_color="transparent")
        btns.pack(fill="x", padx=14, pady=(0, 14))
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)

        self.btn_detect = ctk.CTkButton(btns, text="Detectar tudo", height=44, command=self.on_detect)
        self.btn_detect.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.btn_config = ctk.CTkButton(btns, text="Configurar Rede (REAL)", height=44, command=self.on_configure_real)
        self.btn_config.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        quick = ctk.CTkFrame(left, fg_color="transparent")
        quick.pack(fill="x", padx=14, pady=(0, 14))
        quick.grid_columnconfigure(0, weight=1)
        quick.grid_columnconfigure(1, weight=1)

        self.btn_copy = ctk.CTkButton(
            quick, text="Copiar host/porta/db", height=44,
            fg_color="transparent", border_width=2,
            command=self.on_copy
        )
        self.btn_copy.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.btn_drop = ctk.CTkButton(
            quick,
            text="APAGAR TUDO (PERIGOSO)",
            height=44,
            fg_color="#8B0000",
            command=self.on_run_drop_all
        )
        self.btn_drop.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # RIGHT
        ctk.CTkLabel(right, text="Scripts SQL (deixar pronto para o OPERA)", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=14, pady=(14, 10)
        )

        scripts = ctk.CTkFrame(right, corner_radius=12)
        scripts.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        scripts.grid_columnconfigure(0, weight=1)
        scripts.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            scripts, text="DB alvo (auto pelo 1_CRIAR_BANCO.sql):",
            font=ctk.CTkFont(size=12, weight="bold")
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
            text="EXECUTAR CRIAÇÃO (1→2→3)",
            height=44,
            fg_color="#1f8b4c",
            hover_color="#176b3a",
            text_color="white",
            command=self.on_run_create_all
        )
        self.btn_run_all.grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def _row_entry(self, parent, row, col, label, var):
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=row, column=col, sticky="w",
            padx=(12, 6) if col == 0 else (6, 12),
            pady=(8 if row == 0 else 4, 2)
        )
        ctk.CTkEntry(parent, textvariable=var, height=34).grid(
            row=row + 1, column=col, sticky="ew",
            padx=(12, 6) if col == 0 else (6, 12),
            pady=(0, 6)
        )

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

    # ---------- Logging ----------
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
        for b in (self.btn_detect, self.btn_config, self.btn_folder, self.btn_run_all, self.btn_copy, self.btn_drop):
            b.configure(state=state)

    # ---------- Detect ----------
    def detect_all(self, silent: bool = False):
        ip = self.ip_var.get().strip() or detectar_ip()
        self.ip_var.set(ip)

        try:
            cidr = detectar_rede_cidr(ip)
        except Exception:
            cidr = ""
        self.net_var.set(cidr if cidr else "(não detectado)")

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
                f"psql: {self.psql_var.get()}"
            )

    def on_detect(self):
        self.detect_all(silent=False)

    # ---------- Configure REAL ----------
    def on_configure_real(self):
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
            "Continuar?"
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

        threading.Thread(target=worker, daemon=True).start()

    # ---------- Script pickers ----------
    def _pick_sql_file(self) -> str:
        path = filedialog.askopenfilename(
            title="Selecione um arquivo .sql",
            filetypes=[("SQL", "*.sql"), ("Todos", "*.*")]
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

        mapping = {
            "1_CRIAR_BANCO.sql": self.sql_banco_var,
            "2_CRIAR_SCHEMA.sql": self.sql_schema_var,
            "3_CRIAR_TABELAS.sql": self.sql_tabelas_var,
            "APAGAR_TUDO.sql": self.sql_apagar_var,
        }

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

    # ---------- Execute scripts ----------
    def on_run_create_all(self):
        self.detect_all(silent=True)

        psql = self.psql_var.get().strip()
        host = "localhost"
        port = self.port_var.get().strip() or DEFAULT_PORT
        user = self.user_var.get().strip() or "postgres"
        pwd = self.pass_var.get()
        dbname = self.dbname_var.get().strip() or DB_NAME_DEFAULT

        f1 = self.sql_banco_var.get().strip()
        f2 = self.sql_schema_var.get().strip()
        f3 = self.sql_tabelas_var.get().strip()

        if not f1 or not os.path.exists(f1):
            messagebox.showerror("Scripts", "Selecione o 1_CRIAR_BANCO.sql")
            return
        if not f2 or not os.path.exists(f2):
            messagebox.showerror("Scripts", "Selecione o 2_CRIAR_SCHEMA.sql")
            return
        if not f3 or not os.path.exists(f3):
            messagebox.showerror("Scripts", "Selecione o 3_CRIAR_TABELAS.sql")
            return

        if not messagebox.askyesno(
            "Confirmar",
            "Vou executar os scripts em sequência (1→2→3).\n\n"
            f"DB: {dbname}\n"
            f"Usuário: {user}\n"
            f"Host: {host}\n"
            f"Porta: {port}\n\n"
            "Continuar?"
        ):
            return

        def worker():
            self.set_busy(True)
            self.set_status("executando scripts...")
            try:
                self.log("")
                self.log("=== EXECUÇÃO SCRIPTS (1→2→3) ===")
                self.log(f"psql: {psql}")
                self.log(f"user: {user} host: {host} port: {port}")
                self.log(f"DB alvo: {dbname}")
                self.log("")

                run_psql_file(psql, host, port, user, pwd, "postgres", f1, self.log)
                self.log("✅ 1_CRIAR_BANCO concluído.\n")

                run_psql_file(psql, host, port, user, pwd, dbname, f2, self.log)
                self.log("✅ 2_CRIAR_SCHEMA concluído.\n")

                run_psql_file(psql, host, port, user, pwd, dbname, f3, self.log)
                self.log("✅ 3_CRIAR_TABELAS concluído.\n")

                self.set_status("banco pronto ✅")

                ip_servidor = self.ip_var.get().strip()
                msg = (
                    "BANCO PRONTO PARA O OPERA ✅\n\n"
                    f"IP do servidor: {ip_servidor}\n"
                    f"Porta: {port}\n"
                    f"Banco: {dbname}\n"
                    f"Usuário: {user}\n\n"
                    f"host={ip_servidor} port={port} dbname={dbname}"
                )
                messagebox.showinfo("OPERA • Pronto", msg)

            except Exception as e:
                self.set_status("erro ❌")
                self.log(f"ERRO: {e}")
                messagebox.showerror("Erro ao executar scripts", str(e))
            finally:
                self.set_busy(False)

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

        threading.Thread(target=worker, daemon=True).start()

    def on_copy(self):
        ip = self.ip_var.get().strip()
        port = self.port_var.get().strip() or DEFAULT_PORT
        dbname = self.dbname_var.get().strip() or DB_NAME_DEFAULT
        text = f"host={ip} port={port} dbname={dbname}"
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copiado", f"Copiado:\n\n{text}")


# ------------------ ENTRYPOINT ------------------

if __name__ == "__main__":
    if IS_WINDOWS and not is_admin():
        relaunch_as_admin_silent()
        sys.exit(0)

    app = ConfigurarPostgresApp()
    app.mainloop()