# -*- coding: utf-8 -*-
"""
PLANEJAMENTO_PRODUCAO.py - Planejamento de Produção
Interface base para capacidade, carga de trabalho e cronograma.
"""
from datetime import datetime
import os
import webbrowser
from tkinter import messagebox, ttk

import customtkinter as ctk
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready


class PlanejamentoProducaoPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.tree_ops = None
        self.tree_capacidade = None
        self.tree_tecidos = None
        self.tree_aviamentos = None
        self.kpi_labels = []
        self.filtro_setor = None
        self.filtro_prioridade = None
        self.filtro_programacao = None
        self.detalhe_labels = {}
        self.ops_index = {}
        self.combo_modelo_programacao = None
        self.combo_grade_programacao = None
        self.entry_qtd_programacao = None
        self.combo_prioridade_programacao = None
        self.combo_tipo_programacao = None
        self.entry_programacao_inicio = None
        self.entry_programacao_fim = None
        self._build()
        self._carregar_dados_planejamento()

    def _build(self):
        self.configure(fg_color="transparent")
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_filters()
        self._build_body()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Planejamento de Produção", font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Controle de capacidade, carga de trabalho e cronograma.",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        # JESUS SEJA LOUVADO PARA TODO O SEMPRE AMEM!!!

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(5, weight=1)

        ctk.CTkButton(toolbar, text="Gerar Plano", command=self._gerar_plano).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Reprogramar", command=self._reprogramar).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Simular Capacidade", command=self._simular_capacidade).grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Exportar PDF", command=self._exportar_planejamento).grid(
            row=0, column=3, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Imprimir", command=self._imprimir_planejamento).grid(
            row=0, column=4, padx=(0, 8)
        )

    def _build_filters(self):
        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(12, weight=1)

        ctk.CTkLabel(filters, text="Período").grid(row=0, column=0, padx=(12, 6), pady=8)
        self.plan_inicio_entry = ctk.CTkEntry(filters, placeholder_text="De")
        self.plan_inicio_entry.grid(row=0, column=1, padx=(0, 6), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.plan_inicio_entry),
        ).grid(row=0, column=2, padx=(0, 6), pady=8)
        self.plan_fim_entry = ctk.CTkEntry(filters, placeholder_text="Até")
        self.plan_fim_entry.grid(row=0, column=3, padx=(0, 12), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.plan_fim_entry),
        ).grid(row=0, column=4, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Setor").grid(row=0, column=5, padx=(0, 6), pady=8)
        self.filtro_setor = ctk.CTkOptionMenu(filters, values=["Todos", "Corte", "Costura", "Acabamento"])
        self.filtro_setor.grid(row=0, column=6, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Prioridade").grid(row=0, column=7, padx=(0, 6), pady=8)
        self.filtro_prioridade = ctk.CTkOptionMenu(filters, values=["Alta", "Média", "Baixa", "Todas"])
        self.filtro_prioridade.set("Todas")
        self.filtro_prioridade.grid(row=0, column=8, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Programação").grid(row=0, column=9, padx=(0, 6), pady=8)
        self.filtro_programacao = ctk.CTkOptionMenu(
            filters,
            values=["Todas", "Semanal", "Mensal", "Trimestral", "Semestral", "Coleção"],
        )
        self.filtro_programacao.set("Todas")
        self.filtro_programacao.grid(row=0, column=10, padx=(0, 12), pady=8)
        ctk.CTkButton(filters, text="Filtrar", command=self._carregar_dados_planejamento).grid(
            row=0, column=12, padx=(0, 12), pady=8
        )

        programacao = ctk.CTkFrame(self)
        programacao.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 12))
        programacao.grid_columnconfigure(13, weight=1)
        ctk.CTkLabel(
            programacao,
            text="Passo a passo: Nova Programação de Produção",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=14, sticky="w", padx=12, pady=(8, 4))

        ctk.CTkLabel(programacao, text="1) Período início").grid(row=1, column=0, padx=(12, 6), pady=8)
        self.entry_programacao_inicio = ctk.CTkEntry(programacao, width=110, placeholder_text="dd/mm/aaaa")
        self.entry_programacao_inicio.grid(row=1, column=1, padx=(0, 6), pady=8)
        ctk.CTkButton(programacao, text="📅", width=32, command=lambda: self._abrir_calendario(self.entry_programacao_inicio)).grid(row=1, column=2, padx=(0, 8), pady=8)

        ctk.CTkLabel(programacao, text="2) Período fim").grid(row=1, column=3, padx=(0, 6), pady=8)
        self.entry_programacao_fim = ctk.CTkEntry(programacao, width=110, placeholder_text="dd/mm/aaaa")
        self.entry_programacao_fim.grid(row=1, column=4, padx=(0, 6), pady=8)
        ctk.CTkButton(programacao, text="📅", width=32, command=lambda: self._abrir_calendario(self.entry_programacao_fim)).grid(row=1, column=5, padx=(0, 8), pady=8)

        ctk.CTkLabel(programacao, text="3) Modelo").grid(row=1, column=6, padx=(0, 6), pady=8)
        self.combo_modelo_programacao = ctk.CTkOptionMenu(programacao, values=["Selecione"], command=self._on_modelo_programacao_change)
        self.combo_modelo_programacao.grid(row=1, column=7, padx=(0, 8), pady=8)

        ctk.CTkLabel(programacao, text="4) Quantidade").grid(row=1, column=8, padx=(0, 6), pady=8)
        self.entry_qtd_programacao = ctk.CTkEntry(programacao, width=90, placeholder_text="Qtde")
        self.entry_qtd_programacao.grid(row=1, column=9, padx=(0, 8), pady=8)

        ctk.CTkLabel(programacao, text="5) Grade").grid(row=1, column=10, padx=(0, 6), pady=8)
        self.combo_grade_programacao = ctk.CTkOptionMenu(programacao, values=["Padrão"])
        self.combo_grade_programacao.grid(row=1, column=11, padx=(0, 8), pady=8)

        ctk.CTkLabel(programacao, text="6) Prioridade").grid(row=1, column=12, padx=(0, 6), pady=8)
        self.combo_prioridade_programacao = ctk.CTkOptionMenu(programacao, values=["Alta", "Média", "Baixa"])
        self.combo_prioridade_programacao.set("Média")
        self.combo_prioridade_programacao.grid(row=1, column=13, padx=(0, 8), pady=8)

        ctk.CTkLabel(programacao, text="Programação").grid(row=2, column=0, padx=(12, 6), pady=(0, 10))
        self.combo_tipo_programacao = ctk.CTkOptionMenu(programacao, values=["Semanal", "Mensal", "Trimestral", "Semestral", "Coleção"])
        self.combo_tipo_programacao.set("Semanal")
        self.combo_tipo_programacao.grid(row=2, column=1, padx=(0, 8), pady=(0, 10))

        ctk.CTkButton(programacao, text="Gerar Nova Programação", command=self._gerar_nova_programacao).grid(
            row=2, column=2, columnspan=2, padx=(0, 8), pady=(0, 10)
        )
        ctk.CTkButton(programacao, text="Atualizar Modelos", command=self._carregar_modelos_programacao).grid(
            row=2, column=4, columnspan=2, padx=(0, 8), pady=(0, 10)
        )

        self._carregar_modelos_programacao()

    def _carregar_modelos_programacao(self):
        if not self.combo_modelo_programacao:
            return
        ok, _ = require_ready()
        if not ok:
            return
        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT COALESCE(codigo, ''), COALESCE(descricao, '')
                          FROM {schema}.cadastro_modelos_cabecalho
                         ORDER BY codigo
                        """
                    )
                    rows = cur.fetchall()
            valores = [f"{codigo} - {descricao}".strip(" -") for codigo, descricao in rows if str(codigo).strip()]
            if not valores:
                valores = ["Sem modelos cadastrados"]
            self.combo_modelo_programacao.configure(values=valores)
            self.combo_modelo_programacao.set(valores[0])
            self._on_modelo_programacao_change(valores[0])
        except Exception:
            self.combo_modelo_programacao.configure(values=["Erro ao carregar modelos"])
            self.combo_modelo_programacao.set("Erro ao carregar modelos")

    def _on_modelo_programacao_change(self, modelo_selecionado):
        if not self.combo_grade_programacao:
            return
        codigo = (modelo_selecionado or "").split(" - ")[0].strip()
        if not codigo or codigo.startswith("Sem modelos") or codigo.startswith("Erro"):
            self.combo_grade_programacao.configure(values=["Padrão"])
            self.combo_grade_programacao.set("Padrão")
            return
        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT COALESCE(grade_disponivel, '') FROM {schema}.cadastro_modelos_cabecalho WHERE codigo = %s LIMIT 1",
                        (codigo,),
                    )
                    row = cur.fetchone()
            grade_txt = (row[0] if row else "") or ""
            grades = [g.strip() for g in str(grade_txt).replace(";", ",").split(",") if g.strip()]
            if not grades:
                grades = ["Padrão"]
            self.combo_grade_programacao.configure(values=grades)
            self.combo_grade_programacao.set(grades[0])
        except Exception:
            self.combo_grade_programacao.configure(values=["Padrão"])
            self.combo_grade_programacao.set("Padrão")

    def _gerar_nova_programacao(self):
        if not self._db_ready():
            return

        inicio = self._parse_data(self.entry_programacao_inicio.get() if self.entry_programacao_inicio else "")
        fim = self._parse_data(self.entry_programacao_fim.get() if self.entry_programacao_fim else "")
        modelo_info = self.combo_modelo_programacao.get() if self.combo_modelo_programacao else ""
        codigo_modelo = (modelo_info or "").split(" - ")[0].strip()
        descricao_modelo = (modelo_info or "").split(" - ", 1)[1].strip() if " - " in (modelo_info or "") else codigo_modelo
        grade = self.combo_grade_programacao.get() if self.combo_grade_programacao else "Padrão"
        prioridade = self.combo_prioridade_programacao.get() if self.combo_prioridade_programacao else "Média"
        tipo_programacao = self.combo_tipo_programacao.get() if self.combo_tipo_programacao else "Semanal"

        try:
            quantidade = int(float((self.entry_qtd_programacao.get() if self.entry_qtd_programacao else "0").replace(",", ".")))
        except Exception:
            quantidade = 0

        if not inicio or not fim:
            messagebox.showwarning("Nova Programação", "Informe o período de início e fim.")
            return
        if not codigo_modelo or codigo_modelo.startswith("Sem modelos") or codigo_modelo.startswith("Erro"):
            messagebox.showwarning("Nova Programação", "Selecione um modelo válido.")
            return
        if quantidade <= 0:
            messagebox.showwarning("Nova Programação", "Informe uma quantidade maior que zero.")
            return

        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COALESCE(colecao, '') FROM {schema}.cadastro_modelos_cabecalho WHERE codigo = %s", (codigo_modelo,))
                    row = cur.fetchone()
                    colecao = row[0] if row else ""

                    cur.execute(
                        f"""
                        INSERT INTO {schema}.planejamento_programacao_ops
                            (periodo_inicio, periodo_fim, codigo_modelo, modelo, colecao, quantidade, grade, prioridade, tipo_programacao, status, data_atualizacao)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Planejada', NOW())
                        RETURNING id
                        """,
                        (inicio, fim, codigo_modelo, descricao_modelo, colecao, quantidade, grade, prioridade, tipo_programacao),
                    )
                    novo_id = cur.fetchone()[0]
                    op = f"PRG-{novo_id}"
                    cur.execute(f"UPDATE {schema}.planejamento_programacao_ops SET op = %s WHERE id = %s", (op, novo_id))
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.planejamento_ops (op, modelo, quantidade, inicio, fim, status, prioridade, data_atualizacao)
                        VALUES (%s, %s, %s, %s, %s, 'Planejada', %s, NOW())
                        ON CONFLICT (op) DO UPDATE
                           SET modelo = EXCLUDED.modelo,
                               quantidade = EXCLUDED.quantidade,
                               inicio = EXCLUDED.inicio,
                               fim = EXCLUDED.fim,
                               prioridade = EXCLUDED.prioridade,
                               status = EXCLUDED.status,
                               data_atualizacao = NOW()
                        """,
                        (op, descricao_modelo, quantidade, inicio, fim, prioridade),
                    )
                conn.commit()

            messagebox.showinfo("Nova Programação", f"Programação {op} criada com sucesso.")
            self._carregar_dados_planejamento()
        except Exception as exc:
            messagebox.showerror("Nova Programação", f"Erro ao criar programação: {exc}")

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=4, column=0, sticky="nsew", padx=24, pady=(0, 24))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        kpis = ctk.CTkFrame(body)
        kpis.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        kpis.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for idx, text in enumerate(
            ["OPs em execução: 0", "Atrasos críticos: 0", "Capacidade usada: 0%", "Ociosidade: 0%"]
        ):
            card = ctk.CTkFrame(kpis)
            card.grid(row=0, column=idx, padx=6, sticky="ew")
            label = ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=12, weight="bold"))
            label.pack(
                pady=12
            )
            self.kpi_labels.append(label)

        ordens_frame = ctk.CTkFrame(body)
        ordens_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        ordens_frame.grid_columnconfigure(0, weight=1)
        ordens_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            ordens_frame, text="Ordens Planejadas", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.tree_ops = ttk.Treeview(
            ordens_frame,
            columns=("op", "modelo", "quantidade", "inicio", "fim", "status", "programacao", "colecao"),
            show="headings",
            height=12,
        )
        for col, text, width in (
            ("op", "OP", 90),
            ("modelo", "Modelo", 200),
            ("quantidade", "Qtde", 80),
            ("inicio", "Início", 110),
            ("fim", "Fim", 110),
            ("status", "Status", 120),
            ("programacao", "Programação", 110),
            ("colecao", "Coleção", 120),
        ):
            self.tree_ops.heading(col, text=text)
            self.tree_ops.column(col, width=width)
        self.tree_ops.column("quantidade", anchor="e")
        self.tree_ops.tag_configure("grupo", background="#E8EEF6", font=("Arial", 10, "bold"))
        self.tree_ops.bind("<Double-1>", self._abrir_detalhe_op)

        tree_scroll = ttk.Scrollbar(ordens_frame, orient="vertical", command=self.tree_ops.yview)
        self.tree_ops.configure(yscrollcommand=tree_scroll.set)
        self.tree_ops.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        tree_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16))

        capacity_frame = ctk.CTkFrame(body)
        capacity_frame.grid(row=1, column=1, sticky="nsew")
        capacity_frame.grid_columnconfigure(0, weight=1)
        capacity_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            capacity_frame, text="Capacidade por Recurso", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.tree_capacidade = ttk.Treeview(
            capacity_frame,
            columns=("recurso", "carga", "capacidade", "ocioso"),
            show="headings",
            height=10,
        )
        for col, text, width in (
            ("recurso", "Recurso", 160),
            ("carga", "Carga", 90),
            ("capacidade", "Capacidade", 100),
            ("ocioso", "Ociosidade", 90),
        ):
            self.tree_capacidade.heading(col, text=text)
            self.tree_capacidade.column(col, width=width)
        self.tree_capacidade.column("carga", anchor="e")
        self.tree_capacidade.column("capacidade", anchor="e")
        self.tree_capacidade.column("ocioso", anchor="e")

        capacity_scroll = ttk.Scrollbar(capacity_frame, orient="vertical", command=self.tree_capacidade.yview)
        self.tree_capacidade.configure(yscrollcommand=capacity_scroll.set)
        self.tree_capacidade.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        capacity_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16))

        detalhe_frame = ctk.CTkFrame(body)
        detalhe_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        detalhe_frame.grid_columnconfigure(0, weight=1)
        detalhe_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            detalhe_frame, text="Detalhes do Corte Selecionado", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 8))

        info = ctk.CTkFrame(detalhe_frame)
        info.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))
        info.grid_columnconfigure((0, 1, 2), weight=1)
        for idx, chave in enumerate(("grade", "prazo", "modelo")):
            txt = "Grade: -" if chave == "grade" else ("Prazo início: -" if chave == "prazo" else "Modelo: -")
            lbl = ctk.CTkLabel(info, text=txt, anchor="w")
            lbl.grid(row=0, column=idx, sticky="ew", padx=8, pady=8)
            self.detalhe_labels[chave] = lbl

        tecidos_frame = ctk.CTkFrame(detalhe_frame)
        tecidos_frame.grid(row=2, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))
        tecidos_frame.grid_columnconfigure(0, weight=1)
        tecidos_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(tecidos_frame, text="Tecidos necessários", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 6)
        )
        self.tree_tecidos = ttk.Treeview(tecidos_frame, columns=("descricao", "necessario", "estoque", "saldo", "status"), show="headings", height=6)
        self.tree_tecidos.heading("descricao", text="Tecido")
        self.tree_tecidos.heading("necessario", text="Necessário")
        self.tree_tecidos.heading("estoque", text="Estoque")
        self.tree_tecidos.heading("saldo", text="Saldo")
        self.tree_tecidos.heading("status", text="Status")
        self.tree_tecidos.column("descricao", width=220)
        self.tree_tecidos.column("necessario", width=90, anchor="e")
        self.tree_tecidos.column("estoque", width=90, anchor="e")
        self.tree_tecidos.column("saldo", width=90, anchor="e")
        self.tree_tecidos.column("status", width=80, anchor="center")
        self.tree_tecidos.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        aviamentos_frame = ctk.CTkFrame(detalhe_frame)
        aviamentos_frame.grid(row=2, column=1, sticky="nsew", padx=(8, 16), pady=(0, 16))
        aviamentos_frame.grid_columnconfigure(0, weight=1)
        aviamentos_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(aviamentos_frame, text="Aviamentos necessários", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 6)
        )
        self.tree_aviamentos = ttk.Treeview(aviamentos_frame, columns=("descricao", "qtd"), show="headings", height=6)
        self.tree_aviamentos.heading("descricao", text="Aviamento")
        self.tree_aviamentos.heading("qtd", text="Qtd")
        self.tree_aviamentos.column("descricao", width=250)
        self.tree_aviamentos.column("qtd", width=110, anchor="e")
        self.tree_aviamentos.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    @staticmethod
    def _to_float(valor):
        try:
            return float(valor or 0)
        except Exception:
            return 0.0

    def _db_ready(self):
        ok, msg = require_ready()
        if not ok:
            messagebox.showerror("Planejamento", msg)
        return ok

    def _parse_data(self, texto):
        if not texto:
            return None
        try:
            return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
        except Exception:
            return None

    def _limpar_tree(self, tree):
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)

    def _garantir_tabela_programacao(self, cur, schema):
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {schema}.planejamento_programacao_ops (
                id SERIAL PRIMARY KEY,
                op VARCHAR(60) UNIQUE,
                periodo_inicio DATE NOT NULL,
                periodo_fim DATE NOT NULL,
                codigo_modelo VARCHAR(100) NOT NULL,
                modelo VARCHAR(200),
                colecao VARCHAR(100),
                quantidade INTEGER DEFAULT 0,
                grade VARCHAR(200),
                prioridade VARCHAR(20) DEFAULT 'Média',
                tipo_programacao VARCHAR(30) DEFAULT 'Semanal',
                status VARCHAR(30) DEFAULT 'Planejada',
                observacoes TEXT,
                data_atualizacao TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cur.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_planejamento_ops_op ON {schema}.planejamento_ops(op)"
        )

    def _gerar_plano(self):
        if not self._db_ready():
            return
        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    self._garantir_tabela_programacao(cur, schema)
                    cur.execute(f"DELETE FROM {schema}.planejamento_ops")
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.planejamento_ops (op, modelo, quantidade, inicio, fim, status, prioridade, data_atualizacao)
                        SELECT CONCAT('OC-', id) AS op,
                               COALESCE(descricao_modelo, codigo_modelo, 'Modelo sem descrição') AS modelo,
                               COALESCE(NULLIF(total_pecas, 0), quantidade_desejada, 0) AS quantidade,
                               COALESCE(data_registro::date, CURRENT_DATE) AS inicio,
                               COALESCE(data_final, (COALESCE(data_registro::date, CURRENT_DATE) + INTERVAL '7 day')::date) AS fim,
                               CASE
                                   WHEN COALESCE(status, 'Em Andamento') ILIKE '%final%' THEN 'Finalizada'
                                   WHEN COALESCE(data_final, CURRENT_DATE) < CURRENT_DATE THEN 'Atrasada'
                                   ELSE 'Em execução'
                               END AS status,
                               CASE
                                   WHEN COALESCE(NULLIF(total_pecas, 0), quantidade_desejada, 0) >= 1000 THEN 'Alta'
                                   WHEN COALESCE(NULLIF(total_pecas, 0), quantidade_desejada, 0) >= 300 THEN 'Média'
                                   ELSE 'Baixa'
                               END AS prioridade,
                               NOW()
                          FROM {schema}.ordem_corte_ficha
                         WHERE COALESCE(ativo, TRUE) = TRUE
                        """
                    )
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.planejamento_ops (op, modelo, quantidade, inicio, fim, status, prioridade, data_atualizacao)
                        SELECT COALESCE(op, CONCAT('PRG-', id)),
                               COALESCE(modelo, codigo_modelo),
                               COALESCE(quantidade, 0),
                               periodo_inicio,
                               periodo_fim,
                               COALESCE(status, 'Planejada'),
                               COALESCE(prioridade, 'Média'),
                               NOW()
                          FROM {schema}.planejamento_programacao_ops
                        """
                    )

                    cur.execute(f"DELETE FROM {schema}.planejamento_capacidade")
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.planejamento_capacidade (recurso, carga, capacidade, ociosidade, data_atualizacao)
                        WITH recursos AS (
                            SELECT UPPER(TRIM(COALESCE(cortador, ''))) AS recurso,
                                   SUM(COALESCE(total_pecas, 0))::numeric AS carga
                              FROM {schema}.cadastro_de_corte
                             WHERE COALESCE(NULLIF(cortador, ''), '') <> ''
                             GROUP BY 1
                            UNION ALL
                            SELECT UPPER(TRIM(COALESCE(auxiliar, ''))) AS recurso,
                                   SUM(COALESCE(total_pecas, 0))::numeric AS carga
                              FROM {schema}.cadastro_de_corte
                             WHERE COALESCE(NULLIF(auxiliar, ''), '') <> ''
                             GROUP BY 1
                            UNION ALL
                            SELECT UPPER(TRIM(COALESCE(ajudante, ''))) AS recurso,
                                   SUM(COALESCE(total_pecas, 0))::numeric AS carga
                              FROM {schema}.cadastro_de_corte
                             WHERE COALESCE(NULLIF(ajudante, ''), '') <> ''
                             GROUP BY 1
                        )
                        SELECT recurso,
                               SUM(carga) AS carga,
                               GREATEST(SUM(carga) * 1.20, 1) AS capacidade,
                               GREATEST((SUM(carga) * 1.20) - SUM(carga), 0) AS ociosidade,
                               NOW()
                          FROM recursos
                      GROUP BY recurso
                        """
                    )
                conn.commit()
            self._carregar_dados_planejamento()
            messagebox.showinfo("Planejamento", "Plano atualizado com sucesso.")
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao gerar plano: {exc}")

    def _reprogramar(self):
        if not self._db_ready():
            return
        selecionado = self.tree_ops.focus() if self.tree_ops else None
        if not selecionado:
            messagebox.showwarning("Planejamento", "Selecione uma OP para reprogramar.")
            return
        valores = self.tree_ops.item(selecionado).get("values", [])
        if not valores:
            return
        op = valores[0]
        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        UPDATE {schema}.planejamento_ops
                           SET inicio = COALESCE(inicio, CURRENT_DATE) + INTERVAL '1 day',
                               fim = COALESCE(fim, CURRENT_DATE) + INTERVAL '1 day',
                               status = 'Reprogramada',
                               data_atualizacao = NOW()
                         WHERE op = %s
                        """,
                        (op,),
                    )
                conn.commit()
            self._carregar_dados_planejamento()
            messagebox.showinfo("Planejamento", f"OP {op} reprogramada para +1 dia.")
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao reprogramar: {exc}")

    def _simular_capacidade(self):
        carga = 0.0
        capacidade = 0.0
        if self.tree_capacidade:
            for item in self.tree_capacidade.get_children():
                vals = self.tree_capacidade.item(item).get("values", [])
                carga += self._to_float(vals[1] if len(vals) > 1 else 0)
                capacidade += self._to_float(vals[2] if len(vals) > 2 else 0)
        uso = (carga / capacidade * 100) if capacidade > 0 else 0
        messagebox.showinfo("Simulação", f"Carga total: {carga:,.2f}\nCapacidade total: {capacidade:,.2f}\nUso estimado: {uso:.1f}%")

    def _abrir_gantt(self):
        if not self.tree_ops or not self.tree_ops.get_children():
            messagebox.showinfo("Gantt", "Sem dados para visualizar o Gantt.")
            return
        messagebox.showinfo("Gantt", "Visualização Gantt em evolução. As OPs já estão carregadas na grade.")

    @staticmethod
    def _classificar_programacao(data_inicio):
        if not data_inicio:
            return "Semanal"
        mes = data_inicio.month
        dia = data_inicio.day
        if dia <= 7:
            return "Semanal"
        if dia <= 15:
            return "Mensal"
        if mes in (1, 4, 7, 10):
            return "Trimestral"
        if mes in (1, 7):
            return "Semestral"
        return "Mensal"

    @staticmethod
    def _texto_grade(grade_str):
        bruto = str(grade_str or "").strip()
        if not bruto:
            return "-"
        partes = [p.strip() for p in bruto.replace(';', ',').split(',') if p.strip()]
        return " / ".join(partes) if partes else bruto

    def _limpar_detalhes(self):
        if self.detalhe_labels:
            self.detalhe_labels.get("grade").configure(text="Grade: -")
            self.detalhe_labels.get("prazo").configure(text="Prazo início: -")
            self.detalhe_labels.get("modelo").configure(text="Modelo: -")
        self._limpar_tree(self.tree_tecidos)
        self._limpar_tree(self.tree_aviamentos)

    def _abrir_detalhe_op(self, _event=None):
        if not self.tree_ops:
            return
        item = self.tree_ops.focus()
        if not item:
            return
        valores = self.tree_ops.item(item).get("values", [])
        if not valores:
            return
        op = str(valores[0])
        if op.startswith("GRUPO:"):
            return

        dados = self.ops_index.get(op)
        if not dados:
            self._limpar_detalhes()
            return

        grade_txt = self._texto_grade(dados.get("grade"))
        prazo = dados.get("inicio")
        prazo_txt = prazo.strftime("%d/%m/%Y") if prazo else "-"
        modelo = dados.get("modelo") or "-"
        self.detalhe_labels.get("grade").configure(text=f"Grade: {grade_txt}")
        self.detalhe_labels.get("prazo").configure(text=f"Prazo início: {prazo_txt}")
        self.detalhe_labels.get("modelo").configure(text=f"Modelo: {modelo}")

        self._limpar_tree(self.tree_tecidos)
        for desc, necessario, estoque, saldo, status_estoque in (dados.get("tecidos") or []):
            self.tree_tecidos.insert("", "end", values=(
                desc,
                f"{self._to_float(necessario):,.3f}",
                f"{self._to_float(estoque):,.3f}",
                f"{self._to_float(saldo):,.3f}",
                status_estoque,
            ))

        self._limpar_tree(self.tree_aviamentos)
        for desc, qtd in (dados.get("aviamentos") or []):
            self.tree_aviamentos.insert("", "end", values=(desc, f"{self._to_float(qtd):,.3f}"))

    def _carregar_dados_planejamento(self):
        self._limpar_tree(self.tree_ops)
        self._limpar_tree(self.tree_capacidade)
        self._limpar_detalhes()
        self.ops_index = {}
        ok, _ = require_ready()
        if not ok:
            return

        inicio = self._parse_data(self.plan_inicio_entry.get())
        fim = self._parse_data(self.plan_fim_entry.get())
        setor = (self.filtro_setor.get() if self.filtro_setor else "Todos") or "Todos"
        prioridade = (self.filtro_prioridade.get() if self.filtro_prioridade else "Todas") or "Todas"
        programacao = (self.filtro_programacao.get() if self.filtro_programacao else "Todas") or "Todas"

        filtros = []
        params = []
        if inicio:
            filtros.append("COALESCE(po.inicio, ppo.periodo_inicio, oc.data_registro::date, po.data_atualizacao::date) >= %s")
            params.append(inicio)
        if fim:
            filtros.append("COALESCE(po.fim, ppo.periodo_fim, oc.data_final, po.data_atualizacao::date) <= %s")
            params.append(fim)
        if prioridade != "Todas":
            filtros.append("COALESCE(ppo.prioridade, po.prioridade, 'Média') = %s")
            params.append(prioridade)
        if setor != "Todos":
            filtros.append("COALESCE(po.modelo, ppo.modelo, oc.descricao_modelo, '') ILIKE %s")
            params.append(f"%{setor}%")

        where_ops = ("WHERE " + " AND ".join(filtros)) if filtros else ""

        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    self._garantir_tabela_programacao(cur, schema)
                    cur.execute(
                        f"""
                        SELECT
                            COALESCE(po.op, ppo.op, CONCAT('OC-', oc.id)) AS op,
                            COALESCE(po.modelo, ppo.modelo, oc.descricao_modelo, oc.codigo_modelo, 'Modelo sem descrição') AS modelo,
                            COALESCE(po.quantidade, ppo.quantidade, NULLIF(oc.total_pecas, 0), oc.quantidade_desejada, 0) AS quantidade,
                            COALESCE(po.inicio, ppo.periodo_inicio, oc.data_registro::date, CURRENT_DATE) AS inicio,
                            COALESCE(po.fim, ppo.periodo_fim, oc.data_final, (COALESCE(oc.data_registro::date, CURRENT_DATE) + INTERVAL '7 day')::date) AS fim,
                            COALESCE(po.status, ppo.status, oc.status, 'Planejada') AS status,
                            COALESCE(ppo.prioridade, po.prioridade, 'Média') AS prioridade,
                            COALESCE(ppo.tipo_programacao, '') AS tipo_programacao,
                            COALESCE(cmc.colecao, ppo.colecao, '') AS colecao,
                            COALESCE(ppo.grade, cmc.grade_disponivel, '') AS grade,
                            COALESCE(cmc.codigo, ppo.codigo_modelo, oc.codigo_modelo, '') AS codigo_modelo
                          FROM {schema}.planejamento_ops po
                     LEFT JOIN {schema}.planejamento_programacao_ops ppo ON ppo.op = po.op
                     LEFT JOIN {schema}.ordem_corte_ficha oc ON po.op = CONCAT('OC-', oc.id)
                     LEFT JOIN {schema}.cadastro_modelos_cabecalho cmc ON cmc.codigo = COALESCE(ppo.codigo_modelo, oc.codigo_modelo)
                        {where_ops}
                         ORDER BY COALESCE(po.inicio, ppo.periodo_inicio, oc.data_registro::date, CURRENT_DATE), po.op
                        """,
                        params,
                    )
                    ops = cur.fetchall()

                    cur.execute(
                        f"""
                        SELECT COALESCE(recurso, ''), COALESCE(carga, 0), COALESCE(capacidade, 0), COALESCE(ociosidade, 0)
                          FROM {schema}.planejamento_capacidade
                         ORDER BY recurso
                        """
                    )
                    capacidades = cur.fetchall()

            em_execucao = 0
            atrasadas = 0
            carga_total = 0.0
            capacidade_total = 0.0
            agrupado = {}

            for op, modelo, quantidade, inicio_db, fim_db, status, _prioridade, tipo_programacao, colecao, grade, codigo_modelo in ops:
                tipo = tipo_programacao or self._classificar_programacao(inicio_db)
                if programacao != "Todas":
                    if programacao == "Coleção":
                        if not str(colecao or "").strip():
                            continue
                    elif tipo != programacao:
                        continue

                if str(status) == "Em execução":
                    em_execucao += 1
                if str(status) == "Atrasada":
                    atrasadas += 1

                inicio_txt = inicio_db.strftime("%d/%m/%Y") if inicio_db else ""
                fim_txt = fim_db.strftime("%d/%m/%Y") if fim_db else ""
                grupo = f"Coleção: {colecao}" if programacao == "Coleção" else f"Programação {tipo}"
                agrupado.setdefault(grupo, []).append((op, modelo, int(self._to_float(quantidade)), inicio_txt, fim_txt, status, tipo, colecao))

                self.ops_index[op] = {
                    "modelo": modelo,
                    "inicio": inicio_db,
                    "grade": grade,
                    "codigo_modelo": codigo_modelo,
                    "quantidade": quantidade,
                    "tecidos": [],
                    "aviamentos": [],
                }

            with get_conn() as conn:
                with conn.cursor() as cur:
                    for op, info in self.ops_index.items():
                        codigo_modelo = info.get("codigo_modelo")
                        qtd_pecas = self._to_float(info.get("quantidade"))
                        if not codigo_modelo:
                            continue

                        cur.execute(
                            f"""
                            SELECT
                                COALESCE(cmt.codigo_tecido, '') AS codigo,
                                COALESCE(cmt.descricao, cmt.codigo_tecido, 'Tecido') AS descricao,
                                COALESCE(cmt.metros_peca, 0) * %s AS necessario,
                                COALESCE((
                                    SELECT SUM(COALESCE(et.metros,0))
                                      FROM {schema}.estoque_tecidos et
                                     WHERE et.codigo = cmt.codigo_tecido
                                ), 0) AS estoque
                              FROM {schema}.cadastro_modelos_tecidos cmt
                             WHERE cmt.codigo_modelo = %s
                             ORDER BY 2
                            """,
                            (qtd_pecas, codigo_modelo),
                        )
                        tecidos = []
                        for _codigo, desc, necessario, estoque in cur.fetchall():
                            saldo = self._to_float(estoque) - self._to_float(necessario)
                            status_estoque = "OK" if saldo >= 0 else "Falta"
                            tecidos.append((desc, necessario, estoque, saldo, status_estoque))
                        info["tecidos"] = tecidos

                        cur.execute(
                            f"""
                            SELECT COALESCE(cma.descricao, cma.codigo_aviamento, 'Aviamento') AS descricao,
                                   COALESCE(cma.quantidade, 0) * %s AS qtd
                              FROM {schema}.cadastro_modelos_aviamentos cma
                             WHERE cma.codigo_modelo = %s
                             ORDER BY 1
                            """,
                            (qtd_pecas, codigo_modelo),
                        )
                        info["aviamentos"] = cur.fetchall()

            for grupo in sorted(agrupado.keys()):
                self.tree_ops.insert("", "end", values=(f"GRUPO: {grupo}", "", "", "", "", "", "", ""), tags=("grupo",))
                for linha in agrupado[grupo]:
                    self.tree_ops.insert("", "end", values=linha)

            for recurso, carga, capacidade, ocioso in capacidades:
                carga_total += self._to_float(carga)
                capacidade_total += self._to_float(capacidade)
                self.tree_capacidade.insert(
                    "",
                    "end",
                    values=(recurso, f"{self._to_float(carga):,.2f}", f"{self._to_float(capacidade):,.2f}", f"{self._to_float(ocioso):,.2f}"),
                )

            uso_pct = (carga_total / capacidade_total * 100) if capacidade_total > 0 else 0
            ocioso_pct = max(0.0, 100 - uso_pct)

            if self.kpi_labels:
                self.kpi_labels[0].configure(text=f"OPs em execução: {em_execucao}")
                self.kpi_labels[1].configure(text=f"Atrasos críticos: {atrasadas}")
                self.kpi_labels[2].configure(text=f"Capacidade usada: {uso_pct:.1f}%")
                self.kpi_labels[3].configure(text=f"Ociosidade: {ocioso_pct:.1f}%")
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao carregar planejamento: {exc}")

    def _exportar_planejamento(self):
        try:
            caminho = self._gerar_pdf_planejamento()
            self._abrir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao exportar PDF: {exc}")

    def _imprimir_planejamento(self):
        try:
            caminho = self._gerar_pdf_planejamento()
            self._imprimir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao imprimir: {exc}")

    def _gerar_pdf_planejamento(self):
        nome = f"planejamento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        caminho = os.path.abspath(nome)
        c = canvas.Canvas(caminho, pagesize=A4)
        largura, altura = A4
        y = self._desenhar_cabecalho_pdf(c, largura, altura, "Planejamento de Produção")

        def escrever_titulo(titulo):
            nonlocal y
            c.setFont("Helvetica-Bold", 11)
            c.drawString(40, y, titulo)
            y -= 16
            c.setFont("Helvetica", 9)

        def escrever_linhas(linhas):
            nonlocal y
            for linha in linhas:
                if y < 80:
                    c.showPage()
                    y = altura - 60
                c.drawString(40, y, linha)
                y -= 12

        if self.tree_ops:
            escrever_titulo("Ordens Planejadas")
            linhas = []
            for item in self.tree_ops.get_children():
                vals = self.tree_ops.item(item)["values"]
                linhas.append(f"- OP {vals[0]} | {vals[1]} | Qtde {vals[2]} | {vals[3]} -> {vals[4]} | {vals[5]}")
            escrever_linhas(linhas or ["Sem dados."])
            y -= 8

        if self.tree_capacidade:
            escrever_titulo("Capacidade por Recurso")
            linhas = []
            for item in self.tree_capacidade.get_children():
                vals = self.tree_capacidade.item(item)["values"]
                linhas.append(f"- {vals[0]} | Carga {vals[1]} | Capacidade {vals[2]} | Ocioso {vals[3]}")
            escrever_linhas(linhas or ["Sem dados."])

        c.save()
        return caminho

    def _desenhar_cabecalho_pdf(self, c, largura, altura, titulo):
        header_h = 64
        c.setFillColor(colors.HexColor("#1F5FA6"))
        c.rect(0, altura - header_h, largura, header_h, fill=1, stroke=0)

        logo_path = os.path.join(os.path.dirname(__file__), "LOGO.jpg")
        x_text = 40
        if os.path.exists(logo_path):
            try:
                c.drawImage(logo_path, 24, altura - 52, width=30, height=30, preserveAspectRatio=True, mask='auto')
                x_text = 62
            except Exception:
                pass

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x_text, altura - 34, titulo)
        c.setFont("Helvetica", 9)
        c.drawString(x_text, altura - 49, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        c.setFillColor(colors.HexColor("#666666"))
        c.setFont("Helvetica", 8)
        c.drawString(24, 18, "SISTEMA OPERA — Impressão")
        return altura - header_h - 12

    def _abrir_pdf(self, caminho):
        try:
            webbrowser.open_new_tab("file://" + caminho)
        except Exception:
            if hasattr(os, "startfile"):
                os.startfile(caminho)  # type: ignore[attr-defined]

    def _imprimir_pdf(self, caminho):
        if hasattr(os, "startfile"):
            try:
                os.startfile(caminho, "print")  # type: ignore[attr-defined]
                return
            except Exception:
                pass
        self._abrir_pdf(caminho)
        messagebox.showinfo("Planejamento", "PDF aberto no navegador. Use Ctrl+P para imprimir.")

    def _abrir_calendario(self, entry):
        from datetime import datetime as _dt
        import calendar as _cal

        def setar_data(d):
            entry.delete(0, "end")
            entry.insert(0, d.strftime("%d/%m/%Y"))
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

        now = _dt.now()
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
                        command=lambda d=dia: setar_data(_dt(ano, mes, d)),
                    )
                    btn.grid(row=i + 1, column=j, padx=2, pady=2)

        desenhar_calendario()


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Planejamento de Produção - Teste")
    app.geometry("1200x720")
    page = PlanejamentoProducaoPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()
