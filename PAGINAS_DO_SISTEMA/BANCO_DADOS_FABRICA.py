# BANCO_DADOS_FABRICA_usa-es-pt.py
from PAGINAS_DO_SISTEMA.TEMAS import BotaoPadronizado
from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db

_cfg = db.load_config()

import time
from tkinter import ttk, messagebox
from PAGINAS_DO_SISTEMA.TEMAS import get_contraste_texto, is_dark_color, ajustar_hover
from tkinter import filedialog
import customtkinter as ctk

import psycopg2
import psycopg2.extras

# JESUS SEJA LOUVADO PARA TODO O SEMPRE AMEM!!!
# ============== Classes originais (UI preservada) ==============

class GerenciadorBancoDados:

    TRANSLATIONS = {
        "pt_BR": {
            "admin_indicator": "🔐 ADMIN",
            "database": "Banco:",
            "connect": "Conectar",
            "admin_button": "🔑 Admin",
            "table": "Tabela:",
            "select_table": "Selecionar Tabela",
            "refresh": "Atualizar",
            "new_table": "Nova Tabela",
            "admin_operations": "Operações Admin",
            "delete": "Excluir",
            "edit_table": "Editar Tabela",
            "sql": "SQL",
            "export": "Exportar",
            "edit": "Editar",
            "add": "Adicionar",
            "error": "Erro",
            "warning": "Aviso",
            "info": "Informação",
            "success": "Sucesso",
            "confirm_deletion": "Confirmar Exclusão",
            "no_table_selected": "Nenhuma tabela selecionada.",
            "no_record_selected": "Nenhum registro selecionado.",
            "confirm_delete_records": "Deseja realmente excluir o(s) registro(s) selecionado(s)?",
            "connection_error": "Erro na Conexão",
            "connection_failed": "Falha ao conectar:\n{erro}",
            "status_admin": "Status Admin",
            "not_connected_db": "Não conectado ao banco",
            "status_privileges_title": "🔐 STATUS DE PRIVILÉGIOS",
            "user": "Usuário",
            "database_name": "Banco",
            "ip": "IP",
            "superuser": "Superusuário",
            "yes": "✅ SIM",
            "no": "❌ NÃO",
            "full_admin_privileges": "✅ Privilégios completos de administração",
            "can_manage_all": "✅ Pode criar/alterar/excluir qualquer objeto",
            "access_all_tables": "✅ Acesso a todas as tabelas e schemas",
            "limited_admin_privileges": "⚠️ Privilégios administrativos limitados",
            "operations_may_fail": "❌ Algumas operações podem falhar",
            "create_new_table": "Criar Nova Tabela",
            "table_name": "Nome da Tabela:",
            "add_column": "Adicionar Coluna",
            "remove_column": "Remover Coluna",
            "rename_column": "Renomear Coluna",
            "delete_table": "Excluir Tabela",
            "close_editor": "Fechar Editor",
            "data_view": "Visualização de Dados",
            "advanced_admin_operations_title": "Operações Administrativas Avançadas",
            "admin_ops_header": "🔧 OPERAÇÕES ADMINISTRATIVAS",
            "recreate_schema": "🔄 Recriar Schema",
            "database_statistics": "📊 Estatísticas do BD",
            "view_connections": "🔍 Ver Conexões",
            "quick_backup": "💾 Backup Rápido",
            "manage_schemas": "🗃️ Gerenciar Schemas",
            "manage_users": "👥 Gerenciar Usuários",
            "insufficient_privileges": "Privilégios Insuficientes",
            "admin_required": "Esta operação requer modo ADMINISTRADOR",
            "advanced_sql_console": "Console SQL Avançado — Banco Conectado",
            "run_sql": "▶ Executar (Ctrl+Enter)",
            "save_script": "💾 Salvar",
            "open_script": "📂 Abrir",
            "export_csv": "📤 Exportar CSV",
            "copy": "📋 Copiar",
            "copied_to_clipboard": "Copiado para a área de transferência.",
            "no_rows_selected": "Nenhuma linha selecionada.",
            "close": "❌ Fechar",
            "advanced_editor_title": "Editor Avançado - Tabela: {table}",
            "delete_table_warning": "⚠️ ATENÇÃO!\n\nEsta ação excluirá PERMANENTEMENTE a tabela '{table}' e TODAS as tabelas dependentes (via CASCADE).\n\nTem certeza que deseja continuar?",
            "create": "Criar",
            "cancel": "Cancelar",
            "search_table": "Pesquisar tabela...",
            "add_record": "Adicionar Registro",
            "save": "Salvar",
            "column_name": "Nome da Coluna:",
            "data_type": "Tipo de Dados:",
            "new_name_for": "Novo nome para '{old}':",
            "required_field": " (OBRIGATÓRIO)",
            "table_structure": "Estrutura da Tabela",
            "use_schema": "Usar",
            "schemas_available": "Schemas Disponíveis:",
            "manage_schemas_title": "Gerenciar Schemas",
            "select_table_title": "Selecionar Tabela",
            "rename_column_title": "Renomear Coluna",
            "add_column_title": "Adicionar Coluna",
            "remove_column_title": "Remover Coluna",
            "edit_table_title": "Editor Avançado - Tabela: {table}",
            "rename": "Renomear",
            "add": "Adicionar",
            "remove": "Remover",
            "columns_hint": "Colunas (nome:tipo):",
            "table_created": "Tabela {nome} criada!",
            "table_deleted": "Tabela {table} excluída!",
            "column_added": "Coluna '{nome}' adicionada com sucesso!",
            "column_renamed": "Coluna renomeada!",
            "record_added": "Registro adicionado!",
            "record_updated": "Registro atualizado!",
            "records_deleted": "{count} registro(s) excluído(s) com sucesso!",
            "data_exported": "Dados exportados para:\n{arquivo}",
            "backup_created": "Backup criado com sucesso!\n{arquivo}",
            "schema_recreated": "Schema {schema} recriado com sucesso!",
            "schema_switched": "Schema alterado para: {schema}",
            "sql_execution_error": "Falha ao executar SQL:\n{erro}",
            "sql_execution_finished": "{ok} OK | {erros} ignorados | {afetadas} linhas | {tempo:.1f} ms",
            "sql_ready": "Pronto.",
            "sql_executing": "Executando...",
            "sql_saved": "Salvo em {arquivo}",
            "sql_loaded": "Carregado de {arquivo}",
            "no_results": "Nenhum resultado disponível.",
            "sql_console": "💻 Console SQL",
            "results": "Resultados:",
            "sql_placeholder": "-- Digite comandos SQL. Use ; para separar múltiplos comandos.\n",
            "edit_record_title": "Editar Registro - {table}",
            "confirm_table_deletion": "Confirmar Exclusão de Tabela",
            "confirm_delete_table": "Tem certeza que deseja excluir a tabela {table}?\nTodos os dados serão perdidos!",
            "create_table_error": "O nome da tabela é obrigatório",
            "create_table_columns_error": "Defina pelo menos uma coluna",
            "create_table_fail": "Falha ao criar tabela:\n{e}",
            "add_column_error": "Nome e tipo são obrigatórios",
            "rename_column_error": "Nome não pode ser vazio",
            "add_record_error": "Falha ao adicionar registro:\n{e}",
            "edit_record_error": "Falha ao atualizar registro:\n{e}",
            "delete_records_error": "Falha ao excluir registro(s):\n{e}",
            "export_error": "Falha ao exportar dados:\n{e}",
            "schema_manage_error": "Falha ao gerenciar schemas:\n{e}",
            "schema_switch_error": "Falha ao alterar schema:\n{e}",
            "user_manage_error": "Falha ao obter usuários:\n{e}",
            "statistics_error": "Falha ao obter estatísticas:\n{e}",
            "connections_error": "Falha ao obter conexões:\n{e}",
            "backup_error": "Falha ao criar backup:\n{e}",
            "recreate_schema_confirm": "Isso irá RECRIAR todo o schema atual!\nTodos os dados serão perdidos!\n\nContinuar?",
            "recreate_schema_error": "Falha ao recriar schema:\n{e}",
            "quick_backup_info": "Backup iniciado... Esta operação pode demorar alguns minutos.",
        },
        "en_US": {
            "admin_indicator": "🔐 ADMIN",
            "database": "Database:",
            "connect": "Connect",
            "admin_button": "🔑 Admin",
            "table": "Table:",
            "select_table": "Select Table",
            "refresh": "Refresh",
            "new_table": "New Table",
            "admin_operations": "Admin Operations",
            "delete": "Delete",
            "edit_table": "Edit Table",
            "sql": "SQL",
            "export": "Export",
            "edit": "Edit",
            "add": "Add",
            "error": "Error",
            "warning": "Warning",
            "info": "Information",
            "success": "Success",
            "confirm_deletion": "Confirm Deletion",
            "no_table_selected": "No table selected.",
            "no_record_selected": "No record selected.",
            "confirm_delete_records": "Do you really want to delete the selected record(s)?",
            "connection_error": "Connection Error",
            "connection_failed": "Failed to connect:\n{erro}",
            "status_admin": "Admin Status",
            "not_connected_db": "Not connected to database",
            "status_privileges_title": "🔐 PRIVILEGES STATUS",
            "user": "User",
            "database_name": "Database",
            "ip": "IP",
            "superuser": "Superuser",
            "yes": "✅ YES",
            "no": "❌ NO",
            "full_admin_privileges": "✅ Full administration privileges",
            "can_manage_all": "✅ Can create/change/delete any object",
            "access_all_tables": "✅ Access to all tables and schemas",
            "limited_admin_privileges": "⚠️ Limited administrative privileges",
            "operations_may_fail": "❌ Some operations may fail",
            "create_new_table": "Create New Table",
            "table_name": "Table Name:",
            "add_column": "Add Column",
            "remove_column": "Remove Column",
            "rename_column": "Rename Column",
            "delete_table": "Delete Table",
            "close_editor": "Close Editor",
            "data_view": "Data View",
            "advanced_admin_operations_title": "Advanced Administrative Operations",
            "admin_ops_header": "🔧 ADMINISTRATIVE OPERATIONS",
            "recreate_schema": "🔄 Recreate Schema",
            "database_statistics": "📊 Database Statistics",
            "view_connections": "🔍 View Connections",
            "quick_backup": "💾 Quick Backup",
            "manage_schemas": "🗃️ Manage Schemas",
            "manage_users": "👥 Manage Users",
            "insufficient_privileges": "Insufficient Privileges",
            "admin_required": "This operation requires ADMINISTRATOR mode",
            "advanced_sql_console": "Advanced SQL Console — Connected Database",
            "run_sql": "▶ Run (Ctrl+Enter)",
            "save_script": "💾 Save",
            "open_script": "📂 Open",
            "export_csv": "📤 Export CSV",
            "copy": "📋 Copy",
            "copied_to_clipboard": "Copied to clipboard.",
            "no_rows_selected": "No rows selected.",
            "close": "❌ Close",
            "advanced_editor_title": "Advanced Editor - Table: {table}",
            "delete_table_warning": "⚠️ WARNING!\n\nThis action will PERMANENTLY delete table '{table}' and ALL dependent tables (via CASCADE).\n\nAre you sure you want to continue?",
            "create": "Create",
            "cancel": "Cancel",
            "search_table": "Search table...",
            "add_record": "Add Record",
            "save": "Save",
            "column_name": "Column Name:",
            "data_type": "Data Type:",
            "new_name_for": "New name for '{old}':",
            "required_field": " (REQUIRED)",
            "table_structure": "Table Structure",
            "use_schema": "Use",
            "schemas_available": "Available Schemas:",
            "manage_schemas_title": "Manage Schemas",
            "select_table_title": "Select Table",
            "rename_column_title": "Rename Column",
            "add_column_title": "Add Column",
            "remove_column_title": "Remove Column",
            "edit_table_title": "Advanced Editor - Table: {table}",
            "rename": "Rename",
            "add": "Add",
            "remove": "Remove",
            "columns_hint": "Columns (name:type):",
            "table_created": "Table {nome} created!",
            "table_deleted": "Table {table} deleted!",
            "column_added": "Column '{nome}' added successfully!",
            "column_renamed": "Column renamed!",
            "record_added": "Record added!",
            "record_updated": "Record updated!",
            "records_deleted": "{count} record(s) deleted successfully!",
            "data_exported": "Data exported to:\n{arquivo}",
            "backup_created": "Backup created successfully!\n{arquivo}",
            "schema_recreated": "Schema {schema} recreated successfully!",
            "schema_switched": "Schema switched to: {schema}",
            "sql_execution_error": "Failed to execute SQL:\n{erro}",
            "sql_execution_finished": "{ok} OK | {erros} ignored | {afetadas} rows | {tempo:.1f} ms",
            "sql_ready": "Ready.",
            "sql_executing": "Executing...",
            "sql_saved": "Saved to {arquivo}",
            "sql_loaded": "Loaded from {arquivo}",
            "no_results": "No results available.",
            "sql_console": "💻 SQL Console",
            "results": "Results:",
            "sql_placeholder": "-- Enter SQL commands. Use ; to separate multiple commands.\n",
            "edit_record_title": "Edit Record - {table}",
            "confirm_table_deletion": "Confirm Table Deletion",
            "confirm_delete_table": "Are you sure you want to delete table {table}?\nAll data will be lost!",
            "create_table_error": "Table name is required",
            "create_table_columns_error": "Define at least one column",
            "create_table_fail": "Failed to create table:\n{e}",
            "add_column_error": "Name and type are required",
            "rename_column_error": "Name cannot be empty",
            "add_record_error": "Failed to add record:\n{e}",
            "edit_record_error": "Failed to update record:\n{e}",
            "delete_records_error": "Failed to delete record(s):\n{e}",
            "export_error": "Failed to export data:\n{e}",
            "schema_manage_error": "Failed to manage schemas:\n{e}",
            "schema_switch_error": "Failed to switch schema:\n{e}",
            "user_manage_error": "Failed to get users:\n{e}",
            "statistics_error": "Failed to get statistics:\n{e}",
            "connections_error": "Failed to get connections:\n{e}",
            "backup_error": "Failed to create backup:\n{e}",
            "recreate_schema_confirm": "This will RECREATE the entire current schema!\nAll data will be lost!\n\nContinue?",
            "recreate_schema_error": "Failed to recreate schema:\n{e}",
            "quick_backup_info": "Backup started... This operation may take a few minutes.",
        },
        "es_ES": {
            "admin_indicator": "🔐 ADMIN",
            "database": "Base:",
            "connect": "Conectar",
            "admin_button": "🔑 Admin",
            "table": "Tabla:",
            "select_table": "Seleccionar Tabla",
            "refresh": "Actualizar",
            "new_table": "Nueva Tabla",
            "admin_operations": "Operaciones Admin",
            "delete": "Eliminar",
            "edit_table": "Editar Tabla",
            "sql": "SQL",
            "export": "Exportar",
            "edit": "Editar",
            "add": "Agregar",
            "error": "Error",
            "warning": "Aviso",
            "info": "Información",
            "success": "Éxito",
            "confirm_deletion": "Confirmar Eliminación",
            "no_table_selected": "Ninguna tabla seleccionada.",
            "no_record_selected": "Ningún registro seleccionado.",
            "confirm_delete_records": "¿Desea realmente eliminar los registros seleccionados?",
            "connection_error": "Error de Conexión",
            "connection_failed": "Error al conectar:\n{erro}",
            "status_admin": "Estado Admin",
            "not_connected_db": "No conectado a la base",
            "status_privileges_title": "🔐 ESTADO DE PRIVILEGIOS",
            "user": "Usuario",
            "database_name": "Base",
            "ip": "IP",
            "superuser": "Superusuario",
            "yes": "✅ SÍ",
            "no": "❌ NO",
            "full_admin_privileges": "✅ Privilegios completos de administración",
            "can_manage_all": "✅ Puede crear/alterar/eliminar cualquier objeto",
            "access_all_tables": "✅ Acceso a todas las tablas y schemas",
            "limited_admin_privileges": "⚠️ Privilegios administrativos limitados",
            "operations_may_fail": "❌ Algunas operaciones pueden fallar",
            "create_new_table": "Crear Nueva Tabla",
            "table_name": "Nombre de la Tabla:",
            "add_column": "Agregar Columna",
            "remove_column": "Eliminar Columna",
            "rename_column": "Renombrar Columna",
            "delete_table": "Eliminar Tabla",
            "close_editor": "Cerrar Editor",
            "data_view": "Visualización de Datos",
            "advanced_admin_operations_title": "Operaciones Administrativas Avanzadas",
            "admin_ops_header": "🔧 OPERACIONES ADMINISTRATIVAS",
            "recreate_schema": "🔄 Recrear Schema",
            "database_statistics": "📊 Estadísticas de la Base",
            "view_connections": "🔍 Ver Conexiones",
            "quick_backup": "💾 Respaldo Rápido",
            "manage_schemas": "🗃️ Gestionar Schemas",
            "manage_users": "👥 Gestionar Usuarios",
            "insufficient_privileges": "Privilegios Insuficientes",
            "admin_required": "Esta operación requiere modo ADMINISTRADOR",
            "advanced_sql_console": "Consola SQL Avanzada — Base Conectada",
            "run_sql": "▶ Ejecutar (Ctrl+Enter)",
            "save_script": "💾 Guardar",
            "open_script": "📂 Abrir",
            "export_csv": "📤 Exportar CSV",
            "copy": "📋 Copiar",
            "copied_to_clipboard": "Copiado al portapapeles.",
            "no_rows_selected": "Ninguna fila seleccionada.",
            "close": "❌ Cerrar",
            "advanced_editor_title": "Editor Avanzado - Tabla: {table}",
            "delete_table_warning": "⚠️ ¡ATENCIÓN!\n\nEsta acción eliminará PERMANENTEMENTE la tabla '{table}' y TODAS las tablas dependientes (vía CASCADE).\n\n¿Está seguro de que desea continuar?",
            "create": "Crear",
            "cancel": "Cancelar",
            "search_table": "Buscar tabla...",
            "add_record": "Agregar Registro",
            "save": "Guardar",
            "column_name": "Nombre de la Columna:",
            "data_type": "Tipo de Datos:",
            "new_name_for": "Nuevo nombre para '{old}':",
            "required_field": " (OBLIGATORIO)",
            "table_structure": "Estructura de la Tabla",
            "use_schema": "Usar",
            "schemas_available": "Schemas Disponibles:",
            "manage_schemas_title": "Gestionar Schemas",
            "select_table_title": "Seleccionar Tabla",
            "rename_column_title": "Renombrar Columna",
            "add_column_title": "Agregar Columna",
            "remove_column_title": "Eliminar Columna",
            "edit_table_title": "Editor Avanzado - Tabla: {table}",
            "rename": "Renombrar",
            "add": "Agregar",
            "remove": "Eliminar",
            "columns_hint": "Columnas (nombre:tipo):",
            "table_created": "¡Tabla {nome} creada!",
            "table_deleted": "¡Tabla {table} eliminada!",
            "column_added": "¡Columna '{nome}' agregada con éxito!",
            "column_renamed": "¡Columna renombrada!",
            "record_added": "¡Registro agregado!",
            "record_updated": "¡Registro actualizado!",
            "records_deleted": "¡{count} registro(s) eliminado(s) con éxito!",
            "data_exported": "Datos exportados a:\n{arquivo}",
            "backup_created": "¡Respaldo creado con éxito!\n{arquivo}",
            "schema_recreated": "¡Schema {schema} recreado con éxito!",
            "schema_switched": "Schema cambiado a: {schema}",
            "sql_execution_error": "Error al ejecutar SQL:\n{erro}",
            "sql_execution_finished": "{ok} OK | {erros} ignorados | {afetadas} filas | {tempo:.1f} ms",
            "sql_ready": "Listo.",
            "sql_executing": "Ejecutando...",
            "sql_saved": "Guardado en {arquivo}",
            "sql_loaded": "Cargado desde {arquivo}",
            "no_results": "No hay resultados disponibles.",
            "sql_console": "💻 Consola SQL",
            "results": "Resultados:",
            "sql_placeholder": "-- Escriba comandos SQL. Use ; para separar múltiples comandos.\n",
            "edit_record_title": "Editar Registro - {table}",
            "confirm_table_deletion": "Confirmar Eliminación de Tabla",
            "confirm_delete_table": "¿Está seguro de que desea eliminar la tabla {table}?\n¡Todos los datos se perderán!",
            "create_table_error": "El nombre de la tabla es obligatorio",
            "create_table_columns_error": "Defina al menos una columna",
            "create_table_fail": "Fallo al crear tabla:\n{e}",
            "add_column_error": "Nombre y tipo son obligatorios",
            "rename_column_error": "El nombre no puede estar vacío",
            "add_record_error": "Fallo al agregar registro:\n{e}",
            "edit_record_error": "Fallo al actualizar registro:\n{e}",
            "delete_records_error": "Fallo al eliminar registro(s):\n{e}",
            "export_error": "Fallo al exportar datos:\n{e}",
            "schema_manage_error": "Fallo al gestionar schemas:\n{e}",
            "schema_switch_error": "Fallo al cambiar schema:\n{e}",
            "user_manage_error": "Fallo al obtener usuarios:\n{e}",
            "statistics_error": "Fallo al obtener estadísticas:\n{e}",
            "connections_error": "Fallo al obtener conexiones:\n{e}",
            "backup_error": "Fallo al crear respaldo:\n{e}",
            "recreate_schema_confirm": "¡Esto RECREARÁ todo el schema actual!\n¡Todos los datos se perderán!\n\n¿Continuar?",
            "recreate_schema_error": "Fallo al recrear schema:\n{e}",
            "quick_backup_info": "Respaldo iniciado... Esta operación puede tomar unos minutos.",
        },
    }

    def __init__(self, sistema, frame, arquivo_db="factory.db"):
        # Contexto principal
        self.sistema = sistema
        self.root = sistema.root if hasattr(sistema, 'root') else sistema
        self.frame = frame

        # Logger integrado
        try:
            from PAGINAS_DO_SISTEMA.LOG_SISTEMA import get_logger
            self.logger = get_logger()
            self.logger.set_usuario("admin", "ADMINISTRADOR")
            self.logger.set_pagina("BANCO_DADOS_FABRICA")
        except ImportError:
            # Fallback se o logger não estiver disponível
            class DummyLogger:
                def info(self, msg, detalhes=None): print(f"INFO: {msg}")

                def warning(self, msg, detalhes=None): print(f"WARN: {msg}")

                def error(self, msg, detalhes=None): print(f"ERRO: {msg}")

                def set_usuario(self, user, nome): pass

                def set_pagina(self, pagina): pass

            self.logger = DummyLogger()

        # Estado da conexão com o banco - SEMPRE COMO ADMIN
        self.conn = None
        self.cursor = None
        self.current_table = None
        self.result_tree = None
        self.modo_admin = True  # FORÇAR MODO ADMIN SEMPRE
        # JESUS SEJA LOUVADO PARA TODO O SEMPRE AMEM!!!
        # IMPORTANTE:
        # Não alterar aparência global (ctk.set_appearance_mode / set_default_color_theme)
        # dentro desta página. O tema deve vir do host/menu para evitar que outras
        # telas mudem visualmente ao abrir "Banco de Dados".

        # Componentes da interface gráfica
        self.main_frame = None
        self.tree_frame = None
        self.tree = None
        self.db_entry = None
        self.table_button = None
        self.selected_table_var = None
        self.admin_indicator = None
        self.admin_btn = None
        self.lbl_database = None
        self.lbl_table = None
        self.btn_connect = None
        self.btn_refresh = None
        self.btn_new_table = None
        self.btn_admin_operations = None
        self.btn_delete = None
        self.btn_edit_table = None
        self.btn_sql = None
        self.btn_export = None
        self.btn_edit = None
        self.btn_add = None
        self.idioma_atual = getattr(self.sistema, "idioma_atual", "pt_BR")

        # Inicializar interface e tentar conectar ao banco COMO ADMIN
        self.configurar_interface()
        self.conectar_como_admin()  # SEMPRE CONECTAR COMO ADMIN

    # ========== Métodos auxiliares ==========
    def _get_idioma_atual(self):
        idioma = getattr(self, "idioma_atual", None) or getattr(self.sistema, "idioma_atual", None)
        return idioma or "pt_BR"

    def _get_text(self, chave, **kwargs):
        idioma = self._get_idioma_atual()
        texto = self.TRANSLATIONS.get(idioma, {}).get(chave, self.TRANSLATIONS["pt_BR"].get(chave, chave))
        try:
            return texto.format(**kwargs)
        except Exception:
            return texto

    def _t(self, chave, **kwargs):
        return self._get_text(chave, **kwargs)

    def set_idioma(self, idioma):
        self.idioma_atual = idioma or "pt_BR"
        self.refresh_texts()

    def _center_window(self, window, width, height):
        """Centraliza a janela em relação ao parent (self.root)."""
        if not self.root or not self.root.winfo_exists():
            return
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()
        x = parent_x + (parent_w // 2) - (width // 2)
        y = parent_y + (parent_h // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def _format_column_header(self, column_name):
        idioma = self._get_idioma_atual()
        key = str(column_name or "").strip().lower()
        header_map = {
            "pt_BR": {
                "id": "ID",
                "schema_name": "Schema Name",
                "versao": "Versão",
                "criado_em": "Criado Em",
                "atualizado_em": "Atualizado Em",
                "created_at": "Criado Em",
                "updated_at": "Atualizado Em",
                "name": "Nome",
                "type": "Tipo",
                "required": "Obrigatório",
                "default": "Padrão",
                "pk": "PK",
            },
            "en_US": {
                "id": "ID",
                "schema_name": "Schema Name",
                "versao": "Version",
                "criado_em": "Created At",
                "atualizado_em": "Updated At",
                "created_at": "Created At",
                "updated_at": "Updated At",
                "name": "Name",
                "type": "Type",
                "required": "Required",
                "default": "Default",
                "pk": "PK",
            },
            "es_ES": {
                "id": "ID",
                "schema_name": "Schema Name",
                "versao": "Versión",
                "criado_em": "Creado En",
                "atualizado_em": "Actualizado En",
                "created_at": "Creado En",
                "updated_at": "Actualizado En",
                "name": "Nombre",
                "type": "Tipo",
                "required": "Obligatorio",
                "default": "Predeterminado",
                "pk": "PK",
            },
        }
        translated = header_map.get(idioma, {}).get(key)
        if translated:
            return translated
        base = str(column_name or "").replace("_", " ").strip()
        if not base:
            return str(column_name or "")
        if base.lower() == "id":
            return "ID"
        return base.title()

    def _update_tree_headers(self, tree_widget):
        try:
            if not tree_widget:
                return
            for col in tree_widget["columns"]:
                tree_widget.heading(col, text=self._format_column_header(col))
        except Exception:
            pass

    def _bind_ctrl_a_treeview(self, tree_widget):
        try:
            if not tree_widget:
                return

            def selecionar_tudo(event=None):
                try:
                    itens = tree_widget.get_children()
                    if not itens:
                        return "break"
                    tree_widget.focus_set()
                    tree_widget.selection_set(itens)
                    tree_widget.focus(itens[0])
                    tree_widget.see(itens[0])
                except Exception:
                    pass
                return "break"

            tree_widget.bind("<Control-a>", selecionar_tudo)
            tree_widget.bind("<Control-A>", selecionar_tudo)
        except Exception:
            pass

    def _copiar_linhas_treeview(self, tree_widget, incluir_cabecalho=True, apenas_selecionadas=True):
        try:
            if not tree_widget:
                return False

            itens = tree_widget.selection() if apenas_selecionadas else tree_widget.get_children()
            if not itens:
                return False

            colunas = list(tree_widget["columns"])
            linhas = []

            if incluir_cabecalho and colunas:
                linhas.append("	".join([str(self._format_column_header(c)) for c in colunas]))

            for iid in itens:
                valores = tree_widget.item(iid).get("values", [])
                valores_formatados = []
                for valor in valores:
                    texto = "" if valor is None else str(valor)
                    texto = texto.replace("\r", " ").replace("\n", " ")
                    valores_formatados.append(texto)
                linhas.append("	".join(valores_formatados))

            if not linhas:
                return False

            conteudo = "\n".join(linhas)
            self.root.clipboard_clear()
            self.root.clipboard_append(conteudo)
            self.root.update()
            return True
        except Exception:
            return False

    def _bind_copy_treeview(self, tree_widget):
        try:
            if not tree_widget:
                return

            def copiar_selecao(event=None):
                ok = self._copiar_linhas_treeview(tree_widget, incluir_cabecalho=True, apenas_selecionadas=True)
                if not ok:
                    try:
                        messagebox.showinfo(self._t("info"), self._t("no_rows_selected"), parent=self.root)
                    except Exception:
                        pass
                return "break"

            tree_widget.bind("<Control-c>", copiar_selecao)
            tree_widget.bind("<Control-C>", copiar_selecao)
        except Exception:
            pass

    def refresh_texts(self):
        self.idioma_atual = self._get_idioma_atual()

        widgets = [
            ("admin_indicator", "admin_indicator"),
            ("lbl_database", "database"),
            ("btn_connect", "connect"),
            ("admin_btn", "admin_button"),
            ("lbl_table", "table"),
            ("btn_refresh", "refresh"),
            ("btn_new_table", "new_table"),
            ("btn_admin_operations", "admin_operations"),
            ("btn_delete", "delete"),
            ("btn_edit_table", "edit_table"),
            ("btn_sql", "sql"),
            ("btn_export", "export"),
            ("btn_edit", "edit"),
            ("btn_add", "add"),
        ]
        for attr, key in widgets:
            widget = getattr(self, attr, None)
            try:
                if widget is not None and widget.winfo_exists():
                    widget.configure(text=self._get_text(key))
            except Exception:
                pass

        try:
            if self.table_button is not None and self.table_button.winfo_exists():
                current_label = (self.current_table or "").strip()
                self.table_button.configure(text=current_label or self._get_text("select_table"))
        except Exception:
            pass

        self._update_tree_headers(getattr(self, "tree", None))
        self._update_tree_headers(getattr(self, "result_tree", None))

    def on_language_changed(self, novo_idioma=None):
        if novo_idioma:
            self.idioma_atual = novo_idioma
        else:
            self.idioma_atual = self._get_idioma_atual()
        self.refresh_texts()

    # =================== INTERFACE PRINCIPAL ===================
    def configurar_interface(self):
        """Interface principal obedecendo o idioma do menu"""
        if hasattr(self, 'main_frame') and self.main_frame:
            try:
                self.main_frame.destroy()
            except Exception:
                pass

        self.main_frame = ctk.CTkFrame(self.frame)
        self.main_frame.pack(fill="both", expand=True)

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        top_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", pady=5)

        self.admin_indicator = ctk.CTkLabel(
            top_frame,
            text=self._get_text("admin_indicator"),
            text_color="red",
            font=("Arial", 10, "bold")
        )
        self.admin_indicator.pack(side="left", padx=5)

        self.lbl_database = ctk.CTkLabel(top_frame, text=self._get_text("database"))
        self.lbl_database.pack(side="left", padx=5)

        self.db_entry = ctk.CTkEntry(top_frame, width=200)
        self.db_entry.pack(side="left", padx=5)
        schema = db.get_schema()
        self.db_entry.insert(0, schema or "")

        self.btn_connect = BotaoPadronizado.criar_botao(
            top_frame,
            text=self._get_text("connect"),
            command=self.conectar_como_admin,
            fg_color="#17a2b8",          # cor fixa azul claro
            hover_color="#138496"
        )
        self.btn_connect.pack(side="left", padx=5)

        self.admin_btn = BotaoPadronizado.criar_botao(
            top_frame,
            text=self._get_text("admin_button"),
            command=self.mostrar_status_admin,
            fg_color="#dc3545",           # vermelho
            border_width=1,
            text_color="white",
            hover_color="#b52a3a"
        )
        self.admin_btn.pack(side="left", padx=5)

        self.lbl_table = ctk.CTkLabel(top_frame, text=self._get_text("table"))
        self.lbl_table.pack(side="left", padx=5)

        self.selected_table_var = ctk.StringVar()
        self.table_button = BotaoPadronizado.criar_botao(
            top_frame,
            text=self._get_text("select_table"),
            width=200,
            command=self._abrir_seletor_tabelas,
            fg_color="#17a2b8",
            hover_color="#138496"
        )
        self.table_button.pack(side="left", padx=5)

        self.btn_refresh = BotaoPadronizado.criar_botao(
            top_frame,
            text=self._get_text("refresh"),
            command=self.atualizar_lista_tabelas,
            fg_color="#17a2b8",
            hover_color="#138496"
        )
        self.btn_refresh.pack(side="left", padx=5)

        self.btn_new_table = BotaoPadronizado.criar_botao(
            top_frame,
            text=self._get_text("new_table"),
            command=self.criar_nova_tabela,
            fg_color="#17a2b8",
            hover_color="#138496"
        )
        self.btn_new_table.pack(side="left", padx=5)

        # setas com cor fixa
        BotaoPadronizado.criar_botao(top_frame, text='▲', width=30, command=self.on_arrow_up,
                      fg_color="#17a2b8", hover_color="#138496").pack(side="left", padx=2)
        BotaoPadronizado.criar_botao(top_frame, text='▼', width=30, command=self.on_arrow_down,
                      fg_color="#17a2b8", hover_color="#138496").pack(side="left", padx=2)

        self.tree_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, sticky="ew", pady=5)

        self.btn_admin_operations = BotaoPadronizado.criar_botao(
            bottom_frame,
            text=self._get_text("admin_operations"),
            command=self.operacoes_avancadas,
            fg_color="#6f42c1",           # roxo
            hover_color="#5a2d91"
        )
        self.btn_admin_operations.pack(side="left", padx=5)

        def confirmar_exclusao_registro():
            if not self.current_table:
                messagebox.showerror(self._get_text("error"), self._get_text("no_table_selected"))
                return
            selecionados = self.tree.selection()
            if not selecionados:
                messagebox.showwarning(self._get_text("warning"), self._get_text("no_record_selected"))
                return
            if not messagebox.askyesno(self._get_text("confirm_deletion"), self._get_text("confirm_delete_records")):
                return
            self.excluir_registro()

        self.btn_delete = BotaoPadronizado.criar_botao(
            bottom_frame,
            text=self._get_text("delete"),
            command=confirmar_exclusao_registro,
            fg_color="#dc3545",            # vermelho
            hover_color="#b52a3a"
        )
        self.btn_delete.pack(side="left", padx=5)

        self.btn_edit_table = BotaoPadronizado.criar_botao(
            bottom_frame,
            text=self._get_text("edit_table"),
            command=self.editar_tabela_completa,
            fg_color="#17a2b8",
            hover_color="#138496"
        )
        self.btn_edit_table.pack(side="left", padx=5)

        self.btn_sql = BotaoPadronizado.criar_botao(
            bottom_frame,
            text=self._get_text("sql"),
            command=self.executar_sql_personalizado,
            fg_color="#6c757d",            # cinza
            hover_color="#5a6268"
        )
        self.btn_sql.pack(side="right", padx=5)

        self.btn_export = BotaoPadronizado.criar_botao(
            bottom_frame,
            text=self._get_text("export"),
            command=self.exportar_dados,
            fg_color="#007bff",             # azul
            hover_color="#0056b3"
        )
        self.btn_export.pack(side="right", padx=5)

        self.btn_edit = BotaoPadronizado.criar_botao(
            bottom_frame,
            text=self._get_text("edit"),
            command=self.editar_registro,
            fg_color="#ffc107",             # amarelo
            hover_color="#e0a800",
            text_color="black"
        )
        self.btn_edit.pack(side="right", padx=5)

        self.btn_add = BotaoPadronizado.criar_botao(
            bottom_frame,
            text=self._get_text("add"),
            command=self.adicionar_registro,
            fg_color="#28a745",             # verde
            hover_color="#218838"
        )
        self.btn_add.pack(side="right", padx=5)

    # =================== CONEXÃO COMO ADMINISTRADOR ===================
    def conectar_como_admin(self):
        """Sempre conectar com privilégios de administrador"""
        try:
            if self.conn:
                try:
                    self.cursor.close()
                    self.conn.close()
                except Exception:
                    pass

            # Usar conexão normal mas verificar privilégios de admin
            self.conn = db.get_connection()
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Verificar se temos privilégios de administrador
            self.cursor.execute(
                "SELECT current_user, (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) as is_superuser")
            user_info = self.cursor.fetchone()

            is_admin = user_info['is_superuser'] if user_info else False

            if is_admin:
                self.logger.info("Conectado com privilégios de SUPER ADMIN")
                self.mostrar_status_conexao("🔐 CONECTADO COMO SUPER ADMINISTRADOR")
            else:
                self.logger.warning("Conectado mas SEM privilégios administrativos")
                self.mostrar_status_conexao("⚠️ Conectado SEM privilégios de admin")

            # Configurar interface se necessário
            if not self.tree:
                self.tree = ttk.Treeview(self.tree_frame, selectmode="extended")
                self._bind_ctrl_a_treeview(self.tree)
                self._bind_copy_treeview(self.tree)
                style = ttk.Style()
                style.configure('Treeview', rowheight=25, font=('Arial', 12))
                style.configure('Treeview.Heading', font=('Arial', 12, 'bold'))
                self.tree.pack(fill="both", expand=True)
                self._bind_ctrl_a_treeview(self.tree)

            self.atualizar_lista_tabelas()

        except Exception as e:
            self.logger.error("Erro ao conectar como administrador", detalhes={"erro": str(e)})
            messagebox.showerror(self._get_text("connection_error"),
                                 self._get_text("connection_failed", erro=e),
                                 parent=self.root)
            self.conn = None
            self.cursor = None

    def mostrar_status_admin(self):
        """Mostrar status dos privilégios administrativos"""
        if not self.conn:
            messagebox.showinfo(self._get_text("status_admin"), self._get_text("not_connected_db"))
            return
        # JESUS SEJA LOUVADO PARA TODO O SEMPRE AMEM!!!
        try:
            # Verificar privilégios
            self.cursor.execute("""
                SELECT 
                    current_user,
                    current_database(),
                    inet_client_addr() as client_ip,
                    (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) as is_superuser
            """)
            info = self.cursor.fetchone()

            status = self._get_text("status_privileges_title") + "\n\n"
            status += f"{self._get_text('user')}: {info['current_user']}\n"
            status += f"{self._get_text('database_name')}: {info['current_database']}\n"
            status += f"{self._get_text('ip')}: {info['client_ip']}\n"
            status += f"{self._get_text('superuser')}: {self._get_text('yes') if info['is_superuser'] else self._get_text('no')}\n\n"

            if info['is_superuser']:
                status += self._get_text("full_admin_privileges") + "\n"
                status += self._get_text("can_manage_all") + "\n"
                status += self._get_text("access_all_tables") + "\n"
            else:
                status += self._get_text("limited_admin_privileges") + "\n"
                status += self._get_text("operations_may_fail") + "\n"

            messagebox.showinfo(self._get_text("status_admin"), status)

        except Exception as e:
            messagebox.showerror(self._get_text("error"), f"Falha ao verificar privilégios: {e}")

    def mostrar_status_conexao(self, mensagem):
        """Mostrar status da conexão administrativa"""
        try:
            self.cursor.execute("SELECT current_database(), current_user, version()")
            info = self.cursor.fetchone()

            top = ctk.CTkToplevel(self.root)
            top.title("✅ Conexão Estabelecida")
            top.geometry("500x200")
            top.resizable(False, False)
            top.attributes("-topmost", True)
            self._center_window(top, 500, 200)

            frame = ctk.CTkFrame(top, fg_color="transparent")
            frame.pack(pady=20, padx=20, fill="both", expand=True)

            ctk.CTkLabel(frame, text=mensagem,
                         font=("Arial", 14, "bold"),
                         text_color="red").pack(pady=10)

            ctk.CTkLabel(frame, text=f"{self._t('database_name')}: {info['current_database']} | {self._t('user')}: {info['current_user']}",
                         font=("Arial", 12)).pack(pady=5)

            progress = ctk.CTkProgressBar(frame, width=400, progress_color="red")
            progress.pack(pady=10)
            progress.set(0)

            # Animação de progresso
            def animar_progresso():
                for i in range(1, 101):
                    top.after(i * 5, lambda i=i: progress.set(i / 100))
                top.after(600, top.destroy)

            animar_progresso()

        except Exception as e:
            print(f"Erro ao mostrar status: {e}")

    def conectar_db_handler(self, admin: bool = False):
        """Método original - redirecionar para conexão admin"""
        self.conectar_como_admin()

    # =================== MÉTODOS DE GERENCIAMENTO ===================
    def atualizar_lista_tabelas(self):
        if not self.conn:
            messagebox.showerror("Erro", "Nenhuma conexão ativa com o banco de dados.")
            return

        try:
            schema = db.get_schema()

            # Teste seguro da conexão
            try:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
            except Exception as e:
                self.logger.warning(
                    "Conexão ou cursor inválidos ao atualizar lista de tabelas, tentando reconectar...",
                    detalhes={"erro": str(e)},
                )
                self.conectar_como_admin()
                if not self.conn:
                    raise RuntimeError("Não foi possível restabelecer a conexão com o banco.")
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")

            tabelas = db.list_tables(schema=schema)

            self.tabelas_list = tabelas if tabelas else []
            current = self.selected_table_var.get() if self.selected_table_var else ""

            if not self.tabelas_list:
                self.selected_table_var.set("")
                self.table_button.configure(text=self._get_text("select_table"))
                self.limpar_treeview()
                return

            if current and current in self.tabelas_list:
                self.table_button.configure(text=current)
                self.carregar_tabela(current)
            else:
                nova = self.tabelas_list[0]
                self.selected_table_var.set(nova)
                self.table_button.configure(text=nova)
                self.carregar_tabela(nova)

            self.logger.info(
                "Lista de tabelas atualizada",
                detalhes={"total": len(self.tabelas_list)},
            )

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao atualizar lista de tabelas:\n{e}")
            self.logger.error(
                "Erro ao atualizar lista de tabelas",
                detalhes={"erro": str(e)},
            )

    def carregar_tabela(self, table_name):
        if not (self.conn and table_name):
            self.logger.warning("Tentativa de carregar tabela sem conexão ou nome de tabela.",
                                detalhes={"tabela": table_name, "conexao_ativa": bool(self.conn)})
            return
        try:
            self.limpar_treeview()
            self.current_table = table_name

            schema = db.get_schema()
            cols_info = db.list_columns(table_name, schema=schema)
            colunas = [c["column_name"] for c in cols_info]

            self.tree["columns"] = colunas
            self.tree["show"] = "headings"
            for col in colunas:
                self.tree.heading(col, text=self._format_column_header(col))
                self.tree.column(col, width=120, anchor="w", stretch=True)

            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            qn = qname(table_name, schema)
            self.cursor.execute(f"SELECT * FROM {qn}")
            rows = self.cursor.fetchall()

            if not rows:
                return

            if hasattr(rows[0], 'keys'):
                processed_rows = [tuple(row.get(col_name) for col_name in colunas) for row in rows]
            else:
                processed_rows = rows

            for linha in processed_rows:
                self.tree.insert("", "end", values=linha)

        except Exception as e:
            self.logger.error(f"Falha ao carregar a tabela '{table_name}'", detalhes={"erro": str(e)})
            messagebox.showerror("Erro", f"Falha ao carregar {table_name}:\n{e}")
            self.limpar_treeview()

    def limpar_treeview(self):
        if hasattr(self, 'tree') and self.tree:
            self.tree.delete(*self.tree.get_children())
            self.tree["columns"] = []

    def on_arrow_up(self, event=None):
        self._switch_table(-1)

    def on_arrow_down(self, event=None):
        self._switch_table(1)

    def _switch_table(self, direction):
        if not getattr(self, 'tabelas_list', None):
            self.atualizar_lista_tabelas()
        if not getattr(self, 'tabelas_list', None):
            return
        try:
            idx = self.tabelas_list.index(self.current_table)
        except ValueError:
            return
        new_idx = (idx + direction) % len(self.tabelas_list)
        new_table = self.tabelas_list[new_idx]
        self.selected_table_var.set(new_table)
        self.table_button.configure(text=new_table)
        self.carregar_tabela(new_table)

    # =================== DIÁLOGOS COM TRADUÇÃO E CENTRALIZAÇÃO ===================
    def criar_nova_tabela(self):
        if not self.conn:
            messagebox.showerror("Erro", "Não há conexão com o banco de dados")
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title(self._t("create_new_table"))
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        self._center_window(dialog, 500, 400)

        main = ctk.CTkFrame(dialog)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(main, text=self._t("table_name")).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        nome_entry = ctk.CTkEntry(main, width=300)
        nome_entry.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(main, text=self._t("columns_hint")).grid(row=1, column=0, padx=5, pady=5, sticky="ne")
        col_frame = ctk.CTkFrame(main)
        col_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        col_text = ctk.CTkTextbox(col_frame, width=400, height=200)
        col_text.pack(fill="both", expand=True, padx=5, pady=5)
        col_text.insert("1.0", "id SERIAL PRIMARY KEY\nnome TEXT NOT NULL\nquantidade INTEGER")

        button_frame = ctk.CTkFrame(main)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        def criar():
            nome = nome_entry.get().strip()
            cols = col_text.get("1.0", "end").strip()
            if not nome:
                messagebox.showerror(self._t("error"), self._t("create_table_error"))
                return
            if not cols:
                messagebox.showerror(self._t("error"), self._t("create_table_columns_error"))
                return
            try:
                schema = db.get_schema()
                cols_sql = ",\n".join([c.strip() for c in cols.split("\n") if c.strip()])

                def qname(table, schema):
                    return f'"{schema}"."{table}"' if schema else f'"{table}"'

                qn = qname(nome, schema)
                self.cursor.execute(f"CREATE TABLE {qn} (\n{cols_sql}\n)")
                self.conn.commit()
                messagebox.showinfo(self._t("success"), self._t("table_created", nome=nome))
                self.atualizar_lista_tabelas()
                dialog.destroy()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror(self._t("error"), self._t("create_table_fail", e=e))

        BotaoPadronizado.criar_botao(button_frame, text=self._t("create"), command=criar,
                      fg_color="#28a745", hover_color="#218838").pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(button_frame, text=self._t("cancel"), command=dialog.destroy,
                      fg_color="#6c757d", hover_color="#5a6268").pack(side="left", padx=5)

    def excluir_tabela(self):
        if not self.current_table:
            messagebox.showerror(self._t("error"), self._t("no_table_selected"))
            return
        if not messagebox.askyesno(self._t("confirm_table_deletion"),
                                   self._t("confirm_delete_table", table=self.current_table)):
            return
        try:
            schema = db.get_schema()
            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'
            self.cursor.execute(f"DROP TABLE {qname(self.current_table, schema)}")
            self.conn.commit()
            messagebox.showinfo(self._t("success"), self._t("table_deleted", table=self.current_table))
            self.current_table = None
            self.atualizar_lista_tabelas()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(self._t("error"), f"Falha ao excluir tabela:\n{e}")

    def adicionar_coluna(self, parent_window):
        dialog = ctk.CTkToplevel(parent_window)
        dialog.title(self._t("add_column"))
        dialog.geometry("420x300")
        dialog.transient(parent_window)
        dialog.grab_set()
        self._center_window(dialog, 420, 300)

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text=self._t("column_name")).pack(pady=5)
        nome_entry = ctk.CTkEntry(frame)
        nome_entry.pack(pady=5, fill="x")

        ctk.CTkLabel(frame, text=self._t("data_type")).pack(pady=5)
        tipo_combobox = ctk.CTkComboBox(
            frame,
            values=["VARCHAR(100)", "INTEGER", "NUMERIC(10,2)", "BOOLEAN", "DATE", "TIMESTAMP", "TEXT"]
        )
        tipo_combobox.pack(pady=5, fill="x")
        tipo_combobox.set("TEXT")

        def adicionar():
            nome = nome_entry.get().strip()
            tipo = tipo_combobox.get().strip()
            if not nome or not tipo:
                messagebox.showerror(self._t("error"), self._t("add_column_error"))
                return
            try:
                schema = db.get_schema()
                sql = f'ALTER TABLE "{schema}"."{self.current_table}" ADD COLUMN IF NOT EXISTS "{nome}" {tipo}'
                self.cursor.execute(sql)
                self.conn.commit()
                messagebox.showinfo(self._t("success"), self._t("column_added", nome=nome))
                parent_window.destroy()
                self.editar_tabela_completa()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror(self._t("error"), f"Falha ao adicionar coluna:\n{e}")

        BotaoPadronizado.criar_botao(frame, text=self._t("add"), command=adicionar,
                      fg_color="#28a745", hover_color="#218838").pack(pady=15)

    def renomear_coluna(self, tree, parent_window):
        selected = tree.selection()
        if not selected:
            messagebox.showerror(self._t("error"), "Selecione uma coluna")
            return
        col_data = tree.item(selected[0])["values"]
        old_name = col_data[1]

        dialog = ctk.CTkToplevel(parent_window)
        dialog.title(self._t("rename_column_title"))
        dialog.geometry("400x200")
        dialog.transient(parent_window)
        dialog.grab_set()
        self._center_window(dialog, 400, 200)

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frame, text=self._t("new_name_for", old=old_name)).pack(pady=5)
        new_name_entry = ctk.CTkEntry(frame)
        new_name_entry.pack(pady=5, fill="x")
        new_name_entry.insert(0, old_name)

        def executar():
            new_name = new_name_entry.get().strip()
            if not new_name:
                messagebox.showerror(self._t("error"), self._t("rename_column_error"))
                return
            try:
                schema = db.get_schema()
                def qname(table, schema):
                    return f'"{schema}"."{table}"' if schema else f'"{table}"'
                self.cursor.execute(
                    f'ALTER TABLE {qname(self.current_table, schema)} RENAME COLUMN "{old_name}" TO "{new_name}"')
                self.conn.commit()
                messagebox.showinfo(self._t("success"), self._t("column_renamed"))
                parent_window.destroy()
                self.editar_tabela()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror(self._t("error"), f"Falha ao renomear:\n{e}")

        BotaoPadronizado.criar_botao(frame, text=self._t("rename"), command=executar,
                      fg_color="#28a745", hover_color="#218838").pack(pady=10)

    def adicionar_registro(self):
        if not self.current_table:
            messagebox.showerror(self._t("error"), self._t("no_table_selected"))
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title(self._t("add_record"))
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        self._center_window(dialog, 500, 600)

        main = ctk.CTkScrollableFrame(dialog)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        schema = db.get_schema()
        colunas_info = db.list_columns(self.current_table, schema=schema)
        colunas = [c["column_name"] for c in colunas_info if c["column_name"].lower() != "id"]

        entries = {}
        for coluna in colunas:
            frame = ctk.CTkFrame(main)
            frame.pack(fill="x", pady=5)
            info = next((c for c in colunas_info if c["column_name"] == coluna), None)
            tipo = info["data_type"] if info else "TEXT"
            nullable_raw = info.get("is_nullable", info.get("nullable", "YES")) if info else "YES"
            obrig = self._t("required_field") if str(nullable_raw).strip().upper() in ("NO", "FALSE", "F", "0", "N", "NAO", "NÃO") else ""
            ctk.CTkLabel(frame, text=f"{coluna}{obrig} ({tipo}):").pack(side="left", padx=5)
            e = ctk.CTkEntry(frame)
            e.pack(side="right", fill="x", expand=True, padx=5)
            entries[coluna] = e

        def salvar():
            valores = {}
            for coluna, e in entries.items():
                valor = e.get().strip()
                info = next((c for c in colunas_info if c["column_name"] == coluna), None)
                nullable_raw = info.get("is_nullable", info.get("nullable", "YES")) if info else "YES"
                if str(nullable_raw).strip().upper() in ("NO", "FALSE", "F", "0", "N", "NAO", "NÃO") and not valor:
                    messagebox.showerror(self._t("error"), f"O campo {coluna} é obrigatório!")
                    return
                valores[coluna] = valor
            try:
                schema = db.get_schema()
                cols_sql = ", ".join(valores.keys())
                placeholders = ", ".join(["%s"] * len(valores))

                def qname(table, schema):
                    return f'"{schema}"."{table}"' if schema else f'"{table}"'

                self.cursor.execute(
                    f'INSERT INTO {qname(self.current_table, schema)} ({cols_sql}) VALUES ({placeholders})',
                    tuple(valores.values()))
                self.conn.commit()
                messagebox.showinfo(self._t("success"), self._t("record_added"))
                self.carregar_tabela(self.current_table)
                dialog.destroy()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror(self._t("error"), self._t("add_record_error", e=e))

        btn = ctk.CTkFrame(main)
        btn.pack(fill="x", pady=10)
        BotaoPadronizado.criar_botao(btn, text=self._t("save"), command=salvar,
                      fg_color="#28a745", hover_color="#218838").pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(btn, text=self._t("cancel"), command=dialog.destroy,
                      fg_color="#6c757d", hover_color="#5a6268").pack(side="right", padx=5)

    def editar_registro(self):
        if not self.current_table:
            messagebox.showerror(self._t("error"), self._t("no_table_selected"))
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror(self._t("error"), self._t("no_record_selected"))
            return

        item = self.tree.item(selected[0])
        valores = item["values"]

        schema = db.get_schema()
        colunas_info = db.list_columns(self.current_table, schema=schema)

        if not colunas_info:
            messagebox.showerror(self._t("error"), "Não foi possível obter informações da tabela")
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title(self._t("edit_record_title", table=self.current_table))
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        self._center_window(dialog, 600, 500)

        main = ctk.CTkScrollableFrame(dialog)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        entries = {}
        for i, info in enumerate(colunas_info):
            col_name, col_type = info["column_name"], info["data_type"]
            frame = ctk.CTkFrame(main)
            frame.pack(fill="x", pady=5)
            label = f"{col_name} ({col_type})"
            ctk.CTkLabel(frame, text=label).pack(side="left", padx=5)

            if i != 0:  # Assumindo que a primeira coluna é a PK
                e = ctk.CTkEntry(frame)
                e.insert(0, "" if valores[i] is None else str(valores[i]))
                e.pack(side="right", fill="x", expand=True, padx=5)
                entries[col_name] = e
            else:
                ctk.CTkLabel(frame, text=str(valores[i])).pack(side="right", padx=5)

        def salvar_edicao():
            try:
                pk_col = colunas_info[0]["column_name"]
                pk_val = valores[0]

                sets = []
                params = []
                for col_name, e in entries.items():
                    sets.append(f'"{col_name}" = %s')
                    params.append(e.get())
                params.append(pk_val)
                schema = db.get_schema()

                def qname(table, schema):
                    return f'"{schema}"."{table}"' if schema else f'"{table}"'

                self.cursor.execute(
                    f'UPDATE {qname(self.current_table, schema)} SET {", ".join(sets)} WHERE "{pk_col}" = %s',
                    tuple(params))
                self.conn.commit()
                messagebox.showinfo(self._t("success"), self._t("record_updated"))
                self.carregar_tabela(self.current_table)
                dialog.destroy()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror(self._t("error"), self._t("edit_record_error", e=e))

        btn = ctk.CTkFrame(main)
        btn.pack(fill="x", pady=10)
        BotaoPadronizado.criar_botao(btn, text=self._t("save"), command=salvar_edicao,
                      fg_color="#28a745", hover_color="#218838").pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(btn, text=self._t("cancel"), command=dialog.destroy,
                      fg_color="#6c757d", hover_color="#5a6268").pack(side="right", padx=5)

    def excluir_registro(self):
        if not self.current_table:
            messagebox.showerror(self._t("error"), self._t("no_table_selected"))
            return

        selecionados = self.tree.selection()
        if not selecionados:
            messagebox.showwarning(self._t("warning"), self._t("no_record_selected"))
            return

        try:
            schema = db.get_schema()
            cols = db.list_columns(self.current_table, schema=schema)
            pk_col = cols[0]["column_name"]
            pk_index = 0
            ids = []
            for item in selecionados:
                valores = self.tree.item(item).get("values", [])
                if valores:
                    ids.append(valores[pk_index])

            if not ids:
                messagebox.showerror(self._t("error"), "Não foi possível determinar os IDs dos registros selecionados.")
                return

            placeholders = ", ".join(["%s"] * len(ids))

            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            self.cursor.execute(f'DELETE FROM {qname(self.current_table, schema)} WHERE "{pk_col}" IN ({placeholders})',
                                tuple(ids))
            self.conn.commit()
            messagebox.showinfo(self._t("success"), self._t("records_deleted", count=len(ids)))
            self.carregar_tabela(self.current_table)

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(self._t("error"), self._t("delete_records_error", e=e))

    def exportar_dados(self):
        if not self.current_table:
            messagebox.showerror(self._t("error"), self._t("no_table_selected"))
            return
        try:
            schema = db.get_schema()
            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'
            self.cursor.execute(f"SELECT * FROM {qname(self.current_table, schema)}")
            dados = self.cursor.fetchall()
            cols_info = db.list_columns(self.current_table, schema)
            colunas = [c["column_name"] for c in cols_info]
            linhas = [",".join(colunas)]
            if dados and isinstance(dados[0], dict):
                for r in dados:
                    linhas.append(",".join([f'"{"" if r.get(c) is None else str(r.get(c))}"' for c in colunas]))
            else:
                for row in dados:
                    linhas.append(",".join([f'"{"" if v is None else str(v)}"' for v in row]))
            arquivo = filedialog.asksaveasfilename(defaultextension=".csv",
                                                   filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                                                   title=self._t("export"))
            if arquivo:
                with open(arquivo, "w", encoding="utf-8") as f:
                    f.write("\n".join(linhas))
                messagebox.showinfo(self._t("success"), self._t("data_exported", arquivo=arquivo))
        except Exception as e:
            messagebox.showerror(self._t("error"), self._t("export_error", e=e))

    def executar_sql_personalizado(self):
        import sqlparse
        import re

        if not self.conn:
            messagebox.showerror(self._t("error"), "Nenhuma conexão ativa com o banco de dados.")
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title(self._t("advanced_sql_console"))
        dialog.geometry("1100x700")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_force()
        self._center_window(dialog, 1100, 700)

        main = ctk.CTkFrame(dialog)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        top_bar = ctk.CTkFrame(main, fg_color="transparent")
        top_bar.pack(fill="x", pady=5)
        ctk.CTkLabel(top_bar, text=self._t("sql_console"), font=("Arial", 16, "bold")).pack(side="left", padx=5)
        status_label = ctk.CTkLabel(top_bar, text=self._t("sql_ready"), text_color=get_contraste_texto(getattr(self.sistema, "cor_secundaria", "#E0E0E0")))
        status_label.pack(side="right", padx=10)

        editor_frame = ctk.CTkFrame(main)
        editor_frame.pack(fill="both", expand=False, pady=(5, 10))
        sql_text = ctk.CTkTextbox(editor_frame, height=200, font=("Consolas", 13))
        sql_text.pack(fill="both", expand=True, padx=5, pady=5)
        sql_text.insert("1.0", self._t("sql_placeholder"))

        result_frame = ctk.CTkFrame(main)
        result_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(result_frame, text=self._t("results"), font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=2)

        tree_container = ctk.CTkFrame(result_frame)
        tree_container.pack(fill="both", expand=True)
        scroll_x = ttk.Scrollbar(tree_container, orient="horizontal")
        scroll_y = ttk.Scrollbar(tree_container, orient="vertical")
        self.result_tree = ttk.Treeview(
            tree_container,
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set,
            selectmode="extended"
        )
        scroll_x.config(command=self.result_tree.xview)
        scroll_y.config(command=self.result_tree.yview)
        scroll_x.pack(side="bottom", fill="x")
        scroll_y.pack(side="right", fill="y")
        self.result_tree.pack(side="left", fill="both", expand=True)
        self._bind_ctrl_a_treeview(self.result_tree)
        self._bind_copy_treeview(self.result_tree)

        def executar_sql(*_):
            sql = sql_text.get("1.0", "end").strip()
            if not sql:
                messagebox.showwarning(self._t("warning"), "Digite um comando SQL.")
                return

            inicio = time.time()
            status_label.configure(text=self._t("sql_executing"), text_color="orange")
            dialog.update_idletasks()

            erros_ignoraveis = [
                "already exists",
                "does not exist",
                "duplicate key",
                "duplicate column",
                "constraint",
                "relation",
                "column",
            ]

            sql_sem_comentarios = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
            sql_sem_comentarios = re.sub(r"/\*.*?\*/", "", sql_sem_comentarios, flags=re.DOTALL)
            comandos = [c.strip() for c in sqlparse.split(sql_sem_comentarios) if c.strip()]

            total_afetadas = 0
            total_erros = 0
            total_ok = 0

            try:
                self.result_tree.delete(*self.result_tree.get_children())
                self.result_tree["columns"] = []

                for comando in comandos:
                    try:
                        self.cursor.execute(comando)

                        if self.cursor.description:
                            cols = [d[0] for d in self.cursor.description]
                            self.result_tree["columns"] = cols
                            self.result_tree["show"] = "headings"
                            for c in cols:
                                self.result_tree.heading(c, text=self._format_column_header(c))
                                self.result_tree.column(c, width=150, stretch=True)

                            rows = self.cursor.fetchall()
                            for r in rows:
                                if isinstance(r, dict):
                                    self.result_tree.insert("", "end", values=[r.get(c) for c in cols])
                                else:
                                    self.result_tree.insert("", "end", values=r)
                            total_ok += 1

                        else:
                            total_afetadas += self.cursor.rowcount
                            self.conn.commit()
                            total_ok += 1

                    except Exception as e_cmd:
                        msg = str(e_cmd).lower()
                        ignorar = any(p in msg for p in erros_ignoraveis)
                        safe_erro = str(e_cmd).encode("utf-8", "replace").decode("utf-8")
                        if ignorar:
                            self.logger.warning("Erro leve ignorado", detalhes={"comando": comando, "erro": msg})
                            self.conn.rollback()
                            total_erros += 1
                            continue
                        else:
                            self.conn.rollback()
                            total_erros += 1
                            self.logger.error("Erro grave em SQL", detalhes={"erro": msg, "sql": comando})
                            messagebox.showerror(self._t("error"), self._t("sql_execution_error", erro=safe_erro))
                            break

                duracao = (time.time() - inicio) * 1000
                cor_status = "green" if total_erros == 0 else "orange"
                status_label.configure(
                    text=self._t("sql_execution_finished", ok=total_ok, erros=total_erros, afetadas=total_afetadas, tempo=duracao),
                    text_color=cor_status)
                self.logger.info("Execução SQL finalizada",
                                 detalhes={"comandos_total": len(comandos), "sucesso": total_ok,
                                           "ignorados": total_erros, "afetadas": total_afetadas, "tempo_ms": duracao})

            except Exception as e:
                self.conn.rollback()
                safe_erro = str(e).encode("utf-8", "replace").decode("utf-8")
                status_label.configure(text=self._t("error"), text_color="red")
                messagebox.showerror(self._t("error"), self._t("sql_execution_error", erro=safe_erro))
                self.logger.error("Erro geral em console SQL", detalhes={"erro": safe_erro})

        def salvar_script():
            arquivo = filedialog.asksaveasfilename(defaultextension=".sql", filetypes=[("SQL", "*.sql")])
            if arquivo:
                with open(arquivo, "w", encoding="utf-8") as f:
                    f.write(sql_text.get("1.0", "end"))
                status_label.configure(text=self._t("sql_saved", arquivo=arquivo), text_color="blue")

        def abrir_script():
            arquivo = filedialog.askopenfilename(filetypes=[("SQL", "*.sql"), ("Todos", "*.*")])
            if arquivo:
                with open(arquivo, "r", encoding="utf-8") as f:
                    sql_text.delete("1.0", "end")
                    sql_text.insert("1.0", f.read())
                status_label.configure(text=self._t("sql_loaded", arquivo=arquivo), text_color="blue")

        def exportar_csv():
            if not self.result_tree.get_children():
                messagebox.showinfo(self._t("info"), self._t("no_results"))
                return
            arquivo = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if not arquivo:
                return
            cols = self.result_tree["columns"]
            with open(arquivo, "w", encoding="utf-8") as f:
                f.write(",".join(cols) + "\n")
                for iid in self.result_tree.get_children():
                    vals = self.result_tree.item(iid)["values"]
                    linha = ",".join([str(v or "").replace("\n", " ").replace("\r", "") for v in vals])
                    f.write(linha + "\n")
            messagebox.showinfo(self._t("export"), self._t("data_exported", arquivo=arquivo))

        def copiar_resultados():
            ok = self._copiar_linhas_treeview(self.result_tree, incluir_cabecalho=True, apenas_selecionadas=True)
            if not ok:
                messagebox.showinfo(self._t("info"), self._t("no_rows_selected"))
                return
            status_label.configure(text=self._t("copied_to_clipboard"), text_color="blue")

        btn_frame = ctk.CTkFrame(main)
        btn_frame.pack(fill="x", pady=10)
        BotaoPadronizado.criar_botao(btn_frame, text=self._t("run_sql"), command=executar_sql,
                      fg_color="#28a745", hover_color="#218838").pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(btn_frame, text=self._t("save_script"), command=salvar_script,
                      fg_color="#17a2b8", hover_color="#138496").pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(btn_frame, text=self._t("open_script"), command=abrir_script,
                      fg_color="#007bff", hover_color="#0056b3").pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(btn_frame, text=self._t("copy"), command=copiar_resultados,
                      fg_color="#17a2b8", hover_color="#138496").pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(btn_frame, text=self._t("export_csv"), command=exportar_csv,
                      fg_color="#ffc107", hover_color="#e0a800", text_color="black").pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(btn_frame, text=self._t("close"), command=dialog.destroy,
                      fg_color="#6c757d", hover_color="#5a6268").pack(side="right", padx=5)

        dialog.bind("<Control-Return>", executar_sql)
        dialog.bind("<Control-s>", lambda e: salvar_script())
        dialog.bind("<Control-o>", lambda e: abrir_script())
        dialog.bind("<Control-c>", lambda e: copiar_resultados())
        dialog.bind("<Control-C>", lambda e: copiar_resultados())

        self.logger.info("Console SQL aberto", detalhes={"usuario": "admin", "schema": db.get_schema()})

    def operacoes_avancadas(self):
        if not self.modo_admin:
            messagebox.showwarning(self._t("insufficient_privileges"), self._t("admin_required"))
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title(self._t("advanced_admin_operations_title"))
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        self._center_window(dialog, 500, 400)

        main = ctk.CTkFrame(dialog)
        main.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main, text=self._t("admin_ops_header"), font=("Arial", 16, "bold")).pack(pady=10)

        ops = [
            (self._t("recreate_schema"), self.recriar_schema),
            (self._t("database_statistics"), self.estatisticas_banco),
            (self._t("view_connections"), self.ver_conexoes_ativas),
            (self._t("quick_backup"), self.backup_rapido),
            (self._t("manage_schemas"), self.gerenciar_schemas),
            (self._t("manage_users"), self.gerenciar_usuarios)
        ]

        for texto, comando in ops:
            btn = BotaoPadronizado.criar_botao(main, text=texto, command=comando,
                                fg_color="#17a2b8", hover_color="#138496", height=40)
            btn.pack(fill="x", pady=5)

    def recriar_schema(self):
        if not messagebox.askyesno(self._t("warning"), self._t("recreate_schema_confirm")):
            return
        try:
            schema = db.get_schema()
            self.cursor.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            self.cursor.execute(f"CREATE SCHEMA {schema}")
            self.conn.commit()
            messagebox.showinfo(self._t("success"), self._t("schema_recreated", schema=schema))
            self.atualizar_lista_tabelas()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(self._t("error"), self._t("recreate_schema_error", e=e))

    def estatisticas_banco(self):
        try:
            schema = db.get_schema()
            stats_sql = """
                SELECT schemaname, tablename, tableowner, tablespace, hasindexes, hasrules, hastriggers
                FROM pg_tables WHERE schemaname = %s ORDER BY tablename;
            """
            self.cursor.execute(stats_sql, (schema,))
            tabelas = self.cursor.fetchall()

            info_sql = """
                SELECT COUNT(*) as total_tabelas, SUM(n_live_tup) as total_registros,
                       SUM(pg_total_relation_size(schemaname||'.'||tablename)) as tamanho_total_bytes
                FROM pg_stat_user_tables WHERE schemaname = %s;
            """
            self.cursor.execute(info_sql, (schema,))
            info = self.cursor.fetchone()

            mensagem = f"📊 ESTATÍSTICAS DO SCHEMA: {schema}\n\n"
            mensagem += f"Total de Tabelas: {info['total_tabelas']}\n"
            mensagem += f"Total de Registros: {info['total_registros']}\n"
            mensagem += f"Tamanho Total: {info['tamanho_total_bytes'] // 1024 // 1024} MB\n\n"
            mensagem += "Tabelas no Schema:\n"
            for tabela in tabelas:
                mensagem += f"• {tabela['tablename']} (por: {tabela['tableowner']})\n"

            messagebox.showinfo("Estatísticas do Banco", mensagem)
        except Exception as e:
            messagebox.showerror(self._t("error"), self._t("statistics_error", e=e))

    def ver_conexoes_ativas(self):
        try:
            self.cursor.execute("""
                SELECT pid, usename, application_name, client_addr, client_port, state, query_start, query
                FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start;
            """)
            conexoes = self.cursor.fetchall()

            mensagem = "🔍 CONEXÕES ATIVAS NO BANCO:\n\n"
            if not conexoes:
                mensagem += "Nenhuma conexão ativa no momento."
            else:
                for i, conn in enumerate(conexoes, 1):
                    mensagem += f"{i}. PID: {conn['pid']} | User: {conn['usename']}\n"
                    mensagem += f"   App: {conn['application_name']} | IP: {conn['client_addr']}\n"
                    mensagem += f"   Query: {conn['query'][:100]}...\n\n"

            messagebox.showinfo("Conexões Ativas", mensagem)
        except Exception as e:
            messagebox.showerror(self._t("error"), self._t("connections_error", e=e))

    def backup_rapido(self):
        try:
            schema = db.get_schema()
            backup_file = filedialog.asksaveasfilename(
                defaultextension=".sql",
                filetypes=[("SQL Files", "*.sql"), ("All Files", "*.*")],
                title="Salvar Backup Como",
                initialfile=f"backup_{schema}_{time.strftime('%Y%m%d_%H%M%S')}.sql"
            )

            if backup_file:
                messagebox.showinfo(self._t("info"), self._t("quick_backup_info"))
                # Simulação de backup
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(f"-- Backup do Schema {schema}\n")
                    f.write(f"-- Gerado em: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                messagebox.showinfo(self._t("success"), self._t("backup_created", arquivo=backup_file))
        except Exception as e:
            messagebox.showerror(self._t("error"), self._t("backup_error", e=e))

    def gerenciar_schemas(self):
        try:
            self.cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT LIKE 'pg_%' 
                AND schema_name != 'information_schema'
                ORDER BY schema_name;
            """)
            schemas = self.cursor.fetchall()

            dialog = ctk.CTkToplevel(self.root)
            dialog.title(self._t("manage_schemas_title"))
            dialog.geometry("400x300")
            dialog.transient(self.root)
            dialog.grab_set()
            self._center_window(dialog, 400, 300)

            main = ctk.CTkFrame(dialog)
            main.pack(fill="both", expand=True, padx=10, pady=10)

            ctk.CTkLabel(main, text=self._t("schemas_available"), font=("Arial", 12, "bold")).pack(pady=5)

            schema_list = ctk.CTkScrollableFrame(main)
            schema_list.pack(fill="both", expand=True, pady=5)

            for schema in schemas:
                frame = ctk.CTkFrame(schema_list)
                frame.pack(fill="x", pady=2)
                ctk.CTkLabel(frame, text=schema['schema_name']).pack(side="left", padx=5)

                if schema['schema_name'] != db.get_schema():
                    BotaoPadronizado.criar_botao(frame, text=self._t("use_schema"), width=60,
                                  command=lambda s=schema['schema_name']: self.usar_schema(s, dialog),
                                  fg_color="#28a745", hover_color="#218838").pack(side="right", padx=2)

        except Exception as e:
            messagebox.showerror(self._t("error"), self._t("schema_manage_error", e=e))

    def usar_schema(self, schema_nome, parent):
        try:
            global _cfg
            _cfg["schema"] = schema_nome
            self.db_entry.delete(0, "end")
            self.db_entry.insert(0, schema_nome)
            self.conectar_como_admin()
            parent.destroy()
            messagebox.showinfo(self._t("success"), self._t("schema_switched", schema=schema_nome))
        except Exception as e:
            messagebox.showerror(self._t("error"), self._t("schema_switch_error", e=e))

    def gerenciar_usuarios(self):
        try:
            self.cursor.execute("""
                SELECT usename, usesuper, usecreatedb, usebypassrls, valuntil
                FROM pg_user ORDER BY usename;
            """)
            usuarios = self.cursor.fetchall()

            mensagem = "👥 USUÁRIOS DO BANCO:\n\n"
            for user in usuarios:
                privilegios = []
                if user['usesuper']:
                    privilegios.append("SUPERUSER")
                if user['usecreatedb']:
                    privilegios.append("CREATEDB")
                if user['usebypassrls']:
                    privilegios.append("BYPASSRLS")

                mensagem += f"• {user['usename']}\n"
                mensagem += f"  Privilégios: {', '.join(privilegios) if privilegios else 'Nenhum'}\n"
                if user['valuntil']:
                    mensagem += f"  Validade: {user['valuntil']}\n"
                mensagem += "\n"

            messagebox.showinfo("Usuários do Banco", mensagem)
        except Exception as e:
            messagebox.showerror(self._t("error"), self._t("user_manage_error", e=e))

    def editar_tabela_completa(self):
        if not self.current_table:
            messagebox.showerror(self._t("error"), self._t("no_table_selected"))
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title(self._t("edit_table_title", table=self.current_table))
        dialog.geometry("1000x700")
        dialog.transient(self.root)
        dialog.grab_set()
        self._center_window(dialog, 1000, 700)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab_estrutura = ctk.CTkFrame(notebook)
        notebook.add(tab_estrutura, text=self._t("table_structure"))
        frame_titulo = ctk.CTkFrame(tab_estrutura, fg_color="transparent")
        frame_titulo.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(frame_titulo, text=f"EDIÇÃO DE COLUNAS - {self.current_table}", font=("Arial", 14, "bold")).pack(side="left")

        frame_tree = ctk.CTkFrame(tab_estrutura)
        frame_tree.pack(fill="both", expand=True, pady=10)
        cols = ("cid", "name", "type", "notnull", "dflt_value", "pk")
        tree_estrutura = ttk.Treeview(frame_tree, columns=cols, show="headings", height=15, selectmode="browse")
        for c in cols:
            tree_estrutura.heading(c, text=self._format_column_header(c))
            tree_estrutura.column(c, width=120, anchor="w")

        schema = db.get_schema()
        colunas = db.list_columns(self.current_table, schema)
        for i, col in enumerate(colunas):
            col_name = col.get("column_name") or col.get("name") or col.get("coluna") or ""
            col_type = col.get("data_type") or col.get("type") or col.get("udt_name") or ""
            col_default = col.get("column_default") or col.get("default") or ""

            raw_nullable = col.get("is_nullable", col.get("nullable", "YES"))
            if isinstance(raw_nullable, bool):
                nullable_disp = "YES" if raw_nullable else "NO"
            else:
                nullable_disp = str(raw_nullable).strip().upper()
                if nullable_disp in ("TRUE", "T", "SIM", "S", "1"):
                    nullable_disp = "YES"
                elif nullable_disp in ("FALSE", "F", "NAO", "NÃO", "N", "0"):
                    nullable_disp = "NO"
                elif nullable_disp not in ("YES", "NO"):
                    nullable_disp = "YES"

            tree_estrutura.insert("", "end", values=(
                i + 1,
                col_name,
                col_type,
                nullable_disp,
                col_default,
                ""
            ))

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical", command=tree_estrutura.yview)
        scroll_y.pack(side="right", fill="y")
        tree_estrutura.configure(yscrollcommand=scroll_y.set)
        tree_estrutura.pack(side="left", fill="both", expand=True)

        frame_controles = ctk.CTkFrame(tab_estrutura)
        frame_controles.pack(fill="x", pady=10)
        BotaoPadronizado.criar_botao(frame_controles, text=f"➕ {self._t('add_column')}", command=lambda: self._adicionar_coluna_dialog(dialog),
                      fg_color="#28a745", hover_color="#218838", width=150).pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(frame_controles, text=f"➖ {self._t('remove_column')}",
                      command=lambda: self._remover_coluna_dialog(tree_estrutura, dialog),
                      fg_color="#dc3545", hover_color="#c82333", width=150).pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(frame_controles, text=f"✏️ {self._t('rename_column')}",
                      command=lambda: self._renomear_coluna_dialog(tree_estrutura, dialog),
                      fg_color="#17a2b8", hover_color="#138496", width=150).pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(frame_controles, text=f"🗑️ {self._t('delete_table')}",
                      command=lambda: self._confirmar_exclusao_tabela(dialog),
                      fg_color="#dc3545", hover_color="#c82333", width=150).pack(side="left", padx=5)
        BotaoPadronizado.criar_botao(frame_controles, text=f"❌ {self._t('close_editor')}", command=dialog.destroy,
                      fg_color="#6c757d", hover_color="#5a6268").pack(side="right", padx=5)

        tab_dados = ctk.CTkFrame(notebook)
        notebook.add(tab_dados, text=self._t("data_view"))
        frame_dados = ctk.CTkFrame(tab_dados)
        frame_dados.pack(fill="both", expand=True, padx=10, pady=10)
        self._atualizar_tree_dados(frame_dados, self.current_table)

    def _confirmar_exclusao_tabela(self, parent=None):
        if not self.current_table:
            messagebox.showerror(self._t("error"), self._t("no_table_selected"))
            return
        if not messagebox.askyesno(self._t("confirm_deletion"), self._t("delete_table_warning", table=self.current_table), parent=parent):
            return

        try:
            schema = db.get_schema()
            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'
            self.cursor.execute(f"DROP TABLE {qname(self.current_table, schema)} CASCADE")
            self.conn.commit()
            messagebox.showinfo(self._t("success"), f"Tabela '{self.current_table}' e dependências foram removidas com sucesso!",
                                parent=parent)
            parent.destroy()
            self.current_table = None
            self.atualizar_lista_tabelas()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(self._t("error"), f"Falha ao excluir tabela:\n{e}", parent=parent)

    def _adicionar_coluna_dialog(self, parent):
        self.adicionar_coluna(parent)

    def _remover_coluna_dialog(self, tree, parent):
        selected = tree.selection()
        if not selected:
            messagebox.showerror(self._t("error"), "Selecione uma coluna para remover")
            return
        col_data = tree.item(selected[0])["values"]
        col_name = col_data[1]
        if not messagebox.askyesno(self._t("confirm_deletion"),
                                   f"Remover a coluna '{col_name}'?\nEsta ação não pode ser desfeita!", parent=parent):
            return
        try:
            schema = db.get_schema()
            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'
            self.cursor.execute(f'ALTER TABLE {qname(self.current_table, schema)} DROP COLUMN "{col_name}"')
            self.conn.commit()
            messagebox.showinfo(self._t("success"), f"Coluna '{col_name}' removida!")
            parent.destroy()
            self.editar_tabela_completa()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(self._t("error"), f"Falha ao remover coluna:\n{e}")

    def _renomear_coluna_dialog(self, tree, parent):
        self.renomear_coluna(tree, parent)

    def _atualizar_tree_dados(self, parent_frame, tabela):
        for w in parent_frame.winfo_children():
            w.destroy()

        frame_tree = ctk.CTkFrame(parent_frame)
        frame_tree.pack(fill="both", expand=True)

        schema = db.get_schema()
        cols = db.list_columns(tabela, schema)
        colnames = [c["column_name"] for c in cols]

        tree = ttk.Treeview(frame_tree, columns=colnames, show="headings")
        for c in colnames:
            tree.heading(c, text=self._format_column_header(c))
            tree.column(c, width=120, stretch=True)

        def qname(table, schema):
            return f'"{schema}"."{table}"' if schema else f'"{table}"'

        self.cursor.execute(f"SELECT * FROM {qname(tabela, schema)}")
        rows = self.cursor.fetchall()
        if rows and isinstance(rows[0], dict):
            for r in rows:
                tree.insert("", "end", values=[r.get(c) for c in colnames])
        else:
            for r in rows:
                tree.insert("", "end", values=r)

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
        scroll_y.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scroll_y.set)

        scroll_x = ttk.Scrollbar(frame_tree, orient="horizontal", command=tree.xview)
        scroll_x.pack(side="bottom", fill="x")
        tree.configure(xscrollcommand=scroll_x.set)

        tree.pack(side="left", fill="both", expand=True)

    def _abrir_seletor_tabelas(self):
        if not self.conn:
            messagebox.showerror(self._t("error"), "Nenhum banco de dados conectado.")
            return
        schema = db.get_schema()
        todas = db.list_tables(schema=schema)
        if not todas:
            messagebox.showinfo(self._t("info"), "Nenhuma tabela encontrada no banco.")
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title(self._t("select_table_title"))
        dialog.geometry("400x500")
        dialog.update_idletasks()
        self._center_window(dialog, 400, 500)
        dialog.transient(self.root)
        dialog.grab_set()

        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(dialog, textvariable=search_var, placeholder_text=self._t("search_table"))
        search_entry.pack(fill="x", padx=10, pady=(10, 0))

        scroll = ctk.CTkScrollableFrame(dialog)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        botoes = []

        def refresh():
            termo = (search_var.get() or "").lower()
            for b in botoes:
                b.destroy()
            botoes.clear()
            for t in [t for t in todas if termo in t.lower()]:
                b = BotaoPadronizado.criar_botao(scroll, text=t, command=lambda _t=t: self._selecionar_tabela(_t, dialog),
                                  fg_color="#17a2b8", hover_color="#138496")
                b.pack(fill="x", padx=5, pady=2)
                botoes.append(b)

        search_var.trace_add("write", lambda *_: refresh())
        refresh()

    def _selecionar_tabela(self, nome_tabela, janela):
        self.selected_table_var.set(nome_tabela)
        self.current_table = nome_tabela
        self.table_button.configure(text=nome_tabela)
        self.carregar_tabela(nome_tabela)
        janela.destroy()


class BancoDadosFabricaApp(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None):
        super().__init__(master)
        self.pack(fill="both", expand=True)
        self.root = self._get_root()
        self.gerenciador = GerenciadorBancoDados(sistema=sistema or self, frame=self)

    def _get_root(self):
        w = self
        while w.master is not None:
            w = w.master
        return w


if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Gerenciador de Banco de Dados - SUPER ADMIN")
    root.geometry("1280x700")

    frame = ctk.CTkFrame(root)
    frame.pack(fill="both", expand=True)

    gerenciador = GerenciadorBancoDados(sistema=root, frame=frame)

    root.mainloop()
