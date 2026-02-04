# -*- coding: utf-8 -*-
"""
COMPRAS.py - Módulo de Compras (placeholder inicial)
"""
import customtkinter as ctk


class ComprasPage(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._build()

    def _build(self):
        self.configure(fg_color="transparent")
        ctk.CTkLabel(
            self,
            text="Módulo de Compras",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(20, 6))
        ctk.CTkLabel(
            self,
            text="Cadastro de fornecedores, pedidos de compra e recebimento.",
            font=ctk.CTkFont(size=12)
        ).pack()


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Compras - Teste")
    app.geometry("800x600")
    page = ComprasPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()
