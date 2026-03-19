# -*- coding: utf-8 -*-
"""
RELATORIO_CUSTOS_REAIS.py - Relatório de Custos Reais
Interface base para análise de custos planejados x realizados.
"""
from datetime import datetime
import os
import webbrowser
from tkinter import messagebox, ttk

import customtkinter as ctk
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready


class RelatorioCustosReaisPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.tree_categoria = None
        self.tree_ops = None
        self.kpi_labels = []
        self.filtro_modelo = None
        self.filtro_status = None
        self._build()
        self._carregar_dados_custos()

    def _build(self):
        self.configure(fg_color="transparent")
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_filters()
        self._build_body()

    # JESUS SEJA LOUVADO PARA TODO O SEMPRE AMEM!!!
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Relatório de Custos Reais", font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Comparativo de custos planejados e realizados por OP e categoria.",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(4, weight=1)

        ctk.CTkButton(toolbar, text="Atualizar", command=self._carregar_dados_custos).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(toolbar, text="Exportar PDF", command=self._exportar_custos).grid(
            row=0, column=1, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Imprimir", command=self._imprimir_custos).grid(
            row=0, column=2, padx=(0, 8)
        )
        ctk.CTkButton(toolbar, text="Comparar OPs", command=self._comparar_ops).grid(row=0, column=3)

    def _build_filters(self):
        filters = ctk.CTkFrame(self)
        filters.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 12))
        filters.grid_columnconfigure(9, weight=1)

        ctk.CTkLabel(filters, text="Período").grid(row=0, column=0, padx=(12, 6), pady=8)
        self.custos_inicio_entry = ctk.CTkEntry(filters, placeholder_text="De")
        self.custos_inicio_entry.grid(row=0, column=1, padx=(0, 6), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.custos_inicio_entry),
        ).grid(row=0, column=2, padx=(0, 6), pady=8)
        self.custos_fim_entry = ctk.CTkEntry(filters, placeholder_text="Até")
        self.custos_fim_entry.grid(row=0, column=3, padx=(0, 12), pady=8)
        ctk.CTkButton(
            filters,
            text="📅",
            width=32,
            command=lambda: self._abrir_calendario(self.custos_fim_entry),
        ).grid(row=0, column=4, padx=(0, 12), pady=8)
        ctk.CTkLabel(filters, text="Modelo").grid(row=0, column=5, padx=(0, 6), pady=8)
        self.filtro_modelo = ctk.CTkEntry(filters, placeholder_text="Buscar modelo")
        self.filtro_modelo.grid(
            row=0, column=6, padx=(0, 12), pady=8
        )
        ctk.CTkLabel(filters, text="Status").grid(row=0, column=7, padx=(0, 6), pady=8)
        self.filtro_status = ctk.CTkOptionMenu(filters, values=["Todos", "Em produção", "Finalizado"])
        self.filtro_status.grid(
            row=0, column=8, padx=(0, 12), pady=8
        )
        ctk.CTkButton(filters, text="Filtrar", command=self._carregar_dados_custos).grid(row=0, column=9, padx=(0, 12), pady=8)

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 24))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        kpis = ctk.CTkFrame(body)
        kpis.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        kpis.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for idx, text in enumerate(
            [
                "Custo planejado: R$ 0,00",
                "Custo real: R$ 0,00",
                "Variação: 0,0%",
                "Margem estimada: R$ 0,00",
            ]
        ):
            card = ctk.CTkFrame(kpis)
            card.grid(row=0, column=idx, padx=6, sticky="ew")
            label = ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=12, weight="bold"))
            label.pack(
                pady=12
            )
            self.kpi_labels.append(label)

        comparativo_frame = ctk.CTkFrame(body)
        comparativo_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        comparativo_frame.grid_columnconfigure(0, weight=1)
        comparativo_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            comparativo_frame, text="Comparativo por Categoria", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.tree_categoria = ttk.Treeview(
            comparativo_frame,
            columns=("categoria", "planejado", "real", "variacao"),
            show="headings",
            height=12,
        )
        for col, text, width in (
            ("categoria", "Categoria", 200),
            ("planejado", "Planejado", 120),
            ("real", "Real", 120),
            ("variacao", "Variação", 100),
        ):
            self.tree_categoria.heading(col, text=text)
            self.tree_categoria.column(col, width=width)
        self.tree_categoria.column("planejado", anchor="e")
        self.tree_categoria.column("real", anchor="e")
        self.tree_categoria.column("variacao", anchor="e")

        tree_scroll = ttk.Scrollbar(comparativo_frame, orient="vertical", command=self.tree_categoria.yview)
        self.tree_categoria.configure(yscrollcommand=tree_scroll.set)
        self.tree_categoria.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        tree_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16))

        detalhe_frame = ctk.CTkFrame(body)
        detalhe_frame.grid(row=1, column=1, sticky="nsew")
        detalhe_frame.grid_columnconfigure(0, weight=1)
        detalhe_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            detalhe_frame, text="Detalhes por OP", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.tree_ops = ttk.Treeview(
            detalhe_frame,
            columns=("op", "modelo", "planejado", "real"),
            show="headings",
            height=10,
        )
        for col, text, width in (
            ("op", "OP", 90),
            ("modelo", "Modelo", 160),
            ("planejado", "Planejado", 110),
            ("real", "Real", 110),
        ):
            self.tree_ops.heading(col, text=text)
            self.tree_ops.column(col, width=width)
        self.tree_ops.column("planejado", anchor="e")
        self.tree_ops.column("real", anchor="e")

        detalhe_scroll = ttk.Scrollbar(detalhe_frame, orient="vertical", command=self.tree_ops.yview)
        self.tree_ops.configure(yscrollcommand=detalhe_scroll.set)
        self.tree_ops.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 16))
        detalhe_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 16))

    @staticmethod
    def _to_float(valor):
        try:
            return float(valor or 0)
        except Exception:
            return 0.0

    def _parse_data(self, texto):
        if not texto:
            return None
        try:
            return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
        except Exception:
            return None

    def _limpar_tree(self, tree):
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)

    def _carregar_dados_custos(self):
        self._limpar_tree(self.tree_categoria)
        self._limpar_tree(self.tree_ops)

        ok, _ = require_ready()
        if not ok:
            return

        inicio = self._parse_data(self.custos_inicio_entry.get())
        fim = self._parse_data(self.custos_fim_entry.get())
        modelo = (self.filtro_modelo.get().strip() if self.filtro_modelo else "")
        status_filtro = (self.filtro_status.get() if self.filtro_status else "Todos") or "Todos"

        filtros_ops = []
        params_ops = []
        if inicio:
            filtros_ops.append("data_ref >= %s")
            params_ops.append(inicio)
        if fim:
            filtros_ops.append("data_ref <= %s")
            params_ops.append(fim)
        if modelo:
            filtros_ops.append("modelo ILIKE %s")
            params_ops.append(f"%{modelo}%")
        if status_filtro == "Em produção":
            filtros_ops.append("status_ref IN ('Em Andamento', 'Em execução', 'Planejada')")
        elif status_filtro == "Finalizado":
            filtros_ops.append("status_ref IN ('Finalizado', 'Finalizada')")

        where_ops = ("WHERE " + " AND ".join(filtros_ops)) if filtros_ops else ""

        try:
            schema = get_schema()
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT categoria,
                               SUM(valor_planejado) AS valor_planejado,
                               SUM(valor_real) AS valor_real,
                               CASE WHEN SUM(valor_planejado) > 0
                                    THEN ((SUM(valor_real) - SUM(valor_planejado)) / SUM(valor_planejado)) * 100
                                    ELSE 0 END AS variacao
                          FROM (
                                SELECT 'Tecidos' AS categoria,
                                       SUM(COALESCE(valor_total, 0)) AS valor_planejado,
                                       SUM(COALESCE(valor_total, 0)) AS valor_real
                                  FROM {schema}.cadastro_modelos_tecidos
                                UNION ALL
                                SELECT 'Aviamentos' AS categoria,
                                       SUM(COALESCE(valor_total, 0)) AS valor_planejado,
                                       SUM(COALESCE(valor_total, 0)) AS valor_real
                                  FROM {schema}.cadastro_modelos_aviamentos
                                UNION ALL
                                SELECT 'Outros Insumos' AS categoria,
                                       SUM(COALESCE(valor_total, 0)) AS valor_planejado,
                                       SUM(COALESCE(valor_total, 0)) AS valor_real
                                  FROM {schema}.cadastro_modelos_outros
                                UNION ALL
                                SELECT 'Serviços Externos' AS categoria,
                                       SUM(COALESCE(valor_total, 0)) AS valor_planejado,
                                       SUM(COALESCE(valor_total, 0)) AS valor_real
                                  FROM {schema}.cadastro_modelos_outros_servicos
                               ) x
                         GROUP BY categoria
                         ORDER BY categoria
                        """
                    )
                    categorias = cur.fetchall()

                    cur.execute(
                        f"""
                        SELECT op,
                               modelo,
                               valor_planejado,
                               valor_real,
                               status_ref
                          FROM (
                                SELECT COALESCE(op, '') AS op,
                                       COALESCE(modelo, '') AS modelo,
                                       COALESCE(valor_planejado, 0) AS valor_planejado,
                                       COALESCE(valor_real, 0) AS valor_real,
                                       'Planejada'::text AS status_ref,
                                       data_atualizacao::date AS data_ref
                                  FROM {schema}.custos_reais_ops
                                UNION ALL
                                SELECT CONCAT('OC-', o.id) AS op,
                                       COALESCE(o.descricao_modelo, o.codigo_modelo, 'Modelo sem descrição') AS modelo,
                                       COALESCE(m.gasto_total_por_peca, m.custo_total, 0) * COALESCE(o.quantidade_desejada, 0) AS valor_planejado,
                                       COALESCE(m.gasto_total_por_peca, m.custo_total, 0) * COALESCE(NULLIF(o.total_pecas, 0), o.quantidade_desejada, 0) AS valor_real,
                                       COALESCE(o.status, 'Em Andamento') AS status_ref,
                                       COALESCE(o.data_registro::date, CURRENT_DATE) AS data_ref
                                  FROM {schema}.ordem_corte_ficha o
                             LEFT JOIN {schema}.cadastro_modelos_cabecalho m
                                    ON UPPER(TRIM(COALESCE(m.codigo, ''))) = UPPER(TRIM(COALESCE(o.codigo_modelo, '')))
                                 WHERE COALESCE(o.ativo, TRUE) = TRUE
                               ) dados
                          {where_ops}
                         ORDER BY op
                        """,
                        params_ops,
                    )
                    ops = cur.fetchall()

            total_planejado = 0.0
            total_real = 0.0

            for categoria, planejado, real, variacao in categorias:
                total_planejado += self._to_float(planejado)
                total_real += self._to_float(real)
                self.tree_categoria.insert(
                    "",
                    "end",
                    values=(categoria, f"R$ {self._to_float(planejado):,.2f}", f"R$ {self._to_float(real):,.2f}", f"{self._to_float(variacao):,.2f}%"),
                )

            for op, modelo_op, planejado, real, _status in ops:
                self.tree_ops.insert(
                    "",
                    "end",
                    values=(op, modelo_op, f"R$ {self._to_float(planejado):,.2f}", f"R$ {self._to_float(real):,.2f}"),
                )

            variacao_pct = ((total_real - total_planejado) / total_planejado * 100) if total_planejado > 0 else 0
            margem = total_planejado - total_real

            if self.kpi_labels:
                self.kpi_labels[0].configure(text=f"Custo planejado: R$ {total_planejado:,.2f}")
                self.kpi_labels[1].configure(text=f"Custo real: R$ {total_real:,.2f}")
                self.kpi_labels[2].configure(text=f"Variação: {variacao_pct:.1f}%")
                self.kpi_labels[3].configure(text=f"Margem estimada: R$ {margem:,.2f}")
        except Exception as exc:
            messagebox.showerror("Custos Reais", f"Erro ao carregar custos reais: {exc}")

    def _comparar_ops(self):
        if not self.tree_ops or not self.tree_ops.get_children():
            messagebox.showinfo("Comparar OPs", "Sem dados para comparar.\nDica: gere uma Ordem de Corte em NOVA_ORDEM para simular custos.")
            return

        maior_desvio = None
        maior_valor = float("-inf")
        for item in self.tree_ops.get_children():
            op, modelo, planejado, real = self.tree_ops.item(item).get("values", ["", "", "0", "0"])
            p = self._to_float(str(planejado).replace("R$", "").replace(" ", "").replace(".", "").replace(",", "."))
            r = self._to_float(str(real).replace("R$", "").replace(" ", "").replace(".", "").replace(",", "."))
            desvio = r - p
            if desvio > maior_valor:
                maior_valor = desvio
                maior_desvio = (op, modelo, desvio)

        if maior_desvio:
            messagebox.showinfo(
                "Comparar OPs",
                f"Maior desvio encontrado:\nOP {maior_desvio[0]} - {maior_desvio[1]}\nDesvio: R$ {maior_desvio[2]:,.2f}",
            )

    def _exportar_custos(self):
        try:
            caminho = self._gerar_pdf_custos()
            self._abrir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("Custos Reais", f"Erro ao exportar PDF: {exc}")

    def _imprimir_custos(self):
        try:
            caminho = self._gerar_pdf_custos()
            self._imprimir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("Custos Reais", f"Erro ao imprimir: {exc}")

    def _gerar_pdf_custos(self):
        nome = f"custos_reais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        caminho = os.path.abspath(nome)
        c = canvas.Canvas(caminho, pagesize=A4)
        largura, altura = A4
        y = self._desenhar_cabecalho_pdf(c, largura, altura, "Relatório de Custos Reais")

        def escrever_titulo(titulo):
            nonlocal y
            c.setFont("Helvetica-Bold", 11)
            c.drawString(40, y, titulo)
            y -= 16
            c.setFont("Helvetica", 9)

        def escrever_linhas(linhas):
            nonlocal y
            for linha in linhas:
                if y < 80:
                    c.showPage()
                    y = altura - 60
                c.drawString(40, y, linha)
                y -= 12

        if self.tree_categoria:
            escrever_titulo("Comparativo por Categoria")
            linhas = []
            for item in self.tree_categoria.get_children():
                vals = self.tree_categoria.item(item)["values"]
                linhas.append(f"- {vals[0]} | Planejado {vals[1]} | Real {vals[2]} | Var {vals[3]}")
            escrever_linhas(linhas or ["Sem dados."])
            y -= 8

        if self.tree_ops:
            escrever_titulo("Detalhes por OP")
            linhas = []
            for item in self.tree_ops.get_children():
                vals = self.tree_ops.item(item)["values"]
                linhas.append(f"- OP {vals[0]} | {vals[1]} | Planejado {vals[2]} | Real {vals[3]}")
            escrever_linhas(linhas or ["Sem dados."])

        c.save()
        return caminho

    def _desenhar_cabecalho_pdf(self, c, largura, altura, titulo):
        header_h = 64
        c.setFillColor(colors.HexColor("#1F5FA6"))
        c.rect(0, altura - header_h, largura, header_h, fill=1, stroke=0)

        logo_path = os.path.join(os.path.dirname(__file__), "LOGO.jpg")
        x_text = 40
        if os.path.exists(logo_path):
            try:
                c.drawImage(logo_path, 24, altura - 52, width=30, height=30, preserveAspectRatio=True, mask='auto')
                x_text = 62
            except Exception:
                pass

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x_text, altura - 34, titulo)
        c.setFont("Helvetica", 9)
        c.drawString(x_text, altura - 49, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        c.setFillColor(colors.HexColor("#666666"))
        c.setFont("Helvetica", 8)
        c.drawString(24, 18, "SISTEMA OPERA — Impressão")
        return altura - header_h - 12

    def _abrir_pdf(self, caminho):
        try:
            webbrowser.open_new_tab("file://" + caminho)
        except Exception:
            if hasattr(os, "startfile"):
                os.startfile(caminho)  # type: ignore[attr-defined]

    def _imprimir_pdf(self, caminho):
        if hasattr(os, "startfile"):
            try:
                os.startfile(caminho, "print")  # type: ignore[attr-defined]
                return
            except Exception:
                pass
        self._abrir_pdf(caminho)
        messagebox.showinfo("Custos Reais", "PDF aberto no navegador. Use Ctrl+P para imprimir.")

    def _abrir_calendario(self, entry):
        from datetime import datetime as _dt
        import calendar as _cal

        def setar_data(d):
            entry.delete(0, "end")
            entry.insert(0, d.strftime("%d/%m/%Y"))
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
        top.transient(self)
        top.grab_set()

        now = _dt.now()
        ano = now.year
        mes = now.month

        nav = ctk.CTkFrame(top)
        nav.pack(fill="x", padx=10, pady=5)

        lbl_mes = ctk.CTkLabel(nav, text=f"{_cal.month_name[mes]} {ano}", font=("Arial", 14))
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
            lbl_mes.configure(text=f"{_cal.month_name[mes]} {ano}")
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
                        command=lambda d=dia: setar_data(_dt(ano, mes, d)),
                    )
                    btn.grid(row=i + 1, column=j, padx=2, pady=2)

        desenhar_calendario()


if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Custos Reais - Teste")
    app.geometry("1200x720")
    page = RelatorioCustosReaisPage(master=app)
    page.pack(fill="both", expand=True)
    app.mainloop()


# --- Adaptador global de idioma (injeção automática) ---
try:
    from PAGINAS_DO_SISTEMA.I18N_PAGE_ADAPTER import attach_i18n_support
    attach_i18n_support(RelatorioCustosReaisPage)
except Exception:
    pass
