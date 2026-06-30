# -*- coding: utf-8 -*-
"""
Laboratorio headless para treinar e regredir a IA de estoque.

Este modulo nao escreve no banco real. Ele injeta uma base de estoque
simulada na classe EstoqueIA e executa rodadas de perguntas.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from PAGINAS_DO_SISTEMA.RELATORIO_ESTOQUE_IA import EstoqueIA


def _row(
    grupo: str,
    codigo: str,
    descricao: str,
    cor: str,
    saldo: float,
    unidade: str,
    fornecedor: str,
    localizacao: str,
    subgrupo: str = "",
    categoria: str = "",
    composicao: str = "",
    minimo: float = 0,
    ideal: float = 0,
    consumo: float = 0,
    data_ref: str = "2026-06-20 08:00:00",
) -> Dict[str, Any]:
    return {
        "grupo_principal": grupo,
        "familia": "textil" if grupo == "Tecidos" else "acabamento" if grupo == "Aviamentos" else "geral",
        "codigo": codigo,
        "descricao": descricao,
        "subgrupo": subgrupo,
        "categoria": categoria,
        "cor": cor,
        "fornecedor": fornecedor,
        "localizacao": localizacao,
        "composicao": composicao,
        "unidade": unidade,
        "saldo_num": saldo,
        "estoque_minimo": minimo,
        "estoque_ideal": ideal,
        "consumo_medio": consumo,
        "data_ref": data_ref,
        "origem_tabela": f"estoque_{grupo.lower()}",
    }


ESTOQUE_TREINO: List[Dict[str, Any]] = [
    _row("Tecidos", "TEC-001", "Malha Canelada", "preto", 35, "m", "TexBrasil", "RUA A / PRAT 01", "malha", "canelado", "algodao elastano", 10, 60, 2.5),
    _row("Tecidos", "TEC-002", "Malha Canelada", "azul marinho", 6, "m", "TexBrasil", "RUA A / PRAT 02", "malha", "canelado", "algodao elastano", 10, 60, 2.5),
    _row("Tecidos", "TEC-003", "Moletom Felpado", "cinza", 0, "m", "Sul Textil", "RUA B / PRAT 01", "moletom", "inverno", "algodao poliester", 12, 80, 4),
    _row("Tecidos", "TEC-004", "Tricoline Lisa", "branco", 120, "m", "Fios Nobres", "RUA C / PRAT 04", "plano", "camisaria", "algodao", 20, 100, 3),
    _row("Tecidos", "TEC-005", "Oxford Escolar", "azul", 18, "m", "Fios Nobres", "RUA C / PRAT 05", "plano", "uniforme", "poliester", 25, 120, 5),
    _row("Tecidos", "TEC-006", "Viscose Estampada Floral", "verde", 44, "m", "Casa da Viscose", "RUA D / PRAT 02", "viscose", "estampado", "viscose", 15, 70, 2),
    _row("Tecidos", "TEC-007", "Ribana Tubular", "preto", 9, "kg", "Malharia Prime", "RUA E / BALANCA", "ribana", "acabamento", "algodao elastano", 8, 35, 1.2),
    _row("Tecidos", "TEC-008", "Jeans Leve", "azul", 65, "m", "Denim Pro", "RUA F / ROLO 03", "jeans", "denim", "algodao", 18, 90, 3.5),
    _row("Aviamentos", "ZIP-010", "Ziper Nylon N5", "preto", 200, "un", "Casa do Ziper", "GAVETA 03", "ziper", "fechamento", "", 50, 300, 8),
    _row("Aviamentos", "ZIP-011", "Ziper Nylon N5", "branco", 22, "un", "Casa do Ziper", "GAVETA 03", "ziper", "fechamento", "", 50, 300, 8),
    _row("Aviamentos", "LIN-120-PTO", "Linha 120 Poliester", "preto", 14, "un", "Linhas Forte", "GAVETA 08", "linha", "costura", "poliester", 20, 80, 2),
    _row("Aviamentos", "LIN-120-BCA", "Linha 120 Poliester", "branco", 90, "un", "Linhas Forte", "GAVETA 08", "linha", "costura", "poliester", 20, 80, 2),
    _row("Aviamentos", "BOT-18-DOU", "Botao Metal 18mm", "dourado", 500, "un", "Botoes Sul", "GAVETA 12", "botao", "metal", "", 150, 700, 20),
    _row("Aviamentos", "EL-CH-25", "Elastico Chato 25mm", "preto", 3, "rolo", "Elasticos Brasil", "GAVETA 15", "elastico", "acabamento", "", 5, 20, 0.5),
    _row("Aviamentos", "ETQ-GUIMMA", "Etiqueta Composicao Guimma", "branco", 0, "un", "Print Label", "GAVETA 20", "etiqueta", "identificacao", "", 200, 1000, 40),
    _row("Insumos", "SAC-PP-M", "Saco Plastico PP Medio", "transparente", 1200, "un", "Embala Tudo", "RUA G / CAIXA 01", "embalagem", "plastico", "pp", 300, 1500, 60),
    _row("Insumos", "TAG-001", "Tag Papel Kraft", "marrom", 80, "un", "Print Label", "RUA G / CAIXA 03", "tag", "identificacao", "papel", 100, 600, 25),
    _row("Insumos", "COL-SPRAY", "Cola Spray Temporaria", "branco", 4, "un", "Quimica Norte", "ARMARIO QUIMICOS", "cola", "costura", "", 6, 18, 0.4),
    _row("Insumos", "CX-PAP-40", "Caixa Papelao 40x30", "kraft", 30, "un", "Embala Tudo", "RUA H / PILHA 02", "caixa", "papelao", "papelao", 20, 120, 5),
    _row("Escritorio", "RES-A4", "Resma Papel A4", "branco", 2, "un", "Papelaria Central", "ARMARIO ADM", "papel", "escritorio", "papel", 4, 15, 0.4),
    _row("Escritorio", "CAN-AZ", "Caneta Esferografica Azul", "azul", 18, "un", "Papelaria Central", "ARMARIO ADM", "caneta", "escritorio", "", 5, 30, 0.3),
    _row("Escritorio", "TON-HP85", "Toner HP 85A", "preto", 1, "un", "Info Suprimentos", "ARMARIO TI", "toner", "impressao", "", 1, 4, 0.1),
    _row("Limpeza", "ALC-70-5L", "Alcool 70 5L", "transparente", 1, "gl", "Higieniza Pro", "DEPOSITO LIMPEZA", "alcool", "higiene", "", 2, 8, 0.2),
    _row("Limpeza", "PAP-TOLHA", "Papel Toalha Interfolha", "branco", 12, "pct", "Higieniza Pro", "DEPOSITO LIMPEZA", "papel toalha", "higiene", "", 8, 30, 1),
    _row("Limpeza", "SAC-LIXO-100", "Saco de Lixo 100L", "preto", 0, "pct", "LimpMais", "DEPOSITO LIMPEZA", "saco de lixo", "limpeza", "", 3, 12, 0.5),
    _row("Outros", "CAB-PL-PTO", "Cabide Plastico Adulto", "preto", 300, "un", "Cabides Alpha", "RUA I / CAIXA 05", "cabide", "expedicao", "plastico", 100, 500, 15),
    _row("Outros", "ARQ-MORTO", "Arquivo Morto Papel", "kraft", 16, "un", "Papelaria Central", "ARMARIO ADM", "arquivo", "organizacao", "papel", 5, 30, 0.2),
]


@dataclass
class PerguntaTreino:
    pergunta: str
    deve_conter: List[str] = field(default_factory=list)
    nao_deve_conter: List[str] = field(default_factory=lambda: ["nao entendi completamente"])
    intent: Optional[str] = None


RODADAS_TREINO: List[List[PerguntaTreino]] = [
    [
        PerguntaTreino("tem malha canelada?", ["malha canelada"], intent="detalhar_item"),
        PerguntaTreino("e preta?", ["cor preto", "malha canelada"], intent="itens_por_cor"),
        PerguntaTreino("quem fornece?", ["texbrasil"], intent="listar_fornecedores"),
        PerguntaTreino("onde esta guardada?", ["rua a"], intent="listar_locais"),
    ],
    [
        PerguntaTreino("o que temos em tecidos", ["resumo de tecidos", "cores distintas"], intent="resumo_grupo"),
        PerguntaTreino("liste as cores", ["em tecidos", "preto", "azul", "branco"], intent="listar_cores"),
    ],
    [
        PerguntaTreino("tem ziper prto", ["ziper nylon"], intent="detalhar_item"),
        PerguntaTreino("e branco?", ["ziper nylon", "branco"], intent="itens_por_cor"),
        PerguntaTreino("qual o saldo?", ["saldo"], intent="saldo_item"),
    ],
    [
        PerguntaTreino("quais tecidos estao criticos", ["moletom", "oxford", "malha canelada"], intent="itens_criticos"),
        PerguntaTreino("quantos tecidos temos", ["registros", "itens distintos"], intent="contar_grupo"),
        PerguntaTreino("compare tecidos e aviamentos", ["tecidos", "aviamentos"], intent="comparar_grupos"),
    ],
    [
        PerguntaTreino("quais itens estao zerados", ["moletom", "etiqueta", "saco de lixo"], intent="itens_zerados"),
        PerguntaTreino("sugestao de compra de aviamentos", ["repor", "etiqueta"], intent="sugestao_compra"),
        PerguntaTreino("curva abc dos tecidos", ["classe a", "classe b", "classe c"], intent="analise_abc"),
    ],
    [
        PerguntaTreino("onde fica alcool 70", ["deposito limpeza"], intent="listar_locais"),
        PerguntaTreino("quem fornece tag kraft", ["print label"], intent="listar_fornecedores"),
        PerguntaTreino("tem resma a4?", ["resma papel a4"], intent="detalhar_item"),
    ],
    [
        PerguntaTreino("quais itens brancos temos", ["tricoline", "ziper", "resma"], intent="itens_por_cor"),
        PerguntaTreino("itens abaixo de 10 em tecidos", ["moletom", "malha canelada", "ribana"], intent="itens_abaixo"),
        PerguntaTreino("codigo da linha 120", ["lin-120"], intent="codigo_item"),
    ],
    [
        PerguntaTreino("quanto dura linha 120", ["cobertura", "linha 120"], intent="consultar_cobertura"),
        PerguntaTreino("consumo da cola spray", ["consumo", "0,40"], intent="consultar_consumo"),
        PerguntaTreino("projecao de consumo da cola spray", ["saldo projetado"], intent="projecao_consumo"),
    ],
    [
        PerguntaTreino("distribuicao por fornecedor em tecidos", ["texbrasil", "fios nobres"], intent="distribuicao_fornecedores"),
        PerguntaTreino("distribuicao de cores dos tecidos", ["preto", "azul"], intent="distribuicao_cores"),
        PerguntaTreino("itens recentes de limpeza", ["alcool", "papel toalha", "saco de lixo"], intent="itens_recentes"),
    ],
    [
        PerguntaTreino("tem toner hp85?", ["toner hp 85a"], intent="detalhar_item"),
        PerguntaTreino("resumo da conversa", ["toner", "contexto ativo"], intent="resumo_memoria"),
    ],
]


class EstoqueIALab(EstoqueIA):
    def _carregar_memoria_persistente(self) -> None:
        return None

    def _persistir_memoria_persistente(self, snapshot: Dict[str, Any]) -> None:
        return None


def criar_ia_treino(rows: Optional[List[Dict[str, Any]]] = None) -> EstoqueIALab:
    ia = EstoqueIALab()
    dataset = list(rows or ESTOQUE_TREINO)
    ia._base_dataset = lambda: dataset
    return ia


def _norm_static(text: str) -> str:
    text = (text or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("/", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _primeira_palavra(text: str) -> str:
    partes = _norm_static(text).split()
    return partes[0] if partes else ""


def _typo_basico(text: str) -> str:
    trocas = {
        "ziper": "zipr",
        "zíper": "zipr",
        "elastico": "elastco",
        "elástico": "elastco",
        "alcool": "alcol",
        "álcool": "alcol",
        "poliester": "poliestr",
        "poliéster": "poliestr",
        "canelada": "canelda",
        "papel": "papl",
        "fornecedor": "fornecedr",
    }
    out = text
    for certo, errado in trocas.items():
        out = out.replace(certo, errado)
    return out


def _rows_por_grupo(grupo: str) -> List[Dict[str, Any]]:
    return [r for r in ESTOQUE_TREINO if r["grupo_principal"] == grupo]


def gerar_rodadas_rigorosas(seed: int = 7) -> List[List[PerguntaTreino]]:
    rng = random.Random(seed)
    rodadas: List[List[PerguntaTreino]] = []
    grupos = sorted({r["grupo_principal"] for r in ESTOQUE_TREINO})

    for grupo in grupos:
        rows = _rows_por_grupo(grupo)
        if not rows:
            continue
        cores = sorted({r["cor"] for r in rows if r.get("cor")})
        fornecedores = sorted({r["fornecedor"] for r in rows if r.get("fornecedor")})
        criticos = [r for r in rows if float(r.get("saldo_num") or 0) <= float(r.get("estoque_minimo") or 0)]
        zerados = [r for r in rows if float(r.get("saldo_num") or 0) <= 0]
        grupo_l = grupo.lower()

        rodada = [
            PerguntaTreino(f"o que temos em {grupo_l}", [f"resumo de {grupo_l}", "itens distintos"], intent="resumo_grupo"),
            PerguntaTreino("liste as cores", [cores[0].lower()] if cores else [], intent="listar_cores"),
            PerguntaTreino(f"distribuicao por fornecedor em {grupo_l}", [fornecedores[0].lower()] if fornecedores else [], intent="distribuicao_fornecedores"),
        ]
        if criticos:
            rodada.append(PerguntaTreino(f"quais {grupo_l} estao criticos", [criticos[0]["descricao"].lower()], intent="itens_criticos"))
        if zerados:
            rodada.append(PerguntaTreino(f"{grupo_l} zerados", [zerados[0]["descricao"].lower()], intent="itens_zerados"))
        rodadas.append(rodada)

    itens_amostra = list(ESTOQUE_TREINO)
    rng.shuffle(itens_amostra)
    for row in itens_amostra:
        desc = row["descricao"]
        desc_n = _norm_static(desc)
        primeiro = _primeira_palavra(desc)
        fornecedor = row.get("fornecedor", "")
        local = row.get("localizacao", "")
        codigo = row.get("codigo", "")
        cor = row.get("cor", "")
        rodada = [
            PerguntaTreino(f"tem {desc_n}?", [desc_n], intent="detalhar_item"),
            PerguntaTreino("qual o saldo?", ["saldo"], intent="saldo_item"),
            PerguntaTreino("quem fornece?", [fornecedor.lower()] if fornecedor else [], intent="listar_fornecedores"),
            PerguntaTreino("onde fica?", [local.split("/")[0].strip().lower()] if local else [], intent="listar_locais"),
        ]
        if codigo:
            rodada.append(PerguntaTreino(f"codigo de {desc_n}", [codigo.lower()[:5]], intent="codigo_item"))
        if cor:
            rodada.append(PerguntaTreino(f"quais itens {cor.lower()} temos", [desc_n], intent="itens_por_cor"))
        if row.get("consumo_medio"):
            rodada.append(PerguntaTreino(f"quanto dura {desc_n}", [primeiro], intent="consultar_cobertura"))
        rodadas.append(rodada)

        if len(desc_n) >= 8:
            rodadas.append([
                PerguntaTreino(f"procure {_typo_basico(desc_n)}", [primeiro], intent="detalhar_item"),
            ])

    rodadas.extend([
        [
            PerguntaTreino("quais itens abaixo de 5", ["moletom", "etiqueta"], intent="itens_abaixo"),
            PerguntaTreino("quais itens acima de 100", ["saco plastico", "botao"], intent="itens_acima"),
            PerguntaTreino("itens entre 10 e 20", ["linha 120", "caneta"], intent="itens_entre"),
        ],
        [
            PerguntaTreino("analise de risco do estoque", ["sem saldo", "crítico"], intent="analise_risco"),
            PerguntaTreino("sugestao de compra geral", ["repor"], intent="sugestao_compra"),
            PerguntaTreino("curva abc geral", ["classe a", "classe b", "classe c"], intent="analise_abc"),
        ],
        [
            PerguntaTreino("itens por setor", ["deposito", "gaveta"], intent="itens_por_setor_detalhado"),
            PerguntaTreino("inventario completo", ["inventário geral"], intent="listar_todos_itens"),
            PerguntaTreino("itens recentes", ["itens mais recentes"], intent="itens_recentes"),
        ],
    ])

    return rodadas


def gerar_rodadas_massivas(seed: int = 17, minimo_perguntas: int = 1200) -> List[List[PerguntaTreino]]:
    rng = random.Random(seed)
    rodadas: List[List[PerguntaTreino]] = []
    grupos = sorted({r["grupo_principal"] for r in ESTOQUE_TREINO})

    for grupo in grupos:
        grupo_l = grupo.lower()
        rows = _rows_por_grupo(grupo)
        cores = sorted({r["cor"] for r in rows if r.get("cor")})
        fornecedores = sorted({r["fornecedor"] for r in rows if r.get("fornecedor")})
        rodadas.append([
            PerguntaTreino(f"o que temos em {grupo_l}", [f"resumo de {grupo_l}"], intent="resumo_grupo"),
            PerguntaTreino(f"quantos {grupo_l} temos", ["registros", "itens distintos"], intent="contar_grupo"),
            PerguntaTreino("liste as cores", [cores[0].lower()] if cores else [], intent="listar_cores"),
            PerguntaTreino(f"sugestao de compra de {grupo_l}", ["repor"] if rows else [], intent="sugestao_compra"),
            PerguntaTreino(f"o que preciso comprar em {grupo_l}", [], intent="sugestao_compra"),
            PerguntaTreino(f"quero saber so em {grupo_l} quais itens temos que comprar", [], intent="sugestao_compra"),
            PerguntaTreino(f"distribuicao por fornecedor em {grupo_l}", [fornecedores[0].lower()] if fornecedores else [], intent="distribuicao_fornecedores"),
            PerguntaTreino(f"distribuicao de cores dos {grupo_l}", [cores[0].lower()] if cores else [], intent="distribuicao_cores"),
        ])

    itens = list(ESTOQUE_TREINO)
    rng.shuffle(itens)
    total_estimado = sum(len(r) for r in rodadas)
    ciclos_variacao = 0

    while total_estimado < minimo_perguntas:
        ciclos_variacao += 1
        for row in itens:
            desc = row["descricao"]
            desc_n = _norm_static(desc)
            primeiro = _primeira_palavra(desc)
            codigo = row.get("codigo", "")
            codigo_ref = codigo.lower()[:5] if codigo else ""
            fornecedor = row.get("fornecedor", "")
            local = (row.get("localizacao", "").split("/")[0].strip() or row.get("localizacao", "")).lower()
            cor = row.get("cor", "")
            grupo = row.get("grupo_principal", "")
            grupo_l = grupo.lower()
            unidade = row.get("unidade", "un")
            detalhe_variantes = [
                f"tem {desc_n}?",
                f"procure {desc_n}",
                f"buscar {desc_n}",
                f"detalhes de {desc_n}",
                f"resumo de {desc_n}",
                f"produto {desc_n}",
            ]
            saldo_variantes = [
                f"saldo de {desc_n}",
                f"qual o saldo de {desc_n}",
                f"quantidade de {desc_n}",
                f"qtd de {desc_n}",
            ]
            codigo_variantes = [
                f"codigo de {desc_n}",
                f"qual codigo de {desc_n}",
                f"sku de {desc_n}",
            ]
            fornecedor_variantes = [
                f"quem fornece {desc_n}",
                f"fornecedor de {desc_n}",
                f"compramos de quem {desc_n}",
            ]
            local_variantes = [
                f"onde fica {desc_n}",
                f"localizacao de {desc_n}",
                f"onde esta guardado {desc_n}",
            ]

            rodada: List[PerguntaTreino] = []
            rodada.extend(PerguntaTreino(p, [primeiro], intent="detalhar_item") for p in detalhe_variantes)
            rodada.extend(PerguntaTreino(p, ["saldo"], intent="saldo_item") for p in saldo_variantes)
            if codigo_ref:
                rodada.extend(PerguntaTreino(p, [codigo_ref], intent="codigo_item") for p in codigo_variantes)
            if fornecedor:
                rodada.extend(PerguntaTreino(p, [fornecedor.lower()], intent="listar_fornecedores") for p in fornecedor_variantes)
            if local:
                rodada.extend(PerguntaTreino(p, [local], intent="listar_locais") for p in local_variantes)
            if cor:
                rodada.extend([
                    PerguntaTreino(f"quais itens {cor.lower()} temos", ["saldo total"], intent="itens_por_cor"),
                    PerguntaTreino(f"itens da cor {cor.lower()} em {grupo_l}", ["saldo total"], intent="itens_por_cor"),
                    PerguntaTreino(f"total em {unidade} da cor {cor.lower()} em {grupo_l}", ["saldo total"], intent="itens_por_cor"),
                    PerguntaTreino(f"some todos os {cor.lower()} em {grupo_l}", ["saldo total"], intent="itens_por_cor"),
                ])
            if row.get("consumo_medio"):
                rodada.append(PerguntaTreino(f"quanto dura {desc_n}", [primeiro], intent="consultar_cobertura"))
                rodada.append(PerguntaTreino(f"projecao de consumo de {desc_n}", ["saldo projetado"], intent="projecao_consumo"))
            if ciclos_variacao % 2 == 0 and len(desc_n) >= 8:
                rodada.append(PerguntaTreino(f"tem {_typo_basico(desc_n)}?", [primeiro], intent="detalhar_item"))

            rodadas.append(rodada)
            total_estimado += len(rodada)
            if total_estimado >= minimo_perguntas:
                break

    rodadas.append([
        PerguntaTreino("o que temos de escritorio", ["resumo de escritorio"], intent="resumo_grupo"),
        PerguntaTreino("o que preciso comprar", ["repor"], intent="sugestao_compra"),
        PerguntaTreino("so em escritorio", [], intent="sugestao_compra"),
        PerguntaTreino("o que precisamos compra para escritorio", [], intent="sugestao_compra"),
        PerguntaTreino("quero saber so em escritorio quais itens temos que comprar", [], intent="sugestao_compra"),
    ])
    rodadas.append([
        PerguntaTreino("quantos metros temos de tecido azul", ["saldo total", "m"], intent="itens_por_cor"),
        PerguntaTreino("no tatal de metros", ["saldo total", "m"], intent="itens_por_cor"),
        PerguntaTreino("no total de metros", ["saldo total", "m"], intent="itens_por_cor"),
        PerguntaTreino("total em metros de tecido azul", ["saldo total", "m"], intent="itens_por_cor"),
        PerguntaTreino("some todos os azuis", ["saldo total", "m"], intent="itens_por_cor"),
    ])

    return rodadas


def executar_rodadas(
    rodadas: Optional[Iterable[Iterable[PerguntaTreino]]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    total = 0
    falhas: List[Dict[str, Any]] = []
    transcricao: List[Dict[str, Any]] = []
    latencias_ms: List[float] = []
    por_intent: Dict[str, int] = {}

    for numero, rodada in enumerate(rodadas or RODADAS_TREINO, start=1):
        ia = criar_ia_treino()
        for caso in rodada:
            total += 1
            entidades = ia._extract_entities(caso.pergunta)
            intent, conf = ia._detect_intent(caso.pergunta, entidades)
            inicio = time.perf_counter()
            resposta = ia.responder(caso.pergunta)
            latencia_ms = (time.perf_counter() - inicio) * 1000
            latencias_ms.append(latencia_ms)
            por_intent[intent or "indefinido"] = por_intent.get(intent or "indefinido", 0) + 1
            resposta_norm = ia._normalize(resposta)

            erros: List[str] = []
            if caso.intent and intent != caso.intent:
                erros.append(f"intent esperado {caso.intent}, obtido {intent} ({conf:.2f})")
            for trecho in caso.deve_conter:
                if ia._normalize(trecho) not in resposta_norm:
                    erros.append(f"faltou trecho: {trecho}")
            for trecho in caso.nao_deve_conter:
                if ia._normalize(trecho) in resposta_norm:
                    erros.append(f"trecho proibido apareceu: {trecho}")

            registro = {
                "rodada": numero,
                "pergunta": caso.pergunta,
                "intent": intent,
                "confianca": conf,
                "latencia_ms": round(latencia_ms, 3),
                "resposta": resposta,
                "erros": erros,
            }
            transcricao.append(registro)
            if erros:
                falhas.append(registro)
            if verbose:
                status = "OK" if not erros else "FALHA"
                print(f"[{status}] R{numero} {caso.pergunta} -> {intent} ({conf:.2f})")
                if erros:
                    for erro in erros:
                        print(f"  - {erro}")
                print("  " + resposta.replace("\n", "\n  "))

    return {
        "total": total,
        "ok": total - len(falhas),
        "falhas": falhas,
        "transcricao": transcricao,
        "latencia_ms_media": round(statistics.mean(latencias_ms), 3) if latencias_ms else 0,
        "latencia_ms_p95": round(statistics.quantiles(latencias_ms, n=20)[18], 3) if len(latencias_ms) >= 20 else round(max(latencias_ms or [0]), 3),
        "por_intent": dict(sorted(por_intent.items())),
    }


def executar_treino_prolongado(
    duracao_segundos: int,
    seed: int = 7,
    verbose: bool = False,
    relatorio_json: Optional[str] = None,
) -> Dict[str, Any]:
    inicio = time.time()
    ciclos = 0
    total = 0
    ok = 0
    falhas: List[Dict[str, Any]] = []
    latencias: List[float] = []
    pior_resposta_ms = 0.0
    rodadas = [*RODADAS_TREINO, *gerar_rodadas_rigorosas(seed=seed)]

    while time.time() - inicio < duracao_segundos:
        ciclos += 1
        resultado = executar_rodadas(rodadas=rodadas, verbose=False)
        total += resultado["total"]
        ok += resultado["ok"]
        falhas.extend(resultado["falhas"])
        latencias.extend(r["latencia_ms"] for r in resultado["transcricao"])
        pior_resposta_ms = max(pior_resposta_ms, *(r["latencia_ms"] for r in resultado["transcricao"]))
        if verbose:
            decorrido = int(time.time() - inicio)
            taxa = (ok / total * 100) if total else 0
            print(f"[TREINO] ciclo={ciclos} tempo={decorrido}s acerto={taxa:.2f}% total={total} falhas={len(falhas)}")
        if falhas and len(falhas) > 25:
            break

    resumo = {
        "duracao_solicitada_segundos": duracao_segundos,
        "duracao_real_segundos": round(time.time() - inicio, 2),
        "ciclos": ciclos,
        "total": total,
        "ok": ok,
        "falhas": falhas[:50],
        "acerto_pct": round((ok / total * 100) if total else 0, 3),
        "latencia_ms_media": round(statistics.mean(latencias), 3) if latencias else 0,
        "latencia_ms_p95": round(statistics.quantiles(latencias, n=20)[18], 3) if len(latencias) >= 20 else round(max(latencias or [0]), 3),
        "latencia_ms_max": round(pior_resposta_ms, 3),
        "rodadas_por_ciclo": len(rodadas),
    }
    if relatorio_json:
        path = Path(relatorio_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    return resumo


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Laboratorio da IA de estoque")
    parser.add_argument("--rigoroso", action="store_true", help="Inclui rodadas geradas automaticamente.")
    parser.add_argument("--massivo", action="store_true", help="Executa mais de 1000 perguntas variadas.")
    parser.add_argument("--minimo-perguntas", type=int, default=1200, help="Quantidade minima para o modo massivo.")
    parser.add_argument("--duracao-segundos", type=int, default=0, help="Executa treino prolongado pelo tempo informado.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--json", default="")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.duracao_segundos > 0:
        resultado = executar_treino_prolongado(
            duracao_segundos=args.duracao_segundos,
            seed=args.seed,
            verbose=not args.quiet,
            relatorio_json=args.json or None,
        )
        print("")
        print(
            "Resumo treino prolongado: "
            f"{resultado['ok']}/{resultado['total']} OK "
            f"({resultado['acerto_pct']}%), ciclos={resultado['ciclos']}, "
            f"p95={resultado['latencia_ms_p95']}ms"
        )
        if resultado["falhas"]:
            print("Falhas:")
            for falha in resultado["falhas"][:20]:
                print(f"- R{falha['rodada']} {falha['pergunta']}: {'; '.join(falha['erros'])}")
            return 1
        return 0

    if args.massivo:
        rodadas = [
            *RODADAS_TREINO,
            *gerar_rodadas_rigorosas(seed=args.seed),
            *gerar_rodadas_massivas(seed=args.seed + 10, minimo_perguntas=args.minimo_perguntas),
        ]
    elif args.rigoroso:
        rodadas = [*RODADAS_TREINO, *gerar_rodadas_rigorosas(seed=args.seed)]
    else:
        rodadas = RODADAS_TREINO
    resultado = executar_rodadas(rodadas=rodadas, verbose=not args.quiet)
    print("")
    print(
        f"Resumo IA estoque: {resultado['ok']}/{resultado['total']} perguntas OK "
        f"| média {resultado['latencia_ms_media']}ms | p95 {resultado['latencia_ms_p95']}ms"
    )
    if resultado["falhas"]:
        print("Falhas:")
        for falha in resultado["falhas"]:
            print(f"- R{falha['rodada']} {falha['pergunta']}: {'; '.join(falha['erros'])}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
