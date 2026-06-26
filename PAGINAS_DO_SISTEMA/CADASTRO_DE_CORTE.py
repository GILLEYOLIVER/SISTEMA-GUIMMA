import os
from datetime import datetime
from tkinter import ttk, messagebox
import tkinter.font as tkfont

import customtkinter as ctk
from PIL import Image, ImageTk
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph

from PAGINAS_DO_SISTEMA.TEMAS import padronizar_treeview, padronizar_treeviews_container

# Importação robusta do PyMuPDF
try:
    import fitz as _fitz  # tentar importar 'fitz'
    # Se for o pacote errado (aquele que não tem .open ou .Document), força usar pymupdf
    if not hasattr(_fitz, "open") and not hasattr(_fitz, "Document"):
        raise ImportError("Pacote 'fitz' incorreto detectado")
    fitz = _fitz
except Exception:
    # Fallback explícito para o PyMuPDF correto
    import pymupdf as fitz

from io import BytesIO

# === PostgreSQL helpers ===
try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception as e:
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready


def _pg_connect():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            schema = get_schema()
            cur.execute(f"SET search_path TO {schema}")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    return conn


def centralizar_janela(janela, largura, altura, parent=None):
    parent = parent or janela
    janela.update_idletasks()
    sw = parent.winfo_screenwidth()
    sh = parent.winfo_screenheight()

    largura = min(largura, sw - 40)
    altura = min(altura, sh - 120)

    x = (sw - largura) // 2
    y = (sh - altura) // 2
    janela.geometry(f"{largura}x{altura}+{x}+{y}")
    try:
        janela.minsize(900, 720)
    except Exception:
        pass


class CadastroOrdemCorte(ctk.CTkFrame):

    def __init__(self, master, sistema=None):
        super().__init__(master)
        self.master = master
        self.sistema = sistema
        self.pack(fill="both", expand=True)

        # Inicializa todas as referências de widgets como None
        self.numero_ordem_entry = None
        self.codigo_entry = None
        self.descricao_entry = None
        self.data_entry = None
        self.comprimento_entry = None
        self.largura_entry = None
        self.cortador_entry = None
        self.ajudante_entry = None
        self.composicao_entry = None
        self.obs_entry = None
        self.tree = None
        self.lotes_tree = None
        self.btn_adicionar_tecido = None
        self.tecido_cb = None
        self.cor_cb = None
        self.lbl_total_pecas = None
        self.lbl_total_folhas = None
        self.lbl_metros = None
        self.lbl_rendimento = None

        # Variáveis de controle
        self.numero_ordem = self.gerar_proximo_numero_oc()
        self.tamanhos = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]
        self.grade_disponivel = self.tamanhos.copy()
        self.lotes = {}
        self.tecido_info = {}
        self.modelos_disponiveis = []
        self.tecidos_map = {}

        # Variáveis de controle de interface
        self.total_folhas_var = ctk.StringVar(value="0")
        self.metros_utilizados_var = ctk.StringVar(value="0.00")
        self.bobinas_utilizadas_var = ctk.StringVar(value="0")
        self.total_pecas_var = ctk.StringVar(value="0")
        self.rendimento_var = ctk.StringVar(value="0.00")
        self.tecido_var = ctk.StringVar()
        self.cor_var = ctk.StringVar()
        self._i18n_refs = {}

        # Configuração inicial
        self._conectar_banco_dados()
        self.carregar_dados_iniciais()
        self.carregar_logo()
        self.setup_ui()


    def _get_idioma_atual(self):
        return getattr(self.sistema, "idioma_atual", "pt_BR")

    def _tr(self, chave, **kwargs):
        textos = {
            "pt_BR": {
                "title": "CADASTRO DE ORDEM DE CORTE", "logo_missing": "[LOGO NÃO CARREGADA]", "order_no": "Nº ORDEM:",
                "code": "CÓDIGO:", "description": "DESCRIÇÃO:", "model": "MODELO:", "reload": "↻",
                "length_m": "COMPRIMENTO (m):", "width_m": "LARGURA (m):", "cutter": "CORTADOR:", "assistant": "AJUDANTE:",
                "date": "DATA:", "add_fabric": "Adicionar Tecido", "remove_fabric": "Remover Tecido", "clear_table": "Limpar Tabela",
                "total_pieces": "TOTAL DE PEÇAS:", "sheets": "FOLHAS:", "meters": "METROS:", "yield": "RENDIMENTO:",
                "notes": "OBSERVAÇÕES:", "clear_all": "Limpar Tudo", "save_order": "Salvar Ordem",
                "search_fabric": "Buscar Tecido (código/nome/composição):", "search_fabric_dialog": "Buscar tecido:",
                "available_color": "Cor Disponível:", "bobbins": "Bobinas:", "bobbins_col": "BOBINAS",
                "sheets_short": "Folhas:", "sheets_col": "FOLHAS", "qty_by_size": "Quantidades por Tamanho:",
                "fabric": "TECIDO", "color": "COR", "composition": "COMPOSIÇÃO", "number": "NÚMERO",
                "total_pieces_col": "TOTAL PEÇAS", "total_lot": "TOTAL LOTE",
                "select_model": "select_model", "select_color": "Selecione a cor", "loading_colors": "Carregando cores...",
                "no_fabric_selected": "Nenhum tecido selecionado", "no_color_found": "Nenhuma cor encontrada",
                "no_models_found": "Nenhum modelo encontrado", "load_models_fail": "Falha ao carregar modelos:\n{erro}",
                "initialization_problem": "Problema de inicialização", "diagnostic": "Diagnóstico", "all_widgets_initialized": "Todos os widgets foram inicializados",
                "select_valid_model_before_add": "Selecione um modelo válido antes de adicionar tecido.",
                "select_fabric_remove": "Selecione um tecido para remover.",
                "confirm": "Confirmar", "cancel": "Cancelar", "search": "Buscar",
                "warn": "Aviso", "error": "Erro", "confirm_title": "Confirmar", "table_not_found": "Tabela não encontrada",
                "db_error": "Erro no Banco de Dados", "fill_order_before_save": "Informe o Nº ORDEM antes de salvar.",
                "cut_exists": "Corte já existe", "cut_exists_msg": "A Ordem de Corte {numero_ordem} já existe no sistema e não pode ser salva novamente.",
                "confirm_clear": "Deseja limpar todos os campos?", "interface_not_init": "Interface não inicializada corretamente",
                "clear_fail": "Falha ao limpar campos:\n{erro}", "save_success": "Ordem salva com sucesso!", "save_fail": "Erro ao salvar ordem de corte:\n{erro}",
            },
            "en_US": {
                "title": "CUTTING ORDER REGISTRATION", "logo_missing": "[LOGO NOT LOADED]", "order_no": "ORDER NO.:",
                "code": "CODE:", "description": "DESCRIPTION:", "model": "MODEL:", "reload": "↻",
                "length_m": "LENGTH (m):", "width_m": "WIDTH (m):", "cutter": "CUTTER:", "assistant": "ASSISTANT:",
                "date": "DATE:", "add_fabric": "Add Fabric", "remove_fabric": "Remove Fabric", "clear_table": "Clear Table",
                "total_pieces": "TOTAL PIECES:", "sheets": "SHEETS:", "meters": "METERS:", "yield": "YIELD:",
                "notes": "NOTES:", "clear_all": "Clear All", "save_order": "Save Order",
                "search_fabric": "Search Fabric (code/name/composition):", "search_fabric_dialog": "Search fabric:",
                "available_color": "Available Color:", "bobbins": "Rolls:", "bobbins_col": "ROLLS",
                "sheets_short": "Sheets:", "sheets_col": "SHEETS", "qty_by_size": "Quantities by Size:",
                "fabric": "FABRIC", "color": "COLOR", "composition": "COMPOSITION", "number": "NUMBER",
                "total_pieces_col": "TOTAL PIECES", "total_lot": "TOTAL LOT",
                "select_model": "select_model", "select_color": "Select color", "loading_colors": "Loading colors...",
                "no_fabric_selected": "No fabric selected", "no_color_found": "No color found",
                "no_models_found": "No models found", "load_models_fail": "Failed to load models:\n{erro}",
                "initialization_problem": "Initialization problem", "diagnostic": "Diagnostic", "all_widgets_initialized": "All widgets were initialized",
                "select_valid_model_before_add": "Select a valid model before adding fabric.",
                "select_fabric_remove": "Select a fabric to remove.",
                "confirm": "Confirm", "cancel": "Cancel", "search": "Search",
                "warn": "Warning", "error": "Error", "confirm_title": "Confirm", "table_not_found": "Table not found",
                "db_error": "Database Error", "fill_order_before_save": "Enter the ORDER NO. before saving.",
                "cut_exists": "Order already exists", "cut_exists_msg": "The Cutting Order {numero_ordem} already exists in the system and cannot be saved again.",
                "confirm_clear": "Do you want to clear all fields?", "interface_not_init": "Interface not initialized correctly",
                "clear_fail": "Failed to clear fields:\n{erro}", "save_success": "Order saved successfully!", "save_fail": "Error saving cutting order:\n{erro}",
            },
            "es_ES": {
                "title": "REGISTRO DE ORDEN DE CORTE", "logo_missing": "[LOGO NO CARGADO]", "order_no": "N.º ORDEN:",
                "code": "CÓDIGO:", "description": "DESCRIPCIÓN:", "model": "MODELO:", "reload": "↻",
                "length_m": "LARGO (m):", "width_m": "ANCHO (m):", "cutter": "CORTADOR:", "assistant": "AYUDANTE:",
                "date": "FECHA:", "add_fabric": "Agregar Tela", "remove_fabric": "Quitar Tela", "clear_table": "Limpiar Tabla",
                "total_pieces": "TOTAL DE PIEZAS:", "sheets": "HOJAS:", "meters": "METROS:", "yield": "RENDIMIENTO:",
                "notes": "OBSERVACIONES:", "clear_all": "Limpiar Todo", "save_order": "Guardar Orden",
                "search_fabric": "Buscar Tela (código/nombre/composición):", "search_fabric_dialog": "Buscar tela:",
                "available_color": "Color disponible:", "bobbins": "Bobinas:", "bobbins_col": "BOBINAS",
                "sheets_short": "Hojas:", "sheets_col": "HOJAS", "qty_by_size": "Cantidades por Talla:",
                "fabric": "TELA", "color": "COLOR", "composition": "COMPOSICIÓN", "number": "NÚMERO",
                "total_pieces_col": "TOTAL PIEZAS", "total_lot": "TOTAL LOTE",
                "select_model": "select_model", "select_color": "Seleccione el color", "loading_colors": "Cargando colores...",
                "no_fabric_selected": "Ninguna tela seleccionada", "no_color_found": "No se encontró color",
                "no_models_found": "No se encontraron modelos", "load_models_fail": "Error al cargar modelos:\n{erro}",
                "initialization_problem": "Problema de inicialización", "diagnostic": "Diagnóstico", "all_widgets_initialized": "Todos los widgets fueron inicializados",
                "select_valid_model_before_add": "Seleccione un modelo válido antes de agregar tela.",
                "select_fabric_remove": "Seleccione una tela para quitar.",
                "confirm": "Confirmar", "cancel": "Cancelar", "search": "Buscar",
                "warn": "Aviso", "error": "Error", "confirm_title": "Confirmar", "table_not_found": "Tabla no encontrada",
                "db_error": "Error de base de datos", "fill_order_before_save": "Informe el N.º ORDEN antes de guardar.",
                "cut_exists": "La orden ya existe", "cut_exists_msg": "La Orden de Corte {numero_ordem} ya existe en el sistema y no puede guardarse nuevamente.",
                "confirm_clear": "¿Desea limpiar todos los campos?", "interface_not_init": "Interfaz no inicializada correctamente",
                "clear_fail": "Error al limpiar campos:\n{erro}", "save_success": "¡Orden guardada con éxito!", "save_fail": "Error al guardar la orden de corte:\n{erro}",
            },
        }
        idioma = self._get_idioma_atual()
        base = textos.get(idioma, textos["pt_BR"])
        texto = base.get(chave, textos["pt_BR"].get(chave, chave))
        try:
            return texto.format(**kwargs) if kwargs else texto
        except Exception:
            return texto

    def refresh_texts(self):
        try:
            state = self.get_state()
        except Exception:
            state = None
        for child in self.winfo_children():
            child.destroy()
        self.setup_ui()
        if state:
            try:
                self.set_state(state)
            except Exception:
                pass

    def obter_cores_por_tema(self):
        """Define cores de texto dinamicamente baseado no tema atual - MESMO PADRÃO DA ENTRADA_ESTOQUE"""
        tema_atual = ctk.get_appearance_mode()

        if tema_atual == "Dark":
            self.cor_fundo = getattr(self.sistema, "cor_fundo", "#020617")
            self.cor_primaria = getattr(self.sistema, "cor_primaria", "#1f2937")
            self.cor_secundaria = getattr(self.sistema, "cor_secundaria", "#111827")
            self.cor_texto = getattr(self.sistema, "cor_texto", "#e5e7eb")
            self.cor_texto_entry = "#e5e7eb"
            self.cor_placeholder = "#888888"
            self.cor_borda = getattr(self.sistema, "cor_borda", "#273244")
            self.cor_hover = getattr(self.sistema, "cor_hover", "#334155")
        else:
            self.cor_fundo = "#ffffff"
            self.cor_primaria = "#3a7ebf"
            self.cor_secundaria = "#f0f0f0"
            self.cor_texto = "black"
            self.cor_texto_entry = "black"
            self.cor_placeholder = "#666666"
            self.cor_borda = "#cccccc"
            self.cor_hover = "#2e4a66"

    def configurar_treeview_theme(self):
        """Configura as cores da Treeview baseado no tema atual - MESMO ESTILO DA ENTRADA_ESTOQUE"""
        self.style = ttk.Style()
        self.style.theme_use('default')

        tema_atual = ctk.get_appearance_mode()

        if tema_atual == "Dark":
            cor_fundo = self.cor_secundaria
            cor_texto = self.cor_texto
            cor_campo = self.cor_secundaria
            cor_selecao = self.cor_primaria
        else:
            cor_fundo = "#f0f0f0"
            cor_texto = "black"
            cor_campo = "#f0f0f0"
            cor_selecao = self.cor_primaria

        self.style.configure("Custom.Treeview",
                             background=cor_fundo,
                             foreground=cor_texto,
                             fieldbackground=cor_campo,
                             borderwidth=0,
                             highlightthickness=0,
                             rowheight=22)

        self.style.configure("Custom.Treeview.Heading",
                             background=self.cor_primaria,
                             foreground=self.cor_texto,
                             relief="flat",
                             borderwidth=1,
                             font=('Arial', 10, 'bold'))

        self.style.map('Custom.Treeview',
                       background=[('selected', cor_selecao)],
                       foreground=[('selected', "white")])

    def _recolor_labels_frame(self, frame):
        for widget in frame.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=self.cor_texto)
            if hasattr(widget, "winfo_children"):
                self._recolor_labels_frame(widget)

    def verificar_estrutura_tabela(self):
        try:
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = current_schema()
                      AND table_name = 'estoque_tecidos'
                    LIMIT 1
                """)
                ok = cur.fetchone() is not None
            conn.close()
            if not ok:
                messagebox.showerror(self._tr("table_not_found"), "A tabela 'estoque_tecidos' não existe! Peça ao administrador do sistema para corrigir.")
                return False
            return True
        except Exception as e:
            messagebox.showerror(self._tr("db_error"), f"Falha ao verificar tabela de tecidos:\n{str(e)}")
            return False

    def _conectar_banco_dados(self):
        try:
            conn = _pg_connect()
            conn.close()
            self.conn = None
            self.cursor = None
        except Exception as e:
            messagebox.showerror(self._tr("db_error"), f"Não foi possível conectar ao banco de dados:\n{str(e)}")
            self.master.destroy()

    def get_state(self):
        state = {
            'numero_ordem': self.numero_ordem_entry.get(),
            'codigo': self.codigo_entry.get(),
            'descricao': self.descricao_entry.get(),
            'data': self.data_entry.get(),
            'comprimento': self.comprimento_entry.get(),
            'largura': self.largura_entry.get(),
            'cortador': self.cortador_entry.get(),
            'ajudante': self.ajudante_entry.get(),
            'composicao': getattr(self, "composicao_entry", None).get() if getattr(self, "composicao_entry",
                                                                                   None) else "",
            'observacoes': self.obs_entry.get(),
            'tecidos': [],
            'lotes': []
        }

        for item in self.tree.get_children():
            valores = self.tree.item(item, "values")
            state['tecidos'].append({
                'tecido': valores[0],
                'cor': valores[2],
                'bobinas': valores[6],
                'folhas': valores[8],
                'quantidades': {t: valores[10 + i] for i, t in enumerate(self.tamanhos)}
            })

        for item in self.lotes_tree.get_children():
            valores = self.lotes_tree.item(item, "values")
            state['lotes'].append({
                'lote': valores[0],
                'tecido': valores[1],
                'cor': valores[3],
                'bobinas': valores[7],
                'folhas': valores[9],
                'quantidades': {t: valores[11 + i] for i, t in enumerate(self.tamanhos)}
            })
        return state

    def set_state(self, state):
        if not state:
            return

        self.numero_ordem_entry.configure(state="normal")
        self.numero_ordem_entry.delete(0, "end")
        self.numero_ordem_entry.insert(0, state.get('numero_ordem', ''))
        self.numero_ordem_entry.configure(state="readonly")

        self.codigo_entry.delete(0, "end")
        self.codigo_entry.insert(0, state.get('codigo', ''))

        self.descricao_entry.delete(0, "end")
        self.descricao_entry.insert(0, state.get('descricao', ''))

        self.data_entry.delete(0, "end")
        self.data_entry.insert(0, state.get('data', datetime.now().strftime("%d/%m/%Y")))

        self.comprimento_entry.delete(0, "end")
        self.comprimento_entry.insert(0, state.get('comprimento', '7.35'))

        self.largura_entry.delete(0, "end")
        self.largura_entry.insert(0, state.get('largura', '1.48'))

        self.cortador_entry.delete(0, "end")
        self.cortador_entry.insert(0, state.get('cortador', ''))

        self.ajudante_entry.delete(0, "end")
        self.ajudante_entry.insert(0, state.get('ajudante', ''))

        self.obs_entry.delete(0, "end")
        self.obs_entry.insert(0, state.get('observacoes', ''))

        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self.lotes_tree.get_children():
            self.lotes_tree.delete(item)

        for tecido in state.get('tecidos', []):
            valores = [
                tecido['tecido'], "",
                tecido['cor'], "",
                tecido.get('composicao', ''), "",
                str(tecido['bobinas']), "",
                str(tecido['folhas']), ""
            ]
            for tamanho in self.tamanhos:
                valores.append(str(tecido['quantidades'].get(tamanho, 0)))
            total_pecas = sum(int(q) for q in tecido['quantidades'].values())
            valores.append(str(total_pecas))
            tag = 'evenrow' if len(self.tree.get_children()) % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=valores, tags=(tag,))

        for lote in state.get('lotes', []):
            valores = [
                lote['lote'], lote['tecido'], "", lote['cor'], "", str(lote.get('composicao', '')),
                "", str(lote['bobinas']), "", str(lote['folhas']), ""
            ]
            for tamanho in self.tamanhos:
                valores.append(str(lote['quantidades'].get(tamanho, 0)))
            total_lote = sum(int(q) for q in lote['quantidades'].values())
            valores.append(str(total_lote))
            tag = 'evenrow' if len(self.lotes_tree.get_children()) % 2 == 0 else 'oddrow'
            self.lotes_tree.insert("", "end", values=valores, tags=(tag,))

        self.calcular_totais()

    def limpar_cache_pagina(self):
        pass

    def carregar_dados_iniciais(self):
        self.carregar_tecidos()
        self.carregar_modelos()

        try:
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT grade_disponivel
                    FROM cadastro_modelos_cabecalho
                    WHERE grade_disponivel IS NOT NULL AND grade_disponivel <> ''
                    LIMIT 1
                    """
                )
                resultado = cur.fetchone()
            conn.close()
            if resultado and resultado[0]:
                self.grade_disponivel = [t.strip().upper() for t in str(resultado[0]).split(",") if t.strip()]
            else:
                self.grade_disponivel = self.tamanhos.copy()
        except Exception as e:
            print(f"Erro ao carregar grade inicial: {str(e)}")
            self.grade_disponivel = self.tamanhos.copy()

    def carregar_logo(self):
        try:
            possiveis_logos = [
                "logo.png", "logo.jpg",
                os.path.join(os.path.dirname(__file__), "logo.png"),
                os.path.join(os.path.dirname(__file__), "imgs", "logo.png"),
                os.path.join(os.path.dirname(__file__), "assets", "logo.png")
            ]

            for logo_path in possiveis_logos:
                try:
                    if os.path.exists(logo_path):
                        self.logo_image = ctk.CTkImage(
                            light_image=Image.open(logo_path),
                            size=(150, 50))
                        return True
                except Exception as e:
                    print(f"Erro ao carregar {logo_path}: {str(e)}")
                    continue

            self.logo_image = None
            return False
        except Exception as e:
            print(f"Erro crítico ao carregar logo: {str(e)}")
            self.logo_image = None
            return False

    def gerar_proximo_numero_oc(self):
        try:
            conn = _pg_connect()
            with conn.cursor() as cur:
                cur.execute("SELECT numero_ordem FROM cadastro_de_corte ORDER BY id DESC LIMIT 1")
                row = cur.fetchone()
            conn.close()

            if row and row[0] and str(row[0]).startswith("OC"):
                numero = int(str(row[0])[2:]) + 1
            else:
                numero = 1
            return f"OC{numero:04d}"
        except Exception as e:
            print("Erro ao gerar número da ordem:", e)
            return "OC0001"

    def setup_ui(self):
        """Configuração completa da interface gráfica com MESMO ESTILO DA ENTRADA_ESTOQUE (compacta e sem erros de aspas)."""
        # Atualiza cores baseado no tema atual
        self.obter_cores_por_tema()

        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # =========================
        # CABEÇALHO (compacto)
        # =========================
        header_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        header_frame.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            header_frame,
            text=self._tr("title"),
            font=("Arial", 18, "bold"),
            text_color=self.cor_texto
        ).pack(side="left", padx=10)

        # Logo
        if hasattr(self, "logo_image") and self.logo_image:
            ctk.CTkLabel(header_frame, image=self.logo_image, text="").pack(side="right", padx=10)
        else:
            self._i18n_refs["logo_missing"] = ctk.CTkLabel(header_frame, text=self._tr("logo_missing"), text_color="red")
            self._i18n_refs["logo_missing"].pack(side="right", padx=10)

        # =========================
        # INFORMAÇÕES BÁSICAS (compacto)
        # =========================
        info_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        info_frame.pack(fill="x", pady=4)

        # Linha 1: Nº Ordem
        ordem_frame = ctk.CTkFrame(info_frame, fg_color=self.cor_fundo)
        ordem_frame.pack(fill="x", pady=1)

        self._i18n_refs["order_no"] = ctk.CTkLabel(ordem_frame, text=self._tr("order_no"), width=80, anchor="e", text_color=self.cor_texto)
        self._i18n_refs["order_no"].pack(side="left", padx=5)

        self.numero_ordem_entry = ctk.CTkEntry(
            ordem_frame,
            width=150,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.numero_ordem_entry.pack(side="left", padx=5)
        self.numero_ordem_entry.insert(0, getattr(self, "numero_ordem", ""))
        self.numero_ordem_entry.configure(state="readonly")

        # Linha 2: Código + Descrição
        codigo_frame = ctk.CTkFrame(info_frame, fg_color=self.cor_fundo)
        codigo_frame.pack(fill="x", pady=1)

        self._i18n_refs["code"] = ctk.CTkLabel(codigo_frame, text=self._tr("code"), width=80, anchor="e", text_color=self.cor_texto)
        self._i18n_refs["code"].pack(side="left", padx=5)

        self.codigo_entry = ctk.CTkEntry(
            codigo_frame,
            width=150,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.codigo_entry.pack(side="left", padx=5)
        self.codigo_entry.bind("<FocusOut>", self.buscar_descricao_por_codigo)
        self.codigo_entry.bind("<Return>", self.buscar_descricao_por_codigo)

        self._i18n_refs["description"] = ctk.CTkLabel(codigo_frame, text=self._tr("description"), width=80, anchor="e", text_color=self.cor_texto)
        self._i18n_refs["description"].pack(side="left", padx=5)

        self.descricao_entry = ctk.CTkEntry(
            codigo_frame,
            width=450,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.descricao_entry.pack(side="left", padx=5)

        # Linha 3: Modelo + recarregar
        sel_frame = ctk.CTkFrame(info_frame, fg_color=self.cor_fundo)
        sel_frame.pack(fill="x", pady=1)

        self._i18n_refs["model"] = ctk.CTkLabel(sel_frame, text=self._tr("model"), width=120, anchor="e", text_color=self.cor_texto)
        self._i18n_refs["model"].pack(side="left", padx=5)

        self.modelo_ocf_cb = ctk.CTkComboBox(
            sel_frame,
            values=[],
            width=350,
            command=self._on_modelo_ocf_selected,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover
        )
        self.modelo_ocf_cb.pack(side="left", padx=5)
        self.modelo_ocf_cb.set(self._tr("select_model"))

        ctk.CTkButton(
            sel_frame,
            text=self._tr("reload"),
            width=40,
            command=self._recarregar_modelos_ocf,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=5)

        self._recarregar_modelos_ocf()

        # Linha 4: Dimensões
        dimensoes_frame = ctk.CTkFrame(info_frame, fg_color=self.cor_fundo)
        dimensoes_frame.pack(fill="x", pady=1)

        self._i18n_refs["length_m"] = ctk.CTkLabel(dimensoes_frame, text=self._tr("length_m"), width=120, anchor="e", text_color=self.cor_texto)
        self._i18n_refs["length_m"].pack(side="left", padx=5)

        self.comprimento_entry = ctk.CTkEntry(
            dimensoes_frame,
            width=100,
            placeholder_text="ex: 7.35",
            validate="key",
            validatecommand=(self.register(self._validar_numero), "%P"),
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.comprimento_entry.pack(side="left", padx=5)
        self.comprimento_entry.insert(0, "7.35")

        self._i18n_refs["width_m"] = ctk.CTkLabel(dimensoes_frame, text=self._tr("width_m"), width=100, anchor="e", text_color=self.cor_texto)
        self._i18n_refs["width_m"].pack(side="left", padx=5)

        self.largura_entry = ctk.CTkEntry(
            dimensoes_frame,
            width=100,
            placeholder_text="ex: 1.48",
            validate="key",
            validatecommand=(self.register(self._validar_numero), "%P"),
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.largura_entry.pack(side="left", padx=5)
        self.largura_entry.insert(0, "1.48")

        # Linha 5: Pessoal
        pessoal_frame = ctk.CTkFrame(info_frame, fg_color=self.cor_fundo)
        pessoal_frame.pack(fill="x", pady=1)

        self._i18n_refs["cutter"] = ctk.CTkLabel(pessoal_frame, text=self._tr("cutter"), width=80, anchor="e", text_color=self.cor_texto)
        self._i18n_refs["cutter"].pack(side="left", padx=5)

        self.cortador_entry = ctk.CTkEntry(
            pessoal_frame,
            width=260,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.cortador_entry.pack(side="left", padx=5)

        self._i18n_refs["assistant"] = ctk.CTkLabel(pessoal_frame, text=self._tr("assistant"), width=80, anchor="e", text_color=self.cor_texto)
        self._i18n_refs["assistant"].pack(side="left", padx=5)

        self.ajudante_entry = ctk.CTkEntry(
            pessoal_frame,
            width=260,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.ajudante_entry.pack(side="left", padx=5)

        # Linha 6: Data
        data_frame = ctk.CTkFrame(info_frame, fg_color=self.cor_fundo)
        data_frame.pack(fill="x", pady=1)

        self._i18n_refs["date"] = ctk.CTkLabel(data_frame, text=self._tr("date"), width=80, anchor="e", text_color=self.cor_texto)
        self._i18n_refs["date"].pack(side="left", padx=5)

        self.data_entry = ctk.CTkEntry(
            data_frame,
            width=120,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.data_entry.pack(side="left", padx=5)
        self.data_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))

        # =========================
        # TABELA DE TECIDOS
        # =========================
        table_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        table_frame.pack(fill="both", expand=True, pady=8)

        # Tema da Treeview
        self.configurar_treeview_theme()

        columns = ["tecido", "col1", "cor", "col2", "composicao", "col3", "BOBINAS", "col4", "folhas",
                   "col5"] + self.tamanhos + ["total"]
        headers = [self._tr("fabric"), "", self._tr("color"), "", self._tr("composition"), "", self._tr("bobbins_col"), "", self._tr("sheets_col"), ""] + self.tamanhos + [
            self._tr("total_pieces_col")]

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=4, style="Custom.Treeview")

        for col, header in zip(columns, headers):
            self.tree.heading(col, text=header, anchor="center")
            # largura inicial (vai ser recalculada pela responsiva)
            if header in self.tamanhos or header in ["BOBINAS", "FOLHAS", "TOTAL PEÇAS"]:
                self.tree.column(col, width=60, anchor="center")
            elif header in ["TECIDO", "COR", "COMPOSIÇÃO"]:
                # alinhamento inicial (será centralizado pela responsiva)
                self.tree.column(col, width=120, anchor="center")
            else:
                self.tree.column(col, width=5, stretch=False, anchor="center")

        self.tree.column("total", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(fill="both", expand=True)

        # Auto-ajuste: colunas cabem no frame (sem scroll horizontal) + centraliza
        self._configurar_treeview_responsiva_generic(
            container=table_frame,
            tree=self.tree,
            scrollbar=scrollbar,
            columns=columns,
            min_widths={
                "tecido": self._minwidth_por_header(self.tree, "tecido", 130),
                "cor": self._minwidth_por_header(self.tree, "cor", 95),
                "composicao": self._minwidth_por_header(self.tree, "composicao", 130),
                "BOBINAS": self._minwidth_por_header(self.tree, "BOBINAS", 80),
                "folhas": self._minwidth_por_header(self.tree, "folhas", 80),
                "total": self._minwidth_por_header(self.tree, "total", 90),
                "col1": 6, "col2": 6, "col3": 6, "col4": 6, "col5": 6,
                "PP": self._minwidth_por_header(self.tree, "PP", 48), "P": self._minwidth_por_header(self.tree, "P", 48),
                "M": self._minwidth_por_header(self.tree, "M", 48), "G": self._minwidth_por_header(self.tree, "G", 48),
                "GG": self._minwidth_por_header(self.tree, "GG", 52), "G1": self._minwidth_por_header(self.tree, "G1", 52),
                "G2": self._minwidth_por_header(self.tree, "G2", 52), "G3": self._minwidth_por_header(self.tree, "G3", 52)
            },
            weights={
                "tecido": 4.5, "cor": 2.2, "composicao": 3.2, "BOBINAS": 1.3, "folhas": 1.3, "total": 1.6,
                "col1": 0.1, "col2": 0.1, "col3": 0.1, "col4": 0.1, "col5": 0.1
            }
        )

        # Cores alternadas
        if ctk.get_appearance_mode() == "Dark":
            cor_linha_par = self.cor_fundo
            cor_linha_impar = self.cor_secundaria
        else:
            cor_linha_par = "#ffffff"
            cor_linha_impar = "#f0f0f0"

        self.tree.tag_configure("oddrow", background=cor_linha_impar)
        self.tree.tag_configure("evenrow", background=cor_linha_par)

        # =========================
        # BOTÕES DE AÇÃO
        # =========================
        button_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        button_frame.pack(fill="x", pady=5)

        self.btn_adicionar_tecido = ctk.CTkButton(
            button_frame,
            text=self._tr("add_fabric"),
            command=self.adicionar_tecido,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            font=("Arial", 12)
        )
        self.btn_adicionar_tecido.pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text=self._tr("remove_fabric"),
            command=self.remover_tecido,
            fg_color=self.cor_secundaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            font=("Arial", 12)
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text=self._tr("clear_table"),
            command=self.limpar_tabela,
            fg_color=self.cor_secundaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            font=("Arial", 12)
        ).pack(side="left", padx=5)

        # =========================
        # TABELA DE LOTES
        # =========================
        lotes_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        lotes_frame.pack(fill="both", expand=True, pady=8)

        lote_columns = ["numero", "tecido", "col1", "cor", "col2", "composicao", "col3", "bobinas", "col4", "folhas",
                        "col5"] + self.tamanhos + ["total"]
        lote_headers = [self._tr("number"), self._tr("fabric"), "", self._tr("color"), "", self._tr("composition"), "", self._tr("bobbins_col"), "", self._tr("sheets_col"),
                        ""] + self.tamanhos + [self._tr("total_lot")]

        self.lotes_tree = ttk.Treeview(lotes_frame, columns=lote_columns, show="headings", height=4,
                                       style="Custom.Treeview")

        for col, header in zip(lote_columns, lote_headers):
            self.lotes_tree.heading(col, text=header, anchor="center")
            if header == "NUMERO":
                self.lotes_tree.column(col, width=80, anchor="center")
            elif header == "TECIDO":
                self.lotes_tree.column(col, width=150, anchor="center")
            elif header == "COR":
                self.lotes_tree.column(col, width=100, anchor="center")
            elif header == "COMPOSIÇÃO":
                self.lotes_tree.column(col, width=150, anchor="center")
            elif header == "BOBINAS":
                self.lotes_tree.column(col, width=80, anchor="center")
            elif header == "FOLHAS":
                self.lotes_tree.column(col, width=80, anchor="center")
            elif header in self.tamanhos:
                self.lotes_tree.column(col, width=60, anchor="center")
            elif header == "TOTAL LOTE":
                self.lotes_tree.column(col, width=90, anchor="center")
            else:
                self.lotes_tree.column(col, width=5, stretch=False, anchor="center")

        scrollbar_lotes = ttk.Scrollbar(lotes_frame, orient="vertical", command=self.lotes_tree.yview)
        scrollbar_lotes.pack(side="right", fill="y")
        self.lotes_tree.configure(yscrollcommand=scrollbar_lotes.set)
        self.lotes_tree.pack(fill="both", expand=True)

        # Auto-ajuste lotes (sem scroll horizontal) + centraliza
        self._configurar_treeview_responsiva_generic(
            container=lotes_frame,
            tree=self.lotes_tree,
            scrollbar=scrollbar_lotes,
            columns=lote_columns,
            min_widths={
                "numero": self._minwidth_por_header(self.lotes_tree, "numero", 80),
                "tecido": self._minwidth_por_header(self.lotes_tree, "tecido", 130),
                "cor": self._minwidth_por_header(self.lotes_tree, "cor", 95),
                "composicao": self._minwidth_por_header(self.lotes_tree, "composicao", 130),
                "bobinas": self._minwidth_por_header(self.lotes_tree, "bobinas", 80),
                "folhas": self._minwidth_por_header(self.lotes_tree, "folhas", 80),
                "total": self._minwidth_por_header(self.lotes_tree, "total", 90),
                "col1": 6, "col2": 6, "col3": 6, "col4": 6, "col5": 6,
                "PP": self._minwidth_por_header(self.lotes_tree, "PP", 48), "P": self._minwidth_por_header(self.lotes_tree, "P", 48),
                "M": self._minwidth_por_header(self.lotes_tree, "M", 48), "G": self._minwidth_por_header(self.lotes_tree, "G", 48),
                "GG": self._minwidth_por_header(self.lotes_tree, "GG", 52), "G1": self._minwidth_por_header(self.lotes_tree, "G1", 52),
                "G2": self._minwidth_por_header(self.lotes_tree, "G2", 52), "G3": self._minwidth_por_header(self.lotes_tree, "G3", 52)
            },
            weights={
                "numero": 1.4, "tecido": 4.0, "cor": 2.2, "composicao": 3.0, "bobinas": 1.2, "folhas": 1.2,
                "total": 1.6,
                "col1": 0.1, "col2": 0.1, "col3": 0.1, "col4": 0.1, "col5": 0.1
            }
        )

        self.lotes_tree.tag_configure("oddrow", background=cor_linha_impar)
        self.lotes_tree.tag_configure("evenrow", background=cor_linha_par)

        # =========================
        # RODAPÉ COM TOTAIS
        # =========================
        footer_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        footer_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            footer_frame,
            text=self._tr("total_pieces"),
            width=120,
            anchor="e",
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        ).pack(side="left", padx=5)

        self.lbl_total_pecas = ctk.CTkLabel(
            footer_frame,
            textvariable=self.total_pecas_var,
            width=80,
            anchor="w",
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        )
        self.lbl_total_pecas.pack(side="left", padx=5)

        ctk.CTkLabel(
            footer_frame,
            text=self._tr("sheets"),
            width=80,
            anchor="e",
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        ).pack(side="left", padx=5)

        self.lbl_total_folhas = ctk.CTkLabel(
            footer_frame,
            textvariable=self.total_folhas_var,
            width=80,
            anchor="w",
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        )
        self.lbl_total_folhas.pack(side="left", padx=5)

        ctk.CTkLabel(
            footer_frame,
            text=self._tr("meters"),
            width=80,
            anchor="e",
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        ).pack(side="left", padx=5)

        self.lbl_metros = ctk.CTkLabel(
            footer_frame,
            textvariable=self.metros_utilizados_var,
            width=80,
            anchor="w",
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        )
        self.lbl_metros.pack(side="left", padx=5)

        ctk.CTkLabel(
            footer_frame,
            text=self._tr("yield"),
            width=100,
            anchor="e",
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        ).pack(side="left", padx=5)

        self.lbl_rendimento = ctk.CTkLabel(
            footer_frame,
            textvariable=self.rendimento_var,
            width=80,
            anchor="w",
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        )
        self.lbl_rendimento.pack(side="left", padx=5)

        # =========================
        # OBSERVAÇÕES
        # =========================
        obs_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        obs_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(obs_frame, text=self._tr("notes"), width=100, anchor="e", text_color=self.cor_texto).pack(side="left",
                                                                                                            padx=5)

        self.obs_entry = ctk.CTkEntry(
            obs_frame,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry
        )
        self.obs_entry.pack(side="left", fill="x", expand=True, padx=5)

        # =========================
        # BOTÕES FINAIS
        # =========================
        action_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        action_frame.pack(fill="x", pady=10)

        ctk.CTkButton(
            action_frame,
            text=self._tr("clear_all"),
            command=self.limpar_tudo,
            fg_color=self.cor_secundaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            font=("Arial", 12)
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            action_frame,
            text=self._tr("save_order"),
            command=self.salvar_ordem,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            font=("Arial", 14, "bold")
        ).pack(side="right", padx=5)

        # =========================
        # EVENTOS
        # =========================
        self.comprimento_entry.bind("<KeyRelease>", self.calcular_totais)
        self.largura_entry.bind("<KeyRelease>", self.calcular_totais)

        self.tree.bind("<<TreeviewSelect>>", self.calcular_totais)
        self.tree.bind("<ButtonRelease-1>", self.calcular_totais)

        self.lotes_tree.bind("<ButtonRelease-1>", self.calcular_totais)

        if hasattr(self, "tecido_cb") and self.tecido_cb is not None:
            self.tecido_cb.bind("<<ComboboxSelected>>", self._on_tecido_selected)

        if hasattr(self, "cor_cb") and self.cor_cb is not None:
            self.cor_cb.bind("<<ComboboxSelected>>", self._atualizar_composicao)

        # Se você usa esse helper no projeto, mantém:
        if "padronizar_treeviews_container" in globals():
            padronizar_treeviews_container(self)

        self.after(100, self.carregar_tecidos)
        self.after(100, self.verificar_inicializacao_widgets)

    def _medir_texto_treeview(self, texto, bold=False):
        try:
            familia = "Arial"
            tamanho = 10
            peso = "bold" if bold else "normal"
            fonte = tkfont.Font(family=familia, size=tamanho, weight=peso)
            return int(fonte.measure(str(texto or "")))
        except Exception:
            return int(len(str(texto or "")) * (9 if bold else 8))

    def _minwidth_por_header(self, tree, col, fallback=40):
        try:
            header_text = tree.heading(col).get("text", "")
        except Exception:
            header_text = ""
        largura_texto = self._medir_texto_treeview(header_text, bold=True)
        return max(int(fallback), largura_texto + 28)

    def _configurar_treeview_responsiva_generic(
            self,
            container,
            tree,
            scrollbar,
            columns,
            min_widths=None,
            weights=None,
            debounce_ms=80,
    ):
        """
        Configura auto-ajuste de colunas para Treeview caber no container (sem scroll horizontal).
        - container: frame onde a tree está (ex: table_frame)
        - tree: ttk.Treeview
        - scrollbar: ttk.Scrollbar vertical
        - columns: lista de colunas (mesma usada no Treeview)
        - min_widths: dict {col: minwidth}
        - weights: dict {col: peso} (quem deve ganhar mais largura)
        """
        self._tv_auto = getattr(self, "_tv_auto", {})
        key = id(tree)

        self._tv_auto[key] = {
            "container": container,
            "tree": tree,
            "scrollbar": scrollbar,
            "columns": list(columns),
            "min_widths": dict(min_widths or {}),
            "weights": dict(weights or {}),
            "after_id": None,
            "debounce_ms": int(debounce_ms),
        }

        # garante alinhamento central nos cabeçalhos e colunas por padrão
        for c in columns:
            tree.heading(c, anchor="center")
            tree.column(c, anchor="center")

        def _schedule(_evt=None):
            st = self._tv_auto.get(key)
            if not st:
                return
            if st["after_id"]:
                try:
                    self.after_cancel(st["after_id"])
                except Exception:
                    pass
            st["after_id"] = self.after(st["debounce_ms"], lambda: self._ajustar_colunas_treeview_generic(tree))

        container.bind("<Configure>", _schedule)
        tree.bind("<Configure>", _schedule)

        # primeiro ajuste
        self.after(60, lambda: self._ajustar_colunas_treeview_generic(tree))

    def _ajustar_colunas_treeview_generic(self, tree):
        """Recalcula larguras para caber no container (sem scroll horizontal)."""
        st = getattr(self, "_tv_auto", {}).get(id(tree))
        if not st:
            return

        container = st["container"]
        scrollbar = st["scrollbar"]
        columns = st["columns"]
        min_widths = st["min_widths"]
        weights = st["weights"]

        try:
            cw = container.winfo_width()
            if cw <= 10:
                return

            # reserva espaço da scrollbar vertical
            sbw = 0
            try:
                sbw = max(scrollbar.winfo_width(), scrollbar.winfo_reqwidth(), 18)
            except Exception:
                sbw = 18

            avail = cw - sbw - 8
            if avail <= 50:
                return

            # pesos padrão = 1
            wsum = sum(weights.get(c, 1.0) for c in columns) or 1.0

            widths = {}
            for c in columns:
                min_w = int(min_widths.get(c, 40))
                w = int(avail * (weights.get(c, 1.0) / wsum))
                widths[c] = max(min_w, w)

            used = sum(widths.values())
            if used > avail:
                excesso = used - avail
                redutiveis = [c for c in columns if widths[c] > int(min_widths.get(c, 40))]
                while excesso > 0 and redutiveis:
                    mudou = False
                    for c in redutiveis:
                        min_w = int(min_widths.get(c, 40))
                        if widths[c] > min_w and excesso > 0:
                            widths[c] -= 1
                            excesso -= 1
                            mudou = True
                    if not mudou:
                        break
                    redutiveis = [c for c in columns if widths[c] > int(min_widths.get(c, 40))]
            else:
                diff = avail - used
                if diff != 0:
                    alvo = None
                    maior = -1
                    for c in columns:
                        p = weights.get(c, 1.0)
                        if p > maior:
                            maior = p
                            alvo = c
                    alvo = alvo or columns[0]
                    widths[alvo] = max(int(min_widths.get(alvo, 40)), widths[alvo] + diff)

            # aplica
            for c in columns:
                tree.heading(c, anchor="center")
                tree.column(
                    c,
                    width=int(widths[c]),
                    minwidth=int(min_widths.get(c, 40)),
                    anchor="center",
                    stretch=False
                )
        except Exception:
            pass

    def _validar_numero(self, valor):
        if valor == "":
            return True
        try:
            float(valor)
            return True
        except ValueError:
            return False

    def diagnosticar_widgets(self):
        widgets = {
            'numero_ordem_entry': self.numero_ordem_entry,
            'codigo_entry': self.codigo_entry,
            'descricao_entry': self.descricao_entry,
            'data_entry': self.data_entry,
            'comprimento_entry': self.comprimento_entry,
            'largura_entry': self.largura_entry,
            'cortador_entry': self.cortador_entry,
            'ajudante_entry': self.ajudante_entry,
            'composicao_entry': self.composicao_entry,
            'obs_entry': self.obs_entry,
            'tree': self.tree,
            'lotes_tree': self.lotes_tree
        }
        problemas = [nome for nome, widget in widgets.items() if widget is None]

        if problemas:
            message = "Widgets não inicializados:\n- " + "\n- ".join(problemas)
            messagebox.showerror(self._tr("initialization_problem"), message)
        else:
            messagebox.showinfo(self._tr("diagnostic"), self._tr("all_widgets_initialized"))

    def verificar_inicializacao_widgets(self):
        widgets_essenciais = [
            self.numero_ordem_entry, self.codigo_entry, self.descricao_entry,
            self.data_entry, self.comprimento_entry, self.largura_entry,
            self.cortador_entry, self.ajudante_entry, self.obs_entry,
            self.tree, self.lotes_tree
        ]

        for widget in widgets_essenciais:
            if widget is None:
                print(f"Widget não inicializado: {widget}")

    def _cols_tabela(self, tabela: str) -> set:
        try:
            conn = _pg_connect()
            with conn.cursor() as c:
                c.execute("""
                       SELECT column_name
                       FROM information_schema.columns
                       WHERE table_schema = current_schema()
                         AND table_name = %s
                   """, (tabela,))
                return {r[0].lower() for r in c.fetchall()}
        except Exception:
            return set()
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def carregar_modelos(self):
        try:
            conn = _pg_connect()
            with conn.cursor() as cursor:
                cursor.execute("""
                       SELECT id, codigo, descricao, colecao, tamanho_base 
                       FROM cadastro_modelos_cabecalho
                   """)
                self.modelos_disponiveis = cursor.fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror(self._tr("error"), self._tr("load_models_fail", erro=str(e)))
            self.modelos_disponiveis = []

    def _formatar_metros(self, valor) -> str:
        try:
            if valor is None or (isinstance(valor, str) and not valor.strip()):
                return "0"
            from decimal import Decimal
            dec = Decimal(str(valor))
            if dec == dec.to_integral():
                inteiro = int(dec)
                return f"{inteiro:,}".replace(",", ".")
            parte_int = int(dec)
            parte_frac = abs(dec - parte_int)
            int_str = f"{parte_int:,}".replace(",", ".")
            frac_str = f"{parte_frac:.3f}"[2:]
            frac_str = frac_str.rstrip('0')
            if not frac_str:
                return int_str
            return f"{int_str},{frac_str}"
        except Exception:
            try:
                num = float(valor)
            except Exception:
                return str(valor)
            return f"{num:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    def carregar_tecidos(self):
        try:
            cols = self._cols_tabela('estoque_tecidos')

            tem_composicao = 'composicao' in cols
            tem_metros = 'metros' in cols
            tem_kilos = 'kilos' in cols

            select_parts = [
                "id", "codigo", "descricao", "cor",
                ("COALESCE(composicao, 'Não informado') AS composicao" if tem_composicao
                 else "'Não informado'::text AS composicao"),
                ("COALESCE(metros, 0) AS metros" if tem_metros
                 else "0::numeric AS metros"),
                ("COALESCE(kilos, 0) AS kilos" if tem_kilos
                 else "0::numeric AS kilos"),
            ]
            sql = f"""
                   SELECT {', '.join(select_parts)}
                   FROM estoque_tecidos
                   ORDER BY descricao, cor
               """

            conn = _pg_connect()
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()

            self.tecido_info = {}
            self.tecidos_map = {}

            for row in rows:
                tecido = {
                    'id': row[0],
                    'codigo': row[1],
                    'descricao': row[2],
                    'cor': row[3],
                    'composicao': row[4],
                    'metros': float(row[5]) if row[5] is not None else 0.0,
                    'kilos': float(row[6]) if row[6] is not None else 0.0
                }

                self.tecido_info.setdefault(tecido['descricao'], []).append(tecido)

                chave_completa = f"{tecido['codigo']} - {tecido['descricao']} ({tecido['cor']})"
                self.tecidos_map[chave_completa] = tecido
                self.tecidos_map[tecido['codigo']] = tecido

        except Exception as e:
            messagebox.showerror("Erro no Banco de Dados", f"Falha ao carregar tecidos:\n{str(e)}")

    def _carregar_cores_tecido(self, descricao_tecido):
        try:
            if not descricao_tecido or not hasattr(self, 'cor_cb') or self.cor_cb is None:
                return

            cols = self._cols_tabela('estoque_tecidos')
            tem_metros = 'metros' in cols

            conn = _pg_connect()
            with conn.cursor() as cursor:
                if tem_metros:
                    cursor.execute("""
                           SELECT DISTINCT cor, metros
                           FROM estoque_tecidos
                           WHERE descricao = %s
                           ORDER BY cor
                       """, (descricao_tecido,))
                else:
                    cursor.execute("""
                           SELECT DISTINCT cor, NULL::numeric AS metros
                           FROM estoque_tecidos
                           WHERE descricao = %s
                           ORDER BY cor
                       """, (descricao_tecido,))

                cores = []
                for cor, metros in cursor.fetchall():
                    metros = float(metros) if metros is not None else 0.0
                    if metros <= 0:
                        status = "(ZERADO)"
                    else:
                        metros_fmt = self._formatar_metros(metros)
                        status = f"({metros_fmt}m)"
                    cores.append(f"{cor} {status}")

            if self.cor_cb is not None:
                self.cor_cb.configure(values=cores)
                if cores:
                    self.cor_cb.set(cores[0])
                    self._atualizar_composicao()
        except Exception:
            pass

    def _carregar_cores_por_codigo(self, codigo, combobox_cor, cor_atual=None, tecido_tree=None, descricao=None):
        try:
            codigo_str = str(codigo).strip()

            cols = self._cols_tabela('estoque_tecidos')
            tem_metros = 'metros' in cols

            conn = _pg_connect()
            with conn.cursor() as cursor:
                if tem_metros:
                    cursor.execute("""
                           SELECT DISTINCT cor, metros
                           FROM estoque_tecidos
                           WHERE codigo = %s
                           ORDER BY cor
                       """, (codigo_str,))
                else:
                    cursor.execute("""
                           SELECT DISTINCT cor, NULL::numeric AS metros
                           FROM estoque_tecidos
                           WHERE codigo = %s
                           ORDER BY cor
                       """, (codigo_str,))

                cores_disponiveis = []
                for cor, metros in cursor.fetchall():
                    metros = float(metros) if metros is not None else 0.0
                    if metros <= 0:
                        status = "(ZERADO)"
                    else:
                        metros_fmt = self._formatar_metros(metros)
                        status = f"({metros_fmt}m)"
                    cores_disponiveis.append(f"{cor} {status}")

            # fallback por descrição quando o código não retornar nada
            if not cores_disponiveis and descricao:
                with conn.cursor() as cursor:
                    if tem_metros:
                        cursor.execute(
                            """
                                SELECT DISTINCT cor, metros
                                FROM estoque_tecidos
                                WHERE descricao = %s
                                ORDER BY cor
                            """,
                            (descricao.strip(),),
                        )
                    else:
                        cursor.execute(
                            """
                                SELECT DISTINCT cor, NULL::numeric AS metros
                                FROM estoque_tecidos
                                WHERE descricao = %s
                                ORDER BY cor
                            """,
                            (descricao.strip(),),
                        )

                    for cor, metros in cursor.fetchall():
                        metros = float(metros) if metros is not None else 0.0
                        if metros <= 0:
                            status = "(ZERADO)"
                        else:
                            metros_fmt = self._formatar_metros(metros)
                            status = f"({metros_fmt}m)"
                        cores_disponiveis.append(f"{cor} {status}")

            # Fallback: se o banco não retornar nada, usa as cores já exibidas na TreeView
            if not cores_disponiveis and tecido_tree is not None:
                try:
                    cores_tree = set()
                    for iid in tecido_tree.get_children():
                        valores = tecido_tree.item(iid, "values") or []
                        if len(valores) > 3 and str(valores[1]).strip() == codigo_str:
                            cores_tree.add(str(valores[3]).strip())

                    for cor_tree in sorted(cores_tree):
                        cores_disponiveis.append(f"{cor_tree} (disponível)")
                except Exception:
                    pass

            combobox_cor.configure(values=cores_disponiveis)

            if not cores_disponiveis:
                combobox_cor.set(self._tr("no_color_found"))
                return False

            selecionada = None
            if cor_atual:
                cor_atual = str(cor_atual).strip().lower()
                for cor in cores_disponiveis:
                    if cor.lower().startswith(f"{cor_atual} "):
                        selecionada = cor
                        break

            combobox_cor.set(selecionada or cores_disponiveis[0])
            return True

        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Erro no Banco de Dados",
                                 f"Falha ao carregar cores:\n{str(e)}")
            return False

    def _atualizar_composicao(self):
        try:
            if not (hasattr(self, 'tecido_var') and hasattr(self, 'cor_var') and hasattr(self,
                                                                                         'composicao_entry') and self.composicao_entry):
                return
            tecido = self.tecido_var.get()
            cor_completa = self.cor_var.get()
            if not tecido or not cor_completa:
                return
            cor = cor_completa.split(' (')[0].strip()
            tecido_info = self.tecidos_map.get(tecido)
            if not tecido_info:
                return
            conn = _pg_connect()
            with conn.cursor() as cursor:
                cursor.execute("""
                       SELECT composicao
                       FROM estoque_tecidos
                       WHERE descricao = %s AND cor = %s
                       LIMIT 1
                   """, (tecido_info['descricao'], cor))
                resultado = cursor.fetchone()
            self.composicao_entry.configure(state="normal")
            self.composicao_entry.delete(0, "end")
            self.composicao_entry.insert(0, resultado[0] if resultado and resultado[0] else "Composição não informada")
            self.composicao_entry.configure(state="readonly")
        except Exception:
            pass

    def _on_tecido_selected(self, event=None):
        try:
            if not hasattr(self, 'tecido_var') or not hasattr(self, 'cor_cb'):
                return
            tecido = self.tecido_var.get()
            if not tecido:
                return
            if not hasattr(self, 'tecido_cb') or self.tecido_cb is None:
                return
            tecido_info = self.tecidos_map.get(tecido)
            if not tecido_info:
                return
            self._carregar_cores_tecido(tecido_info.get('descricao', tecido))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao processar seleção de tecido:\n{str(e)}")

    def adicionar_tecido(self):
        if not self.grade_disponivel:
            messagebox.showwarning(self._tr("warn"),
                                   self._tr("select_valid_model_before_add"))
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Adicionar Tecido")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.focus_force()

        centralizar_janela(dialog, largura=1100, altura=820, parent=self)

        self.obter_cores_por_tema()
        self.configurar_treeview_theme()

        main_frame = ctk.CTkScrollableFrame(dialog, fg_color=self.cor_fundo)
        main_frame.pack(fill="both", expand=True, padx=10, pady=(10, 18))

        search_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        search_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(search_frame, text=self._tr("search_fabric_dialog"),
                     width=150, anchor="w", text_color=self.cor_texto).pack(side="left", padx=5)

        search_entry = ctk.CTkEntry(search_frame,
                                    fg_color=self.cor_secundaria,
                                    border_color=self.cor_borda,
                                    text_color=self.cor_texto_entry,
                                    placeholder_text_color=self.cor_placeholder)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)

        tree_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        tree_frame.pack(fill="both", expand=True, pady=5)

        columns = ["ID", "Código", "Descrição", "Cor", "Composição", "Metros Disp.", "Status"]
        tecido_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8, style="Custom.Treeview")

        for col in columns:
            tecido_tree.heading(col, text=col)
            if col == "Descrição":
                tecido_tree.column(col, width=150, anchor='w')
            elif col == "Cor":
                tecido_tree.column(col, width=100, anchor='w')
            elif col == "Composição":
                tecido_tree.column(col, width=200, anchor='w')
            elif col in ["Metros Disp.", "Status"]:
                tecido_tree.column(col, width=80, anchor='center')
            else:
                tecido_tree.column(col, width=80, anchor='w')

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tecido_tree.yview)
        scrollbar.pack(side="right", fill="y")
        tecido_tree.configure(yscrollcommand=scrollbar.set)
        tecido_tree.pack(fill="both", expand=True)
        tecido_tree.tag_configure('esgotado', foreground='red')

        selecionado_var = ctk.StringVar(value="Nenhum tecido selecionado")

        cor_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        cor_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(cor_frame, text=self._tr("available_color"),
                     width=150, anchor="w", text_color=self.cor_texto).pack(side="left", padx=5)

        self.cor_cb_add = ctk.CTkComboBox(cor_frame, state="readonly",
                                          fg_color=self.cor_secundaria,
                                          border_color=self.cor_borda,
                                          text_color=self.cor_texto,
                                          button_color=self.cor_primaria,
                                          button_hover_color=self.cor_hover)
        self.cor_cb_add.set(self._tr("select_color"))
        self.cor_cb_add.pack(side="left", fill="x", expand=True, padx=5)

        info_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        info_frame.pack(fill="x", pady=(4, 2))
        ctk.CTkLabel(info_frame, textvariable=selecionado_var,
                     text_color=self.cor_texto, anchor="w").pack(fill="x", padx=5)

        quant_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        quant_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(quant_frame, text=self._tr("bobbins"), text_color=self.cor_texto).pack(side="left", padx=5)
        bobinas_entry = ctk.CTkEntry(quant_frame, width=80,
                                     fg_color=self.cor_secundaria,
                                     border_color=self.cor_borda,
                                     text_color=self.cor_texto_entry)
        bobinas_entry.pack(side="left", padx=5)
        bobinas_entry.insert(0, "1")

        ctk.CTkLabel(quant_frame, text=self._tr("sheets_short"), text_color=self.cor_texto).pack(side="left", padx=5)
        folhas_entry = ctk.CTkEntry(quant_frame, width=80,
                                    fg_color=self.cor_secundaria,
                                    border_color=self.cor_borda,
                                    text_color=self.cor_texto_entry)
        folhas_entry.pack(side="left", padx=5)
        folhas_entry.insert(0, "1")

        grade_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        grade_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(grade_frame, text=self._tr("qty_by_size"), text_color=self.cor_texto).pack(anchor="w")

        scroll_grade = ctk.CTkScrollableFrame(grade_frame, orientation="horizontal", fg_color=self.cor_fundo)
        scroll_grade.pack(fill="x", expand=True)

        tamanho_entries = {}
        for tamanho in self.grade_disponivel:
            frame = ctk.CTkFrame(scroll_grade, fg_color=self.cor_fundo)
            frame.pack(side="left", padx=5)

            ctk.CTkLabel(frame, text=tamanho, text_color=self.cor_texto).pack()
            entry = ctk.CTkEntry(frame, width=50,
                                 fg_color=self.cor_secundaria,
                                 border_color=self.cor_borda,
                                 text_color=self.cor_texto_entry)
            entry.pack()
            entry.insert(0, "0")
            tamanho_entries[tamanho] = entry

        btn_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        btn_frame.pack(fill="x", pady=(10, 20))

        btn_confirmar = ctk.CTkButton(
            btn_frame,
            text=self._tr("confirm"),
            command=lambda: self._confirmar_adicao_tecido(
                dialog, tecido_tree, self.cor_cb_add,
                bobinas_entry, folhas_entry, tamanho_entries
            ),
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            width=120,
            text_color=self.cor_texto
        )
        btn_confirmar.pack(side="left", padx=5)

        btn_cancelar = ctk.CTkButton(
            btn_frame,
            text=self._tr("cancel"),
            command=dialog.destroy,
            fg_color=self.cor_secundaria,
            hover_color=self.cor_hover,
            width=120,
            text_color=self.cor_texto
        )
        btn_cancelar.pack(side="right", padx=5)

        def on_tecido_select(event=None):
            selecionado = tecido_tree.selection()
            if not selecionado:
                return

            item = tecido_tree.item(selecionado[0])
            valores = item.get('values', [])
            if len(valores) < 4:
                return

            codigo = valores[1]
            descricao = valores[2]
            cor_atual = valores[3]
            metros_disp = valores[5] if len(valores) > 5 else ""
            status = valores[6] if len(valores) > 6 else ""

            selecionado_var.set(
                f"Selecionado: {codigo} - {descricao} | Cor atual: {cor_atual} | Estoque: {metros_disp} ({status})"
            )
            # Evita manter cores antigas enquanto recarrega
            self.cor_cb_add.set(self._tr("loading_colors"))
            self.cor_cb_add.configure(values=[])

            self._carregar_cores_por_codigo(codigo, self.cor_cb_add, cor_atual, tecido_tree, descricao)

        def do_busca():
            self.cor_cb_add.set(self._tr("select_color"))
            self.cor_cb_add.configure(values=[])
            selecionado_var.set(self._tr("no_fabric_selected"))

            self._buscar_tecidos_para_adicao(search_entry, tecido_tree)

            itens = tecido_tree.get_children()
            if len(itens) == 1:
                tecido_tree.selection_set(itens[0])
                tecido_tree.focus(itens[0])
                on_tecido_select()

        btn_buscar = ctk.CTkButton(search_frame, text=self._tr("search"), width=80, command=do_busca,
                                   fg_color=self.cor_primaria, hover_color=self.cor_hover,
                                   text_color=self.cor_texto)
        btn_buscar.pack(side="left", padx=5)
        search_entry.bind("<Return>", lambda event: do_busca())

        tecido_tree.bind("<<TreeviewSelect>>", on_tecido_select)
        do_busca()
        search_entry.focus_set()

        padronizar_treeviews_container(dialog)

    def _salvar_tecidos(self, cursor, cadastro_id):
        def _as_int(v):
            try:
                s = str(v).strip()
                return int(float(s)) if s not in ("", "None", None) else 0
            except Exception:
                return 0

        cursor.execute("""
               SELECT column_name FROM information_schema.columns
               WHERE table_schema = current_schema() AND table_name = 'cadastro_de_corte_tecidos'
           """)
        cols = {r[0] for r in cursor.fetchall()}
        has_comp = "composicao" in cols
        has_total = "total_pecas" in cols

        base_cols = ["cadastro_id", "tecido", "cor"]
        if has_comp: base_cols.append("composicao")
        base_cols += ["bobinas", "folhas", "pp", "p", "m", "g", "gg", "g1", "g2", "g3"]
        if has_total: base_cols.append("total_pecas")

        placeholders = ",".join(["%s"] * len(base_cols))
        sql = f"INSERT INTO cadastro_de_corte_tecidos ({','.join(base_cols)}) VALUES ({placeholders})"

        # VERIFICAÇÃO: Imprime informações para debug
        print(f"Colunas disponíveis na tabela: {cols}")

        for iid in getattr(self, "tree", []).get_children():
            v = list(self.tree.item(iid, "values") or [])
            if len(v) < 19:  # Verifica se tem valores suficientes
                print(f"Aviso: Linha com valores insuficientes: {len(v)} itens")
                continue

            # DEBUG: Imprime os valores
            print(f"Valores da linha: {v}")

            tecido = (v[0] or "").strip()
            cor = (v[2] or "").strip()
            composicao = (v[4] or "").strip()
            bobinas = _as_int(v[6])
            folhas = _as_int(v[8])

            # Extrai as quantidades por tamanho - ATENÇÃO: os índices podem variar
            # Verifique a posição correta dos tamanhos na sua interface
            # Normalmente: índice 10 = PP, 11 = P, 12 = M, 13 = G, 14 = GG, 15 = G1, 16 = G2, 17 = G3
            pp = _as_int(v[10])
            p = _as_int(v[11])
            m = _as_int(v[12])
            g = _as_int(v[13])
            gg = _as_int(v[14])
            g1 = _as_int(v[15])
            g2 = _as_int(v[16])
            g3 = _as_int(v[17])

            # Calcula o total de peças
            total = pp + p + m + g + gg + g1 + g2 + g3

            # Se a coluna total_pecas existe, usa o valor calculado
            if has_total and total == 0:
                # Tenta pegar o total da última coluna se disponível
                if len(v) > 18:
                    total = _as_int(v[18])
                else:
                    total = pp + p + m + g + gg + g1 + g2 + g3

            # DEBUG: Imprime os valores extraídos
            print(f"Tecido: {tecido}, Cor: {cor}, Bobinas: {bobinas}, Folhas: {folhas}")
            print(f"Quantidades: PP={pp}, P={p}, M={m}, G={g}, GG={gg}, G1={g1}, G2={g2}, G3={g3}")
            print(f"Total peças: {total}")

            values = [cadastro_id, tecido, cor]
            if has_comp:
                values.append(composicao)
            values += [bobinas, folhas, pp, p, m, g, gg, g1, g2, g3]
            if has_total:
                values.append(total)

            print(f"SQL a executar: {sql}")
            print(f"Valores: {values}")

            cursor.execute(sql, tuple(values))

    def _salvar_lotes(self, cursor, cadastro_id):
        def _as_int(v):
            try:
                s = str(v).strip()
                return int(float(s)) if s not in ("", "None", None) else 0
            except Exception:
                return 0

        cursor.execute("""
               SELECT column_name FROM information_schema.columns
               WHERE table_schema = current_schema() AND table_name = 'cadastro_de_corte_lotes'
           """)
        cols = {r[0] for r in cursor.fetchall()}
        has_comp = "composicao" in cols
        has_total = "total_lote" in cols

        base_cols = ["cadastro_id", "lote", "tecido", "cor"]
        if has_comp: base_cols.append("composicao")
        base_cols += ["bobinas", "folhas", "pp", "p", "m", "g", "gg", "g1", "g2", "g3"]
        if has_total: base_cols.append("total_lote")

        placeholders = ",".join(["%s"] * len(base_cols))
        sql = f"INSERT INTO cadastro_de_corte_lotes ({','.join(base_cols)}) VALUES ({placeholders})"

        tree = getattr(self, "lotes_tree", None)
        if tree is None:
            return

        for iid in tree.get_children():
            v = list(tree.item(iid, "values") or [])
            if len(v) < 20:  # Ajuste conforme necessário
                continue

            lote = (v[0] or "").strip()
            tecido = (v[1] or "").strip()
            cor = (v[3] or "").strip()
            composicao = (v[5] or "").strip()
            bobinas = _as_int(v[7])
            folhas = _as_int(v[9])

            # Ajuste os índices conforme a estrutura da sua tabela de lotes
            pp = _as_int(v[11])
            p = _as_int(v[12])
            m = _as_int(v[13])
            g = _as_int(v[14])
            gg = _as_int(v[15])
            g1 = _as_int(v[16])
            g2 = _as_int(v[17])
            g3 = _as_int(v[18])

            total = pp + p + m + g + gg + g1 + g2 + g3

            values = [cadastro_id, lote, tecido, cor]
            if has_comp:
                values.append(composicao)
            values += [bobinas, folhas, pp, p, m, g, gg, g1, g2, g3]
            if has_total:
                values.append(total)

            cursor.execute(sql, tuple(values))

    def _buscar_tecidos_para_adicao(self, search_entry, tecido_tree):
        try:
            termo = search_entry.get().strip().lower()

            tecido_tree.delete(*tecido_tree.get_children())

            like_termo = f"%{termo}%" if termo else "%"

            conn = _pg_connect()
            with conn.cursor() as cursor:
                cursor.execute("""
                       SELECT id, codigo, descricao, cor, composicao, metros
                       FROM estoque_tecidos
                       WHERE (LOWER(codigo) LIKE %s OR
                              LOWER(descricao) LIKE %s OR
                              LOWER(cor) LIKE %s OR
                              LOWER(composicao) LIKE %s)
                       ORDER BY descricao, cor
                   """, (like_termo, like_termo, like_termo, like_termo))

                rows = cursor.fetchall()

            for row in rows:
                id_tecido, codigo, descricao, cor, composicao, metros = row
                codigo_str = "" if codigo is None else f"{codigo}"
                metros = float(metros) if metros is not None else 0.0
                status = "Disponível" if metros > 0 else "Esgotado"
                metros_fmt = self._formatar_metros(metros)
                tecido_tree.insert(
                    "",
                    "end",
                    values=(id_tecido, codigo_str, descricao, cor, composicao, f"{metros_fmt}m", status),
                    tags=('esgotado',) if metros <= 0 else ()
                )

            if not tecido_tree.get_children():
                messagebox.showinfo(self._tr("info"), self._tr("search_no_results"))

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na busca:\n{str(e)}")

    def _adicionar_tecido_tabela(self, dados, metros_utilizados):
        try:
            valores = [
                dados['tecido'], "",
                dados['cor'], "",
                dados['composicao'], "",
                str(dados['bobinas']), "",
                str(dados['folhas']), ""
            ]

            for tamanho in self.tamanhos:
                valores.append(str(dados['quantidades'].get(tamanho, 0)))

            total_pecas = sum(int(qtd) for qtd in dados['quantidades'].values())
            valores.append(str(total_pecas))

            tag = 'evenrow' if len(self.tree.get_children()) % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=valores, tags=(tag,))

            self.atualizar_lotes()
            self.calcular_totais()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao adicionar tecido:\n{str(e)}")

    def atualizar_lotes(self):
        lotes_agrupados = {}

        for item in self.tree.get_children():
            valores = self.tree.item(item, 'values')
            try:
                tecido = valores[0]
                cor = valores[2]
                composicao = valores[4]
                bobinas = int(valores[6])
                folhas = int(valores[8])
            except (IndexError, ValueError):
                continue

            chave = (tecido, cor, composicao)
            if chave not in lotes_agrupados:
                lotes_agrupados[chave] = {
                    'tecido': tecido,
                    'cor': cor,
                    'composicao': composicao,
                    'bobinas': 0,
                    'folhas': 0,
                    'quantidades': {t: 0 for t in self.tamanhos}
                }
            lotes_agrupados[chave]['bobinas'] += bobinas
            lotes_agrupados[chave]['folhas'] += folhas

            for idx, tamanho in enumerate(self.tamanhos):
                try:
                    qtd = int(valores[10 + idx])
                    lotes_agrupados[chave]['quantidades'][tamanho] += qtd
                except (IndexError, ValueError):
                    continue

        self.lotes_tree.delete(*self.lotes_tree.get_children())

        for i, (chave, dados) in enumerate(lotes_agrupados.items(), start=1):
            valores = [
                          f"LOTE {i}",
                          dados['tecido'],
                          "",
                          dados['cor'],
                          "",
                          dados['composicao'],
                          "",
                          str(dados['bobinas']),
                          "",
                          str(dados['folhas']),
                          ""
                      ] + [str(dados['quantidades'][t]) for t in self.tamanhos] + [
                          str(sum(dados['quantidades'].values()))
                      ]

            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.lotes_tree.insert("", "end", values=valores, tags=(tag,))

    def calcular_totais(self, event=None):
        try:
            if (self.comprimento_entry is None or
                    self.largura_entry is None or
                    self.tree is None or
                    self.total_folhas_var is None or
                    self.bobinas_utilizadas_var is None or
                    self.total_pecas_var is None or
                    self.metros_utilizados_var is None or
                    self.rendimento_var is None):
                print("Widgets não inicializados para cálculo")
                return

            try:
                comprimento_str = self.comprimento_entry.get()
                largura_str = self.largura_entry.get()
                comprimento = float(comprimento_str) if comprimento_str else 0.0
                largura = float(largura_str) if largura_str else 0.0
            except ValueError as ve:
                print(f"Erro ao converter valores: {ve}")
                comprimento = 0.0
                largura = 0.0

            total_folhas = 0
            total_pecas = 0
            total_bobinas = 0

            if self.tree.get_children():
                for item in self.tree.get_children():
                    valores = self.tree.item(item, 'values')

                    if not valores or len(valores) < 10 + len(self.tamanhos) + 1:
                        continue

                    try:
                        bobinas = int(valores[6]) if valores[6] else 0
                        folhas = int(valores[8]) if valores[8] else 0
                        pecas = int(valores[-1]) if valores[-1] else 0

                        total_folhas += folhas
                        total_bobinas += bobinas
                        total_pecas += pecas
                    except (IndexError, ValueError, TypeError) as e:
                        print(f"Erro ao processar item: {e}")
                        continue

            metros_utilizados = total_folhas * comprimento
            rendimento = metros_utilizados / total_pecas if total_pecas > 0 else 0

            self.total_folhas_var.set(str(total_folhas))
            self.bobinas_utilizadas_var.set(str(total_bobinas))
            self.total_pecas_var.set(str(total_pecas))
            self.metros_utilizados_var.set(f"{metros_utilizados:.2f}")
            self.rendimento_var.set(f"{rendimento:.2f}")

            self.atualizar_lotes()

        except Exception as e:
            print(f"Erro geral no cálculo: {e}")
            self.total_folhas_var.set("0")
            self.bobinas_utilizadas_var.set("0")
            self.total_pecas_var.set("0")
            self.metros_utilizados_var.set("0.00")
            self.rendimento_var.set("0.00")

    def _limpar_totais(self):
        self.total_folhas_var.set("0")
        self.metros_utilizados_var.set("0.00")
        self.bobinas_utilizadas_var.set("0")
        self.total_pecas_var.set("0")
        self.rendimento_var.set("0.00")

    def remover_tecido(self):
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning(self._tr("warn"), self._tr("select_fabric_remove"))
            return

        valores = self.tree.item(selecionado[0], "values")
        self.tree.delete(selecionado[0])

        self.atualizar_lotes()
        self.calcular_totais()

    def limpar_tabela(self):
        if messagebox.askyesno("Confirmar", "Deseja limpar toda a tabela de tecidos?"):
            for item in self.tree.get_children():
                self.tree.delete(item)
            for item in self.lotes_tree.get_children():
                self.lotes_tree.delete(item)
            self.calcular_totais()

    def limpar_tudo(self):
        if (self.codigo_entry is None or self.descricao_entry is None or
                self.comprimento_entry is None or self.largura_entry is None or
                self.cortador_entry is None or self.ajudante_entry is None or
                self.data_entry is None or self.obs_entry is None or
                self.tree is None or self.lotes_tree is None):
            messagebox.showerror(self._tr("error"), self._tr("interface_not_init"))
            return

        if not messagebox.askyesno(self._tr("confirm_title"), self._tr("confirm_clear")):
            return

        try:
            self.codigo_entry.delete(0, "end")
            self.descricao_entry.delete(0, "end")

            self.comprimento_entry.delete(0, "end")
            self.comprimento_entry.insert(0, "7.35")

            self.largura_entry.delete(0, "end")
            self.largura_entry.insert(0, "1.48")

            self.cortador_entry.delete(0, "end")
            self.ajudante_entry.delete(0, "end")

            self.data_entry.delete(0, "end")
            self.data_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))

            if hasattr(self, 'composicao_entry') and self.composicao_entry:
                self.composicao_entry.configure(state="normal")
                self.composicao_entry.delete(0, "end")
                self.composicao_entry.insert(0, "98% POLIESTER 2% ELASTANO")
                self.composicao_entry.configure(state="readonly")

            self.obs_entry.delete(0, "end")

            for item in self.tree.get_children():
                self.tree.delete(item)
            for item in self.lotes_tree.get_children():
                self.lotes_tree.delete(item)

            self.total_folhas_var.set("0")
            self.metros_utilizados_var.set("0.00")
            self.bobinas_utilizadas_var.set("0")
            self.total_pecas_var.set("0")
            self.rendimento_var.set("0.00")

            self.numero_ordem = self.gerar_proximo_numero_oc()
            self.numero_ordem_entry.configure(state="normal")
            self.numero_ordem_entry.delete(0, "end")
            self.numero_ordem_entry.insert(0, self.numero_ordem)
            self.numero_ordem_entry.configure(state="readonly")

        except Exception as e:
            messagebox.showerror(self._tr("error"), self._tr("clear_fail", erro=e))

    def _get_text(self, *attr_names, default=""):
        for name in attr_names:
            try:
                obj = getattr(self, name, None)
                if obj is None:
                    continue
                if hasattr(obj, "get") and callable(getattr(obj, "get")):
                    val = obj.get()
                    return ("" if val is None else str(val)).strip()
            except Exception:
                continue
        return default

    def salvar_ordem(self):
        import traceback

        conn = None
        try:
            conn = _pg_connect()
            with conn.cursor() as cur:

                # ========================================================
                # (0) BLOQUEIO DE DUPLICIDADE (NÃO PERMITE SALVAR A MESMA OC)
                # ========================================================
                numero_ordem = (self._get_text("numero_ordem_entry") or "").strip()
                if not numero_ordem:
                    messagebox.showwarning(self._tr("warn"), self._tr("fill_order_before_save"))
                    return

                # Verifica se já existe no banco (case-insensitive)
                cur.execute(
                    "SELECT 1 FROM cadastro_de_corte WHERE UPPER(numero_ordem) = UPPER(%s) LIMIT 1",
                    (numero_ordem,)
                )
                if cur.fetchone():
                    messagebox.showwarning(self._tr("cut_exists"), self._tr("cut_exists_msg", numero_ordem=numero_ordem))
                    return

                # ========================================================
                # (1) INSERT NO CABEÇALHO DA ORDEM
                # ========================================================
                sql_cab = (
                    "INSERT INTO cadastro_de_corte ("
                    "numero_ordem, codigo, descricao, data, "
                    "comprimento_matriz, largura_matriz, "
                    "cortador, ajudante, auxiliar, "
                    "total_folhas, metros_utilizados, bobinas_utilizadas, "
                    "composicao_tecido, "
                    "pp, p, m, g, gg, g1, g2, g3, "
                    "total_pecas, rendimento, observacoes"
                    ") VALUES ("
                    "%(numero_ordem)s, %(codigo)s, %(descricao)s, %(data)s, "
                    "%(comprimento)s, %(largura)s, "
                    "%(cortador)s, %(ajudante)s, %(auxiliar)s, "
                    "%(total_folhas)s, %(metros)s, %(bobinas)s, "
                    "%(composicao)s, "
                    "%(pp)s, %(p)s, %(m)s, %(g)s, %(gg)s, %(g1)s, %(g2)s, %(g3)s, "
                    "%(total)s, %(rendimento)s, %(obs)s"
                    ") RETURNING id"
                )

                # SOMA DA GRADE TOTAL DOS TECIDOS
                total_grade = {t.lower(): 0 for t in self.tamanhos}

                for item in self.tree.get_children():
                    valores = self.tree.item(item, "values")
                    for i, t in enumerate(self.tamanhos):
                        try:
                            total_grade[t.lower()] += int(str(valores[10 + i]).strip() or 0)
                        except Exception:
                            total_grade[t.lower()] += 0

                # Monta dados do cabeçalho
                dados_cab = {
                    "numero_ordem": numero_ordem,
                    "codigo": self._get_text("codigo_entry"),
                    "descricao": self._get_text("descricao_entry"),
                    "data": datetime.strptime(
                        self._get_text("data_entry") or datetime.now().strftime("%d/%m/%Y"),
                        "%d/%m/%Y"
                    ),
                    "comprimento": float((self._get_text("comprimento_entry") or "0").replace(",", ".")),
                    "largura": float((self._get_text("largura_entry") or "0").replace(",", ".")),
                    "cortador": self._get_text("cortador_entry"),
                    "ajudante": self._get_text("ajudante_entry"),
                    "auxiliar": None,
                    "total_folhas": int(self._get_text("total_folhas_var", default="0") or 0),
                    "metros": float((self._get_text("metros_utilizados_var", default="0") or "0").replace(",", ".")),
                    "bobinas": float((self._get_text("bobinas_utilizadas_var", default="0") or "0").replace(",", ".")),
                    "composicao": "",
                    "pp": total_grade.get("pp", 0),
                    "p": total_grade.get("p", 0),
                    "m": total_grade.get("m", 0),
                    "g": total_grade.get("g", 0),
                    "gg": total_grade.get("gg", 0),
                    "g1": total_grade.get("g1", 0),
                    "g2": total_grade.get("g2", 0),
                    "g3": total_grade.get("g3", 0),
                    "total": int(self._get_text("total_pecas_var", default="0") or 0),
                    "rendimento": float((self._get_text("rendimento_var", default="0") or "0").replace(",", ".")),
                    "obs": self._get_text("obs_entry"),
                }

                cur.execute(sql_cab, dados_cab)
                cadastro_id = cur.fetchone()[0]

                # ========================================================
                # (2) INSERT DOS TECIDOS
                # ========================================================
                sql_tecidos = (
                    "INSERT INTO cadastro_de_corte_tecidos ("
                    "cadastro_id, tecido, cor, composicao, "
                    "bobinas, folhas, "
                    "pp, p, m, g, gg, g1, g2, g3, "
                    "total_pecas"
                    ") VALUES ("
                    "%s, %s, %s, %s, "
                    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                    "%s"
                    ")"
                )

                def _to_float(v):
                    try:
                        s = str(v).strip().replace(",", ".")
                        return float(s) if s else 0.0
                    except Exception:
                        return 0.0

                def _to_int(v):
                    try:
                        s = str(v).strip()
                        return int(float(s)) if s else 0
                    except Exception:
                        return 0

                for item in self.tree.get_children():
                    v = self.tree.item(item, "values")

                    quant = [_to_int(v[10 + i]) for i in range(8)]
                    total_item = sum(quant)

                    cur.execute(
                        sql_tecidos,
                        (
                            cadastro_id,
                            v[0],  # tecido
                            v[2],  # cor
                            v[4],  # composicao
                            _to_float(v[6]),  # bobinas
                            _to_float(v[8]),  # folhas
                            *quant,
                            total_item,
                        ),
                    )

                # ========================================================
                # (3) INSERT DOS LOTES
                # ========================================================
                sql_lotes = (
                    "INSERT INTO cadastro_de_corte_lotes ("
                    "cadastro_id, lote, tecido, cor, composicao, "
                    "bobinas, folhas, "
                    "pp, p, m, g, gg, g1, g2, g3, "
                    "total_lote"
                    ") VALUES ("
                    "%s, %s, %s, %s, %s, "
                    "%s, %s, "
                    "%s, %s, %s, %s, %s, %s, %s, %s, "
                    "%s"
                    ")"
                )

                for item in self.lotes_tree.get_children():
                    v = self.lotes_tree.item(item, "values")

                    quant = [_to_int(v[11 + i]) for i in range(8)]
                    total_item = sum(quant)

                    cur.execute(
                        sql_lotes,
                        (
                            cadastro_id,
                            v[0],  # lote
                            v[1],  # tecido
                            v[3],  # cor
                            v[5],  # composicao
                            _to_float(v[7]),  # bobinas
                            _to_float(v[9]),  # folhas
                            *quant,
                            total_item,
                        ),
                    )

            conn.commit()
            messagebox.showinfo("Sucesso", "Ordem salva com sucesso!")

        except Exception:
            try:
                if conn is not None:
                    conn.rollback()
            except Exception:
                pass

            erro_completo = traceback.format_exc()
            print("\n============= ERRO SALVAR ORDEM =============")
            print(erro_completo)
            print("=============================================\n")

            messagebox.showerror("ERRO ao salvar", erro_completo)

        finally:
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass

    def gerar_pdf_em_buffer(self):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        styles = getSampleStyleSheet()

        estilo_titulo = ParagraphStyle(
            'Titulo',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor(self.cor_texto),
            spaceAfter=12,
            alignment=1
        )

        estilo_subtitulo = ParagraphStyle(
            'Subtitulo',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor(self.cor_texto),
            spaceAfter=6,
            alignment=0
        )

        estilo_texto = ParagraphStyle(
            'Texto',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=6
        )

        margem = 15 * mm
        y = height - margem
        espacamento = 6 * mm

        if hasattr(self, 'logo_photo'):
            try:
                logo_paths = [
                    "logo.png", "logo.jpg",
                    os.path.join(os.path.dirname(__file__), "logo.png"),
                    os.path.join(os.path.dirname(__file__), "imgs", "logo.png"),
                    os.path.join(os.path.dirname(__file__), "assets", "logo.png")
                ]

                for path in logo_paths:
                    if os.path.exists(path):
                        c.drawImage(path, width - margem - 50 * mm, y - 15 * mm,
                                    width=50 * mm, height=15 * mm, preserveAspectRatio=True)
                        break
            except Exception as e:
                print(f"Erro ao carregar logo: {e}")

        p = Paragraph("<b>ORDEM DE CORTE</b>", estilo_titulo)
        p.wrapOn(c, width - 2 * margem, 30 * mm)
        p.drawOn(c, margem, y - 20 * mm)
        y -= 25 * mm

        c.setStrokeColor(colors.HexColor("#80bbff"))
        c.setLineWidth(1.5 * mm)
        c.line(margem, y, width - margem, y)
        y -= 10 * mm

        col1_x = margem
        col2_x = width / 2 + 10 * mm

        info_col1 = [
            ("<b>Nº Ordem:</b>", self.numero_ordem_entry.get()),
            ("<b>Código:</b>", self.codigo_entry.get()),
            ("<b>Descrição:</b>", self.descricao_entry.get()),
            ("<b>Data:</b>", self.data_entry.get())
        ]

        for label, value in info_col1:
            p = Paragraph(f"{label} {value}", estilo_texto)
            p.wrapOn(c, 80 * mm, 10 * mm)
            p.drawOn(c, col1_x, y)
            y -= espacamento

        y = height - margem - 25 * mm
        info_col2 = [
            ("<b>Cortador:</b>", self.cortador_entry.get()),
            ("<b>Ajudante:</b>", self.ajudante_entry.get()),
            ("<b>Comp. Matriz:</b>", f"{self.comprimento_entry.get()} m"),
            ("<b>Largura:</b>", f"{self.largura_entry.get()} m")
        ]

        for label, value in info_col2:
            p = Paragraph(f"{label} {value}", estilo_texto)
            p.wrapOn(c, 80 * mm, 10 * mm)
            p.drawOn(c, col2_x, y)
            y -= espacamento

        y = height - margem - 50 * mm

        p = Paragraph("<b>Observações:</b>", estilo_subtitulo)
        p.wrapOn(c, width - 2 * margem, 10 * mm)
        p.drawOn(c, margem, y)
        y -= 10 * mm

        p = Paragraph(self.obs_entry.get() or "Nenhuma observação informada", estilo_texto)
        p.wrapOn(c, width - 2 * margem, 20 * mm)
        p.drawOn(c, margem, y)
        y -= 20 * mm

        p = Paragraph("<b>Tecidos Utilizados</b>", estilo_subtitulo)
        p.wrapOn(c, width - 2 * margem, 10 * mm)
        p.drawOn(c, margem, y)
        y -= 15 * mm

        headers = ["Tecido", "Cor", "Bobinas", "Folhas"] + self.tamanhos + ["Total"]
        col_widths = [40 * mm, 20 * mm, 15 * mm, 15 * mm] + [10 * mm] * len(self.tamanhos) + [15 * mm]

        data = [headers]
        for item in self.tree.get_children():
            valores = list(self.tree.item(item, "values"))
            tecido_nome = valores[0]
            row = [tecido_nome, valores[2], valores[6], valores[8]] + [valores[10 + i] for i in
                                                                       range(len(self.tamanhos))] + [valores[-1]]
            data.append(row)

        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.cor_texto)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor(self.cor_fundo)),
            ('GRID', (0, 0), (-1, -1), 0.5 * mm, colors.HexColor("#dee2e6")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        altura_tabela = len(data) * 5 * mm + 10 * mm

        if y - altura_tabela < margem:
            c.showPage()
            y = height - margem
            p = Paragraph("<b>Tecidos Utilizados</b> (continuação)", estilo_subtitulo)
            p.wrapOn(c, width - 2 * margem, 10 * mm)
            p.drawOn(c, margem, y)
            y -= 15 * mm

        t.wrapOn(c, width - 2 * margem, altura_tabela)
        t.drawOn(c, margem, y - altura_tabela)
        y -= altura_tabela + 10 * mm

        if self.lotes_tree.get_children():
            p = Paragraph("<b>Lotes de Produção</b>", estilo_subtitulo)
            p.wrapOn(c, width - 2 * margem, 10 * mm)
            p.drawOn(c, margem, y)
            y -= 15 * mm

            headers = ["Lote", "Cor"] + self.tamanhos
            col_widths = [25 * mm, 25 * mm] + [15 * mm] * len(self.tamanhos)

            data = [headers]
            for item in self.lotes_tree.get_children():
                valores = self.lotes_tree.item(item, "values")
                data.append([valores[0], valores[3]] + [valores[11 + i] for i in range(len(self.tamanhos))])

            t = Table(data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.cor_texto)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor(self.cor_fundo)),
                ('GRID', (0, 0), (-1, -1), 0.5 * mm, colors.HexColor("#dee2e6")),
            ]))

            altura_tabela = len(data) * 5 * mm + 10 * mm

            if y - altura_tabela < margem:
                c.showPage()
                y = height - margem
                p = Paragraph("<b>Lotes de Produção</b> (continuação)", estilo_subtitulo)
                p.wrapOn(c, width - 2 * margem, 10 * mm)
                p.drawOn(c, margem, y)
                y -= 15 * mm

            t.wrapOn(c, width - 2 * margem, altura_tabela)
            t.drawOn(c, margem, y - altura_tabela)
            y -= altura_tabela + 10 * mm

        totais = [
            ("<b>Total de Folhas:</b>", self.total_folhas_var.get()),
            ("<b>Metros Utilizados:</b>", self.metros_utilizados_var.get()),
            ("<b>Bobinas Utilizadas:</b>", self.bobinas_utilizadas_var.get()),
            ("<b>Total de Peças:</b>", self.total_pecas_var.get()),
            ("<b>Rendimento:</b>", self.rendimento_var.get())
        ]

        for label, value in totais:
            p = Paragraph(f"{label} {value}", estilo_texto)
            p.wrapOn(c, 80 * mm, 10 * mm)
            p.drawOn(c, margem, y)
            y -= espacamento
            if y < margem + 30 * mm:
                c.showPage()
                y = height - margem

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#6c757d"))
        c.drawString(margem, 15 * mm, f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        c.drawRightString(width - margem, 15 * mm, "Sistema Guimma")

        c.save()
        buffer.seek(0)
        return buffer

    def buscar_descricao_por_codigo(self, event=None):
        codigo = self.codigo_entry.get().strip()
        if not codigo:
            return

        try:
            conn = _pg_connect()
            with conn.cursor() as cursor:
                cursor.execute("""
                       SELECT column_name FROM information_schema.columns 
                       WHERE table_schema = current_schema() AND table_name = 'cadastro_modelos_cabecalho'
                   """)
                colnames = {r[0].lower() for r in cursor.fetchall()}
                candidatos_grade = [
                    "grade_disponivel", "grade", "grade_tamanhos",
                    "tamanhos_disponiveis", "tamanhos", "grade_tam"
                ]
                grade_col = next((c for c in candidatos_grade if c in colnames), None)

                if grade_col:
                    cursor.execute(f"""
                           SELECT descricao, {grade_col}
                           FROM cadastro_modelos_cabecalho
                           WHERE codigo ILIKE %s
                           LIMIT 1
                       """, (codigo,))
                else:
                    cursor.execute("""
                           SELECT descricao
                           FROM cadastro_modelos_cabecalho
                           WHERE codigo ILIKE %s
                           LIMIT 1
                       """, (codigo,))
                resultado = cursor.fetchone()

            if resultado:
                self.descricao_entry.delete(0, "end")
                self.descricao_entry.insert(0, resultado[0])

                grade_str = resultado[1] if (grade_col and len(resultado) > 1) else None
                if grade_str:
                    raw = (str(grade_str) or "").replace(";", ",").replace("/", ",")
                    tamanhos = [t.strip().upper() for t in raw.split(",") if t.strip()]
                    self.grade_disponivel = [t for t in tamanhos if t in self.tamanhos]
                    if not self.grade_disponivel:
                        messagebox.showwarning(
                            "Aviso",
                            "Grade do modelo não contém tamanhos válidos!\nUsando grade padrão."
                        )
                        self.grade_disponivel = self.tamanhos.copy()
                else:
                    self.grade_disponivel = self.tamanhos.copy()

                self.btn_adicionar_tecido.configure(state="normal")
            else:
                messagebox.showinfo(self._tr("not_found"), self._tr("model_not_found_by_code", codigo=codigo))
                self.grade_disponivel = []
                self.btn_adicionar_tecido.configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao buscar modelo:\n{str(e)}")
            self.btn_adicionar_tecido.configure(state="disabled")

    def _confirmar_adicao_tecido(self, dialog, tecido_tree, cor_cb, bobinas_entry, folhas_entry, tamanho_entries):
        conn = None
        try:
            selecionado = tecido_tree.selection()
            if not selecionado:
                raise ValueError("Selecione um tecido na lista")

            item = tecido_tree.item(selecionado[0])
            valores = item['values']

            cor_completa = cor_cb.get()
            cor_selecionada = cor_completa.split(' (')[0].strip()
            if not cor_selecionada or cor_selecionada in ("Selecione uma cor", "Nenhuma cor encontrada"):
                raise ValueError("Selecione uma cor válida")

            tecido_id = valores[0]

            dados_tecido = {
                'id': tecido_id,
                'codigo': str(valores[1]).strip(),
                'tecido': valores[2],
                'composicao': valores[4],
                'cor': str(cor_selecionada).strip(),
                'bobinas': int(bobinas_entry.get()),
                'folhas': int(folhas_entry.get()),
                'quantidades': {}
            }

            if dados_tecido['bobinas'] <= 0 or dados_tecido['folhas'] <= 0:
                raise ValueError("Bobinas e folhas devem ser maiores que zero")

            for tamanho in self.grade_disponivel:
                try:
                    qtd = int(tamanho_entries[tamanho].get() or 0)
                    if qtd < 0:
                        raise ValueError(f"Quantidade inválida para {tamanho}")
                    dados_tecido['quantidades'][tamanho] = qtd
                except ValueError:
                    raise ValueError(f"Valor inválido para tamanho {tamanho}")

            if sum(dados_tecido['quantidades'].values()) <= 0:
                raise ValueError("Informe quantidades para pelo menos um tamanho")

            try:
                comprimento = float(self.comprimento_entry.get())
                largura = float(self.largura_entry.get())
                if comprimento <= 0 or largura <= 0:
                    raise ValueError("Dimensões inválidas")
            except (ValueError, AttributeError):
                raise ValueError("Informe valores válidos para comprimento e largura")

            metros_utilizados = dados_tecido['folhas'] * comprimento

            conn = _pg_connect()
            cursor = conn.cursor()

            cursor.execute("BEGIN")

            cursor.execute(
                """
                    SELECT codigo, descricao
                    FROM estoque_tecidos
                    WHERE id = %s
                    LIMIT 1
                """,
                (tecido_id,),
            )
            row_original = cursor.fetchone()
            if row_original:
                codigo_db, desc_db = row_original
                dados_tecido['codigo'] = str(codigo_db).strip()
                dados_tecido['tecido'] = desc_db if desc_db else dados_tecido['tecido']

            cursor.execute("""
                   SELECT metros, composicao
                   FROM estoque_tecidos
                   WHERE id = %s AND cor = %s
                   FOR UPDATE
                   LIMIT 1
               """, (tecido_id, dados_tecido['cor']))

            resultado = cursor.fetchone()

            # fallback: se o código não bater (ex.: zeros suprimidos), tenta pela descrição
            if not resultado:
                cursor.execute(
                    """
                        SELECT metros, composicao, codigo
                        FROM estoque_tecidos
                        WHERE descricao = %s AND cor = %s
                        ORDER BY codigo
                        FOR UPDATE
                        LIMIT 1
                    """,
                    (dados_tecido['tecido'], dados_tecido['cor']),
                )
                fallback = cursor.fetchone()
                if fallback:
                    metros, composicao, codigo_encontrado = fallback
                    resultado = (metros, composicao)
                    # Corrige o código usado no update/avisos para refletir o registro real
                    dados_tecido['codigo'] = str(codigo_encontrado).strip()

            if not resultado:
                raise ValueError(f"Não encontrado estoque para {dados_tecido['codigo']} - {dados_tecido['cor']}")

            metros_disponiveis, composicao = resultado
            metros_disponiveis = float(metros_disponiveis) if metros_disponiveis is not None else 0.0
            dados_tecido['composicao'] = composicao

            if metros_disponiveis <= 0:
                raise ValueError(f"Estoque zerado para {dados_tecido['codigo']} - {dados_tecido['cor']}")

            if metros_disponiveis < metros_utilizados:
                raise ValueError(
                    f"Estoque insuficiente para {dados_tecido['cor']}!\n"
                    f"Necessário: {metros_utilizados:.2f}m | Disponível: {metros_disponiveis:.2f}m\n\n"
                    f"Sugestões:\n"
                    f"1. Selecione outra cor disponível\n"
                    f"2. Reduza a quantidade de folhas\n"
                    f"3. Verifique outro lote do mesmo tecido"
                )

            novo_estoque = metros_disponiveis - metros_utilizados

            cursor.execute("""
                   UPDATE estoque_tecidos
                   SET metros = %s
                   WHERE id = %s AND cor = %s
               """, (novo_estoque, tecido_id, dados_tecido['cor']))

            conn.commit()

            self._adicionar_tecido_tabela(dados_tecido, metros_utilizados)
            self.carregar_tecidos()

            dialog.destroy()
            from tkinter import messagebox
            messagebox.showinfo("Sucesso", f"Tecido adicionado com sucesso!\nNovo estoque: {novo_estoque:.2f}m")

        except ValueError as e:
            from tkinter import messagebox
            messagebox.showerror(self._tr("validation_error"), str(e))
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            from tkinter import messagebox
            messagebox.showerror("Erro no Banco de Dados",
                                 f"Falha ao atualizar estoque:\n{str(e)}")
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _recarregar_modelos_ocf(self):
        self._ocf_map = {}
        opcoes = []

        try:
            conn = _pg_connect()
            cur = conn.cursor()

            cur.execute("""
                   SELECT column_name FROM information_schema.columns
                   WHERE table_schema = current_schema() AND table_name = 'ordem_corte_ficha'
               """)
            cols_raw = [r[0] for r in cur.fetchall()]
            cols = [c.lower() for c in cols_raw]

            def pick(*cands):
                for c in cands:
                    if c.lower() in cols:
                        return cols_raw[cols.index(c.lower())]
                return None

            col_id = pick('id')
            col_cod = pick('codigo_modelo', 'codigo', 'codigo_corte', 'cod_corte', 'corte_codigo')
            col_desc = pick('descricao', 'descricao_corte', 'descricao_modelo', 'produto', 'nome_modelo',
                            'descricao_produto')
            col_cort = pick('cortador')
            col_aux = pick('auxiliar', 'ajudante')

            if not col_cod:
                if hasattr(self, "modelo_ocf_cb"):
                    self.modelo_ocf_cb.configure(values=[f"[{self._tr("no_models_found")}]"])
                    self.modelo_ocf_cb.set(self._tr("select_model"))
                return

            campos = [c for c in (col_id, col_cod, col_desc, col_cort, col_aux) if c]
            order_col = col_id or col_cod

            cur.execute(f"""
                   SELECT {', '.join(campos)} 
                   FROM ordem_corte_ficha 
                   WHERE ativo = TRUE 
                   ORDER BY {order_col} DESC
               """)

            for row in cur.fetchall():
                data = dict(zip(campos, row))
                codigo = (data.get(col_cod) or "").strip()
                if not codigo:
                    continue

                descricao = (data.get(col_desc) or "").strip() if col_desc else ""
                label = f"{codigo} — {descricao}" if descricao else codigo

                self._ocf_map[label] = {
                    "codigo": codigo,
                    "descricao": descricao,
                    "cortador": (data.get(col_cort) or "").strip() if col_cort else "",
                    "auxiliar": (data.get(col_aux) or "").strip() if col_aux else "",
                }
                opcoes.append(label)

            conn.close()

        except Exception as e:
            print(f"Erro ao carregar modelos da ordem_corte_ficha: {e}")
            opcoes = ["[Erro ao carregar modelos]"]

        if hasattr(self, "modelo_ocf_cb") and self.modelo_ocf_cb is not None:
            self.modelo_ocf_cb.configure(values=opcoes)
            if opcoes and opcoes[0] != "[Erro ao carregar modelos]":
                self.modelo_ocf_cb.set(self._tr("select_model"))
            else:
                self.modelo_ocf_cb.set(opcoes[0] if opcoes else self._tr("no_models_found"))

    def _on_modelo_ocf_selected(self, value: str):
        try:
            info = self._ocf_map.get(value) or {}
            codigo = info.get("codigo", "").strip()
            if not codigo:
                return
            self._ocf_codigo_sel = codigo

            if hasattr(self, "codigo_entry") and self.codigo_entry:
                self.codigo_entry.delete(0, "end")
                self.codigo_entry.insert(0, codigo)

            desc = info.get("descricao", "").strip()
            if desc and hasattr(self, "descricao_entry") and self.descricao_entry:
                self.descricao_entry.delete(0, "end")
                self.descricao_entry.insert(0, desc)

            if info.get("cortador") and hasattr(self, "cortador_entry") and self.cortador_entry:
                self.cortador_entry.delete(0, "end")
                self.cortador_entry.insert(0, info.get("cortador", ""))
            if info.get("auxiliar") and hasattr(self, "ajudante_entry") and self.ajudante_entry:
                self.ajudante_entry.delete(0, "end")
                self.ajudante_entry.insert(0, info.get("auxiliar", ""))

            try:
                if hasattr(self, 'buscar_descricao_por_codigo'):
                    self.buscar_descricao_por_codigo()
            except Exception:
                pass
        except Exception:
            pass

    def _remover_da_ordem_corte_ficha_tx(self, cur, codigo: str) -> int:
        if not codigo:
            return 0
        codigo = str(codigo).strip()

        cur.execute("""
               SELECT column_name FROM information_schema.columns
               WHERE table_schema = current_schema() AND table_name = 'ordem_corte_ficha'
           """)
        cols_raw = [r[0] for r in cur.fetchall()]
        cols_lc = [c.lower() for c in cols_raw]

        def pick(*cands):
            for c in cands:
                if c.lower() in cols_lc:
                    return cols_raw[cols_lc.index(c.lower())]
            return None

        col_cod = pick('codigo_modelo', 'codigo', 'codigo_corte', 'cod_corte', 'corte_codigo')
        if not col_cod:
            return 0

        cur.execute(f"DELETE FROM ordem_corte_ficha WHERE {col_cod} = %s", (codigo,))
        return cur.rowcount or 0


if __name__ == "__main__":
    require_ready()


    class MockSistema:
        cor_primaria = "#3a7ebf"
        cor_secundaria = "#2b2b2b"
        cor_fundo = "#2b2b2b"
        cor_texto = "white"
        cor_borda = "#3a7ebf"
        cor_hover = "#2e4a66"


    root = ctk.CTk()
    app = CadastroOrdemCorte(master=root, sistema=MockSistema())
    app.pack(expand=True, fill="both")
    root.mainloop()

# --- AUTO_PAGE_TRANSLATIONS (gerado automaticamente) ---
from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support as _attach_i18n_support

AUTO_PAGE_TRANSLATIONS = {
    "CadastroOrdemCorte": {
        "pt_BR": {"title": "Cadastro Ordem Corte", "Atualizar": "Atualizar", "Filtrar": "Filtrar", "Salvar": "Salvar", "Cancelar": "Cancelar"},
        "en_US": {"title": "Cadastro Ordem Corte", "Atualizar": "Refresh", "Filtrar": "Filter", "Salvar": "Save", "Cancelar": "Cancel"},
        "es_ES": {"title": "Cadastro Ordem Corte", "Atualizar": "Actualizar", "Filtrar": "Filtrar", "Salvar": "Guardar", "Cancelar": "Cancelar"},
    },
}

for _cls_name, _map in AUTO_PAGE_TRANSLATIONS.items():
    _cls = globals().get(_cls_name)
    if isinstance(_cls, type):
        if not hasattr(_cls, "TRANSLATIONS") and not hasattr(_cls, "_TRANSLATIONS"):
            _cls.TRANSLATIONS = _map
        _attach_i18n_support(_cls, getattr(_cls, "TRANSLATIONS", getattr(_cls, "_TRANSLATIONS", _map)))
