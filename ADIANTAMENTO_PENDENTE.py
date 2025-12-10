# -*- coding: utf-8 -*-
import os, sys
from datetime import datetime
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog

# ---------- PostgreSQL (via BANCO_DE_DADOS_PG) ----------
# Import do módulo PG com fallback por caminho
try:
    import BANCO_DE_DADOS_PG as db  # requer OPERA_PG_DSN e OPERA_PG_SCHEMA=opera
except ModuleNotFoundError:
    import importlib.util
    CANDIDATES = [
        os.path.join(os.path.dirname(__file__), "BANCO_DE_DADOS_PG.py"),
        os.path.join(os.path.dirname(__file__), "..", "BANCO_DE_DADOS_PG.py"),
        r"C:\Users\User\Desktop\sistema\SISTEMA\BANCO_DE_DADOS_PG.py",
    ]
    db = None
    for _p in CANDIDATES:
        if os.path.isfile(_p):
            _spec = importlib.util.spec_from_file_location("BANCO_DE_DADOS_PG", _p)
            db = importlib.util.module_from_spec(_spec)
            sys.modules["BANCO_DE_DADOS_PG"] = db
            _spec.loader.exec_module(db)
            break
    if db is None:
        raise




class AdiantamentosPendentesPage(ctk.CTkFrame):
    """
    Lista e filtra adiantamentos registrados em opera.adiantamento_faccao.
    Observação: o schema atual não tem coluna de status; então exibimos todos os registros
    (com filtros) e permitimos exportar. Se futuramente existir 'status', podemos filtrar por ele.
    """
    def __init__(self, parent, sistema=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.sistema = sistema

        # Verifica banco
        if not db.ready_check():
            msg = "Não foi possível conectar ao banco de dados."
            messagebox.showerror(
                "Banco não preparado",
                msg + "\n\nVerifique OPERA_PG_DSN/OPERA_PG_SCHEMA e rode os scripts."
            )
            raise SystemExit(1)


        # Paleta básica
        self.configure(fg_color=self.C("cor_fundo"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkLabel(
            self, text="ADIANTAMENTOS REGISTRADOS (PG)",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.C("cor_texto")
        )
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 6))

        # Filtros
        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.grid(row=1, column=0, sticky="ew", padx=20)
        for i in range(8):
            filtros.grid_columnconfigure(i, weight=0)
        filtros.grid_columnconfigure(8, weight=1)

        ctk.CTkLabel(filtros, text="Facção:", text_color=self.C("cor_texto")).grid(row=0, column=0, padx=(0,6))
        self.faccao_var = ctk.StringVar(value="")
        self.input_faccao = ctk.CTkEntry(
            filtros, textvariable=self.faccao_var, width=200,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.input_faccao.grid(row=0, column=1, padx=(0,12))

        ctk.CTkLabel(filtros, text="Código:", text_color=self.C("cor_texto")).grid(row=0, column=2, padx=(0,6))
        self.codigo_var = ctk.StringVar(value="")
        self.input_codigo = ctk.CTkEntry(
            filtros, textvariable=self.codigo_var, width=120,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.input_codigo.grid(row=0, column=3, padx=(0,12))

        ctk.CTkLabel(filtros, text="De (AAAA-MM-DD):", text_color=self.C("cor_texto")).grid(row=0, column=4, padx=(0,6))
        self.de_var = ctk.StringVar(value="")
        self.input_de = ctk.CTkEntry(
            filtros, textvariable=self.de_var, width=120,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.input_de.grid(row=0, column=5, padx=(0,12))

        ctk.CTkLabel(filtros, text="Até (AAAA-MM-DD):", text_color=self.C("cor_texto")).grid(row=0, column=6, padx=(0,6))
        self.ate_var = ctk.StringVar(value="")
        self.input_ate = ctk.CTkEntry(
            filtros, textvariable=self.ate_var, width=120,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.input_ate.grid(row=0, column=7, padx=(0,12))

        btn_buscar = ctk.CTkButton(
            filtros, text="Buscar", command=self.buscar, width=100,
            fg_color=self.C("cor_destaque"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        btn_buscar.grid(row=0, column=8, sticky="w")

        # Tabela
        tabela_wrap = ctk.CTkFrame(self, fg_color="transparent")
        tabela_wrap.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10,10))
        tabela_wrap.grid_rowconfigure(0, weight=1)
        tabela_wrap.grid_columnconfigure(0, weight=1)

        cols = ("ID", "Corte ID", "Código", "Facção", "Valor", "Forma", "Parcelas", "Data/Hora")
        self.tree = ttk.Treeview(tabela_wrap, columns=cols, show="headings", height=12)
        self.tree.grid(row=0, column=0, sticky="nsew")
        widths = [80, 90, 100, 220, 100, 110, 90, 160]
        for c, w in zip(cols, widths):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center")

        sb = ttk.Scrollbar(tabela_wrap, orient="vertical", command=self.tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)

        # Ações
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=20, pady=(0,16))

        self.btn_export_csv = ctk.CTkButton(
            actions, text="Exportar CSV", command=self.exportar_csv, width=130,
            fg_color=self.C("cor_imprimir"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_export_csv.pack(side="left", padx=6)

        self.btn_export_pdf = ctk.CTkButton(
            actions, text="Exportar PDF", command=self.exportar_pdf, width=130,
            fg_color=self.C("cor_imprimir"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_export_pdf.pack(side="left", padx=6)

        # Carrega inicial
        self.buscar()

    # ---------- helpers de tema ----------
    def C(self, nome, default=None):
        if self.sistema and hasattr(self.sistema, nome):
            return getattr(self.sistema, nome)
        defaults = {
            "cor_fundo": "#181818",
            "cor_primaria": "#121212",
            "cor_secundaria": "#1F1F1F",
            "cor_texto": "#EEEEEE",
            "cor_hover": "#2C2C2C",
            "cor_borda": "#3A3A3A",
            "cor_destaque": "#BB86FC",
            "cor_sucesso": "#03DAC6",
            "cor_alerta": "#CF6679",
            "cor_adicionar": "#03DAC6",
            "cor_imprimir": "#4A90E2",
        }
        return defaults.get(nome, default)

    # ---------- dados ----------
    def buscar(self):
        fac = (self.faccao_var.get() or "").strip()
        cod = (self.codigo_var.get() or "").strip()
        de = (self.de_var.get() or "").strip()
        ate = (self.ate_var.get() or "").strip()

        where = []
        params = []

        if fac:
            where.append("faccao ILIKE %s")
            params.append(f"%{fac}%")
        if cod:
            where.append("codigo_modelo ILIKE %s")
            params.append(f"%{cod}%")
        if de:
            where.append("data_hora >= %s")
            params.append(de + " 00:00:00")
        if ate:
            where.append("data_hora <= %s")
            params.append(ate + " 23:59:59")

        sql_parts = [
            "SELECT id, corte_id, codigo_modelo, faccao, valor, forma_pagamento, parcelas, data_hora",
            "FROM opera.adiantamento_faccao"  # <— schema qualificado
        ]
        if where:
            sql_parts.append("WHERE " + " AND ".join(where))
        sql_parts.append("ORDER BY data_hora DESC NULLS LAST, id DESC")

        sql_text = " ".join(sql_parts)

        try:
            rows = db.fetch_all(sql_text, tuple(params))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao consultar adiantamentos:\n{e}")
            return

        # Preenche tabela
        for it in self.tree.get_children():
            self.tree.delete(it)
        for r in rows or []:
            v = r.get("valor")
            try:
                v = float(v)
            except Exception:
                pass
            valor_fmt = self._fmt_currency(v)
            dt = r.get("data_hora")
            try:
                if isinstance(dt, str):
                    dt_fmt = dt
                else:
                    dt_fmt = (dt or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                dt_fmt = str(dt)

            self.tree.insert("", "end", values=(
                r.get("id"), r.get("corte_id"), r.get("codigo_modelo"),
                r.get("faccao"), valor_fmt, r.get("forma_pagamento"),
                r.get("parcelas"), dt_fmt
            ))

    def _fmt_currency(self, valor):
        try:
            v = float(str(valor).replace(",", "."))
            inteiro, frac = f"{v:,.2f}".split(".")
            inteiro = inteiro.replace(",", ".")
            return f"R$ {inteiro},{frac}"
        except Exception:
            return "R$ 0,00"

    def exportar_csv(self):
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV", "*.csv")],
                initialfile=f"adiantamentos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                title="Salvar CSV"
            )
            if not path:
                return
            import csv
            cols = ("ID","Corte ID","Código","Facção","Valor","Forma","Parcelas","Data/Hora")
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(cols)
                for iid in self.tree.get_children():
                    writer.writerow(self.tree.item(iid)["values"])
            messagebox.showinfo("Sucesso", f"CSV salvo em:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar CSV:\n{e}")

    def exportar_pdf(self):
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")],
                initialfile=f"adiantamentos_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                title="Salvar PDF"
            )
            if not path:
                return

            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.platypus import Table, TableStyle
            from reportlab.lib import colors

            c = canvas.Canvas(path, pagesize=letter)
            width, height = letter
            left, right = 40, width - 40
            top = height - 40

            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(width/2, top, "Adiantamentos Registrados")
            c.setFont("Helvetica", 9)
            c.drawString(left, top-14, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

            data = [["ID","Corte ID","Código","Facção","Valor","Forma","Parcelas","Data/Hora"]]
            for iid in self.tree.get_children():
                row = [str(x) for x in self.tree.item(iid)["values"]]
                data.append(row)

            col_widths = [50, 60, 60, 150, 70, 70, 60, 110]
            table = Table(data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
                ("FONTSIZE", (0,0), (-1,-1), 9),
                ("GRID", (0,0), (-1,-1), 0.5, colors.black),
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("ALIGN", (0,0), (-1,0), "CENTER"),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ]))

            w, h = table.wrapOn(c, right-left, top-60)
            y = top - 40 - h
            if y < 40:
                y = 40
            table.drawOn(c, left, y)

            c.showPage()
            c.save()
            messagebox.showinfo("Sucesso", f"PDF salvo em:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar PDF:\n{e}")


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.geometry("1000x600")
    root.title("Adiantamentos Registrados (PG)")
    app = AdiantamentosPendentesPage(root, sistema=None)
    app.pack(fill="both", expand=True)
    root.mainloop()
