# -*- coding: utf-8 -*-
"""
RECIBOS_PAGAMENTOS.py
Página para visualizar e organizar recibos de pagamentos salvos em disco.
"""
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime

import customtkinter as ctk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
from TEMAS import get_contraste_texto

SERVICE_FILTER_OPTIONS = [
    "Todos", "Facção", "Bordado", "Caseador", "Botões",
    "Estamparia", "Tingimento", "Outros Trabalhos"
]


class RecibosPagamentosPage(ctk.CTkFrame):
    PAGE_TITLE = "Recibos de Pagamentos"

    def __init__(self, parent, host=None, sistema=None, app=None, **kwargs):
        super().__init__(parent, **kwargs)

        sistema_kw = sistema or app
        if host is None:
            host = (
                sistema_kw
                or kwargs.get("sistema")
                or kwargs.get("app")
                or kwargs.get("controller")
                or kwargs.get("ctx")
                or kwargs.get("root")
                or kwargs.get("main")
            )

        self.host = host
        origem = host or sistema_kw
        theme_from_host = getattr(origem, "theme", None) if origem is not None else None

        if theme_from_host is not None:
            self.theme = theme_from_host
        else:
            cf = getattr(origem, "cor_fundo", "#0f1720") if origem else "#0f1720"
            cp = getattr(origem, "cor_primaria", "#1f2937") if origem else "#1f2937"
            cs = getattr(origem, "cor_secundaria", "#111827") if origem else "#111827"
            ct = getattr(origem, "cor_texto", "#e5e7eb") if origem else "#e5e7eb"
            ct3 = getattr(origem, "cor_terciaria", "#0b1220") if origem else "#0b1220"
            cd = getattr(origem, "cor_destaque", "#2563eb") if origem else "#2563eb"
            ch = getattr(origem, "cor_hover", "#334155") if origem else "#334155"
            ci = getattr(origem, "cor_imprimir", "#ffffff") if origem else "#ffffff"
            cb = getattr(origem, "cor_borda", "#273244") if origem else "#273244"

            self.theme = type("T", (), {
                "cor_fundo": cf,
                "cor_primaria": cp,
                "cor_secundaria": cs,
                "cor_terciaria": ct3,
                "cor_texto": ct,
                "cor_destaque": cd,
                "cor_hover": ch,
                "cor_imprimir": ci,
                "cor_borda": cb,
            })()

        self.configure(fg_color=self.theme.cor_fundo)
        self.receipts_dir = os.path.join(os.getcwd(), "RECIBOS_DE_PAGAMENTOS")
        self._build_ui()
        self._load_receipts()

    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, corner_radius=0, fg_color=self.theme.cor_fundo)
        top.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            top,
            text=self.PAGE_TITLE,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.cor_texto,
        ).grid(row=0, column=0, padx=16, pady=10, sticky="w")

        toolbar = ctk.CTkFrame(self, fg_color=self.theme.cor_secundaria)
        toolbar.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 6))
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.grid_columnconfigure(3, weight=0)

        ctk.CTkLabel(
            toolbar,
            text="Buscar",
            text_color=self.theme.cor_texto,
        ).grid(row=0, column=0, padx=(12, 6), pady=8, sticky="w")

        self.search_var = ctk.StringVar(value="")
        self.search_entry = ctk.CTkEntry(
            toolbar,
            textvariable=self.search_var,
            fg_color=self.theme.cor_terciaria,
            border_color=self.theme.cor_borda,
            text_color=self.theme.cor_texto,
        )
        self.search_entry.grid(row=0, column=1, padx=(0, 12), pady=8, sticky="ew")
        self.search_entry.bind("<Return>", lambda _e: self._load_receipts())

        self.prestador_var = ctk.StringVar(value="Todos")
        self.prestador_combo = ctk.CTkComboBox(
            toolbar,
            values=SERVICE_FILTER_OPTIONS,
            variable=self.prestador_var,
            fg_color=self.theme.cor_terciaria,
            border_color=self.theme.cor_borda,
            text_color=self.theme.cor_texto,
            button_color=self.theme.cor_primaria,
            button_hover_color=self.theme.cor_hover,
            dropdown_fg_color=self.theme.cor_terciaria,
            dropdown_hover_color=self.theme.cor_hover,
            dropdown_text_color=self.theme.cor_texto,
            command=lambda _v: self._load_receipts(),
        )
        self.prestador_combo.grid(row=0, column=2, padx=(0, 12), pady=8, sticky="w")

        def _btn_text(color: str) -> str:
            try:
                return get_contraste_texto(color)
            except Exception:
                return self.theme.cor_texto

        ctk.CTkButton(
            toolbar,
            text="🔄 Atualizar",
            command=self._load_receipts,
            fg_color=self.theme.cor_primaria,
            hover_color=self.theme.cor_hover,
            text_color=_btn_text(self.theme.cor_primaria),
        ).grid(row=0, column=3, padx=6, pady=8)

        ctk.CTkButton(
            toolbar,
            text="🖨️ Imprimir",
            command=self._imprimir_selecionado,
            fg_color=self.theme.cor_destaque,
            hover_color=self.theme.cor_hover,
            text_color=_btn_text(self.theme.cor_destaque),
        ).grid(row=0, column=4, padx=6, pady=8)

        ctk.CTkButton(
            toolbar,
            text="📤 Exportar",
            command=self._exportar_selecionado,
            fg_color=self.theme.cor_primaria,
            hover_color=self.theme.cor_hover,
            text_color=_btn_text(self.theme.cor_primaria),
        ).grid(row=0, column=5, padx=(6, 12), pady=8)

        content = ctk.CTkFrame(self, fg_color=self.theme.cor_terciaria)
        content.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure(
            "Recibos.Treeview",
            background=self.theme.cor_terciaria,
            fieldbackground=self.theme.cor_terciaria,
            foreground=self.theme.cor_texto,
            rowheight=24,
        )
        style.map(
            "Recibos.Treeview",
            background=[("selected", self.theme.cor_destaque)],
        )

        columns = ("prestador", "data", "valor", "arquivo")
        headers = ["PRESTADOR", "DATA", "VALOR", "ARQUIVO"]
        widths = [220, 160, 120, 420]
        anchors = ["w", "center", "e", "w"]

        self.tree = ttk.Treeview(
            content,
            columns=columns,
            show="headings",
            style="Recibos.Treeview",
        )
        for col, header, width, anchor in zip(columns, headers, widths, anchors):
            self.tree.heading(col, text=header)
            self.tree.column(col, width=width, anchor=anchor, stretch=True)
        self.tree.grid(row=0, column=0, sticky="nsew")

        vs = ttk.Scrollbar(content, orient="vertical", command=self.tree.yview)
        hs = ttk.Scrollbar(content, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")

        hint = ctk.CTkLabel(
            self,
            text="Dica: use o campo de busca para filtrar por prestador, data ou valor.",
            text_color=self.theme.cor_texto,
            font=ctk.CTkFont(size=11),
        )
        hint.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 8))

    def _parse_receipt_filename(self, filename: str) -> dict:
        base = os.path.splitext(filename)[0]
        pattern = r"^RECIBO_(?P<prestador>.+)_(?P<data>\d{8}_\d{4})_R\$_(?P<valor>[\d_]+)$"
        match = re.match(pattern, base, re.IGNORECASE)
        info = {
            "prestador": "Não identificado",
            "data": "",
            "valor": "",
        }

        if match:
            prestador = match.group("prestador").replace("_", " ").title()
            data_raw = match.group("data")
            valor_raw = match.group("valor").replace("_", ".")
            try:
                data_fmt = datetime.strptime(data_raw, "%Y%m%d_%H%M").strftime("%d/%m/%Y %H:%M")
            except Exception:
                data_fmt = data_raw
            info.update({
                "prestador": prestador,
                "data": data_fmt,
                "valor": f"R$ {float(valor_raw):,.2f}",
            })
        return info

    def _load_receipts(self):
        termo = (self.search_var.get() or "").strip().lower()
        prestador_filtro = (self.prestador_var.get() or "Todos").strip().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not os.path.isdir(self.receipts_dir):
            os.makedirs(self.receipts_dir, exist_ok=True)

        arquivos = [
            f for f in os.listdir(self.receipts_dir)
            if f.lower().endswith(".pdf")
        ]

        def _mtime(name: str) -> float:
            return os.path.getmtime(os.path.join(self.receipts_dir, name))

        arquivos.sort(key=_mtime, reverse=True)
        for filename in arquivos:
            info = self._parse_receipt_filename(filename)
            path = os.path.join(self.receipts_dir, filename)
            if prestador_filtro != "todos":
                if prestador_filtro not in info["prestador"].lower():
                    continue
            if termo:
                haystack = " ".join([info["prestador"], info["data"], info["valor"], filename]).lower()
                if termo not in haystack:
                    continue
            values = (info["prestador"], info["data"], info["valor"], filename)
            self.tree.insert("", "end", values=values, tags=(path,))

    def _get_selected_path(self) -> str | None:
        selection = self.tree.selection()
        if not selection:
            return None
        tags = self.tree.item(selection[0], "tags")
        return tags[0] if tags else None

    def _imprimir_selecionado(self):
        path = self._get_selected_path()
        if not path:
            messagebox.showwarning("Recibos", "Selecione um recibo para imprimir.")
            return
        if not os.path.exists(path):
            messagebox.showerror("Recibos", "Arquivo não encontrado.")
            return
        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                import subprocess
                import sys

                if sys.platform == "darwin":
                    subprocess.run(["open", path])
                else:
                    subprocess.run(["xdg-open", path])
        except Exception as exc:
            messagebox.showerror("Recibos", f"Falha ao abrir o recibo: {exc}")

    def _exportar_selecionado(self):
        path = self._get_selected_path()
        if not path:
            messagebox.showwarning("Recibos", "Selecione um recibo para exportar.")
            return
        if not os.path.exists(path):
            messagebox.showerror("Recibos", "Arquivo não encontrado.")
            return

        filename = os.path.basename(path)
        destino = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=filename,
            filetypes=[("PDF", "*.pdf")],
            title="Exportar Recibo",
        )
        if not destino:
            return
        try:
            shutil.copy2(path, destino)
            messagebox.showinfo("Recibos", f"Recibo exportado para:\n{destino}")
        except Exception as exc:
            messagebox.showerror("Recibos", f"Falha ao exportar recibo: {exc}")
