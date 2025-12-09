# -*- coding: utf-8 -*-
"""
RELATORIO_ENVIO_DETALHADO.py (PostgreSQL)
Relatório detalhado do fluxo de cortes
"""

import TEMAS
import os
from datetime import datetime, date, timedelta
import customtkinter as ctk
import tkinter.ttk as ttk
from tkinter import messagebox, filedialog

# -------------------- Acesso ao PostgreSQL --------------------
try:
    from BANCO_DE_DADOS_PG import (
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
        tabelas_necessarias = ['controle_envio_cortes', 'entrada_acabamento', 'cortes_finalizados']
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

        ctk.CTkLabel(filt, text="De:").grid(row=0, column=0, padx=(8, 4), pady=8, sticky="e")
        ctk.CTkEntry(filt, width=120, textvariable=self.ini_var).grid(row=0, column=1, padx=4, pady=8)
        ctk.CTkLabel(filt, text="Até:").grid(row=0, column=2, padx=(8, 4), pady=8, sticky="e")
        ctk.CTkEntry(filt, width=120, textvariable=self.fim_var).grid(row=0, column=3, padx=4, pady=8)

        ctk.CTkLabel(filt, text="Buscar:").grid(row=0, column=4, padx=(8, 4), pady=8, sticky="e")
        ent = ctk.CTkEntry(filt, width=280, textvariable=self.busca_var,
                           placeholder_text="código / descrição / destino / costureira")
        ent.grid(row=0, column=5, padx=4, pady=8)
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
            cols = ("data_envio", "codigo", "descricao", "servico", "destino",
                    "pp", "p", "m", "g", "gg", "g1", "g2", "g3", "total", "pilotos", "valor_peca", "valor_total", "obs")
            headers = ["DATA", "CÓDIGO", "DESCRIÇÃO", "SERVIÇO", "DESTINO",
                       "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "TOTAL", "PILOTOS", "V.PEÇA", "V.TOTAL", "OBS"]
            widths = [110, 110, 260, 110, 140, 60, 60, 60, 60, 60, 60, 60, 60, 80, 110, 90, 100, 240]
        elif key == "ret":
            cols = ("data", "envio_id", "codigo", "descricao", "costureira", "pilotos", "aviamentos", "outros", "obs")
            headers = ["DATA", "ENVIO", "CÓDIGO", "DESCRIÇÃO", "COSTUREIRA", "PILOTOS", "AVIAMENTOS", "OUTROS", "OBS"]
            widths = [110, 80, 110, 260, 160, 80, 160, 160, 260]
        elif key == "fin":
            cols = ("data", "codigo", "descricao", "costureira",
                    "qtd_pp", "qtd_p", "qtd_m", "qtd_g", "qtd_gg", "qtd_g1", "qtd_g2", "qtd_g3",
                    "valor_peca", "status", "obs")
            headers = ["DATA", "CÓDIGO", "DESCRIÇÃO", "COSTUREIRA",
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

        ctk.CTkLabel(bar, text="Imprimir seções:").grid(row=0, column=0, padx=(0, 8), pady=(0, 8), sticky="w")
        ctk.CTkCheckBox(bar, text="Interna", variable=self.print_interna_var).grid(row=0, column=1, padx=6, pady=(0, 8))
        ctk.CTkCheckBox(bar, text="Enviados", variable=self.print_env_var).grid(row=0, column=2, padx=6, pady=(0, 8))
        ctk.CTkCheckBox(bar, text="Retorno", variable=self.print_ret_var).grid(row=0, column=3, padx=6, pady=(0, 8))
        ctk.CTkCheckBox(bar, text="Finalizados", variable=self.print_fin_var).grid(row=0, column=4, padx=6, pady=(0, 8))

        # botões
        btns = ctk.CTkFrame(self.tab_rel, fg_color=self.cor_primaria)
        btns.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))
        ctk.CTkButton(btns, text="📤 Exportar CSV (Aba atual)", command=self._export_csv).grid(row=0, column=0,
                                                                                              padx=(0, 8))
        ctk.CTkButton(btns, text="🖨️ Imprimir (seções marcadas)", command=self._report_html).grid(row=0, column=1,
                                                                                                  padx=(0, 8))

    def _fill_table(self, data):
        """Preenche as tabelas com os dados obtidos da pesquisa"""
        self._cache = {
            "interna": data,
            "env": data,
            "ret": data,
            "fin": data,
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
        for row in data:
            # Tabela Interna
            if hasattr(self, "tree_int"):
                values = [row.get(col, "") for col in self.cols_int]
                self.tree_int.insert("", "end", values=values)

            # Tabela Enviados
            if hasattr(self, "tree_env"):
                values = [row.get(col, "") for col in self.cols_env]
                self.tree_env.insert("", "end", values=values)

            # Tabela Retorno
            if hasattr(self, "tree_ret"):
                values = [row.get(col, "") for col in self.cols_ret]
                self.tree_ret.insert("", "end", values=values)

            # Tabela Finalizados
            if hasattr(self, "tree_fin"):
                values = [row.get(col, "") for col in self.cols_fin]
                self.tree_fin.insert("", "end", values=values)

    def _search(self):
        """Realiza a pesquisa geral do relatório"""
        try:
            schema = get_schema()

            # 1) LER COLUNAS REAIS DO BANCO
            env_cols = _columns_of("controle_envio_cortes") or []
            aca_cols = _columns_of("entrada_acabamento") or []
            fin_cols = _columns_of("cortes_finalizados") or []

            def safe_get(row: dict, key: str, default=""):
                return row[key] if key in row else default

            # 2) BUSCAR CONTROLE_ENVIO_CORTES
            env = _select_dicts(f"""
                SELECT *
                FROM {schema}.controle_envio_cortes
                ORDER BY data_envio DESC, id DESC
            """)

            # 3) BUSCAR ACABAMENTO
            try:
                aca = _select_dicts(f"""
                    SELECT *
                    FROM {schema}.entrada_acabamento
                    ORDER BY id DESC
                """)
            except Exception:
                aca = []

            # 4) BUSCAR FINALIZADOS
            try:
                fin = _select_dicts(f"""
                    SELECT *
                    FROM {schema}.cortes_finalizados
                    ORDER BY id DESC
                """)
            except Exception:
                fin = []

            # 5) JOIN
            joined = []
            for e in env:
                corte_id = safe_get(e, "corte_id")

                aca_match = next((x for x in aca if safe_get(x, "corte_id") == corte_id), {})
                fin_match = next((x for x in fin if safe_get(x, "corte_id") == corte_id), {})

                row = {
                    # Campos do banco
                    "id": safe_get(e, "id"),
                    "data_envio": safe_get(e, "data_envio"),
                    "servico": safe_get(e, "servico"),
                    "ordem_corte": safe_get(e, "ordem_corte"),
                    "codigo_corte": safe_get(e, "codigo_corte"),
                    "descricao_corte": safe_get(e, "descricao_corte"),
                    "destino": safe_get(e, "destino"),
                    "costureira": safe_get(e, "costureira"),
                    "faccao": safe_get(e, "faccao"),
                    "pp": safe_get(e, "pp", 0),
                    "p": safe_get(e, "p", 0),
                    "m": safe_get(e, "m", 0),
                    "g": safe_get(e, "g", 0),
                    "gg": safe_get(e, "gg", 0),
                    "g1": safe_get(e, "g1", 0),
                    "g2": safe_get(e, "g2", 0),
                    "g3": safe_get(e, "g3", 0),

                    # acabamento
                    "acabamento_obs": safe_get(aca_match, "observacao", ""),

                    # finalizados
                    "finalizado_data": safe_get(fin_match, "data_finalizacao", ""),

                    # Campos do layout
                    "r_pil": "",
                    "c_pil": "",
                    "r_pilot": "",
                    "c_pilot": "",
                    "r_pil2": "",
                    "c_pil2": "",
                }

                joined.append(row)

            # 6) ATUALIZA TABELA NA TELA
            self._fill_table(joined)

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
        """Gera HTML para impressão"""
        if not getattr(self, "_cache", None):
            messagebox.showinfo("Relatório", "Busque primeiro.")
            return

        # quais seções o usuário marcou
        selected = []
        if getattr(self, "print_interna_var", None) and self.print_interna_var.get():
            selected.append(("Interna", self._cache.get("interna", []), list(self.cols_int),
                             ["DATA ENV.", "CÓDIGO", "DESCRIÇÃO", "DESTINO", "PP", "P", "M", "G", "GG", "G1", "G2",
                              "G3",
                              "TOT.ENV", "PILOTOS", "V.PEÇA", "DATA RET.", "PILOTOS RET.", "DATA FIN.",
                              "PP", "P", "M", "G", "GG", "G1", "G2", "G3"]))
        if getattr(self, "print_env_var", None) and self.print_env_var.get():
            selected.append(("Enviados", self._cache.get("env", []), list(self.cols_env),
                             ["DATA", "CÓDIGO", "DESCRIÇÃO", "SERVIÇO", "DESTINO",
                              "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "TOTAL", "PILOTOS", "V.PEÇA", "V.TOTAL",
                              "OBS"]))
        if getattr(self, "print_ret_var", None) and self.print_ret_var.get():
            selected.append(("Retorno", self._cache.get("ret", []), list(self.cols_ret),
                             ["DATA", "ENVIO", "CÓDIGO", "DESCRIÇÃO", "COSTUREIRA", "PILOTOS", "AVIAMENTOS", "OUTROS",
                              "OBS"]))
        if getattr(self, "print_fin_var", None) and self.print_fin_var.get():
            selected.append(("Finalizados", self._cache.get("fin", []), list(self.cols_fin),
                             ["DATA", "CÓDIGO", "DESCRIÇÃO", "COSTUREIRA",
                              "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "V.PEÇA", "STATUS", "OBS"]))

        if not selected:
            messagebox.showwarning("Relatório", "Selecione pelo menos uma seção para imprimir.")
            return

        from tempfile import gettempdir
        import base64

        filtros = self._cache["filtros"]
        ini, fim, termo = filtros["ini"], filtros["fim"], filtros["termo"]
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        out = os.path.join(gettempdir(), f"relatorio_envio_detalhado_{ini}_a_{fim}.html")

        # carrega logo.jpg
        base_dir = os.path.dirname(__file__)
        logo_path = os.path.join(base_dir, "logo.jpg")
        logo_data_uri = ""
        try:
            if os.path.isfile(logo_path):
                with open(logo_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                logo_data_uri = f"data:image/jpeg;base64,{b64}"
        except Exception:
            logo_data_uri = ""

        # CSS
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
          @page {{ size: A4; margin: 14mm; }}
          body {{ background:var(--bg); color:var(--fg); font:12px/1.5 "Segoe UI", Arial, Helvetica, sans-serif; }}
          header {{ display:flex; align-items:center; gap:12px; padding:10px 12px; background:var(--pri); color:#fff; border-bottom:2px solid var(--acc); }}
          header .t {{ font-weight:700; font-size:18px }}
          header .m {{ margin-left:auto; opacity:.9 }}
          header img.logo {{ height:32px; border-radius:4px; }}
          h2 {{ margin:16px 0 8px; border-bottom:1px solid var(--brd); padding-bottom:6px; }}
          .k {{ margin:6px 0 12px; font-size:12px; opacity:.85 }}
          table {{ width:100%; border-collapse:collapse; margin:8px 0 16px; }}
          thead th {{ position:sticky; top:0; background:var(--pri); color:#fff; padding:8px; text-align:left; }}
          td, th {{ border:1px solid var(--brd); padding:7px 8px; }}
          tbody tr:nth-child(even) td {{ background:rgba(255,255,255,.04); }}
          td.num {{ text-align:right; }}
          .break {{ page-break-after: always; }}

          /* IMPRESSÃO */
          @media print {{
            body, .wrap {{ background:#fff !important; color:#000 !important;
                           -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            header {{ background:#fff !important; color:#000 !important; border-bottom:2px solid #000 !important; }}
            header .t, header .m {{ color:#000 !important; }}
            h2 {{ color:#000 !important; border-color:#000 !important; }}
            .k {{ color:#000 !important; opacity:1 !important; }}
            td, th {{ color:#000 !important; }}
            thead th {{ background:#e6e6e6 !important; color:#000 !important; }}
            tbody tr:nth-child(even) td {{ background:#f7f7f7 !important; }}
          }}
        </style>
        """

        def table_html(rows, cols, headers):
            if not rows:
                return "<div class='k'>Sem dados nesta seção.</div>"
            th = "".join(f"<th>{h}</th>" for h in headers)
            body = []
            for r in rows:
                tds = []
                for c in cols:
                    v = r.get(c, "")
                    if isinstance(v, (datetime, date)):
                        v = v.strftime("%Y-%m-%d")
                    cls = "num" if isinstance(v, (int, float)) else ""
                    tds.append(f"<td class='{cls}'>{v}</td>")
                body.append("<tr>" + "".join(tds) + "</tr>")
            return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(body)}</tbody></table>"

        sections_html = []
        sections_html.append(
            f"<div class='k'>Período: <b>{ini}</b> a <b>{fim}</b> &nbsp;•&nbsp; Busca: <b>{termo or '-'}</b></div>")
        for idx, (titulo, data, cols, headers) in enumerate(selected, start=1):
            sections_html.append(f"<h2>{titulo}</h2>")
            sections_html.append(table_html(data, cols, headers))
            if idx != len(selected):
                sections_html.append("<div class='break'></div>")

        logo_img = f"<img class='logo' src='{logo_data_uri}' alt='logo'>" if logo_data_uri else ""

        html = f"""<!doctype html>
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
      <div class="m">Gerado em {now}</div>
    </header>
    <div class="wrap">
      {''.join(sections_html)}
    </div>
    <script>setTimeout(function(){{window.print();}}, 400);</script>
    </body>
    </html>"""

        try:
            with open(out, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as e:
            messagebox.showerror("Relatório", f"Falha ao gravar arquivo:\n{e}")
            return

        try:
            # tenta abrir no Windows primeiro
            os.startfile(out)
        except Exception:
            import webbrowser
            webbrowser.open_new_tab("file://" + out)

        messagebox.showinfo("Relatório", f"Relatório gerado:\n{out}")


# Teste isolado
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.geometry("1280x720")
    app = RelatorioEnvioDetalhado(root)
    app.pack(fill="both", expand=True)
    root.mainloop()