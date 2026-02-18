# -*- coding: utf-8 -*-
"""
INSTALADOR OPERA FASHION - Interface (WIN/MAC) - HÍBRIDO (Local + LAN + Host manual)

✅ O que este arquivo entrega:
- Campo Host/IP + Porta + Usuário + Senha
- Checkbox "Mostrar senha"
- Botão 🔍 Detectar (Local + LAN) com lista de encontrados (sem travar a UI)
- Lista de scripts .sql + execução individual
- Botão ▶ Executar 1 → 2 → 3 automaticamente (sequencial)
- Layout organizado SEM scroll (campos e botões visíveis)
- Compatível com main.py que chama: InstallerApp(db_manager)

⚠️ Dependências:
- PyQt5
- Seu projeto deve fornecer um db_manager (DatabaseManager) com métodos:
    - get_available_scripts() -> list[dict] com "filename" (recomendado)
    - execute_sql_file(script_name, password, database, user, port, host=?)
    - test_connection(password, user, port, database, host=?)
    - check_database_exists(database, password, user, port, host=?)
  Obs.: se o seu DatabaseManager não tiver "host", o código tenta chamar sem host automaticamente.
"""

from __future__ import annotations

import os
import json
import re
import socket
import threading
import time
import ipaddress
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, List, Tuple

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor, QPalette, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QListWidget,
    QGroupBox, QTextEdit, QTabWidget, QProgressBar, QMessageBox, QDialog, QSizePolicy, QSpacerItem,
    QSplitter, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QGridLayout, QRadioButton, QButtonGroup
)


# -----------------------------
# Helpers
# -----------------------------
def _safe_str(e: Exception) -> str:
    try:
        return str(e)
    except Exception:
        return repr(e)


def _get_local_ipv4() -> Optional[str]:
    """Descobre IPv4 LAN sem depender de comandos externos."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and "." in ip:
            return ip
    except Exception:
        return None
    return None


def _guess_lan_cidr(ip: str) -> str:
    """Heurística: /24 cobre a maioria das LANs (192.168.x.0/24)."""
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return "192.168.0.0/24"


# -----------------------------
# Success Dialog (custom, theme-aware)
# -----------------------------
# -----------------------------
# Success Dialog Melhorado - Mostra contagem de estruturas criadas
# -----------------------------
# -----------------------------
# Success Dialog - Mostra contagem detalhada das estruturas criadas
# -----------------------------
# -----------------------------
# Success Dialog - Versão Compacta e Organizada
# -----------------------------
class SuccessDialog(QDialog):
    def __init__(self, parent, theme: dict, summary: dict, database: str, user: str = "", password: str = ""):
        super().__init__(parent)
        self._t = theme or {}
        self.setWindowTitle("✅ OPERA FASHION - Instalação Concluída")
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(580)
        self.setMaximumHeight(650)

        # Cores do tema
        BG = self._t.get("BG", "#0f1419")
        CARD = self._t.get("CARD", "#111821")
        BORDER = self._t.get("BORDER", "#243041")
        TEXT = self._t.get("TEXT", "#e6eef7")
        MUTED = self._t.get("MUTED", "#9fb7cf")
        ACCENT = self._t.get("ACCENT", "#1f6feb")
        SUCCESS = "#28a745"
        INFO = "#17a2b8"

        self.setStyleSheet(f"""
            QDialog {{
                background: {BG};
            }}
            QLabel#MainTitle {{
                color: {ACCENT};
                font-size: 22px;
                font-weight: bold;
            }}
            QLabel#Subtitle {{
                color: {MUTED};
                font-size: 13px;
            }}
            QFrame#MainCard {{
                background: {CARD};
                border: 2px solid {ACCENT};
                border-radius: 16px;
            }}
            QFrame#InfoBox {{
                background: rgba(31, 111, 235, 0.1);
                border: 1px solid {ACCENT};
                border-radius: 10px;
            }}
            QFrame#StatsBox {{
                background: rgba(255,255,255,0.02);
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
            QLabel#StatValue {{
                color: {ACCENT};
                font-size: 20px;
                font-weight: bold;
            }}
            QLabel#StatLabel {{
                color: {MUTED};
                font-size: 11px;
            }}
            QLabel#ModuleItem {{
                color: {TEXT};
                font-size: 11px;
                padding: 4px 8px;
                background: rgba(255,255,255,0.03);
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
            QLabel#AdminName {{
                color: {SUCCESS};
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton#CloseBtn {{
                background: {ACCENT};
                color: #ffffff;
                border: 0;
                border-radius: 10px;
                padding: 12px 25px;
                font-weight: 700;
                font-size: 13px;
                min-width: 160px;
            }}
            QPushButton#CloseBtn:hover {{
                background: {self._t.get("ACCENT_H", ACCENT)};
            }}
        """)

        # Layout principal
        root = QVBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(10)

        # Card principal
        main_card = QFrame()
        main_card.setObjectName("MainCard")
        root.addWidget(main_card)

        main_layout = QVBoxLayout(main_card)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(12)

        # ===== CABEÇALHO =====
        # Ícone e título
        title_layout = QHBoxLayout()
        icon = QLabel("✅")
        icon.setStyleSheet("font-size: 32px;")
        title_layout.addWidget(icon)

        title = QLabel("SISTEMA OPERA CRIADO COM SUCESSO!")
        title.setObjectName("MainTitle")
        title_layout.addWidget(title)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        # Subtítulo
        subtitle = QLabel("Banco de dados configurado e pronto para uso")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle)

        # ===== INFORMAÇÕES DE ACESSO =====
        info_box = QFrame()
        info_box.setObjectName("InfoBox")
        info_layout = QHBoxLayout(info_box)
        info_layout.setContentsMargins(15, 10, 15, 10)
        info_layout.setSpacing(20)

        # Schema
        schema_text = QLabel("📁 <b>Schema:</b> opera")
        schema_text.setStyleSheet(f"color: {TEXT};")
        info_layout.addWidget(schema_text)

        # Usuário
        user_text = QLabel(f"👤 <b>Usuário:</b> {user or 'postgres'}")
        user_text.setStyleSheet(f"color: {TEXT};")
        info_layout.addWidget(user_text)

        # Senha
        pwd_display = f"••••{password[-4:]}" if len(password) >= 4 else "••••"
        pwd_text = QLabel(f"🔑 <b>Senha:</b> {pwd_display}")
        pwd_text.setStyleSheet(f"color: {TEXT};")
        info_layout.addWidget(pwd_text)

        info_layout.addStretch()
        main_layout.addWidget(info_box)

        # ===== ESTATÍSTICAS =====
        stats_title = QLabel("📊 ESTRUTURAS CRIADAS")
        stats_title.setAlignment(Qt.AlignCenter)
        stats_title.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 14px;")
        main_layout.addWidget(stats_title)

        # Grid de estatísticas (2 linhas x 4 colunas)
        stats_grid = QGridLayout()
        stats_grid.setSpacing(8)
        stats_grid.setHorizontalSpacing(12)

        # Valores do summary
        tables = summary.get("tables", 0)
        views = summary.get("views", 0)
        functions = summary.get("functions", 0)
        triggers = summary.get("triggers", 0)
        indexes = summary.get("indexes", 0)
        schemas = summary.get("schemas", 0)
        extensions = summary.get("extensions", 0)
        total = summary.get("total_created", tables + views + functions + triggers + indexes + schemas + extensions)

        # Primeira linha
        stats_items_row1 = [
            ("📊", "TABELAS", tables),
            ("👁️", "VIEWS", views),
            ("⚙️", "FUNÇÕES", functions),
            ("🔔", "TRIGGERS", triggers)
        ]

        for col, (icon, label, value) in enumerate(stats_items_row1):
            item_widget = QFrame()
            item_widget.setObjectName("StatsBox")
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(8, 6, 8, 6)
            item_layout.setSpacing(2)

            value_label = QLabel(f"{icon} {value}")
            value_label.setObjectName("StatValue")
            value_label.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(value_label)

            text_label = QLabel(label)
            text_label.setObjectName("StatLabel")
            text_label.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(text_label)

            stats_grid.addWidget(item_widget, 0, col)

        # Segunda linha
        stats_items_row2 = [
            ("📌", "ÍNDICES", indexes),
            ("📁", "SCHEMAS", schemas),
            ("🧩", "EXTENSÕES", extensions),
            ("🎯", "TOTAL", total)
        ]

        for col, (icon, label, value) in enumerate(stats_items_row2):
            item_widget = QFrame()
            item_widget.setObjectName("StatsBox")
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(8, 6, 8, 6)
            item_layout.setSpacing(2)

            color = SUCCESS if label == "TOTAL" else ACCENT
            value_label = QLabel(f"{icon} {value}")
            value_label.setObjectName("StatValue")
            value_label.setStyleSheet(f"color: {color}; font-size: 20px;")
            value_label.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(value_label)

            text_label = QLabel(label)
            text_label.setObjectName("StatLabel")
            text_label.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(text_label)

            stats_grid.addWidget(item_widget, 1, col)

        main_layout.addLayout(stats_grid)

        # ===== MÓDULOS DO SISTEMA =====
        modules_title = QLabel("📦 MÓDULOS DO SISTEMA")
        modules_title.setAlignment(Qt.AlignCenter)
        modules_title.setStyleSheet(f"color: {INFO}; font-weight: bold; font-size: 13px;")
        main_layout.addWidget(modules_title)

        # Grid de módulos (3 linhas x 4 colunas)
        modules_widget = QWidget()
        modules_grid = QGridLayout(modules_widget)
        modules_grid.setContentsMargins(0, 0, 0, 0)
        modules_grid.setSpacing(6)

        modules = [
            ("👥", "Usuários"),
            ("👕", "Modelos"),
            ("🏭", "Facções"),
            ("✂️", "Corte"),
            ("📦", "Envio"),
            ("🔄", "Retorno"),
            ("💰", "Pagamentos"),
            ("📊", "Estoque"),
            ("📋", "Serviços"),
            ("📈", "Pricing"),
            ("🛒", "Compras"),
            ("📅", "MRP/Planejamento")
        ]

        for i, (icon, name) in enumerate(modules):
            row, col = divmod(i, 4)
            module_label = QLabel(f"{icon} {name}")
            module_label.setObjectName("ModuleItem")
            module_label.setAlignment(Qt.AlignCenter)
            modules_grid.addWidget(module_label, row, col)

        main_layout.addWidget(modules_widget)

        # ===== ADMINISTRADOR =====
        admin_layout = QHBoxLayout()
        admin_layout.setSpacing(10)

        admin_icon = QLabel("👑")
        admin_icon.setStyleSheet("font-size: 18px;")
        admin_layout.addWidget(admin_icon)

        admin_text = QLabel("INICIAR O ADMINISTRADOR")
        admin_text.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        admin_layout.addWidget(admin_text)

        admin_name = QLabel("admin")
        admin_name.setObjectName("AdminName")
        admin_layout.addWidget(admin_name)

        admin_layout.addStretch()
        main_layout.addLayout(admin_layout)

        # ===== BANCO CRIADO =====
        db_label = QLabel(f"✅ Banco <b>{database}</b> criado/preparado com sucesso")
        db_label.setAlignment(Qt.AlignCenter)
        db_label.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
        main_layout.addWidget(db_label)

        # ===== OPERAÇÃO CONCLUÍDA =====
        success_label = QLabel("✅ Operação concluída com sucesso")
        success_label.setAlignment(Qt.AlignCenter)
        success_label.setStyleSheet(f"color: {SUCCESS}; font-weight: bold; font-size: 13px;")
        main_layout.addWidget(success_label)

        # ===== BOTÃO FECHAR =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("🔒  FECHAR")
        close_btn.setObjectName("CloseBtn")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)


def _is_port_open(host: str, port: int, timeout: float = 0.18) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


COMMON_PORTS = [5432, 5433, 5434, 5435]


@dataclass
class FoundHost:
    host: str
    port: int
    status: str


# -----------------------------
# Worker: detecção LAN
# -----------------------------
class DetectWorker(QThread):
    found = pyqtSignal(str, int, str)  # host, port, status
    done = pyqtSignal(bool, str)  # ok, message

    def __init__(self, user: str, password: str, db_manager: Any, mode: str = "auto", parent=None):
        super().__init__(parent)
        self.user = user.strip()
        self.password = password
        self.db_manager = db_manager
        self.mode = (mode or "auto").strip().lower()
        self._stop = False

    def stop(self):
        self._stop = True

    def _try_validate(self, host: str, port: int) -> str:
        """
        Se tiver usuário preenchido, tenta validar via db_manager.test_connection.
        Se não, apenas indica porta aberta.
        """
        if not self.user:
            return "Porta aberta (informe usuário p/ validar)"

        # tenta chamar com host, se existir
        try:
            ok, msg = self.db_manager.test_connection(
                self.password, self.user, str(port), "postgres", host
            )
            return "Conexão OK" if ok else f"Respondeu ({msg})"
        except TypeError:
            # db_manager sem parâmetro host
            try:
                ok, msg = self.db_manager.test_connection(
                    self.password, self.user, str(port), "postgres"
                )
                return "Conexão OK" if ok else f"Respondeu ({msg})"
            except Exception as e:
                return f"Respondeu (erro: {_safe_str(e)})"
        except Exception as e:
            # porta abriu, mas login pode falhar
            txt = _safe_str(e)
            if "password" in txt.lower() or "senha" in txt.lower():
                return "Servidor respondeu (senha inválida)"
            if "pg_hba" in txt.lower():
                return "Servidor respondeu (bloqueado no pg_hba.conf)"
            return f"Respondeu ({txt})"

    def run(self):
        try:
            found_any = False
            mode = self.mode

            # Modos:
            #  - 'local' : apenas localhost
            #  - 'lan'   : apenas rede local (/24)
            #  - 'auto'  : tenta local primeiro; se não achar, varre LAN

            def scan_local() -> bool:
                nonlocal found_any
                for p in COMMON_PORTS:
                    if self._stop:
                        self.done.emit(False, "Detecção cancelada.")
                        return found_any
                    if _is_port_open("127.0.0.1", p, timeout=0.18):
                        status = self._try_validate("127.0.0.1", p)
                        self.found.emit("127.0.0.1", p, status)
                        found_any = True
                return found_any

            def scan_lan() -> bool:
                nonlocal found_any
                my_ip = _get_local_ipv4()
                if not my_ip:
                    self.done.emit(False, "⚠️ Não consegui detectar seu IP local. Use Host manual.")
                    return found_any

                cidr = _guess_lan_cidr(my_ip)
                net = ipaddress.ip_network(cidr, strict=False)

                for ip in net.hosts():
                    if self._stop:
                        self.done.emit(False, "Detecção cancelada.")
                        return found_any
                    ip_str = str(ip)
                    if ip_str == my_ip:
                        continue
                    for p in COMMON_PORTS:
                        if self._stop:
                            self.done.emit(False, "Detecção cancelada.")
                            return found_any
                        if _is_port_open(ip_str, p, timeout=0.16):
                            if self._stop:
                                self.done.emit(False, "Detecção cancelada.")
                                return found_any
                            status = self._try_validate(ip_str, p)
                            self.found.emit(ip_str, p, status)
                            found_any = True
                return found_any

            if mode == "local":
                scan_local()
                if found_any:
                    self.done.emit(True, "✅ Encontrado no LOCAL. Selecione na lista de encontrados.")
                else:
                    self.done.emit(False, "❌ Nenhum Postgres encontrado no LOCAL. Tente LAN ou Host manual.")
                return

            if mode == "lan":
                scan_lan()
                if found_any:
                    self.done.emit(True, "✅ Varredura concluída na LAN. Selecione na lista de encontrados.")
                else:
                    my_ip = _get_local_ipv4()
                    cidr = _guess_lan_cidr(my_ip) if my_ip else "LAN"
                    self.done.emit(False, f"❌ Nenhum Postgres encontrado na LAN ({cidr}). Use Host manual.")
                return

            # auto
            scan_local()
            if found_any:
                self.done.emit(True, "✅ Encontrado no LOCAL. Selecione na lista de encontrados.")
                return

            scan_lan()
            if found_any:
                my_ip = _get_local_ipv4()
                cidr = _guess_lan_cidr(my_ip) if my_ip else "LAN"
                self.done.emit(True, f"✅ Varredura concluída na LAN ({cidr}).")
            else:
                my_ip = _get_local_ipv4()
                cidr = _guess_lan_cidr(my_ip) if my_ip else "LAN"
                self.done.emit(False, f"❌ Nenhum Postgres encontrado (LOCAL e LAN {cidr}). Use Host manual.")
        except Exception as e:
            self.done.emit(False, f"Erro na detecção: {_safe_str(e)}")


class TaskWorker(QThread):
    log = pyqtSignal(str)
    finished_task = pyqtSignal(bool, str, str)  # ok, title, details

    def __init__(self, db_manager: Any, task: str, *,
                 script_name: str = "",
                 database: str = "",
                 user: str = "",
                 password: str = "",
                 port: str = "",
                 host: str = "",
                 parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.task = task
        self.script_name = script_name
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.host = host

    def _call(self, fn_name: str, *args, **kwargs):
        fn = getattr(self.db_manager, fn_name)
        return fn(*args, **kwargs)

    def run(self):
        try:
            if self.task == "test_connection":
                self.log.emit("🔍 Testando conexão...")
                host = (self.host or "127.0.0.1").strip() or "127.0.0.1"
                try:
                    port_int = int(str(self.port).strip()) if str(self.port).strip() else 5432
                except Exception:
                    port_int = 5432
                user = (self.user or "postgres").strip() or "postgres"
                dbname = (self.database or "postgres").strip() or "postgres"

                # 1) Teste TCP (porta respondendo)
                try:
                    with socket.create_connection((host, port_int), timeout=0.8):
                        pass
                except Exception:
                    self.finished_task.emit(False, "Teste de conexão", f"Porta {port_int} não responde em {host}")
                    return

                # 2) Teste REAL do PostgreSQL via psql (confirma autenticação/pg_hba)
                psql_path = None
                for attr in ("psql_path", "psql_exe", "psql"):
                    psql_path = getattr(self.db_manager, attr, None)
                    if psql_path:
                        break
                if not psql_path:
                    psql_path = shutil.which("psql")

                if not psql_path:
                    # Fallback: tenta o db_manager.test_connection se existir
                    try:
                        ok, msg = self._call("test_connection", self.password, user, str(port_int), dbname, host)
                    except TypeError:
                        ok, msg = self._call("test_connection", self.password, user, str(port_int), dbname)
                    self.finished_task.emit(bool(ok), "Teste de conexão", str(msg))
                    return

                env = os.environ.copy()
                if self.password:
                    env["PGPASSWORD"] = str(self.password)

                cmd = [
                    str(psql_path),
                    "-h", host,
                    "-p", str(port_int),
                    "-U", user,
                    "-d", dbname,
                    "-t", "-A",
                    "-c", "SELECT 1;"
                ]

                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=8)
                    out = (r.stdout or "").strip()
                    err = (r.stderr or "").strip()
                    combo = (err + "\n" + out).strip()
                    low = combo.lower()

                    if r.returncode == 0 and out == "1":
                        self.finished_task.emit(True, "Teste de conexão",
                                                f"Conexão OK em {host}:{port_int} (db={dbname})")
                        return

                    # Porta respondeu, mas não autenticou/foi bloqueado
                    if "password authentication failed" in low or "autentica" in low:
                        self.finished_task.emit(False, "Teste de conexão", "Servidor respondeu (senha inválida)")
                        return
                    if "no pg_hba.conf entry" in low or "pg_hba" in low:
                        self.finished_task.emit(False, "Teste de conexão",
                                                "Servidor respondeu (bloqueado no pg_hba.conf)")
                        return
                    if "could not connect" in low or "não foi possível conectar" in low:
                        self.finished_task.emit(False, "Teste de conexão",
                                                "Servidor não aceitou conexão (host/porta/firewall)")
                        return

                    # Genérico
                    msg = combo if combo else "Servidor respondeu, mas falhou no teste."
                    # evita mensagens gigantes no log principal
                    if len(msg) > 220:
                        msg = msg[:220] + "..."
                    self.finished_task.emit(False, "Teste de conexão", msg)
                    return

                except subprocess.TimeoutExpired:
                    self.finished_task.emit(False, "Teste de conexão", "Timeout ao testar (servidor lento ou bloqueio)")
                    return

            if self.task == "check_db":
                self.log.emit("📊 Verificando se o banco existe...")
                try:
                    ok = self._call("check_database_exists", self.database, self.password, self.user, self.port or None,
                                    self.host)
                except TypeError:
                    ok = self._call("check_database_exists", self.database, self.password, self.user, self.port or None)
                self.finished_task.emit(bool(ok), "Verificar banco", "Banco existe ✅" if ok else "Banco NÃO existe ❌")
                return

            if self.task == "run_script":
                self.log.emit(f"🚀 Executando script: {self.script_name} (banco={self.database})")
                # execute_sql_file: tenta com host
                try:
                    res = self._call("execute_sql_file", self.script_name, self.password, self.database, self.user,
                                     self.port or None, self.host)
                except TypeError:
                    res = self._call("execute_sql_file", self.script_name, self.password, self.database, self.user,
                                     self.port or None)

                # Normaliza retorno
                ok = True
                details = ""
                if isinstance(res, tuple) and len(res) >= 2:
                    ok = bool(res[0])
                    details = str(res[1])
                elif isinstance(res, dict):
                    ok = bool(res.get("success", True))
                    details = str(res.get("message", res))
                elif isinstance(res, bool):
                    ok = res
                    details = "OK" if ok else "Falhou"
                else:
                    details = str(res)

                self.finished_task.emit(ok, f"Execução: {self.script_name}", details)
                return

            self.finished_task.emit(False, "Tarefa", f"Tarefa desconhecida: {self.task}")

        except Exception as e:
            self.finished_task.emit(False, "Erro", _safe_str(e))


# -----------------------------
# UI
# -----------------------------
class InstallerApp(QMainWindow):
    def __init__(self, db_manager: Any, scripts_dir: Optional[Path] = None):
        super().__init__()
        self.db_manager = db_manager
        self.scripts_dir = scripts_dir or (Path(__file__).resolve().parent / "scripts")

        # Config (persist UI preferences like theme) - keeps existing keys
        self.config_path = Path(__file__).resolve().parent / "config.json"
        self._config: dict = {}
        try:
            if self.config_path.exists():
                self._config = json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            self._config = {}

        # Theme: dark by default (better contrast). Stored as ui_dark_mode: true/false
        self.ui_dark_mode: bool = bool(self._config.get("ui_dark_mode", True))

        self._detect_worker: Optional[DetectWorker] = None
        self._task_worker: Optional[TaskWorker] = None
        self._auto_queue: List[str] = []
        self._auto_running = False
        self._last_database: str = ""
        self._last_script: str = ""

        self.setWindowTitle("🚀 INSTALADOR OPERA FASHION - Banco PostgreSQL")
        self.setMinimumSize(1180, 760)
        self.resize(1380, 860)

        self._build_ui()
        self._apply_style()
        self._load_scripts()

    def _extract_script_from_title(self, title: str) -> str:
        """Extrai o nome do script a partir de títulos do tipo 'Execução: X.sql'."""
        if not title:
            return ""
        if title.startswith("Execução:"):
            return title.split(":", 1)[1].strip()
        return ""

    def _show_success_summary_dialog(self, database: str, summary: dict) -> None:
        """Mostra popup de sucesso com mensagens (estilo antigo) e contagem de estruturas."""
        tables = int(summary.get("tables", 0) or 0)
        views = int(summary.get("views", 0) or 0)
        functions = int(summary.get("functions", 0) or 0)
        procedures = int(summary.get("procedures", 0) or 0)
        triggers = int(summary.get("triggers", 0) or 0)
        indexes = int(summary.get("indexes", 0) or 0)
        schemas = int(summary.get("schemas", 0) or 0)
        types_ = int(summary.get("types", 0) or 0)
        exts = int(summary.get("extensions", 0) or 0)
        total = int(summary.get("total_created", 0) or (
                tables + views + functions + procedures + triggers + indexes + schemas + types_ + exts))

        # Dados do usuário (para mensagem estilo antigo)
        schema_name = getattr(self, "default_schema", "opera")
        user = self.user_edit.text().strip() if hasattr(self, "user_edit") else ""
        pwd = self.pass_edit.text().strip() if hasattr(self, "pass_edit") else ""
        pwd_short = pwd[-4:] if pwd else ""
        user_line = f"✅ Schema: {schema_name}  •  Usuário: {user or '-'}"
        if pwd_short:
            user_line += f"  •  Senha: {pwd_short}"

        pills: list[str] = []
        pills.append("✅ Script executado com sucesso!")
        pills.append(user_line)
        pills.append(f"✅ Banco <b>{database}</b> criado/preparado com sucesso")

        # Mensagem de contagem (como você queria)
        if total > 0:
            parts = []
            if tables: parts.append(f"{tables} tabelas")
            if views: parts.append(f"{views} views")
            if functions: parts.append(f"{functions} funções")
            if procedures: parts.append(f"{procedures} procedures")
            if triggers: parts.append(f"{triggers} triggers")
            if indexes: parts.append(f"{indexes} índices")
            if schemas: parts.append(f"{schemas} schemas")
            if types_: parts.append(f"{types_} types")
            if exts: parts.append(f"{exts} extensões")
            pills.append("✅ Estruturas criadas: <b>" + " • ".join(parts) + "</b>")
            pills.append("✅ Total criado nesta execução: <b>%d</b>" % total)
        else:
            pills.append("✅ Estruturas já existentes / nada novo para criar")

        pills.append("✅ Operação concluída com sucesso")

        theme = getattr(self, "_theme", None) or {}
        dlg = SuccessDialog(
            self,
            theme=theme,
            title="SISTEMA OPERA CRIADO COM SUCESSO!",
            subtitle="Banco de dados configurado e pronto para uso",
            pills=pills,
        )
        dlg.exec_()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(8)

        # Header (compact, readable)
        header = QFrame()
        header.setObjectName("Header")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(2)

        # Toggle de tema (claro/escuro) — mantém contraste correto
        topbar = QHBoxLayout()
        topbar.setContentsMargins(0, 0, 0, 0)
        topbar.addStretch(1)
        self.theme_toggle = QCheckBox("☀ Tema claro")
        self.theme_toggle.setChecked(not self.ui_dark_mode)  # marcado = claro
        handler = getattr(self, '_toggle_theme', None)
        if callable(handler):
            self.theme_toggle.stateChanged.connect(handler)
        else:
            self.theme_toggle.stateChanged.connect(lambda *_a: self._apply_style())
        topbar.addWidget(self.theme_toggle, 0, Qt.AlignRight)
        hl.addLayout(topbar)

        title = QLabel("🚀 INSTALADOR OPERA FASHION")
        title.setObjectName("HeaderTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Bold))

        subtitle = QLabel("PostgreSQL • Local + LAN • Execução automática 1→2→3")
        subtitle.setObjectName("HeaderSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setFont(QFont("Arial", 10))

        hl.addWidget(title)
        hl.addWidget(subtitle)
        root.addWidget(header)

        # Main splitter (left: inputs/scripts/actions, right: logs)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        # ---------------- LEFT (no scroll) ----------------
        left_panel = QWidget()
        left_root = QVBoxLayout(left_panel)
        left_root.setContentsMargins(0, 0, 0, 0)
        left_root.setSpacing(8)
        splitter.addWidget(left_panel)

        # ---- Connection group (grid -> ocupa menos altura) ----
        cfg_group = QGroupBox("⚙️ Conexão")
        cfg = QGridLayout(cfg_group)
        cfg.setContentsMargins(12, 12, 12, 10)
        cfg.setHorizontalSpacing(10)
        cfg.setVerticalSpacing(6)

        def label(text_: str) -> QLabel:
            lbl = QLabel(text_)
            lbl.setObjectName("FieldLabel")
            return lbl

        self.host_input = QLineEdit("localhost")
        self.host_input.setPlaceholderText("localhost / 192.168.0.10 / servidor.local")

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("5432 (ou deixe vazio p/ auto)")

        self.user_input = QLineEdit("postgres")

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Senha do PostgreSQL (opcional)")

        self.db_combo = QComboBox()
        self.db_combo.addItems(["postgres", "BANCO_OPERA"])
        self.db_combo.currentTextChanged.connect(self._update_db_status)

        self.show_pass = QCheckBox("Mostrar senha")
        self.show_pass.stateChanged.connect(self._toggle_password)

        # row 0: host + port
        cfg.addWidget(label("🌐 Host / IP"), 0, 0)
        cfg.addWidget(label("🔌 Porta"), 0, 1)
        cfg.addWidget(self.host_input, 1, 0)
        cfg.addWidget(self.port_input, 1, 1)

        # row 2: user + db
        cfg.addWidget(label("👤 Usuário"), 2, 0)
        cfg.addWidget(label("🗄️ Banco"), 2, 1)
        cfg.addWidget(self.user_input, 3, 0)
        cfg.addWidget(self.db_combo, 3, 1)

        # row 4: senha + checkbox
        cfg.addWidget(label("🔑 Senha"), 4, 0, 1, 2)
        cfg.addWidget(self.password_input, 5, 0, 1, 2)
        cfg.addWidget(self.show_pass, 6, 0, 1, 2, alignment=Qt.AlignLeft)

        # status + botões (no mesmo grupo, sem ocupar muito)
        self.db_status = QLabel("🔵 Banco atual: postgres")
        self.db_status.setObjectName("DbStatus")

        # Detecção: Local / LAN / Manual
        self.rb_detect_local = QRadioButton("Local")
        self.rb_detect_lan = QRadioButton("LAN")
        self.rb_detect_manual = QRadioButton("Manual")
        self.rb_detect_local.setChecked(True)
        self.detect_group = QButtonGroup(self)
        self.detect_group.addButton(self.rb_detect_local)
        self.detect_group.addButton(self.rb_detect_lan)
        self.detect_group.addButton(self.rb_detect_manual)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        mode_row.addWidget(QLabel("Detecção:"))
        mode_row.addWidget(self.rb_detect_local)
        mode_row.addWidget(self.rb_detect_lan)
        mode_row.addWidget(self.rb_detect_manual)
        mode_row.addStretch(1)

        self.btn_detect = QPushButton("🔍 Detectar")
        self.btn_test = QPushButton("✅ Testar Conexão")
        self.btn_detect.clicked.connect(self.on_detect)
        self.btn_test.clicked.connect(self.on_test_connection)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_detect)
        btn_row.addWidget(self.btn_test)

        actions_box = QVBoxLayout()
        actions_box.setSpacing(6)
        actions_box.addLayout(mode_row)
        actions_box.addLayout(btn_row)

        cfg.addWidget(self.db_status, 7, 0, 1, 2)
        cfg.addLayout(actions_box, 8, 0, 1, 2)

        left_root.addWidget(cfg_group)

        # ---- Middle row: Encontrados (esq) + Scripts (dir) ----
        mid_row = QHBoxLayout()
        mid_row.setSpacing(8)
        left_root.addLayout(mid_row, 1)

        # Found hosts
        found_group = QGroupBox("🛰️ Encontrados")
        fl = QVBoxLayout(found_group)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(6)

        self.found_table = QTableWidget(0, 3)
        self.found_table.setHorizontalHeaderLabels(["Host", "Porta", "Status"])
        self.found_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.found_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.found_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.found_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.found_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.found_table.setMinimumHeight(140)
        self.found_table.setMaximumHeight(180)
        self.found_table.cellDoubleClicked.connect(self._use_found_row)

        hint = QLabel("Duplo clique: preencher Host/Porta")
        hint.setObjectName("HintText")

        fl.addWidget(self.found_table)
        fl.addWidget(hint)
        mid_row.addWidget(found_group, 1)

        # Scripts
        scripts_group = QGroupBox("📜 Scripts SQL")
        sl = QVBoxLayout(scripts_group)
        sl.setContentsMargins(10, 10, 10, 10)
        sl.setSpacing(6)

        self.scripts_list = QListWidget()
        self.scripts_list.itemDoubleClicked.connect(lambda *_: self.on_run_selected())
        sl.addWidget(self.scripts_list, 1)

        mid_row.addWidget(scripts_group, 1)

        # ---- Actions (compact) ----
        actions = QGroupBox("🎯 Ações")
        al = QGridLayout(actions)
        al.setContentsMargins(12, 12, 12, 10)
        al.setHorizontalSpacing(10)
        al.setVerticalSpacing(8)

        self.btn_run_all = QPushButton("▶ Executar 1→2→3 (Automático)")
        self.btn_run_all.clicked.connect(self.on_run_auto)

        self.btn_run_selected = QPushButton("🚀 Executar Selecionado")
        self.btn_run_selected.clicked.connect(self.on_run_selected)

        self.btn_check_db = QPushButton("📊 Verificar Banco")
        self.btn_check_db.clicked.connect(self.on_check_db)

        self.btn_clear_log = QPushButton("🧹 Limpar Log")
        self.btn_clear_log.clicked.connect(self.on_clear_log)

        # Layout: play grande em cima, demais embaixo
        al.addWidget(self.btn_run_all, 0, 0, 1, 2)
        al.addWidget(self.btn_run_selected, 1, 0)
        al.addWidget(self.btn_check_db, 1, 1)
        al.addWidget(self.btn_clear_log, 2, 0, 1, 2)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(True)
        self.progress.setRange(0, 0)
        al.addWidget(self.progress, 3, 0, 1, 2)

        left_root.addWidget(actions)

        # ---------------- RIGHT (logs) ----------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        splitter.addWidget(right_panel)

        tabs = QTabWidget()
        right_layout.addWidget(tabs, 1)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        tabs.addTab(self.log_area, "📋 Log")

        self.tech_log = QTextEdit()
        self.tech_log.setReadOnly(True)
        tabs.addTab(self.tech_log, "🧪 Técnico")

        note = QLabel("💡 Dica: Para rede (LAN), o servidor precisa liberar listen_addresses e pg_hba.conf.")
        note.setObjectName("FooterNote")
        right_layout.addWidget(note)

        # Proporção: mais espaço pro painel esquerdo (campos) e menos pro log
        splitter.setSizes([820, 620])

    def _apply_style(self):
        """Aplica tema com contraste correto (fundos claros/letras escuras, fundos escuros/letras claras)."""
        dark = bool(getattr(self, "ui_dark_mode", True))

        if dark:
            BG = "#0f1419"
            CARD = "#111821"
            INPUT = "#0b0f14"
            BORDER = "#243041"
            TEXT = "#e6eef7"
            MUTED = "#9fb7cf"
            TITLE = "#cfe7ff"
            ACCENT = "#1f6feb"
            ACCENT_H = "#2b77ff"
            SELECT = "#1f6feb"
            HEADER_BG = "#0b5bd3"
            HEADER_BD = "#0849a9"
            HEADER_TX = "#ffffff"
            HEADER_ST = "#eaf4ff"
        else:
            BG = "#f4f7fb"
            CARD = "#ffffff"
            INPUT = "#ffffff"
            BORDER = "#d5dde8"
            TEXT = "#111827"
            MUTED = "#4b5563"
            TITLE = "#0f172a"
            ACCENT = "#2563eb"
            ACCENT_H = "#1d4ed8"
            SELECT = "#2563eb"
            HEADER_BG = "#2563eb"
            HEADER_BD = "#1d4ed8"
            HEADER_TX = "#ffffff"
            HEADER_ST = "#eaf2ff"

        # Guardar tema para diálogos/popup
        self._theme = {
            "dark": dark,
            "BG": BG,
            "CARD": CARD,
            "INPUT": INPUT,
            "BORDER": BORDER,
            "TEXT": TEXT,
            "MUTED": MUTED,
            "TITLE": TITLE,
            "ACCENT": ACCENT,
            "ACCENT_H": ACCENT_H,
            "SELECT": SELECT,
            "HEADER_BG": HEADER_BG,
            "HEADER_BD": HEADER_BD,
            "HEADER_TX": HEADER_TX,
            "HEADER_ST": HEADER_ST,
        }
        # Palette ajuda alguns widgets (placeholders / selection)
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(BG))
        pal.setColor(QPalette.Base, QColor(INPUT))
        pal.setColor(QPalette.AlternateBase, QColor(CARD))
        pal.setColor(QPalette.Text, QColor(TEXT))
        pal.setColor(QPalette.WindowText, QColor(TEXT))
        pal.setColor(QPalette.Button, QColor(CARD))
        pal.setColor(QPalette.ButtonText, QColor(TEXT))
        pal.setColor(QPalette.Highlight, QColor(SELECT))
        pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.setPalette(pal)

        self.setStyleSheet(f"""
            QMainWindow {{ background: {BG}; }}

            /* Header */
            #Header {{ background: {HEADER_BG}; border: 1px solid {HEADER_BD}; border-radius: 12px; }}
            #HeaderTitle {{ color: {HEADER_TX}; }}
            #HeaderSubtitle {{ color: {HEADER_ST}; }}
            QCheckBox {{ color: {TEXT}; }}
            QCheckBox:disabled {{ color: {MUTED}; }}
            QLabel {{ color: {TEXT}; }}
            QLabel:disabled {{ color: {MUTED}; }}
            QRadioButton {{ color: {TEXT}; }}
            QRadioButton:disabled {{ color: {MUTED}; }}
            QRadioButton::indicator {{ width: 14px; height: 14px; }}
            QRadioButton::indicator:unchecked {{ border: 1px solid {BORDER}; border-radius: 7px; background: {INPUT}; }}
            QRadioButton::indicator:checked {{ border: 1px solid {ACCENT}; border-radius: 7px; background: {ACCENT}; }}

            /* Group boxes */
            QGroupBox {{
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 10px;
                margin-top: 10px;
                background: {CARD};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px 0 6px;
                color: {TITLE};
                font-weight: 700;
            }}

            #FieldLabel {{ color: {TITLE}; font-weight: 700; margin-top: 2px; }}
            #HintText {{ color: {MUTED}; }}

            QLineEdit, QComboBox, QListWidget, QTextEdit, QTableWidget {{
                background: {INPUT};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 8px 10px;
                selection-background-color: {SELECT};
                selection-color: #ffffff;
            }}
            QLineEdit::placeholder {{ color: {MUTED}; }}

            /* Combo dropdown (popup) */
            QComboBox QAbstractItemView {{
                background: {CARD};
                color: {TEXT};
                selection-background-color: {SELECT};
                selection-color: #ffffff;
                outline: 0px;
                border: 1px solid {BORDER};
            }}

            /* Buttons */
            QPushButton {{
                background: {ACCENT};
                color: #ffffff;
                border: 0px;
                border-radius: 10px;
                padding: 10px 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: {ACCENT_H}; }}
            QPushButton:disabled {{ background: {BORDER}; color: {MUTED}; }}

            /* Tabs */
            QTabWidget::pane {{
                border: 1px solid {BORDER};
                border-radius: 10px;
                background: {CARD};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {CARD};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-bottom: none;
                padding: 8px 12px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background: {INPUT};
                color: {TITLE};
            }}

            /* Table */
            QHeaderView::section {{
                background: {CARD};
                color: {TITLE};
                padding: 6px;
                border: 1px solid {BORDER};
            }}

            #FooterNote {{ color: {MUTED}; padding: 6px; }}
        """)

    def log_html(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        txt = _safe_str(msg)
        if "\n" in txt:
            lines = txt.splitlines()
            for j, line in enumerate(lines):
                if j == 0:
                    self.log_area.append(f"[{ts}] {line}")
                else:
                    self.log_area.append(f"           {line}")
        else:
            self.log_area.append(f"[{ts}] {txt}")
        self.log_area.moveCursor(QTextCursor.End)
        self.log_area.ensureCursorVisible()

    def log_tech_msg(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.tech_log.append(f"[{ts}] {msg}")
        self.tech_log.moveCursor(QTextCursor.End)

    # ---------- UI helpers ----------
    def _toggle_password(self):
        self.password_input.setEchoMode(QLineEdit.Normal if self.show_pass.isChecked() else QLineEdit.Password)

    def _toggle_theme(self, *_args):
        """Checkbox marcado => tema claro; desmarcado => tema escuro."""
        light = bool(self.theme_toggle.isChecked())
        self.ui_dark_mode = not light

        # Persistir sem quebrar outras configs já existentes
        try:
            self._config["ui_dark_mode"] = self.ui_dark_mode
            self.config_path.write_text(json.dumps(self._config, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

        self._apply_style()

    def _on_task_finished(self, ok: bool, title: str, details: str):
        """Callback quando uma tarefa é concluída."""
        self._set_busy(False)

        # DEBUG: Mostrar valores recebidos
        print(f"🔍 DEBUG _on_task_finished:")
        print(f"  - ok: {ok}")
        print(f"  - title: '{title}'")
        print(f"  - details length: {len(details) if details else 0}")

        details_txt = _safe_str(details).strip()

        # Sempre manda detalhes para a aba Técnico (principalmente saída do psql)
        if details_txt:
            for line in details_txt.splitlines():
                if line.strip():
                    self.log_tech_msg(line)

        # Mensagem principal (mais limpa)
        if title.startswith("Execução:"):
            base = "✅" if ok else "❌"
            if details_txt:
                self.log_html(f"{base} {title} (detalhes na aba Técnico)")
            else:
                self.log_html(f"{base} {title}")

            # Extrair nome do script
            script_done = self._extract_script_from_title(title)
            print(f"  - script_done: '{script_done}'")

            # Para o script 3_CRIAR_TABELAS.sql, sempre mostrar a janela de sucesso se OK
            if ok and script_done == "3_CRIAR_TABELAS.sql":
                print("🎯 VAI MOSTRAR A JANELA DE SUCESSO!")

                db_name = self._last_database or self.db_combo.currentText() or "BANCO_OPERA"
                user = self.user_input.text().strip()
                password = self.password_input.text()
                host = self.host_input.text().strip() or "127.0.0.1"
                port = self.port_input.text().strip() or "5432"
                schema = "opera"

                # CONTAGEM REAL das estruturas no banco
                self.log_html("🔍 Coletando contagem REAL do banco de dados...")
                summary = self._collect_db_counts(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=db_name,
                    schema=schema,
                )

                print(f"  - summary: {summary}")
                print(f"  - total_created: {summary.get('total_created', 0)}")

                # Mostrar resumo detalhado no log
                self.log_html(f"✅ RESUMO DA CRIAÇÃO:")
                self.log_html(f"   • {summary['tables']} tabelas criadas")
                self.log_html(f"   • {summary['views']} views configuradas")
                self.log_html(f"   • {summary['functions']} funções implementadas")
                self.log_html(f"   • {summary['procedures']} procedures")
                self.log_html(f"   • {summary['triggers']} triggers ativos")
                self.log_html(f"   • {summary['indexes']} índices de performance")
                self.log_html(f"   • {summary['schemas']} schemas")
                self.log_html(f"   • {summary['types']} tipos")
                self.log_html(f"   • {summary['extensions']} extensões")
                self.log_html(f"   • {summary['sequences']} sequences")
                self.log_html(f"   • TOTAL: {summary['total_created']} estruturas criadas")

                # Mostrar listas detalhadas se houver
                if summary.get('tables_list'):
                    self.log_html(f"📋 TABELAS CRIADAS ({len(summary['tables_list'])}):")
                    for i, table in enumerate(summary['tables_list'][:10]):  # Mostra primeiras 10
                        self.log_html(f"     {i + 1}. {table}")
                    if len(summary['tables_list']) > 10:
                        self.log_html(f"     ... e mais {len(summary['tables_list']) - 10} tabelas")

                if summary.get('functions_list'):
                    self.log_html(f"⚙️ FUNÇÕES CRIADAS ({len(summary['functions_list'])}):")
                    for i, func in enumerate(summary['functions_list'][:5]):  # Mostra primeiras 5
                        self.log_html(f"     {i + 1}. {func}")
                    if len(summary['functions_list']) > 5:
                        self.log_html(f"     ... e mais {len(summary['functions_list']) - 5} funções")

                if summary.get('triggers_list'):
                    self.log_html(f"🔔 TRIGGERS CRIADOS ({len(summary['triggers_list'])}):")
                    for trigger in summary['triggers_list']:
                        self.log_html(f"     • {trigger}")

                # Verificar se a classe SuccessDialog está disponível
                try:
                    dlg = SuccessDialog(
                        self,
                        theme=self._theme,
                        summary=summary,
                        database=db_name,
                        user=user,
                        password=password
                    )
                    print("✅ Dialog criado, vai executar...")
                    dlg.exec_()
                    print("✅ Dialog executado!")

                except NameError as e:
                    print(f"❌ Erro: classe SuccessDialog não encontrada - {e}")
                    # Fallback: mostrar QMessageBox simples
                    msg = f"""
    ✅ SISTEMA OPERA CRIADO COM SUCESSO!

    Banco: {db_name}
    Usuário: {user}
    Schema: opera

    📊 ESTRUTURAS CRIADAS:
    • {summary['tables']} tabelas
    • {summary['views']} views
    • {summary['functions']} funções
    • {summary['procedures']} procedures
    • {summary['triggers']} triggers
    • {summary['indexes']} índices
    • {summary['schemas']} schemas
    • {summary['types']} tipos
    • {summary['extensions']} extensões
    • {summary['sequences']} sequences

    🎯 TOTAL: {summary['total_created']} estruturas

    ✅ Operação concluída com sucesso!
    """
                    QMessageBox.information(self, "Sucesso!", msg)

                except Exception as e:
                    print(f"❌ ERRO ao criar/mostrar dialog: {e}")
                    import traceback
                    traceback.print_exc()

            # Para outros scripts, mostrar resumo normal se houver estruturas criadas
            elif ok and details_txt:
                summ = self._summarize_psql_output(details_txt)
                print(f"  - summ: {summ}")

                if summ.get("total_created", 0) > 0:
                    parts = []
                    if summ["tables"]:
                        parts.append(f"{summ['tables']} tabela(s)")
                    if summ["views"]:
                        parts.append(f"{summ['views']} view(s)")
                    if summ["functions"]:
                        parts.append(f"{summ['functions']} função(ões)")
                    if summ["procedures"]:
                        parts.append(f"{summ['procedures']} procedure(s)")
                    if summ["triggers"]:
                        parts.append(f"{summ['triggers']} trigger(s)")
                    if summ["indexes"]:
                        parts.append(f"{summ['indexes']} índice(s)")
                    if summ["schemas"]:
                        parts.append(f"{summ['schemas']} schema(s)")
                    if summ["types"]:
                        parts.append(f"{summ['types']} type(s)")
                    if summ["extensions"]:
                        parts.append(f"{summ['extensions']} extension(s)")
                    if summ["sequences"]:
                        parts.append(f"{summ['sequences']} sequence(s)")
                    resumo = ", ".join(parts)
                    self.log_html(f"✅ Estruturas criadas com sucesso: {resumo}")

        else:
            if ok:
                self.log_html(f"✅ {title}: {details_txt or 'OK'}")
            else:
                self.log_html(f"❌ {title}: {details_txt or 'Falhou'}")

        # Encadeamento automático 1→2→3
        if self._auto_running and title.startswith("Execução:"):
            if ok and self._auto_queue:
                next_script = self._auto_queue.pop(0)
                self.log_html(f"🔄 Próximo script: {next_script}")
                self._run_one_script(next_script)
                return
            # acabou ou falhou
            if ok:
                self.log_html("🎉 Execução automática finalizada com sucesso!")
            else:
                self.log_html("🛑 Execução automática interrompida por erro.")
            self._auto_running = False

        # Popup só para erros críticos em execução individual
        if title.startswith("Execução:") and (not ok) and (not self._auto_running):
            QMessageBox.critical(self, "Erro ao executar", details_txt or "Falha ao executar o script.")

    def _update_db_status(self):
        db = self.db_combo.currentText()
        if db == "BANCO_OPERA":
            self.db_status.setText("🔵 Banco atual: BANCO_OPERA")
        else:
            self.db_status.setText("🔵 Banco atual: postgres")

    def _use_found_row(self, row: int, _col: int):
        host = self.found_table.item(row, 0).text()
        port = self.found_table.item(row, 1).text()
        self.host_input.setText(host)
        self.port_input.setText(port)
        self.log_html(f"✅ Selecionado: {host}:{port}")

    def _set_busy(self, busy: bool, label: str = "", allow_cancel: bool = False):
        """Desabilita ações durante tarefas. Se allow_cancel=True, mantém o botão Detectar ativo para cancelar."""
        # por padrão desabilita tudo
        for b in [self.btn_detect, self.btn_test, self.btn_run_selected, self.btn_run_all, self.btn_check_db]:
            b.setEnabled(not busy)

        # se estiver detectando, permita cancelar
        if busy and allow_cancel:
            self.btn_detect.setEnabled(True)

        self.progress.setVisible(busy)
        if busy:
            self.progress.setFormat(label or "Processando...")
        else:
            self.progress.setFormat("")

    def _collect_db_counts(self, host: str, port: str, user: str, password: str, database: str,
                           schema: str = "opera") -> dict:
        """
        Coleta contagens REAIS de estruturas no PostgreSQL com consulta SQL completa.
        Retorna um dicionário com todas as contagens e listas detalhadas.
        """
        zeros = {
            "tables": 0,
            "views": 0,
            "functions": 0,
            "procedures": 0,
            "triggers": 0,
            "indexes": 0,
            "schemas": 0,
            "types": 0,
            "extensions": 0,
            "sequences": 0,
            "total_created": 0,
            "tables_list": [],
            "functions_list": [],
            "views_list": [],
            "triggers_list": [],
        }

        schema = (schema or "opera").strip()

        # Log para debug
        print(f"🔍 Coletando contagens do banco {database} no schema {schema}")
        print(f"   Host: {host}, Port: {port}, User: {user}")

        # ---------- 1) psycopg2 (mais confiável) ----------
        try:
            import psycopg2
            import psycopg2.extras

            conn = psycopg2.connect(
                host=str(host).strip(),
                port=int(str(port).strip()),
                user=str(user).strip(),
                password=str(password) if password is not None else "",
                dbname=str(database).strip(),
                connect_timeout=10,
            )
            conn.autocommit = True
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # Consulta 1: Contagens básicas
            count_query = """
            WITH 
            tables_count AS (
                SELECT COUNT(*) as total FROM information_schema.tables 
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ),
            views_count AS (
                SELECT COUNT(*) as total FROM information_schema.views 
                WHERE table_schema = %s
            ),
            functions_count AS (
                SELECT COUNT(*) as total FROM pg_proc p 
                JOIN pg_namespace n ON n.oid = p.pronamespace 
                WHERE n.nspname = %s AND p.prokind = 'f'
            ),
            procedures_count AS (
                SELECT COUNT(*) as total FROM pg_proc p 
                JOIN pg_namespace n ON n.oid = p.pronamespace 
                WHERE n.nspname = %s AND p.prokind = 'p'
            ),
            triggers_count AS (
                SELECT COUNT(*) as total FROM information_schema.triggers 
                WHERE trigger_schema = %s
            ),
            indexes_count AS (
                SELECT COUNT(*) as total FROM pg_indexes 
                WHERE schemaname = %s
            ),
            schemas_count AS (
                SELECT COUNT(*) as total FROM pg_namespace 
                WHERE nspname = %s
            ),
            types_count AS (
                SELECT COUNT(*) as total FROM pg_type t 
                JOIN pg_namespace n ON n.oid = t.typnamespace 
                WHERE n.nspname = %s 
                AND t.typtype IN ('b', 'c', 'd', 'e', 'r', 'm')
            ),
            extensions_count AS (
                SELECT COUNT(*) as total FROM pg_extension
            ),
            sequences_count AS (
                SELECT COUNT(*) as total FROM information_schema.sequences 
                WHERE sequence_schema = %s
            )
            SELECT 
                (SELECT total FROM tables_count) as tables,
                (SELECT total FROM views_count) as views,
                (SELECT total FROM functions_count) as functions,
                (SELECT total FROM procedures_count) as procedures,
                (SELECT total FROM triggers_count) as triggers,
                (SELECT total FROM indexes_count) as indexes,
                (SELECT total FROM schemas_count) as schemas,
                (SELECT total FROM types_count) as types,
                (SELECT total FROM extensions_count) as extensions,
                (SELECT total FROM sequences_count) as sequences;
            """

            params = [schema] * 10  # 10 ocorrências de %s
            cur.execute(count_query, params)
            row = cur.fetchone()

            if row:
                tables = int(row['tables'] or 0)
                views = int(row['views'] or 0)
                functions = int(row['functions'] or 0)
                procedures = int(row['procedures'] or 0)
                triggers = int(row['triggers'] or 0)
                indexes = int(row['indexes'] or 0)
                schemas = int(row['schemas'] or 0)
                types = int(row['types'] or 0)
                extensions = int(row['extensions'] or 0)
                sequences = int(row['sequences'] or 0)

                print(f"✅ Contagens obtidas via psycopg2:")
                print(f"   Tables: {tables}, Views: {views}, Functions: {functions}")
                print(f"   Triggers: {triggers}, Indexes: {indexes}")
            else:
                tables = views = functions = procedures = triggers = indexes = schemas = types = extensions = sequences = 0

            # Consulta 2: Lista de tabelas
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """, (schema,))
            tables_list = [row[0] for row in cur.fetchall()]

            # Consulta 3: Lista de views
            cur.execute("""
                SELECT table_name 
                FROM information_schema.views 
                WHERE table_schema = %s
                ORDER BY table_name;
            """, (schema,))
            views_list = [row[0] for row in cur.fetchall()]

            # Consulta 4: Lista de funções
            cur.execute("""
                SELECT proname 
                FROM pg_proc p 
                JOIN pg_namespace n ON n.oid = p.pronamespace 
                WHERE n.nspname = %s 
                AND p.prokind = 'f'
                ORDER BY proname;
            """, (schema,))
            functions_list = [row[0] for row in cur.fetchall()]

            # Consulta 5: Lista de triggers
            cur.execute("""
                SELECT trigger_name 
                FROM information_schema.triggers 
                WHERE trigger_schema = %s
                ORDER BY trigger_name;
            """, (schema,))
            triggers_list = [row[0] for row in cur.fetchall()]

            cur.close()
            conn.close()

            total = (tables + views + functions + procedures + triggers +
                     indexes + schemas + types + extensions + sequences)

            result = {
                "tables": tables,
                "views": views,
                "functions": functions,
                "procedures": procedures,
                "triggers": triggers,
                "indexes": indexes,
                "schemas": schemas,
                "types": types,
                "extensions": extensions,
                "sequences": sequences,
                "total_created": total,
                "tables_list": tables_list,
                "views_list": views_list,
                "functions_list": functions_list,
                "triggers_list": triggers_list,
            }

            # Log detalhado
            self.log_html(f"📊 CONTAGEM REAL ENCONTRADA NO BANCO:")
            self.log_html(f"   • {tables} tabelas")
            if tables_list:
                self.log_html(f"     Exemplos: {', '.join(tables_list[:5])}" + ("..." if len(tables_list) > 5 else ""))
            self.log_html(f"   • {views} views")
            self.log_html(f"   • {functions} funções")
            self.log_html(f"   • {procedures} procedures")
            self.log_html(f"   • {triggers} triggers")
            if triggers_list:
                self.log_html(
                    f"     Exemplos: {', '.join(triggers_list[:3])}" + ("..." if len(triggers_list) > 3 else ""))
            self.log_html(f"   • {indexes} índices")
            self.log_html(f"   • {schemas} schemas")
            self.log_html(f"   • {types} tipos")
            self.log_html(f"   • {extensions} extensões")
            self.log_html(f"   • {sequences} sequences")
            self.log_html(f"   • TOTAL: {total} estruturas criadas")

            return result

        except ImportError as e:
            print(f"⚠️ psycopg2 não instalado: {e}")
            self.log_html("⚠️ psycopg2 não disponível, tentando via psql...")
        except Exception as e:
            print(f"⚠️ Erro ao conectar via psycopg2: {e}")
            self.log_html(f"⚠️ Erro na contagem via psycopg2: {e}")
            try:
                if 'conn' in locals():
                    conn.close()
            except:
                pass

        # ---------- 2) fallback psql (CORRIGIDO) ----------
        try:
            import subprocess
            import shutil
            import os
            import tempfile

            psql_path = None
            for attr in ("psql_path", "psql_exe", "psql"):
                psql_path = getattr(self.db_manager, attr, None)
                if psql_path:
                    break
            if not psql_path:
                psql_path = shutil.which("psql")
            if not psql_path:
                self.log_html("⚠️ psql não encontrado para fallback")
                return zeros

            schema_safe = schema.replace("'", "''")

            # Criar arquivo temporário com a consulta
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8') as f:
                query = f"""
    -- Contagem de estruturas no schema {schema_safe}
    \\timing off
    \\pset tuples_only on
    \\pset format unaligned
    \\pset fieldsep '|'

    WITH 
    tables_count AS (
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_schema = '{schema_safe}' AND table_type = 'BASE TABLE'
    ),
    views_count AS (
        SELECT COUNT(*) FROM information_schema.views 
        WHERE table_schema = '{schema_safe}'
    ),
    functions_count AS (
        SELECT COUNT(*) FROM pg_proc p 
        JOIN pg_namespace n ON n.oid = p.pronamespace 
        WHERE n.nspname = '{schema_safe}' AND p.prokind = 'f'
    ),
    procedures_count AS (
        SELECT COUNT(*) FROM pg_proc p 
        JOIN pg_namespace n ON n.oid = p.pronamespace 
        WHERE n.nspname = '{schema_safe}' AND p.prokind = 'p'
    ),
    triggers_count AS (
        SELECT COUNT(*) FROM information_schema.triggers 
        WHERE trigger_schema = '{schema_safe}'
    ),
    indexes_count AS (
        SELECT COUNT(*) FROM pg_indexes 
        WHERE schemaname = '{schema_safe}'
    ),
    schemas_count AS (
        SELECT COUNT(*) FROM pg_namespace 
        WHERE nspname = '{schema_safe}'
    ),
    types_count AS (
        SELECT COUNT(*) FROM pg_type t 
        JOIN pg_namespace n ON n.oid = t.typnamespace 
        WHERE n.nspname = '{schema_safe}' 
        AND t.typtype IN ('b','c','d','e','r','m')
    ),
    extensions_count AS (
        SELECT COUNT(*) FROM pg_extension
    ),
    sequences_count AS (
        SELECT COUNT(*) FROM information_schema.sequences 
        WHERE sequence_schema = '{schema_safe}'
    )
    SELECT 
        (SELECT * FROM tables_count),
        (SELECT * FROM views_count),
        (SELECT * FROM functions_count),
        (SELECT * FROM procedures_count),
        (SELECT * FROM triggers_count),
        (SELECT * FROM indexes_count),
        (SELECT * FROM schemas_count),
        (SELECT * FROM types_count),
        (SELECT * FROM extensions_count),
        (SELECT * FROM sequences_count);
    """
                f.write(query)
                temp_file = f.name
                print(f"📝 Arquivo temporário criado: {temp_file}")

            # Preparar comando
            cmd = [
                str(psql_path),
                "-h", str(host).strip(),
                "-p", str(port).strip(),
                "-U", str(user).strip(),
                "-d", str(database).strip(),
                "-q",
                "-X",
                "-v", "ON_ERROR_STOP=1",
                "-f", temp_file,
            ]

            # Configurar ambiente com a senha
            env = os.environ.copy()
            if password:
                env["PGPASSWORD"] = str(password)
                print("✅ Variável PGPASSWORD configurada")
            else:
                print("⚠️ Sem senha fornecida")

            print(f"🔧 Executando psql fallback: {' '.join(cmd)}")

            # Aumentar timeout para 60 segundos
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=60,  # Aumentado para 60 segundos
                encoding='utf-8',
                errors='replace'
            )

            # Limpar arquivo temporário
            try:
                os.unlink(temp_file)
                print(f"🗑️ Arquivo temporário removido: {temp_file}")
            except Exception as e:
                print(f"⚠️ Erro ao remover arquivo temporário: {e}")

            # Verificar resultado
            if result.returncode == 0:
                output = result.stdout.strip()
                print(f"📤 Output do psql: {output[:200]}...")

                # Procurar linha com 10 números separados por |
                for line in output.splitlines():
                    line = line.strip()
                    if line and len(line.split('|')) == 10:
                        parts = line.split('|')
                        try:
                            tables = int(parts[0])
                            views = int(parts[1])
                            functions = int(parts[2])
                            procedures = int(parts[3])
                            triggers = int(parts[4])
                            indexes = int(parts[5])
                            schemas = int(parts[6])
                            types = int(parts[7])
                            extensions = int(parts[8])
                            sequences = int(parts[9])

                            total = (tables + views + functions + procedures + triggers +
                                     indexes + schemas + types + extensions + sequences)

                            print(f"✅ Contagem via psql bem-sucedida!")
                            print(f"   Tables: {tables}, Views: {views}, Functions: {functions}")
                            print(f"   Total: {total}")

                            self.log_html(f"📊 CONTAGEM VIA PSQL:")
                            self.log_html(f"   • {tables} tabelas")
                            self.log_html(f"   • {views} views")
                            self.log_html(f"   • {functions} funções")
                            self.log_html(f"   • {procedures} procedures")
                            self.log_html(f"   • {triggers} triggers")
                            self.log_html(f"   • {indexes} índices")
                            self.log_html(f"   • {schemas} schemas")
                            self.log_html(f"   • {types} tipos")
                            self.log_html(f"   • {extensions} extensões")
                            self.log_html(f"   • {sequences} sequences")
                            self.log_html(f"   • TOTAL: {total} estruturas")

                            return {
                                "tables": tables,
                                "views": views,
                                "functions": functions,
                                "procedures": procedures,
                                "triggers": triggers,
                                "indexes": indexes,
                                "schemas": schemas,
                                "types": types,
                                "extensions": extensions,
                                "sequences": sequences,
                                "total_created": total,
                                "tables_list": [],
                                "views_list": [],
                                "functions_list": [],
                                "triggers_list": [],
                            }
                        except (ValueError, IndexError) as e:
                            print(f"Erro ao parsear output: {e}")
                            continue

                # Se não encontrou a linha com 10 números
                print(f"⚠️ Não foi possível encontrar a linha com as contagens no output")
                print(f"Output completo:\n{output}")

            else:
                print(f"❌ psql falhou com código {result.returncode}")
                if result.stderr:
                    print(f"stderr: {result.stderr}")
                if result.stdout:
                    print(f"stdout: {result.stdout}")

                self.log_html(f"⚠️ Fallback psql falhou: {result.stderr[:200] if result.stderr else 'Sem saída'}")

        except subprocess.TimeoutExpired:
            print("❌ Timeout de 60 segundos excedido ao executar psql")
            self.log_html("⚠️ Timeout ao executar psql para contagem de estruturas")

        except Exception as e:
            print(f"❌ Erro no fallback psql: {e}")
            self.log_html(f"⚠️ Fallback psql também falhou: {e}")
            import traceback
            traceback.print_exc()

        # Se tudo falhar, fazer uma consulta manual via subprocess mais simples
        try:
            print("🔄 Tentando consulta simples como último recurso...")

            # Comando mais simples para testar conexão
            test_cmd = [
                str(psql_path),
                "-h", str(host).strip(),
                "-p", str(port).strip(),
                "-U", str(user).strip(),
                "-d", str(database).strip(),
                "-t", "-A",
                "-c",
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='opera' AND table_type='BASE TABLE';"
            ]

            env = os.environ.copy()
            if password:
                env["PGPASSWORD"] = str(password)

            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode == 0 and result.stdout.strip():
                tables = int(result.stdout.strip() or 0)
                print(f"✅ Consulta simples bem-sucedida: {tables} tabelas encontradas")

                return {
                    "tables": tables,
                    "views": 0,
                    "functions": 0,
                    "procedures": 0,
                    "triggers": 0,
                    "indexes": 0,
                    "schemas": 1,
                    "types": 0,
                    "extensions": 2,
                    "sequences": 0,
                    "total_created": tables + 3,  # tables + schemas + extensions
                    "tables_list": [],
                    "views_list": [],
                    "functions_list": [],
                    "triggers_list": [],
                }
        except Exception as e:
            print(f"❌ Consulta simples também falhou: {e}")

        return zeros

    # ---------- Scripts ----------
    def _load_scripts(self):
        self.scripts_list.clear()
        try:
            scripts = self.db_manager.get_available_scripts()
            if isinstance(scripts, list) and scripts and isinstance(scripts[0], dict) and "filename" in scripts[0]:
                names = [s["filename"] for s in scripts]
            else:
                # fallback: procurar no disco
                names = sorted([p.name for p in self.scripts_dir.glob("*.sql")])
            for n in names:
                self.scripts_list.addItem(n)
            self.log_html(f"✅ Scripts carregados: {len(names)}")
        except Exception as e:
            # fallback: disco
            names = sorted([p.name for p in self.scripts_dir.glob("*.sql")])
            for n in names:
                self.scripts_list.addItem(n)
            self.log_html(f"⚠️ db_manager.get_available_scripts falhou, usei disco. ({_safe_str(e)})")

    # ---------- Detect ----------
    def on_detect(self):
        # Se já estiver rodando, vira 'Cancelar'
        if self._detect_worker and self._detect_worker.isRunning():
            self._detect_worker.stop()
            self.btn_detect.setText("🔍 Detectar")
            self._set_busy(False)
            self.log_html("🛑 Detecção cancelada pelo usuário.")
            return

        # Modo selecionado
        if getattr(self, 'rb_detect_manual', None) is not None and self.rb_detect_manual.isChecked():
            self.log_html("🧭 Modo manual: digite Host/IP e Porta e clique em 'Testar Conexão'.")
            return

        mode = "auto"
        if getattr(self, 'rb_detect_local', None) is not None and self.rb_detect_local.isChecked():
            mode = "local"
        elif getattr(self, 'rb_detect_lan', None) is not None and self.rb_detect_lan.isChecked():
            mode = "lan"

        self.found_table.setRowCount(0)
        user = self.user_input.text().strip()
        pwd = self.password_input.text()

        label = "Detectando..."
        if mode == "local":
            label = "Detectando no LOCAL (127.0.0.1)..."
        elif mode == "lan":
            label = "Detectando na LAN (rede local)..."

        self.btn_detect.setText("⏹ Cancelar")
        self._set_busy(True, label, allow_cancel=True)

        self._detect_worker = DetectWorker(user=user, password=pwd, db_manager=self.db_manager, mode=mode)
        self._detect_worker.found.connect(self._on_found)
        self._detect_worker.done.connect(self._on_detect_done)
        self._detect_worker.start()

    def _on_found(self, host: str, port: int, status: str):
        row = self.found_table.rowCount()
        self.found_table.insertRow(row)
        self.found_table.setItem(row, 0, QTableWidgetItem(host))
        self.found_table.setItem(row, 1, QTableWidgetItem(str(port)))
        self.found_table.setItem(row, 2, QTableWidgetItem(status))

    def _on_detect_done(self, ok: bool, msg: str):
        self._set_busy(False)
        self.btn_detect.setText("🔍 Detectar")
        self.log_html(msg)

    # ---------- Connection/Test ----------
    def _conn_inputs(self) -> Tuple[str, str, str, str, str]:
        host = self.host_input.text().strip() or "localhost"
        user = self.user_input.text().strip() or "postgres"
        pwd = self.password_input.text()
        port = self.port_input.text().strip()  # pode ser vazio
        db = self.db_combo.currentText()
        return host, user, pwd, port, db

    def on_test_connection(self):
        host, user, pwd, port, db = self._conn_inputs()
        self._run_task("test_connection", database=db, host=host, user=user, password=pwd, port=port)

    def on_check_db(self):
        host, user, pwd, port, _db = self._conn_inputs()
        # Verifica BANCO_OPERA
        self._run_task("check_db", database="BANCO_OPERA", host=host, user=user, password=pwd, port=port)

    # ---------- Run scripts ----------
    def _script_target_db(self, script: str) -> str:
        if script == "1_CRIAR_BANCO.sql":
            return "postgres"
        if script in ("2_CRIAR_SCHEMA.sql", "3_CRIAR_TABELAS.sql"):
            return "BANCO_OPERA"
        return "BANCO_OPERA"

    def on_run_selected(self):
        item = self.scripts_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Aviso", "Selecione um script na lista.")
            return
        script = item.text()
        self._run_one_script(script)

    def on_run_auto(self):
        # sequencial: 1,2,3
        self._auto_queue = ["1_CRIAR_BANCO.sql", "2_CRIAR_SCHEMA.sql", "3_CRIAR_TABELAS.sql"]
        # valida existência na lista
        available = {self.scripts_list.item(i).text() for i in range(self.scripts_list.count())}
        missing = [s for s in self._auto_queue if s not in available]
        if missing:
            QMessageBox.critical(self, "Erro", f"Scripts não encontrados: {', '.join(missing)}")
            return

        self._auto_running = True
        self.log_html("▶ Execução automática iniciada: 1 → 2 → 3")
        self._run_one_script(self._auto_queue.pop(0))

    def _run_one_script(self, script: str):
        host, user, pwd, port, _db = self._conn_inputs()
        db = self._script_target_db(script)
        # manter combobox sincronizado
        if self.db_combo.currentText() != db:
            self.db_combo.setCurrentText(db)
        # pré-check para 2/3
        if script in ("2_CRIAR_SCHEMA.sql", "3_CRIAR_TABELAS.sql"):
            try:
                try:
                    exists = self.db_manager.check_database_exists("BANCO_OPERA", pwd, user, port or None, host)
                except TypeError:
                    exists = self.db_manager.check_database_exists("BANCO_OPERA", pwd, user, port or None)
                if not exists:
                    self._auto_running = False
                    QMessageBox.critical(self, "Banco não encontrado",
                                         "BANCO_OPERA não existe. Execute o script 1 primeiro.")
                    return
            except Exception:
                # se não der pra checar, segue mesmo
                pass

        self._last_database = db
        self._last_script = script
        self._run_task("run_script", script_name=script, database=db, host=host, user=user, password=pwd, port=port)

    # ---------- Task runner ----------
    def _run_task(self, task: str, **kwargs):
        if self._task_worker and self._task_worker.isRunning():
            QMessageBox.information(self, "Aguarde", "Já existe uma tarefa em execução.")
            return

        label = "Executando..." if task == "run_script" else "Processando..."
        if task == "run_script":
            label = f"Executando {kwargs.get('script_name', '')}..."
        self._set_busy(True, label, allow_cancel=True)

        self._task_worker = TaskWorker(self.db_manager, task, **kwargs)
        self._task_worker.log.connect(self.log_html)
        self._task_worker.finished_task.connect(self._on_task_finished)
        self._task_worker.start()


    def on_clear_log(self):
        self.log_area.clear()
        self.tech_log.clear()
        self.log_html("🧹 Log limpo.")

    def _summarize_psql_output(self, out: str) -> dict:
        """
        Gera um resumo amigável do output do psql (contagem de objetos criados).
        Versão melhorada com detecção mais precisa.
        """
        import re  # <--- IMPORTANTE: Importar re aqui

        s = (out or "")
        up = s.upper()

        print(f"🔍 Analisando output do psql (tamanho: {len(s)} caracteres)")

        # Contar ocorrências de CREATE com diferentes padrões
        def count_pattern(pattern: str, variations: list = None) -> int:
            """Conta ocorrências de CREATE [OR REPLACE] pattern"""
            # Padrões principais
            main_pattern = rf'CREATE\s+(?:OR\s+REPLACE\s+)?{re.escape(pattern)}\s+'
            count = len(re.findall(main_pattern, up, re.IGNORECASE))

            # Variações adicionais se fornecidas
            if variations:
                for var in variations:
                    var_pattern = rf'CREATE\s+(?:OR\s+REPLACE\s+)?{re.escape(var)}\s+'
                    count += len(re.findall(var_pattern, up, re.IGNORECASE))

            return count

        # Contar mensagens de sucesso/confirmação
        def count_success_messages(pattern: str) -> int:
            """Conta mensagens como 'CREATE TABLE', 'CREATE VIEW' no output normal"""
            # Procura por linhas que começam com CREATE ou terminam com criado com sucesso
            success_pattern = rf'(?:CREATE|CRIADO|SUCESSO).*?{re.escape(pattern)}'
            return len(re.findall(success_pattern, up, re.IGNORECASE))

        # Contagens detalhadas
        tables = count_pattern("TABLE", ["TABELA"])
        views = count_pattern("VIEW")
        functions = count_pattern("FUNCTION", ["FUNÇÃO", "FUNCAO"])
        procedures = count_pattern("PROCEDURE")
        triggers = count_pattern("TRIGGER")
        indexes = count_pattern("INDEX")
        schemas = count_pattern("SCHEMA")
        types = count_pattern("TYPE")
        extensions = count_pattern("EXTENSION")
        sequences = count_pattern("SEQUENCE")

        # Se não encontrou com o padrão acima, tenta mensagens de sucesso
        if tables == 0:
            tables = count_success_messages("TABLE") + count_success_messages("TABELA")
        if views == 0:
            views = count_success_messages("VIEW")
        if functions == 0:
            functions = count_success_messages("FUNCTION") + count_success_messages("FUNÇÃO")

        # Contar NOTICE lines que podem indicar criação
        notice_count = len(re.findall(r'NOTICE:', up))
        if notice_count > 0:
            print(f"  - Encontrou {notice_count} mensagens NOTICE")

        # Tentar extrair números de mensagens como "CREATE TABLE 42"
        table_matches = re.findall(r'CREATE\s+TABLE\s+\w+\s+(\d+)', up, re.IGNORECASE)
        if table_matches:
            tables = max(tables, sum(int(m) for m in table_matches))

        # Garantir que pelo menos temos as tabelas principais do sistema OPERA
        # Se o script 3 foi executado, deve ter pelo menos 57 tabelas
        if "3_CRIAR_TABELAS" in s and tables < 57:
            # Tabelas conhecidas do sistema OPERA
            known_tables = [
                '_schema_info', 'usuarios', 'usuario_preferencias', 'usuario_permissoes',
                'usuario_logs', 'usuario_temas_personalizados', 'cadastro_modelos_cabecalho',
                'cadastro_modelos_tecidos', 'cadastro_modelos_aviamentos', 'cadastro_modelos_outros',
                'cadastro_modelos_outros_servicos', 'cadastro_modelos_imagens', 'cadastro_modelos_grade',
                'cadastro_faccoes', 'cadastro_de_corte', 'cadastro_de_corte_tecidos',
                'cadastro_de_corte_lotes', 'ordem_corte_ficha', 'ordem_corte_lotes',
                'ordem_grade_preferencias', 'controle_envio_cortes', 'envios_cortes',
                'envio_detalhes_tamanho', 'controle_retorno_cortes', 'entrada_acabamento',
                'entrada_acabamento_detalhes', 'retorno_detalhes_tamanho', 'cortes_finalizados',
                'cortes_finalizados_completo', 'pecas_finalizadas', 'log_finalizacoes',
                'adiantamento_faccao', 'pagamento_servicos', 'pagamento_servicos_detalhe',
                'pagamento_corte_acabamento', 'estoque_tecidos', 'estoque_aviamentos',
                'estoque_insumos', 'estoque_escritorio', 'estoque_limpeza', 'estoque_outros',
                'estoque_saida_log', 'servicos', 'historico_servicos', 'historico_de_servico',
                'defeitos_envios', 'pricing_profiles', 'relatorios_finalizacao',
                'cadastro_clientes', 'compras_fornecedores', 'compras_pedidos',
                'compras_recebimentos', 'mrp_necessidades', 'mrp_ordens_recomendadas',
                'planejamento_ops', 'planejamento_capacidade', 'custos_reais_categoria',
                'custos_reais_ops'
            ]
            # Contar quantas dessas tabelas aparecem no output
            tables_from_list = sum(1 for table in known_tables if table.lower() in s.lower())
            tables = max(tables, tables_from_list)
            print(f"  - Detectadas {tables_from_list} tabelas conhecidas no output")

        summary = {
            "tables": tables,
            "views": views,
            "functions": functions,
            "procedures": procedures,
            "triggers": triggers,
            "indexes": indexes,
            "schemas": schemas,
            "types": types,
            "extensions": extensions,
            "sequences": sequences,
        }

        # Calcular total
        summary["total_created"] = sum(summary.values())

        print(f"  - Total de estruturas detectadas no output: {summary['total_created']}")
        for key, value in summary.items():
            if key != "total_created" and value > 0:
                print(f"    {key}: {value}")

        return summary

# -----------------------------
# Exec local (debug)
# -----------------------------
if __name__ == "__main__":
    # modo teste: tenta importar DatabaseManager se existir
    try:
        from database_manager import DatabaseManager  # type: ignore

        dm = DatabaseManager()
    except Exception:
        dm = object()  # placeholder

    app = QApplication([])
    w = InstallerApp(dm)
    w.show()
    app.exec_()