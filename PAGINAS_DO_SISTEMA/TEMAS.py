# -*- coding: utf-8 -*-
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
import json
import math
import colorsys
import re
import time
import importlib
import os
import random
from typing import Dict, Any, Optional, Callable, List, Tuple
import customtkinter as ctk
from PIL import Image, ImageTk

# CORREÇÃO: Import seguro do after_guard
try:
    from PAGINAS_DO_SISTEMA.ui_after_guard import safe_after_cancel
except ImportError:
    def safe_after_cancel(*args, **kwargs):
        pass

# CORREÇÃO: Import seguro do ImageGrab
try:
    from PIL import ImageGrab
    IMAGE_GRAB_AVAILABLE = True
except ImportError:
    IMAGE_GRAB_AVAILABLE = False
    ImageGrab = None

# CORREÇÃO: Sistema de logging corrigido - usa __file__ apenas para referência, não para criar pastas
LOGGER = None
try:
    from PAGINAS_DO_SISTEMA.LOG_SISTEMA import get_logger
    # CORREÇÃO: Usa o diretório base correto para os logs
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOGGER = get_logger(base_dir)
except Exception as e:
    print(f"Logger não disponível: {e}")
    LOGGER = None

HEX_RE = re.compile(r"^#([0-9a-fA-F]{6})$")

CORES_BOTOES_PADRAO = {
    "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
    "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
    "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
    "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
    "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
    "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
    "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
    "botao_export_pdf": "#F59E0B"
}

CORES_BOTOES_CLASSICO_CLARO = {
    "botao_salvar": "#0B7F4F", "botao_excluir": "#C83737", "botao_novo": "#2F6FD6",
    "botao_imprimir": "#5F5F6A", "botao_pdf": "#9A6500", "botao_editar": "#4B5563",
    "botao_visualizar": "#4B5563", "botao_confirmar": "#0B7F4F", "botao_cancelar": "#6B7280",
    "botao_exportar": "#4B5563", "botao_importar": "#4B5563", "botao_configurar": "#6B7280",
    "botao_ajuda": "#4B5563", "botao_filtrar": "#4B5563", "botao_limpar": "#9A6500",
    "botao_voltar": "#6B7280", "botao_avancar": "#0B7F4F", "botao_adiantamento": "#0B7F4F",
    "botao_comprovante": "#5F5F6A", "botao_buscar": "#2F6FD6", "botao_export_csv": "#007C89",
    "botao_export_pdf": "#9A6500"
}

CAMPOS_PADRAO = [
    "primaria", "secundaria", "terciaria", "fundo", "texto", "destaque",
    "sucesso", "alerta", "borda", "hover", "selecao",
] + list(CORES_BOTOES_PADRAO.keys())

LABELS_CAMPOS_PADRAO = {
    "primaria": "Primária", "secundaria": "Secundária", "terciaria": "Terciária",
    "fundo": "Fundo", "texto": "Texto", "destaque": "Destaque", "sucesso": "Sucesso",
    "alerta": "Alerta", "borda": "Borda", "hover": "Hover", "selecao": "Seleção",
    "botao_salvar": "Botão Salvar", "botao_excluir": "Botão Excluir", "botao_novo": "Botão Novo",
    "botao_imprimir": "Botão Imprimir", "botao_pdf": "Botão PDF", "botao_editar": "Botão Editar",
    "botao_visualizar": "Botão Visualizar", "botao_confirmar": "Botão Confirmar",
    "botao_cancelar": "Botão Cancelar", "botao_exportar": "Botão Exportar",
    "botao_importar": "Botão Importar", "botao_configurar": "Botão Configurar",
    "botao_ajuda": "Botão Ajuda", "botao_filtrar": "Botão Filtrar", "botao_limpar": "Botão Limpar",
    "botao_voltar": "Botão Voltar", "botao_avancar": "Botão Avançar",
    "botao_adiantamento": "Botão Registrar Adiantamento",
    "botao_comprovante": "Botão Imprimir Comprovante", "botao_buscar": "Botão Buscar",
    "botao_export_csv": "Botão Exportar CSV", "botao_export_pdf": "Botão Exportar PDF"
}

def _valida_hex(s: str) -> bool:
    return bool(HEX_RE.match(s or ""))

def get_contraste_texto(cor_fundo: str) -> str:
    try:
        if not cor_fundo or not isinstance(cor_fundo, str):
            return "#000000"
        hex_color = cor_fundo.lstrip('#')
        if len(hex_color) != 6:
            return "#000000"
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        def linear(canal: int) -> float:
            valor = canal / 255
            return valor / 12.92 if valor <= 0.03928 else ((valor + 0.055) / 1.055) ** 2.4

        luminancia = 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)
        contraste_preto = (luminancia + 0.05) / 0.05
        contraste_branco = 1.05 / (luminancia + 0.05)
        return "#000000" if contraste_preto >= contraste_branco else "#FFFFFF"
    except Exception:
        return "#000000"

def _cor_hex_visivel(cor) -> str:
    """Retorna a cor hexadecimal ativa quando o CustomTkinter usa par claro/escuro."""
    try:
        if isinstance(cor, (tuple, list)):
            if not cor:
                return ""
            indice = 1 if ctk.get_appearance_mode().lower() == "dark" and len(cor) > 1 else 0
            preferida = str(cor[indice] or "")
            if _valida_hex(preferida):
                return preferida
            for item in cor:
                item = str(item or "")
                if _valida_hex(item):
                    return item
            return preferida
        return str(cor or "")
    except Exception:
        return str(cor or "")

def texto_contraste_para_fundo(cor_fundo, fallback: str = "#000000") -> str:
    cor = _cor_hex_visivel(cor_fundo)
    if _valida_hex(cor):
        return get_contraste_texto(cor)
    return fallback

def is_dark_color(cor_hex: str) -> bool:
    try:
        if not cor_hex or not isinstance(cor_hex, str):
            return False
        hex_color = cor_hex.lstrip("#")
        if len(hex_color) != 6:
            return False
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        luminancia = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        return luminancia < 0.5
    except Exception:
        return False

def ajustar_hover(cor_base: str, fator: float = 0.8) -> str:
    try:
        if not cor_base or not isinstance(cor_base, str):
            return cor_base
        hex_color = cor_base.lstrip('#')
        if len(hex_color) != 6:
            return cor_base
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, min(255, int(r * fator)))
        g = max(0, min(255, int(g * fator)))
        b = max(0, min(255, int(b * fator)))
        return f"#{r:02x}{g:02x}{b:02x}".upper()
    except Exception:
        return cor_base


def _realcar_cor(self, hex_color: str, factor: float = 1.2) -> str:
    """Clareia uma cor hex para criar hover realçado."""
    try:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)

        # Clareia a cor
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))

        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return hex_color

def _blend(base_hex: str, target_hex: str, t: float) -> str:
    """Mistura duas cores hex."""
    try:
        base = base_hex.lstrip("#")
        target = target_hex.lstrip("#")
        if len(base) != 6 or len(target) != 6:
            return base_hex
        br, bg, bb = (int(base[0:2],16), int(base[2:4],16), int(base[4:6],16))
        tr, tg, tb = (int(target[0:2],16), int(target[2:4],16), int(target[4:6],16))
        r = int(br + (tr - br) * t)
        g = int(bg + (tg - bg) * t)
        b = int(bb + (tb - bb) * t)
        return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}".upper()
    except Exception:
        return base_hex

def _rgb_from_hex(cor_hex: str):
    try:
        cor = (cor_hex or "").lstrip("#")
        if len(cor) != 6:
            return None
        return tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return None

def _distancia_cores(cor_a: str, cor_b: str) -> float:
    rgb_a = _rgb_from_hex(cor_a)
    rgb_b = _rgb_from_hex(cor_b)
    if not rgb_a or not rgb_b:
        return 999.0
    return sum((a - b) ** 2 for a, b in zip(rgb_a, rgb_b)) ** 0.5

def _cor_fundo_widget(widget) -> str:
    atual = getattr(widget, "master", None)
    while atual is not None:
        try:
            cor = _cor_hex_visivel(atual.cget("fg_color"))
            if _valida_hex(cor):
                return cor
        except Exception:
            pass
        try:
            cor = str(atual.cget("bg") or "")
            if _valida_hex(cor):
                return cor
        except Exception:
            pass
        atual = getattr(atual, "master", None)

    try:
        app = widget.winfo_toplevel()
        cor = getattr(app, "cor_fundo", "")
        if _valida_hex(str(cor)):
            return str(cor)
    except Exception:
        pass
    return "#FFFFFF"

def _cor_acao_visivel(widget) -> str:
    fundo = _cor_fundo_widget(widget)
    try:
        app = widget.winfo_toplevel()
        for attr in ("cor_primaria", "cor_destaque", "cor_sucesso"):
            cor = getattr(app, attr, "")
            if _valida_hex(str(cor)) and _distancia_cores(str(cor), fundo) >= 36:
                return str(cor)
    except Exception:
        pass
    return "#2563EB"

def _botao_precisa_fundo_visivel(widget, fg_real: str) -> bool:
    if not _valida_hex(fg_real):
        return True
    fundo = _cor_fundo_widget(widget)
    return _distancia_cores(fg_real, fundo) < 36

BOTAO_KEYWORDS = (
    ("botao_excluir", ("excluir", "deletar", "remover", "apagar", "inativar", "estornar", "reprovar")),
    ("botao_cancelar", ("cancelar", "fechar", "sair", "nao", "não")),
    ("botao_salvar", ("salvar", "gravar")),
    ("botao_novo", ("novo", "nova", "criar")),
    ("botao_confirmar", ("confirmar", "ok", "aplicar", "finalizar", "concluir", "aprovar")),
    ("botao_adiantamento", ("adiantamento", "adiantar")),
    ("botao_buscar", ("buscar", "pesquisar", "procurar", "localizar", "consultar", "recarregar", "atualizar")),
    ("botao_filtrar", ("filtrar", "filtro")),
    ("botao_limpar", ("limpar", "resetar")),
    ("botao_importar", ("importar",)),
    ("botao_export_pdf", ("exportar pdf", "gerar pdf", "pdf")),
    ("botao_export_csv", ("exportar csv", "csv", "excel")),
    ("botao_exportar", ("exportar",)),
    ("botao_imprimir", ("imprimir", "impressao", "impressão")),
    ("botao_comprovante", ("comprovante", "recibo")),
    ("botao_editar", ("editar", "alterar")),
    ("botao_visualizar", ("visualizar", "detalhes", "abrir", "ver")),
    ("botao_voltar", ("voltar", "anterior")),
    ("botao_avancar", ("avancar", "avançar", "proximo", "próximo")),
    ("botao_configurar", ("configurar", "configuracoes", "configurações")),
    ("botao_ajuda", ("ajuda", "suporte")),
)

def _cor_botao_tema(widget, chave: str) -> str:
    padrao = CORES_BOTOES_PADRAO.get(chave, CORES_BOTOES_PADRAO["botao_buscar"])
    try:
        app = widget.winfo_toplevel()
        valor = getattr(app, f"cor_{chave}", None)
        if _valida_hex(str(valor)):
            return str(valor)
    except Exception:
        pass
    return padrao

def _hover_botao(cor_base: str) -> str:
    """Hover consistente: sempre uma variação mais escura da cor da ação."""
    if not _valida_hex(cor_base):
        return cor_base
    return ajustar_hover(cor_base, 0.82)

def _luminancia_relativa(cor_hex: str) -> float:
    rgb = _rgb_from_hex(cor_hex) or (0, 0, 0)

    def linear(canal: int) -> float:
        valor = canal / 255
        return valor / 12.92 if valor <= 0.03928 else ((valor + 0.055) / 1.055) ** 2.4

    return 0.2126 * linear(rgb[0]) + 0.7152 * linear(rgb[1]) + 0.0722 * linear(rgb[2])

def _contraste_ratio(cor_a: str, cor_b: str) -> float:
    lum_a = _luminancia_relativa(cor_a)
    lum_b = _luminancia_relativa(cor_b)
    maior = max(lum_a, lum_b)
    menor = min(lum_a, lum_b)
    return (maior + 0.05) / (menor + 0.05)

def _cor_botao_com_texto_branco(cor_base: str) -> str:
    """Escurece a cor da ação até texto branco ficar legível e padronizado."""
    if not _valida_hex(cor_base):
        return "#2563EB"
    cor = cor_base
    for _ in range(8):
        if _contraste_ratio(cor, "#FFFFFF") >= 4.5:
            return cor
        cor = ajustar_hover(cor, 0.86)
    return cor

def estilo_botao_por_texto(widget, texto: str | None = None) -> dict[str, str]:
    """Define o estilo semântico padrão para botões comuns do sistema."""
    texto_norm = _normalizar_texto_botao(texto if texto is not None else widget.cget("text"))
    chave = "botao_buscar"
    for chave_candidata, palavras in BOTAO_KEYWORDS:
        if any(palavra in texto_norm for palavra in palavras):
            chave = chave_candidata
            break

    fg = _cor_botao_tema(widget, chave)
    fundo = _cor_fundo_widget(widget)
    if _distancia_cores(fg, fundo) < 40:
        fg = _cor_botao_tema(widget, "botao_buscar")
    if _distancia_cores(fg, fundo) < 40:
        fg = "#2563EB"

    fg = _cor_botao_com_texto_branco(fg)
    hover = _hover_botao(fg)
    return {
        "fg_color": fg,
        "hover_color": hover,
        "text_color": "#FFFFFF",
        "text_color_hover": "#FFFFFF",
        "text_color_disabled": "#9CA3AF" if is_dark_color(fundo) else "#374151",
        "border_color": ajustar_hover(fg, 0.70),
    }

def aplicar_estilo_treeview(*, style=None, prefixo="Treeview", cor_fundo="#FFFFFF",
                            cor_linhas="#F5F5F5", cor_cabecalho="#0D6EFD",
                            cor_texto=None, cor_borda="#CED4DA", cor_selecao="#0D6EFD",
                            altura_linha=25):
    """Aplica estilo padronizado ao Treeview."""
    try:
        style = style or ttk.Style()
        try:
            style.theme_use("clam")
        except:
            pass

        tema_escuro = is_dark_color(cor_fundo)

        if tema_escuro:
            tree_bg = cor_linhas
            tree_fg = cor_texto or get_contraste_texto(cor_linhas)
            field_bg = cor_linhas
            heading_bg = cor_cabecalho
            heading_fg = get_contraste_texto(heading_bg)
            select_bg = _blend(heading_bg, "#FFFFFF", 0.18)
            select_fg = get_contraste_texto(select_bg)
            border = cor_borda
        else:
            tree_bg = "#FFFFFF"
            tree_fg = "#000000"
            field_bg = "#FFFFFF"
            heading_bg = "#EEEEEE"
            heading_fg = "#000000"
            select_bg = "#B7D7FF"
            select_fg = "#000000"
            border = "#C7C7C7"

        style.configure(
            prefixo,
            background=tree_bg,
            fieldbackground=field_bg,
            foreground=tree_fg,
            rowheight=26,
            bordercolor=border,
            borderwidth=1,
            font=("Arial", 10),
            relief="solid",
        )

        style.configure(
            f"{prefixo}.Heading",
            background=heading_bg,
            foreground=heading_fg,
            relief="flat",
            font=("Arial", 10, "bold"),
            borderwidth=0,
            padding=(8, 6),
        )

        style.map(
            prefixo,
            background=[("selected", select_bg)],
            foreground=[("selected", select_fg)],
        )

        if (heading_fg or "").lower() in ("#000", "#000000", "black"):
            heading_hover_bg = _blend(heading_bg, "#000000", 0.14)
            heading_pressed_bg = _blend(heading_bg, "#000000", 0.24)
        else:
            heading_hover_bg = _blend(heading_bg, "#FFFFFF", 0.14)
            heading_pressed_bg = _blend(heading_bg, "#FFFFFF", 0.24)

        style.map(
            f"{prefixo}.Heading",
            background=[("active", heading_hover_bg), ("pressed", heading_pressed_bg)],
            foreground=[("active", heading_fg), ("pressed", heading_fg)],
            relief=[("active", "flat"), ("pressed", "flat")],
        )

        return style
    except Exception as e:
        if LOGGER:
            LOGGER.error(f"Erro ao aplicar estilo Treeview: {e}")
        return None


def padronizar_treeview(tree: ttk.Treeview, prefixo: str | None = None):
    """Padroniza um Treeview com as cores do tema atual."""
    try:
        app = tree.winfo_toplevel()
        cor_fundo = getattr(app, "cor_fundo", "#FFFFFF")
        cor_secundaria = getattr(app, "cor_secundaria", "#F5F5F5")
        cor_primaria = getattr(app, "cor_primaria", "#0D6EFD")
        cor_texto = getattr(app, "cor_texto", get_contraste_texto(cor_fundo))
        cor_borda = getattr(app, "cor_borda", "#CED4DA")

        nome_prefixo = prefixo or tree.cget("style") or "Treeview"

        estilo = aplicar_estilo_treeview(
            style=ttk.Style(),
            prefixo=nome_prefixo,
            cor_fundo=cor_fundo,
            cor_linhas=cor_secundaria,
            cor_cabecalho=cor_primaria,
            cor_texto=cor_texto,
            cor_borda=cor_borda,
            cor_selecao=cor_primaria,
        )

        if estilo:
            tree.configure(style=nome_prefixo)
    except Exception as e:
        if LOGGER:
            LOGGER.error(f"Erro ao padronizar Treeview: {e}")


def padronizar_treeviews_container(widget):
    """Padroniza todas as Treeviews de um container recursivamente."""
    try:
        if isinstance(widget, ttk.Treeview):
            padronizar_treeview(widget)

        for child in widget.winfo_children():
            padronizar_treeviews_container(child)
    except Exception as e:
        if LOGGER:
            LOGGER.error(f"Erro ao padronizar Treeviews do container: {e}")


def padronizar_botoes_container(widget):
    """Padroniza todos os botões de um container recursivamente."""
    try:
        if isinstance(widget, ctk.CTkButton):
            padronizar_botao(widget)

        for child in widget.winfo_children():
            padronizar_botoes_container(child)
    except Exception as e:
        if LOGGER:
            LOGGER.error(f"Erro ao padronizar botões: {e}")


def padronizar_botao(widget: ctk.CTkButton):
    """Aplica padrão de cores a um botão baseado no texto."""
    try:
        texto = widget.cget("text")
        if not texto:
            return

        estilo = estilo_botao_por_texto(widget, texto)
        widget.configure(
            fg_color=estilo["fg_color"],
            hover_color=estilo["hover_color"],
            text_color=estilo["text_color"],
            text_color_disabled=estilo["text_color_disabled"],
            border_color=estilo["border_color"],
            border_width=0,
        )
        _aplicar_hover_texto_botao(widget, estilo["text_color"], estilo["text_color_hover"])
        return

        texto_norm = _normalizar_texto_botao(texto)

        negativos = ("excluir", "deletar", "remover", "apagar", "inativar", "cancelar")
        positivos = ("salvar", "adicionar", "buscar", "cadastrar", "importar", "confirmar")
        destaques = ("exportar", "imprimir", "pdf", "gerar pdf", "comprovante", "visualizar pdf", "editar")

        if any(chave in texto_norm for chave in negativos):
            estilo = {
                "fg_color": "#FA0000",
                "hover_color": "#7A0101",
                "text_color": get_contraste_texto("#FA0000"),
                "text_color_hover": get_contraste_texto("#7A0101"),
            }
        elif any(chave in texto_norm for chave in positivos):
            estilo = {
                "fg_color": "#1B8305",
                "hover_color": "#2A671F",
                "text_color": get_contraste_texto("#1B8305"),
                "text_color_hover": get_contraste_texto("#2A671F"),
            }
        elif any(chave in texto_norm for chave in destaques):
            estilo = {
                "fg_color": "#FF5C00",
                "hover_color": "#6E2800",
                "text_color": get_contraste_texto("#FF5C00"),
                "text_color_hover": get_contraste_texto("#6E2800"),
            }
        else:
            estilo = {
                "fg_color": "#7AB8F5",
                "hover_color": "#5A9BDF",
                "text_color": get_contraste_texto("#7AB8F5"),
                "text_color_hover": get_contraste_texto("#5A9BDF"),
            }

        widget.configure(
            fg_color=estilo["fg_color"],
            hover_color=estilo["hover_color"],
            text_color=estilo["text_color"],
            border_width=0,
        )
        _aplicar_hover_texto_botao(widget, estilo["text_color"], estilo["text_color_hover"])
    except Exception:
        pass


def _normalizar_texto_botao(texto: str) -> str:
    """Normaliza texto do botão para comparação."""
    try:
        import unicodedata
        texto_limpo = (texto or "").strip().lower()
        texto_limpo = unicodedata.normalize("NFKD", texto_limpo)
        texto_limpo = "".join(ch for ch in texto_limpo if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", texto_limpo)
    except Exception:
        return (texto or "").strip().lower()


def _aplicar_hover_texto_botao(widget: ctk.CTkButton, normal: str, hover: str):
    """Configura mudança de cor do texto no hover."""
    widget._opera_texto_normal = normal
    widget._opera_texto_hover = hover
    if getattr(widget, "_opera_hover_texto", None):
        return

    def on_enter(_event=None):
        try:
            widget.configure(text_color=getattr(widget, "_opera_texto_hover", hover))
        except Exception:
            pass

    def on_leave(_event=None):
        try:
            widget.configure(text_color=getattr(widget, "_opera_texto_normal", normal))
        except Exception:
            pass

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)
    widget._opera_hover_texto = True


def remover_bordas_botoes_tema(widget):
    """Remove bordas, contornos e outlines de todos os botões."""
    if getattr(widget, "_opera_preservar_tema", False):
        return

    botoes = (
        ctk.CTkButton,
        ctk.CTkOptionMenu,
        ctk.CTkComboBox,
        ctk.CTkSegmentedButton,
        ctk.CTkSwitch,
    )

    try:
        estilo_ttk = ttk.Style()
        estilo_ttk.configure(
            "TButton",
            relief=tk.FLAT,
            borderwidth=0,
            focusthickness=0,
            highlightthickness=0,
            padding=6,
        )
        estilo_ttk.configure(
            "Opera.TButton",
            relief=tk.FLAT,
            borderwidth=0,
            focusthickness=0,
            highlightthickness=0,
            padding=6,
        )
        estilo_ttk.map(
            "TButton",
            relief=[("pressed", tk.FLAT), ("active", tk.FLAT)],
            bordercolor=[("pressed", ""), ("active", "")],
        )
        estilo_ttk.map(
            "Opera.TButton",
            relief=[("pressed", tk.FLAT), ("active", tk.FLAT)],
            bordercolor=[("pressed", ""), ("active", "")],
        )
    except Exception:
        pass

    try:
        if isinstance(widget, botoes):
            try:
                fg = widget.cget("fg_color") if hasattr(widget, "cget") else None
                hover = widget.cget("hover_color") if hasattr(widget, "cget") else None
                texto = widget.cget("text_color") if hasattr(widget, "cget") else None
                texto_final = texto if texto not in (None, "") else None
                texto_hover = texto_final
                texto_botao = ""
                try:
                    texto_botao = str(widget.cget("text") or "").strip()
                except Exception:
                    texto_botao = ""

                if isinstance(widget, ctk.CTkButton) and texto_botao:
                    estilo = estilo_botao_por_texto(widget, texto_botao)
                    fg = estilo["fg_color"]
                    hover = estilo["hover_color"]
                    texto_final = estilo["text_color"]
                    texto_hover = estilo["text_color_hover"]

                if isinstance(widget, (ctk.CTkButton, ctk.CTkOptionMenu, ctk.CTkComboBox, ctk.CTkSegmentedButton)):
                    fg_real = _cor_hex_visivel(fg)
                    hover_real = _cor_hex_visivel(hover or fg)
                    if isinstance(widget, ctk.CTkButton) and texto_botao and _botao_precisa_fundo_visivel(widget, fg_real):
                        fg = _cor_acao_visivel(widget)
                        hover = ajustar_hover(fg, 0.82)
                        fg_real = _cor_hex_visivel(fg)
                        hover_real = _cor_hex_visivel(hover)
                    if _valida_hex(fg_real):
                        texto_final = get_contraste_texto(fg_real)
                        texto_hover = get_contraste_texto(hover_real) if _valida_hex(hover_real) else texto_final

                widget.configure(
                    border_width=0,
                    corner_radius=getattr(widget, "corner_radius", 8),
                    fg_color=fg or "transparent",
                    hover_color=hover or fg or "transparent",
                    text_color=texto_final,
                )
                if isinstance(widget, ctk.CTkButton):
                    try:
                        fundo_desabilitado = _blend(_cor_hex_visivel(fg), _cor_fundo_widget(widget), 0.45)
                        widget.configure(text_color_disabled=get_contraste_texto(fundo_desabilitado))
                    except Exception:
                        pass
                if isinstance(widget, ctk.CTkButton) and texto_final:
                    _aplicar_hover_texto_botao(widget, texto_final, texto_hover or texto_final)
                try:
                    widget.configure(highlightthickness=0)
                except Exception:
                    pass
            except Exception:
                pass

        if isinstance(widget, tk.Button):
            try:
                widget.configure(
                    borderwidth=0,
                    highlightthickness=0,
                    relief=tk.FLAT,
                )
            except Exception:
                pass

        if isinstance(widget, ttk.Button):
            try:
                widget.configure(style="Opera.TButton")
                widget.state(["!focus"])
            except Exception:
                pass

        if hasattr(widget, "winfo_children"):
            for child in widget.winfo_children():
                remover_bordas_botoes_tema(child)

    except Exception as e:
        if LOGGER:
            LOGGER.error(f"Erro ao remover bordas: {e}")

def aplicar_tags_alternadas(tree: ttk.Treeview, cor_par: str, cor_impar: str):
    """Configura tags de linhas alternadas com contraste automático."""
    try:
        tree.tag_configure("evenrow", background=cor_par, foreground=get_contraste_texto(cor_par))
        tree.tag_configure("oddrow", background=cor_impar, foreground=get_contraste_texto(cor_impar))

        for i, item in enumerate(tree.get_children()):
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            tree.item(item, tags=(tag,))
    except Exception as e:
        if LOGGER:
            LOGGER.error(f"Erro ao aplicar tags alternadas: {e}")


class ModuloPaletas:
    def __init__(self):
        self.PADROES: Dict[str, Dict[str, str]] = {}
        self.temas_originais: Dict[str, Dict[str, str]] = {}
        self.custom: Dict[str, Dict[str, str]] = {}
        self._cache_paleta_completa: Dict[str, Dict[str, str]] = {}
        self._carregar_temas_padrao()

    def _carregar_temas_padrao(self):
        self.PADROES = {
            # ==========================================================
            #  TEMA: AZUL OCEANO
            # ==========================================================
            "Azul Oceano": {
                "primaria": "#0D1B2A", "secundaria": "#1B263B", "terciaria": "#415A77",
                "fundo": "#0B1320", "texto": "#E0E1DD", "destaque": "#3A86FF",
                "sucesso": "#3BCF8E", "alerta": "#EF476F", "borda": "#2E4057",
                "hover": "#253041", "selecao": "#3A86FF", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  TEMA CLÁSSICO CLARO
            # ==========================================================
            "CLÁSSICO CLARO": {
                "primaria": "#F4F4F5", "secundaria": "#D4D4D8", "terciaria": "#A1A1AA",
                "fundo": "#FFFFFF", "texto": "#111827", "destaque": "#4B5563",
                "selecao": "#AFAFAF", "sucesso": "#2E7D32", "alerta": "#C62828",
                "borda": "#9CA3AF", "hover": "#E4E4E7", **CORES_BOTOES_CLASSICO_CLARO
            },

            # ==========================================================
            #  CINZA OCEANO ESCURO
            # ==========================================================
            "Cinza Oceano Escuro": {
                "primaria": "#1A1A1A", "secundaria": "#242424", "terciaria": "#3E3E3E",
                "fundo": "#141414", "texto": "#E0E1DD", "destaque": "#6B6B6B",
                "sucesso": "#3BCF8E", "alerta": "#EF476F", "borda": "#353535",
                "hover": "#2A2A2A", "selecao": "#6B6B6B", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  GRAFITE OCEANO
            # ==========================================================
            "Grafite Oceano": {
                "primaria": "#0F0F0F", "secundaria": "#1C1C1C", "terciaria": "#333333",
                "fundo": "#0A0A0A", "texto": "#E0E1DD", "destaque": "#5A5A5A",
                "sucesso": "#3BCF8E", "alerta": "#EF476F", "borda": "#2B2B2B",
                "hover": "#1F1F1F", "selecao": "#5A5A5A", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  CARVÃO OCEANO
            # ==========================================================
            "Carvão Oceano": {
                "primaria": "#121212", "secundaria": "#1F1F1F", "terciaria": "#3A3A3A",
                "fundo": "#0D0D0D", "texto": "#E0E1DD", "destaque": "#4D4D4D",
                "sucesso": "#3BCF8E", "alerta": "#EF476F", "borda": "#2E2E2E",
                "hover": "#232323", "selecao": "#4D4D4D", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  CINZA OCEANO CLARO
            # ==========================================================
            "Cinza Oceano Claro": {
                "primaria": "#D5D5D5", "secundaria": "#C2C2C2", "terciaria": "#9E9E9E",
                "fundo": "#E8E8E8", "texto": "#1A1A1A", "destaque": "#6B6B6B",
                "sucesso": "#2E9E6E", "alerta": "#D63854", "borda": "#ABABAB",
                "hover": "#CFCFCF", "selecao": "#6B6B6B", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  PRATA OCEANO
            # ==========================================================
            "Prata Oceano": {
                "primaria": "#BEBEBE", "secundaria": "#ABABAB", "terciaria": "#8A8A8A",
                "fundo": "#D4D4D4", "texto": "#1A1A1A", "destaque": "#5A5A5A",
                "sucesso": "#2E9E6E", "alerta": "#D63854", "borda": "#999999",
                "hover": "#B5B5B5", "selecao": "#5A5A5A", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  NÉVOA OCEANO
            # ==========================================================
            "Névoa Oceano": {
                "primaria": "#C9C9C9", "secundaria": "#B6B6B6", "terciaria": "#949494",
                "fundo": "#DEDEDE", "texto": "#1A1A1A", "destaque": "#636363",
                "sucesso": "#2E9E6E", "alerta": "#D63854", "borda": "#A3A3A3",
                "hover": "#808080", "selecao": "#008000", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  ROSÉ ELEGANTE
            # ==========================================================
            "Rosé Elegante": {
                "primaria": "#2B2233", "secundaria": "#3A2A45", "terciaria": "#5E3C58",
                "fundo": "#241C2B", "texto": "#FFE9F3", "destaque": "#FF5C8A",
                "sucesso": "#72E5C1", "alerta": "#FF7B7B", "borda": "#4B3B55",
                "hover": "#34283F", "selecao": "#FF5C8A", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  TERRA NATURAL
            # ==========================================================
            "Terra Natural": {
                "primaria": "#2E241A", "secundaria": "#3B2F22", "terciaria": "#6B4E3D",
                "fundo": "#221A12", "texto": "#F0E7DD", "destaque": "#D9A441",
                "sucesso": "#7FB069", "alerta": "#CE6A46", "borda": "#4A3A2C",
                "hover": "#3A2D22", "selecao": "#D9A441", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  NOITE URBANA
            # ==========================================================
            "Noite Urbana": {
                "primaria": "#121212", "secundaria": "#1F1F1F", "terciaria": "#3E3E3E",
                "fundo": "#181818", "texto": "#EEEEEE", "destaque": "#BB86FC",
                "sucesso": "#03DAC6", "alerta": "#CF6679", "borda": "#3A3A3A",
                "hover": "#2C2C2C", "selecao": "#BB86FC", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  MINIMAL
            # ==========================================================
            "Minimal": {
                "primaria": "#F5F5F5", "secundaria": "#E0E0E0", "terciaria": "#C2C2C2",
                "fundo": "#FFFFFF", "texto": "#212121", "destaque": "#9E9E9E",
                "sucesso": "#66BB6A", "alerta": "#EF5350", "borda": "#BDBDBD",
                "hover": "#EEEEEE", "selecao": "#9E9E9E", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  ROXO ELEGANTE
            # ==========================================================
            "Roxo Elegante": {
                "primaria": "#1E1327", "secundaria": "#291A36", "terciaria": "#432C56",
                "fundo": "#180F22", "texto": "#EDE7F6", "destaque": "#7C4DFF",
                "sucesso": "#00E5FF", "alerta": "#F06292", "borda": "#352443",
                "hover": "#241633", "selecao": "#7C4DFF", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  VERDE CORPORATIVO
            # ==========================================================
            "Verde Corporativo": {
                "primaria": "#0F241D", "secundaria": "#15342A", "terciaria": "#1F4D3D",
                "fundo": "#0B1A15", "texto": "#E8F5E9", "destaque": "#26A69A",
                "sucesso": "#66BB6A", "alerta": "#FF7043", "borda": "#1A3A2F",
                "hover": "#17362D", "selecao": "#26A69A", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  PRETO E OURO
            # ==========================================================
            "Preto e Ouro": {
                "primaria": "#121212", "secundaria": "#1A1A1A", "terciaria": "#333333",
                "fundo": "#0B0B0B", "texto": "#F6F3E7", "destaque": "#D4AF37",
                "sucesso": "#7CB342", "alerta": "#F4511E", "borda": "#2E2E2E",
                "hover": "#222222", "selecao": "#D4AF37", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  CLÁSSICO
            # ==========================================================
            "Clássico": {
                "primaria": "#20232A", "secundaria": "#2C313C", "terciaria": "#3B4252",
                "fundo": "#1B1E24", "texto": "#ECEFF4", "destaque": "#61AFEF",
                "sucesso": "#98C379", "alerta": "#E06C75", "borda": "#2E3440",
                "hover": "#262B36", "selecao": "#61AFEF", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  NOTURNO
            # ==========================================================
            "NOTURNO": {
                "primaria": "#0C0F14", "secundaria": "#141824", "terciaria": "#1E2635",
                "fundo": "#0B0E13", "texto": "#DDE2E9", "destaque": "#4CC9F0",
                "sucesso": "#2DE2A6", "alerta": "#FF477E", "borda": "#1A2030",
                "hover": "#171C28", "selecao": "#4CC9F0", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  SLATE PRO
            # ==========================================================
            "Slate Pro": {
                "primaria": "#1F2937", "secundaria": "#273246", "terciaria": "#3B4B63",
                "fundo": "#151A24", "texto": "#E5E7EB", "destaque": "#60A5FA",
                "sucesso": "#34D399", "alerta": "#F87171", "borda": "#2C3647",
                "hover": "#232C3B", "selecao": "#60A5FA", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  GRAFITE CLEAN
            # ==========================================================
            "Grafite Clean": {
                "primaria": "#222222", "secundaria": "#2C2C2C", "terciaria": "#3A3A3A",
                "fundo": "#1A1A1A", "texto": "#EDEDED", "destaque": "#8AB4F8",
                "sucesso": "#57D38C", "alerta": "#FF6B6B", "borda": "#333333",
                "hover": "#2A2A2A", "selecao": "#8AB4F8", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  AÇO AZUL
            # ==========================================================
            "Aço Azul": {
                "primaria": "#16212F", "secundaria": "#1E2B3C", "terciaria": "#2C3E55",
                "fundo": "#111925", "texto": "#E6EDF5", "destaque": "#4EA8DE",
                "sucesso": "#2DD4BF", "alerta": "#FB7185", "borda": "#233247",
                "hover": "#1B2738", "selecao": "#4EA8DE", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  OLIVA URBANO
            # ==========================================================
            "Oliva Urbano": {
                "primaria": "#172017", "secundaria": "#1F2A1F", "terciaria": "#2C3A2C",
                "fundo": "#121A12", "texto": "#E9F5EA", "destaque": "#7FB069",
                "sucesso": "#86EFAC", "alerta": "#F59E0B", "borda": "#223123",
                "hover": "#1A241A", "selecao": "#7FB069", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  COBALTO PRO
            # ==========================================================
            "Cobalto Pro": {
                "primaria": "#0F1626", "secundaria": "#172035", "terciaria": "#22314F",
                "fundo": "#0B1120", "texto": "#E2E8F0", "destaque": "#3B82F6",
                "sucesso": "#10B981", "alerta": "#EF4444", "borda": "#1B2740",
                "hover": "#132037", "selecao": "#3B82F6", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  PETRÓLEO
            # ==========================================================
            "Petróleo": {
                "primaria": "#102022", "secundaria": "#173034", "terciaria": "#22464C",
                "fundo": "#0B1719", "texto": "#E3F2F4", "destaque": "#22D3EE",
                "sucesso": "#34D399", "alerta": "#F59E0B", "borda": "#1A3236",
                "hover": "#13282C", "selecao": "#22D3EE", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  CHUMBO & LARANJA
            # ==========================================================
            "Chumbo & Laranja": {
                "primaria": "#1A1E24", "secundaria": "#232833", "terciaria": "#2E3542",
                "fundo": "#141821", "texto": "#EDEFF3", "destaque": "#FB923C",
                "sucesso": "#22C55E", "alerta": "#EF4444", "borda": "#2A303C",
                "hover": "#1D2230", "selecao": "#FB923C", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  NEVE AZUL
            # ==========================================================
            "Neve Azul": {
                "primaria": "#E9EEF5", "secundaria": "#DDE6F1", "terciaria": "#C9D4E6",
                "fundo": "#F6FAFF", "texto": "#1F2937", "destaque": "#2563EB",
                "sucesso": "#059669", "alerta": "#DC2626", "borda": "#CBD5E1",
                "hover": "#E2EAF6", "selecao": "#2563EB", **CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  TITANIUM
            # ==========================================================
            "Titanium": {
                "primaria": "#1C1F26", "secundaria": "#262A33", "terciaria": "#313643",
                "fundo": "#171A21", "texto": "#E6E8EB", "destaque": "#9AA4FF",
                "sucesso": "#5EEAD4", "alerta": "#F87171", "borda": "#2A2E38",
                "hover": "#1F2330", "selecao": "#9AA4FF", **CORES_BOTOES_PADRAO
            }
        }
        self.temas_originais = {k: dict(v) for k, v in self.PADROES.items()}
        self._cache_paleta_completa.update(self.PADROES)

    def obter_tema(self, nome_tema: str) -> Optional[Dict[str, str]]:
        if nome_tema in self.custom:
            return self.custom[nome_tema]
        if nome_tema in self.PADROES:
            return self.PADROES[nome_tema]
        return None

    def salvar_tema_personalizado(self, nome: str, paleta: Dict[str, str]) -> bool:
        self.custom[nome] = dict(paleta)
        self._cache_paleta_completa[nome] = self.custom[nome]
        return True

    def remover_tema_personalizado(self, nome: str) -> bool:
        if nome in self.custom:
            del self.custom[nome]
            self._cache_paleta_completa.pop(nome, None)
            return True
        return False

class BotaoPadronizado:
    @staticmethod
    def criar_botao(master, texto=None, tipo="padrao", **kwargs):
        if texto is None and "text" in kwargs:
            texto = kwargs.pop("text")
        if texto is None:
            texto = ""

        config_padrao = {
            "height": 32, "font": ("Arial", 12), "corner_radius": 8, "border_width": 0
        }

        app = BotaoPadronizado._get_app(master)
        cores_tema = BotaoPadronizado._extrair_cores_tema(app)
        cor_padrao_fundo = cores_tema.get("secundaria", "#2C2C2C")

        config_tipo = {
            "padrao": {
                "fg_color": cor_padrao_fundo,
                "hover_color": cores_tema.get("hover", "#3A3A3A"),
                "text_color": texto_contraste_para_fundo(cor_padrao_fundo, cores_tema.get("texto", "#FFFFFF")),
                "border_color": cores_tema.get("borda", "#333333")
            }
        }

        for tipo_btn, cor_padrao in CORES_BOTOES_PADRAO.items():
            cor_especifica = cores_tema.get(tipo_btn, cor_padrao)
            config_tipo[tipo_btn.replace("botao_", "")] = {
                "fg_color": cor_especifica,
                "hover_color": ajustar_hover(cor_especifica),
                "text_color": get_contraste_texto(cor_especifica),
                "border_color": ajustar_hover(cor_especifica, 0.7)
            }

        config_final = {**config_padrao, **config_tipo.get(tipo, config_tipo["padrao"]), **kwargs}
        return ctk.CTkButton(master, text=texto, **config_final)

    @staticmethod
    def _get_app(widget):
        try:
            return widget.winfo_toplevel()
        except:
            root = widget
            while hasattr(root, 'master') and root.master:
                root = root.master
            return root

    @staticmethod
    def _extrair_cores_tema(app) -> Dict[str, str]:
        cores = {}
        attrs_cores = (["primaria", "secundaria", "terciaria", "fundo", "texto",
                        "destaque", "sucesso", "alerta", "borda", "hover", "selecao"] +
                       list(CORES_BOTOES_PADRAO.keys()))
        for attr in attrs_cores:
            try:
                valor = getattr(app, f'cor_{attr}', None)
                if valor and isinstance(valor, str):
                    cores[attr] = valor
            except:
                continue
        return cores

class _Chip(ctk.CTkButton):
    def __init__(self, master, text, command, is_active=False, **kw):
        self.label_text = text
        self.is_active = is_active
        display_text = f"● {text}" if is_active else text
        super().__init__(
            master, text=display_text, command=command,
            height=22, corner_radius=8, font=("Arial", 10, "normal"), **kw
        )
        try:
            self._opera_preservar_tema = True
            self._opera_keep_custom_color = True
        except Exception:
            pass

    def set_active(self, active: bool):
        if self.is_active != active:
            self.is_active = active
            self.configure(text=f"● {self.label_text}" if active else self.label_text)

class PreviewPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.highlighted_element = None
        self.original_border_widths = {}
        self.widgets_referencia: Dict[str, ctk.CTkButton] = {}
        self._build_preview()

    def _build_preview(self):
        self.title_label = ctk.CTkLabel(self, text="Preview do Tema", font=("Arial", 14, "bold"))
        self.title_label.pack(pady=(10, 5))

        self.preview_container = ctk.CTkFrame(self, corner_radius=8, border_width=2)
        self.preview_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.sample_label = ctk.CTkLabel(self.preview_container, text="Texto de Exemplo", font=("Arial", 12))
        self.sample_label.pack(pady=10, padx=10)

        self.sample_button = ctk.CTkButton(self.preview_container, text="Botão Secundário", font=("Arial", 11))
        self.sample_button.pack(pady=5, padx=10)

        self.sample_entry = ctk.CTkEntry(self.preview_container, placeholder_text="Campo de entrada")
        self.sample_entry.pack(pady=5, padx=10, fill="x")

        self.tertiary_frame = ctk.CTkFrame(self.preview_container, corner_radius=6, border_width=2)
        self.tertiary_frame.pack(pady=10, padx=10, fill="x")
        self.tertiary_label = ctk.CTkLabel(self.tertiary_frame, text="Frame Terciário", font=("Arial", 10))
        self.tertiary_label.pack(pady=8)

        self.border_frame = ctk.CTkFrame(self.preview_container, corner_radius=6, border_width=3)
        self.border_frame.pack(pady=5, padx=10, fill="x")
        self.border_label = ctk.CTkLabel(self.border_frame, text="Exemplo de Borda", font=("Arial", 9))
        self.border_label.pack(pady=6)

        status_frame = ctk.CTkFrame(self.preview_container, fg_color="transparent")
        status_frame.pack(pady=10, padx=10)
        self.success_btn = ctk.CTkButton(status_frame, text="Sucesso", width=80)
        self.success_btn.pack(side="left", padx=5)
        self.alert_btn = ctk.CTkButton(status_frame, text="Alerta", width=80)
        self.alert_btn.pack(side="left", padx=5)
        self.highlight_btn = ctk.CTkButton(status_frame, text="Destaque", width=80)
        self.highlight_btn.pack(side="left", padx=5)

        self._criar_botoes_referencia()

    def _criar_botoes_referencia(self):
        ref_frame = ctk.CTkFrame(self.preview_container, fg_color="transparent")
        ref_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(ref_frame, text="Botões de Referência:", font=("Arial", 12, "bold")).pack(anchor="w")

        grid_frame = ctk.CTkFrame(ref_frame, fg_color="transparent")
        grid_frame.pack(fill="x", pady=5)

        textos = {
            "botao_salvar": "Salvar", "botao_excluir": "Excluir", "botao_novo": "Novo",
            "botao_imprimir": "Imprimir", "botao_pdf": "PDF", "botao_editar": "Editar",
            "botao_cancelar": "Cancelar", "botao_confirmar": "Confirmar"
        }
        for i, (chave, texto) in enumerate(textos.items()):
            btn = ctk.CTkButton(grid_frame, text=texto, width=70, height=28)
            btn.grid(row=i//4, column=i%4, padx=2, pady=2)
            self.widgets_referencia[chave] = btn

    def update_preview(self, colors: Dict[str, str]):
        try:
            primaria = colors.get("primaria", "#1F1F1F")
            secundaria = colors.get("secundaria", "#2C2C2C")
            terciaria = colors.get("terciaria", "#3A3A3A")
            texto = colors.get("texto", "#EEEEEE")
            destaque = colors.get("destaque", "#3A86FF")
            sucesso = colors.get("sucesso", "#3BCF8E")
            alerta = colors.get("alerta", "#EF476F")
            borda = colors.get("borda", "#333333")
            hover = colors.get("hover", "#2C2C2C")
            selecao = colors.get("selecao", destaque)

            self.configure(fg_color=colors.get("fundo", "#181818"))
            self.preview_container.configure(fg_color=primaria, border_color=borda)
            self.title_label.configure(text_color=texto)
            self.sample_label.configure(text_color=texto)
            self.sample_button.configure(fg_color=secundaria, hover_color=hover,
                                         text_color=texto, border_color=borda)
            self.sample_entry.configure(fg_color=secundaria, text_color=texto, border_color=borda)
            self.tertiary_frame.configure(fg_color=terciaria, border_color=borda)
            self.tertiary_label.configure(text_color=texto)
            self.border_frame.configure(border_color=borda)
            self.border_label.configure(text_color=texto)

            self.success_btn.configure(fg_color=sucesso, hover_color=ajustar_hover(sucesso),
                                       text_color=get_contraste_texto(sucesso))
            self.alert_btn.configure(fg_color=alerta, hover_color=ajustar_hover(alerta),
                                     text_color=get_contraste_texto(alerta))
            self.highlight_btn.configure(fg_color=destaque, hover_color=ajustar_hover(destaque),
                                         text_color=get_contraste_texto(destaque))
            self.hover_demo_btn = self.sample_button
            self.selecao_demo_btn = self.highlight_btn

            for chave, btn in self.widgets_referencia.items():
                cor = colors.get(chave)
                if cor:
                    btn.configure(fg_color=cor, hover_color=ajustar_hover(cor),
                                  text_color=get_contraste_texto(cor))
        except Exception as e:
            if LOGGER:
                LOGGER.error(f"Erro no preview: {e}")

    def highlight_element(self, campo: str):
        self.clear_highlight()
        element_map = {
            "primaria": [self.preview_container],
            "secundaria": [self.sample_button, self.sample_entry],
            "terciaria": [self.tertiary_frame],
            "fundo": [self],
            "texto": [self.title_label, self.sample_label, self.tertiary_label, self.border_label],
            "destaque": [self.highlight_btn],
            "sucesso": [self.success_btn],
            "alerta": [self.alert_btn],
            "borda": [self.border_frame],
            "hover": [self.sample_button],
            "selecao": [self.highlight_btn],
        }
        for btn_campo, botao in self.widgets_referencia.items():
            element_map[btn_campo] = [botao]

        elements = element_map.get(campo)
        if not elements:
            return

        for elem in elements:
            try:
                if hasattr(elem, 'cget'):
                    self.original_border_widths[elem] = elem.cget('border_width')
                elem.configure(border_width=3, border_color="#FFD700")
            except:
                pass
        self.highlighted_element = elements

    def clear_highlight(self):
        if self.highlighted_element:
            for elem in self.highlighted_element:
                try:
                    bw = self.original_border_widths.get(elem, 1)
                    elem.configure(border_width=bw)
                except:
                    pass
            self.highlighted_element = None
            self.original_border_widths.clear()

class ColorPickerWidget(ctk.CTkFrame):
    def __init__(self, master, initial_color="#FFFFFF", callback: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.callback = callback
        self.current_color = initial_color
        self._advanced_picker_window: Optional[ctk.CTkToplevel] = None
        self._wheel_photo = None

        self.basic_colors = [
            ["#000000", "#333333", "#666666", "#999999", "#CCCCCC", "#FFFFFF"],
            ["#8B0000", "#FF0000", "#FF6347", "#FFA07A", "#FFC0CB"],
            ["#FF4500", "#FF8C00", "#FFA500", "#FFD700", "#FFFF00"],
            ["#006400", "#008000", "#228B22", "#32CD32", "#00FF00"],
            ["#00008B", "#0000FF", "#1E90FF", "#87CEEB", "#ADD8E6"],
            ["#4B0082", "#8A2BE2", "#9370DB", "#BA55D3", "#DA70D6"],
        ]
        self._build_ui()

    def _build_ui(self):
        preview_frame = ctk.CTkFrame(self, fg_color="transparent")
        preview_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(preview_frame, text="Cor Selecionada:", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        self.preview_btn = ctk.CTkButton(
            preview_frame, text=self.current_color, fg_color=self.current_color,
            hover_color=self.current_color, text_color=get_contraste_texto(self.current_color),
            font=("Arial", 10, "bold"), height=30, width=120,
            command=self._open_advanced_picker
        )
        self.preview_btn.pack(side="left", padx=5)

        ctk.CTkLabel(self, text="Paleta Rápida:", font=("Arial", 11, "bold")).pack(anchor="w", padx=5, pady=(10,5))

        canvas_height = len(self.basic_colors) * 28
        canvas_width = 11 * 28
        self.canvas = tk.Canvas(self, width=canvas_width, height=canvas_height,
                                bg="#1E1E1E", highlightthickness=0)
        self.canvas.pack(padx=5, pady=5)

        self.color_rects = {}
        for row_idx, color_row in enumerate(self.basic_colors):
            for col_idx, color in enumerate(color_row):
                x1 = col_idx * 28 + 2
                y1 = row_idx * 28 + 2
                x2 = x1 + 24
                y2 = y1 + 24
                rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#666666", width=1)
                self.color_rects[rect_id] = color
                self.canvas.tag_bind(rect_id, "<Button-1>", lambda e, c=color: self._select_color(c))
                self.canvas.tag_bind(rect_id, "<Enter>", lambda e, rid=rect_id: self.canvas.itemconfig(rid, outline="#FFFFFF", width=2))
                self.canvas.tag_bind(rect_id, "<Leave>", lambda e, rid=rect_id: self.canvas.itemconfig(rid, outline="#666666", width=1))

        ctk.CTkButton(self, text="🎨 Seletor Avançado", font=("Arial", 11), height=30,
                      command=self._open_advanced_picker).pack(pady=10, padx=5)

    def _select_color(self, color: str):
        self.current_color = color
        self.preview_btn.configure(fg_color=color, hover_color=color, text=color,
                                    text_color=get_contraste_texto(color))
        if self.callback:
            self.callback(color)

    def _open_advanced_picker(self):
        if self._advanced_picker_window and self._advanced_picker_window.winfo_exists():
            self._advanced_picker_window.focus()
            return

        def close_picker():
            if self._advanced_picker_window and self._advanced_picker_window.winfo_exists():
                self._advanced_picker_window.destroy()

        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            if len(hex_color) != 6 or not re.fullmatch(r"[0-9A-Fa-f]{6}", hex_color):
                return None
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        def rgb_to_hex(rgb_tuple):
            return "#{:02X}{:02X}{:02X}".format(*rgb_tuple)

        def hsv_to_hex(h, s, v):
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return rgb_to_hex((int(r*255), int(g*255), int(b*255)))

        def build_wheel_image(size, radius, oversample=2):
            base_size = int(size * oversample)
            base_radius = radius * oversample
            image = Image.new("RGBA", (base_size, base_size), (0,0,0,0))
            center = base_size / 2
            for x in range(base_size):
                for y in range(base_size):
                    dx = x - center + 0.5
                    dy = y - center + 0.5
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist <= base_radius:
                        hue = (math.atan2(-dy, dx) % (2*math.pi)) / (2*math.pi)
                        sat = min(1.0, dist / base_radius)
                        r, g, b = colorsys.hsv_to_rgb(hue, sat, 1.0)
                        image.putpixel((x, y), (int(r*255), int(g*255), int(b*255), 255))
            if oversample > 1:
                image = image.resize((size, size), resample=Image.LANCZOS)
            return image

        def grab_screen_hex(x, y):
            if not IMAGE_GRAB_AVAILABLE or ImageGrab is None:
                return None
            try:
                pixel = ImageGrab.grab(bbox=(x, y, x+1, y+1)).getpixel((0,0))
                return rgb_to_hex(pixel)
            except Exception as e:
                if LOGGER:
                    LOGGER.error(f"Erro ao capturar cor: {e}")
                return None

        def start_eyedropper():
            if not IMAGE_GRAB_AVAILABLE:
                messagebox.showwarning("Conta-gotas indisponível", "O recurso de captura de cor não está disponível.")
                return
            overlay = tk.Toplevel(self._advanced_picker_window)
            overlay.overrideredirect(True)
            overlay.attributes("-alpha", 0.02)
            overlay.attributes("-topmost", True)
            overlay.configure(cursor="crosshair", bg="black")
            overlay.geometry(f"{overlay.winfo_screenwidth()}x{overlay.winfo_screenheight()}+0+0")
            overlay.focus_force()

            lens_size = 120
            lens_padding = 16
            lens_canvas = tk.Canvas(overlay, width=lens_size + 2*lens_padding,
                                   height=lens_size + 36, bg="#121212", highlightthickness=0)
            lens_canvas.configure(cursor="circle")
            lens_photo = {"image": None}

            def finish(event=None):
                try:
                    if overlay.winfo_exists():
                        overlay.destroy()
                finally:
                    self._advanced_picker_window.deiconify()
                    self._advanced_picker_window.lift()
                    self._advanced_picker_window.focus_force()

            def update_lens(event):
                try:
                    grab_box = (event.x_root - 12, event.y_root - 12, event.x_root + 13, event.y_root + 13)
                    zoom = ImageGrab.grab(bbox=grab_box).resize((lens_size, lens_size), Image.LANCZOS)
                    lens_photo["image"] = ImageTk.PhotoImage(zoom)
                    lens_canvas.delete("all")
                    lens_canvas.create_rectangle(4, 4, lens_size + lens_padding*2 - 4,
                                                 lens_size + lens_padding + 8, outline="#3A3A3A",
                                                 width=2, fill="#1A1A1A")
                    lens_canvas.create_image(lens_padding, lens_padding, anchor="nw", image=lens_photo["image"])
                    center = lens_padding + lens_size/2
                    lens_canvas.create_line(center-8, lens_padding + lens_size/2,
                                            center+8, lens_padding + lens_size/2, fill="#FFFFFF", width=1)
                    lens_canvas.create_line(lens_padding + lens_size/2, center-8,
                                            lens_padding + lens_size/2, center+8, fill="#FFFFFF", width=1)
                    current_hex = grab_screen_hex(event.x_root, event.y_root) or "--"
                    lens_canvas.create_text(lens_padding, lens_size + lens_padding + 8, anchor="w",
                                            text=current_hex, fill="#E5E7EB", font=("Arial", 11, "bold"))
                    pos_x = max(10, min(event.x_root + 24, overlay.winfo_screenwidth() - lens_size - 2*lens_padding - 10))
                    pos_y = max(10, min(event.y_root + 24, overlay.winfo_screenheight() - lens_size - lens_padding - 40))
                    lens_canvas.place(x=pos_x, y=pos_y)
                except Exception as e:
                    if LOGGER:
                        LOGGER.error(f"Erro na lupa: {e}")

            def pick_color(event):
                color_hex = grab_screen_hex(event.x_root, event.y_root)
                if color_hex:
                    set_current_color(color_hex)
                finish()

            overlay.bind("<Motion>", update_lens)
            overlay.bind("<Button-1>", pick_color)
            overlay.bind("<Escape>", finish)

        initial_rgb = hex_to_rgb(self.current_color) or (255,255,255)
        h, s, v = colorsys.rgb_to_hsv(*(c/255 for c in initial_rgb))
        current_hsv = {"h": h, "s": s, "v": v}

        self._advanced_picker_window = ctk.CTkToplevel(self)
        self._advanced_picker_window.title("Seletor Avançado de Cores")
        self._advanced_picker_window.resizable(True, True)
        self._advanced_picker_window.minsize(390, 450)
        target_w, target_h = 410, 608
        self._advanced_picker_window.geometry(f"{target_w}x{target_h}")
        self._advanced_picker_window.transient(self.winfo_toplevel())
        self._advanced_picker_window.protocol("WM_DELETE_WINDOW", close_picker)
        self._advanced_picker_window.update_idletasks()
        screen_w = self._advanced_picker_window.winfo_screenwidth()
        screen_h = self._advanced_picker_window.winfo_screenheight()
        x = int((screen_w - target_w) / 2)
        y = int((screen_h - target_h) / 2)
        self._advanced_picker_window.geometry(f"{target_w}x{target_h}+{x}+{y}")

        wrapper = ctk.CTkFrame(self._advanced_picker_window, fg_color=self.cget("fg_color"))
        wrapper.pack(fill="both", expand=True, padx=16, pady=16)

        top_row = ctk.CTkFrame(wrapper, fg_color="transparent")
        top_row.pack(fill="x", pady=(0,6))

        preview_btn = ctk.CTkButton(
            top_row,
            text=self.current_color,
            fg_color=self.current_color,
            hover_color=self.current_color,
            text_color=get_contraste_texto(self.current_color),
            font=("Arial", 12, "bold"),
            height=32,
            width=90,
            corner_radius=10,
            command=lambda: None,
        )
        preview_btn.pack(side="left")

        hex_var = tk.StringVar(value=self.current_color)
        hex_entry = ctk.CTkEntry(top_row, textvariable=hex_var, width=110, font=("Arial", 12))
        hex_entry.pack(side="left", padx=(10,6))

        eyedropper = ctk.CTkButton(top_row, text="🧪", width=34, height=34,
                                   fg_color="#3A3A3A", hover_color="#4A4A4A",
                                   command=start_eyedropper)
        eyedropper.pack(side="left")

        toolbar = ctk.CTkFrame(wrapper, fg_color="transparent")
        toolbar.pack(fill="x", pady=(6,6))

        tab_buttons = {}
        tab_frames = {}

        tabs = [
            ("wheel", "⚪", "Roda"),
            ("grays", "⬛", "Web"),
            ("lists", "📃", "Listas"),
            ("pencils", "✏️", "Lápis"),
            ("palettes", "🖼", "Paletas"),
        ]

        tabs_bar = ctk.CTkFrame(toolbar, fg_color="transparent")
        tabs_bar.pack(side="left")

        content_area = ctk.CTkFrame(wrapper, fg_color="transparent")
        content_area.pack(fill="both", expand=True)

        brightness_slider = None
        wheel_canvas = None

        def set_current_color(color_hex, update_entry=True):
            rgb = hex_to_rgb(color_hex)
            if not rgb:
                return
            h_val, s_val, v_val = colorsys.rgb_to_hsv(*(c/255 for c in rgb))
            current_hsv.update({"h": h_val, "s": s_val, "v": v_val})
            preview_btn.configure(fg_color=color_hex, hover_color=color_hex, text=color_hex,
                                  text_color=get_contraste_texto(color_hex))
            if update_entry:
                hex_var.set(color_hex.upper())
            if brightness_slider is not None:
                brightness_slider.configure(progress_color=color_hex, button_color=color_hex,
                                            button_hover_color=color_hex)
                brightness_slider.set(v_val)
            if wheel_canvas is not None:
                update_marker()
            self.current_color = color_hex.upper()

        def update_from_hex(*_):
            set_current_color(hex_var.get())

        hex_entry.bind("<KeyRelease>", update_from_hex)

        bottom_area = ctk.CTkFrame(wrapper, fg_color="transparent")
        bottom_area.pack(fill="x", pady=(6,0))

        favorites_frame = ctk.CTkFrame(bottom_area, fg_color="#1F1F1F", corner_radius=8, border_width=1,
                                       border_color="#3A3A3A")
        favorites_frame.pack(fill="x", pady=(0,8))

        fav_label = ctk.CTkLabel(favorites_frame, text="Favoritos", anchor="w")
        fav_label.pack(fill="x", padx=8, pady=(6,2))

        fav_grid = ctk.CTkFrame(favorites_frame, fg_color="transparent")
        fav_grid.pack(fill="x", padx=6, pady=(0,6))
        recent_colors = ["#F1F2EC", "#E6E6E6", "#CCCCCC", "#B3B3B3", "#999999", "#808080",
                         "#666666", "#4D4D4D", "#333333", "#1A1A1A"]
        for color_hex in recent_colors:
            btn = ctk.CTkButton(fav_grid, text="", width=26, height=24, fg_color=color_hex,
                                hover_color=color_hex, corner_radius=4,
                                command=lambda c=color_hex: set_current_color(c))
            btn.pack(side="left", padx=3, pady=3)

        buttons_frame = ctk.CTkFrame(bottom_area, fg_color="transparent")
        buttons_frame.pack(fill="x")
        ctk.CTkButton(buttons_frame, text="Cancelar", fg_color="#6B7280", hover_color="#4B5563",
                      command=close_picker, width=120).pack(side="left", padx=(0,6))
        ctk.CTkButton(buttons_frame, text="OK", fg_color="#3B82F6", hover_color="#2563EB",
                      command=lambda: (self._select_color(self.current_color), close_picker()), width=120).pack(side="right")

        def register_tab(key, widget):
            tab_frames[key] = widget
            widget.pack_forget()

        def show_tab(key):
            for k, frame in tab_frames.items():
                frame.pack_forget()
            tab_frames[key].pack(fill="both", expand=True)
            for k, btn in tab_buttons.items():
                btn.configure(fg_color="#3B82F6" if k == key else "#2A2A2A",
                               hover_color="#353535" if k == key else "#3A3A3A")

        for key, icon, _tooltip in tabs:
            btn = ctk.CTkButton(
                tabs_bar,
                text=icon,
                width=40,
                height=34,
                corner_radius=8,
                fg_color="#2A2A2A",
                hover_color="#3A3A3A",
                command=lambda k=key: show_tab(k),
            )
            btn.pack(side="left", padx=4)
            tab_buttons[key] = btn

        wheel_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("wheel", wheel_tab)

        wheel_size = 260
        wheel_radius = wheel_size/2 - 6
        wheel_center = wheel_size/2

        wheel_image = build_wheel_image(wheel_size, wheel_radius, oversample=4)
        self._wheel_photo = ImageTk.PhotoImage(wheel_image)

        wheel_canvas = tk.Canvas(wheel_tab, width=wheel_size, height=wheel_size, bg="#1F1F1F",
                                 highlightthickness=0)
        wheel_canvas.pack(pady=(6,12))
        wheel_canvas.create_image(0,0, image=self._wheel_photo, anchor="nw")

        def update_marker():
            wheel_canvas.delete("marker")
            cx = wheel_center + (wheel_radius * current_hsv["s"] * math.cos(current_hsv["h"] * 2 * math.pi))
            cy = wheel_center - (wheel_radius * current_hsv["s"] * math.sin(current_hsv["h"] * 2 * math.pi))
            wheel_canvas.create_oval(cx-7, cy-7, cx+7, cy+7, outline="#000000", width=2, tags="marker")
            wheel_canvas.create_oval(cx-5, cy-5, cx+5, cy+5, outline="#FFFFFF", width=2, tags="marker")

        def update_from_hsv():
            color_hex = hsv_to_hex(current_hsv["h"], current_hsv["s"], current_hsv["v"])
            set_current_color(color_hex)

        def on_wheel_click(event):
            dx = event.x - wheel_center
            dy = event.y - wheel_center
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > wheel_radius:
                return
            hue = (math.atan2(-dy, dx) % (2*math.pi)) / (2*math.pi)
            sat = min(1.0, dist / wheel_radius)
            current_hsv["h"] = hue
            current_hsv["s"] = sat
            update_from_hsv()

        wheel_canvas.bind("<Button-1>", on_wheel_click)
        wheel_canvas.bind("<B1-Motion>", on_wheel_click)

        slider_frame = ctk.CTkFrame(wheel_tab, fg_color="transparent")
        slider_frame.pack(fill="x", pady=(0,10), padx=4)
        ctk.CTkLabel(slider_frame, text="Brilho:").pack(side="left")
        brightness_slider = ctk.CTkSlider(slider_frame, from_=0, to=1, number_of_steps=100,
                                          command=lambda val: (current_hsv.__setitem__('v', float(val)), update_from_hsv()))
        brightness_slider.pack(side="left", fill="x", expand=True, padx=10)
        brightness_slider.set(v)

        quick_palette = ctk.CTkFrame(wheel_tab, fg_color="transparent")
        quick_palette.pack(pady=(0,8))
        palette_colors = [c for row in self.basic_colors for c in row][:24]
        quick_palette_cols = 12
        for idx, color in enumerate(palette_colors):
            btn = ctk.CTkButton(quick_palette, width=24, height=22, text="", fg_color=color,
                                hover_color=color, corner_radius=4,
                                command=lambda c=color: set_current_color(c))
            row = idx // quick_palette_cols
            col = idx % quick_palette_cols
            btn.grid(row=row, column=col, padx=3, pady=3)

        grays_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("grays", grays_tab)

        grayscale_colors = ["#FFFFFF", "#F2F2F2", "#E5E5E5", "#CCCCCC", "#B3B3B3", "#999999", "#808080",
                             "#666666", "#4D4D4D", "#333333", "#1A1A1A", "#000000"]
        gray_frame = ctk.CTkFrame(grays_tab, fg_color="#151515", corner_radius=8, border_width=1,
                                  border_color="#303030")
        gray_frame.pack(fill="both", expand=True, pady=6)

        search_gray = ctk.CTkEntry(gray_frame, placeholder_text="Buscar", height=32)
        search_gray.pack(fill="x", padx=10, pady=(10,6))

        list_holder = ctk.CTkScrollableFrame(gray_frame, fg_color="#151515")
        list_holder.pack(fill="both", expand=True, padx=6, pady=(0,10))

        def render_gray_list(filter_text=""):
            for child in list_holder.winfo_children():
                child.destroy()
            for color_hex in grayscale_colors:
                if filter_text and filter_text.lower() not in color_hex.lower():
                    continue
                row = ctk.CTkFrame(list_holder, fg_color="transparent")
                row.pack(fill="x", pady=3, padx=4)
                swatch = ctk.CTkButton(row, text="", width=32, height=28, fg_color=color_hex,
                                        hover_color=color_hex, corner_radius=6,
                                        command=lambda c=color_hex: set_current_color(c))
                swatch.pack(side="left", padx=(0,10))
                ctk.CTkLabel(row, text=color_hex, font=("Arial", 12)).pack(side="left")

        search_gray.bind("<KeyRelease>", lambda e: render_gray_list(search_gray.get()))
        render_gray_list()

        lists_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("lists", lists_tab)

        list_top = ctk.CTkFrame(lists_tab, fg_color="transparent")
        list_top.pack(fill="x", pady=(6,6))

        palettes_named = {
            "Web": [
                ("Lima", "#BFFF00"), ("Turquesa", "#30D5C8"), ("Aqua", "#00FFFF"), ("Violeta", "#8F00FF"),
                ("Orquídea", "#DA70D6"), ("Céu", "#00BFFF"), ("Espuma", "#AFE1AF"), ("Prata", "#C0C0C0"),
            ],
            "Desenvolvedor": [
                ("controlAccentColor", "#0A84FF"), ("systemBlue", "#0A84FF"), ("findHighlight", "#FFD60A"),
                ("windowBackgroundColor", "#1E1E1E"), ("labelColor", "#FFFFFF"), ("separatorColor", "#2C2C2E"),
            ],
            "Apple": [
                ("Azul", "#0A84FF"), ("Marrom", "#AC8E68"), ("Ciano", "#32ADE6"), ("Verde", "#30D158"),
                ("Magenta", "#FF2D55"), ("Laranja", "#FF9500"), ("Amarelo", "#FFD60A"), ("Roxo", "#BF5AF2"),
                ("Vermelho", "#FF3B30"), ("Branco", "#FFFFFF"),
            ],
        }

        palette_selector = ctk.CTkComboBox(list_top, values=list(palettes_named.keys()), state="readonly", width=150)
        palette_selector.set("Web")
        palette_selector.pack(side="left", padx=(0,8))

        search_list = ctk.CTkEntry(list_top, placeholder_text="Buscar", width=160)
        search_list.pack(side="left")

        list_area = ctk.CTkScrollableFrame(lists_tab, fg_color="#151515")
        list_area.pack(fill="both", expand=True, padx=4, pady=(0,8))

        def render_named():
            for child in list_area.winfo_children():
                child.destroy()
            palette = palette_selector.get()
            search_text = search_list.get().lower()
            for name, color_hex in palettes_named.get(palette, []):
                if search_text and search_text not in name.lower() and search_text not in color_hex.lower():
                    continue
                row = ctk.CTkFrame(list_area, fg_color="transparent")
                row.pack(fill="x", pady=4, padx=6)
                swatch = ctk.CTkButton(row, text="", width=32, height=28, fg_color=color_hex,
                                        hover_color=color_hex, corner_radius=6,
                                        command=lambda c=color_hex: set_current_color(c))
                swatch.pack(side="left", padx=(0,10))
                ctk.CTkLabel(row, text=name, font=("Arial", 12)).pack(side="left")
                ctk.CTkLabel(row, text=color_hex, font=("Arial", 11), text_color="#9CA3AF").pack(side="right")

        palette_selector.configure(command=lambda _: render_named())
        search_list.bind("<KeyRelease>", lambda e: render_named())
        render_named()

        pencils_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("pencils", pencils_tab)

        pencil_sets = {
            "Prata": ["#F7F7F7", "#E2E2E2", "#C5C5C5", "#AAAAAA", "#919191", "#777777", "#5E5E5E"],
            "Clássico": ["#FF3B30", "#FF9500", "#FFD60A", "#34C759", "#0A84FF", "#5856D6", "#AF52DE"],
            "Neon": ["#FF2D55", "#FF6B81", "#FF9500", "#FFD60A", "#64D2FF", "#30DB5B", "#AC8E68"],
        }

        combo_pencil = ctk.CTkComboBox(pencils_tab, values=list(pencil_sets.keys()), state="readonly", width=150)
        combo_pencil.set("Prata")
        combo_pencil.pack(pady=(8,4))

        pencils_canvas = tk.Canvas(pencils_tab, width=330, height=170, bg="#151515", highlightthickness=0)
        pencils_canvas.pack(pady=(0,8))

        def draw_pencils():
            pencils_canvas.delete("all")
            colors = pencil_sets.get(combo_pencil.get(), [])
            cols = 7
            rows = 4
            spacing_x = 48
            spacing_y = 42
            start_x = 16
            start_y = 10
            idx = 0
            for r in range(rows):
                for c in range(cols):
                    if idx >= len(colors):
                        break
                    x = start_x + c * spacing_x
                    y = start_y + r * spacing_y
                    color_hex = colors[idx % len(colors)]
                    pencils_canvas.create_polygon(
                        x, y+10, x+18, y, x+36, y+10, x+36, y+44, x, y+44,
                        fill=color_hex, outline="#2E2E2E", width=1, tags=("pencil", color_hex)
                    )
                    pencils_canvas.create_polygon(
                        x+12, y-4, x+18, y+10, x+24, y-4,
                        fill="#D8D2C4", outline="#2E2E2E", width=1, tags=("pencil", color_hex)
                    )
                    pencils_canvas.create_rectangle(
                        x+4, y+10, x+32, y+40, fill=color_hex, outline="", tags=("pencil", color_hex)
                    )
                    idx += 1

        def on_pencil_click(event):
            items = pencils_canvas.find_withtag("current")
            if not items:
                return
            tags = pencils_canvas.gettags(items[0])
            for t in tags:
                if t.startswith("#"):
                    set_current_color(t)
                    break

        pencils_canvas.bind("<Button-1>", on_pencil_click)
        combo_pencil.configure(command=lambda _: draw_pencils())
        draw_pencils()

        palette_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("palettes", palette_tab)

        palettes_grid = [c for row in self.basic_colors for c in row]
        grid_frame = ctk.CTkScrollableFrame(palette_tab, fg_color="#151515")
        grid_frame.pack(fill="both", expand=True, padx=4, pady=6)

        def render_grid():
            for child in grid_frame.winfo_children():
                child.destroy()
            cols = 12
            for idx, color_hex in enumerate(palettes_grid):
                btn = ctk.CTkButton(grid_frame, text="", width=32, height=28, fg_color=color_hex,
                                    hover_color=color_hex, corner_radius=6,
                                    command=lambda c=color_hex: set_current_color(c))
                row = idx // cols
                col = idx % cols
                btn.grid(row=row, column=col, padx=4, pady=4)

        render_grid()

        set_current_color(self.current_color)
        show_tab("wheel")

    def set_color(self, color: str):
        self._select_color(color)

    def get_color(self) -> str:
        return self.current_color


def aplicar_tema_atalho(app, nome_tema: str) -> bool:
    """
    Atalho de aplicação de tema reutilizando a mesma base da página Temas.
    """
    try:
        paletas = ModuloPaletas()
        tema = paletas.obter_tema(nome_tema)
        if not tema:
            return False

        theme_manager = getattr(app, "theme_manager", None)
        modo_anterior = getattr(app, "tema_modo", None)
        modo_novo = "dark" if is_dark_color(tema.get("fundo", "#111111")) else "light"
        rebuild_interface = (modo_anterior is not None and modo_anterior != modo_novo)

        if theme_manager:
            theme_manager.apply_theme(nome_tema, tema, rebuild_interface=rebuild_interface)
        else:
            for campo, valor in tema.items():
                setattr(app, f"cor_{campo}", valor)

        for attr in ("tema_atual", "current_theme_name", "tema_preferido_inicial"):
            if hasattr(app, attr):
                setattr(app, attr, nome_tema)
        if hasattr(app, "tema_modo"):
            app.tema_modo = modo_novo

        user_manager = getattr(app, "user_manager", None)
        if user_manager and hasattr(user_manager, "save_user_theme"):
            user_manager.save_user_theme(nome_tema)

        try:
            if hasattr(app, "_update_menu_buttons_colors"):
                app._update_menu_buttons_colors()
            if hasattr(app, "update_idletasks"):
                app.update_idletasks()
            if rebuild_interface and hasattr(app, "reload_current_page"):
                app.after(120, app.reload_current_page)
        except Exception:
            pass

        return True
    except Exception as e:
        if LOGGER:
            LOGGER.error(f"Erro ao aplicar tema via atalho ('{nome_tema}'): {e}")
        return False


class TemasPage(ctk.CTkFrame):
    MAX_COLS = 3

    def __init__(self, master=None, *args, **kwargs):
        self.app = self._get_app_reference(kwargs)
        super().__init__(master, *args, **kwargs)
        self._opera_preservar_tema = True

        self.paletas = ModuloPaletas()
        self.vars: Dict[str, tk.StringVar] = {}
        self.campo_selecionado: Optional[str] = None
        self.tema_atual: str = "CLÁSSICO CLARO"
        self._jobs: List[str] = []
        self._widget_cache: Dict[str, Any] = {}

        self._configure_self()
        self._load_initial_data()
        self._build_interface()

        if hasattr(self.app, '_agendar_after'):
            self.app._agendar_after(100, self._finalize_loading)

    def _get_app_reference(self, kwargs) -> Any:
        for key in ["sistema", "app", "controller", "root", "master"]:
            if key in kwargs:
                return kwargs.pop(key)
        root = self
        while hasattr(root, 'master') and root.master:
            root = root.master
            if hasattr(root, 'theme_manager'):
                return root
        return self.winfo_toplevel()

    def _configure_self(self):
        self.configure(fg_color=getattr(self.app, "cor_fundo", "#1e1e1e"))

    def _load_initial_data(self):
        if hasattr(self.app, 'usuario_id') and self.app.usuario_id:
            self.after(50, self._load_custom_themes_from_db)

        self.tema_atual = self._get_current_theme_name()

    # ===== FUNÇÃO CORRIGIDA =====
    def _get_current_theme_name(self) -> str:
        """
        Obtém o nome do tema atualmente aplicado de forma segura,
        verificando se os atributos existem antes de acessá-los.
        """
        # 1. Tenta obter do theme_manager (prioridade máxima)
        try:
            theme_manager = getattr(self.app, 'theme_manager', None)
            if theme_manager is not None:
                if hasattr(theme_manager, 'current_theme_name'):
                    theme_name = theme_manager.current_theme_name
                    if theme_name:
                        return theme_name
        except Exception:
            pass

        # 2. Tenta obter do atributo current_theme_name do app
        try:
            current_theme = getattr(self.app, 'current_theme_name', None)
            if current_theme:
                return current_theme
        except Exception:
            pass

        # 3. Tenta obter do tema_preferido_inicial
        try:
            preferido = getattr(self.app, 'tema_preferido_inicial', None)
            if preferido:
                return preferido
        except Exception:
            pass

        # 4. Fallback para o tema padrão
        return "CLÁSSICO CLARO"

    def _load_custom_themes_from_db(self):
        try:
            from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema
            usuario_id = self.app.usuario_id
            if not usuario_id:
                return

            conn = get_conn()
            if not conn:
                return

            schema = get_schema()
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT nome_tema, cores_tema FROM {schema}.usuario_temas_personalizados WHERE usuario_id = %s",
                    (usuario_id,)
                )
                rows = cur.fetchall()

            for nome, cores_json in rows:
                try:
                    if isinstance(cores_json, dict):
                        paleta = cores_json
                    else:
                        paleta = json.loads(cores_json)
                    if isinstance(paleta, dict):
                        self.paletas.salvar_tema_personalizado(nome, paleta)
                except Exception as e:
                    if LOGGER:
                        LOGGER.error(f"Erro ao carregar tema '{nome}': {e}")

            self._refresh_theme_list()

        except Exception as e:
            if LOGGER:
                LOGGER.error(f"Falha ao carregar temas do banco: {e}")

    def _build_interface(self):
        self._build_header()

        main_layout = ctk.CTkFrame(self, fg_color="transparent")
        main_layout.pack(fill="both", expand=True, padx=5, pady=5)

        self.left_panel = ctk.CTkFrame(main_layout, fg_color="transparent")
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._build_left_panel(self.left_panel)

        center_panel = ctk.CTkFrame(main_layout, fg_color=self.app.cor_secundaria,
                                    corner_radius=10, border_width=2, border_color=self.app.cor_borda)
        center_panel.pack(side="left", fill="both", padx=(0, 5))
        center_panel.configure(width=260)
        self.preview_panel = PreviewPanel(center_panel, fg_color="transparent")
        self.preview_panel.pack(fill="both", expand=True, padx=10, pady=10)

        self.right_panel = ctk.CTkFrame(main_layout, fg_color=self.app.cor_secundaria,
                                        corner_radius=10, border_width=2, border_color=self.app.cor_borda)
        self.right_panel.pack(side="left", fill="both", padx=(5, 0))
        self.right_panel.configure(width=360)
        self._build_right_panel(self.right_panel)

        self._carregar_tema_no_editor(self.tema_atual)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=self.app.cor_secundaria,
                              corner_radius=12, border_width=1, border_color=self.app.cor_borda)
        header.pack(fill="x", padx=5, pady=(0, 8))

        info_frame = ctk.CTkFrame(header, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        ctk.CTkLabel(info_frame, text="Estúdio de Temas", font=("Arial", 20, "bold"),
                     text_color=self.app.cor_texto).pack(anchor="w")
        ctk.CTkLabel(info_frame, text=f"Tema atual: {self.tema_atual}", font=("Arial", 13),
                     text_color=self.app.cor_destaque).pack(anchor="w", pady=(4,0))

        action_frame = ctk.CTkFrame(header, fg_color="transparent")
        action_frame.pack(side="right", padx=12, pady=10)

        BotaoPadronizado.criar_botao(
            action_frame,
            text="Aplicar tema atual",
            tipo="confirmar",
            command=lambda: self._aplicar_tema_completo(self.tema_atual),
            height=36,
            corner_radius=10,
            font=("Arial", 12, "bold"),
        ).pack(side="left", padx=4)

        BotaoPadronizado.criar_botao(
            action_frame,
            text="Novo tema",
            tipo="novo",
            command=self._abrir_criador_tema,
            height=36,
            corner_radius=10,
            font=("Arial", 12, "bold"),
        ).pack(side="left", padx=4)

    def _build_left_panel(self, parent):
        scroll_container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True)

        title_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(title_frame, text="Gerenciar Temas", font=("Arial", 20, "bold"),
                     text_color=self.app.cor_texto).pack(side="left")

        ctk.CTkLabel(title_frame, text=f"Atual: {self.tema_atual}", font=("Arial", 14),
                     text_color=self.app.cor_destaque).pack(side="right")

        BotaoPadronizado.criar_botao(
            title_frame,
            text="+ Novo do Atual",
            tipo="novo",
            command=self._abrir_criador_tema,
            width=120,
            height=28,
        ).pack(side="right", padx=(10, 0))

        self._criar_bloco_temas(
            scroll_container,
            "Temas Padrão",
            list(self.paletas.PADROES.keys()),
            mostrar_botao_base=True
        )

        self._criar_bloco_temas(
            scroll_container,
            "Temas Personalizados",
            list(self.paletas.custom.keys()),
            mostrar_botoes_acao=True,
            is_personalizado=True
        )

    def _criar_bloco_temas(self, parent, titulo, temas, mostrar_botao_base=False,
                           mostrar_botoes_acao=False, is_personalizado=False):
        if not temas and is_personalizado:
            return

        bloc = ctk.CTkFrame(parent, fg_color=self.app.cor_secundaria, corner_radius=10)
        bloc.pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(bloc, text=titulo, font=("Arial", 14, "bold"),
                     text_color=self.app.cor_texto).pack(anchor="w", padx=10, pady=(10, 6))

        themes_container = ctk.CTkFrame(bloc, fg_color="transparent")
        themes_container.pack(fill="x", padx=10, pady=(0, 10))

        col_frames = []
        for i in range(3):
            col_frame = ctk.CTkFrame(themes_container, fg_color="transparent")
            col_frame.pack(side="left", fill="both", expand=True, padx=(0 if i==0 else 5, 5 if i==2 else 0))
            col_frames.append(col_frame)

        items_per_col = (len(temas) + 2) // 3

        for col_idx, col_frame in enumerate(col_frames):
            start_idx = col_idx * items_per_col
            end_idx = min(start_idx + items_per_col, len(temas))
            col_themes = temas[start_idx:end_idx]

            for nome in col_themes:
                self._criar_linha_tema(col_frame, nome, mostrar_botao_base,
                                       mostrar_botoes_acao, is_personalizado)

        if not is_personalizado:
            BotaoPadronizado.criar_botao(
                bloc,
                text="⏱ Restaurar Temas Padrão",
                tipo="exportar",
                command=self._restaurar_temas_padrao,
                height=35,
                font=("Arial", 12, "bold"),
            ).pack(fill="x", padx=10, pady=(0, 10))

    def _criar_linha_tema(self, parent, nome, mostrar_botao_base=False,
                          mostrar_botoes_acao=False, is_personalizado=False):
        is_active = (nome == self.tema_atual)
        fg_color = self.app.cor_destaque if is_active else self.app.cor_terciaria
        text_color = get_contraste_texto(fg_color) if is_active else self.app.cor_texto

        linha_frame = ctk.CTkFrame(parent, fg_color="transparent")
        linha_frame.pack(fill="x", pady=2)

        chip = _Chip(
            linha_frame,
            text=nome,
            command=lambda n=nome: self._aplicar_e_carregar_tema(n),
            is_active=is_active,
            fg_color=fg_color,
            hover_color=self.app.cor_hover,
            text_color=text_color,
        )
        chip.pack(side="left", fill="x", expand=True, padx=(0, 5))

        if mostrar_botao_base:
            BotaoPadronizado.criar_botao(
                linha_frame,
                text="📋",
                tipo="editar",
                command=lambda n=nome: self._carregar_tema_para_edicao(n),
                width=35,
                height=30,
                font=("Arial", 14),
            ).pack(side="right")

        if mostrar_botoes_acao:
            btn_frame = ctk.CTkFrame(linha_frame, fg_color="transparent")
            btn_frame.pack(side="right")

            BotaoPadronizado.criar_botao(
                btn_frame,
                text="📋",
                tipo="editar",
                command=lambda n=nome: self._duplicar_tema_personalizado(n),
                width=30,
                height=28,
                font=("Arial", 12),
            ).pack(side="left", padx=1)

            BotaoPadronizado.criar_botao(
                btn_frame,
                text="✏️",
                tipo="editar",
                command=lambda n=nome: self._editar_tema_personalizado(n),
                width=30,
                height=28,
                font=("Arial", 12),
            ).pack(side="left", padx=1)

            BotaoPadronizado.criar_botao(
                btn_frame,
                text="🗑️",
                tipo="excluir",
                command=lambda n=nome: self._excluir_tema_personalizado(n),
                width=30,
                height=28,
                font=("Arial", 12),
            ).pack(side="left", padx=1)

    def _build_right_panel(self, parent):
        right_scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        right_scroll.pack(fill="both", expand=True, padx=10, pady=(10, 10))

        ctk.CTkLabel(right_scroll, text="Editor de Tema", font=("Arial", 16, "bold"),
                     text_color=self.app.cor_texto).pack(pady=(5, 10), padx=10)

        scroll_editor = ctk.CTkScrollableFrame(right_scroll, fg_color="transparent", height=300)
        scroll_editor.pack(fill="both", expand=True, padx=0, pady=(0, 10))

        self._criar_campos_edicao(scroll_editor)

        separator = ctk.CTkFrame(right_scroll, fg_color=self.app.cor_borda, height=2)
        separator.pack(fill="x", pady=8)

        ctk.CTkLabel(right_scroll, text="Seletor de Cores", font=("Arial", 13, "bold"),
                     text_color=self.app.cor_texto).pack(pady=(5, 5))

        self.color_picker = ColorPickerWidget(right_scroll, fg_color=self.app.cor_fundo, corner_radius=6,
                                              callback=self._on_color_selected)
        self.color_picker.pack(fill="x", pady=(0, 10))

        self._criar_campo_nome(right_scroll)

        self._criar_botoes_acao(right_scroll)

    def _criar_campos_edicao(self, parent):
        for campo in CAMPOS_PADRAO:
            campo_frame = ctk.CTkFrame(parent, fg_color=self.app.cor_terciaria,
                                       corner_radius=6, border_width=1,
                                       border_color=self.app.cor_borda)
            campo_frame.pack(fill="x", pady=5)

            label = ctk.CTkLabel(campo_frame, text=LABELS_CAMPOS_PADRAO[campo],
                                 font=("Arial", 11, "bold"), text_color=self.app.cor_texto, anchor="w")
            label.pack(fill="x", padx=10, pady=(8, 4))

            controls_frame = ctk.CTkFrame(campo_frame, fg_color="transparent")
            controls_frame.pack(fill="x", padx=10, pady=(0, 8))

            var = tk.StringVar(value="#FFFFFF")
            self.vars[campo] = var
            var.trace_add("write", lambda *args: self._update_live_preview())

            entry = ctk.CTkEntry(controls_frame, textvariable=var, font=("Arial", 11), height=32)
            entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

            self._criar_botao_cor(controls_frame, campo, var)

            self._configurar_bind_highlight(campo_frame, label, entry, campo)

    def _criar_botao_cor(self, parent, campo, var):
        def criar_btn():
            return BotaoPadronizado.criar_botao(
                parent,
                text="🎨",
                tipo="editar",
                command=lambda: self._abrir_seletor_cor(campo),
                width=100,
                height=32,
                corner_radius=6,
                font=("Arial", 14),
            )

        color_btn = criar_btn()
        color_btn.pack(side="left")

        def update_btn(*args, btn=color_btn):
            color = var.get()
            if not _valida_hex(color):
                return
            try:
                if hasattr(btn, "winfo_exists") and btn.winfo_exists():
                    btn.configure(
                        fg_color=color,
                        hover_color=color,
                        text_color=get_contraste_texto(color),
                    )
            except (tk.TclError, Exception):
                pass

        var.trace_add("write", update_btn)

        color_btn.bind("<Enter>", lambda e, c=campo: self._safe_preview_highlight(c))
        color_btn.bind("<Leave>", lambda e: self._safe_preview_leave())

    def _configurar_bind_highlight(self, frame, label, entry, campo):
        def on_enter(event):
            self.preview_panel.highlight_element(campo)

        def on_leave(event):
            self.preview_panel.clear_highlight()
            self._update_live_preview()

        for widget in [frame, label, entry]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def _criar_campo_nome(self, parent):
        nome_frame = ctk.CTkFrame(parent, fg_color="transparent")
        nome_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(nome_frame, text="Nome do Tema:", font=("Arial", 11, "bold"),
                     text_color=self.app.cor_texto).pack(anchor="w")

        self.var_nome = tk.StringVar(value="")
        ctk.CTkEntry(nome_frame, textvariable=self.var_nome, font=("Arial", 11),
                     height=32).pack(fill="x", pady=(4, 0))

    def _criar_botoes_acao(self, parent):
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 15))

        BotaoPadronizado.criar_botao(
            btn_frame,
            text="💾 Salvar Tema",
            tipo="salvar",
            command=self._salvar_custom_completo,
            height=38,
            font=("Arial", 12, "bold"),
        ).pack(fill="x", pady=3)

        BotaoPadronizado.criar_botao(
            btn_frame,
            text="🔄 Restaurar Original",
            tipo="excluir",
            command=self._restaurar_tema,
            height=38,
            font=("Arial", 12, "bold"),
        ).pack(fill="x", pady=3)

    def _hls_para_hex(self, hue: float, light: float, sat: float) -> str:
        r, g, b = colorsys.hls_to_rgb(hue % 1.0, max(0.0, min(1.0, light)), max(0.0, min(1.0, sat)))
        return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"

    def _gerar_pre_combinacao_tema(self) -> Dict[str, str]:
        base_atual = self.paletas.obter_tema(self.tema_atual) or self.paletas.PADROES.get("CLÃSSICO CLARO", {})
        fundo_atual = base_atual.get("fundo", "#FFFFFF")
        modo_escuro = is_dark_color(fundo_atual)
        hue = random.random()
        hue_sec = (hue + 0.08) % 1.0
        hue_alt = (hue + 0.48) % 1.0

        if modo_escuro:
            pal = {
                "primaria": self._hls_para_hex(hue, 0.16, 0.28),
                "secundaria": self._hls_para_hex(hue, 0.21, 0.24),
                "terciaria": self._hls_para_hex(hue, 0.31, 0.22),
                "fundo": self._hls_para_hex(hue, 0.11, 0.18),
                "texto": "#F8FAFC",
                "destaque": self._hls_para_hex(hue_sec, 0.55, 0.72),
                "sucesso": "#22C55E",
                "alerta": "#F43F5E",
                "borda": self._hls_para_hex(hue, 0.34, 0.18),
                "hover": self._hls_para_hex(hue, 0.26, 0.22),
                "selecao": self._hls_para_hex(hue_sec, 0.50, 0.74),
            }
        else:
            pal = {
                "primaria": self._hls_para_hex(hue, 0.96, 0.30),
                "secundaria": self._hls_para_hex(hue, 0.90, 0.24),
                "terciaria": self._hls_para_hex(hue, 0.80, 0.20),
                "fundo": "#FFFFFF",
                "texto": "#111827",
                "destaque": self._hls_para_hex(hue_sec, 0.46, 0.74),
                "sucesso": "#15803D",
                "alerta": "#DC2626",
                "borda": self._hls_para_hex(hue, 0.74, 0.20),
                "hover": self._hls_para_hex(hue, 0.86, 0.24),
                "selecao": self._hls_para_hex(hue_sec, 0.50, 0.70),
            }

        pal.update({
            "botao_salvar": pal["sucesso"],
            "botao_excluir": pal["alerta"],
            "botao_novo": pal["destaque"],
            "botao_imprimir": self._hls_para_hex((hue + 0.72) % 1.0, 0.50 if modo_escuro else 0.55, 0.70),
            "botao_pdf": "#D97706" if not modo_escuro else "#F59E0B",
            "botao_editar": self._hls_para_hex(hue_alt, 0.45 if not modo_escuro else 0.58, 0.68),
            "botao_visualizar": pal["destaque"],
            "botao_confirmar": pal["sucesso"],
            "botao_cancelar": "#6B7280",
            "botao_exportar": self._hls_para_hex((hue + 0.72) % 1.0, 0.50 if modo_escuro else 0.55, 0.70),
            "botao_importar": self._hls_para_hex(hue_alt, 0.45 if not modo_escuro else 0.58, 0.68),
            "botao_configurar": "#6B7280",
            "botao_ajuda": pal["destaque"],
            "botao_filtrar": pal["selecao"],
            "botao_limpar": "#B45309" if not modo_escuro else "#F59E0B",
            "botao_voltar": "#6B7280",
            "botao_avancar": pal["destaque"],
            "botao_adiantamento": pal["sucesso"],
            "botao_comprovante": self._hls_para_hex((hue + 0.72) % 1.0, 0.50 if modo_escuro else 0.55, 0.70),
            "botao_buscar": pal["destaque"],
            "botao_export_csv": "#0E7490" if not modo_escuro else "#06B6D4",
            "botao_export_pdf": "#D97706" if not modo_escuro else "#F59E0B",
        })
        return {campo: pal.get(campo, "#FFFFFF").upper() for campo in CAMPOS_PADRAO}

    def _abrir_criador_tema(self):
        try:
            if hasattr(self, "_creator_window") and self._creator_window and self._creator_window.winfo_exists():
                self._creator_window.lift()
                self._creator_window.focus_force()
                return
        except Exception:
            pass

        janela = ctk.CTkToplevel(self)
        self._creator_window = janela
        janela.title("Criar Tema Personalizado")
        janela.geometry("1180x720")
        janela.minsize(980, 620)
        try:
            janela.transient(self.winfo_toplevel())
            janela.focus_force()
        except Exception:
            pass

        vars_criador: Dict[str, tk.StringVar] = {}
        selected = {"campo": None}

        def paleta_atual() -> Dict[str, str]:
            return {campo: (var.get() or "#FFFFFF").upper() for campo, var in vars_criador.items()}

        root = ctk.CTkFrame(janela, fg_color=getattr(self.app, "cor_fundo", "#FFFFFF"))
        root.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkFrame(
            root,
            fg_color=getattr(self.app, "cor_secundaria", "#F4F4F5"),
            corner_radius=10,
            border_width=1,
            border_color=getattr(self.app, "cor_borda", "#9CA3AF"),
        )
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            header,
            text="Novo tema personalizado",
            font=("Arial", 20, "bold"),
            text_color=getattr(self.app, "cor_texto", "#111827"),
        ).pack(side="left", padx=12, pady=10)
        ctk.CTkLabel(
            header,
            text="Ajuste as partes do sistema e salve com o nome que quiser.",
            font=("Arial", 12),
            text_color=getattr(self.app, "cor_texto", "#111827"),
        ).pack(side="left", padx=12, pady=10)

        body = ctk.CTkFrame(root, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        campos_panel = ctk.CTkFrame(
            body,
            fg_color=getattr(self.app, "cor_secundaria", "#F4F4F5"),
            corner_radius=10,
            border_width=1,
            border_color=getattr(self.app, "cor_borda", "#9CA3AF"),
        )
        campos_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(
            campos_panel,
            text="Partes do sistema",
            font=("Arial", 15, "bold"),
            text_color=getattr(self.app, "cor_texto", "#111827"),
        ).pack(anchor="w", padx=12, pady=(10, 4))

        scroll = ctk.CTkScrollableFrame(campos_panel, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        scroll.grid_columnconfigure(0, weight=1)
        scroll.grid_columnconfigure(1, weight=1)

        preview_side = ctk.CTkFrame(
            body,
            fg_color=getattr(self.app, "cor_secundaria", "#F4F4F5"),
            corner_radius=10,
            border_width=1,
            border_color=getattr(self.app, "cor_borda", "#9CA3AF"),
        )
        preview_side.grid(row=0, column=1, sticky="nsew")

        preview = PreviewPanel(preview_side, fg_color="transparent")
        preview.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        def on_picker_color(color):
            campo = selected.get("campo")
            if campo and campo in vars_criador:
                vars_criador[campo].set(color.upper())

        picker = ColorPickerWidget(
            preview_side,
            fg_color=getattr(self.app, "cor_fundo", "#FFFFFF"),
            corner_radius=8,
            callback=on_picker_color,
        )
        picker.pack(fill="x", padx=10, pady=(0, 10))

        bottom = ctk.CTkFrame(root, fg_color="transparent")
        bottom.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(
            bottom,
            text="Nome do tema:",
            font=("Arial", 12, "bold"),
            text_color=getattr(self.app, "cor_texto", "#111827"),
        ).pack(side="left", padx=(0, 8))
        nome_var = tk.StringVar(value=f"{self.tema_atual} Personalizado")
        ctk.CTkEntry(bottom, textvariable=nome_var, height=34, width=320).pack(side="left", padx=(0, 8))

        botoes_campos = {}

        def atualizar_preview(*_):
            preview.update_preview(paleta_atual())

        def selecionar_campo(campo):
            selected["campo"] = campo
            valor = vars_criador[campo].get()
            if _valida_hex(valor):
                picker.set_color(valor)
            preview.highlight_element(campo)

        def atualizar_botao(campo, *_):
            valor = vars_criador[campo].get()
            if not _valida_hex(valor):
                return
            btn = botoes_campos.get(campo)
            if btn and btn.winfo_exists():
                btn.configure(fg_color=valor, hover_color=valor, text_color=get_contraste_texto(valor))
            atualizar_preview()

        def criar_linha(campo, row, col):
            frame = ctk.CTkFrame(
                scroll,
                fg_color=getattr(self.app, "cor_terciaria", "#D4D4D8"),
                corner_radius=8,
                border_width=1,
                border_color=getattr(self.app, "cor_borda", "#9CA3AF"),
            )
            frame.grid(row=row, column=col, sticky="ew", padx=5, pady=5)
            frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                frame,
                text=LABELS_CAMPOS_PADRAO.get(campo, campo),
                anchor="w",
                font=("Arial", 11, "bold"),
                text_color=getattr(self.app, "cor_texto", "#111827"),
            ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(6, 2))

            var = tk.StringVar(value="#FFFFFF")
            vars_criador[campo] = var
            entry = ctk.CTkEntry(frame, textvariable=var, height=30, font=("Arial", 11))
            entry.grid(row=1, column=0, sticky="ew", padx=(8, 6), pady=(0, 8))

            btn_cor = ctk.CTkButton(
                frame,
                text="",
                width=34,
                height=30,
                corner_radius=7,
                command=lambda c=campo: selecionar_campo(c),
            )
            btn_cor.grid(row=1, column=1, sticky="e", padx=(0, 8), pady=(0, 8))
            botoes_campos[campo] = btn_cor

            for widget in (frame, entry, btn_cor):
                widget.bind("<Enter>", lambda e, c=campo: preview.highlight_element(c))
                widget.bind("<Leave>", lambda e: preview.clear_highlight())

            var.trace_add("write", lambda *args, c=campo: atualizar_botao(c))

        for idx, campo in enumerate(CAMPOS_PADRAO):
            criar_linha(campo, idx // 2, idx % 2)

        def aplicar_paleta(paleta):
            for campo in CAMPOS_PADRAO:
                vars_criador[campo].set(paleta.get(campo, "#FFFFFF").upper())
            atualizar_preview()

        def gerar_outra():
            aplicar_paleta(self._gerar_pre_combinacao_tema())

        def salvar_novo_tema():
            nome = (nome_var.get() or "").strip()
            if not nome:
                self._mostrar_aviso("Informe um nome para salvar o tema personalizado.")
                return
            if nome in self.paletas.PADROES:
                self._mostrar_aviso("Esse nome ja existe nos temas padrao. Use outro nome para o tema personalizado.")
                return

            pal = paleta_atual()
            for campo, valor in pal.items():
                if not _valida_hex(valor):
                    self._mostrar_aviso(f"Cor invalida em {LABELS_CAMPOS_PADRAO.get(campo, campo)}: {valor}")
                    return

            self.paletas.salvar_tema_personalizado(nome, pal)
            salvou_banco = self._salvar_tema_personalizado_no_banco(nome, pal)
            self._refresh_theme_list()
            self._carregar_tema_no_editor(nome)
            if hasattr(self, "var_nome"):
                self.var_nome.set(nome)

            if salvou_banco:
                self._mostrar_info("Sucesso", f"Tema personalizado '{nome}' salvo.")
            else:
                self._mostrar_aviso(f"Tema '{nome}' salvo localmente, mas nao foi possivel salvar no banco.")
            janela.destroy()

        BotaoPadronizado.criar_botao(
            bottom,
            text="Gerar outra combinacao",
            tipo="filtrar",
            command=gerar_outra,
            height=34,
            width=180,
            font=("Arial", 12, "bold"),
        ).pack(side="left", padx=4)
        BotaoPadronizado.criar_botao(
            bottom,
            text="Salvar nos personalizados",
            tipo="salvar",
            command=salvar_novo_tema,
            height=34,
            width=210,
            font=("Arial", 12, "bold"),
        ).pack(side="right", padx=4)
        BotaoPadronizado.criar_botao(
            bottom,
            text="Cancelar",
            tipo="cancelar",
            command=janela.destroy,
            height=34,
            width=110,
            font=("Arial", 12, "bold"),
        ).pack(side="right", padx=4)

        aplicar_paleta(self._gerar_pre_combinacao_tema())
        selecionar_campo(CAMPOS_PADRAO[0])

    def _reset_editor_com_defaults(self):
        base_tema = self.tema_atual if self.tema_atual in self.paletas.PADROES else "CLÁSSICO CLARO"
        nome_sugestao = f"{base_tema} Personalizado"
        self.var_nome.set(nome_sugestao)
        self._carregar_tema_no_editor(base_tema)

    def _restaurar_tema(self):
        nome = (self.var_nome.get() or "").strip()
        if not nome:
            self._mostrar_aviso("Informe o nome do tema no campo 'Nome do Tema'.")
            return

        if nome not in self.paletas.temas_originais:
            self._mostrar_aviso(f"'{nome}' não é um tema padrão.")
            return

        tema_original = self.paletas.temas_originais[nome]
        self.paletas.PADROES[nome] = dict(tema_original)
        self._carregar_tema_no_editor(nome)
        self._aplicar_tema_completo(nome)
        self._mostrar_info("Sucesso", f"Tema '{nome}' restaurado para as configurações originais.")

    def _salvar_custom_completo(self):
        nome = (self.var_nome.get() or "").strip()
        if not nome:
            self._mostrar_aviso("Informe um nome para o tema.")
            return

        pal = {}
        for campo, var in self.vars.items():
            val = (var.get() or "").strip()
            if not _valida_hex(val):
                self._mostrar_aviso(f"Cor inválida: {val}")
                return
            pal[campo] = val.upper()

        self.paletas.salvar_tema_personalizado(nome, pal)

        salvou_no_banco = self._salvar_tema_personalizado_no_banco(nome, pal)

        if salvou_no_banco:
            self._mostrar_info("Sucesso", f"Tema '{nome}' salvo no banco e localmente!")
        else:
            self._mostrar_aviso(f"Tema '{nome}' salvo localmente, mas não foi possível salvar no banco.")

        self._aplicar_tema_completo(nome)

    def _salvar_tema_personalizado_no_banco(self, nome_tema, paleta, excluir=False):
        import json
        from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema

        try:
            usuario_id = getattr(self.app, "usuario_id", None)
            if not usuario_id:
                return False

            conn = get_conn()
            if not conn:
                return False

            schema = get_schema()

            if excluir:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {schema}.usuario_temas_personalizados WHERE usuario_id = %s AND nome_tema = %s",
                        (usuario_id, nome_tema),
                    )
                conn.commit()
                return True
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.usuario_temas_personalizados
                            (usuario_id, nome_tema, cores_tema, atualizado_em)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (usuario_id, nome_tema)
                        DO UPDATE SET
                            cores_tema = EXCLUDED.cores_tema,
                            atualizado_em = NOW();
                        """,
                        (usuario_id, nome_tema, json.dumps(paleta, ensure_ascii=False)),
                    )
                conn.commit()
                return True

        except Exception as e:
            if LOGGER:
                LOGGER.error(f"Erro ao salvar tema '{nome_tema}': {e}")
            return False

    def _excluir_tema_personalizado(self, nome_tema):
        resposta = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Deseja realmente excluir o tema '{nome_tema}'?\nEsta ação não pode ser desfeita."
        )

        if not resposta:
            return

        if nome_tema not in self.paletas.custom:
            self._mostrar_aviso(f"Tema personalizado '{nome_tema}' não encontrado.")
            return

        excluiu_banco = self._salvar_tema_personalizado_no_banco(nome_tema, paleta=None, excluir=True)

        if not excluiu_banco:
            messagebox.showerror(
                "Erro",
                f"Não foi possível excluir o tema '{nome_tema}' no banco de dados."
            )
            return

        self.paletas.remover_tema_personalizado(nome_tema)

        if hasattr(self, 'var_nome') and self.var_nome.get() == nome_tema:
            self._reset_editor_com_defaults()

        self._refresh_theme_list()

        messagebox.showinfo("Sucesso", f"Tema '{nome_tema}' excluído!")

    def _refresh_theme_list(self):
        if hasattr(self, 'left_panel') and self.left_panel.winfo_exists():
            for widget in self.left_panel.winfo_children():
                widget.destroy()
            self._build_left_panel(self.left_panel)

    def _rebuild_self_for_theme(self):
        """Reconstrói a própria página após troca de tema para evitar widgets desalinhados."""
        try:
            self.tema_atual = self._get_current_theme_name()
            self._configure_self()

            for widget in list(self.winfo_children()):
                try:
                    widget.destroy()
                except Exception:
                    pass

            self.left_panel = None
            self.right_panel = None
            self.preview_panel = None
            self._widget_cache.clear()

            self._build_interface()
            self.after(60, self._sync_page_after_theme_apply)
        except Exception as e:
            if LOGGER:
                LOGGER.error(f"Erro ao reconstruir página de temas: {e}")

    def _sync_page_after_theme_apply(self):
        """Sincroniza textos, listas e preview depois que a página foi recriada."""
        try:
            self.tema_atual = self._get_current_theme_name()
            self._refresh_theme_list()
            self._carregar_tema_no_editor(self.tema_atual)
        except Exception as e:
            if LOGGER:
                LOGGER.error(f"Erro ao sincronizar página de temas: {e}")

    def _aplicar_e_carregar_tema(self, nome):
        self._aplicar_tema_completo(nome)
        self._carregar_tema_no_editor(nome)

    def _aplicar_tema_completo(self, nome_tema):
        try:
            tema = self.paletas.obter_tema(nome_tema)
            if not tema:
                return False

            self._update_live_preview()

            theme_manager = getattr(self.app, "theme_manager", None)
            if theme_manager:
                theme_manager.apply_theme(nome_tema, tema)
            else:
                for campo, valor in tema.items():
                    setattr(self.app, f"cor_{campo}", valor)

            self.tema_atual = nome_tema
            self.app.tema_atual = nome_tema

            if hasattr(self.app, "current_theme_name"):
                self.app.current_theme_name = nome_tema
            if hasattr(self.app, "tema_preferido_inicial"):
                self.app.tema_preferido_inicial = nome_tema

            is_custom = nome_tema in self.paletas.custom
            paleta_custom = self.paletas.custom.get(nome_tema) if is_custom else None
            self._persistir_preferencia_usuario(nome_tema, paleta_custom)

            self._rebuild_self_for_theme()

            return True

        except Exception as e:
            if LOGGER:
                LOGGER.error(f"Erro ao aplicar tema '{nome_tema}': {e}")
            return False

    def _persistir_preferencia_usuario(self, nome_tema, paleta_custom=None):
        try:
            usuario_id = getattr(self.app, "usuario_id", None)
            if not usuario_id:
                return False

            user_manager = getattr(self.app, "user_manager", None)
            if user_manager:
                if paleta_custom:
                    import json
                    user_manager.save_user_theme_personalizado(nome_tema, json.dumps(paleta_custom))
                else:
                    user_manager.save_user_theme(nome_tema)

                if hasattr(self.app, "tema_preferido_inicial"):
                    self.app.tema_preferido_inicial = nome_tema
                if hasattr(self.app, "current_theme_name"):
                    self.app.current_theme_name = nome_tema
                return True

            tipo = "personalizado" if paleta_custom else "padrao"
            sucesso = self._salvar_preferencia_tema_atual(nome_tema, tipo, paleta_custom)

            if sucesso:
                if hasattr(self.app, "tema_preferido_inicial"):
                    self.app.tema_preferido_inicial = nome_tema
                if hasattr(self.app, "current_theme_name"):
                    self.app.current_theme_name = nome_tema
            return sucesso

        except Exception as e:
            if LOGGER:
                LOGGER.error(f"Erro ao persistir preferência: {e}")
            return False

    def _salvar_preferencia_tema_atual(self, nome_tema, tipo_tema, paleta_custom=None):
        try:
            from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema

            usuario_id = getattr(self.app, 'usuario_id', None)
            if not usuario_id:
                return False

            usar_tema_personalizado = tipo_tema == "personalizado"
            paleta_json = None
            if usar_tema_personalizado and paleta_custom:
                paleta_json = json.dumps(paleta_custom)

            schema = get_schema()
            conn = get_conn()

            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {schema}.usuario_preferencias
                        (usuario_id, tema_nome, usar_tema_personalizado, tema_personalizado, atualizado_em)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (usuario_id) DO UPDATE SET
                        tema_nome = EXCLUDED.tema_nome,
                        usar_tema_personalizado = EXCLUDED.usar_tema_personalizado,
                        tema_personalizado = EXCLUDED.tema_personalizado,
                        atualizado_em = NOW()
                    """,
                    (usuario_id, nome_tema, usar_tema_personalizado, paleta_json)
                )
            conn.commit()

            return True

        except Exception as e:
            if LOGGER:
                LOGGER.error(f"Erro ao salvar preferência: {e}")
            return False

    def _carregar_tema_no_editor(self, nome_tema):
        try:
            tema = self.paletas.obter_tema(nome_tema)
            if not tema:
                self._mostrar_aviso(f"Tema '{nome_tema}' não encontrado.")
                return

            for campo in CAMPOS_PADRAO:
                valor = tema.get(campo, "#FFFFFF")
                if campo in self.vars:
                    try:
                        self.vars[campo].set(valor.upper())
                    except Exception:
                        self.vars[campo].set(valor)

            if hasattr(self, "var_nome") and self.var_nome is not None:
                if not self.var_nome.get().strip():
                    self.var_nome.set(nome_tema)

            if hasattr(self, "preview_panel") and self.preview_panel.winfo_exists():
                try:
                    self.preview_panel.update_preview(tema)
                except Exception as e:
                    if LOGGER:
                        LOGGER.error(f"Erro ao atualizar preview: {e}")

            self.tema_atual = nome_tema

        except Exception as e:
            if LOGGER:
                LOGGER.error(f"Erro ao carregar tema no editor: {e}")
            self._mostrar_erro(f"Falha ao carregar o tema '{nome_tema}' no editor.\n\n{e}")

    def _carregar_tema_para_edicao(self, nome_tema):
        tema_data = self.paletas.obter_tema(nome_tema)

        if not tema_data:
            messagebox.showerror("Erro", f"Tema '{nome_tema}' não encontrado!")
            return

        self._carregar_tema_no_editor(nome_tema)

        nome_sugerido = f"{nome_tema} (Editado)"
        if hasattr(self, 'var_nome'):
            self.var_nome.set(nome_sugerido)

        messagebox.showinfo(
            "Tema Carregado para Edição",
            f"O tema '{nome_tema}' foi carregado no editor à direita."
        )

    def _editar_tema_personalizado(self, nome_tema):
        if nome_tema in self.paletas.custom:
            self._carregar_tema_no_editor(nome_tema)
            if hasattr(self, 'var_nome'):
                self.var_nome.set(nome_tema)

    def _duplicar_tema_personalizado(self, nome_tema):
        if nome_tema in self.paletas.custom:
            self._carregar_tema_no_editor(nome_tema)
            nome_sugerido = f"{nome_tema} (Cópia)"
            if hasattr(self, 'var_nome'):
                self.var_nome.set(nome_sugerido)
        else:
            self._mostrar_aviso(f"Tema personalizado '{nome_tema}' não encontrado.")

    def _criar_tema_da_base(self):
        if hasattr(self.app, 'tema_atual'):
            tema_atual_nome = self.app.tema_atual
            self._carregar_tema_no_editor(tema_atual_nome)
            nome_sugerido = f"{tema_atual_nome} (Cópia)"
            if hasattr(self, 'var_nome'):
                self.var_nome.set(nome_sugerido)

    def _restaurar_temas_padrao(self):
        resposta = messagebox.askyesno(
            "Restaurar Temas Padrão",
            "Esta ação irá recarregar os temas padrão. Continuar?"
        )

        if resposta:
            if hasattr(self.app, 'open_page'):
                self.app.open_page("Temas")
            messagebox.showinfo("Sucesso", "Temas padrão restaurados!")

    def _abrir_seletor_cor(self, campo):
        self.campo_selecionado = campo
        cor_atual = self.vars[campo].get()
        if _valida_hex(cor_atual) and hasattr(self, "color_picker"):
            self.color_picker.set_color(cor_atual)

    def _on_color_selected(self, color):
        if self.campo_selecionado:
            self.vars[self.campo_selecionado].set(color)

    def _update_live_preview(self):
        if hasattr(self, 'preview_panel') and self.preview_panel.winfo_exists():
            colors = {}
            for campo, var in self.vars.items():
                val = var.get()
                if _valida_hex(val):
                    colors[campo] = val
                else:
                    colors[campo] = "#FFFFFF"

            try:
                self.preview_panel.update_preview(colors)
            except Exception as e:
                if LOGGER:
                    LOGGER.error(f"Erro ao atualizar preview: {e}")

    def _safe_preview_highlight(self, campo):
        if hasattr(self, 'preview_panel') and self.preview_panel.winfo_exists():
            try:
                self.preview_panel.highlight_element(campo)
            except Exception:
                pass

    def _safe_preview_leave(self):
        if hasattr(self, 'preview_panel') and self.preview_panel.winfo_exists():
            try:
                self.preview_panel.clear_highlight()
                self._update_live_preview()
            except Exception:
                pass

    def _mostrar_info(self, titulo, mensagem):
        messagebox.showinfo(titulo, mensagem)

    def _mostrar_aviso(self, mensagem):
        messagebox.showwarning("Atenção", mensagem)

    def _mostrar_erro(self, mensagem):
        messagebox.showerror("Erro", mensagem)

    def _finalize_loading(self):
        pass

if __name__ == '__main__':
    print("🚀 INICIANDO SISTEMA DE TEMAS EM MODO DEMONSTRAÇÃO...")

    ctk.set_appearance_mode('dark')
    app = ctk.CTk()
    app.title('Sistema de Temas - Opera (Modo Isolado)')

    app._settings = {
        "theme": "CLÁSSICO CLARO",
        "custom_themes": {},
        "excluded_default_themes": []
    }

    paletas = ModuloPaletas()
    tema_base = paletas.PADROES.get("CLÁSSICO CLARO")
    if tema_base is None:
        tema_base = next(iter(paletas.PADROES.values()))

    for k, v in tema_base.items():
        setattr(app, f'cor_{k}', v)

    app.usuario_id = 1
    app.tema_atual = "CLÁSSICO CLARO"
    app.theme_manager = None
    app.user_manager = None
    app.tema_preferido_inicial = "CLÁSSICO CLARO"
    app.current_theme_name = "CLÁSSICO CLARO"

    page = TemasPage(app, app=app)
    page.pack(fill='both', expand=True, padx=20, pady=20)

    app.geometry('1400x800')
    app.minsize(1200, 700)

    status_frame = ctk.CTkFrame(app, fg_color="transparent")
    status_frame.pack(side="bottom", fill="x", padx=20, pady=10)

    ctk.CTkLabel(
        status_frame,
        text="🔧 Modo Demonstração - Temas do Sistema Guimma (Execução Isolada)",
        font=("Arial", 10),
        text_color="#888888"
    ).pack(side="left")

    print("\n" + "=" * 60)
    print("🎭 TEMAS DO SISTEMA GUIMMA - MODO DEMONSTRAÇÃO ISOLADO")
    print("=" * 60)
    print("📋 Executando como aplicação independente para testes.")
    print("🎮 Interface completa carregada com sucesso!")
    print("=" * 60)

    app.mainloop()

# --- Suporte trilíngue individual desta página ---
TemasPage_TRANSLATIONS = {
    "pt_BR": {
        "title": "Temas",
        "Atualizar": "Atualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
    },
    "en_US": {
        "title": "Themes",
        "Atualizar": "Refresh",
        "Filtrar": "Filter",
        "Limpar": "Clear",
        "Exportar": "Export",
        "Imprimir": "Print",
        "Buscar": "Search",
    },
    "es_ES": {
        "title": "Temas",
        "Atualizar": "Actualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpiar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
    },
}


def _apply_temaspage_translations(self):
    """Aplica tradução individual desta página."""
    idioma = getattr(getattr(self, "sistema", None), "idioma_atual", getattr(self, "idioma_atual", "pt_BR"))
    if idioma not in TemasPage_TRANSLATIONS:
        idioma = "pt_BR"
    if hasattr(self, "titulo"):
        try:
            self.titulo.configure(text=TemasPage_TRANSLATIONS[idioma]["title"])
        except Exception:
            pass


try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    TemasPage.TRANSLATIONS = TemasPage_TRANSLATIONS
    if not hasattr(TemasPage, "apply_page_translations"):
        TemasPage.apply_page_translations = _apply_temaspage_translations
    attach_i18n_support(TemasPage, TemasPage_TRANSLATIONS)
except Exception:
    pass
