# RELATORIO_ACABAMENTO.py
# Relatório de Acabamento – compatível com MENU_PRINCIPAL

from __future__ import annotations
import TEMAS
import csv
from datetime import date, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

# Banco de dados (opcional)
try:
    from BANCO_DE_DADOS_PG import db, require_ready
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


# ---------------------- Página ----------------------
class RelatorioAcabamentoPage(ctk.CTkFrame):
    """
    Página de Relatório de Acabamento.

    Compatível com MENU_PRINCIPAL:
        "file":  "RELATORIO_ACABAMENTO.py",
        "class": "RelatorioAcabamentoPage"
    """

    COLUNAS = (
        "DATA",
        "ORDEM",
        "MODELO",
        "DESCRIÇÃO",
        "FACÇÃO",
        "SERVIÇO",
        "QTD",
        "VALOR_UN",
        "TOTAL",
        "STATUS",
    )

    def __init__(self, master, sistema=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        # Referência ao sistema / menu principal (quando vier pelo MENU_PRINCIPAL)
        self.sistema = sistema

        # Garante que o frame ocupe a área toda
        self.pack(fill="both", expand=True)

        # Logger opcional
        try:
            from LOG_SISTEMA import get_logger
            self.logger = get_logger("OPERA_SYSTEM")
        except Exception:
            self.logger = None

        # ============================================================
        # TEMA – MESMO PADRÃO DO RESTANTE DO SISTEMA (ENTRADA_ESTOQUE)
        # ============================================================
        origem = self.sistema

        if origem is not None and hasattr(origem, "cor_fundo"):
            # Herdar cores do MENU_PRINCIPAL quando a página é aberta por ele
            self.cor_fundo = getattr(origem, "cor_fundo", "#0E1525")
            self.cor_primaria = getattr(origem, "cor_primaria", "#1F538D")
            self.cor_secundaria = getattr(origem, "cor_secundaria", "#111827")
            self.cor_texto = getattr(origem, "cor_texto", "#e5e7eb")
            self.cor_borda = getattr(origem, "cor_borda", "#334155")
            self.cor_hover = getattr(origem, "cor_hover", "#14375E")

            # Cores de destaque / seleção / status
            self.cor_destaque = getattr(origem, "cor_selecao", "#223649")
            self.cor_selecao = getattr(origem, "cor_selecao", self.cor_destaque)
            self.cor_sucesso = getattr(origem, "cor_sucesso", "#22C55E")
            self.cor_alerta = getattr(origem, "cor_alerta", "#EF4444")
        else:
            # Fallback quando a página é executada ISOLADA (sistema=None)
            tema_atual = ctk.get_appearance_mode()
            if tema_atual == "Dark":
                self.cor_fundo = "#020617"
                self.cor_primaria = "#1f2937"
                self.cor_secundaria = "#111827"
                self.cor_texto = "#e5e7eb"
                self.cor_borda = "#273244"
                self.cor_hover = "#334155"
                self.cor_destaque = "#1d4ed8"
                self.cor_selecao = self.cor_destaque
                self.cor_sucesso = "#22C55E"
                self.cor_alerta = "#EF4444"
            else:
                self.cor_fundo = "#ffffff"
                self.cor_primaria = "#3a7ebf"
                self.cor_secundaria = "#f0f0f0"
                self.cor_texto = "black"
                self.cor_borda = "#cccccc"
                self.cor_hover = "#2e4a66"
                self.cor_destaque = self.cor_primaria
                self.cor_selecao = self.cor_primaria
                self.cor_sucesso = "#16A34A"
                self.cor_alerta = "#DC2626"

        # ============================================================
        # FILTROS – mesmo que já existia (mês atual como padrão)
        # ============================================================
        hoje = date.today()
        self.ini_var = tk.StringVar(
            value=_first_day_of_month(hoje).strftime("%Y-%m-%d")
        )
        self.fim_var = tk.StringVar(
            value=_last_day_of_month(hoje).strftime("%Y-%m-%d")
        )
        self.modelo_var = tk.StringVar(value="")
        self.ordem_var = tk.StringVar(value="")
        self.faccao_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Todos")

        # ============================================================
        # APLICA TEMA E MONTA A INTERFACE
        # ============================================================
        self._apply_ttk_theme()
        self._build_ui()

        # Carrega dados iniciais
        self._buscar()

        if self.logger:
            self.logger.info("[PAGINA] Relatório de Acabamento: inicialização OK")


    # ---------------------- Tema Treeview ----------------------
    # ---------------------- Tema Treeview ----------------------
    def _apply_ttk_theme(self):
        """
        Aplica o MESMO estilo de Treeview usado nas outras páginas
        (Entrada de Estoque, Histórico de Serviços, etc).

        Cabeçalho escuro, texto claro e seleção com alto contraste.
        """
        if not hasattr(self, "style"):
            self.style = ttk.Style()

        # "default" é o mais previsível para customizar
        try:
            self.style.theme_use("default")
        except Exception:
            pass

        tema_atual = ctk.get_appearance_mode()
        if tema_atual == "Dark":
            cor_fundo = self.cor_secundaria
            cor_texto = self.cor_texto
            cor_campo = self.cor_secundaria
            cor_selecao = self.cor_selecao
        else:
            cor_fundo = "#f0f0f0"
            cor_texto = "black"
            cor_campo = "#f0f0f0"
            cor_selecao = self.cor_selecao

        # Linhas da tabela
        self.style.configure(
            "Treeview",
            background=cor_fundo,
            fieldbackground=cor_campo,
            foreground=cor_texto,
            bordercolor=self.cor_borda,
            rowheight=26,
            borderwidth=0,
            highlightthickness=0,
        )

        # Cabeçalho com cor primária (igual Entrada de Estoque)
        self.style.configure(
            "Treeview.Heading",
            background=self.cor_primaria,
            foreground=self.cor_texto,
            font=("Arial", 10, "bold"),
            relief="flat",
            borderwidth=1,
        )

        # Seleção forte e legível
        self.style.map(
            "Treeview",
            background=[("selected", cor_selecao)],
            foreground=[("selected", "white")],
        )

    # ---------------------- UI ----------------------
    def _build_ui(self):
        self.configure(fg_color=self.cor_fundo)

        # Título
        header = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        header.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            header,
            text="🎯 Relatório de Acabamento",
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
        bloco_modelo = ctk.CTkFrame(filtros, fg_color=self.cor_fundo)
        bloco_modelo.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(
            bloco_modelo, text="Código/Modelo", text_color=self.cor_texto
        ).grid(row=0, column=0, sticky="w")
        self.modelo_entry = ctk.CTkEntry(
            bloco_modelo,
            textvariable=self.modelo_var,
            width=200,
            placeholder_text="vazio = todos",
        )
        self.modelo_entry.grid(row=1, column=0, padx=(0, 8))

        ctk.CTkLabel(
            bloco_modelo, text="Ordem", text_color=self.cor_texto
        ).grid(row=0, column=1, sticky="w")
        self.ordem_entry = ctk.CTkEntry(
            bloco_modelo,
            textvariable=self.ordem_var,
            width=140,
            placeholder_text="vazio = todas",
        )
        self.ordem_entry.grid(row=1, column=1)

        # Facção / Status
        bloco_faccao = ctk.CTkFrame(filtros, fg_color=self.cor_fundo)
        bloco_faccao.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(
            bloco_faccao, text="Facção", text_color=self.cor_texto
        ).grid(row=0, column=0, sticky="w")
        self.faccao_entry = ctk.CTkEntry(
            bloco_faccao,
            textvariable=self.faccao_var,
            width=200,
            placeholder_text="vazio = todas",
        )
        self.faccao_entry.grid(row=1, column=0, padx=(0, 8))

        ctk.CTkLabel(
            bloco_faccao, text="Status", text_color=self.cor_texto
        ).grid(row=0, column=1, sticky="w")
        self.status_combo = ctk.CTkComboBox(
            bloco_faccao,
            values=["Todos", "Pendente", "Finalizado", "Estornado"],
            variable=self.status_var,
            width=140,
        )
        self.status_combo.grid(row=1, column=1)

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
            if col in ("MODELO", "DESCRIÇÃO", "FACÇÃO", "SERVIÇO"):
                anchor, width = "w", 200
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
        faccao = self.faccao_var.get().strip()
        status = self.status_var.get().strip()

        if db and getattr(db, "ready_check", lambda: False)():
            try:
                # Ajuste o nome da tabela/colunas aqui para o seu banco real.
                # Exemplo com uma tabela hipotética "registro_acabamento":
                require_ready(["registro_acabamento"])

                sql = """
                    SELECT
                        to_char(data_registro, 'YYYY-MM-DD') AS data,
                        ordem_producao                         AS ordem,
                        codigo_modelo                          AS modelo,
                        descricao_modelo                       AS descricao,
                        faccao                                 AS faccao,
                        servico                                AS servico,
                        quantidade                             AS qtd,
                        valor_unitario                         AS valor_un,
                        (quantidade * valor_unitario)          AS total,
                        status                                 AS status
                    FROM registro_acabamento
                    WHERE data_registro BETWEEN %s AND %s
                      AND (%s = '' OR codigo_modelo ILIKE %s OR descricao_modelo ILIKE %s)
                      AND (%s = '' OR ordem_producao ILIKE %s)
                      AND (%s = '' OR faccao ILIKE %s)
                      AND (%s = 'Todos' OR status ILIKE %s)
                    ORDER BY data_registro ASC, ordem_producao ASC
                """

                params = (
                    ini,
                    fim,
                    modelo,
                    f"%{modelo}%",
                    f"%{modelo}%",
                    ordem,
                    f"%{ordem}%",
                    faccao,
                    f"%{faccao}%",
                    status,
                    f"%{status}%",
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
                        r.get("faccao", ""),
                        r.get("servico", ""),
                        qtd,
                        f"{v_un:,.2f}".replace(",", "X").replace(".", ",").replace(
                            "X", "."
                        ),
                        f"{total:,.2f}".replace(",", "X").replace(".", ",").replace(
                            "X", "."
                        ),
                        r.get("status", ""),
                    )
                    self.tree.insert("", "end", values=linha)
                    total_pecas += qtd
                    total_valor += total

            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao consultar dados:\n{e}")
                if self.logger:
                    import traceback

                    self.logger.error(
                        f"[RELATORIO] Acabamento: erro na consulta: {e}\n{traceback.format_exc()}"
                    )
        else:
            # Sem banco: dados fictícios para visual
            demo = [
                (
                    "2025-11-01",
                    "OC-001",
                    "M1234",
                    "Vestido Tubinho",
                    "Facção Alfa",
                    "Passar / Embalar",
                    120,
                    1.50,
                    "Finalizado",
                ),
                (
                    "2025-11-02",
                    "OC-002",
                    "M5678",
                    "Saia Midi",
                    "Facção Beta",
                    "Revisão",
                    80,
                    1.20,
                    "Pendente",
                ),
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
                    d[8],
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
                    f"[RELATORIO] Acabamento: erro ao exportar CSV: {e}\n{traceback.format_exc()}"
                )


# Execução direta (debug)
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Relatório de Acabamento")
    app.geometry("1050x650")
    page = RelatorioAcabamentoPage(app, sistema=None)
    page.pack(fill="both", expand=True)
    app.mainloop()
