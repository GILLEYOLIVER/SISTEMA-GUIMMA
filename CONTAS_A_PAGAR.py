# -*- coding: utf-8 -*-
"""
CONTAS_A_PAGAR.py
Página CTkinter para consolidar Contas a Pagar com base nos cortes finalizados,
cruzando com pagamentos registrados. Adere ao tema do MENU.

Usa BANCO_DE_DADOS_PG para acessar PostgreSQL.

Como usar no seu menu (padrão atual do sistema):

    from CONTAS_A_PAGAR import ContasAPagarPage

    # NOVO PADRÃO (igual ao Cadastro de Modelo, Nova Ordem, etc.)
    page = ContasAPagarPage(parent=container, sistema=self)
    page.pack(fill="both", expand=True)

    # Continua aceitando o padrão antigo para compatibilidade:
    # page = ContasAPagarPage(parent=container, host=self)
"""
import os
import json
from datetime import datetime, date, timedelta

import customtkinter as ctk
import tkinter.ttk as ttk
from tkinter import messagebox, filedialog

# ---- Conexão com PostgreSQL ----
try:
    from BANCO_DE_DADOS_PG import get_conn, get_schema
except Exception as e:
    print(f"Erro ao importar BANCO_DE_DADOS_PG: {e}")

    # Fallback simples para evitar erro de importação
    def get_conn():
        raise RuntimeError("Módulo BANCO_DE_DADOS_PG não disponível")

    def get_schema():
        return "opera"


# ---------- Helpers de data ----------
def _normalize_date_sql(col: str) -> str:
    """
    Converte colunas gravadas como 'DD/MM/YYYY' para 'YYYY-MM-DD' em runtime,
    mantendo o formato quando já estiver ISO.
    """
    return f"""
    (CASE
        WHEN {col} LIKE '__/__/____%' THEN substr({col},7,4)||'-'||substr({col},4,2)||'-'||substr({col},1,2)
        ELSE substr({col},1,10)
     END)
    """.strip()


def _dt(s: str) -> str:
    """Recebe 'AAAA-MM-DD' ou 'DD/MM/YYYY' e retorna 'YYYY-MM-DD'."""
    if not s:
        return ""
    s = s.strip()
    # já ISO
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        pass
    # tenta BR
    try:
        return datetime.strptime(s[:10], "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        return s[:10]


class ContasAPagarPage(ctk.CTkFrame):
    PAGE_TITLE = "Contas a Pagar — Cortes Finalizados"

    def __init__(
        self,
        parent,
        host=None,
        sistema=None,
        app=None,
        **kwargs,
    ):
        """
        host  -> normalmente o MENU_PRINCIPAL (antigo padrão)
        sistema/app -> mesmo objeto do MENU_PRINCIPAL (novo padrão do sistema)

        Exemplos válidos:
            ContasAPagarPage(parent=container, sistema=self)
            ContasAPagarPage(parent=container, host=self)
            ContasAPagarPage(parent=container, app=self)
        """
        super().__init__(parent, **kwargs)

        # -----------------------------
        # 1) Resolver o "sistema" / host
        # -----------------------------
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

        # -----------------------------
        # 2) Montar objeto de tema a partir do host/sistema
        #    - Se host.theme existir, usamos direto
        #    - Senão, usamos atributos cor_* do sistema
        #    - Senão, caímos em defaults
        # -----------------------------
        theme_from_host = getattr(origem, "theme", None) if origem is not None else None

        if theme_from_host is not None:
            self.theme = theme_from_host
        else:
            # usa atributos de cor se existirem, senão defaults
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

        # -----------------------------
        # 3) Aplica o fundo da página conforme o tema
        # -----------------------------
        self.configure(fg_color=self.theme.cor_fundo)

        # -----------------------------
        # 4) Constrói UI e faz primeira busca
        # -----------------------------
        self._build_ui()
        self._search()

    # ============================ UI ============================
    def _build_ui(self):
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Título
        top = ctk.CTkFrame(self, corner_radius=0, fg_color=self.theme.cor_fundo)
        top.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            top,
            text=self.PAGE_TITLE,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.theme.cor_texto,
        ).grid(row=0, column=0, padx=16, pady=10, sticky="w")

        # Filtros
        filt = ctk.CTkFrame(self, fg_color=self.theme.cor_secundaria)
        filt.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 4))
        for i in range(12):
            filt.grid_columnconfigure(i, weight=0)
        filt.grid_columnconfigure(11, weight=1)

        def _first_day(d: date):
            return d.replace(day=1)

        def _last_day(d: date):
            nd = d.replace(day=28) + timedelta(days=4)
            return nd - timedelta(days=nd.day)

        hoje = date.today()
        self.ini_var = ctk.StringVar(value=_first_day(hoje).strftime("%Y-%m-%d"))
        self.fim_var = ctk.StringVar(value=_last_day(hoje).strftime("%Y-%m-%d"))
        self.busca_var = ctk.StringVar(value="")
        self.status_var = ctk.StringVar(value="Finalizado")
        self.por_pagamento_periodo = ctk.BooleanVar(value=True)

        label_kwargs = {"text_color": self.theme.cor_texto}
        entry_kwargs = {
            "fg_color": self.theme.cor_terciaria,
            "border_color": self.theme.cor_borda,
            "text_color": self.theme.cor_texto,
        }

        ctk.CTkLabel(filt, text="De:", **label_kwargs).grid(
            row=0, column=0, padx=(8, 4), pady=8, sticky="e"
        )
        ctk.CTkEntry(filt, width=120, textvariable=self.ini_var, **entry_kwargs).grid(
            row=0, column=1, padx=4, pady=8
        )

        ctk.CTkLabel(filt, text="Até:", **label_kwargs).grid(
            row=0, column=2, padx=(8, 4), pady=8, sticky="e"
        )
        ctk.CTkEntry(filt, width=120, textvariable=self.fim_var, **entry_kwargs).grid(
            row=0, column=3, padx=4, pady=8
        )

        ctk.CTkLabel(filt, text="Status:", **label_kwargs).grid(
            row=0, column=4, padx=(8, 4), pady=8, sticky="e"
        )
        self.cmb_status = ctk.CTkComboBox(
            filt,
            values=["Todos", "Finalizado", "Pendente", "Em Progresso"],
            variable=self.status_var,
            width=140,
            state="readonly",
            fg_color=self.theme.cor_terciaria,
            border_color=self.theme.cor_borda,
            button_color=self.theme.cor_primaria,
            button_hover_color=self.theme.cor_hover,
            text_color=self.theme.cor_texto,
        )
        self.cmb_status.grid(row=0, column=5, padx=4, pady=8)

        ctk.CTkLabel(
            filt,
            text="Buscar (código/descrição/costureira):",
            **label_kwargs,
        ).grid(row=0, column=6, padx=(8, 4), pady=8, sticky="e")

        ent = ctk.CTkEntry(filt, width=260, textvariable=self.busca_var, **entry_kwargs)
        ent.grid(row=0, column=7, padx=4, pady=8)
        ent.bind("<Return>", lambda e: self._search())

        ctk.CTkCheckBox(
            filt,
            text="Considerar apenas pagamentos do período",
            variable=self.por_pagamento_periodo,
            fg_color=self.theme.cor_primaria,
            border_color=self.theme.cor_borda,
            hover_color=self.theme.cor_hover,
            text_color=self.theme.cor_texto,
        ).grid(row=0, column=8, padx=(10, 4), pady=8, sticky="w")

        ctk.CTkButton(
            filt,
            text="🔍 Buscar",
            width=120,
            command=self._search,
            fg_color=self.theme.cor_destaque,
            hover_color=self.theme.cor_hover,
            text_color="white",
        ).grid(row=0, column=11, padx=8, pady=8, sticky="e")

        # KPIs
        kpis = ctk.CTkFrame(self, fg_color=self.theme.cor_terciaria)
        kpis.grid(row=2, column=0, sticky="ew", padx=8, pady=(2, 8))
        for i in range(8):
            kpis.grid_columnconfigure(i, weight=1)

        def _card(col, label):
            box = ctk.CTkFrame(
                kpis,
                corner_radius=10,
                fg_color=self.theme.cor_secundaria,
            )
            box.grid(row=0, column=col, padx=6, pady=6, sticky="ew")
            ctk.CTkLabel(
                box,
                text=label,
                font=ctk.CTkFont(size=12),
                text_color=self.theme.cor_texto,
            ).pack(anchor="w", padx=8, pady=(8, 0))
            v = ctk.CTkLabel(
                box,
                text="0",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=self.theme.cor_destaque,
            )
            v.pack(anchor="w", padx=8, pady=(0, 8))
            return v

        self.kpi_base = _card(0, "Base (R$)")
        self.kpi_pago = _card(1, "Pago (R$)")
        self.kpi_saldo = _card(2, "Saldo a Pagar (R$)")
        self.kpi_cortes = _card(3, "Qtd Cortes")
        self.kpi_costs = _card(4, "Qtd Costureiras")
        self.kpi_media = _card(5, "Média por Corte (R$)")

        # Abas
        tabs = ctk.CTkTabview(self, fg_color=self.theme.cor_secundaria)
        tabs.grid(row=3, column=0, sticky="nsew", padx=8, pady=8)
        self.tab_lan = tabs.add("Lançamentos")
        self.tab_res = tabs.add("Resumo por Costureira")
        self.tab_rel = tabs.add("Relatório")

        # Tabelas
        self._build_table(self.tab_lan, "lan")
        self._build_table(self.tab_res, "res")

        # Relatório/Export
        box_rel = ctk.CTkFrame(self.tab_rel, fg_color=self.theme.cor_secundaria)
        box_rel.grid(row=0, column=0, sticky="nw", padx=10, pady=10)
        ctk.CTkButton(
            box_rel,
            text="📤 Exportar CSV (Lançamentos)",
            command=self._export_csv,
            fg_color=self.theme.cor_primaria,
            hover_color=self.theme.cor_hover,
            text_color="white",
        ).grid(row=0, column=0, padx=6, pady=6)
        ctk.CTkButton(
            box_rel,
            text="🖨️ Relatório HTML",
            command=self._report_html,
            fg_color=self.theme.cor_destaque,
            hover_color=self.theme.cor_hover,
            text_color="white",
        ).grid(row=0, column=1, padx=6, pady=6)

    def _build_table(self, parent, key):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        wrap = ctk.CTkFrame(parent, fg_color=self.theme.cor_terciaria)
        wrap.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure(
            "Contas.Treeview",
            background=self.theme.cor_terciaria,
            fieldbackground=self.theme.cor_terciaria,
            foreground=self.theme.cor_texto,
            rowheight=22,
        )
        style.map(
            "Contas.Treeview",
            background=[("selected", self.theme.cor_destaque)],
        )

        if key == "lan":
            cols = ("data", "codigo", "descricao", "costureira", "boas",
                    "valor_peca", "base", "pago", "saldo", "obs")
            headers = ["DATA", "CÓDIGO", "DESCRIÇÃO", "COSTUREIRA", "BOAS",
                       "VALOR PEÇA", "BASE", "PAGO", "SALDO", "OBS"]
            widths = [110, 120, 260, 160, 90, 110, 120, 120, 120, 260]
            anchors = ["center", "center", "w", "w", "center", "e", "e", "e", "e", "w"]
            self.cols_lan = cols
            self.tree_lan = ttk.Treeview(
                wrap,
                columns=cols,
                show="headings",
                height=20,
                style="Contas.Treeview",
            )
            for c, h, w, a in zip(cols, headers, widths, anchors):
                self.tree_lan.heading(c, text=h)
                self.tree_lan.column(
                    c,
                    width=w,
                    anchor=a,
                    stretch=True if c in ("descricao", "obs") else False,
                )
            self.tree_lan.grid(row=0, column=0, sticky="nsew")
            vs = ttk.Scrollbar(wrap, orient="vertical", command=self.tree_lan.yview)
            hs = ttk.Scrollbar(wrap, orient="horizontal", command=self.tree_lan.xview)
            self.tree_lan.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
            vs.grid(row=0, column=1, sticky="ns")
            hs.grid(row=1, column=0, sticky="ew")

        elif key == "res":
            cols = ("costureira", "cortes", "boas", "base", "pago", "saldo")
            headers = ["COSTUREIRA", "CORTES", "BOAS", "BASE (R$)", "PAGO (R$)", "SALDO (R$)"]
            widths = [200, 90, 100, 120, 120, 120]
            anchors = ["w", "center", "center", "e", "e", "e"]
            self.cols_res = cols
            self.tree_res = ttk.Treeview(
                wrap,
                columns=cols,
                show="headings",
                height=20,
                style="Contas.Treeview",
            )
            for c, h, w, a in zip(cols, headers, widths, anchors):
                self.tree_res.heading(c, text=h)
                self.tree_res.column(c, width=w, anchor=a, stretch=False)
            self.tree_res.grid(row=0, column=0, sticky="nsew")
            vs = ttk.Scrollbar(wrap, orient="vertical", command=self.tree_res.yview)
            self.tree_res.configure(yscrollcommand=vs.set)
            vs.grid(row=0, column=1, sticky="ns")

    # ============================ BUSCA ============================
    def _search(self):
        """
        Busca os cortes_finalizados no período e monta:
          - Lançamentos (linha a linha dos cortes)
          - Resumo por costureira
          - KPIs
        """
        ini = _dt(self.ini_var.get())
        fim = _dt(self.fim_var.get())
        termo = (self.busca_var.get() or "").strip()
        status = self.status_var.get()
        only_period_pay = self.por_pagamento_periodo.get()

        try:
            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()
            cur.execute(f"SET search_path TO {schema}, public")

            # 1) Verificar se a tabela cortes_finalizados existe
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = 'cortes_finalizados'
                )
            """, (schema,))
            if not cur.fetchone()[0]:
                messagebox.showwarning(
                    "Aviso",
                    "Tabela 'cortes_finalizados' não encontrada no banco de dados.",
                )
                conn.close()
                return

            # 2) Descobrir colunas qtd_* existentes
            possiveis = ["qtd_pp", "qtd_p", "qtd_m", "qtd_g", "qtd_gg", "qtd_g1", "qtd_g2", "qtd_g3"]
            in_list = ",".join("'" + c + "'" for c in possiveis)
            cur.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = 'cortes_finalizados'
                  AND column_name IN ({in_list})
            """, (schema,))
            existentes = {row[0] for row in cur.fetchall()}
            tamanhos = [c for c in possiveis if c in existentes]
            boas_expr = " + ".join([f"COALESCE(c.{c},0)" for c in tamanhos]) if tamanhos else "0"

            # 3) Montar consulta principal
            sql_cf = f"""
                SELECT
                  c.data_chegada::date         AS data,
                  COALESCE(c.codigo, '')       AS codigo,
                  COALESCE(c.descricao, '')    AS descricao,
                  COALESCE(c.costureira, '')   AS costureira,
                  COALESCE(c.valor_peca, 0)    AS valor_peca,
                  ({boas_expr})                AS boas,
                  COALESCE(c.observacao, '')   AS obs,
                  COALESCE(c.status, '')       AS status
                FROM {schema}.cortes_finalizados c
                WHERE c.data_chegada::date BETWEEN %s AND %s
            """
            params = [ini, fim]

            if status and status != "Todos":
                sql_cf += " AND c.status ILIKE %s"
                params.append(f"%{status}%")

            if termo:
                sql_cf += " AND (c.codigo ILIKE %s OR c.descricao ILIKE %s OR c.costureira ILIKE %s)"
                like = f"%{termo}%"
                params.extend([like, like, like])

            sql_cf += " ORDER BY c.data_chegada::date ASC"

            cur.execute(sql_cf, tuple(params))
            cf_rows = cur.fetchall()

            # 4) Verificar se a tabela pagamento_corte_acabamento existe
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = 'pagamento_corte_acabamento'
                )
            """, (schema,))
            pagamentos_existem = cur.fetchone()[0]
            pag_rows = []

            if pagamentos_existem:
                sql_pag = f"""
                    SELECT p.codigo, p.costureira, SUM(COALESCE(p.total_pago,0)) AS pago
                    FROM {schema}.pagamento_corte_acabamento p
                    WHERE COALESCE(p.estornado, FALSE) = FALSE
                """
                pag_params = []
                if only_period_pay:
                    sql_pag += " AND p.data_pagamento::date BETWEEN %s AND %s"
                    pag_params.extend([ini, fim])

                sql_pag += " GROUP BY p.codigo, p.costureira"
                cur.execute(sql_pag, tuple(pag_params))
                pag_rows = cur.fetchall()

        except Exception as e:
            messagebox.showerror("Erro SQL", f"Erro ao executar consulta: {e}")
            import traceback
            print(traceback.format_exc())
            try:
                conn.close()
            except Exception:
                pass
            return
        finally:
            try:
                conn.close()
            except Exception:
                pass

        # 6) Montar mapa de pagamentos
        pagos = {}
        for row in pag_rows:
            if len(row) >= 3:
                codigo = row[0] or ""
                costureira = row[1] or ""
                pago = float(row[2] or 0.0)
                pagos[(codigo, costureira)] = pago

        # 7) Montagem das linhas
        lanc = []
        resumo = {}
        total_base = 0.0
        total_pago = 0.0

        for row in cf_rows:
            if len(row) < 8:
                continue

            data = row[0] or ""
            codigo = row[1] or ""
            descricao = row[2] or ""
            costureira = row[3] or ""
            valor_peca = float(row[4] or 0.0)
            boas = int(row[5] or 0)
            obs = row[6] or ""

            base = valor_peca * boas
            pago = pagos.get((codigo, costureira), 0.0)
            saldo = base - pago

            lanc.append({
                "data": data,
                "codigo": codigo,
                "descricao": descricao,
                "costureira": costureira,
                "boas": boas,
                "valor_peca": f"{valor_peca:.2f}",
                "base": f"{base:.2f}",
                "pago": f"{pago:.2f}",
                "saldo": f"{saldo:.2f}",
                "obs": obs,
            })

            total_base += base
            total_pago += pago

            d = resumo.setdefault(costureira, {
                "costureira": costureira,
                "cortes": 0,
                "boas": 0,
                "base": 0.0,
                "pago": 0.0,
                "saldo": 0.0,
            })
            d["cortes"] += 1
            d["boas"] += boas
            d["base"] += base
            d["pago"] += pago
            d["saldo"] = d["base"] - d["pago"]

        # 8) Preencher Treeviews
        def fill(tree: ttk.Treeview, rows, cols):
            tree.delete(*tree.get_children())
            for it in rows:
                tree.insert("", "end", values=[it.get(c, "") for c in cols])

        fill(self.tree_lan, lanc, self.cols_lan)

        res_rows = list(resumo.values())
        res_rows.sort(key=lambda x: x["saldo"], reverse=True)

        res_rows_fmt = []
        for r in res_rows:
            res_rows_fmt.append({
                "costureira": r["costureira"],
                "cortes": r["cortes"],
                "boas": r["boas"],
                "base": f"{r['base']:.2f}",
                "pago": f"{r['pago']:.2f}",
                "saldo": f"{r['saldo']:.2f}",
            })

        fill(self.tree_res, res_rows_fmt, self.cols_res)

        # 9) KPIs
        self.kpi_base.configure(text=f"R$ {total_base:,.2f}")
        self.kpi_pago.configure(text=f"R$ {total_pago:,.2f}")
        self.kpi_saldo.configure(text=f"R$ {(total_base - total_pago):,.2f}")
        self.kpi_cortes.configure(text=f"{len(cf_rows)}")
        self.kpi_costs.configure(text=f"{len(res_rows)}")
        self.kpi_media.configure(
            text=f"R$ {(total_base / len(cf_rows)) if cf_rows else 0:,.2f}"
        )

        # 10) Cache
        self._cache = dict(
            lancamentos=lanc,
            resumo=res_rows,
            filtros=dict(
                ini=ini,
                fim=fim,
                termo=termo,
                status=status,
                only_period_pay=only_period_pay,
            ),
        )

    # ============================ EXPORT/RELATÓRIO ============================
    def _export_csv(self):
        if not getattr(self, "_cache", None):
            messagebox.showinfo("Exportar", "Busque primeiro.")
            return
        fp = filedialog.asksaveasfilename(
            title="Salvar CSV - Lançamentos",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not fp:
            return
        import csv
        with open(fp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(
                [
                    "DATA",
                    "CÓDIGO",
                    "DESCRIÇÃO",
                    "COSTUREIRA",
                    "BOAS",
                    "VALOR_PEÇA",
                    "BASE",
                    "PAGO",
                    "SALDO",
                    "OBS",
                ]
            )
            for r in self._cache["lancamentos"]:
                w.writerow([
                    r["data"],
                    r["codigo"],
                    r["descricao"],
                    r["costureira"],
                    r["boas"],
                    r["valor_peca"],
                    r["base"],
                    r["pago"],
                    r["saldo"],
                    r["obs"],
                ])
        messagebox.showinfo("Exportar", f"Arquivo salvo em:\n{fp}")

    def _report_html(self):
        if not getattr(self, "_cache", None):
            messagebox.showinfo("Relatório", "Busque primeiro.")
            return
        from tempfile import gettempdir

        filtros = self._cache["filtros"]
        ini, fim = filtros["ini"], filtros["fim"]
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        out = os.path.join(gettempdir(), f"contas_a_pagar_{ini}_a_{fim}.html")

        css = f"""
        <style>
          :root {{
            --bg: {self.theme.cor_fundo};
            --bg2: {self.theme.cor_terciaria};
            --fg: {self.theme.cor_texto};
            --pri: {self.theme.cor_primaria};
            --acc: {self.theme.cor_destaque};
            --brd: {self.theme.cor_borda};
          }}
          @page {{ size: A4; margin: 14mm; }}
          body {{ background: var(--bg); color: var(--fg); font: 12px/1.5 "Segoe UI", Arial, Helvetica, sans-serif; }}
          header {{ display:flex; align-items:center; padding:10px 12px; background:var(--pri); color:#fff; border-bottom:2px solid var(--acc); }}
          header .t {{ font-weight:700; font-size:18px; }}
          header .m {{ margin-left:auto; opacity:.9 }}
          h2 {{ margin:16px 0 8px; border-bottom:1px solid var(--brd); padding-bottom:6px; }}
          .kpis {{ display:flex; gap:10px; flex-wrap:wrap; margin:8px 0 14px; }}
          .card {{ background:var(--bg2); border:1px solid var(--brd); border-radius:10px; padding:10px 12px; min-width:180px; }}
          .card .l {{ font-size:12px; opacity:.85; }}
          .card .v {{ font-size:20px; font-weight:700; }}
          table {{ width:100%; border-collapse:collapse; margin:8px 0 16px; }}
          thead th {{ position:sticky; top:0; background:var(--pri); color:#fff; padding:8px; text-align:left; }}
          td, th {{ border:1px solid var(--brd); padding:7px 8px; }}
          tbody tr:nth-child(even) td {{ background:rgba(255,255,255,.04); }}
          td.num {{ text-align:right; }}
          .muted {{ opacity:.85 }}
        </style>
        """

        def tbl(rows, cols, headers):
            if not rows:
                return "<div class='muted'>Sem dados no período.</div>"
            th = "".join(f"<th>{h}</th>" for h in headers)
            body = []
            for r in rows:
                tds = []
                for k in cols:
                    v = r.get(k, "")
                    cls = "num" if (k in ("boas", "base", "pago", "saldo", "valor_peca")) else ""
                    tds.append(f"<td class='{cls}'>{v}</td>")
                body.append("<tr>" + "".join(tds) + "</tr>")
            return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(body)}</tbody></table>"

        lan = self._cache["lancamentos"]
        res = self._cache["resumo"]
        total_base = sum(float(x["base"]) for x in lan) if lan else 0.0
        total_pago = sum(float(x["pago"]) for x in lan) if lan else 0.0
        total_saldo = sum(float(x["saldo"]) for x in lan) if lan else 0.0

        html = f"""<!doctype html>
<html><head><meta charset='utf-8'>{css}</head>
<body>
<header><div class='t'>Contas a Pagar — Cortes Finalizados</div><div class='m'>Gerado em {now}</div></header>
<div class='wrap'>
  <div class='kpis'>
    <div class='card'><div class='l'>Base</div><div class='v'>R$ {total_base:,.2f}</div></div>
    <div class='card'><div class='l'>Pago</div><div class='v'>R$ {total_pago:,.2f}</div></div>
    <div class='card'><div class='l'>Saldo</div><div class='v'>R$ {total_saldo:,.2f}</div></div>
    <div class='card'><div class='l'>Período</div><div class='v'>{ini} a {fim}</div></div>
  </div>

  <h2>Lançamentos</h2>
  {tbl(lan, ["data", "codigo", "descricao", "costureira", "boas", "valor_peca", "base", "pago", "saldo", "obs"],
       ["Data", "Código", "Descrição", "Costureira", "Boas", "V.Peça", "Base", "Pago", "Saldo", "Obs"])}

  <h2>Resumo por Costureira</h2>
  {tbl([
            {"costureira": r["costureira"], "cortes": r["cortes"], "boas": r["boas"],
              "base": f"{r['base']:.2f}", "pago": f"{r['pago']:.2f}", "saldo": f"{r['saldo']:.2f}"} for r in res
        ],
            ["costureira", "cortes", "boas", "base", "pago", "saldo"],
            ["Costureira", "Cortes", "Boas", "Base (R$)", "Pago (R$)", "Saldo (R$)"])
        }

  <p class='muted'>* Base = peças boas x valor peça. Pagamentos considerados {('no período' if self._cache['filtros']['only_period_pay'] else 'em todo o histórico')}.</p>
</div>
<script>setTimeout(function(){{window.print();}}, 400);</script>
</body></html>"""

        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        try:
            os.startfile(out)  # Windows
        except Exception:
            import webbrowser
            webbrowser.open_new_tab("file://" + out)
        messagebox.showinfo("Relatório", f"Relatório gerado:\n{out}")

    # tema adicional se quiser ajustar algo depois
    def aplicar_tema(self):
        pass


# Execução isolada para teste rápido
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.geometry("1200x720")
    app = ContasAPagarPage(root)
    app.pack(fill="both", expand=True)
    root.mainloop()

