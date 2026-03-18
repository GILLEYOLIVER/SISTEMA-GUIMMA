# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, date, time
from tkinter import ttk, messagebox
import tkinter as tk
import customtkinter as ctk

try:
    from tkcalendar import Calendar
except Exception:
    Calendar = None

try:
    from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready
except Exception:
    from BANCO_DE_DADOS_PG import get_conn, get_schema, require_ready


PROGRAMACOES = ["Todas", "Semanal", "Mensal", "Trimestral", "Semestral", "Coleção"]


class OrdensPlanejadasPage(ctk.CTkFrame):
    def __init__(self, master=None, sistema=None, **kwargs):
        super().__init__(master, **kwargs)
        self.sistema = sistema
        self.ops_index = {}
        self._colecoes_cache = ["Todas"]
        self._calendar_popup = None

        self.cor_fundo = getattr(sistema, "cor_fundo", "#F5F5F5")
        self.cor_texto = getattr(sistema, "cor_texto", "#111827")
        self.cor_primaria = getattr(sistema, "cor_primaria", "#3A7EBF")
        self.cor_hover = getattr(sistema, "cor_hover", "#2E4A66")
        self.cor_borda = getattr(sistema, "cor_borda", "#CBD5E1")

        self.configure(fg_color=self.cor_fundo)
        self._build()
        self._carregar_colecoes()
        self._carregar_ops()
        try:
            self.refresh_texts()
        except Exception:
            pass


    # =========================================================
    # UI
    # =========================================================
    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Ordens Planejadas",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.cor_texto,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        box = ctk.CTkFrame(
            self,
            border_width=1,
            border_color=self.cor_borda,
            fg_color=self.cor_fundo,
        )
        box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        box.grid_rowconfigure(2, weight=1)
        box.grid_columnconfigure(0, weight=1)

        barra = ctk.CTkFrame(box, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        barra.grid_columnconfigure(20, weight=1)

        ctk.CTkButton(
            barra,
            text="Atualizar",
            width=135,
            command=self._carregar_ops,
            fg_color=self.cor_primaria,
            hover_color=self._hover(self.cor_primaria),
            text_color="white",
        ).grid(row=0, column=0, padx=(0, 8), pady=4)

        ctk.CTkButton(
            barra,
            text="Abrir na Nova Ordem",
            width=170,
            command=self._abrir_na_nova_ordem,
            fg_color=self.cor_primaria,
            hover_color=self._hover(self.cor_primaria),
            text_color="white",
        ).grid(row=0, column=1, padx=(0, 8), pady=4)

        filtros = ctk.CTkFrame(box, fg_color="transparent")
        filtros.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        for col in range(13):
            filtros.grid_columnconfigure(col, weight=0)
        filtros.grid_columnconfigure(12, weight=1)

        # Linha 1
        ctk.CTkLabel(
            filtros, text="Tempo", text_color=self.cor_texto
        ).grid(row=0, column=0, padx=(0, 6), pady=4, sticky="w")

        self.filtro_programacao = ctk.CTkOptionMenu(
            filtros,
            values=PROGRAMACOES,
            width=145,
            fg_color=self.cor_primaria,
            button_color=self.cor_primaria,
            button_hover_color=self._hover(self.cor_primaria),
        )
        self.filtro_programacao.set("Todas")
        self.filtro_programacao.grid(row=0, column=1, padx=(0, 10), pady=4)

        ctk.CTkLabel(
            filtros, text="Coleção", text_color=self.cor_texto
        ).grid(row=0, column=2, padx=(0, 6), pady=4, sticky="w")

        self.filtro_colecao = ctk.CTkComboBox(
            filtros,
            values=["Todas"],
            width=165
        )
        self.filtro_colecao.set("Todas")
        self.filtro_colecao.grid(row=0, column=3, padx=(0, 10), pady=4)

        ctk.CTkLabel(
            filtros, text="Cód. Modelo", text_color=self.cor_texto
        ).grid(row=0, column=4, padx=(0, 6), pady=4, sticky="w")

        self.filtro_codigo = ctk.CTkEntry(
            filtros,
            placeholder_text="Código",
            width=140
        )
        self.filtro_codigo.grid(row=0, column=5, padx=(0, 10), pady=4)

        ctk.CTkLabel(
            filtros, text="Descrição", text_color=self.cor_texto
        ).grid(row=0, column=6, padx=(0, 6), pady=4, sticky="w")

        self.filtro_modelo = ctk.CTkEntry(
            filtros,
            placeholder_text="Descrição do modelo",
            width=240
        )
        self.filtro_modelo.grid(row=0, column=7, padx=(0, 10), pady=4)

        ctk.CTkButton(
            filtros,
            text="Filtrar",
            width=100,
            command=self._carregar_ops,
            fg_color=self.cor_primaria,
            hover_color=self._hover(self.cor_primaria),
            text_color="white",
        ).grid(row=0, column=8, padx=(0, 6), pady=4)

        ctk.CTkButton(
            filtros,
            text="Limpar Filtros",
            width=120,
            command=self._limpar_filtros,
            fg_color="#6B7280",
            hover_color=self._hover("#6B7280"),
            text_color="white",
        ).grid(row=0, column=9, padx=(0, 6), pady=4)

        # Linha 2
        ctk.CTkLabel(
            filtros, text="Data de", text_color=self.cor_texto
        ).grid(row=1, column=0, padx=(0, 6), pady=4, sticky="w")

        frame_data_de = ctk.CTkFrame(filtros, fg_color="transparent")
        frame_data_de.grid(row=1, column=1, padx=(0, 10), pady=4, sticky="w")

        self.filtro_data_de = ctk.CTkEntry(
            frame_data_de,
            placeholder_text="dd/mm/aaaa",
            width=120
        )
        self.filtro_data_de.pack(side="left", padx=(0, 4))
        self.filtro_data_de.bind("<Button-1>", lambda e: self._abrir_calendario(self.filtro_data_de))

        self.btn_data_de = ctk.CTkButton(
            frame_data_de,
            text="📅",
            width=34,
            command=lambda: self._abrir_calendario(self.filtro_data_de),
            fg_color=self.cor_primaria,
            hover_color=self._hover(self.cor_primaria),
            text_color="white",
        )
        self.btn_data_de.pack(side="left")

        ctk.CTkLabel(
            filtros, text="Data até", text_color=self.cor_texto
        ).grid(row=1, column=2, padx=(0, 6), pady=4, sticky="w")

        frame_data_ate = ctk.CTkFrame(filtros, fg_color="transparent")
        frame_data_ate.grid(row=1, column=3, padx=(0, 10), pady=4, sticky="w")

        self.filtro_data_ate = ctk.CTkEntry(
            frame_data_ate,
            placeholder_text="dd/mm/aaaa",
            width=120
        )
        self.filtro_data_ate.pack(side="left", padx=(0, 4))
        self.filtro_data_ate.bind("<Button-1>", lambda e: self._abrir_calendario(self.filtro_data_ate))

        self.btn_data_ate = ctk.CTkButton(
            frame_data_ate,
            text="📅",
            width=34,
            command=lambda: self._abrir_calendario(self.filtro_data_ate),
            fg_color=self.cor_primaria,
            hover_color=self._hover(self.cor_primaria),
            text_color="white",
        )
        self.btn_data_ate.pack(side="left")

        ctk.CTkLabel(
            filtros, text="Hora de", text_color=self.cor_texto
        ).grid(row=1, column=4, padx=(0, 6), pady=4, sticky="w")

        self.filtro_hora_de = ctk.CTkEntry(
            filtros,
            placeholder_text="hh:mm",
            width=90
        )
        self.filtro_hora_de.grid(row=1, column=5, padx=(0, 10), pady=4)

        ctk.CTkLabel(
            filtros, text="Hora até", text_color=self.cor_texto
        ).grid(row=1, column=6, padx=(0, 6), pady=4, sticky="w")

        self.filtro_hora_ate = ctk.CTkEntry(
            filtros,
            placeholder_text="hh:mm",
            width=90
        )
        self.filtro_hora_ate.grid(row=1, column=7, padx=(0, 10), pady=4)

        info = ctk.CTkLabel(
            filtros,
            text="A data/hora usa atualizado_em; se vazio, usa criado_em.",
            text_color="#6B7280",
            font=ctk.CTkFont(size=11),
        )
        info.grid(row=1, column=8, columnspan=5, sticky="w", padx=(8, 0), pady=4)

        self.tree = ttk.Treeview(
            box,
            columns=(
                "op",
                "codigo",
                "modelo",
                "programacao",
                "colecao",
                "qtd",
                "inicio",
                "fim",
                "status",
                "progresso",
                "atualizado_em",
            ),
            show="headings",
            height=20,
        )

        colunas = (
            ("op", "OP", 115, "center"),
            ("codigo", "Cód. Modelo", 120, "center"),
            ("modelo", "Modelo", 280, "w"),
            ("programacao", "Tempo", 110, "center"),
            ("colecao", "Coleção", 120, "center"),
            ("qtd", "Qtde", 80, "center"),
            ("inicio", "Início", 95, "center"),
            ("fim", "Fim", 95, "center"),
            ("status", "Status", 110, "center"),
            ("progresso", "Progresso", 90, "center"),
            ("atualizado_em", "Atualizado em", 145, "center"),
        )

        for col, txt, w, anc in colunas:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor=anc)

        self.tree.grid(row=2, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))

        scroll_y = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.grid(row=2, column=1, sticky="ns", pady=(0, 10))

        scroll_x = ttk.Scrollbar(box, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=scroll_x.set)
        scroll_x.grid(row=3, column=0, sticky="ew", padx=(10, 0), pady=(0, 10))

        self.tree.bind("<Double-1>", lambda _e: self._abrir_na_nova_ordem())

        for entry in (
            self.filtro_codigo,
            self.filtro_modelo,
            self.filtro_data_de,
            self.filtro_data_ate,
            self.filtro_hora_de,
            self.filtro_hora_ate,
        ):
            entry.bind("<Return>", lambda _e: self._carregar_ops())

    # =========================================================
    # Abertura da página
    # =========================================================
    def on_page_open(self):
        self._carregar_colecoes()
        self._carregar_ops()

    # =========================================================
    # Utilitários
    # =========================================================
    def _db_ready(self):
        ok, msg = require_ready()
        if not ok:
            messagebox.showerror("Ordens Planejadas", msg)
        return ok

    def _hover(self, cor_hex):
        try:
            cor_hex = cor_hex.lstrip("#")
            r = int(cor_hex[0:2], 16)
            g = int(cor_hex[2:4], 16)
            b = int(cor_hex[4:6], 16)
            fator = 0.85
            return f"#{int(r * fator):02x}{int(g * fator):02x}{int(b * fator):02x}"
        except Exception:
            return "#2E4A66"

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

    @staticmethod
    def _fmt_data(d):
        if not d:
            return ""
        try:
            return d.strftime("%d/%m/%Y")
        except Exception:
            return str(d)

    @staticmethod
    def _fmt_data_hora(d):
        if not d:
            return ""
        try:
            return d.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(d)

    @staticmethod
    def _parse_data(texto: str | None):
        if not texto:
            return None
        texto = str(texto).strip()
        if not texto:
            return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(texto, fmt).date()
            except Exception:
                continue
        return None

    @staticmethod
    def _parse_hora(texto: str | None):
        if not texto:
            return None
        texto = str(texto).strip()
        if not texto:
            return None
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(texto, fmt).time()
            except Exception:
                continue
        return None

    @staticmethod
    def _montar_datetime(data_obj: date | None, hora_obj: time | None, fim_do_dia=False):
        if not data_obj:
            return None
        if hora_obj:
            return datetime.combine(data_obj, hora_obj)
        if fim_do_dia:
            return datetime.combine(data_obj, time(23, 59, 59))
        return datetime.combine(data_obj, time(0, 0, 0))

    @staticmethod
    def _calcular_percentuais_grade(grade_rows, quantidade_total):
        tamanhos = ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"]
        percentuais = {tam: 0.0 for tam in tamanhos}
        for tamanho, qtd, pct_salvo in (grade_rows or []):
            tam = str(tamanho or "").strip().upper()
            if tam not in percentuais:
                continue
            if pct_salvo is not None:
                percentuais[tam] = float(pct_salvo or 0)
        return percentuais

    # =========================================================
    # Calendário
    # =========================================================
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

        # =========================================================
        # CORES ADAPTADAS AO TEMA
        # =========================================================
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
                self.after(50, self._carregar_ops)
            except Exception as exc:
                messagebox.showerror(
                    self._get_calendar_title(),
                    self._get_text("calendar_error").format(erro=exc)
                )

        def limpar():
            entry_destino.delete(0, "end")
            popup.destroy()
            self.after(50, self._carregar_ops)

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

    # =========================================================
    # Coleções
    # =========================================================
    def _carregar_colecoes(self):
        if not self._db_ready():
            return

        schema = get_schema()
        valores = ["Todas"]

        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT DISTINCT COALESCE(NULLIF(TRIM(colecao), ''), '')
                      FROM {schema}.planejamento_ops
                     ORDER BY 1
                    """
                )
                encontrados = [
                    str(row[0]).strip()
                    for row in cur.fetchall()
                    if str(row[0] or "").strip()
                ]
                if encontrados:
                    valores.extend(encontrados)
        except Exception:
            pass

        self._colecoes_cache = valores

        try:
            atual = self.filtro_colecao.get().strip()
        except Exception:
            atual = "Todas"

        self.filtro_colecao.configure(values=valores)
        self.filtro_colecao.set(atual if atual in valores else "Todas")

    def _limpar_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _limpar_filtros(self):
        self.filtro_programacao.set("Todas")
        self.filtro_colecao.set("Todas")
        self.filtro_codigo.delete(0, "end")
        self.filtro_modelo.delete(0, "end")
        self.filtro_data_de.delete(0, "end")
        self.filtro_data_ate.delete(0, "end")
        self.filtro_hora_de.delete(0, "end")
        self.filtro_hora_ate.delete(0, "end")
        self._carregar_ops()

    # =========================================================
    # Carga principal
    # =========================================================
    def _carregar_ops(self):
        if not self._db_ready():
            return

        self._limpar_tree()
        self.ops_index = {}
        schema = get_schema()

        programacao = (self.filtro_programacao.get() or "Todas").strip()
        colecao = (self.filtro_colecao.get() or "Todas").strip()
        codigo_modelo = (self.filtro_codigo.get() or "").strip()
        descricao_modelo = (self.filtro_modelo.get() or "").strip()

        data_de = self._parse_data(self.filtro_data_de.get())
        data_ate = self._parse_data(self.filtro_data_ate.get())
        hora_de = self._parse_hora(self.filtro_hora_de.get())
        hora_ate = self._parse_hora(self.filtro_hora_ate.get())

        dt_de = self._montar_datetime(data_de, hora_de, fim_do_dia=False)
        dt_ate = self._montar_datetime(data_ate, hora_ate, fim_do_dia=True)

        if self.filtro_hora_de.get().strip() and not hora_de:
            messagebox.showwarning(
                "Ordens Planejadas",
                "Hora inicial inválida. Use o formato hh:mm."
            )
            return

        if self.filtro_hora_ate.get().strip() and not hora_ate:
            messagebox.showwarning(
                "Ordens Planejadas",
                "Hora final inválida. Use o formato hh:mm."
            )
            return

        if self.filtro_data_de.get().strip() and not data_de:
            messagebox.showwarning(
                "Ordens Planejadas",
                "Data inicial inválida. Use o formato dd/mm/aaaa."
            )
            return

        if self.filtro_data_ate.get().strip() and not data_ate:
            messagebox.showwarning(
                "Ordens Planejadas",
                "Data final inválida. Use o formato dd/mm/aaaa."
            )
            return

        if dt_de and dt_ate and dt_ate < dt_de:
            messagebox.showwarning(
                "Ordens Planejadas",
                "O intervalo de data/hora está inválido."
            )
            return

        filtros = [
            f"""
            NOT EXISTS (
                SELECT 1
                  FROM {schema}.planejamento_ordens_geradas pog
                 WHERE pog.planejamento_id = p.id
            )
            """,
            f"""
            NOT EXISTS (
                SELECT 1
                  FROM {schema}.ordem_corte_ficha ocf
                 WHERE COALESCE(ocf.planejamento_op_id, 0) = p.id
            )
            """,
        ]
        params = []

        if programacao != "Todas":
            filtros.append("COALESCE(p.programacao, 'Mensal') = %s")
            params.append(programacao)

        if colecao != "Todas":
            filtros.append("COALESCE(p.colecao, '') = %s")
            params.append(colecao)

        if codigo_modelo:
            filtros.append("COALESCE(p.codigo_modelo, '') ILIKE %s")
            params.append(f"%{codigo_modelo}%")

        if descricao_modelo:
            filtros.append("COALESCE(p.descricao_modelo, p.modelo, '') ILIKE %s")
            params.append(f"%{descricao_modelo}%")

        if dt_de:
            filtros.append("COALESCE(p.atualizado_em, p.criado_em) >= %s")
            params.append(dt_de)

        if dt_ate:
            filtros.append("COALESCE(p.atualizado_em, p.criado_em) <= %s")
            params.append(dt_ate)

        where_sql = " AND ".join(f"({f})" for f in filtros)

        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        p.id,
                        p.op,
                        COALESCE(p.codigo_modelo, ''),
                        COALESCE(p.descricao_modelo, p.modelo, p.codigo_modelo, ''),
                        COALESCE(p.quantidade, p.total_grade, 0),
                        COALESCE(p.prazo_inicio, p.inicio),
                        COALESCE(p.periodo_fim, p.fim),
                        COALESCE(p.status, 'Planejada'),
                        COALESCE(p.percentual_progresso, 0),
                        COALESCE(p.prioridade, 'Média'),
                        COALESCE(p.programacao, 'Mensal'),
                        COALESCE(p.colecao, ''),
                        COALESCE(p.criado_em, NOW()),
                        COALESCE(p.atualizado_em, p.criado_em, NOW())
                    FROM {schema}.planejamento_ops p
                    WHERE {where_sql}
                    ORDER BY
                        COALESCE(p.programacao, 'Mensal'),
                        COALESCE(p.colecao, ''),
                        COALESCE(p.prazo_inicio, p.inicio, CURRENT_DATE),
                        p.op
                    """,
                    params,
                )
                rows = cur.fetchall()

                for row in rows:
                    (
                        pid,
                        op,
                        codigo,
                        modelo,
                        qtd,
                        inicio,
                        fim,
                        status,
                        progresso,
                        prioridade,
                        programacao_op,
                        colecao_op,
                        criado_em,
                        atualizado_em,
                    ) = row

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
                        "programacao": programacao_op,
                        "colecao": colecao_op,
                        "criado_em": self._fmt_data_hora(criado_em),
                        "atualizado_em": self._fmt_data_hora(atualizado_em),
                        "grade_percentuais": grade_percentuais,
                    }

                    self.tree.insert(
                        "",
                        "end",
                        values=(
                            op,
                            codigo,
                            modelo,
                            programacao_op,
                            colecao_op,
                            qtd,
                            self._fmt_data(inicio),
                            self._fmt_data(fim),
                            status,
                            f"{float(progresso or 0):.0f}%",
                            self._fmt_data_hora(atualizado_em),
                        ),
                    )

        except Exception as exc:
            messagebox.showerror("Ordens Planejadas", f"Erro ao carregar OPs: {exc}")

    # =========================================================
    # Fluxo para Nova Ordem
    # =========================================================
    def _abrir_na_nova_ordem(self):
        item = self.tree.focus()
        if not item:
            selecionados = self.tree.selection()
            if selecionados:
                item = selecionados[0]

        if not item:
            messagebox.showwarning(
                "Ordens Planejadas",
                "Selecione uma OP para abrir na Nova Ordem."
            )
            return

        valores = self.tree.item(item).get("values", [])
        if not valores:
            messagebox.showwarning(
                "Ordens Planejadas",
                "Não foi possível localizar a OP selecionada."
            )
            return

        op = str(valores[0])
        dados = self.ops_index.get(op)

        if not dados:
            messagebox.showwarning(
                "Ordens Planejadas",
                "Não foi possível localizar os dados da OP selecionada."
            )
            return

        if self.sistema and hasattr(self.sistema, "open_page"):
            self.sistema._ordem_planejada_prefill = dados
            self.sistema.open_page("Nova Ordem")
            return

        messagebox.showinfo(
            "Ordens Planejadas",
            "Teste isolado: os dados da OP foram carregados.\n"
            "No sistema completo, esta ação abrirá a página Nova Ordem."
        )


# =========================================================
# TESTE ISOLADO
# =========================================================
    _I18N_MAP = {'en_US': {'Ordens Planejadas': 'Planned Orders', 'Atualizar': 'Refresh', 'Abrir na Nova Ordem': 'Open in New Order', 'Tempo': 'Time', 'Coleção': 'Collection', 'Cód. Modelo': 'Model Code', 'Código': 'Code', 'Descrição': 'Description', 'Descrição do modelo': 'Model description', 'Filtrar': 'Filter', 'Limpar Filtros': 'Clear Filters', 'Data de': 'Date from', 'Data até': 'Date to', 'Hora de': 'Time from', 'Hora até': 'Time to', 'A data/hora usa atualizado_em; se vazio, usa criado_em.': 'Date/time uses atualizado_em; if empty, criado_em is used.', 'Todas': 'All', 'Semanal': 'Weekly', 'Mensal': 'Monthly', 'Trimestral': 'Quarterly', 'Semestral': 'Semiannual', 'dd/mm/aaaa': 'dd/mm/yyyy', 'hh:mm': 'hh:mm', 'OP': 'WO', 'Modelo': 'Model', 'Qtde': 'Qty', 'Início': 'Start', 'Fim': 'End', 'Status': 'Status', 'Progresso': 'Progress', 'Atualizado em': 'Updated at', 'Teste Isolado - Ordens Planejadas': 'Standalone Test - Planned Orders'}, 'es_ES': {'Ordens Planejadas': 'Órdenes Planificadas', 'Atualizar': 'Actualizar', 'Abrir na Nova Ordem': 'Abrir en Nueva Orden', 'Tempo': 'Tiempo', 'Coleção': 'Colección', 'Cód. Modelo': 'Cód. Modelo', 'Código': 'Código', 'Descrição': 'Descripción', 'Descrição do modelo': 'Descripción del modelo', 'Filtrar': 'Filtrar', 'Limpar Filtros': 'Limpiar Filtros', 'Data de': 'Fecha desde', 'Data até': 'Fecha hasta', 'Hora de': 'Hora desde', 'Hora até': 'Hora hasta', 'A data/hora usa atualizado_em; se vazio, usa criado_em.': 'La fecha/hora usa actualizado_em; si está vacío, usa criado_em.', 'Todas': 'Todas', 'Semanal': 'Semanal', 'Mensal': 'Mensual', 'Trimestral': 'Trimestral', 'Semestral': 'Semestral', 'dd/mm/aaaa': 'dd/mm/aaaa', 'hh:mm': 'hh:mm', 'OP': 'OP', 'Modelo': 'Modelo', 'Qtde': 'Cant', 'Início': 'Inicio', 'Fim': 'Fin', 'Status': 'Estado', 'Progresso': 'Progreso', 'Atualizado em': 'Actualizado en', 'Teste Isolado - Ordens Planejadas': 'Prueba aislada - Órdenes Planificadas'}}

    def _get_idioma_atual(self):
        try:
            if getattr(self, "sistema", None) is not None:
                return getattr(self.sistema, "idioma_atual", "pt_BR") or "pt_BR"
        except Exception:
            pass
        return getattr(self, "idioma_atual", "pt_BR") or "pt_BR"

    def _canonical_i18n_text(self, text):
        if text is None:
            return text
        s = str(text)
        maps = getattr(self, "_I18N_MAP", {}) or {}
        if s in maps.get("pt_BR", {}):
            return s
        for _lang, table in maps.items():
            for pt_key, translated in table.items():
                if s == translated:
                    return pt_key
        return s

    def _translate_i18n_text(self, text):
        if text is None:
            return text
        idioma = self._get_idioma_atual()
        maps = getattr(self, "_I18N_MAP", {}) or {}
        canonical = self._canonical_i18n_text(text)
        return maps.get(idioma, {}).get(canonical, canonical)

    def _translate_i18n_values(self, values):
        if not isinstance(values, (list, tuple)):
            return values
        return [self._translate_i18n_text(v) for v in values]

    def _refresh_widget_i18n(self, widget):
        try:
            if hasattr(widget, "cget"):
                try:
                    text = widget.cget("text")
                    if isinstance(text, str) and text:
                        new_text = self._translate_i18n_text(text)
                        if new_text != text:
                            widget.configure(text=new_text)
                except Exception:
                    pass

                try:
                    placeholder = widget.cget("placeholder_text")
                    if isinstance(placeholder, str) and placeholder:
                        new_placeholder = self._translate_i18n_text(placeholder)
                        if new_placeholder != placeholder:
                            widget.configure(placeholder_text=new_placeholder)
                except Exception:
                    pass

                try:
                    values = widget.cget("values")
                    if isinstance(values, (list, tuple)) and values:
                        current = None
                        try:
                            current = widget.get()
                        except Exception:
                            current = None
                        translated_values = self._translate_i18n_values(list(values))
                        widget.configure(values=translated_values)
                        if current:
                            widget.set(self._translate_i18n_text(current))
                except Exception:
                    pass

            if isinstance(widget, ttk.Treeview):
                try:
                    for col in widget["columns"]:
                        info = widget.heading(col)
                        heading_text = info.get("text", "")
                        if heading_text:
                            widget.heading(col, text=self._translate_i18n_text(heading_text))
                except Exception:
                    pass

            for child in widget.winfo_children():
                self._refresh_widget_i18n(child)
        except Exception:
            pass

    def refresh_texts(self):
        try:
            target = getattr(self, "root", None) or self
            self._refresh_widget_i18n(target)
        except Exception:
            pass

        try:
            if hasattr(self, "root") and self.root:
                self.root.title(self._translate_i18n_text(self.root.title()))
        except Exception:
            pass

        try:
            if hasattr(self, "PAGE_TITLE"):
                self.PAGE_TITLE = self._translate_i18n_text(self.PAGE_TITLE)
        except Exception:
            pass

if __name__ == "__main__":
    class SistemaMock:
        def __init__(self):
            self.cor_fundo = "#F5F5F5"
            self.cor_texto = "#111827"
            self.cor_primaria = "#60A5FA"
            self.cor_hover = "#2563EB"
            self.cor_borda = "#CBD5E1"
            self.idioma_atual = "pt_BR"
            self._ordem_planejada_prefill = None

        def open_page(self, nome):
            print(f"[TESTE] open_page chamado: {nome}")
            print(f"[TESTE] prefill: {self._ordem_planejada_prefill}")

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Teste Isolado - Ordens Planejadas")
    app.geometry("1560x860")

    pagina = OrdensPlanejadasPage(app, sistema=SistemaMock())
    pagina.pack(fill="both", expand=True)

    app.mainloop()