import os
import sys
import uuid
import tempfile
import platform
import subprocess
import webbrowser
import shutil
from datetime import datetime

# Silencia o aviso de conflito entre PyFPDF e fpdf2
import warnings

warnings.filterwarnings(
    "ignore",
    message="You have both PyFPDF & fpdf2 installed",
    category=UserWarning,
    module="fpdf",
)

# =================== IMPORTS UI/IMG/PDF ===================
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from TEMAS import get_contraste_texto, is_dark_color, ajustar_hover
import customtkinter as ctk

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
except ImportError:
    Image = ImageTk = ImageDraw = ImageFont = None

try:
    from fpdf import FPDF
except Exception:
    raise RuntimeError("O pacote 'fpdf' é obrigatório. Instale com: pip install fpdf")

# =================== DB (PostgreSQL) ===================
import BANCO_DE_DADOS_PG as db

# =================== SISTEMA DE LOG ===================
try:
    from LOG_SISTEMA import get_logger, SistemaLogger

    logger = get_logger(os.path.dirname(os.path.abspath(__file__)))
except Exception as e:
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('OPERA_FALLBACK')
    print(f"AVISO: Módulo de log não carregado: {e}")

# =================== CONSTANTES ===================
LOGO_PATH = os.path.join(os.path.dirname(__file__), "LOGO.jpg")
TAMANHOS_DISPONIVEIS = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]


# =================== FUNÇÕES UTILITÁRIAS ===================
def verificar_conexao_banco():
    """Verifica se a conexão com o banco está funcionando."""
    try:
        result = db.fetch_one("SELECT 1 as test")
        return result is not None
    except Exception as e:
        print(f"❌ Erro na conexão com o banco: {e}")
        return False


def verificar_tabelas_existem():
    """Confere existência das tabelas necessárias. Lança ValueError se faltar algo."""
    schema = db.get_schema()
    requeridas = [
        "cadastro_modelos_cabecalho",
        "cadastro_modelos_tecidos",
        "cadastro_modelos_aviamentos",
        "cadastro_modelos_outros",
    ]
    faltando = []
    for t in requeridas:
        r = db.fetch_one(
            "SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name=%s LIMIT 1",
            (schema, t),
        )
        if not r:
            faltando.append(f"{schema}.{t}")
    if faltando:
        raise ValueError(", ".join(faltando))


def resolve_table_name(candidates):
    """Tenta resolver nome real da tabela, testando várias possibilidades."""
    schema = db.get_schema()
    for name in candidates:
        low = name.lower()
        r = db.fetch_one(
            "SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name=%s LIMIT 1",
            (schema, low),
        )
        if r:
            return low
    return None


def centralizar_janela(win, w=800, h=600):
    """Centraliza uma janela na tela."""
    try:
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = int((sw - w) / 2)
        y = int((sh - h) / 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        pass


def formatar_valor(txt):
    """Converte '1.234,56' ou '1234,56' -> 1234.56 (float)."""
    if txt is None:
        return 0.0
    s = str(txt).strip().replace(" ", "")
    if s == "":
        return 0.0
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


def formatar_para_exibicao(valor):
    """Converte 1234.56 -> '1.234,56' (str)."""
    try:
        v = float(valor)
    except:
        v = 0.0
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def validar_entrada_monetaria(novo_texto):
    """Permite apenas números, vírgula e ponto em validação de Entry."""
    if novo_texto == "":
        return True
    for ch in novo_texto:
        if ch not in "0123456789,.":
            return False
    return True


# =================== CLASSES PDF ===================
class CadastroModelosPDF(FPDF):
    """Classe para geração de PDF do cadastro de modelos."""

    def header(self):
        self.set_fill_color(0, 51, 102)
        self.rect(0, 0, 210, 28, "F")
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, x=10, y=3.5, h=20)
        self.set_font("helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.set_xy(70, 10)
        self.cell(0, 8, "CADASTRO DE MODELOS DE PRODUTO")
        self.set_draw_color(169, 190, 215)
        self.set_line_width(0.6)
        self.line(10, 30, 200, 30)
        self.set_y(32)

    def footer(self):
        self.set_y(-10)
        self.set_font("helvetica", "I", 7)
        self.cell(0, 6, f"Gerado em {datetime.now():%d/%m/%Y %H:%M}", 0, 0, "C")


def _table(pdf: FPDF, headers, rows, col_w):
    """Cria tabela no PDF."""
    pdf.set_font("helvetica", "B", 6)
    for w, h in zip(col_w, headers):
        pdf.cell(w, 4, h, border=1, align="C")
    pdf.ln()
    pdf.set_font("helvetica", "", 6)
    for row in rows:
        for w, cell in zip(col_w, row):
            pdf.cell(w, 4, str(cell), border=1)
        pdf.ln()


def _images_row(pdf: FPDF, images, size=18, per_row=6):
    """Adiciona linha de imagens no PDF."""
    if not images:
        pdf.ln(size + 2)
        return
    y0 = pdf.get_y()
    x0 = pdf.l_margin
    gap = 6
    col = 0
    for img in images:
        if os.path.isfile(img):
            pdf.image(img, x=x0 + col * (size + gap), y=y0, w=size, h=size)
            col += 1
            if col >= per_row:
                break
    pdf.ln(size + 2)


def add_data_block(pdf: FPDF, data: dict):
    """Adiciona bloco de dados principais no PDF."""
    lh = 4
    xL, xR = 10, 108

    left = [
        ("Código:", data["Codigo"]),
        ("Coleção:", data["Colecao"]),
        ("Modelista:", data["Modelista"]),
        ("Grade disp.:", data["grade_disponivel"]),
    ]
    for lab, val in left:
        pdf.set_x(xL)
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(28, lh, lab)
        pdf.set_font("helvetica", "", 8)
        pdf.cell(60, lh, val, ln=1)

    start_right = 32
    pdf.set_xy(xR, start_right)
    right = [
        ("Descrição:", data["Desc"]),
        ("Tam. Base:", data["Tam"]),
        ("Custo R$:", data["Custo"]),
        ("Pilotista:", data["Piloto"]),
    ]
    for lab, val in right:
        pdf.set_font("helvetica", "B", 8)
        pdf.cell(28, lh, lab)
        pdf.set_font("helvetica", "", 8)
        pdf.multi_cell(62, lh, val)
        pdf.set_x(xR)

    pdf.ln(1)
    pdf.set_x(xL)
    pdf.set_font("helvetica", "B", 8)
    pdf.cell(16, lh, "Data:")
    pdf.set_font("helvetica", "", 8)
    pdf.cell(28, lh, data["Data"])
    pdf.set_font("helvetica", "B", 8)
    pdf.cell(22, lh, "Dificuldade:")
    pdf.set_font("helvetica", "", 8)
    pdf.cell(0, lh, data["Dif"], ln=1)

    pdf.set_draw_color(0)
    pdf.set_line_width(0.4)
    pdf.line(10, pdf.get_y() + 1, 200, pdf.get_y() + 1)
    pdf.ln(4)


def gerar_pdf_cadastro_modelo(
        dados: dict,
        tecidos: list,
        aviamentos: list,
        outros: list,
        imagens_modelo: dict,
        imagens_tecidos: list,
        imagens_aviamentos: list,
        imagens_outros: list,
) -> str:
    """Gera PDF completo do cadastro do modelo - VERSÃO CORRIGIDA"""
    try:
        print("🔄 Iniciando geração do PDF...")

        # Criar PDF
        pdf = CadastroModelosPDF()
        pdf.add_page()

        print("📝 Adicionando dados principais...")
        add_data_block(pdf, dados)

        # Imagem do modelo - COM TRATAMENTO DE ERRO
        try:
            pdf.set_font("helvetica", "B", 8)
            pdf.ln(2)
            pdf.cell(0, 5, "IMAGEM DO MODELO", 0, 1, "C")
            y0 = pdf.get_y()
            frame_w, frame_h = 50, 70
            positions = [("frente", 30), ("costas", 120)]

            for label, x in positions:
                pdf.set_xy(x, y0)
                pdf.set_font("helvetica", "B", 7)
                pdf.cell(frame_w, 4, label.upper(), 0, 1, "C")
                img = imagens_modelo.get(label)
                if img and os.path.isfile(img):
                    try:
                        pdf.image(img, x=x, y=y0 + 4, w=frame_w, h=frame_h)
                        print(f"✅ Imagem {label} adicionada ao PDF")
                    except Exception as img_error:
                        print(f"⚠️ Erro ao adicionar imagem {label}: {img_error}")
                        pdf.rect(x, y0 + 4, frame_w, frame_h)
                else:
                    pdf.rect(x, y0 + 4, frame_w, frame_h)
            pdf.ln(frame_h + 6)
        except Exception as e:
            print(f"⚠️ Erro na seção de imagens do modelo: {e}")
            pdf.ln(80)

        # Tecidos - COM TRATAMENTO
        try:
            pdf.set_font("helvetica", "B", 8)
            pdf.cell(0, 4, "TECIDOS UTILIZADOS", 0, 1, "L")
            headers_t = ["Código", "Descrição", "Cor", "Forn.", "Comp.", "metros_peca", "valor_unidade", "Total"]
            col_t = [18, 28, 12, 20, 20, 18, 18, 18]
            rows_t = [
                [
                    t.get("Código", t.get("codigo", "")),
                    t.get("Descrição", t.get("descricao", "")),
                    t.get("Cor", t.get("cor", "")),
                    t.get("Fornecedor", t.get("fornecedor", "")),
                    t.get("Composição", t.get("composicao", "")),
                    t.get("Metros/Peça", t.get("m_peca", "")),
                    t.get("Valor Metro", t.get("valor", "")),
                    t.get("valor_total", t.get("total", "")),
                ]
                for t in tecidos
            ]
            _table(pdf, headers_t, rows_t, col_t)

            pdf.cell(0, 4, "IMAGENS DOS TECIDOS", 0, 1, "L")
            _images_row(pdf, imagens_tecidos, size=18)
        except Exception as e:
            print(f"⚠️ Erro na seção de tecidos: {e}")

        # Aviamentos - COM TRATAMENTO
        try:
            pdf.cell(0, 4, "AVIAMENTOS UTILIZADOS", 0, 1, "L")
            headers_a = ["Código", "Descrição", "Cor", "Forn.", "Qtd", "valor_unidade", "Total"]
            col_a = [18, 32, 14, 24, 14, 18, 18]
            rows_a = [
                [
                    a.get("Código", a.get("codigo", "")),
                    a.get("Descrição", a.get("descricao", "")),
                    a.get("Cor", a.get("cor", "")),
                    a.get("Fornecedor", a.get("fornecedor", "")),
                    a.get("Quantidade", a.get("quantidade", "")),
                    a.get("Valor Unidade", a.get("preco", "")),
                    a.get("valor_total", a.get("total", "")),
                ]
                for a in aviamentos
            ]
            _table(pdf, headers_a, rows_a, col_a)

            pdf.cell(0, 4, "IMAGENS DOS AVIAMENTOS", 0, 1, "L")
            _images_row(pdf, imagens_aviamentos, size=18)
        except Exception as e:
            print(f"⚠️ Erro na seção de aviamentos: {e}")

        # Outros - COM TRATAMENTO
        try:
            pdf.cell(0, 4, "OUTROS ITENS UTILIZADOS", 0, 1, "L")
            headers_o = ["Código", "Descrição", "Cor", "Unid.", "Forn.", "Preço", "Qtd", "Total"]
            col_o = [18, 32, 14, 12, 24, 18, 14, 18]
            rows_o = [
                [
                    o.get("codigo", ""),
                    o.get("descricao", ""),
                    o.get("cor", ""),
                    o.get("unidade", ""),
                    o.get("fornecedor", ""),
                    o.get("preco", ""),
                    o.get("quantidade", ""),
                    o.get("total", ""),
                ]
                for o in outros
            ]
            _table(pdf, headers_o, rows_o, col_o)

            pdf.cell(0, 4, "IMAGENS DOS OUTROS", 0, 1, "L")
            _images_row(pdf, imagens_outros, size=18)
        except Exception as e:
            print(f"⚠️ Erro na seção de outros: {e}")

        # Garante existência da pasta de saída
        os.makedirs("BANCO_DE_DADOS", exist_ok=True)
        filename = f"cadastro_modelo_{dados.get('Codigo', 'modelo')}.pdf"
        path = os.path.join("BANCO_DE_DADOS", filename)

        print(f"💾 Salvando PDF em: {path}")
        pdf.output(path)
        print("✅ PDF gerado com sucesso!")

        return path

    except Exception as e:
        print(f"❌ ERRO CRÍTICO ao gerar PDF: {e}")
        import traceback
        traceback.print_exc()
        raise


def imprimir_pdf(arquivo_pdf: str):
    """Abre o PDF para impressão/visualização."""
    try:
        if platform.system() == "Windows":
            os.startfile(arquivo_pdf)
        elif platform.system() == "Darwin":
            subprocess.run(["open", arquivo_pdf])
        else:
            subprocess.run(["xdg-open", arquivo_pdf])
    except Exception as e:
        webbrowser.open(arquivo_pdf)
        print(f"Falha ao abrir/imprimir: {e}")


# =================== CLASSE PRINCIPAL ===================
class CadastroModelosApp(ctk.CTkFrame):
    """Classe principal da aplicação de cadastro de modelos."""

    def __init__(self, master, sistema, mostrar_scrollbar=False):
        super().__init__(master)
        self.master = master
        self.sistema = sistema
        self.root = sistema.root if hasattr(sistema, 'root') else sistema

        # CORREÇÃO: Adicionar referências para imagens
        self.frente_img_ref = None
        self.costas_img_ref = None

        # Configurar logger
        self.logger = logger
        if hasattr(self.logger, "set_usuario"):
            self.logger.set_usuario(
                getattr(self, "usuario_atual", "desconhecido"),
                getattr(self, "usuario_hierarquia", "default"),
            )
        if hasattr(self.logger, "set_pagina"):
            self.logger.set_pagina("MenuPrincipal")
        if hasattr(self.logger, "info"):
            self.logger.info(
                "Sistema OPERA inicializado",
                detalhes={"versao": "1.0", "usuario": getattr(self, "usuario_atual", "desconhecido")},
            )

        # Verifica conexão com o banco
        ok, msg = db.require_ready()
        if not ok:
            messagebox.showerror("Banco não preparado", msg, parent=self.root)
            raise SystemExit(1)

        # Verifica se as tabelas necessárias existem
        print("🔍 Verificando tabelas necessárias...")
        try:
            verificar_tabelas_existem()
            print("✅ Todas as tabelas verificadas com sucesso!")
        except ValueError as e:
            messagebox.showerror(
                "Erro - Tabelas Não Encontradas",
                f"As seguintes tabelas necessárias não foram encontradas:\n\n{e}\n\n"
                "Por favor, execute o script SQL de criação de tabelas no banco de dados primeiro.",
                parent=self.root,
            )
            raise SystemExit(1)

        # Criar pasta para imagens
        print("📁 Criando estrutura de pastas para imagens...")
        if not self.criar_pastas_imagens():
            messagebox.showwarning(
                "Aviso",
                "Não foi possível criar todas as pastas de imagens, mas o sistema continuará.",
                parent=self.root,
            )

        # Inicializar estados e widgets
        self._inicializar_estados()

        # Configurar UI
        self._setup_ui()
        self._initialize_data()

        # Mostrar mensagem de sucesso
        self._auto_message("Sistema pronto! Banco e pastas configurados.")
        self.after(500, self._ajustar_tamanho_imagens)  # Ajustar após UI carregar

    def _inicializar_estados(self):
        """Inicializa todos os estados e variáveis da aplicação."""
        # Entries
        self.codigo_entry = None
        self.descricao_entry = None
        self.colecao_entry = None
        self.modelista_entry = None
        self.pilotista_entry = None
        self.custo_entry = None

        # Variáveis de controle
        self.tamanho_base_var = ctk.StringVar(value="M")
        self.dificuldade_var = ctk.StringVar(value="Médio")
        self.pronto_prod_var = ctk.IntVar(value=0)

        # Grade de tamanhos
        self.grade_vars = {}
        self.tamanhos = TAMANHOS_DISPONIVEIS
        for tamanho in self.tamanhos:
            self.grade_vars[tamanho] = ctk.IntVar(value=0)

        # Labels de imagem
        self.frente_img_label = None
        self.costas_img_label = None

        # Dados
        self.tecidos = []
        self.aviamentos = []
        self.outros = []
        self.imagens_tecidos = []
        self.imagens_aviamentos = []
        self.imagens_outros = []
        self.imagens_modelo = {"frente": None, "costas": None}
        self.cadastro_carregado_codigo = None

        # Tabelas
        self.tecidos_tabela = None
        self.aviamentos_tabela = None
        self.outros_tabela = None
        self.tabela_modelos = None

        # Containers de imagem
        self.tecidos_img_container = None
        self.aviamentos_img_container = None
        self.outros_img_container = None

        # Pesquisa
        self.pesquisa_entry = None

    # =================== MÉTODOS DE INICIALIZAÇÃO ===================
    def criar_pastas_imagens(self):
        """Cria as pastas necessárias para armazenar imagens em disco."""
        try:
            pasta_banco = "BANCO_DE_DADOS"
            if not os.path.exists(pasta_banco):
                os.makedirs(pasta_banco)
                print(f"✅ Pasta criada: {pasta_banco}")

            subpastas = [
                "IMAGENS_FRENTE_COSTAS",
                "IMAGENS_TECIDOS",
                "IMAGENS_AVIAMENTOS",
                "IMAGENS_OUTROS",
                "PDFs"
            ]

            for subpasta in subpastas:
                caminho = os.path.join(pasta_banco, subpasta)
                if not os.path.exists(caminho):
                    os.makedirs(caminho)
                    print(f"  📁 Subpasta criada: {caminho}")

            print("🎯 Estrutura de pastas para imagens criada com sucesso!")
            return True

        except Exception as e:
            print(f"❌ Erro ao criar pastas: {e}")
            return False

    def _auto_message(self, texto: str, duracao: int = 2000):
        """Exibe mensagem automática temporária, legível em temas claros e escuros."""
        parent = self.master.winfo_toplevel()

        # Cores vindas do sistema/tema
        cor_primaria = getattr(self.sistema, 'cor_primaria', '#2C3E50')
        cor_fundo = getattr(self.sistema, 'cor_fundo', '#F5F5F5')
        cor_destaque = getattr(self.sistema, 'cor_destaque', '#00BFFF')

        # Usa a função de contraste do módulo TEMAS
        cor_texto = get_contraste_texto(cor_primaria)

        popup = ctk.CTkToplevel(parent)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)

        # Fundo externo acompanha o fundo geral da aplicação
        popup.configure(fg_color=cor_fundo)

        frame = ctk.CTkFrame(
            popup,
            fg_color=cor_primaria,
            corner_radius=10,
            border_width=2,
            border_color=cor_destaque,
        )
        frame.pack(padx=2, pady=2)

        label = ctk.CTkLabel(
            frame,
            text=texto,
            font=("Arial", 13, "bold"),
            text_color=cor_texto,  # <<< AGORA USA COR EM CONTRASTE
        )
        label.pack(padx=20, pady=10)

        # Centraliza na tela
        popup.update_idletasks()
        tela_largura = parent.winfo_screenwidth()
        tela_altura = parent.winfo_screenheight()
        popup_largura = popup.winfo_width()
        popup_altura = popup.winfo_height()
        x = (tela_largura // 2) - (popup_largura // 2)
        y = (tela_altura // 2) - (popup_altura // 2)
        popup.geometry(f"+{x}+{y}")

        popup.after(duracao, popup.destroy)

    # =================== MÉTODOS DE CONFIGURAÇÃO DE UI ===================
    def _setup_ui(self):
        """Configura toda a interface usando abas."""
        for w in self.winfo_children():
            w.destroy()

        # SEMPRE usar cores do sistema
        cor_fundo = getattr(self.sistema, 'cor_fundo', '#FFFFFF')
        cor_texto = getattr(self.sistema, 'cor_texto', '#000000')
        cor_primaria = getattr(self.sistema, 'cor_primaria', '#007BFF')
        cor_borda = getattr(self.sistema, 'cor_borda', '#CED4DA')
        cor_secundaria = getattr(self.sistema, 'cor_secundaria', '#E0E0E0')

        # Configuração de layout - MAIS COMPACTO
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Frame principal MAIS COMPACTO
        main_frame = ctk.CTkFrame(self, fg_color=cor_fundo)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)  # Reduzir padding
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Criar abas (CTkTabview)
        self.tabview = ctk.CTkTabview(main_frame, fg_color=cor_fundo)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)  # Reduzir padding

        # 🔹 Aplica estilo nas abas (ativa + hover)
        self._configurar_estilo_abas()

        # Criar as abas - TODAS com cor_fundo
        self.tab_principal = self.tabview.add("Principal")
        self.tab_tecidos = self.tabview.add("Tecidos")
        self.tab_aviamentos = self.tabview.add("Aviamentos")
        self.tab_outros = self.tabview.add("Outros serviços")
        self.tab_pesquisa = self.tabview.add("Pesquisa")

        # Configurar cada aba COM LAYOUT MAIS COMPACTO
        self._create_principal_tab()
        self._create_tecidos_tab()
        self._create_aviamentos_tab()
        self._create_outros_tab()
        self._create_pesquisa_tab()

        # Botões de ação fixos na parte inferior - MAIS COMPACTOS
        self._create_action_buttons(main_frame)

    def _configurar_estilo_abas(self, notebook=None):
        """
        Deixa as abas bem destacadas, principalmente em tema claro.

        - Se 'notebook' não for passado, tenta usar self.tabview ou self.notebook.
        - Para CTkTabview: usa cores do tema (cor_selecao/cor_primaria) nas abas.
        - Para ttk.Notebook: aplica o estilo 'Opera.TNotebook'.
        """
        # Cores do tema
        cor_fundo = getattr(self.sistema, "cor_fundo", "#FFFFFF")
        cor_secundaria = getattr(self.sistema, "cor_secundaria", "#E0E0E0")
        cor_primaria = getattr(self.sistema, "cor_primaria", "#007BFF")
        cor_texto = getattr(self.sistema, "cor_texto", "#000000")
        cor_selecao = getattr(self.sistema, "cor_selecao", cor_primaria)

        # Descobrir automaticamente o controle de abas, se não foi passado
        if notebook is None:
            if hasattr(self, "tabview") and self.tabview is not None:
                notebook = self.tabview
            elif hasattr(self, "notebook") and self.notebook is not None:
                notebook = self.notebook
            else:
                return  # não há abas para configurar

        # --------- Cores de aba (normal x ativa) ----------
        # Aba ativa: usa cor_selecao, mas se for muito clara escurece duas vezes
        cor_aba_ativa = cor_selecao
        if not is_dark_color(cor_aba_ativa):
            cor_aba_ativa = ajustar_hover(ajustar_hover(cor_aba_ativa))

        # Abas normais: cinza suave (diferente do fundo)
        cor_aba_normal = cor_secundaria
        # Efeito hover nas abas
        cor_aba_hover = ajustar_hover(cor_aba_normal)

        # ================== CASO 1: CTkTabview ==================
        import customtkinter as ctk  # já está importado no arquivo, aqui só usamos o nome

        if isinstance(notebook, ctk.CTkTabview):
            notebook.configure(
                fg_color=cor_fundo,
                text_color=cor_texto,
                segmented_button_fg_color=cor_aba_normal,
                segmented_button_selected_color=cor_aba_ativa,
                segmented_button_selected_hover_color=ajustar_hover(cor_aba_ativa),
                segmented_button_unselected_color=cor_aba_normal,
                segmented_button_unselected_hover_color=cor_aba_hover,
            )
            return

        # ================== CASO 2: ttk.Notebook ==================
        if isinstance(notebook, ttk.Notebook):
            style = ttk.Style(notebook)

            fg_normal = cor_texto
            fg_ativo = get_contraste_texto(cor_aba_ativa)

            style.configure(
                "Opera.TNotebook",
                background=cor_fundo,
                borderwidth=0,
                tabmargins=(0, 0, 0, 0),
            )

            style.configure(
                "Opera.TNotebook.Tab",
                padding=(10, 4),
                background=cor_aba_normal,
                foreground=fg_normal,
                font=("Arial", 11, "bold"),
            )

            style.map(
                "Opera.TNotebook.Tab",
                background=[
                    ("selected", cor_aba_ativa),
                    ("active", cor_aba_hover),
                ],
                foreground=[
                    ("selected", fg_ativo),
                ],
            )

            notebook.configure(style="Opera.TNotebook")

    def _create_principal_tab(self):
        """Cria a aba principal priorizando espaço para imagens grandes."""
        cor_fundo = getattr(self.sistema, 'cor_fundo', '#FFFFFF')
        cor_texto = getattr(self.sistema, 'cor_texto', '#000000')
        cor_borda = getattr(self.sistema, 'cor_borda', '#CED4DA')

        # Cabeçalho SUPER COMPACTO
        titulo_frame = ctk.CTkFrame(self.tab_principal, fg_color="transparent", height=20)
        titulo_frame.pack(fill="x", pady=(2, 1), padx=5)
        titulo_frame.pack_propagate(False)

        ctk.CTkLabel(
            titulo_frame,
            text="CADASTRO DE MODELOS",
            font=("Arial", 11, "bold"),  # Fonte compacta
            text_color=cor_texto,
        ).pack()

        # Linha divisória fina
        ctk.CTkFrame(self.tab_principal, height=1, fg_color=cor_borda).pack(
            fill="x", pady=1, padx=5)

        # Cabeçalho ULTRA COMPACTO (usando a versão que criamos acima)
        self._create_compact_header(self.tab_principal)

        # Imagens do modelo (MÁXIMO TAMANHO) - isso vai ocupar o resto do espaço
        self._create_image_section_large(self.tab_principal)

    def _create_compact_header(self, parent):
        """Cria o cabeçalho compacto - VERSÃO ULTRA COMPACTA."""
        cor_texto = getattr(self.sistema, 'cor_texto', '#000000')
        cor_secundaria = getattr(self.sistema, 'cor_secundaria', '#E0E0E0')
        cor_borda = getattr(self.sistema, 'cor_borda', '#CED4DA')
        cor_selecao = getattr(self.sistema, 'cor_selecao', '#007BFF')

        # Frame principal do cabeçalho - ALTURA TOTAL REDUZIDA
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", pady=2, padx=10)  # Reduzido pady=5 -> pady=2

        # =================== LINHA 1: Código + Descrição ===================
        linha1 = ctk.CTkFrame(header_frame, fg_color="transparent", height=28)  # Altura reduzida
        linha1.pack(fill="x", pady=1)  # Espaçamento mínimo
        linha1.pack_propagate(False)

        # Código
        ctk.CTkLabel(linha1, text="Código:", font=("Arial", 11)).pack(side="left", padx=(0, 5))
        self.codigo_entry = ctk.CTkEntry(linha1, font=("Arial", 11), width=100, height=26)
        self.codigo_entry.pack(side="left", padx=(0, 15))

        # Descrição
        ctk.CTkLabel(linha1, text="Descrição:", font=("Arial", 11)).pack(side="left", padx=(0, 5))
        self.descricao_entry = ctk.CTkEntry(linha1, font=("Arial", 11), width=350, height=26)
        self.descricao_entry.pack(side="left")

        # =================== LINHA 2: Coleção + Tamanho Base + Dificuldade ===================
        linha2 = ctk.CTkFrame(header_frame, fg_color="transparent", height=28)
        linha2.pack(fill="x", pady=1)
        linha2.pack_propagate(False)

        # Coleção
        ctk.CTkLabel(linha2, text="Coleção:", font=("Arial", 11)).pack(side="left", padx=(0, 5))
        self.colecao_entry = ctk.CTkEntry(linha2, font=("Arial", 11), width=120, height=26)
        self.colecao_entry.pack(side="left", padx=(0, 15))

        # Tamanho Base - COMPACTO
        ctk.CTkLabel(linha2, text="Tam Base:", font=("Arial", 11)).pack(side="left", padx=(0, 5))
        tamanho_frame = ctk.CTkFrame(linha2, fg_color="transparent", height=26)
        tamanho_frame.pack(side="left", padx=(0, 15))

        # Radio buttons compactos
        tamanhos = ["PP", "P", "M", "G", "GG"]
        for tam in tamanhos:
            ctk.CTkRadioButton(tamanho_frame, text=tam, variable=self.tamanho_base_var, value=tam,
                               font=("Arial", 10), width=0, height=18,
                               fg_color=cor_selecao, border_color=cor_borda, text_color=cor_texto,
                               hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF')).pack(side="left", padx=2)

        # Dificuldade - COMPACTO
        ctk.CTkLabel(linha2, text="Dificuldade:", font=("Arial", 11)).pack(side="left", padx=(0, 5))
        dificuldade_frame = ctk.CTkFrame(linha2, fg_color="transparent", height=26)
        dificuldade_frame.pack(side="left")

        dificuldades = ["Fácil", "Médio", "Difícil"]
        for dif in dificuldades:
            ctk.CTkRadioButton(dificuldade_frame, text=dif, variable=self.dificuldade_var, value=dif,
                               font=("Arial", 10), width=0, height=18,
                               fg_color=cor_selecao, border_color=cor_borda, text_color=cor_texto,
                               hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF')).pack(side="left", padx=4)

        # =================== LINHA 3: Modelista + Custo + Pilotista ===================
        linha3 = ctk.CTkFrame(header_frame, fg_color="transparent", height=28)
        linha3.pack(fill="x", pady=1)
        linha3.pack_propagate(False)

        # Modelista
        ctk.CTkLabel(linha3, text="Modelista:", font=("Arial", 11)).pack(side="left", padx=(0, 5))
        self.modelista_entry = ctk.CTkEntry(linha3, font=("Arial", 11), width=120, height=26)
        self.modelista_entry.pack(side="left", padx=(0, 15))

        # Custo
        ctk.CTkLabel(linha3, text="Custo R$:", font=("Arial", 11)).pack(side="left", padx=(0, 5))
        self.custo_entry = ctk.CTkEntry(linha3, font=("Arial", 11), width=80, height=26, state="readonly")
        self.custo_entry.insert(0, "0,00")
        self.custo_entry.pack(side="left", padx=(0, 15))

        # Pilotista
        ctk.CTkLabel(linha3, text="Pilotista:", font=("Arial", 11)).pack(side="left", padx=(0, 5))
        self.pilotista_entry = ctk.CTkEntry(linha3, font=("Arial", 11), width=120, height=26)
        self.pilotista_entry.pack(side="left", padx=(0, 15))

        # Pronto para produção (Checkbox compacto)
        ctk.CTkCheckBox(linha3, text="Pronto produção", variable=self.pronto_prod_var,
                        font=("Arial", 11), height=18, width=0,
                        fg_color=cor_selecao, border_color=cor_borda, text_color=cor_texto,
                        hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF')).pack(side="left")

        # =================== LINHA 4: Grade disponível ===================
        linha4 = ctk.CTkFrame(header_frame, fg_color="transparent", height=28)
        linha4.pack(fill="x", pady=1)
        linha4.pack_propagate(False)

        ctk.CTkLabel(linha4, text="Grade disp.:", font=("Arial", 11)).pack(side="left", padx=(0, 5))

        grade_frame = ctk.CTkFrame(linha4, fg_color="transparent")
        grade_frame.pack(side="left")

        # TODOS OS TAMANHOS NA MESMA LINHA - ULTRA COMPACTO
        for tamanho in self.tamanhos:
            ctk.CTkCheckBox(grade_frame, text=tamanho, variable=self.grade_vars[tamanho],
                            font=("Arial", 9), width=0, height=16,
                            fg_color=cor_selecao, border_color=cor_borda, text_color=cor_texto,
                            hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF')).pack(side="left", padx=1)

    def _ajustar_tamanho_imagens(self):
        """Força o redimensionamento das imagens para usar espaço máximo."""
        try:
            for tipo in ['frente', 'costas']:
                caminho = self.imagens_modelo.get(tipo)
                if caminho and os.path.exists(caminho):
                    self._set_label_image(tipo, caminho)
        except Exception as e:
            print(f"⚠️ Erro ao ajustar tamanho das imagens: {e}")

    def _create_image_section_large(self, parent):
        """Cria a seção de imagens com tamanho 380x500."""
        cor_fundo = getattr(self.sistema, 'cor_fundo', '#FFFFFF')
        cor_texto = getattr(self.sistema, 'cor_texto', '#000000')
        cor_secundaria = getattr(self.sistema, 'cor_secundaria', '#E0E0E0')
        cor_primaria = getattr(self.sistema, 'cor_primaria', '#007BFF')
        cor_borda = getattr(self.sistema, 'cor_borda', '#CED4DA')

        img_frame = ctk.CTkFrame(parent, fg_color="transparent")
        img_frame.pack(fill="both", expand=True, pady=3, padx=10)

        # Título MENOR
        ctk.CTkLabel(img_frame, text="IMAGENS DO MODELO", font=("Arial", 12, "bold"),
                     text_color=cor_texto).pack(pady=(0, 3))

        # Container para as imagens lado a lado
        img_container = ctk.CTkFrame(img_frame, fg_color="transparent")
        img_container.pack(fill="both", expand=True)

        # Imagem da frente - DIMINUÍDA
        frente_frame = ctk.CTkFrame(img_container, fg_color=cor_fundo, border_color=cor_borda, border_width=1)
        frente_frame.pack(side="left", fill="both", expand=True, padx=8)

        # Título FRENTE MENOR
        ctk.CTkLabel(frente_frame, text="FRENTE", font=("Arial", 11, "bold"),
                     text_color=cor_texto).pack(pady=3)

        # LABEL DA IMAGEM FRENTE - DIMINUÍDA
        self.frente_img_label = ctk.CTkLabel(frente_frame, text="Clique para adicionar imagem",
                                             width=380, height=500, corner_radius=5,
                                             fg_color=cor_secundaria,
                                             text_color=get_contraste_texto(cor_secundaria),
                                             font=("Arial", 10))
        self.frente_img_label.pack(pady=3)
        self.frente_img_label.bind("<Button-1>", lambda e: self.adicionar_imagem("frente"))

        # Frame dos botões - COMPACTO
        frente_btn_frame = ctk.CTkFrame(frente_frame, fg_color="transparent")
        frente_btn_frame.pack(pady=3)

        # Botões MENORES
        ctk.CTkButton(frente_btn_frame, text="Adicionar", command=lambda: self.adicionar_imagem("frente"),
                      width=90, height=28, font=("Arial", 10),
                      fg_color=cor_primaria, hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF'),
                      text_color=get_contraste_texto(cor_primaria)).pack(side="left", padx=3)

        ctk.CTkButton(frente_btn_frame, text="Remover", command=lambda: self.remover_imagem("frente"),
                      width=90, height=28, font=("Arial", 10),
                      fg_color=getattr(self.sistema, 'cor_alerta', '#DC3545'),
                      hover_color=self._ajustar_hover(getattr(self.sistema, 'cor_alerta', '#DC3545')),
                      text_color=get_contraste_texto(getattr(self.sistema, 'cor_alerta', '#DC3545'))).pack(side="left",
                                                                                                           padx=3)

        # Imagem das costas - DIMINUÍDA
        costas_frame = ctk.CTkFrame(img_container, fg_color=cor_fundo, border_color=cor_borda, border_width=1)
        costas_frame.pack(side="right", fill="both", expand=True, padx=8)

        # Título COSTAS MENOR
        ctk.CTkLabel(costas_frame, text="COSTAS", font=("Arial", 11, "bold"),
                     text_color=cor_texto).pack(pady=3)

        # LABEL DA IMAGEM COSTAS - DIMINUÍDA
        self.costas_img_label = ctk.CTkLabel(costas_frame, text="Clique para adicionar imagem",
                                             width=380, height=500, corner_radius=5,
                                             fg_color=cor_secundaria,
                                             text_color=get_contraste_texto(cor_secundaria),
                                             font=("Arial", 10))
        self.costas_img_label.pack(pady=3)
        self.costas_img_label.bind("<Button-1>", lambda e: self.adicionar_imagem("costas"))

        # Frame dos botões - COMPACTO
        costas_btn_frame = ctk.CTkFrame(costas_frame, fg_color="transparent")
        costas_btn_frame.pack(pady=3)

        # Botões MENORES
        ctk.CTkButton(costas_btn_frame, text="Adicionar", command=lambda: self.adicionar_imagem("costas"),
                      width=90, height=28, font=("Arial", 10),
                      fg_color=cor_primaria, hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF'),
                      text_color=get_contraste_texto(cor_primaria)).pack(side="left", padx=3)

        ctk.CTkButton(costas_btn_frame, text="Remover", command=lambda: self.remover_imagem("costas"),
                      width=90, height=28, font=("Arial", 10),
                      fg_color=getattr(self.sistema, 'cor_alerta', '#DC3545'),
                      hover_color=self._ajustar_hover(getattr(self.sistema, 'cor_alerta', '#DC3545')),
                      text_color=get_contraste_texto(getattr(self.sistema, 'cor_alerta', '#DC3545'))).pack(side="left",
                                                                                                           padx=3)

    def _create_tecidos_tab(self):
        """Cria a aba de tecidos com botões funcionais."""
        # Título
        ctk.CTkLabel(
            self.tab_tecidos,
            text="TECIDOS UTILIZADOS",
            font=("Arial", 16, "bold"),
            text_color=getattr(self.sistema, 'cor_texto', '#000000')
        ).pack(pady=(10, 5))

        # Botões
        tecidos_btn_frame = ctk.CTkFrame(self.tab_tecidos, fg_color="transparent")
        tecidos_btn_frame.pack(fill="x", pady=5, padx=10)

        # Botões com cores dinâmicas para atender a temas claros e escuros
        _cor_btn = getattr(self.sistema, 'cor_primaria', '#007BFF')
        ctk.CTkButton(
            tecidos_btn_frame,
            text="Adicionar Tecido",
            command=self.adicionar_tecido,
            fg_color=_cor_btn,
            hover_color=self._ajustar_hover(_cor_btn),
            text_color=get_contraste_texto(_cor_btn),
            font=("Arial", 12),
            width=140,
            height=35,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            tecidos_btn_frame,
            text="Pesquisar Tecido",
            command=self.pesquisar_tecido,
            fg_color=_cor_btn,
            hover_color=self._ajustar_hover(_cor_btn),
            text_color=get_contraste_texto(_cor_btn),
            font=("Arial", 12),
            width=140,
            height=35,
        ).pack(side="left", padx=5)

        # Tabela de tecidos
        tecidos_tabela_frame = ctk.CTkFrame(self.tab_tecidos, fg_color=getattr(self.sistema, 'cor_fundo', '#FFFFFF'))
        tecidos_tabela_frame.pack(fill="both", expand=True, pady=5, padx=10)

        tecidos_colunas = ["Código", "Descrição", "Cor", "Fornecedor", "Composição", "Metros/Peça", "Valor Metro",
                           "Total"]
        self.tecidos_tabela = ttk.Treeview(tecidos_tabela_frame, columns=tecidos_colunas, show="headings", height=8)

        for col in tecidos_colunas:
            self.tecidos_tabela.heading(col, text=col)
            self.tecidos_tabela.column(col, width=80, anchor="w")

        self.tecidos_tabela.column("Descrição", width=120)
        self.tecidos_tabela.column("Composição", width=100)
        self.tecidos_tabela.column("Fornecedor", width=100)

        scroll_tecidos = ctk.CTkScrollbar(tecidos_tabela_frame, orientation="vertical",
                                          command=self.tecidos_tabela.yview)
        self.tecidos_tabela.configure(yscrollcommand=scroll_tecidos.set)
        scroll_tecidos.pack(side="right", fill="y")
        self.tecidos_tabela.pack(side="left", fill="both", expand=True)

        # Botão remover
        remover_frame = ctk.CTkFrame(self.tab_tecidos, fg_color="transparent")
        remover_frame.pack(fill="x", pady=5, padx=10)

        ctk.CTkButton(remover_frame, text="Remover Tecido", command=self.remover_tecido,
                      fg_color=getattr(self.sistema, 'cor_destaque', '#FFC107'), hover_color="#ff3333",
                      text_color=get_contraste_texto(getattr(self.sistema, "cor_primaria", "#007BFF")), font=("Arial", 12), width=140, height=35).pack(side="left", padx=5)

        # Imagens dos tecidos
        tecidos_img_frame = ctk.CTkFrame(self.tab_tecidos, fg_color=getattr(self.sistema, 'cor_fundo', '#FFFFFF'))
        tecidos_img_frame.pack(fill="x", pady=(10, 5), padx=10)

        ctk.CTkLabel(tecidos_img_frame, text="IMAGENS DOS TECIDOS", font=("Arial", 12, "bold"),
                     text_color=getattr(self.sistema, 'cor_texto', '#000000')).pack(pady=5)

        self.tecidos_img_container = ctk.CTkFrame(tecidos_img_frame, fg_color="transparent")
        self.tecidos_img_container.pack(fill="x")

        ctk.CTkButton(tecidos_img_frame, text="Adicionar Imagem", command=self.adicionar_imagem_tecido,
                      fg_color=getattr(self.sistema, 'cor_primaria', '#007BFF'),
                      hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF'), text_color="white",
                      font=("Arial", 12)).pack(pady=5)

    def _create_aviamentos_tab(self):
        """Cria a aba de aviamentos com botões funcionais."""
        # Título
        ctk.CTkLabel(
            self.tab_aviamentos,
            text="AVIAMENTOS UTILIZADOS",
            font=("Arial", 16, "bold"),
            text_color=getattr(self.sistema, 'cor_texto', '#000000')
        ).pack(pady=(10, 5))

        # Botões
        aviamentos_btn_frame = ctk.CTkFrame(self.tab_aviamentos, fg_color="transparent")
        aviamentos_btn_frame.pack(fill="x", pady=5, padx=10)

        ctk.CTkButton(aviamentos_btn_frame, text="Adicionar Aviamento", command=self.adicionar_aviamento,
                      fg_color=getattr(self.sistema, 'cor_primaria', '#007BFF'),
                      hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF'), text_color="white",
                      font=("Arial", 12), width=140, height=35).pack(side="left", padx=5)

        ctk.CTkButton(aviamentos_btn_frame, text="Pesquisar Aviamento", command=self.pesquisar_aviamento,
                      fg_color=getattr(self.sistema, 'cor_primaria', '#007BFF'),
                      hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF'), text_color="white",
                      font=("Arial", 12), width=140, height=35).pack(side="left", padx=5)

        # Tabela de aviamentos
        aviamentos_tabela_frame = ctk.CTkFrame(self.tab_aviamentos,
                                               fg_color=getattr(self.sistema, 'cor_fundo', '#FFFFFF'))
        aviamentos_tabela_frame.pack(fill="both", expand=True, pady=5, padx=10)

        aviamentos_colunas = ["Código", "Descrição", "Cor", "Fornecedor", "Quantidade", "Valor Unidade", "Total"]
        self.aviamentos_tabela = ttk.Treeview(aviamentos_tabela_frame, columns=aviamentos_colunas, show="headings",
                                              height=8)

        for col in aviamentos_colunas:
            self.aviamentos_tabela.heading(col, text=col)
            self.aviamentos_tabela.column(col, width=80, anchor="w")

        self.aviamentos_tabela.column("Descrição", width=120)
        self.aviamentos_tabela.column("Fornecedor", width=100)

        scroll_aviamentos = ctk.CTkScrollbar(aviamentos_tabela_frame, orientation="vertical",
                                             command=self.aviamentos_tabela.yview)
        self.aviamentos_tabela.configure(yscrollcommand=scroll_aviamentos.set)
        scroll_aviamentos.pack(side="right", fill="y")
        self.aviamentos_tabela.pack(side="left", fill="both", expand=True)

        # Botão remover
        remover_frame = ctk.CTkFrame(self.tab_aviamentos, fg_color="transparent")
        remover_frame.pack(fill="x", pady=5, padx=10)

        ctk.CTkButton(remover_frame, text="Remover Aviamento", command=self.remover_aviamento,
                      fg_color=getattr(self.sistema, 'cor_destaque', '#FFC107'), hover_color="#ff3333",
                      text_color=get_contraste_texto(getattr(self.sistema, "cor_primaria", "#007BFF")), font=("Arial", 12), width=140, height=35).pack(side="left", padx=5)

        # Imagens dos aviamentos
        aviamentos_img_frame = ctk.CTkFrame(self.tab_aviamentos, fg_color=getattr(self.sistema, 'cor_fundo', '#FFFFFF'))
        aviamentos_img_frame.pack(fill="x", pady=(10, 5), padx=10)

        ctk.CTkLabel(aviamentos_img_frame, text="IMAGENS DOS AVIAMENTOS", font=("Arial", 12, "bold"),
                     text_color=getattr(self.sistema, 'cor_texto', '#000000')).pack(pady=5)

        self.aviamentos_img_container = ctk.CTkFrame(aviamentos_img_frame, fg_color="transparent")
        self.aviamentos_img_container.pack(fill="x")

        ctk.CTkButton(aviamentos_img_frame, text="Adicionar Imagem", command=self.adicionar_imagem_aviamento,
                      fg_color=getattr(self.sistema, 'cor_primaria', '#007BFF'),
                      hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF'), text_color="white",
                      font=("Arial", 12)).pack(pady=5)

    def _create_outros_tab(self):
        """Cria a aba de Outros (serviços/itens)."""
        # Título
        ctk.CTkLabel(
            self.tab_outros,
            text="OUTROS ITENS / SERVIÇOS UTILIZADOS",
            font=("Arial", 16, "bold"),
            text_color=getattr(self.sistema, 'cor_texto', '#000000')
        ).pack(pady=(10, 5))

        # Botões
        btn_frame = ctk.CTkFrame(self.tab_outros, fg_color="transparent")
        btn_frame.pack(fill="x", pady=5, padx=10)

        ctk.CTkButton(btn_frame, text="Adicionar Outros serviços",
                      command=self.adicionar_outro,
                      fg_color=getattr(self.sistema, 'cor_primaria', '#007BFF'),
                      text_color=get_contraste_texto(getattr(self.sistema, "cor_primaria", "#007BFF")), font=("Arial", 12),
                      width=140, height=35).pack(side="left", padx=5)

        # Tabela
        tabela_frame = ctk.CTkFrame(self.tab_outros, fg_color=getattr(self.sistema, 'cor_fundo', '#FFFFFF'))
        tabela_frame.pack(fill="both", expand=True, pady=5, padx=10)

        cols = ["Código", "Descrição", "Cor", "Fornecedor", "Unid.", "Quantidade", "Preço", "Total"]
        self.outros_tabela = ttk.Treeview(tabela_frame, columns=cols, show="headings", height=8)
        for c in cols:
            self.outros_tabela.heading(c, text=c)
            self.outros_tabela.column(c, width=80, anchor="w")
        self.outros_tabela.column("Descrição", width=160)
        self.outros_tabela.column("Fornecedor", width=120)

        yscroll = ctk.CTkScrollbar(tabela_frame, orientation="vertical", command=self.outros_tabela.yview)
        self.outros_tabela.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")
        self.outros_tabela.pack(side="left", fill="both", expand=True)

        # Remover
        rodape = ctk.CTkFrame(self.tab_outros, fg_color="transparent")
        rodape.pack(fill="x", pady=5, padx=10)
        btn_remover = ctk.CTkButton(rodape, text="REMOVER SERVIÇOS",
                                    command=self.remover_outro,
                                    fg_color=getattr(self.sistema, 'cor_destaque', '#FFC107'),
                                    text_color=get_contraste_texto(getattr(self.sistema, "cor_primaria", "#007BFF")), font=("Arial", 12),
                                    width=140, height=35)
        btn_remover.pack(side="left", padx=5)
        btn_remover.bind("<Enter>", lambda e: btn_remover.configure(fg_color="#E53935"))
        btn_remover.bind("<Leave>",
                         lambda e: btn_remover.configure(fg_color=getattr(self.sistema, 'cor_destaque', '#FFC107')))

        # Imagens
        img_frame = ctk.CTkFrame(self.tab_outros, fg_color=getattr(self.sistema, 'cor_fundo', '#FFFFFF'))
        img_frame.pack(fill="x", pady=(10, 5), padx=10)

        ctk.CTkLabel(img_frame, text="IMAGENS DOS SERVIÇOS", font=("Arial", 12, "bold"),
                     text_color=getattr(self.sistema, 'cor_texto', '#000000')).pack(pady=5)

        self.outros_img_container = ctk.CTkFrame(img_frame, fg_color="transparent")
        self.outros_img_container.pack(fill="x")

        ctk.CTkButton(img_frame, text="Adicionar Imagem",
                      command=self.adicionar_imagem_outro,
                      fg_color=getattr(self.sistema, 'cor_primaria', '#007BFF'),
                      text_color=get_contraste_texto(getattr(self.sistema, "cor_primaria", "#007BFF")), font=("Arial", 12)).pack(pady=5)

    def _create_pesquisa_tab(self):
        """Cria a aba de pesquisa e pré-visualização de modelos."""
        # Título
        ctk.CTkLabel(
            self.tab_pesquisa,
            text="PESQUISA E PRÉ-VISUALIZAÇÃO DE MODELOS",
            font=("Arial", 16, "bold"),
            text_color=getattr(self.sistema, 'cor_texto', '#000000')
        ).pack(pady=(10, 5))

        # Frame de pesquisa
        pesquisa_frame = ctk.CTkFrame(self.tab_pesquisa, fg_color="transparent")
        pesquisa_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(pesquisa_frame, text="Pesquisar:", font=("Arial", 12)).pack(side="left", padx=5)
        self.pesquisa_entry = ctk.CTkEntry(pesquisa_frame, font=("Arial", 12), width=200)
        self.pesquisa_entry.pack(side="left", padx=5)
        ctk.CTkButton(pesquisa_frame, text="Pesquisar", command=self.pesquisar_modelos, width=80).pack(side="left",
                                                                                                       padx=5)
        ctk.CTkButton(pesquisa_frame, text="Limpar", command=self.limpar_pesquisa, width=80).pack(side="left", padx=5)

        # Tabela de resultados
        tabela_frame = ctk.CTkFrame(self.tab_pesquisa, fg_color=getattr(self.sistema, 'cor_fundo', '#FFFFFF'))
        tabela_frame.pack(fill="both", expand=True, pady=5, padx=10)

        colunas = ["Código", "Descrição", "Coleção", "Data"]
        self.tabela_modelos = ttk.Treeview(tabela_frame, columns=colunas, show="headings", selectmode="browse",
                                           height=12)

        for col in colunas:
            self.tabela_modelos.heading(col, text=col)
            self.tabela_modelos.column(col, width=100, anchor="w")

        self.tabela_modelos.column("Descrição", width=200)
        self.tabela_modelos.column("Coleção", width=150)

        scroll_tabela = ctk.CTkScrollbar(tabela_frame, orientation="vertical", command=self.tabela_modelos.yview)
        self.tabela_modelos.configure(yscrollcommand=scroll_tabela.set)
        scroll_tabela.pack(side="right", fill="y")
        self.tabela_modelos.pack(side="left", fill="both", expand=True)
        self.tabela_modelos.bind("<Double-1>", self.on_double_click_modelos)

        # Botões de ação para pesquisa
        acoes_frame = ctk.CTkFrame(self.tab_pesquisa, fg_color="transparent")
        acoes_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkButton(acoes_frame, text="Carregar Modelo", command=self.carregar_modelo_pesquisa,
                      fg_color=getattr(self.sistema, 'cor_primaria', '#007BFF'),
                      hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF'), text_color="white",
                      font=("Arial", 12)).pack(side="left", padx=5)
        ctk.CTkButton(acoes_frame, text="Gerar PDF", command=self.gerar_pdf_pesquisa,
                      fg_color=getattr(self.sistema, 'cor_primaria', '#007BFF'),
                      hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF'), text_color="white",
                      font=("Arial", 12)).pack(side="left", padx=5)
        ctk.CTkButton(acoes_frame, text="Imprimir PDF", command=self.imprimir_pdf_pesquisa,
                      fg_color=getattr(self.sistema, 'cor_primaria', '#007BFF'),
                      hover_color=getattr(self.sistema, 'cor_hover', '#E9ECEF'), text_color="white",
                      font=("Arial", 12)).pack(side="left", padx=5)

    def _create_action_buttons(self, parent):
        """Cria os botões de ação na parte inferior - VERSÃO COMPACTA."""
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent", height=35)  # Altura fixa
        btn_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)  # Menos padding
        btn_frame.pack_propagate(False)

        # Configurar colunas para alinhar os botões à direita
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=0)
        btn_frame.grid_columnconfigure(2, weight=0)
        btn_frame.grid_columnconfigure(3, weight=0)
        btn_frame.grid_columnconfigure(4, weight=0)

        # Botão Novo Modelo - MAIS COMPACTO
        # Botão Novo Modelo - MAIS COMPACTO com cores dinâmicas
        _cor_btn = getattr(self.sistema, 'cor_primaria', '#007BFF')
        ctk.CTkButton(
            btn_frame,
            text="Novo",
            command=self.novo_cadastro,
            fg_color=_cor_btn,
            hover_color=self._ajustar_hover(_cor_btn),
            text_color=get_contraste_texto(_cor_btn),
            font=("Arial", 10),  # Fonte menor
            width=70,  # Largura reduzida
            height=26  # Altura reduzida
        ).grid(row=0, column=1, padx=2, sticky="e")

        # Botão Gerar PDF - MAIS COMPACTO com cores dinâmicas
        ctk.CTkButton(
            btn_frame,
            text="PDF",
            command=self.on_click_imprimir,
            fg_color=_cor_btn,
            hover_color=self._ajustar_hover(_cor_btn),
            text_color=get_contraste_texto(_cor_btn),
            font=("Arial", 10),
            width=70,
            height=26
        ).grid(row=0, column=2, padx=2, sticky="e")

        # Botão Exportar - MAIS COMPACTO
        ctk.CTkButton(
            btn_frame,
            text="Exportar",
            command=self.exportar_cadastro,
            fg_color=getattr(self.sistema, 'cor_destaque', '#FFC107'),
            hover_color="#ff3333",
            text_color=get_contraste_texto(getattr(self.sistema, "cor_primaria", "#007BFF")),
            font=("Arial", 10),
            width=70,
            height=26
        ).grid(row=0, column=3, padx=2, sticky="e")

        # Botão Salvar (no canto inferior direito) - MAIS COMPACTO
        ctk.CTkButton(
            btn_frame,
            text="Salvar",
            command=self.salvar_cadastro,
            fg_color=getattr(self.sistema, 'cor_sucesso', '#28A745'),
            hover_color="#2ECC71",
            text_color=get_contraste_texto(getattr(self.sistema, "cor_primaria", "#007BFF")),
            font=("Arial", 10, "bold"),
            width=70,
            height=26
        ).grid(row=0, column=4, padx=2, sticky="e")

    def _initialize_data(self):
        """Inicializa dados e atualiza tabelas."""
        self.atualizar_tabela_modelos()
        self.atualizar_totais()

    # =================== MÉTODOS DE IMAGENS ===================
    def adicionar_imagem(self, tipo):
        """Adiciona uma imagem para frente ou costas do modelo."""
        file_path = filedialog.askopenfilename(
            parent=self.root,
            title=f"Selecionar imagem {tipo}",
            filetypes=[
                ("All files", "*.*"),  # Movido para primeira posição
                ("JPEG files", "*.jpg"),
                ("JPEG files", "*.jpeg"),
                ("PNG files", "*.png"),
                ("BMP files", "*.bmp"),
                ("TIFF files", "*.tiff"),
                ("TIFF files", "*.tif"),
            ],
            defaultextension="*.*"  # Adicionado para definir All files como padrão
        )
        if file_path and Image:
            try:
                self.imagens_modelo[tipo] = file_path
                self._set_label_image(tipo, file_path)
                print(f"✅ Imagem {tipo} selecionada: {file_path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível carregar a imagem:\n{str(e)}")
        elif file_path:
            messagebox.showerror("Erro", "PIL (Pillow) não está disponível para processar imagens.")

    def adicionar_imagem_tecido(self):
        """Adiciona imagens para tecidos."""
        paths = filedialog.askopenfilenames(
            parent=self.root,
            title="Selecionar imagens (Tecidos)",
            filetypes=[
                ("All files", "*.*"),  # Movido para primeira posição
                ("JPEG files", "*.jpg"),
                ("JPEG files", "*.jpeg"),
                ("PNG files", "*.png"),
                ("BMP files", "*.bmp"),
                ("TIFF files", "*.tiff"),
                ("TIFF files", "*.tif"),
                ("GIF files", "*.gif"),
            ],
            defaultextension="*.*"  # Adicionado para definir All files como padrão
        )
        if not paths:
            return

        if not hasattr(self, "imagens_tecidos") or self.imagens_tecidos is None:
            self.imagens_tecidos = []

        existentes = set(self.imagens_tecidos)
        novos = [p for p in paths if p not in existentes]
        self.imagens_tecidos.extend(novos)

        self.atualizar_imagens_tecidos()
        print(f"✅ {len(novos)} imagens de tecido adicionadas")

    def adicionar_imagem_aviamento(self):
        """Adiciona imagens para aviamentos."""
        paths = filedialog.askopenfilenames(
            parent=self.root,
            title="Selecionar imagens (Aviamentos)",
            filetypes=[
                ("All files", "*.*"),  # Movido para primeira posição
                ("JPEG files", "*.jpg"),
                ("JPEG files", "*.jpeg"),
                ("PNG files", "*.png"),
                ("BMP files", "*.bmp"),
                ("TIFF files", "*.tiff"),
                ("TIFF files", "*.tif"),
                ("GIF files", "*.gif"),
            ],
            defaultextension="*.*"  # Adicionado para definir All files como padrão
        )
        if not paths:
            return

        if not hasattr(self, "imagens_aviamentos") or self.imagens_aviamentos is None:
            self.imagens_aviamentos = []

        existentes = set(self.imagens_aviamentos)
        novos = [p for p in paths if p not in existentes]
        self.imagens_aviamentos.extend(novos)

        self.atualizar_imagens_aviamentos()
        print(f"✅ {len(novos)} imagens de aviamento adicionadas")

    def adicionar_imagem_outro(self):
        """Adiciona imagens para outros serviços."""
        paths = filedialog.askopenfilenames(
            parent=self.root,
            title="Selecionar imagens (Outros)",
            filetypes=[
                ("All files", "*.*"),  # Movido para primeira posição
                ("JPEG files", "*.jpg"),
                ("JPEG files", "*.jpeg"),
                ("PNG files", "*.png"),
                ("BMP files", "*.bmp"),
                ("TIFF files", "*.tiff"),
                ("TIFF files", "*.tif"),
                ("GIF files", "*.gif"),
            ],
            defaultextension="*.*"  # Adicionado para definir All files como padrão
        )
        if not paths:
            return

        if not hasattr(self, "imagens_outros") or self.imagens_outros is None:
            self.imagens_outros = []

        existentes = set(self.imagens_outros)
        novos = [p for p in paths if p not in existentes]
        self.imagens_outros.extend(novos)

        self.atualizar_imagens_outros()
        print(f"✅ {len(novos)} imagens de outros serviços adicionadas")

    def _safe_file_dialog(self, dialog_type="open", title="Selecionar arquivo", multiple=False, filetypes=None):
        """
        Dialog de arquivo seguro para macOS com tratamento de erros.

        Args:
            dialog_type: "open" ou "save"
            title: Título da janela
            multiple: Se permite múltipla seleção (apenas para open)
            filetypes: Lista de tuplas (descrição, padrão)

        Returns:
            Caminho(s) do arquivo ou None
        """
        if filetypes is None:
            filetypes = [
                ("All files", "*.*"),
                ("JPEG files", "*.jpg"),
                ("JPEG files", "*.jpeg"),
                ("PNG files", "*.png"),
                ("BMP files", "*.bmp"),
                ("TIFF files", "*.tiff"),
                ("TIFF files", "*.tif"),
                ("GIF files", "*.gif"),
            ]

        try:
            if dialog_type == "open":
                if multiple:
                    return filedialog.askopenfilenames(
                        parent=self.root,
                        title=title,
                        filetypes=filetypes
                    )
                else:
                    return filedialog.askopenfilename(
                        parent=self.root,
                        title=title,
                        filetypes=filetypes
                    )
            elif dialog_type == "save":
                return filedialog.asksaveasfilename(
                    parent=self.root,
                    title=title,
                    filetypes=filetypes,
                    defaultextension=".*"
                )
        except Exception as e:
            print(f"❌ Erro no file dialog: {e}")
            messagebox.showerror("Erro", f"Falha ao abrir diálogo de arquivo:\n{e}")
            return None

    def remover_imagem(self, tipo):
        """Remove a imagem do modelo (frente ou costas)."""
        try:
            print(f"🗑️ Removendo imagem {tipo}...")
            if tipo == "frente":
                self.imagens_modelo["frente"] = None
                self._safe_clear_image_reference(self.frente_img_label)
                self.frente_img_label.configure(text="Clique para adicionar imagem")
            elif tipo == "costas":
                self.imagens_modelo["costas"] = None
                self._safe_clear_image_reference(self.costas_img_label)
                self.costas_img_label.configure(text="Clique para adicionar imagem")
            print(f"✅ Imagem {tipo} removida")
        except Exception as e:
            print(f"❌ Erro ao remover imagem {tipo}: {e}")

    def remover_imagem_tecido(self, index):
        """Remove imagem de tecido pelo índice."""
        if 0 <= index < len(self.imagens_tecidos):
            self.imagens_tecidos.pop(index)
            self.atualizar_imagens_tecidos()
            self.atualizar_totais()

    def remover_imagem_aviamento(self, index):
        """Remove imagem de aviamento pelo índice."""
        if 0 <= index < len(self.imagens_aviamentos):
            self.imagens_aviamentos.pop(index)
            self.atualizar_imagens_aviamentos()
            self.atualizar_totais()

    def remover_imagem_outro(self, index):
        """Remove imagem de outro serviço pelo índice."""
        if 0 <= index < len(self.imagens_outros):
            self.imagens_outros.pop(index)
            self.atualizar_imagens_outros()
            self.atualizar_totais()

    def _set_label_image(self, tipo, imagem_path):
        """Define imagem em uma label específica de forma segura - USANDO TAMANHO DINÂMICO."""
        try:
            if not Image or not imagem_path or not os.path.exists(imagem_path):
                print(f"⚠️ Imagem {tipo} não disponível: {imagem_path}")
                self._set_label_text_only(tipo, "Clique para adicionar imagem")
                return

            label_map = {
                "frente": (self.frente_img_label, "frente_img_ref"),
                "costas": (self.costas_img_label, "costas_img_ref")
            }

            if tipo not in label_map:
                print(f"❌ Tipo de imagem desconhecido: {tipo}")
                return

            label, ref_attr = label_map[tipo]

            if not label or not hasattr(label, 'configure'):
                print(f"❌ Label {tipo} não disponível")
                return

            try:
                img = Image.open(imagem_path)

                # Obter tamanho disponível na label
                label_width = label.winfo_width()
                label_height = label.winfo_height()

                # Se não conseguir obter o tamanho real, usar tamanhos padrão DIMINUÍDOS
                if label_width < 10 or label_height < 10:
                    label_width = 380  # ALTERADO: de 400 para 380
                    label_height = 500  # ALTERADO: de 600 para 500

                # Calcular proporção mantendo aspect ratio
                img_ratio = img.width / img.height
                label_ratio = label_width / label_height

                if img_ratio > label_ratio:
                    # Imagem mais larga que o container
                    new_width = label_width
                    new_height = int(label_width / img_ratio)
                else:
                    # Imagem mais alta que o container
                    new_height = label_height
                    new_width = int(label_height * img_ratio)

                # Redimensionar mantendo qualidade
                img = img.resize((new_width, new_height), Image.LANCZOS)
                img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(new_width, new_height))

                setattr(self, ref_attr, img_ctk)
                label.configure(image=getattr(self, ref_attr), text="")

                print(f"✅ Imagem {tipo} carregada: {os.path.basename(imagem_path)} ({new_width}x{new_height})")

            except Exception as img_error:
                print(f"❌ Erro ao processar imagem {tipo}: {img_error}")
                self._set_label_text_only(tipo, "Erro ao carregar imagem")

        except Exception as e:
            print(f"❌ Erro ao carregar imagem {tipo}: {e}")
            self._set_label_text_only(tipo, "Erro ao carregar imagem")

    def _set_label_text_only(self, tipo, text):
        """Define apenas o texto da label de forma segura."""
        try:
            label_map = {
                "frente": self.frente_img_label,
                "costas": self.costas_img_label
            }

            if tipo not in label_map:
                return

            label = label_map[tipo]
            if label and hasattr(label, 'configure'):
                label.configure(text=text)
        except Exception as e:
            print(f"⚠️ Erro ao definir texto da label {tipo}: {e}")

    def _safe_clear_image_reference(self, label):
        """Limpa referências de imagem de forma segura."""
        try:
            label.configure(image=None)
            if hasattr(label, '_image_ref'):
                label._image_ref = None
        except Exception as e:
            print(f"⚠️ Erro ao limpar referência de imagem: {e}")

    def _limpeza_total_imagens(self):
        """LIMPEZA TOTAL E RADICAL das imagens - recria tudo do zero."""
        try:
            print("💥 INICIANDO LIMPEZA TOTAL DE IMAGENS...")

            # 1. LIMPEZA COMPLETA DOS DADOS
            self.imagens_modelo = {"frente": None, "costas": None}
            self.imagens_tecidos.clear()
            self.imagens_aviamentos.clear()
            self.imagens_outros.clear()

            # 2. DESTRUIÇÃO TOTAL DOS CONTAINERS DE MATERIAIS
            containers_info = [
                ('tecidos_img_container', self.tecidos_img_container),
                ('aviamentos_img_container', self.aviamentos_img_container),
                ('outros_img_container', self.outros_img_container)
            ]

            for name, container in containers_info:
                if container and hasattr(container, 'winfo_children') and container.winfo_exists():
                    try:
                        widgets = container.winfo_children()
                        for widget in widgets:
                            try:
                                widget.destroy()
                            except Exception as w_error:
                                print(f"⚠️ Erro ao destruir widget em {name}: {w_error}")
                        print(f"✅ Container {name} DESTRUÍDO ({len(widgets)} widgets)")
                    except Exception as c_error:
                        print(f"⚠️ Erro ao acessar container {name}: {c_error}")

            # 3. RECRIAÇÃO COMPLETA DAS LABELS PRINCIPAIS
            print("🔨 RECRIANDO LABELS DE IMAGEM DO ZERO...")

            # Label FRENTE - Destruir e recriar completamente
            if hasattr(self, 'frente_img_label') and self.frente_img_label:
                try:
                    parent = self.frente_img_label.master
                    self.frente_img_label.destroy()

                    self.frente_img_label = ctk.CTkLabel(
                        parent,
                        text="Clique para adicionar imagem",
                        width=400,
                        height=500,
                        corner_radius=5,
                        fg_color=getattr(self.sistema, "cor_secundaria", "#E0E0E0"),
                        text_color=get_contraste_texto(getattr(self.sistema, "cor_secundaria", "#E0E0E0")),
                        font=("Arial", 12)
                    )
                    self.frente_img_label.pack(pady=5)
                    self.frente_img_label.bind("<Button-1>", lambda e: self.adicionar_imagem("frente"))
                    print("✅ Label FRENTE recriada do ZERO")
                except Exception as e:
                    print(f"❌ ERRO ao recriar label frente: {e}")

            # Label COSTAS - Destruir e recriar completamente
            if hasattr(self, 'costas_img_label') and self.costas_img_label:
                try:
                    parent = self.costas_img_label.master
                    self.costas_img_label.destroy()

                    self.costas_img_label = ctk.CTkLabel(
                        parent,
                        text="Clique para adicionar imagem",
                        width=400,
                        height=500,
                        corner_radius=5,
                        fg_color=getattr(self.sistema, "cor_secundaria", "#E0E0E0"),
                        text_color=get_contraste_texto(getattr(self.sistema, "cor_secundaria", "#E0E0E0")),
                        font=("Arial", 12)
                    )
                    self.costas_img_label.pack(pady=5)
                    self.costas_img_label.bind("<Button-1>", lambda e: self.adicionar_imagem("costas"))
                    print("✅ Label COSTAS recriada do ZERO")
                except Exception as e:
                    print(f"❌ ERRO ao recriar label costas: {e}")

            # 4. LIMPEZA DAS REFERÊNCIAS DE IMAGEM
            if hasattr(self, 'frente_img_ref'):
                self.frente_img_ref = None
            if hasattr(self, 'costas_img_ref'):
                self.costas_img_ref = None
            print("✅ Referências de CTkImage LIMPAS")

            # 5. FORÇAR ATUALIZAÇÃO DA INTERFACE
            try:
                self.update()
                print("✅ Interface atualizada forçadamente")
            except:
                pass

            print("💥 LIMPEZA TOTAL DE IMAGENS CONCLUÍDA - TUDO RECRIADO DO ZERO!")

        except Exception as e:
            print(f"❌ ERRO CRÍTICO na limpeza total de imagens: {e}")
            import traceback
            traceback.print_exc()

    def atualizar_imagens_tecidos(self):
        """Atualiza o container de tecidos."""
        try:
            if not hasattr(self, 'tecidos_img_container') or not self.tecidos_img_container:
                return

            for w in self.tecidos_img_container.winfo_children():
                try:
                    w.destroy()
                except:
                    continue

            for i, img_path in enumerate(self.imagens_tecidos):
                if not img_path or not os.path.exists(img_path):
                    continue

                try:
                    img_frame = ctk.CTkFrame(self.tecidos_img_container, fg_color="transparent")
                    img_frame.pack(side="left", padx=5, pady=5)

                    if Image:
                        img = Image.open(img_path)
                        img.thumbnail((200, 230), Image.LANCZOS)
                        img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 230))

                        label = ctk.CTkLabel(img_frame, image=img_ctk, text="", width=200, height=230)
                        label.image_ref = img_ctk
                        label.pack()

                    ctk.CTkButton(img_frame, text="Remover",
                                  command=lambda idx=i: self.remover_imagem_tecido(idx),
                                  width=60, height=25, font=("Arial", 10)).pack(pady=2)

                except Exception as e:
                    print(f"❌ Erro ao exibir imagem de tecido {i}: {e}")
                    continue

        except Exception as e:
            print(f"❌ Erro em atualizar_imagens_tecidos: {e}")

    def atualizar_imagens_aviamentos(self):
        """Atualiza o container de aviamentos."""
        try:
            if not hasattr(self, 'aviamentos_img_container') or not self.aviamentos_img_container:
                return

            for w in self.aviamentos_img_container.winfo_children():
                try:
                    w.destroy()
                except:
                    continue

            for i, img_path in enumerate(self.imagens_aviamentos):
                if not img_path or not os.path.exists(img_path):
                    continue

                try:
                    img_frame = ctk.CTkFrame(self.aviamentos_img_container, fg_color="transparent")
                    img_frame.pack(side="left", padx=5, pady=5)

                    if Image:
                        img = Image.open(img_path)
                        img.thumbnail((200, 230), Image.LANCZOS)
                        img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 230))

                        label = ctk.CTkLabel(img_frame, image=img_ctk, text="", width=200, height=230)
                        label.image_ref = img_ctk
                        label.pack()

                    ctk.CTkButton(img_frame, text="Remover",
                                  command=lambda idx=i: self.remover_imagem_aviamento(idx),
                                  width=60, height=25, font=("Arial", 10)).pack(pady=2)

                except Exception as e:
                    print(f"❌ Erro ao exibir imagem de aviamento {i}: {e}")
                    continue

        except Exception as e:
            print(f"❌ Erro em atualizar_imagens_aviamentos: {e}")

    def atualizar_imagens_outros(self):
        """Atualiza o container de outros serviços."""
        try:
            if not hasattr(self, 'outros_img_container') or not self.outros_img_container:
                return

            for w in self.outros_img_container.winfo_children():
                try:
                    w.destroy()
                except:
                    continue

            for i, img_path in enumerate(self.imagens_outros):
                if not img_path or not os.path.exists(img_path):
                    continue

                try:
                    img_frame = ctk.CTkFrame(self.outros_img_container, fg_color="transparent")
                    img_frame.pack(side="left", padx=5, pady=5)

                    if Image:
                        img = Image.open(img_path)
                        img.thumbnail((200, 230), Image.LANCZOS)
                        img_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 230))

                        label = ctk.CTkLabel(img_frame, image=img_ctk, text="", width=200, height=230)
                        label.image_ref = img_ctk
                        label.pack()

                    ctk.CTkButton(img_frame, text="Remover",
                                  command=lambda idx=i: self.remover_imagem_outro(idx),
                                  width=60, height=25, font=("Arial", 10)).pack(pady=2)

                except Exception as e:
                    print(f"❌ Erro ao exibir imagem de outro {i}: {e}")
                    continue

        except Exception as e:
            print(f"❌ Erro em atualizar_imagens_outros: {e}")

    # =================== MÉTODOS DE DADOS PRINCIPAIS ===================
    def novo_cadastro(self):
        """Prepara a interface para um novo cadastro - LIMPEZA TOTAL."""
        try:
            print("🔄 Iniciando NOVO CADASTRO - LIMPEZA TOTAL...")

            # 1. LIMPEZA DOS CAMPOS DE TEXTO
            print("📝 Limpando campos de texto...")
            campos_entrada = [
                self.codigo_entry, self.descricao_entry, self.colecao_entry,
                self.modelista_entry, self.pilotista_entry
            ]

            for entry in campos_entrada:
                if entry and hasattr(entry, 'delete') and entry.winfo_exists():
                    try:
                        entry.delete(0, tk.END)
                    except Exception as e:
                        print(f"⚠️ Erro ao limpar entry: {e}")

            # Limpar campo de custo
            if (self.custo_entry and hasattr(self.custo_entry, 'configure')
                    and self.custo_entry.winfo_exists()):
                try:
                    self.custo_entry.configure(state="normal")
                    self.custo_entry.delete(0, tk.END)
                    self.custo_entry.insert(0, "0,00")
                    self.custo_entry.configure(state="readonly")
                except Exception as e:
                    print(f"⚠️ Erro ao limpar custo: {e}")

            # 2. RESET DAS VARIÁVEIS DE CONTROLE
            print("⚙️ Resetando variáveis de controle...")
            try:
                self.tamanho_base_var.set("M")
                self.dificuldade_var.set("Médio")
                self.pronto_prod_var.set(0)
            except Exception as e:
                print(f"⚠️ Erro ao resetar variáveis: {e}")

            # Limpa grade de tamanhos
            for tamanho in self.tamanhos:
                if tamanho in self.grade_vars:
                    try:
                        self.grade_vars[tamanho].set(0)
                    except Exception as e:
                        print(f"⚠️ Erro ao limpar grade {tamanho}: {e}")

            # 3. LIMPEZA TOTAL DOS DADOS
            print("🗑️ Limpando dados internos...")
            self.tecidos.clear()
            self.aviamentos.clear()
            self.outros.clear()
            self.imagens_tecidos.clear()
            self.imagens_aviamentos.clear()
            self.imagens_outros.clear()
            self.imagens_modelo = {"frente": None, "costas": None}
            self.cadastro_carregado_codigo = None

            # 4. LIMPEZA DAS TABELAS
            print("📊 Limpando tabelas...")
            tabelas = [
                (self.tecidos_tabela, "tecidos"),
                (self.aviamentos_tabela, "aviamentos"),
                (self.outros_tabela, "outros")
            ]

            for tv, nome in tabelas:
                if tv and hasattr(tv, 'get_children') and hasattr(tv, 'delete') and tv.winfo_exists():
                    try:
                        for iid in tv.get_children():
                            tv.delete(iid)
                    except Exception as e:
                        print(f"⚠️ Erro ao limpar tabela {nome}: {e}")

            # 5. LIMPEZA TOTAL DAS IMAGENS
            print("🖼️ LIMPEZA TOTAL DAS IMAGENS...")
            self._limpeza_total_imagens()

            # 6. ATUALIZAÇÃO DOS CONTAINERS DE IMAGENS
            print("🔄 Atualizando containers de imagens...")
            try:
                self.atualizar_imagens_tecidos()
            except Exception as e:
                print(f"⚠️ Erro ao atualizar imagens de tecidos: {e}")

            try:
                self.atualizar_imagens_aviamentos()
            except Exception as e:
                print(f"⚠️ Erro ao atualizar imagens de aviamentos: {e}")

            try:
                self.atualizar_imagens_outros()
            except Exception as e:
                print(f"⚠️ Erro ao atualizar imagens de outros: {e}")

            # 7. LIMPEZA DA PESQUISA
            print("🔍 Limpando pesquisa...")
            if (hasattr(self, 'pesquisa_entry') and self.pesquisa_entry
                    and hasattr(self.pesquisa_entry, 'delete') and self.pesquisa_entry.winfo_exists()):
                try:
                    self.pesquisa_entry.delete(0, tk.END)
                except Exception as e:
                    print(f"⚠️ Erro ao limpar pesquisa: {e}")

            # Limpa seleção na tabela de modelos
            if (hasattr(self, 'tabela_modelos') and self.tabela_modelos
                    and hasattr(self.tabela_modelos, 'selection_remove') and self.tabela_modelos.winfo_exists()):
                try:
                    selection = self.tabela_modelos.selection()
                    if selection:
                        self.tabela_modelos.selection_remove(selection)
                except Exception as e:
                    print(f"⚠️ Erro ao limpar seleção: {e}")

            # 8. CONFIGURAÇÕES FINAIS
            print("🎯 Configurações finais...")

            # Foca no campo de código
            if (self.codigo_entry and hasattr(self.codigo_entry, 'focus_set')
                    and self.codigo_entry.winfo_exists()):
                try:
                    self.codigo_entry.focus_set()
                except Exception as e:
                    print(f"⚠️ Erro ao focar no código: {e}")

            # Atualiza totais
            try:
                self.atualizar_totais()
            except Exception as e:
                print(f"⚠️ Erro ao atualizar totais: {e}")

            # Garante que estamos na aba principal
            try:
                if hasattr(self, 'tabview') and self.tabview:
                    self.tabview.set("Principal")
            except Exception as e:
                print(f"⚠️ Erro ao selecionar aba principal: {e}")

            # 9. MENSAGEM DE SUCESSO
            self._auto_message("✅ Novo Cadastro iniciado - Pronto para começar!")
            print("🎉 NOVO CADASTRO INICIADO COM SUCESSO - LIMPEZA TOTAL CONCLUÍDA!")

        except Exception as e:
            print(f"❌ ERRO CRÍTICO em novo_cadastro: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erro", f"Falha ao iniciar novo cadastro:\n{e}")

    def salvar_cadastro(self):
        """Salva ou ATUALIZA o cadastro no banco de dados."""
        try:
            codigo = (self.codigo_entry.get() or "").strip()
            if not codigo:
                messagebox.showwarning("Atenção", "Informe o CÓDIGO do modelo antes de salvar.", parent=self.root)
                return

            # Verificar se é um NOVO cadastro ou ATUALIZAÇÃO
            schema = db.get_schema()
            with db.get_conn_cursor() as (conn, cur):
                # Verificar se o código já existe
                cur.execute(
                    f"SELECT id FROM {schema}.cadastro_modelos_cabecalho WHERE codigo=%s",
                    (codigo,)
                )
                existing = cur.fetchone()

                if existing:
                    # MODE: ATUALIZAÇÃO de cadastro existente
                    cadastro_id = existing["id"]
                    print(f"🔄 ATUALIZANDO cadastro existente: {codigo} (ID: {cadastro_id})")

                    # ATUALIZAR CABEÇALHO
                    cur.execute(
                        f"""
                        UPDATE {schema}.cadastro_modelos_cabecalho 
                        SET descricao=%s, colecao=%s, tamanho_base=%s, dificuldade=%s, 
                            modelista=%s, pilotista=%s, pronto_producao=%s, grade_disponivel=%s,
                            custo_total=%s, data_atualizacao=NOW()
                        WHERE codigo=%s
                        """,
                        (
                            self.descricao_entry.get().strip(),
                            self.colecao_entry.get().strip(),
                            self.tamanho_base_var.get(),
                            self.dificuldade_var.get(),
                            self.modelista_entry.get().strip(),
                            self.pilotista_entry.get().strip(),
                            bool(self.pronto_prod_var.get()),
                            ",".join([t for t in self.tamanhos if self.grade_vars[t].get() == 1]),
                            formatar_valor(self.custo_entry.get()),
                            codigo
                        )
                    )

                else:
                    # MODE: NOVO cadastro
                    print(f"🆕 CRIANDO novo cadastro: {codigo}")
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.cadastro_modelos_cabecalho 
                        (codigo, descricao, colecao, tamanho_base, dificuldade, modelista, 
                         pilotista, pronto_producao, grade_disponivel, custo_total)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            codigo,
                            self.descricao_entry.get().strip(),
                            self.colecao_entry.get().strip(),
                            self.tamanho_base_var.get(),
                            self.dificuldade_var.get(),
                            self.modelista_entry.get().strip(),
                            self.pilotista_entry.get().strip(),
                            bool(self.pronto_prod_var.get()),
                            ",".join([t for t in self.tamanhos if self.grade_vars[t].get() == 1]),
                            formatar_valor(self.custo_entry.get())
                        )
                    )

                    # Buscar o ID do novo cadastro
                    cur.execute(
                        f"SELECT id FROM {schema}.cadastro_modelos_cabecalho WHERE codigo=%s",
                        (codigo,)
                    )
                    result = cur.fetchone()
                    cadastro_id = result["id"] if result else None

                if not cadastro_id:
                    raise Exception("Falha ao obter ID do cadastro")

                # LIMPAR DADOS ANTIGOS antes de salvar os novos (para atualização)
                print(f"🗑️ Limpando dados antigos para {codigo}...")
                for tabela in ['cadastro_modelos_tecidos', 'cadastro_modelos_aviamentos',
                               'cadastro_modelos_outros_servicos', 'cadastro_modelos_imagens']:
                    cur.execute(
                        f"DELETE FROM {schema}.{tabela} WHERE codigo_modelo=%s",
                        (codigo,)
                    )

                # SALVAR TECIDOS (atualizados)
                print(f"💾 Salvando {len(self.tecidos)} tecidos...")
                for tecido in self.tecidos:
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.cadastro_modelos_tecidos 
                        (codigo_modelo, cadastro_id, codigo_tecido, descricao, cor, fornecedor, 
                         composicao, metros_peca, valor_metro, valor_total)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            codigo, cadastro_id,
                            tecido.get("Código", ""),
                            tecido.get("Descrição", ""),
                            tecido.get("Cor", ""),
                            tecido.get("Fornecedor", ""),
                            tecido.get("Composição", ""),
                            formatar_valor(tecido.get("Metros/Peça", "0")),
                            formatar_valor(tecido.get("Valor Metro", "0")),
                            formatar_valor(tecido.get("valor_total", "0"))
                        )
                    )

                # SALVAR AVIAMENTOS (atualizados)
                print(f"💾 Salvando {len(self.aviamentos)} aviamentos...")
                for aviamento in self.aviamentos:
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.cadastro_modelos_aviamentos 
                        (codigo_modelo, cadastro_id, codigo_aviamento, descricao, cor, fornecedor, 
                         quantidade, valor_unidade, valor_total)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            codigo, cadastro_id,
                            aviamento.get("Código", ""),
                            aviamento.get("Descrição", ""),
                            aviamento.get("Cor", ""),
                            aviamento.get("Fornecedor", ""),
                            formatar_valor(aviamento.get("Quantidade", "0")),
                            formatar_valor(aviamento.get("Valor Unidade", "0")),
                            formatar_valor(aviamento.get("valor_total", "0"))
                        )
                    )

                # SALVAR OUTROS SERVIÇOS (atualizados)
                print(f"💾 Salvando {len(self.outros)} outros serviços...")
                for outro in self.outros:
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.cadastro_modelos_outros_servicos 
                        (codigo_modelo, cadastro_id, codigo_servico, descricao, tipo_servico, fornecedor, 
                         unidade, quantidade, valor_unidade, valor_total, observacoes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            codigo, cadastro_id,
                            outro.get("Código", ""),
                            outro.get("Descrição", ""),
                            "Outro Serviço",
                            outro.get("Fornecedor", ""),
                            outro.get("Unid.", ""),
                            formatar_valor(outro.get("Quantidade", "0")),
                            formatar_valor(outro.get("Preço", "0")),
                            formatar_valor(outro.get("valor_total", "0")),
                            ""
                        )
                    )

                # SALVAR IMAGENS (atualizadas)
                print(f"🖼️ Salvando informações de imagens no banco...")

                # Imagens do modelo (frente e costas)
                for tipo_imagem in ['frente', 'costas']:
                    caminho = self.imagens_modelo.get(tipo_imagem)
                    if caminho and os.path.exists(caminho):
                        cur.execute(
                            f"""
                            INSERT INTO {schema}.cadastro_modelos_imagens 
                            (codigo_modelo, cadastro_id, tipo_imagem, caminho_imagem, descricao)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (codigo, cadastro_id, tipo_imagem, caminho, f"Imagem {tipo_imagem} do modelo")
                        )

                # Imagens de tecidos
                for i, caminho in enumerate(self.imagens_tecidos):
                    if caminho and os.path.exists(caminho):
                        cur.execute(
                            f"""
                            INSERT INTO {schema}.cadastro_modelos_imagens 
                            (codigo_modelo, cadastro_id, tipo_imagem, caminho_imagem, descricao)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (codigo, cadastro_id, f"tecido_{i}", caminho, f"Imagem tecido {i}")
                        )

                # Imagens de aviamentos
                for i, caminho in enumerate(self.imagens_aviamentos):
                    if caminho and os.path.exists(caminho):
                        cur.execute(
                            f"""
                            INSERT INTO {schema}.cadastro_modelos_imagens 
                            (codigo_modelo, cadastro_id, tipo_imagem, caminho_imagem, descricao)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (codigo, cadastro_id, f"aviamento_{i}", caminho, f"Imagem aviamento {i}")
                        )

                # Imagens de outros
                for i, caminho in enumerate(self.imagens_outros):
                    if caminho and os.path.exists(caminho):
                        cur.execute(
                            f"""
                            INSERT INTO {schema}.cadastro_modelos_imagens 
                            (codigo_modelo, cadastro_id, tipo_imagem, caminho_imagem, descricao)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (codigo, cadastro_id, f"outro_{i}", caminho, f"Imagem outro {i}")
                        )

                # Commit de todas as operações
                conn.commit()

            # SALVAR IMAGENS EM PASTAS (APENAS AS MODIFICADAS)
            print("💾 Iniciando salvamento seletivo de imagens...")
            if self.salvar_imagens_em_pastas(codigo):
                print("✅ Apenas imagens modificadas salvas com sucesso")
            else:
                print("ℹ️ Nenhuma imagem modificada para salvar - mantendo as existentes")

            # Atualizar lista de modelos
            self.atualizar_tabela_modelos()

            # Mensagem de sucesso
            if existing:
                self._auto_message(f"✅ Modelo '{codigo}' ATUALIZADO com sucesso!", duracao=1600)
                print(f"🎯 Modelo {codigo} atualizado - imagens preservadas conforme modificações")
            else:
                self._auto_message(f"✅ Modelo '{codigo}' SALVO com sucesso!", duracao=1600)
                print(f"🎯 Novo modelo {codigo} criado com todas as imagens")

            self.cadastro_carregado_codigo = codigo

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar/atualizar cadastro:\n{e}")
            print(f"❌ Erro detalhado ao salvar: {e}")
            import traceback
            traceback.print_exc()

    def _remover_imagens_antigas(self, codigo, tipos_imagens=None):
        """Remove apenas as imagens antigas específicas que serão atualizadas."""
        try:
            pasta_banco = "BANCO_DE_DADOS"
            imagens_removidas = 0

            print(f"🗑️ Removendo imagens antigas específicas de {codigo}...")
            print(f"📝 Tipos a verificar: {tipos_imagens}")

            pastas_map = {
                "frente": "IMAGENS_FRENTE_COSTAS",
                "costas": "IMAGENS_FRENTE_COSTAS",
                "tecidos": "IMAGENS_TECIDOS",
                "aviamentos": "IMAGENS_AVIAMENTOS",
                "outros": "IMAGENS_OUTROS"
            }

            for tipo, pasta_nome in pastas_map.items():
                # Se tipos_imagens foi especificado, remove apenas esses tipos
                if tipos_imagens and tipo not in tipos_imagens:
                    continue

                pasta_path = os.path.join(pasta_banco, pasta_nome)
                if os.path.exists(pasta_path):
                    for fname in os.listdir(pasta_path):
                        # Remove apenas arquivos do código específico e tipo específico
                        if tipo in ["frente", "costas"]:
                            if fname.startswith(f"{codigo}_{tipo}"):
                                caminho_completo = os.path.join(pasta_path, fname)
                                try:
                                    os.remove(caminho_completo)
                                    imagens_removidas += 1
                                    print(f"🗑️ Imagem {tipo} removida: {fname}")
                                except Exception as e:
                                    print(f"⚠️ Erro ao remover {fname}: {e}")

                        elif tipo == "tecidos":
                            if fname.startswith(f"{codigo}_tecido_"):
                                caminho_completo = os.path.join(pasta_path, fname)
                                try:
                                    os.remove(caminho_completo)
                                    imagens_removidas += 1
                                    print(f"🗑️ Imagem tecido removida: {fname}")
                                except Exception as e:
                                    print(f"⚠️ Erro ao remover {fname}: {e}")

                        elif tipo == "aviamentos":
                            if fname.startswith(f"{codigo}_aviamento_"):
                                caminho_completo = os.path.join(pasta_path, fname)
                                try:
                                    os.remove(caminho_completo)
                                    imagens_removidas += 1
                                    print(f"🗑️ Imagem aviamento removida: {fname}")
                                except Exception as e:
                                    print(f"⚠️ Erro ao remover {fname}: {e}")

                        elif tipo == "outros":
                            if fname.startswith(f"{codigo}_outro_"):
                                caminho_completo = os.path.join(pasta_path, fname)
                                try:
                                    os.remove(caminho_completo)
                                    imagens_removidas += 1
                                    print(f"🗑️ Imagem outro removida: {fname}")
                                except Exception as e:
                                    print(f"⚠️ Erro ao remover {fname}: {e}")

            print(f"✅ {imagens_removidas} imagens antigas específicas removidas")

        except Exception as e:
            print(f"❌ Erro ao remover imagens antigas específicas: {e}")

    def salvar_imagens_em_pastas(self, codigo):
        """Salva APENAS as imagens que foram modificadas, mantendo as demais."""
        try:
            pasta_banco = "BANCO_DE_DADOS"
            imagens_salvas = 0
            tipos_atualizados = []

            print(f"💾 Salvando APENAS imagens modificadas para {codigo}...")

            # 1. IDENTIFICAR QUAIS TIPOS DE IMAGENS FORAM MODIFICADOS
            print("🔍 Identificando imagens modificadas...")

            # Verificar imagens do modelo (frente/costas)
            for tipo in ['frente', 'costas']:
                caminho_atual = self.imagens_modelo.get(tipo)
                if caminho_atual and os.path.exists(caminho_atual):
                    pasta_fc = os.path.join(pasta_banco, "IMAGENS_FRENTE_COSTAS")
                    if not caminho_atual.startswith(pasta_fc):
                        tipos_atualizados.append(tipo)
                        print(f"📸 Imagem {tipo} MODIFICADA: {os.path.basename(caminho_atual)}")

            # Verificar imagens de tecidos
            if self.imagens_tecidos:
                pasta_tecidos = os.path.join(pasta_banco, "IMAGENS_TECIDOS")
                for i, caminho in enumerate(self.imagens_tecidos):
                    if caminho and os.path.exists(caminho) and not caminho.startswith(pasta_tecidos):
                        if "tecidos" not in tipos_atualizados:
                            tipos_atualizados.append("tecidos")
                        print(f"📸 Imagem tecido {i} MODIFICADA: {os.path.basename(caminho)}")

            # Verificar imagens de aviamentos
            if self.imagens_aviamentos:
                pasta_aviamentos = os.path.join(pasta_banco, "IMAGENS_AVIAMENTOS")
                for i, caminho in enumerate(self.imagens_aviamentos):
                    if caminho and os.path.exists(caminho) and not caminho.startswith(pasta_aviamentos):
                        if "aviamentos" not in tipos_atualizados:
                            tipos_atualizados.append("aviamentos")
                        print(f"📸 Imagem aviamento {i} MODIFICADA: {os.path.basename(caminho)}")

            # Verificar imagens de outros
            if self.imagens_outros:
                pasta_outros = os.path.join(pasta_banco, "IMAGENS_OUTROS")
                for i, caminho in enumerate(self.imagens_outros):
                    if caminho and os.path.exists(caminho) and not caminho.startswith(pasta_outros):
                        if "outros" not in tipos_atualizados:
                            tipos_atualizados.append("outros")
                        print(f"📸 Imagem outro {i} MODIFICADA: {os.path.basename(caminho)}")

            print(f"🎯 Tipos de imagens a atualizar: {tipos_atualizados}")

            # 2. REMOVER APENAS AS IMAGENS DOS TIPOS MODIFICADOS
            if tipos_atualizados:
                self._remover_imagens_antigas(codigo, tipos_atualizados)
            else:
                print("ℹ️ Nenhuma imagem modificada para remover")

            # 3. SALVAR APENAS AS IMAGENS MODIFICADAS

            # Imagens do modelo (frente e costas)
            pasta_fc = os.path.join(pasta_banco, "IMAGENS_FRENTE_COSTAS")
            os.makedirs(pasta_fc, exist_ok=True)

            for tipo in ['frente', 'costas']:
                src = self.imagens_modelo.get(tipo)
                if src and os.path.exists(src):
                    # Salvar apenas se for modificada
                    if tipo in tipos_atualizados or not src.startswith(pasta_fc):
                        extensao = os.path.splitext(src)[1] or '.jpg'
                        dest_nome = f"{codigo}_{tipo}{extensao}"
                        dest_path = os.path.join(pasta_fc, dest_nome)

                        shutil.copy2(src, dest_path)
                        self.imagens_modelo[tipo] = dest_path
                        imagens_salvas += 1
                        print(f"✅ Imagem {tipo} SALVA: {dest_nome}")
                    else:
                        print(f"ℹ️ Imagem {tipo} já salva: {os.path.basename(src)}")

            # Imagens de tecidos (APENAS se houver modificações)
            pasta_tecidos = os.path.join(pasta_banco, "IMAGENS_TECIDOS")
            os.makedirs(pasta_tecidos, exist_ok=True)

            if "tecidos" in tipos_atualizados or self.imagens_tecidos:
                for i, src in enumerate(self.imagens_tecidos):
                    if src and os.path.exists(src):
                        if not src.startswith(pasta_tecidos):  # É uma imagem nova
                            extensao = os.path.splitext(src)[1] or '.jpg'
                            dest_nome = f"{codigo}_tecido_{i}{extensao}"
                            dest_path = os.path.join(pasta_tecidos, dest_nome)

                            shutil.copy2(src, dest_path)
                            self.imagens_tecidos[i] = dest_path
                            imagens_salvas += 1
                            print(f"✅ Imagem tecido {i} SALVA: {dest_nome}")
                        else:
                            print(f"ℹ️ Imagem tecido {i} já salva: {os.path.basename(src)}")
            else:
                print("ℹ️ Nenhuma imagem de tecidos para salvar")

            # Imagens de aviamentos (APENAS se houver modificações)
            pasta_aviamentos = os.path.join(pasta_banco, "IMAGENS_AVIAMENTOS")
            os.makedirs(pasta_aviamentos, exist_ok=True)

            if "aviamentos" in tipos_atualizados or self.imagens_aviamentos:
                for i, src in enumerate(self.imagens_aviamentos):
                    if src and os.path.exists(src):
                        if not src.startswith(pasta_aviamentos):  # É uma imagem nova
                            extensao = os.path.splitext(src)[1] or '.jpg'
                            dest_nome = f"{codigo}_aviamento_{i}{extensao}"
                            dest_path = os.path.join(pasta_aviamentos, dest_nome)

                            shutil.copy2(src, dest_path)
                            self.imagens_aviamentos[i] = dest_path
                            imagens_salvas += 1
                            print(f"✅ Imagem aviamento {i} SALVA: {dest_nome}")
                        else:
                            print(f"ℹ️ Imagem aviamento {i} já salva: {os.path.basename(src)}")
            else:
                print("ℹ️ Nenhuma imagem de aviamentos para salvar")

            # Imagens de outros (APENAS se houver modificações)
            pasta_outros = os.path.join(pasta_banco, "IMAGENS_OUTROS")
            os.makedirs(pasta_outros, exist_ok=True)

            if "outros" in tipos_atualizados or self.imagens_outros:
                for i, src in enumerate(self.imagens_outros):
                    if src and os.path.exists(src):
                        if not src.startswith(pasta_outros):  # É uma imagem nova
                            extensao = os.path.splitext(src)[1] or '.jpg'
                            dest_nome = f"{codigo}_outro_{i}{extensao}"
                            dest_path = os.path.join(pasta_outros, dest_nome)

                            shutil.copy2(src, dest_path)
                            self.imagens_outros[i] = dest_path
                            imagens_salvas += 1
                            print(f"✅ Imagem outro {i} SALVA: {dest_nome}")
                        else:
                            print(f"ℹ️ Imagem outro {i} já salva: {os.path.basename(src)}")
            else:
                print("ℹ️ Nenhuma imagem de outros para salvar")

            print(f"✅ Total de {imagens_salvas} imagens processadas para o modelo {codigo}")
            return imagens_salvas > 0

        except Exception as e:
            print(f"❌ Erro ao salvar imagens seletivamente: {e}")
            import traceback
            traceback.print_exc()
            return False

    def carregar_cadastro(self, codigo):
        """Carrega um cadastro existente do banco de dados para EDIÇÃO."""
        try:
            # Garante que sempre vamos trabalhar com STRING
            codigo_str = str(codigo).strip()
            if not codigo_str:
                messagebox.showwarning("Aviso", "Código inválido para carregar o cadastro!")
                return

            print(f"🔍 Carregando modelo {codigo_str} para EDIÇÃO... "
                  f"(tipo original: {type(codigo).__name__})")

            schema = db.get_schema()

            # Buscar cabeçalho
            hdr = db.fetch_one(
                f"SELECT * FROM {schema}.cadastro_modelos_cabecalho WHERE codigo=%s",
                (codigo_str,)
            )

            if not hdr:
                messagebox.showwarning("Aviso", "Cadastro não encontrado!")
                return

            # LIMPAR dados atuais antes de carregar
            self.novo_cadastro()

            # Preenche campos básicos
            self.codigo_entry.insert(0, hdr.get("codigo", ""))
            self.descricao_entry.insert(0, hdr.get("descricao", ""))
            self.colecao_entry.insert(0, hdr.get("colecao", ""))
            self.modelista_entry.insert(0, hdr.get("modelista", ""))
            self.pilotista_entry.insert(0, hdr.get("pilotista", ""))

            # Configurar variáveis
            self.tamanho_base_var.set(hdr.get("tamanho_base", "M"))
            self.dificuldade_var.set(hdr.get("dificuldade", "Médio"))
            self.pronto_prod_var.set(1 if hdr.get("pronto_producao") else 0)

            # Custo total, se existir na tabela
            if "custo_total" in hdr:
                try:
                    self.custo_entry.configure(state="normal")
                    self.custo_entry.delete(0, tk.END)
                    self.custo_entry.insert(0, formatar_para_exibicao(hdr.get("custo_total", 0)))
                    self.custo_entry.configure(state="readonly")
                except Exception as e:
                    print(f"⚠️ Erro ao aplicar custo_total no entry: {e}")

            # Configurar grade disponível
            grade_str = hdr.get("grade_disponivel", "")
            if grade_str:
                tamanhos_grade = [t.strip() for t in grade_str.split(",")]
                for tamanho in self.tamanhos:
                    self.grade_vars[tamanho].set(1 if tamanho in tamanhos_grade else 0)

            # Carregar tecidos
            tecidos_db = db.fetch_all(
                f"SELECT * FROM {schema}.cadastro_modelos_tecidos "
                f"WHERE codigo_modelo=%s ORDER BY id",
                (codigo_str,)
            )
            self.tecidos.clear()
            for tecido in tecidos_db:
                self.tecidos.append({
                    "Código": tecido.get("codigo_tecido", ""),
                    "Descrição": tecido.get("descricao", ""),
                    "Cor": tecido.get("cor", ""),
                    "Fornecedor": tecido.get("fornecedor", ""),
                    "Composição": tecido.get("composicao", ""),
                    "Metros/Peça": formatar_para_exibicao(tecido.get("metros_peca", 0)),
                    "Valor Metro": formatar_para_exibicao(tecido.get("valor_metro", 0)),
                    "valor_total": formatar_para_exibicao(tecido.get("valor_total", 0))
                })

            # Carregar aviamentos
            aviamentos_db = db.fetch_all(
                f"SELECT * FROM {schema}.cadastro_modelos_aviamentos "
                f"WHERE codigo_modelo=%s ORDER BY id",
                (codigo_str,)
            )
            self.aviamentos.clear()
            for aviamento in aviamentos_db:
                self.aviamentos.append({
                    "Código": aviamento.get("codigo_aviamento", ""),
                    "Descrição": aviamento.get("descricao", ""),
                    "Cor": aviamento.get("cor", ""),
                    "Fornecedor": aviamento.get("fornecedor", ""),
                    "Quantidade": formatar_para_exibicao(aviamento.get("quantidade", 0)),
                    "Valor Unidade": formatar_para_exibicao(aviamento.get("valor_unidade", 0)),
                    "valor_total": formatar_para_exibicao(aviamento.get("valor_total", 0))
                })

            # Carregar outros serviços
            outros_db = db.fetch_all(
                f"SELECT * FROM {schema}.cadastro_modelos_outros_servicos "
                f"WHERE codigo_modelo=%s ORDER BY id",
                (codigo_str,)
            )
            self.outros.clear()
            for outro in outros_db:
                self.outros.append({
                    "Código": outro.get("codigo_servico", ""),
                    "Descrição": outro.get("descricao", ""),
                    "Fornecedor": outro.get("fornecedor", ""),
                    "Unid.": outro.get("unidade", ""),
                    "Quantidade": formatar_para_exibicao(outro.get("quantidade", 0)),
                    "Preço": formatar_para_exibicao(outro.get("valor_unidade", 0)),
                    "valor_total": formatar_para_exibicao(outro.get("valor_total", 0))
                })

            # Atualizar tabelas e totais
            self.atualizar_tabela_tecidos()
            self.atualizar_tabela_aviamentos()
            self.atualizar_tabela_outros()
            self.atualizar_totais()

            # Carregar imagens
            self.carregar_imagens_de_pastas(codigo_str)

            self._auto_message(f"✅ Modelo '{codigo_str}' carregado para EDIÇÃO!", duracao=2000)
            self.cadastro_carregado_codigo = codigo_str

            print(f"🎯 Modelo {codigo_str} pronto para EDIÇÃO - pode adicionar/remover itens e salvar para ATUALIZAR")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar cadastro:\n{e}")
            print(f"❌ Erro detalhado ao carregar: {e}")

    def carregar_imagens_de_pastas(self, codigo):
        """Carrega TODAS as imagens salvas para o modelo."""
        try:
            pasta_banco = "BANCO_DE_DADOS"

            # 1. Carregar imagens do modelo (frente e costas)
            pasta_fc = os.path.join(pasta_banco, "IMAGENS_FRENTE_COSTAS")
            if os.path.exists(pasta_fc):
                for fname in os.listdir(pasta_fc):
                    if fname.startswith(f"{codigo}_frente"):
                        caminho_completo = os.path.join(pasta_fc, fname)
                        self.imagens_modelo["frente"] = caminho_completo
                        print(f"✅ Imagem frente carregada: {fname}")

                    elif fname.startswith(f"{codigo}_costas"):
                        caminho_completo = os.path.join(pasta_fc, fname)
                        self.imagens_modelo["costas"] = caminho_completo
                        print(f"✅ Imagem costas carregada: {fname}")

            # 2. Carregar imagens de tecidos
            pasta_tecidos = os.path.join(pasta_banco, "IMAGENS_TECIDOS")
            self.imagens_tecidos = []  # Limpar lista antes de carregar
            if os.path.exists(pasta_tecidos):
                for fname in os.listdir(pasta_tecidos):
                    if fname.startswith(f"{codigo}_tecido_"):
                        caminho_completo = os.path.join(pasta_tecidos, fname)
                        self.imagens_tecidos.append(caminho_completo)
                        print(f"✅ Imagem tecido carregada: {fname}")

            # 3. Carregar imagens de aviamentos
            pasta_aviamentos = os.path.join(pasta_banco, "IMAGENS_AVIAMENTOS")
            self.imagens_aviamentos = []  # Limpar lista antes de carregar
            if os.path.exists(pasta_aviamentos):
                for fname in os.listdir(pasta_aviamentos):
                    if fname.startswith(f"{codigo}_aviamento_"):
                        caminho_completo = os.path.join(pasta_aviamentos, fname)
                        self.imagens_aviamentos.append(caminho_completo)
                        print(f"✅ Imagem aviamento carregada: {fname}")

            # 4. Carregar imagens de outros
            pasta_outros = os.path.join(pasta_banco, "IMAGENS_OUTROS")
            self.imagens_outros = []  # Limpar lista antes de carregar
            if os.path.exists(pasta_outros):
                for fname in os.listdir(pasta_outros):
                    if fname.startswith(f"{codigo}_outro_"):
                        caminho_completo = os.path.join(pasta_outros, fname)
                        self.imagens_outros.append(caminho_completo)
                        print(f"✅ Imagem outro carregada: {fname}")

            # 5. Atualizar interface gráfica
            self._atualizar_interface_apos_carregamento()

            print(f"✅ Todas as imagens carregadas para o modelo {codigo}")

        except Exception as e:
            print(f"❌ Erro ao carregar imagens: {e}")
            import traceback
            traceback.print_exc()

    def _atualizar_interface_apos_carregamento(self):
        """Atualiza todos os elementos visuais após carregar dados."""
        try:
            # Atualizar imagens do modelo (frente e costas)
            for tipo in ['frente', 'costas']:
                if self.imagens_modelo[tipo] and os.path.exists(self.imagens_modelo[tipo]):
                    self._set_label_image(tipo, self.imagens_modelo[tipo])
                else:
                    self._set_label_text_only(tipo, "Clique para adicionar imagem")

            # Atualizar miniaturas dos materiais
            self.atualizar_imagens_tecidos()
            self.atualizar_imagens_aviamentos()
            self.atualizar_imagens_outros()

            print("✅ Interface atualizada com sucesso")

        except Exception as e:
            print(f"❌ Erro ao atualizar interface: {e}")

    # =================== MÉTODOS DE TECIDOS ===================
    def pesquisar_tecido(self):
        """Pesquisa tecidos no estoque_tecidos."""
        # Usar diálogo customizado para entrada de termo, centralizado e com tema aplicado
        termo = self._input_dialogo(
            "Pesquisar Tecido",
            "Digite parte de código, descrição, cor, fornecedor ou composição:",
        )
        if not termo or not str(termo).strip():
            return

        termo = f"%{termo.strip()}%"

        try:
            rows = db.fetch_all(
                """
                SELECT 
                    codigo,
                    descricao, 
                    cor, 
                    fornecedor, 
                    composicao, 
                    valor_metro,
                    metros as metros_estoque
                FROM opera.estoque_tecidos
                WHERE (codigo ILIKE %s OR descricao ILIKE %s OR cor ILIKE %s 
                       OR fornecedor ILIKE %s OR composicao ILIKE %s)
                ORDER BY descricao
                """,
                (termo, termo, termo, termo, termo),
            )

            print(f"🔍 DEBUG pesquisa_tecido - {len(rows)} resultados")
            for i, row in enumerate(rows):
                print(f"  Resultado {i}: {row}")

            if not rows:
                messagebox.showinfo("Pesquisa", "Nenhum tecido encontrado.", parent=self.root)
                return

            self._mostrar_resultado_pesquisa(rows, "Tecidos", self.adicionar_tecido)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro na pesquisa de tecidos:\n{e}", parent=self.root)

    def adicionar_tecido(self, prefill=None):
        """Adiciona um tecido ao cadastro. Aceita 'prefill' vindo da pesquisa."""
        prefill = prefill or {}

        # Cores do tema (garante contraste em temas claros e escuros)
        cor_fundo = getattr(self.sistema, 'cor_fundo', '#F5F5F5')
        cor_primaria = getattr(self.sistema, 'cor_primaria', '#007BFF')
        cor_texto = getattr(self.sistema, 'cor_texto', '#000000')
        cor_sucesso = getattr(self.sistema, 'cor_sucesso', '#28A745')
        cor_destaque = getattr(self.sistema, 'cor_destaque', '#6C757D')

        # Hovers ajustados automaticamente para a cor base
        hover_primaria = ajustar_hover(cor_primaria)
        hover_sucesso = ajustar_hover(cor_sucesso)
        hover_destaque = ajustar_hover(cor_destaque)

        dialog = ctk.CTkToplevel(master=self.root)
        dialog.transient(self.root)
        dialog.grab_set()
        centralizar_janela(dialog, 450, 550)
        dialog.title("Adicionar Tecido")
        dialog.resizable(False, False)
        dialog.configure(fg_color=cor_fundo)

        # Frame principal
        main_frame = ctk.CTkFrame(dialog, fg_color=cor_fundo)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        campos = [
            ("Código", ""),
            ("Descrição", ""),
            ("Cor", ""),
            ("Fornecedor", ""),
            ("Composição", ""),
            ("Metros/Peça", ""),
            ("Valor Metro", ""),
            ("valor_total", "0,00"),
        ]
        entries = {}

        # Preencher valores iniciais (exceto Metros/Peça)
        for i, (rotulo, default) in enumerate(campos):
            label = ctk.CTkLabel(
                main_frame,
                text=rotulo + ":",
                font=("Arial", 12, "bold"),
                text_color=cor_texto,  # usa cor de texto do tema
            )
            label.grid(row=i, column=0, padx=10, pady=8, sticky="e")

            entry = ctk.CTkEntry(main_frame, font=("Arial", 12), width=250)

            if rotulo == "Metros/Peça":
                inicial = ""
            else:
                inicial = prefill.get(rotulo, default)

            entry.insert(0, inicial)

            if rotulo == "valor_total":
                entry.configure(state="readonly", fg_color="#f0f0f0")
            elif rotulo in ["Metros/Peça", "Valor Metro"]:
                entry.configure(
                    validate="key",
                    validatecommand=(dialog.register(validar_entrada_monetaria), "%P"),
                )

            entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
            entries[rotulo] = entry

        def calcular_total(event=None):
            """Calcula o total automaticamente."""
            try:
                metros_texto = entries["Metros/Peça"].get().strip()
                valor_metro_texto = entries["Valor Metro"].get().strip()

                if not metros_texto or not valor_metro_texto:
                    total = 0.0
                else:
                    metros = formatar_valor(metros_texto)
                    valor_metro = formatar_valor(valor_metro_texto)
                    total = metros * valor_metro

                entries["valor_total"].configure(state="normal")
                entries["valor_total"].delete(0, tk.END)
                entries["valor_total"].insert(0, formatar_para_exibicao(total))
                entries["valor_total"].configure(state="readonly")
                return True

            except Exception as e:
                print(f"Erro no cálculo: {e}")
                return False

        entries["Metros/Peça"].bind("<KeyRelease>", calcular_total)
        entries["Valor Metro"].bind("<KeyRelease>", calcular_total)

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=len(campos) + 1, column=0, columnspan=2, pady=20)

        ctk.CTkButton(
            button_frame,
            text="↻ Calcular Total",
            command=calcular_total,
            fg_color=cor_primaria,
            hover_color=hover_primaria,
            text_color=get_contraste_texto(cor_primaria),  # contraste dinâmico
            font=("Arial", 11, "bold"),
            width=120,
            height=35,
        ).pack(side="left", padx=10)

        def salvar():
            if not calcular_total():
                messagebox.showwarning(
                    "Atenção",
                    "Erro no cálculo do total. Verifique os valores.",
                    parent=dialog,
                )
                return

            codigo = entries["Código"].get().strip()
            descricao = entries["Descrição"].get().strip()
            metros = entries["Metros/Peça"].get().strip()

            if not codigo:
                messagebox.showwarning(
                    "Atenção",
                    "O campo Código é obrigatório.",
                    parent=dialog,
                )
                entries["Código"].focus_set()
                return

            if not descricao:
                messagebox.showwarning(
                    "Atenção",
                    "O campo Descrição é obrigatório.",
                    parent=dialog,
                )
                entries["Descrição"].focus_set()
                return

            if not metros or formatar_valor(metros) == 0:
                messagebox.showwarning(
                    "Atenção",
                    "Informe a quantidade de metros/peça.",
                    parent=dialog,
                )
                entries["Metros/Peça"].focus_set()
                return

            tecido = {
                "Código": codigo,
                "Descrição": descricao,
                "Cor": entries["Cor"].get().strip(),
                "Fornecedor": entries["Fornecedor"].get().strip(),
                "Composição": entries["Composição"].get().strip(),
                "Metros/Peça": entries["Metros/Peça"].get().strip(),
                "Valor Metro": entries["Valor Metro"].get().strip(),
                "valor_total": entries["valor_total"].get().strip(),
            }

            self.tecidos.append(tecido)
            self.atualizar_tabela_tecidos()
            self.atualizar_totais()

            self._auto_message(f"Tecido {codigo} adicionado com sucesso!")
            dialog.destroy()

        def cancelar():
            dialog.destroy()

        ctk.CTkButton(
            button_frame,
            text="💾 Salvar",
            command=salvar,
            fg_color=cor_sucesso,
            hover_color=hover_sucesso,
            text_color=get_contraste_texto(cor_sucesso),
            font=("Arial", 12, "bold"),
            width=100,
            height=35,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="❌ Cancelar",
            command=cancelar,
            fg_color=cor_destaque,
            hover_color=hover_destaque,
            text_color=get_contraste_texto(cor_destaque),
            font=("Arial", 12),
            width=100,
            height=35,
        ).pack(side="left", padx=5)

        if not entries["Código"].get().strip():
            entries["Código"].focus_set()
        elif not entries["Metros/Peça"].get().strip():
            entries["Metros/Peça"].focus_set()
        else:
            entries["Valor Metro"].focus_set()

        calcular_total()
        dialog.wait_window()

    def remover_tecido(self):
        """Remove tecido selecionado."""
        selecionado = self.tecidos_tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um tecido para remover")
            return

        index = self.tecidos_tabela.index(selecionado[0])
        self.tecidos.pop(index)
        self.atualizar_tabela_tecidos()
        self.atualizar_totais()

    # =================== MÉTODOS DE AVIAMENTOS ===================
    def pesquisar_aviamento(self):
        """Pesquisa aviamentos no estoque_aviamentos."""
        # Usar diálogo customizado para entrada de termo, centralizado e com tema aplicado
        termo = self._input_dialogo(
            "Pesquisar Aviamento",
            "Digite parte de código, descrição, cor ou fornecedor:",
        )
        if not termo or not str(termo).strip():
            return

        termo_like = f"%{termo.strip()}%"

        try:
            rows = db.fetch_all(
                """
                SELECT 
                    codigo,
                    descricao, 
                    cor, 
                    fornecedor, 
                    valor_unidade,
                    quantidade as quantidade_estoque
                FROM opera.estoque_aviamentos
                WHERE (codigo ILIKE %s OR descricao ILIKE %s OR cor ILIKE %s OR fornecedor ILIKE %s)
                ORDER BY descricao
                """,
                (termo_like, termo_like, termo_like, termo_like),
            )

            print(f"🔍 DEBUG pesquisa_aviamento - {len(rows)} resultados")
            for i, row in enumerate(rows):
                print(f"  Resultado {i}: {row}")

            if not rows:
                messagebox.showinfo("Pesquisa", "Nenhum aviamento encontrado.", parent=self.root)
                return

            self._mostrar_resultado_pesquisa(rows, "Aviamentos", self.adicionar_aviamento)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro na pesquisa de aviamentos:\n{e}", parent=self.root)

    def adicionar_aviamento(self, prefill=None):
        """Adiciona um aviamento ao cadastro. Aceita 'prefill' vindo da pesquisa."""
        prefill = prefill or {}

        # Cores do tema
        cor_fundo = getattr(self.sistema, 'cor_fundo', '#F5F5F5')
        cor_primaria = getattr(self.sistema, 'cor_primaria', '#007BFF')
        cor_texto = getattr(self.sistema, 'cor_texto', '#000000')
        cor_sucesso = getattr(self.sistema, 'cor_sucesso', '#28A745')
        cor_destaque = getattr(self.sistema, 'cor_destaque', '#6C757D')

        hover_primaria = ajustar_hover(cor_primaria)
        hover_sucesso = ajustar_hover(cor_sucesso)
        hover_destaque = ajustar_hover(cor_destaque)

        dialog = ctk.CTkToplevel(master=self.root)
        dialog.transient(self.root)
        dialog.grab_set()
        centralizar_janela(dialog, 450, 500)
        dialog.title("Adicionar Aviamento")
        dialog.resizable(False, False)
        dialog.configure(fg_color=cor_fundo)

        main_frame = ctk.CTkFrame(dialog, fg_color=cor_fundo)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        campos = [
            ("Código", ""),
            ("Descrição", ""),
            ("Cor", ""),
            ("Fornecedor", ""),
            ("Quantidade", ""),
            ("Valor Unidade", ""),
            ("valor_total", "0,00"),
        ]
        entries = {}

        # Construção dos campos
        for i, (rotulo, default) in enumerate(campos):
            label = ctk.CTkLabel(
                main_frame,
                text=rotulo + ":",
                font=("Arial", 12, "bold"),
                text_color=cor_texto,
            )
            label.grid(row=i, column=0, padx=10, pady=8, sticky="e")

            entry = ctk.CTkEntry(main_frame, font=("Arial", 12), width=250)

            inicial = prefill.get(rotulo, default)

            entry.insert(0, inicial)

            if rotulo == "valor_total":
                entry.configure(state="readonly", fg_color="#f0f0f0")
            elif rotulo in ["Quantidade", "Valor Unidade"]:
                entry.configure(
                    validate="key",
                    validatecommand=(dialog.register(validar_entrada_monetaria), "%P"),
                )

            entry.grid(row=i, column=1, padx=10, pady=8, sticky="w")
            entries[rotulo] = entry

        def calcular_total(event=None):
            """Calcula o total = quantidade * valor_unidade."""
            try:
                quantidade_texto = entries["Quantidade"].get().strip()
                valor_unidade_texto = entries["Valor Unidade"].get().strip()

                if not quantidade_texto or not valor_unidade_texto:
                    total = 0.0
                else:
                    quantidade = formatar_valor(quantidade_texto)
                    valor_unidade = formatar_valor(valor_unidade_texto)
                    total = quantidade * valor_unidade

                entries["valor_total"].configure(state="normal")
                entries["valor_total"].delete(0, tk.END)
                entries["valor_total"].insert(0, formatar_para_exibicao(total))
                entries["valor_total"].configure(state="readonly")
                return True

            except Exception as e:
                print(f"Erro no cálculo: {e}")
                return False

        entries["Quantidade"].bind("<KeyRelease>", calcular_total)
        entries["Valor Unidade"].bind("<KeyRelease>", calcular_total)

        # Botões
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=len(campos) + 1, column=0, columnspan=2, pady=20)

        ctk.CTkButton(
            button_frame,
            text="↻ Calcular Total",
            command=calcular_total,
            fg_color=cor_primaria,
            hover_color=hover_primaria,
            text_color=get_contraste_texto(cor_primaria),
            font=("Arial", 11, "bold"),
            width=120,
            height=35,
        ).pack(side="left", padx=10)

        def salvar():
            if not calcular_total():
                messagebox.showwarning(
                    "Atenção",
                    "Erro no cálculo do total. Verifique os valores.",
                    parent=dialog,
                )
                return

            codigo = entries["Código"].get().strip()
            descricao = entries["Descrição"].get().strip()
            quantidade = entries["Quantidade"].get().strip()

            if not codigo:
                messagebox.showwarning(
                    "Atenção",
                    "O campo Código é obrigatório.",
                    parent=dialog,
                )
                entries["Código"].focus_set()
                return

            if not descricao:
                messagebox.showwarning(
                    "Atenção",
                    "O campo Descrição é obrigatório.",
                    parent=dialog,
                )
                entries["Descrição"].focus_set()
                return

            if not quantidade or formatar_valor(quantidade) == 0:
                messagebox.showwarning(
                    "Atenção",
                    "Informe a quantidade.",
                    parent=dialog,
                )
                entries["Quantidade"].focus_set()
                return

            aviamento = {
                "Código": codigo,
                "Descrição": descricao,
                "Cor": entries["Cor"].get().strip(),
                "Fornecedor": entries["Fornecedor"].get().strip(),
                "Quantidade": entries["Quantidade"].get().strip(),
                "Valor Unidade": entries["Valor Unidade"].get().strip(),
                "valor_total": entries["valor_total"].get().strip(),
            }

            self.aviamentos.append(aviamento)
            self.atualizar_tabela_aviamentos()
            self.atualizar_totais()

            self._auto_message(f"Aviamento {codigo} adicionado com sucesso!")
            dialog.destroy()

        def cancelar():
            dialog.destroy()

        ctk.CTkButton(
            button_frame,
            text="💾 Salvar",
            command=salvar,
            fg_color=cor_sucesso,
            hover_color=hover_sucesso,
            text_color=get_contraste_texto(cor_sucesso),
            font=("Arial", 12, "bold"),
            width=100,
            height=35,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="❌ Cancelar",
            command=cancelar,
            fg_color=cor_destaque,
            hover_color=hover_destaque,
            text_color=get_contraste_texto(cor_destaque),
            font=("Arial", 12),
            width=100,
            height=35,
        ).pack(side="left", padx=5)

        # Foco inicial
        if not entries["Código"].get().strip():
            entries["Código"].focus_set()
        elif not entries["Quantidade"].get().strip():
            entries["Quantidade"].focus_set()
        else:
            entries["Valor Unidade"].focus_set()

        calcular_total()
        dialog.wait_window()

    def remover_aviamento(self):
        """Remove aviamento selecionado."""
        selecionado = self.aviamentos_tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um aviamento para remover")
            return

        index = self.aviamentos_tabela.index(selecionado[0])
        self.aviamentos.pop(index)
        self.atualizar_tabela_aviamentos()
        self.atualizar_totais()

    # =================== MÉTODOS DE OUTROS SERVIÇOS ===================
    def adicionar_outro(self, prefill=None):
        """Adiciona um item/serviço à lista de outros."""
        prefill = prefill or {}

        # Cores do tema
        cor_fundo = getattr(self.sistema, 'cor_fundo', '#F5F5F5')
        cor_primaria = getattr(self.sistema, 'cor_primaria', '#007BFF')
        cor_texto = getattr(self.sistema, 'cor_texto', '#000000')
        cor_sucesso = getattr(self.sistema, 'cor_sucesso', '#28A745')
        cor_destaque = getattr(self.sistema, 'cor_destaque', '#6C757D')

        hover_primaria = ajustar_hover(cor_primaria)
        hover_sucesso = ajustar_hover(cor_sucesso)
        hover_destaque = ajustar_hover(cor_destaque)

        dlg = ctk.CTkToplevel(self.root)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.title("Adicionar Outro (Serviço/Item)")
        centralizar_janela(dlg, 420, 520)
        dlg.configure(fg_color=cor_fundo)
        dlg.resizable(False, False)

        main_frame = ctk.CTkFrame(dlg, fg_color=cor_fundo)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        campos = [
            ("Código", ""),
            ("Descrição", ""),
            ("Cor", ""),
            ("Fornecedor", ""),
            ("Unid.", "un"),
            ("Quantidade", "0"),
            ("Preço", "0,00"),
            ("valor_total", "0,00"),
        ]
        entries = {}

        def _pf(rot):
            # tenta pegar do prefill, aceitando tanto chaves com acento
            # quanto nomes de coluna do banco
            if rot in prefill:
                return prefill.get(rot)
            m = {
                "Código": ["codigo", "código"],
                "Descrição": ["descricao", "descrição"],
                "Cor": ["cor"],
                "Fornecedor": ["fornecedor"],
                "Unid.": ["unidade", "unid"],
                "Quantidade": ["quantidade", "qtd"],
                "Preço": ["preco", "preço", "valor"],
                "valor_total": ["total", "valor_total"],
            }
            if rot in m:
                for k in m[rot]:
                    if k in prefill:
                        return prefill[k]
            return None

        # Construção dos campos
        for i, (rot, default) in enumerate(campos):
            ctk.CTkLabel(
                main_frame,
                text=rot + ":",
                font=("Arial", 12, "bold"),
                text_color=cor_texto,
            ).grid(row=i, column=0, padx=10, pady=5, sticky="e")

            e = ctk.CTkEntry(main_frame, font=("Arial", 12), width=250)
            val = _pf(rot) or default
            e.insert(0, val)

            if rot in ("Quantidade", "Preço"):
                e.configure(
                    validate="key",
                    validatecommand=(dlg.register(validar_entrada_monetaria), "%P"),
                )
            if rot == "valor_total":
                e.configure(state="readonly", fg_color="#f0f0f0")

            e.grid(row=i, column=1, padx=10, pady=5, sticky="w")
            entries[rot] = e

        def calcular_total():
            """Calcula total = quantidade * preço."""
            try:
                qtd = formatar_valor(entries["Quantidade"].get())
                preco = formatar_valor(entries["Preço"].get())
                total = qtd * preco
                entries["valor_total"].configure(state="normal")
                entries["valor_total"].delete(0, "end")
                entries["valor_total"].insert(0, formatar_para_exibicao(total))
                entries["valor_total"].configure(state="readonly")
                return True
            except Exception as e:
                print(f"Erro ao calcular total (outros): {e}")
                return False

        # Atualiza total ao digitar
        entries["Quantidade"].bind("<KeyRelease>", lambda e: calcular_total())
        entries["Preço"].bind("<KeyRelease>", lambda e: calcular_total())

        # Botões
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=len(campos) + 1, column=0, columnspan=2, pady=20)

        ctk.CTkButton(
            button_frame,
            text="↻ Calcular Total",
            command=calcular_total,
            fg_color=cor_primaria,
            hover_color=hover_primaria,
            text_color=get_contraste_texto(cor_primaria),
            font=("Arial", 11, "bold"),
            width=130,
            height=35,
        ).pack(side="left", padx=5)

        def salvar():
            if not calcular_total():
                messagebox.showwarning(
                    "Atenção",
                    "Erro no cálculo do total.",
                    parent=dlg,
                )
                return

            codigo = entries["Código"].get().strip()
            descricao = entries["Descrição"].get().strip()
            if not codigo:
                messagebox.showwarning(
                    "Atenção",
                    "O campo Código é obrigatório.",
                    parent=dlg,
                )
                entries["Código"].focus_set()
                return
            if not descricao:
                messagebox.showwarning(
                    "Atenção",
                    "O campo Descrição é obrigatório.",
                    parent=dlg,
                )
                entries["Descrição"].focus_set()
                return

            outro = {
                "Código": entries["Código"].get().strip(),
                "Descrição": entries["Descrição"].get().strip(),
                "Cor": entries["Cor"].get().strip(),
                "Fornecedor": entries["Fornecedor"].get().strip(),
                "Unid.": entries["Unid."].get().strip(),
                "Quantidade": entries["Quantidade"].get().strip(),
                "Preço": entries["Preço"].get().strip(),
                "valor_total": entries["valor_total"].get().strip(),
            }

            self.outros.append(outro)
            self.atualizar_tabela_outros()
            self.atualizar_totais()

            self._auto_message(f"Item/serviço {outro['Código']} adicionado com sucesso!")
            dlg.destroy()

        def cancelar():
            dlg.destroy()

        ctk.CTkButton(
            button_frame,
            text="Salvar",
            command=salvar,
            fg_color=cor_sucesso,
            hover_color=hover_sucesso,
            text_color=get_contraste_texto(cor_sucesso),
            font=("Arial", 12, "bold"),
            width=100,
            height=35,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Cancelar",
            command=cancelar,
            fg_color=cor_destaque,
            hover_color=hover_destaque,
            text_color=get_contraste_texto(cor_destaque),
            font=("Arial", 12),
            width=110,
            height=35,
        ).pack(side="left", padx=5)

        # Foco inicial
        if not entries["Código"].get().strip():
            entries["Código"].focus_set()
        elif not entries["Quantidade"].get().strip():
            entries["Quantidade"].focus_set()
        else:
            entries["Preço"].focus_set()

        calcular_total()
        dlg.wait_window()

    def remover_outro(self):
        """Remove item/serviço selecionado."""
        sel = self.outros_tabela.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um item para remover")
            return
        idx = self.outros_tabela.index(sel[0])
        if 0 <= idx < len(self.outros):
            self.outros.pop(idx)
        self.atualizar_tabela_outros()
        self.atualizar_totais()

    # =================== MÉTODOS DE PESQUISA ===================
    def pesquisar_modelos(self):
        """Pesquisa modelos na tabela de cadastro_modelos_cabecalho."""
        termo = (self.pesquisa_entry.get() or "").strip()

        for item in self.tabela_modelos.get_children():
            self.tabela_modelos.delete(item)

        schema = db.get_schema()

        if termo:
            sql = f"""
                SELECT
                    codigo,
                    COALESCE(descricao, '') AS descricao,
                    COALESCE(colecao, '') AS colecao,
                    TO_CHAR(COALESCE(data_criacao, NOW()), 'DD/MM/YYYY') AS data_fmt
                FROM {schema}.cadastro_modelos_cabecalho
                WHERE codigo ILIKE %s OR descricao ILIKE %s OR colecao ILIKE %s
                ORDER BY COALESCE(data_criacao, NOW()) DESC, codigo DESC
                LIMIT 50
            """
            params = [f"%{termo}%", f"%{termo}%", f"%{termo}%"]
        else:
            sql = f"""
                SELECT
                    codigo,
                    COALESCE(descricao, '') AS descricao,
                    COALESCE(colecao, '') AS colecao,
                    TO_CHAR(COALESCE(data_criacao, NOW()), 'DD/MM/YYYY') AS data_fmt
                FROM {schema}.cadastro_modelos_cabecalho
                ORDER BY COALESCE(data_criacao, NOW()) DESC, codigo DESC
                LIMIT 50
            """
            params = []

        try:
            rows = db.fetch_all(sql, params)
            for r in rows:
                self.tabela_modelos.insert("", "end", values=(
                    r["codigo"], r["descricao"], r["colecao"], r["data_fmt"]))

            print(f"📊 {len(rows)} modelos encontrados na pesquisa.")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na pesquisa:\n{e}")

    def limpar_pesquisa(self):
        """Limpa a pesquisa."""
        self.pesquisa_entry.delete(0, "end")
        self.atualizar_tabela_modelos()

    def carregar_modelo_pesquisa(self):
        """Carrega modelo selecionado da pesquisa."""
        selecao = self.tabela_modelos.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um modelo para carregar.")
            return

        item = self.tabela_modelos.item(selecao[0])
        codigo = item["values"][0]
        self.carregar_cadastro(codigo)
        self.tabview.set("Principal")
        self._auto_message(f"Modelo {codigo} carregado com sucesso!")

    def gerar_pdf_pesquisa(self):
        """Gera PDF do modelo selecionado na pesquisa."""
        selecao = self.tabela_modelos.selection()
        if not selecao:
            messagebox.showwarning("Aviso", "Selecione um modelo para gerar PDF.")
            return

        item = self.tabela_modelos.item(selecao[0])
        codigo = item["values"][0]

        try:
            self.carregar_cadastro(codigo)
            self.on_click_imprimir()

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar PDF: {str(e)}")

    def imprimir_pdf_pesquisa(self):
        """Imprime PDF do modelo selecionado na pesquisa."""
        self.gerar_pdf_pesquisa()

    def on_double_click_modelos(self, event):
        """Carrega o modelo selecionado na tabela."""
        try:
            item = self.tabela_modelos.selection()
            if not item:
                return
            valores = self.tabela_modelos.item(item[0], "values")
            if not valores or len(valores) == 0:
                return
            codigo = valores[0]
            if not codigo:
                return

            print(f"🔎 Carregando modelo {codigo}...")
            self.carregar_cadastro(codigo)
            self.tabview.set("Principal")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar modelo:\n{e}")

    # =================== MÉTODOS DE ATUALIZAÇÃO DE TABELAS ===================
    def atualizar_tabela_modelos(self):
        """Atualiza a tabela que lista os últimos modelos cadastrados."""
        try:
            for item in self.tabela_modelos.get_children():
                self.tabela_modelos.delete(item)

            schema = db.get_schema()
            sql = f"""
                SELECT
                    codigo,
                    COALESCE(descricao, '') AS descricao,
                    COALESCE(colecao, '') AS colecao,
                    TO_CHAR(COALESCE(data_criacao, NOW()), 'DD/MM/YYYY') AS data_fmt
                FROM {schema}.cadastro_modelos_cabecalho
                ORDER BY COALESCE(data_criacao, NOW()) DESC, codigo DESC
                LIMIT 20
            """
            rows = db.fetch_all(sql)
            for r in rows:
                self.tabela_modelos.insert("", "end", values=(
                    r["codigo"], r["descricao"], r["colecao"], r["data_fmt"]))

            print(f"📊 {len(rows)} modelos listados na tabela.")

        except Exception as e:
            print(f"⚠️ Erro ao atualizar tabela de modelos: {e}")

    def atualizar_tabela_tecidos(self):
        """Atualiza a tabela de tecidos."""
        try:
            for item in self.tecidos_tabela.get_children():
                self.tecidos_tabela.delete(item)

            for t in self.tecidos:
                self.tecidos_tabela.insert("", "end", values=(
                    t.get("Código", ""),
                    t.get("Descrição", ""),
                    t.get("Cor", ""),
                    t.get("Fornecedor", ""),
                    t.get("Composição", ""),
                    t.get("Metros/Peça", "0,00"),
                    t.get("Valor Metro", "0,00"),
                    t.get("valor_total", "0,00"),
                ))

        except Exception as e:
            print(f"❌ Falha ao atualizar tabela 'Tecidos': {e}")

    def atualizar_tabela_aviamentos(self):
        """Atualiza a tabela de aviamentos."""
        try:
            for item in self.aviamentos_tabela.get_children():
                self.aviamentos_tabela.delete(item)

            for a in self.aviamentos:
                self.aviamentos_tabela.insert("", "end", values=(
                    a.get("Código", ""),
                    a.get("Descrição", ""),
                    a.get("Cor", ""),
                    a.get("Fornecedor", ""),
                    a.get("Quantidade", "0"),
                    a.get("Valor Unidade", "0,00"),
                    a.get("valor_total", "0,00"),
                ))

        except Exception as e:
            print(f"❌ Falha ao atualizar tabela 'Aviamentos': {e}")

    def atualizar_tabela_outros(self):
        """Atualiza a tabela de outros serviços."""
        if not getattr(self, "outros_tabela", None) or not self.outros_tabela.winfo_exists():
            return
        for iid in self.outros_tabela.get_children():
            self.outros_tabela.delete(iid)
        for o in self.outros:
            self.outros_tabela.insert("", "end", values=[
                o.get("Código", o.get("codigo", "")),
                o.get("Descrição", o.get("descricao", "")),
                o.get("Cor", o.get("cor", "")),
                o.get("Fornecedor", o.get("fornecedor", "")),
                o.get("Unid.", o.get("unidade", "")),
                o.get("Quantidade", o.get("quantidade", "")),
                o.get("Preço", o.get("preco", "")),
                o.get("valor_total", o.get("total", "")),
            ])

    def atualizar_totais(self):
        """Atualiza o custo total."""
        try:
            total = 0.0
            for t in self.tecidos:
                total += formatar_valor(t.get("valor_total", "0"))
            for a in self.aviamentos:
                total += formatar_valor(a.get("valor_total", "0"))
            for o in self.outros:
                total += formatar_valor(o.get("valor_total", "0"))

            self.custo_entry.configure(state="normal")
            self.custo_entry.delete(0, tk.END)
            self.custo_entry.insert(0, formatar_para_exibicao(total))
            self.custo_entry.configure(state="readonly")

        except Exception as e:
            print(f"Erro ao atualizar totais: {e}")

    # =================== MÉTODOS AUXILIARES ===================
    def _mostrar_resultado_pesquisa(self, rows, titulo, callback_adicionar):
        """Mostra resultados de pesquisa em uma janela."""
        jan = ctk.CTkToplevel(master=self.root)
        jan.transient(self.root)
        jan.grab_set()

        # Cores do tema para esta janela de resultados
        cor_fundo = getattr(self.sistema, 'cor_fundo', '#F5F5F5')
        cor_primaria = getattr(self.sistema, 'cor_primaria', '#007BFF')
        cor_texto = getattr(self.sistema, 'cor_texto', '#000000')
        cor_sucesso = getattr(self.sistema, 'cor_sucesso', '#28A745')
        cor_destaque = getattr(self.sistema, 'cor_destaque', '#6C757D')

        hover_sucesso = ajustar_hover(cor_sucesso)
        hover_destaque = ajustar_hover(cor_destaque)

        centralizar_janela(jan, 1200, 600)
        jan.title(f"Resultados da Pesquisa - {titulo}")
        jan.resizable(True, True)
        jan.configure(fg_color=cor_fundo)

        main_frame = ctk.CTkFrame(jan, fg_color=cor_fundo)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        title_label = ctk.CTkLabel(
            main_frame,
            text=f"Resultados da Pesquisa - {titulo}",
            font=("Arial", 16, "bold"),
            text_color=cor_texto  # contraste com fundo da janela
        )
        title_label.pack(pady=(0, 15))

        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, pady=(0, 15))

        cols = [col for col in (list(rows[0].keys()) if rows else []) if col != 'tabela_origem']
        tabela = ttk.Treeview(table_frame, columns=cols, show="headings", height=12)

        v_scroll = ctk.CTkScrollbar(table_frame, orientation="vertical", command=tabela.yview)
        h_scroll = ctk.CTkScrollbar(table_frame, orientation="horizontal", command=tabela.xview)
        tabela.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        for c in cols:
            nome_exibicao = c.replace('_', ' ').title()
            tabela.heading(c, text=nome_exibicao)

            if c == 'descricao':
                tabela.column(c, width=250, anchor="w")
            elif c in ['fornecedor', 'composicao']:
                tabela.column(c, width=150, anchor="w")
            elif c == 'codigo':
                tabela.column(c, width=120, anchor="w")
            elif c == 'cor':
                tabela.column(c, width=100, anchor="w")
            elif c in ['valor_metro', 'valor_unidade', 'preco']:
                tabela.column(c, width=100, anchor="e")
            elif c in ['metros_estoque', 'quantidade_estoque', 'quantidade']:
                tabela.column(c, width=120, anchor="e")
            else:
                tabela.column(c, width=120, anchor="w")

        tabela.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        for r in rows:
            valores = [r.get(c, "") for c in cols]
            valores_formatados = []
            for i, valor in enumerate(valores):
                col_name = cols[i]
                if col_name in ['valor_metro', 'valor_unidade', 'preco'] and valor:
                    try:
                        if isinstance(valor, (int, float)):
                            valor_num = valor
                        else:
                            valor_str = str(valor).replace(',', '.')
                            valor_num = float(valor_str)
                        valores_formatados.append(formatar_para_exibicao(valor_num))
                    except (ValueError, TypeError):
                        valores_formatados.append(str(valor))
                elif col_name in ['metros_estoque', 'quantidade_estoque', 'quantidade'] and valor:
                    try:
                        if isinstance(valor, (int, float)):
                            valor_num = valor
                        else:
                            valor_str = str(valor).replace(',', '.')
                            valor_num = float(valor_str)
                        valores_formatados.append(str(valor_num))
                    except (ValueError, TypeError):
                        valores_formatados.append(str(valor))
                else:
                    valores_formatados.append(str(valor) if valor is not None else "")

            tabela.insert("", "end", values=valores_formatados)

        def _map_prefill(row_data, callback):
            m_tecidos = {
                "codigo": "Código",
                "descricao": "Descrição",
                "cor": "Cor",
                "fornecedor": "Fornecedor",
                "composicao": "Composição",
                "valor_metro": "Valor Metro",
            }

            m_aviamentos = {
                "codigo": "Código",
                "descricao": "Descrição",
                "cor": "Cor",
                "fornecedor": "Fornecedor",
                "valor_unidade": "Valor Unidade",
            }

            m_outros = {
                "codigo": "Código",
                "descricao": "Descrição",
                "cor": "Cor",
                "fornecedor": "Fornecedor",
                "unidade": "Unid.",
                "preco": "Preço",
            }

            if callback == self.adicionar_tecido:
                m = m_tecidos
            elif callback == self.adicionar_aviamento:
                m = m_aviamentos
            else:
                m = m_outros

            prefill = {}
            for db_col, dialog_field in m.items():
                if db_col in row_data and row_data[db_col] not in (None, ""):
                    valor_real = row_data[db_col]
                    if db_col in ['valor_metro', 'valor_unidade', 'preco']:
                        try:
                            if isinstance(valor_real, (int, float)):
                                valor_num = valor_real
                            else:
                                valor_str = str(valor_real).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
                                valor_num = float(valor_str)
                            valor_real = formatar_para_exibicao(valor_num)
                        except (ValueError, TypeError):
                            pass
                    prefill[dialog_field] = str(valor_real) if valor_real is not None else ""
            return prefill

        def on_escolher_e_abrir():
            sel = tabela.selection()
            if not sel:
                messagebox.showwarning("Atenção", "Selecione um item primeiro.", parent=jan)
                return

            try:
                item_index = tabela.index(sel[0])
                if 0 <= item_index < len(rows):
                    row_original = rows[item_index]
                    prefill = _map_prefill(row_original, callback_adicionar)
                    jan.destroy()
                    callback_adicionar(prefill)
                else:
                    messagebox.showerror("Erro", "Item selecionado não encontrado.", parent=jan)
            except Exception as e:
                print(f"❌ DEBUG - Erro ao adicionar: {e}")
                import traceback
                traceback.print_exc()
                messagebox.showerror("Erro", f"Erro ao adicionar item:\n{e}", parent=jan)

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=10)

        btn_adicionar = ctk.CTkButton(
            button_frame,
            text="➕ Adicionar Selecionado",
            command=on_escolher_e_abrir,
            fg_color=cor_sucesso,
            hover_color=hover_sucesso,
            text_color=get_contraste_texto(cor_sucesso),
            font=("Arial", 12, "bold"),
            width=200,
            height=40,
        )
        btn_adicionar.pack(side="left", padx=10)

        btn_fechar = ctk.CTkButton(
            button_frame,
            text="❌ Fechar",
            command=jan.destroy,
            fg_color=cor_destaque,
            hover_color=hover_destaque,
            text_color=get_contraste_texto(cor_destaque),
            font=("Arial", 12),
            width=120,
            height=40,
        )
        btn_fechar.pack(side="left", padx=10)

        if rows:
            info_text = f"📊 {len(rows)} resultado(s) encontrado(s). "
            info_text += "Duplo-clique em qualquer linha para adicionar rapidamente."

            info_label = ctk.CTkLabel(
                main_frame,
                text=info_text,
                font=("Arial", 11),
                text_color=cor_texto,  # usa cor de texto do tema
            )
            info_label.pack(pady=(10, 0))

        dica_label = ctk.CTkLabel(
            main_frame,
            text="💡 Dica: Use as setas para navegar e Enter ou duplo-clique para selecionar",
            font=("Arial", 9),
            text_color=get_contraste_texto(getattr(self.sistema, "cor_secundaria", "#E0E0E0")),
        )
        dica_label.pack(pady=(5, 0))

        def _on_double_click(event):
            region = tabela.identify("region", event.x, event.y)
            if region == "cell":
                on_escolher_e_abrir()

        tabela.bind("<Double-1>", _on_double_click)

        def _on_closing():
            jan.destroy()

        jan.protocol("WM_DELETE_WINDOW", _on_closing)
        jan.focus_set()
        tabela.focus_set()
        jan.wait_window()

    # =================== MÉTODOS DE AÇÃO ===================
    def on_click_imprimir(self):
        """Gera e abre o PDF do cadastro - VERSÃO CORRIGIDA"""
        try:
            codigo = self.codigo_entry.get().strip()
            if not codigo:
                messagebox.showwarning("Aviso", "Informe o código do modelo para imprimir.")
                return

            print(f"🔄 Iniciando geração do PDF para {codigo}...")

            # Mostrar mensagem de processamento
            self._auto_message("Gerando PDF... Aguarde!")

            dados = {
                "Codigo": codigo,
                "Desc": self.descricao_entry.get().strip(),
                "Colecao": self.colecao_entry.get().strip(),
                "Tam": self.tamanho_base_var.get(),
                "Dif": self.dificuldade_var.get(),
                "Modelista": self.modelista_entry.get().strip(),
                "Piloto": self.pilotista_entry.get().strip(),
                "Custo": self.custo_entry.get().strip(),
                "grade_disponivel": ", ".join([t for t in self.tamanhos if self.grade_vars[t].get() == 1]),
                "Data": datetime.now().strftime("%d/%m/%Y"),
            }

            # Executar em uma thread separada para não travar a interface
            def gerar_pdf_thread():
                try:
                    pdf_path = gerar_pdf_cadastro_modelo(
                        dados=dados,
                        tecidos=self.tecidos,
                        aviamentos=self.aviamentos,
                        outros=self.outros,
                        imagens_modelo=self.imagens_modelo,
                        imagens_tecidos=self.imagens_tecidos,
                        imagens_aviamentos=self.imagens_aviamentos,
                        imagens_outros=self.imagens_outros,
                    )

                    if os.path.exists(pdf_path):
                        # Usar after para atualizar a interface na thread principal
                        self.root.after(0, lambda: self._abrir_pdf(pdf_path))
                    else:
                        self.root.after(0, lambda: messagebox.showerror("Erro", "Falha ao gerar PDF."))

                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Erro", f"Falha ao gerar PDF:\n{e}"))

            # Iniciar thread
            import threading
            thread = threading.Thread(target=gerar_pdf_thread, daemon=True)
            thread.start()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao iniciar geração do PDF:\n{e}")

    def _abrir_pdf(self, pdf_path):
        """Abre o PDF após geração (executado na thread principal)"""
        try:
            imprimir_pdf(pdf_path)
            self._auto_message("PDF gerado e aberto com sucesso!")
            print("✅ PDF aberto com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao abrir PDF:\n{e}")

    def exportar_cadastro(self):
        """Exporta o cadastro (função básica)."""
        try:
            codigo = self.codigo_entry.get().strip()
            if not codigo:
                messagebox.showwarning("Aviso", "Informe o código do modelo para exportar.")
                return

            filename = f"cadastro_{codigo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file_path = filedialog.asksaveasfilename(
                parent=self.root,
                defaultextension=".json",
                initialfile=filename,
                filetypes=[
                    ("JSON files", "*.json"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*")
                ]
            )

            if file_path:
                dados_export = {
                    "codigo": codigo,
                    "descricao": self.descricao_entry.get().strip(),
                    "colecao": self.colecao_entry.get().strip(),
                    "data_exportacao": datetime.now().isoformat(),
                    "itens": {
                        "tecidos": len(self.tecidos),
                        "aviamentos": len(self.aviamentos),
                        "outros": len(self.outros)
                    }
                }

                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(dados_export, f, ensure_ascii=False, indent=2)

                self._auto_message(f"Cadastro exportado para:\n{os.path.basename(file_path)}")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar cadastro:\n{e}")

    def sair(self):
        """Fecha a aplicação."""
        self.root.quit()

    #__________________________________________________________________________
    def __init__(self, master, sistema, mostrar_scrollbar=False):
        super().__init__(master)
        self.master = master
        self.sistema = sistema
        self.root = sistema.root if hasattr(sistema, 'root') else sistema

        # CORREÇÃO: Adicionar referências para imagens
        self.frente_img_ref = None
        self.costas_img_ref = None

        # Configurar logger
        self.logger = logger
        if hasattr(self.logger, "set_usuario"):
            self.logger.set_usuario(
                getattr(self, "usuario_atual", "desconhecido"),
                getattr(self, "usuario_hierarquia", "default"),
            )
        if hasattr(self.logger, "set_pagina"):
            self.logger.set_pagina("MenuPrincipal")
        if hasattr(self.logger, "info"):
            self.logger.info(
                "Sistema OPERA inicializado",
                detalhes={"versao": "1.0", "usuario": getattr(self, "usuario_atual", "desconhecido")},
            )

        # Verifica conexão com o banco
        ok, msg = db.require_ready()
        if not ok:
            messagebox.showerror("Banco não preparado", msg, parent=self.root)
            raise SystemExit(1)

        # Verifica se as tabelas necessárias existem
        print("🔍 Verificando tabelas necessárias...")
        try:
            verificar_tabelas_existem()
            print("✅ Todas as tabelas verificadas com sucesso!")
        except ValueError as e:
            messagebox.showerror(
                "Erro - Tabelas Não Encontradas",
                f"As seguintes tabelas necessárias não foram encontradas:\n\n{e}\n\n"
                "Por favor, execute o script SQL de criação de tabelas no banco de dados primeiro.",
                parent=self.root,
            )
            raise SystemExit(1)

        # Criar pasta para imagens
        print("📁 Criando estrutura de pastas para imagens...")
        if not self.criar_pastas_imagens():
            messagebox.showwarning(
                "Aviso",
                "Não foi possível criar todas as pastas de imagens, mas o sistema continuará.",
                parent=self.root,
            )

        # Inicializar estados e widgets
        self._inicializar_estados()

        # Configurar UI
        self._setup_ui()
        self._initialize_data()

        # APLICAR TEMA LOCAL - NOVO (após um pequeno delay para garantir que a UI foi construída)
        self.after(150, self._aplicar_tema_local)

        # Mostrar mensagem de sucesso
        self._auto_message("Sistema pronto! Banco e pastas configurados.")

    def _ajustar_hover(self, cor):
        """Ajusta uma cor para efeito hover"""
        try:
            cor = cor.lstrip('#')
            r, g, b = tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))
            fator = 0.8
            r = max(0, int(r * fator))
            g = max(0, int(g * fator))
            b = max(0, int(b * fator))
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return cor

    def _input_dialogo(self, titulo: str, mensagem: str):
        """
        Exibe um diálogo simples para entrada de texto que respeita o tema atual.
        Centraliza a janela de diálogo na tela e retorna a string digitada ou None.
        """
        resultado = {"value": None}

        # Janela do diálogo
        dialog = ctk.CTkToplevel(master=self.root)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.title(titulo)
        dialog.resizable(False, False)

        # Dimensões padrão e centralização
        largura = 450
        altura = 170
        centralizar_janela(dialog, largura, altura)

        # Cores do tema
        cor_fundo = getattr(self.sistema, "cor_fundo", "#FFFFFF")
        cor_sucesso = getattr(self.sistema, "cor_sucesso", "#28A745")
        cor_destaque = getattr(self.sistema, "cor_destaque", "#FFC107")

        # Frame principal
        main_frame = ctk.CTkFrame(dialog, fg_color=cor_fundo)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Label
        label = ctk.CTkLabel(
            main_frame,
            text=mensagem,
            wraplength=400,
            justify="left",
            text_color=get_contraste_texto(cor_fundo),
        )
        label.pack(anchor="w", pady=(0, 10))

        # Campo de entrada
        entry = ctk.CTkEntry(main_frame, width=400)
        entry.pack(fill="x", pady=(0, 15))

        # Funções dos botões
        def confirmar():
            resultado["value"] = entry.get()
            dialog.destroy()

        def cancelar():
            resultado["value"] = None
            dialog.destroy()

        # Botões
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack()

        btn_ok = ctk.CTkButton(
            btn_frame,
            text="OK",
            command=confirmar,
            width=120,
            fg_color=cor_sucesso,
            hover_color=self._ajustar_hover(cor_sucesso),
            text_color=get_contraste_texto(cor_sucesso),
        )
        btn_ok.pack(side="left", padx=5)

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=cancelar,
            width=120,
            fg_color=cor_destaque,
            hover_color=self._ajustar_hover(cor_destaque),
            text_color=get_contraste_texto(cor_destaque),
        )
        btn_cancel.pack(side="left", padx=5)

        # === FOCO AUTOMÁTICO NO CAMPO DE ENTRADA ===
        def focar_entry():
            try:
                entry.focus_force()
                entry.icursor(0)
            except Exception:
                pass

        # chama depois da janela aparecer
        dialog.after(50, focar_entry)
        dialog.bind("<Visibility>", lambda e: focar_entry())

        # Atalhos de teclado funcionando mesmo se o foco não estiver no entry
        dialog.bind("<Return>", lambda e: confirmar())
        dialog.bind("<KP_Enter>", lambda e: confirmar())
        dialog.bind("<Escape>", lambda e: cancelar())

        dialog.lift()
        dialog.focus_force()

        # Espera fechar
        dialog.wait_window()
        return resultado["value"]

    def _aplicar_tema_local(self):
        """Aplica o tema do sistema em todos os widgets do CadastroModelosApp"""
        try:
            # Obter cores do sistema
            cor_fundo = getattr(self.sistema, 'cor_fundo', '#FFFFFF')
            cor_primaria = getattr(self.sistema, 'cor_primaria', '#007BFF')
            cor_secundaria = getattr(self.sistema, 'cor_secundaria', '#6C757D')
            cor_texto = getattr(self.sistema, 'cor_texto', '#000000')
            cor_hover = getattr(self.sistema, 'cor_hover', '#E9ECEF')
            cor_destaque = getattr(self.sistema, 'cor_destaque', '#FFC107')
            cor_borda = getattr(self.sistema, 'cor_borda', '#CED4DA')
            cor_sucesso = getattr(self.sistema, 'cor_sucesso', '#28A745')
            cor_alerta = getattr(self.sistema, 'cor_alerta', '#DC3545')
            cor_selecao = getattr(self.sistema, 'cor_selecao', '#007BFF')

            # Aplicar cores em todos os widgets principais
            self.configure(fg_color=cor_fundo)

            if hasattr(self, 'tabview'):
                self.tabview.configure(fg_color=cor_fundo)

                # Aplicar tema em todas as abas
                for tab_name in ["Principal", "Tecidos", "Aviamentos", "Outros serviços", "Pesquisa"]:
                    try:
                        tab = self.tabview.tab(tab_name)
                        tab.configure(fg_color=cor_fundo)
                    except Exception:
                        pass

            # Função recursiva para aplicar cores em todos os widgets
            def _apply_colors(widget):
                for child in widget.winfo_children():
                    try:
                        if isinstance(child, ctk.CTkFrame):
                            child.configure(fg_color=cor_fundo, border_color=cor_borda)
                        elif isinstance(child, ctk.CTkLabel):
                            child.configure(text_color=cor_texto)
                        elif isinstance(child, ctk.CTkButton):
                            # Verificar tipo de botão pela cor
                            text = (child.cget("text") or "").lower()
                            if any(x in text for x in ["salvar", "registrar", "confirmar"]):
                                child.configure(fg_color=cor_sucesso,
                                                hover_color=self._ajustar_hover(cor_sucesso),
                                                text_color=get_contraste_texto(cor_sucesso))
                            elif any(x in text for x in ["cancelar", "excluir", "apagar", "remover"]):
                                child.configure(fg_color=cor_alerta,
                                                hover_color=self._ajustar_hover(cor_alerta),
                                                text_color=get_contraste_texto(cor_alerta))
                            elif any(x in text for x in ["imprimir", "exportar", "pré-visualização", "gerar pdf"]):
                                child.configure(fg_color=cor_destaque,
                                                hover_color=self._ajustar_hover(cor_destaque),
                                                text_color=get_contraste_texto(cor_destaque))
                            else:
                                child.configure(fg_color=cor_primaria,
                                                hover_color=cor_hover,
                                                text_color=get_contraste_texto(cor_primaria),
                                                border_color=cor_borda)
                        elif isinstance(child, ctk.CTkEntry):
                            child.configure(fg_color=cor_secundaria,
                                            border_color=cor_borda,
                                            text_color=cor_texto,
                                            placeholder_text_color=cor_texto)
                        elif isinstance(child, ctk.CTkCheckBox):
                            child.configure(fg_color=cor_selecao,
                                            border_color=cor_borda,
                                            text_color=cor_texto,
                                            hover_color=cor_hover)
                        elif isinstance(child, ctk.CTkRadioButton):
                            child.configure(fg_color=cor_selecao,
                                            border_color=cor_borda,
                                            text_color=cor_texto,
                                            hover_color=cor_hover)
                        elif isinstance(child, ctk.CTkOptionMenu):
                            child.configure(fg_color=cor_primaria,
                                            button_color=cor_selecao,
                                            button_hover_color=self._ajustar_hover(cor_selecao),
                                            text_color=cor_texto)
                        elif isinstance(child, ctk.CTkComboBox):
                            child.configure(fg_color=cor_secundaria,
                                            border_color=cor_borda,
                                            text_color=cor_texto,
                                            button_color=cor_selecao,
                                            button_hover_color=self._ajustar_hover(cor_selecao))
                        elif isinstance(child, ctk.CTkScrollableFrame):
                            child.configure(fg_color=cor_fundo, border_color=cor_borda)
                        elif isinstance(child, ctk.CTkTabview):
                            child.configure(fg_color=cor_fundo)
                        elif isinstance(child, ctk.CTkTextbox):
                            child.configure(fg_color=cor_secundaria,
                                            border_color=cor_borda,
                                            text_color=cor_texto)
                        elif isinstance(child, ctk.CTkProgressBar):
                            child.configure(fg_color=cor_secundaria,
                                            progress_color=cor_selecao,
                                            border_color=cor_borda)
                        elif isinstance(child, ctk.CTkSlider):
                            child.configure(fg_color=cor_secundaria,
                                            progress_color=cor_selecao,
                                            button_color=cor_selecao,
                                            button_hover_color=self._ajustar_hover(cor_selecao))
                        elif isinstance(child, ctk.CTkSegmentedButton):
                            child.configure(fg_color=cor_primaria,
                                            selected_color=cor_selecao,
                                            selected_hover_color=self._ajustar_hover(cor_selecao),
                                            unselected_color=cor_secundaria,
                                            unselected_hover_color=cor_hover,
                                            text_color=cor_texto)
                    except Exception as e:
                        print(f"Erro ao aplicar tema em {child}: {e}")

                    # Aplicar recursivamente
                    _apply_colors(child)

            # Aplicar cores em todos os widgets filhos
            _apply_colors(self)

            # Atualizar Treeviews (tabelas)
            self._atualizar_estilo_tabelas()

        except Exception as e:
            print(f"Erro ao aplicar tema local: {e}")

    def _atualizar_estilo_tabelas(self):
        """Atualiza o estilo das tabelas (Treeviews) para seguir o tema"""
        try:
            from tkinter import ttk

            # Obter cores do sistema
            cor_fundo = getattr(self.sistema, 'cor_fundo', '#FFFFFF')
            cor_primaria = getattr(self.sistema, 'cor_primaria', '#007BFF')
            cor_secundaria = getattr(self.sistema, 'cor_secundaria', '#6C757D')
            cor_texto = getattr(self.sistema, 'cor_texto', '#000000')
            cor_borda = getattr(self.sistema, 'cor_borda', '#CED4DA')
            cor_selecao = getattr(self.sistema, 'cor_selecao', '#007BFF')

            # Criar estilo para as tabelas
            style = ttk.Style()

            # Tentar usar tema 'clam' que é mais customizável
            try:
                style.theme_use('clam')
            except:
                pass

            # Configurar cores da Treeview
            style.configure("Treeview",
                            background=cor_secundaria,
                            fieldbackground=cor_secundaria,
                            foreground=cor_texto,
                            rowheight=25,
                            bordercolor=cor_borda,
                            borderwidth=1,
                            font=("Arial", 10))

            style.configure("Treeview.Heading",
                            background=cor_primaria,
                            foreground=get_contraste_texto(cor_primaria),
                            relief="flat",
                            font=("Arial", 10, "bold"))

            style.map("Treeview",
                      background=[('selected', cor_selecao)],
                      foreground=[('selected', get_contraste_texto(cor_selecao))])

            style.map("Treeview.Heading",
                      relief=[('active', 'flat'), ('pressed', 'flat')])

            # Aplicar estilo a todas as tabelas conhecidas
            tabelas = [
                getattr(self, 'tecidos_tabela', None),
                getattr(self, 'aviamentos_tabela', None),
                getattr(self, 'outros_tabela', None),
                getattr(self, 'tabela_modelos', None)
            ]

            for tabela in tabelas:
                if tabela and hasattr(tabela, 'winfo_exists') and tabela.winfo_exists():
                    try:
                        # Configurar tags para linhas alternadas
                        tabela.tag_configure('evenrow', background=cor_secundaria)
                        tabela.tag_configure('oddrow', background=cor_fundo)

                        # Aplicar tags alternadas
                        children = tabela.get_children()
                        for i, item in enumerate(children):
                            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                            tabela.item(item, tags=(tag,))
                    except Exception as e:
                        print(f"Erro ao aplicar estilo na tabela: {e}")

        except Exception as e:
            print(f"Erro ao atualizar estilo das tabelas: {e}")

# =================== EXECUÇÃO PRINCIPAL ===================
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")


    class SistemaMock:
        def __init__(self):
            self.root = ctk.CTk()
            self.cor_fundo = '#FFFFFF'
            self.cor_texto = '#000000'
            self.cor_primaria = '#007BFF'
            self.cor_hover = '#E9ECEF'
            self.cor_destaque = '#FFC107'
            self.cor_borda = '#CED4DA'
            self.cor_selecao = '#007BFF'  # Cor de seleção


    sistema = SistemaMock()
    sistema.root.title("Sistema de Cadastro de Modelos - OPERA")
    centralizar_janela(sistema.root, 1400, 900)

    app = CadastroModelosApp(sistema.root, sistema)
    app.pack(fill="both", expand=True)


    sistema.root.mainloop()