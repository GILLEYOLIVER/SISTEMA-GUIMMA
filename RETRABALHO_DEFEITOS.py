import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime

try:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except ImportError:
    def get_conn():
        raise RuntimeError("Módulo BANCO_DE_DADOS_PG não encontrado")

    def get_schema():
        return "opera"

    def require_ready(essentials=None):
        return False, "Módulo de banco de dados não disponível"


class RetrabalhoDefeitosPage(ctk.CTkFrame):
    """Módulo separado para retrabalho de defeitos."""

    def __init__(self, master, sistema=None, app=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.parent = master
        if sistema is None:
            sistema = app

        self.sistema = sistema
        self.app = sistema

        origem = self.sistema
        self.cor_primaria = getattr(origem, 'cor_primaria', '#275090')
        self.cor_secundaria = getattr(origem, 'cor_secundaria', '#80bbff')
        self.cor_fundo = getattr(origem, 'cor_fundo', '#f0f0f0')
        self.cor_texto = getattr(origem, 'cor_texto', '#2c3e50')
        self.cor_destaque = getattr(origem, 'cor_selecao', '#e74c3c')
        self.cor_sucesso = getattr(origem, 'cor_sucesso', '#27ae60')
        self.cor_alerta = getattr(origem, 'cor_alerta', '#f39c12')
        self.cor_borda = getattr(origem, 'cor_borda', '#c0c0c0')
        self.cor_hover = getattr(origem, 'cor_hover', '#a0c0ff')

        self._verificar_banco()
        self._criar_interface()
        self._carregar_pendentes()
        self._carregar_defeitos()

    def _verificar_banco(self):
        try:
            ok, msg = require_ready()
            if not ok:
                messagebox.showwarning("Aviso", f"Banco não disponível:\n{msg}")
        except Exception as err:
            messagebox.showwarning("Aviso", f"Erro ao verificar banco:\n{err}")

    def _ensure_schema(self, cursor):
        schema = get_schema()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema}.defeitos_envios (
                id SERIAL PRIMARY KEY,
                historico_id BIGINT,
                envio_id INTEGER,
                envio_corte_id INTEGER,
                codigo VARCHAR(50),
                descricao TEXT,
                prestador VARCHAR(200),
                tamanho VARCHAR(10),
                quantidade INTEGER DEFAULT 0,
                tipo_servico VARCHAR(50),
                valor_peca NUMERIC(12,2) DEFAULT 0,
                origem VARCHAR(20) DEFAULT 'Externo',
                status VARCHAR(50) DEFAULT 'Pendente',
                data_envio DATE,
                data_retorno DATE,
                data_pagamento DATE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_defeitos_envio_status
            ON {schema}.defeitos_envios (status)
        """)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_defeitos_envio_prestador
            ON {schema}.defeitos_envios (prestador)
        """)

    def _criar_interface(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        main = ctk.CTkFrame(self, fg_color=self.cor_fundo, corner_radius=0)
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_rowconfigure(2, weight=1)
        main.grid_rowconfigure(4, weight=1)
        main.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Retrabalho de Defeitos", font=("Roboto", 18, "bold"),
                     text_color=self.cor_texto).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Gerencie envios e baixas internas de peças defeituosas",
                     font=("Roboto", 11), text_color=self.cor_texto).grid(row=1, column=0, sticky="w", pady=(2, 0))

        btns = ctk.CTkFrame(main, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 5))
        ctk.CTkLabel(btns, text="Valor/Peça:", text_color=self.cor_texto).pack(side="left", padx=(0, 4))
        self.valor_peca_entry = ctk.CTkEntry(btns, width=90)
        self.valor_peca_entry.insert(0, "0.00")
        self.valor_peca_entry.pack(side="left", padx=(0, 12))
        ctk.CTkButton(btns, text="Atualizar", command=self._recarregar_tudo,
                      fg_color=self.cor_primaria, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Enviar para Prestador", command=self._registrar_envio_externo,
                      fg_color=self.cor_destaque, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Baixa Interna", command=self._registrar_baixa_interna,
                      fg_color=self.cor_sucesso, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Imprimir Ficha", command=self._imprimir_ficha,
                      fg_color=self.cor_alerta, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)

        pend_frame = ctk.CTkFrame(main, fg_color="transparent")
        pend_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 8))
        pend_frame.grid_rowconfigure(1, weight=1)
        pend_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pend_frame, text="Pendências (defeitos a tratar)",
                     font=("Roboto", 12, "bold"), text_color=self.cor_texto).grid(row=0, column=0, sticky="w")

        self.pend_tree = ttk.Treeview(
            pend_frame,
            columns=("data", "envio", "codigo", "descricao", "prestador", "tamanho", "quantidade", "servico"),
            show="headings",
            height=8
        )
        for col, label, width in [
            ("data", "Data", 100),
            ("envio", "Id de Envio", 90),
            ("codigo", "Código", 90),
            ("descricao", "Descrição", 220),
            ("prestador", "Prestador", 160),
            ("tamanho", "Tamanho", 70),
            ("quantidade", "Defeitos", 80),
            ("servico", "Serviço", 100),
        ]:
            self.pend_tree.heading(col, text=label)
            self.pend_tree.column(col, width=width, anchor="center")
        self.pend_tree.grid(row=1, column=0, sticky="nsew")

        pend_scroll = ttk.Scrollbar(pend_frame, orient="vertical", command=self.pend_tree.yview)
        pend_scroll.grid(row=1, column=1, sticky="ns")
        self.pend_tree.configure(yscrollcommand=pend_scroll.set)

        proc_frame = ctk.CTkFrame(main, fg_color="transparent")
        proc_frame.grid(row=4, column=0, sticky="nsew", padx=15, pady=(0, 10))
        proc_frame.grid_rowconfigure(1, weight=1)
        proc_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(proc_frame, text="Defeitos em Processo",
                     font=("Roboto", 12, "bold"), text_color=self.cor_texto).grid(row=0, column=0, sticky="w")

        self.proc_tree = ttk.Treeview(
            proc_frame,
            columns=("id", "prestador", "codigo", "descricao", "tamanho", "quantidade", "origem",
                     "status", "data_envio", "data_retorno"),
            show="headings",
            height=8
        )
        for col, label, width in [
            ("id", "ID", 60),
            ("prestador", "Prestador", 160),
            ("codigo", "Código", 90),
            ("descricao", "Descrição", 220),
            ("tamanho", "Tamanho", 70),
            ("quantidade", "Defeitos", 80),
            ("origem", "Origem", 90),
            ("status", "Status", 100),
            ("data_envio", "Envio", 90),
            ("data_retorno", "Retorno", 90),
        ]:
            self.proc_tree.heading(col, text=label)
            self.proc_tree.column(col, width=width, anchor="center")
        self.proc_tree.grid(row=1, column=0, sticky="nsew")

        proc_scroll = ttk.Scrollbar(proc_frame, orient="vertical", command=self.proc_tree.yview)
        proc_scroll.grid(row=1, column=1, sticky="ns")
        self.proc_tree.configure(yscrollcommand=proc_scroll.set)

        proc_actions = ctk.CTkFrame(main, fg_color="transparent")
        proc_actions.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 5))
        ctk.CTkButton(proc_actions, text="Marcar Retorno", command=self._marcar_retorno,
                      fg_color=self.cor_alerta, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)
        ctk.CTkButton(proc_actions, text="Finalizar", command=self._finalizar_defeito,
                      fg_color=self.cor_sucesso, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=4)

    def _recarregar_tudo(self):
        self._carregar_pendentes()
        self._carregar_defeitos()

    def _carregar_pendentes(self):
        self.pend_tree.delete(*self.pend_tree.get_children())
        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cur = conn.cursor()
            self._ensure_schema(cur)

            sql = f"""
                SELECT
                    e.data_envio,
                    e.id,
                    COALESCE(e.codigo_corte, ''),
                    COALESCE(e.descricao_corte, ''),
                    COALESCE(cf.nome, ''),
                    COALESCE(r.tamanho, ''),
                    COALESCE(r.defeitos, 0),
                    COALESCE(e.tipo_servico, '')
                FROM {schema}.retorno_detalhes_tamanho r
                JOIN {schema}.envios_cortes e ON e.id = r.envio_id
                LEFT JOIN {schema}.cadastro_faccoes cf ON cf.id = e.prestador_id
                WHERE COALESCE(r.defeitos, 0) > 0
                  AND NOT EXISTS (
                      SELECT 1 FROM {schema}.defeitos_envios d
                       WHERE d.envio_id = e.id
                         AND COALESCE(d.tamanho, '') = COALESCE(r.tamanho, '')
                  )
                ORDER BY e.data_envio DESC, e.id DESC, r.tamanho
            """
            cur.execute(sql)
            for row in cur.fetchall():
                data_envio, envio_id, codigo, desc, prestador, tamanho, qtd, servico = row
                if hasattr(data_envio, "strftime"):
                    data_envio = data_envio.strftime("%d/%m/%Y")
                self.pend_tree.insert("", "end", values=(
                    data_envio or "", envio_id or "", codigo or "", desc or "", prestador or "",
                    tamanho or "", qtd or 0, servico or ""
                ))

            cur.execute(
                """
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = %s
                   AND table_name = 'historico_de_servico'
                """,
                (schema,),
            )
            cols_hist = {row[0] for row in cur.fetchall()}
            if {"evento", "descricao", "quantidade", "status", "setor"}.issubset(cols_hist):
                data_col = "data" if "data" in cols_hist else "data_atualizacao"
                envio_col = "envio_id" if "envio_id" in cols_hist else (
                    "envio_corte_id" if "envio_corte_id" in cols_hist else "NULL"
                )
                sql_hist = f"""
                    SELECT {data_col}, {envio_col}, evento, descricao, setor, quantidade, tipo_servico, id
                    FROM {schema}.historico_de_servico
                    WHERE status = 'Pendente'
                      AND COALESCE(quantidade, 0) > 0
                      AND NOT EXISTS (
                          SELECT 1 FROM {schema}.defeitos_envios d
                           WHERE d.historico_id = {schema}.historico_de_servico.id
                      )
                    ORDER BY {data_col} DESC
                """
                cur.execute(sql_hist)
                for row in cur.fetchall():
                    data_hist, envio_id, evento, desc, setor, qtd, servico, hist_id = row
                    if hasattr(data_hist, "strftime"):
                        data_hist = data_hist.strftime("%d/%m/%Y")
                    self.pend_tree.insert("", "end", values=(
                        data_hist or "", envio_id or "", "-", desc or "", setor or "",
                        "-", qtd or 0, servico or evento or ""
                    ), tags=(f"hist_{hist_id}",))

            conn.commit()
        except Exception as err:
            if conn:
                conn.rollback()
            messagebox.showerror("Erro", f"Falha ao carregar pendências:\n{err}")
        finally:
            if conn:
                conn.close()

    def _carregar_defeitos(self):
        self.proc_tree.delete(*self.proc_tree.get_children())
        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cur = conn.cursor()
            self._ensure_schema(cur)
            cur.execute(f"""
                SELECT id, prestador, codigo, descricao, tamanho, quantidade, origem, status,
                       data_envio, data_retorno
                FROM {schema}.defeitos_envios
                ORDER BY id DESC
            """)
            for row in cur.fetchall():
                (rid, prestador, codigo, desc, tamanho, qtd, origem, status,
                 data_envio, data_retorno) = row
                if hasattr(data_envio, "strftime"):
                    data_envio = data_envio.strftime("%d/%m/%Y")
                if hasattr(data_retorno, "strftime"):
                    data_retorno = data_retorno.strftime("%d/%m/%Y")
                self.proc_tree.insert("", "end", values=(
                    rid, prestador or "", codigo or "", desc or "", tamanho or "", qtd or 0,
                    origem or "", status or "", data_envio or "", data_retorno or ""
                ))
        except Exception as err:
            if conn:
                conn.rollback()
            messagebox.showerror("Erro", f"Falha ao carregar defeitos:\n{err}")
        finally:
            if conn:
                conn.close()

    def _get_pendente_selecionado(self):
        sel = self.pend_tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um defeito pendente.")
            return None
        return self.pend_tree.item(sel[0], "values")

    def _registrar_envio_externo(self):
        dados = self._get_pendente_selecionado()
        if not dados:
            return
        data_envio = datetime.now().date()
        valor_peca = self._valor_peca_atual()
        self._registrar_defeito(dados, origem="Externo", status="Enviado",
                                data_envio=data_envio, valor_peca=valor_peca)

    def _registrar_baixa_interna(self):
        dados = self._get_pendente_selecionado()
        if not dados:
            return
        data_retorno = datetime.now().date()
        valor_peca = self._valor_peca_atual()
        self._registrar_defeito(dados, origem="Interno", status="Finalizado",
                                data_retorno=data_retorno, valor_peca=valor_peca)

    def _valor_peca_atual(self):
        try:
            return float((self.valor_peca_entry.get() or "0").replace(",", "."))
        except Exception:
            return 0.0

    def _registrar_defeito(self, dados, origem, status, data_envio=None, data_retorno=None, valor_peca=0.0):
        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cur = conn.cursor()
            self._ensure_schema(cur)

            data, envio_id, codigo, desc, prestador, tamanho, qtd, servico = dados
            envio_id = int(envio_id) if str(envio_id).isdigit() else None
            cur.execute(f"""
                INSERT INTO {schema}.defeitos_envios
                    (envio_id, codigo, descricao, prestador, tamanho, quantidade,
                     tipo_servico, valor_peca, origem, status, data_envio, data_retorno)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                envio_id,
                codigo if codigo != "-" else None,
                desc,
                prestador,
                tamanho if tamanho != "-" else None,
                int(qtd) if str(qtd).isdigit() else 0,
                servico,
                valor_peca,
                origem,
                status,
                data_envio,
                data_retorno,
            ))
            conn.commit()
            self._recarregar_tudo()
        except Exception as err:
            if conn:
                conn.rollback()
            messagebox.showerror("Erro", f"Falha ao registrar defeito:\n{err}")
        finally:
            if conn:
                conn.close()

    def _get_defeito_processo(self):
        sel = self.proc_tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um defeito em processo.")
            return None
        return self.proc_tree.item(sel[0], "values")

    def _marcar_retorno(self):
        item = self._get_defeito_processo()
        if not item:
            return
        defeito_id = item[0]
        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                f"UPDATE {schema}.defeitos_envios SET status = %s, data_retorno = CURRENT_DATE WHERE id = %s",
                ("Em Conferência", defeito_id),
            )
            conn.commit()
            self._carregar_defeitos()
        except Exception as err:
            if conn:
                conn.rollback()
            messagebox.showerror("Erro", f"Falha ao marcar retorno:\n{err}")
        finally:
            if conn:
                conn.close()

    def _finalizar_defeito(self):
        item = self._get_defeito_processo()
        if not item:
            return
        defeito_id = item[0]
        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                f"UPDATE {schema}.defeitos_envios SET status = %s, data_retorno = CURRENT_DATE WHERE id = %s",
                ("Finalizado", defeito_id),
            )
            conn.commit()
            self._carregar_defeitos()
        except Exception as err:
            if conn:
                conn.rollback()
            messagebox.showerror("Erro", f"Falha ao finalizar defeito:\n{err}")
        finally:
            if conn:
                conn.close()

    def _imprimir_ficha(self):
        item = self._get_defeito_processo()
        if not item:
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except Exception:
            messagebox.showwarning("Aviso", "reportlab não está disponível para gerar a ficha.")
            return
        defeito_id, prestador, codigo, descricao, tamanho, qtd, origem, status, data_envio, data_retorno = item
        filename = f"ficha_defeito_{defeito_id}.pdf"
        c = canvas.Canvas(filename, pagesize=A4)
        width, height = A4
        y = height - 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Ficha de Retrabalho de Defeitos")
        y -= 30
        c.setFont("Helvetica", 11)
        for label, value in [
            ("ID", defeito_id),
            ("Prestador", prestador),
            ("Código", codigo),
            ("Descrição", descricao),
            ("Tamanho", tamanho),
            ("Quantidade", qtd),
            ("Origem", origem),
            ("Status", status),
            ("Envio", data_envio),
            ("Retorno", data_retorno),
        ]:
            c.drawString(40, y, f"{label}: {value}")
            y -= 18
        c.showPage()
        c.save()
        messagebox.showinfo("Sucesso", f"Ficha gerada: {filename}")


if __name__ == "__main__":
    root = ctk.CTk()
    root.geometry("1100x700")
    root.cor_primaria = "#2f4f7f"
    root.cor_secundaria = "#242f44"
    root.cor_fundo = "#1f2637"
    root.cor_texto = "#f0f0f0"
    root.cor_selecao = "#e07d31"
    root.cor_sucesso = "#27ae60"
    root.cor_alerta = "#ffb400"
    root.cor_borda = "#3f5470"
    root.cor_hover = "#3f6fa0"
    app = RetrabalhoDefeitosPage(root, root)
    app.pack(fill="both", expand=True)
    root.mainloop()
