# -*- coding: utf-8 -*-
"""
COMPRAS.py - Módulo de Compras
Interface base para fornecedores, pedidos e recebimentos.
"""
from tkinter import ttk

import customtkinter as ctk


class ComprasPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self._build()

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

        ctk.CTkButton(toolbar, text="Novo Pedido").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Salvar").grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Aprovar").grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Receber").grid(row=0, column=3, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Exportar").grid(row=0, column=4)

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
        parent.grid_rowconfigure(2, weight=1)

        filters = ctk.CTkFrame(parent)
        filters.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        filters.grid_columnconfigure(6, weight=1)

        ctk.CTkLabel(filters, text="Período").grid(row=0, column=0, padx=(12, 6), pady=8)
        ctk.CTkEntry(filters, placeholder_text="De").grid(row=0, column=1, padx=(0, 6), pady=8)
        ctk.CTkEntry(filters, placeholder_text="Até").grid(row=0, column=2, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Status").grid(row=0, column=3, padx=(0, 6), pady=8)
        ctk.CTkOptionMenu(filters, values=["Em aberto", "Aprovado", "Recebido", "Cancelado"]).grid(
            row=0, column=4, padx=(0, 12), pady=8
        )
        ctk.CTkEntry(filters, placeholder_text="Fornecedor ou item").grid(
            row=0, column=5, sticky="ew", padx=(0, 12), pady=8
        )
        ctk.CTkButton(filters, text="Filtrar").grid(row=0, column=6, padx=(0, 12), pady=8)

        summary = ctk.CTkFrame(parent)
        summary.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        summary.grid_columnconfigure((0, 1, 2), weight=1)
        for idx, text in enumerate(
            ["Pedidos em aberto: 0", "Valor em negociação: R$ 0,00", "Lead time médio: 0 dias"]
        ):
            card = ctk.CTkFrame(summary)
            card.grid(row=0, column=idx, padx=6, sticky="ew")
            ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=12, weight="bold")).pack(
                pady=12
            )

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        tree = ttk.Treeview(
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
            tree.heading(col, text=text)
            tree.column(col, width=width)
        tree.column("id", anchor="center")
        tree.column("valor", anchor="e")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    def _build_recebimentos_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        info = ctk.CTkFrame(parent)
        info.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        info.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(info, text="NF / Documento").grid(row=0, column=0, padx=(12, 6), pady=8)
        ctk.CTkEntry(info, placeholder_text="Número da NF").grid(row=0, column=1, padx=(0, 12), pady=8)
        ctk.CTkLabel(info, text="Fornecedor").grid(row=0, column=2, padx=(0, 6), pady=8)
        ctk.CTkEntry(info, placeholder_text="Buscar fornecedor").grid(
            row=0, column=3, padx=(0, 12), pady=8
        )
        ctk.CTkButton(info, text="Registrar Recebimento").grid(
            row=0, column=5, padx=(0, 12), pady=8
        )

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        tree = ttk.Treeview(
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
            tree.heading(col, text=text)
            tree.column(col, width=width)
        tree.column("valor", anchor="e")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    def _build_fornecedores_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(parent)
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        toolbar.grid_columnconfigure(3, weight=1)
        ctk.CTkButton(toolbar, text="Novo Fornecedor").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Atualizar Cadastro").grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Avaliar").grid(row=0, column=2, padx=(0, 8))
        ctk.CTkEntry(toolbar, placeholder_text="Buscar fornecedor").grid(
            row=0, column=4, sticky="ew", padx=(12, 0)
        )

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        tree = ttk.Treeview(
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
            tree.heading(col, text=text)
            tree.column(col, width=width)

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Compras - Teste")
    app.geometry("1200x720")
    page = ComprasPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()