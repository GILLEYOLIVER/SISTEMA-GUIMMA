# -*- coding: utf-8 -*-
"""Adaptador leve para garantir troca de idioma em páginas legadas.

Adiciona/normaliza métodos:
- _get_idioma_atual
- refresh_texts
- set_idioma
- on_language_changed

E aplica tradução recursiva em labels, placeholders, valores de combos,
cabeçalhos de Treeview e labels de Menu.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

COMMON_PAGE_TRANSLATIONS = {
    "pt_BR": {
        "Atualizar": "Atualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
        "Pesquisar": "Pesquisar",
        "Data": "Data",
        "Início": "Início",
        "Fim": "Fim",
        "Status": "Status",
        "Modelo": "Modelo",
        "Descrição": "Descrição",
        "Código": "Código",
        "Quantidade": "Quantidade",
        "Valor": "Valor",
        "Total": "Total",
    },
    "en_US": {
        "Atualizar": "Refresh",
        "Filtrar": "Filter",
        "Limpar": "Clear",
        "Exportar": "Export",
        "Imprimir": "Print",
        "Buscar": "Search",
        "Pesquisar": "Search",
        "Data": "Date",
        "Início": "Start",
        "Fim": "End",
        "Status": "Status",
        "Modelo": "Model",
        "Descrição": "Description",
        "Código": "Code",
        "Quantidade": "Quantity",
        "Valor": "Value",
        "Total": "Total",
    },
    "es_ES": {
        "Atualizar": "Actualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpiar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
        "Pesquisar": "Buscar",
        "Data": "Fecha",
        "Início": "Inicio",
        "Fim": "Fin",
        "Status": "Estado",
        "Modelo": "Modelo",
        "Descrição": "Descripción",
        "Código": "Código",
        "Quantidade": "Cantidad",
        "Valor": "Valor",
        "Total": "Total",
    },
}


def _language_of(owner) -> str:
    for attr in ("idioma_atual",):
        val = getattr(owner, attr, None)
        if isinstance(val, str) and val:
            return val
    for ref in (getattr(owner, "sistema", None), getattr(owner, "app", None), getattr(owner, "master", None)):
        if ref is not None:
            val = getattr(ref, "idioma_atual", None)
            if isinstance(val, str) and val:
                return val
    return "pt_BR"


def _merge_maps(lang: str, page_map: dict | None = None) -> dict:
    merged = dict(COMMON_PAGE_TRANSLATIONS.get("pt_BR", {}))
    merged.update(COMMON_PAGE_TRANSLATIONS.get(lang, {}))
    if isinstance(page_map, dict):
        base = page_map.get("pt_BR", {}) if isinstance(page_map.get("pt_BR", {}), dict) else {}
        cur = page_map.get(lang, {}) if isinstance(page_map.get(lang, {}), dict) else {}
        merged.update(base)
        merged.update(cur)
    return merged


def _translate_widget_tree(root, translate_fn):
    def _translate(value):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return translate_fn(stripped)
        return value

    def _apply(widget):
        for opt in ("text", "placeholder_text"):
            try:
                current = widget.cget(opt)
            except Exception:
                continue
            new_value = _translate(current)
            if new_value != current:
                try:
                    widget.configure(**{opt: new_value})
                except Exception:
                    pass

        try:
            values = widget.cget("values")
            if isinstance(values, (list, tuple)):
                new_values = [_translate(v) for v in values]
                if list(new_values) != list(values):
                    try:
                        widget.configure(values=new_values)
                    except Exception:
                        pass
        except Exception:
            pass

        if isinstance(widget, ttk.Treeview):
            try:
                h0 = widget.heading("#0").get("text", "")
                n0 = _translate(h0)
                if n0 != h0:
                    widget.heading("#0", text=n0)
            except Exception:
                pass
            try:
                for col in widget["columns"]:
                    ht = widget.heading(col).get("text", "")
                    nt = _translate(ht)
                    if nt != ht:
                        widget.heading(col, text=nt)
            except Exception:
                pass

        if isinstance(widget, tk.Menu):
            try:
                end = widget.index("end")
            except Exception:
                end = None
            if end is not None:
                for i in range(end + 1):
                    try:
                        label = widget.entrycget(i, "label")
                    except Exception:
                        continue
                    new_label = _translate(label)
                    if new_label != label:
                        try:
                            widget.entryconfigure(i, label=new_label)
                        except Exception:
                            pass

        try:
            for child in widget.winfo_children():
                _apply(child)
        except Exception:
            pass

    _apply(root)


def attach_i18n_support(page_cls, translations: dict | None = None):
    """Anexa suporte básico de i18n em páginas legadas sem quebrar métodos existentes."""
    if page_cls is None:
        return

    page_map = translations if isinstance(translations, dict) else getattr(page_cls, "TRANSLATIONS", None)
    page_map = page_map if isinstance(page_map, dict) else getattr(page_cls, "_TRANSLATIONS", None)

    old_refresh = getattr(page_cls, "refresh_texts", None)

    def _get_idioma_atual(self):
        return _language_of(self)

    def _tr(self, text):
        lang = _language_of(self)
        mp = _merge_maps(lang, page_map)
        return mp.get(text, text)

    def _refresh_texts(self):
        if callable(old_refresh):
            try:
                old_refresh(self)
            except TypeError:
                old_refresh()
            except Exception:
                pass
        _translate_widget_tree(self, lambda t: _tr(self, t))

    def _set_idioma(self, idioma="pt_BR"):
        try:
            self.idioma_atual = idioma or "pt_BR"
        except Exception:
            pass
        _refresh_texts(self)

    page_cls._get_idioma_atual = getattr(page_cls, "_get_idioma_atual", _get_idioma_atual)
    page_cls._tr = getattr(page_cls, "_tr", _tr)
    page_cls.refresh_texts = _refresh_texts
    page_cls.set_idioma = getattr(page_cls, "set_idioma", _set_idioma)
    page_cls.on_language_changed = getattr(page_cls, "on_language_changed", _set_idioma)

