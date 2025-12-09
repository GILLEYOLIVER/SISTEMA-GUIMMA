import TEMAS
import os
import customtkinter as ctk
from tkinter import ttk, messagebox, END
from datetime import datetime

# Importa o módulo de acesso ao PostgreSQL
try:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
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

        # --- Configuração de cores pelo tema (PADRÃO IGUAL ÀS OUTRAS PÁGINAS) ---
        self.obter_cores_por_tema()

        # Aplica cor de fundo no frame principal (igual Entrada de Estoque / Relatórios)
        self.configure(fg_color=self.cor_fundo)

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

    # ======================================================================
    # TEMA / CORES (MESMA LÓGICA DAS OUTRAS PÁGINAS)
    # ======================================================================
    def obter_cores_por_tema(self):
        """
        Define cores dinamicamente baseado no tema atual (Dark / Light)
        e nas cores definidas no sistema principal.
        """
        tema_atual = ctk.get_appearance_mode()
        origem = self.sistema or self.parent

        if tema_atual == "Dark":
            # Tema escuro – segue padrão do sistema
            self.cor_fundo = getattr(origem, "cor_fundo", "#020617")
            self.cor_primaria = getattr(origem, "cor_primaria", "#1f2937")
            self.cor_secundaria = getattr(origem, "cor_secundaria", "#111827")
            self.cor_terciaria = getattr(origem, "cor_terciaria", self.cor_secundaria)
            self.cor_texto = getattr(origem, "cor_texto", "#e5e7eb")
            self.cor_borda = getattr(origem, "cor_borda", "#273244")
            self.cor_hover = getattr(origem, "cor_hover", "#334155")
            self.cor_destaque = getattr(origem, "cor_destaque",
                                        getattr(origem, "cor_selecao", "#f97316"))
            self.cor_sucesso = getattr(origem, "cor_sucesso", "#22c55e")
            self.cor_alerta = getattr(origem, "cor_alerta", "#eab308")
            self.cor_erro = getattr(origem, "cor_erro", "#ef4444")
        else:
            # Tema claro – padrão consistente com as outras telas
            self.cor_fundo = getattr(origem, "cor_fundo", "#ffffff")
            self.cor_primaria = getattr(origem, "cor_primaria", "#3a7ebf")
            self.cor_secundaria = getattr(origem, "cor_secundaria", "#f0f0f0")
            self.cor_terciaria = getattr(origem, "cor_terciaria", self.cor_secundaria)
            self.cor_texto = getattr(origem, "cor_texto", "#111827")
            self.cor_borda = getattr(origem, "cor_borda", "#cccccc")
            self.cor_hover = getattr(origem, "cor_hover", "#2e4a66")
            self.cor_destaque = getattr(origem, "cor_destaque",
                                        getattr(origem, "cor_selecao", "#2563eb"))
            self.cor_sucesso = getattr(origem, "cor_sucesso", "#16a34a")
            self.cor_alerta = getattr(origem, "cor_alerta", "#eab308")
            self.cor_erro = getattr(origem, "cor_erro", "#b91c1c")

    # ======================================================================
    # BANCO / CONSISTÊNCIA
    # ======================================================================
    def verificar_conexao_banco(self):
        """Verifica se a conexão com o PostgreSQL está funcionando"""
        try:
            ok, msg = require_ready()  # Sem parâmetro
            if not ok:
                messagebox.showwarning(
                    "Aviso",
                    f"Problema na conexão com o banco de dados:\n{msg}\n\n"
                    "Algumas funcionalidades podem não estar disponíveis."
                )
        except Exception as err:
            messagebox.showwarning(
                "Aviso",
                f"Erro ao verificar conexão com o banco:\n{err}\n\n"
                "O sistema tentará continuar, mas pode haver problemas."
            )

    def _ensure_table_schema(self, cursor):
        """Garante que a tabela existe com o schema correto (compatível com o SQL)"""
        schema = get_schema()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema}.cadastro_faccoes (
                id               SERIAL PRIMARY KEY,
                codigo           VARCHAR(10) UNIQUE NOT NULL,
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

    # ======================================================================
    # TREEVIEW – PADRÃO VISUAL IGUAL ÀS OUTRAS TELAS
    # ======================================================================
    def configurar_estilo_treeview(self):
        """
        Estilo da Treeview padronizado:
        - Cabeçalho azul escuro
        - Seleção azul claro (igual ao print)
        - Linhas claras
        """
        style = ttk.Style()
        style.theme_use("default")

        tema = ctk.get_appearance_mode()

        # --------- CORES DE FUNDO ---------
        if tema == "Dark":
            bg = self.cor_secundaria if hasattr(self, "cor_secundaria") else "#111827"
            fg = self.cor_texto if hasattr(self, "cor_texto") else "#E5E7EB"
        else:
            bg = "#F5F5F5"
            fg = "#111111"

        # --------- CABEÇALHO ---------
        header_bg = "#1E3A8A"  # azul cabeçalho
        header_fg = "#FFFFFF"  # texto branco
        header_hover_bg = "#4F8BFF"  # hover no título

        # --------- SELEÇÃO DA LINHA ---------
        select_bg = "#4A90E2"  # ⭐ azul claro igual ao print
        select_fg = "#FFFFFF"  # texto branco

        # --------- CORPO ---------
        style.configure(
            "Custom.Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            rowheight=26,
            font=("Arial", 10),
            borderwidth=0,
            highlightthickness=0,
        )

        # --------- CABEÇALHO ---------
        style.configure(
            "Custom.Treeview.Heading",
            background=header_bg,
            foreground=header_fg,
            font=("Arial", 11, "bold"),
            relief="flat",
            borderwidth=1,
            padding=4,
        )

        style.map(
            "Custom.Treeview.Heading",
            background=[
                ("active", header_hover_bg),
                ("!disabled", header_bg),
            ],
            foreground=[("active", header_fg)]
        )

        # --------- SELEÇÃO FINAL (IGUAL AO PRINT) ---------
        style.map(
            "Custom.Treeview",
            background=[
                ("selected", select_bg),
                ("!selected", bg),
            ],
            foreground=[
                ("selected", select_fg),
                ("!selected", fg),
            ],
        )

    # ======================================================================
    # INTERFACE
    # ======================================================================
    def criar_interface(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo, corner_radius=0)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)

        # ==========================
        # CABEÇALHO
        # ==========================
        header_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_container.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        header_container.grid_columnconfigure(0, weight=1)

        top_row = ctk.CTkFrame(header_container, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew")
        top_row.grid_columnconfigure(0, weight=1)

        title_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w")

        icon_label = ctk.CTkLabel(
            title_frame,
            text="🧵",
            font=("Roboto", 20),
            text_color=self.cor_texto
        )
        icon_label.pack(side="left", padx=(0, 5))

        title_label = ctk.CTkLabel(
            title_frame,
            text="Cadastro de Facções",
            font=("Roboto", 18, "bold"),
            text_color=self.cor_texto
        )
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
            height=32,
        )
        btn_novo.grid(row=0, column=1, sticky="e", padx=(5, 0))

        subtitle_label = ctk.CTkLabel(
            header_container,
            text="Gerencie facções e dados de pagamento",
            font=("Roboto", 11),
            text_color=self.cor_texto,
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0), padx=(25, 0))

        separator = ctk.CTkFrame(header_container, height=1, fg_color=self.cor_borda)
        separator.grid(row=2, column=0, sticky="ew", pady=(8, 5))

        # ==========================
        # FORMULÁRIO
        # ==========================
        form_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        form_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        form_frame.grid_columnconfigure(0, weight=1)
        form_frame.grid_columnconfigure(1, weight=1)

        # --- Bloco esquerdo: dados gerais ---
        bloco_esquerdo = ctk.CTkFrame(form_frame, fg_color="transparent")
        bloco_esquerdo.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        for label_text, field in [
            ("Nome", "nome"),
            ("Telefone", "telefone"),
            ("Endereço", "endereco"),
        ]:
            row = ctk.CTkFrame(bloco_esquerdo, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(
                row,
                text=f"{label_text}:",
                width=100,
                anchor="w",
                text_color=self.cor_texto,
            ).pack(side="left", padx=(0, 5))
            entry = ctk.CTkEntry(
                row,
                height=30,
                fg_color=self.cor_fundo,
                text_color=self.cor_texto,
                border_color=self.cor_borda,
            )
            entry.pack(side="left", fill="x", expand=True)
            self.entries[field] = entry

        # --- Bloco direito: dados para pagamento ---
        bloco_direito = ctk.CTkFrame(form_frame, fg_color="transparent")
        bloco_direito.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        pagamento_label = ctk.CTkLabel(
            bloco_direito,
            text="DADOS PARA PAGAMENTO",
            font=("Roboto", 12, "bold"),
            text_color=self.cor_texto,
        )
        pagamento_label.pack(anchor="w", pady=(0, 6))

        for label_text, field in [
            ("Titular da Conta", "titular_da_conta"),
            ("CPF", "cpf"),
            ("Banco", "banco"),
            ("Agência", "agencia"),
            ("Conta", "conta"),
            ("Pix", "pix"),
        ]:
            row = ctk.CTkFrame(bloco_direito, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row,
                text=f"{label_text}:",
                width=120,
                anchor="w",
                text_color=self.cor_texto,
            ).pack(side="left", padx=(0, 5))
            entry = ctk.CTkEntry(
                row,
                height=30,
                fg_color=self.cor_fundo,
                text_color=self.cor_texto,
                border_color=self.cor_borda,
            )
            entry.pack(side="left", fill="x", expand=True)
            self.entries[field] = entry

        # --- Botões de ação ---
        botoes_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        botoes_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self.btn_salvar = self._criar_botao(
            botoes_frame, "Cadastrar", self.salvar_faccao, self.cor_sucesso
        )
        self.btn_excluir = self._criar_botao(
            botoes_frame, "Excluir", self.excluir_faccao, self.cor_primaria, "disabled"
        )
        self.btn_limpar = self._criar_botao(
            botoes_frame, "Limpar", self.limpar_campos, self.cor_primaria
        )

        # ==========================
        # BUSCA
        # ==========================
        search_frame = ctk.CTkFrame(main_frame, fg_color="transparent", height=36)
        search_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 5))

        self.entry_pesquisa = ctk.CTkEntry(
            search_frame,
            placeholder_text="Pesquisar facções...",
            width=240,
            height=32,
            fg_color=self.cor_fundo,
            text_color=self.cor_texto,
            border_color=self.cor_borda,
        )
        self.entry_pesquisa.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_pesquisa.bind("<KeyRelease>", lambda e: self.pesquisar_faccoes())

        self._criar_botao(
            search_frame,
            "Buscar",
            self.pesquisar_faccoes,
            self.cor_destaque,
            width=90,
            height=32,
        )

        # ==========================
        # TREEVIEW – LISTA DE FACÇÕES
        # ==========================
        tree_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        tree_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        tree_container = ctk.CTkFrame(
            tree_frame, fg_color=self.cor_secundaria, corner_radius=6
        )
        tree_container.grid(row=0, column=0, sticky="nsew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # 👉 PRIMEIRO configuramos o estilo (inclui cabeçalho colorido)
        self.configurar_estilo_treeview()

        # Agora criamos a Treeview usando o estilo "Custom.Treeview"
        self.tree = ttk.Treeview(
            tree_container,
            columns=(
                "Código",
                "Nome",
                "Telefone",
                "Endereço",
                "Titular da Conta",
                "CPF",
                "Banco",
                "Agência",
                "Conta",
                "Pix",
                "Data",
            ),
            show="headings",
            selectmode="browse",
            style="Custom.Treeview",
        )
        self.tree.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        col_config = {
            "Código": 60,
            "Nome": 120,
            "Telefone": 100,
            "Endereço": 200,
            "Titular da Conta": 150,
            "CPF": 110,
            "Banco": 100,
            "Agência": 80,
            "Conta": 100,
            "Pix": 140,
            "Data": 140,
        }
        for col, width in col_config.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=width, stretch=False)

        scrollbar = ttk.Scrollbar(
            tree_container, orient="vertical", command=self.tree.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Eventos da tabela
        self.tree.bind("<Double-1>", self.selecionar_faccao)
        self.tree.bind("<<TreeviewSelect>>", self.atualizar_botoes_por_selecao)

        # Carregamento inicial
        self.pesquisar_faccoes()

    # ======================================================================
    # BOTÕES / ESTADO
    # ======================================================================
    def _criar_botao(self, parent, texto, comando, cor_fg,
                     estado="normal", width=100, height=32):
        btn = ctk.CTkButton(
            parent,
            text=texto,
            command=comando,
            fg_color=cor_fg,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            border_color=self.cor_borda,
            state=estado,
            width=width,
            height=height,
        )
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

    # ======================================================================
    # AÇÕES CRUD
    # ======================================================================
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
        self.modo_edicao = False
        self.faccao_selecionada = None
        self.tree.selection_remove(self.tree.selection())
        self.atualizar_estado_botoes()

    def editar_faccao(self):
        if not self.faccao_selecionada:
            return

        mapping = {
            "nome": 1,
            "telefone": 2,
            "endereco": 3,
            "titular_da_conta": 4,
            "cpf": 5,
            "banco": 6,
            "agencia": 7,
            "conta": 8,
            "pix": 9,
        }

        for field, index in mapping.items():
            self.entries[field].delete(0, END)
            value = self.faccao_selecionada[index]
            self.entries[field].insert(0, "" if value is None else str(value))

    def salvar_faccao(self):
        """Insere ou atualiza uma facção no PostgreSQL, mantendo a lógica e a UI atuais."""
        # Coleta e normaliza dados da UI
        dados = {f: self.entries[f].get().strip() for f in self.entries}

        # Validação mínima
        obrigatorios = ["nome", "telefone", "endereco"]
        for campo in obrigatorios:
            if not dados.get(campo):
                messagebox.showwarning(
                    "Aviso", f"Preencha o campo obrigatório: {campo.capitalize()}"
                )
                return

        def norm(v):
            v = (v or "").strip()
            return v if v else None

        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cur = conn.cursor()

            # Data de exibição (texto), compatível com schemas antigos
            now_txt = datetime.now().strftime("%d/%m/%Y %H:%M")

            if self.modo_edicao and self.faccao_selecionada:
                codigo_alvo = str(self.faccao_selecionada[0]).strip()

                # UPDATE
                cur.execute(
                    f"""
                    UPDATE {schema}.cadastro_faccoes SET
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
                        data_atualizacao=CURRENT_TIMESTAMP
                    WHERE codigo=%s
                    """,
                    (
                        dados["nome"], dados["telefone"], dados["endereco"],
                        norm(dados.get("titular_da_conta")),
                        norm(dados.get("cpf")),
                        norm(dados.get("banco")),
                        norm(dados.get("agencia")),
                        norm(dados.get("conta")),
                        norm(dados.get("pix")),
                        now_txt,
                        codigo_alvo,
                    ),
                )
                msg = "Facção atualizada!"
            else:
                # Gera próximo código
                cur.execute(
                    f"SELECT MAX(NULLIF(codigo,'')::int) FROM {schema}.cadastro_faccoes"
                )
                max_int = cur.fetchone()[0]
                proximo_codigo = 1 if max_int is None else int(max_int) + 1
                codigo_final = str(proximo_codigo).zfill(3)

                # INSERT
                cur.execute(
                    f"""
                    INSERT INTO {schema}.cadastro_faccoes (
                        codigo, nome, telefone, endereco,
                        titular_da_conta, cpf, banco, agencia, conta, pix, data
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        codigo_final,
                        dados["nome"], dados["telefone"], dados["endereco"],
                        norm(dados.get("titular_da_conta")),
                        norm(dados.get("cpf")),
                        norm(dados.get("banco")),
                        norm(dados.get("agencia")),
                        norm(dados.get("conta")),
                        norm(dados.get("pix")),
                        now_txt,
                    ),
                )
                msg = "Facção cadastrada!"

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
        """Pesquisa facções no banco PostgreSQL"""
        # Limpa a Treeview
        self.tree.delete(*self.tree.get_children())

        termo = (self.entry_pesquisa.get() or "").strip()
        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cursor = conn.cursor()

            query = f"""
                SELECT
                    codigo, nome, telefone, endereco,
                    titular_da_conta, cpf, banco, agencia, conta, pix,
                    COALESCE(data_atualizacao::text, data::text) AS data_exibicao
                FROM {schema}.cadastro_faccoes
                WHERE (%s = '' OR nome ILIKE %s OR codigo ILIKE %s)
                ORDER BY
                    NULLIF(codigo,'')::int DESC NULLS LAST
            """
            like = f"%{termo}%"
            cursor.execute(query, (termo, like, like))

            for row in cursor.fetchall():
                self.tree.insert(
                    "", "end",
                    values=tuple("" if v is None else str(v) for v in row)
                )

        except Exception as err:
            messagebox.showerror(
                "Erro", f"Falha ao carregar facções:\n{err}"
            )
        finally:
            if conn:
                conn.close()

    def excluir_faccao(self):
        if not self.faccao_selecionada:
            messagebox.showwarning(
                "Aviso", "Nenhuma facção selecionada para excluir"
            )
            return

        codigo = str(self.faccao_selecionada[0]).strip()
        nome = self.faccao_selecionada[1]

        confirmacao = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Tem certeza que deseja excluir permanentemente:\n"
            f"Código: {codigo}\n"
            f"Facção: {nome}",
            icon="warning",
        )

        if not confirmacao:
            return

        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cursor = conn.cursor()

            cursor.execute(
                f"DELETE FROM {schema}.cadastro_faccoes WHERE codigo = %s",
                (codigo,),
            )

            conn.commit()

            self.verificar_consistencia_banco()
            self.pesquisar_faccoes()
            self.limpar_campos()

            messagebox.showinfo("Sucesso", "Registro excluído com sucesso!")

        except Exception as err:
            messagebox.showerror(
                "Erro", f"Falha na exclusão:\n{str(err)}"
            )
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
    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.geometry("950x650")

    # Cores de exemplo para teste isolado
    root.cor_primaria = "#1f2937"
    root.cor_secundaria = "#111827"
    root.cor_terciaria = "#374151"
    root.cor_fundo = "#020617"
    root.cor_texto = "#e5e7eb"
    root.cor_destaque = "#f97316"
    root.cor_sucesso = "#22c55e"
    root.cor_alerta = "#eab308"
    root.cor_borda = "#273244"
    root.cor_hover = "#334155"

    app = CadastroFaccoesView(root, root)
    app.pack(fill="both", expand=True)
    root.mainloop()
