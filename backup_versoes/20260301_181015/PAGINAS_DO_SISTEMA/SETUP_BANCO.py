# -*- coding: utf-8 -*-
"""
SETUP_BANCO.py — Configurador de Banco (Sistema Opera)

Funcionalidades:
- Janela 1200x700 centralizada
- Primeira vez: campos vazios (só preenche se config validado existir)
- Persistência real: salva validated_ok=True somente após Teste OK
- Mensagens muito claras no centro do app
- Detectar porta (5432–5435)
- Detectar servidores PostgreSQL na rede (scan /24) PARALLEL + CANCEL + PROGRESSO
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

# --- Encoding env (Windows) ---
# Ajuda em ambientes Postgres cluster WIN1252 etc.
if sys.platform.startswith("win"):
    os.environ.setdefault("PGCLIENTENCODING", "WIN1252")
    os.environ.setdefault("PGOPTIONS", "-c client_encoding=WIN1252")

try:
    import psycopg2
except Exception:
    psycopg2 = None


# ============================================================
# Paths
# ============================================================
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
PAGINAS_DIR = PROJECT_ROOT / "PAGINAS_DO_SISTEMA"


def _fallback_app_data_dir(app_name: str = "SistemaOpera") -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return base / app_name
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    return Path.home() / ".config" / app_name


try:
    from OPERA_PATHS import get_app_data_dir  # type: ignore
except Exception:
    def get_app_data_dir(app_name: str = "SistemaOpera") -> Path:
        return _fallback_app_data_dir(app_name)


APP_DATA_DIR = get_app_data_dir()
CONFIG_FILE = APP_DATA_DIR / "config.json"
APP_PAGINAS_CONFIG_FILE = APP_DATA_DIR / "PAGINAS_DO_SISTEMA" / "config.json"

DEV_CONFIG_FILE_PAGINAS = PAGINAS_DIR / "config.json"
DEV_CONFIG_FILE_PARENT = PROJECT_ROOT / "config.json"


def _runtime_pagina_config_candidates() -> List[Path]:
    """
    Candidatos extras (ambiente compilado):
    - pasta do executável
    - pasta atual (cwd)
    """
    candidates: List[Path] = []
    try:
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "PAGINAS_DO_SISTEMA" / "config.json")
    except Exception:
        pass
    try:
        cwd = Path.cwd().resolve()
        candidates.append(cwd / "PAGINAS_DO_SISTEMA" / "config.json")
    except Exception:
        pass

    dedup: List[Path] = []
    seen = set()
    for p in candidates:
        k = str(p)
        if k not in seen:
            seen.add(k)
            dedup.append(p)
    return dedup


# ============================================================
# Model
# ============================================================
@dataclass
class DBConfig:
    mode: str = "local"      # local | rede
    host: str = ""
    port: int = 5432
    dbname: str = "BANCO_OPERA"
    user: str = ""
    password: str = ""
    schema: str = "opera"


def _config_candidates() -> List[Path]:
    # ordem de leitura: prioriza AppData oficial
    return [
        CONFIG_FILE,
        APP_PAGINAS_CONFIG_FILE,
        DEV_CONFIG_FILE_PAGINAS,
        DEV_CONFIG_FILE_PARENT,
        *_runtime_pagina_config_candidates(),
    ]


def _read_json_file(path: Path) -> Optional[dict]:
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None


def load_existing_config_validated() -> Optional[DBConfig]:
    """
    Só carrega e preenche se existir um config com validated_ok=True.
    Isso garante:
      - primeira vez = campos vazios
      - configs antigos não validos são ignorados
    """
    for p in _config_candidates():
        data = _read_json_file(p)
        if not data:
            continue

        if not bool(data.get("validated_ok", False)):
            continue

        defaults = data.get("defaults") if isinstance(data.get("defaults"), dict) else {}
        hosts = data.get("hosts") if isinstance(data.get("hosts"), list) else []
        ports = data.get("ports") if isinstance(data.get("ports"), list) else []

        host = (data.get("host") or (hosts[0] if hosts else "")) or ""
        port = data.get("port") or (ports[0] if ports else 5432)
        user = data.get("user") or (defaults.get("user") if defaults else "") or ""
        password = data.get("password") or (defaults.get("password") if defaults else "") or ""
        dbname = data.get("dbname") or (defaults.get("dbname") if defaults else "BANCO_OPERA") or "BANCO_OPERA"
        schema = data.get("schema") or data.get("pg_schema") or "opera"

        try:
            port = int(port)
        except Exception:
            port = 5432

        mode = str(data.get("mode") or "local")
        if mode not in ("local", "rede"):
            mode = "local"

        return DBConfig(
            mode=mode,
            host=str(host),
            port=int(port),
            dbname=str(dbname),
            user=str(user),
            password=str(password),
            schema=str(schema),
        )

    return None


def save_config(cfg: DBConfig) -> Path:
    """
    Salva config.json e marca validated_ok=True.
    """
    payload_dict = {
        "validated_ok": True,
        "mode": cfg.mode,
        "host": cfg.host,
        "port": int(cfg.port),
        "dbname": cfg.dbname,
        "user": cfg.user,
        "password": cfg.password,
        "schema": cfg.schema,
        "defaults": {"dbname": cfg.dbname, "user": cfg.user, "password": cfg.password},
        "hosts": [cfg.host],
        "ports": [int(cfg.port)],
        "appname": "OPERA_APP",
        "connect_timeout": 8,
    }
    payload = json.dumps(payload_dict, ensure_ascii=False, indent=2)

    targets = [
        CONFIG_FILE,
        APP_PAGINAS_CONFIG_FILE,
        DEV_CONFIG_FILE_PAGINAS,
        DEV_CONFIG_FILE_PARENT,
        *_runtime_pagina_config_candidates(),
    ]

    last_ok = CONFIG_FILE
    for path in targets:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")
            last_ok = path
        except Exception:
            pass

    return last_ok


# ============================================================
# Network helpers
# ============================================================
def get_local_ip() -> str:
    """
    IP local provável (sem depender de internet).
    """
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Força a seleção de interface (não precisa existir)
        s.connect(("192.0.2.1", 1))
        return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return ""
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass


def infer_cidr_24(ip: str) -> str:
    """
    Assume /24 (LAN comum).
    192.168.0.108 -> 192.168.0.0/24
    """
    if not ip or "." not in ip:
        return ""
    parts = ip.split(".")
    if len(parts) != 4:
        return ""
    return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"


def iter_ips_from_cidr24(cidr: str):
    base = cidr.split("/")[0].strip()
    parts = base.split(".")
    if len(parts) != 4:
        return
    a, b, c, _ = parts
    for host in range(1, 255):
        yield f"{a}.{b}.{c}.{host}"


# ============================================================
# Port / Connection
# ============================================================
def _probe_port(host: str, port: int, timeout: float = 0.14) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def detect_ports(host: str) -> List[int]:
    ports = [5432, 5433, 5434, 5435]
    return [p for p in ports if _probe_port(host, p, timeout=0.25)]


def _humanize_pg_error(raw: str, cfg: DBConfig) -> str:
    s = (raw or "").strip()
    low = s.lower()

    if "password authentication failed" in low or "authentication failed" in low:
        return (
            "❌ SENHA OU USUÁRIO INCORRETO.\n\n"
            "O servidor recusou o login.\n"
            "• Confirme o USUÁRIO\n"
            "• Confirme a SENHA\n"
            "• Teste novamente."
        )

    if "no pg_hba.conf entry" in low:
        return (
            "❌ ACESSO BLOQUEADO (pg_hba.conf).\n\n"
            "O servidor não liberou este computador na rede.\n"
            "• No SERVIDOR: libere a rede (CIDR) no pg_hba.conf\n"
            "• Reinicie o serviço do PostgreSQL\n"
            "Depois teste novamente."
        )

    if "does not exist" in low and "database" in low:
        return (
            f"❌ BANCO '{cfg.dbname}' NÃO EXISTE.\n\n"
            "No servidor, crie o banco/schema/tabelas (scripts 1→2→3).\n"
            "Depois teste novamente."
        )

    if "does not exist" in low and "schema" in low:
        return (
            f"❌ SCHEMA '{cfg.schema}' NÃO EXISTE.\n\n"
            "No servidor, crie schema/tabelas (scripts 1→2→3).\n"
            "Depois teste novamente."
        )

    if "could not translate host name" in low or "name or service not known" in low:
        return (
            "❌ HOST/IP INVÁLIDO.\n\n"
            "• Em REDE use IP (ex: 192.168.0.110)\n"
            "• Em LOCAL use localhost\n"
            "Depois teste novamente."
        )

    if "connection refused" in low:
        return (
            "❌ CONEXÃO RECUSADA.\n\n"
            "Possíveis causas:\n"
            "• PostgreSQL desligado no servidor\n"
            "• Porta errada\n"
            "• Firewall bloqueando\n\n"
            "Verifique e tente novamente."
        )

    if "timeout" in low or "timed out" in low:
        return (
            "❌ TIMEOUT NA REDE.\n\n"
            "• IP errado ou servidor fora\n"
            "• Porta bloqueada\n"
            "• Rede lenta\n\n"
            "Verifique Host/IP e Porta."
        )

    return f"❌ ERRO NA CONEXÃO:\n{s}" if s else "❌ ERRO NA CONEXÃO (motivo não identificado)."


def test_connection(cfg: DBConfig) -> Tuple[bool, str]:
    if psycopg2 is None:
        return False, "❌ psycopg2 não instalado. Instale: pip install psycopg2-binary"

    # Pré-teste: porta aberta?
    try:
        with socket.create_connection((cfg.host, int(cfg.port)), timeout=1.2):
            pass
    except Exception as e:
        return False, (
            "❌ NÃO CONSIGO ALCANÇAR O SERVIDOR.\n\n"
            f"Host/IP: {cfg.host}\n"
            f"Porta: {cfg.port}\n\n"
            "Possíveis causas:\n"
            "• IP errado\n"
            "• Porta fechada\n"
            "• Firewall bloqueando\n"
            "• Servidor desligado\n\n"
            f"Detalhe técnico: {e}"
        )

    # Conexão real
    try:
        conn = psycopg2.connect(
            host=cfg.host,
            port=int(cfg.port),
            dbname=cfg.dbname,
            user=cfg.user,
            password=cfg.password,
            connect_timeout=4,
            options=f"-c search_path={cfg.schema}",
        )
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return True, "✅ CONEXÃO OK!\nAgora clique em “Salvar e continuar”."
    except Exception as e:
        msg = str(e) if e else ""
        return False, _humanize_pg_error(msg, cfg)


# ============================================================
# UI Window
# ============================================================
class SetupBancoWindow:
    def __init__(self, parent=None):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        if parent is not None:
            self.root = ctk.CTkToplevel(parent)
            try:
                self.root.transient(parent)
                self.root.grab_set()
            except Exception:
                pass
        else:
            self.root = ctk.CTk()

        # scan control
        self._scan_stop = threading.Event()
        self._scan_running = False

        self._saved_ok = False
        self._last_test_ok = False
        self.exit_code = 1

        self.root.title("Configuração do Banco de Dados - Sistema Opera")
        self.root.minsize(1100, 650)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ✅ tamanho solicitado
        self._center_window(1200, 700)
        self._bring_to_front()

        existing = load_existing_config_validated()
        self._has_existing_config = existing is not None
        self._fixed_dbname = (existing.dbname if existing else "BANCO_OPERA")

        # colors
        C_BG = "#0b1220"
        C_SURFACE = "#0f1b2e"
        C_CARD = "#0d1728"
        C_BORDER = "#1f3b5c"
        C_TEXT_SUB = "#b7c6d8"
        C_OK = "#a6f3b0"
        C_WARN = "#ffd18b"
        C_ERR = "#ff9e9e"
        C_INFO = "#9ecbff"

        self._ui_colors = {"sub": C_TEXT_SUB, "ok": C_OK, "warn": C_WARN, "err": C_ERR, "info": C_INFO}
        self.root.configure(fg_color=C_BG)

        outer = ctk.CTkFrame(self.root, fg_color=C_SURFACE, corner_radius=18, border_width=1, border_color=C_BORDER)
        outer.pack(fill="both", expand=True, padx=18, pady=18)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="Configuração do Banco de Dados",
                     font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="PostgreSQL", fg_color="#162b44", corner_radius=10,
                     text_color=C_TEXT_SUB, font=ctk.CTkFont(size=12, weight="bold"),
                     padx=10, pady=4).grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(header,
                     text="Informe os dados do servidor e teste a conexão antes de salvar.",
                     font=ctk.CTkFont(size=12), text_color=C_TEXT_SUB).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        # Content
        content = ctk.CTkFrame(outer, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))
        content.grid_columnconfigure(0, weight=1, uniform="col")
        content.grid_columnconfigure(1, weight=2, uniform="col")
        content.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(content, fg_color=C_CARD, corner_radius=16, border_width=1, border_color=C_BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        right = ctk.CTkFrame(content, fg_color=C_CARD, corner_radius=16, border_width=1, border_color=C_BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(1, weight=1)

        # LEFT
        ctk.CTkLabel(left, text="Passos rápidos", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 6)
        )
        steps_txt = (
            "1) Escolha Local ou Rede\n"
            "2) Detecte servidores ou preencha Host/IP e Porta\n"
            "3) Informe Usuário, Senha e Schema\n"
            "4) Clique em “Testar conexão”\n"
            "5) Salve para concluir"
        )
        ctk.CTkLabel(left, text=steps_txt, justify="left",
                     text_color=C_TEXT_SUB, font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=16, pady=(0, 10)
        )

        ctk.CTkLabel(left, text="Banco (fixo)", text_color=C_TEXT_SUB,
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16, pady=(10, 2))
        ctk.CTkLabel(left, text=self._fixed_dbname,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=16, pady=(0, 12))

        ctk.CTkLabel(left, text="Servidores encontrados", text_color=C_TEXT_SUB,
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16, pady=(6, 2))

        self.var_found = tk.StringVar(value="(nenhum ainda)")
        self.opt_found = ctk.CTkOptionMenu(
            left,
            values=["(nenhum ainda)"],
            variable=self.var_found,
            command=self._on_select_found_server
        )
        self.opt_found.pack(fill="x", padx=16, pady=(0, 10))

        self.btn_scan = ctk.CTkButton(left, text="Detectar servidores na rede", command=self._on_scan_network)
        self.btn_scan.pack(fill="x", padx=16, pady=(0, 8))

        self.btn_cancel_scan = ctk.CTkButton(
            left, text="Cancelar scan",
            fg_color="#7a1f1f", hover_color="#9a2a2a",
            command=self._on_cancel_scan, state="disabled"
        )
        self.btn_cancel_scan.pack(fill="x", padx=16, pady=(0, 14))

        # RIGHT
        ctk.CTkLabel(right, text="Dados da conexão", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8)
        )

        self.lbl_center = ctk.CTkLabel(
            right, text="",
            text_color=C_INFO,
            font=ctk.CTkFont(size=13, weight="bold"),
            justify="left"
        )
        self.lbl_center.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 12))

        self.var_mode = tk.StringVar(value=(existing.mode if existing else "local"))

        mode_box = ctk.CTkFrame(right, fg_color="transparent")
        mode_box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 12))
        mode_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(mode_box, text="Tipo de banco", text_color=C_TEXT_SUB, font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, sticky="w"
        )
        rb = ctk.CTkFrame(mode_box, fg_color="transparent")
        rb.grid(row=0, column=1, sticky="e")
        ctk.CTkRadioButton(rb, text="Local", value="local", variable=self.var_mode).pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(rb, text="Rede", value="rede", variable=self.var_mode).pack(side="left")

        def field(label: str, row: int, col: int, default: str = "", width: int = 320, show: str | None = None):
            ctk.CTkLabel(right, text=label, text_color=C_TEXT_SUB, font=ctk.CTkFont(size=11)).grid(
                row=row, column=col, sticky="w", padx=16, pady=(0, 4)
            )
            ent = ctk.CTkEntry(right, width=width, show=show) if show else ctk.CTkEntry(right, width=width)
            ent.grid(row=row + 1, column=col, sticky="ew", padx=16, pady=(0, 10))
            if self._has_existing_config and default:
                ent.insert(0, default)
            return ent

        self.ent_host = field("Host / IP", 4, 0, default=(existing.host if existing else ""))
        self.ent_port = field("Porta", 4, 1, default=(str(existing.port) if existing else ""), width=220)

        self.ent_user = field("Usuário", 6, 0, default=(existing.user if existing else ""))
        self.ent_schema = field("Schema", 6, 1, default=(existing.schema if existing else "opera"), width=220)

        ctk.CTkLabel(right, text="Senha", text_color=C_TEXT_SUB, font=ctk.CTkFont(size=11)).grid(
            row=8, column=0, sticky="w", padx=16, pady=(0, 4)
        )
        self.ent_pass = ctk.CTkEntry(right, show="•")
        self.ent_pass.grid(row=9, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))
        if self._has_existing_config and existing.password:
            self.ent_pass.insert(0, existing.password)

        self.var_show = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(right, text="Mostrar senha", variable=self.var_show, command=self._toggle_pass).grid(
            row=10, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 10)
        )

        # Footer
        footer = ctk.CTkFrame(outer, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        footer.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(
            footer,
            text="Pronto. Preencha e clique em “Testar conexão”.",
            text_color=C_TEXT_SUB,
            font=ctk.CTkFont(size=12),
        )
        self.lbl_status.grid(row=0, column=0, sticky="w")

        btns = ctk.CTkFrame(footer, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e")

        self.btn_detect = ctk.CTkButton(btns, text="Detectar porta", width=140, command=self._on_detect_port)
        self.btn_detect.pack(side="left", padx=(0, 10))

        self.btn_test = ctk.CTkButton(btns, text="Testar conexão", width=140, command=self._on_test)
        self.btn_test.pack(side="left", padx=(0, 10))

        self.btn_save = ctk.CTkButton(btns, text="Salvar e continuar", width=170, command=self._on_save, state="disabled")
        self.btn_save.pack(side="left")

        self.root.bind("<Escape>", lambda e: self._on_close())

        # Mensagem inicial
        if not self._has_existing_config:
            self._set_center(
                "Primeira configuração:\n"
                "• Clique em “Detectar servidores na rede” (esquerda)\n"
                "• Ou preencha Host/IP e Porta manualmente\n"
                "Depois: Testar conexão → Salvar.",
                "info"
            )
        else:
            self._set_center(
                "Configuração validada anterior carregada.\nClique em “Testar conexão” para confirmar.",
                "info"
            )

    # ---------- window helpers ----------
    def _center_window(self, w: int, h: int):
        try:
            self.root.update_idletasks()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = int((sw - w) / 2)
            y = int((sh - h) / 2)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            self.root.geometry(f"{w}x{h}")

    def _bring_to_front(self):
        try:
            self.root.lift()
            self.root.focus_force()
            self.root.attributes("-topmost", True)
            self.root.after(250, lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass

    def _set_center(self, text: str, kind: str = "info"):
        color = self._ui_colors.get(kind, self._ui_colors["info"])
        self.lbl_center.configure(text=text, text_color=color)

    def _toggle_pass(self):
        self.ent_pass.configure(show="" if self.var_show.get() else "•")

    def _on_close(self):
        self.exit_code = 0 if self._saved_ok else 1
        try:
            self.root.destroy()
        except Exception:
            pass

    # ---------- servers found ----------
    def _on_select_found_server(self, value: str):
        """
        value no formato: "192.168.0.110:5432"
        """
        try:
            if not value or value.startswith("("):
                return
            if ":" not in value:
                return
            ip, port = value.split(":", 1)
            ip = ip.strip()
            port = port.strip()

            if ip:
                self.ent_host.delete(0, "end")
                self.ent_host.insert(0, ip)
            if port:
                self.ent_port.delete(0, "end")
                self.ent_port.insert(0, port)

            self._set_center(
                f"✅ Servidor selecionado: {ip}:{port}\nAgora clique em “Testar conexão”.",
                "ok"
            )
        except Exception:
            pass

    # ---------- scan control ----------
    def _on_cancel_scan(self):
        if self._scan_running:
            self._scan_stop.set()
            self._set_center("⛔ Cancelando scan... aguarde.", "warn")

    def _scan_try_ip(self, ip: str, ports_to_check: List[int]) -> Optional[str]:
        if self._scan_stop.is_set():
            return None
        for p in ports_to_check:
            if self._scan_stop.is_set():
                return None
            if _probe_port(ip, p, timeout=0.14):
                return f"{ip}:{p}"
        return None

    def _scan_network_for_postgres_parallel(self) -> List[str]:
        """
        Scan paralelo em /24 procurando portas 5432–5435.
        """
        local_ip = get_local_ip()
        cidr = infer_cidr_24(local_ip)
        if not cidr:
            return []

        ports_to_check = [5432, 5433, 5434, 5435]
        ips = [ip for ip in iter_ips_from_cidr24(cidr) if ip != local_ip]

        found: List[str] = []
        total = len(ips)
        tested = 0
        last_ui = 0.0

        max_workers = 64  # rápido na LAN; se quiser mais leve, use 32

        def ui_update(force=False):
            nonlocal last_ui
            now = time.time()
            if force or (now - last_ui) > 0.25:
                last_ui = now
                self._set_center(
                    f"🔎 Escaneando rede {cidr} (5432–5435)\n"
                    f"Progresso: {tested}/{total} | Encontrados: {len(found)}\n"
                    f"{'⛔ Cancelamento solicitado...' if self._scan_stop.is_set() else ''}",
                    "warn" if self._scan_stop.is_set() else "info"
                )
                self.lbl_status.configure(
                    text=f"Escaneando... {tested}/{total} | encontrados: {len(found)}",
                    text_color=self._ui_colors["sub"]
                )
                self.root.update_idletasks()

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(self._scan_try_ip, ip, ports_to_check): ip for ip in ips}

            for fut in as_completed(futures):
                if self._scan_stop.is_set():
                    break

                tested += 1
                try:
                    res = fut.result()
                    if res:
                        found.append(res)
                except Exception:
                    pass

                ui_update(force=False)

        ui_update(force=True)
        found.sort()
        return found

    def _on_scan_network(self):
        if self._scan_running:
            return

        self._scan_running = True
        self._scan_stop.clear()

        self.btn_scan.configure(state="disabled")
        self.btn_cancel_scan.configure(state="normal")
        self._set_center("🔎 Iniciando scan rápido na rede (5432–5435)...", "info")
        self.lbl_status.configure(text="Escaneando rede... (rápido)", text_color=self._ui_colors["sub"])
        self.root.update_idletasks()

        def worker():
            try:
                found = self._scan_network_for_postgres_parallel()
            except Exception:
                found = []

            def done():
                self._scan_running = False
                self.btn_scan.configure(state="normal")
                self.btn_cancel_scan.configure(state="disabled")

                if self._scan_stop.is_set():
                    if found:
                        self.opt_found.configure(values=found)
                        self.var_found.set(found[0])
                        self._on_select_found_server(found[0])
                        self._set_center(
                            f"⛔ Scan cancelado.\nMesmo assim encontrei {len(found)} servidor(es).\nSelecione e teste conexão.",
                            "warn"
                        )
                        self.lbl_status.configure(text="Scan cancelado (com resultados)", text_color=self._ui_colors["warn"])
                    else:
                        self.opt_found.configure(values=["(nenhum encontrado)"])
                        self.var_found.set("(nenhum encontrado)")
                        self._set_center("⛔ Scan cancelado. Nenhum servidor listado.", "warn")
                        self.lbl_status.configure(text="Scan cancelado", text_color=self._ui_colors["warn"])
                    return

                if found:
                    self.opt_found.configure(values=found)
                    self.var_found.set(found[0])
                    self._on_select_found_server(found[0])
                    self.lbl_status.configure(text=f"Encontrados: {len(found)}", text_color=self._ui_colors["ok"])
                    self._set_center(
                        f"✅ Encontrei {len(found)} servidor(es).\nSelecione um e clique em “Testar conexão”.",
                        "ok"
                    )
                else:
                    self.opt_found.configure(values=["(nenhum encontrado)"])
                    self.var_found.set("(nenhum encontrado)")
                    self.lbl_status.configure(text="Nenhum servidor encontrado", text_color=self._ui_colors["warn"])
                    self._set_center(
                        "⚠️ Não encontrei PostgreSQL na rede.\n\n"
                        "Cheque no SERVIDOR:\n"
                        "• PostgreSQL ligado\n"
                        "• Firewall liberando 5432–5435\n"
                        "• listen_addresses = '*'\n"
                        "Depois tente novamente.",
                        "warn"
                    )

            self.root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    # ---------- validate / actions ----------
    def _validate_fields_before_test(self) -> Tuple[bool, str]:
        host = self.ent_host.get().strip()
        port = self.ent_port.get().strip()
        user = self.ent_user.get().strip()
        schema = self.ent_schema.get().strip()

        missing = []
        if not host:
            missing.append("Host/IP")
        if not port:
            missing.append("Porta")
        if not user:
            missing.append("Usuário")
        if not schema:
            missing.append("Schema")

        if missing:
            return False, "⚠️ FALTANDO PREENCHER:\n• " + "\n• ".join(missing)

        try:
            p = int(port)
            if p <= 0 or p > 65535:
                return False, "⚠️ PORTA INVÁLIDA.\nUse um número entre 1 e 65535 (ex: 5432)."
        except Exception:
            return False, "⚠️ PORTA INVÁLIDA.\nUse somente números (ex: 5432)."

        return True, ""

    def _on_detect_port(self):
        host = self.ent_host.get().strip()
        if not host:
            self._set_center("⚠️ Informe o Host/IP primeiro (ex: 192.168.0.110).", "warn")
            return

        self.lbl_status.configure(text="Detectando portas comuns...", text_color=self._ui_colors["sub"])
        self._set_center("Procurando portas 5432/5433/5434/5435 abertas...", "info")
        self.root.update_idletasks()

        ports = detect_ports(host)
        if ports:
            self.ent_port.delete(0, "end")
            self.ent_port.insert(0, str(ports[0]))
            self.lbl_status.configure(text=f"Porta detectada: {ports[0]}", text_color=self._ui_colors["ok"])
            self._set_center(f"✅ Porta encontrada: {ports[0]}\nAgora clique em “Testar conexão”.", "ok")
        else:
            self.lbl_status.configure(text="Nenhuma porta comum detectada.", text_color=self._ui_colors["warn"])
            self._set_center(
                "⚠️ Não encontrei portas comuns abertas.\n"
                "• Informe a porta manualmente (geralmente 5432)\n"
                "• Verifique firewall/servidor\n"
                "Depois teste.",
                "warn"
            )

    def _current_cfg(self) -> DBConfig:
        host = self.ent_host.get().strip()
        port_txt = self.ent_port.get().strip()
        user = self.ent_user.get().strip()
        password = self.ent_pass.get()
        schema = self.ent_schema.get().strip()
        mode = self.var_mode.get().strip() or "local"

        try:
            port = int(port_txt) if port_txt else 5432
        except Exception:
            port = 5432

        return DBConfig(
            mode=mode,
            host=host,
            port=port,
            dbname=self._fixed_dbname,
            user=user,
            password=password,
            schema=(schema or "opera"),
        )

    def _on_test(self):
        ok_fields, msg = self._validate_fields_before_test()
        if not ok_fields:
            self._last_test_ok = False
            self.btn_save.configure(state="disabled")
            self._set_center(msg, "warn")
            self.lbl_status.configure(text="Aguardando correções...", text_color=self._ui_colors["warn"])
            return

        cfg = self._current_cfg()

        self.lbl_status.configure(text="Testando conexão...", text_color=self._ui_colors["sub"])
        self._set_center("Testando conexão com o servidor...", "info")
        self.root.update_idletasks()

        ok, msg = test_connection(cfg)
        self._last_test_ok = ok

        if ok:
            self._set_center(msg, "ok")
            self.lbl_status.configure(text="Conexão bem sucedida ✅", text_color=self._ui_colors["ok"])
            self.btn_save.configure(state="normal")
        else:
            self._set_center(msg, "err")
            self.lbl_status.configure(text="Falha na conexão ❌", text_color=self._ui_colors["err"])
            self.btn_save.configure(state="disabled")

    def _on_save(self):
        if not self._last_test_ok:
            self._set_center("⚠️ Você precisa ter ✅ CONEXÃO OK antes de salvar.", "warn")
            return

        cfg = self._current_cfg()
        try:
            path = save_config(cfg)
            self._saved_ok = True
            self.exit_code = 0
            self._set_center("✅ Configuração salva e validada.\nAbrindo o sistema...", "ok")
            messagebox.showinfo("Configuração salva", f"Configuração salva com sucesso em:\n{path}")
            self.root.destroy()
        except Exception as e:
            self._set_center(f"❌ Falha ao salvar config.\nDetalhe: {e}", "err")
            messagebox.showerror("Erro ao salvar", f"Não foi possível salvar o config.json.\n\n{e}")


# ============================================================
# Entrypoint
# ============================================================
def main():
    window = SetupBancoWindow(parent=None)
    window.root.mainloop()
    return window.exit_code


if __name__ == "__main__":
    raise SystemExit(main())