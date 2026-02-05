# -*- coding: utf-8 -*-
"""
CADASTRO_CLIENTES.py - Módulo de Clientes
Interface base para cadastro, consulta e relacionamento de clientes.
"""
from tkinter import messagebox, ttk

import customtkinter as ctk

try:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception:
    def get_conn():
        raise RuntimeError("Módulo BANCO_DE_DADOS_PG não encontrado")

    def get_schema():
        return "opera"

    def require_ready(essentials=None):
        return False, "Módulo de banco de dados não disponível"


class ClientesPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.entries = {}
        self.tree = None
        self.summary_label = None
        self.selected_id = None
        self._build()
        self._verificar_conexao()
        self.after(200, self._carregar_clientes)

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

        ctk.CTkButton(toolbar, text="Novo Cliente", command=self._limpar_formulario).grid(
            row=0, column=0, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Salvar", command=self._salvar_cliente).grid(
            row=0, column=1, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Inativar", command=self._inativar_cliente).grid(
            row=0, column=2, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Exportar", command=self._exportar_cliente).grid(
            row=0, column=4
        )

    def _build_filters(self):
        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(filters, text="Pesquisar").grid(row=0, column=0, padx=(12, 6), pady=10)
        ctk.CTkLabel(filters, text="Status").grid(row=0, column=2, padx=(0, 6), pady=10)
        self.filter_status = ctk.CTkOptionMenu(filters, values=["Ativo", "Inativo", "Todos"])
        self.filter_status.grid(
            row=0, column=3, padx=(0, 12), pady=10
        )
        self.filter_search = ctk.CTkEntry(filters, placeholder_text="Nome, documento, telefone ou e-mail")
        self.filter_search.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=10)
        ctk.CTkButton(filters, text="Filtrar", command=self._carregar_clientes).grid(
            row=0, column=5, padx=(0, 12), pady=10
        )

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

        self._add_entry(form_fields, "Razão Social / Nome", "nome", 0, required=True)
        self._add_entry(form_fields, "CPF / CNPJ", "documento", 1)
        self._add_entry(form_fields, "Inscrição Estadual", "inscricao", 2)
        self._add_entry(form_fields, "E-mail", "email", 3)
        self._add_entry(form_fields, "Telefone", "telefone", 4)
        self._add_entry(form_fields, "WhatsApp", "whatsapp", 5)
        self._add_entry(form_fields, "Endereço", "endereco", 6)
        self._add_entry(form_fields, "Bairro", "bairro", 7)
        self._add_entry(form_fields, "Cidade", "cidade", 8)
        self._add_entry(form_fields, "UF", "uf", 9)
        self._add_entry(form_fields, "CEP", "cep", 10)
        self._add_entry(form_fields, "Segmento / Canal", "segmento", 11)
        self._add_entry(form_fields, "Observações", "observacoes", 12, height=80, multiline=True)
        self._add_option(form_fields, "Status", "status", ["Ativo", "Inativo"], 13)

        list_frame = ctk.CTkFrame(body)
        list_frame.grid(row=0, column=1, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            list_frame, text="Clientes Cadastrados", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.tree = ttk.Treeview(
            list_frame,
            columns=("id", "nome", "documento", "cidade", "status", "ultima_compra"),
            show="headings",
            height=12,
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("nome", text="Nome")
        self.tree.heading("documento", text="Documento")
        self.tree.heading("cidade", text="Cidade")
        self.tree.heading("status", text="Status")
        self.tree.heading("ultima_compra", text="Atualização")
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("nome", width=220)
        self.tree.column("documento", width=140)
        self.tree.column("cidade", width=140)
        self.tree.column("status", width=90, anchor="center")
        self.tree.column("ultima_compra", width=160, anchor="center")

        self.tree.bind("<<TreeviewSelect>>", self._selecionar_cliente)

        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        tree_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16))

        summary = ctk.CTkFrame(list_frame)
        summary.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        summary.grid_columnconfigure(0, weight=1)
        self.summary_label = ctk.CTkLabel(
            summary,
            text="Resumo: 0 clientes ativos • Receita anual R$ 0,00 • Ticket médio R$ 0,00",
            font=ctk.CTkFont(size=12),
        )
        self.summary_label.grid(row=0, column=0, sticky="w", padx=12, pady=8)

    def _add_entry(self, parent, label, key, row, height=None, multiline=False, required=False):
        label_text = f"{label} *" if required else label
        ctk.CTkLabel(parent, text=label_text).grid(row=row * 2, column=0, sticky="w", pady=(0, 2))
        if multiline:
            entry = ctk.CTkTextbox(parent, height=height or 80)
        else:
            entry = ctk.CTkEntry(parent)
        entry.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 8))
        self.entries[key] = entry

    def _add_option(self, parent, label, key, values, row):
        ctk.CTkLabel(parent, text=label).grid(row=row * 2, column=0, sticky="w", pady=(0, 2))
        option = ctk.CTkOptionMenu(parent, values=values)
        option.set(values[0])
        option.grid(row=row * 2 + 1, column=0, sticky="w", pady=(0, 8))
        self.entries[key] = option

    def _verificar_conexao(self):
        try:
            ok, msg = require_ready()
            if not ok:
                messagebox.showwarning("Banco de dados", msg)
        except Exception as exc:
            messagebox.showwarning("Banco de dados", f"Não foi possível validar o banco: {exc}")

    def _carregar_clientes(self):
        if self.tree is None:
            return
        self.tree.delete(*self.tree.get_children())
        termo = self.filter_search.get().strip() if hasattr(self, "filter_search") else ""
        status = self.filter_status.get() if hasattr(self, "filter_status") else "Todos"
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                params = []
                where = []
                if termo:
                    where.append(
                        "(nome ILIKE %s OR documento ILIKE %s OR telefone ILIKE %s OR email ILIKE %s)"
                    )
                    like = f"%{termo}%"
                    params.extend([like, like, like, like])
                if status and status != "Todos":
                    where.append("status = %s")
                    params.append(status)
                where_clause = f"WHERE {' AND '.join(where)}" if where else ""
                cursor.execute(
                    f"""
                    SELECT id, nome, documento, cidade, status, data_atualizacao
                    FROM {schema}.cadastro_clientes
                    {where_clause}
                    ORDER BY nome ASC
                    """,
                    params,
                )
                rows = cursor.fetchall()
                for row in rows:
                    data_atualizacao = row[5].strftime("%d/%m/%Y %H:%M") if row[5] else ""
                    self.tree.insert(
                        "", "end", values=(row[0], row[1], row[2] or "", row[3] or "", row[4], data_atualizacao)
                    )
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FILTER (WHERE status = 'Ativo') AS ativos,
                           COUNT(*) AS total
                    FROM {schema}.cadastro_clientes
                    """
                )
                total_info = cursor.fetchone()
            conn.commit()
            if self.summary_label and total_info:
                self.summary_label.configure(
                    text=f"Resumo: {total_info[0]} clientes ativos • Total cadastrados {total_info[1]}"
                )
        except Exception as exc:
            messagebox.showerror("Clientes", f"Erro ao carregar clientes: {exc}")

    def _coletar_dados(self):
        data = {}
        for key, widget in self.entries.items():
            if isinstance(widget, ctk.CTkTextbox):
                value = widget.get("1.0", "end").strip()
            else:
                value = widget.get().strip()
            data[key] = value
        return data

    def _salvar_cliente(self):
        dados = self._coletar_dados()
        if not dados.get("nome"):
            messagebox.showwarning("Clientes", "Informe o nome do cliente.")
            return
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                if self.selected_id:
                    cursor.execute(
                        f"""
                        UPDATE {schema}.cadastro_clientes
                        SET nome=%s, documento=%s, inscricao_estadual=%s, email=%s, telefone=%s,
                            whatsapp=%s, endereco=%s, bairro=%s, cidade=%s, uf=%s, cep=%s,
                            segmento=%s, observacoes=%s, status=%s, data_atualizacao=NOW()
                        WHERE id=%s
                        """,
                        (
                            dados.get("nome"),
                            dados.get("documento"),
                            dados.get("inscricao"),
                            dados.get("email"),
                            dados.get("telefone"),
                            dados.get("whatsapp"),
                            dados.get("endereco"),
                            dados.get("bairro"),
                            dados.get("cidade"),
                            dados.get("uf"),
                            dados.get("cep"),
                            dados.get("segmento"),
                            dados.get("observacoes"),
                            dados.get("status") or "Ativo",
                            self.selected_id,
                        ),
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT INTO {schema}.cadastro_clientes
                        (nome, documento, inscricao_estadual, email, telefone, whatsapp, endereco,
                         bairro, cidade, uf, cep, segmento, observacoes, status, data_atualizacao)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            dados.get("nome"),
                            dados.get("documento"),
                            dados.get("inscricao"),
                            dados.get("email"),
                            dados.get("telefone"),
                            dados.get("whatsapp"),
                            dados.get("endereco"),
                            dados.get("bairro"),
                            dados.get("cidade"),
                            dados.get("uf"),
                            dados.get("cep"),
                            dados.get("segmento"),
                            dados.get("observacoes"),
                            dados.get("status") or "Ativo",
                        ),
                    )
            conn.commit()
            self._limpar_formulario()
            self._carregar_clientes()
            messagebox.showinfo("Clientes", "Cliente salvo com sucesso.")
        except Exception as exc:
            messagebox.showerror("Clientes", f"Erro ao salvar cliente: {exc}")

    def _inativar_cliente(self):
        if not self.selected_id:
            messagebox.showwarning("Clientes", "Selecione um cliente para inativar.")
            return
        if not messagebox.askyesno("Clientes", "Deseja inativar este cliente?"):
            return
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"""
                    UPDATE {schema}.cadastro_clientes
                    SET status='Inativo', data_atualizacao=NOW()
                    WHERE id=%s
                    """,
                    (self.selected_id,),
                )
            conn.commit()
            self._limpar_formulario()
            self._carregar_clientes()
        except Exception as exc:
            messagebox.showerror("Clientes", f"Erro ao inativar cliente: {exc}")

    def _exportar_cliente(self):
        messagebox.showinfo(
            "Clientes", "Exportação será integrada com o módulo de relatórios."
        )

    def _limpar_formulario(self):
        for key, widget in self.entries.items():
            if isinstance(widget, ctk.CTkTextbox):
                widget.delete("1.0", "end")
            elif isinstance(widget, ctk.CTkOptionMenu):
                widget.set("Ativo")
            else:
                widget.delete(0, "end")
        self.selected_id = None

    def _selecionar_cliente(self, _event=None):
        if not self.tree:
            return
        selecionado = self.tree.selection()
        if not selecionado:
            return
        item = self.tree.item(selecionado[0])
        valores = item.get("values", [])
        if not valores:
            return
        self.selected_id = valores[0]
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(
                    f"""
                    SELECT nome, documento, inscricao_estadual, email, telefone, whatsapp, endereco,
                           bairro, cidade, uf, cep, segmento, observacoes, status
                    FROM {schema}.cadastro_clientes
                    WHERE id=%s
                    """,
                    (self.selected_id,),
                )
                row = cursor.fetchone()
            conn.commit()
            if row:
                keys = [
                    "nome",
                    "documento",
                    "inscricao",
                    "email",
                    "telefone",
                    "whatsapp",
                    "endereco",
                    "bairro",
                    "cidade",
                    "uf",
                    "cep",
                    "segmento",
                    "observacoes",
                    "status",
                ]
                for key, value in zip(keys, row):
                    widget = self.entries.get(key)
                    if widget is None:
                        continue
                    if isinstance(widget, ctk.CTkTextbox):
                        widget.delete("1.0", "end")
                        widget.insert("1.0", value or "")
                    elif isinstance(widget, ctk.CTkOptionMenu):
                        widget.set(value or "Ativo")
                    else:
                        widget.delete(0, "end")
                        widget.insert(0, value or "")
        except Exception as exc:
            messagebox.showerror("Clientes", f"Erro ao carregar cliente: {exc}")


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Clientes - Teste")
    app.geometry("1100x720")
    page = ClientesPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()
