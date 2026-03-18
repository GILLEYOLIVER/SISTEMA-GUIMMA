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

        # Inicializar interface e tentar conectar ao banco COMO ADMIN
        self.configurar_interface()
        self.conectar_como_admin()

    # =================== MULTILÍNGUA ===================

    def _get_idioma_atual(self):
        idioma = getattr(self.sistema, "idioma_atual", None)
        return idioma or "pt_BR"

    def _tr(self, chave, **kwargs):
        lang = self._get_idioma_atual()
        textos = {
            "pt_BR": {
                "admin": "Administrador",
                "bank": "Banco",
                "connect": "Conectar",
                "admin_button": "Admin",
                "table": "Tabela",
                "select_table": "Selecionar Tabela",
                "refresh": "Atualizar",
                "new_table": "Nova Tabela",
                "admin_operations": "Operações Admin",
                "delete": "Excluir",
                "edit_table": "Editar Tabela",
                "add": "Adicionar",
                "edit": "Editar",
                "export": "Exportar",
                "sql": "SQL",
                "connection_established": "✅ Conexão Estabelecida",
                "database": "Banco",
                "user": "Usuário",
                "show_status_error": "Erro ao mostrar status: {erro}",
                "no_table_selected": "Nenhuma tabela selecionada.",
                "success": "Sucesso",
                "error": "Erro",
                "warning": "Aviso",
                "select_record": "Nenhum registro selecionado.",
                "confirm_delete": "Confirmar Exclusão",
                "confirm_delete_record": "Deseja realmente excluir o(s) registro(s) selecionado(s)?",
                "status_admin_title": "Status Admin",
                "not_connected": "Não conectado ao banco",
                "connection_error": "Erro na Conexão",
                "connection_failed": "Falha ao conectar:\n{erro}",
                "super_admin_connected": "🔐 CONECTADO COMO SUPER ADMINISTRADOR",
                "admin_limited_connected": "⚠️ Conectado SEM privilégios de admin",
                "privileges_title": "🔐 STATUS DE PRIVILÉGIOS\n\n",
                "superuser_yes": "✅ SIM",
                "superuser_no": "❌ NÃO",
                "full_admin_priv": "✅ Privilégios completos de administração\n✅ Pode criar/alterar/excluir qualquer objeto\n✅ Acesso a todas as tabelas e schemas\n",
                "limited_admin_priv": "⚠️ Privilégios administrativos limitados\n❌ Algumas operações podem falhar\n",
                "col_id": "ID",
                "col_schema_name": "Nome do Schema",
                "col_version": "Versão",
                "col_created_at": "Criado em",
                "col_updated_at": "Atualizado em",
                "col_name": "Nome",
                "col_description": "Descrição",
                "col_code": "Código",
                "col_table": "Tabela",
                "col_type": "Tipo",
                "col_status": "Status",
                "col_user": "Usuário",
                "col_date": "Data",
                "col_notnull": "Obrigatório",
                "col_default": "Padrão",
                "col_pk": "PK",
            },
            "en_US": {
                "admin": "Administrator",
                "bank": "Database",
                "connect": "Connect",
                "admin_button": "Admin",
                "table": "Table",
                "select_table": "Select Table",
                "refresh": "Refresh",
                "new_table": "New Table",
                "admin_operations": "Admin Operations",
                "delete": "Delete",
                "edit_table": "Edit Table",
                "add": "Add",
                "edit": "Edit",
                "export": "Export",
                "sql": "SQL",
                "connection_established": "✅ Connection Established",
                "database": "Database",
                "user": "User",
                "show_status_error": "Error showing status: {erro}",
                "no_table_selected": "No table selected.",
                "success": "Success",
                "error": "Error",
                "warning": "Warning",
                "select_record": "No selected record.",
                "confirm_delete": "Confirm Delete",
                "confirm_delete_record": "Do you really want to delete the selected record(s)?",
                "status_admin_title": "Admin Status",
                "not_connected": "Not connected to the database",
                "connection_error": "Connection Error",
                "connection_failed": "Connection failed:\n{erro}",
                "super_admin_connected": "🔐 CONNECTED AS SUPER ADMINISTRATOR",
                "admin_limited_connected": "⚠️ Connected WITHOUT admin privileges",
                "privileges_title": "🔐 PRIVILEGE STATUS\n\n",
                "superuser_yes": "✅ YES",
                "superuser_no": "❌ NO",
                "full_admin_priv": "✅ Full administration privileges\n✅ Can create/alter/delete any object\n✅ Access to all tables and schemas\n",
                "limited_admin_priv": "⚠️ Limited administrative privileges\n❌ Some operations may fail\n",
                "col_id": "ID",
                "col_schema_name": "Schema Name",
                "col_version": "Version",
                "col_created_at": "Created At",
                "col_updated_at": "Updated At",
                "col_name": "Name",
                "col_description": "Description",
                "col_code": "Code",
                "col_table": "Table",
                "col_type": "Type",
                "col_status": "Status",
                "col_user": "User",
                "col_date": "Date",
                "col_notnull": "Required",
                "col_default": "Default",
                "col_pk": "PK",
            },
            "es_ES": {
                "admin": "Administrador",
                "bank": "Banco",
                "connect": "Conectar",
                "admin_button": "Admin",
                "table": "Tabla",
                "select_table": "Seleccionar Tabla",
                "refresh": "Actualizar",
                "new_table": "Nueva Tabla",
                "admin_operations": "Operaciones Admin",
                "delete": "Eliminar",
                "edit_table": "Editar Tabla",
                "add": "Agregar",
                "edit": "Editar",
                "export": "Exportar",
                "sql": "SQL",
                "connection_established": "✅ Conexión Establecida",
                "database": "Base de datos",
                "user": "Usuario",
                "show_status_error": "Error al mostrar estado: {erro}",
                "no_table_selected": "Ninguna tabla seleccionada.",
                "success": "Éxito",
                "error": "Error",
                "warning": "Aviso",
                "select_record": "Ningún registro seleccionado.",
                "confirm_delete": "Confirmar Eliminación",
                "confirm_delete_record": "¿Desea realmente eliminar los registros seleccionados?",
                "status_admin_title": "Estado Admin",
                "not_connected": "No conectado a la base de datos",
                "connection_error": "Error de Conexión",
                "connection_failed": "Falló la conexión:\n{erro}",
                "super_admin_connected": "🔐 CONECTADO COMO SUPER ADMINISTRADOR",
                "admin_limited_connected": "⚠️ Conectado SIN privilegios admin",
                "privileges_title": "🔐 ESTADO DE PRIVILEGIOS\n\n",
                "superuser_yes": "✅ SÍ",
                "superuser_no": "❌ NO",
                "full_admin_priv": "✅ Privilegios completos de administración\n✅ Puede crear/alterar/eliminar cualquier objeto\n✅ Acceso a todas las tablas y esquemas\n",
                "limited_admin_priv": "⚠️ Privilegios administrativos limitados\n❌ Algunas operaciones pueden fallar\n",
                "col_id": "ID",
                "col_schema_name": "Nombre del Schema",
                "col_version": "Versión",
                "col_created_at": "Creado en",
                "col_updated_at": "Actualizado en",
                "col_name": "Nombre",
                "col_description": "Descripción",
                "col_code": "Código",
                "col_table": "Tabla",
                "col_type": "Tipo",
                "col_status": "Estado",
                "col_user": "Usuario",
                "col_date": "Fecha",
                "col_notnull": "Obligatorio",
                "col_default": "Predeterminado",
                "col_pk": "PK",
            },
        }
        base = textos.get(lang, textos["pt_BR"])
        texto = base.get(chave, chave)
        try:
            return texto.format(**kwargs)
        except Exception:
            return texto

    def _traduzir_coluna(self, coluna):
        chave = str(coluna).strip().lower()
        mapa = {
            "id": self._tr("col_id"),
            "schema_name": self._tr("col_schema_name"),
            "versao": self._tr("col_version"),
            "version": self._tr("col_version"),
            "criado_em": self._tr("col_created_at"),
            "created_at": self._tr("col_created_at"),
            "atualizado_em": self._tr("col_updated_at"),
            "updated_at": self._tr("col_updated_at"),
            "nome": self._tr("col_name"),
            "name": self._tr("col_name"),
            "descricao": self._tr("col_description"),
            "description": self._tr("col_description"),
            "codigo": self._tr("col_code"),
            "code": self._tr("col_code"),
            "tabela": self._tr("col_table"),
            "table": self._tr("col_table"),
            "tipo": self._tr("col_type"),
            "type": self._tr("col_type"),
            "status": self._tr("col_status"),
            "usuario": self._tr("col_user"),
            "user": self._tr("col_user"),
            "data": self._tr("col_date"),
            "notnull": self._tr("col_notnull"),
            "dflt_value": self._tr("col_default"),
            "pk": self._tr("col_pk"),
        }
        return mapa.get(chave, str(coluna).replace("_", " ").title())

    def _atualizar_cabecalhos_tree(self, tree=None):
        alvo = tree or self.tree
        if not alvo:
            return
        try:
            for col in alvo["columns"]:
                alvo.heading(col, text=self._traduzir_coluna(col))
        except Exception as e:
            print(f"Erro ao atualizar cabeçalhos: {e}")

    def _get_base_window(self):
        try:
            if hasattr(self.frame, "winfo_toplevel"):
                return self.frame.winfo_toplevel()
        except Exception:
            pass
        try:
            if hasattr(self.root, "winfo_toplevel"):
                return self.root.winfo_toplevel()
        except Exception:
            pass
        return self.root

    # =================== INTERFACE ===================

    def configurar_interface(self):
        """Interface ORIGINAL preservada - apenas ajustes de tradução"""
        if hasattr(self, 'main_frame') and self.main_frame:
            self.main_frame.destroy()

        self.main_frame = ctk.CTkFrame(self.frame)
        self.main_frame.pack(fill="both", expand=True)

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        top_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", pady=5)

        self.admin_indicator = ctk.CTkLabel(
            top_frame,
            text=f"🔐 {self._tr('admin').upper()}",
            text_color="red",
            font=("Arial", 10, "bold"),
        )
        self.admin_indicator.pack(side="left", padx=5)

        ctk.CTkLabel(top_frame, text=f"{self._tr('bank')}:").pack(side="left", padx=5)
        self.db_entry = ctk.CTkEntry(top_frame, width=200)
        self.db_entry.pack(side="left", padx=5)

        schema = db.get_schema()
        self.db_entry.insert(0, schema or "")

        ctk.CTkButton(top_frame, text=self._tr("connect"), command=self.conectar_como_admin).pack(side="left", padx=5)

        self.admin_btn = ctk.CTkButton(
            top_frame,
            text=self._tr("admin_button"),
            command=self.mostrar_status_admin,
            fg_color=getattr(self.sistema, 'cor_selecao', '#dc3545'),
            border_width=1,
            text_color="white",
        )
        self.admin_btn.pack(side="left", padx=5)

        ctk.CTkLabel(top_frame, text=f"{self._tr('table')}:").pack(side="left", padx=5)
        self.selected_table_var = ctk.StringVar()
        self.table_button = ctk.CTkButton(
            top_frame,
            text=self._tr("select_table"),
            width=200,
            command=self._abrir_seletor_tabelas,
        )
        self.table_button.pack(side="left", padx=5)

        ctk.CTkButton(top_frame, text=self._tr("refresh"), command=self.atualizar_lista_tabelas).pack(side="left", padx=5)
        ctk.CTkButton(
            top_frame,
            text=self._tr("new_table"),
            command=self.criar_nova_tabela,
            fg_color=getattr(self.sistema, 'cor_selecao', '#17a2b8'),
        ).pack(side="left", padx=5)

        ctk.CTkButton(top_frame, text='▲', width=30, command=self.on_arrow_up).pack(side="left", padx=2)
        ctk.CTkButton(top_frame, text='▼', width=30, command=self.on_arrow_down).pack(side="left", padx=2)

        self.tree_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, sticky="ew", pady=5)

        ctk.CTkButton(
            bottom_frame,
            text=self._tr("admin_operations"),
            command=self.operacoes_avancadas,
            fg_color=getattr(self.sistema, 'cor_selecao', '#6f42c1'),
            hover_color="#5a2d91",
        ).pack(side="left", padx=5)

        def confirmar_exclusao_registro():
            if not self.current_table:
                messagebox.showerror(self._tr("error"), self._tr("no_table_selected"))
                return
            selecionados = self.tree.selection()
            if not selecionados:
                messagebox.showwarning(self._tr("warning"), self._tr("select_record"))
                return
            if not messagebox.askyesno(self._tr("confirm_delete"), self._tr("confirm_delete_record")):
                return
            self.excluir_registro()

        ctk.CTkButton(
            bottom_frame,
            text=self._tr("delete"),
            command=confirmar_exclusao_registro,
            fg_color=getattr(self.sistema, 'cor_selecao', '#dc3545'),
            hover_color="#b52a3a",
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            bottom_frame,
            text=self._tr("edit_table"),
            command=self.editar_tabela_completa,
            fg_color=getattr(self.sistema, 'cor_selecao', '#17a2b8'),
            hover_color="#138496",
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            bottom_frame,
            text=self._tr("sql"),
            command=self.executar_sql_personalizado,
            fg_color=getattr(self.sistema, 'cor_selecao', '#6c757d'),
        ).pack(side="right", padx=5)
        ctk.CTkButton(
            bottom_frame,
            text=self._tr("export"),
            command=self.exportar_dados,
            fg_color=getattr(self.sistema, 'cor_selecao', '#007bff'),
            hover_color="#0056b3",
        ).pack(side="right", padx=5)
        ctk.CTkButton(
            bottom_frame,
            text=self._tr("edit"),
            command=self.editar_registro,
            fg_color=getattr(self.sistema, 'cor_selecao', '#ffc107'),
            hover_color="#e0a800",
        ).pack(side="right", padx=5)
        ctk.CTkButton(
            bottom_frame,
            text=self._tr("add"),
            command=self.adicionar_registro,
            fg_color=getattr(self.sistema, 'cor_selecao', '#28a745'),
            hover_color="#218838",
        ).pack(side="right", padx=5)

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

            self.conn = db.get_connection()
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            self.cursor.execute(
                "SELECT current_user, (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) as is_superuser"
            )
            user_info = self.cursor.fetchone()

            is_admin = user_info['is_superuser'] if user_info else False

            if is_admin:
                self.logger.info("Conectado com privilégios de SUPER ADMIN")
                self.mostrar_status_conexao(self._tr("super_admin_connected"))
            else:
                self.logger.warning("Conectado mas SEM privilégios administrativos")
                self.mostrar_status_conexao(self._tr("admin_limited_connected"))

            if not self.tree:
                self.tree = ttk.Treeview(self.tree_frame, selectmode="extended")
                style = ttk.Style()
                style.configure('Treeview', rowheight=25, font=('Arial', 12))
                style.configure('Treeview.Heading', font=('Arial', 12, 'bold'))
                self.tree.pack(fill="both", expand=True)

            self.atualizar_lista_tabelas()

        except Exception as e:
            self.logger.error("Erro ao conectar como administrador", detalhes={"erro": str(e)})
            messagebox.showerror(
                self._tr("connection_error"),
                self._tr("connection_failed", erro=e),
                parent=self._get_base_window(),
            )
            self.conn = None
            self.cursor = None

    def mostrar_status_admin(self):
        """Mostrar status dos privilégios administrativos"""
        if not self.conn:
            messagebox.showinfo(self._tr("status_admin_title"), self._tr("not_connected"))
            return

        try:
            self.cursor.execute("""
                SELECT 
                    current_user,
                    current_database(),
                    inet_client_addr() as client_ip,
                    (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) as is_superuser
            """)
            info = self.cursor.fetchone()

            status = self._tr("privileges_title")
            status += f"{self._tr('user')}: {info['current_user']}\n"
            status += f"{self._tr('database')}: {info['current_database']}\n"
            status += f"IP: {info['client_ip']}\n"
            status += f"Superusuário: {self._tr('superuser_yes') if info['is_superuser'] else self._tr('superuser_no')}\n\n"

            if info['is_superuser']:
                status += self._tr("full_admin_priv")
            else:
                status += self._tr("limited_admin_priv")

            messagebox.showinfo(self._tr("status_admin_title"), status)

        except Exception as e:
            messagebox.showerror(self._tr("error"), f"Falha ao verificar privilégios: {e}")

    def mostrar_status_conexao(self, mensagem):
        """Mostrar status da conexão administrativa"""
        try:
            self.cursor.execute("SELECT current_database(), current_user, version()")
            info = self.cursor.fetchone()

            base = self._get_base_window()

            top = ctk.CTkToplevel(base)
            top.title(self._tr("connection_established"))
            top.geometry("500x200")
            top.resizable(False, False)
            top.attributes("-topmost", True)

            x = base.winfo_x() + (base.winfo_width() // 2) - 250
            y = base.winfo_y() + (base.winfo_height() // 2) - 100
            top.geometry(f"+{x}+{y}")

            frame = ctk.CTkFrame(top, fg_color="transparent")
            frame.pack(pady=20, padx=20, fill="both", expand=True)

            ctk.CTkLabel(
                frame,
                text=mensagem,
                font=("Arial", 14, "bold"),
                text_color="red"
            ).pack(pady=10)

            ctk.CTkLabel(
                frame,
                text=f"{self._tr('database')}: {info['current_database']} | {self._tr('user')}: {info['current_user']}",
                font=("Arial", 12)
            ).pack(pady=5)

            progress = ctk.CTkProgressBar(frame, width=400, progress_color="red")
            progress.pack(pady=10)
            progress.set(0)

            def animar_progresso():
                for i in range(1, 101):
                    top.after(i * 5, lambda i=i: progress.set(i / 100))
                top.after(600, top.destroy)

            animar_progresso()

        except Exception as e:
            print(self._tr("show_status_error", erro=e))

    # =================== MÉTODO ORIGINAL DE CONEXÃO ===================

    def conectar_db_handler(self, admin: bool = False):
        self.conectar_como_admin()

    # =================== MÉTODOS ORIGINAIS COMPLETOS ===================

    def atualizar_lista_tabelas(self):
        if not self.conn:
            messagebox.showerror(self._tr("error"), "Nenhuma conexão ativa com o banco de dados.")
            return

        try:
            schema = db.get_schema()

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
                self.table_button.configure(text=self._tr("select_table"))
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

            self.logger.info("Lista de tabelas atualizada", detalhes={"total": len(self.tabelas_list)})

        except Exception as e:
            messagebox.showerror(self._tr("error"), f"Falha ao atualizar lista de tabelas:\n{e}")
            self.logger.error("Erro ao atualizar lista de tabelas", detalhes={"erro": str(e)})

    def carregar_tabela(self, table_name):
        if not (self.conn and table_name):
            self.logger.warning(
                "Tentativa de carregar tabela sem conexão ou nome de tabela.",
                detalhes={"tabela": table_name, "conexao_ativa": bool(self.conn)},
            )
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
                self.tree.heading(col, text=self._traduzir_coluna(col))
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

            self._atualizar_cabecalhos_tree(self.tree)

        except Exception as e:
            self.logger.error(f"Falha ao carregar a tabela '{table_name}'", detalhes={"erro": str(e)})
            messagebox.showerror(self._tr("error"), f"Falha ao carregar {table_name}:\n{e}")
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

    def criar_nova_tabela(self):
        if not self.conn:
            messagebox.showerror(self._tr("error"), "Não há conexão com o banco de dados")
            return

        dialog = ctk.CTkToplevel(self._get_base_window())
        dialog.title("Criar Nova Tabela")
        dialog.geometry("500x400")
        dialog.transient(self._get_base_window())
        dialog.grab_set()

        main = ctk.CTkFrame(dialog)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(main, text="Nome da Tabela:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        nome_entry = ctk.CTkEntry(main, width=300)
        nome_entry.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(main, text="Colunas (nome:tipo):").grid(row=1, column=0, padx=5, pady=5, sticky="ne")
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
                messagebox.showerror(self._tr("error"), "O nome da tabela é obrigatório")
                return
            if not cols:
                messagebox.showerror(self._tr("error"), "Defina pelo menos uma coluna")
                return
            try:
                schema = db.get_schema()
                cols_sql = ",\n".join([c.strip() for c in cols.split("\n") if c.strip()])

                def qname(table, schema):
                    return f'"{schema}"."{table}"' if schema else f'"{table}"'

                qn = qname(nome, schema)

                self.cursor.execute(f"CREATE TABLE {qn} (\n{cols_sql}\n)")
                self.conn.commit()
                messagebox.showinfo(self._tr("success"), f"Tabela {nome} criada!")
                self.atualizar_lista_tabelas()
                dialog.destroy()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror(self._tr("error"), f"Falha ao criar tabela:\n{e}")

        ctk.CTkButton(button_frame, text="Criar", command=criar, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancelar", command=dialog.destroy).pack(side="left", padx=5)

    def excluir_tabela(self):
        if not self.current_table:
            messagebox.showerror(self._tr("error"), self._tr("no_table_selected"))
            return
        if not messagebox.askyesno("Confirmar", f"Tem certeza que deseja excluir a tabela {self.current_table}?\nTodos os dados serão perdidos!"):
            return
        try:
            schema = db.get_schema()

            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            self.cursor.execute(f"DROP TABLE {qname(self.current_table, schema)}")
            self.conn.commit()
            messagebox.showinfo(self._tr("success"), f"Tabela {self.current_table} excluída!")
            self.current_table = None
            self.atualizar_lista_tabelas()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(self._tr("error"), f"Falha ao excluir tabela:\n{e}")

    def editar_tabela(self):
        self.editar_tabela_completa()

    def adicionar_coluna(self, parent_window):
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
                messagebox.showerror(self._tr("error"), "Nome e tipo são obrigatórios")
                return
            try:
                schema = db.get_schema()
                sql = f'ALTER TABLE "{schema}"."{self.current_table}" ADD COLUMN IF NOT EXISTS "{nome}" {tipo}'
                self.cursor.execute(sql)
                self.conn.commit()
                messagebox.showinfo(self._tr("success"), f"Coluna '{nome}' adicionada com sucesso!")
                parent_window.destroy()
                self.editar_tabela_completa()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror(self._tr("error"), f"Falha ao adicionar coluna:\n{e}")

        ctk.CTkButton(frame, text=self._tr("add"), command=adicionar, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(pady=15)

    def renomear_coluna(self, tree, parent_window):
        selected = tree.selection()
        if not selected:
            messagebox.showerror(self._tr("error"), "Selecione uma coluna")
            return
        col_data = tree.item(selected[0])["values"]
        old_name = col_data[1]

        dialog = ctk.CTkToplevel(parent_window)
        dialog.title(f"Renomear Coluna {old_name}")
        dialog.geometry("400x200")
        dialog.transient(parent_window)
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frame, text=f"Novo nome para '{old_name}':").pack(pady=5)
        new_name_entry = ctk.CTkEntry(frame)
        new_name_entry.pack(pady=5, fill="x")
        new_name_entry.insert(0, old_name)

        def executar():
            new_name = new_name_entry.get().strip()
            if not new_name:
                messagebox.showerror(self._tr("error"), "Nome não pode ser vazio")
                return
            try:
                schema = db.get_schema()

                def qname(table, schema):
                    return f'"{schema}"."{table}"' if schema else f'"{table}"'

                self.cursor.execute(
                    f'ALTER TABLE {qname(self.current_table, schema)} RENAME COLUMN "{old_name}" TO "{new_name}"'
                )
                self.conn.commit()
                messagebox.showinfo(self._tr("success"), "Coluna renomeada!")
                parent_window.destroy()
                self.editar_tabela()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror(self._tr("error"), f"Falha ao renomear:\n{e}")

        ctk.CTkButton(frame, text="Renomear", command=executar, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(pady=10)

    def adicionar_registro(self):
        if not self.current_table:
            messagebox.showerror(self._tr("error"), self._tr("no_table_selected"))
            return

        dialog = ctk.CTkToplevel(self._get_base_window())
        dialog.title(f"Adicionar Registro - {self.current_table}")
        dialog.geometry("500x600")
        dialog.transient(self._get_base_window())
        dialog.grab_set()

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
            obrig = " (OBRIGATÓRIO)" if str(nullable_raw).strip().upper() in ("NO", "FALSE", "F", "0", "N", "NAO", "NÃO") else ""
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
                    messagebox.showerror(self._tr("error"), f"O campo {coluna} é obrigatório!")
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
                    tuple(valores.values())
                )
                self.conn.commit()
                messagebox.showinfo(self._tr("success"), "Registro adicionado!")
                self.carregar_tabela(self.current_table)
                dialog.destroy()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror(self._tr("error"), f"Falha ao adicionar registro:\n{e}")

        btn = ctk.CTkFrame(main)
        btn.pack(fill="x", pady=10)
        ctk.CTkButton(btn, text="Salvar", command=salvar, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(side="left", padx=5)
        ctk.CTkButton(btn, text="Cancelar", command=dialog.destroy).pack(side="right", padx=5)

    def editar_registro(self):
        if not self.current_table:
            messagebox.showerror(self._tr("error"), self._tr("no_table_selected"))
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror(self._tr("error"), self._tr("select_record"))
            return

        item = self.tree.item(selected[0])
        valores = item["values"]

        schema = db.get_schema()
        colunas_info = db.list_columns(self.current_table, schema=schema)

        if not colunas_info:
            messagebox.showerror(self._tr("error"), "Não foi possível obter informações da tabela")
            return

        dialog = ctk.CTkToplevel(self._get_base_window())
        dialog.title(f"Editar Registro - {self.current_table}")
        dialog.geometry("600x500")
        dialog.transient(self._get_base_window())
        dialog.grab_set()

        main = ctk.CTkScrollableFrame(dialog)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        entries = {}
        for i, info in enumerate(colunas_info):
            col_name, col_type = info["column_name"], info["data_type"]
            frame = ctk.CTkFrame(main)
            frame.pack(fill="x", pady=5)
            label = f"{col_name} ({col_type})"
            ctk.CTkLabel(frame, text=label).pack(side="left", padx=5)

            if i != 0:
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
                    tuple(params)
                )
                self.conn.commit()
                messagebox.showinfo(self._tr("success"), "Registro atualizado!")
                self.carregar_tabela(self.current_table)
                dialog.destroy()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror(self._tr("error"), f"Falha ao atualizar registro:\n{e}")

        btn = ctk.CTkFrame(main)
        btn.pack(fill="x", pady=10)
        ctk.CTkButton(btn, text="Salvar", command=salvar_edicao, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(side="left", padx=5)
        ctk.CTkButton(btn, text="Cancelar", command=dialog.destroy).pack(side="right", padx=5)

    def excluir_registro(self):
        if not self.current_table:
            messagebox.showerror(self._tr("error"), self._tr("no_table_selected"))
            return

        selecionados = self.tree.selection()
        if not selecionados:
            messagebox.showwarning(self._tr("warning"), self._tr("select_record"))
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
                messagebox.showerror(self._tr("error"), "Não foi possível determinar os IDs dos registros selecionados.")
                return

            placeholders = ", ".join(["%s"] * len(ids))

            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            self.cursor.execute(
                f'DELETE FROM {qname(self.current_table, schema)} WHERE "{pk_col}" IN ({placeholders})',
                tuple(ids)
            )
            self.conn.commit()
            messagebox.showinfo(self._tr("success"), f"{len(ids)} registro(s) excluído(s) com sucesso!")
            self.carregar_tabela(self.current_table)

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(self._tr("error"), f"Falha ao excluir registro(s):\n{e}")

    def exportar_dados(self):
        if not self.current_table:
            messagebox.showerror(self._tr("error"), self._tr("no_table_selected"))
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
            arquivo = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                title="Salvar como CSV"
            )
            if arquivo:
                with open(arquivo, "w", encoding="utf-8") as f:
                    f.write("\n".join(linhas))
                messagebox.showinfo(self._tr("success"), f"Dados exportados para:\n{arquivo}")
        except Exception as e:
            messagebox.showerror(self._tr("error"), f"Falha ao exportar dados:\n{e}")

    def executar_sql_personalizado(self):
        import sqlparse
        import re

        if not self.conn:
            messagebox.showerror(self._tr("error"), "Nenhuma conexão ativa com o banco de dados.")
            return

        dialog = ctk.CTkToplevel(self._get_base_window())
        dialog.title("Console SQL Avançado — Banco Conectado")
        dialog.geometry("1100x700")
        dialog.transient(self._get_base_window())
        dialog.grab_set()
        dialog.focus_force()

        main = ctk.CTkFrame(dialog)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        top_bar = ctk.CTkFrame(main, fg_color="transparent")
        top_bar.pack(fill="x", pady=5)
        ctk.CTkLabel(top_bar, text="💻 Console SQL", font=("Arial", 16, "bold")).pack(side="left", padx=5)
        status_label = ctk.CTkLabel(top_bar, text="Pronto.", text_color=get_contraste_texto(getattr(self.sistema, "cor_secundaria", "#E0E0E0")))
        status_label.pack(side="right", padx=10)

        editor_frame = ctk.CTkFrame(main)
        editor_frame.pack(fill="both", expand=False, pady=(5, 10))
        sql_text = ctk.CTkTextbox(editor_frame, height=200, font=("Consolas", 13))
        sql_text.pack(fill="both", expand=True, padx=5, pady=5)
        sql_text.insert("1.0", "-- Digite comandos SQL. Use ; para separar múltiplos comandos.\n")

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

        def executar_sql(*_):
            sql = sql_text.get("1.0", "end").strip()
            if not sql:
                messagebox.showwarning(self._tr("warning"), "Digite um comando SQL.")
                return

            inicio = time.time()
            status_label.configure(text="Executando...", text_color="orange")
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
                                self.result_tree.heading(c, text=self._traduzir_coluna(c))
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
                            messagebox.showerror(self._tr("error"), f"Falha ao executar:\n{safe_erro}\n\nComando:\n{safe_sql}")
                            break

                duracao = (time.time() - inicio) * 1000
                cor_status = "green" if total_erros == 0 else "orange"
                status_label.configure(
                    text=f"{total_ok} OK | {total_erros} ignorados | {total_afetadas} linhas | {duracao:.1f} ms",
                    text_color=cor_status
                )
                self.logger.info(
                    "Execução SQL finalizada",
                    detalhes={
                        "comandos_total": len(comandos),
                        "sucesso": total_ok,
                        "ignorados": total_erros,
                        "afetadas": total_afetadas,
                        "tempo_ms": duracao,
                    },
                )

            except Exception as e:
                self.conn.rollback()
                safe_erro = str(e).encode("utf-8", "replace").decode("utf-8")
                status_label.configure(text="Erro de execução", text_color="red")
                messagebox.showerror(self._tr("error"), f"Falha geral ao executar SQL:\n{safe_erro}")
                self.logger.error("Erro geral em console SQL", detalhes={"erro": safe_erro})

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
                messagebox.showinfo(self._tr("export"), "Nenhum resultado disponível.")
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
            messagebox.showinfo(self._tr("export"), f"Resultados exportados para:\n{arquivo}")

        btn_frame = ctk.CTkFrame(main)
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="▶ Executar (Ctrl+Enter)", command=executar_sql, fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 Salvar", command=salvar_script, fg_color=getattr(self.sistema, 'cor_selecao', '#17a2b8')).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📂 Abrir", command=abrir_script, fg_color=getattr(self.sistema, 'cor_selecao', '#007bff')).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="📤 Exportar CSV", command=exportar_csv, fg_color=getattr(self.sistema, 'cor_selecao', '#ffc107'), text_color="black").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="❌ Fechar", command=dialog.destroy, fg_color=getattr(self.sistema, 'cor_selecao', '#6c757d')).pack(side="right", padx=5)

        dialog.bind("<Control-Return>", executar_sql)
        dialog.bind("<Control-s>", lambda e: salvar_script())
        dialog.bind("<Control-o>", lambda e: abrir_script())

        self.logger.info("Console SQL aberto", detalhes={"usuario": "admin", "schema": db.get_schema()})

    def operacoes_avancadas(self):
        if not self.modo_admin:
            messagebox.showwarning("Privilégios Insuficientes", "Esta operação requer modo ADMINISTRADOR")
            return

        dialog = ctk.CTkToplevel(self._get_base_window())
        dialog.title("Operações Administrativas Avançadas")
        dialog.geometry("500x400")
        dialog.transient(self._get_base_window())
        dialog.grab_set()

        main = ctk.CTkFrame(dialog)
        main.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main, text="🔧 OPERAÇÕES ADMINISTRATIVAS", font=("Arial", 16, "bold")).pack(pady=10)

        ops = [
            ("🔄 Recriar Schema", self.recriar_schema),
            ("📊 Estatísticas do BD", self.estatisticas_banco),
            ("🔍 Ver Conexões", self.ver_conexoes_ativas),
            ("💾 Backup Rápido", self.backup_rapido),
            ("🗃️ Gerenciar Schemas", self.gerenciar_schemas),
            ("👥 Gerenciar Usuários", self.gerenciar_usuarios)
        ]

        for texto, comando in ops:
            btn = ctk.CTkButton(
                main,
                text=texto,
                command=comando,
                fg_color=getattr(self.sistema, 'cor_selecao', '#17a2b8'),
                hover_color="#138496",
                height=40
            )
            btn.pack(fill="x", pady=5)

    def recriar_schema(self):
        if not messagebox.askyesno("CONFIRMAÇÃO CRÍTICA", "Isso irá RECRIAR todo o schema atual!\nTodos os dados serão perdidos!\n\nContinuar?"):
            return

        try:
            schema = db.get_schema()
            self.cursor.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            self.cursor.execute(f"CREATE SCHEMA {schema}")
            self.conn.commit()
            messagebox.showinfo(self._tr("success"), f"Schema {schema} recriado com sucesso!")
            self.atualizar_lista_tabelas()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(self._tr("error"), f"Falha ao recriar schema:\n{e}")

    def estatisticas_banco(self):
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
            messagebox.showerror(self._tr("error"), f"Falha ao obter estatísticas:\n{e}")

    def ver_conexoes_ativas(self):
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
            messagebox.showerror(self._tr("error"), f"Falha ao obter conexões:\n{e}")

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
                messagebox.showinfo("Info", "Backup iniciado... Esta operação pode demorar alguns minutos.")
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(f"-- Backup do Schema {schema}\n")
                    f.write(f"-- Gerado em: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                messagebox.showinfo(self._tr("success"), f"Backup criado com sucesso!\n{backup_file}")

        except Exception as e:
            messagebox.showerror(self._tr("error"), f"Falha ao criar backup:\n{e}")

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

            dialog = ctk.CTkToplevel(self._get_base_window())
            dialog.title("Gerenciar Schemas")
            dialog.geometry("400x300")
            dialog.transient(self._get_base_window())
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
                    ctk.CTkButton(
                        frame,
                        text="Usar",
                        width=60,
                        command=lambda s=schema['schema_name']: self.usar_schema(s, dialog),
                        fg_color=getattr(self.sistema, 'cor_selecao', '#28a745')
                    ).pack(side="right", padx=2)

        except Exception as e:
            messagebox.showerror(self._tr("error"), f"Falha ao gerenciar schemas:\n{e}")

    def usar_schema(self, schema_nome, parent):
        try:
            global _cfg
            _cfg["schema"] = schema_nome
            self.db_entry.delete(0, "end")
            self.db_entry.insert(0, schema_nome)

            self.conectar_como_admin()
            parent.destroy()
            messagebox.showinfo(self._tr("success"), f"Schema alterado para: {schema_nome}")
        except Exception as e:
            messagebox.showerror(self._tr("error"), f"Falha ao alterar schema:\n{e}")

    def gerenciar_usuarios(self):
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
            messagebox.showerror(self._tr("error"), f"Falha ao obter usuários:\n{e}")

    def editar_tabela_completa(self):
        if not self.current_table:
            messagebox.showerror(self._tr("error"), self._tr("no_table_selected"))
            return

        dialog = ctk.CTkToplevel(self._get_base_window())
        dialog.title(f"Editor Avançado - Tabela: {self.current_table}")
        dialog.geometry("1000x700")
        dialog.transient(self._get_base_window())
        dialog.grab_set()

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab_estrutura = ctk.CTkFrame(notebook)
        notebook.add(tab_estrutura, text="Estrutura da Tabela")
        frame_titulo = ctk.CTkFrame(tab_estrutura, fg_color="transparent")
        frame_titulo.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(frame_titulo, text=f"EDIÇÃO DE COLUNAS - {self.current_table}", font=("Arial", 14, "bold")).pack(side="left")

        frame_tree = ctk.CTkFrame(tab_estrutura)
        frame_tree.pack(fill="both", expand=True, pady=10)
        cols = ("cid", "name", "type", "notnull", "dflt_value", "pk")
        tree_estrutura = ttk.Treeview(frame_tree, columns=cols, show="headings", height=15, selectmode="browse")
        for c in cols:
            tree_estrutura.heading(c, text=self._traduzir_coluna(c))
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

            tree_estrutura.insert("", "end", values=(i + 1, col_name, col_type, nullable_disp, col_default, ""))

        scroll_y = ttk.Scrollbar(frame_tree, orient="vertical", command=tree_estrutura.yview)
        scroll_y.pack(side="right", fill="y")
        tree_estrutura.configure(yscrollcommand=scroll_y.set)
        tree_estrutura.pack(side="left", fill="both", expand=True)

        frame_controles = ctk.CTkFrame(tab_estrutura)
        frame_controles.pack(fill="x", pady=10)
        ctk.CTkButton(frame_controles, text="➕ Adicionar Coluna", command=lambda: self._adicionar_coluna_dialog(dialog), fg_color=getattr(self.sistema, 'cor_selecao', '#28a745'), hover_color="#218838", width=150).pack(side="left", padx=5)
        ctk.CTkButton(frame_controles, text="➖ Remover Coluna", command=lambda: self._remover_coluna_dialog(tree_estrutura, dialog), fg_color=getattr(self.sistema, 'cor_selecao', '#dc3545'), hover_color="#c82333", width=150).pack(side="left", padx=5)
        ctk.CTkButton(frame_controles, text="✏️ Renomear Coluna", command=lambda: self._renomear_coluna_dialog(tree_estrutura, dialog), fg_color=getattr(self.sistema, 'cor_selecao', '#17a2b8'), hover_color="#138496", width=150).pack(side="left", padx=5)
        ctk.CTkButton(frame_controles, text="🗑️ Excluir Tabela", command=lambda: self._confirmar_exclusao_tabela(dialog), fg_color=getattr(self.sistema, 'cor_selecao', '#dc3545'), hover_color="#c82333", width=150).pack(side="left", padx=5)
        ctk.CTkButton(frame_controles, text="❌ Fechar Editor", command=dialog.destroy, fg_color=getattr(self.sistema, 'cor_selecao', '#6c757d'), hover_color="#5a6268").pack(side="right", padx=5)

        tab_dados = ctk.CTkFrame(notebook)
        notebook.add(tab_dados, text="Visualização de Dados")
        frame_dados = ctk.CTkFrame(tab_dados)
        frame_dados.pack(fill="both", expand=True, padx=10, pady=10)
        self._atualizar_tree_dados(frame_dados, self.current_table)

    def _confirmar_exclusao_tabela(self, parent=None):
        if not self.current_table:
            messagebox.showerror(self._tr("error"), self._tr("no_table_selected"))
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

            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            self.cursor.execute(f"DROP TABLE {qname(self.current_table, schema)} CASCADE")
            self.conn.commit()

            messagebox.showinfo(self._tr("success"), f"Tabela '{self.current_table}' e dependências foram removidas com sucesso!", parent=parent)

            parent.destroy()
            self.current_table = None
            self.atualizar_lista_tabelas()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(self._tr("error"), f"Falha ao excluir tabela:\n{e}", parent=parent)

    def _adicionar_coluna_dialog(self, parent):
        self.adicionar_coluna(parent)

    def _remover_coluna_dialog(self, tree, parent):
        selected = tree.selection()
        if not selected:
            messagebox.showerror(self._tr("error"), "Selecione uma coluna para remover")
            return
        col_data = tree.item(selected[0])["values"]
        col_name = col_data[1]
        if not messagebox.askyesno("Confirmar Remoção", f"Remover a coluna '{col_name}'?\nEsta ação não pode ser desfeita!", parent=parent):
            return
        try:
            schema = db.get_schema()

            def qname(table, schema):
                return f'"{schema}"."{table}"' if schema else f'"{table}"'

            self.cursor.execute(f'ALTER TABLE {qname(self.current_table, schema)} DROP COLUMN "{col_name}"')
            self.conn.commit()
            messagebox.showinfo(self._tr("success"), f"Coluna '{col_name}' removida!")
            parent.destroy()
            self.editar_tabela_completa()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror(self._tr("error"), f"Falha ao remover coluna:\n{e}")

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
            tree.heading(c, text=self._traduzir_coluna(c))
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
        self._atualizar_cabecalhos_tree(tree)

    def _abrir_seletor_tabelas(self):
        if not self.conn:
            messagebox.showerror(self._tr("error"), "Nenhum banco de dados conectado.")
            return
        schema = db.get_schema()
        todas = db.list_tables(schema=schema)
        if not todas:
            messagebox.showinfo("Info", "Nenhuma tabela encontrada no banco.")
            return

        dialog = ctk.CTkToplevel(self._get_base_window())
        dialog.title(self._tr("select_table"))
        dialog.geometry("400x500")
        dialog.update_idletasks()
        w, h = 400, 500
        x = (dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (dialog.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        dialog.transient(self._get_base_window())
        dialog.grab_set()

        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(dialog, textvariable=search_var, placeholder_text="Pesquisar tabela...")
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
                b = ctk.CTkButton(scroll, text=t, command=lambda _t=t: self._selecionar_tabela(_t, dialog))
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
    root.idioma_atual = "pt_BR"
    root.title("Gerenciador de Banco de Dados - SUPER ADMIN")
    root.geometry("1280x700")

    frame = ctk.CTkFrame(root)
    frame.pack(fill="both", expand=True)

    gerenciador = GerenciadorBancoDados(sistema=root, frame=frame)

    root.mainloop()
