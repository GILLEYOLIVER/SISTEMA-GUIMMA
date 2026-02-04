# -*- coding: utf-8 -*-
"""
RELATORIO_CUSTOS_REAIS.py - Relatório de custos reais (placeholder inicial)
"""
import customtkinter as ctk


class RelatorioCustosReaisPage(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._build()

    def _build(self):
        self.configure(fg_color="transparent")
        ctk.CTkLabel(
            self,
            text="Relatório de Custos Reais",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(20, 6))
        ctk.CTkLabel(
            self,
            text="Comparativo de custos planejados x realizados.",
            font=ctk.CTkFont(size=12)
        ).pack()


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Custos Reais - Teste")
    app.geometry("800x600")
    page = RelatorioCustosReaisPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()
