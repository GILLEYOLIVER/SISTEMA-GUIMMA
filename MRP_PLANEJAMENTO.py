# -*- coding: utf-8 -*-
"""
MRP_PLANEJAMENTO.py - Módulo MRP
Interface base para cálculo de necessidades de materiais.
"""
from tkinter import ttk

import customtkinter as ctk


class MRPPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self._build()

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

        ctk.CTkButton(toolbar, text="Gerar MRP").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Simular").grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Aprovar Compra").grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Exportar").grid(row=0, column=3, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Configurações").grid(row=0, column=4)

    def _build_filters(self):
        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(7, weight=1)

        ctk.CTkLabel(filters, text="Período").grid(row=0, column=0, padx=(12, 6), pady=8)
        ctk.CTkEntry(filters, placeholder_text="De").grid(row=0, column=1, padx=(0, 6), pady=8)
        ctk.CTkEntry(filters, placeholder_text="Até").grid(row=0, column=2, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Coleção").grid(row=0, column=3, padx=(0, 6), pady=8)
        ctk.CTkOptionMenu(filters, values=["Todas", "Linha Básica", "Coleção 2026"]).grid(
            row=0, column=4, padx=(0, 12), pady=8
        )
        ctk.CTkLabel(filters, text="Status").grid(row=0, column=5, padx=(0, 6), pady=8)
        ctk.CTkOptionMenu(filters, values=["Crítico", "Atenção", "OK", "Todos"]).grid(
            row=0, column=6, padx=(0, 12), pady=8
        )
        ctk.CTkButton(filters, text="Filtrar").grid(row=0, column=8, padx=(0, 12), pady=8)

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
            ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=12, weight="bold")).pack(
                pady=12
            )

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

        tree = ttk.Treeview(
            tree_frame,
            columns=("insumo", "sku", "necessario", "estoque", "faltante", "lead", "fornecedor"),
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
        ):
            tree.heading(col, text=text)
            tree.column(col, width=width)
        tree.column("necessario", anchor="e")
        tree.column("estoque", anchor="e")
        tree.column("faltante", anchor="e")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
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
        ctk.CTkButton(info, text="Converter em Pedido").grid(row=0, column=2, padx=12, pady=8)

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        tree = ttk.Treeview(
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
            tree.heading(col, text=text)
            tree.column(col, width=width)
        tree.column("quantidade", anchor="e")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    def _build_fornecedores_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        tree = ttk.Treeview(
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
            tree.heading(col, text=text)
            tree.column(col, width=width)

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("MRP - Teste")
    app.geometry("1200x720")
    page = MRPPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()