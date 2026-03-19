# -*- coding: utf-8 -*-
import customtkinter as ctk

class ProducaoFinalizadosPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.lbl = ctk.CTkLabel(self, text="Produção Finalizados")
        self.lbl.pack(padx=20, pady=20)

try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    attach_i18n_support(ProducaoFinalizadosPage, {
        "pt_BR": {"Produção Finalizados": "Produção Finalizados"},
        "en_US": {"Produção Finalizados": "Production Finished"},
        "es_ES": {"Produção Finalizados": "Producción Finalizados"},
    })
except Exception:
    pass
