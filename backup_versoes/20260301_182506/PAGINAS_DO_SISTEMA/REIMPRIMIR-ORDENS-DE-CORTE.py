# -*- coding: utf-8 -*-
"""
ORDENS_CORTE_IMPRESSAO.py
Página de listagem e impressão de Ordens de Corte
Usa o mesmo padrão de banco, temas e estilo da NOVA_ORDEM.py
"""

from PAGINAS_DO_SISTEMA import TEMAS
import os
import logging
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PAGINAS_DO_SISTEMA.NOVA_ORDEM import OrdemCorte
import json
from datetime import date, datetime


# ===================== Configuração de logger =====================
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ===================== Acesso ao PostgreSQL =====================
try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
    try:
        from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import PASTA_ORDENS_CORTE
    except Exception:
        PASTA_ORDENS_CORTE = None
except Exception as e:
    print(f"⚠️ Módulo de banco não disponível: {e}")

    def get_conn():
        raise RuntimeError("Módulo BANCO_DE_DADOS_PG indisponível")

    def get_schema():
        return "opera"

    def require_ready(essentials=None):
        return False, "Módulo de banco de dados não disponível"

    PASTA_ORDENS_CORTE = None

if not PASTA_ORDENS_CORTE:
    BASE_DB_DIR = os.path.join("../src", "BANCO DE DADOS", "ORDENS_CORTE")
    os.makedirs(BASE_DB_DIR, exist_ok=True)
    PASTA_ORDENS_CORTE = BASE_DB_DIR


def _exec_all(query: str, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        schema = get_schema()
        try:
            cur.execute(f"SET LOCAL search_path = {schema}")
        except Exception:
            pass
        cur.execute(query, params)
        rows = cur.fetchall()
        return rows
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _exec_row(query: str, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        schema = get_schema()
        try:
            cur.execute(f"SET LOCAL search_path = {schema}")
        except Exception:
            pass
        cur.execute(query, params)
        row = cur.fetchone()
        return row
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _exec_write(query: str, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        schema = get_schema()
        try:
            cur.execute(f"SET LOCAL search_path = {schema}")
        except Exception:
            pass
        cur.execute(query, params)
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass


class OrdensCorteImpressao(ctk.CTkFrame):
    """
    Página: ORDENS DE CORTE – IMPRESSÃO
    Lista todas as ordens da tabela ordem_corte_ficha e permite reimprimir
    com pré-visualização interna.
    """

    def __init__(self, master, *args, **kwargs):
        # Detectar sistema / app para pegar tema
        sistema_kw = kwargs.pop("sistema", None)
        app_kw = kwargs.pop("app", None)
        sistema = sistema_kw or app_kw

        if sistema is None:
            sistema = (
                kwargs.get("controller")
                or kwargs.get("ctx")
                or kwargs.get("root")
                or kwargs.get("main")
            )

        tema_posicional = None
        if args:
            primeiro = args[0]
            if isinstance(primeiro, dict):
                tema_posicional = primeiro
            else:
                if sistema is None:
                    sistema = primeiro

        self.sistema = sistema

        self.usuario_id = None
        self.usuario_nome = None
        if self.sistema is not None:
            self.usuario_id = getattr(self.sistema, "usuario_id", None)
            self.usuario_nome = getattr(self.sistema, "usuario_nome", None)

        # Cores do tema (mesma lógica da NOVA_ORDEM.py)
        if self.sistema is not None:
            self.cor_fundo = getattr(self.sistema, "cor_fundo", "#DEDEDE")
            self.cor_texto = getattr(self.sistema, "cor_texto", "#1A1A1A")
            self.cor_primaria = getattr(self.sistema, "cor_primaria", "#C9C9C9")
            self.cor_borda = getattr(self.sistema, "cor_borda", "#A3A3A3")
            self.cor_hover = getattr(self.sistema, "cor_hover", "#808080")
            self.cor_sucesso = getattr(self.sistema, "cor_sucesso", "#2E9E6E")
            self.cor_alerta = getattr(self.sistema, "cor_alerta", "#D63854")
            self.cor_destaque = getattr(self.sistema, "cor_destaque", "#636363")
            self.cor_selecao = getattr(self.sistema, "cor_selecao", "#008000")
            self.cor_secundaria = getattr(self.sistema, "cor_secundaria", self.cor_primaria)
            self.cor_terciaria = getattr(self.sistema, "cor_terciaria", self.cor_primaria)
            self.cor_imprimir = getattr(self.sistema, "cor_imprimir", self.cor_terciaria)
        else:
            tema_local = tema_posicional if isinstance(tema_posicional, dict) else {}
            self.cor_fundo = tema_local.get("fundo", "#DEDEDE")
            self.cor_texto = tema_local.get("texto", "#1A1A1A")
            self.cor_primaria = tema_local.get("primaria", "#C9C9C9")
            self.cor_borda = tema_local.get("borda", "#A3A3A3")
            self.cor_hover = tema_local.get("hover", "#808080")
            self.cor_sucesso = tema_local.get("sucesso", "#2E9E6E")
            self.cor_alerta = tema_local.get("alerta", "#D63854")
            self.cor_destaque = tema_local.get("destaque", "#636363")
            self.cor_selecao = tema_local.get("selecao", "#008000")
            self.cor_secundaria = tema_local.get("secundaria", self.cor_primaria)
            self.cor_terciaria = tema_local.get("terciaria", self.cor_primaria)
            self.cor_imprimir = tema_local.get("imprimir", self.cor_terciaria)

        self.tema = {
            "fundo": self.cor_fundo,
            "texto": self.cor_texto,
            "primaria": self.cor_primaria,
            "borda": self.cor_borda,
            "hover": self.cor_hover,
            "sucesso": self.cor_sucesso,
            "alerta": self.cor_alerta,
            "destaque": self.cor_destaque,
            "selecao": self.cor_selecao,
            "secundaria": self.cor_secundaria,
            "terciaria": self.cor_terciaria,
            "imprimir": self.cor_imprimir,
        }

        super().__init__(master, fg_color=self.cor_fundo, *args, **kwargs)

        # Mapeamento de colunas do banco
        self.col_id = None
        self.col_codigo = None
        self.col_descricao = None
        self.col_data_final = None
        self.col_quantidade = None
        self.col_impresso = None

        self._logical_cols = []
        self._select_cols = []

        self._configurar_colunas_banco()
        self._build_ui()
        self.atualizar_lista()

    # ----------------------------------------------------------
    #   Configuração de colunas da tabela ordem_corte_ficha
    # ----------------------------------------------------------
    def _configurar_colunas_banco(self):
        try:
            rows = _exec_all(
                """
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = current_schema()
                   AND table_name = 'ordem_corte_ficha'
                """
            )
        except Exception as e:
            logger.error(f"Erro ao ler colunas de ordem_corte_ficha: {e}")
            messagebox.showerror(
                "Erro",
                "Falha ao ler colunas da tabela ordem_corte_ficha.\n"
                "Verifique a conexão com o banco de dados."
            )
            rows = []

        cols = [r[0].lower() for r in rows] if rows else []

        def has(col_name: str) -> bool:
            return col_name.lower() in cols

        # Colunas principais
        if has("id"):
            self.col_id = "id"
        if has("codigo_modelo"):
            self.col_codigo = "codigo_modelo"
        elif has("codigo"):
            self.col_codigo = "codigo"
        if has("descricao_modelo"):
            self.col_descricao = "descricao_modelo"
        elif has("descricao"):
            self.col_descricao = "descricao"
        if has("data_final"):
            self.col_data_final = "data_final"
        if has("quantidade_desejada"):
            self.col_quantidade = "quantidade_desejada"
        elif has("quantidade"):
            self.col_quantidade = "quantidade"

        # Coluna opcional para saber se já foi impressa
        if has("impresso"):
            self.col_impresso = "impresso"
        elif has("foi_impresso"):
            self.col_impresso = "foi_impresso"

        # Definir ordem lógica / SELECT
        logical_cols = []
        select_cols = []

        if self.col_id:
            logical_cols.append("id")
            select_cols.append(self.col_id)
        if self.col_codigo:
            logical_cols.append("codigo")
            select_cols.append(self.col_codigo)
        if self.col_descricao:
            logical_cols.append("descricao")
            select_cols.append(self.col_descricao)
        if self.col_data_final:
            logical_cols.append("data_final")
            select_cols.append(self.col_data_final)
        if self.col_quantidade:
            logical_cols.append("quantidade")
            select_cols.append(self.col_quantidade)
        if self.col_impresso:
            logical_cols.append("impresso")
            select_cols.append(self.col_impresso)

        self._logical_cols = logical_cols
        self._select_cols = select_cols

        logger.info(f"Colunas lógicas para ORDENS_DE_CORTE_IMPRESSAO: {self._logical_cols}")
        if not self._select_cols:
            logger.warning("Nenhuma coluna configurada para seleção em ordem_corte_ficha.")

    # ----------------------------------------------------------
    #   Construção da interface
    # ----------------------------------------------------------
    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Cabeçalho
        header = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header.grid_columnconfigure(0, weight=1)

        titulo = ctk.CTkLabel(
            header,
            text="REIMPRIMIR-ORDENS",
            font=("Arial", 18, "bold"),
            text_color=self.cor_texto,
        )
        titulo.grid(row=0, column=0, sticky="w")

        # Filtros
        filtros = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        filtros.grid(row=1, column=0, sticky="ew", padx=10)
        for i in range(5):
            filtros.grid_columnconfigure(i, weight=0)
        filtros.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(
            filtros, text="Código:", text_color=self.cor_texto, font=("Arial", 12)
        ).grid(row=0, column=0, padx=(0, 4), pady=4, sticky="w")
        self.filtro_codigo = ctk.CTkEntry(
            filtros, width=120, fg_color="white", text_color="black"
        )
        self.filtro_codigo.grid(row=0, column=1, padx=(0, 10), pady=4, sticky="w")

        ctk.CTkLabel(
            filtros, text="Descrição:", text_color=self.cor_texto, font=("Arial", 12)
        ).grid(row=0, column=2, padx=(0, 4), pady=4, sticky="w")
        self.filtro_descricao = ctk.CTkEntry(
            filtros, width=260, fg_color="white", text_color="black"
        )
        self.filtro_descricao.grid(row=0, column=3, padx=(0, 10), pady=4, sticky="w")

        self.var_apenas_nao_impressas = tk.BooleanVar(value=False)
        if self.col_impresso:
            self.chk_nao_impressas = ctk.CTkCheckBox(
                filtros,
                text="Somente ordens não impressas",
                variable=self.var_apenas_nao_impressas,
                fg_color=self.cor_selecao,
                hover_color=self.cor_hover,
                border_color=self.cor_borda,
                text_color=self.cor_texto,
                command=self.atualizar_lista,
            )
            self.chk_nao_impressas.grid(row=0, column=4, padx=(0, 10), pady=4, sticky="w")
        else:
            self.chk_nao_impressas = None

        btn_buscar = ctk.CTkButton(
            filtros,
            text="Buscar",
            command=self.atualizar_lista,
            fg_color=self.cor_selecao,
            hover_color=self.cor_hover,
            text_color="white",
            width=90,
        )
        btn_buscar.grid(row=0, column=5, padx=(0, 4), pady=4, sticky="e")

        btn_limpar = ctk.CTkButton(
            filtros,
            text="Limpar",
            command=self._limpar_filtros,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            width=90,
        )
        btn_limpar.grid(row=0, column=6, padx=(4, 0), pady=4, sticky="e")

        # Tabela
        frame_tabela = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        frame_tabela.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 5))
        frame_tabela.grid_rowconfigure(0, weight=1)
        frame_tabela.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Treeview",
            background="white",
            foreground="black",
            rowheight=24,
            fieldbackground="white",
        )
        style.configure(
            "Treeview.Heading",
            background=self.cor_primaria,
            foreground=self.cor_texto,
            font=("Arial", 11, "bold"),
        )
        style.map("Treeview", background=[("selected", self.cor_selecao)])

        self.tree = ttk.Treeview(
            frame_tabela,
            columns=self._logical_cols,
            show="headings",
            selectmode="browse",
        )
        vsb = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Headings amigáveis
        for col in self._logical_cols:
            if col == "id":
                texto = "ID"
                largura = 60
            elif col == "codigo":
                texto = "Código"
                largura = 100
            elif col == "descricao":
                texto = "Descrição"
                largura = 260
            elif col == "data_final":
                texto = "Data Final"
                largura = 120
            elif col == "quantidade":
                texto = "Quantidade"
                largura = 110
            elif col == "impresso":
                texto = "Impresso?"
                largura = 90
            else:
                texto = col
                largura = 100

            self.tree.heading(col, text=texto)
            self.tree.column(col, width=largura, anchor="center")

        self.tree.bind("<Double-1>", self._on_double_click)

        # Rodapé / Botões
        rodape = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        rodape.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
        rodape.grid_columnconfigure(0, weight=1)
        rodape.grid_columnconfigure(3, weight=0)

        self.lbl_total = ctk.CTkLabel(
            rodape,
            text="0 ordens encontradas",
            text_color=self.cor_texto,
            font=("Arial", 11),
        )
        self.lbl_total.grid(row=0, column=0, sticky="w")

        btn_imprimir = ctk.CTkButton(
            rodape,
            text="Imprimir ordem selecionada",
            command=self.imprimir_selecionada,
            fg_color=self.cor_imprimir,
            hover_color=self.cor_hover,
            text_color="white",
            width=220,
        )
        btn_imprimir.grid(row=0, column=1, padx=8, pady=4, sticky="e")

        btn_atualizar = ctk.CTkButton(
            rodape,
            text="Atualizar lista",
            command=self.atualizar_lista,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            width=150,
        )
        btn_atualizar.grid(row=0, column=2, padx=8, pady=4, sticky="e")

        btn_fechar = ctk.CTkButton(
            rodape,
            text="Fechar",
            command=self._fechar,
            fg_color=self.cor_alerta,
            hover_color=self.cor_hover,
            text_color="white",
            width=120,
        )
        btn_fechar.grid(row=0, column=3, padx=0, pady=4, sticky="e")

    # ----------------------------------------------------------
    #   Ações da interface
    # ----------------------------------------------------------
    def _limpar_filtros(self):
        self.filtro_codigo.delete(0, "end")
        self.filtro_descricao.delete(0, "end")
        if self.chk_nao_impressas is not None:
            self.var_apenas_nao_impressas.set(False)
        self.atualizar_lista()

    def _limpar_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _on_double_click(self, event=None):
        # Duplo clique também abre a pré-visualização
        self.imprimir_selecionada()

    def _fechar(self):
        # Se estiver dentro de uma janela Toplevel, fecha a janela.
        toplevel = self.winfo_toplevel()
        try:
            toplevel.destroy()
        except Exception:
            self.master.destroy()

    # ----------------------------------------------------------
    #   Carregamento de ordens
    # ----------------------------------------------------------
    def atualizar_lista(self):
        if not self._select_cols:
            return

        codigo_filtro = self.filtro_codigo.get().strip()
        desc_filtro = self.filtro_descricao.get().strip()
        apenas_nao_imp = bool(self.var_apenas_nao_impressas.get()) and bool(self.col_impresso)

        sql = "SELECT " + ", ".join(self._select_cols) + " FROM ordem_corte_ficha"
        where = []
        params = []

        if self.col_codigo and codigo_filtro:
            where.append(f"{self.col_codigo} ILIKE %s")
            params.append(f"%{codigo_filtro}%")

        if self.col_descricao and desc_filtro:
            where.append(f"{self.col_descricao} ILIKE %s")
            params.append(f"%{desc_filtro}%")

        if apenas_nao_imp and self.col_impresso:
            where.append(f"({self.col_impresso} = FALSE OR {self.col_impresso} IS NULL)")

        if where:
            sql += " WHERE " + " AND ".join(where)

        # Ordenação
        if self.col_data_final:
            sql += f" ORDER BY {self.col_data_final} DESC"
            if self.col_id:
                sql += f", {self.col_id} DESC"
        elif self.col_id:
            sql += f" ORDER BY {self.col_id} DESC"

        try:
            rows = _exec_all(sql, tuple(params))
        except Exception as e:
            logger.error(f"Erro ao carregar ordens de corte: {e}")
            messagebox.showerror("Erro", f"Falha ao carregar ordens de corte:\n{e}")
            return

        self._limpar_tabela()

        total = 0
        for row in rows:
            dados = dict(zip(self._select_cols, row))
            # Recria o dicionário no padrão _logical_cols
            dados_log = {}
            for lcol, scol in zip(self._logical_cols, self._select_cols):
                dados_log[lcol] = dados.get(scol, "")

            # Formatar data
            if "data_final" in dados_log and isinstance(dados_log["data_final"], datetime):
                dados_log["data_final"] = dados_log["data_final"].strftime("%d/%m/%Y")

            # Formatar boolean
            if "impresso" in dados_log:
                val = dados_log["impresso"]
                if val is None:
                    txt_imp = "Não"
                elif isinstance(val, bool):
                    txt_imp = "Sim" if val else "Não"
                else:
                    txt_imp = str(val)
                dados_log["impresso"] = txt_imp

            values = [dados_log.get(col, "") for col in self._logical_cols]
            iid = dados_log.get("id", None)
            self.tree.insert("", "end", iid=str(iid) if iid is not None else None, values=values)
            total += 1

        self.lbl_total.configure(text=f"{total} ordens encontradas")

    # ----------------------------------------------------------
    #   Impressão / Pré-visualização
    # ----------------------------------------------------------
    def imprimir_selecionada(self):
        """Imprime a ordem selecionada usando o MESMO layout de PDF da NOVA_ORDEM."""
        try:
            item = self.tree.focus()
            if not item:
                messagebox.showwarning("Seleção necessária", "Selecione uma ordem na lista para imprimir.")
                return

            valores = self.tree.item(item, "values")
            if not valores:
                messagebox.showerror("Erro", "Não foi possível obter os dados da linha selecionada.")
                return

            # Supondo que a 1ª coluna é o ID da ordem (como montamos o TreeView)
            try:
                ordem_id = int(valores[0])
            except Exception:
                messagebox.showerror("Erro", "ID da ordem inválido na tabela.")
                return

            dados = self._buscar_dados_ordem_completos(ordem_id)
            if not dados:
                messagebox.showerror("Erro", "Não foi possível carregar os dados completos da ordem.")
                return

            # Abre uma janelinha de confirmação (opcional, mas útil)
            if not messagebox.askyesno(
                    "Imprimir Ordem",
                    f"Deseja imprimir a ordem {dados.get('codigo', dados.get('codigo_modelo', ''))} "
                    f"no layout padrão de Ordem de Corte?"
            ):
                return

            self._imprimir_com_layout_nova_ordem(dados)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao preparar impressão da ordem:\n{e}")

    def _abrir_preview_ordem(self, dados: dict):
        """
        Abre uma janela interna (CTkToplevel) para pré-visualizar
        a ordem de corte antes de gerar o PDF.
        """
        top = ctk.CTkToplevel(self)
        top.title(f"Pré-visualização da Ordem – {dados.get('codigo', '')}")
        top.geometry("700x400")
        top.transient(self.winfo_toplevel())
        top.grab_set()

        frame = ctk.CTkFrame(top, fg_color=self.cor_fundo)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Título
        lbl_titulo = ctk.CTkLabel(
            frame,
            text="ORDEM DE CORTE – PRÉ-VISUALIZAÇÃO",
            font=("Arial", 18, "bold"),
            text_color=self.cor_texto,
        )
        lbl_titulo.pack(anchor="w", pady=(0, 10))

        # Bloco de informações
        bloco = ctk.CTkFrame(frame, fg_color=self.cor_primaria, corner_radius=10)
        bloco.pack(fill="x", pady=(0, 10))

        # Linhas de texto
        info_textos = []

        info_textos.append(f"Código: {dados.get('codigo', '')}")
        info_textos.append(f"Descrição: {dados.get('descricao', '')}")

        if "data_final" in dados and dados.get("data_final"):
            info_textos.append(f"Data final: {dados.get('data_final')}")

        if "quantidade" in dados and dados.get("quantidade"):
            info_textos.append(f"Quantidade: {dados.get('quantidade')}")

        if "impresso" in dados and dados.get("impresso") not in ("", None):
            info_textos.append(f"Impresso?: {dados.get('impresso')}")

        for txt in info_textos:
            lbl = ctk.CTkLabel(
                bloco,
                text=txt,
                font=("Arial", 13),
                text_color=self.cor_texto,
                anchor="w",
                justify="left",
            )
            lbl.pack(fill="x", padx=10, pady=2)

        # Rodapé com botões
        rodape = ctk.CTkFrame(frame, fg_color=self.cor_fundo)
        rodape.pack(fill="x", pady=(10, 0))
        rodape.grid_columnconfigure(0, weight=1)
        rodape.grid_columnconfigure(2, weight=0)

        lbl_hint = ctk.CTkLabel(
            rodape,
            text="Conferir os dados acima. Clique em 'Gerar PDF' para criar o arquivo de impressão.",
            font=("Arial", 11),
            text_color=self.cor_texto,
        )
        lbl_hint.grid(row=0, column=0, sticky="w", padx=2, pady=4)

        btn_gerar = ctk.CTkButton(
            rodape,
            text="Gerar PDF (não abre navegador)",
            fg_color=self.cor_imprimir,
            hover_color=self.cor_hover,
            text_color="white",
            command=lambda: self._gerar_pdf_e_marcar_impresso(dados, top),
            width=220,
        )
        btn_gerar.grid(row=0, column=1, padx=8, pady=4, sticky="e")

        btn_fechar = ctk.CTkButton(
            rodape,
            text="Fechar",
            fg_color=self.cor_alerta,
            hover_color=self.cor_hover,
            text_color="white",
            command=top.destroy,
            width=130,
        )
        btn_fechar.grid(row=0, column=2, padx=0, pady=4, sticky="e")

    def _gerar_pdf_e_marcar_impresso(self, dados: dict, janela_preview=None):
        """
        Gera o PDF da ordem e marca como impressa (se existir coluna),
        mas NÃO abre o navegador/visualizador. Apenas avisa o caminho.
        """
        try:
            caminho_pdf = self._gerar_pdf_ordem(dados)
        except Exception as e:
            logger.error(f"Erro ao gerar PDF da ordem: {e}")
            messagebox.showerror("Erro", f"Falha ao gerar PDF da ordem:\n{e}")
            return

        # Atualiza coluna 'impresso' no banco, se existir
        ordem_id = dados.get("id")
        if self.col_impresso and self.col_id and ordem_id not in (None, ""):
            try:
                _exec_write(
                    f"UPDATE ordem_corte_ficha SET {self.col_impresso} = TRUE WHERE {self.col_id} = %s",
                    (int(ordem_id),),
                )
            except Exception as e:
                logger.error(f"Falha ao marcar ordem como impressa: {e}")

        # Se o filtro de "não impressas" estiver ativo, recarrega a lista
        if self.var_apenas_nao_impressas.get():
            self.atualizar_lista()

        # Fecha a janela de pré-visualização, se ainda estiver aberta
        if janela_preview is not None:
            try:
                janela_preview.destroy()
            except Exception:
                pass

        messagebox.showinfo(
            "PDF gerado",
            f"PDF da ordem foi gerado com sucesso em:\n\n{caminho_pdf}\n\n"
            "Ele não foi aberto automaticamente.\n"
            "Você pode abrir esse arquivo diretamente pela pasta de ordens."
        )

    def _buscar_dados_ordem_completos(self, ordem_id: int):
        """
        Busca TODOS os dados relevantes da tabela ordem_corte_ficha para montar
        o PDF com o mesmo layout da NOVA_ORDEM.
        """
        try:
            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()

            cur.execute(f"SET LOCAL search_path = {schema}")

            # Pegamos todas as colunas para ter liberdade de montar o dicionário
            cur.execute("SELECT * FROM ordem_corte_ficha WHERE id = %s", (ordem_id,))
            row = cur.fetchone()
            if not row:
                return None

            colnames = [desc[0] for desc in cur.description]
            dados = {nome: valor for nome, valor in zip(colnames, row)}

            cur.close()
            conn.close()
            return dados

        except Exception as e:
            try:
                conn.close()
            except Exception:
                pass
            messagebox.showerror("Erro", f"Erro ao buscar dados da ordem:\n{e}")
            return None

    def _imprimir_com_layout_nova_ordem(self, dados: dict):
        """
        Usa a classe OrdemCorte de NOVA_ORDEM.py para gerar o PDF
        com o MESMO layout de impressão, preenchendo os campos a partir
        dos dados salvos em ordem_corte_ficha.
        """
        try:
            # Janela oculta só para gerar o PDF
            dummy = ctk.CTk()
            dummy.withdraw()

            # Passa o mesmo 'sistema' para manter o tema
            oc = OrdemCorte(dummy, sistema=getattr(self, "sistema", None))

            # ---------- CAMPOS BÁSICOS ----------
            # CÓDIGO / MODELO
            codigo = (
                    dados.get("codigo_modelo")
                    or dados.get("codigo")
                    or ""
            )
            descricao = (
                    dados.get("descricao_modelo")
                    or dados.get("descricao")
                    or dados.get("modelo")
                    or ""
            )

            oc.codigo_entry.delete(0, "end")
            oc.codigo_entry.insert(0, str(codigo))

            oc.modelo_entry.delete(0, "end")
            oc.modelo_entry.insert(0, str(descricao))

            # CORTADOR / AUXILIAR
            cortador = dados.get("cortador") or dados.get("nome_cortador") or ""
            auxiliar = dados.get("auxiliar") or dados.get("nome_auxiliar") or ""

            oc.cortador_entry.delete(0, "end")
            oc.cortador_entry.insert(0, str(cortador))

            oc.auxiliar_entry.delete(0, "end")
            oc.auxiliar_entry.insert(0, str(auxiliar))

            # DATA FINAL
            data_final = dados.get("data_final")
            if isinstance(data_final, (date, datetime)):
                data_str = data_final.strftime("%d/%m/%Y")
            elif data_final:
                # Se veio como string, só garante o formato legível
                data_str = str(data_final)
            else:
                data_str = ""

            oc.data_final_entry.delete(0, "end")
            oc.data_final_entry.insert(0, data_str)

            # ---------- QUANTIDADE / PRAZOS ----------
            quantidade = (
                    dados.get("quantidade_desejada")
                    or dados.get("quantidade")
                    or dados.get("total_pecas")
                    or 0
            )

            oc.quantidade_entry.delete(0, "end")
            oc.quantidade_entry.insert(0, str(int(quantidade) if quantidade else ""))

            # dias_estimados + horas_estimadas (podem ter sido gravados separadamente)
            dias_estimados = dados.get("dias_estimados") or 0
            horas_estimadas = dados.get("horas_estimadas") or 0

            # Se o sistema gravou o total em dias (float) e não separou, tenta decompor
            if dias_estimados and not horas_estimadas:
                try:
                    total_dias = float(dias_estimados)
                    dias_int = int(total_dias)
                    horas_float = (total_dias - dias_int) * 24
                    horas_estimadas = round(horas_float, 2)
                    dias_estimados = dias_int
                except Exception:
                    pass

            oc.dias_estimados_entry.delete(0, "end")
            if dias_estimados:
                oc.dias_estimados_entry.insert(0, str(int(dias_estimados)))

            oc.horas_estimadas_entry.delete(0, "end")
            if horas_estimadas:
                # Se for algo tipo 1.5, mostra 1.5 mesmo
                try:
                    h = float(horas_estimadas)
                    if h.is_integer():
                        oc.horas_estimadas_entry.insert(0, str(int(h)))
                    else:
                        oc.horas_estimadas_entry.insert(0, f"{h:.2f}")
                except Exception:
                    oc.horas_estimadas_entry.insert(0, str(horas_estimadas))

            # ---------- PORCENTAGENS / GRADE ----------
            porcentagens_raw = (
                    dados.get("porcentagens")
                    or dados.get("grade_json")
                    or dados.get("grade")
            )

            if porcentagens_raw:
                try:
                    if isinstance(porcentagens_raw, str):
                        porcentagens = json.loads(porcentagens_raw)
                    else:
                        porcentagens = dict(porcentagens_raw)
                except Exception:
                    porcentagens = {}
            else:
                porcentagens = {}

            for i in range(1, 8 + 1):
                campo = oc.campos_grade.get(f"porcent_{i}")
                if not campo:
                    continue
                valor = (
                        porcentagens.get(f"porcent_{i}")
                        or porcentagens.get(str(i))
                        or 0
                )
                campo.delete(0, "end")
                try:
                    # Usa a mesma lógica de formatação da página
                    valor_formatado = oc.formatar_para_inteiro_se_possivel(valor)
                    campo.insert(0, valor_formatado)
                except Exception:
                    campo.insert(0, str(valor))

            # CONSUMO PEÇA
            consumo_peca = dados.get("consumo_peca") or dados.get("consumo")
            if consumo_peca is not None:
                campo_consumo = oc.campos_grade.get("consumo_peca")
                if campo_consumo:
                    campo_consumo.delete(0, "end")
                    try:
                        num = float(consumo_peca)
                        if num.is_integer():
                            campo_consumo.insert(0, str(int(num)))
                        else:
                            # Você já ajustou para aceitar vírgula, então converte:
                            campo_consumo.insert(0, str(num).replace(".", ","))
                    except Exception:
                        campo_consumo.insert(0, str(consumo_peca))

            # ---------- GERAR PDF EXATAMENTE COMO NA NOVA_ORDEM ----------
            oc.previsualizar_impressao()

            # Fecha a janela fantasma
            dummy.destroy()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar PDF no layout da Nova Ordem:\n{e}")

    def _gerar_pdf_ordem(self, dados: dict) -> str:
        """
        Gera um PDF simples de ordem de corte,
        mantendo o mesmo padrão visual (fonte / pasta) da NOVA_ORDEM.py.
        """
        codigo = str(dados.get("codigo") or "").strip()
        if not codigo:
            codigo = f"ordem_{dados.get('id', '')}".strip("_")

        codigo_sanitizado = (
            codigo.replace("/", "-")
            .replace("\\", "-")
            .replace(" ", "_")
        )

        nome_arquivo = f"{codigo_sanitizado}.pdf"
        caminho_pdf = os.path.join(PASTA_ORDENS_CORTE, nome_arquivo)

        contador = 1
        while os.path.exists(caminho_pdf):
            nome_arquivo = f"{codigo_sanitizado}_{contador}.pdf"
            caminho_pdf = os.path.join(PASTA_ORDENS_CORTE, nome_arquivo)
            contador += 1

        c = canvas.Canvas(caminho_pdf, pagesize=A4)
        width, height = A4

        margem_esq = 40
        margem_dir = width - 40
        y = height - 50

        # Cabeçalho
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margem_esq, y, "ORDEM DE CORTE")
        y -= 25

        c.setFont("Helvetica", 10)
        data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
        c.drawRightString(margem_dir, height - 40, f"Impresso em: {data_hoje}")

        # Linha de separação
        c.line(margem_esq, y, margem_dir, y)
        y -= 20

        # Informações principais
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margem_esq, y, "Código:")
        c.setFont("Helvetica", 11)
        c.drawString(margem_esq + 60, y, str(dados.get("codigo", "")))
        y -= 18

        c.setFont("Helvetica-Bold", 11)
        c.drawString(margem_esq, y, "Descrição:")
        c.setFont("Helvetica", 11)
        c.drawString(margem_esq + 70, y, str(dados.get("descricao", "")))
        y -= 18

        if "data_final" in dados and dados.get("data_final"):
            c.setFont("Helvetica-Bold", 11)
            c.drawString(margem_esq, y, "Data Final:")
            c.setFont("Helvetica", 11)
            c.drawString(margem_esq + 70, y, str(dados.get("data_final", "")))
            y -= 18

        if "quantidade" in dados and dados.get("quantidade"):
            c.setFont("Helvetica-Bold", 11)
            c.drawString(margem_esq, y, "Quantidade:")
            c.setFont("Helvetica", 11)
            c.drawString(margem_esq + 80, y, str(dados.get("quantidade", "")))
            y -= 25

        # Rodapé simples
        c.line(margem_esq, 60, margem_dir, 60)
        c.setFont("Helvetica", 9)
        c.drawString(margem_esq, 48, "Sistema OPERA - Ordem de Corte (Impressão)")
        if self.usuario_nome:
            c.drawRightString(margem_dir, 48, f"Usuário: {self.usuario_nome}")

        c.showPage()
        c.save()

        return caminho_pdf


# -----------------------------------------------------------------
#  Teste local (opcional)
# -----------------------------------------------------------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("ORDENS DE CORTE - IMPRESSÃO (Teste Local)")
    root.geometry("900x500")

    pagina = OrdensCorteImpressao(root)
    pagina.pack(fill="both", expand=True)

    root.mainloop()

#03/02/2025