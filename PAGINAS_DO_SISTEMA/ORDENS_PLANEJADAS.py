# -*- coding: utf-8 -*-
from tkinter import ttk, messagebox
import customtkinter as ctk

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready


class OrdensPlanejadasPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.ops_index = {}
        self.configure(fg_color=getattr(sistema, "cor_fundo", "#F5F5F5"))
        self._build()
        self._carregar_ops()

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Ordens Planejadas", font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        box = ctk.CTkFrame(self)
        box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        box.grid_rowconfigure(1, weight=1)
        box.grid_columnconfigure(0, weight=1)

        barra = ctk.CTkFrame(box, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkButton(barra, text="Atualizar", command=self._carregar_ops).pack(side="left", padx=(0, 8))
        ctk.CTkButton(barra, text="Abrir na Nova Ordem", command=self._abrir_na_nova_ordem).pack(side="left")

        self.tree = ttk.Treeview(box, columns=("op", "modelo", "qtd", "inicio", "fim", "status", "progresso"), show="headings", height=18)
        for col, txt, w in (
            ("op", "OP", 120),
            ("modelo", "Modelo", 260),
            ("qtd", "Qtde", 90),
            ("inicio", "Início", 100),
            ("fim", "Fim", 100),
            ("status", "Status", 120),
            ("progresso", "Progresso", 90),
        ):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="center")
        self.tree.column("modelo", anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        sc = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sc.set)
        sc.grid(row=1, column=1, sticky="ns", pady=(0, 10))
        self.tree.bind("<Double-1>", lambda _e: self._abrir_na_nova_ordem())

    def on_page_open(self):
        self._carregar_ops()

    def _db_ready(self):
        ok, msg = require_ready()
        if not ok:
            messagebox.showerror("Ordens Planejadas", msg)
        return ok

    def _fmt_data(self, d):
        if not d:
            return ""
        try:
            return d.strftime("%d/%m/%Y")
        except Exception:
            return str(d)

    @staticmethod
    def _calcular_percentuais_grade(grade_rows, quantidade_total):
        """Usa somente o percentual salvo no Planejamento (sem recalcular)."""
        tamanhos = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]
        percentuais = {tam: 0.0 for tam in tamanhos}
        for tamanho, qtd, pct_salvo in (grade_rows or []):
            tam = str(tamanho or "").strip().upper()
            if tam not in percentuais:
                continue
            if pct_salvo is not None:
                percentuais[tam] = float(pct_salvo or 0)
        return percentuais

    def _carregar_ops(self):
        if not self._db_ready():
            return
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.ops_index = {}
        schema = get_schema()
        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT id, op, COALESCE(descricao_modelo, modelo, codigo_modelo, ''),
                           COALESCE(quantidade, total_grade, 0),
                           COALESCE(prazo_inicio, inicio),
                           COALESCE(periodo_fim, fim),
                           COALESCE(status, 'Planejada'),
                           COALESCE(percentual_progresso, 0),
                           COALESCE(codigo_modelo, ''),
                           COALESCE(prioridade, 'Média')
                      FROM {schema}.planejamento_ops
                     ORDER BY COALESCE(prazo_inicio, inicio, CURRENT_DATE), op
                    """
                )
                for row in cur.fetchall():
                    pid, op, modelo, qtd, inicio, fim, status, progresso, codigo, prioridade = row
                    cur.execute(
                        f"""
                        SELECT COALESCE(tamanho, ''), COALESCE(quantidade, 0), percentual
                          FROM {schema}.planejamento_op_grade
                         WHERE planejamento_id = %s
                        """,
                        (pid,),
                    )
                    grade_rows = cur.fetchall()
                    grade_percentuais = self._calcular_percentuais_grade(grade_rows, qtd)
                    self.ops_index[op] = {
                        "planejamento_id": pid,
                        "op": op,
                        "codigo_modelo": codigo,
                        "descricao_modelo": modelo,
                        "quantidade": int(qtd or 0),
                        "data_final": self._fmt_data(fim),
                        "status": status,
                        "prioridade": prioridade,
                        "grade_percentuais": grade_percentuais,
                    }
                    self.tree.insert("", "end", values=(op, modelo, qtd, self._fmt_data(inicio), self._fmt_data(fim), status, f"{float(progresso or 0):.0f}%"))
        except Exception as exc:
            messagebox.showerror("Ordens Planejadas", f"Erro ao carregar OPs: {exc}")

    def _abrir_na_nova_ordem(self):
        item = self.tree.focus()
        if not item:
            messagebox.showwarning("Ordens Planejadas", "Selecione uma OP para abrir na Nova Ordem.")
            return
        op = str(self.tree.item(item).get("values", [""])[0])
        dados = self.ops_index.get(op)
        if not dados:
            return
        if self.sistema and hasattr(self.sistema, "open_page"):
            self.sistema._ordem_planejada_prefill = dados
            self.sistema.open_page("Nova Ordem")
