import copy
import json
import math
import re
import tkinter as tk
from tkinter import Canvas
import colorsys
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from PIL import Image, ImageTk, ImageGrab

# =================== PALETAS PADRÃO E CAMPOS ===================
DEFAULT_PADROES = {
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

CAMPOS_PADRAO = [
    "primaria", "secundaria", "terciaria", "fundo", "texto", "destaque",
    "sucesso", "alerta", "borda", "hover", "selecao",
    "botao_salvar", "botao_excluir", "botao_novo", "botao_imprimir",
    "botao_pdf", "botao_editar", "botao_visualizar", "botao_confirmar",
    "botao_cancelar", "botao_exportar", "botao_importar", "botao_configurar",
    "botao_ajuda", "botao_filtrar", "botao_limpar", "botao_voltar", "botao_avancar",
    "botao_adiantamento", "botao_comprovante", "botao_buscar", "botao_export_csv", "botao_export_pdf"
]

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

# Importa o gerenciador de preferências
try:
    from settings_manager import save_settings, load_settings
except ImportError:
    def save_settings(settings):
        print("⚠️ settings_manager não encontrado, preferências não serão salvas")
        return False


    def load_settings():
        return {"theme": "Noite Urbana", "custom_themes": {}, "excluded_default_themes": []}


# =================== FUNÇÕES UTILITÁRIAS DE COR ===================

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


HEX_RE = re.compile(r"^#([0-9a-fA-F]{6})$")


def _valida_hex(s):
    return bool(HEX_RE.match(s or ""))


# =================== CLASSE PARA BOTÕES PADRONIZADOS ===================

class BotaoPadronizado:
    @staticmethod
    def criar_botao(master, texto, tipo="padrao", **kwargs):
        config_padrao = {
            "height": 32,
            "font": ("Arial", 12, "bold"),
            "corner_radius": 8,
            "border_width": 1
        }

        try:
            app = master.winfo_toplevel()
            cores = BotaoPadronizado._obter_cores_tema(app)
        except:
            cores = BotaoPadronizado._obter_cores_fallback()

        config_tipo = {
            "padrao": {
                "fg_color": cores["secundaria"],
                "hover_color": cores["hover"],
                "text_color": cores["texto"],
                "border_color": cores["borda"]
            },
            "salvar": {
                "fg_color": cores.get("botao_salvar", "#10b981"),
                "hover_color": ajustar_hover(cores.get("botao_salvar", "#10b981")),
                "text_color": get_contraste_texto(cores.get("botao_salvar", "#10b981")),
                "border_color": ajustar_hover(cores.get("botao_salvar", "#10b981"), 0.7)
            },
            "excluir": {
                "fg_color": cores.get("botao_excluir", "#ef4444"),
                "hover_color": ajustar_hover(cores.get("botao_excluir", "#ef4444")),
                "text_color": get_contraste_texto(cores.get("botao_excluir", "#ef4444")),
                "border_color": ajustar_hover(cores.get("botao_excluir", "#ef4444"), 0.7)
            },
            "novo": {
                "fg_color": cores.get("botao_novo", "#3b82f6"),
                "hover_color": ajustar_hover(cores.get("botao_novo", "#3b82f6")),
                "text_color": get_contraste_texto(cores.get("botao_novo", "#3b82f6")),
                "border_color": ajustar_hover(cores.get("botao_novo", "#3b82f6"), 0.7)
            },
            "imprimir": {
                "fg_color": cores.get("botao_imprimir", "#8b5cf6"),
                "hover_color": ajustar_hover(cores.get("botao_imprimir", "#8b5cf6")),
                "text_color": get_contraste_texto(cores.get("botao_imprimir", "#8b5cf6")),
                "border_color": ajustar_hover(cores.get("botao_imprimir", "#8b5cf6"), 0.7)
            },
            "pdf": {
                "fg_color": cores.get("botao_pdf", "#f59e0b"),
                "hover_color": ajustar_hover(cores.get("botao_pdf", "#f59e0b")),
                "text_color": get_contraste_texto(cores.get("botao_pdf", "#f59e0b")),
                "border_color": ajustar_hover(cores.get("botao_pdf", "#f59e0b"), 0.7)
            },
            "editar": {
                "fg_color": cores.get("botao_editar", "#06b6d4"),
                "hover_color": ajustar_hover(cores.get("botao_editar", "#06b6d4")),
                "text_color": get_contraste_texto(cores.get("botao_editar", "#06b6d4")),
                "border_color": ajustar_hover(cores.get("botao_editar", "#06b6d4"), 0.7)
            },
            "visualizar": {
                "fg_color": cores.get("botao_visualizar", "#6366f1"),
                "hover_color": ajustar_hover(cores.get("botao_visualizar", "#6366f1")),
                "text_color": get_contraste_texto(cores.get("botao_visualizar", "#6366f1")),
                "border_color": ajustar_hover(cores.get("botao_visualizar", "#6366f1"), 0.7)
            },
            "confirmar": {
                "fg_color": cores.get("botao_confirmar", "#22c55e"),
                "hover_color": ajustar_hover(cores.get("botao_confirmar", "#22c55e")),
                "text_color": get_contraste_texto(cores.get("botao_confirmar", "#22c55e")),
                "border_color": ajustar_hover(cores.get("botao_confirmar", "#22c55e"), 0.7)
            },
            "cancelar": {
                "fg_color": cores.get("botao_cancelar", "#6b7280"),
                "hover_color": ajustar_hover(cores.get("botao_cancelar", "#6b7280")),
                "text_color": get_contraste_texto(cores.get("botao_cancelar", "#6b7280")),
                "border_color": ajustar_hover(cores.get("botao_cancelar", "#6b7280"), 0.7)
            },
            "exportar": {
                "fg_color": cores.get("botao_exportar", "#8B5CF6"),
                "hover_color": ajustar_hover(cores.get("botao_exportar", "#8B5CF6")),
                "text_color": get_contraste_texto(cores.get("botao_exportar", "#8B5CF6")),
                "border_color": ajustar_hover(cores.get("botao_exportar", "#8B5CF6"), 0.7)
            },
            "importar": {
                "fg_color": cores.get("botao_importar", "#06B6D4"),
                "hover_color": ajustar_hover(cores.get("botao_importar", "#06B6D4")),
                "text_color": get_contraste_texto(cores.get("botao_importar", "#06B6D4")),
                "border_color": ajustar_hover(cores.get("botao_importar", "#06B6D4"), 0.7)
            },
            "configurar": {
                "fg_color": cores.get("botao_configurar", "#6B7280"),
                "hover_color": ajustar_hover(cores.get("botao_configurar", "#6B7280")),
                "text_color": get_contraste_texto(cores.get("botao_configurar", "#6B7280")),
                "border_color": ajustar_hover(cores.get("botao_configurar", "#6B7280"), 0.7)
            },
            "ajuda": {
                "fg_color": cores.get("botao_ajuda", "#3B82F6"),
                "hover_color": ajustar_hover(cores.get("botao_ajuda", "#3B82F6")),
                "text_color": get_contraste_texto(cores.get("botao_ajuda", "#3B82F6")),
                "border_color": ajustar_hover(cores.get("botao_ajuda", "#3B82F6"), 0.7)
            },
            "filtrar": {
                "fg_color": cores.get("botao_filtrar", "#6366F1"),
                "hover_color": ajustar_hover(cores.get("botao_filtrar", "#6366F1")),
                "text_color": get_contraste_texto(cores.get("botao_filtrar", "#6366F1")),
                "border_color": ajustar_hover(cores.get("botao_filtrar", "#6366F1"), 0.7)
            },
            "limpar": {
                "fg_color": cores.get("botao_limpar", "#F59E0B"),
                "hover_color": ajustar_hover(cores.get("botao_limpar", "#F59E0B")),
                "text_color": get_contraste_texto(cores.get("botao_limpar", "#F59E0B")),
                "border_color": ajustar_hover(cores.get("botao_limpar", "#F59E0B"), 0.7)
            },
            "voltar": {
                "fg_color": cores.get("botao_voltar", "#6B7280"),
                "hover_color": ajustar_hover(cores.get("botao_voltar", "#6B7280")),
                "text_color": get_contraste_texto(cores.get("botao_voltar", "#6B7280")),
                "border_color": ajustar_hover(cores.get("botao_voltar", "#6B7280"), 0.7)
            },
            "avancar": {
                "fg_color": cores.get("botao_avancar", "#10B981"),
                "hover_color": ajustar_hover(cores.get("botao_avancar", "#10B981")),
                "text_color": get_contraste_texto(cores.get("botao_avancar", "#10B981")),
                "border_color": ajustar_hover(cores.get("botao_avancar", "#10B981"), 0.7)
            },
            "adiantamento": {
                "fg_color": cores.get("botao_adiantamento", "#10B981"),
                "hover_color": ajustar_hover(cores.get("botao_adiantamento", "#10B981")),
                "text_color": get_contraste_texto(cores.get("botao_adiantamento", "#10B981")),
                "border_color": ajustar_hover(cores.get("botao_adiantamento", "#10B981"), 0.7)
            },
            "comprovante": {
                "fg_color": cores.get("botao_comprovante", "#8B5CF6"),
                "hover_color": ajustar_hover(cores.get("botao_comprovante", "#8B5CF6")),
                "text_color": get_contraste_texto(cores.get("botao_comprovante", "#8B5CF6")),
                "border_color": ajustar_hover(cores.get("botao_comprovante", "#8B5CF6"), 0.7)
            },
            "buscar": {
                "fg_color": cores.get("botao_buscar", "#3B82F6"),
                "hover_color": ajustar_hover(cores.get("botao_buscar", "#3B82F6")),
                "text_color": get_contraste_texto(cores.get("botao_buscar", "#3B82F6")),
                "border_color": ajustar_hover(cores.get("botao_buscar", "#3B82F6"), 0.7)
            },
            "export_csv": {
                "fg_color": cores.get("botao_export_csv", "#06B6D4"),
                "hover_color": ajustar_hover(cores.get("botao_export_csv", "#06B6D4")),
                "text_color": get_contraste_texto(cores.get("botao_export_csv", "#06B6D4")),
                "border_color": ajustar_hover(cores.get("botao_export_csv", "#06B6D4"), 0.7)
            },
            "export_pdf": {
                "fg_color": cores.get("botao_export_pdf", "#F59E0B"),
                "hover_color": ajustar_hover(cores.get("botao_export_pdf", "#F59E0B")),
                "text_color": get_contraste_texto(cores.get("botao_export_pdf", "#F59E0B")),
                "border_color": ajustar_hover(cores.get("botao_export_pdf", "#F59E0B"), 0.7)
            }
        }

        config_final = {**config_padrao, **config_tipo.get(tipo, config_tipo["padrao"]), **kwargs}
        return ctk.CTkButton(master, text=texto, **config_final)

    @staticmethod
    def _obter_cores_tema(app):
        cores = {}
        atributos_cores = [
            "primaria", "secundaria", "terciaria", "fundo", "texto",
            "destaque", "sucesso", "alerta", "borda", "hover", "selecao",
            "botao_salvar", "botao_excluir", "botao_novo", "botao_imprimir",
            "botao_pdf", "botao_editar", "botao_visualizar", "botao_confirmar",
            "botao_cancelar", "botao_exportar", "botao_importar", "botao_configurar",
            "botao_ajuda", "botao_filtrar", "botao_limpar", "botao_voltar", "botao_avancar",
            "botao_adiantamento", "botao_comprovante", "botao_buscar", "botao_export_csv", "botao_export_pdf"
        ]

        for attr in atributos_cores:
            try:
                valor = getattr(app, f'cor_{attr}', None)
                if valor:
                    cores[attr] = valor
            except:
                continue

        return cores

    @staticmethod
    def _obter_cores_fallback():
        return {
            "secundaria": "#2C2C2C",
            "hover": "#3A3A3A",
            "texto": "#FFFFFF",
            "borda": "#333333",
            "botao_salvar": "#10b981",
            "botao_excluir": "#ef4444",
            "botao_novo": "#3b82f6",
            "botao_imprimir": "#8b5cf6",
            "botao_pdf": "#f59e0b",
            "botao_editar": "#06b6d4",
            "botao_visualizar": "#6366f1",
            "botao_confirmar": "#22c55e",
            "botao_cancelar": "#6b7280",
            "botao_exportar": "#8B5CF6",
            "botao_importar": "#06B6D4",
            "botao_configurar": "#6B7280",
            "botao_ajuda": "#3B82F6",
            "botao_filtrar": "#6366F1",
            "botao_limpar": "#F59E0B",
            "botao_voltar": "#6B7280",
            "botao_avancar": "#10B981",
            "botao_adiantamento": "#10B981",
            "botao_comprovante": "#8B5CF6",
            "botao_buscar": "#3B82F6",
            "botao_export_csv": "#06B6D4",
            "botao_export_pdf": "#F59E0B"
        }


# =================== PAINEL DE PREVIEW ===================

class PreviewPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.highlighted_element = None
        self.original_border_widths = {}
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

        self.sample_entry = ctk.CTkEntry(self.preview_container, placeholder_text="Campo de entrada",
                                         font=("Arial", 11))
        self.sample_entry.pack(pady=5, padx=10, fill="x")

        self.tertiary_frame = ctk.CTkFrame(self.preview_container, corner_radius=6, border_width=2)
        self.tertiary_frame.pack(pady=10, padx=10, fill="x")

        self.tertiary_label = ctk.CTkLabel(self.tertiary_frame, text="Frame Terciário", font=("Arial", 10))
        self.tertiary_label.pack(pady=8)

        self.border_frame = ctk.CTkFrame(self.preview_container, corner_radius=6, border_width=3)
        self.border_frame.pack(pady=5, padx=10, fill="x")

        self.border_label = ctk.CTkLabel(self.border_frame, text="Exemplo de Borda", font=("Arial", 9))
        self.border_label.pack(pady=6)

        btn_frame = ctk.CTkFrame(self.preview_container, fg_color="transparent")
        btn_frame.pack(pady=5, padx=10, fill="x")

        self.success_btn = ctk.CTkButton(btn_frame, text="Sucesso", width=80, height=28, font=("Arial", 10))
        self.success_btn.pack(side="left", padx=5)

        self.alert_btn = ctk.CTkButton(btn_frame, text="Alerta", width=80, height=28, font=("Arial", 10))
        self.alert_btn.pack(side="left", padx=5)

        self.highlight_btn = ctk.CTkButton(btn_frame, text="Destaque", width=80, height=28, font=("Arial", 10))
        self.highlight_btn.pack(side="left", padx=5)

        self.hover_demo_btn = ctk.CTkButton(self.preview_container, text="Passe o mouse aqui (Hover)",
                                            font=("Arial", 10), height=32)
        self.hover_demo_btn.pack(pady=5, padx=10, fill="x")

        self.selecao_demo_btn = ctk.CTkButton(self.preview_container, text="Item Selecionado/Ativo",
                                              font=("Arial", 10, "bold"), height=32)
        self.selecao_demo_btn.pack(pady=5, padx=10, fill="x")

        # Botões de referência
        botoes_referencia_frame = ctk.CTkFrame(self.preview_container, fg_color="transparent")
        botoes_referencia_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(botoes_referencia_frame, text="Botões de Referência:", font=("Arial", 12, "bold")).pack(anchor="w",
                                                                                                             pady=(
                                                                                                                 0, 8))

        botoes_grid = ctk.CTkFrame(botoes_referencia_frame, fg_color="transparent")
        botoes_grid.pack(fill="x")

        # Primeira linha
        linha1 = ctk.CTkFrame(botoes_grid, fg_color="transparent")
        linha1.pack(fill="x", pady=2)

        self.botao_salvar_ref = ctk.CTkButton(linha1, text="Salvar", width=80, height=28)
        self.botao_salvar_ref.pack(side="left", padx=2)

        self.botao_excluir_ref = ctk.CTkButton(linha1, text="Excluir", width=80, height=28)
        self.botao_excluir_ref.pack(side="left", padx=2)

        self.botao_novo_ref = ctk.CTkButton(linha1, text="Novo", width=80, height=28)
        self.botao_novo_ref.pack(side="left", padx=2)

        self.botao_imprimir_ref = ctk.CTkButton(linha1, text="Imprimir", width=80, height=28)
        self.botao_imprimir_ref.pack(side="left", padx=2)

        # Segunda linha
        linha2 = ctk.CTkFrame(botoes_grid, fg_color="transparent")
        linha2.pack(fill="x", pady=2)

        self.botao_pdf_ref = ctk.CTkButton(linha2, text="PDF", width=80, height=28)
        self.botao_pdf_ref.pack(side="left", padx=2)

        self.botao_editar_ref = ctk.CTkButton(linha2, text="Editar", width=80, height=28)
        self.botao_editar_ref.pack(side="left", padx=2)

        self.botao_visualizar_ref = ctk.CTkButton(linha2, text="Visualizar", width=80, height=28)
        self.botao_visualizar_ref.pack(side="left", padx=2)

        self.botao_confirmar_ref = ctk.CTkButton(linha2, text="Confirmar", width=80, height=28)
        self.botao_confirmar_ref.pack(side="left", padx=2)

        # Terceira linha
        linha3 = ctk.CTkFrame(botoes_grid, fg_color="transparent")
        linha3.pack(fill="x", pady=2)

        self.botao_cancelar_ref = ctk.CTkButton(linha3, text="Cancelar", width=80, height=28)
        self.botao_cancelar_ref.pack(side="left", padx=2)

        self.botao_exportar_ref = ctk.CTkButton(linha3, text="Exportar", width=80, height=28)
        self.botao_exportar_ref.pack(side="left", padx=2)

        self.botao_importar_ref = ctk.CTkButton(linha3, text="Importar", width=80, height=28)
        self.botao_importar_ref.pack(side="left", padx=2)

        self.botao_configurar_ref = ctk.CTkButton(linha3, text="Configurar", width=80, height=28)
        self.botao_configurar_ref.pack(side="left", padx=2)

        # Quarta linha
        linha4 = ctk.CTkFrame(botoes_grid, fg_color="transparent")
        linha4.pack(fill="x", pady=2)

        self.botao_ajuda_ref = ctk.CTkButton(linha4, text="Ajuda", width=80, height=28)
        self.botao_ajuda_ref.pack(side="left", padx=2)

        self.botao_filtrar_ref = ctk.CTkButton(linha4, text="Filtrar", width=80, height=28)
        self.botao_filtrar_ref.pack(side="left", padx=2)

        self.botao_limpar_ref = ctk.CTkButton(linha4, text="Limpar", width=80, height=28)
        self.botao_limpar_ref.pack(side="left", padx=2)

        self.botao_voltar_ref = ctk.CTkButton(linha4, text="Voltar", width=80, height=28)
        self.botao_voltar_ref.pack(side="left", padx=2)

        # Quinta linha (novos botões - ADIANTAMENTOS)
        linha5 = ctk.CTkFrame(botoes_grid, fg_color="transparent")
        linha5.pack(fill="x", pady=2)

        self.botao_avancar_ref = ctk.CTkButton(linha5, text="Avançar", width=80, height=28)
        self.botao_avancar_ref.pack(side="left", padx=2)

        self.botao_adiantamento_ref = ctk.CTkButton(linha5, text="Adiantamento", width=80, height=28)
        self.botao_adiantamento_ref.pack(side="left", padx=2)

        self.botao_comprovante_ref = ctk.CTkButton(linha5, text="Comprovante", width=80, height=28)
        self.botao_comprovante_ref.pack(side="left", padx=2)

        self.botao_buscar_ref = ctk.CTkButton(linha5, text="Buscar", width=80, height=28)
        self.botao_buscar_ref.pack(side="left", padx=2)

        # Sexta linha (novos botões - EXPORTAÇÃO)
        linha6 = ctk.CTkFrame(botoes_grid, fg_color="transparent")
        linha6.pack(fill="x", pady=2)

        self.botao_export_csv_ref = ctk.CTkButton(linha6, text="Export CSV", width=80, height=28)
        self.botao_export_csv_ref.pack(side="left", padx=2)

        self.botao_export_pdf_ref = ctk.CTkButton(linha6, text="Export PDF", width=80, height=28)
        self.botao_export_pdf_ref.pack(side="left", padx=2)

    def update_preview(self, colors):
        try:
            primaria = colors.get("primaria", "#1F1F1F")
            secundaria = colors.get("secundaria", "#2C2C2C")
            terciaria = colors.get("terciaria", "#3A3A3A")
            fundo = colors.get("fundo", "#181818")
            texto = colors.get("texto", "#EEEEEE")
            destaque = colors.get("destaque", "#3A86FF")
            sucesso = colors.get("sucesso", "#3BCF8E")
            alerta = colors.get("alerta", "#EF476F")
            borda = colors.get("borda", "#333333")
            hover = colors.get("hover", "#2C2C2C")
            selecao = colors.get("selecao", destaque)

            # Novas cores de botões
            botao_salvar = colors.get("botao_salvar", "#10b981")
            botao_excluir = colors.get("botao_excluir", "#ef4444")
            botao_novo = colors.get("botao_novo", "#3b82f6")
            botao_imprimir = colors.get("botao_imprimir", "#8b5cf6")
            botao_pdf = colors.get("botao_pdf", "#f59e0b")
            botao_editar = colors.get("botao_editar", "#06b6d4")
            botao_visualizar = colors.get("botao_visualizar", "#6366f1")
            botao_confirmar = colors.get("botao_confirmar", "#22c55e")
            botao_cancelar = colors.get("botao_cancelar", "#6b7280")
            botao_exportar = colors.get("botao_exportar", "#8B5CF6")
            botao_importar = colors.get("botao_importar", "#06B6D4")
            botao_configurar = colors.get("botao_configurar", "#6B7280")
            botao_ajuda = colors.get("botao_ajuda", "#3B82F6")
            botao_filtrar = colors.get("botao_filtrar", "#6366F1")
            botao_limpar = colors.get("botao_limpar", "#F59E0B")
            botao_voltar = colors.get("botao_voltar", "#6B7280")
            botao_avancar = colors.get("botao_avancar", "#10B981")
            botao_adiantamento = colors.get("botao_adiantamento", "#10B981")
            botao_comprovante = colors.get("botao_comprovante", "#8B5CF6")
            botao_buscar = colors.get("botao_buscar", "#3B82F6")
            botao_export_csv = colors.get("botao_export_csv", "#06B6D4")
            botao_export_pdf = colors.get("botao_export_pdf", "#F59E0B")

            self.configure(fg_color=fundo)
            self.preview_container.configure(fg_color=primaria, border_color=borda)

            self.title_label.configure(text_color=texto)
            self.sample_label.configure(text_color=texto)

            self.sample_button.configure(fg_color=secundaria, hover_color=hover, text_color=texto, border_color=borda)
            self.sample_entry.configure(fg_color=secundaria, text_color=texto, border_color=borda)
            self.tertiary_frame.configure(fg_color=terciaria, border_color=borda)
            self.tertiary_label.configure(text_color=texto)
            self.border_frame.configure(fg_color=primaria, border_color=borda)
            self.border_label.configure(text_color=texto)
            self.hover_demo_btn.configure(fg_color=secundaria, hover_color=hover, text_color=texto, border_color=borda)
            self.selecao_demo_btn.configure(fg_color=selecao, hover_color=selecao,
                                            text_color=self._get_contrast_color(selecao), border_color=borda)
            self.success_btn.configure(fg_color=sucesso, hover_color=sucesso,
                                       text_color=self._get_contrast_color(sucesso))
            self.alert_btn.configure(fg_color=alerta, hover_color=alerta, text_color=self._get_contrast_color(alerta))
            self.highlight_btn.configure(fg_color=destaque, hover_color=destaque,
                                         text_color=self._get_contrast_color(destaque))

            # Botões de referência
            self.botao_salvar_ref.configure(fg_color=botao_salvar, hover_color=ajustar_hover(botao_salvar),
                                            text_color=get_contraste_texto(botao_salvar),
                                            border_color=ajustar_hover(botao_salvar, 0.7))
            self.botao_excluir_ref.configure(fg_color=botao_excluir, hover_color=ajustar_hover(botao_excluir),
                                             text_color=get_contraste_texto(botao_excluir),
                                             border_color=ajustar_hover(botao_excluir, 0.7))
            self.botao_novo_ref.configure(fg_color=botao_novo, hover_color=ajustar_hover(botao_novo),
                                          text_color=get_contraste_texto(botao_novo),
                                          border_color=ajustar_hover(botao_novo, 0.7))
            self.botao_imprimir_ref.configure(fg_color=botao_imprimir, hover_color=ajustar_hover(botao_imprimir),
                                              text_color=get_contraste_texto(botao_imprimir),
                                              border_color=ajustar_hover(botao_imprimir, 0.7))
            self.botao_pdf_ref.configure(fg_color=botao_pdf, hover_color=ajustar_hover(botao_pdf),
                                         text_color=get_contraste_texto(botao_pdf),
                                         border_color=ajustar_hover(botao_pdf, 0.7))
            self.botao_editar_ref.configure(fg_color=botao_editar, hover_color=ajustar_hover(botao_editar),
                                            text_color=get_contraste_texto(botao_editar),
                                            border_color=ajustar_hover(botao_editar, 0.7))
            self.botao_visualizar_ref.configure(fg_color=botao_visualizar, hover_color=ajustar_hover(botao_visualizar),
                                                text_color=get_contraste_texto(botao_visualizar),
                                                border_color=ajustar_hover(botao_visualizar, 0.7))
            self.botao_confirmar_ref.configure(fg_color=botao_confirmar, hover_color=ajustar_hover(botao_confirmar),
                                               text_color=get_contraste_texto(botao_confirmar),
                                               border_color=ajustar_hover(botao_confirmar, 0.7))
            self.botao_cancelar_ref.configure(fg_color=botao_cancelar, hover_color=ajustar_hover(botao_cancelar),
                                              text_color=get_contraste_texto(botao_cancelar),
                                              border_color=ajustar_hover(botao_cancelar, 0.7))
            self.botao_exportar_ref.configure(fg_color=botao_exportar, hover_color=ajustar_hover(botao_exportar),
                                              text_color=get_contraste_texto(botao_exportar),
                                              border_color=ajustar_hover(botao_exportar, 0.7))
            self.botao_importar_ref.configure(fg_color=botao_importar, hover_color=ajustar_hover(botao_importar),
                                              text_color=get_contraste_texto(botao_importar),
                                              border_color=ajustar_hover(botao_importar, 0.7))
            self.botao_configurar_ref.configure(fg_color=botao_configurar, hover_color=ajustar_hover(botao_configurar),
                                                text_color=get_contraste_texto(botao_configurar),
                                                border_color=ajustar_hover(botao_configurar, 0.7))
            self.botao_ajuda_ref.configure(fg_color=botao_ajuda, hover_color=ajustar_hover(botao_ajuda),
                                           text_color=get_contraste_texto(botao_ajuda),
                                           border_color=ajustar_hover(botao_ajuda, 0.7))
            self.botao_filtrar_ref.configure(fg_color=botao_filtrar, hover_color=ajustar_hover(botao_filtrar),
                                             text_color=get_contraste_texto(botao_filtrar),
                                             border_color=ajustar_hover(botao_filtrar, 0.7))
            self.botao_limpar_ref.configure(fg_color=botao_limpar, hover_color=ajustar_hover(botao_limpar),
                                            text_color=get_contraste_texto(botao_limpar),
                                            border_color=ajustar_hover(botao_limpar, 0.7))
            self.botao_voltar_ref.configure(fg_color=botao_voltar, hover_color=ajustar_hover(botao_voltar),
                                            text_color=get_contraste_texto(botao_voltar),
                                            border_color=ajustar_hover(botao_voltar, 0.7))
            self.botao_avancar_ref.configure(fg_color=botao_avancar, hover_color=ajustar_hover(botao_avancar),
                                             text_color=get_contraste_texto(botao_avancar),
                                             border_color=ajustar_hover(botao_avancar, 0.7))
            self.botao_adiantamento_ref.configure(fg_color=botao_adiantamento,
                                                  hover_color=ajustar_hover(botao_adiantamento),
                                                  text_color=get_contraste_texto(botao_adiantamento),
                                                  border_color=ajustar_hover(botao_adiantamento, 0.7))
            self.botao_comprovante_ref.configure(fg_color=botao_comprovante,
                                                 hover_color=ajustar_hover(botao_comprovante),
                                                 text_color=get_contraste_texto(botao_comprovante),
                                                 border_color=ajustar_hover(botao_comprovante, 0.7))
            self.botao_buscar_ref.configure(fg_color=botao_buscar, hover_color=ajustar_hover(botao_buscar),
                                            text_color=get_contraste_texto(botao_buscar),
                                            border_color=ajustar_hover(botao_buscar, 0.7))
            self.botao_export_csv_ref.configure(fg_color=botao_export_csv, hover_color=ajustar_hover(botao_export_csv),
                                                text_color=get_contraste_texto(botao_export_csv),
                                                border_color=ajustar_hover(botao_export_csv, 0.7))
            self.botao_export_pdf_ref.configure(fg_color=botao_export_pdf, hover_color=ajustar_hover(botao_export_pdf),
                                                text_color=get_contraste_texto(botao_export_pdf),
                                                border_color=ajustar_hover(botao_export_pdf, 0.7))

        except Exception as e:
            print(f"Erro ao atualizar preview: {e}")

    def _get_contrast_color(self, hex_color):
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#000000" if luminance > 0.5 else "#FFFFFF"
        except:
            return "#FFFFFF"

    def highlight_element(self, campo):
        self.clear_highlight()

        element_map = {
            "primaria": self.preview_container,
            "secundaria": [self.sample_button, self.sample_entry],
            "terciaria": self.tertiary_frame,
            "fundo": self,
            "texto": [self.title_label, self.sample_label, self.tertiary_label, self.border_label],
            "destaque": self.highlight_btn,
            "sucesso": self.success_btn,
            "alerta": self.alert_btn,
            "borda": self.border_frame,
            "hover": self.hover_demo_btn,
            "selecao": self.selecao_demo_btn,
            "botao_salvar": self.botao_salvar_ref,
            "botao_excluir": self.botao_excluir_ref,
            "botao_novo": self.botao_novo_ref,
            "botao_imprimir": self.botao_imprimir_ref,
            "botao_pdf": self.botao_pdf_ref,
            "botao_editar": self.botao_editar_ref,
            "botao_visualizar": self.botao_visualizar_ref,
            "botao_confirmar": self.botao_confirmar_ref,
            "botao_cancelar": self.botao_cancelar_ref,
            "botao_exportar": self.botao_exportar_ref,
            "botao_importar": self.botao_importar_ref,
            "botao_configurar": self.botao_configurar_ref,
            "botao_ajuda": self.botao_ajuda_ref,
            "botao_filtrar": self.botao_filtrar_ref,
            "botao_limpar": self.botao_limpar_ref,
            "botao_voltar": self.botao_voltar_ref,
            "botao_avancar": self.botao_avancar_ref,
            "botao_adiantamento": self.botao_adiantamento_ref,
            "botao_comprovante": self.botao_comprovante_ref,
            "botao_buscar": self.botao_buscar_ref,
            "botao_export_csv": self.botao_export_csv_ref,
            "botao_export_pdf": self.botao_export_pdf_ref,
        }

        elements = element_map.get(campo)
        if not elements:
            return

        if not isinstance(elements, list):
            elements = [elements]

        for element in elements:
            try:
                if hasattr(element, 'cget'):
                    try:
                        original_border = element.cget('border_width')
                        self.original_border_widths[element] = original_border
                    except:
                        self.original_border_widths[element] = 2

                if hasattr(element, 'configure'):
                    element.configure(border_width=4, border_color="#FFD700")
            except Exception as e:
                print(f"Erro ao destacar elemento: {e}")

        self.highlighted_element = elements

    def clear_highlight(self):
        if self.highlighted_element:
            for element in self.highlighted_element:
                try:
                    original_border = self.original_border_widths.get(element, 2)
                    if hasattr(element, 'configure'):
                        element.configure(border_width=original_border)
                except Exception as e:
                    print(f"Erro ao limpar destaque: {e}")

            self.highlighted_element = None
            self.original_border_widths.clear()


# =================== SELETOR DE CORES ===================

class ColorPickerWidget(ctk.CTkFrame):
    def __init__(self, master, initial_color="#FFFFFF", callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.callback = callback
        self.current_color = initial_color

        self.basic_colors = [
            ["#000000", "#1A1A1A", "#333333", "#4D4D4D", "#666666", "#808080", "#999999", "#B3B3B3", "#CCCCCC",
             "#E6E6E6", "#FFFFFF"],
            ["#8B0000", "#B22222", "#DC143C", "#FF0000", "#FF6347", "#FF7F7F", "#FFA07A", "#FFB6C1", "#FFC0CB",
             "#FFE4E1"],
            ["#FF4500", "#FF6347", "#FF8C00", "#FFA500", "#FFD700", "#FFFF00", "#FFFFE0", "#FFFACD", "#FFF8DC",
             "#FFEFD5"],
            ["#006400", "#008000", "#228B22", "#32CD32", "#00FF00", "#7FFF00", "#90EE90", "#98FB98", "#ADFF2F",
             "#F0FFF0"],
            ["#00008B", "#0000CD", "#0000FF", "#1E90FF", "#4169E1", "#6495ED", "#87CEEB", "#ADD8E6", "#B0E0E6",
             "#E0FFFF"],
            ["#4B0082", "#483D8B", "#6A5ACD", "#7B68EE", "#8A2BE2", "#9370DB", "#BA55D3", "#DA70D6", "#DDA0DD",
             "#E6E6FA"],
        ]

        self._build_ui()

    def _build_ui(self):
        preview_frame = ctk.CTkFrame(self, fg_color="transparent")
        preview_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(preview_frame, text="Cor Selecionada:", font=("Arial", 11, "bold")).pack(side="left", padx=5)

        self.preview_btn = ctk.CTkButton(preview_frame, text=self.current_color, fg_color=self.current_color,
                                         hover_color=self.current_color,
                                         text_color=self._get_contrast_color(self.current_color),
                                         font=("Arial", 10, "bold"), height=30, width=120,
                                         command=self._open_advanced_picker)
        self.preview_btn.pack(side="left", padx=5)

        palette_label = ctk.CTkLabel(self, text="Paleta de Cores:", font=("Arial", 11, "bold"))
        palette_label.pack(anchor="w", padx=5, pady=(10, 5))

        canvas_height = len(self.basic_colors) * 28
        canvas_width = 11 * 28

        self.canvas = Canvas(self, width=canvas_width, height=canvas_height, bg="#1E1E1E", highlightthickness=0)
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
                self.canvas.tag_bind(rect_id, "<Enter>",
                                     lambda e, rid=rect_id: self.canvas.itemconfig(rid, outline="#FFFFFF", width=2))
                self.canvas.tag_bind(rect_id, "<Leave>",
                                     lambda e, rid=rect_id: self.canvas.itemconfig(rid, outline="#666666", width=1))

        ctk.CTkButton(self, text="🎨 Seletor Avançado", font=("Arial", 11), height=30,
                      command=self._open_advanced_picker).pack(pady=10, padx=5)

    def _select_color(self, color):
        self.current_color = color
        self.preview_btn.configure(fg_color=color, hover_color=color, text=color,
                                   text_color=self._get_contrast_color(color))
        if self.callback:
            self.callback(color)

    def _open_advanced_picker(self):
        if hasattr(self, "_advanced_win") and self._advanced_win.winfo_exists():
            self._advanced_win.focus()
            return

        def close_picker():
            if hasattr(self, "_advanced_win") and self._advanced_win.winfo_exists():
                self._advanced_win.destroy()

        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            if len(hex_color) != 6 or not re.fullmatch(r"[0-9A-Fa-f]{6}", hex_color):
                return None
            return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        def rgb_to_hex(rgb_tuple):
            return "#{:02X}{:02X}{:02X}".format(*rgb_tuple)

        def hsv_to_hex(h, s, v):
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return rgb_to_hex((int(r * 255), int(g * 255), int(b * 255)))

        def build_wheel_image(size, radius, oversample=2):
            base_size = int(size * oversample)
            base_radius = radius * oversample
            image = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
            center = base_size / 2
            for x in range(base_size):
                for y in range(base_size):
                    dx = x - center + 0.5
                    dy = y - center + 0.5
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist <= base_radius:
                        hue = (math.atan2(-dy, dx) % (2 * math.pi)) / (2 * math.pi)
                        sat = min(1.0, dist / base_radius)
                        r, g, b = colorsys.hsv_to_rgb(hue, sat, 1.0)
                        image.putpixel((x, y), (int(r * 255), int(g * 255), int(b * 255), 255))
            if oversample > 1:
                image = image.resize((size, size), resample=Image.LANCZOS)
            return image

        def grab_screen_hex(x, y):
            try:
                pixel = ImageGrab.grab(bbox=(x, y, x + 1, y + 1)).getpixel((0, 0))
                return rgb_to_hex(pixel)
            except Exception as e:
                print(f"⚠️ Não foi possível capturar cor da tela: {e}")
                return None

        def start_eyedropper():
            overlay = tk.Toplevel(self._advanced_win)
            overlay.overrideredirect(True)
            overlay.attributes("-alpha", 0.02)
            overlay.attributes("-topmost", True)
            overlay.configure(cursor="crosshair", bg="black")
            overlay.geometry(f"{overlay.winfo_screenwidth()}x{overlay.winfo_screenheight()}+0+0")
            overlay.focus_force()

            lens_size = 120
            lens_padding = 16
            lens_canvas = tk.Canvas(overlay, width=lens_size + 2 * lens_padding,
                                   height=lens_size + 36, bg="#121212", highlightthickness=0)
            lens_canvas.configure(cursor="circle")
            lens_photo = {"image": None}

            def finish(event=None):
                try:
                    if overlay.winfo_exists():
                        overlay.destroy()
                finally:
                    self._advanced_win.deiconify()
                    self._advanced_win.lift()
                    self._advanced_win.focus_force()

            def update_lens(event):
                try:
                    grab_box = (event.x_root - 12, event.y_root - 12, event.x_root + 13, event.y_root + 13)
                    zoom = ImageGrab.grab(bbox=grab_box).resize((lens_size, lens_size), Image.LANCZOS)
                    lens_photo["image"] = ImageTk.PhotoImage(zoom)
                    lens_canvas.delete("all")
                    lens_canvas.create_rectangle(4, 4, lens_size + lens_padding * 2 - 4,
                                                 lens_size + lens_padding + 8, outline="#3A3A3A",
                                                 width=2, fill="#1A1A1A")
                    lens_canvas.create_image(lens_padding, lens_padding, anchor="nw", image=lens_photo["image"])
                    center = lens_padding + lens_size / 2
                    lens_canvas.create_line(center - 8, lens_padding + lens_size / 2,
                                            center + 8, lens_padding + lens_size / 2, fill="#FFFFFF", width=1)
                    lens_canvas.create_line(lens_padding + lens_size / 2, center - 8,
                                            lens_padding + lens_size / 2, center + 8, fill="#FFFFFF", width=1)
                    current_hex = grab_screen_hex(event.x_root, event.y_root) or "--"
                    lens_canvas.create_text(lens_padding, lens_size + lens_padding + 8, anchor="w",
                                            text=current_hex, fill="#E5E7EB", font=("Arial", 11, "bold"))
                    pos_x = max(10, min(event.x_root + 24, overlay.winfo_screenwidth() - lens_size - 2 * lens_padding - 10))
                    pos_y = max(10, min(event.y_root + 24, overlay.winfo_screenheight() - lens_size - lens_padding - 40))
                    lens_canvas.place(x=pos_x, y=pos_y)
                except Exception as e:
                    print(f"⚠️ Não foi possível atualizar lupa do conta-gotas: {e}")

            def pick_color(event):
                color_hex = grab_screen_hex(event.x_root, event.y_root)
                if color_hex:
                    set_current_color(color_hex)
                finish()

            overlay.bind("<Motion>", update_lens)
            overlay.bind("<Button-1>", pick_color)
            overlay.bind("<Escape>", finish)


        initial_rgb = hex_to_rgb(self.current_color) or (255, 255, 255)
        h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in initial_rgb))
        current_hsv = {"h": h, "s": s, "v": v}

        self._advanced_win = ctk.CTkToplevel(self)
        self._advanced_win.title("Cores")
        self._advanced_win.resizable(True, True)
        self._advanced_win.minsize(390, 450)
        target_w, target_h = 410, 608
        self._advanced_win.geometry(f"{target_w}x{target_h}")
        self._advanced_win.transient(self.winfo_toplevel())
        self._advanced_win.protocol("WM_DELETE_WINDOW", close_picker)
        self._advanced_win.update_idletasks()
        screen_w = self._advanced_win.winfo_screenwidth()
        screen_h = self._advanced_win.winfo_screenheight()
        x = int((screen_w - target_w) / 2)
        y = int((screen_h - target_h) / 2)
        self._advanced_win.geometry(f"{target_w}x{target_h}+{x}+{y}")

        wrapper = ctk.CTkFrame(self._advanced_win, fg_color=self.cget("fg_color"))
        wrapper.pack(fill="both", expand=True, padx=16, pady=16)

        # Preview + entrada hex + gota simulada
        top_row = ctk.CTkFrame(wrapper, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 6))

        preview_btn = ctk.CTkButton(
            top_row,
            text=self.current_color,
            fg_color=self.current_color,
            hover_color=self.current_color,
            text_color=self._get_contrast_color(self.current_color),
            font=("Arial", 12, "bold"),
            height=32,
            width=90,
            corner_radius=10,
            command=lambda: None,
        )
        preview_btn.pack(side="left")

        hex_var = tk.StringVar(value=self.current_color)
        hex_entry = ctk.CTkEntry(top_row, textvariable=hex_var, width=110, font=("Arial", 12))
        hex_entry.pack(side="left", padx=(10, 6))

        eyedropper = ctk.CTkButton(top_row, text="🧪", width=34, height=34,
                                   fg_color="#3A3A3A", hover_color="#4A4A4A",
                                   command=start_eyedropper)
        eyedropper.pack(side="left")

        # Barra de modos (ícones simulados para manter o layout do macOS)
        toolbar = ctk.CTkFrame(wrapper, fg_color="transparent")
        toolbar.pack(fill="x", pady=(6, 6))

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
            h_val, s_val, v_val = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
            current_hsv.update({"h": h_val, "s": s_val, "v": v_val})
            preview_btn.configure(fg_color=color_hex, hover_color=color_hex, text=color_hex,
                                  text_color=self._get_contrast_color(color_hex))
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

        # Área inferior fixa (favoritos + ação)
        bottom_area = ctk.CTkFrame(wrapper, fg_color="transparent")
        bottom_area.pack(fill="x", pady=(6, 0))

        favorites_frame = ctk.CTkFrame(bottom_area, fg_color="#1F1F1F", corner_radius=8, border_width=1,
                                       border_color="#3A3A3A")
        favorites_frame.pack(fill="x", pady=(0, 8))

        fav_label = ctk.CTkLabel(favorites_frame, text="Favoritos", anchor="w")
        fav_label.pack(fill="x", padx=8, pady=(6, 2))

        fav_grid = ctk.CTkFrame(favorites_frame, fg_color="transparent")
        fav_grid.pack(fill="x", padx=6, pady=(0, 6))
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
                      command=close_picker, width=120).pack(side="left", padx=(0, 6))
        ctk.CTkButton(buttons_frame, text="OK", fg_color="#3B82F6", hover_color="#2563EB",
                      command=lambda: (self._select_color(self.current_color), close_picker()), width=120).pack(side="right")

        # ------------------------ Abas ------------------------
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

        for key, icon, tooltip in tabs:
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

        # --------- Aba: Roda (HSV) ---------
        wheel_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("wheel", wheel_tab)

        wheel_size = 260
        wheel_radius = wheel_size / 2 - 6
        wheel_center = wheel_size / 2

        wheel_image = build_wheel_image(wheel_size, wheel_radius, oversample=4)
        self._wheel_photo = ImageTk.PhotoImage(wheel_image)

        wheel_canvas = Canvas(wheel_tab, width=wheel_size, height=wheel_size, bg="#1F1F1F",
                              highlightthickness=0)
        wheel_canvas.pack(pady=(6, 12))
        wheel_canvas.create_image(0, 0, image=self._wheel_photo, anchor="nw")

        def update_marker():
            wheel_canvas.delete("marker")
            cx = wheel_center + (wheel_radius * current_hsv["s"] * math.cos(current_hsv["h"] * 2 * math.pi))
            cy = wheel_center - (wheel_radius * current_hsv["s"] * math.sin(current_hsv["h"] * 2 * math.pi))
            wheel_canvas.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, outline="#000000", width=2, tags="marker")
            wheel_canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, outline="#FFFFFF", width=2, tags="marker")

        def update_from_hsv():
            color_hex = hsv_to_hex(current_hsv["h"], current_hsv["s"], current_hsv["v"])
            set_current_color(color_hex)

        def on_wheel_click(event):
            dx = event.x - wheel_center
            dy = event.y - wheel_center
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > wheel_radius:
                return
            hue = (math.atan2(-dy, dx) % (2 * math.pi)) / (2 * math.pi)
            sat = min(1.0, dist / wheel_radius)
            current_hsv["h"] = hue
            current_hsv["s"] = sat
            update_from_hsv()

        wheel_canvas.bind("<Button-1>", on_wheel_click)
        wheel_canvas.bind("<B1-Motion>", on_wheel_click)

        slider_frame = ctk.CTkFrame(wheel_tab, fg_color="transparent")
        slider_frame.pack(fill="x", pady=(0, 10), padx=4)
        ctk.CTkLabel(slider_frame, text="Brilho:").pack(side="left")
        brightness_slider = ctk.CTkSlider(slider_frame, from_=0, to=1, number_of_steps=100,
                                          command=lambda val: (current_hsv.__setitem__('v', float(val)), update_from_hsv()))
        brightness_slider.pack(side="left", fill="x", expand=True, padx=10)
        brightness_slider.set(v)

        quick_palette = ctk.CTkFrame(wheel_tab, fg_color="transparent")
        quick_palette.pack(pady=(0, 8))
        palette_colors = [c for row in self.basic_colors for c in row][:24]
        quick_palette_cols = 12
        for idx, color in enumerate(palette_colors):
            btn = ctk.CTkButton(quick_palette, width=24, height=22, text="", fg_color=color,
                                hover_color=color, corner_radius=4,
                                command=lambda c=color: set_current_color(c))
            row = idx // quick_palette_cols
            col = idx % quick_palette_cols
            btn.grid(row=row, column=col, padx=3, pady=3)

        # --------- Aba: Escala Web (cinzas + barra lateral) ---------
        grays_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("grays", grays_tab)

        grayscale_colors = ["#FFFFFF", "#F2F2F2", "#E5E5E5", "#CCCCCC", "#B3B3B3", "#999999", "#808080",
                             "#666666", "#4D4D4D", "#333333", "#1A1A1A", "#000000"]
        gray_frame = ctk.CTkFrame(grays_tab, fg_color="#151515", corner_radius=8, border_width=1,
                                  border_color="#303030")
        gray_frame.pack(fill="both", expand=True, pady=6)

        search_gray = ctk.CTkEntry(gray_frame, placeholder_text="Buscar", height=32)
        search_gray.pack(fill="x", padx=10, pady=(10, 6))

        list_holder = ctk.CTkScrollableFrame(gray_frame, fg_color="#151515")
        list_holder.pack(fill="both", expand=True, padx=6, pady=(0, 10))

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
                swatch.pack(side="left", padx=(0, 10))
                ctk.CTkLabel(row, text=color_hex, font=("Arial", 12)).pack(side="left")

        search_gray.bind("<KeyRelease>", lambda e: render_gray_list(search_gray.get()))
        render_gray_list()

        # --------- Aba: Listas (paletas nomeadas) ---------
        lists_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("lists", lists_tab)

        list_top = ctk.CTkFrame(lists_tab, fg_color="transparent")
        list_top.pack(fill="x", pady=(6, 6))

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
        palette_selector.pack(side="left", padx=(0, 8))

        search_list = ctk.CTkEntry(list_top, placeholder_text="Buscar", width=160)
        search_list.pack(side="left")

        list_area = ctk.CTkScrollableFrame(lists_tab, fg_color="#151515")
        list_area.pack(fill="both", expand=True, padx=4, pady=(0, 8))

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
                swatch.pack(side="left", padx=(0, 10))
                ctk.CTkLabel(row, text=name, font=("Arial", 12)).pack(side="left")
                ctk.CTkLabel(row, text=color_hex, font=("Arial", 11), text_color="#9CA3AF").pack(side="right")

        palette_selector.configure(command=lambda _: render_named())
        search_list.bind("<KeyRelease>", lambda e: render_named())
        render_named()

        # --------- Aba: Lápis ---------
        pencils_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("pencils", pencils_tab)

        pencil_sets = {
            "Prata": ["#F7F7F7", "#E2E2E2", "#C5C5C5", "#AAAAAA", "#919191", "#777777", "#5E5E5E"],
            "Clássico": ["#FF3B30", "#FF9500", "#FFD60A", "#34C759", "#0A84FF", "#5856D6", "#AF52DE"],
            "Neon": ["#FF2D55", "#FF6B81", "#FF9500", "#FFD60A", "#64D2FF", "#30DB5B", "#AC8E68"],
        }

        combo_pencil = ctk.CTkComboBox(pencils_tab, values=list(pencil_sets.keys()), state="readonly", width=150)
        combo_pencil.set("Prata")
        combo_pencil.pack(pady=(8, 4))

        pencils_canvas = Canvas(pencils_tab, width=330, height=170, bg="#151515", highlightthickness=0)
        pencils_canvas.pack(pady=(0, 8))

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
                        x, y + 10, x + 18, y, x + 36, y + 10, x + 36, y + 44, x, y + 44,
                        fill=color_hex, outline="#2E2E2E", width=1, tags=("pencil", color_hex)
                    )
                    pencils_canvas.create_polygon(
                        x + 12, y - 4, x + 18, y + 10, x + 24, y - 4,
                        fill="#D8D2C4", outline="#2E2E2E", width=1, tags=("pencil", color_hex)
                    )
                    pencils_canvas.create_rectangle(
                        x + 4, y + 10, x + 32, y + 40, fill=color_hex, outline="", tags=("pencil", color_hex)
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

        # --------- Aba: Paletas (grade de cores) ---------
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

        # Inicializa layout com estado atual
        set_current_color(self.current_color)
        show_tab("wheel")

    def set_color(self, color):
        self._select_color(color)

    def get_color(self):
        return self.current_color

    def _get_contrast_color(self, hex_color):
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#000000" if luminance > 0.5 else "#FFFFFF"
        except:
            return "#FFFFFF"


# =================== COMPONENTES DE UI ===================

class _Chip(ctk.CTkButton):
    def __init__(self, master, text, command, is_active=False, **kw):
        # Guarda o texto original e o estado
        self.label_text = text
        self.is_active = is_active

        display_text = f"● {text}" if is_active else text
        font_style = ("Arial", 12, "bold" if is_active else "normal")

        super().__init__(
            master,
            text=display_text,
            command=command,
            height=28,
            corner_radius=10,
            font=font_style,
            **kw
        )

    def set_active(self, active: bool):
        """Atualiza visualmente o chip para mostrar ou esconder o pontinho."""
        self.is_active = active
        display_text = f"● {self.label_text}" if active else self.label_text
        font_style = ("Arial", 12, "bold" if active else "normal")
        self.configure(text=display_text, font=font_style)


# =================== PÁGINA PRINCIPAL DE TEMAS ===================

class TemasPage(ctk.CTkFrame):
    MAX_COLS = 4

    PADROES = copy.deepcopy(DEFAULT_PADROES)
    CAMPOS = list(CAMPOS_PADRAO)
    LABELS_CAMPOS = dict(LABELS_CAMPOS_PADRAO)

    def __init__(self, master=None, *args, **kwargs):
        # Descobre a referência da aplicação principal
        self.app = (
                kwargs.pop("sistema", None)
                or kwargs.pop("app", None)
                or kwargs.pop("controller", None)
                or kwargs.pop("ctx", None)
                or kwargs.pop("root", None)
                or kwargs.pop("main", None)
        )

        super().__init__(master, *args, **kwargs)

        if self.app is None:
            self.app = self.winfo_toplevel()

        # Sempre inicia com um catálogo de temas fresco para cada instância
        self.PADROES = copy.deepcopy(DEFAULT_PADROES)

        # Garante um gtema local caso o app ainda não tenha
        if not hasattr(self.app, "gtema"):

            class _LocalGTema:
                def __init__(self, app, page):
                    self.app = app
                    self.page = page
                    self.temas_padrao = dict(page.PADROES)

                def aplicar_tema(self, nome):
                    pal = self.temas_padrao.get(nome, TemasPage.PADROES["Noite Urbana"])
                    for k, v in pal.items():
                        setattr(self.app, f"cor_{k}", v)
                    self.page._style_demo_theme()

            self.app.gtema = _LocalGTema(self.app, self)
            pal = TemasPage.PADROES["Noite Urbana"]
            for k, v in pal.items():
                setattr(self.app, f"cor_{k}", v)

        # Fundo da página acompanha o tema atual do app
        self.configure(fg_color=self.app.cor_fundo)

        # Garante que o catálogo global de temas padrão esteja atualizado
        if hasattr(self.app, "gtema"):
            self.app.gtema.temas_padrao.update(self.PADROES)

        # ------------------------------------------------------------------
        # SETTINGS LOCAIS (usadas para tema atual, temas padrão ocultos etc.)
        # ------------------------------------------------------------------
        base_settings = self._get_app_settings()
        if base_settings is None:
            base_settings = {
                "theme": "Noite Urbana",
                "custom_themes": {},
                "excluded_default_themes": [],
            }
            self._set_app_settings(base_settings)

        self.settings = base_settings

        # IMPORTANTE:
        # Lista de temas personalizados AGORA é somente por usuário.
        # Começa vazia e será preenchida APENAS com o que vier do banco
        # (tabela usuario_temas_personalizados filtrando por usuario_id).
        self.custom = {}

        # Guarda cópia dos temas padrão originais
        self.temas_originais = dict(self.PADROES)

        # Remove da tela os temas padrão que o usuário marcou como excluídos
        excluded_themes = self.settings.get("excluded_default_themes", [])
        for tema_excluido in excluded_themes:
            if tema_excluido in self.PADROES:
                del self.PADROES[tema_excluido]
            if hasattr(self.app, "gtema") and tema_excluido in self.app.gtema.temas_padrao:
                del self.app.gtema.temas_padrao[tema_excluido]

        # ------------------------------------------------------------------
        # CARREGAR TEMAS PERSONALIZADOS DO USUÁRIO (preenche self.custom)
        # ------------------------------------------------------------------
        self._carregar_temas_do_banco()

        # Garante padrão de botões em todos os temas carregados
        self._garantir_padrao_botoes_temas()

        # Carrega preferência de tema atual do usuário
        preferencia_tema = self._carregar_preferencia_tema_atual()
        if preferencia_tema:
            tema_nome, tema_tipo = preferencia_tema
            self.tema_atual = tema_nome
        else:
            self.tema_atual = self._get_current_theme()

        # Ajusta a página para usar imediatamente o tema já ativo no menu
        self._sincronizar_tema_inicial()

        self.campo_selecionado = None
        self.vars = {}

        # ------------------------------------------------------------------
        # LAYOUT DA PÁGINA
        # ------------------------------------------------------------------
        self._build_header()

        main_layout = ctk.CTkFrame(self, fg_color="transparent")
        main_layout.pack(fill="both", expand=True, padx=5, pady=5)

        left_panel = ctk.CTkFrame(main_layout, fg_color="transparent")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))

        center_panel = ctk.CTkFrame(
            main_layout,
            fg_color=self.app.cor_secundaria,
            corner_radius=10,
            border_width=2,
            border_color=self.app.cor_borda,
        )
        center_panel.pack(side="left", fill="both", padx=(0, 5))
        center_panel.configure(width=260)

        right_panel = ctk.CTkFrame(
            main_layout,
            fg_color=self.app.cor_secundaria,
            corner_radius=10,
            border_width=2,
            border_color=self.app.cor_borda,
        )
        right_panel.pack(side="left", fill="both", padx=(5, 0))
        right_panel.configure(width=360)

        self._build_left_panel(left_panel)
        self._build_center_panel(center_panel)
        self._build_right_panel(right_panel)

        # ------------------------------------------------------------------
        # IMPORTANTE:
        # Não reaplicar tema global aqui para evitar loop infinito.
        # O ThemeManager já aplicou o tema quando o app iniciou
        # ou quando o usuário clicou em "Salvar / Aplicar".
        # Aqui só montamos o preview com o tema já ativo.
        # ------------------------------------------------------------------
        self._style_demo_theme()
        self._carregar_tema_no_editor(self.tema_atual)

    def _build_header(self):
        header = ctk.CTkFrame(
            self,
            fg_color=self.app.cor_secundaria,
            corner_radius=12,
            border_width=1,
            border_color=self.app.cor_borda,
        )
        header.pack(fill="x", padx=5, pady=(0, 8))

        info_frame = ctk.CTkFrame(header, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="Estúdio de Temas Personalizados",
            font=("Arial", 20, "bold"),
            text_color=self.app.cor_texto,
        ).pack(anchor="w")

        resumo_temas = f"Tema atual: {self.tema_atual} • {len(self.custom)} tema(s) salvo(s)"
        ctk.CTkLabel(
            info_frame,
            text=resumo_temas,
            font=("Arial", 13),
            text_color=self.app.cor_destaque,
        ).pack(anchor="w", pady=(4, 0))

        action_frame = ctk.CTkFrame(header, fg_color="transparent")
        action_frame.pack(side="right", padx=12, pady=10)

        ctk.CTkButton(
            action_frame,
            text="Aplicar tema atual",
            fg_color=self.app.cor_botao_confirmar if hasattr(self.app, "cor_botao_confirmar") else self.app.cor_sucesso,
            hover_color=self.app.cor_hover,
            text_color=self.app.cor_texto,
            command=lambda: self._aplicar_tema_completo(self.tema_atual),
            height=36,
            corner_radius=10,
            font=("Arial", 12, "bold"),
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            action_frame,
            text="Novo tema personalizado",
            fg_color=self.app.cor_destaque,
            hover_color=self.app.cor_hover,
            text_color=get_contraste_texto(self.app.cor_destaque),
            command=self._reset_editor_com_defaults,
            height=36,
            corner_radius=10,
            font=("Arial", 12, "bold"),
        ).pack(side="left", padx=4)

    def _reset_editor_com_defaults(self):
        """Prepara o editor com o tema atual ou padrão."""
        base_tema = self.tema_atual if self.tema_atual in self.PADROES else "Noite Urbana"
        nome_sugestao = f"{base_tema} Personalizado"

        if hasattr(self, "var_nome"):
            self.var_nome.set(nome_sugestao)

        try:
            self._carregar_tema_no_editor(base_tema)
        except Exception:
            self._carregar_tema_no_editor("Noite Urbana")

    def _get_app_settings(self):
        if hasattr(self.app, "_settings"):
            return self.app._settings
        if hasattr(self.app, "settings"):
            return self.app.settings
        return None

    def _set_app_settings(self, settings):
        if hasattr(self.app, "_settings"):
            self.app._settings = settings
        elif hasattr(self.app, "settings"):
            self.app.settings = settings

    def _carregar_temas_do_banco(self):
        """
        Carrega temas personalizados do banco de dados PostgreSQL
        e mescla com os temas que já estão nas configurações locais
        (self.settings["custom_themes"]).

        Preenche o dicionário self.custom com:
            { nome_tema: { 'fundo': '#000000', ... } }

        Retorna: bool - True se carregou com sucesso, False se houve erro.
        """

        import json
        try:
            # Garante que self.custom exista.
            # NÃO limpamos mais aqui, porque ele já veio das settings.
            if not hasattr(self, "custom") or self.custom is None:
                self.custom = {}

            # Se não tiver usuário logado, não tem porquê buscar no banco
            usuario_id = getattr(self.app, "usuario_id", None)
            if not usuario_id:
                print("⚠️ Nenhum usuário definido para carregar temas personalizados.")
                return False

            # Usa o novo módulo de banco
            from BANCO_DE_DADOS_PG import get_conn, get_schema

            conn = get_conn()
            if not conn:
                print("⚠️ Conexão com banco não disponível para carregar temas personalizados.")
                return False

            schema = get_schema()

            # Busca os temas do usuário
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT nome_tema, cores_tema
                        FROM {schema}.usuario_temas_personalizados
                        WHERE usuario_id = %s
                        ORDER BY nome_tema
                        """,
                        (usuario_id,),
                    )
                    rows = cur.fetchall() or []

            carregados = 0
            for nome_tema, cores_tema in rows:
                try:
                    # cores_tema pode vir como dict (JSONB) ou como string JSON
                    if isinstance(cores_tema, dict):
                        tema_data = cores_tema
                    else:
                        tema_data = json.loads(cores_tema) if cores_tema else {}

                    if isinstance(tema_data, dict):
                        # O que vem do banco sobrescreve o que estiver nas settings
                        self.custom[nome_tema] = tema_data
                        carregados += 1
                except Exception as erro_tema:
                    print(f"⚠️ Erro ao processar tema '{nome_tema}' do banco: {erro_tema}")

            print(f"🎨 Temas personalizados carregados do banco: {carregados}")
            return True

        except Exception as erro:
            print(f"❌ Erro ao carregar temas personalizados do banco: {erro}")
            return False

    def _garantir_padrao_botoes_temas(self):
        """Garante que todos os temas tenham o padrão completo de cores dos botões"""

        # Padrão universal de cores dos botões
        padrao_universal = {
            "botao_salvar": "#10B981",
            "botao_excluir": "#EF4444",
            "botao_novo": "#3B82F6",
            "botao_imprimir": "#8B5CF6",
            "botao_pdf": "#F59E0B",
            "botao_editar": "#06B6D4",
            "botao_visualizar": "#6366F1",
            "botao_confirmar": "#22C55E",
            "botao_cancelar": "#6B7280",
            "botao_exportar": "#8B5CF6",
            "botao_importar": "#06B6D4",
            "botao_configurar": "#6B7280",
            "botao_ajuda": "#3B82F6",
            "botao_filtrar": "#6366F1",
            "botao_limpar": "#F59E0B",
            "botao_voltar": "#6B7280",
            "botao_avancar": "#10B981",
            "botao_adiantamento": "#10B981",
            "botao_comprovante": "#8B5CF6",
            "botao_buscar": "#3B82F6",
            "botao_export_csv": "#06B6D4",
            "botao_export_pdf": "#F59E0B"
        }

        # Aplica para todos os temas padrão
        for tema_nome, tema_cores in self.PADROES.items():
            for botao, cor_padrao in padrao_universal.items():
                if botao not in tema_cores or not tema_cores[botao]:
                    tema_cores[botao] = cor_padrao

        # Aplica para todos os temas personalizados
        for tema_nome, tema_cores in self.custom.items():
            for botao, cor_padrao in padrao_universal.items():
                if botao not in tema_cores or not tema_cores[botao]:
                    tema_cores[botao] = cor_padrao

        print("🎨 Padrão de botões aplicado a todos os temas")

    def _build_left_panel(self, parent):
        scroll_container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True)

        title_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(title_frame, text="Gerenciar Temas", font=("Arial", 20, "bold"),
                     text_color=self.app.cor_texto).pack(side="left")
        ctk.CTkLabel(title_frame, text=f"Atual: {self.tema_atual}", font=("Arial", 14),
                     text_color=self.app.cor_destaque).pack(side="right")

        bloc1 = ctk.CTkFrame(scroll_container, fg_color=self.app.cor_secundaria, corner_radius=10)
        bloc1.pack(fill="x", pady=(4, 12))
        ctk.CTkLabel(bloc1, text="Temas Padrão", font=("Arial", 14, "bold"), text_color=self.app.cor_texto).pack(
            anchor="w", padx=10, pady=(10, 6))

        self.chips_padrao = ctk.CTkFrame(bloc1, fg_color="transparent")
        self.chips_padrao.pack(fill="x", padx=10, pady=(0, 10))
        self._render_chip_grid(self.chips_padrao, list(self.PADROES.keys()), is_padrao=True)

        restore_btn = ctk.CTkButton(bloc1, text="🔄 Restaurar Temas Padrão", fg_color="#3498db", hover_color="#2980b9",
                                    font=("Arial", 12, "bold"), height=35, command=self._restaurar_temas_padrao)
        restore_btn.pack(fill="x", padx=10, pady=(0, 10))

        bloc2 = ctk.CTkFrame(scroll_container, fg_color=self.app.cor_secundaria, corner_radius=10)
        bloc2.pack(fill="x", pady=(4, 12))
        ctk.CTkLabel(bloc2, text="Temas Personalizados", font=("Arial", 14, "bold"),
                     text_color=self.app.cor_texto).pack(anchor="w", padx=10, pady=(10, 6))
        self.user_chips = ctk.CTkFrame(bloc2, fg_color="transparent")
        self.user_chips.pack(fill="x", padx=10, pady=(0, 10))
        self._refresca_custom_chips()

    def _build_center_panel(self, parent):
        self.preview_panel = PreviewPanel(parent, fg_color="transparent")
        self.preview_panel.pack(fill="both", expand=True, padx=10, pady=10)

    def _build_right_panel(self, parent):
        ctk.CTkLabel(parent, text="Editor de Tema", font=("Arial", 16, "bold"), text_color=self.app.cor_texto).pack(
            pady=(15, 10), padx=10)

        scroll_editor = ctk.CTkScrollableFrame(parent, fg_color="transparent", height=300)
        scroll_editor.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        for campo in self.CAMPOS:
            campo_frame = ctk.CTkFrame(scroll_editor, fg_color=self.app.cor_terciaria, corner_radius=6, border_width=1,
                                       border_color=self.app.cor_borda)
            campo_frame.pack(fill="x", pady=5)

            label = ctk.CTkLabel(campo_frame, text=self.LABELS_CAMPOS[campo], font=("Arial", 11, "bold"),
                                 text_color=self.app.cor_texto, anchor="w")
            label.pack(fill="x", padx=10, pady=(8, 4))

            var = tk.StringVar(value="#FFFFFF")
            self.vars[campo] = var

            var.trace_add("write", lambda *args: self._update_live_preview())

            controls_frame = ctk.CTkFrame(campo_frame, fg_color="transparent")
            controls_frame.pack(fill="x", padx=10, pady=(0, 8))

            entry = ctk.CTkEntry(controls_frame, textvariable=var, font=("Arial", 11), height=32)
            entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

            def on_enter(event, c=campo):
                self.preview_panel.highlight_element(c)

            def on_leave(event):
                self.preview_panel.clear_highlight()
                self._update_live_preview()

            campo_frame.bind("<Enter>", on_enter)
            campo_frame.bind("<Leave>", on_leave)
            label.bind("<Enter>", on_enter)
            label.bind("<Leave>", on_leave)
            entry.bind("<Enter>", on_enter)
            entry.bind("<Leave>", on_leave)

            def make_color_btn(c=campo, v=var):
                btn = ctk.CTkButton(
                    controls_frame,
                    text="🎨",
                    width=100,
                    height=32,
                    fg_color=v.get(),
                    hover_color=v.get(),
                    text_color=self._get_contrast_color(v.get()),
                    corner_radius=6,
                    font=("Arial", 14),
                    command=lambda: self._abrir_seletor_cor(c),
                )

                def update_btn(*args, _btn=btn, _var=v):
                    # Atualiza a cor do botão sempre que o valor da variável muda
                    color = _var.get()
                    if not _valida_hex(color):
                        return

                    try:
                        # Se o widget já foi destruído, não faz nada
                        if hasattr(_btn, "winfo_exists") and not _btn.winfo_exists():
                            return

                        _btn.configure(
                            fg_color=color,
                            hover_color=color,
                            text_color=self._get_contrast_color(color),
                        )
                    except tk.TclError:
                        # Widget já destruído no lado Tcl → ignora silenciosamente
                        return
                    except Exception as e:
                        print(f"[Temas] Falha ao atualizar cor do botão de preview: {e}")

                v.trace_add("write", update_btn)
                return btn

            color_btn = make_color_btn()
            color_btn.pack(side="left")

            color_btn.bind("<Enter>", lambda e, c=campo: self._safe_preview_highlight(c))
            color_btn.bind("<Leave>", lambda e: self._safe_preview_leave())

        separator = ctk.CTkFrame(parent, fg_color=self.app.cor_borda, height=2)
        separator.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(parent, text="Seletor de Cores", font=("Arial", 13, "bold"), text_color=self.app.cor_texto).pack(
            pady=(5, 5))

        self.color_picker = ColorPickerWidget(parent, fg_color=self.app.cor_fundo, corner_radius=6,
                                              callback=self._on_color_selected)
        self.color_picker.pack(fill="x", padx=10, pady=(0, 10))

        nome_frame = ctk.CTkFrame(parent, fg_color="transparent")
        nome_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(nome_frame, text="Nome do Tema:", font=("Arial", 11, "bold"), text_color=self.app.cor_texto).pack(
            anchor="w")

        self.var_nome = tk.StringVar(value="")
        ctk.CTkEntry(nome_frame, textvariable=self.var_nome, font=("Arial", 11), height=32).pack(fill="x", pady=(4, 0))

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 15))

        ctk.CTkButton(btn_frame, text="💾 Salvar Tema", fg_color="#2ecc71", hover_color="#27ae60",
                      command=self._salvar_custom_completo, font=("Arial", 12, "bold"), height=38).pack(fill="x",
                                                                                                        pady=3)

        ctk.CTkButton(btn_frame, text="🔄 Restaurar Original", fg_color="#e74c3c", hover_color="#c0392b",
                      command=self._restaurar_tema, font=("Arial", 12, "bold"), height=38).pack(fill="x", pady=3)

    def _update_live_preview(self):
        """Atualiza o painel de preview com as cores atuais, se ele ainda existir."""
        panel = getattr(self, "preview_panel", None)

        # Se o painel não existe mais (página foi reconstruída), não faz nada
        try:
            if panel is None or not panel.winfo_exists():
                return
        except Exception:
            return

        colors = {}
        for campo, var in self.vars.items():
            val = var.get()
            if _valida_hex(val):
                colors[campo] = val
            else:
                colors[campo] = "#FFFFFF"

        try:
            panel.update_preview(colors)
        except Exception as e:
            # Evita quebrar a aplicação se o painel for destruído no meio do processo
            print(f"Erro ao atualizar preview: {e}")

    def _safe_preview_highlight(self, campo):
        """Destaca um elemento no preview, se o painel ainda existir."""
        panel = getattr(self, "preview_panel", None)
        try:
            if panel is None or not panel.winfo_exists():
                return
            panel.highlight_element(campo)
        except Exception:
            # Não é crítico se o preview não puder ser destacado
            pass

    def _safe_preview_leave(self):
        """Limpa o destaque e atualiza o preview, se o painel ainda existir."""
        panel = getattr(self, "preview_panel", None)
        try:
            if panel is None or not panel.winfo_exists():
                return
            panel.clear_highlight()
            self._update_live_preview()
        except Exception:
            pass

    def _get_contrast_color(self, hex_color):
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#000000" if luminance > 0.5 else "#FFFFFF"
        except:
            return "#FFFFFF"

    def _abrir_seletor_cor(self, campo):
        self.campo_selecionado = campo
        cor_atual = self.vars[campo].get()
        if _valida_hex(cor_atual):
            self.color_picker.set_color(cor_atual)

    def _on_color_selected(self, color):
        if self.campo_selecionado:
            self.vars[self.campo_selecionado].set(color)

    def _get_current_theme(self):
        settings = self._get_app_settings()
        if settings is not None:
            return settings.get("theme", "Noite Urbana")
        return "Noite Urbana"

    def _obter_paleta_tema(self, nome_tema):
        """Retorna a paleta de um tema a partir das fontes conhecidas."""
        if not nome_tema:
            return None

        theme_manager = getattr(self.app, "theme_manager", None) or getattr(self.app, "_theme_manager", None)

        if hasattr(self, "custom") and isinstance(self.custom, dict) and nome_tema in self.custom:
            return self.custom.get(nome_tema)

        if nome_tema in self.PADROES:
            return self.PADROES.get(nome_tema)

        if theme_manager and getattr(theme_manager, "current_theme_name", None) == nome_tema:
            return getattr(theme_manager, "current_palette", None)

        settings = self._get_app_settings()
        if settings and settings.get("theme") == nome_tema:
            return settings.get("last_palette")

        return None

    def _sincronizar_tema_inicial(self):
        """Garante que a página abra já usando o tema ativo do usuário."""
        theme_manager = getattr(self.app, "theme_manager", None) or getattr(self.app, "_theme_manager", None)

        tema_menu = None
        paleta_menu = None
        if theme_manager:
            tema_menu = getattr(theme_manager, "current_theme_name", None)
            paleta_menu = getattr(theme_manager, "current_palette", None)

        tema_externo = getattr(self.app, "tema_atual_global", None) or getattr(self.app, "tema_atual", None)

        if tema_menu:
            self.tema_atual = tema_menu
        elif tema_externo:
            self.tema_atual = tema_externo

        paleta_inicial = paleta_menu or self._obter_paleta_tema(self.tema_atual)
        if paleta_inicial:
            for chave, valor in paleta_inicial.items():
                setattr(self.app, f"cor_{chave}", valor)

            self.configure(fg_color=paleta_inicial.get("fundo", getattr(self.app, "cor_fundo", "#000000")))

    def _render_chip_grid(self, container, nomes, is_padrao=False):
        """Renderiza a grade de chips - VERSÃO CORRIGIDA"""
        for w in container.winfo_children():
            w.destroy()

        for col in range(self.MAX_COLS):
            container.grid_columnconfigure(col, weight=1, uniform="chips")

        for i, nome in enumerate(nomes):
            r = i // self.MAX_COLS
            c = i % self.MAX_COLS

            chip_frame = ctk.CTkFrame(container, fg_color="transparent")
            chip_frame.grid(row=r, column=c, padx=3, pady=2, sticky="ew")

            is_active = (nome == self.tema_atual)

            inner_frame = ctk.CTkFrame(chip_frame, fg_color="transparent")
            inner_frame.pack(fill="both", expand=True)

            chip = _Chip(inner_frame, text=nome,
                         command=lambda n=nome: self._aplicar_e_carregar_tema(n),
                         is_active=is_active,
                         fg_color=self.app.cor_destaque if is_active else self.app.cor_secundaria,
                         hover_color=self.app.cor_hover,
                         text_color=self.app.cor_texto)
            chip.pack(side="left", fill="both", expand=True, padx=(0, 2))

            edit_btn = ctk.CTkButton(inner_frame, text="✏️", width=30, height=26,
                                      fg_color="#3498db", hover_color="#2980b9",
                                      font=("Arial", 16), corner_radius=6,
                                      command=lambda n=nome, p=is_padrao: self._editar_tema(n, p))
            edit_btn.pack(side="right", padx=(2, 0))

            delete_btn = ctk.CTkButton(inner_frame, text="🗑️", width=30, height=26,
                                       fg_color="#e74c3c", hover_color="#c0392b",
                                       font=("Arial", 16), corner_radius=6,
                                       command=lambda n=nome, p=is_padrao: self._excluir_tema(n, p))
            delete_btn.pack(side="right", padx=(2, 0))

    def _aplicar_e_carregar_tema(self, nome):
        self._aplicar_tema_completo(nome)
        self._carregar_tema_no_editor(nome)

    def _editar_tema(self, nome, is_padrao=False):
        """Carrega o tema no editor para edição rápida."""
        self._carregar_tema_no_editor(nome)

        if is_padrao and nome in self.PADROES and nome not in self.custom:
            sugestao = f"{nome} Personalizado"
            contador = 2
            while sugestao in self.custom or sugestao in self.PADROES:
                sugestao = f"{nome} Personalizado {contador}"
                contador += 1
            self.var_nome.set(sugestao)
        else:
            self.var_nome.set(nome)

        self._update_live_preview()

    def _carregar_tema_no_editor(self, nome):
        tema = None
        if nome in self.PADROES:
            tema = self.PADROES[nome]
        elif nome in self.custom:
            tema = self.custom[nome]
        elif hasattr(self, "_obter_paleta_tema"):
            tema = self._obter_paleta_tema(nome)

        if tema:
            for campo in self.CAMPOS:
                if campo in tema:
                    self.vars[campo].set(tema[campo])
            self.var_nome.set(nome)
            self._update_live_preview()

    def _aplicar_tema_completo(self, nome_tema: str) -> bool:
        """
        Aplica o tema visualmente em toda a aplicação e registra no banco
        como TEMA ATUAL do usuário.
        """
        import tkinter as tk
        import customtkinter as ctk

        try:
            if not nome_tema:
                print("⚠️ Nenhum nome de tema recebido em _aplicar_tema_completo.")
                return False

            # --- Descobrir se é tema personalizado ou padrão ---
            is_custom = hasattr(self, "custom") and isinstance(self.custom, dict) and nome_tema in self.custom
            paleta = {}

            if is_custom:
                paleta = self.custom.get(nome_tema, {}) or {}
            elif hasattr(self, "PADROES") and isinstance(self.PADROES, dict):
                # Tema padrão
                paleta = self.PADROES.get(nome_tema, {}) or {}

            # Fallback: tentar nos temas carregados globalmente no app
            if (not paleta) and hasattr(self.app, "gtema") and hasattr(self.app.gtema, "temas_padrao"):
                paleta = self.app.gtema.temas_padrao.get(nome_tema, {}) or {}

            if not paleta:
                print(f"⚠️ Nenhuma paleta encontrada para o tema '{nome_tema}'.")
                return False

            # --- 1) APLICAR TEMA VISUALMENTE ---

            # Atualiza preview da tela de temas, se existir
            try:
                if hasattr(self, "_atualizar_preview"):
                    self._atualizar_preview(paleta)
            except Exception as e:
                print(f"⚠️ Erro ao atualizar preview do tema '{nome_tema}': {e}")

            # Usa o ThemeManager global do MENU_PRINCIPAL, se existir
            try:
                theme_manager = None
                if hasattr(self.app, "theme_manager"):
                    theme_manager = self.app.theme_manager
                elif hasattr(self.app, "_theme_manager"):
                    theme_manager = self.app._theme_manager

                if theme_manager is not None:
                    # ESSA CHAMADA É O QUE FAZ O TEMA SER APLICADO GLOBALMENTE
                    theme_manager.apply_theme(nome_tema, paleta)
                    print(f"✅ Tema aplicado via ThemeManager: {nome_tema}")
                elif hasattr(self, "_aplicar_tema_fallback"):
                    # Fallback interno da página de Temas
                    self._aplicar_tema_fallback(paleta)
                    print(f"✅ Tema aplicado via fallback: {nome_tema}")
            except Exception as e:
                print(f"⚠️ Falha ao aplicar tema globalmente: {e}")

            # Guarda internamente qual tema é o atual
            self.tema_atual = nome_tema

            # --- 2) GRAVAR NO BANCO: CATÁLOGO + PREFERÊNCIAS DO USUÁRIO ---

            try:
                if is_custom:
                    # Garante que o tema personalizado está salvo no catálogo do usuário
                    self._salvar_tema_personalizado_no_banco(nome_tema, paleta)
            except Exception as e:
                print(f"⚠️ Erro ao salvar tema personalizado '{nome_tema}' no banco: {e}")

            try:
                # Sempre salva a preferência do tema atual
                tipo_tema = "personalizado" if is_custom else "padrao"
                self._salvar_preferencia_tema_atual(nome_tema, tipo_tema)
            except Exception as e:
                print(f"⚠️ Erro ao salvar preferência de tema '{nome_tema}': {e}")

            # --- 3) ATUALIZAR LISTA DE TEMAS PERSONALIZADOS NA INTERFACE ---
            try:
                if hasattr(self, "_refresca_custom_chips"):
                    self._refresca_custom_chips()
            except Exception:
                # Não é crítico para o funcionamento
                pass

            # --- 4) ATUALIZAR VISUAL DOS CHIPS (🔥 movimenta a bolinha ●) ---
            try:
                # Atualiza todos os chips visualmente
                self._atualizar_chips_tema(nome_tema)
            except Exception as e:
                print(f"⚠️ Erro ao atualizar chips: {e}")

            # --- 5) NOTIFICAR MENU PRINCIPAL (CRÍTICO PARA SINCRONIZAÇÃO) ---
            try:
                notificacao_sucesso = self._notificar_menu_principal(nome_tema)
                if notificacao_sucesso:
                    print(f"✅ Menu principal sincronizado com tema: {nome_tema}")
                else:
                    print(f"⚠️ Menu principal não pôde ser sincronizado (pode ser normal em demo)")
            except Exception as e:
                print(f"🚨 Erro crítico ao notificar menu principal: {e}")

            # --- 6) ATUALIZAR CONFIGURAÇÕES LOCAIS ---
            try:
                settings = self._get_app_settings()
                if settings is not None:
                    settings["theme"] = nome_tema
                    settings["last_palette"] = paleta
                    try:
                        save_settings(settings)
                    except Exception as e:
                        print(f"⚠️ Erro ao salvar settings: {e}")
                    self._set_app_settings(settings)
            except Exception as e:
                print(f"⚠️ Erro ao atualizar configurações locais: {e}")

            print(f"🎉 Tema '{nome_tema}' aplicado completamente (personalizado={is_custom})")
            return True

        except Exception as e:
            import traceback
            print(f"❌ Erro inesperado em _aplicar_tema_completo('{nome_tema}'): {e}")
            traceback.print_exc()
            return False

    def _atualizar_chips_tema(self, nome_tema_ativo):
        """Atualiza visualmente todos os chips para mostrar qual tema está ativo"""
        try:
            print(f"🔄 Atualizando chips para tema: {nome_tema_ativo}")

            # Atualiza chips de temas padrão
            for widget in self.chips_padrao.winfo_children():
                for child in widget.winfo_children():
                    if hasattr(child, 'winfo_children'):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, _Chip):
                                is_active = (grandchild.label_text == nome_tema_ativo)
                                grandchild.set_active(is_active)
                                if is_active:
                                    print(f"✅ Chip ativado: {grandchild.label_text}")

            # Atualiza chips de temas personalizados
            for widget in self.user_chips.winfo_children():
                for child in widget.winfo_children():
                    if hasattr(child, 'winfo_children'):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, _Chip):
                                is_active = (grandchild.label_text == nome_tema_ativo)
                                grandchild.set_active(is_active)
                                if is_active:
                                    print(f"✅ Chip personalizado ativado: {grandchild.label_text}")

            print("🎯 Chips atualizados com sucesso")

        except Exception as e:
            print(f"❌ Erro ao atualizar chips: {e}")

    def _aplicar_tema_fallback(self, pal):
        import tkinter as tk
        import customtkinter as ctk

        sidebar = getattr(self.app, "sidebar", None)
        topbar = getattr(self.app, "topbar", None)
        main = getattr(self.app, "main", None)
        content = getattr(self.app, "content", None)

        def process(widget):
            try:
                if isinstance(widget, ctk.CTkLabel):
                    widget.configure(text_color=pal.get("texto", "#FFFFFF"))

                elif isinstance(widget, ctk.CTkButton):
                    cfg = {
                        "fg_color": pal.get("secundaria", "#2C2C2C"),
                        "hover_color": pal.get("hover", "#3A3A3A"),
                        "text_color": pal.get("texto", "#FFFFFF"),
                        "border_color": pal.get("borda", "#333333"),
                    }
                    if widget.cget("fg_color") == "transparent":
                        cfg.pop("fg_color", None)
                    widget.configure(**cfg)

                elif isinstance(widget, ctk.CTkEntry):
                    widget.configure(
                        fg_color=pal.get("secundaria", "#2C2C2C"),
                        text_color=pal.get("texto", "#FFFFFF"),
                        border_color=pal.get("borda", "#333333"),
                    )

                elif isinstance(widget, ctk.CTkScrollableFrame):
                    widget.configure(
                        fg_color=pal.get("primaria", "#1F1F1F"),
                        border_color=pal.get("borda", "#333333"),
                    )

                elif isinstance(widget, ctk.CTkFrame):
                    if widget is sidebar or widget is topbar:
                        widget.configure(
                            fg_color=pal.get("primaria", "#1F1F1F"),
                            border_color=pal.get("borda", "#333333"),
                        )
                    elif widget is main or widget is content:
                        widget.configure(
                            fg_color=pal.get("fundo", "#181818"),
                            border_color=pal.get("borda", "#333333"),
                        )
                    else:
                        widget.configure(
                            fg_color=pal.get("primaria", "#1F1F1F"),
                            border_color=pal.get("borda", "#333333"),
                        )

                elif isinstance(widget, tk.Frame):
                    widget.configure(bg=pal.get("fundo", "#181818"))
                elif isinstance(widget, tk.Label):
                    widget.configure(
                        bg=pal.get("fundo", "#181818"),
                        fg=pal.get("texto", "#FFFFFF"),
                    )
                elif isinstance(widget, tk.Button):
                    widget.configure(
                        bg=pal.get("secundaria", "#2C2C2C"),
                        fg=pal.get("texto", "#FFFFFF"),
                        activebackground=pal.get("hover", "#3A3A3A"),
                    )
            except Exception:
                pass

            try:
                for child in widget.winfo_children():
                    process(child)
            except Exception:
                pass

        process(self.app)

    def _style_demo_theme(self):
        try:
            self.app.configure(fg_color=self.app.cor_fundo)
        except Exception:
            pass

        def _rec(w):
            for c in getattr(w, 'winfo_children', lambda: [])():
                try:
                    import customtkinter as ctk
                    if isinstance(c, ctk.CTkLabel):
                        c.configure(text_color=getattr(self.app, 'cor_texto', '#EEE'))
                    elif isinstance(c, ctk.CTkFrame):
                        c.configure(fg_color=getattr(self.app, 'cor_fundo', '#111'))
                    elif isinstance(c, ctk.CTkButton):
                        c.configure(fg_color=getattr(self.app, 'cor_secundaria', '#222'),
                                    hover_color=getattr(self.app, 'cor_hover', '#2C2C2C'),
                                    text_color=getattr(self.app, 'cor_texto', '#EEE'),
                                    border_color=getattr(self.app, 'cor_borda', '#333'))
                    elif isinstance(c, ctk.CTkEntry):
                        c.configure(fg_color=getattr(self.app, 'cor_secundaria', '#1F1F1F'),
                                    text_color=getattr(self.app, 'cor_texto', '#EEE'),
                                    border_color=getattr(self.app, 'cor_borda', '#333'))
                except Exception:
                    pass
                _rec(c)

        _rec(self)

    def _restaurar_tema(self):
        """Restaura o tema original para o tema atual selecionado no editor"""
        nome = (self.var_nome.get() or "").strip()
        if not nome:
            CTkMessagebox(title="Atenção",
                          message="Informe o nome do tema no campo 'Nome do Tema'.",
                          icon="warning")
            return

        if nome not in self.temas_originais:
            CTkMessagebox(title="Atenção",
                          message=f"'{nome}' não é um tema padrão.",
                          icon="warning")
            return

        # Restaura o tema original
        tema_original = self.temas_originais[nome]
        self.PADROES[nome] = dict(tema_original)

        if hasattr(self.app, "gtema"):
            self.app.gtema.temas_padrao[nome] = dict(tema_original)

        # Remove das configurações personalizadas se existir
        settings = self._get_app_settings()
        if settings is not None:
            if "custom_themes" in settings and nome in settings["custom_themes"]:
                del settings["custom_themes"][nome]
                try:
                    save_settings(settings)
                except Exception as e:
                    print(f"Erro ao salvar preferências: {e}")
            self._set_app_settings(settings)

        # Recarrega o tema no editor
        self._carregar_tema_no_editor(nome)

        # Aplica o tema restaurado
        self._aplicar_tema_completo(nome)

        CTkMessagebox(title="Sucesso",
                      message=f"Tema '{nome}' restaurado para as configurações originais.",
                      icon="check")

    def _salvar_custom_completo(self):
        """
        Lê todas as cores da interface, valida, salva:

        - Em self.custom[nome]
        - Em settings locais (settings_manager)
        - No catálogo de temas personalizados do usuário (PostgreSQL)
        - Atualiza os chips
        - E POR FIM aplica o tema globalmente na aplicação.
        """
        nome = (self.var_nome.get() or "").strip()
        if not nome:
            CTkMessagebox(title="Atenção", message="Informe um nome para o tema.", icon="warning")
            return

        # --- Montar paleta a partir dos campos da tela ---
        pal = {}
        for campo, var in self.vars.items():
            val = (var.get() or "").strip()
            if not _valida_hex(val):
                CTkMessagebox(title="Atenção", message=f"Cor inválida: {val}", icon="warning")
                return
            pal[campo] = val.upper()

        # Garante que o dicionário de temas personalizados exista
        if not hasattr(self, "custom") or self.custom is None:
            self.custom = {}

        # Guarda na memória da página de temas
        self.custom[nome] = pal

        # --- 1) Salvar no banco (catálogo de temas personalizados) ---
        salvou_no_banco = False
        try:
            salvou_no_banco = bool(self._salvar_tema_personalizado_no_banco(nome, pal))
        except Exception as e:
            print(f"⚠️ Erro ao salvar tema personalizado '{nome}' no banco: {e}")

        if salvou_no_banco:
            CTkMessagebox(
                title="Sucesso",
                message=f"Tema '{nome}' salvo no banco e localmente!",
                icon="check"
            )
        else:
            CTkMessagebox(
                title="Aviso",
                message=f"Tema '{nome}' salvo localmente, mas não foi possível salvar no banco.",
                icon="warning"
            )

        # --- 2) Salvar nas preferências locais (settings_manager) ---
        settings = self._get_app_settings()
        if settings is not None:
            if "custom_themes" not in settings:
                settings["custom_themes"] = {}
            settings["custom_themes"][nome] = pal
            try:
                save_settings(settings)
            except Exception as e:
                print(f"Erro ao salvar preferências locais: {e}")
            self._set_app_settings(settings)
            self.settings = settings

        # --- 3) Atualizar cache de temas no app (gtema) ---
        if hasattr(self.app, "gtema") and hasattr(self.app.gtema, "temas_padrao"):
            self.app.gtema.temas_padrao[nome] = pal

        # --- 4) Atualizar chips/listas na tela de temas ---
        try:
            if hasattr(self, "_refresca_custom_chips"):
                self._refresca_custom_chips()
        except Exception:
            pass

        try:
            # Re-renderiza os chips de temas padrão também, se a função existir
            if hasattr(self, "_render_chip_grid") and hasattr(self, "chips_padrao") and hasattr(self, "PADROES"):
                self._render_chip_grid(self.chips_padrao, list(self.PADROES.keys()), is_padrao=True)
        except Exception:
            pass

        # --- 5) Aplicar imediatamente o tema salvo em TODA a aplicação ---
        self._aplicar_tema_completo(nome)

    def _salvar_tema_no_banco(self, nome_tema: str, pal: dict):
        """
        Salva ou atualiza um tema (paleta completa) na tabela
        opera.usuario_temas_personalizados, de forma que fique
        disponível para o usuário em qualquer máquina da rede.
        """
        if not hasattr(self.app, 'db') or self.app.db is None:
            print("⚠️ Sem banco para salvar tema.")
            return False

        try:
            usuario_id = getattr(self.app, "usuario_id", None) or 0
            cores_json = json.dumps(pal, ensure_ascii=False)

            query_salvar_tema = """
                INSERT INTO opera.usuario_temas_personalizados (
                    usuario_id, nome_tema, cores_tema, data_criacao
                ) VALUES (%s, %s, %s, NOW())
                ON CONFLICT (usuario_id, nome_tema) DO UPDATE
                SET cores_tema = EXCLUDED.cores_tema,
                    data_criacao = NOW()
            """

            self.app.db.cursor.execute(query_salvar_tema, (usuario_id, nome_tema, cores_json))
            self.app.db.connection.commit()
            print(f"💾 Tema '{nome_tema}' salvo/atualizado no banco.")
            return True

        except Exception as exc:
            print(f"❌ Erro ao salvar tema no banco: {exc}")
            try:
                self.app.db.connection.rollback()
            except Exception:
                pass
            return False

    def _salvar_tema_personalizado_no_banco(self, nome_tema: str, paleta: dict) -> bool:
        """
        Força a persistência de um tema personalizado no catálogo do usuário.

        Tabela esperada:   opera.usuario_temas_personalizados
            - usuario_id
            - nome_tema
            - cores_tema (JSON)
            - atualizado_em (timestamp)
        """
        import json
        from BANCO_DE_DADOS_PG import get_conn, get_schema

        conn = None

        try:
            usuario_id = getattr(self.app, "usuario_id", None)
            if not usuario_id:
                print("⚠️ Usuário sem ID, não é possível salvar tema personalizado.")
                return False

            schema = get_schema()

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.usuario_temas_personalizados
                            (usuario_id, nome_tema, cores_tema, atualizado_em)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (usuario_id, nome_tema)
                        DO UPDATE SET
                            cores_tema    = EXCLUDED.cores_tema,
                            atualizado_em = NOW();
                        """,
                        (usuario_id, nome_tema, json.dumps(paleta, ensure_ascii=False)),
                    )
                conn.commit()

            print(f"💾 Tema personalizado '{nome_tema}' gravado/atualizado com sucesso no banco.")
            return True

        except Exception as e:
            import traceback
            print(f"❌ Erro ao salvar tema personalizado '{nome_tema}': {e}")
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass
            traceback.print_exc()
            return False

    def _salvar_preferencia_tema_atual(self, nome_tema, tipo_tema="padrao"):
        """
        Salva no banco a preferência de tema atual do usuário.

        Usa a tabela opera.usuario_preferencias com as colunas:
            - tema_nome
            - usar_tema_personalizado
            - tema_personalizado (JSON com a paleta completa, quando personalizado)
            - atualizado_em
        """
        import json
        from BANCO_DE_DADOS_PG import get_conn, get_schema

        try:
            usuario_id = getattr(self.app, 'usuario_id', None)
            if not usuario_id:
                print("⚠️ Usuário sem ID para salvar preferência de tema.")
                return False

            usar_tema_personalizado = str(tipo_tema).lower() == "personalizado"
            tema_personalizado_json = None

            # Quando for tema personalizado, salvamos a paleta completa em JSON
            if usar_tema_personalizado:
                paleta = None

                # Tenta primeiro na lista de temas personalizados carregados
                if hasattr(self, "custom") and isinstance(self.custom, dict):
                    paleta = self.custom.get(nome_tema)

                # Fallback: tenta buscar no gerenciador global de temas, se existir
                if paleta is None and hasattr(self.app, "gtema") and hasattr(self.app.gtema, "temas_padrao"):
                    paleta = self.app.gtema.temas_padrao.get(nome_tema)

                if paleta is not None:
                    try:
                        tema_personalizado_json = json.dumps(paleta, ensure_ascii=False)
                    except Exception as e:
                        print(f"⚠️ Erro ao serializar paleta do tema '{nome_tema}': {e}")
                        tema_personalizado_json = None

            conn = get_conn()
            if not conn:
                print("⚠️ Conexão com banco não disponível para salvar preferência de tema.")
                return False

            schema = get_schema()

            query_salvar_preferencia = (
                f"INSERT INTO {schema}.usuario_preferencias "
                f"    (usuario_id, tema_nome, usar_tema_personalizado, tema_personalizado, atualizado_em) "
                f"VALUES (%s, %s, %s, %s, NOW()) "
                f"ON CONFLICT (usuario_id) DO UPDATE SET "
                f"    tema_nome = EXCLUDED.tema_nome, "
                f"    usar_tema_personalizado = EXCLUDED.usar_tema_personalizado, "
                f"    tema_personalizado = EXCLUDED.tema_personalizado, "
                f"    atualizado_em = NOW()"
            )

            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        query_salvar_preferencia,
                        (usuario_id, nome_tema, usar_tema_personalizado, tema_personalizado_json)
                    )

            print(f"✅ Preferência de tema salva: {nome_tema} (personalizado={usar_tema_personalizado})")

            # Persiste localmente para manter consistência mesmo sem banco
            try:
                settings = self._get_app_settings()
                if settings is not None:
                    settings["theme"] = nome_tema
                    if usar_tema_personalizado and tema_personalizado_json:
                        settings["last_palette"] = json.loads(tema_personalizado_json)
                    save_settings(settings)
                    self._set_app_settings(settings)
            except Exception as e:
                print(f"⚠️ Não foi possível registrar preferência de tema localmente: {e}")
            return True

        except Exception as e:
            print(f"❌ Erro ao salvar preferência de tema: {e}")
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass
            return False

    def _carregar_preferencia_tema_atual(self):
        """Carrega a preferência de tema atual do banco.

        Retorna:
            (tema_nome, tipo_tema) ou None se não houver registro.
            tipo_tema será "personalizado" ou "padrao".
        """
        try:
            if not hasattr(self.app, 'db') or self.app.db is None:
                return None

            if not hasattr(self.app.db, 'cursor') or self.app.db.cursor is None:
                return None

            usuario_id = getattr(self.app, 'usuario_id', None)
            if not usuario_id:
                return None

            query_carregar_preferencia = (
                "SELECT tema_nome, "
                "       COALESCE(usar_tema_personalizado, FALSE) AS usar_tema_personalizado "
                "FROM opera.usuario_preferencias "
                "WHERE usuario_id = %s"
            )

            self.app.db.cursor.execute(query_carregar_preferencia, (usuario_id,))
            resultado = self.app.db.cursor.fetchone()

            if resultado:
                tema_nome, usar_tema_personalizado = resultado
                if not tema_nome:
                    return None

                tipo_tema = "personalizado" if usar_tema_personalizado else "padrao"
                return tema_nome, tipo_tema

            return None

        except Exception as e:
            print(f"❌ Erro ao carregar preferência de tema: {e}")
            return None

    def load_user_theme_completo(self, default_theme: str = "Noite Urbana"):
        """
        Carrega o tema completo do usuário (nome + paleta opcional).

        Retorno:
            (tema_nome, paleta_dict_ou_None)

        Lógica:
            - Lê opera.usuario_preferencias:
                tema_nome, usar_tema_personalizado, tema_personalizado
            - Faz LEFT JOIN em opera.usuario_temas_personalizados para pegar cores_tema.
            - Se usar_tema_personalizado = TRUE:
                tenta pegar a paleta em usuario_temas_personalizados.cores_tema
                (JSONB com todas as cores do tema).
            - Se não encontrar, tenta fallback em usuario_preferencias.tema_personalizado (modelo antigo).
            - Se não for personalizado, retorna só o nome do tema e paleta = None.
        """
        import json

        # Se o usuário não está definido, usa tema padrão
        if not getattr(self.app, "usuario_id", None):
            print("[Tema] Usuário sem ID, aplicando tema padrão.")
            return default_theme, None

        try:
            # Importa aqui dentro para evitar aviso de "unresolved reference"
            from BANCO_DE_DADOS_PG import get_conn, get_schema
        except Exception as e:
            print(f"[Tema] Banco de dados indisponível ao carregar tema: {e}")
            return default_theme, None

        try:
            schema = get_schema()
            query = f"""
                SELECT
                    COALESCE(up.tema_nome, u.tema_preferido, %s) AS tema_nome,
                    COALESCE(up.usar_tema_personalizado, FALSE) AS usar_tema_personalizado,
                    up.tema_personalizado,
                    ut.cores_tema
                FROM {schema}.usuarios u
                LEFT JOIN {schema}.usuario_preferencias up
                    ON u.id = up.usuario_id
                LEFT JOIN {schema}.usuario_temas_personalizados ut
                    ON ut.usuario_id = u.id
                   AND ut.nome_tema = up.tema_nome
                WHERE u.id = %s
            """

            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(query, (default_theme, self.app.usuario_id))
                row = cur.fetchone()
                if not row:
                    print("[Tema] Nenhuma preferência encontrada, usando tema padrão.")
                    return default_theme, None

                tema_nome, usar_custom, tema_json_antigo, cores_tema_db = row

                # Se o usuário está marcado para usar tema personalizado
                if usar_custom:
                    paleta = None

                    # 1) Tenta usar a nova tabela usuario_temas_personalizados (cores_tema)
                    if cores_tema_db:
                        try:
                            if isinstance(cores_tema_db, (dict, list)):
                                paleta = cores_tema_db
                            else:
                                paleta = json.loads(cores_tema_db)
                            print("[Tema] Paleta personalizada carregada de usuario_temas_personalizados.")
                        except Exception as erro_json:
                            print(f"[Tema] Erro ao decodificar cores_tema: {erro_json}")

                    # 2) Fallback: coluna antiga tema_personalizado (JSON em usuario_preferencias)
                    if paleta is None and tema_json_antigo:
                        try:
                            paleta = json.loads(tema_json_antigo)
                            print("[Tema] Paleta personalizada carregada de usuario_preferencias.tema_personalizado.")
                        except json.JSONDecodeError:
                            print("[Tema] JSON inválido em tema_personalizado, usando só nome do tema.")

                    return tema_nome, paleta

                # Não é personalizado → só o nome mesmo
                return tema_nome, None

        except Exception as e:
            print(f"[UserManager] Erro ao carregar tema completo do usuário: {e}")
            import traceback
            traceback.print_exc()
            return default_theme, None

    def _excluir_tema(self, nome, is_padrao=False):
        """Exclui um tema (padrão ou personalizado) APENAS para o usuário atual"""
        # Confirmação de exclusão
        tipo = "padrão" if is_padrao else "personalizado"
        msg = CTkMessagebox(title="Confirmar Exclusão",
                            message=f"Deseja realmente excluir o tema '{nome}' ({tipo})?",
                            icon="question",
                            option_1="Cancelar",
                            option_2="Excluir")

        if msg.get() != "Excluir":
            return

        if is_padrao:
            # Exclusão de tema padrão: remove da lista atual (apenas para este usuário)
            if nome in self.PADROES:
                del self.PADROES[nome]

            # Adiciona à lista de excluídos nas configurações
            settings = self._get_app_settings()
            if settings is None:
                settings = {"theme": "Noite Urbana", "custom_themes": {}, "excluded_default_themes": []}

            if "excluded_default_themes" not in settings:
                settings["excluded_default_themes"] = []
            if nome not in settings["excluded_default_themes"]:
                settings["excluded_default_themes"].append(nome)

        else:
            # Exclusão de tema personalizado: remove APENAS para este usuário
            if nome in self.custom:
                del self.custom[nome]

            # ✅ REMOVER DO BANCO (apenas para este usuário)
            self._remover_tema_do_banco(nome)

            # Remove das configurações locais (apenas deste usuário)
            settings = self._get_app_settings()
            if settings is not None and "custom_themes" in settings and nome in settings["custom_themes"]:
                del settings["custom_themes"][nome]

        # Salva configurações
        try:
            save_settings(settings)
            self._set_app_settings(settings)
            self.settings = settings
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")

        # Se o tema excluído estava ativo, aplica um tema disponível
        if self.tema_atual == nome:
            temas_disponiveis = list(self.PADROES.keys()) + list(self.custom.keys())
            if temas_disponiveis:
                self._aplicar_tema_completo(temas_disponiveis[0])

        # Atualiza interface
        self._refresca_custom_chips()
        self._render_chip_grid(self.chips_padrao, list(self.PADROES.keys()), is_padrao=True)

        CTkMessagebox(title="Sucesso",
                      message=f"Tema '{nome}' excluído com sucesso!\n\nEste tema foi removido apenas do seu usuário.",
                      icon="check")

    def _remover_tema_do_banco(self, nome_tema):
        try:
            if not hasattr(self.app, 'db') or self.app.db is None:
                return False

            if not hasattr(self.app.db, 'cursor') or self.app.db.cursor is None:
                return False

            usuario_id = getattr(self.app, 'usuario_id', None)
            if not usuario_id:
                return False

            query_remover_tema = """
            DELETE FROM opera.usuario_temas_personalizados 
            WHERE usuario_id = %s AND nome_tema = %s
            """

            self.app.db.cursor.execute(query_remover_tema, (usuario_id, nome_tema))

            if hasattr(self.app.db, 'connection') and self.app.db.connection:
                self.app.db.connection.commit()

            print(f"✅ Tema '{nome_tema}' removido do banco para usuário {usuario_id}")
            return True

        except Exception as e:
            print(f"❌ Erro ao remover tema do banco: {e}")
            return False

    def _restaurar_temas_padrao(self):
        """Restaura todos os temas padrão originais"""
        # Confirmação
        msg = CTkMessagebox(title="Confirmar Restauração",
                            message="Deseja restaurar todos os temas padrão?\n\nIsso irá recuperar todos os temas padrão que foram excluídos.",
                            icon="question",
                            option_1="Cancelar",
                            option_2="Restaurar")

        if msg.get() != "Restaurar":
            return

        # Restaura todos os temas padrão originais
        self.PADROES = dict(self.temas_originais)

        # Atualiza gtema se existir
        if hasattr(self.app, "gtema"):
            self.app.gtema.temas_padrao.update(self.PADROES)

        settings = self._get_app_settings()
        if settings is None:
            settings = {}
        settings["excluded_default_themes"] = []
        try:
            save_settings(settings)
        except Exception as e:
            print(f"Erro ao salvar preferências: {e}")
        self._set_app_settings(settings)

        # Atualiza a interface
        self._render_chip_grid(self.chips_padrao, list(self.PADROES.keys()), is_padrao=True)

        CTkMessagebox(title="Sucesso",
                      message=f"{len(self.PADROES)} temas padrão restaurados com sucesso!",
                      icon="check")

    def _refresca_custom_chips(self):
        self._render_chip_grid(self.user_chips, sorted(self.custom.keys()), is_padrao=False)

    def _notificar_menu_principal(self, nome_tema):
        """Notifica o menu principal sobre a mudança de tema usando múltiplas estratégias"""
        try:
            print(f"🔔 Notificando menu principal sobre tema: {nome_tema}")

            sucesso = False

            # ESTRATÉGIA 1: Buscar menu principal diretamente no app
            menu_principal = None

            # Tentar encontrar por atributos comuns
            for attr_name in ['menu_principal', '_menu_principal', 'main_menu', 'menu', 'sidebar', 'nav_frame']:
                if hasattr(self.app, attr_name):
                    menu_principal = getattr(self.app, attr_name)
                    if menu_principal:
                        print(f"✅ Menu encontrado via atributo: {attr_name}")
                        break

            # ESTRATÉGIA 2: Buscar recursivamente por componentes do menu
            if menu_principal is None:
                def buscar_componente_menu(widget):
                    # Verifica se é um componente de menu por classe ou atributos
                    class_name = widget.__class__.__name__.lower()
                    if any(keyword in class_name for keyword in ['menu', 'sidebar', 'nav', 'frame']):
                        # Verifica se tem métodos de menu
                        if (hasattr(widget, 'temas_disponiveis') or
                                hasattr(widget, 'aplicar_tema') or
                                hasattr(widget, 'menu_temas')):
                            return widget

                    # Busca nos filhos
                    for child in widget.winfo_children():
                        result = buscar_componente_menu(child)
                        if result:
                            return result
                    return None

                menu_principal = buscar_componente_menu(self.app)
                if menu_principal:
                    print("✅ Menu encontrado via busca recursiva")

            # ESTRATÉGIA 3: Buscar através do theme_manager
            if menu_principal is None and hasattr(self.app, 'theme_manager'):
                theme_manager = self.app.theme_manager
                for attr_name in ['menu_principal', '_menu_principal', 'main_menu']:
                    if hasattr(theme_manager, attr_name):
                        menu_principal = getattr(theme_manager, attr_name)
                        if menu_principal:
                            print(f"✅ Menu encontrado via theme_manager: {attr_name}")
                            break

            # ESTRATÉGIA 4: Tentar métodos específicos do app
            if menu_principal is None:
                for method_name in ['get_menu_principal', 'obter_menu', 'get_main_menu']:
                    if hasattr(self.app, method_name):
                        try:
                            menu_principal = getattr(self.app, method_name)()
                            if menu_principal:
                                print(f"✅ Menu encontrado via método: {method_name}")
                                break
                        except:
                            continue

            # SE ENCONTROU O MENU: Tentar atualizar
            if menu_principal:
                print(f"🎯 Tentando atualizar menu principal: {type(menu_principal)}")

                # Método 1: Método específico para atualizar tema selecionado
                if hasattr(menu_principal, 'atualizar_tema_selecionado'):
                    try:
                        menu_principal.atualizar_tema_selecionado(nome_tema)
                        sucesso = True
                        print(f"✅ Menu atualizado via 'atualizar_tema_selecionado'")
                    except Exception as e:
                        print(f"❌ Erro em 'atualizar_tema_selecionado': {e}")

                # Método 2: Método para aplicar tema
                if not sucesso and hasattr(menu_principal, 'aplicar_tema'):
                    try:
                        menu_principal.aplicar_tema(nome_tema)
                        sucesso = True
                        print(f"✅ Menu atualizado via 'aplicar_tema'")
                    except Exception as e:
                        print(f"❌ Erro em 'aplicar_tema': {e}")

                # Método 3: Atualizar atributo diretamente
                if not sucesso and hasattr(menu_principal, 'tema_atual'):
                    try:
                        menu_principal.tema_atual = nome_tema
                        sucesso = True
                        print(f"✅ Atributo 'tema_atual' atualizado")
                    except Exception as e:
                        print(f"❌ Erro ao atualizar atributo: {e}")

                # Método 4: Forçar refresh do menu de temas
                if not sucesso and hasattr(menu_principal, 'menu_temas'):
                    try:
                        self._atualizar_menu_temas_diretamente(menu_principal, nome_tema)
                        sucesso = True
                        print(f"✅ Menu de temas atualizado diretamente")
                    except Exception as e:
                        print(f"❌ Erro ao atualizar menu diretamente: {e}")

            # ESTRATÉGIA 5: Sistema de eventos globais
            if not sucesso:
                sucesso = self._usar_sistema_eventos(nome_tema)

            # ESTRATÉGIA 6: Variável global no app
            if not sucesso:
                try:
                    self.app.tema_atual_global = nome_tema
                    print("✅ Variável global 'tema_atual_global' definida")
                    sucesso = True
                except Exception as e:
                    print(f"❌ Erro ao definir variável global: {e}")

            # RESULTADO FINAL
            if sucesso:
                print(f"🎉 Menu principal notificado com sucesso: {nome_tema}")
            else:
                print("⚠️ Menu principal não pôde ser notificado (pode ser normal em modo demo)")

            return sucesso

        except Exception as e:
            print(f"🚨 Erro crítico ao notificar menu principal: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _atualizar_menu_temas_diretamente(self, menu_principal, nome_tema):
        """Atualiza o menu de temas diretamente se possível"""
        try:
            if hasattr(menu_principal, 'menu_temas') and menu_principal.menu_temas:
                # Remove todos os itens do menu
                menu_temas = menu_principal.menu_temas
                menu_temas.delete(0, 'end')

                # Re-adiciona com o checkmark correto
                temas_disponiveis = getattr(menu_principal, 'temas_disponiveis', [])
                for tema in temas_disponiveis:
                    is_selected = (tema == nome_tema)
                    checkmark = "✓ " if is_selected else "  "

                    # Usa o método aplicar_tema se existir, senão usa command padrão
                    if hasattr(menu_principal, 'aplicar_tema'):
                        menu_temas.add_command(
                            label=f"{checkmark}{tema}",
                            command=lambda t=tema: menu_principal.aplicar_tema(t)
                        )
                    else:
                        # Fallback: tenta encontrar um método padrão
                        menu_temas.add_command(
                            label=f"{checkmark}{tema}",
                            command=lambda t=tema: print(f"Tema selecionado: {t}")
                        )

                return True
        except Exception as e:
            print(f"❌ Erro ao atualizar menu diretamente: {e}")

        return False

    def _usar_sistema_eventos(self, nome_tema):
        """Usa sistema de eventos para notificar mudança de tema"""
        try:
            # Método 1: Evento Tkinter personalizado
            if hasattr(self.app, 'event_generate'):
                self.app.event_generate('<<TemaAlterado>>', when='tail')
                print("✅ Evento '<<TemaAlterado>>' gerado")

            # Método 2: Atributo no theme_manager
            if hasattr(self.app, 'theme_manager'):
                theme_manager = self.app.theme_manager
                theme_manager.tema_atual = nome_tema
                print("✅ Tema atual definido no theme_manager")

            # Método 3: Sinal via dicionário de configurações
            if hasattr(self.app, '_settings'):
                self.app._settings['theme'] = nome_tema
                print("✅ Tema atual definido nas settings")

            return True

        except Exception as e:
            print(f"❌ Erro no sistema de eventos: {e}")
            return False


if __name__ == '__main__':
    """
    PONTO DE ENTRADA PRINCIPAL DA APLICAÇÃO
    Este arquivo é uma aplicação GUI, não um arquivo de testes.
    """

    print("🚀 INICIANDO SISTEMA DE TEMAS...")
    print("📁 Este é um arquivo de aplicação GUI, não de testes")

    # Configuração básica da aplicação
    ctk.set_appearance_mode('dark')
    app = ctk.CTk()
    app.title('Sistema de Temas - Opera')

    # Configurações padrão para demonstração
    app._settings = {
        "theme": "Noite Urbana",
        "custom_themes": {},
        "excluded_default_themes": []
    }

    # Aplica tema padrão
    base = TemasPage.PADROES['Noite Urbana']
    for k, v in base.items():
        setattr(app, f'cor_{k}', v)


    # Simula conexão com banco para testes (apenas para demonstração)
    class MockDatabase:
        """Simulação de conexão com banco para demonstração"""

        def __init__(self):
            self.cursor = self.MockCursor()
            self.connection = self.MockConnection()

        class MockCursor:
            def execute(self, query, params=None):
                print(f"📝 [MOCK] Executando query: {query[:50]}...")
                return True

            def fetchone(self):
                # Simula que não há tema salvo no banco
                return None

            def fetchall(self):
                return []

        class MockConnection:
            def commit(self):
                print("✅ [MOCK] Commit simulado")
                return True

            def rollback(self):
                print("🔄 [MOCK] Rollback simulado")
                return True


    # Configura ambiente de demonstração
    app.db = MockDatabase()
    app.usuario_id = 1  # ID de usuário simulado para testes

    print("🎨 Criando interface de temas...")

    try:
        # Cria a página de temas
        page = TemasPage(app)
        page.pack(fill='both', expand=True, padx=20, pady=20)

        # Configuração da janela
        desired_w, desired_h = 1400, 800
        screen_w, screen_h = app.winfo_screenwidth(), app.winfo_screenheight()
        x = (screen_w - desired_w) // 2
        y = (screen_h - desired_h) // 2
        app.geometry(f'{desired_w}x{desired_h}+{x}+{y}')
        app.minsize(1200, 700)

        # Adiciona informações de status
        status_frame = ctk.CTkFrame(app, fg_color="transparent")
        status_frame.pack(side="bottom", fill="x", padx=20, pady=10)

        status_label = ctk.CTkLabel(
            status_frame,
            text="🔧 Modo Demonstração - Sistema de Temas Opera",
            font=("Arial", 10),
            text_color="#888888"
        )
        status_label.pack(side="left")


        # Contador de temas disponíveis
        def atualizar_contador():
            try:
                temas_padrao = len(page.PADROES)
                temas_personalizados = len(page.custom)
                total_temas = temas_padrao + temas_personalizados

                contador_text = f"🎨 Temas: {temas_padrao} padrão + {temas_personalizados} personalizados = {total_temas} total"
                contador_label.configure(text=contador_text)
            except Exception as e:
                print(f"Erro ao atualizar contador: {e}")


        contador_label = ctk.CTkLabel(
            status_frame,
            text="Carregando...",
            font=("Arial", 10),
            text_color="#4ECDC4"
        )
        contador_label.pack(side="right")


        # Atualiza contador periodicamente
        def atualizar_periodicamente():
            atualizar_contador()
            app.after(3000, atualizar_periodicamente)


        app.after(1000, atualizar_periodicamente)

        # Painel de controles de demonstração
        controles_frame = ctk.CTkFrame(app, fg_color="transparent")
        controles_frame.pack(side="bottom", fill="x", padx=20, pady=5)


        # Funções de demonstração
        def demonstrar_salvamento():
            """Demonstra o processo de salvamento"""
            print("\n" + "=" * 50)
            print("🧪 DEMONSTRAÇÃO DE SALVAMENTO")
            print("=" * 50)

            # Simula um tema de teste
            tema_teste = {
                "primaria": "#1A1A1A",
                "secundaria": "#2D2D2D",
                "terciaria": "#3A3A3A",
                "fundo": "#121212",
                "texto": "#FFFFFF",
                "destaque": "#3A86FF",
                "sucesso": "#4CAF50",
                "alerta": "#F44336",
                "borda": "#333333",
                "hover": "#2A2A2A",
                "selecao": "#3A86FF"
            }

            print("🎨 Aplicando tema de teste...")
            page._aplicar_tema_fallback(tema_teste)

            print("💾 Simulando salvamento no banco...")
            resultado = page._salvar_tema_personalizado_no_banco("Tema Demonstração", tema_teste)

            if resultado:
                print("✅ Salvamento simulado com sucesso!")
            else:
                print("⚠️ Salvamento apenas local (banco simulado)")

            print("=" * 50)


        def demonstrar_carregamento():
            """Demonstra o processo de carregamento"""
            print("\n" + "=" * 50)
            print("🔄 DEMONSTRAÇÃO DE CARREGAMENTO")
            print("=" * 50)

            print("📥 Simulando carregamento do banco...")
            resultado = page._carregar_temas_do_banco()

            if resultado:
                print("✅ Carregamento simulado com sucesso!")
            else:
                print("ℹ️ Nenhum tema encontrado no banco simulado")

            print("=" * 50)


        def ciclar_temas():
            """Alterna entre temas automaticamente"""
            temas = list(page.PADROES.keys())
            if hasattr(page, 'tema_atual') and page.tema_atual in temas:
                index = temas.index(page.tema_atual)
                proximo_tema = temas[(index + 1) % len(temas)]
                print(f"🎨 Alternando para: {proximo_tema}")
                page._aplicar_tema_completo(proximo_tema)
            else:
                page._aplicar_tema_completo(temas[0])


        # Botões de controle
        ctk.CTkButton(
            controles_frame,
            text="💾 Demo Salvamento",
            command=demonstrar_salvamento,
            width=140,
            height=30,
            fg_color="#3498db",
            hover_color="#2980b9"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            controles_frame,
            text="🔄 Demo Carregamento",
            command=demonstrar_carregamento,
            width=140,
            height=30,
            fg_color="#9b59b6",
            hover_color="#8e44ad"
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            controles_frame,
            text="🎨 Ciclar Temas",
            command=ciclar_temas,
            width=120,
            height=30,
            fg_color="#e67e22",
            hover_color="#d35400"
        ).pack(side="left", padx=5)


        def mostrar_info():
            """Mostra informações do sistema"""
            print("\n" + "=" * 50)
            print("📊 INFORMAÇÕES DO SISTEMA")
            print("=" * 50)
            print(f"🎯 Tema atual: {getattr(page, 'tema_atual', 'N/A')}")
            print(f"📁 Temas padrão: {len(page.PADROES)}")
            print(f"💾 Temas personalizados: {len(page.custom)}")
            print(f"🔗 Banco simulado: {hasattr(app, 'db')}")
            print(f"👤 Usuário ID: {getattr(app, 'usuario_id', 'N/A')}")
            print("=" * 50)


        ctk.CTkButton(
            controles_frame,
            text="📊 Informações",
            command=mostrar_info,
            width=120,
            height=30,
            fg_color="#2ecc71",
            hover_color="#27ae60"
        ).pack(side="left", padx=5)


        # Configuração de estilo
        def aplicar_estilo():
            try:
                page._style_demo_theme()
                app.configure(fg_color=app.cor_fundo)
                print("🎨 Estilo aplicado com sucesso!")
            except Exception as e:
                print(f"⚠️ Erro ao aplicar estilo: {e}")


        # Bind para fechar
        def fechar_app(event=None):
            print("\n👋 Encerrando demonstração...")
            app.quit()


        app.bind('<Escape>', fechar_app)
        app.protocol("WM_DELETE_WINDOW", fechar_app)

        # Mensagem inicial
        print("\n" + "=" * 60)
        print("🎭 SISTEMA DE TEMAS OPERA - MODO DEMONSTRAÇÃO")
        print("=" * 60)
        print("📋 Este arquivo é uma APLICAÇÃO GUI, não um arquivo de testes.")
        print("   Para executar testes, use arquivos com prefixo 'test_'")
        print("")
        print("🎮 Controles disponíveis:")
        print("   • 💾 Demo Salvamento - Testa salvamento de temas")
        print("   • 🔄 Demo Carregamento - Testa carregamento do banco")
        print("   • 🎨 Ciclar Temas - Alterna entre temas automaticamente")
        print("   • 📊 Informações - Mostra status do sistema")
        print("   • ESC - Fechar aplicação")
        print("")
        print("🔧 Configuração:")
        print("   • Banco de dados: SIMULADO (apenas para testes)")
        print("   • Temas carregados: Simulação completa")
        print("=" * 60)

        # Aplica estilo após inicialização
        app.after(1000, aplicar_estilo)
        app.after(2000, mostrar_info)

        print("🚀 Interface carregada com sucesso!")
        print("📍 Dica: Use os botões na parte inferior para testar funcionalidades")

        # Inicia loop principal
        app.mainloop()

    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
        print("💡 Possíveis soluções:")
        print("   - Verifique se todas as dependências estão instaladas")
        print("   - Execute como script principal, não como teste")
        print("   - Use: python TEMAS.py")

    finally:
        print("\n👋 Demonstração finalizada")
        print("📝 Para integrar no sistema principal, importe a classe TemasPage")

else:
    # Quando importado como módulo no sistema principal
    print("📦 Módulo de Temas carregado para o sistema Opera")