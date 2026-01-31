# -*- coding: utf-8 -*-
"""
CONSULTAR_SERVICOS.py - Histórico Completo de Serviços por Prestador
Versão PostgreSQL - Acessa via BANCO_DE_DADOS_PG

SISTEMA COMPLETAMENTE INTEGRADO COM TEMAS DO MENU PRINCIPAL
PADRÃO IDÊNTICO AO CADASTRO_DE_CORTE
"""

from __future__ import annotations
import os, csv, webbrowser
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
import customtkinter as ctk
import TEMAS
from tkinter import ttk, messagebox, filedialog

# ---------- Acesso PG ----------
try:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception as err:
    def get_conn():
        raise RuntimeError("BANCO_DE_DADOS_PG indisponível: " + str(err))


    def get_schema():
        return "public"


    def require_ready(essentials=None):
        return False, "Módulo de acesso não disponível"


# ---------- Utilitários de Data ----------
def _first_day_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def _first_day_of_semester(d: date) -> date:
    semester = 1 if d.month <= 6 else 7
    return date(d.year, semester, 1)


def _last_day_of_month(d: date) -> date:
    nd = d.replace(day=28) + timedelta(days=4)
    return nd - timedelta(days=nd.day)


def _last_day_of_semester(d: date) -> date:
    semester = 6 if d.month <= 6 else 12
    return date(d.year, semester, 31)


def _dt(s: str) -> str:
    """Normaliza para 'YYYY-MM-DD'."""
    if not s: return ""
    s = s.strip()
    if "/" in s:
        try:
            d = datetime.strptime(s, "%d/%m/%Y").date()
            return d.strftime("%Y-%m-%d")
        except Exception:
            return s
    return s


# ---------- Página Principal ----------
class HistoricoServicosPage(ctk.CTkFrame):
    PAGE_TITLE = "Histórico de Serviços por Prestador"

    def __init__(self, parent, sistema=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Guardar referência ao sistema principal para integração de temas
        self.sistema = sistema or parent

        # CORREÇÃO: Aplicar tema imediatamente ao inicializar
        self.obter_cores_por_tema()

        # Inicializar variáveis de controle
        self.ini_var = ctk.StringVar()
        self.fim_var = ctk.StringVar()
        self.prestador_var = ctk.StringVar()
        self.servico_var = ctk.StringVar(value="Todos")
        self.periodo_var = ctk.StringVar(value="Personalizado")
        self.todos_registros_var = ctk.BooleanVar(value=False)

        # Inicializar widgets como None
        self.tree = None
        self.kpi_envios = None
        self.kpi_retornos = None
        self.kpi_pagos = None
        self.kpi_valor = None
        self.kpi_media = None

        # Configurar interface
        self.setup_ui()
        self._carregar_prestadores()

    def obter_cores_por_tema(self):
        """Define cores de texto dinamicamente baseado no tema atual - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        # CORREÇÃO: Verificar se o sistema principal existe e tem cores definidas
        if hasattr(self, 'sistema') and self.sistema and hasattr(self.sistema, 'cor_fundo'):
            try:
                # Usar cores do sistema principal
                self.cor_fundo = self.sistema.cor_fundo
                self.cor_primaria = self.sistema.cor_primaria
                self.cor_secundaria = self.sistema.cor_secundaria
                self.cor_texto = self.sistema.cor_texto
                self.cor_texto_entry = getattr(self.sistema, 'cor_texto_entry', self.sistema.cor_texto)
                self.cor_placeholder = getattr(self.sistema, 'cor_placeholder', "#888888")
                self.cor_borda = self.sistema.cor_borda
                self.cor_hover = self.sistema.cor_hover
                self.cor_terciaria = getattr(self.sistema, 'cor_terciaria', self.sistema.cor_secundaria)
                return
            except Exception as e:
                print(f"⚠️ Erro ao obter cores do sistema: {e}")

        # CORREÇÃO: Fallback melhorado
        try:
            # Tentar obter do parent se disponível
            parent = self.master
            while parent:
                if hasattr(parent, 'cor_fundo'):
                    self.cor_fundo = parent.cor_fundo
                    self.cor_primaria = parent.cor_primaria
                    self.cor_secundaria = parent.cor_secundaria
                    self.cor_texto = parent.cor_texto
                    self.cor_texto_entry = getattr(parent, 'cor_texto_entry', parent.cor_texto)
                    self.cor_placeholder = getattr(parent, 'cor_placeholder', "#888888")
                    self.cor_borda = parent.cor_borda
                    self.cor_hover = parent.cor_hover
                    self.cor_terciaria = getattr(parent, 'cor_terciaria', parent.cor_secundaria)
                    return
                parent = getattr(parent, 'master', None)
        except Exception:
            pass

        # Fallback baseado no tema do CTk
        tema_atual = ctk.get_appearance_mode()
        if tema_atual == "Dark":
            self.cor_fundo = "#020617"
            self.cor_primaria = "#1f2937"
            self.cor_secundaria = "#111827"
            self.cor_texto = "#e5e7eb"
            self.cor_texto_entry = "#e5e7eb"
            self.cor_placeholder = "#888888"
            self.cor_borda = "#273244"
            self.cor_hover = "#334155"
            self.cor_terciaria = "#1e293b"
        else:
            self.cor_fundo = "#ffffff"
            self.cor_primaria = "#3a7ebf"
            self.cor_secundaria = "#f0f0f0"
            self.cor_texto = "black"
            self.cor_texto_entry = "black"
            self.cor_placeholder = "#666666"
            self.cor_borda = "#cccccc"
            self.cor_hover = "#2e4a66"
            self.cor_terciaria = "#e5e5e5"

    def configurar_treeview_theme(self):
        """Configura as cores da Treeview baseado no tema atual - MESMO ESTILO DO CADASTRO_DE_CORTE"""
        # CORREÇÃO: Garantir que as cores estão atualizadas
        self.obter_cores_por_tema()

        if not hasattr(self, 'style'):
            self.style = ttk.Style()

        self.style.theme_use('default')

        tema_atual = ctk.get_appearance_mode()

        if tema_atual == "Dark":
            cor_fundo = self.cor_secundaria
            cor_texto = self.cor_texto
            cor_campo = self.cor_secundaria
            cor_selecao = self.cor_primaria
        else:
            cor_fundo = "#f0f0f0"
            cor_texto = "black"
            cor_campo = "#f0f0f0"
            cor_selecao = self.cor_primaria

        self.style.configure("Custom.Treeview",
                             background=cor_fundo,
                             foreground=cor_texto,
                             fieldbackground=cor_campo,
                             borderwidth=0,
                             highlightthickness=0,
                             rowheight=25)

        self.style.configure("Custom.Treeview.Heading",
                             background=self.cor_primaria,
                             foreground=self.cor_texto,
                             relief="flat",
                             borderwidth=1,
                             font=('Arial', 10, 'bold'))

        self.style.map('Custom.Treeview',
                       background=[('selected', cor_selecao)],
                       foreground=[('selected', "white")])

    def setup_ui(self):
        """Configuração completa da interface gráfica com MESMO ESTILO DO CADASTRO_DE_CORTE"""
        # CORREÇÃO: Atualizar cores antes de construir a interface
        self.obter_cores_por_tema()

        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ========== CABEÇALHO - MESMO ESTILO DO CADASTRO_DE_CORTE ==========
        header_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        header_frame.pack(fill="x", pady=(0, 10))

        # Título alinhado à esquerda
        ctk.CTkLabel(header_frame, text="HISTÓRICO DE SERVIÇOS POR PRESTADOR",
                     font=("Arial", 18, "bold"), text_color=self.cor_texto).pack(side="left", padx=10)

        # ========== FILTROS - MESMO ESTILO DO CADASTRO_DE_CORTE ==========
        filtros_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        filtros_frame.pack(fill="x", pady=5)

        # Linha 1: Período e datas
        periodo_frame = ctk.CTkFrame(filtros_frame, fg_color=self.cor_fundo)
        periodo_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(periodo_frame, text="Período:", width=80, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        periodo_combo = ctk.CTkComboBox(periodo_frame, values=[
            "Personalizado", "Esta Semana", "Semana Passada", "Este Mês",
            "Mês Passado", "Este Semestre", "Semestre Passado"
            , "Todos"
        ], width=150, variable=self.periodo_var, command=self._on_periodo_change,
                                        fg_color=self.cor_secundaria,
                                        border_color=self.cor_borda,
                                        text_color=self.cor_texto,
                                        button_color=self.cor_primaria,
                                        button_hover_color=self.cor_hover)
        periodo_combo.pack(side="left", padx=5)

        ctk.CTkCheckBox(
            periodo_frame,
            text="Todos os registros",
            variable=self.todos_registros_var,
            command=self._on_todos_registros_toggle,
            text_color=self.cor_texto
        ).pack(side="left", padx=(10, 5))

        ctk.CTkLabel(periodo_frame, text="De:", width=30, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=(15, 5))

        hoje = date.today()
        self.ini_var.set(_first_day_of_month(hoje).strftime("%Y-%m-%d"))

        self.ini_entry = ctk.CTkEntry(periodo_frame, width=120,
                                      fg_color=self.cor_secundaria,
                                      border_color=self.cor_borda,
                                      text_color=self.cor_texto_entry,
                                      textvariable=self.ini_var)
        self.ini_entry.pack(side="left", padx=5)
        ctk.CTkButton(
            periodo_frame,
            text="📅",
            width=28,
            command=lambda: self._abrir_calendario(self.ini_entry),
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(periodo_frame, text="Até:", width=30, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=(15, 5))

        self.fim_var.set(_last_day_of_month(hoje).strftime("%Y-%m-%d"))
        self.fim_entry = ctk.CTkEntry(periodo_frame, width=120,
                                      fg_color=self.cor_secundaria,
                                      border_color=self.cor_borda,
                                      text_color=self.cor_texto_entry,
                                      textvariable=self.fim_var)
        self.fim_entry.pack(side="left", padx=5)
        ctk.CTkButton(
            periodo_frame,
            text="📅",
            width=28,
            command=lambda: self._abrir_calendario(self.fim_entry),
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=(0, 5))

        # Linha 2: Prestador e Serviço
        prestador_frame = ctk.CTkFrame(filtros_frame, fg_color=self.cor_fundo)
        prestador_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(prestador_frame, text="Prestador:", width=80, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        self.prestador_combo = ctk.CTkComboBox(prestador_frame, values=[], width=200,
                                               variable=self.prestador_var,
                                               fg_color=self.cor_secundaria,
                                               border_color=self.cor_borda,
                                               text_color=self.cor_texto,
                                               button_color=self.cor_primaria,
                                               button_hover_color=self.cor_hover)
        self.prestador_combo.pack(side="left", padx=5)

        ctk.CTkLabel(prestador_frame, text="Serviço:", width=80, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=(15, 5))

        serv_combo = ctk.CTkComboBox(prestador_frame, values=[
            "Todos", "Facção", "Bordado", "Caseador", "Botões",
            "Estamparia", "Interna", "Tingimento", "Outros Trabalhos"
        ], width=150, variable=self.servico_var,
                                     fg_color=self.cor_secundaria,
                                     border_color=self.cor_borda,
                                     text_color=self.cor_texto,
                                     button_color=self.cor_primaria,
                                     button_hover_color=self.cor_hover,
                                     command=lambda _: self._carregar_prestadores(self.servico_var.get()))
        serv_combo.pack(side="left", padx=5)

        # Botão buscar
        buscar_btn = ctk.CTkButton(prestador_frame, text="🔍 Buscar", width=100,
                                   command=self._search,
                                   fg_color=self.cor_primaria,
                                   hover_color=self.cor_hover,
                                   text_color=self.cor_texto,
                                   font=("Arial", 12))
        buscar_btn.pack(side="left", padx=(20, 5))

        # ========== KPIs - MESMO ESTILO DO CADASTRO_DE_CORTE ==========
        kpis_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        kpis_frame.pack(fill="x", pady=10)

        # Configurar grid para KPIs
        kpis_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.kpi_envios = self._criar_kpi(kpis_frame, 0, "Envios", "0")
        self.kpi_retornos = self._criar_kpi(kpis_frame, 1, "Retornos", "0")
        self.kpi_pagos = self._criar_kpi(kpis_frame, 2, "Pagamentos", "0")
        self.kpi_valor = self._criar_kpi(kpis_frame, 3, "Valor Total", "R$ 0,00")
        self.kpi_media = self._criar_kpi(kpis_frame, 4, "Tempo Médio", "0 dias")

        # ========== TABELAS (ABAS) ==========
        table_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        table_frame.pack(fill="both", expand=True, pady=10)

        self.configurar_treeview_theme()

        tabs = ctk.CTkTabview(table_frame, fg_color=self.cor_fundo)
        tabs.pack(fill="both", expand=True)

        tab_hist = tabs.add("Histórico")
        tab_defeitos = tabs.add("Peças com Defeito")

        # ---- Aba Histórico ----
        columns = ["data", "tipo", "servico", "codigo", "descricao", "quantidade", "valor_unit", "valor_total",
                   "status"]
        headers = ["Data", "Tipo", "Serviço", "Código", "Descrição", "Quantidade", "V. Unitário", "V. Total", "Status"]
        widths = [100, 120, 120, 100, 200, 80, 100, 100, 120]
        anchors = ["center", "center", "center", "center", "w", "center", "e", "e", "center"]

        self.tree = ttk.Treeview(tab_hist, columns=columns, show="headings",
                                 height=15, style="Custom.Treeview")

        for col, header, width, anchor in zip(columns, headers, widths, anchors):
            self.tree.heading(col, text=header)
            self.tree.column(col, width=width, anchor=anchor)

        v_scrollbar = ttk.Scrollbar(tab_hist, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tab_hist, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        tab_hist.grid_rowconfigure(0, weight=1)
        tab_hist.grid_columnconfigure(0, weight=1)

        # ---- Aba Peças com Defeito ----
        def_columns = ["data", "envio_id", "codigo", "descricao", "tamanho", "defeitos"]
        def_headers = ["Data", "Envio", "Código", "Descrição", "Tamanho", "Defeitos"]
        def_widths = [110, 80, 110, 320, 90, 90]
        def_anchors = ["center", "center", "center", "w", "center", "center"]

        self.defeito_tree = ttk.Treeview(tab_defeitos, columns=def_columns, show="headings",
                                         height=15, style="Custom.Treeview")

        for col, header, width, anchor in zip(def_columns, def_headers, def_widths, def_anchors):
            self.defeito_tree.heading(col, text=header)
            self.defeito_tree.column(col, width=width, anchor=anchor)

        v_def_scroll = ttk.Scrollbar(tab_defeitos, orient="vertical", command=self.defeito_tree.yview)
        h_def_scroll = ttk.Scrollbar(tab_defeitos, orient="horizontal", command=self.defeito_tree.xview)
        self.defeito_tree.configure(yscrollcommand=v_def_scroll.set, xscrollcommand=h_def_scroll.set)

        self.defeito_tree.grid(row=0, column=0, sticky="nsew")
        v_def_scroll.grid(row=0, column=1, sticky="ns")
        h_def_scroll.grid(row=1, column=0, sticky="ew")

        tab_defeitos.grid_rowconfigure(0, weight=1)
        tab_defeitos.grid_columnconfigure(0, weight=1)

        self._atualizar_cores_linhas()

        # ========== BOTÕES DE AÇÃO - MESMO ESTILO DO CADASTRO_DE_CORTE ==========
        action_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        action_frame.pack(fill="x", pady=10)

        ctk.CTkButton(
            action_frame,
            text="📤 Exportar CSV",
            command=self._export_csv,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            font=("Arial", 12),
            width=140,
            height=35
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            action_frame,
            text="🖨️ Gerar Relatório",
            command=self._generate_report,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            font=("Arial", 12),
            width=140,
            height=35
        ).pack(side="right", padx=5)

    def _atualizar_cores_linhas(self):
        """Atualiza cores das linhas alternadas da treeview"""
        if ctk.get_appearance_mode() == "Dark":
            cor_linha_par = self.cor_fundo
            cor_linha_impar = self.cor_secundaria
        else:
            cor_linha_par = "#ffffff"
            cor_linha_impar = "#f0f0f0"

        if hasattr(self, 'tree') and self.tree:
            self.tree.tag_configure("oddrow", background=cor_linha_impar)
            self.tree.tag_configure("evenrow", background=cor_linha_par)

    # CORREÇÃO: Adicionar método para atualizar tema dinamicamente
    def atualizar_tema(self):
        """Atualiza todas as cores quando o tema muda"""
        print("🎨 Atualizando tema na página de Consulta de Serviços...")
        self.obter_cores_por_tema()
        self.configurar_treeview_theme()
        self._atualizar_cores_linhas()

        # Atualizar cores de todos os widgets
        self._atualizar_widgets_tema()

    def _atualizar_widgets_tema(self):
        """Atualiza cores de todos os widgets filhos"""
        try:
            for widget in self.winfo_children():
                self._atualizar_widget_recursivo(widget)
        except Exception as e:
            print(f"⚠️ Erro ao atualizar widgets: {e}")

    def _atualizar_widget_recursivo(self, widget):
        """Atualiza recursivamente as cores dos widgets"""
        try:
            if isinstance(widget, ctk.CTkFrame):
                if widget.cget('fg_color') != 'transparent':
                    widget.configure(fg_color=self.cor_fundo)
            elif isinstance(widget, ctk.CTkButton):
                widget.configure(
                    fg_color=self.cor_primaria,
                    hover_color=self.cor_hover,
                    text_color=self.cor_texto
                )
            elif isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=self.cor_texto)
            elif isinstance(widget, ctk.CTkEntry):
                widget.configure(
                    fg_color=self.cor_secundaria,
                    border_color=self.cor_borda,
                    text_color=self.cor_texto_entry
                )
            elif isinstance(widget, ctk.CTkComboBox):
                widget.configure(
                    fg_color=self.cor_secundaria,
                    border_color=self.cor_borda,
                    text_color=self.cor_texto,
                    button_color=self.cor_primaria,
                    button_hover_color=self.cor_hover
                )

            # Processar filhos recursivamente
            for child in widget.winfo_children():
                self._atualizar_widget_recursivo(child)

        except Exception as e:
            # Ignorar erros em widgets que não podem ser configurados
            pass

    def _criar_kpi(self, parent, col, title, value):
        """Cria um card KPI estilizado - MESMO ESTILO DO CADASTRO_DE_CORTE"""
        box = ctk.CTkFrame(parent, fg_color=self.cor_primaria, corner_radius=8)
        box.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
        box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(box, text=title, font=("Arial", 12),
                     text_color=self.cor_texto).grid(
            row=0, column=0, sticky="w", padx=12, pady=(8, 2)
        )

        lbl = ctk.CTkLabel(box, text=value,
                           font=("Arial", 14, "bold"),
                           text_color=self.cor_texto)
        lbl.grid(row=1, column=0, sticky="w", padx=12, pady=(2, 8))

        return lbl

    # ======= LÓGICA DE NEGÓCIO =======
    def _on_periodo_change(self, choice):
        hoje = date.today()
        if choice == "Todos":
            self.todos_registros_var.set(True)
            self._set_date_entries_state(False)
            return
        self.todos_registros_var.set(False)
        self._set_date_entries_state(True)
        if choice == "Esta Semana":
            inicio = _first_day_of_week(hoje)
            fim = hoje
        elif choice == "Semana Passada":
            inicio = _first_day_of_week(hoje) - timedelta(days=7)
            fim = inicio + timedelta(days=6)
        elif choice == "Este Mês":
            inicio = _first_day_of_month(hoje)
            fim = _last_day_of_month(hoje)
        elif choice == "Mês Passado":
            primeiro_este_mes = _first_day_of_month(hoje)
            fim = primeiro_este_mes - timedelta(days=1)
            inicio = _first_day_of_month(fim)
        elif choice == "Este Semestre":
            inicio = _first_day_of_semester(hoje)
            fim = _last_day_of_semester(hoje)
        elif choice == "Semestre Passado":
            if hoje.month <= 6:
                inicio = date(hoje.year - 1, 7, 1)
                fim = date(hoje.year - 1, 12, 31)
            else:
                inicio = date(hoje.year, 1, 1)
                fim = date(hoje.year, 6, 30)
        else:  # Personalizado
            return

        self.ini_var.set(inicio.strftime("%Y-%m-%d"))
        self.fim_var.set(fim.strftime("%Y-%m-%d"))

    def _on_todos_registros_toggle(self):
        marcado = bool(self.todos_registros_var.get())
        if marcado:
            self.periodo_var.set("Todos")
            self._set_date_entries_state(False)
        else:
            if self.periodo_var.get() == "Todos":
                self.periodo_var.set("Personalizado")
            self._set_date_entries_state(True)

    def _set_date_entries_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.ini_entry.configure(state=state)
        self.fim_entry.configure(state=state)

    def _abrir_calendario(self, entry):
        from datetime import datetime
        import calendar as _cal

        def setar_data(d):
            if self.todos_registros_var.get():
                self.todos_registros_var.set(False)
                self._set_date_entries_state(True)
            entry.delete(0, "end")
            entry.insert(0, d.strftime("%d/%m/%Y"))
            self.periodo_var.set("Personalizado")
            top.destroy()

        top = ctk.CTkToplevel(self)
        top.title("Calendário")
        top.resizable(False, False)

        W, H = 300, 300
        self.update_idletasks()
        top.update_idletasks()

        ex = entry.winfo_rootx()
        ey = entry.winfo_rooty()
        eh = entry.winfo_height()

        x = ex
        y = ey + eh + 6

        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        if x + W > sw:
            x = sw - W - 10
        if y + H > sh:
            y = ey - H - 6

        top.geometry(f"{W}x{H}+{x}+{y}")

        top.transient(self)
        top.grab_set()

        now = datetime.now()
        ano = now.year
        mes = now.month

        nav = ctk.CTkFrame(top)
        nav.pack(fill="x", padx=10, pady=5)

        lbl_mes = ctk.CTkLabel(nav, text=f"{_cal.month_name[mes]} {ano}", font=("Arial", 14))
        ctk.CTkButton(nav, text="<", width=30, command=lambda: mudar_mes(-1)).pack(side="left")
        lbl_mes.pack(side="left", expand=True)
        ctk.CTkButton(nav, text=">", width=30, command=lambda: mudar_mes(1)).pack(side="right")

        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        frame_dias = ctk.CTkFrame(top)
        frame_dias.pack(fill="both", expand=True, padx=10, pady=5)

        for i, dia in enumerate(dias_semana):
            lbl = ctk.CTkLabel(frame_dias, text=dia, width=30, height=30)
            lbl.grid(row=0, column=i, padx=2, pady=2)

        def mudar_mes(delta):
            nonlocal mes, ano
            mes += delta
            if mes > 12:
                mes = 1
                ano += 1
            elif mes < 1:
                mes = 12
                ano -= 1
            lbl_mes.configure(text=f"{_cal.month_name[mes]} {ano}")
            desenhar_calendario()

        def desenhar_calendario():
            for w in frame_dias.grid_slaves():
                if int(w.grid_info()["row"]) > 0:
                    w.destroy()

            cal = _cal.monthcalendar(ano, mes)
            for i, semana in enumerate(cal):
                for j, dia in enumerate(semana):
                    if dia == 0:
                        continue
                    btn = ctk.CTkButton(
                        frame_dias,
                        text=str(dia),
                        width=30,
                        height=30,
                        command=lambda d=dia: setar_data(datetime(ano, mes, d))
                    )
                    btn.grid(row=i + 1, column=j, padx=2, pady=2)

        desenhar_calendario()

    def _carregar_prestadores(self, tipo_servico="Todos"):
        """Carrega lista de prestadores do banco, com filtro opcional por tipo."""
        try:
            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()
            tipo_servico = (tipo_servico or "Todos").strip()
            filtrar_tipo = tipo_servico != "Todos"

            prestadores = set()

            # De cadastro_faccoes
            try:
                if filtrar_tipo:
                    cur.execute(
                        f"""
                        SELECT DISTINCT nome
                        FROM {schema}.cadastro_faccoes
                        WHERE nome IS NOT NULL AND tipo_prestador = %s
                        """,
                        (tipo_servico,),
                    )
                else:
                    cur.execute(f"SELECT DISTINCT nome FROM {schema}.cadastro_faccoes WHERE nome IS NOT NULL")
                prestadores.update(r[0] for r in cur.fetchall())
            except Exception:
                pass

            # De controle_envio_cortes
            if not filtrar_tipo:
                for col in ["costureira", "destino", "faccao"]:
                    try:
                        cur.execute(f"SELECT DISTINCT {col} FROM {schema}.controle_envio_cortes WHERE {col} IS NOT NULL")
                        prestadores.update(r[0] for r in cur.fetchall())
                    except Exception:
                        pass

            # De pagamento_corte_acabamento
            if not filtrar_tipo:
                try:
                    cur.execute(
                        f"SELECT DISTINCT costureira FROM {schema}.pagamento_corte_acabamento WHERE costureira IS NOT NULL")
                    prestadores.update(r[0] for r in cur.fetchall())
                except Exception:
                    pass

            # De envios_cortes (por prestador_id)
            try:
                if filtrar_tipo:
                    cur.execute(
                        f"""SELECT DISTINCT cf.nome
                               FROM {schema}.envios_cortes ec
                               JOIN {schema}.cadastro_faccoes cf ON ec.prestador_id = cf.id
                               WHERE cf.nome IS NOT NULL AND cf.tipo_prestador = %s""",
                        (tipo_servico,),
                    )
                else:
                    cur.execute(
                        f"""SELECT DISTINCT cf.nome
                               FROM {schema}.envios_cortes ec
                               JOIN {schema}.cadastro_faccoes cf ON ec.prestador_id = cf.id
                               WHERE cf.nome IS NOT NULL"""
                    )
                prestadores.update(r[0] for r in cur.fetchall())
            except Exception:
                pass

            prestadores_list = sorted(list(prestadores))
            self.prestador_combo.configure(values=prestadores_list)
            if self.prestador_var.get() not in prestadores_list:
                self.prestador_var.set("")

            cur.close()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar prestadores: {e}")

    def _search(self):
        """Busca histórico consolidado"""
        try:
            todos_registros = bool(self.todos_registros_var.get())
            ini = _dt(self.ini_var.get())
            fim = _dt(self.fim_var.get())
            prestador = self.prestador_var.get().strip()
            servico = self.servico_var.get()

            if not todos_registros:
                if not ini or not fim:
                    messagebox.showwarning("Aviso", "Informe o período da busca")
                    return

            if not prestador:
                messagebox.showwarning("Aviso", "Selecione um prestador")
                return

            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()

            # Limpa tabelas
            for item in self.tree.get_children():
                self.tree.delete(item)
            if hasattr(self, "defeito_tree") and self.defeito_tree:
                for item in self.defeito_tree.get_children():
                    self.defeito_tree.delete(item)

            # KPIs
            total_envios = total_retornos = total_pagos = total_valor = total_dias = 0
            registros = 0

            def _filtro_data(campo: str):
                if todos_registros:
                    return "", []
                return f" AND {campo} BETWEEN %s AND %s", [ini, fim]

            # 1. ENVIOS
            try:
                filtro_data, params_data = _filtro_data("data_envio")
                sql_envios = f"""
                    SELECT data_envio, servico, codigo_corte, descricao_corte, 
                           COALESCE(quantidade_total, 0) as qtd, 
                           COALESCE(valor_peca, 0) as valor_unit,
                           status
                    FROM {schema}.controle_envio_cortes
                    WHERE 1=1
                    {filtro_data}
                      AND (costureira = %s OR destino = %s OR faccao = %s)
                      AND (%s = 'Todos' OR servico = %s)
                    ORDER BY data_envio
                """
                cur.execute(sql_envios, (*params_data, prestador, prestador, prestador, servico, servico))

                for row in cur.fetchall():
                    data, serv, codigo, desc, qtd, valor_unit, status = row
                    valor_total = qtd * valor_unit

                    tag = 'evenrow' if registros % 2 == 0 else 'oddrow'
                    self.tree.insert("", "end", values=(
                        data, "ENVIO", serv, codigo, desc, qtd,
                        f"R$ {valor_unit:.2f}", f"R$ {valor_total:.2f}", status
                    ), tags=(tag,))

                    total_envios += qtd
                    total_valor += valor_total
                    registros += 1
            except Exception as e:
                print(f"Erro em envios: {e}")

            # 1b. ENVIOS (envios_cortes)
            try:
                filtro_data, params_data = _filtro_data("ec.data_envio")
                # Consultar envios registrados na nova tabela envios_cortes.
                # Aqui buscamos o nome do prestador via join com cadastro_faccoes e
                # agregamos as quantidades e valores por tamanho para calcular o total.
                sql_envios2 = f"""
                    SELECT
                        ec.data_envio,
                        ec.tipo_servico,
                        COALESCE(cc.codigo, ec.codigo_corte) as codigo_corte,
                        COALESCE(cc.descricao, ec.descricao_corte) as descricao_corte,
                        COALESCE(ec.qtd_pp, 0) as qtd_pp,
                        COALESCE(ec.qtd_p, 0) as qtd_p,
                        COALESCE(ec.qtd_m, 0) as qtd_m,
                        COALESCE(ec.qtd_g, 0) as qtd_g,
                        COALESCE(ec.qtd_gg, 0) as qtd_gg,
                        COALESCE(ec.qtd_g1, 0) as qtd_g1,
                        COALESCE(ec.qtd_g2, 0) as qtd_g2,
                        COALESCE(ec.qtd_g3, 0) as qtd_g3,
                        COALESCE(ec.valor_pp, 0) as valor_pp,
                        COALESCE(ec.valor_p, 0) as valor_p,
                        COALESCE(ec.valor_m, 0) as valor_m,
                        COALESCE(ec.valor_g, 0) as valor_g,
                        COALESCE(ec.valor_gg, 0) as valor_gg,
                        COALESCE(ec.valor_g1, 0) as valor_g1,
                        COALESCE(ec.valor_g2, 0) as valor_g2,
                        COALESCE(ec.valor_g3, 0) as valor_g3,
                        COALESCE(ec.status_envio, 'Enviado') as status_envio
                    FROM {schema}.envios_cortes ec
                    LEFT JOIN {schema}.cadastro_de_corte cc ON ec.corte_id = cc.id
                    JOIN {schema}.cadastro_faccoes cf ON ec.prestador_id = cf.id
                    WHERE 1=1
                      {filtro_data}
                      AND cf.nome = %s
                      AND (%s = 'Todos' OR ec.tipo_servico = %s)
                    ORDER BY ec.data_envio
                """
                cur.execute(sql_envios2, (*params_data, prestador, servico, servico))
                for row in cur.fetchall():
                    (
                        data, serv, codigo, desc,
                        qpp, qp, qm, qg, qgg, qg1, qg2, qg3,
                        vpp, vp, vm, vg, vgg, vg1, vg2, vg3,
                        status_envio
                    ) = row
                    # Somar quantidades de todas as colunas de tamanho
                    qtd = (
                        (qpp or 0) + (qp or 0) + (qm or 0) + (qg or 0) +
                        (qgg or 0) + (qg1 or 0) + (qg2 or 0) + (qg3 or 0)
                    )
                    # Calcular valor total do envio multiplicando quantidades pelos respectivos valores
                    valor_total_envio = (
                        (qpp or 0) * (vpp or 0) +
                        (qp or 0) * (vp or 0) +
                        (qm or 0) * (vm or 0) +
                        (qg or 0) * (vg or 0) +
                        (qgg or 0) * (vgg or 0) +
                        (qg1 or 0) * (vg1 or 0) +
                        (qg2 or 0) * (vg2 or 0) +
                        (qg3 or 0) * (vg3 or 0)
                    )
                    # Valor unitário médio ponderado (evita divisão por zero)
                    valor_unit_medio = (valor_total_envio / qtd) if qtd > 0 else 0
                    tag = 'evenrow' if registros % 2 == 0 else 'oddrow'
                    self.tree.insert("", "end", values=(
                        data, "ENVIO", serv, codigo or "-", desc or "-", qtd,
                        f"R$ {valor_unit_medio:.2f}", f"R$ {valor_total_envio:.2f}", status_envio or ""
                    ), tags=(tag,))
                    total_envios += qtd
                    total_valor += valor_total_envio
                    registros += 1
            except Exception as e:
                print(f"Erro em envios (envios_cortes): {e}")

            # 2. RETORNOS/ENTRADAS
            try:
                filtro_data, params_data = _filtro_data("e.data_chegada")
                sql_retornos = f"""
                    SELECT e.data_chegada, c.servico, c.codigo_corte, c.descricao_corte,
                           COALESCE((SELECT SUM(COALESCE(quantidade_entregue,0))
                               FROM {schema}.retorno_detalhes_tamanho r
                               WHERE r.retorno_id = e.id), 0) as qtd,
                           COALESCE(c.valor_peca, 0) as valor_unit,
                           c.status
                    FROM {schema}.entrada_acabamento e
                    JOIN {schema}.controle_envio_cortes c ON e.envio_id = c.id
                    WHERE 1=1
                      {filtro_data}
                      AND (c.costureira = %s OR c.destino = %s OR c.faccao = %s)
                      AND (%s = 'Todos' OR c.servico = %s)
                    ORDER BY e.data_chegada
                """
                cur.execute(sql_retornos, (*params_data, prestador, prestador, prestador, servico, servico))

                for row in cur.fetchall():
                    data, serv, codigo, desc, qtd, valor_unit, status = row
                    valor_total = qtd * valor_unit

                    tag = 'evenrow' if registros % 2 == 0 else 'oddrow'
                    self.tree.insert("", "end", values=(
                        data, "RETORNO", serv, codigo, desc, qtd,
                        f"R$ {valor_unit:.2f}", f"R$ {valor_total:.2f}", status
                    ), tags=(tag,))

                    total_retornos += qtd
                    total_valor += valor_total
                    registros += 1
            except Exception as e:
                print(f"Erro em retornos: {e}")

            # 3. PAGAMENTOS
            try:
                filtro_data, params_data = _filtro_data("data_pagamento")
                sql_pagamentos = f"""
                    SELECT data_pagamento, tipo_servico, codigo, descricao,
                           COALESCE(quantidade_finalizada, 0) as qtd,
                           COALESCE(valor_por_peca, 0) as valor_unit,
                           COALESCE(total_pago, 0) as valor_total,
                           CASE WHEN estornado THEN 'Estornado' ELSE 'Pago' END as status
                    FROM {schema}.pagamento_corte_acabamento
                    WHERE 1=1
                      {filtro_data}
                      AND costureira = %s
                      AND (%s = 'Todos' OR tipo_servico = %s)
                      AND estornado = FALSE
                    ORDER BY data_pagamento
                """
                cur.execute(sql_pagamentos, (*params_data, prestador, servico, servico))

                for row in cur.fetchall():
                    data, serv, codigo, desc, qtd, valor_unit, valor_total, status = row

                    tag = 'evenrow' if registros % 2 == 0 else 'oddrow'
                    self.tree.insert("", "end", values=(
                        data, "PAGAMENTO", serv, codigo, desc, qtd,
                        f"R$ {valor_unit:.2f}", f"R$ {valor_total:.2f}", status
                    ), tags=(tag,))

                    total_pagos += 1
                    total_valor += valor_total
                    registros += 1
            except Exception as e:
                print(f"Erro em pagamentos: {e}")

            # 4. HISTÓRICO DE SERVIÇOS
            try:
                filtro_data, params_data = _filtro_data("data")
                sql_historico = f"""
                    SELECT data, evento, descricao, setor, quantidade, valor, status
                    FROM {schema}.historico_de_servico
                    WHERE 1=1
                      {filtro_data}
                      AND setor = %s
                      AND (%s = 'Todos' OR evento = %s)
                    ORDER BY data
                """
                cur.execute(sql_historico, (*params_data, prestador, servico, servico))

                for row in cur.fetchall():
                    data, evento, desc, setor, qtd, valor, status = row

                    tag = 'evenrow' if registros % 2 == 0 else 'oddrow'
                    self.tree.insert("", "end", values=(
                        data, "HISTÓRICO", evento, "-", desc, qtd or 0,
                        f"R$ {valor or 0:.2f}", f"R$ {valor or 0:.2f}", status or ""
                    ), tags=(tag,))

                    if valor:
                        total_valor += valor
                    registros += 1
            except Exception as e:
                print(f"Erro em histórico: {e}")

            # 4b. PEÇAS COM DEFEITO (por tamanho + histórico)
            try:
                filtro_data, params_data = _filtro_data("e.data_envio")
                sql_defeitos = f"""
                    SELECT
                        e.data_envio,
                        e.id,
                        COALESCE(e.codigo_corte, ''),
                        COALESCE(e.descricao_corte, ''),
                        COALESCE(r.tamanho, ''),
                        COALESCE(r.defeitos, 0)
                    FROM {schema}.retorno_detalhes_tamanho r
                    JOIN {schema}.envios_cortes e ON e.id = r.envio_id
                    LEFT JOIN {schema}.cadastro_faccoes cf ON cf.id = e.prestador_id
                    WHERE 1=1
                      {filtro_data}
                      AND COALESCE(cf.nome, '') = %s
                      AND COALESCE(r.defeitos, 0) > 0
                      AND (%s = 'Todos' OR e.tipo_servico = %s)
                    ORDER BY e.data_envio DESC, e.id DESC, r.tamanho
                """
                cur.execute(sql_defeitos, (*params_data, prestador, servico, servico))

                for row in cur.fetchall():
                    data_envio, envio_id, codigo, desc, tamanho, defeitos = row
                    if hasattr(data_envio, "strftime"):
                        data_envio = data_envio.strftime("%d/%m/%Y")
                    tag = 'evenrow' if registros % 2 == 0 else 'oddrow'
                    if hasattr(self, "defeito_tree") and self.defeito_tree:
                        self.defeito_tree.insert("", "end", values=(
                            data_envio or "", envio_id or "", codigo or "", desc or "", tamanho or "", defeitos or 0
                        ), tags=(tag,))
                    registros += 1

                cur.execute(
                    """
                    SELECT column_name
                      FROM information_schema.columns
                     WHERE table_schema = %s
                       AND table_name = 'historico_de_servico'
                    """,
                    (schema,),
                )
                cols_hist = {row[0] for row in cur.fetchall()}
                if {"evento", "descricao", "quantidade", "status", "setor"}.issubset(cols_hist):
                    data_col = "data" if "data" in cols_hist else (
                        "data_atualizacao" if "data_atualizacao" in cols_hist else (
                            "data_envio" if "data_envio" in cols_hist else "data_chegada"
                        )
                    )
                    filtro_data_hist, params_data_hist = _filtro_data(data_col)
                    sql_defeitos_hist = f"""
                        SELECT {data_col}, evento, descricao, quantidade, status
                        FROM {schema}.historico_de_servico
                        WHERE 1=1
                          {filtro_data_hist}
                          AND setor = %s
                          AND (%s = 'Todos' OR evento = %s)
                          AND status = 'Pendente'
                        ORDER BY {data_col} DESC
                    """
                    cur.execute(sql_defeitos_hist, (*params_data_hist, prestador, servico, servico))
                    for row in cur.fetchall():
                        data_hist, evento, desc, qtd, status = row
                        if hasattr(data_hist, "strftime"):
                            data_hist = data_hist.strftime("%d/%m/%Y")
                        tag = 'evenrow' if registros % 2 == 0 else 'oddrow'
                        if hasattr(self, "defeito_tree") and self.defeito_tree:
                            self.defeito_tree.insert("", "end", values=(
                                data_hist or "",
                                "-",
                                "-",
                                desc or "",
                                evento or "",
                                qtd or 0
                            ), tags=(tag,))
                        registros += 1
                elif {"prestador", "quantidade_defeitos"}.issubset(cols_hist):
                    data_col = "data_envio" if "data_envio" in cols_hist else (
                        "data_chegada" if "data_chegada" in cols_hist else "data_atualizacao"
                    )
                    filtro_data_hist, params_data_hist = _filtro_data(f"h.{data_col}")
                    join_corte = ""
                    codigo_expr = "''"
                    desc_expr = "''"
                    if "corte_id" in cols_hist:
                        join_corte = f"LEFT JOIN {schema}.cadastro_de_corte c ON c.id = h.corte_id"
                        codigo_expr = "COALESCE(c.codigo, '')"
                        desc_expr = "COALESCE(c.descricao, '')"
                    envio_expr = "h.envio_id" if "envio_id" in cols_hist else "NULL"
                    servico_cond = "AND (%s = 'Todos' OR h.tipo_servico = %s)" if "tipo_servico" in cols_hist else ""
                    params = list(params_data_hist) + [prestador]
                    if "tipo_servico" in cols_hist:
                        params.extend([servico, servico])
                    sql_defeitos_hist = f"""
                        SELECT h.{data_col} AS data_hist,
                               {envio_expr} AS envio_id,
                               {codigo_expr} AS codigo,
                               {desc_expr} AS descricao,
                               'TOTAL' AS tamanho,
                               COALESCE(h.quantidade_defeitos, 0) AS defeitos
                          FROM {schema}.historico_de_servico h
                          {join_corte}
                         WHERE 1=1
                           {filtro_data_hist}
                           AND COALESCE(h.prestador, '') = %s
                           AND COALESCE(h.quantidade_defeitos, 0) > 0
                           {servico_cond}
                         ORDER BY h.{data_col} DESC
                    """
                    cur.execute(sql_defeitos_hist, tuple(params))
                    for row in cur.fetchall():
                        data_hist, envio_id, codigo, desc, tamanho, defeitos = row
                        if hasattr(data_hist, "strftime"):
                            data_hist = data_hist.strftime("%d/%m/%Y")
                        tag = 'evenrow' if registros % 2 == 0 else 'oddrow'
                        if hasattr(self, "defeito_tree") and self.defeito_tree:
                            self.defeito_tree.insert("", "end", values=(
                                data_hist or "",
                                envio_id or "",
                                codigo or "",
                                desc or "",
                                tamanho or "",
                                defeitos or 0
                            ), tags=(tag,))
                        registros += 1
            except Exception as e:
                print(f"Erro em defeitos pendentes: {e}")

            # Calcular tempo médio (simplificado)
            tempo_medio = total_retornos / max(total_envios, 1) if total_envios > 0 else 0

            # Atualizar KPIs
            self.kpi_envios.configure(text=str(total_envios))
            self.kpi_retornos.configure(text=str(total_retornos))
            self.kpi_pagos.configure(text=str(total_pagos))
            self.kpi_valor.configure(
                text=f"R$ {total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            self.kpi_media.configure(text=f"{tempo_medio:.1f} dias")

            # Cache para exportação
            periodo_ini = ini
            periodo_fim = fim
            if todos_registros:
                periodo_ini = "Todos"
                periodo_fim = ""

            self._last_search = {
                "ini": periodo_ini, "fim": periodo_fim, "prestador": prestador, "servico": servico,
                "total_envios": total_envios, "total_retornos": total_retornos,
                "total_pagos": total_pagos, "total_valor": total_valor
            }

            cur.close()

            if registros == 0:
                messagebox.showinfo("Info", "Nenhum registro encontrado para os filtros informados")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na busca: {e}")

    def _export_csv(self):
        """Exporta para CSV"""
        if not hasattr(self, "_last_search"):
            messagebox.showinfo("Exportar", "Realize uma busca primeiro")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"historico_{self._last_search['prestador']}_{self._last_search['ini']}_{self._last_search['fim']}.csv"
        )

        if not filename:
            return

        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(
                    ["Data", "Tipo", "Serviço", "Código", "Descrição", "Quantidade", "V. Unitário", "V. Total",
                     "Status"])

                for item in self.tree.get_children():
                    values = self.tree.item(item)["values"]
                    writer.writerow(values)

            messagebox.showinfo("Sucesso", f"Arquivo exportado:\n{filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar: {e}")

    def _generate_report(self):
        """Gera relatório HTML"""
        if not hasattr(self, "_last_search"):
            messagebox.showinfo("Relatório", "Realize uma busca primeiro")
            return

        try:
            report_dir = os.path.join(os.path.dirname(__file__), "RELATORIOS_HISTORICO")
            os.makedirs(report_dir, exist_ok=True)

            filename = os.path.join(report_dir,
                                    f"historico_{self._last_search['prestador']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")

            rows_html = ""
            for item in self.tree.get_children():
                values = self.tree.item(item)["values"]
                row = "".join(f"<td>{v}</td>" for v in values)
                rows_html += f"<tr>{row}</tr>"

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Histórico de Serviços</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    .header {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .kpis {{ display: flex; gap: 20px; margin-bottom: 20px; }}
                    .kpi-card {{ background: #e3f2fd; padding: 15px; border-radius: 5px; flex: 1; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #4f46e5; color: white; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <h1>Histórico de Serviços</h1>
                <div class="header">
                    <strong>Prestador:</strong> {self._last_search['prestador']}<br>
                    <strong>Período:</strong> {self._last_search['ini']} a {self._last_search['fim']}<br>
                    <strong>Serviço:</strong> {self._last_search['servico']}
                </div>

                <div class="kpis">
                    <div class="kpi-card">
                        <strong>Envios:</strong> {self._last_search['total_envios']}
                    </div>
                    <div class="kpi-card">
                        <strong>Retornos:</strong> {self._last_search['total_retornos']}
                    </div>
                    <div class="kpi-card">
                        <strong>Pagamentos:</strong> {self._last_search['total_pagos']}
                    </div>
                    <div class="kpi-card">
                        <strong>Valor Total:</strong> R$ {self._last_search['total_valor']:,.2f}
                    </div>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>Data</th><th>Tipo</th><th>Serviço</th><th>Código</th>
                            <th>Descrição</th><th>Quantidade</th><th>V. Unitário</th>
                            <th>V. Total</th><th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </body>
            </html>
            """

            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)

            webbrowser.open(filename)
            messagebox.showinfo("Sucesso", f"Relatório gerado:\n{filename}")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar relatório: {e}")


# ---------- Standalone para testes ----------
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    app = ctk.CTk()
    app.title("Histórico de Serviços - Sistema Opera")
    app.geometry("1400x900")

    # Simular sistema principal com cores
    app.cor_fundo = "#020617"
    app.cor_primaria = "#1f2937"
    app.cor_secundaria = "#111827"
    app.cor_terciaria = "#1e293b"
    app.cor_texto = "#e5e7eb"
    app.cor_selecao = "#2563eb"
    app.cor_hover = "#334155"
    app.cor_imprimir = "#2563eb"
    app.cor_borda = "#273244"
    app.modo = "dark"

    page = HistoricoServicosPage(app, sistema=app)
    page.pack(fill="both", expand=True, padx=10, pady=10)

    app.mainloop()
