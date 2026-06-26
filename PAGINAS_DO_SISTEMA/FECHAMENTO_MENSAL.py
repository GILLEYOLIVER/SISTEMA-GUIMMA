# -*- coding: utf-8 -*-
"""
Fechamento mensal consolidando envios, retornos, pagamentos, adiantamentos e histórico.
Versão PostgreSQL (acessa via BANCO_DE_DADOS_PG).

Tabelas utilizadas (nomes conforme seu banco):
- controle_envio_cortes, envio_detalhes_tamanho, retorno_detalhes_tamanho (se houver),
  registros_entradas, pagamento_corte_acabamento, adiantamento_faccao,
  historico_de_servico, copias_enviadas, copias_devolvidas, cadastro_modelos_cabecalho,
  cortes_finalizados
"""
from __future__ import annotations
from PAGINAS_DO_SISTEMA import TEMAS
import os, csv, webbrowser
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
import customtkinter as ctk
from PAGINAS_DO_SISTEMA.UI_CALENDARIO import abrir_calendario, vincular_calendario
from tkinter import ttk, messagebox, filedialog

# --- PG access ---
try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception as err:
    def get_conn():
        raise RuntimeError("BANCO_DE_DADOS_PG não disponível: " + str(err))
    def get_schema():
        return "public"
    def require_ready(essentials=None):
        return False, "Módulo de acesso não disponível"

# ---------- Helpers de data ----------
def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)
def _last_day_of_month(d: date) -> date:
    nd = d.replace(day=28) + timedelta(days=4)
    return nd - timedelta(days=nd.day)

def _dt(s: str) -> str:
    """Aceita 'DD/MM/AAAA' ou 'AAAA-MM-DD' e retorna 'AAAA-MM-DD'."""
    if not s: return ""
    s = s.strip()
    try:
        if "/" in s:
            d = datetime.strptime(s, "%d/%m/%Y").date()
        else:
            d = datetime.strptime(s[:10], "%Y-%m-%d").date()
        return d.strftime("%Y-%m-%d")
    except Exception:
        return s[:10]

# ---------- Tema ----------
class _Theme:
    def __init__(self, host):
        self.host = host
        self.defaults = dict(
            cor_fundo = "#0d1117", cor_primaria="#1f2d44", cor_secundaria="#0b1220",
            cor_terciaria="#111827", cor_texto="#e5e7eb", cor_destaque="#2563eb",
            cor_hover="#1d4ed8", cor_imprimir="#2563eb", cor_adicionar="#22c55e",
            cor_borda="#334155"
        )
    def get(self, key): return getattr(self.host, key, self.defaults.get(key))
    def __getattr__(self, item): return self.get(item)

# ---------- Página ----------
class FechamentoMensalPage(ctk.CTkFrame):
    TRANSLATIONS = {
        "pt_BR": {
            "page_title": "Fechamento Mensal (Consolidação)",
            "from": "De:", "to": "Até:", "service": "Serviço:",
            "search_label": "Buscar (modelo/corte/costureira):", "search": "🔍 Buscar",
            "date_placeholder": "AAAA-MM-DD",
            "tab_kpi": "Consolidado", "tab_env": "Envios", "tab_ret": "Retornos/Entradas",
            "tab_pag": "Pagamentos", "tab_adi": "Adiantamentos", "tab_his": "Histórico", "tab_rel": "Relatório",
            "export_csv": "📤 Exportar CSV (Consolidado)", "report_html": "🖨️ Gerar Relatório HTML",
            "kpi_sent": "Peças Enviadas", "kpi_returned": "Peças Retornadas", "kpi_missing": "Faltantes",
            "kpi_defect": "Defeitos", "kpi_paid": "Total Pago", "kpi_advance": "Adiantamentos",
            "all": "Todos", "faction":"Facção","embroidery":"Bordado","buttonhole":"Caseador","buttons":"Botões",
            "printing":"Estamparia","dyeing":"Tingimento","other_jobs":"Outros Trabalhos",
            "sum_model":"MODELO","sum_description":"DESCRIÇÃO","sum_destination":"DESTINO","sum_seamstress":"COSTUREIRA","sum_service":"SERVIÇO","sum_sent":"ENVIOS","sum_returned":"RETORNOS","sum_missing":"FALT.","sum_defect":"DEF.","sum_paid_value":"VALOR PAGO",
            "env_date":"DATA","env_order":"ORDEM","env_code":"CÓDIGO","env_description":"DESCRIÇÃO","env_service":"SERVIÇO","env_destination":"DESTINO","env_qty":"QTD","env_samples":"PILOTOS","env_piece_value":"VALOR PEÇA",
            "ret_date":"DATA","ret_code":"CÓDIGO","ret_size":"TAMANHO","ret_qty":"QTD","ret_copies":"CÓPIAS","ret_defect":"DEFEITO","ret_piece_value":"VALOR PEÇA","ret_obs":"OBS",
            "pag_date":"DATA","pag_service":"SERVIÇO","pag_code":"CÓDIGO","pag_description":"DESCRIÇÃO","pag_seamstress":"COSTUREIRA","pag_qty":"QTD","pag_piece_value":"VALOR PEÇA","pag_base":"BASE","pag_discounts":"DESCONTOS","pag_help":"AJUDAS","pag_total":"TOTAL",
            "adi_date":"DATA","adi_model_code":"CÓDIGO MODELO","adi_faction":"FACÇÃO","adi_value":"VALOR","adi_method":"FORMA","adi_installments":"PARCELAS",
            "his_date":"DATA","his_event":"EVENTO","his_cut":"CORTE","his_send":"ENVIO","his_entry":"ENTRADA","his_description":"DESCRIÇÃO","his_sector":"SETOR","his_qty":"QTD","his_value":"VALOR","his_status":"STATUS",
        },
        "en_US": {
            "page_title": "Monthly Closing (Consolidation)",
            "from": "From:", "to": "To:", "service": "Service:",
            "search_label": "Search (model/cut/seamstress):", "search": "🔍 Search",
            "date_placeholder": "YYYY-MM-DD",
            "tab_kpi": "Summary", "tab_env": "Shipments", "tab_ret": "Returns/Entries",
            "tab_pag": "Payments", "tab_adi": "Advances", "tab_his": "History", "tab_rel": "Report",
            "export_csv": "📤 Export CSV (Summary)", "report_html": "🖨️ Generate HTML Report",
            "kpi_sent": "Pieces Sent", "kpi_returned": "Pieces Returned", "kpi_missing": "Missing",
            "kpi_defect": "Defects", "kpi_paid": "Total Paid", "kpi_advance": "Advances",
            "all": "All", "faction":"Outsource","embroidery":"Embroidery","buttonhole":"Buttonhole","buttons":"Buttons",
            "printing":"Printing","dyeing":"Dyeing","other_jobs":"Other Jobs",
            "sum_model":"MODEL","sum_description":"DESCRIPTION","sum_destination":"DESTINATION","sum_seamstress":"SEAMSTRESS","sum_service":"SERVICE","sum_sent":"SENT","sum_returned":"RETURNED","sum_missing":"MISS.","sum_defect":"DEF.","sum_paid_value":"PAID VALUE",
            "env_date":"DATE","env_order":"ORDER","env_code":"CODE","env_description":"DESCRIPTION","env_service":"SERVICE","env_destination":"DESTINATION","env_qty":"QTY","env_samples":"SAMPLES","env_piece_value":"PIECE VALUE",
            "ret_date":"DATE","ret_code":"CODE","ret_size":"SIZE","ret_qty":"QTY","ret_copies":"COPIES","ret_defect":"DEFECT","ret_piece_value":"PIECE VALUE","ret_obs":"NOTES",
            "pag_date":"DATE","pag_service":"SERVICE","pag_code":"CODE","pag_description":"DESCRIPTION","pag_seamstress":"SEAMSTRESS","pag_qty":"QTY","pag_piece_value":"PIECE VALUE","pag_base":"BASE","pag_discounts":"DISCOUNTS","pag_help":"HELPS","pag_total":"TOTAL",
            "adi_date":"DATE","adi_model_code":"MODEL CODE","adi_faction":"OUTSOURCE","adi_value":"VALUE","adi_method":"METHOD","adi_installments":"INSTALLMENTS",
            "his_date":"DATE","his_event":"EVENT","his_cut":"CUT","his_send":"SHIPMENT","his_entry":"ENTRY","his_description":"DESCRIPTION","his_sector":"SECTOR","his_qty":"QTY","his_value":"VALUE","his_status":"STATUS",
        },
        "es_ES": {
            "page_title": "Cierre Mensual (Consolidación)",
            "from": "Desde:", "to": "Hasta:", "service": "Servicio:",
            "search_label": "Buscar (modelo/corte/costurera):", "search": "🔍 Buscar",
            "date_placeholder": "AAAA-MM-DD",
            "tab_kpi": "Consolidado", "tab_env": "Envíos", "tab_ret": "Retornos/Entradas",
            "tab_pag": "Pagos", "tab_adi": "Adelantos", "tab_his": "Historial", "tab_rel": "Reporte",
            "export_csv": "📤 Exportar CSV (Consolidado)", "report_html": "🖨️ Generar Reporte HTML",
            "kpi_sent": "Piezas Enviadas", "kpi_returned": "Piezas Recibidas", "kpi_missing": "Faltantes",
            "kpi_defect": "Defectos", "kpi_paid": "Total Pagado", "kpi_advance": "Adelantos",
            "all": "Todos", "faction":"Facción","embroidery":"Bordado","buttonhole":"Caseador","buttons":"Botones",
            "printing":"Estampado","dyeing":"Teñido","other_jobs":"Otros Trabajos",
            "sum_model":"MODELO","sum_description":"DESCRIPCIÓN","sum_destination":"DESTINO","sum_seamstress":"COSTURERA","sum_service":"SERVICIO","sum_sent":"ENVÍOS","sum_returned":"RETORNOS","sum_missing":"FALT.","sum_defect":"DEF.","sum_paid_value":"VALOR PAGADO",
            "env_date":"FECHA","env_order":"ORDEN","env_code":"CÓDIGO","env_description":"DESCRIPCIÓN","env_service":"SERVICIO","env_destination":"DESTINO","env_qty":"CANT","env_samples":"MUESTRAS","env_piece_value":"VALOR PIEZA",
            "ret_date":"FECHA","ret_code":"CÓDIGO","ret_size":"TALLA","ret_qty":"CANT","ret_copies":"COPIAS","ret_defect":"DEFECTO","ret_piece_value":"VALOR PIEZA","ret_obs":"OBS",
            "pag_date":"FECHA","pag_service":"SERVICIO","pag_code":"CÓDIGO","pag_description":"DESCRIPCIÓN","pag_seamstress":"COSTURERA","pag_qty":"CANT","pag_piece_value":"VALOR PIEZA","pag_base":"BASE","pag_discounts":"DESCUENTOS","pag_help":"AYUDAS","pag_total":"TOTAL",
            "adi_date":"FECHA","adi_model_code":"CÓDIGO MODELO","adi_faction":"FACCIÓN","adi_value":"VALOR","adi_method":"FORMA","adi_installments":"PARCELAS",
            "his_date":"FECHA","his_event":"EVENTO","his_cut":"CORTE","his_send":"ENVÍO","his_entry":"ENTRADA","his_description":"DESCRIPCIÓN","his_sector":"SECTOR","his_qty":"CANT","his_value":"VALOR","his_status":"ESTADO",
        },
    }
    def _init_i18n(self):
        self.idioma_atual = getattr(self._host, "idioma_atual", getattr(self, "idioma_atual", "pt_BR"))
    def _get_text(self, key, default=None):
        lang = getattr(self, "idioma_atual", "pt_BR")
        return self.TRANSLATIONS.get(lang, {}).get(key, self.TRANSLATIONS["pt_BR"].get(key, default if default is not None else key))
    def _service_options(self):
        return [self._get_text(k) for k in ("all","faction","embroidery","buttonhole","buttons","printing","dyeing","other_jobs")]
    def refresh_texts(self):
        self.PAGE_TITLE = self._get_text("page_title")
        try: self.lbl_title.configure(text=self._get_text("page_title"))
        except Exception: pass
        for wname,key in [("lbl_de","from"),("lbl_ate","to"),("lbl_servico","service"),("lbl_busca","search_label"),("btn_buscar","search"),("btn_export_csv","export_csv"),("btn_report_html","report_html")]:
            try: getattr(self, wname).configure(text=self._get_text(key))
            except Exception: pass
        for en in ("ini_entry","fim_entry"):
            try: getattr(self, en).configure(placeholder_text=self._get_text("date_placeholder"))
            except Exception: pass
        try:
            vals = self._service_options()
            current = self.servico_var.get()
            mapping = {"Todos":"all","Facção":"faction","Bordado":"embroidery","Caseador":"buttonhole","Botões":"buttons","Estamparia":"printing","Tingimento":"dyeing","Outros Trabalhos":"other_jobs",
                       "All":"all","Outsource":"faction","Embroidery":"embroidery","Buttonhole":"buttonhole","Buttons":"buttons","Printing":"printing","Dyeing":"dyeing","Other Jobs":"other_jobs",
                       "Facción":"faction","Estampado":"printing","Teñido":"dyeing"}
            self.cmb_serv.configure(values=vals)
            self.servico_var.set(self._get_text(mapping.get(current,"all")))
        except Exception: pass
        try:
            self.tabs._segmented_button.configure(values=[self._get_text("tab_kpi"),self._get_text("tab_env"),self._get_text("tab_ret"),self._get_text("tab_pag"),self._get_text("tab_adi"),self._get_text("tab_his"),self._get_text("tab_rel")])
        except Exception: pass
        self._refresh_tree_headings()
    def _refresh_tree_headings(self):
        maps = {
          "tree_sum":[("modelo","sum_model"),("descricao","sum_description"),("destino","sum_destination"),("costureira","sum_seamstress"),("servico","sum_service"),("env","sum_sent"),("ret","sum_returned"),("falt","sum_missing"),("def","sum_defect"),("valor_pago","sum_paid_value")],
          "tree_env":[("data_envio","env_date"),("ordem_corte","env_order"),("codigo_corte","env_code"),("descricao_corte","env_description"),("servico","env_service"),("destino","env_destination"),("qtd_total","env_qty"),("pilotos","env_samples"),("valor_peca","env_piece_value")],
          "tree_ret":[("data","ret_date"),("codigo","ret_code"),("tamanho","ret_size"),("qtd","ret_qty"),("copias","ret_copies"),("defeito","ret_defect"),("valor_peca","ret_piece_value"),("obs","ret_obs")],
          "tree_pag":[("data_pag","pag_date"),("tipo_servico","pag_service"),("codigo","pag_code"),("descricao","pag_description"),("costureira","pag_seamstress"),("qtd","pag_qty"),("v_peca","pag_piece_value"),("base","pag_base"),("descontos","pag_discounts"),("ajudas","pag_help"),("total","pag_total")],
          "tree_adi":[("data","adi_date"),("codigo_modelo","adi_model_code"),("faccao","adi_faction"),("valor","adi_value"),("forma_pagamento","adi_method"),("parcelas","adi_installments")],
          "tree_his":[("data","his_date"),("evento","his_event"),("corte_id","his_cut"),("envio_id","his_send"),("entrada_id","his_entry"),("descricao","his_description"),("setor","his_sector"),("quant","his_qty"),("valor","his_value"),("status","his_status")]
        }
        for tree_name, items in maps.items():
            tree = getattr(self, tree_name, None)
            if tree:
                for col, key in items:
                    try: tree.heading(col, text=self._get_text(key))
                    except Exception: pass
    PAGE_TITLE = "Fechamento Mensal (Consolidação)"

    def __init__(self, parent, host=None, *args, **kwargs):
        self._host = host or parent
        self.theme = _Theme(self._host)
        super().__init__(parent, fg_color=self.theme.cor_fundo, *args, **kwargs)
        self._init_i18n()
        self._build_ui()
        self._apply_theme_widgets()
        self.refresh_texts()
        self._search()

    # ======= UI =======
    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Título
        top = ctk.CTkFrame(self, corner_radius=0); top.grid(row=0, column=0, sticky="ew")
        self.lbl_title = ctk.CTkLabel(top, text=self.PAGE_TITLE, font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_title.grid(
            row=0, column=0, padx=20, pady=8, sticky="w"
        )

        # Filtros
        filt = ctk.CTkFrame(self); filt.grid(row=1, column=0, sticky="ew", padx=10, pady=(6,6))
        for i in range(10): filt.grid_columnconfigure(i, weight=0)
        filt.grid_columnconfigure(9, weight=1)

        hoje = date.today()
        self.ini_var = ctk.StringVar(value=_first_day_of_month(hoje).strftime("%Y-%m-%d"))
        self.fim_var = ctk.StringVar(value=_last_day_of_month(hoje).strftime("%Y-%m-%d"))

        self.lbl_de = ctk.CTkLabel(filt, text="De:"); self.lbl_de.grid(row=0, column=0, padx=(10,4), pady=8, sticky="e")
        self.ini_entry = ctk.CTkEntry(filt, width=120, textvariable=self.ini_var, placeholder_text="AAAA-MM-DD"); self.ini_entry.grid(row=0, column=1, padx=4, pady=8)
        vincular_calendario(self, self.ini_entry, output_format="%Y-%m-%d")
        ctk.CTkButton(filt, text="📅", width=28, height=26,
                      command=lambda: abrir_calendario(self, self.ini_entry, output_format="%Y-%m-%d")
                      ).grid(row=0, column=1, padx=(86, 4), pady=8, sticky="e")

        self.lbl_ate = ctk.CTkLabel(filt, text="Até:"); self.lbl_ate.grid(row=0, column=2, padx=(12,4), pady=8, sticky="e")
        self.fim_entry = ctk.CTkEntry(filt, width=120, textvariable=self.fim_var, placeholder_text="AAAA-MM-DD"); self.fim_entry.grid(row=0, column=3, padx=4, pady=8)
        vincular_calendario(self, self.fim_entry, output_format="%Y-%m-%d")
        ctk.CTkButton(filt, text="📅", width=28, height=26,
                      command=lambda: abrir_calendario(self, self.fim_entry, output_format="%Y-%m-%d")
                      ).grid(row=0, column=3, padx=(86, 4), pady=8, sticky="e")

        self.servico_var = ctk.StringVar(value="Todos")
        self.lbl_servico = ctk.CTkLabel(filt, text="Serviço:"); self.lbl_servico.grid(row=0, column=4, padx=(12,4), pady=8, sticky="e")
        self.cmb_serv = ctk.CTkComboBox(filt, values=[
            "Todos","Facção","Bordado","Caseador","Botões","Estamparia","Tingimento","Outros Trabalhos"
        ], width=160, variable=self.servico_var, state="readonly")
        self.cmb_serv.grid(row=0, column=5, padx=4, pady=8)

        self.busca_var = ctk.StringVar(value="")
        self.lbl_busca = ctk.CTkLabel(filt, text="Buscar (modelo/corte/costureira):"); self.lbl_busca.grid(row=0, column=6, padx=(12,4), pady=8, sticky="e")
        self.busca_entry = ctk.CTkEntry(filt, width=260, textvariable=self.busca_var); self.busca_entry.grid(row=0, column=7, padx=4, pady=8)
        self.busca_entry.bind("<Return>", lambda e: self._search())
        self.btn_buscar = ctk.CTkButton(filt, text="🔍 Buscar", width=120, command=self._search); self.btn_buscar.grid(row=0, column=9, padx=(8,10), pady=8, sticky="e")

        # Abas
        self.tabs = ctk.CTkTabview(self); self.tabs.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        tabs = self.tabs
        self.tab_kpi = tabs.add("Consolidado")
        self.tab_env = tabs.add("Envios")
        self.tab_ret = tabs.add("Retornos/Entradas")
        self.tab_pag = tabs.add("Pagamentos")
        self.tab_adi = tabs.add("Adiantamentos")
        self.tab_his = tabs.add("Histórico")
        self.tab_rel = tabs.add("Relatório")

        # Consolidado
        self._build_kpi(self.tab_kpi)

        # Tabela resumo (Consolidado)
        wrap_sum = ctk.CTkFrame(self.tab_kpi); wrap_sum.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0,6))
        wrap_sum.grid_columnconfigure(0, weight=1); wrap_sum.grid_rowconfigure(0, weight=1)
        cols_sum = ("modelo","descricao","destino","costureira","servico","env","ret","falt","def","valor_pago")
        headers_sum = ["MODELO","DESCRIÇÃO","DESTINO","COSTUREIRA","SERVIÇO","ENVIOS","RETORNOS","FALT.","DEF.","VALOR PAGO"]
        self.tree_sum = ttk.Treeview(
            wrap_sum, columns=cols_sum, show="headings", height=16,
            style="FechamentoMensal.Treeview",
        )
        widths_sum = [100,240,140,140,120,90,90,90,90,120]
        anchors_sum = ["center","w","w","w","center","center","center","center","center","e"]
        for c,h,w,a in zip(cols_sum, headers_sum, widths_sum, anchors_sum):
            self.tree_sum.heading(c, text=h)
            self.tree_sum.column(c, width=w, anchor=a, stretch=True if c in ("descricao",) else False)
        self.tree_sum.grid(row=0, column=0, sticky="nsew")
        vs_sum = ttk.Scrollbar(wrap_sum, orient="vertical", command=self.tree_sum.yview)
        self.tree_sum.configure(yscrollcommand=vs_sum.set); vs_sum.grid(row=0, column=1, sticky="ns")

        # Demais abas
        self._build_table(self.tab_env, "env")
        self._build_table(self.tab_ret, "ret")
        self._build_table(self.tab_pag, "pag")
        self._build_table(self.tab_adi, "adi")
        self._build_table(self.tab_his, "his")

        # Relatórios
        box_rel = ctk.CTkFrame(self.tab_rel); box_rel.grid(row=0, column=0, sticky="nw", padx=10, pady=10)
        self.btn_export_csv = ctk.CTkButton(box_rel, text="📤 Exportar CSV (Consolidado)", command=self._export_csv); self.btn_export_csv.grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.btn_report_html = ctk.CTkButton(box_rel, text="🖨️ Gerar Relatório HTML", command=self._report_html); self.btn_report_html.grid(row=0, column=1, padx=6, pady=6, sticky="w")

    def _build_kpi(self, parent):
        """
        Constrói a faixa de KPIs no topo da aba 'Consolidado'.
        Expõe os labels em:
          - self.kpi_envios
          - self.kpi_retorno
          - self.kpi_falt
          - self.kpi_def
          - self.kpi_pago
          - self.kpi_adi
        """
        wrap = ctk.CTkFrame(parent)  # container da faixa de KPIs
        wrap.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        for i in range(6):
            wrap.grid_columnconfigure(i, weight=1)

        def make_card(col, titulo, valor_inicial="0"):
            card = ctk.CTkFrame(wrap, corner_radius=10)
            card.grid(row=0, column=col, padx=6, pady=6, sticky="ew")
            ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=12)).grid(
                row=0, column=0, sticky="w", padx=10, pady=(8, 0)
            )
            lbl = ctk.CTkLabel(card, text=valor_inicial, font=ctk.CTkFont(size=20, weight="bold"))
            lbl.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))
            return lbl

        # KPIs (na ordem usada pelo restante do código)
        self.kpi_envios = make_card(0, self._get_text("kpi_sent"), "0")
        self.kpi_retorno = make_card(1, self._get_text("kpi_returned"), "0")
        self.kpi_falt = make_card(2, self._get_text("kpi_missing"), "0")
        self.kpi_def = make_card(3, self._get_text("kpi_defect"), "0")
        self.kpi_pago = make_card(4, self._get_text("kpi_paid"), "R$ 0,00")
        self.kpi_adi = make_card(5, self._get_text("kpi_advance"), "R$ 0,00")

    def _apply_ctk_global_theme(self):
        # Nao altere o tema global a partir desta pagina.
        # ctk.set_appearance_mode(...) muda o sistema inteiro.
        return

    def _style_tree(self):
        st = ttk.Style()
        try: st.theme_use("clam")
        except Exception: pass
        st.configure("FechamentoMensal.Treeview",
                     background=self.theme.cor_terciaria, fieldbackground=self.theme.cor_terciaria,
                     foreground=self.theme.cor_texto, rowheight=24, bordercolor=self.theme.cor_borda, borderwidth=1)
        st.map("FechamentoMensal.Treeview", background=[("selected", self.theme.cor_destaque)], foreground=[("selected","white")])
        st.configure("FechamentoMensal.Treeview.Heading", background=self.theme.cor_primaria, foreground="white", relief="flat")

    def _apply_theme_widgets(self):
        self._style_tree()
        def walk(w):
            for c in w.winfo_children():
                try:
                    if isinstance(c, ctk.CTkFrame):
                        if getattr(c, "_kind", "")=="topbar":
                            c.configure(fg_color=self.theme.cor_primaria)
                        elif getattr(c, "_kind", "")=="filter":
                            c.configure(fg_color=self.theme.cor_secundaria)
                        else:
                            c.configure(fg_color=self.theme.cor_terciaria)
                    elif isinstance(c, ctk.CTkLabel):
                        c.configure(text_color=self.theme.cor_texto)
                    elif isinstance(c, ctk.CTkEntry):
                        c.configure(fg_color=self.theme.cor_secundaria, text_color=self.theme.cor_texto)
                    elif isinstance(c, ctk.CTkComboBox):
                        c.configure(fg_color=self.theme.cor_secundaria, text_color=self.theme.cor_texto,
                                    button_color=self.theme.cor_destaque, border_color=self.theme.cor_borda)
                    elif isinstance(c, ctk.CTkButton):
                        txt = (c.cget("text") or "").lower()
                        c.configure(fg_color=self.theme.cor_destaque, hover_color=self.theme.cor_hover)
                except Exception: pass
                walk(c)
        walk(self)

    def _build_table(self, parent, key):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        wrap = ctk.CTkFrame(parent); wrap.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        wrap.grid_columnconfigure(0, weight=1); wrap.grid_rowconfigure(0, weight=1)

        if key == "env":
            cols = ("data_envio","ordem_corte","codigo_corte","descricao_corte","servico","destino","qtd_total","pilotos","valor_peca")
            headers = ["DATA","ORDEM","CÓDIGO","DESCRIÇÃO","SERVIÇO","DESTINO","QTD","PILOTOS","VALOR PEÇA"]
            widths = [110,100,100,240,120,140,90,90,110]
            anchors = ["center","center","center","w","center","center","center","center","e"]
        elif key == "ret":
            cols = ("data","codigo","tamanho","qtd","copias","defeito","valor_peca","obs")
            headers = ["DATA","CÓDIGO","TAMANHO","QTD","CÓPIAS","DEFEITO","VALOR PEÇA","OBS"]
            widths = [110,120,320,90,90,100,110,260]
            anchors = ["center","center","w","center","center","center","e","w"]
            self.ret_cols_fixed = cols
        elif key == "pag":
            cols = ("data_pag","tipo_servico","codigo","descricao","costureira","qtd","v_peca","base","descontos","ajudas","total")
            headers = ["DATA","SERVIÇO","CÓDIGO","DESCRIÇÃO","COSTUREIRA","QTD","VALOR PEÇA","BASE","DESCONTOS","AJUDAS","TOTAL"]
            widths = [110,120,100,240,160,90,110,110,110,110,120]
            anchors = ["center","center","center","w","w","center","e","e","e","e","e"]
        elif key == "adi":
            cols = ("data","codigo_modelo","faccao","valor","forma_pagamento","parcelas")
            headers = ["DATA","CÓDIGO MODELO","FACÇÃO","VALOR","FORMA","PARCELAS"]
            widths = [110,140,160,110,120,100]
            anchors = ["center","center","w","e","center","center"]
        elif key == "his":
            cols = ("data","evento","corte_id","envio_id","entrada_id","descricao","setor","quant","valor","status")
            headers = ["DATA","EVENTO","CORTE","ENVIO","ENTRADA","DESCRIÇÃO","SETOR","QTD","VALOR","STATUS"]
            widths = [110,160,80,80,80,260,160,90,110,120]
            anchors = ["center","w","center","center","center","w","w","center","e","center"]
        else:
            cols, headers, widths, anchors = [], [], [], []

        tree = ttk.Treeview(
            wrap, columns=cols, show="headings", height=18,
            style="FechamentoMensal.Treeview",
        )
        for c, h, w, a in zip(cols, headers, widths, anchors):
            tree.heading(c, text=h)
            tree.column(c, width=w, anchor=a, stretch=True if c in ("descricao","descricao_corte","obs","tamanho") else False)
        tree.grid(row=0, column=0, sticky="nsew")
        vs = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        hs = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        setattr(self, f"tree_{key}", tree)

    def _kpi(self, parent, col, title, value):
        box = ctk.CTkFrame(parent); box.grid(row=0, column=col, padx=6, pady=6, sticky="ew")
        ctk.CTkLabel(box, text=title).grid(row=0, column=0, sticky="w", padx=10, pady=(6,0))
        lbl = ctk.CTkLabel(box, text=value, font=ctk.CTkFont(size=18, weight="bold"))
        lbl.grid(row=1, column=0, sticky="w", padx=10, pady=(0,8))
        return lbl

    def _atualizar_kpis(self, pag_rows, env_rows, ret_rows, ad_rows):
        """Atualiza os KPIs com os dados carregados."""
        try:
            # Calcular totais
            total_env = sum(int(r.get("qtd", 0) or 0) for r in env_rows)
            total_ret = sum(int(r.get("qtd", 0) or 0) for r in ret_rows)
            total_def = sum(int(r.get("qtd_defeito_pp", 0) or 0) +
                            int(r.get("qtd_defeito_p", 0) or 0) +
                            int(r.get("qtd_defeito_m", 0) or 0) +
                            int(r.get("qtd_defeito_g", 0) or 0) +
                            int(r.get("qtd_defeito_gg", 0) or 0) +
                            int(r.get("qtd_defeito_g1", 0) or 0) +
                            int(r.get("qtd_defeito_g2", 0) or 0) +
                            int(r.get("qtd_defeito_g3", 0) or 0) for r in ret_rows)

            total_falt = max(total_env - total_ret - total_def, 0)
            total_pag = sum(float(r.get("total", 0) or 0) for r in pag_rows)
            total_adi = sum(float(r.get("valor", 0) or 0) for r in ad_rows)

            # Atualizar os labels dos KPIs
            self.kpi_envios.configure(text=str(total_env))
            self.kpi_retorno.configure(text=str(total_ret))
            self.kpi_falt.configure(text=str(total_falt))
            self.kpi_def.configure(text=str(total_def))
            self.kpi_pago.configure(text=f"R$ {total_pag:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            self.kpi_adi.configure(text=f"R$ {total_adi:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        except Exception as e:
            print(f"Erro ao atualizar KPIs: {e}")

    def _preencher_pagamentos(self, rows):
        """Preenche a tabela de pagamentos."""
        try:
            # Limpar tabela
            for item in self.tree_pag.get_children():
                self.tree_pag.delete(item)

            # Preencher com dados
            for row in rows:
                values = (
                    row.get('data_pag', ''),
                    row.get('tipo_servico', ''),
                    row.get('codigo', ''),
                    row.get('descricao', ''),
                    row.get('costureira', ''),
                    row.get('qtd', 0),
                    f"R$ {float(row.get('v_peca', 0)):.2f}",
                    f"R$ {float(row.get('base', 0)):.2f}",
                    f"R$ {float(row.get('descontos', 0)):.2f}",
                    f"R$ {float(row.get('ajudas', 0)):.2f}",
                    f"R$ {float(row.get('total', 0)):.2f}"
                )
                self.tree_pag.insert("", "end", values=values)
        except Exception as e:
            print(f"Erro ao preencher pagamentos: {e}")

    def _preencher_envios(self, rows):
        """Preenche a tabela de envios."""
        try:
            # Limpar tabela
            for item in self.tree_env.get_children():
                self.tree_env.delete(item)

            # Preencher com dados
            for row in rows:
                values = (
                    row.get('data_envio', ''),
                    row.get('ordem_corte', ''),
                    row.get('codigo_corte', ''),
                    row.get('descricao_corte', ''),
                    row.get('servico', ''),
                    row.get('destino', ''),
                    row.get('qtd_total', 0),
                    row.get('pilotos', 0),
                    f"R$ {float(row.get('valor_peca', 0)):.2f}"
                )
                self.tree_env.insert("", "end", values=values)
        except Exception as e:
            print(f"Erro ao preencher envios: {e}")

    def _preencher_retornos(self, rows):
        """Preenche a tabela de retornos."""
        try:
            # Limpar tabela
            for item in self.tree_ret.get_children():
                self.tree_ret.delete(item)

            # Preencher com dados
            for row in rows:
                values = (
                    row.get('data_final', ''),
                    row.get('codigo', ''),
                    row.get('tamanho', ''),
                    row.get('qtd', 0),
                    row.get('copias', 0),
                    row.get('defeito', 0),
                    f"R$ {float(row.get('valor_peca', 0)):.2f}",
                    row.get('obs', '')
                )
                self.tree_ret.insert("", "end", values=values)
        except Exception as e:
            print(f"Erro ao preencher retornos: {e}")

    def _preencher_adiantamentos(self, rows):
        """Preenche a tabela de adiantamentos."""
        try:
            # Limpar tabela
            for item in self.tree_adi.get_children():
                self.tree_adi.delete(item)

            # Preencher com dados
            for row in rows:
                values = (
                    row.get('data', ''),
                    row.get('codigo_modelo', ''),
                    row.get('faccao', ''),
                    f"R$ {float(row.get('valor', 0)):.2f}",
                    row.get('forma_pagamento', ''),
                    row.get('parcelas', 1)
                )
                self.tree_adi.insert("", "end", values=values)
        except Exception as e:
            print(f"Erro ao preencher adiantamentos: {e}")

    # ======= Acesso PG / util =======
    @staticmethod
    def _fetch_all_dicts(cur) -> List[Dict[str, Any]]:
        """Converte fetchall() para lista de dicts com nomes de colunas do cursor."""
        cols = [d[0] for d in cur.description]
        return [ {cols[i]: row[i] for i in range(len(cols))} for row in cur.fetchall() ]

    # ======= Busca / Agregação =======
    def _search(self):
        """Carrega dados do Fechamento Mensal de forma tolerante a colunas ausentes (sem alterar UI)."""
        from datetime import datetime, date
        try:
            # ---------- 1) Coleta segura dos filtros da UI ----------
            def _get_attr(*names, default=""):
                for n in names:
                    try:
                        v = getattr(self, n)
                        # Entry/CTkEntry
                        if hasattr(v, "get"):
                            return v.get() or default
                        # StringVar/CTkStringVar
                        if hasattr(v, "get") and callable(v.get):
                            return v.get() or default
                    except Exception:
                        continue
                return default

            # datas (aceita dd/mm/aaaa e yyyy-mm-dd)
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

            ini_txt = _get_attr("entry_inicio", "data_inicio", "data_inicio_var", default="")
            fim_txt = _get_attr("entry_fim", "data_fim", "data_fim_var", default="")
            serv = (_get_attr("combo_servico", "servico_var", default="Todos") or "Todos")
            termo = _get_attr("entry_busca", "busca_var", default="").strip()

            ini = _parse_date(ini_txt, date.today().replace(day=1))
            fim = _parse_date(fim_txt, date.today())
            # normaliza
            ini_iso = ini.isoformat()
            fim_iso = fim.isoformat()

            # schema
            try:
                from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_schema, get_conn
                schema = get_schema() or "opera"
                conn = get_conn()
            except Exception:
                schema = "opera"
                conn = None

            if conn is None:
                # fallback simples
                from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn as _gc
                conn = _gc()

            cur = conn.cursor()

            # helper: garante dicts
            def _fetch_all_dicts(_cur):
                cols = [d[0] for d in _cur.description]
                rows = _cur.fetchall()
                out = []
                for r in rows:
                    if isinstance(r, dict):
                        out.append(r)
                    else:
                        out.append({cols[i]: r[i] for i in range(len(cols))})
                return out

            # helper: coluna existe?
            def _has_col(table: str, col: str) -> bool:
                cur.execute("""
                    SELECT 1
                      FROM information_schema.columns
                     WHERE table_schema = %s
                       AND table_name   = %s
                       AND column_name  = %s
                     LIMIT 1
                """, (schema, table, col))
                return bool(cur.fetchone())

            # helper: escolhe a primeira coluna existente
            def _pick(table: str, *cands, default=None):
                for c in cands:
                    if _has_col(table, c):
                        return c
                return default

            # --------------------------------------------------------
            # 2) PAGAMENTOS (p = pagamento_corte_acabamento)
            # --------------------------------------------------------
            tab_pag = "pagamento_corte_acabamento"
            has_p = lambda c: _has_col(tab_pag, c)

            sel_p_datapag = "p.data_pagamento::date" if has_p("data_pagamento") else "NULL::date"
            sel_p_tipo = "p.tipo_servico" if has_p("tipo_servico") else "''::text"
            sel_p_cod = "p.codigo" if has_p("codigo") else "''::text"
            sel_p_desc = "p.descricao" if has_p("descricao") else "''::text"
            sel_p_cost = "p.costureira" if has_p("costureira") else "''::text"
            sel_p_qtd = "COALESCE(p.quantidade_finalizada,0)" if has_p("quantidade_finalizada") else "0::numeric"
            sel_p_vpeca = "COALESCE(p.valor_por_peca,0)" if has_p("valor_por_peca") else "0::numeric"
            sel_p_adi = "COALESCE(p.adiantamento,0)" if has_p("adiantamento") else "0::numeric"
            sel_p_descpecas = "COALESCE(p.desconto_pecas,0)" if has_p("desconto_pecas") else "0::numeric"
            sel_p_valdef = "COALESCE(p.valor_defeito,0)" if has_p("valor_defeito") else "0::numeric"
            sel_p_ajuda = "COALESCE(p.ajuda_custo,0)" if has_p("ajuda_custo") else "0::numeric"
            sel_p_boni = "COALESCE(p.bonificacao,0)" if has_p("bonificacao") else "0::numeric"
            sel_p_total = "COALESCE(p.total_pago,0)" if has_p("total_pago") else "0::numeric"
            # CORREÇÃO AQUI: usar FALSE em vez de 0 para coluna booleana
            sel_p_est = "COALESCE(p.estornado, FALSE)" if has_p("estornado") else "FALSE"

            # filtro serviço
            if has_p("tipo_servico"):
                cond_p_serv = "(%s='Todos' OR p.tipo_servico = %s)"
                p_serv_params = (serv, serv)
            else:
                cond_p_serv = "(%s='Todos' OR %s = %s)"  # placeholders queimados
                p_serv_params = (serv, serv)

            f_p_cod = "p.codigo" if has_p("codigo") else "''"
            f_p_desc = "p.descricao" if has_p("descricao") else "''"
            f_p_cost = "p.costureira" if has_p("costureira") else "''"

            sql_pag = f"""
                SELECT
                  {sel_p_datapag}                         AS data_pag,
                  {sel_p_tipo}                            AS tipo_servico,
                  {sel_p_cod}                             AS codigo,
                  {sel_p_desc}                            AS descricao,
                  {sel_p_cost}                            AS costureira,
                  {sel_p_qtd}                             AS qtd,
                  {sel_p_vpeca}                           AS v_peca,
                  ({sel_p_qtd} * {sel_p_vpeca})           AS base,
                  ({sel_p_adi} + {sel_p_descpecas} + {sel_p_valdef}) AS descontos,
                  ({sel_p_ajuda} + {sel_p_boni})          AS ajudas,
                  {sel_p_total}                           AS total
                FROM {schema}.{tab_pag} p
                WHERE {sel_p_datapag} BETWEEN %s AND %s
                  AND {cond_p_serv}
                  AND {sel_p_est} = FALSE  -- CORREÇÃO AQUI: usar FALSE em vez de 0
                  AND (%s = '' OR {f_p_cod} ILIKE %s OR {f_p_desc} ILIKE %s OR {f_p_cost} ILIKE %s)
                ORDER BY {sel_p_datapag} ASC, p.id ASC
            """
            p_pag = (ini_iso, fim_iso, *p_serv_params, termo, f"%{termo}%", f"%{termo}%", f"%{termo}%")
            cur.execute(sql_pag, p_pag)
            pag_rows = _fetch_all_dicts(cur)

            # Preencher tabela de pagamentos
            try:
                self._preencher_pagamentos(pag_rows)
            except Exception:
                pass

            # --------------------------------------------------------
            # 3) ENVIOS (c = controle_envio_cortes, d = envio_detalhes_tamanho)
            # --------------------------------------------------------
            tab_env_cab = "controle_envio_cortes"
            tab_env_det = "envio_detalhes_tamanho"
            has_c = lambda c: _has_col(tab_env_cab, c)
            has_d = lambda c: _has_col(tab_env_det, c)

            c_data_envio = "c.data_envio::date" if has_c("data_envio") else "NULL::date"
            c_codigo = "c.codigo" if has_c("codigo") else "''::text"
            c_desc = "c.descricao" if has_c("descricao") else "''::text"
            c_cost = "c.costureira" if has_c("costureira") else "''::text"
            d_qtd = "COALESCE(d.quantidade,0)" if has_d("quantidade") else "0::int"
            d_qtdpil = "COALESCE(d.quantidade_pilotos,0)" if has_d("quantidade_pilotos") else "0::int"
            d_vpeca = "COALESCE(d.valor_peca,0)" if has_d("valor_peca") else "0::numeric"

            sql_env = f"""
                SELECT
                  {c_data_envio} AS data_envio,
                  {c_codigo}     AS codigo,
                  {c_desc}       AS descricao,
                  {c_cost}       AS costureira,
                  SUM({d_qtd})   AS qtd,
                  SUM({d_qtdpil}) AS pilotos,
                  MAX({d_vpeca}) AS valor_peca
                FROM {schema}.{tab_env_cab} c
                LEFT JOIN {schema}.{tab_env_det} d ON d.envio_id = c.id
                WHERE {c_data_envio} BETWEEN %s AND %s
                  AND (%s = '' OR {c_codigo} ILIKE %s OR {c_desc} ILIKE %s OR {c_cost} ILIKE %s)
                GROUP BY 1,2,3,4
                ORDER BY 1 ASC, 2 ASC
            """
            p_env = (ini_iso, fim_iso, termo, f"%{termo}%", f"%{termo}%", f"%{termo}%")
            try:
                cur.execute(sql_env, p_env)
                env_rows = _fetch_all_dicts(cur)
            except Exception:
                env_rows = []
            try:
                self._preencher_envios(env_rows)
            except Exception:
                pass

            # --------------------------------------------------------
            # 4) RETORNOS / FINALIZADOS (cf = cortes_finalizados)
            # --------------------------------------------------------
            tab_cf = "cortes_finalizados"
            has_cf = lambda c: _has_col(tab_cf, c)

            cf_data = "cf.data_final::date" if has_cf("data_final") else (
                "cf.data_finalizacao::date" if has_cf("data_finalizacao") else "NULL::date")
            cf_cod = "cf.codigo" if has_cf("codigo") else "''::text"
            cf_desc = "cf.descricao" if has_cf("descricao") else "''::text"
            cf_cost = "cf.costureira" if has_cf("costureira") else "''::text"
            cf_valpec = "COALESCE(cf.valor_peca,0)" if has_cf("valor_peca") else "0::numeric"

            # quantidade finalizada: usa total_pecas se existir; senão soma as colunas por tamanho (se existirem)
            if has_cf("total_pecas"):
                cf_qtd = "COALESCE(cf.total_pecas,0)"
            else:
                soma_cols = []
                for ccol in ("qtd_pp", "qtd_p", "qtd_m", "qtd_g", "qtd_gg", "qtd_g1", "qtd_g2", "qtd_g3"):
                    soma_cols.append(f"COALESCE(cf.{ccol},0)") if has_cf(ccol) else None
                soma_cols = [s for s in soma_cols if s]
                cf_qtd = "+".join(soma_cols) if soma_cols else "0::int"

            sql_ret = f"""
                SELECT
                  {cf_data} AS data_final,
                  {cf_cod}  AS codigo,
                  {cf_desc} AS descricao,
                  {cf_cost} AS costureira,
                  ({cf_qtd}) AS qtd,
                  {cf_valpec} AS valor_peca
                FROM {schema}.{tab_cf} cf
                WHERE {cf_data} BETWEEN %s AND %s
                  AND (%s = '' OR {cf_cod} ILIKE %s OR {cf_desc} ILIKE %s OR {cf_cost} ILIKE %s)
                ORDER BY {cf_data} ASC, {cf_cod} ASC
            """
            p_ret = (ini_iso, fim_iso, termo, f"%{termo}%", f"%{termo}%", f"%{termo}%")
            try:
                cur.execute(sql_ret, p_ret)
                ret_rows = _fetch_all_dicts(cur)
            except Exception:
                ret_rows = []
            try:
                self._preencher_retornos(ret_rows)
            except Exception:
                pass

            # --------------------------------------------------------
            # 5) Adiantamentos
            # --------------------------------------------------------
            try:
                tab_ad = "adiantamento_faccao"
                if _has_col(tab_ad, "data_hora") and _has_col(tab_ad, "valor"):
                    ad_data = "a.data_hora::date"
                    ad_codigo = "a.codigo_modelo" if _has_col(tab_ad, "codigo_modelo") else "''::text"
                    ad_faccao = "a.faccao" if _has_col(tab_ad, "faccao") else "''::text"
                    ad_val = "COALESCE(a.valor,0)"
                    ad_forma = "a.forma_pagamento" if _has_col(tab_ad, "forma_pagamento") else "''::text"
                    ad_parcelas = "COALESCE(a.parcelas,1)" if _has_col(tab_ad, "parcelas") else "1::int"

                    sql_ad = f"""
                        SELECT 
                          {ad_data} AS data,
                          {ad_codigo} AS codigo_modelo,
                          {ad_faccao} AS faccao,
                          {ad_val} AS valor,
                          {ad_forma} AS forma_pagamento,
                          {ad_parcelas} AS parcelas
                        FROM {schema}.{tab_ad} a
                        WHERE {ad_data} BETWEEN %s AND %s
                          AND (%s = '' OR {ad_codigo} ILIKE %s OR {ad_faccao} ILIKE %s)
                        ORDER BY {ad_data} ASC
                    """
                    p_ad = (ini_iso, fim_iso, termo, f"%{termo}%", f"%{termo}%")
                    cur.execute(sql_ad, p_ad)
                    ad_rows = _fetch_all_dicts(cur)
                    try:
                        self._preencher_adiantamentos(ad_rows)
                    except Exception:
                        pass
            except Exception:
                pass

            # Fechar cursor
            try:
                cur.close()
            except Exception:
                pass

            # Atualizar KPIs
            self._atualizar_kpis(pag_rows, env_rows, ret_rows, ad_rows)

        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Erro SQL", f"Falha ao carregar dados:\n{e}")

    # ======= Exportação / Relatório =======
    def _export_csv(self):
        if not getattr(self, "_cache_rows", None):
            messagebox.showinfo("Exportar", "Busque primeiro."); return
        fn = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")],
                                          initialfile=f"fechamento_{self._cache_rows['filtros']['ini']}_a_{self._cache_rows['filtros']['fim']}.csv")
        if not fn: return
        with open(fn, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["SEÇÃO","COLUNAS..."])
            # Consolidado (le da tree_sum)
            w.writerow(["CONSOLIDADO","modelo","descricao","destino","costureira","servico","env","ret","falt","def","valor_pago"])
            for iid in self.tree_sum.get_children():
                w.writerow(["CONSOLIDADO"] + list(self.tree_sum.item(iid)["values"]))
            # Envios
            w.writerow([]); w.writerow(["ENVIOS","data_envio","ordem_corte","codigo_corte","descricao_corte","servico","destino","qtd_total","pilotos","valor_peca"])
            for r in self._cache_rows["env"]:
                w.writerow(["ENVIOS", r.get("data_envio"), r.get("ordem_corte"), r.get("codigo_corte"), r.get("descricao_corte"),
                            r.get("servico"), r.get("destino"), r.get("qtd_total"), r.get("pilotos"), r.get("valor_peca")])
            # Retornos
            w.writerow([]); w.writerow(["RETORNOS","data","codigo","tamanho","qtd","copias","defeito","valor_peca","obs"])
            for r in self._cache_rows["ret"]:
                w.writerow(["RETORNOS", r.get("data"), r.get("codigo"), r.get("tamanho"), r.get("qtd"),
                            r.get("copias"), r.get("defeito"), r.get("valor_peca"), r.get("obs")])
            # Pagamentos
            w.writerow([]); w.writerow(["PAGAMENTOS","data_pag","tipo_servico","codigo","descricao","costureira","qtd","v_peca","base","descontos","ajudas","total"])
            for r in self._cache_rows["pag"]:
                w.writerow(["PAGAMENTOS", r.get("data_pag"), r.get("tipo_servico"), r.get("codigo"), r.get("descricao"), r.get("costureira"),
                            r.get("qtd"), r.get("v_peca"), r.get("base"), r.get("descontos"), r.get("ajudas"), r.get("total")])
            # Adiantamentos
            w.writerow([]); w.writerow(["ADIANTAMENTOS","data","codigo_modelo","faccao","valor","forma_pagamento","parcelas"])
            for r in self._cache_rows["adi"]:
                w.writerow(["ADIANTAMENTOS", r.get("data"), r.get("codigo_modelo"), r.get("faccao"), r.get("valor"),
                            r.get("forma_pagamento"), r.get("parcelas")])
            # Histórico
            w.writerow([]); w.writerow(["HISTORICO","data","evento","corte_id","envio_id","entrada_id","descricao","setor","quant","valor","status"])
            for r in self._cache_rows["his"]:
                w.writerow(["HISTORICO", r.get("data"), r.get("evento"), r.get("corte_id"), r.get("envio_id"), r.get("entrada_id"),
                            r.get("descricao"), r.get("setor"), r.get("quant"), r.get("valor"), r.get("status")])
        messagebox.showinfo("Exportar", f"Arquivo salvo em:\n{fn}")

    def _report_html(self):
        if not getattr(self, "_cache_rows", None):
            messagebox.showinfo("Relatório", "Busque primeiro."); return
        ini = self._cache_rows["filtros"]["ini"]; fim = self._cache_rows["filtros"]["fim"]
        serv = self._cache_rows["filtros"]["serv"]; termo = self._cache_rows["filtros"]["termo"]
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out = os.path.join(os.getcwd(), f"fechamento_mensal_{ini}_a_{fim}_{now}.html")

        def rows_to_html(rows, keys, headers):
            th = "".join(f"<th>{h}</th>" for h in headers)
            tb = "".join("<tr>" + "".join(f"<td>{(r.get(k,'') if not isinstance(r.get(k,''), float) else f'{r.get(k,0.0):.2f}')}</td>" for k in keys) + "</tr>" for r in rows)
            return f"<table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table>"

        css = f"""
        <style>
        body{{font-family:Arial,Helvetica,sans-serif;margin:20px;background:{self.theme.cor_fundo};color:{self.theme.cor_texto};}}
        h1{{font-size:20px;margin:0}}
        h2{{font-size:16px;margin-top:20px;border-bottom:1px solid {self.theme.cor_borda};padding-bottom:4px}}
        table{{width:100%;border-collapse:collapse;margin-top:8px}}
        th,td{{border:1px solid {self.theme.cor_borda};padding:6px;font-size:12px}}
        th{{background:{self.theme.cor_primaria};color:white;text-align:left}}
        .kpi{{display:flex;gap:12px;flex-wrap:wrap;margin:10px 0}}
        .card{{border:1px solid {self.theme.cor_borda};border-radius:8px;padding:10px;min-width:160px;background:{self.theme.cor_terciaria};}}
        .right{{text-align:right}}
        .muted{{font-size:12px;color:#bbb}}
        .break{{page-break-after:always;margin-top:18px}}
        </style>
        """
        env = self._cache_rows["env"]; ret = self._cache_rows["ret"]; pag = self._cache_rows["pag"]; adi = self._cache_rows["adi"]; his = self._cache_rows["his"]

        total_env = sum(int(r.get("qtd_total") or 0) for r in env)
        total_ret = sum(int(r.get("qtd") or 0) for r in ret)
        total_falt = max(total_env - total_ret - sum(int(r.get("defeito") or 0) for r in ret), 0)
        total_def = sum(int(r.get("defeito") or 0) for r in ret)
        total_pag = sum(float(r.get("total") or 0) for r in pag)
        total_adi = sum(float(r.get("valor") or 0) for r in adi)

        # Consolidado (pega da tree_sum)
        cons_rows = []
        for iid in self.tree_sum.get_children():
            v = self.tree_sum.item(iid)["values"]
            cons_rows.append(dict(modelo=v[0], descricao=v[1], destino=v[2], costureira=v[3], servico=v[4],
                                  env=v[5], ret=v[6], falt=v[7], defe=v[8], valor_pago=v[9]))

        html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'>{css}</head><body>
        <h1>Fechamento Mensal</h1>
        <div class="muted">Período: {ini} a {fim} • Serviço: {serv} • Busca: {termo or '-'}</div>
        <div class="kpi">
            <div class="card">Peças Enviadas<br><b>{total_env}</b></div>
            <div class="card">Peças Retornadas<br><b>{total_ret}</b></div>
            <div class="card">Faltantes<br><b>{total_falt}</b></div>
            <div class="card">Defeitos<br><b>{total_def}</b></div>
            <div class="card">Total Pago<br><b>R$ {total_pag:.2f}</b></div>
            <div class="card">Adiantamentos<br><b>R$ {total_adi:.2f}</b></div>
        </div>

        <h2>Consolidado por Modelo/Destino/Costureira/Serviço</h2>
        {rows_to_html(cons_rows, ['modelo','descricao','destino','costureira','servico','env','ret','falt','defe','valor_pago'],
                      ['Modelo','Descrição','Destino','Costureira','Serviço','Env.','Ret.','Falt.','Def.','Valor Pago'])}

        <div class="break"></div>
        <h2>Envios</h2>
        {rows_to_html(env, ['data_envio','ordem_corte','codigo_corte','descricao_corte','servico','destino','qtd_total','pilotos','valor_peca'],
                      ['Data','Ordem','Código','Descrição','Serviço','Destino','Qtd','Pilotos','V.Pça'])}

        <div class="break"></div>
        <h2>Retornos/Entradas</h2>
        {rows_to_html(ret, ['data','codigo','tamanho','qtd','copias','defeito','valor_peca','obs'],
                      ['Data','Código','Tam.','Qtd','Cópias','Defeito','V.Pça','Obs'])}

        <div class="break"></div>
        <h2>Pagamentos</h2>
        {rows_to_html(pag, ['data_pag','tipo_servico','codigo','descricao','costureira','qtd','v_peca','base','descontos','ajudas','total'],
                      ['Data','Serviço','Código','Descrição','Costureira','Qtd','V.Pça','Base','Descontos','Ajuda','Total'])}

        <div class="break"></div>
        <h2>Adiantamentos</h2>
        {rows_to_html(adi, ['data','codigo_modelo','faccao','valor','forma_pagamento','parcelas'],
                      ['Data','Modelo','Facção','Valor','Forma','Parcelas'])}

        <div class="break"></div>
        <h2>Histórico de Serviço</h2>
        {rows_to_html(his, ['data','evento','corte_id','envio_id','entrada_id','descricao','setor','quant','valor','status'],
                      ['Data','Evento','Corte','Envio','Entrada','Descrição','Setor','Qtd','Valor','Status'])}

        <p class="muted">Relatório gerado automaticamente a partir do banco (PostgreSQL).</p>
        </body></html>"""

        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        if os.name == "nt":
            os.startfile(out)
        else:
            webbrowser.open_new_tab(out)
        messagebox.showinfo("Relatório", f"Relatório gerado:\n{out}\nUse Ctrl+P para imprimir.")

# --------- Standalone ---------
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = ctk.CTk()
    app.title(FechamentoMensalPage.PAGE_TITLE)
    app.geometry("1200x800")
    # tema de exemplo
    app.cor_fundo="#0d1117"; app.cor_primaria="#1f2d44"; app.cor_secundaria="#0b1220"; app.cor_terciaria="#111827"
    app.cor_texto="#e5e7eb"; app.cor_selecao="#2563eb"; app.cor_hover="#1d4ed8"; app.cor_imprimir="#9333ea"; app.cor_borda="#334155"
    page = FechamentoMensalPage(app, host=app)
    page.pack(fill="both", expand=True)
    app.mainloop()
