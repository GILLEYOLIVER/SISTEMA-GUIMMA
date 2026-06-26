# -*- coding: utf-8 -*-
from PAGINAS_DO_SISTEMA import TEMAS
import os
import sys
import subprocess
import csv
from datetime import datetime
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from PAGINAS_DO_SISTEMA.UI_CALENDARIO import vincular_calendario

# ---------- PostgreSQL (via BANCO_DE_DADOS_PG) ----------
try:
    from PAGINAS_DO_SISTEMA import BANCO_DE_DADOS_PG as db
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
    TRANSLATIONS = {
        "pt_BR": {
            "title": "ADIANTAMENTOS REGISTRADOS (PG)",
            "faccao": "Facção:",
            "code": "Código:",
            "from_date": "De:",
            "to_date": "Até:",
            "date_placeholder": "dd/mm/aaaa",
            "search": "Buscar",
            "export_csv": "Exportar CSV",
            "export_pdf": "Exportar PDF",
            "table_id": "ID",
            "table_cut_id": "Corte ID",
            "table_code": "Código",
            "table_faccao": "Facção",
            "table_value": "Valor",
            "table_payment": "Forma",
            "table_installments": "Parcelas",
            "table_datetime": "Data/Hora",
            "database_not_ready": "Banco não preparado",
            "database_not_ready_message": "Não foi possível conectar ao banco de dados.\n\nVerifique OPERA_PG_DSN/OPERA_PG_SCHEMA e rode os scripts.",
            "error": "Erro",
            "success": "Sucesso",
            "query_error": "Falha ao consultar adiantamentos:\n{erro}",
            "save_csv": "Salvar CSV",
            "save_pdf": "Salvar PDF",
            "csv_saved": "CSV salvo em:\n{path}",
            "pdf_saved": "PDF salvo em:\n{path}",
            "csv_error": "Falha ao salvar CSV:\n{erro}",
            "pdf_error": "Falha ao salvar PDF:\n{erro}",
            "pdf_title": "Adiantamentos Registrados",
            "generated_at": "Gerado em: {data}",
            "csv_filename_prefix": "adiantamentos",
        },
        "en_US": {
            "title": "REGISTERED ADVANCE PAYMENTS (PG)",
            "faccao": "Contractor:",
            "code": "Code:",
            "from_date": "From:",
            "to_date": "To:",
            "date_placeholder": "mm/dd/yyyy",
            "search": "Search",
            "export_csv": "Export CSV",
            "export_pdf": "Export PDF",
            "table_id": "ID",
            "table_cut_id": "Cut ID",
            "table_code": "Code",
            "table_faccao": "Contractor",
            "table_value": "Amount",
            "table_payment": "Method",
            "table_installments": "Installments",
            "table_datetime": "Date/Time",
            "database_not_ready": "Database not ready",
            "database_not_ready_message": "Could not connect to the database.\n\nCheck OPERA_PG_DSN/OPERA_PG_SCHEMA and run the scripts.",
            "error": "Error",
            "success": "Success",
            "query_error": "Failed to query advance payments:\n{erro}",
            "save_csv": "Save CSV",
            "save_pdf": "Save PDF",
            "csv_saved": "CSV saved to:\n{path}",
            "pdf_saved": "PDF saved to:\n{path}",
            "csv_error": "Failed to save CSV:\n{erro}",
            "pdf_error": "Failed to save PDF:\n{erro}",
            "pdf_title": "Registered Advance Payments",
            "generated_at": "Generated at: {data}",
            "csv_filename_prefix": "advance_payments",
        },
        "es_ES": {
            "title": "ADELANTOS REGISTRADOS (PG)",
            "faccao": "Taller:",
            "code": "Código:",
            "from_date": "Desde:",
            "to_date": "Hasta:",
            "date_placeholder": "dd/mm/aaaa",
            "search": "Buscar",
            "export_csv": "Exportar CSV",
            "export_pdf": "Exportar PDF",
            "table_id": "ID",
            "table_cut_id": "Corte ID",
            "table_code": "Código",
            "table_faccao": "Taller",
            "table_value": "Valor",
            "table_payment": "Forma",
            "table_installments": "Cuotas",
            "table_datetime": "Fecha/Hora",
            "database_not_ready": "Base de datos no preparada",
            "database_not_ready_message": "No fue posible conectar a la base de datos.\n\nVerifique OPERA_PG_DSN/OPERA_PG_SCHEMA y ejecute los scripts.",
            "error": "Error",
            "success": "Éxito",
            "query_error": "Error al consultar adelantos:\n{erro}",
            "save_csv": "Guardar CSV",
            "save_pdf": "Guardar PDF",
            "csv_saved": "CSV guardado en:\n{path}",
            "pdf_saved": "PDF guardado en:\n{path}",
            "csv_error": "Error al guardar CSV:\n{erro}",
            "pdf_error": "Error al guardar PDF:\n{erro}",
            "pdf_title": "Adelantos Registrados",
            "generated_at": "Generado el: {data}",
            "csv_filename_prefix": "adelantos",
        },
    }

    def __init__(self, parent, sistema=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.sistema = sistema
        self.idioma_atual = self._obter_idioma_inicial()
        self._ui_refs = {}

        if not db.ready_check():
            messagebox.showerror(
                self._get_text("database_not_ready"),
                self._get_text("database_not_ready_message")
            )
            raise SystemExit(1)

        self.configure(fg_color=self.C("cor_fundo"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.header = ctk.CTkLabel(
            self,
            text=self._get_text("title"),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.C("cor_texto")
        )
        self.header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 6))
        self._ui_refs["title_label"] = self.header

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.grid(row=1, column=0, sticky="ew", padx=20)
        for i in range(10):
            filtros.grid_columnconfigure(i, weight=0)
        filtros.grid_columnconfigure(10, weight=1)

        self.lbl_faccao = ctk.CTkLabel(filtros, text=self._get_text("faccao"), text_color=self.C("cor_texto"))
        self.lbl_faccao.grid(row=0, column=0, padx=(0, 6))
        self._ui_refs["faccao_label"] = self.lbl_faccao

        self.faccao_var = ctk.StringVar(value="")
        self.input_faccao = ctk.CTkEntry(
            filtros,
            textvariable=self.faccao_var,
            width=200,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.input_faccao.grid(row=0, column=1, padx=(0, 12))

        self.lbl_codigo = ctk.CTkLabel(filtros, text=self._get_text("code"), text_color=self.C("cor_texto"))
        self.lbl_codigo.grid(row=0, column=2, padx=(0, 6))
        self._ui_refs["code_label"] = self.lbl_codigo

        self.codigo_var = ctk.StringVar(value="")
        self.input_codigo = ctk.CTkEntry(
            filtros,
            textvariable=self.codigo_var,
            width=120,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto")
        )
        self.input_codigo.grid(row=0, column=3, padx=(0, 12))

        self.lbl_de = ctk.CTkLabel(filtros, text=self._get_text("from_date"), text_color=self.C("cor_texto"))
        self.lbl_de.grid(row=0, column=4, padx=(0, 6))
        self._ui_refs["from_label"] = self.lbl_de

        self.de_var = ctk.StringVar(value="")
        self.input_de = ctk.CTkEntry(
            filtros,
            textvariable=self.de_var,
            width=120,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto"),
            placeholder_text=self._get_text("date_placeholder")
        )
        self.input_de.grid(row=0, column=5, padx=(0, 12))
        vincular_calendario(self, self.input_de, output_format="%Y-%m-%d")
        self._ui_refs["from_entry"] = self.input_de

        self.lbl_ate = ctk.CTkLabel(filtros, text=self._get_text("to_date"), text_color=self.C("cor_texto"))
        self.lbl_ate.grid(row=0, column=6, padx=(0, 6))
        self._ui_refs["to_label"] = self.lbl_ate

        self.ate_var = ctk.StringVar(value="")
        self.input_ate = ctk.CTkEntry(
            filtros,
            textvariable=self.ate_var,
            width=120,
            fg_color=self.C("cor_secundaria"),
            border_color=self.C("cor_borda"),
            text_color=self.C("cor_texto"),
            placeholder_text=self._get_text("date_placeholder")
        )
        self.input_ate.grid(row=0, column=7, padx=(0, 12))
        vincular_calendario(self, self.input_ate, output_format="%Y-%m-%d")
        self._ui_refs["to_entry"] = self.input_ate

        self.btn_buscar = ctk.CTkButton(
            filtros,
            text=self._get_text("search"),
            command=self.buscar,
            width=100,
            fg_color=self.C("cor_destaque"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_buscar.grid(row=0, column=8, sticky="w")
        self._ui_refs["search_button"] = self.btn_buscar

        tabela_wrap = ctk.CTkFrame(self, fg_color="transparent")
        tabela_wrap.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10, 10))
        tabela_wrap.grid_rowconfigure(0, weight=1)
        tabela_wrap.grid_columnconfigure(0, weight=1)

        self.tree_columns = ("ID", "Corte ID", "Código", "Facção", "Valor", "Forma", "Parcelas", "Data/Hora")
        self.tree_heading_keys = {
            "ID": "table_id",
            "Corte ID": "table_cut_id",
            "Código": "table_code",
            "Facção": "table_faccao",
            "Valor": "table_value",
            "Forma": "table_payment",
            "Parcelas": "table_installments",
            "Data/Hora": "table_datetime",
        }
        self.tree = ttk.Treeview(tabela_wrap, columns=self.tree_columns, show="headings", height=12)
        self.tree.grid(row=0, column=0, sticky="nsew")
        widths = [80, 90, 100, 220, 100, 110, 90, 160]
        for c, w in zip(self.tree_columns, widths):
            self.tree.heading(c, text=self._get_text(self.tree_heading_keys[c]))
            self.tree.column(c, width=w, anchor="center")

        sb = ttk.Scrollbar(tabela_wrap, orient="vertical", command=self.tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))

        self.btn_export_csv = ctk.CTkButton(
            actions,
            text=self._get_text("export_csv"),
            command=self.exportar_csv,
            width=130,
            fg_color=self.C("cor_imprimir"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_export_csv.pack(side="left", padx=6)
        self._ui_refs["export_csv_button"] = self.btn_export_csv

        self.btn_export_pdf = ctk.CTkButton(
            actions,
            text=self._get_text("export_pdf"),
            command=self.exportar_pdf,
            width=130,
            fg_color=self.C("cor_imprimir"),
            hover_color=self.C("cor_hover"),
            text_color=self.C("cor_texto"),
            border_color=self.C("cor_borda")
        )
        self.btn_export_pdf.pack(side="left", padx=6)
        self._ui_refs["export_pdf_button"] = self.btn_export_pdf

        self.buscar()

    # ---------- idioma ----------
    def _obter_idioma_inicial(self):
        for origem in (self.sistema, getattr(self.sistema, "app", None)):
            if origem and hasattr(origem, "idioma_atual"):
                idioma = getattr(origem, "idioma_atual")
                if idioma in self.TRANSLATIONS:
                    return idioma
        return "pt_BR"

    def _get_text(self, key, **kwargs):
        base = self.TRANSLATIONS.get(self.idioma_atual, self.TRANSLATIONS["pt_BR"])
        texto = base.get(key, self.TRANSLATIONS["pt_BR"].get(key, key))
        if kwargs:
            try:
                return texto.format(**kwargs)
            except Exception:
                return texto
        return texto

    def refresh_texts(self):
        self._ui_refs["title_label"].configure(text=self._get_text("title"))
        self._ui_refs["faccao_label"].configure(text=self._get_text("faccao"))
        self._ui_refs["code_label"].configure(text=self._get_text("code"))
        self._ui_refs["from_label"].configure(text=self._get_text("from_date"))
        self._ui_refs["to_label"].configure(text=self._get_text("to_date"))
        self._ui_refs["from_entry"].configure(placeholder_text=self._get_text("date_placeholder"))
        self._ui_refs["to_entry"].configure(placeholder_text=self._get_text("date_placeholder"))
        self._ui_refs["search_button"].configure(text=self._get_text("search"))
        self._ui_refs["export_csv_button"].configure(text=self._get_text("export_csv"))
        self._ui_refs["export_pdf_button"].configure(text=self._get_text("export_pdf"))
        self._atualizar_cabecalhos_tree()
        self.buscar()

    def _atualizar_cabecalhos_tree(self):
        for col in self.tree_columns:
            self.tree.heading(col, text=self._get_text(self.tree_heading_keys[col]))

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

    # ---------- formatação ----------
    def _fmt_currency(self, valor):
        try:
            v = float(str(valor).replace(",", "."))
        except Exception:
            return "$0.00" if self.idioma_atual == "en_US" else "R$ 0,00"

        if self.idioma_atual == "en_US":
            return f"${v:,.2f}"
        inteiro, frac = f"{v:,.2f}".split(".")
        inteiro = inteiro.replace(",", ".")
        return f"R$ {inteiro},{frac}"

    def _format_display_datetime(self, value):
        if isinstance(value, str):
            texto = value.strip()
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%Y %I:%M %p"):
                try:
                    value = datetime.strptime(texto, fmt)
                    break
                except Exception:
                    continue
            else:
                return texto

        if not isinstance(value, datetime):
            return "" if value is None else str(value)

        if self.idioma_atual == "en_US":
            return value.strftime("%m/%d/%Y %I:%M %p")
        return value.strftime("%d/%m/%Y %H:%M")

    def _parse_filter_date(self, value, end_of_day=False):
        texto = (value or "").strip()
        if not texto:
            return None

        formatos = []
        if self.idioma_atual == "en_US":
            formatos = ["%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"]
        else:
            formatos = ["%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"]

        for fmt in formatos:
            try:
                dt = datetime.strptime(texto, fmt)
                return dt.strftime("%Y-%m-%d") + (" 23:59:59" if end_of_day else " 00:00:00")
            except Exception:
                continue

        return (texto + (" 23:59:59" if end_of_day else " 00:00:00")) if len(texto) == 10 else texto

    # ---------- dados ----------
    def buscar(self):
        fac = (self.faccao_var.get() or "").strip()
        cod = (self.codigo_var.get() or "").strip()
        de = self._parse_filter_date(self.de_var.get(), end_of_day=False)
        ate = self._parse_filter_date(self.ate_var.get(), end_of_day=True)

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
            params.append(de)
        if ate:
            where.append("data_hora <= %s")
            params.append(ate)

        sql_parts = [
            "SELECT id, corte_id, codigo_modelo, faccao, valor, forma_pagamento, parcelas, data_hora",
            "FROM opera.adiantamento_faccao"
        ]
        if where:
            sql_parts.append("WHERE " + " AND ".join(where))
        sql_parts.append("ORDER BY data_hora DESC NULLS LAST, id DESC")
        sql_text = " ".join(sql_parts)

        try:
            rows = db.fetch_all(sql_text, tuple(params))
        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("query_error", erro=e))
            return

        for it in self.tree.get_children():
            self.tree.delete(it)

        for r in rows or []:
            valor_fmt = self._fmt_currency(r.get("valor"))
            dt_fmt = self._format_display_datetime(r.get("data_hora"))
            self.tree.insert("", "end", values=(
                r.get("id"),
                r.get("corte_id"),
                r.get("codigo_modelo"),
                r.get("faccao"),
                valor_fmt,
                r.get("forma_pagamento"),
                r.get("parcelas"),
                dt_fmt,
            ))

    def exportar_csv(self):
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV", "*.csv")],
                initialfile=f"{self._get_text('csv_filename_prefix')}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                title=self._get_text("save_csv")
            )
            if not path:
                return
            cols = tuple(self._get_text(self.tree_heading_keys[c]) for c in self.tree_columns)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(cols)
                for iid in self.tree.get_children():
                    writer.writerow(self.tree.item(iid)["values"])
            messagebox.showinfo(self._get_text("success"), self._get_text("csv_saved", path=path))
        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("csv_error", erro=e))

    def exportar_pdf(self):
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")],
                initialfile=f"{self._get_text('csv_filename_prefix')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                title=self._get_text("save_pdf")
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
            c.drawCentredString(width / 2, top, self._get_text("pdf_title"))
            c.setFont("Helvetica", 9)
            c.drawString(left, top - 14, self._get_text("generated_at", data=self._format_display_datetime(datetime.now())))

            data = [[self._get_text(self.tree_heading_keys[c]) for c in self.tree_columns]]
            for iid in self.tree.get_children():
                row = [str(x) for x in self.tree.item(iid)["values"]]
                data.append(row)

            col_widths = [50, 60, 60, 150, 70, 70, 60, 110]
            table = Table(data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))

            w, h = table.wrapOn(c, right - left, top - 60)
            y = top - 40 - h
            if y < 40:
                y = 40
            table.drawOn(c, left, y)

            c.showPage()
            c.save()
            messagebox.showinfo(self._get_text("success"), self._get_text("pdf_saved", path=path))
            try:
                if os.name == "nt":
                    os.startfile(path)
                elif os.name == "posix":
                    opener = "open" if sys.platform == "darwin" else "xdg-open"
                    subprocess.call([opener, path])
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror(self._get_text("error"), self._get_text("pdf_error", erro=e))


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.geometry("1000x600")
    root.title("Adiantamentos Registrados")
    app = AdiantamentosPendentesPage(root, sistema=None)
    app.pack(fill="both", expand=True)
    root.mainloop()
