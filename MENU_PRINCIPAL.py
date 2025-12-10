# -*- coding: utf-8 -*-
"""
MENU_PRINCIPAL.py - Sistema OPERA Refatorado
Menu principal com sistema de temas, permissões e cache otimizado.
"""

import json
import platform
import importlib
import inspect
import os
import sys
import threading
import time
from datetime import datetime
from tkinter import messagebox
from PIL import Image, ImageTk
from tkinter import messagebox, ttk
from PIL import Image
import customtkinter as ctk
from TEMAS import (
    TemasPage,
    aplicar_estilo_treeview,
    get_contraste_texto,
    is_dark_color,
    padronizar_treeview,
    remover_bordas_botoes_tema,
)



# ===== IMPORTAÇÕES DO SISTEMA =====
try:
    from USUARIOS import registrar_log_db

    LOGS_DISPONIVEIS = True
    print("✅ Função de logs disponível.")
except ImportError as e:
    LOGS_DISPONIVEIS = False
    print(f"⚠️ Logs não disponíveis: {e}")


    def registrar_log_db(usuario, acao, pagina, detalhe=""):
        """Função fallback para logs."""
        pass

try:
    from BANCO_DE_DADOS_PG import get_conn, get_schema

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
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROUTES_PATH = os.path.join(APP_DIR, "route_map.json")
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
ICONS_DIR = os.path.join(APP_DIR, "icons")
ICONE_SISTEMA = os.path.join(APP_DIR, "ICONE_SISTEMA.png")


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
        try:
            with open(ROUTES_PATH, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
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
        from TEMAS import TemasPage, is_dark_color

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

        # Hovers realçados
        cor_hover_realcado = self._realcar_cor(cor_secundaria, 1.3)

        estilo_btn_ttk = None
        try:
            estilo_btn_ttk = ttk.Style(root_widget)
            aplicar_estilo_treeview(
                style=estilo_btn_ttk,
                prefixo="Treeview",
                cor_fundo=cor_fundo,
                cor_linhas=cor_secundaria,
                cor_cabecalho=cor_primaria,
                cor_texto=get_contraste_texto(cor_secundaria) or cor_texto,
                cor_borda=cor_borda,
                cor_selecao=palette.get("selecao", cor_destaque),
                altura_linha=28,
            )
            estilo_btn_ttk.map(
                "Opera.TButton",
                background=[("active", cor_hover_realcado), ("pressed", cor_hover)],
                relief=[("pressed", tk.FLAT), ("active", tk.FLAT)],
                bordercolor=[("pressed", ""), ("active", "")],
            )
            estilo_btn_ttk.map(
                "TButton",
                background=[("active", cor_hover_realcado), ("pressed", cor_hover)],
                relief=[("pressed", tk.FLAT), ("active", tk.FLAT)],
                bordercolor=[("pressed", ""), ("active", "")],
            )
        except Exception as e:
            print(f"[Tema] Erro ao aplicar tema em Treeview/Botões: {e}")

        def _apply_to_all_widgets(widget):
            """Aplica tema recursivamente em todos os widgets."""
            try:
                # ---------- WIDGETS CUSTOMTKINTER ----------
                if isinstance(widget, ctk.CTkFrame):
                    # frames usam a cor de fundo do tema
                    if hasattr(widget, "_fg_color") and widget._fg_color not in ["transparent", None]:
                        widget.configure(fg_color=cor_fundo)
                    widget.configure(border_color=cor_borda)

                elif isinstance(widget, ctk.CTkButton):
                    widget.configure(
                        fg_color=cor_secundaria,
                        hover_color=cor_hover_realcado,
                        border_color=cor_borda,
                        border_width=0,
                        text_color=cor_texto,
                        font=fonts["button"],
                        corner_radius=8,
                    )

                elif isinstance(widget, ctk.CTkLabel):
                    # >>> AQUI ESTÁ A CORREÇÃO IMPORTANTE <<<
                    # Toda label fica com fundo TRANSPARENTE para não criar qudrado em volta do texto.
                    widget.configure(
                        text_color=cor_texto,
                        font=fonts["body"],
                        fg_color="transparent",
                    )

                elif isinstance(widget, ctk.CTkEntry):
                    widget.configure(
                        fg_color=cor_secundaria,
                        border_color=cor_borda,
                        text_color=cor_texto,
                        font=fonts["body"],
                        placeholder_text_color=(
                            cor_texto if len(str(cor_texto)) <= 7 else str(cor_texto)[:7]
                        ),
                    )

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

                elif isinstance(widget, (ctk.CTkCheckBox, ctk.CTkSwitch)):
                    widget.configure(
                        fg_color=cor_secundaria,
                        border_color=cor_borda,
                        button_color=cor_primaria,
                        button_hover_color=cor_hover_realcado,
                        text_color=cor_texto,
                        font=fonts["body"],
                    )

                elif isinstance(widget, ctk.CTkTabview):
                    widget.configure(
                        segmented_button_fg_color=cor_primaria,
                        segmented_button_selected_color=cor_hover_realcado,
                        segmented_button_unselected_color=cor_secundaria,
                        segmented_button_unselected_hover_color=cor_hover_realcado,
                        text_color=cor_texto,
                        font=fonts["body"],
                    )

                elif isinstance(widget, ctk.CTkScrollableFrame):
                    widget.configure(fg_color=cor_fundo, border_color=cor_borda)

                elif isinstance(widget, ttk.Treeview):
                    padronizar_treeview(widget)

                elif isinstance(widget, ttk.Button):
                    if estilo_btn_ttk:
                        widget.configure(style="Opera.TButton")
                        try:
                            widget.state(["!focus"])
                        except Exception:
                            pass

                # ---------- TKINTER PURO ----------
                elif isinstance(widget, tk.Frame):
                    widget.configure(bg=cor_fundo)

                elif isinstance(widget, tk.Label):
                    widget.configure(bg=cor_fundo, fg=cor_texto, font=fonts["body"])

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

            except Exception:
                # Ignora erros em widgets que não podem ser configurados
                pass

            # Recursão nos filhos
            try:
                for child in widget.winfo_children():
                    _apply_to_all_widgets(child)
            except Exception:
                pass

        _apply_to_all_widgets(root_widget)

    def _apply_global_theme(self, palette: dict):
        try:
            self._apply_palette_to_widget(self.app, palette, self.fonts)

            # CORREÇÃO CRÍTICA — EVITA CAIXAS QUADRADAS
            from TEMAS import remover_bordas_botoes_tema
            remover_bordas_botoes_tema(self.app)

        except Exception as e:
            print(f"[Tema] Erro ao aplicar tema global: {e}")

    def apply_theme_to_widget(self, widget):
        """Aplica o tema atual a um widget específico (ex.: páginas recém-carregadas)."""
        if widget is None:
            return

        from TEMAS import TemasPage

        palette = self.current_palette or {}
        if not palette:
            palette = TemasPage.PADROES.get(self.current_theme_name or "Noite Urbana", {})

        if not palette:
            print("[Tema] Nenhuma paleta disponível para aplicar no widget.")
            return

        try:
            self._apply_palette_to_widget(widget, palette, self.fonts)
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

            # Reconstrói a interface
            app._build_interface()

            try:
                from TEMAS import remover_bordas_botoes_tema
                remover_bordas_botoes_tema(app)
            except Exception as e:
                print("[Tema] Falha ao remover bordas após reconstrução:", e)

            # Atualiza display do usuário
            if hasattr(app, '_update_user_display'):
                app._update_user_display()

            # Recarrega página atual se existir
            if hasattr(app, 'current_page') and app.current_page:
                app.after(500, lambda: app.open_page(app.current_page))

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
                    print(f"[Tema] Paleta personalizada carregada para {self.app.usuario_nome}.")
                    return tema_nome, paleta
                except json.JSONDecodeError:
                    print("[Tema] JSON inválido no tema_personalizado.")
            return tema_nome, None

    def save_user_theme(self, theme_name: str):
        """Salva o nome do tema (padrão) no banco."""
        if not getattr(self.app, "usuario_id", None):
            return

        schema = get_schema()
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

    def save_user_theme_personalizado(self, theme_name: str, palette_json: str):
        """Salva tema personalizado com paleta JSON."""
        if not getattr(self.app, "usuario_id", None):
            return

        schema = get_schema()
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

        perm = permissoes.get(codigo)
        if not perm:
            return False

        return bool(perm.get(acao, False))


# ===== APLICAÇÃO PRINCIPAL =====
class OperaMenuApp(ctk.CTk):
    """Aplicação principal do sistema OPERA."""

    # Configurações de layout
    SIDEBAR_WIDTH = 270
    ITEM_HEIGHT = 44

    # Ícones das categorias
    ICON_MAPPING = {
        "Dashboard": "DASHBORD.png",
        "MODELOS": "ROUPA.png",
        "ORDENS DE CORTE": "TESOURA.png",
        "REGISTRO DE CORTE": "FOLHA DE PAPEL.png",
        "ESTOQUE": "ESTOQUE.png",
        "FACÇÕES": "FABRICA.png",
        "MÃO DE OBRA": "PESSOAS.png",
        "PRODUÇÃO": "PRODUÇAO.png",
        "ACABAMENTO": "FERRAMENTAS.png",
        "FINANCEIRO": "DINHEIRO.png",
        "RELATÓRIOS": "RELATORIO.png",
        "CONFIGURAÇÕES": "ENGRENAGEM.png",
        "BANCO DE DADOS": "BANCO DE DADOS.png",
    }

    # Estrutura do menu
    # Estrutura do menu
    MENU_ESTRUTURA = {
        "Dashboard": ["Dashboard"],
        "MODELOS": ["Cadastrar Modelo", "Imprimir Ficha Técnica"],
        "FACÇÕES": ["Cadastro de Facções", "Pesquisar Serviço"],
        "ESTOQUE": ["Entrada de Estoque", "Saída de Estoque", "Relatórios"],
        "ORDENS DE CORTE": ["Nova Ordem", "Ordens de Corte Impressão"],
        "REGISTRO DE CORTE": ["Cadastrar Corte", "Consultar Ordens"],
        "MÃO DE OBRA": ["Controle de Mão de Obra"],
        "ACABAMENTO": ["Registro Acabamento", "Finalizar Corte / Acabamento"],
        "FINANCEIRO": [
            "Pagamento de Serviços", "Custo Produto", "Folha Pagamento",
            "Fechamento Mensal", "Contas a Pagar", "Adiantamento", "Adiantamentos Pendentes"
        ],
        "RELATÓRIOS": ["Produção", "Serviços Externos", "Modelos Produzidos", "Acabamento"],
        "CONFIGURAÇÕES": ["Trocar Usuário", "Usuários", "Temas"],
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
            "Nova Ordem": "ORDEM_CORTE.png",
            "Ordens de Corte Impressão": "IMPRESSORA.png",
        },
        "REGISTRO DE CORTE": {
            "Cadastrar Corte": "CADASTRO_CORTE.png",
            "Consultar Ordens": "CONSULTAR ORDENS.png",
        },
        "ESTOQUE": {
            "Entrada de Estoque": "ESTOQUE.png",
            "Saída de Estoque": "ESTOQUE.png",
            "Relatórios": "RELATORIO 2.png",
        },
        "FACÇÕES": {
            "Cadastro de Facções": "FACÇAO.png",
            "Pesquisar Serviço": "CONSULTAR ORDENS.png",
        },
        "MÃO DE OBRA": {
            "Controle de Mão de Obra": "MAO DE OBRA.png",
        },
        "PRODUÇÃO": {
            "Produção": "PRODUÇAO.png",
        },
        "ACABAMENTO": {
            "Registro Acabamento": "ACABAMENTO.png",
            "Finalizar Corte / Acabamento": "ACABAMENTO.png",
        },
        "FINANCEIRO": {
            "Pagamento de Serviços": "DINHEIRO.png",
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
        },
        "CONFIGURAÇÕES": {
            "Trocar Usuário": "TROCAR_USUARIO.png",
            "Usuários": "USUARIOS.png",
            "Backup": "BACKUP.png",
            "Temas": "PALETA DE CORES.png",
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
        "Cadastro de Facções": "cadastro_faccoes",
        "Pesquisar Serviço": "pesquisar_servico",
        "Controle de Mão de Obra": "controle_mao_obra",
        "Produção": "Producao",
        "Registro Acabamento": "registro_acabamento",
        "Finalizar Corte / Acabamento": "finalizar_corte",
        "Pagamento de Serviços": "pagamento_servicos",
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
        "Trocar Usuário": "trocar_usuario",
        "Usuários": "config_usuarios",
        "Backup": "config_backup",
        "Temas": "config_temas",
        "Gerenciar": "banco_dados",

    }

    def __init__(self, usuario_id=None, usuario_nome="Admin", usuario_hierarquia="Administrador", tema_preferido=None):
        super().__init__()
        print("🚀 Iniciando sistema OPERA...")

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

        self._preload_complete = True
        self.deiconify()
        self._build_topbar()
        self._add_theme_switch_to_topbar()


        # Atualizar display do usuário


        self._open_initial_page()
        self._ativar_backup_silencioso()
        self.after(100, self._update_user_display)

        print(f"✅ Sistema inicializado para: {self.usuario_nome} ({self.usuario_hierarquia})")
        print(f"🎨 Tema aplicado: {self.current_theme_name}")

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
            self.geometry(f"{screen_width}x{screen_height - 40}+0+0")
        elif IS_MAC:
            self.geometry(f"{screen_width}x{screen_height - 105}+0+25")
        else:
            self.geometry(f"{screen_width}x{screen_height - 40}+0+0")

        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda e: self.ask_quit())

        self.minsize(1024, 768)
        self.focus_force()
        self.lift()

    def toggle_fullscreen(self, event=None):
        """Ativa ou desativa modo tela cheia real."""
        current_state = self.attributes('-fullscreen')
        self.attributes('-fullscreen', not current_state)

    def ask_quit(self, event=None):
        """Pergunta se o usuário deseja sair."""
        if messagebox.askyesno("Sair", "Deseja realmente sair do sistema?"):
            self.destroy()

    # ===== CONFIGURAÇÃO DE TECLADO =====
    def _setup_bindings(self):
        """Configura atalhos de teclado."""
        self.bind("<F5>", lambda e: self.reload_current_page())

        # Atalhos para fullscreen
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        if IS_WIN:
            self.bind("<Escape>",
                      lambda e: self.quit() if messagebox.askyesno("Sair", "Deseja sair do sistema?") else None)
        elif IS_MAC:
            self.bind("<Command-q>",
                      lambda e: self.quit() if messagebox.askyesno("Sair", "Deseja sair do sistema?") else None)
            self.bind("<Command-f>", lambda e: self.toggle_fullscreen())

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
        titulo_frame.pack(pady=(10, 4))

        # Carregar ícone do sistema
        try:
            icon_path = os.path.join(APP_DIR, "ICONE_SISTEMA.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                img = ctk.CTkImage(light_image=img, dark_image=img, size=(28, 28))

                icon_label = ctk.CTkLabel(
                    titulo_frame,
                    image=img,
                    text=""
                )
                icon_label.pack(side="left", padx=(0, 8))
        except Exception as e:
            print(f"⚠️ Erro ao carregar ícone do sistema no sidebar: {e}")

        # Texto "OPERA"
        titulo = ctk.CTkLabel(
            titulo_frame,
            text="SISTEMA OPERA",
            font=("Arial", 24, "bold"),
            text_color=self.cor_texto,
        )
        titulo.pack(side="left")

        # Subtítulo
        subtitulo = ctk.CTkLabel(
            self.sidebar,
            text="Menu Principal",
            font=("Arial", 18),
            text_color=self.cor_texto,
        )
        subtitulo.pack(pady=(0, 12))

        # Frame do menu
        self.menu_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.menu_frame.pack(fill="both", expand=True, padx=4, pady=(4, 8))

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

        self.content = ctk.CTkScrollableFrame(
            self.main,
            fg_color=self.cor_fundo,
            corner_radius=10,
            border_color=self.cor_borda,
            border_width=1,
        )
        self.content.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def _build_topbar(self):
        """Constrói a barra superior MAIS FINA."""
        self.topbar = ctk.CTkFrame(
            self.main,
            fg_color=self.cor_primaria,
            corner_radius=12,
            border_color=self.cor_borda,
            border_width=1,
            height=36  # ALTURA REDUZIDA (era cerca de 50-60px)
        )
        self.topbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        self.topbar.grid_propagate(False)  # Impede que widgets filhos alterem o tamanho

        # CONFIGURAÇÃO DE COLUNAS COM ESPAÇAMENTO ADEQUADO
        self.topbar.grid_columnconfigure(0, weight=1)  # Título
        self.topbar.grid_columnconfigure(1, weight=0)  # Botões de utilidade
        self.topbar.grid_columnconfigure(2, weight=0)  # ESPAÇO ENTRE BOTÕES E TEMA
        self.topbar.grid_columnconfigure(3, weight=0)  # Botão de tema
        self.topbar.grid_columnconfigure(4, weight=0)  # Informações do usuário

        self.title_label = ctk.CTkLabel(
            self.topbar,
            text="Dashboard",
            font=("Arial", 16, "bold"),  # Fonte ligeiramente menor
            text_color=self.cor_texto,
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=15, pady=2)  # Padding horizontal aumentado

        self._build_utility_buttons()
        self._add_theme_switch_to_topbar()  # ADICIONAR BOTÃO DE TEMA AQUI
        self._build_user_widget()

    def _build_utility_buttons(self):
        """Constrói botões de utilidade na topbar com tamanho reduzido."""
        button_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="e", padx=10)  # Padding aumentado

        buttons = [
            ("⟳", self.reload_current_page),
            ("🔄", self.trocar_usuario),
        ]

        for text, command in buttons:
            btn = ctk.CTkButton(
                button_frame,
                text=text,
                width=28,  # Largura reduzida
                height=28,  # Altura reduzida
                corner_radius=8,
                fg_color=self.cor_secundaria,
                hover_color=self.cor_hover,
                text_color=self.cor_texto,
                font=("Arial", 14, "bold"),  # Fonte menor
                command=command,
            )
            btn.pack(side="left", padx=4)  # Padding horizontal entre botões
            self._remove_button_focus(btn)

    def _add_theme_switch_to_topbar(self):
        """Adiciona um switch elegante com ícone de sol/lua e espaçamento correto na topbar."""
        import customtkinter as ctk

        # Remover switch antigo se existir
        if hasattr(self, "theme_switch_frame") and self.theme_switch_frame.winfo_exists():
            self.theme_switch_frame.destroy()

        # Criar frame alinhado à direita COM MAIS ESPAÇAMENTO
        self.theme_switch_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        self.theme_switch_frame.grid(row=0, column=3, padx=15, sticky="e")  # MAIS ESPAÇAMENTO

        # Determinar se está no modo escuro baseado no tema atual
        # Garantir que current_theme_name existe e tem valor válido
        if not hasattr(self, 'current_theme_name') or not self.current_theme_name:
            self.current_theme_name = "CLÁSSICO CLARO"

        is_dark_mode = self.current_theme_name.upper() == "CLÁSSICO ESCURO"

        # ÍCONE DO TEMA (com espaçamento perfeito)
        self.icon_theme = ctk.CTkLabel(
            self.theme_switch_frame,
            text="🌙" if is_dark_mode else "☀️",
            font=("Arial", 16),
        )
        self.icon_theme.pack(side="left", padx=(0, 10))  # espaço de 10px antes do switch

        # Switch elegante e pequeno
        self.theme_switch = ctk.CTkSwitch(
            self.theme_switch_frame,
            text="",
            width=40,
            height=20,
            switch_width=40,
            switch_height=20,
            fg_color="#A3A3A3",
            progress_color="#3B82F6",
            button_color="#FFFFFF",
            button_hover_color="#E5E5E5",
            command=self._toggle_theme_mode
        )

        # Estado inicial baseado no tema atual
        if is_dark_mode:
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()

        self.theme_switch.pack(side="left")

    def _toggle_theme_mode(self):
        """Alterna entre temas respeitando a preferência do usuário."""

        # Se está indo para o modo escuro, sempre usa CLÁSSICO ESCURO
        if self.theme_switch.get() == 1:
            novo_tema = "CLÁSSICO ESCURO"
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

                # Se o usuário não tem tema definido ou é CLÁSSICO ESCURO, usa CLÁSSICO CLARO como fallback
                if not tema_usuario or tema_usuario.upper() == "CLÁSSICO ESCURO":
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
        if self.current_theme_name.upper() == "CLÁSSICO ESCURO":
            self.icon_theme.configure(text="🌙")
            self.theme_switch.select()
        else:
            self.icon_theme.configure(text="☀️")
            self.theme_switch.deselect()

    def _build_user_widget(self):
        """Constrói widget de informações do usuário na MESMA LINHA."""
        user_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        user_frame.grid(row=0, column=4, padx=15, sticky="e")  # MAIS ESPAÇAMENTO

        # Criar UM ÚNICO label com todas as informações na mesma linha
        self.user_info_label = ctk.CTkLabel(
            user_frame,
            text="Carregando...",  # Texto temporário
            font=("Arial", 11),
            text_color=self.cor_texto,
        )
        self.user_info_label.pack(side="right", anchor="e")

    def _update_user_display(self):
        """Atualiza display do usuário na MESMA LINHA."""
        # Atualiza imediatamente uma vez
        self._update_user_info_once()

        # Inicia o relógio apenas se o label existir
        if hasattr(self, 'user_info_label'):
            self.after(1000, self._tick_clock)

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
        self.after(1000, self._tick_clock)

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

        btn = ctk.CTkButton(
            btn_frame,
            text=f"  {categoria}",
            image=icon,
            compound="left",
            anchor="w",
            fg_color=btn_bg,
            hover_color=btn_hover,  # CustomTkinter cuida de ligar/desligar
            text_color=self.cor_texto,
            font=("Arial", 16, "bold") if categoria == "Dashboard" else ("Arial", 16),
            corner_radius=10,
            border_color=border_color,
            border_width=1,
            # hover permanece ativado (padrão), não vamos desligar
            command=lambda c=categoria: self._on_category_click(c),
        )
        btn.pack(fill="both", expand=True, padx=4)
        self._remove_button_focus(btn)

        # ==============================
        # Eventos: só layout + submenu
        # ==============================
        def on_enter(_e):
            try:
                # apenas um leve deslocamento para dar sensação de foco
                btn_frame.pack_configure(padx=(12, 8))

                if categoria != "Dashboard":
                    self._cancel_submenu_close(categoria)
                    self._on_category_hover(categoria)
            except Exception:
                pass

        def on_leave(_e):
            try:
                # volta o padding original
                btn_frame.pack_configure(padx=(10, 10))

                if categoria != "Dashboard":
                    self._schedule_submenu_close(categoria)
            except Exception:
                pass

        # Aplica eventos tanto no card quanto no botão, mas SEM mexer em cor
        btn_frame.bind("<Enter>", on_enter)
        btn_frame.bind("<Leave>", on_leave)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        # Guarda referência para posicionar submenu
        self.botoes_menu[categoria] = btn_frame

    def _create_submenu(self, categoria: str):
        """Cria frame de submenu para uma categoria com tema aplicado."""
        submenu_bg = self.cor_secundaria
        submenu_border = self.cor_borda
        # Hover forte para os itens do submenu
        submenu_hover = self._realcar_cor(submenu_bg, 1.55)

        frame = ctk.CTkFrame(
            self,
            fg_color=submenu_bg,
            corner_radius=12,
            border_color=submenu_border,
            border_width=1,
        )
        frame.configure(width=self.SIDEBAR_WIDTH - 20)

        frame.bind("<Enter>", lambda e, c=categoria: self._cancel_submenu_close(c))
        frame.bind("<Leave>", lambda e, c=categoria: self._schedule_submenu_close(c))

        itens = self.MENU_ESTRUTURA.get(categoria, [])
        visible_items = [
            item for item in itens
            if self.user_manager.has_permission(item, "ver", categoria)
        ]

        for item in visible_items:
            self._create_submenu_item(frame, categoria, item, submenu_bg, submenu_hover)

        self.submenu_frames[categoria] = frame

    def _create_submenu_item(self, parent, categoria: str, item: str,
                             submenu_bg: str, submenu_hover: str):
        """Cria item no submenu com hover bem evidente."""
        item_frame = ctk.CTkFrame(parent, fg_color="transparent")
        item_frame.pack_propagate(False)
        item_frame.pack(fill="x", padx=(6, 6), pady=3)
        item_frame.configure(width=self.SIDEBAR_WIDTH - 40,
                             height=self.ITEM_HEIGHT - 6)

        submenu_icon = self._get_submenu_icon(categoria, item)

        item_bg = submenu_bg
        item_hover = submenu_hover
        item_text_color = self.cor_texto
        item_border = self.cor_borda
        item_border_hover = self._realcar_cor(item_border, 1.4)

        btn = ctk.CTkButton(
            item_frame,
            text=f"  {item}",
            image=submenu_icon,
            compound="left",
            anchor="w",
            fg_color=item_bg,
            hover_color=item_hover,
            text_color=item_text_color,
            font=("Arial", 15),
            corner_radius=8,
            border_color=item_border,
            border_width=1,
            command=lambda i=item: self._on_submenu_click(categoria, i),
        )
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

    def _show_submenu(self, categoria: str):
        """Mostra submenu para uma categoria."""
        if categoria not in self.submenu_frames:
            self._create_submenu(categoria)

        frame = self.submenu_frames[categoria]
        btn_frame = self.botoes_menu.get(categoria)

        if not btn_frame:
            return

        btn_x = btn_frame.winfo_rootx()
        btn_y = btn_frame.winfo_rooty()

        self_x = self.winfo_rootx()
        self_y = self.winfo_rooty()

        rel_x = btn_x - self_x + btn_frame.winfo_width() + 5
        rel_y = btn_y - self_y

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
            self.after_cancel(job)

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

        self._submenu_close_jobs[categoria] = self.after(300, close)

    def _cancel_submenu_close(self, categoria: str):
        """Cancela o fechamento agendado do submenu."""
        job = self._submenu_close_jobs.get(categoria)
        if job:
            self.after_cancel(job)
            self._submenu_close_jobs[categoria] = None

    def _load_user_permissions(self):
        """Carrega todas as permissões do usuário logado e aplica no sistema."""
        try:
            from BANCO_DE_DADOS_PG import fetch_all

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
            print("⚠️ Nenhuma permissão carregada — exibindo apenas Dashboard.")
            self.MENU_ESTRUTURA = {"Dashboard": ["Dashboard"]}
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

        # Aplicar a nova estrutura filtrada
        if total_itens_visiveis == 0:
            print("🚫 Usuário sem nenhuma permissão de visualização — mostrando aviso.")
            self.MENU_ESTRUTURA = {"Dashboard": ["Dashboard"]}
        else:
            self.MENU_ESTRUTURA = estrutura_filtrada

        # Reconstruir menu lateral
        self._build_menu_content()

        print(f"🔒 Permissões aplicadas — {total_itens_visiveis} itens visíveis no menu.")

    # ===== GERENCIAMENTO DE PÁGINAS =====
    def _open_initial_page(self):
        """Abre página inicial após carregamento."""
        self.after(100, self._open_dashboard_automatico)


    # ==============================================================
    # BACKUP AUTOMÁTICO — EXECUTA SEM MOSTRAR A PÁGINA DE BACKUP
    # ==============================================================
    def _ativar_backup_silencioso(self):
        """
        Ativa o backup automático assim que o MENU é carregado.
        NÃO cria interface (BackupPage), apenas manipula BACKUP_AUTO global.
        Compatível com Windows e macOS.
        """

        try:
            from BACKUP import BACKUP_AUTO
        except Exception as e:
            print(f"⚠️ [MENU] Não foi possível importar BACKUP_AUTO: {e}")
            return

        # Já está rodando? então não reinicia.
        if BACKUP_AUTO.get("running"):
            print("🟢 [MENU] Backup automático já ativo — não será reiniciado.")
            return

        print("🔄 [MENU] Inicializando backup automático silencioso...")

        # Definir pasta base do sistema
        base_dir = getattr(self, "diretorio_base",
                           os.path.dirname(os.path.abspath(__file__)))
        from BACKUP import BackupPage
        pasta_backups = BackupPage.criar_pasta_backups_externo(base_dir)

        # CONFIGURAR ESTADO GLOBAL
        BACKUP_AUTO["running"] = True
        BACKUP_AUTO["interval"] = 3600  # 1h padrão
        BACKUP_AUTO["pasta"] = pasta_backups
        BACKUP_AUTO["proximo"] = None

        # Iniciar thread global
        def loop():
            import time
            from BACKUP import BACKUP_AUTO
            from BACKUP import BackupPage  # usar função estática abaixo

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
            self.after(500, self._open_dashboard_automatico)

    def open_page(self, page_name: str, categoria: str | None = None):
        """Abre uma página no conteúdo principal com verificação de permissão."""
        # Não abre se estiver carregando outra página ou fechando o app
        if getattr(self, "_page_loading", False) or getattr(self, "_closing", False):
            return

        # Ação especial: trocar usuário
        if page_name == "Trocar Usuário":
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

                # FACÇÕES
                "Cadastro de Facções": "cadastrar facções",
                "Pesquisar Serviço": "pesquisar serviços",

                # MÃO DE OBRA
                "Controle de Mão de Obra": "controlar mão de obra",

                # PRODUÇÃO
                "Produção": "acessar o módulo de produção",

                # ACABAMENTO
                "Registro Acabamento": "registrar acabamentos",
                "Finalizar Corte / Acabamento": "finalizar cortes e acabamentos",

                # FINANCEIRO
                "Pagamento de Serviços": "efetuar pagamentos de serviços",
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
            # Limpar completamente o conteúdo anterior
            for widget in self.content.winfo_children():
                try:
                    widget.destroy()
                except Exception:
                    pass

            # Carregar página diretamente via rotas (route_map.json)
            frame = self._load_page_direct(page_name)

            if frame:
                # Exibir no container principal
                frame.pack(fill="both", expand=True, padx=10, pady=10)

                # CORREÇÃO ESPECÍFICA PARA PÁGINA DE TEMAS
                if page_name == "Temas":
                    try:
                        # Importa a correção da página de temas
                        from TEMAS import corrigir_labels_pagina_temas

                        # Aplica correção em três momentos para garantir:
                        # 1. Imediatamente (antes da renderização completa)
                        corrigir_labels_pagina_temas(frame)

                        # 2. Após 200ms (durante a renderização)
                        self.after(200, lambda f=frame: corrigir_labels_pagina_temas(f))

                        # 3. Após 500ms (após renderização completa)
                        self.after(500, lambda f=frame: corrigir_labels_pagina_temas(f))

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
                except Exception as e:
                    print(f"⚠️ Erro ao aplicar tema na página '{page_name}': {e}")
                # ==================================================================

                # Atualizar controle de página atual
                self.current_page = page_name

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

    def _log_page_access(self, page_name: str):
        """Registra acesso à página no sistema de logs"""
        if not hasattr(self, 'usuario_nome') or page_name in ["Dashboard", "Trocar Usuário"]:
            return

        try:
            registrar_log_db(
                self.usuario_nome,
                "Navegação",
                f"Acessou: {page_name}",
                f"Usuário: {self.usuario_nome} | Página: {page_name}"
            )
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
            self.after(duration, self._return_to_dashboard)

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

    def _load_page_direct(self, page_name: str):
        """Carrega página diretamente sem cache"""
        route = self.routes.get(page_name)
        if not route:
            raise ValueError(f"Rota não encontrada: {page_name}")

        file_path = os.path.join(APP_DIR, route["file"])
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        # Importa módulo
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        if APP_DIR not in sys.path:
            sys.path.insert(0, APP_DIR)

        try:
            # SEMPRE recarregar o módulo
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)
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
        """Abre tela completa de login para trocar usuário."""
        import tkinter as tk
        from tkinter import ttk

        try:
            # =========================
            # JANELA MODAL DE LOGIN
            # =========================
            login_window = ctk.CTkToplevel(self)
            login_window.title("OPERA - Trocar Usuário")
            login_window.transient(self)

            # Dimensões fixas
            largura_janela = 480
            altura_janela = 680

            # Garantir que a janela exista antes de centralizar
            login_window.update_idletasks()

            screen_largura = login_window.winfo_screenwidth()
            screen_altura = login_window.winfo_screenheight()

            x = (screen_largura - largura_janela) // 2
            y = (screen_altura - altura_janela) // 2

            login_window.geometry(f"{largura_janela}x{altura_janela}+{x}+{y}")
            login_window.resizable(False, False)

            # =========================
            # MOVIMENTAÇÃO DA JANELA
            # =========================
            def start_move(event):
                login_window.x = event.x_root
                login_window.y = event.y_root

            def stop_move(event):
                login_window.x = None
                login_window.y = None

            def do_move(event):
                if hasattr(login_window, "x") and login_window.x is not None:
                    deltax = event.x_root - login_window.x
                    deltay = event.y_root - login_window.y
                    nx = login_window.winfo_x() + deltax
                    ny = login_window.winfo_y() + deltay
                    login_window.geometry(f"+{nx}+{ny}")
                    login_window.x = event.x_root
                    login_window.y = event.y_root

            # =========================
            # FECHAMENTO SEGURO
            # =========================
            def on_login_close():
                try:
                    login_window.grab_release()
                except Exception:
                    pass
                login_window.destroy()

            login_window.protocol("WM_DELETE_WINDOW", on_login_close)

            # =========================
            # CORES DO TEMA ATUAL (DO MENU)
            # =========================
            cor_fundo = getattr(self, "cor_fundo", "#f8f9fa")
            cor_primaria = getattr(self, "cor_primaria", "#ffffff")
            cor_secundaria = getattr(self, "cor_secundaria", "#e9ecef")
            cor_terciaria = getattr(self, "cor_terciaria", "#6c757d")
            cor_texto = getattr(self, "cor_texto", "#212529")
            cor_borda = getattr(self, "cor_borda", "#ced4da")
            cor_botao_primario = getattr(self, "cor_destaque", "#007bff")
            cor_botao_secundario = cor_terciaria
            cor_texto_placeholder = getattr(self, "cor_texto_secundario", "#888888")
            cor_alerta = getattr(self, "cor_alerta", "#ff0000")

            # =========================
            # HELPER DE HOVER (INVERTER CORES)
            # =========================
            def aplicar_hover_inverter(botao, cor_bg_normal, cor_bg_hover, cor_txt_normal, cor_txt_hover):
                """Configura o botão para inverter cores de fundo/texto no hover."""

                def on_enter(_event):
                    botao.configure(fg_color=cor_bg_hover, text_color=cor_txt_hover)

                def on_leave(_event):
                    botao.configure(fg_color=cor_bg_normal, text_color=cor_txt_normal)

                botao.configure(hover_color=cor_bg_normal)
                botao.bind("<Enter>", on_enter)
                botao.bind("<Leave>", on_leave)

            # =========================
            # LAYOUT PRINCIPAL
            # =========================
            login_window.configure(fg_color=cor_fundo)

            container = ctk.CTkFrame(
                login_window,
                fg_color=cor_primaria,
                corner_radius=16,
                border_color=cor_borda,
                border_width=2,
            )
            container.pack(fill="both", expand=True, padx=25, pady=25)

            # ----- TÍTULO (arrastável)
            titulo_frame = ctk.CTkFrame(container, fg_color="transparent")
            titulo_frame.pack(fill="x", padx=25, pady=(25, 15))

            titulo = ctk.CTkLabel(
                titulo_frame,
                text="🔐 TROCAR USUÁRIO",
                font=("Arial", 22, "bold"),
                text_color=cor_texto,
            )
            titulo.pack(pady=10)

            titulo.bind("<ButtonPress-1>", start_move)
            titulo.bind("<ButtonRelease-1>", stop_move)
            titulo.bind("<B1-Motion>", do_move)

            ctk.CTkFrame(
                titulo_frame,
                fg_color=cor_borda,
                height=2,
            ).pack(fill="x", pady=5)

            # ----- FORMULÁRIO
            form_frame = ctk.CTkFrame(container, fg_color="transparent")
            form_frame.pack(fill="both", expand=True, padx=30, pady=20)

            # Campo Usuário
            lbl_usuario = ctk.CTkLabel(
                form_frame,
                text="Usuário:",
                font=("Arial", 14, "bold"),
                text_color=cor_texto,
            )
            lbl_usuario.pack(anchor="w", pady=(10, 5))

            entry_usuario = ctk.CTkEntry(
                form_frame,
                placeholder_text="Digite seu nome de usuário",
                width=300,
                height=45,
                font=("Arial", 14),
                fg_color=cor_secundaria,
                text_color=cor_texto,
                border_width=0,
                placeholder_text_color=cor_texto_placeholder,
                corner_radius=10,
            )
            entry_usuario.pack(fill="x", pady=(0, 20))

            # Campo Senha
            lbl_senha = ctk.CTkLabel(
                form_frame,
                text="Senha:",
                font=("Arial", 14, "bold"),
                text_color=cor_texto,
            )
            lbl_senha.pack(anchor="w", pady=(10, 5))

            entry_senha = ctk.CTkEntry(
                form_frame,
                placeholder_text="Digite sua senha",
                show="•",
                width=300,
                height=45,
                font=("Arial", 14),
                fg_color=cor_secundaria,
                text_color=cor_texto,
                border_width=0,
                placeholder_text_color=cor_texto_placeholder,
                corner_radius=10,
            )
            entry_senha.pack(fill="x", pady=(0, 15))

            # ----- Mostrar senha
            var_mostrar_senha = ctk.BooleanVar()

            def toggle_senha():
                entry_senha.configure(show="" if var_mostrar_senha.get() else "•")

            chk_mostrar = ctk.CTkCheckBox(
                form_frame,
                text="Mostrar senha",
                variable=var_mostrar_senha,
                command=toggle_senha,
                font=("Arial", 13),
                text_color=cor_texto,
                fg_color=cor_botao_primario,
                hover_color=cor_botao_primario,
                border_width=0,
            )
            chk_mostrar.pack(anchor="w", pady=(0, 25))

            # =========================
            # BOTÕES DE AJUDA
            # =========================
            help_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
            help_frame.pack(fill="x", pady=(0, 25))

            def listar_usuarios():
                """Mostra lista de usuários cadastrados e permite seleção."""
                try:
                    from BANCO_DE_DADOS_PG import fetch_all

                    usuarios = fetch_all(
                        "SELECT usuario, hierarquia "
                        "FROM opera.usuarios "
                        "WHERE ativo = true "
                        "ORDER BY usuario"
                    )

                    if not usuarios:
                        messagebox.showinfo(
                            "Usuários",
                            "Nenhum usuário encontrado.",
                            parent=login_window,
                        )
                        return

                    # Janela de listagem
                    user_win = ctk.CTkToplevel(login_window)
                    user_win.title("Usuários Cadastrados")
                    user_win.transient(login_window)

                    # Tamanho
                    user_largura = 520
                    user_altura = 420

                    # Centralizar em relação à janela de login
                    login_window.update_idletasks()
                    parent_x = login_window.winfo_rootx()
                    parent_y = login_window.winfo_rooty()
                    parent_w = login_window.winfo_width()
                    parent_h = login_window.winfo_height()

                    ux = parent_x + (parent_w - user_largura) // 2
                    uy = parent_y + (parent_h - user_altura) // 2

                    user_win.geometry(f"{user_largura}x{user_altura}+{ux}+{uy}")
                    user_win.resizable(False, False)

                    user_win.configure(fg_color=cor_fundo)
                    user_win.grab_set()
                    user_win.focus_force()

                    user_container = ctk.CTkFrame(
                        user_win, fg_color=cor_primaria, corner_radius=12
                    )
                    user_container.pack(fill="both", expand=True, padx=15, pady=15)

                    ctk.CTkLabel(
                        user_container,
                        text="👥 Usuários Cadastrados",
                        font=("Arial", 16, "bold"),
                        text_color=cor_texto,
                    ).pack(pady=(10, 5))

                    # Frame da lista
                    lista_frame = ctk.CTkFrame(
                        user_container, fg_color=cor_secundaria, corner_radius=8
                    )
                    lista_frame.pack(fill="both", expand=True, padx=10, pady=10)

                    # Listbox para permitir duplo clique
                    listbox = tk.Listbox(
                        lista_frame,
                        font=("Arial", 12),
                        activestyle="none",
                        borderwidth=0,
                        highlightthickness=0,
                    )
                    listbox.pack(fill="both", expand=True, padx=8, pady=8)

                    for user in usuarios:
                        texto = f"• {user['usuario']} ({user['hierarquia']})"
                        listbox.insert("end", texto)

                    # Função de seleção (botão + duplo clique)
                    def selecionar_usuario(_event=None):
                        selecao = listbox.curselection()
                        if not selecao:
                            messagebox.showinfo(
                                "Selecionar",
                                "Selecione um usuário na lista.",
                                parent=user_win,
                            )
                            return
                        linha = listbox.get(selecao[0])
                        usuario_nome = linha.replace("•", "", 1).strip()
                        if " (" in usuario_nome:
                            usuario_nome = usuario_nome.split(" (", 1)[0].strip()

                        entry_usuario.delete(0, "end")
                        entry_usuario.insert(0, usuario_nome)

                        try:
                            user_win.grab_release()
                        except Exception:
                            pass
                        user_win.destroy()

                    listbox.bind("<Double-Button-1>", selecionar_usuario)

                    # Botões Selecionar / Fechar
                    botoes_frame = ctk.CTkFrame(
                        user_container, fg_color="transparent"
                    )
                    botoes_frame.pack(fill="x", pady=(8, 5))

                    btn_sel = ctk.CTkButton(
                        botoes_frame,
                        text="✅ Selecionar",
                        command=selecionar_usuario,
                        width=140,
                        height=36,
                        font=("Arial", 12),
                        fg_color=cor_botao_primario,
                        hover_color=cor_botao_primario,
                        corner_radius=8,
                        text_color="white",
                    )
                    btn_sel.pack(side="left", padx=(0, 10))
                    aplicar_hover_inverter(
                        btn_sel,
                        cor_botao_primario,
                        cor_primaria,
                        "white",
                        cor_botao_primario,
                    )

                    btn_fechar = ctk.CTkButton(
                        botoes_frame,
                        text="Fechar",
                        command=lambda: (user_win.grab_release(), user_win.destroy()),
                        width=120,
                        height=36,
                        font=("Arial", 12),
                        fg_color=cor_botao_secundario,
                        hover_color=cor_botao_secundario,
                        corner_radius=8,
                        text_color=cor_texto,
                    )
                    btn_fechar.pack(side="left")
                    aplicar_hover_inverter(
                        btn_fechar,
                        cor_botao_secundario,
                        cor_primaria,
                        cor_texto,
                        cor_botao_secundario,
                    )

                except Exception as e:
                    messagebox.showerror(
                        "Erro",
                        f"Erro ao carregar usuários:\n{e}",
                        parent=login_window,
                    )

            def mostrar_dica_senha():
                """Mostra dica de senha do usuário."""
                usuario = entry_usuario.get().strip()
                if not usuario:
                    messagebox.showinfo(
                        "Dica", "Digite o usuário primeiro.", parent=login_window
                    )
                    return

                try:
                    from BANCO_DE_DADOS_PG import fetch_one

                    resultado = fetch_one(
                        "SELECT dica_senha "
                        "FROM opera.usuarios "
                        "WHERE usuario = %s",
                        (usuario,),
                    )

                    if resultado and resultado.get("dica_senha"):
                        messagebox.showinfo(
                            "Dica de Senha",
                            f"Usuário: {usuario}\n\nDica: {resultado['dica_senha']}",
                            parent=login_window,
                        )
                    else:
                        messagebox.showinfo(
                            "Dica",
                            "Nenhuma dica cadastrada para este usuário.",
                            parent=login_window,
                        )

                except Exception as e:
                    messagebox.showerror(
                        "Erro", f"Erro ao buscar dica:\n{e}", parent=login_window
                    )

            # Linha com os 2 botões de ajuda
            help_inner_frame = ctk.CTkFrame(help_frame, fg_color="transparent")
            help_inner_frame.pack(fill="x")

            btn_listar = ctk.CTkButton(
                help_inner_frame,
                text="👥 Listar Usuários",
                command=listar_usuarios,
                width=160,
                height=36,
                font=("Arial", 12, "bold"),
                fg_color=cor_secundaria,
                hover_color=cor_secundaria,
                corner_radius=8,
                text_color=cor_botao_primario,
            )
            btn_listar.pack(side="left", padx=(0, 8))
            aplicar_hover_inverter(
                btn_listar,
                cor_secundaria,  # normal: cinza claro
                cor_primaria,  # hover: branco
                cor_botao_primario,
                cor_botao_primario,
            )

            btn_dica = ctk.CTkButton(
                help_inner_frame,
                text="🔍 Dica de Senha",
                command=mostrar_dica_senha,
                width=160,
                height=36,
                font=("Arial", 12, "bold"),
                fg_color=cor_secundaria,
                hover_color=cor_secundaria,
                corner_radius=8,
                text_color=cor_botao_primario,
            )
            btn_dica.pack(side="left", padx=8)
            aplicar_hover_inverter(
                btn_dica,
                cor_secundaria,
                cor_primaria,
                cor_botao_primario,
                cor_botao_primario,
            )

            # =========================
            # FUNÇÃO PRINCIPAL DE LOGIN
            # =========================
            def fazer_login():
                usuario = entry_usuario.get().strip()
                senha = entry_senha.get().strip()

                if not usuario or not senha:
                    messagebox.showwarning(
                        "Atenção",
                        "Informe usuário e senha.",
                        parent=login_window,
                    )
                    return

                try:
                    import bcrypt
                    import hashlib
                    from BANCO_DE_DADOS_PG import fetch_one

                    sql = """
                        SELECT 
                            u.id, 
                            u.senha_hash, 
                            u.ativo, 
                            u.hierarquia,
                            COALESCE(up.tema_nome, u.tema_preferido, 'CLÁSSICO CLARO') AS tema_preferido
                        FROM opera.usuarios u
                        LEFT JOIN opera.usuario_preferencias up ON u.id = up.usuario_id
                        WHERE u.usuario = %s
                    """
                    usuario_data = fetch_one(sql, (usuario,))

                    if not usuario_data:
                        messagebox.showerror(
                            "Erro", "Usuário não encontrado.", parent=login_window
                        )
                        return

                    if not usuario_data.get("ativo", True):
                        messagebox.showerror(
                            "Erro", "Usuário inativo.", parent=login_window
                        )
                        return

                    senha_hash = usuario_data["senha_hash"] or ""
                    senha_correta = False

                    # Verificar BCRYPT (pgcrypto)
                    try:
                        if senha_hash.startswith("$2"):
                            if bcrypt.checkpw(senha.encode(), senha_hash.encode()):
                                senha_correta = True
                    except Exception:
                        pass

                    # SHA256 antigo
                    if not senha_correta:

                        def hash_salt(s):
                            return hashlib.sha256(
                                b"sistema_profissional_v2.2" + s.encode()
                            ).hexdigest()

                        def hash_simples(s):
                            return hashlib.sha256(s.encode()).hexdigest()

                        if (
                                senha_hash == hash_salt(senha)
                                or senha_hash == hash_simples(senha)
                        ):
                            senha_correta = True

                    # Texto plano (compatibilidade extrema)
                    if not senha_correta and senha_hash == senha:
                        senha_correta = True

                    if not senha_correta:
                        messagebox.showerror(
                            "Erro", "Senha incorreta.", parent=login_window
                        )
                        return

                    # ============== LOGIN OK ==============
                    # Fechar janela de troca de usuário
                    on_login_close()

                    # Atualizar dados do app
                    self.usuario_id = usuario_data["id"]
                    self.usuario_nome = usuario
                    self.usuario_hierarquia = usuario_data["hierarquia"] or "Padrão"
                    tema_preferido = (
                            usuario_data.get("tema_preferido") or "CLÁSSICO CLARO"
                    )

                    # Atualizar UserManager
                    self.user_manager.usuario_id = self.usuario_id
                    self.user_manager.usuario_nome = self.usuario_nome
                    self.user_manager.usuario_hierarquia = self.usuario_hierarquia

                    # 🔁 RESTAURAR ESTRUTURA COMPLETA DO MENU
                    # (garante que, ao trocar de usuário, a filtragem de permissões
                    #  comece sempre do menu cheio, e não de um menu já filtrado)
                    try:
                        self.MENU_ESTRUTURA = type(self).MENU_ESTRUTURA
                    except Exception:
                        pass

                    # Limpar caches completamente
                    self.permissoes_usuario = {}
                    self.cache_permissoes = {}
                    self.menu_cache = {}
                    self.current_page = None

                    # Recarregar permissões do novo usuário
                    self._load_user_permissions()  # aplica _apply_permissions_to_menu internamente

                    # Carregar tema completo do usuário
                    print(
                        f"🔄 Carregando tema do usuário {self.usuario_nome}: "
                        f"{tema_preferido}"
                    )
                    tema_nome, palette = self.user_manager.load_user_theme_completo()
                    if tema_nome:
                        self.current_theme_name = tema_nome
                        print(f"🎨 Aplicando tema do usuário: {tema_nome}")
                        if palette:
                            self.theme_manager.apply_theme(tema_nome, palette)
                        else:
                            self.theme_manager.apply_theme(tema_nome)
                    else:
                        self.current_theme_name = tema_preferido
                        print(
                            f"🎨 Aplicando tema preferido: {tema_preferido}"
                        )
                        self.theme_manager.apply_theme(tema_preferido)

                    # Reconstruir menu e interface (já com permissões aplicadas)
                    self._build_menu_content()
                    self._update_user_display()
                    self._add_theme_switch_to_topbar()

                    messagebox.showinfo(
                        "Sucesso",
                        f"Usuário alterado para: {usuario}",
                        parent=self,
                    )

                    # Abre o Dashboard respeitando permissão
                    self.open_page("Dashboard")

                except Exception as e:
                    messagebox.showerror(
                        "Erro", f"Erro ao efetuar login:\n{e}", parent=login_window
                    )

            # =========================
            # BOTÕES PRINCIPAIS
            # =========================
            btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=(10, 0))

            btn_entrar = ctk.CTkButton(
                btn_frame,
                text="🎯 ENTRAR NO SISTEMA",
                command=fazer_login,
                width=300,
                height=50,
                font=("Arial", 16, "bold"),
                fg_color=cor_botao_primario,
                hover_color=cor_botao_primario,
                corner_radius=12,
                text_color="white",
            )
            btn_entrar.pack(pady=(0, 12))
            aplicar_hover_inverter(
                btn_entrar,
                cor_botao_primario,
                cor_primaria,
                "white",
                cor_botao_primario,
            )

            btn_cancelar = ctk.CTkButton(
                btn_frame,
                text="❌ CANCELAR",
                command=on_login_close,
                width=300,
                height=40,
                font=("Arial", 14),
                fg_color=cor_botao_secundario,
                hover_color=cor_botao_secundario,
                corner_radius=10,
                text_color=cor_alerta,
            )
            btn_cancelar.pack()
            aplicar_hover_inverter(
                btn_cancelar,
                cor_botao_secundario,
                cor_primaria,
                cor_alerta,
                cor_alerta,
            )

            # Enter → fazer login
            entry_senha.bind("<Return>", lambda e: fazer_login())

            # Exibir janela como modal
            login_window.deiconify()
            login_window.update_idletasks()
            login_window.grab_set()
            login_window.focus_force()
            entry_usuario.focus_set()

            print("✅ Janela de trocar usuário aberta com tema aplicado corretamente")

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