# -*- coding: utf-8 -*-
"""
COMPRAS.py - Módulo de Compras
Interface para fornecedores, pedidos e recebimentos.
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
    def get_conn():
        raise RuntimeError("Módulo BANCO_DE_DADOS_PG não encontrado")

    def get_schema():
        return "opera"

    def require_ready(essentials=None):
        return False, "Módulo de banco de dados não disponível"


class ComprasPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.pedido_entries = {}
        self.recebimento_entries = {}
        self.fornecedor_entries = {}
        self.selected_pedido_id = None
        self.selected_recebimento_id = None
        self.selected_fornecedor_id = None
        self.tree_pedidos = None
        self.tree_recebimentos = None
        self.tree_fornecedores = None
        self._build()
        self._verificar_conexao()
        self.after(200, self._carregar_inicial)

    def _build(self):
        self.configure(fg_color="transparent")
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_tabs()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Módulo de Compras", font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Gestão de fornecedores, pedidos e recebimentos.",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(5, weight=1)

        ctk.CTkButton(toolbar, text="Novo Pedido", command=self._novo_pedido).grid(
            row=0, column=0, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Salvar", command=self._salvar_pedido).grid(
            row=0, column=1, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Aprovar", command=self._aprovar_pedido).grid(
            row=0, column=2, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Receber", command=self._marcar_recebido).grid(
            row=0, column=3, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Exportar PDF", command=self._exportar_compras).grid(
            row=0, column=4
        )
        ctk.CTkButton(toolbar, text="Imprimir", command=self._imprimir_compras).grid(
            row=0, column=5
        )

    def _build_tabs(self):
        tabs = ctk.CTkTabview(self)
        tabs.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))

        pedidos_tab = tabs.add("Pedidos de Compra")
        recebimento_tab = tabs.add("Recebimentos")
        fornecedores_tab = tabs.add("Fornecedores")

        self._build_pedidos_tab(pedidos_tab)
        self._build_recebimentos_tab(recebimento_tab)
        self._build_fornecedores_tab(fornecedores_tab)

    def _build_pedidos_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(3, weight=1)

        filters = ctk.CTkFrame(parent)
        filters.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        filters.grid_columnconfigure(8, weight=1)

        ctk.CTkLabel(filters, text="Período").grid(row=0, column=0, padx=(12, 6), pady=8)
        self.filter_inicio_entry = ctk.CTkEntry(filters, placeholder_text="De")
        self.filter_inicio_entry.grid(row=0, column=1, padx=(0, 6), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.filter_inicio_entry),
        ).grid(row=0, column=2, padx=(0, 6), pady=8)
        self.filter_fim_entry = ctk.CTkEntry(filters, placeholder_text="Até")
        self.filter_fim_entry.grid(row=0, column=3, padx=(0, 12), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.filter_fim_entry),
        ).grid(row=0, column=4, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Status").grid(row=0, column=5, padx=(0, 6), pady=8)
        ctk.CTkOptionMenu(filters, values=["Em aberto", "Aprovado", "Recebido", "Cancelado"]).grid(
            row=0, column=6, padx=(0, 12), pady=8
        )
        ctk.CTkEntry(filters, placeholder_text="Fornecedor ou item").grid(
            row=0, column=7, sticky="ew", padx=(0, 12), pady=8
        )
        ctk.CTkButton(filters, text="Filtrar").grid(row=0, column=8, padx=(0, 12), pady=8)

        form = ctk.CTkFrame(parent)
        form.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        form.grid_columnconfigure(6, weight=1)

        self._add_entry(form, "Fornecedor", self.pedido_entries, "fornecedor", 0, 0)
        self._add_entry(form, "Descrição", self.pedido_entries, "descricao", 0, 2)
        self._add_entry(form, "Valor total", self.pedido_entries, "valor_total", 0, 4)
        self._add_entry(form, "Entrega prevista", self.pedido_entries, "entrega_prevista", 0, 6)

        self._add_entry(form, "Status", self.pedido_entries, "status", 1, 0)
        self._add_entry(form, "Observações", self.pedido_entries, "observacoes", 1, 2)
        self.pedido_entries["entrega_prevista"].bind(
            "<Double-Button-1>",
            lambda e: self._abrir_calendario(self.pedido_entries["entrega_prevista"]),
        )

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        ctk.CTkButton(actions, text="Novo", command=self._novo_pedido).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(actions, text="Salvar", command=self._salvar_pedido).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(actions, text="Cancelar", command=self._novo_pedido).grid(row=0, column=2)

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 16))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree_pedidos = ttk.Treeview(
            tree_frame,
            columns=("id", "data", "fornecedor", "valor", "status", "entrega"),
            show="headings",
            height=10,
        )
        for col, text, width in (
            ("id", "Pedido", 80),
            ("data", "Data", 110),
            ("fornecedor", "Fornecedor", 220),
            ("valor", "Valor", 120),
            ("status", "Status", 120),
            ("entrega", "Entrega Prevista", 140),
        ):
            self.tree_pedidos.heading(col, text=text)
            self.tree_pedidos.column(col, width=width)
        self.tree_pedidos.column("id", anchor="center")
        self.tree_pedidos.column("valor", anchor="e")
        self.tree_pedidos.bind("<<TreeviewSelect>>", self._selecionar_pedido)

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_pedidos.yview)
        self.tree_pedidos.configure(yscrollcommand=tree_scroll.set)
        self.tree_pedidos.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    def _build_recebimentos_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        info = ctk.CTkFrame(parent)
        info.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        info.grid_columnconfigure(6, weight=1)

        self._add_entry(info, "NF / Documento", self.recebimento_entries, "numero_nf", 0, 0)
        self._add_entry(info, "Pedido (ID)", self.recebimento_entries, "pedido_id", 0, 2)
        self._add_entry(info, "Fornecedor", self.recebimento_entries, "fornecedor", 0, 4)
        self._add_entry(info, "Valor", self.recebimento_entries, "valor_total", 1, 0)
        self._add_entry(info, "Data recebimento", self.recebimento_entries, "data_recebimento", 1, 2)
        self._add_entry(info, "Status", self.recebimento_entries, "status", 1, 4)
        self.recebimento_entries["data_recebimento"].bind(
            "<Double-Button-1>",
            lambda e: self._abrir_calendario(self.recebimento_entries["data_recebimento"]),
        )
        ctk.CTkButton(info, text="Registrar Recebimento", command=self._salvar_recebimento).grid(
            row=0, column=6, padx=(12, 12), pady=8, rowspan=2, sticky="ns"
        )

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree_recebimentos = ttk.Treeview(
            tree_frame,
            columns=("nf", "pedido", "fornecedor", "data", "valor", "status"),
            show="headings",
            height=10,
        )
        for col, text, width in (
            ("nf", "NF", 90),
            ("pedido", "Pedido", 90),
            ("fornecedor", "Fornecedor", 220),
            ("data", "Recebimento", 120),
            ("valor", "Valor", 120),
            ("status", "Status", 120),
        ):
            self.tree_recebimentos.heading(col, text=text)
            self.tree_recebimentos.column(col, width=width)
        self.tree_recebimentos.column("valor", anchor="e")
        self.tree_recebimentos.bind("<<TreeviewSelect>>", self._selecionar_recebimento)

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_recebimentos.yview)
        self.tree_recebimentos.configure(yscrollcommand=tree_scroll.set)
        self.tree_recebimentos.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    def _build_fornecedores_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(parent)
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        toolbar.grid_columnconfigure(6, weight=1)
        ctk.CTkButton(toolbar, text="Novo Fornecedor", command=self._novo_fornecedor).grid(
            row=0, column=0, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Salvar", command=self._salvar_fornecedor).grid(
            row=0, column=1, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Inativar", command=self._inativar_fornecedor).grid(
            row=0, column=2, padx=(0, 8)
        )
        self.search_fornecedor = ctk.CTkEntry(toolbar, placeholder_text="Buscar fornecedor")
        self.search_fornecedor.grid(row=0, column=4, sticky="ew", padx=(12, 12))
        ctk.CTkButton(toolbar, text="Filtrar", command=self._carregar_fornecedores).grid(
            row=0, column=5
        )

        form = ctk.CTkFrame(parent)
        form.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        form.grid_columnconfigure(6, weight=1)
        self._add_entry(form, "Nome", self.fornecedor_entries, "nome", 0, 0)
        self._add_entry(form, "Categoria", self.fornecedor_entries, "categoria", 0, 2)
        self._add_entry(form, "Contato", self.fornecedor_entries, "contato", 0, 4)
        self._add_entry(form, "Telefone", self.fornecedor_entries, "telefone", 1, 0)
        self._add_entry(form, "Email", self.fornecedor_entries, "email", 1, 2)
        self._add_entry(form, "Prazo médio (dias)", self.fornecedor_entries, "prazo_medio", 1, 4)
        self._add_entry(form, "Status", self.fornecedor_entries, "status", 2, 0)
        self._add_entry(form, "Observações", self.fornecedor_entries, "observacoes", 2, 2)

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree_fornecedores = ttk.Treeview(
            tree_frame,
            columns=("fornecedor", "categoria", "contato", "prazo", "status"),
            show="headings",
            height=10,
        )
        for col, text, width in (
            ("fornecedor", "Fornecedor", 220),
            ("categoria", "Categoria", 160),
            ("contato", "Contato", 160),
            ("prazo", "Prazo Médio", 120),
            ("status", "Status", 120),
        ):
            self.tree_fornecedores.heading(col, text=text)
            self.tree_fornecedores.column(col, width=width)
        self.tree_fornecedores.bind("<<TreeviewSelect>>", self._selecionar_fornecedor)

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_fornecedores.yview)
        self.tree_fornecedores.configure(yscrollcommand=tree_scroll.set)
        self.tree_fornecedores.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    def _add_entry(self, parent, label, store, key, row, column):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=column, padx=(12, 6), pady=6, sticky="w")
        entry = ctk.CTkEntry(parent)
        entry.grid(row=row, column=column + 1, padx=(0, 12), pady=6, sticky="ew")
        store[key] = entry

    def _verificar_conexao(self):
        try:
            ok, msg = require_ready()
            if not ok:
                messagebox.showwarning("Banco de dados", msg)
        except Exception as exc:
            messagebox.showwarning("Banco de dados", f"Não foi possível validar o banco: {exc}")

    def _carregar_inicial(self):
        self._carregar_fornecedores()
        self._carregar_pedidos()
        self._carregar_recebimentos()

    def _novo_fornecedor(self):
        for entry in self.fornecedor_entries.values():
            entry.delete(0, "end")
        self.selected_fornecedor_id = None

    def _novo_pedido(self):
        for entry in self.pedido_entries.values():
            entry.delete(0, "end")
        self.selected_pedido_id = None

    def _novo_recebimento(self):
        for entry in self.recebimento_entries.values():
            entry.delete(0, "end")
        self.selected_recebimento_id = None

    def _carregar_fornecedores(self):
        if not self.tree_fornecedores:
            return
        self.tree_fornecedores.delete(*self.tree_fornecedores.get_children())
        termo = self.search_fornecedor.get().strip() if hasattr(self, "search_fornecedor") else ""
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                params = []
                where_clause = ""
                if termo:
                    where_clause = "WHERE nome ILIKE %s"
                    params.append(f"%{termo}%")
                cursor.execute(
                    f"""
                    SELECT id, nome, categoria, contato, prazo_medio, status
                    FROM {schema}.compras_fornecedores
                    {where_clause}
                    ORDER BY nome
                    """,
                    params,
                )
                for row in cursor.fetchall():
                    self.tree_fornecedores.insert(
                        "",
                        "end",
                        iid=row[0],
                        values=(row[1], row[2] or "", row[3] or "", row[4] or 0, row[5] or ""),
                    )
            conn.commit()
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao carregar fornecedores: {exc}")

    def _salvar_fornecedor(self):
        nome = self.fornecedor_entries.get("nome").get().strip()
        if not nome:
            messagebox.showwarning("Compras", "Informe o nome do fornecedor.")
            return
        dados = {key: entry.get().strip() for key, entry in self.fornecedor_entries.items()}
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                if self.selected_fornecedor_id:
                    cursor.execute(
                        f"""
                        UPDATE {schema}.compras_fornecedores
                        SET nome=%s, categoria=%s, contato=%s, telefone=%s, email=%s,
                            prazo_medio=%s, status=%s, observacoes=%s, data_atualizacao=NOW()
                        WHERE id=%s
                        """,
                        (
                            dados.get("nome"),
                            dados.get("categoria"),
                            dados.get("contato"),
                            dados.get("telefone"),
                            dados.get("email"),
                            dados.get("prazo_medio") or 0,
                            dados.get("status") or "Ativo",
                            dados.get("observacoes"),
                            self.selected_fornecedor_id,
                        ),
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT INTO {schema}.compras_fornecedores
                        (nome, categoria, contato, telefone, email, prazo_medio, status, observacoes, data_atualizacao)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            dados.get("nome"),
                            dados.get("categoria"),
                            dados.get("contato"),
                            dados.get("telefone"),
                            dados.get("email"),
                            dados.get("prazo_medio") or 0,
                            dados.get("status") or "Ativo",
                            dados.get("observacoes"),
                        ),
                    )
            conn.commit()
            self._novo_fornecedor()
            self._carregar_fornecedores()
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao salvar fornecedor: {exc}")

    def _inativar_fornecedor(self):
        if not self.selected_fornecedor_id:
            messagebox.showwarning("Compras", "Selecione um fornecedor.")
            return
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"""
                    UPDATE {schema}.compras_fornecedores
                    SET status='Inativo', data_atualizacao=NOW()
                    WHERE id=%s
                    """,
                    (self.selected_fornecedor_id,),
                )
            conn.commit()
            self._novo_fornecedor()
            self._carregar_fornecedores()
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao inativar fornecedor: {exc}")

    def _selecionar_fornecedor(self, _event=None):
        if not self.tree_fornecedores:
            return
        selecionado = self.tree_fornecedores.selection()
        if not selecionado:
            return
        fornecedor_id = selecionado[0]
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"""
                    SELECT id, nome, categoria, contato, telefone, email, prazo_medio, status, observacoes
                    FROM {schema}.compras_fornecedores
                    WHERE id=%s
                    """,
                    (fornecedor_id,),
                )
                row = cursor.fetchone()
            conn.commit()
            if row:
                self.selected_fornecedor_id = row[0]
                keys = [
                    "nome",
                    "categoria",
                    "contato",
                    "telefone",
                    "email",
                    "prazo_medio",
                    "status",
                    "observacoes",
                ]
                for key, value in zip(keys, row[1:]):
                    entry = self.fornecedor_entries.get(key)
                    if entry:
                        entry.delete(0, "end")
                        entry.insert(0, value or "")
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao carregar fornecedor: {exc}")

    def _carregar_pedidos(self):
        if not self.tree_pedidos:
            return
        self.tree_pedidos.delete(*self.tree_pedidos.get_children())
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"""
                    SELECT p.id, p.data_pedido, f.nome, p.valor_total, p.status, p.entrega_prevista
                    FROM {schema}.compras_pedidos p
                    LEFT JOIN {schema}.compras_fornecedores f ON f.id = p.fornecedor_id
                    ORDER BY p.data_pedido DESC
                    """
                )
                for row in cursor.fetchall():
                    data = row[1].strftime("%d/%m/%Y") if row[1] else ""
                    entrega = row[5].strftime("%d/%m/%Y") if row[5] else ""
                    self.tree_pedidos.insert(
                        "", "end", values=(row[0], data, row[2] or "", row[3] or 0, row[4] or "", entrega)
                    )
            conn.commit()
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao carregar pedidos: {exc}")

    def _salvar_pedido(self):
        fornecedor = self.pedido_entries.get("fornecedor").get().strip()
        if not fornecedor:
            messagebox.showwarning("Compras", "Informe o fornecedor.")
            return
        dados = {key: entry.get().strip() for key, entry in self.pedido_entries.items()}
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"SELECT id FROM {schema}.compras_fornecedores WHERE nome=%s ORDER BY id DESC LIMIT 1",
                    (fornecedor,),
                )
                fornecedor_id = cursor.fetchone()
                fornecedor_id = fornecedor_id[0] if fornecedor_id else None
                entrega = self._parse_date(dados.get("entrega_prevista"))
                if self.selected_pedido_id:
                    cursor.execute(
                        f"""
                        UPDATE {schema}.compras_pedidos
                        SET fornecedor_id=%s, descricao=%s, valor_total=%s, status=%s,
                            entrega_prevista=%s, observacoes=%s, data_atualizacao=NOW()
                        WHERE id=%s
                        """,
                        (
                            fornecedor_id,
                            dados.get("descricao"),
                            self._parse_numeric(dados.get("valor_total")),
                            dados.get("status") or "Em aberto",
                            entrega,
                            dados.get("observacoes"),
                            self.selected_pedido_id,
                        ),
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT INTO {schema}.compras_pedidos
                        (fornecedor_id, descricao, valor_total, status, entrega_prevista, observacoes, data_atualizacao)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            fornecedor_id,
                            dados.get("descricao"),
                            self._parse_numeric(dados.get("valor_total")),
                            dados.get("status") or "Em aberto",
                            entrega,
                            dados.get("observacoes"),
                        ),
                    )
            conn.commit()
            self._novo_pedido()
            self._carregar_pedidos()
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao salvar pedido: {exc}")

    def _selecionar_pedido(self, _event=None):
        if not self.tree_pedidos:
            return
        selecionado = self.tree_pedidos.selection()
        if not selecionado:
            return
        item = self.tree_pedidos.item(selecionado[0])
        pedido_id = item["values"][0]
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"""
                    SELECT p.id, f.nome, p.descricao, p.valor_total, p.status, p.entrega_prevista, p.observacoes
                    FROM {schema}.compras_pedidos p
                    LEFT JOIN {schema}.compras_fornecedores f ON f.id = p.fornecedor_id
                    WHERE p.id=%s
                    """,
                    (pedido_id,),
                )
                row = cursor.fetchone()
            conn.commit()
            if row:
                self.selected_pedido_id = row[0]
                mapping = {
                    "fornecedor": row[1],
                    "descricao": row[2],
                    "valor_total": row[3],
                    "status": row[4],
                    "entrega_prevista": row[5].strftime("%d/%m/%Y") if row[5] else "",
                    "observacoes": row[6],
                }
                for key, value in mapping.items():
                    entry = self.pedido_entries.get(key)
                    if entry:
                        entry.delete(0, "end")
                        entry.insert(0, value or "")
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao carregar pedido: {exc}")

    def _aprovar_pedido(self):
        if not self.selected_pedido_id:
            messagebox.showwarning("Compras", "Selecione um pedido.")
            return
        self._atualizar_status_pedido("Aprovado")

    def _marcar_recebido(self):
        if not self.selected_pedido_id:
            messagebox.showwarning("Compras", "Selecione um pedido.")
            return
        self._atualizar_status_pedido("Recebido")

    def _atualizar_status_pedido(self, status):
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"""
                    UPDATE {schema}.compras_pedidos
                    SET status=%s, data_atualizacao=NOW()
                    WHERE id=%s
                    """,
                    (status, self.selected_pedido_id),
                )
            conn.commit()
            self._carregar_pedidos()
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao atualizar pedido: {exc}")

    def _carregar_recebimentos(self):
        if not self.tree_recebimentos:
            return
        self.tree_recebimentos.delete(*self.tree_recebimentos.get_children())
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"""
                    SELECT r.id, r.numero_nf, r.pedido_id, f.nome, r.data_recebimento, r.valor_total, r.status
                    FROM {schema}.compras_recebimentos r
                    LEFT JOIN {schema}.compras_fornecedores f ON f.id = r.fornecedor_id
                    ORDER BY r.data_recebimento DESC
                    """
                )
                for row in cursor.fetchall():
                    data = row[4].strftime("%d/%m/%Y") if row[4] else ""
                    self.tree_recebimentos.insert(
                        "",
                        "end",
                        iid=row[0],
                        values=(row[1] or "", row[2] or "", row[3] or "", data, row[5] or 0, row[6] or ""),
                    )
            conn.commit()
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao carregar recebimentos: {exc}")

    def _salvar_recebimento(self):
        numero_nf = self.recebimento_entries.get("numero_nf").get().strip()
        if not numero_nf:
            messagebox.showwarning("Compras", "Informe o número da NF.")
            return
        dados = {key: entry.get().strip() for key, entry in self.recebimento_entries.items()}
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"SELECT id FROM {schema}.compras_fornecedores WHERE nome=%s ORDER BY id DESC LIMIT 1",
                    (dados.get("fornecedor"),),
                )
                fornecedor_id = cursor.fetchone()
                fornecedor_id = fornecedor_id[0] if fornecedor_id else None
                data_recebimento = self._parse_date(dados.get("data_recebimento"))
                if self.selected_recebimento_id:
                    cursor.execute(
                        f"""
                        UPDATE {schema}.compras_recebimentos
                        SET pedido_id=%s, fornecedor_id=%s, numero_nf=%s, data_recebimento=%s,
                            valor_total=%s, status=%s, data_atualizacao=NOW()
                        WHERE id=%s
                        """,
                        (
                            self._parse_int(dados.get("pedido_id")),
                            fornecedor_id,
                            dados.get("numero_nf"),
                            data_recebimento,
                            self._parse_numeric(dados.get("valor_total")),
                            dados.get("status") or "Recebido",
                            self.selected_recebimento_id,
                        ),
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT INTO {schema}.compras_recebimentos
                        (pedido_id, fornecedor_id, numero_nf, data_recebimento, valor_total, status, data_atualizacao)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            self._parse_int(dados.get("pedido_id")),
                            fornecedor_id,
                            dados.get("numero_nf"),
                            data_recebimento,
                            self._parse_numeric(dados.get("valor_total")),
                            dados.get("status") or "Recebido",
                        ),
                    )
            conn.commit()
            self._novo_recebimento()
            self._carregar_recebimentos()
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao salvar recebimento: {exc}")

    def _selecionar_recebimento(self, _event=None):
        if not self.tree_recebimentos:
            return
        selecionado = self.tree_recebimentos.selection()
        if not selecionado:
            return
        recebimento_id = selecionado[0]
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"""
                    SELECT r.id, r.numero_nf, r.pedido_id, f.nome, r.data_recebimento, r.valor_total, r.status
                    FROM {schema}.compras_recebimentos r
                    LEFT JOIN {schema}.compras_fornecedores f ON f.id = r.fornecedor_id
                    WHERE r.id=%s
                    """,
                    (recebimento_id,),
                )
                row = cursor.fetchone()
            conn.commit()
            if row:
                self.selected_recebimento_id = row[0]
                mapping = {
                    "numero_nf": row[1],
                    "pedido_id": row[2],
                    "fornecedor": row[3],
                    "data_recebimento": row[4].strftime("%d/%m/%Y") if row[4] else "",
                    "valor_total": row[5],
                    "status": row[6],
                }
                for key, value in mapping.items():
                    entry = self.recebimento_entries.get(key)
                    if entry:
                        entry.delete(0, "end")
                        entry.insert(0, value or "")
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao carregar recebimento: {exc}")

    def _parse_date(self, text):
        if not text:
            return None
        try:
            return datetime.strptime(text, "%d/%m/%Y").date()
        except ValueError:
            return None

    def _parse_numeric(self, text):
        try:
            return float(str(text).replace(",", "."))
        except Exception:
            return 0

    def _parse_int(self, text):
        try:
            return int(text)
        except Exception:
            return None

    def _exportar_compras(self):
        try:
            caminho = self._gerar_pdf_compras()
            self._abrir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao exportar PDF: {exc}")

    def _imprimir_compras(self):
        try:
            caminho = self._gerar_pdf_compras()
            self._imprimir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("Compras", f"Erro ao imprimir: {exc}")

    def _gerar_pdf_compras(self):
        nome = f"compras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        caminho = os.path.abspath(nome)
        c = canvas.Canvas(caminho, pagesize=A4)
        largura, altura = A4
        y = altura - 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Relatório de Compras")
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

        if self.tree_fornecedores:
            escrever_titulo("Fornecedores")
            linhas = []
            for item in self.tree_fornecedores.get_children():
                vals = self.tree_fornecedores.item(item)["values"]
                linhas.append(f"- {vals[0]} | {vals[1]} | {vals[2]} | Prazo {vals[3]} | {vals[4]}")
            escrever_linhas(linhas or ["Sem dados."])
            y -= 8

        if self.tree_pedidos:
            escrever_titulo("Pedidos de Compra")
            linhas = []
            for item in self.tree_pedidos.get_children():
                vals = self.tree_pedidos.item(item)["values"]
                linhas.append(f"- #{vals[0]} | {vals[2]} | R$ {vals[3]} | {vals[4]} | Entrega {vals[5]}")
            escrever_linhas(linhas or ["Sem dados."])
            y -= 8

        if self.tree_recebimentos:
            escrever_titulo("Recebimentos")
            linhas = []
            for item in self.tree_recebimentos.get_children():
                vals = self.tree_recebimentos.item(item)["values"]
                linhas.append(f"- NF {vals[0]} | Pedido {vals[1]} | {vals[2]} | {vals[3]} | R$ {vals[4]}")
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
        messagebox.showinfo("Compras", "PDF aberto no navegador. Use Ctrl+P para imprimir.")

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
    app.title("Compras - Teste")
    app.geometry("1200x720")
    page = ComprasPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()