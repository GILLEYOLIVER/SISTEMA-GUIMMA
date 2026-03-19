# -*- coding: utf-8 -*-
import customtkinter as ctk

class ProducaoRetornoPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.lbl = ctk.CTkLabel(self, text="Produção Retorno")
        self.lbl.pack(padx=20, pady=20)

try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    attach_i18n_support(ProducaoRetornoPage, {
        "pt_BR": {"Produção Retorno": "Produção Retorno"},
        "en_US": {"Produção Retorno": "Production Return"},
        "es_ES": {"Produção Retorno": "Producción Retorno"},
    })
except Exception:
    pass
