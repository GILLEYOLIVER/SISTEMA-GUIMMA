# -*- coding: utf-8 -*-
"""
Busca profunda de corte.

Localiza um corte pelo codigo/ordem/id e rastreia sua passagem pelas etapas:
ordem, cadastro, envio, retorno, finalizacao e pagamento.
"""

from __future__ import annotations

import html
import os
import tempfile
import webbrowser
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema
except Exception as err:
    def get_conn():
        raise RuntimeError(f"BANCO_DE_DADOS_PG indisponivel: {err}")

    def get_schema():
        return "opera"


TAMANHOS = ("PP", "P", "M", "G", "GG", "G1", "G2", "G3")


def _qident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
                "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:19], fmt)
        except Exception:
            pass
    return None


def _tempo_decorrido(inicio: datetime | None, fim: datetime | None = None) -> str:
    if not inicio:
        return ""
    fim = fim or datetime.now()
    delta = fim - inicio
    if delta.total_seconds() < 0:
        return "data futura"
    dias = delta.days
    horas = delta.seconds // 3600
    minutos = (delta.seconds % 3600) // 60
    if dias:
        return f"{dias} dia(s), {horas}h"
    if horas:
        return f"{horas}h {minutos}min"
    return f"{minutos}min"


class BuscaProfundaCortePage(ctk.CTkFrame):
    ETAPAS = [
        {
            "table": "ordem_corte_ficha",
            "label": "Ordem de corte",
            "date_cols": ["data_registro", "created_at", "data_atualizacao"],
            "status_cols": ["status"],
            "match_cols": ["id", "codigo_modelo", "descricao_modelo", "op_planejamento"],
            "show_cols": ["id", "codigo_modelo", "descricao_modelo", "quantidade_desejada", "total_pecas",
                          "status", "data_registro", "usuario_registro", "op_planejamento"],
        },
        {
            "table": "cadastro_de_corte",
            "label": "Corte cadastrado",
            "date_cols": ["data", "created_at", "updated_at"],
            "status_cols": [],
            "match_cols": ["id", "codigo", "ordem_corte", "numero_ordem", "descricao", "descricao_corte"],
            "show_cols": ["id", "numero_ordem", "ordem_corte", "codigo", "descricao", "descricao_corte", "data",
                          "cortador", "ajudante", "total_pecas", "rendimento"],
        },
        {
            "table": "controle_envio_cortes",
            "label": "Envio legado",
            "date_cols": ["data_envio", "created_at", "updated_at"],
            "status_cols": ["status"],
            "match_cols": ["id", "corte_id", "ordem_corte", "codigo_corte", "descricao_corte", "faccao",
                           "costureira", "destino", "servico"],
            "show_cols": ["id", "corte_id", "ordem_corte", "codigo_corte", "descricao_corte", "servico",
                          "faccao", "costureira", "quantidade_total", "valor_total", "status", "data_envio"],
        },
        {
            "table": "envios_cortes",
            "label": "Enviado para prestador",
            "date_cols": ["data_envio", "created_at", "updated_at"],
            "status_cols": ["status_envio", "status"],
            "match_cols": ["id", "corte_id", "ordem_corte", "codigo_corte", "descricao_corte", "tipo_servico",
                           "colecao", "cliente"],
            "show_cols": ["id", "remessa_id", "corte_id", "ordem_corte", "codigo_corte", "descricao_corte",
                          "tipo_servico", "prestador_id", "total_pecas", "valor_total_envio", "status_envio",
                          "data_envio", "hora_envio", "previsao_entrega"],
        },
        {
            "table": "controle_retorno_cortes",
            "label": "Retorno registrado",
            "date_cols": ["data_chegada", "created_at", "updated_at"],
            "status_cols": [],
            "match_cols": ["id", "envio_id", "observacoes_gerais"],
            "show_cols": ["id", "envio_id", "data_chegada", "total_entregue", "total_copias",
                          "total_defeitos", "total_faltantes", "total_regulares", "valor_total"],
            "related_key": "envios_cortes",
            "related_col": "envio_id",
        },
        {
            "table": "entrada_acabamento",
            "label": "Entrada/acabamento",
            "date_cols": ["data_chegada", "data_pagamento", "created_at", "updated_at"],
            "status_cols": ["pago"],
            "match_cols": ["id", "envio_id", "pagamento_id"],
            "show_cols": ["id", "envio_id", "data_chegada", "total_entregue", "total_defeitos",
                          "total_faltantes", "total_regulares", "valor_total", "pago", "pagamento_id",
                          "valor_pago", "data_pagamento"],
            "related_key": "controle_envio_cortes",
            "related_col": "envio_id",
        },
        {
            "table": "cortes_finalizados",
            "label": "Finalizado",
            "date_cols": ["data_final", "data_conferencia", "data_pagamento", "created_at", "updated_at"],
            "status_cols": ["status", "pago"],
            "match_cols": ["id", "corte_id", "envio_id", "retorno_id", "codigo", "descricao", "costureira",
                           "tipo_servico", "pagamento_id"],
            "show_cols": ["id", "corte_id", "envio_id", "retorno_id", "tipo_servico", "codigo", "descricao",
                          "costureira", "quantidade_finalizada", "status", "pago", "valor_total",
                          "pagamento_id", "data_final", "data_pagamento"],
        },
        {
            "table": "cortes_finalizados_completo",
            "label": "Finalizado completo",
            "date_cols": ["created_at", "updated_at"],
            "status_cols": ["status"],
            "match_cols": ["id", "entrada_id", "envio_id", "corte_id", "ordem_corte", "codigo_corte",
                           "descricao", "usuario_finalizacao"],
            "show_cols": ["id", "entrada_id", "envio_id", "corte_id", "ordem_corte", "codigo_corte",
                          "descricao", "status", "usuario_finalizacao", "created_at"],
        },
        {
            "table": "pecas_finalizadas",
            "label": "Pecas finalizadas",
            "date_cols": ["data_conferencia", "data_pagamento", "data_chegada", "data_envio"],
            "status_cols": ["status", "pago"],
            "match_cols": ["id", "corte_id", "entrada_id", "codigo", "descricao", "costureira", "pagamento_id"],
            "show_cols": ["id", "corte_id", "entrada_id", "codigo", "descricao", "costureira", "status",
                          "pago", "valor_pago", "pagamento_id", "data_pagamento"],
        },
        {
            "table": "adiantamento_faccao",
            "label": "Adiantamento",
            "date_cols": ["data_hora"],
            "status_cols": ["forma_pagamento"],
            "match_cols": ["id", "corte_id", "codigo_modelo", "faccao", "forma_pagamento"],
            "show_cols": ["id", "corte_id", "codigo_modelo", "faccao", "valor", "forma_pagamento",
                          "parcelas", "data_hora"],
        },
        {
            "table": "pagamento_corte_acabamento",
            "label": "Pagamento de corte/acabamento",
            "date_cols": ["data_pagamento"],
            "status_cols": ["estornado"],
            "match_cols": ["id", "codigo", "descricao", "costureira", "tipo_servico"],
            "show_cols": ["id", "costureira", "tipo_servico", "codigo", "descricao", "quantidade_finalizada",
                          "total_pago", "data_pagamento", "estornado"],
        },
        {
            "table": "pagamento_servicos",
            "label": "Pagamento de servicos",
            "date_cols": ["data_pagamento", "data_registro"],
            "status_cols": [],
            "match_cols": ["id", "nome_prestador", "observacoes", "usuario_pagamento", "mes_referencia"],
            "show_cols": ["id", "nome_prestador", "data_pagamento", "valor_total", "valor_liquido",
                          "mes_referencia", "usuario_pagamento", "data_registro"],
            "related_key": "pagamento_servicos",
            "related_col": "id",
        },
        {
            "table": "defeitos_envios",
            "label": "Retrabalho/defeitos",
            "date_cols": ["data_envio", "data_retorno", "data_pagamento", "created_at", "updated_at"],
            "status_cols": ["status"],
            "match_cols": ["id", "historico_id", "envio_id", "envio_corte_id", "codigo_corte",
                           "descricao_corte", "prestador", "tipo_servico"],
            "show_cols": ["id", "envio_id", "envio_corte_id", "codigo_corte", "descricao_corte", "prestador",
                          "tipo_servico", "quantidade", "status", "data_envio", "data_retorno", "data_pagamento"],
        },
    ]

    def __init__(self, master, sistema=None):
        super().__init__(master)
        self.master = master
        self.sistema = sistema
        self.configure(fg_color=self._cor("fundo", "#f8fafc"))
        self._rows_by_iid: dict[str, dict[str, Any]] = {}
        self._last_result: dict[str, Any] | None = None
        self._build_ui()

    def _cor(self, nome: str, fallback: str) -> str:
        return getattr(self.sistema, f"cor_{nome}", fallback)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="BUSCA PROFUNDA DE CORTE",
            font=("Arial", 22, "bold"),
            text_color=self._cor("texto", "#111827"),
        ).grid(row=0, column=0, sticky="w")

        self.status_label = ctk.CTkLabel(
            header,
            text="Digite o codigo, ordem ou ID do corte para rastrear todas as etapas.",
            text_color=self._cor("texto", "#334155"),
        )
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        search = ctk.CTkFrame(self, fg_color=self._cor("secundaria", "#ffffff"), corner_radius=8)
        search.grid(row=1, column=0, sticky="ew", padx=18, pady=8)
        search.grid_columnconfigure(0, weight=1)

        self.busca_var = tk.StringVar()
        self.busca_entry = ctk.CTkEntry(
            search,
            textvariable=self.busca_var,
            placeholder_text="Codigo do corte, numero da ordem ou ID",
            height=38,
        )
        self.busca_entry.grid(row=0, column=0, sticky="ew", padx=(12, 8), pady=12)
        self.busca_entry.bind("<Return>", lambda _event: self.buscar())

        ctk.CTkButton(search, text="Buscar", width=120, command=self.buscar).grid(
            row=0, column=1, padx=6, pady=12
        )
        ctk.CTkButton(search, text="Imprimir", width=120, command=self.imprimir_relatorio).grid(
            row=0, column=2, padx=(6, 12), pady=12
        )

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=18, pady=(8, 18))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(1, weight=1)

        self.resumo_frame = ctk.CTkFrame(body, fg_color=self._cor("secundaria", "#ffffff"), corner_radius=8)
        self.resumo_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        for col in range(4):
            self.resumo_frame.grid_columnconfigure(col, weight=1)

        self.resumo_vars = {}
        for col, (key, label) in enumerate([
            ("codigo", "Codigo"),
            ("etapa", "Etapa atual"),
            ("tempo", "Tempo na etapa"),
            ("registros", "Registros"),
        ]):
            frame = ctk.CTkFrame(self.resumo_frame, fg_color="transparent")
            frame.grid(row=0, column=col, sticky="ew", padx=10, pady=10)
            ctk.CTkLabel(frame, text=label, font=("Arial", 11, "bold"),
                         text_color=self._cor("texto", "#475569")).pack(anchor="w")
            var = tk.StringVar(value="-")
            self.resumo_vars[key] = var
            ctk.CTkLabel(frame, textvariable=var, font=("Arial", 15, "bold"),
                         text_color=self._cor("texto", "#111827"), wraplength=260).pack(anchor="w")

        left = ctk.CTkFrame(body, fg_color=self._cor("secundaria", "#ffffff"), corner_radius=8)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(left, text="Linha do tempo", font=("Arial", 15, "bold"),
                     text_color=self._cor("texto", "#111827")).grid(row=0, column=0, sticky="w", padx=12, pady=10)

        cols = ("data", "etapa", "status", "referencia", "tempo")
        self.timeline_tree = ttk.Treeview(left, columns=cols, show="headings", height=16)
        headings = {
            "data": "Data",
            "etapa": "Etapa",
            "status": "Status",
            "referencia": "Referencia",
            "tempo": "Tempo ate agora",
        }
        widths = {"data": 135, "etapa": 180, "status": 120, "referencia": 230, "tempo": 130}
        for col in cols:
            self.timeline_tree.heading(col, text=headings[col])
            self.timeline_tree.column(col, width=widths[col], anchor="w")
        self.timeline_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.timeline_tree.bind("<<TreeviewSelect>>", self._on_select_event)

        right = ctk.CTkFrame(body, fg_color=self._cor("secundaria", "#ffffff"), corner_radius=8)
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(right, text="Detalhes do registro", font=("Arial", 15, "bold"),
                     text_color=self._cor("texto", "#111827")).grid(row=0, column=0, sticky="w", padx=12, pady=10)
        self.detail_text = ctk.CTkTextbox(right, wrap="word")
        self.detail_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._set_detail("Nenhuma busca realizada.")

    def _set_detail(self, text: str):
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", text)
        self.detail_text.configure(state="disabled")

    def _fetch_rows(self, cur, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        cur.execute(sql, params)
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def _columns(self, cur, schema: str, table: str) -> set[str]:
        cur.execute(
            """
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = %s AND table_name = %s
             ORDER BY ordinal_position
            """,
            (schema, table),
        )
        return {row[0] for row in cur.fetchall()}

    def _table_exists(self, cur, schema: str, table: str) -> bool:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                 WHERE table_schema = %s AND table_name = %s
            )
            """,
            (schema, table),
        )
        row = cur.fetchone()
        return bool(row and row[0])

    def _build_conditions(
        self,
        spec: dict[str, Any],
        columns: set[str],
        terms: list[str],
        related_ids: dict[str, set[Any]],
    ) -> tuple[str, list[Any]]:
        conditions = []
        params: list[Any] = []

        numeric_terms = [int(t) for t in terms if str(t).strip().isdigit()]
        for col in spec.get("match_cols", []):
            if col not in columns:
                continue
            if col.endswith("_id") or col == "id":
                for n in numeric_terms:
                    conditions.append(f"{_qident(col)} = %s")
                    params.append(n)
            for term in terms:
                if term:
                    conditions.append(f"{_qident(col)}::text ILIKE %s")
                    params.append(f"%{term}%")

        if "corte_id" in columns and related_ids.get("cadastro_de_corte"):
            ids = sorted(related_ids["cadastro_de_corte"])
            conditions.append(f"corte_id = ANY(%s)")
            params.append(ids)

        related_key = spec.get("related_key")
        related_col = spec.get("related_col")
        if related_key and related_col in columns and related_ids.get(related_key):
            ids = sorted(related_ids[related_key])
            conditions.append(f"{_qident(related_col)} = ANY(%s)")
            params.append(ids)

        if "envio_id" in columns and related_ids.get("envios_cortes"):
            ids = sorted(related_ids["envios_cortes"])
            conditions.append("envio_id = ANY(%s)")
            params.append(ids)

        if "retorno_id" in columns and related_ids.get("controle_retorno_cortes"):
            ids = sorted(related_ids["controle_retorno_cortes"])
            conditions.append("retorno_id = ANY(%s)")
            params.append(ids)

        if "pagamento_id" in columns and related_ids.get("pagamento_servicos"):
            ids = sorted(related_ids["pagamento_servicos"])
            conditions.append("pagamento_id = ANY(%s)")
            params.append(ids)

        if not conditions:
            return "", []
        return " OR ".join(f"({cond})" for cond in conditions), params

    def _select_stage_rows(
        self,
        cur,
        schema: str,
        spec: dict[str, Any],
        columns: set[str],
        terms: list[str],
        related_ids: dict[str, set[Any]],
    ) -> list[dict[str, Any]]:
        where_sql, params = self._build_conditions(spec, columns, terms, related_ids)
        if not where_sql:
            return []

        select_cols = ["id"] if "id" in columns else []
        for col in spec.get("show_cols", []):
            if col in columns and col not in select_cols:
                select_cols.append(col)
        for col in spec.get("date_cols", []) + spec.get("status_cols", []):
            if col in columns and col not in select_cols:
                select_cols.append(col)
        if not select_cols:
            select_cols = sorted(columns)[:12]

        order_candidates = [col for col in spec.get("date_cols", []) if col in columns]
        order_sql = f"ORDER BY {_qident(order_candidates[0])} DESC NULLS LAST" if order_candidates else ""
        sql = (
            f"SELECT {', '.join(_qident(c) for c in select_cols)} "
            f"FROM {_qident(schema)}.{_qident(spec['table'])} "
            f"WHERE {where_sql} {order_sql} LIMIT 100"
        )
        return self._fetch_rows(cur, sql, tuple(params))

    def _event_from_row(self, spec: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
        data = None
        for col in spec.get("date_cols", []):
            data = _parse_dt(row.get(col))
            if data:
                break
        status_parts = []
        for col in spec.get("status_cols", []):
            if col in row and row.get(col) not in (None, ""):
                if isinstance(row.get(col), bool):
                    if col == "pago":
                        status_parts.append("Pago" if row.get(col) else "Pendente")
                    elif col == "estornado":
                        status_parts.append("Estornado" if row.get(col) else "Ativo")
                    else:
                        status_parts.append("Sim" if row.get(col) else "Nao")
                else:
                    status_parts.append(_as_text(row.get(col)))
        status = " / ".join(dict.fromkeys(status_parts)) or "-"

        ref_cols = ("codigo", "codigo_corte", "codigo_modelo", "ordem_corte", "numero_ordem", "descricao",
                    "descricao_corte", "nome_prestador", "costureira", "faccao")
        refs = [_as_text(row.get(col)) for col in ref_cols if row.get(col)]
        referencia = " | ".join(dict.fromkeys(refs[:3])) or f"ID {row.get('id', '-')}"

        return {
            "table": spec["table"],
            "etapa": spec["label"],
            "data": data,
            "status": status,
            "referencia": referencia,
            "row": row,
        }

    def _collect_related_ids(self, related_ids: dict[str, set[Any]], table: str, row: dict[str, Any]):
        if row.get("id") is not None:
            related_ids.setdefault(table, set()).add(row["id"])
        if row.get("corte_id") is not None:
            related_ids.setdefault("cadastro_de_corte", set()).add(row["corte_id"])
        if row.get("envio_id") is not None:
            related_ids.setdefault("envios_cortes", set()).add(row["envio_id"])
            related_ids.setdefault("controle_envio_cortes", set()).add(row["envio_id"])
        if row.get("retorno_id") is not None:
            related_ids.setdefault("controle_retorno_cortes", set()).add(row["retorno_id"])
        if row.get("entrada_id") is not None:
            related_ids.setdefault("entrada_acabamento", set()).add(row["entrada_id"])
        if row.get("pagamento_id") is not None:
            related_ids.setdefault("pagamento_servicos", set()).add(row["pagamento_id"])

    def _collect_terms(self, terms: list[str], row: dict[str, Any]):
        for col in ("codigo", "codigo_corte", "codigo_modelo", "ordem_corte", "numero_ordem"):
            value = _as_text(row.get(col)).strip()
            if value and value not in terms:
                terms.append(value)

    def buscar(self):
        termo = self.busca_var.get().strip()
        if not termo:
            messagebox.showwarning("Aviso", "Digite o codigo, ordem ou ID do corte.")
            return

        self.status_label.configure(text="Buscando em todas as etapas...")
        self.update_idletasks()

        try:
            result = self._buscar_no_banco(termo)
        except Exception as exc:
            self.status_label.configure(text="Falha ao buscar.")
            messagebox.showerror("Erro", f"Falha na busca profunda:\n{exc}")
            return

        self._last_result = result
        self._render_result(result)

    def _buscar_no_banco(self, termo: str) -> dict[str, Any]:
        schema = get_schema() or "opera"
        events: list[dict[str, Any]] = []
        related_ids: dict[str, set[Any]] = {}
        terms = [termo]

        conn = get_conn()
        try:
            cur = conn.cursor()
            try:
                cur.execute(f"SET search_path TO {_qident(schema)}, public")
            except Exception:
                pass

            for _pass in range(3):
                found_this_pass = 0
                for spec in self.ETAPAS:
                    table = spec["table"]
                    if not self._table_exists(cur, schema, table):
                        continue
                    columns = self._columns(cur, schema, table)
                    rows = self._select_stage_rows(cur, schema, spec, columns, terms, related_ids)
                    seen_keys = {(event["table"], event["row"].get("id")) for event in events}
                    for row in rows:
                        key = (table, row.get("id"))
                        if key in seen_keys:
                            continue
                        event = self._event_from_row(spec, row)
                        events.append(event)
                        seen_keys.add(key)
                        found_this_pass += 1
                        self._collect_related_ids(related_ids, table, row)
                        self._collect_terms(terms, row)
                if found_this_pass == 0:
                    break

            # Relaciona pagamento_servicos via pagamento_servicos_detalhe quando houver entradas.
            if related_ids.get("entrada_acabamento") and self._table_exists(cur, schema, "pagamento_servicos_detalhe"):
                entry_ids = sorted(related_ids["entrada_acabamento"])
                rows = self._fetch_rows(
                    cur,
                    f"""
                    SELECT pagamento_id, entrada_acabamento_id, valor_servico
                      FROM {_qident(schema)}.pagamento_servicos_detalhe
                     WHERE entrada_acabamento_id = ANY(%s)
                    """,
                    (entry_ids,),
                )
                for row in rows:
                    self._collect_related_ids(related_ids, "pagamento_servicos_detalhe", row)

            if related_ids.get("pagamento_servicos") and self._table_exists(cur, schema, "pagamento_servicos"):
                ids = sorted(related_ids["pagamento_servicos"])
                seen_keys = {(event["table"], event["row"].get("id")) for event in events}
                rows = self._fetch_rows(
                    cur,
                    f"""
                    SELECT id, nome_prestador, data_pagamento, valor_total, valor_liquido,
                           mes_referencia, usuario_pagamento, data_registro
                      FROM {_qident(schema)}.pagamento_servicos
                     WHERE id = ANY(%s)
                    """,
                    (ids,),
                )
                spec = next(item for item in self.ETAPAS if item["table"] == "pagamento_servicos")
                for row in rows:
                    key = ("pagamento_servicos", row.get("id"))
                    if key not in seen_keys:
                        events.append(self._event_from_row(spec, row))
                        seen_keys.add(key)

            events.sort(key=lambda item: item["data"] or datetime.min)
            return {"termo": termo, "events": events, "related_ids": related_ids, "terms": terms}
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _etapa_atual(self, events: list[dict[str, Any]]) -> tuple[str, datetime | None]:
        if not events:
            return "Nao localizado", None
        priority = {
            "pagamento_servicos": 90,
            "pagamento_corte_acabamento": 90,
            "pecas_finalizadas": 80,
            "cortes_finalizados": 80,
            "cortes_finalizados_completo": 80,
            "entrada_acabamento": 70,
            "controle_retorno_cortes": 60,
            "defeitos_envios": 55,
            "envios_cortes": 50,
            "controle_envio_cortes": 45,
            "cadastro_de_corte": 30,
            "ordem_corte_ficha": 20,
            "adiantamento_faccao": 10,
        }
        latest = max(events, key=lambda event: (priority.get(event["table"], 0), event["data"] or datetime.min))
        label = latest["etapa"]
        if latest["status"] and latest["status"] != "-":
            label = f"{label} ({latest['status']})"
        return label, latest["data"]

    def _render_result(self, result: dict[str, Any]):
        for item in self.timeline_tree.get_children():
            self.timeline_tree.delete(item)
        self._rows_by_iid.clear()

        events = result["events"]
        etapa, desde = self._etapa_atual(events)
        codigo = next((term for term in result.get("terms", []) if term), result["termo"])

        self.resumo_vars["codigo"].set(codigo)
        self.resumo_vars["etapa"].set(etapa)
        self.resumo_vars["tempo"].set(_tempo_decorrido(desde) if desde else "-")
        self.resumo_vars["registros"].set(str(len(events)))

        if not events:
            self.status_label.configure(text="Nenhum registro encontrado para este codigo.")
            self._set_detail("Nenhum registro encontrado. Verifique se o codigo/ordem foi digitado exatamente.")
            return

        previous_dt = None
        for index, event in enumerate(events, start=1):
            data = event["data"]
            tempo = _tempo_decorrido(data) if data else ""
            if previous_dt and data:
                tempo = f"{_tempo_decorrido(previous_dt, data)} apos etapa anterior"
            values = (_as_text(data), event["etapa"], event["status"], event["referencia"], tempo)
            iid = self.timeline_tree.insert("", "end", values=values)
            self._rows_by_iid[iid] = event
            if data:
                previous_dt = data

        first = self.timeline_tree.get_children()[0]
        self.timeline_tree.selection_set(first)
        self.timeline_tree.focus(first)
        self._on_select_event()
        self.status_label.configure(text=f"Busca concluida: {len(events)} registro(s) encontrados.")

    def _on_select_event(self, _event=None):
        sel = self.timeline_tree.selection()
        if not sel:
            return
        event = self._rows_by_iid.get(sel[0])
        if not event:
            return
        row = event["row"]
        lines = [
            f"Etapa: {event['etapa']}",
            f"Tabela: {event['table']}",
            f"Data: {_as_text(event['data']) or '-'}",
            f"Status: {event['status']}",
            "",
            "Campos encontrados:",
        ]
        for key, value in row.items():
            if value not in (None, ""):
                lines.append(f"- {key}: {_as_text(value)}")
        self._set_detail("\n".join(lines))

    def imprimir_relatorio(self):
        if not self._last_result or not self._last_result.get("events"):
            messagebox.showwarning("Aviso", "Faça uma busca com resultados antes de imprimir.")
            return

        events = self._last_result["events"]
        etapa, desde = self._etapa_atual(events)
        codigo = self.resumo_vars["codigo"].get()

        rows_html = []
        for event in events:
            detalhe = "<br>".join(
                f"<b>{html.escape(str(k))}</b>: {html.escape(_as_text(v))}"
                for k, v in event["row"].items()
                if v not in (None, "")
            )
            rows_html.append(
                "<tr>"
                f"<td>{html.escape(_as_text(event['data']))}</td>"
                f"<td>{html.escape(event['etapa'])}</td>"
                f"<td>{html.escape(event['status'])}</td>"
                f"<td>{html.escape(event['referencia'])}</td>"
                f"<td>{detalhe}</td>"
                "</tr>"
            )

        content = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Rastreamento do Corte {html.escape(codigo)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #111827; margin: 28px; }}
    h1 {{ font-size: 22px; margin: 0 0 6px; }}
    .meta {{ margin: 0 0 18px; color: #475569; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 18px; }}
    .card {{ border: 1px solid #cbd5e1; padding: 10px; border-radius: 6px; }}
    .label {{ color: #475569; font-size: 11px; font-weight: bold; text-transform: uppercase; }}
    .value {{ font-size: 15px; font-weight: bold; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 7px; vertical-align: top; }}
    th {{ background: #e2e8f0; text-align: left; }}
    @media print {{ body {{ margin: 12mm; }} .cards {{ grid-template-columns: repeat(2, 1fr); }} }}
  </style>
</head>
<body>
  <h1>Rastreamento do Corte {html.escape(codigo)}</h1>
  <p class="meta">Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
  <div class="cards">
    <div class="card"><div class="label">Etapa atual</div><div class="value">{html.escape(etapa)}</div></div>
    <div class="card"><div class="label">Tempo na etapa</div><div class="value">{html.escape(_tempo_decorrido(desde) if desde else '-')}</div></div>
    <div class="card"><div class="label">Registros</div><div class="value">{len(events)}</div></div>
    <div class="card"><div class="label">Termos vinculados</div><div class="value">{html.escape(', '.join(self._last_result.get('terms', [])[:6]))}</div></div>
  </div>
  <table>
    <thead>
      <tr><th>Data</th><th>Etapa</th><th>Status</th><th>Referencia</th><th>Detalhes</th></tr>
    </thead>
    <tbody>
      {''.join(rows_html)}
    </tbody>
  </table>
  <script>window.onload = function() {{ setTimeout(function() {{ window.print(); }}, 300); }};</script>
</body>
</html>"""

        fd, path = tempfile.mkstemp(prefix="rastreamento_corte_", suffix=".html")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        webbrowser.open(f"file:///{path.replace(os.sep, '/')}")


if __name__ == "__main__":
    root = ctk.CTk()
    root.geometry("1200x760")
    root.title("Busca Profunda de Corte")
    BuscaProfundaCortePage(root).pack(fill="both", expand=True)
    root.mainloop()
