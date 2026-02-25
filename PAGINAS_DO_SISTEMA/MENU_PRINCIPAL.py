# -*- coding: utf-8 -*-
"""
MENU_PRINCIPAL.py - Sistema OPERA Refatorado
Menu principal com sistema de temas, permissões e cache otimizado.
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
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from tkinter import messagebox, ttk
from tkinter import font as tkfont
from PIL import Image
import customtkinter as ctk

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from PAGINAS_DO_SISTEMA.TEMAS import (
    TemasPage,
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
    print("✅ Função de logs disponível.")
except ImportError as e:
    LOGS_DISPONIVEIS = False
    print(f"⚠️ Logs não disponíveis: {e}")


    def registrar_log_db(usuario, acao, pagina, detalhe=""):
        """Função fallback para logs."""
        pass

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema

    MENU_POSTGRES_AVAILABLE = True
    print("✅ PostgreSQL disponível.")
except Exception as e:
    print(f"❌ PostgreSQL indisponível: {e}")
    MENU_POSTGRES_AVAILABLE = False

    def get_conn():
        raise RuntimeError("PostgreSQL indisponível")

    def get_schema():
        return "opera"

# ===== CONFIGURAÇÕES GLOBAIS =====
IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"
BASE_DIR = os.path.dirname(APP_DIR)
ROOT_DIR = os.path.dirname(SRC_DIR)

# JESUS SEJA LOUVADO PARA TODO O SEMPRE AMEM!!!
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
                print(f"⚠️ Falha ao carregar rotas em {path}: {exc}")
        return {}

    @staticmethod
    def ensure_icons_directory():
        """Garante que a pasta de ícones existe."""
        if not os.path.exists(ICONS_DIR):
            print(f"📁 Criando pasta de ícones: {ICONS_DIR}")
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

    def apply_theme(self, theme_name: str, palette: dict | None = None):
        """Aplica o tema informado (padrão ou personalizado) consistentemente."""
        import customtkinter as ctk
        from PAGINAS_DO_SISTEMA.TEMAS import TemasPage, is_dark_color

        # Obtém a paleta
        if palette:
            pal = dict(palette)  # cópia defensiva
            print(f"[Tema] Aplicando paleta personalizada para '{theme_name}'.")
        else:
            pal = TemasPage.PADROES.get(theme_name)
            if not pal:
                print(f"[Tema] Tema '{theme_name}' não encontrado. Usando 'Noite Urbana'.")
                pal = TemasPage.PADROES.get("Noite Urbana", {})
            else:
                pal = dict(pal)
                print(f"[Tema] Aplicando tema padrão '{theme_name}'.")

        # Guardar estado atual do tema
        self.current_theme_name = theme_name
        self.current_palette = pal

        # Atualiza cores no app PRIMEIRO (cor_fundo, cor_primaria, etc.)
        try:
            for chave, valor in pal.items():
                setattr(self.app, f"cor_{chave}", valor)
        except Exception as e:
            print(f"[Tema] Erro ao aplicar atributos de cor no app: {e}")

        # Ajusta estilos base de botões antes de estilizar widgets existentes
        self._configure_button_styles(pal)

        # Atualiza fontes base compartilhadas
        self._configure_base_fonts()

        # Define modo claro/escuro
        try:
            fundo = pal.get("fundo", "#000000")
            modo = "dark" if is_dark_color(fundo) else "light"
            ctk.set_appearance_mode(modo)
            self.app.tema_modo = modo
        except Exception as e:
            print(f"[Tema] Erro ao definir modo claro/escuro: {e}")

        # Ajusta o tema padrão do CustomTkinter para que novos widgets sigam o modo atual
        try:
            ctk.set_default_color_theme("dark" if getattr(self.app, "tema_modo", "dark") == "dark" else "light")
        except Exception:
            pass

        # Aplica globalmente a paleta nos widgets já existentes
        self._apply_global_theme(pal)

        # Reconstrói a interface completamente (sidebar, topbar, etc.)
        self._rebuild_interface()

        # Persiste preferências locais para que novas páginas herdem o tema
        self._persist_theme_choice(theme_name, pal)

        print(f"[Tema] Tema '{theme_name}' aplicado com sucesso!")

    def _default_fonts(self):
        """Retorna o conjunto padrão de fontes para o sistema."""
        return {
            "title": ("Arial", 14, "bold"),
            "heading": ("Arial", 12, "bold"),
            "body": ("Arial", 12),
            "small": ("Arial", 11),
            "button": ("Arial", 12, "bold"),
        }

    def _configure_button_styles(self, palette: dict):
        """Configura estilos base para botões Tk/ttk antes da aplicação recursiva."""
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
            print(f"[Tema] Erro ao configurar estilos base de botões: {e}")

        try:
            # Remove bordas e destaques padrão de botões Tk
            self.app.option_add("*Button.highlightthickness", 0)
            self.app.option_add("*Button.borderwidth", 0)
            self.app.option_add("*Button.relief", tk.FLAT)
            self.app.option_add("*Button.highlightcolor", cor_secundaria)
            self.app.option_add("*Button.highlightbackground", cor_secundaria)
        except Exception:
            pass

    def _configure_base_fonts(self):
        """Garante que todas as páginas utilizem as mesmas fontes base."""
        try:
            self.app.font_title = self.fonts["title"]
            self.app.font_heading = self.fonts["heading"]
            self.app.font_body = self.fonts["body"]
            self.app.font_small = self.fonts["small"]
            self.app.font_button = self.fonts["button"]
        except Exception as e:
            print(f"[Tema] Erro ao configurar fontes base: {e}")

    def _apply_palette_to_widget(self, root_widget, palette: dict, fonts: dict):
        """Aplica a paleta informada recursivamente em um widget raiz."""
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

        # Hover realçado
        cor_hover_realcado = self._realcar_cor(cor_secundaria, 1.3)

        # === Estilo básico para Treeview (com bom contraste) ===
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
            print(f"[Tema] Erro ao aplicar estilo Treeview: {e}")

        # === Estilo base para ttk.Button ===
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
            print(f"[Tema] Erro ao aplicar tema em botões ttk: {e}")

        # ========== FUNÇÃO RECURSIVA ==========
        def _describe_widget(widget) -> str:
            try:
                name = widget.winfo_name()
                cls = widget.__class__.__name__
                master = widget.master.winfo_name() if getattr(widget, "master", None) else "(sem master)"
                return f"{cls}('{name}' em '{master}')"
            except Exception:
                return repr(widget)

        def _apply_to_all_widgets(widget):
            """Aplica tema a um widget e, se for container, aos filhos."""
            import customtkinter as ctk
            import tkinter as tk
            from tkinter import ttk

            # Se True, NÃO entra nos filhos (pra não mexer nos widgets internos do CTk)
            parar_recursao = False

            try:
                # ====== WIDGETS CUSTOMTKINTER ======

                # Frames principais podem ter filhos tratados normalmente
                if isinstance(widget, ctk.CTkFrame):
                    widget.configure(fg_color=cor_fundo, border_color=cor_borda)
                    parar_recursao = False

                elif isinstance(widget, ctk.CTkButton):
                    # NÃO mexer em fg_color → respeita BotaoPadronizado
                    widget.configure(
                        border_width=0,
                        bg_color="transparent",
                        text_color=cor_texto,
                        font=fonts["button"],
                        corner_radius=getattr(widget, "corner_radius", 8),
                    )
                    # Não entrar nos filhos internos do CTkButton
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
                        print(f"[Tema][DEBUG] Falha ao ajustar CTkOptionMenu {_describe_widget(widget)}: {e}")
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
                        print(f"[Tema][DEBUG] Falha ao ajustar CTkProgressBar {_describe_widget(widget)}: {e}")
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
                        print(f"[Tema][DEBUG] Falha ao ajustar CTkScrollbar {_describe_widget(widget)}: {e}")
                    parar_recursao = True

                elif isinstance(widget, ctk.CTk):
                    try:
                        widget.configure(fg_color=cor_fundo)
                    except Exception as e:
                        print(f"[Tema][DEBUG] Falha ao ajustar CTk root {_describe_widget(widget)}: {e}")
                    parar_recursao = False

                elif isinstance(widget, ctk.CTkToplevel):
                    try:
                        widget.configure(fg_color=cor_fundo)
                    except Exception as e:
                        print(f"[Tema][DEBUG] Falha ao ajustar CTkToplevel {_describe_widget(widget)}: {e}")
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
                    # Não entrar na estrutura interna do CTkTabview
                    parar_recursao = True

                elif isinstance(widget, ctk.CTkScrollableFrame):
                    widget.configure(fg_color=cor_fundo, border_color=cor_borda)
                    # Pode ter conteúdo seu dentro → manter recursão
                    parar_recursao = False

                # ====== TREEVIEW ======
                elif isinstance(widget, ttk.Treeview):
                    padronizar_treeview(widget)
                    # Evitar entrar na estrutura interna do Treeview
                    parar_recursao = True

                # ====== BOTÕES / LABELS / FRAMES TK/TTK ======
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
                            style=
                            "Opera.Vertical.TScrollbar" if orient == "vertical" else "Opera.Horizontal.TScrollbar"
                        )
                    except Exception as e:
                        print(f"[Tema][DEBUG] Falha ao ajustar ttk.Scrollbar {_describe_widget(widget)}: {e}")
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
                        print(f"[Tema][DEBUG] Falha ao ajustar tk.Scrollbar {_describe_widget(widget)}: {e}")
                    parar_recursao = True

                elif isinstance(widget, tk.Canvas):
                    try:
                        widget.configure(bg=cor_fundo, highlightthickness=0, bd=0)
                    except Exception as e:
                        print(f"[Tema][DEBUG] Falha ao ajustar tk.Canvas {_describe_widget(widget)}: {e}")
                    parar_recursao = False

                elif isinstance(widget, ttk.Button):
                    widget.configure(style="Opera.TButton")
                    parar_recursao = True  # normalmente ttk.Button não tem filhos

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
                    parar_recursao = False  # frames são containers normais

                else:
                    print(f"[Tema][DEBUG] Widget não tratado: {_describe_widget(widget)}")

            except Exception as e:
                print(f"[Tema] Erro ao aplicar tema em widget {_describe_widget(widget)}: {e}")

            # === Recursão apenas se não for widget complexo do CTk / ttk ===
            if not parar_recursao:
                try:
                    for child in widget.winfo_children():
                        _apply_to_all_widgets(child)
                except Exception:
                    pass

        # Aplica tema globalmente começando pela raiz
        _apply_to_all_widgets(root_widget)

    def _apply_global_theme(self, palette: dict):
        try:
            self._apply_palette_to_widget(self.app, palette, self.fonts)

            # CORREÇÃO CRÍTICA — EVITA CAIXAS QUADRADAS
            from PAGINAS_DO_SISTEMA.TEMAS import (
                padronizar_botoes_container,
                padronizar_treeviews_container,
                remover_bordas_botoes_tema,
            )
            remover_bordas_botoes_tema(self.app)
            padronizar_treeviews_container(self.app)
            padronizar_botoes_container(self.app)

        except Exception as e:
            print(f"[Tema] Erro ao aplicar tema global: {e}")

    def apply_theme_to_widget(self, widget):
        """Aplica o tema atual a um widget específico (ex.: páginas recém-carregadas)."""
        if widget is None:
            return

        from PAGINAS_DO_SISTEMA.TEMAS import TemasPage

        palette = self.current_palette or {}
        if not palette:
            palette = TemasPage.PADROES.get(self.current_theme_name or "Noite Urbana", {})

        if not palette:
            print("[Tema] Nenhuma paleta disponível para aplicar no widget.")
            return

        try:
            from PAGINAS_DO_SISTEMA.TEMAS import padronizar_botoes_container, padronizar_treeviews_container

            self._apply_palette_to_widget(widget, palette, self.fonts)
            padronizar_treeviews_container(widget)
            padronizar_botoes_container(widget)
            print(f"[Tema] Tema '{self.current_theme_name}' aplicado ao widget {widget.__class__.__name__}.")
        except Exception as e:
            print(f"[Tema] Não foi possível aplicar tema ao widget {widget}: {e}")

    def _realcar_cor(self, hex_color: str, factor: float = 1.2) -> str:
        """Clareia uma cor hex para criar hover realçado."""
        try:
            h = hex_color.lstrip("#")
            if len(h) == 3:
                h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)

            # Clareia a cor
            r = min(255, int(r * factor))
            g = min(255, int(g * factor))
            b = min(255, int(b * factor))

            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color

    def _persist_theme_choice(self, theme_name: str, palette: dict):
        """Salva a escolha do tema localmente para garantir consistência entre páginas."""
        try:
            settings = ConfigManager.load_settings()
            settings["theme"] = theme_name
            # guarda paleta simplificada para reaplicar rapidamente em novas sessões
            settings["last_palette"] = palette
            ConfigManager.save_settings(settings)
        except Exception as e:
            print(f"[Tema] Não foi possível salvar preferências locais: {e}")

    def _rebuild_interface(self):
        """Reconstrói completamente a interface para aplicar o tema."""
        try:
            app = self.app
            print("🔄 Reconstruindo interface com novo tema...")

            # Remove widgets antigos
            if hasattr(app, 'sidebar'):
                app.sidebar.destroy()
            if hasattr(app, 'main'):
                app.main.destroy()

            # Limpar cache de submenus
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

            # Reconstrói a interface
            app._build_interface()

            try:
                from PAGINAS_DO_SISTEMA.TEMAS import remover_bordas_botoes_tema
                remover_bordas_botoes_tema(app)
            except Exception as e:
                print("[Tema] Falha ao remover bordas após reconstrução:", e)

            # Atualiza display do usuário
            if hasattr(app, '_update_user_display'):
                app._update_user_display()

            # Recarrega página atual se existir
            if hasattr(app, 'current_page') and app.current_page:
                app._agendar_after(500, lambda: app.open_page(app.current_page))

        except Exception as e:
            print(f"[Tema] Erro ao reconstruir interface: {e}")

class UserManager:

    def __init__(self, app=None, usuario_id=None, usuario_nome=None, usuario_hierarquia=None):
            self.app = app
            # Usa parâmetros fornecidos OU define padrões
            self.usuario_id = usuario_id
            self.usuario_nome = usuario_nome or "Admin"
            self.usuario_hierarquia = usuario_hierarquia or "Administrador"
            self.permissoes = {}

            print(f"[UserManager] Iniciado para usuário: {self.usuario_nome} ({self.usuario_hierarquia})")

        # Se o UserManager atual não aceita parâmetros, use esta versão alternativa:
    def load_user_theme_completo(self):
        """Carrega tema completo (com paleta personalizada)."""
        import json
        default_theme = "Noite Urbana"
        if not getattr(self.app, "usuario_id", None):
            print("[UserManager][DEBUG] usuario_id não definido ao carregar tema completo; usando padrão")
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
                print(
                    f"[UserManager][DEBUG] Nenhum registro de preferências encontrado para usuario_id={self.app.usuario_id}; "
                    "usando tema padrão"
                )
                return default_theme, None

            tema_nome, usar_custom, tema_json = row
            if usar_custom and tema_json:
                try:
                    paleta = json.loads(tema_json)
                    print(f"[Tema] Paleta personalizada carregada para {self.app.usuario_nome}.")
                    return tema_nome, paleta
                except json.JSONDecodeError:
                    print(
                        f"[Tema][ERRO] JSON inválido no tema_personalizado para usuario_id={self.app.usuario_id}: {tema_json}"
                    )
            return tema_nome, None

    def save_user_theme(self, theme_name: str):
        """Salva o nome do tema (padrão) no banco."""
        if not getattr(self.app, "usuario_id", None):
            print("[UserManager][DEBUG] usuario_id ausente ao salvar tema padrão; operação ignorada")
            return

        schema = get_schema()
        try:
            print(
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
            print("[UserManager][DEBUG] Tema padrão salvo com sucesso")
        except Exception as e:
            print(f"[UserManager][ERRO] Falha ao salvar tema padrão '{theme_name}': {e}")

    def save_user_theme_personalizado(self, theme_name: str, palette_json: str):
        """Salva tema personalizado com paleta JSON."""
        if not getattr(self.app, "usuario_id", None):
            print("[UserManager][DEBUG] usuario_id ausente ao salvar tema personalizado; operação ignorada")
            return

        schema = get_schema()
        try:
            print(
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
            print("[UserManager][DEBUG] Tema personalizado salvo com sucesso")
        except Exception as e:
            print(f"[UserManager][ERRO] Falha ao salvar tema personalizado '{theme_name}': {e}")

    def _is_admin(self) -> bool:
        """Retorna True se o usuário for administrador."""
        try:
            hierarquia = getattr(self.app, "usuario_hierarquia", "")
            if hierarquia and str(hierarquia).strip().lower() in ("admin", "administrador", "superusuario"):
                return True
            return False
        except Exception as e:
            print(f"[UserManager] Erro ao verificar se é admin: {e}")
            return False

    def load_user_permissions(self):
        """Carrega todas as permissões do banco de dados para o usuário atual."""
        if not self.usuario_id:
            print("[Permissões] ⚠️ Nenhum usuário definido — permissões não carregadas.")
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

            # Cria dicionário estruturado
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

            print(f"[Permissões] {len(self.permissoes)} permissões carregadas para '{self.usuario_nome}'.")
            return self.permissoes

        except Exception as e:
            print(f"[Permissões] ❌ Erro ao carregar permissões: {e}")
            self.permissoes = {}
            return {}

    def has_permission(self, pagina: str, acao: str = "ver", categoria: str | None = None) -> bool:
        """Retorna True se o usuário possuir permissão para a ação informada."""
        # Admins têm acesso total
        if self.usuario_hierarquia and self.usuario_hierarquia.lower() in ("admin", "administrador"):
            return True

        # Busca tabela de permissões carregada no app
        permissoes = getattr(self.app, "permissoes_usuario", {})

        # Mapeia nome de página → código
        from MENU_PRINCIPAL import OperaMenuApp
        codigo = None
        if categoria:
            codigo = OperaMenuApp.PAGE_PERMISSION_MAP.get(f"{categoria}:{pagina}")
        if not codigo:
            codigo = OperaMenuApp.PAGE_PERMISSION_MAP.get(pagina)
        if not codigo:
            return True  # se a página não estiver mapeada, não bloquear

        # Permissões obrigatórias para todos os usuários
        if codigo in {"dashboard", "config_temas"}:
            return True

        perm = permissoes.get(codigo)
        if not perm:
            return False

        return bool(perm.get(acao, False))


# ===== APLICAÇÃO PRINCIPAL =====
class OperaMenuApp(ctk.CTk):
    """Aplicação principal do sistema OPERA."""

    # Configurações de layout
    SIDEBAR_WIDTH = 300
    ITEM_HEIGHT = 40
    TOPBAR_HEIGHT = 48

    # Ícones das categorias
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

    # Estrutura do menu
    # Estrutura do menu
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

    # Ícones dos submenus
    SUBMENU_ICON_MAPPING = {
        "Dashboard": {
            "Dashboard": "DASHBORD.png",
        },
        "MODELOS": {
            "Cadastrar Modelo": "ROUPA.png",
            "Imprimir Ficha Técnica": "IMPRESSORA.png",
        },
        "ORDENS DE CORTE": {
            "Nova Ordem": "NOVA_ORDEM.png",
            "Ordens de Corte Impressão": "IMPRESSORA.png",
        },
        "REGISTRO DE CORTE": {
            "Cadastrar Corte": "CADASTRO_CORTE.png",
            "Consultar Ordens": "CONSULTAR ORDENS.png",
        },
        "COMPRAS": {
            "Compras": "DINHEIRO.png",
        },
        "ESTOQUE": {
            "Entrada de Estoque": "ESTOQUE.png",
            "Saída de Estoque": "ESTOQUE.png",
            "Relatórios": "RELATORIO 2.png",
        },
        "COMERCIAL": {
            "Clientes": "USUARIOS.png",
        },
        "PRESTADORES": {
            "Cadastro de Prestadores": "FACÇAO.png",
            "Pesquisar Serviço": "CONSULTAR ORDENS.png",
        },
        "MÃO DE OBRA": {
            "Controle de Mão de Obra": "MAO DE OBRA.png",
        },
        "PLANEJAMENTO": {
            "MRP": "RELATORIO.png",
            "Planejamento de Produção": "PRODUÇAO.png",
            "Custos Reais": "RELATORIO.png",
        },
        "PRODUÇÃO": {
            "Produção": "PRODUÇAO.png",
        },
        "ACABAMENTO": {
            "Registro Acabamento": "ACABAMENTO.png",
            "Finalizar Corte / Acabamento": "ACABAMENTO.png",
            "Retrabalho de Defeitos": "ACABAMENTO.png",
        },
        "FINANCEIRO": {
            "Pagamento de Serviços": "DINHEIRO.png",
            "Recibos de Pagamentos": "IMPRESSORA.png",
            "Custo Produto": "DINHEIRO.png",
            "Folha Pagamento": "DINHEIRO.png",
            "Fechamento Mensal": "DINHEIRO.png",
            "Contas a Pagar": "DINHEIRO.png",
            "Adiantamento": "DINHEIRO.png",
            "Adiantamentos Pendentes": "DINHEIRO.png",
        },
        "RELATÓRIOS": {
            "Produção": "PRODUÇAO.png",
            "Serviços Externos": "SERVIÇOS EXTERNOS.png",
            "Modelos Produzidos": "MODELOS PRODUZIDOS.png",
            "Acabamento": "ACABAMENTO.png",
            "Logs e Atividades": "RELATORIO.png",
        },
        "CONFIGURAÇÕES": {
            "Trocar Usuário": "TROCAR_USUARIO.png",
            "Usuários": "USUARIOS.png",
            "Backup": "BACKUP.png",
            "Temas": "PALETA DE CORES.png",
            "Atualizar Sistema": "ENGRENAGEM.png",
        },
        "BANCO DE DADOS": {
            "Gerenciar": "ENGRENAGEM.png",
            "Backup": "BACKUP.png"
        },
    }

    # Mapeamento de permissões
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

        # Guardar e cancelar callbacks after de forma segura (compatível macOS/Windows)
        initialize_after_guard(self)

        # Ajustes responsivos para telas menores (ex.: 1366x768)
        self._current_ui_scale = None
        self._pending_responsive_job = None
        self._responsive_reflow_lock = False
        self._window_scale_applied = False
        self._startup_responsive_ready = False
        self._last_configure_size = None
        self._configure_responsive_layout(initial=True)

        # === INICIALIZAR CORES PADRÃO ===
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

        # Configurações de usuário
        if not usuario_id:
            self.usuario_id = 0
            self.usuario_nome = "Administrador Local"
            self.usuario_hierarquia = "Admin"
            print("⚙️ Execução direta detectada — modo Admin.")
            # NOVO: Não definir current_theme_name aqui, deixar para o _load_initial_theme
        else:
            self.usuario_id = usuario_id
            self.usuario_nome = usuario_nome
            self.usuario_hierarquia = usuario_hierarquia
            # NOVO: Não definir current_theme_name aqui, deixar para o _load_initial_theme

        # Configurações gerais
        self.settings = ConfigManager.load_settings()
        self.routes = ConfigManager.load_routes()
        ConfigManager.ensure_icons_directory()

        # Preferências recebidas do fluxo de login (fallback caso o banco não retorne nada)
        self.tema_preferido_inicial = tema_preferido or self.settings.get("theme") or "Noite Urbana"

        # Gerenciadores
        self.theme_manager = ThemeManager(self)
        self._theme_manager = self.theme_manager

        self.user_manager = UserManager()
        self.user_manager.app = self
        self.user_manager.usuario_id = self.usuario_id
        self.user_manager.usuario_nome = self.usuario_nome
        self.user_manager.usuario_hierarquia = self.usuario_hierarquia

        # Estados
        self._closing = False
        self._page_loading = False
        self.current_theme_name = None  # SERÁ DEFINIDO NO _load_initial_theme
        self.current_page = None
        self.submenu_frames = {}
        self.botoes_menu = {}
        self._submenu_close_jobs = {}
        self.icons_cache = {}
        self._active_submenu = None
        self._page_cache = {}
        self._page_cache_order = []
        self._page_cache_size = 3
        self._current_frame = None
        self._backup_launch_scheduled = False

        # Configuração da janela
        self._setup_window()

        # Carregar tema - AGORA ESTE MÉTODO DECIDE O TEMA CORRETAMENTE
        print("🎨 Iniciando carregamento do tema...")

        self._load_initial_theme()


        # Construir interface
        self._load_icons()
        self._build_interface()
        self._load_user_permissions()
        self._setup_bindings()
        self._setup_activity_logging()

        self._preload_complete = True
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass

        # Atualizar display do usuário

        # Faz todo o ajuste inicial ainda oculto para evitar "contorção" visual.
        self._apply_fast_initial_fit()

        # Carrega a página inicial ainda com a janela escondida.
        self._open_initial_page()
        try:
            self.update_idletasks()
        except Exception:
            pass
        self._fit_current_page_to_content()

        # Só depois de tudo pronto a janela aparece.
        self.deiconify()
        self.lift()

        # Habilita o watcher somente após a janela existir de fato na tela.
        self._startup_responsive_ready = True
        self._last_configure_size = (int(self.winfo_width() or 0), int(self.winfo_height() or 0))
        self._setup_responsive_watcher()
        self._agendar_after(20, self._maximize_window)

        # Inicializa tarefas secundárias depois que a UI já estabilizou.
        self._agendar_after(80, self._update_user_display)
        self._agendar_after(12000, self._ativar_backup_silencioso)

        print(f"✅ Sistema inicializado para: {self.usuario_nome} ({self.usuario_hierarquia})")
        print(f"🎨 Tema aplicado: {self.current_theme_name}")

    def _calculate_ui_scale(self, width: int, height: int) -> float:
        """Calcula escala preservando legibilidade e encaixe em telas menores."""
        base = min(width / 1920.0, height / 1080.0)
        if width <= 1320 or height <= 720:
            return max(0.68, min(0.78, round(base, 3)))
        if width <= 1366 or height <= 768:
            return max(0.72, min(0.84, round(base, 3)))
        return max(0.74, min(1.0, round(base, 3)))

    def _apply_global_scaling(self, scale: float):
        """Aplica escala global de forma estável para evitar jitter visual."""
        target = max(0.68, min(1.0, float(scale)))
        current = getattr(self, "_applied_global_scale", None)
        if current is not None and abs(current - target) < 0.01:
            return
        self._applied_global_scale = target
        try:
            ctk.set_widget_scaling(target)
            ctk.set_window_scaling(max(0.70, target))
        except Exception as e:
            print(f"⚠️ Erro ao aplicar escala de interface: {e}")

    def _configure_responsive_layout(self, *, initial: bool = False, width: int | None = None, height: int | None = None):
        """Aplica um *fit to screen* proporcional e depois reajusta a página ativa."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        current_width = int(width or self.winfo_width() or screen_width)
        current_height = int(height or self.winfo_height() or screen_height)

        if initial or current_width <= 1 or current_height <= 1:
            current_width, current_height = screen_width, screen_height

        last_size = getattr(self, "_last_responsive_size", None)
        if (
            not initial
            and last_size
            and abs(current_width - last_size[0]) < 24
            and abs(current_height - last_size[1]) < 24
        ):
            return
        self._last_responsive_size = (current_width, current_height)

        new_scale = self._calculate_ui_scale(current_width, current_height)
        same_scale = self._current_ui_scale is not None and abs(self._current_ui_scale - new_scale) < 0.015

        if same_scale and not initial:
            try:
                self._fit_current_page_to_content()
            except Exception:
                pass
            return

        self.ui_scale = new_scale
        self._current_ui_scale = new_scale

        self._base_ui_scale = self.ui_scale
        self._apply_global_scaling(self._base_ui_scale)

        self.SIDEBAR_WIDTH = max(220, int(self.__class__.SIDEBAR_WIDTH * self.ui_scale))
        self.ITEM_HEIGHT = max(30, int(self.__class__.ITEM_HEIGHT * self.ui_scale))
        self.TOPBAR_HEIGHT = max(36, int(self.__class__.TOPBAR_HEIGHT * self.ui_scale))

        self.font_sidebar_titulo = ("Arial", max(14, int(22 * self.ui_scale)), "bold")
        self.font_sidebar_subtitulo = ("Arial", max(11, int(16 * self.ui_scale)))
        self.font_topbar_titulo = ("Arial", max(14, int(26 * self.ui_scale)))
        self.font_topbar_icone = ("Arial", max(14, int(22 * self.ui_scale)))
        self.icon_size_sidebar = max(28, int(52 * self.ui_scale))

        if hasattr(self, "topbar") and self.topbar.winfo_exists():
            self.topbar.configure(height=self.TOPBAR_HEIGHT)
        if hasattr(self, "sidebar") and self.sidebar.winfo_exists():
            self.sidebar.configure(width=self.SIDEBAR_WIDTH)
        if hasattr(self, "title_label") and self.title_label.winfo_exists():
            self.title_label.configure(font=self.font_topbar_titulo)
        if hasattr(self, "icon_theme") and self.icon_theme.winfo_exists():
            self.icon_theme.configure(font=self.font_topbar_icone)

        if hasattr(self, "content") and self.content.winfo_exists():
            try:
                self.content.update_idletasks()
            except Exception:
                pass

        self._refresh_active_page_layout()

    def _refresh_active_page_layout(self):
        """Força a página ativa a recalcular o layout ao redimensionar a janela."""
        frame = getattr(self, "_current_frame", None)
        if not frame or not frame.winfo_exists():
            return
        try:
            frame.update_idletasks()
            if hasattr(frame, "on_resize"):
                frame.on_resize()
            elif hasattr(frame, "atualizar_layout_responsivo"):
                frame.atualizar_layout_responsivo()
            self._apply_page_fit_scale(frame)
        except Exception:
            pass

    def _apply_page_fit_scale(self, frame):
        """Mantido por compatibilidade: evita múltiplas reescalas durante navegação."""
        return

    def _apply_widget_dimension_scale(self, root_widget, factor: float):
        """Sem redimensionamento forçado por widget para manter layout consistente."""
        return

    def _setup_responsive_watcher(self):
        """Recalibra escala automaticamente quando a janela muda de tamanho."""
        self.bind("<Configure>", self._on_window_configure, add="+")

    def _on_window_configure(self, event):
        if event.widget is not self:
            return
        if not getattr(self, "_preload_complete", False):
            return
        if self._pending_responsive_job:
            try:
                self.after_cancel(self._pending_responsive_job)
            except Exception:
                pass

        self._pending_responsive_job = self.after(
            64,
            lambda w=event.width, h=event.height: self._configure_responsive_layout(width=w, height=h),
        )

  # ===== CONFIGURAÇÃO DA JANELA =====
    def _setup_window(self):
        """Configura a janela principal maximizada COM BARRA DE TAREFAS VISÍVEL."""
        self.title("OPERA • Sistema de Gestão")

        # Ícone
        try:
            if os.path.exists(ICONE_SISTEMA):
                icon_image = Image.open(ICONE_SISTEMA)
                self.iconphoto(True, ImageTk.PhotoImage(icon_image))
                print("✅ Ícone do sistema carregado.")
        except Exception as e:
            print(f"⚠️ Erro ao carregar ícone: {e}")

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        if IS_WIN:
            self.geometry(f"{screen_width - 16}x{screen_height - 80}+0+0")
        elif IS_MAC:
            self.geometry(f"{screen_width - 20}x{screen_height - 120}+0+25")
        else:
            self.geometry(f"{screen_width - 16}x{screen_height - 80}+0+0")

        # maximiza antes da janela aparecer para evitar “contorções” visuais
        self._maximize_window()
        self.after(10, self._maximize_window)

        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda e: self.ask_quit())

        self.minsize(min(900, screen_width), min(620, screen_height))
        self.focus_force()
        self.lift()

    def toggle_fullscreen(self, event=None):
        """Ativa ou desativa modo tela cheia real."""
        current_state = self.attributes('-fullscreen')
        self.attributes('-fullscreen', not current_state)

    def _maximize_window(self):
        """Garante a janela maximizada respeitando a barra de tarefas."""
        try:
            if IS_MAC:
                self.attributes("-zoomed", True)
            else:
                self.state("zoomed")
        except tk.TclError:
            pass

    def _apply_fast_initial_fit(self):
        """Aplica o fit inicial uma única vez, ainda com a janela oculta."""
        try:
            self.update_idletasks()
        except Exception:
            pass

        try:
            width = int(self.winfo_screenwidth())
            height = int(self.winfo_screenheight())
            self._configure_responsive_layout(initial=True, width=width, height=height)
        except Exception as exc:
            print(f"⚠️ Falha no ajuste inicial rápido: {exc}")

        try:
            self.update_idletasks()
        except Exception:
            pass

    def ask_quit(self, event=None):
        """Pergunta se o usuário deseja sair."""
        if getattr(self, "_closing", False):
            return
        try:
            confirmar = messagebox.askyesno("Sair", "Deseja realmente sair do sistema?", parent=self)
        except Exception:
            confirmar = messagebox.askyesno("Sair", "Deseja realmente sair do sistema?")

        if confirmar:
            self._agendar_after(1, self.destroy)

    def destroy(self):
        """Finaliza a aplicação cancelando timers pendentes e encerra o processo sem janela residual."""
        if getattr(self, "_closing", False):
            return

        self._closing = True
        self._fechando = True

        try:
            cancel_all_afters(self)
            cancel_all_after_info(self)
        except Exception:
            pass

        try:
            self.unbind_all("<ButtonRelease-1>")
            self.unbind_all("<<TreeviewSelect>>")
            self.unbind_all("<<ComboboxSelected>>")
            self.unbind_all("<KeyRelease>")
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

    # ===== CONFIGURAÇÃO DE TECLADO =====
    def _setup_bindings(self):
        """Configura atalhos de teclado (fechamento correto)."""

        # Recarregar página
        self.bind("<F5>", lambda e: self.reload_current_page())

        # Fullscreen
        self.bind("<F11>", lambda e: self.toggle_fullscreen())

        # ✅ FECHAR SEMPRE COM DESTROY (nunca quit)
        if IS_WIN:
            self.bind("<Escape>", lambda e: self.ask_quit())
            self.bind("<Control-q>", lambda e: self.ask_quit())
        elif IS_MAC:
            self.bind("<Escape>", lambda e: self.ask_quit())
            self.bind("<Command-q>", lambda e: self.ask_quit())
            self.bind("<Command-f>", lambda e: self.toggle_fullscreen())

        # ✅ Botão X do Windows/macOS fecha corretamente
        try:
            self.protocol("WM_DELETE_WINDOW", self.ask_quit)
        except Exception:
            pass

    def _setup_activity_logging(self):
        """Configura logging automático das atividades do usuário."""
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
        """Remove logs antigos (arquivo e banco) após 365 dias."""
        try:
            self._activity_logger.limpar_logs_antigos(dias_manter=365)
        except Exception as e:
            print(f"⚠️ Erro ao limpar logs em arquivo: {e}")

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
            print(f"⚠️ Erro ao limpar logs no banco: {e}")

    def _log_user_activity(self, acao: str, detalhe: str = "", pagina: str | None = None):
        """Registra atividade do usuário no banco e em arquivo."""
        pagina_log = pagina or self.current_page or "MenuPrincipal"
        self._activity_logger.set_usuario(self.usuario_nome, self.usuario_hierarquia)
        self._activity_logger.set_pagina(pagina_log)
        detalhe_log = detalhe or ""
        if pagina_log and "Página:" not in detalhe_log:
            detalhe_log = f"Página: {pagina_log} | {detalhe_log}".strip(" |")
        self._activity_logger.log_usuario(acao, {"detalhe": detalhe_log, "pagina": pagina_log})
        registrar_log_db(self.usuario_nome, acao, pagina_log, detalhe_log)

    def _should_log_event(self, chave: str, intervalo: float = 0.4) -> bool:
        """Evita logs duplicados em sequência rápida."""
        agora = time.monotonic()
        ultimo = self._activity_log_cache.get(chave, 0.0)
        if (agora - ultimo) < intervalo:
            return False
        self._activity_log_cache[chave] = agora
        return True

    def _on_user_click(self, event):
        """Registra cliques em botões e elementos clicáveis."""
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
        """Registra seleção em tabelas."""
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
        """Registra seleção em combos."""
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
        """Registra teclas de ação (atalhos)."""
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

    # ===== GERENCIAMENTO DE TEMAS =====
    def _load_initial_theme(self):
        """Carrega o tema inicial do usuário de forma robusta."""
        try:
            print("🔍 Buscando tema do usuário...")
            print(f"   👤 Usuário ID: {getattr(self, 'usuario_id', 'Nenhum')}")
            print(f"   👤 Nome: {getattr(self, 'usuario_nome', 'Nenhum')}")

            # CASO 1: Modo Administrador Local (sem usuário_id)
            if not hasattr(self, 'usuario_id') or not self.usuario_id:
                print("⚙️ Modo Administrador Local — aplicando CLÁSSICO CLARO")
                self.current_theme_name = "CLÁSSICO CLARO"
                self.theme_manager.apply_theme("CLÁSSICO CLARO")
                return

            # CASO 2: Tem usuário logado - carregar tema dele
            print(f"🔍 Buscando tema para usuário ID: {self.usuario_id}")

            # Verifica se user_manager está pronto
            if not hasattr(self, 'user_manager') or self.user_manager is None:
                print("⚠️ UserManager não disponível, usando tema padrão CLÁSSICO CLARO")
                self.current_theme_name = "CLÁSSICO CLARO"
                self.theme_manager.apply_theme("CLÁSSICO CLARO")
                return

            # Carrega tema completo do usuário (nome + paleta personalizada)
            tema_nome, palette = self.user_manager.load_user_theme_completo()
            print(f"📦 Tema carregado do banco: '{tema_nome}' (paleta: {palette is not None})")

            # Se não encontrou tema, usar preferências recebidas do login antes do padrão local
            if not tema_nome:
                tema_nome = self.tema_preferido_inicial
                palette = None
                print(
                    "📦 Nenhum tema encontrado no banco, usando preferência recebida do login: "
                    f"{tema_nome}"
                )

            # Define o tema atual
            self.current_theme_name = tema_nome

            print(f"🎨 Aplicando tema: {tema_nome}")

            # Aplica o tema (com paleta personalizada se existir)
            if palette:
                self.theme_manager.apply_theme(tema_nome, palette)
            else:
                self.theme_manager.apply_theme(tema_nome)

            print(f"✅ Tema '{tema_nome}' aplicado com sucesso!")

        except Exception as e:
            print(f"❌ Erro ao carregar tema inicial: {e}")
            import traceback
            traceback.print_exc()

            # Fallback garantido - CLÁSSICO CLARO
            print("🔄 Aplicando fallback para tema 'CLÁSSICO CLARO'")
            self.current_theme_name = "CLÁSSICO CLARO"
            self.theme_manager.apply_theme("CLÁSSICO CLARO")

    def _load_icons(self):
        """Carrega todos os ícones do sistema."""
        print("🔄 Carregando ícones PNG...")
        self.icons_cache = {}

        for categoria, filename in self.ICON_MAPPING.items():
            try:
                icon_path = os.path.join(ICONS_DIR, filename)
                if os.path.exists(icon_path):
                    image = Image.open(icon_path)
                    self.icons_cache[categoria] = ctk.CTkImage(
                        light_image=image, dark_image=image, size=(24, 24)
                    )
                else:
                    print(f"❌ Ícone não encontrado: {filename}")
                    self.icons_cache[categoria] = None
            except Exception as e:
                print(f"❌ Erro ao carregar ícone {filename}: {e}")
                self.icons_cache[categoria] = None

        print(f"✅ {sum(1 for x in self.icons_cache.values() if x is not None)} ícones carregados")

    def _get_submenu_icon(self, categoria: str, item: str):
        """Obtém ícone para item de submenu."""
        cache_key = f"{categoria}_{item}"
        if cache_key in self.icons_cache:
            return self.icons_cache[cache_key]

        filename = self.SUBMENU_ICON_MAPPING.get(categoria, {}).get(item, "")
        if not filename:
            self.icons_cache[cache_key] = None
            return None

        try:
            icon_path = os.path.join(ICONS_DIR, filename)
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
                icon = ctk.CTkImage(light_image=image, dark_image=image, size=(20, 20))
                self.icons_cache[cache_key] = icon
                return icon
        except Exception as e:
            print(f"❌ Erro ao carregar ícone de submenu {filename}: {e}")

        self.icons_cache[cache_key] = None
        return None

    # ===== CONSTRUÇÃO DA INTERFACE =====
    def _build_interface(self):
        """Constrói a interface do usuário."""
        self.grid_columnconfigure(0, weight=0, minsize=self.SIDEBAR_WIDTH + 16)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.configure(fg_color=self.cor_fundo)

        # Cria o menu lateral
        self._build_sidebar()

        # REMOVE BORDAS, CONTORNOS E FOCOS DOS BOTÕES DO MENU LATERAL
        remover_foco_e_bordas_menu(self.sidebar)


        # Área principal
        self._build_main_area()

        # Mostrar usuário
        self._update_user_display()

    def remover_foco_e_bordas_menu(widget):
        """
        Remove completamente:
        - borda visual aplicada pelo CustomTkinter
        - foco (highlight) que cria contorno
        - relieves invisíveis

        Aplica isso recursivamente no MENU inteiro.
        """
        import customtkinter as ctk

        try:
            # Lista de widgets que causam contorno ao receber foco
            tipos = (ctk.CTkButton, ctk.CTkOptionMenu, ctk.CTkComboBox)

            if isinstance(widget, tipos):
                try:
                    widget.configure(
                        border_width=0,
                        corner_radius=0,
                        fg_color="transparent",
                        hover_color=widget.cget("hover_color"),
                        text_color=widget.cget("text_color")
                    )

                    # Desativa o foco completamente
                    widget.bind("<FocusVisible>", lambda e: "break")
                    widget.bind("<FocusIn>", lambda e: widget.configure(border_width=0))
                    widget.bind("<FocusOut>", lambda e: widget.configure(border_width=0))

                    # Remove highlight do Tkinter raiz
                    try:
                        widget.configure(highlightthickness=0)
                    except:
                        pass

                except Exception as erro_ajuste:
                    print(f"[MENU] Erro ao remover foco/borda: {erro_ajuste}")

            # Processar recursivamente
            for child in widget.winfo_children():
                remover_foco_e_bordas_menu(child)

        except Exception as e:
            print(f"[MENU] Erro geral ao limpar bordas/foco: {e}")

    def _build_sidebar(self):
        """Constrói a barra lateral."""
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

        # ======================================================
        #  TÍTULO COM ÍCONE DO SISTEMA (NOVO)
        # ======================================================
        titulo_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        )
        titulo_frame.pack(pady=(20, 10))

        # Carregar ícone do sistema
        try:
            icon_path = os.path.join(APP_DIR, "ICONE_SISTEMA.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                img = ctk.CTkImage(
                    light_image=img,
                    dark_image=img,
                    size=(self.icon_size_sidebar, self.icon_size_sidebar),
                )

                icon_label = ctk.CTkLabel(
                    titulo_frame,
                    image=img,
                    text=""
                )
                icon_label.pack(side="left", padx=(0, 10))
        except Exception as e:
            print(f"⚠️ Erro ao carregar ícone do sistema no sidebar: {e}")

        # Texto "OPERA"
        titulo = ctk.CTkLabel(
            titulo_frame,
            text="SISTEMA OPERA",
            font=self.font_sidebar_titulo,
            text_color=self.cor_texto,
        )
        titulo.pack(side="left")

        # Subtítulo
        subtitulo = ctk.CTkLabel(
            self.sidebar,
            text="Menu Principal",
            font=self.font_sidebar_subtitulo,
            text_color=self.cor_texto,
        )
        subtitulo.pack(pady=(0, 40))

        # Frame do menu
        self.menu_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.menu_frame.pack(fill="both", expand=True, padx=10, pady=(4, 8))

        # Construir itens do menu
        self._build_menu_content()

        # ================================
        # 🔥 CHAMADA CERTA NO LUGAR CERTO
        # ================================
        remover_foco_e_bordas_menu(self.sidebar)

    def _build_main_area(self):
        """Constrói a área principal."""
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
        """Constrói a barra superior com altura ~30% maior."""
        # ALTURA ORIGINAL ≈ 36  →  AUMENTADA EM ~30% (≈ 47)
        self.topbar = ctk.CTkFrame(
            self.main,
            fg_color=self.cor_primaria,
            corner_radius=12,
            border_color=self.cor_borda,
            border_width=1,
            height=self.TOPBAR_HEIGHT
        )
        self.topbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        self.topbar.grid_propagate(False)  # Impede que widgets filhos alterem o tamanho

        # CONFIGURAÇÃO DE COLUNAS COM ESPAÇAMENTO ADEQUADO
        self.topbar.grid_columnconfigure(0, weight=1)  # Título
        self.topbar.grid_columnconfigure(1, weight=0)  # Botões de utilidade
        self.topbar.grid_columnconfigure(2, weight=0)  # Espaço entre botões e tema
        self.topbar.grid_columnconfigure(3, weight=0)  # Botão de tema
        self.topbar.grid_columnconfigure(4, weight=0)  # Informações do usuário

        # FONTE DO TÍTULO
        # Se o título estava em 18, +30% ≈ 24
        self.title_label = ctk.CTkLabel(
            self.topbar,
            text="Dashboard",
            font=self.font_topbar_titulo,
            text_color=self.cor_texto,
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=15, pady=4)

        # Botões de utilidade, switch de tema e info do usuário
        self._build_utility_buttons()  # ⬅️ também ajustada em ~30% (abaixo)
        self._add_theme_switch_to_topbar()  # ⬅️ switch maior
        self._build_user_widget()  # ⬅️ fonte do usuário maior

    def _build_utility_buttons(self):
        """Constrói os botões da topbar com hover moderno e ícones confiáveis."""

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

        # =========================
        # ÍCONE ATUALIZAR (PNG)
        # =========================
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
            lbl_refresh = ctk.CTkLabel(
                button_frame,
                text="",
                image=self.icon_refresh,
                fg_color=base_bg,
                corner_radius=0
            )
        else:
            # fallback seguro (bem mais compatível que ⟳)
            lbl_refresh = ctk.CTkLabel(
                button_frame,
                text="↻",
                font=("Segoe UI", 22, "bold"),
                text_color=self.cor_texto,
                fg_color=base_bg,
                corner_radius=0
            )

        lbl_refresh.pack(side="left", padx=16, pady=0)
        lbl_refresh.bind("<Button-1>", lambda e: self.reload_current_page())
        lbl_refresh.bind("<Enter>", lambda e, w=lbl_refresh: on_enter(w))
        lbl_refresh.bind("<Leave>", lambda e, w=lbl_refresh: on_leave(w))

        # ================================
        # ÍCONE TROCAR USUÁRIO (PNG)
        # ================================
        self.icon_switch_user = None
        try:
            icon_path = os.path.join(ICONS_DIR, "TROCAR_USUARIO.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path).convert("RGBA")
                self.icon_switch_user = ctk.CTkImage(light_image=img, dark_image=img, size=(22, 22))
        except Exception as e:
            print("Erro ao carregar TROCAR_USUARIO.png:", e)
            self.icon_switch_user = None

        lbl_user = ctk.CTkLabel(
            button_frame,
            text="",
            image=self.icon_switch_user,
            fg_color=base_bg,
            bg_color="transparent",
            corner_radius=0
        )
        lbl_user.pack(side="left", padx=10, pady=0)
        lbl_user.bind("<Button-1>", lambda e: self.trocar_usuario())
        lbl_user.bind("<Enter>", lambda e, w=lbl_user: on_enter(w))
        lbl_user.bind("<Leave>", lambda e, w=lbl_user: on_leave(w))

    def _add_theme_switch_to_topbar(self):
        """Adiciona switch de tema com ~30% a mais de tamanho."""
        import customtkinter as ctk

        # Remover switch antigo se existir
        if hasattr(self, "theme_switch_frame") and self.theme_switch_frame.winfo_exists():
            self.theme_switch_frame.destroy()

        self.theme_switch_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        self.theme_switch_frame.grid(row=0, column=3, padx=18, sticky="e")

        # Garante current_theme_name
        if not hasattr(self, 'current_theme_name') or not self.current_theme_name:
            self.current_theme_name = "CLÁSSICO CLARO"

        is_dark_mode = self.current_theme_name.upper() == "NOTURNO"

        # ÍCONE DO TEMA – fonte maior (~30%)
        self.icon_theme = ctk.CTkLabel(
            self.theme_switch_frame,
            text="🌙" if is_dark_mode else "☀️",
            font=self.font_topbar_icone,
        )
        self.icon_theme.pack(side="left", padx=(0, 10))

        # Switch – dimensões aumentadas em ~30%
        self.theme_switch = ctk.CTkSwitch(
            self.theme_switch_frame,
            text="",
            width=52,  # ⬅️ era 40
            height=26,  # ⬅️ era 20
            switch_width=52,  # ⬅️ era 40
            switch_height=26,  # ⬅️ era 20
            fg_color="#A3A3A3",
            progress_color="#3B82F6",
            button_color="#FFFFFF",
            button_hover_color="#E5E5E5",
            command=self._toggle_theme_mode
        )

        if is_dark_mode:
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()

        self.theme_switch.pack(side="left")

    def _toggle_theme_mode(self):
        """Alterna entre temas respeitando a preferência do usuário."""

        # Se está indo para o modo escuro, sempre usa NOTURNO
        if self.theme_switch.get() == 1:
            novo_tema = "NOTURNO"
            self.current_theme_name = novo_tema

            # Salvar preferência apenas se tiver usuário logado
            if hasattr(self, 'usuario_id') and self.usuario_id:
                try:
                    self.user_manager.save_user_theme(novo_tema)
                except Exception as e:
                    print("[Tema] Erro ao salvar tema:", e)

            # Aplicar novo tema
            self.theme_manager.apply_theme(novo_tema)

        # Se está indo para o modo claro, restaura o tema do usuário ou padrão
        else:
            # Se tem usuário logado, carrega o tema dele
            if hasattr(self, 'usuario_id') and self.usuario_id:
                tema_usuario, paleta_personalizada = self.user_manager.load_user_theme_completo()

                # Se o usuário não tem tema definido ou é NOTURNO, usa CLÁSSICO CLARO como fallback
                if not tema_usuario or tema_usuario.upper() == "NOTURNO":
                    tema_usuario = "CLÁSSICO CLARO"
            else:
                # Modo Administrador Local - usar CLÁSSICO CLARO como padrão
                tema_usuario = "CLÁSSICO CLARO"
                paleta_personalizada = None

            self.current_theme_name = tema_usuario

            # Aplicar o tema
            if paleta_personalizada:
                self.theme_manager.apply_theme(tema_usuario, paleta_personalizada)
            else:
                self.theme_manager.apply_theme(tema_usuario)

        # RECRIAR switch e ícone corretamente
        self._add_theme_switch_to_topbar()

        # Reaplicar ícone correto (garantia)
        if self.current_theme_name.upper() == "NOTURNO":
            self.icon_theme.configure(text="🌙")
            self.theme_switch.select()
        else:
            self.icon_theme.configure(text="☀️")
            self.theme_switch.deselect()

    def _build_user_widget(self):
        """Constrói widget de informações do usuário com fonte ~30% maior."""
        user_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        user_frame.grid(row=0, column=4, padx=18, sticky="e")

        # FONTE ORIGINAL ≈ 11 → +30% ≈ 14
        self.user_info_label = ctk.CTkLabel(
            user_frame,
            text="Carregando...",
            font=("Arial", 14),  # ⬅️ fonte aumentada em ~30%
            text_color=self.cor_texto,
        )
        self.user_info_label.pack(side="right", anchor="e")

    def _update_user_display(self):
        """Atualiza display do usuário na MESMA LINHA."""
        # Atualiza imediatamente uma vez
        self._update_user_info_once()

        # Inicia o relógio apenas se o label existir
        if hasattr(self, 'user_info_label'):
            self._agendar_after(1000, self._tick_clock)

    def _update_user_info_once(self):
        """Atualiza as informações do usuário uma vez (sem loop)."""
        if not hasattr(self, 'user_info_label'):
            return

        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Montar texto completo na mesma linha
        user_text = f"{now} | 👤 {self.usuario_nome} • {self.usuario_hierarquia}"
        if hasattr(self, 'user_manager') and self.user_manager._is_admin():
            user_text = f"{now} | 👑 {self.usuario_nome} • {self.usuario_hierarquia}"

        try:
            self.user_info_label.configure(text=user_text)
        except Exception as e:
            print(f"Erro ao atualizar informações do usuário: {e}")

    def _tick_clock(self):
        """Atualiza relógio e informações do usuário na MESMA LINHA."""
        if not hasattr(self, 'user_info_label') or not self.winfo_exists():
            return

        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Montar texto completo na mesma linha
        user_text = f"{now} | 👤 {self.usuario_nome} • {self.usuario_hierarquia}"
        if hasattr(self, 'user_manager') and self.user_manager._is_admin():
            user_text = f"{now} | 👑 {self.usuario_nome} • {self.usuario_hierarquia}"

        try:
            self.user_info_label.configure(text=user_text)
        except Exception as e:
            # Se houver erro, para o relógio
            print(f"Erro ao atualizar relógio: {e}")
            return

        # Agenda próxima atualização
        self._agendar_after(1000, self._tick_clock)

    # ===== GERENCIAMENTO DO MENU =====
    def _build_menu_content(self):
        """Constrói o conteúdo do menu lateral aplicando o tema atual."""
        # Limpar completamente
        for widget in self.menu_frame.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        # Limpar cache de submenus para forçar recriação com tema atual
        for categoria, frame in list(self.submenu_frames.items()):
            try:
                frame.destroy()
            except Exception:
                pass
        self.submenu_frames.clear()

        # MOSTRA TODOS OS BOTÕES, independente das permissões
        for categoria in self.MENU_ESTRUTURA.keys():
            self._create_menu_button(categoria)

        print(f"🎯 Menu construído com tema: {len(self.MENU_ESTRUTURA)} categorias visíveis")

    def _create_menu_button(self, categoria: str):
        """
        Cria botão de categoria no menu lateral.

        - Botão SEMPRE visível
        - Hover forte usando apenas hover_color nativo do CTkButton
        - Submenu abre ao passar o mouse
        - Sem “rastro” de cor depois do hover
        """

        # Frame "card" do botão
        btn_frame = ctk.CTkFrame(self.menu_frame, fg_color="transparent")
        btn_frame.pack_propagate(False)
        btn_frame.configure(width=self.SIDEBAR_WIDTH - 20, height=self.ITEM_HEIGHT)
        btn_frame.pack(fill="x", padx=(10, 10), pady=4)

        icon = self.icons_cache.get(categoria)

        # ==============================
        # Cores base
        # ==============================
        base = self.cor_secundaria

        card_bg = self._darker(base, 0.82)  # card fixo, sempre igual
        btn_bg = self._realcar_cor(base, 1.06)  # cor normal do botão
        btn_hover = self._realcar_cor(base, 1.55)  # hover bem mais claro

        border_color = self.cor_borda

        # Card sempre visível, não mexemos mais nessa cor no hover
        btn_frame.configure(fg_color=card_bg)

        # ===============================================
        # BTN: CORREÇÃO DO NEGRITO DO DASHBOARD 👇👇👇
        # Antes: font=("Arial", 16, "bold") if categoria == "Dashboard" else ("Arial", 16)
        # Agora: TODOS usam fonte normal (sem bold)
        # ===============================================
        font_usado = ("Arial", max(11, int(14 * self.ui_scale)))

        btn = ctk.CTkButton(
            btn_frame,
            text=f"  {categoria}",
            image=icon,
            compound="left",
            anchor="w",
            fg_color=btn_bg,
            hover_color=btn_hover,
            text_color=self.cor_texto,
            font=font_usado,  # ✔️ AQUI está o ajuste (antes tinha bold para Dashboard)
            corner_radius=10,
            border_color=border_color,
            border_width=1,
            command=lambda c=categoria: self._on_category_click(c),
        )
        btn.pack(fill="both", expand=True, padx=4)
        self._remove_button_focus(btn)

        # ==============================
        # Eventos: só layout + submenu
        # ==============================
        def on_enter(_e):
            try:
                btn_frame.pack_configure(padx=(12, 8))

                if categoria != "Dashboard":
                    self._cancel_submenu_close(categoria)
                    self._on_category_hover(categoria)
            except Exception:
                pass

        def on_leave(_e):
            try:
                btn_frame.pack_configure(padx=(10, 10))

                if categoria != "Dashboard":
                    self._schedule_submenu_close(categoria)
            except Exception:
                pass

        btn_frame.bind("<Enter>", on_enter)
        btn_frame.bind("<Leave>", on_leave)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        # Guarda referência para posicionar submenu
        self.botoes_menu[categoria] = btn_frame

    def _get_submenu_metrics(self, categoria: str, items: list[str]) -> tuple[int, tuple]:
        """Define métricas dos submenus equilibrando alinhamento e texto completo."""
        font_cfg = ("Arial", max(10, int(11 * getattr(self, "ui_scale", 1.0))))
        base_w = max(170, int(self.SIDEBAR_WIDTH - 12))
        try:
            meter = tkfont.Font(family=font_cfg[0], size=font_cfg[1])
            texto_max = max((meter.measure(it) for it in items), default=base_w - 56)
            width = max(base_w, min(int(texto_max + 58), int(self.winfo_width() * 0.33)))
        except Exception:
            width = base_w
        return width, font_cfg

    def _truncate_submenu_text(self, text: str, font_cfg: tuple, avail_px: int) -> str:
        """Evita corte bruto de texto no submenu usando elipse quando necessário."""
        try:
            meter = tkfont.Font(family=font_cfg[0], size=font_cfg[1])
            if meter.measure(text) <= avail_px:
                return text
            ell = "..."
            while text and meter.measure(text + ell) > avail_px:
                text = text[:-1]
            return (text + ell) if text else ell
        except Exception:
            return text

    def _create_submenu(self, categoria: str):
        """Cria frame de submenu para uma categoria com tema aplicado."""
        submenu_bg = self.cor_secundaria
        submenu_border = self.cor_borda
        # Hover forte para os itens do submenu
        submenu_hover = self._realcar_cor(submenu_bg, 1.55)

        itens = self.MENU_ESTRUTURA.get(categoria, [])
        visible_items = [
            item for item in itens
            if self.user_manager.has_permission(item, "ver", categoria)
        ]

        submenu_width, submenu_font = self._get_submenu_metrics(categoria, visible_items)

        frame = ctk.CTkFrame(
            self,
            fg_color=submenu_bg,
            corner_radius=12,
            border_color=submenu_border,
            border_width=1,
        )
        frame.configure(width=submenu_width)

        frame.bind("<Enter>", lambda e, c=categoria: self._cancel_submenu_close(c))
        frame.bind("<Leave>", lambda e, c=categoria: self._schedule_submenu_close(c))

        for item in visible_items:
            self._create_submenu_item(
                frame,
                categoria,
                item,
                submenu_bg,
                submenu_hover,
                submenu_width=submenu_width,
                submenu_font=submenu_font,
            )

        self.submenu_frames[categoria] = frame

    def _create_submenu_item(self, parent, categoria: str, item: str,
                             submenu_bg: str, submenu_hover: str,
                             submenu_width: int, submenu_font: tuple):
        """Cria item no submenu com hover bem evidente."""
        item_frame = ctk.CTkFrame(parent, fg_color="transparent")
        item_frame.pack_propagate(False)
        item_frame.pack(fill="x", padx=(6, 6), pady=3)
        item_frame.configure(width=max(160, submenu_width - 16),
                             height=max(28, self.ITEM_HEIGHT - 6))

        submenu_icon = self._get_submenu_icon(categoria, item)

        item_bg = submenu_bg
        item_hover = submenu_hover
        item_text_color = self.cor_texto
        item_border = self.cor_borda
        item_border_hover = self._realcar_cor(item_border, 1.4)

        text_px = max(88, submenu_width - 64)
        item_text = self._truncate_submenu_text(item, submenu_font, text_px)

        btn = ctk.CTkButton(
            item_frame,
            text=f"  {item_text}",
            image=submenu_icon,
            compound="left",
            anchor="w",
            fg_color=item_bg,
            hover_color=item_hover,
            text_color=item_text_color,
            font=submenu_font,
            corner_radius=8,
            border_color=item_border,
            border_width=1,
            command=lambda i=item: self._on_submenu_click(categoria, i),
        )
        btn._full_text = item
        btn._submenu_font = submenu_font
        btn.pack(fill="both", expand=True)
        self._remove_button_focus(btn)

        def on_enter_sub(_e, c=categoria):
            try:
                item_frame.pack_configure(padx=(10, 2))
                item_frame.configure(
                    fg_color=self._realcar_cor(item_bg, 0.9)
                )
                # Força hover no botão também
                btn.configure(fg_color=item_hover, border_color=item_border_hover)
                self._cancel_submenu_close(c)
            except Exception:
                pass

        def on_leave_sub(_e, c=categoria):
            try:
                item_frame.pack_configure(padx=(6, 6))
                item_frame.configure(fg_color="transparent")
                btn.configure(fg_color=item_bg, border_color=item_border)
                self._schedule_submenu_close(c)
            except Exception:
                pass

        item_frame.bind("<Enter>", on_enter_sub)
        item_frame.bind("<Leave>", on_leave_sub)
        btn.bind("<Enter>", on_enter_sub)
        btn.bind("<Leave>", on_leave_sub)

    # ===== GERENCIAMENTO DE SUBMENUS =====

    def _realcar_cor(self, hex_color: str, factor: float = 1.2) -> str:
        """Clareia uma cor hex para criar hover realçado."""
        try:
            h = hex_color.lstrip("#")
            if len(h) == 3:
                h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)

            # Clareia a cor
            r = min(255, int(r * factor))
            g = min(255, int(g * factor))
            b = min(255, int(b * factor))

            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color

    # ===== GERENCIAMENTO DE SUBMENUS =====
    def _on_category_click(self, categoria: str):
        """Manipula clique em categoria do menu."""
        if categoria == "Dashboard":
            self._collapse_all_submenus()
            self.open_page("Dashboard")
            return

        frame = self.submenu_frames.get(categoria)
        if frame and frame.winfo_ismapped():
            frame.place_forget()
            self._active_submenu = None
            return

        self._collapse_all_submenus()
        self._show_submenu(categoria)

    def _on_category_hover(self, categoria: str):
        """Manipula hover em categoria do menu."""
        if categoria == "Dashboard" or self._active_submenu == categoria:
            return

        self._collapse_all_submenus()
        self._show_submenu(categoria)

    def _retune_submenu_items(self, frame, submenu_width: int):
        """Mantido por compatibilidade: largura do submenu é estável e não precisa retune."""
        return
    def _show_submenu(self, categoria: str):
        """Mostra submenu alinhado ao botão principal correspondente."""
        if categoria not in self.submenu_frames:
            self._create_submenu(categoria)

        frame = self.submenu_frames[categoria]
        btn_frame = self.botoes_menu.get(categoria)

        if not btn_frame:
            return

        self.update_idletasks()
        btn_frame.update_idletasks()
        frame.update_idletasks()

        # Coordenadas relativas robustas (evita desalinhamento em janelas menores/escala)
        sidebar_x = self.sidebar.winfo_x()
        sidebar_y = self.sidebar.winfo_y()
        menu_x = self.menu_frame.winfo_x() if hasattr(self, "menu_frame") and self.menu_frame.winfo_exists() else 0
        menu_y = self.menu_frame.winfo_y() if hasattr(self, "menu_frame") and self.menu_frame.winfo_exists() else 0

        btn_rel_x = sidebar_x + menu_x + btn_frame.winfo_x()
        btn_rel_y = sidebar_y + menu_y + btn_frame.winfo_y()

        btn_w = max(1, btn_frame.winfo_width())
        btn_h = max(1, btn_frame.winfo_height())
        frame_w = frame.winfo_reqwidth()
        frame_h = frame.winfo_reqheight()

        rel_x = btn_rel_x + btn_w + 2
        if rel_x + frame_w > self.winfo_width() - 10:
            rel_x = btn_rel_x - frame_w - 2

        # Alinha verticalmente ao centro do botão principal
        rel_y = btn_rel_y + max(0, (btn_h - frame_h) // 2)

        max_x = max(10, self.winfo_width() - frame_w - 10)
        max_y = max(10, self.winfo_height() - frame_h - 10)
        rel_x = max(10, min(rel_x, max_x))
        rel_y = max(10, min(rel_y, max_y))

        frame.place(x=rel_x, y=rel_y)
        frame.lift()

        self._active_submenu = categoria

    def _on_submenu_click(self, categoria: str, item: str):
        """Manipula clique em item do submenu."""
        self._collapse_all_submenus()
        self.open_page(item, categoria)

    def _collapse_all_submenus(self):
        """Fecha todos os submenus."""
        for frame in self.submenu_frames.values():
            try:
                frame.place_forget()
            except Exception:
                pass
        self._active_submenu = None

    def _schedule_submenu_close(self, categoria: str):
        """Agenda fechamento do submenu."""
        job = self._submenu_close_jobs.get(categoria)
        if job:
            safe_after_cancel(self, job)

        def close():
            if self._active_submenu == categoria:
                frame = self.submenu_frames.get(categoria)
                if frame and frame.winfo_ismapped():
                    try:
                        mouse_x = self.winfo_pointerx()
                        mouse_y = self.winfo_pointery()

                        btn_frame = self.botoes_menu.get(categoria)
                        if btn_frame:
                            btn_x = btn_frame.winfo_rootx()
                            btn_y = btn_frame.winfo_rooty()
                            btn_width = btn_frame.winfo_width()
                            btn_height = btn_frame.winfo_height()

                            frame_x = frame.winfo_rootx()
                            frame_y = frame.winfo_rooty()
                            frame_width = frame.winfo_width()
                            frame_height = frame.winfo_height()

                            if not (btn_x <= mouse_x <= btn_x + btn_width and
                                    btn_y <= mouse_y <= btn_y + btn_height) and \
                                    not (frame_x <= mouse_x <= frame_x + frame_width and
                                         frame_y <= mouse_y <= frame_y + frame_height):
                                frame.place_forget()
                                self._active_submenu = None
                    except Exception:
                        frame.place_forget()
                        self._active_submenu = None

        self._submenu_close_jobs[categoria] = self._agendar_after(300, close)

    def _cancel_submenu_close(self, categoria: str):
        """Cancela o fechamento agendado do submenu."""
        job = self._submenu_close_jobs.get(categoria)
        if job:
            safe_after_cancel(self, job)
            self._submenu_close_jobs[categoria] = None

    def _load_user_permissions(self):
        """Carrega todas as permissões do usuário logado e aplica no sistema."""
        try:
            from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import fetch_all

            if not getattr(self, "usuario_id", None):
                print("⚠️ Nenhum usuário logado — não foi possível carregar permissões.")
                self.permissoes_usuario = {}
                return

            print(f"[PERMISSÕES] 🔄 Carregando permissões para usuário ID: {self.usuario_id}")

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

            # Sincronizar com o UserManager
            self.user_manager.permissoes = self.permissoes_usuario
            self.user_manager.usuario_id = self.usuario_id
            self.user_manager.usuario_nome = self.usuario_nome
            self.user_manager.usuario_hierarquia = self.usuario_hierarquia

            print(f"🔑 Permissões carregadas para {self.usuario_nome}: {len(permissoes)} registros.")

            # Aplicar imediatamente as restrições no menu
            self._apply_permissions_to_menu()

        except Exception as e:
            print(f"❌ Erro ao carregar permissões: {e}")
            self.permissoes_usuario = {}
            self._build_menu_content()

    def _apply_permissions_to_menu(self):
        """Aplica as permissões carregadas ao menu lateral e submenus."""
        if not hasattr(self, "permissoes_usuario") or not self.permissoes_usuario:
            print("⚠️ Nenhuma permissão carregada — exibindo menu básico obrigatório.")
            self.MENU_ESTRUTURA = {
                "Dashboard": ["Dashboard"],
                "CONFIGURAÇÕES": ["Temas"],
            }
            self._build_menu_content()
            return

        # Se o usuário for admin, não restringe nada
        if str(self.usuario_hierarquia).lower() in ("admin", "administrador"):
            print("👑 Usuário administrador — menu completo liberado.")
            return

        # Recriar MENU_ESTRUTURA filtrado
        estrutura_filtrada = {}
        total_itens_visiveis = 0

        for categoria, itens in self.MENU_ESTRUTURA.items():
            itens_visiveis = []
            for item in itens:
                codigo = self.PAGE_PERMISSION_MAP.get(f"{categoria}:{item}") or self.PAGE_PERMISSION_MAP.get(item)
                if not codigo:
                    continue

                perm = self.permissoes_usuario.get(codigo)
                if perm and perm.get("ver", False):
                    itens_visiveis.append(item)

            if itens_visiveis:
                estrutura_filtrada[categoria] = itens_visiveis
                total_itens_visiveis += len(itens_visiveis)

        # Garantir páginas obrigatórias para todos os usuários
        estrutura_filtrada.setdefault("Dashboard", [])
        if "Dashboard" not in estrutura_filtrada["Dashboard"]:
            estrutura_filtrada["Dashboard"].insert(0, "Dashboard")

        estrutura_filtrada.setdefault("CONFIGURAÇÕES", [])
        if "Temas" not in estrutura_filtrada["CONFIGURAÇÕES"]:
            estrutura_filtrada["CONFIGURAÇÕES"].append("Temas")

        # Aplicar a nova estrutura filtrada
        if total_itens_visiveis == 0:
            print("🚫 Usuário sem nenhuma permissão de visualização — mostrando menu básico obrigatório.")
            self.MENU_ESTRUTURA = {
                "Dashboard": ["Dashboard"],
                "CONFIGURAÇÕES": ["Temas"],
            }
        else:
            self.MENU_ESTRUTURA = estrutura_filtrada

        # Reconstruir menu lateral
        self._build_menu_content()

        print(f"🔒 Permissões aplicadas — {total_itens_visiveis} itens visíveis no menu.")

    # ===== GERENCIAMENTO DE PÁGINAS =====
    def _open_initial_page(self):
        """Abre a página inicial imediatamente, sem atraso visível."""
        self._open_dashboard_automatico()


    # ==============================================================
    # BACKUP AUTOMÁTICO — EXECUTA SEM MOSTRAR A PÁGINA DE BACKUP
    # ==============================================================
    def _ativar_backup_silencioso(self):
        """
        Ativa o backup automático depois que a UI já estabilizou.
        NÃO cria interface (BackupPage), apenas manipula BACKUP_AUTO global.
        Compatível com Windows e macOS.

        IMPORTANTE:
        Usa o mesmo módulo da rota (opera_page_BACKUP) para evitar estado duplicado
        entre imports diferentes do arquivo BACKUP.py.
        """

        if getattr(self, "_backup_launch_scheduled", False):
            self._backup_launch_scheduled = False

        # Se a janela ainda não estiver visível/estável, adia novamente sem bloquear a UI.
        try:
            if not self.winfo_exists() or self.state() == "withdrawn":
                self._backup_launch_scheduled = True
                self._agendar_after(5000, self._ativar_backup_silencioso)
                return
        except Exception:
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
            print(f"⚠️ [MENU] Não foi possível carregar módulo de backup automático: {e}")
            return

        # Já está rodando? então não reinicia.
        if BACKUP_AUTO.get("running"):
            print("🟢 [MENU] Backup automático já ativo — não será reiniciado.")
            return

        print("🔄 [MENU] Inicializando backup automático silencioso...")

        # Definir pasta base do sistema
        base_dir = getattr(self, "diretorio_base",
                           os.path.dirname(os.path.abspath(__file__)))
        pasta_backups = BackupPage.criar_pasta_backups_externo(base_dir)

        # CONFIGURAR ESTADO GLOBAL
        BACKUP_AUTO["running"] = True
        BACKUP_AUTO["interval"] = 3600  # 1h padrão
        BACKUP_AUTO["pasta"] = pasta_backups
        BACKUP_AUTO["proximo"] = None

        # Iniciar thread global
        def loop():
            import time

            print("🟢 [MENU] Thread de backup automático iniciada.")

            # Rodar imediatamente ao iniciar
            BackupPage._executar_backup_auto_silencioso_static()

            while BACKUP_AUTO.get("running", False):
                intervalo = BACKUP_AUTO.get("interval", 3600)
                time.sleep(intervalo)
                if BACKUP_AUTO.get("running", False):
                    BackupPage._executar_backup_auto_silencioso_static()

            print("⏹ [MENU] Loop de backup automático finalizado.")

        # DISPARAR THREAD
        t = threading.Thread(target=loop, daemon=True)
        BACKUP_AUTO["thread"] = t
        t.start()



    def _open_dashboard_automatico(self):
        """Abre o Dashboard automaticamente."""
        if (hasattr(self, '_preload_complete') and self._preload_complete):
            if self.user_manager.has_permission("Dashboard", "ver"):
                print("🚀 Abrindo Dashboard automaticamente...")
                self.open_page("Dashboard")
            else:
                for pagina in self.routes.keys():
                    if self.user_manager.has_permission(pagina, "ver"):
                        print(f"🚀 Abrindo '{pagina}' automaticamente...")
                        self.open_page(pagina)
                        break
        else:
            self._agendar_after(500, self._open_dashboard_automatico)

    def _get_cached_page(self, page_name: str):
        frame = self._page_cache.get(page_name)
        if not frame:
            return None
        if not frame.winfo_exists() or frame.master != self.content:
            try:
                frame.destroy()
            except Exception:
                pass
            self._page_cache.pop(page_name, None)
            if page_name in self._page_cache_order:
                self._page_cache_order.remove(page_name)
            return None
        if page_name in self._page_cache_order:
            self._page_cache_order.remove(page_name)
        self._page_cache_order.append(page_name)
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
                except Exception:
                    pass

    def open_page(self, page_name: str, categoria: str | None = None):
        """Abre uma página no conteúdo principal com verificação de permissão."""
        # Não abre se estiver carregando outra página ou fechando o app
        if getattr(self, "_page_loading", False) or getattr(self, "_closing", False):
            return

        # Ação especial: trocar usuário (mapeada no JSON via action)
        route_action = (self.routes.get(page_name) or {}).get("action")
        if page_name == "Trocar Usuário" or route_action == "trocar_usuario":
            self.trocar_usuario()
            return

        # ===================== VERIFICAÇÃO DE PERMISSÃO =====================
        if not self.user_manager.has_permission(page_name, "ver", categoria):
            messages = {
                # PRINCIPAL
                "Dashboard": "acessar o dashboard",

                # MODELOS
                "Cadastrar Modelo": "cadastrar novos modelos no sistema",
                "Imprimir Ficha Técnica": "imprimir fichas técnicas",

                # ORDENS DE CORTE
                "Nova Ordem": "criar novas ordens de corte",

                # REGISTRO DE CORTE
                "Cadastrar Corte": "cadastrar ordens de corte",
                "Consultar Ordens": "consultar ordens de corte",

                # ESTOQUE
                "Entrada de Estoque": "registrar entradas de estoque",
                "Saída de Estoque": "registrar saídas de estoque",
                "Relatórios": "acessar relatórios de estoque",

                # PRESTADORES
                "Cadastro de Prestadores": "cadastrar prestadores",
                "Pesquisar Serviço": "pesquisar serviços",

                # MÃO DE OBRA
                "Controle de Mão de Obra": "controlar mão de obra",
                # DEFEITOS
                "Retrabalho de Defeitos": "tratar defeitos",

                # PRODUÇÃO
                "Produção": "acessar o módulo de produção",

                # ACABAMENTO
                "Registro Acabamento": "registrar acabamentos",
                "Finalizar Corte / Acabamento": "finalizar cortes e acabamentos",

                # FINANCEIRO
                "Pagamento de Serviços": "efetuar pagamentos de serviços",
                "Recibos de Pagamentos": "visualizar recibos de pagamentos",
                "Custo Produto": "calcular custos de produtos",
                "Folha Pagamento": "acessar folha de pagamento",
                "Fechamento Mensal": "realizar fechamentos mensais",
                "Contas a Pagar": "gerenciar contas a pagar",
                "Adiantamento": "efetuar adiantamentos",
                "Adiantamentos Pendentes": "consultar adiantamentos pendentes",

                # RELATÓRIOS
                "Produção": "acessar relatórios de produção",
                "Serviços Externos": "acessar relatórios de serviços externos",
                "Modelos Produzidos": "acessar relatórios de modelos produzidos",
                "Acabamento": "acessar relatórios de acabamento",

                # CONFIGURAÇÕES / SISTEMA
                "Usuários": "gerenciar usuários do sistema",
                "Temas": "personalizar temas do sistema",
                "Atualizar Sistema": "gerenciar atualizações do sistema",
                "Backup": "realizar backup do sistema",
                "Gerenciar": "gerenciar banco de dados",
            }

            area_descricao = messages.get(page_name, "acessar esta área do sistema")
            usuario_nome = getattr(self, "usuario_nome", "Usuário")
            hierarquia = getattr(self, "usuario_hierarquia", "desconhecido")

            mensagem = f"""Olá {usuario_nome}! 

    Você não tem permissão para {area_descricao}.

    📋 Seu perfil atual: {hierarquia}

    Se você precisa acessar esta funcionalidade, entre em contato com o administrador do sistema."""
            self._show_temporary_message(mensagem)
            return
        # ====================================================================

        self._page_loading = True

        try:
            if self._current_frame and self._current_frame.winfo_exists():
                try:
                    self._current_frame.pack_forget()
                except Exception:
                    pass

            frame = self._get_cached_page(page_name)
            if frame is None:
                # Carregar página diretamente via rotas (route_map.json)
                frame = self._load_page_direct(page_name)
                self._cache_page(page_name, frame)

            if frame:
                # Exibir no container principal
                try:
                    frame._opera_last_fit = None
                except Exception:
                    pass
                frame.pack(fill="both", expand=True, padx=10, pady=10)
                self._agendar_after(45, self._refresh_active_page_layout)

                # CORREÇÃO ESPECÍFICA PARA PÁGINA DE TEMAS
                if page_name == "Temas":
                    try:
                        # Importa a correção da página de temas
                        from PAGINAS_DO_SISTEMA.TEMAS import corrigir_labels_pagina_temas

                        # Aplica correção em três momentos para garantir:
                        # 1. Imediatamente (antes da renderização completa)
                        corrigir_labels_pagina_temas(frame)

                        # 2. Após 200ms (durante a renderização)
                        self._agendar_after(200, lambda f=frame: corrigir_labels_pagina_temas(f))

                        # 3. Após 500ms (após renderização completa)
                        self._agendar_after(500, lambda f=frame: corrigir_labels_pagina_temas(f))

                        print("🔧 Correções visuais aplicadas na página de Temas")

                    except ImportError as e:
                        print(f"⚠️ Não foi possível importar correção de Temas: {e}")
                    except Exception as e:
                        print(f"⚠️ Erro ao aplicar correção na página Temas: {e}")

                # Atualizar título da topbar
                if hasattr(self, "title_label"):
                    self.title_label.configure(text=page_name)

                # ================== INTEGRAÇÃO COM O SISTEMA/TEMA ==================
                try:
                    # Referência do app dentro da página
                    if hasattr(frame, "host"):
                        frame.host = self
                    if hasattr(frame, "sistema"):
                        frame.sistema = self
                    if hasattr(frame, "app"):
                        frame.app = self

                    # Garante que a página recém-carregada receba o tema atual
                    if hasattr(self, "theme_manager"):
                        self.theme_manager.apply_theme_to_widget(frame)

                    # Se a página tiver método para atualizar o tema, chama
                    if hasattr(frame, "atualizar_tema"):
                        frame.atualizar_tema()
                    elif hasattr(frame, "aplicar_tema"):
                        frame.aplicar_tema()
                    elif hasattr(frame, "refresh"):
                        frame.refresh()

                    if page_name == "Logs e Atividades" and hasattr(frame, "abrir_aba_logs"):
                        frame.abrir_aba_logs()
                except Exception as e:
                    print(f"⚠️ Erro ao aplicar tema na página '{page_name}': {e}")
                # ==================================================================

                # Atualizar controle de página atual
                self.current_page = page_name
                self._current_frame = frame

                try:
                    self._fit_current_page_to_content()
                    self._agendar_after(120, self._fit_current_page_to_content)
                except Exception:
                    pass

                # Guardar última página nas configurações
                try:
                    self.settings["last_page"] = page_name
                    ConfigManager.save_settings(self.settings)
                except Exception as e:
                    print(f"⚠️ Erro ao salvar last_page nas configurações: {e}")

                # Registrar acesso à página nos logs
                try:
                    self._log_page_access(page_name)
                except Exception as e:
                    print(f"⚠️ Erro ao registrar log de acesso à página '{page_name}': {e}")

                print(f"✅ Página '{page_name}' carregada com sucesso")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao abrir {page_name}:\n{e}", parent=self)
            print(f"❌ Erro ao abrir página '{page_name}': {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._page_loading = False

    def _fit_current_page_to_content(self):
        """Reaplica o encaixe da página atual dentro da área útil da dashboard."""
        frame = getattr(self, "_current_frame", None)
        if not frame or not frame.winfo_exists():
            return
        if not hasattr(self, "content") or not self.content.winfo_exists():
            return

        self.update_idletasks()
        content_w = int(self.content.winfo_width() or max(100, self.main.winfo_width() - 24))
        content_h = int(self.content.winfo_height() or max(100, self.main.winfo_height() - self.TOPBAR_HEIGHT - 24))
        page_pad = max(2, int(8 * float(getattr(self, "ui_scale", 1.0) or 1.0)))

        try:
            frame.pack_configure(fill="both", expand=True, padx=page_pad, pady=page_pad)
        except Exception:
            pass

        if hasattr(frame, "on_host_resize"):
            try:
                frame.on_host_resize(content_w, content_h, float(getattr(self, "ui_scale", 1.0) or 1.0))
            except Exception as exc:
                print(f"⚠️ Ajuste responsivo falhou em '{getattr(self, 'current_page', '')}': {exc}")

    def _log_page_access(self, page_name: str):
        """Registra acesso à página no sistema de logs"""
        if not hasattr(self, 'usuario_nome'):
            return

        try:
            detalhe = f"Usuário: {self.usuario_nome} | Página: {page_name}"
            self._log_user_activity("Navegação", detalhe, pagina=page_name)
        except Exception:
            pass

    def _show_temporary_message(self, message, duration=3000):
        """Exibe uma mensagem temporária na área de conteúdo"""
        try:
            # Limpa o conteúdo atual
            for widget in self.content.winfo_children():
                widget.destroy()

            # Cria frame para a mensagem
            message_frame = ctk.CTkFrame(
                self.content,
                fg_color=self.cor_secundaria,
                corner_radius=12,
                border_color=self.cor_borda,
                border_width=2
            )
            message_frame.pack(fill="both", expand=True, padx=50, pady=50)

            # Ícone de alerta
            icon_label = ctk.CTkLabel(
                message_frame,
                text="⚠️",
                font=("Arial", 48),
                text_color=self.cor_alerta
            )
            icon_label.pack(pady=(30, 10))

            # Mensagem principal
            message_label = ctk.CTkLabel(
                message_frame,
                text=message,
                font=("Arial", 16, "bold"),
                text_color=self.cor_texto,
                wraplength=400,
                justify="center"
            )
            message_label.pack(pady=10, padx=30)

            # Mensagem secundária
            sub_label = ctk.CTkLabel(
                message_frame,
                text="Esta mensagem desaparecerá automaticamente",
                font=("Arial", 12),
                text_color=self.cor_texto_secundario
            )
            sub_label.pack(pady=(0, 30))

            # Atualiza o título
            self.title_label.configure(text="Acesso Restrito")

            # Agenda o retorno ao Dashboard
            self._agendar_after(duration, self._return_to_dashboard)

        except Exception as e:
            print(f"Erro ao exibir mensagem temporária: {e}")

    def _return_to_dashboard(self):
        """Retorna ao Dashboard após a mensagem temporária"""
        if self.user_manager.has_permission("Dashboard", "ver"):
            self.open_page("Dashboard")
        else:
            # Se não tem permissão para Dashboard, procura primeira página permitida
            for pagina in self.routes.keys():
                if self.user_manager.has_permission(pagina, "ver"):
                    self.open_page(pagina)
                    return

            # Se não encontrou nenhuma página permitida, mostra aviso permanente
            self._show_no_permissions_message()

    def _show_no_permissions_message(self):
        """Mostra mensagem quando usuário não tem acesso a nenhuma página"""
        for widget in self.content.winfo_children():
            widget.destroy()

        message_frame = ctk.CTkFrame(
            self.content,
            fg_color=self.cor_secundaria,
            corner_radius=12,
            border_color=self.cor_borda
        )
        message_frame.pack(fill="both", expand=True, padx=50, pady=50)

        ctk.CTkLabel(
            message_frame,
            text="🚫",
            font=("Arial", 64),
            text_color=self.cor_alerta
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            message_frame,
            text="Acesso Restrito",
            font=("Arial", 24, "bold"),
            text_color=self.cor_texto
        ).pack(pady=10)

        ctk.CTkLabel(
            message_frame,
            text="Você não tem permissão para acessar nenhuma área do sistema.\n\nEntre em contato com o administrador para solicitar acesso.",
            font=("Arial", 14),
            text_color=self.cor_texto,
            wraplength=400,
            justify="center"
        ).pack(pady=10)

        self.title_label.configure(text="Acesso Restrito")

    def _load_page_direct(self, page_name: str, reload_module: bool = False):
        """Carrega página diretamente sem cache"""
        route = self.routes.get(page_name)
        if not route:
            raise ValueError(f"Rota não encontrada: {page_name}")

        file_path = os.path.join(APP_DIR, route["file"])
        if not os.path.exists(file_path):
            file_path = os.path.join(ROOT_DIR, route["file"])
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        # Importa módulo
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

        # Encontra classe da página
        class_name = route.get("class")
        page_class = None

        if class_name:
            page_class = getattr(module, class_name, None)

        if not page_class:
            # Busca primeira subclasse de CTkFrame
            for _, obj in inspect.getmembers(module, inspect.isclass):
                try:
                    if (issubclass(obj, ctk.CTkFrame) and
                            obj.__module__ == module.__name__):
                        page_class = obj
                        break
                except Exception:
                    continue

        if not page_class:
            raise RuntimeError(f"Classe não encontrada em {file_path}")

        # Instancia página SEMPRE nova
        try:
            # Tenta diferentes parâmetros de inicialização
            try:
                return page_class(master=self.content, sistema=self)
            except TypeError:
                try:
                    return page_class(master=self.content, app=self)
                except TypeError:
                    try:
                        return page_class(master=self.content, parent=self)
                    except TypeError:
                        try:
                            return page_class(master=self.content, host=self)
                        except TypeError:
                            try:
                                return page_class(master=self.content)
                            except TypeError:
                                try:
                                    return page_class(self.content)
                                except:
                                    # Fallback: frame vazio
                                    fallback_frame = ctk.CTkFrame(self.content)
                                    fallback_frame.configure(fg_color=self.cor_fundo)
                                    return fallback_frame
        except Exception as e:
            print(f"❌ Erro ao instanciar página {page_name}: {e}")
            # Fallback garantido
            fallback_frame = ctk.CTkFrame(self.content)
            fallback_frame.configure(fg_color=self.cor_fundo)
            return fallback_frame

    def reload_current_page(self):
        """Recarrega a página atual."""
        if hasattr(self, 'current_page') and self.current_page:
            print(f"🔄 Recarregando página: {self.current_page}")
            self.open_page(self.current_page)

    # ===== MENSAGENS TEMPORÁRIAS =====


    # ===== TROCA DE USUÁRIO =====
    # ===== TROCA DE USUÁRIO =====
    def trocar_usuario(self):
        """Abre a janela de troca de usuário via módulo desacoplado (lazy import)."""
        try:
            modulo = importlib.import_module("PAGINAS_DO_SISTEMA.TROCAR_USUARIOS")
            modulo.abrir_janela_trocar_usuario(self)
        except Exception as e:
            print(f"❌ Erro ao abrir janela de trocar usuário: {e}")
            messagebox.showerror(
                "Erro",
                f"Falha ao abrir tela de login:\n{e}",
                parent=self,
            )

    def _remove_button_focus(self, button):
        """Remove foco visual dos botões."""
        try:
            button.configure(border_spacing=0)
        except Exception:
            pass

    def _darker(self, hex_color: str, factor: float = 0.85) -> str:
        """Escurece uma cor hex."""
        try:
            h = hex_color.lstrip("#")
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            r = max(0, min(255, int(r * factor)))
            g = max(0, min(255, int(g * factor)))
            b = max(0, min(255, int(b * factor)))
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color


def remover_foco_e_bordas_menu(widget_root):
    """
    Remove contornos, focos, highlight e bordas internas dos botões do menu lateral.
    Funciona para CTkButton e widgets padrão do Tkinter.
    """

    import customtkinter as ctk
    import tkinter as tk

    def limpar(widget):
        try:
            # ============ BOTÕES CTK ============
            if isinstance(widget, ctk.CTkButton):
                widget.configure(
                    border_width=0,
                    fg_color=widget.cget("fg_color"),
                    hover_color=widget.cget("hover_color"),
                    corner_radius=8
                )

            # ============ TKINTER BUTTON ============
            elif isinstance(widget, tk.Button):
                widget.configure(
                    highlightthickness=0,
                    bd=0,
                    borderwidth=0,
                    relief="flat",
                    highlightbackground=widget.cget("bg"),
                    activebackground=widget.cget("bg")
                )

        except Exception:
            pass

        # percorre filhos
        for child in widget.winfo_children():
            limpar(child)

    limpar(widget_root)


# ===== EXECUÇÃO PRINCIPAL =====
def main():
    """Função principal."""
    try:
        print("🚀 Iniciando sistema OPERA...")
        app = OperaMenuApp(
            usuario_id=None,
            usuario_nome="Admin",
            usuario_hierarquia="Administrador"
        )
        print("✅ Aplicação Tkinter iniciada, entrando no mainloop...")
        app.mainloop()
        print("🔚 Mainloop finalizado - aplicação encerrada normalmente")
    except Exception as e:
        print(f"💥 ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("Erro Fatal", f"Erro ao iniciar o sistema:\n{e}")


if __name__ == "__main__":
    main()
    # fechado aqui

#03/02/2025
