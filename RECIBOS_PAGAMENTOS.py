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

        # ============ CORREÇÃO: BOTÕES COM CORES ESPECÍFICAS ============
        # Função para calcular contraste de texto
        def _get_contrast_text_color(bg_color: str) -> str:
            """Calcula cor do texto com melhor contraste"""
            try:
                if not bg_color or not isinstance(bg_color, str):
                    return "#000000"

                hex_color = bg_color.lstrip('#')
                if len(hex_color) != 6:
                    return "#000000"

                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)

                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                return "#000000" if luminance > 0.5 else "#FFFFFF"
            except Exception:
                return "#000000"

        # Função para ajustar cor para hover (escurece)
        def _adjust_hover_color(base_color: str, factor: float = 0.85) -> str:
            """Ajusta cor para efeito hover"""
            try:
                if not base_color or not isinstance(base_color, str):
                    return base_color

                hex_color = base_color.lstrip('#')
                if len(hex_color) != 6:
                    return base_color

                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)

                r = int(r * factor)
                g = int(g * factor)
                b = int(b * factor)

                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))

                return f"#{r:02x}{g:02x}{b:02x}".upper()
            except Exception:
                return base_color

        # Cores específicas para cada botão (como solicitado)
        CORES_BOTOES = {
            'atualizar': "#3B82F6",  # Azul
            'imprimir': "#10B981",  # Verde
            'exportar': "#F59E0B",  # Laranja
        }

        # Se o tema tiver cores específicas para botões, usa-as
        if hasattr(self.theme, 'cor_botao_padrao'):
            CORES_BOTOES['atualizar'] = self.theme.cor_botao_padrao
        if hasattr(self.theme, 'cor_botao_imprimir'):
            CORES_BOTOES['imprimir'] = self.theme.cor_botao_imprimir
        if hasattr(self.theme, 'cor_botao_exportar'):
            CORES_BOTOES['exportar'] = self.theme.cor_botao_exportar

        # Botão Atualizar (AZUL)
        btn_atualizar_cor = CORES_BOTOES['atualizar']
        self.btn_atualizar = ctk.CTkButton(
            toolbar,
            text="🔄 Atualizar",
            command=self._load_receipts,
            fg_color=btn_atualizar_cor,
            hover_color=_adjust_hover_color(btn_atualizar_cor),
            text_color=_get_contrast_text_color(btn_atualizar_cor),
            border_width=1,
            border_color=self.theme.cor_borda,
            corner_radius=6,
            height=32,
            width=100,
        )
        self.btn_atualizar.grid(row=0, column=3, padx=6, pady=8)

        # Botão Imprimir (VERDE)
        btn_imprimir_cor = CORES_BOTOES['imprimir']
        self.btn_imprimir = ctk.CTkButton(
            toolbar,
            text="🖨️ Imprimir",
            command=self._imprimir_selecionado,
            fg_color=btn_imprimir_cor,
            hover_color=_adjust_hover_color(btn_imprimir_cor),
            text_color=_get_contrast_text_color(btn_imprimir_cor),
            border_width=1,
            border_color=self.theme.cor_borda,
            corner_radius=6,
            height=32,
            width=100,
        )
        self.btn_imprimir.grid(row=0, column=4, padx=6, pady=8)

        # Botão Exportar (LARANJA)
        btn_exportar_cor = CORES_BOTOES['exportar']
        self.btn_exportar = ctk.CTkButton(
            toolbar,
            text="📤 Exportar",
            command=self._exportar_selecionado,
            fg_color=btn_exportar_cor,
            hover_color=_adjust_hover_color(btn_exportar_cor),
            text_color=_get_contrast_text_color(btn_exportar_cor),
            border_width=1,
            border_color=self.theme.cor_borda,
            corner_radius=6,
            height=32,
            width=100,
        )
        self.btn_exportar.grid(row=0, column=5, padx=(6, 12), pady=8)
        # ============ FIM DA CORREÇÃO ============

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

        # Adiciona método para atualizar cores quando o tema mudar
        self.update_theme_colors = lambda: self._update_theme_colors()

    def _update_theme_colors(self):
        """Atualiza as cores dos botões quando o tema é alterado"""
        if not hasattr(self, 'btn_atualizar') or not self.btn_atualizar.winfo_exists():
            return

        # Funções auxiliares
        def _get_contrast_text_color(bg_color: str) -> str:
            try:
                if not bg_color or not isinstance(bg_color, str):
                    return "#000000"
                hex_color = bg_color.lstrip('#')
                if len(hex_color) != 6:
                    return "#000000"
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                return "#000000" if luminance > 0.5 else "#FFFFFF"
            except Exception:
                return "#000000"

        def _adjust_hover_color(base_color: str, factor: float = 0.85) -> str:
            try:
                if not base_color or not isinstance(base_color, str):
                    return base_color
                hex_color = base_color.lstrip('#')
                if len(hex_color) != 6:
                    return base_color
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                r = int(r * factor)
                g = int(g * factor)
                b = int(b * factor)
                r = max(0, min(255, r))
                g = max(0, min(255, g))
                b = max(0, min(255, b))
                return f"#{r:02x}{g:02x}{b:02x}".upper()
            except Exception:
                return base_color

        # Define cores base (com fallback para cores do tema se disponíveis)
        cores = {
            'atualizar': "#3B82F6",  # Azul
            'imprimir': "#10B981",  # Verde
            'exportar': "#F59E0B",  # Laranja
        }

        # Se o tema tiver cores específicas, usa-as
        if hasattr(self.theme, 'cor_botao_padrao'):
            cores['atualizar'] = self.theme.cor_botao_padrao
        if hasattr(self.theme, 'cor_botao_imprimir'):
            cores['imprimir'] = self.theme.cor_botao_imprimir
        if hasattr(self.theme, 'cor_botao_exportar'):
            cores['exportar'] = self.theme.cor_botao_exportar

        # Atualiza botão Atualizar (AZUL)
        self.btn_atualizar.configure(
            fg_color=cores['atualizar'],
            hover_color=_adjust_hover_color(cores['atualizar']),
            text_color=_get_contrast_text_color(cores['atualizar']),
            border_color=self.theme.cor_borda,
        )

        # Atualiza botão Imprimir (VERDE)
        self.btn_imprimir.configure(
            fg_color=cores['imprimir'],
            hover_color=_adjust_hover_color(cores['imprimir']),
            text_color=_get_contrast_text_color(cores['imprimir']),
            border_color=self.theme.cor_borda,
        )

        # Atualiza botão Exportar (LARANJA)
        self.btn_exportar.configure(
            fg_color=cores['exportar'],
            hover_color=_adjust_hover_color(cores['exportar']),
            text_color=_get_contrast_text_color(cores['exportar']),
            border_color=self.theme.cor_borda,
        )

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

    def _btn_style_por_tema(self, tipo: str = "secundario") -> dict:
        """
        Retorna um dict pronto para passar no CTkButton(**dict),
        ajustando automaticamente as cores para Tema Claro/Escuro.

        tipo:
          - "primario"   -> botão principal (ex: Imprimir)
          - "secundario" -> botões comuns (ex: Atualizar/Exportar)
        """

        def _hex_to_rgb(hx: str):
            s = (hx or "").strip().lstrip("#")
            if len(s) == 3:
                s = "".join([c * 2 for c in s])
            if len(s) != 6:
                return (0, 0, 0)
            return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

        def _is_light(hx: str) -> bool:
            r, g, b = _hex_to_rgb(hx)
            lum = (0.2126 * (r / 255) + 0.7152 * (g / 255) + 0.0722 * (b / 255))
            return lum >= 0.62

        def _mix(a: str, b: str, t: float) -> str:
            t = max(0.0, min(1.0, float(t)))
            ar, ag, ab = _hex_to_rgb(a)
            br, bg, bb = _hex_to_rgb(b)
            r = round(ar + (br - ar) * t)
            g = round(ag + (bg - ag) * t)
            b2 = round(ab + (bb - ab) * t)
            return f"#{r:02x}{g:02x}{b2:02x}"

        def _shade(base: str, amount: float) -> str:
            # amount > 0 clareia; amount < 0 escurece
            return _mix(base, "#ffffff", amount) if amount >= 0 else _mix(base, "#000000", abs(amount))

        def _text(bg: str) -> str:
            try:
                return get_contraste_texto(bg)
            except Exception:
                return self.theme.cor_texto

        def _hover(bg: str) -> str:
            return _shade(bg, -0.08 if _is_light(bg) else 0.08)

        ui_light = _is_light(self.theme.cor_fundo)

        if (tipo or "").lower() == "primario":
            fg = self.theme.cor_destaque
            return {
                "fg_color": fg,
                "hover_color": _hover(fg),
                "text_color": _text(fg),
                "border_width": 0,
                "border_color": self.theme.cor_borda,
            }

        # secundário
        if ui_light:
            # No tema claro: botão claro + borda (não fica escuro)
            fg = _shade(self.theme.cor_terciaria or self.theme.cor_fundo, -0.03)
            return {
                "fg_color": fg,
                "hover_color": _hover(fg),
                "text_color": _text(fg),
                "border_width": 1,
                "border_color": self.theme.cor_borda,
            }

        # No tema escuro: mantém primária do tema
        fg = self.theme.cor_primaria
        return {
            "fg_color": fg,
            "hover_color": _hover(fg),
            "text_color": _text(fg),
            "border_width": 0,
            "border_color": self.theme.cor_borda,
        }
if __name__ == "__main__":
    class _Tema:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    class _Host:
        def __init__(self, theme):
            self.theme = theme

    # === Temas de teste (ajuste as cores se quiser) ===
    TEMA_CLARO = _Tema(
        cor_fundo="#f3f4f6",
        cor_secundaria="#e5e7eb",
        cor_terciaria="#ffffff",
        cor_primaria="#d1d5db",     # <- se ficar escuro demais, o seu estilo novo deve corrigir
        cor_destaque="#2563eb",
        cor_hover="#1d4ed8",
        cor_texto="#111827",
        cor_borda="#cbd5e1",
        cor_imprimir="#ffffff",
    )

    TEMA_ESCURO = _Tema(
        cor_fundo="#0f1720",
        cor_secundaria="#111827",
        cor_terciaria="#0b1220",
        cor_primaria="#1f2937",
        cor_destaque="#2563eb",
        cor_hover="#334155",
        cor_texto="#e5e7eb",
        cor_borda="#273244",
        cor_imprimir="#ffffff",
    )

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Teste - RECIBOS_PAGAMENTOS")
    root.geometry("1150x650")

    container = ctk.CTkFrame(root, fg_color="transparent")
    container.pack(fill="both", expand=True)

    topbar = ctk.CTkFrame(container, fg_color="transparent")
    topbar.pack(fill="x", padx=12, pady=(12, 6))

    page_holder = ctk.CTkFrame(container, fg_color="transparent")
    page_holder.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    tema_var = ctk.StringVar(value="CLARO")
    current_page = {"w": None}

    def _rebuild(theme_obj):
        # destrói e recria a página (funciona mesmo se você não tiver apply_theme)
        if current_page["w"] is not None:
            current_page["w"].destroy()
            current_page["w"] = None

        host = _Host(theme_obj)
        w = RecibosPagamentosPage(page_holder, host=host)
        w.pack(fill="both", expand=True)
        current_page["w"] = w

    def _on_tema_change(_=None):
        _rebuild(TEMA_CLARO if tema_var.get() == "CLARO" else TEMA_ESCURO)

    ctk.CTkLabel(topbar, text="Tema de teste:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
    ctk.CTkSegmentedButton(
        topbar,
        values=["CLARO", "ESCURO"],
        variable=tema_var,
        command=_on_tema_change
    ).pack(side="left", padx=10)

    ctk.CTkButton(
        topbar,
        text="Recarregar página",
        command=_on_tema_change
    ).pack(side="right")

    _rebuild(TEMA_CLARO)
    root.mainloop()

#03/02/2025