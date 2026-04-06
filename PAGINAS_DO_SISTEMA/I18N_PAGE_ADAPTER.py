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
import re
import unicodedata

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
    # Navegação/Menu
    ("Menu Principal", "Main Menu", "Menú Principal"),
    ("Dashboard", "Dashboard", "Dashboard"),
    ("Modelos", "Models", "Modelos"),
    ("Ordens de Corte", "Cut Orders", "Órdenes de Corte"),
    ("Registro de Corte", "Cut Records", "Registro de Corte"),
    ("Mão de Obra", "Labor", "Mano de Obra"),
    ("Compras", "Purchasing", "Compras"),
    ("Estoque", "Inventory", "Inventario"),
    ("Vendas", "Sales", "Ventas"),
    ("Fornecedores", "Providers", "Proveedores"),
    ("Acabamento", "Finishing", "Acabado"),
    ("Planejamento", "Planning", "Planificación"),
    ("Financeiro", "Financial", "Financiero"),
    ("Relatórios", "Reports", "Reportes"),
    ("Configurações", "Settings", "Configuración"),
    ("Banco de Dados", "Database", "Base de Datos"),
    # Filtros/consulta
    ("Buscar", "Search", "Buscar"),
    ("Pesquisar", "Search", "Buscar"),
    ("Pesquisar...", "Search...", "Buscar..."),
    ("Filtrar", "Filter", "Filtrar"),
    ("Todos", "All", "Todos"),
    ("Todas", "All", "Todas"),
    ("Selecionar", "Select", "Seleccionar"),
    ("Código/Modelo", "Code/Model", "Código/Modelo"),
    ("Código", "Code", "Código"),
    ("Modelo", "Model", "Modelo"),
    ("Ordem", "Order", "Orden"),
    ("Facção", "Contractor", "Facción"),
    ("Serviço", "Service", "Servicio"),
    ("Ação", "Action", "Acción"),
    ("Usuário", "User", "Usuario"),
    ("Data/Hora", "Date/Time", "Fecha/Hora"),
    ("Data", "Date", "Fecha"),
    ("De", "From", "De"),
    ("Até", "To", "Hasta"),
    ("Início", "Start", "Inicio"),
    ("Fim", "End", "Fin"),
    ("Status", "Status", "Estado"),
    # Tabelas/colunas
    ("Descrição", "Description", "Descripción"),
    ("Qtd", "Qty", "Cant."),
    ("Quantidade", "Quantity", "Cantidad"),
    ("Valor Un.", "Unit Value", "Valor Unit."),
    ("Valor_UN", "Unit Value", "Valor_UN"),
    ("Total", "Total", "Total"),
    ("Total Geral", "Grand Total", "Total General"),
    ("Total Geral (R$)", "Grand Total ($)", "Total General ($)"),
    ("Total Geral (peças)", "Grand Total (pieces)", "Total General (piezas)"),
    ("Cor", "Color", "Color"),
    ("Tamanho", "Size", "Talla"),
    ("Detalhes", "Details", "Detalles"),
    ("Página", "Page", "Página"),
    ("ID", "ID", "ID"),
    ("Hierarquia", "Hierarchy", "Jerarquía"),
    ("Ativo", "Active", "Activo"),
    ("Último Login", "Last Login", "Último Acceso"),
    # Botões/ações
    ("Salvar", "Save", "Guardar"),
    ("Excluir", "Delete", "Eliminar"),
    ("Editar", "Edit", "Editar"),
    ("Novo Usuário", "New User", "Nuevo Usuario"),
    ("Gerenciar Permissões", "Manage Permissions", "Gestionar Permisos"),
    ("Marcar Todos", "Mark All", "Marcar Todos"),
    ("Desmarcar Todos", "Unmark All", "Desmarcar Todos"),
    ("Marcar VER", "Mark VIEW", "Marcar VER"),
    ("Marcar EDITAR", "Mark EDIT", "Marcar EDITAR"),
    ("Marcar IMPRIMIR", "Mark PRINT", "Marcar IMPRIMIR"),
    ("Marcar EXCLUIR", "Mark DELETE", "Marcar ELIMINAR"),
    ("Marcar ADMIN", "Mark ADMIN", "Marcar ADMIN"),
    ("Recarregar", "Reload", "Recargar"),
    ("Estatísticas", "Statistics", "Estadísticas"),
    ("Relatório Completo", "Full Report", "Informe Completo"),
    ("Exportar CSV", "Export CSV", "Exportar CSV"),
    ("Limpar", "Clear", "Limpiar"),
    # Logs e atividades
    ("Logs e Atividades", "Logs and Activities", "Registros y Actividades"),
    ("Filtro de Logs", "Log Filter", "Filtro de Registros"),
    ("Filtrar Registros de Atividade", "Filter Activity Logs", "Filtrar Registros de Actividad"),
    ("Registros de Atividade", "Activity Logs", "Registros de Actividad"),
    ("Últimas ações no sistema", "Latest actions in system", "Últimas acciones en el sistema"),
    ("Histórico completo de ações no sistema", "Full action history in system", "Historial completo de acciones en el sistema"),
    ("Permissões Mais Usadas", "Most Used Permissions", "Permisos Más Usados"),
    ("Distribuição de Hierarquias", "Hierarchy Distribution", "Distribución de Jerarquías"),
    ("Por tipo de usuário", "By user type", "Por tipo de usuario"),
    ("Logs Hoje", "Logs Today", "Registros Hoy"),
    ("Usuários Ativos", "Active Users", "Usuarios Activos"),
    ("Administradores", "Administrators", "Administradores"),
    ("Atividades", "Activities", "Actividades"),
    # Situações e mensagens comuns
    ("Finalizado", "Finished", "Finalizado"),
    ("Pendente", "Pending", "Pendiente"),
    ("Pronto produção", "Production ready", "Listo para producción"),
    ("Nenhum usuário selecionado", "No user selected", "Ningún usuario seleccionado"),
    ("Gerencie usuários, permissões e acessos ao sistema", "Manage users, permissions and system access", "Gestione usuarios, permisos y accesos al sistema"),
    ("Gerencie todos os usuários do sistema", "Manage all system users", "Gestione todos los usuarios del sistema"),
    ("Dica", "Tip", "Consejo"),
    # Cadastro de modelos
    ("Cadastro de Modelos", "Model Registry", "Registro de Modelos"),
    ("Coleção", "Collection", "Colección"),
    ("Tam Base", "Base Size", "Talla Base"),
    ("Dificuldade", "Difficulty", "Dificultad"),
    ("Piloto", "Sample Maker", "Piloto"),
    ("Gasto/Peça", "Cost/Piece", "Costo/Pieza"),
    ("Grade disp.", "Available size range", "Rango de tallas disponible"),
    ("Imagens do Modelo", "Model Images", "Imágenes del Modelo"),
    ("Frente", "Front", "Frente"),
    ("Costas", "Back", "Espalda"),
    ("Adicionar", "Add", "Agregar"),
    ("Remover", "Remove", "Quitar"),
    # Relatórios específicos
    ("Relatório de Acabamento", "Finishing Report", "Informe de Acabado"),
    ("Relatório de Serviços Externos", "External Services Report", "Informe de Servicios Externos"),
    ("Relatório de Modelos Produzidos", "Produced Models Report", "Informe de Modelos Producidos"),
    ("Incluir peças de acabamento", "Include finishing pieces", "Incluir piezas de acabado"),
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

_WORD_TRIPLETS = [
    ("gestão", "management", "gestión"),
    ("usuários", "users", "usuarios"),
    ("usuário", "user", "usuario"),
    ("permissões", "permissions", "permisos"),
    ("permissão", "permission", "permiso"),
    ("logs", "logs", "registros"),
    ("atividades", "activities", "actividades"),
    ("atividade", "activity", "actividad"),
    ("relatório", "report", "informe"),
    ("relatórios", "reports", "informes"),
    ("filtro", "filter", "filtro"),
    ("buscar", "search", "buscar"),
    ("limpar", "clear", "limpiar"),
    ("salvar", "save", "guardar"),
    ("excluir", "delete", "eliminar"),
    ("editar", "edit", "editar"),
    ("novo", "new", "nuevo"),
    ("todos", "all", "todos"),
    ("todas", "all", "todas"),
    ("data", "date", "fecha"),
    ("hora", "time", "hora"),
    ("detalhes", "details", "detalles"),
    ("página", "page", "página"),
    ("ação", "action", "acción"),
    ("ações", "actions", "acciones"),
    ("status", "status", "estado"),
    ("modelo", "model", "modelo"),
    ("ordem", "order", "orden"),
    ("serviço", "service", "servicio"),
    ("facção", "contractor", "facción"),
    ("quantidade", "quantity", "cantidad"),
    ("total", "total", "total"),
    ("valor", "value", "valor"),
    ("código", "code", "código"),
]


def _build_word_maps():
    def _norm_local(value: str) -> str:
        txt = value.strip().lower()
        txt = unicodedata.normalize("NFKD", txt)
        txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
        txt = re.sub(r"\s+", " ", txt)
        return txt

    maps = {"pt_BR": {}, "en_US": {}, "es_ES": {}}
    for pt, en, es in _WORD_TRIPLETS:
        variants = {pt, en, es}
        for v in variants:
            maps["pt_BR"][v] = pt
            maps["en_US"][v] = en
            maps["es_ES"][v] = es
            maps["pt_BR"][_norm_local(v)] = pt
            maps["en_US"][_norm_local(v)] = en
            maps["es_ES"][_norm_local(v)] = es
    return maps


WORD_TRANSLATIONS = _build_word_maps()


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


def _normalize_text(value: str) -> str:
    if not isinstance(value, str):
        return ""
    txt = value.strip().lower()
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = re.sub(r"\s+", " ", txt)
    return txt


def _build_bidirectional_page_map(page_map: dict | None, lang: str) -> dict:
    """
    Constrói mapa bidirecional para páginas:
    qualquer variante PT/EN/ES conhecida passa a apontar para o idioma alvo.
    """
    if not isinstance(page_map, dict):
        return {}

    pt = page_map.get("pt_BR", {}) if isinstance(page_map.get("pt_BR", {}), dict) else {}
    en = page_map.get("en_US", {}) if isinstance(page_map.get("en_US", {}), dict) else {}
    es = page_map.get("es_ES", {}) if isinstance(page_map.get("es_ES", {}), dict) else {}
    target = page_map.get(lang, {}) if isinstance(page_map.get(lang, {}), dict) else {}
    if not target:
        target = pt

    result = {}
    canonical_keys = set(pt.keys()) | set(en.keys()) | set(es.keys()) | set(target.keys())

    for key in canonical_keys:
        target_val = target.get(key, pt.get(key, en.get(key, es.get(key, key))))
        variants = {
            key,
            pt.get(key, key),
            en.get(key, key),
            es.get(key, key),
        }
        variants = {v for v in variants if isinstance(v, str) and v.strip()}
        for v in variants:
            result[v] = target_val
            result[_normalize_text(v)] = target_val

    return result


def _translate_flexible(text: str, mp: dict) -> str:
    if not isinstance(text, str) or not text.strip():
        return text

    # 1) match exato
    if text in mp:
        return mp[text]

    # 2) match normalizado (case/acento/espaço)
    norm = _normalize_text(text)
    if norm in mp:
        return mp[norm]

    # 3) substituição por partes (frases mistas e labels compostas)
    translated = text
    replacements = []
    for k, v in mp.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        k_clean = k.strip()
        if not k_clean or len(k_clean) < 3:
            continue
        replacements.append((k_clean, v))

    # evita substituir termos curtos antes de termos longos
    replacements.sort(key=lambda item: len(item[0]), reverse=True)

    for src, dst in replacements:
        try:
            pattern = re.compile(rf"(?<!\w){re.escape(src)}(?!\w)", re.IGNORECASE)
            translated = pattern.sub(dst, translated)
        except Exception:
            continue

    # 4) fallback por palavra: cobre frases ainda não catalogadas integralmente
    lang_words = WORD_TRANSLATIONS.get("pt_BR", {})
    for _k, _v in WORD_TRANSLATIONS.items():
        if _k == "pt_BR":
            continue
        lang_words.update(_v)

    target_lang = "pt_BR"
    if "Search" in mp.values() or "Save" in mp.values():
        target_lang = "en_US"
    if "Buscar" in mp.values() and "Guardar" in mp.values():
        target_lang = "es_ES"
    target_words = WORD_TRANSLATIONS.get(target_lang, {})

    def _word_sub(match):
        token = match.group(0)
        norm_token = _normalize_text(token)
        canonical = lang_words.get(token) or lang_words.get(norm_token) or token
        repl = target_words.get(canonical) or target_words.get(_normalize_text(canonical)) or token
        if token.isupper():
            return repl.upper()
        if token[:1].isupper():
            return repl[:1].upper() + repl[1:]
        return repl

    try:
        translated = re.sub(r"[A-Za-zÀ-ÿ_]+", _word_sub, translated)
    except Exception:
        pass

    return translated


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
        mp.update(_build_bidirectional_page_map(page_map, lang))
        return _translate_flexible(text, mp)

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
        # Reaplica após delays curtos para cobrir widgets/títulos de Treeview
        # criados ou atualizados depois da montagem inicial da tela.
        try:
            if hasattr(self, "after"):
                self.after(80, lambda: _refresh_texts(self))
                self.after(260, lambda: _refresh_texts(self))
                self.after(700, lambda: _refresh_texts(self))
                self.after(1500, lambda: _refresh_texts(self))
        except Exception:
            pass

    page_cls._get_idioma_atual = getattr(page_cls, "_get_idioma_atual", _get_idioma_atual)
    page_cls._tr = getattr(page_cls, "_tr", _tr)
    page_cls.refresh_texts = _refresh_texts
    page_cls.set_idioma = getattr(page_cls, "set_idioma", _set_idioma)
    page_cls.on_language_changed = getattr(page_cls, "on_language_changed", _set_idioma)

if __name__ == "__main__":
    try:
        print(f"[TESTE_ISOLADO] Módulo carregado: {__file__}")
    except Exception as e:
        print(f"[TESTE_ISOLADO] Falha ao iniciar módulo: {e}")
