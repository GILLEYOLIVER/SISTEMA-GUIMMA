"""Tela avançada de gerenciamento de temas do OPERA.

Esta página foi redesenhada para oferecer uma experiência profissional e
abrangente, permitindo ajustar todas as cores usadas pelo sistema, salvar no
banco e em arquivo, além de pré-visualizar em tempo real onde cada cor é
aplicada."""
from __future__ import annotations

import TEMAS
import importlib
import json
import os
from typing import Any, Dict, Optional, Tuple
import tkinter as tk
from tkinter import colorchooser, ttk

import customtkinter as ctk

from tema_database import DatabaseTemaManager

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")


# ==================== Utilidades locais ====================

# Fallback mínimo para usar caso não seja possível importar TEMAS (evita circular import)
PADROES_COMPLETOS = {
    "Azul Oceano": {
        "primaria": "#0D1B2A", "secundaria": "#1B263B", "terciaria": "#415A77", "fundo": "#0B1320",
        "texto": "#E0E1DD", "destaque": "#3A86FF", "sucesso": "#3BCF8E", "alerta": "#EF476F",
        "borda": "#2E4057", "hover": "#253041", "selecao": "#3A86FF",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Cinza Oceano Escuro": {
        "primaria": "#1A1A1A", "secundaria": "#242424", "terciaria": "#3E3E3E", "fundo": "#141414",
        "texto": "#E0E1DD", "destaque": "#6B6B6B", "sucesso": "#3BCF8E", "alerta": "#EF476F",
        "borda": "#353535", "hover": "#2A2A2A", "selecao": "#6B6B6B",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Grafite Oceano": {
        "primaria": "#0F0F0F", "secundaria": "#1C1C1C", "terciaria": "#333333", "fundo": "#0A0A0A",
        "texto": "#E0E1DD", "destaque": "#5A5A5A", "sucesso": "#3BCF8E", "alerta": "#EF476F",
        "borda": "#2B2B2B", "hover": "#1F1F1F", "selecao": "#5A5A5A",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Carvão Oceano": {
        "primaria": "#121212", "secundaria": "#1F1F1F", "terciaria": "#3A3A3A", "fundo": "#0D0D0D",
        "texto": "#E0E1DD", "destaque": "#4D4D4D", "sucesso": "#3BCF8E", "alerta": "#EF476F",
        "borda": "#2E2E2E", "hover": "#232323", "selecao": "#4D4D4D",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Cinza Oceano Claro": {
        "primaria": "#D5D5D5", "secundaria": "#C2C2C2", "terciaria": "#9E9E9E", "fundo": "#E8E8E8",
        "texto": "#1A1A1A", "destaque": "#6B6B6B", "sucesso": "#2E9E6E", "alerta": "#D63854",
        "borda": "#ABABAB", "hover": "#CFCFCF", "selecao": "#6B6B6B",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Prata Oceano": {
        "primaria": "#BEBEBE", "secundaria": "#ABABAB", "terciaria": "#8A8A8A", "fundo": "#D4D4D4",
        "texto": "#1A1A1A", "destaque": "#5A5A5A", "sucesso": "#2E9E6E", "alerta": "#D63854",
        "borda": "#999999", "hover": "#B5B5B5", "selecao": "#5A5A5A",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Névoa Oceano": {
        "primaria": "#C9C9C9", "secundaria": "#B6B6B6", "terciaria": "#949494", "fundo": "#DEDEDE",
        "texto": "#1A1A1A", "destaque": "#636363", "sucesso": "#2E9E6E", "alerta": "#D63854",
        "borda": "#A3A3A3", "hover": "#808080", "selecao": "#008000",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Rosé Elegante": {
        "primaria": "#2B2233", "secundaria": "#3A2A45", "terciaria": "#5E3C58", "fundo": "#241C2B",
        "texto": "#FFE9F3", "destaque": "#FF5C8A", "sucesso": "#72E5C1", "alerta": "#FF7B7B",
        "borda": "#4B3B55", "hover": "#34283F", "selecao": "#FF5C8A",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Terra Natural": {
        "primaria": "#2E241A", "secundaria": "#3B2F22", "terciaria": "#6B4E3D", "fundo": "#221A12",
        "texto": "#F0E7DD", "destaque": "#D9A441", "sucesso": "#7FB069", "alerta": "#CE6A46",
        "borda": "#4A3A2C", "hover": "#3A2D22", "selecao": "#D9A441",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Noite Urbana": {
        "primaria": "#121212", "secundaria": "#1F1F1F", "terciaria": "#3E3E3E", "fundo": "#181818",
        "texto": "#EEEEEE", "destaque": "#BB86FC", "sucesso": "#03DAC6", "alerta": "#CF6679",
        "borda": "#3A3A3A", "hover": "#2C2C2C", "selecao": "#BB86FC",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Minimal": {
        "primaria": "#F5F5F5", "secundaria": "#E0E0E0", "terciaria": "#C2C2C2", "fundo": "#FFFFFF",
        "texto": "#212121", "destaque": "#9E9E9E", "sucesso": "#66BB6A", "alerta": "#EF5350",
        "borda": "#BDBDBD", "hover": "#EEEEEE", "selecao": "#9E9E9E",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Roxo Elegante": {
        "primaria": "#1E1327", "secundaria": "#291A36", "terciaria": "#432C56", "fundo": "#180F22",
        "texto": "#EDE7F6", "destaque": "#7C4DFF", "sucesso": "#00E5FF", "alerta": "#F06292",
        "borda": "#352443", "hover": "#241633", "selecao": "#7C4DFF",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Verde Corporativo": {
        "primaria": "#0F241D", "secundaria": "#15342A", "terciaria": "#1F4D3D", "fundo": "#0B1A15",
        "texto": "#E8F5E9", "destaque": "#26A69A", "sucesso": "#66BB6A", "alerta": "#FF7043",
        "borda": "#1A3A2F", "hover": "#17362D", "selecao": "#26A69A",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Preto e Ouro": {
        "primaria": "#121212", "secundaria": "#1A1A1A", "terciaria": "#333333", "fundo": "#0B0B0B",
        "texto": "#F6F3E7", "destaque": "#D4AF37", "sucesso": "#7CB342", "alerta": "#F4511E",
        "borda": "#2E2E2E", "hover": "#222222", "selecao": "#D4AF37",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Clássico": {
        "primaria": "#20232A", "secundaria": "#2C313C", "terciaria": "#3B4252", "fundo": "#1B1E24",
        "texto": "#ECEFF4", "destaque": "#61AFEF", "sucesso": "#98C379", "alerta": "#E06C75",
        "borda": "#2E3440", "hover": "#262B36", "selecao": "#61AFEF",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "NOTURNO": {
        "primaria": "#0C0F14", "secundaria": "#141824", "terciaria": "#1E2635", "fundo": "#0B0E13",
        "texto": "#DDE2E9", "destaque": "#4CC9F0", "sucesso": "#2DE2A6", "alerta": "#FF477E",
        "borda": "#1A2030", "hover": "#171C28", "selecao": "#4CC9F0",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "CLÁSSICO CLARO": {
        "primaria": "#FAFAFA", "secundaria": "#F0F0F0", "terciaria": "#D9D9D9", "fundo": "#FFFFFF",
        "texto": "#222222", "destaque": "#0078D4", "sucesso": "#2E7D32", "alerta": "#C62828",
        "borda": "#CCCCCC", "hover": "#F5F5F5", "selecao": "#0078D4",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "CLÁSSICO ESCURO": {
        "primaria": "#2A2F3A", "secundaria": "#374151", "terciaria": "#4B5563", "fundo": "#232833",
        "texto": "#F3F4F6", "destaque": "#6CB4FF", "sucesso": "#A3D9A5", "alerta": "#F28B82",
        "borda": "#3B4552", "hover": "#303745", "selecao": "#6CB4FF",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Slate Pro": {
        "primaria": "#1F2937", "secundaria": "#273246", "terciaria": "#3B4B63", "fundo": "#151A24",
        "texto": "#E5E7EB", "destaque": "#60A5FA", "sucesso": "#34D399", "alerta": "#F87171",
        "borda": "#2C3647", "hover": "#232C3B", "selecao": "#60A5FA",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Grafite Clean": {
        "primaria": "#222222", "secundaria": "#2C2C2C", "terciaria": "#3A3A3A", "fundo": "#1A1A1A",
        "texto": "#EDEDED", "destaque": "#8AB4F8", "sucesso": "#57D38C", "alerta": "#FF6B6B",
        "borda": "#333333", "hover": "#2A2A2A", "selecao": "#8AB4F8",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Aço Azul": {
        "primaria": "#16212F", "secundaria": "#1E2B3C", "terciaria": "#2C3E55", "fundo": "#111925",
        "texto": "#E6EDF5", "destaque": "#4EA8DE", "sucesso": "#2DD4BF", "alerta": "#FB7185",
        "borda": "#233247", "hover": "#1B2738", "selecao": "#4EA8DE",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Oliva Urbano": {
        "primaria": "#172017", "secundaria": "#1F2A1F", "terciaria": "#2C3A2C", "fundo": "#121A12",
        "texto": "#E9F5EA", "destaque": "#7FB069", "sucesso": "#86EFAC", "alerta": "#F59E0B",
        "borda": "#223123", "hover": "#1A241A", "selecao": "#7FB069",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Cobalto Pro": {
        "primaria": "#0F1626", "secundaria": "#172035", "terciaria": "#22314F", "fundo": "#0B1120",
        "texto": "#E2E8F0", "destaque": "#3B82F6", "sucesso": "#10B981", "alerta": "#EF4444",
        "borda": "#1B2740", "hover": "#132037", "selecao": "#3B82F6",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Petróleo": {
        "primaria": "#102022", "secundaria": "#173034", "terciaria": "#22464C", "fundo": "#0B1719",
        "texto": "#E3F2F4", "destaque": "#22D3EE", "sucesso": "#34D399", "alerta": "#F59E0B",
        "borda": "#1A3236", "hover": "#13282C", "selecao": "#22D3EE",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Chumbo & Laranja": {
        "primaria": "#1A1E24", "secundaria": "#232833", "terciaria": "#2E3542", "fundo": "#141821",
        "texto": "#EDEFF3", "destaque": "#FB923C", "sucesso": "#22C55E", "alerta": "#EF4444",
        "borda": "#2A303C", "hover": "#1D2230", "selecao": "#FB923C",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Neve Azul": {
        "primaria": "#E9EEF5", "secundaria": "#DDE6F1", "terciaria": "#C9D4E6", "fundo": "#F6FAFF",
        "texto": "#1F2937", "destaque": "#2563EB", "sucesso": "#059669", "alerta": "#DC2626",
        "borda": "#CBD5E1", "hover": "#E2EAF6", "selecao": "#2563EB",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    },

    "Titanium": {
        "primaria": "#1C1F26", "secundaria": "#262A33", "terciaria": "#313643", "fundo": "#171A21",
        "texto": "#E6E8EB", "destaque": "#9AA4FF", "sucesso": "#5EEAD4", "alerta": "#F87171",
        "borda": "#2A2E38", "hover": "#1F2330", "selecao": "#9AA4FF",
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    }
}


def _try_import_temas_utils():
    """Tenta importar utilitários do TEMAS.py sem causar falhas de import circular."""
    temas_mod = None
    try:
        temas_mod = importlib.import_module("TEMAS")
    except Exception as exc:  # pragma: no cover - apenas log informativo
        print(f"⚠️ Não foi possível importar TEMAS diretamente: {exc}")

    if temas_mod:
        globals()["ajustar_hover"] = getattr(temas_mod, "ajustar_hover", ajustar_hover)
        globals()["get_contraste_texto"] = getattr(temas_mod, "get_contraste_texto", get_contraste_texto)
        globals()["is_dark_color"] = getattr(temas_mod, "is_dark_color", is_dark_color)
        return getattr(temas_mod, "TemasPage", None)
    return None


# Fallbacks básicos caso o import acima não aconteça
def get_contraste_texto(cor_fundo):
    try:
        if not cor_fundo or not isinstance(cor_fundo, str):
            return "#000000"
        hex_color = cor_fundo.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#000000" if luminance > 0.5 else "#FFFFFF"
    except Exception:
        return "#000000"


def is_dark_color(cor):
    try:
        if not cor or not isinstance(cor, str):
            return False
        hex_color = cor.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance <= 0.5
    except Exception:
        return False


def ajustar_hover(cor_base, fator=0.8):
    try:
        if not cor_base or not isinstance(cor_base, str):
            return cor_base
        hex_color = cor_base.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        r = int(r * fator)
        g = int(g * fator)
        b = int(b * fator)
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return f"#{r:02x}{g:02x}{b:02x}".upper()
    except Exception:
        return cor_base


# ==================== Persistência ====================

def _get_user_id(app=None) -> Optional[int]:
    if not app:
        return None
    return getattr(app, "usuario_id", None) or getattr(app, "user_id", None)


def carregar_settings(app=None) -> Dict:
    """Carrega as preferências do usuário a partir do banco ou fallback local."""
    db = DatabaseTemaManager(app)
    user_id = _get_user_id(app)
    settings = db.carregar_preferencias_usuario(user_id=user_id)

    if not settings:
        base = {
            "theme": "Noite Urbana",
            "custom_themes": {},
            "excluded_default_themes": [],
            "aplicar_dashboard": True,
            "aplicar_tabelas": True,
            "aplicar_login": True,
        }
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        base.update(data)
            except Exception:
                pass
        settings = base
    return settings


def salvar_settings(settings: Dict, app=None) -> None:
    """Salva preferências no banco e, como backup, no arquivo settings.json."""
    db = DatabaseTemaManager(app)
    user_id = _get_user_id(app)
    db.salvar_preferencias_usuario(settings, user_id=user_id)

    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"⚠️ Não foi possível salvar settings localmente: {exc}")


# ==================== Página ====================

class Tema2Page(ctk.CTkFrame):
    """Tela de gerenciamento avançado de temas com pré-visualização."""

    # Catálogo padrão exposto para chamadas externas (ex.: ThemeManager)
    PADROES: Dict[str, Dict[str, str]] = dict(PADROES_COMPLETOS)

    # grupos para ficar claro onde cada cor é aplicada
    BASE_COLORS: Tuple[Tuple[str, str, str], ...] = (
        ("fundo", "Fundo / Janela", "Placa de fundo das telas e containers"),
        ("primaria", "Primária", "Topos, cabeçalhos e barras principais"),
        ("secundaria", "Secundária", "Blocos de conteúdo e cartões"),
        ("terciaria", "Terciária", "Detalhes e áreas de apoio"),
        ("borda", "Bordas", "Linhas divisórias e contornos"),
        ("hover", "Hover", "Efeitos ao passar o mouse"),
        ("selecao", "Seleção", "Listas, menus e campos selecionados"),
        ("texto", "Texto", "Textos principais"),
        ("destaque", "Destaque", "Links e elementos de realce"),
    )

    FEEDBACK_COLORS: Tuple[Tuple[str, str, str], ...] = (
        ("sucesso", "Sucesso", "Confirmações, badges positivos"),
        ("alerta", "Alerta", "Erros, avisos e estados críticos"),
    )

    BUTTON_COLORS: Tuple[Tuple[str, str, str], ...] = (
        ("botao_salvar", "Salvar", "Botões de confirmação e salvar"),
        ("botao_excluir", "Excluir", "Ações destrutivas"),
        ("botao_novo", "Novo", "Criações e cadastros"),
        ("botao_imprimir", "Imprimir", "Ações de impressão"),
        ("botao_pdf", "PDF", "Exportação PDF"),
        ("botao_editar", "Editar", "Edição de registros"),
        ("botao_visualizar", "Visualizar", "Visualização detalhada"),
        ("botao_confirmar", "Confirmar", "Confirmações gerais"),
        ("botao_cancelar", "Cancelar", "Reversão/voltar"),
        ("botao_exportar", "Exportar", "Exportações de dados"),
        ("botao_importar", "Importar", "Importações de dados"),
        ("botao_configurar", "Configurar", "Ajustes e configurações"),
        ("botao_ajuda", "Ajuda", "Atalhos e suporte"),
        ("botao_filtrar", "Filtrar", "Filtros e buscas"),
        ("botao_limpar", "Limpar", "Limpeza de filtros"),
        ("botao_voltar", "Voltar", "Navegação retroceder"),
        ("botao_avancar", "Avançar", "Navegação avançar"),
        ("botao_adiantamento", "Adiantamento", "Fluxo financeiro"),
        ("botao_comprovante", "Comprovante", "Emissão de comprovantes"),
        ("botao_buscar", "Buscar", "Botões de busca"),
        ("botao_export_csv", "Exportar CSV", "Exportação CSV"),
        ("botao_export_pdf", "Exportar PDF", "Exportação PDF"),
    )

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.settings = carregar_settings(app)
        self.db_manager = DatabaseTemaManager(app)
        self.indicador_cor_base = "#2b2b2b"
        self.indicador_cores: Dict[str, str] = {}

        # Importa utilitários do TEMAS apenas quando necessário para evitar loop de importação
        temas_cls = _try_import_temas_utils()
        if temas_cls and hasattr(temas_cls, "PADROES"):
            self.temas_padrao: Dict[str, Dict[str, str]] = dict(temas_cls.PADROES)
        else:
            self.temas_padrao = dict(PADROES_COMPLETOS)

        # mantém atributo de classe acessível para consumidores externos
        Tema2Page.PADROES = dict(self.temas_padrao)

        self.temas_personalizados: Dict[str, Dict[str, str]] = self.settings.get(
            "custom_themes", {}
        )
        self._carregar_personalizados_db()
        self.tema_selecionado = tk.StringVar(value=self.settings.get("theme", "Noite Urbana"))
        self.status_var = tk.StringVar(value="")
        self.sync_db = tk.BooleanVar(value=True)
        self.aplicar_dashboard = tk.BooleanVar(value=self.settings.get("aplicar_dashboard", True))
        self.aplicar_tabelas = tk.BooleanVar(value=self.settings.get("aplicar_tabelas", True))
        self.aplicar_login = tk.BooleanVar(value=self.settings.get("aplicar_login", True))
        self.campo_em_edicao = tk.StringVar(value="")

        self._montar_layout()
        self._popular_lista_temas()
        self._carregar_tema(self.tema_selecionado.get())

    # ==================== Layout ====================
    def _montar_layout(self):
        self.grid_columnconfigure(0, weight=2, minsize=220)
        self.grid_columnconfigure(1, weight=7, minsize=640)
        self.grid_columnconfigure(2, weight=5, minsize=520)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=10)
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(6, 4))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Painel avançado de temas",
            font=("Arial", 19, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(6, 2))
        ctk.CTkLabel(
            header,
            text=(
                "Ajuste todas as cores do OPERA, visualize os impactos e sincronize suas "
                "preferências com o banco de dados."
            ),
            text_color="#94a3b8",
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))

    def _carregar_personalizados_db(self):
        """Mescla temas personalizados gravados no banco para o usuário atual."""

        if not self.db_manager:
            return

        try:
            user_id = _get_user_id(self.app)
            if not user_id:
                return
            temas_db = self.db_manager.listar_temas_personalizados(user_id=user_id)
            if temas_db:
                self.temas_personalizados.update(temas_db)
                self.settings["custom_themes"] = dict(self.temas_personalizados)
        except Exception as exc:
            print(f"⚠️ Não foi possível carregar temas personalizados do banco: {exc}")

        # Painel esquerdo: lista de temas
        self.frame_lista = ctk.CTkFrame(self, corner_radius=12)
        self.frame_lista.grid(row=1, column=0, sticky="ns", padx=(12, 8), pady=10)

        titulo_lista = ctk.CTkLabel(
            self.frame_lista,
            text="Temas disponíveis",
            font=("Arial", 13, "bold"),
        )
        titulo_lista.pack(padx=12, pady=(12, 6))

        self.lista_temas = ctk.CTkScrollableFrame(self.frame_lista, width=230, height=560)
        self.lista_temas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Painel central: edição de paleta (com rolagem para não cortar conteúdos)
        self.frame_edicao = ctk.CTkFrame(self, corner_radius=12)
        self.frame_edicao.grid(row=1, column=1, sticky="nsew", padx=8, pady=10)
        self.frame_edicao.grid_columnconfigure(0, weight=1)
        self.frame_edicao.grid_rowconfigure(0, weight=1)

        self.frame_edicao_scroll = ctk.CTkScrollableFrame(
            self.frame_edicao, corner_radius=0, fg_color="transparent"
        )
        self.frame_edicao_scroll.grid(row=0, column=0, sticky="nsew")
        self.frame_edicao_scroll.grid_columnconfigure((0, 1), weight=1, minsize=310)

        self.personalizados_frame = ctk.CTkFrame(self.frame_edicao_scroll, corner_radius=10)
        self.personalizados_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(14, 10))
        self.personalizados_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.personalizados_frame,
            text="Área de temas personalizados",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(6, 2))

        stats_frame = ctk.CTkFrame(self.personalizados_frame, fg_color="transparent")
        stats_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        stats_frame.grid_columnconfigure((0, 1), weight=1)
        self.lbl_contagem_padrao = ctk.CTkLabel(stats_frame, text="Padrões: 0")
        self.lbl_contagem_personalizado = ctk.CTkLabel(stats_frame, text="Personalizados: 0")
        self.lbl_contagem_padrao.grid(row=0, column=0, sticky="w")
        self.lbl_contagem_personalizado.grid(row=0, column=1, sticky="e")

        self.nome_tema_entry = ctk.CTkEntry(
            self.personalizados_frame,
            placeholder_text="Nome do tema",
            height=38,
        )
        self.nome_tema_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 6))

        self.observacao_entry = ctk.CTkEntry(
            self.personalizados_frame,
            placeholder_text="Observação ou cliente (opcional)",
            height=32,
        )
        self.observacao_entry.grid(row=3, column=0, sticky="ew", pady=(2, 8))

        self.personalizados_box = ctk.CTkTextbox(
            self.personalizados_frame,
            height=80,
            wrap="word",
            activate_scrollbars=False,
        )
        self.personalizados_box.grid(row=4, column=0, columnspan=2, sticky="ew")
        self.personalizados_box.configure(state="disabled")

        toggle_frame = ctk.CTkFrame(self.frame_edicao_scroll, fg_color="transparent")
        toggle_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16)
        toggle_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(toggle_frame, text="Sincronizar com banco de dados").grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkSwitch(
            toggle_frame,
            variable=self.sync_db,
            text="",
        ).grid(row=0, column=1, sticky="e")

        integracoes = ctk.CTkFrame(self.frame_edicao_scroll, fg_color="transparent")
        integracoes.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))
        integracoes.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            integracoes, text="Aplicação no sistema", font=("Arial", 12, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(4, 6))
        ctk.CTkLabel(integracoes, text="Dashboard e cards").grid(row=1, column=0, sticky="w")
        ctk.CTkSwitch(integracoes, variable=self.aplicar_dashboard, text="").grid(row=1, column=1, sticky="e")
        ctk.CTkLabel(integracoes, text="Tabelas e listas").grid(row=2, column=0, sticky="w", pady=(2, 0))
        ctk.CTkSwitch(integracoes, variable=self.aplicar_tabelas, text="").grid(row=2, column=1, sticky="e", pady=(2, 0))
        ctk.CTkLabel(integracoes, text="Tela de login / splash").grid(row=3, column=0, sticky="w", pady=(2, 0))
        ctk.CTkSwitch(integracoes, variable=self.aplicar_login, text="").grid(row=3, column=1, sticky="e", pady=(2, 0))

        linha_sep = ctk.CTkFrame(self.frame_edicao_scroll, height=2, fg_color="#1f2937")
        linha_sep.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(8, 10))

        self.campos_cor: Dict[str, ctk.CTkEntry] = {}
        self._montar_grupo_cores(self.BASE_COLORS, titulo="Estrutura e texto", start_row=4, cols=2)
        next_row = 4 + (len(self.BASE_COLORS) // 2) + (1 if len(self.BASE_COLORS) % 2 else 0) + 1
        self._montar_grupo_cores(self.FEEDBACK_COLORS, titulo="Feedbacks", start_row=next_row, cols=2)
        next_row += (len(self.FEEDBACK_COLORS) // 2) + (1 if len(self.FEEDBACK_COLORS) % 2 else 0) + 1
        self._montar_grupo_cores(self.BUTTON_COLORS, titulo="Botões", start_row=next_row, cols=2)

        # Barra fixa de ações (não some com a rolagem)
        botoes = ctk.CTkFrame(self.frame_edicao, fg_color="transparent")
        botoes.grid(row=1, column=0, sticky="ew", padx=16, pady=(10, 6))
        botoes.grid_columnconfigure((0, 1, 2), weight=1, minsize=170)

        self.btn_aplicar = ctk.CTkButton(
            botoes, text="Aplicar tema", command=self._aplicar_tema, height=36
        )
        self.btn_aplicar.grid(row=0, column=0, padx=6)

        self.btn_salvar = ctk.CTkButton(
            botoes, text="Salvar personalizado", command=self._salvar_personalizado, height=36
        )
        self.btn_salvar.grid(row=0, column=1, padx=6)

        self.btn_excluir = ctk.CTkButton(
            botoes,
            text="Excluir personalizado",
            command=self._excluir_personalizado,
            height=36,
            fg_color="#ef4444",
            hover_color=ajustar_hover("#ef4444"),
            text_color=get_contraste_texto("#ef4444"),
        )
        self.btn_excluir.grid(row=0, column=2, padx=6)

        self.lbl_status = ctk.CTkLabel(
            self.frame_edicao,
            textvariable=self.status_var,
            text_color="#16a34a",
        )
        self.lbl_status.grid(row=2, column=0, sticky="w", padx=22, pady=(0, 10))

        # Painel direito: pré-visualização
        self.preview_frame = ctk.CTkFrame(self, corner_radius=12)
        self.preview_frame.grid(row=1, column=2, sticky="nsew", padx=(8, 16), pady=10)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.preview_frame, text="Pré-visualização do tema", font=("Arial", 13, "bold")
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))

        self.preview_area = ctk.CTkFrame(self.preview_frame, corner_radius=10)
        self.preview_area.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.preview_area.grid_columnconfigure(0, weight=1)

        self._montar_preview_widgets()

    def _montar_grupo_cores(
        self,
        campos: Tuple[Tuple[str, str, str], ...],
        titulo: str,
        start_row: int,
        cols: int = 1,
    ):
        titulo_lbl = ctk.CTkLabel(
            self.frame_edicao_scroll,
            text=titulo,
            font=("Arial", 12, "bold"),
        )
        titulo_lbl.grid(row=start_row, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 4))
        row = start_row + 1

        for index, (campo, label, dica) in enumerate(campos):
            col = index % cols
            grid_row = row + (index // cols)

            wrapper = ctk.CTkFrame(self.frame_edicao_scroll, fg_color="transparent")
            wrapper.grid(row=grid_row, column=col, sticky="ew", padx=16, pady=4)
            wrapper.grid_columnconfigure(1, weight=1)

            indicador = ctk.CTkLabel(
                wrapper,
                text="",
                width=18,
                height=18,
                corner_radius=6,
                fg_color=self.indicador_cor_base,
            )
            indicador.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0, 8))

            lbl = ctk.CTkLabel(wrapper, text=label)
            lbl.grid(row=0, column=1, sticky="w")
            lbl.bind("<Enter>", lambda e, text=dica: self._mostrar_status(text, sucesso=True))
            lbl.bind("<Leave>", lambda e: self._mostrar_status("", True))

            entry = ctk.CTkEntry(wrapper, placeholder_text="#RRGGBB", height=32)
            entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
            entry.bind("<FocusIn>", lambda e, c=campo: self._destacar_area(c))
            btn = ctk.CTkButton(
                wrapper,
                width=38,
                text="🎨",
                command=lambda c=campo: self._selecionar_cor(c),
            )
            btn.grid(row=1, column=2, padx=(6, 0))
            btn.bind("<FocusIn>", lambda e, c=campo: self._destacar_area(c))

            self.campos_cor[campo] = entry
            if not hasattr(self, "indicadores"):
                self.indicadores = {}
            self.indicadores[campo] = indicador

    def _montar_preview_widgets(self):
        self.preview_header = ctk.CTkFrame(self.preview_area, corner_radius=8)
        self.preview_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        self.preview_header.grid_columnconfigure(1, weight=1)

        self.preview_title = ctk.CTkLabel(
            self.preview_header, text="Título da tela", font=("Arial", 16, "bold")
        )
        self.preview_title.grid(row=0, column=0, sticky="w", padx=8, pady=6)

        self.preview_actions = ctk.CTkFrame(self.preview_header, fg_color="transparent")
        self.preview_actions.grid(row=0, column=1, sticky="e", padx=8)

        self.preview_btn_primary = ctk.CTkButton(
            self.preview_actions, text="Primário", width=100
        )
        self.preview_btn_secondary = ctk.CTkButton(
            self.preview_actions, text="Secundário", width=100
        )
        self.preview_btn_primary.grid(row=0, column=0, padx=4)
        self.preview_btn_secondary.grid(row=0, column=1, padx=4)

        self.preview_body = ctk.CTkFrame(self.preview_area, corner_radius=8)
        self.preview_body.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.preview_body.grid_columnconfigure(1, weight=1)

        # Filtros e chips
        self.preview_filters = ctk.CTkFrame(self.preview_body, corner_radius=8)
        self.preview_filters.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(8, 6))
        self.preview_filters.grid_columnconfigure((0, 1, 2), weight=1)
        self.preview_chip_1 = ctk.CTkLabel(self.preview_filters, text="Filtro ativo")
        self.preview_chip_2 = ctk.CTkLabel(self.preview_filters, text="Selecionado")
        self.preview_chip_3 = ctk.CTkLabel(self.preview_filters, text="Aviso")
        self.preview_chip_1.grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        self.preview_chip_2.grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        self.preview_chip_3.grid(row=0, column=2, padx=6, pady=6, sticky="ew")

        self.preview_resumos = ctk.CTkFrame(self.preview_body, corner_radius=8)
        self.preview_resumos.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))
        self.preview_resumos.grid_columnconfigure((0, 1, 2), weight=1)
        self.preview_resumo_est = ctk.CTkLabel(self.preview_resumos, text="Estoque\n58 itens", height=52, corner_radius=8, padx=10)
        self.preview_resumo_ord = ctk.CTkLabel(self.preview_resumos, text="Ordens\n14 em produção", height=52, corner_radius=8, padx=10)
        self.preview_resumo_fin = ctk.CTkLabel(self.preview_resumos, text="Financeiro\nR$ 42k", height=52, corner_radius=8, padx=10)
        self.preview_resumo_est.grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        self.preview_resumo_ord.grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        self.preview_resumo_fin.grid(row=0, column=2, padx=6, pady=6, sticky="ew")

        self.preview_card = ctk.CTkFrame(self.preview_body, corner_radius=8)
        self.preview_card.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=6)
        self.preview_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.preview_card,
            text="Card demonstrativo",
            font=("Arial", 13, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        self.preview_card_text = ctk.CTkLabel(
            self.preview_card,
            text=(
                "Visualização das cores aplicadas em elementos de cartão, listas e "
                "campos de texto."
            ),
            wraplength=360,
        )
        self.preview_card_text.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))

        self.preview_alert_success = ctk.CTkLabel(
            self.preview_card,
            text="Mensagem de sucesso",
            corner_radius=6,
            padx=10,
            pady=6,
        )
        self.preview_alert_success.grid(row=2, column=0, sticky="ew", padx=10, pady=4)

        self.preview_alert_error = ctk.CTkLabel(
            self.preview_card,
            text="Mensagem de alerta/erro",
            corner_radius=6,
            padx=10,
            pady=6,
        )
        self.preview_alert_error.grid(row=3, column=0, sticky="ew", padx=10, pady=(4, 10))

        self.preview_badges = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.preview_badges.grid(row=4, column=0, sticky="w", padx=10, pady=(0, 8))
        self.preview_badge_status = ctk.CTkLabel(self.preview_badges, text="Status: Em produção", corner_radius=10, padx=10, pady=6)
        self.preview_badge_cliente = ctk.CTkLabel(self.preview_badges, text="Cliente VIP", corner_radius=10, padx=10, pady=6)
        self.preview_badge_prioridade = ctk.CTkLabel(self.preview_badges, text="Prioridade alta", corner_radius=10, padx=10, pady=6)
        self.preview_badge_status.grid(row=0, column=0, padx=4, pady=2)
        self.preview_badge_cliente.grid(row=0, column=1, padx=4, pady=2)
        self.preview_badge_prioridade.grid(row=0, column=2, padx=4, pady=2)

        self.preview_progress = ctk.CTkProgressBar(self.preview_card, height=10)
        self.preview_progress.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.preview_progress.set(0.65)

        # Formulário e tabela
        self.preview_form = ctk.CTkFrame(self.preview_body, corner_radius=8)
        self.preview_form.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.preview_form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.preview_form, text="Formulário", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 4)
        )
        self.preview_input_1 = ctk.CTkEntry(self.preview_form, placeholder_text="Campo de texto")
        self.preview_input_2 = ctk.CTkEntry(self.preview_form, placeholder_text="Outro campo")
        self.preview_input_1.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=4)
        self.preview_input_2.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 10))

        self.preview_table = ctk.CTkFrame(self.preview_body, corner_radius=8)
        self.preview_table.grid(row=3, column=1, sticky="nsew", padx=10, pady=(0, 8))
        self.preview_table.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(self.preview_table, text="Tabela", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 4)
        )
        self.preview_table_headers = []
        for idx, title in enumerate(["Código", "Status", "Ação"]):
            lbl = ctk.CTkLabel(self.preview_table, text=title, font=("Arial", 11, "bold"))
            lbl.grid(row=1, column=idx, sticky="ew", padx=6, pady=4)
            self.preview_table_headers.append(lbl)
        self.preview_row_status = ctk.CTkLabel(self.preview_table, text="Em produção")
        self.preview_row_action = ctk.CTkButton(self.preview_table, text="Editar", width=80)
        ctk.CTkLabel(self.preview_table, text="#1023").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.preview_row_status.grid(row=2, column=1, sticky="ew", padx=6, pady=4)
        self.preview_row_action.grid(row=2, column=2, sticky="e", padx=6, pady=4)

        self.preview_tree_frame = ctk.CTkFrame(self.preview_body, corner_radius=8)
        self.preview_tree_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 8))
        self.preview_tree_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.preview_tree_frame, text="Treeview (listas)", font=("Arial", 12, "bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(8, 4)
        )
        self.tree_style = ttk.Style(self)
        self.tree_style_name = "Preview.Treeview"
        self.preview_tree = ttk.Treeview(
            self.preview_tree_frame,
            columns=("codigo", "cliente", "status"),
            show="headings",
            style=self.tree_style_name,
            height=4,
        )
        self.preview_tree.heading("codigo", text="Código")
        self.preview_tree.heading("cliente", text="Cliente")
        self.preview_tree.heading("status", text="Status")
        self.preview_tree.column("codigo", width=100, anchor="center")
        self.preview_tree.column("cliente", width=220)
        self.preview_tree.column("status", width=140, anchor="center")
        for cod, cliente, status in [("#1001", "Alfa Têxtil", "Em produção"), ("#1002", "Beta Confecções", "Faturado")]:
            self.preview_tree.insert("", "end", values=(cod, cliente, status))
        self.preview_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.preview_timeline = ctk.CTkFrame(self.preview_body, corner_radius=8)
        self.preview_timeline.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))
        self.preview_timeline.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(self.preview_timeline, text="Linha do tempo", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 4))
        self.timeline_etapa1 = ctk.CTkLabel(self.preview_timeline, text="Pedido criado", corner_radius=10, padx=10, pady=6)
        self.timeline_etapa2 = ctk.CTkLabel(self.preview_timeline, text="Em produção", corner_radius=10, padx=10, pady=6)
        self.timeline_etapa3 = ctk.CTkLabel(self.preview_timeline, text="Pronto para envio", corner_radius=10, padx=10, pady=6)
        self.timeline_etapa1.grid(row=1, column=0, padx=6, pady=(0, 8), sticky="ew")
        self.timeline_etapa2.grid(row=1, column=1, padx=6, pady=(0, 8), sticky="ew")
        self.timeline_etapa3.grid(row=1, column=2, padx=6, pady=(0, 8), sticky="ew")

        self.preview_buttons_bar = ctk.CTkFrame(self.preview_body, fg_color="transparent")
        self.preview_buttons_bar.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        self.preview_buttons_bar.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.btn_preview_salvar = ctk.CTkButton(self.preview_buttons_bar, text="Salvar")
        self.btn_preview_excluir = ctk.CTkButton(self.preview_buttons_bar, text="Excluir")
        self.btn_preview_pdf = ctk.CTkButton(self.preview_buttons_bar, text="PDF")
        self.btn_preview_buscar = ctk.CTkButton(self.preview_buttons_bar, text="Buscar")
        self.btn_preview_cancelar = ctk.CTkButton(self.preview_buttons_bar, text="Cancelar")
        self.btn_preview_salvar.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        self.btn_preview_excluir.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        self.btn_preview_pdf.grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        self.btn_preview_buscar.grid(row=0, column=3, padx=4, pady=4, sticky="ew")
        self.btn_preview_cancelar.grid(row=0, column=4, padx=4, pady=4, sticky="ew")

        self.indicador_editando = ctk.CTkLabel(
            self.preview_body,
            text="Editando: —",
            text_color="#94a3b8",
        )
        self.indicador_editando.grid(row=7, column=0, columnspan=2, sticky="we", padx=10, pady=(0, 10))

        self.preview_targets = {
            "fundo": [self.preview_area],
            "primaria": [self.preview_header],
            "secundaria": [self.preview_body, self.preview_resumos],
            "terciaria": [self.preview_card, self.preview_form, self.preview_table, self.preview_resumo_ord],
            "borda": [self.preview_card, self.preview_body, self.preview_table, self.preview_form],
            "texto": [self.preview_title, self.preview_card_text, self.preview_alert_success, self.preview_alert_error, self.preview_resumo_est, self.preview_resumo_fin],
            "destaque": [self.preview_chip_1, self.preview_chip_2, self.preview_chip_3, self.preview_resumo_fin],
            "sucesso": [self.preview_alert_success, self.preview_badge_status, self.timeline_etapa3, self.preview_resumo_est],
            "alerta": [self.preview_alert_error, self.preview_badge_prioridade, self.preview_resumo_ord],
            "hover": [self.preview_area, self.timeline_etapa1],
            "botao_salvar": [self.preview_btn_secondary, self.btn_preview_salvar],
            "botao_novo": [self.preview_btn_primary],
            "botao_editar": [self.preview_row_action],
            "botao_excluir": [self.btn_preview_excluir],
            "botao_pdf": [self.btn_preview_pdf],
            "botao_buscar": [self.btn_preview_buscar],
            "botao_cancelar": [self.btn_preview_cancelar],
            "borda": [self.preview_table, self.preview_form, self.preview_card, self.preview_timeline],
            "texto": [self.preview_badge_cliente, self.timeline_etapa2],
        }

    # ==================== Dados ====================
    def _popular_lista_temas(self):
        for widget in self.lista_temas.winfo_children():
            widget.destroy()

        for nome in sorted(self.temas_padrao.keys()):
            self._criar_botao_tema(nome, "Padrão")
        for nome in sorted(self.temas_personalizados.keys()):
            self._criar_botao_tema(nome, "Personalizado")

        self._atualizar_box_personalizados()
        self.lbl_contagem_padrao.configure(text=f"Padrões: {len(self.temas_padrao)}")
        self.lbl_contagem_personalizado.configure(
            text=f"Personalizados: {len(self.temas_personalizados)}"
        )

    def _criar_botao_tema(self, nome: str, origem: str):
        paleta = self.temas_padrao.get(nome, self.temas_personalizados.get(nome, {}))
        cor_base = paleta.get("primaria", "#3b82f6")
        botao = ctk.CTkButton(
            self.lista_temas,
            text=f"{nome}\n({origem})",
            height=54,
            fg_color=cor_base,
            hover_color=ajustar_hover(cor_base),
            text_color=get_contraste_texto(cor_base),
            command=lambda n=nome: self._carregar_tema(n),
        )
        botao.pack(fill="x", padx=8, pady=4)
        botao.bind("<Double-Button-1>", lambda e, n=nome: self._aplicar_tema_imediato(n))

    def _atualizar_box_personalizados(self):
        conteudo = []
        if self.temas_personalizados:
            conteudo.append("Temas personalizados salvos:")
            for nome in sorted(self.temas_personalizados.keys()):
                conteudo.append(f"• {nome}")
        else:
            conteudo.append("Nenhum tema personalizado salvo ainda.")

        self.personalizados_box.configure(state="normal")
        self.personalizados_box.delete("1.0", tk.END)
        self.personalizados_box.insert("1.0", "\n".join(conteudo))
        self.personalizados_box.configure(state="disabled")

    # ==================== Manipulação ====================
    def _aplicar_tema_imediato(self, nome: str):
        self._carregar_tema(nome)
        self._aplicar_tema()

    def _carregar_tema(self, nome: str):
        paleta = self.temas_padrao.get(nome) or self.temas_personalizados.get(nome)
        if not paleta:
            return
        self.tema_selecionado.set(nome)
        self.nome_tema_entry.delete(0, tk.END)
        self.nome_tema_entry.insert(0, nome)
        self.observacao_entry.delete(0, tk.END)

        for campo in (
            [c[0] for c in self.BASE_COLORS]
            + [c[0] for c in self.FEEDBACK_COLORS]
            + [c[0] for c in self.BUTTON_COLORS]
        ):
            valor = paleta.get(campo, "")
            if campo not in self.campos_cor:
                continue
            self.campos_cor[campo].delete(0, tk.END)
            self.campos_cor[campo].insert(0, valor)
        self._auto_ajustar_auxiliares(forced_palette=paleta)
        self._atualizar_estilos_campos(paleta)
        self._atualizar_preview(paleta)
        self._mostrar_status(f"Tema '{nome}' carregado", sucesso=True)
        self._destacar_area("primaria")

    def _selecionar_cor(self, campo: str):
        cor_atual = self.campos_cor[campo].get() or "#ffffff"
        cor = colorchooser.askcolor(color=cor_atual)[1]
        if cor:
            self.campos_cor[campo].delete(0, tk.END)
            self.campos_cor[campo].insert(0, cor.upper())
            self._destacar_area(campo)
            self._atualizar_preview_from_entries()

    def _aplicar_tema(self):
        nome, paleta = self._obter_paleta_atual()
        if not paleta:
            self._mostrar_status("Defina todas as cores para aplicar o tema", sucesso=False)
            return

        usar_personalizado = nome in self.temas_personalizados or nome not in self.temas_padrao

        self._persistir_tema_aplicado(nome, paleta, usar_personalizado=usar_personalizado)

        if hasattr(self.app, "theme_manager"):
            try:
                self.app.theme_manager.apply_theme(nome, paleta)
            except Exception as exc:
                self._mostrar_status(f"Erro ao aplicar tema: {exc}", sucesso=False)
                return
        self._sincronizar_paginas()
        self._mostrar_status(f"Tema '{nome}' aplicado e salvo como preferido", sucesso=True)

    def _salvar_personalizado(self):
        nome = self.nome_tema_entry.get().strip() or self.tema_selecionado.get()
        nome = nome or "Tema personalizado"
        _, paleta = self._obter_paleta_atual()
        if not paleta:
            self._mostrar_status("Defina todas as cores para salvar.", sucesso=False)
            return

        self.temas_personalizados[nome] = paleta
        self.settings["custom_themes"] = self.temas_personalizados
        self.settings["tema_atual_paleta"] = paleta
        self.settings["usar_tema_personalizado"] = True
        self._persistir_tema_aplicado(nome, paleta, usar_personalizado=True)
        try:
            if self.sync_db.get() and self.db_manager:
                user_id = _get_user_id(self.app)
                self.db_manager.salvar_tema_personalizado(nome, paleta, user_id=user_id)
        except Exception as exc:
            self._mostrar_status(f"Tema salvo localmente. Banco indisponível: {exc}", sucesso=False)

        self._popular_lista_temas()
        self._mostrar_status(f"Tema personalizado '{nome}' salvo!", sucesso=True)
        self._destacar_area("primaria")

    def _persistir_tema_aplicado(
        self, nome: str, paleta: Dict[str, str], usar_personalizado: Optional[bool] = None
    ):
        """Atualiza settings locais e registra o tema como preferido no banco."""
        self.settings["theme"] = nome
        self.settings["custom_themes"] = self.temas_personalizados
        self.settings["aplicar_dashboard"] = self.aplicar_dashboard.get()
        self.settings["aplicar_tabelas"] = self.aplicar_tabelas.get()
        self.settings["aplicar_login"] = self.aplicar_login.get()
        self.settings["tema_atual_paleta"] = paleta

        if usar_personalizado is None:
            usar_personalizado = nome not in self.temas_padrao or nome in self.temas_personalizados
        self.settings["usar_tema_personalizado"] = usar_personalizado

        salvar_settings(self.settings, self.app if self.sync_db.get() else None)

        try:
            if self.app:
                # Integrações nativas do sistema de usuários
                um = getattr(self.app, "user_manager", None)
                user_id = _get_user_id(self.app)

                if um and hasattr(um, "save_user_theme_personalizado"):
                    tema_json = json.dumps(self.settings.get("custom_themes", {}))
                    um.save_user_theme_personalizado(nome, tema_json)
                    um.save_user_theme(nome)
                elif user_id and self.db_manager:
                    self.db_manager.registrar_tema_atual(
                        nome,
                        paleta,
                        usar_personalizado,
                        self.settings,
                        user_id=user_id,
                    )
        except Exception as exc:
            self._mostrar_status(
                f"⚠️ Preferências locais salvas. Banco indisponível: {exc}", sucesso=False
            )

    def _sincronizar_paginas(self):
        """Ajusta páginas conectadas (dashboard, tabelas, login) para refletir o novo tema."""
        if not self.app:
            return

        feedbacks = []

        if self.aplicar_dashboard.get():
            dash = getattr(self.app, "dashboard_page", None)
            if dash and hasattr(dash, "atualizar_dashboard"):
                try:
                    dash.atualizar_dashboard()
                except Exception as exc:
                    feedbacks.append(f"Dashboard: {exc}")

        if self.aplicar_tabelas.get():
            refresh = getattr(self.app, "atualizar_estilos_listas", None)
            if callable(refresh):
                try:
                    refresh()
                except Exception as exc:
                    feedbacks.append(f"Listas: {exc}")

        if self.aplicar_login.get():
            login_refresh = getattr(self.app, "recarregar_tema_login", None)
            if callable(login_refresh):
                try:
                    login_refresh()
                except Exception as exc:
                    feedbacks.append(f"Login: {exc}")

        if feedbacks:
            self._mostrar_status("; ".join(feedbacks), sucesso=False)

    def _excluir_personalizado(self):
        nome = self.tema_selecionado.get()
        if nome in self.temas_personalizados:
            del self.temas_personalizados[nome]
            self.settings["custom_themes"] = self.temas_personalizados
            salvar_settings(self.settings, self.app if self.sync_db.get() else None)
            self._popular_lista_temas()
            self._carregar_tema("Noite Urbana")
            self._mostrar_status(f"Tema '{nome}' removido.", sucesso=True)
            self._destacar_area("primaria")
        else:
            self._mostrar_status("Apenas temas personalizados podem ser excluídos.", sucesso=False)

    def _auto_ajustar_auxiliares(self, forced_palette: Optional[Dict[str, str]] = None):
        """Preenche hover/contraste com base na primária e aplica pré-visualização."""
        paleta = forced_palette or {}
        prim = paleta.get("primaria") or self.campos_cor.get("primaria", tk.Entry()).get()
        if prim:
            paleta.setdefault("hover", ajustar_hover(prim))
            paleta.setdefault("selecao", ajustar_hover(prim, 1.2))
        for campo, entry in self.campos_cor.items():
            if not entry.get() and campo in paleta:
                entry.insert(0, paleta[campo])
        if paleta:
            self._atualizar_estilos_campos(paleta)
        self._atualizar_preview_from_entries()

    def _nome_campo(self, chave: str) -> str:
        for grupo in (self.BASE_COLORS + self.FEEDBACK_COLORS + self.BUTTON_COLORS):
            if grupo[0] == chave:
                return grupo[1]
        return chave

    def _configurar_se_suportado(self, widget: Any, **kwargs):
        for chave, valor in kwargs.items():
            try:
                widget.configure(**{chave: valor})
            except Exception:
                continue

    def _destacar_area(self, campo: str):
        self.campo_em_edicao.set(campo)
        self.indicador_editando.configure(text=f"Editando: {self._nome_campo(campo)}")
        paleta = getattr(self, "current_paleta", {}) or {}
        destaque = paleta.get("destaque", "#a855f7")
        borda_padrao = paleta.get("borda", "#334155")

        for ind in getattr(self, "indicadores", {}).values():
            cor_indicador = self.indicador_cores.get(
                getattr(ind, "_tema_campo", ""), ind.cget("fg_color")
            )
            self._configurar_se_suportado(ind, fg_color=cor_indicador)
        if campo in getattr(self, "indicadores", {}):
            base_cor = self.indicador_cores.get(campo, destaque)
            self._configurar_se_suportado(
                self.indicadores[campo], fg_color=ajustar_hover(base_cor, 1.08)
            )

        for widgets in getattr(self, "preview_targets", {}).values():
            for widget in widgets:
                self._configurar_se_suportado(
                    widget, border_width=1, border_color=borda_padrao
                )

        for widget in self.preview_targets.get(campo, []):
            self._configurar_se_suportado(widget, border_width=3, border_color=destaque)

    def _obter_paleta_atual(self) -> Tuple[str, Optional[Dict[str, str]]]:
        nome = self.nome_tema_entry.get().strip() or self.tema_selecionado.get()
        paleta: Dict[str, str] = {}
        campos = [c[0] for c in self.BASE_COLORS] + [c[0] for c in self.FEEDBACK_COLORS] + [c[0] for c in self.BUTTON_COLORS]
        for campo in campos:
            valor = self.campos_cor[campo].get().strip()
            if not valor or not valor.startswith("#") or len(valor) != 7:
                return nome, None
            paleta[campo] = valor.upper()

        paleta.setdefault("modo", "dark" if is_dark_color(paleta.get("fundo", "#000000")) else "light")
        paleta.setdefault("texto_botao", get_contraste_texto(paleta.get("primaria", "#3b82f6")))
        return nome, paleta

    def _atualizar_estilos_campos(self, paleta: Dict[str, str]):
        """Pinta entradas e indicadores com a paleta carregada para visualização imediata."""
        for campo, entry in self.campos_cor.items():
            cor = paleta.get(campo) or entry.get()
            if not cor or not cor.startswith("#") or len(cor) != 7:
                continue
            contraste = get_contraste_texto(cor)
            self._configurar_se_suportado(
                entry,
                fg_color=cor,
                text_color=contraste,
                placeholder_text_color=contraste,
                border_color=paleta.get("borda", "#334155"),
            )
            if campo in getattr(self, "indicadores", {}):
                self.indicador_cores[campo] = cor
                self.indicadores[campo]._tema_campo = campo

    def _atualizar_preview_from_entries(self):
        _, paleta = self._obter_paleta_atual()
        if paleta:
            self._atualizar_preview(paleta)

    def _atualizar_preview(self, paleta: Dict[str, str]):
        fundo = paleta.get("fundo", "#0f172a")
        texto = paleta.get("texto", "#e2e8f0")
        primaria = paleta.get("primaria", "#1d4ed8")
        secundaria = paleta.get("secundaria", "#1e293b")
        hover = paleta.get("hover", ajustar_hover(primaria))
        destaque = paleta.get("destaque", "#8b5cf6")

        self.current_paleta = paleta
        self._atualizar_estilos_campos(paleta)
        self.preview_area.configure(fg_color=fundo)
        self.preview_header.configure(fg_color=primaria)
        self.preview_title.configure(text_color=get_contraste_texto(primaria))
        self.preview_actions.configure(fg_color=primaria)
        self.preview_filters.configure(fg_color=paleta.get("terciaria", secundaria))
        for chip in [self.preview_chip_1, self.preview_chip_2, self.preview_chip_3]:
            chip.configure(
                fg_color=destaque,
                text_color=get_contraste_texto(destaque),
                corner_radius=12,
                padx=10,
                pady=8,
            )

        self.preview_resumos.configure(fg_color=paleta.get("secundaria", secundaria))
        self.preview_resumo_est.configure(
            fg_color=paleta.get("sucesso", "#10b981"),
            text_color=get_contraste_texto(paleta.get("sucesso", "#10b981")),
        )
        self.preview_resumo_ord.configure(
            fg_color=paleta.get("alerta", "#ef4444"),
            text_color=get_contraste_texto(paleta.get("alerta", "#ef4444")),
        )
        self.preview_resumo_fin.configure(
            fg_color=destaque,
            text_color=get_contraste_texto(destaque),
        )

        self.preview_btn_primary.configure(
            fg_color=paleta.get("botao_novo", primaria),
            hover_color=ajustar_hover(paleta.get("botao_novo", primaria)),
            text_color=get_contraste_texto(paleta.get("botao_novo", primaria)),
            border_color=paleta.get("borda", "#334155"),
        )
        self.preview_btn_secondary.configure(
            fg_color=paleta.get("botao_salvar", secundaria),
            hover_color=ajustar_hover(paleta.get("botao_salvar", secundaria)),
            text_color=get_contraste_texto(paleta.get("botao_salvar", secundaria)),
            border_color=paleta.get("borda", "#334155"),
        )

        self.preview_body.configure(fg_color=secundaria)
        self.preview_card.configure(fg_color=paleta.get("terciaria", secundaria))
        self.preview_card_text.configure(text_color=texto)
        self.preview_form.configure(fg_color=paleta.get("terciaria", secundaria))
        self.preview_table.configure(fg_color=paleta.get("terciaria", secundaria))
        self.preview_badge_status.configure(
            fg_color=paleta.get("sucesso", "#10b981"),
            text_color=get_contraste_texto(paleta.get("sucesso", "#10b981")),
        )
        self.preview_badge_cliente.configure(
            fg_color=destaque,
            text_color=get_contraste_texto(destaque),
        )
        self.preview_badge_prioridade.configure(
            fg_color=paleta.get("alerta", "#ef4444"),
            text_color=get_contraste_texto(paleta.get("alerta", "#ef4444")),
        )
        self.preview_progress.configure(
            progress_color=paleta.get("sucesso", "#10b981"),
            fg_color=paleta.get("hover", ajustar_hover(primaria)),
        )

        try:
            heading_text = get_contraste_texto(primaria)
            body_text = get_contraste_texto(paleta.get("terciaria", secundaria))
            self.tree_style.configure(
                self.tree_style_name,
                background=paleta.get("terciaria", secundaria),
                fieldbackground=paleta.get("terciaria", secundaria),
                foreground=body_text,
                bordercolor=paleta.get("borda", "#334155"),
            )
            self.tree_style.configure(
                f"{self.tree_style_name}.Heading",
                background=primaria,
                foreground=heading_text,
                bordercolor=paleta.get("borda", "#334155"),
                font=("Arial", 11, "bold"),
            )
        except Exception:
            pass

        for header in self.preview_table_headers:
            header.configure(text_color=texto)
        for entry in [self.preview_input_1, self.preview_input_2]:
            entry.configure(
                fg_color=paleta.get("fundo", fundo),
                border_color=paleta.get("borda", "#334155"),
                text_color=texto,
            )
        self.preview_row_status.configure(
            fg_color=paleta.get("sucesso", "#10b981"),
            text_color=get_contraste_texto(paleta.get("sucesso", "#10b981")),
            corner_radius=6,
            padx=8,
            pady=4,
        )
        self.preview_row_action.configure(
            fg_color=paleta.get("botao_editar", "#06b6d4"),
            hover_color=ajustar_hover(paleta.get("botao_editar", "#06b6d4")),
            text_color=get_contraste_texto(paleta.get("botao_editar", "#06b6d4")),
            border_color=paleta.get("borda", "#334155"),
        )
        self.btn_preview_salvar.configure(
            fg_color=paleta.get("botao_salvar", "#10b981"),
            hover_color=ajustar_hover(paleta.get("botao_salvar", "#10b981")),
            text_color=get_contraste_texto(paleta.get("botao_salvar", "#10b981")),
        )
        self.btn_preview_excluir.configure(
            fg_color=paleta.get("botao_excluir", "#ef4444"),
            hover_color=ajustar_hover(paleta.get("botao_excluir", "#ef4444")),
            text_color=get_contraste_texto(paleta.get("botao_excluir", "#ef4444")),
        )
        self.btn_preview_pdf.configure(
            fg_color=paleta.get("botao_pdf", "#f59e0b"),
            hover_color=ajustar_hover(paleta.get("botao_pdf", "#f59e0b")),
            text_color=get_contraste_texto(paleta.get("botao_pdf", "#f59e0b")),
        )
        self.btn_preview_buscar.configure(
            fg_color=paleta.get("botao_buscar", "#3b82f6"),
            hover_color=ajustar_hover(paleta.get("botao_buscar", "#3b82f6")),
            text_color=get_contraste_texto(paleta.get("botao_buscar", "#3b82f6")),
        )
        self.btn_preview_cancelar.configure(
            fg_color=paleta.get("botao_cancelar", "#6b7280"),
            hover_color=ajustar_hover(paleta.get("botao_cancelar", "#6b7280")),
            text_color=get_contraste_texto(paleta.get("botao_cancelar", "#6b7280")),
        )

        self.preview_alert_success.configure(
            fg_color=paleta.get("sucesso", "#10b981"),
            text_color=get_contraste_texto(paleta.get("sucesso", "#10b981")),
        )
        self.preview_alert_error.configure(
            fg_color=paleta.get("alerta", "#ef4444"),
            text_color=get_contraste_texto(paleta.get("alerta", "#ef4444")),
        )
        self.timeline_etapa1.configure(
            fg_color=paleta.get("borda", "#334155"),
            text_color=get_contraste_texto(paleta.get("borda", "#334155")),
        )
        self.timeline_etapa2.configure(
            fg_color=paleta.get("destaque", "#8b5cf6"),
            text_color=get_contraste_texto(paleta.get("destaque", "#8b5cf6")),
        )
        self.timeline_etapa3.configure(
            fg_color=paleta.get("sucesso", "#10b981"),
            text_color=get_contraste_texto(paleta.get("sucesso", "#10b981")),
        )

        for frame in [
            self.preview_card,
            self.preview_body,
            self.preview_header,
            self.preview_filters,
            self.preview_form,
            self.preview_table,
        ]:
            frame.configure(border_color=paleta.get("borda", "#334155"), border_width=1)

        self.preview_area.configure(border_color=hover, border_width=2)

        if self.campo_em_edicao.get():
            self._destacar_area(self.campo_em_edicao.get())

    def _mostrar_status(self, msg: str, sucesso: bool = True):
        self.status_var.set(msg)
        self.lbl_status.configure(text_color="#16a34a" if sucesso else "#ef4444")


# Compatibilidade com chamadas existentes que esperam TemasPage
TemasPage = Tema2Page

if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Configuração de tema (TEMA2)")
    app.geometry("1200x760")
    page = Tema2Page(app)
    page.pack(fill="both", expand=True)
    app.mainloop()