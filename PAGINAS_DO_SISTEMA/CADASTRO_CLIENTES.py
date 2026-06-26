# -*- coding: utf-8 -*-
"""
CADASTRO_CLIENTES.py - Módulo de Clientes
Interface base para cadastro, consulta e relacionamento de clientes.
"""
from tkinter import messagebox, ttk

import customtkinter as ctk

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
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
        self._field_labels = {}
        self.tree = None
        self.summary_label = None
        self.selected_id = None
        self.filter_search = None
        self._ui_refs = {}
        self._init_theme_tokens()
        self._build()
        self._verificar_conexao()
        self.after(200, self._carregar_clientes)

    def _init_theme_tokens(self):
        self.page_bg = getattr(self.sistema, "cor_fundo", "#f8fafc")
        self.card_bg = getattr(self.sistema, "cor_secundaria", "#ffffff")
        self.input_bg = getattr(self.sistema, "cor_terciaria", "#eef2f7")
        self.text_color = getattr(self.sistema, "cor_texto", "#0f172a")
        self.muted_color = getattr(self.sistema, "cor_texto_secundario", "#475569")
        self.border_color = getattr(self.sistema, "cor_borda", "#cbd5e1")
        self.primary_color = getattr(self.sistema, "cor_primaria", "#2563eb")
        self.hover_color = getattr(self.sistema, "cor_hover", "#1d4ed8")
        self.success_color = getattr(self.sistema, "cor_sucesso", "#047857")
        self.danger_color = getattr(self.sistema, "cor_erro", "#dc2626")
        self.export_color = "#6d4fd8"

    def _button_text_color(self, bg):
        try:
            value = str(bg or "").lstrip("#")
            if len(value) != 6:
                return "#ffffff"
            r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#000000" if lum > 0.62 else "#ffffff"
        except Exception:
            return "#ffffff"

    def _apply_tree_style(self):
        style = ttk.Style()
        tree_style = "Clientes.Treeview"
        style.configure(
            tree_style,
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#111827",
            rowheight=28,
            borderwidth=0,
            font=("Arial", 10),
        )
        style.configure(
            f"{tree_style}.Heading",
            background="#eef2f7",
            foreground="#111827",
            relief="flat",
            font=("Arial", 10, "bold"),
            padding=(8, 6),
        )
        style.map(
            tree_style,
            background=[("selected", "#bfdbfe")],
            foreground=[("selected", "#111827")],
        )
        return tree_style

    # =========================
    # IDIOMA
    # =========================
    def _get_idioma_atual(self):
        return getattr(self.sistema, "idioma_atual", "pt_BR")

    def _get_text(self, chave, **kwargs):
        textos = {
            "pt_BR": {
                "page_title": "Cadastro de Clientes",
                "page_subtitle": "Gestão de contatos, endereços e vínculos para pedidos e relatórios.",
                "form_name": "Razão Social / Nome",
                "form_document": "CPF / CNPJ",
                "form_phone": "Telefone",
                "form_whatsapp": "WhatsApp",
                "form_email": "E-mail",
                "form_inscricao": "Inscrição Estadual",
                "form_city": "Cidade",
                "form_state": "UF",
                "form_zip": "CEP",
                "form_neighborhood": "Bairro",
                "form_address": "Endereço",
                "form_segment": "Segmento / Canal",
                "form_status": "Status",
                "form_notes": "Observações",
                "status_active": "Ativo",
                "status_inactive": "Inativo",
                "btn_new": "Novo Cliente",
                "btn_save": "Salvar",
                "btn_inactivate": "Inativar",
                "btn_export": "Exportar",
                "list_title": "Clientes Cadastrados",
                "col_id": "ID",
                "col_name": "Nome",
                "col_document": "Documento",
                "col_city": "Cidade",
                "col_status": "Status",
                "col_updated": "Atualização",
                "summary_empty": "Resumo: 0 clientes ativos • Total cadastrados 0",
                "summary_text": "Resumo: {ativos} clientes ativos • Total cadastrados {total}",
                "search_label": "Pesquisar por nome",
                "search_placeholder": "Digite uma letra ou parte do nome (ex: A)",
                "db_title": "Banco de dados",
                "clients_title": "Clientes",
                "warn_name": "Informe o nome do cliente.",
                "saved_success": "Cliente salvo com sucesso.",
                "select_inactivate": "Selecione um cliente para inativar.",
                "confirm_inactivate": "Deseja inativar este cliente?",
                "export_info": "Exportação será integrada com o módulo de relatórios.",
                "load_error": "Erro ao carregar clientes: {erro}",
                "save_error": "Erro ao salvar cliente: {erro}",
                "inactivate_error": "Erro ao inativar cliente: {erro}",
                "db_validate_error": "Não foi possível validar o banco: {erro}",
            },
            "en_US": {
                "page_title": "Customer Registry",
                "page_subtitle": "Contact, address, and relationship management for orders and reports.",
                "form_name": "Company / Name",
                "form_document": "Tax ID",
                "form_phone": "Phone",
                "form_whatsapp": "WhatsApp",
                "form_email": "E-mail",
                "form_inscricao": "State Registration",
                "form_city": "City",
                "form_state": "State",
                "form_zip": "ZIP Code",
                "form_neighborhood": "Neighborhood",
                "form_address": "Address",
                "form_segment": "Segment / Channel",
                "form_status": "Status",
                "form_notes": "Notes",
                "status_active": "Active",
                "status_inactive": "Inactive",
                "btn_new": "New Customer",
                "btn_save": "Save",
                "btn_inactivate": "Deactivate",
                "btn_export": "Export",
                "list_title": "Registered Customers",
                "col_id": "ID",
                "col_name": "Name",
                "col_document": "Document",
                "col_city": "City",
                "col_status": "Status",
                "col_updated": "Updated",
                "summary_empty": "Summary: 0 active customers • Total registered 0",
                "summary_text": "Summary: {ativos} active customers • Total registered {total}",
                "search_label": "Search by name",
                "search_placeholder": "Type a letter or part of the name (e.g. A)",
                "db_title": "Database",
                "clients_title": "Customers",
                "warn_name": "Enter the customer name.",
                "saved_success": "Customer saved successfully.",
                "select_inactivate": "Select a customer to deactivate.",
                "confirm_inactivate": "Do you want to deactivate this customer?",
                "export_info": "Export will be integrated with the reports module.",
                "load_error": "Error loading customers: {erro}",
                "save_error": "Error saving customer: {erro}",
                "inactivate_error": "Error deactivating customer: {erro}",
                "db_validate_error": "Could not validate the database: {erro}",
            },
            "es_ES": {
                "page_title": "Registro de Clientes",
                "page_subtitle": "Gestión de contactos, direcciones y vínculos para pedidos e informes.",
                "form_name": "Razón social / Nombre",
                "form_document": "CPF / CNPJ",
                "form_phone": "Teléfono",
                "form_whatsapp": "WhatsApp",
                "form_email": "Correo electrónico",
                "form_inscricao": "Inscripción estatal",
                "form_city": "Ciudad",
                "form_state": "UF",
                "form_zip": "Código postal",
                "form_neighborhood": "Barrio",
                "form_address": "Dirección",
                "form_segment": "Segmento / Canal",
                "form_status": "Estado",
                "form_notes": "Observaciones",
                "status_active": "Activo",
                "status_inactive": "Inactivo",
                "btn_new": "Nuevo Cliente",
                "btn_save": "Guardar",
                "btn_inactivate": "Inactivar",
                "btn_export": "Exportar",
                "list_title": "Clientes Registrados",
                "col_id": "ID",
                "col_name": "Nombre",
                "col_document": "Documento",
                "col_city": "Ciudad",
                "col_status": "Estado",
                "col_updated": "Actualización",
                "summary_empty": "Resumen: 0 clientes activos • Total registrados 0",
                "summary_text": "Resumen: {ativos} clientes activos • Total registrados {total}",
                "search_label": "Buscar por nombre",
                "search_placeholder": "Escriba una letra o parte del nombre (ej.: A)",
                "db_title": "Base de datos",
                "clients_title": "Clientes",
                "warn_name": "Informe el nombre del cliente.",
                "saved_success": "Cliente guardado con éxito.",
                "select_inactivate": "Seleccione un cliente para inactivar.",
                "confirm_inactivate": "¿Desea inactivar este cliente?",
                "export_info": "La exportación se integrará con el módulo de informes.",
                "load_error": "Error al cargar clientes: {erro}",
                "save_error": "Error al guardar cliente: {erro}",
                "inactivate_error": "Error al inactivar cliente: {erro}",
                "db_validate_error": "No fue posible validar la base de datos: {erro}",
            },
        }
        idioma = self._get_idioma_atual()
        base = textos.get(idioma, textos["pt_BR"])
        texto = base.get(chave, textos["pt_BR"].get(chave, chave))
        try:
            return texto.format(**kwargs) if kwargs else texto
        except Exception:
            return texto

    def _map_status_from_db(self, valor):
        if str(valor).strip().lower() == "inativo":
            return self._get_text("status_inactive")
        return self._get_text("status_active")

    def _map_status_to_db(self, valor):
        v = str(valor).strip().lower()
        if v in {"inactive", "inactivo", "inativo"}:
            return "Inativo"
        return "Ativo"

    def refresh_texts(self):
        if self._ui_refs.get("title_label"):
            self._ui_refs["title_label"].configure(text=self._get_text("page_title"))
        if self._ui_refs.get("subtitle_label"):
            self._ui_refs["subtitle_label"].configure(text=self._get_text("page_subtitle"))
        if self._ui_refs.get("btn_new"):
            self._ui_refs["btn_new"].configure(text=self._get_text("btn_new"))
        if self._ui_refs.get("btn_save"):
            self._ui_refs["btn_save"].configure(text=self._get_text("btn_save"))
        if self._ui_refs.get("btn_inactivate"):
            self._ui_refs["btn_inactivate"].configure(text=self._get_text("btn_inactivate"))
        if self._ui_refs.get("btn_export"):
            self._ui_refs["btn_export"].configure(text=self._get_text("btn_export"))
        if self._ui_refs.get("list_title"):
            self._ui_refs["list_title"].configure(text=self._get_text("list_title"))
        if self._ui_refs.get("search_label"):
            self._ui_refs["search_label"].configure(text=self._get_text("search_label"))
        if self.filter_search is not None:
            self.filter_search.configure(placeholder_text=self._get_text("search_placeholder"))
        for key, label in self._field_labels.items():
            required = key == "nome"
            text_key = {
                "nome": "form_name", "documento": "form_document", "telefone": "form_phone",
                "whatsapp": "form_whatsapp", "email": "form_email", "inscricao": "form_inscricao",
                "cidade": "form_city", "uf": "form_state", "cep": "form_zip", "bairro": "form_neighborhood",
                "endereco": "form_address", "segmento": "form_segment", "status": "form_status",
                "observacoes": "form_notes",
            }[key]
            text = self._get_text(text_key)
            if required:
                text += " *"
            label.configure(text=text)
        status_widget = self.entries.get("status")
        if isinstance(status_widget, ctk.CTkOptionMenu):
            atual = status_widget.get()
            mapped = self._map_status_to_db(atual)
            values = [self._get_text("status_active"), self._get_text("status_inactive")]
            status_widget.configure(values=values)
            status_widget.set(self._map_status_from_db(mapped))
        if self.tree is not None:
            self.tree.heading("id", text=self._get_text("col_id"))
            self.tree.heading("nome", text=self._get_text("col_name"))
            self.tree.heading("documento", text=self._get_text("col_document"))
            self.tree.heading("cidade", text=self._get_text("col_city"))
            self.tree.heading("status", text=self._get_text("col_status"))
            self.tree.heading("ultima_compra", text=self._get_text("col_updated"))
        if self.summary_label is not None and not self.summary_label.cget("text"):
            self.summary_label.configure(text=self._get_text("summary_empty"))
        self._carregar_clientes()

    def _build(self):
        self.configure(fg_color=self.page_bg)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_body()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)

        self._ui_refs["title_label"] = ctk.CTkLabel(
            header,
            text=self._get_text("page_title"),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.text_color,
        )
        self._ui_refs["title_label"].grid(row=0, column=0, sticky="w")

        self._ui_refs["subtitle_label"] = ctk.CTkLabel(
            header,
            text=self._get_text("page_subtitle"),
            font=ctk.CTkFont(size=12),
            text_color=self.muted_color,
        )
        self._ui_refs["subtitle_label"].grid(row=1, column=0, sticky="w", pady=(4, 0))

        form_header = ctk.CTkFrame(
            header,
            fg_color=self.card_bg,
            border_width=1,
            border_color=self.border_color,
            corner_radius=8,
        )
        form_header.grid(row=2, column=0, sticky="ew", pady=(14, 0))
        form_header.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._add_entry(form_header, self._get_text("form_name"), "nome", 0, column=0, required=True)
        self._add_entry(form_header, self._get_text("form_document"), "documento", 0, column=1)
        self._add_entry(form_header, self._get_text("form_phone"), "telefone", 0, column=2)
        self._add_entry(form_header, self._get_text("form_whatsapp"), "whatsapp", 0, column=3)
        self._add_entry(form_header, self._get_text("form_email"), "email", 1, column=0)
        self._add_entry(form_header, self._get_text("form_inscricao"), "inscricao", 1, column=1)
        self._add_entry(form_header, self._get_text("form_city"), "cidade", 1, column=2)
        self._add_entry(form_header, self._get_text("form_state"), "uf", 1, column=3)
        self._add_entry(form_header, self._get_text("form_zip"), "cep", 2, column=0)
        self._add_entry(form_header, self._get_text("form_neighborhood"), "bairro", 2, column=1)
        self._add_entry(form_header, self._get_text("form_address"), "endereco", 2, column=2, columnspan=2)
        self._add_entry(form_header, self._get_text("form_segment"), "segmento", 3, column=0)
        self._add_option(form_header, self._get_text("form_status"), "status", [self._get_text("status_active"), self._get_text("status_inactive")], 3, column=1)
        self._add_entry(form_header, self._get_text("form_notes"), "observacoes", 3, column=2, columnspan=2, height=70, multiline=True)

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        toolbar.grid_columnconfigure(3, weight=1)

        self._ui_refs["btn_new"] = ctk.CTkButton(
            toolbar, text=self._get_text("btn_new"), command=self._limpar_formulario,
            width=140, height=32, fg_color=self.primary_color, hover_color=self.hover_color,
            text_color=self._button_text_color(self.primary_color), corner_radius=6,
        )
        self._ui_refs["btn_new"].grid(row=0, column=0, padx=(0, 8))
        self._ui_refs["btn_save"] = ctk.CTkButton(
            toolbar, text=self._get_text("btn_save"), command=self._salvar_cliente,
            width=140, height=32, fg_color=self.success_color,
            text_color=self._button_text_color(self.success_color), corner_radius=6,
        )
        self._ui_refs["btn_save"].grid(row=0, column=1, padx=(0, 8))
        self._ui_refs["btn_inactivate"] = ctk.CTkButton(
            toolbar, text=self._get_text("btn_inactivate"), command=self._inativar_cliente,
            width=140, height=32, fg_color=self.danger_color,
            text_color=self._button_text_color(self.danger_color), corner_radius=6,
        )
        self._ui_refs["btn_inactivate"].grid(row=0, column=2, padx=(0, 8))
        self._ui_refs["btn_export"] = ctk.CTkButton(
            toolbar, text=self._get_text("btn_export"), command=self._exportar_cliente,
            width=140, height=32, fg_color=self.export_color,
            text_color=self._button_text_color(self.export_color), corner_radius=6,
        )
        self._ui_refs["btn_export"].grid(row=0, column=4)

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 16))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        list_frame = ctk.CTkFrame(
            body,
            fg_color=self.card_bg,
            border_width=1,
            border_color=self.border_color,
            corner_radius=8,
        )
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(2, weight=1)

        list_top = ctk.CTkFrame(list_frame, fg_color="transparent")
        list_top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(12, 8))
        list_top.grid_columnconfigure(1, weight=1)

        self._ui_refs["list_title"] = ctk.CTkLabel(
            list_top,
            text=self._get_text("list_title"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.text_color,
        )
        self._ui_refs["list_title"].grid(row=0, column=0, sticky="w")

        search_group = ctk.CTkFrame(list_top, fg_color="transparent")
        search_group.grid(row=0, column=1, sticky="e")
        self._ui_refs["search_label"] = ctk.CTkLabel(
            search_group,
            text=self._get_text("search_label"),
            text_color=self.muted_color,
        )
        self._ui_refs["search_label"].grid(row=0, column=0, padx=(0, 8))
        self.filter_search = ctk.CTkEntry(
            search_group,
            width=420,
            placeholder_text=self._get_text("search_placeholder"),
            fg_color=self.input_bg,
            border_color=self.border_color,
            text_color=self.text_color,
        )
        self.filter_search.grid(row=0, column=1)
        self.filter_search.bind("<KeyRelease>", self._filtrar_em_tempo_real)

        tree_style = self._apply_tree_style()
        self.tree = ttk.Treeview(
            list_frame,
            columns=("id", "nome", "documento", "cidade", "status", "ultima_compra"),
            show="headings",
            height=12,
            style=tree_style,
        )
        self.tree.heading("id", text=self._get_text("col_id"))
        self.tree.heading("nome", text=self._get_text("col_name"))
        self.tree.heading("documento", text=self._get_text("col_document"))
        self.tree.heading("cidade", text=self._get_text("col_city"))
        self.tree.heading("status", text=self._get_text("col_status"))
        self.tree.heading("ultima_compra", text=self._get_text("col_updated"))
        self.tree.column("id", width=60, anchor="center")
        self.tree.column("nome", width=220)
        self.tree.column("documento", width=140)
        self.tree.column("cidade", width=140)
        self.tree.column("status", width=90, anchor="center")
        self.tree.column("ultima_compra", width=160, anchor="center")
        self.tree.bind("<<TreeviewSelect>>", self._selecionar_cliente)

        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.grid(row=2, column=0, sticky="nsew", padx=(14, 0), pady=(0, 10))
        tree_scroll.grid(row=2, column=1, sticky="ns", pady=(0, 10), padx=(0, 14))

        summary = ctk.CTkFrame(list_frame, fg_color=self.input_bg, corner_radius=6)
        summary.grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))
        summary.grid_columnconfigure(0, weight=1)
        self.summary_label = ctk.CTkLabel(
            summary,
            text=self._get_text("summary_empty"),
            font=ctk.CTkFont(size=12),
            text_color=self.text_color,
        )
        self.summary_label.grid(row=0, column=0, sticky="w", padx=12, pady=7)

    def _build_search_footer(self):
        return

    def _add_entry(self, parent, label, key, row, column=0, columnspan=1, height=None, multiline=False, required=False):
        label_text = f"{label} *" if required else label
        lbl = ctk.CTkLabel(parent, text=label_text, text_color=self.text_color, font=ctk.CTkFont(size=11))
        lbl.grid(row=row * 2, column=column, columnspan=columnspan, sticky="w", padx=12, pady=(10 if row == 0 else 0, 2))
        self._field_labels[key] = lbl
        if multiline:
            entry = ctk.CTkTextbox(
                parent,
                height=height or 80,
                fg_color=self.input_bg,
                border_color=self.border_color,
                border_width=1,
                text_color=self.text_color,
            )
        else:
            entry = ctk.CTkEntry(
                parent,
                fg_color=self.input_bg,
                border_color=self.border_color,
                text_color=self.text_color,
                height=28,
            )
        entry.grid(row=row * 2 + 1, column=column, columnspan=columnspan, sticky="ew", padx=12, pady=(0, 8))
        self.entries[key] = entry

    def _add_option(self, parent, label, key, values, row, column=0):
        lbl = ctk.CTkLabel(parent, text=label, text_color=self.text_color, font=ctk.CTkFont(size=11))
        lbl.grid(row=row * 2, column=column, sticky="w", padx=12, pady=(10 if row == 0 else 0, 2))
        self._field_labels[key] = lbl
        option = ctk.CTkOptionMenu(
            parent,
            values=values,
            fg_color=self.primary_color,
            button_color=self.primary_color,
            button_hover_color=self.hover_color,
            text_color=self._button_text_color(self.primary_color),
            height=28,
            width=140,
        )
        option.set(values[0])
        option.grid(row=row * 2 + 1, column=column, sticky="w", padx=12, pady=(0, 8))
        self.entries[key] = option

    def _verificar_conexao(self):
        try:
            ok, msg = require_ready()
            if not ok:
                messagebox.showwarning(self._get_text("db_title"), msg)
        except Exception as exc:
            messagebox.showwarning(self._get_text("db_title"), self._get_text("db_validate_error", erro=exc))

    def _carregar_clientes(self):
        if self.tree is None:
            return
        self.tree.delete(*self.tree.get_children())
        termo = self.filter_search.get().strip() if self.filter_search else ""
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                params = []
                where = []
                if termo:
                    where.append("nome ILIKE %s")
                    params.append(f"{termo}%")
                where_clause = f"WHERE {' AND '.join(where)}" if where else ""
                cursor.execute(f"""
                    SELECT id, nome, documento, cidade, status, data_atualizacao
                    FROM {schema}.cadastro_clientes
                    {where_clause}
                    ORDER BY nome ASC
                    """, params)
                rows = cursor.fetchall()
                for row in rows:
                    data_atualizacao = row[5].strftime("%d/%m/%Y %H:%M") if row[5] else ""
                    self.tree.insert("", "end", values=(row[0], row[1], row[2] or "", row[3] or "", self._map_status_from_db(row[4]), data_atualizacao))
                cursor.execute(f"""
                    SELECT COUNT(*) FILTER (WHERE status = 'Ativo') AS ativos, COUNT(*) AS total
                    FROM {schema}.cadastro_clientes
                    """)
                total_info = cursor.fetchone()
            conn.commit()
            if self.summary_label and total_info:
                self.summary_label.configure(text=self._get_text("summary_text", ativos=total_info[0], total=total_info[1]))
        except Exception as exc:
            messagebox.showerror(self._get_text("clients_title"), self._get_text("load_error", erro=exc))

    def _filtrar_em_tempo_real(self, _event=None):
        self._carregar_clientes()

    def _coletar_dados(self):
        data = {}
        for key, widget in self.entries.items():
            if isinstance(widget, ctk.CTkTextbox):
                value = widget.get("1.0", "end").strip()
            else:
                value = widget.get().strip()
            if key == "status":
                value = self._map_status_to_db(value)
            data[key] = value
        return data

    def _salvar_cliente(self):
        dados = self._coletar_dados()
        if not dados.get("nome"):
            messagebox.showwarning(self._get_text("clients_title"), self._get_text("warn_name"))
            return
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                if self.selected_id:
                    cursor.execute(f"""
                        UPDATE {schema}.cadastro_clientes
                        SET nome=%s, documento=%s, inscricao_estadual=%s, email=%s, telefone=%s,
                            whatsapp=%s, endereco=%s, bairro=%s, cidade=%s, uf=%s, cep=%s,
                            segmento=%s, observacoes=%s, status=%s, data_atualizacao=NOW()
                        WHERE id=%s
                        """, (dados.get("nome"), dados.get("documento"), dados.get("inscricao"), dados.get("email"), dados.get("telefone"), dados.get("whatsapp"), dados.get("endereco"), dados.get("bairro"), dados.get("cidade"), dados.get("uf"), dados.get("cep"), dados.get("segmento"), dados.get("observacoes"), dados.get("status") or "Ativo", self.selected_id))
                else:
                    cursor.execute(f"""
                        INSERT INTO {schema}.cadastro_clientes
                        (nome, documento, inscricao_estadual, email, telefone, whatsapp, endereco,
                         bairro, cidade, uf, cep, segmento, observacoes, status, data_atualizacao)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (dados.get("nome"), dados.get("documento"), dados.get("inscricao"), dados.get("email"), dados.get("telefone"), dados.get("whatsapp"), dados.get("endereco"), dados.get("bairro"), dados.get("cidade"), dados.get("uf"), dados.get("cep"), dados.get("segmento"), dados.get("observacoes"), dados.get("status") or "Ativo"))
            conn.commit()
            self._limpar_formulario()
            self._carregar_clientes()
            messagebox.showinfo(self._get_text("clients_title"), self._get_text("saved_success"))
        except Exception as exc:
            messagebox.showerror(self._get_text("clients_title"), self._get_text("save_error", erro=exc))

    def _inativar_cliente(self):
        if not self.selected_id:
            messagebox.showwarning(self._get_text("clients_title"), self._get_text("select_inactivate"))
            return
        if not messagebox.askyesno(self._get_text("clients_title"), self._get_text("confirm_inactivate")):
            return
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(f"""
                    UPDATE {schema}.cadastro_clientes
                    SET status='Inativo', data_atualizacao=NOW()
                    WHERE id=%s
                    """, (self.selected_id,))
            conn.commit()
            self._limpar_formulario()
            self._carregar_clientes()
        except Exception as exc:
            messagebox.showerror(self._get_text("clients_title"), self._get_text("inactivate_error", erro=exc))

    def _exportar_cliente(self):
        messagebox.showinfo(self._get_text("clients_title"), self._get_text("export_info"))

    def _limpar_formulario(self):
        for key, widget in self.entries.items():
            if isinstance(widget, ctk.CTkTextbox):
                widget.delete("1.0", "end")
            elif isinstance(widget, ctk.CTkOptionMenu):
                widget.set(self._get_text("status_active"))
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
        valores = item.get("values", ())
        if not valores:
            return
        self.selected_id = valores[0]
        try:
            conn = get_conn()
            with conn.cursor() as cursor:
                schema = get_schema()
                cursor.execute(f"""
                    SELECT nome, documento, inscricao_estadual, email, telefone, whatsapp, endereco,
                           bairro, cidade, uf, cep, segmento, observacoes, status
                    FROM {schema}.cadastro_clientes
                    WHERE id=%s
                    """, (self.selected_id,))
                row = cursor.fetchone()
            if not row:
                return
            keys = ["nome", "documento", "inscricao", "email", "telefone", "whatsapp", "endereco", "bairro", "cidade", "uf", "cep", "segmento", "observacoes", "status"]
            data = dict(zip(keys, row))
            for key, widget in self.entries.items():
                if isinstance(widget, ctk.CTkTextbox):
                    widget.delete("1.0", "end")
                    widget.insert("1.0", data.get(key) or "")
                elif isinstance(widget, ctk.CTkOptionMenu):
                    widget.set(self._map_status_from_db(data.get(key) or "Ativo"))
                else:
                    widget.delete(0, "end")
                    widget.insert(0, data.get(key) or "")
        except Exception as exc:
            messagebox.showerror(self._get_text("clients_title"), self._get_text("load_error", erro=exc))

# --- AUTO_PAGE_TRANSLATIONS (gerado automaticamente) ---
from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support as _attach_i18n_support

AUTO_PAGE_TRANSLATIONS = {
    "ClientesPage": {
        "pt_BR": {"title": "Clientes", "Atualizar": "Atualizar", "Filtrar": "Filtrar", "Salvar": "Salvar", "Cancelar": "Cancelar"},
        "en_US": {"title": "Clientes", "Atualizar": "Refresh", "Filtrar": "Filter", "Salvar": "Save", "Cancelar": "Cancel"},
        "es_ES": {"title": "Clientes", "Atualizar": "Actualizar", "Filtrar": "Filtrar", "Salvar": "Guardar", "Cancelar": "Cancelar"},
    },
}

for _cls_name, _map in AUTO_PAGE_TRANSLATIONS.items():
    _cls = globals().get(_cls_name)
    if isinstance(_cls, type):
        if not hasattr(_cls, "TRANSLATIONS") and not hasattr(_cls, "_TRANSLATIONS"):
            _cls.TRANSLATIONS = _map
        _attach_i18n_support(_cls, getattr(_cls, "TRANSLATIONS", getattr(_cls, "_TRANSLATIONS", _map)))

if __name__ == "__main__":
    try:
        print(f"[TESTE_ISOLADO] Módulo carregado: {__file__}")
    except Exception as e:
        print(f"[TESTE_ISOLADO] Falha ao iniciar módulo: {e}")
