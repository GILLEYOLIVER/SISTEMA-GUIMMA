# -*- coding: utf-8 -*-
"""
MRP_PLANEJAMENTO.py - MRP (placeholder inicial)
"""
import customtkinter as ctk


class MRPPage(ctk.CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._build()

    def _build(self):
        self.configure(fg_color="transparent")
        ctk.CTkLabel(
            self,
            text="MRP / Necessidades de Insumos",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(20, 6))
        ctk.CTkLabel(
            self,
            text="Planejamento de necessidades de materiais.",
            font=ctk.CTkFont(size=12)
        ).pack()
