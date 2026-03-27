# -*- coding: utf-8 -*-
"""
ESTOQUE_IA.py
Cérebro do assistente de estoque separado do RELATORIO_ESTOQUE.py.
"""

import math
import re
import random
import unicodedata
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from difflib import get_close_matches
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any, Optional

from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db

@dataclass
class FonteEstoque:
    grupo: str
    tabela: str
    unidade_padrao: str
    usa_metros_kilos: bool = False
    familia: str = "geral"


@dataclass
class ConversaContexto:
    grupo: Optional[str] = None
    subgrupo: Optional[str] = None
    categoria: Optional[str] = None
    item_nome: Optional[str] = None
    item_codigo: Optional[str] = None
    cor: Optional[str] = None
    fornecedor: Optional[str] = None
    localizacao: Optional[str] = None
    composicao: Optional[str] = None
    unidade: Optional[str] = None
    quantidade_ref: Optional[float] = None
    comparacao_grupos: List[str] = field(default_factory=list)
    ultimo_intent: Optional[str] = None
    ultimo_top_n: int = 10
    ultimo_limite: Optional[float] = None
    ultimo_filtro: Dict[str, Any] = field(default_factory=dict)
    ultimas_linhas: List[Dict[str, Any]] = field(default_factory=list)
    ultima_pergunta: Optional[str] = None
    ultimos_itens_mapeados: List[str] = field(default_factory=list)
    objetivo_ativo: Optional[str] = None
    objetivo_status: str = "idle"
    proxima_acao_sugerida: Optional[str] = None


class EstoqueIA:
    """
    IA conversacional de estoque para fábrica de roupas.

    Objetivos:
    - Entender perguntas sobre tecidos, aviamentos, insumos, escritório, limpeza e outros.
    - Manter contexto entre perguntas encadeadas.
    - Responder com foco operacional de fábrica.
    - Trabalhar sobre tabelas reais do banco, sem depender de layout fixo.
    - Ser muito mais rica em intenções, exemplos, filtros e continuidade de conversa.
    """

    FONTES: List[FonteEstoque] = [
        FonteEstoque("Tecidos", "estoque_tecidos", "m", True, "textil"),
        FonteEstoque("Aviamentos", "estoque_aviamentos", "un", False, "acabamento"),
        FonteEstoque("Insumos", "estoque_insumos", "un", False, "materia_prima"),
        FonteEstoque("Escritorio", "estoque_escritorio", "un", False, "apoio"),
        FonteEstoque("Limpeza", "estoque_limpeza", "un", False, "apoio"),
        FonteEstoque("Outros", "estoque_outros", "un", False, "geral"),
    ]

    GRUPOS_SINONIMOS: Dict[str, List[str]] = {
        "Tecidos": [
            "tecido", "tecidos", "malha", "malhas", "plano", "planos", "tricoline", "sarja",
            "alfaiataria", "viscose", "linho", "gabardine", "ribana", "moletom", "helanca",
            "crepe", "jeans", "lycra", "suplex", "canelado", "couro sintético", "courino",
            "tule", "neoprene", "microfibra", "moletinho", "dry fit", "dryfit", "ottoman"
        ],
        "Aviamentos": [
            "aviamento", "aviamentos", "linha", "linhas", "botao", "botão", "botoes", "botões",
            "ziper", "zíper", "ziperes", "zíperes", "elastico", "elástico", "velcro", "agulha",
            "etiqueta", "etiquetas", "rebite", "ilhos", "ilhós", "passante", "passantes",
            "fivela", "viés", "vies", "cursor", "entretela", "ombreira", "cordao", "cordão",
            "renda", "fita", "fita gorgurão", "gorgurao", "gorgurão"
        ],
        "Insumos": [
            "insumo", "insumos", "matéria prima", "materia prima", "matérias primas", "materias primas",
            "cola", "espuma", "embalagem", "embalagens", "saco", "sacos", "caixa", "caixas",
            "papelao", "papelão", "plastico", "plástico", "filme stretch", "etiqueta adesiva",
            "tag", "tags", "cabide", "cabides", "saquinho", "envelope", "adesivo"
        ],
        "Escritorio": [
            "escritorio", "escritório", "papel", "resma", "resmas", "caneta", "canetas", "lapis",
            "lápis", "toner", "cartucho", "pasta", "pastas", "grampo", "grampeador", "clipe",
            "clips", "clipes", "bloco", "post-it", "post it", "caderno", "agenda", "a4"
        ],
        "Limpeza": [
            "limpeza", "detergente", "sabao", "sabão", "cloro", "desinfetante", "alcool", "álcool",
            "pano", "panos", "rodo", "vassoura", "luva", "luvas", "papel toalha", "papel higiênico",
            "papel higienico", "saco de lixo", "sacos de lixo", "amaciante", "desengordurante"
        ],
        "Outros": ["outro", "outros", "diversos", "gerais", "avulso", "avulsos", "misc", "miscelanea"],
    }

    CORES_BASE = [
        "preto", "branco", "azul", "azul marinho", "vermelho", "verde", "amarelo", "rosa", "roxo",
        "bege", "off white", "cinza", "grafite", "marrom", "caramelo", "nude", "lilás", "lilas",
        "vinho", "bordo", "bordô", "laranja", "turquesa", "caqui", "areia", "prata", "dourado"
    ]

    COMPOSICOES_BASE = [
        "algodao", "algodão", "poliester", "poliéster", "viscose", "elastano", "poliamida",
        "acrilico", "acrílico", "linho", "la", "lã", "rayon", "pu", "pvc", "microfibra"
    ]

    PALAVRAS_ACAO = {
        "listar": {"listar", "liste", "mostre", "mostrar", "exiba", "ver", "quais", "quais sao", "quais são"},
        "contar": {"quantos", "quantas", "contagem", "total", "qtd", "quantidade", "numero", "número"},
        "top": {"top", "maiores", "mais", "principal", "principais", "lider", "líder", "lideres", "líderes"},
        "baixo": {"baixo", "baixa", "baixos", "baixas", "critico", "crítico", "criticos", "críticos", "repor", "faltando", "acabando"},
        "comparar": {"compare", "comparar", "comparativo", "diferença", "diferenca", "versus", "vs"},
        "detalhar": {"detalhe", "resuma", "resumo", "ficha", "detalhes", "complete", "completo", "perfil"},
        "onde": {"onde", "local", "localizacao", "localização", "guardado", "guardada", "deposito", "depósito", "setor", "prateleira"},
        "fornecedor": {"fornecedor", "fornecedores", "fornece", "compramos", "comprado", "origem", "marca", "fabricante"},
        "cores": {"cor", "cores", "tons", "coloracao", "coloração", "variação de cor", "variacao de cor"},
        "codigo": {"codigo", "código", "cod", "sku", "referencia", "referência"},
        "composicao": {"composicao", "composição", "material", "materiais", "composto", "composta"},
        "recente": {"recente", "recentes", "ultimos", "últimos", "últimas", "novos", "novidades", "entraram por ultimo", "entraram por último"},
        "zero": {"saldo zero", "zerado", "zerados", "sem saldo", "acabou", "esgotado", "esgotados"},
        "faixa": {"abaixo de", "acima de", "menor que", "maior que", "entre", "faixa", "intervalo"},
        "diversidade": {"tipos", "variedades", "variedade", "cores diferentes", "codigos distintos", "códigos distintos"},
        "cobertura": {"quanto dura", "dias de estoque", "cobertura", "autonomia", "suficiencia", "suficiência"},
        "consumo": {"consumo", "gasto", "uso", "utilizacao", "utilização", "saida", "saída"},
        "risco": {"risco", "criticidade", "classificacao de risco", "classificação de risco", "saude do estoque", "saúde do estoque"},
        "sugestao_compra": {"sugestao de compra", "sugestão de compra", "comprar", "repor", "reposicao", "reposição"},
        "distribuicao": {"distribuicao", "distribuição", "participacao", "participação", "share", "mix"},
        "projecao": {"projecao", "projeção", "previsao", "previsão", "forecast", "simulacao", "simulação"},
        "abc": {"curva abc", "analise abc", "análise abc", "pareto", "classe a", "classe b", "classe c"},
        "memoria": {"resumo da conversa", "memoria", "memória", "o que ja falamos", "o que já falamos", "retomar contexto"},
    }

    CONTINUACOES = {
        "e quais", "e quais sao", "e quais são", "quais são", "quais sao", "e onde", "e quem fornece",
        "e as cores", "e os fornecedores", "e as localizações", "desse", "dessa", "desse item", "desse tecido",
        "dele", "dela", "deles", "desses", "dessas", "esses", "essas", "esse", "essa", "do mesmo", "da mesma"
    }

    INTENTOS_PRIORITARIOS = [
        "saudacao", "ajuda", "listar_grupo", "contar_grupo", "listar_itens", "detalhar_item", "listar_cores",
        "contar_cores", "listar_fornecedores", "listar_locais", "saldo_item", "codigo_item", "itens_criticos",
        "itens_zerados", "itens_abaixo", "itens_acima", "itens_entre", "top_saldo", "top_variedade",
        "itens_por_cor", "itens_por_fornecedor", "itens_por_local", "itens_por_composicao", "comparar_grupos",
        "resumo_grupo", "resumo_geral", "listar_todos_itens", "itens_por_setor_detalhado",
        "itens_recentes", "contar_codigos", "contar_itens_distintos",
        "distribuicao_cores", "distribuicao_fornecedores", "distribuicao_locais", "consultar_cobertura",
        "consultar_consumo", "sugestao_compra", "analise_risco", "projecao_consumo",
        "analise_abc", "resumo_memoria", "workflow_estoque", "resposta_contextual"
    ]

    def __init__(self, resultados=None):
        self.resultados = resultados or []
        self.ctx_historico: List[Tuple[str, str]] = []
        self.contexto = ConversaContexto()
        self.last_intent: Optional[str] = None
        self.last_entities: Dict[str, Any] = {}
        self._sources_cache: Optional[List[Dict[str, Any]]] = None
        self._dialogos_cache: Optional[List[Dict[str, str]]] = None
        self.memoria_consultas: List[Dict[str, Any]] = []
        self.max_memoria_consultas = 120
        self.metricas = {
            "total_consultas": 0,
            "fallbacks": 0,
            "por_intent": Counter(),
        }
        self._carregar_memoria_persistente()

    # =========================================================
    # COMPATIBILIDADE / INTERFACE PÚBLICA
    # =========================================================
    def _remember(self, who: str, text: str) -> None:
        self.ctx_historico.append((who, text))
        if len(self.ctx_historico) > 50:
            self.ctx_historico = self.ctx_historico[-50:]

    def _intent_score(self, pergunta: str) -> Tuple[Optional[str], float]:
        return self._detect_intent(pergunta)

    def _help_text(self, page: int = 1) -> str:
        exemplos = self.gerar_catalogo_dialogos()[:96]
        por_pagina = 12
        total_pages = max(1, math.ceil(len(exemplos) / por_pagina))
        page = max(1, min(page, total_pages))
        ini = (page - 1) * por_pagina
        fim = ini + por_pagina
        linhas = [
            "Posso conversar sobre o estoque real da fábrica com contexto.",
            "",
            "Exemplos de perguntas:",
        ]
        for bloco in exemplos[ini:fim]:
            linhas.append(f"- {bloco['pergunta']}")
        linhas.append("")
        linhas.append(f"Página {page}/{total_pages}")
        linhas.append("Use ajuda 2, ajuda 3, ajuda 4... para ver mais exemplos.")
        return "\n".join(linhas)

    def responder(self, pergunta: str) -> str:
        pergunta = self._safe_text(pergunta)
        self._remember("usuario", pergunta)
        self.contexto.ultima_pergunta = pergunta
        self.metricas["total_consultas"] += 1

        if not pergunta:
            resposta = "Escreva sua pergunta sobre o estoque. Exemplo: quais tecidos temos ou quais aviamentos estão críticos."
            self._remember("ia", resposta)
            return resposta

        normal = self._normalize(pergunta)

        pagina_help = self._extract_help_page(normal)
        if self._is_help(normal):
            resposta = self._help_text(pagina_help)
            self._remember("ia", resposta)
            return resposta

        entidades = self._extract_entities(pergunta)
        if entidades.get("confirmacao") or entidades.get("negacao"):
            resposta = self._responder_confirmacao(entidades)
            self._registrar_memoria_consulta("confirmacao", entidades, resposta)
            self._remember("ia", resposta)
            return resposta

        intent, score = self._detect_intent(pergunta, entidades)
        self.last_intent = intent
        self.last_entities = entidades
        self.metricas["por_intent"][intent or "indefinido"] += 1
        self._update_context(entidades, intent)
        self._atualizar_objetivo_ativo(intent, entidades)

        resposta = self._dispatch(intent, pergunta, normal, entidades)
        if not resposta:
            resposta = self._fallback_conversacional(pergunta, entidades, intent, score)
            self.metricas["fallbacks"] += 1

        resposta = self._enriquecer_resposta_estruturada(intent, entidades, resposta)
        self._sugerir_proxima_acao(intent, entidades, resposta)

        self._registrar_memoria_consulta(intent, entidades, resposta)
        self._remember("ia", resposta)
        return resposta

    # =========================================================
    # BASES TEXTUAIS / AJUDA / EXEMPLOS
    # =========================================================
    def gerar_catalogo_dialogos(self) -> List[Dict[str, str]]:
        if self._dialogos_cache is not None:
            return self._dialogos_cache

        grupos = ["tecidos", "aviamentos", "insumos", "materiais de escritório", "limpeza", "outros"]
        acoes = [
            "quais {g} temos",
            "liste os {g} com quantidade",
            "quantos {g} temos cadastrados",
            "quais {g} estão críticos",
            "quais {g} estão zerados",
            "quais {g} têm maior saldo",
            "quais {g} entraram por último",
            "quais fornecedores temos em {g}",
            "quais localizações existem em {g}",
            "quantos códigos distintos temos em {g}",
            "quais {g} pretos temos",
            "quais {g} brancos temos",
            "quais {g} do fornecedor alfa temos",
            "quais {g} do depósito a temos",
            "quais {g} com composição algodão temos",
            "qual é o resumo de {g}",
        ]

        itens = [
            "alfaiataria", "tricoline", "sarja", "zíper invisível", "linha 120", "botão 18",
            "elástico chato", "cola spray", "resma a4", "álcool 70", "papel toalha", "cabide preto"
        ]
        followups = [
            "quantas cores temos no item {i}",
            "quais são as cores do item {i}",
            "quem fornece {i}",
            "onde está guardado {i}",
            "qual é o código de {i}",
            "qual é o saldo de {i}",
            "me dê o resumo completo de {i}",
            "esse item está crítico",
            "quais localizações existem para {i}",
            "quais fornecedores aparecem em {i}",
        ]

        catalogo: List[Dict[str, str]] = []
        for g in grupos:
            for acao in acoes:
                pergunta = acao.format(g=g)
                catalogo.append({
                    "pergunta": pergunta,
                    "resposta": f"Consulta contextual sobre {g}, listando dados reais do banco conforme o filtro solicitado."
                })
        for i in itens:
            for acao in followups:
                catalogo.append({
                    "pergunta": acao.format(i=i),
                    "resposta": f"Consulta detalhada do item {i}, aproveitando contexto da conversa e retornando dados reais."
                })

        encadeados = []
        for g in grupos:
            for i in itens:
                encadeados.extend([
                    f"quais {g} temos",
                    f"e quais estão críticos",
                    f"e quais são do item {i}",
                    f"quantas cores temos no item {i}",
                    f"quem fornece {i}",
                    f"onde está guardado {i}",
                    f"quero o resumo do item {i}",
                ])
        for p in encadeados:
            catalogo.append({"pergunta": p, "resposta": "Fluxo de conversa encadeado com reaproveitamento do grupo e do item em contexto."})

        self._dialogos_cache = catalogo
        return catalogo

    # =========================================================
    # NORMALIZAÇÃO E EXTRAÇÃO DE ENTIDADES
    # =========================================================
    def _normalize(self, text: str) -> str:
        text = (text or "").strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.replace("/", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _safe_text(self, value: Any) -> str:
        return "" if value is None else str(value).strip()

    def _safe_float(self, value: Any) -> float:
        try:
            if value in (None, ""):
                return 0.0
            return float(str(value).replace(".", "").replace(",", ".")) if isinstance(value, str) and value.count(",") == 1 and value.count(".") > 1 else float(str(value).replace(",", "."))
        except Exception:
            return 0.0

    def _extract_help_page(self, normal: str) -> int:
        m = re.search(r"\bajuda\s+(\d+)\b", normal)
        return int(m.group(1)) if m else 1

    def _is_help(self, normal: str) -> bool:
        return normal in {"ajuda", "socorro", "comandos", "exemplos", "o que voce faz", "o que você faz"} or normal.startswith("ajuda ")

    def _extract_entities(self, pergunta: str) -> Dict[str, Any]:
        original = self._safe_text(pergunta)
        normal = self._normalize(original)

        entities: Dict[str, Any] = {
            "texto_original": original,
            "texto_normalizado": normal,
            "grupo": self._extract_group(normal),
            "grupos_mencionados": self._extract_multiple_groups(normal),
            "cor": self._extract_color(normal),
            "fornecedor": self._extract_after_keywords(normal, ["fornecedor", "fornecedores", "marca", "fabricante", "compramos de"]),
            "localizacao": self._extract_after_keywords(normal, ["depósito", "deposito", "setor", "prateleira", "local", "localização", "localizacao"]),
            "composicao": self._extract_composition(normal),
            "codigo": self._extract_code(normal),
            "numero": self._extract_number(normal),
            "faixa": self._extract_range(normal),
            "item_nome": self._extract_item_name(original, normal),
            "continuidade": self._is_continuation(normal),
            "saudacao": self._is_greeting(normal),
            "comparacao": self._has_any(normal, self.PALAVRAS_ACAO["comparar"]),
            "escopo_global": self._is_global_scope_request(normal),
            "confirmacao": normal in {"sim", "ok", "confirmo", "pode", "pode sim", "isso", "segue", "continue"},
            "negacao": normal in {"nao", "não", "agora nao", "agora não", "cancelar", "pare"},
            "perfil_detalhado": any(t in normal for t in ("detalhado", "detalhe", "completo", "analitico", "analítico")),
        }
        return entities

    def _is_global_scope_request(self, normal: str) -> bool:
        gatilhos = (
            "todos os itens", "tudo do estoque", "estoque completo", "inventario completo", "inventário completo",
            "lista completa", "quero tudo", "quero todos", "mostrar tudo"
        )
        return any(g in normal for g in gatilhos)

    def _extract_group(self, normal: str) -> Optional[str]:
        for grupo, termos in self.GRUPOS_SINONIMOS.items():
            for termo in termos:
                if re.search(rf"\b{re.escape(self._normalize(termo))}\b", normal):
                    return grupo
        if self.contexto.grupo and self._is_continuation(normal):
            return self.contexto.grupo
        return None

    def _extract_multiple_groups(self, normal: str) -> List[str]:
        grupos = []
        for grupo, termos in self.GRUPOS_SINONIMOS.items():
            if any(re.search(rf"\b{re.escape(self._normalize(t))}\b", normal) for t in termos):
                grupos.append(grupo)
        return list(dict.fromkeys(grupos))

    def _extract_color(self, normal: str) -> Optional[str]:
        for cor in sorted(self.CORES_BASE, key=len, reverse=True):
            if re.search(rf"\b{re.escape(self._normalize(cor))}\b", normal):
                return cor
        m = re.search(r"\bcor\s+([a-z0-9 _-]{2,40})$", normal)
        if m:
            return m.group(1).strip()
        return self.contexto.cor if self._is_continuation(normal) else None

    def _extract_composition(self, normal: str) -> Optional[str]:
        for comp in sorted(self.COMPOSICOES_BASE, key=len, reverse=True):
            if re.search(rf"\b{re.escape(self._normalize(comp))}\b", normal):
                return comp
        for chave in ["composicao", "composição", "material", "materiais"]:
            m = re.search(rf"\b{self._normalize(chave)}\b\s+(?:de\s+)?([a-z0-9 %/_-]{{2,50}})", normal)
            if m:
                return m.group(1).strip()
        return self.contexto.composicao if self._is_continuation(normal) else None

    def _extract_after_keywords(self, normal: str, keywords: List[str]) -> Optional[str]:
        for kw in keywords:
            kw_n = self._normalize(kw)
            m = re.search(rf"\b{re.escape(kw_n)}\b\s+(?:do|da|de|dos|das)?\s*([a-z0-9 _./-]{{2,60}})", normal)
            if m:
                trecho = m.group(1).strip()
                trecho = re.split(r"\b(temos|tem|ha|há|com|que|onde|quem|qual|quais)\b", trecho)[0].strip()
                if trecho:
                    return trecho
        return None

    def _extract_code(self, normal: str) -> Optional[str]:
        m = re.search(r"\b(?:codigo|código|cod|sku|referencia|referência)\b\s*[:#-]?\s*([a-z0-9._/-]{2,40})", normal)
        if m:
            return m.group(1).strip()
        m2 = re.search(r"\b([a-z]{1,5}-?\d{2,})\b", normal)
        if m2:
            return m2.group(1).strip()
        return self.contexto.item_codigo if self._is_continuation(normal) else None

    def _extract_number(self, normal: str) -> Optional[float]:
        m = re.search(r"\b(\d+[\.,]?\d*)\b", normal)
        if not m:
            return None
        try:
            return float(m.group(1).replace(",", "."))
        except Exception:
            return None

    def _extract_range(self, normal: str) -> Dict[str, Optional[float]]:
        faixa = {"tipo": None, "min": None, "max": None}
        m_entre = re.search(r"\bentre\s+(\d+[\.,]?\d*)\s+e\s+(\d+[\.,]?\d*)", normal)
        if m_entre:
            faixa["tipo"] = "entre"
            faixa["min"] = float(m_entre.group(1).replace(",", "."))
            faixa["max"] = float(m_entre.group(2).replace(",", "."))
            return faixa
        m_abaixo = re.search(r"\b(?:abaixo de|menor que|menos de)\s+(\d+[\.,]?\d*)", normal)
        if m_abaixo:
            faixa["tipo"] = "abaixo"
            faixa["max"] = float(m_abaixo.group(1).replace(",", "."))
            return faixa
        m_acima = re.search(r"\b(?:acima de|maior que|mais de)\s+(\d+[\.,]?\d*)", normal)
        if m_acima:
            faixa["tipo"] = "acima"
            faixa["min"] = float(m_acima.group(1).replace(",", "."))
            return faixa
        return faixa

    def _extract_item_name(self, original: str, normal: str) -> Optional[str]:
        patterns = [
            r"(?:tecido|aviamento|insumo|item|produto|material)\s+([a-z0-9 _./-]{2,60})",
            r"(?:do|da|de)\s+([a-z0-9 _./-]{2,60})$",
            r"(?:resumo de|detalhes de|saldo de|codigo de|código de|fornecedor de|onde esta|onde está)\s+([a-z0-9 _./-]{2,60})",
        ]
        for pat in patterns:
            m = re.search(pat, normal)
            if m:
                nome = m.group(1).strip(" .:-")
                nome = re.split(r"\b(com|do fornecedor|na cor|de cor|no deposito|no depósito|composicao|composição)\b", nome)[0].strip()
                if nome and len(nome) >= 2:
                    return nome
        if self._is_continuation(normal) and self.contexto.item_nome:
            return self.contexto.item_nome
        return None

    def _is_continuation(self, normal: str) -> bool:
        return any(exp in normal for exp in self.CONTINUACOES) or normal in {"e", "continua", "continue"}

    def _is_greeting(self, normal: str) -> bool:
        return normal in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "opa", "e ai", "e aí"}

    def _has_any(self, normal: str, words: set) -> bool:
        for w in words:
            if self._normalize(w) in normal:
                return True
        return False

    # =========================================================
    # DETECÇÃO DE INTENÇÃO
    # =========================================================
    def _detect_intent(self, pergunta: str, entidades: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], float]:
        entidades = entidades or self._extract_entities(pergunta)
        normal = entidades["texto_normalizado"]
        grupo = entidades.get("grupo")
        item = entidades.get("item_nome")
        codigo = entidades.get("codigo")
        faixa = entidades.get("faixa") or {}

        if entidades.get("saudacao"):
            return "saudacao", 1.0

        if self._is_help(normal):
            return "ajuda", 1.0

        if entidades.get("comparacao") and len(entidades.get("grupos_mencionados") or []) >= 2:
            return "comparar_grupos", 0.98

        if self._has_any(normal, self.PALAVRAS_ACAO["cobertura"]):
            return "consultar_cobertura", 0.94

        if self._has_any(normal, self.PALAVRAS_ACAO["consumo"]):
            return "consultar_consumo", 0.93

        if self._has_any(normal, self.PALAVRAS_ACAO["projecao"]):
            return "projecao_consumo", 0.93

        if self._has_any(normal, self.PALAVRAS_ACAO["abc"]):
            return "analise_abc", 0.93

        if self._has_any(normal, self.PALAVRAS_ACAO["risco"]):
            return "analise_risco", 0.92

        if self._has_any(normal, self.PALAVRAS_ACAO["memoria"]):
            return "resumo_memoria", 0.92

        if any(k in normal for k in ("diagnostico completo", "diagnóstico completo", "auditoria de estoque", "plano de reposicao", "plano de reposição")):
            return "workflow_estoque", 0.96

        if ("setor" in normal or "localizacao" in normal or "localização" in normal) and (
            "cada setor" in normal or "por setor" in normal or "quantos itens" in normal or "seus nomes" in normal
        ):
            return "itens_por_setor_detalhado", 0.95

        if entidades.get("escopo_global") and (self._has_any(normal, self.PALAVRAS_ACAO["listar"]) or "itens" in normal):
            return "listar_todos_itens", 0.95

        if self._has_any(normal, self.PALAVRAS_ACAO["recente"]):
            return "itens_recentes", 0.95

        if self._has_any(normal, self.PALAVRAS_ACAO["baixo"]):
            if faixa.get("tipo") == "abaixo":
                return "itens_abaixo", 0.97
            return "itens_criticos", 0.96

        if self._has_any(normal, self.PALAVRAS_ACAO["zero"]):
            return "itens_zerados", 0.96

        if faixa.get("tipo") == "entre":
            return "itens_entre", 0.96
        if faixa.get("tipo") == "acima":
            return "itens_acima", 0.96
        if faixa.get("tipo") == "abaixo":
            return "itens_abaixo", 0.96

        if self._has_any(normal, self.PALAVRAS_ACAO["cores"]):
            if self._has_any(normal, self.PALAVRAS_ACAO["contar"]):
                return "contar_cores", 0.98
            return "listar_cores", 0.98

        if self._has_any(normal, self.PALAVRAS_ACAO["fornecedor"]):
            if item or codigo:
                return "listar_fornecedores", 0.97
            return "distribuicao_fornecedores", 0.90

        if self._has_any(normal, self.PALAVRAS_ACAO["distribuicao"]) and self._has_any(normal, self.PALAVRAS_ACAO["cores"]):
            return "distribuicao_cores", 0.92

        if self._has_any(normal, self.PALAVRAS_ACAO["distribuicao"]) and self._has_any(normal, self.PALAVRAS_ACAO["onde"]):
            return "distribuicao_locais", 0.92

        if self._has_any(normal, self.PALAVRAS_ACAO["onde"]):
            return "listar_locais", 0.97

        if self._has_any(normal, self.PALAVRAS_ACAO["codigo"]):
            if item or codigo:
                return "codigo_item", 0.97
            return "contar_codigos", 0.91

        if self._has_any(normal, self.PALAVRAS_ACAO["composicao"]):
            if item or entidades.get("composicao"):
                return "itens_por_composicao", 0.96

        if self._has_any(normal, self.PALAVRAS_ACAO["detalhar"]):
            return "detalhar_item", 0.97 if item or codigo else 0.90

        if self._has_any(normal, self.PALAVRAS_ACAO["top"]):
            if self._has_any(normal, self.PALAVRAS_ACAO["cores"]) or "variedade" in normal:
                return "top_variedade", 0.94
            return "top_saldo", 0.95

        if self._has_any(normal, self.PALAVRAS_ACAO["sugestao_compra"]):
            return "sugestao_compra", 0.93

        if entidades.get("cor") and (grupo or item or entidades.get("continuidade")):
            return "itens_por_cor", 0.95

        if entidades.get("fornecedor"):
            return "itens_por_fornecedor", 0.94

        if entidades.get("localizacao"):
            return "itens_por_local", 0.94

        if self._has_any(normal, self.PALAVRAS_ACAO["contar"]):
            if "codigo" in normal or "sku" in normal or "referencia" in normal or "referência" in normal:
                return "contar_codigos", 0.95
            if grupo:
                return "contar_grupo", 0.94
            return "contar_itens_distintos", 0.90

        if grupo and self._has_any(normal, self.PALAVRAS_ACAO["listar"]):
            return "listar_grupo", 0.95

        if item or codigo:
            if "saldo" in normal or "quantidade" in normal or "qtd" in normal:
                return "saldo_item", 0.96
            return "detalhar_item", 0.90

        if grupo:
            return "resumo_grupo", 0.82

        if entidades.get("continuidade") and self.contexto.ultimo_intent:
            return "resposta_contextual", 0.80

        return "resumo_geral", 0.60

    # =========================================================
    # CONTEXTO
    # =========================================================
    def _update_context(self, entidades: Dict[str, Any], intent: Optional[str]) -> None:
        grupo = entidades.get("grupo")
        if grupo:
            self.contexto.grupo = grupo
        if entidades.get("item_nome"):
            self.contexto.item_nome = entidades["item_nome"]
        if entidades.get("codigo"):
            self.contexto.item_codigo = entidades["codigo"]
        if entidades.get("cor"):
            self.contexto.cor = entidades["cor"]
        if entidades.get("fornecedor"):
            self.contexto.fornecedor = entidades["fornecedor"]
        if entidades.get("localizacao"):
            self.contexto.localizacao = entidades["localizacao"]
        if entidades.get("composicao"):
            self.contexto.composicao = entidades["composicao"]
        grupos = entidades.get("grupos_mencionados") or []
        if len(grupos) >= 2:
            self.contexto.comparacao_grupos = grupos
        num = entidades.get("numero")
        if isinstance(num, (int, float)):
            self.contexto.quantidade_ref = float(num)
        if entidades.get("faixa", {}).get("max") is not None:
            self.contexto.ultimo_limite = entidades["faixa"]["max"]
        if entidades.get("faixa", {}).get("min") is not None and entidades["faixa"].get("tipo") == "acima":
            self.contexto.ultimo_limite = entidades["faixa"]["min"]
        if entidades.get("escopo_global"):
            self.contexto.item_nome = None
            self.contexto.item_codigo = None
            self.contexto.cor = None
            self.contexto.fornecedor = None
            self.contexto.localizacao = None
            self.contexto.composicao = None
        self.contexto.ultimo_intent = intent

    def _registrar_memoria_consulta(self, intent: Optional[str], entidades: Dict[str, Any], resposta: str) -> None:
        """
        Mantém memória operacional da conversa para melhorar continuidade.
        """
        if not intent:
            return
        snapshot = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "intent": intent,
            "grupo": entidades.get("grupo") or self.contexto.grupo,
            "item_nome": entidades.get("item_nome") or self.contexto.item_nome,
            "codigo": entidades.get("codigo") or self.contexto.item_codigo,
            "cor": entidades.get("cor") or self.contexto.cor,
            "fornecedor": entidades.get("fornecedor") or self.contexto.fornecedor,
            "resposta_preview": self._safe_text(resposta).split("\n")[0][:160],
        }
        self.memoria_consultas.append(snapshot)
        if len(self.memoria_consultas) > self.max_memoria_consultas:
            self.memoria_consultas = self.memoria_consultas[-self.max_memoria_consultas:]
        self._persistir_memoria_persistente(snapshot)

    def _garantir_tabela_memoria(self) -> None:
        schema = db.get_schema()
        db.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema}.ia_memoria_estoque (
                id BIGSERIAL PRIMARY KEY,
                criado_em TIMESTAMP DEFAULT NOW(),
                intent TEXT,
                grupo TEXT,
                item_nome TEXT,
                codigo TEXT,
                cor TEXT,
                fornecedor TEXT,
                resposta_preview TEXT
            )
        """)

    def _persistir_memoria_persistente(self, snapshot: Dict[str, Any]) -> None:
        try:
            self._garantir_tabela_memoria()
            schema = db.get_schema()
            db.execute(
                f"""INSERT INTO {schema}.ia_memoria_estoque
                (intent, grupo, item_nome, codigo, cor, fornecedor, resposta_preview)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                [
                    snapshot.get("intent"), snapshot.get("grupo"), snapshot.get("item_nome"),
                    snapshot.get("codigo"), snapshot.get("cor"), snapshot.get("fornecedor"),
                    snapshot.get("resposta_preview"),
                ],
            )
        except Exception:
            pass

    def _carregar_memoria_persistente(self) -> None:
        try:
            self._garantir_tabela_memoria()
            schema = db.get_schema()
            rows = db.fetch_all(
                f"""SELECT criado_em, intent, grupo, item_nome, codigo, cor, fornecedor, resposta_preview
                    FROM {schema}.ia_memoria_estoque
                    ORDER BY id DESC
                    LIMIT 30"""
            ) or []
            for r in reversed(rows):
                self.memoria_consultas.append({
                    "ts": self._safe_text(r.get("criado_em")),
                    "intent": self._safe_text(r.get("intent")),
                    "grupo": self._safe_text(r.get("grupo")),
                    "item_nome": self._safe_text(r.get("item_nome")),
                    "codigo": self._safe_text(r.get("codigo")),
                    "cor": self._safe_text(r.get("cor")),
                    "fornecedor": self._safe_text(r.get("fornecedor")),
                    "resposta_preview": self._safe_text(r.get("resposta_preview")),
                })
            if len(self.memoria_consultas) > self.max_memoria_consultas:
                self.memoria_consultas = self.memoria_consultas[-self.max_memoria_consultas:]
        except Exception:
            pass

    def _atualizar_objetivo_ativo(self, intent: Optional[str], entidades: Dict[str, Any]) -> None:
        if entidades.get("escopo_global"):
            self.contexto.objetivo_ativo = "inventario_global"
            self.contexto.objetivo_status = "coletando"
            return
        mapa = {
            "itens_por_setor_detalhado": "analise_setores",
            "analise_risco": "mitigar_risco",
            "sugestao_compra": "planejar_reposicao",
            "analise_abc": "classificacao_curva_abc",
            "projecao_consumo": "projecao_consumo",
            "listar_todos_itens": "inventario_global",
        }
        if intent in mapa:
            self.contexto.objetivo_ativo = mapa[intent]
            self.contexto.objetivo_status = "em_execucao"

    def _responder_confirmacao(self, entidades: Dict[str, Any]) -> str:
        if entidades.get("negacao"):
            self.contexto.proxima_acao_sugerida = None
            self.contexto.objetivo_status = "aguardando_novo_pedido"
            return "Perfeito, cancelei a ação pendente. Me diga o próximo objetivo (ex.: setores, críticos, ABC ou projeção)."
        acao = self.contexto.proxima_acao_sugerida
        if not acao:
            return "Recebi o 'sim'. Se quiser, diga a ação: gerar pdf, listar críticos, inventário completo ou itens por setor."
        mapa = {
            "listar_criticos": "itens_criticos",
            "inventario_completo": "listar_todos_itens",
            "por_setor": "itens_por_setor_detalhado",
            "analise_risco": "analise_risco",
        }
        intent = mapa.get(acao)
        if not intent:
            return "Confirmação recebida, mas não encontrei ação pendente válida. Diga novamente a operação desejada."
        self.contexto.proxima_acao_sugerida = None
        self.contexto.objetivo_status = "confirmado"
        return self._dispatch(intent, "", "", {"escopo_global": True, "grupo": self.contexto.grupo})

    def _sugerir_proxima_acao(self, intent: Optional[str], entidades: Dict[str, Any], resposta: str) -> None:
        if intent in {"resumo_geral", "resumo_grupo"}:
            self.contexto.proxima_acao_sugerida = "listar_criticos"
        elif intent in {"itens_criticos", "analise_risco"}:
            self.contexto.proxima_acao_sugerida = "inventario_completo"
        elif intent in {"listar_todos_itens", "itens_por_setor_detalhado"}:
            self.contexto.proxima_acao_sugerida = "analise_risco"
        elif intent == "sugestao_compra":
            self.contexto.proxima_acao_sugerida = "por_setor"

    def _enriquecer_resposta_estruturada(self, intent: Optional[str], entidades: Dict[str, Any], resposta: str) -> str:
        if not resposta:
            return resposta
        if intent not in {
            "analise_risco", "sugestao_compra", "projecao_consumo",
            "analise_abc", "itens_por_setor_detalhado", "listar_todos_itens", "resumo_geral", "resumo_grupo"
        }:
            return resposta
        objetivo = self.contexto.objetivo_ativo or "consulta_estoque"
        perfil = "detalhado" if entidades.get("perfil_detalhado") else "operacional"
        proxima = self.contexto.proxima_acao_sugerida or "listar_criticos"
        return (
            f"OBJETIVO: {objetivo} ({perfil})\n"
            f"STATUS: {self.contexto.objetivo_status}\n\n"
            f"{resposta}\n\n"
            f"PRÓXIMO PASSO SUGERIDO: {proxima} (responda 'sim' para executar)"
        )

    # =========================================================
    # ACESSO AO BANCO / DESCOBERTA DE COLUNAS
    # =========================================================
    def _list_column_names(self, table: str) -> List[str]:
        try:
            cols = db.list_columns(table)
            saida = []
            for c in cols or []:
                nome = c.get("column_name") if isinstance(c, dict) else None
                if nome:
                    saida.append(str(nome).lower())
            return saida
        except Exception:
            return []

    def _choose_col(self, cols: List[str], candidates: List[str]) -> Optional[str]:
        for cand in candidates:
            if cand.lower() in cols:
                return cand.lower()
        return None

    def _sql_expr(self, col: Optional[str], fallback_sql: str) -> str:
        return col if col else fallback_sql

    def _get_sources(self) -> List[Dict[str, Any]]:
        if self._sources_cache is not None:
            return self._sources_cache

        fontes = []
        for fonte in self.FONTES:
            try:
                if not db.table_exists(fonte.tabela):
                    continue
            except Exception:
                continue
            cols = self._list_column_names(fonte.tabela)
            if not cols:
                continue
            fontes.append({
                "grupo": fonte.grupo,
                "familia": fonte.familia,
                "tabela": fonte.tabela,
                "cols": cols,
                "codigo_col": self._choose_col(cols, ["codigo", "cod", "codigo_item", "sku", "referencia"]),
                "descricao_col": self._choose_col(cols, ["descricao", "nome", "item", "produto", "descricao_item"]),
                "subgrupo_col": self._choose_col(cols, ["grupo", "subgrupo", "linha", "tipo"]),
                "categoria_col": self._choose_col(cols, ["categoria", "classe", "segmento"]),
                "cor_col": self._choose_col(cols, ["cor", "cor_nome"]),
                "fornecedor_col": self._choose_col(cols, ["fornecedor", "marca", "fabricante"]),
                "localizacao_col": self._choose_col(cols, ["localizacao", "localização", "local", "deposito", "depósito", "setor", "prateleira"]),
                "composicao_col": self._choose_col(cols, ["composicao", "composição", "material", "materiais"]),
                "unidade_col": self._choose_col(cols, ["unidade", "un_medida", "medida"]),
                "quantidade_col": self._choose_col(cols, ["quantidade", "qtd", "saldo", "estoque_atual", "saldo_atual"]),
                "metros_col": self._choose_col(cols, ["metros", "metragem", "metro"]),
                "kilos_col": self._choose_col(cols, ["kilos", "kg", "peso"]),
                "largura_col": self._choose_col(cols, ["largura"]),
                "gramatura_col": self._choose_col(cols, ["gramatura"]),
                "estoque_minimo_col": self._choose_col(cols, ["estoque_minimo", "minimo", "mínimo"]),
                "estoque_ideal_col": self._choose_col(cols, ["estoque_ideal", "ideal"]),
                "consumo_medio_col": self._choose_col(cols, ["consumo_medio", "media_consumo", "consumo"]),
                "data_col": self._choose_col(cols, ["data_entrada", "data", "created_at", "updated_at", "atualizado_em"]),
                "obs_col": self._choose_col(cols, ["obs", "observacao", "observações", "observacoes"]),
                "usa_metros_kilos": fonte.usa_metros_kilos,
                "unidade_padrao": fonte.unidade_padrao,
            })
        self._sources_cache = fontes
        return fontes

    def _build_union_query(self) -> str:
        partes = []
        for s in self._get_sources():
            codigo = self._sql_expr(s["codigo_col"], "NULL::text")
            descricao = self._sql_expr(s["descricao_col"], "NULL::text")
            subgrupo = self._sql_expr(s["subgrupo_col"], "NULL::text")
            categoria = self._sql_expr(s["categoria_col"], "NULL::text")
            cor = self._sql_expr(s["cor_col"], "NULL::text")
            fornecedor = self._sql_expr(s["fornecedor_col"], "NULL::text")
            localizacao = self._sql_expr(s["localizacao_col"], "NULL::text")
            composicao = self._sql_expr(s["composicao_col"], "NULL::text")
            largura = self._sql_expr(s["largura_col"], "NULL::text")
            gramatura = self._sql_expr(s["gramatura_col"], "NULL::text")
            minimo = self._sql_expr(s["estoque_minimo_col"], "NULL::numeric")
            ideal = self._sql_expr(s["estoque_ideal_col"], "NULL::numeric")
            consumo = self._sql_expr(s["consumo_medio_col"], "NULL::numeric")
            dataref = self._sql_expr(s["data_col"], "NULL::timestamp")
            obs = self._sql_expr(s["obs_col"], "NULL::text")
            unidade = self._sql_expr(s["unidade_col"], f"'{s['unidade_padrao']}'::text")

            if s["usa_metros_kilos"]:
                saldo_num = f"COALESCE({s['metros_col']},0)" if s["metros_col"] else (f"COALESCE({s['quantidade_col']},0)" if s["quantidade_col"] else "0::numeric")
            else:
                saldo_num = f"COALESCE({s['quantidade_col']},0)" if s["quantidade_col"] else "0::numeric"

            sql = f"""
                SELECT
                    '{s['grupo']}'::text AS grupo_principal,
                    '{s['familia']}'::text AS familia,
                    {codigo}::text AS codigo,
                    {descricao}::text AS descricao,
                    {subgrupo}::text AS subgrupo,
                    {categoria}::text AS categoria,
                    {cor}::text AS cor,
                    {fornecedor}::text AS fornecedor,
                    {localizacao}::text AS localizacao,
                    {composicao}::text AS composicao,
                    {unidade}::text AS unidade,
                    ({saldo_num})::numeric AS saldo_num,
                    {largura}::text AS largura,
                    {gramatura}::text AS gramatura,
                    {minimo}::numeric AS estoque_minimo,
                    {ideal}::numeric AS estoque_ideal,
                    {consumo}::numeric AS consumo_medio,
                    {dataref}::timestamp AS data_ref,
                    {obs}::text AS observacoes,
                    '{s['tabela']}'::text AS origem_tabela
                FROM {s['tabela']}
            """
            partes.append(sql)
        if not partes:
            return "SELECT NULL::text AS grupo_principal WHERE 1=0"
        return "\nUNION ALL\n".join(partes)

    def _run_query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        try:
            rows = db.fetch_all(sql, params or [])
            return rows or []
        except Exception:
            return []

    def _base_dataset(self) -> List[Dict[str, Any]]:
        sql = self._build_union_query()
        return self._run_query(sql)

    # =========================================================
    # FILTROS E APOIO OPERACIONAL
    # =========================================================
    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        r = dict(row or {})
        r["grupo_principal"] = self._safe_text(r.get("grupo_principal"))
        r["codigo"] = self._safe_text(r.get("codigo"))
        r["descricao"] = self._safe_text(r.get("descricao"))
        r["subgrupo"] = self._safe_text(r.get("subgrupo"))
        r["categoria"] = self._safe_text(r.get("categoria"))
        r["cor"] = self._safe_text(r.get("cor"))
        r["fornecedor"] = self._safe_text(r.get("fornecedor"))
        r["localizacao"] = self._safe_text(r.get("localizacao"))
        r["composicao"] = self._safe_text(r.get("composicao"))
        r["unidade"] = self._safe_text(r.get("unidade"))
        r["saldo_num"] = self._safe_float(r.get("saldo_num"))
        r["estoque_minimo"] = self._safe_float(r.get("estoque_minimo"))
        r["estoque_ideal"] = self._safe_float(r.get("estoque_ideal"))
        r["consumo_medio"] = self._safe_float(r.get("consumo_medio"))
        return r

    def _dataset(self, entidades: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        linhas = [self._normalize_row(x) for x in self._base_dataset()]
        if not entidades:
            return linhas

        grupo = entidades.get("grupo") or self.contexto.grupo
        item = entidades.get("item_nome") or self.contexto.item_nome
        codigo = entidades.get("codigo") or self.contexto.item_codigo
        cor = entidades.get("cor") or self.contexto.cor
        fornecedor = entidades.get("fornecedor") or self.contexto.fornecedor
        local = entidades.get("localizacao") or self.contexto.localizacao
        composicao = entidades.get("composicao") or self.contexto.composicao

        def match_text(valor: str, alvo: str) -> bool:
            vn = self._normalize(valor)
            an = self._normalize(alvo)
            return an in vn or vn in an

        out = linhas
        if grupo:
            out = [r for r in out if self._normalize(r.get("grupo_principal", "")) == self._normalize(grupo)]
        if item:
            out = [r for r in out if match_text(r.get("descricao", ""), item) or match_text(r.get("subgrupo", ""), item) or match_text(r.get("categoria", ""), item)]
        if codigo:
            out = [r for r in out if self._normalize(codigo) in self._normalize(r.get("codigo", ""))]
        if cor:
            out = [r for r in out if match_text(r.get("cor", ""), cor)]
        if fornecedor:
            out = [r for r in out if match_text(r.get("fornecedor", ""), fornecedor)]
        if local:
            out = [r for r in out if match_text(r.get("localizacao", ""), local)]
        if composicao:
            out = [r for r in out if match_text(r.get("composicao", ""), composicao)]
        return out

    def _fmt_qtd(self, valor: float) -> str:
        if abs(valor - int(valor)) < 0.0001:
            return f"{int(valor)}"
        return f"{valor:.2f}".replace(".", ",")

    def _fmt_date(self, valor: Any) -> str:
        if valor is None:
            return ""
        if isinstance(valor, datetime):
            return valor.strftime("%d/%m/%Y %H:%M")
        txt = self._safe_text(valor)
        return txt[:19]

    def _unit_for_rows(self, rows: List[Dict[str, Any]]) -> str:
        unidades_validas = {"un", "unid", "unidade", "unidades", "m", "metro", "metros", "kg", "kilo", "kilos", "l", "litro", "litros"}
        for r in rows:
            u = self._safe_text(r.get("unidade"))
            if u and self._normalize(u) in unidades_validas:
                return u
        return "un"

    def _group_label(self, grupo: Optional[str]) -> str:
        return grupo or self.contexto.grupo or "estoque"

    def _save_last_rows(self, rows: List[Dict[str, Any]], intent: str, entidades: Dict[str, Any]) -> None:
        self.contexto.ultimas_linhas = rows[:200]
        self.contexto.ultimo_intent = intent
        self.contexto.ultimo_filtro = entidades
        self.contexto.ultimos_itens_mapeados = [self._safe_text(r.get("descricao")) for r in rows[:50] if self._safe_text(r.get("descricao"))]

    def _rank_item_rows(self, rows: List[Dict[str, Any]], item: Optional[str], codigo: Optional[str]) -> List[Dict[str, Any]]:
        if not item and not codigo:
            return rows

        def score(r: Dict[str, Any]) -> Tuple[int, float]:
            s = 0
            desc = self._normalize(r.get("descricao", ""))
            sub = self._normalize(r.get("subgrupo", ""))
            cat = self._normalize(r.get("categoria", ""))
            cod = self._normalize(r.get("codigo", ""))
            if item:
                ni = self._normalize(item)
                if desc == ni:
                    s += 100
                if ni in desc:
                    s += 60
                if ni in sub:
                    s += 35
                if ni in cat:
                    s += 25
            if codigo:
                nc = self._normalize(codigo)
                if cod == nc:
                    s += 120
                elif nc in cod:
                    s += 80
            return (s, r.get("saldo_num", 0.0))

        return sorted(rows, key=score, reverse=True)

    # =========================================================
    # DESPACHO
    # =========================================================
    def _dispatch(self, intent: Optional[str], pergunta: str, normal: str, entidades: Dict[str, Any]) -> str:
        mapa = {
            "saudacao": self._resp_saudacao,
            "ajuda": self._resp_ajuda,
            "listar_grupo": self._resp_listar_grupo,
            "contar_grupo": self._resp_contar_grupo,
            "listar_itens": self._resp_listar_itens,
            "detalhar_item": self._resp_detalhar_item,
            "listar_cores": self._resp_listar_cores,
            "contar_cores": self._resp_contar_cores,
            "listar_fornecedores": self._resp_fornecedores,
            "listar_locais": self._resp_locais,
            "saldo_item": self._resp_saldo_item,
            "codigo_item": self._resp_codigo_item,
            "itens_criticos": self._resp_criticos,
            "itens_zerados": self._resp_zerados,
            "itens_abaixo": self._resp_abaixo,
            "itens_acima": self._resp_acima,
            "itens_entre": self._resp_entre,
            "top_saldo": self._resp_top_saldo,
            "top_variedade": self._resp_top_variedade,
            "itens_por_cor": self._resp_por_cor,
            "itens_por_fornecedor": self._resp_por_fornecedor,
            "itens_por_local": self._resp_por_local,
            "itens_por_composicao": self._resp_por_composicao,
            "comparar_grupos": self._resp_comparar_grupos,
            "resumo_grupo": self._resp_resumo_grupo,
            "resumo_geral": self._resp_resumo_geral,
            "listar_todos_itens": self._resp_listar_todos_itens,
            "itens_por_setor_detalhado": self._resp_itens_por_setor_detalhado,
            "itens_recentes": self._resp_recentes,
            "contar_codigos": self._resp_contar_codigos,
            "contar_itens_distintos": self._resp_contar_distintos,
            "distribuicao_fornecedores": self._resp_distribuicao_fornecedores,
            "distribuicao_cores": self._resp_distribuicao_cores,
            "distribuicao_locais": self._resp_distribuicao_locais,
            "consultar_cobertura": self._resp_cobertura,
            "consultar_consumo": self._resp_consumo,
            "analise_risco": self._resp_analise_risco,
            "sugestao_compra": self._resp_sugestao_compra,
            "projecao_consumo": self._resp_projecao_consumo,
            "analise_abc": self._resp_analise_abc,
            "resumo_memoria": self._resp_resumo_memoria,
            "workflow_estoque": self._resp_workflow_estoque,
            "resposta_contextual": self._resp_contextual,
        }
        handler = mapa.get(intent)
        return handler(entidades) if handler else ""

    # =========================================================
    # RESPOSTAS
    # =========================================================
    def _resp_saudacao(self, entidades: Dict[str, Any]) -> str:
        return (
            "Olá. Posso consultar o estoque real da fábrica por grupo, item, cor, fornecedor, local, saldo e risco.\n\n"
            "Exemplos:\n"
            "- quais tecidos temos\n"
            "- quantas cores temos no tecido alfaiataria\n"
            "- quem fornece a linha 120\n"
            "- quais aviamentos estão críticos"
        )

    def _resp_ajuda(self, entidades: Dict[str, Any]) -> str:
        return self._help_text(self._extract_help_page(entidades.get("texto_normalizado", "")))

    def _resp_listar_grupo(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        grupo = self._group_label(entidades.get("grupo"))
        if not rows:
            return f"Não encontrei itens em {grupo} com esse filtro."
        agg: Dict[str, float] = {}
        unidade: Dict[str, str] = {}
        for r in rows:
            nome = self._safe_text(r.get("descricao")) or self._safe_text(r.get("subgrupo")) or self._safe_text(r.get("categoria")) or "Sem nome"
            agg[nome] = agg.get(nome, 0.0) + self._safe_float(r.get("saldo_num"))
            unidade[nome] = self._safe_text(r.get("unidade")) or "un"
        ordenado = sorted(agg.items(), key=lambda x: (-x[1], x[0]))
        top_n = 25
        linhas = [f"Encontrei {len(ordenado)} item(ns) em {grupo}."]
        for nome, saldo in ordenado[:top_n]:
            linhas.append(f"- {nome}: {self._fmt_qtd(saldo)} {unidade.get(nome, 'un')}")
        if len(ordenado) > top_n:
            linhas.append(f"... e mais {len(ordenado) - top_n} item(ns).")
        self._save_last_rows(rows, "listar_grupo", entidades)
        return "\n".join(linhas)

    def _resp_contar_grupo(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        grupo = self._group_label(entidades.get("grupo"))
        if not rows:
            return f"Não encontrei registros em {grupo}."
        itens = {self._safe_text(r.get("descricao")) for r in rows if self._safe_text(r.get("descricao"))}
        codigos = {self._safe_text(r.get("codigo")) for r in rows if self._safe_text(r.get("codigo"))}
        saldo = sum(self._safe_float(r.get("saldo_num")) for r in rows)
        return (
            f"Resumo de {grupo}:\n"
            f"- registros: {len(rows)}\n"
            f"- itens distintos: {len(itens)}\n"
            f"- códigos distintos: {len(codigos)}\n"
            f"- saldo somado: {self._fmt_qtd(saldo)} {self._unit_for_rows(rows)}"
        )

    def _resp_listar_itens(self, entidades: Dict[str, Any]) -> str:
        return self._resp_listar_grupo(entidades)

    def _resp_detalhar_item(self, entidades: Dict[str, Any]) -> str:
        rows = self._rank_item_rows(self._dataset(entidades), entidades.get("item_nome"), entidades.get("codigo"))
        if not rows:
            return "Não localizei esse item para detalhar."
        r = rows[0]
        self._save_last_rows(rows, "detalhar_item", entidades)
        riscos = self._classificar_risco(r)
        linhas = [f"Resumo do item: {self._safe_text(r.get('descricao')) or 'Sem nome'}"]
        campos = [
            ("Grupo", r.get("grupo_principal")),
            ("Código", r.get("codigo")),
            ("Subgrupo", r.get("subgrupo")),
            ("Categoria", r.get("categoria")),
            ("Cor", r.get("cor")),
            ("Fornecedor", r.get("fornecedor")),
            ("Localização", r.get("localizacao")),
            ("Composição", r.get("composicao")),
            ("Saldo", f"{self._fmt_qtd(self._safe_float(r.get('saldo_num')))} {self._safe_text(r.get('unidade')) or 'un'}"),
            ("Estoque mínimo", self._fmt_qtd(self._safe_float(r.get("estoque_minimo"))) if r.get("estoque_minimo") not in (None, "") else ""),
            ("Estoque ideal", self._fmt_qtd(self._safe_float(r.get("estoque_ideal"))) if r.get("estoque_ideal") not in (None, "") else ""),
            ("Consumo médio", self._fmt_qtd(self._safe_float(r.get("consumo_medio"))) if r.get("consumo_medio") not in (None, "") else ""),
            ("Largura", r.get("largura")),
            ("Gramatura", r.get("gramatura")),
            ("Última data", self._fmt_date(r.get("data_ref"))),
            ("Origem", r.get("origem_tabela")),
        ]
        for titulo, valor in campos:
            txt = self._safe_text(valor)
            if txt:
                linhas.append(f"- {titulo}: {txt}")
        linhas.append(f"- Situação: {riscos}")
        return "\n".join(linhas)

    def _resp_listar_cores(self, entidades: Dict[str, Any]) -> str:
        rows = self._rank_item_rows(self._dataset(entidades), entidades.get("item_nome"), entidades.get("codigo"))
        cores = sorted({self._safe_text(r.get("cor")) for r in rows if self._safe_text(r.get("cor"))})
        if not cores:
            return "Não encontrei cores para esse filtro."
        item = entidades.get("item_nome") or self.contexto.item_nome or "esse item"
        self._save_last_rows(rows, "listar_cores", entidades)
        return f"Encontrei {len(cores)} cor(es) para {item}:\n- " + "\n- ".join(cores[:50])

    def _resp_contar_cores(self, entidades: Dict[str, Any]) -> str:
        rows = self._rank_item_rows(self._dataset(entidades), entidades.get("item_nome"), entidades.get("codigo"))
        cores = sorted({self._safe_text(r.get("cor")) for r in rows if self._safe_text(r.get("cor"))})
        item = entidades.get("item_nome") or self.contexto.item_nome or "esse item"
        if not cores:
            return f"Não encontrei cores cadastradas para {item}."
        self._save_last_rows(rows, "contar_cores", entidades)
        return f"{item} tem {len(cores)} cor(es) cadastrada(s)."

    def _resp_fornecedores(self, entidades: Dict[str, Any]) -> str:
        rows = self._rank_item_rows(self._dataset(entidades), entidades.get("item_nome"), entidades.get("codigo"))
        fornecedores = sorted({self._safe_text(r.get("fornecedor")) for r in rows if self._safe_text(r.get("fornecedor"))})
        if not fornecedores:
            return "Não encontrei fornecedores para esse filtro."
        self._save_last_rows(rows, "listar_fornecedores", entidades)
        item = entidades.get("item_nome") or self.contexto.item_nome
        if item:
            return f"Fornecedor(es) encontrados para {item}:\n- " + "\n- ".join(fornecedores[:30])
        return "Fornecedores encontrados:\n- " + "\n- ".join(fornecedores[:30])

    def _resp_locais(self, entidades: Dict[str, Any]) -> str:
        rows = self._rank_item_rows(self._dataset(entidades), entidades.get("item_nome"), entidades.get("codigo"))
        locais = sorted({self._safe_text(r.get("localizacao")) for r in rows if self._safe_text(r.get("localizacao"))})
        if not locais:
            return "Não encontrei localizações para esse filtro."
        self._save_last_rows(rows, "listar_locais", entidades)
        item = entidades.get("item_nome") or self.contexto.item_nome
        if item:
            return f"Localização(ões) encontradas para {item}:\n- " + "\n- ".join(locais[:30])
        return "Localizações encontradas:\n- " + "\n- ".join(locais[:30])

    def _resp_saldo_item(self, entidades: Dict[str, Any]) -> str:
        rows = self._rank_item_rows(self._dataset(entidades), entidades.get("item_nome"), entidades.get("codigo"))
        if not rows:
            return "Não encontrei saldo para esse item."
        r = rows[0]
        self._save_last_rows(rows, "saldo_item", entidades)
        return (
            f"Saldo atual de {self._safe_text(r.get('descricao')) or 'esse item'}: "
            f"{self._fmt_qtd(self._safe_float(r.get('saldo_num')))} {self._safe_text(r.get('unidade')) or 'un'}"
        )

    def _resp_codigo_item(self, entidades: Dict[str, Any]) -> str:
        rows = self._rank_item_rows(self._dataset(entidades), entidades.get("item_nome"), entidades.get("codigo"))
        codigos = [self._safe_text(r.get("codigo")) for r in rows if self._safe_text(r.get("codigo"))]
        codigos = list(dict.fromkeys(codigos))
        if not codigos:
            return "Não encontrei código para esse item."
        item = entidades.get("item_nome") or self.contexto.item_nome or "esse item"
        self._save_last_rows(rows, "codigo_item", entidades)
        return f"Código(s) encontrado(s) para {item}:\n- " + "\n- ".join(codigos[:20])

    def _resp_criticos(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        criticos = [r for r in rows if self._is_critical(r)]
        if not criticos:
            return "Não encontrei itens críticos nesse filtro."
        criticos = sorted(criticos, key=lambda r: (self._safe_float(r.get("saldo_num")), self._safe_text(r.get("descricao"))))
        self._save_last_rows(criticos, "itens_criticos", entidades)
        linhas = [f"Encontrei {len(criticos)} item(ns) críticos:"]
        for r in criticos[:25]:
            linhas.append(
                f"- {self._safe_text(r.get('descricao')) or 'Sem nome'} | saldo {self._fmt_qtd(self._safe_float(r.get('saldo_num')))} {self._safe_text(r.get('unidade')) or 'un'}"
                + (f" | mínimo {self._fmt_qtd(self._safe_float(r.get('estoque_minimo')))}" if self._safe_float(r.get("estoque_minimo")) > 0 else "")
            )
        return "\n".join(linhas)

    def _resp_zerados(self, entidades: Dict[str, Any]) -> str:
        rows = [r for r in self._dataset(entidades) if abs(self._safe_float(r.get("saldo_num"))) < 0.0001]
        if not rows:
            return "Não encontrei itens zerados nesse filtro."
        self._save_last_rows(rows, "itens_zerados", entidades)
        linhas = [f"Encontrei {len(rows)} item(ns) zerado(s):"]
        for r in rows[:25]:
            linhas.append(f"- {self._safe_text(r.get('descricao')) or 'Sem nome'} | grupo {self._safe_text(r.get('grupo_principal'))}")
        return "\n".join(linhas)

    def _resp_abaixo(self, entidades: Dict[str, Any]) -> str:
        limite = (entidades.get("faixa") or {}).get("max")
        if limite is None:
            limite = self.contexto.ultimo_limite if self.contexto.ultimo_limite is not None else 10
        rows = [r for r in self._dataset(entidades) if self._safe_float(r.get("saldo_num")) < float(limite)]
        if not rows:
            return f"Não encontrei itens com saldo abaixo de {self._fmt_qtd(float(limite))}."
        rows = sorted(rows, key=lambda r: self._safe_float(r.get("saldo_num")))
        self._save_last_rows(rows, "itens_abaixo", entidades)
        linhas = [f"Itens com saldo abaixo de {self._fmt_qtd(float(limite))}:"]
        for r in rows[:25]:
            linhas.append(f"- {self._safe_text(r.get('descricao'))} | saldo {self._fmt_qtd(self._safe_float(r.get('saldo_num')))} {self._safe_text(r.get('unidade')) or 'un'}")
        return "\n".join(linhas)

    def _resp_acima(self, entidades: Dict[str, Any]) -> str:
        limite = (entidades.get("faixa") or {}).get("min")
        if limite is None:
            limite = self.contexto.quantidade_ref if self.contexto.quantidade_ref is not None else 0
        rows = [r for r in self._dataset(entidades) if self._safe_float(r.get("saldo_num")) > float(limite)]
        if not rows:
            return f"Não encontrei itens com saldo acima de {self._fmt_qtd(float(limite))}."
        rows = sorted(rows, key=lambda r: self._safe_float(r.get("saldo_num")), reverse=True)
        self._save_last_rows(rows, "itens_acima", entidades)
        linhas = [f"Itens com saldo acima de {self._fmt_qtd(float(limite))}:"]
        for r in rows[:25]:
            linhas.append(f"- {self._safe_text(r.get('descricao'))} | saldo {self._fmt_qtd(self._safe_float(r.get('saldo_num')))} {self._safe_text(r.get('unidade')) or 'un'}")
        return "\n".join(linhas)

    def _resp_entre(self, entidades: Dict[str, Any]) -> str:
        faixa = entidades.get("faixa") or {}
        vmin, vmax = faixa.get("min"), faixa.get("max")
        if vmin is None or vmax is None:
            return "Informe um intervalo. Exemplo: itens com saldo entre 10 e 30."
        rows = [r for r in self._dataset(entidades) if float(vmin) <= self._safe_float(r.get("saldo_num")) <= float(vmax)]
        if not rows:
            return f"Não encontrei itens entre {self._fmt_qtd(float(vmin))} e {self._fmt_qtd(float(vmax))}."
        rows = sorted(rows, key=lambda r: self._safe_float(r.get("saldo_num")))
        self._save_last_rows(rows, "itens_entre", entidades)
        linhas = [f"Itens com saldo entre {self._fmt_qtd(float(vmin))} e {self._fmt_qtd(float(vmax))}:"]
        for r in rows[:25]:
            linhas.append(f"- {self._safe_text(r.get('descricao'))} | saldo {self._fmt_qtd(self._safe_float(r.get('saldo_num')))} {self._safe_text(r.get('unidade')) or 'un'}")
        return "\n".join(linhas)

    def _resp_top_saldo(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        if not rows:
            return "Não encontrei itens para montar o ranking."
        ordenado = sorted(rows, key=lambda r: self._safe_float(r.get("saldo_num")), reverse=True)
        self._save_last_rows(ordenado, "top_saldo", entidades)
        linhas = ["Top itens por saldo:"]
        for r in ordenado[:15]:
            linhas.append(f"- {self._safe_text(r.get('descricao'))} | {self._fmt_qtd(self._safe_float(r.get('saldo_num')))} {self._safe_text(r.get('unidade')) or 'un'} | grupo {self._safe_text(r.get('grupo_principal'))}")
        return "\n".join(linhas)

    def _resp_top_variedade(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        if not rows:
            return "Não encontrei dados para variedade."
        mapa: Dict[str, set] = {}
        for r in rows:
            nome = self._safe_text(r.get("descricao")) or self._safe_text(r.get("subgrupo")) or self._safe_text(r.get("categoria"))
            cor = self._safe_text(r.get("cor"))
            if nome and cor:
                mapa.setdefault(nome, set()).add(cor)
        if not mapa:
            return "Não há variações de cor suficientes para montar o ranking."
        ordenado = sorted(((nome, len(cores)) for nome, cores in mapa.items()), key=lambda x: (-x[1], x[0]))
        linhas = ["Top itens por variedade de cores:"]
        for nome, qtd in ordenado[:15]:
            linhas.append(f"- {nome}: {qtd} cor(es)")
        return "\n".join(linhas)

    def _resp_por_cor(self, entidades: Dict[str, Any]) -> str:
        cor = entidades.get("cor") or self.contexto.cor
        rows = self._dataset(entidades)
        if not rows:
            return f"Não encontrei itens com a cor {cor}."
        self._save_last_rows(rows, "itens_por_cor", entidades)
        linhas = [f"Itens encontrados na cor {cor}:"]
        for r in rows[:25]:
            linhas.append(f"- {self._safe_text(r.get('descricao'))} | grupo {self._safe_text(r.get('grupo_principal'))} | saldo {self._fmt_qtd(self._safe_float(r.get('saldo_num')))}")
        return "\n".join(linhas)

    def _resp_por_fornecedor(self, entidades: Dict[str, Any]) -> str:
        fornecedor = entidades.get("fornecedor") or self.contexto.fornecedor
        rows = self._dataset(entidades)
        if not rows:
            return f"Não encontrei itens do fornecedor {fornecedor}."
        self._save_last_rows(rows, "itens_por_fornecedor", entidades)
        linhas = [f"Itens do fornecedor {fornecedor}:"]
        for r in rows[:25]:
            linhas.append(f"- {self._safe_text(r.get('descricao'))} | grupo {self._safe_text(r.get('grupo_principal'))} | saldo {self._fmt_qtd(self._safe_float(r.get('saldo_num')))}")
        return "\n".join(linhas)

    def _resp_por_local(self, entidades: Dict[str, Any]) -> str:
        local = entidades.get("localizacao") or self.contexto.localizacao
        rows = self._dataset(entidades)
        if not rows:
            return f"Não encontrei itens em {local}."
        self._save_last_rows(rows, "itens_por_local", entidades)
        linhas = [f"Itens em {local}:"]
        for r in rows[:25]:
            linhas.append(f"- {self._safe_text(r.get('descricao'))} | grupo {self._safe_text(r.get('grupo_principal'))} | saldo {self._fmt_qtd(self._safe_float(r.get('saldo_num')))}")
        return "\n".join(linhas)

    def _resp_por_composicao(self, entidades: Dict[str, Any]) -> str:
        comp = entidades.get("composicao") or self.contexto.composicao
        rows = self._dataset(entidades)
        if not rows:
            return f"Não encontrei itens com composição {comp}."
        self._save_last_rows(rows, "itens_por_composicao", entidades)
        linhas = [f"Itens com composição {comp}:"]
        for r in rows[:25]:
            linhas.append(f"- {self._safe_text(r.get('descricao'))} | cor {self._safe_text(r.get('cor')) or '-'} | saldo {self._fmt_qtd(self._safe_float(r.get('saldo_num')))}")
        return "\n".join(linhas)

    def _resp_comparar_grupos(self, entidades: Dict[str, Any]) -> str:
        grupos = entidades.get("grupos_mencionados") or self.contexto.comparacao_grupos
        if len(grupos) < 2:
            return "Informe dois grupos para comparar. Exemplo: compare tecidos e aviamentos."
        base = self._dataset({})
        linhas = ["Comparativo entre grupos:"]
        for grupo in grupos[:4]:
            rows = [r for r in base if self._normalize(r.get("grupo_principal", "")) == self._normalize(grupo)]
            itens = len({self._safe_text(r.get("descricao")) for r in rows if self._safe_text(r.get("descricao"))})
            saldo = sum(self._safe_float(r.get("saldo_num")) for r in rows)
            crit = len([r for r in rows if self._is_critical(r)])
            linhas.append(f"- {grupo}: itens distintos {itens}, saldo total {self._fmt_qtd(saldo)}, críticos {crit}")
        return "\n".join(linhas)

    def _resp_resumo_grupo(self, entidades: Dict[str, Any]) -> str:
        grupo = entidades.get("grupo") or self.contexto.grupo
        if not grupo:
            return self._resp_resumo_geral(entidades)
        rows = self._dataset({"grupo": grupo})
        if not rows:
            return f"Não encontrei dados para {grupo}."
        itens = {self._safe_text(r.get("descricao")) for r in rows if self._safe_text(r.get("descricao"))}
        cores = {self._safe_text(r.get("cor")) for r in rows if self._safe_text(r.get("cor"))}
        forn = {self._safe_text(r.get("fornecedor")) for r in rows if self._safe_text(r.get("fornecedor"))}
        locais = {self._safe_text(r.get("localizacao")) for r in rows if self._safe_text(r.get("localizacao"))}
        crit = len([r for r in rows if self._is_critical(r)])
        zero = len([r for r in rows if abs(self._safe_float(r.get("saldo_num"))) < 0.0001])
        saldo = sum(self._safe_float(r.get("saldo_num")) for r in rows)
        return (
            f"Resumo de {grupo}:\n"
            f"- registros: {len(rows)}\n"
            f"- itens distintos: {len(itens)}\n"
            f"- cores distintas: {len(cores)}\n"
            f"- fornecedores: {len(forn)}\n"
            f"- localizações: {len(locais)}\n"
            f"- saldo total: {self._fmt_qtd(saldo)} {self._unit_for_rows(rows)}\n"
            f"- críticos: {crit}\n"
            f"- zerados: {zero}"
        )

    def _resp_resumo_geral(self, entidades: Dict[str, Any]) -> str:
        base = self._dataset({})
        if not base:
            return "Não consegui consultar o estoque agora."
        por_grupo: Dict[str, List[Dict[str, Any]]] = {}
        for r in base:
            por_grupo.setdefault(self._safe_text(r.get("grupo_principal")) or "Sem grupo", []).append(r)
        linhas = ["Resumo geral do estoque:"]
        for grupo, rows in sorted(por_grupo.items()):
            itens = len({self._safe_text(r.get("descricao")) for r in rows if self._safe_text(r.get("descricao"))})
            saldo = sum(self._safe_float(r.get("saldo_num")) for r in rows)
            crit = len([r for r in rows if self._is_critical(r)])
            linhas.append(f"- {grupo}: {itens} item(ns) distintos | saldo {self._fmt_qtd(saldo)} | críticos {crit}")
        linhas.append("Pergunte, por exemplo: quais tecidos temos ou quais aviamentos estão críticos.")
        return "\n".join(linhas)

    def _resp_listar_todos_itens(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset({})
        if not rows:
            return "Não encontrei itens no estoque para listar."
        agg: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            nome = self._safe_text(r.get("descricao")) or "Sem nome"
            grp = self._safe_text(r.get("grupo_principal")) or "Sem grupo"
            key = f"{grp}::{nome}"
            if key not in agg:
                agg[key] = {"grupo": grp, "nome": nome, "saldo": 0.0, "unidade": self._safe_text(r.get("unidade")) or "un"}
            agg[key]["saldo"] += self._safe_float(r.get("saldo_num"))
        ordenado = sorted(agg.values(), key=lambda x: (x["grupo"], x["nome"]))
        self._save_last_rows(rows, "listar_todos_itens", {"escopo_global": True})
        linhas = [f"Inventário geral: {len(ordenado)} item(ns) distintos."]
        for item in ordenado[:80]:
            linhas.append(f"- [{item['grupo']}] {item['nome']} | saldo {self._fmt_qtd(item['saldo'])} {item['unidade']}")
        if len(ordenado) > 80:
            linhas.append(f"... e mais {len(ordenado) - 80} item(ns).")
        return "\n".join(linhas)

    def _resp_itens_por_setor_detalhado(self, entidades: Dict[str, Any]) -> str:
        filtro = {"grupo": entidades.get("grupo")} if entidades.get("grupo") else {}
        rows = self._dataset(filtro if filtro else {})
        if not rows:
            return "Não encontrei dados para listar por setor."
        mapa: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            setor = self._safe_text(r.get("localizacao")) or "Sem localização"
            nome = self._safe_text(r.get("descricao")) or "Sem nome"
            if setor not in mapa:
                mapa[setor] = {"nomes": set(), "saldo": 0.0}
            mapa[setor]["nomes"].add(nome)
            mapa[setor]["saldo"] += self._safe_float(r.get("saldo_num"))
        ordenado = sorted(mapa.items(), key=lambda x: (-len(x[1]["nomes"]), x[0]))
        linhas = ["Itens por setor/localização:"]
        for setor, info in ordenado:
            nomes = sorted(info["nomes"])
            linhas.append(f"- {setor}: {len(nomes)} item(ns) | saldo total {self._fmt_qtd(info['saldo'])}")
            for nome in nomes[:15]:
                linhas.append(f"  • {nome}")
            if len(nomes) > 15:
                linhas.append(f"  • ... +{len(nomes) - 15} item(ns)")
        self._save_last_rows(rows, "itens_por_setor_detalhado", entidades)
        return "\n".join(linhas)

    def _resp_recentes(self, entidades: Dict[str, Any]) -> str:
        rows = [r for r in self._dataset(entidades) if r.get("data_ref") not in (None, "")]
        if not rows:
            return "Não encontrei datas para identificar itens recentes."
        rows = sorted(rows, key=lambda r: self._fmt_date(r.get("data_ref")), reverse=True)
        self._save_last_rows(rows, "itens_recentes", entidades)
        linhas = ["Itens mais recentes:"]
        for r in rows[:20]:
            linhas.append(f"- {self._safe_text(r.get('descricao'))} | data {self._fmt_date(r.get('data_ref'))} | grupo {self._safe_text(r.get('grupo_principal'))}")
        return "\n".join(linhas)

    def _resp_contar_codigos(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        codigos = {self._safe_text(r.get("codigo")) for r in rows if self._safe_text(r.get("codigo"))}
        grupo = entidades.get("grupo") or self.contexto.grupo
        if grupo:
            return f"Encontrei {len(codigos)} código(s) distinto(s) em {grupo}."
        return f"Encontrei {len(codigos)} código(s) distinto(s) no estoque consultado."

    def _resp_contar_distintos(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        itens = {self._safe_text(r.get("descricao")) for r in rows if self._safe_text(r.get("descricao"))}
        return f"Encontrei {len(itens)} item(ns) distinto(s) no filtro atual."

    def _resp_distribuicao_fornecedores(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        mapa: Dict[str, int] = {}
        for r in rows:
            nome = self._safe_text(r.get("fornecedor"))
            if nome:
                mapa[nome] = mapa.get(nome, 0) + 1
        if not mapa:
            return "Não encontrei fornecedores para distribuir nesse filtro."
        ordenado = sorted(mapa.items(), key=lambda x: (-x[1], x[0]))
        linhas = ["Distribuição por fornecedor:"]
        for nome, qtd in ordenado[:20]:
            linhas.append(f"- {nome}: {qtd} registro(s)")
        return "\n".join(linhas)

    def _resp_distribuicao_cores(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        mapa: Dict[str, int] = {}
        for r in rows:
            cor = self._safe_text(r.get("cor"))
            if cor:
                mapa[cor] = mapa.get(cor, 0) + 1
        if not mapa:
            return "Não encontrei cores suficientes para montar a distribuição."
        total = max(1, sum(mapa.values()))
        ordenado = sorted(mapa.items(), key=lambda x: (-x[1], x[0]))
        linhas = ["Distribuição por cor (participação no filtro):"]
        for cor, qtd in ordenado[:25]:
            pct = (qtd / total) * 100
            linhas.append(f"- {cor}: {qtd} registro(s) ({self._fmt_qtd(pct)}%)")
        return "\n".join(linhas)

    def _resp_distribuicao_locais(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        mapa: Dict[str, int] = {}
        for r in rows:
            local = self._safe_text(r.get("localizacao"))
            if local:
                mapa[local] = mapa.get(local, 0) + 1
        if not mapa:
            return "Não encontrei localizações suficientes para montar a distribuição."
        total = max(1, sum(mapa.values()))
        ordenado = sorted(mapa.items(), key=lambda x: (-x[1], x[0]))
        linhas = ["Distribuição por localização (participação no filtro):"]
        for local, qtd in ordenado[:25]:
            pct = (qtd / total) * 100
            linhas.append(f"- {local}: {qtd} registro(s) ({self._fmt_qtd(pct)}%)")
        return "\n".join(linhas)

    def _resp_cobertura(self, entidades: Dict[str, Any]) -> str:
        rows = self._rank_item_rows(self._dataset(entidades), entidades.get("item_nome"), entidades.get("codigo"))
        if not rows:
            return "Não encontrei item para calcular cobertura."
        r = rows[0]
        consumo = self._safe_float(r.get("consumo_medio"))
        saldo = self._safe_float(r.get("saldo_num"))
        if consumo <= 0:
            return "Não há consumo médio suficiente para calcular cobertura desse item."
        dias = saldo / consumo
        return f"A cobertura estimada de {self._safe_text(r.get('descricao'))} é de {self._fmt_qtd(dias)} período(s), considerando consumo médio cadastrado."

    def _resp_consumo(self, entidades: Dict[str, Any]) -> str:
        rows = self._rank_item_rows(self._dataset(entidades), entidades.get("item_nome"), entidades.get("codigo"))
        if not rows:
            return "Não encontrei item para consultar consumo."
        r = rows[0]
        consumo = self._safe_float(r.get("consumo_medio"))
        if consumo <= 0:
            return "Esse item não tem consumo médio cadastrado."
        return f"Consumo médio de {self._safe_text(r.get('descricao'))}: {self._fmt_qtd(consumo)} {self._safe_text(r.get('unidade')) or 'un'} por período."

    def _resp_analise_risco(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        if not rows:
            return "Não encontrei dados para análise de risco."
        classes = Counter()
        for r in rows:
            classes[self._classificar_risco(r)] += 1
        total = max(1, sum(classes.values()))
        ordenado = sorted(classes.items(), key=lambda x: (-x[1], x[0]))
        linhas = ["Matriz de risco do estoque (filtro atual):"]
        for classe, qtd in ordenado:
            pct = (qtd / total) * 100
            linhas.append(f"- {classe}: {qtd} item(ns) ({self._fmt_qtd(pct)}%)")
        criticos = [r for r in rows if self._classificar_risco(r) in {"sem saldo", "crítico", "cobertura curta"}]
        if criticos:
            criticos = sorted(criticos, key=lambda r: (self._safe_float(r.get("saldo_num")), self._safe_text(r.get("descricao"))))
            linhas.append("")
            linhas.append("Prioridade de atenção:")
            for r in criticos[:10]:
                linhas.append(
                    f"- {self._safe_text(r.get('descricao')) or 'Sem nome'} | saldo {self._fmt_qtd(self._safe_float(r.get('saldo_num')))} "
                    f"{self._safe_text(r.get('unidade')) or 'un'} | risco {self._classificar_risco(r)}"
                )
        return "\n".join(linhas)

    def _resp_sugestao_compra(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        if not rows:
            return "Não encontrei dados para sugerir reposição."
        candidatos = []
        for r in rows:
            saldo = self._safe_float(r.get("saldo_num"))
            minimo = self._safe_float(r.get("estoque_minimo"))
            ideal = self._safe_float(r.get("estoque_ideal"))
            consumo = self._safe_float(r.get("consumo_medio"))
            if ideal > 0:
                alvo = ideal
            elif minimo > 0:
                alvo = minimo * 1.35
            elif consumo > 0:
                alvo = consumo * 2.0
            else:
                alvo = 0.0
            if alvo > saldo:
                faltante = max(0.0, alvo - saldo)
                prioridade = (2.0 if saldo <= 0 else 1.2 if minimo > 0 and saldo <= minimo else 1.0) * (1.0 + consumo)
                candidatos.append((prioridade, faltante, r))
        if not candidatos:
            return "No filtro atual, não identifiquei itens com necessidade clara de reposição."
        candidatos.sort(key=lambda x: (-x[0], -x[1]))
        linhas = ["Sugestão inteligente de reposição (estimativa):"]
        for _, faltante, r in candidatos[:15]:
            desc = self._safe_text(r.get("descricao")) or "Sem nome"
            un = self._safe_text(r.get("unidade")) or "un"
            saldo = self._safe_float(r.get("saldo_num"))
            minimo = self._safe_float(r.get("estoque_minimo"))
            ideal = self._safe_float(r.get("estoque_ideal"))
            linhas.append(
                f"- {desc}: sugerido repor ~{self._fmt_qtd(faltante)} {un} "
                f"(saldo {self._fmt_qtd(saldo)}, mínimo {self._fmt_qtd(minimo)}, ideal {self._fmt_qtd(ideal)})"
            )
        linhas.append("Obs.: cálculo usa estoque mínimo/ideal e consumo médio quando disponível.")
        return "\n".join(linhas)

    def _resp_projecao_consumo(self, entidades: Dict[str, Any]) -> str:
        horizonte = entidades.get("numero")
        dias = int(horizonte) if isinstance(horizonte, (int, float)) and horizonte > 0 else 30
        dias = max(1, min(dias, 365))
        rows = self._rank_item_rows(self._dataset(entidades), entidades.get("item_nome"), entidades.get("codigo"))
        if not rows:
            return "Não encontrei item para fazer projeção."
        r = rows[0]
        consumo = self._safe_float(r.get("consumo_medio"))
        saldo = self._safe_float(r.get("saldo_num"))
        if consumo <= 0:
            return "Esse item não tem consumo médio suficiente para projetar."
        saldo_estimado = saldo - (consumo * dias)
        linhas = [
            f"Projeção de consumo para {self._safe_text(r.get('descricao')) or 'item'} em {dias} período(s):",
            f"- saldo atual: {self._fmt_qtd(saldo)} {self._safe_text(r.get('unidade')) or 'un'}",
            f"- consumo médio: {self._fmt_qtd(consumo)} por período",
            f"- saldo projetado: {self._fmt_qtd(saldo_estimado)} {self._safe_text(r.get('unidade')) or 'un'}",
        ]
        if saldo_estimado <= 0:
            linhas.append("- alerta: ruptura provável dentro do horizonte consultado.")
        elif saldo_estimado < self._safe_float(r.get("estoque_minimo")) and self._safe_float(r.get("estoque_minimo")) > 0:
            linhas.append("- alerta: saldo projetado abaixo do estoque mínimo.")
        else:
            linhas.append("- status: saldo projetado ainda em faixa operacional.")
        return "\n".join(linhas)

    def _resp_analise_abc(self, entidades: Dict[str, Any]) -> str:
        rows = self._dataset(entidades)
        if not rows:
            return "Não encontrei dados para análise ABC."
        por_item: Dict[str, float] = {}
        for r in rows:
            nome = self._safe_text(r.get("descricao")) or self._safe_text(r.get("codigo"))
            if nome:
                por_item[nome] = por_item.get(nome, 0.0) + max(0.0, self._safe_float(r.get("saldo_num")))
        if not por_item:
            return "Não há saldo positivo suficiente para classificar em curva ABC."
        total = sum(por_item.values())
        if total <= 0:
            return "Não há base de saldo para calcular curva ABC."
        ordenado = sorted(por_item.items(), key=lambda x: x[1], reverse=True)
        acumulado = 0.0
        classes = {"A": [], "B": [], "C": []}
        for nome, valor in ordenado:
            acumulado += valor
            perc = acumulado / total
            if perc <= 0.80:
                classe = "A"
            elif perc <= 0.95:
                classe = "B"
            else:
                classe = "C"
            classes[classe].append((nome, valor))
        linhas = ["Curva ABC por participação no saldo do filtro:"]
        for classe in ("A", "B", "C"):
            itens = classes[classe]
            subtotal = sum(v for _, v in itens)
            pct = (subtotal / total) * 100 if total > 0 else 0
            linhas.append(f"- Classe {classe}: {len(itens)} item(ns), {self._fmt_qtd(pct)}% do saldo acumulado")
            for nome, valor in itens[:5]:
                linhas.append(f"  • {nome}: {self._fmt_qtd(valor)}")
        return "\n".join(linhas)

    def _resp_resumo_memoria(self, entidades: Dict[str, Any]) -> str:
        if not self.memoria_consultas:
            return "Ainda não tenho memória de consultas nesta sessão. Faça uma pergunta de estoque para começar."
        ultimas = self.memoria_consultas[-8:]
        linhas = ["Resumo inteligente da conversa (últimas consultas):"]
        for m in reversed(ultimas):
            foco = m.get("item_nome") or m.get("grupo") or "estoque geral"
            linhas.append(f"- [{m.get('ts')}] {m.get('intent')} | foco: {foco}")
        if self.contexto.item_nome or self.contexto.grupo:
            linhas.append("")
            linhas.append("Contexto ativo agora:")
            if self.contexto.grupo:
                linhas.append(f"- grupo: {self.contexto.grupo}")
            if self.contexto.item_nome:
                linhas.append(f"- item: {self.contexto.item_nome}")
            if self.contexto.item_codigo:
                linhas.append(f"- código: {self.contexto.item_codigo}")
            if self.contexto.cor:
                linhas.append(f"- cor: {self.contexto.cor}")
        linhas.append("Se quiser, posso continuar usando esse contexto sem você repetir tudo.")
        return "\n".join(linhas)

    def _resp_workflow_estoque(self, entidades: Dict[str, Any]) -> str:
        """
        Workflow de alto nível para auditoria completa de estoque.
        """
        partes = [
            self._resp_resumo_geral(entidades),
            "",
            self._resp_analise_risco(entidades),
            "",
            self._resp_sugestao_compra(entidades),
            "",
            self._resp_itens_por_setor_detalhado(entidades),
        ]
        self.contexto.objetivo_ativo = "workflow_diagnostico_completo"
        self.contexto.objetivo_status = "concluido"
        self.contexto.proxima_acao_sugerida = "inventario_completo"
        return "\n".join(partes)

    def _resp_contextual(self, entidades: Dict[str, Any]) -> str:
        ultimo = self.contexto.ultimo_intent
        if ultimo == "listar_grupo":
            if entidades.get("cor"):
                return self._resp_por_cor(entidades)
            if self._has_any(entidades.get("texto_normalizado", ""), self.PALAVRAS_ACAO["baixo"]):
                return self._resp_criticos(entidades)
            if self._has_any(entidades.get("texto_normalizado", ""), self.PALAVRAS_ACAO["fornecedor"]):
                return self._resp_fornecedores(entidades)
        if self.contexto.item_nome or self.contexto.item_codigo:
            if self._has_any(entidades.get("texto_normalizado", ""), self.PALAVRAS_ACAO["cores"]):
                return self._resp_listar_cores(entidades)
            if self._has_any(entidades.get("texto_normalizado", ""), self.PALAVRAS_ACAO["fornecedor"]):
                return self._resp_fornecedores(entidades)
            if self._has_any(entidades.get("texto_normalizado", ""), self.PALAVRAS_ACAO["onde"]):
                return self._resp_locais(entidades)
        return self._resp_resumo_grupo(entidades)

    # =========================================================
    # APOIO DE RISCO / ANÁLISE
    # =========================================================
    def _is_critical(self, r: Dict[str, Any]) -> bool:
        saldo = self._safe_float(r.get("saldo_num"))
        minimo = self._safe_float(r.get("estoque_minimo"))
        if minimo > 0:
            return saldo <= minimo
        return saldo <= 0

    def _classificar_risco(self, r: Dict[str, Any]) -> str:
        saldo = self._safe_float(r.get("saldo_num"))
        minimo = self._safe_float(r.get("estoque_minimo"))
        ideal = self._safe_float(r.get("estoque_ideal"))
        consumo = self._safe_float(r.get("consumo_medio"))
        if saldo <= 0:
            return "sem saldo"
        if minimo > 0 and saldo <= minimo:
            return "crítico"
        if ideal > 0 and saldo < ideal:
            return "abaixo do ideal"
        if consumo > 0 and saldo / consumo < 1:
            return "cobertura curta"
        return "adequado"

    # =========================================================
    # FALLBACKS
    # =========================================================
    def _fallback_conversacional(self, pergunta: str, entidades: Dict[str, Any], intent: Optional[str], score: float) -> str:
        grupo = entidades.get("grupo") or self.contexto.grupo
        item = entidades.get("item_nome") or self.contexto.item_nome
        if item:
            return (
                f"Entendi que você pode estar falando de {item}.\n"
                f"Você pode perguntar, por exemplo:\n"
                f"- qual o saldo de {item}\n"
                f"- quantas cores temos em {item}\n"
                f"- quem fornece {item}\n"
                f"- onde está guardado {item}"
            )
        if grupo:
            return (
                f"Entendi que o foco pode ser {grupo}.\n"
                f"Você pode perguntar:\n"
                f"- quais {grupo.lower()} temos\n"
                f"- quais {grupo.lower()} estão críticos\n"
                f"- quantos códigos distintos temos em {grupo.lower()}\n"
                f"- quais fornecedores temos em {grupo.lower()}"
            )
        return (
            "Não entendi completamente a intenção.\n"
            "Tente algo como:\n"
            "- quais tecidos temos\n"
            "- quais aviamentos estão críticos\n"
            "- quantas cores temos no tecido alfaiataria\n"
            "- quem fornece a linha 120"
        )



# ------------------------------------------------------------------
# INTERFACE PRINCIPAL (MESMO PADRÃO DO CADASTRO_DE_CORTE)
# ------------------------------------------------------------------
