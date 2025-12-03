# ================================================================
#  TEMA2.py — Editor Profissional de Temas OPERA
#  Layout: MODELO A (Sidebar + Editor + Preview)
#  Cores: 20 propriedades profissionais
#  Tema Base: CLARO / Moderno / Material Design
#  Animações: Ativadas (hover, fade, shadow, transitions)
#  Integração total com tema_database.py e MENU_PRINCIPAL
# ================================================================

from __future__ import annotations
import os
import json
import tkinter as tk
from tkinter import ttk, colorchooser
import customtkinter as ctk
from typing import Dict, Any, Optional, Tuple

from tema_database import DatabaseTemaManager

# ================================================================
# ANIMAÇÕES / MICRO TRANSIÇÕES
# ================================================================

def animar_cor(widget, start, end, steps=12, delay=15):
    """
    Transição suave entre duas cores.
    Converte HEX -> RGB -> interpolação -> HEX.
    """
    try:
        start = start.lstrip("#")
        end = end.lstrip("#")
        sr, sg, sb = int(start[0:2], 16), int(start[2:4], 16), int(start[4:6], 16)
        er, eg, eb = int(end[0:2], 16), int(end[2:4], 16), int(end[4:6], 16)
    except:
        return  # erro silencioso

    def step(i=0):
        if i > steps:
            return
        r = int(sr + (er - sr) * (i / steps))
        g = int(sg + (eg - sg) * (i / steps))
        b = int(sb + (eb - sb) * (i / steps))
        widget.configure(fg_color=f"#{r:02x}{g:02x}{b:02x}")
        widget.after(delay, lambda: step(i + 1))

    step()


def cor_contraste(hex_color: str) -> str:
    """Texto preto/branco conforme a luminosidade."""
    try:
        hex_color = hex_color.lstrip("#")
        r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        luminancia = (0.2126*r + 0.7152*g + 0.0722*b)
        return "#000000" if luminancia > 150 else "#FFFFFF"
    except:
        return "#000000"


# ================================================================
#  PALETA BASE (20 CORES) — CLARO / PROFISSIONAL
# ================================================================

PADROES_COMPLETOS: Dict[str, Dict[str, str]] = {
    "Clássico Claro": {
        # Core
        "fundo": "#F5F6F8",
        "primaria": "#E4E7EB",
        "secundaria": "#FFFFFF",
        "terciaria": "#F0F1F3",
        "borda": "#D0D5DA",
        "sombra": "#C5C9D0",

        # Typography & Interaction
        "texto_principal": "#1D1D1F",
        "texto_secundario": "#4A4A4C",
        "hover": "#EAECEF",
        "foco": "#3B82F6",
        "selecao": "#D3E4FF",
        "highlight": "#0078FF",

        # Buttons
        "botao_salvar": "#3B82F6",
        "botao_excluir": "#E53935",
        "botao_novo": "#00A884",
        "botao_cancelar": "#9CA3AF",

        # Feedback
        "sucesso": "#4CAF50",
        "alerta": "#FFB300",
        "erro": "#D32F2F",
        "info": "#0288D1",
    }
}

DEFAULT_TEMA = PADROES_COMPLETOS["Clássico Claro"]

# ================================================================
#  Funções auxiliares
# ================================================================

def normalizar_hex(valor: str, fallback="#000000") -> str:
    """Garante que a cor seja um HEX válido de 6 dígitos."""
    if not valor or not isinstance(valor, str):
        return fallback
    v = valor.strip().upper()
    if not v.startswith("#"):
        return fallback
    v = v[1:]
    if len(v) < 6:
        return fallback
    try:
        int(v[:6], 16)
        return f"#{v[:6]}"
    except:
        return fallback


def paleta_segura(paleta: Dict[str, str]) -> Dict[str, str]:
    segura = {}
    for k, v in paleta.items():
        segura[k] = normalizar_hex(v, DEFAULT_TEMA.get(k, "#000000"))
    return segura


# ================================================================
#  CLASSE PRINCIPAL — Tema2Page
# ================================================================

class Tema2Page(ctk.CTkFrame):
    """
    Editor profissional de temas — Sidebar + Editor + Preview.
    Com animações, 20 cores profissionais, e integração com PostgreSQL.
    """

    PADROES = PADROES_COMPLETOS

    # Lista das 20 propriedades em ordem visual de edição
    CAMPOS_COR = [
        # Core
        ("fundo", "Fundo Geral"),
        ("primaria", "Primária"),
        ("secundaria", "Secundária"),
        ("terciaria", "Terciária"),
        ("borda", "Borda"),
        ("sombra", "Sombra"),

        # Typography & interaction
        ("texto_principal", "Texto Principal"),
        ("texto_secundario", "Texto Secundário"),
        ("hover", "Hover"),
        ("foco", "Foco"),
        ("selecao", "Seleção"),
        ("highlight", "Destaque / Highlight"),

        # Buttons
        ("botao_salvar", "Botão Salvar"),
        ("botao_excluir", "Botão Excluir"),
        ("botao_novo", "Botão Novo"),
        ("botao_cancelar", "Botão Cancelar"),

        # Feedback
        ("sucesso", "Sucesso"),
        ("alerta", "Alerta"),
        ("erro", "Erro"),
        ("info", "Informação"),
    ]

    def __init__(self, app, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.app = app
        self.db = DatabaseTemaManager(app)

        # Carrega settings do banco
        self.settings = self.db.carregar_preferencias_usuario()
        tema_inicial = self.settings.get("theme", "Clássico Claro")

        # Paleta do tema atual
        self.current_paleta = paleta_segura(
            self.PADROES.get(tema_inicial, DEFAULT_TEMA)
        )

        # Tema selecionado na sidebar
        self.tema_selecionado = tk.StringVar(value=tema_inicial)

        # Dicionário para widgets de edição
        self.editor_widgets: Dict[str, Dict[str, Any]] = {}

        # Monta página
        self._montar_layout()
    # ============================================================
    #   LAYOUT PRINCIPAL (Sidebar + Editor + Preview)
    # ============================================================
    def _montar_layout(self):
        # ============================================================
        # 1 — CONTAINER PRINCIPAL (duas colunas)
        # ============================================================
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Sidebar (lista de temas)
        self.sidebar = ctk.CTkFrame(self, fg_color=self.current_paleta["primaria"])
        self.sidebar.grid(row=0, column=0, sticky="nswe", padx=(0, 1))

        # Editor + Preview (lado direito)
        self.area_principal = ctk.CTkFrame(self, fg_color=self.current_paleta["secundaria"])
        self.area_principal.grid(row=0, column=1, sticky="nswe")

        self.area_principal.grid_columnconfigure(0, weight=1)
        self.area_principal.grid_rowconfigure(1, weight=1)

        # Montar seções
        self._montar_sidebar()
        self._montar_editor()
        self._montar_preview()


    # ============================================================
    #   SIDEBAR — Lista de temas
    # ============================================================
    def _montar_sidebar(self):
        self.sidebar.grid_rowconfigure(1, weight=1)

        # Título
        titulo = ctk.CTkLabel(
            self.sidebar,
            text="Temas Disponíveis",
            text_color=self.current_paleta["texto_principal"],
            font=("Segoe UI", 18, "bold"),
        )
        titulo.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Lista scrollável
        container_lista = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        container_lista.grid(row=1, column=0, sticky="nswe", padx=10, pady=(0, 10))

        container_lista.grid_rowconfigure(0, weight=1)
        container_lista.grid_columnconfigure(0, weight=1)

        self.canvas_lista = tk.Canvas(
            container_lista,
            bg=self.current_paleta["primaria"],
            highlightthickness=0,
        )
        self.canvas_lista.grid(row=0, column=0, sticky="nswe")

        scrollbar = ctk.CTkScrollbar(
            container_lista,
            orientation="vertical",
            command=self.canvas_lista.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.canvas_lista.configure(yscrollcommand=scrollbar.set)

        self.frame_lista = ctk.CTkFrame(
            self.canvas_lista,
            fg_color=self.current_paleta["primaria"]
        )

        self.canvas_lista.create_window((0, 0), window=self.frame_lista, anchor="nw")

        self.frame_lista.bind(
            "<Configure>",
            lambda e: self.canvas_lista.configure(scrollregion=self.canvas_lista.bbox("all"))
        )

        # Botão Criar Tema
        self.btn_criar = ctk.CTkButton(
            self.sidebar,
            text="+ Criar Tema",
            fg_color=self.current_paleta["botao_novo"],
            hover_color=self._escurecer(self.current_paleta["botao_novo"], 0.12),
            text_color=cor_contraste(self.current_paleta["botao_novo"]),
            font=("Segoe UI", 14, "bold"),
            height=40,
            command=self._criar_tema_dialog,
        )
        self.btn_criar.grid(row=2, column=0, padx=20, pady=15, sticky="we")

        # Preencher a lista
        self._popular_lista_temas()


    # ============================================================
    #        MONTA A LISTA DE TEMAS (PADRÃO + PERSONALIZADOS)
    # ============================================================
    def _popular_lista_temas(self):
        for widget in self.frame_lista.winfo_children():
            widget.destroy()

        # Títulos da lista
        sec1 = ctk.CTkLabel(
            self.frame_lista,
            text="Temas Padrão",
            text_color=self.current_paleta["texto_secundario"],
            font=("Segoe UI", 14, "bold"),
        )
        sec1.pack(anchor="w", padx=16, pady=(10, 5))

        for nome in sorted(self.PADROES.keys()):
            self._criar_chip_tema(nome, padrao=True)

        sec2 = ctk.CTkLabel(
            self.frame_lista,
            text="Temas Personalizados",
            text_color=self.current_paleta["texto_secundario"],
            font=("Segoe UI", 14, "bold"),
        )
        sec2.pack(anchor="w", padx=16, pady=(20, 5))

        custom = self.db.listar_temas_personalizados()
        for nome in sorted(custom.keys()):
            self._criar_chip_tema(nome, padrao=False)


    # ============================================================
    #   CHIP DE TEMA (ITEM DA SIDEBAR) + ANIMAÇÕES SUAVES
    # ============================================================
    def _criar_chip_tema(self, nome: str, padrao: bool):
        paleta = self.PADROES.get(nome) if padrao else \
            self.db.listar_temas_personalizados().get(nome, {})

        cor_base = paleta_segura(paleta).get("primaria", "#DDDDDD") if paleta else "#CCCCCC"
        texto_cor = cor_contraste(cor_base)

        frame_chip = ctk.CTkFrame(
            self.frame_lista,
            fg_color=cor_base,
            corner_radius=8,
        )
        frame_chip.pack(fill="x", padx=10, pady=6)

        # Nome do tema
        lbl = ctk.CTkLabel(
            frame_chip,
            text=nome,
            font=("Segoe UI", 14, "bold"),
            text_color=texto_cor,
        )
        lbl.pack(side="left", padx=12, pady=8)

        # Indicador de selecionado
        indicador = ctk.CTkLabel(
            frame_chip,
            text="●" if self.tema_selecionado.get() == nome else "",
            text_color=self.current_paleta["highlight"],
            font=("Segoe UI", 16, "bold"),
        )
        indicador.pack(side="right", padx=12)

        # Eventos
        frame_chip.bind("<Button-1>", lambda e: self._carregar_tema(nome))
        lbl.bind("<Button-1>", lambda e: self._carregar_tema(nome))
        indicador.bind("<Button-1>", lambda e: self._carregar_tema(nome))

        # HOVER ANIMADO
        def entrar(_):
            animar_cor(frame_chip, cor_base, self.current_paleta["hover"])

        def sair(_):
            animar_cor(frame_chip, self.current_paleta["hover"], cor_base)

        frame_chip.bind("<Enter>", entrar)
        frame_chip.bind("<Leave>", sair)


    # ============================================================
    #   ÁREA DO EDITOR (20 seletores de cor, organizados)
    # ============================================================
    def _montar_editor(self):
        self.container_editor = ctk.CTkFrame(self.area_principal, fg_color="transparent")
        self.container_editor.grid(row=0, column=0, sticky="we", padx=20, pady=20)

        titulo = ctk.CTkLabel(
            self.container_editor,
            text="Editor de Cores",
            text_color=self.current_paleta["texto_principal"],
            font=("Segoe UI", 20, "bold"),
        )
        titulo.pack(anchor="w", pady=(0, 10))

        # Grid de 2 colunas
        self.frame_grid = ctk.CTkFrame(self.container_editor, fg_color="transparent")
        self.frame_grid.pack(fill="x", pady=10)

        self.frame_grid.grid_columnconfigure(0, weight=1)
        self.frame_grid.grid_columnconfigure(1, weight=1)

        # Adiciona todas as 20 linhas
        for i, (chave, label_texto) in enumerate(self.CAMPOS_COR):
            self._criar_linha_editor(i, chave, label_texto)

    # ============================================================
    #   CRIA UMA LINHA DO EDITOR DE TEMAS (seleção de cor)
    # ============================================================
    def _criar_linha_editor(self, index, chave, label_texto):
        linha = ctk.CTkFrame(self.frame_grid, fg_color="transparent")
        linha.grid(
            row=index,
            column=0 if index % 2 == 0 else 1,
            sticky="we",
            padx=6,
            pady=8,
        )

        # Nome do campo
        lbl = ctk.CTkLabel(
            linha,
            text=label_texto,
            text_color=self.current_paleta["texto_principal"],
            font=("Segoe UI", 14)
        )
        lbl.pack(anchor="w")

        # Caixa de cor (preview)
        cor_atual = self.current_paleta.get(chave, "#FFFFFF")

        caixa = ctk.CTkFrame(
            linha,
            width=46,
            height=28,
            corner_radius=6,
            fg_color=cor_atual,
        )
        caixa.pack(anchor="w", pady=6)

        # Indicador de hex
        lbl_hex = ctk.CTkLabel(
            linha,
            text=cor_atual,
            text_color=self.current_paleta["texto_secundario"],
            font=("Consolas", 13),
        )
        lbl_hex.pack(anchor="w", pady=(0, 6))

        # Animações de hover
        def entrar(_):
            animar_cor(caixa, self.current_paleta[chave], self.current_paleta["hover"])

        def sair(_):
            animar_cor(caixa, self.current_paleta["hover"], self.current_paleta[chave])

        caixa.bind("<Enter>", entrar)
        caixa.bind("<Leave>", sair)

        # Salvar widgets
        self.editor_widgets[chave] = {
            "linha": linha,
            "caixa": caixa,
            "hex": lbl_hex,
            "label": lbl,
        }

        # Eventos de clique
        caixa.bind("<Button-1>", lambda e, c=chave: self._abrir_colorpicker(c))
        lbl_hex.bind("<Button-1>", lambda e, c=chave: self._abrir_colorpicker(c))
        lbl.bind("<Double-Button-1>", lambda e, c=chave: self._abrir_colorpicker(c))

    # ============================================================
    #   ABRIR COLOR PICKER E ATUALIZAR A COR ESCOLHIDA
    # ============================================================
    def _abrir_colorpicker(self, chave):
        try:
            cor_inicial = self.current_paleta.get(chave, "#FFFFFF")
            cor, _ = colorchooser.askcolor(color=cor_inicial)
            if cor is None:
                return
            r, g, b = map(int, cor)
            escolhida = f"#{r:02X}{g:02X}{b:02X}"
        except:
            return

        # Salvando no dicionário principal
        self.current_paleta[chave] = escolhida

        # Atualizar UI do editor
        self._atualizar_editor(chave, escolhida)

        # Atualizar preview
        self._atualizar_preview(self.current_paleta)

    # ============================================================
    #   ATUALIZA UM ITEM DO EDITOR (cor + texto)
    # ============================================================
    def _atualizar_editor(self, chave, cor):
        w = self.editor_widgets.get(chave)
        if not w:
            return

        # Atualiza a caixa
        animar_cor(w["caixa"], w["caixa"].cget("fg_color"), cor)
        w["hex"].configure(text=cor)

    # ============================================================
    #   ESCURECER / CLAREAR COR (UTILITÁRIO)
    # ============================================================
    def _escurecer(self, hex_color, fator=0.15):
        try:
            c = hex_color.lstrip("#")
            r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

            r = int(r * (1 - fator))
            g = int(g * (1 - fator))
            b = int(b * (1 - fator))

            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))

            return f"#{r:02X}{g:02X}{b:02X}"
        except:
            return hex_color

    # ============================================================
    #   CLAREAR COR
    # ============================================================
    def _clarear(self, hex_color, fator=0.15):
        try:
            c = hex_color.lstrip("#")
            r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

            r = int(r + (255 - r) * fator)
            g = int(g + (255 - g) * fator)
            b = int(b + (255 - b) * fator)

            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))

            return f"#{r:02X}{g:02X}{b:02X}"
        except:
            return hex_color
    # ============================================================
    #   PREVIEW COMPLETO DO TEMA (mini dashboard profissional)
    # ============================================================
    def _montar_preview(self):
        self.preview_frame = ctk.CTkFrame(
            self.area_principal,
            fg_color="transparent"
        )
        self.preview_frame.grid(row=1, column=0, sticky="nswe", padx=20, pady=(0,20))

        titulo_preview = ctk.CTkLabel(
            self.preview_frame,
            text="Pré-visualização do Tema",
            text_color=self.current_paleta["texto_principal"],
            font=("Segoe UI", 20, "bold")
        )
        titulo_preview.pack(anchor="w", pady=(0, 10))

        # Container visual
        self.preview_container = ctk.CTkFrame(
            self.preview_frame,
            fg_color=self.current_paleta["fundo"],
            corner_radius=14,
        )
        self.preview_container.pack(fill="both", expand=True)

        # Construir conteúdo simulado
        self._montar_preview_conteudo()


    # ============================================================
    #   CONSTRÓI O PREVIEW: Mini Dashboard (cards, botões, título)
    # ============================================================
    def _montar_preview_conteudo(self):
        p = self.current_paleta

        for w in self.preview_container.winfo_children():
            w.destroy()

        # Título da seção do mock dashboard
        titulo = ctk.CTkLabel(
            self.preview_container,
            text="Dashboard Exemplo",
            text_color=p["texto_principal"],
            font=("Segoe UI", 22, "bold")
        )
        titulo.pack(anchor="w", padx=20, pady=(20, 10))

        # Subtítulo
        subtitulo = ctk.CTkLabel(
            self.preview_container,
            text="Esta é uma pré-visualização ao vivo das cores do tema.",
            text_color=p["texto_secundario"],
            font=("Segoe UI", 14)
        )
        subtitulo.pack(anchor="w", padx=20, pady=(0, 20))

        # Linha de Botões
        linha_botoes = ctk.CTkFrame(
            self.preview_container, fg_color="transparent"
        )
        linha_botoes.pack(anchor="w", padx=20, pady=10)

        btn_salvar = ctk.CTkButton(
            linha_botoes,
            text="Salvar",
            fg_color=p["botao_salvar"],
            hover_color=self._escurecer(p["botao_salvar"]),
            text_color=cor_contraste(p["botao_salvar"]),
            font=("Segoe UI", 14, "bold"),
            width=120,
            height=36
        )
        btn_salvar.pack(side="left", padx=6)

        btn_excluir = ctk.CTkButton(
            linha_botoes,
            text="Excluir",
            fg_color=p["botao_excluir"],
            hover_color=self._escurecer(p["botao_excluir"]),
            text_color=cor_contraste(p["botao_excluir"]),
            font=("Segoe UI", 14, "bold"),
            width=120,
            height=36
        )
        btn_excluir.pack(side="left", padx=6)

        btn_info = ctk.CTkButton(
            linha_botoes,
            text="Informações",
            fg_color=p["info"],
            hover_color=self._escurecer(p["info"]),
            text_color=cor_contraste(p["info"]),
            font=("Segoe UI", 14, "bold"),
            width=150,
            height=36
        )
        btn_info.pack(side="left", padx=6)

        # Container dos cards
        cards_linha = ctk.CTkFrame(
            self.preview_container,
            fg_color="transparent"
        )
        cards_linha.pack(fill="x", padx=20, pady=(20, 20))

        # Três cartões (tipo dashboard)
        for i in range(3):
            card = ctk.CTkFrame(
                cards_linha,
                width=200,
                height=140,
                fg_color=p["secundaria"],
                corner_radius=12,
            )
            card.pack(side="left", padx=10)

            # Sombra simulada (com borda embaixo)
            sombra = ctk.CTkFrame(
                card,
                height=6,
                fg_color=p["sombra"],
                corner_radius=12,
            )
            sombra.pack(fill="x", side="bottom")

            lbl = ctk.CTkLabel(
                card,
                text=f"Card {i+1}",
                text_color=p["texto_principal"],
                font=("Segoe UI", 16, "bold")
            )
            lbl.pack(anchor="w", padx=12, pady=(12, 0))

            lbl2 = ctk.CTkLabel(
                card,
                text="Texto de exemplo",
                text_color=p["texto_secundario"],
                font=("Segoe UI", 13),
            )
            lbl2.pack(anchor="w", padx=12, pady=(6, 0))

        # Tabela simulada
        table_container = ctk.CTkFrame(
            self.preview_container,
            fg_color=p["terciaria"],
            corner_radius=10
        )
        table_container.pack(fill="x", padx=20, pady=20)

        table_title = ctk.CTkLabel(
            table_container,
            text="Tabela de Exemplo",
            text_color=p["texto_principal"],
            font=("Segoe UI", 16, "bold")
        )
        table_title.pack(anchor="w", padx=12, pady=(10, 6))

        linhas = ["Linha A", "Linha B", "Linha C"]
        for linha in linhas:
            row = ctk.CTkFrame(table_container, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)

            lbl_nome = ctk.CTkLabel(
                row,
                text=linha,
                text_color=p["texto_principal"],
                font=("Segoe UI", 13),
            )
            lbl_nome.pack(side="left")

            lbl_status = ctk.CTkLabel(
                row,
                text="Ativo",
                text_color=p["sucesso"],
                font=("Segoe UI", 13, "bold"),
            )
            lbl_status.pack(side="right", padx=10)


    # ============================================================
    #   REAPLICA CORES TOTALMENTE NO PREVIEW
    # ============================================================
    def _atualizar_preview(self, paleta: Dict[str, str]):
        self.current_paleta = paleta_segura(paleta)
        self.preview_container.configure(fg_color=self.current_paleta["fundo"])
        self._montar_preview_conteudo()
    # ============================================================
    #   CARREGAR UM TEMA DA SIDEBAR
    # ============================================================
    def _carregar_tema(self, nome: str):
        # Verifica se é padrão
        if nome in self.PADROES:
            nova = paleta_segura(self.PADROES[nome])
        else:
            tema_custom = self.db.listar_temas_personalizados()
            nova = paleta_segura(tema_custom.get(nome, DEFAULT_TEMA))

        self.current_paleta = nova
        self.tema_selecionado.set(nome)

        # Atualizar editor e preview
        self._atualizar_editor_completo()
        self._atualizar_preview(nova)

        # Marcar tema ativo na sidebar
        self._marcar_tema_ativo()

        print(f"🎨 Tema carregado: {nome}")


    # ============================================================
    #   ATUALIZA TODOS OS CAMPOS DO EDITOR APÓS TROCAR TEMA
    # ============================================================
    def _atualizar_editor_completo(self):
        for chave, _ in self.CAMPOS_COR:
            cor = self.current_paleta.get(chave, "#FFFFFF")
            if chave in self.editor_widgets:
                w = self.editor_widgets[chave]
                w["hex"].configure(text=cor)
                w["caixa"].configure(fg_color=cor)


    # ============================================================
    #   MARCAR QUAL TEMA ESTÁ ATIVO NA SIDEBAR
    # ============================================================
    def _marcar_tema_ativo(self):
        ativo = self.tema_selecionado.get()

        # Recriar a lista de chips para atualizar indicador
        self._popular_lista_temas()

        # Animação opcional de destaque (microtransição)
        for widget in self.frame_lista.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for lbl in widget.winfo_children():
                    if isinstance(lbl, ctk.CTkLabel) and lbl.cget("text") == ativo:
                        animar_cor(widget, self.current_paleta["primaria"], self.current_paleta["selecao"])
                        widget.after(200, lambda w=widget: animar_cor(
                            w,
                            self.current_paleta["selecao"],
                            self.current_paleta["primaria"]
                        ))


    # ============================================================
    #   APLICAR TEMA A TODO O SISTEMA (MENU PRINCIPAL, PÁGINAS, ETC.)
    # ============================================================
    def _aplicar_tema_global(self):
        if not hasattr(self.app, "aplicar_tema_completo"):
            print("⚠️ app.aplicar_tema_completo não existe — nada a aplicar agora.")
            return

        nome_tema = self.tema_selecionado.get()
        print(f"💡 Aplicando tema global: {nome_tema}")

        try:
            self.app.aplicar_tema_completo(self.current_paleta)
        except Exception as e:
            print(f"❌ Erro ao aplicar tema global: {e}")


    # ============================================================
    #   BOTÃO PARA SALVAR TEMA PERSONALIZADO
    # ============================================================
    def _salvar_tema(self):
        nome = self.tema_selecionado.get()

        # Se for tema padrão, cria uma cópia personalizada
        if nome in self.PADROES:
            nome = f"{nome} (Personalizado)"

        # Salvar no banco
        ok = self.db.salvar_tema_personalizado(nome, self.current_paleta)
        if ok:
            print(f"💾 Tema '{nome}' salvo com sucesso!")

        # Atualizar sidebar
        self._popular_lista_temas()

        # Selecionar o recém-salvo
        self.tema_selecionado.set(nome)
        self._marcar_tema_ativo()

        # Atualizar preferências
        self.db.registrar_tema_atual(
            nome,
            self.current_paleta,
            usar_personalizado=True,
            settings=self.settings
        )


    # ============================================================
    #   CRIAR UM NOVO TEMA VIA DIÁLOGO
    # ============================================================
    def _criar_tema_dialog(self):
        popup = ctk.CTkInputDialog(
            title="Criar Tema",
            text="Nome do novo tema:"
        )
        nome = popup.get_input()

        if not nome:
            return

        # Criar uma cópia do tema atual
        nova_paleta = dict(self.current_paleta)

        ok = self.db.salvar_tema_personalizado(nome, nova_paleta)
        if ok:
            print(f"✨ Novo tema criado: {nome}")

        # Recarregar lista
        self._popular_lista_temas()

        # Selecionar o novo tema
        self.tema_selecionado.set(nome)
        self.current_paleta = nova_paleta
        self._atualizar_editor_completo()
        self._marcar_tema_ativo()

        # Registrar como tema atual
        self.db.registrar_tema_atual(
            nome,
            nova_paleta,
            usar_personalizado=True,
            settings=self.settings
        )


    # ============================================================
    #   EXCLUIR TEMA PERSONALIZADO
    #   (Somente se estiver na tabela usuario_temas_personalizados)
    # ============================================================
    def _excluir_tema(self):
        nome = self.tema_selecionado.get()

        if nome in self.PADROES:
            print("⚠️ Temas padrão não podem ser excluídos.")
            return

        temas = self.db.listar_temas_personalizados()

        if nome not in temas:
            print("⚠️ Tema não encontrado na lista personalizada.")
            return

        # Confirmar
        resp = ctk.CTkMessagebox(
            title="Excluir Tema",
            message=f"Deseja realmente excluir o tema '{nome}'?",
            icon="warning",
            option_1="Cancelar",
            option_2="Excluir"
        ).get()

        if resp != "Excluir":
            return

        # Remover do banco
        conn = self.db.get_connection()
        schema = "opera"
        try:
            with conn.cursor() as c:
                c.execute(
                    f"DELETE FROM {schema}.usuario_temas_personalizados "
                    f"WHERE usuario_id = %s AND nome_tema = %s",
                    (self.db.user_id, nome)
                )
                conn.commit()
                print(f"🗑️ Tema '{nome}' excluído.")
        except Exception as e:
            print("❌ Erro ao excluir tema:", e)
        finally:
            try:
                conn.close()
            except:
                pass

        # Recarregar lista
        self._popular_lista_temas()

        # Voltar ao padrão
        self.tema_selecionado.set("Clássico Claro")
        self.current_paleta = paleta_segura(self.PADROES["Clássico Claro"])
        self._atualizar_editor_completo()
        self._marcar_tema_ativo()
        self._atualizar_preview(self.current_paleta)
    # ============================================================
    #   BARRA INFERIOR — BOTÕES PRINCIPAIS (SALVAR / APLICAR / EXCLUIR)
    # ============================================================
    def _montar_botoes_finais(self):
        barra = ctk.CTkFrame(
            self.area_principal,
            fg_color="transparent"
        )
        barra.grid(row=2, column=0, sticky="we", padx=20, pady=(0, 20))

        barra.grid_columnconfigure(0, weight=1)
        barra.grid_columnconfigure(1, weight=1)
        barra.grid_columnconfigure(2, weight=1)

        # -------------------------- BOTÃO SALVAR
        btn_salvar = ctk.CTkButton(
            barra,
            text="💾 Salvar Tema",
            fg_color=self.current_paleta["botao_salvar"],
            hover_color=self._escurecer(self.current_paleta["botao_salvar"]),
            text_color=cor_contraste(self.current_paleta["botao_salvar"]),
            font=("Segoe UI", 15, "bold"),
            height=42,
            command=self._salvar_tema
        )
        btn_salvar.grid(row=0, column=0, padx=8, sticky="we")

        # -------------------------- APLICAR NO SISTEMA
        btn_aplicar = ctk.CTkButton(
            barra,
            text="✨ Aplicar Tema no Sistema",
            fg_color=self.current_paleta["foco"],
            hover_color=self._escurecer(self.current_paleta["foco"]),
            text_color=cor_contraste(self.current_paleta["foco"]),
            font=("Segoe UI", 15, "bold"),
            height=42,
            command=self._btn_aplicar_click
        )
        btn_aplicar.grid(row=0, column=1, padx=8, sticky="we")

        # -------------------------- EXCLUIR
        btn_excluir = ctk.CTkButton(
            barra,
            text="🗑️ Excluir Tema",
            fg_color=self.current_paleta["botao_excluir"],
            hover_color=self._escurecer(self.current_paleta["botao_excluir"]),
            text_color=cor_contraste(self.current_paleta["botao_excluir"]),
            font=("Segoe UI", 15, "bold"),
            height=42,
            command=self._excluir_tema
        )
        btn_excluir.grid(row=0, column=2, padx=8, sticky="we")


    # ============================================================
    #   BOTÃO "APLICAR TEMA NO SISTEMA"
    # ============================================================
    def _btn_aplicar_click(self):
        nome = self.tema_selecionado.get()

        # Atualiza preferências do usuário
        self.db.registrar_tema_atual(
            nome,
            self.current_paleta,
            usar_personalizado=(nome not in self.PADROES),
            settings=self.settings
        )

        # Aplica visualmente
        self._aplicar_tema_global()

        # Feedback no console
        print(f"✨ Tema '{nome}' aplicado ao sistema.")


    # ============================================================
    #   INICIAR EXIBIÇÃO (APÓS MONTAR TODA A UI)
    # ============================================================
    def _pos_carregamento(self):
        """
        Executado após a página carregar.
        Atualiza botões e preview.
        """
        self._marcar_tema_ativo()
        self._atualizar_editor_completo()
        self._atualizar_preview(self.current_paleta)


    # ============================================================
    #   FINAL DO __init__ — CHAMAR BARRA E INICIAR
    # ============================================================
    def _montar_layout(self):
        super()._montar_layout()

        # Criar barra inferior
        self._montar_botoes_finais()

        # Finalizar carregamento
        self.after(100, self._pos_carregamento)


# ============================================================
#   EXECUÇÃO DIRETA (TESTE INDEPENDENTE)
# ============================================================
if __name__ == "__main__":
    app = ctk.CTk()
    app.geometry("1400x830")
    app.title("Editor de Temas — Sistema OPERA")

    try:
        from tema_database import DatabaseTemaManager
    except:
        print("⚠️ Sem acesso ao banco, rodando em modo demonstração.")

    page = Tema2Page(app)
    page.pack(fill="both", expand=True)

    app.mainloop()
