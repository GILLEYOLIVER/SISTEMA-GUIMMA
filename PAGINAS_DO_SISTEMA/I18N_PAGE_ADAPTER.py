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

_TERM_TRIPLETS = [
    ("Atualizar", "Refresh", "Actualizar"),
    ("Filtrar", "Filter", "Filtrar"),
    ("Limpar", "Clear", "Limpiar"),
    ("Exportar", "Export", "Exportar"),
    ("Exportar PDF", "Export PDF", "Exportar PDF"),
    ("Imprimir", "Print", "Imprimir"),
    ("Buscar", "Search", "Buscar"),
    ("Pesquisar", "Search", "Buscar"),
    ("Pesquisar Ordem", "Search Order", "Buscar Orden"),
    ("Data", "Date", "Fecha"),
    ("Data de", "Date from", "Fecha desde"),
    ("Data até", "Date to", "Fecha hasta"),
    ("Início", "Start", "Inicio"),
    ("Fim", "End", "Fin"),
    ("Status", "Status", "Estado"),
    ("Modelo", "Model", "Modelo"),
    ("Descrição", "Description", "Descripción"),
    ("Código", "Code", "Código"),
    ("Quantidade", "Quantity", "Cantidad"),
    ("Valor", "Value", "Valor"),
    ("Total", "Total", "Total"),
    ("Fornecedor", "Supplier", "Proveedor"),
    ("Entrega Prevista", "Expected Delivery", "Entrega Prevista"),
    ("Observações", "Notes", "Observaciones"),
    ("Salvar", "Save", "Guardar"),
    ("Cancelar", "Cancel", "Cancelar"),
    ("Novo", "New", "Nuevo"),
    ("Aprovar", "Approve", "Aprobar"),
    ("Receber", "Receive", "Recibir"),
    ("Compras", "Purchases", "Compras"),
    ("Consultar Ordens", "Consult Orders", "Consultar Órdenes"),
    ("Cadastrar Corte", "Register Cut", "Registrar Corte"),
    ("Planejamento", "Planning", "Planificación"),
    ("Ordens Planejadas", "Planned Orders", "Órdenes Planificadas"),
    ("Controle de Mão de Obra", "Labor Control", "Control de Mano de Obra"),
    ("Registro Acabamento", "Finishing Record", "Registro de Acabado"),
    ("Pagamento de Serviços", "Service Payments", "Pago de Servicios"),
    ("Recibos de Pagamentos", "Payment Receipts", "Recibos de Pago"),
    ("Custos Reais", "Actual Costs", "Costos Reales"),
    ("Relatórios", "Reports", "Reportes"),
    ("Temas", "Themes", "Temas"),
    ("Usuários", "Users", "Usuarios"),
    ("Nº Ordem", "Order No.", "Nº Orden"),
    ("N° Ordem", "Order No.", "N° Orden"),
    ("Comprimento", "Length", "Longitud"),
    ("Largura", "Width", "Ancho"),
    ("Cortador", "Cutter", "Cortador"),
    ("Auxiliar", "Assistant", "Auxiliar"),
    ("Composição", "Composition", "Composición"),
    ("Serviço", "Service", "Servicio"),
    ("Serviço:", "Service:", "Servicio:"),
    ("Buscar Corte", "Search Cut", "Buscar Corte"),
    ("Buscar Envio", "Search Dispatch", "Buscar Envío"),
    ("Search Cut", "Search Cut", "Buscar Corte"),
    ("Search Dispatch", "Search Dispatch", "Buscar Envío"),
    ("Confirmar Envio", "Confirm Dispatch", "Confirmar Envío"),
    ("Registrar Entrada", "Register Entry", "Registrar Entrada"),
    ("Pré-visualizar PDF", "Preview PDF", "Vista previa PDF"),
    ("Export PDF", "Export PDF", "Exportar PDF"),
    ("Limpar", "Clear", "Limpiar"),
    ("Controle por Tamanho", "Size Control", "Control por Talla"),
    ("Enviado", "Sent", "Enviado"),
    ("Entregue", "Delivered", "Entregado"),
    ("Pilotos", "Samples", "Pilotos"),
    ("Defeito", "Defect", "Defecto"),
    ("Faltante", "Missing", "Faltante"),
    ("Regulares", "Regular", "Regulares"),
    ("Subtotal", "Subtotal", "Subtotal"),
    ("Valor Total", "Total Value", "Valor Total"),
    ("Total de Peças", "Total Pieces", "Total de Piezas"),
    ("Aviamentos Enviados", "Sent Trims", "Avíos Enviados"),
    ("Outros", "Others", "Otros"),
    ("Observações", "Notes", "Observaciones"),
    ("Dados Bancários (Prestador)", "Bank Details (Provider)", "Datos Bancarios (Prestador)"),
    ("Telefone Encarregado", "Supervisor Phone", "Teléfono Encargado"),
    ("Tel. Acabamento", "Finishing Phone", "Tel. Acabado"),
    ("Piloto Recebido", "Sample Received", "Piloto Recibido"),
    ("Piloto entregue? (baixar ao salvar)", "Sample delivered? (deduct on save)", "¿Piloto entregado? (descontar al guardar)"),
    ("Prestador", "Provider", "Prestador"),
    ("Data Envio", "Dispatch Date", "Fecha Envío"),
    ("Ordem", "Order", "Orden"),
    ("Qtde", "Qty", "Cant."),
    ("Facção", "Outsourcing", "Facción"),
    ("Nenhum.", "None.", "Ninguno."),
]


def _build_common_map():
    maps = {"pt_BR": {}, "en_US": {}, "es_ES": {}}
    for pt, en, es in _TERM_TRIPLETS:
        variants = {pt, en, es}
        for v in variants:
            maps["pt_BR"][v] = pt
            maps["en_US"][v] = en
            maps["es_ES"][v] = es
    return maps


COMMON_PAGE_TRANSLATIONS = _build_common_map()


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

        if isinstance(widget, ttk.Notebook):
            try:
                for tab_id in widget.tabs():
                    current = widget.tab(tab_id, "text")
                    new_text = _translate(current)
                    if new_text != current:
                        widget.tab(tab_id, text=new_text)
            except Exception:
                pass

        if isinstance(widget, (tk.Toplevel, tk.Tk)):
            try:
                title = widget.title()
                new_title = _translate(title)
                if new_title != title:
                    widget.title(new_title)
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
