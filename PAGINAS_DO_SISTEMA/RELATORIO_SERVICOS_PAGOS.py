# -*- coding: utf-8 -*-
"""
Relatorio detalhado de servicos pagos.

Mostra o pagamento como documento principal e relaciona servico, corte,
prestador, envio, retorno, acabamento e dados bancarios usados no pagamento.
"""

from __future__ import annotations

import csv
import base64
import html
import mimetypes
import os
import tempfile
import webbrowser
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PAGINAS_DO_SISTEMA.UI_CALENDARIO import vincular_calendario

try:
    from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db
except Exception as err:
    db = None
    _DB_IMPORT_ERROR = err
else:
    _DB_IMPORT_ERROR = None


def _first_day_of_month(value: date) -> date:
    return value.replace(day=1)


def _last_day_of_month(value: date) -> date:
    next_month = (value.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


def _parse_date(value: str, fallback: date) -> date:
    text = (value or "").strip()
    if not text:
        return fallback
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Data invalida: {text}. Use AAAA-MM-DD ou DD/MM/AAAA.")


def _as_money(value: Any) -> str:
    try:
        number = Decimal(str(value or 0))
    except Exception:
        number = Decimal("0")
    text = f"{number:,.2f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return _as_money(value)
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, bool):
        return "Sim" if value else "Nao"
    return str(value)

def _rgb_from_hex(color: str):
    try:
        value = (color or "").strip().lstrip("#")
        if len(value) != 6:
            return None
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return None

def _color_distance(color_a: str, color_b: str) -> float:
    rgb_a = _rgb_from_hex(color_a)
    rgb_b = _rgb_from_hex(color_b)
    if not rgb_a or not rgb_b:
        return 999.0
    return sum((a - b) ** 2 for a, b in zip(rgb_a, rgb_b)) ** 0.5

def _contrast_text(color: str) -> str:
    rgb = _rgb_from_hex(color)
    if not rgb:
        return "#000000"
    r, g, b = rgb
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.5 else "#FFFFFF"


class RelatorioServicosPagosPage(ctk.CTkFrame):
    PAGE_TITLE = "Relatorio de Servicos Pagos"

    TREE_COLUMNS = (
        "pagamento_id",
        "data_pagamento",
        "prestador",
        "servico",
        "codigo",
        "descricao",
        "ordem",
        "qtd",
        "valor_servico",
        "adiantamento",
        "descontos",
        "liquido",
        "status",
    )

    TREE_HEADINGS = {
        "pagamento_id": "Pgto",
        "data_pagamento": "Data",
        "prestador": "Prestador",
        "servico": "Servico",
        "codigo": "Codigo",
        "descricao": "Descricao",
        "ordem": "Ordem",
        "qtd": "Qtd",
        "valor_servico": "Valor Servico",
        "adiantamento": "Adiant.",
        "descontos": "Descontos",
        "liquido": "Liquido",
        "status": "Status",
    }

    FIELD_LABELS = {
        "pagamento_id": "Pagamento",
        "data_pagamento": "Data do pagamento",
        "data_registro": "Data de registro",
        "usuario_pagamento": "Usuario responsavel",
        "mes_referencia": "Mes de referencia",
        "prestador": "Prestador",
        "pagamento_valor_total": "Valor bruto do pagamento",
        "valor_adiantamento_abatido": "Adiantamento abatido",
        "valor_liquido": "Valor liquido pago",
        "pagamento_observacoes": "Observacoes do pagamento",
        "servico": "Tipo de servico",
        "codigo": "Codigo do corte",
        "descricao": "Descricao",
        "ordem": "Ordem de corte",
        "quantidade_finalizada": "Quantidade finalizada",
        "qtd_enviada": "Quantidade enviada",
        "total_pecas": "Total de pecas",
        "valor_peca": "Valor por peca",
        "valor_servico": "Valor do servico",
        "finalizado_valor_total": "Valor finalizado",
        "status_servico": "Status do servico",
        "finalizado_pago": "Servico marcado como pago",
        "entrada_acabamento_id": "Entrada de acabamento",
        "acabamento_data_chegada": "Data de chegada",
        "acabamento_total_entregue": "Total entregue",
        "acabamento_total_regulares": "Pecas regulares",
        "acabamento_total_defeitos": "Pecas com defeito",
        "acabamento_total_faltantes": "Pecas faltantes",
        "acabamento_valor_total": "Valor total no acabamento",
        "status_finalizacao": "Status da conferencia",
        "usuario_conferencia": "Usuario da conferencia",
        "data_conferencia": "Data da conferencia",
        "observacoes_finalizacao": "Observacoes da conferencia",
        "envio_id": "Envio",
        "controle_envio_id": "Controle de envio",
        "data_envio": "Data de envio",
        "previsao_entrega": "Previsao de entrega",
        "status_envio": "Status do envio",
        "destino": "Destino",
        "costureira": "Costureira",
        "faccao": "Faccao",
        "retorno_id": "Retorno",
        "retorno_data_chegada": "Data de retorno",
        "retorno_total_entregue": "Total entregue no retorno",
        "retorno_total_defeitos": "Defeitos no retorno",
        "retorno_total_faltantes": "Faltantes no retorno",
        "retorno_observacoes": "Observacoes do retorno",
        "corte_id": "Corte",
        "numero_ordem": "Numero da ordem",
        "data_corte": "Data do corte",
        "cortador": "Cortador",
        "ajudante": "Ajudante",
        "metros_utilizados": "Metros utilizados",
        "bobinas_utilizadas": "Bobinas utilizadas",
        "rendimento": "Rendimento",
        "grade_regular": "Grade regular",
        "grade_defeitos": "Grade com defeitos",
        "cpf": "CPF",
        "banco": "Banco",
        "agencia": "Agencia",
        "conta": "Conta",
        "pix": "Pix",
        "pca_id": "Comprovante PCA",
        "pca_total_pago": "Total pago no comprovante",
        "pca_adiantamento": "Adiantamento",
        "pca_ajuda_custo": "Ajuda de custo",
        "pca_bonificacao": "Bonificacao",
        "pca_pecas_faltantes": "Pecas faltantes",
        "pca_pecas_estragadas": "Pecas estragadas",
        "pca_desconto_pecas": "Desconto por pecas",
        "pca_estornado": "Estornado",
    }

    MONEY_FIELDS = {
        "pagamento_valor_total", "valor_adiantamento_abatido", "valor_liquido",
        "valor_peca", "valor_servico", "finalizado_valor_total",
        "acabamento_valor_total", "pca_total_pago", "pca_adiantamento",
        "pca_ajuda_custo", "pca_bonificacao", "pca_desconto_pecas",
    }

    DETAIL_GROUPS = (
        ("Pagamento", (
            "pagamento_id", "data_pagamento", "data_registro", "usuario_pagamento",
            "mes_referencia", "prestador", "pagamento_valor_total",
            "valor_adiantamento_abatido", "valor_liquido", "pagamento_observacoes",
        )),
        ("Servico Pago", (
            "servico", "codigo", "descricao", "ordem", "quantidade_finalizada",
            "qtd_enviada", "total_pecas", "valor_peca", "valor_servico",
            "finalizado_valor_total", "status_servico", "finalizado_pago",
        )),
        ("Acabamento e Conferencia", (
            "entrada_acabamento_id", "acabamento_data_chegada", "acabamento_total_entregue",
            "acabamento_total_regulares", "acabamento_total_defeitos", "acabamento_total_faltantes",
            "acabamento_valor_total", "status_finalizacao", "usuario_conferencia",
            "data_conferencia", "observacoes_finalizacao",
        )),
        ("Envio e Retorno", (
            "envio_id", "controle_envio_id", "data_envio", "previsao_entrega",
            "status_envio", "destino", "costureira", "faccao", "retorno_id",
            "retorno_data_chegada", "retorno_total_entregue", "retorno_total_defeitos",
            "retorno_total_faltantes", "retorno_observacoes",
        )),
        ("Corte", (
            "corte_id", "numero_ordem", "data_corte", "cortador", "ajudante",
            "metros_utilizados", "bobinas_utilizadas", "rendimento", "grade_regular",
            "grade_defeitos",
        )),
        ("Dados Bancarios / Comprovante", (
            "cpf", "banco", "agencia", "conta", "pix", "pca_id", "pca_total_pago",
            "pca_adiantamento", "pca_ajuda_custo", "pca_bonificacao",
            "pca_pecas_faltantes", "pca_pecas_estragadas", "pca_desconto_pecas",
            "pca_estornado",
        )),
    )

    def __init__(self, master, sistema=None, app=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema or app
        self._rows: list[dict[str, Any]] = []
        self._row_by_iid: dict[str, dict[str, Any]] = {}

        self._load_theme()
        self.configure(fg_color=self.cor_fundo)

        today = date.today()
        self.ini_var = tk.StringVar(value=_first_day_of_month(today).strftime("%Y-%m-%d"))
        self.fim_var = tk.StringVar(value=_last_day_of_month(today).strftime("%Y-%m-%d"))
        self.prestador_var = tk.StringVar(value="Todos")
        self.servico_var = tk.StringVar(value="Todos")
        self.busca_var = tk.StringVar(value="")

        self._build_ui()
        self.buscar()

    def _load_theme(self):
        origem = self.sistema
        self.cor_fundo = getattr(origem, "cor_fundo", "#ffffff")
        self.cor_texto = getattr(origem, "cor_texto", "#111827")
        self.cor_primaria = getattr(origem, "cor_primaria", "#2563eb")
        self.cor_secundaria = getattr(origem, "cor_secundaria", "#f3f4f6")
        self.cor_terciaria = getattr(origem, "cor_terciaria", "#ffffff")
        self.cor_borda = getattr(origem, "cor_borda", "#cbd5e1")
        self.cor_hover = getattr(origem, "cor_hover", "#1d4ed8")
        self.cor_destaque = getattr(origem, "cor_destaque", "#2563eb")
        self.cor_sucesso = getattr(origem, "cor_sucesso", "#15803d")
        self.cor_alerta = getattr(origem, "cor_alerta", "#b91c1c")

    def _button_color(self, preferred: str | None = None) -> str:
        color = preferred or self.cor_primaria
        if _color_distance(color, self.cor_fundo) < 40:
            color = self.cor_destaque
        if _color_distance(color, self.cor_fundo) < 40:
            color = "#2563EB"
        return color

    def _button_hover_color(self, color: str) -> str:
        hover = self.cor_hover
        if _color_distance(hover, self.cor_fundo) < 80 or _contrast_text(hover) != _contrast_text(color):
            hover = color
        return hover

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text=self.PAGE_TITLE.upper(),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.cor_texto,
        ).grid(row=0, column=0, sticky="w")
        self.status_var = tk.StringVar(value="Relatorio detalhado dos pagamentos de servicos.")
        ctk.CTkLabel(header, textvariable=self.status_var, text_color=self.cor_texto).grid(
            row=1, column=0, sticky="w", pady=(3, 0)
        )

        filters = ctk.CTkFrame(self, fg_color=self.cor_secundaria, border_color=self.cor_borda, border_width=1)
        filters.grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        filters.grid_columnconfigure(8, weight=1)

        self._label(filters, "Inicio", 0, 0)
        self.ini_entry = self._entry(filters, self.ini_var, 1, 0, width=112)
        vincular_calendario(self, self.ini_entry, output_format="%Y-%m-%d")
        self._label(filters, "Fim", 0, 1)
        self.fim_entry = self._entry(filters, self.fim_var, 1, 1, width=112)
        vincular_calendario(self, self.fim_entry, output_format="%Y-%m-%d")
        self._label(filters, "Prestador", 0, 2)
        self.prestador_entry = self._entry(filters, self.prestador_var, 1, 2, width=180)
        self._label(filters, "Servico", 0, 3)
        self.servico_entry = self._entry(filters, self.servico_var, 1, 3, width=150)
        self._label(filters, "Codigo / ordem / texto", 0, 4)
        self.busca_entry = self._entry(filters, self.busca_var, 1, 4, width=210)
        self.busca_entry.bind("<Return>", lambda _event: self.buscar())

        search_color = self._button_color(self.cor_primaria)
        search_hover = self._button_hover_color(search_color)
        self.btn_buscar = ctk.CTkButton(
            filters, text="Buscar", command=self.buscar, fg_color=self.cor_primaria,
            hover_color=search_hover, text_color=_contrast_text(search_color),
            text_color_disabled="#4B5563", width=96,
        )
        self.btn_buscar.configure(fg_color=search_color)
        self.btn_buscar.grid(row=1, column=5, padx=(10, 4), pady=(0, 10), sticky="w")
        ctk.CTkButton(
            filters, text="Exportar CSV", command=self.exportar_csv, fg_color=self.cor_sucesso,
            hover_color=self.cor_hover, text_color="white", width=116,
        ).grid(row=1, column=6, padx=4, pady=(0, 10), sticky="w")
        ctk.CTkButton(
            filters, text="Imprimir", command=self.imprimir_relatorio, fg_color=self.cor_alerta,
            hover_color=self.cor_hover, text_color="white", width=96,
        ).grid(row=1, column=7, padx=4, pady=(0, 10), sticky="w")

        cards = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        cards.grid(row=2, column=0, sticky="ew", padx=14, pady=(2, 8))
        for col in range(5):
            cards.grid_columnconfigure(col, weight=1)
        self.card_vars = {}
        for col, (key, label) in enumerate((
            ("registros", "Registros"),
            ("bruto", "Valor bruto"),
            ("adiantamentos", "Adiantamentos"),
            ("descontos", "Descontos"),
            ("liquido", "Liquido pago"),
        )):
            frame = ctk.CTkFrame(cards, fg_color=self.cor_secundaria, border_color=self.cor_borda, border_width=1)
            frame.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0), pady=0)
            ctk.CTkLabel(frame, text=label, text_color=self.cor_texto, font=ctk.CTkFont(size=11, weight="bold")).pack(
                anchor="w", padx=10, pady=(8, 0)
            )
            var = tk.StringVar(value="0")
            self.card_vars[key] = var
            ctk.CTkLabel(frame, textvariable=var, text_color=self.cor_texto, font=ctk.CTkFont(size=16, weight="bold")).pack(
                anchor="w", padx=10, pady=(2, 8)
            )

        content = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        content.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 14))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=2)
        content.grid_rowconfigure(1, weight=3)

        table_frame = ctk.CTkFrame(content, fg_color=self.cor_secundaria, border_color=self.cor_borda, border_width=1)
        table_frame.grid(row=0, column=0, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self._configure_tree_style()
        self.tree = ttk.Treeview(table_frame, columns=self.TREE_COLUMNS, show="headings", selectmode="browse")
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        widths = {
            "pagamento_id": 64, "data_pagamento": 90, "prestador": 180, "servico": 115,
            "codigo": 140, "descricao": 230, "ordem": 130, "qtd": 60,
            "valor_servico": 105, "adiantamento": 90, "descontos": 90,
            "liquido": 95, "status": 90,
        }
        for col in self.TREE_COLUMNS:
            self.tree.heading(col, text=self.TREE_HEADINGS[col])
            anchor = "e" if col in {"qtd", "valor_servico", "adiantamento", "descontos", "liquido"} else "w"
            self.tree.column(col, width=widths.get(col, 120), minwidth=60, anchor=anchor, stretch=col in {"descricao", "prestador"})

        detail_frame = ctk.CTkFrame(content, fg_color=self.cor_secundaria, border_color=self.cor_borda, border_width=1)
        detail_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            detail_frame, text="VISUALIZACAO DETALHADA DO SERVICO E PAGAMENTO",
            text_color=self.cor_texto, font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        self.detail_view = ctk.CTkScrollableFrame(
            detail_frame, fg_color=self.cor_terciaria, border_color=self.cor_borda, border_width=1
        )
        self.detail_view._opera_preservar_tema = True
        self.detail_view.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.detail_view.grid_columnconfigure(0, weight=1)
        self._set_detail("Selecione um pagamento para ver todos os detalhes.")

    def _label(self, parent, text, row, col):
        ctk.CTkLabel(parent, text=text, text_color=self.cor_texto).grid(
            row=row, column=col, sticky="w", padx=(10 if col == 0 else 6, 0), pady=(8, 2)
        )

    def _entry(self, parent, variable, row, col, width):
        entry = ctk.CTkEntry(
            parent, textvariable=variable, width=width, fg_color=self.cor_terciaria,
            border_color=self.cor_borda, text_color=self.cor_texto,
        )
        entry.grid(row=row, column=col, sticky="w", padx=(10 if col == 0 else 6, 0), pady=(0, 10))
        return entry

    def _configure_tree_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Treeview",
            background=self.cor_terciaria,
            fieldbackground=self.cor_terciaria,
            foreground=self.cor_texto,
            rowheight=24,
        )
        style.configure("Treeview.Heading", background=self.cor_secundaria, foreground=self.cor_texto)

    def buscar(self):
        if db is None:
            messagebox.showerror("Banco indisponivel", f"Falha ao carregar banco:\n{_DB_IMPORT_ERROR}")
            return
        try:
            ini = _parse_date(self.ini_var.get(), _first_day_of_month(date.today()))
            fim = _parse_date(self.fim_var.get(), _last_day_of_month(date.today()))
        except ValueError as exc:
            messagebox.showwarning("Periodo invalido", str(exc))
            return
        if fim < ini:
            messagebox.showwarning("Periodo invalido", "A data final nao pode ser menor que a inicial.")
            return

        prestador = (self.prestador_var.get() or "").strip()
        servico = (self.servico_var.get() or "").strip()
        busca = (self.busca_var.get() or "").strip()

        try:
            self._rows = self._fetch_rows(ini, fim, prestador, servico, busca)
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao gerar relatorio de servicos pagos:\n{exc}")
            return
        self._render_rows()

    def _fetch_rows(self, ini: date, fim: date, prestador: str, servico: str, busca: str) -> list[dict[str, Any]]:
        schema = db.get_schema()
        sql = f"""
            SELECT
                ps.id AS pagamento_id,
                ps.prestador_id,
                COALESCE(ps.nome_prestador, fac.nome, pca.costureira, cf.costureira, cec.costureira, cec.faccao) AS prestador,
                ps.data_pagamento,
                ps.valor_total AS pagamento_valor_total,
                ps.valor_adiantamento_abatido,
                ps.valor_liquido,
                ps.mes_referencia,
                ps.observacoes AS pagamento_observacoes,
                ps.usuario_pagamento,
                ps.data_registro,
                psd.entrada_acabamento_id,
                psd.valor_servico,

                ea.envio_id AS controle_envio_id,
                ea.data_chegada AS acabamento_data_chegada,
                ea.total_entregue AS acabamento_total_entregue,
                ea.total_defeitos AS acabamento_total_defeitos,
                ea.total_faltantes AS acabamento_total_faltantes,
                ea.total_regulares AS acabamento_total_regulares,
                ea.valor_total AS acabamento_valor_total,
                ea.pago AS acabamento_pago,
                ea.valor_pago AS acabamento_valor_pago,
                ea.data_pagamento AS acabamento_data_pagamento,

                ead.status_finalizacao,
                ead.usuario_conferencia,
                ead.data_conferencia,
                ead.observacoes_finalizacao,
                ead.valor_total_pagar,

                cf.id AS finalizado_id,
                cf.corte_id,
                cf.envio_id,
                cf.retorno_id,
                COALESCE(cf.tipo_servico, pca.tipo_servico, ec.tipo_servico, cec.servico) AS servico,
                COALESCE(cf.codigo, pca.codigo, ec.codigo_corte, cec.codigo_corte, cc.codigo) AS codigo,
                COALESCE(cf.descricao, pca.descricao, ec.descricao_corte, cec.descricao_corte, cc.descricao, cc.descricao_corte) AS descricao,
                COALESCE(ec.ordem_corte, cec.ordem_corte, cc.ordem_corte, cc.numero_ordem) AS ordem,
                cf.costureira,
                cf.data_envio,
                cf.data_chegada,
                cf.data_final,
                cf.qtd_enviada,
                cf.total_pecas,
                cf.quantidade_finalizada,
                cf.observacao AS finalizado_observacao,
                cf.status AS status_servico,
                cf.valor_peca,
                cf.bonificacao,
                cf.pago AS finalizado_pago,
                cf.valor_pago AS finalizado_valor_pago,
                cf.valor_total AS finalizado_valor_total,
                cf.qtd_pp, cf.qtd_p, cf.qtd_m, cf.qtd_g, cf.qtd_gg, cf.qtd_g1, cf.qtd_g2, cf.qtd_g3,
                cf.qtd_defeito_pp, cf.qtd_defeito_p, cf.qtd_defeito_m, cf.qtd_defeito_g,
                cf.qtd_defeito_gg, cf.qtd_defeito_g1, cf.qtd_defeito_g2, cf.qtd_defeito_g3,

                ec.id AS envio_id,
                ec.data_envio AS envio_data_envio,
                ec.previsao_entrega,
                ec.status_envio,
                ec.cliente,
                ec.colecao,
                ec.material,
                ec.cores,
                ec.aviamentos,
                ec.outros,
                ec.observacoes AS envio_observacoes,

                cec.data_envio AS controle_data_envio,
                cec.destino,
                cec.faccao,
                cec.quantidade_total,
                cec.valor_total AS controle_valor_total,
                cec.status AS controle_status,
                cec.observacao AS controle_observacao,

                crc.id AS retorno_id,
                crc.data_chegada AS retorno_data_chegada,
                crc.total_entregue AS retorno_total_entregue,
                crc.total_defeitos AS retorno_total_defeitos,
                crc.total_faltantes AS retorno_total_faltantes,
                crc.total_regulares AS retorno_total_regulares,
                crc.valor_total AS retorno_valor_total,
                crc.observacoes_gerais AS retorno_observacoes,

                cc.numero_ordem,
                cc.data AS data_corte,
                cc.cortador,
                cc.ajudante,
                cc.metros_utilizados,
                cc.bobinas_utilizadas,
                cc.rendimento,

                fac.codigo AS prestador_codigo,
                fac.tipo_prestador,
                fac.telefone,
                fac.endereco,
                COALESCE(pca.cpf, fac.cpf) AS cpf,
                COALESCE(pca.banco, fac.banco) AS banco,
                COALESCE(pca.agencia, fac.agencia) AS agencia,
                COALESCE(pca.conta, fac.conta) AS conta,
                COALESCE(pca.pix, fac.pix) AS pix,

                pca.id AS pca_id,
                pca.total_pago AS pca_total_pago,
                pca.adiantamento AS pca_adiantamento,
                pca.ajuda_custo AS pca_ajuda_custo,
                pca.bonificacao AS pca_bonificacao,
                pca.pecas_faltantes AS pca_pecas_faltantes,
                pca.pecas_estragadas AS pca_pecas_estragadas,
                pca.desconto_pecas AS pca_desconto_pecas,
                pca.pecas_com_defeito AS pca_pecas_com_defeito,
                pca.valor_defeito AS pca_valor_defeito,
                pca.estornado AS pca_estornado
            FROM {schema}.pagamento_servicos ps
            LEFT JOIN {schema}.pagamento_servicos_detalhe psd
                   ON psd.pagamento_id = ps.id
            LEFT JOIN {schema}.entrada_acabamento ea
                   ON ea.id = psd.entrada_acabamento_id
                   OR ea.pagamento_id = ps.id
            LEFT JOIN {schema}.entrada_acabamento_detalhes ead
                   ON ead.entrada_id = ea.id
            LEFT JOIN LATERAL (
                SELECT cf0.*
                  FROM {schema}.cortes_finalizados cf0
                 WHERE cf0.entrada_id = ea.id
                    OR cf0.pagamento_id = ps.id
                 ORDER BY cf0.id DESC
                 LIMIT 1
            ) cf ON TRUE
            LEFT JOIN {schema}.envios_cortes ec
                   ON ec.id = cf.envio_id
            LEFT JOIN {schema}.controle_envio_cortes cec
                   ON cec.id = ea.envio_id
                   OR cec.corte_id = cf.corte_id
            LEFT JOIN LATERAL (
                SELECT r0.*
                  FROM {schema}.controle_retorno_cortes r0
                 WHERE r0.id = cf.retorno_id
                    OR r0.envio_id = ec.id
                 ORDER BY r0.data_chegada DESC NULLS LAST, r0.id DESC
                 LIMIT 1
            ) crc ON TRUE
            LEFT JOIN {schema}.cadastro_de_corte cc
                   ON cc.id = COALESCE(cf.corte_id, cec.corte_id, ec.corte_id)
            LEFT JOIN {schema}.cadastro_faccoes fac
                   ON fac.id = COALESCE(ps.prestador_id, ec.prestador_id)
            LEFT JOIN LATERAL (
                SELECT pca0.*
                  FROM {schema}.pagamento_corte_acabamento pca0
                 WHERE pca0.codigo = COALESCE(cf.codigo, ec.codigo_corte, cec.codigo_corte, cc.codigo)
                   AND (pca0.data_pagamento = ps.data_pagamento OR pca0.data_pagamento IS NOT NULL)
                 ORDER BY
                   CASE WHEN pca0.data_pagamento = ps.data_pagamento THEN 0 ELSE 1 END,
                   pca0.data_pagamento DESC NULLS LAST,
                   pca0.id DESC
                 LIMIT 1
            ) pca ON TRUE
            WHERE ps.data_pagamento BETWEEN %s AND %s
              AND (
                    %s = ''
                 OR COALESCE(ps.nome_prestador, fac.nome, pca.costureira, cf.costureira, cec.costureira, cec.faccao, '') ILIKE %s
              )
              AND (
                    %s = ''
                 OR COALESCE(cf.tipo_servico, pca.tipo_servico, ec.tipo_servico, cec.servico, '') ILIKE %s
              )
              AND (
                    %s = ''
                 OR ps.id::text ILIKE %s
                 OR COALESCE(cf.codigo, pca.codigo, ec.codigo_corte, cec.codigo_corte, cc.codigo, '') ILIKE %s
                 OR COALESCE(ec.ordem_corte, cec.ordem_corte, cc.ordem_corte, cc.numero_ordem, '') ILIKE %s
                 OR COALESCE(cf.descricao, pca.descricao, ec.descricao_corte, cec.descricao_corte, cc.descricao, '') ILIKE %s
                 OR COALESCE(ps.observacoes, '') ILIKE %s
              )
            ORDER BY ps.data_pagamento DESC, ps.id DESC, psd.entrada_acabamento_id DESC NULLS LAST
        """
        prestador_filter = "" if prestador.lower() in ("", "todos", "todas") else prestador
        servico_filter = "" if servico.lower() in ("", "todos", "todas") else servico
        like_prestador = f"%{prestador_filter}%"
        like_servico = f"%{servico_filter}%"
        like_busca = f"%{busca}%"
        params = (
            ini, fim,
            prestador_filter, like_prestador,
            servico_filter, like_servico,
            busca, like_busca, like_busca, like_busca, like_busca, like_busca,
        )
        rows = db.fetch_all(sql, params)
        return [self._normalize_row(row) for row in rows]

    def _normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        regular = {
            "PP": row.get("qtd_pp"), "P": row.get("qtd_p"), "M": row.get("qtd_m"), "G": row.get("qtd_g"),
            "GG": row.get("qtd_gg"), "G1": row.get("qtd_g1"), "G2": row.get("qtd_g2"), "G3": row.get("qtd_g3"),
        }
        defeitos = {
            "PP": row.get("qtd_defeito_pp"), "P": row.get("qtd_defeito_p"), "M": row.get("qtd_defeito_m"),
            "G": row.get("qtd_defeito_g"), "GG": row.get("qtd_defeito_gg"), "G1": row.get("qtd_defeito_g1"),
            "G2": row.get("qtd_defeito_g2"), "G3": row.get("qtd_defeito_g3"),
        }
        row["grade_regular"] = " | ".join(f"{k}:{_as_int(v)}" for k, v in regular.items() if _as_int(v))
        row["grade_defeitos"] = " | ".join(f"{k}:{_as_int(v)}" for k, v in defeitos.items() if _as_int(v))
        row["status"] = "Estornado" if row.get("pca_estornado") else ("Pago" if row.get("finalizado_pago") or row.get("acabamento_pago") else "Registrado")
        return row

    def _render_rows(self):
        self.tree.delete(*self.tree.get_children())
        self._row_by_iid.clear()

        bruto = Decimal("0")
        adiantamentos = Decimal("0")
        descontos = Decimal("0")
        liquido = Decimal("0")

        for row in self._rows:
            bruto += Decimal(str(row.get("valor_servico") or row.get("pagamento_valor_total") or 0))
            adiantamentos += Decimal(str(row.get("valor_adiantamento_abatido") or row.get("pca_adiantamento") or 0))
            descontos += Decimal(str(row.get("pca_desconto_pecas") or 0)) + Decimal(str(row.get("pca_valor_defeito") or 0))
            liquido += Decimal(str(row.get("valor_liquido") or row.get("pca_total_pago") or row.get("acabamento_valor_pago") or 0))
            values = (
                row.get("pagamento_id"),
                _as_text(row.get("data_pagamento")),
                _as_text(row.get("prestador")),
                _as_text(row.get("servico")),
                _as_text(row.get("codigo")),
                _as_text(row.get("descricao")),
                _as_text(row.get("ordem")),
                _as_int(row.get("quantidade_finalizada") or row.get("acabamento_total_entregue")),
                _as_money(row.get("valor_servico") or row.get("pagamento_valor_total")),
                _as_money(row.get("valor_adiantamento_abatido") or row.get("pca_adiantamento")),
                _as_money((row.get("pca_desconto_pecas") or 0) + (row.get("pca_valor_defeito") or 0)),
                _as_money(row.get("valor_liquido") or row.get("pca_total_pago") or row.get("acabamento_valor_pago")),
                row.get("status"),
            )
            iid = self.tree.insert("", "end", values=values)
            self._row_by_iid[iid] = row

        self.card_vars["registros"].set(str(len(self._rows)))
        self.card_vars["bruto"].set("R$ " + _as_money(bruto))
        self.card_vars["adiantamentos"].set("R$ " + _as_money(adiantamentos))
        self.card_vars["descontos"].set("R$ " + _as_money(descontos))
        self.card_vars["liquido"].set("R$ " + _as_money(liquido))
        self.status_var.set(f"{len(self._rows)} registro(s) de servicos pagos encontrados.")

        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])
            self._on_select()
        else:
            self._set_detail("Nenhum pagamento encontrado para os filtros informados.")

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        row = self._row_by_iid.get(selection[0])
        if not row:
            return
        self._render_detail(row)

    def _field_label(self, key: str) -> str:
        return self.FIELD_LABELS.get(key, key.replace("_", " ").title())

    def _field_value(self, key: str, value: Any) -> str:
        if key in self.MONEY_FIELDS:
            return "R$ " + _as_money(value)
        return _as_text(value)

    def _detail_pairs(self, row: dict[str, Any], keys: tuple[str, ...]) -> list[tuple[str, str, str]]:
        pairs = []
        for key in keys:
            value = row.get(key)
            if value not in (None, ""):
                pairs.append((key, self._field_label(key), self._field_value(key, value)))
        return pairs

    def _clear_detail(self):
        for child in self.detail_view.winfo_children():
            child.destroy()

    def _render_detail(self, row: dict[str, Any]):
        self._clear_detail()

        resumo = ctk.CTkFrame(
            self.detail_view, fg_color=self.cor_secundaria, border_color=self.cor_borda, border_width=1
        )
        resumo.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
        resumo.grid_columnconfigure(0, weight=1)
        resumo.grid_columnconfigure(1, weight=1)
        resumo.grid_columnconfigure(2, weight=1)

        titulo = f"Pagamento #{_as_text(row.get('pagamento_id'))} - {_as_text(row.get('prestador')) or 'Prestador nao informado'}"
        ctk.CTkLabel(
            resumo, text=titulo, text_color=self.cor_texto,
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w",
        ).grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(10, 2))

        subtitulo = f"{_as_text(row.get('servico')) or 'Servico'} | Codigo {_as_text(row.get('codigo')) or '-'} | Ordem {_as_text(row.get('ordem')) or '-'}"
        ctk.CTkLabel(
            resumo, text=subtitulo, text_color=self.cor_texto, anchor="w",
        ).grid(row=1, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 10))

        destaque_items = (
            ("Valor bruto", "R$ " + _as_money(row.get("pagamento_valor_total") or row.get("valor_servico"))),
            ("Adiantamento", "R$ " + _as_money(row.get("valor_adiantamento_abatido") or row.get("pca_adiantamento"))),
            ("Liquido pago", "R$ " + _as_money(row.get("valor_liquido") or row.get("pca_total_pago") or row.get("acabamento_valor_pago"))),
        )
        for col, (label, value) in enumerate(destaque_items):
            self._render_metric(resumo, col, label, value, col == 2)

        grid_row = 1
        for title, keys in self.DETAIL_GROUPS:
            pairs = self._detail_pairs(row, keys)
            if pairs:
                self._render_group(self.detail_view, grid_row, title, pairs)
                grid_row += 1

    def _render_metric(self, parent, col: int, label: str, value: str, highlight: bool = False):
        color = self.cor_sucesso if highlight else self._button_color(self.cor_primaria)
        text_color = _contrast_text(color)
        card = ctk.CTkFrame(parent, fg_color=color, corner_radius=6)
        card._opera_preservar_tema = True
        card.grid(row=2, column=col, sticky="ew", padx=(12 if col == 0 else 4, 12 if col == 2 else 4), pady=(0, 12))
        ctk.CTkLabel(card, text=label.upper(), text_color=text_color, font=ctk.CTkFont(size=10, weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 0)
        )
        ctk.CTkLabel(card, text=value, text_color=text_color, font=ctk.CTkFont(size=18, weight="bold")).pack(
            anchor="w", padx=10, pady=(1, 8)
        )

    def _render_group(self, parent, row_index: int, title: str, pairs: list[tuple[str, str, str]]):
        group = ctk.CTkFrame(parent, fg_color=self.cor_secundaria, border_color=self.cor_borda, border_width=1)
        group.grid(row=row_index, column=0, sticky="ew", padx=8, pady=6)
        for col in range(4):
            group.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(
            group, text=title.upper(), text_color=self.cor_texto,
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).grid(row=0, column=0, columnspan=4, sticky="ew", padx=12, pady=(10, 6))

        visual_row = 1
        visual_col = 0
        full_width_keys = {"pagamento_observacoes", "observacoes_finalizacao", "retorno_observacoes", "grade_regular", "grade_defeitos"}
        for key, label, value in pairs:
            span = 4 if key in full_width_keys or len(value) > 70 else 1
            if span == 4 and visual_col != 0:
                visual_row += 1
                visual_col = 0
            field = ctk.CTkFrame(group, fg_color=self.cor_terciaria, border_color=self.cor_borda, border_width=1)
            field.grid(row=visual_row, column=visual_col, columnspan=span, sticky="ew", padx=6, pady=5)
            ctk.CTkLabel(
                field, text=label, text_color=self.cor_texto,
                font=ctk.CTkFont(size=10, weight="bold"), anchor="w",
            ).pack(anchor="w", padx=8, pady=(6, 0))
            value_color = self.cor_sucesso if key in {"valor_liquido", "pca_total_pago"} else self.cor_texto
            ctk.CTkLabel(
                field, text=value, text_color=value_color,
                font=ctk.CTkFont(size=12, weight="bold" if key in self.MONEY_FIELDS else "normal"),
                anchor="w", justify="left", wraplength=900,
            ).pack(anchor="w", fill="x", padx=8, pady=(1, 6))

            if span == 4:
                visual_row += 1
                visual_col = 0
            else:
                visual_col += 1
                if visual_col >= 4:
                    visual_row += 1
                    visual_col = 0

    def _set_detail(self, text: str):
        self._clear_detail()
        ctk.CTkLabel(
            self.detail_view, text=text, text_color=self.cor_texto,
            font=ctk.CTkFont(size=13), anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=12)

    def exportar_csv(self):
        if not self._rows:
            messagebox.showwarning("Exportar CSV", "Nao ha registros para exportar.")
            return
        path = filedialog.asksaveasfilename(
            title="Salvar relatorio de servicos pagos",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"relatorio_servicos_pagos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if not path:
            return
        columns = sorted({key for row in self._rows for key in row.keys()})
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns, delimiter=";")
                writer.writeheader()
                for row in self._rows:
                    writer.writerow({key: _as_text(row.get(key)) for key in columns})
            messagebox.showinfo("Exportar CSV", f"Relatorio exportado:\n{path}")
        except Exception as exc:
            messagebox.showerror("Exportar CSV", f"Falha ao exportar:\n{exc}")

    def _logo_data_uri(self) -> str:
        try:
            from PAGINAS_DO_SISTEMA.LOGOMARCA import get_logo_data_uri
            configured_logo = get_logo_data_uri()
            if configured_logo:
                return configured_logo
        except Exception:
            pass

        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = (
            os.path.join(base_dir, "LOGO.jpg"),
            os.path.join(base_dir, "logo.jpg"),
            os.path.join(base_dir, "LOGO.png"),
            os.path.join(base_dir, "logo.png"),
            os.path.join(base_dir, "OPERA.jpg"),
        )
        for path in candidates:
            if not os.path.isfile(path):
                continue
            try:
                mime = mimetypes.guess_type(path)[0] or "image/jpeg"
                with open(path, "rb") as handle:
                    encoded = base64.b64encode(handle.read()).decode("ascii")
                return f"data:{mime};base64,{encoded}"
            except Exception:
                continue
        return ""

    def _html_field(self, key: str, value: Any) -> str:
        if value in (None, ""):
            return ""
        label = html.escape(self._field_label(key))
        text = html.escape(self._field_value(key, value))
        money_class = " money" if key in self.MONEY_FIELDS else ""
        wide_class = " wide" if key in {"pagamento_observacoes", "observacoes_finalizacao", "retorno_observacoes", "grade_regular", "grade_defeitos"} or len(text) > 70 else ""
        return f"<div class='field{money_class}{wide_class}'><span>{label}</span><strong>{text}</strong></div>"

    def _html_group(self, title: str, row: dict[str, Any], keys: tuple[str, ...]) -> str:
        fields = "".join(self._html_field(key, row.get(key)) for key in keys)
        if not fields:
            return ""
        return f"<section class='group'><h3>{html.escape(title)}</h3><div class='field-grid'>{fields}</div></section>"

    def imprimir_relatorio(self):
        if not self._rows:
            messagebox.showwarning("Imprimir", "Nao ha registros para imprimir.")
            return

        logo_data_uri = self._logo_data_uri()
        logo_img = f"<img class='logo' src='{logo_data_uri}' alt='Logo'>" if logo_data_uri else "<div class='logo-placeholder'>Sistema Guimma</div>"

        rows_html = []
        for row in self._rows:
            groups_html = "".join(self._html_group(group, row, keys) for group, keys in self.DETAIL_GROUPS)
            bruto = "R$ " + _as_money(row.get("pagamento_valor_total") or row.get("valor_servico"))
            adiantamento = "R$ " + _as_money(row.get("valor_adiantamento_abatido") or row.get("pca_adiantamento"))
            liquido = "R$ " + _as_money(row.get("valor_liquido") or row.get("pca_total_pago") or row.get("acabamento_valor_pago"))
            status = html.escape(_as_text(row.get("status")) or "Pago")
            rows_html.append(
                "<article class='payment'>"
                "<div class='payment-head'>"
                "<div>"
                f"<div class='eyebrow'>Pagamento #{html.escape(_as_text(row.get('pagamento_id')))}</div>"
                f"<h2>{html.escape(_as_text(row.get('prestador')) or 'Prestador nao informado')}</h2>"
                f"<p>{html.escape(_as_text(row.get('servico')) or 'Servico')} | Codigo {html.escape(_as_text(row.get('codigo')) or '-')} | Ordem {html.escape(_as_text(row.get('ordem')) or '-')}</p>"
                "</div>"
                f"<span class='badge'>{status}</span>"
                "</div>"
                "<div class='payment-values'>"
                f"<div><span>Valor bruto</span><strong>{html.escape(bruto)}</strong></div>"
                f"<div><span>Adiantamento</span><strong>{html.escape(adiantamento)}</strong></div>"
                f"<div class='liquid'><span>Liquido pago</span><strong>{html.escape(liquido)}</strong></div>"
                "</div>"
                f"{groups_html}"
                "</article>"
            )

        content = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Relatorio de Servicos Pagos</title>
  <style>
    :root {{
      --ink: #111827;
      --muted: #64748b;
      --line: #d7dee8;
      --soft: #f8fafc;
      --soft2: #eef6ff;
      --brand: #0f766e;
      --brand-dark: #134e4a;
      --danger: #b91c1c;
      --success: #15803d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--ink);
      margin: 0;
      background: #eef2f7;
      font-size: 12px;
    }}
    .page {{
      width: 210mm;
      min-height: 297mm;
      margin: 0 auto;
      background: white;
      padding: 13mm;
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 3px solid var(--brand);
      padding-bottom: 6px;
      margin-bottom: 8px;
    }}
    .brand {{ display: flex; gap: 10px; align-items: center; }}
    .logo {{ max-height: 42px; max-width: 125px; object-fit: contain; }}
    .logo-placeholder {{
      width: 78px; height: 38px; display: grid; place-items: center;
      background: var(--brand); color: white; font-weight: 800; border-radius: 8px;
    }}
    h1 {{ margin: 0; font-size: 21px; color: var(--brand-dark); letter-spacing: 0; }}
    .meta {{ color: var(--muted); margin-top: 2px; }}
    .doc-info {{ text-align: right; color: var(--muted); line-height: 1.45; }}
    .cards {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin: 8px 0 8px; }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 7px;
      background: var(--soft);
      min-height: 46px;
    }}
    .card.total {{
      background: var(--brand);
      color: white;
      border-color: var(--brand);
    }}
    .label, .card span, .field span, .payment-values span {{
      display: block;
      color: var(--muted);
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 4px;
    }}
    .card.total span {{ color: rgba(255,255,255,.86); }}
    .value, .card strong {{ display: block; font-size: 15px; }}
    .payment {{
      border: 1px solid var(--line);
      border-radius: 10px;
      margin: 0 0 10px;
      overflow: hidden;
      background: white;
    }}
    .payment-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      padding: 8px 12px;
      background: linear-gradient(90deg, #ecfdf5, #eff6ff);
      border-bottom: 1px solid var(--line);
      break-inside: avoid;
    }}
    .eyebrow {{ color: var(--brand); font-weight: 800; font-size: 11px; text-transform: uppercase; }}
    h2 {{ margin: 2px 0; font-size: 18px; color: var(--brand-dark); }}
    p {{ margin: 0; color: #334155; }}
    .badge {{
      background: var(--success);
      color: white;
      border-radius: 999px;
      padding: 6px 10px;
      font-weight: 800;
      white-space: nowrap;
    }}
    .payment-values {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; padding: 8px 12px 2px; break-inside: avoid; }}
    .payment-values div {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 7px 8px;
      background: var(--soft);
    }}
    .payment-values .liquid {{ background: #ecfdf5; border-color: #bbf7d0; }}
    .payment-values strong {{ font-size: 17px; color: var(--ink); }}
    .payment-values .liquid strong {{ color: var(--success); }}
    .group {{ padding: 6px 12px 8px; break-inside: avoid; }}
    .group h3 {{
      color: var(--brand-dark);
      font-size: 12px;
      margin: 6px 0;
      padding-bottom: 4px;
      border-bottom: 1px solid var(--line);
      text-transform: uppercase;
    }}
    .field-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }}
    .field {{
      border: 1px solid var(--line);
      background: var(--soft);
      border-radius: 7px;
      padding: 5px 7px;
      min-height: 40px;
    }}
    .field.wide {{ grid-column: span 4; }}
    .field.money strong {{ color: var(--success); font-size: 13px; }}
    .field strong {{ display: block; line-height: 1.35; overflow-wrap: anywhere; }}
    footer {{
      margin-top: 14px;
      color: var(--muted);
      border-top: 1px solid var(--line);
      padding-top: 8px;
      display: flex;
      justify-content: space-between;
    }}
    @page {{ size: A4; margin: 10mm; }}
    @media print {{
      body {{ background: white; }}
      .page {{ width: auto; min-height: auto; margin: 0; padding: 0; }}
      .payment {{ break-inside: auto; page-break-inside: auto; overflow: visible; }}
      .payment-head, .payment-values, .group h3, .field {{ break-inside: avoid; }}
      .cards {{ grid-template-columns: repeat(5, 1fr); }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <div class="brand">
        {logo_img}
        <div>
          <h1>Relatorio de Servicos Pagos</h1>
          <div class="meta">Periodo: {html.escape(self.ini_var.get())} a {html.escape(self.fim_var.get())}</div>
        </div>
      </div>
      <div class="doc-info">
        <strong>SISTEMA GUIMMA</strong><br>
        Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
        Documento para conferencia de pagamentos
      </div>
    </header>
    <div class="cards">
      <div class="card"><span>Registros</span><strong>{html.escape(self.card_vars['registros'].get())}</strong></div>
      <div class="card"><span>Valor bruto</span><strong>{html.escape(self.card_vars['bruto'].get())}</strong></div>
      <div class="card"><span>Adiantamentos</span><strong>{html.escape(self.card_vars['adiantamentos'].get())}</strong></div>
      <div class="card"><span>Descontos</span><strong>{html.escape(self.card_vars['descontos'].get())}</strong></div>
      <div class="card total"><span>Liquido pago</span><strong>{html.escape(self.card_vars['liquido'].get())}</strong></div>
    </div>
    {''.join(rows_html)}
    <footer>
      <span>Relatorio detalhado de servicos pagos</span>
      <span>Sistema Guimma</span>
    </footer>
  </main>
  <script>window.onload = function() {{ setTimeout(function() {{ window.print(); }}, 350); }};</script>
</body>
</html>"""
        fd, path = tempfile.mkstemp(prefix="relatorio_servicos_pagos_", suffix=".html")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        webbrowser.open(f"file:///{path.replace(os.sep, '/')}")


if __name__ == "__main__":
    root = ctk.CTk()
    root.geometry("1280x760")
    root.title("Relatorio de Servicos Pagos")
    RelatorioServicosPagosPage(root).pack(fill="both", expand=True)
    root.mainloop()
