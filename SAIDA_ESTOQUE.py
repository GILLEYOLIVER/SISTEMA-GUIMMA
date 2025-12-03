import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime
from TEMAS import get_contraste_texto, is_dark_color, ajustar_hover
import BANCO_DE_DADOS_PG as db


class SaidaEstoqueApp(ctk.CTkFrame):
    def __init__(self, master, sistema=None, app=None, **kwargs):
        """
        Tela de Saída de Estoque.
        """
        super().__init__(master, **kwargs)
        self.master = master

        # -----------------------------
        # 1) Resolver o "sistema" (MENU PRINCIPAL)
        # -----------------------------
        sistema = sistema or app or kwargs.get("sistema") or kwargs.get("app") \
                  or kwargs.get("controller") or kwargs.get("root") or kwargs.get("main")
        self.sistema = sistema
        origem = sistema

        # -----------------------------
        # 2) Cores dinâmicas baseadas no tema
        # -----------------------------
        self.obter_cores_por_tema(origem)

        # Aplica fundo da página
        self.configure(fg_color=self.cor_fundo)
        self.pack(fill="both", expand=True)

        # Verifica conexão com o banco
        if not db or not db.ready_check():
            ctk.CTkLabel(
                self,
                text="Erro Crítico: Falha na conexão com o banco de dados.",
                text_color=self.cor_alerta,
                font=("Arial", 16),
            ).pack(pady=50)
            return

        # Inicializações principais
        self.entries = {}
        self.tipos = ["Tecidos", "Aviamentos", "Insumos", "Escritorio", "Limpeza", "Outros"]

        # Campos específicos por tipo de produto
        self.campos_por_tipo = {
            "Tecidos": ["descricao", "codigo", "fornecedor", "composicao", "cor", "metros", "kilos"],
            "Aviamentos": ["descricao", "codigo", "fornecedor", "cor", "quantidade", "unidade"],
            "Insumos": ["descricao", "codigo", "tipo", "quantidade", "unidade", "localizacao"],
            "Escritorio": ["descricao", "codigo", "tipo", "quantidade", "unidade", "localizacao"],
            "Limpeza": ["descricao", "codigo", "tipo", "quantidade", "unidade", "localizacao"],
            "Outros": ["descricao", "codigo", "tipo", "quantidade", "unidade", "localizacao"],
        }

        # Nomes amigáveis para exibição
        self.nomes_amigaveis = {
            "id": "ID",
            "descricao": "Descrição",
            "codigo": "Código",
            "fornecedor": "Fornecedor",
            "composicao": "Composição",
            "cor": "Cor",
            "metros": "Metros",
            "kilos": "Kilos",
            "quantidade": "Quantidade",
            "unidade": "Unidade",
            "tipo": "Tipo",
            "localizacao": "Localização",
        }

        # Cria interface e inicializa com o primeiro tipo
        self.setup_ui()
        self.atualizar_interface(self.tipos[0])

    # ------------------- Helpers de conversão -------------------
    def _to_float(self, txt):
        # aceita "1.234,56", "1234.56", "", None
        if txt is None:
            return None
        s = str(txt).strip()
        if not s:
            return None
        # remove milhar e normaliza vírgula
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    def _to_int(self, txt):
        f = self._to_float(txt)
        if f is None:
            return None
        return int(f)

    def formatar_valor(self, valor, campo):
        if valor is None:
            return ""
        try:
            if isinstance(valor, float):
                return str(int(valor)) if valor.is_integer() else f"{valor:.2f}".replace(".", ",")
            if isinstance(valor, int):
                return str(valor)
            return str(valor)
        except (ValueError, TypeError):
            return str(valor)

    # ------------------- UI -------------------
    def setup_ui(self):
        # Atualiza cores baseado no tema atual
        self.obter_cores_por_tema(self.sistema)

        # Frame superior (título + tipo)
        top_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            top_frame,
            text="Saída de Estoque",
            font=("Arial", 18, "bold"),
            text_color=self.cor_texto,
        ).pack(side="left", padx=10)

        self.tipo_var = ctk.StringVar(value=self.tipos[0])
        self.tipo_cb = ctk.CTkOptionMenu(
            top_frame,
            variable=self.tipo_var,
            values=self.tipos,
            command=self.atualizar_interface,
            fg_color=self.cor_secundaria,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover,
        )
        self.tipo_cb.pack(side="right", padx=10, fill="x", expand=True)

        # Linha de seleção de produto
        self.selecao_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        self.selecao_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            self.selecao_frame,
            text="Produto:",
            width=80,
            text_color=self.cor_texto,
        ).pack(side="left", padx=5)

        self.entry_produto = ctk.CTkEntry(
            self.selecao_frame,
            placeholder_text="Digite código ou descrição do produto",
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto_entry,
            placeholder_text_color=self.cor_placeholder,
        )
        self.entry_produto.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_produto.bind("<KeyRelease>", self.filtrar_produtos)

        self.btn_limpar = ctk.CTkButton(
            self.selecao_frame,
            text="Limpar",
            width=80,
            command=self.limpar_pesquisa,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
        )
        self.btn_limpar.pack(side="left", padx=5)

        # Campos de quantidade/metragem
        self.campos_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        self.campos_frame.pack(fill="x", padx=10, pady=10)

        # Botões de ação
        button_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        button_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            button_frame,
            text="Registrar Saída",
            command=self.registrar_saida,
            fg_color=self.cor_sucesso,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Limpar Campos",
            command=self.limpar_campos,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
        ).pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(
            self,
            text="Selecione um produto",
            text_color=self.cor_texto,
        )
        self.status_label.pack(pady=5)

        # Tree de itens em estoque - CONFIGURAÇÃO IDÊNTICA À ENTRADA
        self.tree_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Configurar estilo da Treeview para combinar com o tema
        self.configurar_treeview_theme()

        # CRIA A TREEVIEW COM O ESTILO CORRETO
        self.tree = ttk.Treeview(self.tree_frame, show="headings", style="Custom.Treeview")
        self.tree.pack(fill="both", expand=True)  # MESMO PACK DA ENTRADA
        self.tree.bind("<Double-1>", self.selecionar_para_saida)

        # SCROLLBAR OPCIONAL - REMOVER SE NÃO PRECISAR
        scrollbar = ttk.Scrollbar(
            self.tree_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    # ------------------- Lógica de UI / dados -------------------

    def obter_cores_por_tema(self, origem=None):
        """Define cores de texto dinamicamente baseado no tema atual"""
        tema_atual = ctk.get_appearance_mode()

        if tema_atual == "Dark":
            # Tema escuro - texto branco
            self.cor_fundo = getattr(origem, "cor_fundo", "#020617")
            self.cor_primaria = getattr(origem, "cor_primaria", "#1f2937")
            self.cor_secundaria = getattr(origem, "cor_secundaria", "#111827")
            self.cor_terciaria = getattr(origem, "cor_terciaria", "#0b1220")
            self.cor_texto = getattr(origem, "cor_texto", "#e5e7eb")
            self.cor_texto_entry = "white"
            self.cor_placeholder = "#888888"
            self.cor_borda = getattr(origem, "cor_borda", "#273244")
            self.cor_hover = getattr(origem, "cor_hover", "#334155")
            self.cor_sucesso = getattr(origem, "cor_sucesso", "#22c55e")
            self.cor_alerta = getattr(origem, "cor_alerta", "#ef4444")
            self.cor_selecao = getattr(origem, "cor_selecao", "#2563eb")
        else:
            # Tema claro - texto preto
            self.cor_fundo = "#ffffff"
            self.cor_primaria = "#3a7ebf"
            self.cor_secundaria = "#f0f0f0"
            self.cor_terciaria = "#e0e0e0"
            self.cor_texto = "black"
            self.cor_texto_entry = "black"
            self.cor_placeholder = "#666666"
            self.cor_borda = "#cccccc"
            self.cor_hover = "#2e4a66"
            self.cor_sucesso = "#22c55e"
            self.cor_alerta = "#ef4444"
            self.cor_selecao = "#2563eb"

        # Ajuste de hover com helper, se disponível
        try:
            self.cor_hover = ajustar_hover(self.cor_primaria, fator=0.9)
        except Exception:
            pass

    def _tabela_por_tipo(self, tipo: str) -> str:
        """Mapeia o tipo para o nome real da tabela."""
        mapa = {
            "Tecidos": "estoque_tecidos",
            "Aviamentos": "estoque_aviamentos",
            "Insumos": "estoque_insumos",
            "Escritorio": "estoque_escritorio",
            "Limpeza": "estoque_limpeza",
            "Outros": "estoque_outros",
        }
        return mapa.get(tipo, "").lower()

    def _colunas_preferidas_por_tipo(self, tipo: str):
        """Define colunas que devem ser exibidas por tipo."""
        if tipo == "Tecidos":
            return [
                "id",
                "codigo",
                "descricao",
                "cor",
                "fornecedor",
                "composicao",
                "metros",
                "kilos",
                "data_entrada",
                "observacoes",
            ]
        elif tipo == "Aviamentos":
            return [
                "id",
                "codigo",
                "descricao",
                "fornecedor",
                "cor",
                "quantidade",
                "unidade",
                "data_entrada",
                "observacoes",
            ]
        else:
            # Insumos / Escritório / Limpeza / Outros
            return [
                "id",
                "codigo",
                "descricao",
                "tipo",
                "quantidade",
                "unidade",
                "localizacao",
                "data_entrada",
                "observacoes",
            ]

    def _campos_existentes(self, tabela, candidatos):
        """Retorna apenas os campos realmente existentes no banco."""
        try:
            cols = set(db.list_columns(tabela))
            return [c for c in candidatos if c in cols]
        except Exception:
            return candidatos

    def formatar_valor_tree(self, v, campo=None):
        """Formata número com 2 ou 3 casas, separador decimal vírgula."""
        if v is None:
            return ""
        casas = 3 if campo == "kilos" else 2
        return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def carregar_estoque(self, tipo=None, filtro_termo: str = None):
        """Carrega e exibe os itens do estoque conforme o tipo selecionado."""
        # ATUALIZA O TEMA ANTES DE CARREGAR OS DADOS
        self.configurar_treeview_theme()

        tipo = tipo or self.tipo_var.get()
        if not tipo or tipo.lower() == "selecione o tipo":
            self.status_label.configure(
                text="Selecione um tipo de item para listar.",
                text_color=self.cor_alerta,
            )
            return

        tabela = self._tabela_por_tipo(tipo)
        if not tabela:
            self.status_label.configure(
                text=f"Tipo '{tipo}' inválido.", text_color=self.cor_alerta
            )
            return

        try:
            # verifica se existe
            if not db.table_exists(tabela):
                self.status_label.configure(
                    text=f"Tabela '{tabela}' não existe.",
                    text_color=self.cor_alerta,
                )
                return

            # colunas e SELECT dinâmico
            colunas = self._colunas_preferidas_por_tipo(tipo)
            colunas = self._campos_existentes(tabela, colunas)
            if not colunas:
                self.status_label.configure(
                    text=f"Sem colunas válidas em {tabela}.",
                    text_color=self.cor_alerta,
                )
                return

            where_extra = ""
            params = []
            if filtro_termo:
                where_extra = " AND (descricao ILIKE %s OR codigo ILIKE %s)"
                like = f"%{filtro_termo}%"
                params.extend([like, like])

            sql = (
                f"SELECT {', '.join(colunas)} FROM {tabela} "
                f"WHERE 1=1 {where_extra} ORDER BY id DESC"
            )

            rows = []
            try:
                if hasattr(db, "fetch_all"):
                    rows = db.fetch_all(sql, params) or []
                elif hasattr(db, "query"):
                    rows = db.query(sql, params) or []
                else:
                    conn, cur = db.get_conn_cursor()
                    cur.execute(sql, params)
                    rows = cur.fetchall()
            except Exception:
                res = db.execute(sql, params)
                if isinstance(res, list):
                    rows = res
                else:
                    rows = []

            # limpa treeview
            for i in self.tree.get_children():
                self.tree.delete(i)

            # redefine colunas do treeview COM ESTILO CORRETO
            self.tree.configure(columns=colunas, show="headings", style="Custom.Treeview")
            for c in colunas:
                texto = self.nomes_amigaveis.get(c, c.replace("_", " ").title())
                largura = 110 if c in (
                    "descricao",
                    "fornecedor",
                    "composicao",
                    "observacoes",
                ) else 90
                self.tree.heading(c, text=texto)
                self.tree.column(c, width=largura, anchor="w")  # Mudei para "w" como na entrada

            # insere dados
            for row in rows:
                if isinstance(row, dict):
                    valores = [row.get(c, "") for c in colunas]
                elif isinstance(row, (list, tuple)):
                    valores = row
                else:
                    continue

                # formata números
                valores_fmt = []
                for c, v in zip(colunas, valores):
                    if c in ("metros", "kilos"):
                        valores_fmt.append(self.formatar_valor_tree(v, c))
                    else:
                        valores_fmt.append(v)
                self.tree.insert("", "end", values=valores_fmt)

            self.status_label.configure(
                text=f"{len(rows)} registro(s) carregado(s) de {tabela}.",
                text_color=self.cor_sucesso,
            )

        except Exception as e:
            self.status_label.configure(
                text=f"Erro ao carregar estoque: {e}",
                text_color=self.cor_alerta,
            )

    def atualizar_interface(self, tipo):
        # Atualiza o tema da treeview antes de criar os campos
        self.configurar_treeview_theme()
        if tipo not in self.tipos:
            return
        self.limpar_campos()
        self.limpar_pesquisa()
        self.configurar_campos_saida(tipo)

    def configurar_treeview_theme(self):
        """Configura as cores da Treeview baseado no tema atual - MESMO PADRÃO DA ENTRADA"""
        self.style = ttk.Style()
        self.style.theme_use('default')

        tema_atual = ctk.get_appearance_mode()

        if tema_atual == "Dark":
            # TEMA ESCURO - MESMO PADRÃO DA ENTRADA
            cor_fundo = self.cor_secundaria
            cor_texto = "white"
            cor_campo = self.cor_secundaria
            cor_borda = self.cor_borda
            cor_selecao = self.cor_primaria
        else:
            # TEMA CLARO - MESMO PADRÃO DA ENTRADA
            cor_fundo = "#f0f0f0"
            cor_texto = "black"
            cor_campo = "#f0f0f0"
            cor_borda = "#cccccc"
            cor_selecao = self.cor_primaria

        # CONFIGURAÇÃO IDÊNTICA À PÁGINA DE ENTRADA
        self.style.configure("Custom.Treeview",
                             background=cor_fundo,
                             foreground=cor_texto,
                             fieldbackground=cor_campo,
                             borderwidth=0,
                             highlightthickness=0)

        # CABEÇALHO COM COR PRIMÁRIA
        self.style.configure("Custom.Treeview.Heading",
                             background=self.cor_primaria,
                             foreground=cor_texto,
                             relief="flat",
                             borderwidth=1)

        # MAPA DE SELEÇÃO IDÊNTICO
        self.style.map('Custom.Treeview',
                       background=[('selected', cor_selecao)],
                       foreground=[('selected', "white")])

    def configurar_campos_saida(self, tipo):
        # Atualiza cores baseado no tema atual
        self.obter_cores_por_tema(self.sistema)

        for widget in self.campos_frame.winfo_children():
            widget.destroy()
        self.entries = {}

        campos = ["Metros", "Kilos"] if tipo == "Tecidos" else ["Quantidade"]
        for campo in campos:
            frame = ctk.CTkFrame(self.campos_frame, fg_color=self.cor_fundo)
            frame.pack(fill="x", padx=5, pady=3)

            ctk.CTkLabel(
                frame,
                text=f"{campo}:",
                width=150,
                text_color=self.cor_texto,
            ).pack(side="left", padx=5)

            entry = ctk.CTkEntry(
                frame,
                placeholder_text="0,00" if campo in ["Metros", "Kilos"] else "0",
                fg_color=self.cor_terciaria,
                border_color=self.cor_borda,
                text_color=self.cor_texto_entry,
                placeholder_text_color=self.cor_placeholder,
            )
            entry.pack(side="left", fill="x", expand=True)
            self.entries[campo.lower()] = entry

    def filtrar_produtos(self, event=None):
        termo = (self.entry_produto.get() or "").strip()
        self.carregar_estoque(self.tipo_var.get(), filtro_termo=termo)

    def limpar_pesquisa(self):
        self.entry_produto.delete(0, "end")
        self.carregar_estoque(self.tipo_var.get())

    def selecionar_para_saida(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return

        item = self.tree.item(item_id)
        valores = item["values"]
        colunas = self.tree["columns"]

        try:
            dados_item = dict(zip(colunas, valores))
            id_real = dados_item.get("id", item_id)
            descricao = dados_item.get("descricao", "Produto")
            codigo = dados_item.get("codigo", "")

            self.entry_produto.delete(0, "end")
            self.entry_produto.insert(
                0, f"{descricao} ({codigo})" if codigo else descricao
            )

            self.id_selecionado = id_real
            self.status_label.configure(
                text=f"Produto selecionado: {descricao}",
                text_color=self.cor_sucesso,
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao selecionar produto: {e}")

    def registrar_saida(self):
        """
        Faz a baixa do item selecionado:
          - Tecidos: baixa metros e/ou kilos (ambos opcionais, pelo menos um precisa ser >0)
          - Demais: baixa quantidade (inteiro >0)
        Garante:
          - SELECT ... FOR UPDATE (evita corrida)
          - Não deixa saldo negativo
          - Mensagem com saldo após a baixa
        """
        if not hasattr(self, "id_selecionado") or not self.id_selecionado:
            messagebox.showwarning(
                "Aviso", "Selecione um produto da lista primeiro!"
            )
            return

        tipo = self.tipo_var.get()
        tabela = self._tabela_por_tipo(tipo)
        dados_saida = {
            k: (v.get().strip() if v else "") for k, v in self.entries.items()
        }

        try:
            with db.get_conn_cursor() as (conn, cur):
                if tipo == "Tecidos":
                    # Bloqueia linha para baixa segura
                    cur.execute(
                        """
                        SELECT id, descricao, codigo, metros, kilos
                        FROM estoque_tecidos
                        WHERE id = %s
                        FOR UPDATE
                        """,
                        (self.id_selecionado,),
                    )
                    produto = cur.fetchone()
                    if not produto:
                        messagebox.showerror("Erro", "Produto não encontrado!")
                        return

                    metros_atual = float(produto.get("metros", 0) or 0)
                    kilos_atual = float(produto.get("kilos", 0) or 0)
                    v_metros = self._to_float(dados_saida.get("metros"))
                    v_kilos = self._to_float(dados_saida.get("kilos"))

                    # pelo menos um informado e >0
                    if (v_metros is None or v_metros <= 0) and (
                        v_kilos is None or v_kilos <= 0
                    ):
                        messagebox.showwarning(
                            "Aviso",
                            "Informe Metros e/ou Kilos maiores que zero para a baixa.",
                        )
                        return

                    # valida saldo
                    if v_metros and v_metros > metros_atual:
                        messagebox.showwarning(
                            "Estoque insuficiente",
                            f"Metros disponíveis: {self.formatar_valor_tree(metros_atual, 'metros')}",
                        )
                        return
                    if v_kilos and v_kilos > kilos_atual:
                        messagebox.showwarning(
                            "Estoque insuficiente",
                            f"Kilos disponíveis: {self.formatar_valor_tree(kilos_atual, 'kilos')}",
                        )
                        return

                    updates, params = [], []
                    if v_metros and v_metros > 0:
                        updates.append("metros = GREATEST(metros - %s, 0)")
                        params.append(v_metros)
                    if v_kilos and v_kilos > 0:
                        updates.append("kilos = GREATEST(kilos - %s, 0)")
                        params.append(v_kilos)

                    params.append(self.id_selecionado)
                    cur.execute(
                        f"UPDATE estoque_tecidos SET {', '.join(updates)} "
                        f"WHERE id = %s RETURNING metros, kilos",
                        params,
                    )
                    saldo = cur.fetchone() or {}
                    msg = (
                        "✅ Saída registrada!\n"
                        f"Saldo: {self.formatar_valor_tree(float(saldo.get('metros', 0) or 0), 'metros')} m"
                        f" / {self.formatar_valor_tree(float(saldo.get('kilos', 0) or 0), 'kilos')} kg"
                    )

                else:
                    # Demais tipos: baixa quantidade inteira
                    cur.execute(
                        f"""
                        SELECT id, descricao, codigo, quantidade
                        FROM {tabela}
                        WHERE id = %s
                        FOR UPDATE
                        """,
                        (self.id_selecionado,),
                    )
                    produto = cur.fetchone()
                    if not produto:
                        messagebox.showerror("Erro", "Produto não encontrado!")
                        return

                    qtd_atual = int(produto.get("quantidade", 0) or 0)
                    qnt_saida = self._to_int(dados_saida.get("quantidade"))

                    if qnt_saida is None or qnt_saida <= 0:
                        messagebox.showwarning(
                            "Aviso", "Informe uma quantidade válida (> 0)!"
                        )
                        return
                    if qnt_saida > qtd_atual:
                        messagebox.showwarning(
                            "Estoque insuficiente", f"Disponível: {qtd_atual}"
                        )
                        return

                    cur.execute(
                        f"UPDATE {tabela} "
                        f"SET quantidade = GREATEST(quantidade - %s, 0) "
                        f"WHERE id = %s RETURNING quantidade",
                        (qnt_saida, self.id_selecionado),
                    )
                    saldo = cur.fetchone() or {}
                    msg = (
                        "✅ Saída registrada!\n"
                        f"Saldo atual: {int(saldo.get('quantidade', 0) or 0)}"
                    )

                # sucesso
                messagebox.showinfo("Sucesso", msg)

            # refresh UI
            self.carregar_estoque(tipo)
            self.limpar_campos()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao registrar saída: {e}")

    def limpar_campos(self):
        for entry in self.entries.values():
            entry.delete(0, "end")
        if hasattr(self, "id_selecionado"):
            del self.id_selecionado
        self.status_label.configure(
            text="Campos limpos",
            text_color=self.cor_texto,
        )


if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1000x700")
    app.title("Sistema de Saída de Estoque")
    SaidaEstoqueApp(app)
    app.mainloop()