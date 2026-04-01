# -*- coding: utf-8 -*-
import customtkinter as ctk

from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support


class ProducaoEnviadosPage(ctk.CTkFrame):
    TRANSLATIONS = {
        "pt_BR": {
            "Produção Enviados": "Produção Enviados",
            "Painel de Produção Enviados": "Painel de Produção Enviados",
        },
        "en_US": {
            "Produção Enviados": "Sent Production",
            "Painel de Produção Enviados": "Sent Production Panel",
        },
        "es_ES": {
            "Produção Enviados": "Producción Enviada",
            "Painel de Produção Enviados": "Panel de Producción Enviada",
        },
    }

    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.lbl_titulo = ctk.CTkLabel(self, text="Produção Enviados", font=("Arial", 18, "bold"))
        self.lbl_titulo.pack(padx=20, pady=(20, 8))

        self.lbl_subtitulo = ctk.CTkLabel(self, text="Painel de Produção Enviados")
        self.lbl_subtitulo.pack(padx=20, pady=(0, 20))


attach_i18n_support(ProducaoEnviadosPage, ProducaoEnviadosPage.TRANSLATIONS)

if __name__ == "__main__":
    try:
        print(f"[TESTE_ISOLADO] Módulo carregado: {__file__}")
    except Exception as e:
        print(f"[TESTE_ISOLADO] Falha ao iniciar módulo: {e}")
