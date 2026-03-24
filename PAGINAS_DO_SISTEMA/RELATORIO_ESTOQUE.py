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
class EstoqueIA:
    """
    Assistente de Estoque - MEGA
    - Intenções ampliadas (40+ intenções, centenas de frases)
    - Extração de entidades (código, números, datas relativas, categoria, local)
    - Perguntas dinâmicas a partir das categorias/locais existentes
    - Handlers: críticos, excesso, zerados/negativos, reposição, ponto de pedido,
      valor por categoria/local, top/bottom N, ABC/Pareto, parados, auditoria, etc.
    """

    INTENT_KWS: Dict[str, List[str]] = {
        # gerais
        "saudacao": ["oi", "olá", "ola", "eae", "bom dia", "boa tarde", "boa noite", "fala"],
        "ajuda": ["ajuda", "o que você faz", "como usa", "exemplos", "sugestões", "perguntas", "help", "menu"],
        "contexto": ["histórico", "contexto", "o que falamos", "últimas mensagens", "ultimo"],
        # inventário
        "categorias": ["categorias", "quais categorias", "listar categorias", "tipos de item", "famílias"],
        "locais": ["locais", "localizações", "endereços", "prateleiras", "setores", "depósito", "deposito", "armário",
                   "armario"],
        "quantidade_total": ["total de itens", "quantos itens", "quantidade total", "qtd total"],
        "itens_unicos": ["itens diferentes", "quantos códigos", "quantos produtos"],
        # estados
        "criticos": ["crítico", "críticos", "baixo", "baixa", "urgente", "prioritário", "repor", "reposição urgente"],
        "excesso": ["excesso", "alto demais", "acima do máximo", "super estocado", "estouro de estoque"],
        "zerados": ["zerado", "zerados", "acabou", "em falta", "faltando", "estoque zero"],
        "negativos": ["negativo", "negativos", "quantidade negativa", "estoque negativo"],
        # compras/reposição
        "reposicao": ["repor", "reposição", "comprar", "pedido de compra", "sugestões de compra",
                      "sugestoes de compra"],
        "ponto_pedido": ["ponto de pedido", "reorder point", "minimo", "mínimo", "maximo", "máximo", "parametros"],
        "leadtime": ["lead time", "tempo de reposição", "dias de entrega"],
        # valor e análises
        "valor_total": ["valor do estoque", "valor total", "patrimônio", "financeiro"],
        "valor_por_categoria": ["valor por categoria", "categoria valor", "custos por categoria"],
        "valor_por_local": ["valor por local", "valor por localização", "custos por local"],
        # grupos específicos
        "tecidos": ["tecido", "tecidos", "metragem", "metros", "rolo", "rolos"],
        "aviamentos": ["aviamento", "aviamentos", "botão", "botões", "zíper", "ziper", "linha", "agulha", "elástico"],
        "limpeza": ["limpeza", "sabão", "detergente", "desinfetante", "vassoura", "pano"],
        "escritorio": ["escritório", "escritorio", "papel", "toner", "caneta", "clipe", "post-it"],
        # rankings
        "top_n": ["top", "maiores", "mais estocados", "mais quantidade", "top itens"],
        "bottom_n": ["menores", "menos quantidade", "quase acabando", "bottom"],
        "abc": ["abc", "pareto", "classe a", "classe b", "classe c", "curva abc"],
        # temporalidade
        "antigos": ["antigo", "antigos", "parado", "não movimentado", "nao movimentado", "obsoleto", "parados"],
        "recem_entrada": ["entrou", "recentes", "chegaram", "novo lote", "novidades"],
        "periodo": ["desde", "até", "entre", "no mês", "na semana", "no dia", "no ano"],
        # busca / utilidades
        "buscar_item": ["buscar", "procurar", "encontrar", "detalhes do", "info do", "dados do"],
        "abrir_por_codigo": ["código", "codigo", "cod:"],
        "comparar": ["comparar", "vs", "contra", "diferença", "dif", "melhor que"],
        "exportar": ["exportar", "csv", "excel", "pdf", "salvar relatório", "salvar relatorio"],
        "agrupar": ["agrupar", "por categoria", "por local", "resumo por", "consolidar"],
        "ajustes": ["ajustar", "corrigir", "inconsistência", "inconsistencia", "duplicados", "valores estranhos"],
    }

    CATEGORY_CANON: Dict[str, List[str]] = {
        "tecidos": ["tecido", "tecidos", "algodão", "algodao", "jeans", "tricoline", "sarja", "viscose", "malha"],
        "aviamentos": ["aviamento", "aviamentos", "botão", "botao", "botões", "ziper", "zíper", "linha", "elástico",
                       "elastico"],
        "limpeza": ["limpeza", "detergente", "sabao", "sabão", "desinfetante", "vassoura", "pano"],
        "escritorio": ["escritorio", "escritório", "papel", "toner", "caneta", "clipe", "post-it"],
        "outros": ["diversos", "outros", "geral"]
    }

    LOCATION_HINTS = ["prateleira", "armário", "armario", "rua", "posição", "posicao", "setor", "deposito", "depósito"]

    def __init__(self, resultados: List[Tuple[Any, ...]]):
        self.resultados = resultados or []
        self.ctx: List[Tuple[str, str]] = []
        self.last_intent: Optional[str] = None
        self.last_entities: Dict[str, Any] = {}

        self._build_indexes()
        self._recompute_stats()

    def _build_indexes(self):
        self.by_cat: Dict[str, list] = defaultdict(list)
        self.by_loc: Dict[str, list] = defaultdict(list)
        self.by_code: Dict[str, tuple] = {}
        self.categories_found: Counter = Counter()

        for row in self.resultados:
            codigo, descricao, categoria, quantidade, status, local, dt = (list(row) + [None] * 7)[:7]
            cat = (categoria or "—").strip()
            loc = (str(local) if local else "—").strip()
            self.by_cat[cat].append(row)
            self.by_loc[loc].append(row)
            self.by_code[str(codigo).lower()] = row
            self.categories_found[cat.lower()] += 1

        self.cat_value_factor = defaultdict(lambda: 7.0)
        for k in list(self.categories_found.keys()):
            kl = k.lower()
            if "tecido" in kl:
                self.cat_value_factor[k] = 15.0
            elif "aviam" in kl:
                self.cat_value_factor[k] = 2.5
            elif "escrit" in kl:
                self.cat_value_factor[k] = 6.0
            elif "limp" in kl:
                self.cat_value_factor[k] = 5.0

    def _recompute_stats(self):
        self.total_items = len(self.resultados)
        self.total_distintos = len({str(r[0]) for r in self.resultados})
        self.low_stock = sum(1 for r in self.resultados if self._qty(r) < 10)
        self.zero_stock = sum(1 for r in self.resultados if self._qty(r) <= 0)
        self.negativos = sum(1 for r in self.resultados if self._qty(r) < 0)
        self.categorias = len(self.categories_found)
        self.valor_total = sum(self._value_of(r) for r in self.resultados)

    def _qty(self, row) -> float:
        try:
            return float(row[3] or 0)
        except Exception:
            return 0.0

    def _value_of(self, row) -> float:
        cat = (row[2] or "outros")
        return self._qty(row) * float(self.cat_value_factor[cat.lower()])

    def _remember(self, who: str, text: str):
        self.ctx.append((who, text))
        if len(self.ctx) > 20:
            self.ctx.pop(0)

    def _intent_score(self, q: str):
        ql = q.lower()
        scores = {}
        for intent, kws in self.INTENT_KWS.items():
            s = 0.0
            for kw in kws:
                if kw in ql:
                    s += 1.0
            near = get_close_matches(ql, kws, n=1, cutoff=0.88)
            if near:
                s += 0.3
            scores[intent] = s
        best = max(scores, key=scores.get)
        conf = scores[best] / (len(ql.split()) + 0.5)
        return (best if scores[best] > 0 else None, conf)

    def _extract(self, q: str) -> Dict[str, Any]:
        ql = q.lower()
        numbers = [float(m) for m in re.findall(r'(?<!\w)(\d+\.?\d*)(?!\w)', ql)]
        n = None
        m = re.search(r'\btop\s*(\d{1,3})\b', ql) or re.search(r'\b(\d{1,3})\s*itens\b', ql)
        if m:
            n = int(m.group(1))
        if not n and numbers and any(k in ql for k in ["top", "maiores", "menores", "bottom"]):
            n = int(numbers[0])

        cats = set()
        for canon, synonyms in self.CATEGORY_CANON.items():
            if any(s in ql for s in synonyms):
                cats.add(canon)
        for c in self.categories_found.keys():
            if c in ql:
                cats.add(c)

        locs = [w for w in self.LOCATION_HINTS if w in ql]

        days = None
        if "30 dias" in ql or "trinta dias" in ql:
            days = 30
        elif "15 dias" in ql or "quinze dias" in ql:
            days = 15
        elif any(x in ql for x in ["7 dias", "uma semana", "7d"]):
            days = 7

        code = None
        m = re.search(r'c[oó]d(?:igo)?\s*[:#]?\s*([a-z0-9\-_.]+)', ql)
        if m:
            code = m.group(1)

        return {"n": n, "numbers": numbers, "cats": list(cats), "locs": locs, "days": days, "code": code}

    # ------------------------ Público ------------------------
    def responder(self, pergunta: str) -> str:
        q = (pergunta or "").strip()
        if not q:
            return "Digite uma pergunta. Ex: *Itens críticos*, *Valor por categoria Tecidos*, *Top 10 por quantidade*."
        self._remember("user", q)

        intent, conf = self._intent_score(q)
        self.last_intent = intent if conf > 0.35 else None
        self.last_entities = self._extract(q)

        if intent == "saudacao":
            return self._say_hello()
        if intent == "ajuda":
            return self._help_text(page=1)
        if intent == "contexto":
            return self._contexto()

        if intent == "categorias":
            return self._categorias()
        if intent == "locais":
            return self._locais()
        if intent == "quantidade_total":
            return self._quant_total()
        if intent == "itens_unicos":
            return f"🔢 Produtos distintos: **{self.total_distintos}**."

        if intent == "criticos":
            return self._criticos()
        if intent == "excesso":
            return self._excesso()
        if intent == "zerados":
            return self._zerados()
        if intent == "negativos":
            return self._negativos()

        if intent == "reposicao":
            return self._reposicao(meta=20)
        if intent == "ponto_pedido":
            return self._ponto_pedido()
        if intent == "leadtime":
            return "⏱️ *Lead time*: informe dias por categoria. Ex.: `lead time tecidos 7 dias`."

        if intent == "valor_total":
            return self._valor_total()
        if intent == "valor_por_categoria":
            return self._valor_por_categoria()
        if intent == "valor_por_local":
            return self._valor_por_local()

        if intent in ("tecidos", "aviamentos", "limpeza", "escritorio"):
            return self._grupagem(intent)

        if intent == "top_n":
            return self._top_n()
        if intent == "bottom_n":
            return self._bottom_n()
        if intent == "abc":
            return self._abc()

        if intent == "antigos":
            return self._antigos(self.last_entities.get("days"))
        if intent == "recem_entrada":
            return "🆕 Itens com entrada recente dependem da sua tabela de movimentação/atualização."

        if intent in ("buscar_item", "abrir_por_codigo", "comparar"):
            out = self._buscar(q)
            if out:
                return out

        if intent == "exportar":
            return "💾 Posso exportar CSV/PDF/Planilha pela aba *Relatório*. Quer que eu filtre antes?"
        if intent == "agrupar":
            return self._agrupar_auto(q)
        if intent == "ajustes":
            return self._auditar_dados()

        out = self._buscar(q)
        if out:
            return out
        return self._fallback()

    # -------------------- Handlers --------------------
    def _say_hello(self) -> str:
        tips = [
            "Pergunte *Itens críticos* ou *Valor do estoque*.",
            "Tente *Top 10 por quantidade* ou *ABC* para ver concentração.",
            "Diga *Categorias* ou *Locais* para começar um filtro rápido.",
        ]
        return "👋 Oi! Vamos gerenciar seu estoque. " + random.choice(tips)

    def _help_text(self, page: int = 1) -> str:
        base = [
            "Itens críticos", "Itens zerados", "Itens negativos", "Excesso de estoque",
            "Valor do estoque", "Valor por categoria", "Valor por local", "ABC (Pareto)",
            "Top 20 por quantidade", "Bottom 20 por quantidade", "Itens não movimentados há 30 dias",
            "Quais categorias temos?", "Quais locais temos?", "Produtos distintos",
            "Tecidos por localização", "Aviamentos críticos", "Limpeza com baixo estoque",
            "Escritório (itens e valores)", "Sugestões de compra", "Ponto de pedido",
            "Comparar tecidos vs aviamentos", "Consolidar por categoria",
            "Abrir por código: 123", "Buscar: zíper", "Top 10 em {cat}", "Bottom 10 em {cat}",
            "Valor em {cat}", "Itens críticos em {cat}", "Itens no local {loc}",
            "Top 10 no local {loc}", "Valor no local {loc}", "Agrupar por local",
            "Itens acima do máximo", "Itens abaixo do mínimo", "Parados há 15 dias",
            "Exportar CSV", "Gerar PDF", "Listar status por categoria"
        ]
        cats = list({c for c in self.by_cat.keys() if c != "—"})
        locs = list({l for l in self.by_loc.keys() if l != "—"})

        def expand(items):
            out = []
            for s in items:
                if "{cat}" in s and cats:
                    out += [s.replace("{cat}", c) for c in cats[:8]]
                elif "{loc}" in s and locs:
                    out += [s.replace("{loc}", l) for l in locs[:8]]
                else:
                    out.append(s)
            return out

        big = expand(base)
        more = []
        for c in cats[:10]:
            more += [f"Quanto vale a categoria {c}?", f"Itens críticos da categoria {c}"]
        for l in locs[:10]:
            more += [f"Quais itens no local {l}?", f"Valor do estoque no local {l}"]
        universe = list(dict.fromkeys(big + more))
        per_page = 40
        pages = max(1, (len(universe) + per_page - 1) // per_page)
        page = max(1, min(page, pages))
        start = (page - 1) * per_page
        end = start + per_page
        block = "\n".join(f"• {q}" for q in universe[start:end])
        return f"🆘 **Exemplos (pág. {page}/{pages})**:\n{block}\n\n" + (
            f"Diga *ajuda página {page + 1}* para ver mais." if page < pages else "")

    def _contexto(self) -> str:
        if not self.ctx:
            return "📌 Ainda não há histórico nesta conversa."
        lines = []
        for who, text in self.ctx[-8:]:
            lines.append(
                f"- **{('Você' if who == 'user' else 'Assistente')}**: {text[:100]}{'...' if len(text) > 100 else ''}")
        return "🗂️ **Últimas trocas**:\n" + "\n".join(lines)

    def _categorias(self) -> str:
        if not self.by_cat:
            return "ℹ️ Nenhuma categoria encontrada."
        cats = sorted(self.by_cat.keys())
        linhas = ["📂 **Categorias**:"] + [f"- {c} ({len(self.by_cat[c])} itens)" for c in cats]
        linhas.append("\n💡 Dica: *Valor em <categoria>* ou *Top 10 em <categoria>*")
        return "\n".join(linhas)

    def _locais(self) -> str:
        locs = sorted(self.by_loc.keys())
        if not locs:
            return "ℹ️ Sem locais cadastrados."
        linhas = ["🗄️ **Locais**:"] + [f"- {l} ({len(self.by_loc[l])} itens)" for l in locs]
        linhas.append("\n💡 Dica: *Itens no local <nome>* ou *Valor no local <nome>*")
        return "\n".join(linhas)

    def _quant_total(self) -> str:
        return f"📦 Itens (linhas) no estoque: **{self.total_items}**. Distintos: **{self.total_distintos}**."

    def _criticos(self, cat: Optional[str] = None) -> str:
        data = self._filter_cat(cat)
        crit = [r for r in data if self._qty(r) < 10]
        if not crit:
            return "✅ Sem itens críticos no momento."
        crit.sort(key=lambda r: self._qty(r))
        linhas = ["🔴 **Críticos (<10)**:"]
        for r in crit[:30]:
            linhas.append(f"- {r[1]} (Cód {r[0]}): {self._qty(r):.2f}")
        linhas.append("\n💡 Posso gerar *Sugestões de compra* com meta 20.")
        return "\n".join(linhas)

    def _excesso(self) -> str:
        linhas = ["🟣 **Possível excesso**:"]
        count = 0
        for cat, items in self.by_cat.items():
            qs = sorted(self._qty(r) for r in items)
            if not qs:
                continue
            med = qs[len(qs) // 2]
            limite = max(30.0, med * 2.0)
            for r in items:
                if self._qty(r) > limite:
                    linhas.append(f"- [{cat}] {r[1]}: {self._qty(r):.2f} (> {limite:.2f})")
                    count += 1
                    if count >= 30:
                        break
            if count >= 30:
                break
        if count == 0:
            return "👍 Não identifiquei excesso relevante com a heurística atual."
        return "\n".join(linhas)

    def _zerados(self) -> str:
        items = [r for r in self.resultados if self._qty(r) <= 0]
        if not items:
            return "👌 Não há itens zerados."
        linhas = ["⚫ **Zerados**:"]
        for r in items[:40]:
            linhas.append(f"- {r[1]} (Cód {r[0]})")
        return "\n".join(linhas)

    def _negativos(self) -> str:
        items = [r for r in self.resultados if self._qty(r) < 0]
        if not items:
            return "👌 Não há itens com quantidade negativa."
        linhas = ["🟥 **Negativos**:"]
        for r in items[:40]:
            linhas.append(f"- {r[1]} (Cód {r[0]}): {self._qty(r):.2f}")
        linhas.append("\n⚠️ Sugiro auditar movimentações e contagens físicas.")
        return "\n".join(linhas)

    def _reposicao(self, meta=20) -> str:
        pend = [r for r in self.resultados if self._qty(r) < meta]
        if not pend:
            return "✅ Todos os itens acima da meta de reposição."
        linhas = [f"📋 **Sugestões de compra** (meta {meta}):"]
        for r in pend[:40]:
            falta = max(0, meta - self._qty(r))
            linhas.append(f"- {r[1]}: +{falta:.0f}")
        linhas.append("\n💡 Dica: *Ponto de pedido* para refinar mínimos/máximos por categoria.")
        return "\n".join(linhas)

    def _ponto_pedido(self) -> str:
        return (
            "📐 **Ponto de Pedido (PP)**\n"
            "PP = Demanda Diária × Lead Time + Estoque de Segurança.\n"
            "Informe demanda média e lead time por categoria para cálculo prático.\n"
            "Exemplo: *Tecidos demanda 10m/dia, lead 7 dias, segurança 20m*."
        )

    def _valor_total(self) -> str:
        return f"💰 **Valor estimado do estoque**: **R$ {self.valor_total:,.2f}**.\n" \
               f"💡 *Valor por categoria* ou *por local* pode detalhar melhor."

    def _valor_por_categoria(self) -> str:
        linhas = ["💰 **Valor por categoria**:"]
        for cat, items in self.by_cat.items():
            total = sum(self._value_of(r) for r in items)
            linhas.append(f"- {cat}: R$ {total:,.2f} (itens {len(items)})")
        return "\n".join(linhas)

    def _valor_por_local(self) -> str:
        linhas = ["🏷️ **Valor por local**:"]
        for loc, items in self.by_loc.items():
            total = sum(self._value_of(r) for r in items)
            linhas.append(f"- {loc}: R$ {total:,.2f} (itens {len(items)})")
        return "\n".join(linhas)

    def _grupagem(self, group: str) -> str:
        target = []
        for cat, items in self.by_cat.items():
            cl = cat.lower()
            if group in cl or any(s in cl for s in self.CATEGORY_CANON.get(group, [])):
                target += items
        if not target:
            return f"ℹ️ Não encontrei itens do grupo *{group}*."
        total = sum(self._qty(r) for r in target)
        crit = sum(1 for r in target if self._qty(r) < 10)
        linhas = [
            f"📦 **{group.capitalize()}**",
            f"• Itens: **{len(target)}**",
            f"• Quantidade total: **{total:.2f}**",
            f"• Críticos (<10): **{crit}**"
        ]
        linhas.append("💡 Diga: *Top 10 em {grupo}* ou *Valor em {grupo}*.")
        return "\n".join(linhas)

    def _top_n(self) -> str:
        n = self.last_entities.get("n") or 10
        cats = self.last_entities.get("cats") or []
        data = self._filter_cat(cats[0] if cats else None)
        data.sort(key=lambda r: self._qty(r), reverse=True)
        if not data:
            return "ℹ️ Sem dados para ranquear."
        linhas = [f"🏆 **Top {n} por quantidade**:"]
        for r in data[:n]:
            linhas.append(f"- {r[1]} (Cód {r[0]}): {self._qty(r):.2f}")
        return "\n".join(linhas)

    def _bottom_n(self) -> str:
        n = self.last_entities.get("n") or 10
        cats = self.last_entities.get("cats") or []
        data = self._filter_cat(cats[0] if cats else None)
        data.sort(key=lambda r: self._qty(r))
        if not data:
            return "ℹ️ Sem dados para ranquear."
        linhas = [f"⬇️ **Bottom {n} por quantidade**:"]
        for r in data[:n]:
            linhas.append(f"- {r[1]} (Cód {r[0]}): {self._qty(r):.2f}")
        return "\n".join(linhas)

    def _abc(self) -> str:
        arr = [(r, self._value_of(r)) for r in self.resultados]
        total = sum(v for _, v in arr) or 1.0
        arr.sort(key=lambda x: x[1], reverse=True)
        cumul = 0.0
        a = b = c = 0
        for r, v in arr:
            cumul += v
            share = cumul / total
            if share <= 0.8:
                a += 1
            elif share <= 0.95:
                b += 1
            else:
                c += 1
        return f"📊 **Curva ABC (por valor)**:\n" \
               f"- Classe A: {a} itens (~80% do valor)\n" \
               f"- Classe B: {b} itens (~15%)\n" \
               f"- Classe C: {c} itens (~5%)\n" \
               f"💡 Foque controles rigorosos na *Classe A*."

    def _antigos(self, dias: Optional[int]) -> str:
        dias = dias or 30
        lim = datetime.now() - timedelta(days=int(dias))
        dated = []
        for r in self.resultados:
            dt = r[6]
            try:
                if hasattr(dt, "strftime"):
                    d = dt
                else:
                    d = None
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
                        try:
                            d = datetime.strptime(str(dt), fmt)
                            break
                        except Exception:
                            continue
                if d and d <= lim:
                    dated.append((d, r))
            except Exception:
                continue
        if not dated:
            return f"ℹ️ Não encontrei itens parados há {dias} dias (ou sem data válida)."
        dated.sort()
        linhas = [f"📅 **Itens parados há ≥{dias} dias**:"]
        for d, r in dated[:30]:
            linhas.append(f"- {r[1]} (desde {_fmt_date(d)})")
        return "\n".join(linhas)

    def _buscar(self, q: str) -> Optional[str]:
        ql = q.lower()
        code = self.last_entities.get("code")
        if code and code in self.by_code:
            return self._format_item(self.by_code[code])
        if ql in self.by_code:
            return self._format_item(self.by_code[ql])
        names = [(r, (r[1] or "").lower()) for r in self.resultados]
        matches = [r for r, n in names if any(p for p in ql.split() if p and p in n)]
        if not matches:
            universe = [n for _, n in names]
            close = get_close_matches(ql, universe, n=5, cutoff=0.63)
            matches = [r for r, n in names if n in close]
        if not matches:
            return None
        if len(matches) == 1:
            return self._format_item(matches[0])
        linhas = [f"🔎 Encontrei **{len(matches)}** itens parecidos:"]
        for r in matches[:15]:
            linhas.append(f"- {r[1]} (Cód {r[0]}, Qtd {self._qty(r):.2f})")
        linhas.append("\n💡 Diga *Código: <id>* para abrir um item específico.")
        return "\n".join(linhas)

    def _format_item(self, r) -> str:
        qty = self._qty(r)
        status = "🔴 CRÍTICO" if qty < 10 else ("🟡 ALERTA" if qty < 15 else "🟢 OK")
        return (
                "📋 **Item**\n"
                f"• Código: `{r[0]}`\n"
                f"• Descrição: {r[1]}\n"
                f"• Categoria: {r[2]}\n"
                f"• Quantidade: **{qty:.2f}**\n"
                f"• Status: {status}\n"
                f"• Localização: {r[5] or '—'}\n"
                f"• Últ. atualização: {_fmt_date(r[6])}\n"
                + (f"💡 Sug. compra (meta 20): +{max(0, 20 - qty):.0f}" if qty < 20 else "")
        )

    def _agrupar_auto(self, q: str) -> str:
        if "categoria" in q.lower():
            return self._valor_por_categoria()
        if "local" in q.lower() or "localização" in q.lower():
            return self._valor_por_local()
        return "🔀 Posso agrupar por *categoria* ou *local*. Qual prefere?"

    def _auditar_dados(self) -> str:
        linhas = ["🧪 **Auditoria rápida**:"]
        seen = set();
        dups = []
        for r in self.resultados:
            code = str(r[0]).lower()
            if code in seen:
                dups.append(code)
            seen.add(code)
        if dups:
            linhas.append(f"- Códigos duplicados: {len(set(dups))}")
        else:
            linhas.append("- Sem códigos duplicados.")
        vazias = sum(1 for r in self.resultados if not (r[1] or "").strip())
        if vazias:
            linhas.append(f"- Descrições vazias: {vazias}")
        absurdas = sum(1 for r in self.resultados if abs(self._qty(r)) > 1e6)
        if absurdas:
            linhas.append(f"- Quantidades potencialmente incorretas: {absurdas}")
        if len(linhas) == 1:
            linhas.append("Tudo consistente! ✅")
        return "\n".join(linhas)

    def _filter_cat(self, cat: Optional[str]) -> List[tuple]:
        if not cat:
            return list(self.resultados)
        out = []
        for c, arr in self.by_cat.items():
            cl = c.lower()
            if str(cat).lower() in cl:
                out += arr
        if not out:
            syns = self.CATEGORY_CANON.get(str(cat).lower(), [])
            for c, arr in self.by_cat.items():
                if any(s in c.lower() for s in syns):
                    out += arr
        return out

    def _fallback(self) -> str:
        choices = [
            "Quer ver *Itens críticos* ou *Zerados*?",
            "Posso mostrar *Valor por categoria* ou *Valor por local*.",
            "Tente *Top 10 por quantidade* ou *ABC (Pareto)*.",
            "Escreva *Buscar: descrição* ou *Código: 123*."
        ]
        return "🤖 Não captei exatamente. " + random.choice(choices)


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

        self._setup_styles()
        self._create_main_layout()
        self.reload_data()
        self._setup_window_protocol()

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
            filtros, placeholder_text="🔎 Buscar por código ou descrição...",
            fg_color=self.cor_secundaria, border_color=self.cor_borda,
            text_color=self.cor_texto_entry, placeholder_text_color=self.cor_placeholder
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.category_var = tk.StringVar(value="Todas")
        self.combo_category = ctk.CTkComboBox(
            filtros, variable=self.category_var, values=["Todas", "Tecidos", "Aviamentos", "Outros"],
            fg_color=self.cor_secundaria, border_color=self.cor_borda,
            button_color=self.cor_primaria, button_hover_color=self.cor_hover,
            text_color=self.cor_texto, dropdown_fg_color=self.cor_secundaria,
            dropdown_text_color=self.cor_texto, dropdown_hover_color=self.cor_hover
        )
        self.combo_category.grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            filtros, text="Aplicar Filtros", command=self.apply_filters,
            fg_color=self.cor_primaria, hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).grid(row=0, column=2)

        # Tabela - MESMO PADRÃO DO CADASTRO_DE_CORTE
        self._create_stock_table(parent=wrapper)

        # Export - MESMO PADRÃO DO CADASTRO_DE_CORTE
        export_frame = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        export_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        ctk.CTkButton(export_frame, text="📄 Exportar CSV", fg_color=self.cor_sucesso,
                      hover_color=self.cor_hover, text_color=self.cor_texto,
                      command=self.export_csv).pack(side="left", padx=5)

        ctk.CTkButton(export_frame, text="🖨️ Gerar PDF", fg_color=self.cor_alerta,
                      hover_color=self.cor_hover, text_color=self.cor_texto,
                      command=self.export_pdf).pack(side="left", padx=5)

        ctk.CTkButton(export_frame, text="📊 Exportar Excel", fg_color=self.cor_destaque,
                      hover_color=self.cor_hover, text_color=self.cor_texto,
                      command=self.export_excel).pack(side="left", padx=5)

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

        cols = ["ID", "Descrição", "Categoria", "Quantidade", "Status", "Localização", "Última Atualização"]
        self.tree = ttk.Treeview(
            table_wrap, columns=cols, show="headings",
            style="Custom.Treeview", yscrollcommand=vsb.set, xscrollcommand=hsb.set
        )

        for name, width, anchor in [
            ("ID", 80, "center"),
            ("Descrição", 300, "w"),
            ("Categoria", 120, "w"),
            ("Quantidade", 90, "center"),
            ("Status", 90, "center"),
            ("Localização", 150, "w"),
            ("Última Atualização", 140, "center"),
        ]:
            self.tree.heading(name, text=name)
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

        self._metric_card(self.cards_frame, "🧾 Total Itens", "—").grid(row=0, column=0, sticky="ew")
        self._metric_card(self.cards_frame, "⚠️ Itens Críticos", "—").grid(row=0, column=1, sticky="ew")
        self._metric_card(self.cards_frame, "📂 Categorias", "—").grid(row=0, column=2, sticky="ew")
        self._metric_card(self.cards_frame, "🕒 Atualizado", "—").grid(row=0, column=3, sticky="ew")

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
        ax1.set_title('Itens por Categoria')
        ax1.tick_params(axis='x', rotation=45)

        ax2 = fig.add_subplot(1, 2, 2)
        ax2.bar(list(critical_items.keys()), list(critical_items.values()))
        ax2.set_title('Itens Críticos')
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

        _metric("🧾 Total Itens", self.stats_data.get("total_items", 0)).grid(row=0, column=0, sticky="ew", padx=6)
        _metric("⚠️ Itens Críticos", self.stats_data.get("low_stock", 0)).grid(row=0, column=1, sticky="ew", padx=6)
        _metric("📂 Categorias", self.stats_data.get("categories", 0)).grid(row=0, column=2, sticky="ew", padx=6)
        _metric("💰 Valor Estimado", f"{self.stats_data.get('total_value', 0):,.2f}").grid(
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
        ctk.CTkLabel(header, text="🤖 Assistente de Estoque Inteligente",
                     font=self.font_titulo_medio, text_color=_hex_contrast(self.cor_primaria)).grid(
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
            placeholder_text="Converse aqui... (Enter para enviar)",
            fg_color=self.cor_secundaria,
            text_color=self.cor_texto_entry,
            placeholder_text_color=self.cor_placeholder
        )
        self.ai_input.grid(row=0, column=0, sticky="ew", padx=(10, 8), pady=8)
        self.ai_input.bind("<Return>", self.process_ai_query)

        self.btn_send = ctk.CTkButton(
            input_frame, text="Enviar", command=self.process_ai_query,
            fg_color=self.cor_destaque, hover_color=self.cor_hover,
            text_color=self.cor_texto, width=90
        )
        self.btn_send.grid(row=0, column=1, padx=(0, 10))

        self.quick_actions = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        self.quick_actions.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        for i, text in enumerate([
            "Itens críticos",
            "Valor do estoque",
            "Tecidos (metragem)",
            "Sugestões de compra",
            "Itens não movimentados há 30 dias",
        ]):
            btn = ctk.CTkButton(self.quick_actions, text=text, width=1,
                                fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                                text_color=self.cor_texto,
                                command=lambda t=text: self._send_quick(t))
            btn.grid(row=0, column=i, padx=4)

        self.extra_actions = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        self.extra_actions.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        ctk.CTkButton(self.extra_actions, text="🔁 Regenerar", command=self._regenerate_last,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)
        ctk.CTkButton(self.extra_actions, text="💾 Exportar conversa", command=self._export_chat,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)
        ctk.CTkButton(self.extra_actions, text="💡 Sugestões/Perguntas", command=self._open_suggestions_window,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)

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
        self.assistente = EstoqueIA(self.resultados)

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
        }
        termos_livres = [t for t in re.findall(r"[a-z0-9áéíóúãõç_-]+", q) if len(t) >= 3 and t not in stopwords]

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

                    for termo in p["termos_livres"]:
                        filtros.append(
                            "(LOWER(COALESCE(descricao,'')) LIKE %s "
                            "OR LOWER(COALESCE(categoria,'')) LIKE %s "
                            "OR LOWER(COALESCE(localizacao,'')) LIKE %s "
                            "OR LOWER(COALESCE(cor,'')) LIKE %s "
                            "OR LOWER(COALESCE(fornecedor,'')) LIKE %s "
                            "OR LOWER(CAST(codigo AS text)) LIKE %s)"
                        )
                        like_term = f"%{termo}%"
                        params.extend([like_term, like_term, like_term, like_term, like_term, like_term])

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
                self.assistente = EstoqueIA(self.resultados)
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
                if self.assistente is None:
                    self.assistente = EstoqueIA(self.resultados)
                resposta_banco = self._ai_query_database(text)
                main = resposta_banco or self.assistente.responder(text)
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

    def _short_variations(self, base_text):
        opts = [
            "Quer que eu *exporte* essa lista?",
            "Deseja ver *apenas os críticos*?",
            "Posso *abrir um item* pelo código se preferir.",
            "Gerar *PDF* com esses dados?",
            "Quer que eu *salve* um relatório agora?"
        ]
        random.shuffle(opts)
        return opts[:2]


# ---------- Execução Standalone ----------
if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.title("Controle de Estoque")
    root.geometry("1100x760")

    app = AdvancedStockReport(root)
    app.pack(fill="both", expand=True)

    root.mainloop()

#03/02/2025

# --- Suporte trilíngue individual desta página ---
AdvancedStockReport_TRANSLATIONS = {
    "pt_BR": {
        "title": "Relatórios de Estoque",
        "Atualizar": "Atualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
    },
    "en_US": {
        "title": "Stock Reports",
        "Atualizar": "Refresh",
        "Filtrar": "Filter",
        "Limpar": "Clear",
        "Exportar": "Export",
        "Imprimir": "Print",
        "Buscar": "Search",
    },
    "es_ES": {
        "title": "Reportes de Inventario",
        "Atualizar": "Actualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpiar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
    },
}


def _apply_advancedstockreport_translations(self):
    """Aplica tradução individual desta página."""
    idioma = getattr(getattr(self, "sistema", None), "idioma_atual", getattr(self, "idioma_atual", "pt_BR"))
    if idioma not in AdvancedStockReport_TRANSLATIONS:
        idioma = "pt_BR"
    if hasattr(self, "titulo"):
        try:
            self.titulo.configure(text=AdvancedStockReport_TRANSLATIONS[idioma]["title"])
        except Exception:
            pass


try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    AdvancedStockReport.TRANSLATIONS = AdvancedStockReport_TRANSLATIONS
    if not hasattr(AdvancedStockReport, "apply_page_translations"):
        AdvancedStockReport.apply_page_translations = _apply_advancedstockreport_translations
    attach_i18n_support(AdvancedStockReport, AdvancedStockReport_TRANSLATIONS)
except Exception:
    pass
