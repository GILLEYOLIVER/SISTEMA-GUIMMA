# -*- coding: utf-8 -*-
"""
PLANEJAMENTO_PRODUCAO.py - Planejamento de Produção (placeholder inicial)
"""
import customtkinter as ctk


class PlanejamentoProducaoPage(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._build()

    def _build(self):
        self.configure(fg_color="transparent")
        ctk.CTkLabel(
            self,
            text="Planejamento de Produção",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(20, 6))
        ctk.CTkLabel(
            self,
            text="Capacidade, carga de trabalho e cronograma.",
            font=ctk.CTkFont(size=12)
        ).pack()


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Planejamento de Produção - Teste")
    app.geometry("800x600")
    page = PlanejamentoProducaoPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()
