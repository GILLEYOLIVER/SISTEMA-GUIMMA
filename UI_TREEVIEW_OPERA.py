"""
UI_TREEVIEW_OPERA.py
====================

Módulo para padronizar o CABEÇALHO do ttk.Treeview no estilo que você aprovou:
- Cabeçalho cinza claro
- Hover (active) fica mais escuro
- Pressed (clicado) fica ainda um pouco mais escuro
- Mantém o corpo (linhas) como está nas páginas (não mexe em zebra/seleção)

✅ Como usar no sistema inteiro (recomendado):
1) Em um ponto único que roda no início do app (ex.: MENU_PRINCIPAL.py ou main),
   chame:

   from UI_TREEVIEW_OPERA import instalar_cabecalho_treeview
   instalar_cabecalho_treeview()

Isso já aplica no estilo padrão "Treeview.Heading" e também em "Custom.Treeview.Heading".
Se alguma página usar outro style (ex.: "Minha.Treeview"), você pode registrar também:

   instalar_cabecalho_treeview(extra_tree_styles=["Minha.Treeview"])

2) (Opcional) Se você quiser garantir que uma Treeview específica use um style padrão:
   from UI_TREEVIEW_OPERA import aplicar_em_treeview
   aplicar_em_treeview(self.tree, tree_style="Custom.Treeview")

Observação:
- Em Windows, o tema "clam" costuma respeitar melhor as cores do Heading.
- Este módulo NÃO altera o corpo da Treeview por padrão (apenas o cabeçalho + hover).
"""

from __future__ import annotations

from typing import Iterable, Optional, Tuple
from tkinter import ttk


# ---------- Config padrão do cabeçalho (igual ao seu print) ----------
DEFAULT_HEADING_BG = "#eeeeee"
DEFAULT_HEADING_FG = "#000000"
DEFAULT_HOVER_BG   = "#cfcfcf"
DEFAULT_PRESSED_BG = "#bdbdbd"
DEFAULT_FONT       = ("Arial", 10, "bold")
DEFAULT_PADDING    = (8, 6)


def _usar_tema_clam(style: ttk.Style) -> None:
    """Tenta ativar o tema 'clam' (melhor para heading no Windows)."""
    try:
        style.theme_use("clam")
    except Exception:
        # fallback silencioso
        pass


def configurar_cabecalho_para_style(
    style: ttk.Style,
    tree_style: str,
    *,
    heading_bg: str = DEFAULT_HEADING_BG,
    heading_fg: str = DEFAULT_HEADING_FG,
    hover_bg: str = DEFAULT_HOVER_BG,
    pressed_bg: str = DEFAULT_PRESSED_BG,
    font: Tuple[str, int, str] = DEFAULT_FONT,
    padding: Tuple[int, int] = DEFAULT_PADDING,
) -> None:
    """
    Configura o cabeçalho (Heading) para um style de Treeview específico.

    Ex.: tree_style="Treeview" -> aplica em "Treeview.Heading"
         tree_style="Custom.Treeview" -> aplica em "Custom.Treeview.Heading"
    """
    heading_style = f"{tree_style}.Heading"

    style.configure(
        heading_style,
        background=heading_bg,
        foreground=heading_fg,
        font=font,
        relief="flat",
        borderwidth=0,
        padding=padding,
    )

    # Mantém hover/pressed igual ao seu print
    style.map(
        heading_style,
        background=[("active", hover_bg), ("pressed", pressed_bg)],
        foreground=[("active", heading_fg), ("pressed", heading_fg)],
        relief=[("pressed", "flat"), ("active", "flat")],
    )


def instalar_cabecalho_treeview(
    *,
    extra_tree_styles: Optional[Iterable[str]] = None,
    heading_bg: str = DEFAULT_HEADING_BG,
    heading_fg: str = DEFAULT_HEADING_FG,
    hover_bg: str = DEFAULT_HOVER_BG,
    pressed_bg: str = DEFAULT_PRESSED_BG,
    font: Tuple[str, int, str] = DEFAULT_FONT,
    padding: Tuple[int, int] = DEFAULT_PADDING,
    usar_clam: bool = True,
) -> ttk.Style:
    """
    Instala o cabeçalho padrão globalmente.

    - Aplica em: "Treeview" e "Custom.Treeview" por padrão
    - Você pode passar outros styles usados em páginas específicas via extra_tree_styles.

    Retorna o ttk.Style usado (para reusar se quiser).
    """
    style = ttk.Style()
    if usar_clam:
        _usar_tema_clam(style)

    tree_styles = ["Treeview", "Custom.Treeview"]
    if extra_tree_styles:
        for s in extra_tree_styles:
            if s and s not in tree_styles:
                tree_styles.append(s)

    for ts in tree_styles:
        configurar_cabecalho_para_style(
            style,
            ts,
            heading_bg=heading_bg,
            heading_fg=heading_fg,
            hover_bg=hover_bg,
            pressed_bg=pressed_bg,
            font=font,
            padding=padding,
        )

    return style


def aplicar_em_treeview(
    tree: ttk.Treeview,
    *,
    tree_style: str = "Custom.Treeview",
    garantir_style: bool = True,
    **kwargs
) -> None:
    """
    Aplica o cabeçalho no style informado e (opcional) garante que a tree use esse style.

    kwargs é repassado para instalar_cabecalho_treeview/configurar_cabecalho_para_style:
    - heading_bg, heading_fg, hover_bg, pressed_bg, font, padding, usar_clam
    """
    style = instalar_cabecalho_treeview(extra_tree_styles=[tree_style], **kwargs)
    # Reforça a configuração especificamente para o tree_style (caso o ttk ignore um dos passos)
    configurar_cabecalho_para_style(style, tree_style, **{k: v for k, v in kwargs.items() if k != "usar_clam"})

    if garantir_style:
        try:
            tree.configure(style=tree_style)
        except Exception:
            # Se falhar por alguma razão, não trava a aplicação
            pass


def reaplicar_em_todas_as_treeviews(
    root,
    *,
    tree_style: str = "Custom.Treeview",
    **kwargs
) -> None:
    """
    Varre todos os widgets abaixo de `root` e reaplica o estilo de cabeçalho
    nas Treeviews encontradas.

    Útil após troca de tema/refresh de UI.
    """
    # instala uma vez
    instalar_cabecalho_treeview(extra_tree_styles=[tree_style], **kwargs)

    def walk(widget):
        for child in widget.winfo_children():
            # ttk.Treeview
            if isinstance(child, ttk.Treeview):
                try:
                    child.configure(style=tree_style)
                except Exception:
                    pass
            walk(child)

    try:
        walk(root)
    except Exception:
        pass
