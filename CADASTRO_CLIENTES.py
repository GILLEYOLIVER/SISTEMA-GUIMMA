# -*- coding: utf-8 -*-
"""
CADASTRO_CLIENTES.py - Módulo de Clientes
Interface base para cadastro, consulta e relacionamento de clientes.
"""
from tkinter import ttk

import customtkinter as ctk


class ClientesPage(ctk.CTkFrame):
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
            header,
            text="Cadastro de Clientes",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Gestão de contatos, endereços e vínculos para pedidos e relatórios.",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(3, weight=1)

        ctk.CTkButton(toolbar, text="Novo Cliente").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Salvar").grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Inativar").grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Exportar").grid(row=0, column=4)

    def _build_filters(self):
        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(filters, text="Pesquisar").grid(row=0, column=0, padx=(12, 6), pady=10)
        ctk.CTkEntry(filters, placeholder_text="Nome, documento, telefone ou e-mail").grid(
            row=0, column=1, sticky="ew", padx=(0, 12), pady=10
        )
        ctk.CTkLabel(filters, text="Status").grid(row=0, column=2, padx=(0, 6), pady=10)
        ctk.CTkOptionMenu(filters, values=["Ativo", "Inativo", "Todos"]).grid(
            row=0, column=3, padx=(0, 12), pady=10
        )
        ctk.CTkButton(filters, text="Filtrar").grid(row=0, column=5, padx=(0, 12), pady=10)

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 24))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        form_frame = ctk.CTkFrame(body)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        form_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form_frame, text="Dados do Cliente", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        form_fields = ctk.CTkFrame(form_frame, fg_color="transparent")
        form_fields.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        form_fields.grid_columnconfigure(0, weight=1)

        self._add_entry(form_fields, "Razão Social / Nome", 0)
        self._add_entry(form_fields, "CPF / CNPJ", 1)
        self._add_entry(form_fields, "Inscrição Estadual", 2)
        self._add_entry(form_fields, "E-mail", 3)
        self._add_entry(form_fields, "Telefone", 4)
        self._add_entry(form_fields, "WhatsApp", 5)
        self._add_entry(form_fields, "Endereço", 6)
        self._add_entry(form_fields, "Bairro", 7)
        self._add_entry(form_fields, "Cidade", 8)
        self._add_entry(form_fields, "UF", 9)
        self._add_entry(form_fields, "CEP", 10)
        self._add_entry(form_fields, "Segmento / Canal", 11)
        self._add_entry(form_fields, "Observações", 12, height=80, multiline=True)

        list_frame = ctk.CTkFrame(body)
        list_frame.grid(row=0, column=1, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            list_frame, text="Clientes Cadastrados", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        tree = ttk.Treeview(
            list_frame,
            columns=("id", "nome", "documento", "cidade", "status", "ultima_compra"),
            show="headings",
            height=12,
        )
        tree.heading("id", text="ID")
        tree.heading("nome", text="Nome")
        tree.heading("documento", text="Documento")
        tree.heading("cidade", text="Cidade")
        tree.heading("status", text="Status")
        tree.heading("ultima_compra", text="Última Compra")
        tree.column("id", width=60, anchor="center")
        tree.column("nome", width=220)
        tree.column("documento", width=140)
        tree.column("cidade", width=140)
        tree.column("status", width=90, anchor="center")
        tree.column("ultima_compra", width=120, anchor="center")

        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        tree_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16))

        summary = ctk.CTkFrame(list_frame)
        summary.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        summary.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            summary,
            text="Resumo: 0 clientes ativos • Receita anual R$ 0,00 • Ticket médio R$ 0,00",
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=8)

    def _add_entry(self, parent, label, row, height=None, multiline=False):
        ctk.CTkLabel(parent, text=label).grid(row=row * 2, column=0, sticky="w", pady=(0, 2))
        if multiline:
            entry = ctk.CTkTextbox(parent, height=height or 80)
        else:
            entry = ctk.CTkEntry(parent)
        entry.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 8))


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Clientes - Teste")
    app.geometry("1100x720")
    page = ClientesPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()
