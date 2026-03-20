# -*- coding: utf-8 -*-
import customtkinter as ctk

from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support


class ProducaoInternaPage(ctk.CTkFrame):
    TRANSLATIONS = {
        "pt_BR": {
            "Produção Interna": "Produção Interna",
            "Painel de Produção Interna": "Painel de Produção Interna",
        },
        "en_US": {
            "Produção Interna": "Internal Production",
            "Painel de Produção Interna": "Internal Production Panel",
        },
        "es_ES": {
            "Produção Interna": "Producción Interna",
            "Painel de Produção Interna": "Panel de Producción Interna",
        },
    }

    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.lbl_titulo = ctk.CTkLabel(self, text="Produção Interna", font=("Arial", 18, "bold"))
        self.lbl_titulo.pack(padx=20, pady=(20, 8))

        self.lbl_subtitulo = ctk.CTkLabel(self, text="Painel de Produção Interna")
        self.lbl_subtitulo.pack(padx=20, pady=(0, 20))


attach_i18n_support(ProducaoInternaPage, ProducaoInternaPage.TRANSLATIONS)
