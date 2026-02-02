import threading
from tkinter import Toplevel
import customtkinter as ctk
from TEMAS import get_contraste_texto, is_dark_color, ajustar_hover
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import csv

# ===================== Acesso ao PostgreSQL =====================
try:
    # módulo que lê config.json e expõe get_conn/get_schema/require_ready
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception as e:
    # Fallbacks simples só para evitar crash se o módulo ainda não estiver pronto
    def get_conn():
        raise RuntimeError(f"Módulo BANCO_DE_DADOS_PG indisponível: {e}")


    def get_schema():
        return "public"


    def require_ready(essentials=None):
        return False, "Módulo de banco de dados não disponível"

# ===================== Aparência base / tema =====================
ctk.set_appearance_mode("System")

SERVICE_FILTER_OPTIONS = [
    "Todos", "Facção", "Bordado", "Caseador", "Botões",
    "Estamparia", "Tingimento", "Outros Trabalhos"
]
SERVICE_OPTIONS = [
    "Facção", "Bordado", "Caseador", "Botões",
    "Estamparia", "Tingimento", "Outros Trabalhos"
]
ORIGEM_OPTIONS = ["Cortes a Pagar", "Cortes Pagos"]  # rótulos da interface


# ===================== Helpers de banco (PG) =====================
# ===================== Helpers de banco (PG) =====================
def _with_search_path(cur):
    """Garante que estamos usando o schema configurado."""
    try:
        cur.execute(f"SET LOCAL search_path = {get_schema()};")
    except Exception:
        pass

def _select_all(sql: str, params=()):
    """Executa SELECT e retorna todas as linhas."""
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        _with_search_path(cur)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def _select_one(sql: str, params=()):
    """Executa SELECT e retorna uma linha."""
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        _with_search_path(cur)
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

def _exec(sql: str, params=()):
    """Executa uma query (INSERT/UPDATE/DELETE)."""
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        _with_search_path(cur)
        cur.execute(sql, params)
        conn.commit()
        return True
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        raise e
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

# Nova função para gerenciar transações manuais
def _get_connection():
    """Obtém uma conexão para transações manuais."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        _with_search_path(cur)
        cur.close()
        return conn
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        raise e


def _select_all(sql: str, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        _with_search_path(cur)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _select_one(sql: str, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        _with_search_path(cur)
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _exec(sql: str, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        _with_search_path(cur)
        cur.execute(sql, params)
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _columns_of(table: str):
    """Retorna conjunto de colunas existentes numa tabela (no schema atual)."""
    rows = _select_all("""
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = %s
    """, (table,))
    return {r[0] for r in rows}



def _column_type(table: str, column: str):
    """Retorna (data_type, udt_name) para uma coluna (ou (None,None) se não existir)."""
    row = _select_one("""
        SELECT data_type, udt_name
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = %s
           AND column_name = %s
    """, (table, column))
    if not row:
        return None, None
    return row[0], row[1]


def _table_exists(table: str) -> bool:
    row = _select_one("""
        SELECT EXISTS(
          SELECT 1
            FROM information_schema.tables
           WHERE table_schema = current_schema()
             AND table_name = %s
        )
    """, (table,))
    return bool(row and row[0])


# ===================== UI principal =====================
class PagamentoModernUI(ctk.CTkFrame):
    def __init__(self, parent, host=None, sistema=None, *args, **kwargs):
        """
        parent  -> container (no menu é self.content, em teste direto é root)
        host    -> janela/menu que tem as cores (cor_fundo, cor_primaria, etc.)
        sistema -> instância principal do sistema (MENU_PRINCIPAL), se for passado

        Obs.: host e sistema são equivalentes para tema; sempre teremos self.sistema.
        """
        # unifica host/sistema
        self._host = host or sistema
        self.sistema = sistema or host

        # tenta descobrir um "host" automaticamente se nada veio
        if self._host is None:
            cand = None
            try:
                # o próprio parent pode ter as cores
                if hasattr(parent, 'cor_fundo') or hasattr(parent, 'cor_primaria'):
                    cand = parent
                # ou o master do parent
                elif hasattr(parent, 'master') and (
                        hasattr(parent.master, 'cor_fundo') or hasattr(parent.master, 'cor_primaria')
                ):
                    cand = parent.master
                # ou o toplevel (janela principal)
                elif hasattr(parent, 'winfo_toplevel'):
                    top = parent.winfo_toplevel()
                    if hasattr(top, 'cor_fundo') or hasattr(top, 'cor_primaria'):
                        cand = top
            except Exception:
                cand = None

            if cand is not None:
                self._host = cand
                if self.sistema is None:
                    self.sistema = cand

        # agora _host pode ser None, mas isso é tratado em _update_theme_from_host
        self._update_theme_from_host()

        # cria o frame já com a cor de fundo calculada
        super().__init__(parent, fg_color=self.main_bg, *args, **kwargs)

        # aplica tema ttk (Treeview, etc.)
        self._apply_ttk_theme()

        # ---------- ESTADO / VARIÁVEIS ----------
        self.valor_por_peca = 0.0
        self.quantidade_finalizada = 0
        self.current_mapping = {}
        self._adiantamento_faccao_record = None  # {id, valor_restante, forma_pagamento, parcelas}
        self._adiantamento_original = 0.0

        # variáveis de filtro
        self.filter_servico_var = tk.StringVar(value="Todos")
        self.tipo_servico_var = tk.StringVar(value="Facção")
        self.source_var = tk.StringVar(value="Finalizados")

        # validações mínimas do banco
        ok, msg = require_ready()

        if not ok:
            messagebox.showwarning(
                "Aviso",
                f"Banco de dados não está pronto:\n{msg}\nAlgumas funções podem falhar."
            )

        # monta a interface
        self._build_ui()

        # conecta sinal para atualizar tema quando o sistema trocar de tema
        self._conectar_sinal_tema()
        self._sync_theme()

        # carrega dados iniciais
        self.pesquisar_finalizados()

    # ===================== Tema / estilo =====================
    def obter_cores_por_tema(self):
        """Define cores de texto dinamicamente baseado no tema atual - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        tema_atual = ctk.get_appearance_mode()

        if tema_atual == "Dark":
            self.cor_fundo = getattr(self.sistema, "cor_fundo", "#020617")
            self.cor_primaria = getattr(self.sistema, "cor_primaria", "#1f2937")
            self.cor_secundaria = getattr(self.sistema, "cor_secundaria", "#111827")
            self.cor_texto = getattr(self.sistema, "cor_texto", "#e5e7eb")
            self.cor_texto_entry = "#e5e7eb"
            self.cor_placeholder = "#888888"
            self.cor_borda = getattr(self.sistema, "cor_borda", "#273244")
            self.cor_hover = getattr(self.sistema, "cor_hover", "#334155")
            self.cor_adicionar = getattr(self.sistema, "cor_adicionar", "#3a7ebf")
            self.cor_imprimir = getattr(self.sistema, "cor_imprimir", "#3a7ebf")
            self.cor_sucesso = getattr(self.sistema, "cor_sucesso", "#22c55e")
        else:
            self.cor_fundo = "#ffffff"
            self.cor_primaria = "#3a7ebf"
            self.cor_secundaria = "#f0f0f0"
            self.cor_texto = "black"
            self.cor_texto_entry = "black"
            self.cor_placeholder = "#666666"
            self.cor_borda = "#cccccc"
            self.cor_hover = "#2e4a66"
            self.cor_adicionar = "#3a7ebf"
            self.cor_imprimir = "#3a7ebf"
            self.cor_sucesso = "#22c55e"

    def _update_theme_from_host(self):
        """Atualiza as cores baseado no host/sistema - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        self.obter_cores_por_tema()
        self.main_bg = self.cor_fundo
        self.topbar_bg = self.cor_primaria
        self.filter_bg = self.cor_secundaria
        self.card_bg = self.cor_secundaria
        self.accent_color = self.cor_primaria


    def configurar_treeview_theme(self):
        """Configura a Treeview com contraste alto (linhas + cabeçalho), independente do tema."""
        self.style = ttk.Style()
        try:
            self.style.theme_use('default')
        except Exception:
            pass

        tema_atual = ctk.get_appearance_mode()

        if tema_atual == "Dark":
            bg_even = self.cor_fundo
            bg_odd = self.cor_secundaria
            fg = get_contraste_texto(bg_even)
            field_bg = self.cor_fundo
            sel_bg = self.cor_primaria
            head_bg = self.cor_primaria
            head_fg = get_contraste_texto(head_bg)
        else:
            bg_even = "#ffffff"
            bg_odd = "#f3f4f6"
            fg = "#111111"
            field_bg = "#ffffff"
            sel_bg = self.cor_primaria
            head_bg = self.cor_primaria
            head_fg = get_contraste_texto(head_bg)

        # salva para usar nas tags (odd/even)
        self._tree_colors = {
            "even": bg_even,
            "odd": bg_odd,
            "fg": fg,
            "sel_bg": sel_bg,
            "sel_fg": get_contraste_texto(sel_bg),
            "head_bg": head_bg,
            "head_fg": head_fg,
        }

        self.style.configure(
            "Custom.Treeview",
            background=bg_even,
            foreground=fg,
            fieldbackground=field_bg,
            borderwidth=0,
            highlightthickness=0,
            rowheight=26,
            font=('Arial', 10)
        )

        self.style.configure(
            "Custom.Treeview.Heading",
            background=head_bg,
            foreground=head_fg,
            relief="flat",
            borderwidth=1,
            font=('Arial', 10, 'bold')
        )

        self.style.map(
            'Custom.Treeview',
            background=[('selected', sel_bg)],
            foreground=[('selected', get_contraste_texto(sel_bg))]
        )

    def _apply_ttk_theme(self):
        """Aplica o tema ttk - MESMO ESTILO DO CADASTRO_DE_CORTE"""
        try:
            self.configurar_treeview_theme()

            # Configurar estilo para outros widgets ttk
            style = ttk.Style()
            style.configure("Vertical.TScrollbar",
                            background=self.cor_secundaria,
                            troughcolor=self.cor_fundo,
                            bordercolor=self.cor_borda)

            style.configure("TCombobox",
                            fieldbackground=self.cor_secundaria,
                            background=self.cor_secundaria,
                            foreground=self.cor_texto)
            style.map("TCombobox",
                      fieldbackground=[("readonly", self.cor_secundaria)],
                      foreground=[("readonly", self.cor_texto)])
        except Exception:
            pass

    def _conectar_sinal_tema(self) -> None:
        try:
            if getattr(self, "_tema_binding_registrado", False):
                return
            toplevel = self.winfo_toplevel()
            if toplevel:
                toplevel.bind("<<TemaAtualizado>>", lambda e: self._sync_theme(), add="+")
                self._tema_binding_registrado = True
        except Exception:
            pass

    def _all_children(self, parent):
        for w in parent.winfo_children():
            yield w
            try:
                yield from self._all_children(w)
            except Exception:
                pass

    def _sync_theme(self) -> None:
        """Sincroniza o tema - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        import customtkinter as ctk
        try:
            self._update_theme_from_host()
        except Exception:
            pass

        try:
            self.configure(fg_color=self.main_bg)
        except Exception:
            pass

        # Atualizar cores de todos os widgets
        for w in self._all_children(self):
            try:
                if isinstance(w, ctk.CTkFrame):
                    if hasattr(w, '_fg_color') and w._fg_color not in ["transparent", None]:
                        w.configure(fg_color=self.card_bg)
                elif isinstance(w, ctk.CTkLabel):
                    w.configure(text_color=self.cor_texto)
                elif isinstance(w, ctk.CTkEntry):
                    w.configure(fg_color=self.cor_secundaria,
                                text_color=self.cor_texto_entry,
                                border_color=self.cor_borda,
                                placeholder_text_color=self.cor_placeholder)
                elif isinstance(w, ctk.CTkComboBox):
                    w.configure(fg_color=self.cor_secundaria,
                                text_color=self.cor_texto,
                                border_color=self.cor_borda,
                                button_color=self.cor_primaria,
                                button_hover_color=self.cor_hover)
                elif isinstance(w, ctk.CTkTextbox):
                    w.configure(fg_color=self.cor_secundaria,
                                text_color=self.cor_texto_entry,
                                border_color=self.cor_borda)
                elif isinstance(w, ctk.CTkCheckBox) or isinstance(w, ctk.CTkSwitch):
                    w.configure(text_color=self.cor_texto)
                elif isinstance(w, ctk.CTkButton):
                    if w._fg_color == self.cor_adicionar or w._fg_color == self.cor_imprimir:
                        # Manter cores específicas para botões de ação
                        pass
                    else:
                        w.configure(fg_color=self.cor_primaria,
                                    hover_color=self.cor_hover,
                                    text_color=self.cor_texto)
            except Exception:
                pass

        try:
            self._apply_ttk_theme()
        except Exception:
            pass

    def _small_label(self, parent, text, row, column, **kwargs):
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=9),
            text_color=self.cor_texto
        ).grid(row=row, column=column, sticky="w", padx=4, pady=1, **kwargs)

    # ===================== Construção da UI =====================
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=1)

        # top bar - MESMO ESTILO DO CADASTRO_DE_CORTE
        topbar = ctk.CTkFrame(self, fg_color=self.topbar_bg, corner_radius=0)
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        topbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            topbar,
            text="PAGAMENTO DE SERVIÇOS",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.cor_texto
        ).grid(row=0, column=0, sticky="w", padx=20, pady=6)

        # filtros - MESMO ESTILO DO CADASTRO_DE_CORTE
        filter_frame = ctk.CTkFrame(self, fg_color=self.filter_bg, corner_radius=8)
        filter_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(4, 2))
        filter_frame.grid_columnconfigure(6, weight=1)

        ctk.CTkLabel(filter_frame, text="Origem:", text_color=self.cor_texto).grid(
            row=0, column=0, padx=(8, 4), pady=4, sticky="w"
        )
        self.orig_seg = ctk.CTkSegmentedButton(
            filter_frame,
            values=ORIGEM_OPTIONS,
            variable=self.source_var,
            selected_color=self.accent_color,
            fg_color=self.cor_primaria,
            height=28,
            command=lambda *_: self.pesquisar_finalizados()
        )
        self.orig_seg.grid(row=0, column=1, padx=4, pady=4)

        ctk.CTkLabel(filter_frame, text="Setor / Serviço:", text_color=self.cor_texto).grid(
            row=0, column=2, padx=(12, 4), pady=4, sticky="w"
        )
        self.filtro_servico_combo = ctk.CTkComboBox(
            filter_frame,
            values=SERVICE_FILTER_OPTIONS,
            variable=self.filter_servico_var,
            width=160,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            dropdown_hover_color=self.cor_hover,
            command=lambda *_: self.pesquisar_finalizados()
        )
        self.filtro_servico_combo.grid(row=0, column=3, padx=4, pady=6)

        self.busca_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Pesquisar...",
            width=180,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry,
            placeholder_text_color=self.cor_placeholder
        )
        self.busca_entry.grid(row=0, column=4, padx=4, pady=6)
        self.busca_entry.bind("<Return>", lambda e: self.pesquisar_finalizados())

        ctk.CTkButton(
            filter_frame,
            text="🔍",
            width=40,
            height=28,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=self.pesquisar_finalizados
        ).grid(row=0, column=5, padx=4, pady=6)

        # conteúdo
        content_frame = ctk.CTkFrame(self, fg_color=self.main_bg, corner_radius=0)
        content_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=4, pady=(0, 6))
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=2)
        content_frame.grid_rowconfigure(0, weight=1)

        # painel esquerdo (lista) - MESMO ESTILO DO CADASTRO_DE_CORTE
        left_panel = ctk.CTkFrame(content_frame, fg_color=self.card_bg, corner_radius=12, border_width=1)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=2)
        left_panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            left_panel,
            text="Finalizações / Entradas",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.cor_texto
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        tabs_left = ctk.CTkTabview(left_panel, fg_color="transparent")
        tabs_left.grid(row=1, column=0, sticky="nsew", padx=6, pady=(2, 6))

        tab_servicos = tabs_left.add("Serviços")
        tab_defeitos = tabs_left.add("Defeitos")

        tree_container = ctk.CTkFrame(tab_servicos, fg_color="transparent")
        tree_container.grid(row=0, column=0, sticky="nsew")
        tab_servicos.grid_rowconfigure(0, weight=1)
        tab_servicos.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_rowconfigure(1, weight=0)
        tree_container.grid_columnconfigure(0, weight=1)

        cols = ("id", "tipo_servico", "codigo", "descricao", "costureira", "data_envio", "data_chegada", "total_qtd")
        self.tree = ttk.Treeview(tree_container, columns=cols, show="headings", height=11, style="Custom.Treeview")
        headings = ["ID", "Serviço", "Código", "Descrição", "Costureira", "Envio", "Chegada", "Qtd"]
        tree_widths = {
            "id": 50,
            "tipo_servico": 85,
            "codigo": 65,
            "descricao": 140,
            "costureira": 110,
            "data_envio": 75,
            "data_chegada": 75,
            "total_qtd": 50,
        }
        for col, h in zip(cols, headings):
            self.tree.heading(col, text=h)
            self.tree.column(col, width=tree_widths.get(col, 80), anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<Double-1>", self._on_select_item)
        self.tree.bind("<Return>", self._on_select_item)

        defeitos_container = ctk.CTkFrame(tab_defeitos, fg_color="transparent")
        defeitos_container.grid(row=0, column=0, sticky="nsew")
        tab_defeitos.grid_rowconfigure(0, weight=1)
        tab_defeitos.grid_columnconfigure(0, weight=1)
        defeitos_container.grid_rowconfigure(0, weight=1)
        defeitos_container.grid_rowconfigure(1, weight=0)
        defeitos_container.grid_columnconfigure(0, weight=1)

        defeitos_cols = ("id", "prestador", "codigo", "descricao", "tamanho", "quantidade", "data_retorno", "status")
        self.defeitos_tree = ttk.Treeview(defeitos_container, columns=defeitos_cols, show="headings",
                                          height=11, style="Custom.Treeview")
        defeitos_headings = ["ID", "Prestador", "Código", "Descrição", "Tam", "Qtd", "Retorno", "Status"]
        defeitos_widths = {
            "id": 50,
            "prestador": 120,
            "codigo": 70,
            "descricao": 140,
            "tamanho": 45,
            "quantidade": 55,
            "data_retorno": 80,
            "status": 70,
        }
        for col, h in zip(defeitos_cols, defeitos_headings):
            self.defeitos_tree.heading(col, text=h)
            self.defeitos_tree.column(col, width=defeitos_widths.get(col, 80), anchor="center")
        self.defeitos_tree.grid(row=0, column=0, sticky="nsew")
        defeitos_vsb = ttk.Scrollbar(defeitos_container, orient="vertical", command=self.defeitos_tree.yview)
        defeitos_hsb = ttk.Scrollbar(defeitos_container, orient="horizontal", command=self.defeitos_tree.xview)
        self.defeitos_tree.configure(yscrollcommand=defeitos_vsb.set, xscrollcommand=defeitos_hsb.set)
        defeitos_vsb.grid(row=0, column=1, sticky="ns")
        defeitos_hsb.grid(row=1, column=0, sticky="ew")
        self.defeitos_tree.bind("<Double-1>", self._on_select_defeito)
        self.defeitos_tree.bind("<Return>", self._on_select_defeito)

        defeitos_actions = ctk.CTkFrame(tab_defeitos, fg_color="transparent")
        defeitos_actions.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        ctk.CTkButton(
            defeitos_actions,
            text="Marcar Pago",
            command=self._pagar_defeito,
            fg_color=self.cor_sucesso,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            height=30,
            width=120
        ).pack(side="left", padx=4)


        # Configurar cores das linhas alternadas (alto contraste)
        colors = getattr(self, "_tree_colors", None) or {}
        cor_linha_par = colors.get("even", "#ffffff")
        cor_linha_impar = colors.get("odd", "#f3f4f6")
        cor_texto = colors.get("fg", self.cor_texto)

        self.tree.tag_configure("oddrow", background=cor_linha_impar, foreground=cor_texto)
        self.tree.tag_configure("evenrow", background=cor_linha_par, foreground=cor_texto)


        # painel direito (resumo e formulários)
        right_panel = ctk.CTkFrame(content_frame, fg_color=self.main_bg, corner_radius=0)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_columnconfigure(1, weight=1)
        right_panel.grid_columnconfigure(2, weight=1)
        right_panel.grid_rowconfigure(3, weight=1)

        # resumo de pagamento - MESMO ESTILO DO CADASTRO_DE_CORTE
        summary_frame = ctk.CTkFrame(right_panel, fg_color=self.card_bg, corner_radius=12, border_width=1)
        summary_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=2, pady=(0, 4))
        summary_frame.grid_columnconfigure(0, weight=1)
        summary_frame.grid_columnconfigure(1, weight=1)
        summary_frame.grid_columnconfigure(2, weight=1)
        summary_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            summary_frame,
            text="Resumo de Pagamento",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.cor_texto
        ).grid(row=0, column=0, padx=12, pady=(4, 2), sticky="w")

        card_base = ctk.CTkFrame(summary_frame, corner_radius=8, fg_color=self.cor_primaria)
        card_base.grid(row=1, column=0, padx=8, pady=6, sticky="ew")
        ctk.CTkLabel(card_base, text="Base (R$)", font=ctk.CTkFont(size=10, weight="bold"), text_color="white").grid(
            row=0, column=0, sticky="w", padx=8, pady=(4, 0)
        )
        self.base_entry = ctk.CTkEntry(card_base, state="readonly", fg_color="white", text_color="black")
        self.base_entry.grid(row=1, column=0, padx=8, pady=(3, 6), sticky="ew")

        card_desc = ctk.CTkFrame(summary_frame, corner_radius=8, fg_color=self.cor_primaria)
        card_desc.grid(row=1, column=1, padx=8, pady=6, sticky="ew")
        ctk.CTkLabel(card_desc, text="Desconto (R$)", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="white").grid(
            row=0, column=0, sticky="w", padx=8, pady=(4, 0)
        )
        self.desconto_entry = ctk.CTkEntry(card_desc, state="readonly", fg_color="white", text_color="black")
        self.desconto_entry.grid(row=1, column=0, padx=8, pady=(3, 6), sticky="ew")

        card_total = ctk.CTkFrame(summary_frame, corner_radius=8, fg_color=self.cor_primaria)
        card_total.grid(row=1, column=2, padx=8, pady=6, sticky="ew")
        ctk.CTkLabel(card_total, text="Total a Pagar", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="white").grid(
            row=0, column=0, sticky="w", padx=8, pady=(4, 0)
        )
        self.total_entry = ctk.CTkEntry(card_total, state="readonly", font=ctk.CTkFont(size=14, weight="bold"),
                                        fg_color="white", text_color="black")
        self.total_entry.grid(row=1, column=0, padx=8, pady=(3, 6), sticky="ew")

        destaque = ctk.CTkFrame(summary_frame, corner_radius=8, fg_color=self.cor_primaria)
        destaque.grid(row=0, column=3, rowspan=2, padx=12, pady=6, sticky="nsew")
        self.total_destaque = ctk.CTkLabel(
            destaque,
            text="R$ 0.00",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        self.total_destaque.grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")
        self.total_lbl = ctk.CTkLabel(
            destaque,
            text="Total a pagar",
            font=ctk.CTkFont(size=11),
            text_color="white"
        )
        self.total_lbl.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="w")
        self.feedback = ctk.CTkLabel(
            destaque,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="#ffd4d4"
        )
        self.feedback.grid(row=2, column=0, padx=16, pady=(0, 6), sticky="w")

        # seções inferiores - MESMO ESTILO DO CADASTRO_DE_CORTE
        ident_card = ctk.CTkFrame(right_panel, fg_color=self.card_bg, corner_radius=12, border_width=1)
        ident_card.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        ident_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            ident_card,
            text="1. Identificação / Quantidades",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.cor_texto
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(4, 2))
        self._small_label(ident_card, "Serviço:", 1, 0)
        servico_combo = ctk.CTkComboBox(
            ident_card,
            values=SERVICE_OPTIONS,
            variable=self.tipo_servico_var,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover
        )
        servico_combo.grid(row=1, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(ident_card, "Código:", 2, 0)
        self.ident_codigo = ctk.CTkEntry(
            ident_card,
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.ident_codigo.grid(row=2, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(ident_card, "Descrição:", 3, 0)
        self.ident_descricao = ctk.CTkEntry(
            ident_card,
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.ident_descricao.grid(row=3, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(ident_card, "Costureira:", 4, 0)
        self.ident_costureira = ctk.CTkEntry(
            ident_card,
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.ident_costureira.grid(row=4, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(ident_card, "Data Envio:", 5, 0)
        self.data_envio = ctk.CTkEntry(
            ident_card,
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.data_envio.grid(row=5, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(ident_card, "Data Chegada:", 6, 0)
        self.data_chegada = ctk.CTkEntry(
            ident_card,
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.data_chegada.grid(row=6, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(ident_card, "Qtd Finalizada:", 7, 0)
        self.quant_final_entry = ctk.CTkEntry(
            ident_card,
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.quant_final_entry.grid(row=7, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(ident_card, "Valor/Peça:", 8, 0)
        self.valor_peca_entry = ctk.CTkEntry(
            ident_card,
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.valor_peca_entry.grid(row=8, column=1, padx=8, pady=1, sticky="ew")

        ajustes_card = ctk.CTkFrame(right_panel, fg_color=self.card_bg, corner_radius=12, border_width=1)
        ajustes_card.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)
        ajustes_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            ajustes_card,
            text="2. Ajustes Financeiros",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.cor_texto
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(4, 2))
        self._small_label(ajustes_card, "Adiantamento (R$):", 1, 0)
        self.adiantamento_entry = ctk.CTkEntry(
            ajustes_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.adiantamento_entry.grid(row=1, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(ajustes_card, "Ajuda de Custo (R$):", 2, 0)
        self.ajuda_entry = ctk.CTkEntry(
            ajustes_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.ajuda_entry.grid(row=2, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(ajustes_card, "Faltantes:", 3, 0)
        self.faltantes_entry = ctk.CTkEntry(
            ajustes_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.faltantes_entry.grid(row=3, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(ajustes_card, "Estragadas:", 4, 0)
        self.estragadas_entry = ctk.CTkEntry(
            ajustes_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.estragadas_entry.grid(row=4, column=1, padx=8, pady=1, sticky="ew")

        # --- Bonificação (opcional) ---
        self._small_label(ajustes_card, "Bonificação (R$):", 5, 0)
        self.bonificacao_entry = ctk.CTkEntry(
            ajustes_card,
            state="disabled",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.bonificacao_entry.grid(row=5, column=1, padx=8, pady=1, sticky="ew")

        self.bonif_var = tk.StringVar(value="nao")
        bonif_opts = ctk.CTkFrame(ajustes_card, fg_color="transparent")
        bonif_opts.grid(row=6, column=1, padx=8, pady=(0, 4), sticky="w")
        ctk.CTkRadioButton(bonif_opts, text="Não", variable=self.bonif_var, value="nao",
                           command=self._toggle_bonificacao, text_color=self.cor_texto).grid(row=0, column=0,
                                                                                             padx=(0, 12))
        ctk.CTkRadioButton(bonif_opts, text="Sim", variable=self.bonif_var, value="sim",
                           command=self._toggle_bonificacao, text_color=self.cor_texto).grid(row=0, column=1)
        self.bonificacao_entry.bind("<KeyRelease>", lambda ev: self.recalcular())

        defeito_card = ctk.CTkFrame(right_panel, fg_color=self.card_bg, corner_radius=12, border_width=1)
        defeito_card.grid(row=1, column=2, sticky="nsew", padx=2, pady=2)
        defeito_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            defeito_card,
            text="3. Defeitos & Adiantamento",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.cor_texto
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(4, 2))
        self._small_label(defeito_card, "Peças c/ Defeito:", 1, 0)
        self.defeito_count_entry = ctk.CTkEntry(
            defeito_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.defeito_count_entry.grid(row=1, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(defeito_card, "Valor Defeito (R$):", 2, 0)
        self.valor_defeito_entry = ctk.CTkEntry(
            defeito_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.valor_defeito_entry.grid(row=2, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(defeito_card, "Observações:", 3, 0)
        self.obs_defeito_text = ctk.CTkTextbox(
            defeito_card,
            height=60,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.obs_defeito_text.grid(row=4, column=0, columnspan=2, padx=12, pady=(2, 6), sticky="ew")

        adiant_frame = ctk.CTkFrame(defeito_card, fg_color=self.cor_primaria, corner_radius=8, border_width=1)
        adiant_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=12, pady=(3, 6))
        adiant_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            adiant_frame,
            text="Adiantamento Registrado",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white"
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 2))
        ctk.CTkLabel(adiant_frame, text="Valor:", font=ctk.CTkFont(size=10), text_color="white").grid(
            row=1, column=0, sticky="e", padx=4
        )
        self.adiantamento_registrado_valor_lbl = ctk.CTkLabel(
            adiant_frame,
            text="R$ 0.00",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white"
        )
        self.adiantamento_registrado_valor_lbl.grid(row=1, column=1, sticky="w", padx=4)
        ctk.CTkLabel(adiant_frame, text="Parcelas:", font=ctk.CTkFont(size=10), text_color="white").grid(
            row=2, column=0, sticky="e", padx=4
        )
        self.adiantamento_registrado_parcelas_lbl = ctk.CTkLabel(adiant_frame, text="0", text_color="white")
        self.adiantamento_registrado_parcelas_lbl.grid(row=2, column=1, sticky="w", padx=4)
        ctk.CTkLabel(adiant_frame, text="Saldo:", font=ctk.CTkFont(size=10), text_color="white").grid(
            row=3, column=0, sticky="e", padx=4
        )
        self.adiantamento_registrado_saldo_lbl = ctk.CTkLabel(
            adiant_frame,
            text="R$ 0.00",
            font=ctk.CTkFont(size=11),
            text_color="white"
        )
        self.adiantamento_registrado_saldo_lbl.grid(row=3, column=1, sticky="w", padx=4)

        desconto_frame = ctk.CTkFrame(adiant_frame, fg_color="transparent")
        desconto_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 3))
        desconto_frame.grid_columnconfigure((1, 2, 3), weight=1)
        ctk.CTkLabel(
            desconto_frame,
            text="Valor atual:",
            font=ctk.CTkFont(size=9),
            text_color="white"
        ).grid(row=0, column=0, sticky="e", padx=4)
        self.adiantamento_valor_atual_entry = ctk.CTkEntry(
            desconto_frame,
            width=100,
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.adiantamento_valor_atual_entry.grid(row=0, column=1, padx=4, sticky="w")
        self.adiantamento_valor_atual_entry.configure(state="normal")
        self.adiantamento_valor_atual_entry.delete(0, "end")
        self.adiantamento_valor_atual_entry.insert(0, "0.00")
        self.adiantamento_valor_atual_entry.configure(state="readonly")
        ctk.CTkLabel(
            desconto_frame,
            text="Valor a descontar:",
            font=ctk.CTkFont(size=9),
            text_color="white"
        ).grid(row=1, column=0, sticky="e", padx=4)
        self.adiantamento_desconto_entry = ctk.CTkEntry(
            desconto_frame,
            width=100,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.adiantamento_desconto_entry.grid(row=1, column=1, padx=4, sticky="w")
        self.adiantamento_desconto_entry.bind("<Return>", lambda e: self.aplicar_desconto_adiantamento())
        self.aplicar_desconto_btn = ctk.CTkButton(
            desconto_frame,
            text="Aplicar",
            width=80,
            height=28,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=self.aplicar_desconto_adiantamento
        )
        self.aplicar_desconto_btn.grid(row=1, column=2, padx=4)
        self.descontar_parcela_btn = ctk.CTkButton(
            adiant_frame,
            text="Descontar 1 parcela",
            width=160,
            height=28,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=self.descontar_parcela_adiantamento
        )
        self.descontar_parcela_btn.grid(row=6, column=0, columnspan=2, padx=8, pady=(2, 6))

        banco_card = ctk.CTkFrame(right_panel, fg_color=self.card_bg, corner_radius=12, border_width=1)
        banco_card.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=2, pady=2)
        banco_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            banco_card,
            text="4. Dados Bancários",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.cor_texto
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(4, 2))
        self._small_label(banco_card, "Titular:", 1, 0)
        self.titular_entry = ctk.CTkEntry(
            banco_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.titular_entry.grid(row=1, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(banco_card, "CPF:", 2, 0)
        self.cpf_entry = ctk.CTkEntry(
            banco_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.cpf_entry.grid(row=2, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(banco_card, "Banco:", 1, 2)
        self.banco_entry = ctk.CTkEntry(
            banco_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.banco_entry.grid(row=1, column=3, padx=8, pady=1, sticky="ew")
        self._small_label(banco_card, "Agência:", 2, 2)
        self.agencia_entry = ctk.CTkEntry(
            banco_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.agencia_entry.grid(row=2, column=3, padx=8, pady=1, sticky="ew")
        self._small_label(banco_card, "Conta:", 3, 0)
        self.conta_entry = ctk.CTkEntry(
            banco_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.conta_entry.grid(row=3, column=1, padx=8, pady=1, sticky="ew")
        self._small_label(banco_card, "PIX:", 3, 2)
        self.pix_entry = ctk.CTkEntry(
            banco_card,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.pix_entry.grid(row=3, column=3, padx=8, pady=1, sticky="ew")

        # ações - MESMO ESTILO DO CADASTRO_DE_CORTE
        actions = ctk.CTkFrame(right_panel, fg_color=self.main_bg)
        actions.grid(row=3, column=0, columnspan=3, sticky="e", pady=(4, 2), padx=2)
        self.salvar_btn = ctk.CTkButton(
            actions,
            text="💾 Salvar",
            width=130,
            height=32,
            fg_color=self.cor_adicionar,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            font=("Arial", 12),
            command=self.salvar_pagamento
        )
        self.exportar_btn = ctk.CTkButton(
            actions,
            text="📤 Exportar CSV",
            width=130,
            height=32,
            fg_color=self.cor_imprimir,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            font=("Arial", 12),
            command=self.exportar_csv
        )
        self.recalcular_btn = ctk.CTkButton(
            actions,
            text="🔁 Recalcular",
            width=120,
            height=32,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            font=("Arial", 12),
            command=self.recalcular
        )
        self.imprimir_btn = ctk.CTkButton(
            actions,
            text="🖨️ Imprimir",
            width=130,
            height=32,
            fg_color=self.cor_imprimir,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            font=("Arial", 12),
            command=self.imprimir_recibo
        )
        self.salvar_btn.grid(row=0, column=0, padx=6)
        self.exportar_btn.grid(row=0, column=1, padx=6)
        self.recalcular_btn.grid(row=0, column=2, padx=6)
        self.imprimir_btn.grid(row=0, column=3, padx=6)

        # binds para recalcular automaticamente
        for e in [
            self.adiantamento_entry, self.ajuda_entry, self.faltantes_entry,
            self.estragadas_entry, self.defeito_count_entry, self.valor_defeito_entry,
            self.bonificacao_entry
        ]:
            e.bind("<KeyRelease>", lambda ev: self.recalcular())

        self.ident_entries = {
            "codigo": self.ident_codigo,
            "descricao": self.ident_descricao,
            "costureira": self.ident_costureira
        }

    # ===================== Lógica auxiliar =====================
    def _toggle_bonificacao(self):
        try:
            usar = (self.bonif_var.get() == "sim")
        except Exception:
            usar = False
        try:
            self.bonificacao_entry.configure(state="normal" if usar else "disabled")
            if not usar:
                self.bonificacao_entry.delete(0, "end")
                self.bonificacao_entry.insert(0, "0.00")
        except Exception:
            pass
        try:
            self.recalcular()
        except Exception:
            pass


    def _buscar_envio_id(self, finalizado_id: int | None = None, codigo: str | None = None):
        """Tenta obter envio_id do corte finalizado (se a coluna existir)."""
        if not _table_exists("cortes_finalizados"):
            return None

        cols_cf = _columns_of("cortes_finalizados")
        if "envio_id" not in cols_cf:
            return None

        try:
            if finalizado_id is not None:
                r = _select_one("SELECT envio_id FROM cortes_finalizados WHERE id = %s LIMIT 1", (finalizado_id,))
            elif codigo:
                r = _select_one("SELECT envio_id FROM cortes_finalizados WHERE codigo = %s ORDER BY id DESC LIMIT 1", (codigo,))
            else:
                r = None
            if r and r[0] is not None:
                return int(r[0])
        except Exception:
            pass
        return None

    def _buscar_corte_id_origem(self, finalizado_id: int | None = None) -> int | None:
        """Tenta obter o corte_id original a partir de cortes_finalizados (se existir)."""
        if not finalizado_id or not _table_exists("cortes_finalizados"):
            return None
        cols_cf = _columns_of("cortes_finalizados")
        if "corte_id" not in cols_cf:
            return None
        try:
            r = _select_one("SELECT corte_id FROM cortes_finalizados WHERE id = %s LIMIT 1", (finalizado_id,))
            if r and r[0] is not None:
                return int(r[0])
        except Exception:
            pass
        return None

    def _buscar_valor_peca(self, codigo: str, finalizado_id: int | None = None) -> float:
        """Busca o valor por peça no fluxo novo (envios_cortes) e cai no antigo se necessário."""
        # 1) se cortes_finalizados já tiver valor_peca/valor_por_peca, usa direto
        try:
            cols_cf = _columns_of("cortes_finalizados") if _table_exists("cortes_finalizados") else set()
            for col in ("valor_peca", "valor_por_peca"):
                if col in cols_cf:
                    if finalizado_id is not None:
                        r = _select_one(f"SELECT {col} FROM cortes_finalizados WHERE id=%s LIMIT 1", (finalizado_id,))
                    else:
                        r = _select_one(f"SELECT {col} FROM cortes_finalizados WHERE codigo=%s ORDER BY id DESC LIMIT 1", (codigo,))
                    if r and r[0] is not None:
                        return float(r[0])
        except Exception:
            pass

        # 2) tenta via envios_cortes (mais confiável no fluxo novo)
        envio_id = self._buscar_envio_id(finalizado_id=finalizado_id, codigo=codigo)
        if envio_id and _table_exists("envios_cortes"):
            cols_env = _columns_of("envios_cortes")
            col_val = "valor_peca" if "valor_peca" in cols_env else ("valor_por_peca" if "valor_por_peca" in cols_env else None)
            if col_val:
                try:
                    r = _select_one(f"SELECT {col_val} FROM envios_cortes WHERE id=%s LIMIT 1", (envio_id,))
                    if r and r[0] is not None:
                        return float(r[0])
                except Exception:
                    pass
            else:
                try:
                    cols_val = [c for c in [
                        "valor_pp", "valor_p", "valor_m", "valor_g",
                        "valor_gg", "valor_g1", "valor_g2", "valor_g3"
                    ] if c in cols_env]
                    if cols_val:
                        r = _select_one(
                            f"SELECT {', '.join(cols_val)} FROM envios_cortes WHERE id=%s LIMIT 1",
                            (envio_id,),
                        )
                        if r:
                            for val in r:
                                if val is not None and float(val or 0) > 0:
                                    return float(val)
                except Exception:
                    pass

        # 2b) tenta via envio_detalhes_tamanho (valor_peca por tamanho)
        if envio_id and _table_exists("envio_detalhes_tamanho"):
            cols_det = _columns_of("envio_detalhes_tamanho")
            if "valor_peca" in cols_det:
                try:
                    r = _select_one(
                        "SELECT MAX(valor_peca) FROM envio_detalhes_tamanho WHERE envio_id = %s",
                        (envio_id,),
                    )
                    if r and r[0] is not None:
                        return float(r[0])
                except Exception:
                    pass

        # 3) fallback fluxo antigo
        if _table_exists("controle_envio_cortes"):
            cols_old = _columns_of("controle_envio_cortes")
            if "valor_peca" in cols_old and ("codigo_corte" in cols_old or "codigo" in cols_old):
                col_cod = "codigo_corte" if "codigo_corte" in cols_old else "codigo"
                try:
                    r = _select_one(f"""
                        SELECT valor_peca
                          FROM controle_envio_cortes
                         WHERE {col_cod} = %s
                      ORDER BY id DESC LIMIT 1
                    """, (codigo,))
                    if r and r[0] is not None:
                        return float(r[0])
                except Exception:
                    pass

        return 0.0

    def _carregar_bonificacao_por_corte(self, codigo: str, finalizado_id: int | None = None) -> None:
        """Define rádio Sim/Não conforme defeitos no retorno e bonificacao salva."""
        valor_flag = 0.0
        total_defeitos = 0
        try:
            if finalizado_id is not None:
                r = _select_one("""
                    SELECT bonificacao
                      FROM cortes_finalizados
                     WHERE id = %s
                  ORDER BY id DESC LIMIT 1
                """, (finalizado_id,))
            else:
                r = _select_one("""
                    SELECT bonificacao
                      FROM cortes_finalizados
                     WHERE codigo = %s
                  ORDER BY id DESC LIMIT 1
                """, (codigo,))
            if r and r[0] is not None:
                try:
                    valor_flag = float(r[0])
                except Exception:
                    valor_flag = 0.0
        except Exception as e:
            print("Erro ao ler bonificação:", e)

        envio_id = self._buscar_envio_id(finalizado_id=finalizado_id, codigo=codigo)
        if envio_id and _table_exists("controle_retorno_cortes"):
            try:
                r_def = _select_one("""
                    SELECT COALESCE(SUM(total_defeitos), 0)
                      FROM controle_retorno_cortes
                     WHERE envio_id = %s
                """, (envio_id,))
                if r_def and r_def[0] is not None:
                    total_defeitos = int(r_def[0] or 0)
            except Exception:
                pass

        if total_defeitos > 0:
            self.bonif_var.set("nao")
            self.bonificacao_entry.configure(state="disabled")
            self.bonificacao_entry.delete(0, "end")
            self.bonificacao_entry.insert(0, "0.00")
        elif valor_flag > 0:
            self.bonif_var.set("sim")
            self.bonificacao_entry.configure(state="normal")
            self.bonificacao_entry.delete(0, "end")
            self.bonificacao_entry.insert(0, f"{valor_flag:.2f}")
        else:
            self.bonif_var.set("sim")
            self.bonificacao_entry.configure(state="normal")
            self.bonificacao_entry.delete(0, "end")
            self.bonificacao_entry.insert(0, "0.00")

        self.recalcular()

    def _carregar_adiantamento_faccao(
        self,
        codigo_modelo: str,
        corte_id: int | None,
        envio_id: int | None = None,
        prestador_nome: str | None = None,
    ) -> None:
        """
        Lê adiantamento_faccao. Prioriza vinculo por envio_id (quando existir),
        depois por corte_id e, por fim, apenas pelo código do modelo.
        """
        self._adiantamento_faccao_record = None
        row = None

        if not _table_exists("adiantamento_faccao"):
            row = None
        else:
            cols_ad = _columns_of("adiantamento_faccao")
            codigo_str = (str(codigo_modelo or "")).strip()
            codigo_variants = []
            if codigo_str:
                codigo_variants.append(codigo_str)
                if codigo_str.isdigit():
                    codigo_nozeros = str(int(codigo_str))
                    if codigo_nozeros not in codigo_variants:
                        codigo_variants.append(codigo_nozeros)
                    codigo_padded = codigo_nozeros.zfill(4)
                    if codigo_padded not in codigo_variants:
                        codigo_variants.append(codigo_padded)
            if not codigo_variants:
                codigo_variants = [codigo_str]

            def _buscar(sql, params):
                try:
                    return _select_one(sql, params)
                except Exception as e:
                    print("lookup adiantamento falhou:", e)
                    return None

            if envio_id and "envio_id" in cols_ad:
                row = _buscar(
                    """
                    SELECT id, COALESCE(valor, 0) AS v, forma_pagamento, COALESCE(parcelas, 1)
                      FROM adiantamento_faccao
                     WHERE codigo_modelo = ANY(%s) AND envio_id = %s
                  ORDER BY id DESC LIMIT 1
                    """,
                    (codigo_variants, envio_id),
                )

            if not row and envio_id and "corte_id" in cols_ad and _table_exists("envios_cortes"):
                try:
                    corte_envio = _select_one(
                        "SELECT corte_id FROM envios_cortes WHERE id = %s LIMIT 1",
                        (envio_id,),
                    )
                    corte_envio_id = int(corte_envio[0]) if corte_envio and corte_envio[0] is not None else None
                except Exception:
                    corte_envio_id = None
                if corte_envio_id:
                    row = _buscar(
                        """
                        SELECT id, COALESCE(valor, 0) AS v, forma_pagamento, COALESCE(parcelas, 1)
                          FROM adiantamento_faccao
                         WHERE codigo_modelo = ANY(%s) AND corte_id = %s
                      ORDER BY id DESC LIMIT 1
                        """,
                        (codigo_variants, corte_envio_id),
                    )

            if not row and corte_id and "corte_id" in cols_ad:
                row = _buscar(
                    """
                    SELECT id, COALESCE(valor, 0) AS v, forma_pagamento, COALESCE(parcelas, 1)
                      FROM adiantamento_faccao
                     WHERE codigo_modelo = ANY(%s) AND corte_id = %s
                  ORDER BY id DESC LIMIT 1
                    """,
                    (codigo_variants, corte_id),
                )

            if not row:
                row = _buscar(
                    """
                    SELECT id, COALESCE(valor, 0) AS v, forma_pagamento, COALESCE(parcelas, 1)
                      FROM adiantamento_faccao
                     WHERE codigo_modelo = ANY(%s)
                  ORDER BY id DESC LIMIT 1
                    """,
                    (codigo_variants,),
                )

            if not row and prestador_nome and "faccao" in cols_ad:
                row = _buscar(
                    """
                    SELECT id, COALESCE(valor, 0) AS v, forma_pagamento, COALESCE(parcelas, 1)
                      FROM adiantamento_faccao
                     WHERE codigo_modelo = ANY(%s) AND faccao ILIKE %s
                  ORDER BY id DESC LIMIT 1
                    """,
                    (codigo_variants, prestador_nome),
                )

        if not row:
            # reset painel
            try:
                self.adiantamento_registrado_valor_lbl.configure(text="R$ 0.00")
                self.adiantamento_registrado_parcelas_lbl.configure(text="0")
                self.adiantamento_registrado_saldo_lbl.configure(text="R$ 0.00")
                self.adiantamento_entry.delete(0, "end")
                self.adiantamento_entry.insert(0, "0.00")
                self.adiantamento_valor_atual_entry.configure(state="normal")
                self.adiantamento_valor_atual_entry.delete(0, "end")
                self.adiantamento_valor_atual_entry.insert(0, "0.00")
                self.adiantamento_valor_atual_entry.configure(state="readonly")
                self.adiantamento_desconto_entry.delete(0, "end")
                self.adiantamento_desconto_entry.insert(0, "0.00")
                self.recalcular()
            except Exception:
                pass
            return

        adiant_id, valor, forma_pgto, parcelas = row
        valor = float(valor or 0)
        parcelas = int(parcelas or 1)
        self._adiantamento_faccao_record = {
            "id": adiant_id,
            "valor_restante": valor,
            "forma_pagamento": forma_pgto or "",
            "parcelas": parcelas,
        }
        try:
            self.adiantamento_registrado_valor_lbl.configure(text=f"R$ {valor:.2f}")
            self.adiantamento_registrado_parcelas_lbl.configure(text=str(parcelas))
            self.adiantamento_registrado_saldo_lbl.configure(text=f"R$ {valor:.2f}")
            self.adiantamento_entry.delete(0, "end")
            self.adiantamento_entry.insert(0, f"{valor:.2f}")
            self.adiantamento_valor_atual_entry.configure(state="normal")
            self.adiantamento_valor_atual_entry.delete(0, "end")
            self.adiantamento_valor_atual_entry.insert(0, f"{valor:.2f}")
            self.adiantamento_valor_atual_entry.configure(state="readonly")
            self.adiantamento_desconto_entry.delete(0, "end")
            self.adiantamento_desconto_entry.insert(0, f"{valor:.2f}")
            self.recalcular()
        except Exception:
            pass

    def _carregar_defeitos_e_pagamento(self, codigo: str, tipo_servico: str, finalizado_id: int | None = None) -> None:
        """
        Preenche campos de defeitos, faltantes/estragadas, ajuda e último pagamento salvo (se houver).
        """
        total_def = 0
        # Defeitos do fluxo novo
        try:
            r = _select_one("""
                SELECT cf.qtd_defeito_pp, cf.qtd_defeito_p, cf.qtd_defeito_m, cf.qtd_defeito_g,
                       cf.qtd_defeito_gg, cf.qtd_defeito_g1, cf.qtd_defeito_g2, cf.qtd_defeito_g3
                  FROM cortes_finalizados cf
                 WHERE cf.codigo = %s
              ORDER BY cf.id DESC LIMIT 1
            """, (codigo,))
            if r:
                total_def = sum(int(x or 0) for x in r)
                self.defeito_count_entry.delete(0, "end")
                self.defeito_count_entry.insert(0, str(total_def))
        except Exception:
            pass

        if total_def <= 0 and _table_exists("controle_retorno_cortes"):
            envio_id = self._buscar_envio_id(finalizado_id=finalizado_id, codigo=codigo)
            if envio_id:
                try:
                    r_def = _select_one("""
                        SELECT COALESCE(SUM(total_defeitos), 0)
                          FROM controle_retorno_cortes
                         WHERE envio_id = %s
                    """, (envio_id,))
                    if r_def and r_def[0] is not None:
                        total_def = int(r_def[0] or 0)
                        if total_def > 0:
                            self.defeito_count_entry.delete(0, "end")
                            self.defeito_count_entry.insert(0, str(total_def))
                except Exception:
                    pass

        self._carregar_bonificacao_por_corte(codigo, finalizado_id=finalizado_id)


        # valor peça (fluxo novo -> envios_cortes; fallback no antigo)
        valor_peca = self._buscar_valor_peca(codigo=codigo, finalizado_id=finalizado_id)
        self.valor_por_peca = float(valor_peca or 0.0)
        self.valor_peca_entry.configure(state="normal")
        self.valor_peca_entry.delete(0, "end")
        self.valor_peca_entry.insert(0, f"{self.valor_por_peca:.2f}")
        self.valor_peca_entry.configure(state="readonly")


        # último pagamento salvo
        try:
            p = _select_one("""
                SELECT pecas_com_defeito, valor_defeito, observacoes_defeito,
                       adiantamento, ajuda_custo, pecas_faltantes, pecas_estragadas
                  FROM pagamento_corte_acabamento
                 WHERE codigo = %s AND tipo_servico = %s
              ORDER BY id DESC LIMIT 1
            """, (codigo, tipo_servico))
            if p:
                p_def, p_vdef, p_obs, p_ad, p_aj, p_falt, p_est = p
                if (p_def or 0) > 0:
                    self.defeito_count_entry.delete(0, "end")
                    self.defeito_count_entry.insert(0, str(int(p_def or 0)))
                self.valor_defeito_entry.delete(0, "end")
                self.valor_defeito_entry.insert(0, f"{float(p_vdef or 0):.2f}")
                self.obs_defeito_text.delete("1.0", "end")
                self.obs_defeito_text.insert("1.0", p_obs or "")

                self.adiantamento_entry.delete(0, "end")
                self.adiantamento_entry.insert(0, f"{float(p_ad or 0):.2f}")
                self.ajuda_entry.delete(0, "end")
                self.ajuda_entry.insert(0, f"{float(p_aj or 0):.2f}")
                self.faltantes_entry.delete(0, "end")
                self.faltantes_entry.insert(0, str(int(p_falt or 0)))
                self.estragadas_entry.delete(0, "end")
                self.estragadas_entry.insert(0, str(int(p_est or 0)))
        except Exception:
            pass

        # defaults
        for e, default in [
            (self.adiantamento_entry, "0.00"),
            (self.ajuda_entry, "0.00"),
            (self.faltantes_entry, "0"),
            (self.estragadas_entry, "0"),
            (self.valor_defeito_entry, "0.00"),
        ]:
            if not e.get().strip():
                e.delete(0, "end")
                e.insert(0, default)

        self.recalcular()

    # ===================== Fluxos principais =====================

    def pesquisar_finalizados(self):
        def map_origem(val):
            m = {
                "Cortes a Pagar": "Finalizados",
                "Cortes Pagos": "Entradas",
                "Finalizados": "Finalizados",
                "Entradas": "Entradas",
            }
            return m.get(val, val)

        try:
            termo = (self.busca_entry.get() or "").strip()
        except Exception:
            termo = ""
        try:
            filtro_servico = self.filtro_servico_combo.get()
        except Exception:
            filtro_servico = "Todos"
        try:
            origem_raw = self.source_var.get()
        except Exception:
            origem_raw = "Finalizados"
        origem = map_origem(origem_raw)

        # limpa grid
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        like = f"%{termo}%"
        rows = []

        if origem == "Finalizados":  # CORTES A PAGAR (fluxo novo)
            if not _table_exists("cortes_finalizados"):
                return

            cols_cf = _columns_of("cortes_finalizados")

            # expressões compatíveis com diferentes esquemas
            codigo_expr = "cf.codigo" if "codigo" in cols_cf else ("cf.codigo_corte" if "codigo_corte" in cols_cf else "''")
            desc_expr = "cf.descricao" if "descricao" in cols_cf else ("cf.descricao_corte" if "descricao_corte" in cols_cf else "''")
            cost_expr = "cf.costureira" if "costureira" in cols_cf else ("cf.destino" if "destino" in cols_cf else "''")
            envio_expr = "cf.data_envio" if "data_envio" in cols_cf else ("cf.data_saida" if "data_saida" in cols_cf else "NULL")
            chegada_expr = "cf.data_chegada" if "data_chegada" in cols_cf else ("cf.data_retorno" if "data_retorno" in cols_cf else "NULL")

            # soma de quantidades (usa as colunas que existirem)
            def _q(col_new, col_old):
                if col_new in cols_cf:
                    return f"COALESCE(cf.{col_new},0)"
                if col_old in cols_cf:
                    return f"COALESCE(cf.{col_old},0)"
                return "0"

            total_qtd_expr = " + ".join([
                _q("qtd_pp", "pp"),
                _q("qtd_p", "p"),
                _q("qtd_m", "m"),
                _q("qtd_g", "g"),
                _q("qtd_gg", "gg"),
                _q("qtd_g1", "g1"),
                _q("qtd_g2", "g2"),
                _q("qtd_g3", "g3"),
            ])

            join_sql = ""
            tipo_expr = "'Facção'"

            # tipo/serviço preferencialmente vem de cortes_finalizados (fluxo novo)
            if "tipo_servico" in cols_cf:
                tipo_expr = "COALESCE(cf.tipo_servico, 'Facção')"
            elif "servico" in cols_cf:
                tipo_expr = "COALESCE(cf.servico, 'Facção')"
            else:
                # tenta via envios_cortes (se houver envio_id)
                if "envio_id" in cols_cf and _table_exists("envios_cortes"):
                    cols_env = _columns_of("envios_cortes")
                    join_sql = " LEFT JOIN envios_cortes e ON e.id = cf.envio_id "
                    if "servico" in cols_env:
                        tipo_expr = "COALESCE(e.servico, 'Facção')"
                    elif "tipo_servico" in cols_env:
                        tipo_expr = "COALESCE(e.tipo_servico, 'Facção')"
                # fallback fluxo antigo
                if tipo_expr == "'Facção'" and _table_exists("controle_envio_cortes"):
                    cols_old = _columns_of("controle_envio_cortes")
                    if ("codigo_corte" in cols_old or "codigo" in cols_old) and "servico" in cols_old:
                        col_cod = "codigo_corte" if "codigo_corte" in cols_old else "codigo"
                        join_sql = f" LEFT JOIN controle_envio_cortes cec ON cec.{col_cod} = {codigo_expr} "
                        tipo_expr = "COALESCE(cec.servico, 'Facção')"

            # pago flag (boolean/int)
            pago_expr = "COALESCE(cf.pago, FALSE)" if "pago" in cols_cf else "FALSE"

            sql = f"""
                SELECT
                    cf.id,
                    {tipo_expr} AS tipo_servico,
                    {codigo_expr} AS codigo,
                    {desc_expr} AS descricao,
                    {cost_expr} AS costureira,
                    {envio_expr} AS data_envio,
                    {chegada_expr} AS data_chegada,
                    ({total_qtd_expr}) AS total_qtd
                  FROM cortes_finalizados cf
                  {join_sql}
                 WHERE {pago_expr} = FALSE
                   AND ({codigo_expr} ILIKE %s OR {desc_expr} ILIKE %s OR {cost_expr} ILIKE %s)
                   AND (%s = 'Todos' OR {tipo_expr} = %s)
                 ORDER BY cf.id DESC
                 LIMIT 400
            """
            rows = _select_all(sql, (like, like, like, filtro_servico, filtro_servico))
        else:  # origem == "Entradas" -> CORTES PAGOS
            if not _table_exists("pagamento_corte_acabamento"):
                return
            sql = """
                SELECT
                    id,                -- id do pagamento
                    tipo_servico,
                    codigo,
                    descricao,
                    costureira,
                    data_envio,
                    data_chegada,
                    quantidade_finalizada AS total_qtd
                  FROM pagamento_corte_acabamento
                 WHERE (codigo ILIKE %s OR descricao ILIKE %s OR costureira ILIKE %s)
                   AND (%s = 'Todos' OR tipo_servico = %s)
                 ORDER BY COALESCE(data_pagamento, now()) DESC NULLS LAST
                 LIMIT 600
            """
            rows = _select_all(sql, (like, like, like, filtro_servico, filtro_servico))

        for r in rows:
            tag = 'evenrow' if len(self.tree.get_children()) % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=r, tags=(tag,))

        self._carregar_defeitos_pagamento()

    def _carregar_defeitos_pagamento(self):
        if not hasattr(self, "defeitos_tree"):
            return
        for iid in self.defeitos_tree.get_children():
            self.defeitos_tree.delete(iid)
        try:
            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()
            cur.execute(f"""
                SELECT id, prestador, codigo, descricao, tamanho, quantidade, data_retorno, status
                  FROM {schema}.defeitos_envios
                 WHERE origem = 'Externo'
                   AND status IN ('Finalizado', 'Aguardando Pagamento')
                 ORDER BY COALESCE(data_retorno, criado_em) DESC NULLS LAST, id DESC
            """)
            for row in cur.fetchall():
                defeito_id, prestador, codigo, desc, tamanho, qtd, data_retorno, status = row
                if hasattr(data_retorno, "strftime"):
                    data_retorno = data_retorno.strftime("%d/%m/%Y")
                self.defeitos_tree.insert("", "end", values=(
                    defeito_id, prestador or "", codigo or "", desc or "", tamanho or "",
                    qtd or 0, data_retorno or "", status or ""
                ))
            conn.close()
        except Exception as e:
            print(f"Erro ao carregar defeitos para pagamento: {e}")

    def _pagar_defeito(self):
        if not hasattr(self, "defeitos_tree"):
            return
        sel = self.defeitos_tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um defeito para pagamento.")
            return
        vals = self.defeitos_tree.item(sel[0], "values")
        defeito_id = vals[0]
        try:
            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()
            cur.execute(
                f"UPDATE {schema}.defeitos_envios SET status = %s, data_pagamento = CURRENT_DATE WHERE id = %s",
                ("Pago", defeito_id),
            )
            conn.commit()
            conn.close()
            self._carregar_defeitos_pagamento()
            messagebox.showinfo("Sucesso", "Pagamento do defeito registrado.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao registrar pagamento:\n{e}")


    def _carregar_dados_bancarios_prestador(
        self,
        destino: str,
        servico: str,
        finalizado_id: int | None = None,
        codigo: str | None = None,
    ) -> None:
        """Preenche campos bancários do prestador (último pagamento -> cadastro_faccoes/envios_cortes)."""

        def _tem_algo(row):
            return bool(row and any((v is not None and str(v).strip() != "") for v in row))

        destino = (destino or "").strip()
        servico = (servico or "").strip()

        row = None

        # 1) último pagamento do prestador nesse serviço
        try:
            row = _select_one("""
                SELECT titular_conta, cpf, banco, agencia, conta, pix
                  FROM pagamento_corte_acabamento
                 WHERE costureira = %s AND tipo_servico = %s
              ORDER BY id DESC LIMIT 1
            """, (destino, servico))
        except Exception:
            row = None

        # 2) fallback: último envio (fluxo novo)
        if not _tem_algo(row) and _table_exists("envios_cortes"):
            cols_env = _columns_of("envios_cortes")
            # nomes possíveis
            col_prest = "destino" if "destino" in cols_env else ("prestador" if "prestador" in cols_env else ("costureira" if "costureira" in cols_env else None))
            col_serv = "servico" if "servico" in cols_env else ("tipo_servico" if "tipo_servico" in cols_env else None)
            needed = ["titular_conta", "cpf", "banco", "agencia", "conta", "pix"]
            if col_prest and col_serv and all(c in cols_env for c in needed):
                try:
                    row = _select_one(f"""
                        SELECT titular_conta, cpf, banco, agencia, conta, pix
                          FROM envios_cortes
                         WHERE {col_prest} = %s AND {col_serv} = %s
                      ORDER BY id DESC LIMIT 1
                    """, (destino, servico))
                except Exception:
                    row = None

        # 3) fallback: prestador_id em cortes_finalizados/envios_cortes -> cadastro_faccoes
        if not _tem_algo(row) and _table_exists("cadastro_faccoes"):
            prestador_id = None
            cols_cf = _columns_of("cortes_finalizados") if _table_exists("cortes_finalizados") else set()
            for col in ("prestador_id", "faccao_id", "costureira_id"):
                if col in cols_cf and finalizado_id:
                    try:
                        r = _select_one(
                            f"SELECT {col} FROM cortes_finalizados WHERE id = %s LIMIT 1",
                            (finalizado_id,),
                        )
                        if r and r[0]:
                            prestador_id = int(r[0])
                            break
                    except Exception:
                        pass

            if prestador_id is None:
                envio_id = self._buscar_envio_id(finalizado_id=finalizado_id, codigo=codigo)
                if envio_id and _table_exists("envios_cortes"):
                    cols_env = _columns_of("envios_cortes")
                    if "prestador_id" in cols_env:
                        try:
                            r = _select_one(
                                "SELECT prestador_id FROM envios_cortes WHERE id = %s LIMIT 1",
                                (envio_id,),
                            )
                            if r and r[0]:
                                prestador_id = int(r[0])
                        except Exception:
                            pass

            if prestador_id:
                try:
                    row = _select_one("""
                        SELECT titular_da_conta, cpf, banco, agencia, conta, pix
                          FROM cadastro_faccoes
                         WHERE id = %s
                      ORDER BY id DESC LIMIT 1
                    """, (prestador_id,))
                except Exception:
                    row = None

        # 4) fallback: cadastro de facções pelo nome (quando não localizar ID)
        if not _tem_algo(row) and _table_exists("cadastro_faccoes"):
            cols_f = _columns_of("cadastro_faccoes")
            if all(c in cols_f for c in ["titular_da_conta", "cpf", "banco", "agencia", "conta", "pix", "nome"]):
                try:
                    row = _select_one("""
                        SELECT titular_da_conta, cpf, banco, agencia, conta, pix
                          FROM cadastro_faccoes
                         WHERE nome ILIKE %s OR codigo ILIKE %s
                      ORDER BY id DESC LIMIT 1
                    """, (destino, destino))
                except Exception:
                    row = None

        vals = row if _tem_algo(row) else ("", "", "", "", "", "")
        try:
            self.titular_entry.delete(0, "end"); self.titular_entry.insert(0, vals[0] or "")
            self.cpf_entry.delete(0, "end"); self.cpf_entry.insert(0, vals[1] or "")
            self.banco_entry.delete(0, "end"); self.banco_entry.insert(0, vals[2] or "")
            self.agencia_entry.delete(0, "end"); self.agencia_entry.insert(0, vals[3] or "")
            self.conta_entry.delete(0, "end"); self.conta_entry.insert(0, vals[4] or "")
            self.pix_entry.delete(0, "end"); self.pix_entry.insert(0, vals[5] or "")
        except Exception:
            pass

    # ===================== Loading / Thread helpers =====================

    def _center_toplevel(self, win, width: int = 320, height: int = 110) -> None:
        """Centraliza uma janela (Toplevel/CTkToplevel) no centro da tela."""
        try:
            win.update_idletasks()
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            x = int((sw - width) / 2)
            y = int((sh - height) / 2)
            win.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _show_loading_window(self, message: str = "Carregando...") -> None:
        """Mostra uma janelinha modal de carregamento no centro da tela."""
        try:
            if getattr(self, "_loading_win", None) is not None:
                try:
                    if self._loading_win.winfo_exists():
                        return
                except Exception:
                    self._loading_win = None
        except Exception:
            self._loading_win = None

        top = self.winfo_toplevel()
        try:
            win = ctk.CTkToplevel(top) if hasattr(ctk, "CTkToplevel") else Toplevel(top)
        except Exception:
            win = Toplevel(top)

        self._loading_win = win
        try:
            win.transient(top)
        except Exception:
            pass
        try:
            win.grab_set()
        except Exception:
            pass

        try:
            win.title("Carregando")
            win.resizable(False, False)
            win.protocol("WM_DELETE_WINDOW", lambda: None)
        except Exception:
            pass

        # Conteúdo
        try:
            frame = ctk.CTkFrame(win, fg_color=getattr(self, "card_bg", "#111827"), corner_radius=12)
            frame.pack(fill="both", expand=True, padx=14, pady=14)
            lbl = ctk.CTkLabel(
                frame,
                text=message,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=getattr(self, "cor_texto", "#e5e7eb"),
            )
            lbl.pack(expand=True)
        except Exception:
            # fallback tkinter puro
            frm = tk.Frame(win)
            frm.pack(fill="both", expand=True, padx=14, pady=14)
            tk.Label(frm, text=message, font=("Arial", 12, "bold")).pack(expand=True)

        self._center_toplevel(win, 340, 120)
        try:
            win.lift()
            win.update()
        except Exception:
            pass

    def _close_loading_window(self) -> None:
        """Fecha a janela de carregamento, se existir."""
        win = getattr(self, "_loading_win", None)
        self._loading_win = None
        if not win:
            return
        try:
            if win.winfo_exists():
                try:
                    win.grab_release()
                except Exception:
                    pass
                win.destroy()
        except Exception:
            pass

    # ===================== Fetchers (thread-safe: só DB, sem mexer na UI) =====================

    def _fetch_dados_bancarios_prestador(
        self,
        destino: str,
        servico: str,
        finalizado_id: int | None = None,
        codigo: str | None = None,
    ):
        """Versão 'somente consulta' de _carregar_dados_bancarios_prestador."""

        def _tem_algo(row):
            return bool(row and any((v is not None and str(v).strip() != "") for v in row))

        destino = (destino or "").strip()
        servico = (servico or "").strip()

        row = None

        # 1) último pagamento do prestador nesse serviço
        try:
            row = _select_one("""
                SELECT titular_conta, cpf, banco, agencia, conta, pix
                  FROM pagamento_corte_acabamento
                 WHERE costureira = %s AND tipo_servico = %s
              ORDER BY id DESC LIMIT 1
            """, (destino, servico))
        except Exception:
            row = None

        # 2) fallback: último envio (fluxo novo)
        if not _tem_algo(row) and _table_exists("envios_cortes"):
            cols_env = _columns_of("envios_cortes")
            col_prest = "destino" if "destino" in cols_env else ("prestador" if "prestador" in cols_env else ("costureira" if "costureira" in cols_env else None))
            col_serv = "servico" if "servico" in cols_env else ("tipo_servico" if "tipo_servico" in cols_env else None)
            needed = ["titular_conta", "cpf", "banco", "agencia", "conta", "pix"]
            if col_prest and col_serv and all(c in cols_env for c in needed):
                try:
                    row = _select_one(f"""
                        SELECT titular_conta, cpf, banco, agencia, conta, pix
                          FROM envios_cortes
                         WHERE {col_prest} = %s AND {col_serv} = %s
                      ORDER BY id DESC LIMIT 1
                    """, (destino, servico))
                except Exception:
                    row = None

        # 3) fallback: prestador_id em cortes_finalizados/envios_cortes -> cadastro_faccoes
        if not _tem_algo(row) and _table_exists("cadastro_faccoes"):
            prestador_id = None
            cols_cf = _columns_of("cortes_finalizados") if _table_exists("cortes_finalizados") else set()
            for col in ("prestador_id", "faccao_id", "costureira_id"):
                if col in cols_cf and finalizado_id:
                    try:
                        r = _select_one(
                            f"SELECT {col} FROM cortes_finalizados WHERE id = %s LIMIT 1",
                            (finalizado_id,),
                        )
                        if r and r[0]:
                            prestador_id = int(r[0])
                            break
                    except Exception:
                        pass

            if prestador_id is None:
                envio_id = self._buscar_envio_id(finalizado_id=finalizado_id, codigo=codigo)
                if envio_id and _table_exists("envios_cortes"):
                    cols_env = _columns_of("envios_cortes")
                    if "prestador_id" in cols_env:
                        try:
                            r = _select_one(
                                "SELECT prestador_id FROM envios_cortes WHERE id = %s LIMIT 1",
                                (envio_id,),
                            )
                            if r and r[0]:
                                prestador_id = int(r[0])
                        except Exception:
                            pass

            if prestador_id:
                try:
                    row = _select_one("""
                        SELECT titular_da_conta, cpf, banco, agencia, conta, pix
                          FROM cadastro_faccoes
                         WHERE id = %s
                      ORDER BY id DESC LIMIT 1
                    """, (prestador_id,))
                except Exception:
                    row = None

        # 4) fallback: cadastro de facções pelo nome (quando não localizar ID)
        if not _tem_algo(row) and _table_exists("cadastro_faccoes"):
            cols_f = _columns_of("cadastro_faccoes")
            if all(c in cols_f for c in ["titular_da_conta", "cpf", "banco", "agencia", "conta", "pix", "nome"]):
                try:
                    row = _select_one("""
                        SELECT titular_da_conta, cpf, banco, agencia, conta, pix
                          FROM cadastro_faccoes
                         WHERE nome ILIKE %s OR codigo ILIKE %s
                      ORDER BY id DESC LIMIT 1
                    """, (destino, destino))
                except Exception:
                    row = None

        return row if _tem_algo(row) else ("", "", "", "", "", "")

    def _fetch_adiantamento_faccao_data(
        self,
        codigo_modelo: str,
        corte_id: int | None,
        envio_id: int | None = None,
        prestador_nome: str | None = None,
    ):
        """Versão 'somente consulta' de _carregar_adiantamento_faccao."""
        if not _table_exists("adiantamento_faccao"):
            return None

        cols_ad = _columns_of("adiantamento_faccao")
        codigo_str = (str(codigo_modelo or "")).strip()
        codigo_variants = []
        if codigo_str:
            codigo_variants.append(codigo_str)
            if codigo_str.isdigit():
                codigo_nozeros = str(int(codigo_str))
                if codigo_nozeros not in codigo_variants:
                    codigo_variants.append(codigo_nozeros)
                codigo_padded = codigo_nozeros.zfill(4)
                if codigo_padded not in codigo_variants:
                    codigo_variants.append(codigo_padded)
        if not codigo_variants:
            codigo_variants = [codigo_str]

        def _buscar(sql, params):
            try:
                return _select_one(sql, params)
            except Exception:
                return None

        row = None

        if envio_id and "envio_id" in cols_ad:
            row = _buscar(
                """
                SELECT id, COALESCE(valor, 0) AS v, forma_pagamento, COALESCE(parcelas, 1)
                  FROM adiantamento_faccao
                 WHERE codigo_modelo = ANY(%s) AND envio_id = %s
              ORDER BY id DESC LIMIT 1
                """,
                (codigo_variants, envio_id),
            )

        if not row and envio_id and "corte_id" in cols_ad and _table_exists("envios_cortes"):
            try:
                corte_envio = _select_one(
                    "SELECT corte_id FROM envios_cortes WHERE id = %s LIMIT 1",
                    (envio_id,),
                )
                corte_envio_id = int(corte_envio[0]) if corte_envio and corte_envio[0] is not None else None
            except Exception:
                corte_envio_id = None
            if corte_envio_id:
                row = _buscar(
                    """
                    SELECT id, COALESCE(valor, 0) AS v, forma_pagamento, COALESCE(parcelas, 1)
                      FROM adiantamento_faccao
                     WHERE codigo_modelo = ANY(%s) AND corte_id = %s
                  ORDER BY id DESC LIMIT 1
                    """,
                    (codigo_variants, corte_envio_id),
                )

        if not row and corte_id and "corte_id" in cols_ad:
            row = _buscar(
                """
                SELECT id, COALESCE(valor, 0) AS v, forma_pagamento, COALESCE(parcelas, 1)
                  FROM adiantamento_faccao
                 WHERE codigo_modelo = ANY(%s) AND corte_id = %s
              ORDER BY id DESC LIMIT 1
                """,
                (codigo_variants, corte_id),
            )

        if not row:
            row = _buscar(
                """
                SELECT id, COALESCE(valor, 0) AS v, forma_pagamento, COALESCE(parcelas, 1)
                  FROM adiantamento_faccao
                 WHERE codigo_modelo = ANY(%s)
              ORDER BY id DESC LIMIT 1
                """,
                (codigo_variants,),
            )

        if not row and prestador_nome and "faccao" in cols_ad:
            row = _buscar(
                """
                SELECT id, COALESCE(valor, 0) AS v, forma_pagamento, COALESCE(parcelas, 1)
                  FROM adiantamento_faccao
                 WHERE codigo_modelo = ANY(%s) AND faccao ILIKE %s
              ORDER BY id DESC LIMIT 1
                """,
                (codigo_variants, prestador_nome),
            )

        if not row:
            return None

        adiant_id, valor, forma_pgto, parcelas = row
        valor = float(valor or 0)
        parcelas = int(parcelas or 1)
        return {
            "id": adiant_id,
            "valor_restante": valor,
            "forma_pagamento": forma_pgto or "",
            "parcelas": parcelas,
        }

    def _fetch_bonificacao_data(self, codigo: str, finalizado_id: int | None, envio_id: int | None):
        """Calcula (modo, valor, habilita_entry) para bonificação sem mexer na UI."""
        valor_flag = 0.0
        total_defeitos = 0

        try:
            if finalizado_id is not None:
                r = _select_one("""
                    SELECT bonificacao
                      FROM cortes_finalizados
                     WHERE id = %s
                  ORDER BY id DESC LIMIT 1
                """, (finalizado_id,))
            else:
                r = _select_one("""
                    SELECT bonificacao
                      FROM cortes_finalizados
                     WHERE codigo = %s
                  ORDER BY id DESC LIMIT 1
                """, (codigo,))
            if r and r[0] is not None:
                try:
                    valor_flag = float(r[0])
                except Exception:
                    valor_flag = 0.0
        except Exception:
            valor_flag = 0.0

        if envio_id and _table_exists("controle_retorno_cortes"):
            try:
                r_def = _select_one("""
                    SELECT COALESCE(SUM(total_defeitos), 0)
                      FROM controle_retorno_cortes
                     WHERE envio_id = %s
                """, (envio_id,))
                if r_def and r_def[0] is not None:
                    total_defeitos = int(r_def[0] or 0)
            except Exception:
                total_defeitos = 0

        if total_defeitos > 0:
            return {"modo": "nao", "valor": 0.0, "habilitado": False}
        if valor_flag > 0:
            return {"modo": "sim", "valor": float(valor_flag), "habilitado": True}
        return {"modo": "sim", "valor": 0.0, "habilitado": True}

    def _fetch_defeitos_e_pagamento_data(self, codigo: str, tipo_servico: str, finalizado_id: int | None, envio_id: int | None):
        """Versão 'somente consulta' de _carregar_defeitos_e_pagamento."""
        total_def = 0

        # Defeitos do fluxo novo
        try:
            r = _select_one("""
                SELECT cf.qtd_defeito_pp, cf.qtd_defeito_p, cf.qtd_defeito_m, cf.qtd_defeito_g,
                       cf.qtd_defeito_gg, cf.qtd_defeito_g1, cf.qtd_defeito_g2, cf.qtd_defeito_g3
                  FROM cortes_finalizados cf
                 WHERE cf.codigo = %s
              ORDER BY cf.id DESC LIMIT 1
            """, (codigo,))
            if r:
                total_def = sum(int(x or 0) for x in r)
        except Exception:
            pass

        if total_def <= 0 and envio_id and _table_exists("controle_retorno_cortes"):
            try:
                r_def = _select_one("""
                    SELECT COALESCE(SUM(total_defeitos), 0)
                      FROM controle_retorno_cortes
                     WHERE envio_id = %s
                """, (envio_id,))
                if r_def and r_def[0] is not None:
                    total_def = int(r_def[0] or 0)
            except Exception:
                pass

        bonif = self._fetch_bonificacao_data(codigo=codigo, finalizado_id=finalizado_id, envio_id=envio_id)

        # valor peça
        try:
            valor_peca = float(self._buscar_valor_peca(codigo=codigo, finalizado_id=finalizado_id) or 0.0)
        except Exception:
            valor_peca = 0.0

        # último pagamento salvo
        ultimo = None
        try:
            p = _select_one("""
                SELECT pecas_com_defeito, valor_defeito, observacoes_defeito,
                       adiantamento, ajuda_custo, pecas_faltantes, pecas_estragadas
                  FROM pagamento_corte_acabamento
                 WHERE codigo = %s AND tipo_servico = %s
              ORDER BY id DESC LIMIT 1
            """, (codigo, tipo_servico))
            if p:
                p_def, p_vdef, p_obs, p_ad, p_aj, p_falt, p_est = p
                ultimo = {
                    "pecas_com_defeito": int(p_def or 0),
                    "valor_defeito": float(p_vdef or 0.0),
                    "observacoes_defeito": p_obs or "",
                    "adiantamento": float(p_ad or 0.0),
                    "ajuda_custo": float(p_aj or 0.0),
                    "pecas_faltantes": int(p_falt or 0),
                    "pecas_estragadas": int(p_est or 0),
                }
        except Exception:
            ultimo = None

        return {
            "total_def": int(total_def or 0),
            "bonificacao": bonif,
            "valor_peca": float(valor_peca or 0.0),
            "ultimo": ultimo,
        }

    # ===================== Apply (sempre no main thread: mexe na UI) =====================

    def _apply_dados_bancarios_vals(self, vals) -> None:
        vals = vals or ("", "", "", "", "", "")
        try:
            self.titular_entry.delete(0, "end"); self.titular_entry.insert(0, vals[0] or "")
            self.cpf_entry.delete(0, "end"); self.cpf_entry.insert(0, vals[1] or "")
            self.banco_entry.delete(0, "end"); self.banco_entry.insert(0, vals[2] or "")
            self.agencia_entry.delete(0, "end"); self.agencia_entry.insert(0, vals[3] or "")
            self.conta_entry.delete(0, "end"); self.conta_entry.insert(0, vals[4] or "")
            self.pix_entry.delete(0, "end"); self.pix_entry.insert(0, vals[5] or "")
        except Exception:
            pass

    def _apply_adiantamento_data(self, record) -> None:
        self._adiantamento_faccao_record = None
        if not record:
            try:
                self.adiantamento_registrado_valor_lbl.configure(text="R$ 0.00")
                self.adiantamento_registrado_parcelas_lbl.configure(text="0")
                self.adiantamento_registrado_saldo_lbl.configure(text="R$ 0.00")
                self.adiantamento_entry.delete(0, "end"); self.adiantamento_entry.insert(0, "0.00")
                self.adiantamento_valor_atual_entry.configure(state="normal")
                self.adiantamento_valor_atual_entry.delete(0, "end"); self.adiantamento_valor_atual_entry.insert(0, "0.00")
                self.adiantamento_valor_atual_entry.configure(state="readonly")
                self.adiantamento_desconto_entry.delete(0, "end"); self.adiantamento_desconto_entry.insert(0, "0.00")
                self.recalcular()
            except Exception:
                pass
            return

        try:
            valor = float(record.get("valor_restante", 0.0) or 0.0)
            parcelas = int(record.get("parcelas", 1) or 1)
        except Exception:
            valor = 0.0
            parcelas = 1

        self._adiantamento_faccao_record = {
            "id": record.get("id"),
            "valor_restante": valor,
            "forma_pagamento": record.get("forma_pagamento", "") or "",
            "parcelas": parcelas,
        }

        try:
            self.adiantamento_registrado_valor_lbl.configure(text=f"R$ {valor:.2f}")
            self.adiantamento_registrado_parcelas_lbl.configure(text=str(parcelas))
            self.adiantamento_registrado_saldo_lbl.configure(text=f"R$ {valor:.2f}")
            self.adiantamento_entry.delete(0, "end"); self.adiantamento_entry.insert(0, f"{valor:.2f}")
            self.adiantamento_valor_atual_entry.configure(state="normal")
            self.adiantamento_valor_atual_entry.delete(0, "end"); self.adiantamento_valor_atual_entry.insert(0, f"{valor:.2f}")
            self.adiantamento_valor_atual_entry.configure(state="readonly")
            self.adiantamento_desconto_entry.delete(0, "end"); self.adiantamento_desconto_entry.insert(0, f"{valor:.2f}")
            self.recalcular()
        except Exception:
            pass

    def _apply_defeitos_e_pagamento_data(self, data: dict) -> None:
        data = data or {}
        total_def = int(data.get("total_def", 0) or 0)
        bonif = data.get("bonificacao") or {}
        valor_peca = float(data.get("valor_peca", 0.0) or 0.0)
        ultimo = data.get("ultimo")

        try:
            # defeitos
            self.defeito_count_entry.delete(0, "end")
            self.defeito_count_entry.insert(0, str(total_def))
        except Exception:
            pass

        # bonificação
        try:
            modo = bonif.get("modo", "sim")
            self.bonif_var.set(modo)
            habil = bool(bonif.get("habilitado", True))
            val = float(bonif.get("valor", 0.0) or 0.0)
            if not habil:
                self.bonificacao_entry.configure(state="disabled")
                self.bonificacao_entry.delete(0, "end")
                self.bonificacao_entry.insert(0, "0.00")
            else:
                self.bonificacao_entry.configure(state="normal")
                self.bonificacao_entry.delete(0, "end")
                self.bonificacao_entry.insert(0, f"{val:.2f}")
        except Exception:
            pass

        # valor/peça
        try:
            self.valor_por_peca = float(valor_peca or 0.0)
            self.valor_peca_entry.configure(state="normal")
            self.valor_peca_entry.delete(0, "end")
            self.valor_peca_entry.insert(0, f"{self.valor_por_peca:.2f}")
            self.valor_peca_entry.configure(state="readonly")
        except Exception:
            pass

        # último pagamento
        if ultimo:
            try:
                if int(ultimo.get("pecas_com_defeito", 0) or 0) > 0:
                    self.defeito_count_entry.delete(0, "end")
                    self.defeito_count_entry.insert(0, str(int(ultimo.get("pecas_com_defeito", 0) or 0)))
                self.valor_defeito_entry.delete(0, "end")
                self.valor_defeito_entry.insert(0, f"{float(ultimo.get('valor_defeito', 0.0) or 0.0):.2f}")
                self.obs_defeito_text.delete("1.0", "end")
                self.obs_defeito_text.insert("1.0", ultimo.get("observacoes_defeito", "") or "")

                self.adiantamento_entry.delete(0, "end")
                self.adiantamento_entry.insert(0, f"{float(ultimo.get('adiantamento', 0.0) or 0.0):.2f}")
                self.ajuda_entry.delete(0, "end")
                self.ajuda_entry.insert(0, f"{float(ultimo.get('ajuda_custo', 0.0) or 0.0):.2f}")
                self.faltantes_entry.delete(0, "end")
                self.faltantes_entry.insert(0, str(int(ultimo.get("pecas_faltantes", 0) or 0)))
                self.estragadas_entry.delete(0, "end")
                self.estragadas_entry.insert(0, str(int(ultimo.get("pecas_estragadas", 0) or 0)))
            except Exception:
                pass

        # defaults
        try:
            for e, default in [
                (self.adiantamento_entry, "0.00"),
                (self.ajuda_entry, "0.00"),
                (self.faltantes_entry, "0"),
                (self.estragadas_entry, "0"),
                (self.valor_defeito_entry, "0.00"),
            ]:
                if not e.get().strip():
                    e.delete(0, "end")
                    e.insert(0, default)
        except Exception:
            pass

        try:
            self.recalcular()
        except Exception:
            pass

    def _finalizar_carregamento_item(self, payload: dict) -> None:
        """Callback no main thread após a thread terminar."""
        try:
            if payload.get("error"):
                messagebox.showerror("Erro", f"Falha ao carregar dados:\n{payload.get('error')}")
                return

            self._apply_defeitos_e_pagamento_data(payload.get("defeitos_pagamento"))
            self._apply_dados_bancarios_vals(payload.get("dados_bancarios"))
            self._apply_adiantamento_data(payload.get("adiantamento"))
        finally:
            self._close_loading_window()
            try:
                self._loading_active = False
            except Exception:
                pass

    def _on_select_item(self, event=None):
        def map_origem(val):
            m = {
                "Cortes a Pagar": "Finalizados",
                "Cortes Pagos": "Entradas",
                "Finalizados": "Finalizados",
                "Entradas": "Entradas",
            }
            return m.get(val, val)

        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0]).get("values", [])

        try:
            origem_raw = self.source_var.get()
        except Exception:
            origem_raw = "Finalizados"
        origem = map_origem(origem_raw)

        if origem == "Entradas":
            messagebox.showinfo("Aviso", "Este corte já foi pago.")
            return

        # evita duplo clique repetido enquanto está carregando
        if getattr(self, "_loading_active", False):
            return
        self._loading_active = True

        mapping = {
            "tipo_servico": vals[1],
            "codigo": vals[2],
            "descricao": vals[3],
            "costureira": vals[4],
        }
        self.tipo_servico_var.set(mapping["tipo_servico"])
        self.current_mapping = mapping
        try:
            self.quantidade_finalizada = int(vals[7] or 0)
        except Exception:
            self.quantidade_finalizada = 0

        # preenche identificação (rápido, sem travar)
        for k, v in mapping.items():
            if k in self.ident_entries:
                entry = self.ident_entries[k]
                entry.configure(state="normal")
                entry.delete(0, "end")
                entry.insert(0, v)
                entry.configure(state="readonly")

        data_envio = vals[5] if len(vals) > 5 else ""
        data_chegada = vals[6] if len(vals) > 6 else ""
        if hasattr(data_envio, "strftime"):
            data_envio = data_envio.strftime("%d/%m/%Y")
        if hasattr(data_chegada, "strftime"):
            data_chegada = data_chegada.strftime("%d/%m/%Y")

        self.data_envio.configure(state="normal")
        self.data_envio.delete(0, "end")
        self.data_envio.insert(0, data_envio or "")
        self.data_envio.configure(state="readonly")

        self.data_chegada.configure(state="normal")
        self.data_chegada.delete(0, "end")
        self.data_chegada.insert(0, data_chegada or "")
        self.data_chegada.configure(state="readonly")

        self.quant_final_entry.configure(state="normal")
        self.quant_final_entry.delete(0, "end")
        self.quant_final_entry.insert(0, str(self.quantidade_finalizada))
        self.quant_final_entry.configure(state="readonly")

        # mostra loading e carrega em thread
        self._show_loading_window("Carregando dados...")

        def worker():
            try:
                try:
                    corte_id = int(vals[0])
                except Exception:
                    corte_id = 0

                codigo = mapping.get("codigo")
                tipo_servico = mapping.get("tipo_servico")
                finalizado_id = corte_id or None

                corte_id_origem = self._buscar_corte_id_origem(finalizado_id)
                envio_id = self._buscar_envio_id(finalizado_id=finalizado_id, codigo=codigo)

                defeitos_pagamento = self._fetch_defeitos_e_pagamento_data(
                    codigo=codigo,
                    tipo_servico=tipo_servico,
                    finalizado_id=finalizado_id,
                    envio_id=envio_id,
                )
                dados_bancarios = self._fetch_dados_bancarios_prestador(
                    destino=mapping.get("costureira"),
                    servico=tipo_servico,
                    finalizado_id=finalizado_id,
                    codigo=codigo,
                )

                adiantamento = None
                corte_ref = corte_id_origem if corte_id_origem else finalizado_id
                if corte_ref or envio_id:
                    adiantamento = self._fetch_adiantamento_faccao_data(
                        codigo_modelo=codigo,
                        corte_id=corte_ref,
                        envio_id=envio_id,
                        prestador_nome=mapping.get("costureira"),
                    )

                payload = {
                    "defeitos_pagamento": defeitos_pagamento,
                    "dados_bancarios": dados_bancarios,
                    "adiantamento": adiantamento,
                }
            except Exception as e:
                payload = {"error": str(e)}

            # volta para o main thread
            try:
                self.after(0, lambda: self._finalizar_carregamento_item(payload))
            except Exception:
                # se a janela foi fechada no meio, só ignora
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _on_select_defeito(self, _event=None):
        """Seleciona um defeito na aba de pagamento."""
        sel = self.defeitos_tree.selection()
        if not sel:
            return
        vals = self.defeitos_tree.item(sel[0]).get("values", [])
        if not vals:
            return
        defeito_id, prestador, codigo, descricao, tamanho, qtd, data_retorno, status = vals
        self._defeito_selecionado = defeito_id

        data_envio = ""
        valor_peca = 0.0
        try:
            row = _select_one(
                "SELECT data_envio, valor_peca FROM defeitos_envios WHERE id = %s",
                (defeito_id,)
            )
            if row:
                data_envio = row[0].strftime("%d/%m/%Y") if hasattr(row[0], "strftime") else (row[0] or "")
                valor_peca = float(row[1] or 0.0)
        except Exception:
            pass

        self.tipo_servico_var.set("Defeito")
        self.current_mapping = {
            "tipo_servico": "Defeito",
            "codigo": codigo,
            "descricao": descricao,
            "costureira": prestador,
        }

        for k, v in self.current_mapping.items():
            if k in self.ident_entries:
                entry = self.ident_entries[k]
                entry.configure(state="normal")
                entry.delete(0, "end")
                entry.insert(0, v or "")
                entry.configure(state="readonly")

        self.data_envio.configure(state="normal")
        self.data_envio.delete(0, "end")
        self.data_envio.insert(0, data_envio or "")
        self.data_envio.configure(state="readonly")

        self.data_chegada.configure(state="normal")
        self.data_chegada.delete(0, "end")
        self.data_chegada.insert(0, data_retorno or "")
        self.data_chegada.configure(state="readonly")

        try:
            self.quantidade_finalizada = int(qtd or 0)
        except Exception:
            self.quantidade_finalizada = 0
        self.quant_final_entry.configure(state="normal")
        self.quant_final_entry.delete(0, "end")
        self.quant_final_entry.insert(0, str(self.quantidade_finalizada))
        self.quant_final_entry.configure(state="readonly")

        self.defeito_count_entry.delete(0, "end")
        self.defeito_count_entry.insert(0, str(self.quantidade_finalizada))
        self.valor_defeito_entry.delete(0, "end")
        self.valor_defeito_entry.insert(0, "0.00")
        self.obs_defeito_text.delete("1.0", "end")
        self.obs_defeito_text.insert("1.0", f"Retrabalho de defeito {tamanho or ''}".strip())

        self.valor_por_peca = float(valor_peca or 0.0)
        self.valor_peca_entry.configure(state="normal")
        self.valor_peca_entry.delete(0, "end")
        self.valor_peca_entry.insert(0, f"{self.valor_por_peca:.2f}")
        self.valor_peca_entry.configure(state="readonly")

        self._carregar_dados_bancarios_prestador(prestador, "Defeito")
        if not (self.titular_entry.get() or "").strip():
            self.titular_entry.insert(0, prestador or "")
        self.recalcular()

    def aplicar_desconto_adiantamento(self):
        if not self._adiantamento_faccao_record:
            messagebox.showwarning("Aviso", "Nenhum adiantamento carregado para descontar.")
            return
        try:
            desconto = float((self.adiantamento_desconto_entry.get() or "0").replace(",", "."))
        except Exception:
            messagebox.showwarning("Erro", "Valor de desconto inválido.")
            return
        if desconto <= 0:
            messagebox.showwarning("Aviso", "Informe um valor maior que zero para descontar.")
            return

        restante = float(self._adiantamento_faccao_record.get("valor_restante", 0.0) or 0)
        parcelas_atual = int(self._adiantamento_faccao_record.get("parcelas", 0) or 0)

        if desconto > restante:
            messagebox.showwarning("Aviso", f"Desconto ({desconto:.2f}) maior que o saldo ({restante:.2f}).")
            return

        valor_parcela = (restante / parcelas_atual) if parcelas_atual > 0 else restante
        novo_saldo = restante - desconto
        if desconto >= restante:
            novo_parcelas = 0
        else:
            parcelas_descontadas = int(desconto // valor_parcela) if valor_parcela > 0 else 0
            novo_parcelas = max(parcelas_atual - parcelas_descontadas, 0)

        try:
            _exec("UPDATE adiantamento_faccao SET valor=%s, parcelas=%s WHERE id=%s",
                  (novo_saldo, novo_parcelas, self._adiantamento_faccao_record["id"]))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao aplicar desconto no adiantamento: {e}")
            return

        self._adiantamento_faccao_record["valor_restante"] = novo_saldo
        self._adiantamento_faccao_record["parcelas"] = novo_parcelas
        self.adiantamento_registrado_saldo_lbl.configure(text=f"R$ {novo_saldo:.2f}")
        self.adiantamento_registrado_parcelas_lbl.configure(text=str(novo_parcelas))
        self.adiantamento_entry.delete(0, "end")
        self.adiantamento_entry.insert(0, f"{desconto:.2f}")
        self.adiantamento_valor_atual_entry.configure(state="normal")
        self.adiantamento_valor_atual_entry.delete(0, "end")
        self.adiantamento_valor_atual_entry.insert(0, f"{novo_saldo:.2f}")
        self.adiantamento_valor_atual_entry.configure(state="readonly")
        self.adiantamento_desconto_entry.delete(0, "end")
        self.adiantamento_desconto_entry.insert(0, f"{novo_saldo:.2f}")
        self.recalcular()
        messagebox.showinfo("Sucesso",
                            f"Descontado R$ {desconto:.2f} do adiantamento. Saldo restante: R$ {novo_saldo:.2f}")

    def descontar_parcela_adiantamento(self):
        if not self._adiantamento_faccao_record:
            messagebox.showwarning("Aviso", "Nenhum adiantamento carregado para descontar.")
            return

        restante = float(self._adiantamento_faccao_record.get("valor_restante", 0.0) or 0)
        parcelas_atual = int(self._adiantamento_faccao_record.get("parcelas", 0) or 0)

        if restante <= 0 or parcelas_atual <= 0:
            messagebox.showwarning("Aviso", "Não há parcelas disponíveis para descontar.")
            return

        valor_parcela = (restante / parcelas_atual) if parcelas_atual > 0 else restante
        desconto = min(valor_parcela, restante)
        novo_saldo = restante - desconto
        novo_parcelas = max(parcelas_atual - 1, 0)

        try:
            _exec(
                "UPDATE adiantamento_faccao SET valor=%s, parcelas=%s WHERE id=%s",
                (novo_saldo, novo_parcelas, self._adiantamento_faccao_record["id"]),
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao aplicar desconto no adiantamento: {e}")
            return

        self._adiantamento_faccao_record["valor_restante"] = novo_saldo
        self._adiantamento_faccao_record["parcelas"] = novo_parcelas
        self.adiantamento_registrado_saldo_lbl.configure(text=f"R$ {novo_saldo:.2f}")
        self.adiantamento_registrado_parcelas_lbl.configure(text=str(novo_parcelas))
        self.adiantamento_entry.delete(0, "end")
        self.adiantamento_entry.insert(0, f"{desconto:.2f}")
        self.adiantamento_valor_atual_entry.configure(state="normal")
        self.adiantamento_valor_atual_entry.delete(0, "end")
        self.adiantamento_valor_atual_entry.insert(0, f"{novo_saldo:.2f}")
        self.adiantamento_valor_atual_entry.configure(state="readonly")
        self.adiantamento_desconto_entry.delete(0, "end")
        self.adiantamento_desconto_entry.insert(0, f"{novo_saldo:.2f}")
        self.recalcular()
        messagebox.showinfo(
            "Sucesso",
            f"Descontada 1 parcela de R$ {desconto:.2f}. Saldo restante: R$ {novo_saldo:.2f}",
        )

    def recalcular(self):
        def _f(entry):
            try:
                return float((entry.get() or "0").replace(",", "."))
            except:
                return 0.0

        def _i(entry):
            try:
                return int(entry.get() or 0)
            except:
                return 0

        adiantamento = _f(self.adiantamento_entry)
        ajuda = _f(self.ajuda_entry)
        faltantes = _i(self.faltantes_entry)
        estragadas = _i(self.estragadas_entry)
        pecas_com_defeito = _i(self.defeito_count_entry)
        valor_defeito = _f(self.valor_defeito_entry)

        try:
            bonificacao = _f(self.bonificacao_entry) if (
                        getattr(self, "bonif_var", None) and self.bonif_var.get() == "sim") else 0.0
        except Exception:
            bonificacao = 0.0

        desconto_pecas = (faltantes + estragadas) * self.valor_por_peca + valor_defeito
        desconto_adiant = adiantamento
        desconto = desconto_pecas + desconto_adiant
        base = self.quantidade_finalizada * self.valor_por_peca
        total = base + ajuda + bonificacao - desconto

        for ent, val in [(self.base_entry, base), (self.desconto_entry, desconto), (self.total_entry, total)]:
            ent.configure(state="normal");
            ent.delete(0, "end");
            ent.insert(0, f"{val:.2f}");
            ent.configure(state="readonly")
        self.total_destaque.configure(text=f"R$ {total:,.2f}")

        msg = ""
        if self.quantidade_finalizada <= 0:
            msg = "Quantidade finalizada deve ser maior que zero."
        elif self.valor_por_peca <= 0:
            msg = "Valor por peça inválido."
        elif (faltantes + estragadas) > self.quantidade_finalizada:
            msg = "Faltantes + estragadas excedem quantidade finalizada."
        self.feedback.configure(text=msg)

    def salvar_pagamento(self):
        def map_origem(val):
            m = {
                "Cortes a Pagar": "Finalizados",
                "Cortes Pagos": "Entradas",
                "Finalizados": "Finalizados",
                "Entradas": "Entradas",
            }
            return m.get(val, val)

        if getattr(self, "quantidade_finalizada", 0) <= 0 or float(getattr(self, "valor_por_peca", 0.0)) <= 0:
            messagebox.showwarning("Erro", "Finalização inválida.")
            return

        def _f(entry):
            try:
                return float((entry.get() or "0").replace(",", "."))
            except:
                return 0.0

        def _i(entry):
            try:
                return int(entry.get() or 0)
            except:
                return 0

        def _s(entry):
            try:
                return (entry.get() or "").strip()
            except:
                return ""

        # Obter valores dos campos
        adiantamento = _f(self.adiantamento_entry)
        ajuda = _f(self.ajuda_entry)
        faltantes = _i(self.faltantes_entry)
        estragadas = _i(self.estragadas_entry)
        pecas_com_defeito = _i(self.defeito_count_entry)
        valor_defeito = _f(self.valor_defeito_entry)

        try:
            bonificacao = _f(self.bonificacao_entry) if (
                    getattr(self, "bonif_var", None) and self.bonif_var.get() == "sim") else 0.0
        except Exception:
            bonificacao = 0.0

        obs_defeito = (self.obs_defeito_text.get("1.0", "end") or "").strip()

        # Dados de identificação
        tipo_servico = self.tipo_servico_var.get()
        codigo = _s(self.ident_entries.get("codigo"))
        descricao = _s(self.ident_entries.get("descricao"))
        costureira = _s(self.ident_entries.get("costureira"))
        data_envio = _s(self.data_envio)
        data_chegada = _s(self.data_chegada)

        # Dados bancários
        titular = _s(self.titular_entry)
        cpf = _s(self.cpf_entry)
        banco = _s(self.banco_entry)
        agencia = _s(self.agencia_entry)
        conta = _s(self.conta_entry)
        pix = _s(self.pix_entry)

        # Cálculos financeiros
        base = int(self.quantidade_finalizada) * float(self.valor_por_peca)
        desconto_pecas = (faltantes + estragadas) * float(self.valor_por_peca) + valor_defeito
        total = base + ajuda + bonificacao - adiantamento - desconto_pecas
        data_pag = datetime.now().strftime("%Y-%m-%d")

        # Determinar origem
        try:
            origem_lista_raw = self.source_var.get()
        except Exception:
            origem_lista_raw = "Finalizados"
        origem_lista = map_origem(origem_lista_raw)

        # Obter ID do item selecionado
        selecionado_id = None
        try:
            sel = self.tree.selection()
            if sel:
                selecionado_id = self.tree.item(sel[0]).get("values", [None])[0]
        except Exception:
            selecionado_id = None

        # Transação no banco de dados - TUDO MANUALMENTE
        conn = None
        pagamento_id = None
        recibo_data = None

        try:
            # 1. Abrir conexão
            conn = get_conn()

            # 2. Criar cursor
            cur = conn.cursor()

            # 3. Definir schema
            try:
                schema = get_schema()
                cur.execute(f"SET search_path TO {schema}")
            except Exception as e:
                print(f"DEBUG: Erro ao definir schema: {e}")

            # 4. Primeiro verificar se a tabela existe
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_schema = current_schema() 
                    AND table_name = 'pagamento_corte_acabamento'
                )
            """)
            tabela_existe = cur.fetchone()[0]

            if not tabela_existe:
                messagebox.showerror("Erro", "Tabela pagamento_corte_acabamento não existe.")
                cur.close()
                conn.close()
                return

            # 5. Preparar dados para inserção
            payload = {
                "tipo_servico": tipo_servico,
                "codigo": codigo,
                "descricao": descricao,
                "costureira": costureira,
                "data_envio": data_envio if data_envio else None,
                "data_chegada": data_chegada if data_chegada else None,
                "quantidade_finalizada": int(self.quantidade_finalizada),
                "valor_por_peca": float(self.valor_por_peca),
                "adiantamento": float(adiantamento),
                "ajuda_custo": float(ajuda),
                "pecas_faltantes": int(faltantes),
                "pecas_estragadas": int(estragadas),
                "desconto_pecas": float(desconto_pecas),
                "bonificacao": float(bonificacao),
                "total_pago": float(total),
                "titular_conta": titular if titular else None,
                "cpf": cpf if cpf else None,
                "banco": banco if banco else None,
                "agencia": agencia if agencia else None,
                "conta": conta if conta else None,
                "pix": pix if pix else None,
                "data_pagamento": data_pag,
                "pecas_com_defeito": int(pecas_com_defeito),
                "valor_defeito": float(valor_defeito),
                "observacoes_defeito": obs_defeito if obs_defeito else None,
                "estornado": False,
                "pago": True
            }
            recibo_data = {
                **payload,
                "data_pagamento_display": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "base_f": base,
                "desconto_f": desconto_pecas,
                "total_f": total
            }

            # 6. Verificar colunas existentes na tabela
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = current_schema() 
                AND table_name = 'pagamento_corte_acabamento'
            """)
            colunas_existentes = [row[0] for row in cur.fetchall()]

            # 7. Filtrar colunas que existem
            cols = [c for c in payload.keys() if c in colunas_existentes]
            vals = [payload[c] for c in cols]

            # 8. Inserir registro na tabela de pagamentos
            marcadores = ", ".join(["%s"] * len(cols))
            insert_sql = f"""
                INSERT INTO pagamento_corte_acabamento ({', '.join(cols)}) 
                VALUES ({marcadores}) 
                RETURNING id
            """

            cur.execute(insert_sql, vals)
            pagamento_id = cur.fetchone()[0]

            print(f"DEBUG: Pagamento inserido com ID: {pagamento_id}")

            # 9. Atualizar tabela de origem se houver item selecionado
            if selecionado_id:
                if origem_lista == "Finalizados":
                    # Verificar se cortes_finalizados existe
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.tables 
                            WHERE table_schema = current_schema() 
                            AND table_name = 'cortes_finalizados'
                        )
                    """)
                    tabela_cortes_existe = cur.fetchone()[0]

                    if tabela_cortes_existe:
                        # Verificar colunas disponíveis
                        cur.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_schema = current_schema() 
                            AND table_name = 'cortes_finalizados'
                        """)
                        colunas_cortes = [row[0] for row in cur.fetchall()]

                        tem_pagamento_id = 'pagamento_id' in colunas_cortes
                        tem_valor_pago = 'valor_pago' in colunas_cortes
                        tem_data_pagamento = 'data_pagamento' in colunas_cortes
                        tem_pago = 'pago' in colunas_cortes

                        # Montar UPDATE dinamicamente
                        update_parts = []
                        update_params = []

                        if tem_pago:
                            update_parts.append("pago = TRUE")

                        if tem_pagamento_id:
                            update_parts.append("pagamento_id = %s")
                            update_params.append(pagamento_id)

                        if tem_valor_pago:
                            update_parts.append("valor_pago = %s")
                            update_params.append(total)

                        if tem_data_pagamento:
                            update_parts.append("data_pagamento = %s")
                            update_params.append(data_pag)

                        if update_parts:
                            update_sql = f"""
                                UPDATE cortes_finalizados 
                                SET {', '.join(update_parts)} 
                                WHERE id = %s
                            """
                            update_params.append(selecionado_id)

                            cur.execute(update_sql, update_params)
                            print(f"DEBUG: Cortes_finalizados atualizado")

                else:  # Entradas
                    # Verificar se entrada_acabamento existe
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.tables 
                            WHERE table_schema = current_schema() 
                            AND table_name = 'entrada_acabamento'
                        )
                    """)
                    tabela_entrada_existe = cur.fetchone()[0]

                    if tabela_entrada_existe:
                        # Verificar colunas disponíveis
                        cur.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_schema = current_schema() 
                            AND table_name = 'entrada_acabamento'
                        """)
                        colunas_entrada = [row[0] for row in cur.fetchall()]

                        tem_pagamento_id = 'pagamento_id' in colunas_entrada
                        tem_valor_pago = 'valor_pago' in colunas_entrada
                        tem_data_pagamento = 'data_pagamento' in colunas_entrada
                        tem_pago = 'pago' in colunas_entrada

                        # Montar UPDATE dinamicamente
                        update_parts = []
                        update_params = []

                        if tem_pago:
                            update_parts.append("pago = TRUE")

                        if tem_pagamento_id:
                            update_parts.append("pagamento_id = %s")
                            update_params.append(pagamento_id)

                        if tem_valor_pago:
                            update_parts.append("valor_pago = %s")
                            update_params.append(total)

                        if tem_data_pagamento:
                            update_parts.append("data_pagamento = %s")
                            update_params.append(data_pag)

                        if update_parts:
                            update_sql = f"""
                                UPDATE entrada_acabamento 
                                SET {', '.join(update_parts)} 
                                WHERE id = %s
                            """
                            update_params.append(selecionado_id)

                            cur.execute(update_sql, update_params)
                            print(f"DEBUG: Entrada_acabamento atualizado")

            # 10. Commit
            conn.commit()
            print(f"DEBUG: Commit realizado com sucesso")

            # 11. Fechar cursor
            cur.close()

            # 12. Feedback ao usuário
            messagebox.showinfo("Sucesso", f"Pagamento registrado com sucesso! (ID: {pagamento_id})")

            # 13. Atualizar lista
            self.pesquisar_finalizados()

            # 14. Limpar formulário
            self.limpar_pagamento()

        except Exception as e:
            # Rollback em caso de erro
            if conn:
                try:
                    conn.rollback()
                    print(f"DEBUG: Rollback realizado devido a erro")
                except Exception:
                    pass

            # Log do erro completo
            import traceback
            error_details = traceback.format_exc()
            print(f"DEBUG: Erro completo no salvamento do pagamento:\n{error_details}")

            # Mensagem amigável ao usuário
            messagebox.showerror("Erro", f"Falha ao salvar o pagamento:\n{str(e)}")

        finally:
            # Fechar conexão
            if conn:
                try:
                    conn.close()
                    print(f"DEBUG: Conexão fechada")
                except Exception:
                    pass

        # 15. Perguntar sobre impressão do comprovante
        if pagamento_id:  # Só perguntar se o pagamento foi salvo com sucesso
            try:
                if messagebox.askyesno("Imprimir", "Deseja imprimir o comprovante agora?"):
                    self.imprimir_recibo(recibo_data)
            except Exception:
                pass

    # ===================== Outras ações (exportar/imprimir) =====================
    def exportar_csv(self):
        try:
            termo = (self.busca_entry.get() or "").strip()
        except Exception:
            termo = ""
        filtro_servico = self.filtro_servico_combo.get() if hasattr(self, "filtro_servico_combo") else "Todos"
        like = f"%{termo}%"

        rows = _select_all("""
            SELECT
                id, tipo_servico, codigo, descricao, costureira,
                data_envio, data_chegada, quantidade_finalizada,
                valor_por_peca, adiantamento, ajuda_custo, pecas_faltantes,
                pecas_estragadas, desconto_pecas, bonificacao, total_pago,
                titular_conta, cpf, banco, agencia, conta, pix, data_pagamento,
                pecas_com_defeito, valor_defeito, observacoes_defeito, estornado
              FROM pagamento_corte_acabamento
             WHERE (codigo ILIKE %s OR descricao ILIKE %s OR costureira ILIKE %s)
               AND (%s = 'Todos' OR tipo_servico = %s)
             ORDER BY COALESCE(data_pagamento, now()) DESC NULLS LAST
        """, (like, like, like, filtro_servico, filtro_servico))

        if not rows:
            messagebox.showinfo("Exportação", "Nenhum registro para exportar.")
            return

        fp = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], title="Salvar CSV")
        if not fp:
            return

        header = [
            "id", "tipo_servico", "codigo", "descricao", "costureira",
            "data_envio", "data_chegada", "quantidade_finalizada",
            "valor_por_peca", "adiantamento", "ajuda_custo", "pecas_faltantes",
            "pecas_estragadas", "desconto_pecas", "bonificacao", "total_pago",
            "titular_conta", "cpf", "banco", "agencia", "conta", "pix", "data_pagamento",
            "pecas_com_defeito", "valor_defeito", "observacoes_defeito", "estornado"
        ]
        try:
            with open(fp, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(header)
                for r in rows:
                    w.writerow([("" if v is None else v) for v in r])
            messagebox.showinfo("Exportação", "CSV exportado com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar CSV: {e}")

    def imprimir_recibo(self, recibo_data: dict | None = None):
        try:
            from reportlab.pdfgen import canvas as pdfcanvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from datetime import datetime
        except ImportError:
            messagebox.showerror("Erro", "Instale as bibliotecas necessárias (reportlab, pillow).")
            return

        def safe_str(v):
            return "" if v is None else str(v).strip()

        def to_float(v):
            try:
                if v is None or v == "":
                    return 0.0
                return float(str(v).replace(",", "."))
            except:
                return 0.0

        def fmt_money(v):
            try:
                return f"R$ {v:,.2f}"
            except:
                return "-"

        def sanitize_filename_part(s):
            invalid = '<>:"/\\|?*'
            for c in invalid:
                s = s.replace(c, "")
            return s.replace(" ", "_")

        def display_data_pag(v):
            if not v:
                return datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            v = str(v).strip()
            for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(v, fmt)
                    return dt.strftime("%d/%m/%Y %H:%M:%S") if "H" in fmt else dt.strftime("%d/%m/%Y")
                except Exception:
                    continue
            return v

        if recibo_data:
            tipo_servico = safe_str(recibo_data.get("tipo_servico"))
            codigo = safe_str(recibo_data.get("codigo"))
            descricao = safe_str(recibo_data.get("descricao"))
            costureira = safe_str(recibo_data.get("costureira"))
            data_envio = safe_str(recibo_data.get("data_envio"))
            data_chegada = safe_str(recibo_data.get("data_chegada"))

            qtd_finalizada = to_float(recibo_data.get("quantidade_finalizada"))
            valor_peca_f = to_float(recibo_data.get("valor_por_peca"))
            adiantamento_f = to_float(recibo_data.get("adiantamento"))
            ajuda_f = to_float(recibo_data.get("ajuda_custo"))
            bonificacao_f = to_float(recibo_data.get("bonificacao"))
            faltantes_f = to_float(recibo_data.get("pecas_faltantes"))
            estragadas_f = to_float(recibo_data.get("pecas_estragadas"))
            pecas_com_defeito = to_float(recibo_data.get("pecas_com_defeito"))
            valor_defeito_f = to_float(recibo_data.get("valor_defeito"))
            observacoes_defeito = safe_str(recibo_data.get("observacoes_defeito")).strip()

            base_f = to_float(recibo_data.get("base_f")) or (qtd_finalizada * valor_peca_f)
            desconto_f = to_float(recibo_data.get("desconto_f"))
            if not desconto_f:
                desconto_f = (faltantes_f + estragadas_f) * valor_peca_f + valor_defeito_f
            total_f = to_float(recibo_data.get("total_f"))
            if not total_f:
                total_f = base_f + ajuda_f + bonificacao_f - adiantamento_f - desconto_f

            titular = safe_str(recibo_data.get("titular_conta"))
            cpf = safe_str(recibo_data.get("cpf"))
            banco = safe_str(recibo_data.get("banco"))
            agencia = safe_str(recibo_data.get("agencia"))
            conta = safe_str(recibo_data.get("conta"))
            pix = safe_str(recibo_data.get("pix"))
            data_pag = display_data_pag(recibo_data.get("data_pagamento_display") or recibo_data.get("data_pagamento"))
        else:
            tipo_servico = safe_str(self.tipo_servico_var.get())
            codigo = safe_str(self.ident_entries.get("codigo").get())
            descricao = safe_str(self.ident_entries.get("descricao").get())
            costureira = safe_str(self.ident_entries.get("costureira").get())
            data_envio = safe_str(self.data_envio.get())
            data_chegada = safe_str(self.data_chegada.get())

            qtd_finalizada = to_float(self.quant_final_entry.get())
            valor_peca_f = to_float(self.valor_peca_entry.get())
            adiantamento_f = to_float(self.adiantamento_entry.get())
            ajuda_f = to_float(self.ajuda_entry.get())
            bonificacao_f = (to_float(self.bonificacao_entry.get())
                             if (getattr(self, 'bonif_var', None) and self.bonif_var.get() == 'sim') else 0.0)
            faltantes_f = to_float(self.faltantes_entry.get())
            estragadas_f = to_float(self.estragadas_entry.get())
            pecas_com_defeito = to_float(self.defeito_count_entry.get())
            valor_defeito_f = to_float(self.valor_defeito_entry.get())
            observacoes_defeito = safe_str(self.obs_defeito_text.get("1.0", "end")).strip()

            base_f = qtd_finalizada * valor_peca_f
            desconto_f = (faltantes_f + estragadas_f) * valor_peca_f + valor_defeito_f
            total_f = base_f + ajuda_f + bonificacao_f - adiantamento_f - desconto_f

            titular = safe_str(self.titular_entry.get())
            cpf = safe_str(self.cpf_entry.get())
            banco = safe_str(self.banco_entry.get())
            agencia = safe_str(self.agencia_entry.get())
            conta = safe_str(self.conta_entry.get())
            pix = safe_str(self.pix_entry.get())
            data_pag = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        nome_facacao = costureira if costureira else tipo_servico
        base_name = f"RECIBO_{tipo_servico}_{nome_facacao}_{codigo}_{descricao}"
        base_name = sanitize_filename_part(base_name.upper())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        default_name = f"{base_name}_{timestamp}.pdf"

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF", "*.pdf")],
            title="Salvar Recibo"
        )
        if not path:
            return

        try:
            c = pdfcanvas.Canvas(path, pagesize=A4)
            w, h = A4
            margin = 10 * mm
            header_h = 45

            logo_path = None
            for candidate in ("logo.jpg", "logo.png"):
                if os.path.exists(candidate):
                    logo_path = candidate
                    break

            def draw_single_receipt(y_top):
                # Barra de topo
                c.setFillColor(colors.HexColor("#1F5FA6"))
                c.rect(0, y_top - header_h, w, header_h, fill=1, stroke=0)

                title_x = margin
                if logo_path:
                    try:
                        from PIL import Image
                        img = Image.open(logo_path)
                        orig_w, orig_h = img.size
                        desired_height = 40
                        scale = desired_height / orig_h
                        logo_w = orig_w * scale
                        logo_h = desired_height
                        c.drawImage(
                            logo_path,
                            margin,
                            y_top - header_h + (header_h - logo_h) / 2,
                            width=logo_w,
                            height=logo_h,
                            preserveAspectRatio=True,
                            mask="auto",
                        )
                        title_x = margin + logo_w + 8
                    except Exception:
                        title_x = margin

                header_main = f"RECIBO - {tipo_servico.upper() if tipo_servico else ''}"
                if costureira:
                    header_main += f" - {costureira.upper()}"

                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", 16)
                c.drawString(title_x, y_top - header_h + 20, header_main)
                c.setFont("Helvetica", 9)
                c.drawString(title_x, y_top - header_h + 5, "Pagamento de Corte / Acabamento")

                y = y_top - header_h - 10

                # Identificação
                c.setFont("Helvetica-Bold", 11)
                c.setFillColor(colors.black)
                c.drawString(margin, y, "Identificação")
                y -= 14
                c.setFont("Helvetica", 8)
                qtd_display = int(qtd_finalizada) if float(qtd_finalizada).is_integer() else qtd_finalizada
                c.drawString(margin, y, f"Serviço: {tipo_servico}")
                c.drawString(margin + 200, y, f"Código: {codigo}")
                y -= 12
                c.drawString(margin, y, f"Descrição: {descricao}")
                c.drawString(margin + 200, y, f"Costureira/Empresa: {costureira}")
                y -= 12
                c.drawString(margin, y, f"Data Envio: {data_envio}")
                c.drawString(margin + 200, y, f"Data Chegada: {data_chegada}")
                y -= 10

                c.setStrokeColor(colors.HexColor("#CCCCCC"))
                c.setLineWidth(0.6)
                c.line(margin, y, w - margin, y)
                y -= 14

                # Quantidades / Valores
                c.setFont("Helvetica-Bold", 11)
                c.drawString(margin, y, "Quantidades / Valores")
                y -= 14
                c.setFont("Helvetica", 8)
                c.drawString(margin, y, f"Quantidade Finalizada: {qtd_display}")
                c.drawString(margin + 200, y, f"Valor por Peça: {fmt_money(valor_peca_f)}")
                y -= 12
                c.drawString(margin, y, f"Adiantamento: {fmt_money(adiantamento_f)}")
                c.drawString(margin + 200, y, f"Ajuda de Custo: {fmt_money(ajuda_f)}")
                y -= 12
                c.drawString(margin, y,
                             f"Peças Faltantes: {int(faltantes_f) if float(faltantes_f).is_integer() else faltantes_f}")
                c.drawString(margin + 200, y,
                             f"Peças Estragadas: {int(estragadas_f) if float(estragadas_f).is_integer() else estragadas_f}")
                y -= 12
                c.drawString(margin, y,
                             f"Peças com Defeito: {int(pecas_com_defeito) if float(pecas_com_defeito).is_integer() else pecas_com_defeito}")
                c.drawString(margin + 200, y, f"Valor Defeito: {fmt_money(valor_defeito_f)}")
                y -= 10

                c.line(margin, y, w - margin, y)
                y -= 14

                # Resumo
                c.setFont("Helvetica-Bold", 11)
                c.drawString(margin, y, "Resumo de Pagamento")
                y -= 14
                c.setFont("Helvetica", 8)
                c.drawString(margin, y, f"Pagamento Base: {fmt_money(base_f)}")
                c.drawString(margin + 200, y, f"Desconto: {fmt_money(desconto_f)}")
                y -= 12
                c.setFont("Helvetica-Bold", 9)
                c.drawString(margin, y, f"Total a Pagar: {fmt_money(total_f)}")
                y -= 16

                c.line(margin, y, w - margin, y)
                y -= 14

                # Bancários
                c.setFont("Helvetica-Bold", 11)
                c.drawString(margin, y, "Dados Bancários")
                y -= 14
                c.setFont("Helvetica", 8)
                c.drawString(margin, y, f"Titular: {titular}")
                c.drawString(margin + 200, y, f"CPF: {cpf}")
                y -= 12
                c.drawString(margin, y, f"Banco: {banco}")
                c.drawString(margin + 200, y, f"Agência: {agencia}")
                y -= 12
                c.drawString(margin, y, f"Conta: {conta}")
                c.drawString(margin + 200, y, f"PIX: {pix}")
                y -= 12

                # Observações / Data
                c.setFont("Helvetica", 8)
                c.drawString(margin, y,
                             f"Observações de Defeito: {observacoes_defeito if observacoes_defeito else '-'}")
                y -= 14
                c.drawString(margin, y, f"Data de Emissão: {data_pag}")
                y -= 30

                # Assinaturas
                sig_w = 160
                c.setFont("Helvetica", 9)
                c.drawString(margin, y, "Assinatura da Facção / Prestador:")
                c.drawString(margin + sig_w + 80, y, "Assinatura da Empresa:")
                y_line = y - 16
                c.setStrokeColor(colors.black)
                c.setLineWidth(1)
                c.line(margin, y_line, margin + sig_w, y_line)
                c.line(margin + sig_w + 80, y_line, margin + sig_w + 80 + sig_w, y_line)
                y_name = y_line - 16
                c.setFont("Helvetica", 7)
                c.drawString(margin, y_name, "Nome legível:")
                c.drawString(margin + sig_w + 80, y_name, "Nome legível:")

            # Duas vias na mesma página
            top_start = h - (margin * 0.5)
            draw_single_receipt(top_start)

            mid_y = h / 2
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.5)
            c.setDash(3, 2)
            c.line(margin, mid_y, w - margin, mid_y)
            c.setDash()

            bottom_start = mid_y - 5
            draw_single_receipt(bottom_start)

            c.showPage()
            c.save()

            # Tentar abrir
            try:
                if os.name == "nt":
                    os.startfile(path)
                else:
                    import subprocess, sys
                    if sys.platform == "darwin":
                        subprocess.run(["open", path])
                    else:
                        subprocess.run(["xdg-open", path])
            except Exception:
                pass

            messagebox.showinfo("Recibo", f"Recibo gerado em: {path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar recibo: {e}")

        # ===================== limpeza de formulário (mesmo comportamento do antigo) =====================

    def limpar_pagamento(self):
        for k in ["codigo", "descricao", "costureira"]:
            if k in self.ident_entries:
                self.ident_entries[k].configure(state="normal")
                self.ident_entries[k].delete(0, "end")
                self.ident_entries[k].configure(state="readonly")
        for e in [self.data_envio, self.data_chegada, self.quant_final_entry, self.valor_peca_entry]:
            e.configure(state="normal");
            e.delete(0, "end");
            e.configure(state="readonly")

        for e in [self.adiantamento_entry, self.ajuda_entry, self.faltantes_entry, self.estragadas_entry]:
            e.delete(0, "end")
        for e in [self.titular_entry, self.cpf_entry, self.banco_entry, self.agencia_entry, self.conta_entry,
                  self.pix_entry]:
            e.delete(0, "end")
        for entry in [self.base_entry, self.desconto_entry, self.total_entry]:
            entry.configure(state="normal");
            entry.delete(0, "end");
            entry.configure(state="readonly")

        self.defeito_count_entry.delete(0, "end")
        self.valor_defeito_entry.delete(0, "end")
        self.obs_defeito_text.delete("1.0", "end")
        self.total_destaque.configure(text="R$ 0.00")
        self.feedback.configure(text="")
        self.quantidade_finalizada = 0
        self.valor_por_peca = 0.0
        self.current_mapping = {}

        # reset bonificação
        try:
            self.bonif_var.set("nao")
            self._toggle_bonificacao()
        except Exception:
            pass

    # ===================== Execução direta =====================


if __name__ == "__main__":
    ok, msg = require_ready(['cortes_finalizados', 'pagamento_corte_acabamento'])
    if not ok:
        messagebox.showwarning("Aviso", f"Banco de dados não está pronto:\n{msg}")

    root = ctk.CTk()
    root.title("Pagamento - PostgreSQL")
    root.geometry("1600x900")


    class MockSistema:
        cor_primaria = "#3a7ebf"
        cor_secundaria = "#2b2b2b"
        cor_fundo = "#2b2b2b"
        cor_texto = "white"
        cor_borda = "#3a7ebf"
        cor_hover = "#2e4a66"
        cor_adicionar = "#3a7ebf"
        cor_imprimir = "#3a7ebf"


    app = PagamentoModernUI(root, sistema=MockSistema())
    app.pack(fill="both", expand=True)
    root.mainloop()

# 31/01/2026##
