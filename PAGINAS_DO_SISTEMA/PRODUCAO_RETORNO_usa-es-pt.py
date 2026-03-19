# -*- coding: utf-8 -*-
import customtkinter as ctk

from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support


class ProducaoRetornoPage(ctk.CTkFrame):
    TRANSLATIONS = {
        "pt_BR": {
            "Produção Retorno": "Produção Retorno",
            "Painel de Produção Retorno": "Painel de Produção Retorno",
        },
        "en_US": {
            "Produção Retorno": "Production Return",
            "Painel de Produção Retorno": "Production Return Panel",
        },
        "es_ES": {
            "Produção Retorno": "Producción de Retorno",
            "Painel de Produção Retorno": "Panel de Producción de Retorno",
        },
    }

    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.lbl_titulo = ctk.CTkLabel(self, text="Produção Retorno", font=("Arial", 18, "bold"))
        self.lbl_titulo.pack(padx=20, pady=(20, 8))

        self.lbl_subtitulo = ctk.CTkLabel(self, text="Painel de Produção Retorno")
        self.lbl_subtitulo.pack(padx=20, pady=(0, 20))


attach_i18n_support(ProducaoRetornoPage, ProducaoRetornoPage.TRANSLATIONS)
