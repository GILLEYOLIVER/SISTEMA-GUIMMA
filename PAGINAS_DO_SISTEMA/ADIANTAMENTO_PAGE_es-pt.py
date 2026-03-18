# -*- coding: utf-8 -*-
from PAGINAS_DO_SISTEMA import TEMAS
import customtkinter as ctk
from tkinter import messagebox, filedialog
from tkinter import ttk
from datetime import datetime
import os
import sys
import subprocess

# ---- Banco de dados (PostgreSQL) ----
try:
    from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db
except ModuleNotFoundError:
    import importlib.util

    CANDIDATES = [
        os.path.join(os.path.dirname(__file__), "BANCO_DE_DADOS_PG.py"),
        os.path.join(os.path.dirname(__file__), "..", "BANCO_DE_DADOS_PG.py"),
        r"C:\Users\User\Desktop\sistema\SISTEMA\BANCO_DE_DADOS_PG.py",
    ]
    db = None
    for _p in CANDIDATES:
        if os.path.isfile(_p):
            _spec = importlib.util.spec_from_file_location("BANCO_DE_DADOS_PG", _p)
            db = importlib.util.module_from_spec(_spec)
            sys.modules["BANCO_DE_DADOS_PG"] = db
            _spec.loader.exec_module(db)
            break
    if db is None:
        raise

# ---- ReportLab (impressão PDF) ----
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors


class PagamentoAdiantamentoPage(ctk.CTkFrame):
    TRANSLATIONS = {
        "pt_BR": {
            "title": "CONTROLE DE ADIANTAMENTOS PARA FACÇÕES",
            "search_type": "Tipo:",
            "search_provider": "Prestador:",
            "search_term": "Busca:",
            "search_placeholder": "Código/ordem/descrição...",
            "search_button": "Buscar",
            "search_all": "Todos",
            "advancement_data": "DADOS DO ADIANTAMENTO",
            "provider_type": "Tipo Prestador:",
            "provider_name": "Costureira/Prestador:",
            "model_code": "Código do Modelo:",
            "description": "Descrição:",
            "amount": "Valor (R$):",
            "payment_method": "Forma de Pagamento:",
            "cash_payment": "À Vista",
            "installment_payment": "Parcelado",
            "installments": "Nº Parcelas:",
            "date_time": "Data/Hora:",
            "print_receipt": "Imprimir Comprovante",
            "register_advancement": "Registrar Adiantamento",
            "clear": "Limpar",
            "table_id": "ID",
            "table_code": "Código",
            "table_provider": "Prestador",
            "table_type": "Tipo",
            "table_service": "Serviço",
            "table_status": "Status",
            "table_sent_date": "Data Envio",
            "table_pieces_qty": "Qtd Peças",
            "status_returned": "Retornado",
            "status_in_progress": "Em andamento",
            "database_not_ready": "Banco não preparado",
            "database_not_ready_message": "Não foi possível conectar ao banco de dados.\n\nVerifique OPERA_PG_DSN/OPERA_PG_SCHEMA e rode os scripts.",
            "error": "Erro",
            "warning": "Aviso",
            "success": "Sucesso",
            "invalid_value_title": "Valor Inválido",
            "invalid_installments_title": "Parcelas Inválidas",
            "select_cut_warning": "Selecione um corte na tabela.",
            "invalid_cut_data": "Dados do corte inválidos.",
            "enter_advancement_amount": "Informe o valor do adiantamento.",
            "positive_numeric_value": "Informe um valor numérico positivo.",
            "invalid_installments": "Número de parcelas inválido.",
            "register_success": "Adiantamento registrado com sucesso!",
            "no_record_inserted": "Nenhum registro foi inserido no banco.",
            "search_services_error": "Falha ao buscar serviços:\n{erro}",
            "register_advancement_error": "Falha ao registrar adiantamento:\n{erro}",
            "generate_receipt_error": "Erro ao gerar comprovante:\n{erro}",
            "save_receipt_as": "Salvar Comprovante como",
            "pdf_files": "Arquivos PDF",
            "receipt_generated": "Comprovante gerado com sucesso:\n{caminho}",
            "description_not_found": "Descrição não encontrada",
            "receipt_title": "COMPROVANTE DE ADIANTAMENTO",
            "copy_label": "VIA {numero}",
            "company_name": "OPERA FASHION",
            "company_cnpj": "CNPJ: 053222550001-94",
            "company_address": "Endereço: RUA ALFREDO NASCER QUADRA QI 05 LOTE 20 CONJUNTO VERA CRUZ 1",
            "receipt_provider": "Facção:",
            "receipt_model_code": "Código do Modelo:",
            "receipt_description": "Descrição:",
            "receipt_amount": "Valor:",
            "receipt_payment_method": "Forma de Pagamento:",
            "receipt_installments": "Parcelas:",
            "receipt_date_time": "Data/Hora:",
            "receipt_signature": "Assinatura do Recebedor:",
            "receipt_filename_prefix": "Adiantamento",
        },
        "en_US": {
            "title": "ADVANCE PAYMENT CONTROL FOR CONTRACTORS",
            "search_type": "Type:",
            "search_provider": "Provider:",
            "search_term": "Search:",
            "search_placeholder": "Code/order/description...",
            "search_button": "Search",
            "search_all": "All",
            "advancement_data": "ADVANCE PAYMENT DETAILS",
            "provider_type": "Provider Type:",
            "provider_name": "Seamstress/Provider:",
            "model_code": "Model Code:",
            "description": "Description:",
            "amount": "Amount:",
            "payment_method": "Payment Method:",
            "cash_payment": "Cash",
            "installment_payment": "Installments",
            "installments": "No. of Installments:",
            "date_time": "Date/Time:",
            "print_receipt": "Print Receipt",
            "register_advancement": "Register Advance",
            "clear": "Clear",
            "table_id": "ID",
            "table_code": "Code",
            "table_provider": "Provider",
            "table_type": "Type",
            "table_service": "Service",
            "table_status": "Status",
            "table_sent_date": "Sent Date",
            "table_pieces_qty": "Qty Pieces",
            "status_returned": "Returned",
            "status_in_progress": "In progress",
            "database_not_ready": "Database not ready",
            "database_not_ready_message": "Could not connect to the database.\n\nCheck OPERA_PG_DSN/OPERA_PG_SCHEMA and run the scripts.",
            "error": "Error",
            "warning": "Warning",
            "success": "Success",
            "invalid_value_title": "Invalid Value",
            "invalid_installments_title": "Invalid Installments",
            "select_cut_warning": "Select a cut in the table.",
            "invalid_cut_data": "Invalid cut data.",
            "enter_advancement_amount": "Enter the advance payment amount.",
            "positive_numeric_value": "Enter a positive numeric value.",
            "invalid_installments": "Invalid number of installments.",
            "register_success": "Advance payment registered successfully!",
            "no_record_inserted": "No record was inserted into the database.",
            "search_services_error": "Failed to search services:\n{erro}",
            "register_advancement_error": "Failed to register advance payment:\n{erro}",
            "generate_receipt_error": "Error generating receipt:\n{erro}",
            "save_receipt_as": "Save Receipt As",
            "pdf_files": "PDF Files",
            "receipt_generated": "Receipt generated successfully:\n{caminho}",
            "description_not_found": "Description not found",
            "receipt_title": "ADVANCE PAYMENT RECEIPT",
            "copy_label": "COPY {numero}",
            "company_name": "OPERA FASHION",
            "company_cnpj": "CNPJ: 053222550001-94",
            "company_address": "Address: RUA ALFREDO NASCER QUADRA QI 05 LOTE 20 CONJUNTO VERA CRUZ 1",
            "receipt_provider": "Contractor:",
            "receipt_model_code": "Model Code:",
            "receipt_description": "Description:",
            "receipt_amount": "Amount:",
            "receipt_payment_method": "Payment Method:",
            "receipt_installments": "Installments:",
            "receipt_date_time": "Date/Time:",
            "receipt_signature": "Receiver Signature:",
            "receipt_filename_prefix": "Advance",
        },
        "es_ES": {
            "title": "CONTROL DE ADELANTOS PARA TALLERES",
            "search_type": "Tipo:",
            "search_provider": "Prestador:",
            "search_term": "Búsqueda:",
            "search_placeholder": "Código/orden/descripción...",
            "search_button": "Buscar",
            "search_all": "Todos",
            "advancement_data": "DATOS DEL ADELANTO",
            "provider_type": "Tipo de Prestador:",
            "provider_name": "Costurera/Prestador:",
            "model_code": "Código del Modelo:",
            "description": "Descripción:",
            "amount": "Valor:",
            "payment_method": "Forma de Pago:",
            "cash_payment": "Al Contado",
            "installment_payment": "En Cuotas",
            "installments": "Nº de Cuotas:",
            "date_time": "Fecha/Hora:",
            "print_receipt": "Imprimir Comprobante",
            "register_advancement": "Registrar Adelanto",
            "clear": "Limpiar",
            "table_id": "ID",
            "table_code": "Código",
            "table_provider": "Prestador",
            "table_type": "Tipo",
            "table_service": "Servicio",
            "table_status": "Estado",
            "table_sent_date": "Fecha Envío",
            "table_pieces_qty": "Cant. Piezas",
            "status_returned": "Devuelto",
            "status_in_progress": "En curso",
            "database_not_ready": "Base de datos no preparada",
            "database_not_ready_message": "No fue posible conectar a la base de datos.\n\nVerifique OPERA_PG_DSN/OPERA_PG_SCHEMA y ejecute los scripts.",
            "error": "Error",
            "warning": "Aviso",
            "success": "Éxito",
            "invalid_value_title": "Valor Inválido",
            "invalid_installments_title": "Cuotas Inválidas",
            "select_cut_warning": "Seleccione un corte en la tabla.",
            "invalid_cut_data": "Datos del corte inválidos.",
            "enter_advancement_amount": "Informe el valor del adelanto.",
            "positive_numeric_value": "Informe un valor numérico positivo.",
            "invalid_installments": "Número de cuotas inválido.",
            "register_success": "¡Adelanto registrado con éxito!",
            "no_record_inserted": "No se insertó ningún registro en la base de datos.",
            "search_services_error": "Error al buscar servicios:\n{erro}",
            "register_advancement_error": "Error al registrar adelanto:\n{erro}",
            "generate_receipt_error": "Error al generar el comprobante:\n{erro}",
            "save_receipt_as": "Guardar Comprobante como",
            "pdf_files": "Archivos PDF",
            "receipt_generated": "Comprobante generado con éxito:\n{caminho}",
            "description_not_found": "Descripción no encontrada",
            "receipt_title": "COMPROBANTE DE ADELANTO",
            "copy_label": "VÍA {numero}",
            "company_name": "OPERA FASHION",
            "company_cnpj": "CNPJ: 053222550001-94",
            "company_address": "Dirección: RUA ALFREDO NASCER QUADRA QI 05 LOTE 20 CONJUNTO VERA CRUZ 1",
            "receipt_provider": "Taller:",
            "receipt_model_code": "Código del Modelo:",
            "receipt_description": "Descripción:",
            "receipt_amount": "Valor:",
            "receipt_payment_method": "Forma de Pago:",
            "receipt_installments": "Cuotas:",
            "receipt_date_time": "Fecha/Hora:",
            "receipt_signature": "Firma del Receptor:",
            "receipt_filename_prefix": "Adelanto",
        },
    }

    PROVIDER_TYPE_FALLBACKS = {
        "pt_BR": ["Todos", "Faccao", "Bordado", "Lavanderia", "Passadoria", "Corte", "Acabamento"],
        "en_US": ["All", "Sewing", "Embroidery", "Laundry", "Ironing", "Cutting", "Finishing"],
        "es_ES": ["Todos", "Costura", "Bordado", "Lavandería", "Planchado", "Corte", "Acabado"],
    }

    def __init__(self, parent, sistema=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.sistema = sistema
        self._ui_refs = {}
        self._language_maps = {"provider_type": {}}
        self.idioma_atual = self._obter_idioma_inicial()
        self._apply_palette()

        if not db.ready_check():
            messagebox.showerror(
                self._get_text("database_not_ready"),
                self._get_text("database_not_ready_message")
            )
            raise SystemExit(1)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self.header = ctk.CTkLabel(
            self,
            text=self._get_text("title"),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.C("cor_texto"),
            anchor="w"
        )
        self.header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self._ui_refs["title_label"] = self.header

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)

        search_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.lbl_tipo_busca = ctk.CTkLabel(search_frame, text=self._get_text("search_type"), text_color=self.C("cor_texto"))
        self.lbl_tipo_busca.pack(side="left", padx=(0, 6))
        self._ui_refs["search_type_label"] = self.lbl_tipo_busca

        self.tipo_busca_var = ctk.StringVar(value=self._get_text("search_all"))
        self.combo_tipo_busca = ctk.CTkComboBox(
            search_frame,
            variable=self.tipo_busca_var,
            values=[self._get_text("search_all")],
            width=140,
            command=lambda _v=None: self._on_tipo_busca_changed(),
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            button_color=self.C("cor_primaria"),
            button_hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            dropdown_fg_color=self.C("cor_secundaria"),
            dropdown_hover_color=self.C("cor_hover"),
            dropdown_text_color=self.C("cor_texto")
        )
        self.combo_tipo_busca.pack(side="left", padx=(0, 10))

        self.lbl_prestador_busca = ctk.CTkLabel(search_frame, text=self._get_text("search_provider"), text_color=self.C("cor_texto"))
        self.lbl_prestador_busca.pack(side="left", padx=(0, 6))
        self._ui_refs["search_provider_label"] = self.lbl_prestador_busca

        self.prestador_busca_var = ctk.StringVar(value="")
        self.combo_prestador_busca = ctk.CTkComboBox(
            search_frame,
            variable=self.prestador_busca_var,
            values=[""],
            width=220,
            command=lambda _v=None: None,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            button_color=self.C("cor_primaria"),
            button_hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            dropdown_fg_color=self.C("cor_secundaria"),
            dropdown_hover_color=self.C("cor_hover"),
            dropdown_text_color=self.C("cor_texto")
        )
        self.combo_prestador_busca.pack(side="left", padx=(0, 10))

        self.lbl_busca = ctk.CTkLabel(search_frame, text=self._get_text("search_term"), text_color=self.C("cor_texto"))
        self.lbl_busca.pack(side="left", padx=(0, 6))
        self._ui_refs["search_term_label"] = self.lbl_busca

        self.entry_codigo_modelo = ctk.CTkEntry(
            search_frame,
            width=200,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto"),
            placeholder_text=self._get_text("search_placeholder")
        )
        self.entry_codigo_modelo.pack(side="left", padx=(0, 10))
        self.entry_codigo_modelo.bind("<Return>", lambda e: self.buscar_cortes())
        self._ui_refs["search_entry"] = self.entry_codigo_modelo

        self.btn_buscar = ctk.CTkButton(
            search_frame,
            text=self._get_text("search_button"),
            command=self.buscar_cortes,
            width=90,
            fg_color=self.C("cor_destaque"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_buscar.pack(side="left")
        self._ui_refs["search_button"] = self.btn_buscar

        self.tree_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.tree_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        self.tree_columns = ("ID", "Código", "Prestador", "Tipo", "Serviço", "Status", "Data Envio", "Qtd Peças")
        self.tree_column_meta = {
            "ID": {"key": "table_id", "width": 80, "anchor": "center"},
            "Código": {"key": "table_code", "width": 110, "anchor": "center"},
            "Prestador": {"key": "table_provider", "width": 220, "anchor": "w"},
            "Tipo": {"key": "table_type", "width": 110, "anchor": "center"},
            "Serviço": {"key": "table_service", "width": 140, "anchor": "w"},
            "Status": {"key": "table_status", "width": 110, "anchor": "center"},
            "Data Envio": {"key": "table_sent_date", "width": 130, "anchor": "center"},
            "Qtd Peças": {"key": "table_pieces_qty", "width": 90, "anchor": "center"},
        }

        self.tree_cortes = ttk.Treeview(
            self.tree_frame,
            columns=self.tree_columns,
            show="headings",
            height=6
        )
        self.tree_cortes.grid(row=0, column=0, sticky="nsew")
        for col in self.tree_columns:
            info = self.tree_column_meta[col]
            self.tree_cortes.heading(col, text=self._get_text(info["key"]))
            self.tree_cortes.column(col, width=info["width"], anchor=info["anchor"])

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree_cortes.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree_cortes.configure(yscrollcommand=scrollbar.set)
        self.tree_cortes.bind("<Double-1>", self.selecionar_corte)

        adiantamento_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        adiantamento_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        self.lbl_dados_adiantamento = ctk.CTkLabel(
            adiantamento_frame,
            text=self._get_text("advancement_data"),
            font=ctk.CTkFont(weight="bold"),
            text_color=self.C("cor_texto")
        )
        self.lbl_dados_adiantamento.grid(row=0, column=0, columnspan=4, pady=(0, 10), sticky="w")
        self._ui_refs["advancement_title"] = self.lbl_dados_adiantamento

        self.lbl_tipo_form = ctk.CTkLabel(adiantamento_frame, text=self._get_text("provider_type"), text_color=self.C("cor_texto"))
        self.lbl_tipo_form.grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self._ui_refs["provider_type_label"] = self.lbl_tipo_form

        self.tipo_form_var = ctk.StringVar(value=self._get_text("search_all"))
        self.combo_tipo_form = ctk.CTkComboBox(
            adiantamento_frame,
            variable=self.tipo_form_var,
            values=[self._get_text("search_all")],
            width=150,
            command=lambda _v=None: self._on_tipo_form_changed(),
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            button_color=self.C("cor_primaria"),
            button_hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            dropdown_fg_color=self.C("cor_secundaria"),
            dropdown_hover_color=self.C("cor_hover"),
            dropdown_text_color=self.C("cor_texto")
        )
        self.combo_tipo_form.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        self.lbl_prestador_form = ctk.CTkLabel(adiantamento_frame, text=self._get_text("provider_name"), text_color=self.C("cor_texto"))
        self.lbl_prestador_form.grid(row=1, column=2, sticky="e", padx=5, pady=2)
        self._ui_refs["provider_name_label"] = self.lbl_prestador_form

        self.prestador_form_var = ctk.StringVar(value="")
        self.combo_prestador_form = ctk.CTkComboBox(
            adiantamento_frame,
            variable=self.prestador_form_var,
            values=[""],
            width=250,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            button_color=self.C("cor_primaria"),
            button_hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            dropdown_fg_color=self.C("cor_secundaria"),
            dropdown_hover_color=self.C("cor_hover"),
            dropdown_text_color=self.C("cor_texto")
        )
        self.combo_prestador_form.grid(row=1, column=3, sticky="w", padx=5, pady=2)

        self.lbl_codigo_modelo = ctk.CTkLabel(adiantamento_frame, text=self._get_text("model_code"), text_color=self.C("cor_texto"))
        self.lbl_codigo_modelo.grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self._ui_refs["model_code_label"] = self.lbl_codigo_modelo

        self.entry_codigo_modelo_selecionado = ctk.CTkEntry(
            adiantamento_frame,
            width=150,
            state="disabled",
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.entry_codigo_modelo_selecionado.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        self.lbl_descricao_modelo = ctk.CTkLabel(adiantamento_frame, text=self._get_text("description"), text_color=self.C("cor_texto"))
        self.lbl_descricao_modelo.grid(row=3, column=0, sticky="e", padx=5, pady=2)
        self._ui_refs["description_label"] = self.lbl_descricao_modelo

        self.entry_descricao_modelo = ctk.CTkEntry(
            adiantamento_frame,
            width=250,
            state="disabled",
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.entry_descricao_modelo.grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=2)

        self.lbl_valor = ctk.CTkLabel(adiantamento_frame, text=self._get_text("amount"), text_color=self.C("cor_texto"))
        self.lbl_valor.grid(row=4, column=0, sticky="e", padx=5, pady=2)
        self._ui_refs["amount_label"] = self.lbl_valor

        self.entry_valor = ctk.CTkEntry(
            adiantamento_frame,
            width=150,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.entry_valor.grid(row=4, column=1, sticky="w", padx=5, pady=2)

        self.lbl_pagamento = ctk.CTkLabel(adiantamento_frame, text=self._get_text("payment_method"), text_color=self.C("cor_texto"))
        self.lbl_pagamento.grid(row=5, column=0, sticky="e", padx=5, pady=2)
        self._ui_refs["payment_method_label"] = self.lbl_pagamento

        self.pagamento_var = ctk.StringVar(value=self._get_payment_display("cash"))
        self.combo_pagamento = ctk.CTkComboBox(
            adiantamento_frame,
            variable=self.pagamento_var,
            values=self._payment_values(),
            width=150,
            command=self.atualizar_visibilidade_parcelas,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            button_color=self.C("cor_primaria"),
            button_hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            dropdown_fg_color=self.C("cor_secundaria"),
            dropdown_hover_color=self.C("cor_hover"),
            dropdown_text_color=self.C("cor_texto")
        )
        self.combo_pagamento.grid(row=5, column=1, sticky="w", padx=5, pady=2)

        self.label_parcelas = ctk.CTkLabel(adiantamento_frame, text=self._get_text("installments"), text_color=self.C("cor_texto"))
        self.entry_parcelas = ctk.CTkEntry(
            adiantamento_frame,
            width=50,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.entry_parcelas.insert(0, "1")
        self._ui_refs["installments_label"] = self.label_parcelas

        self.lbl_data = ctk.CTkLabel(adiantamento_frame, text=self._get_text("date_time"), text_color=self.C("cor_texto"))
        self.lbl_data.grid(row=7, column=0, sticky="e", padx=5, pady=2)
        self._ui_refs["date_time_label"] = self.lbl_data

        self.label_data = ctk.CTkLabel(
            adiantamento_frame,
            text=self._format_datetime_display(datetime.now()),
            text_color=self.C("cor_texto")
        )
        self.label_data.grid(row=7, column=1, sticky="w", padx=5, pady=2)

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="e", pady=(10, 0))

        self.btn_imprimir = ctk.CTkButton(
            btn_frame,
            text=self._get_text("print_receipt"),
            command=self.imprimir_comprovante,
            width=150,
            state="disabled",
            fg_color=self.C("cor_imprimir"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_imprimir.pack(side="left", padx=5)
        self._ui_refs["print_button"] = self.btn_imprimir

        self.btn_salvar = ctk.CTkButton(
            btn_frame,
            text=self._get_text("register_advancement"),
            command=self.registrar_adiantamento,
            width=180,
            state="disabled",
            fg_color=self.C("cor_adicionar"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_salvar.pack(side="left", padx=5)
        self._ui_refs["save_button"] = self.btn_salvar

        self.btn_limpar = ctk.CTkButton(
            btn_frame,
            text=self._get_text("clear"),
            command=self.limpar_campos,
            width=80,
            fg_color=self.C("cor_secundaria"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_limpar.pack(side="left", padx=5)
        self._ui_refs["clear_button"] = self.btn_limpar

        self._init_prestadores_ui()
        self.atualizar_data_hora()

        try:
            if self.sistema and hasattr(self.sistema, "_aplicar_tema_global"):
                self.sistema._aplicar_tema_global()
        except Exception:
            pass

    # ---------- idioma ----------
    def _obter_idioma_inicial(self):
        for origem in (self.sistema, getattr(self.sistema, "app", None)):
            if origem and hasattr(origem, "idioma_atual"):
                idioma = getattr(origem, "idioma_atual")
                if idioma in self.TRANSLATIONS:
                    return idioma
        return "pt_BR"

    def _get_text(self, key, **kwargs):
        base = self.TRANSLATIONS.get(self.idioma_atual, self.TRANSLATIONS["pt_BR"])
        texto = base.get(key, self.TRANSLATIONS["pt_BR"].get(key, key))
        if kwargs:
            try:
                return texto.format(**kwargs)
            except Exception:
                return texto
        return texto

    def _payment_values(self):
        return [self._get_text("cash_payment"), self._get_text("installment_payment")]

    def _get_payment_display(self, internal_value):
        return self._get_text("cash_payment") if internal_value == "cash" else self._get_text("installment_payment")

    def _get_payment_internal(self, text):
        if text == self._get_text("installment_payment"):
            return "installment"
        return "cash"

    def _map_provider_type_display(self, internal_value):
        mapa = self._language_maps.setdefault("provider_type", {})
        for idioma, values in self.PROVIDER_TYPE_FALLBACKS.items():
            if internal_value in values:
                idx = values.index(internal_value)
                return self.PROVIDER_TYPE_FALLBACKS.get(self.idioma_atual, self.PROVIDER_TYPE_FALLBACKS["pt_BR"])[idx]
        if not mapa:
            return internal_value
        return mapa.get(self.idioma_atual, {}).get(internal_value, internal_value)

    def _map_provider_type_internal(self, display_value):
        mapa = self._language_maps.setdefault("provider_type", {})
        idioma_map = mapa.get(self.idioma_atual, {})
        if display_value in idioma_map:
            return idioma_map[display_value]
        pt_map = mapa.get("pt_BR", {})
        if display_value in pt_map:
            return pt_map[display_value]
        return display_value

    def _update_provider_type_maps(self, internal_types):
        mapa = {}
        for idioma in self.TRANSLATIONS:
            mapa[idioma] = {}
        for idx, internal in enumerate(internal_types):
            for idioma in self.TRANSLATIONS:
                fallbacks = self.PROVIDER_TYPE_FALLBACKS.get(idioma, self.PROVIDER_TYPE_FALLBACKS["pt_BR"])
                display = fallbacks[idx] if idx < len(fallbacks) else internal
                mapa[idioma][display] = internal
        self._language_maps["provider_type"] = mapa

    def _format_datetime_display(self, value):
        if isinstance(value, str):
            texto = value.strip()
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M"):
                try:
                    value = datetime.strptime(texto, fmt)
                    break
                except Exception:
                    continue
            else:
                return texto

        if not isinstance(value, datetime):
            return "" if value is None else str(value)

        if self.idioma_atual == "en_US":
            return value.strftime("%m/%d/%Y %I:%M %p")
        return value.strftime("%d/%m/%Y %H:%M")

    def _format_date_for_table(self, value):
        return self._format_datetime_display(value)

    def _format_currency(self, value):
        try:
            v = float(str(value).replace(",", "."))
        except Exception:
            return "$0.00" if self.idioma_atual == "en_US" else "R$ 0,00"

        if self.idioma_atual == "en_US":
            return f"${v:,.2f}"
        inteiro, frac = f"{v:,.2f}".split(".")
        inteiro = inteiro.replace(",", ".")
        return f"R$ {inteiro},{frac}"

    def refresh_texts(self):
        pagamento_atual = self._get_payment_internal(self.pagamento_var.get())
        tipo_busca_atual = self._map_provider_type_internal(self.tipo_busca_var.get())
        tipo_form_atual = self._map_provider_type_internal(self.tipo_form_var.get())

        self._ui_refs["title_label"].configure(text=self._get_text("title"))
        self._ui_refs["search_type_label"].configure(text=self._get_text("search_type"))
        self._ui_refs["search_provider_label"].configure(text=self._get_text("search_provider"))
        self._ui_refs["search_term_label"].configure(text=self._get_text("search_term"))
        self._ui_refs["search_entry"].configure(placeholder_text=self._get_text("search_placeholder"))
        self._ui_refs["search_button"].configure(text=self._get_text("search_button"))
        self._ui_refs["advancement_title"].configure(text=self._get_text("advancement_data"))
        self._ui_refs["provider_type_label"].configure(text=self._get_text("provider_type"))
        self._ui_refs["provider_name_label"].configure(text=self._get_text("provider_name"))
        self._ui_refs["model_code_label"].configure(text=self._get_text("model_code"))
        self._ui_refs["description_label"].configure(text=self._get_text("description"))
        self._ui_refs["amount_label"].configure(text=self._get_text("amount"))
        self._ui_refs["payment_method_label"].configure(text=self._get_text("payment_method"))
        self._ui_refs["installments_label"].configure(text=self._get_text("installments"))
        self._ui_refs["date_time_label"].configure(text=self._get_text("date_time"))
        self._ui_refs["print_button"].configure(text=self._get_text("print_receipt"))
        self._ui_refs["save_button"].configure(text=self._get_text("register_advancement"))
        self._ui_refs["clear_button"].configure(text=self._get_text("clear"))

        self.combo_pagamento.configure(values=self._payment_values())
        self.pagamento_var.set(self._get_payment_display(pagamento_atual))

        self._init_prestadores_ui(tipo_busca_atual=tipo_busca_atual, tipo_form_atual=tipo_form_atual)
        self._atualizar_cabecalhos_tree()
        self.atualizar_visibilidade_parcelas()
        self.label_data.configure(text=self._format_datetime_display(datetime.now()))

    def _atualizar_cabecalhos_tree(self):
        for col in self.tree_columns:
            info = self.tree_column_meta[col]
            self.tree_cortes.heading(col, text=self._get_text(info["key"]))

    # ---------- tema ----------
    def C(self, nome, default=None):
        if self.sistema and hasattr(self.sistema, nome):
            return getattr(self.sistema, nome)
        defaults = {
            "cor_fundo": "#181818",
            "cor_primaria": "#121212",
            "cor_secundaria": "#1F1F1F",
            "cor_texto": "#EEEEEE",
            "cor_hover": "#2C2C2C",
            "cor_borda": "#3A3A3A",
            "cor_destaque": "#BB86FC",
            "cor_sucesso": "#03DAC6",
            "cor_alerta": "#CF6679",
            "cor_adicionar": "#03DAC6",
            "cor_imprimir": "#CF6679",
        }
        return defaults.get(nome, default)

    def _apply_palette(self):
        self.configure(fg_color=self.C("cor_fundo"))

    def _pg_exec(self, sql: str, params=None) -> int:
        return db.execute(sql, params)

    # ---------- prestadores ----------
    def _db_has_column(self, table_qualified: str, column: str) -> bool:
        try:
            schema = "public"
            table = table_qualified
            if "." in table_qualified:
                schema, table = table_qualified.split(".", 1)
            r = db.fetch_one(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s AND column_name = %s
                LIMIT 1
                """,
                (schema, table, column)
            )
            return bool(r)
        except Exception:
            return False

    def _db_has_table(self, table_qualified: str) -> bool:
        try:
            schema = "public"
            table = table_qualified
            if "." in table_qualified:
                schema, table = table_qualified.split(".", 1)
            r = db.fetch_one(
                """
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = %s AND table_name = %s
                 LIMIT 1
                """,
                (schema, table),
            )
            return bool(r)
        except Exception:
            return False

    def _db_columns(self, table_qualified: str) -> set[str]:
        try:
            schema = "public"
            table = table_qualified
            if "." in table_qualified:
                schema, table = table_qualified.split(".", 1)
            rows = db.fetch_all(
                """
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = %s AND table_name = %s
                """,
                (schema, table),
            )
            return {r.get("column_name") for r in (rows or []) if r.get("column_name")}
        except Exception:
            return set()

    def _load_tipos_prestador(self):
        tipos = ["Todos"]
        try:
            has_tipo = self._db_has_column("opera.cadastro_faccoes", "tipo_prestador")
            if has_tipo:
                rows = db.fetch_all(
                    "SELECT DISTINCT tipo_prestador AS t FROM opera.cadastro_faccoes "
                    "WHERE COALESCE(ativo, TRUE) = TRUE AND COALESCE(tipo_prestador,'') <> '' "
                    "ORDER BY 1"
                )
                for r in rows or []:
                    t = (r.get("t") or "").strip()
                    if t and t not in tipos:
                        tipos.append(t)
        except Exception:
            pass

        if len(tipos) == 1:
            tipos = self.PROVIDER_TYPE_FALLBACKS["pt_BR"][:]
        return tipos

    def _load_prestadores(self, tipo_display: str):
        tipo = self._map_provider_type_internal((tipo_display or self._get_text("search_all")).strip())
        nomes = [""]

        if not hasattr(self, "_prestador_id_by_nome"):
            self._prestador_id_by_nome = {}

        try:
            has_tipo = self._db_has_column("opera.cadastro_faccoes", "tipo_prestador")
            has_ativo = self._db_has_column("opera.cadastro_faccoes", "ativo")

            where = []
            params = []

            if has_ativo:
                where.append("COALESCE(ativo, TRUE) = TRUE")

            if tipo and tipo != "Todos" and has_tipo:
                where.append("tipo_prestador = %s")
                params.append(tipo)

            where_sql = ("WHERE " + " AND ".join(where)) if where else ""
            rows = db.fetch_all(
                f"SELECT id, nome FROM opera.cadastro_faccoes {where_sql} ORDER BY nome",
                tuple(params) if params else None
            )

            for r in rows or []:
                n = (r.get("nome") or "").strip()
                pid = r.get("id")
                if n:
                    nomes.append(n)
                    if pid is not None:
                        self._prestador_id_by_nome[n] = pid
        except Exception:
            pass

        return nomes

    def _init_prestadores_ui(self, tipo_busca_atual=None, tipo_form_atual=None):
        tipos_internos = self._load_tipos_prestador()
        self._update_provider_type_maps(tipos_internos)
        tipos_display = [self._map_provider_type_display(t) for t in tipos_internos]

        if tipo_busca_atual is None:
            tipo_busca_atual = self._map_provider_type_internal(self.tipo_busca_var.get()) if hasattr(self, "tipo_busca_var") else "Todos"
        if tipo_form_atual is None:
            tipo_form_atual = self._map_provider_type_internal(self.tipo_form_var.get()) if hasattr(self, "tipo_form_var") else "Todos"

        try:
            self.combo_tipo_busca.configure(values=tipos_display)
        except Exception:
            pass
        try:
            self.combo_tipo_form.configure(values=tipos_display)
        except Exception:
            pass

        self.tipo_busca_var.set(self._map_provider_type_display(tipo_busca_atual if tipo_busca_atual in tipos_internos else "Todos"))
        self.tipo_form_var.set(self._map_provider_type_display(tipo_form_atual if tipo_form_atual in tipos_internos else "Todos"))

        self._on_tipo_busca_changed()
        self._on_tipo_form_changed()

    def _on_tipo_busca_changed(self):
        tipo = (self.tipo_busca_var.get() or self._get_text("search_all")).strip()
        nomes = self._load_prestadores(tipo)
        try:
            self.combo_prestador_busca.configure(values=nomes)
        except Exception:
            pass
        try:
            if self.prestador_busca_var.get() not in nomes:
                self.prestador_busca_var.set("")
        except Exception:
            pass

    def _on_tipo_form_changed(self):
        tipo = (self.tipo_form_var.get() or self._get_text("search_all")).strip()
        nomes = self._load_prestadores(tipo)
        try:
            self.combo_prestador_form.configure(values=nomes)
        except Exception:
            pass
        try:
            if self.prestador_form_var.get() not in nomes:
                self.prestador_form_var.set("")
        except Exception:
            pass

    # ---------- dados ----------
    def buscar_cortes(self):
        termo = (self.entry_codigo_modelo.get() or "").strip()
        tipo_display = (self.tipo_busca_var.get() if hasattr(self, "tipo_busca_var") else self._get_text("search_all")) or self._get_text("search_all")
        tipo = self._map_provider_type_internal((tipo_display or self._get_text("search_all")).strip())
        prestador_nome = (self.prestador_busca_var.get() if hasattr(self, "prestador_busca_var") else "") or ""
        prestador_nome = prestador_nome.strip()

        where_parts = []
        params = []

        prestador_id = None
        try:
            prestador_id = getattr(self, "_prestador_id_by_nome", {}).get(prestador_nome) if prestador_nome else None
        except Exception:
            prestador_id = None

        if prestador_id is not None:
            where_parts.append("e.prestador_id = %s")
            params.append(prestador_id)
        elif prestador_nome:
            where_parts.append("COALESCE(cf.nome,'') ILIKE %s")
            params.append(f"%{prestador_nome}%")

        if termo:
            like = f"%{termo}%"
            where_parts.append(
                "(COALESCE(e.codigo_corte,'') ILIKE %s OR "
                "COALESCE(e.ordem_corte,'') ILIKE %s OR "
                "COALESCE(e.descricao_corte,'') ILIKE %s OR "
                "COALESCE(e.tipo_servico,'') ILIKE %s)"
            )
            params += [like, like, like, like]

        if tipo and tipo != "Todos" and self._db_has_column("opera.cadastro_faccoes", "tipo_prestador"):
            where_parts.append("COALESCE(cf.tipo_prestador,'') = %s")
            params.append(tipo)

        where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        sql = f"""
            SELECT
                e.corte_id,
                e.codigo_corte,
                COALESCE(cf.nome,'') AS prestador,
                COALESCE(cf.tipo_prestador,'') AS tipo,
                COALESCE(e.tipo_servico,'') AS servico,
                CASE
                    WHEN r.id IS NOT NULL THEN 'Retornado'
                    WHEN COALESCE(e.status_envio,'') <> '' THEN e.status_envio
                    ELSE 'Em andamento'
                END AS status,
                e.data_envio,
                COALESCE(e.total_pecas, 0) AS qtd_pecas
            FROM opera.envios_cortes e
            LEFT JOIN opera.cadastro_faccoes cf ON cf.id = e.prestador_id
            LEFT JOIN opera.controle_retorno_cortes r ON r.envio_id = e.id
            {where_sql}
            ORDER BY e.data_envio DESC NULLS LAST, e.id DESC
            LIMIT 500
        """

        try:
            rows = []
            rows_envios = db.fetch_all(sql, tuple(params) if params else None)
            for r in rows_envios or []:
                codigo_corte = r.get("codigo_corte")
                if isinstance(codigo_corte, (int, float)) or (isinstance(codigo_corte, str) and str(codigo_corte).isdigit()):
                    codigo_corte = str(codigo_corte).zfill(4)

                rows.append((
                    r.get("corte_id"),
                    codigo_corte,
                    r.get("prestador") or "",
                    self._map_provider_type_display(r.get("tipo") or ""),
                    r.get("servico") or "",
                    self._translate_status(r.get("status") or ""),
                    self._format_date_for_table(r.get("data_envio")),
                    r.get("qtd_pecas"),
                ))

            if self._db_has_table("opera.cortes_finalizados"):
                cols_cf = self._db_columns("opera.cortes_finalizados")
                corte_id_expr = "cf.corte_id" if "corte_id" in cols_cf else "cf.id"
                codigo_expr = "cf.codigo" if "codigo" in cols_cf else ("cf.codigo_corte" if "codigo_corte" in cols_cf else "''")
                desc_expr = "cf.descricao" if "descricao" in cols_cf else ("cf.descricao_corte" if "descricao_corte" in cols_cf else "''")
                prest_expr = "cf.costureira" if "costureira" in cols_cf else ("cf.destino" if "destino" in cols_cf else "''")
                tipo_expr = "cf.tipo_servico" if "tipo_servico" in cols_cf else ("cf.servico" if "servico" in cols_cf else "''")
                envio_expr = "cf.data_envio" if "data_envio" in cols_cf else ("cf.data_saida" if "data_saida" in cols_cf else "NULL")

                def _q(col_new, col_old):
                    if col_new in cols_cf:
                        return f"COALESCE(cf.{col_new},0)"
                    if col_old in cols_cf:
                        return f"COALESCE(cf.{col_old},0)"
                    return "0"

                total_qtd_expr = " + ".join([
                    _q("qtd_pp", "pp"),
                    _q("qtd_p", "p"),
                    _q("qtd_m", "m"),
                    _q("qtd_g", "g"),
                    _q("qtd_gg", "gg"),
                    _q("qtd_g1", "g1"),
                    _q("qtd_g2", "g2"),
                    _q("qtd_g3", "g3"),
                ])

                join_sql = ""
                prestador_nome_expr = prest_expr
                tipo_prestador_expr = "''"
                prestador_id_col = None
                for col in ("prestador_id", "faccao_id", "costureira_id"):
                    if col in cols_cf:
                        prestador_id_col = col
                        break

                if prestador_id_col and self._db_has_table("opera.cadastro_faccoes"):
                    join_sql = "LEFT JOIN opera.cadastro_faccoes cfacc ON cfacc.id = cf." + prestador_id_col
                    prestador_nome_expr = "COALESCE(cfacc.nome, '')"
                    if self._db_has_column("opera.cadastro_faccoes", "tipo_prestador"):
                        tipo_prestador_expr = "COALESCE(cfacc.tipo_prestador, '')"

                where_parts_cf = []
                params_cf = []

                if prestador_id is not None and prestador_id_col:
                    where_parts_cf.append(f"cf.{prestador_id_col} = %s")
                    params_cf.append(prestador_id)
                elif prestador_nome:
                    where_parts_cf.append(f"{prestador_nome_expr} ILIKE %s")
                    params_cf.append(f"%{prestador_nome}%")

                if termo:
                    like = f"%{termo}%"
                    where_parts_cf.append(f"({codigo_expr} ILIKE %s OR {desc_expr} ILIKE %s OR {tipo_expr} ILIKE %s)")
                    params_cf += [like, like, like]

                if tipo and tipo != "Todos" and tipo_prestador_expr != "''":
                    where_parts_cf.append(f"{tipo_prestador_expr} = %s")
                    params_cf.append(tipo)

                where_sql_cf = ("WHERE " + " AND ".join(where_parts_cf)) if where_parts_cf else ""

                sql_cf = f"""
                    SELECT
                        {corte_id_expr} AS corte_id,
                        {codigo_expr} AS codigo_corte,
                        {prestador_nome_expr} AS prestador,
                        {tipo_prestador_expr} AS tipo,
                        {tipo_expr} AS servico,
                        'Finalizado' AS status,
                        {envio_expr} AS data_envio,
                        ({total_qtd_expr}) AS qtd_pecas
                      FROM opera.cortes_finalizados cf
                      {join_sql}
                      {where_sql_cf}
                  ORDER BY cf.id DESC
                     LIMIT 300
                """

                rows_finalizados = db.fetch_all(sql_cf, tuple(params_cf) if params_cf else None)
                for r in rows_finalizados or []:
                    codigo_corte = r.get("codigo_corte")
                    if isinstance(codigo_corte, (int, float)) or (isinstance(codigo_corte, str) and str(codigo_corte).isdigit()):
                        codigo_corte = str(codigo_corte).zfill(4)

                    rows.append((
                        r.get("corte_id"),
                        codigo_corte,
                        r.get("prestador") or "",
                        self._map_provider_type_display(r.get("tipo") or ""),
                        r.get("servico") or "",
                        self._translate_status(r.get("status") or "Finalizado"),
                        self._format_date_for_table(r.get("data_envio")),
                        r.get("qtd_pecas") or 0,
                    ))

            for item in self.tree_cortes.get_children():
                self.tree_cortes.delete(item)

            for new_row in rows:
                self.tree_cortes.insert("", "end", values=new_row)

        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("search_services_error", erro=e))

    def _translate_status(self, status):
        mapa = {
            "Retornado": self._get_text("status_returned"),
            "Em andamento": self._get_text("status_in_progress"),
            "Finalizado": "Finalizado" if self.idioma_atual == "pt_BR" else ("Finished" if self.idioma_atual == "en_US" else "Finalizado"),
        }
        return mapa.get(status, status)

    def buscar_descricao_modelo(self, codigo_modelo):
        desc = ""
        try:
            q1 = db.fetch_one(
                "SELECT descricao_modelo AS d FROM ordem_corte_ficha WHERE TRIM(codigo_modelo)=TRIM(%s) LIMIT 1",
                (codigo_modelo,)
            )
            if q1 and q1.get("d"):
                return q1["d"]
            q2 = db.fetch_one(
                "SELECT descricao AS d FROM cadastro_de_corte WHERE TRIM(codigo)=TRIM(%s) LIMIT 1",
                (codigo_modelo,)
            )
            if q2 and q2.get("d"):
                return q2["d"]
            q3 = db.fetch_one(
                "SELECT descricao AS d FROM cadastro_modelos_cabecalho WHERE TRIM(codigo)=TRIM(%s) LIMIT 1",
                (codigo_modelo,)
            )
            if q3 and q3.get("d"):
                return q3["d"]
        except Exception:
            pass
        return desc or self._get_text("description_not_found")

    def obter_descricao_corte(self, corte_id, codigo_modelo):
        try:
            r = db.fetch_one(
                "SELECT descricao_corte AS d FROM controle_envio_cortes "
                "WHERE corte_id = %s AND TRIM(codigo_corte)=TRIM(%s) LIMIT 1",
                (corte_id, codigo_modelo)
            )
            if r and r.get("d"):
                return r["d"]
        except Exception:
            pass
        return ""

    def selecionar_corte(self, event):
        selected_item = self.tree_cortes.focus()
        if not selected_item:
            return
        corte_data = self.tree_cortes.item(selected_item)["values"]
        if not corte_data or len(corte_data) < 3:
            return

        corte_id = corte_data[0]
        codigo = str(corte_data[1])
        if codigo.isdigit():
            codigo = codigo.zfill(4)

        self.entry_codigo_modelo.delete(0, "end")
        self.entry_codigo_modelo.insert(0, codigo)

        try:
            prestador = corte_data[2] if len(corte_data) > 2 else ""
            tipo_display = corte_data[3] if len(corte_data) > 3 else self._get_text("search_all")
            if prestador is None:
                prestador = ""
            if tipo_display is None or str(tipo_display).strip() == "":
                tipo_display = self._get_text("search_all")

            self.tipo_form_var.set(str(tipo_display))
            self.prestador_form_var.set(str(prestador))
            self.tipo_busca_var.set(str(tipo_display))
            self.prestador_busca_var.set(str(prestador))
        except Exception:
            pass

        try:
            self.entry_codigo_modelo_selecionado.configure(state="normal")
            self.entry_codigo_modelo_selecionado.delete(0, "end")
            self.entry_codigo_modelo_selecionado.insert(0, codigo)
            self.entry_codigo_modelo_selecionado.configure(state="disabled")
        except Exception:
            pass

        descricao = self.obter_descricao_corte(corte_id, codigo) or self.buscar_descricao_modelo(codigo)
        try:
            self.entry_descricao_modelo.configure(state="normal")
            self.entry_descricao_modelo.delete(0, "end")
            self.entry_descricao_modelo.insert(0, descricao)
            self.entry_descricao_modelo.configure(state="disabled")
        except Exception:
            pass

        self.entry_valor.delete(0, "end")
        self.pagamento_var.set(self._get_payment_display("cash"))
        self.entry_parcelas.delete(0, "end")
        self.entry_parcelas.insert(0, "1")
        self.atualizar_visibilidade_parcelas()

        try:
            self.btn_imprimir.configure(state="normal")
            self.btn_salvar.configure(state="normal")
        except Exception:
            pass

    def atualizar_visibilidade_parcelas(self, event=None):
        if self._get_payment_internal(self.pagamento_var.get()) == "installment":
            self.label_parcelas.grid(row=6, column=0, sticky="e", padx=5, pady=2)
            self.entry_parcelas.grid(row=6, column=1, sticky="w", padx=5, pady=2)
        else:
            self.label_parcelas.grid_forget()
            self.entry_parcelas.grid_forget()

    def limpar_campos(self):
        self.entry_codigo_modelo.delete(0, "end")
        try:
            self.tipo_busca_var.set(self._get_text("search_all"))
            self.prestador_busca_var.set("")
            self.tipo_form_var.set(self._get_text("search_all"))
            self.prestador_form_var.set("")
        except Exception:
            pass
        self.entry_codigo_modelo_selecionado.configure(state="normal")
        self.entry_codigo_modelo_selecionado.delete(0, "end")
        self.entry_codigo_modelo_selecionado.configure(state="disabled")
        self.entry_descricao_modelo.configure(state="normal")
        self.entry_descricao_modelo.delete(0, "end")
        self.entry_descricao_modelo.configure(state="disabled")
        self.entry_valor.delete(0, "end")
        self.pagamento_var.set(self._get_payment_display("cash"))
        self.entry_parcelas.delete(0, "end")
        self.entry_parcelas.insert(0, "1")
        self.atualizar_visibilidade_parcelas()
        self.btn_salvar.configure(state="disabled")
        self.btn_imprimir.configure(state="disabled")

    def registrar_adiantamento(self):
        selected_item = self.tree_cortes.focus()
        if not selected_item:
            messagebox.showwarning(self._get_text("warning"), self._get_text("select_cut_warning"))
            return

        corte_data = self.tree_cortes.item(selected_item).get("values", [])
        if not corte_data or len(corte_data) < 3:
            messagebox.showwarning(self._get_text("warning"), self._get_text("invalid_cut_data"))
            return

        corte_id = corte_data[0]
        codigo_modelo = corte_data[1]
        faccao = corte_data[2]

        valor_str = (self.entry_valor.get() or "").strip()
        if not valor_str:
            messagebox.showwarning(self._get_text("warning"), self._get_text("enter_advancement_amount"))
            return

        try:
            valor = float(valor_str.replace(",", "."))
            if valor <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(self._get_text("warning"), self._get_text("positive_numeric_value"))
            return

        forma_pagamento = self._get_payment_internal(self.pagamento_var.get())
        parcelas = 1
        if forma_pagamento == "installment":
            parcelas_str = (self.entry_parcelas.get() or "").strip()
            try:
                parcelas = int(parcelas_str)
                if parcelas < 1:
                    raise ValueError
            except ValueError:
                messagebox.showwarning(self._get_text("warning"), self._get_text("invalid_installments"))
                return

        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        forma_pagamento_db = self._get_payment_display("cash") if forma_pagamento == "cash" else self._get_payment_display("installment")

        try:
            resultado = db.execute(
                "INSERT INTO adiantamento_faccao (corte_id, codigo_modelo, faccao, valor, forma_pagamento, parcelas, data_hora) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    corte_id,
                    str(codigo_modelo),
                    str(faccao),
                    float(valor),
                    str(forma_pagamento_db),
                    int(parcelas),
                    data_hora,
                )
            )

            if resultado > 0:
                messagebox.showinfo(self._get_text("success"), self._get_text("register_success"))
                caminho_pdf = self.imprimir_comprovante(mostrar_mensagem=False)
                if caminho_pdf:
                    try:
                        if os.name == "nt":
                            os.startfile(caminho_pdf)
                        elif os.name == "posix":
                            opener = "open" if sys.platform == "darwin" else "xdg-open"
                            subprocess.call([opener, caminho_pdf])
                    except Exception:
                        pass
                self.limpar_campos()
            else:
                messagebox.showerror(self._get_text("error"), self._get_text("no_record_inserted"))

        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("register_advancement_error", erro=e))

    def imprimir_comprovante(self, mostrar_mensagem=True):
        try:
            selected_item = self.tree_cortes.focus()
            if not selected_item:
                messagebox.showwarning(self._get_text("warning"), self._get_text("select_cut_warning"))
                return None
            corte_data = self.tree_cortes.item(selected_item)["values"]
            if not corte_data or len(corte_data) < 3:
                messagebox.showwarning(self._get_text("warning"), self._get_text("invalid_cut_data"))
                return None

            corte_id = corte_data[0]
            codigo = str(corte_data[1])
            if codigo.isdigit():
                codigo = codigo.zfill(4)

            faccao = corte_data[2]
            valor_str = (self.entry_valor.get() or "").strip()
            forma_pagamento_display = self.pagamento_var.get()
            parcelas = self.entry_parcelas.get() if self._get_payment_internal(forma_pagamento_display) == "installment" else "1"
            data_hora = self._format_datetime_display(datetime.now())

            descricao = self.obter_descricao_corte(corte_id, codigo) or self.buscar_descricao_modelo(codigo)
            if not valor_str:
                messagebox.showwarning(self._get_text("warning"), self._get_text("enter_advancement_amount"))
                return None
            try:
                valor = float(valor_str.replace(",", "."))
                if valor <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning(self._get_text("invalid_value_title"), self._get_text("positive_numeric_value"))
                return None

            if self._get_payment_internal(forma_pagamento_display) == "installment":
                try:
                    parc = int(parcelas)
                    if parc < 1:
                        raise ValueError
                except ValueError:
                    messagebox.showwarning(self._get_text("invalid_installments_title"), self._get_text("invalid_installments"))
                    return None

            default_dir = os.path.join(os.path.expanduser("~"), "Documents")
            nome_padrao = f"{self._get_text('receipt_filename_prefix')}_{codigo}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            caminho = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialdir=default_dir,
                initialfile=nome_padrao,
                filetypes=[(self._get_text("pdf_files"), "*.pdf")],
                title=self._get_text("save_receipt_as")
            )
            if not caminho:
                return None

            c = canvas.Canvas(caminho, pagesize=letter)
            width, height = letter
            meio_pagina = height / 2

            def safe_str(v):
                return "" if v is None else str(v).strip()

            def desenhar_comprovante(c_local, width_local, height_local, y_position, via_num):
                left_margin = 50
                right_margin = width_local - 50
                table_width = right_margin - left_margin

                c_local.setFont("Helvetica-Bold", 14)
                c_local.drawCentredString(width_local / 2, y_position, self._get_text("receipt_title"))
                c_local.setFont("Helvetica-Bold", 9)
                via_text = self._get_text("copy_label", numero=via_num)
                text_w = c_local.stringWidth(via_text, "Helvetica-Bold", 9)
                c_local.drawString(right_margin - text_w, y_position, via_text)

                empresa_y = y_position - 22
                c_local.setFont("Helvetica-Bold", 11)
                c_local.drawString(left_margin, empresa_y, self._get_text("company_name"))
                c_local.setFont("Helvetica", 9)
                c_local.drawString(left_margin, empresa_y - 14, self._get_text("company_cnpj"))
                c_local.drawString(left_margin, empresa_y - 28, self._get_text("company_address"))

                line_y = empresa_y - 36
                c_local.setLineWidth(0.8)
                c_local.line(left_margin, line_y, right_margin, line_y)

                dados_table = [
                    [self._get_text("receipt_provider"), safe_str(faccao)],
                    [self._get_text("receipt_model_code"), safe_str(codigo)],
                    [self._get_text("receipt_description"), safe_str(descricao)],
                    [self._get_text("receipt_amount"), self._format_currency(valor)],
                    [self._get_text("receipt_payment_method"), safe_str(forma_pagamento_display)],
                    [self._get_text("receipt_installments"), safe_str(parcelas)],
                    [self._get_text("receipt_date_time"), safe_str(data_hora)]
                ]

                col0_w = 150
                col1_w = table_width - col0_w
                t = Table(dados_table, colWidths=[col0_w, col1_w])
                t.setStyle(TableStyle([
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                wrapped_width, wrapped_height = t.wrap(table_width, height_local)
                table_y = line_y - 10 - wrapped_height
                t.drawOn(c_local, left_margin, table_y)

                assinatura_top = table_y - 60
                c_local.setFont("Helvetica", 9)
                signature_line_length = 300
                line_y_sign = assinatura_top - 12
                center_x = (left_margin + right_margin) / 2
                c_local.setLineWidth(1)
                line_start = center_x - signature_line_length / 2
                c_local.line(line_start, line_y_sign, line_start + signature_line_length, line_y_sign)
                label_text = self._get_text("receipt_signature")
                label_w = c_local.stringWidth(label_text, "Helvetica", 9)
                label_x = center_x - label_w / 2
                c_local.drawString(label_x, line_y_sign + 12, label_text)

            desenhar_comprovante(c, width, height, height - 40, 1)
            c.setLineWidth(0.8)
            c.line(50, meio_pagina, width - 50, meio_pagina)
            desenhar_comprovante(c, width, height, meio_pagina - 40, 2)
            c.save()

            if mostrar_mensagem:
                messagebox.showinfo(self._get_text("success"), self._get_text("receipt_generated", caminho=caminho))

            try:
                if os.name == "nt":
                    os.startfile(caminho)
                elif os.name == "posix":
                    opener = "open" if sys.platform == "darwin" else "xdg-open"
                    subprocess.call([opener, caminho])
            except Exception:
                pass

            return caminho
        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("generate_receipt_error", erro=e))
            return None

    def atualizar_data_hora(self):
        try:
            self.label_data.configure(text=self._format_datetime_display(datetime.now()))
        except Exception:
            pass
        self.after(1000, self.atualizar_data_hora)


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.geometry("900x600")
    root.title("Controle de Adiantamentos")
    app = PagamentoAdiantamentoPage(root, sistema=None)
    app.pack(fill="both", expand=True)
    root.mainloop()
