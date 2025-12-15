# -*- coding: utf-8 -*-
"""
Dashboard (PostgreSQL com Fallback)
----------------------
- Mantém layout e lógica visual.
- Funciona mesmo sem PostgreSQL com dados mock.
- Inclui teste isolado com `if __name__ == "__main__":`.
"""

import os
from datetime import datetime, timedelta, date
import customtkinter as ctk
from TEMAS import (
    get_contraste_texto,
    is_dark_color,
    ajustar_hover,
    aplicar_estilo_treeview,
    aplicar_tags_alternadas,
)
from tkinter import ttk, messagebox

# ==== IMPORT CORRETO DO MÓDULO POSTGRESQL COM FALLBACK ====
POSTGRES_DISPONIVEL = False

try:
    # Tenta importar o módulo PostgreSQL
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    from BANCO_DE_DADOS_PG import (
        get_schema, ready_check,
        fetch_all, fetch_one, execute, get_conn
    )

    # Testa a conexão usando ready_check()
    try:
        if ready_check():
            POSTGRES_DISPONIVEL = True
            print("✅ PostgreSQL conectado com sucesso!")

            # Define o search_path explicitamente.  BANCO_DE_DADOS_PG já define,
            # mas repetimos aqui para garantir que a sessão atual esteja correta.
            try:
                schema = get_schema() or "opera"
                execute(f"SET search_path TO {schema}, public")
                print(f"[OK] search_path definido para: {schema}, public")
            except Exception as se:
                print(f"[WARN] Não foi possível definir search_path: {se}")

            # Aliases locais
            globals()['_fetch_all'] = fetch_all
            globals()['_fetch_one'] = fetch_one
            globals()['_exec_write'] = execute
        else:
            print("⚠️ PostgreSQL não disponível: ready_check() retornou False")
            POSTGRES_DISPONIVEL = False
    except Exception as e:
        print(f"❌ Erro ao testar PostgreSQL: {e}")
        POSTGRES_DISPONIVEL = False

except Exception as e:
    print(f"❌ Módulo PostgreSQL não disponível: {e}")
    POSTGRES_DISPONIVEL = False

# ==== FALLBACK PARA DADOS MOCK ====
if not POSTGRES_DISPONIVEL:
    # Banco de dados indisponível: log informativo (sem referência a mock)
    print("ℹ️ Banco de dados indisponível. Funções de fallback ativas.")


    # Classe de dados de demonstração (não usada).  Mantida para compatibilidade.
    class DadosMock:
        def __init__(self):
            # Estruturas vazias — não retornam dados de demonstração
            self.estoque_tecidos = []
            self.ordem_corte_ficha = []
            self.cadastro_de_corte = []
            self.cortes_finalizados = []


    dados_mock = DadosMock()


    # Funções de fallback: retornam dados vazios para SELECTs e 0 para comandos de escrita.
    def _fetch_all(sql, params=None):
        """Retorna lista vazia quando o banco não está disponível."""
        return []


    def _fetch_one(sql, params=None):
        """Retorna None quando o banco não está disponível."""
        return None


    def _exec_write(sql, params=None):
        """Comando de escrita em modo offline: não faz nada e retorna 0."""
        return 0


    def get_schema():
        """Retorna o schema padrão (public) quando o banco não está disponível."""
        return "public"


    def require_ready():
        """Indica que o banco está indisponível ao chamar require_ready."""
        return (False, "Banco de dados indisponível")


# ==== HELPERS PARA POSTGRESQL ====
def _table_exists_pg(table_name: str) -> bool:
    """
    True se a tabela existir em QUALQUER schema do search_path atual,
    com fallback explícito para get_schema(), 'opera' e 'public'.
    Compatível com _fetch_one que retorna dict ou tupla.
    """
    tn = (table_name or "").strip().lower()
    if not tn:
        return False

    # 1) no search_path atual
    try:
        row = _fetch_one(
            """
            SELECT EXISTS (
              SELECT 1
                FROM pg_catalog.pg_tables
               WHERE LOWER(tablename) = LOWER(%s)
                 AND schemaname = ANY (current_schemas(true))
            ) AS ok
            """,
            (tn,),
        )
        ok = (row.get("ok") if isinstance(row, dict) else row[0]) if row else False
        if bool(ok):
            return True
    except Exception:
        pass

    # 2) schemas explícitos (o configurado, 'opera', 'public')
    for sc in ((get_schema() or "opera"), "opera", "public"):
        try:
            row = _fetch_one(
                """
                SELECT EXISTS (
                  SELECT 1
                    FROM information_schema.tables
                   WHERE LOWER(table_schema) = LOWER(%s)
                     AND LOWER(table_name)   = LOWER(%s)
                ) AS ok
                """,
                (sc, tn),
            )
            ok = (row.get("ok") if isinstance(row, dict) else row[0]) if row else False
            if bool(ok):
                return True
        except Exception:
            continue

    return False


def _columns_pg(table: str):
    """Lista colunas em qualquer schema do search_path; fallback para schema configurado/opera/public."""
    tn = table.lower()
    # 1) tenta no search_path
    try:
        rows = _fetch_all("""
            SELECT c.column_name
              FROM information_schema.columns c
             WHERE c.table_name = %s
               AND c.table_schema = ANY (current_schemas(true))
             ORDER BY c.ordinal_position
        """, (tn,))
        if rows:
            return [list(r.values())[0] for r in rows]
    except Exception:
        pass

    # 2) tenta explicitamente em schemas comuns
    for sc in [get_schema(), "opera", "public"]:
        try:
            rows = _fetch_all("""
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = %s
                   AND table_name   = %s
                 ORDER BY ordinal_position
            """, (sc, tn))
            if rows:
                return [list(r.values())[0] for r in rows]
        except Exception:
            continue
    return []


def _pick_column_pg(table: str, candidates: list[str]) -> str | None:
    """Encontra a primeira coluna que existe na tabela entre os candidatos."""
    cols = _columns_pg(table)
    if not cols:
        return None

    lc_cols = [c.lower() for c in cols]
    for candidate in candidates:
        if candidate.lower() in lc_cols:
            return cols[lc_cols.index(candidate.lower())]
    return None


def _pick(colnames, *candidates, default=None):
    """Encontra o primeiro candidato que existe na lista de nomes de colunas."""
    lc = [c.lower() for c in colnames]
    for cand in candidates:
        if cand.lower() in lc:
            return colnames[lc.index(cand.lower())]
    return default


def _to_date_any(v):
    """Aceita date/datetime/str (YYYY-MM-DD ou DD/MM/YYYY) e retorna date ou None."""
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
        except Exception:
            pass
    return None


def _to_datetime_any(v):
    """Aceita datetime/date/str e retorna datetime (00:00 se vier apenas data)."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, datetime.min.time())

    s = str(v).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(s[:19], fmt)
        except Exception:
            pass
    return None


# ===================== DASHBOARD UI =====================
class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, sistema):
        super().__init__(master, fg_color=sistema.cor_fundo)
        self.sistema = sistema
        self.POSTGRES_DISPONIVEL = POSTGRES_DISPONIVEL

        # Paleta herdada
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

        # Cores para Treeview - CORES FIXAS para garantir contraste
        self.cor_cabecalho_fundo = "#2C3E50"  # AZUL ESCURO
        self.cor_cabecalho_texto = "#FFFFFF"  # BRANCO
        self.cor_linhas_fundo = "#FFFFFF"  # BRANCO
        self.cor_linhas_texto = "#000000"  # PRETO

        # Cores para comboboxes em fundos claros
        self.cor_combobox_fundo = "#FFFFFF"  # BRANCO
        self.cor_combobox_texto = "#000000"  # PRETO
        self.cor_combobox_botao = "#2C3E50"  # AZUL ESCURO
        self.cor_combobox_botao_hover = "#1a2b45"  # AZUL MAIS ESCURO

        # Mock de dados auxiliares
        self.dados_producao = getattr(
            sistema, "dados_producao",
            {"em_andamento": [], "finalizados": [],
             "metas": {"semanal": 0, "atingido_semanal": 0,
                       "mensal": 0, "atingido_mensal": 0}}
        )
        self.departamentos = getattr(
            sistema, "departamentos",
            ["Corte", "Facção", "Bordado", "Caseador",
             "Botões", "Estamparia", "Tingimento", "Acabamento"]
        )
        self.selected_depart = ctk.StringVar(value="Todos")

        # Estado do gráfico
        self.fig_grafico = None
        self.ax_grafico = None
        self.canvas_grafico = None
        self.filtro_tempo_var = ctk.StringVar(value="7 dias")
        self.tipo_grafico = "dashboard"
        self.modelo_selecionado = None

        # Frame principal dos cards
        self.frame_cards = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        self.frame_cards.pack(fill="x", pady=(0, 2))

        # Cards + restante da UI
        self._criar_cards_resumo(self.frame_cards)
        self._construir()

        # Atualização inicial
        self.atualizar_dashboard()
        self.bind("<Map>", lambda e: self._refresh_debounced())
        self.bind("<Visibility>", lambda e: self._refresh_debounced())
        self.on_show = self.atualizar_dashboard

        # Auto-refresh tolerante
        self._setup_auto_refresh()
        self.bind("<FocusIn>", lambda e: self._refresh_debounced())
        self.iniciar_atualizacao_automatica(30)

    # ------------------------ UI ------------------------
    def _construir(self):

        # ============================================================
        # DEFINIÇÕES ESSENCIAIS (antes de usar estoque/grafico)
        # ============================================================
        self.tipos_estoque = ["Tecidos", "Aviamentos", "Insumos", "Escritorio", "Limpeza", "Outros"]
        self.cols_estoque = ("ID", "Número Item", "Descrição", "Código", "Data Entrada", "Quantidade")

        # ============================================================
        #     CARDS (já criados no __init__) – apenas compacta espaço
        # ============================================================
        self.frame_cards.pack(fill="x", pady=(0, 4))

        # ============================================================
        #  SEÇÃO DUPLA LADO A LADO: ESTOQUE (ESQ) + GRÁFICO (DIR)
        # ============================================================

        duplo_section = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        duplo_section.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        # As duas colunas se expandem ao esticar tela
        duplo_section.grid_columnconfigure(0, weight=2)  # Estoque
        duplo_section.grid_columnconfigure(1, weight=3)  # Gráfico
        duplo_section.grid_rowconfigure(0, weight=1)

        # ============================================================
        #                    ESTOQUE À ESQUERDA
        # ============================================================

        frame_est = ctk.CTkFrame(duplo_section, fg_color="#F8F9FA", corner_radius=10)
        frame_est.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        frame_est.grid_rowconfigure(2, weight=1)  # tabela expande
        frame_est.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame_est,
            text="ESTOQUE",
            font=("Arial", 14, "bold"),
            text_color="#2C3E50"
        ).grid(row=0, column=0, pady=(6, 2), sticky="w", padx=10)

        # --- filtro estoque ---
        filtro_est = ctk.CTkFrame(frame_est, fg_color="#F8F9FA")
        filtro_est.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 4))
        filtro_est.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            filtro_est,
            text="Tipo:",
            font=("Arial", 12),
            text_color="#2C3E50"
        ).grid(row=0, column=0, padx=(0, 6))

        self.combo_tipo_estoque = ctk.CTkComboBox(
            filtro_est,
            values=self.tipos_estoque,
            command=lambda _: self._atualizar_tabela_estoque(),
            fg_color=self.cor_combobox_fundo,
            text_color=self.cor_combobox_texto,
            button_color=self.cor_combobox_botao,
            button_hover_color=self.cor_combobox_botao_hover
        )
        self.combo_tipo_estoque.grid(row=0, column=1, sticky="ew")
        self.combo_tipo_estoque.set("Tecidos")

        # --- tabela estoque ---
        tabela_frame = ctk.CTkFrame(frame_est, fg_color="#F8F9FA")
        tabela_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=4)
        tabela_frame.grid_columnconfigure(0, weight=1)
        tabela_frame.grid_rowconfigure(0, weight=1)

        self.tree_est = ttk.Treeview(
            tabela_frame,
            columns=self.cols_estoque,
            show="headings",
            height=8
        )

        for col in self.cols_estoque:
            self.tree_est.heading(col, text=col)
            self.tree_est.column(col, anchor="w", width=120)

        sb_e = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tree_est.yview)
        self.tree_est.configure(yscroll=sb_e.set)

        sb_e.grid(row=0, column=1, sticky="ns")
        self.tree_est.grid(row=0, column=0, sticky="nsew")

        self._atualizar_tabela_estoque()

        # ============================================================
        #                     GRÁFICO À DIREITA
        # ============================================================

        frame_gra = ctk.CTkFrame(duplo_section, fg_color=self.cor_secundaria, corner_radius=10)
        frame_gra.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        frame_gra.grid_columnconfigure(0, weight=1)
        frame_gra.grid_rowconfigure(2, weight=1)  # gráfico expande

        ctk.CTkLabel(
            frame_gra,
            text="STATUS DE PRODUÇÃO",
            font=("Arial", 14, "bold"),
            text_color=self.cor_texto
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(6, 2))

        self.tempo_menu = ctk.CTkOptionMenu(
            frame_gra,
            values=["7 dias", "15 dias", "30 dias"],
            variable=self.filtro_tempo_var,
            command=lambda _: self.atualizar_grafico_dashboard(),
            fg_color=self.cor_terciaria,
            text_color=self.cor_texto,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_destaque
        )
        self.tempo_menu.grid(row=1, column=0, sticky="e", padx=10, pady=(0, 4))

        # container do gráfico
        self.grafico_container = ctk.CTkFrame(
            frame_gra,
            fg_color=self.cor_secundaria,
            corner_radius=8
        )
        self.grafico_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=6)
        self.grafico_container.grid_columnconfigure(0, weight=1)
        self.grafico_container.grid_rowconfigure(0, weight=1)

        # cria gráfico
        self.criar_grafico_dashboard()

        # ============================================================
        #        ÚLTIMOS FINALIZADOS (compactado)
        # ============================================================
        self._carregar_ultimos_finalizados(limite=3)

        # ============================================================
        #        PRODUÇÃO EM ANDAMENTO (compactado)
        # ============================================================

        frame_and = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        frame_and.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            frame_and,
            text="PRODUÇÃO EM ANDAMENTO",
            font=("Arial", 15, "bold"),
            text_color=self.cor_texto
        ).pack(pady=(4, 2))

        # filtro setores
        filtro_frame = ctk.CTkFrame(frame_and, fg_color="#F8F9FA", corner_radius=6)
        filtro_frame.pack(fill="x", pady=(2, 2))

        ctk.CTkLabel(
            filtro_frame,
            text="Departamento:",
            font=("Arial", 12),
            text_color="#2C3E50"
        ).pack(side="left", padx=(6, 6))

        deps_ext = list(self.departamentos)
        try:
            idx = deps_ext.index("Corte")
            deps_ext.insert(idx + 1, "CORTES P/ ENVIAR")
        except:
            deps_ext.append("CORTES P/ ENVIAR")

        valores = ["Todos"] + deps_ext

        self.combo_depart = ctk.CTkComboBox(
            filtro_frame,
            values=valores,
            variable=self.selected_depart,
            command=lambda _: self._filtrar_tabela_andamento(),
            width=160,
            height=23
        )
        self.combo_depart.pack(side="left")

        # tabela produção
        cont = ctk.CTkFrame(frame_and, fg_color="#F8F9FA", corner_radius=6)
        cont.pack(fill="x", padx=10, pady=(0, 4))

        tree_container = ctk.CTkFrame(cont, fg_color="transparent")
        tree_container.pack(fill="x")

        cols = (
            "Código", "Descrição", "Cortador", "Data Registro",
            "Qtd. Desejada", "Dias Estimados", "Horas Estimadas", "Origem"
        )

        self.tree_and = ttk.Treeview(
            tree_container,
            columns=cols,
            show="headings",
            height=5
        )

        for c in cols:
            self.tree_and.heading(c, text=c)
            self.tree_and.column(c, anchor="w", width=120)

        sb1 = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_and.yview)
        self.tree_and.configure(yscroll=sb1.set)
        sb1.pack(side="right", fill="y")

        sb2 = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree_and.xview)
        self.tree_and.configure(xscroll=sb2.set)
        sb2.pack(side="bottom", fill="x")

        self.tree_and.pack(fill="x", padx=5, pady=4)

        self.tree_and.bind("<<TreeviewSelect>>", lambda e: self.atualizar_grafico_tempo_modelo())
        self.tree_and.bind("<Double-1>", lambda e: self.atualizar_grafico_tempo_modelo())

        self.after(100, self._ajustar_colunas_conteudo)
        self._aplicar_estilo_treeviews()

    def _ajustar_colunas_conteudo(self):
        """Ajusta automaticamente a largura das colunas do Treeview com base no conteúdo."""
        try:
            for col in self.tree_and["columns"]:
                max_largura = len(col) * 12  # largura mínima pelo título
                for item in self.tree_and.get_children():
                    valor = str(self.tree_and.set(item, col))
                    largura = len(valor) * 9
                    if largura > max_largura:
                        max_largura = largura
                self.tree_and.column(col, width=max(120, min(max_largura + 20, 400)))
        except Exception as e:
            print(f"⚠️ Erro ao ajustar colunas: {e}")

    # ------------------------ Data helpers ------------------------
    def iniciar_atualizacao_automatica(self, intervalo_segundos: int = 60):
        """Atualiza automaticamente os dados e o gráfico do dashboard a cada intervalo."""
        try:
            if hasattr(self, "_carregar_cortes"):
                self._carregar_cortes()
            elif hasattr(self, "_atualizar_cortes"):
                self._atualizar_cortes()

            if hasattr(self, "_atualizar_grafico"):
                self._atualizar_grafico()

            print(f"🔄 Gráfico atualizado automaticamente ({intervalo_segundos}s)")

        except Exception as e:
            print(f"⚠️ Erro na atualização automática: {e}")

        # Agenda a próxima execução sem travar a interface
        self.after(intervalo_segundos * 1000, lambda: self.iniciar_atualizacao_automatica(intervalo_segundos))

    def _atualizar_tabela_estoque(self):
        setor = self.combo_tipo_estoque.get()
        tabelas = {
            "Tecidos": "estoque_tecidos",
            "Aviamentos": "estoque_aviamentos",
            "Insumos": "estoque_insumos",
            "Escritorio": "estoque_escritorio",
            "Limpeza": "estoque_limpeza",
            "Outros": "estoque_outros",
        }
        nome_tabela = tabelas.get(setor)
        if not nome_tabela:
            return

        if not _table_exists_pg(nome_tabela):
            try:
                _fetch_one(f"SELECT 1 FROM {get_schema()}.{nome_tabela} LIMIT 1")
            except Exception:
                messagebox.showwarning("Aviso", f"Tabela '{nome_tabela}' não encontrada.")
                return

        cols = _columns_pg(nome_tabela)
        if not cols and setor == "Tecidos" and not self.POSTGRES_DISPONIVEL:
            cols = ["id", "numero_item", "descricao", "codigo", "data_entrada", "metros"]

        col_id = _pick(cols, "id", default="id")
        col_num = _pick(cols, "numero_item", "numero", "nitem", default=None)
        col_desc = _pick(cols, "descricao", "descricao_item", "descricao_tecido", default=None)
        col_cod = _pick(cols, "codigo", "cod", default=None)
        col_data = _pick(cols, "data_entrada", "data", default=None)
        if nome_tabela == "estoque_tecidos":
            col_qtd = _pick(cols, "metros", "quantidade", default="metros")
        else:
            col_qtd = _pick(cols, "quantidade", "qtd", "qtde", default=None)

        select_cols = [col_id] + [c for c in (col_num, col_desc, col_cod, col_data, col_qtd) if c]
        if self.POSTGRES_DISPONIVEL:
            sql = f"SELECT {', '.join(select_cols)} FROM {get_schema()}.{nome_tabela} ORDER BY {col_id} DESC LIMIT 50"
        else:
            sql = f"SELECT {', '.join(select_cols)} FROM {nome_tabela} ORDER BY {col_id} DESC LIMIT 50"

        rows = _fetch_all(sql) or []

        self.tree_est.delete(*self.tree_est.get_children())
        for r in rows:
            if isinstance(r, dict):
                vals = [r.get(c) for c in select_cols]
            else:
                vals = list(r)

            while len(vals) < 6:
                vals.append("")

            if len(vals) > 4:
                dt_ref = _to_datetime_any(vals[4])
                if dt_ref:
                    vals[4] = dt_ref.strftime("%d/%m/%Y %H:%M")

            self.tree_est.insert("", "end", values=tuple(vals[:6]))

    def _buscar_cortes_por_setor(self, setor: str):
        """Busca cortes por setor - APENAS dados reais."""
        setor_norm = (setor or "").strip().lower()
        resultados = []

        try:
            if not self.POSTGRES_DISPONIVEL:
                print("❌ PostgreSQL não disponível")
                return []

            print(f"🔍 Buscando cortes para setor: {setor_norm}")

            if setor_norm in ("corte", "cortes"):
                sql = f"""
                    SELECT 
                        codigo_modelo as codigo,
                        COALESCE(descricao_modelo,'') as descricao,
                        COALESCE(cortador,'') as destino,
                        COALESCE(data_registro, NOW()) as data_ref,
                        COALESCE(quantidade_desejada,0) as qtd,
                        COALESCE(dias_estimados,0) as dias_estimados,
                        COALESCE(horas_estimadas,0) as horas_estimadas,
                        'Corte' as origem
                    FROM {get_schema()}.ordem_corte_ficha
                    ORDER BY id DESC
                    LIMIT 100
                """
                print("📋 SQL Ordem Corte:", sql)
                resultados = _fetch_all(sql)
                print(f"✅ Encontrados {len(resultados)} cortes em ordem_corte_ficha")

            elif setor_norm == "cortes p/ enviar":
                sql = f"""
                    SELECT 
                        COALESCE(codigo,'') as codigo,
                        COALESCE(descricao,'') as descricao,
                        COALESCE(cortador,'') as destino,
                        COALESCE(data, NOW()) as data_ref,
                        COALESCE(total_pecas,0) as qtd,
                        0 as dias_estimados,
                        0 as horas_estimadas,
                        'Cortes p/ Enviar' as origem
                    FROM {get_schema()}.cadastro_de_corte
                    ORDER BY id DESC
                    LIMIT 100
                """
                print("📋 SQL Cadastro Corte:", sql)
                resultados = _fetch_all(sql)
                print(f"✅ Encontrados {len(resultados)} cortes em cadastro_de_corte")

            elif setor_norm == "todos":
                sql_ordem = f"""
                    SELECT 
                        codigo_modelo as codigo,
                        COALESCE(descricao_modelo,'') as descricao,
                        COALESCE(cortador,'') as destino,
                        COALESCE(data_registro, NOW()) as data_ref,
                        COALESCE(quantidade_desejada,0) as qtd,
                        COALESCE(dias_estimados,0) as dias_estimados,
                        COALESCE(horas_estimadas,0) as horas_estimadas,
                        'Corte' as origem
                    FROM {get_schema()}.ordem_corte_ficha
                    ORDER BY id DESC
                    LIMIT 50
                """
                sql_cadastro = f"""
                    SELECT 
                        COALESCE(codigo,'') as codigo,
                        COALESCE(descricao,'') as descricao,
                        COALESCE(cortador,'') as destino,
                        COALESCE(data, NOW()) as data_ref,
                        COALESCE(total_pecas,0) as qtd,
                        0 as dias_estimados,
                        0 as horas_estimadas,
                        'Cortes p/ Enviar' as origem
                    FROM {get_schema()}.cadastro_de_corte
                    ORDER BY id DESC
                    LIMIT 50
                """
                resultados_ordem = _fetch_all(sql_ordem)
                resultados_cadastro = _fetch_all(sql_cadastro)
                resultados = resultados_ordem + resultados_cadastro
                print(f"✅ Encontrados {len(resultados)} cortes no total")

            else:
                sql = f"""
                    SELECT 
                        COALESCE(codigo_corte,'') as codigo,
                        COALESCE(descricao_corte,'') as descricao,
                        COALESCE(destino,'') as destino,
                        COALESCE(data_envio, NOW()) as data_ref,
                        COALESCE(total_pecas,0) as qtd,
                        0 as dias_estimados,
                        0 as horas_estimadas,
                        COALESCE(servico,'') as origem
                    FROM {get_schema()}.controle_envio_cortes
                    WHERE LOWER(COALESCE(servico,'')) = LOWER(%s)
                    ORDER BY id DESC
                    LIMIT 100
                """
                resultados = _fetch_all(sql, (setor_norm,))
                print(f"✅ Encontrados {len(resultados)} cortes para setor {setor_norm}")

        except Exception as e:
            print(f"❌ Erro ao buscar cortes: {e}")
            resultados = []

        return resultados

    def _preencher_tabela_andamento(self):
        """Recarrega a Treeview 'PRODUÇÃO EM ANDAMENTO' com dados reais."""
        try:
            for item in self.tree_and.get_children():
                self.tree_and.delete(item)
        except Exception:
            pass

        if not self.POSTGRES_DISPONIVEL:
            self.tree_and.insert("", "end", values=(
                "Banco de dados",
                "indisponível",
                "Conecte ao PostgreSQL",
                "-",
                "0",
                "0",
                "0",
                "-"
            ))
            self.after(150, self._ajustar_colunas_conteudo)
            return

        try:
            setor = (self.selected_depart.get() if hasattr(self, "selected_depart") else "Todos") or "Todos"
            linhas = self._buscar_cortes_por_setor(setor)

            if not linhas:
                self.tree_and.insert("", "end", values=(
                    "Nenhum dado",
                    "encontrado",
                    "Verifique as tabelas",
                    "-",
                    "0",
                    "0",
                    "0",
                    "-"
                ))
                self.after(150, self._ajustar_colunas_conteudo)
                return

            for linha in linhas:
                if isinstance(linha, dict):
                    codigo = linha.get('codigo', '')
                    descricao = linha.get('descricao', '')
                    destino = linha.get('destino', '')
                    data_ref = linha.get('data_ref', '')
                    qtd = linha.get('qtd', 0)
                    dias_estimados = linha.get('dias_estimados', 0)
                    horas_estimadas = linha.get('horas_estimadas', 0)
                    origem = linha.get('origem', '')
                else:
                    vals = list(linha) if not isinstance(linha, tuple) else list(linha)
                    codigo = vals[0] if len(vals) > 0 else ''
                    descricao = vals[1] if len(vals) > 1 else ''
                    destino = vals[2] if len(vals) > 2 else ''
                    data_ref = vals[3] if len(vals) > 3 else ''
                    qtd = vals[4] if len(vals) > 4 else 0
                    dias_estimados = vals[5] if len(vals) > 5 else 0
                    horas_estimadas = vals[6] if len(vals) > 6 else 0
                    origem = vals[7] if len(vals) > 7 else ''

                if isinstance(data_ref, (date, datetime)):
                    fmt_base = "%d/%m/%Y %H:%M" if isinstance(data_ref, datetime) else "%d/%m/%Y"
                    data_fmt = data_ref.strftime(fmt_base)
                else:
                    data_fmt = str(data_ref).split(".")[0] if data_ref else ""

                qtd_fmt = f"{int(qtd):,}" if qtd else "0"

                try:
                    dias_val = float(dias_estimados) if dias_estimados is not None else 0.0
                except Exception:
                    dias_val = 0.0
                dias_fmt = f"{dias_val:.2f}".rstrip("0").rstrip(".") if dias_val else "0"

                try:
                    horas_val = float(horas_estimadas) if horas_estimadas is not None else 0.0
                except Exception:
                    horas_val = 0.0
                horas_fmt = f"{horas_val:.2f}".rstrip("0").rstrip(".") if horas_val else "0"

                self.tree_and.insert(
                    "", "end",
                    values=(codigo, descricao, destino, data_fmt, qtd_fmt, dias_fmt, horas_fmt, origem)
                )

            self.after(150, self._ajustar_colunas_conteudo)

        except Exception as e:
            print(f"Erro ao preencher tabela andamento: {e}")
            self.tree_and.insert("", "end", values=(
                "Erro",
                f"ao carregar: {str(e)[:30]}",
                "Verifique console",
                "-",
                "0",
                "0",
                "0",
                "-"
            ))
            self.after(150, self._ajustar_colunas_conteudo)

    def _filtrar_tabela_andamento(self):
        self._preencher_tabela_andamento()

    # ------------------------ Charts ------------------------
    def criar_grafico_dashboard(self):
        for w in self.grafico_container.winfo_children():
            w.destroy()

        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            self.fig_grafico = Figure(figsize=(3, 3), dpi=100, facecolor=self.cor_secundaria)
            self.ax_grafico = self.fig_grafico.add_subplot(111)
            self.fig_grafico.patch.set_facecolor(self.cor_secundaria)
            self.ax_grafico.set_facecolor(self.cor_secundaria)

            self.ax_grafico.pie(
                [1],
                labels=["Selecione um corte"],
                startangle=90,
                colors=[self.cor_borda],
                wedgeprops={'width': 0.4},
                labeldistance=1.1
            )
            self.ax_grafico.axis('equal')

            try:
                self.fig_grafico.tight_layout(pad=1.2)
            except Exception:
                pass

            self.canvas_grafico = FigureCanvasTkAgg(self.fig_grafico, master=self.grafico_container)
            self.canvas_grafico.draw()
            self.canvas_grafico.get_tk_widget().pack(fill='both', expand=True)

            try:
                self.lbl_info_grafico = ctk.CTkLabel(
                    self.grafico_container,
                    text="Selecione um item na tabela",
                    text_color="#FF6B6B",
                    font=ctk.CTkFont(size=11)  # 🔹 fonte um pouco menor
                )
                self.lbl_info_grafico.pack(side="bottom", pady=(0, 6))
            except Exception as e:
                print(f"Erro ao criar label info: {e}")
                pass

            self.tipo_grafico = "dashboard"

        except Exception as e:
            print(f"Erro ao criar gráfico: {e}")
            fallback_label = ctk.CTkLabel(
                self.grafico_container,
                text="Gráfico não disponível\nInstale matplotlib\n\nErro: " + str(e)[:50],
                text_color="#FF6B6B",
                font=("Arial", 12)
            )
            fallback_label.pack(expand=True)

    def atualizar_grafico_dashboard(self):
        """Atualiza o gráfico principal com diagnósticos detalhados."""
        print("[Dashboard][DEBUG] atualizar_grafico_dashboard chamado")

        if not getattr(self, "grafico_container", None):
            print("[Dashboard][WARN] grafico_container não inicializado; recriando gráfico básico")
            try:
                self.criar_grafico_dashboard()
            except Exception as e:
                print(f"[Dashboard][ERRO] Falha ao recriar grafico_container: {e}")
            return

        try:
            selecao = []
            if hasattr(self, "tree_and"):
                try:
                    selecao = list(self.tree_and.selection())
                except Exception as e:
                    print(f"[Dashboard][DEBUG] Não foi possível ler seleção da tree: {e}")

            print(f"[Dashboard][DEBUG] Linhas selecionadas na tree: {len(selecao)}")

            # Como não há implementação detalhada do gráfico, refazemos o gráfico padrão
            self.criar_grafico_dashboard()

            if hasattr(self, "lbl_info_grafico"):
                texto = "Selecione um item na tabela" if not selecao else "Gráfico atualizado"
                try:
                    self.lbl_info_grafico.configure(text=texto)
                except Exception:
                    pass

        except Exception as e:
            print(f"[Dashboard][ERRO] Falha ao atualizar gráfico principal: {e}")

    def atualizar_grafico_tempo_modelo(self):
        """Mostra progresso temporal real da ordem selecionada."""
        if not getattr(self, "ax_grafico", None):
            return

        try:
            selecionados = []
            try:
                selecionados = list(self.tree_and.selection()) if hasattr(self, "tree_and") else []
            except Exception:
                pass

            if not selecionados:
                self.tipo_grafico = "dashboard"
                self.atualizar_grafico_dashboard()
                if hasattr(self, "lbl_info_grafico"):
                    self.lbl_info_grafico.configure(text="Selecione um item na tabela")
                return

            valores = self.tree_and.item(selecionados[0], "values") if hasattr(self, "tree_and") else []
            codigo = valores[0] if len(valores) > 0 else "-"
            descricao = valores[1] if len(valores) > 1 else "-"
            data_txt = valores[3] if len(valores) > 3 else ""
            dias_txt = valores[5] if len(valores) > 5 else 0
            horas_txt = valores[6] if len(valores) > 6 else 0
            origem_txt = valores[7] if len(valores) > 7 else ""

            def _to_float(v):
                try:
                    return float(str(v).replace(",", "."))
                except Exception:
                    return 0.0

            dias_estimados = _to_float(dias_txt)
            horas_estimadas = _to_float(horas_txt)

            # Se tiver horas preenchidas e o dia for apenas fração (<1),
            # usa só as horas para não duplicar o tempo.
            if horas_estimadas > 0 and dias_estimados < 1:
                total_horas = max(horas_estimadas, 0.0)
            else:
                total_horas = max((dias_estimados * 24.0) + horas_estimadas, 0.0)

            inicio = _to_datetime_any(data_txt) or datetime.now()
            agora = datetime.now()
            decorrido_horas = max((agora - inicio).total_seconds() / 3600.0, 0.0)

            self.ax_grafico.clear()

            origem_norm = str(origem_txt).strip().lower()
            if origem_norm == "cortes p/ enviar":
                wedges, texts, autotexts = self.ax_grafico.pie(
                    [1],
                    labels=["Concluído"],
                    autopct=lambda _: "100%",
                    startangle=90,
                    colors=[self.cor_sucesso],
                    wedgeprops={'width': 0.4},
                    pctdistance=1.30,
                    labeldistance=1.1
                )
                for t in texts + autotexts:
                    t.set_color(self.cor_texto)
                    t.set_fontsize(10)
                msg = f"{descricao} ({codigo}) — Corte pronto para envio"

            elif total_horas <= 0:
                self.ax_grafico.pie(
                    [1],
                    labels=["Sem estimativa"],
                    startangle=90,
                    colors=[self.cor_borda],
                    wedgeprops={'width': 0.4},
                    labeldistance=1.1
                )
                msg = "Informe dias/horas estimados para ver o progresso"

            else:
                restante_horas = max(total_horas - decorrido_horas, 0.0)

                valores_pizza = [max(decorrido_horas, 0.01)]
                labels = ["Concluído"]
                cores = [self.cor_destaque]

                if restante_horas > 0:
                    valores_pizza.append(max(restante_horas, 0.01))
                    labels.append("Restante")
                    cores.append(self.cor_borda)

                soma_valores = sum(valores_pizza)

                def _autopct(percent):
                    try:
                        valor = (percent / 100.0) * soma_valores
                        return f"{(valor / total_horas) * 100:.1f}%"
                    except Exception:
                        return f"{percent:.1f}%"

                wedges, texts, autotexts = self.ax_grafico.pie(
                    valores_pizza,
                    labels=labels,
                    autopct=_autopct,
                    startangle=90,
                    colors=cores,
                    wedgeprops={'width': 0.4},
                    pctdistance=1.35,
                    labeldistance=1.08
                )

                def _afastar_rotulos(rotulos, deslocamento=0.02):
                    for t in rotulos:
                        try:
                            x, y = t.get_position()
                            t.set_position((x, y + deslocamento))
                        except Exception:
                            continue

                for t in texts + autotexts:
                    t.set_color(self.cor_texto)
                    t.set_fontsize(10)

                _afastar_rotulos(texts, deslocamento=0.02)
                _afastar_rotulos(autotexts, deslocamento=-0.04)

                perc_concluido = (decorrido_horas / total_horas) * 100 if total_horas else 0
                perc_restante = max((restante_horas / total_horas) * 100, 0) if total_horas else 0

                # Concluído: abaixo de 1h vira minutos
                if decorrido_horas < 1:
                    if decorrido_horas <= 0:
                        decorrido_str = "0min"
                    else:
                        dec_min = int(round(decorrido_horas * 60))
                        if dec_min >= 60:
                            decorrido_str = "1h"
                        else:
                            decorrido_str = f"{dec_min}min"
                else:
                    decorrido_str = f"{decorrido_horas:.1f}h"

                # Restante: abaixo de 1h vira minutos
                if restante_horas < 1:
                    if restante_horas <= 0:
                        restante_str = "0min"
                    else:
                        rest_min = int(round(restante_horas * 60))
                        if rest_min >= 60:
                            restante_str = "1h"
                        else:
                            restante_str = f"{rest_min}min"
                else:
                    restante_str = f"{restante_horas:.1f}h"

                # 🔹 Abreviação mais curta para caber dentro do menu
                descricao_curta = descricao
                if len(descricao_curta) > 32:
                    descricao_curta = descricao_curta[:29].rstrip() + "..."

                # 🔹 Quebra em 2 linhas para não ser cortado horizontalmente
                msg = (
                    f"{descricao_curta} ({codigo})\n"
                    f"Concluído {decorrido_str} ({perc_concluido:.1f}%) | "
                    f"Restante {restante_str} ({perc_restante:.1f}%)"
                )

            self.ax_grafico.axis('equal')
            try:
                self.fig_grafico.tight_layout(pad=1.2)
            except Exception:
                pass
            self.canvas_grafico.draw()

            self.tipo_grafico = "tempo_modelo"
            if hasattr(self, "lbl_info_grafico"):
                self.lbl_info_grafico.configure(text=msg)
        except Exception as e:
            print(f"Erro ao atualizar gráfico do modelo: {e}")

    def _sort_treeview(self, tree, col, reverse):
        """Função para ordenar Treeview quando clicar no heading."""
        try:
            items = [(tree.set(item, col), item) for item in tree.get_children('')]

            try:
                items.sort(key=lambda x: float(x[0]) if x[0].replace('.', '').isdigit() else x[0], reverse=reverse)
            except:
                items.sort(key=lambda x: x[0], reverse=reverse)

            for index, (_, item) in enumerate(items):
                tree.move(item, '', index)

            tree.heading(col, command=lambda: self._sort_treeview(tree, col, not reverse))
        except Exception as e:
            print(f"Erro ao ordenar Treeview: {e}")

    # ------------------------ Métricas Simples ------------------------
    def _contar_em_andamento_db(self) -> int:
        """Conta itens em andamento - APENAS dados reais."""
        try:
            if not self.POSTGRES_DISPONIVEL:
                return 0

            rows_ordem = _fetch_all(f"SELECT COUNT(*) as cnt FROM {get_schema()}.ordem_corte_ficha")
            rows_cadastro = _fetch_all(f"SELECT COUNT(*) as cnt FROM {get_schema()}.cadastro_de_corte")
            total = (list(rows_ordem[0].values())[0] if rows_ordem else 0) + \
                    (list(rows_cadastro[0].values())[0] if rows_cadastro else 0)
            return int(total)
        except Exception:
            return 0

    def _contar_finalizados_db(self) -> int:
        """Conta itens finalizados - APENAS dados reais."""
        try:
            if not self.POSTGRES_DISPONIVEL:
                return 0

            if _table_exists_pg("cortes_finalizados"):
                row = _fetch_one(f"SELECT COUNT(*) as cnt FROM {get_schema()}.cortes_finalizados")
                if isinstance(row, dict):
                    return int(row.get("cnt", 0) or 0)
                if row:
                    return int(row[0] or 0)
            return 0
        except Exception:
            return 0

    def _sum_finalizados_periodo(self, periodo: str = "7d") -> int:
        """Soma finalizados - APENAS dados reais."""
        try:
            if not self.POSTGRES_DISPONIVEL:
                return 0

            if _table_exists_pg("cortes_finalizados"):
                rows = _fetch_all(f"SELECT COUNT(*) as cnt FROM {get_schema()}.cortes_finalizados")
                return list(rows[0].values())[0] if rows else 0
            return 0
        except Exception:
            return 0

    def _sum_pecas_finalizadas_periodo(self, periodo: str = "semana") -> int:
        """Soma peças finalizadas - APENAS dados reais."""
        try:
            if not self.POSTGRES_DISPONIVEL:
                return 0

            if _table_exists_pg("cortes_finalizados"):
                col_total = _pick_column_pg("cortes_finalizados", ["total_pecas", "quantidade", "qtd"])
                if col_total:
                    rows = _fetch_all(
                        f"SELECT COALESCE(SUM({col_total}),0) as total FROM {get_schema()}.cortes_finalizados")
                    return int(list(rows[0].values())[0] or 0)
            return 0
        except Exception:
            return 0

    def _ultimos_finalizados_from_db(self, limite: int = 3):
        """Últimos finalizados - APENAS dados reais."""
        try:
            if not self.POSTGRES_DISPONIVEL:
                return []

            if _table_exists_pg("cortes_finalizados"):
                rows = _fetch_all(f"""
                    SELECT descricao, total_pecas, data_final 
                    FROM {get_schema()}.cortes_finalizados 
                    ORDER BY data_final DESC 
                    LIMIT {limite}
                """)
                itens = []
                for row in rows:
                    data = _to_date_any(row.get('data_final')) or date.today()
                    itens.append({
                        "titulo": row.get('descricao', 'Corte'),
                        "qtd": int(row.get('total_pecas', 0)),
                        "data": data,
                        "data_str": data.strftime("%d/%m/%Y")
                    })
                return itens
            return []
        except Exception as e:
            print(f"Erro ao buscar últimos finalizados: {e}")
            return []

    # ------------------------ Cards / UI ------------------------
    def _criar_cards_resumo(self, parent_frame):
        import customtkinter as ctk
        parent_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="cards")

        def mk_card(col, titulo, lbl_attr, cor):
            card = ctk.CTkFrame(
                parent_frame, fg_color=self.cor_secundaria,
                corner_radius=10, border_width=1, border_color=self.cor_borda
            )
            card.grid(row=0, column=col, padx=6, sticky="nsew")
            ctk.CTkLabel(card, text=titulo, font=("Arial", 15, "bold"),
                         text_color=self.cor_texto).pack(pady=(10, 4))
            lbl = ctk.CTkLabel(card, text="0", font=("Arial", 28, "bold"), text_color=cor)
            lbl.pack(pady=(0, 10))
            setattr(self, lbl_attr, lbl)

        mk_card(0, "Em Andamento", "lbl_card_andamento", self.cor_destaque)
        mk_card(1, "Finalizadas (7d)", "lbl_card_finalizadas_7d", self.cor_sucesso)
        mk_card(2, "Produção Semanal", "lbl_card_prod_semanal", self.cor_destaque)
        mk_card(3, "Produção Mensal", "lbl_card_prod_mensal", self.cor_destaque)

        self.atualizar_cards_resumo()

    def _carregar_ultimos_finalizados(self, parent=None, limite: int = 3):
        import customtkinter as ctk

        # Fonte reduzida
        fonte_titulo = ctk.CTkFont(family="Arial", size=15, weight="bold")
        fonte_qtde = ctk.CTkFont(family="Arial", size=14, weight="bold")
        fonte_data = ctk.CTkFont(family="Arial", size=12)

        # Frame externo
        if parent is not None:
            self.frame_ultimos = parent
        elif not hasattr(self, "frame_ultimos") or self.frame_ultimos is None:
            self.frame_ultimos = ctk.CTkFrame(self, fg_color="transparent")
            self.frame_ultimos.pack(fill="x", pady=(4, 0))

        # Limpa
        for w in self.frame_ultimos.winfo_children():
            w.destroy()

        # Título compacto
        titulo = ctk.CTkLabel(
            self.frame_ultimos,
            text="ÚLTIMOS FINALIZADOS",
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            text_color=self.cor_texto
        )
        titulo.pack(anchor="w", padx=10, pady=(0, 4))

        row = ctk.CTkFrame(self.frame_ultimos, fg_color="transparent")
        row.pack(fill="x", padx=8)

        # Dados do banco
        dados = self._ultimos_finalizados_from_db(limite=limite)
        while len(dados) < 3:
            dados.append({"titulo": "-", "qtd": 0, "data_str": "-"})

        # Criação dos cards
        for i, it in enumerate(dados[:3]):
            card = ctk.CTkFrame(
                row,
                fg_color=self.cor_secundaria,
                corner_radius=10,
                border_width=1,
                border_color=self.cor_borda,
                height=76  # <<<<< ALTURA REDUZIDA
            )
            card.grid(row=0, column=i, sticky="nsew", padx=8, pady=4)

            # Não deixar aumentar de tamanho
            card.pack_propagate(False)

            # Título
            ctk.CTkLabel(
                card, text=it["titulo"],
                font=fonte_titulo,
                text_color=self.cor_texto
            ).pack(pady=(8, 2))

            # Quantidade
            ctk.CTkLabel(
                card, text=f"Qtde: {it['qtd']}",
                font=fonte_qtde,
                text_color="#40A9FF"
            ).pack(pady=(0, 2))

            # Data
            ctk.CTkLabel(
                card, text=it["data_str"],
                font=fonte_data,
                text_color=self.cor_texto
            ).pack(pady=(0, 4))

            row.grid_columnconfigure(i, weight=1)

    # ------------------------ Auto-refresh ------------------------
    def _setup_auto_refresh(self):
        try:
            self.after(5000, self._poll_refresh_token)
        except Exception:
            pass

    def _refresh_debounced(self, ms: int = 500):
        try:
            if getattr(self, "_refresh_after_id", None):
                self.after_cancel(self._refresh_after_id)
        except Exception:
            pass
        self._refresh_after_id = self.after(ms, self.atualizar_dashboard)

    def _poll_refresh_token(self):
        try:
            if hasattr(self, 'lbl_card_andamento'):
                self.atualizar_cards_resumo()
        except Exception:
            pass
        finally:
            try:
                self.after(5000, self._poll_refresh_token)
            except Exception:
                pass

    # ------------------------ Atualização geral ------------------------
    def atualizar_cards_resumo(self):
        try:
            self.lbl_card_andamento.configure(text=str(self._contar_em_andamento_db()))
        except Exception as e:
            print(f"Erro card andamento: {e}")

        try:
            self.lbl_card_finalizadas_7d.configure(text=str(self._sum_finalizados_periodo("7d")))
        except Exception as e:
            print(f"Erro card finalizadas: {e}")

        try:
            self.lbl_card_prod_semanal.configure(text=str(self._sum_pecas_finalizadas_periodo("semana")))
        except Exception as e:
            print(f"Erro card produção semanal: {e}")

        try:
            self.lbl_card_prod_mensal.configure(text=str(self._sum_pecas_finalizadas_periodo("mes")))
        except Exception as e:
            print(f"Erro card produção mensal: {e}")

    def atualizar_dashboard(self):
        try:
            self.atualizar_cards_resumo()
            self._preencher_tabela_andamento()
            self._atualizar_tabela_estoque()
            if getattr(self, "tipo_grafico", "dashboard") == "dashboard":
                self.atualizar_grafico_dashboard()
            self._carregar_ultimos_finalizados(limite=3)
        except Exception as e:
            print(f"Erro ao atualizar dashboard: {e}")

    def on_show(self):
        self.atualizar_dashboard()

    def _verificar_tabelas(self):
        """Verifica se as tabelas necessárias existem no banco."""
        if not self.POSTGRES_DISPONIVEL:
            return

        tabelas = ["ordem_corte_ficha", "cadastro_de_corte", "cortes_finalizados"]

        for tabela in tabelas:
            if _table_exists_pg(tabela):
                print(f"✅ Tabela {tabela} existe")
            else:
                print(f"❌ Tabela {tabela} NÃO existe")

    def _aplicar_estilo_treeviews(self):
        """
        Estilo das Treeviews do Dashboard:
        - Cabeçalho SEMPRE com fundo escuro e texto claro.
        - Linhas com bom contraste em tema claro/escuro.
        - Seleção com fundo forte e texto claro (visível em tema claro).
        """
        try:
            style = ttk.Style()

            # -------- CABEÇALHO (TÍTULOS) – FUNDO ESCURO / LETRAS CLARAS --------
            cab_bg = self.cor_cabecalho_fundo  # já definido no __init__ (#2C3E50)
            cab_fg = self.cor_cabecalho_texto  # já definido no __init__ (#FFFFFF)

            # -------- CORPO DA TABELA (LINHAS) --------
            if is_dark_color(self.cor_fundo):
                linhas_bg = "#111827"  # bem escuro
                linhas_fg = "#E5E7EB"  # bem claro
            else:
                linhas_bg = self.cor_linhas_fundo  # normalmente #FFFFFF
                linhas_fg = self.cor_linhas_texto  # normalmente #000000

            # Cor da seleção (linha marcada)
            selecao_bg = ajustar_hover(self.cor_destaque)
            selecao_fg = get_contraste_texto(selecao_bg)

            aplicar_estilo_treeview(
                style=style,
                prefixo="OperaDashboard.Treeview",
                cor_fundo=self.cor_fundo,
                cor_linhas=linhas_bg,
                cor_cabecalho=cab_bg,
                cor_texto=linhas_fg,
                cor_borda=self.cor_borda,
                cor_selecao=selecao_bg,
                altura_linha=22,
            )

            # Aplica o estilo específico nas Treeviews do dashboard
            for tree in (getattr(self, "tree_est", None),
                         getattr(self, "tree_and", None)):
                if tree is not None:
                    tree.configure(style="OperaDashboard.Treeview")
                    aplicar_tags_alternadas(tree, linhas_bg, self.cor_fundo)

        except Exception as e:
            print(f"⚠️ Erro ao aplicar estilo nas Treeviews do Dashboard: {e}")


# ===================== Teste isolado =====================

if __name__ == "__main__":
    # Sistema básico apenas com cores
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

        dados_producao = {"em_andamento": [], "finalizados": [],
                          "metas": {"semanal": 0, "atingido_semanal": 0,
                                    "mensal": 0, "atingido_mensal": 0}}
        departamentos = ["Corte", "Facção", "Bordado", "Caseador",
                         "Botões", "Estamparia", "Tingimento", "Acabamento"]


    import customtkinter as ctk

    try:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
    except Exception:
        pass

    root = ctk.CTk()

    # Título baseado na conexão
    if POSTGRES_DISPONIVEL:
        root.title("Dashboard - Conectado ao PostgreSQL")
        print("=" * 50)
        print("✅ DASHBOARD - MODO CONECTADO")
        print("=" * 50)

        # Verificar tabelas existentes
        tabelas_verificar = ["ordem_corte_ficha", "cadastro_de_corte", "cortes_finalizados", "estoque_tecidos"]
        for tabela in tabelas_verificar:
            if _table_exists_pg(tabela):
                try:
                    count_sql = f"SELECT COUNT(*) as cnt FROM {get_schema()}.{tabela}"
                    count_result = _fetch_one(count_sql)
                    count = list(count_result.values())[0] if count_result else 0
                    print(f"📊 {tabela}: {count} registros")
                except Exception as e:
                    print(f"📊 {tabela}: existe (erro ao contar: {e})")
            else:
                print(f"❌ {tabela}: NÃO existe")

        print("=" * 50)
    else:
        root.title("Dashboard - Banco de Dados Indisponível")
        print("=" * 50)
        print("❌ DASHBOARD - BANCO DE DADOS INDISPONÍVEL")
        print("ℹ️  Conecte ao PostgreSQL para ver dados reais")
        print("=" * 50)

    root.geometry("1200x800")

    page = DashboardPage(root, sistema=SistemaBasico())
    page.pack(fill="both", expand=True)


    # Função para atualizar com F5
    def atualizar_com_f5(event):
        print("🔄 Atualizando dashboard via F5...")
        page.atualizar_dashboard()


    root.bind('<F5>', atualizar_com_f5)

    if POSTGRES_DISPONIVEL:
        print("💡 Pressione F5 para atualizar o dashboard")
    else:
        print("💡 Conecte ao PostgreSQL e pressione F5 para atualizar")


    def on_closing():
        print("👋 Fechando dashboard...")
        root.destroy()


    root.protocol("WM_DELETE_WINDOW", on_closing)

    try:
        if POSTGRES_DISPONIVEL:
            page.atualizar_dashboard()
        else:
            aviso_frame = ctk.CTkFrame(root, fg_color="#f59e0b", corner_radius=8)
            aviso_frame.pack(pady=20, padx=20, fill="x")

            aviso_label = ctk.CTkLabel(
                aviso_frame,
                text="❌ BANCO DE DADOS INDISPONÍVEL\nConecte ao PostgreSQL para ver dados reais",
                text_color="#000000",
                font=("Arial", 16, "bold"),
                justify="center"
            )
            aviso_label.pack(pady=20)

        root.mainloop()

    except KeyboardInterrupt:
        print("🛑 Dashboard interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao executar dashboard: {e}")
        import traceback

        traceback.print_exc()

#15/12/2025
