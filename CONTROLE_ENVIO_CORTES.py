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
        self.quantidades = {t: ctk.IntVar(value=0) for t in self.tamanhos}
        self.pilotos = {t: ctk.IntVar(value=0) for t in self.tamanhos}
        self.valores = {t: tk.StringVar(value="") for t in self.tamanhos}

        # Valor único
        self.valor_unico_var = tk.IntVar(value=0)

        # Piloto (tam + qtd)
        self.piloto_tam_var = tk.StringVar(value=self.tamanhos[0])
        self.piloto_qtd_var = ctk.IntVar(value=0)

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
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # Cabeçalho + logo - COM TEMA
        header = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        header.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(header, text="CONTROLE DE MÃO DE OBRA — Envio de Cortes",
                     font=("Arial", 18, "bold"), text_color=self.cor_texto).pack(side="left", padx=(0, 6))

        if PIL_OK and os.path.exists(LOGO_PATH):
            img = Image.open(LOGO_PATH)
            w, h = img.size
            tw = 140
            th = int(h * (tw / w))
            self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(tw, th))
            ctk.CTkLabel(header, image=self.logo_img, text="").pack(side="right")

        # Linha: Buscar Corte - COM TEMA
        l_busca = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        l_busca.pack(fill="x", pady=6)

        ctk.CTkLabel(l_busca, text="Buscar Corte:", width=110, text_color=self.cor_texto).pack(side="left", padx=(0, 6))

        self.busca_entry = ctk.CTkEntry(l_busca, width=300, placeholder_text="Número, código ou descrição",
                                        fg_color=self.cor_terciaria, border_color=self.cor_borda,
                                        text_color=self.cor_texto, placeholder_text_color="#888888")
        self.busca_entry.pack(side="left")
        self.busca_entry.bind("<Return>", lambda e: self.buscar_cortes())

        ctk.CTkButton(l_busca, text="Buscar", width=90, command=self.buscar_cortes,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=8)

        # Costureira + Serviço + Dados bancários - COM TEMA
        prest = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        prest.pack(fill="x", pady=8)

        linha = ctk.CTkFrame(prest, fg_color=self.cor_fundo)
        linha.pack(fill="x", pady=(6, 2))

        # Filtro de serviço - COM TEMA
        ctk.CTkLabel(linha, text="Filtrar Serviço:", width=100, text_color=self.cor_texto).pack(side="left",
                                                                                                padx=(2, 5))

        self.filtro_servico_cb = ctk.CTkComboBox(
            linha,
            width=120,
            values=["Carregando..."],
            state="readonly",
            fg_color=self.cor_secundaria, border_color=self.cor_borda,
            button_color=self.cor_primaria, button_hover_color=self.cor_hover,
            text_color=self.cor_texto, dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto, dropdown_hover_color=self.cor_hover
        )
        self.filtro_servico_cb.set("Todos")
        self.filtro_servico_cb.pack(side="left", padx=(0, 10))
        self.filtro_servico_cb.bind("<<ComboboxSelected>>", lambda e: self._aplicar_filtro_servico())

        ctk.CTkLabel(linha, text="Buscar Costureira:", width=120, text_color=self.cor_texto).pack(side="left",
                                                                                                  padx=(0, 6))

        # Combobox de costureira - COM TEMA
        self.prestador_busca_cb = ctk.CTkComboBox(
            linha,
            width=360,
            values=["Digite para buscar..."],
            state="normal",
            fg_color=self.cor_secundaria, border_color=self.cor_borda,
            button_color=self.cor_primaria, button_hover_color=self.cor_hover,
            text_color=self.cor_texto, dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto, dropdown_hover_color=self.cor_hover
        )
        self.prestador_busca_cb.set("")
        self.prestador_busca_cb.pack(side="left")

        # Configurar eventos após o combobox ser criado
        self.prestador_busca_cb.bind("<KeyRelease>", lambda e: self._filtrar_combo_prestador())
        self.prestador_busca_cb.bind("<Return>", self._on_costureira_selected)
        self.prestador_busca_cb.bind("<FocusOut>", self._on_costureira_selected)
        self.prestador_busca_cb.bind("<<ComboboxSelected>>",
                                     lambda e: self._on_prestador_change(self.prestador_busca_cb.get()))

        ctk.CTkLabel(linha, text="Serviço:", width=80, text_color=self.cor_texto).pack(side="left", padx=(20, 6))

        # Combobox de tipo de serviço - COM TEMA
        self.tipo_cb = ctk.CTkComboBox(
            linha,
            width=220,
            values=SERVICOS_FIXOS,
            state="readonly",
            fg_color=self.cor_secundaria, border_color=self.cor_borda,
            button_color=self.cor_primaria, button_hover_color=self.cor_hover,
            text_color=self.cor_texto, dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto, dropdown_hover_color=self.cor_hover
        )
        self.tipo_cb.set("Facção")
        self.tipo_cb.pack(side="left")
        self.tipo_cb.bind("<<ComboboxSelected>>", self._on_tipo_changed)

        # Bancário (somente leitura) - COM TEMA
        banco = ctk.CTkFrame(prest, fg_color=self.cor_fundo)
        banco.pack(fill="x", pady=(10, 6))

        ctk.CTkLabel(banco, text="Dados Bancários do Prestador", font=("Arial", 13, "bold"),
                     text_color=self.cor_texto).pack(anchor="w", padx=4, pady=2)

        grid = ctk.CTkFrame(banco, fg_color=self.cor_fundo)
        grid.pack(fill="x", padx=2)

        def ro(parent, w=220):
            e = ctk.CTkEntry(parent, width=w, fg_color=self.cor_terciaria, border_color=self.cor_borda,
                             text_color=self.cor_texto, state="disabled")
            return e

        l1b = ctk.CTkFrame(grid, fg_color=self.cor_fundo)
        l1b.pack(fill="x", pady=2)
        ctk.CTkLabel(l1b, text="Telefone:", width=90, text_color=self.cor_texto).pack(side="left", padx=4)
        self.telefone_entry = ro(l1b, 220)
        self.telefone_entry.pack(side="left", padx=4)
        ctk.CTkLabel(l1b, text="CPF:", width=60, text_color=self.cor_texto).pack(side="left", padx=4)
        self.cpf_entry = ro(l1b, 180)
        self.cpf_entry.pack(side="left", padx=4)
        ctk.CTkLabel(l1b, text="Banco:", width=70, text_color=self.cor_texto).pack(side="left", padx=4)
        self.banco_entry = ro(l1b, 180)
        self.banco_entry.pack(side="left", padx=4)

        l2b = ctk.CTkFrame(grid, fg_color=self.cor_fundo)
        l2b.pack(fill="x", pady=2)
        ctk.CTkLabel(l2b, text="Agência:", width=90, text_color=self.cor_texto).pack(side="left", padx=4)
        self.agencia_entry = ro(l2b, 160)
        self.agencia_entry.pack(side="left", padx=4)
        ctk.CTkLabel(l2b, text="Conta:", width=60, text_color=self.cor_texto).pack(side="left", padx=4)
        self.conta_entry = ro(l2b, 180)
        self.conta_entry.pack(side="left", padx=4)
        ctk.CTkLabel(l2b, text="PIX:", width=70, text_color=self.cor_texto).pack(side="left", padx=4)
        self.pix_entry = ro(l2b, 220)
        self.pix_entry.pack(side="left", padx=4)

        l3b = ctk.CTkFrame(grid, fg_color=self.cor_fundo)
        l3b.pack(fill="x", pady=2)
        ctk.CTkLabel(l3b, text="Titular da Conta:", width=140, text_color=self.cor_texto).pack(side="left", padx=4)
        self.titular_entry = ro(l3b, 280)
        self.titular_entry.pack(side="left", padx=4)

        # Tabela de cortes - COM TEMA
        tabela_frame = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        tabela_frame.pack(fill="both", expand=True, pady=8)

        # Configurar estilo da Treeview para combinar com o tema
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure("Treeview",
                             background=self.cor_secundaria,
                             foreground=self.cor_texto,
                             fieldbackground=self.cor_secundaria,
                             borderwidth=0,
                             highlightthickness=0)
        self.style.map('Treeview', background=[('selected', self.cor_primaria)])

        # Configurar colunas da treeview
        cols_ui = ["ID", "Número", "Código", "Descrição", "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "Total"]
        self.cortes_tree = ttk.Treeview(tabela_frame, columns=cols_ui, show="headings", height=7, style="Treeview")

        # Configurar cabeçalhos
        headers = {
            "ID": "ID", "Número": "Número", "Código": "Código", "Descrição": "Descrição",
            "PP": "PP", "P": "P", "M": "M", "G": "G", "GG": "GG", "G1": "G1", "G2": "G2", "G3": "G3",
            "Total": "Total"
        }

        for col in cols_ui:
            self.cortes_tree.heading(col, text=headers[col])
            w = 70 if col in ["PP", "P", "M", "G", "GG", "G1", "G2", "G3", "Total"] else 130
            if col in ["ID", "Número"]:
                w = 100
            self.cortes_tree.column(col, width=w, anchor="center")

        sb = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.cortes_tree.yview)
        sb.pack(side="right", fill="y")
        self.cortes_tree.configure(yscrollcommand=sb.set)
        self.cortes_tree.pack(fill="both", expand=True)
        self.cortes_tree.bind("<<TreeviewSelect>>", self.on_corte_selecionado)

        # Detalhes do corte básico - COM TEMA
        det = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        det.pack(fill="x", pady=6)

        l1 = ctk.CTkFrame(det, fg_color=self.cor_fundo)
        l1.pack(fill="x", pady=2)

        ctk.CTkLabel(l1, text="Telefone Encarregado:", width=150, text_color=self.cor_texto).pack(side="left", padx=4)
        self.tel_encarregado_entry = ctk.CTkEntry(l1, width=180, fg_color=self.cor_terciaria,
                                                  border_color=self.cor_borda, text_color=self.cor_texto)
        self.tel_encarregado_entry.pack(side="left", padx=4)

        ctk.CTkLabel(l1, text="Telefone Acabamento:", width=150, text_color=self.cor_texto).pack(side="left", padx=4)
        self.tel_acabamento_entry = ctk.CTkEntry(l1, width=180, fg_color=self.cor_terciaria,
                                                 border_color=self.cor_borda, text_color=self.cor_texto)
        self.tel_acabamento_entry.pack(side="left", padx=4)

        ctk.CTkLabel(l1, text="Data:", width=60, text_color=self.cor_texto).pack(side="left", padx=4)
        self.data_entry = ctk.CTkEntry(l1, width=120, fg_color=self.cor_terciaria,
                                       border_color=self.cor_borda, text_color=self.cor_texto)
        self.data_entry.insert(0, today_str())
        self.data_entry.pack(side="left", padx=4)

        # Previsão de entrega + calendário - COM TEMA
        ctk.CTkLabel(l1, text="Previsão de Entrega:", width=160, text_color=self.cor_texto).pack(side="left", padx=4)
        self.previsao_entry = ctk.CTkEntry(l1, width=120, fg_color=self.cor_terciaria,
                                           border_color=self.cor_borda, text_color=self.cor_texto)
        self.previsao_entry.pack(side="left", padx=(4, 0))

        ctk.CTkButton(l1, text="📅", width=36, command=lambda: self._abrir_calendario(self.previsao_entry),
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=(6, 4))

        self.previsao_entry.bind("<Double-Button-1>", lambda e: self._abrir_calendario(self.previsao_entry))

        l2 = ctk.CTkFrame(det, fg_color=self.cor_fundo)
        l2.pack(fill="x", pady=2)
        ctk.CTkLabel(l2, text="Código:", width=70, text_color=self.cor_texto).pack(side="left", padx=4)
        self.codigo_entry = ctk.CTkEntry(l2, width=180, fg_color=self.cor_terciaria,
                                         border_color=self.cor_borda, text_color=self.cor_texto,
                                         state="disabled")
        self.codigo_entry.pack(side="left", padx=4)

        ctk.CTkLabel(l2, text="Descrição:", width=80, text_color=self.cor_texto).pack(side="left", padx=4)
        self.descricao_entry = ctk.CTkEntry(l2, width=360, fg_color=self.cor_terciaria,
                                            border_color=self.cor_borda, text_color=self.cor_texto,
                                            state="disabled")
        self.descricao_entry.pack(side="left", padx=4)

        ctk.CTkLabel(l2, text="Nº Ordem:", width=80, text_color=self.cor_texto).pack(side="left", padx=4)
        self.ordem_entry = ctk.CTkEntry(l2, width=120, fg_color=self.cor_terciaria,
                                        border_color=self.cor_borda, text_color=self.cor_texto,
                                        state="disabled")
        self.ordem_entry.pack(side="left", padx=4)

        # Área central (2 colunas) - COM TEMA
        mid = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        mid.pack(fill="both", expand=True, pady=6)
        mid.grid_columnconfigure(0, weight=3)
        mid.grid_columnconfigure(1, weight=2)
        mid.grid_rowconfigure(0, weight=1)

        # ESQUERDA (grade) - COM TEMA
        left = ctk.CTkFrame(mid, fg_color=self.cor_fundo)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(left, text="Quantidades por Tamanho", font=("Arial", 13, "bold"),
                     text_color=self.cor_texto).pack(anchor="w", padx=4, pady=2)

        ctrl_valor = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        ctrl_valor.pack(fill="x", pady=(0, 6))

        self.chk_valor_unico = ctk.CTkCheckBox(ctrl_valor, text="Valor único para todos os tamanhos",
                                               variable=self.valor_unico_var, command=self._on_toggle_valor_unico,
                                               fg_color=self.cor_primaria, hover_color=self.cor_hover,
                                               text_color=self.cor_texto, checkmark_color=self.cor_texto)
        self.chk_valor_unico.pack(anchor="w", padx=4)

        header_g = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        header_g.pack(fill="x")

        for h, w in [("Tam.", 60), ("Disponível", 90), ("Enviar", 90), ("Pilotos", 90), ("Valor/Peça (R$)", 120),
                     ("Subtotal", 110)]:
            ctk.CTkLabel(header_g, text=h, width=w, text_color=self.cor_texto).pack(side="left", padx=2)

        self.grade_widgets = {}
        for tam in self.tamanhos:
            row = ctk.CTkFrame(left, fg_color=self.cor_fundo)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=tam, width=60, text_color=self.cor_texto).pack(side="left", padx=2)

            lbl_disp = ctk.CTkLabel(row, text="0", width=90, text_color=self.cor_texto)
            lbl_disp.pack(side="left", padx=2)

            ent_qtd = ctk.CTkEntry(row, width=90, textvariable=self.quantidades[tam],
                                   fg_color=self.cor_terciaria, border_color=self.cor_borda, text_color=self.cor_texto)
            ent_qtd.pack(side="left", padx=2)

            ent_pil = ctk.CTkEntry(row, width=90, textvariable=self.pilotos[tam],
                                   fg_color=self.cor_terciaria, border_color=self.cor_borda, text_color=self.cor_texto)
            ent_pil.pack(side="left", padx=2)

            ent_val = ctk.CTkEntry(row, width=120, textvariable=self.valores[tam], placeholder_text="0,00",
                                   fg_color=self.cor_terciaria, border_color=self.cor_borda, text_color=self.cor_texto,
                                   placeholder_text_color="#888888")
            ent_val.pack(side="left", padx=2)
            ent_val.bind("<KeyRelease>", lambda e, T=tam: self._on_valor_edit(T))

            ent_qtd.bind("<KeyRelease>", self._recalcular)
            ent_pil.bind("<KeyRelease>", lambda e: (self._recalcular(), self._update_piloto_resumo()))

            lbl_total = ctk.CTkLabel(row, text=fmt_moeda(0), width=110, text_color=self.cor_texto)
            lbl_total.pack(side="left", padx=2)

            self.grade_widgets[tam] = {"disp": lbl_disp, "sub": lbl_total, "ent_val": ent_val}

        # Totais - COM TEMA
        totais = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        totais.pack(fill="x", pady=(6, 2))

        ctk.CTkLabel(totais, text="Total de Peças:", width=120, font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=4)

        self.lbl_total_pecas = ctk.CTkLabel(totais, text="0", font=("Arial", 12, "bold"), text_color=self.cor_texto)
        self.lbl_total_pecas.pack(side="left", padx=4)

        ctk.CTkLabel(totais, text="Valor Total:", width=110, font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=12)

        self.lbl_valor_total = ctk.CTkLabel(totais, text=fmt_moeda(0), font=("Arial", 12, "bold"),
                                            text_color=self.cor_texto)
        self.lbl_valor_total.pack(side="left", padx=4)

        # Botões de ação - COM TEMA
        botoes = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        botoes.pack(fill="x", pady=(6, 8))

        ctk.CTkButton(botoes, text="Confirmar Envio", width=160, command=self.confirmar_envio,
                      fg_color=self.cor_sucesso, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)

        ctk.CTkButton(botoes, text="Pré-visualizar PDF", width=150, command=self.preview_impressao,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)

        ctk.CTkButton(botoes, text="Exportar PDF", width=140, command=self.exportar_pdf,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)

        ctk.CTkButton(botoes, text="Limpar", width=120, command=self._limpar,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)

        # DIREITA (piloto + textos) - COM TEMA
        right = ctk.CTkFrame(mid, fg_color=self.cor_fundo)
        right.grid(row=0, column=1, sticky="nsew")

        sec_piloto = ctk.CTkFrame(right, fg_color=self.cor_fundo)
        sec_piloto.pack(fill="x", pady=(4, 8))

        ctk.CTkLabel(sec_piloto, text="Piloto Enviado", font=("Arial", 13, "bold"),
                     text_color=self.cor_texto).pack(anchor="w", padx=4, pady=(4, 2))

        lp = ctk.CTkFrame(sec_piloto, fg_color=self.cor_fundo)
        lp.pack(fill="x", padx=4, pady=4)

        ctk.CTkLabel(lp, text="Tamanho:", width=80, text_color=self.cor_texto).pack(side="left")

        # Combobox de tamanhos para piloto - COM TEMA
        piloto_tam_cb = ctk.CTkComboBox(
            lp,
            width=100,
            values=self.tamanhos,
            variable=self.piloto_tam_var,
            state="readonly",
            fg_color=self.cor_secundaria, border_color=self.cor_borda,
            button_color=self.cor_primaria, button_hover_color=self.cor_hover,
            text_color=self.cor_texto, dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto, dropdown_hover_color=self.cor_hover
        )
        piloto_tam_cb.set(self.tamanhos[0])
        piloto_tam_cb.pack(side="left", padx=4)

        ctk.CTkLabel(lp, text="Qtd:", width=40, text_color=self.cor_texto).pack(side="left")

        ctk.CTkEntry(lp, width=80, textvariable=self.piloto_qtd_var,
                     fg_color=self.cor_terciaria, border_color=self.cor_borda, text_color=self.cor_texto).pack(
            side="left", padx=4)

        ctk.CTkButton(lp, text="Registrar", width=100, command=self._registrar_piloto,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=6)

        self.piloto_resumo_lbl = ctk.CTkLabel(sec_piloto, text="Nenhum.", anchor="w", text_color=self.cor_texto)
        self.piloto_resumo_lbl.pack(fill="x", padx=4, pady=(0, 4))

        # Área de textos - COM TEMA
        ctk.CTkLabel(right, text="Aviamentos Enviados:", text_color=self.cor_texto).pack(anchor="w", padx=4)

        self.aviamentos_entry = ctk.CTkTextbox(right, height=60, fg_color=self.cor_terciaria,
                                               border_color=self.cor_borda, text_color=self.cor_texto)
        self.aviamentos_entry.pack(fill="both", expand=False, padx=4, pady=4)

        ctk.CTkLabel(right, text="Outros (linha, renda, aparelhos, etc.):", text_color=self.cor_texto).pack(anchor="w",
                                                                                                            padx=4)

        self.outros_entry = ctk.CTkTextbox(right, height=60, fg_color=self.cor_terciaria,
                                           border_color=self.cor_borda, text_color=self.cor_texto)
        self.outros_entry.pack(fill="both", expand=False, padx=4, pady=4)

        ctk.CTkLabel(right, text="Observações:", text_color=self.cor_texto).pack(anchor="w", padx=4)

        self.obs_text = ctk.CTkTextbox(right, height=120, fg_color=self.cor_terciaria,
                                       border_color=self.cor_borda, text_color=self.cor_texto)
        self.obs_text.pack(fill="both", expand=True, padx=4, pady=4)

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
        else:
            for prestador in self.prestadores_filtrados:
                if len(prestador) > 1 and prestador[1] and prestador[1].lower() == nome.lower():
                    self._prestador_map[nome.lower()] = prestador[0]
                    self._preencher_banco(prestador[0])
                    return

            messagebox.showwarning("Aviso", "Prestador não encontrado.")
            self._preencher_banco(None)

    def _on_prestador_change(self, choice):
        """Callback do combobox quando seleciona um item da lista."""
        if choice and not choice.startswith("Nenhum prestador"):
            self._on_costureira_selected()

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
                        SELECT nome, telefone, cpf, banco, agencia, conta, chave_pix, titular_da_conta
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
        """SELECT padrão: id, numero(qualquer nome do banco), codigo, descricao, pp..g3, total."""
        cols = self._corte_schema["all_cols"]
        numero = self._corte_schema["numero"] or "'' AS numero"
        codigo = self._corte_schema["codigo"] or "'' AS codigo"
        descricao = self._corte_schema["descricao"] or "'' AS descricao"

        if self._corte_schema["total"] and self._corte_schema["total"] in cols:
            total = self._corte_schema["total"]
        else:
            total = "0 AS total_pecas"

        def col_or_zero(c):
            return c if c in cols else f"0 AS {c}"

        return ", ".join([
            "id",
            numero,
            codigo,
            descricao,
            col_or_zero("pp"), col_or_zero("p"), col_or_zero("m"), col_or_zero("g"),
            col_or_zero("gg"), col_or_zero("g1"), col_or_zero("g2"), col_or_zero("g3"),
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
        self.codigo_entry.configure(state="normal")
        self.descricao_entry.configure(state="normal")
        self.ordem_entry.configure(state="normal")

        self.codigo_entry.delete(0, "end")
        self.codigo_entry.insert(0, vals[2] if len(vals) > 2 else "")
        self.descricao_entry.delete(0, "end")
        self.descricao_entry.insert(0, vals[3] if len(vals) > 3 else "")
        self.ordem_entry.delete(0, "end")
        self.ordem_entry.insert(0, vals[1] if len(vals) > 1 else "")

        self.codigo_entry.configure(state="disabled")
        self.descricao_entry.configure(state="disabled")
        self.ordem_entry.configure(state="disabled")

        # Preenche grade com saldos
        cols_tam = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]
        for i, tam in enumerate(cols_tam):
            idx = 4 + i  # após id, numero, codigo, descricao
            if idx < len(vals):
                self.grade_widgets[tam]["disp"].configure(text=str(safe_int(vals[idx])))

        # Limpa quantidades enviadas
        for tam in self.tamanhos:
            self.quantidades[tam].set(0)
            self.pilotos[tam].set(0)
            self.valores[tam].set("")

        self._recalcular()

    # ----------------------------- Métodos de Grade -----------------------------
    def _on_toggle_valor_unico(self):
        if self.valor_unico_var.get():
            primeiro_valor = None
            for tam in self.tamanhos:
                v = self.valores[tam].get().strip()
                if v and parse_valor(v) > 0:
                    primeiro_valor = v
                    break
            if primeiro_valor:
                for tam in self.tamanhos:
                    self.valores[tam].set(primeiro_valor)
            for tam in self.tamanhos:
                self.grade_widgets[tam]["ent_val"].configure(state="disabled")
        else:
            for tam in self.tamanhos:
                self.grade_widgets[tam]["ent_val"].configure(state="normal")

    def _on_valor_edit(self, tam):
        if self.valor_unico_var.get():
            v = self.valores[tam].get()
            for t in self.tamanhos:
                self.valores[t].set(v)
        self._recalcular()

    def _recalcular(self, event=None):
        total_pecas = 0
        total_valor = 0.0
        for tam in self.tamanhos:
            qtd = safe_int(self.quantidades[tam].get())
            pil = safe_int(self.pilotos[tam].get())
            val = parse_valor(self.valores[tam].get())
            sub = (qtd + pil) * val
            self.grade_widgets[tam]["sub"].configure(text=fmt_moeda(sub))
            total_pecas += qtd + pil
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
    def _abrir_calendario(self, entry):
        def setar_data(d):
            entry.delete(0, "end")
            entry.insert(0, d.strftime("%d/%m/%Y"))
            top.destroy()

        top = ctk.CTkToplevel(self)
        top.title("Calendário")
        top.geometry("300x300")
        top.transient(self)
        top.grab_set()

        now = datetime.now()
        ano = now.year
        mes = now.month

        # Navegação
        nav = ctk.CTkFrame(top)
        nav.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(nav, text="<", width=30, command=lambda: mudar_mes(-1)).pack(side="left")
        ctk.CTkLabel(nav, text=f"{_cal.month_name[mes]} {ano}", font=("Arial", 14)).pack(side="left", expand=True)
        ctk.CTkButton(nav, text=">", width=30, command=lambda: mudar_mes(1)).pack(side="right")

        # Dias da semana
        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
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
            ctk.CTkLabel(nav, text=f"{_cal.month_name[mes]} {ano}", font=("Arial", 14)).pack(side="left", expand=True)
            desenhar_calendario()

        def desenhar_calendario():
            for w in frame_dias.grid_slaves():
                if int(w.grid_info()["row"]) > 0:
                    w.destroy()

            cal = _cal.monthcalendar(ano, mes)
            for i, semana in enumerate(cal):
                for j, dia in enumerate(semana):
                    if dia == 0:
                        continue
                    btn = ctk.CTkButton(frame_dias, text=str(dia), width=30, height=30,
                                        command=lambda d=dia: setar_data(datetime(ano, mes, d)))
                    btn.grid(row=i + 1, column=j, padx=2, pady=2)

        desenhar_calendario()

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

        total_pecas = sum(safe_int(self.quantidades[t].get()) + safe_int(self.pilotos[t].get()) for t in self.tamanhos)
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
                        enviar = safe_int(self.quantidades[TAM].get()) + safe_int(self.pilotos[TAM].get())
                        if enviar > atual[TAM]:
                            messagebox.showerror("Erro",
                                                 f"Saldo insuficiente para {TAM}. Disponível: {atual[TAM]}, enviar: {enviar}.")
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

    def confirmar_envio(self):
        if not self._validar_envio():
            return

        try:
            from BANCO_DE_DADOS_PG import get_conn, get_schema

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {get_schema()};")
                    # 1. Debita do corte
                    qtds = {t: safe_int(self.quantidades[t].get()) for t in self.tamanhos}
                    pils = {t: safe_int(self.pilotos[t].get()) for t in self.tamanhos}
                    self._debitar_do_corte(cur, self.corte_selecionado, qtds, pils)

                    # 2. Insere na tabela de envios
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = %s AND table_name = 'envios_cortes'
                        )
                    """, (get_schema(),))
                    if not cur.fetchone()[0]:
                        # Criar tabela se não existir
                        cur.execute(f"""
                            CREATE TABLE {get_schema()}.envios_cortes (
                                id SERIAL PRIMARY KEY,
                                data_envio DATE,
                                prestador_id INTEGER,
                                tipo_servico TEXT,
                                corte_id INTEGER,
                                qtd_pp INTEGER DEFAULT 0,
                                qtd_p INTEGER DEFAULT 0,
                                qtd_m INTEGER DEFAULT 0,
                                qtd_g INTEGER DEFAULT 0,
                                qtd_gg INTEGER DEFAULT 0,
                                qtd_g1 INTEGER DEFAULT 0,
                                qtd_g2 INTEGER DEFAULT 0,
                                qtd_g3 INTEGER DEFAULT 0,
                                piloto_pp INTEGER DEFAULT 0,
                                piloto_p INTEGER DEFAULT 0,
                                piloto_m INTEGER DEFAULT 0,
                                piloto_g INTEGER DEFAULT 0,
                                piloto_gg INTEGER DEFAULT 0,
                                piloto_g1 INTEGER DEFAULT 0,
                                piloto_g2 INTEGER DEFAULT 0,
                                piloto_g3 INTEGER DEFAULT 0,
                                valor_pp NUMERIC(10,2) DEFAULT 0,
                                valor_p NUMERIC(10,2) DEFAULT 0,
                                valor_m NUMERIC(10,2) DEFAULT 0,
                                valor_g NUMERIC(10,2) DEFAULT 0,
                                valor_gg NUMERIC(10,2) DEFAULT 0,
                                valor_g1 NUMERIC(10,2) DEFAULT 0,
                                valor_g2 NUMERIC(10,2) DEFAULT 0,
                                valor_g3 NUMERIC(10,2) DEFAULT 0,
                                aviamentos TEXT,
                                outros TEXT,
                                observacoes TEXT,
                                tel_encarregado TEXT,
                                tel_acabamento TEXT,
                                previsao_entrega DATE
                            )
                        """)

                    # Inserir dados
                    data_envio = datetime.now().date()
                    previsao_str = self.previsao_entry.get().strip()
                    previsao = None
                    if previsao_str:
                        try:
                            previsao = datetime.strptime(previsao_str, "%d/%m/%Y").date()
                        except Exception:
                            pass

                    cur.execute(f"""
                        INSERT INTO {get_schema()}.envios_cortes (
                            data_envio, prestador_id, tipo_servico, corte_id,
                            qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3,
                            piloto_pp, piloto_p, piloto_m, piloto_g, piloto_gg, piloto_g1, piloto_g2, piloto_g3,
                            valor_pp, valor_p, valor_m, valor_g, valor_gg, valor_g1, valor_g2, valor_g3,
                            aviamentos, outros, observacoes, tel_encarregado, tel_acabamento, previsao_entrega
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        data_envio, self._prestador_id, self._tipo_servico, self.corte_selecionado,
                        qtds["PP"], qtds["P"], qtds["M"], qtds["G"], qtds["GG"], qtds["G1"], qtds["G2"], qtds["G3"],
                        pils["PP"], pils["P"], pils["M"], pils["G"], pils["GG"], pils["G1"], pils["G2"], pils["G3"],
                        parse_valor(self.valores["PP"].get()), parse_valor(self.valores["P"].get()),
                        parse_valor(self.valores["M"].get()), parse_valor(self.valores["G"].get()),
                        parse_valor(self.valores["GG"].get()), parse_valor(self.valores["G1"].get()),
                        parse_valor(self.valores["G2"].get()), parse_valor(self.valores["G3"].get()),
                        self.aviamentos_entry.get("1.0", "end-1c"),
                        self.outros_entry.get("1.0", "end-1c"),
                        self.obs_text.get("1.0", "end-1c"),
                        self.tel_encarregado_entry.get(),
                        self.tel_acabamento_entry.get(),
                        previsao
                    ))

                    conn.commit()

            messagebox.showinfo("Sucesso", "Envio confirmado e saldo debitado.")
            self._atualizar_saldo_pos_envio(self.corte_selecionado)
            self._recarregar_lista_cortes()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao confirmar envio: {e}")

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

        # Gera PDF temporário e abre no navegador
        try:
            pdf_path = self._gerar_pdf()
            webbrowser.open(pdf_path)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar pré-visualização: {e}")

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
            messagebox.showinfo("Sucesso", f"PDF salvo em: {pdf_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar PDF: {e}")

    def _gerar_pdf(self, output_path=None):
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
        except ImportError:
            messagebox.showerror("Erro", "Biblioteca reportlab não instalada.")
            return

        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".pdf", prefix="envio_corte_")
            os.close(fd)

        # Dados do prestador
        prest_nome = self._prestador_nome
        prest_tel = self.telefone_entry.get()
        prest_banco = self.banco_entry.get()
        prest_agencia = self.agencia_entry.get()
        prest_conta = self.conta_entry.get()
        prest_pix = self.pix_entry.get()
        prest_titular = self.titular_entry.get()

        # Dados do corte
        corte_codigo = self.codigo_entry.get()
        corte_desc = self.descricao_entry.get()
        corte_ordem = self.ordem_entry.get()

        # Outros dados
        data_envio = self.data_entry.get()
        previsao = self.previsao_entry.get()
        tel_enc = self.tel_encarregado_entry.get()
        tel_acab = self.tel_acabamento_entry.get()
        aviamentos = self.aviamentos_entry.get("1.0", "end-1c")
        outros = self.outros_entry.get("1.0", "end-1c")
        obs = self.obs_text.get("1.0", "end-1c")

        # Quantidades e valores
        qtds = {t: safe_int(self.quantidades[t].get()) for t in self.tamanhos}
        pils = {t: safe_int(self.pilotos[t].get()) for t in self.tamanhos}
        vals = {t: parse_valor(self.valores[t].get()) for t in self.tamanhos}
        totais = {t: (qtds[t] + pils[t]) * vals[t] for t in self.tamanhos}
        total_geral = sum(totais.values())

        # Criar PDF
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4

        # Logo
        if PIL_OK and os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH)
                w, h = img.size
                max_w = 50 * mm
                scale = max_w / w
                c.drawImage(LOGO_PATH, width - 60 * mm, height - 30 * mm, width=w * scale, height=h * scale)
            except Exception:
                pass

        # Título
        c.setFont("Helvetica-Bold", 16)
        c.drawString(30 * mm, height - 30 * mm, "CONTROLE DE MÃO DE OBRA — Envio de Cortes")

        # Dados do prestador
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30 * mm, height - 45 * mm, "Dados do Prestador:")
        c.setFont("Helvetica", 10)
        c.drawString(30 * mm, height - 52 * mm, f"Nome: {prest_nome}")
        c.drawString(30 * mm, height - 59 * mm, f"Telefone: {prest_tel}")
        c.drawString(30 * mm, height - 66 * mm, f"Banco: {prest_banco}")
        c.drawString(30 * mm, height - 73 * mm, f"Agência: {prest_agencia}")
        c.drawString(30 * mm, height - 80 * mm, f"Conta: {prest_conta}")
        c.drawString(30 * mm, height - 87 * mm, f"PIX: {prest_pix}")
        c.drawString(30 * mm, height - 94 * mm, f"Titular: {prest_titular}")

        # Dados do corte
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30 * mm, height - 110 * mm, "Dados do Corte:")
        c.setFont("Helvetica", 10)
        c.drawString(30 * mm, height - 117 * mm, f"Código: {corte_codigo}")
        c.drawString(30 * mm, height - 124 * mm, f"Descrição: {corte_desc}")
        c.drawString(30 * mm, height - 131 * mm, f"Nº Ordem: {corte_ordem}")

        # Detalhes do envio
        c.setFont("Helvetica-Bold", 12)
        c.drawString(30 * mm, height - 147 * mm, "Detalhes do Envio:")
        c.setFont("Helvetica", 10)
        c.drawString(30 * mm, height - 154 * mm, f"Data: {data_envio}")
        c.drawString(30 * mm, height - 161 * mm, f"Previsão de Entrega: {previsao}")
        c.drawString(30 * mm, height - 168 * mm, f"Tel. Encarregado: {tel_enc}")
        c.drawString(30 * mm, height - 175 * mm, f"Tel. Acabamento: {tel_acab}")

        # Tabela de quantidades
        y_table = height - 200 * mm
        c.setFont("Helvetica-Bold", 10)
        headers = ["Tam.", "Qtd", "Piloto", "Valor/Peça", "Subtotal"]
        col_widths = [20 * mm, 20 * mm, 20 * mm, 25 * mm, 25 * mm]
        x = 30 * mm
        for i, h in enumerate(headers):
            c.drawString(x, y_table, h)
            x += col_widths[i]

        y_table -= 6 * mm
        c.setFont("Helvetica", 9)
        for tam in self.tamanhos:
            x = 30 * mm
            c.drawString(x, y_table, tam)
            x += col_widths[0]
            c.drawString(x, y_table, str(qtds[tam]))
            x += col_widths[1]
            c.drawString(x, y_table, str(pils[tam]))
            x += col_widths[2]
            c.drawString(x, y_table, fmt_dec2_br(vals[tam]))
            x += col_widths[3]
            c.drawString(x, y_table, fmt_dec2_br(totais[tam]))
            y_table -= 5 * mm

        # Total geral
        y_table -= 5 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30 * mm, y_table, "TOTAL GERAL:")
        c.drawString(30 * mm + sum(col_widths[:4]), y_table, fmt_dec2_br(total_geral))

        # Aviamentos, outros, observações
        y_text = y_table - 15 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30 * mm, y_text, "Aviamentos:")
        c.setFont("Helvetica", 9)
        c.drawString(30 * mm, y_text - 6 * mm, aviamentos[:100] + "..." if len(aviamentos) > 100 else aviamentos)

        y_text -= 12 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30 * mm, y_text, "Outros:")
        c.setFont("Helvetica", 9)
        c.drawString(30 * mm, y_text - 6 * mm, outros[:100] + "..." if len(outros) > 100 else outros)

        y_text -= 12 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30 * mm, y_text, "Observações:")
        c.setFont("Helvetica", 9)
        # Quebra de linha para observações
        obs_lines = []
        line = ""
        for word in obs.split():
            if len(line + " " + word) <= 100:
                line += " " + word
            else:
                obs_lines.append(line)
                line = word
        if line:
            obs_lines.append(line)

        for i, line in enumerate(obs_lines[:5]):
            c.drawString(30 * mm, y_text - 6 * mm - (i * 4 * mm), line.strip())

        c.save()
        return output_path


if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Controle de Mão de Obra — Envio de Cortes")
    root.geometry("1200x900")
    app = EnvioCortes(root)
    root.mainloop()