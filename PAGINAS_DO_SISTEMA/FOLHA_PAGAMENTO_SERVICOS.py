# -*- coding: utf-8 -*-
"""
FOLHA_PAGAMENTO_SERVICOS.py  (versão PostgreSQL)
- Usa BANCO_DE_DADOS_PG.get_conn/get_schema/require_ready (config.json).
- NÃO cria tabelas; apenas lê.
- Filtros: período, serviço, termo (costureira/código/descrição, se existirem), incluir estornados.
- Agrega por Prestador e total geral; mantém UI e lógica original.

Requisitos de tabela (como na sua tela de pagamentos):
pagamento_corte_acabamento: costureira, tipo_servico, quantidade_finalizada, valor_por_peca,
adiantamento, ajuda_custo, bonificacao?, pecas_faltantes, pecas_estragadas, desconto_pecas,
total_pago, cpf, banco, agencia, conta, pix, data_pagamento, estornado,
pecas_com_defeito?, valor_defeito?
"""
from __future__ import annotations
import os, csv, sys, webbrowser
from datetime import datetime, date, timedelta
import customtkinter as ctk
from PAGINAS_DO_SISTEMA.TEMAS import get_contraste_texto, is_dark_color, ajustar_hover
from tkinter import ttk, messagebox, filedialog

# ---------- Cores/tema ----------
ACCENT_BLUE = "#2563eb"
CARD_BG = "#111827"
MAIN_BG = "#0d1117"
TOP_BAR_BG = "#1f2d44"
FILTER_BG = "#0b1220"

# ---------- Pastas locais (mantidas) ----------
DB_DIR = "../BANCO DE DADOS"
RELATORIO_DIR = os.path.join(DB_DIR, "RELATORIO_FOLHA_PAGAMENTO")
os.makedirs(RELATORIO_DIR, exist_ok=True)

SERVICE_FILTER_OPTIONS = [
    "Todos", "Facção", "Bordado", "Caseador", "Botões",
    "Estamparia", "Tingimento", "Outros Trabalhos"
]

# ---------- Acesso PG ----------
try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception as err:
    def get_conn():
        raise RuntimeError("BANCO_DE_DADOS_PG indisponível: " + str(err))
    def get_schema():
        return "public"
    def require_ready(essentials=None):
        return False, "Módulo de acesso não disponível"

# ---------- Helpers ----------
def _dt(s: str) -> str:
    """Normaliza para 'YYYY-MM-DD' (aceita 'DD/MM/YYYY')."""
    if not s:
        return ""
    s = s.strip()
    if "/" in s:
        try:
            d = datetime.strptime(s, "%d/%m/%Y").date()
            return d.strftime("%Y-%m-%d")
        except Exception:
            return s
    return s

def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)

def _last_day_of_month(d: date) -> date:
    nd = d.replace(day=28) + timedelta(days=4)
    return nd - timedelta(days=nd.day)

def _normalize_date_sql(col: str) -> str:
    """
    Normaliza uma coluna qualquer (date/timestamp/text/varchar) para DATE no PostgreSQL.
    - YYYY-MM-DD ou DD/MM/YYYY quando texto.
    - Tudo retorna DATE (ou NULL::date).
    """
    return f"""
    (CASE
        WHEN pg_typeof({col}) = 'date'::regtype THEN {col}::date
        WHEN pg_typeof({col}) = 'timestamp without time zone'::regtype THEN {col}::date
        WHEN pg_typeof({col}) = 'timestamp with time zone'::regtype THEN {col}::date
        WHEN pg_typeof({col}) = 'text'::regtype OR pg_typeof({col}) = 'character varying'::regtype THEN
            CASE
              WHEN {col} ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}' THEN to_date(left({col}, 10), 'YYYY-MM-DD')
              WHEN {col} ~ '^[0-9]{{2}}/[0-9]{{2}}/[0-9]{{4}}' THEN to_date(left({col}, 10), 'DD/MM/YYYY')
              ELSE NULL::date
            END
        ELSE NULL::date
     END)
    """


# =====================================================================
#                               PÁGINA
# =====================================================================
class FolhaPagamentoServicosPage(ctk.CTkFrame):
    TRANSLATIONS = {
     "pt_BR":{"page_title":"Folha de Pagamento - Serviços","from":"De:","to":"Até:","service":"Serviço:","search_label":"Buscar:","search_placeholder":"Costureira/código/descrição","include_reversed":"Incluir estornados","search":"🔍 Buscar","all":"Todos","faction":"Facção","embroidery":"Bordado","buttonhole":"Caseador","buttons":"Botões","printing":"Estamparia","dyeing":"Tingimento","other_jobs":"Outros Trabalhos","kpi_total":"Total a Pagar (R$)","kpi_base":"Base (R$)","kpi_discounts":"Descontos (R$)","kpi_help":"Ajuda/Bonificação (R$)","col_provider":"Prestador","col_cpf":"CPF","col_services":"Serviços","col_qty":"Qtd","col_base":"Base","col_discounts":"Descontos","col_help":"Ajuda/Bonif.","col_total":"Total","export_csv":"📤 Exportar CSV","report_html":"🖨️ Relatório HTML"},
     "en_US":{"page_title":"Payroll - Services","from":"From:","to":"To:","service":"Service:","search_label":"Search:","search_placeholder":"Seamstress/code/description","include_reversed":"Include reversed entries","search":"🔍 Search","all":"All","faction":"Outsource","embroidery":"Embroidery","buttonhole":"Buttonhole","buttons":"Buttons","printing":"Printing","dyeing":"Dyeing","other_jobs":"Other Jobs","kpi_total":"Total to Pay (R$)","kpi_base":"Base (R$)","kpi_discounts":"Discounts (R$)","kpi_help":"Help/Bonus (R$)","col_provider":"Provider","col_cpf":"Tax ID","col_services":"Services","col_qty":"Qty","col_base":"Base","col_discounts":"Discounts","col_help":"Help/Bonus","col_total":"Total","export_csv":"📤 Export CSV","report_html":"🖨️ HTML Report"},
     "es_ES":{"page_title":"Nómina - Servicios","from":"Desde:","to":"Hasta:","service":"Servicio:","search_label":"Buscar:","search_placeholder":"Costurera/código/descripción","include_reversed":"Incluir estornados","search":"🔍 Buscar","all":"Todos","faction":"Facción","embroidery":"Bordado","buttonhole":"Caseador","buttons":"Botones","printing":"Estampado","dyeing":"Teñido","other_jobs":"Otros Trabajos","kpi_total":"Total a Pagar (R$)","kpi_base":"Base (R$)","kpi_discounts":"Descuentos (R$)","kpi_help":"Ayuda/Bonificación (R$)","col_provider":"Prestador","col_cpf":"CPF","col_services":"Servicios","col_qty":"Cant.","col_base":"Base","col_discounts":"Descuentos","col_help":"Ayuda/Bonif.","col_total":"Total","export_csv":"📤 Exportar CSV","report_html":"🖨️ Reporte HTML"}
    }
    def _init_i18n(self):
        self.idioma_atual = getattr(self.sistema, "idioma_atual", getattr(self._host, "idioma_atual", "pt_BR"))
    def _get_text(self, key, default=None):
        lang = getattr(self, "idioma_atual", "pt_BR")
        return self.TRANSLATIONS.get(lang, {}).get(key, self.TRANSLATIONS["pt_BR"].get(key, default if default is not None else key))
    def _service_options_i18n(self):
        return [self._get_text(k) for k in ("all","faction","embroidery","buttonhole","buttons","printing","dyeing","other_jobs")]
    def refresh_texts(self):
        try: self.lbl_title.configure(text=self._get_text("page_title"))
        except Exception: pass
        for n,k in [("lbl_de","from"),("lbl_ate","to"),("lbl_servico","service"),("lbl_busca","search_label"),("est_chk","include_reversed"),("buscar_btn","search"),("btn_export_csv","export_csv"),("btn_report_html","report_html")]:
            try: getattr(self,n).configure(text=self._get_text(k))
            except Exception: pass
        for n in ("ini_entry","fim_entry"):
            try: getattr(self,n).configure(placeholder_text="YYYY-MM-DD" if self.idioma_atual=="en_US" else "AAAA-MM-DD")
            except Exception: pass
        try: self.busca_entry.configure(placeholder_text=self._get_text("search_placeholder"))
        except Exception: pass
        try:
            vals=self._service_options_i18n()
            current=self.servico_var.get()
            rev={"Todos":"all","Facção":"faction","Bordado":"embroidery","Caseador":"buttonhole","Botões":"buttons","Estamparia":"printing","Tingimento":"dyeing","Outros Trabalhos":"other_jobs","All":"all","Outsource":"faction","Embroidery":"embroidery","Buttonhole":"buttonhole","Buttons":"buttons","Printing":"printing","Dyeing":"dyeing","Other Jobs":"other_jobs","Facción":"faction","Estampado":"printing","Teñido":"dyeing"}
            self.serv_combo.configure(values=vals)
            self.servico_var.set(self._get_text(rev.get(current,"all")))
        except Exception: pass
        try:
            for col,key in [("prestador","col_provider"),("cpf","col_cpf"),("servicos","col_services"),("qtd","col_qty"),("base","col_base"),("descontos","col_discounts"),("ajudas","col_help"),("total","col_total")]:
                self.tree.heading(col, text=self._get_text(key))
        except Exception: pass
    PAGE_TITLE = "Folha de Pagamento - Serviços"

    def __init__(self, parent, host=None, sistema=None, *args, **kwargs):
        """
        parent  -> container (no menu é self.content, em teste direto é app/root)
        host    -> janela/menu que tem as cores (cor_fundo, cor_primaria, etc.)
        sistema -> instância principal do sistema (MENU_PRINCIPAL), se for passado

        Obs.: host e sistema são equivalentes para tema; sempre teremos self.sistema.
        """
        # Garante que sempre exista um "host" com tema
        self._host = host or sistema or parent
        # Garante que self.sistema exista (usado em _kpi)
        self.sistema = sistema or host or parent

        # Atualiza cores/tema a partir do host/sistema
        self._update_theme_from_host()

        # Cria o frame principal já com a cor de fundo correta
        super().__init__(parent, fg_color=self.main_bg, *args, **kwargs)

        # Aplica tema nos widgets ttk (Treeview, Scrollbar etc.)
        self._apply_ttk_theme()

        # filtros padrão: mês atual
        hoje = date.today()
        self.ini_var = ctk.StringVar(
            value=_first_day_of_month(hoje).strftime("%Y-%m-%d")
        )
        self.fim_var = ctk.StringVar(
            value=_last_day_of_month(hoje).strftime("%Y-%m-%d")
        )
        self.servico_var = ctk.StringVar(value="Todos")
        self.busca_var = ctk.StringVar(value="")
        self.incluir_estornados = ctk.BooleanVar(value=False)
        self.agrupar_por_servico = ctk.BooleanVar(value=True)

        # Monta UI e sincroniza tema
        self._init_i18n()
        self._build_ui()
        self.refresh_texts()
        self._conectar_sinal_tema()
        self._sync_theme()

        # Carrega dados iniciais
        self._search()


    # ---------- Tema & ttk ----------
    def _update_theme_from_host(self):
        self.accent_color = getattr(self._host, "cor_selecao", ACCENT_BLUE)
        self.main_bg = getattr(self._host, "cor_fundo", MAIN_BG)
        self.topbar_bg = getattr(self._host, "cor_primaria", TOP_BAR_BG)
        self.filter_bg = getattr(self._host, "cor_secundaria", FILTER_BG)
        self.card_bg = getattr(self._host, "cor_terciaria", CARD_BG)
        self.text_color = getattr(self._host, "cor_texto", "white")
        self.cor_imprimir = getattr(self._host, "cor_imprimir", self.accent_color)
        self.cor_hover = getattr(self._host, "cor_hover", None)
        self.cor_adicionar = getattr(self._host, "cor_adicionar", self.accent_color)

    def _apply_ttk_theme(self):
        try:
            style = ttk.Style()
            try: style.theme_use("clam")
            except Exception: pass
            bg_card = self.card_bg
            bg_main = self.main_bg
            fg_text = self.text_color or "white"
            accent = self.accent_color
            topbar = self.topbar_bg

            style.configure("Treeview",
                            background=bg_card, fieldbackground=bg_card, foreground=fg_text,
                            bordercolor=bg_main, borderwidth=0, rowheight=24)
            style.map("Treeview",
                      background=[("selected", accent)],
                      foreground=[("selected","white")])
            style.configure("Treeview.Heading", background=topbar, foreground="white", relief="flat")
            style.configure("Vertical.TScrollbar", background=bg_card, troughcolor=bg_main, bordercolor=bg_main)
            style.configure("TCombobox", fieldbackground=bg_card, background=bg_card, foreground=fg_text)
        except Exception:
            pass

    def _conectar_sinal_tema(self):
        try:
            if getattr(self, "_tema_binding_registrado", False): return
            top = self.winfo_toplevel()
            if top:
                top.bind("<<TemaAtualizado>>", lambda e: self._sync_theme(), add="+")
                self._tema_binding_registrado = True
        except Exception:
            pass

    def _all_children(self, parent):
        for w in parent.winfo_children():
            yield w
            try: yield from self._all_children(w)
            except Exception: pass

    def _sync_theme(self):
        try: ctk.set_appearance_mode(getattr(self._host, "modo", "Dark"))
        except Exception: pass
        try: self.configure(fg_color=self.main_bg)
        except Exception: pass
        for w in self._all_children(self):
            try:
                if isinstance(w, ctk.CTkFrame): w.configure(fg_color=self.card_bg)
                elif isinstance(w, ctk.CTkLabel): w.configure(text_color=self.text_color or "white")
                elif isinstance(w, ctk.CTkEntry): w.configure(fg_color=self.filter_bg, text_color=self.text_color or "white")
                elif isinstance(w, ctk.CTkComboBox): w.configure(fg_color=self.filter_bg, text_color=self.text_color or "white")
                elif isinstance(w, ctk.CTkTextbox): w.configure(fg_color=self.filter_bg, text_color=self.text_color or "white")
                elif isinstance(w, ctk.CTkCheckBox): w.configure(text_color=self.text_color or "white")
            except Exception: pass
        self._apply_ttk_theme()

    # ---------- UI ----------
    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Topbar
        top = ctk.CTkFrame(self, fg_color=self.topbar_bg, corner_radius=0)
        top.grid(row=0, column=0, sticky="ew")
        self.lbl_title = ctk.CTkLabel(top, text=self.PAGE_TITLE,
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="white").grid(row=0, column=0, sticky="w", padx=20, pady=8)

        # Filtros
        filt = ctk.CTkFrame(self, fg_color=self.filter_bg, corner_radius=10)
        filt.grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 6))
        for i in range(10): filt.grid_columnconfigure(i, weight=0)
        filt.grid_columnconfigure(9, weight=1)

        self.lbl_de = ctk.CTkLabel(filt, text="De:"); self.lbl_de.grid(row=0, column=0, padx=(10,4), pady=8, sticky="e")
        self.ini_entry = ctk.CTkEntry(filt, width=120, textvariable=self.ini_var, placeholder_text="AAAA-MM-DD")
        self.ini_entry.grid(row=0, column=1, padx=4, pady=8)

        self.lbl_ate = ctk.CTkLabel(filt, text="Até:"); self.lbl_ate.grid(row=0, column=2, padx=(12,4), pady=8, sticky="e")
        self.fim_entry = ctk.CTkEntry(filt, width=120, textvariable=self.fim_var, placeholder_text="AAAA-MM-DD")
        self.fim_entry.grid(row=0, column=3, padx=4, pady=8)

        self.lbl_servico = ctk.CTkLabel(filt, text="Serviço:"); self.lbl_servico.grid(row=0, column=4, padx=(12,4), pady=8, sticky="e")
        self.serv_combo = ctk.CTkComboBox(filt, values=self._service_options_i18n(), width=160, variable=self.servico_var)
        self.serv_combo.grid(row=0, column=5, padx=4, pady=8)

        self.lbl_busca = ctk.CTkLabel(filt, text="Buscar:"); self.lbl_busca.grid(row=0, column=6, padx=(12,4), pady=8, sticky="e")
        self.busca_entry = ctk.CTkEntry(filt, width=180, textvariable=self.busca_var, placeholder_text="Costureira/código/descrição")
        self.busca_entry.grid(row=0, column=7, padx=4, pady=8)
        self.busca_entry.bind("<Return>", lambda e: self._search())

        self.est_chk = ctk.CTkCheckBox(filt, text="Incluir estornados", variable=self.incluir_estornados, command=self._search)
        self.est_chk.grid(row=0, column=8, padx=(12,4), pady=8)

        self.buscar_btn = ctk.CTkButton(filt, text="🔍 Buscar", width=120, fg_color=self.accent_color,
                                        hover_color=self.cor_hover, command=self._search)
        self.buscar_btn.grid(row=0, column=9, padx=(8,10), pady=8, sticky="e")

        # Conteúdo
        content = ctk.CTkFrame(self, fg_color=self.main_bg, corner_radius=0)
        content.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        # KPIs
        kpis = ctk.CTkFrame(content, fg_color=self.card_bg, corner_radius=12)
        kpis.grid(row=0, column=0, sticky="ew", padx=4, pady=6)
        kpis.grid_columnconfigure((0,1,2,3), weight=1)
        self.kpi_total = self._kpi(kpis, 0, self._get_text("kpi_total"), "0,00")
        self.kpi_base = self._kpi(kpis, 1, self._get_text("kpi_base"), "0,00")
        self.kpi_desc = self._kpi(kpis, 2, self._get_text("kpi_discounts"), "0,00")
        self.kpi_ajuda = self._kpi(kpis, 3, self._get_text("kpi_help"), "0,00")

        # Tabela
        table_wrap = ctk.CTkFrame(content, fg_color=self.card_bg, corner_radius=12)
        table_wrap.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0,6))
        table_wrap.grid_columnconfigure(0, weight=1)
        table_wrap.grid_rowconfigure(0, weight=1)

        cols = ("prestador","cpf","servicos","qtd","base","descontos","ajudas","total","banco","agencia","conta","pix","lanc")
        headers = ["Prestador","CPF","Serviços","Qtd","Base","Descontos","Ajuda/Bonif.","Total Pago","Banco","Agência","Conta","PIX","Lanç."]
        widths = [160,100,140,60,100,100,110,110,120,90,120,140,60]
        anchors = ["w","center","center","center","e","e","e","e","w","center","center","w","center"]
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", height=18)
        for c,h,w,a in zip(cols,headers,widths,anchors):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor=a, stretch=True if c in ("prestador","servicos","pix") else False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        # Ações
        actions = ctk.CTkFrame(content, fg_color=self.main_bg)
        actions.grid(row=2, column=0, sticky="e", padx=4, pady=6)
        ctk.CTkButton(actions, text="📤 Exportar CSV", width=140,
                      fg_color=self.cor_imprimir, hover_color=self.cor_hover, command=self._export_csv).grid(row=0, column=0, padx=6)
        ctk.CTkButton(actions, text="🖨️ Gerar Folha (HTML)", width=170,
                      fg_color=self.cor_imprimir, hover_color=self.cor_hover, command=self._generate_html).grid(row=0, column=1, padx=6)

    def _kpi(self, parent, col, title, value):
        box = ctk.CTkFrame(parent, fg_color=getattr(self.sistema, 'cor_selecao', '#0f172a'), corner_radius=10)
        box.grid(row=0, column=col, padx=6, pady=6, sticky="ew")
        ctk.CTkLabel(box, text=title, font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="w", padx=10, pady=(8,0))
        lbl = ctk.CTkLabel(box, text=value, font=ctk.CTkFont(size=18, weight="bold"))
        lbl.grid(row=1, column=0, sticky="w", padx=10, pady=(0,10))
        return lbl

    # ---------- BUSCA E AGREGAÇÃO ----------
    def _search(self):
        """
        Busca os lançamentos de pagamento por período/serviço/costureira,
        de forma tolerante a colunas ausentes em pagamento_corte_acabamento.
        """
        from datetime import datetime, date
        from tkinter import messagebox

        def _get_val(widget_or_var, default=None):
            if widget_or_var is None:
                return default
            try:
                return widget_or_var.get() if callable(getattr(widget_or_var, "get", None)) else default
            except Exception:
                return default

        def _parse_date(s, fallback=None):
            s = (s or "").strip()
            if not s:
                return fallback or date.today()
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    return datetime.strptime(s, fmt).date()
                except Exception:
                    pass
            return fallback or date.today()

        # --------- 1) Coleta filtros da UI ---------
        try:
            ini_txt = _get_val(self.ini_var, "")
            fim_txt = _get_val(self.fim_var, "")
            serv = _get_val(self.servico_var, "Todos") or "Todos"
            termo = (_get_val(self.busca_var, "") or "").strip()
            incluir_est = _get_val(self.incluir_estornados, False)

            ini = _parse_date(ini_txt, date.today().replace(day=1))
            fim = _parse_date(fim_txt, date.today())
            ini_iso, fim_iso = ini.isoformat(), fim.isoformat()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler filtros: {e}")
            return

        # --------- 2) Conexão e schema ---------
        try:
            from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_schema, get_conn
            schema = get_schema() or "opera"
            conn = get_conn()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao conectar: {e}")
            return

        cur = conn.cursor()

        try:
            # --------- 3) Descoberta de colunas em pagamento_corte_acabamento ---------
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = 'pagamento_corte_acabamento'
            """, (schema,))
            col_info = {r[0]: r[1] for r in cur.fetchall()}
            cols = set(col_info.keys())

            # Flags de existência
            has_codigo = 'codigo' in cols
            has_descricao = 'descricao' in cols
            has_bonificacao = 'bonificacao' in cols
            has_valor_defeito = 'valor_defeito' in cols
            has_ajuda_custo = 'ajuda_custo' in cols
            has_adiantamento = 'adiantamento' in cols
            has_desc_pecas = 'desconto_pecas' in cols
            has_qtd_final = 'quantidade_finalizada' in cols
            has_vlr_peca = 'valor_por_peca' in cols
            has_tipo_servico = 'tipo_servico' in cols
            has_estornado = 'estornado' in cols
            estornado_type = col_info.get('estornado', '') if has_estornado else ''
            has_data_pag = 'data_pagamento' in cols

            # bancários
            has_cpf = 'cpf' in cols
            has_banco = 'banco' in cols
            has_agencia = 'agencia' in cols
            has_conta = 'conta' in cols
            has_pix = 'pix' in cols

            # --------- 4) Expressões seguras ---------
            data_expr = "p.data_pagamento::date" if has_data_pag else "NULL::date"
            sel_tipo = "p.tipo_servico" if has_tipo_servico else "''::text"
            sel_qtd = "COALESCE(p.quantidade_finalizada,0)" if has_qtd_final else "0::numeric"
            sel_vpeca = "COALESCE(p.valor_por_peca,0)" if has_vlr_peca else "0::numeric"
            sel_adi = "COALESCE(p.adiantamento,0)" if has_adiantamento else "0::numeric"
            sel_descp = "COALESCE(p.desconto_pecas,0)" if has_desc_pecas else "0::numeric"
            sel_vdef = "COALESCE(p.valor_defeito,0)" if has_valor_defeito else "0::numeric"
            sel_ajuda = "COALESCE(p.ajuda_custo,0)" if has_ajuda_custo else "0::numeric"
            sel_boni = "COALESCE(p.bonificacao,0)" if has_bonificacao else "0::numeric"
            sel_total = "COALESCE(p.total_pago,0)"

            # CORREÇÃO: Tratamento correto para coluna estornado (pode ser boolean ou integer)
            if has_estornado:
                if estornado_type == 'boolean':
                    sel_est = "COALESCE(p.estornado, false)"  # Para boolean
                    est_condition = f"({sel_est} = false)"  # Não estornado
                else:
                    sel_est = "COALESCE(p.estornado, 0)"  # Para integer
                    est_condition = f"({sel_est} = 0)"  # Não estornado
            else:
                est_condition = "true"  # Sempre inclui se a coluna não existe

            # Bancários tolerantes
            sel_cpf = "COALESCE(p.cpf,'')" if has_cpf else "''::text"
            sel_banco = "COALESCE(p.banco,'')" if has_banco else "''::text"
            sel_agencia = "COALESCE(p.agencia,'')" if has_agencia else "''::text"
            sel_conta = "COALESCE(p.conta,'')" if has_conta else "''::text"
            sel_pix = "COALESCE(p.pix,'')" if has_pix else "''::text"

            # --------- 5) Condições de filtro ---------
            # Serviço
            if has_tipo_servico:
                cond_serv = "(%s = 'Todos' OR p.tipo_servico = %s)"
                serv_params = (serv, serv)
            else:
                cond_serv = "(%s = 'Todos' OR %s = %s)"
                serv_params = (serv, serv)

            # Filtro textual seguro
            f_codigo = "p.codigo" if has_codigo else "''"
            f_desc = "p.descricao" if has_descricao else "''"
            f_cost = "p.costureira"

            # --------- 6) SQL principal ---------
            sql = f"""
                SELECT
                  p.costureira,
                  {sel_tipo} AS tipo_servico,
                  SUM({sel_qtd})                           AS qtd,
                  SUM({sel_qtd} * {sel_vpeca})             AS base,
                  SUM({sel_ajuda} + {sel_boni})            AS ajudas,
                  SUM({sel_adi} + {sel_descp} + {sel_vdef}) AS descontos,
                  SUM({sel_total})                         AS total,
                  MAX({sel_cpf})                           AS cpf,
                  MAX({sel_banco})                         AS banco,
                  MAX({sel_agencia})                       AS agencia,
                  MAX({sel_conta})                         AS conta,
                  MAX({sel_pix})                           AS pix,
                  COUNT(1)                                 AS lanc
                FROM {schema}.pagamento_corte_acabamento p
                WHERE {data_expr} BETWEEN %s AND %s
                  AND {cond_serv}
            """

            params = [ini_iso, fim_iso, *serv_params]

            # CORREÇÃO: Condição para estornados
            if not incluir_est and has_estornado:
                sql += f" AND {est_condition}"
            # Se incluir_est é True ou a coluna não existe, não aplica filtro

            if termo:
                sql += " AND (p.costureira ILIKE %s"
                params.append(f"%{termo}%")
                if has_codigo:
                    sql += " OR p.codigo ILIKE %s"
                    params.append(f"%{termo}%")
                if has_descricao:
                    sql += " OR p.descricao ILIKE %s"
                    params.append(f"%{termo}%")
                sql += ")"

            # GROUP BY
            sql += f" GROUP BY p.costureira, {sel_tipo} ORDER BY p.costureira ASC, {sel_tipo} ASC"

            # --------- 7) Execução e render ---------
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

            # Preenche a tree
            if hasattr(self, 'tree'):
                self.tree.delete(*self.tree.get_children())
                for r in rows:
                    self.tree.insert("", "end", values=r)

            # Atualiza KPIs
            total_geral = sum(row[6] for row in rows) if rows else 0  # índice 6 = total
            base_geral = sum(row[3] for row in rows) if rows else 0  # índice 3 = base
            desc_geral = sum(row[5] for row in rows) if rows else 0  # índice 5 = descontos
            aj_geral = sum(row[4] for row in rows) if rows else 0  # índice 4 = ajudas

            self.kpi_total.configure(text=f"{total_geral:,.2f}")
            self.kpi_base.configure(text=f"{base_geral:,.2f}")
            self.kpi_desc.configure(text=f"{desc_geral:,.2f}")
            self.kpi_ajuda.configure(text=f"{aj_geral:,.2f}")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na busca: {e}")
        finally:
            try:
                cur.close()
            except Exception:
                pass

    # ---------- Exportações ----------
    def _ensure_relatorios_dir(self) -> str:
        out_dir = os.path.join(DB_DIR, "RELATORIO_FOLHA_PAGAMENTO")
        os.makedirs(out_dir, exist_ok=True)
        return out_dir

    def _export_csv(self):
        """Exporta o resumo para CSV em BANCO DE DADOS/RELATORIO_FOLHA_PAGAMENTO/."""
        if not getattr(self, "_last_agg", None):
            messagebox.showinfo("Exportar", "Faça uma busca primeiro.")
            return

        out_dir = self._ensure_relatorios_dir()
        ini = self._last_filters.get("ini", "")
        fim = self._last_filters.get("fim", "")
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fname = f"folha_servicos_{ini}_a_{fim}_{now}.csv"
        fpath = os.path.join(out_dir, fname)

        try:
            with open(fpath, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow([
                    "Prestador", "CPF", "Serviço", "Qtd", "Base", "Descontos", "Ajuda/Bonif.",
                    "Total Pago", "Banco", "Agência", "Conta", "PIX", "Lançamentos"
                ])
                if self.agrupar_por_servico.get():
                    for prest, d in sorted(self._last_agg.items()):
                        for tipo, s in d["servicos"].items():
                            w.writerow([
                                prest, d["cpf"], tipo, s["qtd"],
                                f"{s['base']:.2f}", f"{s['desc']:.2f}", f"{s['aj']:.2f}",
                                f"{s['total']:.2f}", d["banco"], d["agencia"], d["conta"],
                                d["pix"], s["lanc"]
                            ])
                else:
                    for prest, d in sorted(self._last_agg.items()):
                        w.writerow([
                            prest, d["cpf"], "Todos", d["qtd"],
                            f"{d['base']:.2f}", f"{d['desc']:.2f}", f"{d['aj']:.2f}",
                            f"{d['total']:.2f}", d["banco"], d["agencia"], d["conta"],
                            d["pix"], d["lanc"]
                        ])
            messagebox.showinfo("Exportar", f"Arquivo salvo em:\n{fpath}")
        except Exception as e:
            messagebox.showerror("Exportar", f"Erro ao salvar CSV:\n{e}")

    def _generate_html(self):
        """Gera o relatório HTML e abre para impressão."""
        if not getattr(self, "_last_agg", None):
            messagebox.showinfo("Relatório", "Faça uma busca primeiro.")
            return

        out_dir = self._ensure_relatorios_dir()
        ini = self._last_filters["ini"]
        fim = self._last_filters["fim"]
        serv = self._last_filters["serv"]
        termo = self._last_filters["termo"]
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fname = f"folha_pagamento_servicos_{ini}_a_{fim}_{now}.html"
        out = os.path.join(out_dir, fname)

        css = """
        <style>
        body{font-family:Arial,Helvetica,sans-serif;margin:20px;color:#111}
        h1{font-size:20px;margin:0}
        h2{font-size:16px;margin-top:18px;border-bottom:1px solid #ddd;padding-bottom:4px}
        table{width:100%;border-collapse:collapse;margin-top:8px}
        th,td{border:1px solid #ddd;padding:6px;font-size:12px}
        th{background:#f5f5f5;text-align:left}
        .kpi{display:flex;gap:12px;flex-wrap:wrap;margin:10px 0}
        .card{border:1px solid #ddd;border-radius:8px;padding:10px;min-width:160px}
        .right{text-align:right}
        .muted{color:#666;font-size:12px}
        .page-break{page-break-after:always;margin-top:18px}
        </style>
        """

        total_kpi = sum(d["total"] for d in self._last_agg.values())
        base_kpi = sum(d["base"] for d in self._last_agg.values())
        desc_kpi = sum(d["desc"] for d in self._last_agg.values())
        aj_kpi = sum(d["aj"] for d in self._last_agg.values())

        rows = ""
        for prest, d in sorted(self._last_agg.items()):
            servs = ", ".join(f"{t}:{v['qtd']}" for t, v in d["servicos"].items())
            rows += (
                f"<tr><td>{prest}</td><td>{d['cpf']}</td><td>{servs}</td>"
                f"<td class='right'>{d['qtd']}</td>"
                f"<td class='right'>{d['base']:.2f}</td>"
                f"<td class='right'>{d['desc']:.2f}</td>"
                f"<td class='right'>{d['aj']:.2f}</td>"
                f"<td class='right'><b>{d['total']:.2f}</b></td>"
                f"<td>{d['banco']}</td><td>{d['agencia']}</td><td>{d['conta']}</td><td>{d['pix']}</td>"
                f"<td class='right'>{d['lanc']}</td></tr>"
            )

        html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'>{css}</head><body>
        <h1>Folha de Pagamento - Serviços</h1>
        <div class="muted">Período: {ini} a {fim} • Serviço: {serv} • Busca: {termo or '-'}</div>
        <div class="kpi">
          <div class="card"><div>Total a Pagar</div><div><b>R$ {total_kpi:.2f}</b></div></div>
          <div class="card"><div>Base</div><div><b>R$ {base_kpi:.2f}</b></div></div>
          <div class="card"><div>Descontos</div><div><b>R$ {desc_kpi:.2f}</b></div></div>
          <div class="card"><div>Ajuda/Bonificação</div><div><b>R$ {aj_kpi:.2f}</b></div></div>
        </div>

        <h2>Resumo por Prestador</h2>
        <table>
          <thead><tr><th>Prestador</th><th>CPF</th><th>Serviços</th><th class='right'>Qtd</th><th class='right'>Base</th><th class='right'>Descontos</th><th class='right'>Ajuda/Bonif.</th><th class='right'>Total</th><th>Banco</th><th>Agência</th><th>Conta</th><th>PIX</th><th class='right'>Lanç.</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        <div class="page-break"></div>
        """

        for prest, d in sorted(self._last_agg.items()):
            html += f"""
            <h2>Recibo / Prestador</h2>
            <table>
              <tr><th>Prestador</th><td>{prest}</td><th>CPF</th><td>{d['cpf']}</td></tr>
              <tr><th>Banco</th><td>{d['banco']}</td><th>Agência</th><td>{d['agencia']}</td></tr>
              <tr><th>Conta</th><td>{d['conta']}</td><th>PIX</th><td>{d['pix']}</td></tr>
            </table>
            <table>
              <thead><tr><th>Serviço</th><th class='right'>Qtd</th><th class='right'>Base</th><th class='right'>Descontos</th><th class='right'>Ajuda/Bonif.</th><th class='right'>Total</th></tr></thead>
              <tbody>
            """
            for tipo, s in d["servicos"].items():
                html += (
                    f"<tr><td>{tipo}</td><td class='right'>{s['qtd']}</td>"
                    f"<td class='right'>{s['base']:.2f}</td>"
                    f"<td class='right'>{s['desc']:.2f}</td>"
                    f"<td class='right'>{s['aj']:.2f}</td>"
                    f"<td class='right'><b>{s['total']:.2f}</b></td></tr>"
                )
            html += (
                f"<tr><td><b>TOTAL</b></td><td class='right'><b>{d['qtd']}</b></td>"
                f"<td class='right'><b>{d['base']:.2f}</b></td>"
                f"<td class='right'><b>{d['desc']:.2f}</b></td>"
                f"<td class='right'><b>{d['aj']:.2f}</b></td>"
                f"<td class='right'><b>{d['total']:.2f}</b></td></tr>"
                "</tbody></table>"
                "<p class='muted'>Assinatura do responsável: ______________________________________ &nbsp;&nbsp; Data: ____/____/______</p>"
                "<div class='page-break'></div>"
            )

        html += "<p class='muted'>Relatório gerado automaticamente. Revise os dados antes de efetuar os pagamentos.</p></body></html>"

        try:
            with open(out, "w", encoding="utf-8") as f:
                f.write(html)

            if os.name == "nt":
                os.startfile(out)  # Windows
            else:
                webbrowser.open_new_tab(out)

            messagebox.showinfo("Relatório", f"Folha gerada em:\n{out}\nUse Ctrl+P para imprimir.")
        except Exception as e:
            messagebox.showerror("Relatório", f"Erro ao gerar arquivo:\n{e}")


# ------------------ Standalone de teste ------------------
if __name__ == "__main__":
    ok, msg = require_ready()
    if not ok:
        messagebox.showwarning("Banco de Dados", f"Problema ao conectar ao PostgreSQL:\n{msg}")
        # Não saia completamente, deixe o usuário tentar mesmo sem conexão
    else:
        # Verificar se a tabela existe
        try:
            conn = get_conn()
            schema = get_schema()
            cur = conn.cursor()
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = 'pagamento_corte_acabamento'
                )
            """, (schema,))
            tabela_existe = cur.fetchone()[0]
            cur.close()

            if not tabela_existe:
                messagebox.showwarning("Tabela não encontrada",
                                       f"A tabela 'pagamento_corte_acabamento' não foi encontrada no schema '{schema}'.")
        except Exception as e:
            messagebox.showwarning("Erro na verificação", f"Erro ao verificar tabela: {e}")

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = ctk.CTk()
    app.title(FolhaPagamentoServicosPage.PAGE_TITLE)
    app.geometry("1200x760")
    page = FolhaPagamentoServicosPage(app, host=app)
    page.pack(fill="both", expand=True)
    app.mainloop()