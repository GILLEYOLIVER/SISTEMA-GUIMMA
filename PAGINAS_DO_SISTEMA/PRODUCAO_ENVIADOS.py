# -*- coding: utf-8 -*-
import customtkinter as ctk

class ProducaoEnviadosPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.lbl = ctk.CTkLabel(self, text="Produção Enviados")
        self.lbl.pack(padx=20, pady=20)

try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    attach_i18n_support(ProducaoEnviadosPage, {
        "pt_BR": {"Produção Enviados": "Produção Enviados"},
        "en_US": {"Produção Enviados": "Production Sent"},
        "es_ES": {"Produção Enviados": "Producción Enviados"},
    })
except Exception:
    pass
