# -*- coding: utf-8 -*-
"""
RELATORIO_ENVIO_DETALHADO.py (PostgreSQL)
Relatório detalhado do fluxo de cortes
"""

from PAGINAS_DO_SISTEMA import TEMAS
import os
from datetime import datetime, date, timedelta
import customtkinter as ctk
import tkinter.ttk as ttk
from tkinter import messagebox, filedialog

# -------------------- Acesso ao PostgreSQL --------------------
try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import (
        get_conn,
        get_schema,
        require_ready,
        table_exists,
    )

    _pg_error = None
except Exception as _err:
    _pg_error = _err


    def get_conn():
        raise RuntimeError(f"Módulo BANCO_DE_DADOS_PG indisponível: {_pg_error}")


    def get_schema():
        return "opera"


    def require_ready(essentials=None):
        return False, f"Módulo BANCO_DE_DADOS_PG indisponível: {_pg_error}"


    def table_exists(table: str, schema: str = None) -> bool:
        return True


# -------------------- Helpers de execução SQL --------------------
def _with_search_path(cur):
    """Garante que estamos usando o schema configurado"""
    try:
        cur.execute(f"SET LOCAL search_path = {get_schema()};")
    except Exception:
        pass


def _select_dicts(sql: str, params=()):
    """Executa SQL e retorna lista de dicts"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        _with_search_path(cur)
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description] if cur.description else []
        out = []
        for row in cur.fetchall():
            out.append({c: v for c, v in zip(cols, row)})
        return out
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _select_one(sql: str, params=()):
    rows = _select_dicts(sql, params)
    return rows[0] if rows else None


def _columns_of(table: str):
    """Lista nomes de colunas de uma tabela"""
    rows = _select_dicts("""
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = %s
         ORDER BY ordinal_position
    """, (table,))
    return [r["column_name"].lower() for r in rows]


# -------------------- Utilidades de data --------------------
def _dt(s: str) -> str:
    """Normaliza data para 'YYYY-MM-DD'"""
    if not s:
        return ""
    s = s.strip()
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        pass
    try:
        return datetime.strptime(s[:10], "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        return s[:10]


def _normalize_date_sql(col: str) -> str:
    """Converte coluna para texto antes de aplicar regex para data"""
    return f"""
    CASE
      WHEN {col} IS NULL THEN NULL
      WHEN ({col}::text) ~ '^\\d{{2}}/\\d{{2}}/\\d{{4}}' THEN 
           to_date(substring({col}::text from '^(\\d{{2}}/\\d{{2}}/\\d{{4}})'), 'DD/MM/YYYY')
      WHEN ({col}::text) ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}' THEN 
           to_date(substring({col}::text from '^(\\d{{4}}-\\d{{2}}-\\d{{2}})'), 'YYYY-MM-DD')
      ELSE NULL
    END
    """.strip()


# -------------------- Descoberta dinâmica de colunas --------------------
def _pick(cols: list[str], *cands) -> str | None:
    """Retorna o primeiro nome de coluna existente"""
    cl = [c.lower() for c in cols]
    for c in cands:
        if c and c.lower() in cl:
            return c
    return None


def _has(cols: list[str], name: str) -> bool:
    return name.lower() in cols


def _sizes_sum_expr(cols: list[str], prefix=""):
    """Cria expressão SQL somando os tamanhos existentes"""
    parts = []
    for k in ("pp", "p", "m", "g", "gg", "g1", "g2", "g3"):
        if _has(cols, f"{prefix}{k}"):
            parts.append(f"COALESCE({prefix}{k},0)")
        elif _has(cols, f"qtd_{k}"):
            parts.append(f"COALESCE(qtd_{k},0)")
    return " + ".join(parts) if parts else "0"


# -------------------- Página --------------------
class RelatorioEnvioDetalhado(ctk.CTkFrame):
    PAGE_TITLE = "Relatório Detalhado — Envio de Cortes"

    def __init__(self, parent, host=None):
        super().__init__(parent)
        self.host = host

        # ✅ CORREÇÃO: Obter cores do host de forma robusta
        self._definir_cores_do_tema(host)

        # Validação do banco
        ok, msg = require_ready()
        if not ok:
            messagebox.showwarning("Aviso", f"Banco de dados não está pronto:\n{msg}\nLeitura pode falhar.")

        # Verificação das tabelas
        schema = get_schema()
        tabelas_necessarias = ['envios_cortes', 'controle_retorno_cortes', 'retorno_detalhes_tamanho', 'cortes_finalizados']
        tabelas_faltando = []
        for tabela in tabelas_necessarias:
            try:
                if not table_exists(tabela, schema):
                    tabelas_faltando.append(tabela)
            except Exception:
                tabelas_faltando.append(tabela)

        if tabelas_faltando:
            messagebox.showwarning("Aviso",
                                   f"Algumas tabelas necessárias não foram encontradas:\n"
                                   f"{', '.join(tabelas_faltando)}\n"
                                   f"Alguns relatórios podem não funcionar corretamente.")

        self._build_ui()
        self._apply_theme_to_ui()
        self._search()

    def _definir_cores_do_tema(self, host):
        """Define as cores do tema de forma robusta"""
        if host and hasattr(host, 'cor_fundo'):
            # Usar cores do host
            self.cor_fundo = host.cor_fundo
            self.cor_primaria = host.cor_primaria
            self.cor_secundaria = host.cor_secundaria
            self.cor_terciaria = getattr(host, 'cor_terciaria', host.cor_secundaria)
            self.cor_texto = host.cor_texto
            self.cor_destaque = host.cor_destaque
            self.cor_hover = getattr(host, 'cor_hover', host.cor_destaque)
            self.cor_borda = getattr(host, 'cor_borda', host.cor_secundaria)
        else:
            # Cores padrão
            self.cor_fundo = "#1e1e1e"
            self.cor_primaria = "#2d2d30"
            self.cor_secundaria = "#3e3e42"
            self.cor_terciaria = "#252526"
            self.cor_texto = "#cccccc"
            self.cor_destaque = "#007acc"
            self.cor_hover = "#4a4a4a"
            self.cor_borda = "#404040"

    def atualizar_tema(self):
        """Método simples para atualizar tema quando chamado pelo menu"""
        try:
            if self.host and hasattr(self.host, 'cor_fundo'):
                self._definir_cores_do_tema(self.host)
                self._apply_theme_to_ui()
                print("✅ Tema atualizado no relatório")
        except Exception as e:
            print(f"Erro ao atualizar tema: {e}")

    def _apply_theme_to_ui(self):
        """Aplica o tema personalizado na interface"""
        try:
            # Configurar appearance mode
            ctk.set_appearance_mode("dark")

            # Aplicar tema ao frame principal
            self.configure(fg_color=self.cor_fundo)

            # Aplicar tema recursivamente
            self._aplicar_tema_widgets(self)

        except Exception as e:
            print(f"Erro ao aplicar tema na UI: {e}")

    def _aplicar_tema_widgets(self, widget):
        """Aplica tema recursivamente nos widgets"""
        try:
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=self.cor_texto)
            elif isinstance(widget, ctk.CTkButton):
                widget.configure(
                    fg_color=self.cor_destaque,
                    hover_color=self.cor_hover,
                    text_color=self.cor_texto,
                    border_color=self.cor_borda
                )
            elif isinstance(widget, ctk.CTkEntry):
                widget.configure(
                    fg_color=self.cor_secundaria,
                    border_color=self.cor_borda,
                    text_color=self.cor_texto,
                    placeholder_text_color="#9ca3af"
                )
            elif isinstance(widget, ctk.CTkFrame):
                widget.configure(
                    fg_color=self.cor_primaria,
                    border_color=self.cor_borda
                )
            elif isinstance(widget, ttk.Treeview):
                self._aplicar_tema_treeview(widget)

            # Processar filhos
            for child in widget.winfo_children():
                self._aplicar_tema_widgets(child)

        except Exception:
            pass

    def _aplicar_tema_treeview(self, tree):
        """Aplica tema ao treeview ttk"""
        try:
            style = ttk.Style()
            style.theme_use('default')

            # Configurar estilo principal
            style.configure("Treeview",
                            background=self.cor_secundaria,
                            foreground=self.cor_texto,
                            fieldbackground=self.cor_secundaria,
                            borderwidth=1,
                            rowheight=25)

            # Configurar cabeçalhos
            style.configure("Treeview.Heading",
                            background=self.cor_primaria,
                            foreground=self.cor_texto,
                            relief="raised",
                            borderwidth=1,
                            font=('Arial', 10, 'bold'))

            # Configurar seleção
            style.map("Treeview",
                      background=[('selected', self.cor_destaque)],
                      foreground=[('selected', self.cor_texto)])

        except Exception as e:
            print(f"Erro ao aplicar tema treeview: {e}")

    def _build_ui(self):
        """Constrói a interface do usuário"""
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Frame do topo
        top = ctk.CTkFrame(self, corner_radius=0, fg_color=self.cor_primaria)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text=self.PAGE_TITLE, font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=self.cor_texto).grid(row=0, column=0, padx=16, pady=10, sticky="w")

        # Frame de filtros
        filt = ctk.CTkFrame(self, fg_color=self.cor_secundaria)
        filt.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 4))
        for i in range(10):
            filt.grid_columnconfigure(i, weight=0)
        filt.grid_columnconfigure(9, weight=1)

        def _first_day(d: date): return d.replace(day=1)

        def _last_day(d: date):
            nd = d.replace(day=28) + timedelta(days=4)
            return nd - timedelta(days=nd.day)

        hoje = date.today()
        self.ini_var = ctk.StringVar(value=_first_day(hoje).strftime("%Y-%m-%d"))
        self.fim_var = ctk.StringVar(value=_last_day(hoje).strftime("%Y-%m-%d"))
        self.busca_var = ctk.StringVar(value="")
        self.periodo_var = ctk.StringVar(value="Este mês")

        ctk.CTkLabel(filt, text="De:").grid(row=0, column=0, padx=(8, 4), pady=8, sticky="e")
        ctk.CTkEntry(filt, width=120, textvariable=self.ini_var).grid(row=0, column=1, padx=4, pady=8)
        ctk.CTkLabel(filt, text="Até:").grid(row=0, column=2, padx=(8, 4), pady=8, sticky="e")
        ctk.CTkEntry(filt, width=120, textvariable=self.fim_var).grid(row=0, column=3, padx=4, pady=8)

        ctk.CTkLabel(filt, text="Período:").grid(row=0, column=4, padx=(8, 4), pady=8, sticky="e")
        periodo_menu = ctk.CTkOptionMenu(
            filt,
            values=["Este mês", "Últimos 30 dias", "Todos os períodos"],
            variable=self.periodo_var,
            command=lambda _: self._apply_periodo()
        )
        periodo_menu.grid(row=0, column=5, padx=4, pady=8)

        ctk.CTkLabel(filt, text="Buscar:").grid(row=0, column=6, padx=(8, 4), pady=8, sticky="e")
        ent = ctk.CTkEntry(filt, width=280, textvariable=self.busca_var,
                           placeholder_text="código / descrição / destino / prestador")
        ent.grid(row=0, column=7, padx=4, pady=8)
        ent.bind("<Return>", lambda e: self._search())

        ctk.CTkButton(filt, text="🔍 Buscar", width=120, command=self._search).grid(
            row=0, column=8, padx=8, pady=8, sticky="e"
        )

        # Abas
        tabs = ctk.CTkTabview(self)
        tabs.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        self.tab_interna = tabs.add("Interna")
        self.tab_env = tabs.add("Enviados")
        self.tab_ret = tabs.add("Retorno")
        self.tab_fin = tabs.add("Finalizados")
        self.tab_rel = tabs.add("Relatório")

        # Tabelas
        self._build_table(self.tab_interna, "int")
        self._build_table(self.tab_env, "env")
        self._build_table(self.tab_ret, "ret")
        self._build_table(self.tab_fin, "fin")

        # Relatório
        box_rel = ctk.CTkFrame(self.tab_rel, fg_color=self.cor_primaria)
        box_rel.grid(row=0, column=0, sticky="nw", padx=10, pady=10)
        ctk.CTkButton(box_rel, text="📤 Exportar CSV (Aba atual)", command=self._export_csv).grid(row=0, column=0,
                                                                                                 padx=6, pady=6)
        ctk.CTkButton(box_rel, text="🖨️ Relatório HTML", command=self._report_html).grid(row=0, column=1, padx=6,
                                                                                         pady=6)

        self._build_report_controls()

    def _build_table(self, parent, key):
        """Constrói uma tabela"""
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        wrap = ctk.CTkFrame(parent, fg_color=self.cor_fundo)
        wrap.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)

        if key == "env":
            cols = ("envio_id", "data_envio", "hora_envio", "codigo", "descricao", "servico", "destino",
                    "pp", "p", "m", "g", "gg", "g1", "g2", "g3", "total", "pilotos", "valor_peca", "valor_total", "obs")
            headers = ["ENVIO", "DATA", "HORA", "CÓDIGO", "DESCRIÇÃO", "SERVIÇO", "DESTINO",
                       "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "TOTAL", "PILOTOS", "V.PEÇA", "V.TOTAL", "OBS"]
            widths = [80, 110, 80, 110, 260, 110, 140, 60, 60, 60, 60, 60, 60, 60, 60, 80, 110, 90, 100, 240]
        elif key == "ret":
            cols = ("retorno_id", "envio_id", "data", "hora", "codigo", "descricao", "prestador",
                    "pp", "p", "m", "g", "gg", "g1", "g2", "g3",
                    "pilotos", "aviamentos", "outros", "obs")
            headers = ["RETORNO", "ENVIO", "DATA", "HORA", "CÓDIGO", "DESCRIÇÃO", "PRESTADOR",
                       "PP", "P", "M", "G", "GG", "G1", "G2", "G3",
                       "PILOTOS", "AVIAMENTOS", "OUTROS", "OBS"]
            widths = [90, 80, 110, 80, 110, 240, 160, 60, 60, 60, 60, 60, 60, 60, 60, 80, 160, 160, 240]
        elif key == "fin":
            cols = ("data", "codigo", "descricao", "prestador",
                    "qtd_pp", "qtd_p", "qtd_m", "qtd_g", "qtd_gg", "qtd_g1", "qtd_g2", "qtd_g3",
                    "valor_peca", "status", "obs")
            headers = ["DATA", "CÓDIGO", "DESCRIÇÃO", "PRESTADOR",
                       "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "V.PEÇA", "STATUS", "OBS"]
            widths = [110, 110, 260, 160, 60, 60, 60, 60, 60, 60, 60, 60, 90, 110, 260]
        elif key == "int":
            cols = ("data_envio", "codigo", "descricao", "destino", "pp", "p", "m", "g", "gg", "g1", "g2", "g3",
                    "total_env", "pilotos_env", "valor_peca_env",
                    "data_retorno", "pilotos_ret",
                    "data_final", "pp_fin", "p_fin", "m_fin", "g_fin", "gg_fin", "g1_fin", "g2_fin", "g3_fin")
            headers = ["DATA ENV.", "CÓDIGO", "DESCRIÇÃO", "DESTINO", "PP", "P", "M", "G", "GG", "G1", "G2", "G3",
                       "TOT.ENV", "PILOTOS", "V.PEÇA",
                       "DATA RET.", "PILOTOS RET.",
                       "DATA FIN.", "PP", "P", "M", "G", "GG", "G1", "G2", "G3"]
            widths = [110, 110, 260, 140, 60, 60, 60, 60, 60, 60, 60, 60, 80, 80, 90, 110, 100, 110, 60, 60, 60, 60, 60,
                      60, 60]
        else:
            cols, headers, widths = [], [], []

        tree = ttk.Treeview(wrap, columns=cols, show="headings", height=20)
        for c, h, w in zip(cols, headers, widths):
            tree.heading(c, text=h)
            tree.column(c, width=w, anchor="center" if c not in ("descricao", "obs") else "w",
                        stretch=True if c in ("descricao", "obs") else False)
        tree.grid(row=0, column=0, sticky="nsew")
        vs = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        hs = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        setattr(self, f"tree_{key}", tree)
        setattr(self, f"cols_{key}", cols)

    def _build_report_controls(self):
        """Barra de controles da aba Relatório"""
        self.tab_rel.grid_columnconfigure(0, weight=1)
        bar = ctk.CTkFrame(self.tab_rel, fg_color=self.cor_primaria)
        bar.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        # checkboxes
        self.print_interna_var = ctk.BooleanVar(value=True)
        self.print_env_var = ctk.BooleanVar(value=True)
        self.print_ret_var = ctk.BooleanVar(value=True)
        self.print_fin_var = ctk.BooleanVar(value=True)
        self.print_landscape_var = ctk.BooleanVar(value=False)

        ctk.CTkLabel(bar, text="Imprimir seções:").grid(row=0, column=0, padx=(0, 8), pady=(0, 8), sticky="w")
        ctk.CTkCheckBox(bar, text="Interna", variable=self.print_interna_var).grid(row=0, column=1, padx=6, pady=(0, 8))
        ctk.CTkCheckBox(bar, text="Enviados", variable=self.print_env_var).grid(row=0, column=2, padx=6, pady=(0, 8))
        ctk.CTkCheckBox(bar, text="Retorno", variable=self.print_ret_var).grid(row=0, column=3, padx=6, pady=(0, 8))
        ctk.CTkCheckBox(bar, text="Finalizados", variable=self.print_fin_var).grid(row=0, column=4, padx=6, pady=(0, 8))
        ctk.CTkCheckBox(bar, text="Imprimir em paisagem", variable=self.print_landscape_var).grid(
            row=0, column=5, padx=6, pady=(0, 8)
        )

        # botões
        btns = ctk.CTkFrame(self.tab_rel, fg_color=self.cor_primaria)
        btns.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))
        ctk.CTkButton(btns, text="📤 Exportar CSV (Aba atual)", command=self._export_csv).grid(row=0, column=0,
                                                                                              padx=(0, 8))
        ctk.CTkButton(btns, text="🖨️ Imprimir (seções marcadas)", command=self._report_html).grid(row=0, column=1,
                                                                                                  padx=(0, 8))

    def _apply_periodo(self):
        hoje = date.today()
        if self.periodo_var.get() == "Todos os períodos":
            self.ini_var.set("")
            self.fim_var.set("")
            return
        if self.periodo_var.get() == "Últimos 30 dias":
            ini = hoje - timedelta(days=30)
            self.ini_var.set(ini.strftime("%Y-%m-%d"))
            self.fim_var.set(hoje.strftime("%Y-%m-%d"))
            return
        ini = hoje.replace(day=1)
        fim = (ini.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        self.ini_var.set(ini.strftime("%Y-%m-%d"))
        self.fim_var.set(fim.strftime("%Y-%m-%d"))

    def _fill_table(self, data_int, data_env, data_ret, data_fin):
        """Preenche as tabelas com os dados obtidos da pesquisa"""
        self._cache = {
            "interna": data_int,
            "env": data_env,
            "ret": data_ret,
            "fin": data_fin,
            "filtros": {
                "ini": self.ini_var.get(),
                "fim": self.fim_var.get(),
                "termo": self.busca_var.get()
            }
        }

        # Limpar todas as tabelas primeiro
        for key in ["int", "env", "ret", "fin"]:
            tree = getattr(self, f"tree_{key}", None)
            if tree:
                for item in tree.get_children():
                    tree.delete(item)

        # Preencher cada tabela com os dados apropriados
        for row in data_int:
            # Tabela Interna
            if hasattr(self, "tree_int"):
                values = [row.get(col, "") for col in self.cols_int]
                self.tree_int.insert("", "end", values=values)

        for row in data_env:
            if hasattr(self, "tree_env"):
                values = [row.get(col, "") for col in self.cols_env]
                self.tree_env.insert("", "end", values=values)

        for row in data_ret:
            if hasattr(self, "tree_ret"):
                values = [row.get(col, "") for col in self.cols_ret]
                self.tree_ret.insert("", "end", values=values)

        for row in data_fin:
            if hasattr(self, "tree_fin"):
                values = [row.get(col, "") for col in self.cols_fin]
                self.tree_fin.insert("", "end", values=values)

    def _search(self):
        """Realiza a pesquisa geral do relatório"""
        try:
            schema = get_schema()

            # 1) LER COLUNAS REAIS DO BANCO
            env_cols = _columns_of("envios_cortes") or []
            ret_cols = _columns_of("controle_retorno_cortes") or []
            ret_det_cols = _columns_of("retorno_detalhes_tamanho") or []
            fin_cols = _columns_of("cortes_finalizados") or []

            def safe_get(row: dict, key: str, default=""):
                return row[key] if key in row else default

            def _filtra_termo(row: dict, *keys):
                termo = (self.busca_var.get() or "").strip().lower()
                if not termo:
                    return True
                for k in keys:
                    val = str(row.get(k, "") or "").lower()
                    if termo in val:
                        return True
                return False

            ini = _dt(self.ini_var.get())
            fim = _dt(self.fim_var.get())
            env_date_col = _pick(env_cols, "data_envio", "data", "data_saida", "data_envio_corte")
            env_date_sql = _normalize_date_sql(env_date_col) if env_date_col else "NULL"
            date_filter = ""
            params = []
            if ini and fim and env_date_col:
                date_filter = f"WHERE {env_date_sql} BETWEEN %s AND %s"
                params.extend([ini, fim])

            # 2) BUSCAR ENVIOS
            env = _select_dicts(f"""
                SELECT *
                FROM {schema}.envios_cortes
                {date_filter}
                ORDER BY {env_date_col or 'id'} DESC
            """, params)

            prestador_lookup = {}
            try:
                prestadores = _select_dicts(f"SELECT id, nome FROM {schema}.cadastro_faccoes")
                prestador_lookup = {p["id"]: p["nome"] for p in prestadores}
            except Exception:
                prestador_lookup = {}

            # 3) BUSCAR RETORNOS (cabeçalho)
            try:
                ret = _select_dicts(f"""
                    SELECT *
                    FROM {schema}.controle_retorno_cortes
                    ORDER BY id DESC
                """)
            except Exception:
                ret = []

            # 4) BUSCAR RETORNOS (detalhes por tamanho)
            try:
                ret_det = _select_dicts(f"""
                    SELECT *
                    FROM {schema}.retorno_detalhes_tamanho
                    ORDER BY envio_id DESC
                """)
            except Exception:
                ret_det = []

            # 5) BUSCAR FINALIZADOS
            try:
                fin = _select_dicts(f"""
                    SELECT *
                    FROM {schema}.cortes_finalizados
                    ORDER BY id DESC
                """)
            except Exception:
                fin = []

            # 6) Mapeamentos
            codigo_col = _pick(env_cols, "codigo_corte", "codigo", "codigo_modelo")
            desc_col = _pick(env_cols, "descricao_corte", "descricao")
            servico_col = _pick(env_cols, "tipo_servico", "servico")
            destino_col = _pick(env_cols, "destino", "prestador", "faccao", "costureira")
            prestador_id_col = _pick(env_cols, "prestador_id")
            pilotos_col = _pick(env_cols, "total_pilotos", "pilotos", "resumo_pilotos")
            valor_total_envio_col = _pick(env_cols, "valor_total_envio", "valor_total")
            valor_peca_col = _pick(env_cols, "valor_peca", "valor_unitario")
            envio_id_col = _pick(env_cols, "id")
            hora_envio_col = _pick(env_cols, "hora_envio")
            qtd_pp_col = _pick(env_cols, "qtd_pp", "pp")
            qtd_p_col = _pick(env_cols, "qtd_p", "p")
            qtd_m_col = _pick(env_cols, "qtd_m", "m")
            qtd_g_col = _pick(env_cols, "qtd_g", "g")
            qtd_gg_col = _pick(env_cols, "qtd_gg", "gg")
            qtd_g1_col = _pick(env_cols, "qtd_g1", "g1")
            qtd_g2_col = _pick(env_cols, "qtd_g2", "g2")
            qtd_g3_col = _pick(env_cols, "qtd_g3", "g3")

            env_rows = []
            for e in env:
                prestador_nome = ""
                if prestador_id_col and safe_get(e, prestador_id_col) in prestador_lookup:
                    prestador_nome = prestador_lookup.get(safe_get(e, prestador_id_col), "")
                row = {
                    "envio_id": safe_get(e, envio_id_col, ""),
                    "data_envio": safe_get(e, env_date_col, ""),
                    "hora_envio": safe_get(e, hora_envio_col, ""),
                    "codigo": safe_get(e, codigo_col, ""),
                    "descricao": safe_get(e, desc_col, ""),
                    "servico": safe_get(e, servico_col, ""),
                    "destino": prestador_nome or safe_get(e, destino_col, ""),
                    "pp": safe_get(e, qtd_pp_col, 0),
                    "p": safe_get(e, qtd_p_col, 0),
                    "m": safe_get(e, qtd_m_col, 0),
                    "g": safe_get(e, qtd_g_col, 0),
                    "gg": safe_get(e, qtd_gg_col, 0),
                    "g1": safe_get(e, qtd_g1_col, 0),
                    "g2": safe_get(e, qtd_g2_col, 0),
                    "g3": safe_get(e, qtd_g3_col, 0),
                    "total": safe_get(e, "total_pecas", safe_get(e, "total", None)),
                    "pilotos": safe_get(e, pilotos_col, ""),
                    "valor_peca": safe_get(e, valor_peca_col, ""),
                    "valor_total": safe_get(e, valor_total_envio_col, ""),
                    "obs": safe_get(e, "observacoes", "") or safe_get(e, "observacao", "") or safe_get(e, "obs", ""),
                }
                if row["total"] in (None, ""):
                    row["total"] = (
                        safe_get(e, qtd_pp_col, 0)
                        + safe_get(e, qtd_p_col, 0)
                        + safe_get(e, qtd_m_col, 0)
                        + safe_get(e, qtd_g_col, 0)
                        + safe_get(e, qtd_gg_col, 0)
                        + safe_get(e, qtd_g1_col, 0)
                        + safe_get(e, qtd_g2_col, 0)
                        + safe_get(e, qtd_g3_col, 0)
                    )
                if not row["valor_peca"] and row["total"]:
                    try:
                        row["valor_peca"] = round(float(row["valor_total"] or 0) / float(row["total"]), 2)
                    except Exception:
                        row["valor_peca"] = ""
                if _filtra_termo(row, "codigo", "descricao", "destino", "servico"):
                    env_rows.append(row)

            ret_date_col = _pick(ret_cols, "data_chegada", "data_retorno", "data", "data_entrada")
            ret_hora_col = _pick(ret_cols, "hora_chegada", "hora_retorno", "hora")
            ret_envio_col = _pick(ret_cols, "envio_id", "corte_id")
            ret_id_col = _pick(ret_cols, "id")
            ret_pil_col = _pick(ret_cols, "resumo_piloto", "pilotos")
            ret_avi_col = _pick(ret_cols, "aviamentos_recebidos", "aviamentos")
            ret_outros_col = _pick(ret_cols, "outros_recebidos", "outros")
            ret_obs_col = _pick(ret_cols, "observacoes_gerais", "observacao", "obs")

            detalhe_por_envio = {}
            for d in ret_det:
                envio_id = safe_get(d, "envio_id")
                if envio_id not in detalhe_por_envio:
                    detalhe_por_envio[envio_id] = {"pp": 0, "p": 0, "m": 0, "g": 0, "gg": 0, "g1": 0, "g2": 0, "g3": 0}
                tam = str(safe_get(d, "tamanho", "")).upper()
                entregue = safe_get(d, "entregue", 0)
                if tam in ("PP", "P", "M", "G", "GG", "G1", "G2", "G3"):
                    key = tam.lower()
                    detalhe_por_envio[envio_id][key] = detalhe_por_envio[envio_id].get(key, 0) + entregue

            ret_rows = []
            for r in ret:
                envio_id = safe_get(r, ret_envio_col, "")
                tamanhos = detalhe_por_envio.get(envio_id, {"pp": 0, "p": 0, "m": 0, "g": 0, "gg": 0, "g1": 0, "g2": 0, "g3": 0})
                envio_match = next((x for x in env if safe_get(x, envio_id_col) == envio_id), {})
                prestador_nome = ""
                if prestador_id_col and safe_get(envio_match, prestador_id_col) in prestador_lookup:
                    prestador_nome = prestador_lookup.get(safe_get(envio_match, prestador_id_col), "")
                row = {
                    "retorno_id": safe_get(r, ret_id_col, ""),
                    "envio_id": envio_id,
                    "data": safe_get(r, ret_date_col, ""),
                    "hora": safe_get(r, ret_hora_col, ""),
                    "codigo": safe_get(envio_match, codigo_col, ""),
                    "descricao": safe_get(envio_match, desc_col, ""),
                    "prestador": prestador_nome or safe_get(envio_match, destino_col, ""),
                    "pp": tamanhos.get("pp", 0),
                    "p": tamanhos.get("p", 0),
                    "m": tamanhos.get("m", 0),
                    "g": tamanhos.get("g", 0),
                    "gg": tamanhos.get("gg", 0),
                    "g1": tamanhos.get("g1", 0),
                    "g2": tamanhos.get("g2", 0),
                    "g3": tamanhos.get("g3", 0),
                    "pilotos": safe_get(r, ret_pil_col, ""),
                    "aviamentos": safe_get(r, ret_avi_col, ""),
                    "outros": safe_get(r, ret_outros_col, ""),
                    "obs": safe_get(r, ret_obs_col, ""),
                }
                if _filtra_termo(row, "codigo", "descricao", "prestador"):
                    ret_rows.append(row)

            fin_date_col = _pick(fin_cols, "data_finalizacao", "data", "data_final")
            fin_codigo_col = _pick(fin_cols, "codigo_corte", "codigo")
            fin_desc_col = _pick(fin_cols, "descricao_corte", "descricao")
            fin_cost_col = _pick(fin_cols, "prestador", "faccao", "costureira")
            fin_valor_peca_col = _pick(fin_cols, "valor_peca", "valor_unitario")
            status_col = _pick(fin_cols, "status")
            fin_envio_col = _pick(fin_cols, "envio_id", "corte_id")

            fin_rows = []
            for f in fin:
                row = {
                    "data": safe_get(f, fin_date_col, ""),
                    "codigo": safe_get(f, fin_codigo_col, ""),
                    "descricao": safe_get(f, fin_desc_col, ""),
                    "prestador": safe_get(f, fin_cost_col, ""),
                    "qtd_pp": safe_get(f, "qtd_pp", safe_get(f, "pp", 0)),
                    "qtd_p": safe_get(f, "qtd_p", safe_get(f, "p", 0)),
                    "qtd_m": safe_get(f, "qtd_m", safe_get(f, "m", 0)),
                    "qtd_g": safe_get(f, "qtd_g", safe_get(f, "g", 0)),
                    "qtd_gg": safe_get(f, "qtd_gg", safe_get(f, "gg", 0)),
                    "qtd_g1": safe_get(f, "qtd_g1", safe_get(f, "g1", 0)),
                    "qtd_g2": safe_get(f, "qtd_g2", safe_get(f, "g2", 0)),
                    "qtd_g3": safe_get(f, "qtd_g3", safe_get(f, "g3", 0)),
                    "valor_peca": safe_get(f, fin_valor_peca_col, ""),
                    "status": safe_get(f, status_col, ""),
                    "obs": safe_get(f, "observacao", "") or safe_get(f, "obs", ""),
                }
                if _filtra_termo(row, "codigo", "descricao", "prestador"):
                    fin_rows.append(row)

            # 7) JOIN interno para a aba Interna
            int_rows = []
            for e in env:
                join_key = safe_get(e, envio_id_col)
                ret_match = next((x for x in ret if safe_get(x, ret_envio_col) == join_key), {})
                fin_match = next((x for x in fin if safe_get(x, fin_envio_col) == join_key), {})
                row = {
                    "data_envio": safe_get(e, env_date_col, ""),
                    "codigo": safe_get(e, codigo_col, ""),
                    "descricao": safe_get(e, desc_col, ""),
                    "destino": safe_get(e, destino_col, ""),
                    "pp": safe_get(e, qtd_pp_col, 0),
                    "p": safe_get(e, qtd_p_col, 0),
                    "m": safe_get(e, qtd_m_col, 0),
                    "g": safe_get(e, qtd_g_col, 0),
                    "gg": safe_get(e, qtd_gg_col, 0),
                    "g1": safe_get(e, qtd_g1_col, 0),
                    "g2": safe_get(e, qtd_g2_col, 0),
                    "g3": safe_get(e, qtd_g3_col, 0),
                    "total_env": safe_get(e, "total_pecas", safe_get(e, "total", "")),
                    "pilotos_env": safe_get(e, pilotos_col, ""),
                    "valor_peca_env": safe_get(e, valor_peca_col, ""),
                    "data_retorno": safe_get(ret_match, ret_date_col, ""),
                    "pilotos_ret": safe_get(ret_match, ret_pil_col, ""),
                    "data_final": safe_get(fin_match, fin_date_col, ""),
                    "pp_fin": safe_get(fin_match, "qtd_pp", safe_get(fin_match, "pp", 0)),
                    "p_fin": safe_get(fin_match, "qtd_p", safe_get(fin_match, "p", 0)),
                    "m_fin": safe_get(fin_match, "qtd_m", safe_get(fin_match, "m", 0)),
                    "g_fin": safe_get(fin_match, "qtd_g", safe_get(fin_match, "g", 0)),
                    "gg_fin": safe_get(fin_match, "qtd_gg", safe_get(fin_match, "gg", 0)),
                    "g1_fin": safe_get(fin_match, "qtd_g1", safe_get(fin_match, "g1", 0)),
                    "g2_fin": safe_get(fin_match, "qtd_g2", safe_get(fin_match, "g2", 0)),
                    "g3_fin": safe_get(fin_match, "qtd_g3", safe_get(fin_match, "g3", 0)),
                }
                if _filtra_termo(row, "codigo", "descricao", "destino"):
                    if row["total_env"] in (None, ""):
                        row["total_env"] = (
                            safe_get(e, qtd_pp_col, 0)
                            + safe_get(e, qtd_p_col, 0)
                            + safe_get(e, qtd_m_col, 0)
                            + safe_get(e, qtd_g_col, 0)
                            + safe_get(e, qtd_gg_col, 0)
                            + safe_get(e, qtd_g1_col, 0)
                            + safe_get(e, qtd_g2_col, 0)
                            + safe_get(e, qtd_g3_col, 0)
                        )
                    if not row["valor_peca_env"] and row["total_env"]:
                        try:
                            total_envio = safe_get(e, valor_total_envio_col, 0)
                            row["valor_peca_env"] = round(float(total_envio or 0) / float(row["total_env"]), 2)
                        except Exception:
                            row["valor_peca_env"] = ""
                    int_rows.append(row)

            # 7) ATUALIZA TABELA NA TELA
            self._fill_table(int_rows, env_rows, ret_rows, fin_rows)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na pesquisa:\n{e}")
            raise

    def _export_csv(self):
        """Exporta dados para CSV"""
        if not getattr(self, "_cache", None):
            messagebox.showinfo("Exportar", "Busque primeiro.")
            return

        # detecta aba ativa
        current = None
        if hasattr(self, "tree_int") and self.tree_int.winfo_ismapped():
            current = ("Interna", self.tree_int, self.cols_int, self._cache["interna"])
        if hasattr(self, "tree_env") and self.tree_env.winfo_ismapped():
            current = ("Enviados", self.tree_env, self.cols_env, self._cache["env"])
        if hasattr(self, "tree_ret") and self.tree_ret.winfo_ismapped():
            current = ("Retorno", self.tree_ret, self.cols_ret, self._cache["ret"])
        if hasattr(self, "tree_fin") and self.tree_fin.winfo_ismapped():
            current = ("Finalizados", self.tree_fin, self.cols_fin, self._cache["fin"])

        # fallback: interna
        if current is None:
            current = ("Interna", self.tree_int, self.cols_int, self._cache["interna"])

        nome, _, cols, data = current
        fp = filedialog.asksaveasfilename(
            title=f"Salvar CSV - {nome}",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")]
        )
        if not fp:
            return
        import csv
        try:
            with open(fp, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow([h.upper() for h in cols])
                for r in data:
                    row = []
                    for c in cols:
                        v = r.get(c, "")
                        if isinstance(v, (datetime, date)):
                            v = v.strftime("%Y-%m-%d")
                        row.append(v)
                    w.writerow(row)
            messagebox.showinfo("Exportar", f"Arquivo salvo em:\n{fp}")
        except Exception as e:
            messagebox.showerror("Exportar", f"Falha ao salvar CSV:\n{e}")

    def _report_html(self):
        """Gera HTML para impressão (corrigido e mais robusto)"""
        if not getattr(self, "_cache", None):
            messagebox.showinfo("Relatório", "Busque primeiro.")
            return

        # =========================
        # Helpers
        # =========================
        import html as _html
        import sys
        import subprocess
        from tempfile import gettempdir
        import base64
        from datetime import datetime, date

        def _safe_filename_part(s: str) -> str:
            """Evita caracteres inválidos no nome do arquivo (ex: 31/01/2026)."""
            s = str(s or "").strip()
            # troca tudo que costuma quebrar no Windows/mac
            for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', '\t']:
                s = s.replace(ch, "-")
            while "--" in s:
                s = s.replace("--", "-")
            return s.strip("-") or "sem_data"

        def _fmt_date(v):
            """Formata date/datetime em pt-BR."""
            if isinstance(v, datetime):
                return v.strftime("%d/%m/%Y %H:%M")
            if isinstance(v, date):
                return v.strftime("%d/%m/%Y")
            return v

        def _to_number_if_possible(v):
            """Se vier '123' ou '123,45' como string, converte para número (para alinhar à direita)."""
            if isinstance(v, str):
                s = v.strip()
                if not s:
                    return v
                s2 = s.replace(".", "").replace(",", ".")  # pt-BR -> float (tenta)
                # tenta int primeiro se não tiver ponto
                try:
                    if "." not in s2:
                        return int(s2)
                    return float(s2)
                except Exception:
                    return v
            return v

        def _open_file(path):
            """Abre o HTML no sistema (Windows/macOS/Linux)."""
            try:
                # Windows
                if hasattr(os, "startfile"):
                    os.startfile(path)  # type: ignore[attr-defined]
                    return True
            except Exception:
                pass

            try:
                # macOS
                if sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                    return True
                # Linux
                if sys.platform.startswith("linux"):
                    subprocess.Popen(["xdg-open", path])
                    return True
            except Exception:
                pass

            # fallback navegador
            try:
                import webbrowser
                webbrowser.open_new_tab("file://" + path)
                return True
            except Exception:
                return False

        # =========================
        # Seções selecionadas
        # =========================
        selected = []

        if getattr(self, "print_interna_var", None) and self.print_interna_var.get():
            selected.append((
                "Interna",
                self._cache.get("interna", []),
                list(self.cols_int),
                ["DATA ENV.", "CÓDIGO", "DESCRIÇÃO", "DESTINO", "PP", "P", "M", "G", "GG", "G1", "G2", "G3",
                 "TOT.ENV", "PILOTOS", "V.PEÇA", "DATA RET.", "PILOTOS RET.", "DATA FIN.",
                 "PP", "P", "M", "G", "GG", "G1", "G2", "G3"]
            ))

        if getattr(self, "print_env_var", None) and self.print_env_var.get():
            selected.append((
                "Enviados",
                self._cache.get("env", []),
                list(self.cols_env),
                ["ENVIO", "DATA", "HORA", "CÓDIGO", "DESCRIÇÃO", "SERVIÇO", "DESTINO",
                 "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "TOTAL", "PILOTOS", "V.PEÇA", "V.TOTAL", "OBS"]
            ))

        if getattr(self, "print_ret_var", None) and self.print_ret_var.get():
            selected.append((
                "Retorno",
                self._cache.get("ret", []),
                list(self.cols_ret),
                ["RETORNO", "ENVIO", "DATA", "HORA", "CÓDIGO", "DESCRIÇÃO", "PRESTADOR",
                 "PP", "P", "M", "G", "GG", "G1", "G2", "G3",
                 "PILOTOS", "AVIAMENTOS", "OUTROS", "OBS"]
            ))

        if getattr(self, "print_fin_var", None) and self.print_fin_var.get():
            selected.append((
                "Finalizados",
                self._cache.get("fin", []),
                list(self.cols_fin),
                ["DATA", "CÓDIGO", "DESCRIÇÃO", "PRESTADOR",
                 "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "V.PEÇA", "STATUS", "OBS"]
            ))

        if not selected:
            messagebox.showwarning("Relatório", "Selecione pelo menos uma seção para imprimir.")
            return

        # =========================
        # Filtros / saída
        # =========================
        filtros = self._cache.get("filtros", {}) or {}
        ini = filtros.get("ini", "")
        fim = filtros.get("fim", "")
        termo = filtros.get("termo", "")

        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        ini_safe = _safe_filename_part(ini)
        fim_safe = _safe_filename_part(fim)
        out = os.path.join(gettempdir(), f"relatorio_envio_detalhado_{ini_safe}_a_{fim_safe}.html")

        # =========================
        # Logo
        # =========================
        base_dir = os.path.dirname(__file__)
        # tenta algumas opções comuns
        logo_candidates = [
            os.path.join(base_dir, "logo.jpg"),
            os.path.join(base_dir, "logo.jpeg"),
            os.path.join(base_dir, "logo.png"),
        ]

        logo_data_uri = ""
        for lp in logo_candidates:
            try:
                if os.path.isfile(lp):
                    ext = os.path.splitext(lp)[1].lower()
                    mime = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
                    with open(lp, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("ascii")
                    logo_data_uri = f"data:{mime};base64,{b64}"
                    break
            except Exception:
                continue

        # =========================
        # CSS (mantive seu visual)
        # =========================
        orientation = "landscape" if (getattr(self, "print_landscape_var", None) and self.print_landscape_var.get()) else "portrait"

        css = f"""
        <style>
          :root {{
            --bg: {self.cor_fundo};
            --bg2:{self.cor_terciaria};
            --fg: {self.cor_texto};
            --pri:{self.cor_primaria};
            --acc:{self.cor_destaque};
            --brd:{self.cor_borda};
          }}
          @page {{ size: A4 {orientation}; margin: 14mm; }}
          body {{ background:var(--bg); color:var(--fg); font:12px/1.5 "Segoe UI", Arial, Helvetica, sans-serif; }}
          header {{ display:flex; align-items:center; gap:12px; padding:10px 12px; background:var(--pri); color:#fff; border-bottom:2px solid var(--acc); }}
          header .t {{ font-weight:700; font-size:18px }}
          header .m {{ margin-left:auto; opacity:.9 }}
          header img.logo {{ height:32px; border-radius:4px; }}
          header .controls {{ display:flex; gap:8px; align-items:center; }}
          header .controls button {{
            background: transparent;
            color: inherit;
            border: 1px solid var(--acc);
            padding: 4px 8px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
          }}
          header .controls button.primary {{
            background: var(--acc);
            color: #fff;
            border-color: var(--acc);
          }}
          header .controls button.active {{
            background: var(--acc);
            color: #fff;
          }}
          h2 {{ margin:16px 0 8px; border-bottom:1px solid var(--brd); padding-bottom:6px; }}
          .k {{ margin:6px 0 12px; font-size:12px; opacity:.85 }}
          table {{ width:100%; border-collapse:collapse; margin:8px 0 16px; }}
          thead th {{ position:sticky; top:0; background:var(--pri); color:#fff; padding:8px; text-align:left; }}
          td, th {{ border:1px solid var(--brd); padding:7px 8px; }}
          tbody tr:nth-child(even) td {{ background:rgba(255,255,255,.04); }}
          td.num {{ text-align:right; }}
          .break {{ page-break-after: always; }}

          @media print {{
            body, .wrap {{ background:#fff !important; color:#000 !important;
                           -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            header {{ background:#fff !important; color:#000 !important; border-bottom:2px solid #000 !important; }}
            header .t, header .m {{ color:#000 !important; }}
            header .controls {{ display:none; }}
            h2 {{ color:#000 !important; border-color:#000 !important; }}
            .k {{ color:#000 !important; opacity:1 !important; }}
            td, th {{ color:#000 !important; }}
            thead th {{ background:#e6e6e6 !important; color:#000 !important; }}
            tbody tr:nth-child(even) td {{ background:#f7f7f7 !important; }}
          }}
        </style>
        """

        # =========================
        # HTML de tabelas (corrigido)
        # =========================
        def table_html(rows, cols, headers):
            if not rows:
                return "<div class='k'>Sem dados nesta seção.</div>"

            # Se headers não bater com cols, usa cols como fallback para não desalinha
            if not headers or len(headers) != len(cols):
                headers_use = [str(c).upper() for c in cols]
            else:
                headers_use = headers

            th = "".join(f"<th>{_html.escape(str(h))}</th>" for h in headers_use)

            body_rows = []
            for r in rows:
                tds = []
                # r precisa ser dict; se vier tuple/list por algum motivo, não quebra
                if not isinstance(r, dict):
                    # tenta converter por ordem de cols
                    try:
                        r = {cols[i]: r[i] for i in range(min(len(cols), len(r)))}
                    except Exception:
                        r = {}

                for c in cols:
                    v = r.get(c, "")
                    v = _fmt_date(v)
                    v = _to_number_if_possible(v)

                    cls = "num" if isinstance(v, (int, float)) else ""
                    # escapa HTML para não quebrar tabela (ex: texto com < > &)
                    cell = _html.escape(str(v)) if v is not None else ""
                    tds.append(f"<td class='{cls}'>{cell}</td>")

                body_rows.append("<tr>" + "".join(tds) + "</tr>")

            return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"

        # =========================
        # Monta seções
        # =========================
        sections_html = []
        sections_html.append(
            f"<div class='k'>Período: <b>{_html.escape(str(ini) or '-')}</b> a <b>{_html.escape(str(fim) or '-')}</b>"
            f" &nbsp;•&nbsp; Busca: <b>{_html.escape(str(termo) or '-')}</b></div>"
        )

        for idx, (titulo, data, cols, headers) in enumerate(selected, start=1):
            sections_html.append(f"<h2>{_html.escape(str(titulo))}</h2>")
            sections_html.append(table_html(data, cols, headers))
            if idx != len(selected):
                sections_html.append("<div class='break'></div>")

        logo_img = f"<img class='logo' src='{logo_data_uri}' alt='logo'>" if logo_data_uri else ""
        print_controls = """
        <div class="controls">
          <button type="button" data-orient="portrait">Retrato</button>
          <button type="button" data-orient="landscape">Paisagem</button>
          <button type="button" class="primary" id="btn-print">Imprimir</button>
        </div>
        """

        html_doc = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="color-scheme" content="light">
  {css}
</head>
<body>
<header>
  {logo_img}
  <div class="t">Relatório Detalhado — Envio de Cortes</div>
  {print_controls}
  <div class="m">Gerado em {now}</div>
</header>

<div class="wrap">
  {''.join(sections_html)}
</div>

<script>
  (function() {{
    var initial = "{orientation}";
    var buttons = document.querySelectorAll('[data-orient]');
    function setOrientation(value) {{
      var style = document.getElementById('page-orientation');
      if (!style) {{
        style = document.createElement('style');
        style.id = 'page-orientation';
        document.head.appendChild(style);
      }}
      style.textContent = '@page {{ size: A4 ' + value + '; margin: 14mm; }}';
      buttons.forEach(function(btn) {{
        btn.classList.toggle('active', btn.getAttribute('data-orient') === value);
      }});
    }}
    buttons.forEach(function(btn) {{
      btn.addEventListener('click', function() {{
        setOrientation(btn.getAttribute('data-orient'));
      }});
    }});
    setOrientation(initial);

    var printBtn = document.getElementById('btn-print');
    if (printBtn) {{
      printBtn.addEventListener('click', function() {{
        window.print();
      }});
    }}
  }})();
</script>
</body>
</html>"""

        # =========================
        # Grava e abre
        # =========================
        try:
            with open(out, "w", encoding="utf-8") as f:
                f.write(html_doc)
        except Exception as e:
            messagebox.showerror("Relatório", f"Falha ao gravar arquivo:\n{e}")
            return

        opened = _open_file(out)
        if not opened:
            messagebox.showwarning("Relatório", f"Relatório gerado, mas não consegui abrir automaticamente:\n{out}")
            return

        messagebox.showinfo("Relatório", f"Relatório gerado:\n{out}")


# Teste isolado
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.geometry("1280x720")
    app = RelatorioEnvioDetalhado(root)
    app.pack(fill="both", expand=True)
    root.mainloop()

#03/02/2025

# --- Suporte trilíngue individual desta página ---
RelatorioEnvioDetalhado_TRANSLATIONS = {
    "pt_BR": {
        "title": "Relatório de Envio Detalhado",
        "Atualizar": "Atualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
    },
    "en_US": {
        "title": "Detailed Shipping Report",
        "Atualizar": "Refresh",
        "Filtrar": "Filter",
        "Limpar": "Clear",
        "Exportar": "Export",
        "Imprimir": "Print",
        "Buscar": "Search",
    },
    "es_ES": {
        "title": "Reporte Detallado de Envío",
        "Atualizar": "Actualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpiar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
    },
}


def _apply_relatorioenviodetalhado_translations(self):
    """Aplica tradução individual desta página."""
    idioma = getattr(getattr(self, "sistema", None), "idioma_atual", getattr(self, "idioma_atual", "pt_BR"))
    if idioma not in RelatorioEnvioDetalhado_TRANSLATIONS:
        idioma = "pt_BR"
    if hasattr(self, "titulo"):
        try:
            self.titulo.configure(text=RelatorioEnvioDetalhado_TRANSLATIONS[idioma]["title"])
        except Exception:
            pass


try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    RelatorioEnvioDetalhado.TRANSLATIONS = RelatorioEnvioDetalhado_TRANSLATIONS
    if not hasattr(RelatorioEnvioDetalhado, "apply_page_translations"):
        RelatorioEnvioDetalhado.apply_page_translations = _apply_relatorioenviodetalhado_translations
    attach_i18n_support(RelatorioEnvioDetalhado, RelatorioEnvioDetalhado_TRANSLATIONS)
except Exception:
    pass
# -*- coding: utf-8 -*-
"""Compatibilidade: encaminha para RELATORIO_ENVIO_DETALHADO.py."""

import importlib.util
import sys
from pathlib import Path

_target = Path(__file__).with_name("RELATORIO_ENVIO_DETALHADO.py")
_spec = importlib.util.spec_from_file_location("compat_relatorio_envio_detalhado", str(_target))
if _spec is None or _spec.loader is None:
    raise ImportError(f"Não foi possível carregar {_target}")
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

for _name in dir(_mod):
    if _name.startswith("__") and _name not in {"__all__", "__doc__"}:
        continue
    globals()[_name] = getattr(_mod, _name)

__all__ = getattr(_mod, "__all__", [n for n in globals() if not n.startswith("_")])
