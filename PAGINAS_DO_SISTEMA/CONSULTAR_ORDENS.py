# -*- coding: utf-8 -*-
from PAGINAS_DO_SISTEMA import TEMAS
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel, filedialog
import os
from PIL import Image, ImageDraw, ImageFont, ImageTk
from datetime import date, datetime, timedelta
# >>> REMOVIDO sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from PAGINAS_DO_SISTEMA.UI_CALENDARIO import abrir_calendario, vincular_calendario

# ====== ACESSO AO POSTGRES ======
try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception as e:
    def get_conn():
        raise RuntimeError("BANCO_DE_DADOS_PG não disponível: %s" % e)


    def get_schema():
        return "public"


    def require_ready(essentials=None):
        return False, "BANCO_DE_DADOS_PG ausente"


def cor_e_clara(cor):
    """Retorna True se a cor for clara"""
    cor = cor.lstrip("#")
    if len(cor) == 6:
        r, g, b = [int(cor[i:i + 2], 16) for i in (0, 2, 4)]
        return (r * 299 + g * 587 + b * 114) / 1000 > 128
    return False


def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def _last_day_of_month(d: date) -> date:
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


class OrdemCorteFinalizada(ctk.CTkFrame):
    TRANSLATIONS = {
        "pt_BR": {
            "search_order": "Buscar Ordem:",
            "search_placeholder": "Digite código ou descrição...",
            "search": "🔍 Buscar",
            "print_pdf": "📄 Imprimir PDF",
            "materials_used": "MATERIAIS UTILIZADOS",
            "production_lots": "LOTES DE PRODUÇÃO",
            "totals": "TOTAIS:",
            "pieces": "PEÇAS:",
            "sheets": "FOLHAS:",
            "meters": "METROS:",
            "yield": "RENDIMENTO:",
            "size_distribution": "DISTRIBUIÇÃO POR TAMANHO:",
            "observations": "OBSERVAÇÕES:",
            "obs_placeholder": "Insira observações relevantes...",
            "orders_found": "ORDENS ENCONTRADAS",
            "orders_header": "ORDEM   | CÓDIGO | DESCRIÇÃO           | QTD  | DATA      ",
            "cancel": "Cancelar",
            "save_pdf": "Salvar PDF",
            "print": "Imprimir",
            "close": "Fechar",
            "search_title": "Busca",
            "database": "Banco de Dados",
            "error": "Erro",
            "warning": "Aviso",
            "success": "Sucesso",
            "type_code_or_description": "Digite o código ou descrição para buscar.",
            "no_orders_found": "Nenhuma ordem encontrada.",
            "search_error": "Erro ao buscar ordem:\n{erro}",
            "select_order": "Selecione a Ordem",
            "order_not_found": "Ordem não encontrada!",
            "no_order_loaded": "Nenhuma ordem carregada para gerar PDF.",
            "temp_pdf_error": "Falha ao gerar PDF temporário:\n{erro}",
            "load_order_error": "Falha ao carregar ordem:\n{erro}",
            "no_observation": "Nenhuma observação",
            "pdf_saved_success": "PDF salvo com sucesso em:\n{caminho}",
            "pdf_files": "Arquivos PDF",
            "preview_title": "Pré-visualização do PDF",
            "pdf_preview_unavailable": "Não foi possível renderizar a pré-visualização do PDF neste computador. O arquivo será aberto externamente.",
            "open_pdf_error": "Não foi possível abrir o PDF:\n{erro}",
            "schema_validation_error": "Não foi possível validar o schema:\n{erro}",
            "query_order": "Consultar Ordens de Corte",
            "order_number": "Nº ORDEM:",
            "code": "CÓDIGO:",
            "description": "DESCRIÇÃO:",
            "length": "COMPRIMENTO (m):",
            "width": "LARGURA (m):",
            "cutter": "CORTADOR:",
            "assistant": "AJUDANTE:",
            "date": "DATA:",
            "fabric": "TECIDO",
            "color": "COR",
            "composition": "COMPOSIÇÃO",
            "rolls": "BOBINAS",
            "sheets_short": "FOLHAS",
            "pp": "PP",
            "p": "P",
            "m": "M",
            "g": "G",
            "gg": "GG",
            "g1": "G1",
            "g2": "G2",
            "g3": "G3",
            "total": "TOTAL",
            "lot": "LOTE",
            "lot_number": "Nº",
            "cut_information": "INFORMAÇÕES DO CORTE",
            "cut_lots": "LOTES DE CORTE",
            "real_percentage": "PORCENTAGEM REAL",
            "total_pieces_yield": "TOTAL DE PEÇAS E RENDIMENTO",
            "total_pieces": "Total Peças:",
            "yield_label": "Rendimento:",
            "sheets_label_full": "Folhas:",
            "meters_used": "Metros Utilizados:",
            "observations_title": "OBSERVAÇÕES",
            "signature": "Assinatura do Responsável",
            "printed_on": "Impresso em: {date}",
            "cut_order_produced": "ORDEM DE CORTE PRODUZIDA",
        },
        "en_US": {
            "search_order": "Search Order:",
            "search_placeholder": "Enter code or description...",
            "search": "🔍 Search",
            "print_pdf": "📄 Print PDF",
            "materials_used": "MATERIALS USED",
            "production_lots": "PRODUCTION LOTS",
            "totals": "TOTALS:",
            "pieces": "PIECES:",
            "sheets": "SHEETS:",
            "meters": "METERS:",
            "yield": "YIELD:",
            "size_distribution": "SIZE DISTRIBUTION:",
            "observations": "OBSERVATIONS:",
            "obs_placeholder": "Enter relevant notes...",
            "orders_found": "ORDERS FOUND",
            "orders_header": "ORDER   | CODE   | DESCRIPTION          | QTY  | DATE      ",
            "cancel": "Cancel",
            "save_pdf": "Save PDF",
            "print": "Print",
            "close": "Close",
            "search_title": "Search",
            "database": "Database",
            "error": "Error",
            "warning": "Warning",
            "success": "Success",
            "type_code_or_description": "Enter the code or description to search.",
            "no_orders_found": "No orders found.",
            "search_error": "Error searching order:\n{erro}",
            "select_order": "Select Order",
            "order_not_found": "Order not found!",
            "no_order_loaded": "No order loaded to generate PDF.",
            "temp_pdf_error": "Failed to generate temporary PDF:\n{erro}",
            "load_order_error": "Failed to load order:\n{erro}",
            "no_observation": "No observations",
            "pdf_saved_success": "PDF saved successfully at:\n{caminho}",
            "pdf_files": "PDF Files",
            "preview_title": "PDF Preview",
            "pdf_preview_unavailable": "Could not render the PDF preview on this computer. The file will be opened externally.",
            "open_pdf_error": "Could not open the PDF:\n{erro}",
            "schema_validation_error": "Could not validate the schema:\n{erro}",
            "query_order": "View Cut Orders",
            "order_number": "ORDER N°:",
            "code": "CODE:",
            "description": "DESCRIPTION:",
            "length": "LENGTH (m):",
            "width": "WIDTH (m):",
            "cutter": "CUTTER:",
            "assistant": "ASSISTANT:",
            "date": "DATE:",
            "fabric": "FABRIC",
            "color": "COLOR",
            "composition": "COMPOSITION",
            "rolls": "ROLLS",
            "sheets_short": "SHEETS",
            "pp": "PP",
            "p": "P",
            "m": "M",
            "g": "G",
            "gg": "GG",
            "g1": "G1",
            "g2": "G2",
            "g3": "G3",
            "total": "TOTAL",
            "lot": "LOT",
            "lot_number": "N°",
            "cut_information": "CUT INFORMATION",
            "cut_lots": "CUT LOTS",
            "real_percentage": "REAL PERCENTAGE",
            "total_pieces_yield": "TOTAL PIECES AND YIELD",
            "total_pieces": "Total Pieces:",
            "yield_label": "Yield:",
            "sheets_label_full": "Sheets:",
            "meters_used": "Meters Used:",
            "observations_title": "OBSERVATIONS",
            "signature": "Responsible Signature",
            "printed_on": "Printed on: {date}",
            "cut_order_produced": "CUT ORDER PRODUCED",
        },
        "es_ES": {
            "search_order": "Buscar Orden:",
            "search_placeholder": "Ingrese código o descripción...",
            "search": "🔍 Buscar",
            "print_pdf": "📄 Imprimir PDF",
            "materials_used": "MATERIALES UTILIZADOS",
            "production_lots": "LOTES DE PRODUCCIÓN",
            "totals": "TOTALES:",
            "pieces": "PIEZAS:",
            "sheets": "HOJAS:",
            "meters": "METROS:",
            "yield": "RENDIMIENTO:",
            "size_distribution": "DISTRIBUCIÓN POR TALLA:",
            "observations": "OBSERVACIONES:",
            "obs_placeholder": "Ingrese observaciones relevantes...",
            "orders_found": "ÓRDENES ENCONTRADAS",
            "orders_header": "ORDEN   | CÓDIGO | DESCRIPCIÓN          | CANT | FECHA     ",
            "cancel": "Cancelar",
            "save_pdf": "Guardar PDF",
            "print": "Imprimir",
            "close": "Cerrar",
            "search_title": "Búsqueda",
            "database": "Base de Datos",
            "error": "Error",
            "warning": "Aviso",
            "success": "Éxito",
            "type_code_or_description": "Ingrese el código o la descripción para buscar.",
            "no_orders_found": "No se encontraron órdenes.",
            "search_error": "Error al buscar la orden:\n{erro}",
            "select_order": "Seleccionar Orden",
            "order_not_found": "¡Orden no encontrada!",
            "no_order_loaded": "No hay una orden cargada para generar PDF.",
            "temp_pdf_error": "Error al generar el PDF temporal:\n{erro}",
            "load_order_error": "Error al cargar la orden:\n{erro}",
            "no_observation": "Sin observaciones",
            "pdf_saved_success": "PDF guardado correctamente en:\n{caminho}",
            "pdf_files": "Archivos PDF",
            "preview_title": "Vista previa del PDF",
            "pdf_preview_unavailable": "No fue posible renderizar la vista previa del PDF en este equipo. El archivo se abrirá externamente.",
            "open_pdf_error": "No fue posible abrir el PDF:\n{erro}",
            "schema_validation_error": "No fue posible validar el esquema:\n{erro}",
            "query_order": "Consultar Órdenes de Corte",
            "order_number": "Nº ORDEN:",
            "code": "CÓDIGO:",
            "description": "DESCRIPCIÓN:",
            "length": "LARGO (m):",
            "width": "ANCHO (m):",
            "cutter": "CORTADOR:",
            "assistant": "AYUDANTE:",
            "date": "FECHA:",
            "fabric": "TELA",
            "color": "COLOR",
            "composition": "COMPOSICIÓN",
            "rolls": "BOBINAS",
            "sheets_short": "HOJAS",
            "pp": "PP",
            "p": "P",
            "m": "M",
            "g": "G",
            "gg": "GG",
            "g1": "G1",
            "g2": "G2",
            "g3": "G3",
            "total": "TOTAL",
            "lot": "LOTE",
            "lot_number": "Nº",
            "cut_information": "INFORMACIÓN DEL CORTE",
            "cut_lots": "LOTES DE CORTE",
            "real_percentage": "PORCENTAJE REAL",
            "total_pieces_yield": "TOTAL DE PIEZAS Y RENDIMIENTO",
            "total_pieces": "Total Piezas:",
            "yield_label": "Rendimiento:",
            "sheets_label_full": "Hojas:",
            "meters_used": "Metros Utilizados:",
            "observations_title": "OBSERVACIONES",
            "signature": "Firma del Responsable",
            "printed_on": "Impreso el: {date}",
            "cut_order_produced": "ORDEN DE CORTE PRODUCIDA",
        },
    }

    def _get_idioma_atual(self):
        return getattr(self.sistema, "idioma_atual", "pt_BR")

    def _get_text(self, chave, **kwargs):
        idioma = self._get_idioma_atual()
        texto = self.TRANSLATIONS.get(idioma, {}).get(chave, self.TRANSLATIONS.get("pt_BR", {}).get(chave, chave))
        try:
            return texto.format(**kwargs)
        except Exception:
            return texto

    def refresh_texts(self):
        refs = getattr(self, "_ui_refs", {})
        if refs.get("search_label"):
            refs["search_label"].configure(text=self._get_text("search_order"))
        if refs.get("search_entry"):
            refs["search_entry"].configure(placeholder_text=self._get_text("search_placeholder"))
        if refs.get("search_button"):
            refs["search_button"].configure(text=self._get_text("search"))
        if refs.get("print_button"):
            refs["print_button"].configure(text=self._get_text("print_pdf"))
        if refs.get("materials_title"):
            refs["materials_title"].configure(text=self._get_text("materials_used"))
        if refs.get("lots_title"):
            refs["lots_title"].configure(text=self._get_text("production_lots"))
        if refs.get("totals_title"):
            refs["totals_title"].configure(text=self._get_text("totals"))
        if refs.get("pieces_label"):
            refs["pieces_label"].configure(text=self._get_text("pieces"))
        if refs.get("sheets_label"):
            refs["sheets_label"].configure(text=self._get_text("sheets"))
        if refs.get("meters_label"):
            refs["meters_label"].configure(text=self._get_text("meters"))
        if refs.get("yield_label"):
            refs["yield_label"].configure(text=self._get_text("yield"))
        if refs.get("size_title"):
            refs["size_title"].configure(text=self._get_text("size_distribution"))
        if refs.get("obs_label"):
            refs["obs_label"].configure(text=self._get_text("observations"))
        if refs.get("obs_entry"):
            refs["obs_entry"].configure(placeholder_text=self._get_text("obs_placeholder"))

        # Atualizar os labels dos campos de entrada
        if hasattr(self, "_label_widgets"):
            for campo, label_widget in self._label_widgets.items():
                if label_widget and label_widget.winfo_exists():
                    if campo == "order_number":
                        label_widget.configure(text=self._get_text("order_number"))
                    elif campo == "code":
                        label_widget.configure(text=self._get_text("code"))
                    elif campo == "description":
                        label_widget.configure(text=self._get_text("description"))
                    elif campo == "length":
                        label_widget.configure(text=self._get_text("length"))
                    elif campo == "width":
                        label_widget.configure(text=self._get_text("width"))
                    elif campo == "cutter":
                        label_widget.configure(text=self._get_text("cutter"))
                    elif campo == "assistant":
                        label_widget.configure(text=self._get_text("assistant"))
                    elif campo == "date":
                        label_widget.configure(text=self._get_text("date"))

        # Atualizar cabeçalhos das tabelas
        if hasattr(self, "tree_tecido") and self.tree_tecido.winfo_exists():
            colunas_tecido = (
                self._get_text("fabric"),
                self._get_text("color"),
                self._get_text("composition"),
                self._get_text("rolls"),
                self._get_text("sheets_short"),
                self._get_text("pp"),
                self._get_text("p"),
                self._get_text("m"),
                self._get_text("g"),
                self._get_text("gg"),
                self._get_text("g1"),
                self._get_text("g2"),
                self._get_text("g3"),
                self._get_text("total")
            )
            self.tree_tecido["columns"] = colunas_tecido
            for col in colunas_tecido:
                self.tree_tecido.heading(col, text=col)

        if hasattr(self, "tree_lote") and self.tree_lote.winfo_exists():
            colunas_lote = (
                self._get_text("lot_number"),
                self._get_text("fabric"),
                self._get_text("color"),
                self._get_text("composition"),
                self._get_text("rolls"),
                self._get_text("sheets_short"),
                self._get_text("pp"),
                self._get_text("p"),
                self._get_text("m"),
                self._get_text("g"),
                self._get_text("gg"),
                self._get_text("g1"),
                self._get_text("g2"),
                self._get_text("g3"),
                self._get_text("total")
            )
            self.tree_lote["columns"] = colunas_lote
            for col in colunas_lote:
                self.tree_lote.heading(col, text=col)

    def __init__(self, master, sistema=None, app=None, *args, **kwargs):
        # Normaliza: funciona tanto se o menu passar 'sistema' quanto 'app'
        self.sistema = sistema or app

        # Herdar tema do sistema, com fallback seguro
        origem = self.sistema
        self.cor_fundo = getattr(origem, "cor_fundo", "#0E1525")
        self.cor_texto = getattr(origem, "cor_texto", "#ffffff")
        self.cor_borda = getattr(origem, "cor_borda", "#347083")
        self.cor_primaria = getattr(origem, "cor_primaria", "#1F538D")
        self.cor_hover = getattr(origem, "cor_hover", "#14375E")
        self.cor_sucesso = getattr(origem, "cor_sucesso", "#2e7d32")
        self.cor_alerta = getattr(origem, "cor_alerta", "#a83232")
        self.cor_imprimir = getattr(origem, "cor_imprimir", "#1F538D")

        super().__init__(master, fg_color=self.cor_fundo, *args, **kwargs)

        # Checa apenas conectividade (não cria tabelas)
        try:
            require_ready(["cadastro_de_corte",
                           "cadastro_de_corte_tecidos",
                           "cadastro_de_corte_lotes"])
        except Exception as _e:
            # Não bloqueia a UI: apenas informa
            try:
                messagebox.showwarning(self._get_text("database"),
                                       self._get_text("schema_validation_error", erro=_e))
            except Exception:
                pass

        self.campos = {}
        self._label_widgets = {}  # Armazena os widgets de label para atualização
        self._ui_refs = {}
        self.dados_ordem_atual = None
        self._ultimo_pdf_temp = None  # caminho do último PDF gerado para preview
        hoje = date.today()
        self.periodo_inicio_var = tk.StringVar(value=_first_day_of_month(hoje).strftime("%Y-%m-%d"))
        self.periodo_fim_var = tk.StringVar(value=_last_day_of_month(hoje).strftime("%Y-%m-%d"))

        # ------------------------ UI: BUSCA ------------------------
        frame_busca = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        frame_busca.pack(fill="x", padx=10, pady=5)

        self._ui_refs["search_label"] = ctk.CTkLabel(frame_busca, text=self._get_text("search_order"),
                                                     text_color=self.cor_texto)
        self._ui_refs["search_label"].pack(side="left", padx=(0, 5))
        self.ordem_busca_entry = ctk.CTkEntry(
            frame_busca, width=250,
            placeholder_text=self._get_text("search_placeholder"),
            text_color=self.cor_texto, fg_color=self.cor_fundo, border_color=self.cor_borda
        )
        self.ordem_busca_entry.pack(side="left", fill="x", expand=True, padx=5)
        self._ui_refs["search_entry"] = self.ordem_busca_entry
        self.ordem_busca_entry.bind("<Return>", lambda e: self.buscar_ordem())

        self._ui_refs["search_button"] = ctk.CTkButton(
            frame_busca, text=self._get_text("search"), width=100, command=self.buscar_ordem,
            fg_color=self.cor_primaria, hover_color=self.cor_hover, text_color=self.cor_texto
        )
        self._ui_refs["search_button"].pack(side="left", padx=5)

        self._ui_refs["print_button"] = ctk.CTkButton(
            frame_busca, text=self._get_text("print_pdf"), width=120,
            command=self.previsualizar_controle,
            fg_color=self.cor_imprimir, hover_color=self.cor_hover, text_color=self.cor_texto
        )
        self._ui_refs["print_button"].pack(side="left", padx=5)

        frame_periodo = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        frame_periodo.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(frame_periodo, text="Período:", text_color=self.cor_texto).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(frame_periodo, text="Início", text_color=self.cor_texto).pack(side="left", padx=(0, 4))
        self.periodo_inicio_entry = ctk.CTkEntry(
            frame_periodo,
            textvariable=self.periodo_inicio_var,
            width=120,
            text_color=self.cor_texto,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
        )
        self.periodo_inicio_entry.pack(side="left")
        vincular_calendario(self, self.periodo_inicio_entry, output_format="%Y-%m-%d")
        ctk.CTkButton(
            frame_periodo,
            text="📅",
            width=32,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=lambda: self._abrir_calendario_periodo(self.periodo_inicio_entry),
        ).pack(side="left", padx=(4, 12))

        ctk.CTkLabel(frame_periodo, text="Fim", text_color=self.cor_texto).pack(side="left", padx=(0, 4))
        self.periodo_fim_entry = ctk.CTkEntry(
            frame_periodo,
            textvariable=self.periodo_fim_var,
            width=120,
            text_color=self.cor_texto,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
        )
        self.periodo_fim_entry.pack(side="left")
        vincular_calendario(self, self.periodo_fim_entry, output_format="%Y-%m-%d")
        ctk.CTkButton(
            frame_periodo,
            text="📅",
            width=32,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=lambda: self._abrir_calendario_periodo(self.periodo_fim_entry),
        ).pack(side="left", padx=(4, 12))

        ctk.CTkButton(
            frame_periodo,
            text="Limpar período",
            width=120,
            fg_color=self.cor_alerta,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=self._limpar_periodo_busca,
        ).pack(side="left", padx=(0, 5))

        self.periodo_inicio_entry.bind("<Return>", lambda _e: self.buscar_ordem(), add="+")
        self.periodo_fim_entry.bind("<Return>", lambda _e: self.buscar_ordem(), add="+")

        # ------------------------ UI: INFO BÁSICAS ------------------------
        frame_info = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        frame_info.pack(fill="x", padx=10, pady=5)

        # Criar campos com labels que serão armazenados para tradução
        self._criar_label_entry(frame_info, "order_number", 0, 0)
        self._criar_label_entry(frame_info, "code", 0, 2)
        self._criar_label_entry(frame_info, "description", 0, 4, colspan=3)
        self._criar_label_entry(frame_info, "length", 1, 0)
        self._criar_label_entry(frame_info, "width", 1, 2)
        self._criar_label_entry(frame_info, "cutter", 2, 0)
        self._criar_label_entry(frame_info, "assistant", 2, 2)
        self._criar_label_entry(frame_info, "date", 2, 4)

        # ------------------------ UI: TECIDOS ------------------------
        frame_tecidos = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        frame_tecidos.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        self._ui_refs["materials_title"] = ctk.CTkLabel(frame_tecidos, text=self._get_text("materials_used"),
                                                        font=("Arial", 12, "bold"), text_color=self.cor_texto)
        self._ui_refs["materials_title"].pack(pady=(0, 5))

        colunas_tecido = (
            self._get_text("fabric"),
            self._get_text("color"),
            self._get_text("composition"),
            self._get_text("rolls"),
            self._get_text("sheets_short"),
            self._get_text("pp"),
            self._get_text("p"),
            self._get_text("m"),
            self._get_text("g"),
            self._get_text("gg"),
            self._get_text("g1"),
            self._get_text("g2"),
            self._get_text("g3"),
            self._get_text("total")
        )
        self.tree_tecido = self._criar_tabela(frame_tecidos, colunas_tecido)
        self.tree_tecido.pack(fill="both", expand=True)

        # ------------------------ UI: LOTES ------------------------
        frame_lotes = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        frame_lotes.pack(fill="both", expand=True, padx=10, pady=5)
        self._ui_refs["lots_title"] = ctk.CTkLabel(frame_lotes, text=self._get_text("production_lots"),
                                                   font=("Arial", 12, "bold"), text_color=self.cor_texto)
        self._ui_refs["lots_title"].pack(pady=(0, 5))

        colunas_lote = (
            self._get_text("lot_number"),
            self._get_text("fabric"),
            self._get_text("color"),
            self._get_text("composition"),
            self._get_text("rolls"),
            self._get_text("sheets_short"),
            self._get_text("pp"),
            self._get_text("p"),
            self._get_text("m"),
            self._get_text("g"),
            self._get_text("gg"),
            self._get_text("g1"),
            self._get_text("g2"),
            self._get_text("g3"),
            self._get_text("total")
        )
        self.tree_lote = self._criar_tabela(frame_lotes, colunas_lote)
        self.tree_lote.pack(fill="both", expand=True)

        # ------------------------ UI: TOTAIS ------------------------
        frame_totais = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        frame_totais.pack(fill="x", padx=10, pady=10)
        self._ui_refs["totals_title"] = ctk.CTkLabel(frame_totais, text=self._get_text("totals"),
                                                     font=("Arial", 12, "bold"),
                                                     text_color=self.cor_texto)
        self._ui_refs["totals_title"].grid(row=0, column=0, sticky="w")

        self.total_pecas_valor = self._criar_label_valor(frame_totais, "pieces", "0", 0, 1)
        self.folhas_valor = self._criar_label_valor(frame_totais, "sheets", "0", 0, 3)
        self.metros_valor = self._criar_label_valor(frame_totais, "meters", "0", 0, 5)
        self.rendimento_valor = self._criar_label_valor(frame_totais, "yield", "0%", 0, 7)

        # ------------------------ UI: % REAL ------------------------
        frame_pct = ctk.CTkFrame(frame_totais, fg_color=self.cor_fundo)
        frame_pct.grid(row=1, column=0, columnspan=8, sticky="nsew", pady=(10, 0))
        self._ui_refs["size_title"] = ctk.CTkLabel(frame_pct, text=self._get_text("size_distribution"),
                                                   font=("Arial", 11, "bold"), text_color=self.cor_texto)
        self._ui_refs["size_title"].pack()

        self.tree_porcentagem = ttk.Treeview(
            frame_pct, columns=("PP", "P", "M", "G", "GG", "G1", "G2", "G3"),
            show="headings", height=1
        )
        self.tree_porcentagem.pack(fill="x", padx=5, pady=5)
        for col in ("PP", "P", "M", "G", "GG", "G1", "G2", "G3"):
            self.tree_porcentagem.heading(col, text=col)
            self.tree_porcentagem.column(col, anchor="center", width=60)

        # ------------------------ UI: OBS ------------------------
        frame_obs = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        frame_obs.pack(fill="x", padx=10, pady=10)
        self._ui_refs["obs_label"] = ctk.CTkLabel(frame_obs, text=self._get_text("observations"), font=("Arial", 12),
                                                  text_color=self.cor_texto)
        self._ui_refs["obs_label"].pack(anchor="w")

        self.obs_entry = ctk.CTkEntry(
            frame_obs, placeholder_text=self._get_text("obs_placeholder"),
            text_color=self.cor_texto, fg_color=self.cor_fundo, border_color=self.cor_borda
        )
        self.obs_entry.pack(fill="x", pady=5)
        self._ui_refs["obs_entry"] = self.obs_entry

        # Estilo do Treeview conforme tema
        self._configurar_estilo_treeview()
        self.refresh_texts()

    # -------------------- UI helpers --------------------
    def _criar_label_entry(self, frame, campo_key, linha, coluna, colspan=1):
        """Cria um par label/entry com suporte a tradução"""
        texto_label = self._get_text(campo_key)
        label = ctk.CTkLabel(
            frame,
            text=texto_label,
            font=("Arial", 11),
            anchor="e",
            text_color=self.cor_texto
        )
        label.grid(row=linha, column=coluna, padx=(10, 5), pady=2, sticky="e")

        # Armazena o label para atualização futura
        self._label_widgets[campo_key] = label

        entry = ctk.CTkEntry(
            frame,
            width=120 if campo_key != "description" else 300,
            font=("Arial", 11),
            text_color=self.cor_texto,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda
        )
        entry.grid(row=linha, column=coluna + 1, padx=(0, 10), pady=2, sticky="w", columnspan=colspan)

        self.campos[campo_key] = entry
        return entry

    def _criar_label_valor(self, frame, chave_texto, valor, linha, coluna):
        texto = self._get_text(chave_texto)
        texto_label = ctk.CTkLabel(frame, text=texto, font=("Arial", 11), text_color=self.cor_texto)
        texto_label.grid(
            row=linha, column=coluna, padx=(10, 0), sticky="e"
        )
        self._ui_refs[f"{chave_texto}_label"] = texto_label
        label = ctk.CTkLabel(frame, text=valor, font=("Arial", 11, "bold"), text_color=self.cor_sucesso)
        label.grid(row=linha, column=coluna + 1, padx=(0, 20), sticky="w")
        return label

    def _criar_tabela(self, frame, colunas):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Custom.Treeview",
                        background=self.cor_fundo,
                        foreground=self.cor_texto,
                        fieldbackground=self.cor_fundo,
                        bordercolor=self.cor_borda,
                        font=("Arial", 10))
        style.map("Custom.Treeview",
                  background=[('selected', self.cor_primaria)],
                  foreground=[('selected', self.cor_texto)])

        tree = ttk.Treeview(frame, columns=colunas, show="headings", style="Custom.Treeview", height=6)
        for col in colunas:
            tree.heading(col, text=col)
            tree.column(col, width=70, anchor="center", minwidth=50)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        return tree

    def _configurar_estilo_treeview(self):
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Treeview",
                        background=self.cor_fundo,
                        foreground=self.cor_texto,
                        fieldbackground=self.cor_fundo,
                        borderwidth=0,
                        font=('Arial', 10))
        style.map('Treeview',
                  background=[('selected', self.cor_primaria)],
                  foreground=[('selected', self.cor_texto)])

    def _abrir_calendario_periodo(self, entry):
        return abrir_calendario(self, entry, output_format="%Y-%m-%d")

    def _limpar_periodo_busca(self):
        self.periodo_inicio_var.set("")
        self.periodo_fim_var.set("")

    def _parse_data_busca(self, valor):
        texto = str(valor or "").strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(texto[:10], fmt).date()
            except Exception:
                pass
        return None

    # -------------------- Busca & carga (Agora no PostgreSQL) --------------------
    def buscar_ordem(self):
        termo = (self.ordem_busca_entry.get() or "").strip()
        data_inicio = self._parse_data_busca(self.periodo_inicio_var.get())
        data_fim = self._parse_data_busca(self.periodo_fim_var.get())
        if not termo and not data_inicio and not data_fim:
            messagebox.showwarning(self._get_text("search_title"), self._get_text("type_code_or_description"))
            return
        try:
            schema = get_schema()
            where = []
            params = []
            if termo:
                where.append("(codigo ILIKE %s OR descricao ILIKE %s)")
                params.extend([f"%{termo}%", f"%{termo}%"])
            if data_inicio:
                where.append("data >= %s")
                params.append(data_inicio)
            if data_fim:
                where.append("data <= %s")
                params.append(data_fim)
            where_sql = " WHERE " + " AND ".join(where) if where else ""

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {schema};")
                    cur.execute(f"""
                        SELECT
                            id,
                            numero_ordem,
                            codigo,
                            descricao,
                            data,
                            comprimento_matriz,
                            largura_matriz,
                            cortador,
                            ajudante,
                            total_folhas,
                            metros_utilizados,
                            bobinas_utilizadas,
                            composicao_tecido,
                            total_pecas,
                            rendimento,
                            observacoes
                        FROM {schema}.cadastro_de_corte
                        {where_sql}
                        ORDER BY
                            data DESC NULLS LAST,
                            COALESCE(NULLIF(numero_ordem,'')::int, 0) DESC,
                            id DESC
                    """, tuple(params))
                    resultados = cur.fetchall()

            if not resultados:
                messagebox.showinfo(self._get_text("search_title"), self._get_text("no_orders_found"))
                return
            if len(resultados) > 1:
                self._escolher_ordem(resultados)
            else:
                self._carregar_ordem(resultados[0])

        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("search_error", erro=e))

    def _escolher_ordem(self, ordens):
        def criar_callback(ordem):
            return lambda: self._executar_e_fechar(ordem, popup)

        popup = ctk.CTkToplevel(self)
        popup.title(self._get_text("select_order"))
        popup.resizable(False, False)
        popup.configure(fg_color=self.cor_fundo)
        popup.grab_set()

        card = ctk.CTkFrame(
            popup,
            fg_color=self.cor_primaria,
            border_color=self.cor_borda,
            border_width=2,
            corner_radius=12,
            width=500,
            height=290
        )
        card.pack(padx=12, pady=12, fill="both", expand=True)

        ctk.CTkLabel(
            card,
            text=self._get_text("orders_found"),
            font=("Consolas", 15, "bold"),
            text_color=self.cor_texto,
            fg_color="transparent"
        ).pack(pady=(10, 6))

        ctk.CTkLabel(
            card,
            text=self._get_text("orders_header"),
            font=("Consolas", 12, "bold"),
            text_color=self.cor_texto,
            fg_color=self.cor_fundo,
            anchor="w"
        ).pack(padx=10, fill="x")

        lista_frame = ctk.CTkScrollableFrame(
            card,
            fg_color=self.cor_fundo,
            corner_radius=8,
            border_color=self.cor_borda,
            border_width=1,
            width=460,
            height=150,
            orientation="vertical"
        )
        lista_frame.pack(padx=10, pady=(0, 10), fill="both", expand=True)

        for o in ordens:
            num, codigo, desc, data = o[1], o[2], o[3], o[4]
            total = o[13] or 0
            texto = f"{str(num):<8}| {str(codigo):<6}| {str(desc):<20.20}| {str(total):>4} | {str(data)}"
            ctk.CTkButton(
                lista_frame,
                text=texto,
                anchor="w",
                fg_color="transparent",
                hover_color=self.cor_hover,
                text_color=self.cor_texto,
                font=("Consolas", 12),
                command=criar_callback(o)
            ).pack(fill="x", pady=2)

        ctk.CTkButton(
            card,
            text=self._get_text("cancel"),
            fg_color=self.cor_alerta if hasattr(self, "cor_alerta") else "#a83232",
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            width=100,
            font=("Arial", 12),
            command=popup.destroy
        ).pack(pady=(0, 12))

        popup.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (popup.winfo_width() // 2) - 200
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (popup.winfo_height() // 2)
        popup.geometry(f"+{max(10, x)}+{y}")

    def _executar_e_fechar(self, ordem, popup):
        self._carregar_ordem(ordem)
        popup.destroy()

    def _carregar_ordem(self, resultado):
        try:
            schema = get_schema()
            cadastro_id = resultado[0]

            with get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET LOCAL search_path = {schema};")
                    cursor.execute(f"""
                        SELECT
                            id,
                            numero_ordem,
                            codigo,
                            descricao,
                            data,
                            comprimento_matriz,
                            largura_matriz,
                            cortador,
                            ajudante,
                            total_folhas,
                            metros_utilizados,
                            bobinas_utilizadas,
                            composicao_tecido,
                            total_pecas,
                            rendimento,
                            observacoes
                        FROM {schema}.cadastro_de_corte
                        WHERE id = %s
                    """, (cadastro_id,))
                    dados_ordem = cursor.fetchone()

                    if not dados_ordem:
                        messagebox.showwarning(self._get_text("warning"), self._get_text("order_not_found"))
                        return

                    # Preenche campos básicos
                    campos_principais = {
                        "order_number": dados_ordem[1],
                        "code": dados_ordem[2],
                        "description": dados_ordem[3],
                        "date": dados_ordem[4],
                        "length": dados_ordem[5],
                        "width": dados_ordem[6],
                        "cutter": dados_ordem[7],
                        "assistant": dados_ordem[8]
                    }

                    for campo, valor in campos_principais.items():
                        if campo in self.campos:
                            self.campos[campo].delete(0, 'end')
                            self.campos[campo].insert(0, str(valor))

                    # Preenche totais
                    self.total_pecas_valor.configure(text=str(dados_ordem[13] or 0))
                    self.folhas_valor.configure(text=str(dados_ordem[9] or 0))
                    self.metros_valor.configure(text=str(dados_ordem[10] or 0))
                    self.rendimento_valor.configure(text=f"{dados_ordem[14] or 0}%")

                    # Preenche observações
                    self.obs_entry.delete(0, 'end')
                    self.obs_entry.insert(0, dados_ordem[15] if dados_ordem[15] else self._get_text("no_observation"))

                    # Armazena dados completos
                    self.dados_ordem_atual = {
                        "numero_ordem": dados_ordem[1],
                        "codigo": dados_ordem[2],
                        "descricao": dados_ordem[3],
                        "data": dados_ordem[4],
                        "comprimento_matriz": dados_ordem[5],
                        "largura_matriz": dados_ordem[6],
                        "cortador": dados_ordem[7],
                        "ajudante": dados_ordem[8],
                        "total_folhas": dados_ordem[9],
                        "metros_utilizados": dados_ordem[10],
                        "bobinas_utilizadas": dados_ordem[11],
                        "composicao_tecido": dados_ordem[12],
                        "total_pecas": dados_ordem[13],
                        "rendimento": dados_ordem[14],
                        "observacoes": dados_ordem[15]
                    }

                    # Tecidos
                    cursor.execute(f"""
                        SELECT tecido, cor, composicao, bobinas, folhas,
                               pp, p, m, g, gg, g1, g2, g3, total_pecas
                        FROM {schema}.cadastro_de_corte_tecidos
                        WHERE cadastro_id = %s
                    """, (cadastro_id,))
                    tecidos = cursor.fetchall()
                    self.tree_tecido.delete(*self.tree_tecido.get_children())
                    for tecido in tecidos:
                        self.tree_tecido.insert('', 'end', values=tecido)

                    # Lotes
                    cursor.execute(f"""
                        SELECT lote, tecido, cor, composicao, bobinas, folhas,
                               pp, p, m, g, gg, g1, g2, g3, total_lote
                        FROM {schema}.cadastro_de_corte_lotes
                        WHERE cadastro_id = %s
                        ORDER BY
                            COALESCE(NULLIF(lote,'')::int, 0) ASC
                    """, (cadastro_id,))
                    lotes = cursor.fetchall()
                    self.tree_lote.delete(*self.tree_lote.get_children())
                    for lote in lotes:
                        self.tree_lote.insert('', 'end', values=lote)

            self._atualizar_porcentagem_real()

        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("load_order_error", erro=e))

    # --- Helper para montar nome de arquivo padrão ------------------------------
    def _nome_pdf_padrao(self):
        from datetime import datetime
        import re

        codigo = str(self.dados_ordem_atual.get("codigo", "SEM_COD")).strip()
        descricao = str(self.dados_ordem_atual.get("descricao", "SEM_DESC")).strip()
        data = str(self.dados_ordem_atual.get("data", datetime.now().strftime("%d-%m-%Y"))).strip()

        data = data.replace("/", "-")
        descricao = descricao.replace(" ", "_")

        inval = r'[\\/:*?"<>|]'
        codigo = re.sub(inval, "_", codigo)
        descricao = re.sub(inval, "_", descricao)
        data = re.sub(inval, "-", data)

        return f"{codigo}_{descricao}_{data}.pdf"

    # -------------------- Pré-visualização (PDF real) --------------------
    def previsualizar_controle(self):
        if not self.dados_ordem_atual:
            messagebox.showwarning(self._get_text("warning"), self._get_text("no_order_loaded"))
            return

        def _to_int(v):
            if v is None:
                return 0
            s = str(v).strip().replace('.', '').replace(',', '.')
            try:
                return int(round(float(s)))
            except Exception:
                d = ''.join(ch for ch in str(v) if ch.isdigit())
                return int(d) if d else 0

        total_pecas_calc = 0
        for item in self.tree_tecido.get_children():
            vals = self.tree_tecido.item(item)['values']
            if len(vals) > 13:
                total_pecas_calc += _to_int(vals[13])

        try:
            self.dados_ordem_atual["total_pecas"] = total_pecas_calc
            if hasattr(self, "total_pecas_valor"):
                self.total_pecas_valor.configure(text=str(total_pecas_calc))
        except Exception:
            pass

        dados_pdf = {
            "numero_ordem": self.dados_ordem_atual.get("numero_ordem", ""),
            "codigo": self.dados_ordem_atual.get("codigo", ""),
            "descricao": self.dados_ordem_atual.get("descricao", ""),
            "data": self.dados_ordem_atual.get("data", ""),
            "cortador": self.dados_ordem_atual.get("cortador", ""),
            "ajudante": self.dados_ordem_atual.get("ajudante", ""),
            "total_pecas": total_pecas_calc,
            "rendimento": self.dados_ordem_atual.get("rendimento", ""),
            "folhas": self.dados_ordem_atual.get("total_folhas", ""),
            "metros_utilizados": self.dados_ordem_atual.get("metros_utilizados", ""),
            "observacoes": self.dados_ordem_atual.get("observacoes", ""),
            "tecidos": [],
            "lotes": []
        }

        for it in self.tree_tecido.get_children():
            v = self.tree_tecido.item(it)['values']
            dados_pdf["tecidos"].append({
                "tecidos": v[0], "cor": v[1], "comp": v[2], "bob": v[3], "folhas": v[4],
                "pp": v[5], "p": v[6], "m": v[7], "g": v[8], "gg": v[9],
                "g1": v[10], "g2": v[11], "g3": v[12], "total": v[13]
            })
        for it in self.tree_lote.get_children():
            v = self.tree_lote.item(it)["values"]
            if not v:
                continue
            dados_pdf["lotes"].append({
                "nº": v[0], "tecidos": v[1], "cor": v[2], "comp": v[3],
                "bob": v[4], "folhas": v[5],
                "pp": v[6], "p": v[7], "m": v[8], "g": v[9], "gg": v[10],
                "g1": v[11], "g2": v[12], "g3": v[13], "total": v[14],
            })

        import tempfile
        tmp = tempfile.gettempdir()
        nome = f"ORDEM_CORTE_{(dados_pdf['numero_ordem'] or 'TMP')}.pdf"
        temp_pdf = os.path.join(tmp, nome)
        try:
            self._gerar_pdf_ordem_de_corte(dados_pdf, temp_pdf)
        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("temp_pdf_error", erro=e))
            return

        self._ultimo_pdf_temp = temp_pdf
        self._mostrar_previsualizacao_pdf(temp_pdf)

    def _mostrar_previsualizacao_pdf(self, pdf_path):
        import os
        import sys
        import subprocess
        from tkinter import messagebox, Canvas, Frame
        from PIL import Image
        import customtkinter as ctk

        img = None

        try:
            import fitz
            doc = fitz.open(pdf_path)
            page = doc[0]
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            doc.close()
        except Exception:
            try:
                from pdf2image import convert_from_path
                pages = convert_from_path(pdf_path, dpi=150)
                img = pages[0]
            except Exception as e:
                try:
                    if sys.platform.startswith("darwin"):
                        subprocess.Popen(["open", pdf_path])
                    elif os.name == "nt":
                        os.startfile(pdf_path)
                    else:
                        subprocess.Popen(["xdg-open", pdf_path])
                    return
                except Exception:
                    messagebox.showerror(
                        self._get_text("error"),
                        self._get_text("pdf_preview_unavailable")
                    )
                    return

        if img is None:
            messagebox.showerror(self._get_text("error"), self._get_text("pdf_preview_unavailable"))
            return

        largura_max_preview = 760
        if img.width > largura_max_preview:
            fator = largura_max_preview / img.width
            nova_altura = int(img.height * fator)
            img = img.resize((largura_max_preview, nova_altura), Image.LANCZOS)

        self._preview_ctkimage = ctk.CTkImage(
            light_image=img,
            size=(img.width, img.height)
        )

        janela = ctk.CTkToplevel(self)
        janela.title(self._get_text("preview_title"))
        janela.geometry("850x750")
        janela.minsize(850, 750)
        janela.configure(fg_color=getattr(self, "cor_fundo", "#0E1525"))

        main_frame = ctk.CTkFrame(janela, fg_color=getattr(self, "cor_fundo", "#0E1525"))
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = Canvas(main_frame, bg=getattr(self, "cor_fundo", "#0E1525"), highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(main_frame, orientation="vertical", command=canvas.yview)
        scrollable = Frame(canvas, bg=getattr(self, "cor_fundo", "#0E1525"))

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        canvas.create_window((0, 0), window=scrollable, anchor="nw")

        def configure_scrollregion(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable.bind("<Configure>", configure_scrollregion)

        label_imagem = ctk.CTkLabel(
            scrollable,
            image=self._preview_ctkimage,
            text="",
            fg_color=getattr(self, "cor_fundo", "#0E1525"),
        )
        label_imagem.pack(pady=10)

        def _on_mouse_wheel(event):
            if event.delta:
                canvas.yview_scroll(-int(event.delta / 120), "units")
            else:
                if getattr(event, "num", None) == 4:
                    canvas.yview_scroll(-3, "units")
                elif getattr(event, "num", None) == 5:
                    canvas.yview_scroll(3, "units")

        def _bind_scroll():
            canvas.bind_all("<MouseWheel>", _on_mouse_wheel)
            canvas.bind_all("<Button-4>", _on_mouse_wheel)
            canvas.bind_all("<Button-5>", _on_mouse_wheel)

        def _unbind_scroll(*_):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        _bind_scroll()
        janela.bind("<Destroy>", _unbind_scroll)

        botoes = ctk.CTkFrame(janela, fg_color=getattr(self, "cor_fundo", "#0E1525"))
        botoes.pack(fill="x", padx=10, pady=(0, 10))

        cor_prim = getattr(self, "cor_primaria", "#1F538D")
        cor_hover = getattr(self, "cor_hover", "#14375E")
        cor_texto = getattr(self, "cor_texto", "#ffffff")
        cor_fechar = getattr(self, "cor_alerta", "#a83232")

        ctk.CTkButton(
            botoes,
            text=self._get_text("save_pdf"),
            width=120,
            command=self._salvar_pdf,
            fg_color=cor_prim,
            hover_color=cor_hover,
            text_color=cor_texto,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            botoes,
            text=self._get_text("print"),
            width=120,
            command=self._imprimir_pdf,
            fg_color=cor_prim,
            hover_color=cor_hover,
            text_color=cor_texto,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            botoes,
            text=self._get_text("close"),
            width=120,
            command=janela.destroy,
            fg_color=cor_fechar,
            hover_color="#7a2525",
            text_color=cor_texto,
        ).pack(side="right", padx=10)

        janela.update_idletasks()
        largura_monitor = janela.winfo_screenwidth()
        altura_monitor = janela.winfo_screenheight()
        largura_janela = janela.winfo_width()
        altura_janela = janela.winfo_height()

        pos_x = (largura_monitor // 3) - (largura_janela // 2)
        pos_y = (altura_monitor // 5) - (altura_janela // 2)
        janela.geometry(f"{largura_janela}x{altura_janela}+{pos_x}+{pos_y}")
        janela.grab_set()

        self._preview_window = janela
        self._preview_canvas = canvas

    # -------------------- (opcional) salvar direto --------------------
    def gerar_pdf(self):
        if not self.dados_ordem_atual:
            messagebox.showwarning(self._get_text("warning"), self._get_text("no_order_loaded"))
            return

        total_pecas_calc = 0
        for item in self.tree_tecido.get_children():
            valores = self.tree_tecido.item(item)['values']
            try:
                total_pecas_calc += int(valores[13])
            except (ValueError, IndexError, TypeError):
                pass

        dados_pdf = {
            "numero_ordem": self.dados_ordem_atual["numero_ordem"],
            "codigo": self.dados_ordem_atual["codigo"],
            "descricao": self.dados_ordem_atual["descricao"],
            "data": self.dados_ordem_atual["data"],
            "cortador": self.dados_ordem_atual["cortador"],
            "ajudante": self.dados_ordem_atual["ajudante"],
            "total_pecas": total_pecas_calc,
            "rendimento": self.dados_ordem_atual["rendimento"],
            "folhas": self.dados_ordem_atual["total_folhas"],
            "metros_utilizados": self.dados_ordem_atual["metros_utilizados"],
            "observacoes": self.dados_ordem_atual["observacoes"],
            "tecidos": [],
            "lotes": []
        }

        for item in self.tree_tecido.get_children():
            valores = self.tree_tecido.item(item)['values']
            dados_pdf["tecidos"].append({
                "tecidos": valores[0], "cor": valores[1], "comp": valores[2], "bob": valores[3], "folhas": valores[4],
                "pp": valores[5], "p": valores[6], "m": valores[7], "g": valores[8], "gg": valores[9],
                "g1": valores[10], "g2": valores[11], "g3": valores[12], "total": valores[13]
            })

        for item in self.tree_lote.get_children():
            vals = self.tree_lote.item(item)["values"]
            dados_pdf["lotes"].append({
                "nº": vals[0], "tecidos": vals[1], "cor": vals[2], "comp": vals[3], "bob": vals[4], "folhas": vals[5],
                "pp": vals[6], "p": vals[7], "m": vals[8], "g": vals[9], "gg": vals[10],
                "g1": vals[11], "g2": vals[12], "g3": vals[13], "total": vals[14],
            })

        nome_padrao = f"ORDEM_CORTE_{dados_pdf['numero_ordem']}.pdf"
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        caminho_arquivo = filedialog.asksaveasfilename(
            initialdir=desktop, defaultextension=".pdf",
            filetypes=[(self._get_text("pdf_files"), "*.pdf")], initialfile=nome_padrao
        )

        if caminho_arquivo:
            self._gerar_pdf_ordem_de_corte(dados_pdf, caminho_arquivo)
            messagebox.showinfo(self._get_text("success"), self._get_text("pdf_saved_success", caminho=caminho_arquivo))

    # -------------------- Impressora/Salvar usados pelo preview --------------------
    def _salvar_pdf(self):
        if not self.dados_ordem_atual:
            return

        from tkinter import filedialog, messagebox
        import os

        def _to_int(v):
            s = str(v).strip().replace(".", "").replace(",", ".")
            try:
                return int(round(float(s)))
            except Exception:
                return int("".join(ch for ch in str(v) if ch.isdigit()) or 0)

        total_pecas_calc = 0
        for item in self.tree_tecido.get_children():
            vals = self.tree_tecido.item(item)['values']
            if len(vals) > 13:
                total_pecas_calc += _to_int(vals[13])

        dados_pdf = {
            "numero_ordem": self.dados_ordem_atual.get("numero_ordem", ""),
            "codigo": self.dados_ordem_atual.get("codigo", ""),
            "descricao": self.dados_ordem_atual.get("descricao", ""),
            "data": self.dados_ordem_atual.get("data", ""),
            "cortador": self.dados_ordem_atual.get("cortador", ""),
            "ajudante": self.dados_ordem_atual.get("ajudante", ""),
            "total_pecas": total_pecas_calc,
            "rendimento": self.dados_ordem_atual.get("rendimento", ""),
            "folhas": self.dados_ordem_atual.get("total_folhas", ""),
            "metros_utilizados": self.dados_ordem_atual.get("metros_utilizados", ""),
            "observacoes": self.dados_ordem_atual.get("observacoes", ""),
            "tecidos": [],
            "lotes": [],
        }

        for item in self.tree_tecido.get_children():
            v = self.tree_tecido.item(item)['values']
            dados_pdf["tecidos"].append({
                "tecidos": v[0], "cor": v[1], "comp": v[2], "bob": v[3], "folhas": v[4],
                "pp": v[5], "p": v[6], "m": v[7], "g": v[8], "gg": v[9], "g1": v[10],
                "g2": v[11], "g3": v[12], "total": v[13]
            })

        for item in self.tree_lote.get_children():
            v = self.tree_lote.item(item)['values']
            dados_pdf["lotes"].append({
                "nº": v[0], "tecidos": v[1], "cor": v[2], "comp": v[3], "bob": v[4],
                "folhas": v[5], "pp": v[6], "p": v[7], "m": v[8], "g": v[9],
                "gg": v[10], "g1": v[11], "g2": v[12], "g3": v[13], "total": v[14]
            })

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        nome_padrao = self._nome_pdf_padrao()

        caminho_arquivo = filedialog.asksaveasfilename(
            initialdir=desktop,
            defaultextension=".pdf",
            filetypes=[(self._get_text("pdf_files"), "*.pdf")],
            initialfile=nome_padrao
        )

        if caminho_arquivo:
            self._gerar_pdf_ordem_de_corte(dados_pdf, caminho_arquivo)
            messagebox.showinfo(self._get_text("success"), self._get_text("pdf_saved_success", caminho=caminho_arquivo))

    def _imprimir_pdf(self):
        import os, sys, tempfile, shutil
        from tkinter import messagebox, filedialog

        if not getattr(self, "dados_ordem_atual", None):
            messagebox.showwarning(self._get_text("warning"), self._get_text("no_order_loaded"))
            return

        def _to_int(v):
            s = str(v).strip().replace(".", "").replace(",", ".")
            try:
                return int(round(float(s)))
            except Exception:
                return int("".join(ch for ch in str(v) if ch.isdigit()) or 0)

        total_pecas_calc = 0
        for item in self.tree_tecido.get_children():
            vals = self.tree_tecido.item(item)['values']
            if len(vals) > 13:
                total_pecas_calc += _to_int(vals[13])

        dados_pdf = {
            "numero_ordem": self.dados_ordem_atual.get("numero_ordem", ""),
            "codigo": self.dados_ordem_atual.get("codigo", ""),
            "descricao": self.dados_ordem_atual.get("descricao", ""),
            "data": self.dados_ordem_atual.get("data", ""),
            "cortador": self.dados_ordem_atual.get("cortador", ""),
            "ajudante": self.dados_ordem_atual.get("ajudante", ""),
            "total_pecas": total_pecas_calc,
            "rendimento": self.dados_ordem_atual.get("rendimento", ""),
            "folhas": self.dados_ordem_atual.get("total_folhas", ""),
            "metros_utilizados": self.dados_ordem_atual.get("metros_utilizados", ""),
            "observacoes": self.dados_ordem_atual.get("observacoes", ""),
            "tecidos": [],
            "lotes": []
        }

        for item in self.tree_tecido.get_children():
            v = self.tree_tecido.item(item)['values']
            dados_pdf["tecidos"].append({
                "tecidos": v[0], "cor": v[1], "comp": v[2], "bob": v[3], "folhas": v[4],
                "pp": v[5], "p": v[6], "m": v[7], "g": v[8], "gg": v[9], "g1": v[10],
                "g2": v[11], "g3": v[12], "total": v[13]
            })

        for item in self.tree_lote.get_children():
            v = self.tree_lote.item(item)['values']
            dados_pdf["lotes"].append({
                "nº": v[0], "tecidos": v[1], "cor": v[2], "comp": v[3], "bob": v[4],
                "folhas": v[5], "pp": v[6], "p": v[7], "m": v[8], "g": v[9],
                "gg": v[10], "g1": v[11], "g2": v[12], "g3": v[13], "total": v[14]
            })

        tmp_dir = tempfile.gettempdir()
        temp_path = os.path.join(tmp_dir, "ORDEM_CORTE_TMP.pdf")
        try:
            self._gerar_pdf_ordem_de_corte(dados_pdf, temp_path)
        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("temp_pdf_error", erro=e))
            return

        if messagebox.askyesno(self._get_text("save_pdf"), "Deseja salvar uma cópia do PDF antes de imprimir?"):
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            nome_padrao = self._nome_pdf_padrao()
            destino = filedialog.asksaveasfilename(
                initialdir=desktop,
                defaultextension=".pdf",
                filetypes=[(self._get_text("pdf_files"), "*.pdf")],
                initialfile=nome_padrao
            )
            if destino:
                try:
                    shutil.copyfile(temp_path, destino)
                    messagebox.showinfo(self._get_text("success"), self._get_text("pdf_saved_success", caminho=destino))
                except Exception as e:
                    messagebox.showerror(self._get_text("error"), f"Falha ao salvar o PDF:\n{e}")

        if sys.platform.startswith("win"):
            try:
                os.startfile(temp_path, "print")
                messagebox.showinfo(self._get_text("print"), "Arquivo enviado para a impressora.")
            except Exception as e:
                messagebox.showerror(self._get_text("error"), f"Falha ao imprimir:\n{e}")
        else:
            messagebox.showinfo(
                self._get_text("print"),
                "Impressão direta é suportada no Windows. Abra o PDF salvo e imprima pelo visualizador do sistema."
            )

    # -------------------- Geração do PDF --------------------
    def _gerar_pdf_ordem_de_corte(self, dados, nome_arquivo):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from datetime import datetime
        import os

        c = canvas.Canvas(nome_arquivo, pagesize=A4)
        largura, altura = A4
        margem = 1 * cm
        row_height = 0.5 * cm
        available_width = largura - 2 * margem
        y = altura - margem

        c.setFillColorRGB(0.11, 0.32, 0.55)
        c.rect(0, y - 1.8 * cm, largura, 2.5 * cm, fill=1, stroke=0)
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LOGO.jpg")
        if os.path.exists(logo_path):
            try:
                from reportlab.lib.utils import ImageReader
                from PIL import Image as PilImage
                img_logo = PilImage.open(logo_path)
                w, h = img_logo.size
                max_logo_height = 1.8 * cm
                aspect = w / h
                logo_height = max_logo_height
                logo_width = logo_height * aspect
                rect_bottom = y - 1.8 * cm
                rect_height = 2.5 * cm
                logo_y = rect_bottom + (rect_height - logo_height) / 2
                logo_x = margem
                c.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height, mask='auto')
            except Exception:
                pass

        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(1, 1, 1)
        c.drawCentredString(largura / 2, y - 1.1 * cm, self._get_text("cut_order_produced"))
        y -= 2.8 * cm

        c.setFillColorRGB(0, 0, 0)

        # 1) DADOS BÁSICOS (duas colunas)
        c.setFont("Helvetica", 9)
        pares = [
            (self._get_text("order_number"), dados.get("numero_ordem", "")),
            (self._get_text("code"), dados.get("codigo", "")),
            (self._get_text("description"), dados.get("descricao", "")),
            (self._get_text("date"), dados.get("data", "")),
            (self._get_text("cutter"), dados.get("cortador", "")),
            (self._get_text("assistant"), dados.get("ajudante", "")),
        ]
        for i in range(0, len(pares), 2):
            c.drawString(margem, y, f"{pares[i][0]:<12} {pares[i][1]}")
            if i + 1 < len(pares):
                c.drawString(largura / 2, y, f"{pares[i + 1][0]:<12} {pares[i + 1][1]}")
            y -= 0.6 * cm

        def tabela_header(text, ncols):
            nonlocal y
            table_w = available_width
            x0 = (largura - table_w) / 2
            c.setStrokeColorRGB(0, 0, 0)
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 15)
            c.line(x0, y, x0 + table_w, y)
            c.drawCentredString(largura / 2, y - 1 * cm, text)
            y -= 2 * cm
            return x0, table_w / ncols

        # 2) INFORMAÇÕES DO CORTE (tecidos)
        cols_t = [
            self._get_text("fabric"),
            self._get_text("color"),
            self._get_text("composition"),
            self._get_text("rolls"),
            self._get_text("sheets_short"),
            self._get_text("pp"),
            self._get_text("p"),
            self._get_text("m"),
            self._get_text("g"),
            self._get_text("gg"),
            self._get_text("g1"),
            self._get_text("g2"),
            self._get_text("g3"),
            self._get_text("total")
        ]
        original_larguras_t = [90, 45, 80, 35, 40, 22, 22, 22, 22, 22, 22, 22, 22, 45]
        scale_t = available_width / sum(original_larguras_t)
        larguras_t = [w * scale_t for w in original_larguras_t]
        x0_t, w_t = tabela_header(self._get_text("cut_information"), len(cols_t))
        c.setFont("Helvetica-Bold", 7)
        x = x0_t
        row_height = 0.5 * cm
        for col, w in zip(cols_t, larguras_t):
            c.rect(x, y - row_height, w, row_height, fill=0)
            c.drawCentredString(x + w / 2, y - row_height + 0.1 * cm, col)
            x += w
        y -= row_height
        c.setFont("Helvetica", 6)
        for t in dados.get("tecidos", []):
            x = x0_t
            vals = [
                t.get("tecidos", ""), t.get("cor", ""), t.get("comp", ""),
                str(t.get("bob", "")), str(t.get("folhas", "")),
                str(t.get("pp", "")), str(t.get("p", "")), str(t.get("m", "")),
                str(t.get("g", "")), str(t.get("gg", "")), str(t.get("g1", "")),
                str(t.get("g2", "")), str(t.get("g3", "")), str(t.get("total", ""))
            ]
            for v, w in zip(vals, larguras_t):
                c.rect(x, y - row_height, w, row_height, fill=0)
                c.drawCentredString(x + w / 2, y - row_height + 0.1 * cm, v)
                x += w
            y -= row_height

        # 3) LOTES DE CORTE (tabela)
        y -= 0.5 * cm
        cols_l = [
            self._get_text("lot_number"),
            self._get_text("fabric"),
            self._get_text("color"),
            self._get_text("composition"),
            self._get_text("rolls"),
            self._get_text("sheets_short"),
            self._get_text("pp"),
            self._get_text("p"),
            self._get_text("m"),
            self._get_text("g"),
            self._get_text("gg"),
            self._get_text("g1"),
            self._get_text("g2"),
            self._get_text("g3"),
            self._get_text("total")
        ]
        original_larguras_l = [30, 60, 45, 80, 35, 40, 22, 22, 22, 22, 22, 22, 22, 22, 45]
        scale_l = available_width / sum(original_larguras_l)
        larguras_l = [w * scale_l for w in original_larguras_l]
        x0_l, w_l = tabela_header(self._get_text("cut_lots"), len(cols_l))
        c.setFont("Helvetica-Bold", 7)
        x = x0_l
        for col, w in zip(cols_l, larguras_l):
            c.rect(x, y - row_height, w, row_height, fill=0)
            c.drawCentredString(x + w / 2, y - row_height + 0.1 * cm, col)
            x += w
        y -= row_height
        c.setFont("Helvetica", 6)
        for idx, lote in enumerate(dados.get("lotes", []), start=1):
            x = x0_l
            num = lote.get("numero") or lote.get("nº") or str(idx)
            vals = [
                num, lote.get("tecidos", ""), lote.get("cor", ""), lote.get("comp", ""),
                str(lote.get("bob", "")), str(lote.get("folhas", "")),
                str(lote.get("pp", "")), str(lote.get("p", "")), str(lote.get("m", "")),
                str(lote.get("g", "")), str(lote.get("gg", "")), str(lote.get("g1", "")),
                str(lote.get("g2", "")), str(lote.get("g3", "")), str(lote.get("total", ""))
            ]
            for v, w in zip(vals, larguras_l):
                c.rect(x, y - row_height, w, row_height, fill=0)
                c.drawCentredString(x + w / 2, y - row_height + 0.1 * cm, v)
                x += w
            y -= row_height

        # 4) PORCENTAGEM REAL
        y -= 0.5 * cm
        cols_pr = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]
        x0_pr, w_pr = tabela_header(self._get_text("real_percentage"), len(cols_pr))

        keys = [k.lower() for k in cols_pr]
        totais = {k: sum(int(l.get(k, 0) or 0) for l in dados.get("lotes", [])) for k in keys}
        total_peças = sum(totais.values()) or 1
        pct = {k: totais[k] / total_peças * 100 for k in keys}

        c.setFont("Helvetica-Bold", 7)
        x = x0_pr
        for col in cols_pr:
            c.rect(x, y - row_height, w_pr, row_height, fill=0)
            c.drawCentredString(x + w_pr / 2, y - row_height + 0.1 * cm, col)
            x += w_pr
        y -= row_height

        c.setFont("Helvetica", 6)
        x = x0_pr
        for k in keys:
            txt = f"{pct.get(k, 0):.1f}%"
            c.rect(x, y - row_height, w_pr, row_height, fill=0)
            c.drawCentredString(x + w_pr / 2, y - row_height + 0.1 * cm, txt)
            x += w_pr
        y -= row_height

        # 5) TOTAL DE PEÇAS E RENDIMENTO
        y -= 0.4 * cm
        c.setFont("Helvetica-Bold", 10)
        c.line((largura - available_width) / 2, y, (largura + available_width) / 2, y)
        c.drawString(margem, y - 0.3 * cm, self._get_text("total_pieces_yield"))
        y -= 0.8 * cm
        totais_lbl = [
            (self._get_text("total_pieces"), str(dados.get("total_pecas", ""))),
            (self._get_text("yield_label"), str(dados.get("rendimento", ""))),
            (self._get_text("sheets_label_full"), str(dados.get("folhas", ""))),
            (self._get_text("meters_used"), str(dados.get("metros_utilizados", "")))
        ]
        c.setFont("Helvetica", 9)
        for lbl, val in totais_lbl:
            c.drawString(margem, y, f"{lbl:<20} {val}")
            y -= 0.6 * cm

        # 6) OBSERVAÇÕES
        y -= 0.4 * cm
        c.setFont("Helvetica-Bold", 10)
        c.line((largura - available_width) / 2, y, (largura + available_width) / 2, y)
        c.drawString(margem, y - 0.3 * cm, self._get_text("observations_title"))
        y -= 0.8 * cm
        obs_h = 2 * cm
        x0_obs = (largura - available_width) / 2
        c.rect(x0_obs, y - obs_h, available_width, obs_h, fill=0)
        c.setFont("Helvetica", 8)
        c.drawString(x0_obs + 0.2 * cm, y - 0.3 * cm, dados.get("observacoes", ""))
        y -= obs_h + 0.4 * cm

        # 7) ASSINATURA
        texto = self._get_text("signature")
        tamanho_fonte = 9
        c.setFont("Helvetica", tamanho_fonte)
        text_w = c.stringWidth(texto, "Helvetica", tamanho_fonte)
        x_texto = (largura - text_w) / 2
        y_texto = y - 0.5 * cm
        min_y = margem + 1 * cm
        if y_texto < min_y:
            y_texto = min_y
        c.drawString(x_texto, y_texto, texto)
        y_linha = y_texto - 0.4 * cm
        line_len = 8 * cm
        x_linha = (largura - line_len) / 2
        c.line(x_linha, y_linha, x_linha + line_len, y_linha)
        y = y_linha - 0.5 * cm

        # 8) RODAPÉ
        c.setFont("Helvetica-Oblique", 7)
        c.drawRightString(largura - margem, 0.5 * cm,
                          self._get_text("printed_on", date=datetime.now().strftime('%d/%m/%Y %H:%M')))
        c.save()

    # -------------------- utilitários --------------------
    def _draw_table_with_borders(self, c, x, y, colunas, larguras_padrao, dados):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        altura_linha = 20
        fonte = "Helvetica"
        tamanho_fonte = 10
        padding = 6
        larguras = []
        for i, col in enumerate(colunas):
            max_largura = stringWidth(col, fonte, tamanho_fonte) + padding
            for item in dados:
                texto = str(item.get(col.lower().replace(".", ""), ""))
                largura_texto = stringWidth(texto, fonte, tamanho_fonte) + padding
                if largura_texto > max_largura:
                    max_largura = largura_texto
            if i == 0 and col.lower().startswith("n"):
                max_largura = max(max_largura, 40)
            else:
                max_largura = max(max_largura, 25)
                max_largura = min(max_largura, 80)
            larguras.append(max_largura)

        c.setFont("Helvetica-Bold", tamanho_fonte)
        current_x = x
        for col, larg in zip(colunas, larguras):
            c.rect(current_x, y - altura_linha, larg, altura_linha, fill=0)
            c.drawCentredString(current_x + larg / 2, y - altura_linha + 5, col)
            current_x += larg
        y -= altura_linha

        c.setFont(fonte, tamanho_fonte)
        for item in dados:
            current_x = x
            for col, larg in zip(colunas, larguras):
                c.rect(current_x, y - altura_linha, larg, altura_linha, fill=0)
                valor = str(item.get(col.lower().replace(".", ""), ""))
                c.drawCentredString(current_x + larg / 2, y - altura_linha + 5, valor)
                current_x += larg
            y -= altura_linha
        return y

    def atualizar_tema(self, novo_tema):
        if novo_tema == "dark":
            self.cor_fundo = "#0E1525"
            self.cor_texto = "white"
        else:
            self.cor_fundo = "#F0F0F0"
            self.cor_texto = "black"

        self.configure(fg_color=self.cor_fundo)
        for widget in self.winfo_children():
            if hasattr(widget, 'configure'):
                if 'text_color' in widget.configure():
                    widget.configure(text_color=self.cor_texto)
                if 'fg_color' in widget.configure():
                    widget.configure(fg_color=self.cor_fundo)
                if 'border_color' in widget.configure():
                    widget.configure(border_color=self.cor_borda)

    def _draw_section_header(self, c, x, y, texto, largura):
        from reportlab.lib.units import cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, texto)
        y -= 0.3 * cm
        c.line(x, y, largura - x, y)
        return y - 0.5 * cm

    def _atualizar_porcentagem_real(self):
        tamanhos = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]
        totais = {t: 0 for t in tamanhos}
        total_geral = 0

        for item in self.tree_lote.get_children():
            valores = self.tree_lote.item(item)['values']
            for i, t in enumerate(tamanhos, start=6):
                qtd_str = str(valores[i])
                try:
                    qtd = int(qtd_str)
                except Exception:
                    qtd = int(''.join(ch for ch in qtd_str if ch.isdigit()) or 0)
                totais[t] += qtd
                total_geral += qtd

        porcentagens = []
        for t in tamanhos:
            pct = (totais[t] / total_geral * 100) if total_geral > 0 else 0
            porcentagens.append(f"{pct:.1f}%")

        self.tree_porcentagem.delete(*self.tree_porcentagem.get_children())
        self.tree_porcentagem.insert("", "end", values=porcentagens)


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("Visualização da Ordem de Corte")


    class SistemaMock:
        idioma_atual = "pt_BR"
        cor_fundo = "#121212"
        cor_borda = "#2E2E3E"
        cor_primaria = "#1E1E2E"
        cor_hover = "#3E3E4E"
        cor_sucesso = "#57D9A3"
        cor_alerta = "#FFBB55"
        cor_imprimir = "#646CFF"
        cor_texto = "#E0E0E0"


    OrdemCorteFinalizada(root, SistemaMock()).pack(fill="both", expand=True, padx=20, pady=20)
    root.mainloop()
