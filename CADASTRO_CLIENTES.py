# -*- coding: utf-8 -*-
"""
CADASTRO_CLIENTES.py - Módulo de Clientes (placeholder inicial)
"""
import customtkinter as ctk


class ClientesPage(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._build()

    def _build(self):
        self.configure(fg_color="transparent")
        ctk.CTkLabel(
            self,
            text="Cadastro de Clientes",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(20, 6))
        ctk.CTkLabel(
            self,
            text="Cadastro e consulta de clientes para pedidos e relatórios.",
            font=ctk.CTkFont(size=12)
        ).pack()


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Clientes - Teste")
    app.geometry("800x600")
    page = ClientesPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()
