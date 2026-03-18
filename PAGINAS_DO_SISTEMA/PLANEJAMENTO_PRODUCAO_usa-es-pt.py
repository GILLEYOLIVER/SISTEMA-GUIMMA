# -*- coding: utf-8 -*-
"""
PLANEJAMENTO_PRODUCAO.py - Planejamento de Produção
Nova versão focada em programação de OPs a partir dos modelos cadastrados,
com cálculo de tecidos e aviamentos e comparação com estoque.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import os
import webbrowser
from decimal import Decimal
from tkinter import messagebox, ttk
import tkinter as tk

import customtkinter as ctk

try:
    from tkcalendar import Calendar
except Exception:
    Calendar = None
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready


TAMANHOS_GRADE = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]
PROGRAMACOES = ["Semanal", "Mensal", "Trimestral", "Semestral", "Coleção"]
PRIORIDADES = ["Baixa", "Média", "Alta", "Urgente"]


class PlanejamentoProducaoPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.tree_ops = None
        self.tree_capacidade = None
        self.tree_tecidos = None
        self.tree_aviamentos = None
        self.kpi_labels = []
        self.ops_index = {}
        self.detalhe_labels = {}
        self.modelos_cache = []
        self._calendar_popup = None

        self.cor_fundo = getattr(sistema, "cor_fundo", "#F5F5F5")
        self.cor_primaria = getattr(sistema, "cor_primaria", "#3A7EBF")
        self.cor_secundaria = getattr(sistema, "cor_secundaria", "#E5E7EB")
        self.cor_texto = getattr(sistema, "cor_texto", "#111827")
        self.cor_hover = getattr(sistema, "cor_hover", "#2E4A66")
        self.cor_borda = getattr(sistema, "cor_borda", "#CBD5E1")
        self.cor_sucesso = getattr(sistema, "cor_sucesso", "#16A34A")
        self.cor_alerta = getattr(sistema, "cor_alerta", "#DC2626")
        self.cor_destaque = getattr(sistema, "cor_destaque", "#2563EB")

        self.configure(fg_color=self.cor_fundo)
        self._build()
        self._garantir_estrutura_planejamento()
        self._carregar_modelos_cache()
        self._carregar_dados_planejamento()

    # =========================================================
    # Construção da interface
    # =========================================================
    def _build(self):
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_header()
        self._build_toolbar()
        self._build_filters()
        self._build_body()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=self.cor_fundo, border_color=self.cor_borda, border_width=1)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Planejamento de Produção",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.cor_texto,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(
            header,
            text="Crie OPs por período, modelo, grade e prioridade. Os materiais são calculados a partir do cadastro do modelo.",
            font=ctk.CTkFont(size=12),
            text_color=self.cor_texto,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        toolbar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        toolbar.grid_columnconfigure(5, weight=1)

        ctk.CTkButton(
            toolbar,
            text="Nova Programação",
            command=self._abrir_dialogo_nova_programacao,
            fg_color=self.cor_sucesso,
            hover_color=self._hover(self.cor_sucesso),
            text_color="white",
        ).grid(row=0, column=0, padx=(0, 8), pady=4)

        ctk.CTkButton(
            toolbar,
            text="Atualizar",
            command=self._carregar_dados_planejamento,
            fg_color=self.cor_primaria,
            hover_color=self._hover(self.cor_primaria),
            text_color="white",
        ).grid(row=0, column=1, padx=(0, 8), pady=4)

        ctk.CTkButton(
            toolbar,
            text="Reprogramar +1 dia",
            command=self._reprogramar,
            fg_color=self.cor_destaque,
            hover_color=self._hover(self.cor_destaque),
            text_color="white",
        ).grid(row=0, column=2, padx=(0, 8), pady=4)

        ctk.CTkButton(
            toolbar,
            text="Exportar PDF",
            command=self._exportar_planejamento,
            fg_color="#EF4444",
            hover_color=self._hover("#EF4444"),
            text_color="white",
        ).grid(row=0, column=3, padx=(0, 8), pady=4)

        ctk.CTkButton(
            toolbar,
            text="Imprimir",
            command=self._imprimir_planejamento,
            fg_color="#F59E0B",
            hover_color=self._hover("#F59E0B"),
            text_color="white",
        ).grid(row=0, column=4, padx=(0, 8), pady=4)

    def _build_filters(self):
        filters = ctk.CTkFrame(self, fg_color=self.cor_fundo)
        filters.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 8))
        filters.grid_columnconfigure(12, weight=1)

        ctk.CTkLabel(filters, text="Período", text_color=self.cor_texto).grid(row=0, column=0, padx=(4, 6), pady=6)
        self.plan_inicio_entry = ctk.CTkEntry(filters, placeholder_text="De", width=135)
        self.plan_inicio_entry.grid(row=0, column=1, padx=(0, 4), pady=6)
        ctk.CTkButton(filters, text="📅", width=32, command=lambda: self._abrir_calendario(self.plan_inicio_entry)).grid(row=0, column=2, padx=(0, 8), pady=6)
        self.plan_fim_entry = ctk.CTkEntry(filters, placeholder_text="Até", width=135)
        self.plan_fim_entry.grid(row=0, column=3, padx=(0, 4), pady=6)
        ctk.CTkButton(filters, text="📅", width=32, command=lambda: self._abrir_calendario(self.plan_fim_entry)).grid(row=0, column=4, padx=(0, 10), pady=6)

        ctk.CTkLabel(filters, text="Coleção", text_color=self.cor_texto).grid(row=0, column=5, padx=(0, 6), pady=6)
        self.filtro_colecao = ctk.CTkComboBox(filters, values=["Todas"], width=160)
        self.filtro_colecao.set("Todas")
        self.filtro_colecao.grid(row=0, column=6, padx=(0, 10), pady=6)

        ctk.CTkLabel(filters, text="Prioridade", text_color=self.cor_texto).grid(row=0, column=7, padx=(0, 6), pady=6)
        self.filtro_prioridade = ctk.CTkOptionMenu(filters, values=["Todas"] + PRIORIDADES, width=130)
        self.filtro_prioridade.set("Todas")
        self.filtro_prioridade.grid(row=0, column=8, padx=(0, 10), pady=6)

        ctk.CTkLabel(filters, text="Programação", text_color=self.cor_texto).grid(row=0, column=9, padx=(0, 6), pady=6)
        self.filtro_programacao = ctk.CTkOptionMenu(filters, values=["Todas"] + PROGRAMACOES, width=150)
        self.filtro_programacao.set("Mensal")
        self.filtro_programacao.grid(row=0, column=10, padx=(0, 10), pady=6)

        ctk.CTkButton(filters, text="Filtrar", command=self._carregar_dados_planejamento, fg_color=self.cor_primaria, hover_color=self._hover(self.cor_primaria)).grid(row=0, column=12, padx=(0, 6), pady=6)

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 14))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        kpis = ctk.CTkFrame(body)
        kpis.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        kpis.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for idx, text in enumerate(["OPs em execução: 0", "Atrasos críticos: 0", "Capacidade usada: 0%", "Ociosidade: 0%"]):
            card = ctk.CTkFrame(kpis)
            card.grid(row=0, column=idx, padx=6, pady=6, sticky="ew")
            label = ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=13, weight="bold"), text_color=self.cor_texto)
            label.pack(pady=12)
            self.kpi_labels.append(label)

        ordens_frame = ctk.CTkFrame(body)
        ordens_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        ordens_frame.grid_columnconfigure(0, weight=1)
        ordens_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(ordens_frame, text="Programações / OPs", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

        self.tree_ops = ttk.Treeview(
            ordens_frame,
            columns=("op", "modelo", "qtde", "inicio", "fim", "status", "progresso", "programacao", "colecao"),
            show="headings",
            height=14,
        )
        for col, text, width in (
            ("op", "OP", 95),
            ("modelo", "Modelo", 250),
            ("qtde", "Qtde", 65),
            ("inicio", "Início", 80),
            ("fim", "Fim", 80),
            ("status", "Status", 80),
            ("progresso", "Progresso", 85),
            ("programacao", "Programação", 110),
            ("colecao", "Coleção", 95),
        ):
            self.tree_ops.heading(col, text=text)
            self.tree_ops.column(col, width=width, anchor="center")
        self.tree_ops.column("modelo", anchor="w")
        self.tree_ops.column("colecao", stretch=True)
        self.tree_ops.tag_configure("grupo", background="#DDE8F5", font=("Arial", 10, "bold"))
        self.tree_ops.tag_configure("op_andamento", background="#DDF5E3")
        self.tree_ops.tag_configure("op_falta", background="#FADDDD")
        self.tree_ops.tag_configure("op_concluida", background="#DDEBFF")
        self.tree_ops.bind("<Double-1>", self._abrir_detalhe_op)

        scroll_ops = ttk.Scrollbar(ordens_frame, orient="vertical", command=self.tree_ops.yview)
        self.tree_ops.configure(yscrollcommand=scroll_ops.set)
        self.tree_ops.grid(row=1, column=0, sticky="nsew", padx=(14, 0), pady=(0, 14))
        scroll_ops.grid(row=1, column=1, sticky="ns", pady=(0, 14))

        capacidade_frame = ctk.CTkFrame(body)
        capacidade_frame.grid(row=1, column=1, sticky="nsew")
        capacidade_frame.grid_columnconfigure(0, weight=1)
        capacidade_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(capacidade_frame, text="Resumo de Materiais", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

        self.tree_capacidade = ttk.Treeview(capacidade_frame, columns=("recurso", "carga", "capacidade", "ocioso"), show="headings", height=12)
        for col, text, width in (
            ("recurso", "Recurso", 125),
            ("carga", "Necessário", 100),
            ("capacidade", "Estoque", 100),
            ("ocioso", "Saldo", 80),
        ):
            self.tree_capacidade.heading(col, text=text)
            self.tree_capacidade.column(col, width=width, anchor="center")
        self.tree_capacidade.column("ocioso", stretch=True)
        scroll_cap = ttk.Scrollbar(capacidade_frame, orient="vertical", command=self.tree_capacidade.yview)
        self.tree_capacidade.configure(yscrollcommand=scroll_cap.set)
        self.tree_capacidade.grid(row=1, column=0, sticky="nsew", padx=(14, 0), pady=(0, 14))
        scroll_cap.grid(row=1, column=1, sticky="ns", pady=(0, 14))

        detalhe_frame = ctk.CTkFrame(body)
        detalhe_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        detalhe_frame.grid_columnconfigure(0, weight=1)
        detalhe_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(detalhe_frame, text="Detalhes da OP Selecionada", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 6))

        info = ctk.CTkFrame(detalhe_frame)
        info.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 8))
        info.grid_columnconfigure((0, 1, 2, 3), weight=1)
        for idx, chave in enumerate(("grade", "prazo", "modelo", "prioridade")):
            txt = {
                "grade": "Grade: -",
                "prazo": "Prazo início: -",
                "modelo": "Modelo: -",
                "prioridade": "Prioridade: -",
            }[chave]
            lbl = ctk.CTkLabel(info, text=txt, anchor="w")
            lbl.grid(row=0, column=idx, sticky="ew", padx=8, pady=8)
            self.detalhe_labels[chave] = lbl

        tecidos_frame = ctk.CTkFrame(detalhe_frame)
        tecidos_frame.grid(row=2, column=0, sticky="nsew", padx=(14, 7), pady=(0, 14))
        tecidos_frame.grid_columnconfigure(0, weight=1)
        tecidos_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(tecidos_frame, text="Tecidos necessários", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))
        self.tree_tecidos = ttk.Treeview(tecidos_frame, columns=("codigo", "descricao", "necessario", "estoque", "saldo", "status"), show="headings", height=6)
        for col, text, width in (
            ("codigo", "Código", 85),
            ("descricao", "Tecido", 200),
            ("necessario", "Necessário", 90),
            ("estoque", "Estoque", 90),
            ("saldo", "Saldo", 90),
            ("status", "Status", 90),
        ):
            self.tree_tecidos.heading(col, text=text)
            self.tree_tecidos.column(col, width=width, anchor="center")
        self.tree_tecidos.column("descricao", anchor="w")
        self.tree_tecidos.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        aviamentos_frame = ctk.CTkFrame(detalhe_frame)
        aviamentos_frame.grid(row=2, column=1, sticky="nsew", padx=(7, 14), pady=(0, 14))
        aviamentos_frame.grid_columnconfigure(0, weight=1)
        aviamentos_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(aviamentos_frame, text="Aviamentos necessários", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 6))
        self.tree_aviamentos = ttk.Treeview(aviamentos_frame, columns=("codigo", "descricao", "necessario", "estoque", "saldo", "status"), show="headings", height=6)
        for col, text, width in (
            ("codigo", "Código", 85),
            ("descricao", "Aviamento", 200),
            ("necessario", "Necessário", 90),
            ("estoque", "Estoque", 90),
            ("saldo", "Saldo", 90),
            ("status", "Status", 90),
        ):
            self.tree_aviamentos.heading(col, text=text)
            self.tree_aviamentos.column(col, width=width, anchor="center")
        self.tree_aviamentos.column("descricao", anchor="w")
        self.tree_aviamentos.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    # =========================================================
    # Banco / estrutura
    # =========================================================
    def _db_ready(self):
        ok, msg = require_ready()
        if not ok:
            messagebox.showerror("Planejamento", msg)
        return ok

    def _garantir_estrutura_planejamento(self):
        if not self._db_ready():
            return
        schema = get_schema()
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS codigo_modelo VARCHAR(100)")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS descricao_modelo TEXT")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS colecao VARCHAR(100)")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS programacao VARCHAR(30) DEFAULT 'Mensal'")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS periodo_inicio DATE")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS periodo_fim DATE")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS prazo_inicio DATE")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS observacoes TEXT")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS total_grade INTEGER DEFAULT 0")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP DEFAULT NOW()")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP DEFAULT NOW()")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS percentual_progresso NUMERIC(5,2) DEFAULT 0")
                    cur.execute(f"ALTER TABLE {schema}.planejamento_ops ADD COLUMN IF NOT EXISTS etapa_atual VARCHAR(40) DEFAULT 'Planejada'")
                    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_planejamento_ops_op_uq ON {schema}.planejamento_ops(op)")
                    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_planejamento_ops_modelo ON {schema}.planejamento_ops(codigo_modelo)")
                    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_planejamento_ops_programacao ON {schema}.planejamento_ops(programacao)")
                    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_planejamento_ops_colecao ON {schema}.planejamento_ops(colecao)")

                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {schema}.planejamento_op_grade (
                            id SERIAL PRIMARY KEY,
                            planejamento_id INTEGER NOT NULL REFERENCES {schema}.planejamento_ops(id) ON DELETE CASCADE,
                            tamanho VARCHAR(10) NOT NULL,
                            quantidade INTEGER DEFAULT 0 NOT NULL,
                            percentual NUMERIC(12,4) DEFAULT 0,
                            created_at TIMESTAMP DEFAULT NOW(),
                            UNIQUE (planejamento_id, tamanho)
                        )
                        """
                    )
                    cur.execute(f"ALTER TABLE {schema}.planejamento_op_grade ADD COLUMN IF NOT EXISTS percentual NUMERIC(12,4) DEFAULT 0")
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {schema}.planejamento_op_tecidos (
                            id SERIAL PRIMARY KEY,
                            planejamento_id INTEGER NOT NULL REFERENCES {schema}.planejamento_ops(id) ON DELETE CASCADE,
                            codigo_tecido VARCHAR(100),
                            descricao TEXT,
                            cor VARCHAR(50),
                            fornecedor VARCHAR(100),
                            composicao VARCHAR(100),
                            consumo_por_peca NUMERIC(12,4) DEFAULT 0,
                            quantidade_necessaria NUMERIC(12,4) DEFAULT 0,
                            estoque_atual NUMERIC(12,4) DEFAULT 0,
                            saldo_previsto NUMERIC(12,4) DEFAULT 0,
                            status_estoque VARCHAR(20) DEFAULT 'OK',
                            created_at TIMESTAMP DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {schema}.planejamento_ordens_geradas (
                            id SERIAL PRIMARY KEY,
                            planejamento_id INTEGER NOT NULL REFERENCES {schema}.planejamento_ops(id) ON DELETE CASCADE,
                            op VARCHAR(60) NOT NULL,
                            ordem_corte_id INTEGER REFERENCES {schema}.ordem_corte_ficha(id) ON DELETE SET NULL,
                            codigo_modelo VARCHAR(100),
                            descricao_modelo TEXT,
                            quantidade INTEGER DEFAULT 0,
                            status VARCHAR(30) DEFAULT 'Ordem Gerada',
                            criado_em TIMESTAMP DEFAULT NOW(),
                            atualizado_em TIMESTAMP DEFAULT NOW(),
                            UNIQUE (planejamento_id)
                        )
                        """
                    )
                    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_planejamento_ordens_op ON {schema}.planejamento_ordens_geradas(op)")
                    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_planejamento_ordens_ordem ON {schema}.planejamento_ordens_geradas(ordem_corte_id)")
                    cur.execute(
                        f"ALTER TABLE {schema}.ordem_corte_ficha ADD COLUMN IF NOT EXISTS planejamento_op_id INTEGER REFERENCES {schema}.planejamento_ops(id) ON DELETE SET NULL"
                    )
                    cur.execute(f"ALTER TABLE {schema}.ordem_corte_ficha ADD COLUMN IF NOT EXISTS op_planejamento VARCHAR(60)")
                    cur.execute(
                        f"ALTER TABLE {schema}.controle_envio_cortes ADD COLUMN IF NOT EXISTS op_planejamento VARCHAR(60)"
                    )
                    cur.execute(
                        f"ALTER TABLE {schema}.controle_retorno_cortes ADD COLUMN IF NOT EXISTS op_planejamento VARCHAR(60)"
                    )
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {schema}.planejamento_op_aviamentos (
                            id SERIAL PRIMARY KEY,
                            planejamento_id INTEGER NOT NULL REFERENCES {schema}.planejamento_ops(id) ON DELETE CASCADE,
                            codigo_aviamento VARCHAR(100),
                            descricao TEXT,
                            cor VARCHAR(50),
                            fornecedor VARCHAR(100),
                            consumo_por_peca NUMERIC(12,4) DEFAULT 0,
                            quantidade_necessaria NUMERIC(12,4) DEFAULT 0,
                            estoque_atual NUMERIC(12,4) DEFAULT 0,
                            saldo_previsto NUMERIC(12,4) DEFAULT 0,
                            status_estoque VARCHAR(20) DEFAULT 'OK',
                            created_at TIMESTAMP DEFAULT NOW()
                        )
                        """
                    )
                conn.commit()
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao preparar estrutura do banco: {exc}")

    def _carregar_modelos_cache(self):
        self.modelos_cache = []
        if not self._db_ready():
            return
        schema = get_schema()
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT codigo, COALESCE(descricao, ''), COALESCE(colecao, ''), COALESCE(grade_disponivel, '')
                        FROM {schema}.cadastro_modelos_cabecalho
                        ORDER BY descricao, codigo
                        """
                    )
                    self.modelos_cache = cur.fetchall()
        except Exception:
            self.modelos_cache = []

        colecoes = sorted({(row[2] or '').strip() for row in self.modelos_cache if (row[2] or '').strip()})
        valores = ["Todas"] + colecoes if colecoes else ["Todas"]
        if hasattr(self, "filtro_colecao") and self.filtro_colecao:
            self.filtro_colecao.configure(values=valores)
            self.filtro_colecao.set("Todas")

    # =========================================================
    # Utilidades
    # =========================================================
    @staticmethod
    def _to_float(valor):
        try:
            if valor is None:
                return 0.0
            return float(valor)
        except Exception:
            try:
                return float(str(valor).replace(".", "").replace(",", "."))
            except Exception:
                return 0.0

    @staticmethod
    def _fmt_num(valor, casas=3):
        numero = PlanejamentoProducaoPage._to_float(valor)
        txt = f"{numero:,.{casas}f}"
        return txt.replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _fmt_int(valor):
        return f"{int(round(PlanejamentoProducaoPage._to_float(valor)))}"

    @staticmethod
    def _sanitizar_texto_para_banco(texto):
        """Evita erro de codec/charmap ao persistir textos com símbolos especiais."""
        if texto is None:
            return ""
        txt = str(texto)
        for origem, destino in {
            "✅": "OK",
            "⚠️": "ATENCAO",
            "⚠": "ATENCAO",
            "•": "-",
            "═": "=",
        }.items():
            txt = txt.replace(origem, destino)
        txt = txt.replace("\ufe0f", "")
        try:
            txt.encode("cp1252")
            return txt
        except Exception:
            return txt.encode("cp1252", errors="replace").decode("cp1252")

    def _hover(self, cor):
        try:
            cor = cor.lstrip("#")
            r, g, b = [int(cor[i:i+2], 16) for i in (0, 2, 4)]
            fator = 0.85
            return f"#{int(r*fator):02x}{int(g*fator):02x}{int(b*fator):02x}"
        except Exception:
            return cor

    def _parse_data(self, texto):
        if not texto:
            return None
        try:
            return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
        except Exception:
            return None

    def _data_txt(self, valor):
        return valor.strftime("%d/%m/%Y") if valor else ""

    def _limpar_tree(self, tree):
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)

    def _limpar_detalhes(self):
        for chave, texto in {
            "grade": "Grade: -",
            "prazo": "Prazo início: -",
            "modelo": "Modelo: -",
            "prioridade": "Prioridade: -",
        }.items():
            if chave in self.detalhe_labels:
                self.detalhe_labels[chave].configure(text=texto)
        self._limpar_tree(self.tree_tecidos)
        self._limpar_tree(self.tree_aviamentos)

    def _gerar_codigo_op(self, cur, programacao):
        prefixo = {
            "Semanal": "OPS",
            "Mensal": "OPM",
            "Trimestral": "OPT",
            "Semestral": "OPSE",
            "Coleção": "OPC",
        }.get(programacao, "OP")
        cur.execute(f"SELECT COUNT(*) FROM {get_schema()}.planejamento_ops WHERE op LIKE %s", (f"{prefixo}-%",))
        prox = (cur.fetchone()[0] or 0) + 1
        return f"{prefixo}-{prox:04d}"

    # =========================================================
    # Cálculo de materiais
    # =========================================================
    def _carregar_materiais_modelo(self, codigo_modelo, quantidade_total):
        schema = get_schema()
        tecidos = []
        aviamentos = []
        outros = []
        servicos = []
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT codigo_tecido, COALESCE(descricao, ''), COALESCE(cor, ''),
                           COALESCE(fornecedor, ''), COALESCE(composicao, ''), COALESCE(metros_peca, 0)
                      FROM {schema}.cadastro_modelos_tecidos
                     WHERE codigo_modelo = %s
                     ORDER BY descricao, codigo_tecido
                    """,
                    (codigo_modelo,),
                )
                for codigo, descricao, cor, fornecedor, composicao, consumo in cur.fetchall():
                    necessario = self._to_float(consumo) * quantidade_total
                    cur.execute(
                        f"""
                        SELECT COALESCE(SUM(metros), 0)
                          FROM {schema}.estoque_tecidos
                         WHERE codigo = %s
                        """,
                        (codigo,),
                    )
                    estoque = self._to_float(cur.fetchone()[0])
                    saldo = estoque - necessario
                    tecidos.append({
                        "codigo": codigo or "",
                        "descricao": descricao or codigo or "Tecido",
                        "cor": cor or "",
                        "fornecedor": fornecedor or "",
                        "composicao": composicao or "",
                        "consumo": self._to_float(consumo),
                        "necessario": necessario,
                        "estoque": estoque,
                        "saldo": saldo,
                        "status": "OK" if saldo >= 0 else "FALTA",
                    })

                cur.execute(
                    f"""
                    SELECT codigo_aviamento, COALESCE(descricao, ''), COALESCE(cor, ''),
                           COALESCE(fornecedor, ''), COALESCE(quantidade, 0)
                      FROM {schema}.cadastro_modelos_aviamentos
                     WHERE codigo_modelo = %s
                     ORDER BY descricao, codigo_aviamento
                    """,
                    (codigo_modelo,),
                )
                for codigo, descricao, cor, fornecedor, consumo in cur.fetchall():
                    necessario = self._to_float(consumo) * quantidade_total
                    cur.execute(
                        f"""
                        SELECT COALESCE(SUM(quantidade), 0)
                          FROM {schema}.estoque_aviamentos
                         WHERE codigo = %s
                        """,
                        (codigo,),
                    )
                    estoque = self._to_float(cur.fetchone()[0])
                    saldo = estoque - necessario
                    aviamentos.append({
                        "codigo": codigo or "",
                        "descricao": descricao or codigo or "Aviamento",
                        "cor": cor or "",
                        "fornecedor": fornecedor or "",
                        "consumo": self._to_float(consumo),
                        "necessario": necessario,
                        "estoque": estoque,
                        "saldo": saldo,
                        "status": "OK" if saldo >= 0 else "FALTA",
                    })

                cur.execute(
                    f"""
                    SELECT COALESCE(codigo, ''), COALESCE(descricao, ''), COALESCE(cor, ''),
                           COALESCE(fornecedor, ''), COALESCE(unidade, ''), COALESCE(quantidade, 0)
                      FROM {schema}.cadastro_modelos_outros
                     WHERE codigo_modelo = %s
                     ORDER BY descricao, codigo
                    """,
                    (codigo_modelo,),
                )
                for codigo, descricao, cor, fornecedor, unidade, consumo in cur.fetchall():
                    necessario = self._to_float(consumo) * quantidade_total
                    cur.execute(
                        f"""
                        SELECT (
                            COALESCE((SELECT SUM(quantidade) FROM {schema}.estoque_insumos WHERE codigo = %s), 0) +
                            COALESCE((SELECT SUM(quantidade) FROM {schema}.estoque_outros WHERE codigo = %s), 0) +
                            COALESCE((SELECT SUM(quantidade) FROM {schema}.estoque_escritorio WHERE codigo = %s), 0) +
                            COALESCE((SELECT SUM(quantidade) FROM {schema}.estoque_limpeza WHERE codigo = %s), 0)
                        )
                        """,
                        (codigo, codigo, codigo, codigo),
                    )
                    estoque = self._to_float(cur.fetchone()[0])
                    saldo = estoque - necessario
                    outros.append({
                        "codigo": codigo or "",
                        "descricao": descricao or codigo or "Outro material",
                        "cor": cor or "",
                        "fornecedor": fornecedor or "",
                        "unidade": unidade or "",
                        "consumo": self._to_float(consumo),
                        "necessario": necessario,
                        "estoque": estoque,
                        "saldo": saldo,
                        "status": "OK" if saldo >= 0 else "FALTA",
                    })

                cur.execute(
                    f"""
                    SELECT COALESCE(codigo_servico, ''), COALESCE(descricao, ''), COALESCE(tipo_servico, ''),
                           COALESCE(fornecedor, ''), COALESCE(unidade, ''), COALESCE(quantidade, 0),
                           COALESCE(valor_unidade, 0)
                      FROM {schema}.cadastro_modelos_outros_servicos
                     WHERE codigo_modelo = %s
                     ORDER BY descricao, codigo_servico
                    """,
                    (codigo_modelo,),
                )
                for codigo, descricao, tipo_servico, fornecedor, unidade, quantidade, valor_unidade in cur.fetchall():
                    qtd = self._to_float(quantidade) * quantidade_total
                    valor = self._to_float(valor_unidade) * qtd
                    servicos.append({
                        "codigo": codigo or "",
                        "descricao": descricao or codigo or "Serviço",
                        "tipo_servico": tipo_servico or "",
                        "fornecedor": fornecedor or "",
                        "unidade": unidade or "",
                        "quantidade": qtd,
                        "valor_estimado": valor,
                        "status": "OK",
                    })
        return tecidos, aviamentos, outros, servicos

    # =========================================================
    # Nova programação
    # =========================================================
    def _abrir_dialogo_nova_programacao(self):
        if not self._db_ready():
            return
        self._carregar_modelos_cache()

        top = ctk.CTkToplevel(self)
        top.title("Nova Programação de Produção")
        largura_janela, altura_janela = 1220, 900
        sw = top.winfo_screenwidth()
        sh = top.winfo_screenheight()
        x = max(20, (sw - largura_janela) // 2)
        y = max(20, (sh - altura_janela) // 2)
        top.geometry(f"{largura_janela}x{altura_janela}+{x}+{y}")
        top.transient(self)
        top.grab_set()
        top.configure(fg_color=self.cor_fundo)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)
        top.grid_rowconfigure(2, weight=0)

        ctk.CTkLabel(top, text="Nova Programação", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 8))

        body = ctk.CTkScrollableFrame(top, fg_color=self.cor_fundo)
        body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        # Passo 1
        passo1 = ctk.CTkFrame(body)
        passo1.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        passo1.grid_columnconfigure((1, 3, 5, 7), weight=1)
        ctk.CTkLabel(passo1, text="Passo 1 - Definir período e tipo de programação", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=8, sticky="w", padx=12, pady=(10, 8))

        ctk.CTkLabel(passo1, text="Período início").grid(row=1, column=0, padx=(12, 6), pady=6, sticky="w")
        ent_inicio = ctk.CTkEntry(passo1, width=140)
        ent_inicio.grid(row=1, column=1, padx=(0, 6), pady=6, sticky="ew")
        ent_inicio.insert(0, date.today().strftime("%d/%m/%Y"))
        ctk.CTkButton(passo1, text="📅", width=32, command=lambda: self._abrir_calendario(ent_inicio)).grid(row=1, column=2, padx=(0, 12), pady=6)

        ctk.CTkLabel(passo1, text="Período fim").grid(row=1, column=3, padx=(0, 6), pady=6, sticky="w")
        ent_fim = ctk.CTkEntry(passo1, width=140)
        ent_fim.grid(row=1, column=4, padx=(0, 6), pady=6, sticky="ew")
        ent_fim.insert(0, (date.today() + timedelta(days=30)).strftime("%d/%m/%Y"))
        ctk.CTkButton(passo1, text="📅", width=32, command=lambda: self._abrir_calendario(ent_fim)).grid(row=1, column=5, padx=(0, 12), pady=6)

        ctk.CTkLabel(passo1, text="Programação").grid(row=1, column=6, padx=(0, 6), pady=6, sticky="w")
        cmb_programacao = ctk.CTkOptionMenu(passo1, values=PROGRAMACOES)
        cmb_programacao.set("Mensal")
        cmb_programacao.grid(row=1, column=7, padx=(0, 12), pady=6, sticky="ew")

        ctk.CTkLabel(passo1, text="Prazo para começar").grid(row=2, column=0, padx=(12, 6), pady=(0, 10), sticky="w")
        ent_prazo = ctk.CTkEntry(passo1, width=140)
        ent_prazo.grid(row=2, column=1, padx=(0, 6), pady=(0, 10), sticky="ew")
        ent_prazo.insert(0, date.today().strftime("%d/%m/%Y"))
        ctk.CTkButton(passo1, text="📅", width=32, command=lambda: self._abrir_calendario(ent_prazo)).grid(row=2, column=2, padx=(0, 12), pady=(0, 10))

        ctk.CTkLabel(passo1, text="Coleção").grid(row=2, column=3, padx=(0, 6), pady=(0, 10), sticky="w")
        valores_colecao = sorted({(m[2] or '').strip() for m in self.modelos_cache if (m[2] or '').strip()}) or [""]
        cmb_colecao = ctk.CTkComboBox(passo1, values=valores_colecao)
        if valores_colecao:
            cmb_colecao.set(valores_colecao[0])
        cmb_colecao.grid(row=2, column=4, padx=(0, 12), pady=(0, 10), sticky="ew")

        ctk.CTkLabel(passo1, text="Prioridade").grid(row=2, column=6, padx=(0, 6), pady=(0, 10), sticky="w")
        cmb_prioridade = ctk.CTkOptionMenu(passo1, values=PRIORIDADES)
        cmb_prioridade.set("Média")
        cmb_prioridade.grid(row=2, column=7, padx=(0, 12), pady=(0, 10), sticky="ew")

        # Passo 2
        passo2 = ctk.CTkFrame(body)
        passo2.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        passo2.grid_columnconfigure(1, weight=1)
        passo2.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(passo2, text="Passo 2 - Escolher modelo", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(10, 8))

        modelos_exibicao = [f"{m[0]} - {m[1]}" for m in self.modelos_cache] or [""]
        ctk.CTkLabel(passo2, text="Modelo").grid(row=1, column=0, padx=(12, 6), pady=6, sticky="w")
        cmb_modelo = ctk.CTkComboBox(passo2, values=modelos_exibicao)
        if modelos_exibicao:
            cmb_modelo.set(modelos_exibicao[0])
        cmb_modelo.grid(row=1, column=1, padx=(0, 12), pady=6, sticky="ew")

        lbl_grade_disp = ctk.CTkLabel(passo2, text="Grade disponível: -")
        lbl_grade_disp.grid(row=2, column=0, columnspan=4, sticky="w", padx=12, pady=(0, 10))

        # Passo 3
        passo3 = ctk.CTkFrame(body)
        passo3.grid(row=2, column=0, sticky="nsew", padx=(0, 8), pady=(0, 10))
        ctk.CTkLabel(passo3, text="Passo 3 - Distribuir grade (porcentagem)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(10, 8))

        ctk.CTkLabel(passo3, text="Quantidade desejada").grid(row=1, column=0, padx=(12, 6), pady=(0, 8), sticky="w")
        ent_quantidade = ctk.CTkEntry(passo3, width=160)
        ent_quantidade.insert(0, "0")
        ent_quantidade.grid(row=1, column=1, padx=(0, 12), pady=(0, 8), sticky="w")

        grade_vars = {}
        grade_entries = {}
        grade_labels = {}
        tamanhos_ativos = TAMANHOS_GRADE.copy()
        for i, tamanho in enumerate(TAMANHOS_GRADE):
            grade_vars[tamanho] = ctk.StringVar(value="0")
            linha_base = 2 + (i // 4) * 2
            lbl_tam = ctk.CTkLabel(passo3, text=tamanho)
            lbl_tam.grid(row=linha_base, column=(i % 4), padx=8, pady=(0, 4), sticky="w")
            grade_labels[tamanho] = lbl_tam
            ent = ctk.CTkEntry(passo3, width=90, textvariable=grade_vars[tamanho])
            ent.grid(row=linha_base + 1, column=(i % 4), padx=8, pady=(0, 10), sticky="w")
            grade_entries[tamanho] = ent

        lbl_total_grade = ctk.CTkLabel(passo3, text="Total da porcentagem: 0%")
        lbl_total_grade.grid(row=6, column=0, columnspan=4, sticky="w", padx=12, pady=(0, 10))

        # Passo 4
        passo4 = ctk.CTkFrame(body)
        passo4.grid(row=2, column=1, sticky="nsew", padx=(8, 0), pady=(0, 10))
        passo4.grid_rowconfigure(2, weight=1)
        passo4.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(passo4, text="Passo 4 - Conferir materiais", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 8))

        resumo_box = ctk.CTkTextbox(passo4, height=250)
        resumo_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        resumo_box.insert("1.0", "Selecione o modelo e informe a quantidade para calcular tecidos e aviamentos.")

        resumo_visual = ctk.CTkTextbox(body, height=90)
        resumo_visual.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        resumo_visual.insert("1.0", "Resumo de conferência: preencha os passos para visualizar os dados principais da programação.")

        bottom = ctk.CTkFrame(top)
        bottom.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        bottom.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            bottom,
            text="Calcular materiais",
            command=lambda: recalcular_resumo(),
            fg_color=self.cor_primaria,
            hover_color=self._hover(self.cor_primaria),
            text_color=self.cor_texto,
        ).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(
            bottom,
            text="Salvar programação",
            command=lambda: salvar_programacao(),
            fg_color=self.cor_sucesso,
            hover_color=self._hover(self.cor_sucesso),
            text_color="white",
        ).pack(side="right", padx=8, pady=8)

        def modelo_info():
            valor = (cmb_modelo.get() or "").strip()
            codigo = valor.split(" - ", 1)[0].strip() if valor else ""
            for row in self.modelos_cache:
                if row[0] == codigo:
                    return {
                        "codigo": row[0],
                        "descricao": row[1] or "",
                        "colecao": row[2] or "",
                        "grade": row[3] or "",
                    }
            return None


        def _parse_tamanhos_grade(grade_texto: str):
            txt = (grade_texto or "").upper().replace("|", ",").replace("/", ",").replace(";", ",")
            partes = [p.strip() for p in txt.split(",") if p.strip()]
            validos = [t for t in TAMANHOS_GRADE if t in partes]
            return validos or TAMANHOS_GRADE.copy()

        def _aplicar_tamanhos_disponiveis(tamanhos):
            nonlocal tamanhos_ativos
            tamanhos_ativos = list(tamanhos or TAMANHOS_GRADE)
            for tam in TAMANHOS_GRADE:
                if tam in tamanhos_ativos:
                    grade_labels[tam].grid()
                    grade_entries[tam].grid()
                else:
                    grade_vars[tam].set("0")
                    grade_labels[tam].grid_remove()
                    grade_entries[tam].grid_remove()

        def atualizar_modelo(*_args):
            info = modelo_info()
            if not info:
                lbl_grade_disp.configure(text="Grade disponível: -")
                return
            grade_txt = info["grade"] or "-"
            lbl_grade_disp.configure(text=f"Grade disponível: {grade_txt}")
            _aplicar_tamanhos_disponiveis(_parse_tamanhos_grade(info.get("grade") or ""))
            if info["colecao"]:
                cmb_colecao.set(info["colecao"])
            atualizar_resumo_visual()

        def total_grade():
            total = 0.0
            for tamanho in tamanhos_ativos:
                try:
                    total += float((grade_vars[tamanho].get() or "0").replace(",", "."))
                except Exception:
                    pass
            lbl_total_grade.configure(text=f"Total da porcentagem: {total:.2f}%")
            atualizar_resumo_visual()
            return total

        def calcular_grade_quantidades(quantidade_total: int):
            percentuais = {}
            soma = 0.0
            for tamanho in tamanhos_ativos:
                try:
                    pct = float((grade_vars[tamanho].get() or "0").replace(",", "."))
                except Exception:
                    pct = 0.0
                if pct < 0:
                    pct = 0.0
                percentuais[tamanho] = pct
                soma += pct

            if quantidade_total <= 0 or soma <= 0:
                return {t: 0 for t in tamanhos_ativos}, percentuais, soma

            grade_qtd = {t: int(round((percentuais[t] / soma) * quantidade_total)) for t in tamanhos_ativos}
            diferenca = quantidade_total - sum(grade_qtd.values())
            if diferenca != 0 and tamanhos_ativos:
                principal = max(tamanhos_ativos, key=lambda t: percentuais.get(t, 0.0))
                grade_qtd[principal] = max(0, grade_qtd.get(principal, 0) + diferenca)
            return grade_qtd, percentuais, soma

        def recalcular_resumo():
            info = modelo_info()
            if not info:
                resumo_box.delete("1.0", "end")
                resumo_box.insert("1.0", "Selecione um modelo válido.")
                return [], []
            qtd_manual = int(self._to_float(ent_quantidade.get()))
            quantidade_total = qtd_manual
            if quantidade_total <= 0:
                resumo_box.delete("1.0", "end")
                resumo_box.insert("1.0", "Informe a quantidade desejada maior que zero.")
                return [], []
            tecidos, aviamentos, outros, servicos = self._carregar_materiais_modelo(info["codigo"], quantidade_total)
            linhas = [
                f"Modelo: {info['codigo']} - {info['descricao']}",
                f"Quantidade: {quantidade_total}",
                f"Programação: {cmb_programacao.get()}",
                f"Coleção: {cmb_colecao.get()}",
                "",
                "TECIDOS:",
            ]
            if tecidos:
                for item in tecidos:
                    linhas.append(
                        f"- {item['codigo']} | {item['descricao']} | necessário {self._fmt_num(item['necessario'])} m | estoque {self._fmt_num(item['estoque'])} m | {item['status']}"
                    )
            else:
                linhas.append("- Modelo sem tecidos cadastrados.")
            linhas.append("")
            linhas.append("AVIAMENTOS:")
            if aviamentos:
                for item in aviamentos:
                    linhas.append(
                        f"- {item['codigo']} | {item['descricao']} | necessário {self._fmt_num(item['necessario'])} | estoque {self._fmt_num(item['estoque'])} | {item['status']}"
                    )
            else:
                linhas.append("- Modelo sem aviamentos cadastrados.")

            linhas.append("")
            linhas.append("OUTROS MATERIAIS:")
            if outros:
                for item in outros:
                    un = f" {item['unidade']}" if item.get("unidade") else ""
                    linhas.append(
                        f"- {item['codigo']} | {item['descricao']} | necessário {self._fmt_num(item['necessario'])}{un} | estoque {self._fmt_num(item['estoque'])}{un} | {item['status']}"
                    )
            else:
                linhas.append("- Modelo sem outros materiais cadastrados.")

            linhas.append("")
            linhas.append("OUTROS SERVIÇOS:")
            if servicos:
                for item in servicos:
                    un = f" {item['unidade']}" if item.get("unidade") else ""
                    linhas.append(
                        f"- {item['codigo']} | {item['descricao']} | tipo {item['tipo_servico'] or '-'} | qtd {self._fmt_num(item['quantidade'])}{un} | custo estimado R$ {self._fmt_num(item['valor_estimado'])} | {item['status']}"
                    )
            else:
                linhas.append("- Modelo sem outros serviços cadastrados.")

            faltas = sum(1 for x in tecidos if x.get("status") != "OK") + \
                     sum(1 for x in aviamentos if x.get("status") != "OK") + \
                     sum(1 for x in outros if x.get("status") != "OK")
            linhas.append("")
            linhas.append(f"STATUS GERAL DOS MATERIAIS: {'OK ✅' if faltas == 0 else f'FALTAS ⚠️ ({faltas} item(ns))'}")
            resumo_box.delete("1.0", "end")
            resumo_box.insert("1.0", "\n".join(linhas))
            return tecidos, aviamentos

        def atualizar_resumo_visual():
            info = modelo_info() or {"codigo": "-", "descricao": "-", "colecao": "", "grade": ""}
            qtd = int(self._to_float(ent_quantidade.get()))
            grade_partes = []
            grade_detalhe = []
            total_distribuido_pct = 0.0
            for tam in tamanhos_ativos:
                valor = self._to_float(grade_vars[tam].get())
                total_distribuido_pct += valor
                grade_detalhe.append(f"  • {tam}: {valor:.2f}%")
                if valor > 0:
                    grade_partes.append(f"{tam}:{valor:.2f}%")
            grade_txt = " | ".join(grade_partes) if grade_partes else "Sem distribuição de grade"

            grade_qtd, _pct, _soma_pct = calcular_grade_quantidades(qtd)
            total_distribuido = sum(grade_qtd.values())

            diferenca = qtd - total_distribuido
            if diferenca == 0:
                status_grade = "✅ Grade fechada com a quantidade desejada"
            elif diferenca > 0:
                status_grade = f"⚠️ Faltam {diferenca} peça(s)"
            else:
                status_grade = f"⚠️ Excedeu {abs(diferenca)} peça(s)"

            linhas = [
                "════════ RESUMO DE CONFERÊNCIA ════════",
                f"Modelo      : {info.get('codigo') or '-'} - {info.get('descricao') or '-'}",
                f"Coleção     : {cmb_colecao.get() or info.get('colecao') or '-'}",
                f"Programação : {cmb_programacao.get()}    |    Prioridade: {cmb_prioridade.get()}",
                f"Período     : {ent_inicio.get()} até {ent_fim.get()}    |    Prazo início: {ent_prazo.get()}",
                "",
                "Quantidade planejada",
                f"  • Total informado : {qtd}",
                f"  • Total % grade   : {total_distribuido_pct:.2f}%",
                f"  • Total na grade  : {total_distribuido}",
                f"  • Situação        : {status_grade}",
                "",
                "Distribuição por tamanho (percentual)",
                *grade_detalhe,
                "",
                "Distribuição por tamanho (quantidade calculada)",
                *[f"  • {tam}: {qtd_tam}" for tam, qtd_tam in grade_qtd.items()],
                "",
                f"Consolidado da grade: {grade_txt}",
            ]
            resumo_visual.delete("1.0", "end")
            resumo_visual.insert("1.0", "\n".join(linhas))

        def salvar_programacao():
            info = modelo_info()
            if not info:
                messagebox.showwarning("Planejamento", "Selecione um modelo válido.", parent=top)
                return

            periodo_inicio = self._parse_data(ent_inicio.get())
            periodo_fim = self._parse_data(ent_fim.get())
            prazo_inicio = self._parse_data(ent_prazo.get())
            if not periodo_inicio or not periodo_fim or not prazo_inicio:
                messagebox.showwarning("Planejamento", "Preencha as datas corretamente no formato dd/mm/aaaa.", parent=top)
                return
            if periodo_fim < periodo_inicio:
                messagebox.showwarning("Planejamento", "A data final não pode ser menor que a inicial.", parent=top)
                return

            total_pct = total_grade()
            qtd_manual = int(self._to_float(ent_quantidade.get()))
            quantidade_total = qtd_manual
            if quantidade_total <= 0:
                messagebox.showwarning("Planejamento", "Informe uma quantidade maior que zero.", parent=top)
                return
            if total_pct <= 0:
                messagebox.showwarning("Planejamento", "Informe os percentuais da grade por tamanho (Passo 3).", parent=top)
                return

            tecidos, aviamentos = recalcular_resumo()
            programacao = cmb_programacao.get()
            prioridade = cmb_prioridade.get()
            colecao = (cmb_colecao.get() or info.get("colecao") or "").strip()
            observacoes = resumo_visual.get("1.0", "end").strip()
            observacoes = self._sanitizar_texto_para_banco(observacoes)
            grade_dict, percentuais_digitados, _soma_pct = calcular_grade_quantidades(quantidade_total)
            grade_dict = {t: q for t, q in grade_dict.items() if q > 0}

            try:
                schema = get_schema()
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        op = self._gerar_codigo_op(cur, programacao)
                        cur.execute(
                            f"""
                            INSERT INTO {schema}.planejamento_ops (
                                op, modelo, quantidade, inicio, fim, status, prioridade,
                                codigo_modelo, descricao_modelo, colecao, programacao,
                                periodo_inicio, periodo_fim, prazo_inicio, observacoes,
                                total_grade, data_atualizacao, criado_em, atualizado_em
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, NOW(), NOW(), NOW()
                            ) RETURNING id
                            """,
                            (
                                op,
                                info["descricao"] or info["codigo"],
                                quantidade_total,
                                prazo_inicio,
                                periodo_fim,
                                "Planejada",
                                prioridade,
                                info["codigo"],
                                info["descricao"],
                                colecao,
                                programacao,
                                periodo_inicio,
                                periodo_fim,
                                prazo_inicio,
                                observacoes,
                                quantidade_total,
                            ),
                        )
                        planejamento_id = cur.fetchone()[0]

                        for tamanho, qtd in grade_dict.items():
                            if qtd <= 0:
                                continue
                            pct_digitado = float(percentuais_digitados.get(tamanho, 0) or 0)
                            cur.execute(
                                f"""
                                INSERT INTO {schema}.planejamento_op_grade (planejamento_id, tamanho, quantidade, percentual)
                                VALUES (%s, %s, %s, %s)
                                """,
                                (planejamento_id, tamanho, qtd, pct_digitado),
                            )

                        for item in tecidos:
                            cur.execute(
                                f"""
                                INSERT INTO {schema}.planejamento_op_tecidos (
                                    planejamento_id, codigo_tecido, descricao, cor, fornecedor, composicao,
                                    consumo_por_peca, quantidade_necessaria, estoque_atual, saldo_previsto, status_estoque
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    planejamento_id, item["codigo"], item["descricao"], item["cor"], item["fornecedor"], item["composicao"],
                                    item["consumo"], item["necessario"], item["estoque"], item["saldo"], item["status"],
                                ),
                            )

                        for item in aviamentos:
                            cur.execute(
                                f"""
                                INSERT INTO {schema}.planejamento_op_aviamentos (
                                    planejamento_id, codigo_aviamento, descricao, cor, fornecedor,
                                    consumo_por_peca, quantidade_necessaria, estoque_atual, saldo_previsto, status_estoque
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    planejamento_id, item["codigo"], item["descricao"], item["cor"], item["fornecedor"],
                                    item["consumo"], item["necessario"], item["estoque"], item["saldo"], item["status"],
                                ),
                            )
                    conn.commit()
                self._carregar_dados_planejamento()
                messagebox.showinfo("Planejamento", "Programação salva com sucesso.", parent=top)
                top.destroy()
            except Exception as exc:
                messagebox.showerror("Planejamento", f"Erro ao salvar programação: {exc}", parent=top)

        cmb_modelo.bind("<<ComboboxSelected>>", atualizar_modelo)
        cmb_programacao.configure(command=lambda _v: atualizar_resumo_visual())
        cmb_prioridade.configure(command=lambda _v: atualizar_resumo_visual())
        cmb_colecao.bind("<KeyRelease>", lambda _e: atualizar_resumo_visual())
        ent_inicio.bind("<KeyRelease>", lambda _e: atualizar_resumo_visual())
        ent_fim.bind("<KeyRelease>", lambda _e: atualizar_resumo_visual())
        ent_prazo.bind("<KeyRelease>", lambda _e: atualizar_resumo_visual())
        atualizar_modelo()
        for tamanho in TAMANHOS_GRADE:
            grade_entries[tamanho].bind("<KeyRelease>", lambda _e: total_grade())
        ent_quantidade.bind("<KeyRelease>", lambda _e: recalcular_resumo())
        atualizar_resumo_visual()

    # =========================================================
    # Carregamento / detalhes
    # =========================================================
    def _calcular_progresso_real(self, cur, planejamento_id, op, codigo_modelo):
        schema = get_schema()

        def _col_exists(tabela: str, coluna: str) -> bool:
            cur.execute(
                """
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = current_schema()
                   AND table_name = %s
                   AND column_name = %s
                 LIMIT 1
                """,
                (tabela, coluna),
            )
            return bool(cur.fetchone())

        def _existe_por_colunas(tabela: str, colunas_alvo, valores_alvo) -> bool:
            clausulas = []
            params = []
            for col in colunas_alvo:
                if _col_exists(tabela, col):
                    clausulas.append(f"COALESCE({col}::text, '') = %s")
                    params.append(str(valores_alvo[col] or ""))
            if not clausulas:
                return False
            sql = f"SELECT 1 FROM {schema}.{tabela} WHERE " + " OR ".join(clausulas) + " LIMIT 1"
            cur.execute(sql, tuple(params))
            return bool(cur.fetchone())

        etapas = [
            "Nova Ordem",
            "Cadastro de Corte",
            "Controle de Mão de Obra",
            "Registro Acabamento",
            "Finalizar Corte/Acabamento",
            "Pagamento de Serviços",
        ]
        total_etapas = len(etapas)
        etapa_idx = -1

        op_txt = op or ""
        # Etapa 1 - Nova Ordem (salvou ordem de corte)
        if _existe_por_colunas(
            "ordem_corte_ficha",
            ["planejamento_op_id", "op_planejamento", "ordem", "ordem_corte"],
            {
                "planejamento_op_id": planejamento_id,
                "op_planejamento": op_txt,
                "ordem": op_txt,
                "ordem_corte": op_txt,
            },
        ):
            etapa_idx = max(etapa_idx, 0)

        # Etapa 2 - Cadastro de Corte
        if _existe_por_colunas(
            "cadastro_de_corte",
            ["op_planejamento", "ordem", "ordem_corte"],
            {
                "op_planejamento": op_txt,
                "ordem": op_txt,
                "ordem_corte": op_txt,
            },
        ):
            etapa_idx = max(etapa_idx, 1)

        # Etapa 3 - Controle de Mão de Obra
        if _existe_por_colunas(
            "controle_envio_cortes",
            ["op_planejamento", "ordem", "ordem_corte"],
            {
                "op_planejamento": op_txt,
                "ordem": op_txt,
                "ordem_corte": op_txt,
            },
        ) or _existe_por_colunas(
            "envios_cortes",
            ["op_planejamento", "ordem", "ordem_corte"],
            {
                "op_planejamento": op_txt,
                "ordem": op_txt,
                "ordem_corte": op_txt,
            },
        ):
            etapa_idx = max(etapa_idx, 2)

        # Etapa 4 - Registro Acabamento
        if _existe_por_colunas(
            "controle_retorno_cortes",
            ["op_planejamento", "ordem", "ordem_corte"],
            {
                "op_planejamento": op_txt,
                "ordem": op_txt,
                "ordem_corte": op_txt,
            },
        ):
            etapa_idx = max(etapa_idx, 3)

        # Etapa 5 - Finalizar Corte/Acabamento
        if _existe_por_colunas(
            "cortes_finalizados_completo",
            ["op_planejamento", "ordem", "ordem_corte"],
            {
                "op_planejamento": op_txt,
                "ordem": op_txt,
                "ordem_corte": op_txt,
            },
        ) or _existe_por_colunas(
            "cortes_finalizados",
            ["op_planejamento", "ordem", "ordem_corte"],
            {
                "op_planejamento": op_txt,
                "ordem": op_txt,
                "ordem_corte": op_txt,
            },
        ):
            etapa_idx = max(etapa_idx, 4)

        # Etapa 6 - Pagamento de Serviços
        if _existe_por_colunas(
            "pagamento_corte_acabamento",
            ["op_planejamento", "ordem", "ordem_corte"],
            {
                "op_planejamento": op_txt,
                "ordem": op_txt,
                "ordem_corte": op_txt,
            },
        ):
            etapa_idx = max(etapa_idx, 5)

        if etapa_idx < 0:
            etapa = "Planejada"
            progresso = 0.0
            status = "Planejada"
        else:
            etapa = etapas[etapa_idx]
            progresso = round(((etapa_idx + 1) / total_etapas) * 100.0, 1)
            if etapa_idx >= total_etapas - 1:
                etapa = "Pagamento de Serviços"
                progresso = 100.0
                status = "Pronta"
            else:
                status = "Em execução"

        cur.execute(
            f"""
            UPDATE {schema}.planejamento_ops
               SET status=%s,
                   etapa_atual=%s,
                   percentual_progresso=%s,
                   atualizado_em=NOW(),
                   data_atualizacao=NOW()
             WHERE id=%s
            """,
            (status, etapa, progresso, planejamento_id),
        )
        return status, etapa, progresso

    def _status_eh_andamento(self, status: str, progresso: float = 0.0) -> bool:
        st = (status or "").strip().lower()
        if st in {"em andamento", "em execução"}:
            return True
        try:
            p = float(progresso or 0)
            return 0 < p < 100
        except Exception:
            return False

    def _tag_status_op(self, status: str, progresso: float = 0.0) -> str | None:
        st = (status or "").strip().lower()
        try:
            p = float(progresso or 0)
        except Exception:
            p = 0.0
        if p >= 100 or st in {"pronta", "finalizada", "concluída", "concluida"}:
            return "op_concluida"
        if self._status_eh_andamento(status, p):
            return "op_andamento"
        if st in {"atrasada", "falta", "pendente", "planejada"} or p <= 0:
            return "op_falta"
        return None

    def on_page_open(self):
        self._carregar_modelos_cache()
        self._carregar_dados_planejamento()

    def _carregar_dados_planejamento(self):
        self._limpar_tree(self.tree_ops)
        self._limpar_tree(self.tree_capacidade)
        self._limpar_detalhes()
        self.ops_index = {}
        if not self._db_ready():
            return

        inicio = self._parse_data(self.plan_inicio_entry.get())
        fim = self._parse_data(self.plan_fim_entry.get())
        prioridade = (self.filtro_prioridade.get() or "Todas").strip()
        programacao = (self.filtro_programacao.get() or "Todas").strip()
        colecao = (self.filtro_colecao.get() or "Todas").strip()

        schema = get_schema()
        filtros = []
        params = []
        if inicio:
            filtros.append("COALESCE(periodo_inicio, inicio) >= %s")
            params.append(inicio)
        if fim:
            filtros.append("COALESCE(periodo_fim, fim) <= %s")
            params.append(fim)
        if prioridade != "Todas":
            filtros.append("COALESCE(prioridade, 'Média') = %s")
            params.append(prioridade)
        if programacao != "Todas":
            filtros.append("COALESCE(programacao, 'Mensal') = %s")
            params.append(programacao)
        if colecao != "Todas":
            filtros.append("COALESCE(colecao, '') = %s")
            params.append(colecao)

        where_sql = ("WHERE " + " AND ".join(filtros)) if filtros else ""

        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT id, op, COALESCE(descricao_modelo, modelo, codigo_modelo, ''),
                               COALESCE(quantidade, total_grade, 0),
                               COALESCE(prazo_inicio, inicio),
                               COALESCE(periodo_fim, fim),
                               COALESCE(status, 'Planejada'),
                               COALESCE(programacao, 'Mensal'),
                               COALESCE(colecao, ''),
                               COALESCE(prioridade, 'Média'),
                               COALESCE(codigo_modelo, ''),
                               COALESCE(observacoes, ''),
                               COALESCE(etapa_atual, COALESCE(status, 'Planejada')),
                               COALESCE(percentual_progresso, 0)
                          FROM {schema}.planejamento_ops
                        {where_sql}
                         ORDER BY COALESCE(programacao, 'Mensal'), COALESCE(prazo_inicio, inicio, CURRENT_DATE), op
                        """,
                        params,
                    )
                    rows = cur.fetchall()

                    agrupado = {}
                    em_execucao = 0
                    atrasadas = 0

                    for row in rows:
                        (
                            planejamento_id,
                            op,
                            modelo,
                            quantidade,
                            prazo_inicio,
                            periodo_fim,
                            status,
                            programacao_op,
                            colecao_op,
                            prioridade_op,
                            codigo_modelo,
                            observacoes,
                            _etapa_atual_db,
                            _percentual_db,
                        ) = row
                        if status == "Atrasada":
                            atrasadas += 1

                        status, etapa_atual, percentual = self._calcular_progresso_real(cur, planejamento_id, op, codigo_modelo)
                        if self._status_eh_andamento(status, percentual):
                            em_execucao += 1
                        grupo = f"COLEÇÃO: {colecao_op}" if programacao == "Coleção" else f"PROGRAMAÇÃO {programacao_op}"
                        agrupado.setdefault(grupo, []).append((
                            op,
                            modelo,
                            self._fmt_int(quantidade),
                            self._data_txt(prazo_inicio),
                            self._data_txt(periodo_fim),
                            status,
                            f"{percentual:.0f}%",
                            programacao_op,
                            colecao_op,
                        ))

                        cur.execute(
                            f"SELECT tamanho, quantidade FROM {schema}.planejamento_op_grade WHERE planejamento_id=%s ORDER BY id",
                            (planejamento_id,),
                        )
                        grade_rows = cur.fetchall()
                        grade_txt = " / ".join([f"{tam}:{qtd}" for tam, qtd in grade_rows]) if grade_rows else "-"

                        cur.execute(
                            f"""
                            SELECT codigo_tecido, COALESCE(descricao, ''), COALESCE(quantidade_necessaria, 0),
                                   COALESCE(estoque_atual, 0), COALESCE(saldo_previsto, 0), COALESCE(status_estoque, 'OK')
                              FROM {schema}.planejamento_op_tecidos
                             WHERE planejamento_id=%s
                             ORDER BY descricao, codigo_tecido
                            """,
                            (planejamento_id,),
                        )
                        tecidos = cur.fetchall()

                        cur.execute(
                            f"""
                            SELECT codigo_aviamento, COALESCE(descricao, ''), COALESCE(quantidade_necessaria, 0),
                                   COALESCE(estoque_atual, 0), COALESCE(saldo_previsto, 0), COALESCE(status_estoque, 'OK')
                              FROM {schema}.planejamento_op_aviamentos
                             WHERE planejamento_id=%s
                             ORDER BY descricao, codigo_aviamento
                            """,
                            (planejamento_id,),
                        )
                        aviamentos = cur.fetchall()

                        self.ops_index[op] = {
                            "id": planejamento_id,
                            "op": op,
                            "modelo": modelo,
                            "codigo_modelo": codigo_modelo,
                            "inicio": prazo_inicio,
                            "fim": periodo_fim,
                            "grade": grade_txt,
                            "prioridade": prioridade_op,
                            "status": status,
                            "programacao": programacao_op,
                            "colecao": colecao_op,
                            "observacoes": observacoes,
                            "etapa_atual": etapa_atual,
                            "progresso": percentual,
                            "tecidos": tecidos,
                            "aviamentos": aviamentos,
                        }

                    totais = {
                        "Tecidos": [0.0, 0.0],
                        "Aviamentos": [0.0, 0.0],
                    }
                    for info in self.ops_index.values():
                        for _codigo, _desc, necessario, estoque, _saldo, _status in info["tecidos"]:
                            totais["Tecidos"][0] += self._to_float(necessario)
                            totais["Tecidos"][1] += self._to_float(estoque)
                        for _codigo, _desc, necessario, estoque, _saldo, _status in info["aviamentos"]:
                            totais["Aviamentos"][0] += self._to_float(necessario)
                            totais["Aviamentos"][1] += self._to_float(estoque)

            for grupo in agrupado:
                self.tree_ops.insert("", "end", values=(f"GRUPO: {grupo}", "", "", "", "", "", "", "", ""), tags=("grupo",))
                for linha in agrupado[grupo]:
                    status_linha = str(linha[5]) if len(linha) > 5 else ""
                    progresso_linha_txt = str(linha[6]).replace("%", "") if len(linha) > 6 else "0"
                    try:
                        progresso_linha = float(progresso_linha_txt or 0)
                    except Exception:
                        progresso_linha = 0.0
                    tag_linha = self._tag_status_op(status_linha, progresso_linha)
                    self.tree_ops.insert("", "end", values=linha, tags=(tag_linha,) if tag_linha else ())

            carga_total = 0.0
            capacidade_total = 0.0
            for recurso, (necessario, estoque) in totais.items():
                saldo = estoque - necessario
                carga_total += necessario
                capacidade_total += estoque
                self.tree_capacidade.insert("", "end", values=(recurso, self._fmt_num(necessario), self._fmt_num(estoque), self._fmt_num(saldo)))

            uso_pct = (carga_total / capacidade_total * 100) if capacidade_total > 0 else 0.0
            ocioso_pct = max(0.0, 100.0 - uso_pct)
            if self.kpi_labels:
                self.kpi_labels[0].configure(text=f"OPs em execução: {em_execucao}")
                self.kpi_labels[1].configure(text=f"Atrasos críticos: {atrasadas}")
                self.kpi_labels[2].configure(text=f"Capacidade usada: {uso_pct:.1f}%")
                self.kpi_labels[3].configure(text=f"Ociosidade: {ocioso_pct:.1f}%")
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao carregar planejamento: {exc}")

    def _abrir_detalhe_op(self, _event=None):
        if not self.tree_ops:
            return
        item = self.tree_ops.focus()
        if not item:
            return
        valores = self.tree_ops.item(item).get("values", [])
        if not valores:
            return
        op = str(valores[0])
        if op.startswith("GRUPO:"):
            return

        dados = self.ops_index.get(op)
        if not dados:
            self._limpar_detalhes()
            return

        self.detalhe_labels["grade"].configure(text=f"Grade: {dados.get('grade') or '-'}")
        self.detalhe_labels["prazo"].configure(text=f"Prazo início: {self._data_txt(dados.get('inicio')) or '-'}")
        self.detalhe_labels["modelo"].configure(text=f"Modelo: {dados.get('modelo') or '-'}")
        self.detalhe_labels["prioridade"].configure(
            text=f"Prioridade: {dados.get('prioridade') or '-'} | Etapa: {dados.get('etapa_atual') or '-'} | Progresso: {dados.get('progresso', 0):.0f}%"
        )

        self._limpar_tree(self.tree_tecidos)
        for codigo, descricao, necessario, estoque, saldo, status in dados.get("tecidos", []):
            self.tree_tecidos.insert("", "end", values=(codigo, descricao, self._fmt_num(necessario), self._fmt_num(estoque), self._fmt_num(saldo), status))

        self._limpar_tree(self.tree_aviamentos)
        for codigo, descricao, necessario, estoque, saldo, status in dados.get("aviamentos", []):
            self.tree_aviamentos.insert("", "end", values=(codigo, descricao, self._fmt_num(necessario), self._fmt_num(estoque), self._fmt_num(saldo), status))

    # =========================================================
    # Ações
    # =========================================================
    def _reprogramar(self):
        selecionado = self.tree_ops.focus() if self.tree_ops else None
        if not selecionado:
            messagebox.showwarning("Planejamento", "Selecione uma OP para reprogramar.")
            return
        valores = self.tree_ops.item(selecionado).get("values", [])
        if not valores:
            return
        op = str(valores[0])
        if op.startswith("GRUPO:"):
            return
        schema = get_schema()
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        UPDATE {schema}.planejamento_ops
                           SET inicio = COALESCE(inicio, CURRENT_DATE) + INTERVAL '1 day',
                               prazo_inicio = COALESCE(prazo_inicio, CURRENT_DATE) + INTERVAL '1 day',
                               fim = COALESCE(fim, CURRENT_DATE) + INTERVAL '1 day',
                               periodo_fim = COALESCE(periodo_fim, CURRENT_DATE) + INTERVAL '1 day',
                               status = 'Reprogramada',
                               atualizado_em = NOW(),
                               data_atualizacao = NOW()
                         WHERE op = %s
                        """,
                        (op,),
                    )
                conn.commit()
            self._carregar_dados_planejamento()
            messagebox.showinfo("Planejamento", f"OP {op} reprogramada com sucesso.")
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao reprogramar: {exc}")

    # =========================================================
    # PDF
    # =========================================================
    def _exportar_planejamento(self):
        try:
            caminho = self._gerar_pdf_planejamento()
            self._abrir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao exportar PDF: {exc}")

    def _imprimir_planejamento(self):
        try:
            caminho = self._gerar_pdf_planejamento()
            self._imprimir_pdf(caminho)
        except Exception as exc:
            messagebox.showerror("Planejamento", f"Erro ao imprimir: {exc}")

    def _gerar_pdf_planejamento(self):
        nome = f"planejamento_producao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        caminho = os.path.abspath(nome)
        pdf = canvas.Canvas(caminho, pagesize=A4)
        largura, altura = A4
        y = self._desenhar_cabecalho_pdf(pdf, largura, altura, "Planejamento de Produção")

        periodo_txt = f"{(self.plan_inicio_entry.get() or '').strip() or '-'} até {(self.plan_fim_entry.get() or '').strip() or '-'}"
        filtro_txt = f"Programação: {self.filtro_programacao.get()} | Prioridade: {self.filtro_prioridade.get()} | Coleção: {self.filtro_colecao.get()}"

        pdf.setFillColor(colors.HexColor("#F3F4F6"))
        pdf.roundRect(30, y - 36, largura - 60, 30, 6, fill=1, stroke=0)
        pdf.setFillColor(colors.HexColor("#111827"))
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(38, y - 18, f"Período selecionado: {periodo_txt}")
        pdf.setFont("Helvetica", 8)
        pdf.drawString(38, y - 30, filtro_txt)
        y -= 48

        def nova_pagina():
            nonlocal y
            pdf.showPage()
            y = self._desenhar_cabecalho_pdf(pdf, largura, altura, "Planejamento de Produção")
            self._desenhar_rodape_pdf(pdf, largura)

        def titulo(txt):
            nonlocal y
            if y < 80:
                nova_pagina()
            pdf.setFont("Helvetica-Bold", 11)
            pdf.setFillColor(colors.HexColor("#1F5FA6"))
            pdf.drawString(36, y, txt)
            y -= 14

        def linha(txt, bold=False, cor="#111827", recuo=0, espacamento=11):
            nonlocal y
            if y < 60:
                nova_pagina()
            pdf.setFillColor(colors.HexColor(cor))
            pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 8)
            pdf.drawString(36 + recuo, y, txt)
            y -= espacamento

        def card_op(op):
            nonlocal y
            if y < 95:
                nova_pagina()
            dados = self.ops_index.get(op, {})
            grade = dados.get("grade", "-")
            modelo = dados.get("modelo", "-")
            inicio = self._data_txt(dados.get("inicio")) or "-"
            fim = self._data_txt(dados.get("fim")) or "-"
            status = dados.get("status") or "-"
            prioridade = dados.get("prioridade") or "-"
            progresso = f"{dados.get('progresso', 0):.0f}%"

            h = 52
            pdf.setFillColor(colors.HexColor("#EEF2FF"))
            pdf.roundRect(34, y - h + 6, largura - 68, h, 6, fill=1, stroke=0)
            linha(f"{op}  |  {modelo}", bold=True, cor="#0F172A", recuo=2)
            linha(f"Status: {status} | Progresso: {progresso} | Prioridade: {prioridade}", cor="#1F2937", recuo=2)
            linha(f"Prazo: {inicio} até {fim}", cor="#1F2937", recuo=2)
            linha(f"Grade: {grade}", cor="#1F2937", recuo=2)
            y -= 4

        titulo("Programações cadastradas")
        if self.tree_ops and self.tree_ops.get_children():
            for item in self.tree_ops.get_children():
                vals = self.tree_ops.item(item).get("values", [])
                if not vals:
                    continue
                if str(vals[0]).startswith("GRUPO:"):
                    linha(str(vals[0]), bold=True, cor="#374151", espacamento=13)
                else:
                    card_op(str(vals[0]))
        else:
            linha("Sem programações cadastradas.")

        y -= 8
        titulo("Resumo de materiais")
        if self.tree_capacidade and self.tree_capacidade.get_children():
            for item in self.tree_capacidade.get_children():
                vals = self.tree_capacidade.item(item).get("values", [])
                if vals:
                    linha(f"{vals[0]}  |  Necessário: {vals[1]}  |  Estoque: {vals[2]}  |  Saldo: {vals[3]}")
        else:
            linha("Sem resumo de materiais.")

        y -= 6
        titulo("Observações gerais")
        linha("• Documento gerado automaticamente com base nos filtros aplicados na tela de Planejamento de Produção.")
        linha("• Itens com status FALTA devem ser tratados antes da liberação final das ordens planejadas.")

        self._desenhar_rodape_pdf(pdf, largura)

        pdf.save()
        return caminho

    def _desenhar_cabecalho_pdf(self, pdf, largura, altura, titulo):
        header_h = 62
        pdf.setFillColor(colors.HexColor("#1F5FA6"))
        pdf.rect(0, altura - header_h, largura, header_h, fill=1, stroke=0)
        logo = self._obter_logo_pdf()
        if logo:
            try:
                pdf.drawImage(logo, 14, altura - 56, width=46, height=46, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(74, altura - 28, titulo)
        pdf.setFont("Helvetica", 9)
        pdf.drawString(74, altura - 43, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        return altura - header_h - 16

    @staticmethod
    def _obter_logo_pdf():
        base = os.path.dirname(os.path.abspath(__file__))
        # Prioriza a logomarca oficial solicitada
        for nome in ("LOGO.jpg", "ICONE_SISTEMA.png", "OPERA.jpg"):
            p = os.path.join(base, nome)
            if os.path.exists(p):
                return p
        return None

    @staticmethod
    def _desenhar_rodape_pdf(pdf, largura):
        try:
            pagina = pdf.getPageNumber()
        except Exception:
            pagina = "-"
        pdf.setStrokeColor(colors.HexColor("#D1D5DB"))
        pdf.line(30, 28, largura - 30, 28)
        pdf.setFillColor(colors.HexColor("#6B7280"))
        pdf.setFont("Helvetica", 8)
        pdf.drawString(36, 16, "Sistema OPERA • Planejamento de Produção")
        pdf.drawRightString(largura - 36, 16, f"Página {pagina}")

    def _abrir_pdf(self, caminho):
        try:
            webbrowser.open_new_tab("file://" + caminho)
        except Exception:
            if hasattr(os, "startfile"):
                os.startfile(caminho)

    def _imprimir_pdf(self, caminho):
        if hasattr(os, "startfile"):
            try:
                os.startfile(caminho, "print")
                return
            except Exception:
                pass
        self._abrir_pdf(caminho)
        messagebox.showinfo("Planejamento", "PDF aberto. Use Ctrl+P para imprimir.")

    # =========================================================
    # Calendário
    # =========================================================
    def _get_calendar_locale(self):
        idioma = getattr(self.sistema, "idioma_atual", "pt_BR")
        mapa = {
            "pt": "pt_BR",
            "pt_BR": "pt_BR",
            "en": "en_US",
            "en_US": "en_US",
            "es": "es_ES",
            "es_ES": "es_ES",
        }
        return mapa.get(idioma, "pt_BR")

    def _get_date_pattern(self):
        idioma = getattr(self.sistema, "idioma_atual", "pt_BR")
        mapa = {
            "pt": "dd/mm/yyyy",
            "pt_BR": "dd/mm/yyyy",
            "en": "mm/dd/yyyy",
            "en_US": "mm/dd/yyyy",
            "es": "dd/mm/yyyy",
            "es_ES": "dd/mm/yyyy",
        }
        return mapa.get(idioma, "dd/mm/yyyy")

    def _get_calendar_title(self):
        idioma = getattr(self.sistema, "idioma_atual", "pt_BR")
        textos = {
            "pt": "Calendário",
            "pt_BR": "Calendário",
            "en": "Calendar",
            "en_US": "Calendar",
            "es": "Calendario",
            "es_ES": "Calendario",
        }
        return textos.get(idioma, "Calendário")

    def _get_text(self, chave):
        idioma = getattr(self.sistema, "idioma_atual", "pt_BR")
        textos = {
            "pt": {
                "clear": "Limpar",
                "today": "Hoje",
                "confirm": "Confirmar",
                "calendar_missing": "A biblioteca tkcalendar não está instalada.\n\nInstale com:\npip install tkcalendar",
                "calendar_error": "Erro ao selecionar data: {erro}",
            },
            "pt_BR": {
                "clear": "Limpar",
                "today": "Hoje",
                "confirm": "Confirmar",
                "calendar_missing": "A biblioteca tkcalendar não está instalada.\n\nInstale com:\npip install tkcalendar",
                "calendar_error": "Erro ao selecionar data: {erro}",
            },
            "en": {
                "clear": "Clear",
                "today": "Today",
                "confirm": "Confirm",
                "calendar_missing": "The tkcalendar library is not installed.\n\nInstall with:\npip install tkcalendar",
                "calendar_error": "Error selecting date: {erro}",
            },
            "en_US": {
                "clear": "Clear",
                "today": "Today",
                "confirm": "Confirm",
                "calendar_missing": "The tkcalendar library is not installed.\n\nInstall with:\npip install tkcalendar",
                "calendar_error": "Error selecting date: {erro}",
            },
            "es": {
                "clear": "Limpiar",
                "today": "Hoy",
                "confirm": "Confirmar",
                "calendar_missing": "La biblioteca tkcalendar no está instalada.\n\nInstala con:\npip install tkcalendar",
                "calendar_error": "Error al seleccionar fecha: {erro}",
            },
            "es_ES": {
                "clear": "Limpiar",
                "today": "Hoy",
                "confirm": "Confirmar",
                "calendar_missing": "La biblioteca tkcalendar no está instalada.\n\nInstala con:\npip install tkcalendar",
                "calendar_error": "Error al seleccionar fecha: {erro}",
            },
        }
        idioma_textos = textos.get(idioma, textos["pt_BR"])
        return idioma_textos.get(chave, chave)

    def _abrir_calendario(self, entry_destino):
        if Calendar is None:
            messagebox.showwarning(
                self._get_calendar_title(),
                self._get_text("calendar_missing")
            )
            return

        try:
            if self._calendar_popup and self._calendar_popup.winfo_exists():
                self._calendar_popup.destroy()
        except Exception:
            pass

        popup = ctk.CTkToplevel(self)
        self._calendar_popup = popup
        popup.title(self._get_calendar_title())
        popup.geometry("320x340")
        popup.resizable(False, False)
        popup.transient(self.winfo_toplevel())
        popup.grab_set()

        try:
            popup.after(10, popup.lift)
            popup.focus_force()
        except Exception:
            pass

        try:
            x = entry_destino.winfo_rootx()
            y = entry_destino.winfo_rooty() + entry_destino.winfo_height() + 4
            popup.geometry(f"+{x}+{y}")
        except Exception:
            pass

        aparencia = ctk.get_appearance_mode().lower()

        if aparencia == "light":
            popup_fg = "#F4F6F9"
            corpo_fg = "#EDEFF3"
            rodape_fg = "transparent"

            btn_secundario = "#6B7280"
            btn_secundario_hover = "#4B5563"

            btn_hoje = "#2563EB"
            btn_hoje_hover = "#1D4ED8"

            btn_confirmar = "#60A5FA"
            btn_confirmar_hover = "#3B82F6"

            texto_btn = "#FFFFFF"
        else:
            popup_fg = "#2B2B2B"
            corpo_fg = "#343638"
            rodape_fg = "transparent"

            btn_secundario = "#4B5563"
            btn_secundario_hover = "#374151"

            btn_hoje = "#2563EB"
            btn_hoje_hover = "#1D4ED8"

            btn_confirmar = self.cor_primaria
            btn_confirmar_hover = self._hover(self.cor_primaria)

            texto_btn = "#FFFFFF"

        popup.configure(fg_color=popup_fg)

        corpo = ctk.CTkFrame(
            popup,
            fg_color=corpo_fg,
            corner_radius=10
        )
        corpo.pack(fill="both", expand=True, padx=8, pady=8)

        data_inicial = self._parse_data(entry_destino.get())
        if data_inicial is None:
            data_inicial = date.today()

        locale_escolhido = self._get_calendar_locale()
        pattern_escolhido = self._get_date_pattern()

        try:
            calendario = Calendar(
                corpo,
                selectmode="day",
                year=data_inicial.year,
                month=data_inicial.month,
                day=data_inicial.day,
                date_pattern=pattern_escolhido,
                firstweekday="sunday",
                locale=locale_escolhido,
                showweeknumbers=False
            )
        except Exception:
            calendario = Calendar(
                corpo,
                selectmode="day",
                year=data_inicial.year,
                month=data_inicial.month,
                day=data_inicial.day,
                date_pattern=pattern_escolhido,
                firstweekday="sunday",
                showweeknumbers=False
            )

        calendario.pack(fill="both", expand=True, padx=6, pady=6)

        rodape = ctk.CTkFrame(corpo, fg_color=rodape_fg)
        rodape.pack(fill="x", padx=6, pady=(0, 6))

        def confirmar():
            try:
                data_escolhida = calendario.get_date()
                entry_destino.delete(0, "end")
                entry_destino.insert(0, data_escolhida)
                popup.destroy()
            except Exception as exc:
                messagebox.showerror(
                    self._get_calendar_title(),
                    self._get_text("calendar_error").format(erro=exc)
                )

        def limpar():
            entry_destino.delete(0, "end")
            popup.destroy()

        ctk.CTkButton(
            rodape,
            text=self._get_text("clear"),
            width=90,
            height=34,
            corner_radius=8,
            command=limpar,
            fg_color=btn_secundario,
            hover_color=btn_secundario_hover,
            text_color=texto_btn,
            border_width=0,
        ).pack(side="left")

        ctk.CTkButton(
            rodape,
            text=self._get_text("today"),
            width=90,
            height=34,
            corner_radius=8,
            command=lambda: calendario.selection_set(date.today()),
            fg_color=btn_hoje,
            hover_color=btn_hoje_hover,
            text_color=texto_btn,
            border_width=0,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            rodape,
            text=self._get_text("confirm"),
            width=110,
            height=34,
            corner_radius=8,
            command=confirmar,
            fg_color=btn_confirmar,
            hover_color=btn_confirmar_hover,
            text_color=texto_btn,
            border_width=0,
        ).pack(side="right")

        popup.bind("<Escape>", lambda e: popup.destroy())


if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1500x820")
    app.title("Planejamento de Produção")
    pagina = PlanejamentoProducaoPage(app)
    pagina.pack(fill="both", expand=True)
    app.mainloop()




# ===== PATCH MULTILÍNGUE LIGADO AO MENU =====
try:
    import customtkinter as _ctk_ml
    from tkinter import ttk as _ttk_ml
except Exception:
    _ctk_ml = None
    _ttk_ml = None

def _ml_get_lang(self):
    return getattr(getattr(self, 'sistema', None), 'idioma_atual', 'pt_BR') or 'pt_BR'

def _ml_translate(self, text):
    if not text:
        return text
    lang = _ml_get_lang(self)
    mapping = getattr(self.__class__, '_TRANSLATIONS', {})
    current = mapping.get(lang, mapping.get('pt_BR', {}))
    if text in current:
        return current[text]
    for _, mp in mapping.items():
        if text in mp:
            canon = mp[text]
            return current.get(canon, canon)
    return text

def _ml_translate_list(self, values):
    return [self._ml_translate(v) for v in values]

def _ml_walk(widget):
    try:
        yield widget
        for child in widget.winfo_children():
            yield from _ml_walk(child)
    except Exception:
        return

def _ml_refresh_texts(self):
    if _ctk_ml is None:
        return
    for w in _ml_walk(self):
        try:
            if hasattr(w, 'cget'):
                try:
                    txt = w.cget('text')
                except Exception:
                    txt = None
                if isinstance(txt, str) and txt:
                    new = self._ml_translate(txt)
                    if new != txt:
                        try:
                            w.configure(text=new)
                        except Exception:
                            pass
                try:
                    ph = w.cget('placeholder_text')
                except Exception:
                    ph = None
                if isinstance(ph, str) and ph:
                    new_ph = self._ml_translate(ph)
                    if new_ph != ph:
                        try:
                            w.configure(placeholder_text=new_ph)
                        except Exception:
                            pass
        except Exception:
            pass

    # placeholders por atributo
    for attr, base in getattr(self.__class__, '_PLACEHOLDERS', {}).items():
        obj = getattr(self, attr, None)
        if obj is not None:
            try:
                obj.configure(placeholder_text=self._ml_translate(base))
            except Exception:
                pass

    # combos / option menus / segmented
    for attr, base_values in getattr(self.__class__, '_COMBOS', {}).items():
        obj = getattr(self, attr, None)
        if obj is None:
            continue
        try:
            current_value = obj.get()
        except Exception:
            current_value = None
        new_values = self._ml_translate_list(base_values)
        try:
            obj.configure(values=new_values)
        except Exception:
            pass
        if current_value:
            try:
                obj.set(self._ml_translate(current_value))
            except Exception:
                try:
                    obj.set(self._ml_translate(base_values[0]))
                except Exception:
                    pass

    # tree headings
    for attr, cols in getattr(self.__class__, '_TREE_HEADINGS', {}).items():
        tree = getattr(self, attr, None)
        if tree is None:
            continue
        try:
            for col, label in cols.items():
                tree.heading(col, text=self._ml_translate(label))
        except Exception:
            pass

    # tabview texts
    tab_names = getattr(self.__class__, '_TABS', [])
    for w in _ml_walk(self):
        if _ctk_ml and isinstance(w, _ctk_ml.CTkTabview):
            try:
                buttons = getattr(w._segmented_button, '_buttons_dict', {})
                for original in tab_names:
                    btn = buttons.get(original)
                    if btn is not None:
                        btn.configure(text=self._ml_translate(original))
            except Exception:
                pass

    # page title class attr
    try:
        if hasattr(self.__class__, 'PAGE_TITLE'):
            self.__class__.PAGE_TITLE = self._ml_translate(self.__class__.PAGE_TITLE)
    except Exception:
        pass

    try:
        self.update_idletasks()
    except Exception:
        pass

def _ml_on_language_changed(self, *_args, **_kwargs):
    try:
        self.refresh_texts()
    except Exception:
        try:
            _ml_refresh_texts(self)
        except Exception:
            pass

_TRANSLATIONS = {
 'pt_BR': {'Planejamento de Produção':'Planejamento de Produção','Production Planning':'Planejamento de Produção','Crie OPs por período, modelo, grade e prioridade. Os materiais são calculados a partir do cadastro do modelo.':'Crie OPs por período, modelo, grade e prioridade. Os materiais são calculados a partir do cadastro do modelo.','Nova Programação':'Nova Programação','New Plan':'Nova Programação','Atualizar':'Atualizar','Refresh':'Atualizar','Reprogramar +1 dia':'Reprogramar +1 dia','Reschedule +1 day':'Reprogramar +1 dia','Exportar PDF':'Exportar PDF','Export PDF':'Exportar PDF','Imprimir':'Imprimir','Print':'Imprimir','Período':'Período','Period':'Período','De':'De','From':'De','Até':'Até','To':'Até','Coleção':'Coleção','Collection':'Coleção','Prioridade':'Prioridade','Priority':'Prioridade','Programação':'Programação','Schedule':'Programação','Filtrar':'Filtrar','Filter':'Filtrar','Todas':'Todas','All':'Todas','Baixa':'Baixa','Low':'Baixa','Média':'Média','Medium':'Média','Alta':'Alta','High':'Alta','Urgente':'Urgente','Urgent':'Urgente','Semanal':'Semanal','Weekly':'Semanal','Mensal':'Mensal','Monthly':'Mensal','Trimestral':'Trimestral','Quarterly':'Trimestral','Semestral':'Semestral','Semiannual':'Semestral','OPs em execução: 0':'OPs em execução: 0','Ops in progress: 0':'OPs em execução: 0','Atrasos críticos: 0':'Atrasos críticos: 0','Critical delays: 0':'Atrasos críticos: 0','Capacidade usada: 0%':'Capacidade usada: 0%','Used capacity: 0%':'Capacidade usada: 0%','Ociosidade: 0%':'Ociosidade: 0%','Idle time: 0%':'Ociosidade: 0%','Programações / OPs':'Programações / OPs','Plans / Ops':'Programações / OPs','Resumo de Materiais':'Resumo de Materiais','Materials Summary':'Resumo de Materiais'},
 'en_US': {'Planejamento de Produção':'Production Planning','Production Planning':'Production Planning','Crie OPs por período, modelo, grade e prioridade. Os materiais são calculados a partir do cadastro do modelo.':'Create ops by period, model, size mix and priority. Materials are calculated from the model registration.','Nova Programação':'New Plan','New Plan':'New Plan','Atualizar':'Refresh','Refresh':'Refresh','Reprogramar +1 dia':'Reschedule +1 day','Reschedule +1 day':'Reschedule +1 day','Exportar PDF':'Export PDF','Export PDF':'Export PDF','Imprimir':'Print','Print':'Print','Período':'Period','Period':'Period','De':'From','From':'From','Até':'To','To':'To','Coleção':'Collection','Collection':'Collection','Prioridade':'Priority','Priority':'Priority','Programação':'Schedule','Schedule':'Schedule','Filtrar':'Filter','Filter':'Filter','Todas':'All','All':'All','Baixa':'Low','Low':'Low','Média':'Medium','Medium':'Medium','Alta':'High','High':'High','Urgente':'Urgent','Urgent':'Urgent','Semanal':'Weekly','Weekly':'Weekly','Mensal':'Monthly','Monthly':'Monthly','Trimestral':'Quarterly','Quarterly':'Quarterly','Semestral':'Semiannual','Semiannual':'Semiannual','OPs em execução: 0':'Ops in progress: 0','Ops in progress: 0':'Ops in progress: 0','Atrasos críticos: 0':'Critical delays: 0','Critical delays: 0':'Critical delays: 0','Capacidade usada: 0%':'Used capacity: 0%','Used capacity: 0%':'Used capacity: 0%','Ociosidade: 0%':'Idle time: 0%','Idle time: 0%':'Idle time: 0%','Programações / OPs':'Plans / Ops','Plans / Ops':'Plans / Ops','Resumo de Materiais':'Materials Summary','Materials Summary':'Materials Summary'},
 'es_ES': {'Planejamento de Produção':'Planificación de Producción','Production Planning':'Planificación de Producción','Crie OPs por período, modelo, grade e prioridade. Os materiais são calculados a partir do cadastro do modelo.':'Cree OPs por período, modelo, tallas y prioridad. Los materiales se calculan a partir del registro del modelo.','Nova Programação':'Nueva Programación','New Plan':'Nueva Programación','Atualizar':'Actualizar','Refresh':'Actualizar','Reprogramar +1 dia':'Reprogramar +1 día','Reschedule +1 day':'Reprogramar +1 día','Exportar PDF':'Exportar PDF','Export PDF':'Exportar PDF','Imprimir':'Imprimir','Print':'Imprimir','Período':'Período','Period':'Período','De':'Desde','From':'Desde','Até':'Hasta','To':'Hasta','Coleção':'Colección','Collection':'Colección','Prioridade':'Prioridad','Priority':'Prioridad','Programação':'Programación','Schedule':'Programación','Filtrar':'Filtrar','Filter':'Filtrar','Todas':'Todas','All':'Todas','Baixa':'Baja','Low':'Baja','Média':'Media','Medium':'Media','Alta':'Alta','High':'Alta','Urgente':'Urgente','Urgent':'Urgente','Semanal':'Semanal','Weekly':'Semanal','Mensal':'Mensual','Monthly':'Mensual','Trimestral':'Trimestral','Quarterly':'Trimestral','Semestral':'Semestral','Semiannual':'Semestral','OPs em execução: 0':'OPs en ejecución: 0','Ops in progress: 0':'OPs en ejecución: 0','Atrasos críticos: 0':'Retrasos críticos: 0','Critical delays: 0':'Retrasos críticos: 0','Capacidade usada: 0%':'Capacidad usada: 0%','Used capacity: 0%':'Capacidad usada: 0%','Ociosidade: 0%':'Ociosidad: 0%','Idle time: 0%':'Ociosidad: 0%','Programações / OPs':'Programaciones / OPs','Plans / Ops':'Programaciones / OPs','Resumo de Materiais':'Resumen de Materiales','Materials Summary':'Resumen de Materiales'}
}
_TREE_HEADINGS = {'tree_ops': {'op':'OP','modelo':'Modelo','qtde':'Qtde','inicio':'Início','fim':'Fim','status':'Status','progresso':'Progresso','programacao':'Programação','colecao':'Coleção'}, 'tree_capacidade': {'recurso':'Recurso','capacidade':'Capacidade','ocupacao':'Ocupação','saldo':'Saldo'}, 'tree_tecidos': {'codigo':'Código','descricao':'Descrição','necessario':'Necessário','estoque':'Estoque','saldo':'Saldo'}, 'tree_aviamentos': {'codigo':'Código','descricao':'Descrição','necessario':'Necessário','estoque':'Estoque','saldo':'Saldo'}}
_PLACEHOLDERS = {'plan_inicio_entry':'De','plan_fim_entry':'Até'}
_COMBOS = {'filtro_colecao':['Todas'], 'filtro_prioridade':['Todas','Baixa','Média','Alta','Urgente'], 'filtro_programacao':['Todas','Semanal','Mensal','Trimestral','Semestral','Coleção']}
_TABS = []

PlanejamentoProducaoPage._TRANSLATIONS = _TRANSLATIONS
PlanejamentoProducaoPage._TREE_HEADINGS = _TREE_HEADINGS
PlanejamentoProducaoPage._PLACEHOLDERS = _PLACEHOLDERS
PlanejamentoProducaoPage._COMBOS = _COMBOS
PlanejamentoProducaoPage._TABS = _TABS

PlanejamentoProducaoPage._ml_translate = _ml_translate
PlanejamentoProducaoPage._ml_translate_list = _ml_translate_list
PlanejamentoProducaoPage.refresh_texts = _ml_refresh_texts
PlanejamentoProducaoPage.on_language_changed = _ml_on_language_changed
