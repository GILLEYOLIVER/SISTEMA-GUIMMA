# -*- coding: utf-8 -*-
import TEMAS
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import tempfile
import webbrowser

# ---------- LOGO ----------
LOGO_PATH = os.path.join(os.path.dirname(__file__), "LOGO.jpg")

# ---------- ACESSO PG ----------
try:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception as err:
    def get_conn():
        raise RuntimeError("BANCO_DE_DADOS_PG indisponível: " + str(err))


    def get_schema():
        return "public"


    def require_ready(essentials=None):
        return False, "Módulo de acesso não disponível"


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


# ============================== Tela ==============================
class FinalizacaoCortes(ctk.CTkFrame):
    tamanhos = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]

    def __init__(self, master, sistema=None):
        super().__init__(master)
        self.master = master
        self.sistema = sistema
        self.retorno_selecionado = None
        self._prestador_id = None
        self._prestador_nome = ""
        self._tipo_servico = ""
        self.mostrar_finalizados = False

        # Atualiza cores baseado no tema atual - MESMO PADRÃO DO CADASTRO_DE_CORTE
        self.obter_cores_por_tema()

        # Variáveis para campos editáveis
        self.entregues_vars = {t: tk.StringVar(value="0") for t in self.tamanhos}
        self.copias_vars = {t: tk.StringVar(value="0") for t in self.tamanhos}
        self.defeitos_vars = {t: tk.StringVar(value="0") for t in self.tamanhos}
        self.faltantes_vars = {t: tk.StringVar(value="0") for t in self.tamanhos}

        # Dados originais
        self.enviado_por_tam = {t: 0 for t in self.tamanhos}
        self.valor_por_tam = {t: 0.0 for t in self.tamanhos}
        self.pilotos_por_tam = {t: 0 for t in self.tamanhos}

        self.pack(fill="both", expand=True)
        self._build_ui()
        self.carregar_retornos_pendentes()

    # ----------------------------- THEME MANAGEMENT -----------------------------
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
        else:
            self.cor_fundo = "#ffffff"
            self.cor_primaria = "#3a7ebf"
            self.cor_secundaria = "#f0f0f0"
            self.cor_texto = "black"
            self.cor_texto_entry = "black"
            self.cor_placeholder = "#666666"
            self.cor_borda = "#cccccc"
            self.cor_hover = "#2e4a66"

    def configurar_treeview_theme(self):
        """Configura as cores da Treeview baseado no tema atual.

        Ajuste de contraste:
        - Em alguns temas, `self.cor_texto` pode ficar escuro demais para a Treeview.
        - Aqui forçamos uma cor de texto com alto contraste por modo (Dark/Light).
        """
        self.style = ttk.Style()
        self.style.theme_use('default')

        tema_atual = ctk.get_appearance_mode()

        if tema_atual == "Dark":
            cor_fundo = self.cor_secundaria
            cor_texto = "#F8FAFC"          # texto bem claro (alto contraste)
            cor_campo = self.cor_secundaria
            cor_selecao = self.cor_primaria
            cor_heading_fg = "#FFFFFF"
        else:
            cor_fundo = "#f0f0f0"
            cor_texto = "#0B1220"          # texto bem escuro (alto contraste)
            cor_campo = "#f0f0f0"
            cor_selecao = self.cor_primaria
            cor_heading_fg = "#FFFFFF"

        # guarda para reuso nas tags das linhas
        self._tree_fg = cor_texto

        self.style.configure(
            "Custom.Treeview",
            background=cor_fundo,
            foreground=cor_texto,
            fieldbackground=cor_campo,
            borderwidth=0,
            highlightthickness=0,
            rowheight=25,
        )

        self.style.configure(
            "Custom.Treeview.Heading",
            background=self.cor_primaria,
            foreground=cor_heading_fg,
            relief="flat",
            borderwidth=1,
            font=('Arial', 10, 'bold'),
        )

        self.style.map(
            'Custom.Treeview',
            background=[('selected', cor_selecao)],
            foreground=[('selected', 'white')],
        )

    def _recolor_labels_frame(self, frame):
        for widget in frame.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=self.cor_texto)
            if hasattr(widget, "winfo_children"):
                self._recolor_labels_frame(widget)

    def _normalizar_valor(self, var, max_value):
        raw = str(var.get())
        digits = "".join(ch for ch in raw if ch.isdigit())
        if raw != digits:
            var.set(digits)
        if digits == "":
            return 0
        valor = int(digits)
        if max_value > 0 and valor > max_value:
            valor = max_value
            var.set(str(valor))
        return valor


    # ----------------------------- UI -----------------------------
    def _build_ui(self):
        # Atualiza cores antes de construir a UI
        self.obter_cores_por_tema()

        main = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # Título + logo - MESMO ESTILO DO CADASTRO_DE_CORTE
        head = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        head.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            head,
            text="CONTROLE DE MÃO DE OBRA — Finalização de Cortes",
            font=("Arial", 18, "bold"),
            text_color=self.cor_texto
        ).pack(side="left")

        try:
            from PIL import Image
            if os.path.exists(LOGO_PATH):
                img = Image.open(LOGO_PATH)
                w, h = img.size
                tw = 140
                th = int(h * (tw / w))
                self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(tw, th))
                ctk.CTkLabel(head, image=self.logo_img, text="").pack(side="right")
        except Exception:
            pass

        # Buscar retorno + filtro
        busca = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        busca.pack(fill="x", pady=6)

        ctk.CTkLabel(busca, text="Buscar Retorno:", width=120,
                     text_color=self.cor_texto).pack(side="left", padx=(0, 6))

        self.busca_entry = ctk.CTkEntry(busca, width=250,
                                        placeholder_text="Ordem, código ou descrição",
                                        fg_color=self.cor_secundaria,
                                        border_color=self.cor_borda,
                                        text_color=self.cor_texto_entry,
                                        placeholder_text_color=self.cor_placeholder)
        self.busca_entry.pack(side="left")
        self.busca_entry.bind("<Return>", lambda e: self.carregar_retornos_pendentes())

        ctk.CTkButton(busca, text="Buscar", width=90,
                      command=self.carregar_retornos_pendentes,
                      fg_color=self.cor_primaria,
                      hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=8)

        # Checkbox para mostrar finalizados
        self.cb_mostrar_finalizados = ctk.CTkCheckBox(
            busca,
            text="Mostrar Finalizados",
            command=self.toggle_visualizacao_finalizados,
            text_color=self.cor_texto
        )
        self.cb_mostrar_finalizados.pack(side="left", padx=8)

        # Prestador + Serviço
        prest = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        prest.pack(fill="x", pady=(6, 8))

        linha = ctk.CTkFrame(prest, fg_color=self.cor_fundo)
        linha.pack(fill="x", pady=(4, 2))

        ctk.CTkLabel(linha, text="Prestador:", width=100,
                     text_color=self.cor_texto).pack(side="left", padx=4)

        self.prestador_entry = ctk.CTkEntry(linha, width=360,
                                            fg_color=self.cor_secundaria,
                                            border_color=self.cor_borda,
                                            text_color=self.cor_texto_entry)
        self.prestador_entry.pack(side="left", padx=4)
        self.prestador_entry.configure(state="disabled")

        ctk.CTkLabel(linha, text="Serviço:", width=80,
                     text_color=self.cor_texto).pack(side="left", padx=(16, 4))

        self.servico_entry = ctk.CTkEntry(linha, width=220,
                                          fg_color=self.cor_secundaria,
                                          border_color=self.cor_borda,
                                          text_color=self.cor_texto_entry)
        self.servico_entry.pack(side="left")
        self.servico_entry.configure(state="disabled")

        # Tabela de retornos pendentes - MESMO ESTILO DO CADASTRO_DE_CORTE
        tabela_frame = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        tabela_frame.pack(fill="both", expand=True, pady=8)

        cols = ["ID", "Ordem", "Código", "Descrição", "Prestador", "Data Entrada", "Status", "Qtd Peças"]

        # Configurar estilo da Treeview
        self.configurar_treeview_theme()

        self.retornos_tree = ttk.Treeview(tabela_frame, columns=cols, show="headings", height=7,
                                          style="Custom.Treeview")
        sb = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.retornos_tree.yview)
        sb.pack(side="right", fill="y")
        self.retornos_tree.configure(yscrollcommand=sb.set)
        self.retornos_tree.pack(fill="both", expand=True)

        for col in cols:
            self.retornos_tree.heading(col, text=col)
            w = 100 if col in ["ID", "Status"] else (90 if col == "Qtd Peças" else 140)
            self.retornos_tree.column(col, width=w, anchor="center")

        self.retornos_tree.bind("<<TreeviewSelect>>", self.on_retorno_selecionado)

        # Configurar cores das linhas alternadas
        if ctk.get_appearance_mode() == "Dark":
            cor_linha_par = self.cor_fundo
            cor_linha_impar = self.cor_secundaria
        else:
            cor_linha_par = "#ffffff"
            cor_linha_impar = "#f0f0f0"

        # Cores por status
        try:
            self.retornos_tree.tag_configure('status_conferencia', background='#FFF9C4', foreground='black')
            self.retornos_tree.tag_configure('status_finalizado', background='#C8E6C9', foreground='black')
            self.retornos_tree.tag_configure("oddrow", background=cor_linha_impar, foreground=getattr(self, '_tree_fg', self.cor_texto))
            self.retornos_tree.tag_configure("evenrow", background=cor_linha_par, foreground=getattr(self, '_tree_fg', self.cor_texto))
        except Exception:
            pass

        # Detalhes do corte
        det = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        det.pack(fill="x", pady=6)

        l1 = ctk.CTkFrame(det, fg_color=self.cor_fundo)
        l1.pack(fill="x", pady=2)

        ctk.CTkLabel(l1, text="Entrada ID:", width=100,
                     text_color=self.cor_texto).pack(side="left", padx=4)

        self.entrada_id_entry = ctk.CTkEntry(l1, width=120,
                                             fg_color=self.cor_secundaria,
                                             border_color=self.cor_borda,
                                             text_color=self.cor_texto_entry)
        self.entrada_id_entry.pack(side="left", padx=4)
        self.entrada_id_entry.configure(state="disabled")

        ctk.CTkLabel(l1, text="Data Chegada:", width=100,
                     text_color=self.cor_texto).pack(side="left", padx=4)

        self.data_entrada_entry = ctk.CTkEntry(l1, width=180,
                                               fg_color=self.cor_secundaria,
                                               border_color=self.cor_borda,
                                               text_color=self.cor_texto_entry)
        self.data_entrada_entry.pack(side="left", padx=4)
        self.data_entrada_entry.configure(state="disabled")

        l2 = ctk.CTkFrame(det, fg_color=self.cor_fundo)
        l2.pack(fill="x", pady=2)

        ctk.CTkLabel(l2, text="Código:", width=70,
                     text_color=self.cor_texto).pack(side="left", padx=4)

        self.codigo_entry = ctk.CTkEntry(l2, width=180,
                                         fg_color=self.cor_secundaria,
                                         border_color=self.cor_borda,
                                         text_color=self.cor_texto_entry)
        self.codigo_entry.pack(side="left", padx=4)
        self.codigo_entry.configure(state="disabled")

        ctk.CTkLabel(l2, text="Descrição:", width=80,
                     text_color=self.cor_texto).pack(side="left", padx=4)

        self.descricao_entry = ctk.CTkEntry(l2, width=380,
                                            fg_color=self.cor_secundaria,
                                            border_color=self.cor_borda,
                                            text_color=self.cor_texto_entry)
        self.descricao_entry.pack(side="left", padx=4)
        self.descricao_entry.configure(state="disabled")

        ctk.CTkLabel(l2, text="Nº Ordem:", width=80,
                     text_color=self.cor_texto).pack(side="left", padx=4)

        self.ordem_entry = ctk.CTkEntry(l2, width=120,
                                        fg_color=self.cor_secundaria,
                                        border_color=self.cor_borda,
                                        text_color=self.cor_texto_entry)
        self.ordem_entry.pack(side="left", padx=4)
        self.ordem_entry.configure(state="disabled")

        # Área central (grade e observações)
        mid = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        mid.pack(fill="both", expand=True, pady=6)
        mid.grid_columnconfigure(0, weight=3)
        mid.grid_columnconfigure(1, weight=2)
        mid.grid_rowconfigure(0, weight=1)

        # Grade
        left = ctk.CTkFrame(mid, fg_color=self.cor_fundo)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(left, text="Controle por Tamanho - Edite as quantidades",
                     font=("Arial", 13, "bold"),
                     text_color=self.cor_texto).pack(anchor="w", padx=4, pady=(4, 6))

        header_g = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        header_g.pack(fill="x")

        for h, w in [("Tam.", 60), ("Enviado", 80), ("Entregue", 90), ("Cópias", 80), ("Defeito", 80), ("Faltante", 80),
                     ("Regulares", 120), ("Valor/Peça", 100), ("Subtotal", 110)]:
            ctk.CTkLabel(header_g, text=h, width=w,
                         text_color=self.cor_texto).pack(side="left", padx=2)

        self.grade_widgets = {}
        for tam in self.tamanhos:
            row = ctk.CTkFrame(left, fg_color=self.cor_fundo)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=tam, width=60,
                         text_color=self.cor_texto).pack(side="left", padx=2)

            lbl_env = ctk.CTkLabel(row, text="0", width=80,
                                   text_color=self.cor_texto)
            lbl_env.pack(side="left", padx=2)

            ent_ent = ctk.CTkEntry(
                row,
                width=90,
                textvariable=self.entregues_vars[tam],
                fg_color=self.cor_secundaria,
                border_color=self.cor_borda,
                text_color=self.cor_texto_entry,
            )
            ent_ent.pack(side="left", padx=2)
            ent_ent.bind("<KeyRelease>", self._recalcular_totais)

            ent_cop = ctk.CTkEntry(
                row, width=80,
                textvariable=self.copias_vars[tam],
                state="disabled",
                takefocus=0,
                fg_color=self.cor_secundaria,
                border_color=self.cor_borda,
                text_color=self.cor_texto_entry
            )
            ent_cop.pack(side="left", padx=2)

            ent_def = ctk.CTkEntry(
                row,
                width=80,
                textvariable=self.defeitos_vars[tam],
                fg_color=self.cor_secundaria,
                border_color=self.cor_borda,
                text_color=self.cor_texto_entry,
            )
            ent_def.pack(side="left", padx=2)
            ent_def.bind("<KeyRelease>", self._recalcular_totais)

            ent_fal = ctk.CTkEntry(
                row,
                width=80,
                textvariable=self.faltantes_vars[tam],
                fg_color=self.cor_secundaria,
                border_color=self.cor_borda,
                text_color=self.cor_texto_entry,
            )
            ent_fal.pack(side="left", padx=2)
            ent_fal.bind("<KeyRelease>", self._recalcular_totais)

            lbl_reg = ctk.CTkLabel(row, text="0", width=120,
                                   text_color=self.cor_texto)
            lbl_reg.pack(side="left", padx=2)

            lbl_val = ctk.CTkLabel(row, text=fmt_moeda(0), width=100,
                                   text_color=self.cor_texto)
            lbl_val.pack(side="left", padx=2)

            lbl_sub = ctk.CTkLabel(row, text=fmt_moeda(0), width=110,
                                   text_color=self.cor_texto)
            lbl_sub.pack(side="left", padx=2)

            self.grade_widgets[tam] = {
                "enviado": lbl_env,
                "regulares": lbl_reg,
                "valor": lbl_val,
                "subtotal": lbl_sub
            }

        totais = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        totais.pack(fill="x", pady=(6, 8))

        ctk.CTkLabel(totais, text="Total Entregue:", width=140,
                     font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=4)

        self.lbl_total_entregue = ctk.CTkLabel(totais, text="0",
                                               font=("Arial", 12, "bold"),
                                               text_color=self.cor_texto)
        self.lbl_total_entregue.pack(side="left", padx=4)

        ctk.CTkLabel(totais, text="Cópias:", width=80,
                     font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=12)

        self.lbl_total_copias = ctk.CTkLabel(totais, text="0",
                                             font=("Arial", 12, "bold"),
                                             text_color=self.cor_texto)
        self.lbl_total_copias.pack(side="left", padx=4)

        ctk.CTkLabel(totais, text="Defeito:", width=80,
                     font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=12)

        self.lbl_total_defeito = ctk.CTkLabel(totais, text="0",
                                              font=("Arial", 12, "bold"),
                                              text_color=self.cor_texto)
        self.lbl_total_defeito.pack(side="left", padx=4)

        ctk.CTkLabel(totais, text="Faltante:", width=80,
                     font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=12)

        self.lbl_total_faltante = ctk.CTkLabel(totais, text="0",
                                               font=("Arial", 12, "bold"),
                                               text_color=self.cor_texto)
        self.lbl_total_faltante.pack(side="left", padx=4)

        ctk.CTkLabel(totais, text="Regulares (pagas):", width=160,
                     font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=12)

        self.lbl_total_regulares = ctk.CTkLabel(totais, text="0",
                                                font=("Arial", 12, "bold"),
                                                text_color=self.cor_texto)
        self.lbl_total_regulares.pack(side="left", padx=4)

        ctk.CTkLabel(totais, text="Valor Total a Pagar:", width=170,
                     font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=12)

        self.lbl_valor_total = ctk.CTkLabel(totais, text=fmt_moeda(0),
                                            font=("Arial", 12, "bold"),
                                            text_color=self.cor_texto)
        self.lbl_valor_total.pack(side="left", padx=4)

        # --- Bonificação ---
        self.bonif_final_var = tk.StringVar(value="sim")
        bonif_frame = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        bonif_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(bonif_frame, text="Bonificação:", width=120,
                     font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(side="left", padx=4)

        ctk.CTkRadioButton(bonif_frame, text="Sim",
                           variable=self.bonif_final_var, value="sim",
                           text_color=self.cor_texto).pack(side="left", padx=(0, 8))

        ctk.CTkRadioButton(bonif_frame, text="Não",
                           variable=self.bonif_final_var, value="nao",
                           text_color=self.cor_texto).pack(side="left")

        botoes = ctk.CTkFrame(left, fg_color=self.cor_fundo)
        botoes.pack(fill="x", pady=(2, 8))

        self.btn_finalizar = ctk.CTkButton(
            botoes,
            text="Finalizar Corte Completo",
            width=180,
            command=self.finalizar_completo,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            state="disabled",
        )
        self.btn_finalizar.pack(side="left", padx=4)

        self.btn_baixa_parcial = ctk.CTkButton(
            botoes,
            text="Salvar Baixa Parcial",
            width=150,
            command=self.salvar_baixa_parcial,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            state="disabled",
        )
        self.btn_baixa_parcial.pack(side="left", padx=4)

        ctk.CTkButton(botoes, text="Limpar", width=120,
                      command=self.limpar_campos,
                      fg_color=self.cor_secundaria,
                      hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)

        ctk.CTkButton(botoes, text="Imprimir Relatório", width=160,
                      command=self.abrir_relatorio,
                      fg_color=self.cor_primaria,
                      hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)

        # Observações
        right = ctk.CTkFrame(mid, fg_color=self.cor_fundo)
        right.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(right, text="Observações de Finalização:",
                     font=("Arial", 12, "bold"),
                     text_color=self.cor_texto).pack(anchor="w", padx=6, pady=(6, 2))

        self.obs_finalizacao_txt = ctk.CTkTextbox(right, height=140,
                                                  fg_color=self.cor_secundaria,
                                                  border_color=self.cor_borda,
                                                  text_color=self.cor_texto_entry)
        self.obs_finalizacao_txt.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    # ----------------------------- Loaders -----------------------------
    def toggle_visualizacao_finalizados(self):
        self.mostrar_finalizados = self.cb_mostrar_finalizados.get()
        self.carregar_retornos_pendentes()

    def _set_search_path(self, cur, schema):
        try:
            cur.execute(f"SET LOCAL search_path = {schema};")
        except Exception:
            pass

    def _cols(self, cur, schema, table_name):
        cur.execute("""
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = %s
               AND table_name   = %s
        """, (schema, table_name))
        return {r[0] for r in cur.fetchall()}

    def _col_type(self, cur, schema, table_name, column_name):
        """Retorna (data_type, udt_name) de uma coluna (PostgreSQL), ou (None, None) se não existir."""
        cur.execute(
            """
            SELECT data_type, udt_name
              FROM information_schema.columns
             WHERE table_schema = %s
               AND table_name   = %s
               AND column_name  = %s
            """,
            (schema, table_name, column_name),
        )
        r = cur.fetchone()
        if not r:
            return None, None
        return r[0], r[1]

    def carregar_retornos_pendentes(self):
        """
        Mostra APENAS cortes em conferência para finalizar.
        (Aceita "Em Conferencia" e "Em Conferência")

        Se "Mostrar Finalizados" estiver marcado, também mostra "Finalizado".
        """
        try:
            termo = (self.busca_entry.get() or "").strip()

            # limpa tabela (NOME CERTO)
            self.retornos_tree.delete(*self.retornos_tree.get_children())

            # mapa retorno -> envio
            self.mapa_retorno_envio = {}

            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()
            self._set_search_path(cur, schema)

            # detecta colunas reais (pra não quebrar)
            cols_env = self._cols(cur, schema, "envios_cortes")
            status_col = "status_envio" if "status_envio" in cols_env else ("status" if "status" in cols_env else None)
            total_col = "total_pecas" if "total_pecas" in cols_env else (
                "quantidade_total" if "quantidade_total" in cols_env else None)

            # prestador: prioriza cadastro_faccoes se existir prestador_id
            has_prestador_id = "prestador_id" in cols_env
            prestador_expr = "COALESCE(f.nome,'')"
            if not has_prestador_id:
                # fallback por texto, se existir
                cand = []
                if "costureira" in cols_env: cand.append("e.costureira")
                if "faccao" in cols_env: cand.append("e.faccao")
                prestador_expr = "COALESCE(" + (", ".join(cand) + ", ''" if cand else "''") + ")"

            if not status_col:
                messagebox.showerror("Erro",
                                     "A tabela envios_cortes não possui coluna de status (status_envio/status).")
                conn.close()
                return

            status_expr = f"COALESCE(e.{status_col}, '')"
            qtd_expr = f"COALESCE(e.{total_col}, 0)" if total_col else "0"

            sql = f"""
                SELECT
                    r.id                                   AS retorno_id,
                    r.envio_id                             AS envio_id,
                    COALESCE(e.ordem_corte, c.numero_ordem, c.ordem_corte, '')       AS ordem_corte,
                    COALESCE(e.codigo_corte, c.codigo, '')                           AS codigo_corte,
                    COALESCE(e.descricao_corte, c.descricao_corte, c.descricao, '')  AS descricao_corte,
                    {prestador_expr}                       AS prestador,
                    r.data_chegada                         AS data_chegada,
                    {status_expr}                          AS status_envio,
                    {qtd_expr}                             AS qtd_total
                FROM {schema}.controle_retorno_cortes r
                JOIN {schema}.envios_cortes e ON e.id = r.envio_id
                {"LEFT JOIN " + schema + ".cadastro_faccoes f ON f.id = e.prestador_id" if has_prestador_id else ""}
                LEFT JOIN {schema}.cadastro_de_corte c ON c.id = e.corte_id
            """

            where = []
            params = []

            mostrar_finalizados = bool(self.cb_mostrar_finalizados.get())

            # ✅ filtro correto
            if mostrar_finalizados:
                where.append(
                    f"({status_expr} ILIKE 'em conferen%%' OR {status_expr} ILIKE 'em conferên%%' OR {status_expr} = 'Finalizado')")
            else:
                where.append(f"({status_expr} ILIKE 'em conferen%%' OR {status_expr} ILIKE 'em conferên%%')")

            if termo:
                like = f"%{termo}%"
                where.append("""
                    (
                        COALESCE(e.ordem_corte,'')     ILIKE %s OR
                        COALESCE(e.codigo_corte,'')    ILIKE %s OR
                        COALESCE(e.descricao_corte,'') ILIKE %s OR
                        COALESCE(c.codigo,'')          ILIKE %s OR
                        COALESCE(c.descricao,'')       ILIKE %s
                    )
                """)
                params.extend([like, like, like, like, like])

            if where:
                sql += " WHERE " + " AND ".join(where)

            sql += " ORDER BY r.data_chegada DESC, r.id DESC"

            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            conn.close()

            for i, row in enumerate(rows):
                (retorno_id, envio_id, ordem, codigo, descricao, prestador, data_chegada, status_envio, qtd_total) = row

                self.mapa_retorno_envio[int(retorno_id)] = int(envio_id)

                # status tolerante
                st = (status_envio or "").strip()
                st_norm = st.lower().replace("ê", "e").replace("í", "i")

                tag_status = ()
                if st_norm.startswith("em conferencia"):
                    tag_status = ("status_conferencia",)
                elif st == "Finalizado":
                    tag_status = ("status_finalizado",)

                row_tag = "evenrow" if i % 2 == 0 else "oddrow"
                tags = tag_status + (row_tag,) if tag_status else (row_tag,)

                self.retornos_tree.insert(
                    "",
                    "end",
                    values=(
                        retorno_id,
                        ordem,
                        codigo,
                        descricao,
                        prestador,
                        data_chegada.strftime("%d/%m/%Y") if data_chegada else "",
                        status_envio,
                        qtd_total,
                    ),
                    tags=tags
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erro", f"Falha ao carregar retornos: {e}")

    # ... (o restante dos métodos permanecem EXATAMENTE iguais, apenas o visual foi modificado)
    # Todos os métodos de lógica, banco de dados, cálculos, etc. permanecem inalterados

    def on_retorno_selecionado(self, _event=None):
        sel = self.retornos_tree.selection()
        if not sel: return
        v = self.retornos_tree.item(sel[0], "values")

        self.retorno_selecionado = {
            "id": v[0], "ordem": v[1], "codigo": v[2], "descricao": v[3],
            "prestador": v[4], "data_entrada": v[5], "status": v[6]
        }

        if self.retorno_selecionado["status"] == "Finalizado":
            messagebox.showinfo("Aviso", "Corte já finalizado.")
            self.limpar_campos()
            return

        self._tipo_servico = self._buscar_servico(self.retorno_selecionado["id"]) or ""
        self._prestador_nome = self.retorno_selecionado["prestador"] or ""

        self._preencher_header_retorno()
        self._carregar_detalhes_retorno()

    def _buscar_servico(self, retorno_id):
        """
        Retorna o tipo de serviço (Facção, Bordado, etc.)
        do envio vinculado a este RETORNO.
        """
        try:
            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()
            self._set_search_path(cur, schema)

            cur.execute(f"""
                SELECT COALESCE(e.tipo_servico, '')
                  FROM {schema}.controle_retorno_cortes r
                  JOIN {schema}.envios_cortes e
                    ON e.id = r.envio_id
                 WHERE r.id = %s
                 LIMIT 1
            """, (retorno_id,))
            row = cur.fetchone()
            conn.close()

            servico = row[0] if row else ""
            print(f"[DEBUG] _buscar_servico retorno_id={retorno_id} -> '{servico}'")
            return servico

        except Exception as exc:
            print(f"[DEBUG] _buscar_servico ERRO: {exc}")
            return ""

    def _preencher_header_retorno(self):
        self.prestador_entry.configure(state="normal")
        self.prestador_entry.delete(0, tk.END)
        self.prestador_entry.insert(0, self._prestador_nome or "")
        self.prestador_entry.configure(state="disabled")

        self.servico_entry.configure(state="normal")
        self.servico_entry.delete(0, tk.END)
        self.servico_entry.insert(0, self._tipo_servico or "")
        self.servico_entry.configure(state="disabled")

        self.entrada_id_entry.configure(state="normal")
        self.entrada_id_entry.delete(0, tk.END)
        self.entrada_id_entry.insert(0, self.retorno_selecionado["id"])
        self.entrada_id_entry.configure(state="disabled")

        self.codigo_entry.configure(state="normal")
        self.codigo_entry.delete(0, tk.END)
        self.codigo_entry.insert(0, self.retorno_selecionado["codigo"])
        self.codigo_entry.configure(state="disabled")

        self.descricao_entry.configure(state="normal")
        self.descricao_entry.delete(0, tk.END)
        self.descricao_entry.insert(0, self.retorno_selecionado["descricao"])
        self.descricao_entry.configure(state="disabled")

        self.ordem_entry.configure(state="normal")
        self.ordem_entry.delete(0, tk.END)
        self.ordem_entry.insert(0, self.retorno_selecionado["ordem"])
        self.ordem_entry.configure(state="disabled")

        self.data_entrada_entry.configure(state="normal")
        self.data_entrada_entry.delete(0, tk.END)
        self.data_entrada_entry.insert(0, self.retorno_selecionado["data_entrada"])
        self.data_entrada_entry.configure(state="disabled")

    def _carregar_detalhes_retorno(self):
        """
        Carrega na grade os dados do ENVIO + RETORNO para o retorno selecionado.

        Usa:
          - self.mapa_retorno_envio[retorno_id] -> envio_id
          - envio_detalhes_tamanho             -> quantidade enviada, pilotos, valor_peca
          - retorno_detalhes_tamanho           -> entregue, copias, defeitos, faltantes
        """
        if not getattr(self, "retorno_selecionado", None):
            messagebox.showwarning("Aviso", "Selecione um retorno na lista.")
            return

        try:
            retorno_id = int(self.retorno_selecionado["id"])
        except Exception:
            messagebox.showerror("Erro", "ID de retorno inválido.")
            return

        print(f"\n================ _carregar_detalhes_retorno() retorno_id={retorno_id} ================")

        # pega o envio_id a partir do mapa preenchido em carregar_retornos_pendentes
        envio_id = None
        if hasattr(self, "mapa_retorno_envio"):
            envio_id = self.mapa_retorno_envio.get(retorno_id)

        if not envio_id:
            messagebox.showerror("Erro", "Não foi possível localizar o envio desta entrada.")
            print(f"[DEBUG] mapa_retorno_envio: {getattr(self, 'mapa_retorno_envio', None)}")
            return

        print(f"[DEBUG] envio_id vinculado = {envio_id}")

        # 0) LIMPA A GRADE
        for t in self.tamanhos:
            self.entregues_vars[t].set(0)
            self.copias_vars[t].set(0)
            self.defeitos_vars[t].set(0)
            self.faltantes_vars[t].set(0)

            self.enviado_por_tam[t] = 0
            self.valor_por_tam[t] = 0.0
            self.pilotos_por_tam[t] = 0

            self.grade_widgets[t]["enviado"].configure(text="0")
            self.grade_widgets[t]["valor"].configure(text=fmt_moeda(0))
            self.grade_widgets[t]["regulares"].configure(text="0")
            self.grade_widgets[t]["subtotal"].configure(text=fmt_moeda(0))

        try:
            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()
            self._set_search_path(cur, schema)

            # 1) DETALHE DO ENVIO (envio_detalhes_tamanho)
            # Primeiro tenta carregar via tabela de detalhes. Caso não haja registro,
            # recorre à tabela envios_cortes diretamente.
            cur.execute(
                f"""
                SELECT tamanho,
                       COALESCE(quantidade,0)         AS quantidade,
                       COALESCE(quantidade_pilotos,0) AS pilotos,
                       COALESCE(valor_peca,0)         AS valor_peca
                  FROM {schema}.envio_detalhes_tamanho
                 WHERE envio_id = %s
                """,
                (envio_id,),
            )
            envio_rows = cur.fetchall()
            print(f"[DEBUG] Linhas em envio_detalhes_tamanho: {len(envio_rows)}")

            if envio_rows:
                # Popula dados com base na tabela de detalhes
                for tamanho, quantidade, pilotos, valor_peca in envio_rows:
                    if tamanho not in self.tamanhos:
                        continue

                    qtd_env = safe_int(quantidade)
                    qtd_pil = safe_int(pilotos)
                    val_uni = float(valor_peca or 0)

                    total_enviado = qtd_env + qtd_pil

                    self.enviado_por_tam[tamanho] = total_enviado
                    self.pilotos_por_tam[tamanho] = qtd_pil
                    self.valor_por_tam[tamanho] = val_uni

                    self.grade_widgets[tamanho]["enviado"].configure(text=str(total_enviado))
                    self.grade_widgets[tamanho]["valor"].configure(text=fmt_moeda(val_uni))

                    print(
                        f"[DEBUG] ENVIO tam={tamanho} | qtd={qtd_env} | pilotos={qtd_pil} "
                        f"| total_enviado={total_enviado} | valor={val_uni}"
                    )
            else:
                # Não há registro em envio_detalhes_tamanho; calcular a partir de envios_cortes
                print("[DEBUG] Nenhum detalhe em envio_detalhes_tamanho. Consultando envios_cortes...")
                cur.execute(
                    f"""
                    SELECT
                        qtd_pp, qtd_p, qtd_m, qtd_g, qtd_gg, qtd_g1, qtd_g2, qtd_g3,
                        piloto_pp, piloto_p, piloto_m, piloto_g, piloto_gg, piloto_g1, piloto_g2, piloto_g3,
                        valor_pp, valor_p, valor_m, valor_g, valor_gg, valor_g1, valor_g2, valor_g3
                    FROM {schema}.envios_cortes
                    WHERE id = %s
                    """,
                    (envio_id,),
                )
                row_envio = cur.fetchone()
                if row_envio:
                    # Mapear índices para tamanhos
                    qtd_indices = {t: i for i, t in enumerate(["PP","P","M","G","GG","G1","G2","G3"])}
                    pil_indices = {t: i+8 for i, t in enumerate(["PP","P","M","G","GG","G1","G2","G3"])}
                    val_indices = {t: i+16 for i, t in enumerate(["PP","P","M","G","GG","G1","G2","G3"])}
                    for tam in self.tamanhos:
                        qtd_env = safe_int(row_envio[qtd_indices[tam]])
                        qtd_pil = safe_int(row_envio[pil_indices[tam]])
                        val_uni = float(row_envio[val_indices[tam]] or 0)
                        total_enviado = qtd_env + qtd_pil
                        self.enviado_por_tam[tam] = total_enviado
                        self.pilotos_por_tam[tam] = qtd_pil
                        self.valor_por_tam[tam] = val_uni
                        self.grade_widgets[tam]["enviado"].configure(text=str(total_enviado))
                        self.grade_widgets[tam]["valor"].configure(text=fmt_moeda(val_uni))
                        print(
                            f"[DEBUG] ENVIO tam={tam} | qtd={qtd_env} | pilotos={qtd_pil} | total_enviado={total_enviado} | valor={val_uni}"
                        )

            # 2) DETALHE DO RETORNO (retorno_detalhes_tamanho)
            cur.execute(
                f"""
                SELECT tamanho,
                       COALESCE(entregue,0)  AS entregue,
                       COALESCE(copias,0)    AS copias,
                       COALESCE(defeitos,0)  AS defeitos,
                       COALESCE(faltantes,0) AS faltantes
                  FROM {schema}.retorno_detalhes_tamanho
                 WHERE envio_id = %s
                """,
                (envio_id,),
            )
            retorno_rows = cur.fetchall()
            print(f"[DEBUG] Linhas em retorno_detalhes_tamanho: {len(retorno_rows)}")

            for tamanho, entregue, copias, defeitos, faltantes in retorno_rows:
                if tamanho not in self.tamanhos:
                    continue

                self.entregues_vars[tamanho].set(entregue or 0)
                self.copias_vars[tamanho].set(copias or 0)
                self.defeitos_vars[tamanho].set(defeitos or 0)
                self.faltantes_vars[tamanho].set(faltantes or 0)

                print(
                    f"[DEBUG] RETORNO tam={tamanho} | ent={entregue} | "
                    f"copias={copias} | defeitos={defeitos} | faltantes={faltantes}"
                )

            conn.close()

            # 3) Recalcula totais/subtotais
            self._recalcular_totais()

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erro", f"Falha ao carregar detalhes do retorno:\n{e}")

    def _recalcular_totais(self, _event=None):
        total_entregue = 0
        total_copias = 0
        total_defeito = 0
        total_faltante = 0
        total_regulares = 0
        valor_total = 0.0
        completo = True
        tem_envio = False
        tem_informado = False

        for t in self.tamanhos:
            enviado = safe_int(self.grade_widgets[t]["enviado"].cget("text"))
            entregue = self._normalizar_valor(self.entregues_vars[t], enviado)
            copias = self._normalizar_valor(self.copias_vars[t], enviado)
            defeito = self._normalizar_valor(self.defeitos_vars[t], enviado)
            faltante = self._normalizar_valor(self.faltantes_vars[t], enviado)

            if enviado > 0:
                tem_envio = True

            # Normaliza valores para não exceder o enviado
            if defeito < 0:
                defeito = 0
                self.defeitos_vars[t].set(0)
            if faltante < 0:
                faltante = 0
                self.faltantes_vars[t].set(0)
            if defeito > enviado:
                defeito = enviado
                self.defeitos_vars[t].set(enviado)
            if faltante > enviado:
                faltante = enviado
                self.faltantes_vars[t].set(enviado)

            if entregue < 0:
                entregue = 0
                self.entregues_vars[t].set(0)

            if entregue + defeito > enviado:
                entregue = max(enviado - defeito, 0)
                self.entregues_vars[t].set(entregue)

            # Faltante sempre recalculado com base em Enviado, Entregue e Defeito
            faltante = max(enviado - entregue - defeito, 0)
            self.faltantes_vars[t].set(faltante)
            if entregue + defeito + faltante > enviado:
                faltante = max(enviado - entregue - defeito, 0)
                self.faltantes_vars[t].set(faltante)
                if entregue + defeito > enviado:
                    entregue = max(enviado - defeito, 0)
                    self.entregues_vars[t].set(entregue)
                    faltante = 0
                    self.faltantes_vars[t].set(0)

            # Cópias não excedem entregue
            if copias > entregue:
                self.copias_vars[t].set(min(copias, entregue))
                copias = safe_int(self.copias_vars[t].get())

            reg = max(0, entregue - copias - defeito)
            subtotal = reg * float(self.valor_por_tam[t])

            self.grade_widgets[t]["regulares"].configure(text=str(reg))
            self.grade_widgets[t]["subtotal"].configure(text=fmt_moeda(subtotal))

            informado = entregue + defeito + faltante
            if informado > 0:
                tem_informado = True
            if informado != enviado:
                completo = False

            total_entregue += entregue
            total_copias += copias
            total_defeito += defeito
            total_faltante += faltante
            total_regulares += reg
            valor_total += subtotal

        self.lbl_total_entregue.configure(text=str(total_entregue))
        self.lbl_total_copias.configure(text=str(total_copias))
        self.lbl_total_defeito.configure(text=str(total_defeito))

        # Se houver defeito, força "Não" na bonificação
        try:
            if total_defeito > 0:
                self.bonif_final_var.set("nao")
        except Exception:
            pass

        self.lbl_total_faltante.configure(text=str(total_faltante))
        self.lbl_total_regulares.configure(text=str(total_regulares))
        self.lbl_valor_total.configure(text=fmt_moeda(valor_total))

        try:
            if tem_envio and completo:
                self.btn_finalizar.configure(state="normal")
                self.btn_baixa_parcial.configure(state="disabled")
            elif tem_informado:
                self.btn_finalizar.configure(state="disabled")
                self.btn_baixa_parcial.configure(state="normal")
            else:
                self.btn_finalizar.configure(state="disabled")
                self.btn_baixa_parcial.configure(state="disabled")
        except Exception:
            pass

    # ----------------------------- Relatório -----------------------------
    def abrir_relatorio(self):
        if not self.retorno_selecionado:
            messagebox.showwarning("Aviso", "Selecione um retorno primeiro!")
            return

        dados = self._coletar_dados_relatorio()
        html = self._gerar_html_relatorio(dados)

        win = ctk.CTkToplevel(self)
        win.title("Relatório de Finalização")
        win.geometry("900x650")

        header = ctk.CTkFrame(win)
        header.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(header, text="RELATÓRIO DE FINALIZAÇÃO", font=("Arial", 18, "bold")).pack(side="left")

        prev = ctk.CTkTextbox(win, font=("Consolas", 12))
        prev.pack(fill="both", expand=True, padx=10, pady=6)

        preview_txt = []
        preview_txt.append(f"Prestador : {dados['prestador']}")
        preview_txt.append(f"Serviço   : {dados['servico']}")
        preview_txt.append(f"Ordem     : {dados['ordem']}  |  Código: {dados['codigo']}")
        preview_txt.append(f"Descrição : {dados['descricao']}")
        preview_txt.append(f"Entrada   : {dados['data_entrada']}  |  Emissão: {dados['emissao']}")
        preview_txt.append("-" * 90)
        preview_txt.append(
            f"{'Tam.':<5}{'Enviado':>9}{'Entregue':>11}{'Cópias':>8}{'Defeito':>9}{'Faltante':>10}{'Regulares':>11}{'Vlr/Pç':>10}{'Subtotal':>12}")
        preview_txt.append("-" * 90)
        for r in dados["linhas"]:
            preview_txt.append(
                f"{r['tam']:<5}{r['enviado']:>9}{r['entregue']:>11}{r['copias']:>8}{r['defeito']:>9}{r['faltante']:>10}{r['regulares']:>11}{r['valor_peca']:>10}{r['subtotal']:>12}")
        preview_txt.append("-" * 90)
        tt = dados["totais"]
        preview_txt.append(
            f"{'Totais:':<5}{'':>9}{tt['entregue']:>11}{tt['copias']:>8}{tt['defeito']:>9}{tt['faltante']:>10}{tt['regulares']:>11}{'':>10}{tt['valor_total']:>12}"
        )
        if dados["obs"]:
            preview_txt.append("\nObservações:\n" + dados["obs"])

        prev.insert("1.0", "\n".join(preview_txt))
        prev.configure(state="disabled")

        barra = ctk.CTkFrame(win, fg_color="transparent")
        barra.pack(fill="x", padx=10, pady=(6, 10))

        def _imprimir():
            self._imprimir_html(html)

        def _abrir_nav():
            try:
                path = self._salvar_html_temporario(html, auto_open=True, imprimir=False)
                if path:
                    messagebox.showinfo("Prévia",
                                        "Relatório aberto no navegador.\nUse o comando Imprimir (Ctrl+P) para PDF.")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao abrir no navegador: {e}")

        def _salvar_html():
            try:
                file = filedialog.asksaveasfilename(defaultextension=".html",
                                                    filetypes=[("HTML", "*.html")],
                                                    title="Salvar Relatório (HTML)")
                if not file:
                    return
                with open(file, "w", encoding="utf-8") as f:
                    f.write(html)
                messagebox.showinfo("Sucesso", "Relatório salvo!")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao salvar: {e}")

        ctk.CTkButton(barra, text="Imprimir", width=120, command=_imprimir).pack(side="left", padx=4)
        ctk.CTkButton(barra, text="Abrir no Navegador", width=160, command=_abrir_nav).pack(side="left", padx=4)
        ctk.CTkButton(barra, text="Salvar HTML", width=140, command=_salvar_html).pack(side="left", padx=4)

    def _coletar_dados_relatorio(self):
        d = {
            "prestador": self._prestador_nome or "",
            "servico": self._tipo_servico or "",
            "ordem": (self.ordem_entry.get() or "").strip(),
            "codigo": (self.codigo_entry.get() or "").strip(),
            "descricao": (self.descricao_entry.get() or "").strip(),
            "data_entrada": (self.data_entrada_entry.get() or "").strip(),
            "emissao": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "linhas": [],
            "totais": {},
            "obs": (self.obs_finalizacao_txt.get("1.0", tk.END) or "").strip(),
            "logo": LOGO_PATH if os.path.exists(LOGO_PATH) else None
        }

        total_entregue = total_copias = total_defeito = total_faltante = total_regulares = 0
        total_valor = 0.0

        for t in self.tamanhos:
            enviado = safe_int(self.enviado_por_tam.get(t, 0))
            entregue = safe_int(self.entregues_vars[t].get())
            copias = safe_int(self.copias_vars[t].get())
            defeito = safe_int(self.defeitos_vars[t].get())
            faltante = safe_int(self.faltantes_vars[t].get())

            reg = max(0, entregue - copias - defeito)
            valor_peca = float(self.valor_por_tam.get(t, 0.0))
            subtotal = reg * valor_peca

            total_entregue += entregue
            total_copias += copias
            total_defeito += defeito
            total_faltante += faltante
            total_regulares += reg
            total_valor += subtotal

            d["linhas"].append({
                "tam": t,
                "enviado": enviado,
                "entregue": entregue,
                "copias": copias,
                "defeito": defeito,
                "faltante": faltante,
                "regulares": reg,
                "valor_peca": f"{valor_peca:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "subtotal": f"{subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            })

        d["totais"] = {
            "entregue": total_entregue,
            "copias": total_copias,
            "defeito": total_defeito,
            "faltante": total_faltante,
            "regulares": total_regulares,
            "valor_total": f"{total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        }
        return d

    def _gerar_html_relatorio(self, d):
        # Ajuste: evitar escape de barra invertida em f-string. Calcula caminho do logo fora do f-string
        logo_path = None
        if d.get("logo"):
            try:
                logo_path = d["logo"].replace("\\", "/")
            except Exception:
                logo_path = d["logo"]
        logo_html = f'<img src="file:///{logo_path}" style="height:70px;">' if logo_path else ""
        linhas_html = []
        for r in d["linhas"]:
            linhas_html.append(f"""
                <tr>
                  <td>{r['tam']}</td>
                  <td style="text-align:right">{r['enviado']}</td>
                  <td style="text-align:right">{r['entregue']}</td>
                  <td style="text-align:right">{r['copias']}</td>
                  <td style="text-align:right">{r['defeito']}</td>
                  <td style="text-align:right">{r['faltante']}</td>
                  <td style="text-align:right">{r['regulares']}</td>
                  <td style="text-align:right">{r['valor_peca']}</td>
                  <td style="text-align:right">{r['subtotal']}</td>
                </tr>
            """)
        obs_html = f"<h3>Observações</h3><pre>{(d['obs'] or '').replace('<', '&lt;').replace('>', '&gt;')}</pre>" if d[
            "obs"] else ""

        return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Relatório de Finalização</title>
<style>
  *{{box-sizing:border-box}} body{{font-family:Arial, Helvetica, sans-serif; margin:20px}}
  .topo{{display:flex; align-items:center; justify-content:space-between; margin-bottom:10px}}
  h1{{font-size:20px; margin:0}}
  .grid-info{{margin:10px 0; font-size:14px}}
  table{{width:100%; border-collapse:collapse; font-size:13px}}
  th, td{{border:1px solid #444; padding:6px}}
  th{{background:#f1f1f1; text-align:center}}
  .totais{{text-align:right; font-weight:bold; margin-top:10px; font-size:14px}}
  @media print{{ .no-print{{display:none}} }}
</style>
</head>
<body>
  <div class="topo">
    <div>{logo_html}</div>
    <div style="text-align:right">
      <h1>RELATÓRIO DE FINALIZAÇÃO</h1>
      <div>Emissão: {d['emissao']}</div>
    </div>
  </div>

  <div class="grid-info">
    <div><b>Prestador:</b> {d['prestador']}</div>
    <div><b>Serviço:</b> {d['servico']}</div>
    <div><b>Ordem:</b> {d['ordem']} &nbsp;&nbsp; <b>Código:</b> {d['codigo']}</div>
    <div><b>Descrição:</b> {d['descricao']}</div>
    <div><b>Data de Entrada:</b> {d['data_entrada']}</div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Tam.</th><th>Enviado</th><th>Entregue</th><th>Cópias</th><th>Defeito</th><th>Faltante</th><th>Regulares</th><th>Valor/Peça</th><th>Subtotal</th>
      </tr>
    </thead>
    <tbody>
      {''.join(linhas_html)}
    </tbody>
  </table>

  <div class="totais">
    Totais — Entregue: {d['totais']['entregue']} |
    Cópias: {d['totais']['copias']} |
    Defeito: {d['totais']['defeito']} |
    Faltante: {d['totais']['faltante']} |
    Regulares: {d['totais']['regulares']} |
    Valor Total: R$ {d['totais']['valor_total']}
  </div>

  {obs_html}

  <div class="no-print" style="margin-top:12px; font-size:12px; color:#666">Dica: Ctrl+P para imprimir ou salvar como PDF.</div>
</body>
</html>"""

    def _imprimir_html(self, html):
        try:
            self._salvar_html_temporario(html, auto_open=False, imprimir=True)
            messagebox.showinfo("Impressão", "Relatório enviado para impressão (ou aberto para imprimir).")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao imprimir: {e}")

    def _salvar_html_temporario(self, html, auto_open=False, imprimir=False):
        fd, path = tempfile.mkstemp(prefix="relatorio_finalizacao_", suffix=".html")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        if auto_open:
            try:
                # Evita backslashes em f-string computando caminho seguro
                safe_path = path.replace("\\", "/")
                webbrowser.open(f"file:///{safe_path}")
            except Exception:
                pass
        if imprimir:
            try:
                os.startfile(path, "print")  # Windows
            except Exception:
                # Em sistemas que não suportam os.startfile, abre no navegador
                try:
                    safe_path = path.replace("\\", "/")
                    webbrowser.open(f"file:///{safe_path}")
                except Exception:
                    pass
        return path

    # ----------------------------- Ações de Banco -----------------------------
    def finalizar_completo(self):
        """Finaliza o corte selecionado e deixa disponível para PAGAMENTO.

        Ajustes importantes:
        - Não usa mais `entrada_acabamento` (tabela antiga).
        - Usa `controle_retorno_cortes.envio_id` (via mapa retorno->envio).
        - Consolida `retorno_detalhes_tamanho` conforme os valores da tela.
        - Marca `envios_cortes.status_envio = 'Finalizado'`.
        - Registra/atualiza uma linha em `cortes_finalizados` para a tela de PAGAMENTO_SERVICOS
          encontrar o corte em "Cortes a Pagar".
        """
        if not getattr(self, "retorno_selecionado", None):
            messagebox.showwarning("Aviso", "Selecione um retorno na lista.")
            return

        try:
            retorno_id = int(self.retorno_selecionado["id"])
        except Exception:
            messagebox.showerror("Erro", "ID de retorno inválido.")
            return

        if not messagebox.askyesno("Confirmar", "Deseja realmente finalizar este corte?"):
            return

        # pega envio_id via mapa (preenchido em carregar_retornos_pendentes)
        envio_id = None
        if hasattr(self, "mapa_retorno_envio"):
            envio_id = self.mapa_retorno_envio.get(retorno_id)

        if not envio_id:
            messagebox.showerror("Erro", "Não foi possível localizar o envio desta entrada.")
            return

        try:
            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()
            self._set_search_path(cur, schema)

            # (1) Consolida detalhes por tamanho conforme a tela
            totals = {
                "entregue": 0,
                "copias": 0,
                "defeitos": 0,
                "faltantes": 0,
                "regulares": 0,
                "valor_total": 0.0,
            }
            reg_por_tam = {}

            cur.execute(f"DELETE FROM {schema}.retorno_detalhes_tamanho WHERE envio_id = %s", (envio_id,))

            for t in self.tamanhos:
                entregue = safe_int(self.entregues_vars[t].get())
                copias = safe_int(self.copias_vars[t].get())
                defeitos = safe_int(self.defeitos_vars[t].get())
                faltantes = safe_int(self.faltantes_vars[t].get())

                regulares = max(0, entregue - defeitos - faltantes)
                reg_por_tam[t] = int(regulares)

                valor_peca = float(self.valor_por_tam.get(t, 0.0) or 0.0)
                subtotal = regulares * valor_peca

                if any([entregue, copias, defeitos, faltantes, regulares]) or subtotal > 0:
                    cur.execute(f"""
                        INSERT INTO {schema}.retorno_detalhes_tamanho
                            (envio_id, tamanho, entregue, copias, defeitos, faltantes, regulares, subtotal)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (envio_id, t, entregue, copias, defeitos, faltantes, regulares, subtotal))

                totals["entregue"] += entregue
                totals["copias"] += copias
                totals["defeitos"] += defeitos
                totals["faltantes"] += faltantes
                totals["regulares"] += regulares
                totals["valor_total"] += float(subtotal or 0.0)

            # (2) Atualiza o cabeçalho do retorno (controle_retorno_cortes)
            obs_finalizacao = (self.obs_finalizacao_txt.get("1.0", tk.END) or "").strip()

            cols_ret = self._cols(cur, schema, "controle_retorno_cortes")
            if "observacoes_finalizacao" in cols_ret:
                cur.execute(f"""
                    UPDATE {schema}.controle_retorno_cortes
                       SET observacoes_finalizacao = %s,
                           total_entregue = %s,
                           total_copias = %s,
                           total_defeitos = %s,
                           total_faltantes = %s,
                           total_regulares = %s,
                           valor_total = %s
                     WHERE id = %s
                """, (obs_finalizacao, totals["entregue"], totals["copias"], totals["defeitos"],
                        totals["faltantes"], totals["regulares"], totals["valor_total"], retorno_id))
            else:
                if "observacoes_gerais" in cols_ret:
                    cur.execute(f"""
                        UPDATE {schema}.controle_retorno_cortes
                           SET observacoes_gerais = %s,
                               total_entregue = %s,
                               total_copias = %s,
                               total_defeitos = %s,
                               total_faltantes = %s,
                               total_regulares = %s,
                               valor_total = %s
                         WHERE id = %s
                    """, (obs_finalizacao, totals["entregue"], totals["copias"], totals["defeitos"],
                            totals["faltantes"], totals["regulares"], totals["valor_total"], retorno_id))
                else:
                    cur.execute(f"""
                        UPDATE {schema}.controle_retorno_cortes
                           SET total_entregue = %s,
                               total_copias = %s,
                               total_defeitos = %s,
                               total_faltantes = %s,
                               total_regulares = %s,
                               valor_total = %s
                         WHERE id = %s
                    """, (totals["entregue"], totals["copias"], totals["defeitos"],
                            totals["faltantes"], totals["regulares"], totals["valor_total"], retorno_id))

            # (3) Marca o envio como FINALIZADO
            cols_envio = self._cols(cur, schema, "envios_cortes")
            if "status_envio" in cols_envio:
                cur.execute(f"""
                    UPDATE {schema}.envios_cortes
                       SET status_envio = 'Finalizado'
                     WHERE id = %s
                """, (envio_id,))
            elif "status" in cols_envio:
                cur.execute(f"""
                    UPDATE {schema}.envios_cortes
                       SET status = 'Finalizado'
                     WHERE id = %s
                """, (envio_id,))

            # (4) Registra/atualiza em cortes_finalizados para o PAGAMENTO_SERVICOS listar
            # dados base (puxando do envio)
            cur.execute(f"""
                SELECT
                    COALESCE(e.codigo_corte, ''),
                    COALESCE(e.descricao_corte, ''),
                    COALESCE(e.data_envio, NULL),
                    COALESCE(r.data_chegada, NULL),
                    COALESCE(f.nome, '')
                FROM {schema}.envios_cortes e
                JOIN {schema}.controle_retorno_cortes r ON r.id = %s
                LEFT JOIN {schema}.cadastro_faccoes f ON f.id = e.prestador_id
                WHERE e.id = %s
                LIMIT 1
            """, (retorno_id, envio_id))
            row = cur.fetchone() or ("", "", None, None, "")
            codigo_corte, desc_corte, data_envio, data_chegada, prestador_nome = row

            # tenta ler tipo de serviço do envio (se existir)
            tipo_servico = ""
            try:
                if "tipo_servico" in cols_envio:
                    cur.execute(f"SELECT COALESCE(tipo_servico,'') FROM {schema}.envios_cortes WHERE id=%s", (envio_id,))
                    r2 = cur.fetchone()
                    tipo_servico = (r2[0] if r2 else "") or ""
            except Exception:
                tipo_servico = ""

            # bonificação: guarda valor se o usuário marcou "sim" e tiver campo de valor na tela
            bonif_valor = 0.0
            try:
                bonif_aplicada = (self.bonif_final_var.get() == "sim")
            except Exception:
                bonif_aplicada = False
            if bonif_aplicada:
                try:
                    bonif_valor = float((self.valor_bonif_entry.get() or "0").replace(",", "."))
                except Exception:
                    bonif_valor = 0.0

            # monta payload adaptando às colunas existentes
            try:
                cols_cf = self._cols(cur, schema, "cortes_finalizados")
            except Exception:
                cols_cf = set()

            if cols_cf:
                # procura registro existente para este envio
                existing_id = None
                if "envio_id" in cols_cf:
                    cur.execute(f"""
                        SELECT id
                          FROM {schema}.cortes_finalizados
                         WHERE envio_id = %s
                      ORDER BY id DESC LIMIT 1
                    """, (envio_id,))
                    rr = cur.fetchone()
                    existing_id = rr[0] if rr else None
                else:
                    # fallback pelo código (menos ideal)
                    cur.execute(f"""
                        SELECT id
                          FROM {schema}.cortes_finalizados
                         WHERE codigo = %s
                      ORDER BY id DESC LIMIT 1
                    """, (codigo_corte,))
                    rr = cur.fetchone()
                    existing_id = rr[0] if rr else None

                # mapeia tamanhos -> sufixos da tabela (qtd_pp, qtd_p, ...)
                mapa_sufixo = {"PP": "pp", "P": "p", "M": "m", "G": "g", "GG": "gg", "G1": "g1", "G2": "g2", "G3": "g3"}

                data_payload = {}
                if "envio_id" in cols_cf: data_payload["envio_id"] = envio_id
                if "retorno_id" in cols_cf: data_payload["retorno_id"] = retorno_id
                if "tipo_servico" in cols_cf: data_payload["tipo_servico"] = tipo_servico
                if "codigo" in cols_cf: data_payload["codigo"] = codigo_corte
                if "descricao" in cols_cf: data_payload["descricao"] = desc_corte
                if "costureira" in cols_cf: data_payload["costureira"] = prestador_nome
                if "data_envio" in cols_cf: data_payload["data_envio"] = data_envio
                if "data_chegada" in cols_cf: data_payload["data_chegada"] = data_chegada
                if "valor_total" in cols_cf: data_payload["valor_total"] = totals["valor_total"]
                if "bonificacao" in cols_cf:
                    # Compatibilidade: alguns bancos têm bonificacao BOOLEAN (apenas flag),
                    # outros têm bonificacao NUMERIC (valor). Ajusta automaticamente.
                    dt, _udt = self._col_type(cur, schema, "cortes_finalizados", "bonificacao")
                    if dt == "boolean":
                        data_payload["bonificacao"] = bool(bonif_aplicada)
                        # se existir coluna para armazenar o valor, gravamos também
                        for cand in ("valor_bonificacao", "bonificacao_valor", "bonificacao_rs", "valor_bonificacao_rs"):
                            if cand in cols_cf:
                                data_payload[cand] = float(bonif_valor or 0.0)
                                break
                    else:
                        data_payload["bonificacao"] = float(bonif_valor or 0.0)


                for tam, suf in mapa_sufixo.items():
                    col = f"qtd_{suf}"
                    if col in cols_cf:
                        data_payload[col] = int(reg_por_tam.get(tam, 0))

                # por padrão, não marca pago aqui
                if existing_id:
                    sets = ", ".join([f"{k} = %s" for k in data_payload.keys()])
                    vals = list(data_payload.values())
                    vals.append(existing_id)
                    cur.execute(f"""
                        UPDATE {schema}.cortes_finalizados
                           SET {sets}
                         WHERE id = %s
                    """, tuple(vals))
                else:
                    # cria defaults de pago, se existir
                    if "pago" in cols_cf:
                        data_payload["pago"] = False
                    cols = ", ".join(data_payload.keys())
                    placeholders = ", ".join(["%s"] * len(data_payload))
                    cur.execute(f"""
                        INSERT INTO {schema}.cortes_finalizados ({cols})
                        VALUES ({placeholders})
                    """, tuple(data_payload.values()))

            conn.commit()
            conn.close()

            messagebox.showinfo("Sucesso", "Corte finalizado com sucesso.")
            self.limpar_campos()
            self.carregar_retornos_pendentes()

        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            messagebox.showerror("Erro", f"Falha ao finalizar corte: {e}")

    def salvar_baixa_parcial(self):
        """Salva a conferência atual (baixa parcial) SEM marcar como Finalizado.

        Ajuste importante:
        - Antes este método tentava localizar envio_id em `entrada_acabamento` (tabela antiga).
        - Agora ele usa o vínculo correto `controle_retorno_cortes.envio_id` (via mapa retorno->envio),
          e persiste os detalhes em `retorno_detalhes_tamanho` (consolidando os valores que estão na tela).
        """
        if not getattr(self, "retorno_selecionado", None):
            messagebox.showwarning("Aviso", "Selecione um retorno na lista.")
            return

        try:
            retorno_id = int(self.retorno_selecionado["id"])
        except Exception:
            messagebox.showerror("Erro", "ID de retorno inválido.")
            return

        # pega envio_id via mapa (preenchido em carregar_retornos_pendentes)
        envio_id = None
        if hasattr(self, "mapa_retorno_envio"):
            envio_id = self.mapa_retorno_envio.get(retorno_id)

        if not envio_id:
            messagebox.showerror("Erro", "Não foi possível localizar o envio desta entrada.")
            return

        try:
            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()
            self._set_search_path(cur, schema)

            # (1) Consolida detalhes por tamanho conforme a tela
            totals = {
                "entregue": 0,
                "copias": 0,
                "defeitos": 0,
                "faltantes": 0,
                "regulares": 0,
                "valor_total": 0.0,
            }

            # Importante: aqui fazemos consolidação (replace) para garantir consistência do pagamento.
            cur.execute(f"DELETE FROM {schema}.retorno_detalhes_tamanho WHERE envio_id = %s", (envio_id,))

            for t in self.tamanhos:
                entregue = safe_int(self.entregues_vars[t].get())
                copias = safe_int(self.copias_vars[t].get())
                defeitos = safe_int(self.defeitos_vars[t].get())
                faltantes = safe_int(self.faltantes_vars[t].get())

                regulares = max(0, entregue - defeitos - faltantes)
                valor_peca = float(self.valor_por_tam.get(t, 0.0) or 0.0)
                subtotal = regulares * valor_peca

                # grava somente linhas com algum dado
                if any([entregue, copias, defeitos, faltantes, regulares]) or subtotal > 0:
                    cur.execute(f"""
                        INSERT INTO {schema}.retorno_detalhes_tamanho
                            (envio_id, tamanho, entregue, copias, defeitos, faltantes, regulares, subtotal)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (envio_id, t, entregue, copias, defeitos, faltantes, regulares, subtotal))

                totals["entregue"] += entregue
                totals["copias"] += copias
                totals["defeitos"] += defeitos
                totals["faltantes"] += faltantes
                totals["regulares"] += regulares
                totals["valor_total"] += float(subtotal or 0.0)

            # (2) Atualiza o cabeçalho do retorno (controle_retorno_cortes)
            obs_finalizacao = (self.obs_finalizacao_txt.get("1.0", tk.END) or "").strip()

            cols_ret = self._cols(cur, schema, "controle_retorno_cortes")
            # tenta gravar em coluna dedicada, se existir; senão, reaproveita observacoes_gerais
            if "observacoes_finalizacao" in cols_ret:
                cur.execute(f"""
                    UPDATE {schema}.controle_retorno_cortes
                       SET observacoes_finalizacao = %s,
                           total_entregue = %s,
                           total_copias = %s,
                           total_defeitos = %s,
                           total_faltantes = %s,
                           total_regulares = %s,
                           valor_total = %s
                     WHERE id = %s
                """, (obs_finalizacao, totals["entregue"], totals["copias"], totals["defeitos"],
                        totals["faltantes"], totals["regulares"], totals["valor_total"], retorno_id))
            else:
                # fallback: mantém observações gerais
                if "observacoes_gerais" in cols_ret:
                    cur.execute(f"""
                        UPDATE {schema}.controle_retorno_cortes
                           SET observacoes_gerais = %s,
                               total_entregue = %s,
                               total_copias = %s,
                               total_defeitos = %s,
                               total_faltantes = %s,
                               total_regulares = %s,
                               valor_total = %s
                         WHERE id = %s
                    """, (obs_finalizacao, totals["entregue"], totals["copias"], totals["defeitos"],
                            totals["faltantes"], totals["regulares"], totals["valor_total"], retorno_id))
                else:
                    # se não houver coluna de observações, atualiza somente totais
                    cur.execute(f"""
                        UPDATE {schema}.controle_retorno_cortes
                           SET total_entregue = %s,
                               total_copias = %s,
                               total_defeitos = %s,
                               total_faltantes = %s,
                               total_regulares = %s,
                               valor_total = %s
                         WHERE id = %s
                    """, (totals["entregue"], totals["copias"], totals["defeitos"],
                            totals["faltantes"], totals["regulares"], totals["valor_total"], retorno_id))

            # (3) Mantém status do envio como "Em Conferência"
            cols_envio = self._cols(cur, schema, "envios_cortes")
            if "status_envio" in cols_envio:
                cur.execute(f"""
                    UPDATE {schema}.envios_cortes
                       SET status_envio = 'Em Conferência'
                     WHERE id = %s
                """, (envio_id,))
            elif "status" in cols_envio:
                cur.execute(f"""
                    UPDATE {schema}.envios_cortes
                       SET status = 'Em Conferência'
                     WHERE id = %s
                """, (envio_id,))

            conn.commit()
            conn.close()

            messagebox.showinfo("Sucesso", "Baixa parcial salva com sucesso.")
            self.limpar_campos()
            self.carregar_retornos_pendentes()

        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            messagebox.showerror("Erro", f"Falha ao salvar baixa parcial: {e}")

    def limpar_campos(self):
        self.retorno_selecionado = None
        self._prestador_id = None
        self._prestador_nome = ""
        self._tipo_servico = ""

        for entry in [self.prestador_entry, self.servico_entry, self.entrada_id_entry,
                      self.codigo_entry, self.descricao_entry, self.ordem_entry, self.data_entrada_entry]:
            entry.configure(state="normal")
            entry.delete(0, tk.END)
            entry.configure(state="disabled")

        for t in self.tamanhos:
            self.entregues_vars[t].set(0)
            self.copias_vars[t].set(0)
            self.defeitos_vars[t].set(0)
            self.faltantes_vars[t].set(0)
            self.grade_widgets[t]["enviado"].configure(text="0")
            self.grade_widgets[t]["valor"].configure(text=fmt_moeda(0))
            self.grade_widgets[t]["regulares"].configure(text="0")
            self.grade_widgets[t]["subtotal"].configure(text=fmt_moeda(0))

        self.lbl_total_entregue.configure(text="0")
        self.lbl_total_copias.configure(text="0")
        self.lbl_total_defeito.configure(text="0")
        self.lbl_total_faltante.configure(text="0")
        self.lbl_total_regulares.configure(text="0")
        self.lbl_valor_total.configure(text=fmt_moeda(0))
        self.obs_finalizacao_txt.delete("1.0", tk.END)


# ============================== Executar ==============================
if __name__ == "__main__":
    # Verificação simplificada - remove o parâmetro da chamada
    ok, msg = require_ready()

    if not ok:
        messagebox.showwarning("Banco de Dados", f"Problema ao conectar ao PostgreSQL:\n{msg}")

    root = ctk.CTk()
    root.title("Finalização de Cortes - Controle de Mão de Obra")
    root.geometry("1400x900")
    app = FinalizacaoCortes(root)
    root.mainloop()
