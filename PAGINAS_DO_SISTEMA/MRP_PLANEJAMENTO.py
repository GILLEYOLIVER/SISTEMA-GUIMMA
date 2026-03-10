# -*- coding: utf-8 -*-
"""
MRP_PLANEJAMENTO.py - Módulo MRP
Interface base para cálculo de necessidades de materiais.
"""
from datetime import datetime
import os
import webbrowser
from tkinter import messagebox, ttk

import customtkinter as ctk
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready


class MRPPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.tree_necessidades = None
        self.tree_ordens = None
        self.tree_fornecedores = None
        self.kpi_labels = []
        self.filtro_colecao = None
        self.filtro_status = None
        self._build()
        self._carregar_dados_mrp()

    def _build(self):
        self.configure(fg_color="transparent")
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_filters()
        self._build_results()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="MRP / Necessidades de Insumos", font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Planejamento de materiais com base em ordens e estoque atual.",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(5, weight=1)

        ctk.CTkButton(toolbar, text="Gerar MRP", command=self._gerar_mrp).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Simular", command=self._simular_mrp).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Aprovar Compra", command=self._aprovar_compra).grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Exportar PDF", command=self._exportar_mrp).grid(
            row=0, column=3, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Imprimir", command=self._imprimir_mrp).grid(
            row=0, column=4, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Configurações", command=self._abrir_configuracoes).grid(row=0, column=5)

    def _build_filters(self):
        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(9, weight=1)

        ctk.CTkLabel(filters, text="Período").grid(row=0, column=0, padx=(12, 6), pady=8)
        self.mrp_inicio_entry = ctk.CTkEntry(filters, placeholder_text="De")
        self.mrp_inicio_entry.grid(row=0, column=1, padx=(0, 6), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.mrp_inicio_entry),
        ).grid(row=0, column=2, padx=(0, 6), pady=8)
        self.mrp_fim_entry = ctk.CTkEntry(filters, placeholder_text="Até")
        self.mrp_fim_entry.grid(row=0, column=3, padx=(0, 12), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.mrp_fim_entry),
        ).grid(row=0, column=4, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Coleção").grid(row=0, column=5, padx=(0, 6), pady=8)
        self.filtro_colecao = ctk.CTkOptionMenu(filters, values=["Todas", "Linha Básica", "Coleção 2026"])
        self.filtro_colecao.grid(
            row=0, column=6, padx=(0, 12), pady=8
        )
        ctk.CTkLabel(filters, text="Status").grid(row=0, column=7, padx=(0, 6), pady=8)
        self.filtro_status = ctk.CTkOptionMenu(filters, values=["Crítico", "Atenção", "OK", "Todos"])
        self.filtro_status.set("Todos")
        self.filtro_status.grid(
            row=0, column=8, padx=(0, 12), pady=8
        )
        ctk.CTkButton(filters, text="Filtrar", command=self._carregar_dados_mrp).grid(row=0, column=9, padx=(0, 12), pady=8)

    def _build_results(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 24))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        kpis = ctk.CTkFrame(body)
        kpis.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        kpis.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for idx, text in enumerate(
            ["Itens críticos: 0", "Faltantes: 0", "Valor a comprar: R$ 0,00", "Lead time médio: 0 dias"]
        ):
            card = ctk.CTkFrame(kpis)
            card.grid(row=0, column=idx, padx=6, sticky="ew")
            label = ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=12, weight="bold"))
            label.pack(
                pady=12
            )
            self.kpi_labels.append(label)

        tabs = ctk.CTkTabview(body)
        tabs.grid(row=1, column=0, sticky="nsew")

        necessidades_tab = tabs.add("Necessidades")
        ordens_tab = tabs.add("Ordens Recomendadas")
        fornecedores_tab = tabs.add("Fornecedores Críticos")

        self._build_necessidades_tab(necessidades_tab)
        self._build_ordens_tab(ordens_tab)
        self._build_fornecedores_tab(fornecedores_tab)

    def _build_necessidades_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree_necessidades = ttk.Treeview(
            tree_frame,
            columns=("insumo", "sku", "necessario", "estoque", "faltante", "lead", "fornecedor", "status"),
            show="headings",
            height=12,
        )
        for col, text, width in (
            ("insumo", "Insumo", 220),
            ("sku", "SKU", 120),
            ("necessario", "Necessário", 110),
            ("estoque", "Estoque", 90),
            ("faltante", "Faltante", 90),
            ("lead", "Lead Time", 90),
            ("fornecedor", "Fornecedor", 200),
            ("status", "Status", 90),
        ):
            self.tree_necessidades.heading(col, text=text)
            self.tree_necessidades.column(col, width=width)
        self.tree_necessidades.column("necessario", anchor="e")
        self.tree_necessidades.column("estoque", anchor="e")
        self.tree_necessidades.column("faltante", anchor="e")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_necessidades.yview)
        self.tree_necessidades.configure(yscrollcommand=tree_scroll.set)
        self.tree_necessidades.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    def _build_ordens_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        info = ctk.CTkFrame(parent)
        info.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        info.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(info, text="Plano de compra recomendado").grid(
            row=0, column=0, padx=12, pady=8, sticky="w"
        )
        ctk.CTkButton(info, text="Converter em Pedido", command=self._aprovar_compra).grid(row=0, column=2, padx=12, pady=8)

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree_ordens = ttk.Treeview(
            tree_frame,
            columns=("ordem", "insumo", "quantidade", "fornecedor", "data"),
            show="headings",
            height=10,
        )
        for col, text, width in (
            ("ordem", "Ordem", 90),
            ("insumo", "Insumo", 220),
            ("quantidade", "Quantidade", 120),
            ("fornecedor", "Fornecedor", 200),
            ("data", "Entrega Prevista", 140),
        ):
            self.tree_ordens.heading(col, text=text)
            self.tree_ordens.column(col, width=width)
        self.tree_ordens.column("quantidade", anchor="e")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_ordens.yview)
        self.tree_ordens.configure(yscrollcommand=tree_scroll.set)
        self.tree_ordens.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    @staticmethod
    def _to_float(valor):
        try:
            return float(valor or 0)
        except Exception:
            return 0.0

    def _db_ready(self):
        ok, msg = require_ready()
        if not ok:
            messagebox.showerror("MRP", msg)
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

    def _gerar_mrp(self):
        if not self._db_ready():
            return

        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        DELETE FROM {schema}.mrp_necessidades
                        """
                    )

                    cur.execute(
                        f"""
                        INSERT INTO {schema}.mrp_necessidades
                            (insumo, sku, necessario, estoque, faltante, lead_time, fornecedor, status, data_atualizacao)
                        WITH demanda AS (
                            SELECT o.codigo_modelo,
                                   COALESCE(NULLIF(o.total_pecas, 0), o.quantidade_desejada, 0)::numeric AS qtde
                              FROM {schema}.ordem_corte_ficha o
                             WHERE COALESCE(o.ativo, TRUE) = TRUE
                               AND COALESCE(o.status, 'Em Andamento') <> 'Cancelada'
                        ),
                        necessidade_tecidos AS (
                            SELECT 'Tecido'::text AS tipo,
                                   COALESCE(t.codigo_tecido, t.descricao, t.codigo_modelo) AS sku,
                                   COALESCE(t.descricao, t.codigo_tecido, 'Tecido sem descrição') AS insumo,
                                   COALESCE(t.fornecedor, '') AS fornecedor,
                                   SUM(COALESCE(t.metros_peca, 0) * d.qtde) AS necessario
                              FROM {schema}.cadastro_modelos_tecidos t
                              JOIN demanda d ON d.codigo_modelo = t.codigo_modelo
                             GROUP BY 1,2,3,4
                        ),
                        necessidade_aviamentos AS (
                            SELECT 'Aviamento'::text AS tipo,
                                   COALESCE(a.codigo_aviamento, a.descricao, a.codigo_modelo) AS sku,
                                   COALESCE(a.descricao, a.codigo_aviamento, 'Aviamento sem descrição') AS insumo,
                                   COALESCE(a.fornecedor, '') AS fornecedor,
                                   SUM(COALESCE(a.quantidade, 0) * d.qtde) AS necessario
                              FROM {schema}.cadastro_modelos_aviamentos a
                              JOIN demanda d ON d.codigo_modelo = a.codigo_modelo
                             GROUP BY 1,2,3,4
                        ),
                        necessidade_outros AS (
                            SELECT 'Insumo'::text AS tipo,
                                   COALESCE(o.codigo, o.descricao, o.codigo_modelo) AS sku,
                                   COALESCE(o.descricao, o.codigo, 'Insumo sem descrição') AS insumo,
                                   COALESCE(o.fornecedor, '') AS fornecedor,
                                   SUM(COALESCE(o.quantidade, 0) * d.qtde) AS necessario
                              FROM {schema}.cadastro_modelos_outros o
                              JOIN demanda d ON d.codigo_modelo = o.codigo_modelo
                             GROUP BY 1,2,3,4
                        ),
                        necessidade_total AS (
                            SELECT * FROM necessidade_tecidos
                            UNION ALL
                            SELECT * FROM necessidade_aviamentos
                            UNION ALL
                            SELECT * FROM necessidade_outros
                        ),
                        estoque_total AS (
                            SELECT 'Tecido'::text AS tipo,
                                   COALESCE(codigo, descricao) AS sku,
                                   COALESCE(descricao, codigo, 'Tecido sem descrição') AS insumo,
                                   COALESCE(fornecedor, '') AS fornecedor,
                                   SUM(COALESCE(metros, 0)) AS estoque
                              FROM {schema}.estoque_tecidos
                             GROUP BY 1,2,3,4
                            UNION ALL
                            SELECT 'Aviamento'::text AS tipo,
                                   COALESCE(codigo, descricao) AS sku,
                                   COALESCE(descricao, codigo, 'Aviamento sem descrição') AS insumo,
                                   COALESCE(fornecedor, '') AS fornecedor,
                                   SUM(COALESCE(quantidade, 0)) AS estoque
                              FROM {schema}.estoque_aviamentos
                             GROUP BY 1,2,3,4
                            UNION ALL
                            SELECT 'Insumo'::text AS tipo,
                                   COALESCE(codigo, descricao) AS sku,
                                   COALESCE(descricao, codigo, 'Insumo sem descrição') AS insumo,
                                   COALESCE(fornecedor, '') AS fornecedor,
                                   SUM(COALESCE(quantidade, 0)) AS estoque
                              FROM {schema}.estoque_insumos
                             GROUP BY 1,2,3,4
                        )
                        SELECT n.insumo,
                               n.sku,
                               ROUND(SUM(n.necessario), 3) AS necessario,
                               ROUND(COALESCE(MAX(e.estoque), 0), 3) AS estoque,
                               ROUND(GREATEST(SUM(n.necessario) - COALESCE(MAX(e.estoque), 0), 0), 3) AS faltante,
                               COALESCE(MAX(f.prazo_medio), 0) AS lead_time,
                               COALESCE(NULLIF(MAX(n.fornecedor), ''), NULLIF(MAX(e.fornecedor), ''), 'Fornecedor não informado') AS fornecedor,
                               CASE
                                   WHEN GREATEST(SUM(n.necessario) - COALESCE(MAX(e.estoque), 0), 0) <= 0 THEN 'OK'
                                   WHEN COALESCE(MAX(f.prazo_medio), 0) >= 20 THEN 'Crítico'
                                   ELSE 'Atenção'
                               END AS status,
                               NOW()
                          FROM necessidade_total n
                     LEFT JOIN estoque_total e
                            ON e.tipo = n.tipo
                           AND (
                                UPPER(TRIM(COALESCE(e.sku, ''))) = UPPER(TRIM(COALESCE(n.sku, '')))
                                OR UPPER(TRIM(COALESCE(e.insumo, ''))) = UPPER(TRIM(COALESCE(n.insumo, '')))
                           )
                     LEFT JOIN {schema}.compras_fornecedores f
                            ON UPPER(TRIM(COALESCE(f.nome, ''))) = UPPER(TRIM(COALESCE(n.fornecedor, e.fornecedor, '')))
                      GROUP BY n.insumo, n.sku
                        """
                    )

                    cur.execute(f"DELETE FROM {schema}.mrp_ordens_recomendadas WHERE status = 'Planejada'")
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.mrp_ordens_recomendadas (insumo, quantidade, fornecedor, entrega_prevista, status, data_atualizacao)
                        SELECT insumo,
                               faltante,
                               COALESCE(NULLIF(fornecedor, ''), 'Fornecedor não informado'),
                               CURRENT_DATE + (COALESCE(lead_time, 0) * INTERVAL '1 day'),
                               'Planejada',
                               NOW()
                          FROM {schema}.mrp_necessidades
                         WHERE COALESCE(faltante, 0) > 0
                        """
                    )
                conn.commit()

            self._carregar_dados_mrp()
            messagebox.showinfo("MRP", "MRP gerado com sucesso. Necessidades e ordens foram atualizadas.")
        except Exception as exc:
            messagebox.showerror("MRP", f"Erro ao gerar MRP: {exc}")

    def _simular_mrp(self):
        if self.tree_necessidades is None:
            return

        total_faltante = 0.0
        itens_criticos = 0
        for item in self.tree_necessidades.get_children():
            vals = self.tree_necessidades.item(item).get("values", [])
            faltante = self._to_float(vals[4] if len(vals) > 4 else 0)
            status = str(vals[7]) if len(vals) > 7 else ""
            total_faltante += faltante
            if status == "Crítico":
                itens_criticos += 1

        messagebox.showinfo(
            "Simulação MRP",
            f"Simulação concluída.\nItens críticos: {itens_criticos}\nQuantidade total faltante: {total_faltante:,.2f}",
        )

    def _aprovar_compra(self):
        if self.tree_ordens is None:
            return

        selecionado = self.tree_ordens.focus()
        if not selecionado:
            messagebox.showwarning("Aprovar Compra", "Selecione uma ordem recomendada para aprovar.")
            return

        valores = self.tree_ordens.item(selecionado).get("values", [])
        if not valores:
            return

        ordem_id = valores[0]
        if not self._db_ready():
            return

        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE {schema}.mrp_ordens_recomendadas SET status = 'Aprovada', data_atualizacao = NOW() WHERE id = %s",
                        (ordem_id,),
                    )
                conn.commit()

            self._carregar_dados_mrp()
            messagebox.showinfo("Aprovar Compra", f"Ordem {ordem_id} aprovada com sucesso.")
        except Exception as exc:
            messagebox.showerror("Aprovar Compra", f"Erro ao aprovar compra: {exc}")

    def _abrir_configuracoes(self):
        messagebox.showinfo(
            "Configurações MRP",
            "Configurações do MRP em desenvolvimento.\nUse os filtros para período e status nesta versão.",
        )

    def _carregar_dados_mrp(self):
        self._limpar_tree(self.tree_necessidades)
        self._limpar_tree(self.tree_ordens)
        self._limpar_tree(self.tree_fornecedores)

        ok, _ = require_ready()
        if not ok:
            return

        inicio = self._parse_data(self.mrp_inicio_entry.get())
        fim = self._parse_data(self.mrp_fim_entry.get())
        status = (self.filtro_status.get() if self.filtro_status else "Todos") or "Todos"

        where_nec = []
        params_nec = []
        if inicio:
            where_nec.append("data_atualizacao::date >= %s")
            params_nec.append(inicio)
        if fim:
            where_nec.append("data_atualizacao::date <= %s")
            params_nec.append(fim)
        if status != "Todos":
            where_nec.append("status = %s")
            params_nec.append(status)

        where_sql_nec = ("WHERE " + " AND ".join(where_nec)) if where_nec else ""

        where_ord = []
        params_ord = []
        if inicio:
            where_ord.append("data_atualizacao::date >= %s")
            params_ord.append(inicio)
        if fim:
            where_ord.append("data_atualizacao::date <= %s")
            params_ord.append(fim)
        where_sql_ord = ("WHERE " + " AND ".join(where_ord)) if where_ord else ""

        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT id, COALESCE(insumo, ''), COALESCE(sku, ''), COALESCE(necessario, 0),
                               COALESCE(estoque, 0), COALESCE(faltante, 0), COALESCE(lead_time, 0),
                               COALESCE(fornecedor, ''), COALESCE(status, 'OK')
                          FROM {schema}.mrp_necessidades
                          {where_sql_nec}
                         ORDER BY
                           CASE COALESCE(status, 'OK') WHEN 'Crítico' THEN 0 WHEN 'Atenção' THEN 1 ELSE 2 END,
                           faltante DESC,
                           insumo
                        """,
                        params_nec,
                    )
                    necessidades = cur.fetchall()

                    cur.execute(
                        f"""
                        SELECT id, COALESCE(insumo, ''), COALESCE(quantidade, 0), COALESCE(fornecedor, ''),
                               entrega_prevista, COALESCE(status, 'Planejada')
                          FROM {schema}.mrp_ordens_recomendadas
                          {where_sql_ord}
                         ORDER BY data_atualizacao DESC, id DESC
                        """,
                        params_ord,
                    )
                    ordens = cur.fetchall()

                    cur.execute(
                        f"""
                        WITH base_fornecedores AS (
                            SELECT TRIM(COALESCE(fornecedor, '')) AS fornecedor, 'estoque'::text AS origem
                              FROM {schema}.estoque_insumos
                             WHERE TRIM(COALESCE(fornecedor, '')) <> ''
                            UNION ALL
                            SELECT TRIM(COALESCE(fornecedor, '')) AS fornecedor, 'estoque'::text AS origem
                              FROM {schema}.estoque_aviamentos
                             WHERE TRIM(COALESCE(fornecedor, '')) <> ''
                            UNION ALL
                            SELECT TRIM(COALESCE(fornecedor, '')) AS fornecedor, 'estoque'::text AS origem
                              FROM {schema}.estoque_tecidos
                             WHERE TRIM(COALESCE(fornecedor, '')) <> ''
                            UNION ALL
                            SELECT COALESCE(f.nome, 'Fornecedor não informado') AS fornecedor, 'compras'::text AS origem
                              FROM {schema}.compras_pedidos p
                         LEFT JOIN {schema}.compras_fornecedores f ON f.id = p.fornecedor_id
                        ),
                        atrasos AS (
                            SELECT COALESCE(f.nome, 'Fornecedor não informado') AS fornecedor,
                                   ROUND(AVG(GREATEST(COALESCE(r.data_recebimento, CURRENT_DATE) - COALESCE(p.entrega_prevista, p.data_pedido), 0)), 1) AS atraso_medio
                              FROM {schema}.compras_pedidos p
                         LEFT JOIN {schema}.compras_fornecedores f ON f.id = p.fornecedor_id
                         LEFT JOIN {schema}.compras_recebimentos r ON r.pedido_id = p.id
                             WHERE COALESCE(p.status, 'Em aberto') IN ('Em aberto', 'Parcial', 'Aprovado', 'Recebido')
                          GROUP BY 1
                        )
                        SELECT b.fornecedor,
                               COUNT(*) AS insumos_criticos,
                               COALESCE(MAX(a.atraso_medio), 0) AS atraso_medio
                          FROM base_fornecedores b
                     LEFT JOIN atrasos a ON UPPER(TRIM(a.fornecedor)) = UPPER(TRIM(b.fornecedor))
                      GROUP BY 1
                      ORDER BY 2 DESC, 3 DESC
                      LIMIT 20
                        """
                    )
                    fornecedores = cur.fetchall()

            total_faltante = 0.0
            itens_criticos = 0
            lead_sum = 0.0

            for linha in necessidades:
                _, insumo, sku, necessario, estoque, faltante, lead, fornecedor, st = linha
                total_faltante += self._to_float(faltante)
                lead_sum += self._to_float(lead)
                if st == "Crítico":
                    itens_criticos += 1
                self.tree_necessidades.insert(
                    "",
                    "end",
                    values=(
                        insumo,
                        sku,
                        f"{self._to_float(necessario):,.2f}",
                        f"{self._to_float(estoque):,.2f}",
                        f"{self._to_float(faltante):,.2f}",
                        int(self._to_float(lead)),
                        fornecedor,
                        st,
                    ),
                )

            for linha in ordens:
                ordem_id, insumo, quantidade, fornecedor, entrega_prevista, _ = linha
                entrega_txt = entrega_prevista.strftime("%d/%m/%Y") if entrega_prevista else ""
                self.tree_ordens.insert(
                    "",
                    "end",
                    values=(ordem_id, insumo, f"{self._to_float(quantidade):,.2f}", fornecedor, entrega_txt),
                )

            for linha in fornecedores:
                fornecedor, insumos_criticos, atraso_medio = linha
                risco = "Alto" if self._to_float(atraso_medio) >= 7 else "Médio" if self._to_float(atraso_medio) >= 3 else "Baixo"
                self.tree_fornecedores.insert(
                    "",
                    "end",
                    values=(fornecedor, int(insumos_criticos or 0), f"{self._to_float(atraso_medio):.1f} dias", risco),
                )

            total_itens = len(necessidades)
            lead_medio = (lead_sum / total_itens) if total_itens else 0
            if self.kpi_labels:
                self.kpi_labels[0].configure(text=f"Itens críticos: {itens_criticos}")
                self.kpi_labels[1].configure(text=f"Faltantes: {total_faltante:,.2f}")
                self.kpi_labels[2].configure(text=f"Valor a comprar: R$ 0,00")
                self.kpi_labels[3].configure(text=f"Lead time médio: {lead_medio:.1f} dias")
        except Exception as exc:
            messagebox.showerror("MRP", f"Erro ao carregar dados do MRP: {exc}")

    def _build_fornecedores_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree_fornecedores = ttk.Treeview(
            tree_frame,
            columns=("fornecedor", "insumos", "atraso", "risco"),
            show="headings",
            height=10,
        )
        for col, text, width in (
            ("fornecedor", "Fornecedor", 240),
            ("insumos", "Insumos Críticos", 160),
            ("atraso", "Atraso Médio", 120),
            ("risco", "Risco", 120),
        ):
            self.tree_fornecedores.heading(col, text=text)
            self.tree_fornecedores.column(col, width=width)

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_fornecedores.yview)
        self.tree_fornecedores.configure(yscrollcommand=tree_scroll.set)
        self.tree_fornecedores.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    def _exportar_mrp(self):
        try:
            caminho = self._gerar_pdf_mrp()
            self._abrir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("MRP", f"Erro ao exportar PDF: {exc}")

    def _imprimir_mrp(self):
        try:
            caminho = self._gerar_pdf_mrp()
            self._imprimir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("MRP", f"Erro ao imprimir: {exc}")

    def _gerar_pdf_mrp(self):
        nome = f"mrp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        caminho = os.path.abspath(nome)
        c = canvas.Canvas(caminho, pagesize=A4)
        largura, altura = A4
        y = altura - 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Relatório MRP")
        y -= 24
        c.setFont("Helvetica", 9)
        c.drawString(40, y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        y -= 18

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

        if self.tree_necessidades:
            escrever_titulo("Necessidades")
            linhas = []
            for item in self.tree_necessidades.get_children():
                vals = self.tree_necessidades.item(item)["values"]
                linhas.append(
                    f"- {vals[0]} | {vals[1]} | Necessário {vals[2]} | Estoque {vals[3]} | Faltante {vals[4]}"
                )
            escrever_linhas(linhas or ["Sem dados."])
            y -= 8

        if self.tree_ordens:
            escrever_titulo("Ordens Recomendadas")
            linhas = []
            for item in self.tree_ordens.get_children():
                vals = self.tree_ordens.item(item)["values"]
                linhas.append(f"- {vals[0]} | {vals[1]} | Qtde {vals[2]} | {vals[3]} | {vals[4]}")
            escrever_linhas(linhas or ["Sem dados."])
            y -= 8

        if self.tree_fornecedores:
            escrever_titulo("Fornecedores Críticos")
            linhas = []
            for item in self.tree_fornecedores.get_children():
                vals = self.tree_fornecedores.item(item)["values"]
                linhas.append(f"- {vals[0]} | Insumos {vals[1]} | Atraso {vals[2]} | Risco {vals[3]}")
            escrever_linhas(linhas or ["Sem dados."])

        c.save()
        return caminho

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
        messagebox.showinfo("MRP", "PDF aberto no navegador. Use Ctrl+P para imprimir.")

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
    app.title("MRP - Teste")
    app.geometry("1200x720")
    page = MRPPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()
