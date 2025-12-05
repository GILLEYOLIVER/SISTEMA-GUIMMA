# DEF.py - Módulo completo de Ordem de Corte
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import os
from tkinter import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import json
import logging
import tkinter as tk

# ===================== Configuração de logger =====================
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ===================== Acesso ao PostgreSQL =====================
try:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready

    try:
        from BANCO_DE_DADOS_PG import PASTA_ORDENS_CORTE
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
    BASE_DB_DIR = os.path.join("../BANCO DE DADOS", "ORDENS_CORTE")
    os.makedirs(BASE_DB_DIR, exist_ok=True)
    PASTA_ORDENS_CORTE = BASE_DB_DIR


# ===================== Helpers SQL =====================
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


# ============================================================
#  PREFERÊNCIAS DE GRADE POR USUÁRIO (TABELA 48)
# ============================================================
_grade_pref_table_ok = False


def ensure_grade_pref_table():
    global _grade_pref_table_ok
    if _grade_pref_table_ok:
        return

    try:
        conn = get_conn()
        cur = conn.cursor()

        # Verifica se schema opera existe
        cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'opera'")
        if not cur.fetchone():
            cur.execute("CREATE SCHEMA opera")
            conn.commit()
            print("✅ Schema opera criado")

        # Cria a tabela no schema opera
        cur.execute("""
            CREATE TABLE IF NOT EXISTS opera.ordem_grade_preferencias (
                id            SERIAL PRIMARY KEY,
                usuario_id    INTEGER NOT NULL,
                nome          VARCHAR(100) NOT NULL,
                porcent_1     NUMERIC(12,4) DEFAULT 0,
                porcent_2     NUMERIC(12,4) DEFAULT 0,
                porcent_3     NUMERIC(12,4) DEFAULT 0,
                porcent_4     NUMERIC(12,4) DEFAULT 0,
                porcent_5     NUMERIC(12,4) DEFAULT 0,
                porcent_6     NUMERIC(12,4) DEFAULT 0,
                porcent_7     NUMERIC(12,4) DEFAULT 0,
                porcent_8     NUMERIC(12,4) DEFAULT 0,
                criado_em     TIMESTAMP DEFAULT NOW(),
                atualizado_em TIMESTAMP DEFAULT NOW(),
                UNIQUE (usuario_id, nome)
            )
        """)
        conn.commit()

        # Verifica se tabela usuarios existe e adiciona FK se existir
        try:
            cur.execute("""
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'opera' 
                AND table_name = 'usuarios'
                LIMIT 1
            """)
            if cur.fetchone():
                # Adiciona FK se não existir
                cur.execute("""
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_schema = 'opera' 
                    AND table_name = 'ordem_grade_preferencias' 
                    AND constraint_name = 'ordem_grade_preferencias_usuario_id_fkey'
                    LIMIT 1
                """)
                if not cur.fetchone():
                    cur.execute("""
                        ALTER TABLE opera.ordem_grade_preferencias 
                        ADD CONSTRAINT ordem_grade_preferencias_usuario_id_fkey 
                        FOREIGN KEY (usuario_id) 
                        REFERENCES opera.usuarios(id) 
                        ON DELETE CASCADE
                    """)
                    conn.commit()
                    print("✅ FK para usuarios adicionada")
        except Exception as e:
            print(f"⚠️ Não foi possível adicionar FK: {e}")

        _grade_pref_table_ok = True
        print("✅ Tabela ordem_grade_preferencias verificada/criada")
        cur.close()
        conn.close()

    except Exception as e:
        print("⚠️ Erro ao criar/verificar tabela ordem_grade_preferencias:", e)
        if conn:
            conn.close()
        raise


class OrdemCorte(ctk.CTkFrame):

    def __init__(self, master, *args, **kwargs):
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

        super().__init__(master, fg_color=self.cor_fundo, **kwargs)

        self.campos_grade = {}
        self.inputs_grade = {}
        self.grade_disponivel = []

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.criar_widgets()
        self.after(100, self.carregar_modelos_combo)

    def _is_dark_color(self, hex_color):
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            return (0.299 * r + 0.587 * g + 0.114 * b) < 140
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

    def criar_widgets(self):
        if isinstance(self.master, (ctk.CTk, ctk.CTkToplevel)):
            self.master.geometry("900x700")

        self.main_frame = ctk.CTkScrollableFrame(self, fg_color=self.cor_fundo, width=900, height=1123)
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        cabecalho_frame = ctk.CTkFrame(self.main_frame, fg_color=self.cor_fundo, height=50)
        cabecalho_frame.pack(fill="x", pady=(20, 10), padx=20)

        ctk.CTkLabel(cabecalho_frame,
                     text="ORDEM DE CORTE",
                     font=("Arial", 18, "bold"),
                     text_color=self.cor_texto).pack(side="left")

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
        self.busca_entry.bind("<Return>", lambda e: self.buscar_modelo())

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

        # Chamar criar_grade_corte antes de criar_secao_tecidos
        self.criar_grade_corte()
        self.criar_secao_tecidos()

        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20, padx=20)

        imprimir_btn = ctk.CTkButton(
            btn_frame,
            text="Imprimir Pré-visualização",
            command=self.previsualizar_impressao,
            fg_color=getattr(self.sistema, 'cor_selecao', '#4A90E2'),
            hover_color="#357ABD",
            text_color="#FFFFFF"
        )
        imprimir_btn.pack(side="right", padx=10)

        salvar_btn = ctk.CTkButton(
            btn_frame,
            text="Salvar Ordem",
            command=self.salvar_ordem,
            fg_color=getattr(self.sistema, 'cor_selecao', '#2E7D32'),
            hover_color="#1B5E20",
            text_color="#FFFFFF"
        )
        salvar_btn.pack(side="right", padx=10)

        cancelar_btn = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=self.master.destroy,
            fg_color=getattr(self.sistema, 'cor_selecao', '#D32F2F'),
            hover_color="#B71C1C",
            text_color="#FFFFFF"
        )
        cancelar_btn.pack(side="right", padx=10)

    def criar_grade_corte(self):
        grade_frame = ctk.CTkFrame(self.main_frame, fg_color=self.cor_fundo)
        grade_frame.pack(fill="x", pady=10, padx=20)

        ctk.CTkLabel(
            grade_frame,
            text="GRADE DE CORTE",
            font=("Arial", 14, "bold"),
            text_color=self.cor_texto
        ).pack(anchor="w")

        self.grade_pref_var = tk.StringVar(value="")

        # Vincular a variável para detectar mudanças
        self.grade_pref_var.trace('w', lambda *args: self._on_grade_pref_change())

        pref_frame = ctk.CTkFrame(grade_frame, fg_color=self.cor_fundo)
        pref_frame.pack(fill="x", pady=(4, 4))

        ctk.CTkLabel(
            pref_frame,
            text="Preferência de grade:",
            font=("Arial", 11),
            text_color=self.cor_texto
        ).pack(side="left", padx=(0, 6))

        self.combo_grade = ctk.CTkComboBox(
            pref_frame,
            variable=self.grade_pref_var,
            values=[],
            width=220,
            state="readonly"
        )
        self.combo_grade.pack(side="left", padx=4)

        btn_salvar_pref = ctk.CTkButton(
            pref_frame,
            text="Salvar grade como preferência",
            command=self.salvar_preferencia_grade,
            fg_color=self.cor_sucesso,
            hover_color=self._ajustar_hover(self.cor_sucesso),
            text_color=self.cor_texto,
            font=("Arial", 11)
        )
        btn_salvar_pref.pack(side="left", padx=6)

        btn_excluir_pref = ctk.CTkButton(
            pref_frame,
            text="Excluir preferência",
            command=self.excluir_preferencia_grade,
            fg_color=self.cor_alerta,
            hover_color=self._ajustar_hover(self.cor_alerta),
            text_color=self.cor_texto,
            font=("Arial", 11)
        )
        btn_excluir_pref.pack(side="left", padx=6)

        header_frame = ctk.CTkFrame(grade_frame, fg_color=self.cor_fundo)
        header_frame.pack(fill="x", pady=5)

        tamanhos = ["TAMANHOS", "PP", "P", "M", "G", "GG", "G1", "G2", "G3", "CONSUMO PEÇA"]
        for i, tamanho in enumerate(tamanhos):
            largura = 70 if i > 0 else 100
            ctk.CTkLabel(
                header_frame,
                text=tamanho,
                width=largura,
                font=("Arial", 11, "bold"),
                text_color=self.cor_texto
            ).grid(row=0, column=i, padx=2)

        porcent_frame = ctk.CTkFrame(grade_frame, fg_color=self.cor_fundo)
        porcent_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(
            porcent_frame,
            text="PORCENTAGEM",
            width=100,
            font=("Arial", 11),
            text_color=self.cor_texto
        ).grid(row=0, column=0)

        for i in range(1, 9):
            entry = ctk.CTkEntry(
                porcent_frame,
                width=70,
                font=("Arial", 10),
                fg_color=self.cor_fundo,
                border_color=self.cor_borda,
                text_color=self.cor_texto
            )
            entry.grid(row=0, column=i, padx=2)
            self.campos_grade[f"porcent_{i}"] = entry

        consumo = ctk.CTkEntry(
            porcent_frame,
            width=70,
            font=("Arial", 10),
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            text_color=self.cor_texto
        )
        consumo.grid(row=0, column=9, padx=2)
        self.campos_grade["consumo_peca"] = consumo

        quant_frame = ctk.CTkFrame(grade_frame, fg_color=self.cor_fundo)
        quant_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            quant_frame,
            text="QUANTIDADE DESEJADA:",
            font=("Arial", 12),
            text_color=self.cor_texto
        ).pack(side="left")

        self.quantidade_entry = ctk.CTkEntry(
            quant_frame,
            width=80,
            placeholder_text="Ex: 500",
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            text_color=self.cor_texto
        )
        self.quantidade_entry.pack(side="left", padx=(4, 10))

        ctk.CTkLabel(
            quant_frame,
            text="DIAS ESTIMADOS:",
            font=("Arial", 12),
            text_color=self.cor_texto
        ).pack(side="left", padx=4)

        self.dias_estimados_entry = ctk.CTkEntry(
            quant_frame,
            width=50,
            placeholder_text="Ex: 3",
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            text_color=self.cor_texto
        )
        self.dias_estimados_entry.pack(side="left")

        ctk.CTkLabel(
            quant_frame,
            text="HORAS ESTIMADAS:",
            font=("Arial", 12),
            text_color=self.cor_texto
        ).pack(side="left", padx=10)

        self.horas_estimadas_entry = ctk.CTkEntry(
            quant_frame,
            width=50,
            placeholder_text="Ex: 6",
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            text_color=self.cor_texto
        )
        self.horas_estimadas_entry.pack(side="left")

        # Carregar preferências ao iniciar
        self.after(200, self.carregar_preferencias_grade)

    def _on_grade_pref_change(self):
        """Chamado automaticamente quando a preferência de grade muda no combobox"""
        nome = self.grade_pref_var.get().strip()
        if nome and nome not in ["", "Selecione...", "Nenhuma preferência"]:
            # Pequeno delay para garantir que a interface está atualizada
            self.after(100, lambda: self.aplicar_preferencia_grade_silenciosa())

    def aplicar_preferencia_grade_silenciosa(self):
        """Versão silenciosa que não mostra mensagens de sucesso/erro"""
        nome = self.grade_pref_var.get().strip()
        if not nome or not getattr(self, "usuario_id", None):
            return

        try:
            ensure_grade_pref_table()
        except Exception as e:
            print("⚠️ Erro ao garantir tabela de preferências de grade:", e)
            return

        try:
            row = _exec_row(
                """
                SELECT porcent_1, porcent_2, porcent_3, porcent_4,
                       porcent_5, porcent_6, porcent_7, porcent_8
                  FROM ordem_grade_preferencias
                 WHERE usuario_id = %s
                   AND nome = %s
                """,
                (self.usuario_id, nome)
            )
        except Exception as e:
            # Não mostra mensagem de erro para não incomodar o usuário
            print(f"⚠️ Erro ao buscar preferência '{nome}': {e}")
            return

        if row:
            valores = row
            for i, val in enumerate(valores, start=1):
                campo = self.campos_grade.get(f"porcent_{i}")
                if campo:
                    # Habilita o campo temporariamente para preencher
                    estado_original = campo.cget("state")
                    campo.configure(state="normal")
                    campo.delete(0, "end")
                    # Formata o valor usando a função de formatação
                    if val is not None:
                        valor_formatado = self.formatar_para_inteiro_se_possivel(val)
                        campo.insert(0, valor_formatado)
                    else:
                        campo.insert(0, "0")
                    # Restaura o estado original baseado na grade disponível
                    mapeamento_tamanhos = {
                        1: "PP", 2: "P", 3: "M", 4: "G",
                        5: "GG", 6: "G1", 7: "G2", 8: "G3"
                    }
                    tamanho = mapeamento_tamanhos.get(i)
                    if tamanho and tamanho in self.grade_disponivel:
                        campo.configure(state="normal")
                    else:
                        campo.configure(state="disabled")

            # Mostra mensagem sutil no console
            print(f"✅ Preferência '{nome}' aplicada automaticamente")
        else:
            print(f"⚠️ Preferência '{nome}' não encontrada")

    def carregar_preferencias_grade(self):
        """Carrega a lista de preferências de grade do usuário logado para o ComboBox."""
        try:
            ensure_grade_pref_table()
        except Exception as e:
            print("⚠️ Erro ao garantir tabela de preferências de grade:", e)

        if not getattr(self, "usuario_id", None):
            # Sem usuário, não carrega nada
            if hasattr(self, "combo_grade"):
                self.combo_grade.configure(values=[])
                self.combo_grade.set("Nenhuma preferência")
            return

        try:
            rows = _exec_all(
                """
                SELECT nome
                  FROM ordem_grade_preferencias
                 WHERE usuario_id = %s
                 ORDER BY nome ASC
                """,
                (self.usuario_id,)
            )
            valores = [r[0] for r in rows] if rows else []
            if hasattr(self, "combo_grade"):
                self.combo_grade.configure(values=valores)
                if not valores:
                    self.combo_grade.set("Nenhuma preferência")
                else:
                    self.combo_grade.set("Selecione uma preferência")
        except Exception as e:
            print("⚠️ Erro ao carregar preferências de grade:", e)
            logger.error(f"Erro ao carregar preferências de grade: {e}")
            if hasattr(self, "combo_grade"):
                self.combo_grade.configure(values=["Erro ao carregar"])
                self.combo_grade.set("Erro ao carregar")

    def salvar_preferencia_grade(self):
        """Salva a grade atual (porcentagens PP–G3) como uma preferência nomeada do usuário."""
        try:
            ensure_grade_pref_table()
        except Exception as e:
            print("⚠️ Erro ao garantir tabela de preferências de grade:", e)

        if not getattr(self, "usuario_id", None):
            messagebox.showwarning(
                "Usuário não definido",
                "Não foi possível identificar o usuário logado para salvar a preferência."
            )
            return

        # Usar CTkInputDialog para entrada do nome
        try:
            from customtkinter import CTkInputDialog
            dialog = CTkInputDialog(
                text="Informe um nome para esta preferência de grade:",
                title="Salvar preferência de grade"
            )
            # Centralizar a janela
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f'{width}x{height}+{x}+{y}')
            nome = dialog.get_input()
        except ImportError:
            # Fallback caso CTkInputDialog não esteja disponível
            import tkinter.simpledialog as simpledialog
            nome = simpledialog.askstring(
                "Salvar preferência de grade",
                "Informe um nome para esta preferência de grade:"
            )

        if not nome:
            return  # cancelado

        # Lê as porcentagens atuais dos campos
        valores = []
        for i in range(1, 9):
            campo = self.campos_grade.get(f"porcent_{i}")
            if campo:
                # Habilita temporariamente se estiver disabled
                estado_original = campo.cget("state")
                if estado_original == "disabled":
                    campo.configure(state="normal")

                txt = campo.get().strip().replace(",", ".")
                if not txt:
                    valores.append(0.0)
                else:
                    try:
                        valores.append(float(txt))
                    except ValueError:
                        valores.append(0.0)

                # Restaura estado original
                if estado_original == "disabled":
                    campo.configure(state=estado_original)
            else:
                valores.append(0.0)

        try:
            # INSERIR ou ATUALIZAR
            _exec_write(
                """
                INSERT INTO ordem_grade_preferencias
                    (usuario_id, nome,
                     porcent_1, porcent_2, porcent_3, porcent_4,
                     porcent_5, porcent_6, porcent_7, porcent_8)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (usuario_id, nome) DO UPDATE SET
                    porcent_1 = EXCLUDED.porcent_1,
                    porcent_2 = EXCLUDED.porcent_2,
                    porcent_3 = EXCLUDED.porcent_3,
                    porcent_4 = EXCLUDED.porcent_4,
                    porcent_5 = EXCLUDED.porcent_5,
                    porcent_6 = EXCLUDED.porcent_6,
                    porcent_7 = EXCLUDED.porcent_7,
                    porcent_8 = EXCLUDED.porcent_8,
                    atualizado_em = NOW();
                """,
                (self.usuario_id, nome, *valores)
            )

            # Atualiza combo
            self.carregar_preferencias_grade()
            # Seleciona automaticamente a preferência recém-salva
            self.grade_pref_var.set(nome)
            if hasattr(self, "combo_grade"):
                self.combo_grade.set(nome)

            messagebox.showinfo(
                "Preferência salva",
                f"A preferência de grade '{nome}' foi salva com sucesso!\n\nAs porcentagens serão automaticamente preenchidas quando você selecionar esta preferência."
            )

        except Exception as e:
            # Log detalhado do erro
            logger.error(f"Erro ao salvar preferência de grade: {e}")
            messagebox.showerror(
                "Erro ao salvar preferência",
                f"Falha ao salvar preferência de grade:\n{str(e)[:200]}"
            )

    def excluir_preferencia_grade(self):
        """Exclui a preferência selecionada no ComboBox para o usuário atual."""
        nome = self.grade_pref_var.get().strip() if hasattr(self, "grade_pref_var") else ""
        if not nome or not getattr(self, "usuario_id", None):
            return

        if messagebox.askyesno(
                "Excluir preferência",
                f"Tem certeza que deseja excluir a preferência de grade '{nome}'?"
        ):
            try:
                ensure_grade_pref_table()
                _exec_write(
                    """
                    DELETE FROM ordem_grade_preferencias
                     WHERE usuario_id = %s
                       AND nome = %s
                    """,
                    (self.usuario_id, nome)
                )
                self.grade_pref_var.set("")
                if hasattr(self, "combo_grade"):
                    self.combo_grade.set("")
                self.carregar_preferencias_grade()
                messagebox.showinfo("Sucesso", f"Preferência '{nome}' excluída com sucesso.")
            except Exception as e:
                messagebox.showerror(
                    "Erro ao excluir preferência",
                    f"Não foi possível excluir a preferência '{nome}':\n{e}"
                )

    def criar_secao_tecidos(self):
        tecidos_main_frame = ctk.CTkFrame(self.main_frame, fg_color=self.cor_fundo)
        tecidos_main_frame.pack(fill="x", pady=10, padx=20)

        for linha in range(2):
            linha_frame = ctk.CTkFrame(tecidos_main_frame, fg_color=self.cor_fundo)
            linha_frame.pack(fill="x", pady=10)
            linha_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="col")
            self.criar_bloco_tecido(linha_frame, "TECIDO 1", 0, mostrar_rotulos=True)
            self.criar_bloco_largura(linha_frame, 1)
            self.criar_bloco_tecido(linha_frame, "TECIDO 2", 2, mostrar_rotulos=False)
            self.criar_bloco_tecido(linha_frame, "TECIDO 3", 3, mostrar_rotulos=False)
            self.criar_bloco_tecido(linha_frame, "FORRO", 4, mostrar_rotulos=False)

    def criar_bloco_tecido(self, parent, titulo, coluna, mostrar_rotulos=True):
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

    # =================== ACESSO A DADOS ===================
    @staticmethod
    def _map_colunas(nome_tabela: str):
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
        if not escolha or escolha in ("(nenhum modelo)", "Modelos disponíveis", "Selecione um modelo"):
            return

        # Extrai o código do modelo
        codigo = escolha.split(" - ")[0].strip()
        if codigo:
            # Busca e preenche o modelo
            self.preencher_modelo_por_codigo(codigo)

            # DEPOIS de preencher o modelo, tenta carregar as porcentagens padrão
            self.after(100, self.carregar_porcentagens_padrao_modelo)

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

            # ADICIONADO: Buscar também as porcentagens padrão se existirem
            # Verifica se existe coluna de porcentagens no modelo
            colunas_porcent = []
            for i in range(1, 9):
                col_possivel = f"porcent_{i}"
                # Verifica se a coluna existe na tabela
                existe = _exec_row("""
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = current_schema() 
                    AND table_name = %s 
                    AND column_name = %s
                """, (nome_tabela, col_possivel))
                if existe:
                    colunas_porcent.append(f"COALESCE({col_possivel}, 0)")

            if colunas_porcent:
                partes.extend(colunas_porcent)

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

            # Processa os resultados
            cod = row[0]
            desc = row[1] if len(row) > 1 else ""
            grade_val = row[2] if len(row) > 2 else None

            # Índice inicial para porcentagens
            idx_porcentagens = 3  # depois de código, descrição, grade

            self.codigo_entry.delete(0, "end")
            self.codigo_entry.insert(0, cod or "")
            self.modelo_entry.delete(0, "end")
            self.modelo_entry.insert(0, desc or "")

            if grade_val and str(grade_val).strip():
                self.grade_disponivel = [t.strip().upper() for t in str(grade_val).split(",") if t.strip()]
            else:
                self.grade_disponivel = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]

            self.atualizar_campos_grade()

            # Se encontrou porcentagens no banco, preenche automaticamente
            if colunas_porcent and len(row) > idx_porcentagens:
                self.preencher_porcentagens_do_banco(row[idx_porcentagens:])

        except Exception as e:
            messagebox.showerror("Erro no Banco de Dados", f"Erro ao buscar modelo:\n{e}")

    def preencher_porcentagens_do_banco(self, valores_porcentagem):
        """Preenche os campos de porcentagem com valores do banco."""
        try:
            for i, valor in enumerate(valores_porcentagem, start=1):
                campo = self.campos_grade.get(f"porcent_{i}")  # CORREÇÃO: Use self.campos_grade
                if campo and campo.cget("state") != "disabled":
                    campo.delete(0, "end")
                    if valor is not None and float(valor) != 0:
                        # Usar a função de formatação
                        valor_formatado = self.formatar_para_inteiro_se_possivel(valor)
                        campo.insert(0, valor_formatado)
                    else:
                        campo.insert(0, "0")
        except Exception as e:
            print(f"Erro ao preencher porcentagens: {e}")

    def formatar_para_inteiro_se_possivel(self, valor):
        """
        Tenta formatar um valor para inteiro se possível.
        Ex: 34.00 → "34", 34.50 → "34.50"
        """
        try:
            num = float(valor)
            if num.is_integer():
                return str(int(num))
            else:
                return f"{num:.2f}"
        except:
            return str(valor)

    def forcar_inteiro(self, valor):
        """Converte qualquer valor para inteiro, removendo casas decimais."""
        try:
            return str(int(float(valor)))
        except:
            return "0"

    def carregar_porcentagens_padrao_modelo(self):
        """Tenta carregar porcentagens padrão do modelo atual do banco."""
        try:
            codigo = self.codigo_entry.get().strip()
            if not codigo:
                return

            # Tenta buscar porcentagens da tabela de modelos primeiro
            nome_tabela = self._resolver_tabela_modelo()

            # Verifica se existem colunas de porcentagem na tabela
            colunas_existentes = []
            for i in range(1, 9):
                existe = _exec_row("""
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = current_schema() 
                    AND table_name = %s 
                    AND column_name = %s
                """, (nome_tabela, f"porcent_{i}"))
                if existe:
                    colunas_existentes.append(f"porcent_{i}")

            if not colunas_existentes:
                # Se não tem na tabela de modelos, tenta na tabela de configurações
                self.carregar_porcentagens_configuracao()
                return

            # Monta query para buscar porcentagens
            m = self._map_colunas(nome_tabela)
            selecao = ", ".join([f"COALESCE({col}, 0)" for col in colunas_existentes])

            row = _exec_row(f"""
                SELECT {selecao}
                FROM {nome_tabela}
                WHERE {m['codigo']} = %s
                LIMIT 1
            """, (codigo,))

            if row:
                # Preenche os campos com os valores do banco
                for i, valor in enumerate(row, start=1):
                    campo = self.campos_grade.get(f"porcent_{i}")
                    if campo and campo.cget("state") != "disabled":
                        campo.delete(0, "end")
                        if float(valor) != 0:
                            # Usar a função de formatação
                            valor_formatado = self.formatar_para_inteiro_se_possivel(valor)
                            campo.insert(0, valor_formatado)
                        else:
                            campo.insert(0, "0")

        except Exception as e:
            print(f"Erro ao carregar porcentagens padrão: {e}")

    def carregar_porcentagens_configuracao(self):
        """Tenta carregar porcentagens de uma tabela de configuração específica."""
        try:
            # Verifica se existe tabela de configurações de porcentagem
            existe_tabela = _exec_row("""
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = current_schema() 
                AND table_name = 'config_porcentagem_modelo'
                LIMIT 1
            """)

            if not existe_tabela:
                return

            codigo = self.codigo_entry.get().strip()
            if not codigo:
                return

            # Busca configurações para este modelo
            row = _exec_row("""
                SELECT porcent_1, porcent_2, porcent_3, porcent_4,
                       porcent_5, porcent_6, porcent_7, porcent_8
                FROM config_porcentagem_modelo
                WHERE codigo_modelo = %s
                LIMIT 1
            """, (codigo,))

            if row:
                for i, valor in enumerate(row, start=1):
                    campo = self.campos_grade.get(f"porcent_{i}")
                    if campo and campo.cget("state") != "disabled":
                        campo.delete(0, "end")
                        if valor is not None and float(valor) != 0:
                            campo.insert(0, f"{float(valor):.2f}")
                        else:
                            campo.insert(0, "0")

        except Exception as e:
            print(f"Erro ao carregar porcentagens de configuração: {e}")

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

            # Verifica se existem colunas de porcentagem
            colunas_porcent = []
            for i in range(1, 9):
                existe = _exec_row("""
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = current_schema() 
                    AND table_name = %s 
                    AND column_name = %s
                """, (nome_tabela, f"porcent_{i}"))
                if existe:
                    colunas_porcent.append(f"COALESCE(porcent_{i}, 0)")

            partes = [m["codigo"]]
            if m["descricao"]:
                partes.append(f"COALESCE({m['descricao']}, '')")
            if m["grade"]:
                partes.append(m["grade"])
            if colunas_porcent:
                partes.extend(colunas_porcent)

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

            # Processa resultados
            cod = row[0]
            desc = row[1] if len(row) > 1 else ""
            grade_val = row[2] if len(row) > 2 else None

            # Índice para porcentagens
            idx_porcentagens = 3  # depois de código, descrição, grade

            self.codigo_entry.delete(0, "end")
            self.codigo_entry.insert(0, cod or "")
            self.modelo_entry.delete(0, "end")
            self.modelo_entry.insert(0, desc or "")

            if grade_val:
                self.grade_disponivel = [t.strip().upper() for t in str(grade_val).split(",") if t.strip()]
            else:
                self.grade_disponivel = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]

            self.atualizar_campos_grade()

            # Se encontrou porcentagens, preenche automaticamente
            if colunas_porcent and len(row) > idx_porcentagens:
                self.preencher_porcentagens_do_banco(row[idx_porcentagens:])

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
                        # Só insere "0" se o campo estiver vazio
                        if not campo.get().strip():
                            campo.insert(0, "0")
                    else:
                        campo.delete(0, "end")
                        campo.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("Erro na Interface", f"Falha ao atualizar campos:\n{str(e)}")

    # =================== PDF / Impressão ===================
    def previsualizar_impressao(self):
        codigo_modelo = self.codigo_entry.get().strip().replace("/", "-").replace("\\", "-")
        if not codigo_modelo:
            codigo_modelo = f"ordem_sem_codigo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        caminho_pasta = PASTA_ORDENS_CORTE
        nome_arquivo = f"{codigo_modelo}.pdf"
        caminho_pdf = os.path.join(caminho_pasta, nome_arquivo)

        contador = 1
        while os.path.exists(caminho_pdf):
            nome_arquivo = f"{codigo_modelo}_{contador}.pdf"
            caminho_pdf = os.path.join(caminho_pasta, nome_arquivo)
            contador += 1

        c = canvas.Canvas(caminho_pdf, pagesize=A4)
        width, height = A4
        margem_esq = 20
        margem_dir = width - 20
        y = height - 20

        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, y, "ORDEM DE CORTE")
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(margem_dir, y, f"DATA: {datetime.now().strftime('%d/%m/%Y')}")

        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(base_dir, "LOGO.JPG")
            if os.path.exists(logo_path):
                img = ImageReader(logo_path)
                LOGO_H = 35
                iw, ih = img.getSize()
                scale = LOGO_H / float(ih)
                LOGO_W = iw * scale
                c.drawImage(
                    logo_path,
                    margem_esq,
                    height - 5 - LOGO_H,
                    width=LOGO_W,
                    height=LOGO_H,
                    mask='auto'
                )
        except Exception as e:
            print("Aviso: não foi possível desenhar a logo:", e)

        y -= 35
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margem_esq, y, f"CODIGO: {self.codigo_entry.get()}")
        c.drawString(margem_esq + 90, y, f"Modelo: {self.modelo_entry.get()}")
        y -= 20
        c.drawString(margem_esq, y, f"CORTADOR: {self.cortador_entry.get()}")
        y -= 15
        c.drawString(margem_esq, y, f"AUXILIAR: {self.auxiliar_entry.get()}")
        c.drawRightString(margem_dir, y + 15, f"FINALIZAÇÃO: {self.data_final_entry.get()}")

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

        c.setFont("Helvetica-Bold", 10)
        c.drawString(margem_esq, y, "QUANTIDADE DESEJADA:")
        c.drawString(margem_esq + 160, y, self.quantidade_entry.get())
        y -= 30

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

        c.showPage()
        c.save()

        try:
            os.startfile(caminho_pdf)
        except AttributeError:
            try:
                os.system(f"open '{caminho_pdf}'")
            except:
                os.system(f"xdg-open '{caminho_pdf}'")

    def _tabela_existe(self, nome: str) -> bool:
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
        if not self._tabela_existe("cadastro_de_corte"):
            return

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

        campos = []
        valores = []
        params = []
        if c_cod:
            campos.append(c_cod);
            valores.append("%s");
            params.append(codigo)
        if c_desc:
            campos.append(c_desc);
            valores.append("%s");
            params.append(descricao)
        if c_cort:
            campos.append(c_cort);
            valores.append("%s");
            params.append(cortador or None)
        if c_qtd:
            campos.append(c_qtd);
            valores.append("%s");
            params.append(quantidade)
        if c_data:
            campos.append(c_data);
            valores.append("%s");
            params.append(datetime.now().strftime("%d/%m/%Y"))

        if not campos:
            return

        _exec_write(
            f"INSERT INTO cadastro_de_corte ({', '.join(campos)}) VALUES ({', '.join(valores)})",
            tuple(params),
        )

    def salvar_ordem(self):
        try:
            from datetime import datetime, date

            porcentagens = {}
            for k, var in self.campos_grade.items():
                if k.startswith("porcent_"):
                    raw = var.get().strip() if hasattr(var, "get") else str(var).strip()
                    raw = raw.replace(",", ".") or "0"
                    try:
                        porcentagens[k] = float(raw)
                    except ValueError:
                        porcentagens[k] = 0.0

            codigo = self.codigo_entry.get().strip()
            descricao = self.modelo_entry.get().strip()
            cortador = self.cortador_entry.get().strip()
            auxiliar = self.auxiliar_entry.get().strip() or None

            data_final_str = self.data_final_entry.get().strip()
            if data_final_str:
                data_final = datetime.strptime(data_final_str, "%d/%m/%Y").date()
            else:
                data_final = date.today()

            dias_txt = self.dias_estimados_entry.get().strip().replace(",", ".") or "0"
            horas_txt = self.horas_estimadas_entry.get().strip().replace(",", ".") or "0"
            try:
                dias = float(dias_txt)
                horas = float(horas_txt)
            except ValueError:
                dias = horas = 0.0
            dias_estimados = dias + (horas / 24.0)

            qtd_str = self.quantidade_entry.get().strip()
            quantidade = int(qtd_str) if qtd_str.isdigit() else None

            consumo_raw = self.campos_grade.get("consumo_peca")
            consumo_val = None
            if consumo_raw:
                txt = consumo_raw.get().strip()
                if txt:
                    txt = txt.replace(",", ".")
                    try:
                        consumo_val = float(txt)
                    except ValueError:
                        consumo_val = None

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
            c_dataf = pick("data_final")
            c_dias = pick("dias_estimados")
            c_horas = pick("horas_estimadas")
            c_porcent = pick("porcentagens")
            c_consumo = pick("consumo_peca")
            c_qtd = pick("quantidade_desejada")
            c_total = pick("total_pecas")

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
            add(c_dataf, data_final)
            add(c_dias, dias_estimados)
            add(c_horas, horas)
            add(c_porcent, json.dumps(porcentagens, ensure_ascii=False))
            add(c_consumo, consumo_val)
            add(c_qtd, quantidade)
            add(c_total, quantidade)

            if not insert_cols:
                raise RuntimeError("Nenhuma coluna compatível encontrada para inserir ordem de corte.")

            query = f"INSERT INTO ordem_corte_ficha ({', '.join(insert_cols)}) VALUES ({', '.join(placeholders)})"
            _exec_write(query, tuple(params))

            log_data = {col: val for col, val in zip(insert_cols, params)}
            logger.info(f"✅ Ordem de corte salva com sucesso: {log_data}")

            messagebox.showinfo("Sucesso", "Ordem de corte salva com sucesso!")

            deseja_imprimir = messagebox.askyesno(
                "Imprimir ordem",
                "Deseja imprimir ordem agora?"
            )
            if deseja_imprimir:
                self.previsualizar_impressao()

            self.limpar_campos()

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar ordem:\n{e}")

    def limpar_campos(self):
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

    def apply_theme(self, paleta: dict):
        if not isinstance(paleta, dict):
            return

        self.tema.update(paleta)

        self.cor_fundo = self.tema.get("fundo", self.cor_fundo)
        self.cor_texto = self.tema.get("texto", self.cor_texto)
        self.cor_primaria = self.tema.get("primaria", self.cor_primaria)
        self.cor_secundaria = self.tema.get("secundaria", self.cor_secundaria)
        self.cor_borda = self.tema.get("borda", self.cor_borda)
        self.cor_hover = self.tema.get("hover", self.cor_hover)
        self.cor_sucesso = self.tema.get("sucesso", self.cor_sucesso)
        self.cor_alerta = self.tema.get("alerta", self.cor_alerta)
        self.cor_destaque = self.tema.get("destaque", self.cor_destaque)
        self.cor_selecao = self.tema.get("selecao", self.cor_selecao)
        self.cor_imprimir = self.tema.get("imprimir", self.tema.get("terciaria", self.cor_imprimir))

        self.configure(fg_color=self.cor_fundo)

        try:
            for w in self.winfo_children():
                self._reaplicar_cores_widgets(w)
        except Exception:
            pass

    def _reaplicar_cores_widgets(self, widget):
        import tkinter as tk

        try:
            import customtkinter as ctk
        except Exception:
            ctk = None

        try:
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
                    fg = self.cor_secundaria
                    hv = self.cor_hover
                    texto = (widget.cget("text") or "").lower()
                    if any(p in texto for p in ["salvar", "registrar", "confirmar"]):
                        fg = self.cor_sucesso
                    elif any(p in texto for p in ["cancelar", "excluir", "apagar"]):
                        fg = self.cor_alerta
                    elif any(p in texto for p in ["imprimir", "exportar", "pré-visualização"]):
                        fg = self.cor_imprimir

                    widget.configure(
                        fg_color=fg,
                        hover_color=hv,
                        border_color=self.cor_borda,
                        text_color=self.cor_texto,
                    )

            if isinstance(widget, tk.Canvas):
                widget.configure(bg=self.cor_fundo)

        except Exception:
            pass

        try:
            for child in widget.winfo_children():
                self._reaplicar_cores_widgets(child)
        except Exception:
            pass


if __name__ == "__main__":
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

        try:
            ctk.set_appearance_mode("light")
            root = ctk.CTk()
            root.title("Ordem de Corte")
            root.geometry("900x700")

            app = OrdemCorte(root)
            app.pack(fill="both", expand=True, padx=10, pady=10)
            root.mainloop()
        except Exception as gui_exc:
            print(f"Falha ao iniciar a interface gráfica: {gui_exc}")
    except Exception as e:
        print(f"Erro inesperado ao iniciar a aplicação: {e}")