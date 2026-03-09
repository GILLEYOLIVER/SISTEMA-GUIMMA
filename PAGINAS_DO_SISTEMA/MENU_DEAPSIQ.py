# -*- coding: utf-8 -*-
"""
MENU_PRINCIPAL.py - Sistema OPERA Refatorado
Menu principal com layout moderno (clean, sidebar com categorias expansíveis)
e todas as funcionalidades originais preservadas.
"""

import json
import platform
import importlib
import importlib.util
import inspect
import os
import sys
import threading
import time
import traceback
from datetime import datetime

import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk
import customtkinter as ctk

OPERA_DEBUG = bool(os.environ.get('OPERA_DEBUG', '').strip())

def _dprint(*args, **kwargs):
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

# ===== FUNÇÃO AUXILIAR DE DETECÇÃO DE COR ESCURA (FALLBACK) =====
def is_dark_color_fallback(hex_color: str) -> bool:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        luminancia = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminancia < 0.5
    except:
        return True

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
        default = {"theme": "Noite Urbana", "last_page": "Dashboard"}
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
                    _dprint(f"[Tema] Tema '{theme_name}' não encontrado. Usando 'Noite Urbana'.")
                    pal = ModuloPaletas().PADROES.get("Noite Urbana", {})
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
        self._update_menu_buttons_colors()

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
                    widget.configure(
                        border_width=0,
                        bg_color="transparent",
                        text_color=cor_texto,
                        font=fonts["button"],
                        corner_radius=getattr(widget, "corner_radius", 8),
                    )
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
                        button_hover_color=cor_hover_realcado,
                        text_color=cor_texto,
                        font=fonts["body"],
                        dropdown_fg_color=cor_secundaria,
                        dropdown_text_color=cor_texto,
                        dropdown_hover_color=cor_hover_realcado,
                    )
                    parar_recursao = True
                elif isinstance(widget, ctk.CTkOptionMenu):
                    try:
                        widget.configure(
                            fg_color=cor_secundaria,
                            button_color=cor_primaria,
                            button_hover_color=cor_hover_realcado,
                            text_color=cor_texto,
                            dropdown_fg_color=cor_secundaria,
                            dropdown_text_color=cor_texto,
                            dropdown_hover_color=cor_hover_realcado,
                        )
                    except Exception as e:
                        _dprint(f"[Tema][DEBUG] Falha ao ajustar CTkOptionMenu {_describe_widget(widget)}: {e}")
                    parar_recursao = True
                elif isinstance(widget, (ctk.CTkCheckBox, ctk.CTkSwitch)):
                    widget.configure(
                        fg_color=cor_secundaria,
                        border_color=cor_borda,
                        button_color=cor_primaria,
                        button_hover_color=cor_hover_realcado,
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
                            button_hover_color=cor_hover_realcado,
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
                        segmented_button_unselected_hover_color=cor_hover_realcado,
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
                padronizar_botoes_container,
                padronizar_treeviews_container,
                remover_bordas_botoes_tema,
            )
            remover_bordas_botoes_tema(self.app)
            padronizar_treeviews_container(self.app)
            padronizar_botoes_container(self.app)
        except Exception as e:
            _dprint(f"[Tema] Erro ao aplicar tema global: {e}")

    def apply_theme_to_widget(self, widget):
        if widget is None:
            return
        from PAGINAS_DO_SISTEMA.TEMAS import TemasPage
        palette = self.current_palette or {}
        if not palette:
            palette = TemasPage.PADROES.get(self.current_theme_name or "Noite Urbana", {})
        if not palette:
            _dprint("[Tema] Nenhuma paleta disponível para aplicar no widget.")
            return
        try:
            from PAGINAS_DO_SISTEMA.TEMAS import padronizar_botoes_container, padronizar_treeviews_container
            self._apply_palette_to_widget(widget, palette, self.fonts)
            padronizar_treeviews_container(widget)
            padronizar_botoes_container(widget)
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

    def _update_menu_buttons_colors(self):
        """Atualiza as cores dos botões do menu de acordo com o tema."""
        try:
            # Cores baseadas na paleta atual
            pal = self.current_palette or {}
            cor_fundo = pal.get("fundo", "#181818")
            cor_secundaria = pal.get("secundaria", "#1F1F1F")
            cor_texto = pal.get("texto", "#EEEEEE")
            cor_hover = pal.get("hover", "#2C2C2C")
            cor_destaque = pal.get("destaque", "#BB86FC")
            tema_escuro = is_dark_color(cor_fundo)

            if tema_escuro:
                menu_bg = cor_secundaria
                menu_texto = cor_texto
                hover_bg = cor_hover
                submenu_bg = self._realcar_cor(cor_secundaria, 1.1)
                submenu_texto = cor_texto
                active_bg = cor_destaque
                active_texto = get_contraste_texto(active_bg)
            else:
                menu_bg = cor_secundaria
                menu_texto = cor_texto
                hover_bg = cor_hover
                submenu_bg = self._realcar_cor(cor_secundaria, 0.95)
                submenu_texto = cor_texto
                active_bg = cor_destaque
                active_texto = get_contraste_texto(active_bg)

            # Atualiza sidebar e topbar
            if hasattr(self.app, 'sidebar') and self.app.sidebar.winfo_exists():
                self.app.sidebar.configure(fg_color=menu_bg)
            if hasattr(self.app, 'topbar') and self.app.topbar.winfo_exists():
                self.app.topbar.configure(fg_color=menu_bg)

            # Atualiza botões de categoria
            for categoria, btn_info in self.app.botoes_menu.items():
                if not btn_info["frame"].winfo_exists():
                    continue
                ativo = (categoria == self.app._active_submenu)
                cor_fg = active_bg if ativo else menu_bg
                cor_txt = active_texto if ativo else menu_texto
                btn_info["button"].configure(
                    fg_color=cor_fg,
                    hover_color=hover_bg,
                    text_color=cor_txt,
                )

            # Atualiza subitens
            for categoria, subframe in self.app.submenu_frames.items():
                if not subframe.winfo_exists():
                    continue
                for btn in getattr(subframe, "_submenu_buttons", []):
                    if not btn.winfo_exists():
                        continue
                    item_name = getattr(btn, "_menu_item_name", "")
                    selected = (self.app.current_page == item_name)
                    btn.configure(
                        fg_color=active_bg if selected else submenu_bg,
                        hover_color=hover_bg,
                        text_color=active_texto if selected else submenu_texto,
                    )
            _dprint("[Tema] Cores do menu atualizadas.")
        except Exception as e:
            _dprint(f"[Tema] Erro ao atualizar cores do menu: {e}")

# ===== GERENCIADOR DE USUÁRIOS =====
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
        default_theme = "Noite Urbana"
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
                return default_theme, None
            tema_nome, usar_custom, tema_json = row
            if usar_custom and tema_json:
                try:
                    paleta = json.loads(tema_json)
                    return tema_nome, paleta
                except json.JSONDecodeError:
                    pass
            return tema_nome, None

    def save_user_theme(self, theme_name: str):
        if not getattr(self.app, "usuario_id", None):
            return
        schema = get_schema()
        try:
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
        except Exception as e:
            _dprint(f"[UserManager][ERRO] Falha ao salvar tema padrão '{theme_name}': {e}")

    def save_user_theme_personalizado(self, theme_name: str, palette_json: str):
        if not getattr(self.app, "usuario_id", None):
            return
        schema = get_schema()
        try:
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
        except Exception as e:
            _dprint(f"[UserManager][ERRO] Falha ao salvar tema personalizado '{theme_name}': {e}")

    def _is_admin(self) -> bool:
        hierarquia = getattr(self.app, "usuario_hierarquia", "")
        return hierarquia and str(hierarquia).strip().lower() in ("admin", "administrador", "superusuario")

    def load_user_permissions(self):
        if not self.usuario_id:
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
            return self.permissoes
        except Exception as e:
            _dprint(f"[Permissões] ❌ Erro ao carregar permissões: {e}")
            self.permissoes = {}
            return {}

    def has_permission(self, pagina: str, acao: str = "ver", categoria: str | None = None) -> bool:
        if self._is_admin():
            return True
        permissoes = getattr(self.app, "permissoes_usuario", {})
        from MENU_PRINCIPAL import OperaMenuApp
        codigo = None
        if categoria:
            codigo = OperaMenuApp.PAGE_PERMISSION_MAP.get(f"{categoria}:{pagina}")
        if not codigo:
            codigo = OperaMenuApp.PAGE_PERMISSION_MAP.get(pagina)
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
    """Aplicação principal do sistema OPERA - Layout moderno com todas as funcionalidades."""

    SIDEBAR_WIDTH = 260
    TOPBAR_HEIGHT = 60

    # Mantém os mapeamentos originais
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
        "ORDENS DE CORTE": ["Nova Ordem", "Ordens de Corte Impressão"],
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
        "ORDENS DE CORTE": {"Nova Ordem": "NOVA_ORDEM.png", "Ordens de Corte Impressão": "IMPRESSORA.png"},
        "REGISTRO DE CORTE": {"Cadastrar Corte": "CADASTRO_CORTE.png", "Consultar Ordens": "CONSULTAR ORDENS.png"},
        "COMPRAS": {"Compras": "DINHEIRO.png"},
        "ESTOQUE": {"Entrada de Estoque": "ESTOQUE.png", "Saída de Estoque": "ESTOQUE.png", "Relatórios": "RELATORIO 2.png"},
        "COMERCIAL": {"Clientes": "USUARIOS.png"},
        "PRESTADORES": {"Cadastro de Prestadores": "FACÇAO.png", "Pesquisar Serviço": "CONSULTAR ORDENS.png"},
        "MÃO DE OBRA": {"Controle de Mão de Obra": "MAO DE OBRA.png"},
        "PLANEJAMENTO": {"MRP": "RELATORIO.png", "Planejamento de Produção": "PRODUÇAO.png", "Custos Reais": "RELATORIO.png"},
        "PRODUÇÃO": {"Produção": "PRODUÇAO.png"},
        "ACABAMENTO": {"Registro Acabamento": "ACABAMENTO.png", "Finalizar Corte / Acabamento": "ACABAMENTO.png", "Retrabalho de Defeitos": "ACABAMENTO.png"},
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

    def __init__(self, usuario_id=None, usuario_nome="Admin", usuario_hierarquia="Administrador", tema_preferido=None):
        reset_tk_default_root()
        super().__init__()

        self._preload_complete = False
        initialize_after_guard(self)

        self._current_ui_scale = None
        self._pending_responsive_job = None
        self._responsive_reflow_lock = False
        self._window_scale_applied = False
        self._startup_responsive_ready = False
        self._last_configure_size = None

        # Cores padrão (serão sobrescritas pelo tema)
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
        self.tema_preferido_inicial = tema_preferido or self.settings.get("theme") or "Noite Urbana"

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
        self.submenu_frames = {}          # {categoria: frame}
        self.botoes_menu = {}             # {categoria: {"frame": frame, "button": btn}}
        self._submenu_close_jobs = {}
        self.icons_cache = {}
        self._active_submenu = None
        self._submenu_timer = None
        self._page_cache = {}
        self._page_cache_order = []
        self._page_cache_size = 3
        self._current_frame = None
        self._backup_launch_scheduled = False
        self.permissoes_usuario = {}

        self._calculate_initial_scale_and_fonts()
        self._setup_window()
        _dprint("🎨 Iniciando carregamento do tema...")
        self._load_initial_theme()
        self._load_icons()
        self._build_interface()   # layout moderno
        self._load_user_permissions()
        self._setup_bindings()
        self._setup_activity_logging()
        self._setup_responsive_watcher()
        self._preload_complete = True

        self.deiconify()
        self.lift()
        self.focus_force()
        self._apply_initial_layout()
        self._open_dashboard_agora()
        self._agendar_after(100, self._update_user_display)
        self._agendar_after(5000, self._ativar_backup_silencioso)

        _dprint(f"✅ Sistema inicializado para: {self.usuario_nome} ({self.usuario_hierarquia})")
        _dprint(f"🎨 Tema aplicado: {self.current_theme_name}")

    # ================== MÉTODOS AUXILIARES (preservados) ==================
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
        self.SIDEBAR_WIDTH = max(220, int(260 * self.ui_scale))
        self.ITEM_HEIGHT = max(32, int(44 * self.ui_scale))
        self.TOPBAR_HEIGHT = max(36, int(60 * self.ui_scale))

    def _apply_initial_layout(self):
        self._maximize_window()
        self.update_idletasks()

    def _setup_responsive_watcher(self):
        self.bind("<Configure>", self._on_window_configure, add="+")

    def _on_window_configure(self, event):
        if event.widget is not self:
            return
        if not getattr(self, "_preload_complete", False):
            return
        size_key = (int(event.width), int(event.height))
        if getattr(self, "_last_resize_seen", None) == size_key and self._pending_responsive_job:
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
        self._pending_responsive_job = self.after(120, _apply_resize)

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
            old_scale = float(getattr(self, "ui_scale", 1.0))
            mode_changed = initial or abs(old_scale - new_scale) >= 0.01
            if not mode_changed:
                return
            self.ui_scale = new_scale
            self.SIDEBAR_WIDTH = max(220, int(260 * self.ui_scale))
            self.ITEM_HEIGHT = max(32, int(44 * self.ui_scale))
            self.TOPBAR_HEIGHT = max(36, int(60 * self.ui_scale))
            if hasattr(self, "sidebar") and self.sidebar.winfo_exists():
                self.grid_columnconfigure(0, weight=0, minsize=self.SIDEBAR_WIDTH + 16)
                self.sidebar.configure(width=self.SIDEBAR_WIDTH)
            if hasattr(self, "topbar") and self.topbar.winfo_exists():
                self.topbar.configure(height=self.TOPBAR_HEIGHT)
            if hasattr(self, "menu_frame") and self.menu_frame.winfo_exists():
                self._hide_all_submenus()
                self._load_icons()
                self._build_menu_content()
            self.update_idletasks()
            if self._active_submenu and self._active_submenu in self.submenu_frames:
                self.after_idle(lambda: self._show_submenu(self._active_submenu))
        finally:
            self._responsive_reflow_lock = False

    def _calculate_ui_scale(self, width: int, height: int) -> float:
        if width < 1500 or height < 900:
            return 0.78
        return 1.0

    def _show_submenu(self, categoria: str):
        frame = self.submenu_frames.get(categoria)
        if not frame:
            return
        # Esconde todos os outros
        for nome, outro_frame in self.submenu_frames.items():
            if nome != categoria and outro_frame.winfo_ismapped():
                outro_frame.pack_forget()
        # Mostra o atual
        if not frame.winfo_ismapped():
            frame.pack(fill="x", padx=0, pady=(0, 8))
        self._active_submenu = categoria
        self.theme_manager._update_menu_buttons_colors()

    def _hide_submenu(self, categoria: str):
        frame = self.submenu_frames.get(categoria)
        if frame and frame.winfo_ismapped():
            frame.pack_forget()
        if self._active_submenu == categoria:
            self._active_submenu = None
            self.theme_manager._update_menu_buttons_colors()

    def _hide_all_submenus(self):
        for frame in self.submenu_frames.values():
            if frame.winfo_ismapped():
                try:
                    frame.pack_forget()
                except Exception:
                    pass
        if self._active_submenu:
            self._active_submenu = None
            self.theme_manager._update_menu_buttons_colors()
        if self._submenu_timer:
            try:
                self.after_cancel(self._submenu_timer)
            except Exception:
                pass
            self._submenu_timer = None

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
            _dprint(f"⚠️ Erro ao abrir Dashboard: {e}")

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
        try:
            confirmar = messagebox.askyesno("Sair", "Deseja realmente sair do sistema?", parent=self)
        except Exception:
            confirmar = messagebox.askyesno("Sair", "Deseja realmente sair do sistema?")
        if confirmar:
            self._agendar_after(1, self.destroy)

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

    # ================== LOGGING (preservado) ==================
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
        if not MENU_POSTGRES_AVAILABLE:
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
        registrar_log_db(self.usuario_nome, acao, pagina_log, detalhe_log)

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

    # ================== CARREGAMENTO DE TEMA E ÍCONES ==================
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

    def _load_icons(self):
        _dprint("🔄 Carregando ícones...")
        self.icons_cache = {}
        for categoria, filename in self.ICON_MAPPING.items():
            try:
                icon_path = os.path.join(ICONS_DIR, filename)
                if os.path.exists(icon_path):
                    image = Image.open(icon_path)
                    self.icons_cache[categoria] = ctk.CTkImage(
                        light_image=image, dark_image=image, size=(24, 24)
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
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
                icon = ctk.CTkImage(light_image=image, dark_image=image, size=(20, 20))
                self.icons_cache[cache_key] = icon
                return icon
        except Exception as e:
            _dprint(f"❌ Erro ao carregar ícone de submenu {filename}: {e}")
        return None

    # ================== CONSTRUÇÃO DA INTERFACE (LAYOUT MODERNO) ==================
    def _build_interface(self):
        self.grid_columnconfigure(0, weight=0, minsize=self.SIDEBAR_WIDTH + 16)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.configure(fg_color=self.cor_fundo)

        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        # Sidebar com cor de fundo secundária
        self.sidebar = ctk.CTkFrame(
            self,
            width=self.SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=self.cor_secundaria,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo e título
        header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(30, 20))

        try:
            icon_path = os.path.join(APP_DIR, "ICONE_SISTEMA.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                img = ctk.CTkImage(light_image=img, dark_image=img, size=(40, 40))
                icon_label = ctk.CTkLabel(header, image=img, text="")
                icon_label.pack(side="left", padx=(0, 12))
                self._brand_icon_ref = img
        except Exception as e:
            _dprint(f"⚠️ Erro ao carregar ícone no sidebar: {e}")

        titulos = ctk.CTkFrame(header, fg_color="transparent")
        titulos.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(
            titulos,
            text="OPERA",
            font=("Segoe UI", 24, "bold"),
            text_color=self.cor_destaque,
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            titulos,
            text="Gestão Industrial",
            font=("Segoe UI", 12),
            text_color=self.cor_texto_secundario,
            anchor="w",
        ).pack(anchor="w")

        # Separador
        sep = ctk.CTkFrame(self.sidebar, fg_color=self.cor_borda, height=1)
        sep.pack(fill="x", padx=20, pady=10)

        # Área rolável do menu
        scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        self.menu_frame = scroll  # para compatibilidade

        # Criar botões de categoria
        for categoria in self.MENU_ESTRUTURA.keys():
            self._create_category_button(scroll, categoria)

    def _create_category_button(self, parent, categoria: str):
        # Frame que contém o botão principal e, possivelmente, o submenu
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=2)

        subs = self.MENU_ESTRUTURA.get(categoria, [])
        tem_sub = bool(subs and any(self.user_manager.has_permission(item, "ver", categoria) for item in subs))

        icon = self.icons_cache.get(categoria)

        if tem_sub:
            # Botão principal com seta (não abre página, apenas expande)
            btn = ctk.CTkButton(
                frame,
                text=f"  {categoria}",
                image=icon,
                compound="left",
                anchor="w",
                height=self.ITEM_HEIGHT,
                fg_color="transparent",
                hover_color=self.cor_hover,
                text_color=self.cor_texto,
                font=("Segoe UI", 13, "bold"),
                corner_radius=0,
                border_width=0,
                command=lambda c=categoria: self._toggle_category(c)
            )
            btn.pack(fill="x")

            # Submenu (inicialmente oculto)
            sub_frame = ctk.CTkFrame(frame, fg_color="transparent")
            sub_frame.pack(fill="x", padx=(25, 0))
            sub_frame.pack_forget()  # oculto

            # Criar itens do submenu (somente os permitidos)
            for item in subs:
                if not self.user_manager.has_permission(item, "ver", categoria):
                    continue
                sub_icon = self._get_submenu_icon(categoria, item)
                sub_btn = ctk.CTkButton(
                    sub_frame,
                    text=f"    {item}",
                    image=sub_icon,
                    compound="left",
                    anchor="w",
                    height=self.ITEM_HEIGHT - 4,
                    fg_color="transparent",
                    hover_color=self.cor_hover,
                    text_color=self.cor_texto,
                    font=("Segoe UI", 12),
                    corner_radius=0,
                    border_width=0,
                    command=lambda i=item: self.open_page(i, categoria)
                )
                sub_btn.pack(fill="x", pady=1)
                sub_btn._menu_item_name = item
                sub_btn._menu_categoria = categoria

            self.botoes_menu[categoria] = {"frame": frame, "button": btn}
            self.submenu_frames[categoria] = sub_frame
            sub_frame._submenu_buttons = sub_frame.winfo_children()  # guarda referência para atualização de cores
        else:
            # Categoria sem submenu: abre página diretamente
            btn = ctk.CTkButton(
                frame,
                text=f"  {categoria}",
                image=icon,
                compound="left",
                anchor="w",
                height=self.ITEM_HEIGHT,
                fg_color="transparent",
                hover_color=self.cor_hover,
                text_color=self.cor_texto,
                font=("Segoe UI", 13, "bold"),
                corner_radius=0,
                border_width=0,
                command=lambda c=categoria: self.open_page(c)
            )
            btn.pack(fill="x")
            self.botoes_menu[categoria] = {"frame": frame, "button": btn}

    def _toggle_category(self, categoria: str):
        if categoria not in self.submenu_frames:
            return
        if self._active_submenu == categoria:
            self._hide_submenu(categoria)
        else:
            self._hide_all_submenus()
            self._show_submenu(categoria)

    def _build_main_area(self):
        self.main = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=self.cor_fundo,
        )
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        # Topbar
        self.topbar = ctk.CTkFrame(
            self.main,
            height=self.TOPBAR_HEIGHT,
            fg_color=self.cor_primaria,
            corner_radius=0,
        )
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)

        # Título da página
        self.title_label = ctk.CTkLabel(
            self.topbar,
            text="Dashboard",
            font=("Segoe UI", 20, "bold"),
            text_color=self.cor_texto,
        )
        self.title_label.pack(side="left", padx=30, pady=12)

        # Botões à direita
        right_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        right_frame.pack(side="right", padx=20)

        # Relógio
        self.lbl_clock = ctk.CTkLabel(
            right_frame,
            text="",
            font=("Segoe UI", 13),
            text_color=self.cor_texto_secundario,
        )
        self.lbl_clock.pack(side="left", padx=15)

        # Informações do usuário
        self.lbl_user = ctk.CTkLabel(
            right_frame,
            text=f"{self.usuario_nome} • {self.usuario_hierarquia}",
            font=("Segoe UI", 13),
            text_color=self.cor_texto,
        )
        self.lbl_user.pack(side="left", padx=15)

        # Botão refresh
        self.btn_refresh = ctk.CTkButton(
            right_frame,
            text="↻",
            width=32,
            height=32,
            font=("Segoe UI", 16),
            fg_color="transparent",
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            corner_radius=4,
            command=self.reload_current_page,
        )
        self.btn_refresh.pack(side="left", padx=5)

        # Botão trocar usuário
        self.btn_switch_user = ctk.CTkButton(
            right_frame,
            text="👤",
            width=32,
            height=32,
            font=("Segoe UI", 16),
            fg_color="transparent",
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            corner_radius=4,
            command=self.trocar_usuario,
        )
        self.btn_switch_user.pack(side="left", padx=5)

        # Switch de tema
        self._add_theme_switch_to_topbar(right_frame)

        # Área de conteúdo
        self.content = ctk.CTkFrame(self.main, fg_color=self.cor_fundo)
        self.content.pack(fill="both", expand=True, padx=15, pady=15)

        # Iniciar atualização do relógio
        self._start_clock()

    def _add_theme_switch_to_topbar(self, parent):
        is_dark = self.current_theme_name and "NOTURNO" in self.current_theme_name.upper()
        icon_text = "🌙" if is_dark else "☀️"

        self.icon_theme = ctk.CTkLabel(
            parent,
            text=icon_text,
            font=("Segoe UI", 16),
            text_color=self.cor_texto,
        )
        self.icon_theme.pack(side="left", padx=(10, 5))

        self.theme_switch = ctk.CTkSwitch(
            parent,
            text="",
            width=44,
            height=22,
            switch_width=44,
            switch_height=22,
            fg_color="#A3A3A3",
            progress_color="#3B82F6",
            button_color="#FFFFFF",
            button_hover_color="#E5E5E5",
            command=self._toggle_theme_mode
        )
        if is_dark:
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
        self.theme_switch.pack(side="left", padx=5)

    def _toggle_theme_mode(self):
        if self.theme_switch.get() == 1:
            novo_tema = "NOTURNO"
            self.current_theme_name = novo_tema
            if hasattr(self, 'usuario_id') and self.usuario_id:
                try:
                    self.user_manager.save_user_theme(novo_tema)
                except Exception as e:
                    _dprint("[Tema] Erro ao salvar tema:", e)
            self.theme_manager.apply_theme(novo_tema, rebuild_interface=False)
        else:
            if hasattr(self, 'usuario_id') and self.usuario_id:
                tema_usuario, paleta_personalizada = self.user_manager.load_user_theme_completo()
                if not tema_usuario or tema_usuario.upper() == "NOTURNO":
                    tema_usuario = "CLÁSSICO CLARO"
            else:
                tema_usuario = "CLÁSSICO CLARO"
                paleta_personalizada = None
            self.current_theme_name = tema_usuario
            if paleta_personalizada:
                self.theme_manager.apply_theme(tema_usuario, paleta_personalizada, rebuild_interface=False)
            else:
                self.theme_manager.apply_theme(tema_usuario, rebuild_interface=False)
        # Atualiza ícone do tema
        self.icon_theme.configure(text="🌙" if self.theme_switch.get() == 1 else "☀️")

    def _start_clock(self):
        def update():
            if hasattr(self, 'lbl_clock') and self.lbl_clock.winfo_exists():
                self.lbl_clock.configure(text=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                self.after(1000, update)
        update()

    # ================== GERENCIAMENTO DE PÁGINAS (preservado) ==================
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

    def open_page(self, page_name: str, categoria: str | None = None):
        if getattr(self, "_page_loading", False) or getattr(self, "_closing", False):
            return
        route_action = (self.routes.get(page_name) or {}).get("action")
        if page_name == "Trocar Usuário" or route_action == "trocar_usuario":
            self.trocar_usuario()
            return
        if not self.user_manager.has_permission(page_name, "ver", categoria):
            self._show_temporary_message(f"Sem permissão para acessar {page_name}")
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
                frame.place(x=0, y=0, relwidth=1, relheight=1)
                if hasattr(self, "title_label"):
                    self.title_label.configure(text=page_name)
                try:
                    if hasattr(frame, "host"):
                        frame.host = self
                    if hasattr(frame, "sistema"):
                        frame.sistema = self
                    if hasattr(frame, "app"):
                        frame.app = self
                    if hasattr(self, "theme_manager"):
                        self.theme_manager.apply_theme_to_widget(frame)
                except Exception as e:
                    _dprint(f"⚠️ Erro ao aplicar tema: {e}")
                self.current_page = page_name
                self._current_frame = frame
                if page_name == "Dashboard":
                    self._active_submenu = None
                elif categoria:
                    self._active_submenu = categoria
                self.theme_manager._update_menu_buttons_colors()
                try:
                    self.settings["last_page"] = page_name
                    ConfigManager.save_settings(self.settings)
                except:
                    pass
                _dprint(f"✅ Página '{page_name}' carregada")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Erro", f"Falha ao abrir {page_name}:\n{e}", parent=self)
            _dprint(f"❌ Erro: {e}")
        finally:
            self._page_loading = False

    def _show_temporary_message(self, message, duration=3000):
        try:
            for widget in self.content.winfo_children():
                widget.destroy()
            msg_frame = ctk.CTkFrame(
                self.content,
                fg_color=self.cor_secundaria,
                corner_radius=8,
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
        try:
            return page_class(master=self.content, sistema=self)
        except:
            try:
                return page_class(master=self.content, app=self)
            except:
                try:
                    return page_class(master=self.content)
                except:
                    fallback = ctk.CTkFrame(self.content)
                    fallback.configure(fg_color=self.cor_fundo)
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

    def _update_user_display(self):
        if hasattr(self, 'lbl_user') and self.lbl_user.winfo_exists():
            self.lbl_user.configure(text=f"{self.usuario_nome} • {self.usuario_hierarquia}")

def main():
    try:
        _dprint("🚀 Iniciando sistema OPERA...")
        app = OperaMenuApp()
        _dprint("✅ Aplicação iniciada, entrando no mainloop...")
        app.mainloop()
    except Exception as e:
        _dprint(f"💥 ERRO CRÍTICO: {e}")
        traceback.print_exc()
        messagebox.showerror("Erro Fatal", f"Erro ao iniciar o sistema:\n{e}")

if __name__ == "__main__":
    main()