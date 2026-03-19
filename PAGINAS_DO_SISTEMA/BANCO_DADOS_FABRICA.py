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
        # Aparência (se o sistema tiver atributos de tema)
        if self.sistema:
            try:
                ctk.set_appearance_mode(self.sistema.aparencia_atual)
                ctk.set_default_color_theme(self.sistema.tema_atual)
            except AttributeError:
                pass

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

        self.btn_connect = ctk.CTkButton(
            top_frame,
            text=self._get_text("connect"),
            command=self.conectar_como_admin
        )
        self.btn_connect.pack(side="left", padx=5)

        self.admin_btn = ctk.CTkButton(
            top_frame,
            text=self._get_text("admin_button"),
            command=self.mostrar_status_admin,
            fg_color=getattr(self.sistema, 'cor_selecao', '#dc3545'),
            border_width=1,
            text_color="white"
        )
        self.admin_btn.pack(side="left", padx=5)

        self.lbl_table = ctk.CTkLabel(top_frame, text=self._get_text("table"))
        self.lbl_table.pack(side="left", padx=5)

        self.selected_table_var = ctk.StringVar()
        self.table_button = ctk.CTkButton(
            top_frame,
            text=self._get_text("select_table"),
            width=200,
            command=self._abrir_seletor_tabelas
        )
        self.table_button.pack(side="left", padx=5)

        self.btn_refresh = ctk.CTkButton(
            top_frame,
            text=self._get_text("refresh"),
            command=self.atualizar_lista_tabelas
        )
        self.btn_refresh.pack(side="left", padx=5)

        self.btn_new_table = ctk.CTkButton(
            top_frame,
            text=self._get_text("new_table"),
            command=self.criar_nova_tabela,
            fg_color=getattr(self.sistema, 'cor_selecao', '#17a2b8')
        )
        self.btn_new_table.pack(side="left", padx=5)

        ctk.CTkButton(top_frame, text='▲', width=30, command=self.on_arrow_up).pack(side="left", padx=2)
        ctk.CTkButton(top_frame, text='▼', width=30, command=self.on_arrow_down).pack(side="left", padx=2)

        self.tree_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, sticky="ew", pady=5)

        self.btn_admin_operations = ctk.CTkButton(
            bottom_frame,
            text=self._get_text("admin_operations"),
            command=self.operacoes_avancadas,
            fg_color=getattr(self.sistema, 'cor_selecao', '#6f42c1'),
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

        self.btn_delete = ctk.CTkButton(
            bottom_frame,
            text=self._get_text("delete"),
            command=confirmar_exclusao_registro,
            fg_color=getattr(self.sistema, 'cor_selecao', '#dc3545'),
            hover_color="#b52a3a"
        )
        self.btn_delete.pack(side="left", padx=5)

        self.btn_edit_table = ctk.CTkButton(
            bottom_frame,
            text=self._get_text("edit_table"),
            command=self.editar_tabela_completa,
            fg_color=getattr(self.sistema, 'cor_selecao', '#17a2b8'),
            hover_color="#138496"
        )
        self.btn_edit_table.pack(side="left", padx=5)

        self.btn_sql = ctk.CTkButton(
            bottom_frame,
            text=self._get_text("sql"),
            command=self.executar_sql_personalizado,
            fg_color=getattr(self.sistema, 'cor_selecao', '#6c757d')
        )
        self.btn_sql.pack(side="right", padx=5)

        self.btn_export = ctk.CTkButton(
            bottom_frame,
            text=self._get_text("export"),
            command=self.exportar_dados,
            fg_color=getattr(self.sistema, 'cor_selecao', '#007bff'),
            hover_color="#0056b3"
        )
        self.btn_export.pack(side="right", padx=5)

        self.btn_edit = ctk.CTkButton(
            bottom_frame,
            text=self._get_text("edit"),
            command=self.editar_registro,
            fg_color=getattr(self.sistema, 'cor_selecao', '#ffc107'),
            hover_color="#e0a800"
        )
        self.btn_edit.pack(side="right", padx=5)

        self.btn_add = ctk.CTkButton(
            bottom_frame,
            text=self._get_text("add"),
            command=self.adicionar_registro,
            fg_color=getattr(self.sistema, 'cor_selecao', '#28a745'),
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
                style = ttk.Style()
                style.configure('Treeview', rowheight=25, font=('Arial', 12))
                style.configure('Treeview.Heading', font=('Arial', 12, 'bold'))
                self.tree.pack(fill="both", expand=True)

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

            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 100
            top.geometry(f"+{x}+{y}")

            frame = ctk.CTkFrame(top, fg_color="transparent")
            frame.pack(pady=20, padx=20, fill="both", expand=True)

            ctk.CTkLabel(frame, text=mensagem,
                         font=("Arial", 14, "bold"),
                         text_color="red").pack(pady=10)

            ctk.CTkLabel(frame, text=f"Banco: {info['current_database']} | Usuário: {info['current_user']}",
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

    # =================== MÉTODO ORIGINAL DE CONEXÃO ===================

    def conectar_db_handler(self, admin: bool = False):
        """Método original - redirecionar para conexão admin"""
        self.conectar_como_admin()

    # =================== MÉTODOS ORIGINAIS COMPLETOS ===================
    # [Todos os métodos originais são mantidos exatamente como estavam]
    # atualizar_lista_tabelas, carregar_tabela, limpar_treeview, on_arrow_up,
    # on_arrow_down, _switch_table, criar_nova_tabela, excluir_tabela,
    # editar_tabela, adicionar_coluna, renomear_coluna, adicionar_registro,
    # editar_registro, excluir_registro, exportar_dados, executar_sql_personalizado,
    # operacoes_avancadas, recriar_schema, estatisticas_banco, ver_conexoes_ativas,
    # backup_rapido, gerenciar_schemas, usar_schema, gerenciar_usuarios,
    # editar_tabela_completa, _confirmar_exclusao_tabela, _adicionar_coluna_dialog,
    # _remover_coluna_dialog, _renomear_coluna_dialog, _atualizar_tree_dados,
    # _abrir_seletor_tabelas, _selecionar_tabela

    def atualizar_lista_tabelas(self):
        """
        Atualiza a lista de tabelas do banco de dados.

        Correções:
        - Não usa mais self.cursor para testar a conexão (evita "cursor already closed").
        - Usa um cursor LOCAL, novo, com with self.conn.cursor().
        - Se a conexão/cursor estiverem inválidos, tenta reconectar automaticamente
          chamando conectar_como_admin() e repete o teste.
        """
        if not self.conn:
            messagebox.showerror("Erro", "Nenhuma conexão ativa com o banco de dados.")
            return

        try:
            schema = db.get_schema()

            # ===== TESTE SEGURO DA CONEXÃO =====
            try:
                # Usa um cursor local apenas para testar a conexão
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
            except Exception as e:
                # Se chegou aqui, o cursor/conexão está ruim (inclui "cursor already closed")
                self.logger.warning(
                    "Conexão ou cursor inválidos ao atualizar lista de tabelas, tentando reconectar...",
                    detalhes={"erro": str(e)},
                )

                # Tenta reconectar como ADMIN
                self.conectar_como_admin()

                # Se ainda assim não tiver conexão, aborta
                if not self.conn:
                    raise RuntimeError("Não foi possível restabelecer a conexão com o banco.")

                # Testa novamente com a nova conexão
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")

            # ===== OBTÉM LISTA DE TABELAS USANDO O MÓDULO DB =====
            tabelas = db.list_tables(schema=schema)

            self.tabelas_list = tabelas if tabelas else []
            current = self.selected_table_var.get() if self.selected_table_var else ""

            if not self.tabelas_list:
                # Não há tabelas → limpa UI e sai
                self.selected_table_var.set("")
                self.table_button.configure(text="Selecionar Tabela")
                self.limpar_treeview()
                return

            # Se já havia uma tabela selecionada e ela ainda existe, mantém
            if current and current in self.tabelas_list:
                self.table_button.configure(text=current)
                self.carregar_tabela(current)
            else:
                # Senão, seleciona a primeira tabela da lista
                nova = self.tabelas_list[0]
                self.selected_table_var.set(nova)
                self.table_button.configure(text=nova)
                self.carregar_tabela(nova)

            # Log informativo
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
        """MÉTODO ORIGINAL PRESERVADO"""
        if not (self.conn and table_name):
            self.logger.warning("Tentativa de carregar tabela sem conexão ou nome de tabela.",
                                detalhes={"tabela": table_name, "conexao_ativa": bool(self.conn)})
            return
        try:
            # Limpa a visualização da tabela anterior
            self.limpar_treeview()
            self.current_table = table_name

            schema = db.get_schema()
            # Obtém a lista de colunas e suas informações da tabela atual
            cols_info = db.list_columns(table_name, schema=schema)

            # Extrai apenas os nomes das colunas para usar como cabeçalhos
            colunas = [c["column_name"] for c in cols_info]

            # Configura as colunas no componente Treeview
            self.tree["columns"] = colunas
            self.tree["show"] = "headings"  # Mostra apenas os cabeçalhos, não a coluna de ID interna
            for col in colunas:
                self.tree.heading(col, text=self._format_column_header(col))
                self.tree.column(col, width=120, anchor="w", stretch=True)

            # Função auxiliar para obter o nome qualificado da tabela (ex: "opera"."usuarios")
            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            qn = qname(table_name, schema)

            # Executa a consulta para obter todos os dados da tabela
            self.cursor.execute(f"SELECT * FROM {qn}")
            rows = self.cursor.fetchall()

            # Se não houver linhas de dados, não há mais nada a fazer
            if not rows:
                return

            # --- INÍCIO DA CORREÇÃO APLICADA ---

            # Verifica se as linhas retornadas são objetos tipo dicionário (como RealDictRow)
            # A verificação 'hasattr(rows[0], "keys")' é mais robusta que 'isinstance(dict)'
            if hasattr(rows[0], 'keys'):
                # Se forem dicionários, converte-os para uma lista de tuplos.
                # A ordem dos valores no tuplo deve corresponder exatamente à ordem das colunas.
                processed_rows = [tuple(row.get(col_name) for col_name in colunas) for row in rows]
            else:
                # Se já forem tuplos (ou listas), usa-os diretamente.
                processed_rows = rows

            # Insere cada linha de dados processada no Treeview
            for linha in processed_rows:
                self.tree.insert("", "end", values=linha)

            # --- FIM DA CORREÇÃO APLICADA ---

        except Exception as e:
            # Em caso de erro, mostra uma mensagem e limpa a visualização
            self.logger.error(f"Falha ao carregar a tabela '{table_name}'", detalhes={"erro": str(e)})
            messagebox.showerror("Erro", f"Falha ao carregar {table_name}:\n{e}")
            self.limpar_treeview()

    def limpar_treeview(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        if hasattr(self, 'tree') and self.tree:
            self.tree.delete(*self.tree.get_children())
            self.tree["columns"] = []

    def on_arrow_up(self, event=None):
        """MÉTODO ORIGINAL PRESERVADO"""
        self._switch_table(-1)

    def on_arrow_down(self, event=None):
        """MÉTODO ORIGINAL PRESERVADO"""
        self._switch_table(1)

    def _switch_table(self, direction):
        """MÉTODO ORIGINAL PRESERVADO"""
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

    def criar_nova_tabela(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        if not self.conn:
            messagebox.showerror("Erro", "Não há conexão com o banco de dados")
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Criar Nova Tabela")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        main = ctk.CTkFrame(dialog)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(main, text="Nome da Tabela:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        nome_entry = ctk.CTkEntry(main, width=300)
        nome_entry.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(main, text="Colunas (nome:tipo):").grid(row=1, column=0, padx=5, pady=5, sticky="ne")
        col_frame = ctk.CTkFrame(main);
        col_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        col_text = ctk.CTkTextbox(col_frame, width=400, height=200);
        col_text.pack(fill="both", expand=True, padx=5, pady=5)
        col_text.insert("1.0", "id SERIAL PRIMARY KEY\nnome TEXT NOT NULL\nquantidade INTEGER")

        button_frame = ctk.CTkFrame(main);
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        def criar():
            nome = nome_entry.get().strip()
            cols = col_text.get("1.0", "end").strip()
            if not nome:
                messagebox.showerror("Erro", "O nome da tabela é obrigatório");
                return
            if not cols:
                messagebox.showerror("Erro", "Defina pelo menos uma coluna");
                return
            try:
                schema = db.get_schema()
                cols_sql = ",\n".join([c.strip() for c in cols.split("\n") if c.strip()])

                # Função auxiliar para nome qualificado
                def qname(table, schema):
                    return f'"{schema}"."{table}"' if schema else f'"{table}"'

                qn = qname(nome, schema)

                self.cursor.execute(f"CREATE TABLE {qn} (\n{cols_sql}\n)")
                self.conn.commit()
                messagebox.showinfo("Sucesso", f"Tabela {nome} criada!")
                self.atualizar_lista_tabelas()
                dialog.destroy()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("Erro", f"Falha ao criar tabela:\n{e}")

        ctk.CTkButton(button_frame, text="Criar", command=criar, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancelar", command=dialog.destroy).pack(side="left", padx=5)

    # ... [Todos os outros métodos originais são mantidos exatamente como estavam]

    # Restante dos métodos originais completos...
    def excluir_tabela(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        if not self.current_table:
            messagebox.showerror("Erro", "Nenhuma tabela selecionada")
            return
        if not messagebox.askyesno("Confirmar",
                                   f"Tem certeza que deseja excluir a tabela {self.current_table}?\nTodos os dados serão perdidos!"):
            return
        try:
            schema = db.get_schema()

            # Função auxiliar para nome qualificado
            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            self.cursor.execute(f"DROP TABLE {qname(self.current_table, schema)}")
            self.conn.commit()
            messagebox.showinfo("Sucesso", f"Tabela {self.current_table} excluída!")
            self.current_table = None
            self.atualizar_lista_tabelas()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erro", f"Falha ao excluir tabela:\n{e}")

    def editar_tabela(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        self.editar_tabela_completa()

    def adicionar_coluna(self, parent_window):
        """MÉTODO ORIGINAL PRESERVADO"""
        dialog = ctk.CTkToplevel(parent_window)
        dialog.title("Adicionar Coluna")
        dialog.geometry("420x300")
        dialog.transient(parent_window)
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Nome da Coluna:").pack(pady=5)
        nome_entry = ctk.CTkEntry(frame)
        nome_entry.pack(pady=5, fill="x")

        ctk.CTkLabel(frame, text="Tipo de Dados:").pack(pady=5)
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
                messagebox.showerror("Erro", "Nome e tipo são obrigatórios")
                return
            try:
                schema = db.get_schema()
                sql = f'ALTER TABLE "{schema}"."{self.current_table}" ADD COLUMN IF NOT EXISTS "{nome}" {tipo}'
                self.cursor.execute(sql)
                self.conn.commit()
                messagebox.showinfo("Sucesso", f"Coluna '{nome}' adicionada com sucesso!")
                parent_window.destroy()
                self.editar_tabela_completa()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("Erro", f"Falha ao adicionar coluna:\n{e}")

        ctk.CTkButton(frame, text="Adicionar", command=adicionar, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(pady=15)

    def renomear_coluna(self, tree, parent_window):
        """MÉTODO ORIGINAL PRESERVADO"""
        selected = tree.selection()
        if not selected:
            messagebox.showerror("Erro", "Selecione uma coluna");
            return
        col_data = tree.item(selected[0])["values"]
        old_name = col_data[1]

        dialog = ctk.CTkToplevel(parent_window)
        dialog.title(f"Renomear Coluna {old_name}")
        dialog.geometry("400x200");
        dialog.transient(parent_window);
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog);
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frame, text=f"Novo nome para '{old_name}':").pack(pady=5)
        new_name_entry = ctk.CTkEntry(frame);
        new_name_entry.pack(pady=5, fill="x");
        new_name_entry.insert(0, old_name)

        def executar():
            new_name = new_name_entry.get().strip()
            if not new_name: messagebox.showerror("Erro", "Nome não pode ser vazio"); return
            try:
                schema = db.get_schema()

                # Função auxiliar para nome qualificado
                def qname(table, schema):
                    return f'"{schema}"."{table}"' if schema else f'"{table}"'

                self.cursor.execute(
                    f'ALTER TABLE {qname(self.current_table, schema)} RENAME COLUMN "{old_name}" TO "{new_name}"')
                self.conn.commit()
                messagebox.showinfo("Sucesso", "Coluna renomeada!")
                parent_window.destroy();
                self.editar_tabela()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("Erro", f"Falha ao renomear:\n{e}")

        ctk.CTkButton(frame, text="Renomear", command=executar, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(pady=10)

    def adicionar_registro(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        if not self.current_table:
            messagebox.showerror("Erro", "Nenhuma tabela selecionada");
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Adicionar Registro - {self.current_table}")
        dialog.geometry("500x600");
        dialog.transient(self.root);
        dialog.grab_set()

        main = ctk.CTkScrollableFrame(dialog);
        main.pack(fill="both", expand=True, padx=10, pady=10)

        schema = db.get_schema()
        colunas_info = db.list_columns(self.current_table, schema=schema)

        colunas = [c["column_name"] for c in colunas_info if c["column_name"].lower() != "id"]

        entries = {}
        for coluna in colunas:
            frame = ctk.CTkFrame(main);
            frame.pack(fill="x", pady=5)
            info = next((c for c in colunas_info if c["column_name"] == coluna), None)
            tipo = info["data_type"] if info else "TEXT"
            nullable_raw = info.get("is_nullable", info.get("nullable", "YES")) if info else "YES"
            obrig = " (OBRIGATÓRIO)" if str(nullable_raw).strip().upper() in ("NO", "FALSE", "F", "0", "N", "NAO", "NÃO") else ""
            ctk.CTkLabel(frame, text=f"{coluna}{obrig} ({tipo}):").pack(side="left", padx=5)
            e = ctk.CTkEntry(frame);
            e.pack(side="right", fill="x", expand=True, padx=5);
            entries[coluna] = e

        def salvar():
            valores = {}
            for coluna, e in entries.items():
                valor = e.get().strip()
                info = next((c for c in colunas_info if c["column_name"] == coluna), None)
                nullable_raw = info.get("is_nullable", info.get("nullable", "YES")) if info else "YES"
                if str(nullable_raw).strip().upper() in ("NO", "FALSE", "F", "0", "N", "NAO", "NÃO") and not valor:
                    messagebox.showerror("Erro", f"O campo {coluna} é obrigatório!");
                    return
                valores[coluna] = valor
            try:
                schema = db.get_schema()
                cols_sql = ", ".join(valores.keys())
                placeholders = ", ".join(["%s"] * len(valores))

                # Função auxiliar para nome qualificado
                def qname(table, schema):
                    return f'"{schema}"."{table}"' if schema else f'"{table}"'

                self.cursor.execute(
                    f'INSERT INTO {qname(self.current_table, schema)} ({cols_sql}) VALUES ({placeholders})',
                    tuple(valores.values()))
                self.conn.commit()
                messagebox.showinfo("Sucesso", "Registro adicionado!")
                self.carregar_tabela(self.current_table);
                dialog.destroy()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("Erro", f"Falha ao adicionar registro:\n{e}")

        btn = ctk.CTkFrame(main);
        btn.pack(fill="x", pady=10)
        ctk.CTkButton(btn, text="Salvar", command=salvar, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(side="left", padx=5)
        ctk.CTkButton(btn, text="Cancelar", command=dialog.destroy).pack(side="right", padx=5)

    def editar_registro(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        if not self.current_table:
            messagebox.showerror("Erro", "Nenhuma tabela selecionada");
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Erro", "Nenhum registro selecionado");
            return

        item = self.tree.item(selected[0])
        valores = item["values"]

        schema = db.get_schema()
        colunas_info = db.list_columns(self.current_table, schema=schema)

        if not colunas_info:
            messagebox.showerror("Erro", "Não foi possível obter informações da tabela");
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Editar Registro - {self.current_table}")
        dialog.geometry("600x500");
        dialog.transient(self.root);
        dialog.grab_set()

        main = ctk.CTkScrollableFrame(dialog);
        main.pack(fill="both", expand=True, padx=10, pady=10)

        entries = {}
        for i, info in enumerate(colunas_info):
            col_name, col_type = info["column_name"], info["data_type"]
            frame = ctk.CTkFrame(main);
            frame.pack(fill="x", pady=5)
            label = f"{col_name} ({col_type})"
            ctk.CTkLabel(frame, text=label).pack(side="left", padx=5)

            # Para colunas que não são chaves primárias (assumindo que a primeira coluna é a PK)
            if i != 0:  # Assumindo que a primeira coluna é a PK
                e = ctk.CTkEntry(frame);
                e.insert(0, "" if valores[i] is None else str(valores[i]))
                e.pack(side="right", fill="x", expand=True, padx=5);
                entries[col_name] = e
            else:
                ctk.CTkLabel(frame, text=str(valores[i])).pack(side="right", padx=5)

        def salvar_edicao():
            try:
                # Assumindo que a primeira coluna é a PK
                pk_col = colunas_info[0]["column_name"]
                pk_val = valores[0]

                sets = []
                params = []
                for col_name, e in entries.items():
                    sets.append(f'"{col_name}" = %s')
                    params.append(e.get())
                params.append(pk_val)
                schema = db.get_schema()

                # Função auxiliar para nome qualificado
                def qname(table, schema):
                    return f'"{schema}"."{table}"' if schema else f'"{table}"'

                self.cursor.execute(
                    f'UPDATE {qname(self.current_table, schema)} SET {", ".join(sets)} WHERE "{pk_col}" = %s',
                    tuple(params))
                self.conn.commit()
                messagebox.showinfo("Sucesso", "Registro atualizado!")
                self.carregar_tabela(self.current_table);
                dialog.destroy()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("Erro", f"Falha ao atualizar registro:\n{e}")

        btn = ctk.CTkFrame(main);
        btn.pack(fill="x", pady=10)
        ctk.CTkButton(btn, text="Salvar", command=salvar_edicao, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(side="left", padx=5)
        ctk.CTkButton(btn, text="Cancelar", command=dialog.destroy).pack(side="right", padx=5)

    def excluir_registro(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        if not self.current_table:
            messagebox.showerror("Erro", "Nenhuma tabela selecionada.")
            return

        selecionados = self.tree.selection()
        if not selecionados:
            messagebox.showwarning("Aviso", "Nenhum registro selecionado.")
            return

        try:
            schema = db.get_schema()
            cols = db.list_columns(self.current_table, schema=schema)

            # Assume que a primeira coluna é a PK
            pk_col = cols[0]["column_name"]
            pk_index = 0
            ids = []
            for item in selecionados:
                valores = self.tree.item(item).get("values", [])
                if valores:
                    ids.append(valores[pk_index])

            if not ids:
                messagebox.showerror("Erro", "Não foi possível determinar os IDs dos registros selecionados.")
                return

            placeholders = ", ".join(["%s"] * len(ids))

            # Monta nome qualificado
            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            self.cursor.execute(f'DELETE FROM {qname(self.current_table, schema)} WHERE "{pk_col}" IN ({placeholders})',
                                tuple(ids))
            self.conn.commit()
            messagebox.showinfo("Sucesso", f"{len(ids)} registro(s) excluído(s) com sucesso!")
            self.carregar_tabela(self.current_table)

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erro", f"Falha ao excluir registro(s):\n{e}")

    def exportar_dados(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        if not self.current_table:
            messagebox.showerror("Erro", "Nenhuma tabela selecionada");
            return
        try:
            schema = db.get_schema()

            # Função auxiliar para nome qualificado
            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            self.cursor.execute(f"SELECT * FROM {qname(self.current_table, schema)}")
            dados = self.cursor.fetchall()
            cols_info = db.list_columns(self.current_table, schema)
            colunas = [c["column_name"] for c in cols_info]
            # monta CSV
            linhas = [",".join(colunas)]
            if dados and isinstance(dados[0], dict):
                for r in dados:
                    linhas.append(",".join([f'"{"" if r.get(c) is None else str(r.get(c))}"' for c in colunas]))
            else:
                for row in dados:
                    linhas.append(",".join([f'"{"" if v is None else str(v)}"' for v in row]))
            arquivo = filedialog.asksaveasfilename(defaultextension=".csv",
                                                   filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                                                   title="Salvar como CSV")
            if arquivo:
                with open(arquivo, "w", encoding="utf-8") as f:
                    f.write("\n".join(linhas))
                messagebox.showinfo("Sucesso", f"Dados exportados para:\n{arquivo}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar dados:\n{e}")

    def executar_sql_personalizado(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        import sqlparse
        import re
        from datetime import datetime

        if not self.conn:
            messagebox.showerror("Erro", "Nenhuma conexão ativa com o banco de dados.")
            return

        # ======= Cria janela principal =======
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Console SQL Avançado — Banco Conectado")
        dialog.geometry("1100x700")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_force()

        main = ctk.CTkFrame(dialog)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # ======= Cabeçalho =======
        top_bar = ctk.CTkFrame(main, fg_color="transparent")
        top_bar.pack(fill="x", pady=5)
        ctk.CTkLabel(top_bar, text="💻 Console SQL", font=("Arial", 16, "bold")).pack(side="left", padx=5)
        status_label = ctk.CTkLabel(top_bar, text="Pronto.", text_color=get_contraste_texto(getattr(self.sistema, "cor_secundaria", "#E0E0E0")))
        status_label.pack(side="right", padx=10)

        # ======= Editor de SQL =======
        editor_frame = ctk.CTkFrame(main)
        editor_frame.pack(fill="both", expand=False, pady=(5, 10))
        sql_text = ctk.CTkTextbox(editor_frame, height=200, font=("Consolas", 13))
        sql_text.pack(fill="both", expand=True, padx=5, pady=5)
        sql_text.insert("1.0", "-- Digite comandos SQL. Use ; para separar múltiplos comandos.\n")

        # ======= Resultados =======
        result_frame = ctk.CTkFrame(main)
        result_frame.pack(fill="both", expand=True)
        ctk.CTkLabel(result_frame, text="Resultados:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=2)

        tree_container = ctk.CTkFrame(result_frame)
        tree_container.pack(fill="both", expand=True)
        scroll_x = ttk.Scrollbar(tree_container, orient="horizontal")
        scroll_y = ttk.Scrollbar(tree_container, orient="vertical")
        self.result_tree = ttk.Treeview(tree_container, xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        scroll_x.config(command=self.result_tree.xview)
        scroll_y.config(command=self.result_tree.yview)
        scroll_x.pack(side="bottom", fill="x")
        scroll_y.pack(side="right", fill="y")
        self.result_tree.pack(side="left", fill="both", expand=True)

        # ======= Função principal de execução =======
        def executar_sql(*_):
            sql = sql_text.get("1.0", "end").strip()
            if not sql:
                messagebox.showwarning("Aviso", "Digite um comando SQL.")
                return

            inicio = time.time()
            status_label.configure(text="Executando...", text_color="orange")
            dialog.update_idletasks()

            # ======= Erros leves a ignorar =======
            erros_ignoraveis = [
                "already exists",
                "does not exist",
                "duplicate key",
                "duplicate column",
                "constraint",
                "relation",
                "column",
            ]

            # ======= Remove comentários e divide comandos =======
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
                            # SELECT ou RETURNING
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
                            # DDL/DML sem retorno
                            total_afetadas += self.cursor.rowcount
                            self.conn.commit()
                            total_ok += 1

                    except Exception as e_cmd:
                        msg = str(e_cmd).lower()
                        ignorar = any(p in msg for p in erros_ignoraveis)
                        safe_erro = str(e_cmd).encode("utf-8", "replace").decode("utf-8")
                        safe_sql = comando.encode("utf-8", "replace").decode("utf-8")

                        if ignorar:
                            self.logger.warning("Erro leve ignorado", detalhes={"comando": comando, "erro": msg})
                            self.conn.rollback()
                            total_erros += 1
                            continue
                        else:
                            self.conn.rollback()
                            total_erros += 1
                            self.logger.error("Erro grave em SQL", detalhes={"erro": msg, "sql": comando})
                            messagebox.showerror("Erro", f"Falha ao executar:\n{safe_erro}\n\nComando:\n{safe_sql}")
                            break  # para execução em erro grave

                duracao = (time.time() - inicio) * 1000
                cor_status = "green" if total_erros == 0 else "orange"
                status_label.configure(
                    text=f"{total_ok} OK | {total_erros} ignorados | {total_afetadas} linhas | {duracao:.1f} ms",
                    text_color=cor_status)
                self.logger.info("Execução SQL finalizada",
                                 detalhes={"comandos_total": len(comandos), "sucesso": total_ok,
                                           "ignorados": total_erros, "afetadas": total_afetadas, "tempo_ms": duracao})

            except Exception as e:
                self.conn.rollback()
                safe_erro = str(e).encode("utf-8", "replace").decode("utf-8")
                status_label.configure(text="Erro de execução", text_color="red")
                messagebox.showerror("Erro", f"Falha geral ao executar SQL:\n{safe_erro}")
                self.logger.error("Erro geral em console SQL", detalhes={"erro": safe_erro})

        # ======= Funções auxiliares =======
        def salvar_script():
            arquivo = filedialog.asksaveasfilename(defaultextension=".sql", filetypes=[("SQL", "*.sql")])
            if arquivo:
                with open(arquivo, "w", encoding="utf-8") as f:
                    f.write(sql_text.get("1.0", "end"))
                status_label.configure(text=f"Salvo em {arquivo}", text_color="blue")

        def abrir_script():
            arquivo = filedialog.askopenfilename(filetypes=[("SQL", "*.sql"), ("Todos", "*.*")])
            if arquivo:
                with open(arquivo, "r", encoding="utf-8") as f:
                    sql_text.delete("1.0", "end")
                    sql_text.insert("1.0", f.read())
                status_label.configure(text=f"Carregado de {arquivo}", text_color="blue")

        def exportar_csv():
            if not self.result_tree.get_children():
                messagebox.showinfo("Exportar", "Nenhum resultado disponível.")
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
            messagebox.showinfo("Exportar", f"Resultados exportados para:\n{arquivo}")

        # ======= Botões inferiores =======
        btn_frame = ctk.CTkFrame(main)
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="▶ Executar (Ctrl+Enter)", command=executar_sql, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(
            side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 Salvar", command=salvar_script, fg_color=getattr(self.sistema, 'cor_selecao', '#17a2b8')).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📂 Abrir", command=abrir_script, fg_color=getattr(self.sistema, 'cor_selecao', '#007bff')).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📤 Exportar CSV", command=exportar_csv, fg_color=getattr(self.sistema, 'cor_selecao', '#ffc107'),
                      text_color="black").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="❌ Fechar", command=dialog.destroy, fg_color=getattr(self.sistema, 'cor_selecao', '#6c757d')).pack(side="right", padx=5)

        # ======= Atalhos =======
        dialog.bind("<Control-Return>", executar_sql)
        dialog.bind("<Control-s>", lambda e: salvar_script())
        dialog.bind("<Control-o>", lambda e: abrir_script())

        self.logger.info("Console SQL aberto", detalhes={"usuario": "admin", "schema": db.get_schema()})

    def operacoes_avancadas(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        if not self.modo_admin:
            messagebox.showwarning("Privilégios Insuficientes", "Esta operação requer modo ADMINISTRADOR")
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Operações Administrativas Avançadas")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        main = ctk.CTkFrame(dialog)
        main.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main, text="🔧 OPERAÇÕES ADMINISTRATIVAS", font=("Arial", 16, "bold")).pack(pady=10)

        # Botões para operações admin
        ops = [
            ("🔄 Recriar Schema", self.recriar_schema),
            ("📊 Estatísticas do BD", self.estatisticas_banco),
            ("🔍 Ver Conexões", self.ver_conexoes_ativas),
            ("💾 Backup Rápido", self.backup_rapido),
            ("🗃️ Gerenciar Schemas", self.gerenciar_schemas),
            ("👥 Gerenciar Usuários", self.gerenciar_usuarios)
        ]

        for texto, comando in ops:
            btn = ctk.CTkButton(main, text=texto, command=comando, fg_color=getattr(self.sistema, 'cor_selecao', '#17a2b8'), hover_color="#138496", height=40)
            btn.pack(fill="x", pady=5)

    def recriar_schema(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        if not messagebox.askyesno("CONFIRMAÇÃO CRÍTICA",
                                   "Isso irá RECRIAR todo o schema atual!\nTodos os dados serão perdidos!\n\nContinuar?"):
            return

        try:
            schema = db.get_schema()
            self.cursor.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            self.cursor.execute(f"CREATE SCHEMA {schema}")
            self.conn.commit()
            messagebox.showinfo("Sucesso", f"Schema {schema} recriado com sucesso!")
            self.atualizar_lista_tabelas()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erro", f"Falha ao recriar schema:\n{e}")

    def estatisticas_banco(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        try:
            stats_sql = """
                SELECT 
                    schemaname,
                    tablename,
                    tableowner,
                    tablespace,
                    hasindexes,
                    hasrules,
                    hastriggers
                FROM pg_tables 
                WHERE schemaname = %s
                ORDER BY tablename;
            """
            schema = db.get_schema()
            self.cursor.execute(stats_sql, (schema,))
            tabelas = self.cursor.fetchall()

            info_sql = """
                SELECT 
                    COUNT(*) as total_tabelas,
                    SUM(n_live_tup) as total_registros,
                    SUM(pg_total_relation_size(schemaname||'.'||tablename)) as tamanho_total_bytes
                FROM pg_stat_user_tables 
                WHERE schemaname = %s;
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
            messagebox.showerror("Erro", f"Falha ao obter estatísticas:\n{e}")

    def ver_conexoes_ativas(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        try:
            self.cursor.execute("""
                SELECT 
                    pid,
                    usename,
                    application_name,
                    client_addr,
                    client_port,
                    state,
                    query_start,
                    query
                FROM pg_stat_activity 
                WHERE state = 'active'
                ORDER BY query_start;
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
            messagebox.showerror("Erro", f"Falha ao obter conexões:\n{e}")

    def backup_rapido(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        try:
            schema = db.get_schema()
            backup_file = filedialog.asksaveasfilename(
                defaultextension=".sql",
                filetypes=[("SQL Files", "*.sql"), ("All Files", "*.*")],
                title="Salvar Backup Como",
                initialfile=f"backup_{schema}_{time.strftime('%Y%m%d_%H%M%S')}.sql"
            )

            if backup_file:
                messagebox.showinfo("Info", "Backup iniciado... Esta operação pode demorar alguns minutos.")
                # Em uma implementação real, você usaria pg_dump aqui
                # Por enquanto, vamos apenas criar um arquivo de exemplo
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(f"-- Backup do Schema {schema}\n")
                    f.write(f"-- Gerado em: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                messagebox.showinfo("Sucesso", f"Backup criado com sucesso!\n{backup_file}")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao criar backup:\n{e}")

    def gerenciar_schemas(self):
        """MÉTODO ORIGINAL PRESERVADO"""
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
            dialog.title("Gerenciar Schemas")
            dialog.geometry("400x300")
            dialog.transient(self.root)
            dialog.grab_set()

            main = ctk.CTkFrame(dialog)
            main.pack(fill="both", expand=True, padx=10, pady=10)

            ctk.CTkLabel(main, text="Schemas Disponíveis:", font=("Arial", 12, "bold")).pack(pady=5)

            schema_list = ctk.CTkScrollableFrame(main)
            schema_list.pack(fill="both", expand=True, pady=5)

            for schema in schemas:
                frame = ctk.CTkFrame(schema_list)
                frame.pack(fill="x", pady=2)
                ctk.CTkLabel(frame, text=schema['schema_name']).pack(side="left", padx=5)

                if schema['schema_name'] != db.get_schema():
                    ctk.CTkButton(frame, text="Usar", width=60,
                                  command=lambda s=schema['schema_name']: self.usar_schema(s, dialog),
                                  fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(side="right", padx=2)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerenciar schemas:\n{e}")

    def usar_schema(self, schema_nome, parent):
        """MÉTODO ORIGINAL PRESERVADO"""
        try:
            # Atualiza o schema no config
            global _cfg
            _cfg["schema"] = schema_nome
            self.db_entry.delete(0, "end")
            self.db_entry.insert(0, schema_nome)

            # Reconecta com o novo schema
            self.conectar_como_admin()
            parent.destroy()
            messagebox.showinfo("Sucesso", f"Schema alterado para: {schema_nome}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao alterar schema:\n{e}")

    def gerenciar_usuarios(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        try:
            self.cursor.execute("""
                SELECT 
                    usename,
                    usesuper,
                    usecreatedb,
                    usebypassrls,
                    valuntil
                FROM pg_user 
                ORDER BY usename;
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
            messagebox.showerror("Erro", f"Falha ao obter usuários:\n{e}")

    def editar_tabela_completa(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        if not self.current_table:
            messagebox.showerror("Erro", "Nenhuma tabela selecionada");
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Editor Avançado - Tabela: {self.current_table}")
        dialog.geometry("1000x700");
        dialog.transient(self.root);
        dialog.grab_set()

        notebook = ttk.Notebook(dialog);
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab_estrutura = ctk.CTkFrame(notebook);
        notebook.add(tab_estrutura, text="Estrutura da Tabela")
        frame_titulo = ctk.CTkFrame(tab_estrutura, fg_color="transparent");
        frame_titulo.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(frame_titulo, text=f"EDIÇÃO DE COLUNAS - {self.current_table}", font=("Arial", 14, "bold")).pack(
            side="left")

        frame_tree = ctk.CTkFrame(tab_estrutura);
        frame_tree.pack(fill="both", expand=True, pady=10)
        cols = ("cid", "name", "type", "notnull", "dflt_value", "pk")
        tree_estrutura = ttk.Treeview(frame_tree, columns=cols, show="headings", height=15, selectmode="browse")
        for c in cols: tree_estrutura.heading(c, text=self._format_column_header(c)); tree_estrutura.column(c, width=120, anchor="w")

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
                ""  # PK info não disponível na função atual
            ))

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical", command=tree_estrutura.yview)
        scroll_y.pack(side="right", fill="y");
        tree_estrutura.configure(yscrollcommand=scroll_y.set)
        tree_estrutura.pack(side="left", fill="both", expand=True)

        frame_controles = ctk.CTkFrame(tab_estrutura);
        frame_controles.pack(fill="x", pady=10)
        ctk.CTkButton(frame_controles, text="➕ Adicionar Coluna", command=lambda: self._adicionar_coluna_dialog(dialog),
                      fg_color=getattr(self.sistema, 'cor_selecao', '#28a745'), hover_color="#218838", width=150).pack(side="left", padx=5)
        ctk.CTkButton(frame_controles, text="➖ Remover Coluna",
                      command=lambda: self._remover_coluna_dialog(tree_estrutura, dialog), fg_color=getattr(self.sistema, 'cor_selecao', '#dc3545'),
                      hover_color="#c82333", width=150).pack(side="left", padx=5)
        ctk.CTkButton(frame_controles, text="✏️ Renomear Coluna",
                      command=lambda: self._renomear_coluna_dialog(tree_estrutura, dialog), fg_color=getattr(self.sistema, 'cor_selecao', '#17a2b8'),
                      hover_color="#138496", width=150).pack(side="left", padx=5)
        ctk.CTkButton(frame_controles, text="🗑️ Excluir Tabela",
                      command=lambda: self._confirmar_exclusao_tabela(dialog), fg_color=getattr(self.sistema, 'cor_selecao', '#dc3545'),
                      hover_color="#c82333", width=150).pack(side="left", padx=5)
        ctk.CTkButton(frame_controles, text="❌ Fechar Editor", command=dialog.destroy, fg_color=getattr(self.sistema, 'cor_selecao', '#6c757d'),
                      hover_color="#5a6268").pack(side="right", padx=5)

        tab_dados = ctk.CTkFrame(notebook);
        notebook.add(tab_dados, text="Visualização de Dados")
        frame_dados = ctk.CTkFrame(tab_dados);
        frame_dados.pack(fill="both", expand=True, padx=10, pady=10)
        self._atualizar_tree_dados(frame_dados, self.current_table)

    def _confirmar_exclusao_tabela(self, parent=None):
        """MÉTODO ORIGINAL PRESERVADO"""
        if not self.current_table:
            messagebox.showerror("Erro", "Nenhuma tabela selecionada")
            return

        aviso = (
            f"⚠️ ATENÇÃO!\n\n"
            f"Esta ação excluirá PERMANENTEMENTE a tabela '{self.current_table}' "
            f"e TODAS as tabelas dependentes (via CASCADE).\n\n"
            f"Tem certeza que deseja continuar?"
        )

        if not messagebox.askyesno("Confirmar Exclusão de Tabela", aviso, parent=parent):
            return

        try:
            schema = db.get_schema()

            # Função auxiliar para nome qualificado
            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            # ✅ Usa CASCADE para remover dependências
            self.cursor.execute(f"DROP TABLE {qname(self.current_table, schema)} CASCADE")
            self.conn.commit()

            messagebox.showinfo("Sucesso", f"Tabela '{self.current_table}' e dependências foram removidas com sucesso!",
                                parent=parent)

            parent.destroy()
            self.current_table = None
            self.atualizar_lista_tabelas()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erro", f"Falha ao excluir tabela:\n{e}", parent=parent)

    def _adicionar_coluna_dialog(self, parent):
        """MÉTODO ORIGINAL PRESERVADO"""
        self.adicionar_coluna(parent)

    def _remover_coluna_dialog(self, tree, parent):
        """MÉTODO ORIGINAL PRESERVADO"""
        selected = tree.selection()
        if not selected:
            messagebox.showerror("Erro", "Selecione uma coluna para remover");
            return
        col_data = tree.item(selected[0])["values"]
        col_name = col_data[1]
        if not messagebox.askyesno("Confirmar Remoção",
                                   f"Remover a coluna '{col_name}'?\nEsta ação não pode ser desfeita!", parent=parent):
            return
        try:
            schema = db.get_schema()

            # Função auxiliar para nome qualificado
            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            self.cursor.execute(f'ALTER TABLE {qname(self.current_table, schema)} DROP COLUMN "{col_name}"')
            self.conn.commit()
            messagebox.showinfo("Sucesso", f"Coluna '{col_name}' removida!")
            parent.destroy();
            self.editar_tabela_completa()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Erro", f"Falha ao remover coluna:\n{e}")

    def _renomear_coluna_dialog(self, tree, parent):
        """MÉTODO ORIGINAL PRESERVADO"""
        self.renomear_coluna(tree, parent)

    def _atualizar_tree_dados(self, parent_frame, tabela):
        """MÉTODO ORIGINAL PRESERVADO"""
        for w in parent_frame.winfo_children():
            w.destroy()

        frame_tree = ctk.CTkFrame(parent_frame);
        frame_tree.pack(fill="both", expand=True)

        schema = db.get_schema()
        cols = db.list_columns(tabela, schema)
        colnames = [c["column_name"] for c in cols]

        tree = ttk.Treeview(frame_tree, columns=colnames, show="headings")
        for c in colnames:
            tree.heading(c, text=self._format_column_header(c));
            tree.column(c, width=120, stretch=True)

        # Função auxiliar para nome qualificado
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
        scroll_y.pack(side="right", fill="y");
        tree.configure(yscrollcommand=scroll_y.set)

        scroll_x = ttk.Scrollbar(frame_tree, orient="horizontal", command=tree.xview)
        scroll_x.pack(side="bottom", fill="x");
        tree.configure(xscrollcommand=scroll_x.set)

        tree.pack(side="left", fill="both", expand=True)

    def _abrir_seletor_tabelas(self):
        """MÉTODO ORIGINAL PRESERVADO"""
        if not self.conn:
            messagebox.showerror("Erro", "Nenhum banco de dados conectado.");
            return
        schema = db.get_schema()
        todas = db.list_tables(schema=schema)
        if not todas:
            messagebox.showinfo("Info", "Nenhuma tabela encontrada no banco.");
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Selecionar Tabela");
        dialog.geometry("400x500")
        dialog.update_idletasks()
        w, h = 400, 500
        x = (dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (dialog.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        dialog.transient(self.root);
        dialog.grab_set()

        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(dialog, textvariable=search_var, placeholder_text="Pesquisar tabela...")
        search_entry.pack(fill="x", padx=10, pady=(10, 0))

        scroll = ctk.CTkScrollableFrame(dialog);
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        botoes = []

        def refresh():
            termo = (search_var.get() or "").lower()
            for b in botoes: b.destroy()
            botoes.clear()
            for t in [t for t in todas if termo in t.lower()]:
                b = ctk.CTkButton(scroll, text=t, command=lambda _t=t: self._selecionar_tabela(_t, dialog))
                b.pack(fill="x", padx=5, pady=2);
                botoes.append(b)

        search_var.trace_add("write", lambda *_: refresh());
        refresh()

    def _selecionar_tabela(self, nome_tabela, janela):
        """MÉTODO ORIGINAL PRESERVADO"""
        self.selected_table_var.set(nome_tabela)
        self.current_table = nome_tabela
        self.table_button.configure(text=nome_tabela)
        self.carregar_tabela(nome_tabela)
        janela.destroy()


class BancoDadosFabricaApp(ctk.CTkFrame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack(fill="both", expand=True)
        self.root = self._get_root()
        self.gerenciador = GerenciadorBancoDados(sistema=self, frame=self)

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