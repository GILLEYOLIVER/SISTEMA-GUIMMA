# -*- coding: utf-8 -*-
from PAGINAS_DO_SISTEMA import TEMAS
import customtkinter as ctk
import json
import os
from tkinter import ttk, messagebox
from datetime import datetime, date
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
            self.dsn = os.getenv("OPERA_PG_DSN") or cfg.get(
                "pg_dsn") or "postgresql://postgres:gil25802580@localhost:5433/BANCO_OPERA"
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
        except Exception as e:
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
        """
        Verifica se a tabela existe no schema atual (insensível a maiúsculas),
        com fallback seguro via to_regclass().
        """
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
            res = self.fetch_one("""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = %s AND LOWER(table_name) = LOWER(%s)
            """, (self.schema, table_name))
            return bool(res)
        except Exception:
            return False

    def list_columns(self, table_name: str) -> set[str]:
        rows = self.fetch_all(
            "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",
            (self.schema, table_name.lower()))
        return {row['column_name'].lower() for row in rows}

    def debug_tables(self):
        """Mostra todas as tabelas reais do schema."""
        tabelas = self.fetch_all(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name",
            (self.schema,))
        print("[DEBUG] Tabelas reais encontradas:", [t["table_name"] for t in tabelas])



db = DBManager()

# === LISTAGEM RESUMIDA DAS TABELAS DE ESTOQUE ===
try:
    conn = db.get_connection()
    schema = getattr(db, "schema", "opera")
    tabelas_alvo = [
        "estoque_tecidos", "estoque_aviamentos", "estoque_insumos",
        "estoque_escritorio", "estoque_limpeza", "estoque_outros"
    ]

    print(f"\n{'='*85}")
    print(f"📦 LISTAGEM DAS TABELAS DE ESTOQUE NO SCHEMA '{schema}'")
    print(f"{'='*85}\n")

    for idx, nome_tabela in enumerate(tabelas_alvo, 1):
        if not db.table_exists(nome_tabela):
            print(f"⚠️  {idx:02d}. {nome_tabela:<25} → ❌ NÃO ENCONTRADA\n")
            continue

        colunas = db.fetch_all("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema, nome_tabela))

        total_cols = len(colunas)
        print(f"🧾  {idx:02d}. {nome_tabela}")
        print(f"    {'-' * (len(nome_tabela) + 6)}")

        for c in colunas:
            print(f"      • {c['column_name']:<25} {c['data_type']}")

        print(f"      → Total de colunas: {total_cols}")
        print()  # linha em branco após cada tabela

    print(f"{'='*85}")
    print("✅ Listagem concluída com sucesso.")
    print(f"{'='*85}\n")

except Exception as e:
    print(f"[ERRO] Falha ao listar tabelas e colunas: {e}")
# =============================================================================
# APLICAÇÃO PRINCIPAL
# =============================================================================
class EntradaEstoqueApp(ctk.CTkFrame):
    def __init__(self, master, sistema=None, **kwargs):
        """
        Inicializa a página de Entrada de Estoque de forma compatível
        com o sistema Opera Fashion e o MENU_PRINCIPAL.
        """
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.master = master

        # === CORREÇÃO: APLICAR CORES AO FRAME PRINCIPAL ===
        # Herda as cores e tema do sistema principal
        self.cor_fundo = getattr(sistema, "cor_fundo", "#2b2b2b")
        self.cor_primaria = getattr(sistema, "cor_primaria", "#3a7ebf")
        self.cor_secundaria = getattr(sistema, "cor_secundaria", "#2b3a49")
        self.cor_texto = getattr(sistema, "cor_texto", "white")
        self.cor_hover = getattr(sistema, "cor_hover", "#2e4a66")
        self.cor_borda = getattr(sistema, "cor_borda", "#3a7ebf")

        # APLICAR COR DE FUNDO AO FRAME PRINCIPAL
        self.configure(fg_color=self.cor_fundo)
        # ==================================================

        self.pack(fill="both", expand=True)

        from PAGINAS_DO_SISTEMA.LOG_SISTEMA import get_logger
        self.logger = get_logger("OPERA_SYSTEM")

        try:
            # Dados principais
            self.tipos = ["Tecidos", "Aviamentos", "Insumos", "Escritorio", "Limpeza", "Outros"]
            self.campos_por_tipo = {
                "Tecidos": ["descricao", "codigo", "fornecedor", "composicao", "cor", "metros", "kilos", "data_entrada",
                            "observacoes"],
                "Aviamentos": ["descricao", "codigo", "fornecedor", "cor", "quantidade", "unidade", "data_entrada",
                               "observacoes"],
                "Insumos": ["descricao", "codigo", "tipo", "quantidade", "unidade", "localizacao", "data_entrada",
                            "observacoes"],
            }
            for tipo in ["Escritorio", "Limpeza", "Outros"]:
                self.campos_por_tipo[tipo] = self.campos_por_tipo["Insumos"]

            self.nomes_amigaveis = {
                "id": "ID", "descricao": "Descrição", "codigo": "Código", "fornecedor": "Fornecedor",
                "composicao": "Composição", "cor": "Cor", "metros": "Metros", "kilos": "Kilos",
                "data_entrada": "Data Entrada", "observacoes": "Observações", "tipo": "Tipo",
                "quantidade": "Quantidade", "unidade": "Unidade", "localizacao": "Localização"
            }

            self.entries = {}

            # Criação da interface
            self.setup_ui()
            self.atualizar_interface(self.tipo_var.get())

            self.logger.info("[PAGINA] Entrada de Estoque: inicialização concluída com sucesso.")

        except Exception as e:
            import traceback
            self.logger.error(f"[PAGINA] Falha ao inicializar Entrada de Estoque: {e}\n{traceback.format_exc()}")
            print(f"[ERRO] Falha ao inicializar Entrada de Estoque: {e}")

    def setup_ui(self):
        # Atualiza cores baseado no tema atual
        self.obter_cores_por_tema()

        # Frame superior com título e tipo de material - MESMO ESTILO DA SAÍDA
        top_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        top_frame.pack(fill="x", padx=10, pady=10)

        # Título alinhado à esquerda - MESMO ESTILO DA SAÍDA
        ctk.CTkLabel(top_frame, text="Entrada de Estoque", font=("Arial", 18, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=10)

        # Combobox de tipo alinhada à direita - MESMO ESTILO DA SAÍDA
        self.tipo_var = ctk.StringVar(value="Tecidos")
        self.tipo_cb = ctk.CTkOptionMenu(top_frame, variable=self.tipo_var, values=self.tipos,
                                         command=self.atualizar_interface, width=200,
                                         fg_color=self.cor_secundaria,
                                         button_color=self.cor_primaria,
                                         button_hover_color=self.cor_hover,
                                         text_color=self.cor_texto,
                                         dropdown_fg_color=self.cor_secundaria,
                                         dropdown_text_color=self.cor_texto,
                                         dropdown_hover_color=self.cor_hover)
        self.tipo_cb.pack(side="right", padx=10, fill="x", expand=True)

        # Frame dos campos - MESMO ESTILO DA SAÍDA
        self.campos_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        self.campos_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Botões principais - MESMO ESTILO DA SAÍDA
        button_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        button_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(button_frame, text="Registrar Entrada", command=self.salvar_entrada,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto, font=("Arial", 12, "bold")).pack(side="left", padx=5)

        ctk.CTkButton(button_frame, text="Limpar Campos", command=self.limpar_campos,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto, font=("Arial", 12)).pack(side="left", padx=5)

        # Status - MESMO ESTILO DA SAÍDA
        self.status_label = ctk.CTkLabel(self, text="", text_color=self.cor_texto)
        self.status_label.pack(pady=5)

        # Treeview - MESMO ESTILO DA SAÍDA
        self.tree_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Configurar estilo da Treeview para combinar com o tema
        self.configurar_treeview_theme()

        self.tree = ttk.Treeview(self.tree_frame, show="headings", style="Custom.Treeview")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.carregar_item_selecionado)

    def configurar_treeview_theme(self):
        """Configura as cores da Treeview baseado no tema atual - MESMO ESTILO DA SAÍDA"""
        self.style = ttk.Style()
        self.style.theme_use('default')

        tema_atual = ctk.get_appearance_mode()

        if tema_atual == "Dark":
            # TEMA ESCURO - MESMO ESTILO DA SAÍDA
            cor_fundo = self.cor_secundaria
            cor_texto = self.cor_texto
            cor_campo = self.cor_secundaria
            cor_selecao = self.cor_primaria
        else:
            # TEMA CLARO - MESMO ESTILO DA SAÍDA
            cor_fundo = "#f0f0f0"
            cor_texto = "black"
            cor_campo = "#f0f0f0"
            cor_selecao = self.cor_primaria

        # CONFIGURAÇÃO IGUAL À SAÍDA
        self.style.configure("Custom.Treeview",
                             background=cor_fundo,
                             foreground=cor_texto,
                             fieldbackground=cor_campo,
                             borderwidth=0,
                             highlightthickness=0,
                             rowheight=25)

        # CABEÇALHO COM COR PRIMÁRIA (IGUAL À SAÍDA) - CORRIGIDO
        self.style.configure("Custom.Treeview.Heading",
                             background=self.cor_primaria,  # MUDADO: cor_primaria em vez de cor_secundaria
                             foreground=self.cor_texto,
                             relief="flat",
                             borderwidth=1,
                             font=('Arial', 10, 'bold'))

        # MAPA DE SELEÇÃO IGUAL À SAÍDA
        self.style.map('Custom.Treeview',
                       background=[('selected', cor_selecao)],
                       foreground=[('selected', "white")])

    def obter_cores_por_tema(self):
        """Define cores de texto dinamicamente baseado no tema atual - PADRÃO SAÍDA"""
        tema_atual = ctk.get_appearance_mode()

        if tema_atual == "Dark":
            # Tema escuro - MESMO PADRÃO DA SAÍDA
            self.cor_fundo = getattr(self.sistema, "cor_fundo", "#020617")
            self.cor_primaria = getattr(self.sistema, "cor_primaria", "#1f2937")
            self.cor_secundaria = getattr(self.sistema, "cor_secundaria", "#111827")
            self.cor_texto = getattr(self.sistema, "cor_texto", "#e5e7eb")
            self.cor_texto_entry = "#e5e7eb"
            self.cor_placeholder = "#888888"
            self.cor_borda = getattr(self.sistema, "cor_borda", "#273244")
            self.cor_hover = getattr(self.sistema, "cor_hover", "#334155")
        else:
            # Tema claro - MESMO PADRÃO DA SAÍDA
            self.cor_fundo = "#ffffff"
            self.cor_primaria = "#3a7ebf"
            self.cor_secundaria = "#f0f0f0"
            self.cor_texto = "black"
            self.cor_texto_entry = "black"
            self.cor_placeholder = "#666666"
            self.cor_borda = "#cccccc"
            self.cor_hover = "#2e4a66"

    def atualizar_interface(self, tipo_selecionado: str):
        # Atualiza o tema da treeview antes de criar os campos
        self.configurar_treeview_theme()
        self.criar_campos_entrada(tipo_selecionado)
        self.configurar_tabela(tipo_selecionado)
        self.carregar_dados_existente()
        self.status_label.configure(text=f"Pronto para editar: {tipo_selecionado}")

    def criar_campos_entrada(self, tipo: str):
        """Cria dinamicamente os campos de entrada baseando-se nas colunas reais do banco."""
        # Atualiza cores baseado no tema atual
        self.obter_cores_por_tema()

        for widget in self.campos_frame.winfo_children():
            widget.destroy()
        self.entries.clear()

        # Mapeamento correto baseado nas colunas reais do banco
        self.campos_por_tipo = {
            "Tecidos": ["codigo", "descricao", "fornecedor", "composicao", "cor", "metros", "kilos", "data_entrada",
                        "observacoes"],
            "Aviamentos": ["codigo", "descricao", "fornecedor", "cor", "quantidade", "unidade", "data_entrada",
                           "observacoes"],
            "Insumos": ["codigo", "descricao", "fornecedor", "cor", "quantidade", "unidade", "data_entrada",
                        "observacoes"],
            "Escritorio": ["codigo", "descricao", "fornecedor", "cor", "quantidade", "unidade", "data_entrada",
                           "observacoes"],
            "Limpeza": ["codigo", "descricao", "fornecedor", "cor", "quantidade", "unidade", "data_entrada",
                        "observacoes"],
            "Outros": ["codigo", "descricao", "fornecedor", "cor", "quantidade", "unidade", "data_entrada",
                       "observacoes"]
        }

        placeholders = {
            "metros": "0,00",
            "kilos": "0,00",
            "quantidade": "0,00",
            "data_entrada": datetime.now().strftime("%d/%m/%Y")
        }

        campos = self.campos_por_tipo.get(tipo, [])

        for campo in campos:
            # Frame do campo - MESMO ESTILO DA SAÍDA
            frame = ctk.CTkFrame(self.campos_frame, fg_color=self.cor_fundo)
            frame.pack(fill="x", padx=5, pady=3)

            label_text = self.nomes_amigaveis.get(campo, campo.title()) + ":"
            ctk.CTkLabel(frame, text=label_text, width=150, anchor="e",
                         text_color=self.cor_texto).pack(side="left", padx=5)

            if campo in ["descricao", "observacoes"]:
                widget = ctk.CTkTextbox(frame, height=60 if campo == "observacoes" else 40,
                                        fg_color=self.cor_secundaria,
                                        border_color=self.cor_borda,
                                        text_color=self.cor_texto_entry,
                                        border_width=1)
                widget.pack(side="left", fill="x", expand=True)
                self.entries[campo] = widget
            else:
                widget = ctk.CTkEntry(frame, placeholder_text=placeholders.get(campo, ""),
                                      fg_color=self.cor_secundaria,
                                      border_color=self.cor_borda,
                                      text_color=self.cor_texto_entry,
                                      placeholder_text_color=self.cor_placeholder,
                                      border_width=1)

                # VALIDAÇÃO: Bloquear números no campo unidade para Insumos, Escritorio, Limpeza e Outros
                if campo == "unidade" and tipo in ["Insumos", "Escritorio", "Limpeza", "Outros"]:
                    def validar_unidade(text):
                        """Valida se o texto contém apenas letras e caracteres permitidos."""
                        if text == "":
                            return True
                        # Verifica se contém números
                        if any(char.isdigit() for char in text):
                            return False
                        # Permite letras, espaços, traços, barras, parênteses
                        return all(char.isalpha() or char.isspace() or char in '-/()' for char in text)

                    # Função de validação em tempo real (APENAS para CTkEntry)
                    def on_unidade_change(*args):
                        texto = unidade_var.get()  # Usa a variável StringVar, não o widget diretamente
                        if not validar_unidade(texto):
                            # Remove o último caractere se for inválido
                            current_text = unidade_var.get()
                            if len(current_text) > 0:
                                unidade_var.set(current_text[:-1])

                            # Mostra mensagem amigável no status label
                            self.status_label.configure(
                                text="❌ Não é possível inserir números no campo 'Unidade'. Use apenas letras.",
                                text_color="red"
                            )
                            # Remove a mensagem após 3 segundos
                            self.after(3000, lambda: self.status_label.configure(
                                text=f"Pronto para editar: {tipo}",
                                text_color=self.cor_texto
                            ))

                            # Feedback visual
                            widget.configure(border_color="red")
                            self.after(2000, lambda: widget.configure(
                                border_color=self.cor_borda
                            ))
                        else:
                            widget.configure(border_color=self.cor_borda)

                    # Cria variável para monitorar mudanças
                    unidade_var = ctk.StringVar()
                    widget.configure(textvariable=unidade_var)
                    unidade_var.trace_add("write", on_unidade_change)

                    # Tooltip permanente
                    widget.configure(placeholder_text="Ex: unidades, caixas, pacotes... (sem números)")

                widget.pack(side="left", fill="x", expand=True)
                self.entries[campo] = widget

        # Preenche data atual automaticamente
        if 'data_entrada' in self.entries:
            self.entries['data_entrada'].insert(0, datetime.now().strftime("%d/%m/%Y"))

        # Adiciona pesquisa apenas para Tecidos - MESMO ESTILO DA SAÍDA
        if tipo == "Tecidos":
            self.adicionar_pesquisa_codigo()

        # Atualiza status
        self.status_label.configure(text=f"Pronto para editar: {tipo}", text_color=self.cor_texto)

    def configurar_tabela(self, tipo: str):
        colunas_desejadas = ['id'] + self.campos_por_tipo.get(tipo, [])
        self.tree["columns"] = tuple(colunas_desejadas)

        # Limpar colunas existentes
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
            self.tree.column(col, width=0)

        # Configurar novas colunas
        for col in colunas_desejadas:
            nome_amigavel = self.nomes_amigaveis.get(col, col.title())
            largura = 50 if col == 'id' else 120
            self.tree.heading(col, text=nome_amigavel)
            self.tree.column(col, width=largura, stretch=True, anchor="w")

    def adicionar_pesquisa_codigo(self):
        frame = ctk.CTkFrame(self.campos_frame, fg_color=self.cor_fundo)
        frame.pack(fill="x", padx=5, pady=3)

        ctk.CTkLabel(frame, text="Pesquisar Código:", width=150, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        pesquisa_entry = ctk.CTkEntry(frame, placeholder_text="Digite um código para pesquisar",
                                      fg_color=self.cor_secundaria,
                                      border_color=self.cor_borda,
                                      text_color=self.cor_texto,
                                      placeholder_text_color="#888888")
        pesquisa_entry.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkButton(frame, text="🔍", width=30,
                      command=lambda: self.pesquisar_codigo(pesquisa_entry.get()),
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left")

        self.entries['pesquisa_codigo'] = pesquisa_entry

    def pesquisar_codigo(self, codigo: str):
        if not codigo.strip():
            return

        tipo = self.tipo_var.get()
        schema = getattr(db, "schema", "opera")
        tabela_nome = f"estoque_{tipo.lower()}"
        tabela_qual = f"{schema}.{tabela_nome}"

        if not db.table_exists(tabela_nome):
            messagebox.showwarning("Aviso", f"Tabela '{tabela_qual}' não encontrada.")
            return

        item = db.fetch_one(f"SELECT * FROM {tabela_qual} WHERE codigo ILIKE %s ORDER BY id DESC LIMIT 1",
                            (f"%{codigo.strip()}%",))
        if not item:
            self.status_label.configure(text=f"Código não encontrado: {codigo}", text_color="orange")
            return

        for campo, widget in self.entries.items():
            if campo in item and campo != 'pesquisa_codigo':
                valor = self.formatar_valor(item[campo], campo)
                if isinstance(widget, ctk.CTkTextbox):
                    widget.delete("1.0", "end")
                    widget.insert("1.0", valor)
                else:
                    widget.delete(0, "end")
                    widget.insert(0, valor)

        self.status_label.configure(text=f"Código encontrado e carregado: {item['codigo']}", text_color="green")

    # --- FUNÇÃO CORRIGIDA ---
    def carregar_dados_existente(self):
        """
        Carrega dados do estoque para a Treeview, mapeando colunas "amigáveis" da UI
        para colunas reais do banco e usando schema.tabela qualificado.
        """
        import os
        from unicodedata import normalize

        def _norm(s: str) -> str:
            if s is None: return ""
            s = str(s)
            try:
                s = normalize("NFKD", s);
                s = "".join(ch for ch in s if ord(ch) < 128)
            except Exception:
                pass
            return "".join(ch for ch in s.lower() if ch.isalnum())

        ALIASES = {
            "id": "id", "descricao": "descricao", "descrição": "descricao", "codigo": "codigo", "código": "codigo",
            "fornecedor": "fornecedor", "composicao": "composicao", "composição": "composicao", "cor": "cor",
            "metros": "metros", "kilos": "kilos", "kg": "kilos", "kiloskg": "kilos",
            "dataentrada": "data_entrada", "data_entrada": "data_entrada",
            "observacoes": "observacoes", "observações": "observacoes",
            "quantidade": "quantidade", "qtd": "quantidade",
            "unidade": "unidade", "tipo": "tipo",
            "localizacao": "localizacao", "localização": "localizacao",
            "valormetro": "valor_metro", "valor_kilo": "valor_kilo", "valorkilo": "valor_kilo",
            "createdat": "created_at", "updatedat": "updated_at",
        }

        def _get_schema():
            for getter in ("get_schema", "schema", "get_current_schema"):
                if hasattr(db, getter):
                    try:
                        v = getattr(db, getter);
                        v = v() if callable(v) else v
                        if v: return str(v)
                    except Exception:
                        pass
            return os.getenv("OPERA_PG_SCHEMA", "opera")

        def _table_exists(tab_qual: str, schema: str, nome: str) -> bool:
            try:
                if getattr(db, "table_exists", None) and db.table_exists(tab_qual): return True
            except Exception:
                pass
            try:
                r = db.fetch_one("""
                    SELECT EXISTS(SELECT 1 FROM information_schema.tables
                                  WHERE table_schema=%s AND table_name=%s) AS ok
                """, [schema, nome])
                if r and r.get("ok"): return True
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

        tipo_raw = (self.tipo_var.get() or "").strip()
        if not tipo_raw or tipo_raw.lower() == "selecione o tipo": return
        tipo_sql = tipo_raw.lower().replace(" ", "_")
        tabela_nome = f"estoque_{tipo_sql}"
        schema = _get_schema()
        tabela_qual = f"{schema}.{tabela_nome}"

        try:
            db.execute(f"SET search_path TO {schema}, public")
        except Exception:
            pass

        if not _table_exists(tabela_qual, schema, tabela_nome):
            try:
                self.status_label.configure(text=f"Tabela '{tabela_qual}' não existe.", text_color="orange")
            except Exception:
                pass
            return

        cols_tree = list(self.tree["columns"])
        if not cols_tree: return
        cols_tree_norm = [_norm(c) for c in cols_tree]

        try:
            rows = db.fetch_all("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema=%s AND table_name=%s
            """, [schema, tabela_nome]) or []
            cols_db = {str(r["column_name"]) for r in rows}
        except Exception:
            cols_db = set()

        if not cols_db:
            try:
                self.status_label.configure(text=f"Não foi possível listar colunas de {tabela_qual}.",
                                            text_color="orange")
            except Exception:
                pass
            return

        tree_to_db = {}
        for i, c_norm in enumerate(cols_tree_norm):
            if c_norm in ALIASES:
                cand = ALIASES[c_norm]
                if cand == "quantidade" and "quantidade" not in cols_db and "qtd" in cols_db:
                    tree_to_db[cols_tree[i]] = "qtd"
                else:
                    tree_to_db[cols_tree[i]] = cand

        for i, c in enumerate(cols_tree):
            if c in tree_to_db: continue
            normed = _norm(c)
            if normed in cols_db:
                tree_to_db[c] = normed
                continue
            heur = []
            if normed == "observacoes" and "observacoes" in cols_db: heur.append("observacoes")
            if normed == "descricao" and "descricao" in cols_db: heur.append("descricao")
            if normed == "codigo" and "codigo" in cols_db: heur.append("codigo")
            if normed == "dataentrada" and "data_entrada" in cols_db: heur.append("data_entrada")
            if normed == "kg" and "kilos" in cols_db: heur.append("kilos")
            if normed == "qtd" and "quantidade" in cols_db: heur.append("quantidade")
            if normed == "quantidade" and "qtd" in cols_db: heur.append("qtd")
            if heur: tree_to_db[c] = heur[0]

        validos = [c for c in cols_tree if c in tree_to_db and tree_to_db[c] in cols_db]
        if not validos:
            try:
                self.status_label.configure(text="Nenhuma coluna da Treeview corresponde às colunas do banco.",
                                            text_color="orange")
            except Exception:
                pass
            return

        order_col = "data_entrada" if "data_entrada" in cols_db else ("id" if "id" in cols_db else None)
        order_sql = f" ORDER BY {order_col} DESC" if order_col else ""

        select_cols = list({tree_to_db[c] for c in validos})
        if "id" in cols_db and "id" not in select_cols: select_cols.insert(0, "id")

        try:
            sql = f"SELECT {', '.join(select_cols)} FROM {tabela_qual}{order_sql}"
            dados = db.fetch_all(sql) or []
            for item in dados:
                linha = []
                for col_label in cols_tree:
                    col_db = tree_to_db.get(col_label)
                    val = item.get(col_db) if (col_db and isinstance(item, dict)) else None
                    if hasattr(self, "formatar_valor"):
                        try:
                            val = self.formatar_valor(val, col_db or col_label)
                        except Exception:
                            pass
                    linha.append(val)
                iid = item.get("id") if isinstance(item, dict) and "id" in item else ""
                self.tree.insert("", "end", iid=iid, values=linha)

            try:
                self.status_label.configure(text=f"{len(dados)} itens carregados.", text_color="green")
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Erro de Carregamento", f"Não foi possível carregar os dados:\n{e}")

    def carregar_item_selecionado(self, event):
        """
        Carrega o registro completo do item selecionado na Treeview para os campos de entrada.
        """
        try:
            selecao = self.tree.selection()
            if not selecao: return
            item_id = selecao[0]
            if not item_id: return

            tipo = (self.tipo_var.get() or "").strip()
            if not tipo:
                messagebox.showwarning("Aviso", "Nenhum tipo de material selecionado.")
                return

            schema = getattr(db, "schema", "opera")
            tabela_nome = f"estoque_{tipo.lower()}"
            tabela_qual = f"{schema}.{tabela_nome}"

            if not db.table_exists(tabela_nome):
                messagebox.showerror("Erro", f"Tabela '{tabela_qual}' não existe no schema atual.")
                return

            item_completo = db.fetch_one(f"SELECT * FROM {tabela_qual} WHERE id = %s", (item_id,))
            if not item_completo:
                messagebox.showerror("Erro", f"Item ID {item_id} não encontrado em '{tabela_qual}'.")
                return

            self.limpar_campos()

            for campo, widget in self.entries.items():
                if campo not in item_completo: continue
                valor = self.formatar_valor(item_completo[campo], campo)
                if isinstance(widget, ctk.CTkTextbox):
                    widget.delete("1.0", "end");
                    widget.insert("1.0", valor)
                else:
                    widget.delete(0, "end");
                    widget.insert(0, valor)

            self.status_label.configure(text=f"Item ID {item_id} carregado de {tabela_qual}.", text_color="blue")

        except Exception as e:
            messagebox.showerror("Erro ao carregar item", f"Falha ao carregar item selecionado:\n{e}")

    def limpar_campos(self):
        for campo, widget in self.entries.items():
            if campo == 'pesquisa_codigo': continue
            if isinstance(widget, ctk.CTkTextbox):
                widget.delete("1.0", "end")
            else:
                widget.delete(0, "end")
        if 'data_entrada' in self.entries:
            self.entries['data_entrada'].insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.tree.selection_remove(self.tree.selection())
        self.status_label.configure(text="Campos limpos.")

    def salvar_entrada(self):
        """
        Salva fielmente todos os campos da interface na tabela correspondente ao tipo selecionado.

        ✅ CORRIGE DATA:
        - Converte 'DD/MM/AAAA' para date (Python) antes de enviar ao PostgreSQL.

        ✅ MENSAGEM DE SUCESSO (AJUSTE PEDIDO):
        - Mostra: CÓDIGO + DESCRIÇÃO/NOME + COR + QUANTIDADE (sem data).
        """

        from datetime import datetime, date
        from decimal import Decimal, InvalidOperation
        import os
        import customtkinter as ctk
        from tkinter import messagebox

        def _get_val(widget):
            """Extrai texto de Entry ou Textbox."""
            try:
                if isinstance(widget, ctk.CTkTextbox):
                    return widget.get("1.0", "end-1c").strip()
                return widget.get().strip()
            except Exception:
                return ""

        def _to_decimal(valor):
            """Converte texto BR para Decimal."""
            try:
                if isinstance(valor, (int, float, Decimal)):
                    return Decimal(str(valor))

                s = str(valor).strip()
                if not s:
                    return Decimal("0")

                # 1.234,56 -> 1234.56
                if "," in s:
                    s = s.replace(".", "").replace(",", ".")
                    return Decimal(s)

                # 1.234.567 -> 1234567 (milhar)
                if "." in s:
                    parts = s.split(".")
                    if all(len(p) == 3 for p in parts[1:]):
                        s = "".join(parts)
                        return Decimal(s)

                return Decimal(s)
            except (InvalidOperation, TypeError, ValueError):
                return Decimal("0")

        def _fmt_num_br(v):
            """Formata Decimal/num para pt-BR (vírgula) sem zeros inúteis."""
            if v is None:
                return ""
            try:
                d = v if isinstance(v, Decimal) else Decimal(str(v))
                s = format(d, "f")
                if "." in s:
                    s = s.rstrip("0").rstrip(".")
                return s.replace(".", ",")
            except Exception:
                return str(v)

        def _to_date(valor_texto):
            """Converte 'DD/MM/AAAA' (ou 'AAAA-MM-DD') para date. Se vazio -> hoje."""
            if isinstance(valor_texto, date) and not isinstance(valor_texto, datetime):
                return valor_texto
            if isinstance(valor_texto, datetime):
                return valor_texto.date()

            s = (valor_texto or "").strip()
            if not s:
                return date.today()

            for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    pass

            raise ValueError(f"Data inválida: '{s}'. Use DD/MM/AAAA.")

        def _validar_unidade_salvamento(unidade_texto, tipo):
            """Valida se a unidade não contém números para as abas específicas."""
            if tipo in ["Insumos", "Escritorio", "Limpeza", "Outros"] and unidade_texto:
                if any(char.isdigit() for char in unidade_texto):
                    return False
            return True

        def _get_schema():
            """Retorna schema atual."""
            try:
                if hasattr(db, "get_schema"):
                    return db.get_schema()
            except Exception:
                pass
            return os.getenv("OPERA_PG_SCHEMA", "opera")

        # Tipo selecionado
        tipo_raw = (self.tipo_var.get() or "").strip()
        if not tipo_raw or tipo_raw.lower() == "selecione o tipo":
            messagebox.showwarning("⚠️ Aviso", "Selecione um tipo de material.")
            return

        tipo = tipo_raw.lower().replace(" ", "_")
        tabela_nome = f"estoque_{tipo}"
        schema = _get_schema()
        tabela_qual = f"{schema}.{tabela_nome}"

        print(f"\n[DEBUG] Tipo selecionado: {tipo_raw}")
        print(f"[DEBUG] Tabela alvo: {tabela_qual}")

        # Confere se tabela existe
        if hasattr(db, "table_exists") and not db.table_exists(tabela_nome):
            messagebox.showerror("❌ Erro", f"A tabela '{tabela_qual}' não existe.")
            return

        # Colunas reais do banco
        colunas_info = db.fetch_all(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            [schema, tabela_nome]
        ) or []
        colunas_db = [r["column_name"] for r in colunas_info]

        # Coleta dados da UI
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

            # ✅ CORREÇÃO DA DATA (aqui)
            if campo == "data_entrada":
                try:
                    dados[campo] = _to_date(valor)
                except Exception as e:
                    messagebox.showerror("❌ Data inválida", str(e))
                    return
                continue

            if campo in ["metros", "kilos", "quantidade"]:
                dados[campo] = _to_decimal(valor)
                continue

            if valor != "":
                dados[campo] = valor.strip()

        # Se existir data_entrada no banco e não veio por algum motivo, usa hoje
        if "data_entrada" in colunas_db and "data_entrada" not in dados:
            dados["data_entrada"] = date.today()

        # Validação unidade
        if "unidade" in colunas_db and not _validar_unidade_salvamento(unidade_valor, tipo_raw):
            messagebox.showerror(
                "❌ Unidade inválida",
                "Não é permitido usar números no campo 'Unidade' para este tipo.\n"
                "Use apenas letras (ex: unidades, caixas, pacotes)."
            )
            return

        # timestamps (se existirem)
        agora = datetime.now()
        if "created_at" in colunas_db and "created_at" not in dados:
            dados["created_at"] = agora
        if "updated_at" in colunas_db:
            dados["updated_at"] = agora

        if not dados:
            messagebox.showwarning("⚠️ Aviso", "Nenhum dado válido foi informado.")
            return

        # INSERT
        try:
            campos = list(dados.keys())
            placeholders = ", ".join(["%s"] * len(campos))
            valores = [dados[c] for c in campos]

            sql = f"INSERT INTO {tabela_qual} ({', '.join(campos)}) VALUES ({placeholders})"
            db.execute(sql, valores)

            # ===========================
            # ✅ AJUSTE PEDIDO: MENSAGEM
            # ===========================
            codigo_msg = (dados.get("codigo") or "").strip()
            desc_msg = (dados.get("descricao") or dados.get("nome") or "").strip()
            cor_msg = (dados.get("cor") or cor_valor or "").strip()

            qtd_msg = ""
            if "quantidade" in dados:
                qtd_msg = _fmt_num_br(dados.get("quantidade"))
            elif "metros" in dados or "kilos" in dados:
                # fallback p/ Tecidos
                metros = _fmt_num_br(dados.get("metros")) if "metros" in dados else ""
                kilos = _fmt_num_br(dados.get("kilos")) if "kilos" in dados else ""
                partes = []
                if metros not in ("", "0"):
                    partes.append(f"{metros} m")
                if kilos not in ("", "0"):
                    partes.append(f"{kilos} kg")
                qtd_msg = " / ".join(partes) if partes else "0"

            unidade_msg = (dados.get("unidade") or unidade_valor or "").strip()
            if unidade_msg and "quantidade" in dados and qtd_msg:
                qtd_msg = f"{qtd_msg} {unidade_msg}"

            mensagem = (
                "✅ Cadastro realizado com sucesso!\n\n"
                f"📌 Código: {codigo_msg or '-'}\n"
                f"📝 Descrição: {desc_msg or '-'}\n"
                f"🎨 Cor: {cor_msg or '-'}\n"
                f"📦 Quantidade: {qtd_msg or '-'}"
            )

            messagebox.showinfo("✅ Salvo", mensagem)

            # Recarrega e limpa
            try:
                self.carregar_dados_existente()
            except Exception:
                pass
            try:
                self.limpar_campos()
            except Exception:
                pass

        except Exception as e:
            messagebox.showerror("Erro ao gravar no banco", f"Ocorreu um erro ao gravar no banco:\n{e}")

    def formatar_valor(self, valor, campo):
        if valor is None:
            return ""

        if isinstance(valor, date):
            return valor.strftime("%d/%m/%Y")

        try:
            # Não formata o código como número; retorna literal
            if str(campo).lower() == 'codigo':
                return str(valor)

            # Formata campos numéricos de estoque (metros, kilos, quantidade)
            if str(campo).lower() in ('metros', 'kilos', 'quantidade'):
                from decimal import Decimal, InvalidOperation
                try:
                    dec = Decimal(str(valor))
                except (InvalidOperation, ValueError, TypeError):
                    return str(valor)
                # Se o valor é inteiro (sem parte decimal), exibe apenas a parte inteira com separador de milhar
                if dec == dec.to_integral():
                    parte_inteira = int(dec)
                    return f"{parte_inteira:,}".replace(',', '.')
                else:
                    # Tem parte decimal: formata com até 3 casas decimais
                    # Usa vírgula como separador decimal e ponto como milhar
                    parte_inteira = int(dec)
                    parte_decimal = abs(dec - parte_inteira)
                    parte_inteira_str = f"{parte_inteira:,}".replace(',', '.')
                    # Converte parte_decimal para string com 3 casas
                    frac_str = f"{parte_decimal:.3f}"[2:]  # remove '0.'
                    # Remove zeros à direita
                    frac_str = frac_str.rstrip('0')
                    return f"{parte_inteira_str},{frac_str}"

            # Para outros campos numéricos genéricos
            valor_float = float(valor)
            # Para valores até 999, mostra sem casas decimais
            if abs(valor_float) <= 999 and valor_float.is_integer():
                return f"{int(valor_float)}"
            elif abs(valor_float) <= 999:
                # Para valores decimais até 999, mostra com 2 casas decimais
                return f"{valor_float:.2f}".replace(".", ",")
            else:
                # Para valores acima de 999, mostra com separador de milhar e 3 casas decimais
                parte_inteira = int(valor_float)
                parte_decimal = valor_float - parte_inteira
                parte_inteira_str = f"{parte_inteira:,}".replace(",", ".")
                parte_decimal_str = f"{parte_decimal:.3f}"[1:].replace('.', ',')
                return f"{parte_inteira_str}{parte_decimal_str}"

        except Exception:
            return str(valor)

if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1200x800")
    app.title("Sistema de Entrada de Estoque")
    try:
        db.fetch_one('SELECT 1')
        print('[OK] Conexão com o banco de dados verificada com sucesso.')
        EntradaEstoqueApp(app)
    except Exception as e:
        print(f'[ERRO FATAL] Não foi possível conectar ao banco de dados: {e}')
        ctk.CTkLabel(app, text=f"ERRO DE CONEXÃO:\n{e}", text_color="red", font=("Arial", 16)).pack(pady=50, padx=20)
    app.mainloop()

#atual 14/12/2025
