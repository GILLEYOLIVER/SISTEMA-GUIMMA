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
        self._build()
        self._carregar_dados_planejamento()

    def _build(self):
        self.configure(fg_color="transparent")
        self.grid_rowconfigure(3, weight=1)
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
        ctk.CTkButton(toolbar, text="Gantt", command=self._abrir_gantt).grid(row=0, column=5)

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
        self.filtro_setor.grid(
            row=0, column=6, padx=(0, 12), pady=8
        )
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

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 24))
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
        self.tree_tecidos = ttk.Treeview(tecidos_frame, columns=("descricao", "qtd"), show="headings", height=6)
        self.tree_tecidos.heading("descricao", text="Tecido")
        self.tree_tecidos.heading("qtd", text="Metros")
        self.tree_tecidos.column("descricao", width=250)
        self.tree_tecidos.column("qtd", width=110, anchor="e")
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

    def _gerar_plano(self):
        if not self._db_ready():
            return
        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {schema}.planejamento_ops"
                    )
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
                        f"DELETE FROM {schema}.planejamento_capacidade"
                    )
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

                    cur.execute(
                        f"""
                        UPDATE {schema}.planejamento_capacidade
                           SET ociosidade = GREATEST(COALESCE(capacidade, 0) - COALESCE(carga, 0), 0),
                               data_atualizacao = NOW()
                        """
                    )
                    cur.execute(
                        f"""
                        UPDATE {schema}.planejamento_ops
                           SET status = CASE
                               WHEN fim IS NOT NULL AND fim < CURRENT_DATE THEN 'Atrasada'
                               WHEN inicio IS NOT NULL AND inicio <= CURRENT_DATE THEN 'Em execução'
                               ELSE COALESCE(status, 'Planejada')
                           END,
                           data_atualizacao = NOW()
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
        for desc, qtd in (dados.get("tecidos") or []):
            self.tree_tecidos.insert("", "end", values=(desc, f"{self._to_float(qtd):,.3f}"))

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
            filtros.append("COALESCE(po.inicio, po.data_atualizacao::date) >= %s")
            params.append(inicio)
        if fim:
            filtros.append("COALESCE(po.fim, po.data_atualizacao::date) <= %s")
            params.append(fim)
        if prioridade != "Todas":
            filtros.append("COALESCE(po.prioridade, 'Média') = %s")
            params.append(prioridade)
        if setor != "Todos":
            filtros.append("COALESCE(po.modelo, '') ILIKE %s")
            params.append(f"%{setor}%")

        where_ops = ("WHERE " + " AND ".join(filtros)) if filtros else ""

        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT
                            COALESCE(po.op, CONCAT('OC-', oc.id)) AS op,
                            COALESCE(po.modelo, oc.descricao_modelo, oc.codigo_modelo, 'Modelo sem descrição') AS modelo,
                            COALESCE(po.quantidade, NULLIF(oc.total_pecas, 0), oc.quantidade_desejada, 0) AS quantidade,
                            COALESCE(po.inicio, oc.data_registro::date, CURRENT_DATE) AS inicio,
                            COALESCE(po.fim, oc.data_final, (COALESCE(oc.data_registro::date, CURRENT_DATE) + INTERVAL '7 day')::date) AS fim,
                            COALESCE(po.status, oc.status, 'Planejada') AS status,
                            COALESCE(po.prioridade, 'Média') AS prioridade,
                            COALESCE(cmc.colecao, '') AS colecao,
                            COALESCE(cmc.grade_disponivel, '') AS grade,
                            COALESCE(cmc.id, 0) AS cadastro_id
                          FROM {schema}.ordem_corte_ficha oc
                     LEFT JOIN {schema}.planejamento_ops po
                            ON po.op = CONCAT('OC-', oc.id)
                     LEFT JOIN {schema}.cadastro_modelos_cabecalho cmc
                            ON cmc.codigo = oc.codigo_modelo
                        {where_ops}
                         ORDER BY COALESCE(po.inicio, oc.data_registro::date, CURRENT_DATE), COALESCE(po.op, CONCAT('OC-', oc.id))
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

            for op, modelo, quantidade, inicio_db, fim_db, status, _prioridade, colecao, grade, _cadastro_id in ops:
                tipo = self._classificar_programacao(inicio_db)
                if programacao != "Todas":
                    if programacao == "Coleção":
                        if not str(colecao or "").strip():
                            continue
                    elif tipo != programacao:
                        continue

                if status == "Em execução":
                    em_execucao += 1
                if status == "Atrasada":
                    atrasadas += 1

                inicio_txt = inicio_db.strftime("%d/%m/%Y") if inicio_db else ""
                fim_txt = fim_db.strftime("%d/%m/%Y") if fim_db else ""
                grupo = f"Coleção: {colecao}" if programacao == "Coleção" else f"Programação {tipo}"
                agrupado.setdefault(grupo, []).append((op, modelo, int(self._to_float(quantidade)), inicio_txt, fim_txt, status, tipo, colecao))

                self.ops_index[op] = {
                    "modelo": modelo,
                    "inicio": inicio_db,
                    "grade": grade,
                    "tecidos": [],
                    "aviamentos": [],
                }

            with get_conn() as conn:
                with conn.cursor() as cur:
                    for op in list(self.ops_index.keys()):
                        op_num = op.replace("OC-", "")
                        if not op_num.isdigit():
                            continue
                        cur.execute(
                            f"""
                            SELECT COALESCE(cmt.descricao, cmt.codigo_tecido, 'Tecido') AS descricao,
                                   COALESCE(cmt.metros_peca, 0) * COALESCE(NULLIF(oc.total_pecas, 0), oc.quantidade_desejada, 0) AS qtd
                              FROM {schema}.ordem_corte_ficha oc
                              JOIN {schema}.cadastro_modelos_tecidos cmt
                                ON cmt.codigo_modelo = oc.codigo_modelo
                             WHERE oc.id = %s
                             ORDER BY 1
                            """,
                            (int(op_num),),
                        )
                        self.ops_index[op]["tecidos"] = cur.fetchall()

                        cur.execute(
                            f"""
                            SELECT COALESCE(cma.descricao, cma.codigo_aviamento, 'Aviamento') AS descricao,
                                   COALESCE(cma.quantidade, 0) * COALESCE(NULLIF(oc.total_pecas, 0), oc.quantidade_desejada, 0) AS qtd
                              FROM {schema}.ordem_corte_ficha oc
                              JOIN {schema}.cadastro_modelos_aviamentos cma
                                ON cma.codigo_modelo = oc.codigo_modelo
                             WHERE oc.id = %s
                             ORDER BY 1
                            """,
                            (int(op_num),),
                        )
                        self.ops_index[op]["aviamentos"] = cur.fetchall()

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
