# -*- coding: utf-8 -*-
"""
MENU_PRINCIPAL.py - Sistema OPERA Refatorado com Performance e Funcionalidade Completa
Inclui tradução recursiva de widgets (otimizada) e todas as features originais.
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
import queue
from datetime import datetime

import tkinter as tk
from tkinter import messagebox, ttk, font as tkfont

from PIL import Image, ImageTk
import customtkinter as ctk

# ===== CONFIGURAÇÕES DE PERFORMANCE =====
OPERA_DEBUG = bool(os.environ.get('OPERA_DEBUG', '').strip())
ACTIVITY_DB_LOG_ENABLED = os.environ.get("OPERA_DB_ACTIVITY_LOG", "0").strip().lower() in {"1", "true", "yes", "on"}
ACTIVITY_LOGGING_ENABLED = os.environ.get("OPERA_ACTIVITY_LOG", "1") == "1"
OPERA_NO_HOVER = os.environ.get("OPERA_NO_HOVER", "0") == "1"

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
except ImportError:
    LOGS_DISPONIVEIS = False
    def registrar_log_db(usuario, acao, pagina, detalhe=""): pass

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema
    MENU_POSTGRES_AVAILABLE = True
except Exception:
    MENU_POSTGRES_AVAILABLE = False
    def get_conn(): raise RuntimeError("PostgreSQL indisponível")
    def get_schema(): return "opera"

# Cooldown do banco (5s)
if MENU_POSTGRES_AVAILABLE:
    _raw_get_conn = get_conn
    _DB_FAIL_UNTIL = 0.0
    _DB_COOLDOWN_SECONDS = 5.0
    def get_conn(*args, **kwargs):
        global _DB_FAIL_UNTIL
        now = time.time()
        if now < _DB_FAIL_UNTIL:
            raise RuntimeError("Banco indisponível (cooldown)")
        try:
            return _raw_get_conn(*args, **kwargs)
        except Exception as e:
            _DB_FAIL_UNTIL = now + _DB_COOLDOWN_SECONDS
            raise e

# ===== FUNÇÕES AUXILIARES =====
def is_dark_color_fallback(hex_color: str) -> bool:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    try:
        r, g, b = int(hex_color[0:2],16), int(hex_color[2:4],16), int(hex_color[4:6],16)
        return (0.299*r + 0.587*g + 0.114*b)/255 < 0.5
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
    local = os.path.join(APP_DIR, filename)
    if os.path.exists(local): return local
    base = os.path.join(BASE_DIR, filename)
    if os.path.exists(base): return base
    return os.path.join(ROOT_DIR, filename)

ROUTES_PATH = _resolve_app_path("route_map.json")
SETTINGS_PATH = _resolve_app_path("settings.json")
ICONS_DIR = _resolve_app_path("icons")
ICONE_SISTEMA = _resolve_app_path("ICONE_SISTEMA.png")

# ===== GERENCIADOR DE CONFIGURAÇÕES =====
class ConfigManager:
    @staticmethod
    def load_settings() -> dict:
        default = {"theme": "CLÁSSICO CLARO", "last_page": "Dashboard", "language": "pt_BR", "preload_last_page": True}
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict): default.update(data)
            except: pass
        return default
    @staticmethod
    def save_settings(data: dict):
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except: pass
    @staticmethod
    def load_routes() -> dict:
        for path in [ROUTES_PATH, os.path.join(BASE_DIR, "route_map.json")]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f) or {}
                except: pass
        return {}
    @staticmethod
    def ensure_icons_directory():
        os.makedirs(ICONS_DIR, exist_ok=True)
        return ICONS_DIR

# ===== GERENCIADOR DE TEMAS (VERSÃO LEVE MAS COMPLETA) =====
class ThemeManager:
    def __init__(self, app):
        self.app = app
        self.current_theme_name = None
        self.current_palette = None
        self.fonts = self._default_fonts()
        self._init_global_styles()

    def _init_global_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Opera.TButton', relief='flat', borderwidth=0, padding=6)
        style.configure('Opera.Treeview', rowheight=28, borderwidth=0)
        style.configure('Opera.Vertical.TScrollbar', troughcolor='#2d2d30', background='#007acc')
        style.configure('Opera.Horizontal.TScrollbar', troughcolor='#2d2d30', background='#007acc')

    def _default_fonts(self):
        return {"title": ("Arial",14,"bold"), "heading": ("Arial",12,"bold"), "body": ("Arial",12), "small": ("Arial",11), "button": ("Arial",12,"bold")}

    def apply_theme(self, theme_name: str, palette: dict = None, *, rebuild_interface: bool = False):
        from PAGINAS_DO_SISTEMA.TEMAS import ModuloPaletas
        if palette:
            pal = dict(palette)
        else:
            pal = ModuloPaletas().PADROES.get(theme_name, ModuloPaletas().PADROES.get("CLÁSSICO CLARO", {}))
        self.current_theme_name = theme_name
        self.current_palette = pal
        for k,v in pal.items():
            setattr(self.app, f"cor_{k}", v)
        modo = "dark" if is_dark_color(pal.get("fundo","#000000")) else "light"
        ctk.set_appearance_mode(modo)
        self.app.tema_modo = modo
        self._update_ttk_styles(pal)
        if hasattr(self.app, "_update_menu_buttons_colors"):
            self.app._update_menu_buttons_colors()
        if rebuild_interface:
            self._rebuild_interface()
        self._persist_theme(theme_name, pal)
        _dprint(f"[Tema] '{theme_name}' aplicado (modo {modo})")

    def _update_ttk_styles(self, pal):
        style = ttk.Style()
        style.configure('Opera.TButton', background=pal.get("secundaria","#1F2937"), foreground=pal.get("texto","#FFFFFF"))
        style.map('Opera.TButton', background=[('active', pal.get("hover","#374151"))])
        style.configure('Opera.Treeview', background=pal.get("fundo","#181818"), fieldbackground=pal.get("fundo","#181818"), foreground=pal.get("texto","#FFFFFF"))
        style.configure('Opera.Treeview.Heading', background=pal.get("primaria","#3B82F6"), foreground=get_contraste_texto(pal.get("primaria","#3B82F6")))
        style.configure('Opera.Vertical.TScrollbar', troughcolor=pal.get("secundaria","#1F2937"), background=pal.get("primaria","#3B82F6"))
        style.configure('Opera.Horizontal.TScrollbar', troughcolor=pal.get("secundaria","#1F2937"), background=pal.get("primaria","#3B82F6"))

    def _persist_theme(self, theme_name, palette):
        try:
            settings = ConfigManager.load_settings()
            settings["theme"] = theme_name
            ConfigManager.save_settings(settings)
            if hasattr(self.app, "user_manager") and self.app.user_manager:
                self.app.user_manager.save_user_theme(theme_name)
        except: pass

    def apply_theme_to_widget(self, widget):
        if not widget or getattr(widget, '_theme_applied', False):
            return
        pal = self.current_palette or {}
        if not pal: return
        try:
            if isinstance(widget, (ctk.CTkFrame, ctk.CTkScrollableFrame)):
                widget.configure(fg_color=pal.get("fundo"), border_color=pal.get("borda"))
            elif isinstance(widget, ctk.CTkButton):
                widget.configure(fg_color=pal.get("primaria"), hover_color=pal.get("hover"),
                                 text_color=get_contraste_texto(pal.get("primaria")))
            elif isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=pal.get("texto"))
            elif isinstance(widget, (ctk.CTkEntry, ctk.CTkComboBox)):
                widget.configure(fg_color=pal.get("secundaria"), text_color=pal.get("texto"), border_color=pal.get("borda"))
            elif isinstance(widget, ttk.Treeview):
                padronizar_treeview(widget)
            widget._theme_applied = True
        except: pass

    def _rebuild_interface(self):
        try:
            app = self.app
            _dprint("🔄 Reconstruindo interface (modo claro/escuro)...")
            if hasattr(app, 'sidebar'):
                app.sidebar.destroy()
            if hasattr(app, 'main'):
                app.main.destroy()
            if hasattr(app, 'submenu_frames'):
                for f in list(app.submenu_frames.values()):
                    try: f.destroy()
                    except: pass
                app.submenu_frames.clear()
            if hasattr(app, 'botoes_menu'):
                app.botoes_menu.clear()
            if hasattr(app, "_page_cache"):
                for cached in list(app._page_cache.values()):
                    try: cached.destroy()
                    except: pass
                app._page_cache.clear()
                app._page_cache_order = []
                app._current_frame = None
            app._build_interface()
            remover_bordas_botoes_tema(app)
            if hasattr(app, '_update_user_display'):
                app._update_user_display()
            if app.current_page:
                app.open_page(app.current_page)
        except Exception as e:
            _dprint(f"[Tema] Erro na reconstrução: {e}")

# ===== GERENCIADOR DE USUÁRIO COM CARREGAMENTO ASSÍNCRONO =====
class UserManager:
    def __init__(self, app=None, usuario_id=None, usuario_nome=None, usuario_hierarquia=None):
        self.app = app
        self.usuario_id = usuario_id
        self.usuario_nome = usuario_nome or "Admin"
        self.usuario_hierarquia = usuario_hierarquia or "Administrador"
        self.permissoes = {}
        self._permissions_loaded = threading.Event()

    def load_user_permissions_async(self, callback=None):
        def _load():
            try:
                if not self.usuario_id:
                    self.permissoes = {}
                elif self.usuario_hierarquia and self.usuario_hierarquia.lower() in ("admin","administrador"):
                    self.permissoes = {cod: {"ver":True,"editar":True,"imprimir":True,"excluir":True,"administrar":True}
                                       for cod in self.app.PAGE_PERMISSION_MAP.values()}
                else:
                    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import fetch_all
                    sql = "SELECT codigo, pode_ver, pode_editar, pode_imprimir, pode_excluir, pode_administrar FROM opera.usuario_permissoes WHERE usuario_id = %s"
                    rows = fetch_all(sql, (self.usuario_id,))
                    self.permissoes = {r["codigo"]: {"ver":r["pode_ver"],"editar":r["pode_editar"],"imprimir":r["pode_imprimir"],"excluir":r["pode_excluir"],"administrar":r["pode_administrar"]}
                                       for r in rows}
                self._permissions_loaded.set()
                if callback:
                    self.app.after_idle(callback)
            except Exception as e:
                _dprint(f"[Permissões] Erro async: {e}")
                self.permissoes = {}
                self._permissions_loaded.set()
        threading.Thread(target=_load, daemon=True).start()

    def has_permission(self, pagina, acao="ver", categoria=None):
        if self.usuario_hierarquia and self.usuario_hierarquia.lower() in ("admin","administrador"):
            return True
        if not self._permissions_loaded.is_set():
            return True
        page_map = getattr(self.app.__class__, "PAGE_PERMISSION_MAP", {})
        codigo = page_map.get(f"{categoria}:{pagina}") or page_map.get(pagina)
        if not codigo or codigo in {"dashboard","config_temas"}:
            return True
        perm = self.permissoes.get(codigo)
        return bool(perm and perm.get(acao, False))

    def load_user_theme_completo(self):
        default = "CLÁSSICO CLARO"
        if not getattr(self.app, "usuario_id", None):
            return default, None
        try:
            schema = get_schema()
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(f"SELECT COALESCE(up.tema_nome, u.tema_preferido, %s) AS tema_nome, up.usar_tema_personalizado, up.tema_personalizado FROM {schema}.usuarios u LEFT JOIN {schema}.usuario_preferencias up ON u.id = up.usuario_id WHERE u.id = %s", (default, self.app.usuario_id))
                row = cur.fetchone()
            if row and row[1] and row[2]:
                return row[0], json.loads(row[2])
            return row[0] if row else default, None
        except Exception as e:
            _dprint(f"[UserManager] Erro tema: {e}")
            return default, None

    def save_user_theme(self, theme_name: str):
        if not getattr(self.app, "usuario_id", None): return
        schema = get_schema()
        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(f"INSERT INTO {schema}.usuario_preferencias (usuario_id, tema_nome, usar_tema_personalizado) VALUES (%s, %s, FALSE) ON CONFLICT (usuario_id) DO UPDATE SET tema_nome = EXCLUDED.tema_nome, usar_tema_personalizado = FALSE, tema_personalizado = NULL", (self.app.usuario_id, theme_name))
                conn.commit()
        except: pass

    def save_user_theme_personalizado(self, theme_name, palette_json):
        if not getattr(self.app, "usuario_id", None): return
        schema = get_schema()
        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(f"INSERT INTO {schema}.usuario_preferencias (usuario_id, tema_nome, usar_tema_personalizado, tema_personalizado) VALUES (%s, %s, TRUE, %s) ON CONFLICT (usuario_id) DO UPDATE SET tema_nome = EXCLUDED.tema_nome, usar_tema_personalizado = TRUE, tema_personalizado = EXCLUDED.tema_personalizado", (self.app.usuario_id, theme_name, palette_json))
                conn.commit()
        except: pass

# ===== APLICAÇÃO PRINCIPAL (REFATORADA COM FUNCIONALIDADE COMPLETA) =====
class OperaMenuApp(ctk.CTk):
    SIDEBAR_WIDTH = 300
    ITEM_HEIGHT = 40
    TOPBAR_HEIGHT = 48

    ICON_MAPPING = {
        "Dashboard": "DASHBORD.png", "MODELOS": "ROUPA.png", "ORDENS DE CORTE": "TESOURA.png",
        "REGISTRO DE CORTE": "FOLHA DE PAPEL.png", "ESTOQUE": "ESTOQUE.png", "COMPRAS": "DINHEIRO.png",
        "COMERCIAL": "USUARIOS.png", "PRESTADORES": "FABRICA.png", "MÃO DE OBRA": "PESSOAS.png",
        "PRODUÇÃO": "PRODUÇAO.png", "ACABAMENTO": "FERRAMENTAS.png", "FINANCEIRO": "DINHEIRO.png",
        "PLANEJAMENTO": "RELATORIO.png", "RELATÓRIOS": "RELATORIO.png", "CONFIGURAÇÕES": "ENGRENAGEM.png",
        "BANCO DE DADOS": "BANCO DE DADOS.png",
    }
    MENU_ESTRUTURA = {
        "Dashboard": ["Dashboard"], "MODELOS": ["Cadastrar Modelo", "Imprimir Ficha Técnica"],
        "ORDENS DE CORTE": ["Nova Ordem", "Ordens Planejadas", "Ordens de Corte Impressão"],
        "REGISTRO DE CORTE": ["Cadastrar Corte", "Consultar Ordens"], "MÃO DE OBRA": ["Controle de Mão de Obra"],
        "COMPRAS": ["Compras"], "ESTOQUE": ["Entrada de Estoque", "Saída de Estoque", "Relatórios"],
        "COMERCIAL": ["Clientes"], "PRESTADORES": ["Cadastro de Prestadores", "Pesquisar Serviço"],
        "ACABAMENTO": ["Registro Acabamento", "Finalizar Corte / Acabamento", "Retrabalho de Defeitos"],
        "PLANEJAMENTO": ["MRP", "Planejamento de Produção", "Custos Reais"],
        "FINANCEIRO": ["Pagamento de Serviços", "Recibos de Pagamentos", "Custo Produto", "Folha Pagamento", "Fechamento Mensal", "Contas a Pagar", "Adiantamento", "Adiantamentos Pendentes"],
        "RELATÓRIOS": ["Produção", "Serviços Externos", "Modelos Produzidos", "Acabamento", "Logs e Atividades"],
        "CONFIGURAÇÕES": ["Trocar Usuário", "Usuários", "Temas", "Atualizar Sistema"],
        "BANCO DE DADOS": ["Gerenciar", "Backup"],
    }
    SUBMENU_ICON_MAPPING = {
        "Dashboard":{"Dashboard":"DASHBORD.png"},
        "MODELOS":{"Cadastrar Modelo":"ROUPA.png","Imprimir Ficha Técnica":"IMPRESSORA.png"},
        "ORDENS DE CORTE":{"Nova Ordem":"NOVA_ORDEM.png","Ordens Planejadas":"RELATORIO.png","Ordens de Corte Impressão":"IMPRESSORA.png"},
        "REGISTRO DE CORTE":{"Cadastrar Corte":"CADASTRO_CORTE.png","Consultar Ordens":"CONSULTAR ORDENS.png"},
        "COMPRAS":{"Compras":"DINHEIRO.png"},"ESTOQUE":{"Entrada de Estoque":"ESTOQUE.png","Saída de Estoque":"ESTOQUE.png","Relatórios":"RELATORIO 2.png"},
        "COMERCIAL":{"Clientes":"USUARIOS.png"},"PRESTADORES":{"Cadastro de Prestadores":"FACÇAO.png","Pesquisar Serviço":"CONSULTAR ORDENS.png"},
        "MÃO DE OBRA":{"Controle de Mão de Obra":"MAO DE OBRA.png"},"PLANEJAMENTO":{"MRP":"RELATORIO.png","Planejamento de Produção":"PRODUÇAO.png","Custos Reais":"RELATORIO.png"},
        "PRODUÇÃO":{"Produção":"PRODUÇAO.png"},"ACABAMENTO":{"Registro Acabamento":"ACABAMENTO.png","Finalizar Corte / Acabamento":"ACABAMENTO.png","Retrabalho de Defeitos":"ACABAMENTO.png"},
        "FINANCEIRO":{"Pagamento de Serviços":"DINHEIRO.png","Recibos de Pagamentos":"IMPRESSORA.png","Custo Produto":"DINHEIRO.png","Folha Pagamento":"DINHEIRO.png","Fechamento Mensal":"DINHEIRO.png","Contas a Pagar":"DINHEIRO.png","Adiantamento":"DINHEIRO.png","Adiantamentos Pendentes":"DINHEIRO.png"},
        "RELATÓRIOS":{"Produção":"PRODUÇAO.png","Serviços Externos":"SERVIÇOS EXTERNOS.png","Modelos Produzidos":"MODELOS PRODUZIDOS.png","Acabamento":"ACABAMENTO.png","Logs e Atividades":"RELATORIO.png"},
        "CONFIGURAÇÕES":{"Trocar Usuário":"TROCAR_USUARIO.png","Usuários":"USUARIOS.png","Backup":"BACKUP.png","Temas":"PALETA DE CORES.png","Atualizar Sistema":"ENGRENAGEM.png"},
        "BANCO DE DADOS":{"Gerenciar":"ENGRENAGEM.png","Backup":"BACKUP.png"},
    }
    PAGE_PERMISSION_MAP = {
        "Dashboard":"dashboard","Cadastrar Modelo":"cadastro_modelos","Imprimir Ficha Técnica":"ficha_tecnica",
        "Nova Ordem":"ordem_corte","Ordens Planejadas":"ordem_corte","Ordens de Corte Impressão":"ordem_corte_impressao",
        "Cadastrar Corte":"cadastro_corte","Consultar Ordens":"consultar_ordens","Entrada de Estoque":"estoque_entrada",
        "Saída de Estoque":"estoque_saida","Relatórios":"estoque_relatorios","Cadastro de Prestadores":"cadastro_faccoes",
        "Pesquisar Serviço":"pesquisar_servico","Controle de Mão de Obra":"controle_mao_obra","Retrabalho de Defeitos":"retrabalho_defeitos",
        "Produção":"Producao","Registro Acabamento":"registro_acabamento","Finalizar Corte / Acabamento":"finalizar_corte",
        "Pagamento de Serviços":"pagamento_servicos","Recibos de Pagamentos":"recibos_pagamentos","Custo Produto":"custo_produto",
        "Folha Pagamento":"folha_pagamento","Fechamento Mensal":"fechamento_mensal","Contas a Pagar":"contas_pagar",
        "Adiantamento":"adiantamento","Adiantamentos Pendentes":"adiantamentos_pendentes","RELATÓRIOS:Produção":"relatorio_Producao",
        "Serviços Externos":"relatorio_servicos_externos","Modelos Produzidos":"relatorio_modelos_produzidos",
        "Acabamento":"relatorio_acabamento","Logs e Atividades":"config_usuarios","Trocar Usuário":"trocar_usuario",
        "Usuários":"config_usuarios","Backup":"config_backup","Temas":"config_temas","Atualizar Sistema":"config_atualizacao",
        "Gerenciar":"banco_dados",
    }
    SUPPORTED_LANGUAGES = {"pt_BR":"Português (Brasil)","en_US":"English (US)","es_ES":"Español"}
    UI_TEXTS = {
        "pt_BR":{"system_title":"SISTEMA OPERA","main_menu":"Menu Principal","topbar_dashboard":"Dashboard","language":"Idioma","current_language":"Idioma atual","refresh_page":"Atualizar página","switch_user":"Trocar usuário","loading":"Carregando...","error":"Erro","exit_title":"Sair","exit_confirm":"Deseja realmente sair do sistema?","yes":"Sim","no":"Não","language_changed":"Idioma alterado para {language}","no_permission":"Sem permissão para acessar {page}","clock_format":"%d/%m/%Y %H:%M:%S","loading_page":"Carregando sistema..."},
        "en_US":{"system_title":"OPERA SYSTEM","main_menu":"Main Menu","topbar_dashboard":"Dashboard","language":"Language","current_language":"Current language","refresh_page":"Refresh page","switch_user":"Switch user","loading":"Loading...","error":"Error","exit_title":"Exit","exit_confirm":"Do you really want to exit the system?","yes":"Yes","no":"No","language_changed":"Language changed to {language}","no_permission":"No permission to access {page}","clock_format":"%m/%d/%Y %I:%M:%S %p","loading_page":"Loading system..."},
        "es_ES":{"system_title":"SISTEMA OPERA","main_menu":"Menú Principal","topbar_dashboard":"Panel","language":"Idioma","current_language":"Idioma actual","refresh_page":"Actualizar página","switch_user":"Cambiar usuario","loading":"Cargando...","error":"Error","exit_title":"Salir","exit_confirm":"¿Realmente desea salir del sistema?","yes":"Sí","no":"No","language_changed":"Idioma cambiado a {language}","no_permission":"Sin permiso para acceder a {page}","clock_format":"%d/%m/%Y %H:%M:%S","loading_page":"Cargando sistema..."},
    }
    MENU_LABELS = {
        "Dashboard":{"pt_BR":"Dashboard","en_US":"Dashboard","es_ES":"Panel"},
        "MODELOS":{"pt_BR":"MODELOS","en_US":"MODELS","es_ES":"MODELOS"},
        "ORDENS DE CORTE":{"pt_BR":"ORDENS DE CORTE","en_US":"CUT ORDERS","es_ES":"ÓRDENES DE CORTE"},
        "REGISTRO DE CORTE":{"pt_BR":"REGISTRO DE CORTE","en_US":"CUT RECORDS","es_ES":"REGISTRO DE CORTE"},
        "MÃO DE OBRA":{"pt_BR":"MÃO DE OBRA","en_US":"LABOR","es_ES":"MANO DE OBRA"},
        "COMPRAS":{"pt_BR":"COMPRAS","en_US":"PURCHASING","es_ES":"COMPRAS"},
        "ESTOQUE":{"pt_BR":"ESTOQUE","en_US":"INVENTORY","es_ES":"STOCK"},
        "COMERCIAL":{"pt_BR":"COMERCIAL","en_US":"SALES","es_ES":"COMERCIAL"},
        "PRESTADORES":{"pt_BR":"PRESTADORES","en_US":"PROVIDERS","es_ES":"PRESTADORES"},
        "ACABAMENTO":{"pt_BR":"ACABAMENTO","en_US":"FINISHING","es_ES":"ACABADO"},
        "PLANEJAMENTO":{"pt_BR":"PLANEJAMENTO","en_US":"PLANNING","es_ES":"PLANIFICACIÓN"},
        "FINANCEIRO":{"pt_BR":"FINANCEIRO","en_US":"FINANCIAL","es_ES":"FINANZAS"},
        "RELATÓRIOS":{"pt_BR":"RELATÓRIOS","en_US":"REPORTS","es_ES":"INFORMES"},
        "CONFIGURAÇÕES":{"pt_BR":"CONFIGURAÇÕES","en_US":"SETTINGS","es_ES":"CONFIGURACIÓN"},
        "BANCO DE DADOS":{"pt_BR":"BANCO DE DADOS","en_US":"DATABASE","es_ES":"BASE DE DATOS"},
        "Cadastrar Modelo":{"pt_BR":"Cadastrar Modelo","en_US":"Register Model","es_ES":"Registrar Modelo"},
        "Imprimir Ficha Técnica":{"pt_BR":"Imprimir Ficha Técnica","en_US":"Print Technical Sheet","es_ES":"Imprimir Ficha Técnica"},
        "Nova Ordem":{"pt_BR":"Nova Ordem","en_US":"New Order","es_ES":"Nueva Orden"},
        "Ordens Planejadas":{"pt_BR":"Ordens Planejadas","en_US":"Planned Orders","es_ES":"Órdenes Planificadas"},
        "Ordens de Corte Impressão":{"pt_BR":"Ordens de Corte Impressão","en_US":"Print Cut Orders","es_ES":"Impresión de Órdenes"},
        "Cadastrar Corte":{"pt_BR":"Cadastrar Corte","en_US":"Register Cut","es_ES":"Registrar Corte"},
        "Consultar Ordens":{"pt_BR":"Consultar Ordens","en_US":"Consult Orders","es_ES":"Consultar Órdenes"},
        "Controle de Mão de Obra":{"pt_BR":"Controle de Mão de Obra","en_US":"Labor Control","es_ES":"Control de Mano de Obra"},
        "Compras":{"pt_BR":"Compras","en_US":"Purchases","es_ES":"Compras"},
        "Entrada de Estoque":{"pt_BR":"Entrada de Estoque","en_US":"Stock Entry","es_ES":"Entrada de Stock"},
        "Saída de Estoque":{"pt_BR":"Saída de Estoque","en_US":"Stock Output","es_ES":"Salida de Stock"},
        "Relatórios":{"pt_BR":"Relatórios","en_US":"Reports","es_ES":"Informes"},
        "Clientes":{"pt_BR":"Clientes","en_US":"Clients","es_ES":"Clientes"},
        "Cadastro de Prestadores":{"pt_BR":"Cadastro de Prestadores","en_US":"Providers Register","es_ES":"Registro de Prestadores"},
        "Pesquisar Serviço":{"pt_BR":"Pesquisar Serviço","en_US":"Search Service","es_ES":"Buscar Servicio"},
        "Registro Acabamento":{"pt_BR":"Registro Acabamento","en_US":"Finishing Record","es_ES":"Registro de Acabado"},
        "Finalizar Corte / Acabamento":{"pt_BR":"Finalizar Corte / Acabamento","en_US":"Finalize Cut / Finishing","es_ES":"Finalizar Corte / Acabado"},
        "Retrabalho de Defeitos":{"pt_BR":"Retrabalho de Defeitos","en_US":"Defect Rework","es_ES":"Retrabajo de Defectos"},
        "MRP":{"pt_BR":"MRP","en_US":"MRP","es_ES":"MRP"},
        "Planejamento de Produção":{"pt_BR":"Planejamento de Produção","en_US":"Production Planning","es_ES":"Planificación de Producción"},
        "Custos Reais":{"pt_BR":"Custos Reais","en_US":"Actual Costs","es_ES":"Costos Reales"},
        "Pagamento de Serviços":{"pt_BR":"Pagamento de Serviços","en_US":"Service Payments","es_ES":"Pago de Servicios"},
        "Recibos de Pagamentos":{"pt_BR":"Recibos de Pagamentos","en_US":"Payment Receipts","es_ES":"Recibos de Pago"},
        "Custo Produto":{"pt_BR":"Custo Produto","en_US":"Product Cost","es_ES":"Costo del Producto"},
        "Folha Pagamento":{"pt_BR":"Folha Pagamento","en_US":"Payroll","es_ES":"Nómina"},
        "Fechamento Mensal":{"pt_BR":"Fechamento Mensal","en_US":"Monthly Closing","es_ES":"Cierre Mensual"},
        "Contas a Pagar":{"pt_BR":"Contas a Pagar","en_US":"Accounts Payable","es_ES":"Cuentas por Pagar"},
        "Adiantamento":{"pt_BR":"Adiantamento","en_US":"Advance","es_ES":"Adelanto"},
        "Adiantamentos Pendentes":{"pt_BR":"Adiantamentos Pendentes","en_US":"Pending Advances","es_ES":"Adelantos Pendientes"},
        "Produção":{"pt_BR":"Produção","en_US":"Production","es_ES":"Producción"},
        "Serviços Externos":{"pt_BR":"Serviços Externos","en_US":"External Services","es_ES":"Servicios Externos"},
        "Modelos Produzidos":{"pt_BR":"Modelos Produzidos","en_US":"Produced Models","es_ES":"Modelos Producidos"},
        "Logs e Atividades":{"pt_BR":"Logs e Atividades","en_US":"Logs and Activities","es_ES":"Registros y Actividades"},
        "Trocar Usuário":{"pt_BR":"Trocar Usuário","en_US":"Switch User","es_ES":"Cambiar Usuario"},
        "Usuários":{"pt_BR":"Usuários","en_US":"Users","es_ES":"Usuarios"},
        "Temas":{"pt_BR":"Temas","en_US":"Themes","es_ES":"Temas"},
        "Atualizar Sistema":{"pt_BR":"Atualizar Sistema","en_US":"Update System","es_ES":"Actualizar Sistema"},
        "Gerenciar":{"pt_BR":"Gerenciar","en_US":"Manage","es_ES":"Gestionar"},
        "Backup":{"pt_BR":"Backup","en_US":"Backup","es_ES":"Respaldo"},
    }

    # Cache estático de ícones
    _shared_icons_cache = {}
    _current_icon_size = None

    def __init__(self, usuario_id=None, usuario_nome="Admin", usuario_hierarquia="Administrador", tema_preferido=None):
        reset_tk_default_root()
        super().__init__()
        self.withdraw()
        self._closing = False
        self._page_loading = False
        self._preload_complete = False
        initialize_after_guard(self)

        # Atributos de interface
        self.cor_fundo = "#1e1e1e"
        self.cor_primaria = "#2d2d30"
        self.cor_secundaria = "#3e3e42"
        self.cor_texto = "#cccccc"
        self.cor_borda = "#404040"
        self.cor_hover = "#4a4a4a"
        self.cor_destaque = "#007acc"

        # Dados do usuário
        self.usuario_id = usuario_id or 0
        self.usuario_nome = usuario_nome or "Administrador Local"
        self.usuario_hierarquia = usuario_hierarquia or "Admin"
        self.settings = ConfigManager.load_settings()
        self.routes = ConfigManager.load_routes()
        ConfigManager.ensure_icons_directory()
        self.idioma_atual = self.settings.get("language", "pt_BR")
        if self.idioma_atual not in self.SUPPORTED_LANGUAGES:
            self.idioma_atual = "pt_BR"

        # Managers
        self.theme_manager = ThemeManager(self)
        self.user_manager = UserManager(self, self.usuario_id, self.usuario_nome, self.usuario_hierarquia)

        # Estado da UI
        self.current_theme_name = None
        self.current_page = None
        self.submenu_frames = {}
        self.botoes_menu = {}
        self._active_submenu = None
        self._submenu_timer = None
        self._page_cache = {}
        self._page_cache_order = []
        self._page_cache_size = 4
        self._current_frame = None
        self.permissoes_usuario = {}
        self.icons_cache = {}

        # Configurações de escala
        self._calculate_initial_scale()
        self._setup_window()
        self._load_initial_theme()
        self._load_icons_static()
        self._build_interface()
        self.user_manager.load_user_permissions_async(callback=self._on_permissions_loaded)
        self._setup_bindings()
        self._setup_activity_logging()
        self._startup_tasks()
        self._preload_complete = True
        self.deiconify()
        self.lift()
        self.focus_force()

    # ===== MÉTODOS DE FECHAMENTO CORRETO =====
    def destroy(self):
        if self._closing:
            return
        self._closing = True
        try:
            if hasattr(self, '_activity_db_worker_stop'):
                self._activity_db_worker_stop.set()
            if hasattr(self, '_activity_db_queue'):
                self._activity_db_queue.put_nowait(None)
        except:
            pass
        cancel_all_afters(self)
        cancel_all_after_info(self)
        self._current_frame = None
        self._page_cache.clear()
        self.submenu_frames.clear()
        self.botoes_menu.clear()
        try:
            self.withdraw()
            self.update_idletasks()
        except:
            pass
        super().destroy()
        try:
            os._exit(0)
        except:
            pass

    # ===== CONFIGURAÇÕES INICIAIS =====
    def _calculate_initial_scale(self):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        base = min(sw/1920, sh/1080)
        self.ui_scale = max(0.68, min(1.0, base))
        ctk.set_widget_scaling(self.ui_scale)
        ctk.set_window_scaling(self.ui_scale)
        self.SIDEBAR_WIDTH = max(220, int(300 * self.ui_scale))
        self.ITEM_HEIGHT = max(32, int(40 * self.ui_scale))
        self.TOPBAR_HEIGHT = max(36, int(48 * self.ui_scale))
        self.font_sidebar_titulo = ("Arial", max(14, int(22*self.ui_scale)), "bold")
        self.font_sidebar_subtitulo = ("Arial", max(11, int(16*self.ui_scale)))
        self.font_topbar_titulo = ("Arial", max(14, int(26*self.ui_scale)))
        self.font_topbar_icone = ("Arial", max(14, int(22*self.ui_scale)))
        self.icon_size_sidebar = max(28, int(52*self.ui_scale))

    def _setup_window(self):
        self.title("OPERA • Sistema de Gestão")
        if os.path.exists(ICONE_SISTEMA):
            try:
                self.iconphoto(True, ImageTk.PhotoImage(Image.open(ICONE_SISTEMA)))
            except: pass
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        if IS_WIN:
            self.geometry(f"{sw-16}x{sh-80}+0+0")
        elif IS_MAC:
            self.geometry(f"{sw-20}x{sh-120}+0+25")
        else:
            self.geometry(f"{sw-16}x{sh-80}+0+0")
        self.minsize(min(900, sw), min(620, sh))
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda e: self.ask_quit())
        self.protocol("WM_DELETE_WINDOW", self.ask_quit)

    def toggle_fullscreen(self, event=None):
        self.attributes('-fullscreen', not self.attributes('-fullscreen'))

    def ask_quit(self, event=None):
        if self._closing: return
        if messagebox.askyesno(self._get_text("exit_title"), self._get_text("exit_confirm"), parent=self):
            self.destroy()

    def _setup_bindings(self):
        self.bind("<F5>", lambda e: self.reload_current_page())
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        if IS_WIN:
            self.bind("<Escape>", lambda e: self.ask_quit())
            self.bind("<Control-q>", lambda e: self.ask_quit())
        elif IS_MAC:
            self.bind("<Command-q>", lambda e: self.ask_quit())
            self.bind("<Command-f>", lambda e: self.toggle_fullscreen())

    # ===== LOGS DE ATIVIDADE (OPCIONAL) =====
    def _setup_activity_logging(self):
        if not ACTIVITY_LOGGING_ENABLED:
            return
        self._activity_logger = get_logger(APP_DIR)
        self._activity_logger.set_usuario(self.usuario_nome, self.usuario_hierarquia)
        self._activity_logger.set_pagina(self.current_page or "MenuPrincipal")
        self._activity_log_cache = {}
        self._activity_db_queue = queue.Queue(maxsize=300)
        self._activity_db_worker_stop = threading.Event()
        self._activity_db_worker = threading.Thread(target=self._db_log_worker_loop, name="opera-db-log-worker", daemon=True)
        self._activity_db_worker.start()
        self.bind_all("<ButtonRelease-1>", self._on_user_click, add="+")
        self.bind_all("<<TreeviewSelect>>", self._on_treeview_select, add="+")
        self.bind_all("<<ComboboxSelected>>", self._on_combobox_select, add="+")
        self.bind_all("<KeyRelease>", self._on_user_key, add="+")

    def _db_log_worker_loop(self):
        while not self._closing and not self._activity_db_worker_stop.is_set():
            try:
                item = self._activity_db_queue.get(timeout=0.8)
            except queue.Empty:
                continue
            if item is None:
                self._activity_db_queue.task_done()
                break
            try:
                registrar_log_db(*item)
            except Exception as e:
                _dprint(f"⚠️ Falha ao gravar log no banco: {e}")
            finally:
                self._activity_db_queue.task_done()

    def _enqueue_db_log(self, usuario, pagina, acao, detalhe):
        if not LOGS_DISPONIVEIS or not MENU_POSTGRES_AVAILABLE:
            return
        try:
            self._activity_db_queue.put_nowait((usuario, pagina, acao, detalhe))
        except queue.Full:
            pass

    def _log_user_activity(self, acao, detalhe="", pagina=None):
        if not ACTIVITY_LOGGING_ENABLED:
            return
        pagina_log = pagina or self.current_page or "MenuPrincipal"
        self._activity_logger.set_usuario(self.usuario_nome, self.usuario_hierarquia)
        self._activity_logger.set_pagina(pagina_log)
        self._activity_logger.log_usuario(acao, {"detalhe": detalhe, "pagina": pagina_log})
        if ACTIVITY_DB_LOG_ENABLED and LOGS_DISPONIVEIS and MENU_POSTGRES_AVAILABLE:
            registrar_log_db(self.usuario_nome, pagina_log, acao, detalhe)

    def _should_log_event(self, chave, intervalo=0.4):
        if not ACTIVITY_LOGGING_ENABLED:
            return False
        agora = time.monotonic()
        ultimo = self._activity_log_cache.get(chave, 0.0)
        if (agora - ultimo) < intervalo:
            return False
        self._activity_log_cache[chave] = agora
        return True

    def _on_user_click(self, event):
        if not ACTIVITY_LOGGING_ENABLED: return
        widget = event.widget
        if not widget or widget is self: return
        try: widget_class = widget.winfo_class()
        except: widget_class = ""
        clicavel = widget_class in {"Button", "TButton", "CTkButton"}
        has_command = False
        texto = ""
        if hasattr(widget, "cget"):
            try:
                texto = widget.cget("text")
                has_command = bool(widget.cget("command"))
            except: pass
        if not (clicavel or has_command): return
        acao = "Clique"
        detalhe = f"{widget_class}"
        if texto: detalhe = f"{widget_class} | {texto}"
        texto_upper = (texto or "").strip().upper()
        if any(p in texto_upper for p in ("SALVAR","GRAVAR","CADASTRAR","ATUALIZAR")):
            acao = "Salvou"
        elif any(p in texto_upper for p in ("EXCLUIR","APAGAR","REMOVER","DELETAR")):
            acao = "Apagou"
        elif any(p in texto_upper for p in ("EDITAR","ALTERAR")):
            acao = "Editou"
        if self._should_log_event(f"click:{detalhe}"):
            self._log_user_activity(acao, detalhe)

    def _on_treeview_select(self, event):
        if not ACTIVITY_LOGGING_ENABLED: return
        widget = event.widget
        if not widget: return
        try:
            selection = widget.selection()
            if not selection: return
            item_id = selection[0]
            valores = widget.item(item_id, "values")
            resumo = ", ".join(str(v) for v in valores[:3]) if valores else str(item_id)
        except: return
        detalhe = f"Treeview | {resumo}"
        if self._should_log_event(f"tree:{detalhe}", 0.8):
            self._log_user_activity("Selecionou item", detalhe)

    def _on_combobox_select(self, event):
        if not ACTIVITY_LOGGING_ENABLED: return
        widget = event.widget
        if not widget: return
        try: valor = widget.get()
        except: return
        detalhe = f"Combobox | {valor}"
        if self._should_log_event(f"combo:{detalhe}"):
            self._log_user_activity("Selecionou opção", detalhe)

    def _on_user_key(self, event):
        if not ACTIVITY_LOGGING_ENABLED: return
        keysym = event.keysym or ""
        if keysym in {"Shift_L","Shift_R","Control_L","Control_R","Alt_L","Alt_R"}: return
        is_shortcut = bool(event.state & 0x4)
        is_action_key = keysym in {"Return","F5","F11","Escape"}
        if not (is_shortcut or is_action_key): return
        detalhe = f"Tecla | {keysym}"
        if self._should_log_event(f"key:{detalhe}", 0.6):
            self._log_user_activity("Atalho", detalhe)

    # ===== TEMA =====
    def _load_initial_theme(self):
        tema, paleta = self.user_manager.load_user_theme_completo()
        if not tema:
            tema = self.settings.get("theme", "CLÁSSICO CLARO")
        self.current_theme_name = tema
        self.theme_manager.apply_theme(tema, paleta, rebuild_interface=False)

    def _load_icons_static(self):
        size = (24,24)
        if self._shared_icons_cache and self._current_icon_size == size:
            self.icons_cache = self._shared_icons_cache
            return
        new_cache = {}
        for cat, fname in self.ICON_MAPPING.items():
            path = os.path.join(ICONS_DIR, fname)
            if os.path.exists(path):
                try:
                    img = Image.open(path)
                    new_cache[cat] = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                except: pass
        self._shared_icons_cache = new_cache
        self._current_icon_size = size
        self.icons_cache = new_cache

    def _get_submenu_icon(self, categoria, item):
        key = f"{categoria}_{item}"
        if key in self.icons_cache:
            return self.icons_cache[key]
        fname = self.SUBMENU_ICON_MAPPING.get(categoria, {}).get(item, "")
        if fname:
            path = os.path.join(ICONS_DIR, fname)
            if os.path.exists(path):
                try:
                    img = Image.open(path)
                    icon = ctk.CTkImage(light_image=img, dark_image=img, size=(20,20))
                    self.icons_cache[key] = icon
                    return icon
                except: pass
        return None

    def _update_menu_buttons_colors(self):
        if not hasattr(self, 'botoes_menu'): return
        pal = self.theme_manager.current_palette or {}
        fg_normal = pal.get("secundaria", "#1F2937")
        fg_hover = pal.get("hover", "#374151")
        txt_normal = pal.get("texto", "#FFFFFF")
        txt_hover = txt_normal
        for cat, btn_frame in self.botoes_menu.items():
            if not btn_frame.winfo_exists(): continue
            for child in btn_frame.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    ativo = (cat == self._active_submenu)
                    child.configure(fg_color=fg_hover if ativo else fg_normal,
                                    text_color=txt_hover if ativo else txt_normal,
                                    hover_color=fg_hover)
        for sub in self.submenu_frames.values():
            if sub.winfo_exists():
                sub.configure(fg_color=pal.get("secundaria", "#1F2937"))
                for inner in sub.winfo_children():
                    for btn in inner.winfo_children():
                        if isinstance(btn, ctk.CTkButton):
                            btn.configure(fg_color=pal.get("terciaria", "#3E3E3E"), text_color=txt_normal, hover_color=fg_hover)

    # ===== CONSTRUÇÃO DA INTERFACE =====
    def _build_interface(self):
        self.grid_columnconfigure(0, weight=0, minsize=self.SIDEBAR_WIDTH+16)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.configure(fg_color=self.cor_fundo)
        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=self.SIDEBAR_WIDTH, corner_radius=14, fg_color=self.cor_primaria, border_width=2, border_color=self.cor_borda)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.sidebar.grid_propagate(False)
        titulo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        titulo_frame.pack(pady=(20,10))
        if os.path.exists(ICONE_SISTEMA):
            try:
                img = Image.open(ICONE_SISTEMA)
                icon = ctk.CTkImage(light_image=img, dark_image=img, size=(self.icon_size_sidebar, self.icon_size_sidebar))
                ctk.CTkLabel(titulo_frame, image=icon, text="").pack(side="left", padx=(0,10))
            except: pass
        self.sidebar_title_label = ctk.CTkLabel(titulo_frame, text=self._get_text("system_title"), font=self.font_sidebar_titulo, text_color=self.cor_texto)
        self.sidebar_title_label.pack(side="left")
        self.sidebar_subtitle_label = ctk.CTkLabel(self.sidebar, text=self._get_text("main_menu"), font=self.font_sidebar_subtitulo, text_color=self.cor_texto)
        self.sidebar_subtitle_label.pack(pady=(0,40))
        self.menu_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.menu_frame.pack(fill="both", expand=True, padx=10, pady=(4,8))
        self._build_menu_content()

    def _build_menu_content(self):
        for w in self.menu_frame.winfo_children():
            w.destroy()
        for f in list(self.submenu_frames.values()):
            try: f.destroy()
            except: pass
        self.submenu_frames.clear()
        self.botoes_menu.clear()
        for i, cat in enumerate(self.MENU_ESTRUTURA.keys()):
            self._create_menu_button(cat, i)

    def _create_menu_button(self, categoria, pos):
        btn_frame = ctk.CTkFrame(self.menu_frame, fg_color="transparent", width=self.SIDEBAR_WIDTH-20, height=self.ITEM_HEIGHT)
        btn_frame.pack(fill="x", padx=(10,10), pady=max(1, int(2*self.ui_scale)))
        btn_frame.pack_propagate(False)
        icon = self.icons_cache.get(categoria)
        pal = self.theme_manager.current_palette or {}
        fg = pal.get("secundaria", "#1F2937")
        txt = pal.get("texto", "#FFFFFF")
        btn = ctk.CTkButton(btn_frame, text=f"  {self._translate_menu_label(categoria)}", image=icon, compound="left", anchor="w",
                            fg_color=fg, hover_color=pal.get("hover","#374151"), text_color=txt,
                            font=("Arial", max(11, int(14*self.ui_scale))), corner_radius=max(8, int(10*self.ui_scale)),
                            border_width=1, border_color=self.cor_borda,
                            command=lambda c=categoria: self._on_category_click(c))
        btn._opera_menu_button = True
        btn.pack(fill="both", expand=True, padx=max(2, int(4*self.ui_scale)))
        self.botoes_menu[categoria] = btn_frame
        self._create_submenu(categoria)
        if categoria != "Dashboard":
            def on_enter(e, cat=categoria): self._show_submenu(cat)
            def on_leave(e): self._schedule_submenu_hide()
            btn_frame.bind("<Enter>", on_enter, add="+")
            btn_frame.bind("<Leave>", on_leave, add="+")
            btn.bind("<Enter>", on_enter, add="+")
            btn.bind("<Leave>", on_leave, add="+")

    def _create_submenu(self, categoria):
        itens = self.MENU_ESTRUTURA.get(categoria, [])
        if self.user_manager._permissions_loaded.is_set():
            itens = [i for i in itens if self.user_manager.has_permission(i, "ver", categoria)]
        if not itens:
            return
        pal = self.theme_manager.current_palette or {}
        sub = ctk.CTkFrame(self, fg_color=pal.get("secundaria","#1F2937"), corner_radius=10, border_width=1, border_color=self.cor_borda)
        inner = ctk.CTkFrame(sub, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=4, pady=6)
        for item in itens:
            self._create_submenu_item(inner, categoria, item)
        sub.bind("<Enter>", lambda e: self._cancel_submenu_hide_timer())
        sub.bind("<Leave>", lambda e: self._schedule_submenu_hide())
        inner.bind("<Enter>", lambda e: self._cancel_submenu_hide_timer())
        inner.bind("<Leave>", lambda e: self._schedule_submenu_hide())
        self.submenu_frames[categoria] = sub

    def _create_submenu_item(self, parent, categoria, item):
        item_frame = ctk.CTkFrame(parent, fg_color="transparent")
        item_frame.pack(fill="x", padx=2, pady=1)
        icon = self._get_submenu_icon(categoria, item)
        pal = self.theme_manager.current_palette or {}
        btn = ctk.CTkButton(item_frame, text=f"  {self._translate_menu_label(item)}", image=icon, compound="left", anchor="w",
                            fg_color=pal.get("terciaria","#3E3E3E"), hover_color=pal.get("hover","#374151"),
                            text_color=pal.get("texto","#FFFFFF"), font=("Arial", max(11, int(13*self.ui_scale))),
                            height=max(32, int(36*self.ui_scale)), corner_radius=6, border_width=0,
                            command=lambda i=item: self._on_submenu_click(categoria, i))
        btn._opera_submenu_button = True
        btn.pack(fill="x", expand=True, padx=4, pady=2)

    def _show_submenu(self, categoria):
        self._cancel_submenu_hide_timer()
        frame = self.submenu_frames.get(categoria)
        btn_frame = self.botoes_menu.get(categoria)
        if not frame or not btn_frame: return
        self.update_idletasks()
        for nome, f in self.submenu_frames.items():
            if nome != categoria:
                try: f.place_forget()
                except: pass
        self._active_submenu = categoria
        self._update_menu_buttons_colors()
        root_x, root_y = self.winfo_rootx(), self.winfo_rooty()
        btn_x = btn_frame.winfo_rootx() - root_x
        btn_y = btn_frame.winfo_rooty() - root_y
        btn_w, btn_h = btn_frame.winfo_width(), btn_frame.winfo_height()
        frame.update_idletasks()
        fw, fh = frame.winfo_width(), frame.winfo_reqheight()
        x = btn_x + btn_w + 4
        y = btn_y
        if x + fw > self.winfo_width() - 10:
            x = btn_x - fw - 4
        if x < 10: x = 10
        if y + fh > self.winfo_height() - 10:
            y = self.winfo_height() - fh - 10
        if y < 10: y = 10
        frame.place(in_=self, x=x, y=y)
        frame.lift()

    def _cancel_submenu_hide_timer(self):
        if self._submenu_timer:
            try: self.after_cancel(self._submenu_timer)
            except: pass
            self._submenu_timer = None

    def _schedule_submenu_hide(self, delay=300):
        self._cancel_submenu_hide_timer()
        def hide():
            self._submenu_timer = None
            x, y = self.winfo_pointerx(), self.winfo_pointery()
            w = self.winfo_containing(x, y)
            while w:
                if getattr(w, '_opera_menu_button', False) or getattr(w, '_opera_submenu_button', False):
                    return
                if w in self.submenu_frames.values() or w in self.botoes_menu.values():
                    return
                w = getattr(w, 'master', None)
            self._hide_all_submenus()
        self._submenu_timer = self.after(delay, hide)

    def _hide_all_submenus(self):
        self._cancel_submenu_hide_timer()
        for f in self.submenu_frames.values():
            try: f.place_forget()
            except: pass
        self._active_submenu = None
        self._update_menu_buttons_colors()

    def _on_category_click(self, categoria):
        if categoria == "Dashboard":
            self._hide_all_submenus()
            self.open_page("Dashboard")
        else:
            if self._active_submenu == categoria:
                self._hide_all_submenus()
            else:
                self._hide_all_submenus()
                self._show_submenu(categoria)

    def _on_submenu_click(self, categoria, item):
        self._hide_all_submenus()
        self.open_page(item, categoria)

    def _build_main_area(self):
        self.main = ctk.CTkFrame(self, corner_radius=14, fg_color=self.cor_fundo, border_width=2, border_color=self.cor_borda)
        self.main.grid(row=0, column=1, sticky="nsew", padx=(0,8), pady=8)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)
        self._build_topbar()
        self.content_shell = ctk.CTkFrame(self.main, fg_color=self.cor_fundo, corner_radius=10, border_width=1, border_color=self.cor_borda)
        self.content_shell.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        self.content_shell.grid_columnconfigure(0, weight=1)
        self.content_shell.grid_rowconfigure(0, weight=1)
        self.content = ctk.CTkFrame(self.content_shell, fg_color=self.cor_fundo)
        self.content.grid(row=0, column=0, sticky="nsew")

    def _build_topbar(self):
        self.topbar = ctk.CTkFrame(self.main, fg_color=self.cor_primaria, corner_radius=12, border_width=1, border_color=self.cor_borda, height=self.TOPBAR_HEIGHT)
        self.topbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8,4))
        self.topbar.grid_propagate(False)
        self.topbar.grid_columnconfigure(0, weight=1)
        self.title_label = ctk.CTkLabel(self.topbar, text=self._translate_page_name("Dashboard"), font=self.font_topbar_titulo, text_color=self.cor_texto)
        self.title_label.grid(row=0, column=0, sticky="w", padx=15, pady=4)
        self._build_utility_buttons()
        self._add_language_selector_to_topbar()
        self._add_theme_switch_to_topbar()
        self._build_user_widget()

    def _build_utility_buttons(self):
        btn_frame = ctk.CTkFrame(self.topbar, fg_color=self.cor_primaria, height=34)
        btn_frame.grid(row=0, column=1, sticky="e", padx=10, pady=10)
        btn_frame.grid_propagate(False)
        refresh_icon = None
        for nome in ["ATUALIZAR.png","REFRESH.png","RELOAD.png","ATUALIZAR_PAGINA.png"]:
            p = os.path.join(ICONS_DIR, nome)
            if os.path.exists(p):
                try:
                    img = Image.open(p).convert("RGBA")
                    refresh_icon = ctk.CTkImage(light_image=img, dark_image=img, size=(22,22))
                    break
                except: pass
        if refresh_icon:
            lbl = ctk.CTkLabel(btn_frame, text="", image=refresh_icon, fg_color="transparent")
        else:
            lbl = ctk.CTkLabel(btn_frame, text="↻", font=("Segoe UI",22,"bold"), text_color=self.cor_texto)
        lbl.pack(side="left", padx=16)
        lbl.bind("<Button-1>", lambda e: self.reload_current_page())
        # Trocar usuário
        switch_icon = None
        try:
            p = os.path.join(ICONS_DIR, "TROCAR_USUARIO.png")
            if os.path.exists(p):
                img = Image.open(p).convert("RGBA")
                switch_icon = ctk.CTkImage(light_image=img, dark_image=img, size=(22,22))
        except: pass
        if switch_icon:
            lbl_sw = ctk.CTkLabel(btn_frame, text="", image=switch_icon, fg_color="transparent")
        else:
            lbl_sw = ctk.CTkLabel(btn_frame, text="👤", font=("Segoe UI",20,"bold"), text_color=self.cor_texto)
        lbl_sw.pack(side="left", padx=10)
        lbl_sw.bind("<Button-1>", lambda e: self.trocar_usuario())

    def _add_language_selector_to_topbar(self):
        frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        frame.grid(row=0, column=2, padx=(0,12), sticky="e")
        ctk.CTkLabel(frame, text=f"🌐 {self._get_text('language')}", font=("Arial",12,"bold"), text_color=self.cor_texto).pack(side="left", padx=(0,8))
        self.language_status_label = ctk.CTkLabel(frame, text=self._get_language_display_name(), font=("Arial",11), text_color=self.cor_texto)
        self.language_status_label.pack(side="left", padx=(0,8))
        self.language_var = ctk.StringVar(value=self._get_language_display_name())
        self.language_menu = ctk.CTkOptionMenu(frame, variable=self.language_var, values=list(self.SUPPORTED_LANGUAGES.values()),
                                               width=170, command=self._change_language,
                                               fg_color=self.cor_secundaria, button_color=self.cor_primaria,
                                               text_color=self.cor_texto)
        self.language_menu.pack(side="left")

    def _add_theme_switch_to_topbar(self):
        frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        frame.grid(row=0, column=3, padx=18, sticky="e")
        is_dark = self._theme_mode_from_name(self.current_theme_name) == "dark"
        self.icon_theme = ctk.CTkLabel(frame, text="🌙" if is_dark else "☀️", font=self.font_topbar_icone)
        self.icon_theme.pack(side="left", padx=(0,10))
        self.theme_switch = ctk.CTkSwitch(frame, text="", width=52, height=26, command=self._toggle_theme_mode)
        if is_dark:
            self.theme_switch.deselect()
        else:
            self.theme_switch.select()
        self.theme_switch.pack(side="left")

    def _theme_mode_from_name(self, tema_nome):
        return "dark" if tema_nome and tema_nome.upper() in {"NOTURNO","PRETO E OURO","NOITE URBANA"} else "light"

    def _toggle_theme_mode(self):
        is_dark = (self.theme_switch.get() == 0)
        tema = "Preto e Ouro" if is_dark else "CLÁSSICO CLARO"
        from PAGINAS_DO_SISTEMA.TEMAS import aplicar_tema_atalho
        aplicar_tema_atalho(self, tema)
        self.icon_theme.configure(text="🌙" if is_dark else "☀️")
        self._update_menu_buttons_colors()
        if self._current_frame and self._current_frame.winfo_exists():
            self.theme_manager.apply_theme_to_widget(self._current_frame)

    def _build_user_widget(self):
        user_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        user_frame.grid(row=0, column=4, padx=18, sticky="e")
        self.user_info_label = ctk.CTkLabel(user_frame, text=self._get_text("loading"), font=("Arial",14), text_color=self.cor_texto)
        self.user_info_label.pack(side="right")
        self._update_user_display()

    def _update_user_display(self):
        self._update_user_info_once()
        self._tick_clock()

    def _update_user_info_once(self):
        now = datetime.now().strftime(self._get_text("clock_format"))
        admin = (self.usuario_hierarquia and self.usuario_hierarquia.lower() in ("admin","administrador"))
        prefix = "👑 " if admin else "👤 "
        self.user_info_label.configure(text=f"{now} | {prefix}{self.usuario_nome} • {self.usuario_hierarquia}")

    def _tick_clock(self):
        if not self.winfo_exists(): return
        self._update_user_info_once()
        self.after(1000, self._tick_clock)

    # ===== TRADUÇÃO COMPLETA (COM RECURSÃO OTIMIZADA) =====
    def _get_text(self, key, **kwargs):
        base = self.UI_TEXTS.get(self.idioma_atual, self.UI_TEXTS["pt_BR"])
        txt = base.get(key, self.UI_TEXTS["pt_BR"].get(key, key))
        try: return txt.format(**kwargs)
        except: return txt

    def _get_language_display_name(self):
        return self.SUPPORTED_LANGUAGES.get(self.idioma_atual, self.SUPPORTED_LANGUAGES["pt_BR"])

    def _translate_menu_label(self, text):
        m = self.MENU_LABELS.get(text, {})
        return m.get(self.idioma_atual, m.get("pt_BR", text))

    def _translate_page_name(self, page_name):
        if page_name == "Dashboard": return self._get_text("topbar_dashboard")
        return self._translate_menu_label(page_name)

    def _refresh_frame_language(self, frame):
        """Atualiza idioma de um frame e todos os seus widgets (recursão controlada)."""
        if not frame or not getattr(frame, "winfo_exists", lambda: False)():
            return
        # Tenta método específico da página primeiro
        if hasattr(frame, "refresh_i18n"):
            frame.refresh_i18n(self.idioma_atual)
        elif hasattr(frame, "set_idioma"):
            frame.set_idioma(self.idioma_atual)
        elif hasattr(frame, "on_language_changed"):
            frame.on_language_changed(self.idioma_atual)
        # Atualiza recursivamente todos os widgets filhos (mas sem excessos)
        def _apply_to_widget(w):
            try:
                # Atualiza textos comuns
                for opt in ("text", "placeholder_text"):
                    try:
                        atual = w.cget(opt)
                        if isinstance(atual, str) and atual.strip():
                            # Tenta traduzir se houver chave correspondente
                            trad = self._translate_menu_label(atual)
                            if trad != atual:
                                w.configure(**{opt: trad})
                    except: pass
                # Combobox/OptionMenu
                if isinstance(w, (ttk.Combobox, ctk.CTkComboBox, ctk.CTkOptionMenu)):
                    try:
                        vals = w.cget("values")
                        if isinstance(vals, (list, tuple)):
                            novos = [self._translate_menu_label(v) for v in vals]
                            if novos != list(vals):
                                w.configure(values=novos)
                    except: pass
                # Treeview headings
                if isinstance(w, ttk.Treeview):
                    try:
                        heading0 = w.heading("#0").get("text", "")
                        novo0 = self._translate_menu_label(heading0)
                        if novo0 != heading0:
                            w.heading("#0", text=novo0)
                        for col in w["columns"]:
                            atual = w.heading(col).get("text", "")
                            novo = self._translate_menu_label(atual)
                            if novo != atual:
                                w.heading(col, text=novo)
                    except: pass
                # Passa para filhos
                for child in w.winfo_children():
                    _apply_to_widget(child)
            except: pass
        _apply_to_widget(frame)

    def _change_language(self, selected):
        novo = None
        for code, name in self.SUPPORTED_LANGUAGES.items():
            if name == selected:
                novo = code
                break
        if not novo or novo == self.idioma_atual: return
        self.idioma_atual = novo
        self.settings["language"] = novo
        ConfigManager.save_settings(self.settings)
        # Atualiza elementos da interface principal
        self.sidebar_title_label.configure(text=self._get_text("system_title"))
        self.sidebar_subtitle_label.configure(text=self._get_text("main_menu"))
        self.language_status_label.configure(text=self._get_language_display_name())
        self.language_var.set(self._get_language_display_name())
        self.title_label.configure(text=self._translate_page_name(self.current_page or "Dashboard"))
        # Recria menus (para itens do menu principal e submenus)
        self._build_menu_content()
        self._update_menu_buttons_colors()
        # Atualiza idioma da página atual (recursivamente) e de todas as páginas em cache
        if self._current_frame and self._current_frame.winfo_exists():
            self._refresh_frame_language(self._current_frame)
        for frame in self._page_cache.values():
            if frame is not self._current_frame:
                self._refresh_frame_language(frame)
        # Marca cache como não aplicado tema (opcional)
        for frame in self._page_cache.values():
            frame._theme_applied = False
        _dprint(f"Idioma alterado para {novo}")

    # ===== CARREGAMENTO DE PÁGINAS (LAZY + CACHE) =====
    def open_page(self, page_name, categoria=None):
        if self._page_loading or self._closing: return
        if not self.user_manager._permissions_loaded.is_set():
            self.after(50, lambda: self.open_page(page_name, categoria))
            return
        if not self.user_manager.has_permission(page_name, "ver", categoria):
            self._show_temporary_message(self._get_text("no_permission", page=self._translate_page_name(page_name)))
            return
        self._page_loading = True
        try:
            if self._current_frame and self._current_frame.winfo_exists():
                self._current_frame.place_forget()
            frame = self._page_cache.get(page_name)
            if frame is None:
                frame = self._load_page_direct(page_name)
                self._cache_page(page_name, frame)
            if frame:
                if not getattr(frame, '_theme_applied', False):
                    self.theme_manager.apply_theme_to_widget(frame)
                frame.place(x=0, y=0, relwidth=1, relheight=1)
                self.title_label.configure(text=self._translate_page_name(page_name))
                if hasattr(frame, "on_page_open"):
                    frame.on_page_open()
                self.current_page = page_name
                self._current_frame = frame
                self.settings["last_page"] = page_name
                ConfigManager.save_settings(self.settings)
                # Garante idioma correto na página recém-carregada
                self._refresh_frame_language(frame)
                _dprint(f"✅ Página '{page_name}' carregada")
        except Exception as e:
            messagebox.showerror(self._get_text("error"), f"Falha ao abrir {page_name}:\n{e}", parent=self)
        finally:
            self._page_loading = False

    def _load_page_direct(self, page_name):
        route = self.routes.get(page_name)
        if not route:
            raise ValueError(f"Rota não encontrada: {page_name}")
        file_path = os.path.join(APP_DIR, route["file"])
        if not os.path.exists(file_path):
            file_path = os.path.join(ROOT_DIR, route["file"])
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        module_key = f"opera_page_{module_name}"
        sys.path.insert(0, APP_DIR)
        sys.path.insert(0, ROOT_DIR)
        try:
            if module_key in sys.modules:
                module = sys.modules[module_key]
            else:
                spec = importlib.util.spec_from_file_location(module_key, file_path)
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
                if issubclass(obj, ctk.CTkFrame) and obj.__module__ == module.__name__:
                    page_class = obj
                    break
        if not page_class:
            raise RuntimeError(f"Classe não encontrada em {file_path}")
        for args in [{"master":self.content, "sistema":self}, {"master":self.content, "app":self}, {"master":self.content, "host":self},
                     {"parent":self.content, "sistema":self}, {"parent":self.content, "app":self}, {"parent":self.content, "host":self},
                     {"master":self.content}, {"parent":self.content}]:
            try:
                return page_class(**args)
            except:
                continue
        raise RuntimeError(f"Não foi possível instanciar {page_name}")

    def _cache_page(self, page_name, frame):
        self._page_cache[page_name] = frame
        if page_name in self._page_cache_order:
            self._page_cache_order.remove(page_name)
        self._page_cache_order.append(page_name)
        while len(self._page_cache_order) > self._page_cache_size:
            old = self._page_cache_order.pop(0)
            old_frame = self._page_cache.pop(old, None)
            if old_frame:
                try: old_frame.destroy()
                except: pass

    def reload_current_page(self):
        if self.current_page:
            self.open_page(self.current_page)

    def _show_temporary_message(self, message, duration=3000):
        for w in self.content.winfo_children():
            w.destroy()
        msg_frame = ctk.CTkFrame(self.content, fg_color=self.cor_secundaria, corner_radius=12)
        msg_frame.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(msg_frame, text=message, font=("Arial",14), text_color=self.cor_texto, wraplength=400).pack(padx=30, pady=30)
        self.after(duration, lambda: self.open_page("Dashboard") if self.user_manager.has_permission("Dashboard","ver") else None)

    def _on_permissions_loaded(self):
        self._build_menu_content()
        self._update_menu_buttons_colors()

    # ===== INICIALIZAÇÃO LEVE =====
    def _startup_tasks(self):
        self._open_initial_page()
        self._apply_theme_to_current_frame()
        self._update_user_display()
        self._smart_preload_last_page()

    def _open_initial_page(self):
        if self.user_manager.has_permission("Dashboard", "ver"):
            self.open_page("Dashboard")
        else:
            for p in self.routes.keys():
                if self.user_manager.has_permission(p, "ver"):
                    self.open_page(p)
                    break

    def _apply_theme_to_current_frame(self):
        if self._current_frame and self._current_frame.winfo_exists():
            self.theme_manager.apply_theme_to_widget(self._current_frame)

    def _smart_preload_last_page(self):
        if self.settings.get("preload_last_page", True):
            last = self.settings.get("last_page")
            if last and last != self.current_page and last not in self._page_cache:
                try:
                    frame = self._load_page_direct(last)
                    self._cache_page(last, frame)
                    frame.place_forget()
                except: pass

    def trocar_usuario(self):
        try:
            modulo = importlib.import_module("PAGINAS_DO_SISTEMA.TROCAR_USUARIOS")
            modulo.abrir_janela_trocar_usuario(self)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao abrir tela de login:\n{e}", parent=self)

# ===== MAIN =====
def main():
    try:
        app = OperaMenuApp()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Erro Fatal", f"Erro ao iniciar o sistema:\n{e}")

if __name__ == "__main__":
    main()