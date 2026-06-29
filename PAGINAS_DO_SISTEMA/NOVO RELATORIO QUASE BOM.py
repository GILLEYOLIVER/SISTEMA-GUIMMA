# -*- coding: utf-8 -*-
"""
RELATORIO_ESTOQUE.py — versão COMPLETA com IA MEGA + UI conversacional
- Integração com BANCO_DE_DADOS_PG (PostgreSQL)
- UI com abas: 📋 Relatório | 📊 Análise | 🤖 Assistente
- IA MEGA (40+ intenções, centenas de variações, análises ricas)
- SISTEMA DE CLASSIFICAÇÃO DE CRITICIDADE POR GRUPO
- SUGESTÕES DE COMPRA AUTOMÁTICAS

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


# ==============================================================================
# CLASSE ESTOQUE IA - VERSÃO COM CLASSIFICAÇÃO DE CRITICIDADE
# ==============================================================================
class EstoqueIA:
    # ------------------------------------------------------------------
    # TABELAS REAIS
    # ------------------------------------------------------------------
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
        "Aviamentos": ["aviamento", "aviamentos", "ziper", "zíper", "linha", "botao", "botão", "elastico", "elástico",
                       "agulha", "etiqueta"],
        "Insumos": ["insumo", "insumos"],
        "Escritorio": ["escritorio", "escritório", "papel", "caneta", "toner", "clip", "clipe", "grampeador"],
        "Limpeza": ["limpeza", "detergente", "sabao", "sabão", "alcool", "álcool", "pano", "vassoura"],
        "Outros": ["outro", "outros", "diversos", "geral"],
    }

    # ------------------------------------------------------------------
    # REGRAS DE CRITICIDADE POR GRUPO
    # ------------------------------------------------------------------
    REGRAS_CRITICIDADE = {
        "Tecidos": {
            "critico_percentual": 20,  # <= 20% do ideal
            "baixo_percentual": 40,  # <= 40% do ideal
            "usa_metros_primario": True,  # prioriza metros
            "cor_critico": "#EF4444",
            "cor_baixo": "#F59E0B",
            "cor_normal": "#10B981",
            "mensagem": "Tecidos com estoque baixo podem atrasar a produção. Recomendamos compra planejada."
        },
        "Aviamentos": {
            "critico_percentual": 30,
            "baixo_percentual": 50,
            "usa_metros_primario": False,
            "cor_critico": "#EF4444",
            "cor_baixo": "#F59E0B",
            "cor_normal": "#10B981",
            "mensagem": "Aviamentos são itens de alto giro. Mantenha estoque para não parar a linha."
        },
        "Insumos": {
            "critico_percentual": 30,
            "baixo_percentual": 50,
            "usa_metros_primario": False,
            "cor_critico": "#EF4444",
            "cor_baixo": "#F59E0B",
            "cor_normal": "#10B981",
            "mensagem": "Insumos essenciais para produção. Verifique regularmente."
        },
        "Escritorio": {
            "critico_percentual": 15,
            "baixo_percentual": 35,
            "usa_metros_primario": False,
            "cor_critico": "#EF4444",
            "cor_baixo": "#F59E0B",
            "cor_normal": "#10B981",
            "mensagem": "Materiais administrativos. Reposição pode ser agendada."
        },
        "Limpeza": {
            "critico_percentual": 20,
            "baixo_percentual": 40,
            "usa_metros_primario": False,
            "cor_critico": "#EF4444",
            "cor_baixo": "#F59E0B",
            "cor_normal": "#10B981",
            "mensagem": "Produtos de limpeza têm consumo constante. Planeje compras mensais."
        },
        "Outros": {
            "critico_percentual": 25,
            "baixo_percentual": 50,
            "usa_metros_primario": False,
            "cor_critico": "#EF4444",
            "cor_baixo": "#F59E0B",
            "cor_normal": "#10B981",
            "mensagem": "Itens diversos. Avalie necessidade conforme demanda."
        }
    }

    # Regra geral (fallback)
    REGRA_GERAL = {
        "critico_percentual": 30,
        "baixo_percentual": 50,
        "usa_metros_primario": False,
        "cor_critico": "#EF4444",
        "cor_baixo": "#F59E0B",
        "cor_normal": "#10B981",
        "mensagem": "Mantenha estoque acima de 50% do ideal para evitar rupturas."
    }

    # Palavras que indicam continuação do último tópico
    CONTINUATION_WORDS = {
        "quais", "quais?", "liste", "liste-os", "liste-os?", "eles", "elas", "esses", "essas",
        "os", "as", "mostre", "mostra", "nomes", "liste eles", "liste os nomes", "e quais", "e os nomes",
        "detalhes", "mais", "próximos", "próxima", "anterior", "voltar", "página", "pagina"
    }

    # ------------------------------------------------------------------
    # DICIONÁRIO GIGANTE DE INTENÇÕES (COMPLETO)
    # ------------------------------------------------------------------
    INTENCOES_ESTOQUE = {
        "saudacao": [
            "oi", "olá", "ola", "opa", "e ai", "ei", "bom dia", "boa tarde", "boa noite",
            "fala", "fala comigo", "ola assistente", "oi assistente", "preciso de ajuda",
            "quero consultar o estoque", "vamos consultar o estoque", "abrir estoque",
            "me ajude com o estoque", "quero ver o estoque", "preciso saber do estoque",
            "ola tudo bem", "oi tudo bem", "como vai", "vamos conversar"
        ],
        "despedida": [
            "tchau", "até logo", "ate logo", "obrigado", "obrigada", "valeu", "encerrar",
            "finalizar", "fechar", "pode parar", "é só isso", "era isso", "fim",
            "encerrar atendimento", "parar consulta", "sair", "obg", "vlw", "falou"
        ],
        "ajuda": [
            "ajuda", "o que você faz", "como funciona", "o que posso perguntar",
            "quais perguntas posso fazer", "me dê exemplos", "me de exemplos",
            "como consultar", "como pesquisar", "como buscar", "me mostre comandos",
            "me mostre exemplos", "o que você entende", "quais consultas você faz",
            "me explique", "quero saber como usar", "me orientar", "como falar com você",
            "que tipo de pergunta posso fazer", "quais tipos de consulta voce entende"
        ],
        "limpar_contexto": [
            "limpar contexto", "limpar conversa", "esquecer assunto", "mudar de assunto",
            "zerar contexto", "reiniciar consulta", "reiniciar conversa", "novo assunto",
            "não é disso que estou falando", "nao e disso que estou falando", "esquece isso",
            "vamos falar de outra coisa", "apagar filtros", "limpar filtros", "zerar filtros",
            "começar do zero", "comecar do zero", "limpar memoria"
        ],
        "confirmacao": [
            "sim", "isso", "isso mesmo", "correto", "certo", "exato", "pode ser",
            "ok", "beleza", "isso ai", "é isso", "e isso", "confirma", "confirmado",
            "perfeito", "ta certo", "está certo", "pode seguir"
        ],
        "negacao": [
            "não", "nao", "nunca", "errado", "não é isso", "nao e isso", "não quero isso",
            "nao quero isso", "não era isso", "nao era isso", "cancela", "cancelar",
            "deixa", "deixa pra la", "deixa pra lá", "para", "pare", "não precisa"
        ],
        "quantidade_total_itens": [
            "quantos itens temos",
            "quantos itens tem no estoque",
            "quantos produtos temos",
            "qual o total de itens",
            "qual o total do estoque",
            "quantidade total do estoque",
            "total de produtos cadastrados",
            "há quantos itens no estoque",
            "existem quantos itens no estoque",
            "me diga quantos itens temos",
            "me fala quantos itens temos",
            "quantos registros existem",
            "qual a quantidade total de itens",
            "qual o número total de itens",
            "numero total de itens",
            "número total de itens",
            "total geral do estoque",
            "quantidade geral do estoque",
            "total de cadastros no estoque",
            "quantos materiais temos",
            "quantos itens existem no sistema",
            "qual a soma total dos itens"
        ],
        "quantidade_total_pecas": [
            "quantas peças temos",
            "quantas pecas temos",
            "quantidade total de peças",
            "quantidade total de pecas",
            "quantas unidades temos",
            "total de unidades",
            "quantidade total em unidades",
            "somando tudo quantas unidades temos",
            "quantidade total de produtos em unidades",
            "total em peças"
        ],
        "quantidade_total_metros": [
            "quantos metros temos",
            "total de metros",
            "quantidade total em metros",
            "somar metragem",
            "metragem total",
            "total de tecido em metros",
            "quantos metros há no estoque",
            "quantos metros existem",
            "soma dos metros",
            "quanto temos em metragem",
            "metragem geral"
        ],
        "quantidade_total_kilos": [
            "quantos kilos temos",
            "quantos quilos temos",
            "total em kilos",
            "total em quilos",
            "quantidade total em kilos",
            "quantidade total em quilos",
            "somar kilos",
            "somar quilos",
            "peso total",
            "total em peso"
        ],
        "quantidade_por_grupo_tecidos": [
            "quantos tecidos temos",
            "quantos itens de tecido temos",
            "quantos tecidos existem",
            "qual o total de tecidos",
            "total de tecidos",
            "quantidade de tecidos cadastrados",
            "tem quantos tecidos",
            "me diga quantos tecidos temos",
            "me fala quantos tecidos temos",
            "quantos tecidos há",
            "numero de tecidos",
            "número de tecidos",
            "quantidade de tecido no estoque",
            "total de itens da categoria tecidos",
            "quantos produtos de tecido temos",
            "quantos artigos de tecido temos"
        ],
        "quantidade_por_grupo_aviamentos": [
            "quantos aviamentos temos",
            "qual o total de aviamentos",
            "quantidade de aviamentos",
            "tem quantos aviamentos",
            "quantos aviamentos existem",
            "me diga quantos aviamentos temos",
            "número de aviamentos",
            "numero de aviamentos",
            "total de itens de aviamento",
            "quantos produtos de aviamento temos"
        ],
        "quantidade_por_grupo_insumos": [
            "quantos insumos temos",
            "qual o total de insumos",
            "quantidade de insumos",
            "tem quantos insumos",
            "quantos insumos existem",
            "me diga quantos insumos temos",
            "numero de insumos",
            "número de insumos",
            "total de itens de insumos"
        ],
        "quantidade_por_grupo_escritorio": [
            "quantos itens de escritorio temos",
            "quantos materiais de escritorio temos",
            "qual o total de escritorio",
            "quantidade de escritorio",
            "itens de escritório",
            "materiais de escritório",
            "tem quantos itens de escritório",
            "quantos produtos de escritório temos",
            "total de materiais de escritório"
        ],
        "quantidade_por_grupo_limpeza": [
            "quantos itens de limpeza temos",
            "quantos produtos de limpeza temos",
            "qual o total de limpeza",
            "quantidade de limpeza",
            "tem quantos itens de limpeza",
            "quantos materiais de limpeza temos",
            "total de produtos de limpeza"
        ],
        "quantidade_por_grupo_outros": [
            "quantos itens em outros temos",
            "qual o total de outros",
            "quantidade de outros",
            "tem quantos em outros",
            "quantos itens diversos temos",
            "total de itens diversos",
            "quantos produtos diversos temos"
        ],
        "listar_itens_geral": [
            "quais itens temos",
            "liste os itens",
            "mostrar itens",
            "mostre os itens",
            "listar estoque",
            "listar produtos",
            "quais produtos temos",
            "o que temos no estoque",
            "me mostra o estoque",
            "me mostre os produtos",
            "quero ver os itens",
            "traga os itens",
            "listar tudo",
            "mostrar tudo",
            "quais materiais temos",
            "quero a lista do estoque",
            "lista completa do estoque",
            "liste todos os itens",
            "mostre todo o estoque",
            "quais artigos temos"
        ],
        "listar_tecidos": [
            "quais tecidos temos",
            "liste os tecidos",
            "mostrar tecidos",
            "mostre os tecidos",
            "quero ver os tecidos",
            "lista de tecidos",
            "listar tecidos",
            "o que temos de tecido",
            "quais tipos de tecido temos",
            "me mostra os tecidos",
            "traga os tecidos cadastrados",
            "quais artigos de tecido temos",
            "mostre os artigos de tecido"
        ],
        "listar_aviamentos": [
            "quais aviamentos temos",
            "liste os aviamentos",
            "mostrar aviamentos",
            "mostre os aviamentos",
            "quero ver os aviamentos",
            "lista de aviamentos",
            "listar aviamentos",
            "o que temos de aviamento"
        ],
        "listar_insumos": [
            "quais insumos temos",
            "liste os insumos",
            "mostrar insumos",
            "mostre os insumos",
            "lista de insumos",
            "listar insumos",
            "o que temos de insumo"
        ],
        "listar_escritorio": [
            "quais materiais de escritorio temos",
            "liste os itens de escritorio",
            "mostrar itens de escritorio",
            "mostre os materiais de escritorio",
            "lista de escritorio",
            "listar escritorio",
            "o que temos de escritorio"
        ],
        "listar_limpeza": [
            "quais itens de limpeza temos",
            "liste os itens de limpeza",
            "mostrar limpeza",
            "mostre os produtos de limpeza",
            "lista de limpeza",
            "listar limpeza",
            "o que temos de limpeza"
        ],
        "listar_outros": [
            "quais itens diversos temos",
            "liste outros itens",
            "mostrar outros",
            "mostre itens diversos",
            "lista de outros",
            "listar outros",
            "o que temos em outros"
        ],
        "listar_por_categoria": [
            "liste os itens por categoria",
            "mostrar itens por categoria",
            "agrupar por categoria",
            "quais itens temos por categoria",
            "lista por categoria",
            "mostrar categorias com itens",
            "separar itens por categoria"
        ],
        "listar_por_tipo": [
            "liste por tipo",
            "mostrar por tipo",
            "agrupar por tipo",
            "quais tipos temos",
            "lista por tipo",
            "separar por tipo",
            "mostrar itens por tipo"
        ],
        "listar_por_fornecedor": [
            "liste por fornecedor",
            "mostrar por fornecedor",
            "agrupar por fornecedor",
            "quais itens temos por fornecedor",
            "lista por fornecedor",
            "separar por fornecedor",
            "mostrar produtos por fornecedor"
        ],
        "listar_por_cor": [
            "liste por cor",
            "mostrar por cor",
            "agrupar por cor",
            "quais itens temos por cor",
            "lista por cor",
            "separar por cor",
            "mostrar produtos por cor"
        ],
        "listar_por_localizacao": [
            "liste por localização",
            "liste por localizacao",
            "mostrar por localização",
            "mostrar por localizacao",
            "agrupar por localização",
            "agrupar por localizacao",
            "quais itens temos por local",
            "lista por local",
            "mostrar produtos por local"
        ],
        "buscar_codigo": [
            "codigo 4545",
            "código 4545",
            "qual item é o codigo 4545",
            "qual item é o código 4545",
            "de que é o codigo 4545",
            "de que é o código 4545",
            "o que é o codigo 4545",
            "o que é o código 4545",
            "buscar código 4545",
            "buscar codigo 4545",
            "procurar código 4545",
            "procurar codigo 4545",
            "mostrar item do código 4545",
            "mostrar item do codigo 4545",
            "me diga o item do código 4545",
            "me diga o item do codigo 4545",
            "qual produto é o código 4545",
            "qual produto é o codigo 4545",
            "que item é o 4545",
            "o que significa o código 4545",
            "me fale sobre o codigo 4545",
            "qual artigo é o codigo 4545"
        ],
        "buscar_descricao": [
            "buscar por descrição",
            "buscar por descricao",
            "procurar item pela descrição",
            "procurar item pela descricao",
            "achar item pelo nome",
            "buscar produto pelo nome",
            "quero procurar pela descrição",
            "pesquisar descrição",
            "pesquisar descricao",
            "buscar item pelo texto",
            "achar artigo pelo nome",
            "procurar tecido pelo nome"
        ],
        "buscar_texto_livre": [
            "procure ziper",
            "buscar algodao",
            "buscar algodão",
            "procurar cetim",
            "achar linha",
            "buscar botão",
            "buscar botao",
            "procurar elástico",
            "procurar elastico",
            "quero achar um item",
            "me mostra itens que contenham",
            "pesquisar por palavra",
            "buscar por palavra",
            "procurar artigo"
        ],
        "buscar_exata": [
            "buscar exatamente",
            "busca exata",
            "procure exatamente esse nome",
            "pesquisa exata",
            "correspondência exata",
            "correspondencia exata"
        ],
        "buscar_aproximada": [
            "mesmo se estiver escrito errado",
            "considera erro de digitação",
            "considere erro de digitacao",
            "procure parecido",
            "busca aproximada",
            "pesquisa aproximada",
            "achar nome parecido",
            "procure mesmo com erro",
            "considere escrita errada"
        ],
        "detalhar_item": [
            "me dê detalhes do item",
            "me de detalhes do item",
            "mostrar detalhes",
            "ver detalhes do produto",
            "detalhar esse item",
            "quero os dados completos desse item",
            "fale mais sobre esse item",
            "abrir detalhes do item",
            "mostrar informacoes completas",
            "mostrar informações completas"
        ],
        "localizacao_item": [
            "onde está o código 4545",
            "onde está o item",
            "onde fica esse item",
            "qual a localização do código 4545",
            "qual a localizacao do codigo 4545",
            "qual a localização do item",
            "qual a localizacao do item",
            "em que local está",
            "em que localizacao está",
            "em que localização está",
            "qual depósito está",
            "qual deposito está",
            "qual prateleira está",
            "onde encontro esse item",
            "me diga a localização",
            "onde esta guardado"
        ],
        "fornecedor_item": [
            "qual o fornecedor desse item",
            "quem fornece esse item",
            "fornecedor do código 4545",
            "fornecedor do codigo 4545",
            "de quem compramos esse item",
            "quem vende esse item",
            "me diga o fornecedor"
        ],
        "cor_item": [
            "qual a cor desse item",
            "cor do código 4545",
            "cor do codigo 4545",
            "esse item é de que cor",
            "me diga a cor desse produto",
            "qual cor está cadastrada"
        ],
        "categoria_item": [
            "qual a categoria desse item",
            "categoria do código 4545",
            "categoria do codigo 4545",
            "esse item é de qual categoria",
            "me diga a categoria desse produto"
        ],
        "tipo_item": [
            "qual o tipo desse item",
            "tipo do código 4545",
            "tipo do codigo 4545",
            "esse item é de qual tipo",
            "me diga o tipo desse produto"
        ],
        "unidade_item": [
            "qual a unidade desse item",
            "esse item é contado em que unidade",
            "unidade do código 4545",
            "unidade do codigo 4545",
            "é em metros ou unidades",
            "me diga a unidade"
        ],
        "valor_unitario_item": [
            "qual o valor unitário desse item",
            "qual o valor unitario desse item",
            "valor do código 4545",
            "valor do codigo 4545",
            "quanto custa esse item",
            "preço desse item",
            "preco desse item",
            "valor por unidade"
        ],
        "data_entrada_item": [
            "quando esse item entrou",
            "data de entrada do item",
            "quando foi cadastrado",
            "qual a data de entrada",
            "quando esse produto chegou",
            "quando deu entrada"
        ],
        "observacoes_item": [
            "qual a observação desse item",
            "qual a observacao desse item",
            "mostrar observações",
            "mostrar observacoes",
            "tem observação",
            "tem observacao",
            "o que está nas observações",
            "o que está nas observacoes"
        ],
        "itens_criticos": [
            "itens críticos",
            "itens criticos",
            "quais itens estão críticos",
            "quais itens estão criticos",
            "o que está acabando",
            "o que esta acabando",
            "quais produtos estão acabando",
            "quais produtos estao acabando",
            "itens com estoque baixo",
            "mostrar itens críticos",
            "mostrar itens criticos",
            "quais estão abaixo do mínimo",
            "quais estão abaixo do minimo",
            "quais precisam repor",
            "o que precisa repor",
            "itens abaixo do limite",
            "estoque baixo",
            "quais estão faltando",
            "quais artigos estão acabando"
        ],
        "itens_zerados": [
            "quais itens estão zerados",
            "quais itens estao zerados",
            "itens sem estoque",
            "produtos sem estoque",
            "o que está zerado",
            "o que esta zerado",
            "quais itens acabaram",
            "quais produtos acabaram",
            "mostrar itens zerados"
        ],
        "itens_positivos": [
            "quais itens ainda temos",
            "mostrar itens com saldo",
            "mostrar itens disponíveis",
            "mostrar itens disponiveis",
            "quais produtos estão disponíveis",
            "quais produtos estao disponiveis",
            "itens com estoque",
            "produtos com estoque"
        ],
        "maior_quantidade": [
            "qual item tem mais quantidade",
            "qual item tem maior quantidade",
            "quais têm mais",
            "quais tem mais",
            "qual deles tem maior quantidade",
            "mostre os maiores saldos",
            "quais são os itens com maior estoque",
            "quais sao os itens com maior estoque",
            "top itens com mais estoque",
            "o que mais temos",
            "qual tem mais",
            "qual produto lidera em quantidade",
            "qual tecido tem mais metros",
            "qual item está com maior saldo",
            "maiores quantidades",
            "qual artigo tem mais"
        ],
        "menor_quantidade": [
            "qual item tem menos quantidade",
            "qual item tem menor quantidade",
            "quais têm menos",
            "quais tem menos",
            "qual deles tem menor quantidade",
            "mostre os menores saldos",
            "quais são os itens com menor estoque",
            "quais sao os itens com menor estoque",
            "o que menos temos",
            "qual tem menos",
            "qual tecido tem menos metros",
            "qual item está com menor saldo",
            "menores quantidades"
        ],
        "top_10_maiores": [
            "top 10 maiores",
            "top 10 por quantidade",
            "top 10 com maior quantidade",
            "10 itens com mais estoque",
            "dez itens com mais estoque",
            "ranking dos maiores",
            "top dez maiores",
            "mostrar top 10 do estoque"
        ],
        "top_10_menores": [
            "top 10 menores",
            "top 10 com menor quantidade",
            "10 itens com menos estoque",
            "dez itens com menos estoque",
            "ranking dos menores",
            "top dez menores",
            "mostrar top 10 dos menores"
        ],
        "ordenar_crescente": [
            "ordene do menor para o maior",
            "ordem crescente",
            "crescente",
            "mostrar crescente",
            "organizar do menor para o maior",
            "classificar crescente"
        ],
        "ordenar_decrescente": [
            "ordene do maior para o menor",
            "ordem decrescente",
            "decrescente",
            "mostrar decrescente",
            "organizar do maior para o menor",
            "classificar decrescente"
        ],
        "quantidade_tecidos_metros": [
            "quantos metros temos de tecido",
            "quantos metros temos em tecidos",
            "total de metros de tecido",
            "somar metragem dos tecidos",
            "somar metros dos tecidos",
            "quantidade total em metros dos tecidos",
            "me diga quantos metros de tecido temos",
            "metragem total dos tecidos",
            "qual a metragem total",
            "quantos metros há de tecidos",
            "metros de tecido no estoque",
            "total de tecido em metro",
            "quanto temos de tecido em metros"
        ],
        "quantidade_tecidos_kilos": [
            "quantos kilos temos de tecido",
            "quantos quilos temos de tecido",
            "total em kilos dos tecidos",
            "total em quilos dos tecidos",
            "somar kilos de tecido",
            "somar quilos de tecido",
            "quantidade total em kilos de tecidos",
            "quantidade total em quilos de tecidos"
        ],
        "listar_tecidos_por_tipo": [
            "quais tipos de tecido temos",
            "listar tecidos por tipo",
            "mostrar tecidos por tipo",
            "agrupar tecidos por tipo",
            "me diga os tipos de tecido",
            "quais categorias de tecido temos"
        ],
        "listar_itens_categoria_especifica": [
            "liste os itens de aviamentos",
            "liste os itens de tecidos",
            "liste os itens de insumos",
            "liste os itens de limpeza",
            "liste os itens de escritorio",
            "liste os itens de escritório",
            "liste os itens de outros",
            "mostrar itens da categoria tecidos",
            "mostrar itens da categoria aviamentos",
            "mostrar itens da categoria insumos",
            "mostrar itens da categoria limpeza"
        ],
        "filtrar_por_fornecedor": [
            "quais itens são do fornecedor x",
            "quais itens sao do fornecedor x",
            "listar itens do fornecedor x",
            "mostrar itens do fornecedor x",
            "o que temos do fornecedor x",
            "quais produtos vieram do fornecedor x",
            "filtrar por fornecedor",
            "somente do fornecedor",
            "me mostra só do fornecedor",
            "me mostra so do fornecedor"
        ],
        "filtrar_por_cor": [
            "quais itens temos na cor azul",
            "liste os tecidos azuis",
            "o que temos da cor preta",
            "mostrar itens vermelhos",
            "filtrar por cor",
            "somente itens azuis",
            "só os pretos",
            "so os pretos",
            "quero ver os brancos",
            "me mostre os itens da cor"
        ],
        "filtrar_por_localizacao": [
            "quais itens estão no deposito 1",
            "quais itens estao no deposito 1",
            "mostrar itens da prateleira a",
            "filtrar por localização",
            "filtrar por localizacao",
            "somente itens desse local",
            "itens desse depósito",
            "itens desse deposito",
            "o que tem nesse local"
        ],
        "filtrar_por_tipo": [
            "filtrar por tipo",
            "somente desse tipo",
            "quero ver só desse tipo",
            "quero ver so desse tipo",
            "me mostra apenas esse tipo",
            "filtrar itens pelo tipo"
        ],
        "filtrar_por_categoria": [
            "filtrar por categoria",
            "somente dessa categoria",
            "quero ver só dessa categoria",
            "quero ver so dessa categoria",
            "me mostra apenas essa categoria",
            "filtrar itens pela categoria"
        ],
        "filtrar_por_data": [
            "itens de hoje",
            "itens de ontem",
            "itens dessa semana",
            "itens deste mês",
            "itens deste mes",
            "itens do mês passado",
            "itens do mes passado",
            "entradas recentes",
            "mostrar itens por data",
            "filtrar por data"
        ],
        "entradas_recentes": [
            "quais foram as últimas entradas",
            "quais foram as ultimas entradas",
            "mostrar entradas recentes",
            "últimos itens cadastrados",
            "ultimos itens cadastrados",
            "itens cadastrados recentemente",
            "o que entrou por último",
            "o que entrou por ultimo",
            "últimos lançamentos",
            "ultimos lançamentos"
        ],
        "entradas_antigas": [
            "quais são as entradas mais antigas",
            "quais sao as entradas mais antigas",
            "mostrar os itens mais antigos",
            "itens cadastrados há mais tempo",
            "o que entrou primeiro",
            "entradas antigas"
        ],
        "valor_total_estoque": [
            "qual o valor total do estoque",
            "quanto vale o estoque",
            "valor total dos itens",
            "qual o custo total do estoque",
            "quanto temos em estoque em valor",
            "soma do valor do estoque",
            "valor geral do estoque",
            "quanto representa o estoque",
            "qual o montante do estoque",
            "quanto vale tudo que temos",
            "quanto da em valor o estoque inteiro"
        ],
        "valor_por_categoria": [
            "qual o valor dos tecidos",
            "qual o valor dos aviamentos",
            "qual o valor dos insumos",
            "qual o valor da limpeza",
            "qual o valor do escritorio",
            "qual o valor do escritório",
            "valor por categoria",
            "quanto vale cada categoria",
            "mostrar o valor por grupo",
            "soma de valor por categoria"
        ],
        "valor_por_item": [
            "quanto vale esse item",
            "valor desse item",
            "qual o valor desse produto",
            "preço desse produto",
            "preco desse produto",
            "valor unitário desse item",
            "valor unitario desse item",
            "quanto custa esse artigo"
        ],
        "comparacao_quantidade": [
            "qual tem mais",
            "qual deles tem mais",
            "qual desses tem mais",
            "qual tem menos",
            "qual deles tem menos",
            "qual desses tem menos",
            "entre esses qual tem maior quantidade",
            "entre esses qual tem menor quantidade",
            "compare esses itens",
            "compara esses itens",
            "qual está acabando",
            "qual esta acabando",
            "qual é maior",
            "qual é menor",
            "qual e maior",
            "qual e menor",
            "qual deles rende mais"
        ],
        "comparacao_valor": [
            "qual é mais caro",
            "qual é mais barato",
            "qual e mais caro",
            "qual e mais barato",
            "compare o valor desses itens",
            "qual tem maior valor",
            "qual tem menor valor"
        ],
        "comparacao_fornecedor": [
            "quais são do mesmo fornecedor",
            "quais sao do mesmo fornecedor",
            "compare fornecedores",
            "esses itens são do mesmo fornecedor",
            "esses itens sao do mesmo fornecedor"
        ],
        "comparacao_localizacao": [
            "estão no mesmo local",
            "estao no mesmo local",
            "compare localização",
            "compare localizacao",
            "esses itens ficam juntos",
            "esses produtos estão na mesma prateleira",
            "esses produtos estao na mesma prateleira"
        ],
        "resumo_item": [
            "resuma esse item",
            "resumo do item",
            "me dá um resumo",
            "me de um resumo",
            "fala resumido desse item",
            "resumir produto"
        ],
        "resumo_grupo": [
            "resuma os tecidos",
            "resuma os aviamentos",
            "resuma essa categoria",
            "me dê um resumo do grupo",
            "me de um resumo do grupo",
            "resumo da categoria"
        ],
        "contagem_por_fornecedor": [
            "quantos itens temos por fornecedor",
            "contagem por fornecedor",
            "agrupar quantidade por fornecedor",
            "quantidade de itens por fornecedor",
            "qual fornecedor tem mais itens"
        ],
        "contagem_por_cor": [
            "quantos itens temos por cor",
            "contagem por cor",
            "agrupar quantidade por cor",
            "quantidade de itens por cor",
            "qual cor aparece mais"
        ],
        "contagem_por_localizacao": [
            "quantos itens temos por local",
            "contagem por localização",
            "contagem por localizacao",
            "agrupar quantidade por localização",
            "agrupar quantidade por localizacao",
            "quantidade de itens por local"
        ],
        "contagem_por_categoria": [
            "quantos itens temos por categoria",
            "contagem por categoria",
            "agrupar quantidade por categoria",
            "quantidade de itens por categoria",
            "qual categoria tem mais itens"
        ],
        "contagem_por_tipo": [
            "quantos itens temos por tipo",
            "contagem por tipo",
            "agrupar quantidade por tipo",
            "quantidade de itens por tipo",
            "qual tipo tem mais itens"
        ],
        "item_existe": [
            "tem esse item",
            "esse item existe",
            "esse código existe",
            "esse codigo existe",
            "tem esse código",
            "tem esse codigo",
            "esse produto está cadastrado",
            "esse produto esta cadastrado",
            "esse nome existe no estoque"
        ],
        "item_nao_existe_confirmacao": [
            "não achei",
            "nao achei",
            "não encontrou",
            "nao encontrou",
            "não existe",
            "nao existe",
            "não tem cadastrado",
            "nao tem cadastrado"
        ],
        "listar_semelhantes": [
            "quais parecidos temos",
            "liste itens parecidos",
            "mostrar semelhantes",
            "buscar semelhantes",
            "achar parecidos",
            "me mostra similares"
        ],
        "continuacao_lista": [
            "continue",
            "continuar",
            "mostre mais",
            "traga mais",
            "próximos",
            "proximos",
            "mais itens",
            "quero ver mais",
            "continue a lista"
        ],
        "voltar_lista_anterior": [
            "volte",
            "voltar",
            "lista anterior",
            "mostre a anterior",
            "quero a lista anterior",
            "retorne para antes"
        ],
        "selecionar_primeiro": [
            "o primeiro",
            "primeiro item",
            "quero o primeiro",
            "me fale do primeiro"
        ],
        "selecionar_segundo": [
            "o segundo",
            "segundo item",
            "quero o segundo",
            "me fale do segundo"
        ],
        "selecionar_ultimo": [
            "o último",
            "o ultimo",
            "último item",
            "ultimo item",
            "quero o último",
            "quero o ultimo",
            "me fale do último",
            "me fale do ultimo"
        ],
        "referencia_pronominal": [
            "esse",
            "essa",
            "esses",
            "essas",
            "dele",
            "dela",
            "deles",
            "delas",
            "esse item",
            "esse tecido",
            "esse produto",
            "essa cor",
            "esse fornecedor"
        ],
        "pergunta_aberta_saldo": [
            "quanto tem",
            "quanto temos",
            "qual a quantidade",
            "qual o saldo",
            "quanto resta",
            "quantidade atual",
            "saldo atual",
            "me diga quanto tem",
            "quanto sobrou"
        ],
        "pergunta_aberta_valor": [
            "quanto vale",
            "qual o valor",
            "quanto custa",
            "preço",
            "preco",
            "valor atual",
            "me diga o valor"
        ],
        "pergunta_aberta_reposicao": [
            "precisa repor",
            "precisa comprar",
            "está acabando",
            "esta acabando",
            "tem estoque baixo",
            "precisa reabastecer",
            "necessita reposição",
            "necessita reposicao"
        ],
        "exportar_lista": [
            "exportar",
            "quero exportar",
            "exporte essa lista",
            "salvar essa lista",
            "gerar relatório",
            "gerar relatorio",
            "baixar essa lista",
            "exportar resultado"
        ]
    }

    SINONIMOS = {
        "acoes_listar": [
            "listar", "liste", "lista", "mostrar", "mostre", "me mostre", "me mostra",
            "traga", "trazer", "exibir", "exiba", "ver", "quero ver", "quais",
            "quais são", "quais sao", "me diga", "me fale", "apresentar", "consultar",
            "abrir", "exponha", "revele", "retorne"
        ],
        "acoes_buscar": [
            "buscar", "busca", "procurar", "procure", "achar", "ache", "pesquisar",
            "pesquise", "localizar", "localize", "encontrar", "encontre", "verificar",
            "confere", "consultar", "consulta", "vasculhar", "descobrir"
        ],
        "acoes_filtrar": [
            "filtrar", "filtre", "somente", "apenas", "só", "so", "deixe só", "deixe so",
            "me mostra só", "me mostra so", "quero só", "quero so", "restrinja", "separe",
            "limite a", "mostre apenas", "apresente apenas"
        ],
        "acoes_ordenar": [
            "ordenar", "ordene", "organizar", "organize", "classificar", "classifique",
            "do maior para o menor", "do menor para o maior", "crescente", "decrescente",
            "ordem crescente", "ordem decrescente", "ranking", "ranquear", "colocar em ordem"
        ],
        "acoes_somar": [
            "somar", "soma", "totalizar", "totalize", "calcular total", "some",
            "quantidade total", "total", "valor total", "metragem total", "montante",
            "acumular", "fazer a soma", "somatorio", "somatório"
        ],
        "acoes_comparar": [
            "comparar", "compare", "comparação", "comparacao", "qual tem mais",
            "qual tem menos", "qual é maior", "qual e maior", "qual é menor", "qual e menor",
            "diferença", "diferenca", "entre esses", "entre estes", "comparativo", "contrastar"
        ],
        "codigo": [
            "codigo", "código", "cod", "cód", "ref", "referencia", "referência",
            "numero", "número", "id", "identificador", "cód.", "cod.", "n do item",
            "numero do item", "número do item", "chave", "registro"
        ],
        "descricao": [
            "descricao", "descrição", "nome", "produto", "item", "material",
            "titulo", "título", "texto", "designacao", "designação", "nome do item",
            "artigo", "descritor", "nome do produto"
        ],
        "categoria": [
            "categoria", "grupo", "classe", "familia", "família", "setor", "segmento",
            "tipo geral", "linha", "secao", "seção", "divisão", "divisao",
            "grupo principal", "categoria principal"
        ],
        "tipo": [
            "tipo", "subtipo", "modelo", "variedade", "espécie", "especie",
            "classificação", "classificacao", "natureza", "modelo do item"
        ],
        "subgrupo": [
            "subgrupo", "sub categoria", "subcategoria", "subtipo", "ramo", "subclasse"
        ],
        "tecidos": [
            "tecido", "tecidos", "malha", "plano", "alfaiataria", "crepe", "algodao",
            "algodão", "cetim", "seda", "linho", "viscose", "tricoline", "sarja",
            "jeans", "denim", "tule", "renda", "microfibra", "suplex", "helanca",
            "malharia", "tecido plano", "tecido de malha", "lycra", "moletom",
            "flanela", "gabardine", "oxford", "chiffon", "organza", "neoprene",
            "jacquard", "canelado", "crepinho", "creponado", "tecidos", "mousseline",
            "viscolinho", "malha fria", "malha canelada"
        ],
        "aviamentos": [
            "aviamento", "aviamentos", "ziper", "zíper", "zip", "botao", "botão",
            "linha", "linhas", "agulha", "agulhas", "elastico", "elástico", "fita",
            "fitas", "velcro", "passamanaria", "cursor", "cursores", "rebite",
            "ilhos", "ilhós", "colchete", "colchetes", "entretela", "etiqueta",
            "etiquetas", "viés", "vies", "viés pronto", "argola", "fivela", "renda",
            "rendas", "cordao", "cordão", "galao", "galão", "rendado", "botoes",
            "botões", "cursores de ziper", "passadores"
        ],
        "insumos": [
            "insumo", "insumos", "materia prima", "matéria prima", "base", "componente",
            "componentes", "material de produção", "material de producao", "recurso",
            "recurso produtivo", "consumivel", "consumível"
        ],
        "escritorio": [
            "escritorio", "escritório", "material de escritorio", "material de escritório",
            "papelaria", "administrativo", "folha", "folhas", "caneta", "canetas",
            "lapis", "lápis", "toner", "cartucho", "grampeador", "grampos", "pasta",
            "pastas", "agenda", "caderno", "cadernos", "impressao", "impressão",
            "etiqueta de escritório", "etiqueta de escritorio", "borracha", "marcador"
        ],
        "limpeza": [
            "limpeza", "produto de limpeza", "produtos de limpeza", "detergente", "sabao",
            "sabão", "alcool", "álcool", "desinfetante", "agua sanitaria", "água sanitária",
            "pano", "panos", "luva", "luvas", "vassoura", "rodo", "papel toalha",
            "saco de lixo", "higiene", "limpador", "desengordurante", "esponja"
        ],
        "outros": [
            "outros", "diversos", "misc", "miscelanea", "miscelânea", "varios", "vários",
            "geral", "sortidos", "outros itens", "itens diversos", "demais"
        ],
        "quantidade": [
            "quantidade", "qtd", "qtde", "saldo", "resta", "restante", "tem", "temos",
            "existem", "há", "ha", "número", "numero", "volume", "total", "estoque",
            "saldo atual", "quantidade atual", "estoque atual", "disponivel", "disponível",
            "sobrou", "contagem", "quantos"
        ],
        "unidade": [
            "unidade", "unidades", "und", "unds", "un", "peca", "peça", "pecas", "peças",
            "item", "itens", "volume", "volumes"
        ],
        "metros": [
            "metro", "metros", "m", "metragem", "mt", "mts", "metro linear",
            "metros lineares", "metrôs", "metragem total", "metragem disponivel",
            "metragem disponível"
        ],
        "kilos": [
            "quilo", "quilos", "kilo", "kilos", "kg", "kgs", "quilograma", "quilogramas",
            "peso", "pesagem", "peso total"
        ],
        "valor": [
            "valor", "preco", "preço", "custo", "custa", "vale", "valor unitario",
            "valor unitário", "preço unitário", "preco unitario", "valor total",
            "montante", "financeiro", "custo total", "custo unitário", "custo unitario",
            "quanto vale", "quanto custa", "em dinheiro"
        ],
        "fornecedor": [
            "fornecedor", "fornecedores", "origem", "empresa", "fabricante", "marca",
            "vendedor", "quem fornece", "quem vende", "proveniente de", "comprado de",
            "fornecedor do item", "origem do produto"
        ],
        "cor": [
            "cor", "cores", "tonalidade", "tom", "azul", "preto", "preta", "branco",
            "branca", "vermelho", "vermelha", "verde", "amarelo", "amarela", "rosa",
            "roxo", "roxa", "bege", "cinza", "marrom", "laranja", "vinho", "off white",
            "cru", "nude", "estampado", "estampada", "liso", "lisa", "azulado", "escuro",
            "claro"
        ],
        "localizacao": [
            "localizacao", "localização", "local", "onde está", "onde esta", "onde fica",
            "depósito", "deposito", "almoxarifado", "prateleira", "setor", "gaveta",
            "armario", "armário", "corredor", "estante", "coluna", "posição", "posicao",
            "box", "baia", "sala", "area", "área", "armazenado", "guardado"
        ],
        "critico": [
            "critico", "crítico", "criticos", "críticos", "baixo", "baixa", "acabando",
            "faltando", "repor", "reposição", "reposicao", "urgente", "mínimo", "minimo",
            "abaixo do limite", "estoque baixo", "quase acabando", "insuficiente",
            "estoque crítico", "precisa comprar"
        ],
        "zerado": [
            "zerado", "zerada", "zerados", "sem estoque", "acabou", "acabaram",
            "indisponível", "indisponivel", "esgotado", "esgotada", "nada", "vazio"
        ],
        "maior": [
            "maior", "mais", "top", "lider", "líder", "principal", "mais alto", "máximo",
            "maximo", "mais quantidade", "maior saldo", "mais metros", "mais quilos",
            "mais valor", "mais caro"
        ],
        "menor": [
            "menor", "menos", "último", "ultimo", "mais baixo", "mínimo", "minimo",
            "menor saldo", "menos metros", "menos quilos", "pior saldo", "mais barato"
        ],
        "ordem_crescente": [
            "crescente", "do menor para o maior", "ascendente", "asc", "menor primeiro"
        ],
        "ordem_decrescente": [
            "decrescente", "do maior para o menor", "descendente", "desc", "maior primeiro"
        ],
        "data_entrada": [
            "data de entrada", "entrada", "quando entrou", "cadastro", "data cadastro",
            "data de cadastro", "lancamento", "lançamento", "registro", "quando chegou",
            "data do registro"
        ],
        "observacoes": [
            "observacao", "observação", "observacoes", "observações", "nota", "nota interna",
            "comentario", "comentário", "anotação", "anotacao", "detalhe extra", "observado"
        ],
        "pesquisa_aproximada": [
            "parecido", "semelhante", "similar", "aproximado", "com erro", "mesmo errado",
            "digitado errado", "parece com", "quase igual", "busca fuzzy", "escrito errado"
        ],
        "continuidade": [
            "esses", "essas", "esse", "essa", "eles", "elas", "dele", "dela", "deles",
            "delas", "aqueles", "aquelas", "o primeiro", "o segundo", "o último",
            "o ultimo", "esse aí", "esse ai", "desses", "desses itens", "dessas opções",
            "dessas opcoes", "do grupo", "da lista", "do resultado", "dos encontrados",
            "deles todos"
        ],
        "confirmacao": [
            "sim", "isso", "isso mesmo", "correto", "certo", "confirma", "confirmado",
            "ok", "beleza", "pode ser", "exatamente", "perfeito", "isso ai", "é isso", "e isso"
        ],
        "negacao": [
            "nao", "não", "errado", "não é", "nao e", "não era", "nao era", "não quero",
            "nao quero", "cancela", "cancelar", "deixa", "deixa pra lá", "deixa pra la"
        ],
        "tecidos_especificos": [
            "alfaiataria", "crepe", "algodao", "algodão", "cetim", "seda", "linho",
            "viscose", "sarja", "jeans", "tricoline", "gabardine", "oxford", "tule",
            "renda", "flanela", "lycra", "suplex", "neoprene", "helanca", "organza",
            "chiffon", "jacquard", "mousseline", "creponado", "canelado", "moletinho",
            "malha fria", "viscolinho"
        ],
        "aviamentos_especificos": [
            "ziper", "zíper", "botao", "botão", "linha", "agulha", "elastico", "elástico",
            "viés", "vies", "entretela", "cursor", "colchete", "rebite", "fivela",
            "argola", "cordao", "cordão", "etiqueta", "passamanaria", "renda", "velcro"
        ],
        "erros_comuns": [
            "ziper", "ziperr", "zip", "algodam", "algodao", "cetin", "aviamneto",
            "aviamentoo", "insumoo", "limpesa", "escritorioo", "localisacao", "forncedor",
            "desricao", "descrisao", "quantidae", "qantidade", "metrso", "quiloz",
            "codgo", "codigoo", "cora", "fornecdor", "alfaiatari", "crep", "vicscose"
        ]
    }

    # ------------------------------------------------------------------
    # ATRIBUTOS
    # ------------------------------------------------------------------
    def __init__(self, resultados=None):
        self.resultados = resultados or []
        self.ctx: List[Tuple[str, str]] = []
        self.last_intent: Optional[str] = None
        self.last_entities: Dict[str, Any] = {}
        self.last_result_rows: List[Dict[str, Any]] = []
        self.last_result_summary: Dict[str, Any] = {}
        self._sources_cache: Optional[List[Dict[str, Any]]] = None

        self._page_offset = 0
        self._page_size = 10
        self._total_results = 0
        self._current_page = 1
        self._last_query_params: Tuple[str, List[Any]] = ("", [])

        self._candidate_words = None

    # ------------------------------------------------------------------
    # MÉTODOS DE COMPATIBILIDADE
    # ------------------------------------------------------------------
    def _intent_score(self, pergunta: str) -> Tuple[Optional[str], float]:
        return self._detect_intent(pergunta)

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

    def _format_number_pt(self, value: float, casas: int = 2) -> str:
        s = f"{value:,.{casas}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip().lower())

    # ------------------------------------------------------------------
    # MÉTODO PRINCIPAL: CLASSIFICAÇÃO DE CRITICIDADE
    # ------------------------------------------------------------------
    def _classificar_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifica um item com base no estoque atual e regras por grupo.
        Retorna: status, percentual, cor, mensagem, sugestao_compra
        """
        grupo = item.get("grupo", "Outros")
        regra = self.REGRAS_CRITICIDADE.get(grupo, self.REGRA_GERAL)

        # Obter estoque atual
        estoque_atual = self._safe_float(item.get("saldo_num", 0))

        # Obter ou calcular estoque ideal
        estoque_ideal = self._safe_float(item.get("estoque_ideal"))
        if estoque_ideal <= 0:
            # Calcular estoque ideal baseado no grupo e consumo estimado
            estoque_ideal = self._calcular_estoque_ideal(item, regra)

        # Calcular percentual
        if estoque_ideal > 0:
            percentual = (estoque_atual / estoque_ideal) * 100
        else:
            percentual = 100.0 if estoque_atual > 0 else 0.0

        # Determinar status e cor
        if percentual <= regra["critico_percentual"]:
            status = "CRÍTICO"
            cor = regra["cor_critico"]
            acao = f"⚠️ COMPRA URGENTE! Estoque em {percentual:.1f}% do ideal"
        elif percentual <= regra["baixo_percentual"]:
            status = "BAIXO"
            cor = regra["cor_baixo"]
            acao = f"📦 ALERTA! Estoque em {percentual:.1f}% do ideal"
        else:
            status = "NORMAL"
            cor = regra["cor_normal"]
            acao = f"✅ OK. Estoque em {percentual:.1f}% do ideal"

        # Sugestão de compra
        sugestao_compra = ""
        if status in ["CRÍTICO", "BAIXO"]:
            quantidade_repor = max(0, estoque_ideal - estoque_atual)
            sugestao_compra = f"Comprar {self._format_number_pt(quantidade_repor)} para atingir o ideal"
            if status == "CRÍTICO":
                sugestao_compra += " (URGENTE!)"

        return {
            "status": status,
            "percentual": percentual,
            "cor": cor,
            "estoque_ideal": estoque_ideal,
            "estoque_atual": estoque_atual,
            "acao": acao,
            "sugestao_compra": sugestao_compra,
            "mensagem_grupo": regra["mensagem"]
        }

    def _calcular_estoque_ideal(self, item: Dict[str, Any], regra: Dict) -> float:
        """
        Calcula estoque ideal baseado em heurística por grupo.
        """
        grupo = item.get("grupo", "Outros")
        estoque_atual = self._safe_float(item.get("saldo_num", 0))

        # Se não tem estoque ideal cadastrado, usar regra padrão
        # Baseado no consumo médio (se disponível) ou valor padrão
        if regra.get("usa_metros_primario", False):
            # Tecidos: ideal baseado em consumo médio mensal
            if estoque_atual > 0:
                # Se tem estoque, assume que é o mínimo necessário
                return max(estoque_atual * 2, 50)  # pelo menos 50m
            else:
                return 100.0  # padrão 100m
        else:
            # Aviamentos, insumos, etc.
            if estoque_atual > 0:
                return max(estoque_atual * 2, 100)  # pelo menos 100 unidades
            else:
                return 200.0  # padrão 200 unidades

    # ------------------------------------------------------------------
    # ACESSO AO BANCO (UNION + FETCH)
    # ------------------------------------------------------------------
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
                "data_col": self._choose_col(cols,
                                             ["data_entrada", "data", "created_at", "atualizado_em", "updated_at"]),
                "obs_col": self._choose_col(cols, ["observacoes", "observação", "observacoes", "obs"]),
                "estoque_ideal_col": self._choose_col(cols, ["estoque_ideal", "ideal", "estoque_base"]),
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
            estoque_ideal = self._sql_expr(s["estoque_ideal_col"], "NULL::numeric")

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
                    {obs}::text AS observacoes,
                    {estoque_ideal}::numeric AS estoque_ideal
                FROM {s['tabela']}
            """)
        return "\nUNION ALL\n".join(parts) if parts else "SELECT NULL::text AS grupo WHERE FALSE"

    def _fetch_rows(self, where_sql: str = "", params: Optional[List[Any]] = None,
                    order_sql: str = "ORDER BY saldo_num DESC, descricao ASC", limit: Optional[int] = 50) -> List[
        Dict[str, Any]]:
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

    def _fetch_rows_com_classificacao(self, where_sql: str = "", params: Optional[List[Any]] = None,
                                      order_sql: str = "", limit: Optional[int] = 50) -> List[Dict[str, Any]]:
        """
        Busca itens e adiciona classificação de criticidade.
        """
        rows = self._fetch_rows(where_sql, params, order_sql, limit)

        if not rows or rows[0].get("__erro__"):
            return rows

        # Adicionar classificação a cada item
        for row in rows:
            classificacao = self._classificar_item(row)
            row.update(classificacao)

        return rows

    # ------------------------------------------------------------------
    # DETECÇÃO DE INTENÇÃO E ENTIDADES
    # ------------------------------------------------------------------
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
            "operador": None,
            "valor_operador": None,
            "valor_operador2": None,
        }

        m_codigo = re.search(r"(?:codigo|código|cod)\s*[:#-]?\s*([a-z0-9._/-]+)", qn)
        if m_codigo:
            ent["codigo"] = m_codigo.group(1).strip()

        m_top = re.search(r"(?:top|primeiros|ultimos|últimos|ultimos)\s*(\d{1,3})", qn)
        if m_top:
            ent["top_n"] = int(m_top.group(1))

        m_abaixo = re.search(
            r"(?:abaixo de|menor que|inferior a|criticos abaixo de|críticos abaixo de)\s*(\d+[\.,]?\d*)", qn)
        if m_abaixo:
            ent["limite"] = float(m_abaixo.group(1).replace(",", "."))

        # Operadores
        op_patterns = [
            (r"(?:maior que|acima de|>)\s*(\d+(?:[.,]\d+)?)", ">", 1),
            (r"(?:menor que|abaixo de|<)\s*(\d+(?:[.,]\d+)?)", "<", 1),
            (r">=\s*(\d+(?:[.,]\d+)?)", ">=", 1),
            (r"<=\s*(\d+(?:[.,]\d+)?)", "<=", 1),
            (r"entre\s*(\d+(?:[.,]\d+)?)\s*e\s*(\d+(?:[.,]\d+)?)", "between", 2),
        ]
        for pat, op, n in op_patterns:
            m = re.search(pat, qn)
            if m:
                ent["operador"] = op
                if n == 1:
                    ent["valor_operador"] = float(m.group(1).replace(",", "."))
                else:
                    ent["valor_operador"] = float(m.group(1).replace(",", "."))
                    ent["valor_operador2"] = float(m.group(2).replace(",", "."))
                break

        for label, key in [
            (r"cor\s+([\w\s/_-]+)", "cor"),
            (r"fornecedor\s+([\w\s/_-]+)", "fornecedor"),
            (r"(?:local|localizacao|localização|deposito|depósito|setor)\s+([\w\s/_-]+)", "local"),
            (r"categoria\s+([\w\s/_-]+)", "categoria"),
        ]:
            m = re.search(label, qn)
            if m:
                ent[key] = m.group(1).strip(" ?.,;:")

        ent["pedir_lista"] = any(
            x in qn for x in ["liste", "listar", "mostre", "mostra", "quais", "quais sao", "quais são", "eles", "elas"])
        ent["pedir_nomes"] = any(
            x in qn for x in ["nomes", "liste os nomes", "liste nomes", "mostrar nomes", "mostre os nomes"])
        ent["pedir_criticos"] = any(
            x in qn for x in ["critico", "crítico", "criticos", "críticos", "baixo estoque", "repor"])
        ent["pedir_contagem"] = any(x in qn for x in ["quantos", "quantas", "contagem", "total", "temos", "tem "])

        # busca livre curta
        limpa = re.sub(r"[?!.:,;]", " ", qn)
        for remover in ["quantos", "quantas", "temos", "tem", "liste", "listar", "mostre", "mostrar", "quais", "os",
                        "as", "de", "do", "da", "no", "na"]:
            limpa = re.sub(rf"\b{re.escape(remover)}\b", " ", limpa)
        limpa = re.sub(r"\s+", " ", limpa).strip()
        if len(limpa) >= 3:
            ent["buscar_texto"] = limpa

        return ent

    def _detect_intent(self, q: str) -> Tuple[Optional[str], float]:
        qn = self._normalize(q)
        if not qn:
            return None, 0.0

        # Novas intenções
        if any(x in qn for x in ["itens baixos", "alerta", "estoque baixo", "baixo estoque"]):
            return "baixos", 0.90
        if any(x in qn for x in ["sugestões de compra", "sugestoes de compra", "o que comprar", "precisa comprar"]):
            return "sugestoes_compra", 0.90
        if any(x in qn for x in ["relatório de críticos", "relatorio de criticos", "resumo crítico"]):
            return "criticos", 0.85

        # Buscar nos dicionários de intenções
        for intent, phrases in self.INTENCOES_ESTOQUE.items():
            for phrase in phrases:
                if phrase in qn:
                    return intent, 0.95

        # Regras originais
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

    # ------------------------------------------------------------------
    # PAGINAÇÃO, DETALHES, REFERÊNCIA PRONOMINAL
    # ------------------------------------------------------------------
    def _is_pagination_command(self, q: str) -> bool:
        qn = self._normalize(q)
        return any(
            term in qn for term in ["próxima página", "próximos", "mais itens", "próxima", "página 2", "mostre mais"])

    def _handle_pagination(self, q: str) -> str:
        qn = self._normalize(q)
        if "próxima" in qn or "mais" in qn:
            self._page_offset += self._page_size
            if self._page_offset >= self._total_results:
                self._page_offset = max(0, self._total_results - self._page_size)
                return "Não há mais itens para mostrar. Essa é a última página."
        elif "anterior" in qn or "voltar" in qn:
            self._page_offset = max(0, self._page_offset - self._page_size)
        elif "página" in qn:
            m = re.search(r"página\s*(\d+)", qn)
            if m:
                page = int(m.group(1))
                self._page_offset = (page - 1) * self._page_size
            else:
                return "Para ir a uma página específica, diga 'página X'."
        sql, params = self._last_query_params
        if not sql:
            return "Nenhuma consulta anterior para paginar."
        limit_sql = f" LIMIT {self._page_size} OFFSET {self._page_offset}"
        sql = re.sub(r"\s+LIMIT\s+\d+\s+OFFSET\s+\d+", "", sql, flags=re.IGNORECASE)
        sql += limit_sql
        rows = db.fetch_all(sql, params)
        if not rows:
            return "Não há resultados para exibir."
        self.last_result_rows = rows
        return self._format_list_response(rows, start=self._page_offset + 1)

    def _is_details_request(self, q: str) -> bool:
        qn = self._normalize(q)
        return any(term in qn for term in ["detalhes", "detalhar", "mais informações", "dados completos"])

    def _show_item_details(self) -> str:
        if not self.last_result_rows:
            return "Nenhum item selecionado ainda. Faça uma busca primeiro."
        item = self.last_result_rows[0]
        return self._format_item_details(item)

    def _format_item_details(self, item: Dict[str, Any]) -> str:
        codigo = self._safe_text(item.get("codigo", "—"))
        descricao = self._safe_text(item.get("descricao", "Sem descrição"))
        grupo = self._safe_text(item.get("grupo", "—"))
        categoria = self._safe_text(item.get("categoria_exibicao", "—"))
        cor = self._safe_text(item.get("cor", "—"))
        fornecedor = self._safe_text(item.get("fornecedor", "—"))
        local = self._safe_text(item.get("localizacao", "—"))
        saldo = self._safe_text(item.get("saldo_exibicao", ""))
        if not saldo:
            saldo = self._format_number_pt(self._safe_float(item.get("saldo_num", 0)))
        unidade = self._safe_text(item.get("unidade", "—"))
        medida = self._safe_text(item.get("tipo_medida", "—"))
        data = self._safe_text(item.get("data_entrada", "—"))
        if data != "—" and "strftime" in dir(data):
            data = data.strftime("%d/%m/%Y")
        obs = self._safe_text(item.get("observacoes", "—"))
        status = item.get("status", "NORMAL")
        percentual = item.get("percentual", 100)
        sugestao = item.get("sugestao_compra", "")

        return (
            f"📦 **{descricao}**\n"
            f"• Código: {codigo}\n"
            f"• Grupo: {grupo}\n"
            f"• Categoria: {categoria}\n"
            f"• Cor: {cor}\n"
            f"• Fornecedor: {fornecedor}\n"
            f"• Localização: {local}\n"
            f"• Saldo: {saldo}\n"
            f"• Unidade: {unidade}\n"
            f"• Tipo de medida: {medida}\n"
            f"• Data de entrada: {data}\n"
            f"• Observações: {obs}\n"
            f"• Status: {status} ({percentual:.1f}% do ideal)\n"
            f"• Sugestão: {sugestao if sugestao else 'Estoque OK'}"
        )

    def _is_reference(self, q: str) -> bool:
        qn = self._normalize(q)
        return any(term in qn for term in ["esse", "essa", "esse item", "desse", "dessa", "ele", "ela"])

    def _handle_reference(self, q: str) -> str:
        if not self.last_result_rows:
            return "Não tenho um item recente para referência. Faça uma busca primeiro."
        item = self.last_result_rows[0]
        qn = self._normalize(q)
        if "cor" in qn:
            return f"A cor é {self._safe_text(item.get('cor', 'não informada'))}."
        elif "fornecedor" in qn:
            return f"O fornecedor é {self._safe_text(item.get('fornecedor', 'não informado'))}."
        elif "local" in qn:
            return f"Está localizado em {self._safe_text(item.get('localizacao', 'não informado'))}."
        elif "quantidade" in qn or "saldo" in qn:
            saldo = self._safe_text(item.get("saldo_exibicao", ""))
            if not saldo:
                saldo = self._format_number_pt(self._safe_float(item.get("saldo_num", 0)))
            return f"O saldo é {saldo}."
        elif "status" in qn or "crítico" in qn:
            return f"Status: {item.get('status', 'NORMAL')} ({item.get('percentual', 100):.1f}% do ideal)"
        elif "detalhes" in qn or "informações" in qn:
            return self._format_item_details(item)
        else:
            return self._format_item_summary(item)

    def _format_item_summary(self, item: Dict[str, Any]) -> str:
        desc = self._safe_text(item.get("descricao", "Sem descrição"))
        cod = self._safe_text(item.get("codigo", "—"))
        grupo = self._safe_text(item.get("grupo", "—"))
        saldo = self._safe_text(item.get("saldo_exibicao", ""))
        if not saldo:
            saldo = self._format_number_pt(self._safe_float(item.get("saldo_num", 0)))
        status = item.get("status", "NORMAL")
        return f"{desc} (Cód: {cod}) – Grupo: {grupo} – Saldo: {saldo} – Status: {status}"

    # ------------------------------------------------------------------
    # BUSCA AVANÇADA COM CORREÇÃO ORTOGRÁFICA
    # ------------------------------------------------------------------
    def _load_candidate_words(self) -> set:
        if self._candidate_words is not None:
            return self._candidate_words
        words = set()
        # Adiciona sinônimos dos dicionários
        for category, synlist in self.SINONIMOS.items():
            for w in synlist:
                if len(w) >= 3:
                    words.add(w)
        # Adiciona palavras das tabelas reais
        try:
            sql = f"""
                SELECT DISTINCT LOWER(descricao) FROM ({self._build_union_query()}) u
                WHERE descricao IS NOT NULL
                UNION
                SELECT DISTINCT LOWER(cor) FROM ({self._build_union_query()}) u
                WHERE cor IS NOT NULL
                UNION
                SELECT DISTINCT LOWER(fornecedor) FROM ({self._build_union_query()}) u
                WHERE fornecedor IS NOT NULL
                UNION
                SELECT DISTINCT LOWER(localizacao) FROM ({self._build_union_query()}) u
                WHERE localizacao IS NOT NULL
                UNION
                SELECT DISTINCT LOWER(categoria_exibicao) FROM ({self._build_union_query()}) u
                WHERE categoria_exibicao IS NOT NULL
            """
            rows = db.fetch_all(sql)
            for row in rows:
                for val in row.values():
                    if val:
                        for w in re.findall(r"[a-z0-9áéíóúãõç_-]+", str(val).lower()):
                            if len(w) >= 3:
                                words.add(w)
        except Exception:
            pass
        self._candidate_words = words
        return words

    def _prepare_search_terms(self, q: str, entities: Dict[str, Any]) -> List[str]:
        qn = self._normalize(q)
        # Remover operadores
        qn = re.sub(r"\b(?:maior|menor|acima|abaixo|>=|<=|>|<|igual|entre)\b", "", qn)
        stopwords = {"o", "a", "os", "as", "de", "do", "da", "dos", "das", "e", "ou", "em", "no", "na", "para", "por",
                     "com", "sem", "que", "qual", "quais", "quanto", "quantos", "tem", "temos", "ia", "banco",
                     "estoque", "item", "itens", "verifique", "mostrar", "mostre", "procure", "buscar", "algo"}
        words = re.findall(r"[a-z0-9áéíóúãõç_-]+", qn)
        candidates = self._load_candidate_words()
        corrected = []
        for w in words:
            if len(w) < 3 or w in stopwords:
                continue
            if w in candidates:
                corrected.append(w)
            else:
                matches = get_close_matches(w, candidates, n=1, cutoff=0.8)
                if matches:
                    corrected.append(matches[0])
                else:
                    corrected.append(w)
        # Adicionar entidades
        if entities.get("codigo"):
            corrected.append(entities["codigo"])
        if entities.get("cor"):
            corrected.append(entities["cor"])
        if entities.get("fornecedor"):
            corrected.append(entities["fornecedor"])
        if entities.get("local"):
            corrected.append(entities["local"])
        if entities.get("categoria"):
            corrected.append(entities["categoria"])
        return list(set(corrected))

    def _advanced_search(self, terms: List[str], entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        union_sql = self._build_union_query()
        where_parts = []
        params = []

        # Filtros por entidades
        if entities.get("grupo"):
            where_parts.append("grupo = %s")
            params.append(entities["grupo"])
        if entities.get("codigo"):
            where_parts.append("LOWER(COALESCE(codigo, '')) = %s")
            params.append(entities["codigo"].lower())

        # Operador
        op = entities.get("operador")
        if op:
            if op == "between":
                v1 = entities.get("valor_operador")
                v2 = entities.get("valor_operador2")
                if v1 is not None and v2 is not None:
                    where_parts.append("saldo_num BETWEEN %s AND %s")
                    params.extend([v1, v2])
            else:
                val = entities.get("valor_operador")
                if val is not None:
                    where_parts.append(f"saldo_num {op} %s")
                    params.append(val)

        # Busca por termos
        if terms:
            term_conditions = []
            for term in terms:
                term_conditions.append("(" + " OR ".join([
                    "LOWER(COALESCE(descricao, '')) LIKE %s",
                    "LOWER(COALESCE(codigo, '')) LIKE %s",
                    "LOWER(COALESCE(cor, '')) LIKE %s",
                    "LOWER(COALESCE(fornecedor, '')) LIKE %s",
                    "LOWER(COALESCE(localizacao, '')) LIKE %s",
                    "LOWER(COALESCE(categoria_exibicao, '')) LIKE %s",
                    "LOWER(COALESCE(grupo, '')) LIKE %s",
                ]) + ")")
                like = f"%{term}%"
                params.extend([like] * 7)
            where_parts.append("(" + " AND ".join(term_conditions) + ")")

        where_sql = " AND ".join(where_parts) if where_parts else "1=1"
        order_sql = "ORDER BY saldo_num DESC, descricao ASC"
        limit_sql = f" LIMIT {self._page_size} OFFSET {self._page_offset}"
        sql = f"""
            WITH estoque_base AS (
                {union_sql}
            )
            SELECT *
            FROM estoque_base
            WHERE {where_sql}
            {order_sql}
            {limit_sql}
        """
        rows = db.fetch_all(sql, tuple(params))
        self._last_query_params = (sql, params)

        # Adicionar classificação
        for row in rows:
            classificacao = self._classificar_item(row)
            row.update(classificacao)

        return rows or []

    def _format_list_response(self, rows: List[Dict[str, Any]], start: int = 1) -> str:
        if not rows:
            return "Nenhum resultado encontrado."
        total = len(rows)
        end = start + total - 1
        lines = [f"🔍 Encontrei **{total}** item(ns). Mostrando de {start} a {end}:"]
        for i, r in enumerate(rows, start=start):
            desc = self._safe_text(r.get("descricao", "Sem descrição"))
            cod = self._safe_text(r.get("codigo", "—"))
            grupo = self._safe_text(r.get("grupo", "—"))
            saldo = self._safe_text(r.get("saldo_exibicao", ""))
            if not saldo:
                saldo = self._format_number_pt(self._safe_float(r.get("saldo_num", 0)))
            status = r.get("status", "NORMAL")
            percentual = r.get("percentual", 100)
            extra = []
            cor = self._safe_text(r.get("cor"))
            if cor:
                extra.append(f"Cor: {cor}")
            local = self._safe_text(r.get("localizacao"))
            if local:
                extra.append(f"Local: {local}")

            # Emoji de status
            if status == "CRÍTICO":
                status_emoji = "🔴"
            elif status == "BAIXO":
                status_emoji = "🟠"
            else:
                status_emoji = "🟢"

            line = f"{i}. {desc} | Cód: {cod} | Grupo: {grupo} | Saldo: {saldo} | {status_emoji} {status} ({percentual:.1f}%)"
            if extra:
                line += " | " + " | ".join(extra)
            lines.append(line)
        if total >= self._page_size:
            lines.append("\n💡 Digite 'próxima página' para ver mais itens.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # RESPOSTAS ESPECÍFICAS
    # ------------------------------------------------------------------
    def _responder_saudacao(self) -> str:
        return (
            "Olá! Sou seu assistente de estoque inteligente. 📊\n\n"
            "Posso consultar tecidos, aviamentos, insumos, escritório, limpeza e outros.\n"
            "**Funcionalidades:**\n"
            "• Classificação automática: CRÍTICO, BAIXO, NORMAL\n"
            "• Sugestões de compra baseadas no estoque ideal\n"
            "• Busca por código, descrição, cor, fornecedor, localização\n"
            "• Operadores: >, <, >=, <=, between\n"
            "• Paginação: 'próxima página', 'anterior'\n"
            "• Detalhes: 'detalhes' após uma busca\n\n"
            "**Exemplos:**\n"
            "• Quantos tecidos temos?\n"
            "• Mostre os críticos\n"
            "• Itens baixos\n"
            "• Sugestões de compra\n"
            "• Buscar código 123\n"
            "• Itens do fornecedor X\n"
            "• Itens com menos de 10 unidades\n"
            "Digite 'ajuda' para mais exemplos."
        )

    def _responder_ajuda(self) -> str:
        return (
            "📚 **Ajuda do Assistente de Estoque** 📚\n\n"
            "**Comandos principais:**\n"
            "🔢 **Quantidades:**\n"
            "  - Quantos tecidos temos?\n"
            "  - Qual o total em metros?\n\n"
            "⚠️ **Classificação de estoque:**\n"
            "  - Mostre os críticos (≤ 20-30% do ideal)\n"
            "  - Itens baixos (≤ 35-50% do ideal)\n"
            "  - Sugestões de compra\n\n"
            "🔎 **Buscas específicas:**\n"
            "  - Buscar código 123\n"
            "  - Itens da cor azul\n"
            "  - Produtos do fornecedor X\n"
            "  - Localização: depósito 1\n\n"
            "💰 **Valores:**\n"
            "  - Qual o valor do estoque?\n"
            "  - Valor dos tecidos\n\n"
            "📊 **Rankings:**\n"
            "  - Top 10 por quantidade\n"
            "  - Itens com maior quantidade\n\n"
            "🧮 **Operadores:**\n"
            "  - Itens com menos de 10 unidades\n"
            "  - Quantidade maior que 50\n"
            "  - Entre 5 e 20 unidades\n\n"
            "📄 **Ações:**\n"
            "  - Exportar lista\n"
            "  - Detalhar o item (após uma busca)\n"
            "  - Próxima página / mais itens\n\n"
            "**Regras de classificação por grupo:**\n"
            "• Tecidos: Crítico ≤20% | Baixo ≤40%\n"
            "• Aviamentos: Crítico ≤30% | Baixo ≤50%\n"
            "• Insumos: Crítico ≤30% | Baixo ≤50%\n"
            "• Escritório: Crítico ≤15% | Baixo ≤35%\n"
            "• Limpeza: Crítico ≤20% | Baixo ≤40%\n"
            "• Outros: Crítico ≤25% | Baixo ≤50%"
        )

    def _responder_busca_codigo(self, entities: Dict[str, Any]) -> str:
        if not entities.get("codigo"):
            return "Me diga o código do item para eu buscar no banco."
        where, params = self._build_filters(entities)
        rows = self._fetch_rows_com_classificacao(where_sql=where, params=params, order_sql="ORDER BY descricao ASC",
                                                  limit=10)
        if rows and rows[0].get("__erro__"):
            return f"Erro ao consultar o banco: {rows[0]['__erro__']}"
        if not rows:
            return f"Não encontrei item com código {entities['codigo']}."
        self.last_result_rows = rows
        self._store_result_context(rows, entities, "buscar_codigo")
        return self._format_item_details(rows[0])

    def _responder_criticos(self, entities: Dict[str, Any]) -> str:
        """
        Lista itens críticos com classificação detalhada.
        """
        where, params = self._build_filters(entities)
        rows = self._fetch_rows_com_classificacao(where_sql=where, params=params, limit=None)
        # Filtrar apenas críticos
        rows = [r for r in rows if r.get("status") == "CRÍTICO"]

        if rows and rows[0].get("__erro__"):
            return f"Erro ao consultar o banco: {rows[0]['__erro__']}"

        self.last_result_rows = rows
        self._store_result_context(rows, entities, "criticos")

        if not rows:
            return (
                f"✅ **Ótimo!** Não encontrei itens em situação **CRÍTICA** com esse filtro.\n\n"
                f"📊 **Classificação de estoque:**\n"
                f"• 🔴 CRÍTICO: ≤ {self.REGRAS_CRITICIDADE.get('Outros', self.REGRA_GERAL)['critico_percentual']}% do ideal\n"
                f"• 🟠 BAIXO: ≤ {self.REGRAS_CRITICIDADE.get('Outros', self.REGRA_GERAL)['baixo_percentual']}% do ideal\n"
                f"• 🟢 NORMAL: > {self.REGRAS_CRITICIDADE.get('Outros', self.REGRA_GERAL)['baixo_percentual']}%\n\n"
                f"💡 **Dica:** Se quiser ver itens em BAIXO, pergunte 'mostrar itens baixos'."
            )

        # Separar por grupo para melhor visualização
        criticos_por_grupo = defaultdict(list)
        for r in rows:
            criticos_por_grupo[r.get("grupo", "Outros")].append(r)

        resposta = ["🔴 **ITENS EM ESTOQUE CRÍTICO** 🔴\n"]
        resposta.append("Estes itens estão com estoque abaixo do limite crítico:\n")

        for grupo, itens in criticos_por_grupo.items():
            regra = self.REGRAS_CRITICIDADE.get(grupo, self.REGRA_GERAL)
            resposta.append(
                f"\n**{grupo}** (Crítico ≤ {regra['critico_percentual']}% | Baixo ≤ {regra['baixo_percentual']}%)")
            resposta.append(f"_{regra['mensagem']}_\n")

            for i, item in enumerate(itens[:30], 1):
                desc = self._safe_text(item.get("descricao", "Sem descrição"))
                cod = self._safe_text(item.get("codigo", "—"))
                saldo = self._safe_text(item.get("saldo_exibicao", ""))
                if not saldo:
                    saldo = self._format_number_pt(self._safe_float(item.get("saldo_num", 0)))
                ideal = self._format_number_pt(item.get("estoque_ideal", 0))
                percentual = item.get("percentual", 0)
                sugestao = item.get("sugestao_compra", "")

                resposta.append(
                    f"  {i}. **{desc}** (Cód: {cod})\n"
                    f"     📦 Saldo: {saldo} | Ideal: {ideal} | {percentual:.1f}% do ideal\n"
                    f"     💰 {sugestao}"
                )

        resposta.append(f"\n\n📊 **Total de itens críticos: {len(rows)}**")
        resposta.append("\n💡 Digite 'detalhes' para ver informações completas de um item.")

        return "\n".join(resposta)

    def _responder_baixos(self, entities: Dict[str, Any]) -> str:
        """
        Lista itens em alerta (estoque baixo).
        """
        where, params = self._build_filters(entities)
        rows = self._fetch_rows_com_classificacao(where_sql=where, params=params, limit=None)
        rows = [r for r in rows if r.get("status") == "BAIXO"]

        if not rows:
            return "✅ Não encontrei itens em situação BAIXA (entre 26% e 50% do ideal)."

        resposta = ["🟠 **ITENS EM ALERTA (ESTOQUE BAIXO)** 🟠\n"]
        resposta.append("Estes itens estão com estoque entre 26% e 50% do ideal:\n")

        for i, item in enumerate(rows[:50], 1):
            desc = self._safe_text(item.get("descricao", "Sem descrição"))
            cod = self._safe_text(item.get("codigo", "—"))
            grupo = item.get("grupo", "—")
            saldo = self._safe_text(item.get("saldo_exibicao", ""))
            if not saldo:
                saldo = self._format_number_pt(self._safe_float(item.get("saldo_num", 0)))
            percentual = item.get("percentual", 0)
            sugestao = item.get("sugestao_compra", "")

            resposta.append(
                f"{i}. **{desc}** | Cód: {cod} | Grupo: {grupo}\n"
                f"   📦 Saldo: {saldo} | {percentual:.1f}% do ideal\n"
                f"   💰 {sugestao}"
            )

        resposta.append(f"\n📊 **Total de itens em alerta: {len(rows)}**")
        return "\n".join(resposta)

    def _responder_sugestoes_compra(self, entities: Dict[str, Any]) -> str:
        """
        Gera relatório de sugestões de compra.
        """
        where, params = self._build_filters(entities)
        rows = self._fetch_rows_com_classificacao(where_sql=where, params=params, limit=None)

        # Filtrar itens que precisam de compra (CRÍTICO + BAIXO)
        precisam_comprar = [r for r in rows if r.get("status") in ["CRÍTICO", "BAIXO"]]

        if not precisam_comprar:
            return "✅ **Excelente!** Não há necessidade de compra neste momento. Todos os itens estão com estoque adequado."

        # Agrupar por grupo
        por_grupo = defaultdict(list)
        for item in precisam_comprar:
            por_grupo[item.get("grupo", "Outros")].append(item)

        # Calcular total
        total_estimado = 0
        sugestoes = []

        sugestoes.append("🛒 **SUGESTÕES DE COMPRA** 🛒\n")
        sugestoes.append("Baseado no estoque ideal calculado:\n")

        for grupo, itens in por_grupo.items():
            regra = self.REGRAS_CRITICIDADE.get(grupo, self.REGRA_GERAL)
            sugestoes.append(f"\n**{grupo}** - Prioridade: {regra['mensagem']}")
            sugestoes.append("_" * 40)

            grupo_valor = 0
            for item in itens[:30]:
                desc = self._safe_text(item.get("descricao", "Sem descrição"))
                cod = self._safe_text(item.get("codigo", "—"))
                atual = self._safe_float(item.get("saldo_num", 0))
                ideal = item.get("estoque_ideal", 0)
                qtd_compra = max(0, ideal - atual)
                valor_unitario = self._estimar_valor_unitario(item)
                grupo_valor += qtd_compra * valor_unitario

                sugestoes.append(
                    f"  • **{desc}** (Cód: {cod})\n"
                    f"    Atual: {self._format_number_pt(atual)} | Ideal: {self._format_number_pt(ideal)}\n"
                    f"    → Comprar: {self._format_number_pt(qtd_compra)} | Status: {item.get('status')}"
                )

            total_estimado += grupo_valor

        sugestoes.append(f"\n\n💰 **Valor estimado total da compra: R$ {self._format_number_pt(total_estimado, 2)}**")
        sugestoes.append("\n💡 **Dica:** Para itens críticos, priorize a compra imediata.")

        return "\n".join(sugestoes)

    def _responder_contagem(self, entities: Dict[str, Any]) -> str:
        where, params = self._build_filters(entities)
        rows = self._fetch_rows_com_classificacao(where_sql=where, params=params, order_sql="ORDER BY descricao ASC",
                                                  limit=None)
        if rows and rows[0].get("__erro__"):
            return f"Erro ao consultar o banco: {rows[0]['__erro__']}"

        total_linhas = len(rows)
        total_codigos = len(
            {self._safe_text(r.get('codigo')).lower() for r in rows if self._safe_text(r.get('codigo'))})
        saldo_total = sum(self._safe_float(r.get("saldo_num")) for r in rows)
        grupo = entities.get("grupo") or "itens"

        # Contagem por status
        status_count = Counter(r.get("status", "NORMAL") for r in rows)

        self._store_result_context(rows, entities, "contagem")
        return (
            f"📊 **Contagem em tempo real**\n"
            f"• {grupo}: **{total_linhas}** registro(s)\n"
            f"• Códigos distintos: **{total_codigos}**\n"
            f"• Saldo numérico total: **{self._format_number_pt(saldo_total)}**\n\n"
            f"**Classificação dos itens:**\n"
            f"• 🔴 CRÍTICO: {status_count.get('CRÍTICO', 0)} item(ns)\n"
            f"• 🟠 BAIXO: {status_count.get('BAIXO', 0)} item(ns)\n"
            f"• 🟢 NORMAL: {status_count.get('NORMAL', 0)} item(ns)\n\n"
            f"💡 Se quiser, posso listar os nomes, mostrar só os críticos, baixos ou sugestões de compra."
        )

    def _responder_listar(self, entities: Dict[str, Any]) -> str:
        where, params = self._build_filters(entities)
        if self.last_result_rows and not any(
                [entities.get("grupo"), entities.get("codigo"), entities.get("cor"), entities.get("fornecedor"),
                 entities.get("local"), entities.get("categoria")]):
            q_rows = self.last_result_rows
        else:
            q_rows = self._fetch_rows_com_classificacao(where_sql=where, params=params,
                                                        order_sql="ORDER BY descricao ASC", limit=50)
            if q_rows and q_rows[0].get("__erro__"):
                return f"Erro ao consultar o banco: {q_rows[0]['__erro__']}"
        self.last_result_rows = q_rows
        self._store_result_context(q_rows, entities, "listar")
        if not q_rows:
            return "Não encontrei itens para listar com esse filtro."
        return self._format_list_response(q_rows, start=1)

    def _responder_grupo(self, entities: Dict[str, Any]) -> str:
        return self._responder_contagem(entities)

    def _responder_busca_livre(self, entities: Dict[str, Any], q: str) -> str:
        terms = self._prepare_search_terms(q, entities)
        rows = self._advanced_search(terms, entities)
        if not rows:
            return "Nenhum item encontrado com os critérios informados. Tente usar sinônimos ou verificar a ortografia."
        self.last_result_rows = rows
        self._total_results = len(rows)
        return self._format_list_response(rows, start=1)

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

    def _store_result_context(self, rows: List[Dict[str, Any]], entities: Dict[str, Any],
                              intent: Optional[str]) -> None:
        self.last_result_rows = rows[:]
        self.last_result_summary = {
            "grupo": entities.get("grupo"),
            "categoria": entities.get("categoria"),
            "local": entities.get("local"),
            "intent": intent,
            "count": len(rows),
        }

    def _estimar_valor_unitario(self, item: Dict[str, Any]) -> float:
        """
        Estima valor unitário baseado no grupo (para sugestões de compra).
        """
        grupo = item.get("grupo", "Outros")
        if grupo == "Tecidos":
            return 15.0  # valor estimado por metro
        elif grupo == "Aviamentos":
            return 2.5
        elif grupo == "Insumos":
            return 5.0
        elif grupo == "Escritorio":
            return 3.0
        elif grupo == "Limpeza":
            return 4.0
        else:
            return 7.0

    # ------------------------------------------------------------------
    # PONTO DE ENTRADA PÚBLICO
    # ------------------------------------------------------------------
    def responder(self, pergunta: str) -> str:
        q = (pergunta or "").strip()
        if not q:
            return "Aguardando sua pergunta."

        self._remember("user", q)

        # Verificar comandos especiais
        if self._is_pagination_command(q):
            return self._handle_pagination(q)
        if self._is_details_request(q):
            return self._show_item_details()
        if self._is_reference(q):
            return self._handle_reference(q)

        # Detectar intenção e entidades
        intent, conf = self._detect_intent(q)
        current_entities = self._extract_entities(q)
        entities = self._merge_with_context(current_entities, q)

        # Executar intenção
        try:
            if intent == "saudacao":
                resp = self._responder_saudacao()
            elif intent == "ajuda":
                resp = self._responder_ajuda()
            elif intent == "buscar_codigo":
                resp = self._responder_busca_codigo(entities)
            elif intent == "criticos":
                resp = self._responder_criticos(entities)
            elif intent == "baixos":
                resp = self._responder_baixos(entities)
            elif intent == "sugestoes_compra":
                resp = self._responder_sugestoes_compra(entities)
            elif intent == "contagem_grupo":
                resp = self._responder_contagem(entities)
            elif intent == "listar":
                resp = self._responder_listar(entities)
            elif intent == "grupo":
                resp = self._responder_grupo(entities)
            else:
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

        self.last_intent = intent
        self.last_entities = entities
        self._remember("assistant", resp)
        return resp


# ==============================================================================
# INTERFACE PRINCIPAL (MESMO PADRÃO DO CADASTRO_DE_CORTE)
# ==============================================================================
class AdvancedStockReport(ctk.CTkFrame):
    def __init__(self, parent, controller=None):
        super().__init__(parent)
        self.parent = parent
        self.controller = controller or self._create_default_controller()

        # === APLICAR CORES DO TEMA ===
        self.obter_cores_por_tema()
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
        controller = getattr(self, "controller", None)

        if controller is not None and hasattr(controller, "cor_fundo"):
            atributos_de_cor = [
                "cor_fundo", "cor_primaria", "cor_secundaria", "cor_terciaria",
                "cor_texto", "cor_texto_entry", "cor_texto_secundario",
                "cor_placeholder", "cor_borda", "cor_hover",
                "cor_sucesso", "cor_alerta", "cor_destaque", "cor_selecao",
            ]

            for nome_atributo in atributos_de_cor:
                if hasattr(controller, nome_atributo):
                    setattr(self, nome_atributo, getattr(controller, nome_atributo))

            if not hasattr(self, "cor_texto_entry"):
                self.cor_texto_entry = getattr(self, "cor_texto", "#ffffff")
            if not hasattr(self, "cor_placeholder"):
                self.cor_placeholder = getattr(self, "cor_texto_secundario", "#888888")
            if not hasattr(self, "cor_selecao"):
                self.cor_selecao = getattr(self, "cor_destaque", "#4f46e5")
            return

        # Fallback tema roxo
        self.cor_fundo = "#130720"
        self.cor_primaria = "#24113b"
        self.cor_secundaria = "#1a0d2b"
        self.cor_terciaria = "#10061b"
        self.cor_texto = "#f5f5ff"
        self.cor_texto_entry = self.cor_texto
        self.cor_texto_secundario = "#b5aecf"
        self.cor_placeholder = "#9b8fb5"
        self.cor_borda = "#3b235a"
        self.cor_hover = "#312049"
        self.cor_sucesso = "#22c55e"
        self.cor_alerta = "#ef4444"
        self.cor_destaque = "#4f46e5"
        self.cor_selecao = self.cor_destaque

    def configurar_treeview_theme(self):
        self.obter_cores_por_tema()
        self.style = ttk.Style()
        self.style.theme_use("default")
        cor_fundo_linhas = self.cor_secundaria
        cor_texto_linhas = self.cor_texto
        cor_campo = self.cor_secundaria
        cor_selecao = getattr(self, "cor_selecao", None) or getattr(self, "cor_destaque", None) or self.cor_primaria
        self.style.configure(
            "Custom.Treeview",
            background=cor_fundo_linhas,
            foreground=cor_texto_linhas,
            fieldbackground=cor_campo,
            borderwidth=0,
            highlightthickness=0,
            rowheight=25,
        )
        self.style.configure(
            "Custom.Treeview.Heading",
            background=self.cor_primaria,
            foreground=self.cor_texto,
            relief="flat",
            borderwidth=1,
            font=("Arial", 10, "bold"),
        )
        self.style.map(
            "Custom.Treeview",
            background=[("selected", cor_selecao)],
            foreground=[("selected", "#FFFFFF")],
        )

    def _create_default_controller(self):
        class DefaultController:
            def __init__(self):
                self.obter_cores_por_tema()

            def obter_cores_por_tema(self):
                aplicacao_principal = None
                if hasattr(self, "controller") and self.controller is not None:
                    aplicacao_principal = self.controller
                else:
                    try:
                        topo = self.winfo_toplevel()
                        if isinstance(topo, ctk.CTk):
                            aplicacao_principal = topo
                    except Exception:
                        pass

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
                    if aplicacao_principal is not None and hasattr(aplicacao_principal, nome_atributo):
                        valor = getattr(aplicacao_principal, nome_atributo)
                        if isinstance(valor, str) and valor.strip():
                            return valor
                    return valor_default

                self.cor_fundo = obter_cor("cor_fundo", default_cor_fundo)
                self.cor_primaria = obter_cor("cor_primaria", default_cor_primaria)
                self.cor_secundaria = obter_cor("cor_secundaria", default_cor_secundaria)
                self.cor_terciaria = obter_cor("cor_terciaria", default_cor_terciaria)
                self.cor_texto = obter_cor("cor_texto", default_cor_texto)
                self.cor_texto_entry = obter_cor("cor_texto", default_cor_texto)
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
        self.configurar_treeview_theme()

    def _create_main_layout(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color=self.cor_primaria)
        header.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        ctk.CTkLabel(header, text="Controle de Estoque", font=self.font_titulo,
                     text_color=_hex_contrast(self.cor_primaria)).pack(side="left", padx=20)
        ctk.CTkButton(header, text="Atualizar Dados", command=self.reload_data, width=120,
                      fg_color=self.cor_secundaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="right", padx=20)

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

        footer = ctk.CTkFrame(self, height=40, fg_color=self.cor_primaria)
        footer.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        ctk.CTkLabel(
            footer,
            text=f"🟢 Conectado | {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            font=self.font_pequeno,
            text_color=_hex_contrast(self.cor_primaria)
        ).pack(side="left", padx=20)

    # ------------------------------------------------------------------
    # ABA: RELATÓRIO
    # ------------------------------------------------------------------
    def _setup_report_tab(self):
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
            filtros, placeholder_text="🔎 Buscar por código ou descrição...",
            fg_color=self.cor_secundaria, border_color=self.cor_borda,
            text_color=self.cor_texto_entry, placeholder_text_color=self.cor_placeholder
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.category_var = tk.StringVar(value="Todas")
        self.combo_category = ctk.CTkComboBox(
            filtros, variable=self.category_var,
            values=["Todas", "Tecidos", "Aviamentos", "Insumos", "Escritorio", "Limpeza", "Outros"],
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

        self._create_stock_table(parent=wrapper)

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
            ("Status", 100, "center"),
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

        if ctk.get_appearance_mode() == "Dark":
            cor_linha_par = self.cor_fundo
            cor_linha_impar = self.cor_secundaria
        else:
            cor_linha_par = "#ffffff"
            cor_linha_impar = "#f0f0f0"
        self.tree.tag_configure("oddrow", background=cor_linha_impar)
        self.tree.tag_configure("evenrow", background=cor_linha_par)

    # ------------------------------------------------------------------
    # ABA: ANÁLISE
    # ------------------------------------------------------------------
    def _setup_analytics_tab(self):
        self.tab_analytics.grid_rowconfigure(0, weight=1)
        self.tab_analytics.grid_columnconfigure(0, weight=1)
        wrapper = ctk.CTkFrame(self.tab_analytics, fg_color=self.cor_fundo)
        wrapper.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        wrapper.grid_rowconfigure(1, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        # Cards
        self.cards_frame = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        self.cards_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for i in range(4):
            self.cards_frame.grid_columnconfigure(i, weight=1)

        self._metric_card(self.cards_frame, "🧾 Total Itens", "—").grid(row=0, column=0, sticky="ew")
        self._metric_card(self.cards_frame, "⚠️ Itens Críticos", "—").grid(row=0, column=1, sticky="ew")
        self._metric_card(self.cards_frame, "📂 Categorias", "—").grid(row=0, column=2, sticky="ew")
        self._metric_card(self.cards_frame, "🕒 Atualizado", "—").grid(row=0, column=3, sticky="ew")

        # Botões de ações
        botoes_frame = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        botoes_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        botoes_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkButton(
            botoes_frame, text="📊 Relatório de Críticos",
            command=self._gerar_relatorio_criticos,
            fg_color=self.cor_alerta, hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).grid(row=0, column=0, padx=5, sticky="ew")

        ctk.CTkButton(
            botoes_frame, text="🟠 Itens Baixos",
            command=self._gerar_itens_baixos,
            fg_color="#F59E0B", hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).grid(row=0, column=1, padx=5, sticky="ew")

        ctk.CTkButton(
            botoes_frame, text="🛒 Sugestões de Compra",
            command=self._gerar_sugestoes_compra,
            fg_color=self.cor_destaque, hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).grid(row=0, column=2, padx=5, sticky="ew")

        ctk.CTkButton(
            botoes_frame, text="📈 Análise por Grupo",
            command=self._gerar_analise_grupo,
            fg_color=self.cor_primaria, hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).grid(row=0, column=3, padx=5, sticky="ew")

        self.charts_frame = ctk.CTkFrame(wrapper, fg_color=self.cor_fundo)
        self.charts_frame.grid(row=2, column=0, sticky="nsew")
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
            ctk.CTkLabel(box, text=title, text_color=self.cor_texto).pack(anchor="w", padx=10, pady=(8, 0))
            ctk.CTkLabel(box, text=str(value), font=self.font_metrica, text_color=self.cor_texto).pack(anchor="w",
                                                                                                       padx=10,
                                                                                                       pady=(2, 10))
            return box

        _metric("🧾 Total Itens", self.stats_data.get("total_items", 0)).grid(row=0, column=0, sticky="ew", padx=6)
        _metric("⚠️ Itens Críticos", self.stats_data.get("low_stock", 0)).grid(row=0, column=1, sticky="ew", padx=6)
        _metric("📂 Categorias", self.stats_data.get("categories", 0)).grid(row=0, column=2, sticky="ew", padx=6)
        _metric("💰 Valor Estimado", f"R$ {self.stats_data.get('total_value', 0):,.2f}").grid(row=0, column=3,
                                                                                             sticky="ew", padx=6)

    def _gerar_relatorio_criticos(self):
        if self.assistente:
            resposta = self.assistente.responder("mostrar itens críticos")
            self._post_bot(resposta, slow=False)
            self.tabs.set("🤖 Assistente")
        else:
            messagebox.showwarning("IA", "Assistente não inicializado.")

    def _gerar_itens_baixos(self):
        if self.assistente:
            resposta = self.assistente.responder("itens baixos")
            self._post_bot(resposta, slow=False)
            self.tabs.set("🤖 Assistente")
        else:
            messagebox.showwarning("IA", "Assistente não inicializado.")

    def _gerar_sugestoes_compra(self):
        if self.assistente:
            resposta = self.assistente.responder("sugestões de compra")
            self._post_bot(resposta, slow=False)
            self.tabs.set("🤖 Assistente")
        else:
            messagebox.showwarning("IA", "Assistente não inicializado.")

    def _gerar_analise_grupo(self):
        if self.assistente:
            resposta = self.assistente.responder("resumo por grupo")
            self._post_bot(resposta, slow=False)
            self.tabs.set("🤖 Assistente")
        else:
            messagebox.showwarning("IA", "Assistente não inicializado.")

    # ------------------------------------------------------------------
    # ABA: ASSISTENTE
    # ------------------------------------------------------------------
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
            "Itens baixos",
            "Sugestões de compra",
            "Resumo por grupo",
            "Valor do estoque",
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

        self._post_bot("Olá! Sou seu assistente de estoque inteligente. Como posso ajudar?", slow=False)

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
        for widget in frame.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=self.cor_texto)
            if hasattr(widget, "winfo_children"):
                self._recolor_labels_frame(widget)

    def _validar_numero(self, valor):
        if valor == "":
            return True
        try:
            float(valor)
            return True
        except ValueError:
            return False

    def diagnosticar_widgets(self):
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
        widgets_essenciais = [
            self.search_entry, self.combo_category, self.tree,
            self.ai_input, self.btn_send
        ]
        for widget in widgets_essenciais:
            if widget is None:
                print(f"Widget não inicializado: {widget}")

    def _formatar_metros(self, valor) -> str:
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
        try:
            try:
                from PIL import Image
            except ImportError:
                print("PIL/Pillow não disponível para carregar logo")
                self.logo_image = None
                return False

            try:
                from PAGINAS_DO_SISTEMA.LOGOMARCA import get_logo_path
                configured_logo = get_logo_path()
            except Exception:
                configured_logo = ""
            possiveis_logos = [
                configured_logo,
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
                        original_image = Image.open(logo_path)
                        width, height = original_image.size
                        new_width = 150
                        new_height = int((new_width / width) * height)
                        if new_height > 80:
                            new_height = 80
                            new_width = int((new_height / height) * width)
                        self.logo_image = ctk.CTkImage(
                            light_image=original_image,
                            dark_image=original_image,
                            size=(new_width, new_height)
                        )
                        print(f"Logo carregada: {logo_path} ({new_width}x{new_height})")
                        return True
                except Exception as e:
                    print(f"Erro ao carregar {logo_path}: {str(e)}")
                    continue

            print("Nenhuma logo encontrada, criando placeholder...")
            self.logo_image = None
            return False
        except Exception as e:
            print(f"Erro crítico ao carregar logo: {str(e)}")
            self.logo_image = None
            return False

    def _limpar_totais(self):
        self.total_folhas_var = ctk.StringVar(value="0")
        self.metros_utilizados_var = ctk.StringVar(value="0.00")
        self.bobinas_utilizadas_var = ctk.StringVar(value="0")
        self.total_pecas_var = ctk.StringVar(value="0")
        self.rendimento_var = ctk.StringVar(value="0.00")

    def limpar_cache_pagina(self):
        pass

    def get_state(self):
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
        self.carregar_logo()
        self.reload_data()

    def _recarregar_modelos_ocf(self):
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
        try:
            if hasattr(self, 'search_entry') and self.search_entry:
                self.search_entry.delete(0, "end")
                self.search_entry.insert(0, value)
                self.apply_filters()
        except Exception as e:
            print(f"Erro ao processar seleção: {e}")

    def _remover_da_ordem_corte_ficha_tx(self, cur, codigo: str) -> int:
        return 0

    def _buscar_tecidos_para_adicao(self, search_entry, tecido_tree):
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
        dialog = ctk.CTkToplevel(self)
        dialog.title("Adicionar Item do Estoque")
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
        selecionado = self.tree.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um item para remover!")
            return
        if messagebox.askyesno("Confirmar", "Deseja remover o item selecionado?"):
            self.tree.delete(selecionado[0])
            self.calcular_totais()

    def limpar_tabela(self):
        if messagebox.askyesno("Confirmar", "Deseja limpar toda a tabela?"):
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.calcular_totais()

    def limpar_tudo(self):
        if not messagebox.askyesno("Confirmar", "Deseja limpar todos os filtros e dados?"):
            return
        try:
            self.search_entry.delete(0, "end")
            self.category_var.set("Todas")
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.reload_data()
            messagebox.showinfo("Sucesso", "Todos os dados foram limpos!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao limpar dados:\n{e}")

    def salvar_ordem(self):
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
                    cur.execute(f"SET LOCAL search_path = {schema};")
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
                            # Determinar status baseado na quantidade (simples para tabela)
                            if quantidade <= 0:
                                status_display = "ZERADO"
                            elif quantidade < 10:
                                status_display = "CRÍTICO"
                            elif quantidade < 20:
                                status_display = "BAIXO"
                            else:
                                status_display = "NORMAL"
                            resultados.append(
                                (codigo, descricao, categoria, quantidade, status_display, localizacao, ultima))
        except Exception as e:
            messagebox.showerror("Leitura do banco", f"Erro ao consultar: {e}")
            return
        self.resultados = resultados
        self._refresh_table()
        self._recalc_stats()
        self._create_analytics_charts()
        self._create_metrics_panel()
        self.assistente = EstoqueIA(self.resultados)

    # ------------------------------------------------------------------
    # IA + BANCO (consultas inteligentes)
    # ------------------------------------------------------------------
    def _get_ai_sources(self, cur, schema: str):
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
                "fornecedor": next((f for f in ("fornecedor", "fornecedor_nome", "prestador", "provider") if f in cols),
                                   None),
                "data": next(
                    (f for f in ("data_atualizacao", "ultima_atualizacao", "atualizado_em", "updated_at") if f in cols),
                    None),
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
                    if p["top_n"] or p["bottom_n"] or p["is_busca"] or p["codigo"] or p["is_critico"] or p[
                        "limiar"] is not None or p["termos_livres"]:
                        limit = max(1, min(100, p["top_n"] or p["bottom_n"] or 20))
                        if p["bottom_n"] or p["is_abaixo"] or p["is_critico"]:
                            order = "quantidade ASC, descricao ASC"
                            titulo = f"⬇️ **Menores quantidades (top {limit})**"
                        else:
                            order = "quantidade DESC, descricao ASC"
                            titulo = f"⬆️ **Maiores quantidades (top {limit})**"
                        if p["is_busca"] and not p["codigo"]:
                            termo = p["raw"].replace("buscar", "").replace("procurar", "").replace("encontrar",
                                                                                                   "").strip()
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
        low_stock = sum(1 for i in self.resultados if i[3] is not None and float(i[3]) < 10)
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
            col_widths = [25, 90, 35, 30, 30, 45, 35]
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

    # ------------------------------------------------------------------
    # SUGESTÕES
    # ------------------------------------------------------------------
    def _open_suggestions_window(self):
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
        self.obter_cores_por_tema()
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
        body = ctk.CTkFrame(win, fg_color=self.cor_fundo)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=0)
        left = ctk.CTkFrame(body, fg_color=self.cor_fundo)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk_label_cat = ctk.CTkLabel(left, text="Categorias", text_color=self.cor_texto)
        tk_label_cat.pack(anchor="w")
        self._sug_cat_list = tk.Listbox(left, activestyle="dotbox", bg=self.cor_secundaria, fg=self.cor_texto,
                                        selectbackground=self.cor_selecao)
        self._sug_cat_list.pack(fill="both", expand=True)
        self._sug_cat_list.bind("<<ListboxSelect>>", lambda e: self._on_select_category())
        right = ctk.CTkFrame(body, fg_color=self.cor_fundo)
        right.grid(row=0, column=1, sticky="nsew")
        tk_label_q = ctk.CTkLabel(right, text="Perguntas", text_color=self.cor_texto)
        tk_label_q.pack(anchor="w")
        self._sug_q_list = tk.Listbox(right, activestyle="dotbox", bg=self.cor_secundaria, fg=self.cor_texto,
                                      selectbackground=self.cor_selecao)
        self._sug_q_list.pack(fill="both", expand=True)
        self._sug_q_list.bind("<Double-1>", lambda e: self._send_selected_question())
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
        self._sug_categories = list(self.sug_catalog.keys())
        self._sug_cat_list.delete(0, "end")
        for cat in self._sug_categories:
            try:
                self._sug_cat_list.insert("end", f"{cat} ({len(self.sug_catalog.get(cat, []))})")
            except Exception:
                self._sug_cat_list.insert("end", cat)
        if self._sug_categories:
            self._sug_cat_list.select_set(0)
            self._on_select_category()

    def _build_suggestions_catalog(self) -> Dict[str, List[str]]:
        cats = sorted({(str(r[2]) or "—") for r in self.resultados if r and len(r) > 2})
        locs = sorted({(str(r[5]) or "—") for r in self.resultados if r and len(r) > 5})
        cats = [c for c in cats if c and c != "—"][:30] or ["Tecidos", "Aviamentos", "Insumos", "Escritorio", "Limpeza",
                                                            "Outros"]
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
            out = list(dict.fromkeys(out))
            return out[:limit]

        def at_least(lst: List[str], n: int, filler_prefix: str) -> List[str]:
            i = 1
            while len(lst) < n:
                lst.append(f"{filler_prefix} #{i}")
                i += 1
            return lst

        geral_tpl = [
            "Itens críticos", "Itens baixos", "Itens zerados", "Itens negativos", "Excesso de estoque",
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
        cat_tpl = [
            "Valor em {cat}", "Itens críticos em {cat}", "Itens baixos em {cat}", "Itens zerados em {cat}",
            "Itens negativos em {cat}", "Top {N} em {cat}", "Bottom {N} em {cat}",
            "ABC por valor em {cat}", "Parados há {D} dias em {cat}", "Conferir duplicados em {cat}",
            "Exportar {cat} para CSV", "Gerar PDF de {cat}",
            "Itens abaixo de {L} em {cat}", "Itens acima de {L} em {cat}"
        ]
        por_categoria = expand(cat_tpl)
        por_categoria = at_least(por_categoria, 210, "Pergunta por categoria")
        loc_tpl = [
            "Quais itens no local {loc}?", "Valor no local {loc}", "Top {N} no local {loc}",
            "Bottom {N} no local {loc}", "Críticos no local {loc}", "Baixos no local {loc}", "Zerados no local {loc}",
            "Negativos no local {loc}", "Parados há {D} dias no local {loc}",
            "Exportar itens do local {loc}", "Gerar PDF do local {loc}",
            "Itens abaixo de {L} no local {loc}", "Itens acima de {L} no local {loc}"
        ]
        por_local = expand(loc_tpl)
        por_local = at_least(por_local, 210, "Pergunta por local")
        estados_tpl = [
            "Listar itens críticos", "Listar itens baixos", "Listar itens zerados", "Listar itens negativos",
            "Detectar excesso por categoria", "Detectar excesso por local",
            "Críticos por {cat}", "Baixos por {cat}", "Zerados por {cat}", "Negativos por {cat}",
            "Críticos por {loc}", "Baixos por {loc}", "Zerados por {loc}", "Negativos por {loc}",
            "Itens abaixo de {L}", "Itens acima de {L}"
        ]
        estados = expand(estados_tpl)
        estados = at_least(estados, 210, "Pergunta de estado")
        financeiro_tpl = [
            "Valor do estoque", "Valor por categoria", "Valor por local",
            "Quanto vale a categoria {cat}?", "Qual o valor no local {loc}?",
            "Top {N} em valor (categoria)", "Top {N} em valor (local)",
            "Curva ABC por valor", "Classe A detalhar", "Classe B detalhar", "Classe C detalhar",
            "Exportar valores por categoria", "Exportar valores por local"
        ]
        financeiro = expand(financeiro_tpl)
        financeiro = at_least(financeiro, 210, "Pergunta financeira")
        rank_tpl = [
            "Top {N} por quantidade", "Bottom {N} por quantidade",
            "Top {N} em {cat}", "Bottom {N} em {cat}",
            "Top {N} no local {loc}", "Bottom {N} no local {loc}"
        ]
        rankings = expand(rank_tpl)
        rankings = at_least(rankings, 210, "Pergunta de ranking")
        temporal_tpl = [
            "Itens não movimentados há {D} dias", "Parados há {D} dias em {cat}",
            "Parados há {D} dias no local {loc}", "Entradas recentes (últimos {D} dias)",
            "Comparar últimos {D} dias vs {D} dias anteriores"
        ]
        temporal = expand(temporal_tpl)
        temporal = at_least(temporal, 210, "Pergunta temporal")
        busca_tpl = [
            "Buscar: {term}", "Código: {code}", "Detalhes do item {code}",
            "Procurar por descrição contendo {term}", "Abrir por código {code}",
            "Comparar {cat} vs {cat}", "Comparar {loc} vs {loc}"
        ]
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
        export_tpl = [
            "Exportar CSV", "Exportar Excel", "Gerar PDF",
            "Exportar {cat} em CSV", "Exportar {cat} em Excel", "Gerar PDF da categoria {cat}",
            "Exportar local {loc} em CSV", "Exportar local {loc} em Excel", "Gerar PDF do local {loc}",
            "Exportar Top {N}", "Exportar Bottom {N}", "Exportar críticos", "Exportar baixos", "Exportar zerados",
            "Exportar negativos"
        ]
        exportacao = expand(export_tpl)
        exportacao = at_least(exportacao, 210, "Pergunta de exportação")
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
        total = max(1, len(qs))
        pages = max(1, (total + self._sug_page_size - 1) // self._sug_page_size)
        self._sug_page = max(0, min(self._sug_page, pages - 1))
        start = self._sug_page * self._sug_page_size
        end = start + self._sug_page_size
        view = qs[start:end]
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

    # ------------------------------------------------------------------
    # CHAT / IA
    # ------------------------------------------------------------------
    def process_ai_query(self, event=None):
        q = self.ai_input.get().strip()
        if not q:
            return
        if q.lower().startswith("ajuda página"):
            try:
                page = int(re.findall(r'\d+', q)[0])
            except Exception:
                page = 1
            self._post_user(q)
            self._post_bot(self.assistente._help_text(page=page) if hasattr(self.assistente,
                                                                            '_help_text') else "Ajuda disponível com mais detalhes.")
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
                resposta_local = self.assistente.responder(text)
                intent, conf = self.assistente._intent_score(text)
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

    def _short_variations(self, base_text):
        return []

    def _should_use_db_answer(self, text: str, intent: Optional[str], conf: float) -> bool:
        q = (text or "").strip().lower()
        if not q:
            return False
        if intent in {"saudacao", "ajuda", "contexto"} and conf >= 0.15:
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
        if "nenhum resultado encontrado no banco" in banco_l or "não consegui consultar o banco" in banco_l:
            return (
                f"{local_txt}\n\n"
                "No banco não encontrei um resultado exato com esse filtro agora. "
                "Se quiser, eu tento por código, categoria, cor, local ou fornecedor."
            )
        if "verificação no banco concluída" in banco_l:
            return (
                "Entendi 👍\n"
                f"{banco_txt}\n\n"
                "Se você me disser o que deseja (ex.: categoria, cor, fornecedor ou código), "
                "eu te devolvo uma resposta bem mais específica."
            )
        return (
            "Perfeito, consultei no banco em tempo real:\n"
            f"{banco_txt}\n\n"
            "Se quiser, já te entrego também um resumo em formato de ação (o que comprar, o que está crítico, e prioridade)."
        )


# ---------- Execução Standalone ----------
if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.title("Controle de Estoque")
    root.geometry("1100x760")
    app = AdvancedStockReport(root)
    app.pack(fill="both", expand=True)
    root.mainloop()

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
