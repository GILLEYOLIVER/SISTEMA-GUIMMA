# -*- coding: utf-8 -*-
"""
RELATORIO_CUSTOS_REAIS.py - Relatório de Custos Reais
Interface base para análise de custos planejados x realizados.
"""
from datetime import datetime
import os
import webbrowser
from tkinter import messagebox, ttk

import customtkinter as ctk
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class RelatorioCustosReaisPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.tree_categoria = None
        self.tree_ops = None
        self._build()

    def _build(self):
        self.configure(fg_color="transparent")
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_filters()
        self._build_body()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Relatório de Custos Reais", font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Comparativo de custos planejados e realizados por OP e categoria.",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(4, weight=1)

        ctk.CTkButton(toolbar, text="Atualizar").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Exportar PDF", command=self._exportar_custos).grid(
            row=0, column=1, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Imprimir", command=self._imprimir_custos).grid(
            row=0, column=2, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Comparar OPs").grid(row=0, column=3)

    def _build_filters(self):
        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(9, weight=1)

        ctk.CTkLabel(filters, text="Período").grid(row=0, column=0, padx=(12, 6), pady=8)
        self.custos_inicio_entry = ctk.CTkEntry(filters, placeholder_text="De")
        self.custos_inicio_entry.grid(row=0, column=1, padx=(0, 6), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.custos_inicio_entry),
        ).grid(row=0, column=2, padx=(0, 6), pady=8)
        self.custos_fim_entry = ctk.CTkEntry(filters, placeholder_text="Até")
        self.custos_fim_entry.grid(row=0, column=3, padx=(0, 12), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.custos_fim_entry),
        ).grid(row=0, column=4, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Modelo").grid(row=0, column=5, padx=(0, 6), pady=8)
        ctk.CTkEntry(filters, placeholder_text="Buscar modelo").grid(
            row=0, column=6, padx=(0, 12), pady=8
        )
        ctk.CTkLabel(filters, text="Status").grid(row=0, column=7, padx=(0, 6), pady=8)
        ctk.CTkOptionMenu(filters, values=["Todos", "Em produção", "Finalizado"]).grid(
            row=0, column=8, padx=(0, 12), pady=8
        )
        ctk.CTkButton(filters, text="Filtrar").grid(row=0, column=9, padx=(0, 12), pady=8)

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 24))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        kpis = ctk.CTkFrame(body)
        kpis.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        kpis.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for idx, text in enumerate(
            [
                "Custo planejado: R$ 0,00",
                "Custo real: R$ 0,00",
                "Variação: 0,0%",
                "Margem estimada: R$ 0,00",
            ]
        ):
            card = ctk.CTkFrame(kpis)
            card.grid(row=0, column=idx, padx=6, sticky="ew")
            ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=12, weight="bold")).pack(
                pady=12
            )

        comparativo_frame = ctk.CTkFrame(body)
        comparativo_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        comparativo_frame.grid_columnconfigure(0, weight=1)
        comparativo_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            comparativo_frame, text="Comparativo por Categoria", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.tree_categoria = ttk.Treeview(
            comparativo_frame,
            columns=("categoria", "planejado", "real", "variacao"),
            show="headings",
            height=12,
        )
        for col, text, width in (
            ("categoria", "Categoria", 200),
            ("planejado", "Planejado", 120),
            ("real", "Real", 120),
            ("variacao", "Variação", 100),
        ):
            self.tree_categoria.heading(col, text=text)
            self.tree_categoria.column(col, width=width)
        self.tree_categoria.column("planejado", anchor="e")
        self.tree_categoria.column("real", anchor="e")
        self.tree_categoria.column("variacao", anchor="e")

        tree_scroll = ttk.Scrollbar(comparativo_frame, orient="vertical", command=self.tree_categoria.yview)
        self.tree_categoria.configure(yscrollcommand=tree_scroll.set)
        self.tree_categoria.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        tree_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16))

        detalhe_frame = ctk.CTkFrame(body)
        detalhe_frame.grid(row=1, column=1, sticky="nsew")
        detalhe_frame.grid_columnconfigure(0, weight=1)
        detalhe_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            detalhe_frame, text="Detalhes por OP", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.tree_ops = ttk.Treeview(
            detalhe_frame,
            columns=("op", "modelo", "planejado", "real"),
            show="headings",
            height=10,
        )
        for col, text, width in (
            ("op", "OP", 90),
            ("modelo", "Modelo", 160),
            ("planejado", "Planejado", 110),
            ("real", "Real", 110),
        ):
            self.tree_ops.heading(col, text=text)
            self.tree_ops.column(col, width=width)
        self.tree_ops.column("planejado", anchor="e")
        self.tree_ops.column("real", anchor="e")

        detalhe_scroll = ttk.Scrollbar(detalhe_frame, orient="vertical", command=self.tree_ops.yview)
        self.tree_ops.configure(yscrollcommand=detalhe_scroll.set)
        self.tree_ops.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        detalhe_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16))

    def _exportar_custos(self):
        try:
            caminho = self._gerar_pdf_custos()
            self._abrir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("Custos Reais", f"Erro ao exportar PDF: {exc}")

    def _imprimir_custos(self):
        try:
            caminho = self._gerar_pdf_custos()
            self._imprimir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("Custos Reais", f"Erro ao imprimir: {exc}")

    def _gerar_pdf_custos(self):
        nome = f"custos_reais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        caminho = os.path.abspath(nome)
        c = canvas.Canvas(caminho, pagesize=A4)
        largura, altura = A4
        y = altura - 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Relatório de Custos Reais")
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

        if self.tree_categoria:
            escrever_titulo("Comparativo por Categoria")
            linhas = []
            for item in self.tree_categoria.get_children():
                vals = self.tree_categoria.item(item)["values"]
                linhas.append(f"- {vals[0]} | Planejado {vals[1]} | Real {vals[2]} | Var {vals[3]}")
            escrever_linhas(linhas or ["Sem dados."])
            y -= 8

        if self.tree_ops:
            escrever_titulo("Detalhes por OP")
            linhas = []
            for item in self.tree_ops.get_children():
                vals = self.tree_ops.item(item)["values"]
                linhas.append(f"- OP {vals[0]} | {vals[1]} | Planejado {vals[2]} | Real {vals[3]}")
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
        messagebox.showinfo("Custos Reais", "PDF aberto no navegador. Use Ctrl+P para imprimir.")

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
    app.title("Custos Reais - Teste")
    app.geometry("1200x720")
    page = RelatorioCustosReaisPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()
