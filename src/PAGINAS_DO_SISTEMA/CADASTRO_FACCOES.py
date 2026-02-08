from PAGINAS_DO_SISTEMA import TEMAS
import os
import customtkinter as ctk
from tkinter import ttk, messagebox, END
from datetime import datetime

# Importa o módulo de acesso ao PostgreSQL
try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except ImportError:
    # Fallback para desenvolvimento local
    def get_conn():
        raise RuntimeError("Módulo BANCO_DE_DADOS_PG não encontrado")


    def get_schema():
        return "opera"


    def require_ready(essentials=None):
        return False, "Módulo de banco de dados não disponível"


class CadastroFaccoesView(ctk.CTkFrame):

    def __init__(self, master, sistema=None, app=None, *args, **kwargs):
        """
        Construtor compatível com o menu principal.

        O menu tenta instanciar assim, nessa ordem:
        - klass(master=parent, sistema=self)
        - klass(master=parent, app=self)
        - klass(master=parent)
        - klass(parent)

        Por isso deixamos 'sistema' e 'app' opcionais.
        """
        super().__init__(master, *args, **kwargs)

        # Referências básicas
        self.parent = master

        # Se vier 'sistema' ou 'app', usa como referência para cores / integrações
        if sistema is None:
            sistema = app  # permite funcionar tanto com 'sistema' quanto com 'app'

        self.sistema = sistema
        self.app = sistema  # para compatibilidade com código antigo que usa self.app

        # --- Configuração de cores (com fallback) ---
        origem = self.sistema  # atalhos; pode ser None, getattr trata o default

        self.cor_primaria = getattr(origem, 'cor_primaria', '#275090')
        self.cor_secundaria = getattr(origem, 'cor_secundaria', '#80bbff')
        self.cor_terciaria = getattr(origem, 'cor_terciaria', self.cor_secundaria)
        self.cor_fundo = getattr(origem, 'cor_fundo', '#f0f0f0')
        self.cor_texto = getattr(origem, 'cor_texto', '#2c3e50')
        self.cor_destaque = getattr(origem, 'cor_selecao', '#e74c3c')
        self.cor_sucesso = getattr(origem, 'cor_sucesso', '#27ae60')
        self.cor_alerta = getattr(origem, 'cor_alerta', '#f39c12')
        self.cor_erro = getattr(origem, 'cor_erro', self.cor_alerta)
        self.cor_borda = getattr(origem, 'cor_borda', '#c0c0c0')
        self.cor_hover = getattr(origem, 'cor_hover', '#a0c0ff')

        # --- Estado ---
        self.faccao_selecionada = None
        self.modo_edicao = False
        self.entries = {}

        # --- Verificar conexão com o banco PostgreSQL ---
        self.verificar_conexao_banco()

        # --- Inicialização da interface ---
        self.criar_interface()
        if hasattr(self, "configurar_eventos"):
            self.configurar_eventos()

        # --- Carregamento inicial adiado para garantir que a UI esteja pronta ---
        self.after_idle(self._carregar_inicial)

    def verificar_conexao_banco(self):
        """Verifica se a conexão com o PostgreSQL está funcionando"""
        try:
            # Remove o parâmetro ou ajuste conforme a implementação real
            ok, msg = require_ready()  # Sem parâmetro
            if not ok:
                messagebox.showwarning("Aviso",
                                       f"Problema na conexão com o banco de dados:\n{msg}\n\n"
                                       "Algumas funcionalidades podem não estar disponíveis.")
        except Exception as err:
            messagebox.showwarning("Aviso",
                                   f"Erro ao verificar conexão com o banco:\n{err}\n\n"
                                   "O sistema tentará continuar, mas pode haver problemas.")

    def _ensure_table_schema(self, cursor):
        """Garante que a tabela existe com o schema correto (compatível com o SQL)"""
        schema = get_schema()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema}.cadastro_faccoes (
                id               SERIAL PRIMARY KEY,
                codigo           VARCHAR(10) UNIQUE NOT NULL,
                tipo_prestador   VARCHAR(50) NOT NULL DEFAULT 'Facção',
                nome             VARCHAR(200) NOT NULL,
                telefone         VARCHAR(50),
                endereco         TEXT,
                titular_da_conta VARCHAR(200),
                cpf              VARCHAR(20),
                banco            VARCHAR(50),
                agencia          VARCHAR(20),
                conta            VARCHAR(30),
                pix              VARCHAR(100),
                data             DATE,
                data_atualizacao DATE
            )
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.cadastro_faccoes
            ADD COLUMN IF NOT EXISTS tipo_prestador VARCHAR(50) NOT NULL DEFAULT 'Facção'
        """)

        # Cria índices se não existirem
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_faccoes_nome 
            ON {schema}.cadastro_faccoes (nome)
        """)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_faccoes_codigo 
            ON {schema}.cadastro_faccoes (codigo)
        """)

    def configurar_eventos(self):
        """Configura eventos adicionais"""
        # Atualiza a pesquisa enquanto digita
        self.entry_pesquisa.bind('<KeyRelease>', lambda e: self.pesquisar_faccoes())

        # Enter no campo de pesquisa executa a busca
        self.entry_pesquisa.bind('<Return>', lambda e: self.pesquisar_faccoes())

    def verificar_consistencia_banco(self):
        """Verificação de consistência adaptada para PostgreSQL"""
        try:
            schema = get_schema()
            conn = get_conn()
            cursor = conn.cursor()

            cursor.execute(f"SELECT codigo FROM {schema}.cadastro_faccoes")
            codigos_banco = {row[0] for row in cursor.fetchall()}

            codigos_tree = {self.tree.item(item)['values'][0] for item in self.tree.get_children()}
            fantasmas = codigos_tree - codigos_banco

            if fantasmas:
                for item in self.tree.get_children():
                    if self.tree.item(item)['values'][0] in fantasmas:
                        self.tree.delete(item)

            conn.close()
            return True
        except Exception as err:
            print(f"Erro na verificação: {err}")
            return False

    def configurar_estilo_treeview(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Custom.Treeview",
                        background=self.cor_secundaria,
                        foreground=self.cor_texto,
                        rowheight=26,
                        fieldbackground=self.cor_secundaria,
                        font=('Arial', 10),
                        bordercolor=self.cor_borda)
        style.map("Custom.Treeview",
                  background=[('selected', self.cor_hover)],
                  foreground=[('selected', 'white')])
        style.configure("Custom.Treeview.Heading",
                        font=('Arial', 11, 'bold'),
                        background=self.cor_primaria,
                        foreground=self.cor_texto)

    def criar_interface(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo, corner_radius=0)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)

        # Cabeçalho
        header_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_container.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        header_container.grid_columnconfigure(0, weight=1)

        top_row = ctk.CTkFrame(header_container, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew")
        top_row.grid_columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w")
        icon_label = ctk.CTkLabel(title_frame, text="🧵", font=("Roboto", 20), text_color=self.cor_texto)
        icon_label.pack(side="left", padx=(0, 5))
        title_label = ctk.CTkLabel(title_frame, text="Cadastro de Prestadores", font=("Roboto", 18, "bold"),
                                   text_color=self.cor_texto)
        title_label.pack(side="left")

        btn_novo = ctk.CTkButton(
            top_row,
            text="Novo",
            command=self.limpar_campos,
            fg_color=self.cor_destaque,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            border_color=self.cor_borda,
            width=90,
            height=32
        )
        btn_novo.grid(row=0, column=1, sticky="e", padx=(5, 0))

        subtitle_label = ctk.CTkLabel(
            header_container,
            text="Gerencie prestadores e dados de pagamento",
            font=("Roboto", 11),
            text_color=self.cor_texto
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0), padx=(25, 0))

        separator = ctk.CTkFrame(header_container, height=1, fg_color=self.cor_borda)
        separator.grid(row=2, column=0, sticky="ew", pady=(8, 5))

        # Formulário
        form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        form_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        form_frame.grid_columnconfigure(0, weight=1)
        form_frame.grid_columnconfigure(1, weight=1)

        # Dados gerais
        bloco_esquerdo = ctk.CTkFrame(form_frame, fg_color="transparent")
        bloco_esquerdo.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        for label_text, field in [("Nome", "nome"), ("Telefone", "telefone"), ("Endereço", "endereco")]:
            row = ctk.CTkFrame(bloco_esquerdo, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=f"{label_text}:", width=100, anchor="w", text_color=self.cor_texto).pack(side="left",
                                                                                                            padx=(0, 5))
            entry = ctk.CTkEntry(row, height=30, fg_color=self.cor_fundo, text_color=self.cor_texto,
                                 border_color=self.cor_borda)
            entry.pack(side="left", fill="x", expand=True)
            self.entries[field] = entry

        tipo_row = ctk.CTkFrame(bloco_esquerdo, fg_color="transparent")
        tipo_row.pack(fill="x", pady=4)
        ctk.CTkLabel(tipo_row, text="Tipo:", width=100, anchor="w", text_color=self.cor_texto).pack(side="left",
                                                                                                    padx=(0, 5))
        self.tipo_prestador_var = ctk.StringVar(value="Facção")
        self.tipo_prestador_menu = ctk.CTkOptionMenu(
            tipo_row,
            values=[
                "Facção",
                "Bordado",
                "Caseador",
                "Botões",
                "Estamparia",
                "Interna",
                "Tingimento",
                "Outros Trabalhos",
            ],
            variable=self.tipo_prestador_var,
            fg_color=self.cor_fundo,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            width=200
        )
        self.tipo_prestador_menu.pack(side="left", fill="x", expand=True)

        # Dados bancários
        bloco_direito = ctk.CTkFrame(form_frame, fg_color="transparent")
        bloco_direito.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        pagamento_label = ctk.CTkLabel(bloco_direito, text="DADOS PARA PAGAMENTO", font=("Roboto", 12, "bold"),
                                       text_color=self.cor_texto)
        pagamento_label.pack(anchor="w", pady=(0, 6))

        for label_text, field in [
            ("Titular da Conta", "titular_da_conta"),
            ("CPF", "cpf"),
            ("Banco", "banco"),
            ("Agência", "agencia"),
            ("Conta", "conta"),
            ("Pix", "pix")
        ]:
            row = ctk.CTkFrame(bloco_direito, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{label_text}:", width=120, anchor="w", text_color=self.cor_texto).pack(side="left",
                                                                                                            padx=(0, 5))
            entry = ctk.CTkEntry(row, height=30, fg_color=self.cor_fundo, text_color=self.cor_texto,
                                 border_color=self.cor_borda)
            entry.pack(side="left", fill="x", expand=True)
            self.entries[field] = entry

        # Botões de ação
        botoes_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        botoes_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self.btn_salvar = self._criar_botao(botoes_frame, "Cadastrar", self.salvar_faccao, self.cor_sucesso)
        self.btn_excluir = self._criar_botao(botoes_frame, "Excluir", self.excluir_faccao, self.cor_primaria,
                                             "disabled")
        self.btn_limpar = self._criar_botao(botoes_frame, "Limpar", self.limpar_campos, self.cor_primaria)

        # Busca
        search_frame = ctk.CTkFrame(main_frame, fg_color="transparent", height=36)
        search_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 5))
        self.entry_pesquisa = ctk.CTkEntry(
            search_frame,
            placeholder_text="Pesquisar prestadores...",
            width=240,
            height=32,
            fg_color=self.cor_fundo,
            text_color=self.cor_texto,
            border_color=self.cor_borda
        )
        self.entry_pesquisa.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_pesquisa.bind("<KeyRelease>", lambda e: self.pesquisar_faccoes())
        self.tipo_filtro_var = ctk.StringVar(value="Todos")
        self.tipo_filtro_menu = ctk.CTkOptionMenu(
            search_frame,
            values=[
                "Todos",
                "Facção",
                "Bordado",
                "Caseador",
                "Botões",
                "Estamparia",
                "Interna",
                "Tingimento",
                "Outros Trabalhos",
            ],
            variable=self.tipo_filtro_var,
            fg_color=self.cor_fundo,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            width=160,
            command=lambda _: self.pesquisar_faccoes()
        )
        self.tipo_filtro_menu.pack(side="left", padx=(0, 5))
        self._criar_botao(search_frame, "Buscar", self.pesquisar_faccoes, self.cor_destaque, width=90, height=32)

        # Treeview
        tree_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        tree_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        tree_container = ctk.CTkFrame(tree_frame, fg_color=self.cor_secundaria, corner_radius=6)
        tree_container.grid(row=0, column=0, sticky="nsew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_container,
            columns=("Código", "Nome", "Tipo", "Telefone", "Endereço",
                     "Titular da Conta", "CPF", "Banco", "Agência",
                     "Conta", "Pix", "Data"),
            show="headings",
            selectmode="browse",
            style="Custom.Treeview"
        )
        self.tree.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        col_config = {
            "Código": 60,
            "Nome": 120,
            "Tipo": 110,
            "Telefone": 100,
            "Endereço": 200,
            "Titular da Conta": 150,
            "CPF": 110,
            "Banco": 100,
            "Agência": 80,
            "Conta": 100,
            "Pix": 140,
            "Data": 140
        }
        for col, width in col_config.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=width, stretch=False)

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.configurar_estilo_treeview()
        self.tree.bind("<Double-1>", self.selecionar_faccao)
        self.tree.bind("<<TreeviewSelect>>", self.atualizar_botoes_por_selecao)

        self.pesquisar_faccoes()

    def _criar_botao(self, parent, texto, comando, cor_fg, estado="normal", width=100, height=32):
        btn = ctk.CTkButton(parent, text=texto, command=comando, fg_color=cor_fg, hover_color=self.cor_hover,
                            text_color=self.cor_texto, border_color=self.cor_borda, state=estado,
                            width=width, height=height)
        btn.pack(side="left", padx=3)
        return btn

    def atualizar_estado_botoes(self):
        if self.modo_edicao:
            self.btn_salvar.configure(text="Atualizar", fg_color=self.cor_alerta)
            self.btn_excluir.configure(state="disabled")
        else:
            self.btn_salvar.configure(text="Cadastrar", fg_color=self.cor_sucesso)
            estado = "normal" if self.faccao_selecionada else "disabled"
            self.btn_excluir.configure(state=estado)

    def atualizar_botoes_por_selecao(self, event):
        sel = self.tree.focus()
        if sel:
            self.faccao_selecionada = self.tree.item(sel)['values']
            self.btn_excluir.configure(state="normal")
        else:
            self.faccao_selecionada = None
            self.btn_excluir.configure(state="disabled")

    def selecionar_faccao(self, event):
        sel = self.tree.focus()
        if not sel:
            return
        self.faccao_selecionada = self.tree.item(sel)['values']
        self.modo_edicao = True
        self.editar_faccao()
        self.atualizar_estado_botoes()

    def limpar_campos(self):
        for e in self.entries.values():
            e.delete(0, END)
        self.tipo_prestador_var.set("Facção")
        self.modo_edicao = False
        self.faccao_selecionada = None
        self.tree.selection_remove(self.tree.selection())
        self.atualizar_estado_botoes()

    def editar_faccao(self):
        if not self.faccao_selecionada:
            return

        mapping = {
            "nome": 1,
            "telefone": 3,
            "endereco": 4,
            "titular_da_conta": 5,
            "cpf": 6,
            "banco": 7,
            "agencia": 8,
            "conta": 9,
            "pix": 10
        }

        self.tipo_prestador_var.set(self.faccao_selecionada[2])
        for field, index in mapping.items():
            self.entries[field].delete(0, END)
            value = self.faccao_selecionada[index]
            self.entries[field].insert(0, "" if value is None else str(value))

    def salvar_faccao(self):
        """Insere ou atualiza um prestador no PostgreSQL, mantendo a lógica e a UI atuais."""
        # Coleta e normaliza dados da UI
        dados = {f: self.entries[f].get().strip() for f in self.entries}
        dados["tipo_prestador"] = self.tipo_prestador_var.get().strip()

        # Validação mínima
        obrigatorios = ["nome", "telefone", "endereco", "tipo_prestador"]
        for campo in obrigatorios:
            if not dados.get(campo):
                messagebox.showwarning("Aviso", f"Preencha o campo obrigatório: {campo.capitalize()}")
                return

        def norm(v):
            v = (v or "").strip()
            return v if v else None

        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cur = conn.cursor()

            # ✅ coluna 'data' é DATE, então salvamos DATE de verdade (sem string)
            now_date = datetime.now().date()

            if self.modo_edicao and self.faccao_selecionada:
                codigo_alvo = str(self.faccao_selecionada[0]).strip()

                cur.execute(
                    f"""
                    UPDATE {schema}.cadastro_faccoes SET
                        tipo_prestador=%s,
                        nome=%s,
                        telefone=%s,
                        endereco=%s,
                        titular_da_conta=%s,
                        cpf=%s,
                        banco=%s,
                        agencia=%s,
                        conta=%s,
                        pix=%s,
                        data=%s,
                        data_atualizacao=CURRENT_DATE
                    WHERE codigo=%s
                    """,
                    (
                        dados["tipo_prestador"],
                        dados["nome"], dados["telefone"], dados["endereco"],
                        norm(dados.get("titular_da_conta")),
                        norm(dados.get("cpf")),
                        norm(dados.get("banco")),
                        norm(dados.get("agencia")),
                        norm(dados.get("conta")),
                        norm(dados.get("pix")),
                        now_date,
                        codigo_alvo,
                    ),
                )
                msg = "Prestador atualizado!"
            else:
                # Gera próximo código: ignora vazios e converte para int com segurança
                cur.execute(f"SELECT MAX(NULLIF(codigo,'')::int) FROM {schema}.cadastro_faccoes")
                max_int = cur.fetchone()[0]
                proximo_codigo = 1 if max_int is None else int(max_int) + 1
                codigo_final = str(proximo_codigo).zfill(3)

                cur.execute(
                    f"""
                    INSERT INTO {schema}.cadastro_faccoes (
                        codigo, tipo_prestador, nome, telefone, endereco,
                        titular_da_conta, cpf, banco, agencia, conta, pix, data
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        codigo_final,
                        dados["tipo_prestador"],
                        dados["nome"], dados["telefone"], dados["endereco"],
                        norm(dados.get("titular_da_conta")),
                        norm(dados.get("cpf")),
                        norm(dados.get("banco")),
                        norm(dados.get("agencia")),
                        norm(dados.get("conta")),
                        norm(dados.get("pix")),
                        now_date,
                    ),
                )
                msg = "Prestador cadastrado!"

            conn.commit()
            messagebox.showinfo("Sucesso", msg)
            self.pesquisar_faccoes()
            self.limpar_campos()

        except Exception as err:
            messagebox.showerror("Erro", f"Falha ao salvar:\n{err}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def pesquisar_faccoes(self):
        """Pesquisa prestadores no banco PostgreSQL"""
        # Limpa a Treeview completamente
        self.tree.delete(*self.tree.get_children())

        termo = (self.entry_pesquisa.get() or "").strip()
        tipo_filtro = (self.tipo_filtro_var.get() or "Todos").strip()
        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cursor = conn.cursor()

            # Consulta corrigida - removida referência à coluna data_criacao
            query = f"""
                SELECT
                    codigo, nome, tipo_prestador, telefone, endereco,
                    titular_da_conta, cpf, banco, agencia, conta, pix,
                    COALESCE(data_atualizacao::text, data::text) AS data_exibicao
                FROM {schema}.cadastro_faccoes
                WHERE (%s = '' OR nome ILIKE %s OR codigo ILIKE %s)
                  AND (%s = 'Todos' OR tipo_prestador = %s)
                ORDER BY
                    NULLIF(codigo,'')::int DESC NULLS LAST
            """
            like = f"%{termo}%"
            cursor.execute(query, (termo, like, like, tipo_filtro, tipo_filtro))

            for row in cursor.fetchall():
                self.tree.insert("", "end", values=tuple("" if v is None else str(v) for v in row))

        except Exception as err:
            messagebox.showerror("Erro", f"Falha ao carregar prestadores:\n{err}")
        finally:
            if conn:
                conn.close()

    def excluir_faccao(self):
        if not self.faccao_selecionada:
            messagebox.showwarning("Aviso", "Nenhum prestador selecionado para excluir")
            return

        codigo = str(self.faccao_selecionada[0]).strip()
        nome = self.faccao_selecionada[1]

        confirmacao = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Tem certeza que deseja excluir permanentemente:\n"
            f"Código: {codigo}\n"
            f"Prestador: {nome}",
            icon="warning"
        )

        if not confirmacao:
            return

        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cursor = conn.cursor()

            cursor.execute(f"DELETE FROM {schema}.cadastro_faccoes WHERE codigo = %s", (codigo,))

            conn.commit()

            self.verificar_consistencia_banco()
            self.pesquisar_faccoes()
            self.limpar_campos()

            messagebox.showinfo("Sucesso", "Registro excluído com sucesso!")

        except Exception as err:
            messagebox.showerror("Erro", f"Falha na exclusão:\n{str(err)}")

        finally:
            if conn:
                conn.close()

    def limpar_registros_fantasmas(self):
        """Força a verificação/remoção de fantasmas"""
        self.verificar_consistencia_banco()

    def recarregar_dados(self):
        self.verificar_consistencia_banco()
        self.pesquisar_faccoes()
        messagebox.showinfo("Info", "Dados recarregados com sucesso!")

    def _carregar_inicial(self):
        """Método chamado após a interface ser carregada, para exibir os dados imediatamente"""
        self.verificar_consistencia_banco()
        self.pesquisar_faccoes()


if __name__ == "__main__":
    root = ctk.CTk()
    root.geometry("950x650")
    # cores de exemplo
    root.cor_primaria = "#2f4f7f"
    root.cor_secundaria = "#242f44"
    root.cor_terciaria = "#445c9c"
    root.cor_fundo = "#1f2637"
    root.cor_texto = "#f0f0f0"
    root.cor_destaque = "#e07d31"
    root.cor_sucesso = "#27ae60"
    root.cor_alerta = "#ffb400"
    root.cor_borda = "#3f5470"
    root.cor_hover = "#3f6fa0"

    app = CadastroFaccoesView(root, root)
    app.pack(fill="both", expand=True)
    root.mainloop()

# 31/01/2026##