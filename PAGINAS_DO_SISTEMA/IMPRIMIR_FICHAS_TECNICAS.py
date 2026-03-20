# -*- coding: utf-8 -*-
"""
IMPRIMIR_FICHAS_TECNICAS.py  (versão PostgreSQL)
------------------------------------------------------------------
Atalho para listar modelos já cadastrados e gerar o PDF usando
EXATAMENTE o mesmo layout da página CADASTRAR_MODELO.py.

- Importa gerar_pdf_cadastro_modelo do seu CADASTRAR_MODELO.py
- Lê os dados do banco (PostgreSQL) e mapeia nos MESMOS campos do gerador
- Duplo clique ou botão gera o PDF e imprime/abre
"""
from PAGINAS_DO_SISTEMA import TEMAS
import os
import re
import platform
import subprocess
from datetime import datetime
from typing import Tuple, Optional
# JESUS SEJA LOUVADO PARA TODO O SEMPRE AMEM!!!
try:
    import tkinter as tk  # type: ignore
    from tkinter import ttk, messagebox, filedialog  # type: ignore
except Exception:
    # tkinter não disponível (possível em ambientes headless)
    tk = None
    ttk = None
    messagebox = None
    filedialog = None

# customtkinter é usado para a interface; se não estiver disponível (por exemplo em testes), usa tk como fallback
try:
    import customtkinter as ctk  # type: ignore
except Exception:
    # Fallback simples: reutiliza tk como ctk (pode ser None) para não quebrar importação em testes
    ctk = tk  # type: ignore

# Cria substitutos mínimos para messagebox e filedialog caso tkinter não esteja disponível
if messagebox is None:
    class _DummyMB:
        @staticmethod
        def showerror(title: str, message: str):
            print(f"ERRO: {title}: {message}")
        @staticmethod
        def showwarning(title: str, message: str):
            print(f"AVISO: {title}: {message}")
        @staticmethod
        def showinfo(title: str, message: str):
            print(f"INFO: {title}: {message}")
    messagebox = _DummyMB()  # type: ignore
# JESUS SEJA LOUVADO PARA TODO O SEMPRE AMEM!!!
if filedialog is None:
    class _DummyFD:
        @staticmethod
        def asksaveasfilename(*args, **kwargs):
            return ''
    filedialog = _DummyFD()  # type: ignore

# === Usa o MESMO gerador de PDF do seu módulo ===
try:
    import importlib.util
    from pathlib import Path

    _base_dir = Path(__file__).resolve().parent
    _modelo_candidates = [
        _base_dir / "CADASTRAR_MODELO.py",
        _base_dir / "CADASTRAR_MODELO.py",
    ]
    _modelo_path = next((p for p in _modelo_candidates if p.exists()), None)
    if _modelo_path is None:
        raise FileNotFoundError("CADASTRAR_MODELO*.py não encontrado")

    _spec = importlib.util.spec_from_file_location("opera_cadastrar_modelo", str(_modelo_path))
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Spec inválido para {_modelo_path}")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    gerar_pdf_cadastro_modelo_exato = _mod.gerar_pdf_cadastro_modelo
except Exception as e:
    raise ImportError(
        "Não foi possível importar 'gerar_pdf_cadastro_modelo' de CADASTRAR_MODELO.py.\n"
        "Garanta que o arquivo existe e não possui erros de sintaxe.\n"
        f"Erro original: {e}"
    )

# === Acesso PostgreSQL via módulo de acesso ===
try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception as err:
    def get_conn():
        raise RuntimeError("BANCO_DE_DADOS_PG indisponível: " + str(err))
    def get_schema():
        return "opera"
    def require_ready(essentials=None):
        return False, "Módulo de acesso não disponível"

# =============================================================
# UTILITÁRIOS
# =============================================================
def _exec_all(query: str, params: Tuple = ()):
    """Executa um SELECT e retorna rows (lista de tuplas). Define search_path."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        schema = get_schema()
        try:
            cur.execute(f"SET LOCAL search_path = {schema};")
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


def _exec_row(query: str, params: Tuple = ()):
    """Executa SELECT que retorna 1 linha (ou None)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        schema = get_schema()
        try:
            cur.execute(f"SET LOCAL search_path = {schema};")
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


def _to_str(v) -> str:
    """Formata números para pt-BR (duas casas, vírgula decimal)."""
    s = (str(v) or "").strip()
    if not s or s.lower() == "none":
        return "0,00"
    try:
        return f"{float(s):.2f}".replace(".", ",")
    except Exception:
        s = s.replace("R$", "").replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", ".")
        try:
            return f"{float(s):.2f}".replace(".", ",")
        except Exception:
            return (str(v) or "").replace(".", ",")


def _parse_display_date(value) -> str:
    """
    Converte datas do banco para dd/mm/aaaa, aceitando:
    - 'YYYY-MM-DD'
    - 'YYYY-MM-DD HH:MM:SS' (ou com 'T')
    - 'DD/MM/YYYY' (retorna como está)
    Caso não reconheça, retorna str(value).
    """
    s = str(value or "").strip()
    if not s:
        return ""
    if re.match(r"^\d{2}/\d{2}/\d{4}$", s):
        return s
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%d/%m/%Y")
        except Exception:
            pass
    return s


def _has_column(table: str, column: str) -> bool:
    """Verifica se uma coluna existe na tabela do schema atual."""
    row = _exec_row("""
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = %s
           AND column_name = %s
         LIMIT 1
    """, (table, column))
    return bool(row)

def _table_exists(tbl: str) -> bool:
    row = _exec_row("""
        SELECT 1
          FROM information_schema.tables
         WHERE table_schema = current_schema()
           AND table_name = %s
         LIMIT 1
    """, (tbl,))
    return bool(row)

def _pick_col_expr(table: str, candidates: list[str], alias: str, cast: str = "text") -> str:
    """
    Retorna a primeira coluna existente entre 'candidates' para 'table'.
    Se nenhuma existir, devolve 'NULL::<cast> AS <alias>'.
    Ex.: _pick_col_expr('cadastro_modelos_tecidos', ['codigo_tecido','codigo'], 'codigo')
    """
    for col in candidates:
        if _has_column(table, col):
            return f"{col} AS {alias}"
    return f"NULL::{cast} AS {alias}"



# =============================================================
# CARREGAMENTO DE DADOS
# =============================================================
def carregar_dados_modelo(codigo: str):
    """
    Retorna (dados, tecidos, aviamentos, outros, imagens_modelo, imgs_t, imgs_a, imgs_o)
    prontos para o gerador de PDF.
    """
    # ------------------ Cabeçalho (custo_total -> AS custo) ------------------
    cab = _exec_row("""
        SELECT id, codigo, descricao, colecao, tamanho_base, dificuldade,
               modelista, pilotista,
               COALESCE(custo_total, 0) AS custo,
               pronto_producao, grade_disponivel,
               COALESCE(TO_CHAR(COALESCE(data_criacao::timestamp, NOW()), 'YYYY-MM-DD'), '') AS data_criacao
          FROM cadastro_modelos_cabecalho
         WHERE codigo = %s
         LIMIT 1
    """, (codigo,))
    if not cab:
        messagebox.showwarning("Aviso", f"Modelo '{codigo}' não encontrado.")
        return None

    (cad_id, codigo, descricao, colecao, tamanho_base, dificuldade,
     modelista, pilotista, custo, pronto_producao, grade_disponivel, data_criacao) = cab

    dados = {
        "Codigo":           codigo or "",
        "Desc":             descricao or "",
        "Colecao":          colecao or "",
        "Tam":              tamanho_base or "",
        "Dif":              dificuldade or "",
        "Modelista":        modelista or "",
        "Piloto":           pilotista or "",
        "Custo":            _to_str(custo),
        "grade_disponivel": grade_disponivel or "",
        "Data":             _parse_display_date(data_criacao),
    }

    # ------------------ Tecidos (NUNCA citar colunas inexistentes) ------------------
    # Se não houver 'codigo_tecido', tenta 'codigo'; se não houver nenhuma, usa NULL AS codigo
    t_codigo = _pick_col_expr("cadastro_modelos_tecidos", ["codigo_tecido", "codigo"], "codigo")
    tecidos_rows = _exec_all(f"""
        SELECT
            {t_codigo},
            COALESCE(descricao, '') AS descricao,
            COALESCE(cor, '')       AS cor,
            COALESCE(fornecedor,'') AS fornecedor,
            COALESCE(composicao,'') AS composicao,
            COALESCE(metros_peca, 0)  AS mpeca,
            COALESCE(valor_metro, 0)  AS vmetro,
            COALESCE(valor_total, 0)  AS vtotal
          FROM cadastro_modelos_tecidos
         WHERE cadastro_id = %s
         ORDER BY id ASC
    """, (cad_id,))
    tecidos = [{
        "Código":        r[0],
        "Descrição":     r[1],
        "Cor":           r[2],
        "Fornecedor":    r[3],
        "Composição":    r[4],
        "Metros/Peça":   _to_str(r[5]),
        "Valor Metro":   _to_str(r[6]),
        "valor_total":   _to_str(r[7]),
    } for r in tecidos_rows]

    # ------------------ Aviamentos (idem: codigo_aviamento/codigo) ------------------
    a_codigo = _pick_col_expr("cadastro_modelos_aviamentos", ["codigo_aviamento", "codigo"], "codigo")
    av_rows = _exec_all(f"""
        SELECT
            {a_codigo},
            COALESCE(descricao,'') AS descricao,
            COALESCE(cor,'')       AS cor,
            COALESCE(fornecedor,'') AS fornecedor,
            COALESCE(quantidade, 0)    AS qtd,
            COALESCE(valor_unidade, 0) AS vun,
            COALESCE(valor_total, 0)   AS vtot
          FROM cadastro_modelos_aviamentos
         WHERE cadastro_id = %s
         ORDER BY id ASC
    """, (cad_id,))
    aviamentos = [{
        "Código":         r[0],
        "Descrição":      r[1],
        "Cor":            r[2],
        "Fornecedor":     r[3],
        "Quantidade":     _to_str(r[4]),
        "Valor Unidade":  _to_str(r[5]),
        "valor_total":    _to_str(r[6]),
    } for r in av_rows]

    # ------------------ Outros (detecta qual tabela você está usando) ------------------
    outros_tbl = "cadastro_modelos_outros_servicos" if _table_exists("cadastro_modelos_outros_servicos") \
                  else "cadastro_modelos_outros"
    outros_rows = _exec_all(f"SELECT * FROM {outros_tbl} WHERE cadastro_id = %s ORDER BY id ASC", (cad_id,))
    outros = []
    if outros_rows:
        cols = [c[0] for c in _exec_all("""
            SELECT a.attname
              FROM pg_attribute a
              JOIN pg_class t ON a.attrelid = t.oid
              JOIN pg_namespace n ON t.relnamespace = n.oid
             WHERE n.nspname = current_schema()
               AND t.relname = %s
               AND a.attnum > 0
             ORDER BY a.attnum
        """, (outros_tbl,))]
        for row in outros_rows:
            m = {cols[i]: row[i] for i in range(min(len(cols), len(row)))}
            outros.append({
                "codigo":     (m.get("codigo_servico") or m.get("codigo") or ""),
                "descricao":  (m.get("descricao") or m.get("tipo_servico") or ""),
                "cor":        m.get("cor", ""),
                "unidade":    m.get("unidade", "un"),
                "fornecedor": m.get("fornecedor", ""),
                "preco":      _to_str(m.get("valor_unidade", 0)),
                "quantidade": _to_str(m.get("quantidade", 0)),
                "total":      _to_str(m.get("valor_total", 0)),
            })

    # ------------------ Imagens (tipo_imagem/caminho_imagem com fallback) ------------------
    tipo_col = "tipo_imagem" if _has_column("cadastro_modelos_imagens", "tipo_imagem") else "tipo"
    if   _has_column("cadastro_modelos_imagens", "caminho_imagem"): path_col = "caminho_imagem"
    elif _has_column("cadastro_modelos_imagens", "caminho"):        path_col = "caminho"
    elif _has_column("cadastro_modelos_imagens", "imagem"):         path_col = "imagem"
    else:                                                           path_col = None

    imagens_modelo = {"frente": None, "costas": None}
    imgs_t, imgs_a, imgs_o = [], [], []
    encontrou_db = False

    if path_col:
        img_rows = _exec_all(f"""
            SELECT {tipo_col}, {path_col}
              FROM cadastro_modelos_imagens
             WHERE cadastro_id = %s
             ORDER BY id ASC
        """, (cad_id,))
        for tipo, caminho in img_rows:
            if not caminho:
                continue
            encontrou_db = True
            t = str(tipo or "").lower()
            if t == "frente":
                imagens_modelo["frente"] = caminho
            elif t == "costas":
                imagens_modelo["costas"] = caminho
            elif t.startswith("tecido"):
                imgs_t.append(caminho)
            elif t.startswith("aviamento"):
                imgs_a.append(caminho)
            else:
                imgs_o.append(caminho)

    # Fallback de arquivos se não houver registros de imagens no banco
    if not encontrou_db:
        try:
            base_dirs = []
            current_dir = os.path.dirname(os.path.abspath(__file__))
            for c in [
                os.path.join(current_dir, "BANCO DE DADOS"),
                os.path.join(current_dir, "BANCO_DE_DADOS"),
                os.path.join(current_dir, "..", "BANCO DE DADOS"),
                os.path.join(current_dir, "..", "BANCO_DE_DADOS"),
            ]:
                if os.path.isdir(c):
                    base_dirs.append(c)
            base_dir = base_dirs[0] if base_dirs else None
            if base_dir:
                fr_dirs, co_dirs, te_dirs, av_dirs, ou_dirs = [], [], [], [], []
                for root, dirs, files in os.walk(base_dir):
                    name = os.path.basename(root).lower()
                    if "frente" in name or "front" in name: fr_dirs.append(root)
                    if "costas" in name or "back"  in name: co_dirs.append(root)
                    if "tecido" in name:                    te_dirs.append(root)
                    if "aviamento" in name:                 av_dirs.append(root)
                    if "outro" in name:                     ou_dirs.append(root)

                def busca(dirs):
                    out, codigo_lower = [], (codigo or "").lower()
                    valid = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
                    for d in dirs:
                        for f in os.listdir(d):
                            if f.lower().endswith(valid):
                                path = os.path.join(d, f)
                                if codigo_lower and codigo_lower in f.lower():
                                    out.insert(0, path)
                                else:
                                    out.append(path)
                    return out

                fr = busca(fr_dirs); co = busca(co_dirs)
                if fr: imagens_modelo["frente"] = fr[0]
                if co: imagens_modelo["costas"] = co[0]
                imgs_t = busca(te_dirs); imgs_a = busca(av_dirs); imgs_o = busca(ou_dirs)
        except Exception:
            pass

    return (dados, tecidos, aviamentos, outros, imagens_modelo, imgs_t, imgs_a, imgs_o)




# =============================================================
# AÇÃO: ABRIR/IMPRIMIR PDF
# =============================================================
def abrir_ou_imprimir_pdf(pdf_path: str, imprimir: bool = True, printer: str | None = None):
    """
    Abre ou imprime o PDF usando o aplicativo adequado.
    - No Windows: tenta os.startfile(..., 'print') e depois vários visualizadores (SumatraPDF, Adobe, Foxit).
    - macOS/Linux: apenas abre o arquivo no app padrão.
    """
    pdf_path = os.path.abspath(pdf_path)

    if platform.system() == "Windows":
        if imprimir:
            ok = imprimir_pdf_windows(pdf_path, printer=printer)
            if ok:
                return
        # fallback: só abrir
        try:
            os.startfile(pdf_path)
            return
        except Exception:
            pass

        # fallback final: abrir pasta com o arquivo selecionado
        try:
            subprocess.run(["explorer", "/select,", pdf_path], check=False)
            return
        except Exception:
            pass

        messagebox.showwarning(
            "Aviso",
            f"Não foi possível abrir/imprimir automaticamente.\nArquivo salvo em:\n{pdf_path}"
        )
        return

    # macOS / Linux
    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", pdf_path], check=False)
        else:
            subprocess.run(["xdg-open", pdf_path], check=False)
    except Exception:
        messagebox.showwarning(
            "Aviso",
            f"Não foi possível abrir automaticamente.\nArquivo salvo em:\n{pdf_path}"
        )


def imprimir_pdf_windows(pdf_path: str, printer: str | None = None) -> bool:
    """
    Tenta imprimir no Windows de forma robusta.
    1) os.startfile(path, 'print')
    2) SumatraPDF (se instalado)
    3) Adobe Reader / Acrobat (vários caminhos possíveis)
    4) Foxit (vários caminhos)
    Retorna True se algum método foi disparado sem erro imediato.
    """
    pdf_path = os.path.abspath(pdf_path)

    # 1) Verbo print do Shell (depende do app padrão de PDF registrar "print")
    try:
        os.startfile(pdf_path, "print")
        return True
    except Exception:
        pass

    # 2–4) Visualizadores conhecidos
    viewers = [
        # SumatraPDF
        r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
        r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",

        # Adobe Reader / Acrobat (variantes comuns)
        r"C:\Program Files\Adobe\Acrobat Reader\Reader\AcroRd32.exe",
        r"C:\Program Files (x86)\Adobe\Acrobat Reader\Reader\AcroRd32.exe",
        r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
        r"C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\Acrobat.exe",

        # Foxit Reader
        r"C:\Program Files\Foxit Software\Foxit PDF Reader\FoxitPDFReader.exe",
        r"C:\Program Files (x86)\Foxit Software\Foxit PDF Reader\FoxitPDFReader.exe",
        r"C:\Program Files\Foxit Reader\Foxit Reader.exe",
        r"C:\Program Files (x86)\Foxit Reader\Foxit Reader.exe",
    ]

    CREATE_NO_WINDOW = 0x08000000

    for exe in viewers:
        if not os.path.isfile(exe):
            continue
        try:
            if "SumatraPDF" in exe:
                cmd = [exe, "-print-to-default", "-silent", "-exit-on-print", pdf_path]

            elif ("Acrobat" in exe) or ("AcroRd32" in exe):
                if printer:
                    # /t <file> <printer> <driver> <port>
                    cmd = [exe, "/t", pdf_path, printer, "", ""]
                else:
                    cmd = [exe, "/p", "/h", pdf_path]

            elif "Foxit" in exe:
                if printer:
                    cmd = [exe, "/t", pdf_path, printer]
                else:
                    cmd = [exe, "/p", pdf_path]
            else:
                continue

            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW
            )
            return True
        except Exception:
            continue

    return False


# =============================================================
# UI: PÁGINA DE IMPRESSÃO
# =============================================================
class ImprimirFichasTecnicasPage(ctk.CTkFrame):
    TRANSLATIONS = {
     "pt_BR":{"title":"IMPRIMIR FICHAS TÉCNICAS (layout idêntico ao CADASTRAR_MODELO)","search_label":"Pesquisar:","search_placeholder":"Código, descrição ou coleção...","search":"Buscar","clear":"Limpar","print_sheet":"Imprimir Ficha","save_pdf":"Salvar PDF...","refresh":"Atualizar Lista","col_code":"Código","col_description":"Descrição","col_collection":"Coleção","col_base_size":"Tamanho Base","col_date":"Data","warning":"Aviso","error":"Erro","info":"Informação"},
     "en_US":{"title":"PRINT TECHNICAL SHEETS (same layout as CADASTRAR_MODELO)","search_label":"Search:","search_placeholder":"Code, description or collection...","search":"Search","clear":"Clear","print_sheet":"Print Sheet","save_pdf":"Save PDF...","refresh":"Refresh List","col_code":"Code","col_description":"Description","col_collection":"Collection","col_base_size":"Base Size","col_date":"Date","warning":"Warning","error":"Error","info":"Information"},
     "es_ES":{"title":"IMPRIMIR FICHAS TÉCNICAS (mismo diseño que CADASTRAR_MODELO)","search_label":"Buscar:","search_placeholder":"Código, descripción o colección...","search":"Buscar","clear":"Limpiar","print_sheet":"Imprimir Ficha","save_pdf":"Guardar PDF...","refresh":"Actualizar Lista","col_code":"Código","col_description":"Descripción","col_collection":"Colección","col_base_size":"Talla Base","col_date":"Fecha","warning":"Aviso","error":"Error","info":"Información"}
    }
    def _init_i18n(self):
        self.idioma_atual = getattr(self.sistema, "idioma_atual", "pt_BR")
    def _get_text(self, key, default=None):
        lang = getattr(self, "idioma_atual", "pt_BR")
        return self.TRANSLATIONS.get(lang, {}).get(key, self.TRANSLATIONS["pt_BR"].get(key, default if default is not None else key))
    def refresh_texts(self):
        for n,k in [("title_label","title"),("search_label","search_label"),("search_btn","search"),("clear_btn","clear"),("print_btn","print_sheet"),("save_pdf_btn","save_pdf"),("refresh_btn","refresh")]:
            try: getattr(self,n).configure(text=self._get_text(k))
            except Exception: pass
        try: self.search_entry.configure(placeholder_text=self._get_text("search_placeholder"))
        except Exception: pass
        try:
            for col,key in [("Código","col_code"),("Descrição","col_description"),("Coleção","col_collection"),("Tamanho Base","col_base_size"),("Data","col_date")]:
                self.tree.heading(col, text=self._get_text(key))
        except Exception: pass
    def __init__(self, master=None, sistema=None):
        super().__init__(master, fg_color=getattr(sistema, 'cor_fundo', '#0F0F0F') if sistema else '#0F0F0F')
        self.sistema = sistema
        self._init_i18n()
        self._build_ui()
        self.refresh_texts()
        self._carregar_modelos()

    # -------------------- UI --------------------
    def _build_ui(self):
        cor_texto = getattr(self.sistema, 'cor_texto', '#FFFFFF') if self.sistema else '#FFFFFF'
        cor_prim = getattr(self.sistema, 'cor_primaria', '#1F6FEB') if self.sistema else '#1F6FEB'
        cor_hover = getattr(self.sistema, 'cor_hover', '#2A2A2A') if self.sistema else '#2A2A2A'
        cor_borda = getattr(self.sistema, 'cor_borda', '#2F2F2F') if self.sistema else '#2F2F2F'

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self, text="IMPRIMIR FICHAS TÉCNICAS (layout idêntico ao CADASTRAR_MODELO)",
                             font=("Arial, Helvetica, sans-serif", 18, "bold"), text_color=cor_texto)
        self.title_label.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        ctk.CTkFrame(self, height=2, fg_color=cor_borda).grid(row=0, column=0, sticky="ew", padx=10, pady=(42, 8))

        search = ctk.CTkFrame(self, fg_color="transparent")
        search.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        search.grid_columnconfigure(1, weight=1)

        self.search_label = ctk.CTkLabel(search, text="Pesquisar:", font=("Arial", 13), text_color=cor_texto); self.search_label.grid(row=0, column=0, padx=(0, 6))
        self.search_entry = ctk.CTkEntry(search, placeholder_text="Código, descrição ou coleção...", height=34)
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self._pesquisar())

        self.search_btn = ctk.CTkButton(search, text="Buscar", command=self._pesquisar, fg_color=cor_prim, hover_color=cor_hover); self.search_btn.grid(row=0, column=2, padx=(8, 0))
        self.clear_btn = ctk.CTkButton(search, text="Limpar", command=self._limpar_busca); self.clear_btn.grid(row=0, column=3, padx=(8, 0))

        table_frame = ctk.CTkFrame(self, fg_color="transparent")
        table_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("Código", "Descrição", "Coleção", "Tamanho Base", "Data")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse", height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140 if c != "Descrição" else 260, anchor="w")
        self.tree.column("Código", width=120)
        self.tree.column("Data", width=120)

        yscroll = ctk.CTkScrollbar(table_frame, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns", padx=(4, 0))

        self.tree.bind("<Double-1>", lambda e: self._imprimir_selecionado())

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 12))
        self.print_btn = ctk.CTkButton(actions, text="Imprimir Ficha", command=self._imprimir_selecionado, fg_color=cor_prim, hover_color=cor_hover); self.print_btn.pack(side="left", padx=(0, 8))
        self.save_pdf_btn = ctk.CTkButton(actions, text="Salvar PDF...", command=self._salvar_pdf); self.save_pdf_btn.pack(side="left", padx=(0, 8))
        self.refresh_btn = ctk.CTkButton(actions, text="Atualizar Lista", command=self._carregar_modelos); self.refresh_btn.pack(side="left", padx=(0, 8))

    # -------------------- Dados / ações --------------------
    def _carregar_modelos(self):
        """Carrega até 300 modelos para a Treeview, formatando a data para exibição."""
        self.tree.delete(*self.tree.get_children())
        try:
            rows = _exec_all("""
                SELECT codigo, descricao, colecao, tamanho_base,
                       COALESCE(TO_CHAR(COALESCE(data_criacao::timestamp, NOW()), 'YYYY-MM-DD'),'') AS data_criacao
                  FROM cadastro_modelos_cabecalho
                 ORDER BY COALESCE(data_criacao::timestamp, NOW()) DESC, codigo DESC
                 LIMIT 300
            """)
            for r in rows:
                r = list(r)
                r[4] = _parse_display_date(r[4])
                self.tree.insert("", "end", values=r)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar modelos:\n{e}")

    def _pesquisar(self):
        """Pesquisa por código, descrição ou coleção e preenche a lista."""
        termo = (self.search_entry.get() or "").strip()
        self.tree.delete(*self.tree.get_children())
        if not termo:
            self._carregar_modelos()
            return
        try:
            like = f"%{termo}%"
            rows = _exec_all("""
                SELECT codigo, descricao, colecao, tamanho_base,
                       COALESCE(TO_CHAR(COALESCE(data_criacao::timestamp, NOW()), 'YYYY-MM-DD'),'') AS data_criacao
                  FROM cadastro_modelos_cabecalho
                 WHERE codigo ILIKE %s OR descricao ILIKE %s OR colecao ILIKE %s
                 ORDER BY COALESCE(data_criacao::timestamp, NOW()) DESC, codigo DESC
                 LIMIT 300
            """, (like, like, like))
            for r in rows:
                r = list(r)
                r[4] = _parse_display_date(r[4])
                self.tree.insert("", "end", values=r)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na pesquisa:\n{e}")

    def _limpar_busca(self):
        """Limpa o campo de busca e recarrega a lista."""
        self.search_entry.delete(0, tk.END)
        self._carregar_modelos()

    def _get_codigo(self) -> Optional[str]:
        """Retorna o código selecionado na Treeview, ou None se nada selecionado."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Selecione um modelo na tabela.")
            return None
        return self.tree.item(sel[0], "values")[0]

    def _imprimir_selecionado(self):
        """Gera o PDF no layout do CADASTRAR_MODELO e envia para impressão/abertura."""
        codigo = self._get_codigo()
        if not codigo:
            return
        blocos = carregar_dados_modelo(codigo)
        if not blocos:
            return
        dados, tecidos, aviamentos, outros, imgs_modelo, imgs_t, imgs_a, imgs_o = blocos
        try:
            pdf_path = gerar_pdf_cadastro_modelo_exato(
                dados=dados,
                tecidos=tecidos,
                aviamentos=aviamentos,
                outros=outros,
                imagens_modelo=imgs_modelo,
                imagens_tecidos=imgs_t,
                imagens_aviamentos=imgs_a,
                imagens_outros=imgs_o,
            )
            if os.path.exists(pdf_path):
                abrir_ou_imprimir_pdf(pdf_path, imprimir=True)
            else:
                messagebox.showerror("Erro", "Falha ao gerar o PDF.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar/imprimir PDF:\n{e}")

    def _salvar_pdf(self):
        """Gera o PDF e permite escolher onde salvar o arquivo."""
        codigo = self._get_codigo()
        if not codigo:
            return
        blocos = carregar_dados_modelo(codigo)
        if not blocos:
            return
        dados, tecidos, aviamentos, outros, imgs_modelo, imgs_t, imgs_a, imgs_o = blocos
        try:
            pdf_path = gerar_pdf_cadastro_modelo_exato(
                dados=dados,
                tecidos=tecidos,
                aviamentos=aviamentos,
                outros=outros,
                imagens_modelo=imgs_modelo,
                imagens_tecidos=imgs_t,
                imagens_aviamentos=imgs_a,
                imagens_outros=imgs_o,
            )
            destino = filedialog.asksaveasfilename(
                title="Salvar Ficha Técnica",
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")]
            )
            if destino:
                import shutil
                shutil.copyfile(pdf_path, destino)
                messagebox.showinfo("Sucesso", f"PDF salvo em:\n{destino}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar PDF:\n{e}")

# =============================================================
# EXECUÇÃO DIRETA
# =============================================================
if __name__ == "__main__":
    # Só executa a interface gráfica se customtkinter ou tkinter estiverem disponíveis
    if hasattr(ctk, "CTk"):
        # Chama require_ready sem argumentos; algumas versões não aceitam parâmetros
        try:
            ok, msg = require_ready()
        except TypeError:
            # Compatibilidade com assinatura que aceita lista
            try:
                ok, msg = require_ready([
                    'cadastro_modelos_cabecalho',
                    'cadastro_modelos_tecidos',
                    'cadastro_modelos_aviamentos'
                ])
            except Exception:
                ok, msg = False, "Problema ao conectar ao banco."
        if not ok:
            try:
                messagebox.showwarning("Banco de Dados", f"Problema ao conectar ao PostgreSQL:\n{msg}")
            except Exception:
                print(f"Problema ao conectar ao PostgreSQL:\n{msg}")

        try:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")
        except Exception:
            pass

        root = ctk.CTk()
        root.title("Imprimir Fichas Técnicas")
        root.geometry("980x640")

        page = ImprimirFichasTecnicasPage(root)
        page.pack(fill="both", expand=True)

        root.mainloop()
    else:
        # Se a biblioteca de interface não estiver disponível, apenas informa que o módulo foi carregado
        print("Módulo IMPRIMIR_FICHAS_TECNICAS carregado. Interface gráfica desativada pela ausência de customtkinter/tkinter.")
