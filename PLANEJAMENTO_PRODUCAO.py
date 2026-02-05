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
from reportlab.pdfgen import canvas

try:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception:
    def get_conn():
        raise RuntimeError("Módulo BANCO_DE_DADOS_PG não encontrado")

    def get_schema():
        return "opera"

    def require_ready(essentials=None):
        return False, "Módulo de banco de dados não disponível"


class PlanejamentoProducaoPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.tree_ops = None
        self.tree_capacidade = None
        self.kpi_labels = {}
        self.selected_op_id = None
        self.selected_capacidade_id = None
        self._tabelas_ok = {}
        self._build()
        self._verificar_conexao()
        self.after(200, self._carregar_dados)

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

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(5, weight=1)

        ctk.CTkButton(toolbar, text="Gerar Plano", command=self._abrir_form_op).grid(
            row=0, column=0, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Reprogramar", command=self._editar_op).grid(
            row=0, column=1, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Simular Capacidade", command=self._abrir_form_capacidade).grid(
            row=0, column=2, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Exportar PDF", command=self._exportar_planejamento).grid(
            row=0, column=3, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Imprimir", command=self._imprimir_planejamento).grid(
            row=0, column=4, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Gantt").grid(row=0, column=5)

    def _build_filters(self):
        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(9, weight=1)

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
        self.filter_setor = ctk.CTkOptionMenu(
            filters, values=["Todos", "Corte", "Costura", "Acabamento"]
        )
        self.filter_setor.grid(row=0, column=6, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Prioridade").grid(row=0, column=7, padx=(0, 6), pady=8)
        self.filter_prioridade = ctk.CTkOptionMenu(
            filters, values=["Alta", "Média", "Baixa", "Todas"]
        )
        self.filter_prioridade.grid(row=0, column=8, padx=(0, 12), pady=8)
        ctk.CTkButton(filters, text="Filtrar", command=self._carregar_dados).grid(
            row=0, column=9, padx=(0, 12), pady=8
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
        kpi_info = [
            ("execucao", "OPs em execução", "0"),
            ("atrasos", "Atrasos críticos", "0"),
            ("capacidade", "Capacidade usada", "0%"),
            ("ociosidade", "Ociosidade", "0%"),
        ]
        for idx, (key, title, value) in enumerate(kpi_info):
            card = ctk.CTkFrame(kpis)
            card.grid(row=0, column=idx, padx=6, sticky="ew")
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12)).pack(
                anchor="w", padx=16, pady=(10, 0)
            )
            label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=18, weight="bold"))
            label.pack(anchor="w", padx=16, pady=(4, 10))
            self.kpi_labels[key] = label

        ordens_frame = ctk.CTkFrame(body)
        ordens_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        ordens_frame.grid_columnconfigure(0, weight=1)
        ordens_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            ordens_frame, text="Ordens Planejadas", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.tree_ops = ttk.Treeview(
            ordens_frame,
            columns=("op", "modelo", "quantidade", "inicio", "fim", "status"),
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
        ):
            self.tree_ops.heading(col, text=text)
            self.tree_ops.column(col, width=width)
        self.tree_ops.column("quantidade", anchor="e")
        self.tree_ops.bind("<<TreeviewSelect>>", self._selecionar_op)

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
        self.tree_capacidade.bind("<<TreeviewSelect>>", self._selecionar_capacidade)

        capacity_scroll = ttk.Scrollbar(capacity_frame, orient="vertical", command=self.tree_capacidade.yview)
        self.tree_capacidade.configure(yscrollcommand=capacity_scroll.set)
        self.tree_capacidade.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        capacity_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16))

    def _verificar_conexao(self):
        try:
            ok, msg = require_ready()
            if not ok:
                messagebox.showwarning("Banco de dados", msg)
        except Exception as exc:
            messagebox.showwarning("Banco de dados", f"Não foi possível validar o banco: {exc}")

    def _checar_tabela(self, tabela, force=False):
        if tabela in self._tabelas_ok and not force:
            return self._tabelas_ok[tabela]
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = %s AND table_name = %s
                    )
                    """,
                    (schema, tabela),
                )
                exists = cursor.fetchone()[0]
            conn.commit()
            self._tabelas_ok[tabela] = bool(exists)
            if not exists:
                messagebox.showwarning(
                    "Planejamento",
                    f"Tabela '{tabela}' não encontrada. Verifique a instalação do banco.",
                )
            return self._tabelas_ok[tabela]
        except Exception as exc:
            self._tabelas_ok[tabela] = False
            messagebox.showerror("Planejamento", f"Erro ao validar tabela {tabela}: {exc}")
            return False

    def _carregar_dados(self):
        if not self.tree_ops or not self.tree_capacidade:
            return
        if not self._checar_tabela("planejamento_ops") or not self._checar_tabela("planejamento_capacidade"):
            self.tree_ops.delete(*self.tree_ops.get_children())
            self.tree_capacidade.delete(*self.tree_capacidade.get_children())
            self._atualizar_kpis(0, 0, 0, 0)
            return

        self.tree_ops.delete(*self.tree_ops.get_children())
        self.tree_capacidade.delete(*self.tree_capacidade.get_children())

        inicio = self._parse_data(self.plan_inicio_entry.get().strip())
        fim = self._parse_data(self.plan_fim_entry.get().strip())
        prioridade = self.filter_prioridade.get() if hasattr(self, "filter_prioridade") else "Todas"
        setor = self.filter_setor.get() if hasattr(self, "filter_setor") else "Todos"

        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                params = []
                where = []
                if inicio:
                    where.append("inicio >= %s")
                    params.append(inicio)
                if fim:
                    where.append("fim <= %s")
                    params.append(fim)
                if prioridade and prioridade != "Todas":
                    where.append("prioridade = %s")
                    params.append(prioridade)
                where_clause = f"WHERE {' AND '.join(where)}" if where else ""
                cursor.execute(
                    f"""
                    SELECT id, op, modelo, quantidade, inicio, fim, status, prioridade
                    FROM {schema}.planejamento_ops
                    {where_clause}
                    ORDER BY inicio ASC NULLS LAST
                    """,
                    params,
                )
                rows = cursor.fetchall()
                for row in rows:
                    inicio_txt = row[4].strftime("%d/%m/%Y") if row[4] else ""
                    fim_txt = row[5].strftime("%d/%m/%Y") if row[5] else ""
                    self.tree_ops.insert(
                        "", "end", values=(row[1], row[2], row[3], inicio_txt, fim_txt, row[6]), iid=row[0]
                    )

                params = []
                where = []
                if setor and setor != "Todos":
                    where.append("recurso ILIKE %s")
                    params.append(f"%{setor}%")
                where_clause = f"WHERE {' AND '.join(where)}" if where else ""
                cursor.execute(
                    f"""
                    SELECT id, recurso, carga, capacidade, ociosidade
                    FROM {schema}.planejamento_capacidade
                    {where_clause}
                    ORDER BY recurso ASC
                    """,
                    params,
                )
                rows_cap = cursor.fetchall()
                for row in rows_cap:
                    self.tree_capacidade.insert(
                        "",
                        "end",
                        values=(row[1], f"{row[2]:.2f}", f"{row[3]:.2f}", f"{row[4]:.2f}"),
                        iid=row[0],
                    )
            conn.commit()
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao carregar dados: {exc}")
            return

        ops_execucao = sum(1 for row in rows if (row[6] or "").lower() in {"em andamento", "em execução", "em execucao"})
        atrasos = sum(
            1
            for row in rows
            if row[5] and row[5] < datetime.now().date() and (row[6] or "").lower() != "concluída"
        )

        total_carga = sum(float(row[2]) for row in rows_cap) if rows_cap else 0
        total_capacidade = sum(float(row[3]) for row in rows_cap) if rows_cap else 0
        total_ociosidade = sum(float(row[4]) for row in rows_cap) if rows_cap else 0
        capacidade_pct = (total_carga / total_capacidade * 100) if total_capacidade else 0
        ociosidade_pct = (total_ociosidade / total_capacidade * 100) if total_capacidade else 0
        self._atualizar_kpis(ops_execucao, atrasos, capacidade_pct, ociosidade_pct)

    def _atualizar_kpis(self, execucao, atrasos, capacidade, ociosidade):
        if not self.kpi_labels:
            return
        self.kpi_labels["execucao"].configure(text=str(execucao))
        self.kpi_labels["atrasos"].configure(text=str(atrasos))
        self.kpi_labels["capacidade"].configure(text=f"{capacidade:.0f}%")
        self.kpi_labels["ociosidade"].configure(text=f"{ociosidade:.0f}%")

    def _selecionar_op(self, _event=None):
        if not self.tree_ops:
            return
        selecionado = self.tree_ops.selection()
        self.selected_op_id = selecionado[0] if selecionado else None

    def _selecionar_capacidade(self, _event=None):
        if not self.tree_capacidade:
            return
        selecionado = self.tree_capacidade.selection()
        self.selected_capacidade_id = selecionado[0] if selecionado else None

    def _abrir_form_op(self):
        self.selected_op_id = None
        self._abrir_form_op_dados()

    def _editar_op(self):
        if not self.selected_op_id:
            messagebox.showwarning("Planejamento", "Selecione uma OP para reprogramar.")
            return
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"""
                    SELECT op, modelo, quantidade, inicio, fim, status, prioridade
                    FROM {schema}.planejamento_ops
                    WHERE id = %s
                    """,
                    (self.selected_op_id,),
                )
                row = cursor.fetchone()
            conn.commit()
            if not row:
                messagebox.showwarning("Planejamento", "OP não encontrada.")
                return
            self._abrir_form_op_dados(row)
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao carregar OP: {exc}")

    def _abrir_form_op_dados(self, dados=None):
        top = ctk.CTkToplevel(self)
        top.title("Planejamento de OP")
        top.grab_set()
        top.resizable(False, False)

        frame = ctk.CTkFrame(top)
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        frame.grid_columnconfigure(1, weight=1)

        def add_label(text, row):
            ctk.CTkLabel(frame, text=text).grid(row=row, column=0, sticky="w", pady=4)

        add_label("OP", 0)
        op_entry = ctk.CTkEntry(frame)
        op_entry.grid(row=0, column=1, sticky="ew", pady=4)

        add_label("Modelo", 1)
        modelo_entry = ctk.CTkEntry(frame)
        modelo_entry.grid(row=1, column=1, sticky="ew", pady=4)

        add_label("Quantidade", 2)
        qtd_entry = ctk.CTkEntry(frame)
        qtd_entry.grid(row=2, column=1, sticky="ew", pady=4)

        add_label("Início", 3)
        inicio_entry = ctk.CTkEntry(frame)
        inicio_entry.grid(row=3, column=1, sticky="ew", pady=4)
        ctk.CTkButton(
            frame, text="📅", width=32, command=lambda: self._abrir_calendario(inicio_entry)
        ).grid(row=3, column=2, padx=(6, 0))

        add_label("Fim", 4)
        fim_entry = ctk.CTkEntry(frame)
        fim_entry.grid(row=4, column=1, sticky="ew", pady=4)
        ctk.CTkButton(
            frame, text="📅", width=32, command=lambda: self._abrir_calendario(fim_entry)
        ).grid(row=4, column=2, padx=(6, 0))

        add_label("Status", 5)
        status_option = ctk.CTkOptionMenu(frame, values=["Planejada", "Em execução", "Concluída"])
        status_option.grid(row=5, column=1, sticky="w", pady=4)

        add_label("Prioridade", 6)
        prioridade_option = ctk.CTkOptionMenu(frame, values=["Alta", "Média", "Baixa"])
        prioridade_option.grid(row=6, column=1, sticky="w", pady=4)

        if dados:
            op_entry.insert(0, dados[0] or "")
            modelo_entry.insert(0, dados[1] or "")
            qtd_entry.insert(0, str(dados[2] or ""))
            if dados[3]:
                inicio_entry.insert(0, dados[3].strftime("%d/%m/%Y"))
            if dados[4]:
                fim_entry.insert(0, dados[4].strftime("%d/%m/%Y"))
            status_option.set(dados[5] or "Planejada")
            prioridade_option.set(dados[6] or "Média")

        def salvar():
            if not self._checar_tabela("planejamento_ops"):
                return
            op = op_entry.get().strip()
            inicio = self._parse_data(inicio_entry.get().strip())
            fim = self._parse_data(fim_entry.get().strip())
            try:
                quantidade = int(qtd_entry.get().strip() or 0)
            except ValueError:
                messagebox.showwarning("Planejamento", "Quantidade inválida.")
                return
            try:
                conn = get_conn()
                with conn.cursor() as cursor:
                    schema = get_schema()
                    if self.selected_op_id and dados:
                        cursor.execute(
                            f"""
                            UPDATE {schema}.planejamento_ops
                            SET op=%s, modelo=%s, quantidade=%s, inicio=%s, fim=%s,
                                status=%s, prioridade=%s, data_atualizacao=NOW()
                            WHERE id=%s
                            """,
                            (
                                op,
                                modelo_entry.get().strip(),
                                quantidade,
                                inicio,
                                fim,
                                status_option.get(),
                                prioridade_option.get(),
                                self.selected_op_id,
                            ),
                        )
                    else:
                        if not op:
                            op = self._gerar_op_sequencial(cursor, schema)
                        elif self._op_existe(cursor, schema, op):
                            messagebox.showwarning("Planejamento", "OP já existe. Use outra numeração.")
                            return
                        cursor.execute(
                            f"""
                            INSERT INTO {schema}.planejamento_ops
                            (op, modelo, quantidade, inicio, fim, status, prioridade, data_atualizacao)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                            """,
                            (
                                op,
                                modelo_entry.get().strip(),
                                quantidade,
                                inicio,
                                fim,
                                status_option.get(),
                                prioridade_option.get(),
                            ),
                        )
                conn.commit()
                self._carregar_dados()
                top.destroy()
            except Exception as exc:
                messagebox.showerror("Planejamento", f"Erro ao salvar OP: {exc}")

        ctk.CTkButton(frame, text="Salvar", command=salvar).grid(
            row=7, column=1, sticky="e", pady=(12, 0)
        )

    def _gerar_op_sequencial(self, cursor, schema):
        cursor.execute(
            f"""
            SELECT MAX(CAST(op AS INTEGER))
            FROM {schema}.planejamento_ops
            WHERE op ~ '^[0-9]+$'
            """
        )
        ultimo = cursor.fetchone()[0]
        proximo = (ultimo or 0) + 1
        return str(proximo)

    def _op_existe(self, cursor, schema, op):
        cursor.execute(
            f"""
            SELECT 1
            FROM {schema}.planejamento_ops
            WHERE op = %s
            LIMIT 1
            """,
            (op,),
        )
        return cursor.fetchone() is not None

    def _abrir_form_capacidade(self):
        top = ctk.CTkToplevel(self)
        top.title("Capacidade por Recurso")
        top.grab_set()
        top.resizable(False, False)

        frame = ctk.CTkFrame(top)
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Recurso").grid(row=0, column=0, sticky="w", pady=4)
        recurso_entry = ctk.CTkEntry(frame)
        recurso_entry.grid(row=0, column=1, sticky="ew", pady=4)

        ctk.CTkLabel(frame, text="Carga").grid(row=1, column=0, sticky="w", pady=4)
        carga_entry = ctk.CTkEntry(frame)
        carga_entry.grid(row=1, column=1, sticky="ew", pady=4)

        ctk.CTkLabel(frame, text="Capacidade").grid(row=2, column=0, sticky="w", pady=4)
        capacidade_entry = ctk.CTkEntry(frame)
        capacidade_entry.grid(row=2, column=1, sticky="ew", pady=4)

        def salvar():
            if not self._checar_tabela("planejamento_capacidade"):
                return
            recurso = recurso_entry.get().strip()
            if not recurso:
                messagebox.showwarning("Planejamento", "Informe o recurso.")
                return
            try:
                carga = float(carga_entry.get().replace(",", ".") or 0)
                capacidade = float(capacidade_entry.get().replace(",", ".") or 0)
            except ValueError:
                messagebox.showwarning("Planejamento", "Valores numéricos inválidos.")
                return
            ociosidade = max(capacidade - carga, 0)
            try:
                conn = get_conn()
                with conn.cursor() as cursor:
                    schema = get_schema()
                    cursor.execute(
                        f"""
                        INSERT INTO {schema}.planejamento_capacidade
                        (recurso, carga, capacidade, ociosidade, data_atualizacao)
                        VALUES (%s, %s, %s, %s, NOW())
                        """,
                        (recurso, carga, capacidade, ociosidade),
                    )
                conn.commit()
                self._carregar_dados()
                top.destroy()
            except Exception as exc:
                messagebox.showerror("Planejamento", f"Erro ao salvar capacidade: {exc}")

        ctk.CTkButton(frame, text="Salvar", command=salvar).grid(
            row=3, column=1, sticky="e", pady=(12, 0)
        )

    def _parse_data(self, texto):
        if not texto:
            return None
        try:
            return datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            return None

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
        y = altura - 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Planejamento de Produção")
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

        parent = entry.winfo_toplevel()

        def setar_data(d):
            entry.delete(0, "end")
            entry.insert(0, d.strftime("%d/%m/%Y"))
            top.destroy()

        top = ctk.CTkToplevel(parent)
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
        top.transient(parent)
        top.grab_set()
        top.lift()

        now = _dt.now()
        ano = now.year
        mes = now.month

        nav = ctk.CTkFrame(top)
        nav.pack(fill="x", padx=10, pady=5)

        meses_pt = [
            "",
            "Janeiro",
            "Fevereiro",
            "Março",
            "Abril",
            "Maio",
            "Junho",
            "Julho",
            "Agosto",
            "Setembro",
            "Outubro",
            "Novembro",
            "Dezembro",
        ]
        lbl_mes = ctk.CTkLabel(nav, text=f"{meses_pt[mes]} {ano}", font=("Arial", 14))
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
            lbl_mes.configure(text=f"{meses_pt[mes]} {ano}")
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
