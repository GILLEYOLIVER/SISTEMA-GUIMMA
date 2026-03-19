# -*- coding: utf-8 -*-
import customtkinter as ctk

class ProducaoRetornoPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.lbl = ctk.CTkLabel(self, text="Produção Retorno")
        self.lbl.pack(padx=20, pady=20)

try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    attach_i18n_support(ProducaoRetornoPage, {
        "pt_BR": {"Produção Retorno": "Produção Retorno"},
        "en_US": {"Produção Retorno": "Production Return"},
        "es_ES": {"Produção Retorno": "Producción Retorno"},
    })
except Exception:
    pass

# --- AUTO_PAGE_TRANSLATIONS (gerado automaticamente) ---
from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support as _attach_i18n_support

AUTO_PAGE_TRANSLATIONS = {
    "ProducaoRetornoPage": {
        "pt_BR": {"title": "Producao Retorno", "Atualizar": "Atualizar", "Filtrar": "Filtrar", "Salvar": "Salvar", "Cancelar": "Cancelar"},
        "en_US": {"title": "Producao Retorno", "Atualizar": "Refresh", "Filtrar": "Filter", "Salvar": "Save", "Cancelar": "Cancel"},
        "es_ES": {"title": "Producao Retorno", "Atualizar": "Actualizar", "Filtrar": "Filtrar", "Salvar": "Guardar", "Cancelar": "Cancelar"},
    },
}

for _cls_name, _map in AUTO_PAGE_TRANSLATIONS.items():
    _cls = globals().get(_cls_name)
    if isinstance(_cls, type):
        if not hasattr(_cls, "TRANSLATIONS") and not hasattr(_cls, "_TRANSLATIONS"):
            _cls.TRANSLATIONS = _map
        _attach_i18n_support(_cls, getattr(_cls, "TRANSLATIONS", getattr(_cls, "_TRANSLATIONS", _map)))
