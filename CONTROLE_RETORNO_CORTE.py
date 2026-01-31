# -*- coding: utf-8 -*-
import TEMAS
import BANCO_DE_DADOS_PG as db
import os
import json
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from BANCO_DE_DADOS_PG import get_conn, get_schema

# ---------- CONFIGURAÇÃO ----------
# ============================== Utils ==============================
def safe_int(v, default=0):
    try:
        if v is None: return default
        s = str(v).strip()
        if not s: return default
        return int(float(s.replace(".", "").replace(",", ".")))
    except Exception:
        return default

LOGO_PATH = os.path.join(os.path.dirname(__file__), "LOGO.jpg")

def parse_valor(s):
    try:
        s = (s or "").strip().replace("R$", "").replace(" ", "")
        if not s: return 0.0
        return float(s.replace(".", "").replace(",", "."))
    except Exception:
        return 0.0

def fmt_moeda(v):
    s = f"{float(v):,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def fmt_dec2_br(valor):
    """
    Formata um número float para padrão brasileiro:
    - 2 casas decimais
    - vírgula como separador decimal
    - sem separador de milhar
    """
    try:
        return f"{float(valor):.2f}".replace(".", ",")
    except (ValueError, TypeError):
        return "0,00"

# ---------- helpers p/ cadastro_faccoes ----------
def _coluna_titular():
    """Descobre nome da coluna do titular"""
    try:
        result = db.fetch_all(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s",
            (db.get_schema(), "cadastro_faccoes")
        )
        cols = [r["column_name"] for r in result]
        for p in ["titular_da_conta", "titular_conta", "titular"]:
            if p in cols: return p
        for c in cols:
            if "titular" in c.lower(): return c
        return None
    except Exception:
        return None

def _coluna_endereco():
    """Descobre nome da coluna do endereço"""
    try:
        result = db.fetch_all(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s",
            (db.get_schema(), "cadastro_faccoes")
        )
        all_cols = [r["column_name"] for r in result]
        lower = [c.lower() for c in all_cols]
        prefer = ["endereco", "endereço", "endereco_completo", "logradouro", "rua"]
        for p in prefer:
            if p in lower: return all_cols[lower.index(p)]
        for c in all_cols:
            lc = c.lower()
            if any(k in lc for k in ["endereco", "endereço", "logradouro", "rua"]):
                return c
        return None
    except Exception:
        return None

# ---------- helpers p/ envios_cortes ----------
def _coluna_colecao():
    """Descobre nome da coluna da coleção na tabela envios_cortes"""
    try:
        result = db.fetch_all(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s AND column_name ILIKE '%colecao%'",
            (db.get_schema(), "envios_cortes")
        )
        return result[0]["column_name"] if result else "colecao"
    except Exception:
        return "colecao"

def _coluna_material():
    """Descobre nome da coluna do material na tabela envios_cortes"""
    try:
        result = db.fetch_all(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s AND column_name ILIKE '%material%'",
            (db.get_schema(), "envios_cortes")
        )
        return result[0]["column_name"] if result else "material"
    except Exception:
        return "material"

def _coluna_cliente():
    """Descobre nome da coluna do cliente na tabela envios_cortes"""
    try:
        result = db.fetch_all(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s AND column_name ILIKE '%cliente%'",
            (db.get_schema(), "envios_cortes")
        )
        return result[0]["column_name"] if result else "cliente"
    except Exception:
        return "cliente"

# ============================== Tela ==============================
class RetornoCortes(ctk.CTkFrame):
    tamanhos = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]

    def __init__(self, master, sistema=None):
        super().__init__(master)
        self.master = master
        self.sistema = sistema

        # === APLICAR CORES AO FRAME PRINCIPAL ===
        self.obter_cores_por_tema()
        self.configure(fg_color=self.cor_fundo)

        # Variáveis de estado
        self.envio_selecionado = None
        self._prestador_id = None
        self._prestador_nome = ""
        self._tipo_servico = ""
        self._prest_endereco = ""

        # Dicionários para grade
        # StringVar evita exceções do Tkinter quando o campo fica vazio ("")
        self.entregues = {t: tk.StringVar(value="0") for t in self.tamanhos}
        self.copias = {t: tk.StringVar(value="0") for t in self.tamanhos}
        self.defeitos = {t: tk.StringVar(value="0") for t in self.tamanhos}
        self.faltantes = {t: tk.StringVar(value="0") for t in self.tamanhos}

        # Quantidades já entregues (acumuladas de devoluções anteriores) por tamanho.
        # Estes valores são preenchidos quando os detalhes do envio são carregados
        # em ``_carregar_detalhes_envio``.  Eles representam o total de peças
        # devolvidas em retornos anteriores e são usados para calcular o
        # saldo pendente (faltantes) quando o usuário informa novas quantidades
        # entregues.  Sem essa variável, o campo "faltantes" não é atualizado
        # automaticamente ao digitar no campo "Entregue".  Consulte
        # ``_recalcular`` para mais detalhes.
        self.entregues_prev = {t: 0 for t in self.tamanhos}

        # Dados por tamanho
        self.enviado_por_tam = {t: 0 for t in self.tamanhos}
        self.valor_por_tam = {t: 0.0 for t in self.tamanhos}
        self.pilotos_por_tam = {t: 0 for t in self.tamanhos}

        # Widgets da grade
        self.grade_widgets = {}

        # Variáveis de controle
        self.piloto_entregue_var = ctk.BooleanVar(value=True)
        self.incluir_conferencia_var = tk.BooleanVar(value=False)


        # Widgets principais (serão criados no _build_ui)
        self.busca_entry = None
        self.prestador_entry = None
        self.servico_entry = None
        self.telefone_entry = None
        self.cpf_entry = None
        self.banco_entry = None
        self.agencia_entry = None
        self.conta_entry = None
        self.pix_entry = None
        self.titular_entry = None
        self.envios_tree = None
        self.tel_encarregado_entry = None
        self.tel_acabamento_entry = None
        self.data_chegada_entry = None
        self.codigo_entry = None
        self.descricao_entry = None
        self.ordem_entry = None
        self.lbl_total_entregue = None
        self.lbl_total_copias = None
        self.lbl_total_regulares = None
        self.lbl_valor_total = None
        self.piloto_resumo_lbl = None
        self.aviamentos_txt = None
        self.outros_txt = None
        self.obs_geral_txt = None
        self.cb_mostrar_conf = None
        self.cb_piloto_entregue = None
        self.style = None

        # Logo
        self.logo_img = None

        # Configuração inicial
        self.pack(fill="both", expand=True)
        self._build_ui()
        self.carregar_envios_pendentes()

    def obter_cores_por_tema(self):
        """Define cores de texto dinamicamente baseado no tema atual - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
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
            self.cor_sucesso = getattr(self.sistema, "cor_sucesso", "#22c55e")
            self.cor_alerta = getattr(self.sistema, "cor_alerta", "#ef4444")
            self.cor_selecao = getattr(self.sistema, "cor_selecao", "#2563eb")
        else:
            self.cor_fundo = "#ffffff"
            self.cor_primaria = "#3a7ebf"
            self.cor_secundaria = "#f0f0f0"
            self.cor_texto = "black"
            self.cor_texto_entry = "black"
            self.cor_placeholder = "#666666"
            self.cor_borda = "#cccccc"
            self.cor_hover = "#2e4a66"
            self.cor_sucesso = "#22c55e"
            self.cor_alerta = "#ef4444"
            self.cor_selecao = "#3a7ebf"

    def configurar_treeview_theme(self):
        """Configura as cores da Treeview baseado no tema atual - MESMO ESTILO DO CADASTRO_DE_CORTE"""
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
                             rowheight=25)

        self.style.configure("Custom.Treeview.Heading",
                             background=self.cor_primaria,
                             foreground=self.cor_texto,
                             relief="flat",
                             borderwidth=1,
                             font=('Arial', 10, 'bold'))

        self.style.map('Custom.Treeview',
                       background=[('selected', cor_selecao)],
                       foreground=[('selected', "white")])

    # ----------------------------- UI -----------------------------
    def _build_ui(self):
        # Frame principal com tema
        main = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # Título + logo - MESMO ESTILO DO CADASTRO_DE_CORTE
        head = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        head.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(head, text="CONTROLE DE MÃO DE OBRA — Retorno de Cortes",
                     font=("Arial", 18, "bold"), text_color=self.cor_texto).pack(side="left", padx=10)

        # Logo
        try:
            from PIL import Image
            if os.path.exists(LOGO_PATH):
                img = Image.open(LOGO_PATH)
                w, h = img.size
                tw = 140
                th = int(h * (tw / w))
                self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(tw, th))
                ctk.CTkLabel(head, image=self.logo_img, text="").pack(side="right", padx=10)
        except Exception:
            pass

        # Buscar envio - MESMO ESTILO DO CADASTRO_DE_CORTE
        busca = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        busca.pack(fill="x", pady=6)

        ctk.CTkLabel(busca, text="Buscar Envio:", width=120, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        self.busca_entry = ctk.CTkEntry(busca, width=320, placeholder_text="Ordem, código ou descrição",
                                        fg_color=self.cor_secundaria, border_color=self.cor_borda,
                                        text_color=self.cor_texto_entry,
                                        placeholder_text_color=self.cor_placeholder)
        self.busca_entry.pack(side="left", padx=5)
        self.busca_entry.bind("<Return>", lambda e: self.carregar_envios_pendentes())

        ctk.CTkButton(busca, text="Buscar", width=90, command=self.carregar_envios_pendentes,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=5)

        # Filtro: incluir 'Em Conferência' na listagem - MESMO ESTILO DO CADASTRO_DE_CORTE
        self.cb_mostrar_conf = ctk.CTkCheckBox(
            busca,
            text="Mostrar 'Em Conferência'",
            variable=self.incluir_conferencia_var,
            onvalue=True,
            offvalue=False,
            command=self.carregar_envios_pendentes,
            fg_color=self.cor_selecao,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            checkmark_color=self.cor_texto
        )
        self.cb_mostrar_conf.pack(side="left", padx=8)

        # Prestador + Serviço (somente leitura) - MESMO ESTILO DO CADASTRO_DE_CORTE
        prest = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        prest.pack(fill="x", pady=(6, 8))

        linha = ctk.CTkFrame(prest, fg_color=self.cor_fundo)
        linha.pack(fill="x", pady=(4, 2))

        ctk.CTkLabel(linha, text="Prestador:", width=100, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        self.prestador_entry = ctk.CTkEntry(linha, width=360,
                                            fg_color=self.cor_secundaria,
                                            border_color=self.cor_borda,
                                            text_color=self.cor_texto_entry)
        self.prestador_entry.pack(side="left", padx=5)
        self.prestador_entry.configure(state="disabled")

        ctk.CTkLabel(linha, text="Serviço:", width=80, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        self.servico_entry = ctk.CTkEntry(linha, width=220,
                                          fg_color=self.cor_secundaria,
                                          border_color=self.cor_borda,
                                          text_color=self.cor_texto_entry)
        self.servico_entry.pack(side="left", padx=5)
        self.servico_entry.configure(state="disabled")

        # Dados bancários (somente leitura) - MESMO ESTILO DO CADASTRO_DE_CORTE
        banco = ctk.CTkFrame(prest, fg_color=self.cor_fundo)
        banco.pack(fill="x", pady=(10, 6))

        ctk.CTkLabel(banco, text="Dados Bancários do Prestador", font=("Arial", 13, "bold"),
                     text_color=self.cor_texto).pack(anchor="w", padx=5, pady=2)

        grid = ctk.CTkFrame(banco, fg_color=self.cor_fundo)
        grid.pack(fill="x", padx=2)

        def ro(parent, w=220):
            e = ctk.CTkEntry(parent, width=w,
                             fg_color=self.cor_secundaria,
                             border_color=self.cor_borda,
                             text_color=self.cor_texto_entry,
                             state="disabled")
            return e

        l1b = ctk.CTkFrame(grid, fg_color=self.cor_fundo)
        l1b.pack(fill="x", pady=2)

        ctk.CTkLabel(l1b, text="Telefone:", width=90, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)
        self.telefone_entry = ro(l1b, 220)
        self.telefone_entry.pack(side="left", padx=5)

        ctk.CTkLabel(l1b, text="CPF:", width=60, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)
        self.cpf_entry = ro(l1b, 180)
        self.cpf_entry.pack(side="left", padx=5)

        ctk.CTkLabel(l1b, text="Banco:", width=70, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)
        self.banco_entry = ro(l1b, 180)
        self.banco_entry.pack(side="left", padx=5)

        l2b = ctk.CTkFrame(grid, fg_color=self.cor_fundo)
        l2b.pack(fill="x", pady=2)

        ctk.CTkLabel(l2b, text="Agência:", width=90, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)
        self.agencia_entry = ro(l2b, 160)
        self.agencia_entry.pack(side="left", padx=5)

        ctk.CTkLabel(l2b, text="Conta:", width=60, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)
        self.conta_entry = ro(l2b, 180)
        self.conta_entry.pack(side="left", padx=5)

        ctk.CTkLabel(l2b, text="PIX:", width=70, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)
        self.pix_entry = ro(l2b, 220)
        self.pix_entry.pack(side="left", padx=5)

        l3b = ctk.CTkFrame(grid, fg_color=self.cor_fundo)
        l3b.pack(fill="x", pady=2)

        ctk.CTkLabel(l3b, text="Titular da Conta:", width=140, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)
        self.titular_entry = ro(l3b, 280)
        self.titular_entry.pack(side="left", padx=5)

        # Tabela de envios pendentes - MESMO ESTILO DO CADASTRO_DE_CORTE
        tabela_frame = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        tabela_frame.pack(fill="both", expand=True, pady=8)

        # Configurar estilo da Treeview para combinar com o tema
        self.configurar_treeview_theme()

        cols = ["ID", "Ordem", "Código", "Descrição", "Prestador", "Data Envio", "Status", "Qtd Peças"]
        self.envios_tree = ttk.Treeview(tabela_frame, columns=cols, show="headings", height=7, style="Custom.Treeview")

        sb = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.envios_tree.yview)
        sb.pack(side="right", fill="y")
        self.envios_tree.configure(yscrollcommand=sb.set)
        self.envios_tree.pack(fill="both", expand=True)

        for col in cols:
            self.envios_tree.heading(col, text=col)
            w = 100 if col in ["ID", "Status"] else (90 if col == "Qtd Peças" else 140)
            self.envios_tree.column(col, width=w, anchor="center")
        self.envios_tree.bind("<<TreeviewSelect>>", self.on_envio_selecionado)
        self.envios_tree.bind("<Double-1>", self._aviso_envio_em_conferencia)

        # Cores por status - MESMO ESTILO DO CADASTRO_DE_CORTE
        if ctk.get_appearance_mode() == "Dark":
            cor_linha_par = self.cor_fundo
            cor_linha_impar = self.cor_secundaria
        else:
            cor_linha_par = "#ffffff"
            cor_linha_impar = "#f0f0f0"

        try:
            self.envios_tree.tag_configure('status_conferencia', background='#FFF9C4', foreground='black')
            self.envios_tree.tag_configure('status_finalizado', background='#C8E6C9', foreground='black')
            self.envios_tree.tag_configure('oddrow', background=cor_linha_impar)
            self.envios_tree.tag_configure('evenrow', background=cor_linha_par)
        except Exception:
            pass

        # Detalhes do corte - MESMO ESTILO DO CADASTRO_DE_CORTE
        det = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        det.pack(fill="x", pady=6)

        l1 = ctk.CTkFrame(det, fg_color=self.cor_fundo)
        l1.pack(fill="x", pady=2)

        ctk.CTkLabel(l1, text="Telefone Encarregado:", width=150, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        self.tel_encarregado_entry = ctk.CTkEntry(l1, width=180,
                                                  fg_color=self.cor_secundaria,
                                                  border_color=self.cor_borda,
                                                  text_color=self.cor_texto_entry)
        self.tel_encarregado_entry.pack(side="left", padx=5)

        ctk.CTkLabel(l1, text="Telefone Acabamento:", width=150, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        self.tel_acabamento_entry = ctk.CTkEntry(l1, width=180,
                                                 fg_color=self.cor_secundaria,
                                                 border_color=self.cor_borda,
                                                 text_color=self.cor_texto_entry)
        self.tel_acabamento_entry.pack(side="left", padx=5)

        ctk.CTkLabel(l1, text="Data de Chegada:", width=140, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        self.data_chegada_entry = ctk.CTkEntry(l1, width=120,
                                               fg_color=self.cor_secundaria,
                                               border_color=self.cor_borda,
                                               text_color=self.cor_texto_entry)
        self.data_chegada_entry.pack(side="left", padx=5)
        self.data_chegada_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))

        l2 = ctk.CTkFrame(det, fg_color=self.cor_fundo)
        l2.pack(fill="x", pady=2)

        ctk.CTkLabel(l2, text="Código:", width=70, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        self.codigo_entry = ctk.CTkEntry(l2, width=180,
                                         fg_color=self.cor_secundaria,
                                         border_color=self.cor_borda,
                                         text_color=self.cor_texto_entry)
        self.codigo_entry.pack(side="left", padx=5)
        self.codigo_entry.configure(state="disabled")

        ctk.CTkLabel(l2, text="Descrição:", width=80, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        self.descricao_entry = ctk.CTkEntry(l2, width=380,
                                            fg_color=self.cor_secundaria,
                                            border_color=self.cor_borda,
                                            text_color=self.cor_texto_entry)
        self.descricao_entry.pack(side="left", padx=5)
        self.descricao_entry.configure(state="disabled")

        ctk.CTkLabel(l2, text="Nº Ordem:", width=80, anchor="e",
                     text_color=self.cor_texto).pack(side="left", padx=5)

        self.ordem_entry = ctk.CTkEntry(l2, width=120,
                                        fg_color=self.cor_secundaria,
                                        border_color=self.cor_borda,
                                        text_color=self.cor_texto_entry)
        self.ordem_entry.pack(side="left", padx=5)
        self.ordem_entry.configure(state="disabled")

        # Área central (2 colunas) - MESMO ESTILO DO CADASTRO_DE_CORTE
        mid = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        mid.pack(fill="both", expand=True, pady=6)
        mid.grid_columnconfigure(0, weight=3)
        mid.grid_columnconfigure(1, weight=2)
        mid.grid_rowconfigure(0, weight=1)

        # ESQ — grade por tamanho - MESMO ESTILO DO CADASTRO_DE_CORTE
        left = ctk.CTkFrame(mid, fg_color=self.cor_fundo)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(left, text="Controle por Tamanho", font=("Arial", 13, "bold"),
                     text_color=self.cor_texto).pack(anchor="w", padx=5, pady=(4, 6))

        header_g = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        header_g.pack(fill="x")

        header_specs = [
            ("Tam.", 60),
            ("Enviado", 80),
            ("Entregue", 90),
            ("Cópias", 80),
            ("Defeito", 80),
            ("Faltante", 80),
            ("Regulares (pagas)", 120),
            ("Valor/Peça", 100),
            ("Subtotal", 110),
        ]
        for h, w in header_specs:
            lbl = ctk.CTkLabel(header_g, text=h, width=w, anchor="center",
                               text_color=self.cor_texto)
            if h == "Entregue":
                self.header_entregue_label = lbl
            lbl.pack(side="left", padx=2)

        self.grade_widgets = {}
        for tam in self.tamanhos:
            row = ctk.CTkFrame(left, fg_color=self.cor_fundo)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=tam, width=60, anchor="center",
                         text_color=self.cor_texto).pack(side="left", padx=2)

            lbl_env = ctk.CTkLabel(row, text="0", width=80, anchor="center",
                                   text_color=self.cor_texto)
            lbl_env.pack(side="left", padx=2)

            ent_ent = ctk.CTkEntry(row, width=90, textvariable=self.entregues[tam],
                                   fg_color=self.cor_secundaria,
                                   border_color=self.cor_borda,
                                   text_color=self.cor_texto_entry)
            ent_ent.pack(side="left", padx=2)
            ent_ent.bind("<KeyRelease>", self._recalcular)

            ent_cop = ctk.CTkEntry(row, width=80, textvariable=self.copias[tam],
                                   fg_color=self.cor_secundaria,
                                   border_color=self.cor_borda,
                                   text_color=self.cor_texto_entry)
            ent_cop.pack(side="left", padx=2)
            ent_cop.bind("<KeyRelease>", self._recalcular)

            ent_def = ctk.CTkEntry(row, width=80, textvariable=self.defeitos[tam],
                                   fg_color=self.cor_secundaria,
                                   border_color=self.cor_borda,
                                   text_color=self.cor_texto_entry)
            ent_def.pack(side="left", padx=2)
            ent_def.bind("<KeyRelease>", self._recalcular)

            ent_fal = ctk.CTkEntry(row, width=80, textvariable=self.faltantes[tam],
                                   fg_color=self.cor_secundaria,
                                   border_color=self.cor_borda,
                                   text_color=self.cor_texto_entry)
            ent_fal.pack(side="left", padx=2)
            ent_fal.bind("<KeyRelease>", self._recalcular)

            lbl_reg = ctk.CTkLabel(row, text="0", width=120, anchor="center",
                                   text_color=self.cor_texto)
            lbl_reg.pack(side="left", padx=2)

            lbl_val = ctk.CTkLabel(row, text=fmt_moeda(0), width=100, anchor="center",
                                   text_color=self.cor_texto)
            lbl_val.pack(side="left", padx=2)

            lbl_sub = ctk.CTkLabel(row, text=fmt_moeda(0), width=110, anchor="center",
                                   text_color=self.cor_texto)
            lbl_sub.pack(side="left", padx=2)

            self.grade_widgets[tam] = {"enviado": lbl_env, "regulares": lbl_reg, "valor": lbl_val, "subtotal": lbl_sub}

        totais = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        totais.pack(fill="x", pady=(6, 8))

        ctk.CTkLabel(totais, text="Total Entregue:", width=140, font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=5)

        self.lbl_total_entregue = ctk.CTkLabel(totais, text="0", font=("Arial", 12, "bold"),
                                               text_color=self.cor_texto)
        self.lbl_total_entregue.pack(side="left", padx=5)

        ctk.CTkLabel(totais, text="Cópias:", width=80, font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=12)

        self.lbl_total_copias = ctk.CTkLabel(totais, text="0", font=("Arial", 12, "bold"),
                                             text_color=self.cor_texto)
        self.lbl_total_copias.pack(side="left", padx=5)

        ctk.CTkLabel(totais, text="Regulares (pagas):", width=160, font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=12)

        self.lbl_total_regulares = ctk.CTkLabel(totais, text="0", font=("Arial", 12, "bold"),
                                                text_color=self.cor_texto)
        self.lbl_total_regulares.pack(side="left", padx=5)

        ctk.CTkLabel(totais, text="Valor Total a Pagar:", width=170, font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=12)

        self.lbl_valor_total = ctk.CTkLabel(totais, text=fmt_moeda(0), font=("Arial", 12, "bold"),
                                            text_color=self.cor_texto)
        self.lbl_valor_total.pack(side="left", padx=5)

        botoes = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        botoes.pack(fill="x", pady=(2, 8))

        ctk.CTkButton(botoes, text="Registrar Entrada", width=160, command=self.registrar_entrada,
                      fg_color=self.cor_sucesso, hover_color=self.cor_hover,
                      text_color=self.cor_texto, font=("Arial", 12)).pack(side="left", padx=5)

        ctk.CTkButton(botoes, text="Pré-visualizar PDF", width=150, command=self.pre_visualizar_pdf,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto, font=("Arial", 12)).pack(side="left", padx=5)

        ctk.CTkButton(botoes, text="Exportar PDF", width=120, command=self.exportar_pdf,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto, font=("Arial", 12)).pack(side="left", padx=5)

        ctk.CTkButton(botoes, text="Limpar", width=120, command=self.limpar_campos,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto, font=("Arial", 12)).pack(side="left", padx=5)

        # DIR — Piloto/Observações - MESMO ESTILO DO CADASTRO_DE_CORTE
        right = ctk.CTkFrame(mid, fg_color=self.cor_fundo)
        right.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(right, text="Piloto Recebido:", font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(anchor="w", padx=6, pady=(6, 2))

        self.piloto_resumo_lbl = ctk.CTkLabel(right, text="Nenhum.", justify="left",
                                              text_color=self.cor_texto)
        self.piloto_resumo_lbl.pack(fill="x", padx=6)

        self.cb_piloto_entregue = ctk.CTkCheckBox(
            right,
            text="Piloto entregue? (dar baixa na piloto ao salvar)",
            variable=self.piloto_entregue_var,
            fg_color=self.cor_selecao,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            checkmark_color=self.cor_texto
        )
        self.cb_piloto_entregue.pack(anchor="w", padx=6, pady=(4, 8))

        ctk.CTkLabel(right, text="Aviamentos Recebidos:", font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(anchor="w", padx=6, pady=(8, 2))

        self.aviamentos_txt = ctk.CTkTextbox(right, height=90,
                                             fg_color=self.cor_secundaria,
                                             border_color=self.cor_borda,
                                             text_color=self.cor_texto_entry)
        self.aviamentos_txt.pack(fill="x", padx=6)

        ctk.CTkLabel(right, text="Outros (linha, renda, aparelhos, etc.) — Recebidos:",
                     font=("Arial", 12, "bold"), text_color=self.cor_texto).pack(anchor="w", padx=6, pady=(8, 2))

        self.outros_txt = ctk.CTkTextbox(right, height=90,
                                         fg_color=self.cor_secundaria,
                                         border_color=self.cor_borda,
                                         text_color=self.cor_texto_entry)
        self.outros_txt.pack(fill="x", padx=6)

        ctk.CTkLabel(right, text="Observações Gerais:", font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(anchor="w", padx=6, pady=(8, 2))

        self.obs_geral_txt = ctk.CTkTextbox(right, height=140,
                                            fg_color=self.cor_secundaria,
                                            border_color=self.cor_borda,
                                            text_color=self.cor_texto_entry)
        self.obs_geral_txt.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    # ----------------------------- Loaders -----------------------------
    def carregar_envios_pendentes(self):
        """
        Carrega lista de envios a partir da tabela ``envios_cortes``.

        - Sempre oculta "Finalizado"
        - Só mostra "Em Conferencia/Em Conferência" se a caixa estiver marcada
        """
        try:
            termo = (self.busca_entry.get() or "").strip()
            self.envios_tree.delete(*self.envios_tree.get_children())

            params = []

            # Base: esconder somente finalizados
            where = [
                "e.status_envio != 'Finalizado'"
            ]

            # ✅ AQUI É O AJUSTE:
            # Se a caixa NÃO estiver marcada, esconda os envios em conferência
            if not self.incluir_conferencia_var.get():
                where.append(
                    "(COALESCE(e.status_envio,'') NOT ILIKE 'Em Conferen%%' "
                    "AND COALESCE(e.status_envio,'') NOT ILIKE 'Em Conferên%%')"
                )

            if termo:
                like = f"%{termo}%"
                where.append("""
                    (e.ordem_corte ILIKE %s
                     OR e.codigo_corte ILIKE %s
                     OR e.descricao_corte ILIKE %s
                     OR f.nome ILIKE %s
                     OR e.colecao ILIKE %s
                     OR e.cores ILIKE %s
                     OR e.material ILIKE %s)
                """)
                params.extend([like, like, like, like, like, like, like])

            where_sql = " AND ".join(where)

            # Obter nomes reais das colunas dinâmicas
            colecao_col = _coluna_colecao()
            material_col = _coluna_material()
            cliente_col = _coluna_cliente()

            sql = f"""
                SELECT
                    e.id,
                    COALESCE(e.ordem_corte, '')              AS ordem_corte,
                    COALESCE(e.codigo_corte, '')             AS codigo_corte,
                    COALESCE(e.descricao_corte, '')          AS descricao_corte,
                    COALESCE(f.nome, '')                     AS destino,
                    TO_CHAR(e.data_envio, 'DD/MM/YYYY')      AS data_envio,
                    COALESCE(e.status_envio, 'Enviado')      AS status,
                    COALESCE(e.tipo_servico, '')             AS servico,
                    COALESCE(e.{colecao_col}, '')            AS colecao,
                    COALESCE(e.{material_col}, '')           AS material,
                    COALESCE(e.{cliente_col}, '')            AS cliente,
                    COALESCE(e.cores, '')                    AS cores,
                    COALESCE(e.prioridade, '')               AS prioridade,
                    COALESCE(e.forma_pagamento, '')          AS forma_pagamento,
                    COALESCE(e.qtd_pp, 0)                    AS qtd_pp,
                    COALESCE(e.qtd_p, 0)                     AS qtd_p,
                    COALESCE(e.qtd_m, 0)                     AS qtd_m,
                    COALESCE(e.qtd_g, 0)                     AS qtd_g,
                    COALESCE(e.qtd_gg, 0)                    AS qtd_gg,
                    COALESCE(e.qtd_g1, 0)                    AS qtd_g1,
                    COALESCE(e.qtd_g2, 0)                    AS qtd_g2,
                    COALESCE(e.qtd_g3, 0)                    AS qtd_g3
                FROM {get_schema()}.envios_cortes e
                LEFT JOIN {get_schema()}.cadastro_faccoes f ON f.id = e.prestador_id
                WHERE {where_sql}
                ORDER BY e.id DESC
            """

            rows = db.fetch_all(sql, tuple(params)) or []

            for row in rows:
                qtd_total = (
                        int(row.get("qtd_pp", 0)) + int(row.get("qtd_p", 0)) + int(row.get("qtd_m", 0)) +
                        int(row.get("qtd_g", 0)) + int(row.get("qtd_gg", 0)) + int(row.get("qtd_g1", 0)) +
                        int(row.get("qtd_g2", 0)) + int(row.get("qtd_g3", 0))
                )

                self.envios_tree.insert(
                    "",
                    "end",
                    values=(
                        row.get("id"),
                        row.get("ordem_corte"),
                        row.get("codigo_corte"),
                        row.get("descricao_corte"),
                        row.get("destino"),
                        row.get("data_envio"),
                        row.get("status"),
                        qtd_total
                    )
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erro", f"Falha ao carregar envios: {e}")

    def _carregar_dados_prestador(self, prestador_id):
        """Carrega dados do prestador e preenche campos bancários."""
        try:
            print(f"DEBUG: Carregando prestador_id = {prestador_id}")  # DEBUG

            if not prestador_id:
                print("DEBUG: prestador_id é None ou vazio")  # DEBUG
                self._preencher_banco(None)
                return

            tit_col = _coluna_titular()
            end_col = _coluna_endereco()

            base = "id, nome, COALESCE(telefone,'') as telefone, COALESCE(cpf,'') as cpf, COALESCE(banco,'') as banco, COALESCE(agencia,'') as agencia, COALESCE(conta,'') as conta, COALESCE(pix,'') as pix"
            select_full = f"{base}, COALESCE({tit_col},'') as titular" if tit_col else f"{base}, '' as titular"
            select_full += f", COALESCE({end_col},'') as endereco" if end_col else ", '' as endereco"

            sql = f"""
                SELECT {select_full}
                FROM {get_schema()}.cadastro_faccoes
                WHERE id = %s
                LIMIT 1
            """

            print(f"DEBUG: SQL = {sql}")  # DEBUG
            print(f"DEBUG: Parâmetro = {prestador_id}")  # DEBUG

            row = db.fetch_one(sql, (prestador_id,))

            print(f"DEBUG: Resultado da consulta = {row}")  # DEBUG

            if row:
                self._prestador_nome = row.get("nome") or ""
                print(f"DEBUG: Nome do prestador = {self._prestador_nome}")  # DEBUG

                self.prestador_entry.configure(state="normal")
                self.prestador_entry.delete(0, tk.END)
                self.prestador_entry.insert(0, self._prestador_nome)
                self.prestador_entry.configure(state="disabled")

                # Preencher dados bancários
                dados = [
                    row.get("telefone", ""),
                    row.get("cpf", ""),
                    row.get("banco", ""),
                    row.get("agencia", ""),
                    row.get("conta", ""),
                    row.get("pix", ""),
                    row.get("titular", "") if tit_col else "",
                    row.get("endereco", "") if end_col else ""
                ]

                print(f"DEBUG: Dados bancários = {dados}")  # DEBUG
                self._preencher_banco(dados, True)
            else:
                print("DEBUG: Nenhum resultado encontrado para prestador_id")  # DEBUG
                self._preencher_banco(None)

        except Exception as e:
            print(f"DEBUG: Erro ao carregar dados do prestador: {e}")  # DEBUG
            self._preencher_banco(None)
            messagebox.showerror("Erro", f"Falha ao carregar dados do prestador: {e}")

    def _carregar_detalhes_envio(self, envio_id):
        """Carrega grade, valores, telefones e observações do envio selecionado."""
        try:
            # Limpa grade atual
            for t in self.tamanhos:
                self.entregues[t].set(0)
                self.copias[t].set(0)
                self.defeitos[t].set(0)
                self.faltantes[t].set(0)
                self.enviado_por_tam[t] = 0
                self.valor_por_tam[t] = 0.0
                self.pilotos_por_tam[t] = 0
                self.grade_widgets[t]["enviado"].configure(text="0")
                self.grade_widgets[t]["regulares"].configure(text="0")
                self.grade_widgets[t]["valor"].configure(text=fmt_moeda(0))
                self.grade_widgets[t]["subtotal"].configure(text=fmt_moeda(0))

            self.lbl_total_entregue.configure(text="0")
            self.lbl_total_copias.configure(text="0")
            self.lbl_total_regulares.configure(text="0")
            self.lbl_valor_total.configure(text=fmt_moeda(0))

            # Dados da tabela envios_cortes
            mapa_sufixo = {
                "PP": "pp", "P": "p", "M": "m", "G": "g",
                "GG": "gg", "G1": "g1", "G2": "g2", "G3": "g3",
            }

            cols_qtd = [f"qtd_{s}" for s in mapa_sufixo.values()]
            cols_pil = [f"piloto_{s}" for s in mapa_sufixo.values()]
            cols_val = [f"valor_{s}" for s in mapa_sufixo.values()]

            outras_cols = [
                "aviamentos", "outros", "observacoes",
                "tel_encarregado", "tel_acabamento",
                "prestador_id", "tipo_servico", "resumo_pilotos"
            ]

            sql_envio = f"""
                SELECT {', '.join(cols_qtd + cols_pil + cols_val + outras_cols)}
                FROM {get_schema()}.envios_cortes
                WHERE id = %s
            """
            row = db.fetch_one(sql_envio, (envio_id,))

            if row:
                # Carregar dados do prestador
                self._prestador_id = row.get("prestador_id")
                self._tipo_servico = row.get("tipo_servico") or ""

                # Atualiza o campo de serviço
                self.servico_entry.configure(state="normal")
                self.servico_entry.delete(0, tk.END)
                self.servico_entry.insert(0, self._tipo_servico or "")
                self.servico_entry.configure(state="disabled")

                # Carrega dados bancários
                if self._prestador_id:
                    self._carregar_dados_prestador(self._prestador_id)

                # Carregar resumo de pilotos e valores
                resumo_pilotos = []
                for tam, suf in mapa_sufixo.items():
                    qtd_env = row.get(f"qtd_{suf}") or 0
                    qtd_pil = row.get(f"piloto_{suf}") or 0
                    val_unit = row.get(f"valor_{suf}") or 0

                    self.enviado_por_tam[tam] = int(qtd_env)
                    self.pilotos_por_tam[tam] = int(qtd_pil)
                    self.valor_por_tam[tam] = float(val_unit or 0)

                    self.grade_widgets[tam]["enviado"].configure(text=str(qtd_env))
                    self.grade_widgets[tam]["valor"].configure(text=fmt_moeda(val_unit))

                    if qtd_pil:
                        resumo_pilotos.append(f"{tam}={qtd_pil}")

                # Telefones do envio
                self.tel_encarregado_entry.delete(0, tk.END)
                self.tel_encarregado_entry.insert(0, row.get("tel_encarregado") or "")

                self.tel_acabamento_entry.delete(0, tk.END)
                self.tel_acabamento_entry.insert(0, row.get("tel_acabamento") or "")

                # Observações do envio
                self.aviamentos_txt.delete("1.0", tk.END)
                self.aviamentos_txt.insert("1.0", row.get("aviamentos") or "")

                self.outros_txt.delete("1.0", tk.END)
                self.outros_txt.insert("1.0", row.get("outros") or "")

                self.obs_geral_txt.delete("1.0", tk.END)
                self.obs_geral_txt.insert("1.0", row.get("observacoes") or "")

                # Resumo de pilotos
                if row.get("resumo_pilotos"):
                    self.piloto_resumo_lbl.configure(text=row["resumo_pilotos"])
                elif resumo_pilotos:
                    self.piloto_resumo_lbl.configure(text=", ".join(resumo_pilotos))
                else:
                    self.piloto_resumo_lbl.configure(text="Nenhum.")

            # Ajustes adicionais do RETORNO, se já existir
            try:
                sql_ret = f"""
                    SELECT resumo_piloto, aviamentos_recebidos, outros_recebidos, observacoes_gerais
                    FROM {get_schema()}.controle_retorno_cortes
                    WHERE envio_id = %s
                """
                row_ret = db.fetch_one(sql_ret, (envio_id,))

                if row_ret:
                    if row_ret.get("resumo_piloto"):
                        self.piloto_resumo_lbl.configure(text=row_ret["resumo_piloto"] or "Nenhum.")

                    self.aviamentos_txt.delete("1.0", tk.END)
                    self.aviamentos_txt.insert("1.0", row_ret.get("aviamentos_recebidos") or "")

                    self.outros_txt.delete("1.0", tk.END)
                    self.outros_txt.insert("1.0", row_ret.get("outros_recebidos") or "")

                    self.obs_geral_txt.delete("1.0", tk.END)
                    self.obs_geral_txt.insert("1.0", row_ret.get("observacoes_gerais") or "")
            except Exception:
                pass  # Ignora erro se não existir retorno

            # Recalcula totais
            # Antes de recalcular, carregue a quantidade já entregue em retornos
            # para cada tamanho.  Isto permite mostrar ao usuário quantas peças
            # ainda restam a serem devolvidas.  A tabela ``retorno_detalhes_tamanho``
            # acumula todas as devoluções parciais; somamos as colunas
            # ``entregue`` para obter o total já devolvido.  Em seguida,
            # calculamos o saldo pendente subtraindo do valor originalmente
            # enviado (qtd_*) em ``envios_cortes``.  Esse saldo é então
            # exibido no campo "faltantes" de cada tamanho.
            try:
                # Obter soma de peças já entregues por tamanho nas devoluções
                sql_sum = f"""
                    SELECT tamanho, SUM(entregue) AS total_entregue
                    FROM {get_schema()}.retorno_detalhes_tamanho
                    WHERE envio_id = %s
                    GROUP BY tamanho
                """
                entregas = db.fetch_all(sql_sum, (envio_id,))
                entregas_map = {str(r["tamanho"]).upper(): int(r["total_entregue"] or 0) for r in entregas}

                # Para cada tamanho, armazenar o total entregue acumulado e
                # calcular o saldo pendente = enviado - entregue_acumulado.
                # Esses valores de ``entregues_prev`` serão usados em
                # ``_recalcular`` para atualizar o campo "faltantes" quando
                # o usuário digitar novas quantidades no campo "Entregue".
                for tam in self.tamanhos:
                    enviado = self.enviado_por_tam.get(tam, 0)
                    acumulado = entregas_map.get(tam, 0)
                    # Armazena o total de peças já entregues em devoluções anteriores
                    self.entregues_prev[tam] = acumulado or 0
                    pendente = enviado - (acumulado or 0)
                    if pendente < 0:
                        pendente = 0
                    try:
                        # Atualiza variável StringVar para refletir saldo restante
                        self.faltantes[tam].set(str(pendente))
                    except Exception:
                        pass
            except Exception as e:
                # Se falhar, apenas ignora e mantém faltantes conforme inicial
                print(f"[DEBUG] Falha ao calcular pendentes: {e}")

            self._recalcular()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar detalhes do envio:\n{e}")

    def on_envio_selecionado(self, _event=None):
        """Dispara quando o usuário clica em um envio na lista."""
        sel = self.envios_tree.selection()
        if not sel:
            return

        valores = self.envios_tree.item(sel[0], "values")
        try:
            envio_id = int(valores[0])
        except Exception:
            envio_id = None

        ordem = valores[1] if len(valores) > 1 else ""
        codigo = valores[2] if len(valores) > 2 else ""
        descricao = valores[3] if len(valores) > 3 else ""
        prestador = valores[4] if len(valores) > 4 else ""
        data_envio = valores[5] if len(valores) > 5 else ""
        status = (valores[6] if len(valores) > 6 else "") or ""
        qtd_total = valores[7] if len(valores) > 7 else 0

        # Guarda o envio selecionado
        self.envio_selecionado = {
            "id": envio_id,
            "ordem": ordem,
            "codigo": codigo,
            "descricao": descricao,
            "prestador": prestador,
            "data_envio": data_envio,
            "status": status,
            "qtd_total": qtd_total,
        }

        status = status.strip()
        status_normalizado = status.casefold()
        if status_normalizado.startswith("em conferen"):
            self.envio_selecionado = None
            return

        if status == "Finalizado":
            messagebox.showinfo("Aviso", "Este envio já está FINALIZADO.\nNão é possível registrar novo retorno.")
            return

        # Preenche campos do cabeçalho IMEDIATAMENTE
        self.codigo_entry.configure(state="normal")
        self.codigo_entry.delete(0, tk.END)
        self.codigo_entry.insert(0, codigo)
        self.codigo_entry.configure(state="disabled")

        self.descricao_entry.configure(state="normal")
        self.descricao_entry.delete(0, tk.END)
        self.descricao_entry.insert(0, descricao)
        self.descricao_entry.configure(state="disabled")

        self.ordem_entry.configure(state="normal")
        self.ordem_entry.delete(0, tk.END)
        self.ordem_entry.insert(0, ordem)
        self.ordem_entry.configure(state="disabled")

        # Preenche o prestador
        self.prestador_entry.configure(state="normal")
        self.prestador_entry.delete(0, tk.END)
        self.prestador_entry.insert(0, prestador)
        self.prestador_entry.configure(state="disabled")

        # Data de chegada padrão = hoje
        self.data_chegada_entry.delete(0, tk.END)
        self.data_chegada_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))

        # Limpa campos bancários
        self._limpar_campos_bancarios()

        # Carrega todos os detalhes
        if envio_id is not None:
            self._carregar_detalhes_envio(envio_id)

    def _aviso_envio_em_conferencia(self, _event=None):
        """Exibe aviso ao tentar abrir envio que já está em conferência."""
        sel = self.envios_tree.selection()
        if not sel:
            return

        valores = self.envios_tree.item(sel[0], "values")
        status = (valores[6] if len(valores) > 6 else "") or ""
        if status.strip().casefold().startswith("em conferen"):
            messagebox.showinfo("Aviso", "Esse corte já está em conferência.")

    def _preencher_banco(self, dados, has_titular=False):
        valores = ["", "", "", "", "", ""]
        titular = ""
        if dados:
            d = list(dados)
            if len(d) < 6: d.extend([""] * (6 - len(d)))
            valores = d[:6]
            if has_titular and len(d) > 6: titular = d[6] or ""

        for entry, val in [
            (self.telefone_entry, valores[0]),
            (self.cpf_entry, valores[1]),
            (self.banco_entry, valores[2]),
            (self.agencia_entry, valores[3]),
            (self.conta_entry, valores[4]),
            (self.pix_entry, valores[5]),
            (self.titular_entry, titular)
        ]:
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, val or "")
            entry.configure(state="disabled")

    # ----------------------------- Cálculos -----------------------------
    def _recalcular(self, _event=None):
        total_entregue = 0
        total_copias = 0
        total_regulares = 0
        valor_total = 0.0

        for tam in self.tamanhos:
            # Quantidade informada nesta entrada
            entregue = safe_int(self.entregues[tam].get())
            copias = safe_int(self.copias[tam].get())
            defeitos = safe_int(self.defeitos[tam].get())

            # Atualizar automaticamente o saldo pendente (faltantes)
            # O total enviado por tamanho é armazenado em ``self.enviado_por_tam``.
            # ``self.entregues_prev`` contém o total de peças já devolvidas em
            # retornos anteriores.  Para calcular o saldo pendente, subtraímos
            # o total entregue acumulado e a quantidade informada nesta entrada.
            try:
                enviado_total = self.enviado_por_tam.get(tam, 0)
                acumulado = self.entregues_prev.get(tam, 0)
                pendente = enviado_total - acumulado - entregue
                if pendente < 0:
                    pendente = 0
                # Atualiza o StringVar de faltantes para refletir o saldo atual
                self.faltantes[tam].set(str(pendente))
            except Exception:
                # Se ocorrer qualquer erro, não atualiza o campo faltantes
                pass

            # Regulares = entregue - defeitos (não descontamos faltantes)
            regulares = max(0, entregue - defeitos)
            self.grade_widgets[tam]["regulares"].configure(text=str(regulares))

            # Subtotal = regulares * valor_unitario
            subtotal = regulares * self.valor_por_tam[tam]
            self.grade_widgets[tam]["subtotal"].configure(text=fmt_moeda(subtotal))

            total_entregue += entregue
            total_copias += copias
            total_regulares += regulares
            valor_total += subtotal

        self.lbl_total_entregue.configure(text=str(total_entregue))
        self.lbl_total_copias.configure(text=str(total_copias))
        self.lbl_total_regulares.configure(text=str(total_regulares))
        self.lbl_valor_total.configure(text=fmt_moeda(valor_total))

        # Ajusta o título da coluna conforme entrada parcial
        try:
            if getattr(self, "header_entregue_label", None):
                if total_entregue > 0:
                    self.header_entregue_label.configure(text="ENTR/PARCIAL")
                else:
                    self.header_entregue_label.configure(text="Entregue")
        except Exception:
            pass

    # ----------------------------- Ações -----------------------------
    def registrar_entrada(self):
        """
        Registra a ENTRADA (retorno) de um envio.
        - Permite múltiplas entradas para o mesmo envio (devoluções parciais).
        - Grava cabeçalho em {schema}.controle_retorno_cortes
        - Grava detalhes em {schema}.retorno_detalhes_tamanho
        - Atualiza status do envio em {schema}.envios_cortes
        - Remove o corte da lista (recarrega somente pendentes)
        """
        print("\n================ INÍCIO registrar_entrada() ================\n")

        if not self.envio_selecionado:
            print("[DEBUG] registrar_entrada: nenhum envio selecionado.")
            messagebox.showwarning("Aviso", "Selecione um envio antes de registrar entrada.")
            return

        envio_id = self.envio_selecionado["id"]
        print(f"[DEBUG] registrar_entrada: envio_id selecionado = {envio_id}")

        # ✅ FIX: define schema UMA vez
        schema = get_schema()
        print(f"[DEBUG] schema ativo = {schema}")

        try:
            # 1) Permitir múltiplas entradas para o mesmo envio
            # (devoluções parciais) -> NÃO bloqueia entradas repetidas

            # 2) Coletar dados da tela
            data_chegada_str = (self.data_chegada_entry.get() or "").strip()
            if data_chegada_str:
                try:
                    data_chegada = datetime.strptime(data_chegada_str, "%d/%m/%Y").date()
                except ValueError:
                    print("[WARN] Data inválida no campo data_chegada, usando hoje.")
                    data_chegada = datetime.now().date()
            else:
                data_chegada = datetime.now().date()

            tel_enc = (self.tel_encarregado_entry.get() or "").strip()
            tel_acab = (self.tel_acabamento_entry.get() or "").strip()
            piloto_resumo = (self.piloto_resumo_lbl.cget("text") or "").strip()
            aviamentos = (self.aviamentos_txt.get("1.0", tk.END) or "").strip()
            outros = (self.outros_txt.get("1.0", tk.END) or "").strip()
            obs_geral = (self.obs_geral_txt.get("1.0", tk.END) or "").strip()

            print(f"[DEBUG] data_chegada      = {data_chegada}")
            print(f"[DEBUG] tel_encarregado  = '{tel_enc}'")
            print(f"[DEBUG] tel_acabamento   = '{tel_acab}'")
            print(f"[DEBUG] resumo_piloto    = '{piloto_resumo}'")
            print(f"[DEBUG] aviamentos       = '{aviamentos}'")
            print(f"[DEBUG] outros           = '{outros}'")
            print(f"[DEBUG] observacoes      = '{obs_geral}'")

            # 3) Calcular totais a partir da grade por tamanho
            total_entregue = 0
            total_copias = 0
            total_defeitos = 0
            total_faltantes = 0
            total_regulares = 0
            valor_total = 0.0

            print("\n[DEBUG] ---- DETALHES POR TAMANHO ----")
            for tam in self.tamanhos:
                entregue = safe_int(self.entregues[tam].get())
                copias = safe_int(self.copias[tam].get())
                defeitos = safe_int(self.defeitos[tam].get())
                faltantes = safe_int(self.faltantes[tam].get())

                # Regulares desta entrada: entregue - defeitos (não subtrai faltantes)
                regulares = max(0, entregue - defeitos)

                valor_unit = float(self.valor_por_tam.get(tam, 0.0) or 0.0)
                subtotal = regulares * valor_unit

                print(
                    f"[DEBUG] TAM={tam} | entregues={entregue} | copias={copias} | "
                    f"defeitos={defeitos} | faltantes={faltantes} | regulares={regulares} | "
                    f"valor_unit={valor_unit} | subtotal={subtotal}"
                )

                total_entregue += entregue
                total_copias += copias
                total_defeitos += defeitos
                total_faltantes += faltantes
                total_regulares += regulares
                valor_total += subtotal

            print("\n[DEBUG] ---- TOTAIS CALCULADOS ----")
            print(f"total_entregue  = {total_entregue}")
            print(f"total_copias    = {total_copias}")
            print(f"total_defeitos  = {total_defeitos}")
            print(f"total_faltantes = {total_faltantes}")
            print(f"total_regulares = {total_regulares}")
            print(f"valor_total     = {valor_total}\n")

            if (
                total_entregue == 0
                and total_copias == 0
                and total_defeitos == 0
                and total_faltantes == 0
            ):
                if not messagebox.askyesno(
                    "Salvar corte completo?",
                    "Nenhuma quantidade informada. Deseja salvar corte completo?",
                ):
                    return

            # 4) Inserir cabeçalho em controle_retorno_cortes
            print("[DEBUG] INSERT em controle_retorno_cortes...")
            result = db.fetch_one(
                f"""
                INSERT INTO {schema}.controle_retorno_cortes
                (envio_id, data_chegada, telefone_encarregado, telefone_acabamento,
                 resumo_piloto, aviamentos_recebidos, outros_recebidos, observacoes_gerais,
                 total_entregue, total_copias, total_defeitos, total_faltantes,
                 total_regulares, valor_total)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (
                    envio_id, data_chegada, tel_enc, tel_acab,
                    piloto_resumo, aviamentos, outros, obs_geral,
                    total_entregue, total_copias, total_defeitos,
                    total_faltantes, total_regulares, valor_total
                )
            )
            retorno_id = result["id"] if result else None
            print(f"[DEBUG] controle_retorno_cortes.id gerado = {retorno_id}")

            # 5) Gravar detalhes por tamanho em retorno_detalhes_tamanho
            # Mantém histórico: NÃO faz DELETE
            print("[DEBUG] Inserindo novos detalhes em retorno_detalhes_tamanho...")
            for tam in self.tamanhos:
                entregue = safe_int(self.entregues[tam].get())
                copias = safe_int(self.copias[tam].get())
                defeitos = safe_int(self.defeitos[tam].get())
                faltantes = safe_int(self.faltantes[tam].get())

                regulares = max(0, entregue - defeitos)
                valor_unit = float(self.valor_por_tam.get(tam, 0.0) or 0.0)
                subtotal = regulares * valor_unit

                # Só grava se houver alguma quantidade nesta entrada
                if entregue > 0 or copias > 0 or defeitos > 0 or faltantes > 0:
                    print(
                        f"[DEBUG] INSERT retorno_detalhes_tamanho | envio_id={envio_id}, "
                        f"tam={tam}, ent={entregue}, copias={copias}, "
                        f"defeitos={defeitos}, faltantes={faltantes}, "
                        f"regulares={regulares}, subtotal={subtotal}"
                    )
                    db.execute(
                        f"""
                        INSERT INTO {schema}.retorno_detalhes_tamanho
                        (envio_id, tamanho, entregue, copias, defeitos, faltantes, regulares, subtotal)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (envio_id, tam, entregue, copias, defeitos, faltantes, regulares, subtotal)
                    )

            # 6) Atualizar status do envio na tabela envios_cortes
            # Verifica se total entregue acumulado >= enviado por tamanho
            try:
                sql_orig = f"""
                    SELECT COALESCE(qtd_pp,0) AS pp, COALESCE(qtd_p,0) AS p, COALESCE(qtd_m,0) AS m,
                           COALESCE(qtd_g,0) AS g, COALESCE(qtd_gg,0) AS gg,
                           COALESCE(qtd_g1,0) AS g1, COALESCE(qtd_g2,0) AS g2, COALESCE(qtd_g3,0) AS g3
                      FROM {schema}.envios_cortes
                     WHERE id = %s
                """
                orig = db.fetch_one(sql_orig, (envio_id,)) or {}

                sql_sum = f"""
                    SELECT tamanho, SUM(entregue) AS total_entregue
                      FROM {schema}.retorno_detalhes_tamanho
                     WHERE envio_id = %s
                     GROUP BY tamanho
                """
                soma = db.fetch_all(sql_sum, (envio_id,)) or []
                soma_map = {str(r["tamanho"]).upper(): int(r["total_entregue"] or 0) for r in soma}

                mapa_env = {
                    "PP": orig.get("pp", 0),
                    "P": orig.get("p", 0),
                    "M": orig.get("m", 0),
                    "G": orig.get("g", 0),
                    "GG": orig.get("gg", 0),
                    "G1": orig.get("g1", 0),
                    "G2": orig.get("g2", 0),
                    "G3": orig.get("g3", 0),
                }

                finalizado = True
                for tam, qtd_env in mapa_env.items():
                    entregues_tot = soma_map.get(tam, 0)
                    if entregues_tot < int(qtd_env or 0):
                        finalizado = False
                        break

                # ✅ PADRÃO sem acento para bater com filtros do sistema
                novo_status = "Finalizado" if finalizado else "Em Conferencia"
                print(f"[DEBUG] Atualizando status do envio {envio_id} para '{novo_status}'...")

                db.execute(
                    f"UPDATE {schema}.envios_cortes SET status_envio = %s WHERE id = %s",
                    (novo_status, envio_id,)
                )

            except Exception as e:
                print(f"[WARN] Falha ao atualizar status do envio: {e}")

            # 7) Zerar pilotos se marcado (baixa de piloto)
            if self.piloto_entregue_var.get():
                print("[DEBUG] piloto_entregue_var = True -> zerando quantidade_pilotos em envio_detalhes_tamanho...")

                db.execute(
                    f"""
                    UPDATE {schema}.envio_detalhes_tamanho
                       SET quantidade_pilotos = 0
                     WHERE envio_id = %s
                       AND quantidade_pilotos > 0
                    """,
                    (envio_id,)
                )

            print("\n================ FIM registrar_entrada() (SUCESSO) ================\n")

            # 8) Limpar seleção e recarregar somente pendentes
            self._limpar_campos()
            self.carregar_envios_pendentes()

            messagebox.showinfo("Sucesso", "Entrada registrada com sucesso!")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ERRO] registrar_entrada: {e}")
            messagebox.showerror("Erro", f"Falha ao registrar entrada: {e}")

    def pre_visualizar_pdf(self):
        messagebox.showinfo("Pré-visualizar PDF", "Funcionalidade de pré-visualização será implementada aqui.")

    def exportar_pdf(self):
        messagebox.showinfo("Exportar PDF", "Funcionalidade de exportação PDF será implementada aqui.")

    def limpar_campos(self):
        self._limpar_campos()

    def _limpar_campos(self):
        self.envio_selecionado = None
        self._prestador_id = None
        self._prestador_nome = ""
        self._tipo_servico = ""

        for t in self.tamanhos:
            self.entregues[t].set(0)
            self.copias[t].set(0)
            self.defeitos[t].set(0)
            self.faltantes[t].set(0)
            self.enviado_por_tam[t] = 0
            self.valor_por_tam[t] = 0.0
            self.pilotos_por_tam[t] = 0
            self.grade_widgets[t]["enviado"].configure(text="0")
            self.grade_widgets[t]["regulares"].configure(text="0")
            self.grade_widgets[t]["valor"].configure(text=fmt_moeda(0))
            self.grade_widgets[t]["subtotal"].configure(text=fmt_moeda(0))

        self.lbl_total_entregue.configure(text="0")
        self.lbl_total_copias.configure(text="0")
        self.lbl_total_regulares.configure(text="0")
        self.lbl_valor_total.configure(text=fmt_moeda(0))
        if getattr(self, "header_entregue_label", None):
            self.header_entregue_label.configure(text="Entregue")

        self.prestador_entry.configure(state="normal")
        self.prestador_entry.delete(0, tk.END)
        self.prestador_entry.configure(state="disabled")
        self.servico_entry.configure(state="normal")
        self.servico_entry.delete(0, tk.END)
        self.servico_entry.configure(state="disabled")
        self.telefone_entry.configure(state="normal")
        self.telefone_entry.delete(0, tk.END)
        self.telefone_entry.configure(state="disabled")
        self.cpf_entry.configure(state="normal")
        self.cpf_entry.delete(0, tk.END)
        self.cpf_entry.configure(state="disabled")
        self.banco_entry.configure(state="normal")
        self.banco_entry.delete(0, tk.END)
        self.banco_entry.configure(state="disabled")
        self.agencia_entry.configure(state="normal")
        self.agencia_entry.delete(0, tk.END)
        self.agencia_entry.configure(state="disabled")
        self.conta_entry.configure(state="normal")
        self.conta_entry.delete(0, tk.END)
        self.conta_entry.configure(state="disabled")
        self.pix_entry.configure(state="normal")
        self.pix_entry.delete(0, tk.END)
        self.pix_entry.configure(state="disabled")
        self.titular_entry.configure(state="normal")
        self.titular_entry.delete(0, tk.END)
        self.titular_entry.configure(state="disabled")

        self.codigo_entry.configure(state="normal")
        self.codigo_entry.delete(0, tk.END)
        self.codigo_entry.configure(state="disabled")
        self.descricao_entry.configure(state="normal")
        self.descricao_entry.delete(0, tk.END)
        self.descricao_entry.configure(state="disabled")
        self.ordem_entry.configure(state="normal")
        self.ordem_entry.delete(0, tk.END)
        self.ordem_entry.configure(state="disabled")

        self.tel_encarregado_entry.delete(0, tk.END)
        self.tel_acabamento_entry.delete(0, tk.END)
        self.data_chegada_entry.delete(0, tk.END)
        self.data_chegada_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))

        self.piloto_resumo_lbl.configure(text="Nenhum.")
        self.aviamentos_txt.delete("1.0", tk.END)
        self.outros_txt.delete("1.0", tk.END)
        self.obs_geral_txt.delete("1.0", tk.END)
        self.piloto_entregue_var.set(True)

    def _limpar_campos_bancarios(self):
        """Limpa todos os campos bancários."""
        campos_bancarios = [
            self.telefone_entry,
            self.cpf_entry,
            self.banco_entry,
            self.agencia_entry,
            self.conta_entry,
            self.pix_entry,
            self.titular_entry
        ]

        for entry in campos_bancarios:
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.configure(state="disabled")

# ============================== MAIN ==============================
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("Sistema de Controle de Mão de Obra — Retorno de Cortes")
    root.geometry("1400x900")
    app = RetornoCortes(root)
    root.mainloop()
