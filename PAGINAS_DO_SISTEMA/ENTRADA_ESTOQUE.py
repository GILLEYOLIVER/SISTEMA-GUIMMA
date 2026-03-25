# -*- coding: utf-8 -*-
from PAGINAS_DO_SISTEMA import TEMAS
import customtkinter as ctk
import json
import os
from tkinter import ttk, messagebox
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from contextlib import contextmanager

# JESUS SEJA LOUVADO PARA TODO O SEMPRE AMEM!!!

# =============================================================================
# MÓDULO DE ACESSO A DADOS PADRONIZADO
# =============================================================================
class DBManager:
    """Classe unificada para gerir a conexão e as operações com o banco de dados."""

    def __init__(self):
        self.conn = None
        self.is_core_module = False
        self.schema = "opera"
        self.pgdb_module = None
        try:
            from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as pgdb
            self.pgdb_module = pgdb
            self.is_core_module = True
            self.schema = self.pgdb_module.get_schema()
            print("[INFO] Módulo 'BANCO_DE_DADOS_PG' carregado com sucesso.")
        except ImportError:
            self.is_core_module = False
            print("[WARN] Módulo 'BANCO_DE_DADOS_PG' não encontrado. Usando conexão DSN de fallback.")
            try:
                with open(os.path.join(os.path.dirname(__file__), "config.json"), "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
            self.dsn = os.getenv("OPERA_PG_DSN") or cfg.get("pg_dsn") or "postgresql://postgres:postgres@localhost:5433/BANCO_OPERA"
            self.schema = os.getenv("OPERA_PG_SCHEMA") or cfg.get("pg_schema") or "opera"

    def get_connection(self):
        if self.is_core_module:
            return self.pgdb_module.get_connection()
        if self.conn and not self.conn.closed:
            return self.conn
        import psycopg2
        self.conn = psycopg2.connect(self.dsn)
        return self.conn

    @contextmanager
    def cursor(self, commit=False):
        conn = self.get_connection()
        if conn.status != 1:
            conn.rollback()
        import psycopg2.extras
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cur.execute(f"SET search_path TO {self.schema}, public;")
            yield cur
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def fetch_all(self, query: str, params=None) -> list[dict]:
        with self.cursor() as cur:
            cur.execute(query, params or ())
            return [dict(row) for row in cur.fetchall()]

    def fetch_one(self, query: str, params=None) -> dict | None:
        with self.cursor() as cur:
            cur.execute(query, params or ())
            row = cur.fetchone()
            return dict(row) if row else None

    def execute(self, query: str, params=None) -> int:
        with self.cursor(commit=True) as cur:
            cur.execute(query, params or ())
            return cur.rowcount

    def table_exists(self, table_name: str) -> bool:
        if not table_name:
            return False
        try:
            full_name = f"{self.schema}.{table_name.lower()}"
            res = self.fetch_one("SELECT to_regclass(%s) IS NOT NULL AS ok", [full_name])
            if res and res.get("ok"):
                return True
        except Exception:
            pass
        try:
            res = self.fetch_one(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = %s AND LOWER(table_name) = LOWER(%s)
                """,
                (self.schema, table_name),
            )
            return bool(res)
        except Exception:
            return False

    def list_columns(self, table_name: str) -> set[str]:
        rows = self.fetch_all(
            "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",
            (self.schema, table_name.lower()),
        )
        return {row["column_name"].lower() for row in rows}

    def debug_tables(self):
        tabelas = self.fetch_all(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name",
            (self.schema,),
        )
        print("[DEBUG] Tabelas reais encontradas:", [t["table_name"] for t in tabelas])


db = DBManager()


class EntradaEstoqueApp(ctk.CTkFrame):
    def __init__(self, master, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.master = master
        self._ui_refs = {}
        self._column_keys = []
        self.entries = {}
        self._last_tipo_interno = "Tecidos"
        self._metric_column_by_type = {
            "Tecidos": ("metros", "kilos"),
            "Aviamentos": ("quantidade",),
            "Insumos": ("quantidade",),
            "Escritorio": ("quantidade",),
            "Limpeza": ("quantidade",),
            "Outros": ("quantidade",),
        }
        self._stock_thresholds = {
            "Tecidos": {"critico": Decimal("20"), "baixo": Decimal("40")},
            "Aviamentos": {"critico": Decimal("30"), "baixo": Decimal("50")},
            "Insumos": {"critico": Decimal("30"), "baixo": Decimal("50")},
            "Escritorio": {"critico": Decimal("15"), "baixo": Decimal("35")},
            "Limpeza": {"critico": Decimal("20"), "baixo": Decimal("40")},
            "Outros": {"critico": Decimal("25"), "baixo": Decimal("50")},
        }
        self.tecido_referencia_var = ctk.StringVar(value="metros")

        self.configure(fg_color=getattr(sistema, "cor_fundo", "#ffffff"))
        self.pack(fill="both", expand=True)

        from PAGINAS_DO_SISTEMA.LOG_SISTEMA import get_logger
        self.logger = get_logger("OPERA_SYSTEM")

        try:
            self.tipos = ["Tecidos", "Aviamentos", "Insumos", "Escritorio", "Limpeza", "Outros"]
            self.campos_por_tipo = {
                "Tecidos": [
                    "codigo", "descricao", "fornecedor", "composicao", "cor",
                    "metros", "kilos",
                    "estoque_ideal", "estoque_minimo", "estoque_critico",
                    "data_entrada", "observacoes"
                ],
                "Aviamentos": [
                    "codigo", "descricao", "fornecedor", "cor",
                    "quantidade", "unidade",
                    "estoque_ideal", "estoque_minimo", "estoque_critico",
                    "data_entrada", "observacoes"
                ],
                "Insumos": [
                    "codigo", "descricao", "fornecedor", "cor",
                    "quantidade", "unidade",
                    "estoque_ideal", "estoque_minimo", "estoque_critico",
                    "data_entrada", "observacoes"
                ],
                "Escritorio": [
                    "codigo", "descricao", "fornecedor", "cor",
                    "quantidade", "unidade",
                    "estoque_ideal", "estoque_minimo", "estoque_critico",
                    "data_entrada", "observacoes"
                ],
                "Limpeza": [
                    "codigo", "descricao", "fornecedor", "cor",
                    "quantidade", "unidade",
                    "estoque_ideal", "estoque_minimo", "estoque_critico",
                    "data_entrada", "observacoes"
                ],
                "Outros": [
                    "codigo", "descricao", "fornecedor", "cor",
                    "quantidade", "unidade",
                    "estoque_ideal", "estoque_minimo", "estoque_critico",
                    "data_entrada", "observacoes"
                ],
            }

            self.setup_ui()
            self.atualizar_interface(self.tipos[0])
            self.logger.info("[PAGINA] Entrada de Estoque: inicialização concluída com sucesso.")
        except Exception as e:
            import traceback
            self.logger.error(f"[PAGINA] Falha ao inicializar Entrada de Estoque: {e}\n{traceback.format_exc()}")
            print(f"[ERRO] Falha ao inicializar Entrada de Estoque: {e}")

    # =========================================================
    # MULTILÍNGUA
    # =========================================================
    def _get_idioma_atual(self):
        return getattr(self.sistema, "idioma_atual", "pt_BR")

    # ADICIONE ESTE MÉTODO DENTRO DA CLASSE EntradaEstoqueApp

    def _aplicar_estilo_tags_treeview(self):
        try:
            if not hasattr(self, "tree") or self.tree is None:
                return

            tema_atual = ctk.get_appearance_mode()

            if tema_atual == "Dark":
                self.tree.tag_configure("critico", background="#4c1d1d", foreground="#fecaca")
                self.tree.tag_configure("baixo", background="#45320f", foreground="#fde68a")
                self.tree.tag_configure("normal", background="#0f2e1d", foreground="#bbf7d0")
                self.tree.tag_configure("sem_referencia", background="#1f2937", foreground="#d1d5db")
            else:
                self.tree.tag_configure("critico", background="#ffe5e5", foreground="#a40000")
                self.tree.tag_configure("baixo", background="#fff7d6", foreground="#8a5a00")
                self.tree.tag_configure("normal", background="#e9f9ee", foreground="#0f6b2e")
                self.tree.tag_configure("sem_referencia", background="#f3f4f6", foreground="#4b5563")
        except Exception:
            pass

    def _get_text(self, chave, **kwargs):
        idioma = self._get_idioma_atual()
        textos = {
            "pt_BR": {
                "title": "Entrada de Estoque",
                "status_ready": "Pronto para editar: {tipo}",
                "register_entry": "Registrar Entrada",
                "clear_fields": "Limpar Campos",
                "search_code": "Pesquisar Código:",
                "search_code_placeholder": "Digite um código para pesquisar",
                "db_connection_error": "ERRO DE CONEXÃO:\n{erro}",
                "warning": "Aviso",
                "error": "Erro",
                "success": "Sucesso",
                "load_error": "Erro de Carregamento",
                "type_required": "Selecione um tipo de material.",
                "table_missing": "A tabela '{tabela}' não existe.",
                "table_missing_schema": "Tabela '{tabela}' não existe no schema atual.",
                "table_not_found": "Tabela '{tabela}' não encontrada.",
                "code_not_found": "Código não encontrado: {codigo}",
                "code_loaded": "Código encontrado e carregado: {codigo}",
                "items_loaded": "{quantidade} itens carregados.",
                "no_matching_columns": "Nenhuma coluna da Treeview corresponde às colunas do banco.",
                "columns_list_error": "Não foi possível listar colunas de {tabela}.",
                "item_load_error": "Falha ao carregar item selecionado:\n{erro}",
                "item_id_not_found": "Item ID {item_id} não encontrado em '{tabela}'.",
                "item_loaded": "Item ID {item_id} carregado de {tabela}.",
                "no_type_selected": "Nenhum tipo de material selecionado.",
                "fields_cleared": "Campos limpos.",
                "invalid_date": "Data inválida",
                "invalid_date_detail": "Data inválida: '{valor}'. Use DD/MM/AAAA.",
                "invalid_unit": "Unidade inválida",
                "invalid_unit_detail": "Não é permitido usar números no campo 'Unidade' para este tipo.\nUse apenas letras (ex: unidades, caixas, pacotes).",
                "invalid_unit_realtime": "❌ Não é possível inserir números no campo 'Unidade'. Use apenas letras.",
                "tooltip_unit": "Ex: unidades, caixas, pacotes... (sem números)",
                "no_valid_data": "Nenhum dado válido foi informado.",
                "lower_than_current_stock": "Valor menor que o estoque atual",
                "use_output_page": "Utilize a página de Saída para baixa em estoque.",
                "no_change": "Sem alteração",
                "same_values": "Os valores informados são iguais aos valores atuais do estoque.",
                "stock_updated": "✅ Estoque atualizado",
                "stock_updated_ok": "Item já existente atualizado com sucesso.",
                "stock_updated_detail": "Quantidade/medidas atualizadas com sucesso!\n\n📌 Código: {codigo}\n🎨 Cor: {cor}\n{linhas}",
                "saved_title": "✅ Salvo",
                "saved_message": "✅ Cadastro realizado com sucesso!\n\n📌 Código: {codigo}\n📝 Descrição: {descricao}\n🎨 Cor: {cor}\n📦 Quantidade: {quantidade}",
                "save_error_title": "Erro ao gravar no banco",
                "save_error_message": "Ocorreu um erro ao gravar no banco:\n{erro}",
                "col_id": "ID",
                "col_descricao": "Descrição",
                "col_codigo": "Código",
                "col_fornecedor": "Fornecedor",
                "col_composicao": "Composição",
                "col_cor": "Cor",
                "col_metros": "Metros",
                "col_kilos": "Kilos",
                "col_data_entrada": "Data Entrada",
                "col_observacoes": "Observações",
                "col_tipo": "Tipo",
                "col_quantidade": "Quantidade",
                "col_unidade": "Unidade",
                "col_localizacao": "Localização",
                "type_tecidos": "Tecidos",
                "type_aviamentos": "Aviamentos",
                "type_insumos": "Insumos",
                "type_escritorio": "Escritório",
                "type_limpeza": "Limpeza",
                "type_outros": "Outros",
                "col_percentual_estoque": "% Estoque",
                "col_status_estoque": "Status Estoque",
                "col_referencia_estoque": "Referência",
                "col_estoque_ideal": "Estoque Ideal",
                "col_estoque_minimo": "Estoque Mínimo",
                "col_estoque_critico": "Estoque Crítico",
                "reference_base": "Base da Referência",
                "reference_base_hint": "Para tecidos, a referência será comparada por esta base.",
                "reference_base_metros": "Metros",
                "reference_base_kilos": "Kilos",
                "status_critical": "Crítico",
                "status_low": "Baixo",
                "status_normal": "Normal",
                "status_no_reference": "Sem referência",
                "stock_rule_summary": "Referência real aplicada | Críticos: {criticos} | Baixos: {baixos} | Normais: {normais}",
            },
            "en_US": {
                "title": "Stock Entry",
                "status_ready": "Ready to edit: {tipo}",
                "register_entry": "Register Entry",
                "clear_fields": "Clear Fields",
                "search_code": "Search Code:",
                "search_code_placeholder": "Enter a code to search",
                "db_connection_error": "CONNECTION ERROR:\n{erro}",
                "warning": "Warning",
                "error": "Error",
                "success": "Success",
                "load_error": "Loading Error",
                "type_required": "Select a material type.",
                "table_missing": "Table '{tabela}' does not exist.",
                "table_missing_schema": "Table '{tabela}' does not exist in the current schema.",
                "table_not_found": "Table '{tabela}' not found.",
                "code_not_found": "Code not found: {codigo}",
                "code_loaded": "Code found and loaded: {codigo}",
                "items_loaded": "{quantidade} item(s) loaded.",
                "no_matching_columns": "No Treeview columns match the database columns.",
                "columns_list_error": "Could not list columns from {tabela}.",
                "item_load_error": "Failed to load selected item:\n{erro}",
                "item_id_not_found": "Item ID {item_id} not found in '{tabela}'.",
                "item_loaded": "Item ID {item_id} loaded from {tabela}.",
                "no_type_selected": "No material type selected.",
                "fields_cleared": "Fields cleared.",
                "invalid_date": "Invalid date",
                "invalid_date_detail": "Invalid date: '{valor}'. Use MM/DD/YYYY or YYYY-MM-DD.",
                "invalid_unit": "Invalid unit",
                "invalid_unit_detail": "Numbers are not allowed in the 'Unit' field for this type.\nUse letters only (e.g. units, boxes, packages).",
                "invalid_unit_realtime": "❌ Numbers are not allowed in the 'Unit' field. Use letters only.",
                "tooltip_unit": "Ex: units, boxes, packages... (no numbers)",
                "no_valid_data": "No valid data was entered.",
                "lower_than_current_stock": "Value lower than current stock",
                "use_output_page": "Use the Output page to decrease stock.",
                "no_change": "No change",
                "same_values": "The entered values are the same as the current stock values.",
                "stock_updated": "✅ Stock updated",
                "stock_updated_ok": "Existing item updated successfully.",
                "stock_updated_detail": "Quantity/measures updated successfully!\n\n📌 Code: {codigo}\n🎨 Color: {cor}\n{linhas}",
                "saved_title": "✅ Saved",
                "saved_message": "✅ Entry saved successfully!\n\n📌 Code: {codigo}\n📝 Description: {descricao}\n🎨 Color: {cor}\n📦 Quantity: {quantidade}",
                "save_error_title": "Error saving to database",
                "save_error_message": "An error occurred while saving to the database:\n{erro}",
                "col_id": "ID",
                "col_descricao": "Description",
                "col_codigo": "Code",
                "col_fornecedor": "Supplier",
                "col_composicao": "Composition",
                "col_cor": "Color",
                "col_metros": "Meters",
                "col_kilos": "Kilos",
                "col_data_entrada": "Entry Date",
                "col_observacoes": "Notes",
                "col_tipo": "Type",
                "col_quantidade": "Quantity",
                "col_unidade": "Unit",
                "col_localizacao": "Location",
                "type_tecidos": "Fabrics",
                "type_aviamentos": "Trims",
                "type_insumos": "Supplies",
                "type_escritorio": "Office",
                "type_limpeza": "Cleaning",
                "type_outros": "Others",
                "col_percentual_estoque": "% Stock",
                "col_status_estoque": "Stock Status",
                "col_referencia_estoque": "Reference",
                "col_estoque_ideal": "Ideal Stock",
                "col_estoque_minimo": "Minimum Stock",
                "col_estoque_critico": "Critical Stock",
                "reference_base": "Reference Base",
                "reference_base_hint": "For fabrics, the reference will be compared using this base.",
                "reference_base_metros": "Meters",
                "reference_base_kilos": "Kilos",
                "status_critical": "Critical",
                "status_low": "Low",
                "status_normal": "Normal",
                "status_no_reference": "No reference",
                "stock_rule_summary": "Real reference applied | Critical: {criticos} | Low: {baixos} | Normal: {normais}",
            },
            "es_ES": {
                "title": "Entrada de Stock",
                "status_ready": "Listo para editar: {tipo}",
                "register_entry": "Registrar Entrada",
                "clear_fields": "Limpiar Campos",
                "search_code": "Buscar Código:",
                "search_code_placeholder": "Escriba un código para buscar",
                "db_connection_error": "ERROR DE CONEXIÓN:\n{erro}",
                "warning": "Aviso",
                "error": "Error",
                "success": "Éxito",
                "load_error": "Error de Carga",
                "type_required": "Seleccione un tipo de material.",
                "table_missing": "La tabla '{tabela}' no existe.",
                "table_missing_schema": "La tabla '{tabela}' no existe en el esquema actual.",
                "table_not_found": "Tabla '{tabela}' no encontrada.",
                "code_not_found": "Código no encontrado: {codigo}",
                "code_loaded": "Código encontrado y cargado: {codigo}",
                "items_loaded": "{quantidade} elemento(s) cargado(s).",
                "no_matching_columns": "Ninguna columna de la Treeview coincide con las columnas de la base.",
                "columns_list_error": "No fue posible listar columnas de {tabela}.",
                "item_load_error": "No fue posible cargar el elemento seleccionado:\n{erro}",
                "item_id_not_found": "Elemento ID {item_id} no encontrado en '{tabela}'.",
                "item_loaded": "Elemento ID {item_id} cargado desde {tabela}.",
                "no_type_selected": "Ningún tipo de material seleccionado.",
                "fields_cleared": "Campos limpiados.",
                "invalid_date": "Fecha inválida",
                "invalid_date_detail": "Fecha inválida: '{valor}'. Use DD/MM/AAAA.",
                "invalid_unit": "Unidad inválida",
                "invalid_unit_detail": "No se permiten números en el campo 'Unidad' para este tipo.\nUse solo letras (ej: unidades, cajas, paquetes).",
                "invalid_unit_realtime": "❌ No se permiten números en el campo 'Unidad'. Use solo letras.",
                "tooltip_unit": "Ej: unidades, cajas, paquetes... (sin números)",
                "no_valid_data": "No se informó ningún dato válido.",
                "lower_than_current_stock": "Valor menor que el stock actual",
                "use_output_page": "Utilice la página de Salida para bajar stock.",
                "no_change": "Sin cambios",
                "same_values": "Los valores informados son iguales a los valores actuales del stock.",
                "stock_updated": "✅ Stock actualizado",
                "stock_updated_ok": "El elemento existente fue actualizado con éxito.",
                "stock_updated_detail": "¡Cantidad/medidas actualizadas con éxito!\n\n📌 Código: {codigo}\n🎨 Color: {cor}\n{linhas}",
                "saved_title": "✅ Guardado",
                "saved_message": "✅ ¡Registro realizado con éxito!\n\n📌 Código: {codigo}\n📝 Descripción: {descricao}\n🎨 Color: {cor}\n📦 Cantidad: {quantidade}",
                "save_error_title": "Error al guardar en la base",
                "save_error_message": "Ocurrió un error al guardar en la base de datos:\n{erro}",
                "col_id": "ID",
                "col_descricao": "Descripción",
                "col_codigo": "Código",
                "col_fornecedor": "Proveedor",
                "col_composicao": "Composición",
                "col_cor": "Color",
                "col_metros": "Metros",
                "col_kilos": "Kilos",
                "col_data_entrada": "Fecha de Entrada",
                "col_observacoes": "Observaciones",
                "col_tipo": "Tipo",
                "col_quantidade": "Cantidad",
                "col_unidade": "Unidad",
                "col_localizacao": "Ubicación",
                "type_tecidos": "Tejidos",
                "type_aviamentos": "Avíos",
                "type_insumos": "Insumos",
                "type_escritorio": "Oficina",
                "type_limpeza": "Limpieza",
                "type_outros": "Otros",
                "col_percentual_estoque": "% Stock",
                "col_status_estoque": "Estado Stock",
                "col_referencia_estoque": "Referencia",
                "col_estoque_ideal": "Stock Ideal",
                "col_estoque_minimo": "Stock Mínimo",
                "col_estoque_critico": "Stock Crítico",
                "reference_base": "Base de Referencia",
                "reference_base_hint": "Para tejidos, la referencia se comparará usando esta base.",
                "reference_base_metros": "Metros",
                "reference_base_kilos": "Kilos",
                "status_critical": "Crítico",
                "status_low": "Bajo",
                "status_normal": "Normal",
                "status_no_reference": "Sin referencia",
                "stock_rule_summary": "Referencia real aplicada | Críticos: {criticos} | Bajos: {baixos} | Normales: {normais}",
            },
        }
        base = textos.get(idioma, textos["pt_BR"])
        return base.get(chave, chave).format(**kwargs)

    def _get_tipo_texto(self, tipo_interno):
        mapa = {
            "Tecidos": "type_tecidos",
            "Aviamentos": "type_aviamentos",
            "Insumos": "type_insumos",
            "Escritorio": "type_escritorio",
            "Limpeza": "type_limpeza",
            "Outros": "type_outros",
        }
        return self._get_text(mapa.get(tipo_interno, tipo_interno))

    def _get_tipo_por_texto(self, texto_exibido):
        for tipo in self.tipos:
            if texto_exibido == self._get_tipo_texto(tipo):
                return tipo
        return texto_exibido if texto_exibido in self.tipos else self.tipos[0]

    def _get_date_pattern(self):
        idioma = self._get_idioma_atual()
        return {
            "pt_BR": "%d/%m/%Y",
            "en_US": "%m/%d/%Y",
            "es_ES": "%d/%m/%Y",
        }.get(idioma, "%d/%m/%Y")

    def _get_datetime_pattern(self):
        idioma = self._get_idioma_atual()
        return {
            "pt_BR": "%d/%m/%Y %H:%M",
            "en_US": "%m/%d/%Y %I:%M %p",
            "es_ES": "%d/%m/%Y %H:%M",
        }.get(idioma, "%d/%m/%Y %H:%M")

    def _parse_date_text(self, texto):
        s = (texto or "").strip()
        if not s:
            return date.today()

        formatos = ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"]
        if self._get_idioma_atual() == "en_US":
            formatos = ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"]

        for fmt in formatos:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue

        raise ValueError(self._get_text("invalid_date_detail", valor=s))

    def _formatar_data_localizada(self, valor):
        if valor in (None, ""):
            return ""

        if isinstance(valor, datetime):
            if valor.hour == 0 and valor.minute == 0 and valor.second == 0:
                return valor.strftime(self._get_date_pattern())
            return valor.strftime(self._get_datetime_pattern())

        if isinstance(valor, date):
            return valor.strftime(self._get_date_pattern())

        texto = str(valor).strip()
        formatos = (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
        )
        for fmt in formatos:
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

    def _texto_coluna(self, coluna):
        mapa = {
            "id": "col_id",
            "descricao": "col_descricao",
            "codigo": "col_codigo",
            "fornecedor": "col_fornecedor",
            "composicao": "col_composicao",
            "cor": "col_cor",
            "metros": "col_metros",
            "kilos": "col_kilos",
            "data_entrada": "col_data_entrada",
            "observacoes": "col_observacoes",
            "tipo": "col_tipo",
            "quantidade": "col_quantidade",
            "unidade": "col_unidade",
            "localizacao": "col_localizacao",
            "estoque_ideal": "col_estoque_ideal",
            "estoque_minimo": "col_estoque_minimo",
            "estoque_critico": "col_estoque_critico",
            "percentual_estoque": "col_percentual_estoque",
            "status_estoque": "col_status_estoque",
            "referencia_estoque": "col_referencia_estoque",
        }
        return self._get_text(mapa.get(coluna, coluna))

    def _to_decimal(self, valor):
        try:
            if isinstance(valor, Decimal):
                return valor
            if isinstance(valor, (int, float)):
                return Decimal(str(valor))
            s = str(valor or "").strip()
            if not s:
                return Decimal("0")
            if "," in s and "." in s:
                s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                s = s.replace(",", ".")
            return Decimal(s)
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")

    def _normalizar_base_referencia_tecido(self, valor):
        v = str(valor or "").strip().lower()
        if v in ("kg", "quilo", "quilos", "kilo", "kilos"):
            return "kilos"
        return "metros"

    def _obter_base_referencia_tecido(self, item=None):
        if isinstance(item, dict):
            unidade = item.get("unidade")
            if unidade not in (None, ""):
                return self._normalizar_base_referencia_tecido(unidade)
        return self._normalizar_base_referencia_tecido(self.tecido_referencia_var.get())

    def _obter_metrica_item(self, item, tipo):
        if tipo == "Tecidos":
            base = self._obter_base_referencia_tecido(item)
            if base == "kilos":
                return self._to_decimal(item.get("kilos", 0)), "kilos"
            return self._to_decimal(item.get("metros", 0)), "metros"
        for campo in self._metric_column_by_type.get(tipo, ("quantidade",)):
            return self._to_decimal(item.get(campo, 0)), campo
        return Decimal("0"), "quantidade"

    def _classificar_estoque_real(self, valor_atual, estoque_minimo, estoque_critico):
        if estoque_critico > 0 and valor_atual <= estoque_critico:
            return self._get_text("status_critical"), "critico"
        if estoque_minimo > 0 and valor_atual <= estoque_minimo:
            return self._get_text("status_low"), "baixo"
        return self._get_text("status_normal"), "normal"

    def _enriquecer_dados_com_referencia_real(self, dados, tipo):
        contagem = {"critico": 0, "baixo": 0, "normal": 0}
        for item in dados:
            valor_atual, campo_base = self._obter_metrica_item(item, tipo)
            estoque_ideal = self._to_decimal(item.get("estoque_ideal", 0))
            estoque_minimo = self._to_decimal(item.get("estoque_minimo", 0))
            estoque_critico = self._to_decimal(item.get("estoque_critico", 0))

            item["__valor_estoque__"] = valor_atual
            item["__campo_estoque__"] = campo_base
            item["referencia_estoque"] = estoque_ideal

            if estoque_ideal <= 0:
                item["percentual_estoque"] = Decimal("0")
                item["status_estoque"] = self._get_text("status_no_reference")
                item["__status_tag__"] = "sem_referencia"
                continue

            percentual = Decimal("0")
            if estoque_ideal > 0:
                percentual = (valor_atual / estoque_ideal) * Decimal("100")
            percentual = min(percentual, Decimal("999.99"))

            status_texto, status_tag = self._classificar_estoque_real(valor_atual, estoque_minimo, estoque_critico)
            item["percentual_estoque"] = percentual
            item["status_estoque"] = status_texto
            item["__status_tag__"] = status_tag
            contagem[status_tag] += 1

        return dados, contagem

    def refresh_texts(self):
        atual = self._last_tipo_interno
        if "title_label" in self._ui_refs:
            self._ui_refs["title_label"].configure(text=self._get_text("title"))
        if "type_menu" in self._ui_refs:
            self._ui_refs["type_menu"].configure(values=[self._get_tipo_texto(t) for t in self.tipos])
            self.tipo_var.set(self._get_tipo_texto(atual))
        if "register_button" in self._ui_refs:
            self._ui_refs["register_button"].configure(text=self._get_text("register_entry"))
        if "clear_button" in self._ui_refs:
            self._ui_refs["clear_button"].configure(text=self._get_text("clear_fields"))
        self.configurar_tabela(atual)
        self.criar_campos_entrada(atual)
        self.status_label.configure(text=self._get_text("status_ready", tipo=self._get_tipo_texto(atual)))

    # =========================================================
    # TEMA / UI
    # =========================================================
    def obter_cores_por_tema(self):
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

    def setup_ui(self):
        self.obter_cores_por_tema()

        top_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        top_frame.pack(fill="x", padx=10, pady=10)

        self._ui_refs["title_label"] = ctk.CTkLabel(
            top_frame,
            text=self._get_text("title"),
            font=("Arial", 18, "bold"),
            text_color=self.cor_texto,
        )
        self._ui_refs["title_label"].pack(side="left", padx=10)

        self.tipo_var = ctk.StringVar(value=self._get_tipo_texto("Tecidos"))
        self._ui_refs["type_menu"] = ctk.CTkOptionMenu(
            top_frame,
            variable=self.tipo_var,
            values=[self._get_tipo_texto(t) for t in self.tipos],
            command=self.atualizar_interface,
            width=200,
            fg_color=self.cor_secundaria,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
        )
        self._ui_refs["type_menu"].pack(side="right", padx=10, fill="x", expand=True)

        self.campos_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        self.campos_frame.pack(fill="both", expand=True, padx=10, pady=10)

        button_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        button_frame.pack(fill="x", padx=10, pady=5)

        self._ui_refs["register_button"] = ctk.CTkButton(
            button_frame,
            text=self._get_text("register_entry"),
            command=self.salvar_entrada,
        )
        self._ui_refs["register_button"].pack(side="left", padx=5)

        self._ui_refs["clear_button"] = ctk.CTkButton(
            button_frame,
            text=self._get_text("clear_fields"),
            command=self.limpar_campos,
        )
        self._ui_refs["clear_button"].pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.pack(pady=5)

        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.configurar_treeview_theme()

        self.tree = ttk.Treeview(self.tree_frame, show="headings")
        self.tree.pack(fill="both", expand=True)

        # CHAMADA SEGURA
        if hasattr(self, "_aplicar_estilo_tags_treeview"):
            self._aplicar_estilo_tags_treeview()

        self.tree.bind("<Double-1>", self.carregar_item_selecionado)

    def configurar_treeview_theme(self):
        self.style = ttk.Style()
        self.style.theme_use("default")
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

        self.style.configure(
            "Custom.Treeview",
            background=cor_fundo,
            foreground=cor_texto,
            fieldbackground=cor_campo,
            borderwidth=0,
            highlightthickness=0,
            rowheight=25,
        )
        self.style.configure(
            "Custom.Treeview.Heading",
            background=self.cor_primaria,
            foreground=cor_texto,
            relief="flat",
            borderwidth=1,
            font=("Arial", 10, "bold"),
        )
        self.style.map(
            "Custom.Treeview",
            background=[("selected", cor_selecao)],
            foreground=[("selected", "white")],
        )

    # =========================================================
    # FLUXO DA PÁGINA
    # =========================================================
    def atualizar_interface(self, tipo_selecionado: str):
        tipo_interno = self._get_tipo_por_texto(tipo_selecionado)
        self._last_tipo_interno = tipo_interno
        self.configurar_treeview_theme()
        self.tipo_var.set(self._get_tipo_texto(tipo_interno))
        self.criar_campos_entrada(tipo_interno)
        self.configurar_tabela(tipo_interno)
        self.carregar_dados_existente()
        self.status_label.configure(
            text=self._get_text("status_ready", tipo=self._get_tipo_texto(tipo_interno)),
            text_color=self.cor_texto,
        )

    def criar_campos_entrada(self, tipo: str):
        self.obter_cores_por_tema()

        for widget in self.campos_frame.winfo_children():
            widget.destroy()
        self.entries.clear()

        placeholders = {
            "metros": "0,00",
            "kilos": "0,00",
            "quantidade": "0,00",
            "data_entrada": date.today().strftime(self._get_date_pattern()),
        }

        campos = self.campos_por_tipo.get(tipo, [])

        for campo in campos:
            frame = ctk.CTkFrame(self.campos_frame, fg_color=self.cor_fundo)
            frame.pack(fill="x", padx=5, pady=3)

            label_text = self._texto_coluna(campo) + ":"
            ctk.CTkLabel(frame, text=label_text, width=150, anchor="e", text_color=self.cor_texto).pack(side="left", padx=5)

            if campo in ["descricao", "observacoes"]:
                widget = ctk.CTkTextbox(
                    frame,
                    height=60 if campo == "observacoes" else 40,
                    fg_color=self.cor_secundaria,
                    border_color=self.cor_borda,
                    text_color=self.cor_texto_entry,
                    border_width=1,
                )
                widget.pack(side="left", fill="x", expand=True)
                self.entries[campo] = widget
            else:
                widget = ctk.CTkEntry(
                    frame,
                    placeholder_text=placeholders.get(campo, ""),
                    fg_color=self.cor_secundaria,
                    border_color=self.cor_borda,
                    text_color=self.cor_texto_entry,
                    placeholder_text_color=self.cor_placeholder,
                    border_width=1,
                )

                if campo == "unidade" and tipo in ["Insumos", "Escritorio", "Limpeza", "Outros"]:
                    def validar_unidade(text):
                        if text == "":
                            return True
                        if any(char.isdigit() for char in text):
                            return False
                        return all(char.isalpha() or char.isspace() or char in "-/()" for char in text)

                    def on_unidade_change(*args):
                        texto = unidade_var.get()
                        if not validar_unidade(texto):
                            current_text = unidade_var.get()
                            if len(current_text) > 0:
                                unidade_var.set(current_text[:-1])

                            self.status_label.configure(
                                text=self._get_text("invalid_unit_realtime"),
                                text_color="red",
                            )
                            self.after(
                                3000,
                                lambda: self.status_label.configure(
                                    text=self._get_text("status_ready", tipo=self._get_tipo_texto(tipo)),
                                    text_color=self.cor_texto,
                                ),
                            )
                            widget.configure(border_color="red")
                            self.after(2000, lambda: widget.configure(border_color=self.cor_borda))
                        else:
                            widget.configure(border_color=self.cor_borda)

                    unidade_var = ctk.StringVar()
                    widget.configure(textvariable=unidade_var)
                    unidade_var.trace_add("write", on_unidade_change)
                    widget.configure(placeholder_text=self._get_text("tooltip_unit"))

                widget.pack(side="left", fill="x", expand=True)
                self.entries[campo] = widget

        if "data_entrada" in self.entries:
            self.entries["data_entrada"].insert(0, date.today().strftime(self._get_date_pattern()))

        if tipo == "Tecidos":
            self._criar_seletor_base_referencia_tecido()
            self.adicionar_pesquisa_codigo()

        self.status_label.configure(
            text=self._get_text("status_ready", tipo=self._get_tipo_texto(tipo)),
            text_color=self.cor_texto,
        )

    def _criar_seletor_base_referencia_tecido(self):
        frame = ctk.CTkFrame(self.campos_frame, fg_color=self.cor_fundo)
        frame.pack(fill="x", padx=5, pady=3)

        ctk.CTkLabel(
            frame,
            text=self._get_text("reference_base") + ":",
            width=150,
            anchor="e",
            text_color=self.cor_texto,
        ).pack(side="left", padx=5)

        valores = [
            self._get_text("reference_base_metros"),
            self._get_text("reference_base_kilos"),
        ]
        valor_atual = self._normalizar_base_referencia_tecido(self.tecido_referencia_var.get())
        exibicao = self._get_text("reference_base_metros") if valor_atual == "metros" else self._get_text("reference_base_kilos")
        self.tecido_referencia_exibicao_var = ctk.StringVar(value=exibicao)

        def ao_mudar(valor):
            self.tecido_referencia_var.set(
                "kilos" if valor == self._get_text("reference_base_kilos") else "metros"
            )
            self.carregar_dados_existente()

        seletor = ctk.CTkOptionMenu(
            frame,
            variable=self.tecido_referencia_exibicao_var,
            values=valores,
            command=ao_mudar,
            width=220,
            fg_color=self.cor_secundaria,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover,
        )
        seletor.pack(side="left", padx=5)

        ctk.CTkLabel(
            frame,
            text=self._get_text("reference_base_hint"),
            text_color=self.cor_texto,
            anchor="w",
        ).pack(side="left", padx=10)

    def configurar_tabela(self, tipo: str):

        colunas_desejadas = ["id"] + self.campos_por_tipo.get(tipo, []) + ["referencia_estoque", "percentual_estoque", "status_estoque"]
        self._column_keys = list(colunas_desejadas)
        self.tree["columns"] = tuple(colunas_desejadas)

        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
            self.tree.column(col, width=0)

        for col in colunas_desejadas:
            if col == "id":
                largura = 50
            elif col in ("percentual_estoque", "status_estoque", "referencia_estoque"):
                largura = 130
            else:
                largura = 120
            self.tree.heading(col, text=self._texto_coluna(col))
            self.tree.column(col, width=largura, stretch=True, anchor="w")

    def adicionar_pesquisa_codigo(self):
        frame = ctk.CTkFrame(self.campos_frame, fg_color=self.cor_fundo)
        frame.pack(fill="x", padx=5, pady=3)

        ctk.CTkLabel(
            frame,
            text=self._get_text("search_code"),
            width=150,
            anchor="e",
            text_color=self.cor_texto,
        ).pack(side="left", padx=5)

        pesquisa_entry = ctk.CTkEntry(
            frame,
            placeholder_text=self._get_text("search_code_placeholder"),
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            placeholder_text_color=self.cor_placeholder,
        )
        pesquisa_entry.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkButton(
            frame,
            text="🔍",
            width=30,
            command=lambda: self.pesquisar_codigo(pesquisa_entry.get()),
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
        ).pack(side="left")

        self.entries["pesquisa_codigo"] = pesquisa_entry

    def pesquisar_codigo(self, codigo: str):
        if not codigo.strip():
            return

        tipo = self._last_tipo_interno
        schema = getattr(db, "schema", "opera")
        tabela_nome = f"estoque_{tipo.lower()}"
        tabela_qual = f"{schema}.{tabela_nome}"

        if not db.table_exists(tabela_nome):
            messagebox.showwarning(self._get_text("warning"), self._get_text("table_not_found", tabela=tabela_qual))
            return

        item = db.fetch_one(
            f"SELECT * FROM {tabela_qual} WHERE codigo ILIKE %s ORDER BY id DESC LIMIT 1",
            (f"%{codigo.strip()}%",),
        )
        if not item:
            self.status_label.configure(text=self._get_text("code_not_found", codigo=codigo), text_color="orange")
            return

        for campo, widget in self.entries.items():
            if campo in item and campo != "pesquisa_codigo":
                valor = self.formatar_valor(item[campo], campo)
                if isinstance(widget, ctk.CTkTextbox):
                    widget.delete("1.0", "end")
                    widget.insert("1.0", valor)
                else:
                    widget.delete(0, "end")
                    widget.insert(0, valor)

        if tipo == "Tecidos":
            base = self._obter_base_referencia_tecido(item)
            self.tecido_referencia_var.set(base)
            if hasattr(self, "tecido_referencia_exibicao_var"):
                self.tecido_referencia_exibicao_var.set(
                    self._get_text("reference_base_kilos") if base == "kilos" else self._get_text("reference_base_metros")
                )

        self.status_label.configure(text=self._get_text("code_loaded", codigo=item["codigo"]), text_color="green")

    def carregar_dados_existente(self):
        import os
        from unicodedata import normalize

        def _norm(s: str) -> str:
            if s is None:
                return ""
            s = str(s)
            try:
                s = normalize("NFKD", s)
                s = "".join(ch for ch in s if ord(ch) < 128)
            except Exception:
                pass
            return "".join(ch for ch in s.lower() if ch.isalnum())

        aliases = {
            "id": "id",
            "descricao": "descricao",
            "codigo": "codigo",
            "fornecedor": "fornecedor",
            "composicao": "composicao",
            "cor": "cor",
            "metros": "metros",
            "kilos": "kilos",
            "kg": "kilos",
            "dataentrada": "data_entrada",
            "observacoes": "observacoes",
            "quantidade": "quantidade",
            "qtd": "quantidade",
            "unidade": "unidade",
            "tipo": "tipo",
            "localizacao": "localizacao",
            "estoqueideal": "estoque_ideal",
            "estoqueminimo": "estoque_minimo",
            "estoquecritico": "estoque_critico",
            "createdat": "created_at",
            "updatedat": "updated_at",
        }

        def _get_schema():
            for getter in ("get_schema", "schema", "get_current_schema"):
                if hasattr(db, getter):
                    try:
                        v = getattr(db, getter)
                        v = v() if callable(v) else v
                        if v:
                            return str(v)
                    except Exception:
                        pass
            return os.getenv("OPERA_PG_SCHEMA", "opera")

        def _table_exists(tab_qual: str, schema: str, nome: str) -> bool:
            try:
                if getattr(db, "table_exists", None) and db.table_exists(tab_qual):
                    return True
            except Exception:
                pass
            try:
                r = db.fetch_one(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema=%s AND table_name=%s
                    ) AS ok
                    """,
                    [schema, nome],
                )
                if r and r.get("ok"):
                    return True
            except Exception:
                pass
            try:
                r = db.fetch_one("SELECT to_regclass(%s) IS NOT NULL AS ok", [tab_qual])
                return bool(r and r.get("ok"))
            except Exception:
                return False

        try:
            self.tree.delete(*self.tree.get_children())
        except Exception:
            pass

        tipo_raw = self._last_tipo_interno
        tabela_nome = f"estoque_{tipo_raw.lower()}"
        schema = _get_schema()
        tabela_qual = f"{schema}.{tabela_nome}"

        try:
            db.execute(f"SET search_path TO {schema}, public")
        except Exception:
            pass

        if not _table_exists(tabela_qual, schema, tabela_nome):
            self.status_label.configure(text=self._get_text("table_missing", tabela=tabela_qual), text_color="orange")
            return

        cols_tree = list(self.tree["columns"])
        if not cols_tree:
            return
        cols_tree_norm = [_norm(c) for c in cols_tree]

        try:
            rows = db.fetch_all(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema=%s AND table_name=%s
                """,
                [schema, tabela_nome],
            ) or []
            cols_db = {str(r["column_name"]) for r in rows}
        except Exception:
            cols_db = set()

        if not cols_db:
            self.status_label.configure(
                text=self._get_text("columns_list_error", tabela=tabela_qual),
                text_color="orange",
            )
            return

        tree_to_db = {}
        for i, c_norm in enumerate(cols_tree_norm):
            if c_norm in aliases:
                cand = aliases[c_norm]
                if cand == "quantidade" and "quantidade" not in cols_db and "qtd" in cols_db:
                    tree_to_db[cols_tree[i]] = "qtd"
                else:
                    tree_to_db[cols_tree[i]] = cand

        for i, c in enumerate(cols_tree):
            if c in tree_to_db:
                continue
            normed = _norm(c)
            if normed in cols_db:
                tree_to_db[c] = normed

        validos = [c for c in cols_tree if c in tree_to_db and tree_to_db[c] in cols_db]
        if not validos:
            self.status_label.configure(text=self._get_text("no_matching_columns"), text_color="orange")
            return

        order_col = "data_entrada" if "data_entrada" in cols_db else ("id" if "id" in cols_db else None)
        order_sql = f" ORDER BY {order_col} DESC" if order_col else ""

        select_cols = list({tree_to_db[c] for c in validos})
        if "id" in cols_db and "id" not in select_cols:
            select_cols.insert(0, "id")

        try:
            sql = f"SELECT {', '.join(select_cols)} FROM {tabela_qual}{order_sql}"
            dados = db.fetch_all(sql) or []
            dados, contagem = self._enriquecer_dados_com_referencia_real(dados, tipo_raw)
            self._aplicar_estilo_tags_treeview()
            for item in dados:
                linha = []
                for col_label in cols_tree:
                    if col_label in ("percentual_estoque", "status_estoque", "referencia_estoque"):
                        val = item.get(col_label)
                        linha.append(self.formatar_valor(val, col_label))
                        continue
                    col_db = tree_to_db.get(col_label)
                    val = item.get(col_db) if (col_db and isinstance(item, dict)) else None
                    linha.append(self.formatar_valor(val, col_db or col_label))
                iid = item.get("id") if isinstance(item, dict) and "id" in item else ""
                self.tree.insert("", "end", iid=iid, values=linha, tags=(item.get("__status_tag__", "sem_referencia"),))

            self.status_label.configure(
                text=self._get_text(
                    "stock_rule_summary",
                    criticos=contagem.get("critico", 0),
                    baixos=contagem.get("baixo", 0),
                    normais=contagem.get("normal", 0),
                ),
                text_color="green",
            )
        except Exception as e:
            messagebox.showerror(self._get_text("load_error"), self._get_text("save_error_message", erro=e))

    def carregar_item_selecionado(self, event):
        try:
            selecao = self.tree.selection()
            if not selecao:
                return
            item_id = selecao[0]
            if not item_id:
                return

            tipo = self._last_tipo_interno
            if not tipo:
                messagebox.showwarning(self._get_text("warning"), self._get_text("no_type_selected"))
                return

            schema = getattr(db, "schema", "opera")
            tabela_nome = f"estoque_{tipo.lower()}"
            tabela_qual = f"{schema}.{tabela_nome}"

            if not db.table_exists(tabela_nome):
                messagebox.showerror(self._get_text("error"), self._get_text("table_missing_schema", tabela=tabela_qual))
                return

            item_completo = db.fetch_one(f"SELECT * FROM {tabela_qual} WHERE id = %s", (item_id,))
            if not item_completo:
                messagebox.showerror(self._get_text("error"), self._get_text("item_id_not_found", item_id=item_id, tabela=tabela_qual))
                return

            self.limpar_campos()

            for campo, widget in self.entries.items():
                if campo not in item_completo:
                    continue
                valor = self.formatar_valor(item_completo[campo], campo)
                if isinstance(widget, ctk.CTkTextbox):
                    widget.delete("1.0", "end")
                    widget.insert("1.0", valor)
                else:
                    widget.delete(0, "end")
                    widget.insert(0, valor)

            if tipo == "Tecidos":
                base = self._obter_base_referencia_tecido(item_completo)
                self.tecido_referencia_var.set(base)
                if hasattr(self, "tecido_referencia_exibicao_var"):
                    self.tecido_referencia_exibicao_var.set(
                        self._get_text("reference_base_kilos") if base == "kilos" else self._get_text("reference_base_metros")
                    )

            self.status_label.configure(
                text=self._get_text("item_loaded", item_id=item_id, tabela=tabela_qual),
                text_color="blue",
            )
        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("item_load_error", erro=e))

    def limpar_campos(self):
        for campo, widget in self.entries.items():
            if campo == "pesquisa_codigo":
                continue
            if isinstance(widget, ctk.CTkTextbox):
                widget.delete("1.0", "end")
            else:
                widget.delete(0, "end")
        if "data_entrada" in self.entries:
            self.entries["data_entrada"].insert(0, date.today().strftime(self._get_date_pattern()))
        if self._last_tipo_interno == "Tecidos":
            self.tecido_referencia_var.set("metros")
            if hasattr(self, "tecido_referencia_exibicao_var"):
                self.tecido_referencia_exibicao_var.set(self._get_text("reference_base_metros"))
        try:
            self.tree.selection_remove(self.tree.selection())
        except Exception:
            pass
        self.status_label.configure(text=self._get_text("fields_cleared"), text_color=self.cor_texto)

    def salvar_entrada(self):
        from decimal import Decimal, InvalidOperation

        def _get_val(widget):
            try:
                if isinstance(widget, ctk.CTkTextbox):
                    return widget.get("1.0", "end-1c").strip()
                return widget.get().strip()
            except Exception:
                return ""

        def _to_decimal(valor):
            try:
                if isinstance(valor, (int, float, Decimal)):
                    return Decimal(str(valor))
                s = str(valor).strip()
                if not s:
                    return Decimal("0")
                if "," in s:
                    s = s.replace(".", "").replace(",", ".")
                    return Decimal(s)
                if "." in s:
                    parts = s.split(".")
                    if all(len(p) == 3 for p in parts[1:]):
                        s = "".join(parts)
                        return Decimal(s)
                return Decimal(s)
            except (InvalidOperation, TypeError, ValueError):
                return Decimal("0")

        def _fmt_num_local(v):
            if v is None:
                return ""
            try:
                d = v if isinstance(v, Decimal) else Decimal(str(v))
                s = format(d, "f")
                if "." in s:
                    s = s.rstrip("0").rstrip(".")
                if self._get_idioma_atual() == "en_US":
                    return s
                return s.replace(".", ",")
            except Exception:
                return str(v)

        def _validar_unidade_salvamento(unidade_texto, tipo):
            if tipo in ["Insumos", "Escritorio", "Limpeza", "Outros"] and unidade_texto:
                if any(char.isdigit() for char in unidade_texto):
                    return False
            return True

        def _get_schema():
            try:
                if hasattr(db, "get_schema"):
                    return db.get_schema()
            except Exception:
                pass
            return os.getenv("OPERA_PG_SCHEMA", "opera")

        tipo_raw = self._last_tipo_interno
        if not tipo_raw:
            messagebox.showwarning(self._get_text("warning"), self._get_text("type_required"))
            return

        tabela_nome = f"estoque_{tipo_raw.lower()}"
        schema = _get_schema()
        tabela_qual = f"{schema}.{tabela_nome}"

        if hasattr(db, "table_exists") and not db.table_exists(tabela_nome):
            messagebox.showerror(self._get_text("error"), self._get_text("table_missing", tabela=tabela_qual))
            return

        colunas_info = db.fetch_all(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            [schema, tabela_nome],
        ) or []
        colunas_db = [r["column_name"] for r in colunas_info]

        dados = {}
        cor_valor = ""
        unidade_valor = ""

        for campo, widget in self.entries.items():
            if campo == "pesquisa_codigo":
                continue

            valor = _get_val(widget)

            if campo == "cor":
                cor_valor = valor
            if campo == "unidade":
                unidade_valor = valor

            if campo not in colunas_db:
                continue

            if campo == "data_entrada":
                try:
                    dados[campo] = self._parse_date_text(valor)
                except Exception as e:
                    messagebox.showerror(self._get_text("invalid_date"), str(e))
                    return
                continue

            if campo in ["metros", "kilos", "quantidade", "estoque_ideal", "estoque_minimo", "estoque_critico"]:
                dados[campo] = _to_decimal(valor)
                continue

            if valor != "":
                dados[campo] = valor.strip()

        if "data_entrada" in colunas_db and "data_entrada" not in dados:
            dados["data_entrada"] = date.today()

        if tipo_raw == "Tecidos" and "unidade" in colunas_db:
            dados["unidade"] = self._normalizar_base_referencia_tecido(self.tecido_referencia_var.get())

        if "unidade" in colunas_db and not _validar_unidade_salvamento(unidade_valor, tipo_raw):
            messagebox.showerror(self._get_text("invalid_unit"), self._get_text("invalid_unit_detail"))
            return

        estoque_ideal = _to_decimal(dados.get("estoque_ideal", 0))
        estoque_minimo = _to_decimal(dados.get("estoque_minimo", 0))
        estoque_critico = _to_decimal(dados.get("estoque_critico", 0))
        if any(v < 0 for v in (estoque_ideal, estoque_minimo, estoque_critico)):
            messagebox.showerror(self._get_text("error"), "Os níveis de estoque não podem ser negativos.")
            return
        if estoque_ideal > 0 and estoque_minimo > estoque_ideal:
            messagebox.showerror(self._get_text("error"), "O estoque mínimo não pode ser maior que o estoque ideal.")
            return
        if estoque_minimo > 0 and estoque_critico > estoque_minimo:
            messagebox.showerror(self._get_text("error"), "O estoque crítico não pode ser maior que o estoque mínimo.")
            return

        agora = datetime.now()

        def _buscar_existente_codigo_cor():
            codigo = (dados.get("codigo") or "").strip()
            cor = (dados.get("cor") or cor_valor or "").strip()
            if not codigo or "codigo" not in colunas_db or "cor" not in colunas_db:
                return None
            try:
                return db.fetch_one(
                    f"SELECT * FROM {tabela_qual} WHERE codigo=%s AND COALESCE(cor,'')=COALESCE(%s,'') ORDER BY id DESC LIMIT 1",
                    [codigo, cor],
                )
            except Exception:
                return None

        def _campos_estoque_editados():
            campos = []
            for c in ("quantidade", "metros", "kilos"):
                if c in colunas_db and c in dados:
                    campos.append(c)
            return campos

        def _comparar_campos_estoque(existente_reg):
            campos = _campos_estoque_editados()
            atuais = {c: _to_decimal(existente_reg.get(c, 0)) for c in campos}
            novos = {c: _to_decimal(dados.get(c, 0)) for c in campos}
            return campos, atuais, novos

        if "created_at" in colunas_db and "created_at" not in dados:
            dados["created_at"] = agora
        if "updated_at" in colunas_db:
            dados["updated_at"] = agora

        if not dados:
            messagebox.showwarning(self._get_text("warning"), self._get_text("no_valid_data"))
            return

        existente = _buscar_existente_codigo_cor()
        if existente:
            campos_estoque, valores_atuais, valores_novos = _comparar_campos_estoque(existente)

            if campos_estoque:
                if any(valores_novos[c] < valores_atuais[c] for c in campos_estoque):
                    detalhes = [f"- {c}: atual {_fmt_num_local(valores_atuais[c])} | informado {_fmt_num_local(valores_novos[c])}" for c in campos_estoque]
                    messagebox.showwarning(
                        self._get_text("lower_than_current_stock"),
                        "\n".join(detalhes) + "\n\n" + self._get_text("use_output_page"),
                    )
                    return

                if all(valores_novos[c] == valores_atuais[c] for c in campos_estoque):
                    messagebox.showinfo(self._get_text("no_change"), self._get_text("same_values"))
                    return

            campos_update = []
            params_update = []
            for campo, valor in dados.items():
                if campo in ("id", "created_at"):
                    continue
                campos_update.append(f"{campo}=%s")
                params_update.append(valor)

            if "updated_at" in colunas_db and "updated_at" not in dados:
                campos_update.append("updated_at=%s")
                params_update.append(agora)

            params_update.extend([existente.get("codigo"), existente.get("cor")])
            sql_upd = f"UPDATE {tabela_qual} SET {', '.join(campos_update)} WHERE codigo=%s AND COALESCE(cor,'')=COALESCE(%s,'')"
            db.execute(sql_upd, params_update)

            linhas_campos = []
            for c in campos_estoque:
                linhas_campos.append(f"📦 {c.capitalize()} anterior: {_fmt_num_local(valores_atuais[c])}")
                linhas_campos.append(f"📦 {c.capitalize()} novo: {_fmt_num_local(valores_novos[c])}")
            if not linhas_campos:
                linhas_campos.append("📦 Item atualizado com sucesso.")

            messagebox.showinfo(
                self._get_text("stock_updated"),
                self._get_text(
                    "stock_updated_detail",
                    codigo=existente.get("codigo") or "-",
                    cor=existente.get("cor") or "-",
                    linhas="\n".join(linhas_campos),
                ),
            )
            try:
                self.carregar_dados_existente()
            except Exception:
                pass
            return

        try:
            campos = list(dados.keys())
            placeholders = ", ".join(["%s"] * len(campos))
            valores = [dados[c] for c in campos]

            sql = f"INSERT INTO {tabela_qual} ({', '.join(campos)}) VALUES ({placeholders})"
            db.execute(sql, valores)

            codigo_msg = (dados.get("codigo") or "").strip()
            desc_msg = (dados.get("descricao") or dados.get("nome") or "").strip()
            cor_msg = (dados.get("cor") or cor_valor or "").strip()

            qtd_msg = ""
            if "quantidade" in dados:
                qtd_msg = _fmt_num_local(dados.get("quantidade"))
            elif "metros" in dados or "kilos" in dados:
                metros = _fmt_num_local(dados.get("metros")) if "metros" in dados else ""
                kilos = _fmt_num_local(dados.get("kilos")) if "kilos" in dados else ""
                partes = []
                if metros not in ("", "0"):
                    partes.append(f"{metros} m")
                if kilos not in ("", "0"):
                    partes.append(f"{kilos} kg")
                qtd_msg = " / ".join(partes) if partes else "0"

            unidade_msg = (dados.get("unidade") or unidade_valor or "").strip()
            if unidade_msg and "quantidade" in dados and qtd_msg:
                qtd_msg = f"{qtd_msg} {unidade_msg}"

            messagebox.showinfo(
                self._get_text("saved_title"),
                self._get_text(
                    "saved_message",
                    codigo=codigo_msg or "-",
                    descricao=desc_msg or "-",
                    cor=cor_msg or "-",
                    quantidade=qtd_msg or "-",
                ),
            )

            try:
                self.carregar_dados_existente()
            except Exception:
                pass
            try:
                self.limpar_campos()
            except Exception:
                pass

        except Exception as e:
            msg_err = str(e)
            if "viol" in msg_err.lower() and "codigo" in msg_err.lower() and "cor" in msg_err.lower():
                existente = _buscar_existente_codigo_cor()
                if existente:
                    campos_estoque, valores_atuais, valores_novos = _comparar_campos_estoque(existente)
                    if campos_estoque and any(valores_novos[c] < valores_atuais[c] for c in campos_estoque):
                        messagebox.showwarning(self._get_text("lower_than_current_stock"), self._get_text("use_output_page"))
                        return

                    campos_update = []
                    params_update = []
                    for campo, valor in dados.items():
                        if campo in ("id", "created_at"):
                            continue
                        campos_update.append(f"{campo}=%s")
                        params_update.append(valor)
                    if "updated_at" in colunas_db and "updated_at" not in dados:
                        campos_update.append("updated_at=%s")
                        params_update.append(agora)
                    params_update.extend([existente.get("codigo"), existente.get("cor")])
                    db.execute(
                        f"UPDATE {tabela_qual} SET {', '.join(campos_update)} WHERE codigo=%s AND COALESCE(cor,'')=COALESCE(%s,'')",
                        params_update,
                    )
                    messagebox.showinfo(self._get_text("stock_updated"), self._get_text("stock_updated_ok"))
                    try:
                        self.carregar_dados_existente()
                    except Exception:
                        pass
                    return
            messagebox.showerror(self._get_text("save_error_title"), self._get_text("save_error_message", erro=e))

    def formatar_valor(self, valor, campo):
        if valor is None:
            return ""

        campo = str(campo).lower()

        if campo == "data_entrada":
            return self._formatar_data_localizada(valor)

        try:
            if campo == "codigo":
                return str(valor)

            if campo == "status_estoque":
                return str(valor)

            if campo in ("percentual_estoque",):
                dec = self._to_decimal(valor)
                if self._get_idioma_atual() == "en_US":
                    return f"{float(dec):.1f}%"
                return f"{float(dec):.1f}%".replace(".", ",")

            if campo in ("referencia_estoque", "estoque_ideal", "estoque_minimo", "estoque_critico"):
                dec = self._to_decimal(valor)
                if campo == "referencia_estoque" and dec <= 0:
                    return "-"
                return self.formatar_valor(dec, "quantidade")

            if campo in ("metros", "kilos", "quantidade"):
                from decimal import Decimal, InvalidOperation
                try:
                    dec = Decimal(str(valor))
                except (InvalidOperation, ValueError, TypeError):
                    return str(valor)

                if self._get_idioma_atual() == "en_US":
                    if dec == dec.to_integral():
                        return f"{int(dec):,}"
                    return f"{float(dec):,.3f}".rstrip("0").rstrip(".")

                if dec == dec.to_integral():
                    parte_inteira = int(dec)
                    return f"{parte_inteira:,}".replace(",", ".")
                else:
                    parte_inteira = int(dec)
                    parte_decimal = abs(dec - parte_inteira)
                    parte_inteira_str = f"{parte_inteira:,}".replace(",", ".")
                    frac_str = f"{parte_decimal:.3f}"[2:]
                    frac_str = frac_str.rstrip("0")
                    return f"{parte_inteira_str},{frac_str}"

            valor_float = float(valor)
            if self._get_idioma_atual() == "en_US":
                if abs(valor_float) <= 999 and valor_float.is_integer():
                    return f"{int(valor_float)}"
                elif abs(valor_float) <= 999:
                    return f"{valor_float:.2f}"
                else:
                    return f"{valor_float:,.3f}".rstrip("0").rstrip(".")

            if abs(valor_float) <= 999 and valor_float.is_integer():
                return f"{int(valor_float)}"
            elif abs(valor_float) <= 999:
                return f"{valor_float:.2f}".replace(".", ",")
            else:
                parte_inteira = int(valor_float)
                parte_decimal = valor_float - parte_inteira
                parte_inteira_str = f"{parte_inteira:,}".replace(",", ".")
                parte_decimal_str = f"{parte_decimal:.3f}"[1:].replace(".", ",")
                return f"{parte_inteira_str}{parte_decimal_str}"

        except Exception:
            return str(valor)


if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1200x800")
    app.title("Sistema de Entrada de Estoque")

    class SistemaMock:
        def __init__(self):
            self.idioma_atual = "pt_BR"

    try:
        db.fetch_one("SELECT 1")
        print("[OK] Conexão com o banco de dados verificada com sucesso.")
        EntradaEstoqueApp(app, sistema=SistemaMock())
    except Exception as e:
        print(f"[ERRO FATAL] Não foi possível conectar ao banco de dados: {e}")
        ctk.CTkLabel(
            app,
            text=f"ERRO DE CONEXÃO:\n{e}",
            text_color="red",
            font=("Arial", 16),
        ).pack(pady=50, padx=20)

    app.mainloop()

# --- AUTO_PAGE_TRANSLATIONS (gerado automaticamente) ---
from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support as _attach_i18n_support

AUTO_PAGE_TRANSLATIONS = {
    "EntradaEstoqueApp": {
        "pt_BR": {"title": "Entrada Estoque", "Atualizar": "Atualizar", "Filtrar": "Filtrar", "Salvar": "Salvar", "Cancelar": "Cancelar"},
        "en_US": {"title": "Entrada Estoque", "Atualizar": "Refresh", "Filtrar": "Filter", "Salvar": "Save", "Cancelar": "Cancel"},
        "es_ES": {"title": "Entrada Estoque", "Atualizar": "Actualizar", "Filtrar": "Filtrar", "Salvar": "Guardar", "Cancelar": "Cancelar"},
    },
}

for _cls_name, _map in AUTO_PAGE_TRANSLATIONS.items():
    _cls = globals().get(_cls_name)
    if isinstance(_cls, type):
        if not hasattr(_cls, "TRANSLATIONS") and not hasattr(_cls, "_TRANSLATIONS"):
            _cls.TRANSLATIONS = _map
        _attach_i18n_support(_cls, getattr(_cls, "TRANSLATIONS", getattr(_cls, "_TRANSLATIONS", _map)))
