# -*- coding: utf-8 -*-
"""
RELATORIO_CUSTOS_REAIS.py - Relatório de Custos Reais
Interface base para análise de custos planejados x realizados.
"""
from tkinter import ttk

import customtkinter as ctk


class RelatorioCustosReaisPage(ctk.CTkFrame):
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
        self._build_body()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Relatório de Custos Reais", font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Comparativo de custos planejados e realizados por OP e categoria.",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(4, weight=1)

        ctk.CTkButton(toolbar, text="Atualizar").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Exportar").grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Imprimir").grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Comparar OPs").grid(row=0, column=3)

    def _build_filters(self):
        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(7, weight=1)

        ctk.CTkLabel(filters, text="Período").grid(row=0, column=0, padx=(12, 6), pady=8)
        ctk.CTkEntry(filters, placeholder_text="De").grid(row=0, column=1, padx=(0, 6), pady=8)
        ctk.CTkEntry(filters, placeholder_text="Até").grid(row=0, column=2, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Modelo").grid(row=0, column=3, padx=(0, 6), pady=8)
        ctk.CTkEntry(filters, placeholder_text="Buscar modelo").grid(
            row=0, column=4, padx=(0, 12), pady=8
        )
        ctk.CTkLabel(filters, text="Status").grid(row=0, column=5, padx=(0, 6), pady=8)
        ctk.CTkOptionMenu(filters, values=["Todos", "Em produção", "Finalizado"]).grid(
            row=0, column=6, padx=(0, 12), pady=8
        )
        ctk.CTkButton(filters, text="Filtrar").grid(row=0, column=8, padx=(0, 12), pady=8)

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
            [
                "Custo planejado: R$ 0,00",
                "Custo real: R$ 0,00",
                "Variação: 0,0%",
                "Margem estimada: R$ 0,00",
            ]
        ):
            card = ctk.CTkFrame(kpis)
            card.grid(row=0, column=idx, padx=6, sticky="ew")
            ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=12, weight="bold")).pack(
                pady=12
            )

        comparativo_frame = ctk.CTkFrame(body)
        comparativo_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        comparativo_frame.grid_columnconfigure(0, weight=1)
        comparativo_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            comparativo_frame, text="Comparativo por Categoria", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        tree = ttk.Treeview(
            comparativo_frame,
            columns=("categoria", "planejado", "real", "variacao"),
            show="headings",
            height=12,
        )
        for col, text, width in (
            ("categoria", "Categoria", 200),
            ("planejado", "Planejado", 120),
            ("real", "Real", 120),
            ("variacao", "Variação", 100),
        ):
            tree.heading(col, text=text)
            tree.column(col, width=width)
        tree.column("planejado", anchor="e")
        tree.column("real", anchor="e")
        tree.column("variacao", anchor="e")

        tree_scroll = ttk.Scrollbar(comparativo_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        tree_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16))

        detalhe_frame = ctk.CTkFrame(body)
        detalhe_frame.grid(row=1, column=1, sticky="nsew")
        detalhe_frame.grid_columnconfigure(0, weight=1)
        detalhe_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            detalhe_frame, text="Detalhes por OP", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        detalhe_tree = ttk.Treeview(
            detalhe_frame,
            columns=("op", "modelo", "planejado", "real"),
            show="headings",
            height=10,
        )
        for col, text, width in (
            ("op", "OP", 90),
            ("modelo", "Modelo", 160),
            ("planejado", "Planejado", 110),
            ("real", "Real", 110),
        ):
            detalhe_tree.heading(col, text=text)
            detalhe_tree.column(col, width=width)
        detalhe_tree.column("planejado", anchor="e")
        detalhe_tree.column("real", anchor="e")

        detalhe_scroll = ttk.Scrollbar(detalhe_frame, orient="vertical", command=detalhe_tree.yview)
        detalhe_tree.configure(yscrollcommand=detalhe_scroll.set)
        detalhe_tree.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        detalhe_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16))


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Custos Reais - Teste")
    app.geometry("1200x720")
    page = RelatorioCustosReaisPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()