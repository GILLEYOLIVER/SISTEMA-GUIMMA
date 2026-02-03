# -*- coding: utf-8 -*-
"""
CONTAS_A_PAGAR.py - VERSÃO COMPLETA
Busca cortes de múltiplas tabelas conforme o status
"""
import TEMAS
import os
from datetime import datetime, date, timedelta

import customtkinter as ctk
import tkinter.ttk as ttk
from tkinter import messagebox, filedialog

try:
    from BANCO_DE_DADOS_PG import get_conn, get_schema
except Exception as e:
    print(f"Erro ao importar BANCO_DE_DADOS_PG: {e}")
    def get_conn():
        raise RuntimeError("Módulo BANCO_DE_DADOS_PG não disponível")
    def get_schema():
        return "opera"


def _dt(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except:
        pass
    try:
        return datetime.strptime(s[:10], "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return s[:10]


class ContasAPagarPage(ctk.CTkFrame):
    PAGE_TITLE = "Contas a Pagar — Controle Completo"

    def __init__(self, parent, host=None, sistema=None, app=None, **kwargs):
        super().__init__(parent, **kwargs)

        sistema_kw = sistema or app
        if host is None:
            host = sistema_kw or kwargs.get("sistema") or kwargs.get("app")
        self.host = host
        origem = host or sistema_kw

        theme_from_host = getattr(origem, "theme", None) if origem else None
        if theme_from_host:
            self.theme = theme_from_host
        else:
            cf = getattr(origem, "cor_fundo", "#0f1720") if origem else "#0f1720"
            cp = getattr(origem, "cor_primaria", "#1f2937") if origem else "#1f2937"
            cs = getattr(origem, "cor_secundaria", "#111827") if origem else "#111827"
            ct = getattr(origem, "cor_texto", "#e5e7eb") if origem else "#e5e7eb"
            ct3 = getattr(origem, "cor_terciaria", "#0b1220") if origem else "#0b1220"
            cd = getattr(origem, "cor_destaque", "#2563eb") if origem else "#2563eb"
            ch = getattr(origem, "cor_hover", "#334155") if origem else "#334155"
            cb = getattr(origem, "cor_borda", "#273244") if origem else "#273244"
            self.theme = type("T", (), {
                "cor_fundo": cf, "cor_primaria": cp, "cor_secundaria": cs,
                "cor_terciaria": ct3, "cor_texto": ct, "cor_destaque": cd,
                "cor_hover": ch, "cor_borda": cb,
            })()

        self.configure(fg_color=self.theme.cor_fundo)
        self._build_ui()
        self._search()

    def _build_ui(self):
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, corner_radius=0, fg_color=self.theme.cor_fundo)
        top.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(top, text=self.PAGE_TITLE, font=ctk.CTkFont(size=16, weight="bold"), text_color=self.theme.cor_texto).grid(row=0, column=0, padx=16, pady=10, sticky="w")

        filt = ctk.CTkFrame(self, fg_color=self.theme.cor_secundaria)
        filt.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 4))
        for i in range(12):
            filt.grid_columnconfigure(i, weight=0)
        filt.grid_columnconfigure(11, weight=1)

        hoje = date.today()
        self.ini_var = ctk.StringVar(value=hoje.replace(day=1).strftime("%Y-%m-%d"))
        nd = hoje.replace(day=28) + timedelta(days=4)
        self.fim_var = ctk.StringVar(value=(nd - timedelta(days=nd.day)).strftime("%Y-%m-%d"))
        self.busca_var = ctk.StringVar(value="")
        self.status_var = ctk.StringVar(value="Todos")
        self.por_pagamento_periodo = ctk.BooleanVar(value=False)

        lbl = {"text_color": self.theme.cor_texto}
        ent = {"fg_color": self.theme.cor_terciaria, "border_color": self.theme.cor_borda, "text_color": self.theme.cor_texto}

        ctk.CTkLabel(filt, text="De:", **lbl).grid(row=0, column=0, padx=(8,4), pady=8)
        ctk.CTkEntry(filt, width=120, textvariable=self.ini_var, **ent).grid(row=0, column=1, padx=4, pady=8)
        ctk.CTkLabel(filt, text="Até:", **lbl).grid(row=0, column=2, padx=(8,4), pady=8)
        ctk.CTkEntry(filt, width=120, textvariable=self.fim_var, **ent).grid(row=0, column=3, padx=4, pady=8)
        ctk.CTkLabel(filt, text="Status:", **lbl).grid(row=0, column=4, padx=(8,4), pady=8)
        ctk.CTkComboBox(filt, values=["Todos", "Enviado", "Em Progresso", "Pendente", "Finalizado"], variable=self.status_var, width=140, state="readonly", fg_color=self.theme.cor_terciaria, border_color=self.theme.cor_borda, text_color=self.theme.cor_texto).grid(row=0, column=5, padx=4, pady=8)
        ctk.CTkLabel(filt, text="Buscar:", **lbl).grid(row=0, column=6, padx=(8,4), pady=8)
        e = ctk.CTkEntry(filt, width=200, textvariable=self.busca_var, **ent)
        e.grid(row=0, column=7, padx=4, pady=8)
        e.bind("<Return>", lambda ev: self._search())
        ctk.CTkCheckBox(filt, text="Apenas pag. do período", variable=self.por_pagamento_periodo, fg_color=self.theme.cor_primaria, text_color=self.theme.cor_texto).grid(row=0, column=8, padx=8, pady=8)
        ctk.CTkButton(filt, text="Buscar", width=100, command=self._search, fg_color=self.theme.cor_destaque, text_color="white").grid(row=0, column=11, padx=8, pady=8, sticky="e")

        kpis = ctk.CTkFrame(self, fg_color=self.theme.cor_terciaria)
        kpis.grid(row=2, column=0, sticky="ew", padx=8, pady=(2,8))
        for i in range(6): kpis.grid_columnconfigure(i, weight=1)

        def card(col, txt):
            b = ctk.CTkFrame(kpis, corner_radius=10, fg_color=self.theme.cor_secundaria)
            b.grid(row=0, column=col, padx=6, pady=6, sticky="ew")
            ctk.CTkLabel(b, text=txt, font=ctk.CTkFont(size=12), text_color=self.theme.cor_texto).pack(anchor="w", padx=8, pady=(8,0))
            v = ctk.CTkLabel(b, text="0", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.theme.cor_destaque)
            v.pack(anchor="w", padx=8, pady=(0,8))
            return v

        self.kpi_base = card(0, "Base (R$)")
        self.kpi_pago = card(1, "Pago (R$)")
        self.kpi_saldo = card(2, "Saldo a Pagar (R$)")
        self.kpi_cortes = card(3, "Qtd Cortes")
        self.kpi_costs = card(4, "Qtd Costureiras")
        self.kpi_media = card(5, "Média por Corte (R$)")

        tabs = ctk.CTkTabview(self, fg_color=self.theme.cor_secundaria)
        tabs.grid(row=3, column=0, sticky="nsew", padx=8, pady=8)
        self.tab_lan = tabs.add("Lançamentos")
        self.tab_res = tabs.add("Resumo por Costureira")
        self._build_table(self.tab_lan, "lan")
        self._build_table(self.tab_res, "res")

    def _build_table(self, parent, key):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        wrap = ctk.CTkFrame(parent, fg_color=self.theme.cor_terciaria)
        wrap.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Contas.Treeview", background=self.theme.cor_terciaria,
                        fieldbackground=self.theme.cor_terciaria, foreground=self.theme.cor_texto, rowheight=22)

        if key == "lan":
            cols = (
            "status", "data", "codigo", "descricao", "costureira", "boas", "valor_peca", "base", "pago", "saldo")
            hdrs = ["STATUS", "DATA", "CÓDIGO", "DESCRIÇÃO", "COSTUREIRA", "BOAS", "VLR PEÇA", "BASE", "PAGO", "SALDO"]
            wdts = [100, 90, 100, 200, 140, 70, 80, 100, 100, 100]
            self.cols_lan = cols
            self.tree_lan = ttk.Treeview(wrap, columns=cols, show="headings", height=20, style="Contas.Treeview")
            for c, h, w in zip(cols, hdrs, wdts):
                self.tree_lan.heading(c, text=h, anchor="center")
                self.tree_lan.column(c, width=w, anchor="center")
            self.tree_lan.grid(row=0, column=0, sticky="nsew")
            vs = ttk.Scrollbar(wrap, orient="vertical", command=self.tree_lan.yview)
            vs.grid(row=0, column=1, sticky="ns")
            self.tree_lan.configure(yscrollcommand=vs.set)
        else:
            cols = ("costureira", "cortes", "boas", "base", "pago", "saldo")
            hdrs = ["COSTUREIRA", "CORTES", "BOAS", "BASE (R$)", "PAGO (R$)", "SALDO (R$)"]
            wdts = [180, 80, 80, 110, 110, 110]
            self.cols_res = cols
            self.tree_res = ttk.Treeview(wrap, columns=cols, show="headings", height=20, style="Contas.Treeview")
            for c, h, w in zip(cols, hdrs, wdts):
                self.tree_res.heading(c, text=h, anchor="center")
                self.tree_res.column(c, width=w, anchor="center")
            self.tree_res.grid(row=0, column=0, sticky="nsew")
            vs = ttk.Scrollbar(wrap, orient="vertical", command=self.tree_res.yview)
            vs.grid(row=0, column=1, sticky="ns")
            self.tree_res.configure(yscrollcommand=vs.set)

    def _search(self):
        ini = _dt(self.ini_var.get())
        fim = _dt(self.fim_var.get())
        termo = (self.busca_var.get() or "").strip()
        status_filtro = self.status_var.get()
        only_period = self.por_pagamento_periodo.get()

        try:
            conn = get_conn()
            cur = conn.cursor()
            schema = get_schema()
            cur.execute(f"SET search_path TO {schema}, public")

            all_rows = []

            # =====================================================
            # 1) ENVIADO - Cortes na facção (envios_cortes sem retorno)
            # =====================================================
            if status_filtro in ("Todos", "Enviado"):
                sql_enviado = f"""
                    SELECT 
                        'Enviado' AS status_calc,
                        e.data_envio::date AS data,
                        COALESCE(e.codigo_corte, '') AS codigo,
                        COALESCE(e.descricao_corte, '') AS descricao,
                        COALESCE(f.nome, 'N/A') AS costureira,
                        COALESCE(e.total_pecas, 0) AS boas,
                        COALESCE(e.valor_total_envio / NULLIF(e.total_pecas, 0), 0) AS valor_peca,
                        COALESCE(e.valor_total_envio, 0) AS base,
                        0 AS pago,
                        NULL::date AS data_pagamento
                    FROM {schema}.envios_cortes e
                    LEFT JOIN {schema}.cadastro_faccoes f ON e.prestador_id = f.id
                    LEFT JOIN {schema}.controle_retorno_cortes r ON r.envio_id = e.id
                    WHERE e.data_envio::date BETWEEN %s AND %s
                      AND r.id IS NULL
                      AND e.status_envio = 'Enviado'
                """
                params_env = [ini, fim]
                if termo:
                    sql_enviado += " AND (e.codigo_corte ILIKE %s OR e.descricao_corte ILIKE %s OR f.nome ILIKE %s)"
                    lk = f"%{termo}%"
                    params_env.extend([lk, lk, lk])
                cur.execute(sql_enviado, tuple(params_env))
                all_rows.extend(cur.fetchall())

            # =====================================================
            # 2) EM PROGRESSO - Retornados mas não finalizados (em conferência)
            # =====================================================
            if status_filtro in ("Todos", "Em Progresso"):
                sql_progresso = f"""
                    SELECT 
                        'Em Progresso' AS status_calc,
                        r.data_chegada::date AS data,
                        COALESCE(e.codigo_corte, '') AS codigo,
                        COALESCE(e.descricao_corte, '') AS descricao,
                        COALESCE(f.nome, 'N/A') AS costureira,
                        COALESCE(r.total_entregue, 0) AS boas,
                        COALESCE(e.valor_total_envio / NULLIF(e.total_pecas, 0), 0) AS valor_peca,
                        COALESCE(r.valor_total, e.valor_total_envio, 0) AS base,
                        0 AS pago,
                        NULL::date AS data_pagamento
                    FROM {schema}.controle_retorno_cortes r
                    JOIN {schema}.envios_cortes e ON r.envio_id = e.id
                    LEFT JOIN {schema}.cadastro_faccoes f ON e.prestador_id = f.id
                    LEFT JOIN {schema}.cortes_finalizados cf ON cf.retorno_id = r.id
                    WHERE r.data_chegada::date BETWEEN %s AND %s
                      AND cf.id IS NULL
                """
                params_prog = [ini, fim]
                if termo:
                    sql_progresso += " AND (e.codigo_corte ILIKE %s OR e.descricao_corte ILIKE %s OR f.nome ILIKE %s)"
                    lk = f"%{termo}%"
                    params_prog.extend([lk, lk, lk])
                cur.execute(sql_progresso, tuple(params_prog))
                all_rows.extend(cur.fetchall())

            # =====================================================
            # 3) PENDENTE - Finalizados mas NÃO pagos
            # =====================================================
            if status_filtro in ("Todos", "Pendente"):
                sql_pendente = f"""
                    SELECT 
                        'Pendente' AS status_calc,
                        cf.data_chegada::date AS data,
                        COALESCE(cf.codigo, '') AS codigo,
                        COALESCE(cf.descricao, '') AS descricao,
                        COALESCE(cf.costureira, '') AS costureira,
                        COALESCE(cf.qtd_pp,0) + COALESCE(cf.qtd_p,0) + COALESCE(cf.qtd_m,0) + 
                        COALESCE(cf.qtd_g,0) + COALESCE(cf.qtd_gg,0) + COALESCE(cf.qtd_g1,0) + 
                        COALESCE(cf.qtd_g2,0) + COALESCE(cf.qtd_g3,0) AS boas,
                        COALESCE(NULLIF(cf.valor_peca, 0), e.valor_total_envio / NULLIF(e.total_pecas, 0), 0) AS valor_peca,
                        COALESCE(cf.valor_total, 0) AS base,
                        COALESCE(cf.valor_pago, 0) AS pago,
                        cf.data_pagamento::date AS data_pagamento
                    FROM {schema}.cortes_finalizados cf
                    LEFT JOIN {schema}.envios_cortes e ON cf.envio_id = e.id
                    WHERE cf.data_chegada::date BETWEEN %s AND %s
                      AND (cf.pago = FALSE OR cf.pago IS NULL)
                """
                params_pend = [ini, fim]
                if termo:
                    sql_pendente += " AND (cf.codigo ILIKE %s OR cf.descricao ILIKE %s OR cf.costureira ILIKE %s)"
                    lk = f"%{termo}%"
                    params_pend.extend([lk, lk, lk])
                cur.execute(sql_pendente, tuple(params_pend))
                all_rows.extend(cur.fetchall())

            # =====================================================
            # 4) FINALIZADO - Finalizados E pagos
            # =====================================================
            if status_filtro in ("Todos", "Finalizado"):
                sql_final = f"""
                    SELECT 
                        'Finalizado' AS status_calc,
                        cf.data_chegada::date AS data,
                        COALESCE(cf.codigo, '') AS codigo,
                        COALESCE(cf.descricao, '') AS descricao,
                        COALESCE(cf.costureira, '') AS costureira,
                        COALESCE(cf.qtd_pp,0) + COALESCE(cf.qtd_p,0) + COALESCE(cf.qtd_m,0) + 
                        COALESCE(cf.qtd_g,0) + COALESCE(cf.qtd_gg,0) + COALESCE(cf.qtd_g1,0) + 
                        COALESCE(cf.qtd_g2,0) + COALESCE(cf.qtd_g3,0) AS boas,
                        COALESCE(NULLIF(cf.valor_peca, 0), e.valor_total_envio / NULLIF(e.total_pecas, 0), 0) AS valor_peca,
                        COALESCE(cf.valor_total, 0) AS base,
                        COALESCE(cf.valor_pago, 0) AS pago,
                        cf.data_pagamento::date AS data_pagamento
                    FROM {schema}.cortes_finalizados cf
                    LEFT JOIN {schema}.envios_cortes e ON cf.envio_id = e.id
                    WHERE cf.data_chegada::date BETWEEN %s AND %s
                      AND cf.pago = TRUE
                """
                params_fin = [ini, fim]
                if termo:
                    sql_final += " AND (cf.codigo ILIKE %s OR cf.descricao ILIKE %s OR cf.costureira ILIKE %s)"
                    lk = f"%{termo}%"
                    params_fin.extend([lk, lk, lk])
                cur.execute(sql_final, tuple(params_fin))
                all_rows.extend(cur.fetchall())

            conn.close()

        except Exception as ex:
            messagebox.showerror("Erro", str(ex))
            import traceback
            print(traceback.format_exc())
            return

        # Processar resultados
        lanc = []
        resumo = {}
        total_base = 0.0
        total_pago = 0.0

        try:
            d1 = datetime.strptime(ini, "%Y-%m-%d").date()
            d2 = datetime.strptime(fim, "%Y-%m-%d").date()
        except:
            d1 = d2 = date.today()

        for row in all_rows:
            # row: 0=status,1=data,2=cod,3=desc,4=cost,5=boas,6=vpeca,7=base,8=pago,9=dpag
            status_str = row[0] or ""
            data_str = str(row[1]) if row[1] else ""
            codigo = row[2] or ""
            descricao = row[3] or ""
            costureira = row[4] or ""
            boas = int(row[5] or 0)
            valor_peca = float(row[6] or 0)
            base_db = float(row[7] or 0)
            pago_db = float(row[8] or 0)
            data_pag = row[9]

            # Calcula BASE
            if base_db > 0:
                base = base_db
            else:
                base = valor_peca * boas

            # PAGO
            pago = pago_db
            if only_period:
                if not data_pag or not (d1 <= data_pag <= d2):
                    pago = 0.0

            saldo = base - pago

            lanc.append({
                "status": status_str,
                "data": data_str,
                "codigo": codigo,
                "descricao": descricao,
                "costureira": costureira,
                "boas": boas,
                "valor_peca": f"{valor_peca:.2f}",
                "base": f"{base:.2f}",
                "pago": f"{pago:.2f}",
                "saldo": f"{saldo:.2f}",
            })

            total_base += base
            total_pago += pago

            if costureira not in resumo:
                resumo[costureira] = {"costureira": costureira, "cortes": 0, "boas": 0, "base": 0.0, "pago": 0.0}
            r = resumo[costureira]
            r["cortes"] += 1
            r["boas"] += boas
            r["base"] += base
            r["pago"] += pago

        # Ordenar por data
        lanc.sort(key=lambda x: x["data"], reverse=True)

        # Preenche tabelas
        self.tree_lan.delete(*self.tree_lan.get_children())
        for item in lanc:
            self.tree_lan.insert("", "end", values=[item[c] for c in self.cols_lan])

        res_list = sorted(resumo.values(), key=lambda x: x["base"]-x["pago"], reverse=True)
        self.tree_res.delete(*self.tree_res.get_children())
        for r in res_list:
            self.tree_res.insert("", "end", values=[
                r["costureira"], r["cortes"], r["boas"],
                f"{r['base']:.2f}", f"{r['pago']:.2f}", f"{r['base']-r['pago']:.2f}"
            ])

        # KPIs
        self.kpi_base.configure(text=f"R$ {total_base:,.2f}")
        self.kpi_pago.configure(text=f"R$ {total_pago:,.2f}")
        self.kpi_saldo.configure(text=f"R$ {total_base - total_pago:,.2f}")
        self.kpi_cortes.configure(text=f"{len(all_rows)}")
        self.kpi_costs.configure(text=f"{len(res_list)}")
        self.kpi_media.configure(text=f"R$ {(total_base/len(all_rows)) if all_rows else 0:,.2f}")

        self._cache = {"lancamentos": lanc, "resumo": res_list}


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.geometry("1200x720")
    app = ContasAPagarPage(root)
    app.pack(fill="both", expand=True)
    root.mainloop()

#03/02/2025