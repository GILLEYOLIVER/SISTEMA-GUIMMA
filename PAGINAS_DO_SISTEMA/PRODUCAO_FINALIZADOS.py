# -*- coding: utf-8 -*-
import customtkinter as ctk

from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support


class ProducaoFinalizadosPage(ctk.CTkFrame):
    TRANSLATIONS = {
        "pt_BR": {
            "Produção Finalizados": "Produção Finalizados",
            "Painel de Produção Finalizados": "Painel de Produção Finalizados",
        },
        "en_US": {
            "Produção Finalizados": "Finished Production",
            "Painel de Produção Finalizados": "Finished Production Panel",
        },
        "es_ES": {
            "Produção Finalizados": "Producción Finalizada",
            "Painel de Produção Finalizados": "Panel de Producción Finalizada",
        },
    }

    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.lbl_titulo = ctk.CTkLabel(self, text="Produção Finalizados", font=("Arial", 18, "bold"))
        self.lbl_titulo.pack(padx=20, pady=(20, 8))

        self.lbl_subtitulo = ctk.CTkLabel(self, text="Painel de Produção Finalizados")
        self.lbl_subtitulo.pack(padx=20, pady=(0, 20))


attach_i18n_support(ProducaoFinalizadosPage, ProducaoFinalizadosPage.TRANSLATIONS)

if __name__ == "__main__":
    try:
        print(f"[TESTE_ISOLADO] Módulo carregado: {__file__}")
    except Exception as e:
        print(f"[TESTE_ISOLADO] Falha ao iniciar módulo: {e}")
