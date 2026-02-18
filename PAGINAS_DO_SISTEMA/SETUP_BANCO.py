# -*- coding: utf-8 -*-
"""
SETUP_BANCO.py — Configurador de Banco (Universal Mac/Windows)

- Abre janela de configuração do Postgres
- Deve ser chamada também quando a conexão com o banco cair (ou se o config.json sumir/corromper)
- Detecta porta e testa conexão para reencontrar o banco
- Só permite "Salvar e concluir" após conexão OK
- Se fechar no X sem salvar: retorna exit code 1 (cancelado)
- Salva config.json atualizado em múltiplos lugares (criando pastas automaticamente):
  1) Local correto do app (Mac: Application Support / Windows: AppData)
  2) AppData/Application Support/PAGINAS_DO_SISTEMA/config.json
  3) Pasta atual do projeto (PAGINAS_DO_SISTEMA/config.json)
  4) Raiz do projeto (../config.json)
  5) Candidatos de instalação no diretório do executável e cwd
"""

from __future__ import annotations

import json
import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

# --- FIX encoding (Windows) ---
# Em Postgres no Windows, o cluster pode estar em WIN1252 e algumas mensagens vêm em cp1252.
# Se o psycopg2 carregar antes disso, pode dar: utf-8 codec can't decode byte 0xe3...
if sys.platform.startswith("win"):
    os.environ.setdefault("PGCLIENTENCODING", "WIN1252")
    # Opcional: força também via GUC logo na conexão (não atrapalha)
    os.environ.setdefault("PGOPTIONS", "-c client_encoding=WIN1252")

try:
    import psycopg2
except Exception:
    psycopg2 = None


# ============================================================
# Paths (usa OPERA_PATHS se existir; senão fallback)
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



def _server_info_candidates() -> List[Path]:
    """Locais prováveis do server_info.json gerado no servidor."""
    candidates: List[Path] = []

    program_data = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
    candidates.append(program_data / "Opera" / "server_info.json")

    try:
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "server_info.json")
    except Exception:
        pass

    try:
        cwd = Path.cwd().resolve()
        candidates.append(cwd / "server_info.json")
    except Exception:
        pass

    # fallback do repositório (útil em dev)
    candidates.append(PROJECT_ROOT / "server_info.json")

    dedup: List[Path] = []
    seen = set()
    for c in candidates:
        key = str(c)
        if key not in seen:
            seen.add(key)
            dedup.append(c)
    return dedup


def _load_server_info(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None

        host = str(raw.get("host") or "").strip()
        if not host:
            return None

        return {
            "mode": "rede",
            "host": host,
            "port": int(raw.get("port") or 5432),
            "dbname": str(raw.get("dbname") or "BANCO_OPERA"),
            "user": str(raw.get("user") or "postgres"),
            "password": str(raw.get("password") or ""),
            "schema": str(raw.get("schema") or "opera"),
            "source": str(path),
        }
    except Exception:
        return None


def _runtime_pagina_config_candidates() -> List[Path]:
    """
    Candidatos extras para instalação (Windows/Mac):
    - diretório do executável + PAGINAS_DO_SISTEMA/config.json
    - diretório atual + PAGINAS_DO_SISTEMA/config.json
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

    # evita duplicados mantendo ordem
    dedup: List[Path] = []
    seen = set()
    for p in candidates:
        key = str(p)
        if key not in seen:
            seen.add(key)
            dedup.append(p)
    return dedup


# ============================================================
# Model
# ============================================================
@dataclass
class DBConfig:
    mode: str = "local"      # local | rede
    host: str = "localhost"
    port: int = 5432
    dbname: str = "BANCO_OPERA"
    user: str = "postgres"
    password: str = ""
    schema: str = "opera"


def _config_candidates() -> List[Path]:
    # prioridade dev -> oficial
    return [
        DEV_CONFIG_FILE_PAGINAS,
        DEV_CONFIG_FILE_PARENT,
        APP_PAGINAS_CONFIG_FILE,
        CONFIG_FILE,
        *_runtime_pagina_config_candidates(),
    ]


def _config_from_server_info() -> Optional[DBConfig]:
    for path in _server_info_candidates():
        data = _load_server_info(path)
        if data:
            print(f"[CONFIG] server_info.json detectado: {path}")
            return DBConfig(
                mode=str(data.get("mode") or "rede"),
                host=str(data.get("host") or "localhost"),
                port=int(data.get("port") or 5432),
                dbname=str(data.get("dbname") or "BANCO_OPERA"),
                user=str(data.get("user") or "postgres"),
                password=str(data.get("password") or ""),
                schema=str(data.get("schema") or "opera"),
            )
    return None


def load_existing_config() -> Optional[DBConfig]:
    for p in _config_candidates():
        try:
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8")) or {}
                if not isinstance(data, dict):
                    continue

                # aceita "formato grande" (defaults/hosts/ports)
                if "defaults" in data and isinstance(data.get("defaults"), dict):
                    defaults = data.get("defaults") or {}
                    host = (data.get("hosts") or ["localhost"])[0]
                    ports = data.get("ports") or [5432]
                    port = int(ports[0]) if ports else 5432
                    schema = (data.get("schema") or data.get("pg_schema") or "opera") or "opera"

                    return DBConfig(
                        mode=(data.get("mode") or "local"),
                        host=str(host or "localhost"),
                        port=int(port),
                        dbname=str(defaults.get("dbname") or "BANCO_OPERA"),
                        user=str(defaults.get("user") or "postgres"),
                        password=str(defaults.get("password") or ""),
                        schema=str(schema),
                    )

                # formato simples
                return DBConfig(
                    mode=str(data.get("mode") or "local"),
                    host=str(data.get("host") or "localhost"),
                    port=int(data.get("port") or 5432),
                    dbname=str(data.get("dbname") or "BANCO_OPERA"),
                    user=str(data.get("user") or "postgres"),
                    password=str(data.get("password") or ""),
                    schema=str(data.get("schema") or "opera"),
                )
        except Exception:
            pass
    return None


def save_config(cfg: DBConfig) -> Path:
    """
    Salva config.json em múltiplos lugares e cria as pastas se não existirem.

    Isso mantém o arquivo sempre atualizado para o módulo `banco_de_dados_pg`,
    inclusive em fluxos de recuperação quando a conexão foi perdida.
    """
    payload_dict = {
        "mode": cfg.mode,
        "host": cfg.host,
        "port": int(cfg.port),
        "dbname": cfg.dbname,
        "user": cfg.user,
        "password": cfg.password,
        "schema": cfg.schema,
        # formato expandido para compatibilidade com BANCO_DE_DADOS_PG.py
        "defaults": {
            "dbname": cfg.dbname,
            "user": cfg.user,
            "password": cfg.password,
        },
        "hosts": [cfg.host],
        "ports": [int(cfg.port)],
        "appname": "OPERA_APP",
        "connect_timeout": 8,
    }
    payload = json.dumps(payload_dict, ensure_ascii=False, indent=2)

    targets = [
        CONFIG_FILE,             # oficial (Mac/Windows)
        APP_PAGINAS_CONFIG_FILE, # AppData/Application Support/PAGINAS_DO_SISTEMA/config.json
        DEV_CONFIG_FILE_PAGINAS, # PAGINAS_DO_SISTEMA/config.json
        DEV_CONFIG_FILE_PARENT,  # raiz do projeto/config.json
        *_runtime_pagina_config_candidates(),
    ]

    for path in targets:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")
            print(f"[CONFIG] salvo em: {path}")
        except Exception as e:
            print(f"[CONFIG] falha ao salvar em {path}: {e}")

    return CONFIG_FILE


# ============================================================
# Helpers: detect port / test connection
# ============================================================
def _probe_port(host: str, port: int, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def detect_ports(host: str) -> List[int]:
    common = [5432, 5433, 5434, 5435]
    return [p for p in common if _probe_port(host, p)]


def test_connection(cfg: DBConfig) -> Tuple[bool, str]:
    if psycopg2 is None:
        return False, "psycopg2 não está instalado. Instale: pip install psycopg2-binary"

    # 1) Pré-teste de rede/porta (evita timeout longo do psycopg2)
    try:
        with socket.create_connection((cfg.host, int(cfg.port)), timeout=1.2):
            pass
    except Exception as e:
        return False, f"Falha: servidor/porta inacessível ({cfg.host}:{cfg.port}) - {e}"

    # 2) Conexão real no Postgres
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
        return True, "✅ Conexão OK!"
    except Exception as e:
        # evita estourar decode ao converter erro em texto
        try:
            msg = str(e)
        except Exception:
            msg = repr(e)
        return False, f"Falha: {msg}"




# ============================================================
# UI Window
# ============================================================
class SetupBancoWindow:
    def __init__(self, parent=None):
        # --- Aparência (somente UI) ---
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Se já existe UI (root), criamos Toplevel modal
        if parent is not None:
            self.root = ctk.CTkToplevel(parent)
            try:
                self.root.transient(parent)
                self.root.grab_set()
            except Exception:
                pass
        else:
            self.root = ctk.CTk()

        self._saved_ok = False
        self._last_test_ok = False
        self.exit_code = 1

        self.root.title("Configuração do Banco de Dados - Sistema Opera")
        self.root.minsize(940, 660)

        # fecha no X
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # tamanho + centralização
        self._center_window(940, 660)

        # trazer pra frente
        self._bring_to_front()

        existing = load_existing_config() or _config_from_server_info() or DBConfig()

        # ===========================
        # UI — Layout moderno (grid)
        # ===========================
        C_BG = "#0b1220"
        C_SURFACE = "#0f1b2e"
        C_CARD = "#0d1728"
        C_BORDER = "#1f3b5c"
        C_TEXT_SUB = "#b7c6d8"
        C_OK = "#a6f3b0"
        C_WARN = "#ffd18b"
        C_ERR = "#ff9e9e"

        self._ui_colors = {"sub": C_TEXT_SUB, "ok": C_OK, "warn": C_WARN, "err": C_ERR}

        self.root.configure(fg_color=C_BG)

        outer = ctk.CTkFrame(
            self.root,
            fg_color=C_SURFACE,
            corner_radius=18,
            border_width=1,
            border_color=C_BORDER,
        )
        outer.pack(fill="both", expand=True, padx=18, pady=18)

        # grid base
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=1)

        # ---------- Header ----------
        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Configuração do Banco de Dados",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        badge = ctk.CTkLabel(
            header,
            text="PostgreSQL",
            fg_color="#162b44",
            corner_radius=10,
            text_color=C_TEXT_SUB,
            font=ctk.CTkFont(size=12, weight="bold"),
            padx=10,
            pady=4,
        )
        badge.grid(row=0, column=1, sticky="e")

        subtitle = ctk.CTkLabel(
            header,
            text="Informe os dados do servidor e teste a conexão antes de salvar.",
            font=ctk.CTkFont(size=12),
            text_color=C_TEXT_SUB,
        )
        subtitle.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # ---------- Content (2 col) ----------
        content = ctk.CTkFrame(outer, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))
        content.grid_columnconfigure(0, weight=1, uniform="col")
        content.grid_columnconfigure(1, weight=2, uniform="col")
        content.grid_rowconfigure(0, weight=1)

        # Left: resumo / ajuda rápida
        left = ctk.CTkFrame(content, fg_color=C_CARD, corner_radius=16, border_width=1, border_color=C_BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left,
            text="Passos rápidos",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        steps_txt = (
            "1) Escolha Local ou Rede\n"
            "2) Preencha Host/IP e Porta\n"
            "3) Informe Usuário, Senha e Schema\n"
            "4) Clique em “Testar conexão”\n"
            "5) Salve para concluir"
        )
        ctk.CTkLabel(
            left,
            text=steps_txt,
            justify="left",
            text_color=C_TEXT_SUB,
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        # infos fixas (somente UI — leitura)
        self._fixed_dbname = existing.dbname or "BANCO_OPERA"
        info = ctk.CTkFrame(left, fg_color="transparent")
        info.grid(row=2, column=0, sticky="ew", padx=16, pady=(6, 14))
        info.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(info, text="Banco (fixo)", text_color=C_TEXT_SUB, font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(info, text=self._fixed_dbname, font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=1, column=0, sticky="w", pady=(2, 0)
        )

        # Right: formulário
        right = ctk.CTkFrame(content, fg_color=C_CARD, corner_radius=16, border_width=1, border_color=C_BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=0)
        right.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            right,
            text="Dados da conexão",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 10))

        # --- Tipo (Local/Rede) ---
        self.var_mode = tk.StringVar(value=existing.mode if existing.mode in ("local", "rede") else "local")

        mode_box = ctk.CTkFrame(right, fg_color="transparent")
        mode_box.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 12))
        mode_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(mode_box, text="Tipo de banco", text_color=C_TEXT_SUB, font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, sticky="w"
        )

        rb = ctk.CTkFrame(mode_box, fg_color="transparent")
        rb.grid(row=0, column=1, sticky="e")
        ctk.CTkRadioButton(rb, text="Local", value="local", variable=self.var_mode).pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(rb, text="Rede", value="rede", variable=self.var_mode).pack(side="left")

        # --- Campos (grid) ---
        def field(label: str, row: int, col: int, default: str = "", width: int = 320, show: str | None = None):
            ctk.CTkLabel(
                right,
                text=label,
                text_color=C_TEXT_SUB,
                font=ctk.CTkFont(size=11),
            ).grid(row=row, column=col, sticky="w", padx=16, pady=(0, 4))
            ent = ctk.CTkEntry(right, width=width, show=show) if show else ctk.CTkEntry(right, width=width)
            ent.grid(row=row + 1, column=col, sticky="ew", padx=16, pady=(0, 10))
            if default:
                ent.insert(0, default)
            return ent

        # Host / Porta
        self.ent_host = field("Host / IP", 2, 0, default=str(existing.host or "localhost"))
        self.ent_port = field("Porta", 2, 1, default=str(existing.port or 5432), width=220)

        # Usuário / Schema
        self.ent_user = field("Usuário", 4, 0, default=str(existing.user or "postgres"))
        self.ent_schema = field("Schema", 4, 1, default=str(existing.schema or "opera"), width=220)

        # Senha (linha cheia)
        ctk.CTkLabel(
            right,
            text="Senha",
            text_color=C_TEXT_SUB,
            font=ctk.CTkFont(size=11),
        ).grid(row=6, column=0, sticky="w", padx=16, pady=(0, 4))

        self.ent_pass = ctk.CTkEntry(right, show="•")
        self.ent_pass.grid(row=7, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))
        if existing.password:
            self.ent_pass.insert(0, existing.password)

        self.var_show = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            right,
            text="Mostrar senha",
            variable=self.var_show,
            command=self._toggle_pass,
        ).grid(row=8, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 10))

        # ---------- Footer ----------
        footer = ctk.CTkFrame(outer, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        footer.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(
            footer,
            text=f"Pronto. Porta sugerida: {existing.port}",
            text_color=C_TEXT_SUB,
            font=ctk.CTkFont(size=12),
        )
        self.lbl_status.grid(row=0, column=0, sticky="w")

        btns = ctk.CTkFrame(footer, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e")

        self.btn_detect = ctk.CTkButton(btns, text="Detectar porta", width=140, command=self._on_detect_port)
        self.btn_detect.pack(side="left", padx=(0, 10))

        self.btn_import = ctk.CTkButton(btns, text="Importar server_info", width=170, command=self._on_import_server_info)
        self.btn_import.pack(side="left", padx=(0, 10))

        self.btn_test = ctk.CTkButton(btns, text="Testar conexão", width=140, command=self._on_test)
        self.btn_test.pack(side="left", padx=(0, 10))

        self.btn_save = ctk.CTkButton(btns, text="Salvar e continuar", width=170, command=self._on_save, state="disabled")
        self.btn_save.pack(side="left")

        self.root.bind("<Escape>", lambda e: self._on_close())

    # -------------------------
    # Window helpers
    # -------------------------
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

    # -------------------------
    # Close behavior
    # -------------------------
    def _on_close(self):
        # Se não salvou com sucesso, consideramos cancelado
        if not self._saved_ok:
            self.exit_code = 1
            try:
                self.root.destroy()
            except Exception:
                pass
            return

        self.exit_code = 0
        try:
            self.root.destroy()
        except Exception:
            pass

    # -------------------------
    # UI actions
    # -------------------------
    def _toggle_pass(self):
        try:
            self.ent_pass.configure(show="" if self.var_show.get() else "•")
        except Exception:
            pass

    def _current_cfg(self) -> DBConfig:
        host = self.ent_host.get().strip() or "localhost"
        schema = self.ent_schema.get().strip() or "opera"
        dbname = self._fixed_dbname
        user = self.ent_user.get().strip() or "postgres"
        password = self.ent_pass.get()

        try:
            port = int(self.ent_port.get().strip() or "5432")
        except Exception:
            port = 5432

        mode = self.var_mode.get().strip() or "local"

        return DBConfig(
            mode=mode,
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            schema=schema,
        )


    def _apply_external_cfg(self, cfg: DBConfig):
        self.var_mode.set(cfg.mode if cfg.mode in ("local", "rede") else "rede")

        self.ent_host.delete(0, "end")
        self.ent_host.insert(0, str(cfg.host or "localhost"))

        self.ent_port.delete(0, "end")
        self.ent_port.insert(0, str(cfg.port or 5432))

        self.ent_user.delete(0, "end")
        self.ent_user.insert(0, str(cfg.user or "postgres"))

        self.ent_schema.delete(0, "end")
        self.ent_schema.insert(0, str(cfg.schema or "opera"))

        self.ent_pass.delete(0, "end")
        if cfg.password:
            self.ent_pass.insert(0, cfg.password)

        self._last_test_ok = False
        self.btn_save.configure(state="disabled")

    def _on_import_server_info(self):
        path_txt = filedialog.askopenfilename(
            title="Selecione o server_info.json",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
        )
        if not path_txt:
            return

        data = _load_server_info(Path(path_txt))
        if not data:
            messagebox.showerror("Importação", "Arquivo inválido. Selecione um server_info.json válido.")
            return

        cfg = DBConfig(
            mode=str(data.get("mode") or "rede"),
            host=str(data.get("host") or "localhost"),
            port=int(data.get("port") or 5432),
            dbname=self._fixed_dbname,
            user=str(data.get("user") or "postgres"),
            password=str(data.get("password") or ""),
            schema=str(data.get("schema") or "opera"),
        )
        self._apply_external_cfg(cfg)
        self.lbl_status.configure(
            text=f"server_info importado: {path_txt}",
            text_color=self._ui_colors.get("ok", "#a6f3b0"),
        )

    def _on_detect_port(self):
        host = self.ent_host.get().strip() or "localhost"
        self.lbl_status.configure(text="Detectando portas...", text_color=self._ui_colors.get("sub", "#b7c6d8"))
        self.root.update_idletasks()

        ports = detect_ports(host)
        if ports:
            self.ent_port.delete(0, "end")
            self.ent_port.insert(0, str(ports[0]))
            self.lbl_status.configure(text=f"Porta detectada: {ports[0]}", text_color=self._ui_colors.get("ok", "#a6f3b0"))
        else:
            self.lbl_status.configure(text="⚠️ Nenhuma porta detectada. Informe manualmente.", text_color=self._ui_colors.get("warn", "#ffd18b"))

    def _on_test(self):
        cfg = self._current_cfg()
        ok, msg = test_connection(cfg)
        self._last_test_ok = ok

        if ok:
            self.lbl_status.configure(text=msg, text_color=self._ui_colors.get("ok", "#a6f3b0"))
            self.btn_save.configure(state="normal")
        else:
            self.lbl_status.configure(text=msg, text_color=self._ui_colors.get("err", "#ff9e9e"))
            self.btn_save.configure(state="disabled")

    def _on_save(self):
        if not self._last_test_ok:
            messagebox.showwarning("Validação", "Teste a conexão e confirme que está OK antes de salvar.")
            return

        cfg = self._current_cfg()
        try:
            path = save_config(cfg)
            self._saved_ok = True
            self.exit_code = 0
            messagebox.showinfo("Configuração salva", f"Configuração salva com sucesso em:\n{path}")
            self.root.destroy()
        except Exception as e:
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