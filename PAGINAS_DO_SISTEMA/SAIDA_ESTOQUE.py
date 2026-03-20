import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime

from PAGINAS_DO_SISTEMA.TEMAS import ajustar_hover
from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db


class SaidaEstoqueApp(ctk.CTkFrame):
    def __init__(self, master, sistema=None, app=None, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.sistema = (
            sistema
            or app
            or kwargs.get("sistema")
            or kwargs.get("app")
            or kwargs.get("controller")
            or kwargs.get("root")
            or kwargs.get("main")
        )
        self._ui_refs = {}
        self._column_keys = []
        self.entries = {}
        self.id_selecionado = None

        self.tipos = ["Tecidos", "Aviamentos", "Insumos", "Escritorio", "Limpeza", "Outros"]

        self.configure(fg_color=self._get_cor_fundo())
        self.pack(fill="both", expand=True)

        if not db or not db.ready_check():
            ctk.CTkLabel(
                self,
                text=self._get_text("db_error"),
                text_color="#ef4444",
                font=("Arial", 16),
            ).pack(pady=50)
            return

        self.setup_ui()
        self.atualizar_interface(self.tipos[0])

    # =========================
    # IDIOMA
    # =========================
    def _get_idioma_atual(self):
        return getattr(self.sistema, "idioma_atual", "pt_BR")

    def _get_text(self, chave, **kwargs):
        idioma = self._get_idioma_atual()
        textos = {
            "pt_BR": {
                "title": "Saída de Estoque",
                "db_error": "Erro Crítico: Falha na conexão com o banco de dados.",
                "product": "Produto:",
                "search_placeholder": "Digite código ou descrição do produto",
                "clear": "Limpar",
                "register_output": "Registrar Saída",
                "clear_fields": "Limpar Campos",
                "select_product": "Selecione um produto",
                "select_type_to_list": "Selecione um tipo de item para listar.",
                "invalid_type": "Tipo '{tipo}' inválido.",
                "table_missing": "Tabela '{tabela}' não existe.",
                "no_valid_columns": "Sem colunas válidas em {tabela}.",
                "records_loaded": "{quantidade} registro(s) carregado(s) de {tabela}.",
                "load_error": "Erro ao carregar estoque: {erro}",
                "product_selected": "Produto selecionado: {descricao}",
                "selection_error": "Erro ao selecionar produto: {erro}",
                "warning": "Aviso",
                "error": "Erro",
                "success": "Sucesso",
                "select_product_first": "Selecione um produto da lista primeiro!",
                "enter_meters_or_kilos": "Informe Metros e/ou Kilos maiores que zero para a baixa.",
                "insufficient_stock": "Estoque insuficiente",
                "meters_available": "Metros disponíveis: {valor}",
                "kilos_available": "Kilos disponíveis: {valor}",
                "valid_quantity": "Informe uma quantidade válida (> 0)!",
                "available_value": "Disponível: {valor}",
                "product_not_found": "Produto não encontrado!",
                "output_registered": "✅ Saída registrada!",
                "remaining_balance": "Saldo atual: {valor}",
                "remaining_fabric_balance": "Saldo: {metros} m / {kilos} kg",
                "register_error": "Falha ao registrar saída: {erro}",
                "fields_cleared": "Campos limpos",
                "field_meters": "Metros:",
                "field_kilos": "Kilos:",
                "field_quantity": "Quantidade:",
                "col_id": "ID",
                "col_description": "Descrição",
                "col_code": "Código",
                "col_supplier": "Fornecedor",
                "col_composition": "Composição",
                "col_color": "Cor",
                "col_meters": "Metros",
                "col_kilos": "Kilos",
                "col_quantity": "Quantidade",
                "col_unit": "Unidade",
                "col_type": "Tipo",
                "col_location": "Localização",
                "col_date_entry": "Data",
                "col_notes": "Observações",
                "type_fabrics": "Tecidos",
                "type_trims": "Aviamentos",
                "type_inputs": "Insumos",
                "type_office": "Escritório",
                "type_cleaning": "Limpeza",
                "type_others": "Outros",
            },
            "en_US": {
                "title": "Stock Output",
                "db_error": "Critical Error: Database connection failed.",
                "product": "Product:",
                "search_placeholder": "Type product code or description",
                "clear": "Clear",
                "register_output": "Register Output",
                "clear_fields": "Clear Fields",
                "select_product": "Select a product",
                "select_type_to_list": "Select an item type to list.",
                "invalid_type": "Invalid type '{tipo}'.",
                "table_missing": "Table '{tabela}' does not exist.",
                "no_valid_columns": "No valid columns in {tabela}.",
                "records_loaded": "{quantidade} record(s) loaded from {tabela}.",
                "load_error": "Error loading stock: {erro}",
                "product_selected": "Selected product: {descricao}",
                "selection_error": "Error selecting product: {erro}",
                "warning": "Warning",
                "error": "Error",
                "success": "Success",
                "select_product_first": "Select a product from the list first!",
                "enter_meters_or_kilos": "Enter meters and/or kilos greater than zero for the stock output.",
                "insufficient_stock": "Insufficient stock",
                "meters_available": "Available meters: {valor}",
                "kilos_available": "Available kilos: {valor}",
                "valid_quantity": "Enter a valid quantity (> 0)!",
                "available_value": "Available: {valor}",
                "product_not_found": "Product not found!",
                "output_registered": "✅ Output registered!",
                "remaining_balance": "Current balance: {valor}",
                "remaining_fabric_balance": "Balance: {metros} m / {kilos} kg",
                "register_error": "Failed to register stock output: {erro}",
                "fields_cleared": "Fields cleared",
                "field_meters": "Meters:",
                "field_kilos": "Kilos:",
                "field_quantity": "Quantity:",
                "col_id": "ID",
                "col_description": "Description",
                "col_code": "Code",
                "col_supplier": "Supplier",
                "col_composition": "Composition",
                "col_color": "Color",
                "col_meters": "Meters",
                "col_kilos": "Kilos",
                "col_quantity": "Quantity",
                "col_unit": "Unit",
                "col_type": "Type",
                "col_location": "Location",
                "col_date_entry": "Date",
                "col_notes": "Notes",
                "type_fabrics": "Fabrics",
                "type_trims": "Trims",
                "type_inputs": "Supplies",
                "type_office": "Office",
                "type_cleaning": "Cleaning",
                "type_others": "Others",
            },
            "es_ES": {
                "title": "Salida de Stock",
                "db_error": "Error Crítico: Falló la conexión con la base de datos.",
                "product": "Producto:",
                "search_placeholder": "Escriba código o descripción del producto",
                "clear": "Limpiar",
                "register_output": "Registrar Salida",
                "clear_fields": "Limpiar Campos",
                "select_product": "Seleccione un producto",
                "select_type_to_list": "Seleccione un tipo de artículo para listar.",
                "invalid_type": "Tipo '{tipo}' inválido.",
                "table_missing": "La tabla '{tabela}' no existe.",
                "no_valid_columns": "No hay columnas válidas en {tabela}.",
                "records_loaded": "{quantidade} registro(s) cargado(s) de {tabela}.",
                "load_error": "Error al cargar stock: {erro}",
                "product_selected": "Producto seleccionado: {descricao}",
                "selection_error": "Error al seleccionar producto: {erro}",
                "warning": "Aviso",
                "error": "Error",
                "success": "Éxito",
                "select_product_first": "¡Seleccione primero un producto de la lista!",
                "enter_meters_or_kilos": "Ingrese metros y/o kilos mayores que cero para la salida.",
                "insufficient_stock": "Stock insuficiente",
                "meters_available": "Metros disponibles: {valor}",
                "kilos_available": "Kilos disponibles: {valor}",
                "valid_quantity": "¡Ingrese una cantidad válida (> 0)!",
                "available_value": "Disponible: {valor}",
                "product_not_found": "¡Producto no encontrado!",
                "output_registered": "✅ ¡Salida registrada!",
                "remaining_balance": "Saldo actual: {valor}",
                "remaining_fabric_balance": "Saldo: {metros} m / {kilos} kg",
                "register_error": "Error al registrar la salida: {erro}",
                "fields_cleared": "Campos limpiados",
                "field_meters": "Metros:",
                "field_kilos": "Kilos:",
                "field_quantity": "Cantidad:",
                "col_id": "ID",
                "col_description": "Descripción",
                "col_code": "Código",
                "col_supplier": "Proveedor",
                "col_composition": "Composición",
                "col_color": "Color",
                "col_meters": "Metros",
                "col_kilos": "Kilos",
                "col_quantity": "Cantidad",
                "col_unit": "Unidad",
                "col_type": "Tipo",
                "col_location": "Ubicación",
                "col_date_entry": "Fecha",
                "col_notes": "Observaciones",
                "type_fabrics": "Tejidos",
                "type_trims": "Avíos",
                "type_inputs": "Insumos",
                "type_office": "Oficina",
                "type_cleaning": "Limpieza",
                "type_others": "Otros",
            },
        }
        base = textos.get(idioma, textos["pt_BR"])
        return base.get(chave, chave).format(**kwargs)

    def _get_tipo_texto(self, tipo_interno):
        mapa = {
            "Tecidos": "type_fabrics",
            "Aviamentos": "type_trims",
            "Insumos": "type_inputs",
            "Escritorio": "type_office",
            "Limpeza": "type_cleaning",
            "Outros": "type_others",
        }
        return self._get_text(mapa.get(tipo_interno, tipo_interno))

    def _get_tipo_por_texto(self, texto_exibido):
        for tipo in self.tipos:
            if texto_exibido == self._get_tipo_texto(tipo):
                return tipo
        return texto_exibido if texto_exibido in self.tipos else self.tipos[0]

    def _get_date_pattern(self):
        idioma = self._get_idioma_atual()
        return {"pt_BR": "%d/%m/%Y", "en_US": "%m/%d/%Y", "es_ES": "%d/%m/%Y"}.get(idioma, "%d/%m/%Y")

    def _get_datetime_pattern(self):
        idioma = self._get_idioma_atual()
        return {"pt_BR": "%d/%m/%Y %H:%M", "en_US": "%m/%d/%Y %I:%M %p", "es_ES": "%d/%m/%Y %H:%M"}.get(idioma, "%d/%m/%Y %H:%M")

    def _formatar_data_localizada(self, valor):
        if valor in (None, ""):
            return ""

        if isinstance(valor, datetime):
            if valor.hour == 0 and valor.minute == 0 and valor.second == 0:
                return valor.strftime(self._get_date_pattern())
            return valor.strftime(self._get_datetime_pattern())

        texto = str(valor).strip()
        if not texto:
            return ""

        formatos_teste = (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
        )
        for fmt in formatos_teste:
            try:
                dt = datetime.strptime(texto, fmt)
                if fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                    return dt.strftime(self._get_date_pattern())
                if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
                    return dt.strftime(self._get_date_pattern())
                return dt.strftime(self._get_datetime_pattern())
            except Exception:
                continue
        return texto

    # =========================
    # TEMA
    # =========================
    def _get_cor_fundo(self):
        return getattr(self.sistema, "cor_fundo", "#ffffff") if ctk.get_appearance_mode() == "Dark" else "#ffffff"

    def obter_cores_por_tema(self, origem=None):
        tema_atual = ctk.get_appearance_mode()
        if tema_atual == "Dark":
            self.cor_fundo = getattr(origem, "cor_fundo", "#020617")
            self.cor_primaria = getattr(origem, "cor_primaria", "#1f2937")
            self.cor_secundaria = getattr(origem, "cor_secundaria", "#111827")
            self.cor_terciaria = getattr(origem, "cor_terciaria", "#0b1220")
            self.cor_texto = getattr(origem, "cor_texto", "#e5e7eb")
            self.cor_texto_entry = "white"
            self.cor_placeholder = "#888888"
            self.cor_borda = getattr(origem, "cor_borda", "#273244")
            self.cor_hover = getattr(origem, "cor_hover", "#334155")
            self.cor_sucesso = getattr(origem, "cor_sucesso", "#22c55e")
            self.cor_alerta = getattr(origem, "cor_alerta", "#ef4444")
        else:
            self.cor_fundo = "#ffffff"
            self.cor_primaria = "#3a7ebf"
            self.cor_secundaria = "#f0f0f0"
            self.cor_terciaria = "#e0e0e0"
            self.cor_texto = "black"
            self.cor_texto_entry = "black"
            self.cor_placeholder = "#666666"
            self.cor_borda = "#cccccc"
            self.cor_hover = "#2e4a66"
            self.cor_sucesso = "#22c55e"
            self.cor_alerta = "#ef4444"
        try:
            self.cor_hover = ajustar_hover(self.cor_primaria, fator=0.9)
        except Exception:
            pass

    # =========================
    # UI
    # =========================
    def setup_ui(self):
        self.obter_cores_por_tema(self.sistema)

        top_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        top_frame.pack(fill="x", padx=10, pady=10)

        self._ui_refs["title_label"] = ctk.CTkLabel(top_frame, text=self._get_text("title"), font=("Arial", 18, "bold"), text_color=self.cor_texto)
        self._ui_refs["title_label"].pack(side="left", padx=10)

        self.tipo_var = ctk.StringVar(value=self._get_tipo_texto(self.tipos[0]))
        self._ui_refs["type_menu"] = ctk.CTkOptionMenu(
            top_frame,
            variable=self.tipo_var,
            values=[self._get_tipo_texto(t) for t in self.tipos],
            command=self.atualizar_interface,
            fg_color=self.cor_secundaria,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover,
        )
        self._ui_refs["type_menu"].pack(side="right", padx=10, fill="x", expand=True)

        self.selecao_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        self.selecao_frame.pack(fill="x", padx=10, pady=10)

        self._ui_refs["product_label"] = ctk.CTkLabel(self.selecao_frame, text=self._get_text("product"), width=80, text_color=self.cor_texto)
        self._ui_refs["product_label"].pack(side="left", padx=5)

        self.entry_produto = ctk.CTkEntry(
            self.selecao_frame,
            placeholder_text=self._get_text("search_placeholder"),
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry,
            placeholder_text_color=self.cor_placeholder,
        )
        self.entry_produto.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_produto.bind("<KeyRelease>", self.filtrar_produtos)
        self._ui_refs["search_entry"] = self.entry_produto

        self._ui_refs["clear_button"] = ctk.CTkButton(self.selecao_frame, text=self._get_text("clear"), width=80, command=self.limpar_pesquisa, fg_color=self.cor_primaria, hover_color=self.cor_hover, text_color=self.cor_texto)
        self._ui_refs["clear_button"].pack(side="left", padx=5)

        self.campos_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        self.campos_frame.pack(fill="x", padx=10, pady=10)

        button_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        button_frame.pack(fill="x", padx=10, pady=5)

        self._ui_refs["register_button"] = ctk.CTkButton(button_frame, text=self._get_text("register_output"), command=self.registrar_saida, fg_color=self.cor_sucesso, hover_color=self.cor_hover, text_color=self.cor_texto)
        self._ui_refs["register_button"].pack(side="left", padx=5)

        self._ui_refs["clear_fields_button"] = ctk.CTkButton(button_frame, text=self._get_text("clear_fields"), command=self.limpar_campos, fg_color=self.cor_primaria, hover_color=self.cor_hover, text_color=self.cor_texto)
        self._ui_refs["clear_fields_button"].pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(self, text=self._get_text("select_product"), text_color=self.cor_texto)
        self.status_label.pack(pady=5)
        self._ui_refs["status_label"] = self.status_label

        self.tree_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.configurar_treeview_theme()
        self.tree = ttk.Treeview(self.tree_frame, show="headings", style="Custom.Treeview")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.selecionar_para_saida)

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def refresh_texts(self):
        self._ui_refs["title_label"].configure(text=self._get_text("title"))
        self._ui_refs["product_label"].configure(text=self._get_text("product"))
        self._ui_refs["search_entry"].configure(placeholder_text=self._get_text("search_placeholder"))
        self._ui_refs["clear_button"].configure(text=self._get_text("clear"))
        self._ui_refs["register_button"].configure(text=self._get_text("register_output"))
        self._ui_refs["clear_fields_button"].configure(text=self._get_text("clear_fields"))
        self.status_label.configure(text=self._get_text("select_product"))
        atual_interno = self._get_tipo_por_texto(self.tipo_var.get())
        self._ui_refs["type_menu"].configure(values=[self._get_tipo_texto(t) for t in self.tipos])
        self.tipo_var.set(self._get_tipo_texto(atual_interno))
        self._atualizar_cabecalhos_tree()
        self.configurar_campos_saida(atual_interno)

    # =========================
    # DADOS
    # =========================
    def _tabela_por_tipo(self, tipo):
        return {
            "Tecidos": "estoque_tecidos",
            "Aviamentos": "estoque_aviamentos",
            "Insumos": "estoque_insumos",
            "Escritorio": "estoque_escritorio",
            "Limpeza": "estoque_limpeza",
            "Outros": "estoque_outros",
        }.get(tipo, "").lower()

    def _colunas_preferidas_por_tipo(self, tipo):
        if tipo == "Tecidos":
            return ["id", "codigo", "descricao", "cor", "fornecedor", "composicao", "metros", "kilos", "data_entrada", "observacoes"]
        if tipo == "Aviamentos":
            return ["id", "codigo", "descricao", "fornecedor", "cor", "quantidade", "unidade", "data_entrada", "observacoes"]
        return ["id", "codigo", "descricao", "tipo", "quantidade", "unidade", "localizacao", "data_entrada", "observacoes"]

    def _campos_existentes(self, tabela, candidatos):
        try:
            cols = set(db.list_columns(tabela))
            return [c for c in candidatos if c in cols]
        except Exception:
            return candidatos

    def _texto_coluna(self, coluna):
        mapa = {
            "id": "col_id",
            "descricao": "col_description",
            "codigo": "col_code",
            "fornecedor": "col_supplier",
            "composicao": "col_composition",
            "cor": "col_color",
            "metros": "col_meters",
            "kilos": "col_kilos",
            "quantidade": "col_quantity",
            "unidade": "col_unit",
            "tipo": "col_type",
            "localizacao": "col_location",
            "data_entrada": "col_date_entry",
            "observacoes": "col_notes",
        }
        return self._get_text(mapa.get(coluna, coluna))

    def _atualizar_cabecalhos_tree(self):
        for coluna in self._column_keys:
            self.tree.heading(coluna, text=self._texto_coluna(coluna))

    def formatar_valor_tree(self, v, campo=None):
        if v is None:
            return ""
        if campo == "data_entrada":
            return self._formatar_data_localizada(v)
        if campo in ("metros", "kilos"):
            casas = 3 if campo == "kilos" else 2
            try:
                return f"{float(v):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except Exception:
                return str(v)
        return str(v)

    def carregar_estoque(self, tipo=None, filtro_termo=None):
        self.configurar_treeview_theme()
        tipo = tipo or self._get_tipo_por_texto(self.tipo_var.get())
        if not tipo:
            self.status_label.configure(text=self._get_text("select_type_to_list"), text_color=self.cor_alerta)
            return

        tabela = self._tabela_por_tipo(tipo)
        if not tabela:
            self.status_label.configure(text=self._get_text("invalid_type", tipo=tipo), text_color=self.cor_alerta)
            return

        try:
            if not db.table_exists(tabela):
                self.status_label.configure(text=self._get_text("table_missing", tabela=tabela), text_color=self.cor_alerta)
                return

            colunas = self._campos_existentes(tabela, self._colunas_preferidas_por_tipo(tipo))
            if not colunas:
                self.status_label.configure(text=self._get_text("no_valid_columns", tabela=tabela), text_color=self.cor_alerta)
                return

            where_extra = ""
            params = []
            if filtro_termo:
                where_extra = " AND (descricao ILIKE %s OR codigo ILIKE %s)"
                like = f"%{filtro_termo}%"
                params.extend([like, like])

            sql = f"SELECT {', '.join(colunas)} FROM {tabela} WHERE 1=1 {where_extra} ORDER BY id DESC"

            rows = []
            if hasattr(db, "fetch_all"):
                rows = db.fetch_all(sql, params) or []
            elif hasattr(db, "query"):
                rows = db.query(sql, params) or []
            else:
                with db.get_conn_cursor() as (_conn, cur):
                    cur.execute(sql, params)
                    rows = cur.fetchall()

            for i in self.tree.get_children():
                self.tree.delete(i)

            self.tree.configure(columns=colunas, show="headings", style="Custom.Treeview")
            self._column_keys = list(colunas)

            for c in colunas:
                largura = 110 if c in ("descricao", "fornecedor", "composicao", "observacoes") else 90
                if c == "data_entrada":
                    largura = 130
                self.tree.heading(c, text=self._texto_coluna(c))
                self.tree.column(c, width=largura, anchor="w")

            for row in rows:
                if isinstance(row, dict):
                    valores = [row.get(c, "") for c in colunas]
                else:
                    valores = row
                self.tree.insert("", "end", values=[self.formatar_valor_tree(v, c) for c, v in zip(colunas, valores)])

            self.status_label.configure(
                text=self._get_text("records_loaded", quantidade=len(rows), tabela=tabela),
                text_color=self.cor_sucesso,
            )
        except Exception as e:
            self.status_label.configure(text=self._get_text("load_error", erro=e), text_color=self.cor_alerta)

    def atualizar_interface(self, tipo):
        tipo_interno = self._get_tipo_por_texto(tipo)
        if tipo_interno not in self.tipos:
            return
        self.tipo_var.set(self._get_tipo_texto(tipo_interno))
        self.limpar_campos()
        self.limpar_pesquisa()
        self.configurar_campos_saida(tipo_interno)

    def configurar_treeview_theme(self):
        style = ttk.Style()
        style.theme_use("default")
        if ctk.get_appearance_mode() == "Dark":
            cor_fundo = self.cor_secundaria
            cor_texto = "white"
        else:
            cor_fundo = "#f0f0f0"
            cor_texto = "black"

        style.configure("Custom.Treeview", background=cor_fundo, foreground=cor_texto, fieldbackground=cor_fundo, borderwidth=0, highlightthickness=0)
        style.configure("Custom.Treeview.Heading", background=self.cor_primaria, foreground=cor_texto, relief="flat", borderwidth=1)
        style.map("Custom.Treeview", background=[("selected", self.cor_primaria)], foreground=[("selected", "white")])

    def configurar_campos_saida(self, tipo):
        for widget in self.campos_frame.winfo_children():
            widget.destroy()
        self.entries = {}

        campos = [("metros", "field_meters"), ("kilos", "field_kilos")] if tipo == "Tecidos" else [("quantidade", "field_quantity")]
        for chave, texto in campos:
            frame = ctk.CTkFrame(self.campos_frame, fg_color=self.cor_fundo)
            frame.pack(fill="x", padx=5, pady=3)

            ctk.CTkLabel(frame, text=self._get_text(texto), width=150, text_color=self.cor_texto).pack(side="left", padx=5)
            entry = ctk.CTkEntry(
                frame,
                placeholder_text="0,00" if chave in ("metros", "kilos") else "0",
                fg_color=self.cor_terciaria,
                border_color=self.cor_borda,
                text_color=self.cor_texto_entry,
                placeholder_text_color=self.cor_placeholder,
            )
            entry.pack(side="left", fill="x", expand=True)
            self.entries[chave] = entry

    # =========================
    # AÇÕES
    # =========================
    def filtrar_produtos(self, event=None):
        self.carregar_estoque(self._get_tipo_por_texto(self.tipo_var.get()), (self.entry_produto.get() or "").strip())

    def limpar_pesquisa(self):
        self.entry_produto.delete(0, "end")
        self.carregar_estoque(self._get_tipo_por_texto(self.tipo_var.get()))

    def selecionar_para_saida(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        item = self.tree.item(item_id)
        dados = dict(zip(self.tree["columns"], item["values"]))
        try:
            self.id_selecionado = dados.get("id", item_id)
            descricao = dados.get("descricao", "Produto")
            codigo = dados.get("codigo", "")
            self.entry_produto.delete(0, "end")
            self.entry_produto.insert(0, f"{descricao} ({codigo})" if codigo else descricao)
            self.status_label.configure(text=self._get_text("product_selected", descricao=descricao), text_color=self.cor_sucesso)
        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("selection_error", erro=e))

    def _to_float(self, txt):
        if txt is None:
            return None
        s = str(txt).strip()
        if not s:
            return None
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    def _to_int(self, txt):
        f = self._to_float(txt)
        return None if f is None else int(f)

    def registrar_saida(self):
        if not self.id_selecionado:
            messagebox.showwarning(self._get_text("warning"), self._get_text("select_product_first"))
            return

        tipo = self._get_tipo_por_texto(self.tipo_var.get())
        tabela = self._tabela_por_tipo(tipo)
        dados_saida = {k: (v.get().strip() if v else "") for k, v in self.entries.items()}

        try:
            with db.get_conn_cursor() as (_conn, cur):
                if tipo == "Tecidos":
                    cur.execute(
                        "SELECT id, descricao, codigo, metros, kilos FROM estoque_tecidos WHERE id = %s FOR UPDATE",
                        (self.id_selecionado,),
                    )
                    produto = cur.fetchone()
                    if not produto:
                        messagebox.showerror(self._get_text("error"), self._get_text("product_not_found"))
                        return

                    metros_atual = float(produto.get("metros", 0) or 0)
                    kilos_atual = float(produto.get("kilos", 0) or 0)
                    v_metros = self._to_float(dados_saida.get("metros"))
                    v_kilos = self._to_float(dados_saida.get("kilos"))

                    if (v_metros is None or v_metros <= 0) and (v_kilos is None or v_kilos <= 0):
                        messagebox.showwarning(self._get_text("warning"), self._get_text("enter_meters_or_kilos"))
                        return

                    if v_metros and v_metros > metros_atual:
                        messagebox.showwarning(self._get_text("insufficient_stock"), self._get_text("meters_available", valor=self.formatar_valor_tree(metros_atual, "metros")))
                        return
                    if v_kilos and v_kilos > kilos_atual:
                        messagebox.showwarning(self._get_text("insufficient_stock"), self._get_text("kilos_available", valor=self.formatar_valor_tree(kilos_atual, "kilos")))
                        return

                    updates, params = [], []
                    if v_metros and v_metros > 0:
                        updates.append("metros = GREATEST(metros - %s, 0)")
                        params.append(v_metros)
                    if v_kilos and v_kilos > 0:
                        updates.append("kilos = GREATEST(kilos - %s, 0)")
                        params.append(v_kilos)

                    params.append(self.id_selecionado)
                    cur.execute(f"UPDATE estoque_tecidos SET {', '.join(updates)} WHERE id = %s RETURNING metros, kilos", params)
                    saldo = cur.fetchone() or {}
                    msg = f"{self._get_text('output_registered')}\n{self._get_text('remaining_fabric_balance', metros=self.formatar_valor_tree(float(saldo.get('metros', 0) or 0), 'metros'), kilos=self.formatar_valor_tree(float(saldo.get('kilos', 0) or 0), 'kilos'))}"
                else:
                    cur.execute(f"SELECT id, descricao, codigo, quantidade FROM {tabela} WHERE id = %s FOR UPDATE", (self.id_selecionado,))
                    produto = cur.fetchone()
                    if not produto:
                        messagebox.showerror(self._get_text("error"), self._get_text("product_not_found"))
                        return

                    qtd_atual = int(produto.get("quantidade", 0) or 0)
                    qnt_saida = self._to_int(dados_saida.get("quantidade"))
                    if qnt_saida is None or qnt_saida <= 0:
                        messagebox.showwarning(self._get_text("warning"), self._get_text("valid_quantity"))
                        return
                    if qnt_saida > qtd_atual:
                        messagebox.showwarning(self._get_text("insufficient_stock"), self._get_text("available_value", valor=qtd_atual))
                        return

                    cur.execute(f"UPDATE {tabela} SET quantidade = GREATEST(quantidade - %s, 0) WHERE id = %s RETURNING quantidade", (qnt_saida, self.id_selecionado))
                    saldo = cur.fetchone() or {}
                    msg = f"{self._get_text('output_registered')}\n{self._get_text('remaining_balance', valor=int(saldo.get('quantidade', 0) or 0))}"

                messagebox.showinfo(self._get_text("success"), msg)

            self.carregar_estoque(tipo)
            self.limpar_campos()
        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("register_error", erro=e))

    def limpar_campos(self):
        for entry in self.entries.values():
            entry.delete(0, "end")
        self.id_selecionado = None
        self.status_label.configure(text=self._get_text("fields_cleared"), text_color=self.cor_texto)


if __name__ == "__main__":
    class SistemaMock:
        def __init__(self):
            self.idioma_atual = "pt_BR"

    app = ctk.CTk()
    app.geometry("1000x700")
    app.title("Sistema de Saída de Estoque")
    pagina = SaidaEstoqueApp(app, sistema=SistemaMock())
    pagina.pack(fill="both", expand=True)
    app.mainloop()

# --- AUTO_PAGE_TRANSLATIONS (gerado automaticamente) ---
from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support as _attach_i18n_support

AUTO_PAGE_TRANSLATIONS = {
    "SaidaEstoqueApp": {
        "pt_BR": {"title": "Saida Estoque", "Atualizar": "Atualizar", "Filtrar": "Filtrar", "Salvar": "Salvar", "Cancelar": "Cancelar"},
        "en_US": {"title": "Saida Estoque", "Atualizar": "Refresh", "Filtrar": "Filter", "Salvar": "Save", "Cancelar": "Cancel"},
        "es_ES": {"title": "Saida Estoque", "Atualizar": "Actualizar", "Filtrar": "Filtrar", "Salvar": "Guardar", "Cancelar": "Cancelar"},
    },
}

for _cls_name, _map in AUTO_PAGE_TRANSLATIONS.items():
    _cls = globals().get(_cls_name)
    if isinstance(_cls, type):
        if not hasattr(_cls, "TRANSLATIONS") and not hasattr(_cls, "_TRANSLATIONS"):
            _cls.TRANSLATIONS = _map
        _attach_i18n_support(_cls, getattr(_cls, "TRANSLATIONS", getattr(_cls, "_TRANSLATIONS", _map)))
