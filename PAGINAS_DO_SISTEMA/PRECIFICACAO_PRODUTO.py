# -*- coding: utf-8 -*-
"""
PRECIFICACAO_PRODUTO_v2.py
Tela PROFISSIONAL de Precificação de Produto (CustomTkinter).

- Perfis nomeados, presets de canal, arredondamento psicológico
- BOM (itens) com soma, lote planejado, escada de margens (CSV)
- Relatório de PRÉ-CUSTO em HTML, pronto para imprimir
"""

from __future__ import annotations
from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db

# ------------------------- IMPORTS BÁSICOS -------------------------
import os, csv, math, datetime, webbrowser, sys
import psycopg2, psycopg2.extras
from typing import List, Dict, Tuple, Optional

# UI
try:
    import customtkinter as ctk
    from tkinter import messagebox, simpledialog
except Exception:
    raise SystemExit("Este arquivo requer 'customtkinter'. Instale com:  pip install customtkinter")

# --------------------- LOCALIZAÇÃO DO BANCO -----------------------
# Procura o factory.db em locais comuns do seu projeto
DB_CANDIDATES = [
    os.path.join(os.getcwd(), "BANCO DE DADOS", "factory.db"),
    os.path.join(os.path.dirname(__file__), "BANCO DE DADOS", "factory.db"),
    os.path.join(os.getcwd(), "factory.db"),
    "factory.db",
]


def _find_db() -> str:
    for p in DB_CANDIDATES:
        if os.path.exists(p):
            return p
    # fallback: assume o primeiro caminho (BANCO DE DADOS/factory.db na pasta atual)
    return DB_CANDIDATES[0]


DB_PATH = _find_db()

# Diretório-base onde está o banco (normalmente ".../BANCO DE DADOS")
DB_DIR = os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else os.getcwd()

# ---------------- CRIA PASTA DE RELATÓRIOS (logo ao abrir) ----------------
# Todos os relatórios de PRÉ-CUSTO vão para:
#   BANCO DE DADOS/RELATORIO_PRE_CUSTO/
RELATORIO_PRE_CUSTO_DIR = os.path.join(DB_DIR, "RELATORIO_PRE_CUSTO")
os.makedirs(RELATORIO_PRE_CUSTO_DIR, exist_ok=True)

# ------------------------- PG CONEXÃO -------------------------
# ------------------------- PG CONEXÃO -------------------------
# Usa exclusivamente o módulo central BANCO_DE_DADOS_PG
try:
    from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as pg
except Exception as e:
    raise SystemExit(f"Falha ao carregar BANCO_DE_DADOS_PG: {e}")

import psycopg2, psycopg2.extras  # seguimos usando cursores dict para esta tela

# Healthcheck + schema
try:
    ok, msg = pg.require_ready()
    if ok:
        print("✅ PostgreSQL conectado com sucesso!")
    else:
        print(f"⚠️ PostgreSQL não disponível: {msg}")
except Exception as e:
    print(f"❌ Erro ao testar PostgreSQL: {e}")

SCHEMA = pg.get_schema()  # ex.: "opera"


def _connect():
    """
    Retorna uma conexão pronta do módulo PG.
    O módulo já definiu o search_path (ex.: 'opera, public') de forma segura.
    """
    return pg.get_connection()


def _run(cur, sql: str, params=None):
    """
    Executa SQL no cursor informado (mantém compat com chamadas existentes).
    """
    cur.execute(sql, params or ())


# ------------------ Consultas utilitárias -------------------------------------
def _get_models(conn):
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            _run(cur, """
                SELECT codigo, COALESCE(descricao, '') AS descricao
                  FROM cadastro_modelos_cabecalho
                 ORDER BY codigo
            """)
            rows = cur.fetchall()
            return [(r["codigo"], r["descricao"]) for r in rows]
    except Exception:
        return []


def _get_model_header_cost(conn, codigo: str) -> float:
    """Custo de materiais/aviamentos do cabeçalho (vários nomes possíveis)."""
    col_candidates = ["custo_total_materiais", "custo_total", "total_gasto", "valor_total", "custo"]
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            _run(cur, """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
            """, (pg.get_schema(), "cadastro_modelos_cabecalho"))  # ← CORRETO
            available = {r["column_name"] for r in cur.fetchall()}
    except Exception:
        available = set()
    pick = [c for c in col_candidates if c in available] or col_candidates
    cols = ", ".join([f"COALESCE({c}, 0) AS {c}" for c in pick])
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            _run(cur, f"""
                SELECT {cols}
                  FROM cadastro_modelos_cabecalho
                 WHERE codigo = %s
                 LIMIT 1
            """, (codigo,))
            row = cur.fetchone()
            if not row: return 0.0
            for c in pick:
                try:
                    v = float(row.get(c) or 0.0)
                except Exception:
                    v = 0.0
                if v > 0: return v
            try:
                return max(float(row.get(c) or 0.0) for c in pick)
            except Exception:
                return 0.0
    except Exception:
        return 0.0


def _get_sewing_cost(conn, codigo: str) -> float:
    """Valor por peça a pagar (tabela controle_envio_cortes)."""
    value_expr = "COALESCE(valor_peca, valor_por_peca, valor_unitario, valor, 0)"
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            _run(cur, f"""
                SELECT {value_expr} AS v
                  FROM controle_envio_cortes
                 WHERE codigo = %s
                 ORDER BY NULLIF(data_envio::date, NULL) DESC NULLS LAST, id DESC
                 LIMIT 1
            """, (codigo,))
            row = cur.fetchone()
            if row and row.get("v") not in (None, ""):
                return float(row["v"])
    except Exception:
        pass
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            _run(cur, f"""
                SELECT {value_expr} AS v
                  FROM controle_envio_cortes
                 WHERE codigo = %s
                 ORDER BY id DESC
                 LIMIT 1
            """, (codigo,))
            row = cur.fetchone()
            if row and row.get("v") not in (None, ""):
                return float(row["v"])
    except Exception:
        pass
    if codigo == "MDL-003": return 19.0
    if codigo == "MDL-004": return 21.0
    return 0.0


def _get_bom_items(conn, codigo: str):
    """Busca itens da BOM (tecidos e aviamentos) em tabelas comuns do seu sistema."""
    results = []
    candidates = [
        ("cadastro_modelos_itens", dict(item="descricao", qtd="quantidade", un="unidade", custo_unit="custo_unitario")),
        ("cadastro_modelos_tecidos", dict(item="tecido", qtd="quantidade", un="unidade", custo_unit="custo_unitario")),
        ("cadastro_modelos_aviamentos",
         dict(item="aviamento", qtd="quantidade", un="unidade", custo_unit="custo_unitario")),
        ("cadastro_modelos_componentes",
         dict(item="componente", qtd="quantidade", un="unidade", custo_unit="custo_unitario")),
        ("cadastro_modelos_outros", dict(item="descricao", qtd="quantidade", un="unidade", custo_unit="valor_unidade")),
    ]
    for table, cols in candidates:
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                _run(cur, """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                """, (pg.get_schema(), "cadastro_modelos_cabecalho"))  # ← CORRETO

                _run(cur, """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema=%s AND table_name=%s
                """, (pg.get_schema(), table))  # ← ADICIONAR pg.get_schema() AQUI
                names = {r["column_name"] for r in cur.fetchall()}
                if not names:
                    continue
                where = "codigo = %s";
                params = (codigo,)
                if "cadastro_id" in names and "codigo" not in names:
                    _run(cur, "SELECT id FROM cadastro_modelos_cabecalho WHERE codigo=%s", (codigo,))
                    r = cur.fetchone()
                    if not r:
                        continue
                    cadastro_id = r["id"]
                    where = f"cadastro_id = {cadastro_id}";
                    params = ()

                sel = [f"COALESCE({v}, '') AS {k}" for k, v in cols.items() if v in names]
                sel.append(
                    "COALESCE(custo_total, NULL) AS custo_total_col" if "custo_total" in names else "NULL AS custo_total_col")
                sql = f"SELECT {', '.join(sel)} FROM {table} WHERE {where}"
                _run(cur, sql, params)
                rows = cur.fetchall()
                for r in rows:
                    item = {
                        "tipo": table.replace("cadastro_modelos_", ""),
                        "item": r.get("item", ""),
                        "qtd": float(_safe_float(r.get("qtd"))) if "qtd" in r else 0.0,
                        "un": r.get("un", ""),
                        "custo_unit": float(_safe_float(r.get("custo_unit"))) if "custo_unit" in r else 0.0,
                    }
                    if r.get("custo_total_col") not in (None, ""):
                        item["custo_total"] = float(_safe_float(r.get("custo_total_col")))
                    else:
                        item["custo_total"] = item["qtd"] * item["custo_unit"]
                    results.append(item)
        except Exception:
            continue
    return results


def _safe_float(v) -> float:
    try:
        return float(str(v).replace(",", ".").strip()) if v not in (None, "") else 0.0
    except Exception:
        return 0.0


# ------------------ Página ----------------------------------------------------
class PrecificacaoProdutoPage(ctk.CTkFrame):
    PAGE_TITLE = "Precificação de Produto"

    CHANNEL_PRESETS = {
        "Varejo (Loja)": dict(comissao=0.0, cartao=3.5),
        "Atacado": dict(comissao=0.0, cartao=1.5),
        "E-commerce": dict(comissao=0.0, cartao=4.0),
        "Marketplace": dict(comissao=12.0, cartao=0.0),
    }

    ROUNDING_MODES = [
        "Sem arredondamento",
        "Terminar em .90 (para cima)",
        "Terminar em .99 (para cima)",
        "Múltiplo de 0,50 (para cima)",
        "Múltiplo de 1,00 (para cima)",
        "Múltiplo de 5,00 (para cima)",
        "Múltiplo de 10,00 (para cima)",
    ]

    def __init__(self, master, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema

        # === APLICAR CORES AO FRAME PRINCIPAL ===
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

        self._build_ui()
        self._apply_role_colors(self)
        self._load_defaults()
        # seleção inicial
        values = self.cmb_modelo.cget("values")
        target = "MDL-003"
        if isinstance(values, (list, tuple)) and target in values:
            self.cmb_modelo.set(target)
        elif values:
            self.cmb_modelo.set(values[0])
        self._on_model_change()
        try:
            self.refresh_texts()
        except Exception:
            pass


    # ---------- UI
    def _build_ui(self):
        # Frame principal com tema
        main = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        main.grid_rowconfigure(99, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # Cabeçalho - COM TEMA
        header = ctk.CTkFrame(main, fg_color=self.cor_fundo)
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        header.grid_columnconfigure(7, weight=1)

        ctk.CTkLabel(header, text=self.PAGE_TITLE, font=("Arial", 20, "bold"),
                     text_color=self.cor_texto).grid(row=0, column=0, padx=(0, 12), pady=6, sticky="w")

        ctk.CTkLabel(header, text="Modelo", text_color=self.cor_texto).grid(row=0, column=1, padx=6)

        # Combobox de modelo - COM TEMA
        self.cmb_modelo = ctk.CTkComboBox(
            header,
            values=self._load_model_values(),
            command=lambda _=None: self._on_model_change(),
            width=180,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover
        )
        self.cmb_modelo.grid(row=0, column=2, pady=6)

        self.lbl_desc = ctk.CTkLabel(header, text="-", anchor="w", text_color=self.cor_texto)
        self.lbl_desc.grid(row=0, column=3, padx=12, sticky="w")

        ctk.CTkButton(header, text="Recarregar", command=self._on_model_change,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).grid(row=0, column=4, padx=6)

        ctk.CTkLabel(header, text="Canal", text_color=self.cor_texto).grid(row=0, column=5, padx=(24, 6))

        # Combobox de canal - COM TEMA
        self.cmb_canal = ctk.CTkComboBox(
            header,
            values=list(self.CHANNEL_PRESETS.keys()),
            command=lambda _=None: self._apply_channel_preset(),
            width=160,
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover
        )
        self.cmb_canal.set("Varejo (Loja)")
        self.cmb_canal.grid(row=0, column=6, pady=6)

        # Tabs - COM TEMA
        tabs = ctk.CTkTabview(main, fg_color=self.cor_fundo, segmented_button_fg_color=self.cor_primaria,
                              segmented_button_selected_color=self.cor_selecao,
                              segmented_button_selected_hover_color=self.cor_hover,
                              text_color=self.cor_texto)
        tabs.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.tab_resumo = tabs.add("Resumo")
        self.tab_custos = tabs.add("Custos")
        self.tab_impostos = tabs.add("Impostos & Margem")
        self.tab_simul = tabs.add("Simulações")
        self.tab_bom = tabs.add("BOM / Itens")
        self.tab_rel = tabs.add("Relatório")

        # Configurar cores das abas - CORREÇÃO APLICADA
        try:
            self.tab_resumo.configure(fg_color=self.cor_fundo)
            self.tab_custos.configure(fg_color=self.cor_fundo)
            self.tab_impostos.configure(fg_color=self.cor_fundo)
            self.tab_simul.configure(fg_color=self.cor_fundo)
            self.tab_bom.configure(fg_color=self.cor_fundo)
            self.tab_rel.configure(fg_color=self.cor_fundo)
        except AttributeError as e:
            print(f"Aviso: Não foi possível configurar todas as abas: {e}")

        # Vars
        self.v = dict(
            materiais=ctk.StringVar(value="0"),
            costura=ctk.StringVar(value="0"),
            fixos_mes=ctk.StringVar(value="0"),
            capacidade_mes=ctk.StringVar(value="1000"),
            overhead=ctk.StringVar(value="0"),
            variaveis=ctk.StringVar(value="0"),
            frete=ctk.StringVar(value="0"),

            impostos_pct=ctk.StringVar(value="12"),
            comissao_pct=ctk.StringVar(value="5"),
            cartao_pct=ctk.StringVar(value="3.5"),
            margem_pct=ctk.StringVar(value="15"),
            perdas_pct=ctk.StringVar(value="0"),
            defeito_pct=ctk.StringVar(value="0"),

            lote=ctk.StringVar(value="1"),

            custo_total=ctk.StringVar(value="0"),
            preco_sugerido=ctk.StringVar(value="0"),
            lucro_unit=ctk.StringVar(value="0"),
            markup=ctk.StringVar(value="0"),
            preco_alvo=ctk.StringVar(value="0"),
            margem_atingida=ctk.StringVar(value="0"),
            lote_be=ctk.StringVar(value="0"),

            arred_mode=ctk.StringVar(value="Sem arredondamento"),
        )

        # --- Resumo (cards grandes) ---
        self._card(self.tab_resumo, "Materiais (R$)", self.v["materiais"], 0, 0, big=True)
        self._card(self.tab_resumo, "Costura (R$)", self.v["costura"], 0, 1, big=True)
        self._card(self.tab_resumo, "Overhead/peça (R$)", self.v["overhead"], 1, 0)
        self._card(self.tab_resumo, "Custo Total (R$)", self.v["custo_total"], 1, 1, big=True)
        self._card(self.tab_resumo, "Preço Sugerido (R$)", self.v["preco_sugerido"], 2, 0, big=True)
        self._card(self.tab_resumo, "Lucro Unit. (R$)", self.v["lucro_unit"], 2, 1)
        self._card(self.tab_resumo, "Markup (x)", self.v["markup"], 3, 0)
        self._card(self.tab_resumo, "Lote Ponto de Equilíbrio", self.v["lote_be"], 3, 1)

        # --- Custos ---
        r = 0
        self._entry(self.tab_custos, "Materiais / Aviamentos (R$)", "materiais", r);
        r += 1
        self._entry(self.tab_custos, "Costura por peça (R$)", "costura", r);
        r += 1
        self._entry(self.tab_custos, "Custos fixos/mês (R$)", "fixos_mes", r);
        r += 1
        self._entry(self.tab_custos, "Capacidade/mês (peças)", "capacidade_mes", r);
        r += 1
        self._entry(self.tab_custos, "Overhead por peça (R$)", "overhead", r, readonly=True);
        r += 1
        self._entry(self.tab_custos, "Custos variáveis unit. (R$)", "variaveis", r);
        r += 1
        self._entry(self.tab_custos, "Frete / logística unit. (R$)", "frete", r);
        r += 1
        self._entry(self.tab_custos, "Perdas materiais (%)", "perdas_pct", r);
        r += 1
        self._entry(self.tab_custos, "Defeito / retrabalho (%)", "defeito_pct", r);
        r += 1
        self._entry(self.tab_custos, "Lote planejado (peças)", "lote", r);
        r += 1
        ctk.CTkButton(self.tab_custos, text="Calcular", command=self._recalc,
                      fg_color=self.cor_sucesso, hover_color=self.cor_hover,
                      text_color=self.cor_texto).grid(row=r, column=0, columnspan=2, sticky="ew", pady=8);
        r += 1

        # --- Impostos & Margem ---
        r = 0
        self._entry(self.tab_impostos, "Impostos (%)", "impostos_pct", r);
        r += 1
        self._entry(self.tab_impostos, "Comissão (%)", "comissao_pct", r);
        r += 1
        self._entry(self.tab_impostos, "Taxa cartão (%)", "cartao_pct", r);
        r += 1
        self._entry(self.tab_impostos, "Margem desejada (%)", "margem_pct", r);
        r += 1

        ctk.CTkLabel(self.tab_impostos, text="Arredondamento", text_color=self.cor_texto).grid(row=r, column=0, padx=6,
                                                                                               pady=4, sticky="w")

        # Combobox de arredondamento - COM TEMA
        self.cmb_round = ctk.CTkComboBox(
            self.tab_impostos,
            values=self.ROUNDING_MODES,
            width=220,
            command=lambda _=None: self._recalc(),
            fg_color=self.cor_secundaria,
            border_color=self.cor_borda,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            text_color=self.cor_texto,
            dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto,
            dropdown_hover_color=self.cor_hover
        )
        self.cmb_round.set(self.v["arred_mode"].get())
        self.cmb_round.grid(row=r, column=1, padx=6, pady=4, sticky="e");
        r += 1

        ctk.CTkButton(self.tab_impostos, text="Salvar perfil como...", command=self._save_profile_as,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).grid(row=r, column=0, columnspan=2, sticky="ew", pady=8);
        r += 1
        ctk.CTkButton(self.tab_impostos, text="Carregar perfil...", command=self._load_profile_pick,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, 8));
        r += 1

        # --- Simulações ---
        sim_frame = ctk.CTkFrame(self.tab_simul, fg_color=self.cor_fundo)
        sim_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        sim_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sim_frame, text="Escada de preços (margem %)", font=("Arial", 14, "bold"),
                     text_color=self.cor_texto).grid(row=0, column=0, pady=(4, 6))

        self._margins = [10, 15, 20, 25, 30, 40, 50]
        self._sim_table = ctk.CTkTextbox(sim_frame, width=520, height=200,
                                         fg_color=self.cor_terciaria, border_color=self.cor_borda,
                                         text_color=self.cor_texto)
        self._sim_table.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        tgt = ctk.CTkFrame(self.tab_simul, fg_color=self.cor_fundo)
        tgt.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        self._entry(tgt, "Preço alvo do mercado (R$)", "preco_alvo", 0)
        ctk.CTkButton(tgt, text="Analisar preço alvo", command=self._analisar_preco_alvo,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).grid(row=0, column=2, padx=6)
        ctk.CTkLabel(tgt, text="Margem atingida (%)", text_color=self.cor_texto).grid(row=0, column=3, padx=(18, 6))
        self._out_margem_atingida = ctk.CTkLabel(tgt, textvariable=self.v["margem_atingida"],
                                                 font=("Arial", 14, "bold"), text_color=self.cor_texto)
        self._out_margem_atingida.grid(row=0, column=4, padx=6)

        ctk.CTkButton(self.tab_simul, text="Exportar simulações CSV", command=self._export_csv,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 8))

        # --- BOM ---
        self._bom_table = ctk.CTkTextbox(self.tab_bom, width=700, height=320,
                                         fg_color=self.cor_terciaria, border_color=self.cor_borda,
                                         text_color=self.cor_texto)
        self._bom_table.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # --- Relatório ---
        rel_frame = ctk.CTkFrame(self.tab_rel, fg_color=self.cor_fundo)
        rel_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        rel_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(rel_frame, text="Relatório de Pré-Custo", font=("Arial", 16, "bold"),
                     text_color=self.cor_texto).grid(row=0, column=0, columnspan=2, pady=(6, 10), sticky="w")

        ctk.CTkButton(rel_frame, text="Gerar & Abrir HTML", command=self._gerar_relatorio,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).grid(row=1, column=0, padx=6, pady=4, sticky="ew")

        ctk.CTkButton(rel_frame, text="Imprimir (Windows)", command=self._imprimir_windows,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).grid(row=1, column=1, padx=6, pady=4, sticky="ew")

        ctk.CTkButton(rel_frame, text="Copiar preço sugerido", command=self._copy_price,
                      fg_color=self.cor_sucesso, hover_color=self.cor_hover,
                      text_color=self.cor_texto).grid(row=2, column=0, columnspan=2, padx=6, pady=6, sticky="ew")

        # watchers
        for key in ["materiais", "costura", "fixos_mes", "capacidade_mes", "variaveis", "frete", "perdas_pct",
                    "defeito_pct", "impostos_pct", "comissao_pct", "cartao_pct", "margem_pct", "lote"]:
            self.v[key].trace_add("write", lambda *_: self._recalc())

    # ---------- helpers de UI
    def _card(self, parent, title, var, row, col, big=False):
        frame = ctk.CTkFrame(parent, fg_color=self.cor_secundaria)
        frame.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=title, text_color=self.cor_texto).grid(row=0, column=0, pady=(8, 2))
        font = ("Arial", 24, "bold") if big else ("Arial", 18, "bold")
        ctk.CTkLabel(frame, textvariable=var, font=font, text_color=self.cor_texto).grid(row=1, column=0, pady=(0, 8))

    def _entry(self, parent, label, key, row, readonly=False):
        ctk.CTkLabel(parent, text=label, text_color=self.cor_texto).grid(row=row, column=0, padx=6, pady=4, sticky="w")
        state = "disabled" if readonly else "normal"
        e = ctk.CTkEntry(parent, textvariable=self.v[key], justify="right", width=220,
                         fg_color=self.cor_terciaria, border_color=self.cor_borda,
                         text_color=self.cor_texto, state=state,
                         placeholder_text_color="#888888")
        e.grid(row=row, column=1, padx=6, pady=4, sticky="e")
        return e

    def _load_model_values(self):
        try:
            conn = _connect()
            models = _get_models(conn)
        except Exception:
            models = []
        finally:
            try:
                conn.close()
            except Exception:
                pass
        prefer = [m for m in models if m[0] in ("MDL-003", "MDL-004")]
        others = [m for m in models if m[0] not in ("MDL-003", "MDL-004")]
        self._model_desc_map = {c: d for c, d in models}
        values = [c for c, _ in prefer] + [c for c, _ in others]
        return values

    # ---------- carregamento e cálculo
    def _on_model_change(self):
        codigo = self.cmb_modelo.get().strip()
        self.lbl_desc.configure(text=self._model_desc_map.get(codigo, "-"))
        try:
            conn = _connect()
            materiais = _get_model_header_cost(conn, codigo)
            costura = _get_sewing_cost(conn, codigo)
            bom = _get_bom_items(conn, codigo)
        except Exception:
            materiais, costura, bom = 0.0, 0.0, []
        finally:
            try:
                conn.close()
            except Exception:
                pass

        if codigo == "MDL-003" and (not costura or costura <= 0): costura = 19.0
        if codigo == "MDL-004" and (not costura or costura <= 0): costura = 21.0

        self._last_bom = bom
        self.v["materiais"].set(f"{materiais:.2f}")
        self.v["costura"].set(f"{costura:.2f}")
        self._render_bom(bom)
        self._recalc()

    def _render_bom(self, bom: List[Dict]):
        tb = self._bom_table
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        if not bom:
            tb.insert("end", "Sem itens de BOM localizados para este modelo.\n")
        else:
            tb.insert("end", f"{'Tipo':12} {'Item':35} {'Qtd':>8} {'Un':>4} {'C.Unit':>10} {'C.Total':>10}\n")
            tb.insert("end", "-" * 90 + "\n")
            for it in bom:
                tb.insert("end",
                          f"{it.get('tipo', ''):12} {it.get('item', '')[:35]:35} {it.get('qtd', 0):>8.2f} {it.get('un', ''):>4} {it.get('custo_unit', 0):>10.2f} {it.get('custo_total', 0):>10.2f}\n")
            tb.insert("end", "-" * 90 + "\n")
            soma = sum(it.get("custo_total", 0) for it in bom)
            tb.insert("end", f"{'':12} {'TOTAL ITENS':35} {'':8} {'':4} {'':10} {soma:>10.2f}\n")
        tb.configure(state="disabled")

    def _as_float(self, s) -> float:
        try:
            return float(str(s).replace("%", "").replace(",", ".").strip()) if str(s).strip() else 0.0
        except Exception:
            return 0.0

    def _apply_channel_preset(self):
        canal = self.cmb_canal.get()
        preset = self.CHANNEL_PRESETS.get(canal, {})
        if "comissao" in preset:
            self.v["comissao_pct"].set(str(preset["comissao"]))
        if "cartao" in preset:
            self.v["cartao_pct"].set(str(preset["cartao"]))
        self._recalc()

    def _round_price(self, val: float, mode: str) -> float:
        if mode == "Sem arredondamento":
            return val
        if val <= 0:
            return val
        import math
        if mode.startswith("Terminar em .90"):
            base = math.floor(val)
            r = base + 0.90
            return r if r >= val else base + 1 + 0.90
        if mode.startswith("Terminar em .99"):
            base = math.floor(val)
            r = base + 0.99
            return r if r >= val else base + 1 + 0.99

        def round_up_multiple(v, step):
            return math.ceil(v / step) * step

        if "0,50" in mode: return round_up_multiple(val, 0.50)
        if "1,00" in mode: return round_up_multiple(val, 1.00)
        if "5,00" in mode: return round_up_multiple(val, 5.00)
        if "10,00" in mode: return round_up_multiple(val, 10.00)
        return val

    def _recalc(self):
        materiais = self._as_float(self.v["materiais"].get())
        costura = self._as_float(self.v["costura"].get())
        fixos_mes = self._as_float(self.v["fixos_mes"].get())
        capacidade = max(1, int(self._as_float(self.v["capacidade_mes"].get())))
        variaveis = self._as_float(self.v["variaveis"].get())
        frete = self._as_float(self.v["frete"].get())
        perdas = self._as_float(self.v["perdas_pct"].get()) / 100.0
        defeito = self._as_float(self.v["defeito_pct"].get()) / 100.0
        lote = max(1, int(self._as_float(self.v["lote"].get())))

        impostos = self._as_float(self.v["impostos_pct"].get()) / 100.0
        comissao = self._as_float(self.v["comissao_pct"].get()) / 100.0
        cartao = self._as_float(self.v["cartao_pct"].get()) / 100.0
        margem = self._as_float(self.v["margem_pct"].get()) / 100.0
        mode = self.cmb_round.get()

        # perdas/defeito aplicados
        materiais_eff = materiais * (1 + perdas)
        custo_defeito = (materiais + costura) * defeito

        overhead = fixos_mes / capacidade if capacidade > 0 else 0.0
        custo_total = materiais_eff + costura + custo_defeito + overhead + variaveis + frete

        deducoes = impostos + comissao + cartao + margem
        if deducoes >= 0.99: deducoes = 0.99
        liquido = 1.0 - deducoes
        preco_raw = custo_total / liquido if liquido > 0 else 0.0
        preco = self._round_price(preco_raw, mode)
        lucro = preco - custo_total
        markup = (preco / custo_total) if custo_total > 0 else 0.0

        # ponto de equilíbrio aproximado por lote
        try:
            lucro_unit = lucro
            lote_be = math.ceil((fixos_mes / capacidade) / lucro_unit) if lucro_unit > 0 else 0
        except Exception:
            lote_be = 0

        self.v["overhead"].set(f"{overhead:.2f}")
        self.v["custo_total"].set(f"{custo_total:.2f}")
        self.v["preco_sugerido"].set(f"{preco:.2f}")
        self.v["lucro_unit"].set(f"{lucro:.2f}")
        self.v["markup"].set(f"{markup:.2f}x")
        self.v["lote_be"].set(f"{lote_be}")

        self._render_simulacoes(custo_total)

    def _render_simulacoes(self, custo_total: float):
        imp = self._as_float(self.v["impostos_pct"].get()) / 100.0
        com = self._as_float(self.v["comissao_pct"].get()) / 100.0
        car = self._as_float(self.v["cartao_pct"].get()) / 100.0
        tb = self._sim_table
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        tb.insert("end", f"{'Margem%':>8} {'Preço':>12} {'Lucro':>12} {'Markup':>8}\n")
        tb.insert("end", "-" * 50 + "\n")
        for m in self._margins:
            m_d = m / 100.0
            ded = imp + com + car + m_d
            if ded >= 0.99: ded = 0.99
            preco = custo_total / (1.0 - ded) if (1.0 - ded) > 0 else 0.0
            lucro = preco - custo_total
            markup = (preco / custo_total) if custo_total > 0 else 0.0
            tb.insert("end", f"{m:>8.0f} {preco:>12.2f} {lucro:>12.2f} {markup:>8.2f}\n")
        tb.configure(state="disabled")

    def _analisar_preco_alvo(self):
        preco_alvo = self._as_float(self.v["preco_alvo"].get())
        custo = self._as_float(self.v["custo_total"].get())
        if preco_alvo <= 0 or custo <= 0:
            messagebox.showinfo("Analisar", "Informe um preço alvo e recalcule os custos.")
            return
        imp = self._as_float(self.v["impostos_pct"].get()) / 100.0
        com = self._as_float(self.v["comissao_pct"].get()) / 100.0
        car = self._as_float(self.v["cartao_pct"].get()) / 100.0
        margem_real = (preco_alvo * (1 - (imp + com + car)) - custo) / preco_alvo
        self.v["margem_atingida"].set(f"{(margem_real * 100):.2f}%")

    def _export_csv(self):
        try:
            rows = [["Margem%", "Preço", "Lucro", "Markup"]]
            imp = self._as_float(self.v["impostos_pct"].get()) / 100.0
            com = self._as_float(self.v["comissao_pct"].get()) / 100.0
            car = self._as_float(self.v["cartao_pct"].get()) / 100.0
            custo_total = self._as_float(self.v["custo_total"].get())

            for m in self._margins:
                m_d = m / 100.0
                ded = imp + com + car + m_d
                if ded >= 0.99: ded = 0.99
                preco = custo_total / (1.0 - ded) if (1.0 - ded) > 0 else 0.0
                lucro = preco - custo_total
                markup = (preco / custo_total) if custo_total > 0 else 0.0
                rows.append([m, f"{preco:.2f}", f"{lucro:.2f}", f"{markup:.2f}"])

            out = os.path.join(os.getcwd(), "simulacoes_precos.csv")
            with open(out, "w", newline="", encoding="utf-8") as f:
                csv.writer(f, delimiter=";").writerows(rows)
            messagebox.showinfo("Exportar", f"Arquivo salvo:\n{out}")
        except Exception as e:
            messagebox.showerror("Exportar", f"Falha ao exportar CSV:\n{e}")

    # ---------- perfis (gravação no banco local)
    def _ensure_profile_table(self, conn):
        """Removido: criação/migração de tabelas foi movida para BANCO_DE_DADOS.
        Esta função agora é um no-op para evitar qualquer CREATE TABLE a partir da UI."""
        return

    def _save_profile_as(self):
        nome = simpledialog.askstring("Salvar perfil", "Nome do perfil:")
        if not nome:
            return
        try:
            conn = _connect()
            self._ensure_profile_table(conn)
            conn.execute("""
                INSERT INTO pricing_profiles (nome, impostos, comissao, cartao, margem, perdas, defeito, fixos, capacidade, variaveis, frete, arredondamento, canal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(nome) DO UPDATE SET
                    impostos=excluded.impostos,
                    comissao=excluded.comissao,
                    cartao=excluded.cartao,
                    margem=excluded.margem,
                    perdas=excluded.perdas,
                    defeito=excluded.defeito,
                    fixos=excluded.fixos,
                    capacidade=excluded.capacidade,
                    variaveis=excluded.variaveis,
                    frete=excluded.frete,
                    arredondamento=excluded.arredondamento,
                    canal=excluded.canal
            """, (
                nome,
                self._as_float(self.v["impostos_pct"].get()),
                self._as_float(self.v["comissao_pct"].get()),
                self._as_float(self.v["cartao_pct"].get()),
                self._as_float(self.v["margem_pct"].get()),
                self._as_float(self.v["perdas_pct"].get()),
                self._as_float(self.v["defeito_pct"].get()),
                self._as_float(self.v["fixos_mes"].get()),
                self._as_float(self.v["capacidade_mes"].get()),
                self._as_float(self.v["variaveis"].get()),
                self._as_float(self.v["frete"].get()),
                self.cmb_round.get(),
                self.cmb_canal.get(),
            ))
            conn.commit()
            messagebox.showinfo("Perfil", f"Perfil '{nome}' salvo/atualizado.")
        except Exception as e:
            messagebox.showerror("Perfil", f"Erro ao salvar: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _load_profile_pick(self):
        try:
            conn = _connect()
            self._ensure_profile_table(conn)
            cur = conn.execute("SELECT nome FROM pricing_profiles ORDER BY nome")
            nomes = [r["nome"] for r in cur.fetchall()]
        except Exception as e:
            messagebox.showerror("Perfil", f"Erro: {e}")
            try:
                conn.close()
            except Exception:
                pass
            return

        if not nomes:
            messagebox.showinfo("Perfil", "Nenhum perfil salvo.")
            try:
                conn.close()
            except Exception:
                pass
            return

        nome = simpledialog.askstring("Carregar perfil", f"Digite o nome do perfil:\nDisponíveis: {', '.join(nomes)}")
        if not nome or nome not in nomes:
            try:
                conn.close()
            except Exception:
                pass
            return

        try:
            cur = conn.execute("""
                SELECT impostos, comissao, cartao, margem, perdas, defeito, fixos, capacidade, variaveis, frete, arredondamento, canal
                  FROM pricing_profiles WHERE nome=%s
            """, (nome,))
            row = cur.fetchone()
            if not row:
                messagebox.showinfo("Perfil", "Perfil não encontrado.")
                return
            self.v["impostos_pct"].set(str(row["impostos"]))
            self.v["comissao_pct"].set(str(row["comissao"]))
            self.v["cartao_pct"].set(str(row["cartao"]))
            self.v["margem_pct"].set(str(row["margem"]))
            self.v["perdas_pct"].set(str(row["perdas"]))
            self.v["defeito_pct"].set(str(row["defeito"]))
            self.v["fixos_mes"].set(str(row["fixos"]))
            self.v["capacidade_mes"].set(str(row["capacidade"]))
            self.v["variaveis"].set(str(row["variaveis"]))
            self.v["frete"].set(str(row["frete"]))
            self.cmb_round.set(row["arredondamento"] or "Sem arredondamento")
            self.cmb_canal.set(row["canal"] or "Varejo (Loja)")
            messagebox.showinfo("Perfil", f"Perfil '{nome}' carregado.")
            self._recalc()
        except Exception as e:
            messagebox.showerror("Perfil", f"Erro ao carregar: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _load_defaults(self):
        self.v["impostos_pct"].set(self.v["impostos_pct"].get() or "12")
        self.v["comissao_pct"].set(self.v["comissao_pct"].get() or "5")
        self.v["cartao_pct"].set(self.v["cartao_pct"].get() or "3.5")
        self.v["margem_pct"].set(self.v["margem_pct"].get() or "15")
        self.v["fixos_mes"].set(self.v["fixos_mes"].get() or "0")
        self.v["capacidade_mes"].set(self.v["capacidade_mes"].get() or "1000")
        self.v["variaveis"].set(self.v["variaveis"].get() or "0")
        self.v["frete"].set(self.v["frete"].get() or "0")
        self.v["perdas_pct"].set(self.v["perdas_pct"].get() or "0")
        self.v["defeito_pct"].set(self.v["defeito_pct"].get() or "0")

    # ----------- utilidades
    def _copy_price(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.v["preco_sugerido"].get())
            messagebox.showinfo("Copiar", "Preço sugerido copiado para a área de transferência.")
        except Exception:
            pass

    # ----------- Relatório de pré-custo (HTML)
    def _gerar_relatorio(self):
        """Gera relatório HTML em BANCO DE DADOS/RELATORIO_PRE_CUSTO/ e abre no navegador."""
        try:
            codigo = self.cmb_modelo.get().strip()
            desc = self._model_desc_map.get(codigo, "-")
            now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            fname = f"relatorio_pre_custo_{codigo}_{now}.html"
            out = os.path.join(RELATORIO_PRE_CUSTO_DIR, fname)

            bom = getattr(self, "_last_bom", [])
            html = self._render_html_relatorio(codigo, desc, bom)

            with open(out, "w", encoding="utf-8") as f:
                f.write(html)

            webbrowser.open_new_tab(out)
            messagebox.showinfo("Relatório", f"Relatório gerado e aberto:\n{out}")
        except Exception as e:
            messagebox.showerror("Relatório", f"Erro ao gerar relatório:\n{e}")

    def _imprimir_windows(self):
        """Cria relatório HTML em BANCO DE DADOS/RELATORIO_PRE_CUSTO/ e tenta imprimir (Windows)."""
        try:
            codigo = self.cmb_modelo.get().strip()
            desc = self._model_desc_map.get(codigo, "-")
            now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            fname = f"relatorio_pre_custo_{codigo}_{now}.html"
            out = os.path.join(RELATORIO_PRE_CUSTO_DIR, fname)

            html = self._render_html_relatorio(codigo, desc, getattr(self, "_last_bom", []))
            with open(out, "w", encoding="utf-8") as f:
                f.write(html)

            if os.name == "nt":
                os.startfile(out)  # abre no navegador
                try:
                    os.startfile(out, "print")  # tenta enviar para impressão
                except Exception:
                    pass
            else:
                webbrowser.open_new_tab(out)

            messagebox.showinfo("Relatório", f"Relatório criado:\n{out}\nUse Ctrl+P para imprimir.")
        except Exception as e:
            messagebox.showerror("Relatório", f"Erro ao imprimir:\n{e}")

    def _render_html_relatorio(self, codigo: str, desc: str, bom: List[Dict]) -> str:
        """
        Gera o HTML do Relatório de Pré-Custo com:
          - cabeçalho com logo.jpg (mesmo diretório do arquivo) embutida em base64
          - layout com alto contraste
          - CSS @media print forçando preto/branco para evitar "texto opaco"
          - tabelas de Resumo, Parâmetros e BOM
        """
        import base64

        # atalhos
        def gv(key):
            return self.v[key].get()

        def fnum(x):
            try:
                return f"{float(x):.2f}"
            except:
                return str(x)

        # --- BOM (itens) ---
        bom_rows = ""
        total_bom = 0.0
        if bom:
            for it in bom:
                total_bom += float(it.get("custo_total", 0.0))
                bom_rows += (
                    "<tr>"
                    f"<td>{it.get('tipo', '')}</td>"
                    f"<td>{it.get('item', '')}</td>"
                    f"<td class='num'>{it.get('qtd', 0):.2f}</td>"
                    f"<td>{it.get('un', '')}</td>"
                    f"<td class='num'>{it.get('custo_unit', 0):.2f}</td>"
                    f"<td class='num'>{it.get('custo_total', 0):.2f}</td>"
                    "</tr>"
                )
        else:
            bom_rows = "<tr><td colspan='6'>Sem itens localizados.</td></tr>"

        total_lote = float(self._as_float(gv('preco_sugerido'))) * max(1, int(self._as_float(gv('lote'))))

        # --- carrega logo.jpg (mesmo diretório do arquivo) e embute ---
        base_dir = os.path.dirname(__file__)
        logo_path = os.path.join(base_dir, "logo.jpg")
        logo_data_uri = ""
        try:
            if os.path.isfile(logo_path):
                with open(logo_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                logo_data_uri = f"data:image/jpeg;base64,{b64}"
        except Exception:
            logo_data_uri = ""

        # --- CSS com alto contraste e overrides para impressão ---
        css = """
        <style>
          :root{
            --bg:#0f1623;        /* fundo tela (dark) */
            --fg:#e6e6e6;        /* texto tela (claro) */
            --head:#1f3b63;      /* cabeçalho tela */
            --brd:#2a3850;       /* borda tela */
          }
          @page { size: A4; margin: 14mm; }
          body{ background:var(--bg); color:var(--fg); font:12px/1.5 "Segoe UI", Arial, Helvetica, sans-serif; }
          header{ display:flex; align-items:center; gap:12px; background:var(--head); color:#fff; padding:10px 12px; border-bottom:2px solid #3a7bd5; }
          header img.logo{ height:36px; border-radius:4px; }
          header .t{ font-weight:700; font-size:18px }
          header .m{ margin-left:auto; opacity:.9 }
          .wrap{ padding:8px 12px; }
          h2{ margin:18px 0 8px; border-bottom:1px solid var(--brd); padding-bottom:6px; }
          table{ width:100%; border-collapse:collapse; margin:8px 0 16px; }
          th,td{ border:1px solid var(--brd); padding:7px 8px; }
          thead th{ background:#1d2740; color:#fff; }
          tbody tr:nth-child(even) td{ background:rgba(255,255,255,.04); }
          td.num{ text-align:right; }
          .kpi{ display:flex; gap:12px; flex-wrap:wrap; margin:10px 0 6px; }
          .card{ border:1px solid var(--brd); border-radius:10px; padding:10px 12px; min-width:160px; background:#121b2b; }
          .card .title{ font-size:12px; opacity:.85 }
          .card .val{ font-size:18px; font-weight:700; }

          /* ---------- impressão: força preto/branco e alto contraste ---------- */
          @media print {
            body, .wrap { background:#fff !important; color:#000 !important;
                          -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            header{ background:#fff !important; color:#000 !important; border-bottom:2px solid #000 !important; }
            header .t, header .m{ color:#000 !important; }
            h2{ color:#000 !important; border-color:#000 !important; }
            th,td{ color:#000 !important; border-color:#000 !important; }
            thead th{ background:#e6e6e6 !important; color:#000 !important; }
            tbody tr:nth-child(even) td{ background:#f7f7f7 !important; }
            .card{ background:#fff !important; border-color:#000 !important; }
          }
        </style>
        """

        # --- HTML ---
        logo_img = f"<img class='logo' src='{logo_data_uri}' alt='logo'>" if logo_data_uri else ""
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

        html = f"""<!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="color-scheme" content="light">
      {css}
    </head>
    <body>
    <header>
      {logo_img}
      <div class="t">Relatório de Pré-Custo</div>
      <div class="m">Gerado em {now}</div>
    </header>

    <div class="wrap">
      <div style="margin:6px 0 12px">Modelo: <b>{codigo}</b> — {desc}</div>

      <h2>Resumo</h2>
      <div class="kpi">
        <div class="card"><div class="title">Materiais</div><div class="val">R$ {gv('materiais')}</div></div>
        <div class="card"><div class="title">Costura</div><div class="val">R$ {gv('costura')}</div></div>
        <div class="card"><div class="title">Overhead/peça</div><div class="val">R$ {gv('overhead')}</div></div>
        <div class="card"><div class="title">Custo Total</div><div class="val">R$ {gv('custo_total')}</div></div>
        <div class="card"><div class="title">Preço Sugerido</div><div class="val">R$ {gv('preco_sugerido')}</div></div>
        <div class="card"><div class="title">Lucro Unit.</div><div class="val">R$ {gv('lucro_unit')}</div></div>
        <div class="card"><div class="title">Markup</div><div class="val">{gv('markup')}</div></div>
      </div>

      <h2>Parâmetros</h2>
      <table>
        <tr><th>Canal</th><td>{self.cmb_canal.get()}</td><th>Arredondamento</th><td>{self.cmb_round.get()}</td></tr>
        <tr><th>Impostos %</th><td class="num">{gv('impostos_pct')}</td><th>Comissão %</th><td class="num">{gv('comissao_pct')}</td></tr>
        <tr><th>Cartão %</th><td class="num">{gv('cartao_pct')}</td><th>Margem %</th><td class="num">{gv('margem_pct')}</td></tr>
        <tr><th>Perdas %</th><td class="num">{gv('perdas_pct')}</td><th>Defeito %</th><td class="num">{gv('defeito_pct')}</td></tr>
        <tr><th>Fixos/mês</th><td class="num">{gv('fixos_mes')}</td><th>Capacidade/mês</th><td class="num">{gv('capacidade_mes')}</td></tr>
        <tr><th>Variáveis unit.</th><td class="num">{gv('variaveis')}</td><th>Frete unit.</th><td class="num">{gv('frete')}</td></tr>
        <tr><th>Lote planejado</th><td class="num">{gv('lote')}</td><th>Total do lote (sugerido)</th><td class="num">R$ {total_lote:.2f}</td></tr>
      </table>

      <h2>BOM / Itens</h2>
      <table>
        <thead>
          <tr><th>Tipo</th><th>Item</th><th class="num">Qtd</th><th>Un</th><th class="num">C.Unit</th><th class="num">C.Total</th></tr>
        </thead>
        <tbody>{bom_rows}</tbody>
      </table>

      <p style="margin-top:20px;font-size:11px;opacity:.85">
        Relatório gerado automaticamente. Revise os dados antes de divulgar.
      </p>
    </div>

    <script>setTimeout(function(){{window.print();}}, 400);</script>
    </body>
    </html>"""
        return html

    # ----------- estilo de botões por papel
    def _apply_role_colors(self, parent=None):
        parent = parent or self
        try:
            for w in parent.winfo_children():
                try:
                    if isinstance(w, ctk.CTkButton):
                        txt = (w.cget("text") or "").lower()
                        if any(k in txt for k in
                               ["salvar", "registrar", "confirmar", "calcular", "analisar", "exportar", "gerar",
                                "imprimir", "copiar"]):
                            w.configure(fg_color=getattr(self.sistema, "cor_sucesso", "#2e7d32"))
                        elif any(k in txt for k in ["excluir", "apagar"]):
                            w.configure(fg_color=getattr(self.sistema, "cor_alerta", "#c62828"))
                        elif any(k in txt for k in ["imprimir"]):
                            w.configure(fg_color=getattr(self.sistema, "cor_imprimir", "#9E9E9E"))
                except Exception:
                    pass
                if hasattr(w, "winfo_children"):
                    self._apply_role_colors(w)
        except Exception:
            pass


# ------------------ Execução standalone --------------------------------------
    _I18N_MAP = {'en_US': {'Precificação de Produto': 'Product Pricing', 'Modelo': 'Model', 'Recarregar': 'Reload', 'Canal': 'Channel', 'Resumo': 'Summary', 'Custos': 'Costs', 'Impostos & Margem': 'Taxes & Margin', 'Simulações': 'Simulations', 'BOM / Itens': 'BOM / Items', 'Relatório': 'Report', 'Calcular': 'Calculate', 'Arredondamento': 'Rounding', 'Salvar perfil como...': 'Save profile as...', 'Carregar perfil...': 'Load profile...', 'Escada de preços (margem %)': 'Price ladder (margin %)', 'Analisar preço alvo': 'Analyze target price', 'Margem atingida (%)': 'Achieved margin (%)', 'Exportar simulações CSV': 'Export simulations CSV', 'Relatório de Pré-Custo': 'Pre-Cost Report', 'Gerar & Abrir HTML': 'Generate & Open HTML', 'Imprimir (Windows)': 'Print (Windows)', 'Copiar preço sugerido': 'Copy suggested price', 'Varejo (Loja)': 'Retail (Store)', 'Atacado': 'Wholesale', 'E-commerce': 'E-commerce', 'Marketplace': 'Marketplace', 'Sem arredondamento': 'No rounding', 'Terminar em .90 (para cima)': 'End in .90 (round up)', 'Terminar em .99 (para cima)': 'End in .99 (round up)', 'Múltiplo de 0,50 (para cima)': 'Multiple of 0.50 (round up)', 'Múltiplo de 1,00 (para cima)': 'Multiple of 1.00 (round up)', 'Múltiplo de 5,00 (para cima)': 'Multiple of 5.00 (round up)', 'Múltiplo de 10,00 (para cima)': 'Multiple of 10.00 (round up)'}, 'es_ES': {'Precificação de Produto': 'Fijación de Precio del Producto', 'Modelo': 'Modelo', 'Recarregar': 'Recargar', 'Canal': 'Canal', 'Resumo': 'Resumen', 'Custos': 'Costos', 'Impostos & Margem': 'Impuestos y Margen', 'Simulações': 'Simulaciones', 'BOM / Itens': 'BOM / Ítems', 'Relatório': 'Informe', 'Calcular': 'Calcular', 'Arredondamento': 'Redondeo', 'Salvar perfil como...': 'Guardar perfil como...', 'Carregar perfil...': 'Cargar perfil...', 'Escada de preços (margem %)': 'Escala de precios (margen %)', 'Analisar preço alvo': 'Analizar precio objetivo', 'Margem atingida (%)': 'Margen alcanzado (%)', 'Exportar simulações CSV': 'Exportar simulaciones CSV', 'Relatório de Pré-Custo': 'Informe de Pre-Costo', 'Gerar & Abrir HTML': 'Generar y Abrir HTML', 'Imprimir (Windows)': 'Imprimir (Windows)', 'Copiar preço sugerido': 'Copiar precio sugerido', 'Varejo (Loja)': 'Minorista (Tienda)', 'Atacado': 'Mayorista', 'E-commerce': 'E-commerce', 'Marketplace': 'Marketplace', 'Sem arredondamento': 'Sin redondeo', 'Terminar em .90 (para cima)': 'Terminar en .90 (hacia arriba)', 'Terminar em .99 (para cima)': 'Terminar en .99 (hacia arriba)', 'Múltiplo de 0,50 (para cima)': 'Múltiplo de 0,50 (hacia arriba)', 'Múltiplo de 1,00 (para cima)': 'Múltiplo de 1,00 (hacia arriba)', 'Múltiplo de 5,00 (para cima)': 'Múltiplo de 5,00 (hacia arriba)', 'Múltiplo de 10,00 (para cima)': 'Múltiplo de 10,00 (hacia arriba)'}}

    def _get_idioma_atual(self):
        try:
            if getattr(self, "sistema", None) is not None:
                return getattr(self.sistema, "idioma_atual", "pt_BR") or "pt_BR"
        except Exception:
            pass
        return getattr(self, "idioma_atual", "pt_BR") or "pt_BR"

    def _canonical_i18n_text(self, text):
        if text is None:
            return text
        s = str(text)
        maps = getattr(self, "_I18N_MAP", {}) or {}
        if s in maps.get("pt_BR", {}):
            return s
        for _lang, table in maps.items():
            for pt_key, translated in table.items():
                if s == translated:
                    return pt_key
        return s

    def _translate_i18n_text(self, text):
        if text is None:
            return text
        idioma = self._get_idioma_atual()
        maps = getattr(self, "_I18N_MAP", {}) or {}
        canonical = self._canonical_i18n_text(text)
        return maps.get(idioma, {}).get(canonical, canonical)

    def _translate_i18n_values(self, values):
        if not isinstance(values, (list, tuple)):
            return values
        return [self._translate_i18n_text(v) for v in values]

    def _refresh_widget_i18n(self, widget):
        try:
            if hasattr(widget, "cget"):
                try:
                    text = widget.cget("text")
                    if isinstance(text, str) and text:
                        new_text = self._translate_i18n_text(text)
                        if new_text != text:
                            widget.configure(text=new_text)
                except Exception:
                    pass

                try:
                    placeholder = widget.cget("placeholder_text")
                    if isinstance(placeholder, str) and placeholder:
                        new_placeholder = self._translate_i18n_text(placeholder)
                        if new_placeholder != placeholder:
                            widget.configure(placeholder_text=new_placeholder)
                except Exception:
                    pass

                try:
                    values = widget.cget("values")
                    if isinstance(values, (list, tuple)) and values:
                        current = None
                        try:
                            current = widget.get()
                        except Exception:
                            current = None
                        translated_values = self._translate_i18n_values(list(values))
                        widget.configure(values=translated_values)
                        if current:
                            widget.set(self._translate_i18n_text(current))
                except Exception:
                    pass

            if isinstance(widget, ttk.Treeview):
                try:
                    for col in widget["columns"]:
                        info = widget.heading(col)
                        heading_text = info.get("text", "")
                        if heading_text:
                            widget.heading(col, text=self._translate_i18n_text(heading_text))
                except Exception:
                    pass

            for child in widget.winfo_children():
                self._refresh_widget_i18n(child)
        except Exception:
            pass

    def refresh_texts(self):
        try:
            target = getattr(self, "root", None) or self
            self._refresh_widget_i18n(target)
        except Exception:
            pass

        try:
            if hasattr(self, "root") and self.root:
                self.root.title(self._translate_i18n_text(self.root.title()))
        except Exception:
            pass

        try:
            if hasattr(self, "PAGE_TITLE"):
                self.PAGE_TITLE = self._translate_i18n_text(self.PAGE_TITLE)
        except Exception:
            pass

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = ctk.CTk()
    app.title(PrecificacaoProdutoPage.PAGE_TITLE)
    app.geometry("1200x760")
    page = PrecificacaoProdutoPage(app)
    page.pack(fill="both", expand=True)
    app.mainloop()

