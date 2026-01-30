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
    """Converte uma string de valor monetário (brasileiro ou internacional) em float.

    Exemplos:
        '1.234,56' -> 1234.56
        '1234,56'  -> 1234.56
        '1234.56'  -> 1234.56
        '15,00'    -> 15.0
        '15.00'    -> 15.0
        '' ou None -> 0.0
    """
    try:
        s = (s or "").strip().replace("R$", "").replace(" ", "")
        if not s:
            return 0.0
        # Primeiro, tente interpretar diretamente (dot decimal)
        try:
            return float(s)
        except Exception:
            pass
        # Caso contrário, trate ponto como separador de milhar e vírgula como decimal
        try:
            return float(s.replace(".", "").replace(",", "."))
        except Exception:
            return 0.0
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
        # Quantidades originais informadas pelo usuário (por tamanho)
        self.quantidades = {t: tk.StringVar(value="0") for t in self.tamanhos}
        # Seleção de envio por tamanho (checkbox)
        self.selecionar_envio = {t: tk.IntVar(value=0) for t in self.tamanhos}
        # Número de cópias retiradas diretamente do corte para cada tamanho (piloto automático)
        # Esses valores serão subtraídos das quantidades enviadas e somados aos pilotos
        self.copias_do_corte = {t: tk.StringVar(value="0") for t in self.tamanhos}
        # Pilotos informados manualmente via o campo "Registrar".
        # Por simplicidade, trataremos a coluna "Pilotos" como editável. O valor exibido representa
        # o número total de pilotos que serão enviados deste tamanho. Quando o usuário ajusta o
        # valor de pilotos, o sistema irá recalcular a quantidade de cópias restantes do corte.
        # `pilotos` armazena o valor mostrado no campo da grade (pilotos a serem enviados).
        self.pilotos = {t: tk.StringVar(value="0") for t in self.tamanhos}
        # Armazenamos o número original de cópias digitadas para cada tamanho.
        # Este valor é usado para debitar corretamente as cópias no corte.
        self.copias_original = {t: 0 for t in self.tamanhos}
        # Saldo base do corte por tamanho (quantidade disponível original)
        self.saldo_base = {t: 0 for t in self.tamanhos}
        # Valor unitário (como string) para cada tamanho
        self.valores = {t: tk.StringVar(value="") for t in self.tamanhos}

        # Valor único
        self.valor_unico_var = tk.IntVar(value=0)

        # Piloto (tam + qtd) - usado para registrar pilotos extras via o painel lateral
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
        # Combobox de costureira usando CTkComboBox com callback adequado
        # Valores serão carregados dinamicamente em _carregar_prestadores
        self.prestador_busca_cb = ctk.CTkComboBox(
            linha,
            width=360,
            values=[],
            state="normal",
            fg_color=self.cor_secundaria, border_color=self.cor_borda,
            button_color=self.cor_primaria, button_hover_color=self.cor_hover,
            text_color=self.cor_texto, dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto, dropdown_hover_color=self.cor_hover,
            command=self._on_prestador_change  # CTkComboBox usa `command` para callback
        )
        self.prestador_busca_cb.set("")
        self.prestador_busca_cb.pack(side="left")

        # Configurar eventos de digitação e perda de foco
        # O evento de seleção é tratado pelo argumento `command` acima
        self.prestador_busca_cb.bind("<KeyRelease>", lambda e: self._filtrar_combo_prestador())
        self.prestador_busca_cb.bind("<Return>", self._on_costureira_selected)
        self.prestador_busca_cb.bind("<FocusOut>", self._on_costureira_selected)

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

        # Cabeçalho da grade, agora com coluna adicional "Cópias Ret. Corte"
        for h, w in [
            ("Sel.", 50),
            ("Tam.", 60),
            ("Disponível", 90),
            ("Cópias Ret. Corte", 90),
            ("Enviar", 90),
            ("Pilotos", 90),
            ("Valor/Peça (R$)", 120),
            ("Subtotal", 110),
        ]:
            ctk.CTkLabel(header_g, text=h, width=w, text_color=self.cor_texto).pack(side="left", padx=2)

        self.grade_widgets = {}
        for tam in self.tamanhos:
            row = ctk.CTkFrame(left, fg_color=self.cor_fundo)
            row.pack(fill="x", pady=2)

            # Seleção rápida (envio total)
            chk_envio = ctk.CTkCheckBox(
                row,
                text="",
                width=50,
                variable=self.selecionar_envio[tam],
                command=lambda T=tam: self._on_toggle_selecionar_envio(T),
                fg_color=self.cor_primaria,
                hover_color=self.cor_hover,
                text_color=self.cor_texto,
                checkmark_color=self.cor_texto,
            )
            chk_envio.pack(side="left", padx=2)

            # Coluna do tamanho
            ctk.CTkLabel(row, text=tam, width=60, text_color=self.cor_texto).pack(side="left", padx=2)

            # Disponível
            lbl_disp = ctk.CTkLabel(row, text="0", width=90, text_color=self.cor_texto)
            lbl_disp.pack(side="left", padx=2)

            # Cópias retiradas do corte: representa o número de cópias removidas do corte para este tamanho.
            # Este campo é editável; ao alterar, o saldo disponível é atualizado e a quantidade a enviar
            # é preenchida automaticamente com o saldo disponível.
            ent_cop = ctk.CTkEntry(row, width=90, textvariable=self.copias_do_corte[tam],
                                   fg_color=self.cor_terciaria, border_color=self.cor_borda, text_color=self.cor_texto)
            ent_cop.pack(side="left", padx=2)
            # Ao editar o campo de cópias, atualize o valor original e recalcule o saldo de cópias
            ent_cop.bind("<KeyRelease>", lambda e, T=tam: self._on_copias_edit(T))

            # Quantidade a enviar (depois de subtrair cópias)
            ent_qtd = ctk.CTkEntry(row, width=90, textvariable=self.quantidades[tam],
                                   fg_color=self.cor_terciaria, border_color=self.cor_borda, text_color=self.cor_texto)
            ent_qtd.pack(side="left", padx=2)
            ent_qtd.bind("<KeyRelease>", self._recalcular)

            # Pilotos: campo editável. O valor digitado representa o número de pilotos que serão enviados.
            ent_pil = ctk.CTkEntry(row, width=90, textvariable=self.pilotos[tam],
                                   fg_color=self.cor_terciaria, border_color=self.cor_borda, text_color=self.cor_texto)
            ent_pil.pack(side="left", padx=2)
            # Ao editar o campo de pilotos, recalcula o saldo de cópias restantes
            ent_pil.bind("<KeyRelease>", lambda e, T=tam: self._on_pilotos_edit(T))

            # Valor unitário
            ent_val = ctk.CTkEntry(row, width=120, textvariable=self.valores[tam], placeholder_text="0,00",
                                   fg_color=self.cor_terciaria, border_color=self.cor_borda, text_color=self.cor_texto,
                                   placeholder_text_color="#888888")
            ent_val.pack(side="left", padx=2)
            # Recalcular subtotais ao editar valor
            ent_val.bind("<KeyRelease>", lambda e, T=tam: self._on_valor_edit(T))

            # Subtotal
            lbl_total = ctk.CTkLabel(row, text=fmt_moeda(0), width=110, text_color=self.cor_texto)
            lbl_total.pack(side="left", padx=2)

            # Armazenar widgets relevantes
            self.grade_widgets[tam] = {
                "disp": lbl_disp,
                "sub": lbl_total,
                "ent_val": ent_val,
                "ent_qtd": ent_qtd,
                "chk_envio": chk_envio,
            }

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
                # Normaliza o nome removendo espaços duplicados
                visivel = " ".join((nome or "").split())
                if visivel:
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
        """
        Quando uma costureira é selecionada no combobox.
        Este método é chamado tanto pelo parâmetro `command` do CTkComboBox
        quanto por eventos de teclado (Return e FocusOut).
        Ele normaliza o nome, obtém o ID correspondente e chama
        _preencher_banco para carregar os dados.
        """
        # Normalizar o nome (remove múltiplos espaços e pontas) para comparação
        nome = " ".join((self.prestador_busca_cb.get() or "").split()).strip()

        # Se for indicação de nenhum prestador ou campo vazio, limpar
        if not nome or nome.startswith("Nenhum prestador"):
            self.prestador_busca_cb.set("")
            self._preencher_banco(None)
            return

        # Tentar obter o ID pelo mapa (nomes normalizados e minúsculos)
        pid = self._prestador_map.get(nome.lower())
        if pid:
            self._preencher_banco(pid)
        else:
            # Fallback: procurar na lista de prestadores filtrados
            for prestador in self.prestadores_filtrados:
                if len(prestador) > 1:
                    n = " ".join((prestador[1] or "").split())
                    if n.lower() == nome.lower():
                        pid = prestador[0]
                        self._prestador_map[nome.lower()] = pid
                        self._preencher_banco(pid)
                        return
            # Se não encontrar
            messagebox.showwarning("Aviso", "Prestador não encontrado.")
            self._preencher_banco(None)

    def _on_prestador_change(self, choice):
        """
        Callback do CTkComboBox quando um item é selecionado.
        Este método é disparado via parâmetro `command` do CTkComboBox.
        Ele normaliza o texto selecionado, atualiza o campo do combobox e
        chama a rotina de seleção para carregar os dados bancários.
        """
        # Se não há escolha (usuário limpou o campo), limpar dados
        if not choice:
            self._preencher_banco(None)
            return

        # Normalizar espaços duplicados e atualizar a seleção
        nome = " ".join(str(choice).split())
        self.prestador_busca_cb.set(nome)

        # Se for indicação de nenhum prestador, limpar
        if nome.startswith("Nenhum prestador"):
            self._preencher_banco(None)
            return

        # Chamar rotina padrão de seleção
        self._on_costureira_selected()

    def _preencher_banco(self, prestador_id):
        """Preenche os dados bancários do prestador selecionado"""
        # Se nenhum prestador foi selecionado, limpar os campos
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
            schema = get_schema()
            # Garantir que prestador_id é inteiro
            try:
                prestador_id = int(prestador_id)
            except Exception:
                pass
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {schema};")
                    # Detectar colunas existentes para PIX (pix ou chave_pix) e ativo
                    cur.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = 'cadastro_faccoes'
                    """, (schema,))
                    cols = {r[0] for r in cur.fetchall()}
                    pix_col = "pix" if "pix" in cols else ("chave_pix" if "chave_pix" in cols else None)
                    ativo_filter = " AND ativo = TRUE" if "ativo" in cols else ""
                    if not pix_col:
                        raise Exception("A tabela cadastro_faccoes não possui coluna PIX (pix/chave_pix).")
                    # Consulta dinâmica com coluna de pix
                    query = f"""
                        SELECT
                            COALESCE(nome,'') AS nome,
                            COALESCE(telefone,'') AS telefone,
                            COALESCE(cpf,'') AS cpf,
                            COALESCE(banco,'') AS banco,
                            COALESCE(agencia,'') AS agencia,
                            COALESCE(conta,'') AS conta,
                            COALESCE({pix_col},'') AS pix,
                            COALESCE(titular_da_conta,'') AS titular_da_conta
                        FROM {schema}.cadastro_faccoes
                        WHERE id=%s {ativo_filter}
                    """
                    cur.execute(query, (prestador_id,))
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
                saldo = safe_int(vals[idx])
                self.saldo_base[tam] = saldo
                self.grade_widgets[tam]["disp"].configure(text=str(saldo))

        # Limpa quantidades enviadas
        for tam in self.tamanhos:
            self.quantidades[tam].set("0")
            self.pilotos[tam].set("0")
            self.valores[tam].set("")
            self.copias_do_corte[tam].set("0")
            self.copias_original[tam] = 0
            self.selecionar_envio[tam].set(0)
            try:
                self.grade_widgets[tam]["ent_qtd"].configure(state="normal")
            except Exception:
                pass

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

    def _set_quantidade_envio(self, tam, valor, bloquear=False):
        try:
            self.quantidades[tam].set(str(max(int(valor), 0)))
        except Exception:
            self.quantidades[tam].set("0")
        try:
            estado = "disabled" if bloquear else "normal"
            self.grade_widgets[tam]["ent_qtd"].configure(state=estado)
        except Exception:
            pass
        self._recalcular()

    def _on_toggle_selecionar_envio(self, tam):
        selecionado = bool(self.selecionar_envio[tam].get())
        if selecionado:
            disponivel = safe_int(self.grade_widgets[tam]["disp"].cget("text"))
            self._set_quantidade_envio(tam, disponivel, bloquear=True)
        else:
            self._set_quantidade_envio(tam, 0, bloquear=False)

    # ----------------------------- Edição de Cópias e Pilotos -----------------------------
    def _on_copias_edit(self, tam):
        """
        Regra correta:
        - "Cópias retiradas do corte" diminui SOMENTE o "Disponível".
        - "ENVIAR" é atualizado automaticamente com o saldo disponível.
        """
        try:
            base = int(self.saldo_base.get(tam, 0) or 0)
            retiradas = safe_int(self.copias_do_corte[tam].get())

            if retiradas < 0:
                retiradas = 0
                self.copias_do_corte[tam].set(0)

            if base > 0 and retiradas > base:
                retiradas = base
                self.copias_do_corte[tam].set(base)

            disponivel = max(base - retiradas, 0)
            self.grade_widgets[tam]["disp"].configure(text=str(disponivel))

            # Armazena o valor original de cópias digitadas
            self.copias_original[tam] = retiradas

            # Atualiza automaticamente o campo ENVIAR com o saldo disponível
            bloquear = bool(self.selecionar_envio[tam].get())
            self._set_quantidade_envio(tam, disponivel, bloquear=bloquear)
        except Exception:
            pass

    def _on_pilotos_edit(self, tam):
        """
        Pilotos NÃO devem recalcular/alterar "Cópias retiradas do corte".
        Pilotos são informados manualmente e entram apenas nos totais/subtotais.
        """
        try:
            p = safe_int(self.pilotos[tam].get())

            if p < 0:
                p = 0
                self.pilotos[tam].set(0)
        except Exception:
            # Se ocorrer algum erro de conversão, ignore
            pass
        # Recalcular totais após ajuste
        try:
            self._recalcular()

        except Exception:
            pass

    def _recalcular(self, event=None):
        total_pecas = 0
        total_valor = 0.0
        for tam in self.tamanhos:
            # Quantidade informada pelo usuário (peças regulares)
            qtd_original = safe_int(self.quantidades[tam].get())
            # Número de pilotos definidos (digitados ou registrados via painel)
            pilotos = safe_int(self.pilotos[tam].get())
            # Valor unitário da peça
            val = parse_valor(self.valores[tam].get())
            # Número total de peças a enviar = regulares + pilotos
            qtd_envio = qtd_original + pilotos
            # Subtotal = total de peças * valor unitário
            sub = qtd_envio * val
            # Atualiza subtotal na UI
            try:
                self.grade_widgets[tam]["sub"].configure(text=fmt_moeda(sub))
            except Exception:
                pass
            total_pecas += qtd_envio
            total_valor += sub
        # Atualiza totais na UI
        try:
            self.lbl_total_pecas.configure(text=str(total_pecas))
            self.lbl_valor_total.configure(text=fmt_moeda(total_valor))
        except Exception:
            pass
        # Atualiza o resumo de pilotos
        try:
            self._update_piloto_resumo()
        except Exception:
            pass

    def _update_piloto_resumo(self):
        pils = [(t, safe_int(self.pilotos[t].get())) for t in self.tamanhos]
        pils = [(t, q) for t, q in pils if q > 0]
        if not pils:
            self.piloto_resumo_lbl.configure(text="Nenhum.")
            return
        txt = ", ".join([f"{t}={q}" for t, q in pils])
        self.piloto_resumo_lbl.configure(text=txt)

    def _registrar_piloto(self):
        """
        Registra pilotos adicionais via painel lateral.
        Ao registrar, incrementa o valor da coluna "Pilotos" para o tamanho selecionado e
        atualiza automaticamente o saldo de cópias restantes.
        """
        tam = self.piloto_tam_var.get()
        qtd = safe_int(self.piloto_qtd_var.get())
        if not qtd:
            return
        # Incrementa o valor de pilotos para o tamanho escolhido
        try:
            current = safe_int(self.pilotos[tam].get())
        except Exception:
            current = 0
        self.pilotos[tam].set(str(current + qtd))
        # Limpa o campo de entrada após registrar
        self.piloto_qtd_var.set("0")
        # Atualiza o saldo de cópias restantes considerando o novo valor de pilotos
        try:
            self._on_pilotos_edit(tam)
        except Exception:
            pass

    # ----------------------------- Métodos de Ação -----------------------------
    def _abrir_calendario(self, entry):
        from datetime import datetime
        import calendar as _cal

        def setar_data(d):
            entry.delete(0, "end")
            entry.insert(0, d.strftime("%d/%m/%Y"))
            top.destroy()

        top = ctk.CTkToplevel(self)
        top.title("Calendário")
        top.resizable(False, False)

        # ===== POSIÇÃO (abre abaixo do entry, como na imagem) =====
        W, H = 300, 300
        self.update_idletasks()
        top.update_idletasks()

        ex = entry.winfo_rootx()
        ey = entry.winfo_rooty()
        eh = entry.winfo_height()

        x = ex
        y = ey + eh + 6

        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        if x + W > sw:
            x = sw - W - 10
        if y + H > sh:
            y = ey - H - 6

        top.geometry(f"{W}x{H}+{x}+{y}")
        # =========================================================

        top.transient(self)
        top.grab_set()

        now = datetime.now()
        ano = now.year
        mes = now.month

        # Navegação
        nav = ctk.CTkFrame(top)
        nav.pack(fill="x", padx=10, pady=5)

        lbl_mes = ctk.CTkLabel(nav, text=f"{_cal.month_name[mes]} {ano}", font=("Arial", 14))
        ctk.CTkButton(nav, text="<", width=30, command=lambda: mudar_mes(-1)).pack(side="left")
        lbl_mes.pack(side="left", expand=True)
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
            lbl_mes.configure(text=f"{_cal.month_name[mes]} {ano}")
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
                    btn = ctk.CTkButton(
                        frame_dias,
                        text=str(dia),
                        width=30,
                        height=30,
                        command=lambda d=dia: setar_data(datetime(ano, mes, d))
                    )
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
            # Zera todas as quantidades informadas
            self.quantidades[tam].set("0")
            # Zera as cópias retiradas do corte
            self.copias_do_corte[tam].set("0")
            # Zera o total de pilotos visíveis
            self.pilotos[tam].set("0")
            # Zera o número original de cópias digitadas
            self.copias_original[tam] = 0
            # Zera saldo base
            self.saldo_base[tam] = 0
            # Limpa seleção rápida
            self.selecionar_envio[tam].set(0)
            # Zera pilotos manuais (mantém compatibilidade, embora não seja usado)
            try:
                self.pilotos_manual[tam] = 0
            except Exception:
                pass
            # Limpa o valor unitário
            self.valores[tam].set("")
            # Reseta o display da coluna "Disponível" e "Subtotal"
            self.grade_widgets[tam]["disp"].configure(text="0")
            self.grade_widgets[tam]["sub"].configure(text=fmt_moeda(0))
            try:
                self.grade_widgets[tam]["ent_qtd"].configure(state="normal")
            except Exception:
                pass
        self.lbl_total_pecas.configure(text="0")
        self.lbl_valor_total.configure(text=fmt_moeda(0))
        self.aviamentos_entry.delete("1.0", "end")
        self.outros_entry.delete("1.0", "end")
        self.obs_text.delete("1.0", "end")
        self.piloto_resumo_lbl.configure(text="Nenhum.")
        # Zera a quantidade de piloto a registrar
        try:
            self.piloto_qtd_var.set("0")
        except Exception:
            pass
        # Deseleciona valor único e restaura campos de valor unitário
        self.valor_unico_var.set(0)
        self._on_toggle_valor_unico()

    def _gerar_pdf(self, caminho_pdf: str | None = None, dados: dict | None = None, abrir_pdf: bool = False) -> str:
        """
        Gera o PDF profissional do "CONTROLE DE MÃO DE OBRA — Envio de Cortes"
        (versão compacta para caber em 1 página).

        - Se `caminho_pdf` for None: cria um arquivo temporário.
        - Se `dados` for None: coleta automaticamente os dados da tela atual (best effort).
        - Se `abrir_pdf` for True: abre o PDF no visualizador padrão.

        Retorna o caminho do PDF gerado.
        """
        from datetime import datetime, date
        import os
        import re
        import sys
        import tempfile
        import webbrowser

        # ReportLab
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_RIGHT

        # ----------------------------
        # Helpers
        # ----------------------------
        def _t(v):
            if v is None:
                return ""
            if isinstance(v, (date, datetime)):
                try:
                    return v.strftime("%d/%m/%Y")
                except Exception:
                    return str(v)
            return str(v).strip()

        def _p(text):
            """Para Paragraph: converte quebras de linha para <br/> (ReportLab)."""
            txt = _t(text)
            txt = txt.replace("\r\n", "\n").replace("\r", "\n")
            txt = re.sub(r"\n{3,}", "\n\n", txt)
            txt = txt.replace("\n", "<br/>")
            return txt.strip() if txt.strip() else "-"

        def _int(v, default=0):
            try:
                if v is None or v == "":
                    return int(default)
                if isinstance(v, (int, float)):
                    return int(v)
                s = str(v).strip()
                if not s:
                    return int(default)
                return int(float(s.replace(".", "").replace(",", ".")))
            except Exception:
                return int(default)

        def _num(v, default=0.0):
            try:
                if v is None or v == "":
                    return float(default)
                if isinstance(v, (int, float)):
                    return float(v)
                s = str(v).strip().replace("R$", "").replace(" ", "")
                if not s:
                    return float(default)
                try:
                    return float(s)
                except Exception:
                    return float(s.replace(".", "").replace(",", "."))
            except Exception:
                return float(default)

        def fmt_moeda(v):
            val = float(_num(v, 0.0))
            s = f"{val:,.2f}"
            return s.replace(",", "X").replace(".", ",").replace("X", ".")

        def fmt_data(v):
            s = _t(v)
            return s if s else "-"

        def _find_logo_path(candidate: str | None):
            c = (candidate or "").strip()
            if c and os.path.exists(c):
                return c
            # tenta variável global do arquivo (se existir)
            try:
                lp = globals().get("LOGO_PATH", "")
                if lp and os.path.exists(lp):
                    return lp
            except Exception:
                pass
            return None

        def _open_pdf(path_pdf: str):
            try:
                abs_path = os.path.abspath(path_pdf)
                if sys.platform.startswith("win"):
                    url = "file:///" + abs_path.replace("\\", "/")
                else:
                    url = "file://" + abs_path
                webbrowser.open(url)
            except Exception:
                pass

        # ----------------------------
        # Caminho do PDF
        # ----------------------------
        if not caminho_pdf:
            fd, caminho_pdf = tempfile.mkstemp(suffix=".pdf", prefix="envio_corte_")
            os.close(fd)

        # ----------------------------
        # Coleta automática (se não vier dados)
        # ----------------------------
        if dados is None:
            # Tenta ler entries mais comuns; se algum não existir, segue vazio
            def _get_entry(attr):
                try:
                    w = getattr(self, attr, None)
                    return w.get() if w is not None else ""
                except Exception:
                    return ""

            def _get_text(attr):
                try:
                    w = getattr(self, attr, None)
                    return w.get("1.0", "end-1c") if w is not None else ""
                except Exception:
                    return ""

            prestador = {
                "nome": _get_entry("prestador_nome_entry") or _get_entry("nome_entry") or getattr(self,
                                                                                                  "_prestador_nome",
                                                                                                  "") or "",
                "telefone": _get_entry("telefone_entry"),
                "banco": _get_entry("banco_entry"),
                "agencia": _get_entry("agencia_entry"),
                "conta": _get_entry("conta_entry"),
                "pix": _get_entry("pix_entry"),
                "titular": _get_entry("titular_entry"),
            }

            corte = {
                "codigo": _get_entry("codigo_entry"),
                "descricao": _get_entry("descricao_entry"),
                "ordem_corte": _get_entry("ordem_entry") or _get_entry("ordem_corte_entry"),
            }

            envio = {
                "data_envio": _get_entry("data_entry") or _get_entry("data_envio_entry"),
                "previsao_entrega": _get_entry("previsao_entry") or _get_entry("previsao_entrega_entry"),
                "tel_encarregado": _get_entry("tel_encarregado_entry"),
                "tel_acabamento": _get_entry("tel_acabamento_entry"),
            }

            aviamentos = _get_text("aviamentos_entry")
            outros = _get_text("outros_entry")
            observacoes = _get_text("obs_text") or _get_text("observacoes_text")

            tamanhos = getattr(self, "tamanhos", ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"])

            itens = []
            total_geral = 0.0

            for tam in tamanhos:
                qtd = 0
                piloto = 0
                valor_peca = 0.0

                try:
                    if hasattr(self, "quantidades") and tam in self.quantidades:
                        qtd = _int(self.quantidades[tam].get(), 0)
                except Exception:
                    pass

                try:
                    if hasattr(self, "pilotos") and tam in self.pilotos:
                        piloto = _int(self.pilotos[tam].get(), 0)
                except Exception:
                    pass

                try:
                    if hasattr(self, "valores") and tam in self.valores:
                        valor_peca = _num(self.valores[tam].get(), 0.0)
                except Exception:
                    pass

                subtotal = (qtd + piloto) * valor_peca
                total_geral += subtotal

                itens.append({
                    "tam": tam,
                    "qtd": qtd,
                    "piloto": piloto,
                    "valor_peca": valor_peca,
                    "subtotal": subtotal,
                })

            dados = {
                "prestador": prestador,
                "corte": corte,
                "envio": envio,
                "itens": itens,
                "totais": {"total_geral": total_geral},
                "campos_texto": {"aviamentos": aviamentos, "outros": outros, "observacoes": observacoes},
                "meta": {
                    "logo_path": globals().get("LOGO_PATH", ""),
                    "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "empresa_nome": "OPERA / EMPRESA",
                },
            }

        # ----------------------------
        # Normaliza dados
        # ----------------------------
        prestador = dados.get("prestador", {}) or {}
        corte = dados.get("corte", {}) or {}
        envio = dados.get("envio", {}) or {}
        itens = dados.get("itens", []) or []
        totais = dados.get("totais", {}) or {}
        campos_texto = dados.get("campos_texto", {}) or {}
        meta = dados.get("meta", {}) or {}

        # Recalcula total (garante consistência)
        itens_norm = []
        total_geral = 0.0
        for it in itens:
            tam = _t(it.get("tam")) or "-"
            qtd = _int(it.get("qtd"), 0)
            piloto = _int(it.get("piloto"), 0)
            valor_peca = _num(it.get("valor_peca"), 0.0)
            subtotal = it.get("subtotal")
            if subtotal is None or subtotal == "":
                subtotal = (qtd + piloto) * valor_peca
            subtotal = _num(subtotal, 0.0)

            total_geral += subtotal
            itens_norm.append({
                "tam": tam, "qtd": qtd, "piloto": piloto, "valor_peca": valor_peca, "subtotal": subtotal
            })

        if totais.get("total_geral") not in (None, ""):
            total_geral = _num(totais.get("total_geral"), total_geral)

        titulo = "CONTROLE DE MÃO DE OBRA — Envio de Cortes"
        gerado_em = _t(meta.get("gerado_em")) or datetime.now().strftime("%d/%m/%Y %H:%M")
        logo_path = _find_logo_path(meta.get("logo_path"))
        empresa_nome = (_t(meta.get("empresa_nome")) or "OPERA / EMPRESA").strip()

        # ----------------------------
        # Documento (margens ok, mas espaçamentos compactos)
        # ----------------------------
        doc = SimpleDocTemplate(
            caminho_pdf,
            pagesize=A4,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title=titulo,
            author="Ópera Fashion",
        )

        styles = getSampleStyleSheet()

        style_title = ParagraphStyle(
            "OPERA_Title",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=15,
            alignment=TA_LEFT,
            spaceAfter=2,
        )
        style_sub = ParagraphStyle(
            "OPERA_Sub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#444444"),
            alignment=TA_LEFT,
        )
        style_value = ParagraphStyle(
            "OPERA_Value",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#222222"),
        )
        style_box_title = ParagraphStyle(
            "OPERA_BoxTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#111111"),
            spaceAfter=2,
        )
        style_total = ParagraphStyle(
            "OPERA_Total",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#111111"),
        )
        style_small = ParagraphStyle(
            "OPERA_Small",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#666666"),
        )

        def build_footer(canvas, _doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.HexColor("#666666"))
            canvas.drawString(16 * mm, 9 * mm, "SISTEMA OPERA — Impressão")
            canvas.drawRightString(210 * mm - 16 * mm, 9 * mm, f"Página {canvas.getPageNumber()}")
            canvas.restoreState()

        def kv_table(title_left: str, rows_left, title_right: str, rows_right):
            left_parts = [Paragraph(title_left, style_box_title)]
            for k, v in rows_left:
                left_parts.append(Paragraph(f"{_t(k)}: <b>{_p(v)}</b>", style_value))

            right_parts = [Paragraph(title_right, style_box_title)]
            for k, v in rows_right:
                right_parts.append(Paragraph(f"{_t(k)}: <b>{_p(v)}</b>", style_value))

            t = Table([[left_parts, right_parts]], colWidths=[(doc.width * 0.5) - 4, (doc.width * 0.5) - 4])
            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (0, 0), 0.6, colors.HexColor("#D0D0D0")),
                ("BOX", (1, 0), (1, 0), 0.6, colors.HexColor("#D0D0D0")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
            ]))
            return t

        def text_box_compacto(title: str, body: str):
            # caixa compacta: padding menor
            elements = [
                Paragraph(title, style_box_title),
                Paragraph(_p(body), style_value),
            ]
            t = Table([[elements]], colWidths=[doc.width])
            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D0D0D0")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
            ]))
            return t

        story = []

        # ----------------------------
        # Cabeçalho
        # ----------------------------
        header_left = [
            Paragraph(titulo, style_title),
            Paragraph(f"Gerado em: {gerado_em}", style_sub),
        ]

        header_right = []
        if logo_path:
            try:
                img = RLImage(logo_path)
                img.drawHeight = 16 * mm
                img.drawWidth = 42 * mm
                header_right.append(img)
            except Exception:
                header_right.append(
                    Paragraph("ÓPERA FASHION", ParagraphStyle("LogoTxt", parent=style_title, alignment=TA_RIGHT)))
        else:
            header_right.append(
                Paragraph("ÓPERA FASHION", ParagraphStyle("LogoTxt", parent=style_title, alignment=TA_RIGHT)))

        header_tbl = Table([[header_left, header_right]], colWidths=[doc.width * 0.70, doc.width * 0.30])
        header_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_tbl)
        story.append(Spacer(1, 1.5 * mm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#222222")))
        story.append(Spacer(1, 4 * mm))

        # ----------------------------
        # Blocos (dados)
        # ----------------------------
        story.append(kv_table(
            "Dados do Prestador",
            [
                ("Nome", prestador.get("nome")),
                ("Telefone", prestador.get("telefone")),
                ("Banco", prestador.get("banco")),
                ("Agência", prestador.get("agencia")),
                ("Conta", prestador.get("conta")),
                ("PIX", prestador.get("pix")),
                ("Titular", prestador.get("titular")),
            ],
            "Dados do Corte / Envio",
            [
                ("Código", corte.get("codigo")),
                ("Descrição", corte.get("descricao")),
                ("Nº Ordem", corte.get("ordem_corte")),
                ("Data", fmt_data(envio.get("data_envio"))),
                ("Previsão de Entrega", fmt_data(envio.get("previsao_entrega"))),
                ("Tel. Encarregado", envio.get("tel_encarregado")),
                ("Tel. Acabamento", envio.get("tel_acabamento")),
            ],
        ))
        story.append(Spacer(1, 4 * mm))

        # ----------------------------
        # Tabela Itens (COMPACTA para 1 página)
        # ----------------------------
        story.append(Paragraph("Itens do Envio", style_box_title))
        story.append(Spacer(1, 1.5 * mm))

        table_data = [["Tam.", "Qtd", "Piloto", "Valor/Peça", "Subtotal"]]
        for it in itens_norm:
            table_data.append([
                it["tam"],
                str(it["qtd"]),
                str(it["piloto"]),
                fmt_moeda(it["valor_peca"]),
                fmt_moeda(it["subtotal"]),
            ])

        # colunas um pouco menores (compacta)
        col_widths = [18 * mm, 16 * mm, 16 * mm, 28 * mm, 28 * mm]
        # altura fixa pra reduzir “crescimento” (header + linhas)
        row_heights = [6 * mm] + [4.6 * mm] * (len(table_data) - 1)

        itens_tbl = Table(table_data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
        itens_tbl.setStyle(TableStyle([
            # Cabeçalho
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, 0), 2),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 2),

            # Corpo
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D0D0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            ("ALIGN", (1, 1), (2, -1), "CENTER"),
            ("ALIGN", (3, 1), (4, -1), "RIGHT"),

            # padding MÍNIMO (principal pra caber 1 página)
            ("LEFTPADDING", (0, 1), (-1, -1), 3),
            ("RIGHTPADDING", (0, 1), (-1, -1), 3),
            ("TOPPADDING", (0, 1), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 1),

            # zebra
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
        ]))
        story.append(itens_tbl)
        story.append(Spacer(1, 2.5 * mm))

        # TOTAL (compacto)
        total_tbl = Table(
            [[Paragraph("TOTAL GERAL:", style_value), Paragraph(fmt_moeda(total_geral), style_total)]],
            colWidths=[doc.width * 0.7, doc.width * 0.3]
        )
        total_tbl.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 1.0, colors.HexColor("#222222")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(total_tbl)
        story.append(Spacer(1, 3 * mm))

        # ----------------------------
        # Caixas (compactas) — Aviamentos / Outros / Observações
        # ----------------------------
        story.append(text_box_compacto("Aviamentos", campos_texto.get("aviamentos", "")))
        story.append(Spacer(1, 2 * mm))
        story.append(text_box_compacto("Outros", campos_texto.get("outros", "")))
        story.append(Spacer(1, 2 * mm))
        story.append(text_box_compacto("Observações", campos_texto.get("observacoes", "")))
        story.append(Spacer(1, 3 * mm))

        # ----------------------------
        # Assinaturas (compactas e na mesma página)
        # ----------------------------
        nome_prest = (_t(prestador.get("nome")) or "").strip()
        if not nome_prest:
            nome_prest = "______________________________"

        assin_tbl = Table(
            [
                ["Assinatura do Prestador", "Assinatura da Empresa"],
                ["______________________________", "______________________________"],
                [f"Nome: {nome_prest}", f"Nome: {empresa_nome}"],
                ["Data: ____/____/________", "Data: ____/____/________"],
            ],
            colWidths=[doc.width * 0.5, doc.width * 0.5],
            rowHeights=[5 * mm, 7 * mm, 5 * mm, 5 * mm]
        )
        assin_tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),

            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),

            ("ALIGN", (0, 1), (-1, 1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("LINEABOVE", (0, 0), (-1, 0), 1.0, colors.HexColor("#222222")),
            ("BOX", (0, 0), (0, -1), 0.6, colors.HexColor("#D0D0D0")),
            ("BOX", (1, 0), (1, -1), 0.6, colors.HexColor("#D0D0D0")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FAFAFA")),

            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(assin_tbl)

        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("Documento gerado automaticamente pelo Sistema Ópera.", style_small))

        # ----------------------------
        # Build
        # ----------------------------
        doc.build(story, onFirstPage=build_footer, onLaterPages=build_footer)

        if abrir_pdf:
            _open_pdf(caminho_pdf)

        return caminho_pdf

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

    def _debitar_do_corte(self, cur, corte_id: int, qtds: dict, copias: dict):
        """
        Debita do cadastro_de_corte as quantidades enviadas (qtds) e as cópias retiradas do corte.

        O débito de estoque considera que cada peça retirada do corte é removida do saldo de peças disponíveis.  Isso
        inclui tanto as peças regulares a serem enviadas quanto as cópias retiradas do corte (independentemente de
        serem utilizadas como pilotos).  As cópias utilizadas como pilotos e as cópias remanescentes já são todas
        contabilizadas na quantidade total de peças retiradas.  Portanto, para cada tamanho o débito total é:

            débito = quantidade_enviada + copias_original

        onde ``copias_original`` representa o número de cópias digitadas pelo usuário para aquele tamanho.

        :param cur: cursor do banco de dados
        :param corte_id: id do corte no cadastro_de_corte
        :param qtds: dict com quantidades regulares a enviar por tamanho (PP, P, ..., G3)
        :param copias: dict com o número de cópias originais retiradas para cada tamanho (PP, P, ..., G3)
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
            # quantidade regular a enviar
            qtd = int(qtds.get(TAM, 0))
            # cópias originais retiradas do corte
            cop = int(copias.get(TAM, 0))
            enviar = qtd + cop
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
                    # Para cada tamanho, calcula a quantidade efetivamente enviada (quantidade informada - cópias retiradas)
                    # e o número total de pilotos (cópias retiradas + manuais). As cópias retiradas são subtraídas das
                    # quantidades enviadas e adicionadas aos pilotos. O dicionário "pilotos" armazena o total de pilotos
                    # (automáticos + manuais), pois a coluna de pilotos da grade exibe este valor.
                    qtds = {}
                    pils = {}
                    for t in self.tamanhos:
                        # Quantidade regular a enviar
                        qtds[t] = safe_int(self.quantidades[t].get())
                        # Número de pilotos enviados
                        pils[t] = safe_int(self.pilotos[t].get())
                    # Debitar do corte com quantidades enviadas e cópias originais
                    # O débito considera a soma de quantidades regulares e cópias retiradas do corte.
                    copias_orig = {}
                    # Também calcula as cópias remanescentes para cada tamanho (cópias originais - pilotos).  Essas
                    # cópias remanescentes serão armazenadas em colunas separadas na tabela de envios e usadas para
                    # futuras operações.
                    leftover_copies = {}
                    for t in self.tamanhos:
                        # ``copias_original`` armazena o número de cópias informadas pelo usuário para cada tamanho.
                        # Se o usuário não informou cópias, o valor será 0.
                        orig = int(self.copias_original.get(t, 0)) if isinstance(self.copias_original, dict) else 0
                        pil = safe_int(self.pilotos[t].get())
                        copias_orig[t] = orig
                        # Cópi as remanescentes (não utilizadas como pilotos) não podem ser negativas
                        leftover_copies[t] = max(orig - pil, 0)
                    self._debitar_do_corte(cur, self.corte_selecionado, qtds, copias_orig)

                    # 2. Insere na tabela de envios
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = %s AND table_name = 'envios_cortes'
                        )
                    """, (get_schema(),))
                    if not cur.fetchone()[0]:
                        # Criar tabela se não existir.  Esta definição inclui todas as colunas necessárias
                        # para registrar quantidades, cópias retiradas, pilotos, valores e informações adicionais
                        # do envio.
                        cur.execute(f"""
                            CREATE TABLE {get_schema()}.envios_cortes (
                                id SERIAL PRIMARY KEY,
                                remessa_id UUID,
                                data_envio DATE NOT NULL,
                                hora_envio TIME,
                                prestador_id INTEGER REFERENCES {get_schema()}.cadastro_faccoes(id),
                                tipo_servico TEXT,
                                corte_id INTEGER REFERENCES {get_schema()}.cadastro_de_corte(id),
                                ordem_corte VARCHAR(50),
                                codigo_corte VARCHAR(100),
                                descricao_corte TEXT,
                                colecao VARCHAR(100),
                                material VARCHAR(100),
                                cliente VARCHAR(200),
                                cores TEXT,
                                prioridade VARCHAR(30),
                                forma_pagamento VARCHAR(50),
                                status_envio VARCHAR(30) DEFAULT 'Enviado',
                                -- Quantidades enviadas por tamanho
                                qtd_pp INTEGER DEFAULT 0,
                                qtd_p  INTEGER DEFAULT 0,
                                qtd_m  INTEGER DEFAULT 0,
                                qtd_g  INTEGER DEFAULT 0,
                                qtd_gg INTEGER DEFAULT 0,
                                qtd_g1 INTEGER DEFAULT 0,
                                qtd_g2 INTEGER DEFAULT 0,
                                qtd_g3 INTEGER DEFAULT 0,
                                -- Cópias remanescentes por tamanho (após descontar os pilotos)
                                copias_pp INTEGER DEFAULT 0,
                                copias_p  INTEGER DEFAULT 0,
                                copias_m  INTEGER DEFAULT 0,
                                copias_g  INTEGER DEFAULT 0,
                                copias_gg INTEGER DEFAULT 0,
                                copias_g1 INTEGER DEFAULT 0,
                                copias_g2 INTEGER DEFAULT 0,
                                copias_g3 INTEGER DEFAULT 0,
                                -- Pilotos enviados por tamanho
                                piloto_pp INTEGER DEFAULT 0,
                                piloto_p  INTEGER DEFAULT 0,
                                piloto_m  INTEGER DEFAULT 0,
                                piloto_g  INTEGER DEFAULT 0,
                                piloto_gg INTEGER DEFAULT 0,
                                piloto_g1 INTEGER DEFAULT 0,
                                piloto_g2 INTEGER DEFAULT 0,
                                piloto_g3 INTEGER DEFAULT 0,
                                -- Valores unitários por tamanho
                                valor_pp NUMERIC(10,2) DEFAULT 0,
                                valor_p  NUMERIC(10,2) DEFAULT 0,
                                valor_m  NUMERIC(10,2) DEFAULT 0,
                                valor_g  NUMERIC(10,2) DEFAULT 0,
                                valor_gg NUMERIC(10,2) DEFAULT 0,
                                valor_g1 NUMERIC(10,2) DEFAULT 0,
                                valor_g2 NUMERIC(10,2) DEFAULT 0,
                                valor_g3 NUMERIC(10,2) DEFAULT 0,
                                total_pecas INTEGER DEFAULT 0,
                                total_pilotos INTEGER DEFAULT 0,
                                valor_total_envio NUMERIC(12,2) DEFAULT 0,
                                resumo_pilotos TEXT,
                                copias_do_corte TEXT,
                                aviamentos TEXT,
                                outros TEXT,
                                observacoes TEXT,
                                tel_encarregado TEXT,
                                tel_acabamento TEXT,
                                previsao_entrega DATE,
                                created_at TIMESTAMP DEFAULT NOW(),
                                updated_at TIMESTAMP DEFAULT NOW()
                            )
                        """)
                    else:
                        # Se a tabela já existe, verifique se as colunas adicionais existem e as adicione se necessário
                        # Lista de colunas esperadas para cópias e campos extras
                        expected_cols = [
                            'copias_pp', 'copias_p', 'copias_m', 'copias_g', 'copias_gg', 'copias_g1', 'copias_g2',
                            'copias_g3',
                            'copias_do_corte', 'hora_envio', 'colecao', 'material', 'cliente', 'cores', 'prioridade',
                            'forma_pagamento', 'status_envio'
                        ]
                        for col in expected_cols:
                            cur.execute("""
                                SELECT column_name
                                FROM information_schema.columns
                                WHERE table_schema = %s AND table_name = 'envios_cortes' AND column_name = %s
                            """, (get_schema(), col))
                            if not cur.fetchone():
                                # Adiciona a coluna com um tipo adequado
                                if col.startswith('copias_'):
                                    cur.execute(
                                        f"ALTER TABLE {get_schema()}.envios_cortes ADD COLUMN {col} INTEGER DEFAULT 0")
                                elif col in ('hora_envio',):
                                    cur.execute(f"ALTER TABLE {get_schema()}.envios_cortes ADD COLUMN {col} TIME")
                                elif col in ('colecao', 'material'):
                                    cur.execute(
                                        f"ALTER TABLE {get_schema()}.envios_cortes ADD COLUMN {col} VARCHAR(100)")
                                elif col == 'cliente':
                                    cur.execute(
                                        f"ALTER TABLE {get_schema()}.envios_cortes ADD COLUMN {col} VARCHAR(200)")
                                elif col in ('cores', 'copias_do_corte', 'observacoes', 'aviamentos', 'outros'):
                                    cur.execute(f"ALTER TABLE {get_schema()}.envios_cortes ADD COLUMN {col} TEXT")
                                elif col in ('prioridade', 'forma_pagamento', 'status_envio'):
                                    cur.execute(
                                        f"ALTER TABLE {get_schema()}.envios_cortes ADD COLUMN {col} VARCHAR(30)")
                                else:
                                    # fallback
                                    cur.execute(f"ALTER TABLE {get_schema()}.envios_cortes ADD COLUMN {col} TEXT")
                        cur.execute("""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_schema = %s AND table_name = 'envios_cortes' AND column_name = 'remessa_id'
                        """, (get_schema(),))
                        if not cur.fetchone():
                            cur.execute(
                                f"ALTER TABLE {get_schema()}.envios_cortes ADD COLUMN remessa_id UUID"
                            )

                    # Inserir dados
                    data_envio = datetime.now().date()
                    previsao_str = self.previsao_entry.get().strip()
                    previsao = None
                    if previsao_str:
                        try:
                            previsao = datetime.strptime(previsao_str, "%d/%m/%Y").date()
                        except Exception:
                            pass

                    # -----------------------------------------------------------------
                    # Compute totals: number of pieces, pilots and total value
                    # total_pecas -> soma de quantidades enviadas + pilotos totais
                    # total_pilotos -> soma de pilotos totais
                    # valor_total_envio -> (quantidade enviada + pilotos totais) * valor unitário de cada tamanho
                    tamanhos_lista = list(self.tamanhos)
                    total_pecas = 0
                    total_pilotos = 0
                    valor_total_envio = 0.0
                    for t in tamanhos_lista:
                        q = qtds.get(t, 0)
                        p = pils.get(t, 0)
                        total_pecas += q + p
                        total_pilotos += p
                        v = parse_valor(self.valores[t].get())
                        valor_total_envio += (q + p) * v
                    # resumo de pilotos para visualização (ex: "PP:2; P:1")
                    resumo_parts = []
                    for t in tamanhos_lista:
                        pt = pils.get(t, 0)
                        if pt:
                            resumo_parts.append(f"{t}:{pt}")
                    resumo_pilotos = "; ".join(resumo_parts) if resumo_parts else None
                    # resumo de cópias retiradas do corte (ex: "PP:1; M:2")
                    copias_parts = []
                    for t in tamanhos_lista:
                        cp = safe_int(self.copias_do_corte[t].get())
                        if cp:
                            copias_parts.append(f"{t}:{cp}")
                    copias_do_corte_str = "; ".join(copias_parts) if copias_parts else None

                    # Inserir dados e retornar o id
                    # Recuperar informações de ordem, código e descrição do corte selecionado
                    # Estas informações são utilizadas nas páginas de retorno para exibir corretamente
                    # o número de ordem, o código do corte e a descrição no histórico.
                    corte_ordem = (self.ordem_entry.get() or "").strip()
                    corte_codigo = (self.codigo_entry.get() or "").strip()
                    corte_desc = (self.descricao_entry.get() or "").strip()
                    import uuid
                    remessa_id = str(uuid.uuid4())
                    cur.execute(f"""
                        INSERT INTO {get_schema()}.envios_cortes (
                            remessa_id, data_envio, hora_envio, prestador_id, tipo_servico, corte_id, ordem_corte, codigo_corte, descricao_corte,
                            qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3,
                            copias_pp, copias_p, copias_m, copias_g, copias_gg, copias_g1, copias_g2, copias_g3,
                            piloto_pp, piloto_p, piloto_m, piloto_g, piloto_gg, piloto_g1, piloto_g2, piloto_g3,
                            valor_pp, valor_p, valor_m, valor_g, valor_gg, valor_g1, valor_g2, valor_g3,
                            aviamentos, outros, observacoes, tel_encarregado, tel_acabamento, previsao_entrega,
                            total_pecas, total_pilotos, valor_total_envio, resumo_pilotos, copias_do_corte
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s
                        )
                        RETURNING id
                    """,
                                (
                                    remessa_id,
                                    data_envio,
                                    datetime.now().time(),
                                    self._prestador_id,
                                    self._tipo_servico,
                                    self.corte_selecionado,
                                    corte_ordem,
                                    corte_codigo,
                                    corte_desc,
                                    # Quantidades a enviar
                                    qtds["PP"], qtds["P"], qtds["M"], qtds["G"], qtds["GG"], qtds["G1"], qtds["G2"],
                                    qtds["G3"],
                                    # Cópias remanescentes (cópias originais - pilotos)
                                    leftover_copies["PP"], leftover_copies["P"], leftover_copies["M"],
                                    leftover_copies["G"], leftover_copies["GG"], leftover_copies["G1"],
                                    leftover_copies["G2"], leftover_copies["G3"],
                                    # Pilotos enviados
                                    pils["PP"], pils["P"], pils["M"], pils["G"], pils["GG"], pils["G1"], pils["G2"],
                                    pils["G3"],
                                    # Valores unitários
                                    parse_valor(self.valores["PP"].get()), parse_valor(self.valores["P"].get()),
                                    parse_valor(self.valores["M"].get()), parse_valor(self.valores["G"].get()),
                                    parse_valor(self.valores["GG"].get()), parse_valor(self.valores["G1"].get()),
                                    parse_valor(self.valores["G2"].get()), parse_valor(self.valores["G3"].get()),
                                    # Textos diversos e dados adicionais
                                    self.aviamentos_entry.get("1.0", "end-1c"),
                                    self.outros_entry.get("1.0", "end-1c"),
                                    self.obs_text.get("1.0", "end-1c"),
                                    self.tel_encarregado_entry.get(),
                                    self.tel_acabamento_entry.get(),
                                    previsao,
                                    # Totais calculados
                                    total_pecas, total_pilotos, valor_total_envio,
                                    resumo_pilotos,
                                    copias_do_corte_str
                                ))
                    # Obter ID do envio recém inserido
                    envio_id_inserted = cur.fetchone()[0]

                    conn.commit()

            messagebox.showinfo("Sucesso", "Envio confirmado e saldo debitado.")
            self._atualizar_saldo_pos_envio(self.corte_selecionado)
            self._recarregar_lista_cortes()
            self._limpar()

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


if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Controle de Mão de Obra — Envio de Cortes")
    root.geometry("1200x900")
    app = EnvioCortes(root)
    root.mainloop()
