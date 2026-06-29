import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from PAGINAS_DO_SISTEMA.UI_CALENDARIO import abrir_calendario

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
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
                data_finalizacao DATE,
                hora_envio TIME,
                hora_retorno TIME,
                hora_finalizacao TIME,
                previsao_entrega DATE,
                tel_encarregado VARCHAR(50),
                tel_acabamento VARCHAR(50),
                aviamentos TEXT,
                outros TEXT,
                observacoes TEXT,
                data_pagamento DATE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.defeitos_envios
            ADD COLUMN IF NOT EXISTS valor_peca NUMERIC(12,2) DEFAULT 0
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.defeitos_envios
            ADD COLUMN IF NOT EXISTS data_finalizacao DATE
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.defeitos_envios
            ADD COLUMN IF NOT EXISTS hora_envio TIME
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.defeitos_envios
            ADD COLUMN IF NOT EXISTS hora_retorno TIME
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.defeitos_envios
            ADD COLUMN IF NOT EXISTS hora_finalizacao TIME
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.defeitos_envios
            ADD COLUMN IF NOT EXISTS previsao_entrega DATE
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.defeitos_envios
            ADD COLUMN IF NOT EXISTS tel_encarregado VARCHAR(50)
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.defeitos_envios
            ADD COLUMN IF NOT EXISTS tel_acabamento VARCHAR(50)
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.defeitos_envios
            ADD COLUMN IF NOT EXISTS aviamentos TEXT
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.defeitos_envios
            ADD COLUMN IF NOT EXISTS outros TEXT
        """)
        cursor.execute(f"""
            ALTER TABLE {schema}.defeitos_envios
            ADD COLUMN IF NOT EXISTS observacoes TEXT
        """)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_defeitos_envio_status
            ON {schema}.defeitos_envios (status)
        """)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_defeitos_envio_prestador
            ON {schema}.defeitos_envios (prestador)
        """)
        cursor.execute(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_defeitos_envio_unico
            ON {schema}.defeitos_envios (envio_id, tamanho)
            WHERE envio_id IS NOT NULL AND tamanho IS NOT NULL
        """)
        cursor.execute(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_defeitos_envio_hist_unico
            ON {schema}.defeitos_envios (historico_id)
            WHERE historico_id IS NOT NULL
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
        item = self.pend_tree.item(sel[0])
        return {
            "values": item.get("values", ()),
            "tags": item.get("tags", ()),
        }

    def _registrar_envio_externo(self):
        dados = self._get_pendente_selecionado()
        if not dados:
            return
        self._abrir_janela_envio_defeito(dados, origem="Externo", status="Enviado")

    def _registrar_baixa_interna(self):
        dados = self._get_pendente_selecionado()
        if not dados:
            return
        data_retorno = datetime.now().date()
        data_finalizacao = datetime.now().date()
        valor_peca = self._valor_peca_atual()
        self._registrar_defeito(dados, origem="Interno", status="Finalizado",
                                data_retorno=data_retorno, valor_peca=valor_peca,
                                data_finalizacao=data_finalizacao)

    def _valor_peca_atual(self):
        try:
            return float((self.valor_peca_entry.get() or "0").replace(",", "."))
        except Exception:
            return 0.0

    def _registrar_defeito(self, dados, origem, status, data_envio=None, data_retorno=None,
                           valor_peca=0.0, previsao_entrega=None, tel_encarregado=None,
                           tel_acabamento=None, aviamentos=None, outros=None, observacoes=None,
                           data_finalizacao=None, data_pagamento=None):
        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cur = conn.cursor()
            self._ensure_schema(cur)

            values = list(dados["values"]) if isinstance(dados, dict) else list(dados or [])
            if len(values) < 8:
                values.extend([""] * (8 - len(values)))
            data, envio_id, codigo, desc, prestador, tamanho, qtd, servico = values[:8]
            envio_id = int(envio_id) if str(envio_id).isdigit() else None
            historico_id = None
            if isinstance(dados, dict):
                for tag in dados.get("tags", ()):
                    if tag.startswith("hist_") and tag.split("_")[-1].isdigit():
                        historico_id = int(tag.split("_")[-1])
                        break

            if historico_id:
                cur.execute(
                    f"SELECT 1 FROM {schema}.defeitos_envios WHERE historico_id = %s",
                    (historico_id,),
                )
            else:
                cur.execute(
                    f"""
                    SELECT 1 FROM {schema}.defeitos_envios
                     WHERE envio_id = %s AND COALESCE(tamanho, '') = COALESCE(%s, '')
                    """,
                    (envio_id, tamanho if tamanho != "-" else None),
                )
            if cur.fetchone():
                messagebox.showwarning("Aviso", "Este defeito já foi enviado anteriormente.")
                return

            hora_envio = datetime.now().time() if data_envio else None
            hora_retorno = datetime.now().time() if data_retorno else None
            if status == "Finalizado" and not data_finalizacao:
                data_finalizacao = datetime.now().date()
            hora_finalizacao = datetime.now().time() if data_finalizacao else None

            cur.execute(f"""
                INSERT INTO {schema}.defeitos_envios
                    (historico_id, envio_id, codigo, descricao, prestador, tamanho, quantidade,
                     tipo_servico, valor_peca, origem, status, data_envio, data_retorno,
                     data_finalizacao, hora_envio, hora_retorno, hora_finalizacao,
                     previsao_entrega, tel_encarregado, tel_acabamento, aviamentos, outros,
                     observacoes, data_pagamento)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                historico_id,
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
                data_finalizacao,
                hora_envio,
                hora_retorno,
                hora_finalizacao,
                previsao_entrega,
                tel_encarregado,
                tel_acabamento,
                aviamentos,
                outros,
                observacoes,
                data_pagamento,
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

    def _parse_date(self, valor):
        if not valor:
            return None
        if hasattr(valor, "year"):
            return valor
        texto = str(valor).strip()
        if not texto:
            return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(texto, fmt).date()
            except Exception:
                continue
        return None

    def _format_date(self, valor):
        if hasattr(valor, "strftime"):
            return valor.strftime("%d/%m/%Y")
        return str(valor or "")


    def _centralizar_toplevel(self, win: ctk.CTkToplevel, largura=None, altura=None, parent=None, pad=20):
        """Centraliza a janela e garante que fique totalmente visível na tela."""
        try:
            win.update_idletasks()
            if largura is None:
                largura = max(int(win.winfo_reqwidth()), int(win.winfo_width()))
            if altura is None:
                altura = max(int(win.winfo_reqheight()), int(win.winfo_height()))

            sw = int(win.winfo_screenwidth())
            sh = int(win.winfo_screenheight())

            max_w = max(200, sw - pad * 2)
            max_h = max(200, sh - pad * 2)
            largura = min(int(largura), max_w)
            altura = min(int(altura), max_h)

            if parent is not None:
                try:
                    parent.update_idletasks()
                    px = int(parent.winfo_rootx())
                    py = int(parent.winfo_rooty())
                    pw = int(parent.winfo_width())
                    ph = int(parent.winfo_height())
                    x = px + (pw - largura) // 2
                    y = py + (ph - altura) // 2
                except Exception:
                    x = (sw - largura) // 2
                    y = (sh - altura) // 2
            else:
                x = (sw - largura) // 2
                y = (sh - altura) // 2

            x = max(pad, min(int(x), sw - largura - pad))
            y = max(pad, min(int(y), sh - altura - pad))

            win.geometry(f"{largura}x{altura}+{x}+{y}")
        except Exception:
            pass

    def _abrir_calendario(self, entry, parent=None):
        return abrir_calendario(parent or self, entry, output_format="%d/%m/%Y")
        from datetime import datetime
        import calendar as _cal

        meses_pt = [
            "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ]

        def setar_data(d):
            entry.delete(0, "end")
            entry.insert(0, d.strftime("%d/%m/%Y"))
            if parent is not None:
                parent.lift()
                parent.focus_force()
            top.destroy()

        top = ctk.CTkToplevel(self)
        top.title("Calendário")
        top.resizable(False, False)

        W, H = 300, 300
        self.update_idletasks()
        top.update_idletasks()

        ex = entry.winfo_rootx()
        ey = entry.winfo_rooty()
        eh = entry.winfo_height()

        x = ex
        y = ey + eh + 6

        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        if x + W > sw:
            x = sw - W - 10
        if y + H > sh:
            y = ey - H - 6

        top.geometry(f"{W}x{H}+{x}+{y}")
        top.transient(parent or self)
        top.grab_set()
        top.focus_force()
        top.lift()

        now = datetime.now()
        ano = now.year
        mes = now.month

        nav = ctk.CTkFrame(top)
        nav.pack(fill="x", padx=10, pady=5)

        lbl_mes = ctk.CTkLabel(nav, text=f"{meses_pt[mes]} {ano}", font=("Arial", 14))
        ctk.CTkButton(nav, text="<", width=30, command=lambda: mudar_mes(-1)).pack(side="left")
        lbl_mes.pack(side="left", expand=True)
        ctk.CTkButton(nav, text=">", width=30, command=lambda: mudar_mes(1)).pack(side="right")

        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        frame_dias = ctk.CTkFrame(top)
        frame_dias.pack(fill="both", expand=True, padx=10, pady=5)

        for i, dia in enumerate(dias_semana):
            lbl = ctk.CTkLabel(frame_dias, text=dia, width=30, height=30)
            lbl.grid(row=0, column=i, padx=2, pady=2)

        def mudar_mes(delta):
            nonlocal mes, ano
            mes += delta
            if mes > 12:
                mes = 1
                ano += 1
            elif mes < 1:
                mes = 12
                ano -= 1
            lbl_mes.configure(text=f"{meses_pt[mes]} {ano}")
            desenhar_calendario()

        def desenhar_calendario():
            for w in frame_dias.grid_slaves():
                if int(w.grid_info()["row"]) > 0:
                    w.destroy()

            cal = _cal.monthcalendar(ano, mes)
            for i, semana in enumerate(cal):
                for j, dia in enumerate(semana):
                    if dia == 0:
                        continue
                    btn = ctk.CTkButton(
                        frame_dias,
                        text=str(dia),
                        width=30,
                        height=30,
                        command=lambda d=dia: setar_data(datetime(ano, mes, d))
                    )
                    btn.grid(row=i + 1, column=j, padx=2, pady=2)

        desenhar_calendario()

    def _carregar_info_envio(self, envio_id):
        if not envio_id:
            return {}
        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = %s
                   AND table_name = 'envios_cortes'
                """,
                (schema,),
            )
            cols = {row[0] for row in cur.fetchall()}
            wanted = {
                "codigo_corte": "codigo",
                "descricao_corte": "descricao",
                "ordem_corte": "ordem_corte",
                "data_envio": "data_envio",
                "previsao_entrega": "previsao_entrega",
                "tel_encarregado": "tel_encarregado",
                "tel_acabamento": "tel_acabamento",
                "prestador_id": "prestador_id",
            }
            select_cols = [col for col in wanted if col in cols]
            if not select_cols:
                return {}
            cur.execute(
                f"SELECT {', '.join(select_cols)} FROM {schema}.envios_cortes WHERE id = %s",
                (envio_id,),
            )
            row = cur.fetchone()
            if not row:
                return {}
            result = {}
            for idx, col in enumerate(select_cols):
                result[wanted[col]] = row[idx]
            return result
        except Exception:
            return {}
        finally:
            if conn:
                conn.close()

    def _carregar_info_prestador(self, prestador_id=None, nome=None):
        if not prestador_id and not nome:
            return {}
        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = %s
                   AND table_name = 'cadastro_faccoes'
                """,
                (schema,),
            )
            cols = {row[0] for row in cur.fetchall()}
            wanted = ["nome", "telefone", "banco", "agencia", "conta", "pix", "titular_da_conta"]
            select_cols = [col for col in wanted if col in cols]
            if not select_cols:
                return {}
            if prestador_id:
                cur.execute(
                    f"SELECT {', '.join(select_cols)} FROM {schema}.cadastro_faccoes WHERE id = %s",
                    (prestador_id,),
                )
            else:
                cur.execute(
                    f"SELECT {', '.join(select_cols)} FROM {schema}.cadastro_faccoes WHERE nome = %s",
                    (nome,),
                )
            row = cur.fetchone()
            if not row:
                return {}
            data = dict(zip(select_cols, row))
            return {
                "nome": data.get("nome") or nome or "",
                "telefone": data.get("telefone") or "",
                "banco": data.get("banco") or "",
                "agencia": data.get("agencia") or "",
                "conta": data.get("conta") or "",
                "pix": data.get("pix") or "",
                "titular": data.get("titular_da_conta") or "",
            }
        except Exception:
            return {}
        finally:
            if conn:
                conn.close()

    def _montar_dados_pdf_defeito(self, defeito, prestador_info=None, envio_info=None, extras=None):
        prestador_info = prestador_info or {}
        envio_info = envio_info or {}
        extras = extras or {}
        tamanhos = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]

        tamanho_defeito = (defeito.get("tamanho") or "").upper()
        qtd_defeito = int(defeito.get("quantidade") or 0)
        valor_peca = float(defeito.get("valor_peca") or 0.0)
        itens = []
        total_geral = 0.0
        for tam in tamanhos:
            qtd = qtd_defeito if tam == tamanho_defeito else 0
            subtotal = qtd * valor_peca
            total_geral += subtotal
            itens.append({
                "tam": tam,
                "qtd": qtd,
                "piloto": 0,
                "valor_peca": valor_peca,
                "subtotal": subtotal,
            })

        prestador = {
            "nome": prestador_info.get("nome") or defeito.get("prestador") or "",
            "telefone": prestador_info.get("telefone") or "",
            "banco": prestador_info.get("banco") or "",
            "agencia": prestador_info.get("agencia") or "",
            "conta": prestador_info.get("conta") or "",
            "pix": prestador_info.get("pix") or "",
            "titular": prestador_info.get("titular") or "",
        }
        corte = {
            "codigo": defeito.get("codigo") or envio_info.get("codigo") or "",
            "descricao": defeito.get("descricao") or envio_info.get("descricao") or "",
            "ordem_corte": envio_info.get("ordem_corte") or "",
        }
        envio = {
            "data_envio": defeito.get("data_envio") or envio_info.get("data_envio") or "",
            "previsao_entrega": defeito.get("previsao_entrega") or envio_info.get("previsao_entrega") or "",
            "tel_encarregado": defeito.get("tel_encarregado") or envio_info.get("tel_encarregado") or "",
            "tel_acabamento": defeito.get("tel_acabamento") or envio_info.get("tel_acabamento") or "",
        }
        campos_texto = {
            "aviamentos": defeito.get("aviamentos") or extras.get("aviamentos") or "",
            "outros": defeito.get("outros") or extras.get("outros") or "",
            "observacoes": defeito.get("observacoes") or extras.get("observacoes") or "",
        }
        return {
            "prestador": prestador,
            "corte": corte,
            "envio": envio,
            "itens": itens,
            "totais": {"total_geral": total_geral},
            "campos_texto": campos_texto,
            "meta": extras.get("meta") or {},
        }

    def _gerar_pdf_defeito(self, caminho_pdf: str | None = None, dados: dict | None = None,
                           abrir_pdf: bool = False) -> str:
        from datetime import datetime, date
        import os
        import re
        import sys
        import tempfile
        import webbrowser

        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_RIGHT

        def _t(v):
            if v is None:
                return ""
            if isinstance(v, (date, datetime)):
                try:
                    return v.strftime("%d/%m/%Y")
                except Exception:
                    return str(v)
            return str(v).strip()

        def _p(text):
            txt = _t(text)
            txt = txt.replace("\r\n", "\n").replace("\r", "\n")
            txt = re.sub(r"\n{3,}", "\n\n", txt)
            txt = txt.replace("\n", "<br/>")
            return txt.strip() if txt.strip() else "-"

        def _int(v, default=0):
            try:
                if v is None or v == "":
                    return int(default)
                if isinstance(v, (int, float)):
                    return int(v)
                s = str(v).strip()
                if not s:
                    return int(default)
                return int(float(s.replace(".", "").replace(",", ".")))
            except Exception:
                return int(default)

        def _num(v, default=0.0):
            try:
                if v is None or v == "":
                    return float(default)
                if isinstance(v, (int, float)):
                    return float(v)
                s = str(v).strip().replace("R$", "").replace(" ", "")
                if not s:
                    return float(default)
                try:
                    return float(s)
                except Exception:
                    return float(s.replace(".", "").replace(",", "."))
            except Exception:
                return float(default)

        def fmt_moeda(v):
            val = float(_num(v, 0.0))
            s = f"{val:,.2f}"
            return s.replace(",", "X").replace(".", ",").replace("X", ".")

        def fmt_data(v):
            s = _t(v)
            return s if s else "-"

        def _find_logo_path(candidate: str | None):
            c = (candidate or "").strip()
            if c and os.path.exists(c):
                return c
            try:
                from PAGINAS_DO_SISTEMA.LOGOMARCA import get_logo_path
                configured_logo = get_logo_path()
                if configured_logo and os.path.exists(configured_logo):
                    return configured_logo
            except Exception:
                pass
            if os.path.exists("LOGO.jpg"):
                return "LOGO.jpg"
            try:
                lp = globals().get("LOGO_PATH", "")
                if lp and os.path.exists(lp):
                    return lp
            except Exception:
                pass
            return None

        def _open_pdf(path_pdf: str):
            try:
                abs_path = os.path.abspath(path_pdf)
                if sys.platform.startswith("win"):
                    url = "file:///" + abs_path.replace("\\", "/")
                else:
                    url = "file://" + abs_path
                webbrowser.open(url)
            except Exception:
                pass

        if not caminho_pdf:
            fd, caminho_pdf = tempfile.mkstemp(suffix=".pdf", prefix="defeito_envio_")
            os.close(fd)

        prestador = dados.get("prestador", {}) or {}
        corte = dados.get("corte", {}) or {}
        envio = dados.get("envio", {}) or {}
        itens = dados.get("itens", []) or []
        totais = dados.get("totais", {}) or {}
        campos_texto = dados.get("campos_texto", {}) or {}
        meta = dados.get("meta", {}) or {}

        itens_norm = []
        total_geral = 0.0
        for it in itens:
            tam = _t(it.get("tam")) or "-"
            qtd = _int(it.get("qtd"), 0)
            piloto = _int(it.get("piloto"), 0)
            valor_peca = _num(it.get("valor_peca"), 0.0)
            subtotal = it.get("subtotal")
            if subtotal is None or subtotal == "":
                subtotal = (qtd + piloto) * valor_peca
            subtotal = _num(subtotal, 0.0)
            total_geral += subtotal
            itens_norm.append({
                "tam": tam, "qtd": qtd, "piloto": piloto, "valor_peca": valor_peca, "subtotal": subtotal
            })

        if totais.get("total_geral") not in (None, ""):
            total_geral = _num(totais.get("total_geral"), total_geral)

        titulo = "CONTROLE DE MÃO DE OBRA — Retrabalho de Defeitos"
        gerado_em = _t(meta.get("gerado_em")) or datetime.now().strftime("%d/%m/%Y %H:%M")
        logo_path = _find_logo_path(meta.get("logo_path"))
        empresa_nome = (_t(meta.get("empresa_nome")) or "Sistema Guimma").strip()

        doc = SimpleDocTemplate(
            caminho_pdf,
            pagesize=A4,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            title=titulo,
            author="Sistema Guimma",
        )

        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            "OPERA_Title_Defeito",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=15,
            alignment=TA_LEFT,
            spaceAfter=2,
        )
        style_sub = ParagraphStyle(
            "OPERA_Sub_Defeito",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#444444"),
            alignment=TA_LEFT,
        )
        style_value = ParagraphStyle(
            "OPERA_Value_Defeito",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#222222"),
        )
        style_box_title = ParagraphStyle(
            "OPERA_BoxTitle_Defeito",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#111111"),
            spaceAfter=2,
        )
        style_total = ParagraphStyle(
            "OPERA_Total_Defeito",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#111111"),
        )
        style_small = ParagraphStyle(
            "OPERA_Small_Defeito",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#666666"),
        )

        def build_footer(canvas, _doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.HexColor("#666666"))
            canvas.drawString(16 * mm, 9 * mm, "SISTEMA GUIMMA — Impressão")
            canvas.drawRightString(210 * mm - 16 * mm, 9 * mm, f"Página {canvas.getPageNumber()}")
            canvas.restoreState()

        def kv_table(title_left: str, rows_left, title_right: str, rows_right):
            left_parts = [Paragraph(title_left, style_box_title)]
            for k, v in rows_left:
                left_parts.append(Paragraph(f"{_t(k)}: <b>{_p(v)}</b>", style_value))

            right_parts = [Paragraph(title_right, style_box_title)]
            for k, v in rows_right:
                right_parts.append(Paragraph(f"{_t(k)}: <b>{_p(v)}</b>", style_value))

            t = Table([[left_parts, right_parts]], colWidths=[(doc.width * 0.5) - 4, (doc.width * 0.5) - 4])
            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (0, 0), 0.6, colors.HexColor("#D0D0D0")),
                ("BOX", (1, 0), (1, 0), 0.6, colors.HexColor("#D0D0D0")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
            ]))
            return t

        def text_box_compacto(title: str, body: str):
            elements = [
                Paragraph(title, style_box_title),
                Paragraph(_p(body), style_value),
            ]
            t = Table([[elements]], colWidths=[doc.width])
            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D0D0D0")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
            ]))
            return t

        story = []
        header_left = [
            Paragraph(titulo, style_title),
            Paragraph(f"Gerado em: {gerado_em}", style_sub),
        ]

        header_right = []
        if logo_path:
            try:
                img = RLImage(logo_path)
                img.drawHeight = 16 * mm
                img.drawWidth = 42 * mm
                header_right.append(img)
            except Exception:
                header_right.append(
                    Paragraph("SISTEMA GUIMMA", ParagraphStyle("LogoTxtDefeito", parent=style_title, alignment=TA_RIGHT)))
        else:
            header_right.append(
                Paragraph("SISTEMA GUIMMA", ParagraphStyle("LogoTxtDefeito", parent=style_title, alignment=TA_RIGHT)))

        header_tbl = Table([[header_left, header_right]], colWidths=[doc.width * 0.70, doc.width * 0.30])
        header_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_tbl)
        story.append(Spacer(1, 1.5 * mm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#222222")))
        story.append(Spacer(1, 4 * mm))

        story.append(kv_table(
            "Dados do Prestador",
            [
                ("Nome", prestador.get("nome")),
                ("Telefone", prestador.get("telefone")),
                ("Banco", prestador.get("banco")),
                ("Agência", prestador.get("agencia")),
                ("Conta", prestador.get("conta")),
                ("PIX", prestador.get("pix")),
                ("Titular", prestador.get("titular")),
            ],
            "Dados do Corte / Envio",
            [
                ("Código", corte.get("codigo")),
                ("Descrição", corte.get("descricao")),
                ("Nº Ordem", corte.get("ordem_corte")),
                ("Data", fmt_data(envio.get("data_envio"))),
                ("Previsão de Entrega", fmt_data(envio.get("previsao_entrega"))),
                ("Tel. Encarregado", envio.get("tel_encarregado")),
                ("Tel. Acabamento", envio.get("tel_acabamento")),
            ],
        ))
        story.append(Spacer(1, 4 * mm))

        story.append(Paragraph("Itens do Envio", style_box_title))
        story.append(Spacer(1, 1.5 * mm))

        table_data = [["Tam.", "Qtd", "Piloto", "Valor/Peça", "Subtotal"]]
        for it in itens_norm:
            table_data.append([
                it["tam"],
                str(it["qtd"]),
                str(it["piloto"]),
                fmt_moeda(it["valor_peca"]),
                fmt_moeda(it["subtotal"]),
            ])

        col_widths = [18 * mm, 16 * mm, 16 * mm, 28 * mm, 28 * mm]
        row_heights = [6 * mm] + [4.6 * mm] * (len(table_data) - 1)

        itens_tbl = Table(table_data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
        itens_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, 0), 2),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 2),

            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D0D0D0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            ("ALIGN", (1, 1), (2, -1), "CENTER"),
            ("ALIGN", (3, 1), (4, -1), "RIGHT"),

            ("LEFTPADDING", (0, 1), (-1, -1), 3),
            ("RIGHTPADDING", (0, 1), (-1, -1), 3),
            ("TOPPADDING", (0, 1), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 1),

            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
        ]))
        story.append(itens_tbl)
        story.append(Spacer(1, 2.5 * mm))

        total_tbl = Table(
            [[Paragraph("TOTAL GERAL:", style_value), Paragraph(fmt_moeda(total_geral), style_total)]],
            colWidths=[doc.width * 0.7, doc.width * 0.3]
        )
        total_tbl.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 1.0, colors.HexColor("#222222")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(total_tbl)
        story.append(Spacer(1, 3 * mm))

        story.append(text_box_compacto("Aviamentos", campos_texto.get("aviamentos", "")))
        story.append(Spacer(1, 2 * mm))
        story.append(text_box_compacto("Outros", campos_texto.get("outros", "")))
        story.append(Spacer(1, 2 * mm))
        story.append(text_box_compacto("Observações", campos_texto.get("observacoes", "")))
        story.append(Spacer(1, 3 * mm))

        nome_prest = (_t(prestador.get("nome")) or "").strip()
        if not nome_prest:
            nome_prest = "______________________________"

        assin_tbl = Table(
            [
                ["Assinatura do Prestador", "Assinatura da Empresa"],
                ["______________________________", "______________________________"],
                [f"Nome: {nome_prest}", f"Nome: {empresa_nome}"],
                ["Data: ____/____/________", "Data: ____/____/________"],
            ],
            colWidths=[doc.width * 0.5, doc.width * 0.5],
            rowHeights=[5 * mm, 7 * mm, 5 * mm, 5 * mm]
        )
        assin_tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),

            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),

            ("ALIGN", (0, 1), (-1, 1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("LINEABOVE", (0, 0), (-1, 0), 1.0, colors.HexColor("#222222")),
            ("BOX", (0, 0), (0, -1), 0.6, colors.HexColor("#D0D0D0")),
            ("BOX", (1, 0), (1, -1), 0.6, colors.HexColor("#D0D0D0")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FAFAFA")),

            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(assin_tbl)

        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("Documento gerado automaticamente pelo Sistema Guimma.", style_small))

        doc.build(story, onFirstPage=build_footer, onLaterPages=build_footer)

        if abrir_pdf:
            _open_pdf(caminho_pdf)

        return caminho_pdf


    def _abrir_janela_envio_defeito(self, dados, origem, status):
        values = list(dados["values"])
        if len(values) < 8:
            values.extend([""] * (8 - len(values)))
        data, envio_id, codigo, desc, prestador, tamanho, qtd, servico = values[:8]

        envio_id_num = int(envio_id) if str(envio_id).isdigit() else None
        envio_info = self._carregar_info_envio(envio_id_num)
        prestador_info = self._carregar_info_prestador(envio_info.get("prestador_id"), prestador)

        janela = ctk.CTkToplevel(self)
        janela.title("Pré-visualização do envio de defeito")
        janela.resizable(True, True)

        # comportamento de modal
        try:
            janela.transient(self.winfo_toplevel())
        except Exception:
            pass
        janela.grab_set()
        janela.focus_force()
        janela.lift()

        # layout: área rolável + barra de botões fixa (evita cortar)
        janela.grid_rowconfigure(0, weight=1)
        janela.grid_rowconfigure(1, weight=0)
        janela.grid_columnconfigure(0, weight=1)

        body = ctk.CTkScrollableFrame(janela, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=14, pady=(14, 8))
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)

        def _add_row(label, value, row):
            ctk.CTkLabel(body, text=label, text_color=self.cor_texto).grid(
                row=row, column=0, sticky="w", padx=(0, 10), pady=4
            )
            lbl = ctk.CTkLabel(body, text=value, text_color=self.cor_texto)
            lbl.grid(row=row, column=1, sticky="w", pady=4)

        row = 0
        _add_row("Prestador:", prestador, row); row += 1
        _add_row("Código:", codigo, row); row += 1
        _add_row("Descrição:", desc, row); row += 1
        _add_row("Tamanho:", tamanho, row); row += 1
        _add_row("Quantidade:", qtd, row); row += 1
        _add_row("Serviço:", servico, row); row += 1

        # Data envio
        ctk.CTkLabel(body, text="Data Envio:", text_color=self.cor_texto).grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=4
        )
        data_envio_entry = ctk.CTkEntry(body, width=160)
        data_envio_entry.insert(0, self._format_date(envio_info.get("data_envio") or datetime.now().date()))
        data_envio_entry.grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        # Previsão entrega + calendário
        ctk.CTkLabel(body, text="Previsão Entrega:", text_color=self.cor_texto).grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=4
        )
        previsao_frame = ctk.CTkFrame(body, fg_color="transparent")
        previsao_frame.grid(row=row, column=1, sticky="w", pady=4)
        previsao_entry = ctk.CTkEntry(previsao_frame, width=160)
        previsao_entry.insert(0, self._format_date(envio_info.get("previsao_entrega")))
        previsao_entry.pack(side="left")
        ctk.CTkButton(
            previsao_frame,
            text="📅",
            width=36,
            command=lambda: self._abrir_calendario(previsao_entry, parent=janela),
        ).pack(side="left", padx=(6, 0))
        previsao_entry.bind("<Double-Button-1>", lambda e: self._abrir_calendario(previsao_entry, parent=janela))
        row += 1

        # Valor/peça
        ctk.CTkLabel(body, text="Valor/Peça:", text_color=self.cor_texto).grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=4
        )
        valor_entry = ctk.CTkEntry(body, width=160)
        valor_entry.insert(0, f"{self._valor_peca_atual():.2f}")
        valor_entry.grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        # Telefones
        ctk.CTkLabel(body, text="Tel. Encarregado:", text_color=self.cor_texto).grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=4
        )
        tel_encarregado_entry = ctk.CTkEntry(body)
        tel_encarregado_entry.insert(0, envio_info.get("tel_encarregado") or "")
        tel_encarregado_entry.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        ctk.CTkLabel(body, text="Tel. Acabamento:", text_color=self.cor_texto).grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=4
        )
        tel_acabamento_entry = ctk.CTkEntry(body)
        tel_acabamento_entry.insert(0, envio_info.get("tel_acabamento") or "")
        tel_acabamento_entry.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        # Textos (com largura elástica)
        ctk.CTkLabel(body, text="Aviamentos:", text_color=self.cor_texto).grid(
            row=row, column=0, sticky="nw", padx=(0, 10), pady=4
        )
        aviamentos_text = ctk.CTkTextbox(body, height=70)
        aviamentos_text.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        ctk.CTkLabel(body, text="Outros:", text_color=self.cor_texto).grid(
            row=row, column=0, sticky="nw", padx=(0, 10), pady=4
        )
        outros_text = ctk.CTkTextbox(body, height=70)
        outros_text.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        ctk.CTkLabel(body, text="Observações:", text_color=self.cor_texto).grid(
            row=row, column=0, sticky="nw", padx=(0, 10), pady=4
        )
        observacoes_text = ctk.CTkTextbox(body, height=90)
        observacoes_text.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        def _coletar_pdf_data():
            try:
                valor = float((valor_entry.get() or "0").replace(",", "."))
            except Exception:
                valor = 0.0

            defeito_info = {
                "codigo": codigo,
                "descricao": desc,
                "prestador": prestador,
                "tamanho": tamanho,
                "quantidade": int(qtd) if str(qtd).isdigit() else 0,
                "valor_peca": valor,
                "data_envio": self._parse_date(data_envio_entry.get()),
                "previsao_entrega": self._parse_date(previsao_entry.get()),
                "tel_encarregado": tel_encarregado_entry.get(),
                "tel_acabamento": tel_acabamento_entry.get(),
                "aviamentos": aviamentos_text.get("1.0", "end-1c"),
                "outros": outros_text.get("1.0", "end-1c"),
                "observacoes": observacoes_text.get("1.0", "end-1c"),
            }
            meta = {
                "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "empresa_nome": "Sistema Guimma",
                "logo_path": "LOGO.jpg",
            }
            return self._montar_dados_pdf_defeito(
                defeito_info,
                prestador_info=prestador_info,
                envio_info=envio_info,
                extras={"meta": meta},
            ), defeito_info

        def _pre_visualizar():
            try:
                dados_pdf, _ = _coletar_pdf_data()
                self._gerar_pdf_defeito(dados=dados_pdf, abrir_pdf=True)
            except Exception as err:
                messagebox.showerror("Erro", f"Falha ao gerar pré-visualização:\n{err}")

        def _confirmar_envio():
            _, defeito_info = _coletar_pdf_data()
            self._registrar_defeito(
                dados,
                origem=origem,
                status=status,
                data_envio=defeito_info.get("data_envio"),
                valor_peca=defeito_info.get("valor_peca"),
                previsao_entrega=defeito_info.get("previsao_entrega"),
                tel_encarregado=defeito_info.get("tel_encarregado"),
                tel_acabamento=defeito_info.get("tel_acabamento"),
                aviamentos=defeito_info.get("aviamentos"),
                outros=defeito_info.get("outros"),
                observacoes=defeito_info.get("observacoes"),
            )
            janela.destroy()
            messagebox.showinfo("Sucesso", "Defeito enviado com sucesso.")

        botoes = ctk.CTkFrame(janela, fg_color="transparent")
        botoes.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
        botoes.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            botoes, text="Pré-visualizar", command=_pre_visualizar,
            fg_color=self.cor_alerta, hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            botoes, text="Enviar", command=_confirmar_envio,
            fg_color=self.cor_sucesso, hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            botoes, text="Cancelar", command=janela.destroy,
            fg_color=self.cor_destaque, hover_color=self.cor_hover,
            text_color=self.cor_texto
        ).pack(side="left", padx=6)

        # Ajusta tamanho e centraliza (sem sair da tela). Se precisar, rola o conteúdo sem cortar.
        janela.update_idletasks()
        sw = janela.winfo_screenwidth()
        sh = janela.winfo_screenheight()
        req_w = max(720, janela.winfo_reqwidth())
        req_h = max(520, janela.winfo_reqheight())
        w = min(req_w + 30, int(sw * 0.92))
        h = min(req_h + 30, int(sh * 0.90))
        self._centralizar_toplevel(janela, w, h, parent=self.winfo_toplevel())


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
                f"""
                UPDATE {schema}.defeitos_envios
                   SET status = %s,
                       data_retorno = CURRENT_DATE,
                       hora_retorno = CURRENT_TIME
                 WHERE id = %s
                """,
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
                f"""
                UPDATE {schema}.defeitos_envios
                   SET status = %s,
                       data_finalizacao = CURRENT_DATE,
                       hora_finalizacao = CURRENT_TIME
                 WHERE id = %s
                """,
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
            from reportlab.lib.pagesizes import A4  # noqa: F401
        except Exception:
            messagebox.showwarning("Aviso", "reportlab não está disponível para gerar a ficha.")
            return
        defeito_id = item[0]
        conn = None
        try:
            schema = get_schema()
            conn = get_conn()
            cur = conn.cursor()
            self._ensure_schema(cur)
            cur.execute(
                f"""
                SELECT envio_id, prestador, codigo, descricao, tamanho, quantidade, valor_peca,
                       data_envio, previsao_entrega, tel_encarregado, tel_acabamento,
                       aviamentos, outros, observacoes
                  FROM {schema}.defeitos_envios
                 WHERE id = %s
                """,
                (defeito_id,),
            )
            row = cur.fetchone()
            if not row:
                messagebox.showwarning("Aviso", "Defeito não encontrado.")
                return
            (envio_id, prestador, codigo, descricao, tamanho, qtd, valor_peca,
             data_envio, previsao_entrega, tel_encarregado, tel_acabamento,
             aviamentos, outros, observacoes) = row

            envio_info = self._carregar_info_envio(envio_id)
            prestador_info = self._carregar_info_prestador(envio_info.get("prestador_id"), prestador)
            defeito_info = {
                "codigo": codigo,
                "descricao": descricao,
                "prestador": prestador,
                "tamanho": tamanho,
                "quantidade": qtd,
                "valor_peca": valor_peca,
                "data_envio": data_envio,
                "previsao_entrega": previsao_entrega,
                "tel_encarregado": tel_encarregado,
                "tel_acabamento": tel_acabamento,
                "aviamentos": aviamentos,
                "outros": outros,
                "observacoes": observacoes,
            }
            dados_pdf = self._montar_dados_pdf_defeito(
                defeito_info,
                prestador_info=prestador_info,
                envio_info=envio_info,
                extras={
                    "meta": {
                        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "empresa_nome": "Sistema Guimma",
                        "logo_path": "LOGO.jpg",
                    }
                },
            )
            self._abrir_janela_impressao(defeito_id, dados_pdf)
        except Exception as err:
            messagebox.showerror("Erro", f"Falha ao gerar ficha:\n{err}")
        finally:
            if conn:
                conn.close()

    def _abrir_janela_impressao(self, defeito_id, dados_pdf):
        janela = ctk.CTkToplevel(self)
        janela.title("Imprimir ficha de defeito")
        janela.geometry("420x180")
        janela.grab_set()

        ctk.CTkLabel(
            janela,
            text="Escolha a ação para a ficha de defeito:",
            text_color=self.cor_texto,
            font=("Roboto", 12, "bold"),
        ).pack(pady=(16, 8))

        def _pre_visualizar():
            try:
                self._gerar_pdf_defeito(dados=dados_pdf, abrir_pdf=True)
            except Exception as err:
                messagebox.showerror("Erro", f"Falha ao abrir pré-visualização:\n{err}")

        def _salvar_pdf():
            caminho = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=f"ficha_defeito_{defeito_id}.pdf",
            )
            if not caminho:
                return
            try:
                self._gerar_pdf_defeito(caminho_pdf=caminho, dados=dados_pdf, abrir_pdf=False)
                messagebox.showinfo("Sucesso", f"Ficha salva em: {caminho}")
            except Exception as err:
                messagebox.showerror("Erro", f"Falha ao salvar ficha:\n{err}")

        botoes = ctk.CTkFrame(janela, fg_color="transparent")
        botoes.pack(pady=12)
        ctk.CTkButton(botoes, text="Pré-visualizar", command=_pre_visualizar,
                      fg_color=self.cor_alerta, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=6)
        ctk.CTkButton(botoes, text="Salvar PDF", command=_salvar_pdf,
                      fg_color=self.cor_sucesso, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=6)
        ctk.CTkButton(botoes, text="Fechar", command=janela.destroy,
                      fg_color=self.cor_destaque, hover_color=self.cor_hover,
                      text_color=self.cor_texto).pack(side="left", padx=6)


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

#03/02/2025

# --- Suporte trilíngue individual desta página ---
RetrabalhoDefeitosPage_TRANSLATIONS = {
    "pt_BR": {
        "title": "Retrabalho de Defeitos",
        "Atualizar": "Atualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
    },
    "en_US": {
        "title": "Defect Rework",
        "Atualizar": "Refresh",
        "Filtrar": "Filter",
        "Limpar": "Clear",
        "Exportar": "Export",
        "Imprimir": "Print",
        "Buscar": "Search",
    },
    "es_ES": {
        "title": "Retrabajo de Defectos",
        "Atualizar": "Actualizar",
        "Filtrar": "Filtrar",
        "Limpar": "Limpiar",
        "Exportar": "Exportar",
        "Imprimir": "Imprimir",
        "Buscar": "Buscar",
    },
}


def _apply_retrabalhodefeitospage_translations(self):
    """Aplica tradução individual desta página."""
    idioma = getattr(getattr(self, "sistema", None), "idioma_atual", getattr(self, "idioma_atual", "pt_BR"))
    if idioma not in RetrabalhoDefeitosPage_TRANSLATIONS:
        idioma = "pt_BR"
    if hasattr(self, "titulo"):
        try:
            self.titulo.configure(text=RetrabalhoDefeitosPage_TRANSLATIONS[idioma]["title"])
        except Exception:
            pass


try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    RetrabalhoDefeitosPage.TRANSLATIONS = RetrabalhoDefeitosPage_TRANSLATIONS
    if not hasattr(RetrabalhoDefeitosPage, "apply_page_translations"):
        RetrabalhoDefeitosPage.apply_page_translations = _apply_retrabalhodefeitospage_translations
    attach_i18n_support(RetrabalhoDefeitosPage, RetrabalhoDefeitosPage_TRANSLATIONS)
except Exception:
    pass
