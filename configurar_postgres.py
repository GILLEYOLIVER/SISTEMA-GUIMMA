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
from tkinter import messagebox

import winreg


APP_TITLE = "OPERA • Configurador PostgreSQL (Servidor)"
DEFAULT_PORT = "5432"
TAG_HBA = "# --- OPERA: acesso rede (adicionado automaticamente) ---"


# --- FIX encoding (Windows) ---
# Ajuda em ambientes PT-BR onde outputs/arquivos estão em cp1252 (ex: byte 0xE3 = ã).
if sys.platform.startswith("win"):
    os.environ.setdefault("PGCLIENTENCODING", "WIN1252")
    os.environ.setdefault("PGOPTIONS", "-c client_encoding=WIN1252")


# ------------------ Helpers: Admin / subprocess / logging ------------------

def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    """
    Relança o mesmo script elevando privilégios (UAC).
    """
    try:
        params = " ".join([f'"{a}"' for a in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    except Exception as e:
        messagebox.showerror("Permissão", f"Não consegui solicitar Admin (UAC): {e}")


def run_powershell(ps_command: str, timeout: int = 30) -> str:
    """
    Executa comando PowerShell e retorna stdout (str).
    """
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
        capture_output=True, text=True, timeout=timeout
    )
    if completed.returncode != 0:
        err = (completed.stderr or "").strip()
        out = (completed.stdout or "").strip()
        raise RuntimeError(f"PowerShell falhou.\nCMD: {ps_command}\nSTDOUT: {out}\nSTDERR: {err}")
    return (completed.stdout or "").strip()


def run_cmd(cmd_list, timeout: int = 30, env=None) -> tuple[int, str, str]:
    """
    Executa comando e retorna (returncode, stdout, stderr).
    """
    p = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_file(path: str) -> str:
    stamp = now_stamp()
    bak = f"{path}.bak_{stamp}"
    shutil.copy2(path, bak)
    return bak


# ------------------ Encoding-safe read/write ------------------

def read_text_smart(path: str) -> tuple[list[str], str]:
    """
    Lê arquivo tentando UTF-8 e fazendo fallback para cp1252/latin-1.
    Retorna (linhas, encoding_usado).
    """
    with open(path, "rb") as f:
        raw = f.read()

    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            txt = raw.decode(enc)
            return txt.splitlines(), enc
        except UnicodeDecodeError:
            continue

    # último recurso: substitui caracteres inválidos
    txt = raw.decode("utf-8", errors="replace")
    return txt.splitlines(), "utf-8"


def write_text_smart(path: str, lines: list[str], encoding: str):
    """
    Escreve preservando a codificação detectada.
    """
    data = "\n".join(lines) + "\n"
    with open(path, "w", encoding=encoding, errors="replace", newline="\n") as f:
        f.write(data)


# ------------------ PostgreSQL detection (service + datadir) ------------------

def _get_service_imagepath(service_name: str) -> str:
    key_path = rf"SYSTEM\CurrentControlSet\Services\{service_name}"
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
        image_path, _ = winreg.QueryValueEx(k, "ImagePath")
    return image_path


def _extract_datadir_from_imagepath(image_path: str) -> str:
    # Ex: ... pg_ctl.exe runservice -N "postgresql-x64-18" -D "C:\Program Files\PostgreSQL\18\data"
    m = re.search(r'-D\s+"([^"]+)"', image_path)
    if m:
        return m.group(1)

    m2 = re.search(r"-D\s+([^\s]+)", image_path)
    if m2:
        return m2.group(1)

    return ""


def detectar_postgres_service_and_datadir() -> tuple[str, str]:
    """
    Retorna (service_name, data_dir) do PostgreSQL 18.
    """
    candidates = ["postgresql-x64-18", "postgresql-18"]

    for svc in candidates:
        try:
            img = _get_service_imagepath(svc)
            datadir = _extract_datadir_from_imagepath(img)
            if datadir:
                return svc, datadir
            return svc, ""
        except FileNotFoundError:
            continue

    # fallback: procura serviços contendo postgres e 18
    try:
        out = run_powershell(
            r"Get-Service | Where-Object { $_.Name -match 'postgres' -and $_.Name -match '18' } | "
            r"Select-Object -First 1 -ExpandProperty Name"
        )
        if out:
            img = _get_service_imagepath(out.strip())
            datadir = _extract_datadir_from_imagepath(img)
            return out.strip(), datadir
    except Exception:
        pass

    return "", ""


def infer_install_root_from_datadir(datadir: str) -> str:
    if not datadir:
        return ""
    p = os.path.normpath(datadir)
    return os.path.dirname(p)  # ...\18\data -> ...\18


def find_psql_exe(datadir: str) -> str:
    root = infer_install_root_from_datadir(datadir)
    if not root:
        return ""
    psql = os.path.join(root, "bin", "psql.exe")
    return psql if os.path.exists(psql) else ""


# ------------------ Network detection ------------------

def detectar_ip() -> str:
    import socket
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return ""
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass


def detectar_rede_cidr_por_powershell(ip_alvo: str) -> str:
    """
    Pega PrefixLength do IP via Get-NetIPAddress e calcula rede CIDR.
    Ex: 192.168.0.108 + prefix 24 => 192.168.0.0/24
    """
    if not ip_alvo:
        return ""

    ps = (
        "Get-NetIPAddress -AddressFamily IPv4 | "
        f"Where-Object {{ $_.IPAddress -eq '{ip_alvo}' }} | "
        "Select-Object -First 1 -ExpandProperty PrefixLength"
    )
    out = run_powershell(ps, timeout=15).strip()
    if not out:
        return ""
    prefix = int(out)
    net = ipaddress.IPv4Network(f"{ip_alvo}/{prefix}", strict=False)
    return f"{net.network_address}/{prefix}"


# ------------------ Config modifications ------------------

def set_listen_addresses(conf_path: str, logger) -> None:
    lines, enc = read_text_smart(conf_path)

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

    write_text_smart(conf_path, lines, enc)
    logger(f"postgresql.conf: {target} OK (encoding: {enc})")


def ensure_pg_hba_rule(hba_path: str, network_cidr: str, logger) -> None:
    if not network_cidr:
        raise RuntimeError("Rede CIDR vazia. Não é possível atualizar pg_hba.conf.")

    lines, enc = read_text_smart(hba_path)

    rule = f"host    all             all             {network_cidr}            scram-sha-256"
    norm_rule = re.sub(r"\s+", " ", rule).strip().lower()

    for l in lines:
        if re.sub(r"\s+", " ", l).strip().lower() == norm_rule:
            logger(f"pg_hba.conf: regra já existe ({network_cidr}) (encoding: {enc})")
            return

    if TAG_HBA not in lines:
        lines.append("")
        lines.append(TAG_HBA)

    lines.append(rule)

    write_text_smart(hba_path, lines, enc)
    logger(f"pg_hba.conf: regra adicionada ({network_cidr}) (encoding: {enc})")


def ensure_firewall_rule(port: str, logger) -> None:
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


def restart_service(service_name: str, logger) -> None:
    run_powershell(f"Restart-Service -Name '{service_name}' -Force", timeout=60)
    time.sleep(2)
    status = run_powershell(f"(Get-Service -Name '{service_name}').Status", timeout=10).strip()
    logger(f"Serviço {service_name}: {status}")


def test_psql_connection(psql_exe: str, host: str, port: str, user: str, password: str, dbname: str, logger) -> bool:
    if not psql_exe or not os.path.exists(psql_exe):
        raise RuntimeError("psql.exe não encontrado (não consegui testar).")

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    # reforça encoding no subprocess
    env["PGCLIENTENCODING"] = "WIN1252"
    env["PGOPTIONS"] = "-c client_encoding=WIN1252"

    cmd = [psql_exe, "-h", host, "-p", port, "-U", user, "-d", dbname, "-c", "SELECT 1;"]
    rc, out, err = run_cmd(cmd, timeout=25, env=env)

    if rc == 0:
        logger("Teste psql: OK (SELECT 1)")
        return True

    logger("Teste psql: FALHOU")
    if out.strip():
        logger("STDOUT:\n" + out.strip())
    if err.strip():
        logger("STDERR:\n" + err.strip())
    return False


# ------------------ UI helpers ------------------

def centralizar_janela(win: ctk.CTk, width: int, height: int):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = int((sw / 2) - (width / 2))
    y = int((sh / 2) - (height / 2))
    win.geometry(f"{width}x{height}+{x}+{y}")


# ------------------ UI App ------------------

class ConfigurarPostgresApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ✅ SEM MENSAGEM: se não for Admin, só pede UAC e relança
        # (quando abrir elevado, segue normalmente)
        if not is_admin():
            relaunch_as_admin()
            self.after(50, self.destroy)
            return

        # Aparência
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Janela
        self.title(APP_TITLE)
        self.win_width = 1100
        self.win_height = 800
        centralizar_janela(self, self.win_width, self.win_height)
        self.resizable(False, False)

        # Queue do log (thread-safe)
        self.log_q = queue.Queue()

        # ✅ TUDO VAZIO AO ABRIR (nada gravado / nada pré-preenchido)
        self.ip_var = ctk.StringVar(value="")
        self.port_var = ctk.StringVar(value="")
        self.net_var = ctk.StringVar(value="")
        self.svc_var = ctk.StringVar(value="")
        self.datadir_var = ctk.StringVar(value="")
        self.psql_var = ctk.StringVar(value="")

        self.user_var = ctk.StringVar(value="")
        self.pass_var = ctk.StringVar(value="")
        self.db_var = ctk.StringVar(value="")

        # UI
        self._build_ui()
        self._pump_logs()

        # ❌ NÃO detecta nada automaticamente ao abrir
        # (o usuário clica em "Detectar tudo")
        # self.detect_all()

    def _build_ui(self):
        wrapper = ctk.CTkFrame(self, corner_radius=14)
        wrapper.pack(fill="both", expand=True, padx=16, pady=16)

        top = ctk.CTkFrame(wrapper, corner_radius=14)
        top.pack(fill="x", padx=14, pady=(14, 10))

        ctk.CTkLabel(
            top, text="Configurador do PostgreSQL (Servidor)",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w", padx=14, pady=(12, 0))

        ctk.CTkLabel(
            top,
            text="Detectar • Configurar REAL • Testar • Mostrar dados para clientes",
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=14, pady=(4, 12))

        main = ctk.CTkFrame(wrapper, corner_radius=14)
        main.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(main, corner_radius=14)
        left.grid(row=0, column=0, sticky="nsew", padx=(14, 7), pady=14)

        right = ctk.CTkFrame(main, corner_radius=14)
        right.grid(row=0, column=1, sticky="nsew", padx=(7, 14), pady=14)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # LEFT
        ctk.CTkLabel(left, text="Detecção", font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", padx=14, pady=(12, 6)
        )

        form = ctk.CTkFrame(left, fg_color="transparent")
        form.pack(fill="x", padx=14, pady=(0, 6))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="IP do servidor:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 4)
        )
        ctk.CTkEntry(form, textvariable=self.ip_var, height=34).grid(
            row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 10)
        )

        ctk.CTkLabel(form, text="Porta:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 4)
        )
        ctk.CTkEntry(form, textvariable=self.port_var, height=34).grid(
            row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 10)
        )

        ctk.CTkLabel(form, text="Rede liberada (CIDR):", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=(0, 4)
        )
        ctk.CTkEntry(form, textvariable=self.net_var, height=34).grid(
            row=3, column=0, sticky="ew", padx=(0, 10), pady=(0, 10)
        )

        ctk.CTkLabel(form, text="Serviço Postgres:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=2, column=1, sticky="w", padx=(10, 0), pady=(0, 4)
        )
        ctk.CTkEntry(form, textvariable=self.svc_var, height=34).grid(
            row=3, column=1, sticky="ew", padx=(10, 0), pady=(0, 10)
        )

        ctk.CTkLabel(form, text="Data Directory (-D):", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=4, column=0, sticky="w", padx=(0, 10), pady=(0, 4)
        )
        ctk.CTkEntry(form, textvariable=self.datadir_var, height=34).grid(
            row=5, column=0, sticky="ew", padx=(0, 10), pady=(0, 10)
        )

        ctk.CTkLabel(form, text="psql.exe:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=4, column=1, sticky="w", padx=(10, 0), pady=(0, 4)
        )
        ctk.CTkEntry(form, textvariable=self.psql_var, height=34).grid(
            row=5, column=1, sticky="ew", padx=(10, 0), pady=(0, 10)
        )

        # Credenciais teste (vazias)
        ctk.CTkLabel(left, text="Teste de conexão (psql)", font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", padx=14, pady=(8, 6)
        )

        form2 = ctk.CTkFrame(left, fg_color="transparent")
        form2.pack(fill="x", padx=14, pady=(0, 10))
        form2.grid_columnconfigure(0, weight=1)
        form2.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form2, text="Usuário:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 4)
        )
        ctk.CTkEntry(form2, textvariable=self.user_var, height=34).grid(
            row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 10)
        )

        ctk.CTkLabel(form2, text="Banco:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 4)
        )
        ctk.CTkEntry(form2, textvariable=self.db_var, height=34).grid(
            row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 10)
        )

        ctk.CTkLabel(form2, text="Senha (não é salva):", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=(0, 4)
        )
        ctk.CTkEntry(form2, textvariable=self.pass_var, show="*", height=34).grid(
            row=3, column=0, sticky="ew", padx=(0, 10), pady=(0, 10)
        )

        # Botões
        btns = ctk.CTkFrame(left, fg_color="transparent")
        btns.pack(fill="x", padx=14, pady=(0, 14))
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)

        self.btn_detect = ctk.CTkButton(btns, text="Detectar tudo", height=44, command=self.on_detect)
        self.btn_detect.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.btn_config = ctk.CTkButton(btns, text="CONFIGURAR AGORA (REAL)", height=44, command=self.on_configure_real)
        self.btn_config.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        btns2 = ctk.CTkFrame(left, fg_color="transparent")
        btns2.pack(fill="x", padx=14, pady=(0, 14))
        btns2.grid_columnconfigure(0, weight=1)
        btns2.grid_columnconfigure(1, weight=1)

        self.btn_test = ctk.CTkButton(btns2, text="Testar conexão (psql)", height=44, command=self.on_test)
        self.btn_test.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.btn_copy = ctk.CTkButton(btns2, text="Copiar host/porta", height=44, fg_color="transparent", border_width=2,
                                      command=self.on_copy)
        self.btn_copy.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # RIGHT: Logs
        ctk.CTkLabel(right, text="Log (tempo real)", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 6)
        )

        self.logbox = ctk.CTkTextbox(right, corner_radius=10)
        self.logbox.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        self.logbox.configure(state="disabled")

        self.status_lbl = ctk.CTkLabel(right, text="Status: pronto", font=ctk.CTkFont(size=12))
        self.status_lbl.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 12))

    # ---------------- logging ----------------
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
        for b in (self.btn_detect, self.btn_config, self.btn_test, self.btn_copy):
            b.configure(state=state)

    # ---------------- detection ----------------
    def detect_all(self):
        ip = detectar_ip()
        self.ip_var.set(ip)

        cidr = ""
        try:
            cidr = detectar_rede_cidr_por_powershell(ip)
        except Exception:
            cidr = ""
        self.net_var.set(cidr)

        svc, datadir = ("", "")
        try:
            svc, datadir = detectar_postgres_service_and_datadir()
        except Exception as e:
            raise RuntimeError(f"Falha ao detectar Postgres: {e}")

        self.svc_var.set(svc)
        self.datadir_var.set(datadir)

        psql = find_psql_exe(datadir) if datadir else ""
        self.psql_var.set(psql)

    def on_detect(self):
        try:
            self.detect_all()
            messagebox.showinfo(
                "Detecção",
                f"IP: {self.ip_var.get()}\n"
                f"Rede: {self.net_var.get()}\n"
                f"Serviço: {self.svc_var.get()}\n"
                f"DataDir: {self.datadir_var.get()}\n"
                f"psql: {self.psql_var.get()}"
            )
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ---------------- real configure ----------------
    def on_configure_real(self):
        if not is_admin():
            messagebox.showerror("Permissão", "Rode como Administrador para configurar de verdade.")
            return

        try:
            self.detect_all()
        except Exception as e:
            messagebox.showerror("Erro", f"Detecção falhou:\n{e}")
            return

        svc = self.svc_var.get().strip()
        datadir = self.datadir_var.get().strip()
        cidr = self.net_var.get().strip()
        port = (self.port_var.get().strip() or DEFAULT_PORT)
        self.port_var.set(port)

        if not svc:
            messagebox.showerror("Erro", "Não detectei o serviço do PostgreSQL 18.")
            return
        if not datadir or not os.path.isdir(datadir):
            messagebox.showerror("Erro", "Data Directory (-D) inválido.")
            return
        if not cidr or "/" not in cidr:
            messagebox.showerror("Erro", "Não consegui detectar a rede CIDR.")
            return

        conf = os.path.join(datadir, "postgresql.conf")
        hba = os.path.join(datadir, "pg_hba.conf")
        if not os.path.exists(conf) or not os.path.exists(hba):
            messagebox.showerror("Erro", f"Não encontrei:\n{conf}\n{hba}")
            return

        if not messagebox.askyesno(
            "Confirmar",
            "Vou configurar o PostgreSQL para aceitar conexões na rede:\n"
            f"- Serviço: {svc}\n"
            f"- Rede: {cidr}\n"
            f"- Porta: {port}\n\n"
            "Isso vai editar postgresql.conf e pg_hba.conf, abrir firewall e reiniciar o serviço.\n\n"
            "Continuar?"
        ):
            return

        def worker():
            self.set_busy(True)
            self.set_status("configurando...")
            try:
                self.log("=== INÍCIO CONFIGURAÇÃO REAL ===")
                self.log(f"Serviço: {svc}")
                self.log(f"DataDir: {datadir}")
                self.log(f"Rede CIDR: {cidr}")
                self.log(f"Porta: {port}")
                self.log("")

                self.log("Criando backups...")
                bak_conf = backup_file(conf)
                bak_hba = backup_file(hba)
                self.log(f"Backup conf: {bak_conf}")
                self.log(f"Backup hba : {bak_hba}")
                self.log("")

                self.log("Ajustando postgresql.conf...")
                set_listen_addresses(conf, self.log)
                self.log("")

                self.log("Ajustando pg_hba.conf...")
                ensure_pg_hba_rule(hba, cidr, self.log)
                self.log("")

                self.log("Firewall...")
                ensure_firewall_rule(port, self.log)
                self.log("")

                self.log("Reiniciando serviço...")
                restart_service(svc, self.log)
                self.log("")

                self.log("✅ Configuração REAL concluída.")
                self.set_status("configurado ✅")

                ip = self.ip_var.get().strip()
                msg = (
                    "PostgreSQL configurado como SERVIDOR ✅\n\n"
                    f"IP do servidor: {ip}\n"
                    f"Porta: {port}\n"
                    f"Rede liberada: {cidr}\n\n"
                    "Nos clientes, use:\n"
                    f"host={ip} port={port}\n"
                )
                messagebox.showinfo("OPERA • Servidor pronto", msg)

            except Exception as e:
                self.log("")
                self.log("❌ ERRO na configuração REAL")
                self.log(str(e))
                self.set_status("erro ❌")
                messagebox.showerror("Erro", f"Falha ao configurar:\n\n{e}")
            finally:
                self.set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    # ---------------- test connection ----------------
    def on_test(self):
        try:
            self.detect_all()
        except Exception as e:
            messagebox.showerror("Erro", f"Detecção falhou:\n{e}")
            return

        psql = self.psql_var.get().strip()
        host = self.ip_var.get().strip()
        port = (self.port_var.get().strip() or DEFAULT_PORT)
        self.port_var.set(port)

        user = self.user_var.get().strip()
        pwd = self.pass_var.get()
        dbn = self.db_var.get().strip()

        if not psql or not os.path.exists(psql):
            messagebox.showerror("Erro", "psql.exe não detectado.")
            return
        if not host:
            messagebox.showerror("Erro", "IP do servidor não detectado.")
            return
        if not port:
            messagebox.showerror("Erro", "Porta vazia.")
            return
        if not user or not dbn:
            messagebox.showerror("Erro", "Informe usuário e banco para testar.")
            return

        def worker():
            self.set_busy(True)
            self.set_status("testando conexão...")
            try:
                self.log("=== TESTE psql ===")
                self.log(f"psql: {psql}")
                self.log(f"host: {host} port: {port} user: {user} db: {dbn}")
                ok = test_psql_connection(psql, host, port, user, pwd, dbn, self.log)
                self.set_status("teste OK ✅" if ok else "teste falhou ❌")
                if ok:
                    messagebox.showinfo("Teste", "Conexão OK ✅\n\nSELECT 1 executado com sucesso.")
                else:
                    messagebox.showerror("Teste", "Falha na conexão ❌\n\nVeja o log para detalhes.")
            except Exception as e:
                self.log(str(e))
                self.set_status("teste erro ❌")
                messagebox.showerror("Erro", f"Falha no teste:\n\n{e}")
            finally:
                self.set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    # ---------------- copy ----------------
    def on_copy(self):
        ip = self.ip_var.get().strip()
        port = (self.port_var.get().strip() or DEFAULT_PORT)
        if not ip:
            messagebox.showerror("Erro", "IP vazio. Clique em 'Detectar tudo' primeiro.")
            return
        text = f"host={ip} port={port}"
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copiado", f"Copiado:\n\n{text}")


if __name__ == "__main__":
    app = ConfigurarPostgresApp()
    app.mainloop()
