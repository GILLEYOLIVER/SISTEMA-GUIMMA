# -*- coding: utf-8 -*-
"""
ENVIO_CORTE.py — Envio de Cortes / Controle de Mão de Obra
"""
import os
import webbrowser
import tempfile
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import calendar as _cal
import os
import sys
import subprocess
import webbrowser
import tempfile
from datetime import datetime


# Importação do módulo PostgreSQL
try:
    from BANCO_DE_DADOS_PG import get_conn, get_schema

    PG_OK = True
except Exception as e:
    print(f"Erro ao importar módulo PostgreSQL: {e}")
    PG_OK = False

# ---------- LOGO (UI e PDF) ----------
LOGO_PATH = os.path.join(os.path.dirname(__file__), "LOGO.jpg")
try:
    from PIL import Image

    PIL_OK = True
except Exception:
    PIL_OK = False

SERVICOS_FIXOS = ["Facção", "Bordado", "Caseador", "Botões", "Estamparia", "Interna", "Tingimento", "Outros Trabalhos"]


# ============================== Utils ==============================
def safe_int(v, default=0):
    try:
        if v is None:
            return default
        s = str(v).strip()
        if not s:
            return default
        return int(float(s.replace(".", "").replace(",", ".")))
    except Exception:
        return default


def parse_valor(s):
    """'1.234,56' | '1234.56' | '' -> float"""
    try:
        s = (s or "").strip().replace("R$", "").replace(" ", "")
        if not s:
            return 0.0
        return float(s.replace(".", "").replace(",", "."))
    except Exception:
        return 0.0


def fmt_moeda(v):
    s = f"{float(v):,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def today_str():
    return datetime.now().strftime("%d/%m/%Y")


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


# ============================== Página ==============================
class EnvioCortes(ctk.CTkFrame):
    tamanhos = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]

    def __init__(self, master, sistema=None):
        super().__init__(master)
        self.master = master
        self.sistema = sistema

        # === CORREÇÃO: APLICAR CORES AO FRAME PRINCIPAL ===
        # Herda as cores e tema do sistema principal
        self.cor_fundo = getattr(sistema, "cor_fundo", "#020617")
        self.cor_primaria = getattr(sistema, "cor_primaria", "#1f2937")
        self.cor_secundaria = getattr(sistema, "cor_secundaria", "#111827")
        self.cor_terciaria = getattr(sistema, "cor_terciaria", "#0b1220")
        self.cor_texto = getattr(sistema, "cor_texto", "#e5e7eb")
        self.cor_borda = getattr(sistema, "cor_borda", "#273244")
        self.cor_hover = getattr(sistema, "cor_hover", "#334155")
        self.cor_sucesso = getattr(sistema, "cor_sucesso", "#22c55e")
        self.cor_alerta = getattr(sistema, "cor_alerta", "#ef4444")
        self.cor_selecao = getattr(sistema, "cor_selecao", "#2563eb")

        # APLICAR COR DE FUNDO AO FRAME PRINCIPAL
        self.configure(fg_color=self.cor_fundo)
        # ==================================================

        # Verificar se o PostgreSQL está disponível
        if not PG_OK:
            messagebox.showerror("Erro", "Módulo PostgreSQL não disponível. Verifique a configuração.")
            return

        # ---- Estados ----
        self._prestadores_full = []
        self._prestador_id = None
        self._prestador_nome = ""
        self._prestador_map = {}
        self._tipo_servico = "Facção"
        self.corte_selecionado = None

        # Estado para filtro de serviços
        self.filtro_servico_var = tk.StringVar(value="Todos")
        self.prestadores_filtrados = []

        self.configuracao = {"label_empresa": "Empresa:", "label_telefone": "Telefone empresa:"}

        # Variáveis da grade
        # StringVar evita exceções do Tkinter quando o campo fica vazio
        self.quantidades = {t: tk.StringVar(value="0") for t in self.tamanhos}
        self.pilotos = {t: tk.StringVar(value="0") for t in self.tamanhos}
        self.valores = {t: tk.StringVar(value="") for t in self.tamanhos}
        self._total_por_tam = {t: 0 for t in self.tamanhos}
        self._piloto_prev = {t: 0 for t in self.tamanhos}

        # Valor único
        self.valor_unico_var = tk.IntVar(value=0)

        # Piloto (tam + qtd)
        self.piloto_tam_var = tk.StringVar(value=self.tamanhos[0])
        self.piloto_qtd_var = tk.StringVar(value="0")

        # Esquema de cadastro_de_corte detectado
        self._corte_schema = None

        self.pack(fill="both", expand=True)
        self._build_ui()
        self._resolver_corte_schema()
        self._carregar_prestadores()
        self._buscar_cortes_iniciais()

    # ----------------------------- UI -----------------------------
    def _build_ui(self):
        # Frame principal com tema
        main = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        main.pack(fill="both", expand=True, padx=8, pady=4)

        # Cabeçalho + logo
        header = ctk.CTkFrame(main, fg_color=self.cor_fundo, height=40)
        header.pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(
            header,
            text="CONTROLE DE MÃO DE OBRA — Envio de Cortes",
            font=("Arial", 14, "bold"),
            text_color=self.cor_texto
        ).pack(side="left", padx=(0, 6))

        if PIL_OK and os.path.exists(LOGO_PATH):
            img = Image.open(LOGO_PATH)
            w, h = img.size
            tw = 90
            th = int(h * (tw / w))
            self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(tw, th))
            ctk.CTkLabel(header, image=self.logo_img, text="").pack(side="right")

        # =========== SEÇÃO 1: BUSCA DE CORTE ===========
        l_busca = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        l_busca.pack(fill="x", pady=2)

        ctk.CTkLabel(
            l_busca,
            text="Buscar Corte:",
            width=100,
            text_color=self.cor_texto
        ).pack(side="left", padx=(0, 4))

        self.busca_entry = ctk.CTkEntry(
            l_busca,
            width=280,
            placeholder_text="Número, código ou descrição",
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            placeholder_text_color="#888888"
        )
        self.busca_entry.pack(side="left")
        self.busca_entry.bind("<Return>", lambda e: self.buscar_cortes())

        ctk.CTkButton(
            l_busca,
            text="Buscar",
            width=80,
            command=self.buscar_cortes,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=4)

        # =========== SEÇÃO 2: DADOS DO PRESTADOR ===========
        prest = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        prest.pack(fill="x", pady=2)

        linha = ctk.CTkFrame(prest, fg_color=self.cor_fundo)
        linha.pack(fill="x", pady=(2, 1))

        # Filtro de serviço oculto
        hidden = ctk.CTkFrame(prest, fg_color=self.cor_fundo)
        hidden.pack_forget()
        self.filtro_servico_cb = ctk.CTkComboBox(
            hidden,
            width=100,
            values=["Todos"],
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover
        )
        self.filtro_servico_cb.set("Todos")

        # Costureira
        ctk.CTkLabel(
            linha,
            text="Costureira:",
            width=80,
            text_color=self.cor_texto
        ).pack(side="left", padx=(2, 4))

        self.prestador_busca_cb = ctk.CTkComboBox(
            linha,
            width=350,
            values=["Digite para buscar..."],
            state="normal",
            command=self._on_prestador_change,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover
        )
        self.prestador_busca_cb.set("")
        self.prestador_busca_cb.pack(side="left")

        # Eventos do combobox de costureira
        self.prestador_busca_cb.bind("<KeyRelease>", lambda e: self._filtrar_combo_prestador())
        self.prestador_busca_cb.bind("<Return>", self._on_costureira_selected)
        self.prestador_busca_cb.bind("<FocusOut>", self._on_costureira_selected)
        self.prestador_busca_cb.bind(
            "<<ComboboxSelected>>",
            lambda e: self._on_prestador_change(self.prestador_busca_cb.get())
        )

        # Tipo de Serviço
        ctk.CTkLabel(
            linha,
            text="Serviço:",
            width=70,
            text_color=self.cor_texto
        ).pack(side="left", padx=(12, 4))

        self.tipo_cb = ctk.CTkComboBox(
            linha,
            width=150,
            values=SERVICOS_FIXOS,
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover
        )
        self.tipo_cb.set("Facção")
        self.tipo_cb.pack(side="left")
        self.tipo_cb.bind("<<ComboboxSelected>>", self._on_tipo_changed)

        # =========== SEÇÃO 3: DADOS BANCÁRIOS DO PRESTADOR ===========
        banco = ctk.CTkFrame(prest, fg_color=self.cor_fundo)
        banco.pack(fill="x", pady=(4, 2))

        ctk.CTkLabel(
            banco,
            text="Dados Bancários do Prestador",
            font=("Arial", 11, "bold"),
            text_color=self.cor_texto
        ).pack(anchor="w", padx=4, pady=1)

        grid = ctk.CTkFrame(banco, fg_color=self.cor_fundo)
        grid.pack(fill="x", padx=2, pady=1)

        def ro(parent, w=200):
            e = ctk.CTkEntry(
                parent,
                width=w,
                fg_color=self.cor_terciaria,
                border_color=self.cor_borda,
                text_color=self.cor_texto,
                state="disabled"
            )
            return e

        # Linha 1: Telefone, CPF, Banco (somente leitura - carregados do banco)
        l1b = ctk.CTkFrame(grid, fg_color=self.cor_fundo)
        l1b.pack(fill="x", pady=1)
        ctk.CTkLabel(l1b, text="Telefone:", width=80, text_color=self.cor_texto).pack(side="left", padx=2)
        self.telefone_entry = ro(l1b, 180)
        self.telefone_entry.pack(side="left", padx=2)
        ctk.CTkLabel(l1b, text="CPF:", width=50, text_color=self.cor_texto).pack(side="left", padx=2)
        self.cpf_entry = ro(l1b, 150)
        self.cpf_entry.pack(side="left", padx=2)
        ctk.CTkLabel(l1b, text="Banco:", width=60, text_color=self.cor_texto).pack(side="left", padx=2)
        self.banco_entry = ro(l1b, 150)
        self.banco_entry.pack(side="left", padx=2)

        # Linha 2: Agência, Conta, PIX (somente leitura - carregados do banco)
        l2b = ctk.CTkFrame(grid, fg_color=self.cor_fundo)
        l2b.pack(fill="x", pady=1)
        ctk.CTkLabel(l2b, text="Agência:", width=80, text_color=self.cor_texto).pack(side="left", padx=2)
        self.agencia_entry = ro(l2b, 140)
        self.agencia_entry.pack(side="left", padx=2)
        ctk.CTkLabel(l2b, text="Conta:", width=50, text_color=self.cor_texto).pack(side="left", padx=2)
        self.conta_entry = ro(l2b, 150)
        self.conta_entry.pack(side="left", padx=2)
        ctk.CTkLabel(l2b, text="PIX:", width=60, text_color=self.cor_texto).pack(side="left", padx=2)
        self.pix_entry = ro(l2b, 180)
        self.pix_entry.pack(side="left", padx=2)

        # Linha 3: Titular, Email, Endereço (EDITÁVEIS)
        l3b = ctk.CTkFrame(grid, fg_color=self.cor_fundo)
        l3b.pack(fill="x", pady=1)
        ctk.CTkLabel(l3b, text="Titular:", width=80, text_color=self.cor_texto).pack(side="left", padx=2)
        self.titular_entry = ctk.CTkEntry(
            l3b,
            width=150,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal"
        )
        self.titular_entry.pack(side="left", padx=2)

        ctk.CTkLabel(l3b, text="Email:", width=50, text_color=self.cor_texto).pack(side="left", padx=2)
        self.email_entry = ctk.CTkEntry(
            l3b,
            width=150,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal"
        )
        self.email_entry.pack(side="left", padx=2)

        ctk.CTkLabel(l3b, text="Endereço:", width=70, text_color=self.cor_texto).pack(side="left", padx=2)
        self.endereco_entry = ctk.CTkEntry(
            l3b,
            width=180,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal"
        )
        self.endereco_entry.pack(side="left", padx=2)

        # =========== SEÇÃO 4: TABELA DE CORTES ===========
        tabela_frame = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        tabela_frame.pack(fill="x", pady=2)

        # Configurar estilo da Treeview
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure(
            "Treeview",
            background=self.cor_secundaria,
            foreground=self.cor_texto,
            fieldbackground=self.cor_secundaria,
            borderwidth=0,
            highlightthickness=0,
            rowheight=20,
            font=("Arial", 9)
        )
        self.style.map('Treeview', background=[('selected', self.cor_primaria)])

        self.style.configure(
            "Treeview.Heading",
            font=("Arial", 9, "bold"),
            background=self.cor_primaria,
            foreground=self.cor_texto
        )

        # Configurar colunas da treeview
        cols_ui = ["ID", "Número", "Código", "Descrição",
                   "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "Total"]

        self.cortes_tree = ttk.Treeview(
            tabela_frame,
            columns=cols_ui,
            show="headings",
            height=4,
            style="Treeview"
        )

        headers = {
            "ID": "ID", "Número": "Número", "Código": "Código", "Descrição": "Descrição",
            "PP": "PP", "P": "P", "M": "M", "G": "G", "GG": "GG", "G1": "G1", "G2": "G2", "G3": "G3",
            "Total": "Total"
        }

        for col in cols_ui:
            self.cortes_tree.heading(col, text=headers[col])
            if col in ["PP", "P", "M", "G", "GG", "G1", "G2", "G3", "Total"]:
                w = 50
            elif col in ["ID", "Número"]:
                w = 70
            elif col == "Código":
                w = 90
            else:
                w = 160
            self.cortes_tree.column(col, width=w, anchor="center")

        self.cortes_tree.pack(fill="x")
        self.cortes_tree.bind("<<TreeviewSelect>>", self.on_corte_selecionado)

        # =========== SEÇÃO 5: DETALHES DO CORTE E CONTATOS ===========
        det = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        det.pack(fill="x", pady=2)

        l1 = ctk.CTkFrame(det, fg_color=self.cor_fundo)
        l1.pack(fill="x", pady=1)

        # Contatos de Encarregado e Acabamento
        ctk.CTkLabel(
            l1,
            text="Tel Encarregado:",
            width=100,
            text_color=self.cor_texto
        ).pack(side="left", padx=2)
        self.tel_encarregado_entry = ctk.CTkEntry(
            l1,
            width=120,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal"
        )
        self.tel_encarregado_entry.pack(side="left", padx=2)

        ctk.CTkLabel(
            l1,
            text="Tel Acabamento:",
            width=100,
            text_color=self.cor_texto
        ).pack(side="left", padx=2)
        self.tel_acabamento_entry = ctk.CTkEntry(
            l1,
            width=120,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal"
        )
        self.tel_acabamento_entry.pack(side="left", padx=2)

        # Data de Envio
        ctk.CTkLabel(
            l1,
            text="Data:",
            width=40,
            text_color=self.cor_texto
        ).pack(side="left", padx=2)
        self.data_entry = ctk.CTkEntry(
            l1,
            width=90,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal"
        )
        self.data_entry.insert(0, today_str())
        self.data_entry.pack(side="left", padx=2)

        # Previsão de Entrega com Calendário
        ctk.CTkLabel(
            l1,
            text="Prev. Entrega:",
            width=90,
            text_color=self.cor_texto
        ).pack(side="left", padx=2)
        self.previsao_entry = ctk.CTkEntry(
            l1,
            width=90,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal"
        )
        self.previsao_entry.pack(side="left", padx=2)

        ctk.CTkButton(
            l1,
            text="📅",
            width=30,
            command=lambda: self._abrir_calendario(self.previsao_entry),
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=2)

        self.previsao_entry.bind("<Double-Button-1>", lambda e: self._abrir_calendario(self.previsao_entry))

        # Campos Adicionais: Prioridade e Modalidade de Pagamento
        ctk.CTkLabel(
            l1,
            text="Prioridade:",
            width=70,
            text_color=self.cor_texto
        ).pack(side="left", padx=(10, 2))

        self.prioridade_cb = ctk.CTkComboBox(
            l1,
            width=100,
            values=["Normal", "Urgente", "Prioritário"],
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover
        )
        self.prioridade_cb.set("Normal")
        self.prioridade_cb.pack(side="left", padx=2)

        ctk.CTkLabel(
            l1,
            text="Pagamento:",
            width=70,
            text_color=self.cor_texto
        ).pack(side="left", padx=(10, 2))

        self.pagamento_cb = ctk.CTkComboBox(
            l1,
            width=100,
            values=["À Vista", "30 Dias", "60 Dias", "90 Dias"],
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover
        )
        self.pagamento_cb.set("30 Dias")
        self.pagamento_cb.pack(side="left", padx=2)

        # Linha 2: Dados do Corte
        l2 = ctk.CTkFrame(det, fg_color=self.cor_fundo)
        l2.pack(fill="x", pady=1)

        ctk.CTkLabel(l2, text="Código:", width=60, text_color=self.cor_texto).pack(side="left", padx=2)
        self.codigo_entry = ctk.CTkEntry(
            l2,
            width=120,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="disabled"
        )
        self.codigo_entry.pack(side="left", padx=2)

        ctk.CTkLabel(l2, text="Descrição:", width=70, text_color=self.cor_texto).pack(side="left", padx=2)
        self.descricao_entry = ctk.CTkEntry(
            l2,
            width=280,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="disabled"
        )
        self.descricao_entry.pack(side="left", padx=2)

        ctk.CTkLabel(l2, text="Nº Ordem:", width=70, text_color=self.cor_texto).pack(side="left", padx=2)
        self.ordem_entry = ctk.CTkEntry(
            l2,
            width=100,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="disabled"
        )
        self.ordem_entry.pack(side="left", padx=2)

        # Linha 3: Campos Adicionais do Corte
        l3 = ctk.CTkFrame(det, fg_color=self.cor_fundo)
        l3.pack(fill="x", pady=1)

        ctk.CTkLabel(l3, text="Coleção:", width=60, text_color=self.cor_texto).pack(side="left", padx=2)
        self.colecao_entry = ctk.CTkEntry(
            l3,
            width=120,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal"
        )
        self.colecao_entry.pack(side="left", padx=2)

        ctk.CTkLabel(l3, text="Material:", width=60, text_color=self.cor_texto).pack(side="left", padx=2)
        self.material_entry = ctk.CTkEntry(
            l3,
            width=120,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal"
        )
        self.material_entry.pack(side="left", padx=2)

        # CORES - CAMPO DE TEXTO PARA DIGITAR
        ctk.CTkLabel(l3, text="Cores:", width=40, text_color=self.cor_texto).pack(side="left", padx=2)
        self.cores_entry = ctk.CTkEntry(
            l3,
            width=200,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal",
            placeholder_text="Ex: Preto, Branco, Vermelho"
        )
        self.cores_entry.pack(side="left", padx=2)

        ctk.CTkLabel(l3, text="Cliente:", width=60, text_color=self.cor_texto).pack(side="left", padx=(10, 2))
        self.cliente_entry = ctk.CTkEntry(
            l3,
            width=120,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal"
        )
        self.cliente_entry.pack(side="left", padx=2)

        # =========== SEÇÃO 6: ÁREA CENTRAL (QUANTIDADES + INFORMAÇÕES) ===========
        mid = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        mid.pack(fill="both", expand=True, pady=2)
        mid.grid_columnconfigure(0, weight=3)
        mid.grid_columnconfigure(1, weight=2)
        mid.grid_rowconfigure(0, weight=1)

        # =========== COLUNA ESQUERDA: QUANTIDADES POR TAMANHO ===========
        left = ctk.CTkFrame(mid, fg_color=self.cor_fundo)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(
            left,
            text="Quantidades por Tamanho",
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        ).pack(anchor="w", padx=4, pady=1)

        # Controle de Valor Único
        ctrl_valor = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        ctrl_valor.pack(fill="x", pady=(0, 2))

        self.chk_valor_unico = ctk.CTkCheckBox(
            ctrl_valor,
            text="Valor único para todos os tamanhos",
            variable=self.valor_unico_var,
            command=self._on_toggle_valor_unico,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            checkmark_color=self.cor_texto
        )
        self.chk_valor_unico.pack(anchor="w", padx=4)

        # Cabeçalho da Grade
        header_g = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        header_g.pack(fill="x")

        for h, w in [
            ("Tam.", 50),
            ("Disp.", 70),
            ("Enviar", 70),
            ("Pilot.", 70),
            ("Valor/Peça", 100),
            ("Subtotal", 90)
        ]:
            ctk.CTkLabel(header_g, text=h, width=w, text_color=self.cor_texto).pack(side="left", padx=1)

        # Grade de Tamanhos
        self.grade_widgets = {}
        for tam in self.tamanhos:
            row = ctk.CTkFrame(left, fg_color=self.cor_fundo)
            row.pack(fill="x", pady=0)

            ctk.CTkLabel(row, text=tam, width=50, text_color=self.cor_texto).pack(side="left", padx=1)

            lbl_disp = ctk.CTkLabel(row, text="0", width=70, text_color=self.cor_texto)
            lbl_disp.pack(side="left", padx=1)

            ent_qtd = ctk.CTkEntry(
                row,
                width=70,
                textvariable=self.quantidades[tam],
                fg_color=self.cor_terciaria,
                border_color=self.cor_borda,
                text_color=self.cor_texto,
                state="normal"
            )
            ent_qtd.pack(side="left", padx=1)

            ent_pil = ctk.CTkEntry(
                row,
                width=70,
                textvariable=self.pilotos[tam],
                fg_color=self.cor_terciaria,
                border_color=self.cor_borda,
                text_color=self.cor_texto,
                state="normal"
            )
            ent_pil.pack(side="left", padx=1)

            ent_val = ctk.CTkEntry(
                row,
                width=100,
                textvariable=self.valores[tam],
                placeholder_text="0,00",
                fg_color=self.cor_terciaria,
                border_color=self.cor_borda,
                text_color=self.cor_texto,
                placeholder_text_color="#888888",
                state="normal"
            )
            ent_val.pack(side="left", padx=1)
            ent_val.bind("<KeyRelease>", lambda e, T=tam: self._on_valor_edit(T))

            ent_qtd.bind("<KeyRelease>", lambda e, T=tam: self._on_qtd_edit(T))
            ent_pil.bind("<KeyRelease>", lambda e, T=tam: self._on_piloto_edit(T))

            lbl_total = ctk.CTkLabel(row, text=fmt_moeda(0), width=90, text_color=self.cor_texto)
            lbl_total.pack(side="left", padx=1)

            self.grade_widgets[tam] = {"disp": lbl_disp, "sub": lbl_total, "ent_val": ent_val}

        # Totais
        totais = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        totais.pack(fill="x", pady=(2, 1))

        ctk.CTkLabel(
            totais,
            text="Total Peças:",
            width=90,
            font=("Arial", 11, "bold"),
            text_color=self.cor_texto
        ).pack(side="left", padx=2)

        self.lbl_total_pecas = ctk.CTkLabel(
            totais,
            text="0",
            font=("Arial", 11, "bold"),
            text_color=self.cor_texto
        )
        self.lbl_total_pecas.pack(side="left", padx=2)

        ctk.CTkLabel(
            totais,
            text="Valor Total:",
            width=90,
            font=("Arial", 11, "bold"),
            text_color=self.cor_texto
        ).pack(side="left", padx=8)

        self.lbl_valor_total = ctk.CTkLabel(
            totais,
            text=fmt_moeda(0),
            font=("Arial", 11, "bold"),
            text_color=self.cor_texto
        )
        self.lbl_valor_total.pack(side="left", padx=2)

        # Botões de Ação
        botoes = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        botoes.pack(fill="x", pady=(2, 4))

        ctk.CTkButton(
            botoes,
            text="Confirmar Envio",
            width=140,
            command=self.confirmar_envio,
            fg_color=self.cor_sucesso,
            hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            botoes,
            text="Pré-visualizar",
            width=120,
            command=self.preview_impressao,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            botoes,
            text="Exportar PDF",
            width=100,
            command=self.exportar_pdf,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            botoes,
            text="Limpar",
            width=80,
            command=self._limpar,
            fg_color=self.cor_secundaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=2)

        # =========== COLUNA DIREITA: PILOTO E INFORMAÇÕES ADICIONAIS ===========
        right = ctk.CTkFrame(mid, fg_color=self.cor_fundo)
        right.grid(row=0, column=1, sticky="nsew")

        # Seção Piloto Enviado
        sec_piloto = ctk.CTkFrame(right, fg_color=self.cor_fundo)
        sec_piloto.pack(fill="x", pady=(1, 4))

        ctk.CTkLabel(
            sec_piloto,
            text="Piloto Enviado",
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        ).pack(anchor="w", padx=4, pady=(2, 1))

        lp = ctk.CTkFrame(sec_piloto, fg_color=self.cor_fundo)
        lp.pack(fill="x", padx=4, pady=2)

        ctk.CTkLabel(lp, text="Tamanho:", width=60, text_color=self.cor_texto).pack(side="left")

        piloto_tam_cb = ctk.CTkComboBox(
            lp,
            width=80,
            values=self.tamanhos,
            variable=self.piloto_tam_var,
            state="readonly",
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover
        )
        piloto_tam_cb.set(self.tamanhos[0])
        piloto_tam_cb.pack(side="left", padx=2)

        ctk.CTkLabel(lp, text="Qtd:", width=30, text_color=self.cor_texto).pack(side="left")

        ctk.CTkEntry(
            lp,
            width=60,
            textvariable=self.piloto_qtd_var,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto,
            state="normal"
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            lp,
            text="Registrar",
            width=80,
            command=self._registrar_piloto,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=4)

        self.piloto_resumo_lbl = ctk.CTkLabel(
            sec_piloto,
            text="Nenhum.",
            anchor="w",
            font=("Arial", 10),
            text_color=self.cor_texto
        )
        self.piloto_resumo_lbl.pack(fill="x", padx=4, pady=(0, 2))

        # Área de Textos: Aviamentos
        ctk.CTkLabel(
            right,
            text="Aviamentos Enviados:",
            font=("Arial", 10),
            text_color=self.cor_texto
        ).pack(anchor="w", padx=4)

        self.aviamentos_entry = ctk.CTkTextbox(
            right,
            height=60,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto
        )
        self.aviamentos_entry.pack(fill="x", expand=False, padx=4, pady=1)

        # Área de Textos: Outros
        ctk.CTkLabel(
            right,
            text="Outros (linha, renda, etc.):",
            font=("Arial", 10),
            text_color=self.cor_texto
        ).pack(anchor="w", padx=4)

        self.outros_entry = ctk.CTkTextbox(
            right,
            height=60,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto
        )
        self.outros_entry.pack(fill="x", expand=False, padx=4, pady=1)

        # Área de Textos: Observações Gerais
        ctk.CTkLabel(
            right,
            text="Observações Gerais:",
            font=("Arial", 10),
            text_color=self.cor_texto
        ).pack(anchor="w", padx=4)

        self.obs_text = ctk.CTkTextbox(
            right,
            height=100,
            fg_color=self.cor_terciaria,
            border_color=self.cor_borda,
            text_color=self.cor_texto
        )
        self.obs_text.pack(fill="both", expand=True, padx=4, pady=1)

        # Carregar dados após a UI estar construída
        self.after(100, self._carregar_dados_iniciais)

    def _carregar_dados_iniciais(self):
        """Carrega os dados iniciais após a UI estar pronta"""
        try:
            # Carregar serviços para o filtro
            servicos_disponiveis = ["Todos"] + self._carregar_tipos_servicos()
            self.filtro_servico_cb.configure(values=servicos_disponiveis)
            self.filtro_servico_cb.set("Todos")

        except Exception as e:
            print(f"Erro ao carregar dados iniciais: {e}")

    # ----------------------------- Métodos de Carregamento -----------------------------
    def _carregar_prestadores(self):
        """Carrega todos os prestadores do banco de dados"""
        try:
            from BANCO_DE_DADOS_PG import get_conn, get_schema

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {get_schema()};")
                    cur.execute(
                        f"SELECT id, COALESCE(nome,''), COALESCE(telefone,''), COALESCE(tipo_prestador,'Facção') FROM {get_schema()}.cadastro_faccoes WHERE ativo = TRUE ORDER BY nome")
                    rows = cur.fetchall()

            nomes = []
            self._prestador_map = {}
            for pid, nome, tel, tipo in rows:
                visivel = (nome or "").strip()
                nomes.append(visivel)
                self._prestador_map[visivel.lower()] = pid

            self._prestadores_full = rows
            self.prestadores_filtrados = rows

            # Atualizar o combobox com os nomes
            self.prestador_busca_cb.configure(values=nomes)
            self._preencher_banco(None)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar prestadores: {e}")

    def _carregar_tipos_servicos(self):
        """Carrega os tipos de serviços únicos dos prestadores cadastrados"""
        try:
            # Buscar tipos únicos de prestadores cadastrados
            tipos_unicos = set()
            for prestador in self._prestadores_full:
                if len(prestador) > 3 and prestador[3]:
                    tipos_unicos.add(prestador[3])

            if tipos_unicos:
                return sorted(list(tipos_unicos))

            return SERVICOS_FIXOS

        except Exception as e:
            print(f"Erro ao carregar tipos de serviços: {e}")
            return SERVICOS_FIXOS

    def _aplicar_filtro_servico(self):
        """Aplica o filtro de serviço na lista de prestadores"""
        servico_selecionado = self.filtro_servico_var.get()

        if servico_selecionado == "Todos":
            self.prestadores_filtrados = self._prestadores_full
            nomes = [r[1] for r in self._prestadores_full]
        else:
            self.prestadores_filtrados = []
            for prestador in self._prestadores_full:
                if len(prestador) > 3 and prestador[3] == servico_selecionado:
                    self.prestadores_filtrados.append(prestador)

            if not self.prestadores_filtrados:
                nomes = [f"Nenhum prestador para {servico_selecionado}"]
            else:
                nomes = [r[1] for r in self.prestadores_filtrados]

        self.prestador_busca_cb.configure(values=nomes)

        self._prestador_map.clear()
        for prestador in self.prestadores_filtrados:
            if len(prestador) >= 2:
                nome = prestador[1]
                pid = prestador[0]
                if nome and not nome.startswith("Nenhum prestador"):
                    self._prestador_map[nome.lower()] = pid

        current_selection = self.prestador_busca_cb.get()
        if current_selection and current_selection.lower() not in self._prestador_map:
            self.prestador_busca_cb.set("")
            self._preencher_banco(None)

    def _filtrar_combo_prestador(self, event=None):
        """Filtra a lista de prestadores no combobox baseado no texto digitado"""
        termo = self.prestador_busca_cb.get().lower()

        if not termo:
            nomes = [r[1] for r in self.prestadores_filtrados if len(r) > 1 and r[1]]
            self.prestador_busca_cb.configure(values=nomes)
            return

        filtrados = []
        for prestador in self.prestadores_filtrados:
            if len(prestador) > 1 and prestador[1] and termo in prestador[1].lower():
                filtrados.append(prestador[1])

        self.prestador_busca_cb.configure(values=filtrados)

    def _on_costureira_selected(self, event=None):
        """Quando uma costureira é selecionada no combobox"""
        nome = self.prestador_busca_cb.get().strip()

        if nome.startswith("Nenhum prestador"):
            self.prestador_busca_cb.set("")
            self._preencher_banco(None)
            return

        if not nome:
            self._preencher_banco(None)
            return

        pid = self._prestador_map.get(nome.lower())
        if pid:
            self._preencher_banco(pid)
            return

        # Tenta localizar diretamente no banco (caso não esteja na lista carregada)
        encontrado = self._buscar_prestador_por_nome(nome)
        if encontrado:
            pid = encontrado[0]
            self._prestador_map[nome.lower()] = pid
            self._preencher_banco(pid)
            return

        messagebox.showwarning("Aviso", "Prestador não encontrado.")
        self._preencher_banco(None)

    def _on_prestador_change(self, choice):
        """Callback do combobox quando seleciona um item da lista."""
        if choice and not choice.startswith("Nenhum prestador"):
            self._on_costureira_selected()

    def _selecionar_prestador_por_nome(self, nome):
        """Seleciona o prestador pelo nome e preenche dados bancários se ele existir."""
        if not nome:
            return

        alvo = nome.strip().lower()
        pid = None
        for prestador in self._prestadores_full:
            if len(prestador) > 1 and prestador[1] and prestador[1].strip().lower() == alvo:
                pid = prestador[0]
                break

        if pid:
            self._prestador_map[alvo] = pid
            self.prestador_busca_cb.set(nome)
            self._preencher_banco(pid)
            return

        # Busca direta no banco para cortes antigos ou facções inativas
        encontrado = self._buscar_prestador_por_nome(nome)
        if encontrado:
            pid = encontrado[0]
            self._prestador_map[alvo] = pid
            self.prestador_busca_cb.set(encontrado[1] or nome)
            self._preencher_banco(pid)

    def _buscar_prestador_por_nome(self, nome):
        """Retorna (id, nome) de um prestador a partir do nome (case-insensitive)."""
        if not nome:
            return None

        try:
            from BANCO_DE_DADOS_PG import get_conn, get_schema

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {get_schema()};")
                    cur.execute(
                        f"""
                            SELECT id, nome
                            FROM {get_schema()}.cadastro_faccoes
                            WHERE LOWER(nome) = LOWER(%s)
                            LIMIT 1
                        """,
                        (nome,),
                    )
                    return cur.fetchone()
        except Exception:
            # Evita propagar erro secundário; preenchimento será limpo
            return None

    def _preencher_banco(self, prestador_id):
        """Preenche os dados bancários do prestador selecionado"""
        if not prestador_id:
            self._prestador_id = None
            self._prestador_nome = ""
            for w in [self.telefone_entry, self.cpf_entry, self.banco_entry,
                      self.agencia_entry, self.conta_entry, self.pix_entry, self.titular_entry]:
                w.configure(state="normal")
                w.delete(0, "end")
                w.configure(state="disabled")
            return

        try:
            from BANCO_DE_DADOS_PG import get_conn, get_schema

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {get_schema()};")
                    cur.execute(f"""
                        SELECT nome, telefone, cpf, banco, agencia, conta, pix, titular_da_conta
                        FROM {get_schema()}.cadastro_faccoes WHERE id=%s AND ativo = TRUE
                    """, (prestador_id,))
                    row = cur.fetchone()

            if not row:
                messagebox.showwarning("Aviso", "Prestador não encontrado no banco de dados.")
                return

            nome, tel, cpf, banco, agencia, conta, pix, titular = row
            self._prestador_id = prestador_id
            self._prestador_nome = nome or ""

            campos = [
                (self.telefone_entry, tel or ""),
                (self.cpf_entry, cpf or ""),
                (self.banco_entry, banco or ""),
                (self.agencia_entry, agencia or ""),
                (self.conta_entry, conta or ""),
                (self.pix_entry, pix or ""),
                (self.titular_entry, titular or "")
            ]

            for w, v in campos:
                w.configure(state="normal")
                w.delete(0, "end")
                w.insert(0, v)
                w.configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar dados bancários: {e}")

    def _carregar_dados_corte_pronto(self, corte_id):
        """Busca dados do corte pronto para envio (controle_envio_cortes) e retorna a última linha."""
        try:
            from BANCO_DE_DADOS_PG import get_conn, get_schema

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {get_schema()};")
                    cur.execute(f"""
                        SELECT servico, faccao, costureira, ordem_corte, codigo_corte, descricao_corte,
                               COALESCE(pp,0), COALESCE(p,0), COALESCE(m,0), COALESCE(g,0), COALESCE(gg,0),
                               COALESCE(g1,0), COALESCE(g2,0), COALESCE(g3,0), COALESCE(quantidade_total,0)
                        FROM {get_schema()}.controle_envio_cortes
                        WHERE corte_id = %s
                        ORDER BY id DESC
                        LIMIT 1
                    """, (corte_id,))
                    return cur.fetchone()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar corte pronto para envio: {e}")
        return None

    def _on_tipo_changed(self, event=None):
        """Quando o tipo de serviço é alterado"""
        self._tipo_servico = self.tipo_cb.get()

        valores_filtro = self.filtro_servico_cb.cget("values")
        if valores_filtro and self._tipo_servico in valores_filtro:
            self.filtro_servico_var.set(self._tipo_servico)
            self._aplicar_filtro_servico()

    # ----------------------------- Métodos de Corte -----------------------------
    def _resolver_corte_schema(self):
        """Detecta nomes reais das colunas de cadastro_de_corte"""
        try:
            from BANCO_DE_DADOS_PG import get_conn, get_schema

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {get_schema()};")
                    cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = %s AND table_name = 'cadastro_de_corte'
                        ORDER BY ordinal_position
                    """, (get_schema(),))
                    cols = {r[0] for r in cur.fetchall()}
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao detectar schema do corte: {e}")
            cols = set()

        if "numero_ordem" in cols:
            numero = "numero_ordem"
        elif "numero_corte" in cols:
            numero = "numero_corte"
        elif "ordem_corte" in cols:
            numero = "ordem_corte"
        else:
            numero = None

        codigo = "codigo" if "codigo" in cols else ("codigo_corte" if "codigo_corte" in cols else None)
        descricao = "descricao" if "descricao" in cols else ("descricao_corte" if "descricao_corte" in cols else None)
        total = "total_pecas" if "total_pecas" in cols else (
            "total_p" if "total_p" in cols else ("total" if "total" in cols else None))

        if numero and "ordem" in numero:
            num_label = "Nº Ordem"
        else:
            num_label = "Número" if numero else "Número"

        self._corte_schema = {"numero": numero, "codigo": codigo, "descricao": descricao, "total": total,
                              "num_label": num_label, "all_cols": cols}

        cols_ui = ["ID", "Número", "Código", "Descrição", "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "Total"]
        self.cortes_tree.configure(columns=cols_ui)
        headers = {"ID": "ID", "Número": num_label, "Código": "Código", "Descrição": "Descrição",
                   "PP": "PP", "P": "P", "M": "M", "G": "G", "GG": "GG", "G1": "G1", "G2": "G2", "G3": "G3",
                   "Total": "Total"}
        for col in cols_ui:
            self.cortes_tree.heading(col, text=headers[col])
            w = 70 if col in ["PP", "P", "M", "G", "GG", "G1", "G2", "G3", "Total"] else 130
            if col in ["ID", "Número"]:
                w = 100
            self.cortes_tree.column(col, width=w, anchor="center")

    def _sql_select_list(self):
        """SELECT padrão: id, numero(qualquer nome do banco), codigo, descricao, pp..g3, total.

        Quando as colunas de tamanho não existem na tabela principal, usamos a soma registrada
        nas tabelas detalhadas (tecidos ou lotes) para que a grade da tela traga as quantidades
        por tamanho em vez de zeros.
        """
        cols = self._corte_schema["all_cols"]
        numero = self._corte_schema["numero"] or "'' AS numero"
        codigo = self._corte_schema["codigo"] or "'' AS codigo"
        descricao = self._corte_schema["descricao"] or "'' AS descricao"

        schema = get_schema()

        def col_or_soma(c):
            if c in cols:
                return c
            return (
                "COALESCE((SELECT SUM({col}) FROM {schema}.cadastro_de_corte_tecidos WHERE cadastro_id = id), "
                "COALESCE((SELECT SUM({col}) FROM {schema}.cadastro_de_corte_lotes WHERE cadastro_id = id), 0)) AS {col}"
            ).format(col=c, schema=schema)

        if self._corte_schema["total"] and self._corte_schema["total"] in cols:
            total = self._corte_schema["total"]
        else:
            total = (
                f"COALESCE((SELECT SUM(total_pecas) FROM {schema}.cadastro_de_corte_tecidos WHERE cadastro_id = id), "
                f"COALESCE((SELECT SUM(total_lote) FROM {schema}.cadastro_de_corte_lotes WHERE cadastro_id = id), 0)) AS total_pecas"
            )

        return ", ".join([
            "id",
            numero,
            codigo,
            descricao,
            col_or_soma("pp"), col_or_soma("p"), col_or_soma("m"), col_or_soma("g"),
            col_or_soma("gg"), col_or_soma("g1"), col_or_soma("g2"), col_or_soma("g3"),
            total
        ])

    def _buscar_cortes_iniciais(self):
        try:
            self.cortes_tree.delete(*self.cortes_tree.get_children())
            from BANCO_DE_DADOS_PG import get_conn, get_schema

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {get_schema()};")
                    select_list = self._sql_select_list()
                    cur.execute(f"SELECT {select_list} FROM {get_schema()}.cadastro_de_corte ORDER BY 1 DESC LIMIT 50")
                    for row in cur.fetchall():
                        self.cortes_tree.insert("", "end", values=row)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar cortes: {e}")

    def buscar_cortes(self):
        termo = (self.busca_entry.get() or "").strip()
        if not termo:
            self._buscar_cortes_iniciais()
            return

        try:
            self.cortes_tree.delete(*self.cortes_tree.get_children())
            from BANCO_DE_DADOS_PG import get_conn, get_schema

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {get_schema()};")
                    select_list = self._sql_select_list()
                    numero = self._corte_schema["numero"]
                    codigo = self._corte_schema["codigo"]
                    descricao = self._corte_schema["descricao"]

                    where_parts = []
                    params = []
                    if numero:
                        where_parts.append(f"CAST({numero} AS TEXT) ILIKE %s")
                        params.append(f"%{termo}%")
                    if codigo:
                        where_parts.append(f"CAST({codigo} AS TEXT) ILIKE %s")
                        params.append(f"%{termo}%")
                    if descricao:
                        where_parts.append(f"CAST({descricao} AS TEXT) ILIKE %s")
                        params.append(f"%{termo}%")

                    where_clause = " OR ".join(where_parts)
                    cur.execute(
                        f"SELECT {select_list} FROM {get_schema()}.cadastro_de_corte WHERE {where_clause} ORDER BY 1 DESC LIMIT 100",
                        params)
                    for row in cur.fetchall():
                        self.cortes_tree.insert("", "end", values=row)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na busca: {e}")

    def on_corte_selecionado(self, event):
        sel = self.cortes_tree.selection()
        if not sel:
            return
        item = sel[0]
        vals = self.cortes_tree.item(item, "values")
        if not vals:
            return

        # ID é o primeiro elemento
        corte_id = vals[0]
        self.corte_selecionado = corte_id

        # Preenche campos básicos
        def _set_entry(entry, value):
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, value)
            entry.configure(state="disabled")

        _set_entry(self.codigo_entry, vals[2] if len(vals) > 2 else "")
        _set_entry(self.descricao_entry, vals[3] if len(vals) > 3 else "")
        _set_entry(self.ordem_entry, vals[1] if len(vals) > 1 else "")

        # Preenche grade com saldos
        cols_tam = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]
        for i, tam in enumerate(cols_tam):
            idx = 4 + i  # após id, numero, codigo, descricao
            if idx < len(vals):
                qtd_tam = safe_int(vals[idx])
            else:
                qtd_tam = 0

            self.grade_widgets[tam]["disp"].configure(text=str(qtd_tam))
            self.quantidades[tam].set(qtd_tam)
            self._total_por_tam[tam] = qtd_tam
            self._piloto_prev[tam] = 0

        # Limpa quantidades enviadas
        for tam in self.tamanhos:
            self.pilotos[tam].set(0)
            self.valores[tam].set("")

        self._recalcular()

        corte_pronto = self._carregar_dados_corte_pronto(corte_id)
        if corte_pronto:
            servico, faccao, costureira, ordem, codigo, descricao, *qtds, _total = corte_pronto

            if codigo:
                _set_entry(self.codigo_entry, codigo)
            if descricao:
                _set_entry(self.descricao_entry, descricao)
            if ordem:
                _set_entry(self.ordem_entry, ordem)

            for tam, qtd in zip(self.tamanhos, qtds):
                qtd_int = safe_int(qtd)
                self.grade_widgets[tam]["disp"].configure(text=str(qtd_int))
                self.quantidades[tam].set(qtd_int)
                self._total_por_tam[tam] = qtd_int
                self._piloto_prev[tam] = 0

            if servico:
                self.tipo_cb.set(servico)
                self._on_tipo_changed()

            self._selecionar_prestador_por_nome(faccao or costureira)

    # ----------------------------- Métodos de Grade -----------------------------
    def _on_toggle_valor_unico(self):
        if self.valor_unico_var.get():
            primeiro_valor = None
            for tam in self.tamanhos:
                v = self.valores[tam].get().strip()
                if v:
                    primeiro_valor = v
                    break

            if primeiro_valor is None:
                primeiro_valor = "0,00"

            for tam in self.tamanhos:
                self.valores[tam].set(primeiro_valor)
            for tam in self.tamanhos:
                self.grade_widgets[tam]["ent_val"].configure(state="disabled")
            self._recalcular()
        else:
            for tam in self.tamanhos:
                self.grade_widgets[tam]["ent_val"].configure(state="normal")

    def _on_valor_edit(self, tam):
        if self.valor_unico_var.get():
            v = self.valores[tam].get()
            for t in self.tamanhos:
                self.valores[t].set(v)
        self._recalcular()

    def _on_qtd_edit(self, tam):
        qtd = safe_int(self.quantidades[tam].get())
        self.quantidades[tam].set(qtd)
        pil = safe_int(self.pilotos[tam].get())
        self._total_por_tam[tam] = qtd + pil
        self._piloto_prev[tam] = pil
        self._recalcular()

    def _on_piloto_edit(self, tam):
        novo_piloto = safe_int(self.pilotos[tam].get())
        total_planejado = self._total_por_tam.get(tam) or (safe_int(self.quantidades[tam].get()) + safe_int(self._piloto_prev.get(tam, 0)))
        envio_liquido = max(total_planejado - novo_piloto, 0)
        self.quantidades[tam].set(envio_liquido)
        self._total_por_tam[tam] = envio_liquido + novo_piloto
        self._piloto_prev[tam] = novo_piloto
        self._recalcular()
        self._update_piloto_resumo()

    def _recalcular(self, event=None):
        total_pecas = 0
        total_valor = 0.0
        for tam in self.tamanhos:
            pil = safe_int(self.pilotos[tam].get())
            total_planejado = self._total_por_tam.get(tam)
            if total_planejado is None or total_planejado == 0:
                total_planejado = safe_int(self.quantidades[tam].get()) + pil

            envio_liquido = max(total_planejado - pil, 0)
            self.quantidades[tam].set(envio_liquido)
            self._total_por_tam[tam] = envio_liquido + pil

            val = parse_valor(self.valores[tam].get())
            sub = envio_liquido * val
            self.grade_widgets[tam]["sub"].configure(text=fmt_moeda(sub))
            total_pecas += envio_liquido
            total_valor += sub
        self.lbl_total_pecas.configure(text=str(total_pecas))
        self.lbl_valor_total.configure(text=fmt_moeda(total_valor))

    def _update_piloto_resumo(self):
        pils = [(t, safe_int(self.pilotos[t].get())) for t in self.tamanhos]
        pils = [(t, q) for t, q in pils if q > 0]
        if not pils:
            self.piloto_resumo_lbl.configure(text="Nenhum.")
            return
        txt = ", ".join([f"{t}={q}" for t, q in pils])
        self.piloto_resumo_lbl.configure(text=txt)

    def _registrar_piloto(self):
        tam = self.piloto_tam_var.get()
        qtd = safe_int(self.piloto_qtd_var.get())
        if not qtd:
            return
        self.pilotos[tam].set(self.pilotos[tam].get() + qtd)
        self.piloto_qtd_var.set(0)
        self._recalcular()
        self._update_piloto_resumo()

    # ----------------------------- Métodos de Ação -----------------------------
    def _abrir_calendario(self, entry, widget_origem=None):
        """
        Abre janela do calendário alinhada ao BOTÃO (widget_origem) se existir.
        Caso contrário, alinha ao próprio campo (entry).
        """

        def setar_data(data_escolhida):
            entry.delete(0, "end")
            entry.insert(0, data_escolhida.strftime("%d/%m/%Y"))
            top.destroy()

        # Fechar janela anterior se existir
        if hasattr(self, '_cal_janela') and self._cal_janela.winfo_exists():
            self._cal_janela.destroy()

        top = ctk.CTkToplevel(self)
        self._cal_janela = top  # Guardar referência
        top.title("Calendário")
        top.resizable(False, False)

        # Não definir geometry ainda - vamos criar conteúdo primeiro

        top.transient(self)  # Fica sempre na frente da janela principal
        top.grab_set()  # Modal - trava interação com outras janelas

        # =============================================
        # CONTEÚDO DO CALENDÁRIO (criar primeiro)
        # =============================================

        # --- CALENDÁRIO em português ---
        MESES_PT = [
            "", "Janeiro", "Fevereiro", "Março", "Abril",
            "Maio", "Junho", "Julho", "Agosto",
            "Setembro", "Outubro", "Novembro", "Dezembro"
        ]
        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

        agora = datetime.now()
        ano = agora.year
        mes = agora.month

        frame_nav = ctk.CTkFrame(top)
        frame_nav.pack(fill="x", padx=10, pady=5)

        btn_anterior = ctk.CTkButton(
            frame_nav, text="<", width=30,
            command=lambda: mudar_mes(-1)
        )
        btn_anterior.pack(side="left")

        lbl_mes_ano = ctk.CTkLabel(
            frame_nav,
            text=f"{MESES_PT[mes]} {ano}",
            font=("Arial", 14)
        )
        lbl_mes_ano.pack(side="left", expand=True)

        btn_proximo = ctk.CTkButton(
            frame_nav, text=">", width=30,
            command=lambda: mudar_mes(1)
        )
        btn_proximo.pack(side="right")

        frame_dias = ctk.CTkFrame(top)
        frame_dias.pack(fill="both", expand=True, padx=10, pady=5)

        for i, dia in enumerate(dias_semana):
            lbl = ctk.CTkLabel(frame_dias, text=dia, width=30, height=30)
            lbl.grid(row=0, column=i, padx=2, pady=2)

        def mudar_mes(delta):
            nonlocal mes, ano
            mes += delta
            if mes > 12:
                mes = 1
                ano += 1
            elif mes < 1:
                mes = 12
                ano -= 1
            lbl_mes_ano.configure(text=f"{MESES_PT[mes]} {ano}")
            desenhar_calendario()

        def desenhar_calendario():
            for widget in frame_dias.grid_slaves():
                if int(widget.grid_info()["row"]) > 0:
                    widget.destroy()

            calendario_mes = _cal.monthcalendar(ano, mes)
            for linha, semana in enumerate(calendario_mes):
                for coluna, dia in enumerate(semana):
                    if dia == 0:
                        continue
                    btn_dia = ctk.CTkButton(
                        frame_dias,
                        text=str(dia),
                        width=30,
                        height=30,
                        command=lambda d=dia: setar_data(datetime(ano, mes, d))
                    )
                    btn_dia.grid(row=linha + 1, column=coluna, padx=2, pady=2)

        desenhar_calendario()

        # =============================================
        # AGORA SIM - POSICIONAR A JANELA
        # (após o conteúdo estar criado)
        # =============================================

        # Forçar atualização para calcular tamanhos
        top.update_idletasks()

        # Obter posição do widget alvo (botão ou campo)
        alvo = widget_origem if widget_origem else entry
        alvo.update_idletasks()

        # Posição do widget alvo
        alvo_x = alvo.winfo_rootx()
        alvo_y = alvo.winfo_rooty()
        alvo_largura = alvo.winfo_width()
        alvo_altura = alvo.winfo_height()

        # Tamanho real do calendário (agora já calculado)
        largura_cal = top.winfo_width()
        altura_cal = top.winfo_height()

        # CALCULAR POSIÇÃO X (horizontal)
        # =============================================
        # PARA MOVER: ajuste os valores abaixo
        # =============================================
        if widget_origem:  # Se for o botão 📅
            # Posição X: alinhar à direita do botão
            x = alvo_x + alvo_largura - largura_cal  # Alinha à direita

            # AJUSTE AQUI para mover horizontalmente:
            # x = x - 150  # ← SUBTRAIA valor para mover para ESQUERDA
            x = x - 100  # ← Exemplo: 100px para esquerda
            # x = x + 50   # ← SOME valor para mover para DIREITA
        else:  # Se for o campo entry
            # Centralizar sobre o campo
            x = alvo_x + (alvo_largura // 2) - (largura_cal // 2)

        # CALCULAR POSIÇÃO Y (vertical)
        # =============================================
        # PARA MOVER: ajuste os valores abaixo
        # =============================================
        y = alvo_y + alvo_altura  # Coloca abaixo do widget
        y = y + 5  # ← SOME valor para mover para BAIXO
        # y = y - 50  # ← SUBTRAIA valor para mover para CIMA

        # Ajustar para não sair da tela
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        if x + largura_cal > screen_width:
            x = screen_width - largura_cal - 20
        if x < 0:
            x = 20
        if y + altura_cal > screen_height:
            y = alvo_y - altura_cal - 10
        if y < 0:
            y = 20

        # APLICAR POSIÇÃO FINAL
        top.geometry(f"{largura_cal}x{altura_cal}+{int(x)}+{int(y)}")

        # Garantir que está na frente
        top.lift()
        top.focus_force()

    def _limpar(self):
        self.corte_selecionado = None
        self.cortes_tree.selection_remove(self.cortes_tree.selection())
        self.busca_entry.delete(0, "end")
        self.prestador_busca_cb.set("")
        self.tipo_cb.set("Facção")
        self._preencher_banco(None)
        self.tel_encarregado_entry.delete(0, "end")
        self.tel_acabamento_entry.delete(0, "end")
        self.data_entry.delete(0, "end")
        self.data_entry.insert(0, today_str())
        self.previsao_entry.delete(0, "end")
        self.codigo_entry.configure(state="normal")
        self.descricao_entry.configure(state="normal")
        self.ordem_entry.configure(state="normal")
        self.codigo_entry.delete(0, "end")
        self.descricao_entry.delete(0, "end")
        self.ordem_entry.delete(0, "end")
        self.codigo_entry.configure(state="disabled")
        self.descricao_entry.configure(state="disabled")
        self.ordem_entry.configure(state="disabled")
        for tam in self.tamanhos:
            self.quantidades[tam].set(0)
            self.pilotos[tam].set(0)
            self.valores[tam].set("")
            self._total_por_tam[tam] = 0
            self._piloto_prev[tam] = 0
            self.grade_widgets[tam]["disp"].configure(text="0")
            self.grade_widgets[tam]["sub"].configure(text=fmt_moeda(0))
        self.lbl_total_pecas.configure(text="0")
        self.lbl_valor_total.configure(text=fmt_moeda(0))
        self.aviamentos_entry.delete("1.0", "end")
        self.outros_entry.delete("1.0", "end")
        self.obs_text.delete("1.0", "end")
        self.piloto_resumo_lbl.configure(text="Nenhum.")
        self.valor_unico_var.set(0)
        self._on_toggle_valor_unico()

    def _validar_envio(self):
        if not self._prestador_id:
            messagebox.showwarning("Aviso", "Selecione um prestador.")
            return False
        if not self.corte_selecionado:
            messagebox.showwarning("Aviso", "Selecione um corte.")
            return False

        total_pecas = 0
        for t in self.tamanhos:
            pil = safe_int(self.pilotos[t].get())
            total_planejado = self._total_por_tam.get(t) or (safe_int(self.quantidades[t].get()) + pil)
            total_pecas += max(total_planejado - pil, 0)
        if total_pecas == 0:
            messagebox.showwarning("Aviso", "Informe quantidades a enviar.")
            return False

        # Verificar saldo
        try:
            from BANCO_DE_DADOS_PG import get_conn, get_schema

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {get_schema()};")
                    # Obter colunas disponíveis
                    cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = %s AND table_name = 'cadastro_de_corte'
                    """, (get_schema(),))
                    cols = {r[0] for r in cur.fetchall()}
                    tamanhos_db = [c for c in ["pp", "p", "m", "g", "gg", "g1", "g2", "g3"] if c in cols]
                    if not tamanhos_db:
                        messagebox.showerror("Erro", "Tabela cadastro_de_corte não possui colunas de tamanho.")
                        return False

                    select_cols = ", ".join(tamanhos_db)
                    cur.execute(f"SELECT {select_cols} FROM {get_schema()}.cadastro_de_corte WHERE id=%s",
                                (self.corte_selecionado,))
                    row = cur.fetchone()
                    if not row:
                        messagebox.showerror("Erro", "Corte não encontrado.")
                        return False

                    atual = {tam.upper(): int(row[i]) for i, tam in enumerate(tamanhos_db)}
                    for tam in tamanhos_db:
                        TAM = tam.upper()
                        enviar_total = self._total_por_tam.get(TAM) or (
                            safe_int(self.quantidades[TAM].get()) + safe_int(self.pilotos[TAM].get())
                        )
                        if enviar_total > atual[TAM]:
                            messagebox.showerror(
                                "Erro",
                                f"Saldo insuficiente para {TAM}. Disponível: {atual[TAM]}, enviar: {enviar_total}."
                            )
                            return False

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na validação: {e}")
            return False

        return True

    def _debitar_do_corte(self, cur, corte_id: int, qtds: dict, pils: dict):
        """
        Debita do cadastro_de_corte as quantidades enviadas (qtds) e pilotos (pils).
        """
        from BANCO_DE_DADOS_PG import get_schema

        # Obter colunas disponíveis
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = 'cadastro_de_corte'
        """, (get_schema(),))
        cols = {r[0] for r in cur.fetchall()}

        tamanhos_cols = [c for c in ["pp", "p", "m", "g", "gg", "g1", "g2", "g3"] if c in cols]
        total_col = None
        for c in ["total_pecas", "total_p", "total"]:
            if c in cols:
                total_col = c
                break
        if not tamanhos_cols:
            raise ValueError("Tabela cadastro_de_corte não possui colunas de tamanho (PP..G3).")

        select_cols = ", ".join(tamanhos_cols + ([total_col] if total_col else []))
        cur.execute(f"SELECT {select_cols} FROM {get_schema()}.cadastro_de_corte WHERE id=%s", (corte_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Corte não encontrado.")

        atual = {tam.upper(): int(row[i]) for i, tam in enumerate(tamanhos_cols)}
        atual_total = int(row[len(tamanhos_cols)]) if total_col else None

        novo = {}
        debito_total = 0
        for tam in tamanhos_cols:
            TAM = tam.upper()
            enviar = int(qtds.get(TAM, 0)) + int(pils.get(TAM, 0))
            debito_total += enviar
            if enviar > atual[TAM]:
                raise ValueError(f"Saldo insuficiente para {TAM}. Tentando debitar {enviar}, saldo {atual[TAM]}.")
            novo[tam] = atual[TAM] - enviar

        valores_set = ", ".join([f"{tam}=%s" for tam in tamanhos_cols])
        params = [novo[tam] for tam in tamanhos_cols]

        if total_col is not None and atual_total is not None:
            novo_total = max(atual_total - debito_total, 0)
            valores_set += f", {total_col}=%s"
            params.append(novo_total)

        params.append(corte_id)
        cur.execute(f"UPDATE {get_schema()}.cadastro_de_corte SET {valores_set} WHERE id=%s", params)

    # ----------------------------- SALVAR ENVIO -----------------------------
    def confirmar_envio(self):
        """Salva o envio na tabela envios_cortes com TODOS os campos da tela."""

        if not self.corte_selecionado:
            messagebox.showwarning("Aviso", "Selecione um corte antes de confirmar o envio.")
            return

        if not self._prestador_id:
            messagebox.showwarning("Aviso", "Selecione a costureira/prestador antes de confirmar o envio.")
            return

        try:
            from BANCO_DE_DADOS_PG import get_conn, get_schema
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar módulo de banco de dados:\n{e}")
            return

        try:
            # ---------------- DADOS BÁSICOS ----------------
            schema = get_schema()

            # data_envio
            data_envio_str = (self.data_entry.get() or "").strip()
            try:
                data_envio = datetime.strptime(data_envio_str, "%d/%m/%Y").date()
            except Exception:
                data_envio = datetime.now().date()

            # hora_envio = agora
            hora_envio = datetime.now().time()

            prestador_id = self._prestador_id
            tipo_servico = (self.tipo_cb.get() or "").strip() or "Facção"

            # corte_id veio da seleção da tree de cortes
            # self.corte_selecionado costuma ser uma tupla/linha do SELECT
            # onde o primeiro elemento é o ID do corte
            try:
                corte_id = int(self.corte_selecionado[0])
            except Exception:
                corte_id = None

            ordem_corte = (self.ordem_entry.get() or "").strip() or None
            codigo_corte = (self.codigo_entry.get() or "").strip() or None
            descricao_corte = (self.descricao_entry.get() or "").strip() or None

            colecao = (self.colecao_entry.get() or "").strip() or None
            material = (self.material_entry.get() or "").strip() or None
            cliente = (self.cliente_entry.get() or "").strip() or None
            cores = (self.cores_entry.get() or "").strip() or None

            prioridade = (self.prioridade_cb.get() or "").strip() or None
            forma_pagamento = (self.pagamento_cb.get() or "").strip() or None

            status_envio = "Enviado"

            # ---------------- GRADE / QUANTIDADES ----------------
            # Quantidades por tamanho
            qtd_pp = safe_int(self.quantidades["PP"].get())
            qtd_p = safe_int(self.quantidades["P"].get())
            qtd_m = safe_int(self.quantidades["M"].get())
            qtd_g = safe_int(self.quantidades["G"].get())
            qtd_gg = safe_int(self.quantidades["GG"].get())
            qtd_g1 = safe_int(self.quantidades["G1"].get())
            qtd_g2 = safe_int(self.quantidades["G2"].get())
            qtd_g3 = safe_int(self.quantidades["G3"].get())

            # Valores por tamanho
            valor_pp = parse_valor(self.valores["PP"].get())
            valor_p = parse_valor(self.valores["P"].get())
            valor_m = parse_valor(self.valores["M"].get())
            valor_g = parse_valor(self.valores["G"].get())
            valor_gg = parse_valor(self.valores["GG"].get())
            valor_g1 = parse_valor(self.valores["G1"].get())
            valor_g2 = parse_valor(self.valores["G2"].get())
            valor_g3 = parse_valor(self.valores["G3"].get())

            # Totais
            total_pecas = (
                    qtd_pp + qtd_p + qtd_m + qtd_g +
                    qtd_gg + qtd_g1 + qtd_g2 + qtd_g3
            )

            total_pilotos = (
                    safe_int(self.pilotos["PP"].get()) +
                    safe_int(self.pilotos["P"].get()) +
                    safe_int(self.pilotos["M"].get()) +
                    safe_int(self.pilotos["G"].get()) +
                    safe_int(self.pilotos["GG"].get()) +
                    safe_int(self.pilotos["G1"].get()) +
                    safe_int(self.pilotos["G2"].get()) +
                    safe_int(self.pilotos["G3"].get())
            )

            valor_total_envio = (
                    qtd_pp * valor_pp +
                    qtd_p * valor_p +
                    qtd_m * valor_m +
                    qtd_g * valor_g +
                    qtd_gg * valor_gg +
                    qtd_g1 * valor_g1 +
                    qtd_g2 * valor_g2 +
                    qtd_g3 * valor_g3
            )

            # ---------------- TEXTOS / OBSERVAÇÕES ----------------
            resumo_pilotos = self.piloto_resumo_lbl.cget("text") or "Nenhum."
            resumo_pilotos = resumo_pilotos.strip() or "Nenhum."

            aviamentos = ""
            if hasattr(self, "aviamentos_entry"):
                aviamentos = self.aviamentos_entry.get("1.0", "end").strip() or None

            outros = ""
            if hasattr(self, "outros_entry"):
                outros = self.outros_entry.get("1.0", "end").strip() or None

            observacoes = ""
            if hasattr(self, "obs_text"):
                observacoes = self.obs_text.get("1.0", "end").strip() or None

            tel_encarregado = (self.tel_encarregado_entry.get() or "").strip() or None
            tel_acabamento = (self.tel_acabamento_entry.get() or "").strip() or None

            # Previsão de entrega
            previsao_str = (self.previsao_entry.get() or "").strip()
            previsao_entrega = None
            if previsao_str:
                try:
                    previsao_entrega = datetime.strptime(previsao_str, "%d/%m/%Y").date()
                except Exception:
                    previsao_entrega = None  # se der erro, deixa nulo para não travar

            # ---------------- INSERT NO BANCO ----------------
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {schema};")

                    sql = f"""
                        INSERT INTO envios_cortes (
                            data_envio, hora_envio, prestador_id, tipo_servico, corte_id,
                            ordem_corte, codigo_corte, descricao_corte,
                            colecao, material, cliente, cores,
                            prioridade, forma_pagamento, status_envio,
                            qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3,
                            valor_pp, valor_p, valor_m, valor_g, valor_gg, valor_g1, valor_g2, valor_g3,
                            total_pecas, total_pilotos, valor_total_envio,
                            resumo_pilotos, aviamentos, outros, observacoes,
                            tel_encarregado, tel_acabamento, previsao_entrega
                        )
                        VALUES (
                            %s,%s,%s,%s,%s,
                            %s,%s,%s,
                            %s,%s,%s,%s,
                            %s,%s,%s,
                            %s,%s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,
                            %s,%s,%s,%s,
                            %s,%s,%s
                        )
                        RETURNING id
                    """

                    cur.execute(
                        sql,
                        (
                            data_envio, hora_envio, prestador_id, tipo_servico, corte_id,
                            ordem_corte, codigo_corte, descricao_corte,
                            colecao, material, cliente, cores,
                            prioridade, forma_pagamento, status_envio,
                            qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3,
                            valor_pp, valor_p, valor_m, valor_g, valor_gg, valor_g1, valor_g2, valor_g3,
                            total_pecas, total_pilotos, valor_total_envio,
                            resumo_pilotos, aviamentos, outros, observacoes,
                            tel_encarregado, tel_acabamento, previsao_entrega,
                        )
                    )
                    envio_id = cur.fetchone()[0]
                    conn.commit()

            messagebox.showinfo("Sucesso", f"Envio registrado com sucesso! ID: {envio_id}")
            self._limpar()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar envio:\n{e}")

    def _atualizar_saldo_pos_envio(self, corte_id: int):
        """
        Recarrega apenas os saldos (labels 'disp') do corte na grade,
        mantendo todos os campos digitados pelo usuário.
        """
        try:
            from BANCO_DE_DADOS_PG import get_conn, get_schema

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {get_schema()};")
                    # Quais colunas existem
                    cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = %s AND table_name = 'cadastro_de_corte'
                    """, (get_schema(),))
                    cols = {r[0] for r in cur.fetchall()}
                    tamanhos_db = [c for c in ["pp", "p", "m", "g", "gg", "g1", "g2", "g3"] if c in cols]
                    if not tamanhos_db:
                        return

                    select_cols = ", ".join(tamanhos_db)
                    cur.execute(f"SELECT {select_cols} FROM {get_schema()}.cadastro_de_corte WHERE id=%s", (corte_id,))
                    row = cur.fetchone()
                    if not row:
                        return

                    # Atualiza somente os labels de 'Disponível' na UI
                    for i, col in enumerate(tamanhos_db):
                        tam_ui = col.upper()
                        if tam_ui in self.grade_widgets and "disp" in self.grade_widgets[tam_ui]:
                            self.grade_widgets[tam_ui]["disp"].configure(text=str(int(row[i])))

        except Exception:
            pass

    def _recarregar_lista_cortes(self):
        termo = (self.busca_entry.get() or "").strip()
        if termo:
            self.buscar_cortes()
        else:
            self._buscar_cortes_iniciais()

    def preview_impressao(self):
        if not self._prestador_id or not self.corte_selecionado:
            messagebox.showwarning("Aviso", "Selecione prestador e corte.")
            return

        # Gera PDF temporário e abre com o visualizador padrão do sistema
        try:
            pdf_path = self._gerar_pdf()
            if not pdf_path:
                # _gerar_pdf já mostrou mensagem (ex.: reportlab não instalado)
                return
            self._abrir_pdf(pdf_path)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar pré-visualização:\n{e}")

    def exportar_pdf(self):
        if not self._prestador_id or not self.corte_selecionado:
            messagebox.showwarning("Aviso", "Selecione prestador e corte.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Salvar PDF como"
        )
        if not file_path:
            return

        try:
            pdf_path = self._gerar_pdf(file_path)
            if not pdf_path:
                return
            messagebox.showinfo("Sucesso", f"PDF salvo em:\n{pdf_path}")
            # Se quiser, já abre o PDF salvo:
            # self._abrir_pdf(pdf_path)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar PDF:\n{e}")

    def _abrir_pdf(self, pdf_path: str):
        """Abre o PDF usando o visualizador padrão do sistema (Windows/macOS/Linux)."""
        try:
            if sys.platform.startswith("win"):
                os.startfile(pdf_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", pdf_path])
            else:
                # Linux / outros: tenta abrir no navegador ou aplicativo padrão
                # Garante formato file:// para webbrowser
                if not pdf_path.startswith("file://"):
                    url = "file://" + pdf_path
                else:
                    url = pdf_path
                webbrowser.open_new_tab(url)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o PDF:\n{e}")

    def _gerar_pdf(self, output_path=None):
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.lib.colors import Color, black, gray
        except ImportError:
            messagebox.showerror(
                "Erro",
                "Biblioteca 'reportlab' não instalada.\n\n"
                "Instale com:\n\n"
                "pip install reportlab"
            )
            return None

        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".pdf", prefix="envio_corte_")
            os.close(fd)

        # Funções auxiliares
        def safe_int(v):
            try:
                s = str(v).strip()
                if not s:
                    return 0
                return int(float(s.replace(",", ".")))
            except Exception:
                return 0

        def parse_valor(v):
            try:
                s = str(v).strip().replace(".", "").replace(",", ".")
                if not s:
                    return 0.0
                return float(s)
            except Exception:
                return 0.0

        # ---------- Dados ----------
        prest_nome = self._prestador_nome
        prest_tel = self.telefone_entry.get()
        prest_banco = self.banco_entry.get()
        prest_agencia = self.agencia_entry.get()
        prest_conta = self.conta_entry.get()
        prest_pix = self.pix_entry.get()
        prest_titular = self.titular_entry.get()
        prest_email = self.email_entry.get()
        prest_endereco = self.endereco_entry.get()

        corte_codigo = self.codigo_entry.get()
        corte_desc = self.descricao_entry.get()
        corte_ordem = self.ordem_entry.get()

        # Novos campos
        colecao = self.colecao_entry.get()
        material = self.material_entry.get()
        cliente = self.cliente_entry.get()

        # Obter cores selecionadas
        cores_selecionadas = []
        cores_opcoes = ["Preto", "Branco", "Vermelho", "Azul", "Verde", "Amarelo",
                        "Rosa", "Roxo", "Laranja", "Cinza", "Marrom", "Bege",
                        "Estampado", "Listrado", "Xadrez", "Bordô", "Mostarda", "Turquesa"]

        for cor in cores_opcoes:
            if hasattr(self, 'cores_vars') and cor in self.cores_vars:
                if self.cores_vars[cor].get():
                    cores_selecionadas.append(cor)

        cores_texto = ", ".join(cores_selecionadas) if cores_selecionadas else "Não informado"

        data_envio = self.data_entry.get()
        hora_envio = datetime.now().strftime("%H:%M")
        tipo_servico = getattr(self, "_tipo_servico", "")

        # Campos adicionais
        prioridade = self.prioridade_cb.get()
        pagamento = self.pagamento_cb.get()
        tel_encarregado = self.tel_encarregado_entry.get()
        tel_acabamento = self.tel_acabamento_entry.get()

        aviamentos = self.aviamentos_entry.get("1.0", "end-1c")
        outros = self.outros_entry.get("1.0", "end-1c")
        obs = self.obs_text.get("1.0", "end-1c")

        # Quantidades e valores
        qtds = {t: safe_int(self.quantidades[t].get()) for t in self.tamanhos}
        pils = {t: safe_int(self.pilotos[t].get()) for t in self.tamanhos}
        vals = {t: parse_valor(self.valores[t].get()) for t in self.tamanhos}
        totais = {t: (qtds[t] + pils[t]) * vals[t] for t in self.tamanhos}
        total_geral = sum(totais.values())
        total_pecas = sum(qtds.values()) + sum(pils.values())

        # ---------- Criar PDF ----------
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4

        # Cores
        cor_primaria = Color(0.2, 0.4, 0.6)  # Azul escuro
        cor_secundaria = Color(0.8, 0.9, 0.95)  # Azul claro
        cor_cinza = Color(0.95, 0.95, 0.95)

        # Cabeçalho com fundo colorido
        c.setFillColor(cor_primaria)
        c.rect(0, height - 30 * mm, width, 30 * mm, fill=1, stroke=0)

        # Logo
        if PIL_OK and os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH)
                w, h = img.size
                max_w = 30 * mm
                scale = max_w / w
                img_w = w * scale
                img_h = h * scale

                c.drawImage(
                    LOGO_PATH,
                    width - 40 * mm,
                    height - 22 * mm,
                    width=img_w,
                    height=img_h,
                    mask='auto'
                )
            except Exception:
                pass

        # Título
        c.setFont("Helvetica-Bold", 18)
        c.setFillColorRGB(1, 1, 1)
        c.drawString(20 * mm, height - 20 * mm, "CONTROLE DE MÃO DE OBRA")

        c.setFont("Helvetica", 11)
        c.drawString(20 * mm, height - 26 * mm, "Envio de Corte - Comprovante")

        # Data e hora
        c.setFont("Helvetica", 9)
        c.drawString(width - 85 * mm, height - 26 * mm, f"Data/Hora: {data_envio} {hora_envio}")

        # Linha separadora
        c.setStrokeColor(cor_primaria)
        c.setLineWidth(1)
        c.line(20 * mm, height - 35 * mm, width - 20 * mm, height - 35 * mm)

        # ---------- SEÇÃO 1: Dados do Prestador ----------
        y = height - 42 * mm

        # Título da seção
        c.setFillColor(cor_primaria)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, y, "DADOS DO PRESTADOR")

        # Altura do cartão
        altura_conteudo = 36 * mm  # Aumentado para mais campos

        # Retângulo de fundo
        c.setFillColor(cor_cinza)
        c.rect(20 * mm, y - altura_conteudo, width - 40 * mm, altura_conteudo, fill=1, stroke=0)
        c.setStrokeColor(gray)
        c.setLineWidth(0.5)
        c.rect(20 * mm, y - altura_conteudo, width - 40 * mm, altura_conteudo, fill=0, stroke=1)

        # Conteúdo
        y_start = y - 8 * mm

        # Linha 1: Nome e Telefone
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_start, "Nome:")
        c.setFont("Helvetica", 9)
        nome_text = prest_nome or ""
        if len(nome_text) > 25:
            nome_text = nome_text[:22] + "..."
        c.drawString(42 * mm, y_start, nome_text)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width / 2 + 10 * mm, y_start, "Telefone:")
        c.setFont("Helvetica", 9)
        c.drawString(width / 2 + 35 * mm, y_start, prest_tel or "")

        # Linha 2: CPF e Email
        y_start -= 5 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_start, "CPF:")
        c.setFont("Helvetica", 9)
        c.drawString(42 * mm, y_start, self.cpf_entry.get() or "")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width / 2 + 10 * mm, y_start, "Email:")
        c.setFont("Helvetica", 9)
        email_text = prest_email or ""
        if len(email_text) > 25:
            email_text = email_text[:22] + "..."
        c.drawString(width / 2 + 35 * mm, y_start, email_text)

        # Linha 3: Banco e Endereço
        y_start -= 5 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_start, "Banco:")
        c.setFont("Helvetica", 9)
        c.drawString(42 * mm, y_start, prest_banco or "")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width / 2 + 10 * mm, y_start, "Endereço:")
        c.setFont("Helvetica", 9)
        endereco_text = prest_endereco or ""
        if len(endereco_text) > 25:
            endereco_text = endereco_text[:22] + "..."
        c.drawString(width / 2 + 35 * mm, y_start, endereco_text)

        # Linha 4: Agência e Conta
        y_start -= 5 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_start, "Agência:")
        c.setFont("Helvetica", 9)
        c.drawString(42 * mm, y_start, prest_agencia or "")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width / 2 + 10 * mm, y_start, "Conta:")
        c.setFont("Helvetica", 9)
        c.drawString(width / 2 + 35 * mm, y_start, prest_conta or "")

        # Linha 5: PIX e Titular
        y_start -= 5 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_start, "PIX:")
        c.setFont("Helvetica", 9)
        c.drawString(42 * mm, y_start, prest_pix or "")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width / 2 + 10 * mm, y_start, "Titular:")
        c.setFont("Helvetica", 9)
        titular_text = prest_titular or ""
        if len(titular_text) > 25:
            titular_text = titular_text[:22] + "..."
        c.drawString(width / 2 + 35 * mm, y_start, titular_text)

        # ---------- SEÇÃO 2: Dados do Corte ----------
        y = y_start - 12 * mm

        # Título da seção
        c.setFillColor(cor_primaria)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, y, "DADOS DO CORTE")

        # Altura
        altura_corte = 30 * mm  # Aumentado para incluir novos campos

        # Retângulo de fundo
        c.setFillColor(cor_cinza)
        c.rect(20 * mm, y - altura_corte, width - 40 * mm, altura_corte, fill=1, stroke=0)
        c.setStrokeColor(gray)
        c.rect(20 * mm, y - altura_corte, width - 40 * mm, altura_corte, fill=0, stroke=1)

        # Conteúdo
        y_corte = y - 8 * mm

        # Linha 1: Ordem, Código, Serviço
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_corte, "Ordem:")
        c.setFont("Helvetica", 9)
        ordem_text = corte_ordem or ""
        c.drawString(42 * mm, y_corte, ordem_text)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(85 * mm, y_corte, "Código:")
        c.setFont("Helvetica", 9)
        codigo_text = corte_codigo or ""
        c.drawString(100 * mm, y_corte, codigo_text)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(140 * mm, y_corte, "Serviço:")
        c.setFont("Helvetica", 9)
        servico_text = tipo_servico or ""
        if len(servico_text) > 12:
            servico_text = servico_text[:10] + "..."
        c.drawString(155 * mm, y_corte, servico_text)

        # Linha 2: Descrição e Cliente
        y_corte -= 5 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_corte, "Descrição:")
        c.setFont("Helvetica", 9)
        desc_text = corte_desc or ""
        if len(desc_text) > 40:
            desc_text = desc_text[:37] + "..."
        c.drawString(50 * mm, y_corte, desc_text)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width / 2 + 10 * mm, y_corte, "Cliente:")
        c.setFont("Helvetica", 9)
        cliente_text = cliente or ""
        if len(cliente_text) > 15:
            cliente_text = cliente_text[:12] + "..."
        c.drawString(width / 2 + 35 * mm, y_corte, cliente_text)

        # Linha 3: Coleção e Material
        y_corte -= 5 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_corte, "Coleção:")
        c.setFont("Helvetica", 9)
        colecao_text = colecao or ""
        c.drawString(45 * mm, y_corte, colecao_text)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(100 * mm, y_corte, "Material:")
        c.setFont("Helvetica", 9)
        material_text = material or ""
        c.drawString(120 * mm, y_corte, material_text)

        # Linha 4: CORES (informação importante)
        y_corte -= 5 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_corte, "Cores:")
        c.setFont("Helvetica", 9)
        # Se houver muitas cores, quebrar em linhas
        if cores_texto:
            if len(cores_texto) > 60:
                # Quebrar em duas linhas
                palavras = cores_texto.split(", ")
                linha1 = ", ".join(palavras[:len(palavras) // 2])
                linha2 = ", ".join(palavras[len(palavras) // 2:])
                c.drawString(42 * mm, y_corte, linha1)
                y_corte -= 4 * mm
                c.drawString(42 * mm, y_corte, linha2)
            else:
                c.drawString(42 * mm, y_corte, cores_texto)

        # Linha 5: Contatos e Informações Adicionais
        y_corte -= 9 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_corte, "Tel Encarregado:")
        c.setFont("Helvetica", 9)
        c.drawString(52 * mm, y_corte, tel_encarregado or "")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(120 * mm, y_corte, "Tel Acabamento:")
        c.setFont("Helvetica", 9)
        c.drawString(148 * mm, y_corte, tel_acabamento or "")

        # Linha 6: Prioridade e Pagamento
        y_corte -= 5 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_corte, "Prioridade:")
        c.setFont("Helvetica", 9)
        c.drawString(48 * mm, y_corte, prioridade)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(120 * mm, y_corte, "Pagamento:")
        c.setFont("Helvetica", 9)
        c.drawString(145 * mm, y_corte, pagamento)

        # ---------- SEÇÃO 3: Tabela de Quantidades ----------
        y_table_start = y_corte - 15 * mm

        # Título da seção
        c.setFillColor(cor_primaria)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, y_table_start, "QUANTIDADES POR TAMANHO")

        y_table_start -= 6 * mm

        # Cabeçalho da tabela
        headers = ["TAM.", "QTD", "PILOTOS", "VALOR", "SUBTOTAL"]
        col_widths = [20 * mm, 18 * mm, 22 * mm, 25 * mm, 28 * mm]
        table_width = sum(col_widths)

        # Posicionar tabela
        table_x = 25 * mm

        # Fundo do cabeçalho
        c.setFillColor(cor_secundaria)
        c.rect(table_x, y_table_start - 6 * mm, table_width, 6 * mm, fill=1, stroke=1)

        # Texto do cabeçalho
        x = table_x
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(black)
        for i, header in enumerate(headers):
            c.drawCentredString(x + col_widths[i] / 2, y_table_start - 3.5 * mm, header)
            x += col_widths[i]

        y_table_start -= 8 * mm

        # Dados da tabela
        y = y_table_start
        c.setFont("Helvetica", 8)
        for i, tam in enumerate(self.tamanhos):
            # Linha zebrada
            if i % 2 == 0:
                c.setFillColor(cor_cinza)
                c.rect(table_x, y - 5 * mm, table_width, 5 * mm, fill=1, stroke=0)

            c.setFillColor(black)
            x = table_x
            # Tamanho
            c.drawCentredString(x + col_widths[0] / 2, y - 3 * mm, tam)
            x += col_widths[0]
            # Quantidade
            c.drawCentredString(x + col_widths[1] / 2, y - 3 * mm, str(qtds[tam]))
            x += col_widths[1]
            # Pilotos
            c.drawCentredString(x + col_widths[2] / 2, y - 3 * mm, str(pils[tam]))
            x += col_widths[2]
            # Valor
            c.drawCentredString(x + col_widths[3] / 2, y - 3 * mm, fmt_dec2_br(vals[tam]))
            x += col_widths[3]
            # Subtotal
            c.drawCentredString(x + col_widths[4] / 2, y - 3 * mm, fmt_dec2_br(totais[tam]))

            y -= 6 * mm

        # Linha de total
        y -= 3 * mm
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        c.line(table_x, y, table_x + table_width, y)

        y -= 6 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(table_x, y, "TOTAL PEÇAS:")
        c.drawRightString(table_x + sum(col_widths[:3]) - 5 * mm, y, str(total_pecas))

        c.drawString(table_x + sum(col_widths[:3]) + 5 * mm, y, "VALOR TOTAL:")
        c.drawRightString(table_x + table_width, y, fmt_dec2_br(total_geral))

        # ---------- SEÇÃO 4: Informações Adicionais ----------
        y_info_start = y - 15 * mm

        # Título da seção
        c.setFillColor(cor_primaria)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, y_info_start, "INFORMAÇÕES ADICIONAIS")

        y_info_start -= 6 * mm

        # Aviamentos
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(25 * mm, y_info_start, "Aviamentos Enviados:")
        c.setFont("Helvetica", 8)

        if aviamentos.strip():
            lines = []
            words = aviamentos.split()
            line = ""
            for word in words:
                if len(line + " " + word) <= 90:
                    line += " " + word
                else:
                    lines.append(line.strip())
                    line = word
            if line:
                lines.append(line.strip())

            for i, line in enumerate(lines[:3]):
                c.drawString(30 * mm, y_info_start - (i + 1) * 4 * mm, line)
            if len(lines) > 3:
                c.drawString(30 * mm, y_info_start - 4 * 4 * mm, "...")
            y_info_start -= len(lines[:3]) * 4 * mm + 4 * mm
        else:
            y_info_start -= 4 * mm

        # Outros
        if outros.strip():
            c.setFont("Helvetica-Bold", 9)
            c.drawString(25 * mm, y_info_start, "Outros (linha, renda, etc.):")
            c.setFont("Helvetica", 8)

            lines = []
            words = outros.split()
            line = ""
            for word in words:
                if len(line + " " + word) <= 90:
                    line += " " + word
                else:
                    lines.append(line.strip())
                    line = word
            if line:
                lines.append(line.strip())

            for i, line in enumerate(lines[:2]):
                c.drawString(30 * mm, y_info_start - (i + 1) * 4 * mm, line)
            if len(lines) > 2:
                c.drawString(30 * mm, y_info_start - 3 * 4 * mm, "...")
            y_info_start -= len(lines[:2]) * 4 * mm + 4 * mm
        else:
            y_info_start -= 4 * mm

        # Observações
        if obs.strip():
            c.setFont("Helvetica-Bold", 9)
            c.drawString(25 * mm, y_info_start, "Observações:")
            c.setFont("Helvetica", 8)

            lines = []
            words = obs.split()
            line = ""
            for word in words:
                if len(line + " " + word) <= 90:
                    line += " " + word
                else:
                    lines.append(line.strip())
                    line = word
            if line:
                lines.append(line.strip())

            for i, line in enumerate(lines[:4]):
                c.drawString(30 * mm, y_info_start - (i + 1) * 4 * mm, line)
            if len(lines) > 4:
                c.drawString(30 * mm, y_info_start - 5 * 4 * mm, "...")

        # ---------- RODAPÉ ----------
        c.setFont("Helvetica", 7)
        c.setFillColor(gray)
        c.drawCentredString(width / 2, 8 * mm, "Documento gerado automaticamente - Sistema de Controle de Mão de Obra")

        # Número de página
        c.drawString(width - 25 * mm, 5 * mm, "Página 1/1")

        c.save()
        return output_path


if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Controle de Mão de Obra — Envio de Cortes")
    root.geometry("1200x900")
    app = EnvioCortes(root)
    root.mainloop()