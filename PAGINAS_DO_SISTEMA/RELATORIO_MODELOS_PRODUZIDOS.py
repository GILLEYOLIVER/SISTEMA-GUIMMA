# RELATORIO_MODELOS_PRODUZIDOS.py
# Relatório de Modelos Produzidos – compatível com MENU_PRINCIPAL

from __future__ import annotations
from PAGINAS_DO_SISTEMA import TEMAS
import csv
from datetime import date, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

# Banco de dados (opcional)
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
    prox = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return prox - timedelta(days=1)
# JESUS SEJA LOUVADO PARA TODO O SEMPRE AMEM!!!

# ---------------------- Página ----------------------
class RelatorioModelosProduzidosPage(ctk.CTkFrame):
    """
    Página de Relatório de Modelos Produzidos.

    Compatível com MENU_PRINCIPAL:
        "file":  "RELATORIO_MODELOS_PRODUZIDOS.py",
        "class": "RelatorioModelosProduzidosPage"
    """

    COLUNAS = (
        "DATA",
        "ORDEM",
        "MODELO",
        "DESCRIÇÃO",
        "COR",
        "TAMANHO",
        "QTD",
        "VALOR_UN",
        "TOTAL",
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

        # Tema herdado do sistema (com defaults)
        origem = self.sistema
        self.cor_fundo = getattr(origem, "cor_fundo", "#0E1525")
        self.cor_texto = getattr(origem, "cor_texto", "#e5e7eb")
        self.cor_borda = getattr(origem, "cor_borda", "#334155")
        self.cor_primaria = getattr(origem, "cor_primaria", "#1F538D")
        self.cor_hover = getattr(origem, "cor_hover", "#14375E")
        self.cor_destaque = getattr(origem, "cor_selecao", "#223649")

        # Filtros padrão (mês atual)
        hoje = date.today()
        self.ini_var = tk.StringVar(
            value=_first_day_of_month(hoje).strftime("%Y-%m-%d")
        )
        self.fim_var = tk.StringVar(
            value=_last_day_of_month(hoje).strftime("%Y-%m-%d")
        )
        self.modelo_var = tk.StringVar(value="")
        self.ordem_var = tk.StringVar(value="")
        self.incluir_acabamento = tk.BooleanVar(value=True)

        # Cria UI
        self._apply_ttk_theme()
        self._build_ui()

        # Carrega dados iniciais
        self._buscar()

        if self.logger:
            self.logger.info(
                "[PAGINA] Relatório de Modelos Produzidos: inicialização OK"
            )

    # ---------------------- Tema Treeview ----------------------
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
            relief="flat",
        )
        style.map("Treeview", background=[("selected", self.cor_destaque)])

    # ---------------------- UI ----------------------
    def _build_ui(self):
        self.configure(fg_color=self.cor_fundo)

        # Título
        header = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            header,
            text="📦 Relatório de Modelos Produzidos",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.cor_texto,
        ).pack(side="left")

        # Filtros
        filtros = ctk.CTkFrame(
            self,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            border_width=1,
            corner_radius=10,
        )
        filtros.pack(fill="x", padx=10, pady=(0, 10))

        # Período
        bloco_data = ctk.CTkFrame(filtros, fg_color=self.cor_fundo)
        bloco_data.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(
            bloco_data, text="Início", text_color=self.cor_texto
        ).grid(row=0, column=0, sticky="w")
        self.ini_entry = ctk.CTkEntry(
            bloco_data, textvariable=self.ini_var, width=120
        )
        self.ini_entry.grid(row=1, column=0, padx=(0, 8))

        ctk.CTkLabel(
            bloco_data, text="Fim", text_color=self.cor_texto
        ).grid(row=0, column=1, sticky="w")
        self.fim_entry = ctk.CTkEntry(
            bloco_data, textvariable=self.fim_var, width=120
        )
        self.fim_entry.grid(row=1, column=1)

        # Modelo / Ordem
        bloco_filtro = ctk.CTkFrame(filtros, fg_color=self.cor_fundo)
        bloco_filtro.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(
            bloco_filtro, text="Código/Modelo", text_color=self.cor_texto
        ).grid(row=0, column=0, sticky="w")
        self.modelo_entry = ctk.CTkEntry(
            bloco_filtro,
            textvariable=self.modelo_var,
            width=200,
            placeholder_text="vazio = todos",
        )
        self.modelo_entry.grid(row=1, column=0, padx=(0, 8))

        ctk.CTkLabel(
            bloco_filtro, text="Ordem", text_color=self.cor_texto
        ).grid(row=0, column=1, sticky="w")
        self.ordem_entry = ctk.CTkEntry(
            bloco_filtro,
            textvariable=self.ordem_var,
            width=140,
            placeholder_text="vazio = todas",
        )
        self.ordem_entry.grid(row=1, column=1)

        # Checkbox
        bloco_chk = ctk.CTkFrame(filtros, fg_color=self.cor_fundo)
        bloco_chk.pack(side="left", padx=10, pady=10)

        ctk.CTkCheckBox(
            bloco_chk,
            text="Incluir peças de acabamento",
            variable=self.incluir_acabamento,
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            border_color=self.cor_borda,
        ).pack(anchor="w")

        # Ações
        acoes = ctk.CTkFrame(filtros, fg_color=self.cor_fundo)
        acoes.pack(side="right", padx=10, pady=10)

        ctk.CTkButton(
            acoes,
            text="🔍 Buscar",
            fg_color=self.cor_primaria,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=self._buscar,
            width=120,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            acoes,
            text="⬇️ Exportar CSV",
            fg_color=self.cor_destaque,
            hover_color=self.cor_hover,
            text_color=self.cor_texto,
            command=self._exportar_csv,
            width=140,
        ).pack(side="left", padx=6)

        # Tabela
        frame_tabela = ctk.CTkFrame(
            self,
            fg_color=self.cor_fundo,
            border_color=self.cor_borda,
            border_width=1,
            corner_radius=10,
        )
        frame_tabela.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(
            frame_tabela,
            columns=self.COLUNAS,
            show="headings",
            selectmode="browse",
        )
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        for col in self.COLUNAS:
            self.tree.heading(col, text=col)
            anchor = "center"
            width = 90
            if col in ("MODELO", "DESCRIÇÃO"):
                anchor, width = "w", 220
            if col == "COR":
                anchor, width = "w", 120
            if col == "TOTAL":
                width = 110
            self.tree.column(col, anchor=anchor, width=width, stretch=True)

        # Rodapé de totais
        footer = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        footer.pack(fill="x", padx=10, pady=(0, 12))

        ctk.CTkLabel(
            footer, text="Total Geral (peças):", text_color=self.cor_texto
        ).pack(side="left")
        self.lbl_total_pecas = ctk.CTkLabel(
            footer,
            text="0",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.cor_texto,
        )
        self.lbl_total_pecas.pack(side="left", padx=(4, 12))

        ctk.CTkLabel(
            footer, text="Total Geral (R$):", text_color=self.cor_texto
        ).pack(side="left")
        self.lbl_total_valor = ctk.CTkLabel(
            footer,
            text="0,00",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.cor_texto,
        )
        self.lbl_total_valor.pack(side="left", padx=(4, 0))

    # ---------------------- Busca ----------------------
    def _buscar(self):
        # Limpa tabela
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        total_pecas = 0
        total_valor = 0.0

        ini = self.ini_var.get().strip()
        fim = self.fim_var.get().strip()
        modelo = self.modelo_var.get().strip()
        ordem = self.ordem_var.get().strip()

        if db and getattr(db, "ready_check", lambda: False)():
            try:
                # Ajuste os nomes das tabelas/colunas para os reais do seu banco:
                # Exemplo usando uma tabela hipotética "producao_modelos"
                require_ready(["producao_modelos"])

                sql = """
                    SELECT
                        to_char(data_producao, 'YYYY-MM-DD') AS data,
                        ordem_producao                         AS ordem,
                        codigo_modelo                          AS modelo,
                        descricao_modelo                       AS descricao,
                        cor                                    AS cor,
                        tamanho                                AS tamanho,
                        quantidade                             AS qtd,
                        valor_unitario                         AS valor_un,
                        (quantidade * valor_unitario)          AS total
                    FROM producao_modelos
                    WHERE data_producao BETWEEN %s AND %s
                      AND (%s = '' OR codigo_modelo ILIKE %s OR descricao_modelo ILIKE %s)
                      AND (%s = '' OR ordem_producao ILIKE %s)
                    ORDER BY data_producao ASC, ordem_producao ASC
                """

                params = (
                    ini,
                    fim,
                    modelo,
                    f"%{modelo}%",
                    f"%{modelo}%",
                    ordem,
                    f"%{ordem}%",
                )

                rows = db.fetch_all(sql, params)

                for r in rows:
                    qtd = int(r.get("qtd", 0) or 0)
                    v_un = float(r.get("valor_un", 0) or 0)
                    total = float(r.get("total", qtd * v_un))

                    linha = (
                        r.get("data", ""),
                        r.get("ordem", ""),
                        r.get("modelo", ""),
                        r.get("descricao", ""),
                        r.get("cor", ""),
                        r.get("tamanho", ""),
                        qtd,
                        f"{v_un:,.2f}".replace(",", "X").replace(".", ",").replace(
                            "X", "."
                        ),
                        f"{total:,.2f}".replace(",", "X").replace(".", ",").replace(
                            "X", "."
                        ),
                    )
                    self.tree.insert("", "end", values=linha)
                    total_pecas += qtd
                    total_valor += total

            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao consultar dados:\n{e}")
                if self.logger:
                    import traceback

                    self.logger.error(
                        f"[RELATORIO] Modelos Produzidos: erro na consulta: {e}\n{traceback.format_exc()}"
                    )
        else:
            # Sem banco: dados fictícios apenas para visual
            demo = [
                ("2025-11-01", "OC-001", "M1234", "Vestido Tubinho", "Preto", "M", 80, 39.9),
                ("2025-11-01", "OC-001", "M1234", "Vestido Tubinho", "Preto", "G", 60, 39.9),
                ("2025-11-02", "OC-002", "M5678", "Saia Midi", "Azul", "M", 100, 29.9),
            ]
            for d in demo:
                total = d[6] * d[7]
                linha = (
                    d[0],
                    d[1],
                    d[2],
                    d[3],
                    d[4],
                    d[5],
                    d[6],
                    f"{d[7]:,.2f}".replace(",", "X").replace(".", ",").replace(
                        "X", "."
                    ),
                    f"{total:,.2f}".replace(",", "X").replace(".", ",").replace(
                        "X", "."
                    ),
                )
                self.tree.insert("", "end", values=linha)
                total_pecas += d[6]
                total_valor += total

        self.lbl_total_pecas.configure(text=str(total_pecas))
        self.lbl_total_valor.configure(
            text=f"{total_valor:,.2f}".replace(",", "X").replace(".", ",").replace(
                "X", "."
            )
        )

    # ---------------------- Exportar ----------------------
    def _exportar_csv(self):
        if not self.tree.get_children():
            messagebox.showinfo("Exportar", "Não há dados para exportar.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            title="Salvar CSV",
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

                self.logger.error(
                    f"[RELATORIO] Modelos Produzidos: erro ao exportar CSV: {e}\n{traceback.format_exc()}"
                )


# Execução direta (debug)
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Relatório de Modelos Produzidos")
    app.geometry("1050x650")
    page = RelatorioModelosProduzidosPage(app, sistema=None)
    page.pack(fill="both", expand=True)
    app.mainloop()

#03/02/2025

# --- Adaptador global de idioma (injeção automática) ---
try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    attach_i18n_support(RelatorioModelosProduzidosPage)
except Exception:
    pass
