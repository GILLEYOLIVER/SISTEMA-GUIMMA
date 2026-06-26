# -*- coding: utf-8 -*-
"""Comportamentos compartilhados para campos de seleção."""

from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk


def abrir_lista_combobox(widget) -> bool:
    """Abre a lista de um combobox CTk/ttk quando possível."""
    try:
        if hasattr(widget, "_open_dropdown_menu"):
            widget._open_dropdown_menu()
            return True
    except Exception:
        pass

    try:
        if isinstance(widget, ttk.Combobox):
            widget.tk.call("ttk::combobox::Post", str(widget))
            return True
    except Exception:
        pass

    return False


def habilitar_duplo_clique_combobox(widget):
    """Permite abrir a lista com duplo clique no campo do combobox."""
    if getattr(widget, "_opera_duplo_clique_combo", False):
        return widget

    def _abrir(_event=None):
        try:
            widget.after(1, lambda: abrir_lista_combobox(widget))
        except Exception:
            abrir_lista_combobox(widget)
        return "break"

    try:
        widget.bind("<Double-Button-1>", _abrir, add="+")
    except Exception:
        pass

    for attr in ("_entry", "_canvas"):
        try:
            interno = getattr(widget, attr, None)
            if interno is not None:
                interno.bind("<Double-Button-1>", _abrir, add="+")
        except Exception:
            pass

    try:
        widget._opera_duplo_clique_combo = True
    except Exception:
        pass
    return widget


def instalar_duplo_clique_global():
    """Aplica o duplo clique aos comboboxes novos criados depois da instalação."""
    if getattr(ctk.CTkComboBox, "_opera_duplo_clique_global", False):
        return

    original_ctk_init = ctk.CTkComboBox.__init__

    def _ctk_init(self, *args, **kwargs):
        original_ctk_init(self, *args, **kwargs)
        habilitar_duplo_clique_combobox(self)

    ctk.CTkComboBox.__init__ = _ctk_init
    ctk.CTkComboBox._opera_duplo_clique_global = True

    if not getattr(ttk.Combobox, "_opera_duplo_clique_global", False):
        original_ttk_init = ttk.Combobox.__init__

        def _ttk_init(self, *args, **kwargs):
            original_ttk_init(self, *args, **kwargs)
            habilitar_duplo_clique_combobox(self)

        ttk.Combobox.__init__ = _ttk_init
        ttk.Combobox._opera_duplo_clique_global = True
