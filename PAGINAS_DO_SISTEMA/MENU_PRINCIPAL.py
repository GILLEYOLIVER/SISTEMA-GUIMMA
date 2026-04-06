# -*- coding: utf-8 -*-
"""
MENU_PRINCIPAL.py - Sistema OPERA Refatorado
Menu principal com sistema de temas, permissões e cache otimizado.
VERSÃO SEM HOVER - BOTÕES ESTÁTICOS
"""

import json
import platform
import importlib
import importlib.util
import inspect
import functools
import os
import sys
import threading
import time
from datetime import datetime

import tkinter as tk
from tkinter import messagebox, ttk, font as tkfont

from PIL import Image, ImageTk
import customtkinter as ctk

OPERA_DEBUG = bool(os.environ.get('OPERA_DEBUG', '').strip())
ACTIVITY_DB_LOG_ENABLED = str(os.environ.get("OPERA_DB_ACTIVITY_LOG", "0")).strip().lower() in {"1", "true", "yes", "on"}


def _dprint(*args, **kwargs):
    """Print controlado por OPERA_DEBUG para não atrasar o startup."""
    if OPERA_DEBUG:
        print(*args, **kwargs)


APP_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from PAGINAS_DO_SISTEMA.TEMAS import (
    TemasPage,
    ModuloPaletas,
    aplicar_estilo_treeview,
    get_contraste_texto,
    is_dark_color,
    padronizar_treeview,
    remover_bordas_botoes_tema,
)
from PAGINAS_DO_SISTEMA.ui_after_guard import (
    cancel_all_after_info,
    cancel_all_afters,
    initialize_after_guard,
    reset_tk_default_root,
    safe_after_cancel,
)
from PAGINAS_DO_SISTEMA.LOG_SISTEMA import get_logger

# ===== IMPORTAÇÕES DO SISTEMA =====
try:
    from PAGINAS_DO_SISTEMA.USUARIOS import registrar_log_db

    LOGS_DISPONIVEIS = True
    _dprint("✅ Função de logs disponível.")
except ImportError as e:
    LOGS_DISPONIVEIS = False
    _dprint(f"⚠️ Logs não disponíveis: {e}")


    def registrar_log_db(usuario, acao, pagina, detalhe=""):
        """Função fallback para logs."""
        pass

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema

    MENU_POSTGRES_AVAILABLE = True
    _dprint("✅ PostgreSQL disponível.")
except Exception as e:
    _dprint(f"❌ PostgreSQL indisponível: {e}")
    MENU_POSTGRES_AVAILABLE = False


    def get_conn():
        raise RuntimeError("PostgreSQL indisponível")


    def get_schema():
        return "opera"

# === WRAPPER: evita travar o sistema quando o banco cair ===
# Se a conexão falhar 1x, entra em "cooldown" e não tenta de novo por alguns segundos,
# evitando spam de tentativas e travamentos em páginas que só precisam abrir a UI.
if 'MENU_POSTGRES_AVAILABLE' in globals() and MENU_POSTGRES_AVAILABLE:
    _raw_get_conn = get_conn  # mantém referência
    _DB_FAIL_UNTIL = 0.0
    _DB_COOLDOWN_SECONDS = float(os.environ.get("OPERA_DB_COOLDOWN", "30") or "30")


    def get_conn(*args, **kwargs):
        global _DB_FAIL_UNTIL
        now = time.time()
        if now < _DB_FAIL_UNTIL:
            raise RuntimeError("Banco de dados indisponível (cooldown ativo).")
        try:
            return _raw_get_conn(*args, **kwargs)
        except Exception as e:
            _DB_FAIL_UNTIL = now + _DB_COOLDOWN_SECONDS
            raise e


# ===== FUNÇÃO AUXILIAR DE DETECÇÃO DE COR ESCURA (FALLBACK) =====
def is_dark_color_fallback(hex_color: str) -> bool:
    """
    Calcula se uma cor hexadecimal é escura com base na luminância.
    Retorna True para cores escuras, False para claras.
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        luminancia = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminancia < 0.5
    except:
        return True  # seguro: assume escuro


# Tenta importar a função original, senão usa o fallback
try:
    from PAGINAS_DO_SISTEMA.TEMAS import is_dark_color
except ImportError:
    is_dark_color = is_dark_color_fallback

# ===== CONFIGURAÇÕES GLOBAIS =====
IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"
BASE_DIR = os.path.dirname(APP_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)


def _resolve_app_path(filename: str) -> str:
    """Resolve caminhos de arquivos compartilhados na raiz do projeto."""
    local_path = os.path.join(APP_DIR, filename)
    if os.path.exists(local_path):
        return local_path
    base_path = os.path.join(BASE_DIR, filename)
    if os.path.exists(base_path):
        return base_path
    return os.path.join(ROOT_DIR, filename)


ROUTES_PATH = _resolve_app_path("route_map.json")
SETTINGS_PATH = _resolve_app_path("settings.json")
ICONS_DIR = _resolve_app_path("icons")
ICONE_SISTEMA = _resolve_app_path("ICONE_SISTEMA.png")


# ===== GERENCIADOR DE CONFIGURAÇÕES =====
class ConfigManager:
    """Gerencia configurações do sistema."""

    @staticmethod
    def load_settings() -> dict:
        """Carrega configurações do arquivo settings.json."""
        default = {"theme": "CLÁSSICO CLARO", "last_page": "Dashboard", "language": "pt_BR"}
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    user_settings = json.load(f)
                    if isinstance(user_settings, dict):
                        default.update(user_settings)
            except Exception:
                pass
        return default

    @staticmethod
    def save_settings(data: dict):
        """Salva configurações no arquivo settings.json."""
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @staticmethod
    def load_routes() -> dict:
        """Carrega rotas do arquivo route_map.json."""
        candidates = [
            ROUTES_PATH,
            os.path.join(BASE_DIR, "route_map.json"),
            os.path.join(os.getcwd(), "route_map.json"),
        ]
        for path in candidates:
            if not path or not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                if isinstance(data, dict) and data:
                    return data
            except Exception as exc:
                _dprint(f"⚠️ Falha ao carregar rotas em {path}: {exc}")
        return {}

    @staticmethod
    def ensure_icons_directory():
        """Garante que a pasta de ícones existe."""
        if not os.path.exists(ICONS_DIR):
            _dprint(f"📁 Criando pasta de ícones: {ICONS_DIR}")
            os.makedirs(ICONS_DIR, exist_ok=True)
        return ICONS_DIR


# ===== GERENCIADOR DE TEMAS =====
class ThemeManager:
    """Gerencia e aplica temas no sistema OPERA."""

    def __init__(self, app):
        self.app = app
        self.current_theme_name: str | None = None
        self.current_palette: dict | None = None
        self.fonts = self._default_fonts()

    def apply_theme(self, theme_name: str, palette: dict | None = None, *, rebuild_interface: bool = False):
        """Aplica o tema informado (padrão ou personalizado) consistentemente."""
        import customtkinter as ctk
        from PAGINAS_DO_SISTEMA.TEMAS import ModuloPaletas, is_dark_color

        # Obtém a paleta
        if palette:
            pal = dict(palette)
            _dprint(f"[Tema] Aplicando paleta personalizada para '{theme_name}'.")
        else:
            try:
                pal = ModuloPaletas().PADROES.get(theme_name)
                if not pal:
                    _dprint(f"[Tema] Tema '{theme_name}' não encontrado. Usando 'CLÁSSICO CLARO'.")
                    pal = ModuloPaletas().PADROES.get("CLÁSSICO CLARO", {})
                else:
                    pal = dict(pal)
                    _dprint(f"[Tema] Aplicando tema padrão '{theme_name}'.")
            except:
                fallback = {
                    "primaria": "#121212", "secundaria": "#1F1F1F", "terciaria": "#3E3E3E",
                    "fundo": "#181818", "texto": "#EEEEEE", "destaque": "#BB86FC",
                    "sucesso": "#03DAC6", "alerta": "#CF6679", "borda": "#3A3A3A",
                    "hover": "#2C2C2C", "selecao": "#BB86FC"
                }
                pal = fallback

        self.current_theme_name = theme_name
        self.current_palette = pal

        try:
            for chave, valor in pal.items():
                setattr(self.app, f"cor_{chave}", valor)
        except Exception as e:
            _dprint(f"[Tema] Erro ao aplicar atributos de cor no app: {e}")

        self._configure_button_styles(pal)
        self._configure_base_fonts()

        try:
            fundo = pal.get("fundo", "#000000")
            modo = "dark" if is_dark_color(fundo) else "light"
            ctk.set_appearance_mode(modo)
            self.app.tema_modo = modo
        except Exception as e:
            _dprint(f"[Tema] Erro ao definir modo claro/escuro: {e}")

        try:
            ctk.set_default_color_theme("dark" if getattr(self.app, "tema_modo", "dark") == "dark" else "light")
        except Exception:
            pass

        self._apply_global_theme(pal)

        try:
            if hasattr(self.app, "_update_menu_buttons_colors"):
                self.app._update_menu_buttons_colors()
        except Exception as e:
            _dprint(f"[Tema] Falha ao atualizar cores do menu: {e}")

        try:
            if hasattr(self.app, 'refresh_theme_widgets'):
                self.app.refresh_theme_widgets()
            elif rebuild_interface:
                self._rebuild_interface()
        except Exception as e:
            _dprint(f"[Tema] Falha ao atualizar widgets existentes: {e}")

        self._persist_theme_choice(theme_name, pal)
        _dprint(f"[Tema] Tema '{theme_name}' aplicado com sucesso!")

    def _default_fonts(self):
        return {
            "title": ("Arial", 14, "bold"),
            "heading": ("Arial", 12, "bold"),
            "body": ("Arial", 12),
            "small": ("Arial", 11),
            "button": ("Arial", 12, "bold"),
        }

    def _configure_button_styles(self, palette: dict):
        import tkinter as tk
        from tkinter import ttk

        cor_secundaria = palette.get("secundaria", "#1F2937")
        cor_texto = palette.get("texto", "#FFFFFF")
        cor_hover = palette.get("hover", cor_secundaria)

        try:
            estilo = ttk.Style(self.app)
            estilo.configure(
                "Opera.TButton",
                background=cor_secundaria,
                foreground=cor_texto,
                relief=tk.FLAT,
                borderwidth=0,
                focusthickness=0,
                highlightthickness=0,
                padding=6,
                font=self.fonts["button"],
            )
            estilo.configure(
                "TButton",
                background=cor_secundaria,
                foreground=cor_texto,
                relief=tk.FLAT,
                borderwidth=0,
                focusthickness=0,
                highlightthickness=0,
                padding=6,
                font=self.fonts["button"],
            )
            estilo.map(
                "Opera.TButton",
                background=[("active", cor_hover), ("pressed", cor_hover)],
                relief=[("pressed", tk.FLAT), ("active", tk.FLAT)],
                bordercolor=[("pressed", ""), ("active", "")],
            )
            estilo.map(
                "TButton",
                background=[("active", cor_hover), ("pressed", cor_hover)],
                relief=[("pressed", tk.FLAT), ("active", tk.FLAT)],
                bordercolor=[("pressed", ""), ("active", "")],
            )
        except Exception as e:
            _dprint(f"[Tema] Erro ao configurar estilos base de botões: {e}")

        try:
            self.app.option_add("*Button.highlightthickness", 0)
            self.app.option_add("*Button.borderwidth", 0)
            self.app.option_add("*Button.relief", tk.FLAT)
            self.app.option_add("*Button.highlightcolor", cor_secundaria)
            self.app.option_add("*Button.highlightbackground", cor_secundaria)
        except Exception:
            pass

    def _configure_base_fonts(self):
        try:
            self.app.font_title = self.fonts["title"]
            self.app.font_heading = self.fonts["heading"]
            self.app.font_body = self.fonts["body"]
            self.app.font_small = self.fonts["small"]
            self.app.font_button = self.fonts["button"]
        except Exception as e:
            _dprint(f"[Tema] Erro ao configurar fontes base: {e}")

    def _apply_palette_to_widget(self, root_widget, palette: dict, fonts: dict):
        import customtkinter as ctk
        import tkinter as tk
        from tkinter import ttk

        cor_fundo = palette.get("fundo", "#000000")
        cor_primaria = palette.get("primaria", "#3B82F6")
        cor_secundaria = palette.get("secundaria", "#1F2937")
        cor_texto = palette.get("texto", "#FFFFFF")
        cor_borda = palette.get("borda", "#333333")
        cor_hover = palette.get("hover", "#374151")
        cor_sucesso = palette.get("sucesso", "#22c55e")
        cor_alerta = palette.get("alerta", "#ef4444")
        cor_destaque = palette.get("destaque", "#2563eb")

        cor_hover_realcado = self._realcar_cor(cor_secundaria, 1.3)

        try:
            aplicar_estilo_treeview(
                style=ttk.Style(root_widget),
                prefixo="Treeview",
                cor_fundo=cor_fundo,
                cor_linhas=cor_secundaria,
                cor_cabecalho=cor_primaria,
                cor_texto=get_contraste_texto(cor_secundaria) or cor_texto,
                cor_borda=cor_borda,
                cor_selecao=palette.get("selecao", cor_destaque),
                altura_linha=28,
            )
        except Exception as e:
            _dprint(f"[Tema] Erro ao aplicar estilo Treeview: {e}")

        try:
            estilo_btn_ttk = ttk.Style(root_widget)
            estilo_btn_ttk.configure(
                "Opera.TButton",
                background=cor_secundaria,
                foreground=cor_texto,
                relief=tk.FLAT,
                borderwidth=0,
                focusthickness=0,
                highlightthickness=0,
                padding=6,
                font=fonts["button"],
            )
            estilo_btn_ttk.map(
                "Opera.TButton",
                background=[("active", cor_hover_realcado), ("pressed", cor_hover)],
                relief=[("pressed", tk.FLAT), ("active", tk.FLAT)],
            )
            estilo_btn_ttk.map(
                "TButton",
                background=[("active", cor_hover_realcado), ("pressed", cor_hover)],
                relief=[("pressed", tk.FLAT), ("active", tk.FLAT)],
            )
        except Exception as e:
            _dprint(f"[Tema] Erro ao aplicar tema em botões ttk: {e}")

        try:
            estilo_form_ttk = ttk.Style(root_widget)
            estilo_form_ttk.configure(
                "Opera.TCombobox",
                fieldbackground=cor_secundaria,
                background=cor_secundaria,
                foreground=cor_texto,
                bordercolor=cor_borda,
                arrowcolor=cor_texto,
                insertcolor=cor_texto,
            )
            estilo_form_ttk.map(
                "Opera.TCombobox",
                fieldbackground=[("readonly", cor_secundaria), ("active", cor_secundaria)],
                foreground=[("readonly", cor_texto), ("active", cor_texto)],
                background=[("readonly", cor_secundaria), ("active", cor_secundaria)],
            )
            estilo_form_ttk.configure(
                "Opera.TCheckbutton",
                background=cor_fundo,
                foreground=cor_texto,
                indicatorcolor=cor_destaque,
                indicatordiameter=14,
                focuscolor=cor_fundo,
                font=fonts["body"],
            )
            estilo_form_ttk.map(
                "Opera.TCheckbutton",
                background=[("active", cor_fundo)],
                foreground=[("active", cor_texto)],
                indicatorcolor=[("selected", cor_destaque), ("active", cor_hover_realcado)],
            )
            estilo_form_ttk.configure(
                "Opera.TRadiobutton",
                background=cor_fundo,
                foreground=cor_texto,
                indicatorcolor=cor_destaque,
                focuscolor=cor_fundo,
                font=fonts["body"],
            )
            estilo_form_ttk.map(
                "Opera.TRadiobutton",
                background=[("active", cor_fundo)],
                foreground=[("active", cor_texto)],
                indicatorcolor=[("selected", cor_destaque), ("active", cor_hover_realcado)],
            )
        except Exception as e:
            _dprint(f"[Tema] Erro ao aplicar estilos ttk de formulários: {e}")

        def _describe_widget(widget) -> str:
            try:
                name = widget.winfo_name()
                cls = widget.__class__.__name__
                master = widget.master.winfo_name() if getattr(widget, "master", None) else "(sem master)"
                return f"{cls}('{name}' em '{master}')"
            except Exception:
                return repr(widget)

        def _apply_to_all_widgets(widget):
            parar_recursao = False
            try:
                if isinstance(widget, ctk.CTkFrame):
                    widget.configure(fg_color=cor_fundo, border_color=cor_borda)
                    parar_recursao = False
                elif isinstance(widget, ctk.CTkButton):
                    try:
                        cor_texto_botao = self._contrast_text_for_color(cor_primaria, fallback=cor_texto)
                        widget.configure(
                            border_width=0,
                            bg_color="transparent",
                            fg_color=cor_primaria,
                            hover_color=cor_hover,
                            border_color=cor_borda,
                            text_color=cor_texto_botao,
                            font=fonts["button"],
                            corner_radius=getattr(widget, "corner_radius", 8),
                            hover=True,
                        )
                    except Exception as e:
                        _dprint(f"[Tema][DEBUG] Falha ao ajustar CTkButton: {e}")
                    parar_recursao = True
                elif isinstance(widget, ctk.CTkLabel):
                    widget.configure(
                        fg_color="transparent",
                        bg_color="transparent",
                        text_color=cor_texto,
                        font=fonts["body"],
                    )
                    parar_recursao = True
                elif isinstance(widget, ctk.CTkEntry):
                    widget.configure(
                        fg_color=cor_secundaria,
                        border_color=cor_borda,
                        text_color=cor_texto,
                        font=fonts["body"],
                    )
                    parar_recursao = True
                elif isinstance(widget, ctk.CTkComboBox):
                    widget.configure(
                        fg_color=cor_secundaria,
                        border_color=cor_borda,
                        button_color=cor_primaria,
                        button_hover_color=cor_hover,
                        text_color=cor_texto,
                        font=fonts["body"],
                        dropdown_fg_color=cor_secundaria,
                        dropdown_text_color=cor_texto,
                        dropdown_hover_color=cor_hover,
                    )
                    parar_recursao = True
                elif isinstance(widget, ctk.CTkOptionMenu):
                    try:
                        option_texto = self._contrast_text_for_color(cor_secundaria, fallback=cor_texto)
                        widget.configure(
                            fg_color=cor_secundaria,
                            button_color=cor_primaria,
                            button_hover_color=cor_hover,
                            text_color=option_texto,
                            dropdown_fg_color=cor_secundaria,
                            dropdown_text_color=option_texto,
                            dropdown_hover_color=cor_hover,
                        )
                    except Exception as e:
                        _dprint(f"[Tema][DEBUG] Falha ao ajustar CTkOptionMenu {_describe_widget(widget)}: {e}")
                    parar_recursao = True
                elif isinstance(widget, ctk.CTkCheckBox):
                    cor_checkbox = cor_destaque or cor_primaria
                    cor_checkmark = self._contrast_text_for_color(cor_checkbox, fallback=cor_texto)
                    widget.configure(
                        fg_color=cor_checkbox,
                        hover_color=cor_hover_realcado,
                        border_color=cor_borda,
                        checkmark_color=cor_checkmark,
                        text_color=cor_texto,
                        font=fonts["body"],
                    )
                    parar_recursao = True
                elif isinstance(widget, ctk.CTkRadioButton):
                    cor_radio = cor_destaque or cor_primaria
                    widget.configure(
                        fg_color=cor_radio,
                        hover_color=cor_hover_realcado,
                        border_color=cor_borda,
                        text_color=cor_texto,
                        font=fonts["body"],
                    )
                    parar_recursao = True
                elif isinstance(widget, ctk.CTkSwitch):
                    widget.configure(
                        fg_color=cor_secundaria,
                        progress_color=cor_destaque,
                        button_color=cor_texto,
                        button_hover_color=cor_hover,
                        border_color=cor_borda,
                        text_color=cor_texto,
                        font=fonts["body"],
                    )
                    parar_recursao = True
                elif isinstance(widget, ctk.CTkProgressBar):
                    try:
                        widget.configure(
                            fg_color=cor_secundaria,
                            progress_color=cor_destaque,
                            border_color=cor_borda,
                        )
                    except Exception as e:
                        _dprint(f"[Tema][DEBUG] Falha ao ajustar CTkProgressBar {_describe_widget(widget)}: {e}")
                    parar_recursao = True
                elif isinstance(widget, ctk.CTkScrollbar):
                    try:
                        widget.configure(
                            fg_color=cor_secundaria,
                            button_color=cor_primaria,
                            button_hover_color=cor_hover,
                            progress_color=cor_primaria,
                        )
                    except Exception as e:
                        _dprint(f"[Tema][DEBUG] Falha ao ajustar CTkScrollbar {_describe_widget(widget)}: {e}")
                    parar_recursao = True
                elif isinstance(widget, ctk.CTk):
                    try:
                        widget.configure(fg_color=cor_fundo)
                    except Exception as e:
                        _dprint(f"[Tema][DEBUG] Falha ao ajustar CTk root {_describe_widget(widget)}: {e}")
                    parar_recursao = False
                elif isinstance(widget, ctk.CTkToplevel):
                    try:
                        widget.configure(fg_color=cor_fundo)
                    except Exception as e:
                        _dprint(f"[Tema][DEBUG] Falha ao ajustar CTkToplevel {_describe_widget(widget)}: {e}")
                    parar_recursao = False
                elif isinstance(widget, ctk.CTkTabview):
                    widget.configure(
                        segmented_button_fg_color=cor_primaria,
                        segmented_button_selected_color=cor_hover_realcado,
                        segmented_button_unselected_color=cor_secundaria,
                        segmented_button_unselected_hover_color=cor_hover,
                        segmented_button_selected_hover_color=cor_hover_realcado,
                        text_color=cor_texto,
                        font=fonts["body"],
                    )
                    parar_recursao = True
                elif isinstance(widget, ctk.CTkScrollableFrame):
                    widget.configure(fg_color=cor_fundo, border_color=cor_borda)
                    parar_recursao = False
                elif isinstance(widget, ttk.Treeview):
                    padronizar_treeview(widget)
                    parar_recursao = True
                elif isinstance(widget, ttk.Scrollbar):
                    try:
                        estilo_scroll = ttk.Style(widget)
                        estilo_scroll.configure(
                            "Opera.Vertical.TScrollbar",
                            troughcolor=cor_secundaria,
                            bordercolor=cor_borda,
                            background=cor_primaria,
                            arrowcolor=cor_texto,
                        )
                        estilo_scroll.configure(
                            "Opera.Horizontal.TScrollbar",
                            troughcolor=cor_secundaria,
                            bordercolor=cor_borda,
                            background=cor_primaria,
                            arrowcolor=cor_texto,
                        )
                        estilo_scroll.map(
                            "Opera.Vertical.TScrollbar",
                            background=[("active", cor_hover_realcado)],
                            arrowcolor=[("active", cor_texto)],
                        )
                        estilo_scroll.map(
                            "Opera.Horizontal.TScrollbar",
                            background=[("active", cor_hover_realcado)],
                            arrowcolor=[("active", cor_texto)],
                        )
                        orient = widget.cget("orient")
                        widget.configure(
                            style="Opera.Vertical.TScrollbar" if orient == "vertical" else "Opera.Horizontal.TScrollbar"
                        )
                    except Exception as e:
                        _dprint(f"[Tema][DEBUG] Falha ao ajustar ttk.Scrollbar {_describe_widget(widget)}: {e}")
                    parar_recursao = True
                elif isinstance(widget, tk.Scrollbar):
                    try:
                        widget.configure(
                            bg=cor_fundo,
                            activebackground=cor_hover,
                            troughcolor=cor_secundaria,
                            highlightthickness=0,
                            bd=0,
                            relief=tk.FLAT,
                        )
                    except Exception as e:
                        _dprint(f"[Tema][DEBUG] Falha ao ajustar tk.Scrollbar {_describe_widget(widget)}: {e}")
                    parar_recursao = True
                elif isinstance(widget, tk.Canvas):
                    try:
                        widget.configure(bg=cor_fundo, highlightthickness=0, bd=0)
                    except Exception as e:
                        _dprint(f"[Tema][DEBUG] Falha ao ajustar tk.Canvas {_describe_widget(widget)}: {e}")
                    parar_recursao = False
                elif isinstance(widget, ttk.Button):
                    widget.configure(style="Opera.TButton")
                    parar_recursao = True
                elif isinstance(widget, tk.Button):
                    widget.configure(
                        bg=cor_secundaria,
                        fg=cor_texto,
                        activebackground=cor_hover,
                        relief=tk.FLAT,
                        borderwidth=0,
                        highlightthickness=0,
                        font=fonts["button"],
                    )
                    parar_recursao = True
                elif isinstance(widget, tk.Label):
                    widget.configure(
                        bg=cor_fundo,
                        fg=cor_texto,
                        font=fonts["body"],
                    )
                    parar_recursao = True
                elif isinstance(widget, tk.Entry):
                    widget.configure(
                        bg=cor_secundaria,
                        fg=cor_texto,
                        insertbackground=cor_texto,
                        disabledbackground=cor_secundaria,
                        disabledforeground=cor_texto,
                        readonlybackground=cor_secundaria,
                        relief=tk.FLAT,
                        bd=1,
                        highlightthickness=1,
                        highlightbackground=cor_borda,
                        highlightcolor=cor_destaque,
                        font=fonts["body"],
                    )
                    parar_recursao = True
                elif isinstance(widget, tk.Text):
                    widget.configure(
                        bg=cor_secundaria,
                        fg=cor_texto,
                        insertbackground=cor_texto,
                        relief=tk.FLAT,
                        bd=1,
                        highlightthickness=1,
                        highlightbackground=cor_borda,
                        highlightcolor=cor_destaque,
                        font=fonts["body"],
                    )
                    parar_recursao = True
                elif isinstance(widget, tk.Checkbutton):
                    widget.configure(
                        bg=cor_fundo,
                        fg=cor_texto,
                        activebackground=cor_fundo,
                        activeforeground=cor_texto,
                        selectcolor=cor_destaque,
                        highlightthickness=0,
                        bd=0,
                        relief=tk.FLAT,
                        font=fonts["body"],
                    )
                    parar_recursao = True
                elif isinstance(widget, tk.Radiobutton):
                    widget.configure(
                        bg=cor_fundo,
                        fg=cor_texto,
                        activebackground=cor_fundo,
                        activeforeground=cor_texto,
                        selectcolor=cor_destaque,
                        highlightthickness=0,
                        bd=0,
                        relief=tk.FLAT,
                        font=fonts["body"],
                    )
                    parar_recursao = True
                elif isinstance(widget, ttk.Combobox):
                    try:
                        widget.configure(style="Opera.TCombobox")
                    except Exception:
                        pass
                    parar_recursao = True
                elif isinstance(widget, ttk.Checkbutton):
                    try:
                        widget.configure(style="Opera.TCheckbutton")
                    except Exception:
                        pass
                    parar_recursao = True
                elif isinstance(widget, ttk.Radiobutton):
                    try:
                        widget.configure(style="Opera.TRadiobutton")
                    except Exception:
                        pass
                    parar_recursao = True
                elif isinstance(widget, tk.Frame) and not widget.__class__.__module__.startswith("customtkinter"):
                    widget.configure(bg=cor_fundo)
                    parar_recursao = False
                else:
                    _dprint(f"[Tema][DEBUG] Widget não tratado: {_describe_widget(widget)}")
            except Exception as e:
                _dprint(f"[Tema] Erro ao aplicar tema em widget {_describe_widget(widget)}: {e}")

            if not parar_recursao:
                try:
                    for child in widget.winfo_children():
                        _apply_to_all_widgets(child)
                except Exception:
                    pass

        _apply_to_all_widgets(root_widget)

    def _apply_global_theme(self, palette: dict):
        try:
            self._apply_palette_to_widget(self.app, palette, self.fonts)
            from PAGINAS_DO_SISTEMA.TEMAS import (
                padronizar_treeviews_container,
                remover_bordas_botoes_tema,
            )
            remover_bordas_botoes_tema(self.app)
            padronizar_treeviews_container(self.app)
        except Exception as e:
            _dprint(f"[Tema] Erro ao aplicar tema global: {e}")

    def apply_theme_to_widget(self, widget):
        if widget is None:
            return
        from PAGINAS_DO_SISTEMA.TEMAS import TemasPage
        palette = self.current_palette or {}
        if not palette:
            palette = TemasPage.PADROES.get(self.current_theme_name or "CLÁSSICO CLARO", {})
        if not palette:
            _dprint("[Tema] Nenhuma paleta disponível para aplicar no widget.")
            return
        try:
            from PAGINAS_DO_SISTEMA.TEMAS import padronizar_treeviews_container
            self._apply_palette_to_widget(widget, palette, self.fonts)
            padronizar_treeviews_container(widget)
            _dprint(f"[Tema] Tema '{self.current_theme_name}' aplicado ao widget {widget.__class__.__name__}.")
        except Exception as e:
            _dprint(f"[Tema] Não foi possível aplicar tema ao widget {widget}: {e}")

    def _realcar_cor(self, hex_color: str, factor: float = 1.2) -> str:
        try:
            h = hex_color.lstrip("#")
            if len(h) == 3:
                h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            r = min(255, int(r * factor))
            g = min(255, int(g * factor))
            b = min(255, int(b * factor))
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color

    def _persist_theme_choice(self, theme_name: str, palette: dict):
        try:
            settings = ConfigManager.load_settings()
            settings["theme"] = theme_name
            settings["last_palette"] = palette
            ConfigManager.save_settings(settings)
        except Exception as e:
            _dprint(f"[Tema] Não foi possível salvar preferências locais: {e}")

    def _rebuild_interface(self):
        try:
            app = self.app
            _dprint("🔄 Reconstruindo interface com novo tema...")
            if hasattr(app, 'sidebar'):
                app.sidebar.destroy()
            if hasattr(app, 'main'):
                app.main.destroy()
            if hasattr(app, 'submenu_frames'):
                for categoria, frame in list(app.submenu_frames.items()):
                    try:
                        frame.destroy()
                    except Exception:
                        pass
                app.submenu_frames.clear()
            if hasattr(app, 'botoes_menu'):
                app.botoes_menu.clear()
            if hasattr(app, "_page_cache"):
                for cached_frame in list(app._page_cache.values()):
                    try:
                        cached_frame.destroy()
                    except Exception:
                        pass
                app._page_cache.clear()
                app._page_cache_order = []
                app._current_frame = None
            app._build_interface()
            try:
                from PAGINAS_DO_SISTEMA.TEMAS import remover_bordas_botoes_tema
                remover_bordas_botoes_tema(app)
            except Exception as e:
                _dprint("[Tema] Falha ao remover bordas após reconstrução:", e)
            if hasattr(app, '_update_user_display'):
                app._update_user_display()
            if hasattr(app, 'current_page') and app.current_page:
                app._agendar_after(500, lambda: app.open_page(app.current_page))
        except Exception as e:
            _dprint(f"[Tema] Erro ao reconstruir interface: {e}")

    def _create_submenu_item(self, parent, categoria: str, item: str):
        item_frame = ctk.CTkFrame(parent, fg_color="transparent")
        item_frame.pack(fill="x", padx=2, pady=1)

        icon = self._get_submenu_icon(categoria, item)
        style = self._get_menu_style_tokens()

        btn = ctk.CTkButton(
            item_frame,
            text=f"  {self._translate_menu_label(item)}",
            image=icon,
            compound="left",
            anchor="w",
            fg_color=style["submenu_bg"],
            hover=False,
            text_color=style["submenu_texto"],
            text_color_hover=style["submenu_texto"],
            text_color_disabled=style["submenu_texto"],
            font=("Arial", max(11, int(13 * getattr(self, "ui_scale", 1.0)))),
            height=max(32, int(36 * getattr(self, "ui_scale", 1.0))),
            corner_radius=6,
            border_width=0,
            command=lambda i=item: self._on_submenu_click(categoria, i)
        )
        btn._opera_submenu_button = True
        btn.pack(fill="x", expand=True, padx=4, pady=2)

    def _update_menu_buttons_colors(self):
        try:
            style = self._get_menu_style_tokens()

            for categoria, btn_frame in self.botoes_menu.items():
                if not btn_frame.winfo_exists():
                    continue

                for child in btn_frame.winfo_children():
                    if not isinstance(child, ctk.CTkButton):
                        continue

                    ativo = (categoria == self._active_submenu)

                    if ativo:
                        fg = style["hover_bg"]
                        txt = style["hover_texto"]
                    else:
                        fg = style["menu_bg"]
                        txt = style["menu_texto"]

                    child.configure(
                        fg_color=fg,
                        hover=False,
                        text_color=txt,
                        text_color_hover=txt,
                        text_color_disabled=txt,
                        border_color=self.cor_borda,
                        border_width=1,
                    )

            for _, submenu_frame in self.submenu_frames.items():
                if not submenu_frame.winfo_exists():
                    continue

                submenu_frame.configure(
                    fg_color=style["submenu_painel_bg"],
                    border_color=self.cor_borda,
                    border_width=1,
                )

                for inner_frame in submenu_frame.winfo_children():
                    if isinstance(inner_frame, ctk.CTkFrame):
                        for btn_container in inner_frame.winfo_children():
                            if isinstance(btn_container, ctk.CTkFrame):
                                for btn in btn_container.winfo_children():
                                    if isinstance(btn, ctk.CTkButton):
                                        btn.configure(
                                            fg_color=style["submenu_bg"],
                                            hover=False,
                                            text_color=style["submenu_texto"],
                                            text_color_hover=style["submenu_texto"],
                                            text_color_disabled=style["submenu_texto"],
                                            border_width=0,
                                        )
            _dprint("[Tema] Cores do menu e submenu atualizadas.")
        except Exception as e:
            _dprint(f"[Tema] Erro ao atualizar cores do menu: {e}")


class UserManager:
    def __init__(self, app=None, usuario_id=None, usuario_nome=None, usuario_hierarquia=None):
        self.app = app
        self.usuario_id = usuario_id
        self.usuario_nome = usuario_nome or "Admin"
        self.usuario_hierarquia = usuario_hierarquia or "Administrador"
        self.permissoes = {}
        _dprint(f"[UserManager] Iniciado para usuário: {self.usuario_nome} ({self.usuario_hierarquia})")

    def load_user_theme_completo(self):
        import json
        default_theme = "CLÁSSICO CLARO"
        try:
            if not getattr(self.app, "usuario_id", None):
                _dprint("[UserManager][DEBUG] usuario_id não definido ao carregar tema completo; usando padrão")
                return default_theme, None

            schema = get_schema()
            query = f"""
                SELECT
                    COALESCE(up.tema_nome, u.tema_preferido, %s) AS tema_nome,
                    up.usar_tema_personalizado,
                    up.tema_personalizado
                FROM {schema}.usuarios u
                LEFT JOIN {schema}.usuario_preferencias up ON u.id = up.usuario_id
                WHERE u.id = %s
            """

            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(query, (default_theme, self.app.usuario_id))
                row = cur.fetchone()

            if not row:
                _dprint(
                    f"[UserManager][DEBUG] Nenhum registro de preferências encontrado para usuario_id={self.app.usuario_id}; "
                    "usando tema padrão"
                )
                return default_theme, None

            tema_nome, usar_custom, tema_json = row
            if usar_custom and tema_json:
                try:
                    paleta = json.loads(tema_json)
                    _dprint(f"[Tema] Paleta personalizada carregada para {self.app.usuario_nome}.")
                    return tema_nome, paleta
                except json.JSONDecodeError:
                    _dprint(
                        f"[Tema][ERRO] JSON inválido no tema_personalizado para usuario_id={self.app.usuario_id}: {tema_json}"
                    )

            return tema_nome, None

        except Exception as e:
            _dprint(f"[UserManager][AVISO] Banco indisponível ao carregar tema do usuário: {e}")
            return default_theme, None

    def save_user_theme(self, theme_name: str):
        if not getattr(self.app, "usuario_id", None):
            _dprint("[UserManager][DEBUG] usuario_id ausente ao salvar tema padrão; operação ignorada")
            return
        schema = get_schema()
        try:
            _dprint(
                f"[UserManager][DEBUG] Gravando tema padrão '{theme_name}' para usuario_id={self.app.usuario_id} no schema {schema}"
            )
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {schema}.usuario_preferencias
                        (usuario_id, tema_nome, usar_tema_personalizado)
                    VALUES (%s, %s, FALSE)
                    ON CONFLICT (usuario_id)
                    DO UPDATE SET
                        tema_nome = EXCLUDED.tema_nome,
                        usar_tema_personalizado = FALSE,
                        tema_personalizado = NULL
                """, (self.app.usuario_id, theme_name))
                conn.commit()
            _dprint("[UserManager][DEBUG] Tema padrão salvo com sucesso")
        except Exception as e:
            _dprint(f"[UserManager][ERRO] Falha ao salvar tema padrão '{theme_name}': {e}")

    def save_user_theme_personalizado(self, theme_name: str, palette_json: str):
        if not getattr(self.app, "usuario_id", None):
            _dprint("[UserManager][DEBUG] usuario_id ausente ao salvar tema personalizado; operação ignorada")
            return
        schema = get_schema()
        try:
            _dprint(
                f"[UserManager][DEBUG] Gravando tema personalizado '{theme_name}' (len={len(palette_json) if palette_json else 0}) "
                f"para usuario_id={self.app.usuario_id} no schema {schema}"
            )
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {schema}.usuario_preferencias
                        (usuario_id, tema_nome, usar_tema_personalizado, tema_personalizado)
                    VALUES (%s, %s, TRUE, %s)
                    ON CONFLICT (usuario_id)
                    DO UPDATE SET
                        tema_nome = EXCLUDED.tema_nome,
                        usar_tema_personalizado = TRUE,
                        tema_personalizado = EXCLUDED.tema_personalizado
                """, (self.app.usuario_id, theme_name, palette_json))
                conn.commit()
            _dprint("[UserManager][DEBUG] Tema personalizado salvo com sucesso")
        except Exception as e:
            _dprint(f"[UserManager][ERRO] Falha ao salvar tema personalizado '{theme_name}': {e}")

    def _is_admin(self) -> bool:
        try:
            hierarquia = getattr(self.app, "usuario_hierarquia", "")
            if hierarquia and str(hierarquia).strip().lower() in ("admin", "administrador", "superusuario"):
                return True
            return False
        except Exception as e:
            _dprint(f"[UserManager] Erro ao verificar se é admin: {e}")
            return False

    def load_user_permissions(self):
        if not self.usuario_id:
            _dprint("[Permissões] ⚠️ Nenhum usuário definido — permissões não carregadas.")
            self.permissoes = {}
            return {}
        try:
            schema = get_schema()
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(f"""
                    SELECT 
                        codigo,
                        pode_ver,
                        pode_editar,
                        pode_imprimir,
                        pode_excluir,
                        pode_administrar
                    FROM {schema}.usuario_permissoes
                    WHERE usuario_id = %s
                """, (self.usuario_id,))
                rows = cur.fetchall()
            self.permissoes = {
                row[0]: {
                    "ver": row[1],
                    "editar": row[2],
                    "imprimir": row[3],
                    "excluir": row[4],
                    "administrar": row[5]
                }
                for row in rows
            }
            _dprint(f"[Permissões] {len(self.permissoes)} permissões carregadas para '{self.usuario_nome}'.")
            return self.permissoes
        except Exception as e:
            _dprint(f"[Permissões] ❌ Erro ao carregar permissões: {e}")
            self.permissoes = {}
            return {}

    def has_permission(self, pagina: str, acao: str = "ver", categoria: str | None = None) -> bool:
        if self.usuario_hierarquia and self.usuario_hierarquia.lower() in ("admin", "administrador"):
            return True
        permissoes = getattr(self.app, "permissoes_usuario", {})
        page_map = getattr(self.app.__class__, "PAGE_PERMISSION_MAP", {})
        codigo = None
        if categoria:
            codigo = page_map.get(f"{categoria}:{pagina}")
        if not codigo:
            codigo = page_map.get(pagina)
        if not codigo:
            return True
        if codigo in {"dashboard", "config_temas"}:
            return True
        perm = permissoes.get(codigo)
        if not perm:
            return False
        return bool(perm.get(acao, False))


# ===== APLICAÇÃO PRINCIPAL =====
class OperaMenuApp(ctk.CTk):
    """Aplicação principal do sistema OPERA."""

    SIDEBAR_WIDTH = 300
    ITEM_HEIGHT = 40
    TOPBAR_HEIGHT = 48

    ICON_MAPPING = {
        "Dashboard": "DASHBORD.png",
        "MODELOS": "ROUPA.png",
        "ORDENS DE CORTE": "TESOURA.png",
        "REGISTRO DE CORTE": "FOLHA DE PAPEL.png",
        "ESTOQUE": "ESTOQUE.png",
        "COMPRAS": "DINHEIRO.png",
        "COMERCIAL": "USUARIOS.png",
        "PRESTADORES": "FABRICA.png",
        "MÃO DE OBRA": "PESSOAS.png",
        "PRODUÇÃO": "PRODUÇAO.png",
        "ACABAMENTO": "FERRAMENTAS.png",
        "FINANCEIRO": "DINHEIRO.png",
        "PLANEJAMENTO": "RELATORIO.png",
        "RELATÓRIOS": "RELATORIO.png",
        "CONFIGURAÇÕES": "ENGRENAGEM.png",
        "BANCO DE DADOS": "BANCO DE DADOS.png",
    }

    MENU_ESTRUTURA = {
        "Dashboard": ["Dashboard"],
        "MODELOS": ["Cadastrar Modelo", "Imprimir Ficha Técnica"],
        "ORDENS DE CORTE": ["Nova Ordem", "Ordens Planejadas", "Ordens de Corte Impressão"],
        "REGISTRO DE CORTE": ["Cadastrar Corte", "Consultar Ordens"],
        "MÃO DE OBRA": ["Controle de Mão de Obra"],
        "COMPRAS": ["Compras"],
        "ESTOQUE": ["Entrada de Estoque", "Saída de Estoque", "Relatórios"],
        "COMERCIAL": ["Clientes"],
        "PRESTADORES": ["Cadastro de Prestadores", "Pesquisar Serviço"],
        "ACABAMENTO": ["Registro Acabamento", "Finalizar Corte / Acabamento", "Retrabalho de Defeitos"],
        "PLANEJAMENTO": ["MRP", "Planejamento de Produção", "Custos Reais"],
        "FINANCEIRO": [
            "Pagamento de Serviços", "Recibos de Pagamentos", "Custo Produto", "Folha Pagamento",
            "Fechamento Mensal", "Contas a Pagar", "Adiantamento", "Adiantamentos Pendentes"
        ],
        "RELATÓRIOS": [
            "Produção",
            "Serviços Externos",
            "Modelos Produzidos",
            "Acabamento",
            "Logs e Atividades",
        ],
        "CONFIGURAÇÕES": ["Trocar Usuário", "Usuários", "Temas", "Atualizar Sistema"],
        "BANCO DE DADOS": ["Gerenciar", "Backup"],
    }

    SUBMENU_ICON_MAPPING = {
        "Dashboard": {"Dashboard": "DASHBORD.png"},
        "MODELOS": {"Cadastrar Modelo": "ROUPA.png", "Imprimir Ficha Técnica": "IMPRESSORA.png"},
        "ORDENS DE CORTE": {"Nova Ordem": "NOVA_ORDEM.png", "Ordens Planejadas": "RELATORIO.png",
                            "Ordens de Corte Impressão": "IMPRESSORA.png"},
        "REGISTRO DE CORTE": {"Cadastrar Corte": "CADASTRO_CORTE.png", "Consultar Ordens": "CONSULTAR ORDENS.png"},
        "COMPRAS": {"Compras": "DINHEIRO.png"},
        "ESTOQUE": {"Entrada de Estoque": "ESTOQUE.png", "Saída de Estoque": "ESTOQUE.png",
                    "Relatórios": "RELATORIO 2.png"},
        "COMERCIAL": {"Clientes": "USUARIOS.png"},
        "PRESTADORES": {"Cadastro de Prestadores": "FACÇAO.png", "Pesquisar Serviço": "CONSULTAR ORDENS.png"},
        "MÃO DE OBRA": {"Controle de Mão de Obra": "MAO DE OBRA.png"},
        "PLANEJAMENTO": {"MRP": "RELATORIO.png", "Planejamento de Produção": "PRODUÇAO.png",
                         "Custos Reais": "RELATORIO.png"},
        "PRODUÇÃO": {"Produção": "PRODUÇAO.png"},
        "ACABAMENTO": {"Registro Acabamento": "ACABAMENTO.png", "Finalizar Corte / Acabamento": "ACABAMENTO.png",
                       "Retrabalho de Defeitos": "ACABAMENTO.png"},
        "FINANCEIRO": {
            "Pagamento de Serviços": "DINHEIRO.png", "Recibos de Pagamentos": "IMPRESSORA.png",
            "Custo Produto": "DINHEIRO.png", "Folha Pagamento": "DINHEIRO.png",
            "Fechamento Mensal": "DINHEIRO.png", "Contas a Pagar": "DINHEIRO.png",
            "Adiantamento": "DINHEIRO.png", "Adiantamentos Pendentes": "DINHEIRO.png"
        },
        "RELATÓRIOS": {
            "Produção": "PRODUÇAO.png", "Serviços Externos": "SERVIÇOS EXTERNOS.png",
            "Modelos Produzidos": "MODELOS PRODUZIDOS.png", "Acabamento": "ACABAMENTO.png",
            "Logs e Atividades": "RELATORIO.png"
        },
        "CONFIGURAÇÕES": {
            "Trocar Usuário": "TROCAR_USUARIO.png", "Usuários": "USUARIOS.png",
            "Backup": "BACKUP.png", "Temas": "PALETA DE CORES.png", "Atualizar Sistema": "ENGRENAGEM.png"
        },
        "BANCO DE DADOS": {"Gerenciar": "ENGRENAGEM.png", "Backup": "BACKUP.png"},
    }

    PAGE_PERMISSION_MAP = {
        "Dashboard": "dashboard",
        "Cadastrar Modelo": "cadastro_modelos",
        "Imprimir Ficha Técnica": "ficha_tecnica",
        "Nova Ordem": "ordem_corte",
        "Ordens Planejadas": "ordem_corte",
        "Ordens de Corte Impressão": "ordem_corte_impressao",
        "Cadastrar Corte": "cadastro_corte",
        "Consultar Ordens": "consultar_ordens",
        "Entrada de Estoque": "estoque_entrada",
        "Saída de Estoque": "estoque_saida",
        "Relatórios": "estoque_relatorios",
        "Cadastro de Prestadores": "cadastro_faccoes",
        "Pesquisar Serviço": "pesquisar_servico",
        "Controle de Mão de Obra": "controle_mao_obra",
        "Retrabalho de Defeitos": "retrabalho_defeitos",
        "Produção": "Producao",
        "Registro Acabamento": "registro_acabamento",
        "Finalizar Corte / Acabamento": "finalizar_corte",
        "Pagamento de Serviços": "pagamento_servicos",
        "Recibos de Pagamentos": "recibos_pagamentos",
        "Custo Produto": "custo_produto",
        "Folha Pagamento": "folha_pagamento",
        "Fechamento Mensal": "fechamento_mensal",
        "Contas a Pagar": "contas_pagar",
        "Adiantamento": "adiantamento",
        "Adiantamentos Pendentes": "adiantamentos_pendentes",
        "RELATÓRIOS:Produção": "relatorio_Producao",
        "Serviços Externos": "relatorio_servicos_externos",
        "Modelos Produzidos": "relatorio_modelos_produzidos",
        "Acabamento": "relatorio_acabamento",
        "Logs e Atividades": "config_usuarios",
        "Trocar Usuário": "trocar_usuario",
        "Usuários": "config_usuarios",
        "Backup": "config_backup",
        "Temas": "config_temas",
        "Atualizar Sistema": "config_atualizacao",
        "Gerenciar": "banco_dados",
    }

    SUPPORTED_LANGUAGES = {
        "pt_BR": "Português (Brasil)",
        "en_US": "English (US)",
        "es_ES": "Español",
    }

    UI_TEXTS = {
        "pt_BR": {
            "system_title": "SISTEMA OPERA",
            "main_menu": "Menu Principal",
            "topbar_dashboard": "Dashboard",
            "language": "Idioma",
            "current_language": "Idioma atual",
            "refresh_page": "Atualizar página",
            "switch_user": "Trocar usuário",
            "loading": "Carregando...",
            "error": "Erro",
            "exit_title": "Sair",
            "exit_confirm": "Deseja realmente sair do sistema?",
            "yes": "Sim",
            "no": "Não",
            "language_changed": "Idioma alterado para {language}",
            "no_permission": "Sem permissão para acessar {page}",
            "clock_format": "%d/%m/%Y %H:%M:%S",
        },
        "en_US": {
            "system_title": "OPERA SYSTEM",
            "main_menu": "Main Menu",
            "topbar_dashboard": "Dashboard",
            "language": "Language",
            "current_language": "Current language",
            "refresh_page": "Refresh page",
            "switch_user": "Switch user",
            "loading": "Loading...",
            "error": "Error",
            "exit_title": "Exit",
            "exit_confirm": "Do you really want to exit the system?",
            "yes": "Yes",
            "no": "No",
            "language_changed": "Language changed to {language}",
            "no_permission": "No permission to access {page}",
            "clock_format": "%m/%d/%Y %I:%M:%S %p",
        },
        "es_ES": {
            "system_title": "SISTEMA OPERA",
            "main_menu": "Menú Principal",
            "topbar_dashboard": "Panel",
            "language": "Idioma",
            "current_language": "Idioma actual",
            "refresh_page": "Actualizar página",
            "switch_user": "Cambiar usuario",
            "loading": "Cargando...",
            "error": "Error",
            "exit_title": "Salir",
            "exit_confirm": "¿Realmente desea salir del sistema?",
            "yes": "Sí",
            "no": "No",
            "language_changed": "Idioma cambiado a {language}",
            "no_permission": "Sin permiso para acceder a {page}",
            "clock_format": "%d/%m/%Y %H:%M:%S",
        },
    }

    MENU_LABELS = {
        "Dashboard": {"pt_BR": "Dashboard", "en_US": "Dashboard", "es_ES": "Panel"},
        "MODELOS": {"pt_BR": "MODELOS", "en_US": "MODELS", "es_ES": "MODELOS"},
        "ORDENS DE CORTE": {"pt_BR": "ORDENS DE CORTE", "en_US": "CUT ORDERS", "es_ES": "ÓRDENES DE CORTE"},
        "REGISTRO DE CORTE": {"pt_BR": "REGISTRO DE CORTE", "en_US": "CUT RECORDS", "es_ES": "REGISTRO DE CORTE"},
        "MÃO DE OBRA": {"pt_BR": "MÃO DE OBRA", "en_US": "LABOR", "es_ES": "MANO DE OBRA"},
        "COMPRAS": {"pt_BR": "COMPRAS", "en_US": "PURCHASING", "es_ES": "COMPRAS"},
        "ESTOQUE": {"pt_BR": "ESTOQUE", "en_US": "INVENTORY", "es_ES": "STOCK"},
        "COMERCIAL": {"pt_BR": "COMERCIAL", "en_US": "SALES", "es_ES": "COMERCIAL"},
        "PRESTADORES": {"pt_BR": "PRESTADORES", "en_US": "PROVIDERS", "es_ES": "PRESTADORES"},
        "ACABAMENTO": {"pt_BR": "ACABAMENTO", "en_US": "FINISHING", "es_ES": "ACABADO"},
        "PLANEJAMENTO": {"pt_BR": "PLANEJAMENTO", "en_US": "PLANNING", "es_ES": "PLANIFICACIÓN"},
        "FINANCEIRO": {"pt_BR": "FINANCEIRO", "en_US": "FINANCIAL", "es_ES": "FINANZAS"},
        "RELATÓRIOS": {"pt_BR": "RELATÓRIOS", "en_US": "REPORTS", "es_ES": "INFORMES"},
        "CONFIGURAÇÕES": {"pt_BR": "CONFIGURAÇÕES", "en_US": "SETTINGS", "es_ES": "CONFIGURACIÓN"},
        "BANCO DE DADOS": {"pt_BR": "BANCO DE DADOS", "en_US": "DATABASE", "es_ES": "BASE DE DATOS"},
        "Cadastrar Modelo": {"pt_BR": "Cadastrar Modelo", "en_US": "Register Model", "es_ES": "Registrar Modelo"},
        "Imprimir Ficha Técnica": {"pt_BR": "Imprimir Ficha Técnica", "en_US": "Print Technical Sheet",
                                   "es_ES": "Imprimir Ficha Técnica"},
        "Nova Ordem": {"pt_BR": "Nova Ordem", "en_US": "New Order", "es_ES": "Nueva Orden"},
        "Ordens Planejadas": {"pt_BR": "Ordens Planejadas", "en_US": "Planned Orders", "es_ES": "Órdenes Planificadas"},
        "Ordens de Corte Impressão": {"pt_BR": "Ordens de Corte Impressão", "en_US": "Print Cut Orders",
                                      "es_ES": "Impresión de Órdenes"},
        "Cadastrar Corte": {"pt_BR": "Cadastrar Corte", "en_US": "Register Cut", "es_ES": "Registrar Corte"},
        "Consultar Ordens": {"pt_BR": "Consultar Ordens", "en_US": "Consult Orders", "es_ES": "Consultar Órdenes"},
        "Controle de Mão de Obra": {"pt_BR": "Controle de Mão de Obra", "en_US": "Labor Control",
                                    "es_ES": "Control de Mano de Obra"},
        "Compras": {"pt_BR": "Compras", "en_US": "Purchases", "es_ES": "Compras"},
        "Entrada de Estoque": {"pt_BR": "Entrada de Estoque", "en_US": "Stock Entry", "es_ES": "Entrada de Stock"},
        "Saída de Estoque": {"pt_BR": "Saída de Estoque", "en_US": "Stock Output", "es_ES": "Salida de Stock"},
        "Relatórios": {"pt_BR": "Relatórios", "en_US": "Reports", "es_ES": "Informes"},
        "Clientes": {"pt_BR": "Clientes", "en_US": "Clients", "es_ES": "Clientes"},
        "Cadastro de Prestadores": {"pt_BR": "Cadastro de Prestadores", "en_US": "Providers Register",
                                    "es_ES": "Registro de Prestadores"},
        "Pesquisar Serviço": {"pt_BR": "Pesquisar Serviço", "en_US": "Search Service", "es_ES": "Buscar Servicio"},
        "Registro Acabamento": {"pt_BR": "Registro Acabamento", "en_US": "Finishing Record",
                                "es_ES": "Registro de Acabado"},
        "Finalizar Corte / Acabamento": {"pt_BR": "Finalizar Corte / Acabamento", "en_US": "Finalize Cut / Finishing",
                                         "es_ES": "Finalizar Corte / Acabado"},
        "Retrabalho de Defeitos": {"pt_BR": "Retrabalho de Defeitos", "en_US": "Defect Rework",
                                   "es_ES": "Retrabajo de Defectos"},
        "MRP": {"pt_BR": "MRP", "en_US": "MRP", "es_ES": "MRP"},
        "Planejamento de Produção": {"pt_BR": "Planejamento de Produção", "en_US": "Production Planning",
                                     "es_ES": "Planificación de Producción"},
        "Custos Reais": {"pt_BR": "Custos Reais", "en_US": "Actual Costs", "es_ES": "Costos Reales"},
        "Pagamento de Serviços": {"pt_BR": "Pagamento de Serviços", "en_US": "Service Payments",
                                  "es_ES": "Pago de Servicios"},
        "Recibos de Pagamentos": {"pt_BR": "Recibos de Pagamentos", "en_US": "Payment Receipts",
                                  "es_ES": "Recibos de Pago"},
        "Custo Produto": {"pt_BR": "Custo Produto", "en_US": "Product Cost", "es_ES": "Costo del Producto"},
        "Folha Pagamento": {"pt_BR": "Folha Pagamento", "en_US": "Payroll", "es_ES": "Nómina"},
        "Fechamento Mensal": {"pt_BR": "Fechamento Mensal", "en_US": "Monthly Closing", "es_ES": "Cierre Mensual"},
        "Contas a Pagar": {"pt_BR": "Contas a Pagar", "en_US": "Accounts Payable", "es_ES": "Cuentas por Pagar"},
        "Adiantamento": {"pt_BR": "Adiantamento", "en_US": "Advance", "es_ES": "Adelanto"},
        "Adiantamentos Pendentes": {"pt_BR": "Adiantamentos Pendentes", "en_US": "Pending Advances",
                                    "es_ES": "Adelantos Pendientes"},
        "Produção": {"pt_BR": "Produção", "en_US": "Production", "es_ES": "Producción"},
        "Serviços Externos": {"pt_BR": "Serviços Externos", "en_US": "External Services",
                              "es_ES": "Servicios Externos"},
        "Modelos Produzidos": {"pt_BR": "Modelos Produzidos", "en_US": "Produced Models",
                               "es_ES": "Modelos Producidos"},
        "Logs e Atividades": {"pt_BR": "Logs e Atividades", "en_US": "Logs and Activities",
                              "es_ES": "Registros y Actividades"},
        "Trocar Usuário": {"pt_BR": "Trocar Usuário", "en_US": "Switch User", "es_ES": "Cambiar Usuario"},
        "Usuários": {"pt_BR": "Usuários", "en_US": "Users", "es_ES": "Usuarios"},
        "Temas": {"pt_BR": "Temas", "en_US": "Themes", "es_ES": "Temas"},
        "Atualizar Sistema": {"pt_BR": "Atualizar Sistema", "en_US": "Update System", "es_ES": "Actualizar Sistema"},
        "Gerenciar": {"pt_BR": "Gerenciar", "en_US": "Manage", "es_ES": "Gestionar"},
        "Backup": {"pt_BR": "Backup", "en_US": "Backup", "es_ES": "Respaldo"},
    }

    def __init__(self, usuario_id=None, usuario_nome="Admin", usuario_hierarquia="Administrador", tema_preferido=None):
        reset_tk_default_root()
        super().__init__()
        try:
            self.withdraw()
        except Exception:
            pass

        self._preload_complete = False
        initialize_after_guard(self)

        self._current_ui_scale = None
        self._pending_responsive_job = None
        self._responsive_reflow_lock = False
        self._window_scale_applied = False
        self._startup_responsive_ready = False
        self._last_configure_size = None
        self._last_resize_seen = None
        self._last_responsive_signature = None
        self._menu_layout_signature = None

        self.cor_fundo = "#1e1e1e"
        self.cor_primaria = "#2d2d30"
        self.cor_secundaria = "#3e3e42"
        self.cor_terciaria = "#252526"
        self.cor_texto = "#cccccc"
        self.cor_borda = "#404040"
        self.cor_hover = "#4a4a4a"
        self.cor_sucesso = "#107c10"
        self.cor_alerta = "#a1260d"
        self.cor_destaque = "#007acc"
        self.cor_selecao = "#007acc"
        self.cor_texto_secundario = "#888888"

        if not usuario_id:
            self.usuario_id = 0
            self.usuario_nome = "Administrador Local"
            self.usuario_hierarquia = "Admin"
            _dprint("⚙️ Execução direta detectada — modo Admin.")
        else:
            self.usuario_id = usuario_id
            self.usuario_nome = usuario_nome
            self.usuario_hierarquia = usuario_hierarquia

        self.settings = ConfigManager.load_settings()
        self.routes = ConfigManager.load_routes()
        ConfigManager.ensure_icons_directory()
        self.tema_preferido_inicial = tema_preferido or self.settings.get("theme") or "CLÁSSICO CLARO"
        self.idioma_atual = self.settings.get("language") or "pt_BR"
        if self.idioma_atual not in self.SUPPORTED_LANGUAGES:
            self.idioma_atual = "pt_BR"

        self.theme_manager = ThemeManager(self)
        self._theme_manager = self.theme_manager

        self.user_manager = UserManager()
        self.user_manager.app = self
        self.user_manager.usuario_id = self.usuario_id
        self.user_manager.usuario_nome = self.usuario_nome
        self.user_manager.usuario_hierarquia = self.usuario_hierarquia

        self._closing = False
        self._page_loading = False
        self.current_theme_name = None
        self.current_page = None
        self.submenu_frames = {}
        self.botoes_menu = {}
        self._submenu_close_jobs = {}
        self.icons_cache = {}
        self._icon_size_signature = None
        self._active_submenu = None
        self._submenu_timer = None
        self._page_cache = {}
        self._page_cache_order = []
        self._page_cache_size = self._resolve_page_cache_size()
        self._current_frame = None
        self._backup_launch_scheduled = False
        self.permissoes_usuario = {}

        self._calculate_initial_scale_and_fonts()
        self._setup_window()
        _dprint("🎨 Iniciando carregamento do tema...")
        self._load_initial_theme()
        self._load_icons()
        self._build_interface()
        self._load_user_permissions()
        self._setup_bindings()
        self._setup_activity_logging()
        self._setup_responsive_watcher()
        self._preload_complete = True

        self._show_startup_loading()
        self.deiconify()
        self.lift()
        self.focus_force()
        self._apply_initial_layout()
        self._agendar_after(10, self._startup_open_initial_page)
        self._agendar_after(220, lambda: self._apply_theme_to_frame_safely(self._current_frame))
        self._agendar_after(350, self._enable_startup_responsive_ready)
        self._agendar_after(2500, self._smart_preload_pages)
        self._agendar_after(100, self._update_user_display)
        self._agendar_after(5000, self._ativar_backup_silencioso)
        self._update_menu_buttons_colors()

        _dprint(f"✅ Sistema inicializado para: {self.usuario_nome} ({self.usuario_hierarquia})")
        _dprint(f"🎨 Tema aplicado: {self.current_theme_name}")

    def _calculate_initial_scale_and_fonts(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        base = min(screen_width / 1920.0, screen_height / 1080.0)
        if screen_width <= 1320 or screen_height <= 720:
            self.ui_scale = max(0.68, min(0.78, round(base, 3)))
        elif screen_width <= 1366 or screen_height <= 768:
            self.ui_scale = max(0.72, min(0.84, round(base, 3)))
        else:
            self.ui_scale = max(0.74, min(1.0, round(base, 3)))
        try:
            ctk.set_widget_scaling(self.ui_scale)
            ctk.set_window_scaling(max(0.70, self.ui_scale))
        except Exception as e:
            _dprint(f"⚠️ Erro ao aplicar escala: {e}")
        self.SIDEBAR_WIDTH = max(220, int(300 * self.ui_scale))
        self.ITEM_HEIGHT = max(32, int(40 * self.ui_scale))
        self.TOPBAR_HEIGHT = max(36, int(48 * self.ui_scale))
        self.font_sidebar_titulo = ("Arial", max(14, int(22 * self.ui_scale)), "bold")
        self.font_sidebar_subtitulo = ("Arial", max(11, int(16 * self.ui_scale)))
        self.font_topbar_titulo = ("Arial", max(14, int(26 * self.ui_scale)))
        self.font_topbar_icone = ("Arial", max(14, int(22 * self.ui_scale)))
        self.icon_size_sidebar = max(28, int(52 * self.ui_scale))

    def _resolve_page_cache_size(self) -> int:
        """Define cache adaptativo para equilibrar memória e velocidade."""
        forced = os.environ.get("OPERA_PAGE_CACHE_SIZE", "").strip()
        if forced.isdigit():
            return max(1, min(6, int(forced)))
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        cpu = max(1, int(os.cpu_count() or 1))
        if screen_width <= 1366 or screen_height <= 768 or cpu <= 4:
            return 2
        if screen_width >= 1920 and screen_height >= 1080 and cpu >= 8:
            return 4
        return 3

    def _apply_initial_layout(self):
        self._maximize_window()
        self.update_idletasks()

    def _enable_startup_responsive_ready(self):
        self._startup_responsive_ready = True

    def _show_startup_loading(self):
        """Mostra um painel leve enquanto a primeira página ainda está carregando."""
        try:
            if not hasattr(self, "content") or not self.content.winfo_exists():
                return
            for widget in self.content.winfo_children():
                try:
                    widget.destroy()
                except Exception:
                    pass
            card = ctk.CTkFrame(
                self.content,
                fg_color=self.cor_secundaria,
                corner_radius=14,
                border_color=self.cor_borda,
                border_width=1,
            )
            card.place(relx=0.5, rely=0.5, anchor="center")
            ctk.CTkLabel(
                card,
                text=self._get_text("system_title"),
                font=("Arial", 18, "bold"),
                text_color=self.cor_texto,
            ).pack(padx=24, pady=(20, 8))
            ctk.CTkLabel(
                card,
                text=self._get_text("loading_page"),
                font=("Arial", 14),
                text_color=self.cor_texto,
            ).pack(padx=24, pady=(0, 18))
            self._startup_loading_card = card
            self.update_idletasks()
        except Exception:
            self._startup_loading_card = None

    def _startup_open_initial_page(self):
        if getattr(self, "_closing", False):
            return

        def _do_open():
            if getattr(self, "_closing", False):
                return
            try:
                self._open_dashboard_agora()
            finally:
                try:
                    if getattr(self, "_startup_loading_card", None) and self._startup_loading_card.winfo_exists():
                        self._startup_loading_card.destroy()
                except Exception:
                    pass
                self._update_menu_buttons_colors()

        try:
            self.after_idle(_do_open)
        except Exception:
            _do_open()

    def _setup_responsive_watcher(self):
        self.bind("<Configure>", self._on_window_configure, add="+")

    def _on_window_configure(self, event):
        if event.widget is not self:
            return
        if not getattr(self, "_preload_complete", False):
            return
        if not getattr(self, "_startup_responsive_ready", False):
            return
        width = int(event.width or 0)
        height = int(event.height or 0)
        if width <= 1 or height <= 1:
            return
        size_key = (width, height)
        last_size = getattr(self, "_last_resize_seen", None)
        if last_size and abs(last_size[0] - width) < 8 and abs(last_size[1] - height) < 8:
            return
        self._last_resize_seen = size_key
        if self._pending_responsive_job:
            try:
                self.after_cancel(self._pending_responsive_job)
            except Exception:
                pass
            self._pending_responsive_job = None

        def _apply_resize():
            self._pending_responsive_job = None
            self._configure_responsive_layout(width=size_key[0], height=size_key[1])
            try:
                self._notify_current_page_resize(width=size_key[0], height=size_key[1])
            except Exception:
                pass

        self._pending_responsive_job = self.after(180, _apply_resize)

    def _calculate_ui_scale(self, width: int, height: int) -> float:
        if width < 1500 or height < 900:
            return 0.78
        return 1.0

    def _configure_responsive_layout(self, *, initial: bool = False, width: int | None = None,
                                     height: int | None = None):
        if getattr(self, "_responsive_reflow_lock", False) and not initial:
            return
        self._responsive_reflow_lock = True
        try:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            current_width = int(width or self.winfo_width() or screen_width)
            current_height = int(height or self.winfo_height() or screen_height)
            if initial or current_width <= 1 or current_height <= 1:
                current_width, current_height = screen_width, screen_height
            new_scale = self._calculate_ui_scale(current_width, current_height)
            layout_signature = (new_scale, current_width < 1500 or current_height < 900)
            if not initial and getattr(self, "_last_responsive_signature", None) == layout_signature:
                return
            self._last_responsive_signature = layout_signature
            self.ui_scale = new_scale
            self._responsive_mode = "compact" if new_scale < 1.0 else "normal"
            self.SIDEBAR_WIDTH = max(220, int(300 * self.ui_scale))
            self.ITEM_HEIGHT = max(32, int(40 * self.ui_scale))
            self.TOPBAR_HEIGHT = max(36, int(48 * self.ui_scale))
            self.font_sidebar_titulo = ("Arial", max(14, int(22 * self.ui_scale)), "bold")
            self.font_sidebar_subtitulo = ("Arial", max(11, int(16 * self.ui_scale)))
            self.font_topbar_titulo = ("Arial", max(14, int(26 * self.ui_scale)))
            self.font_topbar_icone = ("Arial", max(14, int(22 * self.ui_scale)))
            self.icon_size_sidebar = max(28, int(52 * self.ui_scale))
            if hasattr(self, "sidebar") and self.sidebar.winfo_exists():
                self.grid_columnconfigure(0, weight=0, minsize=self.SIDEBAR_WIDTH + 16)
                self.sidebar.configure(width=self.SIDEBAR_WIDTH)
            if hasattr(self, "topbar") and self.topbar.winfo_exists():
                self.topbar.configure(height=self.TOPBAR_HEIGHT)
            menu_signature = (self.SIDEBAR_WIDTH, self.ITEM_HEIGHT, self.icon_size_sidebar, self.idioma_atual)
            if hasattr(self, "menu_frame") and self.menu_frame.winfo_exists() and (
                initial or getattr(self, "_menu_layout_signature", None) != menu_signature
            ):
                self._menu_layout_signature = menu_signature
                self._hide_all_submenus()
                self._load_icons()
                self._build_menu_content()
            self.update_idletasks()
            if self._current_frame and getattr(self._current_frame, "winfo_exists", lambda: False)():
                try:
                    self._current_frame.place_configure(x=0, y=0, relwidth=1, relheight=1)
                except Exception:
                    pass
        finally:
            self._responsive_reflow_lock = False

    def _show_submenu(self, categoria: str):
        self._cancel_submenu_hide_timer()
        frame = self.submenu_frames.get(categoria)
        btn_frame = self.botoes_menu.get(categoria)
        if not frame or not btn_frame:
            return
        self.update_idletasks()
        for nome, outro_frame in self.submenu_frames.items():
            if nome != categoria:
                try:
                    outro_frame.place_forget()
                except Exception:
                    pass
        self._active_submenu = categoria
        self._update_menu_buttons_colors()
        root_x = self.winfo_rootx()
        root_y = self.winfo_rooty()
        btn_x = btn_frame.winfo_rootx() - root_x
        btn_y = btn_frame.winfo_rooty() - root_y
        btn_w = btn_frame.winfo_width()
        btn_h = btn_frame.winfo_height()
        frame.update_idletasks()
        frame_width = frame.winfo_width()
        frame_height = frame.winfo_reqheight()
        x = btn_x + btn_w + 4
        y = btn_y
        area_w = self.winfo_width()
        if x + frame_width > area_w - 10:
            x = btn_x - frame_width - 4
        if x < 10:
            x = 10
        area_h = self.winfo_height()
        if y + frame_height > area_h - 10:
            y = area_h - frame_height - 10
        if y < 10:
            y = 10
        frame.place(in_=self, x=x, y=y)
        frame.lift()
        frame.tkraise()

    def _resolve_theme_color(self, color, fallback: str) -> str:
        if isinstance(color, (tuple, list)) and color:
            try:
                modo = ctk.get_appearance_mode().lower()
            except Exception:
                modo = "dark"
            if len(color) >= 2:
                return str(color[1] if modo == "dark" else color[0])
            return str(color[0])
        if isinstance(color, str) and color.strip():
            return color
        return fallback

    def _is_dark_tk_color(self, color) -> bool:
        cor = self._resolve_theme_color(color, "#111827")
        return is_dark_color(cor)

    def _contrast_text_for_color(self, color, fallback: str = "#F8FAFC") -> str:
        cor = self._resolve_theme_color(color, "#111827")
        try:
            if cor.startswith("#") and len(cor) == 7:
                return get_contraste_texto(cor)
            r16, g16, b16 = self.winfo_rgb(cor)
            r, g, b = r16 / 65535.0, g16 / 65535.0, b16 / 65535.0
            luminancia = (0.299 * r + 0.587 * g + 0.114 * b)
            return "#000000" if luminancia > 0.5 else "#FFFFFF"
        except Exception:
            return get_contraste_texto(cor) or fallback

    def _get_menu_style_tokens(self) -> dict:
        pal = getattr(getattr(self, "theme_manager", None), "current_palette", None) or {}
        cor_secundaria = self._resolve_theme_color(pal.get("secundaria", self.cor_secundaria), self.cor_secundaria)
        cor_hover_base = self._resolve_theme_color(pal.get("hover", cor_secundaria), cor_secundaria)
        cor_borda = self._resolve_theme_color(pal.get("borda", self.cor_borda), self.cor_borda)
        cor_fundo = getattr(self, "cor_fundo", "#111827")
        tema_escuro = self._is_dark_tk_color(cor_secundaria) or self._is_dark_tk_color(cor_fundo)
        try:
            tema_escuro = tema_escuro or (self._theme_mode_from_name(getattr(self, "current_theme_name", "")) == "dark")
        except Exception:
            pass
        try:
            tema_escuro = tema_escuro or (ctk.get_appearance_mode().lower() == "dark")
        except Exception:
            pass

        if tema_escuro:
            menu_bg = self._realcar_cor(cor_secundaria, 1.06)
            submenu_bg = self._realcar_cor(cor_secundaria, 1.06)
            hover_bg = self._realcar_cor(cor_hover_base, 1.12)
            menu_texto = "#FFFFFF"
            hover_texto = "#FFFFFF"
            submenu_texto = "#FFFFFF"
        else:
            menu_bg = self._darker(cor_secundaria, 0.95)
            submenu_bg = self._darker(cor_secundaria, 0.95)
            hover_bg = self._darker(cor_hover_base, 0.82)
            menu_texto = self._contrast_text_for_color(menu_bg, fallback="#000000")
            hover_texto = self._contrast_text_for_color(hover_bg, fallback=menu_texto)
            submenu_texto = self._contrast_text_for_color(submenu_bg, fallback=menu_texto)

        return {
            "menu_bg": menu_bg,
            "menu_texto": menu_texto,
            "hover_bg": hover_bg,
            "hover_texto": hover_texto,
            "submenu_painel_bg": cor_secundaria,
            "submenu_bg": submenu_bg,
            "submenu_texto": submenu_texto,
            "submenu_hover_bg": hover_bg,
            "submenu_hover_texto": hover_texto,
            "cor_borda": cor_borda,
            "tema_escuro": tema_escuro,
        }

    def _open_dashboard_agora(self):
        try:
            if self.user_manager.has_permission("Dashboard", "ver"):
                _dprint("🚀 Abrindo Dashboard...")
                self.open_page("Dashboard")
            else:
                for pagina in self.routes.keys():
                    if self.user_manager.has_permission(pagina, "ver"):
                        _dprint(f"🚀 Abrindo '{pagina}'...")
                        self.open_page(pagina)
                        break
        except Exception as e:
            _dprint(f"⚠️ Erro ao abrir página inicial: {e}")

    def _smart_preload_pages(self):
        """Pré-carrega a última página usada só quando a UI já estabilizou."""
        if getattr(self, "_closing", False):
            return
        if str(os.environ.get("OPERA_PRELOAD_LAST_PAGE", "0")).strip().lower() not in {"1", "true", "yes", "on"}:
            return
        last_page = (self.settings or {}).get("last_page")
        if not last_page or last_page == self.current_page:
            return
        if last_page in self._page_cache:
            return
        if not self.user_manager.has_permission(last_page, "ver"):
            return

        def _do_preload():
            if getattr(self, "_page_loading", False) or getattr(self, "_closing", False):
                return
            try:
                frame = self._load_page_direct(last_page)
                if frame:
                    try:
                        frame.place_forget()
                    except Exception:
                        pass
                    self._cache_page(last_page, frame)
                    _dprint(f"⚡ Pré-cache da página '{last_page}' concluído")
            except Exception as exc:
                _dprint(f"⚠️ Pré-cache ignorado para '{last_page}': {exc}")

        self._agendar_after(600, _do_preload)

    def _setup_window(self):
        self.title("OPERA • Sistema de Gestão")
        try:
            if os.path.exists(ICONE_SISTEMA):
                icon_image = Image.open(ICONE_SISTEMA)
                self.iconphoto(True, ImageTk.PhotoImage(icon_image))
                _dprint("✅ Ícone do sistema carregado.")
        except Exception as e:
            _dprint(f"⚠️ Erro ao carregar ícone: {e}")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        if IS_WIN:
            self.geometry(f"{screen_width - 16}x{screen_height - 80}+0+0")
        elif IS_MAC:
            self.geometry(f"{screen_width - 20}x{screen_height - 120}+0+25")
        else:
            self.geometry(f"{screen_width - 16}x{screen_height - 80}+0+0")
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda e: self.ask_quit())
        self.minsize(min(900, screen_width), min(620, screen_height))

    def toggle_fullscreen(self, event=None):
        current_state = self.attributes('-fullscreen')
        self.attributes('-fullscreen', not current_state)

    def _maximize_window(self):
        try:
            if IS_MAC:
                self.attributes("-zoomed", True)
            else:
                self.state("zoomed")
        except tk.TclError:
            pass

    def ask_quit(self, event=None):
        if getattr(self, "_closing", False):
            return
        titulo_saida = self._get_text("exit_title")
        mensagem_saida = self._get_text("exit_confirm")
        confirmar = self._show_exit_dialog(titulo_saida, mensagem_saida)
        if confirmar:
            self._agendar_after(1, self.destroy)

    def _show_exit_dialog(self, titulo: str, mensagem: str) -> bool:
        resposta = {"ok": False}
        try:
            dlg = ctk.CTkToplevel(self)
            dlg.title(titulo)
            dlg.transient(self)
            dlg.resizable(False, False)
            dlg.grab_set()
            dlg.configure(fg_color=self.cor_fundo)
            w, h = 460, 230
            x = self.winfo_rootx() + max(20, (self.winfo_width() - w) // 2)
            y = self.winfo_rooty() + max(20, (self.winfo_height() - h) // 2)
            dlg.geometry(f"{w}x{h}+{x}+{y}")

            card = ctk.CTkFrame(dlg, fg_color=self.cor_secundaria, corner_radius=12, border_width=1, border_color=self.cor_borda)
            card.pack(fill="both", expand=True, padx=14, pady=14)

            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=18, pady=(16, 4))
            try:
                if os.path.exists(ICONE_SISTEMA):
                    img = Image.open(ICONE_SISTEMA).convert("RGBA")
                    logo = ctk.CTkImage(light_image=img, dark_image=img, size=(26, 26))
                    dlg._exit_logo = logo
                    ctk.CTkLabel(header, image=logo, text="").pack(side="left", padx=(0, 8))
            except Exception:
                pass

            ctk.CTkLabel(
                header,
                text=titulo,
                font=("Arial", 16, "bold"),
                text_color=self.cor_texto,
            ).pack(side="left")

            ctk.CTkLabel(
                card,
                text=mensagem,
                font=("Arial", 18, "bold"),
                text_color=self.cor_texto,
                wraplength=400,
                justify="center",
            ).pack(fill="x", padx=20, pady=(8, 22))

            botoes = ctk.CTkFrame(card, fg_color="transparent")
            botoes.pack(pady=(0, 16))

            def _set(v: bool):
                resposta["ok"] = v
                dlg.destroy()

            ctk.CTkButton(
                botoes,
                text=self._get_text("yes"),
                width=140,
                fg_color=self.cor_primaria,
                hover_color=self.cor_hover,
                text_color=self._contrast_text_for_color(self.cor_primaria, fallback="#FFFFFF"),
                font=("Arial", 14, "bold"),
                border_width=1,
                border_color=self.cor_borda,
                command=lambda: _set(True),
            ).pack(side="left", padx=8)
            ctk.CTkButton(
                botoes,
                text=self._get_text("no"),
                width=140,
                fg_color=self._darker(self.cor_secundaria, 0.97),
                hover_color=self._realcar_cor(self.cor_secundaria, 1.05),
                text_color=self._contrast_text_for_color(self.cor_secundaria, fallback=self.cor_texto),
                border_width=1,
                border_color=self.cor_borda,
                font=("Arial", 14, "bold"),
                command=lambda: _set(False),
            ).pack(side="left", padx=8)

            dlg.protocol("WM_DELETE_WINDOW", lambda: _set(False))
            self.wait_window(dlg)
            return bool(resposta["ok"])
        except Exception:
            try:
                return messagebox.askyesno(titulo, mensagem, parent=self)
            except Exception:
                return messagebox.askyesno(titulo, mensagem)

    def destroy(self):
        if getattr(self, "_closing", False):
            return
        self._closing = True
        try:
            cancel_all_afters(self)
            cancel_all_after_info(self)
        except Exception:
            pass
        try:
            self.withdraw()
            self.update_idletasks()
        except Exception:
            pass
        try:
            super().destroy()
        except Exception:
            pass
        try:
            import os
            os._exit(0)
        except Exception:
            pass

    def _setup_bindings(self):
        self.bind("<F5>", lambda e: self.reload_current_page())
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        if IS_WIN:
            self.bind("<Escape>", lambda e: self.ask_quit())
            self.bind("<Control-q>", lambda e: self.ask_quit())
        elif IS_MAC:
            self.bind("<Escape>", lambda e: self.ask_quit())
            self.bind("<Command-q>", lambda e: self.ask_quit())
            self.bind("<Command-f>", lambda e: self.toggle_fullscreen())
        try:
            self.protocol("WM_DELETE_WINDOW", self.ask_quit)
        except Exception:
            pass

    def _setup_activity_logging(self):
        self._activity_logger = get_logger(APP_DIR)
        self._activity_logger.set_usuario(self.usuario_nome, self.usuario_hierarquia)
        self._activity_logger.set_pagina(self.current_page or "MenuPrincipal")
        self._activity_log_cache = {}
        self._limpar_logs_antigos()
        self.bind_all("<ButtonRelease-1>", self._on_user_click, add="+")
        self.bind_all("<<TreeviewSelect>>", self._on_treeview_select, add="+")
        self.bind_all("<<ComboboxSelected>>", self._on_combobox_select, add="+")
        self.bind_all("<KeyRelease>", self._on_user_key, add="+")

    def _limpar_logs_antigos(self):
        try:
            self._activity_logger.limpar_logs_antigos(dias_manter=365)
        except Exception as e:
            _dprint(f"⚠️ Erro ao limpar logs em arquivo: {e}")
        if not MENU_POSTGRES_AVAILABLE or not ACTIVITY_DB_LOG_ENABLED:
            return
        try:
            schema = get_schema()
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {schema}.usuario_logs "
                    "WHERE data_hora < NOW() - INTERVAL '365 days'"
                )
                conn.commit()
        except Exception as e:
            _dprint(f"⚠️ Erro ao limpar logs no banco: {e}")

    def _log_user_activity(self, acao: str, detalhe: str = "", pagina: str | None = None):
        pagina_log = pagina or self.current_page or "MenuPrincipal"
        self._activity_logger.set_usuario(self.usuario_nome, self.usuario_hierarquia)
        self._activity_logger.set_pagina(pagina_log)
        detalhe_log = detalhe or ""
        if pagina_log and "Página:" not in detalhe_log:
            detalhe_log = f"Página: {pagina_log} | {detalhe_log}".strip(" |")
        self._activity_logger.log_usuario(acao, {"detalhe": detalhe_log, "pagina": pagina_log})
        if ACTIVITY_DB_LOG_ENABLED and LOGS_DISPONIVEIS and MENU_POSTGRES_AVAILABLE:
            try:
                registrar_log_db(self.usuario_nome, pagina_log, acao, detalhe_log)
            except Exception as e:
                _dprint(f"⚠️ Falha ao gravar log de atividade no banco: {e}")

    def _should_log_event(self, chave: str, intervalo: float = 0.4) -> bool:
        agora = time.monotonic()
        ultimo = self._activity_log_cache.get(chave, 0.0)
        if (agora - ultimo) < intervalo:
            return False
        self._activity_log_cache[chave] = agora
        return True

    def _on_user_click(self, event):
        widget = event.widget
        if not widget or widget is self:
            return
        try:
            widget_class = widget.winfo_class()
        except Exception:
            widget_class = ""
        clicavel = widget_class in {"Button", "TButton", "CTkButton"}
        has_command = False
        texto = ""
        if hasattr(widget, "cget"):
            try:
                texto = widget.cget("text")
            except Exception:
                texto = ""
            try:
                has_command = bool(widget.cget("command"))
            except Exception:
                has_command = False
        if not (clicavel or has_command):
            return
        acao = "Clique"
        detalhe = f"{widget_class}"
        if texto:
            detalhe = f"{widget_class} | {texto}"
        texto_upper = (texto or "").strip().upper()
        if any(palavra in texto_upper for palavra in ("SALVAR", "GRAVAR", "CADASTRAR", "ATUALIZAR")):
            acao = "Salvou"
        elif any(palavra in texto_upper for palavra in ("EXCLUIR", "APAGAR", "REMOVER", "DELETAR")):
            acao = "Apagou"
        elif any(palavra in texto_upper for palavra in ("EDITAR", "ALTERAR")):
            acao = "Editou"
        if self._should_log_event(f"click:{detalhe}"):
            self._log_user_activity(acao, detalhe)

    def _on_treeview_select(self, event):
        widget = event.widget
        if not widget:
            return
        try:
            selection = widget.selection()
            if not selection:
                return
            item_id = selection[0]
            valores = widget.item(item_id, "values")
            resumo = ", ".join(str(v) for v in valores[:3]) if valores else str(item_id)
        except Exception:
            return
        detalhe = f"Treeview | {resumo}"
        if self._should_log_event(f"tree:{detalhe}", intervalo=0.8):
            self._log_user_activity("Selecionou item", detalhe)

    def _on_combobox_select(self, event):
        widget = event.widget
        if not widget:
            return
        try:
            valor = widget.get()
        except Exception:
            return
        detalhe = f"Combobox | {valor}"
        if self._should_log_event(f"combo:{detalhe}"):
            self._log_user_activity("Selecionou opção", detalhe)

    def _on_user_key(self, event):
        keysym = event.keysym or ""
        if keysym in {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"}:
            return
        is_shortcut = bool(event.state & 0x4)
        is_action_key = keysym in {"Return", "F5", "F11", "Escape"}
        if not (is_shortcut or is_action_key):
            return
        detalhe = f"Tecla | {keysym}"
        if self._should_log_event(f"key:{detalhe}", intervalo=0.6):
            self._log_user_activity("Atalho", detalhe)

    def _load_initial_theme(self):
        try:
            _dprint("🔍 Buscando tema do usuário...")
            if not hasattr(self, 'usuario_id') or not self.usuario_id:
                _dprint("⚙️ Modo Administrador Local — aplicando CLÁSSICO CLARO")
                self.current_theme_name = "CLÁSSICO CLARO"
                self.theme_manager.apply_theme("CLÁSSICO CLARO", rebuild_interface=False)
                return
            if not hasattr(self, 'user_manager') or self.user_manager is None:
                _dprint("⚠️ UserManager não disponível, usando tema padrão")
                self.current_theme_name = "CLÁSSICO CLARO"
                self.theme_manager.apply_theme("CLÁSSICO CLARO", rebuild_interface=False)
                return
            tema_nome, palette = self.user_manager.load_user_theme_completo()
            _dprint(f"📦 Tema carregado: '{tema_nome}'")
            if not tema_nome:
                tema_nome = self.tema_preferido_inicial
                palette = None
            self.current_theme_name = tema_nome
            if palette:
                self.theme_manager.apply_theme(tema_nome, palette, rebuild_interface=False)
            else:
                self.theme_manager.apply_theme(tema_nome, rebuild_interface=False)
            _dprint(f"✅ Tema '{tema_nome}' aplicado!")
        except Exception as e:
            _dprint(f"❌ Erro ao carregar tema: {e}")
            self.current_theme_name = "CLÁSSICO CLARO"
            self.theme_manager.apply_theme("CLÁSSICO CLARO", rebuild_interface=False)

    @functools.lru_cache(maxsize=256)
    def _load_icon_asset(self, icon_path: str):
        if not os.path.exists(icon_path):
            return None
        try:
            return Image.open(icon_path)
        except Exception:
            return None

    def _load_icons(self):
        _dprint("🔄 Carregando ícones...")
        requested_size = (24, 24)
        if self._icon_size_signature == requested_size and self.icons_cache:
            return
        self.icons_cache = {}
        self._icon_size_signature = requested_size
        for categoria, filename in self.ICON_MAPPING.items():
            try:
                icon_path = os.path.join(ICONS_DIR, filename)
                image = self._load_icon_asset(icon_path)
                if image is not None:
                    self.icons_cache[categoria] = ctk.CTkImage(
                        light_image=image, dark_image=image, size=requested_size
                    )
            except Exception as e:
                _dprint(f"❌ Erro ao carregar ícone {filename}: {e}")
        _dprint(f"✅ {len(self.icons_cache)} ícones carregados")

    def _get_submenu_icon(self, categoria: str, item: str):
        cache_key = f"{categoria}_{item}"
        if cache_key in self.icons_cache:
            return self.icons_cache[cache_key]
        filename = self.SUBMENU_ICON_MAPPING.get(categoria, {}).get(item, "")
        if not filename:
            return None
        try:
            icon_path = os.path.join(ICONS_DIR, filename)
            image = self._load_icon_asset(icon_path)
            if image is not None:
                icon = ctk.CTkImage(light_image=image, dark_image=image, size=(20, 20))
                self.icons_cache[cache_key] = icon
                return icon
        except Exception as e:
            _dprint(f"❌ Erro ao carregar ícone de submenu {filename}: {e}")
        return None

    def _build_interface(self):
        self.grid_columnconfigure(0, weight=0, minsize=self.SIDEBAR_WIDTH + 16)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.configure(fg_color=self.cor_fundo)
        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self,
            width=self.SIDEBAR_WIDTH,
            corner_radius=14,
            fg_color=self.cor_primaria,
            border_color=self.cor_borda,
            border_width=2,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.sidebar.grid_propagate(False)
        titulo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        titulo_frame.pack(pady=(20, 10))
        try:
            icon_path = os.path.join(APP_DIR, "ICONE_SISTEMA.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                img = ctk.CTkImage(
                    light_image=img,
                    dark_image=img,
                    size=(self.icon_size_sidebar, self.icon_size_sidebar),
                )
                icon_label = ctk.CTkLabel(titulo_frame, image=img, text="")
                icon_label.pack(side="left", padx=(0, 10))
        except Exception as e:
            _dprint(f"⚠️ Erro ao carregar ícone no sidebar: {e}")
        self.sidebar_title_label = ctk.CTkLabel(
            titulo_frame,
            text=self._get_text("system_title"),
            font=self.font_sidebar_titulo,
            text_color=self.cor_texto,
        )
        self.sidebar_title_label.pack(side="left")
        self.sidebar_subtitle_label = ctk.CTkLabel(
            self.sidebar,
            text=self._get_text("main_menu"),
            font=self.font_sidebar_subtitulo,
            text_color=self.cor_texto,
        )
        self.sidebar_subtitle_label.pack(pady=(0, 40))
        self.menu_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.menu_frame.pack(fill="both", expand=True, padx=10, pady=(4, 8))
        self._build_menu_content()

    def _build_main_area(self):
        self.main = ctk.CTkFrame(
            self,
            corner_radius=14,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            border_width=2,
        )
        self.main.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=8)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)
        self._build_topbar()
        self.content_shell = ctk.CTkFrame(
            self.main,
            fg_color=self.cor_fundo,
            corner_radius=10,
            border_color=self.cor_borda,
            border_width=1,
        )
        self.content_shell.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.content_shell.grid_columnconfigure(0, weight=1)
        self.content_shell.grid_rowconfigure(0, weight=1)
        self.content = ctk.CTkFrame(self.content_shell, fg_color=self.cor_fundo)
        self.content.grid(row=0, column=0, sticky="nsew")

    def _build_topbar(self):
        self.topbar = ctk.CTkFrame(
            self.main,
            fg_color=self.cor_primaria,
            corner_radius=12,
            border_color=self.cor_borda,
            border_width=1,
            height=self.TOPBAR_HEIGHT
        )
        self.topbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        self.topbar.grid_propagate(False)
        self.topbar.grid_columnconfigure(0, weight=1)
        self.topbar.grid_columnconfigure(1, weight=0)
        self.topbar.grid_columnconfigure(2, weight=0)
        self.topbar.grid_columnconfigure(3, weight=0)
        self.topbar.grid_columnconfigure(4, weight=0)
        self.topbar.grid_columnconfigure(5, weight=0)
        self.title_label = ctk.CTkLabel(
            self.topbar,
            text=self._translate_page_name("Dashboard"),
            font=self.font_topbar_titulo,
            text_color=self.cor_texto,
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=15, pady=4)
        self._build_utility_buttons()
        self._add_language_selector_to_topbar()
        self._add_theme_switch_to_topbar()
        self._build_user_widget()

    def _build_utility_buttons(self):
        button_frame = ctk.CTkFrame(
            self.topbar,
            fg_color=self.cor_primaria,
            corner_radius=0,
            border_width=0,
            height=34
        )
        button_frame.grid(row=0, column=1, sticky="e", padx=10, pady=10)
        button_frame.grid_propagate(False)
        base_bg = "transparent"
        hover_bg = self.cor_terciaria
        hover_radius = 12

        def on_enter(widget):
            widget.configure(fg_color=hover_bg, corner_radius=hover_radius)

        def on_leave(widget):
            widget.configure(fg_color=base_bg, corner_radius=0)

        self.icon_refresh = None
        for nome in ["ATUALIZAR.png", "REFRESH.png", "RELOAD.png", "ATUALIZAR_PAGINA.png"]:
            try:
                p = os.path.join(ICONS_DIR, nome)
                if os.path.exists(p):
                    img = Image.open(p).convert("RGBA")
                    self.icon_refresh = ctk.CTkImage(light_image=img, dark_image=img, size=(22, 22))
                    break
            except Exception:
                pass
        if self.icon_refresh:
            self.lbl_refresh = ctk.CTkLabel(
                button_frame,
                text="",
                image=self.icon_refresh,
                fg_color=base_bg,
                corner_radius=0
            )
        else:
            self.lbl_refresh = ctk.CTkLabel(
                button_frame,
                text="↻",
                font=("Segoe UI", 22, "bold"),
                text_color=self.cor_texto,
                fg_color=base_bg,
                corner_radius=0
            )
        self.lbl_refresh.pack(side="left", padx=16, pady=0)
        self.lbl_refresh.bind("<Button-1>", lambda e: self.reload_current_page())
        self.lbl_refresh.bind("<Enter>", lambda e, w=self.lbl_refresh: on_enter(w))
        self.lbl_refresh.bind("<Leave>", lambda e, w=self.lbl_refresh: on_leave(w))
        self.icon_switch_user = None
        try:
            icon_path = os.path.join(ICONS_DIR, "TROCAR_USUARIO.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path).convert("RGBA")
                self.icon_switch_user = ctk.CTkImage(light_image=img, dark_image=img, size=(22, 22))
        except Exception as e:
            _dprint("Erro ao carregar TROCAR_USUARIO.png:", e)
        self.lbl_switch_user = ctk.CTkLabel(
            button_frame,
            text="",
            image=self.icon_switch_user,
            fg_color=base_bg,
            bg_color="transparent",
            corner_radius=0
        )
        self.lbl_switch_user.pack(side="left", padx=10, pady=0)
        self.lbl_switch_user.bind("<Button-1>", lambda e: self.trocar_usuario())
        self.lbl_switch_user.bind("<Enter>", lambda e, w=self.lbl_switch_user: on_enter(w))
        self.lbl_switch_user.bind("<Leave>", lambda e, w=self.lbl_switch_user: on_leave(w))

    def _get_text(self, chave: str, **kwargs) -> str:
        base = self.UI_TEXTS.get(self.idioma_atual, self.UI_TEXTS["pt_BR"])
        texto = base.get(chave, self.UI_TEXTS["pt_BR"].get(chave, chave))
        try:
            return texto.format(**kwargs)
        except Exception:
            return texto

    def _get_language_display_name(self, idioma: str | None = None) -> str:
        codigo = idioma or self.idioma_atual
        return self.SUPPORTED_LANGUAGES.get(codigo, self.SUPPORTED_LANGUAGES["pt_BR"])

    def _translate_menu_label(self, texto: str) -> str:
        mapa = self.MENU_LABELS.get(texto)
        if not mapa:
            return texto
        return mapa.get(self.idioma_atual, mapa.get("pt_BR", texto))

    def _translate_page_name(self, page_name: str) -> str:
        if page_name == "Dashboard":
            return self._get_text("topbar_dashboard")
        return self._translate_menu_label(page_name)

    def _save_language_preference(self):
        try:
            self.settings["language"] = self.idioma_atual
            ConfigManager.save_settings(self.settings)
        except Exception as e:
            _dprint(f"⚠️ Não foi possível salvar idioma: {e}")

    def _clear_page_cache_except_current(self):
        current = getattr(self, "_current_frame", None)
        current_page = getattr(self, "current_page", None)
        for page_name, frame in list(self._page_cache.items()):
            if frame is current and page_name == current_page:
                continue
            try:
                frame.destroy()
            except Exception:
                pass
            self._page_cache.pop(page_name, None)
            if page_name in self._page_cache_order:
                self._page_cache_order.remove(page_name)

    def _refresh_frame_language(self, frame=None):
        frame = frame or getattr(self, "_current_frame", None)
        if not frame or not getattr(frame, "winfo_exists", lambda: False)():
            return
        idioma = getattr(self, "idioma_atual", "pt_BR")
        mapa_traducao = {}
        try:
            all_maps = getattr(frame.__class__, "_TRANSLATIONS", {}) or getattr(frame, "_TRANSLATIONS", {})
            if isinstance(all_maps, dict):
                base = all_maps.get("pt_BR", {}) if isinstance(all_maps.get("pt_BR", {}), dict) else {}
                atual = all_maps.get(idioma, {}) if isinstance(all_maps.get(idioma, {}), dict) else {}
                mapa_traducao = dict(base)
                mapa_traducao.update(atual)
        except Exception:
            mapa_traducao = {}

        def _resolve_mapa_widget(widget):
            try:
                wm = getattr(widget.__class__, "_TRANSLATIONS", {}) or getattr(widget, "_TRANSLATIONS", {})
                if isinstance(wm, dict) and (idioma in wm or "pt_BR" in wm):
                    base = wm.get("pt_BR", {}) if isinstance(wm.get("pt_BR", {}), dict) else {}
                    atual = wm.get(idioma, {}) if isinstance(wm.get(idioma, {}), dict) else {}
                    mp = dict(base)
                    mp.update(atual)
                    if mp:
                        return mp
            except Exception:
                pass
            return mapa_traducao

        def _traduzir_texto(valor, widget=None):
            if not isinstance(valor, str):
                return valor
            texto = valor.strip()
            if not texto:
                return valor
            mp = _resolve_mapa_widget(widget) if widget is not None else mapa_traducao
            return mp.get(texto, mp.get(valor, valor))

        def _traduzir_widget(widget):
            # Textos comuns em widgets TK/CTK
            for opt in ("text", "placeholder_text"):
                try:
                    atual = widget.cget(opt)
                except Exception:
                    continue
                novo = _traduzir_texto(atual, widget)
                if novo != atual:
                    try:
                        widget.configure(**{opt: novo})
                    except Exception:
                        pass

            # Combobox / OptionMenu: valores exibidos
            for opt in ("values",):
                try:
                    valores = widget.cget(opt)
                except Exception:
                    continue
                if isinstance(valores, (list, tuple)):
                    novos = [_traduzir_texto(v, widget) for v in valores]
                    if list(novos) != list(valores):
                        try:
                            widget.configure(**{opt: novos})
                        except Exception:
                            pass

            # Treeviews: cabeçalhos de colunas + coluna árvore
            if isinstance(widget, ttk.Treeview):
                try:
                    texto_tree = widget.heading("#0").get("text", "")
                    novo_tree = _traduzir_texto(texto_tree, widget)
                    if novo_tree != texto_tree:
                        widget.heading("#0", text=novo_tree)
                except Exception:
                    pass
                try:
                    for col in widget["columns"]:
                        heading = widget.heading(col)
                        atual = heading.get("text", "")
                        novo = _traduzir_texto(atual, widget)
                        if novo != atual:
                            widget.heading(col, text=novo)
                except Exception:
                    pass

            # Menus clássicos do Tk
            if isinstance(widget, tk.Menu):
                try:
                    end = widget.index("end")
                except Exception:
                    end = None
                if end is not None:
                    for idx in range(end + 1):
                        try:
                            label = widget.entrycget(idx, "label")
                        except Exception:
                            continue
                        novo = _traduzir_texto(label, widget)
                        if novo != label:
                            try:
                                widget.entryconfigure(idx, label=novo)
                            except Exception:
                                pass

        def _aplicar_idioma(widget):
            try:
                if hasattr(widget, "sistema"):
                    widget.sistema = self
                if hasattr(widget, "app"):
                    widget.app = self
                if hasattr(widget, "idioma_atual"):
                    widget.idioma_atual = idioma
            except Exception:
                pass

            for metodo in ("set_idioma", "on_language_changed", "refresh_texts"):
                try:
                    if not hasattr(widget, metodo):
                        continue
                    fn = getattr(widget, metodo)
                    if not callable(fn):
                        continue
                    if metodo in ("set_idioma", "on_language_changed"):
                        fn(idioma)
                    else:
                        fn()
                except Exception as err:
                    _dprint(f"⚠️ {widget.__class__.__name__}.{metodo} falhou: {err}")
            try:
                _traduzir_widget(widget)
            except Exception:
                pass
            try:
                for child in widget.winfo_children():
                    _aplicar_idioma(child)
            except Exception:
                pass

        try:
            _aplicar_idioma(frame)
        except Exception as e:
            _dprint(f"⚠️ Erro ao atualizar idioma do frame {getattr(frame, '__class__', type(frame)).__name__}: {e}")

    def _refresh_current_page_language(self):
        self._refresh_frame_language(getattr(self, "_current_frame", None))

    def _change_language(self, selected_value=None):
        novo_idioma = selected_value if selected_value in self.SUPPORTED_LANGUAGES else None

        if novo_idioma is None:
            for codigo, nome in self.SUPPORTED_LANGUAGES.items():
                if nome == selected_value:
                    novo_idioma = codigo
                    break

        if not novo_idioma:
            novo_idioma = "pt_BR"

        idioma_atual = getattr(self, "idioma_atual", "pt_BR")
        pagina_atual = getattr(self, "current_page", None)
        frame_atual = getattr(self, "_current_frame", None)
        submenu_ativo = getattr(self, "_active_submenu", None)

        if novo_idioma == idioma_atual:
            if hasattr(self, "language_status_label") and self.language_status_label.winfo_exists():
                self.language_status_label.configure(text=self._get_language_display_name())
            return

        self.idioma_atual = novo_idioma
        self._save_language_preference()

        try:
            self.settings["language"] = novo_idioma
            ConfigManager.save_settings(self.settings)
        except Exception:
            pass

        try:
            self._refresh_language_widgets()
        except Exception as e:
            _dprint(f"⚠️ Erro ao atualizar widgets de idioma: {e}")

        # Atualiza idioma em todos os frames já carregados (cache + página atual),
        # para que qualquer página aberta após a troca já apareça no idioma novo.
        try:
            for frame in list(getattr(self, "_page_cache", {}).values()):
                self._refresh_frame_language(frame)
        except Exception as e:
            _dprint(f"⚠️ Erro ao atualizar idioma dos frames em cache: {e}")

        try:
            if pagina_atual and hasattr(self, "title_label") and self.title_label.winfo_exists():
                self.title_label.configure(text=self._translate_page_name(pagina_atual))
        except Exception as e:
            _dprint(f"⚠️ Erro ao atualizar título da página: {e}")

        try:
            if pagina_atual:
                if frame_atual and frame_atual.winfo_exists():
                    try:
                        frame_atual.place_forget()
                    except Exception:
                        pass

                try:
                    frame_cache = self._page_cache.get(pagina_atual)
                    if frame_cache:
                        try:
                            frame_cache.destroy()
                        except Exception:
                            pass
                        self._page_cache.pop(pagina_atual, None)
                except Exception:
                    pass

                self._current_frame = None
                self._page_loading = False
                self.open_page(pagina_atual)
        except Exception as e:
            _dprint(f"⚠️ Erro ao recarregar página atual no novo idioma: {e}")

        try:
            if submenu_ativo:
                self._active_submenu = submenu_ativo
            self._update_menu_buttons_colors()
        except Exception as e:
            _dprint(f"⚠️ Erro ao restaurar submenu ativo: {e}")

        try:
            if hasattr(self, "language_status_label") and self.language_status_label.winfo_exists():
                self.language_status_label.configure(text=self._get_language_display_name())
        except Exception:
            pass

    def _add_language_selector_to_topbar(self):
        if hasattr(self, "language_frame") and self.language_frame.winfo_exists():
            self.language_frame.destroy()

        self.language_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        self.language_frame.grid(row=0, column=2, padx=(0, 12), sticky="e")

        self.language_label = ctk.CTkLabel(
            self.language_frame,
            text=f"🌐 {self._get_text('language')}",
            font=("Arial", max(11, int(12 * getattr(self, 'ui_scale', 1.0))), "bold"),
            text_color=self.cor_texto,
        )
        self.language_label.pack(side="left", padx=(0, 8))

        self.language_status_label = ctk.CTkLabel(
            self.language_frame,
            text=self._get_language_display_name(),
            font=("Arial", max(10, int(11 * getattr(self, 'ui_scale', 1.0)))),
            text_color=self.cor_texto,
        )
        self.language_status_label.pack(side="left", padx=(0, 8))

        self.language_var = ctk.StringVar(value=self._get_language_display_name())
        idioma_menu_texto = self._contrast_text_for_color(self.cor_secundaria, fallback=self.cor_texto)
        self.language_menu = ctk.CTkOptionMenu(
            self.language_frame,
            variable=self.language_var,
            values=list(self.SUPPORTED_LANGUAGES.values()),
            width=max(150, int(170 * getattr(self, 'ui_scale', 1.0))),
            command=self._change_language,
            fg_color=self.cor_secundaria,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=idioma_menu_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=idioma_menu_texto,
            dropdown_hover_color=self.cor_hover,
        )
        self.language_menu.pack(side="left")

    @staticmethod
    def _theme_mode_from_name(tema_nome: str) -> str:
        nome = (tema_nome or "").strip().upper()
        if nome in {"NOTURNO", "PRETO E OURO", "NOITE URBANA"}:
            return "dark"
        return "light"

    def _add_theme_switch_to_topbar(self):
        import customtkinter as ctk

        if hasattr(self, "theme_switch_frame") and self.theme_switch_frame.winfo_exists():
            self.theme_switch_frame.destroy()

        self.theme_switch_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        self.theme_switch_frame.grid(row=0, column=3, padx=18, sticky="e")

        if not hasattr(self, "current_theme_name") or not self.current_theme_name:
            self.current_theme_name = "CLÁSSICO CLARO"

        is_dark_mode = self._theme_mode_from_name(self.current_theme_name) == "dark"

        self.icon_theme = ctk.CTkLabel(
            self.theme_switch_frame,
            text="🌙" if is_dark_mode else "☀️",
            font=self.font_topbar_icone,
        )
        self.icon_theme.pack(side="left", padx=(0, 10))

        # flag anti-loop
        self._theme_switch_syncing = True

        self.theme_switch = ctk.CTkSwitch(
            self.theme_switch_frame,
            text="",
            width=52,
            height=26,
            switch_width=52,
            switch_height=26,
            fg_color="#A3A3A3",
            progress_color="#3B82F6",
            button_color="#FFFFFF",
            button_hover_color="#E5E5E5",
            command=self._on_theme_switch_changed
        )

        # sincroniza estado VISUAL sem executar lógica extra
        # (neste switch, o estado selecionado representa "dia/claro")
        if is_dark_mode:
            self.theme_switch.deselect()
        else:
            self.theme_switch.select()

        self.theme_switch.pack(side="left")

        self._theme_switch_syncing = False

    def _apply_theme_by_name(self, tema_nome: str):
        try:
            from PAGINAS_DO_SISTEMA.TEMAS import ModuloPaletas
            paletas = ModuloPaletas()
            paleta = paletas.PADROES.get(tema_nome) or paletas.PADROES.get("CLÁSSICO CLARO", {})

            if hasattr(self, "theme_manager") and self.theme_manager:
                self.theme_manager.apply_theme(tema_nome, paleta, rebuild_interface=False)

            # força menu/submenu
            if hasattr(self, "_update_menu_buttons_colors"):
                self._update_menu_buttons_colors()

            # atualiza frame atual
            if hasattr(self, "_current_frame") and self._current_frame and self._current_frame.winfo_exists():
                if hasattr(self.theme_manager, "apply_theme_to_widget"):
                    self.theme_manager.apply_theme_to_widget(self._current_frame)
                else:
                    self.theme_manager._apply_palette_to_widget(self._current_frame, paleta, self.theme_manager.fonts)

            # topbar e content
            if hasattr(self, "topbar") and self.topbar.winfo_exists():
                self.theme_manager._apply_palette_to_widget(self.topbar, paleta, self.theme_manager.fonts)
            if hasattr(self, "content") and self.content.winfo_exists():
                self.theme_manager._apply_palette_to_widget(self.content, paleta, self.theme_manager.fonts)

            # salva preferência
            if hasattr(self, "user_manager") and self.user_manager:
                self.user_manager.save_user_theme(tema_nome)

            self.current_theme_name = tema_nome

            # reforço (corrige repaint atrasado)
            self.after(80, lambda: self._update_menu_buttons_colors() if hasattr(self,
                                                                                 "_update_menu_buttons_colors") else None)
            self.after(180, lambda: self._update_menu_buttons_colors() if hasattr(self,
                                                                                  "_update_menu_buttons_colors") else None)

        except Exception as e:
            _dprint(f"❌ Erro ao aplicar tema '{tema_nome}': {e}")
            messagebox.showerror("Erro", f"Falha ao aplicar tema:\n{e}", parent=self)

    def _toggle_theme_mode(self):
        """Switch claro/escuro usando a mesma rotina da página TEMAS (e rebuild ao trocar modo)."""
        try:
            is_dark = bool(self.theme_switch.get())
            tema_nome = "Preto e Ouro" if is_dark else "CLÁSSICO CLARO"

            # Ícone
            if hasattr(self, "icon_theme") and self.icon_theme.winfo_exists():
                self.icon_theme.configure(text="🌙" if is_dark else "☀️")

            # Mantém estado do switch coerente
            try:
                self.theme_switch.select() if is_dark else self.theme_switch.deselect()
            except Exception:
                pass

            # === MESMO JEITO DA PÁGINA TEMAS ===
            from PAGINAS_DO_SISTEMA.TEMAS import ModuloPaletas
            paletas = ModuloPaletas()
            paleta = paletas.obter_tema(tema_nome) if hasattr(paletas, "obter_tema") else paletas.PADROES.get(tema_nome)

            if not paleta:
                tema_fallback = "Preto e Ouro" if is_dark else "CLÁSSICO CLARO"
                paleta = paletas.PADROES.get(tema_fallback, {})

            # Detecta se está trocando o modo (dark<->light) e força rebuild
            modo_anterior = getattr(self, "tema_modo", None)  # "dark"/"light" (se já existir)
            modo_novo = "dark" if is_dark else "light"
            rebuild = (modo_anterior is not None and modo_anterior != modo_novo)

            if hasattr(self, "theme_manager") and self.theme_manager:
                self.theme_manager.apply_theme(tema_nome, paleta, rebuild_interface=rebuild)
            else:
                for campo, valor in paleta.items():
                    setattr(self, f"cor_{campo}", valor)

            self.current_theme_name = tema_nome
            self.tema_preferido_inicial = tema_nome
            self.tema_atual = tema_nome
            self.tema_modo = modo_novo

            # Persiste preferência
            if hasattr(self, "user_manager") and self.user_manager:
                self.user_manager.save_user_theme(tema_nome)

            # Reforço (pós-redraw)
            def _reforcar():
                try:
                    if hasattr(self, "_update_menu_buttons_colors"):
                        self._update_menu_buttons_colors()
                    self.update_idletasks()
                except Exception:
                    pass

            _reforcar()
            self.after(80, _reforcar)
            self.after(180, _reforcar)

        except Exception as e:
            _dprint(f"❌ Erro ao trocar tema: {e}")
            try:
                messagebox.showerror("Erro", f"Falha ao trocar tema:\n{e}", parent=self)
            except Exception:
                messagebox.showerror("Erro", f"Falha ao trocar tema:\n{e}")

    def _on_theme_switch_changed(self):
        # se estamos só sincronizando (recriando switch), não faz nada
        if getattr(self, "_theme_switch_syncing", False):
            return

        # neste switch, 1 = dia/claro e 0 = noite/escuro
        is_dark = (self.theme_switch.get() == 0)
        tema_nome = "Preto e Ouro" if is_dark else "CLÁSSICO CLARO"

        if hasattr(self, "icon_theme") and self.icon_theme.winfo_exists():
            self.icon_theme.configure(text="🌙" if is_dark else "☀️")

        # atalho direto para a lógica de aplicação da página TEMAS
        from PAGINAS_DO_SISTEMA.TEMAS import aplicar_tema_atalho

        ok = aplicar_tema_atalho(self, tema_nome)
        if not ok:
            _dprint(f"❌ Falha no atalho de tema '{tema_nome}' via TEMAS.py")
            try:
                messagebox.showerror("Erro", f"Falha ao aplicar tema '{tema_nome}' via atalho.", parent=self)
            except Exception:
                messagebox.showerror("Erro", f"Falha ao aplicar tema '{tema_nome}' via atalho.")
            return

        try:
            if hasattr(self, "_update_menu_buttons_colors"):
                self._update_menu_buttons_colors()
        except Exception:
            pass

        # garante posição visual da chave conforme o tema efetivamente aplicado
        self.after(20, self._sync_theme_switch_with_current_theme)

    def _sync_theme_switch_with_current_theme(self):
        try:
            if not hasattr(self, "theme_switch") or not self.theme_switch.winfo_exists():
                return
            is_dark_mode = self._theme_mode_from_name(getattr(self, "current_theme_name", "")) == "dark"
            self._theme_switch_syncing = True
            if is_dark_mode:
                self.theme_switch.deselect()
            else:
                self.theme_switch.select()
            if hasattr(self, "icon_theme") and self.icon_theme.winfo_exists():
                self.icon_theme.configure(text="🌙" if is_dark_mode else "☀️")
        except Exception:
            pass
        finally:
            self._theme_switch_syncing = False

    def _build_user_widget(self):
        user_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        user_frame.grid(row=0, column=4, padx=18, sticky="e")
        self.user_info_label = ctk.CTkLabel(
            user_frame,
            text=self._get_text("loading"),
            font=("Arial", 14),
            text_color=self.cor_texto,
        )
        self.user_info_label.pack(side="right", anchor="e")

    def _update_user_display(self):
        self._update_user_info_once()
        if hasattr(self, 'user_info_label'):
            self._agendar_after(1000, self._tick_clock)

    def _update_user_info_once(self):
        if not hasattr(self, 'user_info_label'):
            return
        now = datetime.now().strftime(self._get_text("clock_format"))
        user_text = f"{now} | 👤 {self.usuario_nome} • {self.usuario_hierarquia}"
        if hasattr(self, 'user_manager') and self.user_manager._is_admin():
            user_text = f"{now} | 👑 {self.usuario_nome} • {self.usuario_hierarquia}"
        try:
            self.user_info_label.configure(text=user_text)
        except Exception as e:
            _dprint(f"Erro ao atualizar informações: {e}")

    def _tick_clock(self):
        if not hasattr(self, 'user_info_label') or not self.winfo_exists():
            return
        now = datetime.now().strftime(self._get_text("clock_format"))
        user_text = f"{now} | 👤 {self.usuario_nome} • {self.usuario_hierarquia}"
        if hasattr(self, 'user_manager') and self.user_manager._is_admin():
            user_text = f"{now} | 👑 {self.usuario_nome} • {self.usuario_hierarquia}"
        try:
            self.user_info_label.configure(text=user_text)
        except Exception as e:
            _dprint(f"Erro ao atualizar relógio: {e}")
            return
        self._agendar_after(1000, self._tick_clock)

    def _refresh_language_widgets(self):
        try:
            if hasattr(self, "sidebar_title_label") and self.sidebar_title_label.winfo_exists():
                self.sidebar_title_label.configure(text=self._get_text("system_title"))

            if hasattr(self, "sidebar_subtitle_label") and self.sidebar_subtitle_label.winfo_exists():
                self.sidebar_subtitle_label.configure(text=self._get_text("main_menu"))

            if hasattr(self, "language_label") and self.language_label.winfo_exists():
                self.language_label.configure(text=f"🌐 {self._get_text('language')}")

            if hasattr(self, "language_status_label") and self.language_status_label.winfo_exists():
                self.language_status_label.configure(text=self._get_language_display_name())

            if hasattr(self, "language_var"):
                self.language_var.set(self._get_language_display_name())

            if hasattr(self, "language_menu") and self.language_menu.winfo_exists():
                self.language_menu.configure(values=list(self.SUPPORTED_LANGUAGES.values()))

            if hasattr(self, "user_info_label") and self.user_info_label.winfo_exists():
                self._update_user_info_once()

            if hasattr(self, "current_page") and self.current_page and hasattr(self,
                                                                               "title_label") and self.title_label.winfo_exists():
                self.title_label.configure(text=self._translate_page_name(self.current_page))

            self._build_menu_content()
            self._update_menu_buttons_colors()

        except Exception as e:
            _dprint(f"⚠️ Erro ao atualizar widgets de idioma: {e}")

    def _cancel_submenu_hide_timer(self):
        if self._submenu_timer:
            try:
                self.after_cancel(self._submenu_timer)
            except Exception:
                pass
            self._submenu_timer = None

    def _schedule_submenu_hide(self, delay: int = 220):
        self._cancel_submenu_hide_timer()

        def _hide_if_outside():
            self._submenu_timer = None
            try:
                x = self.winfo_pointerx()
                y = self.winfo_pointery()
            except Exception:
                self._hide_all_submenus()
                return

            try:
                widget_abaixo = self.winfo_containing(x, y)
            except Exception:
                widget_abaixo = None

            while widget_abaixo is not None:
                if getattr(widget_abaixo, '_opera_menu_button', False) or getattr(widget_abaixo,
                                                                                  '_opera_submenu_button', False):
                    return
                if widget_abaixo in self.submenu_frames.values() or widget_abaixo in self.botoes_menu.values():
                    return
                widget_abaixo = getattr(widget_abaixo, 'master', None)

            self._hide_all_submenus()

        try:
            self._submenu_timer = self.after(delay, _hide_if_outside)
        except Exception:
            self._submenu_timer = None

    def _hide_submenu(self, categoria: str):
        self._cancel_submenu_hide_timer()
        frame = self.submenu_frames.get(categoria)
        if frame:
            frame.place_forget()
        if self._active_submenu == categoria:
            self._active_submenu = None
            self._update_menu_buttons_colors()

    def _apply_menu_hover_behavior(self, widget, fg, texto, hover_fg, hover_texto, *, border_width=1,
                                   border_color=None):
        """Aplica no menu o mesmo padrão de hover da página de temas: fundo muda no hover e o texto acompanha."""
        try:
            widget.configure(
                fg_color=fg,
                hover=True,
                hover_color=hover_fg,
                text_color=texto,
                border_width=border_width,
                border_color=border_color if border_color is not None else self.cor_borda,
            )
        except Exception:
            pass

        widget._opera_menu_hover_cfg = {
            "fg": fg,
            "texto": texto,
            "hover_fg": hover_fg,
            "hover_texto": hover_texto,
            "border_width": border_width,
            "border_color": border_color if border_color is not None else self.cor_borda,
        }

        if getattr(widget, "_opera_menu_hover_bound", False):
            return

        def on_enter(_event=None, b=widget):
            cfg = getattr(b, "_opera_menu_hover_cfg", None) or {}
            try:
                b.configure(
                    fg_color=cfg.get("hover_fg", cfg.get("fg")),
                    text_color=cfg.get("hover_texto", cfg.get("texto")),
                )
            except Exception:
                pass

        def on_leave(_event=None, b=widget):
            cfg = getattr(b, "_opera_menu_hover_cfg", None) or {}
            try:
                b.configure(
                    fg_color=cfg.get("fg"),
                    text_color=cfg.get("texto"),
                )
            except Exception:
                pass

        try:
            widget.bind("<Enter>", on_enter, add="+")
            widget.bind("<Leave>", on_leave, add="+")
            widget._opera_menu_hover_bound = True
        except Exception:
            pass

    def _update_menu_buttons_colors(self):
        try:
            style = self._get_menu_style_tokens()

            for categoria, btn_frame in self.botoes_menu.items():
                if not btn_frame.winfo_exists():
                    continue

                for child in btn_frame.winfo_children():
                    if not isinstance(child, ctk.CTkButton):
                        continue

                    ativo = (categoria == self._active_submenu)
                    fg = style["hover_bg"] if ativo else style["menu_bg"]
                    txt = style["hover_texto"] if ativo else style["menu_texto"]

                    self._apply_menu_hover_behavior(
                        child,
                        fg=fg,
                        texto=txt,
                        hover_fg=style["hover_bg"],
                        hover_texto=style["hover_texto"],
                        border_width=1,
                        border_color=self.cor_borda,
                    )

            for _, submenu_frame in self.submenu_frames.items():
                if not submenu_frame.winfo_exists():
                    continue

                submenu_frame.configure(
                    fg_color=style["submenu_painel_bg"],
                    border_color=self.cor_borda,
                    border_width=1,
                )

                for inner_frame in submenu_frame.winfo_children():
                    if isinstance(inner_frame, ctk.CTkFrame):
                        for btn_container in inner_frame.winfo_children():
                            if isinstance(btn_container, ctk.CTkFrame):
                                for btn in btn_container.winfo_children():
                                    if isinstance(btn, ctk.CTkButton):
                                        self._apply_menu_hover_behavior(
                                            btn,
                                            fg=style["submenu_bg"],
                                            texto=style["submenu_texto"],
                                            hover_fg=style["submenu_hover_bg"],
                                            hover_texto=style["submenu_hover_texto"],
                                            border_width=0,
                                            border_color=style["submenu_bg"],
                                        )
            _dprint("[Tema] Cores do menu e submenu atualizadas.")
        except Exception as e:
            _dprint(f"[Tema] Erro ao atualizar cores do menu: {e}")

    def _hide_all_submenus(self):
        self._cancel_submenu_hide_timer()
        for frame in self.submenu_frames.values():
            try:
                frame.place_forget()
            except Exception:
                pass
        if self._active_submenu:
            self._active_submenu = None
            self._update_menu_buttons_colors()

    def _create_menu_button(self, categoria: str, posicao: int):
        btn_frame = ctk.CTkFrame(
            self.menu_frame,
            fg_color="transparent",
            width=self.SIDEBAR_WIDTH - 20,
            height=self.ITEM_HEIGHT
        )
        btn_frame.pack(fill="x", padx=(10, 10), pady=max(1, int(2 * self.ui_scale)))
        btn_frame.pack_propagate(False)

        icon = self.icons_cache.get(categoria)
        style = self._get_menu_style_tokens()

        ativo = (categoria == self._active_submenu)
        btn_bg = style["hover_bg"] if ativo else style["menu_bg"]
        cor_texto = style["hover_texto"] if ativo else style["menu_texto"]

        btn = ctk.CTkButton(
            btn_frame,
            text=f"  {self._translate_menu_label(categoria)}",
            image=icon,
            compound="left",
            anchor="w",
            fg_color=btn_bg,
            hover=True,
            hover_color=style["hover_bg"],
            text_color=cor_texto,
            font=("Arial", max(11, int(14 * self.ui_scale))),
            corner_radius=max(8, int(10 * self.ui_scale)),
            border_color=self.cor_borda,
            border_width=1,
            command=lambda c=categoria: self._on_category_click(c)
        )

        btn._opera_menu_button = True
        btn_frame._menu_button = btn
        btn_frame._menu_categoria = categoria

        def _refresh_menu_button(_event=None, b=btn, cat=categoria):
            try:
                style_local = self._get_menu_style_tokens()
                ativo_local = (cat == self._active_submenu)
                fg = style_local["hover_bg"] if ativo_local else style_local["menu_bg"]
                txt = style_local["hover_texto"] if ativo_local else style_local["menu_texto"]
                self._apply_menu_hover_behavior(
                    b,
                    fg=fg,
                    texto=txt,
                    hover_fg=style_local["hover_bg"],
                    hover_texto=style_local["hover_texto"],
                    border_width=1,
                    border_color=self.cor_borda,
                )
            except Exception:
                pass

        self._apply_menu_hover_behavior(
            btn,
            fg=btn_bg,
            texto=cor_texto,
            hover_fg=style["hover_bg"],
            hover_texto=style["hover_texto"],
            border_width=1,
            border_color=self.cor_borda,
        )

        btn.pack(fill="both", expand=True, padx=max(2, int(4 * self.ui_scale)))

        if categoria != "Dashboard":
            def _menu_mouse_enter(_event=None, cat=categoria):
                self._cancel_submenu_hide_timer()
                self._show_submenu(cat)

            def _menu_mouse_leave(_event=None):
                self._schedule_submenu_hide()

            for widget_alvo in (btn_frame, btn):
                try:
                    widget_alvo.bind("<Enter>", _menu_mouse_enter, add="+")
                    widget_alvo.bind("<Leave>", _menu_mouse_leave, add="+")
                except Exception:
                    pass

        self.botoes_menu[categoria] = btn_frame
        self._create_submenu(categoria)

    def _create_submenu_item(self, parent, categoria: str, item: str):
        item_frame = ctk.CTkFrame(parent, fg_color="transparent")
        item_frame.pack(fill="x", padx=2, pady=1)

        icon = self._get_submenu_icon(categoria, item)
        style = self._get_menu_style_tokens()

        btn = ctk.CTkButton(
            item_frame,
            text=f"  {self._translate_menu_label(item)}",
            image=icon,
            compound="left",
            anchor="w",
            fg_color=style["submenu_bg"],
            hover=True,
            hover_color=style["submenu_hover_bg"],
            text_color=style["submenu_texto"],
            font=("Arial", max(11, int(13 * getattr(self, "ui_scale", 1.0)))),
            height=max(32, int(36 * getattr(self, "ui_scale", 1.0))),
            corner_radius=6,
            border_width=0,
            command=lambda i=item: self._on_submenu_click(categoria, i)
        )

        self._apply_menu_hover_behavior(
            btn,
            fg=style["submenu_bg"],
            texto=style["submenu_texto"],
            hover_fg=style["submenu_hover_bg"],
            hover_texto=style["submenu_hover_texto"],
            border_width=0,
            border_color=style["submenu_bg"],
        )

        btn.pack(fill="x", expand=True, padx=4, pady=2)

    def _create_submenu(self, categoria: str):
        itens = self.MENU_ESTRUTURA.get(categoria, [])
        itens_visiveis = [
            item for item in itens
            if self.user_manager.has_permission(item, "ver", categoria)
        ]
        if not itens_visiveis:
            return
        style = self._get_menu_style_tokens()
        cor_fundo = style["submenu_painel_bg"]
        cor_borda = self.cor_borda
        escala = getattr(self, "ui_scale", 1.0)
        maior_texto = max(len(str(item)) for item in itens_visiveis)
        largura_texto = int(maior_texto * max(8, int(9 * escala)))
        submenu_width = max(
            300,
            int(self.SIDEBAR_WIDTH * 1.12),
            largura_texto + int(110 * escala)
        )
        frame = ctk.CTkFrame(
            self,
            width=submenu_width,
            fg_color=cor_fundo,
            corner_radius=10,
            border_color=cor_borda,
            border_width=1,
        )
        inner_container = ctk.CTkFrame(frame, fg_color="transparent")
        inner_container.pack(fill="both", expand=True, padx=4, pady=6)
        inner_container._submenu_width = submenu_width
        for item in itens_visiveis:
            self._create_submenu_item(inner_container, categoria, item)

        def _submenu_mouse_enter(_event=None):
            self._cancel_submenu_hide_timer()

        def _submenu_mouse_leave(_event=None):
            self._schedule_submenu_hide()

        for widget_alvo in (frame, inner_container):
            try:
                widget_alvo.bind("<Enter>", _submenu_mouse_enter, add="+")
                widget_alvo.bind("<Leave>", _submenu_mouse_leave, add="+")
            except Exception:
                pass

        self.submenu_frames[categoria] = frame

    def _build_menu_content(self):
        for widget in self.menu_frame.winfo_children():
            widget.destroy()
        for frame in list(self.submenu_frames.values()):
            try:
                frame.destroy()
            except:
                pass
        self.submenu_frames.clear()
        self.botoes_menu.clear()
        for i, categoria in enumerate(self.MENU_ESTRUTURA.keys()):
            self._create_menu_button(categoria, i)
        _dprint(f"🎯 Menu construído com {len(self.MENU_ESTRUTURA)} categorias")

    def _on_category_click(self, categoria: str):
        if categoria == "Dashboard":
            self._hide_all_submenus()
            self.open_page("Dashboard")
            return
        if self._active_submenu == categoria:
            self._hide_submenu(categoria)
        else:
            self._hide_all_submenus()
            self._show_submenu(categoria)

    def _on_submenu_click(self, categoria: str, item: str):
        self._hide_all_submenus()
        self.open_page(item, categoria)

    def _realcar_cor(self, hex_color: str, factor: float = 1.2) -> str:
        try:
            h = hex_color.lstrip("#")
            if len(h) == 3:
                h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            r = min(255, int(r * factor))
            g = min(255, int(g * factor))
            b = min(255, int(b * factor))
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color

    def _darker(self, hex_color: str, factor: float = 0.85) -> str:
        try:
            if not hex_color or hex_color == "transparent":
                return hex_color
            h = hex_color.lstrip("#")
            if len(h) == 3:
                h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            r = max(0, min(255, int(r * factor)))
            g = max(0, min(255, int(g * factor)))
            b = max(0, min(255, int(b * factor)))
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color

    def _load_user_permissions(self):
        try:
            if not hasattr(self, 'usuario_id') or not self.usuario_id:
                self.permissoes_usuario = {}
                return
            if self.usuario_hierarquia and self.usuario_hierarquia.lower() in ("admin", "administrador"):
                self.permissoes_usuario = {
                    codigo: {"ver": True, "editar": True, "imprimir": True, "excluir": True, "administrar": True}
                    for codigo in self.PAGE_PERMISSION_MAP.values()}
                return
            try:
                from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import fetch_all
                sql = """
                    SELECT codigo, pode_ver, pode_editar, pode_imprimir, pode_excluir, pode_administrar
                    FROM opera.usuario_permissoes
                    WHERE usuario_id = %s
                """
                permissoes = fetch_all(sql, (self.usuario_id,))
                self.permissoes_usuario = {
                    p["codigo"]: {
                        "ver": p["pode_ver"],
                        "editar": p["pode_editar"],
                        "imprimir": p["pode_imprimir"],
                        "excluir": p["pode_excluir"],
                        "administrar": p["pode_administrar"],
                    }
                    for p in permissoes
                }
            except Exception as e:
                _dprint(f"⚠️ Erro ao carregar permissões: {e}")
                self.permissoes_usuario = {}
        except Exception as e:
            _dprint(f"❌ Erro em _load_user_permissions: {e}")
            self.permissoes_usuario = {}

    def _get_cached_page(self, page_name: str):
        frame = self._page_cache.get(page_name)
        if not frame:
            return None
        if not frame.winfo_exists() or frame.master != self.content:
            try:
                frame.destroy()
            except:
                pass
            self._page_cache.pop(page_name, None)
            if page_name in self._page_cache_order:
                self._page_cache_order.remove(page_name)
            return None
        return frame

    def _cache_page(self, page_name: str, frame):
        self._page_cache[page_name] = frame
        if page_name in self._page_cache_order:
            self._page_cache_order.remove(page_name)
        self._page_cache_order.append(page_name)
        while len(self._page_cache_order) > self._page_cache_size:
            old_page = self._page_cache_order.pop(0)
            old_frame = self._page_cache.pop(old_page, None)
            if old_frame:
                try:
                    old_frame.destroy()
                except:
                    pass

    def _apply_theme_to_frame_safely(self, frame):
        """Reaplica tema no frame informado (incluindo widgets criados com atraso)."""
        if not frame or not getattr(frame, "winfo_exists", lambda: False)():
            return
        try:
            if hasattr(frame, "host"):
                frame.host = self
            if hasattr(frame, "sistema"):
                frame.sistema = self
            if hasattr(frame, "app"):
                frame.app = self
            if hasattr(self, "theme_manager") and self.theme_manager:
                self.theme_manager.apply_theme_to_widget(frame)
            if hasattr(self, "_update_menu_buttons_colors"):
                self._update_menu_buttons_colors()
        except Exception as e:
            _dprint(f"⚠️ Erro ao reaplicar tema no frame: {e}")

    def open_page(self, page_name: str, categoria: str | None = None):
        if getattr(self, "_page_loading", False) or getattr(self, "_closing", False):
            return
        route_action = (self.routes.get(page_name) or {}).get("action")
        if page_name == "Trocar Usuário" or route_action == "trocar_usuario":
            self.trocar_usuario()
            return
        if not self.user_manager.has_permission(page_name, "ver", categoria):
            self._show_temporary_message(self._get_text("no_permission", page=self._translate_page_name(page_name)))
            return
        self._page_loading = True
        try:
            if self._current_frame and self._current_frame.winfo_exists():
                self._current_frame.place_forget()
            frame = self._get_cached_page(page_name)
            if frame is None:
                frame = self._load_page_direct(page_name)
                self._cache_page(page_name, frame)
            if frame:
                try:
                    self._refresh_frame_language(frame)
                except Exception as _exc:
                    _dprint(f"⚠️ Erro ao aplicar idioma ao abrir '{page_name}': {_exc}")
                frame.place(x=0, y=0, relwidth=1, relheight=1)
                # Ajuste responsivo: informa a página o tamanho real do container
                try:
                    self.after(80, self._notify_current_page_resize)
                except Exception:
                    pass
                if page_name == "Nova Ordem" and hasattr(self,
                                                         "_ordem_planejada_prefill") and self._ordem_planejada_prefill:
                    try:
                        if hasattr(frame, "carregar_op_planejada"):
                            frame.carregar_op_planejada(self._ordem_planejada_prefill)
                        self._ordem_planejada_prefill = None
                    except Exception as _exc:
                        _dprint(f"⚠️ Prefill de OP planejada falhou: {_exc}")

                if hasattr(self, "title_label"):
                    self.title_label.configure(text=self._translate_page_name(page_name))
                try:
                    if hasattr(frame, "on_page_open"):
                        frame.on_page_open()
                except Exception as _exc:
                    _dprint(f"⚠️ Erro ao atualizar página ao abrir '{page_name}': {_exc}")
                self._apply_theme_to_frame_safely(frame)
                # Um único reforço tardio evita travar a abertura com várias reaplicações em cascata.
                self.after(220,
                           lambda f=frame: self._apply_theme_to_frame_safely(f) if f is self._current_frame else None)
                self.current_page = page_name
                self._current_frame = frame
                try:
                    self.settings["last_page"] = page_name
                    ConfigManager.save_settings(self.settings)
                except:
                    pass
                try:
                    if getattr(self, "_startup_loading_card", None) and self._startup_loading_card.winfo_exists():
                        self._startup_loading_card.destroy()
                except Exception:
                    pass
                _dprint(f"✅ Página '{page_name}' carregada")
        except Exception as e:
            messagebox.showerror(self._get_text("error"),
                                 f"Falha ao abrir {self._translate_page_name(page_name)}:\n{e}", parent=self)
            _dprint(f"❌ Erro: {e}")
        finally:
            self._page_loading = False

    def _fit_current_page_to_content(self):
        frame = getattr(self, "_current_frame", None)
        if not frame or not frame.winfo_exists():
            return
        if not hasattr(self, "content") or not self.content.winfo_exists():
            return
        self.update_idletasks()
        try:
            frame.place_configure(x=0, y=0, relwidth=1, relheight=1)
        except:
            pass

    def _notify_current_page_resize(self, width: int | None = None, height: int | None = None):
        """Notifica a página atual (se suportar) o tamanho REAL do container 'content'.

        Isso é essencial para páginas responsivas (ex.: PAGAMENTO_SERVICOS) que ajustam minsize/escala.
        """
        frame = getattr(self, "_current_frame", None)
        if not frame or not getattr(frame, "winfo_exists", lambda: False)():
            return
        if not hasattr(frame, "on_host_resize"):
            return

        try:
            self.update_idletasks()
        except Exception:
            pass

        container = getattr(self, "content", None)
        if container is None:
            container = getattr(self, "content_frame", None)

        cw = ch = 0
        try:
            if container is not None and container.winfo_exists():
                cw = int(container.winfo_width() or 0)
                ch = int(container.winfo_height() or 0)
        except Exception:
            cw = ch = 0

        if cw <= 1:
            try:
                cw = int(width or self.winfo_width() or 0)
            except Exception:
                cw = int(width or 0)
        if ch <= 1:
            try:
                ch = int(height or self.winfo_height() or 0)
            except Exception:
                ch = int(height or 0)

        try:
            scale = float(getattr(self, "ui_scale", 1.0) or 1.0)
        except Exception:
            scale = 1.0

        try:
            frame.on_host_resize(max(1, cw), max(1, ch), scale)
        except Exception:
            pass

    def _show_temporary_message(self, message, duration=3000):
        try:
            for widget in self.content.winfo_children():
                widget.destroy()
            msg_frame = ctk.CTkFrame(
                self.content,
                fg_color=self.cor_secundaria,
                corner_radius=12,
                border_color=self.cor_borda,
                border_width=2
            )
            msg_frame.place(relx=0.5, rely=0.5, anchor="center")
            ctk.CTkLabel(
                msg_frame,
                text=message,
                font=("Arial", 14),
                text_color=self.cor_texto,
                wraplength=400
            ).pack(padx=30, pady=30)
            self.after(duration, self._return_to_dashboard)
        except Exception as e:
            _dprint(f"Erro ao exibir mensagem: {e}")

    def _return_to_dashboard(self):
        if self.user_manager.has_permission("Dashboard", "ver"):
            self.open_page("Dashboard")

    def _load_page_direct(self, page_name: str, reload_module: bool = False):
        route = self.routes.get(page_name)
        if not route:
            raise ValueError(f"Rota não encontrada: {page_name}")
        file_path = os.path.join(APP_DIR, route["file"])
        if not os.path.exists(file_path):
            file_path = os.path.join(ROOT_DIR, route["file"])
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        module_key = f"opera_page_{module_name}"
        if APP_DIR not in sys.path:
            sys.path.insert(0, APP_DIR)
        if ROOT_DIR not in sys.path:
            sys.path.insert(0, ROOT_DIR)
        try:
            if module_key in sys.modules and reload_module:
                module = importlib.reload(sys.modules[module_key])
            elif module_key in sys.modules:
                module = sys.modules[module_key]
            else:
                spec = importlib.util.spec_from_file_location(module_key, file_path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Spec inválido para {file_path}")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_key] = module
                spec.loader.exec_module(module)
        except Exception as e:
            raise ImportError(f"Erro ao importar {module_name}: {e}")
        class_name = route.get("class")
        page_class = None
        if class_name:
            page_class = getattr(module, class_name, None)
        if not page_class:
            for _, obj in inspect.getmembers(module, inspect.isclass):
                try:
                    if (issubclass(obj, ctk.CTkFrame) and
                            obj.__module__ == module.__name__):
                        page_class = obj
                        break
                except:
                    continue
        if not page_class:
            raise RuntimeError(f"Classe não encontrada em {file_path}")
        last_error = None
        try:
            from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
        except Exception:
            attach_i18n_support = None

        def _finalize_frame(frame_obj):
            """Padroniza integração da página com host e i18n global."""
            if frame_obj is None:
                return frame_obj
            try:
                if hasattr(frame_obj, "sistema"):
                    frame_obj.sistema = self
                if hasattr(frame_obj, "app"):
                    frame_obj.app = self
                if hasattr(frame_obj, "host"):
                    frame_obj.host = self
            except Exception:
                pass
            if callable(attach_i18n_support):
                try:
                    attach_i18n_support(frame_obj.__class__)
                except Exception:
                    pass
            try:
                if hasattr(frame_obj, "set_idioma"):
                    frame_obj.set_idioma(getattr(self, "idioma_atual", "pt_BR"))
                elif hasattr(frame_obj, "on_language_changed"):
                    frame_obj.on_language_changed(getattr(self, "idioma_atual", "pt_BR"))
                elif hasattr(frame_obj, "refresh_texts"):
                    frame_obj.refresh_texts()
            except Exception:
                pass
            return frame_obj

        # 1) padrão principal do sistema
        try:
            return _finalize_frame(page_class(master=self.content, sistema=self))
        except Exception as e:
            last_error = e

        # 2) algumas páginas usam "app"
        try:
            return _finalize_frame(page_class(master=self.content, app=self))
        except Exception as e:
            last_error = e

        # 3) algumas páginas antigas usam "host"
        try:
            return _finalize_frame(page_class(master=self.content, host=self))
        except Exception as e:
            last_error = e

        # 4) algumas páginas antigas usam "parent" em vez de "master"
        try:
            return _finalize_frame(page_class(self.content, sistema=self))
        except Exception as e:
            last_error = e

        # 5) fallback ainda mais compatível
        try:
            return _finalize_frame(page_class(self.content, app=self))
        except Exception as e:
            last_error = e

        try:
            return _finalize_frame(page_class(self.content, host=self))
        except Exception as e:
            last_error = e

        # 6) sem referência ao sistema
        try:
            return _finalize_frame(page_class(master=self.content))
        except Exception as e:
            last_error = e

        try:
            return _finalize_frame(page_class(self.content))
        except Exception as e:
            last_error = e

        # 7) se tudo falhar, mostra erro visual em vez de frame vazio "mudo"
        fallback = ctk.CTkFrame(self.content, fg_color=self.cor_fundo)

        try:
            ctk.CTkLabel(
                fallback,
                text=f"Erro ao abrir a página:\n{page_name}\n\n{last_error}",
                text_color=self.cor_texto,
                justify="left",
                wraplength=700,
                font=("Arial", 14)
            ).pack(padx=20, pady=20, anchor="w")
        except Exception:
            pass

        _dprint(f"❌ Falha ao instanciar '{page_name}': {last_error}")
        return fallback

    def reload_current_page(self):
        if hasattr(self, 'current_page') and self.current_page:
            _dprint(f"🔄 Recarregando: {self.current_page}")
            self.open_page(self.current_page)

    def _ativar_backup_silencioso(self):
        if getattr(self, "_backup_launch_scheduled", False):
            self._backup_launch_scheduled = False
        try:
            if not self.winfo_exists():
                self._backup_launch_scheduled = True
                self.after(5000, self._ativar_backup_silencioso)
                return
        except:
            pass
        try:
            route = self.routes.get("Backup", {})
            file_rel = route.get("file", "BACKUP.py")
            file_path = os.path.join(APP_DIR, file_rel)
            if not os.path.exists(file_path):
                file_path = os.path.join(ROOT_DIR, file_rel)
            module_key = "opera_page_BACKUP"
            if module_key in sys.modules:
                backup_module = sys.modules[module_key]
            else:
                spec = importlib.util.spec_from_file_location(module_key, file_path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Spec inválido para {file_path}")
                backup_module = importlib.util.module_from_spec(spec)
                sys.modules[module_key] = backup_module
                spec.loader.exec_module(backup_module)
            BACKUP_AUTO = backup_module.BACKUP_AUTO
            BackupPage = backup_module.BackupPage
        except Exception as e:
            _dprint(f"⚠️ Erro ao carregar backup: {e}")
            return
        if BACKUP_AUTO.get("running"):
            return
        _dprint("🔄 Inicializando backup silencioso...")
        base_dir = getattr(self, "diretorio_base", os.path.dirname(os.path.abspath(__file__)))
        pasta_backups = BackupPage.criar_pasta_backups_externo(base_dir)
        BACKUP_AUTO["running"] = True
        BACKUP_AUTO["interval"] = 3600
        BACKUP_AUTO["pasta"] = pasta_backups

        def loop():
            import time
            BackupPage._executar_backup_auto_silencioso_static()
            while BACKUP_AUTO.get("running", False):
                time.sleep(BACKUP_AUTO.get("interval", 3600))
                if BACKUP_AUTO.get("running", False):
                    BackupPage._executar_backup_auto_silencioso_static()

        t = threading.Thread(target=loop, daemon=True)
        BACKUP_AUTO["thread"] = t
        t.start()

    def trocar_usuario(self):
        try:
            modulo = importlib.import_module("PAGINAS_DO_SISTEMA.TROCAR_USUARIOS")
            modulo.abrir_janela_trocar_usuario(self)
        except Exception as e:
            _dprint(f"❌ Erro ao trocar usuário: {e}")
            messagebox.showerror("Erro", f"Falha ao abrir tela de login:\n{e}", parent=self)

    def _agendar_after(self, ms, func):
        if self._closing:
            return None
        try:
            return self.after(ms, func)
        except:
            return None


def remover_foco_e_bordas_menu(widget_root):
    import customtkinter as ctk
    import tkinter as tk
    def limpar(widget):
        try:
            if isinstance(widget, ctk.CTkButton):
                widget.configure(
                    border_width=0,
                    fg_color=widget.cget("fg_color"),
                    hover_color=widget.cget("hover_color"),
                    corner_radius=8
                )
            elif isinstance(widget, tk.Button):
                widget.configure(
                    highlightthickness=0,
                    bd=0,
                    borderwidth=0,
                    relief="flat"
                )
        except:
            pass
        for child in widget.winfo_children():
            limpar(child)

    limpar(widget_root)


def main():
    try:
        _dprint("🚀 Iniciando sistema OPERA...")
        app = OperaMenuApp()
        _dprint("✅ Aplicação iniciada, entrando no mainloop...")
        app.mainloop()
    except Exception as e:
        _dprint(f"💥 ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Erro Fatal", f"Erro ao iniciar o sistema:\n{e}")


if __name__ == "__main__":
    main()

# --- AUTO_PAGE_TRANSLATIONS (gerado automaticamente) ---
from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support as _attach_i18n_support

AUTO_PAGE_TRANSLATIONS = {
    "OperaMenuApp": {
        "pt_BR": {"title": "Opera Menu", "Atualizar": "Atualizar", "Filtrar": "Filtrar", "Salvar": "Salvar", "Cancelar": "Cancelar"},
        "en_US": {"title": "Opera Menu", "Atualizar": "Refresh", "Filtrar": "Filter", "Salvar": "Save", "Cancelar": "Cancel"},
        "es_ES": {"title": "Opera Menu", "Atualizar": "Actualizar", "Filtrar": "Filtrar", "Salvar": "Guardar", "Cancelar": "Cancelar"},
    },
}

for _cls_name, _map in AUTO_PAGE_TRANSLATIONS.items():
    _cls = globals().get(_cls_name)
    if isinstance(_cls, type):
        if not hasattr(_cls, "TRANSLATIONS") and not hasattr(_cls, "_TRANSLATIONS"):
            _cls.TRANSLATIONS = _map
        _attach_i18n_support(_cls, getattr(_cls, "TRANSLATIONS", getattr(_cls, "_TRANSLATIONS", _map)))
