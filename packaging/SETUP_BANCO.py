# -*- coding: utf-8 -*-
"""
SETUP_BANCO.py — Configurador de Banco (Universal Mac/Windows)

- Abre janela de configuração do Postgres
- Detecta porta
- Testa conexão
- Só permite "Salvar e concluir" após conexão OK
- Se fechar no X sem salvar: retorna exit code 1 (cancelado)
- Salva config.json em 3 lugares (criando pastas automaticamente):
  1) Local correto do app (Mac: Application Support / Windows: AppData)
  2) Pasta atual do projeto (PAGINAS_DO_SISTEMA/config.json)
  3) Raiz do projeto (../config.json)
"""

from __future__ import annotations

import json
import os
import socket
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Tuple

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

try:
    import psycopg2
except Exception:
    psycopg2 = None


# ============================================================
# Paths (usa OPERA_PATHS se existir; senão fallback)
# ============================================================
CURRENT_DIR = Path(__file__).resolve().parent


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

DEV_CONFIG_FILE_HERE = CURRENT_DIR / "config.json"
DEV_CONFIG_FILE_PARENT = CURRENT_DIR.parent / "config.json"


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
    return [DEV_CONFIG_FILE_HERE, DEV_CONFIG_FILE_PARENT, CONFIG_FILE]


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
    Salva config.json em 3 lugares e cria as pastas se não existirem.
    """
    payload = json.dumps(asdict(cfg), ensure_ascii=False, indent=2)

    targets = [
        CONFIG_FILE,             # oficial (Mac/Windows)
        DEV_CONFIG_FILE_HERE,    # PAGINAS_DO_SISTEMA/config.json
        DEV_CONFIG_FILE_PARENT,  # raiz do projeto/config.json
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

    try:
        conn = psycopg2.connect(
            host=cfg.host,
            port=int(cfg.port),
            dbname=cfg.dbname,
            user=cfg.user,
            password=cfg.password,
            connect_timeout=3,
            options=f"-c search_path={cfg.schema}",
        )
        conn.close()
        return True, "✅ Conexão OK!"
    except Exception as e:
        return False, f"❌ Falha: {e}"


# ============================================================
# UI Window
# ============================================================
class SetupBancoWindow:
    def __init__(self, parent=None):
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

        self._parent = parent
        self._saved_ok = False
        self._last_test_ok = False
        self.exit_code = 1

        self.root.title("Configuração do Banco - SistemaOpera")
        self.root.minsize(980, 520)

        # fecha no X
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # tamanho + centralização
        self._center_window(980, 520)

        # trazer pra frente
        self._bring_to_front()

        existing = load_existing_config() or DBConfig()

        # ===== Layout =====
        self.root.configure(fg_color="#0b1220")

        outer = ctk.CTkFrame(self.root, fg_color="#0f1b2e", corner_radius=16, border_width=1, border_color="#1f3b5c")
        outer.pack(fill="both", expand=True, padx=18, pady=18)

        title = ctk.CTkLabel(outer, text="Configuração do Banco de Dados", font=ctk.CTkFont(size=22, weight="bold"))
        title.place(x=26, y=22)

        subtitle = ctk.CTkLabel(
            outer,
            text="Instalação do SistemaOpera • Configure local/rede, teste conexão e conclua.",
            font=ctk.CTkFont(size=12),
            text_color="#b7c6d8",
        )
        subtitle.place(x=26, y=58)

        # ===== Tipo (Local/Rede) =====
        self.var_mode = tk.StringVar(value=existing.mode if existing.mode in ("local", "rede") else "local")

        ctk.CTkLabel(outer, text="Tipo de banco:", font=ctk.CTkFont(size=13, weight="bold")).place(x=26, y=100)
        ctk.CTkRadioButton(outer, text="Local", value="local", variable=self.var_mode).place(x=150, y=100)
        ctk.CTkRadioButton(outer, text="Rede", value="rede", variable=self.var_mode).place(x=240, y=100)

        # ===== Campos =====
        def mk_label(txt, x, y):
            ctk.CTkLabel(outer, text=txt, font=ctk.CTkFont(size=13, weight="bold")).place(x=x, y=y)

        def mk_entry(x, y, w=220, default=""):
            ent = ctk.CTkEntry(outer, width=w)
            ent.place(x=x, y=y)
            ent.insert(0, default)
            return ent

        y1 = 150
        mk_label("Host/IP", 26, y1 - 22)
        self.ent_host = mk_entry(26, y1, 220, existing.host)

        mk_label("Porta", 270, y1 - 22)
        self.ent_port = mk_entry(270, y1, 140, str(existing.port))

        mk_label("Banco", 430, y1 - 22)
        self.ent_db = mk_entry(430, y1, 240, existing.dbname)

        mk_label("Schema", 690, y1 - 22)
        self.ent_schema = mk_entry(690, y1, 240, existing.schema)

        y2 = 220
        mk_label("Usuário", 26, y2 - 22)
        self.ent_user = mk_entry(26, y2, 220, existing.user)

        mk_label("Senha", 270, y2 - 22)
        self.ent_pass = ctk.CTkEntry(outer, width=220, show="•")
        self.ent_pass.place(x=270, y=y2)
        if existing.password:
            self.ent_pass.insert(0, existing.password)

        self.var_show = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(outer, text="Mostrar senha", variable=self.var_show, command=self._toggle_pass)\
            .place(x=420, y=y2 + 42)

        # ===== Status =====
        self.lbl_status = ctk.CTkLabel(outer, text="Aguardando validação.", text_color="#b7c6d8")
        self.lbl_status.place(x=26, y=300)

        # ===== Botões =====
        self.btn_detect = ctk.CTkButton(outer, text="Detectar porta", width=150, command=self._on_detect_port)
        self.btn_detect.place(x=26, y=350)

        self.btn_test = ctk.CTkButton(outer, text="Testar conexão", width=150, command=self._on_test)
        self.btn_test.place(x=190, y=350)

        self.btn_save = ctk.CTkButton(
            outer, text="Salvar e concluir instalação", width=240, command=self._on_save, state="disabled"
        )
        self.btn_save.place(x=690, y=350)

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
        dbname = self.ent_db.get().strip() or "BANCO_OPERA"
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

    def _on_detect_port(self):
        host = self.ent_host.get().strip() or "localhost"
        self.lbl_status.configure(text="Detectando portas...", text_color="#b7c6d8")
        self.root.update_idletasks()

        ports = detect_ports(host)
        if ports:
            self.ent_port.delete(0, "end")
            self.ent_port.insert(0, str(ports[0]))
            self.lbl_status.configure(text=f"✅ Portas detectadas: {ports}", text_color="#a6f3b0")
        else:
            self.lbl_status.configure(text="⚠️ Nenhuma porta detectada. Informe manualmente.", text_color="#ffd18b")

    def _on_test(self):
        cfg = self._current_cfg()
        ok, msg = test_connection(cfg)
        self._last_test_ok = ok

        if ok:
            self.lbl_status.configure(text=msg, text_color="#a6f3b0")
            self.btn_save.configure(state="normal")
        else:
            self.lbl_status.configure(text=msg, text_color="#ff9e9e")
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
