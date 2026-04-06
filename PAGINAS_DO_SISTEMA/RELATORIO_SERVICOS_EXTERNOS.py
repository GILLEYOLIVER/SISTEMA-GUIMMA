# RELATORIO_SERVICOS_EXTERNOS.py
# Relatório de Serviços Externos (Facções) – compatível com MENU_PRINCIPAL

from __future__ import annotations
from PAGINAS_DO_SISTEMA import TEMAS
import csv
import os
from datetime import date, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

# Banco (opcional)
try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import db, require_ready
except Exception:
    db = None
    def require_ready(_tables=None):
        return False, "Módulo BANCO_DE_DADOS_PG indisponível"


# ---------------------- Helpers de datas ----------------------
def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)

def _last_day_of_month(d: date) -> date:
    next_month = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)

# ---------------------- Página ----------------------
class RelatorioServicosExternosPage(ctk.CTkFrame):
    """
    Página de Relatório de Serviços Externos (Facções).
    Compatível com MENU_PRINCIPAL: __init__(master, sistema=None, *args, **kwargs)
    """

    COLUNAS = (
        "DATA", "FACÇÃO", "SERVIÇO", "ORDEM", "MODELO", "QTD", "VALOR_UN", "TOTAL"
    )

    def __init__(self, master, sistema=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.sistema = sistema
        self.pack(fill="both", expand=True)

        # Logger opcional
        try:
            from PAGINAS_DO_SISTEMA.LOG_SISTEMA import get_logger
            self.logger = get_logger("OPERA_SYSTEM")
        except Exception:
            self.logger = None

        # Tema herdado (fallback seguro)
        origem = self.sistema
        self.cor_fundo    = getattr(origem, "cor_fundo",    "#0E1525")
        self.cor_texto    = getattr(origem, "cor_texto",    "#e5e7eb")
        self.cor_borda    = getattr(origem, "cor_borda",    "#334155")
        self.cor_primaria = getattr(origem, "cor_primaria", "#1F538D")
        self.cor_hover    = getattr(origem, "cor_hover",    "#14375E")
        self.cor_destaque = getattr(origem, "cor_selecao",  "#223649")

        # Filtros padrão (mês atual)
        hoje = date.today()
        self.ini_var = tk.StringVar(value=_first_day_of_month(hoje).strftime("%Y-%m-%d"))
        self.fim_var = tk.StringVar(value=_last_day_of_month(hoje).strftime("%Y-%m-%d"))
        self.faccao_var = tk.StringVar(value="Todas")
        self.servico_var = tk.StringVar(value="Todos")

        # Constrói UI
        self._apply_ttk_theme()
        self._build_ui()

        # Carrega dados iniciais
        self._buscar()

        if self.logger:
            self.logger.info("[PAGINA] Relatório de Serviços Externos: inicialização OK")

    # ---------------------- UI ----------------------
    def _apply_ttk_theme(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Treeview",
            background=self.cor_fundo,
            fieldbackground=self.cor_fundo,
            foreground=self.cor_texto,
            bordercolor=self.cor_borda,
            rowheight=26,
        )
        style.configure(
            "Treeview.Heading",
            background=self.cor_destaque,
            foreground=self.cor_texto,
            relief="flat"
        )
        style.map("Treeview", background=[("selected", self.cor_destaque)])

    def _build_ui(self):
        self.configure(fg_color=self.cor_fundo)

        # Título
        header = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            header, text="🚚 Relatório de Serviços Externos",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.cor_texto
        ).pack(side="left")

        # Filtros
        filtros = ctk.CTkFrame(self, fg_color=self.cor_fundo, border_color=self.cor_borda, border_width=1, corner_radius=10)
        filtros.pack(fill="x", padx=10, pady=(0, 10))

        # Período
        bloco_data = ctk.CTkFrame(filtros, fg_color=self.cor_fundo)
        bloco_data.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(bloco_data, text="Início", text_color=self.cor_texto).grid(row=0, column=0, sticky="w")
        self.ini_entry = ctk.CTkEntry(bloco_data, textvariable=self.ini_var, width=120)
        self.ini_entry.grid(row=1, column=0, padx=(0, 8))

        ctk.CTkLabel(bloco_data, text="Fim", text_color=self.cor_texto).grid(row=0, column=1, sticky="w")
        self.fim_entry = ctk.CTkEntry(bloco_data, textvariable=self.fim_var, width=120)
        self.fim_entry.grid(row=1, column=1)

        # Facção/Serviço
        bloco_sel = ctk.CTkFrame(filtros, fg_color=self.cor_fundo)
        bloco_sel.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(bloco_sel, text="Facção", text_color=self.cor_texto).grid(row=0, column=0, sticky="w")
        self.faccao_entry = ctk.CTkEntry(bloco_sel, textvariable=self.faccao_var, width=200, placeholder_text="Todas")
        self.faccao_entry.grid(row=1, column=0, padx=(0, 8))

        ctk.CTkLabel(bloco_sel, text="Serviço", text_color=self.cor_texto).grid(row=0, column=1, sticky="w")
        self.servico_entry = ctk.CTkEntry(bloco_sel, textvariable=self.servico_var, width=200, placeholder_text="Todos")
        self.servico_entry.grid(row=1, column=1)

        # Ações
        acoes = ctk.CTkFrame(filtros, fg_color=self.cor_fundo)
        acoes.pack(side="right", padx=10, pady=10)

        ctk.CTkButton(
            acoes, text="🔍 Buscar", fg_color=self.cor_primaria, hover_color=self.cor_hover,
            text_color=self.cor_texto, command=self._buscar, width=120
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            acoes, text="⬇️ Exportar CSV", fg_color=self.cor_destaque, hover_color=self.cor_hover,
            text_color=self.cor_texto, command=self._exportar_csv, width=140
        ).pack(side="left", padx=6)

        # Tabela
        tabela_frame = ctk.CTkFrame(self, fg_color=self.cor_fundo, border_color=self.cor_borda, border_width=1, corner_radius=10)
        tabela_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(tabela_frame, columns=self.COLUNAS, show="headings", selectmode="browse")
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        for col in self.COLUNAS:
            self.tree.heading(col, text=col)
            anchor = "center"
            width = 100
            if col in ("FACÇÃO", "SERVIÇO", "MODELO"):
                anchor, width = "w", 200
            if col == "TOTAL":
                width = 120
            self.tree.column(col, anchor=anchor, width=width, stretch=True)

        # Rodapé (totais)
        footer = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        footer.pack(fill="x", padx=10, pady=(0, 12))

        ctk.CTkLabel(footer, text="Total Geral (R$):", text_color=self.cor_texto).pack(side="left")
        self.lbl_total = ctk.CTkLabel(footer, text="0,00", font=ctk.CTkFont(size=16, weight="bold"),
                                      text_color=self.cor_texto)
        self.lbl_total.pack(side="left", padx=(6, 0))

    # ---------------------- Lógica ----------------------
    def _buscar(self):
        # Limpa a tabela
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Consulta o banco, se disponível
        registros = []
        total_geral = 0.0

        ini = self.ini_var.get().strip()
        fim = self.fim_var.get().strip()
        faccao = self.faccao_var.get().strip()
        servico = self.servico_var.get().strip()

        if db and getattr(db, "ready_check", lambda: False)():
            try:
                require_ready(['cortes_finalizados', 'pagamento_corte_acabamento'])
            except Exception:
                # seguimos sem travar a UI
                pass

            try:
                # Exemplo de query – ajuste aos seus nomes reais de colunas/tabelas
                sql = """
                    SELECT
                        to_char(cf.data_finalizacao, 'YYYY-MM-DD') AS data,
                        coalesce(cf.faccao, '') AS faccao,
                        coalesce(cf.servico, '') AS servico,
                        coalesce(cf.ordem, '')   AS ordem,
                        coalesce(cf.modelo, '')  AS modelo,
                        cf.qtd as quantidade,
                        cf.valor_unitario as valor_un,
                        (cf.qtd * cf.valor_unitario) as total
                    FROM cortes_finalizados cf
                    WHERE cf.data_finalizacao BETWEEN %s AND %s
                      AND (%s = 'Todas' OR cf.faccao ILIKE %s)
                      AND (%s = 'Todos' OR cf.servico ILIKE %s)
                    ORDER BY cf.data_finalizacao ASC
                """
                params = (ini, fim, faccao or "Todas", f"%{faccao}%", servico or "Todos", f"%{servico}%")
                rows = db.fetch_all(sql, params)

                for r in rows:
                    linha = (
                        r.get("data", ""),
                        r.get("faccao", ""),
                        r.get("servico", ""),
                        r.get("ordem", ""),
                        r.get("modelo", ""),
                        r.get("quantidade", 0),
                        f"{float(r.get('valor_un', 0)):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                        f"{float(r.get('total', 0)):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    )
                    self.tree.insert("", "end", values=linha)
                    total_geral += float(r.get("total", 0) or 0)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao consultar dados:\n{e}")
                if self.logger:
                    import traceback
                    self.logger.error(f"[RELATORIO] Serviços Externos: erro na consulta: {e}\n{traceback.format_exc()}")

        else:
            # Sem banco: dados fictícios para visual
            demo = [
                ("2025-11-01", "Facção Alfa", "Costura", "OC-001", "M1234", 120, 2.50, 300.00),
                ("2025-11-02", "Facção Beta", "Vincar",  "OC-002", "M5678", 80,  1.90, 152.00),
            ]
            for d in demo:
                linha = (
                    d[0], d[1], d[2], d[3], d[4],
                    d[5],
                    f"{float(d[6]):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    f"{float(d[7]):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                )
                self.tree.insert("", "end", values=linha)
                total_geral += float(d[7])

        self.lbl_total.configure(
            text=f"{total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    def _exportar_csv(self):
        if not self.tree.get_children():
            messagebox.showinfo("Exportar", "Não há dados para exportar.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Salvar CSV"
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(self.COLUNAS)
                for iid in self.tree.get_children():
                    vals = self.tree.item(iid, "values")
                    writer.writerow(vals)
            messagebox.showinfo("Exportar", f"Arquivo salvo:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar CSV:\n{e}")
            if self.logger:
                import traceback
                self.logger.error(f"[RELATORIO] Serviços Externos: erro ao exportar CSV: {e}\n{traceback.format_exc()}")


# Execução isolada (debug)
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Relatório de Serviços Externos")
    app.geometry("1000x650")
    page = RelatorioServicosExternosPage(app, sistema=None)
    page.pack(fill="both", expand=True)
    app.mainloop()


#03/02/2025


# --- Suporte de idioma consolidado desta página ---
import tkinter as _tk_i18n
from tkinter import ttk as _ttk_i18n


def _opera_page_lang(instance):
    idioma = getattr(getattr(instance, "sistema", None), "idioma_atual", None)
    if not idioma:
        idioma = getattr(getattr(instance, "host", None), "idioma_atual", None)
    if not idioma:
        idioma = getattr(instance, "idioma_atual", None)
    return idioma or "pt_BR"


def _opera_translate_widget_tree(instance, widget, translation_map):
    try:
        for opt in ("text", "placeholder_text"):
            try:
                current = widget.cget(opt)
            except Exception:
                continue
            if isinstance(current, str) and current in translation_map:
                try:
                    widget.configure(**{opt: translation_map[current]})
                except Exception:
                    pass

        try:
            values = widget.cget("values")
        except Exception:
            values = None
        if isinstance(values, (list, tuple)):
            mapped = [translation_map.get(v, v) if isinstance(v, str) else v for v in values]
            if list(mapped) != list(values):
                try:
                    widget.configure(values=mapped)
                except Exception:
                    pass

        if isinstance(widget, _ttk_i18n.Treeview):
            try:
                heading = widget.heading("#0")
                text = heading.get("text", "")
                if text in translation_map:
                    widget.heading("#0", text=translation_map[text])
            except Exception:
                pass
            try:
                for col in widget["columns"]:
                    heading = widget.heading(col)
                    text = heading.get("text", "")
                    if text in translation_map:
                        widget.heading(col, text=translation_map[text])
            except Exception:
                pass

        if isinstance(widget, _tk_i18n.Menu):
            try:
                end = widget.index("end")
            except Exception:
                end = None
            if end is not None:
                for idx in range(end + 1):
                    try:
                        label = widget.entrycget(idx, "label")
                    except Exception:
                        continue
                    if isinstance(label, str) and label in translation_map:
                        try:
                            widget.entryconfigure(idx, label=translation_map[label])
                        except Exception:
                            pass

        for child in widget.winfo_children():
            _opera_translate_widget_tree(instance, child, translation_map)
    except Exception:
        pass


def _opera_apply_page_i18n(instance, class_ref, page_title=None):
    idioma = _opera_page_lang(instance)
    maps = getattr(class_ref, "_TRANSLATIONS", {}) or {}
    base = maps.get("pt_BR", {}) if isinstance(maps.get("pt_BR", {}), dict) else {}
    current = maps.get(idioma, {}) if isinstance(maps.get(idioma, {}), dict) else {}
    translation_map = dict(base)
    translation_map.update(current)

    for attr in ("titulo", "title_label", "lbl_titulo", "header_title", "page_title_label"):
        widget = getattr(instance, attr, None)
        if widget is not None:
            try:
                current_text = widget.cget("text")
                if isinstance(current_text, str):
                    widget.configure(text=translation_map.get(current_text, current_text))
            except Exception:
                pass

    if page_title:
        try:
            instance.PAGE_TITLE = translation_map.get(page_title, page_title)
        except Exception:
            pass

    _opera_translate_widget_tree(instance, instance, translation_map)


def _opera_set_idioma_factory(class_ref, page_title=None):
    def set_idioma(self, idioma):
        self.idioma_atual = idioma
        _opera_apply_page_i18n(self, class_ref, page_title)

    def on_language_changed(self, idioma=None):
        if idioma:
            self.idioma_atual = idioma
        _opera_apply_page_i18n(self, class_ref, page_title)

    def refresh_texts(self):
        _opera_apply_page_i18n(self, class_ref, page_title)

    return set_idioma, on_language_changed, refresh_texts



RelatorioServicosExternosPage._TRANSLATIONS = {
    "pt_BR": {'🚚 Relatório de Serviços Externos': '🚚 Relatório de Serviços Externos', 'Início': 'Início', 'Fim': 'Fim', 'Facção': 'Facção', 'Serviço': 'Serviço', '🔍 Buscar': '🔍 Buscar', '⬇️ Exportar CSV': '⬇️ Exportar CSV', 'Todas': 'Todas', 'Todos': 'Todos', 'Total Geral (R$):': 'Total Geral (R$):', 'DATA': 'DATA', 'FACÇÃO': 'FACÇÃO', 'SERVIÇO': 'SERVIÇO', 'ORDEM': 'ORDEM', 'MODELO': 'MODELO', 'QTD': 'QTD', 'VALOR_UN': 'VALOR_UN', 'TOTAL': 'TOTAL'},
    "en_US": {'🚚 Relatório de Serviços Externos': '🚚 External Services Report', 'Início': 'Start', 'Fim': 'End', 'Facção': 'Contractor', 'Serviço': 'Service', '🔍 Buscar': '🔍 Search', '⬇️ Exportar CSV': '⬇️ Export CSV', 'Todas': 'All', 'Todos': 'All', 'Total Geral (R$):': 'Grand Total (R$):', 'DATA': 'DATE', 'FACÇÃO': 'CONTRACTOR', 'SERVIÇO': 'SERVICE', 'ORDEM': 'ORDER', 'MODELO': 'MODEL', 'QTD': 'QTY', 'VALOR_UN': 'UNIT_VALUE', 'TOTAL': 'TOTAL'},
    "es_ES": {'🚚 Relatório de Serviços Externos': '🚚 Reporte de Servicios Externos', 'Início': 'Inicio', 'Fim': 'Fin', 'Facção': 'Facción', 'Serviço': 'Servicio', '🔍 Buscar': '🔍 Buscar', '⬇️ Exportar CSV': '⬇️ Exportar CSV', 'Todas': 'Todas', 'Todos': 'Todos', 'Total Geral (R$):': 'Total General (R$):', 'DATA': 'FECHA', 'FACÇÃO': 'FACCIÓN', 'SERVIÇO': 'SERVICIO', 'ORDEM': 'ORDEN', 'MODELO': 'MODELO', 'QTD': 'CANT.', 'VALOR_UN': 'VALOR_UN', 'TOTAL': 'TOTAL'},
}

RelatorioServicosExternosPage.TRANSLATIONS = RelatorioServicosExternosPage._TRANSLATIONS
RelatorioServicosExternosPage.PAGE_TITLE = 'Relatório de Serviços Externos'
RelatorioServicosExternosPage.set_idioma, RelatorioServicosExternosPage.on_language_changed, RelatorioServicosExternosPage.refresh_texts = _opera_set_idioma_factory(RelatorioServicosExternosPage, 'Relatório de Serviços Externos')
