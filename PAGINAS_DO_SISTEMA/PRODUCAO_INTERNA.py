# -*- coding: utf-8 -*-
import customtkinter as ctk

class ProducaoInternaPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.lbl = ctk.CTkLabel(self, text="Produção Interna")
        self.lbl.pack(padx=20, pady=20)

try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    attach_i18n_support(ProducaoInternaPage, {
        "pt_BR": {"Produção Interna": "Produção Interna"},
        "en_US": {"Produção Interna": "Internal Production"},
        "es_ES": {"Produção Interna": "Producción Interna"},
    })
except Exception:
    pass
