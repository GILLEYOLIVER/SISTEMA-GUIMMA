# RELATORIO_SERVICOS_EXTERNOS.py
# Relatório de Serviços Externos (Facções) – compatível com MENU_PRINCIPAL

from __future__ import annotations
from PAGINAS_DO_SISTEMA import TEMAS
import csv
import os
from datetime import date, datetime, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import unicodedata

import customtkinter as ctk
from PAGINAS_DO_SISTEMA.UI_CALENDARIO import abrir_calendario, vincular_calendario

REL_SERVICOS_EXTERNOS_TREEVIEW_STYLE = "RelatorioServicosExternos.Treeview"

# Banco (opcional)
try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, ready_check, require_ready
except Exception:
    get_conn = None

    def get_schema():
        return "opera"

    def ready_check():
        return False

    def require_ready(_tables=None):
        return False, "Módulo BANCO_DE_DADOS_PG indisponível"


# ---------------------- Helpers de datas ----------------------
def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)

def _last_day_of_month(d: date) -> date:
    next_month = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


def _normalizar_texto(valor) -> str:
    texto = str(valor or "").strip().lower()
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def _eh_faccao(valor) -> bool:
    texto = _normalizar_texto(valor)
    return texto in ("faccao", "facao") or texto.startswith("fac")

# ---------------------- Página ----------------------
class RelatorioServicosExternosPage(ctk.CTkFrame):
    """
    Página de Relatório de Serviços Externos (Facções).
    Compatível com MENU_PRINCIPAL: __init__(master, sistema=None, *args, **kwargs)
    """

    COLUNAS = (
        "DATA", "FACÇÃO", "SERVIÇO", "ORDEM", "MODELO", "QTD", "VALOR_UN", "TOTAL"
    )
    SERVICOS_FILTRO = (
        "Todos", "Facção", "Bordado", "Caseador", "Botões",
        "Estamparia", "Interna", "Tingimento", "Outros Trabalhos"
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
        self.faccao_options, self.servico_options = self._carregar_opcoes_filtros()

        # Constrói UI
        self._apply_ttk_theme()
        self._build_ui()

        # Carrega dados iniciais
        self._buscar()

        if self.logger:
            self.logger.info("[PAGINA] Relatório de Serviços Externos: inicialização OK")

    # ---------------------- UI ----------------------
    def _apply_ttk_theme(self):
        style = ttk.Style(self)

        style.configure(
            REL_SERVICOS_EXTERNOS_TREEVIEW_STYLE,
            background=self.cor_fundo,
            fieldbackground=self.cor_fundo,
            foreground=self.cor_texto,
            bordercolor=self.cor_borda,
            rowheight=26,
        )
        style.configure(
            f"{REL_SERVICOS_EXTERNOS_TREEVIEW_STYLE}.Heading",
            background=self.cor_destaque,
            foreground=self.cor_texto,
            relief="flat"
        )
        style.map(REL_SERVICOS_EXTERNOS_TREEVIEW_STYLE, background=[("selected", self.cor_destaque)])

    def _carregar_opcoes_filtros(self):
        faccoes = ["Todas"]
        servicos = list(self.SERVICOS_FILTRO)

        if get_conn and ready_check():
            try:
                schema = get_schema()
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"SET LOCAL search_path = {schema}")
                        cur.execute(
                            """
                            SELECT DISTINCT COALESCE(costureira, '') AS faccao
                              FROM cortes_finalizados
                             WHERE COALESCE(costureira, '') <> ''
                             ORDER BY 1
                            """
                        )
                        for row in cur.fetchall() or []:
                            valor = str(row[0] or "").strip()
                            if valor and valor not in faccoes:
                                faccoes.append(valor)

                        cur.execute(
                            """
                            SELECT DISTINCT COALESCE(tipo_servico, '') AS servico
                              FROM cortes_finalizados
                             WHERE COALESCE(tipo_servico, '') <> ''
                             ORDER BY 1
                            """
                        )
                        for row in cur.fetchall() or []:
                            valor = str(row[0] or "").strip()
                            if valor and valor not in servicos:
                                servicos.append(valor)
            except Exception:
                pass

        if len(faccoes) == 1:
            faccoes.extend(["Facção Alfa", "Facção Beta"])
        for valor in ("Costura", "Vincar"):
            if valor not in servicos:
                servicos.append(valor)

        return faccoes, servicos

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
        vincular_calendario(self, self.ini_entry, output_format="%Y-%m-%d", on_select=lambda _data: self._buscar())
        ctk.CTkButton(
            bloco_data,
            text="📅",
            width=32,
            height=30,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=lambda: self._abrir_calendario(self.ini_entry),
        ).grid(row=1, column=1, padx=(0, 8))

        ctk.CTkLabel(bloco_data, text="Fim", text_color=self.cor_texto).grid(row=0, column=2, sticky="w")
        self.fim_entry = ctk.CTkEntry(bloco_data, textvariable=self.fim_var, width=120)
        self.fim_entry.grid(row=1, column=2)
        vincular_calendario(self, self.fim_entry, output_format="%Y-%m-%d", on_select=lambda _data: self._buscar())
        ctk.CTkButton(
            bloco_data,
            text="📅",
            width=32,
            height=30,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=lambda: self._abrir_calendario(self.fim_entry),
        ).grid(row=1, column=3, padx=(8, 0))

        for entry in (self.ini_entry, self.fim_entry):
            entry.bind("<Return>", lambda _event: self._buscar(), add="+")
            entry.bind("<FocusOut>", lambda _event: self._buscar(), add="+")

        # Facção/Serviço
        bloco_sel = ctk.CTkFrame(filtros, fg_color=self.cor_fundo)
        bloco_sel.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(bloco_sel, text="Facção", text_color=self.cor_texto).grid(row=0, column=0, sticky="w")
        self.faccao_entry = ctk.CTkComboBox(
            bloco_sel,
            variable=self.faccao_var,
            values=self.faccao_options,
            width=200,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            dropdown_fg_color=self.cor_fundo,
            dropdown_hover_color=self.cor_hover,
            dropdown_text_color=self.cor_texto,
            text_color=self.cor_texto,
            command=lambda _valor=None: self._buscar(),
        )
        self.faccao_entry.grid(row=1, column=0, padx=(0, 8))

        ctk.CTkLabel(bloco_sel, text="Serviço", text_color=self.cor_texto).grid(row=0, column=1, sticky="w")
        self.servico_entry = ctk.CTkComboBox(
            bloco_sel,
            variable=self.servico_var,
            values=self.servico_options,
            width=200,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            button_color=self.cor_primaria,
            button_hover_color=self.cor_hover,
            dropdown_fg_color=self.cor_fundo,
            dropdown_hover_color=self.cor_hover,
            dropdown_text_color=self.cor_texto,
            text_color=self.cor_texto,
            command=lambda _valor=None: self._buscar(),
        )
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

        self.tree = ttk.Treeview(
            tabela_frame,
            columns=self.COLUNAS,
            show="headings",
            selectmode="browse",
            style=REL_SERVICOS_EXTERNOS_TREEVIEW_STYLE,
        )
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

    def _abrir_calendario(self, entry):
        return abrir_calendario(
            self,
            entry,
            output_format="%Y-%m-%d",
            on_select=lambda _data: self._buscar(),
        )

    def _parse_filter_date(self, value):
        text = str(value or "").strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(text[:10], fmt).date()
            except Exception:
                pass
        return None

    def _date_matches(self, row_date, ini_date, fim_date):
        data = self._parse_filter_date(row_date)
        if not data:
            return False
        if ini_date and data < ini_date:
            return False
        if fim_date and data > fim_date:
            return False
        return True

    def _faccao_matches(self, row_faccao, filtro):
        filtro = str(filtro or "").strip()
        if not filtro or filtro in ("Todas", "Todos"):
            return True
        return _normalizar_texto(filtro) in _normalizar_texto(row_faccao)

    def _servico_matches(self, row_servico, filtro):
        filtro = str(filtro or "").strip()
        if not filtro or filtro == "Todos":
            return True

        servico = _normalizar_texto(row_servico)
        filtro_norm = _normalizar_texto(filtro)

        if _eh_faccao(filtro):
            return servico in ("costura", "faccao", "faccao externa")

        return filtro_norm in servico

    # ---------------------- Lógica ----------------------
    def _buscar(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        total_geral = 0.0

        ini = self.ini_var.get().strip()
        fim = self.fim_var.get().strip()
        faccao = self.faccao_var.get().strip()
        servico = self.servico_var.get().strip()
        ini_date = self._parse_filter_date(ini)
        fim_date = self._parse_filter_date(fim)
        ini_sql = ini_date.strftime("%Y-%m-%d") if ini_date else "1900-01-01"
        fim_sql = fim_date.strftime("%Y-%m-%d") if fim_date else "2999-12-31"

        if get_conn and ready_check():
            try:
                require_ready(['cortes_finalizados'])
            except Exception:
                pass

            try:
                schema = get_schema()
                sql = """
                    SELECT
                        to_char(COALESCE(cf.data_final, cf.data_chegada, cf.data_envio)::date, 'YYYY-MM-DD') AS data,
                        COALESCE(cf.costureira, '') AS faccao,
                        COALESCE(cf.tipo_servico, '') AS servico,
                        COALESCE(cf.codigo, '') AS ordem,
                        COALESCE(cf.descricao, '') AS modelo,
                        COALESCE(cf.quantidade_finalizada, cf.total_pecas, cf.qtd_enviada, 0) AS quantidade,
                        COALESCE(cf.valor_peca, 0) AS valor_un,
                        COALESCE(
                            cf.valor_total,
                            COALESCE(cf.quantidade_finalizada, cf.total_pecas, cf.qtd_enviada, 0) * COALESCE(cf.valor_peca, 0)
                        ) AS total
                    FROM cortes_finalizados cf
                    WHERE COALESCE(cf.data_final, cf.data_chegada, cf.data_envio)::date BETWEEN %s AND %s
                      AND (%s = 'Todas' OR cf.costureira ILIKE %s)
                      AND (
                            %s = 'Todos'
                         OR cf.tipo_servico ILIKE %s
                         OR (%s AND cf.tipo_servico ILIKE '%%Costura%%')
                      )
                    ORDER BY COALESCE(cf.data_final, cf.data_chegada, cf.data_envio)::date ASC, cf.id ASC
                """
                servico_sql = servico or "Todos"
                servico_faccao = _eh_faccao(servico)
                params = (
                    ini_sql,
                    fim_sql,
                    faccao or "Todas",
                    f"%{faccao}%",
                    servico_sql,
                    f"%{servico}%",
                    servico_faccao,
                )
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"SET LOCAL search_path = {schema}")
                        cur.execute(sql, params)
                        rows = cur.fetchall()

                for r in rows:
                    linha = (
                        r[0] or "",
                        r[1] or "",
                        r[2] or "",
                        r[3] or "",
                        r[4] or "",
                        r[5] or 0,
                        f"{float(r[6] or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                        f"{float(r[7] or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    )
                    self.tree.insert("", "end", values=linha)
                    total_geral += float(r[7] or 0)
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
                if not self._date_matches(d[0], ini_date, fim_date):
                    continue
                if not self._faccao_matches(d[1], faccao):
                    continue
                if not self._servico_matches(d[2], servico):
                    continue
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

# --- Suporte trilíngue individual desta página ---
RelatorioServicosExternosPage_TRANSLATIONS = {
    "pt_BR": {
        "title": "Serviços Externos",
        "Atualizar": "Atualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
    },
    "en_US": {
        "title": "External Services",
        "Atualizar": "Refresh",
        "Filtrar": "Filter",
        "Limpar": "Clear",
        "Exportar": "Export",
        "Imprimir": "Print",
        "Buscar": "Search",
    },
    "es_ES": {
        "title": "Servicios Externos",
        "Atualizar": "Actualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpiar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
    },
}


def _apply_relatorioservicosexternospage_translations(self):
    """Aplica tradução individual desta página."""
    idioma = getattr(getattr(self, "sistema", None), "idioma_atual", getattr(self, "idioma_atual", "pt_BR"))
    if idioma not in RelatorioServicosExternosPage_TRANSLATIONS:
        idioma = "pt_BR"
    if hasattr(self, "titulo"):
        try:
            self.titulo.configure(text=RelatorioServicosExternosPage_TRANSLATIONS[idioma]["title"])
        except Exception:
            pass


try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    RelatorioServicosExternosPage.TRANSLATIONS = RelatorioServicosExternosPage_TRANSLATIONS
    if not hasattr(RelatorioServicosExternosPage, "apply_page_translations"):
        RelatorioServicosExternosPage.apply_page_translations = _apply_relatorioservicosexternospage_translations
    attach_i18n_support(RelatorioServicosExternosPage, RelatorioServicosExternosPage_TRANSLATIONS)
except Exception:
    pass
