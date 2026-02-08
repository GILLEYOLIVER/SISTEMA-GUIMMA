# -*- coding: utf-8 -*-
"""
Dashboard (PostgreSQL) - VERSÃO COMPLETA CORRIGIDA
- Gráficos de Status de Produção (barras + linhas) ao selecionar período
- Gráfico de Tempo do Modelo (pizza) ao dar duplo clique em um corte
- Cards com Cortes + Peças
- Últimos Finalizados com código, descrição e quantidade
"""

import os
from datetime import datetime, timedelta, date
import customtkinter as ctk
from PAGINAS_DO_SISTEMA.TEMAS import (
    get_contraste_texto,
    is_dark_color,
    ajustar_hover,
    aplicar_estilo_treeview,
    aplicar_tags_alternadas,
)
from tkinter import ttk, messagebox

# ==== IMPORT POSTGRESQL COM FALLBACK ====
POSTGRES_DISPONIVEL = False

try:
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import (
        get_schema, ready_check,
        fetch_all, fetch_one, execute, get_conn
    )

    try:
        if ready_check():
            POSTGRES_DISPONIVEL = True
            print("PostgreSQL conectado!")

            try:
                schema = get_schema() or "opera"
                execute(f"SET search_path TO {schema}, public")
            except Exception as se:
                print(f"Erro search_path: {se}")

            globals()['_fetch_all'] = fetch_all
            globals()['_fetch_one'] = fetch_one
            globals()['_exec_write'] = execute
        else:
            POSTGRES_DISPONIVEL = False
    except Exception as e:
        print(f"Erro PostgreSQL: {e}")
        POSTGRES_DISPONIVEL = False

except Exception as e:
    print(f"Módulo PostgreSQL não disponível: {e}")
    POSTGRES_DISPONIVEL = False

# ==== FALLBACK ====
if not POSTGRES_DISPONIVEL:
    print("Banco de dados indisponível. Funções de fallback ativas.")


    def _fetch_all(sql, params=None):
        return []


    def _fetch_one(sql, params=None):
        return None


    def _exec_write(sql, params=None):
        return 0


    def get_schema():
        return "opera"


# ==== HELPERS POSTGRESQL ====
def _table_exists_pg(table_name: str) -> bool:
    tn = (table_name or "").strip().lower()
    if not tn:
        return False

    try:
        row = _fetch_one("""
            SELECT EXISTS (
              SELECT 1 FROM pg_catalog.pg_tables
               WHERE LOWER(tablename) = LOWER(%s)
                 AND schemaname = ANY (current_schemas(true))
            ) AS ok
        """, (tn,))
        ok = (row.get("ok") if isinstance(row, dict) else row[0]) if row else False
        if bool(ok):
            return True
    except:
        pass

    for sc in ((get_schema() or "opera"), "opera", "public"):
        try:
            row = _fetch_one("""
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.tables
                   WHERE LOWER(table_schema) = LOWER(%s)
                     AND LOWER(table_name) = LOWER(%s)
                ) AS ok
            """, (sc, tn))
            ok = (row.get("ok") if isinstance(row, dict) else row[0]) if row else False
            if bool(ok):
                return True
        except:
            continue
    return False


def _columns_pg(table: str):
    tn = table.lower()
    try:
        rows = _fetch_all("""
            SELECT c.column_name FROM information_schema.columns c
             WHERE c.table_name = %s AND c.table_schema = ANY (current_schemas(true))
             ORDER BY c.ordinal_position
        """, (tn,))
        if rows:
            return [list(r.values())[0] for r in rows]
    except:
        pass

    for sc in [get_schema(), "opera", "public"]:
        try:
            rows = _fetch_all("""
                SELECT column_name FROM information_schema.columns
                 WHERE table_schema = %s AND table_name = %s
                 ORDER BY ordinal_position
            """, (sc, tn))
            if rows:
                return [list(r.values())[0] for r in rows]
        except:
            continue
    return []


def _pick(colnames, *candidates, default=None):
    lc = [c.lower() for c in colnames]
    for cand in candidates:
        if cand.lower() in lc:
            return colnames[lc.index(cand.lower())]
    return default


def _to_date_any(v):
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).date()
        except:
            pass
    return None


def _to_datetime_any(v):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, datetime.min.time())

    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:19], fmt)
        except:
            pass
    return None


# ===================== DASHBOARD UI =====================
class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, sistema):
        super().__init__(master, fg_color=sistema.cor_fundo)
        self.sistema = sistema
        self.POSTGRES_DISPONIVEL = POSTGRES_DISPONIVEL

        # Paleta
        self.cor_primaria = sistema.cor_primaria
        self.cor_secundaria = sistema.cor_secundaria
        self.cor_terciaria = sistema.cor_terciaria
        self.cor_fundo = sistema.cor_fundo
        self.cor_texto = sistema.cor_texto
        self.cor_destaque = sistema.cor_destaque
        self.cor_sucesso = sistema.cor_sucesso
        self.cor_alerta = sistema.cor_alerta
        self.cor_borda = sistema.cor_borda
        self.cor_hover = sistema.cor_hover

        # Cores fixas
        self.cor_cabecalho_fundo = "#2C3E50"
        self.cor_cabecalho_texto = "#FFFFFF"
        self.cor_linhas_fundo = "#FFFFFF"
        self.cor_linhas_texto = "#000000"
        self.cor_combobox_fundo = "#FFFFFF"
        self.cor_combobox_texto = "#000000"
        self.cor_combobox_botao = "#2C3E50"
        self.cor_combobox_botao_hover = "#1a2b45"

        self.dados_producao = getattr(sistema, "dados_producao",
                                      {"em_andamento": [], "finalizados": [],
                                       "metas": {"semanal": 0, "atingido_semanal": 0, "mensal": 0,
                                                 "atingido_mensal": 0}})
        self.departamentos = getattr(sistema, "departamentos",
                                     ["Corte", "Facção", "Bordado", "Caseador", "Botões", "Estamparia", "Tingimento",
                                      "Acabamento"])
        self.selected_depart = ctk.StringVar(value="Todos")
        self.painel_prod_periodo_var = ctk.StringVar(value="7 dias")
        self.painel_prod_grafico_var = ctk.StringVar(value="Barras")
        self.painel_prod_setor_var = ctk.StringVar(value="Todos")

        # Estado gráfico
        self.fig_grafico = None
        self.ax_grafico = None
        self.canvas_grafico = None
        self.filtro_tempo_var = ctk.StringVar(value="7 dias")
        self.tipo_grafico = "dashboard"
        self.modelo_selecionado = None

        # Frame cards
        self.frame_cards = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        self.frame_cards.pack(fill="x", pady=(0, 2))

        self._criar_cards_resumo(self.frame_cards)
        self._construir()

        self.atualizar_dashboard()
        self.bind("<Map>", lambda e: self._refresh_debounced())
        self.bind("<Visibility>", lambda e: self._refresh_debounced())
        self.on_show = self.atualizar_dashboard

        self._setup_auto_refresh()
        self.bind("<FocusIn>", lambda e: self._refresh_debounced())
        self.iniciar_atualizacao_automatica(30)

    def _construir(self):
        self.tipos_estoque = ["Tecidos", "Aviamentos", "Insumos", "Escritorio", "Limpeza", "Outros"]
        self.cols_estoque = ("ID", "Número Item", "Descrição", "Código", "Data Entrada", "Quantidade")

        self.frame_cards.pack(fill="x", pady=(0, 2))

        duplo_section = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        duplo_section.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        duplo_section.grid_columnconfigure(0, weight=2)
        duplo_section.grid_columnconfigure(1, weight=3)
        duplo_section.grid_rowconfigure(0, weight=1)

        # ESTOQUE
        frame_est = ctk.CTkFrame(duplo_section, fg_color="#F8F9FA", corner_radius=10)
        frame_est.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        frame_est.grid_rowconfigure(2, weight=1)
        frame_est.grid_rowconfigure(3, weight=0)
        frame_est.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame_est, text="ESTOQUE", font=("Arial", 14, "bold"),
                     text_color="#2C3E50").grid(row=0, column=0, pady=(4, 2), sticky="w", padx=10)

        filtro_est = ctk.CTkFrame(frame_est, fg_color="#F8F9FA")
        filtro_est.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 4))
        filtro_est.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(filtro_est, text="Tipo:", font=("Arial", 12),
                     text_color="#2C3E50").grid(row=0, column=0, padx=(0, 6))

        self.combo_tipo_estoque = ctk.CTkComboBox(
            filtro_est, values=self.tipos_estoque,
            command=lambda _: self._atualizar_tabela_estoque(),
            fg_color=self.cor_combobox_fundo, text_color=self.cor_combobox_texto,
            button_color=self.cor_combobox_botao, button_hover_color=self.cor_combobox_botao_hover)
        self.combo_tipo_estoque.grid(row=0, column=1, sticky="ew")
        self.combo_tipo_estoque.set("Tecidos")

        tabela_frame = ctk.CTkFrame(frame_est, fg_color="#F8F9FA")
        tabela_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(4, 2))
        tabela_frame.grid_columnconfigure(0, weight=1)
        tabela_frame.grid_rowconfigure(0, weight=1)

        self.tree_est = ttk.Treeview(tabela_frame, columns=self.cols_estoque, show="headings", height=5)
        for col in self.cols_estoque:
            self.tree_est.heading(col, text=col)
            self.tree_est.column(col, anchor="w", width=100, stretch=True)

        sb_e = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tree_est.yview)
        self.tree_est.configure(yscroll=sb_e.set)
        sb_e.grid(row=0, column=1, sticky="ns")
        self.tree_est.grid(row=0, column=0, sticky="nsew")

        area_extra = ctk.CTkFrame(frame_est, fg_color="#F8F9FA", corner_radius=8, height=190)
        area_extra.grid(row=3, column=0, sticky="nsew", padx=10, pady=(2, 8))
        area_extra.grid_columnconfigure(0, weight=1)
        area_extra.grid_rowconfigure(2, weight=0)
        area_extra.grid_rowconfigure(1, weight=0)
        area_extra.grid_rowconfigure(0, weight=0)
        cabecalho_painel = ctk.CTkFrame(area_extra, fg_color="transparent")
        cabecalho_painel.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        cabecalho_painel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            cabecalho_painel,
            text="Painel de produção (indicadores visuais)",
            font=("Arial", 12, "bold"),
            text_color="#2C3E50",
        ).grid(row=0, column=0, sticky="w")

        filtros_painel = ctk.CTkFrame(cabecalho_painel, fg_color="transparent")
        filtros_painel.grid(row=0, column=1, sticky="e")

        self.combo_painel_setor = ctk.CTkComboBox(
            filtros_painel,
            values=["Todos", "Ordem Corte", "Corte Pronto", "Enviado", "Conferência", "Pendente", "Pago"],
            variable=self.painel_prod_setor_var,
            command=lambda _: self._atualizar_painel_producao(),
            width=140,
            height=24,
        )
        self.combo_painel_setor.pack(side="left", padx=(0, 6))

        self.combo_painel_periodo = ctk.CTkComboBox(
            filtros_painel,
            values=["7 dias", "15 dias", "30 dias"],
            variable=self.painel_prod_periodo_var,
            command=lambda _: self._atualizar_painel_producao(),
            width=90,
            height=24,
        )
        self.combo_painel_periodo.pack(side="left", padx=(0, 6))

        self.combo_painel_grafico = ctk.CTkComboBox(
            filtros_painel,
            values=["Barras", "Linha", "Rosca"],
            variable=self.painel_prod_grafico_var,
            command=lambda _: self._atualizar_painel_producao(),
            width=90,
            height=24,
        )
        self.combo_painel_grafico.pack(side="left")

        indicadores_frame = ctk.CTkFrame(area_extra, fg_color="transparent")
        indicadores_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        for i in range(3):
            indicadores_frame.grid_columnconfigure(i, weight=1)

        def _card(titulo, cor):
            card = ctk.CTkFrame(indicadores_frame, fg_color="#FFFFFF", corner_radius=10)
            ctk.CTkLabel(card, text=titulo, font=("Arial", 11), text_color="#6B7280").pack(anchor="w", padx=10, pady=(6, 0))
            valor_lbl = ctk.CTkLabel(card, text="0", font=("Arial", 15, "bold"), text_color="#2C3E50")
            valor_lbl.pack(anchor="w", padx=10, pady=(2, 2))
            barra = ctk.CTkProgressBar(card, progress_color=cor, height=6)
            barra.set(0.0)
            barra.pack(fill="x", padx=10, pady=(0, 8))
            return card, valor_lbl, barra

        card_and, self.lbl_painel_andamento, self.pb_painel_andamento = _card("Ordens em andamento", "#3B82F6")
        card_and.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        card_atr, self.lbl_painel_atrasos, self.pb_painel_atrasos = _card("Atrasos críticos", "#EF4444")
        card_atr.grid(row=0, column=1, sticky="nsew", padx=6)

        card_efi, self.lbl_painel_eficiencia, self.pb_painel_eficiencia = _card("Eficiência diária", "#10B981")
        card_efi.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        self.painel_prod_chart = ctk.CTkCanvas(area_extra, bg="#FFFFFF", highlightthickness=0, height=80)
        self.painel_prod_chart.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 6))

        self._atualizar_tabela_estoque()

        # GRÁFICO
        frame_gra = ctk.CTkFrame(duplo_section, fg_color=self.cor_secundaria, corner_radius=10)
        frame_gra.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        frame_gra.grid_columnconfigure(0, weight=1)
        frame_gra.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(frame_gra, text="STATUS DE PRODUÇÃO", font=("Arial", 14, "bold"),
                     text_color=self.cor_texto).grid(row=0, column=0, sticky="w", padx=10, pady=(4, 2))

        self.tempo_menu = ctk.CTkOptionMenu(
            frame_gra, values=["7 dias", "15 dias", "30 dias"],
            variable=self.filtro_tempo_var,
            command=lambda _: self._mostrar_grafico_producao(),
            fg_color=self.cor_terciaria, text_color=self.cor_texto,
            button_color=self.cor_primaria, button_hover_color=self.cor_destaque)
        self.tempo_menu.grid(row=1, column=0, sticky="e", padx=10, pady=(0, 4))

        self.grafico_container = ctk.CTkFrame(frame_gra, fg_color=self.cor_secundaria, corner_radius=8)
        self.grafico_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=6)
        self.grafico_container.grid_columnconfigure(0, weight=1)
        self.grafico_container.grid_rowconfigure(0, weight=1)

        self.criar_grafico_inicial()

        # ÚLTIMOS FINALIZADOS
        self._carregar_ultimos_finalizados(limite=3)

        # PRODUÇÃO EM ANDAMENTO
        frame_and = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        frame_and.pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(frame_and, text="PRODUÇÃO EM ANDAMENTO", font=("Arial", 15, "bold"),
                     text_color=self.cor_texto).pack(pady=(2, 2))

        filtro_frame = ctk.CTkFrame(frame_and, fg_color="#F8F9FA", corner_radius=6)
        filtro_frame.pack(fill="x", pady=(2, 1))

        ctk.CTkLabel(filtro_frame, text="Departamento:", font=("Arial", 12),
                     text_color="#2C3E50").pack(side="left", padx=(6, 6))

        valores = ["Todos", "Corte", "CORTES P/ ENVIAR", "Enviado", "Conferência", "Finalizado"] + list(
            self.departamentos)

        self.combo_depart = ctk.CTkComboBox(
            filtro_frame, values=valores, variable=self.selected_depart,
            command=lambda _: self._filtrar_tabela_andamento(), width=160, height=23)
        self.combo_depart.pack(side="left")

        cont = ctk.CTkFrame(frame_and, fg_color="#F8F9FA", corner_radius=6)
        cont.pack(fill="x", padx=10, pady=(0, 4))

        tree_container = ctk.CTkFrame(cont, fg_color="transparent")
        tree_container.pack(fill="x")

        cols = ("Código", "Descrição", "Cortador", "Data Registro",
                "Qtd. Desejada", "Dias Estimados", "Horas Estimadas", "Origem")

        self.tree_and = ttk.Treeview(tree_container, columns=cols, show="headings", height=3)

        for c in cols:
            self.tree_and.heading(c, text=c)
            if c == "Descrição":
                self.tree_and.column(c, anchor="w", width=170, stretch=True)
            elif c in ("Código", "Cortador", "Origem"):
                self.tree_and.column(c, anchor="center", width=80, stretch=False)
            elif c == "Data Registro":
                self.tree_and.column(c, anchor="center", width=110, stretch=False)
            else:
                self.tree_and.column(c, anchor="center", width=90, stretch=False)

        sb1 = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_and.yview)
        self.tree_and.configure(yscroll=sb1.set)
        sb1.pack(side="right", fill="y")

        self.tree_and.pack(fill="x", padx=5, pady=4)

        # Bind duplo clique para mostrar gráfico do modelo
        self.tree_and.bind("<Double-1>", lambda e: self._mostrar_grafico_tempo_modelo())

        self.after(100, self._ajustar_colunas_conteudo)
        self._aplicar_estilo_treeviews()

    # ================== GRÁFICOS ==================

    def criar_grafico_inicial(self):
        """Cria área do gráfico."""
        for w in self.grafico_container.winfo_children():
            w.destroy()

        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            self.fig_grafico = Figure(figsize=(6, 4), dpi=100, facecolor=self.cor_secundaria)
            self.canvas_grafico = FigureCanvasTkAgg(self.fig_grafico, master=self.grafico_container)
            self.canvas_grafico.get_tk_widget().pack(fill='both', expand=True)

            self.lbl_info_grafico = ctk.CTkLabel(
                self.grafico_container, text="Selecione um período ou dê duplo clique em um corte",
                text_color=self.cor_texto, font=ctk.CTkFont(size=11))
            self.lbl_info_grafico.pack(side="bottom", pady=(0, 6))

            self._mostrar_grafico_producao()

        except Exception as e:
            print(f"Erro ao criar gráfico: {e}")
            ctk.CTkLabel(self.grafico_container, text=f"Instale matplotlib\npip install matplotlib",
                         text_color="#FF6B6B").pack(expand=True)

    def _mostrar_grafico_producao(self):
        """Mostra gráficos de barras + linhas de status de produção."""
        self.tipo_grafico = "producao"

        if not hasattr(self, "fig_grafico") or self.fig_grafico is None:
            self.criar_grafico_inicial()
            return

        try:
            from matplotlib.figure import Figure

            self.fig_grafico.clear()

            # 2 subplots
            self.ax_barras = self.fig_grafico.add_subplot(121)
            self.ax_linha = self.fig_grafico.add_subplot(122)

            for ax in [self.ax_barras, self.ax_linha]:
                ax.set_facecolor(self.cor_secundaria)
                ax.tick_params(colors=self.cor_texto, labelsize=8)
                for spine in ax.spines.values():
                    spine.set_color(self.cor_borda)

            # Período
            periodo = self.filtro_tempo_var.get()
            dias = 7 if "7" in periodo else 15 if "15" in periodo else 30

            # Busca dados
            dados = self._buscar_dados_fluxo(dias)

            # GRÁFICO BARRAS
            etapas = dados["etapas"]
            quantidades = dados["quantidades"]
            pecas = dados["pecas"]
            cores = ["#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EF4444", "#22C55E"]

            y_pos = range(len(etapas))
            bars = self.ax_barras.barh(y_pos, quantidades, color=cores, height=0.6)

            self.ax_barras.set_yticks(y_pos)
            self.ax_barras.set_yticklabels(etapas, fontsize=9, color=self.cor_texto)
            self.ax_barras.set_xlabel("Cortes", fontsize=9, color=self.cor_texto)
            self.ax_barras.set_title(f"Fluxo ({dias}d)", fontsize=11, color=self.cor_texto, fontweight='bold')

            for i, (bar, qtd, pcs) in enumerate(zip(bars, quantidades, pecas)):
                label = f"{qtd}" if qtd > 0 else ""
                self.ax_barras.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                                    label, va='center', fontsize=8, color=self.cor_texto)

            max_val = max(quantidades) if quantidades and max(quantidades) > 0 else 10
            self.ax_barras.set_xlim(0, max_val * 1.3)
            self.ax_barras.invert_yaxis()

            # GRÁFICO LINHA
            datas = dados["evolucao"]["datas"]
            finalizados = dados["evolucao"]["finalizados"]
            enviados = dados["evolucao"]["enviados"]

            if datas:
                datas_fmt = [d.strftime("%d/%m") if isinstance(d, (date, datetime)) else str(d)[:5] for d in datas]
                x = range(len(datas_fmt))

                if finalizados:
                    self.ax_linha.plot(x, finalizados, marker='o', linewidth=2, markersize=5,
                                       color="#22C55E", label="Finalizados")
                    self.ax_linha.fill_between(x, finalizados, alpha=0.3, color="#22C55E")

                if enviados and any(v > 0 for v in enviados):
                    self.ax_linha.plot(x, enviados, marker='s', linewidth=2, markersize=4,
                                       color="#F59E0B", label="Enviados")

                self.ax_linha.set_xticks(x)
                self.ax_linha.set_xticklabels(datas_fmt, fontsize=7, color=self.cor_texto, rotation=45)
                self.ax_linha.legend(fontsize=7, loc='upper left', facecolor=self.cor_secundaria,
                                     labelcolor=self.cor_texto, framealpha=0.8)
            else:
                self.ax_linha.text(0.5, 0.5, "Sem dados", ha='center', va='center',
                                   fontsize=10, color=self.cor_texto, transform=self.ax_linha.transAxes)

            self.ax_linha.set_title(f"Evolução ({dias}d)", fontsize=11, color=self.cor_texto, fontweight='bold')
            self.ax_linha.grid(True, alpha=0.3, color=self.cor_borda)

            self.fig_grafico.tight_layout(pad=1.5)
            self.canvas_grafico.draw()

            total_cortes = sum(quantidades)
            total_pecas = sum(pecas)
            if hasattr(self, "lbl_info_grafico"):
                self.lbl_info_grafico.configure(
                    text=f"Total: {total_cortes} cortes | {total_pecas} peças ({dias} dias)")

        except Exception as e:
            print(f"Erro gráfico produção: {e}")

    def _mostrar_grafico_tempo_modelo(self):
        """Mostra gráfico de pizza com progresso do modelo selecionado."""
        try:
            selecionados = list(self.tree_and.selection()) if hasattr(self, "tree_and") else []

            if not selecionados:
                self._mostrar_grafico_producao()
                return

            self.tipo_grafico = "tempo_modelo"

            valores = self.tree_and.item(selecionados[0], "values")
            codigo = valores[0] if len(valores) > 0 else "-"
            descricao = valores[1] if len(valores) > 1 else "-"
            data_txt = valores[3] if len(valores) > 3 else ""
            dias_txt = valores[5] if len(valores) > 5 else 0
            horas_txt = valores[6] if len(valores) > 6 else 0
            origem_txt = valores[7] if len(valores) > 7 else ""

            def _to_float(v):
                try:
                    return float(str(v).replace(",", "."))
                except:
                    return 0.0

            dias_estimados = _to_float(dias_txt)
            horas_estimadas = _to_float(horas_txt)

            if horas_estimadas > 0 and dias_estimados < 1:
                total_horas = max(horas_estimadas, 0.0)
            else:
                total_horas = max((dias_estimados * 24.0) + horas_estimadas, 0.0)

            inicio = _to_datetime_any(data_txt) or datetime.now()
            agora = datetime.now()
            decorrido_horas = max((agora - inicio).total_seconds() / 3600.0, 0.0)

            self.fig_grafico.clear()
            ax = self.fig_grafico.add_subplot(111)
            ax.set_facecolor(self.cor_secundaria)

            origem_norm = str(origem_txt).strip().lower()

            if origem_norm in ("corte pronto", "cortes p/ enviar"):
                wedges, texts, autotexts = ax.pie(
                    [1], labels=["Concluído"], autopct=lambda _: "100%",
                    startangle=90, colors=[self.cor_sucesso],
                    wedgeprops={'width': 0.4}, pctdistance=1.30, labeldistance=1.1)
                for t in texts + autotexts:
                    t.set_color(self.cor_texto)
                    t.set_fontsize(10)
                msg = f"{codigo} - {descricao[:30]} | Pronto para envio"

            elif total_horas <= 0:
                ax.pie([1], labels=["Sem estimativa"], startangle=90,
                       colors=[self.cor_borda], wedgeprops={'width': 0.4}, labeldistance=1.1)
                msg = "Informe dias/horas estimados"

            else:
                restante_horas = max(total_horas - decorrido_horas, 0.0)
                valores_pizza = [max(decorrido_horas, 0.01)]
                labels = ["Concluído"]
                cores = [self.cor_destaque]

                if restante_horas > 0:
                    valores_pizza.append(max(restante_horas, 0.01))
                    labels.append("Restante")
                    cores.append(self.cor_borda)

                soma = sum(valores_pizza)

                def _autopct(percent):
                    try:
                        valor = (percent / 100.0) * soma
                        return f"{(valor / total_horas) * 100:.1f}%"
                    except:
                        return f"{percent:.1f}%"

                wedges, texts, autotexts = ax.pie(
                    valores_pizza, labels=labels, autopct=_autopct,
                    startangle=90, colors=cores,
                    wedgeprops={'width': 0.4}, pctdistance=1.35, labeldistance=1.08)

                for t in texts + autotexts:
                    t.set_color(self.cor_texto)
                    t.set_fontsize(10)

                perc_concluido = (decorrido_horas / total_horas) * 100
                perc_restante = (restante_horas / total_horas) * 100

                dec_str = f"{decorrido_horas:.1f}h" if decorrido_horas >= 1 else f"{int(decorrido_horas * 60)}min"
                rest_str = f"{restante_horas:.1f}h" if restante_horas >= 1 else f"{int(restante_horas * 60)}min"

                desc_curta = descricao[:25] + "..." if len(descricao) > 25 else descricao
                msg = f"{codigo} - {desc_curta}\nConcluído: {dec_str} ({perc_concluido:.0f}%) | Restante: {rest_str} ({perc_restante:.0f}%)"

            ax.axis('equal')
            ax.set_title(f"Progresso: {codigo}", fontsize=12, color=self.cor_texto, fontweight='bold')

            self.fig_grafico.tight_layout(pad=1.5)
            self.canvas_grafico.draw()

            if hasattr(self, "lbl_info_grafico"):
                self.lbl_info_grafico.configure(text=msg)

        except Exception as e:
            print(f"Erro gráfico modelo: {e}")

    def _buscar_dados_fluxo(self, dias: int = 7):
        """Busca dados do fluxo de produção."""
        dados = {
            "etapas": ["Ordem Corte", "Corte Pronto", "Enviado", "Conferência", "Pendente", "Pago"],
            "quantidades": [0, 0, 0, 0, 0, 0],
            "pecas": [0, 0, 0, 0, 0, 0],
            "evolucao": {"datas": [], "finalizados": [], "enviados": []}
        }

        if not self.POSTGRES_DISPONIVEL:
            return dados

        schema = get_schema()

        try:
            row = _fetch_one(
                f"SELECT COUNT(*), COALESCE(SUM(quantidade_desejada),0) FROM {schema}.ordem_corte_ficha WHERE data_registro >= CURRENT_DATE - INTERVAL '{dias} days'")
            if row:
                dados["quantidades"][0] = int(row[0] or 0) if not isinstance(row, dict) else int(
                    list(row.values())[0] or 0)
                dados["pecas"][0] = int(row[1] or 0) if not isinstance(row, dict) else int(list(row.values())[1] or 0)
        except:
            pass

        try:
            row = _fetch_one(
                f"SELECT COUNT(*), COALESCE(SUM(total_pecas),0) FROM {schema}.cadastro_de_corte WHERE data >= CURRENT_DATE - INTERVAL '{dias} days'")
            if row:
                dados["quantidades"][1] = int(row[0] or 0) if not isinstance(row, dict) else int(
                    list(row.values())[0] or 0)
                dados["pecas"][1] = int(row[1] or 0) if not isinstance(row, dict) else int(list(row.values())[1] or 0)
        except:
            pass

        try:
            row = _fetch_one(f"""
                SELECT COUNT(*), COALESCE(SUM(e.total_pecas),0) FROM {schema}.envios_cortes e
                LEFT JOIN {schema}.controle_retorno_cortes r ON r.envio_id = e.id
                WHERE r.id IS NULL AND e.data_envio >= CURRENT_DATE - INTERVAL '{dias} days'
            """)
            if row:
                dados["quantidades"][2] = int(row[0] or 0) if not isinstance(row, dict) else int(
                    list(row.values())[0] or 0)
                dados["pecas"][2] = int(row[1] or 0) if not isinstance(row, dict) else int(list(row.values())[1] or 0)
        except:
            pass

        try:
            row = _fetch_one(f"""
                SELECT COUNT(*), COALESCE(SUM(r.total_entregue),0) FROM {schema}.controle_retorno_cortes r
                LEFT JOIN {schema}.cortes_finalizados cf ON cf.retorno_id = r.id
                WHERE cf.id IS NULL AND r.data_chegada >= CURRENT_DATE - INTERVAL '{dias} days'
            """)
            if row:
                dados["quantidades"][3] = int(row[0] or 0) if not isinstance(row, dict) else int(
                    list(row.values())[0] or 0)
                dados["pecas"][3] = int(row[1] or 0) if not isinstance(row, dict) else int(list(row.values())[1] or 0)
        except:
            pass

        try:
            row = _fetch_one(f"""
                SELECT COUNT(*), COALESCE(SUM(COALESCE(qtd_pp,0)+COALESCE(qtd_p,0)+COALESCE(qtd_m,0)+COALESCE(qtd_g,0)+COALESCE(qtd_gg,0)+COALESCE(qtd_g1,0)+COALESCE(qtd_g2,0)+COALESCE(qtd_g3,0)),0)
                FROM {schema}.cortes_finalizados WHERE (pago=FALSE OR pago IS NULL) AND data_chegada >= CURRENT_DATE - INTERVAL '{dias} days'
            """)
            if row:
                dados["quantidades"][4] = int(row[0] or 0) if not isinstance(row, dict) else int(
                    list(row.values())[0] or 0)
                dados["pecas"][4] = int(row[1] or 0) if not isinstance(row, dict) else int(list(row.values())[1] or 0)
        except:
            pass

        try:
            row = _fetch_one(f"""
                SELECT COUNT(*), COALESCE(SUM(COALESCE(qtd_pp,0)+COALESCE(qtd_p,0)+COALESCE(qtd_m,0)+COALESCE(qtd_g,0)+COALESCE(qtd_gg,0)+COALESCE(qtd_g1,0)+COALESCE(qtd_g2,0)+COALESCE(qtd_g3,0)),0)
                FROM {schema}.cortes_finalizados WHERE pago=TRUE AND data_chegada >= CURRENT_DATE - INTERVAL '{dias} days'
            """)
            if row:
                dados["quantidades"][5] = int(row[0] or 0) if not isinstance(row, dict) else int(
                    list(row.values())[0] or 0)
                dados["pecas"][5] = int(row[1] or 0) if not isinstance(row, dict) else int(list(row.values())[1] or 0)
        except:
            pass

        # Evolução diária
        try:
            rows = _fetch_all(
                f"SELECT data_chegada::date as dia, COUNT(*) as qtd FROM {schema}.cortes_finalizados WHERE data_chegada >= CURRENT_DATE - INTERVAL '{dias} days' GROUP BY dia ORDER BY dia")
            for row in (rows or []):
                if isinstance(row, dict):
                    dados["evolucao"]["datas"].append(row.get("dia"))
                    dados["evolucao"]["finalizados"].append(int(row.get("qtd", 0) or 0))
                else:
                    dados["evolucao"]["datas"].append(row[0])
                    dados["evolucao"]["finalizados"].append(int(row[1] or 0))
        except:
            pass

        try:
            rows = _fetch_all(
                f"SELECT data_envio::date as dia, COUNT(*) as qtd FROM {schema}.envios_cortes WHERE data_envio >= CURRENT_DATE - INTERVAL '{dias} days' GROUP BY dia ORDER BY dia")
            enviados_map = {}
            for row in (rows or []):
                if isinstance(row, dict):
                    enviados_map[row.get("dia")] = int(row.get("qtd", 0) or 0)
                else:
                    enviados_map[row[0]] = int(row[1] or 0)

            for d in dados["evolucao"]["datas"]:
                dados["evolucao"]["enviados"].append(enviados_map.get(d, 0))
        except:
            pass

        while len(dados["evolucao"]["enviados"]) < len(dados["evolucao"]["datas"]):
            dados["evolucao"]["enviados"].append(0)

        return dados

    # ================== DADOS ==================

    def _contar_em_andamento_db(self) -> int:
        try:
            if not self.POSTGRES_DISPONIVEL:
                return 0

            schema = get_schema()
            total = 0

            try:
                row = _fetch_one(f"SELECT COUNT(*) FROM {schema}.ordem_corte_ficha")
                total += int(row[0] or 0) if row and not isinstance(row, dict) else int(
                    list(row.values())[0] or 0) if row else 0
            except:
                pass

            try:
                row = _fetch_one(f"SELECT COUNT(*) FROM {schema}.cadastro_de_corte")
                total += int(row[0] or 0) if row and not isinstance(row, dict) else int(
                    list(row.values())[0] or 0) if row else 0
            except:
                pass

            try:
                row = _fetch_one(
                    f"SELECT COUNT(*) FROM {schema}.envios_cortes e LEFT JOIN {schema}.controle_retorno_cortes r ON r.envio_id=e.id WHERE r.id IS NULL")
                total += int(row[0] or 0) if row and not isinstance(row, dict) else int(
                    list(row.values())[0] or 0) if row else 0
            except:
                pass

            return total
        except:
            return 0

    def _sum_producao_periodo(self, periodo: str = "semana"):
        try:
            if not self.POSTGRES_DISPONIVEL:
                return {"cortes": 0, "pecas": 0}

            schema = get_schema()
            intervalo = "7 days" if periodo == "semana" else "30 days"

            row = _fetch_one(f"""
                SELECT COUNT(*), COALESCE(SUM(COALESCE(qtd_pp,0)+COALESCE(qtd_p,0)+COALESCE(qtd_m,0)+COALESCE(qtd_g,0)+COALESCE(qtd_gg,0)+COALESCE(qtd_g1,0)+COALESCE(qtd_g2,0)+COALESCE(qtd_g3,0)),0)
                FROM {schema}.cortes_finalizados WHERE pago=TRUE AND data_chegada >= CURRENT_DATE - INTERVAL '{intervalo}'
            """)

            if row:
                if isinstance(row, dict):
                    vals = list(row.values())
                    return {"cortes": int(vals[0] or 0), "pecas": int(vals[1] or 0)}
                else:
                    return {"cortes": int(row[0] or 0), "pecas": int(row[1] or 0)}
            return {"cortes": 0, "pecas": 0}
        except:
            return {"cortes": 0, "pecas": 0}

    def _contar_atrasos_criticos_db(self, dias: int = 7) -> int:
        try:
            if not self.POSTGRES_DISPONIVEL:
                return 0

            if not _table_exists_pg("envios_cortes") or not _table_exists_pg("controle_retorno_cortes"):
                return 0

            schema = get_schema()
            row = _fetch_one(f"""
                SELECT COUNT(*) FROM {schema}.envios_cortes e
                LEFT JOIN {schema}.controle_retorno_cortes r ON r.envio_id = e.id
                WHERE r.id IS NULL AND e.data_envio <= CURRENT_DATE - INTERVAL '{dias} days'
            """)
            if row:
                return int(row[0] or 0) if not isinstance(row, dict) else int(list(row.values())[0] or 0)
            return 0
        except:
            return 0

    def _eficiencia_diaria_db(self, dias: int = 7) -> float:
        dados = self._buscar_dados_fluxo(dias)
        try:
            pagos = dados["quantidades"][5]
            pendente = dados["quantidades"][4]
            total = pagos + pendente
            if total <= 0:
                return 0.0
            return (pagos / total) * 100.0
        except Exception:
            return 0.0

    def _atualizar_painel_producao(self):
        try:
            periodo = self.painel_prod_periodo_var.get() or "7 dias"
            dias = int((periodo.split() or ["7"])[0])
        except Exception:
            dias = 7

        dados_fluxo = self._buscar_dados_fluxo(dias)
        total_fluxo = max(1, sum(dados_fluxo.get("quantidades", [])))

        andamento = self._contar_em_andamento_db()
        atrasos = self._contar_atrasos_criticos_db(dias=7)
        eficiencia = self._eficiencia_diaria_db(dias=dias)

        if hasattr(self, "lbl_painel_andamento"):
            self.lbl_painel_andamento.configure(text=str(andamento))
            self.pb_painel_andamento.set(min(1.0, andamento / total_fluxo))

        if hasattr(self, "lbl_painel_atrasos"):
            self.lbl_painel_atrasos.configure(text=str(atrasos))
            self.pb_painel_atrasos.set(min(1.0, atrasos / total_fluxo))

        if hasattr(self, "lbl_painel_eficiencia"):
            self.lbl_painel_eficiencia.configure(text=f"{eficiencia:.0f}%")
            self.pb_painel_eficiencia.set(min(1.0, eficiencia / 100.0))

        self._desenhar_grafico_painel(dados_fluxo)

    def _desenhar_grafico_painel(self, dados_fluxo: dict):
        if not hasattr(self, "painel_prod_chart"):
            return

        canvas = self.painel_prod_chart
        canvas.delete("all")

        largura = canvas.winfo_width()
        altura = canvas.winfo_height()
        if largura <= 10 or altura <= 10:
            self.after(100, lambda: self._desenhar_grafico_painel(dados_fluxo))
            return

        setor = self.painel_prod_setor_var.get() or "Todos"
        tipo = self.painel_prod_grafico_var.get() or "Barras"

        etapas = dados_fluxo.get("etapas", [])
        valores = dados_fluxo.get("quantidades", [])

        if setor != "Todos" and setor in etapas:
            idx = etapas.index(setor)
            valor_setor = valores[idx] if idx < len(valores) else 0
            total = sum(valores)
            etapas = [setor, "Outros"]
            valores = [valor_setor, max(0, total - valor_setor)]

        if not valores:
            return

        max_val = max(valores) if max(valores) > 0 else 1
        cores = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#0EA5E9", "#64748B"]

        if tipo == "Rosca":
            total = sum(valores)
            start = 0
            cx, cy = largura / 2, altura / 2
            raio = min(largura, altura) / 2 - 6
            for i, val in enumerate(valores):
                ext = (val / total) * 360 if total else 0
                canvas.create_arc(
                    cx - raio, cy - raio, cx + raio, cy + raio,
                    start=start, extent=ext, fill=cores[i % len(cores)], outline=""
                )
                start += ext
            canvas.create_oval(cx - raio * 0.7, cy - raio * 0.7, cx + raio * 0.7, cy + raio * 0.7,
                               fill="#FFFFFF", outline="")
        elif tipo == "Linha":
            padding = 12
            step = (largura - 2 * padding) / max(1, len(valores) - 1)
            pontos = []
            for i, val in enumerate(valores):
                x = padding + i * step
                y = altura - padding - (val / max_val) * (altura - 2 * padding)
                pontos.extend([x, y])
            if len(pontos) >= 4:
                canvas.create_line(*pontos, fill="#3B82F6", width=2, smooth=True)
                for i in range(0, len(pontos), 2):
                    canvas.create_oval(pontos[i] - 3, pontos[i + 1] - 3, pontos[i] + 3, pontos[i + 1] + 3,
                                       fill="#3B82F6", outline="")
        else:
            padding = 12
            largura_barra = (largura - 2 * padding) / max(1, len(valores))
            for i, val in enumerate(valores):
                x0 = padding + i * largura_barra + 4
                x1 = padding + (i + 1) * largura_barra - 4
                altura_barra = (val / max_val) * (altura - 2 * padding)
                y0 = altura - padding - altura_barra
                y1 = altura - padding
                canvas.create_rectangle(x0, y0, x1, y1, fill=cores[i % len(cores)], outline="")

    def _ultimos_finalizados_from_db(self, limite: int = 3):
        try:
            if not self.POSTGRES_DISPONIVEL:
                return []

            schema = get_schema()
            rows = _fetch_all(f"""
                SELECT COALESCE(codigo,'') as codigo, COALESCE(descricao,'') as descricao,
                    COALESCE(qtd_pp,0)+COALESCE(qtd_p,0)+COALESCE(qtd_m,0)+COALESCE(qtd_g,0)+
                    COALESCE(qtd_gg,0)+COALESCE(qtd_g1,0)+COALESCE(qtd_g2,0)+COALESCE(qtd_g3,0) as total,
                    data_chegada
                FROM {schema}.cortes_finalizados WHERE pago=TRUE
                ORDER BY data_chegada DESC, id DESC LIMIT {limite}
            """)

            itens = []
            for row in (rows or []):
                if isinstance(row, dict):
                    codigo = row.get('codigo', '')
                    descricao = row.get('descricao', '')
                    total = int(row.get('total', 0) or 0)
                    data = _to_date_any(row.get('data_chegada'))
                else:
                    codigo = row[0] if len(row) > 0 else ''
                    descricao = row[1] if len(row) > 1 else ''
                    total = int(row[2] or 0) if len(row) > 2 else 0
                    data = _to_date_any(row[3]) if len(row) > 3 else None

                itens.append({
                    "codigo": codigo,
                    "descricao": descricao,
                    "qtd": total,
                    "data_str": data.strftime("%d/%m/%Y") if data else "-"
                })
            return itens
        except:
            return []

    def _buscar_cortes_por_setor(self, setor: str):
        setor_norm = (setor or "").strip().lower()
        resultados = []

        if not self.POSTGRES_DISPONIVEL:
            return []

        schema = get_schema()

        try:
            if setor_norm == "todos":
                for sql in [
                    f"SELECT codigo_modelo as codigo, COALESCE(descricao_modelo,'') as descricao, COALESCE(cortador,'') as destino, COALESCE(data_registro,NOW()) as data_ref, COALESCE(quantidade_desejada,0) as qtd, COALESCE(dias_estimados,0) as dias, COALESCE(horas_estimadas,0) as horas, 'Ordem Corte' as origem FROM {schema}.ordem_corte_ficha ORDER BY id DESC LIMIT 20",
                    f"SELECT COALESCE(codigo,'') as codigo, COALESCE(descricao,'') as descricao, COALESCE(cortador,'') as destino, COALESCE(data,NOW()) as data_ref, COALESCE(total_pecas,0) as qtd, 0 as dias, 0 as horas, 'Corte Pronto' as origem FROM {schema}.cadastro_de_corte ORDER BY id DESC LIMIT 20",
                    f"SELECT COALESCE(e.codigo_corte,'') as codigo, COALESCE(e.descricao_corte,'') as descricao, COALESCE(f.nome,'') as destino, COALESCE(e.data_envio,NOW()) as data_ref, COALESCE(e.total_pecas,0) as qtd, 0 as dias, 0 as horas, 'Enviado' as origem FROM {schema}.envios_cortes e LEFT JOIN {schema}.cadastro_faccoes f ON e.prestador_id=f.id LEFT JOIN {schema}.controle_retorno_cortes r ON r.envio_id=e.id WHERE r.id IS NULL ORDER BY e.id DESC LIMIT 20",
                ]:
                    resultados.extend(_fetch_all(sql) or [])

            elif setor_norm in ("corte", "cortes", "ordem corte"):
                sql = f"SELECT codigo_modelo as codigo, COALESCE(descricao_modelo,'') as descricao, COALESCE(cortador,'') as destino, COALESCE(data_registro,NOW()) as data_ref, COALESCE(quantidade_desejada,0) as qtd, COALESCE(dias_estimados,0) as dias, COALESCE(horas_estimadas,0) as horas, 'Ordem Corte' as origem FROM {schema}.ordem_corte_ficha ORDER BY id DESC LIMIT 50"
                resultados = _fetch_all(sql) or []

            elif setor_norm == "cortes p/ enviar":
                sql = f"SELECT COALESCE(codigo,'') as codigo, COALESCE(descricao,'') as descricao, COALESCE(cortador,'') as destino, COALESCE(data,NOW()) as data_ref, COALESCE(total_pecas,0) as qtd, 0 as dias, 0 as horas, 'Corte Pronto' as origem FROM {schema}.cadastro_de_corte ORDER BY id DESC LIMIT 50"
                resultados = _fetch_all(sql) or []

            elif setor_norm in ("enviado", "enviados"):
                sql = f"SELECT COALESCE(e.codigo_corte,'') as codigo, COALESCE(e.descricao_corte,'') as descricao, COALESCE(f.nome,'') as destino, COALESCE(e.data_envio,NOW()) as data_ref, COALESCE(e.total_pecas,0) as qtd, 0 as dias, 0 as horas, 'Enviado' as origem FROM {schema}.envios_cortes e LEFT JOIN {schema}.cadastro_faccoes f ON e.prestador_id=f.id LEFT JOIN {schema}.controle_retorno_cortes r ON r.envio_id=e.id WHERE r.id IS NULL ORDER BY e.id DESC LIMIT 50"
                resultados = _fetch_all(sql) or []

            elif setor_norm in ("conferência", "conferencia"):
                sql = f"SELECT COALESCE(e.codigo_corte,'') as codigo, COALESCE(e.descricao_corte,'') as descricao, COALESCE(f.nome,'') as destino, COALESCE(r.data_chegada,NOW()) as data_ref, COALESCE(r.total_entregue,0) as qtd, 0 as dias, 0 as horas, 'Conferência' as origem FROM {schema}.controle_retorno_cortes r JOIN {schema}.envios_cortes e ON r.envio_id=e.id LEFT JOIN {schema}.cadastro_faccoes f ON e.prestador_id=f.id LEFT JOIN {schema}.cortes_finalizados cf ON cf.retorno_id=r.id WHERE cf.id IS NULL ORDER BY r.id DESC LIMIT 50"
                resultados = _fetch_all(sql) or []

            elif setor_norm in ("finalizado", "finalizados"):
                sql = f"SELECT COALESCE(codigo,'') as codigo, COALESCE(descricao,'') as descricao, COALESCE(costureira,'') as destino, COALESCE(data_chegada,NOW()) as data_ref, COALESCE(qtd_pp,0)+COALESCE(qtd_p,0)+COALESCE(qtd_m,0)+COALESCE(qtd_g,0)+COALESCE(qtd_gg,0)+COALESCE(qtd_g1,0)+COALESCE(qtd_g2,0)+COALESCE(qtd_g3,0) as qtd, 0 as dias, 0 as horas, CASE WHEN pago=TRUE THEN 'Pago' ELSE 'Pendente' END as origem FROM {schema}.cortes_finalizados ORDER BY id DESC LIMIT 50"
                resultados = _fetch_all(sql) or []

        except Exception as e:
            print(f"Erro busca: {e}")

        return resultados

    # ================== TABELAS ==================

    def _atualizar_tabela_estoque(self):
        setor = self.combo_tipo_estoque.get()
        tabelas = {"Tecidos": "estoque_tecidos", "Aviamentos": "estoque_aviamentos", "Insumos": "estoque_insumos",
                   "Escritorio": "estoque_escritorio", "Limpeza": "estoque_limpeza", "Outros": "estoque_outros"}
        nome_tabela = tabelas.get(setor)
        if not nome_tabela:
            return

        cols = _columns_pg(nome_tabela)
        if not cols:
            cols = ["id", "numero_item", "descricao", "codigo", "data_entrada",
                    "metros" if setor == "Tecidos" else "quantidade"]

        col_id = _pick(cols, "id", default="id")
        col_num = _pick(cols, "numero_item", "numero", default=None)
        col_desc = _pick(cols, "descricao", default=None)
        col_cod = _pick(cols, "codigo", default=None)
        col_data = _pick(cols, "data_entrada", "data", default=None)
        col_qtd = _pick(cols, "metros", "quantidade", default="quantidade") if setor == "Tecidos" else _pick(cols,
                                                                                                             "quantidade",
                                                                                                             default=None)

        select_cols = [col_id] + [c for c in (col_num, col_desc, col_cod, col_data, col_qtd) if c]
        sql = f"SELECT {', '.join(select_cols)} FROM {get_schema()}.{nome_tabela} ORDER BY {col_id} DESC LIMIT 50"
        rows = _fetch_all(sql) or []

        self.tree_est.delete(*self.tree_est.get_children())
        for r in rows:
            vals = [r.get(c) for c in select_cols] if isinstance(r, dict) else list(r)
            while len(vals) < 6:
                vals.append("")
            if len(vals) > 4:
                dt = _to_datetime_any(vals[4])
                if dt:
                    vals[4] = dt.strftime("%d/%m/%Y %H:%M")
            self.tree_est.insert("", "end", values=tuple(vals[:6]))

    def _preencher_tabela_andamento(self):
        try:
            for item in self.tree_and.get_children():
                self.tree_and.delete(item)
        except:
            pass

        if not self.POSTGRES_DISPONIVEL:
            self.tree_and.insert("", "end", values=("DB indisponível", "-", "-", "-", "0", "0", "0", "-"))
            return

        try:
            setor = self.selected_depart.get() or "Todos"
            linhas = self._buscar_cortes_por_setor(setor)

            if not linhas:
                self.tree_and.insert("", "end", values=("Sem dados", "-", "-", "-", "0", "0", "0", "-"))
                return

            for linha in linhas:
                if isinstance(linha, dict):
                    codigo = linha.get('codigo', '')
                    descricao = linha.get('descricao', '')
                    destino = linha.get('destino', '')
                    data_ref = linha.get('data_ref', '')
                    qtd = linha.get('qtd', 0)
                    dias = linha.get('dias', 0)
                    horas = linha.get('horas', 0)
                    origem = linha.get('origem', '')
                else:
                    vals = list(linha)
                    codigo = vals[0] if len(vals) > 0 else ''
                    descricao = vals[1] if len(vals) > 1 else ''
                    destino = vals[2] if len(vals) > 2 else ''
                    data_ref = vals[3] if len(vals) > 3 else ''
                    qtd = vals[4] if len(vals) > 4 else 0
                    dias = vals[5] if len(vals) > 5 else 0
                    horas = vals[6] if len(vals) > 6 else 0
                    origem = vals[7] if len(vals) > 7 else ''

                if isinstance(data_ref, (date, datetime)):
                    data_fmt = data_ref.strftime("%d/%m/%Y %H:%M") if isinstance(data_ref,
                                                                                 datetime) else data_ref.strftime(
                        "%d/%m/%Y")
                else:
                    data_fmt = str(data_ref).split(".")[0] if data_ref else ""

                self.tree_and.insert("", "end", values=(codigo, descricao, destino, data_fmt, qtd, dias, horas, origem))

            self.after(150, self._ajustar_colunas_conteudo)
        except Exception as e:
            print(f"Erro tabela: {e}")

    def _filtrar_tabela_andamento(self):
        self._preencher_tabela_andamento()

    def _ajustar_colunas_conteudo(self):
        try:
            for col in self.tree_and["columns"]:
                max_largura = len(col) * 12
                for item in self.tree_and.get_children():
                    valor = str(self.tree_and.set(item, col))
                    largura = len(valor) * 9
                    if largura > max_largura:
                        max_largura = largura
                self.tree_and.column(col, width=max(100, min(max_largura + 20, 300)))
        except:
            pass

    # ================== CARDS ==================

    def _criar_cards_resumo(self, parent_frame):
        parent_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="cards")

        def mk_card(col, titulo, lbl_attr, cor):
            card = ctk.CTkFrame(
                parent_frame,
                fg_color="#FFFFFF",
                corner_radius=12,
                border_width=1,
                border_color="#E2E8F0",
            )
            card.grid(row=0, column=col, padx=6, sticky="nsew")

            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=12, pady=(8, 0))
            ctk.CTkLabel(
                header,
                text=titulo,
                font=("Arial", 11, "bold"),
                text_color="#64748B",
            ).pack(anchor="w")

            lbl = ctk.CTkLabel(card, text="0", font=("Arial", 18, "bold"), text_color=cor)
            lbl.pack(anchor="w", padx=12, pady=(4, 6))

            barra = ctk.CTkProgressBar(card, progress_color=cor, height=6)
            barra.set(0.0)
            barra.pack(fill="x", padx=12, pady=(0, 10))
            setattr(self, f"{lbl_attr}_bar", barra)
            setattr(self, lbl_attr, lbl)

        mk_card(0, "Em Andamento", "lbl_card_andamento", self.cor_destaque)
        mk_card(1, "Finalizados (7d)", "lbl_card_finalizadas_7d", self.cor_sucesso)
        mk_card(2, "Produção Semanal", "lbl_card_prod_semanal", self.cor_destaque)
        mk_card(3, "Produção Mensal", "lbl_card_prod_mensal", self.cor_destaque)

        self.atualizar_cards_resumo()

    def atualizar_cards_resumo(self):
        try:
            self.lbl_card_andamento.configure(text=str(self._contar_em_andamento_db()))
            if hasattr(self, "lbl_card_andamento_bar"):
                self.lbl_card_andamento_bar.set(min(1.0, self._contar_em_andamento_db() / 100.0))
        except:
            pass

        try:
            prod_7d = self._sum_producao_periodo("semana")
            self.lbl_card_finalizadas_7d.configure(text=str(prod_7d["cortes"]))
            if hasattr(self, "lbl_card_finalizadas_7d_bar"):
                self.lbl_card_finalizadas_7d_bar.set(min(1.0, prod_7d["cortes"] / 100.0))
        except:
            pass

        try:
            prod_sem = self._sum_producao_periodo("semana")
            self.lbl_card_prod_semanal.configure(text=f"Cortes: {prod_sem['cortes']}\nPeças: {prod_sem['pecas']}")
            if hasattr(self, "lbl_card_prod_semanal_bar"):
                self.lbl_card_prod_semanal_bar.set(min(1.0, prod_sem["cortes"] / 100.0))
        except:
            pass

        try:
            prod_mes = self._sum_producao_periodo("mes")
            self.lbl_card_prod_mensal.configure(text=f"Cortes: {prod_mes['cortes']}\nPeças: {prod_mes['pecas']}")
            if hasattr(self, "lbl_card_prod_mensal_bar"):
                self.lbl_card_prod_mensal_bar.set(min(1.0, prod_mes["cortes"] / 100.0))
        except:
            pass

    def _carregar_ultimos_finalizados(self, parent=None, limite: int = 3):
        if parent is not None:
            self.frame_ultimos = parent
        elif not hasattr(self, "frame_ultimos") or self.frame_ultimos is None:
            self.frame_ultimos = ctk.CTkFrame(self, fg_color="transparent")
            self.frame_ultimos.pack(fill="x", pady=(4, 0))

        for w in self.frame_ultimos.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.frame_ultimos, text="ÚLTIMOS FINALIZADOS (PAGOS)", font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=self.cor_texto).pack(anchor="w", padx=10, pady=(0, 4))

        row = ctk.CTkFrame(self.frame_ultimos, fg_color="transparent")
        row.pack(fill="x", padx=8)

        dados = self._ultimos_finalizados_from_db(limite=limite)
        if not dados:
            dados = [{"codigo": "-", "descricao": "Nenhum corte pago", "qtd": 0, "data_str": "-"}]
        while len(dados) < 3:
            dados.append({"codigo": "-", "descricao": "-", "qtd": 0, "data_str": "-"})

        for i, it in enumerate(dados[:3]):
            card = ctk.CTkFrame(row, fg_color=self.cor_secundaria, corner_radius=10, border_width=1,
                                border_color=self.cor_borda, height=90)
            card.grid(row=0, column=i, sticky="nsew", padx=8, pady=4)
            card.pack_propagate(False)

            ctk.CTkLabel(card, text=f"Cód: {it.get('codigo', '-')}", font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=self.cor_destaque).pack(pady=(6, 0))

            desc = it.get('descricao', '-')
            ctk.CTkLabel(card, text=desc[:30] + "..." if len(desc) > 30 else desc, font=ctk.CTkFont(size=12),
                         text_color=self.cor_texto).pack(pady=(2, 0))

            ctk.CTkLabel(card, text=f"Peças: {it.get('qtd', 0)}", font=ctk.CTkFont(size=16, weight="bold"),
                         text_color="#40A9FF").pack(pady=(2, 0))

            ctk.CTkLabel(card, text=it.get("data_str", "-"), font=ctk.CTkFont(size=12), text_color=self.cor_texto).pack(
                pady=(0, 4))

            row.grid_columnconfigure(i, weight=1)

    # ================== AUTO REFRESH ==================

    def _setup_auto_refresh(self):
        try:
            self.after(5000, self._poll_refresh_token)
        except:
            pass

    def _refresh_debounced(self, ms: int = 500):
        try:
            if getattr(self, "_refresh_after_id", None):
                self.after_cancel(self._refresh_after_id)
        except:
            pass
        self._refresh_after_id = self.after(ms, self.atualizar_dashboard)

    def _poll_refresh_token(self):
        try:
            if hasattr(self, 'lbl_card_andamento'):
                self.atualizar_cards_resumo()
        except:
            pass
        finally:
            try:
                self.after(5000, self._poll_refresh_token)
            except:
                pass

    def iniciar_atualizacao_automatica(self, intervalo_segundos: int = 60):
        try:
            pass
        except:
            pass
        self.after(intervalo_segundos * 1000, lambda: self.iniciar_atualizacao_automatica(intervalo_segundos))

    def atualizar_dashboard(self):
        try:
            self.atualizar_cards_resumo()
            self._atualizar_painel_producao()
            self._preencher_tabela_andamento()
            self._atualizar_tabela_estoque()
            if getattr(self, "tipo_grafico", "producao") == "producao":
                self._mostrar_grafico_producao()
            self._carregar_ultimos_finalizados(limite=3)
        except Exception as e:
            print(f"Erro dashboard: {e}")

    def on_show(self):
        self.atualizar_dashboard()

    def _aplicar_estilo_treeviews(self):
        try:
            style = ttk.Style()
            cab_bg = self.cor_cabecalho_fundo
            if is_dark_color(self.cor_fundo):
                linhas_bg = "#111827"
                linhas_fg = "#E5E7EB"
            else:
                linhas_bg = self.cor_linhas_fundo
                linhas_fg = self.cor_linhas_texto

            selecao_bg = ajustar_hover(self.cor_destaque)

            aplicar_estilo_treeview(
                style=style, prefixo="OperaDashboard.Treeview",
                cor_fundo=self.cor_fundo, cor_linhas=linhas_bg,
                cor_cabecalho=cab_bg, cor_texto=linhas_fg,
                cor_borda=self.cor_borda, cor_selecao=selecao_bg, altura_linha=22)

            for tree in (getattr(self, "tree_est", None), getattr(self, "tree_and", None)):
                if tree:
                    tree.configure(style="OperaDashboard.Treeview")
                    aplicar_tags_alternadas(tree, linhas_bg, self.cor_fundo)
        except Exception as e:
            print(f"Erro estilo: {e}")


# ===================== TESTE =====================
if __name__ == "__main__":
    class SistemaBasico:
        cor_primaria = "#0e1a2b"
        cor_secundaria = "#1a2b45"
        cor_terciaria = "#2e3a4a"
        cor_fundo = "#121b2e"
        cor_texto = "#f5f7fa"
        cor_destaque = "#3b82f6"
        cor_sucesso = "#10b981"
        cor_alerta = "#f59e0b"
        cor_borda = "#2e3a4a"
        cor_hover = "#334155"
        dados_producao = {"em_andamento": [], "finalizados": [], "metas": {}}
        departamentos = ["Corte", "Facção", "Bordado", "Acabamento"]


    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.title("Dashboard - PostgreSQL")
    root.geometry("1200x800")

    page = DashboardPage(root, sistema=SistemaBasico())
    page.pack(fill="both", expand=True)

    root.bind('<F5>', lambda e: page.atualizar_dashboard())
    root.mainloop()

#03/02/2025