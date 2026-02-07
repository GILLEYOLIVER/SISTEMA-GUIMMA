# -*- coding: utf-8 -*-
"""
MRP_PLANEJAMENTO.py - Módulo MRP
Interface base para cálculo de necessidades de materiais.
"""
from datetime import datetime
import os
import webbrowser
from tkinter import messagebox, ttk

import customtkinter as ctk
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class MRPPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.tree_necessidades = None
        self.tree_ordens = None
        self.tree_fornecedores = None
        self._build()

    def _build(self):
        self.configure(fg_color="transparent")
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_filters()
        self._build_results()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="MRP / Necessidades de Insumos", font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Planejamento de materiais com base em ordens e estoque atual.",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(5, weight=1)

        ctk.CTkButton(toolbar, text="Gerar MRP").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Simular").grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Aprovar Compra").grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Exportar PDF", command=self._exportar_mrp).grid(
            row=0, column=3, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Imprimir", command=self._imprimir_mrp).grid(
            row=0, column=4, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Configurações").grid(row=0, column=5)

    def _build_filters(self):
        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(9, weight=1)

        ctk.CTkLabel(filters, text="Período").grid(row=0, column=0, padx=(12, 6), pady=8)
        self.mrp_inicio_entry = ctk.CTkEntry(filters, placeholder_text="De")
        self.mrp_inicio_entry.grid(row=0, column=1, padx=(0, 6), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.mrp_inicio_entry),
        ).grid(row=0, column=2, padx=(0, 6), pady=8)
        self.mrp_fim_entry = ctk.CTkEntry(filters, placeholder_text="Até")
        self.mrp_fim_entry.grid(row=0, column=3, padx=(0, 12), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.mrp_fim_entry),
        ).grid(row=0, column=4, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Coleção").grid(row=0, column=5, padx=(0, 6), pady=8)
        ctk.CTkOptionMenu(filters, values=["Todas", "Linha Básica", "Coleção 2026"]).grid(
            row=0, column=6, padx=(0, 12), pady=8
        )
        ctk.CTkLabel(filters, text="Status").grid(row=0, column=7, padx=(0, 6), pady=8)
        ctk.CTkOptionMenu(filters, values=["Crítico", "Atenção", "OK", "Todos"]).grid(
            row=0, column=8, padx=(0, 12), pady=8
        )
        ctk.CTkButton(filters, text="Filtrar").grid(row=0, column=9, padx=(0, 12), pady=8)

    def _build_results(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 24))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        kpis = ctk.CTkFrame(body)
        kpis.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        kpis.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for idx, text in enumerate(
            ["Itens críticos: 0", "Faltantes: 0", "Valor a comprar: R$ 0,00", "Lead time médio: 0 dias"]
        ):
            card = ctk.CTkFrame(kpis)
            card.grid(row=0, column=idx, padx=6, sticky="ew")
            ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=12, weight="bold")).pack(
                pady=12
            )

        tabs = ctk.CTkTabview(body)
        tabs.grid(row=1, column=0, sticky="nsew")

        necessidades_tab = tabs.add("Necessidades")
        ordens_tab = tabs.add("Ordens Recomendadas")
        fornecedores_tab = tabs.add("Fornecedores Críticos")

        self._build_necessidades_tab(necessidades_tab)
        self._build_ordens_tab(ordens_tab)
        self._build_fornecedores_tab(fornecedores_tab)

    def _build_necessidades_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree_necessidades = ttk.Treeview(
            tree_frame,
            columns=("insumo", "sku", "necessario", "estoque", "faltante", "lead", "fornecedor"),
            show="headings",
            height=12,
        )
        for col, text, width in (
            ("insumo", "Insumo", 220),
            ("sku", "SKU", 120),
            ("necessario", "Necessário", 110),
            ("estoque", "Estoque", 90),
            ("faltante", "Faltante", 90),
            ("lead", "Lead Time", 90),
            ("fornecedor", "Fornecedor", 200),
        ):
            self.tree_necessidades.heading(col, text=text)
            self.tree_necessidades.column(col, width=width)
        self.tree_necessidades.column("necessario", anchor="e")
        self.tree_necessidades.column("estoque", anchor="e")
        self.tree_necessidades.column("faltante", anchor="e")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_necessidades.yview)
        self.tree_necessidades.configure(yscrollcommand=tree_scroll.set)
        self.tree_necessidades.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    def _build_ordens_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        info = ctk.CTkFrame(parent)
        info.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        info.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(info, text="Plano de compra recomendado").grid(
            row=0, column=0, padx=12, pady=8, sticky="w"
        )
        ctk.CTkButton(info, text="Converter em Pedido").grid(row=0, column=2, padx=12, pady=8)

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree_ordens = ttk.Treeview(
            tree_frame,
            columns=("ordem", "insumo", "quantidade", "fornecedor", "data"),
            show="headings",
            height=10,
        )
        for col, text, width in (
            ("ordem", "Ordem", 90),
            ("insumo", "Insumo", 220),
            ("quantidade", "Quantidade", 120),
            ("fornecedor", "Fornecedor", 200),
            ("data", "Entrega Prevista", 140),
        ):
            self.tree_ordens.heading(col, text=text)
            self.tree_ordens.column(col, width=width)
        self.tree_ordens.column("quantidade", anchor="e")

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_ordens.yview)
        self.tree_ordens.configure(yscrollcommand=tree_scroll.set)
        self.tree_ordens.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    def _build_fornecedores_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.tree_fornecedores = ttk.Treeview(
            tree_frame,
            columns=("fornecedor", "insumos", "atraso", "risco"),
            show="headings",
            height=10,
        )
        for col, text, width in (
            ("fornecedor", "Fornecedor", 240),
            ("insumos", "Insumos Críticos", 160),
            ("atraso", "Atraso Médio", 120),
            ("risco", "Risco", 120),
        ):
            self.tree_fornecedores.heading(col, text=text)
            self.tree_fornecedores.column(col, width=width)

        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_fornecedores.yview)
        self.tree_fornecedores.configure(yscrollcommand=tree_scroll.set)
        self.tree_fornecedores.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=12)

    def _exportar_mrp(self):
        try:
            caminho = self._gerar_pdf_mrp()
            self._abrir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("MRP", f"Erro ao exportar PDF: {exc}")

    def _imprimir_mrp(self):
        try:
            caminho = self._gerar_pdf_mrp()
            self._imprimir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("MRP", f"Erro ao imprimir: {exc}")

    def _gerar_pdf_mrp(self):
        nome = f"mrp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        caminho = os.path.abspath(nome)
        c = canvas.Canvas(caminho, pagesize=A4)
        largura, altura = A4
        y = altura - 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Relatório MRP")
        y -= 24
        c.setFont("Helvetica", 9)
        c.drawString(40, y, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        y -= 18

        def escrever_titulo(titulo):
            nonlocal y
            c.setFont("Helvetica-Bold", 11)
            c.drawString(40, y, titulo)
            y -= 16
            c.setFont("Helvetica", 9)

        def escrever_linhas(linhas):
            nonlocal y
            for linha in linhas:
                if y < 80:
                    c.showPage()
                    y = altura - 60
                c.drawString(40, y, linha)
                y -= 12

        if self.tree_necessidades:
            escrever_titulo("Necessidades")
            linhas = []
            for item in self.tree_necessidades.get_children():
                vals = self.tree_necessidades.item(item)["values"]
                linhas.append(
                    f"- {vals[0]} | {vals[1]} | Necessário {vals[2]} | Estoque {vals[3]} | Faltante {vals[4]}"
                )
            escrever_linhas(linhas or ["Sem dados."])
            y -= 8

        if self.tree_ordens:
            escrever_titulo("Ordens Recomendadas")
            linhas = []
            for item in self.tree_ordens.get_children():
                vals = self.tree_ordens.item(item)["values"]
                linhas.append(f"- {vals[0]} | {vals[1]} | Qtde {vals[2]} | {vals[3]} | {vals[4]}")
            escrever_linhas(linhas or ["Sem dados."])
            y -= 8

        if self.tree_fornecedores:
            escrever_titulo("Fornecedores Críticos")
            linhas = []
            for item in self.tree_fornecedores.get_children():
                vals = self.tree_fornecedores.item(item)["values"]
                linhas.append(f"- {vals[0]} | Insumos {vals[1]} | Atraso {vals[2]} | Risco {vals[3]}")
            escrever_linhas(linhas or ["Sem dados."])

        c.save()
        return caminho

    def _abrir_pdf(self, caminho):
        try:
            webbrowser.open_new_tab("file://" + caminho)
        except Exception:
            if hasattr(os, "startfile"):
                os.startfile(caminho)  # type: ignore[attr-defined]

    def _imprimir_pdf(self, caminho):
        if hasattr(os, "startfile"):
            try:
                os.startfile(caminho, "print")  # type: ignore[attr-defined]
                return
            except Exception:
                pass
        self._abrir_pdf(caminho)
        messagebox.showinfo("MRP", "PDF aberto no navegador. Use Ctrl+P para imprimir.")

    def _abrir_calendario(self, entry):
        from datetime import datetime as _dt
        import calendar as _cal

        def setar_data(d):
            entry.delete(0, "end")
            entry.insert(0, d.strftime("%d/%m/%Y"))
            top.destroy()

        top = ctk.CTkToplevel(self)
        top.title("Calendário")
        top.resizable(False, False)

        W, H = 300, 300
        self.update_idletasks()
        top.update_idletasks()

        ex = entry.winfo_rootx()
        ey = entry.winfo_rooty()
        eh = entry.winfo_height()

        x = ex
        y = ey + eh + 6

        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        if x + W > sw:
            x = sw - W - 10
        if y + H > sh:
            y = ey - H - 6

        top.geometry(f"{W}x{H}+{x}+{y}")
        top.transient(self)
        top.grab_set()

        now = _dt.now()
        ano = now.year
        mes = now.month

        nav = ctk.CTkFrame(top)
        nav.pack(fill="x", padx=10, pady=5)

        lbl_mes = ctk.CTkLabel(nav, text=f"{_cal.month_name[mes]} {ano}", font=("Arial", 14))
        ctk.CTkButton(nav, text="<", width=30, command=lambda: mudar_mes(-1)).pack(side="left")
        lbl_mes.pack(side="left", expand=True)
        ctk.CTkButton(nav, text=">", width=30, command=lambda: mudar_mes(1)).pack(side="right")

        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        frame_dias = ctk.CTkFrame(top)
        frame_dias.pack(fill="both", expand=True, padx=10, pady=5)

        for i, dia in enumerate(dias_semana):
            lbl = ctk.CTkLabel(frame_dias, text=dia, width=30, height=30)
            lbl.grid(row=0, column=i, padx=2, pady=2)

        def mudar_mes(delta):
            nonlocal mes, ano
            mes += delta
            if mes > 12:
                mes = 1
                ano += 1
            elif mes < 1:
                mes = 12
                ano -= 1
            lbl_mes.configure(text=f"{_cal.month_name[mes]} {ano}")
            desenhar_calendario()

        def desenhar_calendario():
            for w in frame_dias.grid_slaves():
                if int(w.grid_info()["row"]) > 0:
                    w.destroy()

            cal = _cal.monthcalendar(ano, mes)
            for i, semana in enumerate(cal):
                for j, dia in enumerate(semana):
                    if dia == 0:
                        continue
                    btn = ctk.CTkButton(
                        frame_dias,
                        text=str(dia),
                        width=30,
                        height=30,
                        command=lambda d=dia: setar_data(_dt(ano, mes, d)),
                    )
                    btn.grid(row=i + 1, column=j, padx=2, pady=2)

        desenhar_calendario()


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("MRP - Teste")
    app.geometry("1200x720")
    page = MRPPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()