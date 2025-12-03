# NOVA_ORDEM.py — módulo completo (ajustado)
import customtkinter as ctk
from TEMAS import get_contraste_texto, is_dark_color, ajustar_hover
from tkinter import messagebox
from datetime import datetime
import os
from tkinter import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import os
import json
import logging

# ===================== Configuração de logger =====================
# Define um logger simples para registrar operações de salvamento. O logger
# usa um StreamHandler padrão (saída no console) com um formato de data e
# nível. Essa configuração é aplicada apenas se o logger ainda não tiver
# handlers, evitando múltiplos handlers em execuções repetidas.
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ===================== Acesso ao PostgreSQL =====================
try:
    # Módulo de acesso que lê config.json e expõe get_conn/get_schema/require_ready
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
    # Se esse módulo também expõe a pasta de ordens, usamos; senão, fallback abaixo
    try:
        from BANCO_DE_DADOS_PG import PASTA_ORDENS_CORTE  # opcional
    except Exception:
        PASTA_ORDENS_CORTE = None
except Exception as e:
    # Fallback explícito para facilitar mensagens de erro
    def get_conn():
        raise RuntimeError(f"Módulo BANCO_DE_DADOS_PG indisponível: {e}")
    def get_schema():
        return "opera"
    def require_ready(essentials=None):
        return False, "Módulo de banco de dados não disponível"
    PASTA_ORDENS_CORTE = None

# Fallback para a pasta de saída dos PDFs (se não vier do módulo PG)
if not PASTA_ORDENS_CORTE:
    BASE_DB_DIR = os.path.join("../BANCO DE DADOS", "ORDENS_CORTE")
    os.makedirs(BASE_DB_DIR, exist_ok=True)
    PASTA_ORDENS_CORTE = BASE_DB_DIR


# ===================== Helpers SQL =====================
def _exec_all(query: str, params=()):
    """Executa SELECT (múltiplas linhas) já setando o search_path."""
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
    """Executa SELECT (uma linha) já setando o search_path."""
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
    """Executa INSERT/UPDATE/DELETE com commit."""
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


class OrdemCorte(ctk.CTkFrame):

    def _apply_role_colors(self, parent=None):
        import customtkinter as ctk
        parent = parent or self

        try:
            for w in parent.winfo_children():
                if isinstance(w, ctk.CTkButton):
                    txt = (w.cget("text") or "").lower()

                    # Botão de salvar / confirmar / registrar
                    if any(x in txt for x in ["salvar", "registrar", "confirmar"]):
                        w.configure(
                            fg_color=self.cor_sucesso,
                            hover_color=self._ajustar_hover(self.cor_sucesso),
                            text_color=self.cor_texto
                        )

                    # Botão de cancelar / excluir / apagar
                    elif any(x in txt for x in ["cancelar", "excluir", "apagar"]):
                        w.configure(
                            fg_color=self.cor_alerta,
                            hover_color=self._ajustar_hover(self.cor_alerta),
                            text_color=self.cor_texto
                        )

                    # Botão de impressão / exportar / pré-visualização
                    elif any(x in txt for x in ["imprimir", "exportar", "pré-visualização"]):
                        w.configure(
                            fg_color=self.cor_imprimir,
                            hover_color=self._ajustar_hover(self.cor_imprimir),
                            text_color="#FFFFFF" if self._is_dark_color(self.cor_imprimir) else "#000000"
                        )

                    # Botões genéricos usam a cor primária do tema
                    else:
                        w.configure(
                            fg_color=self.cor_primaria,
                            hover_color=self._ajustar_hover(self.cor_primaria),
                            text_color=self.cor_texto
                        )

                # Recursividade para frames internos
                if hasattr(w, "winfo_children"):
                    self._apply_role_colors(w)

        except Exception as e:
            print(f"Erro ao aplicar cores: {e}")

    # ------ pequenas utils de cor usadas acima ------
    def _is_dark_color(self, hex_color):
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            # luminância relativa simples
            return (0.299*r + 0.587*g + 0.114*b) < 140
        except Exception:
            return False

    def _ajustar_hover(self, hex_color):
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            r = max(0, min(255, int(r * 0.85)))
            g = max(0, min(255, int(g * 0.85)))
            b = max(0, min(255, int(b * 0.85)))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    def __init__(self, master, *args, **kwargs):
        """
        Construtor da tela de Ordem de Corte.

        Compatível com:
        - Chamada via MENU_PRINCIPAL: OrdemCorte(master=frame, sistema=app)
        - Execução direta de teste: OrdemCorte(root)  ou  OrdemCorte(root, tema_dict)
        - Chamada antiga: OrdemCorte(frame, app_obj)
        """
        # -----------------------------
        # 1) Descobrir o "sistema" (MENU PRINCIPAL)
        # -----------------------------
        sistema_kw = kwargs.pop("sistema", None)
        app_kw = kwargs.pop("app", None)

        sistema = sistema_kw or app_kw

        # Se vierem aliases usados em outras telas
        if sistema is None:
            sistema = (
                    kwargs.get("controller")
                    or kwargs.get("ctx")
                    or kwargs.get("root")
                    or kwargs.get("main")
            )

        # Se alguém passou algo posicional depois de master
        tema_posicional = None
        if args:
            primeiro = args[0]
            if isinstance(primeiro, dict):
                # Caso: OrdemCorte(root, {"fundo": ..., ...})
                tema_posicional = primeiro
            else:
                # Caso: OrdemCorte(root, sistema)
                if sistema is None:
                    sistema = primeiro

        # Guarda o sistema (MENU PRINCIPAL) para uso posterior
        self.sistema = sistema

        # -----------------------------
        # 2) Definir cores PRINCIPAIS a partir do MENU
        #    (HERDAR DIRETAMENTE DO SISTEMA)
        # -----------------------------
        if self.sistema is not None:
            # Sempre pegar as cores diretamente do menu principal
            self.cor_fundo = getattr(self.sistema, "cor_fundo", "#DEDEDE")
            self.cor_texto = getattr(self.sistema, "cor_texto", "#1A1A1A")
            self.cor_primaria = getattr(self.sistema, "cor_primaria", "#C9C9C9")
            self.cor_borda = getattr(self.sistema, "cor_borda", "#A3A3A3")
            self.cor_hover = getattr(self.sistema, "cor_hover", "#808080")
            self.cor_sucesso = getattr(self.sistema, "cor_sucesso", "#2E9E6E")
            self.cor_alerta = getattr(self.sistema, "cor_alerta", "#D63854")
            self.cor_destaque = getattr(self.sistema, "cor_destaque", "#636363")
            self.cor_selecao = getattr(self.sistema, "cor_selecao", "#008000")
            # **NOVO**: secundária e terciária também herdadas do menu
            self.cor_secundaria = getattr(self.sistema, "cor_secundaria", self.cor_primaria)
            self.cor_terciaria = getattr(self.sistema, "cor_terciaria", self.cor_primaria)
            # Se o sistema tiver cor específica para imprimir, usa; senão cai na primária
            self.cor_imprimir = getattr(self.sistema, "cor_imprimir", self.cor_terciaria)
        else:
            # Fallback: caso a tela seja aberta sozinha, sem menu
            # (ou em testes isolados)
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
            # **NOVO**: secundária e terciária também no fallback
            self.cor_secundaria = tema_local.get("secundaria", self.cor_primaria)
            self.cor_terciaria = tema_local.get("terciaria", self.cor_primaria)
            self.cor_imprimir = tema_local.get("imprimir", self.cor_terciaria)

        # Guarda também um dicionário de tema interno (opcional)
        self.tema = {
            "fundo": self.cor_fundo,
            "texto": self.cor_texto,
            "primaria": self.cor_primaria,
            "secundaria": self.cor_secundaria,
            "terciaria": self.cor_terciaria,
            "borda": self.cor_borda,
            "hover": self.cor_hover,
            "sucesso": self.cor_sucesso,
            "alerta": self.cor_alerta,
            "destaque": self.cor_destaque,
            "selecao": self.cor_selecao,
            "imprimir": self.cor_imprimir,
        }

        # -----------------------------
        # 3) Inicializar o Frame base já com a cor correta de fundo
        # -----------------------------
        super().__init__(master, fg_color=self.cor_fundo, **kwargs)

        # -----------------------------
        # 4) Estados internos
        # -----------------------------
        self.campos_grade = {}
        self.inputs_grade = {}
        self.grade_disponivel = []

        # Layout base
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # -----------------------------
        # 5) Criar os widgets da tela
        # -----------------------------
        self.criar_widgets()

        # -----------------------------
        # 6) Carregar modelos depois de montar a tela
        # -----------------------------
        self.after(100, self.carregar_modelos_combo)

    def apply_theme(self, paleta: dict):
        """
        Recebe o dicionário de tema do menu (OperaMenuApp.theme) e
        reaplica as cores em todos os widgets desta tela.
        """

        if not isinstance(paleta, dict):
            return

        # atualiza dicionário interno
        self.tema.update(paleta)

        # atualiza atributos de cor
        self.cor_fundo     = self.tema.get("fundo",     self.cor_fundo)
        self.cor_texto     = self.tema.get("texto",     self.cor_texto)
        self.cor_primaria  = self.tema.get("primaria",  self.cor_primaria)
        self.cor_secundaria = self.tema.get("secundaria", self.cor_secundaria)
        self.cor_borda     = self.tema.get("borda",     self.cor_borda)
        self.cor_hover     = self.tema.get("hover",     self.cor_hover)
        self.cor_sucesso   = self.tema.get("sucesso",   self.cor_sucesso)
        self.cor_alerta    = self.tema.get("alerta",    self.cor_alerta)
        self.cor_destaque  = self.tema.get("destaque",  self.cor_destaque)
        self.cor_selecao   = self.tema.get("selecao",   self.cor_selecao)
        self.cor_imprimir  = self.tema.get("imprimir", self.tema.get("terciaria", self.cor_imprimir))

        # aplica no próprio frame
        self.configure(fg_color=self.cor_fundo)

        # percorre todos widgets da tela e reaplica cores básicas
        try:
            for w in self.winfo_children():
                self._reaplicar_cores_widgets(w)
        except Exception:
            pass

    def _reaplicar_cores_widgets(self, widget):
        """
        Ajusta as cores de cada tipo de widget (frames, labels, botões,
        entries, comboboxes, etc.), recursivamente.
        """
        import tkinter as tk

        try:
            import customtkinter as ctk
        except Exception:
            ctk = None

        try:
            # --------- widgets CTk ---------
            if ctk is not None:
                if isinstance(widget, ctk.CTkFrame):
                    widget.configure(fg_color=self.cor_fundo, border_color=self.cor_borda)

                elif isinstance(widget, ctk.CTkLabel):
                    widget.configure(text_color=self.cor_texto)

                elif isinstance(widget, ctk.CTkEntry):
                    widget.configure(
                        fg_color=self.cor_secundaria,
                        border_color=self.cor_borda,
                        text_color=self.cor_texto,
                    )

                elif isinstance(widget, ctk.CTkComboBox):
                    widget.configure(
                        fg_color=self.cor_secundaria,
                        border_color=self.cor_borda,
                        button_color=self.cor_primaria,
                        button_hover_color=self.cor_hover,
                        text_color=self.cor_texto,
                    )

                elif isinstance(widget, ctk.CTkScrollableFrame):
                    widget.configure(fg_color=self.cor_fundo)

                elif isinstance(widget, ctk.CTkButton):
                    # cor padrão dos botões: secundária
                    fg = self.cor_secundaria
                    hv = self.cor_hover
                    # se for botão de salvar / sucesso
                    texto = (widget.cget("text") or "").lower()
                    if any(p in texto for p in ["salvar", "registrar", "confirmar"]):
                        fg = self.cor_sucesso
                    # se for cancelar/excluir
                    elif any(p in texto for p in ["cancelar", "excluir", "apagar"]):
                        fg = self.cor_alerta
                    # se for imprimir/exportar
                    elif any(p in texto for p in ["imprimir", "exportar", "pré-visualização"]):
                        fg = self.cor_imprimir

                    widget.configure(
                        fg_color=fg,
                        hover_color=hv,
                        border_color=self.cor_borda,
                        text_color=self.cor_texto,
                    )

            # --------- widgets Tk puros (Canvas etc.) ---------
            if isinstance(widget, tk.Canvas):
                widget.configure(bg=self.cor_fundo)

        except Exception:
            pass

        # recursão para os filhos
        try:
            for child in widget.winfo_children():
                self._reaplicar_cores_widgets(child)
        except Exception:
            pass


    def criar_widgets(self):
        # Configurar para tamanho A4 (210x297mm em pixels, considerando 96dpi)
        if isinstance(self.master, (ctk.CTk, ctk.CTkToplevel)):
            self.master.geometry("900x700")

        # Frame principal com scrollbar
        self.main_frame = ctk.CTkScrollableFrame(self, fg_color=self.cor_fundo, width=900, height=1123)
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        # Cabeçalho com espaço para logo
        cabecalho_frame = ctk.CTkFrame(self.main_frame, fg_color=self.cor_fundo, height=50)
        cabecalho_frame.pack(fill="x", pady=(20, 10), padx=20)

        ctk.CTkLabel(cabecalho_frame,
                     text="ORDEM DE CORTE",
                     font=("Arial", 18, "bold"),
                     text_color=self.cor_texto).pack(side="left")

        # Linha 1 - Campo de Busca
        busca_frame = ctk.CTkFrame(self.main_frame, fg_color=self.cor_fundo)
        busca_frame.pack(fill="x", padx=20, pady=(5, 10))

        ctk.CTkLabel(busca_frame,
                     text="Buscar Modelo (Código ou Descrição):",
                     font=("Arial", 12),
                     text_color=self.cor_texto).pack(side="left")

        self.busca_entry = ctk.CTkEntry(busca_frame,
                                        width=300,
                                        placeholder_text="Ex: VEST123 ou Vestido Longo",
                                        fg_color=self.cor_fundo,
                                        border_color=self.cor_borda, text_color=self.cor_texto)
        self.busca_entry.pack(side="left", padx=5)
        self.busca_entry.bind("<Return>", lambda e: self.buscar_modelo())  # Enter ativa busca

        buscar_btn = ctk.CTkButton(busca_frame,
                                   text="Buscar",
                                   command=self.buscar_modelo,
                                   fg_color=self.cor_primaria,
                                   hover_color=self.cor_hover)
        buscar_btn.pack(side="left", padx=5)

        self.modelos_combo = ctk.CTkComboBox(
            busca_frame,
            values=["Carregando..."],
            width=300,
            command=self._on_combo_modelo
        )
        self.modelos_combo.set("Modelos disponíveis")
        self.modelos_combo.pack(side="left", padx=(10, 0))

        # Linha 2 - Código, Modelo e Data
        linha1_frame = ctk.CTkFrame(self.main_frame, fg_color=self.cor_fundo)
        linha1_frame.pack(fill="x", pady=5, padx=20)

        ctk.CTkLabel(linha1_frame,
                     text="CODIGO:",
                     font=("Arial", 12),
                     text_color=self.cor_texto).pack(side="left")

        self.codigo_entry = ctk.CTkEntry(linha1_frame,
                                         width=100,
                                         placeholder_text="___________",
                                         fg_color=self.cor_fundo,
                                         border_color=self.cor_borda, text_color=self.cor_texto)
        self.codigo_entry.pack(side="left", padx=5)

        ctk.CTkLabel(linha1_frame,
                     text="Modelo:",
                     font=("Arial", 12),
                     text_color=self.cor_texto).pack(side="left", padx=10)

        self.modelo_entry = ctk.CTkEntry(linha1_frame,
                                         width=300,
                                         placeholder_text="______________________________________",
                                         fg_color=self.cor_fundo,
                                         border_color=self.cor_borda, text_color=self.cor_texto)
        self.modelo_entry.pack(side="left", padx=5)

        ctk.CTkLabel(linha1_frame,
                     text="DATA " + datetime.now().strftime("%d/%m/%Y"),
                     font=("Arial", 12),
                     text_color=self.cor_texto).pack(side="right", padx=10)

        # Linha 2 - Cortador, Auxiliar e Data Finalização
        linha2_frame = ctk.CTkFrame(self.main_frame, fg_color=self.cor_fundo)
        linha2_frame.pack(fill="x", pady=5, padx=20)

        ctk.CTkLabel(linha2_frame,
                     text="CORTADOR:",
                     font=("Arial", 12),
                     text_color=self.cor_texto).pack(side="left")

        self.cortador_entry = ctk.CTkEntry(linha2_frame,
                                           width=150,
                                           placeholder_text="________________",
                                           fg_color=self.cor_fundo,
                                           border_color=self.cor_borda, text_color=self.cor_texto)
        self.cortador_entry.pack(side="left", padx=5)

        ctk.CTkLabel(linha2_frame,
                     text="AUXILIAR:",
                     font=("Arial", 12),
                     text_color=self.cor_texto).pack(side="left", padx=10)

        self.auxiliar_entry = ctk.CTkEntry(linha2_frame,
                                           width=200,
                                           placeholder_text="______________________________",
                                           fg_color=self.cor_fundo,
                                           border_color=self.cor_borda, text_color=self.cor_texto)
        self.auxiliar_entry.pack(side="left", padx=5)

        ctk.CTkLabel(linha2_frame,
                     text="DATA FINALIZAÇÃO:",
                     font=("Arial", 12),
                     text_color=self.cor_texto).pack(side="left", padx=10)

        self.data_final_entry = ctk.CTkEntry(linha2_frame,
                                             width=120,
                                             placeholder_text="__/__/____",
                                             fg_color=self.cor_fundo,
                                             border_color=self.cor_borda, text_color=self.cor_texto)
        self.data_final_entry.pack(side="left")

        # Grade de Corte
        self.criar_grade_corte()

        # Seção de Tecidos
        self.criar_secao_tecidos()

        # ===============================
        # BOTÕES PADRONIZADOS - NOVA_ORDEM
        # ===============================

        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20, padx=20)

        # Botão "Imprimir Pré-visualização" → Azul fixo
        imprimir_btn = ctk.CTkButton(
            btn_frame,
            text="Imprimir Pré-visualização",
            command=self.previsualizar_impressao,
            fg_color=getattr(self.sistema, 'cor_selecao', '#4A90E2'),  # Azul vivo fixo
            hover_color="#357ABD",  # Azul escuro no hover
            text_color="#FFFFFF"  # Texto branco para contraste
        )
        imprimir_btn.pack(side="right", padx=10)

        # Botão "Salvar Ordem" → Verde fixo
        salvar_btn = ctk.CTkButton(
            btn_frame,
            text="Salvar Ordem",
            command=self.salvar_ordem,
            fg_color=getattr(self.sistema, 'cor_selecao', '#2E7D32'),  # Verde vivo fixo
            hover_color="#1B5E20",  # Verde escuro no hover
            text_color="#FFFFFF"
        )
        salvar_btn.pack(side="right", padx=10)

        # Botão "Cancelar" → Vermelho fixo
        cancelar_btn = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=self.master.destroy,
            fg_color=getattr(self.sistema, 'cor_selecao', '#D32F2F'),  # Vermelho vivo fixo
            hover_color="#B71C1C",  # Vermelho escuro no hover
            text_color="#FFFFFF"
        )
        cancelar_btn.pack(side="right", padx=10)

    def criar_grade_corte(self):
        """Cria a seção de grade de corte com campos de entrada"""
        grade_frame = ctk.CTkFrame(self.main_frame, fg_color=self.cor_fundo)
        grade_frame.pack(fill="x", pady=10, padx=20)

        ctk.CTkLabel(grade_frame,
                     text="GRADE DE CORTE",
                     font=("Arial", 14, "bold"),
                     text_color=self.cor_texto).pack(anchor="w")

        # Cabeçalho
        header_frame = ctk.CTkFrame(grade_frame, fg_color=self.cor_fundo)
        header_frame.pack(fill="x", pady=5)

        tamanhos = ["TAMANHOS", "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "CONSUMO PEÇA"]
        for i, tamanho in enumerate(tamanhos):
            ctk.CTkLabel(header_frame,
                         text=tamanho,
                         width=70 if i > 0 else 100,
                         font=("Arial", 11, "bold"),
                         text_color=self.cor_texto).grid(row=0, column=i, padx=2)

        # Linha de porcentagem
        porcent_frame = ctk.CTkFrame(grade_frame, fg_color=self.cor_fundo)
        porcent_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(porcent_frame,
                     text="PORCENTAGEM",
                     width=100,
                     font=("Arial", 11),
                     text_color=self.cor_texto).grid(row=0, column=0)

        for i in range(1, 9):  # PP até G3
            entry = ctk.CTkEntry(porcent_frame,
                                 width=70,
                                 font=("Arial", 10),
                                 fg_color=self.cor_fundo,
                                 border_color=self.cor_borda,
                                 text_color=self.cor_texto)
            entry.grid(row=0, column=i, padx=2)
            self.campos_grade[f"porcent_{i}"] = entry

        # Adicionando o campo de consumo da peça
        consumo = ctk.CTkEntry(porcent_frame,
                               width=70,
                               font=("Arial", 10),
                               fg_color=self.cor_fundo,
                               border_color=self.cor_borda,
                               text_color=self.cor_texto)
        consumo.grid(row=0, column=9, padx=2)
        self.campos_grade["consumo_peca"] = consumo

        # Quantidade Desejada
        quant_frame = ctk.CTkFrame(grade_frame, fg_color=self.cor_fundo)
        quant_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(quant_frame,
                     text="QUANTIDADE DESEJADA:",
                     font=("Arial", 12),
                     text_color=self.cor_texto).pack(side="left")

        self.quantidade_entry = ctk.CTkEntry(quant_frame,
                                             width=150,
                                             placeholder_text="Qtd Total",
                                             fg_color=self.cor_fundo,
                                             border_color=self.cor_borda,
                                             text_color=self.cor_texto)
        self.quantidade_entry.pack(side="left", padx=10)

        ctk.CTkLabel(quant_frame,
                     text="DIAS ESTIMADOS:",
                     font=("Arial", 12),
                     text_color=self.cor_texto).pack(side="left", padx=10)

        self.dias_estimados_entry = ctk.CTkEntry(quant_frame,
                                                 width=50,
                                                 placeholder_text="Ex: 3",
                                                 fg_color=self.cor_fundo,
                                                 border_color=self.cor_borda, text_color=self.cor_texto)
        self.dias_estimados_entry.pack(side="left")

        ctk.CTkLabel(quant_frame,
                     text="HORAS ESTIMADAS:",
                     font=("Arial", 12),
                     text_color=self.cor_texto).pack(side="left", padx=10)

        self.horas_estimadas_entry = ctk.CTkEntry(quant_frame,
                                                  width=50,
                                                  placeholder_text="Ex: 6",
                                                  fg_color=self.cor_fundo,
                                                  border_color=self.cor_borda, text_color=self.cor_texto)
        self.horas_estimadas_entry.pack(side="left")

    def criar_secao_tecidos(self):
        tecidos_main_frame = ctk.CTkFrame(self.main_frame, fg_color=self.cor_fundo)
        tecidos_main_frame.pack(fill="x", pady=10, padx=20)

        for linha in range(2):  # 2 linhas de blocos
            linha_frame = ctk.CTkFrame(tecidos_main_frame, fg_color=self.cor_fundo)
            linha_frame.pack(fill="x", pady=10)

            linha_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="col")

            # Sempre mostrar rótulos nas caixas TECIDO 1
            self.criar_bloco_tecido(linha_frame, "TECIDO 1", 0, mostrar_rotulos=True)
            self.criar_bloco_largura(linha_frame, 1)
            self.criar_bloco_tecido(linha_frame, "TECIDO 2", 2, mostrar_rotulos=False)
            self.criar_bloco_tecido(linha_frame, "TECIDO 3", 3, mostrar_rotulos=False)
            self.criar_bloco_tecido(linha_frame, "FORRO", 4, mostrar_rotulos=False)

    def criar_bloco_tecido(self, parent, titulo, coluna, mostrar_rotulos=True):
        # Frame do tecido
        tecido_frame = ctk.CTkFrame(
            parent,
            fg_color=self.cor_fundo,
            border_width=2,
            border_color=self.cor_borda
        )
        tecido_frame.grid(row=0, column=coluna, sticky="nsew", padx=2, pady=5)

        ctk.CTkLabel(
            tecido_frame,
            text=titulo,
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        ).pack(pady=(5, 5))

        bloco_frame = ctk.CTkFrame(tecido_frame, fg_color=self.cor_fundo)
        bloco_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        cor_fundo_canvas = self.sistema.cor_fundo if self.sistema else self.cor_fundo

        if mostrar_rotulos:
            textos = ["CÓDIGO", "NOME", "COMPOSIÇÃO"]
            for texto in textos:
                ctk.CTkLabel(
                    bloco_frame,
                    text=texto,
                    font=("Arial", 10, "bold"),
                    text_color=self.cor_texto
                ).pack(anchor="w", padx=5)

                canvas = Canvas(
                    bloco_frame,
                    height=20,
                    bg=cor_fundo_canvas,
                    highlightthickness=0
                )
                canvas.pack(fill="x", padx=5, pady=(0, 6))
                canvas.create_line(0, 18, 240, 18, fill=self.cor_borda, width=1)
        else:
            espacamento = 25
            canvas = Canvas(
                bloco_frame,
                height=130,
                bg=cor_fundo_canvas,
                highlightthickness=0
            )
            canvas.pack(fill="x", padx=5, pady=10)
            for i in range(5):
                y = 15 + i * espacamento
                canvas.create_line(10, y, 240, y, fill=self.cor_borda, width=1)

    def criar_bloco_largura(self, parent, coluna):
        largura_frame = ctk.CTkFrame(
            parent,
            fg_color=self.cor_fundo,
            border_width=2,
            border_color=self.cor_borda
        )
        largura_frame.grid(row=0, column=coluna, sticky="nsew", padx=2, pady=5)

        ctk.CTkLabel(
            largura_frame,
            text="LARGURA/MTS",
            font=("Arial", 12, "bold"),
            text_color=self.cor_texto
        ).pack(pady=(5, 10))

        cor_fundo_canvas = self.sistema.cor_fundo if self.sistema else self.cor_fundo

        canvas = Canvas(
            largura_frame,
            height=130,
            bg=cor_fundo_canvas,
            highlightthickness=0
        )
        canvas.pack(fill="x", padx=10, pady=10)

        espacamento = 25
        for i in range(5):
            y = 15 + i * espacamento
            canvas.create_line(10, y, 280, y, fill=self.cor_borda, width=1)

    # =================== ACESSO A DADOS (PostgreSQL) ===================
    @staticmethod
    def _map_colunas(nome_tabela: str):
        """
        Descobre como se chamam as colunas (codigo, descricao, grade, id) na tabela informada.
        Retorna um dict com chaves: codigo, descricao (ou None), grade (ou None), id (ou None).
        """
        rows = _exec_all("""
            SELECT LOWER(column_name)
              FROM information_schema.columns
             WHERE table_schema = current_schema()
               AND table_name = %s
        """, (nome_tabela,))
        cols = {r[0] for r in rows}

        def pick(*cands):
            for c in cands:
                if c and c.lower() in cols:
                    return c
            return None

        m = {
            "codigo": pick("codigo", "codigo_modelo", "cod_modelo", "cod", "modelo_codigo"),
            "descricao": pick("descricao", "descricao_modelo", "modelo", "nome", "titulo"),
            "grade": pick("grade_disponivel", "grade", "grade_modelo"),
            "id": pick("id", "id_modelo", "id_cadastro", "pk", "codigo_id")
        }
        if not m["codigo"]:
            raise RuntimeError(f"A tabela {nome_tabela} não possui nenhuma coluna de código conhecida.")
        return m

    def _resolver_tabela_modelo(self):
        """
        Detecta qual tabela existe: 'ficha_tecnica_cabecalho' (legado) ou
        'cadastro_modelos_cabecalho' (atual), usando information_schema.
        """
        for nome in ("cadastro_modelos_cabecalho", "ficha_tecnica_cabecalho"):
            row = _exec_row("""
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = current_schema()
                   AND table_name = %s
                 LIMIT 1
            """, (nome,))
            if row:
                return nome
        raise RuntimeError(
            "Nenhuma tabela de modelos encontrada (ficha_tecnica_cabecalho/cadastro_modelos_cabecalho)."
        )

    def carregar_modelos_combo(self):
        try:
            nome_tabela = self._resolver_tabela_modelo()
            m = self._map_colunas(nome_tabela)

            # Monta SELECT só com colunas existentes
            partes = [m["codigo"]]
            if m["descricao"]:
                partes.append(f"COALESCE({m['descricao']}, '')")
            selecao = ", ".join(partes)

            orderby = m["codigo"] if not m["id"] else m["id"]

            rows = _exec_all(f"""
                SELECT {selecao}
                  FROM {nome_tabela}
                 WHERE TRIM(COALESCE({m['codigo']}, '')) <> ''
                 ORDER BY {orderby} ASC
            """)

            # Normaliza em (codigo, descricao)
            valores = []
            for r in rows:
                if len(r) == 1:
                    codigo, desc = r[0], ""
                else:
                    codigo, desc = r[0], r[1] or ""
                valores.append(f"{codigo} - {desc}".strip(" -"))

            self.modelos_combo.configure(values=valores or ["(nenhum modelo)"])
            self.modelos_combo.set("Selecione um modelo")
        except Exception as e:
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao carregar modelos:\n{e}")

    def _on_combo_modelo(self, escolha: str):
        """Quando o usuário seleciona um item no ComboBox."""
        if not escolha or escolha in ("(nenhum modelo)", "Modelos disponíveis"):
            return
        codigo = escolha.split(" - ")[0].strip()
        if codigo:
            self.preencher_modelo_por_codigo(codigo)

    def preencher_modelo_por_codigo(self, codigo: str):
        """Busca pelo código e preenche código, descrição e grade_disponivel (PG)."""
        try:
            nome_tabela = self._resolver_tabela_modelo()
            m = self._map_colunas(nome_tabela)

            # SELECT só com colunas existentes
            partes = [m["codigo"]]
            if m["descricao"]:
                partes.append(f"COALESCE({m['descricao']}, '')")
            if m["grade"]:
                partes.append(m["grade"])
            selecao = ", ".join(partes)

            row = _exec_row(f"""
                SELECT {selecao}
                  FROM {nome_tabela}
                 WHERE {m['codigo']} = %s
                 LIMIT 1
            """, (codigo,))

            if not row:
                messagebox.showinfo("Resultado", "Modelo não encontrado.")
                return

            cod = row[0]
            desc = row[1] if len(row) > 1 else ""
            grade_val = row[2] if len(row) > 2 else None

            self.codigo_entry.delete(0, "end");
            self.codigo_entry.insert(0, cod or "")
            self.modelo_entry.delete(0, "end");
            self.modelo_entry.insert(0, desc or "")

            if grade_val and str(grade_val).strip():
                self.grade_disponivel = [t.strip().upper() for t in str(grade_val).split(",") if t.strip()]
            else:
                self.grade_disponivel = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]

            self.atualizar_campos_grade()

        except Exception as e:
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao buscar modelo:\n{e}")

    def buscar_modelo(self):
        """
        Busca por código OU descrição digitados no campo de busca e
        preenche a tela com o primeiro resultado mais recente (PG).
        """
        termo = self.busca_entry.get().strip()
        if not termo:
            messagebox.showwarning("Atenção", "Digite um código ou descrição para buscar.")
            return

        try:
            nome_tabela = self._resolver_tabela_modelo()
            m = self._map_colunas(nome_tabela)
            like = f"%{termo}%"

            partes = [m["codigo"]]
            if m["descricao"]:
                partes.append(f"COALESCE({m['descricao']}, '')")
            if m["grade"]:
                partes.append(m["grade"])
            selecao = ", ".join(partes)

            filtros = [f"{m['codigo']} ILIKE %s"]
            params = [like]
            if m["descricao"]:
                filtros.append(f"{m['descricao']} ILIKE %s")
                params.append(like)
            where = " OR ".join(filtros)

            orderby = m["id"] or m["codigo"]

            row = _exec_row(f"""
                SELECT {selecao}
                  FROM {nome_tabela}
                 WHERE {where}
                 ORDER BY {orderby} DESC
                 LIMIT 1
            """, tuple(params))

            if not row:
                messagebox.showinfo("Resultado", "Nenhum modelo encontrado com esse termo.")
                return

            cod = row[0]
            desc = row[1] if len(row) > 1 else ""
            grade_val = row[2] if len(row) > 2 else None

            self.codigo_entry.delete(0, "end");
            self.codigo_entry.insert(0, cod or "")
            self.modelo_entry.delete(0, "end");
            self.modelo_entry.insert(0, desc or "")

            if grade_val:
                self.grade_disponivel = [t.strip().upper() for t in str(grade_val).split(",") if t.strip()]
            else:
                self.grade_disponivel = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]

            self.atualizar_campos_grade()

            # Espelha no ComboBox, se existir
            try:
                if hasattr(self, "modelos_combo") and self.modelos_combo is not None:
                    alvo = f"{cod} - {desc}".strip(" -")
                    if alvo in (self.modelos_combo.cget("values") or []):
                        self.modelos_combo.set(alvo)
            except Exception:
                pass

        except Exception as e:
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao buscar modelo:\n{e}")

    def atualizar_campos_grade(self):
        """Atualiza os campos de porcentagem conforme a grade disponível"""
        try:
            mapeamento_tamanhos = {
                1: "PP", 2: "P", 3: "M", 4: "G",
                5: "GG", 6: "G1", 7: "G2", 8: "G3"
            }

            for num, tamanho in mapeamento_tamanhos.items():
                campo = self.campos_grade.get(f"porcent_{num}")
                if campo:
                    if tamanho in self.grade_disponivel:
                        campo.configure(state="normal")
                        if not campo.get():
                            campo.insert(0, "0")
                    else:
                        campo.delete(0, "end")
                        campo.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("Erro na Interface", f"Falha ao atualizar campos:\n{str(e)}")

    # =================== PDF / Impressão ===================

    def previsualizar_impressao(self):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from datetime import datetime
        import os

        # ---------- Preparação do arquivo ----------
        codigo_modelo = self.codigo_entry.get().strip().replace("/", "-").replace("\\", "-")
        if not codigo_modelo:
            codigo_modelo = f"ordem_sem_codigo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        caminho_pasta = PASTA_ORDENS_CORTE  # vindo do módulo ou fallback

        nome_arquivo = f"{codigo_modelo}.pdf"
        caminho_pdf = os.path.join(caminho_pasta, nome_arquivo)

        contador = 1
        while os.path.exists(caminho_pdf):
            nome_arquivo = f"{codigo_modelo}_{contador}.pdf"
            caminho_pdf = os.path.join(caminho_pasta, nome_arquivo)
            contador += 1

        # ---------- Criando o PDF ----------
        c = canvas.Canvas(caminho_pdf, pagesize=A4)
        width, height = A4
        margem_esq = 20
        margem_dir = width - 20
        y = height - 20

        # ---------- Cabeçalho ----------
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, y, "ORDEM DE CORTE")
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(margem_dir, y, f"DATA: {datetime.now().strftime('%d/%m/%Y')}")

        # ---------- Logo no canto superior esquerdo ----------
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(base_dir, "LOGO.JPG")  # nome real do arquivo
            if os.path.exists(logo_path):
                img = ImageReader(logo_path)

                LOGO_H = 35  # altura em pontos (~8,8 mm)
                iw, ih = img.getSize()
                scale = LOGO_H / float(ih)
                LOGO_W = iw * scale

                c.drawImage(
                    logo_path,
                    margem_esq,
                    height - 5 - LOGO_H,  # topo da página (não altera y do layout)
                    width=LOGO_W,
                    height=LOGO_H,
                    mask='auto'
                )
        except Exception as e:
            print("Aviso: não foi possível desenhar a logo:", e)

        # ---------- Bloco de identificação ----------
        y -= 35
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margem_esq, y, f"CODIGO: {self.codigo_entry.get()}")
        c.drawString(margem_esq + 90, y, f"Modelo: {self.modelo_entry.get()}")
        y -= 20
        c.drawString(margem_esq, y, f"CORTADOR: {self.cortador_entry.get()}")
        y -= 15
        c.drawString(margem_esq, y, f"AUXILIAR: {self.auxiliar_entry.get()}")
        c.drawRightString(margem_dir, y + 15, f"FINALIZAÇÃO: {self.data_final_entry.get()}")

        # ---------- Grade de corte ----------
        y -= 10
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width / 2, y, "GRADE DE CORTE")
        y -= 18

        col_titulos = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]
        col_w = 50
        inicio_x = margem_esq + 65
        col_x = [inicio_x + i * col_w for i in range(len(col_titulos))]

        c.setFont("Helvetica-Bold", 8)
        altura_linha = 12
        y_tamanhos = y
        for i, titulo in enumerate(col_titulos):
            c.rect(col_x[i], y_tamanhos - altura_linha, col_w, altura_linha)
            c.drawCentredString(col_x[i] + col_w // 2, y_tamanhos - altura_linha + 3, titulo)
        c.drawCentredString(margem_esq + 32, y_tamanhos - altura_linha + 3, "TAMANHOS")

        # Bloco CONSUMO PEÇA
        consumo_x = col_x[-1] + col_w + 15
        consumo_w = 80
        consumo_h = altura_linha * 2
        c.rect(consumo_x, y_tamanhos - consumo_h, consumo_w, consumo_h)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(consumo_x + consumo_w / 2, y_tamanhos - altura_linha + 2, "CONSUMO PEÇA")
        c.setFont("Helvetica", 8)
        c.drawCentredString(consumo_x + consumo_w / 2, y_tamanhos - consumo_h + 3,
                            self.campos_grade["consumo_peca"].get())
        c.setFont("Helvetica-Bold", 8)

        y -= 18
        for i in range(len(col_titulos)):
            c.rect(col_x[i], y - altura_linha, col_w, altura_linha)
            val = self.campos_grade.get(f"porcent_{i + 1}").get()
            c.drawCentredString(col_x[i] + col_w // 2, y - altura_linha + 3, val)
        c.drawCentredString(margem_esq + 32, y - altura_linha + 3, "PORCENTAGEM")
        y -= 30

        # ---------- Quantidade desejada ----------
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margem_esq, y, "QUANTIDADE DESEJADA:")
        c.drawString(margem_esq + 160, y, self.quantidade_entry.get())
        y -= 30

        # ---------- Tecidos ----------
        colunas = ["TECIDO 1", "LARGURA/MTS", "TECIDO 2", "TECIDO 3", "FORRO"]
        col_w = 110
        col_x = [margem_esq + i * col_w for i in range(len(colunas))]
        c.setFont("Helvetica-Bold", 10)
        for i, titulo in enumerate(colunas):
            c.drawCentredString(col_x[i] + col_w / 2, y, titulo)
        y -= 10

        linhas = 7
        linha_altura = 14
        box_altura = linha_altura * (linhas + 1)
        espacamento = box_altura + 8
        c.setFont("Helvetica-Bold", 9)

        for _ in range(5):
            c.rect(col_x[0], y - box_altura, col_w, box_altura)
            base_y = y - box_altura + 10
            c.drawString(col_x[0] + 5, base_y + 38, "CÓDIGO")
            c.drawString(col_x[0] + 5, base_y + 24, "NOME")
            c.drawString(col_x[0] + 5, base_y + 10, "COMPOSIÇÃO")
            for j in range(1, 5):
                c.rect(col_x[j], y - box_altura, col_w, box_altura)
                for i in range(linhas):
                    linha_y = y - 12 - i * linha_altura
                    c.line(col_x[j] + 5, linha_y, col_x[j] + col_w - 10, linha_y)
            y -= espacamento

        # ---------- Observações ----------
        y -= 5
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margem_esq, y, "OBSERVAÇÕES:")
        y -= 12
        for _ in range(2):
            c.line(margem_esq, y, margem_dir, y)
            y -= 12

        y -= 10
        c.drawString(margem_esq, y, "Assinatura do Responsável:")
        c.line(margem_esq + 160, y, margem_dir, y)

        # ---------- Finalizar ----------
        c.showPage()
        c.save()

        try:
            os.startfile(caminho_pdf)  # Windows
        except AttributeError:
            try:
                os.system(f"open '{caminho_pdf}'")  # macOS
            except:
                os.system(f"xdg-open '{caminho_pdf}'")  # Linux

    def _tabela_existe(self, nome: str) -> bool:
        """Retorna True se a tabela existir no schema atual."""
        row = _exec_row(
            """
            SELECT 1
              FROM information_schema.tables
             WHERE table_schema = current_schema()
               AND table_name = %s
             LIMIT 1
            """,
            (nome,),
        )
        return bool(row)

    def _inserir_em_cadastro_de_corte(self, codigo: str, descricao: str, cortador: str, quantidade: int | None):
        """
        Insere também na tabela CADASTRO_DE_CORTE (se existir), garantindo que a
        DESCRIÇÃO seja gravada junto. Detecta automaticamente os nomes das colunas.
        Colunas comuns: codigo, descricao, cortador, total_pecas, data
        """
        if not self._tabela_existe("cadastro_de_corte"):
            return  # não existe — nada a fazer

        # Descobre colunas
        cols = [r[0] for r in _exec_all(
            """
            SELECT LOWER(column_name)
              FROM information_schema.columns
             WHERE table_schema = current_schema()
               AND table_name = %s
            """,
            ("cadastro_de_corte",),
        )]
        def pick(*cands):
            for c in cands:
                if c.lower() in cols:
                    return c
            return None

        c_cod = pick("codigo", "codigo_corte", "cod", "codigo_modelo")
        c_desc = pick("descricao", "descricao_corte", "descricao_modelo", "modelo", "nome")
        c_cort = pick("cortador", "responsavel")
        c_qtd = pick("total_pecas", "quantidade", "qtd", "qtde")
        c_data = pick("data", "data_registro", "data_cadastro")

        # Monta INSERT só com o que existe
        campos = []
        valores = []
        params = []
        if c_cod:
            campos.append(c_cod); valores.append("%s"); params.append(codigo)
        if c_desc:
            campos.append(c_desc); valores.append("%s"); params.append(descricao)
        if c_cort:
            campos.append(c_cort); valores.append("%s"); params.append(cortador or None)
        if c_qtd:
            campos.append(c_qtd); valores.append("%s"); params.append(quantidade)
        if c_data:
            campos.append(c_data); valores.append("%s"); params.append(datetime.now().strftime("%d/%m/%Y"))

        if not campos:
            return  # não há nada compatível para inserir

        _exec_write(
            f"INSERT INTO cadastro_de_corte ({', '.join(campos)}) VALUES ({', '.join(valores)})",
            tuple(params),
        )

    def salvar_ordem(self):
        """Salva uma ordem de corte na tabela ordem_corte_ficha (com ajudante incluso)."""
        try:
            from datetime import datetime, date, timedelta
            import json

            # ----- Porcentagens -----
            porcentagens = {}
            for k, var in self.campos_grade.items():
                if k.startswith("porcent_"):
                    raw = var.get().strip() if hasattr(var, "get") else str(var).strip()
                    raw = raw.replace(",", ".") or "0"
                    try:
                        porcentagens[k] = float(raw)
                    except ValueError:
                        porcentagens[k] = 0.0

            # ----- Campos principais -----
            codigo = self.codigo_entry.get().strip()
            descricao = self.modelo_entry.get().strip()
            cortador = self.cortador_entry.get().strip()
            auxiliar = self.auxiliar_entry.get().strip() or None
            ajudante = None
            if hasattr(self, "ajudante_entry"):
                ajudante = self.ajudante_entry.get().strip() or None

            # ----- Data final -----
            data_final_str = self.data_final_entry.get().strip()
            if data_final_str:
                data_final = datetime.strptime(data_final_str, "%d/%m/%Y").date()
            else:
                data_final = date.today()

            # ----- Estimativas -----
            dias_txt = self.dias_estimados_entry.get().strip().replace(",", ".") or "0"
            horas_txt = self.horas_estimadas_entry.get().strip().replace(",", ".") or "0"
            try:
                dias = float(dias_txt)
                horas = float(horas_txt)
            except ValueError:
                dias = horas = 0.0
            dias_estimados = dias + (horas / 24.0)

            # ----- Quantidade -----
            qtd_str = self.quantidade_entry.get().strip()
            quantidade = int(qtd_str) if qtd_str.isdigit() else None

            consumo_raw = self.campos_grade.get("consumo_peca")
            consumo = consumo_raw.get().strip() if consumo_raw else None

            # ----- Detecta colunas existentes -----
            cols = [r[0].lower() for r in _exec_all("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = current_schema()
                AND table_name = 'ordem_corte_ficha'
            """)]

            def pick(*cands):
                for c in cands:
                    if c.lower() in cols:
                        return c
                return None

            c_codigo = pick("codigo_modelo")
            c_desc = pick("descricao_modelo")
            c_cort = pick("cortador")
            c_aux = pick("auxiliar")
            c_aju = pick("ajudante")
            c_dataf = pick("data_final")
            c_dias = pick("dias_estimados")
            c_horas = pick("horas_estimadas")
            c_porcent = pick("porcentagens")
            c_consumo = pick("consumo_peca")
            c_qtd = pick("quantidade_desejada")
            c_total = pick("total_pecas")

            # ----- Monta INSERT dinâmico -----
            insert_cols, placeholders, params = [], [], []

            def add(col, val):
                if col:
                    insert_cols.append(col)
                    placeholders.append("%s")
                    params.append(val)

            add(c_codigo, codigo)
            add(c_desc, descricao)
            add(c_cort, cortador)
            add(c_aux, auxiliar)
            add(c_aju, ajudante)
            add(c_dataf, data_final)
            add(c_dias, dias_estimados)
            add(c_horas, horas)
            add(c_porcent, json.dumps(porcentagens, ensure_ascii=False))
            add(c_consumo, consumo)
            add(c_qtd, quantidade)
            add(c_total, quantidade)

            if not insert_cols:
                raise RuntimeError("Nenhuma coluna compatível encontrada para inserir ordem de corte.")

            query = f"INSERT INTO ordem_corte_ficha ({', '.join(insert_cols)}) VALUES ({', '.join(placeholders)})"
            _exec_write(query, tuple(params))

            log_data = {col: val for col, val in zip(insert_cols, params)}
            logger.info(f"✅ Ordem de corte salva: {log_data}")

            messagebox.showinfo("Sucesso", "Ordem de corte salva com sucesso!")
            self.previsualizar_impressao()
            self.limpar_campos()

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar ordem:\n{e}")

    def limpar_campos(self):
        """Limpa todos os campos do formulário"""
        self.codigo_entry.delete(0, "end")
        self.modelo_entry.delete(0, "end")
        self.cortador_entry.delete(0, "end")
        self.auxiliar_entry.delete(0, "end")
        self.data_final_entry.delete(0, "end")
        self.quantidade_entry.delete(0, "end")
        self.dias_estimados_entry.delete(0, "end")
        self.horas_estimadas_entry.delete(0, "end")

        for campo in self.campos_grade.values():
            campo.delete(0, "end")
            campo.configure(state="normal")




if __name__ == "__main__":
    """
    Ponto de entrada do módulo. Verifica conexão com o banco de dados e
    inicializa a interface gráfica caso o ambiente suporte Tkinter.

    A função require_ready foi atualizada para não aceitar argumentos.
    Portanto, invocamos sem parâmetros. Em versões antigas do módulo de
    banco, passar uma lista vazia também funcionará. Caso ocorra um
    TypeError, um fallback com lista vazia será usado. Qualquer outro erro
    exibe uma mensagem simples.
    """
    try:
        try:
            ok, msg = require_ready()
        except TypeError:
            ok, msg = require_ready([])
        except Exception as exc:
            ok, msg = False, str(exc)

        if not ok:
            try:
                messagebox.showwarning("Banco de Dados", f"Problema ao conectar ao PostgreSQL:\n{msg}")
            except Exception:
                print(f"Problema ao conectar ao PostgreSQL: {msg}")

        # Inicializa a interface gráfica somente se tkinter estiver disponível
        try:
            ctk.set_appearance_mode("light")
            root = ctk.CTk()
            root.title("Ordem de Corte")

            tema = {
                "fundo": "#f0f0f0",
                "texto": "#2c3e50",
                "primaria": "#275090",
                "borda": "#c0c0c0",
                "hover": "#a0c0ff"
            }

            app = OrdemCorte(root, tema)
            app.pack(fill="both", expand=True)
            root.mainloop()
        except Exception as gui_exc:
            # Em ambientes sem suporte a GUI, apenas registra o erro
            print(f"Falha ao iniciar a interface gráfica: {gui_exc}")
    except Exception as e:
        # Captura genérica para evitar que exceções não tratadas quebrem o script
        print(f"Erro inesperado ao iniciar a aplicação: {e}")
