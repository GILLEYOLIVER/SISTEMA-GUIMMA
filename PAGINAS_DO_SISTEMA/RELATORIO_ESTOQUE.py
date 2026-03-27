# -*- coding: utf-8 -*-
"""
RELATORIO_ESTOQUE.py — versão COMPLETA com IA MEGA + UI conversacional
- Integração com BANCO_DE_DADOS_PG (PostgreSQL)
- UI com abas: 📋 Relatório | 📊 Análise | 🤖 Assistente
- IA MEGA (40+ intenções, centenas de variações, análises ricas)

Requisitos opcionais: fpdf, matplotlib
"""

from PAGINAS_DO_SISTEMA import TEMAS
import os
import csv
import re
import threading
import queue
import time
import random
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from difflib import get_close_matches
from typing import List, Dict, Tuple, Any, Optional

import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import tkinter as tk

# Exportações/relatórios (opcionais) - CORREÇÃO DO FPDF
try:
    # Tentar importar fpdf2 primeiro (mais moderno)
    from fpdf import FPDF

    FPDF_AVAILABLE = True
    print("[INFO] fpdf2 disponível para geração de PDF")
except ImportError:
    try:
        # Fallback para PyFPDF (mais antigo)
        from pyfpdf import FPDF

        FPDF_AVAILABLE = True
        print("[INFO] PyFPDF disponível para geração de PDF")
    except ImportError:
        FPDF = None
        FPDF_AVAILABLE = False
        print("[INFO] Nenhuma biblioteca FPDF disponível")

try:
    import matplotlib

    matplotlib.use("Agg")  # evita conflitos de backend
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    MATPLOTLIB_AVAILABLE = True
    print("[INFO] Matplotlib disponível para gráficos")
except Exception:
    plt = None
    FigureCanvasTkAgg = None
    MATPLOTLIB_AVAILABLE = False
    print("[INFO] Matplotlib não disponível")

# === ACESSO AO POSTGRES ===
from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db
from PAGINAS_DO_SISTEMA.RELATORIO_ESTOQUE_IA import EstoqueIA as EstoqueIAAvancada


# ------------------------------------------------------------------
# Utilitários simples
# ------------------------------------------------------------------
def _hex_contrast(hex_color: str) -> str:
    """Retorna preto ou branco dependendo do contraste com a cor fornecida (hex #RRGGBB)."""
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return "#000000" if brightness > 128 else "#FFFFFF"
    except Exception:
        return "#FFFFFF"


def _fmt_date(dt):
    if not dt:
        return "—"
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%Y")
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(dt), fmt).strftime("%d/%m/%Y")
        except Exception:
            continue
    return str(dt)


# ------------------------------------------------------------------
# IA — Classe MEGA
# ------------------------------------------------------------------
# -*- coding: utf-8 -*-
"""
EstoqueIA - Versão offline com dicionário gigante e consultas SQL dinâmicas.
Nenhuma dependência externa de ML. Usa apenas Python padrão + psycopg2.
"""

import re
import random
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from difflib import get_close_matches
from typing import List, Dict, Tuple, Any, Optional

# Tenta importar opcionais para gráficos e PDF
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except:
    MATPLOTLIB_AVAILABLE = False

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except:
    FPDF_AVAILABLE = False

# Conexão com banco (deve estar no mesmo projeto)
from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db


def _fmt_date(dt):
    if not dt:
        return "—"
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%Y")
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(dt), fmt).strftime("%d/%m/%Y")
        except:
            continue
    return str(dt)


# -*- coding: utf-8 -*-
"""
ESTOQUE_IA_INTELIGENTE_V3.py
Classe pronta para substituir a classe EstoqueIA atual do RELATORIO_ESTOQUE.py.

Objetivos:
- Corrigir erro de compatibilidade com _intent_score
- Consultar TODAS as tabelas reais do estoque
- Entender perguntas por código, descrição, cor, fornecedor, tipo e localização
- Responder de forma natural, mas sempre baseada em SQL real
- Funcionar sem dependências externas de IA
"""



import re
import unicodedata
from dataclasses import dataclass
from difflib import get_close_matches
from typing import Any, Dict, List, Optional, Tuple

from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db


import re
from typing import Any, Dict, List, Optional, Tuple

from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db


class EstoqueIA:
    TABELAS = {
        "Tecidos": "estoque_tecidos",
        "Aviamentos": "estoque_aviamentos",
        "Insumos": "estoque_insumos",
        "Escritorio": "estoque_escritorio",
        "Limpeza": "estoque_limpeza",
        "Outros": "estoque_outros",
    }

    GROUP_SYNONYMS = {
        "Tecidos": ["tecido", "tecidos", "malha", "sarja", "tricoline", "viscose", "jeans", "algodao", "algodão"],
        "Aviamentos": ["aviamento", "aviamentos", "ziper", "zíper", "linha", "botao", "botão", "elastico", "elástico", "agulha", "etiqueta"],
        "Insumos": ["insumo", "insumos"],
        "Escritorio": ["escritorio", "escritório", "papel", "caneta", "toner", "clip", "clipe", "grampeador"],
        "Limpeza": ["limpeza", "detergente", "sabao", "sabão", "alcool", "álcool", "pano", "vassoura"],
        "Outros": ["outro", "outros", "diversos", "geral"],
    }

    CONTINUATION_WORDS = {
        "quais", "quais?", "liste", "liste-os", "liste-os?", "eles", "elas", "esses", "essas",
        "os", "as", "mostre", "mostra", "nomes", "liste eles", "liste os nomes", "e quais", "e os nomes"
    }

    def __init__(self, resultados=None):
        self.resultados = resultados or []
        self.ctx: List[Tuple[str, str]] = []
        self.last_intent: Optional[str] = None
        self.last_entities: Dict[str, Any] = {}
        self.last_result_rows: List[Dict[str, Any]] = []
        self.last_result_summary: Dict[str, Any] = {}
        self._sources_cache: Optional[List[Dict[str, Any]]] = None

    # ---------------------------
    # Compatibilidade com UI antiga
    # ---------------------------
    def _intent_score(self, pergunta: str) -> Tuple[Optional[str], float]:
        return self._detect_intent(pergunta)

    # ---------------------------
    # Infra / schema discovery
    # ---------------------------
    def _remember(self, who: str, text: str) -> None:
        self.ctx.append((who, text))
        if len(self.ctx) > 20:
            self.ctx = self.ctx[-20:]

    def _safe_float(self, value: Any) -> float:
        try:
            if value is None or value == "":
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    def _safe_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _list_column_names(self, table: str) -> List[str]:
        try:
            cols = db.list_columns(table)
            names = []
            for c in cols or []:
                if isinstance(c, dict):
                    nm = c.get("column_name")
                else:
                    nm = getattr(c, "get", lambda _k, _d=None: None)("column_name")
                if nm:
                    names.append(str(nm).lower())
            return names
        except Exception:
            return []

    def _choose_col(self, cols: List[str], candidates: List[str]) -> Optional[str]:
        for c in candidates:
            if c.lower() in cols:
                return c.lower()
        return None

    def _get_sources(self) -> List[Dict[str, Any]]:
        if self._sources_cache is not None:
            return self._sources_cache

        sources: List[Dict[str, Any]] = []
        for grupo, tabela in self.TABELAS.items():
            try:
                if not db.table_exists(tabela):
                    continue
            except Exception:
                continue

            cols = self._list_column_names(tabela)
            if not cols:
                continue

            source = {
                "grupo": grupo,
                "tabela": tabela,
                "cols": cols,
                "codigo_col": self._choose_col(cols, ["codigo", "cod"]),
                "descricao_col": self._choose_col(cols, ["descricao", "descrição", "nome", "produto"]),
                "cor_col": self._choose_col(cols, ["cor"]),
                "fornecedor_col": self._choose_col(cols, ["fornecedor"]),
                "composicao_col": self._choose_col(cols, ["composicao", "composição"]),
                "tipo_col": self._choose_col(cols, ["tipo"]),
                "categoria_col": self._choose_col(cols, ["categoria"]),
                "localizacao_col": self._choose_col(cols, ["localizacao", "localização", "local"]),
                "metros_col": self._choose_col(cols, ["metros", "metro"]),
                "kilos_col": self._choose_col(cols, ["kilos", "quilo", "kg"]),
                "quantidade_col": self._choose_col(cols, ["quantidade", "qtd"]),
                "unidade_col": self._choose_col(cols, ["unidade"]),
                "data_col": self._choose_col(cols, ["data_entrada", "data", "created_at", "atualizado_em", "updated_at"]),
                "obs_col": self._choose_col(cols, ["observacoes", "observação", "observacoes", "obs"]),
            }
            sources.append(source)

        self._sources_cache = sources
        return sources

    def _sql_expr(self, col: Optional[str], fallback_sql: str) -> str:
        if col:
            return col
        return fallback_sql

    def _build_union_query(self) -> str:
        parts = []
        for s in self._get_sources():
            codigo = self._sql_expr(s["codigo_col"], "NULL::text")
            descricao = self._sql_expr(s["descricao_col"], "NULL::text")
            cor = self._sql_expr(s["cor_col"], "NULL::text")
            fornecedor = self._sql_expr(s["fornecedor_col"], "NULL::text")
            composicao = self._sql_expr(s["composicao_col"], "NULL::text")
            localizacao = self._sql_expr(s["localizacao_col"], "NULL::text")
            data_col = self._sql_expr(s["data_col"], "NULL::timestamp")
            obs = self._sql_expr(s["obs_col"], "NULL::text")

            categoria_expr = "NULL::text"
            if s["categoria_col"]:
                categoria_expr = s["categoria_col"]
            elif s["tipo_col"]:
                categoria_expr = s["tipo_col"]
            else:
                categoria_expr = f"'{s['grupo']}'::text"

            if s["grupo"] == "Tecidos":
                saldo_num = f"COALESCE({s['metros_col']}, 0)" if s["metros_col"] else "0::numeric"
                saldo_display = (
                    f"TRIM(BOTH ' ' FROM "
                    f"CONCAT(CASE WHEN {s['metros_col']} IS NOT NULL THEN COALESCE({s['metros_col']},0)::text || ' m' ELSE '' END, "
                    f"CASE WHEN {s['kilos_col']} IS NOT NULL THEN CASE WHEN {s['metros_col']} IS NOT NULL THEN ' | ' ELSE '' END || COALESCE({s['kilos_col']},0)::text || ' kg' ELSE '' END))"
                    if s["metros_col"] or s["kilos_col"] else "''::text"
                )
                unidade = "'m/kg'::text"
                medidas = "'tecido'::text"
            else:
                saldo_num = f"COALESCE({s['quantidade_col']}, 0)" if s["quantidade_col"] else "0::numeric"
                saldo_display = f"COALESCE({s['quantidade_col']}, 0)::text" if s["quantidade_col"] else "'0'::text"
                unidade = self._sql_expr(s["unidade_col"], "NULL::text")
                medidas = "'quantidade'::text"

            parts.append(f"""
                SELECT
                    '{s['grupo']}'::text AS grupo,
                    '{s['tabela']}'::text AS tabela,
                    {codigo}::text AS codigo,
                    {descricao}::text AS descricao,
                    {categoria_expr}::text AS categoria_exibicao,
                    {cor}::text AS cor,
                    {fornecedor}::text AS fornecedor,
                    {composicao}::text AS composicao,
                    {localizacao}::text AS localizacao,
                    {saldo_num}::numeric AS saldo_num,
                    {saldo_display}::text AS saldo_exibicao,
                    {unidade}::text AS unidade,
                    {medidas}::text AS tipo_medida,
                    {data_col} AS data_entrada,
                    {obs}::text AS observacoes
                FROM {s['tabela']}
            """)
        return "\nUNION ALL\n".join(parts) if parts else "SELECT NULL::text AS grupo WHERE FALSE"

    def _fetch_rows(self, where_sql: str = "", params: Optional[List[Any]] = None,
                    order_sql: str = "ORDER BY saldo_num DESC, descricao ASC", limit: Optional[int] = 50) -> List[Dict[str, Any]]:
        params = params or []
        union_sql = self._build_union_query()
        if "WHERE" not in where_sql.upper() and where_sql.strip():
            where_sql = f"WHERE {where_sql}"
        limit_sql = f"LIMIT {int(limit)}" if limit else ""
        sql = f"""
            WITH estoque_base AS (
                {union_sql}
            )
            SELECT *
            FROM estoque_base
            {where_sql}
            {order_sql}
            {limit_sql}
        """
        try:
            rows = db.fetch_all(sql, tuple(params))
            return rows or []
        except Exception as e:
            return [{"__erro__": str(e)}]

    # ---------------------------
    # NLP leve e contexto
    # ---------------------------
    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    def _detect_group(self, q: str) -> Optional[str]:
        qn = self._normalize(q)
        for grupo, words in self.GROUP_SYNONYMS.items():
            for w in words:
                if w in qn:
                    return grupo
        return None

    def _extract_entities(self, q: str) -> Dict[str, Any]:
        qn = self._normalize(q)
        ent: Dict[str, Any] = {
            "grupo": self._detect_group(q),
            "codigo": None,
            "cor": None,
            "fornecedor": None,
            "local": None,
            "categoria": None,
            "limite": None,
            "top_n": None,
            "buscar_texto": None,
            "pedir_lista": False,
            "pedir_nomes": False,
            "pedir_criticos": False,
            "pedir_contagem": False,
        }

        m_codigo = re.search(r"(?:codigo|código|cod)\s*[:#-]?\s*([a-z0-9._/-]+)", qn)
        if m_codigo:
            ent["codigo"] = m_codigo.group(1).strip()

        m_top = re.search(r"(?:top|primeiros|ultimos|últimos|ultimos)\s*(\d{1,3})", qn)
        if m_top:
            ent["top_n"] = int(m_top.group(1))

        m_abaixo = re.search(r"(?:abaixo de|menor que|inferior a|criticos abaixo de|críticos abaixo de)\s*(\d+[\.,]?\d*)", qn)
        if m_abaixo:
            ent["limite"] = float(m_abaixo.group(1).replace(",", "."))

        for label, key in [
            (r"cor\s+([\w\s/_-]+)", "cor"),
            (r"fornecedor\s+([\w\s/_-]+)", "fornecedor"),
            (r"(?:local|localizacao|localização|deposito|depósito|setor)\s+([\w\s/_-]+)", "local"),
            (r"categoria\s+([\w\s/_-]+)", "categoria"),
        ]:
            m = re.search(label, qn)
            if m:
                ent[key] = m.group(1).strip(" ?.,;:")

        ent["pedir_lista"] = any(x in qn for x in ["liste", "listar", "mostre", "mostra", "quais", "quais sao", "quais são", "eles", "elas"])
        ent["pedir_nomes"] = any(x in qn for x in ["nomes", "liste os nomes", "liste nomes", "mostrar nomes", "mostre os nomes"])
        ent["pedir_criticos"] = any(x in qn for x in ["critico", "crítico", "criticos", "críticos", "baixo estoque", "repor"])
        ent["pedir_contagem"] = any(x in qn for x in ["quantos", "quantas", "contagem", "total", "temos", "tem "])

        # busca livre curta
        limpa = re.sub(r"[?!.:,;]", " ", qn)
        for remover in ["quantos", "quantas", "temos", "tem", "liste", "listar", "mostre", "mostrar", "quais", "os", "as", "de", "do", "da", "no", "na"]:
            limpa = re.sub(rf"\b{re.escape(remover)}\b", " ", limpa)
        limpa = re.sub(r"\s+", " ", limpa).strip()
        if len(limpa) >= 3:
            ent["buscar_texto"] = limpa

        return ent

    def _detect_intent(self, q: str) -> Tuple[Optional[str], float]:
        qn = self._normalize(q)
        if not qn:
            return None, 0.0

        if qn in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"}:
            return "saudacao", 1.0
        if any(x in qn for x in ["ajuda", "o que voce faz", "o que você faz", "como usar"]):
            return "ajuda", 0.95
        if any(x in qn for x in ["codigo", "código", "cod "]):
            return "buscar_codigo", 0.92
        if any(x in qn for x in ["critico", "crítico", "criticos", "críticos", "baixo estoque", "repor urgente"]):
            return "criticos", 0.90
        if any(x in qn for x in ["quantos", "quantas", "contagem", "total"]) and self._detect_group(qn):
            return "contagem_grupo", 0.90
        if any(x in qn for x in ["liste", "listar", "nomes", "quais", "mostre"]):
            return "listar", 0.70
        if self._detect_group(qn):
            return "grupo", 0.60
        return "busca_livre", 0.45

    def _merge_with_context(self, current: Dict[str, Any], q: str) -> Dict[str, Any]:
        qn = self._normalize(q)
        merged = dict(self.last_entities or {})
        merged.update({k: v for k, v in current.items() if v not in (None, False, "")})

        continuation = (
            qn in self.CONTINUATION_WORDS
            or qn.startswith("quais")
            or qn.startswith("liste")
            or qn.startswith("mostre")
            or qn.startswith("e ")
        )
        if continuation and self.last_result_summary:
            if not merged.get("grupo"):
                merged["grupo"] = self.last_result_summary.get("grupo")
            if not merged.get("categoria"):
                merged["categoria"] = self.last_result_summary.get("categoria")
            if not merged.get("local"):
                merged["local"] = self.last_result_summary.get("local")

        return merged

    # ---------------------------
    # Renderização
    # ---------------------------
    def _format_number_pt(self, value: float, casas: int = 2) -> str:
        s = f"{value:,.{casas}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def _human_intro(self) -> str:
        return (
            "Olá! Posso consultar o estoque real por tecidos, aviamentos, insumos, escritório, limpeza e outros.\n"
            "Você pode pedir contagem, críticos, nomes, código, cor, fornecedor ou localização."
        )

    def _rows_to_list(self, rows: List[Dict[str, Any]], max_items: int = 20) -> str:
        if not rows:
            return "Nenhum item encontrado."
        out = []
        for r in rows[:max_items]:
            desc = self._safe_text(r.get("descricao")) or "Sem descrição"
            cod = self._safe_text(r.get("codigo")) or "—"
            grupo = self._safe_text(r.get("grupo")) or "—"
            local = self._safe_text(r.get("localizacao")) or "—"
            cor = self._safe_text(r.get("cor"))
            saldo = self._safe_text(r.get("saldo_exibicao")) or self._format_number_pt(self._safe_float(r.get("saldo_num")))
            extra = []
            if cor:
                extra.append(f"Cor: {cor}")
            if local:
                extra.append(f"Local: {local}")
            out.append(f"- {desc} | Cód: {cod} | Grupo: {grupo} | Saldo: {saldo}" + (" | " + " | ".join(extra) if extra else ""))
        return "\n".join(out)

    def _store_result_context(self, rows: List[Dict[str, Any]], entities: Dict[str, Any], intent: Optional[str]) -> None:
        self.last_result_rows = rows[:]
        self.last_result_summary = {
            "grupo": entities.get("grupo"),
            "categoria": entities.get("categoria"),
            "local": entities.get("local"),
            "intent": intent,
            "count": len(rows),
        }

    # ---------------------------
    # Respostas
    # ---------------------------
    def _responder_saudacao(self) -> str:
        return self._human_intro()

    def _responder_ajuda(self) -> str:
        return (
            self._human_intro() + "\n\n"
            "Exemplos:\n"
            "- quantos tecidos temos\n"
            "- liste os nomes dos tecidos\n"
            "- mostre os críticos de limpeza\n"
            "- buscar código 123\n"
            "- itens do fornecedor santa luzia\n"
            "- o que temos no depósito A"
        )

    def _build_filters(self, entities: Dict[str, Any]) -> Tuple[str, List[Any]]:
        where = []
        params: List[Any] = []

        if entities.get("grupo"):
            where.append("grupo = %s")
            params.append(entities["grupo"])
        if entities.get("codigo"):
            where.append("LOWER(COALESCE(codigo, '')) = %s")
            params.append(str(entities["codigo"]).lower())
        if entities.get("cor"):
            where.append("LOWER(COALESCE(cor, '')) LIKE %s")
            params.append(f"%{entities['cor'].lower()}%")
        if entities.get("fornecedor"):
            where.append("LOWER(COALESCE(fornecedor, '')) LIKE %s")
            params.append(f"%{entities['fornecedor'].lower()}%")
        if entities.get("local"):
            where.append("LOWER(COALESCE(localizacao, '')) LIKE %s")
            params.append(f"%{entities['local'].lower()}%")
        if entities.get("categoria"):
            where.append("LOWER(COALESCE(categoria_exibicao, '')) LIKE %s")
            params.append(f"%{entities['categoria'].lower()}%")

        return " AND ".join(where), params

    def _responder_contagem(self, entities: Dict[str, Any]) -> str:
        where, params = self._build_filters(entities)
        rows = self._fetch_rows(where_sql=where, params=params, order_sql="ORDER BY descricao ASC", limit=None)
        if rows and rows[0].get("__erro__"):
            return f"Erro ao consultar o banco: {rows[0]['__erro__']}"

        total_linhas = len(rows)
        total_codigos = len({self._safe_text(r.get('codigo')).lower() for r in rows if self._safe_text(r.get('codigo'))})
        saldo_total = sum(self._safe_float(r.get("saldo_num")) for r in rows)
        grupo = entities.get("grupo") or "itens"

        self._store_result_context(rows, entities, "contagem")
        return (
            f"Perfeito, consultei o banco em tempo real.\n"
            f"Encontrei {total_linhas} registro(s) em {grupo}.\n"
            f"Códigos distintos: {total_codigos}.\n"
            f"Saldo numérico total: {self._format_number_pt(saldo_total)}.\n\n"
            f"Se quiser, eu posso listar os nomes, mostrar só os críticos ou separar por fornecedor/localização."
        )

    def _responder_criticos(self, entities: Dict[str, Any]) -> str:
        limite = entities.get("limite")
        if limite is None:
            limite = 10.0 if entities.get("grupo") != "Tecidos" else 20.0
        where, params = self._build_filters(entities)
        where = (where + " AND " if where else "") + "saldo_num < %s"
        params.append(limite)
        rows = self._fetch_rows(where_sql=where, params=params, order_sql="ORDER BY saldo_num ASC, descricao ASC", limit=50)
        if rows and rows[0].get("__erro__"):
            return f"Erro ao consultar o banco: {rows[0]['__erro__']}"
        self._store_result_context(rows, entities, "criticos")
        if not rows:
            return f"Ótimo: não encontrei itens críticos abaixo de {self._format_number_pt(limite)} com esse filtro."
        return (
            f"Encontrei {len(rows)} item(ns) crítico(s) abaixo de {self._format_number_pt(limite)}.\n"
            f"{self._rows_to_list(rows, max_items=20)}\n\n"
            f"Posso agora listar só os nomes, exportar a relação ou separar por grupo."
        )

    def _responder_listar(self, entities: Dict[str, Any]) -> str:
        where, params = self._build_filters(entities)
        # continuação: se o usuário só pediu "quais" ou "liste eles", usa último resultado
        q_rows = None
        if self.last_result_rows and not any([entities.get("grupo"), entities.get("codigo"), entities.get("cor"), entities.get("fornecedor"), entities.get("local"), entities.get("categoria")]):
            q_rows = self.last_result_rows
        else:
            q_rows = self._fetch_rows(where_sql=where, params=params, order_sql="ORDER BY descricao ASC", limit=50)
            if q_rows and q_rows[0].get("__erro__"):
                return f"Erro ao consultar o banco: {q_rows[0]['__erro__']}"
        self._store_result_context(q_rows, entities, "listar")
        if not q_rows:
            return "Não encontrei itens para listar com esse filtro."
        return f"Aqui está a lista encontrada:\n{self._rows_to_list(q_rows, max_items=30)}"

    def _responder_busca_codigo(self, entities: Dict[str, Any]) -> str:
        if not entities.get("codigo"):
            return "Me diga o código do item para eu buscar no banco."
        where, params = self._build_filters(entities)
        rows = self._fetch_rows(where_sql=where, params=params, order_sql="ORDER BY descricao ASC", limit=10)
        if rows and rows[0].get("__erro__"):
            return f"Erro ao consultar o banco: {rows[0]['__erro__']}"
        self._store_result_context(rows, entities, "buscar_codigo")
        if not rows:
            return f"Não encontrei item com código {entities['codigo']}."
        r = rows[0]
        return (
            f"Encontrei este item no banco:\n"
            f"Descrição: {self._safe_text(r.get('descricao')) or 'Sem descrição'}\n"
            f"Código: {self._safe_text(r.get('codigo')) or '—'}\n"
            f"Grupo: {self._safe_text(r.get('grupo')) or '—'}\n"
            f"Categoria/Tipo: {self._safe_text(r.get('categoria_exibicao')) or '—'}\n"
            f"Cor: {self._safe_text(r.get('cor')) or '—'}\n"
            f"Fornecedor: {self._safe_text(r.get('fornecedor')) or '—'}\n"
            f"Localização: {self._safe_text(r.get('localizacao')) or '—'}\n"
            f"Saldo: {self._safe_text(r.get('saldo_exibicao')) or self._format_number_pt(self._safe_float(r.get('saldo_num')))}"
        )

    def _responder_grupo(self, entities: Dict[str, Any]) -> str:
        return self._responder_contagem(entities)

    def _responder_busca_livre(self, entities: Dict[str, Any], q: str) -> str:
        texto = entities.get("buscar_texto") or self._normalize(q)
        words = [w for w in re.split(r"\s+", texto) if len(w) >= 2]
        conditions = []
        params: List[Any] = []
        for w in words[:6]:
            like = f"%{w.lower()}%"
            conditions.append("(" + " OR ".join([
                "LOWER(COALESCE(descricao, '')) LIKE %s",
                "LOWER(COALESCE(codigo, '')) LIKE %s",
                "LOWER(COALESCE(cor, '')) LIKE %s",
                "LOWER(COALESCE(fornecedor, '')) LIKE %s",
                "LOWER(COALESCE(localizacao, '')) LIKE %s",
                "LOWER(COALESCE(categoria_exibicao, '')) LIKE %s",
                "LOWER(COALESCE(grupo, '')) LIKE %s",
            ]) + ")")
            params.extend([like] * 7)
        where = " AND ".join(conditions)
        rows = self._fetch_rows(where_sql=where, params=params, order_sql="ORDER BY saldo_num DESC, descricao ASC", limit=30)
        if rows and rows[0].get("__erro__"):
            return f"Erro ao consultar o banco: {rows[0]['__erro__']}"
        self._store_result_context(rows, entities, "busca_livre")
        if not rows:
            return "Não encontrei resultados com esse texto no estoque real."
        return (
            f"Achei {len(rows)} resultado(s) relacionados a '{texto}'.\n"
            f"{self._rows_to_list(rows, max_items=20)}\n\n"
            f"Se quiser, eu refino por grupo, cor, fornecedor, código ou localização."
        )

    # ---------------------------
    # Entrada pública
    # ---------------------------
    def responder(self, pergunta: str) -> str:
        q = (pergunta or "").strip()
        if not q:
            return "Aguardando sua pergunta."

        self._remember("user", q)
        intent, conf = self._detect_intent(q)
        current_entities = self._extract_entities(q)
        entities = self._merge_with_context(current_entities, q)

        self.last_intent = intent
        self.last_entities = entities

        try:
            if intent == "saudacao":
                resp = self._responder_saudacao()
            elif intent == "ajuda":
                resp = self._responder_ajuda()
            elif intent == "buscar_codigo":
                resp = self._responder_busca_codigo(entities)
            elif intent == "criticos":
                resp = self._responder_criticos(entities)
            elif intent == "contagem_grupo":
                resp = self._responder_contagem(entities)
            elif intent == "listar":
                resp = self._responder_listar(entities)
            elif intent == "grupo":
                resp = self._responder_grupo(entities)
            else:
                # escolha contextual automática
                if entities.get("pedir_criticos"):
                    resp = self._responder_criticos(entities)
                elif entities.get("pedir_lista") or entities.get("pedir_nomes"):
                    resp = self._responder_listar(entities)
                elif entities.get("pedir_contagem") and entities.get("grupo"):
                    resp = self._responder_contagem(entities)
                else:
                    resp = self._responder_busca_livre(entities, q)
        except Exception as e:
            resp = f"Erro ao gerar resposta: {e}"

        self._remember("assistant", resp)
        return resp



# -*- coding: utf-8 -*-
"""
ESTOQUE_IA_INTELIGENTE_V3.py
Classe pronta para substituir a classe EstoqueIA atual do RELATORIO_ESTOQUE.py.

Objetivos:
- Corrigir erro de compatibilidade com _intent_score
- Consultar TODAS as tabelas reais do estoque
- Entender perguntas por código, descrição, cor, fornecedor, tipo e localização
- Responder de forma natural, mas sempre baseada em SQL real
- Funcionar sem dependências externas de IA
"""

import re
import unicodedata
from dataclasses import dataclass
from difflib import get_close_matches
from typing import Any, Dict, List, Optional, Tuple

from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db


@dataclass
class FonteEstoque:
    tipo: str
    tabela: str
    unidade_base: str
    possui_metros_kilos: bool = False


class EstoqueIA:
    """
    Assistente de estoque orientado por SQL real.
    Compatível com chamadas novas (responder) e antigas (_intent_score).
    """

    FONTES: List[FonteEstoque] = [
        FonteEstoque("Tecidos", "estoque_tecidos", "tecidos", True),
        FonteEstoque("Aviamentos", "estoque_aviamentos", "unidades"),
        FonteEstoque("Insumos", "estoque_insumos", "unidades"),
        FonteEstoque("Escritorio", "estoque_escritorio", "unidades"),
        FonteEstoque("Limpeza", "estoque_limpeza", "unidades"),
        FonteEstoque("Outros", "estoque_outros", "unidades"),
    ]

    SAUDACOES = {
        "oi", "ola", "olá", "opa", "eai", "e aí", "bom dia", "boa tarde", "boa noite"
    }

    PALAVRAS_CRITICOS = {"critico", "críticos", "criticos", "baixo", "baixos", "acabando", "falta", "faltando", "repor"}
    PALAVRAS_TOTAIS = {"total", "quantos", "quantidade", "somar", "soma"}
    PALAVRAS_BUSCA = {"buscar", "procurar", "encontrar", "mostrar", "mostre", "ver", "detalhes", "dados"}
    PALAVRAS_CODIGO = {"codigo", "código", "cod"}
    PALAVRAS_LOCAL = {"local", "localizacao", "localização", "onde", "deposito", "depósito", "prateleira"}
    PALAVRAS_VALOR = {"valor", "custo", "preco", "preço", "vale", "financeiro"}
    PALAVRAS_LISTAR = {"listar", "liste", "quais", "temos", "tem", "existem"}

    SINONIMOS_TIPO = {
        "tecidos": "Tecidos",
        "tecido": "Tecidos",
        "aviamentos": "Aviamentos",
        "aviamento": "Aviamentos",
        "insumos": "Insumos",
        "insumo": "Insumos",
        "escritorio": "Escritorio",
        "escritório": "Escritorio",
        "limpeza": "Limpeza",
        "outros": "Outros",
        "outro": "Outros",
    }

    def __init__(self, resultados=None):
        self.resultados = resultados or []
        self.ctx: List[Tuple[str, str]] = []
        self.last_intent: Optional[str] = None
        self.last_entities: Dict[str, Any] = {}
        self.schema = getattr(db, "get_schema", lambda: "opera")()
        self._fontes_validas = self._descobrir_fontes_validas()
        self._tipos_disponiveis = [f.tipo for f in self._fontes_validas]
        self._locais_cache: List[str] = []
        self._fornecedores_cache: List[str] = []

    # ---------------- Compatibilidade ----------------
    def _intent_score(self, pergunta: str) -> Tuple[Optional[str], float]:
        """Compatibilidade com código antigo da UI."""
        return self._detect_intent(pergunta)

    # ---------------- Utilidades ----------------
    def _remember(self, who: str, text: str) -> None:
        self.ctx.append((who, text))
        if len(self.ctx) > 20:
            self.ctx = self.ctx[-20:]

    def _norm(self, text: Any) -> str:
        text = "" if text is None else str(text)
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"\s+", " ", text.strip().lower())

    def _descobrir_fontes_validas(self) -> List[FonteEstoque]:
        validas = []
        for fonte in self.FONTES:
            try:
                if db.table_exists(fonte.tabela, self.schema):
                    validas.append(fonte)
            except TypeError:
                if db.table_exists(fonte.tabela):
                    validas.append(fonte)
            except Exception:
                continue
        return validas or self.FONTES[:2]

    def _todas_as_fontes_sql(self) -> str:
        partes = []
        for fonte in self._fontes_validas:
            if fonte.possui_metros_kilos:
                partes.append(f"""
                    SELECT
                        '{fonte.tipo}' AS tipo,
                        '{fonte.tabela}' AS tabela_origem,
                        id,
                        COALESCE(codigo::text, '') AS codigo,
                        COALESCE(descricao, '') AS descricao,
                        COALESCE(cor, '') AS cor,
                        COALESCE(fornecedor, '') AS fornecedor,
                        COALESCE(composicao, '') AS composicao,
                        COALESCE(localizacao, '') AS localizacao,
                        COALESCE(observacoes, '') AS observacoes,
                        COALESCE(data_entrada::text, '') AS data_entrada,
                        NULLIF(TRIM(COALESCE(categoria, '')), '') AS categoria,
                        COALESCE(metros, 0)::numeric AS quantidade_base,
                        'metros' AS unidade_base,
                        COALESCE(metros, 0)::numeric AS metros,
                        COALESCE(kilos, 0)::numeric AS kilos,
                        NULL::text AS unidade,
                        NULL::numeric AS quantidade
                    FROM {self.schema}.{fonte.tabela}
                """)
            else:
                partes.append(f"""
                    SELECT
                        '{fonte.tipo}' AS tipo,
                        '{fonte.tabela}' AS tabela_origem,
                        id,
                        COALESCE(codigo::text, '') AS codigo,
                        COALESCE(descricao, '') AS descricao,
                        COALESCE(cor, '') AS cor,
                        COALESCE(fornecedor, '') AS fornecedor,
                        '' AS composicao,
                        COALESCE(localizacao, '') AS localizacao,
                        COALESCE(observacoes, '') AS observacoes,
                        COALESCE(data_entrada::text, '') AS data_entrada,
                        NULLIF(TRIM(COALESCE(categoria, COALESCE(tipo, ''))), '') AS categoria,
                        COALESCE(quantidade, 0)::numeric AS quantidade_base,
                        COALESCE(NULLIF(TRIM(unidade), ''), 'unidades') AS unidade_base,
                        NULL::numeric AS metros,
                        NULL::numeric AS kilos,
                        COALESCE(NULLIF(TRIM(unidade), ''), 'unidades') AS unidade,
                        COALESCE(quantidade, 0)::numeric AS quantidade
                    FROM {self.schema}.{fonte.tabela}
                """)
        return "\nUNION ALL\n".join(partes)

    def _run(self, sql: str, params: tuple = ()) -> List[dict]:
        try:
            return db.fetch_all(sql, params)
        except Exception:
            try:
                with db.get_conn_cursor() as (_conn, cur):
                    cur.execute(sql, params)
                    rows = cur.fetchall() or []
                    out = []
                    for row in rows:
                        out.append(dict(row) if not isinstance(row, dict) else row)
                    return out
            except Exception as e:
                return [{"_erro": str(e)}]

    def _one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        try:
            return db.fetch_one(sql, params)
        except Exception:
            rows = self._run(sql, params)
            if rows and "_erro" not in rows[0]:
                return rows[0]
            return None

    def _extrair_limite(self, pergunta: str, default: float) -> float:
        q = self._norm(pergunta)
        m = re.search(r"(?:abaixo de|menor que|inferior a|acima de|maior que|superior a)\s*(\d+[\.,]?\d*)", q)
        if m:
            return float(m.group(1).replace(",", "."))
        nums = re.findall(r"\d+[\.,]?\d*", q)
        return float(nums[0].replace(",", ".")) if nums else default

    def _extrair_codigo(self, pergunta: str) -> Optional[str]:
        q = pergunta.strip()
        m = re.search(r"(?:cod(?:igo)?|c[oó]digo)\s*[:#-]?\s*([A-Za-z0-9._/-]+)", q, re.I)
        if m:
            return m.group(1).strip()
        tokens = re.findall(r"[A-Za-z]{0,4}\d{2,}[A-Za-z0-9._/-]*|\d{3,}", q)
        return tokens[0].strip() if tokens else None

    def _extrair_tipo(self, pergunta: str) -> Optional[str]:
        q = self._norm(pergunta)
        for k, v in self.SINONIMOS_TIPO.items():
            if k in q:
                return v
        if self.last_entities.get("tipo") in self._tipos_disponiveis and re.search(r"\be\s+os\b|\be\s+as\b|\bdesses\b|\bdessas\b", q):
            return self.last_entities.get("tipo")
        return None

    def _extrair_local(self, pergunta: str) -> Optional[str]:
        locais = self._listar_locais_reais()
        q = self._norm(pergunta)
        for loc in locais:
            if self._norm(loc) in q:
                return loc
        return None

    def _extrair_termo_busca(self, pergunta: str) -> str:
        q = pergunta.strip()
        q = re.sub(r"\b(quantos|quais|temos|tem|mostrar|mostre|listar|liste|buscar|procurar|encontrar|do|da|de|dos|das|no|na|nos|nas|em|por|favor)\b", " ", q, flags=re.I)
        return re.sub(r"\s+", " ", q).strip(" ?!.")

    def _listar_locais_reais(self) -> List[str]:
        if self._locais_cache:
            return self._locais_cache
        sql = f"SELECT DISTINCT NULLIF(TRIM(localizacao), '') AS localizacao FROM ({self._todas_as_fontes_sql()}) t WHERE NULLIF(TRIM(localizacao), '') IS NOT NULL ORDER BY 1"
        rows = self._run(sql)
        self._locais_cache = [r["localizacao"] for r in rows if r.get("localizacao")]
        return self._locais_cache

    def _listar_fornecedores_reais(self) -> List[str]:
        if self._fornecedores_cache:
            return self._fornecedores_cache
        sql = f"SELECT DISTINCT NULLIF(TRIM(fornecedor), '') AS fornecedor FROM ({self._todas_as_fontes_sql()}) t WHERE NULLIF(TRIM(fornecedor), '') IS NOT NULL ORDER BY 1"
        rows = self._run(sql)
        self._fornecedores_cache = [r["fornecedor"] for r in rows if r.get("fornecedor")]
        return self._fornecedores_cache

    # ---------------- Intenção ----------------
    def _detect_intent(self, pergunta: str) -> Tuple[Optional[str], float]:
        q = self._norm(pergunta)
        if not q:
            return None, 0.0

        if q in self.SAUDACOES or any(s in q for s in self.SAUDACOES):
            return "saudacao", 0.95
        if "ajuda" in q or "o que voce faz" in q or "o que você faz" in q:
            return "ajuda", 0.95
        if any(p in q for p in self.PALAVRAS_CRITICOS):
            return "criticos", 0.85
        if "valor" in q and "categoria" in q:
            return "valor_por_categoria", 0.90
        if any(p in q for p in self.PALAVRAS_VALOR):
            return "valor_total", 0.82
        if ("quantos" in q or "qtd" in q or "quantidade" in q) and self._extrair_tipo(pergunta):
            return "quantidade_tipo", 0.91
        if any(p in q for p in self.PALAVRAS_LOCAL) and ("onde" in q or self._extrair_codigo(pergunta) or len(q.split()) <= 6):
            return "localizar", 0.88
        if self._extrair_codigo(pergunta):
            return "buscar_codigo", 0.93
        if any(p in q for p in self.PALAVRAS_LISTAR) and self._extrair_tipo(pergunta):
            return "listar_tipo", 0.86
        if any(p in q for p in self.PALAVRAS_TOTAIS):
            return "quantidade_total", 0.72
        if any(p in q for p in self.PALAVRAS_BUSCA):
            return "buscar_livre", 0.74
        return "buscar_livre", 0.40

    # ---------------- Resposta ----------------
    def responder(self, pergunta: str) -> str:
        q = (pergunta or "").strip()
        if not q:
            return "Digite sua pergunta primeiro."

        self._remember("user", q)
        intent, score = self._detect_intent(q)
        entities = {
            "tipo": self._extrair_tipo(q),
            "codigo": self._extrair_codigo(q),
            "local": self._extrair_local(q),
            "limite": self._extrair_limite(q, 10),
            "termo": self._extrair_termo_busca(q),
        }
        self.last_intent = intent
        self.last_entities = entities

        try:
            if intent == "saudacao":
                resp = self._resp_saudacao()
            elif intent == "ajuda":
                resp = self._resp_ajuda()
            elif intent == "criticos":
                resp = self._resp_criticos(entities)
            elif intent == "quantidade_total":
                resp = self._resp_quantidade_total()
            elif intent == "quantidade_tipo":
                resp = self._resp_quantidade_por_tipo(entities["tipo"])
            elif intent == "listar_tipo":
                resp = self._resp_listar_tipo(entities["tipo"])
            elif intent == "buscar_codigo":
                resp = self._resp_busca_codigo(entities["codigo"])
            elif intent == "localizar":
                resp = self._resp_localizar(entities)
            elif intent == "valor_total":
                resp = self._resp_valor_total(entities)
            elif intent == "valor_por_categoria":
                resp = self._resp_valor_por_categoria()
            else:
                resp = self._resp_busca_livre(entities["termo"], entities)
        except Exception as e:
            resp = f"Erro ao gerar resposta: {e}"

        self._remember("assistant", resp)
        return resp

    # ---------------- Handlers ----------------
    def _resp_saudacao(self) -> str:
        tipos = ", ".join(self._tipos_disponiveis)
        return (
            "Olá. Estou pronto para consultar o estoque real do banco.\n\n"
            f"Hoje eu consigo conversar sobre: {tipos}.\n"
            "Exemplos:\n"
            "- quantos tecidos temos\n"
            "- itens críticos abaixo de 10\n"
            "- código 12345\n"
            "- onde está o item código 12345\n"
            "- mostre aviamentos\n"
            "- valor total do estoque"
        )

    def _resp_ajuda(self) -> str:
        return self._resp_saudacao()

    def _resp_quantidade_total(self) -> str:
        sql = f"SELECT COUNT(*) AS itens, COALESCE(SUM(quantidade_base),0) AS quantidade_total FROM ({self._todas_as_fontes_sql()}) t"
        row = self._one(sql) or {}
        itens = int(row.get("itens") or 0)
        qtd = float(row.get("quantidade_total") or 0)
        return f"No estoque inteiro existem {itens} registros, com total acumulado de {qtd:,.2f}.".replace(",", "X").replace(".", ",").replace("X", ".")

    def _resp_quantidade_por_tipo(self, tipo: Optional[str]) -> str:
        if not tipo:
            return "Não consegui identificar o tipo do item na sua pergunta."
        sql = f"SELECT COUNT(*) AS itens, COALESCE(SUM(quantidade_base),0) AS quantidade_total FROM ({self._todas_as_fontes_sql()}) t WHERE tipo = %s"
        row = self._one(sql, (tipo,)) or {}
        itens = int(row.get("itens") or 0)
        qtd = float(row.get("quantidade_total") or 0)
        return f"Hoje {tipo} tem {itens} registros e soma {qtd:,.2f} na unidade base do cadastro.".replace(",", "X").replace(".", ",").replace("X", ".")

    def _resp_listar_tipo(self, tipo: Optional[str]) -> str:
        if not tipo:
            return "Diga qual tipo você quer listar: Tecidos, Aviamentos, Insumos, Escritório, Limpeza ou Outros."
        sql = f"""
            SELECT codigo, descricao, cor, fornecedor, localizacao, quantidade_base, unidade_base
            FROM ({self._todas_as_fontes_sql()}) t
            WHERE tipo = %s
            ORDER BY descricao NULLS LAST, codigo NULLS LAST
            LIMIT 20
        """
        rows = self._run(sql, (tipo,))
        if not rows or rows[0].get("_erro"):
            return f"Não encontrei dados de {tipo} agora."
        linhas = [f"{tipo} encontrados:"]
        for r in rows:
            linhas.append(
                f"- {r['descricao']} | cód {r['codigo']} | {float(r['quantidade_base'] or 0):,.2f} {r['unidade_base']} | local {r['localizacao'] or 'não informado'}"
                .replace(",", "X").replace(".", ",").replace("X", ".")
            )
        return "\n".join(linhas)

    def _resp_criticos(self, entities: Dict[str, Any]) -> str:
        limite = float(entities.get("limite") or 10)
        tipo = entities.get("tipo")
        local = entities.get("local")
        filtros = ["quantidade_base < %s"]
        params: List[Any] = [limite]
        if tipo:
            filtros.append("tipo = %s")
            params.append(tipo)
        if local:
            filtros.append("localizacao = %s")
            params.append(local)
        sql = f"""
            SELECT tipo, codigo, descricao, cor, fornecedor, localizacao, quantidade_base, unidade_base
            FROM ({self._todas_as_fontes_sql()}) t
            WHERE {' AND '.join(filtros)}
            ORDER BY quantidade_base ASC, descricao ASC
            LIMIT 30
        """
        rows = self._run(sql, tuple(params))
        if not rows or rows[0].get("_erro"):
            return "Não consegui listar os itens críticos agora."
        if len(rows) == 0:
            return f"Não encontrei itens abaixo de {limite:,.2f}.".replace(",", "X").replace(".", ",").replace("X", ".")
        cab = f"Itens críticos abaixo de {limite:,.2f}:".replace(",", "X").replace(".", ",").replace("X", ".")
        linhas = [cab]
        for r in rows:
            linhas.append(
                f"- [{r['tipo']}] {r['descricao']} | cód {r['codigo']} | saldo {float(r['quantidade_base'] or 0):,.2f} {r['unidade_base']} | local {r['localizacao'] or 'não informado'}"
                .replace(",", "X").replace(".", ",").replace("X", ".")
            )
        return "\n".join(linhas)

    def _resp_busca_codigo(self, codigo: Optional[str]) -> str:
        if not codigo:
            return "Informe o código do item para eu pesquisar."
        sql = f"""
            SELECT *
            FROM ({self._todas_as_fontes_sql()}) t
            WHERE codigo ILIKE %s
            ORDER BY tipo, descricao
            LIMIT 10
        """
        rows = self._run(sql, (codigo,))
        if not rows:
            rows = self._run(sql, (f"%{codigo}%",))
        if not rows or rows[0].get("_erro"):
            return f"Não achei item com código {codigo}."
        return self._formatar_detalhes_item(rows)

    def _resp_localizar(self, entities: Dict[str, Any]) -> str:
        codigo = entities.get("codigo")
        if codigo:
            return self._resp_busca_codigo(codigo)
        termo = entities.get("termo")
        local = entities.get("local")
        if local and (not termo or self._norm(termo) == self._norm(local)):
            sql = f"""
                SELECT tipo, codigo, descricao, quantidade_base, unidade_base
                FROM ({self._todas_as_fontes_sql()}) t
                WHERE localizacao = %s
                ORDER BY descricao
                LIMIT 20
            """
            rows = self._run(sql, (local,))
            if not rows or rows[0].get("_erro"):
                return f"Não encontrei itens no local {local}."
            linhas = [f"Itens no local {local}:"]
            for r in rows:
                linhas.append(
                    f"- [{r['tipo']}] {r['descricao']} | cód {r['codigo']} | {float(r['quantidade_base'] or 0):,.2f} {r['unidade_base']}"
                    .replace(",", "X").replace(".", ",").replace("X", ".")
                )
            return "\n".join(linhas)
        return self._resp_busca_livre(termo, entities)

    def _resp_busca_livre(self, termo: str, entities: Dict[str, Any]) -> str:
        termo = (termo or "").strip()
        if len(termo) < 2:
            return "Faça uma pergunta um pouco mais específica para eu pesquisar no estoque real."

        tipo = entities.get("tipo")
        filtros = ["(descricao ILIKE %s OR codigo ILIKE %s OR cor ILIKE %s OR fornecedor ILIKE %s OR localizacao ILIKE %s)"]
        like = f"%{termo}%"
        params: List[Any] = [like, like, like, like, like]
        if tipo:
            filtros.append("tipo = %s")
            params.append(tipo)

        sql = f"""
            SELECT tipo, codigo, descricao, cor, fornecedor, localizacao, quantidade_base, unidade_base
            FROM ({self._todas_as_fontes_sql()}) t
            WHERE {' AND '.join(filtros)}
            ORDER BY descricao, codigo
            LIMIT 20
        """
        rows = self._run(sql, tuple(params))

        if not rows:
            candidatos = get_close_matches(self._norm(termo), [self._norm(x) for x in self._listar_fornecedores_reais()], n=1, cutoff=0.85)
            if candidatos:
                real = next((x for x in self._listar_fornecedores_reais() if self._norm(x) == candidatos[0]), termo)
                return self._resp_busca_livre(real, entities)
            return f"Não achei resultados para '{termo}'."

        if rows[0].get("_erro"):
            return f"Erro ao pesquisar '{termo}': {rows[0]['_erro']}"

        linhas = [f"Encontrei {len(rows)} resultado(s) para '{termo}':"]
        for r in rows:
            linhas.append(
                f"- [{r['tipo']}] {r['descricao']} | cód {r['codigo']} | cor {r['cor'] or '-'} | fornecedor {r['fornecedor'] or '-'} | saldo {float(r['quantidade_base'] or 0):,.2f} {r['unidade_base']} | local {r['localizacao'] or 'não informado'}"
                .replace(",", "X").replace(".", ",").replace("X", ".")
            )
        return "\n".join(linhas)

    def _resp_valor_total(self, entities: Dict[str, Any]) -> str:
        tipo = entities.get("tipo")
        filtros = []
        params: List[Any] = []
        if tipo:
            filtros.append("tipo = %s")
            params.append(tipo)
        where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        sql = f"""
            SELECT tipo, COUNT(*) AS itens, COALESCE(SUM(quantidade_base),0) AS total_quantidade
            FROM ({self._todas_as_fontes_sql()}) t
            {where}
            GROUP BY tipo
            ORDER BY tipo
        """
        rows = self._run(sql, tuple(params))
        if not rows or rows[0].get("_erro"):
            return "Não consegui calcular esse resumo agora."
        linhas = ["Resumo financeiro estimado por volume cadastrado:"]
        total_geral = 0.0
        for r in rows:
            qtd = float(r.get("total_quantidade") or 0)
            fator = self._fator_estimado_tipo(r.get("tipo"))
            valor = qtd * fator
            total_geral += valor
            linhas.append(
                f"- {r['tipo']}: {int(r['itens'] or 0)} itens | quantidade {qtd:,.2f} | valor estimado {valor:,.2f}"
                .replace(",", "X").replace(".", ",").replace("X", ".")
            )
        linhas.append(f"Total estimado: {total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        linhas.append("Observação: isso é uma estimativa por fator médio, porque o cadastro enviado não mostra um preço unitário padrão para todos os tipos.")
        return "\n".join(linhas)

    def _resp_valor_por_categoria(self) -> str:
        sql = f"""
            SELECT COALESCE(NULLIF(TRIM(categoria), ''), tipo) AS categoria_final,
                   COALESCE(SUM(quantidade_base),0) AS total_quantidade,
                   COUNT(*) AS itens,
                   MIN(tipo) AS tipo_ref
            FROM ({self._todas_as_fontes_sql()}) t
            GROUP BY categoria_final
            ORDER BY categoria_final
        """
        rows = self._run(sql)
        if not rows or rows[0].get("_erro"):
            return "Não consegui montar o valor por categoria agora."
        linhas = ["Valor estimado por categoria:"]
        for r in rows:
            qtd = float(r.get("total_quantidade") or 0)
            valor = qtd * self._fator_estimado_tipo(r.get("tipo_ref"))
            linhas.append(
                f"- {r['categoria_final']}: quantidade {qtd:,.2f} | itens {int(r['itens'] or 0)} | valor estimado {valor:,.2f}"
                .replace(",", "X").replace(".", ",").replace("X", ".")
            )
        return "\n".join(linhas)

    # ---------------- Formatação ----------------
    def _formatar_detalhes_item(self, rows: List[dict]) -> str:
        linhas = ["Encontrei estes itens:"]
        for r in rows:
            bloco = [
                f"- [{r.get('tipo')}] {r.get('descricao') or 'Sem descrição'}",
                f"  código: {r.get('codigo') or '-'}",
                f"  cor: {r.get('cor') or '-'}",
                f"  fornecedor: {r.get('fornecedor') or '-'}",
                f"  local: {r.get('localizacao') or 'não informado'}",
                f"  data entrada: {r.get('data_entrada') or '-'}",
            ]
            if r.get("metros") is not None or r.get("kilos") is not None:
                bloco.append(
                    f"  saldo: {float(r.get('metros') or 0):,.2f} metros | {float(r.get('kilos') or 0):,.3f} kilos"
                    .replace(",", "X").replace(".", ",").replace("X", ".")
                )
            else:
                bloco.append(
                    f"  saldo: {float(r.get('quantidade') or r.get('quantidade_base') or 0):,.2f} {r.get('unidade') or r.get('unidade_base') or 'unidades'}"
                    .replace(",", "X").replace(".", ",").replace("X", ".")
                )
            linhas.extend(bloco)
        return "\n".join(linhas)

    def _fator_estimado_tipo(self, tipo: Optional[str]) -> float:
        mapa = {
            "Tecidos": 15.0,
            "Aviamentos": 2.5,
            "Insumos": 7.0,
            "Escritorio": 6.0,
            "Limpeza": 5.0,
            "Outros": 7.0,
        }
        return mapa.get(tipo or "", 7.0)




# ------------------------------------------------------------------
# INTERFACE PRINCIPAL (MESMO PADRÃO DO CADASTRO_DE_CORTE)
# ------------------------------------------------------------------
class AdvancedStockReport(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller or self._create_default_controller()

        # === APLICAR CORES DO TEMA (MESMO PADRÃO DO CADASTRO_DE_CORTE) ===
        self.obter_cores_por_tema()

        # APLICAR COR DE FUNDO AO FRAME PRINCIPAL
        self.configure(fg_color=self.cor_fundo)

        # fontes
        self.font_titulo = ctk.CTkFont(family="Arial", size=24, weight="bold")
        self.font_titulo_medio = ctk.CTkFont(family="Arial", size=16, weight="bold")
        self.font_normal = ctk.CTkFont(family="Arial", size=12)
        self.font_pequeno = ctk.CTkFont(family="Arial", size=10)
        self.font_metrica = ctk.CTkFont(family="Arial", size=18, weight="bold")

        # dados
        self.resultados = []
        self.stats_data = {"total_items": 0, "low_stock": 0, "categories": 0, "total_value": 0.0}
        self.assistente = None

        # fila/threads IA
        self._ai_queue = queue.Queue()
        self._last_user_prompt = None
        self._ai_worker_running = False
        self._ai_schema_cache = []
        self._ai_schema_cache_ts = 0.0
        self._ai_pending_action: Optional[str] = None
        self._ai_perfil_resposta = "operacional"
        self._ai_metricas = {"mensagens": 0, "acoes_diretas": 0, "fallback_db": 0}

        self._setup_styles()
        self._create_main_layout()
        self.reload_data()
        self._setup_window_protocol()
        self._ajustar_janela_inicial()

    def _ajustar_janela_inicial(self):
        """
        Abre a janela do relatório maior e centralizada.
        Só ajusta quando estiver em uma janela de topo.
        """
        try:
            top = self.winfo_toplevel()
            if top is None:
                return
            top.update_idletasks()
            sw = top.winfo_screenwidth()
            sh = top.winfo_screenheight()
            largura = min(1500, max(1180, int(sw * 0.88)))
            altura = min(920, max(760, int(sh * 0.86)))
            x = max(0, (sw - largura) // 2)
            y = max(0, (sh - altura) // 2)
            top.minsize(1120, 700)
            top.geometry(f"{largura}x{altura}+{x}+{y}")
            top.lift()
        except Exception:
            pass

    def obter_cores_por_tema(self):
        """
        Define as cores do relatório de estoque.

        1) Se o relatório foi aberto a partir do MENU_PRINCIPAL, copia TODAS as
           cores do próprio menu (controller), garantindo que fique idêntico.
        2) Se não houver controller, usa um tema roxo padrão.
        """
        controller = getattr(self, "controller", None)

        # 1) Herdar as cores diretamente do MENU_PRINCIPAL
        if controller is not None and hasattr(controller, "cor_fundo"):
            # Lista de atributos de cor que queremos copiar do menu
            atributos_de_cor = [
                "cor_fundo",
                "cor_primaria",
                "cor_secundaria",
                "cor_terciaria",
                "cor_texto",
                "cor_texto_entry",
                "cor_texto_secundario",
                "cor_placeholder",
                "cor_borda",
                "cor_hover",
                "cor_sucesso",
                "cor_alerta",
                "cor_destaque",
                "cor_selecao",
            ]

            for nome_atributo in atributos_de_cor:
                if hasattr(controller, nome_atributo):
                    setattr(self, nome_atributo, getattr(controller, nome_atributo))

            # Garantias de fallback caso o menu não tenha alguns atributos específicos
            if not hasattr(self, "cor_texto_entry"):
                self.cor_texto_entry = getattr(self, "cor_texto", "#ffffff")

            if not hasattr(self, "cor_placeholder"):
                self.cor_placeholder = getattr(self, "cor_texto_secundario", "#888888")

            if not hasattr(self, "cor_selecao"):
                self.cor_selecao = getattr(self, "cor_destaque", "#4f46e5")

            return

        # 2) Fallback: tema roxo padrão (usado somente se não houver controller)
        self.cor_fundo = "#130720"  # Fundo geral roxo bem escuro
        self.cor_primaria = "#24113b"  # Cards e blocos principais
        self.cor_secundaria = "#1a0d2b"  # Blocos internos / áreas secundárias
        self.cor_terciaria = "#10061b"  # Detalhes / fundo mais escuro

        self.cor_texto = "#f5f5ff"  # Texto principal claro
        self.cor_texto_entry = self.cor_texto
        self.cor_texto_secundario = "#b5aecf"
        self.cor_placeholder = "#9b8fb5"

        self.cor_borda = "#3b235a"
        self.cor_hover = "#312049"

        self.cor_sucesso = "#22c55e"
        self.cor_alerta = "#ef4444"

        self.cor_destaque = "#4f46e5"  # Roxo mais vivo para destaques
        self.cor_selecao = self.cor_destaque

    def configurar_treeview_theme(self):
        """
        Configura as cores da Treeview usando as mesmas cores do tema atual.
        Não trava em nenhuma paleta fixa: sempre usa self.cor_* que vem do menu.
        """
        # Garante que as cores estão sincronizadas com o tema antes de aplicar
        self.obter_cores_por_tema()

        self.style = ttk.Style()
        self.style.theme_use("default")

        cor_fundo_linhas = self.cor_secundaria
        cor_texto_linhas = self.cor_texto
        cor_campo = self.cor_secundaria

        # Cor de seleção: usa cor_selecao, se não existir tenta destaque ou primaria
        cor_selecao = getattr(self, "cor_selecao", None) or \
                      getattr(self, "cor_destaque", None) or \
                      self.cor_primaria

        # Configuração geral das linhas
        self.style.configure(
            "Custom.Treeview",
            background=cor_fundo_linhas,
            foreground=cor_texto_linhas,
            fieldbackground=cor_campo,
            borderwidth=0,
            highlightthickness=0,
            rowheight=25,
        )

        # Cabeçalho usando a cor primária do tema
        self.style.configure(
            "Custom.Treeview.Heading",
            background=self.cor_primaria,
            foreground=self.cor_texto,
            relief="flat",
            borderwidth=1,
            font=("Arial", 10, "bold"),
        )

        # Mapeia cor de seleção usando a paleta atual
        self.style.map(
            "Custom.Treeview",
            background=[("selected", cor_selecao)],
            foreground=[("selected", "#FFFFFF")],
        )

    def _create_default_controller(self):
        """
        Controller mínimo usado quando o relatório é executado sozinho
        (sem MENU_PRINCIPAL). Mantém um tema roxo padrão.
        """

        class DefaultController:
            def __init__(self):
                self.obter_cores_por_tema()

            def obter_cores_por_tema(self):
                """
                Sincroniza as cores do relatório com o tema já aplicado no sistema.

                Prioridade:
                1) Se o relatório estiver aberto dentro do MENU_PRINCIPAL, usa as
                   propriedades de cor do próprio menu (self.controller).
                2) Se não houver controller, tenta usar o CTk raiz.
                3) Se nada existir, usa um fallback simples baseado no modo claro/escuro.
                """
                # ------------- descobrir a "fonte" das cores -------------
                aplicacao_principal = None

                # 1) controller passado pelo MENU_PRINCIPAL
                if hasattr(self, "controller") and self.controller is not None:
                    aplicacao_principal = self.controller
                else:
                    # 2) tenta o CTk raiz (quando aberto sozinho para testes)
                    try:
                        topo = self.winfo_toplevel()
                        if isinstance(topo, ctk.CTk):
                            aplicacao_principal = topo
                    except Exception:
                        aplicacao_principal = None

                # ------------- fallback genérico, só se não houver tema -------------
                modo_aparencia = ctk.get_appearance_mode()
                if modo_aparencia == "Dark":
                    default_cor_fundo = "#020617"
                    default_cor_primaria = "#111827"
                    default_cor_secundaria = "#020617"
                    default_cor_terciaria = "#111827"
                    default_cor_texto = "#E5E7EB"
                    default_cor_texto_secundario = "#9CA3AF"
                    default_cor_borda = "#273244"
                    default_cor_hover = "#334155"
                    default_cor_destaque = "#2563EB"
                    default_cor_sucesso = "#22C55E"
                    default_cor_alerta = "#EF4444"
                    default_cor_selecao = "#2563EB"
                else:
                    default_cor_fundo = "#F7F7F7"
                    default_cor_primaria = "#FFFFFF"
                    default_cor_secundaria = "#F0F2F5"
                    default_cor_terciaria = "#E5E7EB"
                    default_cor_texto = "#111827"
                    default_cor_texto_secundario = "#6B7280"
                    default_cor_borda = "#D1D5DB"
                    default_cor_hover = "#E5E7EB"
                    default_cor_destaque = "#2563EB"
                    default_cor_sucesso = "#16A34A"
                    default_cor_alerta = "#DC2626"
                    default_cor_selecao = "#2563EB"

                def obter_cor(nome_atributo, valor_default):
                    """
                    Lê a cor do atributo (por exemplo 'cor_fundo') na aplicação principal.
                    Se não existir ou for vazio, usa o valor_default.
                    """
                    if aplicacao_principal is not None and hasattr(aplicacao_principal, nome_atributo):
                        valor = getattr(aplicacao_principal, nome_atributo)
                        if isinstance(valor, str) and valor.strip():
                            return valor
                    return valor_default

                # ------------- copiar efetivamente as cores para o relatório -------------
                self.cor_fundo = obter_cor("cor_fundo", default_cor_fundo)
                self.cor_primaria = obter_cor("cor_primaria", default_cor_primaria)
                self.cor_secundaria = obter_cor("cor_secundaria", default_cor_secundaria)
                self.cor_terciaria = obter_cor("cor_terciaria", default_cor_terciaria)

                self.cor_texto = obter_cor("cor_texto", default_cor_texto)
                # entradas usam o mesmo texto padrão
                self.cor_texto_entry = obter_cor("cor_texto", default_cor_texto)
                # placeholder usa texto_secundario se existir
                self.cor_placeholder = obter_cor("cor_texto_secundario", default_cor_texto_secundario)

                self.cor_borda = obter_cor("cor_borda", default_cor_borda)
                self.cor_hover = obter_cor("cor_hover", default_cor_hover)

                self.cor_destaque = obter_cor("cor_destaque", default_cor_destaque)
                self.cor_sucesso = obter_cor("cor_sucesso", default_cor_sucesso)
                self.cor_alerta = obter_cor("cor_alerta", default_cor_alerta)
                self.cor_selecao = obter_cor("cor_selecao", default_cor_selecao)

        return DefaultController()

    def _setup_window_protocol(self):
        try:
            if hasattr(self.parent, 'protocol') and callable(self.parent.protocol):
                self.parent.protocol('WM_DELETE_WINDOW', self._safe_shutdown)
        except Exception:
            pass

    def _safe_shutdown(self):
        try:
            self._ai_worker_running = False
            if hasattr(self.parent, 'destroy'):
                self.parent.destroy()
        finally:
            pass

    def _setup_styles(self):
        """
        Configura os estilos visuais internos da página,
        sempre usando a paleta já definida em obter_cores_por_tema.
        """
        self.configurar_treeview_theme()

    def _page_lang(self):
        idioma = getattr(getattr(self, "sistema", None), "idioma_atual", None)
        if not idioma:
            idioma = getattr(getattr(self, "controller", None), "idioma_atual", None)
        if not idioma:
            idioma = "pt_BR"
        return idioma

    def _txt(self, key: str) -> str:
        labels = {
            "pt_BR": {
                "report_tab": "📋 Relatório",
                "analysis_tab": "📊 Análise",
                "assistant_tab": "🤖 Assistente",
                "search": "🔎 Buscar por código ou descrição...",
                "apply_filters": "Aplicar Filtros",
                "export_csv": "📄 Exportar CSV",
                "generate_pdf": "🖨️ Gerar PDF",
                "export_excel": "📊 Exportar Excel",
                "print": "🖨️ Imprimir",
                "header": ["ID", "Descrição", "Categoria", "Quantidade", "Status", "Localização", "Última Atualização"],
                "total_items": "🧾 Total Itens",
                "critical_items": "⚠️ Itens Críticos",
                "categories": "📂 Categorias",
                "updated": "🕒 Atualizado",
                "estimated_value": "💰 Valor Estimado",
                "by_category": "Quantidade por Categoria",
                "critical_by_category": "Itens Críticos por Categoria",
                "assistant_title": "🤖 Assistente de Estoque Inteligente",
                "assistant_ph": "Converse aqui... (Enter para enviar)",
                "send": "Enviar",
                "quick_1": "Itens críticos",
                "quick_2": "Valor do estoque",
                "quick_3": "Tecidos (metragem)",
                "quick_4": "Sugestões de compra",
                "quick_5": "Itens não movimentados há 30 dias",
                "regen": "🔁 Regenerar",
                "export_chat": "💾 Exportar conversa",
                "suggestions": "💡 Sugestões/Perguntas",
            },
            "en_US": {
                "report_tab": "📋 Report",
                "analysis_tab": "📊 Analysis",
                "assistant_tab": "🤖 Assistant",
                "search": "🔎 Search by code or description...",
                "apply_filters": "Apply Filters",
                "export_csv": "📄 Export CSV",
                "generate_pdf": "🖨️ Generate PDF",
                "export_excel": "📊 Export Excel",
                "print": "🖨️ Print",
                "header": ["ID", "Description", "Category", "Quantity", "Status", "Location", "Last Update"],
                "total_items": "🧾 Total Items",
                "critical_items": "⚠️ Critical Items",
                "categories": "📂 Categories",
                "updated": "🕒 Updated",
                "estimated_value": "💰 Estimated Value",
                "by_category": "Quantity by Category",
                "critical_by_category": "Critical Items by Category",
                "assistant_title": "🤖 Smart Stock Assistant",
                "assistant_ph": "Chat here... (Press Enter to send)",
                "send": "Send",
                "quick_1": "Critical items",
                "quick_2": "Stock value",
                "quick_3": "Fabrics (meterage)",
                "quick_4": "Purchase suggestions",
                "quick_5": "Items not moved for 30 days",
                "regen": "🔁 Regenerate",
                "export_chat": "💾 Export chat",
                "suggestions": "💡 Suggestions/Questions",
            },
            "es_ES": {
                "report_tab": "📋 Reporte",
                "analysis_tab": "📊 Análisis",
                "assistant_tab": "🤖 Asistente",
                "search": "🔎 Buscar por código o descripción...",
                "apply_filters": "Aplicar Filtros",
                "export_csv": "📄 Exportar CSV",
                "generate_pdf": "🖨️ Generar PDF",
                "export_excel": "📊 Exportar Excel",
                "print": "🖨️ Imprimir",
                "header": ["ID", "Descripción", "Categoría", "Cantidad", "Estado", "Ubicación", "Última Actualización"],
                "total_items": "🧾 Total Ítems",
                "critical_items": "⚠️ Ítems Críticos",
                "categories": "📂 Categorías",
                "updated": "🕒 Actualizado",
                "estimated_value": "💰 Valor Estimado",
                "by_category": "Cantidad por Categoría",
                "critical_by_category": "Ítems Críticos por Categoría",
                "assistant_title": "🤖 Asistente Inteligente de Stock",
                "assistant_ph": "Escriba aquí... (Enter para enviar)",
                "send": "Enviar",
                "quick_1": "Ítems críticos",
                "quick_2": "Valor del stock",
                "quick_3": "Tejidos (metraje)",
                "quick_4": "Sugerencias de compra",
                "quick_5": "Ítems sin movimiento hace 30 días",
                "regen": "🔁 Regenerar",
                "export_chat": "💾 Exportar conversación",
                "suggestions": "💡 Sugerencias/Preguntas",
            }
        }
        idioma = self._page_lang()
        return labels.get(idioma, labels["pt_BR"]).get(key, labels["pt_BR"].get(key, key))

    def _refresh_texts_runtime(self):
        try:
            if hasattr(self, 'search_entry'):
                self.search_entry.configure(placeholder_text=self._txt('search'))
            if hasattr(self, 'btn_apply_filters'):
                self.btn_apply_filters.configure(text=self._txt('apply_filters'))
            if hasattr(self, 'btn_export_csv'):
                self.btn_export_csv.configure(text=self._txt('export_csv'))
            if hasattr(self, 'btn_export_pdf'):
                self.btn_export_pdf.configure(text=self._txt('generate_pdf'))
            if hasattr(self, 'btn_export_excel'):
                self.btn_export_excel.configure(text=self._txt('export_excel'))
            if hasattr(self, 'btn_print'):
                self.btn_print.configure(text=self._txt('print'))
            if hasattr(self, 'tree'):
                headers = self._txt('header')
                cols = list(self.tree["columns"])
                for col, head in zip(cols, headers):
                    self.tree.heading(col, text=head)
            if hasattr(self, 'ai_input'):
                self.ai_input.configure(placeholder_text=self._txt('assistant_ph'))
            if hasattr(self, 'btn_send'):
                self.btn_send.configure(text=self._txt('send'))
            if hasattr(self, 'lbl_assistant_title'):
                self.lbl_assistant_title.configure(text=self._txt('assistant_title'))
            if hasattr(self, 'btn_regen'):
                self.btn_regen.configure(text=self._txt('regen'))
            if hasattr(self, 'btn_export_chat'):
                self.btn_export_chat.configure(text=self._txt('export_chat'))
            if hasattr(self, 'btn_suggestions'):
                self.btn_suggestions.configure(text=self._txt('suggestions'))
            if hasattr(self, 'quick_buttons'):
                keys = ['quick_1','quick_2','quick_3','quick_4','quick_5']
                for btn, key in zip(self.quick_buttons, keys):
                    btn.configure(text=self._txt(key))
        except Exception:
            pass

    def _create_main_layout(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header - MESMO PADRÃO DO CADASTRO_DE_CORTE
        header = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color=self.cor_primaria)
        header.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

        ctk.CTkLabel(header, text="Controle de Estoque", font=self.font_titulo,
                     text_color=_hex_contrast(self.cor_primaria)).pack(side="left", padx=20)

        ctk.CTkButton(header, text="Atualizar Dados", command=self.reload_data, width=120,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="right", padx=20)

        # Tabs - MESMO PADRÃO DO CADASTRO_DE_CORTE
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=self.cor_fundo,
            segmented_button_fg_color=self.cor_primaria,
            segmented_button_selected_color=self.cor_hover,
            segmented_button_unselected_color=self.cor_secundaria,
            segmented_button_unselected_hover_color=self.cor_hover,
            text_color=self.cor_texto
        )
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.tab_report = self.tabs.add("📋 Relatório")
        self.tab_analytics = self.tabs.add("📊 Análise")
        self.tab_ai = self.tabs.add("🤖 Assistente")

        self._setup_report_tab()
        self._setup_analytics_tab()
        self._setup_ai_tab()
        self._refresh_texts_runtime()

        # Footer - MESMO PADRÃO DO CADASTRO_DE_CORTE
        footer = ctk.CTkFrame(self, height=40, fg_color=self.cor_primaria)
        footer.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        ctk.CTkLabel(
            footer,
            text=f"🟢 Conectado | {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            font=self.font_pequeno,
            text_color=_hex_contrast(self.cor_primaria)
        ).pack(side="left", padx=20)

    # ----------------- ABA: RELATÓRIO -----------------
    def _setup_report_tab(self):
        self.tab_report.grid_rowconfigure(0, weight=1)
        self.tab_report.grid_columnconfigure(0, weight=1)

        wrapper = ctk.CTkFrame(self.tab_report, fg_color=self.cor_fundo)
        wrapper.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        wrapper.grid_rowconfigure(0, weight=0)
        wrapper.grid_rowconfigure(1, weight=1)
        wrapper.grid_rowconfigure(2, weight=0)
        wrapper.grid_columnconfigure(0, weight=1)

        # Filtros - MESMO PADRÃO DO CADASTRO_DE_CORTE
        filtros = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        filtros.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        filtros.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            filtros, placeholder_text=self._txt("search"),
            fg_color=self.cor_secundaria, border_color=self.cor_borda,
            text_color=self.cor_texto_entry, placeholder_text_color=self.cor_placeholder
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.category_var = tk.StringVar(value="Todas")
        self.combo_category = ctk.CTkComboBox(
            filtros,
            variable=self.category_var,
            values=["Todas", "Tecidos", "Aviamentos", "Insumos", "Escritorio", "Limpeza", "Outros"],
            state="readonly",
            fg_color=self.cor_secundaria, border_color=self.cor_borda,
            button_color=self.cor_primaria, button_hover_color=self.cor_hover,
            text_color=self.cor_texto, dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto, dropdown_hover_color=self.cor_hover
        )
        self.combo_category.grid(row=0, column=1, padx=(0, 8))

        self.btn_apply_filters = ctk.CTkButton(
            filtros, text=self._txt("apply_filters"), command=self.apply_filters,
            fg_color=self.cor_primaria, hover_color=self.cor_hover,
            text_color=self.cor_texto
        )
        self.btn_apply_filters.grid(row=0, column=2)

        # Tabela - MESMO PADRÃO DO CADASTRO_DE_CORTE
        self._create_stock_table(parent=wrapper)

        # Export - MESMO PADRÃO DO CADASTRO_DE_CORTE
        export_frame = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        export_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        self.btn_export_csv = ctk.CTkButton(export_frame, text=self._txt("export_csv"), fg_color=self.cor_sucesso,
                      hover_color=self.cor_hover, text_color=self.cor_texto,
                      command=self.export_csv)
        self.btn_export_csv.pack(side="left", padx=5)

        self.btn_export_pdf = ctk.CTkButton(export_frame, text=self._txt("generate_pdf"), fg_color=self.cor_alerta,
                      hover_color=self.cor_hover, text_color=self.cor_texto,
                      command=self.export_pdf)
        self.btn_export_pdf.pack(side="left", padx=5)

        self.btn_export_excel = ctk.CTkButton(export_frame, text=self._txt("export_excel"), fg_color=self.cor_destaque,
                      hover_color=self.cor_hover, text_color=self.cor_texto,
                      command=self.export_excel)
        self.btn_export_excel.pack(side="left", padx=5)

    def _create_stock_table(self, parent=None):
        if parent is None:
            parent = self.tab_report

        container = ctk.CTkFrame(parent, fg_color=self.cor_fundo)
        container.grid(row=1, column=0, sticky="nsew")
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        table_wrap = ctk.CTkFrame(container, fg_color=self.cor_fundo)
        table_wrap.grid(row=0, column=0, sticky="nsew")
        table_wrap.grid_rowconfigure(0, weight=1)
        table_wrap.grid_columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(table_wrap, orient="vertical")
        hsb = ttk.Scrollbar(table_wrap, orient="horizontal")

        # Configurar estilo da Treeview - MESMO PADRÃO DO CADASTRO_DE_CORTE
        self.configurar_treeview_theme()

        cols = ["col_id", "col_descricao", "col_categoria", "col_quantidade", "col_status", "col_localizacao", "col_ultima_atualizacao"]
        self.tree = ttk.Treeview(
            table_wrap, columns=cols, show="headings",
            style="Custom.Treeview", yscrollcommand=vsb.set, xscrollcommand=hsb.set
        )

        headers = self._txt("header")
        specs = [
            ("col_id", 80, "center"),
            ("col_descricao", 300, "w"),
            ("col_categoria", 120, "w"),
            ("col_quantidade", 90, "center"),
            ("col_status", 90, "center"),
            ("col_localizacao", 150, "w"),
            ("col_ultima_atualizacao", 140, "center"),
        ]
        for (name, width, anchor), header in zip(specs, headers):
            self.tree.heading(name, text=header)
            self.tree.column(name, width=width, anchor=anchor)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Configurar cores das linhas alternadas - MESMO PADRÃO DO CADASTRO_DE_CORTE
        if ctk.get_appearance_mode() == "Dark":
            cor_linha_par = self.cor_fundo
            cor_linha_impar = self.cor_secundaria
        else:
            cor_linha_par = "#ffffff"
            cor_linha_impar = "#f0f0f0"

        self.tree.tag_configure("oddrow", background=cor_linha_impar)
        self.tree.tag_configure("evenrow", background=cor_linha_par)

    # ----------------- ABA: ANÁLISE -----------------
    def _setup_analytics_tab(self):
        self.tab_analytics.grid_rowconfigure(0, weight=1)
        self.tab_analytics.grid_columnconfigure(0, weight=1)

        wrapper = ctk.CTkFrame(self.tab_analytics, fg_color=self.cor_fundo)
        wrapper.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        wrapper.grid_rowconfigure(1, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        self.cards_frame = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        self.cards_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for i in range(4):
            self.cards_frame.grid_columnconfigure(i, weight=1)

        self._metric_card(self.cards_frame, self._txt("total_items"), "—").grid(row=0, column=0, sticky="ew")
        self._metric_card(self.cards_frame, self._txt("critical_items"), "—").grid(row=0, column=1, sticky="ew")
        self._metric_card(self.cards_frame, self._txt("categories"), "—").grid(row=0, column=2, sticky="ew")
        self._metric_card(self.cards_frame, self._txt("updated"), "—").grid(row=0, column=3, sticky="ew")

        self.charts_frame = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        self.charts_frame.grid(row=1, column=0, sticky="nsew")
        self.charts_frame.grid_rowconfigure(0, weight=1)
        self.charts_frame.grid_columnconfigure(0, weight=1)

        self._create_analytics_charts()
        self._create_metrics_panel()

    def _metric_card(self, parent, title, value="—"):
        card = ctk.CTkFrame(parent, fg_color=self.cor_secundaria, corner_radius=10)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, text_color=self.cor_texto).grid(
            row=0, column=0, padx=10, pady=(8, 0), sticky="w"
        )
        ctk.CTkLabel(card, text=str(value), font=("Segoe UI", 18, "bold"),
                     text_color=self.cor_texto).grid(
            row=1, column=0, padx=10, pady=(2, 10), sticky="w"
        )
        return card

    def _create_analytics_charts(self):
        if not self.resultados or not MATPLOTLIB_AVAILABLE:
            ctk.CTkLabel(self.charts_frame, text="Matplotlib não disponível para gráficos",
                         text_color=self.cor_texto).grid(row=0, column=0, sticky="nsew")
            return

        categories = {}
        critical_items = {}
        for item in self.resultados:
            cat = item[2] or "—"
            qty = float(item[3] or 0)
            categories[cat] = categories.get(cat, 0) + 1
            if qty < 10:
                critical_items[cat] = critical_items.get(cat, 0) + 1

        plt.rcParams.update({'axes.facecolor': self.cor_secundaria})
        fig = plt.figure(figsize=(10, 4))
        fig.patch.set_facecolor(self.cor_secundaria)

        ax1 = fig.add_subplot(1, 2, 1)
        ax1.bar(list(categories.keys()), list(categories.values()))
        ax1.set_title(self._txt('by_category'))
        ax1.tick_params(axis='x', rotation=45)

        ax2 = fig.add_subplot(1, 2, 2)
        ax2.bar(list(critical_items.keys()), list(critical_items.values()))
        ax2.set_title(self._txt('critical_by_category'))
        ax2.tick_params(axis='x', rotation=45)

        fig.tight_layout()

        if hasattr(self, 'chart_canvas'):
            try:
                self.chart_canvas.get_tk_widget().destroy()
            except Exception:
                pass
        self.chart_canvas = FigureCanvasTkAgg(fig, master=self.charts_frame)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def _create_metrics_panel(self):
        if hasattr(self, "metrics_frame") and self.metrics_frame is not None:
            try:
                self.metrics_frame.destroy()
            except Exception:
                pass

        parent = self.charts_frame
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=0)
        parent.grid_columnconfigure(0, weight=1)

        self.metrics_frame = ctk.CTkFrame(parent, fg_color=self.cor_fundo)
        self.metrics_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.metrics_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def _metric(title, value):
            box = ctk.CTkFrame(self.metrics_frame, fg_color=self.cor_secundaria, corner_radius=10)
            ctk.CTkLabel(box, text=title, text_color=self.cor_texto).pack(
                anchor="w", padx=10, pady=(8, 0)
            )
            ctk.CTkLabel(box, text=str(value), font=self.font_metrica,
                         text_color=self.cor_texto).pack(
                anchor="w", padx=10, pady=(2, 10)
            )
            return box

        _metric(self._txt("total_items"), self.stats_data.get("total_items", 0)).grid(row=0, column=0, sticky="ew", padx=6)
        _metric(self._txt("critical_items"), self.stats_data.get("low_stock", 0)).grid(row=0, column=1, sticky="ew", padx=6)
        _metric(self._txt("categories"), self.stats_data.get("categories", 0)).grid(row=0, column=2, sticky="ew", padx=6)
        _metric(self._txt("estimated_value"), f"{self.stats_data.get('total_value', 0):,.2f}").grid(
            row=0, column=3, sticky="ew", padx=6
        )

    # ----------------- ABA: ASSISTENTE -----------------
    def _setup_ai_tab(self):
        self.tab_ai.grid_rowconfigure(0, weight=1)
        self.tab_ai.grid_columnconfigure(0, weight=1)

        wrapper = ctk.CTkFrame(self.tab_ai, fg_color=self.cor_fundo)
        wrapper.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        wrapper.grid_rowconfigure(1, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(wrapper, height=48, fg_color=self.cor_primaria)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.grid_columnconfigure(0, weight=1)
        self.lbl_assistant_title = ctk.CTkLabel(header, text=self._txt("assistant_title"),
                     font=self.font_titulo_medio, text_color=_hex_contrast(self.cor_primaria))
        self.lbl_assistant_title.grid(
            row=0, column=0, sticky="w", padx=12, pady=10
        )

        body = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=0)
        body.grid_columnconfigure(0, weight=1)

        self.chat_canvas = tk.Canvas(body, bg=self.cor_fundo, highlightthickness=0, bd=0)
        self.chat_scroll = ttk.Scrollbar(body, orient="vertical", command=self.chat_canvas.yview)
        self.chat_frame = ctk.CTkFrame(self.chat_canvas, fg_color=self.cor_fundo)
        self.chat_frame.bind("<Configure>",
                             lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))
        self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        self.chat_canvas.configure(yscrollcommand=self.chat_scroll.set)

        self.chat_canvas.grid(row=0, column=0, sticky="nsew")
        self.chat_scroll.grid(row=0, column=1, sticky="ns")

        input_frame = ctk.CTkFrame(body, height=52, fg_color=self.cor_secundaria, corner_radius=12)
        input_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(6, 8))
        input_frame.grid_columnconfigure(0, weight=1)

        self.ai_input = ctk.CTkEntry(
            input_frame,
            placeholder_text=self._txt("assistant_ph"),
            fg_color=self.cor_secundaria,
            text_color=self.cor_texto_entry,
            placeholder_text_color=self.cor_placeholder
        )
        self.ai_input.grid(row=0, column=0, sticky="ew", padx=(10, 8), pady=8)
        self.ai_input.bind("<Return>", self.process_ai_query)

        self.btn_send = ctk.CTkButton(
            input_frame, text=self._txt("send"), command=self.process_ai_query,
            fg_color=self.cor_destaque, hover_color=self.cor_hover,
            text_color=self.cor_texto, width=90
        )
        self.btn_send.grid(row=0, column=1, padx=(0, 10))

        self.quick_actions = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        self.quick_actions.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self.quick_buttons = []
        quick_keys = ["quick_1", "quick_2", "quick_3", "quick_4", "quick_5"]
        for i, key in enumerate(quick_keys):
            text = self._txt(key)
            btn = ctk.CTkButton(self.quick_actions, text=text, width=1,
                                fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                                text_color=self.cor_texto,
                                command=lambda t=text: self._send_quick(t))
            btn.grid(row=0, column=i, padx=4)
            self.quick_buttons.append(btn)

        self.extra_actions = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        self.extra_actions.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        self.btn_regen = ctk.CTkButton(self.extra_actions, text=self._txt("regen"), command=self._regenerate_last,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto)
        self.btn_regen.pack(side="left", padx=4)
        self.btn_export_chat = ctk.CTkButton(self.extra_actions, text=self._txt("export_chat"), command=self._export_chat,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto)
        self.btn_export_chat.pack(side="left", padx=4)
        self.btn_suggestions = ctk.CTkButton(self.extra_actions, text=self._txt("suggestions"), command=self._open_suggestions_window,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto)
        self.btn_suggestions.pack(side="left", padx=4)

        self._post_bot(
            "👋 Olá! Pergunte sobre *críticos*, *valor*, *tecidos*, *localização* ou digite o *código* do item.",
            slow=False)

    def _post_bubble(self, text, from_user=True):
        wrap = ctk.CTkFrame(self.chat_frame, fg_color=self.cor_fundo)
        wrap.pack(fill="x", padx=8, pady=2)

        bubble_color = self.cor_destaque if from_user else self.cor_secundaria
        text_color = _hex_contrast(bubble_color) if from_user else self.cor_texto
        anchor_side = "e" if from_user else "w"

        bubble = ctk.CTkFrame(wrap, fg_color=bubble_color if from_user else bubble_color, corner_radius=14)
        bubble.pack(anchor=anchor_side, padx=6, pady=2)

        label = ctk.CTkLabel(bubble, text=text, justify="left", text_color=text_color, wraplength=720)
        label.pack(padx=10, pady=8)

        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def _post_user(self, text):
        self._post_bubble(text, from_user=True)

    def _post_bot(self, text, slow=True):
        if not slow:
            self._post_bubble(text, from_user=False)
            return
        typing_id = self._show_typing()

        def _run():
            time.sleep(min(0.3 + len(text) / 120.0, 2.5))
            self._hide_typing(typing_id)
            self._post_bubble(text, from_user=False)

        threading.Thread(target=_run, daemon=True).start()

    def _show_typing(self):
        wrap = ctk.CTkFrame(self.chat_frame, fg_color=self.cor_fundo)
        wrap.pack(fill="x", padx=8, pady=2)
        bubble = ctk.CTkFrame(wrap, fg_color=self.cor_secundaria, corner_radius=14)
        bubble.pack(anchor="w", padx=6, pady=2)
        label = ctk.CTkLabel(bubble, text="digitando...", text_color=self.cor_texto)
        label.pack(padx=10, pady=8)
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)
        return wrap

    def _hide_typing(self, widget):
        try:
            widget.destroy()
        except Exception:
            pass

    def _send_quick(self, text):
        self.ai_input.delete(0, "end")
        self.ai_input.insert(0, text)
        self.process_ai_query()

    def _regenerate_last(self):
        if not self._last_user_prompt:
            messagebox.showinfo("Regenerar", "Ainda não há mensagem para regenerar.")
            return
        self._enqueue_ai(self._last_user_prompt, is_regen=True)

    def _export_chat(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Texto", "*.txt")], title="Salvar conversa"
        )
        if not filename:
            return
        try:
            lines = []
            for child in self.chat_frame.winfo_children():
                for sub in child.winfo_children():
                    for lbl in sub.winfo_children():
                        if isinstance(lbl, ctk.CTkLabel):
                            lines.append(lbl.cget("text"))
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            messagebox.showinfo("Exportar", "Conversa salva com sucesso.")
        except Exception as e:
            messagebox.showerror("Exportar", f"Falha ao salvar: {e}")

    def _recolor_labels_frame(self, frame):
        """Recursivamente recolore todos os labels em um frame - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        for widget in frame.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=self.cor_texto)
            if hasattr(widget, "winfo_children"):
                self._recolor_labels_frame(widget)

    def _validar_numero(self, valor):
        """Validação de números - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        if valor == "":
            return True
        try:
            float(valor)
            return True
        except ValueError:
            return False

    def diagnosticar_widgets(self):
        """Diagnóstico de widgets - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        widgets = {
            'search_entry': self.search_entry,
            'combo_category': self.combo_category,
            'tree': self.tree,
            'ai_input': self.ai_input,
            'btn_send': self.btn_send
        }
        problemas = [nome for nome, widget in widgets.items() if widget is None]

        if problemas:
            message = "Widgets não inicializados:\n- " + "\n- ".join(problemas)
            messagebox.showerror("Problema de Inicialização", message)
        else:
            messagebox.showinfo("Diagnóstico", "Todos os widgets foram inicializados corretamente")

    def verificar_inicializacao_widgets(self):
        """Verificação de inicialização - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        widgets_essenciais = [
            self.search_entry, self.combo_category, self.tree,
            self.ai_input, self.btn_send
        ]

        for widget in widgets_essenciais:
            if widget is None:
                print(f"Widget não inicializado: {widget}")

    def _formatar_metros(self, valor) -> str:
        """Formatação de metros - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        try:
            if valor is None or (isinstance(valor, str) and not valor.strip()):
                return "0"
            from decimal import Decimal
            dec = Decimal(str(valor))
            if dec == dec.to_integral():
                inteiro = int(dec)
                return f"{inteiro:,}".replace(",", ".")
            parte_int = int(dec)
            parte_frac = abs(dec - parte_int)
            int_str = f"{parte_int:,}".replace(",", ".")
            frac_str = f"{parte_frac:.3f}"[2:]
            frac_str = frac_str.rstrip('0')
            if not frac_str:
                return int_str
            return f"{int_str},{frac_str}"
        except Exception:
            try:
                num = float(valor)
            except Exception:
                return str(valor)
            return f"{num:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    def carregar_logo(self):
        """Carregamento de logo - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        try:
            # Import do PIL dentro da função para evitar erro se não estiver disponível
            try:
                from PIL import Image
            except ImportError:
                print("PIL/Pillow não disponível para carregar logo")
                self.logo_image = None
                return False

            possiveis_logos = [
                "logo.png", "logo.jpg", "logo.jpeg", "logo.gif", "logo.bmp",
                os.path.join(os.path.dirname(__file__), "logo.png"),
                os.path.join(os.path.dirname(__file__), "logo.jpg"),
                os.path.join(os.path.dirname(__file__), "imgs", "logo.png"),
                os.path.join(os.path.dirname(__file__), "imgs", "logo.jpg"),
                os.path.join(os.path.dirname(__file__), "assets", "logo.png"),
                os.path.join(os.path.dirname(__file__), "assets", "logo.jpg"),
                os.path.join(os.path.dirname(__file__), "..", "logo.png"),
                os.path.join(os.path.dirname(__file__), "..", "logo.jpg")
            ]

            for logo_path in possiveis_logos:
                try:
                    if os.path.exists(logo_path):
                        # Carregar e redimensionar a imagem
                        original_image = Image.open(logo_path)

                        # Manter proporção da imagem
                        width, height = original_image.size
                        new_width = 150
                        new_height = int((new_width / width) * height)

                        # Redimensionar se necessário
                        if new_height > 80:  # Limitar altura máxima
                            new_height = 80
                            new_width = int((new_height / height) * width)

                        self.logo_image = ctk.CTkImage(
                            light_image=original_image,
                            dark_image=original_image,  # Mesma imagem para ambos os temas
                            size=(new_width, new_height)
                        )
                        print(f"Logo carregada: {logo_path} ({new_width}x{new_height})")
                        return True

                except Exception as e:
                    print(f"Erro ao carregar {logo_path}: {str(e)}")
                    continue

            # Se não encontrou logo, criar um placeholder
            print("Nenhuma logo encontrada, criando placeholder...")
            self.logo_image = None
            return False

        except Exception as e:
            print(f"Erro crítico ao carregar logo: {str(e)}")
            self.logo_image = None
            return False

    def _limpar_totais(self):
        """Limpeza de totais - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        self.total_folhas_var = ctk.StringVar(value="0")
        self.metros_utilizados_var = ctk.StringVar(value="0.00")
        self.bobinas_utilizadas_var = ctk.StringVar(value="0")
        self.total_pecas_var = ctk.StringVar(value="0")
        self.rendimento_var = ctk.StringVar(value="0.00")

    def limpar_cache_pagina(self):
        """Limpeza de cache - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        pass

    def get_state(self):
        """Obter estado atual - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        state = {
            'filtro_pesquisa': self.search_entry.get(),
            'categoria_filtro': self.category_var.get(),
            'dados_tabela': []
        }

        for item in self.tree.get_children():
            valores = self.tree.item(item, "values")
            state['dados_tabela'].append(valores)

        return state

    def set_state(self, state):
        """Restaurar estado - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        if not state:
            return

        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, state.get('filtro_pesquisa', ''))

        self.category_var.set(state.get('categoria_filtro', 'Todas'))

        for item in self.tree.get_children():
            self.tree.delete(item)

        for valores in state.get('dados_tabela', []):
            self.tree.insert("", "end", values=valores)

        self.apply_filters()

    def _get_text(self, *attr_names, default=""):
        """Obter texto de widgets - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        for name in attr_names:
            try:
                obj = getattr(self, name, None)
                if obj is None:
                    continue
                if hasattr(obj, "get") and callable(getattr(obj, "get")):
                    val = obj.get()
                    return ("" if val is None else str(val)).strip()
            except Exception:
                continue
        return default

    def verificar_estrutura_tabela(self):
        """Verificação de estrutura de tabela - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        try:
            conn = db.get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = current_schema()
                      AND table_name LIKE 'estoque_%'
                    LIMIT 1
                """)
                ok = cur.fetchone() is not None
            conn.close()
            if not ok:
                messagebox.showerror(
                    "Tabela não encontrada",
                    "Nenhuma tabela de estoque encontrada! Verifique a estrutura do banco."
                )
                return False
            return True
        except Exception as e:
            messagebox.showerror("Erro no Banco de Dados",
                                 f"Falha ao verificar tabelas de estoque:\n{str(e)}")
            return False

    def _conectar_banco_dados(self):
        """Conexão com banco - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        try:
            conn = db.get_connection()
            conn.close()
            self.conn = None
            self.cursor = None
        except Exception as e:
            messagebox.showerror("Erro de Banco de Dados",
                                 f"Não foi possível conectar ao banco de dados:\n{str(e)}")
            self.master.destroy()

    def _cols_tabela(self, tabela: str) -> set:
        """Obter colunas da tabela - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        try:
            conn = db.get_connection()
            with conn.cursor() as c:
                c.execute("""
                       SELECT column_name
                       FROM information_schema.columns
                       WHERE table_schema = current_schema()
                         AND table_name = %s
                   """, (tabela,))
                return {r[0].lower() for r in c.fetchall()}
        except Exception:
            return set()
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def carregar_dados_iniciais(self):
        """Carregar dados iniciais - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        self.carregar_logo()
        self.reload_data()

    def _recarregar_modelos_ocf(self):
        """Recarregar modelos - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        # Implementação simplificada para compatibilidade
        try:
            conn = db.get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT categoria 
                    FROM estoque_tecidos 
                    WHERE categoria IS NOT NULL
                """)
                categorias = [r[0] for r in cur.fetchall()]

            if hasattr(self, 'combo_category'):
                valores_atual = list(self.combo_category.cget('values'))
                if 'Todas' not in valores_atual:
                    self.combo_category.configure(values=['Todas'] + categorias)
        except Exception as e:
            print(f"Erro ao recarregar categorias: {e}")

    def _on_modelo_ocf_selected(self, value: str):
        """Callback de seleção de modelo - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        # Implementação para compatibilidade com a estrutura do Cadastro de Corte
        try:
            if hasattr(self, 'search_entry') and self.search_entry:
                self.search_entry.delete(0, "end")
                self.search_entry.insert(0, value)
                self.apply_filters()
        except Exception as e:
            print(f"Erro ao processar seleção: {e}")

    def _remover_da_ordem_corte_ficha_tx(self, cur, codigo: str) -> int:
        """Remover da ordem de corte - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        # Implementação de compatibilidade
        return 0

    def _buscar_tecidos_para_adicao(self, search_entry, tecido_tree):
        """Buscar tecidos para adição - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        try:
            termo = search_entry.get().strip().lower()
            if not termo:
                messagebox.showwarning("Aviso", "Digite um termo para busca!")
                return

            tecido_tree.delete(*tecido_tree.get_children())

            conn = db.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                       SELECT codigo, descricao, categoria, quantidade, localizacao
                       FROM estoque_tecidos 
                       WHERE (LOWER(codigo) LIKE %s OR 
                              LOWER(descricao) LIKE %s OR 
                              LOWER(categoria) LIKE %s)
                       ORDER BY descricao
                   """, (f"%{termo}%", f"%{termo}%", f"%{termo}%"))

                rows = cursor.fetchall()

            for row in rows:
                codigo, descricao, categoria, quantidade, localizacao = row
                status = "Crítico" if quantidade < 10 else "Normal" if quantidade > 0 else "Zerado"
                tecido_tree.insert(
                    "",
                    "end",
                    values=(codigo, descricao, categoria, quantidade, localizacao, status),
                    tags=('esgotado',) if quantidade <= 0 else ()
                )

            if not tecido_tree.get_children():
                messagebox.showinfo("Informação", "Nenhum item encontrado com o termo buscado.")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha na busca:\n{str(e)}")

    def _confirmar_adicao_tecido(self, dialog, tecido_tree, cor_cb, bobinas_entry, folhas_entry, tamanho_entries):
        """Confirmar adição de tecido - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        try:
            selecionado = tecido_tree.selection()
            if not selecionado:
                raise ValueError("Selecione um item na lista")

            item = tecido_tree.item(selecionado[0])
            valores = item['values']

            dados_item = {
                'codigo': valores[0],
                'descricao': valores[1],
                'categoria': valores[2],
                'quantidade': valores[3],
                'localizacao': valores[4]
            }

            # Adicionar à tabela principal
            valores_tabela = [
                dados_item['codigo'],
                dados_item['descricao'],
                dados_item['categoria'],
                dados_item['quantidade'],
                "Crítico" if dados_item['quantidade'] < 10 else "Normal",
                dados_item['localizacao'],
                datetime.now().strftime("%d/%m/%Y")
            ]

            tag = 'evenrow' if len(self.tree.get_children()) % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=valores_tabela, tags=(tag,))

            dialog.destroy()
            messagebox.showinfo("Sucesso", "Item adicionado com sucesso!")

        except ValueError as e:
            messagebox.showerror("Erro de Validação", str(e))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao adicionar item:\n{str(e)}")

    def adicionar_tecido(self):
        """Diálogo para adicionar tecido - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Adicionar Item do Estoque")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.focus_force()

        # Centralizar janela
        dialog.update_idletasks()
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        largura = 800
        altura = 600
        x = (sw - largura) // 2
        y = (sh - altura) // 2
        dialog.geometry(f"{largura}x{altura}+{x}+{y}")

        # Aplicar tema
        self.obter_cores_por_tema()

        main_frame = ctk.CTkScrollableFrame(dialog, fg_color=self.cor_fundo)
        main_frame.pack(fill="both", expand=True, padx=10, pady=(10, 18))

        search_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        search_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(search_frame, text="Buscar Item (código/descrição/categoria):",
                     width=150, anchor="w", text_color=self.cor_texto).pack(side="left", padx=5)

        search_entry = ctk.CTkEntry(search_frame,
                                    fg_color=self.cor_secundaria,
                                    border_color=self.cor_borda,
                                    text_color=self.cor_texto_entry,
                                    placeholder_text_color=self.cor_placeholder)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)

        tree_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        tree_frame.pack(fill="both", expand=True, pady=5)

        columns = ["Código", "Descrição", "Categoria", "Quantidade", "Localização", "Status"]
        tecido_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8, style="Custom.Treeview")

        for col in columns:
            tecido_tree.heading(col, text=col)
            if col == "Descrição":
                tecido_tree.column(col, width=150, anchor='w')
            elif col == "Categoria":
                tecido_tree.column(col, width=100, anchor='w')
            elif col == "Localização":
                tecido_tree.column(col, width=100, anchor='w')
            else:
                tecido_tree.column(col, width=80, anchor='center')

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tecido_tree.yview)
        scrollbar.pack(side="right", fill="y")
        tecido_tree.configure(yscrollcommand=scrollbar.set)
        tecido_tree.pack(fill="both", expand=True)
        tecido_tree.tag_configure('esgotado', foreground='red')

        def do_busca():
            self._buscar_tecidos_para_adicao(search_entry, tecido_tree)

        btn_buscar = ctk.CTkButton(search_frame, text="Buscar", width=80, command=do_busca,
                                   fg_color=self.cor_primaria, hover_color=self.cor_hover,
                                   text_color=self.cor_texto)
        btn_buscar.pack(side="left", padx=5)
        search_entry.bind("<Return>", lambda event: do_busca())

        btn_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
        btn_frame.pack(fill="x", pady=(10, 20))

        btn_confirmar = ctk.CTkButton(
            btn_frame,
            text="Confirmar Seleção",
            command=lambda: self._confirmar_adicao_tecido(
                dialog, tecido_tree, None, None, None, None
            ),
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            width=120,
            text_color=self.cor_texto
        )
        btn_confirmar.pack(side="left", padx=5)

        btn_cancelar = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            command=dialog.destroy,
            fg_color=self.cor_secundaria,
            hover_color=self.cor_hover,
            width=120,
            text_color=self.cor_texto
        )
        btn_cancelar.pack(side="right", padx=5)

        search_entry.focus_set()

    def remover_tecido(self):
        """Remover item selecionado - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um item para remover!")
            return

        if messagebox.askyesno("Confirmar", "Deseja remover o item selecionado?"):
            self.tree.delete(selecionado[0])
            self.calcular_totais()

    def limpar_tabela(self):
        """Limpar tabela - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        if messagebox.askyesno("Confirmar", "Deseja limpar toda a tabela?"):
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.calcular_totais()

    def limpar_tudo(self):
        """Limpar tudo - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        if not messagebox.askyesno("Confirmar", "Deseja limpar todos os filtros e dados?"):
            return

        try:
            self.search_entry.delete(0, "end")
            self.category_var.set("Todas")

            for item in self.tree.get_children():
                self.tree.delete(item)

            # Recarregar dados originais
            self.reload_data()

            messagebox.showinfo("Sucesso", "Todos os dados foram limpos!")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao limpar dados:\n{e}")

    def salvar_ordem(self):
        """Salvar ordem - MESMO PADRÃO DO CADASTRO_DE_CORTE"""
        # Para compatibilidade com a estrutura do Cadastro de Corte
        messagebox.showinfo("Informação", "Use a função de exportação para salvar os dados do relatório.")

    def reload_data(self):
        ok, msg = db.require_ready()
        if not ok:
            messagebox.showerror("Banco de dados", f"Falha: {msg}")
            return

        schema = db.get_schema()
        resultados = []
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {db.get_schema()};")
                    cur.execute("""
                        SELECT table_name
                          FROM information_schema.tables
                         WHERE table_schema = %s AND table_name LIKE 'estoque_%%'
                    """, (schema,))
                    tabelas = [r[0] for r in cur.fetchall()]

                    for tabela in tabelas:
                        cur.execute("""
                            SELECT column_name
                              FROM information_schema.columns
                             WHERE table_schema = %s AND table_name = %s
                        """, (schema, tabela))
                        cols = [c[0] for c in cur.fetchall()]
                        have = set(cols)

                        if not {"codigo", "descricao"}.issubset(have):
                            continue

                        qtd_field = next((f for f in ["quantidade", "metros", "qtd", "estoque"] if f in have), None)
                        if not qtd_field:
                            continue

                        loc_field = next((f for f in ["localizacao", "local", "endereco", "posicao"] if f in have),
                                         None)
                        date_field = next(
                            (f for f in ["data_atualizacao", "ultima_atualizacao", "atualizado_em", "updated_at"] if
                             f in have), None)
                        cat_field = "categoria" if "categoria" in have else None
                        status_field = "status" if "status" in have else None

                        sel = ["codigo", "descricao"]
                        sel.append(cat_field if cat_field else f"'{tabela}' as categoria")
                        sel.append(qtd_field)
                        sel.append(status_field if status_field else "NULL as status")
                        sel.append(loc_field if loc_field else "NULL as localizacao")
                        sel.append(date_field if date_field else "NULL as ultima_atualizacao")

                        sql = f"SELECT {', '.join(sel)} FROM {schema}.{tabela}"
                        cur.execute(sql)
                        for row in cur.fetchall():
                            codigo = row[0]
                            descricao = row[1]
                            categoria = row[2]
                            quantidade = float(row[3]) if row[3] is not None else 0.0
                            status = row[4]
                            localizacao = row[5]
                            dt = row[6]
                            ultima = _fmt_date(dt)
                            resultados.append((codigo, descricao, categoria, quantidade, status, localizacao, ultima))
        except Exception as e:
            messagebox.showerror("Leitura do banco", f"Erro ao consultar: {e}")
            return

        self.resultados = resultados
        self._refresh_table()
        self._recalc_stats()
        self._create_analytics_charts()
        self._create_metrics_panel()
        self.assistente = EstoqueIAAvancada(self.resultados)

    # ---------- IA + BANCO (consultas inteligentes) ----------
    def _get_ai_sources(self, cur, schema: str):
        """Mapeia tabelas/colunas de estoque para consultas IA sem hardcode."""
        now = time.time()
        if self._ai_schema_cache and (now - self._ai_schema_cache_ts) < 300:
            return self._ai_schema_cache

        cur.execute("""
            SELECT table_name
              FROM information_schema.tables
             WHERE table_schema = %s
               AND table_name LIKE 'estoque_%%'
             ORDER BY table_name
        """, (schema,))
        tabelas = [r[0] for r in cur.fetchall()]

        fontes = []
        for tabela in tabelas:
            cur.execute("""
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = %s
                   AND table_name = %s
            """, (schema, tabela))
            cols = {c[0].lower() for c in cur.fetchall()}
            if not {"codigo", "descricao"}.issubset(cols):
                continue

            qtd_field = next((f for f in ("quantidade", "metros", "qtd", "estoque") if f in cols), None)
            if not qtd_field:
                continue
            fontes.append({
                "tabela": tabela,
                "grupo": tabela.replace("estoque_", ""),
                "qtd": qtd_field,
                "cat": "categoria" if "categoria" in cols else None,
                "status": "status" if "status" in cols else None,
                "local": next((f for f in ("localizacao", "local", "endereco", "posicao") if f in cols), None),
                "cor": next((f for f in ("cor", "cores", "color") if f in cols), None),
                "fornecedor": next((f for f in ("fornecedor", "fornecedor_nome", "prestador", "provider") if f in cols), None),
                "data": next((f for f in ("data_atualizacao", "ultima_atualizacao", "atualizado_em", "updated_at")
                              if f in cols), None),
            })

        self._ai_schema_cache = fontes
        self._ai_schema_cache_ts = now
        return fontes

    def _ai_parse_query(self, pergunta: str) -> dict:
        q = (pergunta or "").strip().lower()
        nums = [int(x) for x in re.findall(r"(?<!\w)(\d+)(?!\w)", q)]
        stopwords = {
            "o", "a", "os", "as", "de", "do", "da", "dos", "das", "e", "ou", "em", "no", "na", "nos", "nas",
            "para", "por", "com", "sem", "que", "qual", "quais", "quanto", "quantos", "tem", "temos", "ia",
            "banco", "estoque", "item", "itens", "verifique", "mostrar", "mostre", "procure", "buscar", "algo"
            , "cores", "cor", "fornecedor", "fornecedores", "categoria", "categorias", "local", "locais"
        }
        termos_livres = [t for t in re.findall(r"[a-z0-9áéíóúãõç_-]+", q) if len(t) >= 3 and t not in stopwords]

        grupo_alvo = None
        mapa_grupo = {
            "tecido": "tecidos", "tecidos": "tecidos",
            "aviamento": "aviamentos", "aviamentos": "aviamentos",
            "insumo": "insumos", "insumos": "insumos",
            "escritorio": "escritorio", "escritório": "escritorio",
            "limpeza": "limpeza",
            "outro": "outros", "outros": "outros",
        }
        for termo, grupo in mapa_grupo.items():
            if termo in q:
                grupo_alvo = grupo
                break

        codigo = None
        m_cod = re.search(r"c[oó]d(?:igo)?\s*[:#]?\s*([a-z0-9_.\-/]+)", q)
        if m_cod:
            codigo = m_cod.group(1).strip()

        limiar = None
        m_lim = re.search(r"(?:abaixo|menor(?:es)? que|acima|maior(?:es)? que)\s*(\d+)", q)
        if m_lim:
            limiar = int(m_lim.group(1))

        top_n = None
        m_top = re.search(r"\b(?:top|maiores?)\s*(\d{1,3})\b", q)
        if m_top:
            top_n = int(m_top.group(1))
        elif "top" in q and nums:
            top_n = nums[0]

        bottom_n = None
        m_bot = re.search(r"\b(?:bottom|menores?)\s*(\d{1,3})\b", q)
        if m_bot:
            bottom_n = int(m_bot.group(1))

        m_cat = re.search(r"categoria\s+([\w\s_/\-]+)", q)
        categoria = (m_cat.group(1).strip(" ?.,;:") if m_cat else None)

        m_loc = re.search(r"(?:local|localiza(?:ç|c)ão|setor|dep[oó]sito)\s+([\w\s_/\-]+)", q)
        local = (m_loc.group(1).strip(" ?.,;:") if m_loc else None)
        m_cor = re.search(r"cor(?:es)?\s+([\w\s_/\-]+)", q)
        cor = (m_cor.group(1).strip(" ?.,;:") if m_cor else None)
        m_forn = re.search(r"(?:fornecedor|fornecedores|prestador|prestadores)\s+([\w\s_/\-]+)", q)
        fornecedor = (m_forn.group(1).strip(" ?.,;:") if m_forn else None)

        return {
            "raw": q,
            "codigo": codigo,
            "limiar": limiar,
            "top_n": top_n,
            "bottom_n": bottom_n,
            "categoria": categoria,
            "local": local,
            "cor": cor,
            "fornecedor": fornecedor,
            "grupo_alvo": grupo_alvo,
            "termos_livres": termos_livres[:6],
            "is_critico": any(k in q for k in ("crítico", "critico", "baixo estoque", "repor urgente")),
            "is_valor": any(k in q for k in ("valor", "financeiro", "patrimônio", "patrimonio")),
            "is_contagem": any(k in q for k in ("quantos", "contagem", "total itens", "total de itens")),
            "is_busca": any(k in q for k in ("buscar", "procurar", "encontrar", "detalhe", "detalhes")),
            "is_banco": any(k in q for k in ("banco", "tempo real", "agora", "atualizado")),
            "is_cores": any(k in q for k in ("cor", "cores")),
            "is_fornecedores": any(k in q for k in ("fornecedor", "fornecedores", "prestador", "prestadores")),
            "is_abaixo": any(k in q for k in ("abaixo", "menor")),
            "is_acima": any(k in q for k in ("acima", "maior")),
        }

    def _ai_query_database(self, pergunta: str) -> Optional[str]:
        """Resposta IA com consulta dinâmica no banco para perguntas estratégicas."""
        p = self._ai_parse_query(pergunta)

        schema = db.get_schema()
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL search_path = {schema};")
                    fontes = self._get_ai_sources(cur, schema)
                    if not fontes:
                        return "ℹ️ Não encontrei tabelas de estoque válidas para consulta IA."

                    union_parts = []
                    for f in fontes:
                        cat = f["cat"] if f["cat"] else f"'{f['tabela']}'"
                        status = f["status"] if f["status"] else "NULL"
                        local = f["local"] if f["local"] else "NULL"
                        cor = f["cor"] if f["cor"] else "NULL"
                        fornecedor = f["fornecedor"] if f["fornecedor"] else "NULL"
                        data = f["data"] if f["data"] else "NULL"
                        union_parts.append(
                            f"SELECT codigo, descricao, {cat} AS categoria, "
                            f"COALESCE({f['qtd']},0)::numeric AS quantidade, "
                            f"{status} AS status, {local} AS localizacao, {cor} AS cor, {fornecedor} AS fornecedor, "
                            f"{data} AS ultima_atualizacao, "
                            f"'{f['grupo']}' AS origem_grupo, "
                            f"'{f['tabela']}' AS origem "
                            f"FROM {schema}.{f['tabela']}"
                        )

                    cte = " WITH estoque_unificado AS (" + " UNION ALL ".join(union_parts) + ") "
                    filtros = []
                    params = []

                    if p["codigo"]:
                        filtros.append("LOWER(CAST(codigo AS text)) = %s")
                        params.append(p["codigo"].lower())
                    if p["categoria"]:
                        filtros.append("LOWER(COALESCE(categoria,'')) LIKE %s")
                        params.append(f"%{p['categoria'].lower()}%")
                    if p["local"]:
                        filtros.append("LOWER(COALESCE(localizacao,'')) LIKE %s")
                        params.append(f"%{p['local'].lower()}%")
                    if p["cor"]:
                        filtros.append("LOWER(COALESCE(cor,'')) LIKE %s")
                        params.append(f"%{p['cor'].lower()}%")
                    if p["fornecedor"]:
                        filtros.append("LOWER(COALESCE(fornecedor,'')) LIKE %s")
                        params.append(f"%{p['fornecedor'].lower()}%")
                    if p.get("grupo_alvo"):
                        filtros.append("LOWER(COALESCE(origem_grupo,'')) = %s")
                        params.append(p["grupo_alvo"].lower())

                    termos_busca = list(p["termos_livres"] or [])
                    if p.get("grupo_alvo"):
                        termos_busca = [t for t in termos_busca if t != p["grupo_alvo"]]
                    if p["is_cores"] and not p["cor"]:
                        termos_busca = [t for t in termos_busca if t not in {"cores", "cor"}]
                    if p["is_fornecedores"] and not p["fornecedor"]:
                        termos_busca = [t for t in termos_busca if t not in {"fornecedor", "fornecedores"}]

                    for termo in termos_busca:
                        filtros.append(
                            "(LOWER(COALESCE(descricao,'')) LIKE %s "
                            "OR LOWER(COALESCE(categoria,'')) LIKE %s "
                            "OR LOWER(COALESCE(origem_grupo,'')) LIKE %s "
                            "OR LOWER(COALESCE(localizacao,'')) LIKE %s "
                            "OR LOWER(COALESCE(cor,'')) LIKE %s "
                            "OR LOWER(COALESCE(fornecedor,'')) LIKE %s "
                            "OR LOWER(CAST(codigo AS text)) LIKE %s)"
                        )
                        like_term = f"%{termo}%"
                        params.extend([like_term, like_term, like_term, like_term, like_term, like_term, like_term])

                    if p["is_critico"] and not p["limiar"]:
                        filtros.append("quantidade < 10")
                    if p["limiar"] is not None:
                        if p["is_acima"]:
                            filtros.append("quantidade > %s")
                        else:
                            filtros.append("quantidade < %s")
                        params.append(p["limiar"])

                    where_sql = (" WHERE " + " AND ".join(filtros)) if filtros else ""

                    if p["is_fornecedores"]:
                        sql = cte + f"""
                            SELECT COALESCE(fornecedor, '—') AS fornecedor, COUNT(*) AS itens, SUM(quantidade) AS qtd
                              FROM estoque_unificado
                              {where_sql}
                             GROUP BY COALESCE(fornecedor, '—')
                             ORDER BY itens DESC, fornecedor ASC
                             LIMIT 50
                        """
                        cur.execute(sql, tuple(params))
                        rows = cur.fetchall()
                        if not rows:
                            return "ℹ️ Nenhum fornecedor encontrado no banco para esse filtro."
                        linhas = ["🏦 **Fornecedores encontrados no banco**:"]
                        for forn, itens, qtd in rows:
                            linhas.append(f"- {forn}: {int(itens or 0)} itens, qtd {float(qtd or 0):.2f}")
                        return "\n".join(linhas)

                    if p["is_cores"]:
                        sql = cte + f"""
                            SELECT COALESCE(cor, '—') AS cor, COUNT(*) AS itens, SUM(quantidade) AS qtd
                              FROM estoque_unificado
                              {where_sql}
                             GROUP BY COALESCE(cor, '—')
                             ORDER BY itens DESC, cor ASC
                             LIMIT 50
                        """
                        cur.execute(sql, tuple(params))
                        rows = cur.fetchall()
                        if not rows:
                            return "ℹ️ Nenhuma cor encontrada no banco para esse filtro."
                        linhas = ["🎨 **Cores encontradas no banco**:"]
                        for cor, itens, qtd in rows:
                            linhas.append(f"- {cor}: {int(itens or 0)} itens, qtd {float(qtd or 0):.2f}")
                        return "\n".join(linhas)

                    if p["is_valor"]:
                        sql = cte + f"""
                            SELECT COUNT(*) AS itens,
                                   SUM(quantidade) AS qtd_total,
                                   SUM(
                                       quantidade * CASE
                                           WHEN LOWER(COALESCE(categoria,'')) LIKE '%%tecid%%' THEN 15
                                           WHEN LOWER(COALESCE(categoria,'')) LIKE '%%aviam%%' THEN 2.5
                                           WHEN LOWER(COALESCE(categoria,'')) LIKE '%%escrit%%' THEN 6
                                           WHEN LOWER(COALESCE(categoria,'')) LIKE '%%limp%%' THEN 5
                                           ELSE 7
                                       END
                                   ) AS valor_estimado
                              FROM estoque_unificado
                              {where_sql}
                        """
                        cur.execute(sql, tuple(params))
                        itens, qtd_total, valor = cur.fetchone()
                        return (
                            "🏦 **Consulta em tempo real no banco**\n"
                            f"• Itens considerados: **{int(itens or 0)}**\n"
                            f"• Quantidade total: **{float(qtd_total or 0):,.2f}**\n"
                            f"• Valor estimado: **R$ {float(valor or 0):,.2f}**"
                        )

                    if p["is_contagem"] and not (p["top_n"] or p["bottom_n"]):
                        sql = cte + f"""
                            SELECT COUNT(*) AS linhas,
                                   COUNT(DISTINCT codigo) AS codigos_distintos,
                                   SUM(quantidade) AS qtd_total
                              FROM estoque_unificado
                              {where_sql}
                        """
                        cur.execute(sql, tuple(params))
                        linhas, distintos, qtd = cur.fetchone()
                        return (
                            "📊 **Contagem direta no banco**\n"
                            f"• Linhas: **{int(linhas or 0)}**\n"
                            f"• Códigos distintos: **{int(distintos or 0)}**\n"
                            f"• Quantidade total: **{float(qtd or 0):,.2f}**"
                        )

                    if p["top_n"] or p["bottom_n"] or p["is_busca"] or p["codigo"] or p["is_critico"] or p["limiar"] is not None or p["termos_livres"]:
                        limit = max(1, min(100, p["top_n"] or p["bottom_n"] or 20))
                        if p["bottom_n"] or p["is_abaixo"] or p["is_critico"]:
                            order = "quantidade ASC, descricao ASC"
                            titulo = f"⬇️ **Menores quantidades (top {limit})**"
                        else:
                            order = "quantidade DESC, descricao ASC"
                            titulo = f"⬆️ **Maiores quantidades (top {limit})**"

                        if p["is_busca"] and not p["codigo"]:
                            termo = p["raw"].replace("buscar", "").replace("procurar", "").replace("encontrar", "").strip()
                            if termo:
                                where_extra = "LOWER(COALESCE(descricao,'')) LIKE %s OR LOWER(CAST(codigo AS text)) LIKE %s"
                                filtros.append(f"({where_extra})")
                                params.extend([f"%{termo}%", f"%{termo}%"])
                                where_sql = " WHERE " + " AND ".join(filtros)

                        sql = cte + f"""
                            SELECT codigo, descricao, categoria, quantidade, COALESCE(localizacao,'—') AS localizacao,
                                   COALESCE(cor,'—') AS cor, COALESCE(fornecedor,'—') AS fornecedor, origem
                              FROM estoque_unificado
                              {where_sql}
                             ORDER BY {order}
                             LIMIT {limit}
                        """
                        cur.execute(sql, tuple(params))
                        rows = cur.fetchall()
                        if not rows:
                            return "ℹ️ Nenhum resultado encontrado no banco para esse filtro."

                        linhas = ["🏦 **Consulta em tempo real no banco**", titulo]
                        for r in rows[:limit]:
                            linhas.append(
                                f"- `{r[0]}` • {r[1]} • qtd **{float(r[3] or 0):.2f}** • "
                                f"cat {r[2] or '—'} • local {r[4]} • cor {r[5]} • forn {r[6]} • tabela {r[7]}"
                            )
                        return "\n".join(linhas)

                    sql = cte + f"""
                        SELECT COUNT(*) AS linhas, COUNT(DISTINCT codigo) AS codigos, SUM(quantidade) AS qtd
                          FROM estoque_unificado
                          {where_sql}
                    """
                    cur.execute(sql, tuple(params))
                    linhas, codigos, qtd = cur.fetchone()
                    return (
                        "🏦 **Verificação no banco concluída**\n"
                        f"• Linhas: **{int(linhas or 0)}**\n"
                        f"• Códigos distintos: **{int(codigos or 0)}**\n"
                        f"• Quantidade total: **{float(qtd or 0):,.2f}**"
                    )

        except Exception as e:
            return f"⚠️ Não consegui consultar o banco agora: {e}"

        return None

    def _refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for item in self.resultados:
            self.tree.insert("", "end", values=item)

    def _recalc_stats(self):
        total_items = len(self.resultados)
        low_stock = sum(1 for i in self.resultados if float(i[3] or 0) < 10)
        categories = len(set(i[2] for i in self.resultados if i[2]))
        total_value = 0.0
        for i in self.resultados:
            cat = (i[2] or "").lower()
            if "tecido" in cat:
                total_value += float(i[3] or 0) * 15.0
            elif "aviam" in cat:
                total_value += float(i[3] or 0) * 2.5
            elif "escrit" in cat:
                total_value += float(i[3] or 0) * 6.0
            elif "limp" in cat:
                total_value += float(i[3] or 0) * 5.0
            else:
                total_value += float(i[3] or 0) * 7.0
        self.stats_data.update({
            "total_items": total_items,
            "low_stock": low_stock,
            "categories": categories,
            "total_value": total_value,
        })

        try:
            for child in self.cards_frame.winfo_children():
                child.destroy()
            self._metric_card(self.cards_frame, "🧾 Total Itens", total_items).grid(row=0, column=0, sticky="ew")
            self._metric_card(self.cards_frame, "⚠️ Itens Críticos", low_stock).grid(row=0, column=1, sticky="ew")
            self._metric_card(self.cards_frame, "📂 Categorias", categories).grid(row=0, column=2, sticky="ew")
            self._metric_card(self.cards_frame, "🕒 Atualizado", datetime.now().strftime("%d/%m/%Y %H:%M")).grid(row=0,
                                                                                                                column=3,
                                                                                                                sticky="ew")
        except Exception:
            pass

    def apply_filters(self):
        term = (self.search_entry.get() or "").strip().lower()
        cat = (self.category_var.get() or "Todas").lower()

        def match(row):
            in_cat = (cat == "todas") or ((row[2] or "").lower() == cat)
            if not term:
                return in_cat
            return in_cat and (term in (str(row[0]).lower()) or term in (str(row[1]).lower()))

        filtered = [r for r in self.resultados if match(r)]
        for i in self.tree.get_children():
            self.tree.delete(i)
        for item in filtered:
            self.tree.insert("", "end", values=item)

    def export_csv(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")], title="Salvar CSV"
        )
        if not filename:
            return
        try:
            cols = ["ID", "Descrição", "Categoria", "Quantidade", "Status", "Localização", "Última Atualização"]
            with open(filename, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(cols)
                for item in self.tree.get_children():
                    w.writerow(self.tree.item(item, "values"))
            messagebox.showinfo("Exportar CSV", "Arquivo salvo com sucesso.")
        except Exception as e:
            messagebox.showerror("Exportar CSV", f"Falha ao salvar: {e}")

    def export_pdf(self):
        if not FPDF_AVAILABLE:
            messagebox.showwarning("PDF", "Biblioteca FPDF não encontrada. Instale: pip install fpdf2")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], title="Salvar PDF"
        )
        if not filename:
            return
        try:
            pdf = FPDF(orientation="L", unit="mm", format="A4")
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Relatório de Estoque", ln=True, align="C")
            pdf.set_font("Arial", "", 9)

            cols = ["ID", "Descrição", "Categoria", "Quantidade", "Status", "Localização", "Última Atualização"]
            col_widths = [25, 90, 35, 30, 25, 45, 35]

            for c, w in zip(cols, col_widths):
                pdf.cell(w, 8, c, border=1, align="C")
            pdf.ln()

            for iid in self.tree.get_children():
                vals = list(self.tree.item(iid, "values"))
                if len(vals) >= 4:
                    try:
                        vals[3] = f"{float(vals[3]):.2f}"
                    except Exception:
                        pass
                for v, w in zip(vals, col_widths):
                    pdf.cell(w, 6, str(v)[:40], border=1)
                pdf.ln()

            pdf.output(filename)
            messagebox.showinfo("PDF", "PDF gerado com sucesso.")
        except Exception as e:
            messagebox.showerror("PDF", f"Falha ao gerar PDF: {e}")

    def export_excel(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".xls", filetypes=[("Planilha Excel (CSV)", "*.xls"), ("CSV", "*.csv")],
            title="Salvar Excel"
        )
        if not filename:
            return
        try:
            cols = ["ID", "Descrição", "Categoria", "Quantidade", "Status", "Localização", "Última Atualização"]
            with open(filename, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(cols)
                for item in self.tree.get_children():
                    w.writerow(self.tree.item(item, "values"))
            messagebox.showinfo("Exportar Excel", "Planilha salva com sucesso.")
        except Exception as e:
            messagebox.showerror("Exportar Excel", f"Falha ao salvar: {e}")

    # --------- SUGESTÕES (modo leve com carregamento sob demanda) ----------
    def _open_suggestions_window(self):
        """Janela leve: carrega só a categoria escolhida. Evita travamentos."""
        try:
            if not hasattr(self, "assistente") or self.assistente is None:
                self.assistente = EstoqueIAAvancada(self.resultados)
        except Exception:
            pass

        try:
            self.sug_catalog = self._build_suggestions_catalog()
        except Exception as e:
            messagebox.showerror("Sugestões", f"Erro ao montar catálogo: {e}")
            return

        win = ctk.CTkToplevel(self)
        self._sug_win = win
        win.title("Sugestões de Perguntas (leve)")
        win.geometry("860x560")
        win.grab_set()

        # Atualizar cores para a janela de sugestões
        self.obter_cores_por_tema()

        # Top info + filter - MESMO PADRÃO DO CADASTRO_DE_CORTE
        top = ctk.CTkFrame(win, fg_color=self.cor_fundo)
        top.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(top, text="Duplo clique na pergunta para enviar. Use o filtro para reduzir a lista.",
                     text_color=self.cor_texto).pack(anchor="w")
        filt_row = ctk.CTkFrame(win, fg_color=self.cor_fundo)
        filt_row.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(filt_row, text="Filtro:", text_color=self.cor_texto, width=50).pack(side="left")
        self._sug_filter_var = tk.StringVar()
        self._sug_filter = ctk.CTkEntry(filt_row, textvariable=self._sug_filter_var,
                                        placeholder_text="Filtrar perguntas...",
                                        fg_color=self.cor_secundaria, border_color=self.cor_borda,
                                        text_color=self.cor_texto_entry, placeholder_text_color=self.cor_placeholder)
        self._sug_filter.pack(side="left", fill="x", expand=True)
        self._sug_filter_var.trace_add("write", lambda *a: self._reload_questions())

        # Split panes: left categories, right questions - MESMO PADRÃO DO CADASTRO_DE_CORTE
        body = ctk.CTkFrame(win, fg_color=self.cor_fundo)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=0)

        # Categories list (Listbox é mais rápido que Treeview para coluna única)
        left = ctk.CTkFrame(body, fg_color=self.cor_fundo)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk_label_cat = ctk.CTkLabel(left, text="Categorias", text_color=self.cor_texto)
        tk_label_cat.pack(anchor="w")
        self._sug_cat_list = tk.Listbox(left, activestyle="dotbox", bg=self.cor_secundaria, fg=self.cor_texto,
                                        selectbackground=self.cor_selecao)
        self._sug_cat_list.pack(fill="both", expand=True)
        self._sug_cat_list.bind("<<ListboxSelect>>", lambda e: self._on_select_category())

        # Questions list - MESMO PADRÃO DO CADASTRO_DE_CORTE
        right = ctk.CTkFrame(body, fg_color=self.cor_fundo)
        right.grid(row=0, column=1, sticky="nsew")
        tk_label_q = ctk.CTkLabel(right, text="Perguntas", text_color=self.cor_texto)
        tk_label_q.pack(anchor="w")
        self._sug_q_list = tk.Listbox(right, activestyle="dotbox", bg=self.cor_secundaria, fg=self.cor_texto,
                                      selectbackground=self.cor_selecao)
        self._sug_q_list.pack(fill="both", expand=True)
        self._sug_q_list.bind("<Double-1>", lambda e: self._send_selected_question())

        # Pagination - MESMO PADRÃO DO CADASTRO_DE_CORTE
        pager = ctk.CTkFrame(body, fg_color=self.cor_fundo)
        pager.grid(row=1, column=1, sticky="ew")
        self._sug_page = 0
        self._sug_page_size = 150
        ctk.CTkButton(pager, text="◀ Anterior", width=100,
                      command=lambda: self._change_page(-1),
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)
        self._sug_page_label = ctk.CTkLabel(pager, text="Página 1/1", text_color=self.cor_texto)
        self._sug_page_label.pack(side="left", padx=8)
        ctk.CTkButton(pager, text="Próxima ▶", width=100,
                      command=lambda: self._change_page(+1),
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)

        # Load categories
        self._sug_categories = list(self.sug_catalog.keys())
        self._sug_cat_list.delete(0, "end")
        for cat in self._sug_categories:
            try:
                self._sug_cat_list.insert("end", f"{cat} ({len(self.sug_catalog.get(cat, []))})")
            except Exception:
                self._sug_cat_list.insert("end", cat)

        # Select first category by default
        if self._sug_categories:
            self._sug_cat_list.select_set(0)
            self._on_select_category()

    # -------------- NOVO: construtor do catálogo de sugestões --------------
    def _build_suggestions_catalog(self) -> Dict[str, List[str]]:
        """
        Gera 200+ sugestões por categoria (leve, com combinações programáticas).
        As categorias de sugestões são grupos de intenções (não as categorias de estoque).
        """
        # Dinâmicos do seu banco
        cats = sorted({(str(r[2]) or "—") for r in self.resultados if r and len(r) > 2})
        locs = sorted({(str(r[5]) or "—") for r in self.resultados if r and len(r) > 5})
        cats = [c for c in cats if c and c != "—"][:30] or ["Tecidos", "Aviamentos", "Outros"]
        locs = [l for l in locs if l and l != "—"][:30] or ["Depósito", "Prateleira A", "Armário 1"]

        Ns = [5, 10, 12, 15, 20, 25, 30, 40, 50, 75, 100]
        DAYS = [7, 10, 15, 20, 30, 45, 60, 90, 120, 180]
        LIM = [5, 8, 10, 12, 15, 20, 30, 50]

        def expand(templates: List[str], limit: int = 260) -> List[str]:
            out = []
            for t in templates:
                if "{N}" in t:
                    for n in Ns:
                        out.append(t.replace("{N}", str(n)))
                elif "{D}" in t:
                    for d in DAYS:
                        out.append(t.replace("{D}", str(d)))
                elif "{L}" in t:
                    for l in LIM:
                        out.append(t.replace("{L}", str(l)))
                elif "{cat}" in t:
                    for c in cats:
                        out.append(t.replace("{cat}", c))
                elif "{loc}" in t:
                    for l in locs:
                        out.append(t.replace("{loc}", l))
                else:
                    out.append(t)
            # de-dup + cap
            out = list(dict.fromkeys(out))
            return out[:limit]

        def at_least(lst: List[str], n: int, filler_prefix: str) -> List[str]:
            i = 1
            while len(lst) < n:
                lst.append(f"{filler_prefix} #{i}")
                i += 1
            return lst

        # 1) Geral
        geral_tpl = [
            "Itens críticos", "Itens zerados", "Itens negativos", "Excesso de estoque",
            "Valor do estoque", "Valor por categoria", "Valor por local",
            "Top {N} por quantidade", "Bottom {N} por quantidade", "ABC (Pareto)",
            "Itens não movimentados há {D} dias", "Quais categorias temos?", "Quais locais temos?",
            "Produtos distintos", "Agrupar por categoria", "Agrupar por local",
            "Exportar CSV", "Gerar PDF", "Exportar Excel",
            "Ponto de pedido", "Sugestões de compra", "Auditar dados de estoque",
            "Buscar: zíper", "Buscar: linha", "Buscar: agulha", "Comparar tecidos vs aviamentos",
            "Itens abaixo de {L} unidades", "Itens acima de {L} unidades"
        ]
        geral = expand(geral_tpl)
        geral = at_least(geral, 210, "Pergunta geral")

        # 2) Inventário por Categoria (dinâmico)
        cat_tpl = [
            "Valor em {cat}", "Itens críticos em {cat}", "Itens zerados em {cat}",
            "Itens negativos em {cat}", "Top {N} em {cat}", "Bottom {N} em {cat}",
            "ABC por valor em {cat}", "Parados há {D} dias em {cat}", "Conferir duplicados em {cat}",
            "Exportar {cat} para CSV", "Gerar PDF de {cat}",
            "Itens abaixo de {L} em {cat}", "Itens acima de {L} em {cat}"
        ]
        por_categoria = expand(cat_tpl)
        por_categoria = at_least(por_categoria, 210, "Pergunta por categoria")

        # 3) Inventário por Local (dinâmico)
        loc_tpl = [
            "Quais itens no local {loc}?", "Valor no local {loc}", "Top {N} no local {loc}",
            "Bottom {N} no local {loc}", "Críticos no local {loc}", "Zerados no local {loc}",
            "Negativos no local {loc}", "Parados há {D} dias no local {loc}",
            "Exportar itens do local {loc}", "Gerar PDF do local {loc}",
            "Itens abaixo de {L} no local {loc}", "Itens acima de {L} no local {loc}"
        ]
        por_local = expand(loc_tpl)
        por_local = at_least(por_local, 210, "Pergunta por local")

        # 4) Estados (críticos/zerados/negativos/excesso)
        estados_tpl = [
            "Listar itens críticos", "Listar itens zerados", "Listar itens negativos",
            "Detectar excesso por categoria", "Detectar excesso por local",
            "Críticos por {cat}", "Zerados por {cat}", "Negativos por {cat}",
            "Críticos por {loc}", "Zerados por {loc}", "Negativos por {loc}",
            "Itens abaixo de {L}", "Itens acima de {L}"
        ]
        estados = expand(estados_tpl)
        estados = at_least(estados, 210, "Pergunta de estado")

        # 5) Financeiro
        financeiro_tpl = [
            "Valor do estoque", "Valor por categoria", "Valor por local",
            "Quanto vale a categoria {cat}?", "Qual o valor no local {loc}?",
            "Top {N} em valor (categoria)", "Top {N} em valor (local)",
            "Curva ABC por valor", "Classe A detalhar", "Classe B detalhar", "Classe C detalhar",
            "Exportar valores por categoria", "Exportar valores por local"
        ]
        financeiro = expand(financeiro_tpl)
        financeiro = at_least(financeiro, 210, "Pergunta financeira")

        # 6) Rankings
        rank_tpl = [
            "Top {N} por quantidade", "Bottom {N} por quantidade",
            "Top {N} em {cat}", "Bottom {N} em {cat}",
            "Top {N} no local {loc}", "Bottom {N} no local {loc}"
        ]
        rankings = expand(rank_tpl)
        rankings = at_least(rankings, 210, "Pergunta de ranking")

        # 7) Temporalidade
        temporal_tpl = [
            "Itens não movimentados há {D} dias", "Parados há {D} dias em {cat}",
            "Parados há {D} dias no local {loc}", "Entradas recentes (últimos {D} dias)",
            "Comparar últimos {D} dias vs {D} dias anteriores"
        ]
        temporal = expand(temporal_tpl)
        temporal = at_least(temporal, 210, "Pergunta temporal")

        # 8) Busca & Itens
        busca_tpl = [
            "Buscar: {term}", "Código: {code}", "Detalhes do item {code}",
            "Procurar por descrição contendo {term}", "Abrir por código {code}",
            "Comparar {cat} vs {cat}", "Comparar {loc} vs {loc}"
        ]
        # gerar termos/códigos fakes leves
        terms = ["zíper", "linha", "agulha", "botão", "elástico", "jeans", "sarja", "tricoline", "malha"]
        codes = [f"{i:03d}-{j:02d}" for i in range(1, 60) for j in range(1, 5)]
        busca = []
        for t in busca_tpl:
            if "{term}" in t:
                for x in terms:
                    busca.append(t.replace("{term}", x))
            elif "{code}" in t:
                for x in codes[:240]:
                    busca.append(t.replace("{code}", x))
            elif "{cat}" in t:
                # pares de categorias distintos
                for i in range(min(len(cats), 12)):
                    for j in range(i + 1, min(len(cats), 12)):
                        busca.append(t.replace("{cat}", cats[i], 1).replace("{cat}", cats[j], 1))
            elif "{loc}" in t:
                for i in range(min(len(locs), 12)):
                    for j in range(i + 1, min(len(locs), 12)):
                        busca.append(t.replace("{loc}", locs[i], 1).replace("{loc}", locs[j], 1))
            else:
                busca.append(t)
        busca = list(dict.fromkeys(busca))[:260]
        busca = at_least(busca, 210, "Pergunta de busca")

        # 9) Exportação
        export_tpl = [
            "Exportar CSV", "Exportar Excel", "Gerar PDF",
            "Exportar {cat} em CSV", "Exportar {cat} em Excel", "Gerar PDF da categoria {cat}",
            "Exportar local {loc} em CSV", "Exportar local {loc} em Excel", "Gerar PDF do local {loc}",
            "Exportar Top {N}", "Exportar Bottom {N}", "Exportar críticos", "Exportar zerados", "Exportar negativos"
        ]
        exportacao = expand(export_tpl)
        exportacao = at_least(exportacao, 210, "Pergunta de exportação")

        # 10) Ajustes & Auditoria
        ajustes_tpl = [
            "Auditar dados de estoque", "Procurar duplicados", "Procurar descrições vazias",
            "Procurar quantidades absurdas", "Sincronizar categorias com rotas",
            "Logs por item", "Logs por categoria {cat}", "Logs por local {loc}",
            "Itens abaixo do mínimo {L}", "Itens acima do máximo {L}"
        ]
        ajustes = expand(ajustes_tpl)
        ajustes = at_least(ajustes, 210, "Pergunta de ajuste")

        catalog = {
            "Geral": geral,
            "Por Categoria (dinâmico)": por_categoria,
            "Por Local (dinâmico)": por_local,
            "Estados": estados,
            "Financeiro": financeiro,
            "Rankings": rankings,
            "Temporalidade": temporal,
            "Busca & Itens": busca,
            "Exportação": exportacao,
            "Ajustes & Auditoria": ajustes,
        }
        return catalog

    def _on_select_category(self):
        idxs = self._sug_cat_list.curselection()
        if not idxs:
            return
        raw = self._sug_cat_list.get(idxs[0])
        cat = raw.split(" (")[0]
        self._sug_current_cat = cat
        self._sug_page = 0
        self._reload_questions()

    def _reload_questions(self):
        cat = getattr(self, "_sug_current_cat", None)
        if not cat:
            return
        filter_term = (self._sug_filter_var.get() or "").strip().lower()
        all_qs = self.sug_catalog.get(cat, [])
        if filter_term:
            qs = [q for q in all_qs if filter_term in q.lower()]
        else:
            qs = list(all_qs)

        # pagination
        total = max(1, len(qs))
        pages = max(1, (total + self._sug_page_size - 1) // self._sug_page_size)
        self._sug_page = max(0, min(self._sug_page, pages - 1))
        start = self._sug_page * self._sug_page_size
        end = start + self._sug_page_size
        view = qs[start:end]

        # fill listbox
        self._sug_q_list.delete(0, "end")
        for q in view:
            self._sug_q_list.insert("end", q)

        self._sug_page_label.configure(text=f"Página {self._sug_page + 1}/{pages}  •  {len(qs)} itens")

    def _change_page(self, delta):
        self._sug_page = max(0, self._sug_page + delta)
        self._reload_questions()

    def _send_selected_question(self):
        sel = self._sug_q_list.curselection()
        if not sel:
            return
        text = self._sug_q_list.get(sel[0])
        self.ai_input.delete(0, "end")
        self.ai_input.insert(0, text)
        self.process_ai_query()
        try:
            self._sug_win.destroy()
        except Exception:
            pass

    # --------- CHAT / IA ----------
    def process_ai_query(self, event=None):
        q = self.ai_input.get().strip()
        if not q:
            return
        # paginação de ajuda (comando "ajuda página X")
        if q.lower().startswith("ajuda página"):
            try:
                page = int(re.findall(r'\d+', q)[0])
            except Exception:
                page = 1
            self._post_user(q)
            self._post_bot(self.assistente._help_text(page=page))
            self.ai_input.delete(0, "end")
            return

        self._last_user_prompt = q
        self.ai_input.delete(0, "end")
        self._post_user(q)
        self._enqueue_ai(q)

    def _enqueue_ai(self, text, is_regen=False):
        self._ai_queue.put((text, is_regen))
        if not self._ai_worker_running:
            self._ai_worker_running = True
            threading.Thread(target=self._ai_worker_loop, daemon=True).start()

    def _ai_worker_loop(self):
        while self._ai_worker_running:
            try:
                text, is_regen = self._ai_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self._ai_metricas["mensagens"] += 1
                if self.assistente is None:
                    self.assistente = EstoqueIAAvancada(self.resultados)

                acao_direta = self._try_handle_direct_ai_action(text)
                if acao_direta:
                    self._post_bot(acao_direta)
                    self.assistente._remember("assistant", acao_direta)
                    self._ai_metricas["acoes_diretas"] += 1
                    continue

                resposta_local = self.assistente.responder(text)
                intent, conf = self.assistente._intent_score(text)
                self._ajustar_perfil_resposta(text)
                usar_banco = self._should_use_db_answer(text, intent, conf)
                resposta_banco = self._ai_query_database(text) if usar_banco else None
                main = self._merge_local_and_db_response(resposta_local, resposta_banco, text)
                variations = [] if resposta_banco else self._short_variations(main)
                out = main
                if variations:
                    out += "\n\n" + " ".join(f"_{v}_" for v in variations)
                self._post_bot(out)
                self.assistente._remember("assistant", main)
            except Exception as e:
                self._post_bot(f"⚠️ Erro ao gerar resposta: {e}", slow=False)
            finally:
                self._ai_queue.task_done()

    def _try_handle_direct_ai_action(self, text: str) -> Optional[str]:
        q = (text or "").strip().lower()
        if not q:
            return None

        if q in {"sim", "ok", "confirmo", "pode", "pode sim", "isso"}:
            if self._ai_pending_action == "pdf":
                self.after(0, self.export_pdf)
                self._ai_pending_action = None
                return "Confirmação recebida. Abri a exportação de PDF."
            if self._ai_pending_action == "csv":
                self.after(0, self.export_csv)
                self._ai_pending_action = None
                return "Confirmação recebida. Abri a exportação de CSV."
            if self._ai_pending_action == "excel":
                self.after(0, self.export_excel)
                self._ai_pending_action = None
                return "Confirmação recebida. Abri a exportação de Excel."
            if self._ai_pending_action == "criticos":
                self._ai_pending_action = None
                return self.assistente.responder("quais itens estão críticos")

        if q in {"nao", "não", "cancelar", "pare"}:
            self._ai_pending_action = None
            return "Tudo bem, ação cancelada. Me diga o próximo objetivo."

        if any(k in q for k in ("gerar pdf", "gere pdf", "exportar pdf", "salvar pdf", "relatorio em pdf", "relatório em pdf")):
            self.after(0, self.export_pdf)
            return "Perfeito. Abri a exportação de PDF para você."

        if any(k in q for k in ("exportar csv", "gerar csv", "salvar csv")):
            self.after(0, self.export_csv)
            return "Perfeito. Abri a exportação de CSV para você."

        if any(k in q for k in ("exportar excel", "gerar excel", "salvar excel", "planilha")):
            self.after(0, self.export_excel)
            return "Perfeito. Abri a exportação de Excel para você."

        if any(k in q for k in ("apenas os criticos", "apenas os críticos", "somente criticos", "somente críticos")):
            return self.assistente.responder("quais itens estão críticos")

        if any(k in q for k in ("gerar relatorio completo", "gerar relatório completo", "inventario completo", "inventário completo")):
            self._ai_pending_action = "pdf"
            return (
                "Posso gerar o relatório completo agora.\n"
                "Se quiser continuar, responda: SIM."
            )

        if "diagnostico ia" in q or "diagnóstico ia" in q:
            return (
                "Diagnóstico rápido da IA:\n"
                f"- mensagens processadas: {self._ai_metricas['mensagens']}\n"
                f"- ações diretas executadas: {self._ai_metricas['acoes_diretas']}\n"
                f"- fallbacks de banco: {self._ai_metricas['fallback_db']}\n"
                f"- perfil atual de resposta: {self._ai_perfil_resposta}"
            )

        return None

    def _short_variations(self, base_text):
        # Evita ruído e loops de confirmação no chat.
        return []

    def _ajustar_perfil_resposta(self, text: str) -> None:
        q = (text or "").lower()
        if any(k in q for k in ("detalhado", "detalhe", "completo", "analitico", "analítico", "explique")):
            self._ai_perfil_resposta = "detalhado"
        elif any(k in q for k in ("rápido", "rapido", "resumo", "curto")):
            self._ai_perfil_resposta = "objetivo"
        else:
            self._ai_perfil_resposta = "operacional"

    def _should_use_db_answer(self, text: str, intent: Optional[str], conf: float) -> bool:
        q = (text or "").strip().lower()
        if not q:
            return False
        gatilhos_explicitos_banco = ("no banco", "direto no banco", "consulta sql", "query", "banco de dados")
        if any(g in q for g in gatilhos_explicitos_banco):
            return True
        if intent in {"saudacao", "ajuda", "contexto"} and conf >= 0.15:
            return False
        intents_locais_fortes = {
            "listar_grupo", "contar_grupo", "resumo_grupo", "resumo_geral", "listar_todos_itens",
            "itens_por_setor_detalhado", "itens_criticos", "contar_itens_distintos", "contar_codigos"
        }
        if intent in intents_locais_fortes and conf >= 0.70:
            return False
        termos_db = (
            "estoque", "item", "itens", "quantidade", "categoria", "local", "cor", "fornecedor",
            "prestador", "codigo", "código", "top", "bottom", "critico", "crítico", "valor",
            "abaixo", "acima", "quanto", "quais", "buscar", "procurar"
        )
        return any(t in q for t in termos_db)

    def _strip_markdown_tokens(self, text: str) -> str:
        if not text:
            return ""
        cleaned = text.replace("**", "").replace("`", "")
        cleaned = cleaned.replace("🏦 ", "").replace("📊 ", "").replace("ℹ️ ", "")
        return cleaned.strip()

    def _merge_local_and_db_response(self, resposta_local: str, resposta_banco: Optional[str], pergunta: str) -> str:
        local_txt = self._strip_markdown_tokens(resposta_local)
        if not resposta_banco:
            return local_txt

        banco_txt = self._strip_markdown_tokens(resposta_banco)
        banco_l = banco_txt.lower()
        estado = "ok"
        if ("linhas: 0" in banco_l or "linhas:0" in banco_l) and local_txt and "não encontrei" not in local_txt.lower():
            return local_txt

        if "nenhum resultado encontrado no banco" in banco_l or "não consegui consultar o banco" in banco_l:
            estado = "no_match"
            self._ai_metricas["fallback_db"] += 1
            return (
                f"{local_txt}\n\n"
                "No banco não encontrei um resultado exato com esse filtro agora. "
                "Se quiser, eu tento por código, categoria, cor, local ou fornecedor."
            )

        if "verificação no banco concluída" in banco_l:
            estado = "disambiguation"
            return (
                "Entendi 👍\n"
                f"{banco_txt}\n\n"
                "Se você me disser o que deseja (ex.: categoria, cor, fornecedor ou código), "
                "eu te devolvo uma resposta bem mais específica."
            )

        resposta = (
            "Perfeito, consultei no banco em tempo real:\n"
            f"{banco_txt}"
        )
        if self._ai_perfil_resposta == "detalhado" and estado == "ok":
            resposta += "\n\nPróximo passo sugerido: peça 'análise de risco' ou 'curva abc' para aprofundar."
        return resposta


# ---------- Execução Standalone ----------


# --- Traduções completas aplicadas antes do __main__ ---
AdvancedStockReport_TRANSLATIONS = {
    "pt_BR": {
        "window_title": "Relatórios - Sistema Opera",
        "title": "Relatórios",
        "subtitle": "Controle de Estoque",
        "refresh": "Atualizar Dados",
        "report_tab": "📋 Relatório",
        "analysis_tab": "📊 Análise",
        "assistant_tab": "🤖 Assistente",
        "search": "🔎 Buscar por código ou descrição...",
        "apply_filters": "Aplicar Filtros",
        "clear_filters": "Limpar Filtros",
        "category_all": "Todas",
        "category_fabrics": "Tecidos",
        "category_trims": "Aviamentos",
        "category_inputs": "Insumos",
        "category_office": "Escritorio",
        "category_cleaning": "Limpeza",
        "category_other": "Outros",
        "export_csv": "📄 Exportar CSV",
        "generate_pdf": "🖨️ Gerar PDF",
        "export_excel": "📊 Exportar Excel",
        "print": "🖨️ Imprimir",
        "header": ["ID", "Descrição", "Categoria", "Quantidade", "Status", "Localização", "Última Atualização"],
        "total_items": "🧾 Total Itens",
        "critical_items": "⚠️ Itens Críticos",
        "categories": "📂 Categorias",
        "updated": "🕒 Atualizado",
        "estimated_value": "💰 Valor Estimado",
        "by_category": "Quantidade por Categoria",
        "critical_by_category": "Itens Críticos por Categoria",
        "assistant_title": "🤖 Assistente de Estoque Inteligente",
        "assistant_ph": "Converse aqui... (Enter para enviar)",
        "assistant_greeting": "👋 Olá! Pergunte sobre críticos, valor, tecidos, localização ou digite o código do item.",
        "typing_indicator": "digitando...",
        "send": "Enviar",
        "quick_1": "Itens críticos",
        "quick_2": "Valor do estoque",
        "quick_3": "Tecidos (metragem)",
        "quick_4": "Sugestões de compra",
        "quick_5": "Itens não movimentados há 30 dias",
        "regen": "🔁 Regenerar",
        "export_chat": "💾 Exportar conversa",
        "suggestions": "💡 Sugestões/Perguntas",
        "connected": "🟢 Conectado | {data}",
        "add_item_title": "Adicionar Item do Estoque",
        "add_item_search_label": "Buscar Item (código/descrição/categoria):",
        "add_item_search_button": "Buscar",
        "add_item_confirm": "Confirmar",
        "add_item_cancel": "Cancelar",
        "suggestions_title": "Sugestões de Perguntas",
        "suggestions_info": "Duplo clique na pergunta para enviar. Use o filtro para reduzir a lista.",
        "suggestions_filter_label": "Filtro:",
        "suggestions_filter_placeholder": "Filtrar perguntas...",
        "suggestions_categories": "Categorias",
        "suggestions_questions": "Perguntas",
        "suggestions_prev": "◀ Anterior",
        "suggestions_next": "Próxima ▶",
        "suggestions_page_info": "Página {page} de {total} | {count} perguntas",
        "title_info": "Informação",
        "title_warning": "Aviso",
        "title_error": "Erro",
        "title_confirm": "Confirmar",
        "msg_no_message_regen": "Ainda não há mensagem para regenerar.",
    },
    "en_US": {
        "window_title": "Reports - Opera System",
        "title": "Reports",
        "subtitle": "Stock Control",
        "refresh": "Refresh Data",
        "report_tab": "📋 Report",
        "analysis_tab": "📊 Analysis",
        "assistant_tab": "🤖 Assistant",
        "search": "🔎 Search by code or description...",
        "apply_filters": "Apply Filters",
        "clear_filters": "Clear Filters",
        "category_all": "All",
        "category_fabrics": "Fabrics",
        "category_trims": "Trims",
        "category_inputs": "Inputs",
        "category_office": "Office",
        "category_cleaning": "Cleaning",
        "category_other": "Others",
        "export_csv": "📄 Export CSV",
        "generate_pdf": "🖨️ Generate PDF",
        "export_excel": "📊 Export Excel",
        "print": "🖨️ Print",
        "header": ["ID", "Description", "Category", "Quantity", "Status", "Location", "Last Update"],
        "total_items": "🧾 Total Items",
        "critical_items": "⚠️ Critical Items",
        "categories": "📂 Categories",
        "updated": "🕒 Updated",
        "estimated_value": "💰 Estimated Value",
        "by_category": "Quantity by Category",
        "critical_by_category": "Critical Items by Category",
        "assistant_title": "🤖 Smart Stock Assistant",
        "assistant_ph": "Chat here... (Press Enter to send)",
        "assistant_greeting": "👋 Hello! Ask about critical items, stock value, fabrics, locations, or type an item code.",
        "typing_indicator": "typing...",
        "send": "Send",
        "quick_1": "Critical items",
        "quick_2": "Stock value",
        "quick_3": "Fabrics (meterage)",
        "quick_4": "Purchase suggestions",
        "quick_5": "Items not moved for 30 days",
        "regen": "🔁 Regenerate",
        "export_chat": "💾 Export chat",
        "suggestions": "💡 Suggestions/Questions",
        "connected": "🟢 Connected | {data}",
        "add_item_title": "Add Stock Item",
        "add_item_search_label": "Search Item (code/description/category):",
        "add_item_search_button": "Search",
        "add_item_confirm": "Confirm",
        "add_item_cancel": "Cancel",
        "suggestions_title": "Question Suggestions",
        "suggestions_info": "Double-click a question to send it. Use the filter to reduce the list.",
        "suggestions_filter_label": "Filter:",
        "suggestions_filter_placeholder": "Filter questions...",
        "suggestions_categories": "Categories",
        "suggestions_questions": "Questions",
        "suggestions_prev": "◀ Previous",
        "suggestions_next": "Next ▶",
        "suggestions_page_info": "Page {page} of {total} | {count} questions",
        "title_info": "Information",
        "title_warning": "Warning",
        "title_error": "Error",
        "title_confirm": "Confirm",
        "msg_no_message_regen": "There is no message to regenerate yet.",
    },
    "es_ES": {
        "window_title": "Reportes - Sistema Opera",
        "title": "Reportes",
        "subtitle": "Control de Stock",
        "refresh": "Actualizar Datos",
        "report_tab": "📋 Reporte",
        "analysis_tab": "📊 Análisis",
        "assistant_tab": "🤖 Asistente",
        "search": "🔎 Buscar por código o descripción...",
        "apply_filters": "Aplicar Filtros",
        "clear_filters": "Limpiar Filtros",
        "category_all": "Todas",
        "category_fabrics": "Tejidos",
        "category_trims": "Avíos",
        "category_inputs": "Insumos",
        "category_office": "Oficina",
        "category_cleaning": "Limpieza",
        "category_other": "Otros",
        "export_csv": "📄 Exportar CSV",
        "generate_pdf": "🖨️ Generar PDF",
        "export_excel": "📊 Exportar Excel",
        "print": "🖨️ Imprimir",
        "header": ["ID", "Descripción", "Categoría", "Cantidad", "Estado", "Ubicación", "Última Actualización"],
        "total_items": "🧾 Total Ítems",
        "critical_items": "⚠️ Ítems Críticos",
        "categories": "📂 Categorías",
        "updated": "🕒 Actualizado",
        "estimated_value": "💰 Valor Estimado",
        "by_category": "Cantidad por Categoría",
        "critical_by_category": "Ítems Críticos por Categoría",
        "assistant_title": "🤖 Asistente Inteligente de Stock",
        "assistant_ph": "Escriba aquí... (Enter para enviar)",
        "assistant_greeting": "👋 ¡Hola! Pregunte sobre críticos, valor, tejidos, ubicación o escriba el código del ítem.",
        "typing_indicator": "escribiendo...",
        "send": "Enviar",
        "quick_1": "Ítems críticos",
        "quick_2": "Valor del stock",
        "quick_3": "Tejidos (metraje)",
        "quick_4": "Sugerencias de compra",
        "quick_5": "Ítems sin movimiento hace 30 días",
        "regen": "🔁 Regenerar",
        "export_chat": "💾 Exportar conversación",
        "suggestions": "💡 Sugerencias/Preguntas",
        "connected": "🟢 Conectado | {data}",
        "add_item_title": "Agregar Ítem de Stock",
        "add_item_search_label": "Buscar ítem (código/descripción/categoría):",
        "add_item_search_button": "Buscar",
        "add_item_confirm": "Confirmar",
        "add_item_cancel": "Cancelar",
        "suggestions_title": "Sugerencias de Preguntas",
        "suggestions_info": "Doble clic en la pregunta para enviarla. Use el filtro para reducir la lista.",
        "suggestions_filter_label": "Filtro:",
        "suggestions_filter_placeholder": "Filtrar preguntas...",
        "suggestions_categories": "Categorías",
        "suggestions_questions": "Preguntas",
        "suggestions_prev": "◀ Anterior",
        "suggestions_next": "Siguiente ▶",
        "suggestions_page_info": "Página {page} de {total} | {count} preguntas",
        "title_info": "Información",
        "title_warning": "Aviso",
        "title_error": "Error",
        "title_confirm": "Confirmar",
        "msg_no_message_regen": "Todavía no hay mensaje para regenerar.",
    },
}

def _opera_page_lang(self):
    idioma = getattr(getattr(self, "sistema", None), "idioma_atual", None)
    if not idioma:
        idioma = getattr(getattr(self, "controller", None), "idioma_atual", None)
    if idioma not in AdvancedStockReport_TRANSLATIONS:
        idioma = "pt_BR"
    return idioma

def _opera_txt(self, key, **kwargs):
    idioma = _opera_page_lang(self)
    bloco = AdvancedStockReport_TRANSLATIONS.get(idioma, AdvancedStockReport_TRANSLATIONS["pt_BR"])
    texto = bloco.get(key, AdvancedStockReport_TRANSLATIONS["pt_BR"].get(key, key))
    if isinstance(texto, str) and kwargs:
        try:
            return texto.format(**kwargs)
        except Exception:
            return texto
    return texto

def _opera_msgbox(self, kind, title_key, message_key, **kwargs):
    title = self._txt(title_key)
    message = self._txt(message_key, **kwargs)
    fn = getattr(messagebox, kind, messagebox.showinfo)
    return fn(title, message)

def _opera_category_values(self):
    return [
        self._txt("category_all"),
        self._txt("category_fabrics"),
        self._txt("category_trims"),
        self._txt("category_inputs"),
        self._txt("category_office"),
        self._txt("category_cleaning"),
        self._txt("category_other"),
    ]

def _opera_refresh_texts_runtime(self):
    try:
        if hasattr(self, "winfo_toplevel"):
            try:
                self.winfo_toplevel().title(self._txt("window_title"))
            except Exception:
                pass
        if hasattr(self, "lbl_header_title"):
            self.lbl_header_title.configure(text=self._txt("subtitle"))
        if hasattr(self, "btn_refresh"):
            self.btn_refresh.configure(text=self._txt("refresh"))
        if hasattr(self, "lbl_footer"):
            self.lbl_footer.configure(text=self._txt("connected", data=datetime.now().strftime('%d/%m/%Y %H:%M')))
        if hasattr(self, "tabs") and hasattr(self, "_tab_keys"):
            vals = [self._txt(k) for k in self._tab_keys]
            try:
                current = self.tabs.get()
                self.tabs._segmented_button.configure(values=vals)
                for old, new in zip(getattr(self, "_tab_labels", vals), vals):
                    if old in self.tabs._name_list and old != new:
                        idx = self.tabs._name_list.index(old)
                        self.tabs._name_list[idx] = new
                        self.tabs._tab_dict[new] = self.tabs._tab_dict.pop(old)
                self._tab_labels = vals
                if current in getattr(self, "_tab_labels", []):
                    self.tabs.set(current)
            except Exception:
                pass
        if hasattr(self, "search_entry"):
            self.search_entry.configure(placeholder_text=self._txt("search"))
        if hasattr(self, "combo_category"):
            current = self.category_var.get() if hasattr(self, "category_var") else None
            vals = self._category_values()
            self.combo_category.configure(values=vals)
            if current not in vals:
                current = vals[0]
            self.combo_category.set(current)
        if hasattr(self, "btn_apply_filters"):
            self.btn_apply_filters.configure(text=self._txt("apply_filters"))
        if hasattr(self, "btn_export_csv"):
            self.btn_export_csv.configure(text=self._txt("export_csv"))
        if hasattr(self, "btn_export_pdf"):
            self.btn_export_pdf.configure(text=self._txt("generate_pdf"))
        if hasattr(self, "btn_export_excel"):
            self.btn_export_excel.configure(text=self._txt("export_excel"))
        if hasattr(self, "btn_print"):
            self.btn_print.configure(text=self._txt("print"))
        if hasattr(self, "tree"):
            headers = self._txt("header")
            for col, head in zip(self.tree["columns"], headers):
                self.tree.heading(col, text=head)
        if hasattr(self, "lbl_assistant_title"):
            self.lbl_assistant_title.configure(text=self._txt("assistant_title"))
        if hasattr(self, "ai_input"):
            self.ai_input.configure(placeholder_text=self._txt("assistant_ph"))
        if hasattr(self, "btn_send"):
            self.btn_send.configure(text=self._txt("send"))
        if hasattr(self, "btn_regen"):
            self.btn_regen.configure(text=self._txt("regen"))
        if hasattr(self, "btn_export_chat"):
            self.btn_export_chat.configure(text=self._txt("export_chat"))
        if hasattr(self, "btn_suggestions"):
            self.btn_suggestions.configure(text=self._txt("suggestions"))
        if hasattr(self, "quick_buttons"):
            keys = ["quick_1", "quick_2", "quick_3", "quick_4", "quick_5"]
            for btn, key in zip(self.quick_buttons, keys):
                btn.configure(text=self._txt(key))
        if hasattr(self, "cards_frame") and hasattr(self, "stats_data"):
            try:
                for widget in self.cards_frame.winfo_children():
                    widget.destroy()
                self._metric_card(self.cards_frame, self._txt("total_items"), self.stats_data.get("total_items", "—")).grid(row=0, column=0, sticky="ew")
                self._metric_card(self.cards_frame, self._txt("critical_items"), self.stats_data.get("low_stock", "—")).grid(row=0, column=1, sticky="ew")
                self._metric_card(self.cards_frame, self._txt("categories"), self.stats_data.get("categories", "—")).grid(row=0, column=2, sticky="ew")
                self._metric_card(self.cards_frame, self._txt("updated"), datetime.now().strftime("%d/%m/%Y %H:%M")).grid(row=0, column=3, sticky="ew")
            except Exception:
                pass
    except Exception:
        pass

def _opera_create_main_layout(self):
    self.grid_rowconfigure(1, weight=1)
    self.grid_columnconfigure(0, weight=1)

    header = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color=self.cor_primaria)
    header.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

    self.lbl_header_title = ctk.CTkLabel(
        header, text=self._txt("subtitle"), font=self.font_titulo,
        text_color=_hex_contrast(self.cor_primaria)
    )
    self.lbl_header_title.pack(side="left", padx=20)

    self.btn_refresh = ctk.CTkButton(
        header, text=self._txt("refresh"), command=self.reload_data, width=140,
        fg_color=self.cor_secundaria, hover_color=self.cor_hover, text_color=self.cor_texto
    )
    self.btn_refresh.pack(side="right", padx=20)

    self.tabs = ctk.CTkTabview(
        self,
        fg_color=self.cor_fundo,
        segmented_button_fg_color=self.cor_primaria,
        segmented_button_selected_color=self.cor_hover,
        segmented_button_unselected_color=self.cor_secundaria,
        segmented_button_unselected_hover_color=self.cor_hover,
        text_color=self.cor_texto
    )
    self.tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    self._tab_keys = ["report_tab", "analysis_tab", "assistant_tab"]
    self._tab_labels = [self._txt(k) for k in self._tab_keys]
    self.tab_report = self.tabs.add(self._tab_labels[0])
    self.tab_analytics = self.tabs.add(self._tab_labels[1])
    self.tab_ai = self.tabs.add(self._tab_labels[2])

    self._setup_report_tab()
    self._setup_analytics_tab()
    self._setup_ai_tab()

    footer = ctk.CTkFrame(self, height=40, fg_color=self.cor_primaria)
    footer.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
    self.lbl_footer = ctk.CTkLabel(
        footer,
        text=self._txt("connected", data=datetime.now().strftime('%d/%m/%Y %H:%M')),
        font=self.font_pequeno,
        text_color=_hex_contrast(self.cor_primaria)
    )
    self.lbl_footer.pack(side="left", padx=20)
    self._refresh_texts_runtime()

def _opera_setup_report_tab(self):
    self.tab_report.grid_rowconfigure(0, weight=1)
    self.tab_report.grid_columnconfigure(0, weight=1)

    wrapper = ctk.CTkFrame(self.tab_report, fg_color=self.cor_fundo)
    wrapper.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
    wrapper.grid_rowconfigure(0, weight=0)
    wrapper.grid_rowconfigure(1, weight=1)
    wrapper.grid_rowconfigure(2, weight=0)
    wrapper.grid_columnconfigure(0, weight=1)

    filtros = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
    filtros.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    filtros.grid_columnconfigure(0, weight=1)

    self.search_entry = ctk.CTkEntry(
        filtros,
        placeholder_text=self._txt("search"),
        fg_color=self.cor_secundaria,
        border_color=self.cor_borda,
        text_color=self.cor_texto_entry,
        placeholder_text_color=self.cor_placeholder
    )
    self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

    self.category_var = tk.StringVar(value=self._category_values()[0])
    self.combo_category = ctk.CTkComboBox(
        filtros,
        variable=self.category_var,
        values=self._category_values(),
        state="readonly",
        fg_color=self.cor_secundaria, border_color=self.cor_borda,
        button_color=self.cor_primaria, button_hover_color=self.cor_hover,
        text_color=self.cor_texto, dropdown_fg_color=self.cor_secundaria,
        dropdown_text_color=self.cor_texto, dropdown_hover_color=self.cor_hover
    )
    self.combo_category.grid(row=0, column=1, padx=(0, 8))

    self.btn_apply_filters = ctk.CTkButton(
        filtros, text=self._txt("apply_filters"), command=self.apply_filters,
        fg_color=self.cor_primaria, hover_color=self.cor_hover, text_color=self.cor_texto
    )
    self.btn_apply_filters.grid(row=0, column=2)

    self._create_stock_table(parent=wrapper)

    export_frame = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
    export_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))

    self.btn_export_csv = ctk.CTkButton(export_frame, text=self._txt("export_csv"),
        fg_color=self.cor_sucesso, hover_color=self.cor_hover, text_color=self.cor_texto,
        command=self.export_csv)
    self.btn_export_csv.pack(side="left", padx=5)

    self.btn_export_pdf = ctk.CTkButton(export_frame, text=self._txt("generate_pdf"),
        fg_color=self.cor_alerta, hover_color=self.cor_hover, text_color=self.cor_texto,
        command=self.export_pdf)
    self.btn_export_pdf.pack(side="left", padx=5)

    self.btn_export_excel = ctk.CTkButton(export_frame, text=self._txt("export_excel"),
        fg_color=self.cor_destaque, hover_color=self.cor_hover, text_color=self.cor_texto,
        command=self.export_excel)
    self.btn_export_excel.pack(side="left", padx=5)

    self.btn_print = ctk.CTkButton(export_frame, text=self._txt("print"),
        fg_color=self.cor_secundaria, hover_color=self.cor_hover, text_color=self.cor_texto,
        command=self._opera_print_report if hasattr(self, "_opera_print_report") else self.export_pdf)
    self.btn_print.pack(side="left", padx=5)

def _opera_setup_ai_tab(self):
    self.tab_ai.grid_rowconfigure(0, weight=1)
    self.tab_ai.grid_columnconfigure(0, weight=1)

    wrapper = ctk.CTkFrame(self.tab_ai, fg_color=self.cor_fundo)
    wrapper.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
    wrapper.grid_rowconfigure(1, weight=1)
    wrapper.grid_columnconfigure(0, weight=1)

    header = ctk.CTkFrame(wrapper, height=48, fg_color=self.cor_primaria)
    header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    header.grid_columnconfigure(0, weight=1)
    self.lbl_assistant_title = ctk.CTkLabel(header, text=self._txt("assistant_title"),
                     font=self.font_titulo_medio, text_color=_hex_contrast(self.cor_primaria))
    self.lbl_assistant_title.grid(row=0, column=0, sticky="w", padx=12, pady=10)

    body = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
    body.grid(row=1, column=0, sticky="nsew")
    body.grid_rowconfigure(0, weight=1)
    body.grid_rowconfigure(1, weight=0)
    body.grid_columnconfigure(0, weight=1)

    self.chat_canvas = tk.Canvas(body, bg=self.cor_fundo, highlightthickness=0, bd=0)
    self.chat_scroll = ttk.Scrollbar(body, orient="vertical", command=self.chat_canvas.yview)
    self.chat_frame = ctk.CTkFrame(self.chat_canvas, fg_color=self.cor_fundo)
    self.chat_frame.bind("<Configure>", lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))
    self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
    self.chat_canvas.configure(yscrollcommand=self.chat_scroll.set)
    self.chat_canvas.grid(row=0, column=0, sticky="nsew")
    self.chat_scroll.grid(row=0, column=1, sticky="ns")

    input_frame = ctk.CTkFrame(body, height=52, fg_color=self.cor_secundaria, corner_radius=12)
    input_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(6, 8))
    input_frame.grid_columnconfigure(0, weight=1)

    self.ai_input = ctk.CTkEntry(
        input_frame, placeholder_text=self._txt("assistant_ph"),
        fg_color=self.cor_secundaria, text_color=self.cor_texto_entry,
        placeholder_text_color=self.cor_placeholder
    )
    self.ai_input.grid(row=0, column=0, sticky="ew", padx=(10, 8), pady=8)
    self.ai_input.bind("<Return>", self.process_ai_query)

    self.btn_send = ctk.CTkButton(
        input_frame, text=self._txt("send"), command=self.process_ai_query,
        fg_color=self.cor_destaque, hover_color=self.cor_hover, text_color=self.cor_texto, width=90
    )
    self.btn_send.grid(row=0, column=1, padx=(0, 10))

    self.quick_actions = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
    self.quick_actions.grid(row=2, column=0, sticky="ew", pady=(6, 0))
    self.quick_buttons = []
    quick_keys = ["quick_1", "quick_2", "quick_3", "quick_4", "quick_5"]
    for i, key in enumerate(quick_keys):
        text = self._txt(key)
        btn = ctk.CTkButton(self.quick_actions, text=text, width=1,
                            fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                            text_color=self.cor_texto, command=lambda t=text: self._send_quick(t))
        btn.grid(row=0, column=i, padx=4)
        self.quick_buttons.append(btn)

    self.extra_actions = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
    self.extra_actions.grid(row=3, column=0, sticky="ew", pady=(4, 0))
    self.btn_regen = ctk.CTkButton(self.extra_actions, text=self._txt("regen"), command=self._regenerate_last,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover, text_color=self.cor_texto)
    self.btn_regen.pack(side="left", padx=4)
    self.btn_export_chat = ctk.CTkButton(self.extra_actions, text=self._txt("export_chat"), command=self._export_chat,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover, text_color=self.cor_texto)
    self.btn_export_chat.pack(side="left", padx=4)
    self.btn_suggestions = ctk.CTkButton(self.extra_actions, text=self._txt("suggestions"), command=self._open_suggestions_window,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover, text_color=self.cor_texto)
    self.btn_suggestions.pack(side="left", padx=4)

    self._post_bot(self._txt("assistant_greeting"), slow=False)

def _opera_show_typing(self):
    wrap = ctk.CTkFrame(self.chat_frame, fg_color=self.cor_fundo)
    wrap.pack(fill="x", padx=8, pady=2)
    bubble = ctk.CTkFrame(wrap, fg_color=self.cor_secundaria, corner_radius=14)
    bubble.pack(anchor="w", padx=6, pady=2)
    label = ctk.CTkLabel(bubble, text=self._txt("typing_indicator"), text_color=self.cor_texto)
    label.pack(padx=10, pady=8)
    self.chat_canvas.update_idletasks()
    self.chat_canvas.yview_moveto(1.0)
    return wrap

def _opera_regenerate_last(self):
    if not getattr(self, "_last_user_prompt", None):
        self._msgbox("showinfo", "title_info", "msg_no_message_regen")
        return
    self._enqueue_ai(self._last_user_prompt, is_regen=True)

def _opera_adicionar_tecido(self):
    dialog = ctk.CTkToplevel(self)
    dialog.title(self._txt("add_item_title"))
    dialog.transient(self.winfo_toplevel())
    dialog.grab_set()
    dialog.focus_force()
    dialog.update_idletasks()
    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    largura = 800
    altura = 600
    x = (sw - largura) // 2
    y = (sh - altura) // 2
    dialog.geometry(f"{largura}x{altura}+{x}+{y}")

    self.obter_cores_por_tema()

    main_frame = ctk.CTkScrollableFrame(dialog, fg_color=self.cor_fundo)
    main_frame.pack(fill="both", expand=True, padx=10, pady=(10, 18))

    search_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
    search_frame.pack(fill="x", pady=5)

    ctk.CTkLabel(search_frame, text=self._txt("add_item_search_label"),
                 width=220, anchor="w", text_color=self.cor_texto).pack(side="left", padx=5)

    search_entry = ctk.CTkEntry(search_frame, fg_color=self.cor_secundaria,
                                border_color=self.cor_borda, text_color=self.cor_texto_entry,
                                placeholder_text_color=self.cor_placeholder)
    search_entry.pack(side="left", fill="x", expand=True, padx=5)

    tree_frame = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
    tree_frame.pack(fill="both", expand=True, pady=5)

    columns = ["Código", "Descrição", "Categoria", "Quantidade", "Localização", "Status"]
    tecido_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8, style="Custom.Treeview")
    for col in columns:
        tecido_tree.heading(col, text=col)
        tecido_tree.column(col, width=130 if col in ("Descrição", "Localização") else 100, anchor='w' if col in ("Descrição","Categoria","Localização") else 'center')
    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tecido_tree.yview)
    scrollbar.pack(side="right", fill="y")
    tecido_tree.configure(yscrollcommand=scrollbar.set)
    tecido_tree.pack(fill="both", expand=True)

    btn_buscar = ctk.CTkButton(search_frame, text=self._txt("add_item_search_button"),
                               command=lambda: self._buscar_tecidos_para_adicao(search_entry, tecido_tree))
    btn_buscar.pack(side="left", padx=5)

    btn_row = ctk.CTkFrame(main_frame, fg_color=self.cor_fundo)
    btn_row.pack(fill="x", pady=(8, 0))
    ctk.CTkButton(btn_row, text=self._txt("add_item_confirm"),
                  command=lambda: self._confirmar_adicao_tecido(dialog, tecido_tree)).pack(side="right", padx=5)
    ctk.CTkButton(btn_row, text=self._txt("add_item_cancel"),
                  command=dialog.destroy, fg_color=self.cor_secundaria, text_color=self.cor_texto).pack(side="right", padx=5)

def _opera_open_suggestions_window(self):
    win = ctk.CTkToplevel(self)
    win.title(self._txt("suggestions_title"))
    win.geometry("860x560")
    win.grab_set()

    self.obter_cores_por_tema()

    top = ctk.CTkFrame(win, fg_color=self.cor_fundo)
    top.pack(fill="x", padx=10, pady=(10, 6))
    ctk.CTkLabel(top, text=self._txt("suggestions_info"), text_color=self.cor_texto).pack(anchor="w")

    filt_row = ctk.CTkFrame(win, fg_color=self.cor_fundo)
    filt_row.pack(fill="x", padx=10, pady=(0, 6))
    ctk.CTkLabel(filt_row, text=self._txt("suggestions_filter_label"), text_color=self.cor_texto, width=60).pack(side="left")

    self._sug_filter_var = tk.StringVar()
    self._sug_filter = ctk.CTkEntry(
        filt_row, textvariable=self._sug_filter_var,
        placeholder_text=self._txt("suggestions_filter_placeholder"),
        fg_color=self.cor_secundaria, border_color=self.cor_borda,
        text_color=self.cor_texto_entry, placeholder_text_color=self.cor_placeholder
    )
    self._sug_filter.pack(side="left", fill="x", expand=True)
    self._sug_filter_var.trace_add("write", lambda *a: self._reload_questions())

    body = ctk.CTkFrame(win, fg_color=self.cor_fundo)
    body.pack(fill="both", expand=True, padx=10, pady=10)
    body.grid_columnconfigure(0, weight=1)
    body.grid_columnconfigure(1, weight=3)
    body.grid_rowconfigure(0, weight=1)
    body.grid_rowconfigure(1, weight=0)

    left = ctk.CTkFrame(body, fg_color=self.cor_fundo)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    ctk.CTkLabel(left, text=self._txt("suggestions_categories"), text_color=self.cor_texto).pack(anchor="w")
    self._sug_cat_list = tk.Listbox(left, activestyle="dotbox", bg=self.cor_secundaria, fg=self.cor_texto,
                                    selectbackground=self.cor_selecao)
    self._sug_cat_list.pack(fill="both", expand=True)
    self._sug_cat_list.bind("<<ListboxSelect>>", lambda e: self._on_select_category())

    right = ctk.CTkFrame(body, fg_color=self.cor_fundo)
    right.grid(row=0, column=1, sticky="nsew")
    ctk.CTkLabel(right, text=self._txt("suggestions_questions"), text_color=self.cor_texto).pack(anchor="w")
    self._sug_q_list = tk.Listbox(right, activestyle="dotbox", bg=self.cor_secundaria, fg=self.cor_texto,
                                  selectbackground=self.cor_selecao)
    self._sug_q_list.pack(fill="both", expand=True)
    self._sug_q_list.bind("<Double-Button-1>", lambda e: self._insert_selected_question())

    nav = ctk.CTkFrame(body, fg_color=self.cor_fundo)
    nav.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8,0))
    self._sug_prev_btn = ctk.CTkButton(nav, text=self._txt("suggestions_prev"), width=110, command=self._sug_prev_page)
    self._sug_prev_btn.pack(side="left", padx=4)
    self._sug_next_btn = ctk.CTkButton(nav, text=self._txt("suggestions_next"), width=110, command=self._sug_next_page)
    self._sug_next_btn.pack(side="right", padx=4)
    self._sug_page_label = ctk.CTkLabel(nav, text="")
    self._sug_page_label.pack(side="left", expand=True)

    try:
        self._load_suggestion_bases()
        self._reload_categories()
        self._reload_questions()
    except Exception:
        pass

# aplicar monkey patches
AdvancedStockReport._page_lang = _opera_page_lang
AdvancedStockReport._txt = _opera_txt
AdvancedStockReport._msgbox = _opera_msgbox
AdvancedStockReport._category_values = _opera_category_values
AdvancedStockReport._refresh_texts_runtime = _opera_refresh_texts_runtime
AdvancedStockReport._create_main_layout = _opera_create_main_layout
AdvancedStockReport._setup_report_tab = _opera_setup_report_tab
AdvancedStockReport._setup_ai_tab = _opera_setup_ai_tab
AdvancedStockReport._show_typing = _opera_show_typing
AdvancedStockReport._regenerate_last = _opera_regenerate_last
AdvancedStockReport.adicionar_tecido = _opera_adicionar_tecido
AdvancedStockReport._open_suggestions_window = _opera_open_suggestions_window

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.title("Relatórios - Sistema Opera")
    root.geometry("1100x760")

    app = AdvancedStockReport(root)
    app.pack(fill="both", expand=True)

    root.mainloop()
