# -*- coding: utf-8 -*-
import TEMAS
import customtkinter as ctk
from tkinter import messagebox, filedialog
from tkinter import ttk
from datetime import datetime
import os
import sys
import subprocess

# ---- Banco de dados (PostgreSQL) ----
# Import do módulo PG com fallback por caminho
try:
    import BANCO_DE_DADOS_PG as db  # exige OPERA_PG_DSN e OPERA_PG_SCHEMA
except ModuleNotFoundError:
    import importlib.util

    CANDIDATES = [
        os.path.join(os.path.dirname(__file__), "BANCO_DE_DADOS_PG.py"),
        os.path.join(os.path.dirname(__file__), "..", "BANCO_DE_DADOS_PG.py"),
        r"C:\Users\User\Desktop\sistema\SISTEMA\BANCO_DE_DADOS_PG.py",
    ]
    db = None
    for _p in CANDIDATES:
        if os.path.isfile(_p):
            _spec = importlib.util.spec_from_file_location("BANCO_DE_DADOS_PG", _p)
            db = importlib.util.module_from_spec(_spec)
            sys.modules["BANCO_DE_DADOS_PG"] = db
            _spec.loader.exec_module(db)
            break
    if db is None:
        raise

# Helpers PG


# ---- ReportLab (impressão PDF) ----
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib import colors


class PagamentoAdiantamentoPage(ctk.CTkFrame):
    def __init__(self, parent, sistema=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.sistema = sistema
        self._apply_palette()

        # Verifica banco
        if not db.ready_check():
            msg = "Não foi possível conectar ao banco de dados."
            messagebox.showerror(
                "Banco não preparado",
                msg + "\n\nVerifique OPERA_PG_DSN/OPERA_PG_SCHEMA e rode os scripts."
            )
            raise SystemExit(1)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self,
            text="CONTROLE DE ADIANTAMENTOS PARA FACÇÕES",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.C("cor_texto"),
            anchor="w"
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)

        # --- busca ---
        search_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # --- filtros de busca ---
        ctk.CTkLabel(search_frame, text="Tipo:", text_color=self.C("cor_texto")
                     ).pack(side="left", padx=(0, 6))

        self.tipo_busca_var = ctk.StringVar(value="Todos")
        self.combo_tipo_busca = ctk.CTkComboBox(
            search_frame,
            variable=self.tipo_busca_var,
            values=["Todos"],
            width=140,
            command=lambda _v=None: self._on_tipo_busca_changed(),
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            button_color=self.C("cor_primaria"),
            button_hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            dropdown_fg_color=self.C("cor_secundaria"),
            dropdown_hover_color=self.C("cor_hover"),
            dropdown_text_color=self.C("cor_texto")
        )
        self.combo_tipo_busca.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(search_frame, text="Prestador:", text_color=self.C("cor_texto")
                     ).pack(side="left", padx=(0, 6))

        self.prestador_busca_var = ctk.StringVar(value="")
        self.combo_prestador_busca = ctk.CTkComboBox(
            search_frame,
            variable=self.prestador_busca_var,
            values=[""],
            width=220,
            command=lambda _v=None: None,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            button_color=self.C("cor_primaria"),
            button_hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            dropdown_fg_color=self.C("cor_secundaria"),
            dropdown_hover_color=self.C("cor_hover"),
            dropdown_text_color=self.C("cor_texto")
        )
        self.combo_prestador_busca.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(search_frame, text="Busca:", text_color=self.C("cor_texto")
                     ).pack(side="left", padx=(0, 6))

        # Mantém o mesmo nome para reaproveitar a lógica já existente
        self.entry_codigo_modelo = ctk.CTkEntry(
            search_frame, width=200,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto"),
            placeholder_text="Código/ordem/descrição..."
        )
        self.entry_codigo_modelo.pack(side="left", padx=(0, 10))
        self.entry_codigo_modelo.bind("<Return>", lambda e: self.buscar_cortes())

        btn_buscar = ctk.CTkButton(
            search_frame, text="Buscar", command=self.buscar_cortes, width=90,
            fg_color=self.C("cor_destaque"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        btn_buscar.pack(side="left")

        # --- tabela ---
        self.tree_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.tree_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        self.tree_cortes = ttk.Treeview(
            self.tree_frame,
            columns=("ID", "Código", "Prestador", "Tipo", "Serviço", "Status", "Data Envio", "Qtd Peças"),
            show="headings",
            height=6
        )
        self.tree_cortes.grid(row=0, column=0, sticky="nsew")
        for col, width, anchor in [
            ("ID", 80, "center"),
            ("Código", 110, "center"),
            ("Prestador", 220, "w"),
            ("Tipo", 110, "center"),
            ("Serviço", 140, "w"),
            ("Status", 110, "center"),
            ("Data Envio", 130, "center"),
            ("Qtd Peças", 90, "center"),
        ]:
            self.tree_cortes.heading(col, text=col)
            self.tree_cortes.column(col, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree_cortes.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree_cortes.configure(yscrollcommand=scrollbar.set)
        self.tree_cortes.bind("<Double-1>", self.selecionar_corte)

        # --- adiantamento ---
        adiantamento_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        adiantamento_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(adiantamento_frame, text="DADOS DO ADIANTAMENTO",
                     font=ctk.CTkFont(weight="bold"), text_color=self.C("cor_texto")
                     ).grid(row=0, column=0, columnspan=4, pady=(0, 10), sticky="w")

        ctk.CTkLabel(adiantamento_frame, text="Tipo Prestador:", text_color=self.C("cor_texto")
                     ).grid(row=1, column=0, sticky="e", padx=5, pady=2)

        self.tipo_form_var = ctk.StringVar(value="Todos")
        self.combo_tipo_form = ctk.CTkComboBox(
            adiantamento_frame,
            variable=self.tipo_form_var,
            values=["Todos"],
            width=150,
            command=lambda _v=None: self._on_tipo_form_changed(),
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            button_color=self.C("cor_primaria"),
            button_hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            dropdown_fg_color=self.C("cor_secundaria"),
            dropdown_hover_color=self.C("cor_hover"),
            dropdown_text_color=self.C("cor_texto")
        )
        self.combo_tipo_form.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        ctk.CTkLabel(adiantamento_frame, text="Costureira/Prestador:", text_color=self.C("cor_texto")
                     ).grid(row=1, column=2, sticky="e", padx=5, pady=2)

        self.prestador_form_var = ctk.StringVar(value="")
        self.combo_prestador_form = ctk.CTkComboBox(
            adiantamento_frame,
            variable=self.prestador_form_var,
            values=[""],
            width=250,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            button_color=self.C("cor_primaria"),
            button_hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            dropdown_fg_color=self.C("cor_secundaria"),
            dropdown_hover_color=self.C("cor_hover"),
            dropdown_text_color=self.C("cor_texto")
        )
        self.combo_prestador_form.grid(row=1, column=3, sticky="w", padx=5, pady=2)

        ctk.CTkLabel(adiantamento_frame, text="Código do Modelo:", text_color=self.C("cor_texto")
                     ).grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.entry_codigo_modelo_selecionado = ctk.CTkEntry(
            adiantamento_frame, width=150, state="disabled",
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.entry_codigo_modelo_selecionado.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        ctk.CTkLabel(adiantamento_frame, text="Descrição:", text_color=self.C("cor_texto")
                     ).grid(row=3, column=0, sticky="e", padx=5, pady=2)
        self.entry_descricao_modelo = ctk.CTkEntry(
            adiantamento_frame, width=250, state="disabled",
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.entry_descricao_modelo.grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=2)

        ctk.CTkLabel(adiantamento_frame, text="Valor (R$):", text_color=self.C("cor_texto")
                     ).grid(row=4, column=0, sticky="e", padx=5, pady=2)
        self.entry_valor = ctk.CTkEntry(
            adiantamento_frame, width=150,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.entry_valor.grid(row=4, column=1, sticky="w", padx=5, pady=2)

        ctk.CTkLabel(adiantamento_frame, text="Forma de Pagamento:", text_color=self.C("cor_texto")
                     ).grid(row=5, column=0, sticky="e", padx=5, pady=2)
        self.pagamento_var = ctk.StringVar(value="À Vista")
        self.combo_pagamento = ctk.CTkComboBox(
            adiantamento_frame,
            variable=self.pagamento_var,
            values=["À Vista", "Parcelado"],
            width=150,
            command=self.atualizar_visibilidade_parcelas,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            button_color=self.C("cor_primaria"),
            button_hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            dropdown_fg_color=self.C("cor_secundaria"),
            dropdown_hover_color=self.C("cor_hover"),
            dropdown_text_color=self.C("cor_texto")
        )
        self.combo_pagamento.grid(row=5, column=1, sticky="w", padx=5, pady=2)

        self.label_parcelas = ctk.CTkLabel(adiantamento_frame, text="Nº Parcelas:", text_color=self.C("cor_texto"))
        self.entry_parcelas = ctk.CTkEntry(
            adiantamento_frame, width=50,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.entry_parcelas.insert(0, "1")

        ctk.CTkLabel(adiantamento_frame, text="Data/Hora:", text_color=self.C("cor_texto")
                     ).grid(row=7, column=0, sticky="e", padx=5, pady=2)
        self.label_data = ctk.CTkLabel(
            adiantamento_frame, text=datetime.now().strftime("%d/%m/%Y %H:%M"),
            text_color=self.C("cor_texto")
        )
        self.label_data.grid(row=7, column=1, sticky="w", padx=5, pady=2)

        # --- botões ---
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="e", pady=(10, 0))

        self.btn_imprimir = ctk.CTkButton(
            btn_frame, text="Imprimir Comprovante",
            command=self.imprimir_comprovante, width=150, state="disabled",
            fg_color=self.C("cor_imprimir"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_imprimir.pack(side="left", padx=5)

        self.btn_salvar = ctk.CTkButton(
            btn_frame, text="Registrar Adiantamento",
            command=self.registrar_adiantamento, width=180, state="disabled",
            fg_color=self.C("cor_adicionar"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_salvar.pack(side="left", padx=5)

        self.btn_limpar = ctk.CTkButton(
            btn_frame, text="Limpar",
            command=self.limpar_campos, width=80,
            fg_color=self.C("cor_secundaria"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_limpar.pack(side="left", padx=5)

        # Carrega tipos/prestadores para busca e formulário (facção, bordado, etc.)
        self._init_prestadores_ui()

        self.atualizar_data_hora()

        try:
            if self.sistema and hasattr(self.sistema, "_aplicar_tema_global"):
                self.sistema._aplicar_tema_global()
        except Exception:
            pass

    # ---------- tema ----------
    def C(self, nome, default=None):
        if self.sistema and hasattr(self.sistema, nome):
            return getattr(self.sistema, nome)
        defaults = {
            "cor_fundo": "#181818",
            "cor_primaria": "#121212",
            "cor_secundaria": "#1F1F1F",
            "cor_texto": "#EEEEEE",
            "cor_hover": "#2C2C2C",
            "cor_borda": "#3A3A3A",
            "cor_destaque": "#BB86FC",
            "cor_sucesso": "#03DAC6",
            "cor_alerta": "#CF6679",
            "cor_adicionar": "#03DAC6",
            "cor_imprimir": "#CF6679",
        }
        return defaults.get(nome, default)

    def _apply_palette(self):
        self.configure(fg_color=self.C("cor_fundo"))

    def _pg_exec(self, sql: str, params=None) -> int:
        """Wrapper para db.execute mantendo compatibilidade"""
        return db.execute(sql, params)

    # ---------- prestadores (facção / costureira / bordado etc.) ----------

    def _db_has_column(self, table_qualified: str, column: str) -> bool:
        """Checa se uma coluna existe (evita quebrar quando o schema muda)."""
        try:
            schema = "public"
            table = table_qualified
            if "." in table_qualified:
                schema, table = table_qualified.split(".", 1)
            r = db.fetch_one(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s AND column_name = %s
                LIMIT 1
                """,
                (schema, table, column)
            )
            return bool(r)
        except Exception:
            # se falhar, assume que não existe (mantém compatibilidade)
            return False

    def _db_has_table(self, table_qualified: str) -> bool:
        """Checa se uma tabela existe no schema informado."""
        try:
            schema = "public"
            table = table_qualified
            if "." in table_qualified:
                schema, table = table_qualified.split(".", 1)
            r = db.fetch_one(
                """
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = %s AND table_name = %s
                 LIMIT 1
                """,
                (schema, table),
            )
            return bool(r)
        except Exception:
            return False

    def _db_columns(self, table_qualified: str) -> set[str]:
        """Retorna o conjunto de colunas existentes numa tabela."""
        try:
            schema = "public"
            table = table_qualified
            if "." in table_qualified:
                schema, table = table_qualified.split(".", 1)
            rows = db.fetch_all(
                """
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = %s AND table_name = %s
                """,
                (schema, table),
            )
            return {r.get("column_name") for r in (rows or []) if r.get("column_name")}
        except Exception:
            return set()

    def _load_tipos_prestador(self):
        """Carrega os tipos cadastrados em opera.cadastro_faccoes (tipo_prestador)."""
        tipos = ["Todos"]
        try:
            # tenta schema opera
            has_tipo = self._db_has_column("opera.cadastro_faccoes", "tipo_prestador")
            if has_tipo:
                rows = db.fetch_all(
                    "SELECT DISTINCT tipo_prestador AS t FROM opera.cadastro_faccoes "
                    "WHERE COALESCE(ativo, TRUE) = TRUE AND COALESCE(tipo_prestador,'') <> '' "
                    "ORDER BY 1"
                )
                for r in rows or []:
                    t = (r.get("t") or "").strip()
                    if t and t not in tipos:
                        tipos.append(t)
        except Exception:
            pass

        # fallback mínimo (caso tabela não tenha a coluna ou esteja vazia)
        if len(tipos) == 1:
            tipos += ["Faccao", "Bordado", "Lavanderia", "Passadoria", "Corte", "Acabamento"]

        return tipos

    def _load_prestadores(self, tipo: str):
        """Carrega nomes de prestadores por tipo (ou todos) e mantém um mapa nome->id."""
        tipo = (tipo or "Todos").strip()
        nomes = [""]  # permite “vazio”

        # mapa global (evita depender de JOIN por nome em outras telas)
        if not hasattr(self, "_prestador_id_by_nome"):
            self._prestador_id_by_nome = {}

        try:
            has_tipo = self._db_has_column("opera.cadastro_faccoes", "tipo_prestador")
            has_ativo = self._db_has_column("opera.cadastro_faccoes", "ativo")

            where = []
            params = []

            if has_ativo:
                where.append("COALESCE(ativo, TRUE) = TRUE")

            if tipo and tipo != "Todos" and has_tipo:
                where.append("tipo_prestador = %s")
                params.append(tipo)

            where_sql = ("WHERE " + " AND ".join(where)) if where else ""
            rows = db.fetch_all(
                f"SELECT id, nome FROM opera.cadastro_faccoes {where_sql} ORDER BY nome",
                tuple(params) if params else None
            )

            for r in rows or []:
                n = (r.get("nome") or "").strip()
                pid = r.get("id")
                if n:
                    nomes.append(n)
                    if pid is not None:
                        self._prestador_id_by_nome[n] = pid
        except Exception:
            pass

        return nomes

    def _init_prestadores_ui(self):
        """Inicializa os combos de tipo/prestador (busca e formulário)."""
        tipos = self._load_tipos_prestador()

        try:
            self.combo_tipo_busca.configure(values=tipos)
        except Exception:
            pass
        try:
            self.combo_tipo_form.configure(values=tipos)
        except Exception:
            pass

        # Carrega prestadores iniciais (Todos)
        self._on_tipo_busca_changed()
        self._on_tipo_form_changed()

    def _on_tipo_busca_changed(self):
        tipo = (self.tipo_busca_var.get() or "Todos").strip()
        nomes = self._load_prestadores(tipo)
        try:
            self.combo_prestador_busca.configure(values=nomes)
        except Exception:
            pass
        # se o valor atual não existir mais, limpa
        try:
            if self.prestador_busca_var.get() not in nomes:
                self.prestador_busca_var.set("")
        except Exception:
            pass

    def _on_tipo_form_changed(self):
        tipo = (self.tipo_form_var.get() or "Todos").strip()
        nomes = self._load_prestadores(tipo)
        try:
            self.combo_prestador_form.configure(values=nomes)
        except Exception:
            pass
        try:
            if self.prestador_form_var.get() not in nomes:
                self.prestador_form_var.set("")
        except Exception:
            pass

    # ---------- dados (PostgreSQL) ----------

    def buscar_cortes(self):
        """
        Busca SERVIÇOS do prestador (o que ele fez / está fazendo).
        Fonte correta: opera.envios_cortes (liga pelo prestador_id).
        """
        termo = (self.entry_codigo_modelo.get() or "").strip()
        tipo = (getattr(self, "tipo_busca_var", None).get() if hasattr(self, "tipo_busca_var") else "Todos") or "Todos"
        tipo = (tipo or "Todos").strip()
        prestador_nome = (getattr(self, "prestador_busca_var", None).get() if hasattr(self,
                                                                                      "prestador_busca_var") else "") or ""
        prestador_nome = prestador_nome.strip()

        where_parts = []
        params = []

        prestador_id = None
        try:
            prestador_id = getattr(self, "_prestador_id_by_nome", {}).get(prestador_nome) if prestador_nome else None
        except Exception:
            prestador_id = None

        if prestador_id is not None:
            where_parts.append("e.prestador_id = %s")
            params.append(prestador_id)
        elif prestador_nome:
            where_parts.append("COALESCE(cf.nome,'') ILIKE %s")
            params.append(f"%{prestador_nome}%")

        if termo:
            like = f"%{termo}%"
            where_parts.append(
                "(COALESCE(e.codigo_corte,'') ILIKE %s OR "
                "COALESCE(e.ordem_corte,'') ILIKE %s OR "
                "COALESCE(e.descricao_corte,'') ILIKE %s OR "
                "COALESCE(e.tipo_servico,'') ILIKE %s)"
            )
            params += [like, like, like, like]

        if tipo and tipo != "Todos" and self._db_has_column("opera.cadastro_faccoes", "tipo_prestador"):
            where_parts.append("COALESCE(cf.tipo_prestador,'') = %s")
            params.append(tipo)

        where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        sql = f"""
                SELECT
                    e.corte_id,
                    e.codigo_corte,
                    COALESCE(cf.nome,'') AS prestador,
                    COALESCE(cf.tipo_prestador,'') AS tipo,
                    COALESCE(e.tipo_servico,'') AS servico,
                    CASE
                        WHEN r.id IS NOT NULL THEN 'Retornado'
                        WHEN COALESCE(e.status_envio,'') <> '' THEN e.status_envio
                        ELSE 'Em andamento'
                    END AS status,
                    e.data_envio,
                    COALESCE(e.total_pecas, 0) AS qtd_pecas
                FROM opera.envios_cortes e
                LEFT JOIN opera.cadastro_faccoes cf ON cf.id = e.prestador_id
                LEFT JOIN opera.controle_retorno_cortes r ON r.envio_id = e.id
                {where_sql}
                ORDER BY e.data_envio DESC NULLS LAST, e.id DESC
                LIMIT 500
            """

        try:
            rows = []
            rows_envios = db.fetch_all(sql, tuple(params) if params else None)
            for r in rows_envios or []:
                codigo_corte = r.get("codigo_corte")
                if isinstance(codigo_corte, (int, float)) or (
                        isinstance(codigo_corte, str) and str(codigo_corte).isdigit()):
                    codigo_corte = str(codigo_corte).zfill(4)

                rows.append((
                    r.get("corte_id"),
                    codigo_corte,
                    r.get("prestador") or "",
                    r.get("tipo") or "",
                    r.get("servico") or "",
                    r.get("status") or "",
                    r.get("data_envio"),
                    r.get("qtd_pecas"),
                ))

            if self._db_has_table("opera.cortes_finalizados"):
                cols_cf = self._db_columns("opera.cortes_finalizados")
                corte_id_expr = "cf.corte_id" if "corte_id" in cols_cf else "cf.id"
                codigo_expr = "cf.codigo" if "codigo" in cols_cf else (
                    "cf.codigo_corte" if "codigo_corte" in cols_cf else "''"
                )
                desc_expr = "cf.descricao" if "descricao" in cols_cf else (
                    "cf.descricao_corte" if "descricao_corte" in cols_cf else "''"
                )
                prest_expr = "cf.costureira" if "costureira" in cols_cf else (
                    "cf.destino" if "destino" in cols_cf else "''"
                )
                tipo_expr = "cf.tipo_servico" if "tipo_servico" in cols_cf else (
                    "cf.servico" if "servico" in cols_cf else "''"
                )
                envio_expr = "cf.data_envio" if "data_envio" in cols_cf else (
                    "cf.data_saida" if "data_saida" in cols_cf else "NULL"
                )

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
                prestador_nome_expr = prest_expr
                tipo_prestador_expr = "''"
                prestador_id_col = None
                for col in ("prestador_id", "faccao_id", "costureira_id"):
                    if col in cols_cf:
                        prestador_id_col = col
                        break

                if prestador_id_col and self._db_has_table("opera.cadastro_faccoes"):
                    join_sql = "LEFT JOIN opera.cadastro_faccoes cfacc ON cfacc.id = cf." + prestador_id_col
                    prestador_nome_expr = "COALESCE(cfacc.nome, '')"
                    if self._db_has_column("opera.cadastro_faccoes", "tipo_prestador"):
                        tipo_prestador_expr = "COALESCE(cfacc.tipo_prestador, '')"

                where_parts_cf = []
                params_cf = []

                if prestador_id is not None and prestador_id_col:
                    where_parts_cf.append(f"cf.{prestador_id_col} = %s")
                    params_cf.append(prestador_id)
                elif prestador_nome:
                    where_parts_cf.append(f"{prestador_nome_expr} ILIKE %s")
                    params_cf.append(f"%{prestador_nome}%")

                if termo:
                    like = f"%{termo}%"
                    where_parts_cf.append(
                        f"({codigo_expr} ILIKE %s OR {desc_expr} ILIKE %s OR {tipo_expr} ILIKE %s)"
                    )
                    params_cf += [like, like, like]

                if tipo and tipo != "Todos" and tipo_prestador_expr != "''":
                    where_parts_cf.append(f"{tipo_prestador_expr} = %s")
                    params_cf.append(tipo)

                where_sql_cf = ("WHERE " + " AND ".join(where_parts_cf)) if where_parts_cf else ""

                sql_cf = f"""
                    SELECT
                        {corte_id_expr} AS corte_id,
                        {codigo_expr} AS codigo_corte,
                        {prestador_nome_expr} AS prestador,
                        {tipo_prestador_expr} AS tipo,
                        {tipo_expr} AS servico,
                        'Finalizado' AS status,
                        {envio_expr} AS data_envio,
                        ({total_qtd_expr}) AS qtd_pecas
                      FROM opera.cortes_finalizados cf
                      {join_sql}
                      {where_sql_cf}
                  ORDER BY cf.id DESC
                     LIMIT 300
                """

                rows_finalizados = db.fetch_all(sql_cf, tuple(params_cf) if params_cf else None)
                for r in rows_finalizados or []:
                    codigo_corte = r.get("codigo_corte")
                    if isinstance(codigo_corte, (int, float)) or (
                            isinstance(codigo_corte, str) and str(codigo_corte).isdigit()):
                        codigo_corte = str(codigo_corte).zfill(4)

                    rows.append((
                        r.get("corte_id"),
                        codigo_corte,
                        r.get("prestador") or "",
                        r.get("tipo") or "",
                        r.get("servico") or "",
                        r.get("status") or "",
                        r.get("data_envio"),
                        r.get("qtd_pecas") or 0,
                    ))

            for item in self.tree_cortes.get_children():
                self.tree_cortes.delete(item)

            for new_row in rows:
                self.tree_cortes.insert("", "end", values=new_row)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao buscar serviços:\n{e}")

    def buscar_descricao_modelo(self, codigo_modelo):
        desc = ""
        try:
            q1 = db.fetch_one(
                "SELECT descricao_modelo AS d FROM ordem_corte_ficha WHERE TRIM(codigo_modelo)=TRIM(%s) LIMIT 1",
                (codigo_modelo,)
            )

            if q1 and q1.get("d"):
                return q1["d"]
            q2 = db.fetch_one(
                "SELECT descricao AS d FROM cadastro_de_corte WHERE TRIM(codigo)=TRIM(%s) LIMIT 1",
                (codigo_modelo,)
            )

            if q2 and q2.get("d"):
                return q2["d"]
            q3 = db.fetch_one(
                "SELECT descricao AS d FROM cadastro_modelos_cabecalho WHERE TRIM(codigo)=TRIM(%s) LIMIT 1",
                (codigo_modelo,)
            )

            if q3 and q3.get("d"):
                return q3["d"]
        except Exception:
            pass
        return desc or "Descrição não encontrada"

    def obter_descricao_corte(self, corte_id, codigo_modelo):
        try:
            r = db.fetch_one(
                "SELECT descricao_corte AS d FROM controle_envio_cortes "
                "WHERE corte_id = %s AND TRIM(codigo_corte)=TRIM(%s) LIMIT 1",
                (corte_id, codigo_modelo)
            )

            if r and r.get("d"):
                return r["d"]
        except Exception:
            pass
        return ""

    def selecionar_corte(self, event):
        selected_item = self.tree_cortes.focus()
        if not selected_item:
            return
        corte_data = self.tree_cortes.item(selected_item)['values']
        if not corte_data or len(corte_data) < 3:
            return

        corte_id = corte_data[0]
        codigo = str(corte_data[1])
        if codigo.isdigit():
            codigo = codigo.zfill(4)

        self.entry_codigo_modelo.delete(0, "end")
        self.entry_codigo_modelo.insert(0, codigo)

        # Preenche prestador/tipo (quando disponível)
        try:
            prestador = corte_data[2] if len(corte_data) > 2 else ""
            tipo = corte_data[3] if len(corte_data) > 3 else "Todos"

            if prestador is None:
                prestador = ""
            if tipo is None or str(tipo).strip() == "":
                tipo = "Todos"

            # combos do formulário
            try:
                self.tipo_form_var.set(str(tipo))
            except Exception:
                pass
            try:
                self.prestador_form_var.set(str(prestador))
            except Exception:
                pass

            # combos da busca (facilita “achar os cortes delas”)
            try:
                self.tipo_busca_var.set(str(tipo))
            except Exception:
                pass
            try:
                self.prestador_busca_var.set(str(prestador))
            except Exception:
                pass
        except Exception:
            pass

        try:
            self.entry_codigo_modelo_selecionado.configure(state="normal")
            self.entry_codigo_modelo_selecionado.delete(0, "end")
            self.entry_codigo_modelo_selecionado.insert(0, codigo)
            self.entry_codigo_modelo_selecionado.configure(state="disabled")
        except Exception:
            pass

        descricao = self.obter_descricao_corte(corte_id, codigo) or self.buscar_descricao_modelo(codigo)
        try:
            self.entry_descricao_modelo.configure(state="normal")
            self.entry_descricao_modelo.delete(0, "end")
            self.entry_descricao_modelo.insert(0, descricao)
            self.entry_descricao_modelo.configure(state="disabled")
        except Exception:
            pass

        self.entry_valor.delete(0, "end")
        self.pagamento_var.set("À Vista")
        self.entry_parcelas.delete(0, "end")
        self.entry_parcelas.insert(0, "1")
        self.atualizar_visibilidade_parcelas()

        try:
            self.btn_imprimir.configure(state="normal")
        except Exception:
            pass
        try:
            self.btn_salvar.configure(state="normal")
        except Exception:
            pass

    def atualizar_visibilidade_parcelas(self, event=None):
        if self.pagamento_var.get() == "Parcelado":
            self.label_parcelas.grid(row=6, column=0, sticky="e", padx=5, pady=2)
            self.entry_parcelas.grid(row=6, column=1, sticky="w", padx=5, pady=2)
        else:
            self.label_parcelas.grid_forget()
            self.entry_parcelas.grid_forget()

    def limpar_campos(self):
        self.entry_codigo_modelo.delete(0, "end")
        # limpa filtros/seleções de prestador
        try:
            self.tipo_busca_var.set("Todos")
        except Exception:
            pass
        try:
            self.prestador_busca_var.set("")
        except Exception:
            pass
        try:
            self.tipo_form_var.set("Todos")
        except Exception:
            pass
        try:
            self.prestador_form_var.set("")
        except Exception:
            pass
        self.entry_codigo_modelo_selecionado.configure(state="normal")
        self.entry_codigo_modelo_selecionado.delete(0, "end")
        self.entry_codigo_modelo_selecionado.configure(state="disabled")
        self.entry_descricao_modelo.configure(state="normal")
        self.entry_descricao_modelo.delete(0, "end")
        self.entry_descricao_modelo.configure(state="disabled")
        self.entry_valor.delete(0, "end")
        self.pagamento_var.set("À Vista")
        self.entry_parcelas.delete(0, "end")
        self.entry_parcelas.insert(0, "1")
        self.atualizar_visibilidade_parcelas()
        self.btn_salvar.configure(state="disabled")
        self.btn_imprimir.configure(state="disabled")

    def registrar_adiantamento(self):
        selected_item = self.tree_cortes.focus()
        if not selected_item:
            messagebox.showwarning("Aviso", "Selecione um corte na tabela.")
            return

        corte_data = self.tree_cortes.item(selected_item).get('values', [])
        if not corte_data or len(corte_data) < 3:
            messagebox.showwarning("Aviso", "Dados do corte inválidos.")
            return

        # Extrair dados do corte selecionado
        corte_id = corte_data[0]
        codigo_modelo = corte_data[1]
        faccao = corte_data[2]

        print(f"🔍 Registrando adiantamento: Corte ID={corte_id}, Modelo={codigo_modelo}, Facção={faccao}")

        # Validar valor
        valor_str = (self.entry_valor.get() or "").strip()
        if not valor_str:
            messagebox.showwarning("Aviso", "Informe o valor do adiantamento.")
            return

        try:
            valor = float(valor_str.replace(',', '.'))
            if valor <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Aviso", "Informe um valor numérico positivo.")
            return

        # Validar forma de pagamento e parcelas
        forma_pagamento = self.pagamento_var.get()
        parcelas = 1
        if forma_pagamento == "Parcelado":
            parcelas_str = (self.entry_parcelas.get() or "").strip()
            try:
                parcelas = int(parcelas_str)
                if parcelas < 1:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Aviso", "Número de parcelas inválido.")
                return

        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"💰 Dados do adiantamento: R$ {valor:.2f}, {forma_pagamento}, {parcelas} parcela(s)")

        try:
            # 🔥 CORREÇÃO PRINCIPAL: Usar db.execute em vez de _pg_exec
            resultado = db.execute(
                "INSERT INTO adiantamento_faccao (corte_id, codigo_modelo, faccao, valor, forma_pagamento, parcelas, data_hora) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    corte_id, str(codigo_modelo), str(faccao), float(valor), str(forma_pagamento), int(parcelas),
                    data_hora)
            )

            if resultado > 0:
                print("✅ Adiantamento registrado no banco com sucesso!")
                messagebox.showinfo("Sucesso", "Adiantamento registrado com sucesso!")

                # Gerar e abrir comprovante PDF
                caminho_pdf = self.imprimir_comprovante(mostrar_mensagem=False)
                if caminho_pdf:
                    try:
                        if os.name == "nt":
                            os.startfile(caminho_pdf)
                        elif os.name == "posix":
                            opener = "open" if sys.platform == "darwin" else "xdg-open"
                            subprocess.call([opener, caminho_pdf])
                        print(f"📄 Comprovante gerado: {caminho_pdf}")
                    except Exception as e:
                        print(f"⚠️ Não foi possível abrir o PDF: {e}")

                # Limpar campos após sucesso
                self.limpar_campos()
            else:
                messagebox.showerror("Erro", "Nenhum registro foi inserido no banco.")

        except Exception as e:
            error_msg = f"Falha ao registrar adiantamento:\n{str(e)}"
            print(f"❌ {error_msg}")
            messagebox.showerror("Erro", error_msg)

    def imprimir_comprovante(self, mostrar_mensagem=True):
        try:
            selected_item = self.tree_cortes.focus()
            if not selected_item:
                messagebox.showwarning("Aviso", "Selecione um corte na tabela antes de imprimir.")
                return None
            corte_data = self.tree_cortes.item(selected_item)['values']
            if not corte_data or len(corte_data) < 3:
                messagebox.showwarning("Aviso", "Dados do corte inválidos.")
                return None

            corte_id = corte_data[0]
            codigo = str(corte_data[1])
            if codigo.isdigit():
                codigo = codigo.zfill(4)

            faccao = corte_data[2]
            valor_str = (self.entry_valor.get() or "").strip()
            forma_pagamento = self.pagamento_var.get()
            parcelas = self.entry_parcelas.get() if forma_pagamento == "Parcelado" else "1"
            data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

            descricao = self.obter_descricao_corte(corte_id, codigo) or self.buscar_descricao_modelo(codigo)
            if not valor_str:
                messagebox.showwarning("Aviso", "Informe o valor do adiantamento.")
                return None
            try:
                valor = float(valor_str.replace(",", "."))
                if valor <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Valor Inválido", "Informe um valor numérico positivo.")
                return None

            if forma_pagamento == "Parcelado":
                try:
                    parc = int(parcelas)
                    if parc < 1:
                        raise ValueError
                except ValueError:
                    messagebox.showwarning("Parcelas Inválidas", "Número de parcelas deve ser positivo.")
                    return None

            # Diálogo para salvar PDF
            default_dir = os.path.join(os.path.expanduser("~"), "Documents")
            nome_padrao = f"Adiantamento_{codigo}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            caminho = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialdir=default_dir,
                initialfile=nome_padrao,
                filetypes=[("Arquivos PDF", "*.pdf")],
                title="Salvar Comprovante como"
            )
            if not caminho:
                return None

            c = canvas.Canvas(caminho, pagesize=letter)
            width, height = letter
            meio_pagina = height / 2

            styles = getSampleStyleSheet()

            def safe_str(v):
                return "" if v is None else str(v).strip()

            def format_currency(valor_local):
                try:
                    v = float(str(valor_local).replace(",", "."))
                    inteiro, frac = f"{v:,.2f}".split(".")
                    inteiro = inteiro.replace(",", ".")
                    return f"R$ {inteiro},{frac}"
                except Exception:
                    return "R$ 0,00"

            def desenhar_comprovante(c_local, width_local, height_local, y_position, via_num):
                left_margin = 50
                right_margin = width_local - 50
                table_width = right_margin - left_margin

                c_local.setFont("Helvetica-Bold", 14)
                c_local.drawCentredString(width_local / 2, y_position, "COMPROVANTE DE ADIANTAMENTO")
                c_local.setFont("Helvetica-Bold", 9)
                via_text = f"VIA {via_num}"
                text_w = c_local.stringWidth(via_text, "Helvetica-Bold", 9)
                c_local.drawString(right_margin - text_w, y_position, via_text)

                empresa_y = y_position - 22
                c_local.setFont("Helvetica-Bold", 11)
                c_local.drawString(left_margin, empresa_y, "OPERA FASHION")
                c_local.setFont("Helvetica", 9)
                c_local.drawString(left_margin, empresa_y - 14, "CNPJ: 053222550001-94")
                c_local.drawString(left_margin, empresa_y - 28,
                                   "Endereço: RUA ALFREDO NASCER QUADRA QI 05 LOTE 20 CONJUNTO VERA CRUZ 1")

                line_y = empresa_y - 36
                c_local.setLineWidth(0.8)
                c_local.line(left_margin, line_y, right_margin, line_y)

                dados_table = [
                    ["Facção:", safe_str(faccao)],
                    ["Código do Modelo:", safe_str(codigo)],
                    ["Descrição:", safe_str(descricao)],
                    ["Valor:", format_currency(valor)],
                    ["Forma de Pagamento:", safe_str(forma_pagamento)],
                    ["Parcelas:", safe_str(parcelas)],
                    ["Data/Hora:", safe_str(data_hora)]
                ]

                col0_w = 150
                col1_w = table_width - col0_w
                t = Table(dados_table, colWidths=[col0_w, col1_w])
                t.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                wrapped_width, wrapped_height = t.wrap(table_width, height_local)
                table_y = line_y - 10 - wrapped_height
                t.drawOn(c_local, left_margin, table_y)

                assinatura_top = table_y - 60
                c_local.setFont("Helvetica", 9)
                signature_line_length = 300
                line_y_sign = assinatura_top - 12
                center_x = (left_margin + right_margin) / 2
                c_local.setLineWidth(1)
                line_start = center_x - signature_line_length / 2
                c_local.line(line_start, line_y_sign, line_start + signature_line_length, line_y_sign)
                label_text = "Assinatura do Recebedor:"
                label_w = c_local.stringWidth(label_text, "Helvetica", 9)
                label_x = center_x - label_w / 2
                c_local.drawString(label_x, line_y_sign + 12, label_text)

            desenhar_comprovante(c, width, height, height - 40, 1)
            c.setLineWidth(0.8)
            c.line(50, meio_pagina, width - 50, meio_pagina)
            desenhar_comprovante(c, width, height, meio_pagina - 40, 2)

            c.save()

            if mostrar_mensagem:
                messagebox.showinfo("Sucesso", f"Comprovante gerado com sucesso:\n{caminho}")

            try:
                if os.name == 'nt':
                    os.startfile(caminho)
                elif os.name == 'posix':
                    opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                    subprocess.call([opener, caminho])
            except Exception:
                pass

            return caminho
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar comprovante:\n{str(e)}")
            return None

    def atualizar_data_hora(self):
        try:
            self.label_data.configure(text=datetime.now().strftime("%d/%m/%Y %H:%M"))
        except Exception:
            pass
        self.after(1000, self.atualizar_data_hora)

if __name__ == "__main__":
        ctk.set_appearance_mode("dark")
        root = ctk.CTk()
        root.geometry("900x600")
        root.title("Controle de Adiantamentos para Facções (PG)")
        app = PagamentoAdiantamentoPage(root, sistema=None)
        app.pack(fill="both", expand=True)
        root.mainloop()