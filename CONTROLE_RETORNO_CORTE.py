# -*- coding: utf-8 -*-
import BANCO_DE_DADOS_PG as db
import os
import json
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk

# ---------- CONFIGURAÇÃO ----------
LOGO_PATH = os.path.join(os.path.dirname(__file__), "LOGO.jpg")


# ============================== Utils ==============================
def safe_int(v, default=0):
    try:
        if v is None: return default
        s = str(v).strip()
        if not s: return default
        return int(float(s.replace(".", "").replace(",", ".")))
    except Exception:
        return default


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


# ============================== Tela ==============================
class RetornoCortes(ctk.CTkFrame):
    tamanhos = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]

    def __init__(self, master, sistema=None):
        super().__init__(master)
        self.master = master
        self.sistema = sistema

        # === APLICAR CORES AO FRAME PRINCIPAL ===
        # Usando o mesmo padrão de cores do CADASTRO_DE_CORTE
        self.obter_cores_por_tema()
        self.configure(fg_color=self.cor_fundo)

        self.envio_selecionado = None
        self._prestador_id = None
        self._prestador_nome = ""
        self._tipo_servico = ""

        # estados grade
        self.entregues = {t: ctk.IntVar(value=0) for t in self.tamanhos}
        self.copias = {t: ctk.IntVar(value=0) for t in self.tamanhos}
        self.defeitos = {t: ctk.IntVar(value=0) for t in self.tamanhos}
        self.faltantes = {t: ctk.IntVar(value=0) for t in self.tamanhos}

        self.enviado_por_tam = {t: 0 for t in self.tamanhos}
        self.valor_por_tam = {t: 0.0 for t in self.tamanhos}

        self.pilotos_por_tam = {t: 0 for t in self.tamanhos}
        self.piloto_entregue_var = ctk.BooleanVar(value=True)
        self.incluir_conferencia_var = ctk.BooleanVar(value=True)
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

        for h, w in [("Tam.", 60), ("Enviado", 80), ("Entregue", 90), ("Cópias", 80), ("Defeito", 80), ("Faltante", 80),
                     ("Regulares (pagas)", 120), ("Valor/Peça", 100), ("Subtotal", 110)]:
            ctk.CTkLabel(header_g, text=h, width=w, anchor="center",
                         text_color=self.cor_texto).pack(side="left", padx=2)

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
        try:
            termo = (self.busca_entry.get() or "").strip()
            self.envios_tree.delete(*self.envios_tree.get_children())

            if termo:
                result = db.fetch_all("""
                                      SELECT id,
                                             ordem_corte,
                                             codigo_corte,
                                             descricao_corte,
                                             destino,
                                             data_envio,
                                             status,
                                             servico,
                                             COALESCE((SELECT SUM(COALESCE(quantidade_pilotos, 0))
                                                       FROM envio_detalhes_tamanho edt
                                                       WHERE edt.envio_id = controle_envio_cortes.id), 0) AS qtd_total
                                      FROM controle_envio_cortes
                                      WHERE (status = 'Enviado' OR (status = 'Em Conferência' AND %s))
                                        AND (ordem_corte ILIKE %s OR codigo_corte ILIKE %s OR descricao_corte ILIKE %s)
                                      ORDER BY data_envio DESC
                                      """, (True if self.incluir_conferencia_var.get() else False,
                                            f"%{termo}%", f"%{termo}%", f"%{termo}%"))
            else:
                result = db.fetch_all("""
                                      SELECT id,
                                             ordem_corte,
                                             codigo_corte,
                                             descricao_corte,
                                             destino,
                                             data_envio,
                                             status,
                                             servico,
                                             COALESCE((SELECT SUM(COALESCE(quantidade_pilotos, 0))
                                                       FROM envio_detalhes_tamanho edt
                                                       WHERE edt.envio_id = controle_envio_cortes.id), 0) AS qtd_total
                                      FROM controle_envio_cortes
                                      WHERE status = 'Enviado'
                                         OR (status = 'Em Conferência' AND %s)
                                      ORDER BY data_envio DESC LIMIT 60
                                      """, (True if self.incluir_conferencia_var.get() else False,))

            for i, row in enumerate(result):
                tag = ()
                try:
                    st = (row["status"] or "").strip()
                    if st == "Em Conferência":
                        tag = ('status_conferencia',)
                    elif st == "Finalizado":
                        tag = ('status_finalizado',)
                except Exception:
                    pass

                # Adicionar tag para linhas alternadas
                row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                if tag:
                    tag = tag + (row_tag,)
                else:
                    tag = (row_tag,)

                self.envios_tree.insert("", "end",
                                        values=(row["id"], row["ordem_corte"], row["codigo_corte"],
                                                row["descricao_corte"],
                                                row["destino"], row["data_envio"], row["status"], row["qtd_total"]),
                                        tags=tag)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar envios: {e}")

    def on_envio_selecionado(self, _event=None):
        sel = self.envios_tree.selection()
        if not sel: return
        v = self.envios_tree.item(sel[0], "values")

        self.envio_selecionado = {
            "id": v[0], "ordem": v[1], "codigo": v[2], "descricao": v[3],
            "prestador": v[4], "data_envio": v[5]
        }

        try:
            status = (v[6] or "").strip()
        except Exception:
            status = ""

        if status == "Em Conferência":
            self.envio_selecionado = {
                "id": v[0], "ordem": v[1], "codigo": v[2], "descricao": v[3],
                "prestador": v[4], "data_envio": v[5], "status": status
            }
            self._limpar_campos()
            return

        if status == "Finalizado":
            messagebox.showinfo("Aviso", "Corte finalizado — não é possível registrar nova entrada.")
            return

        self.envio_selecionado = {
            "id": v[0], "ordem": v[1], "codigo": v[2], "descricao": v[3],
            "prestador": v[4], "data_envio": v[5], "status": status
        }
        self._tipo_servico = self._buscar_servico(self.envio_selecionado["id"]) or ""
        self._prestador_nome = self.envio_selecionado["prestador"] or ""

        self._preencher_header_envio()
        self._carregar_detalhes_envio()
        self._carregar_prestador_por_nome(self._prestador_nome)

    def _buscar_servico(self, envio_id):
        try:
            result = db.fetch_one("SELECT servico FROM controle_envio_cortes WHERE id=%s LIMIT 1", (envio_id,))
            return result["servico"] if result else ""
        except Exception:
            return ""

    def _preencher_header_envio(self):
        self.prestador_entry.configure(state="normal")
        self.prestador_entry.delete(0, tk.END)
        self.prestador_entry.insert(0, self._prestador_nome or "")
        self.prestador_entry.configure(state="disabled")
        self.servico_entry.configure(state="normal")
        self.servico_entry.delete(0, tk.END)
        self.servico_entry.insert(0, self._tipo_servico or "")
        self.servico_entry.configure(state="disabled")

        self.codigo_entry.configure(state="normal")
        self.codigo_entry.delete(0, tk.END)
        self.codigo_entry.insert(0, self.envio_selecionado["codigo"])
        self.codigo_entry.configure(state="disabled")
        self.descricao_entry.configure(state="normal")
        self.descricao_entry.delete(0, tk.END)
        self.descricao_entry.insert(0, self.envio_selecionado["descricao"])
        self.descricao_entry.configure(state="disabled")
        self.ordem_entry.configure(state="normal")
        self.ordem_entry.delete(0, tk.END)
        self.ordem_entry.insert(0, self.envio_selecionado["ordem"])
        self.ordem_entry.configure(state="disabled")

    def _carregar_prestador_por_nome(self, nome):
        self._prestador_id = None
        nome = (nome or "").strip()
        if not nome:
            self._preencher_banco(None)
            return

        try:
            tit_col = _coluna_titular()

            base = "id, COALESCE(telefone,''), COALESCE(cpf,''), COALESCE(banco,''), COALESCE(agencia,''), COALESCE(conta,''), COALESCE(pix,'')"
            select_full = f"{base}, COALESCE({tit_col},'')" if tit_col else f"{base}, ''"

            result = db.fetch_all(f"""
                SELECT {select_full}
                FROM cadastro_faccoes
                WHERE TRIM(LOWER(nome)) = TRIM(LOWER(%s))
                ORDER BY id DESC LIMIT 1
            """, (nome,))

            if not result:
                result = db.fetch_all(
                    f"SELECT {select_full} FROM cadastro_faccoes WHERE nome ILIKE %s ORDER BY id DESC LIMIT 1",
                    (f"%{nome}%",))

            row = result[0] if result else None
            self._prestador_id = row["id"] if row else None

            # endereço (opcional)
            end_col = _coluna_endereco()
            self._prest_endereco = ""
            if end_col and self._prestador_id:
                result = db.fetch_one(f"SELECT COALESCE({end_col},'') FROM cadastro_faccoes WHERE id=%s LIMIT 1",
                                      (self._prestador_id,))
                self._prest_endereco = (result[list(result.keys())[0]] if result else "") or ""

            if row:
                dados = [row[key] for key in row.keys() if key != "id"]
                self._preencher_banco(dados, True)
            else:
                self._preencher_banco(None)

        except Exception as e:
            self._preencher_banco(None)
            messagebox.showerror("Erro", f"Falha ao carregar dados do prestador: {e}")

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

    def _carregar_detalhes_envio(self):
        envio_id = self.envio_selecionado["id"]
        try:
            # Limpar dados anteriores
            for t in self.tamanhos:
                self.enviado_por_tam[t] = 0
                self.valor_por_tam[t] = 0.0
                self.pilotos_por_tam[t] = 0
                self.entregues[t].set(0)
                self.copias[t].set(0)
                self.defeitos[t].set(0)
                self.faltantes[t].set(0)
                self.grade_widgets[t]["enviado"].configure(text="0")
                self.grade_widgets[t]["regulares"].configure(text="0")
                self.grade_widgets[t]["valor"].configure(text=fmt_moeda(0))
                self.grade_widgets[t]["subtotal"].configure(text=fmt_moeda(0))

            # Carregar detalhes do envio - CORREÇÃO AQUI
            result = db.fetch_all("""
                                  SELECT tamanho, COALESCE(quantidade_pilotos, 0) as quantidade_pilotos
                                  FROM envio_detalhes_tamanho
                                  WHERE envio_id = %s
                                  """, (envio_id,))

            for row in result:
                tam = row["tamanho"]
                if tam not in self.tamanhos: continue
                self.pilotos_por_tam[tam] = row["quantidade_pilotos"] or 0
                self.enviado_por_tam[tam] = self.pilotos_por_tam[tam]  # Usando pilotos como quantidade enviada
                self.grade_widgets[tam]["enviado"].configure(text=str(self.pilotos_por_tam[tam] or 0))

            # Carregar valores unitários da tabela controle_envio_cortes
            result_valores = db.fetch_one("""
                                          SELECT pp,
                                                 p,
                                                 m,
                                                 g,
                                                 gg,
                                                 g1,
                                                 g2,
                                                 g3
                                          FROM controle_envio_cortes
                                          WHERE id = %s
                                          """, (envio_id,))

            if result_valores:
                # Mapear os valores por tamanho
                valores_map = {
                    "PP": result_valores["pp"] or 0.0,
                    "P": result_valores["p"] or 0.0,
                    "M": result_valores["m"] or 0.0,
                    "G": result_valores["g"] or 0.0,
                    "GG": result_valores["gg"] or 0.0,
                    "G1": result_valores["g1"] or 0.0,
                    "G2": result_valores["g2"] or 0.0,
                    "G3": result_valores["g3"] or 0.0
                }

                for tam in self.tamanhos:
                    self.valor_por_tam[tam] = float(valores_map.get(tam, 0.0))
                    self.grade_widgets[tam]["valor"].configure(text=fmt_moeda(self.valor_por_tam[tam]))

            # Carregar dados de piloto
            result = db.fetch_all("""
                                  SELECT resumo_piloto, aviamentos_recebidos, outros_recebidos, observacoes_gerais
                                  FROM controle_retorno_cortes
                                  WHERE envio_id = %s
                                  """, (envio_id,))

            if result:
                row = result[0]
                self.piloto_resumo_lbl.configure(text=row["resumo_piloto"] or "Nenhum.")
                self.aviamentos_txt.delete("1.0", tk.END)
                self.aviamentos_txt.insert("1.0", row["aviamentos_recebidos"] or "")
                self.outros_txt.delete("1.0", tk.END)
                self.outros_txt.insert("1.0", row["outros_recebidos"] or "")
                self.obs_geral_txt.delete("1.0", tk.END)
                self.obs_geral_txt.insert("1.0", row["observacoes_gerais"] or "")
            else:
                self.piloto_resumo_lbl.configure(text="Nenhum.")
                self.aviamentos_txt.delete("1.0", tk.END)
                self.outros_txt.delete("1.0", tk.END)
                self.obs_geral_txt.delete("1.0", tk.END)

            # Carregar dados de retorno se existir
            result = db.fetch_all("""
                                  SELECT tamanho, entregue, copias, defeitos, faltantes
                                  FROM retorno_detalhes_tamanho
                                  WHERE envio_id = %s
                                  """, (envio_id,))

            for row in result:
                tam = row["tamanho"]
                if tam not in self.tamanhos: continue
                self.entregues[tam].set(row["entregue"] or 0)
                self.copias[tam].set(row["copias"] or 0)
                self.defeitos[tam].set(row["defeitos"] or 0)
                self.faltantes[tam].set(row["faltantes"] or 0)

            self._recalcular()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar detalhes do envio: {e}")

    # ----------------------------- Cálculos -----------------------------
    def _recalcular(self, _event=None):
        total_entregue = 0
        total_copias = 0
        total_regulares = 0
        valor_total = 0.0

        for tam in self.tamanhos:
            entregue = safe_int(self.entregues[tam].get())
            copias = safe_int(self.copias[tam].get())
            defeitos = safe_int(self.defeitos[tam].get())
            faltantes = safe_int(self.faltantes[tam].get())

            # Regulares = entregue - defeitos - faltantes
            regulares = max(0, entregue - defeitos - faltantes)
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

    # ----------------------------- Ações -----------------------------
    def registrar_entrada(self):
        if not self.envio_selecionado:
            messagebox.showwarning("Aviso", "Selecione um envio antes de registrar entrada.")
            return

        envio_id = self.envio_selecionado["id"]
        try:
            # Verificar se já existe retorno
            result = db.fetch_one("SELECT id FROM controle_retorno_cortes WHERE envio_id=%s LIMIT 1", (envio_id,))
            retorno_id = result["id"] if result else None

            # Dados principais
            data_chegada_str = self.data_chegada_entry.get().strip()
            data_chegada = datetime.strptime(data_chegada_str, "%d/%m/%Y") if data_chegada_str else datetime.now()

            tel_enc = self.tel_encarregado_entry.get().strip()
            tel_acab = self.tel_acabamento_entry.get().strip()

            piloto_resumo = self.piloto_resumo_lbl.cget("text") or "Nenhum."
            aviamentos = self.aviamentos_txt.get("1.0", tk.END).strip()
            outros = self.outros_txt.get("1.0", tk.END).strip()
            obs_geral = self.obs_geral_txt.get("1.0", tk.END).strip()

            # Calcular totais
            total_entregue = 0
            total_copias = 0
            total_defeitos = 0
            total_faltantes = 0
            total_regulares = 0
            valor_total = 0.0
            for tam in self.tamanhos:
                entregue = safe_int(self.entregues[tam].get())
                copias = safe_int(self.copias[tam].get())
                defeitos = safe_int(self.defeitos[tam].get())
                faltantes = safe_int(self.faltantes[tam].get())
                regulares = max(0, entregue - defeitos - faltantes)
                subtotal = regulares * self.valor_por_tam[tam]

                total_entregue += entregue
                total_copias += copias
                total_defeitos += defeitos
                total_faltantes += faltantes
                total_regulares += regulares
                valor_total += subtotal

            # Inserir/atualizar controle_retorno_cortes
            if retorno_id:
                db.execute("""
                    UPDATE controle_retorno_cortes
                    SET data_chegada=%s, telefone_encarregado=%s, telefone_acabamento=%s,
                        resumo_piloto=%s, aviamentos_recebidos=%s, outros_recebidos=%s, observacoes_gerais=%s,
                        total_entregue=%s, total_copias=%s, total_defeitos=%s, total_faltantes=%s,
                        total_regulares=%s, valor_total=%s
                    WHERE id=%s
                """, (data_chegada, tel_enc, tel_acab, piloto_resumo, aviamentos, outros, obs_geral,
                      total_entregue, total_copias, total_defeitos, total_faltantes, total_regulares, valor_total,
                      retorno_id))
            else:
                result = db.fetch_one("""
                    INSERT INTO controle_retorno_cortes
                    (envio_id, data_chegada, telefone_encarregado, telefone_acabamento,
                     resumo_piloto, aviamentos_recebidos, outros_recebidos, observacoes_gerais,
                     total_entregue, total_copias, total_defeitos, total_faltantes,
                     total_regulares, valor_total)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                """, (envio_id, data_chegada, tel_enc, tel_acab, piloto_resumo, aviamentos, outros, obs_geral,
                      total_entregue, total_copias, total_defeitos, total_faltantes, total_regulares, valor_total))
                retorno_id = result["id"] if result else None

            # Inserir/atualizar retorno_detalhes_tamanho
            db.execute("DELETE FROM retorno_detalhes_tamanho WHERE envio_id=%s", (envio_id,))
            for tam in self.tamanhos:
                entregue = safe_int(self.entregues[tam].get())
                copias = safe_int(self.copias[tam].get())
                defeitos = safe_int(self.defeitos[tam].get())
                faltantes = safe_int(self.faltantes[tam].get())
                regulares = max(0, entregue - defeitos - faltantes)
                subtotal = regulares * self.valor_por_tam[tam]

                if entregue > 0 or copias > 0 or defeitos > 0 or faltantes > 0:
                    db.execute("""
                        INSERT INTO retorno_detalhes_tamanho
                        (envio_id, tamanho, entregue, copias, defeitos, faltantes, regulares, subtotal)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (envio_id, tam, entregue, copias, defeitos, faltantes, regulares, subtotal))

            # Atualizar status do envio para "Em Conferência"
            db.execute("UPDATE controle_envio_cortes SET status='Em Conferência' WHERE id=%s", (envio_id,))

            # Dar baixa no piloto se marcado
            if self.piloto_entregue_var.get():
                db.execute("""
                    UPDATE envio_detalhes_tamanho
                    SET quantidade_pilotos = 0
                    WHERE envio_id = %s AND quantidade_pilotos > 0
                """, (envio_id,))

            messagebox.showinfo("Sucesso", "Entrada registrada com sucesso!")
            self.carregar_envios_pendentes()

        except Exception as e:
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


# ============================== MAIN ==============================
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.title("Sistema de Controle de Mão de Obra — Retorno de Cortes")
    root.geometry("1400x900")
    app = RetornoCortes(root)
    root.mainloop()