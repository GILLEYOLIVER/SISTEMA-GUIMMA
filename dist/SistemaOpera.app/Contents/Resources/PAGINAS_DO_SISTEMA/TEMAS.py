from __future__ import annotations


def corrigir_labels_pagina_temas(widget):
    """
    CORREÇÃO CRÍTICA: Remove fundos, bordas e contornos dos CTkLabels
    que estão dentro de botões na página de Temas.
    Isso elimina o quadrado branco ao redor do texto.
    """
    import customtkinter as ctk

    try:
        # CORREÇÃO 1: Labels dentro de botões (MAIOR PROBLEMA)
        if isinstance(widget, ctk.CTkButton):
            # Procura por labels dentro do botão
            for child in widget.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    # Remove COMPLETAMENTE qualquer aparência visual
                    try:
                        child.configure(
                            fg_color="transparent",  # FUNDO TRANSPARENTE
                            border_width=0,  # SEM BORDA
                            corner_radius=0,  # SEM CANTOS ARREDONDADOS
                            bg_color="transparent"  # COR DE FUNDO TRANSPARENTE
                        )
                    except Exception:
                        pass

                    # Remove highlight do Tkinter (nivel mais baixo)
                    try:
                        child.configure(highlightthickness=0)
                    except Exception:
                        pass

            # Também remove bordas do próprio botão se existirem
            try:
                widget.configure(border_width=0)
            except Exception:
                pass

        # CORREÇÃO 2: Labels soltos na página
        elif isinstance(widget, ctk.CTkLabel):
            try:
                # Verifica se o label tem cor de fundo visível
                fg_color = widget.cget("fg_color")
                if fg_color and fg_color not in ["transparent", "None", "", None]:
                    widget.configure(
                        fg_color="transparent",
                        border_width=0,
                        corner_radius=0
                    )
                else:
                    # Já é transparente, só remove bordas
                    widget.configure(border_width=0, corner_radius=0)
            except Exception:
                # Fallback: tenta tornar transparente de qualquer forma
                try:
                    widget.configure(fg_color="transparent", border_width=0, corner_radius=0)
                except Exception:
                    pass

        # CORREÇÃO 3: Remove bordas de outros widgets que podem causar contorno
        elif isinstance(widget, (ctk.CTkEntry, ctk.CTkOptionMenu, ctk.CTkComboBox)):
            try:
                widget.configure(border_width=0, highlightthickness=0)
            except Exception:
                pass

        # APLICA RECURSIVAMENTE EM TODOS OS FILHOS
        for child in widget.winfo_children():
            corrigir_labels_pagina_temas(child)

    except Exception as e:
        # Ignora erros, não quebra a aplicação
        pass
import copy
import importlib
import importlib.util
import json
import math
import re
import tkinter as tk
from tkinter import Canvas
from tkinter import ttk
import colorsys
import customtkinter as ctk
from PIL import Image, ImageTk
import tkinter.messagebox as messagebox

_image_grab_spec = importlib.util.find_spec("PIL.ImageGrab")
ImageGrab = importlib.import_module("PIL.ImageGrab") if _image_grab_spec else None
# =================== UTILITÁRIOS DE CORREÇÃO GLOBAL ===================



def corrigir_bordas_labels(widget):
    """
    Remove qualquer borda ou contorno visual que aparece em labels após trocar o tema.
    Aplica recursivamente em todos os filhos.
    """
    try:
        import customtkinter as ctk
        # Remove borda apenas de labels
        if isinstance(widget, ctk.CTkLabel):
            app = widget.winfo_toplevel(); cor_fundo = getattr(app, "cor_fundo", "transparent"); widget.configure(border_width=0, corner_radius=0, fg_color=cor_fundo)

        # Aplicar aos filhos
        for child in widget.winfo_children():
            corrigir_bordas_labels(child)

    except Exception as e:
        try:
            nome = widget.winfo_name()
            classe = widget.__class__.__name__
        except Exception:
            nome = "<desconhecido>"
            classe = widget.__class__.__name__ if hasattr(widget, "__class__") else "<sem classe>"
        print(f"[ERRO corrigir_bordas_labels] {classe}('{nome}') → {e}")

def corrigir_labels_transparentes(widget):
    """
    Garante que TODOS os CTkLabel fiquem com fg_color="transparent",
    corrigindo o que o ThemeManager sobrescreveu no MENU.
    """
    import customtkinter as ctk

    try:
        if isinstance(widget, ctk.CTkLabel):
            app = widget.winfo_toplevel(); cor_fundo = getattr(app, "cor_fundo", "transparent"); widget.configure(fg_color=cor_fundo, border_width=0, corner_radius=0)

        for child in widget.winfo_children():
            corrigir_labels_transparentes(child)

    except Exception:
        pass


# =================== CONSTANTES E CONFIGURAÇÕES ===================

# Importa o gerenciador de preferências
try:
    from settings_manager import save_settings, load_settings
except ImportError:
    def save_settings(settings):
        print("⚠️ settings_manager não encontrado, preferências não serão salvas")
        return False


    def load_settings():
        return {"theme": "Noite Urbana", "custom_themes": {}, "excluded_default_themes": []}

# Import do CTkMessagebox (se disponível)
try:
    from CTkMessagebox import CTkMessagebox

    MESSAGEBOX_AVAILABLE = True
except ImportError:
    MESSAGEBOX_AVAILABLE = False
    print("⚠️ CTkMessagebox não disponível, usando tkinter.messagebox")


# =================== CLASSES UTILITÁRIAS ===================

class BotaoPadronizado:
    """Classe para criação de botões com cores padronizadas"""

    CORES_BOTOES_PADRAO = {
        "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
        "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
        "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
        "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
        "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
        "botao_voltar": "#6B7280", "botao_avancar": "#10B981", "botao_adiantamento": "#10B981",
        "botao_comprovante": "#8B5CF6", "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
        "botao_export_pdf": "#F59E0B"
    }

    @staticmethod
    def criar_botao(master, texto=None, tipo="padrao", **kwargs):
        """
        Cria um CTkButton com padrão de cores.

        Compatível com:
            BotaoPadronizado.criar_botao(frame, "Salvar", tipo="salvar")
        e também com:
            BotaoPadronizado.criar_botao(frame, text="Salvar", tipo="salvar")
        """
        # Permitir usar text= em vez de texto=
        if texto is None and "text" in kwargs:
            texto = kwargs.pop("text")

        if texto is None:
            texto = ""

        config_padrao = {
            "height": 32,
            "font": ("Arial", 12),
            "corner_radius": 8,
            "border_width": 0
        }

        try:
            app = master.winfo_toplevel()
            cores = BotaoPadronizado._obter_cores_tema(app)
        except Exception:
            cores = BotaoPadronizado._obter_cores_fallback()

        config_tipo = {
            "padrao": {
                "fg_color": cores["secundaria"],
                "hover_color": cores["hover"],
                "text_color": cores["texto"],
                "border_color": cores["borda"]
            }
        }

        # Adiciona configurações específicas para cada tipo de botão
        for tipo_btn, cor in BotaoPadronizado.CORES_BOTOES_PADRAO.items():
            config_tipo[tipo_btn.replace("botao_", "")] = {
                "fg_color": cores.get(tipo_btn, cor),
                "hover_color": BotaoPadronizado._ajustar_cor(cores.get(tipo_btn, cor)),
                "text_color": BotaoPadronizado._get_contraste_texto(cores.get(tipo_btn, cor)),
                "border_color": BotaoPadronizado._ajustar_cor(cores.get(tipo_btn, cor), 0.7)
            }

        tipo_config = config_tipo.get(tipo, config_tipo["padrao"])
        config_final = {**config_padrao, **tipo_config, **kwargs}

        return ctk.CTkButton(master, text=texto, **config_final)

    @staticmethod
    def _obter_cores_tema(app):
        cores = {}
        atributos_cores = [
                              "primaria", "secundaria", "terciaria", "fundo", "texto",
                              "destaque", "sucesso", "alerta", "borda", "hover", "selecao"
                          ] + list(BotaoPadronizado.CORES_BOTOES_PADRAO.keys())

        for attr in atributos_cores:
            try:
                valor = getattr(app, f'cor_{attr}', None)
                if valor:
                    cores[attr] = valor
            except Exception:
                continue

        return cores

    @staticmethod
    def _obter_cores_fallback():
        return {
            "secundaria": "#2C2C2C",
            "hover": "#3A3A3A",
            "texto": "#FFFFFF",
            "borda": "#333333",
            **BotaoPadronizado.CORES_BOTOES_PADRAO
        }

    @staticmethod
    def _ajustar_cor(cor_base, fator=0.8):
        try:
            if not cor_base or not isinstance(cor_base, str):
                return cor_base

            hex_color = cor_base.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

            r = int(r * fator)
            g = int(g * fator)
            b = int(b * fator)

            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))

            return f"#{r:02x}{g:02x}{b:02x}".upper()
        except Exception:
            return cor_base

    @staticmethod
    def _get_contraste_texto(cor_fundo):
        try:
            if not cor_fundo or not isinstance(cor_fundo, str):
                return "#000000"

            hex_color = cor_fundo.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#000000" if luminance > 0.5 else "#FFFFFF"
        except Exception:
            return "#000000"


# =================== SELETOR DE CORES ===================

class ColorPickerWidget(ctk.CTkFrame):
    def __init__(self, master, initial_color="#FFFFFF", callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.callback = callback
        self.current_color = initial_color

        self.basic_colors = [
            ["#000000", "#1A1A1A", "#333333", "#4D4D4D", "#666666", "#808080", "#999999", "#B3B3B3", "#CCCCCC",
             "#E6E6E6", "#FFFFFF"],
            ["#8B0000", "#B22222", "#DC143C", "#FF0000", "#FF6347", "#FF7F7F", "#FFA07A", "#FFB6C1", "#FFC0CB",
             "#FFE4E1"],
            ["#FF4500", "#FF6347", "#FF8C00", "#FFA500", "#FFD700", "#FFFF00", "#FFFFE0", "#FFFACD", "#FFF8DC",
             "#FFEFD5"],
            ["#006400", "#008000", "#228B22", "#32CD32", "#00FF00", "#7FFF00", "#90EE90", "#98FB98", "#ADFF2F",
             "#F0FFF0"],
            ["#00008B", "#0000CD", "#0000FF", "#1E90FF", "#4169E1", "#6495ED", "#87CEEB", "#ADD8E6", "#B0E0E6",
             "#E0FFFF"],
            ["#4B0082", "#483D8B", "#6A5ACD", "#7B68EE", "#8A2BE2", "#9370DB", "#BA55D3", "#DA70D6", "#DDA0DD",
             "#E6E6FA"],
        ]

        self._build_ui()

    def _build_ui(self):
        preview_frame = ctk.CTkFrame(self, fg_color="transparent")
        preview_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(preview_frame, text="Cor Selecionada:", font=("Arial", 11, "bold")).pack(side="left", padx=5)

        self.preview_btn = ctk.CTkButton(preview_frame, text=self.current_color, fg_color=self.current_color,
                                         hover_color=self.current_color,
                                         text_color=self._get_contrast_color(self.current_color),
                                         font=("Arial", 10, "bold"), height=30, width=120,
                                         command=self._open_advanced_picker)
        self.preview_btn.pack(side="left", padx=5)

        palette_label = ctk.CTkLabel(self, text="Paleta de Cores:", font=("Arial", 11, "bold"))
        palette_label.pack(anchor="w", padx=5, pady=(10, 5))

        canvas_height = len(self.basic_colors) * 28
        canvas_width = 11 * 28

        self.canvas = Canvas(self, width=canvas_width, height=canvas_height, bg="#1E1E1E", highlightthickness=0)
        self.canvas.pack(padx=5, pady=5)

        self.color_rects = {}
        for row_idx, color_row in enumerate(self.basic_colors):
            for col_idx, color in enumerate(color_row):
                x1 = col_idx * 28 + 2
                y1 = row_idx * 28 + 2
                x2 = x1 + 24
                y2 = y1 + 24

                rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#666666", width=1)
                self.color_rects[rect_id] = color

                self.canvas.tag_bind(rect_id, "<Button-1>", lambda e, c=color: self._select_color(c))
                self.canvas.tag_bind(rect_id, "<Enter>",
                                     lambda e, rid=rect_id: self.canvas.itemconfig(rid, outline="#FFFFFF", width=2))
                self.canvas.tag_bind(rect_id, "<Leave>",
                                     lambda e, rid=rect_id: self.canvas.itemconfig(rid, outline="#666666", width=1))

        ctk.CTkButton(self, text="🎨 Seletor Avançado", font=("Arial", 11), height=30,
                      command=self._open_advanced_picker).pack(pady=10, padx=5)

    def _select_color(self, color):
        self.current_color = color
        self.preview_btn.configure(fg_color=color, hover_color=color, text=color,
                                   text_color=self._get_contrast_color(color))
        if self.callback:
            self.callback(color)

    def _open_advanced_picker(self):
        if hasattr(self, "_advanced_win") and self._advanced_win.winfo_exists():
            self._advanced_win.focus()
            return

        def close_picker():
            if hasattr(self, "_advanced_win") and self._advanced_win.winfo_exists():
                self._advanced_win.destroy()

        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            if len(hex_color) != 6 or not re.fullmatch(r"[0-9A-Fa-f]{6}", hex_color):
                return None
            return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        def rgb_to_hex(rgb_tuple):
            return "#{:02X}{:02X}{:02X}".format(*rgb_tuple)

        def hsv_to_hex(h, s, v):
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return rgb_to_hex((int(r * 255), int(g * 255), int(b * 255)))

        def build_wheel_image(size, radius, oversample=2):
            base_size = int(size * oversample)
            base_radius = radius * oversample
            image = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
            center = base_size / 2
            for x in range(base_size):
                for y in range(base_size):
                    dx = x - center + 0.5
                    dy = y - center + 0.5
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist <= base_radius:
                        hue = (math.atan2(-dy, dx) % (2 * math.pi)) / (2 * math.pi)
                        sat = min(1.0, dist / base_radius)
                        r, g, b = colorsys.hsv_to_rgb(hue, sat, 1.0)
                        image.putpixel((x, y), (int(r * 255), int(g * 255), int(b * 255), 255))
            if oversample > 1:
                image = image.resize((size, size), resample=Image.LANCZOS)
            return image

        def grab_screen_hex(x, y):
            if ImageGrab is None:
                return None
            try:
                pixel = ImageGrab.grab(bbox=(x, y, x + 1, y + 1)).getpixel((0, 0))
                return rgb_to_hex(pixel)
            except Exception as e:
                print(f"⚠️ Não foi possível capturar cor da tela: {e}")
                return None

        def start_eyedropper():
            if ImageGrab is None:
                messagebox.showwarning(
                    "Conta-gotas indisponível",
                    "O recurso de captura de cor não está disponível neste ambiente.",
                )
                return
            overlay = tk.Toplevel(self._advanced_win)
            overlay.overrideredirect(True)
            overlay.attributes("-alpha", 0.02)
            overlay.attributes("-topmost", True)
            overlay.configure(cursor="crosshair", bg="black")
            overlay.geometry(f"{overlay.winfo_screenwidth()}x{overlay.winfo_screenheight()}+0+0")
            overlay.focus_force()

            lens_size = 120
            lens_padding = 16
            lens_canvas = tk.Canvas(overlay, width=lens_size + 2 * lens_padding,
                                   height=lens_size + 36, bg="#121212", highlightthickness=0)
            lens_canvas.configure(cursor="circle")
            lens_photo = {"image": None}

            def finish(event=None):
                try:
                    if overlay.winfo_exists():
                        overlay.destroy()
                finally:
                    self._advanced_win.deiconify()
                    self._advanced_win.lift()
                    self._advanced_win.focus_force()

            def update_lens(event):
                try:
                    grab_box = (event.x_root - 12, event.y_root - 12, event.x_root + 13, event.y_root + 13)
                    zoom = ImageGrab.grab(bbox=grab_box).resize((lens_size, lens_size), Image.LANCZOS)
                    lens_photo["image"] = ImageTk.PhotoImage(zoom)
                    lens_canvas.delete("all")
                    lens_canvas.create_rectangle(4, 4, lens_size + lens_padding * 2 - 4,
                                                 lens_size + lens_padding + 8, outline="#3A3A3A",
                                                 width=2, fill="#1A1A1A")
                    lens_canvas.create_image(lens_padding, lens_padding, anchor="nw", image=lens_photo["image"])
                    center = lens_padding + lens_size / 2
                    lens_canvas.create_line(center - 8, lens_padding + lens_size / 2,
                                            center + 8, lens_padding + lens_size / 2, fill="#FFFFFF", width=1)
                    lens_canvas.create_line(lens_padding + lens_size / 2, center - 8,
                                            lens_padding + lens_size / 2, center + 8, fill="#FFFFFF", width=1)
                    current_hex = grab_screen_hex(event.x_root, event.y_root) or "--"
                    lens_canvas.create_text(lens_padding, lens_size + lens_padding + 8, anchor="w",
                                            text=current_hex, fill="#E5E7EB", font=("Arial", 11, "bold"))
                    pos_x = max(10, min(event.x_root + 24, overlay.winfo_screenwidth() - lens_size - 2 * lens_padding - 10))
                    pos_y = max(10, min(event.y_root + 24, overlay.winfo_screenheight() - lens_size - lens_padding - 40))
                    lens_canvas.place(x=pos_x, y=pos_y)
                except Exception as e:
                    print(f"⚠️ Não foi possível atualizar lupa do conta-gotas: {e}")

            def pick_color(event):
                color_hex = grab_screen_hex(event.x_root, event.y_root)
                if color_hex:
                    set_current_color(color_hex)
                finish()

            overlay.bind("<Motion>", update_lens)
            overlay.bind("<Button-1>", pick_color)
            overlay.bind("<Escape>", finish)

        initial_rgb = hex_to_rgb(self.current_color) or (255, 255, 255)
        h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in initial_rgb))
        current_hsv = {"h": h, "s": s, "v": v}

        self._advanced_win = ctk.CTkToplevel(self)
        self._advanced_win.title("Cores")
        self._advanced_win.resizable(True, True)
        self._advanced_win.minsize(390, 450)
        target_w, target_h = 410, 608
        self._advanced_win.geometry(f"{target_w}x{target_h}")
        self._advanced_win.transient(self.winfo_toplevel())
        self._advanced_win.protocol("WM_DELETE_WINDOW", close_picker)
        self._advanced_win.update_idletasks()
        screen_w = self._advanced_win.winfo_screenwidth()
        screen_h = self._advanced_win.winfo_screenheight()
        x = int((screen_w - target_w) / 2)
        y = int((screen_h - target_h) / 2)
        self._advanced_win.geometry(f"{target_w}x{target_h}+{x}+{y}")

        wrapper = ctk.CTkFrame(self._advanced_win, fg_color=self.cget("fg_color"))
        wrapper.pack(fill="both", expand=True, padx=16, pady=16)

        top_row = ctk.CTkFrame(wrapper, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 6))

        preview_btn = ctk.CTkButton(
            top_row,
            text=self.current_color,
            fg_color=self.current_color,
            hover_color=self.current_color,
            text_color=self._get_contrast_color(self.current_color),
            font=("Arial", 12, "bold"),
            height=32,
            width=90,
            corner_radius=10,
            command=lambda: None,
        )
        preview_btn.pack(side="left")

        hex_var = tk.StringVar(value=self.current_color)
        hex_entry = ctk.CTkEntry(top_row, textvariable=hex_var, width=110, font=("Arial", 12))
        hex_entry.pack(side="left", padx=(10, 6))

        eyedropper = ctk.CTkButton(top_row, text="🧪", width=34, height=34,
                                   fg_color="#3A3A3A", hover_color="#4A4A4A",
                                   command=start_eyedropper)
        eyedropper.pack(side="left")

        toolbar = ctk.CTkFrame(wrapper, fg_color="transparent")
        toolbar.pack(fill="x", pady=(6, 6))

        tab_buttons = {}
        tab_frames = {}

        tabs = [
            ("wheel", "⚪", "Roda"),
            ("grays", "⬛", "Web"),
            ("lists", "📃", "Listas"),
            ("pencils", "✏️", "Lápis"),
            ("palettes", "🖼", "Paletas"),
        ]

        tabs_bar = ctk.CTkFrame(toolbar, fg_color="transparent")
        tabs_bar.pack(side="left")

        content_area = ctk.CTkFrame(wrapper, fg_color="transparent")
        content_area.pack(fill="both", expand=True)

        brightness_slider = None
        wheel_canvas = None

        def set_current_color(color_hex, update_entry=True):
            rgb = hex_to_rgb(color_hex)
            if not rgb:
                return
            h_val, s_val, v_val = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
            current_hsv.update({"h": h_val, "s": s_val, "v": v_val})
            preview_btn.configure(fg_color=color_hex, hover_color=color_hex, text=color_hex,
                                  text_color=self._get_contrast_color(color_hex))
            if update_entry:
                hex_var.set(color_hex.upper())
            if brightness_slider is not None:
                brightness_slider.configure(progress_color=color_hex, button_color=color_hex,
                                            button_hover_color=color_hex)
                brightness_slider.set(v_val)
            if wheel_canvas is not None:
                update_marker()
            self.current_color = color_hex.upper()

        def update_from_hex(*_):
            set_current_color(hex_var.get())

        hex_entry.bind("<KeyRelease>", update_from_hex)

        bottom_area = ctk.CTkFrame(wrapper, fg_color="transparent")
        bottom_area.pack(fill="x", pady=(6, 0))

        favorites_frame = ctk.CTkFrame(bottom_area, fg_color="#1F1F1F", corner_radius=8, border_width=1,
                                       border_color="#3A3A3A")
        favorites_frame.pack(fill="x", pady=(0, 8))

        fav_label = ctk.CTkLabel(favorites_frame, text="Favoritos", anchor="w")
        fav_label.pack(fill="x", padx=8, pady=(6, 2))

        fav_grid = ctk.CTkFrame(favorites_frame, fg_color="transparent")
        fav_grid.pack(fill="x", padx=6, pady=(0, 6))
        recent_colors = ["#F1F2EC", "#E6E6E6", "#CCCCCC", "#B3B3B3", "#999999", "#808080",
                         "#666666", "#4D4D4D", "#333333", "#1A1A1A"]
        for color_hex in recent_colors:
            btn = ctk.CTkButton(fav_grid, text="", width=26, height=24, fg_color=color_hex,
                                hover_color=color_hex, corner_radius=4,
                                command=lambda c=color_hex: set_current_color(c))
            btn.pack(side="left", padx=3, pady=3)

        buttons_frame = ctk.CTkFrame(bottom_area, fg_color="transparent")
        buttons_frame.pack(fill="x")
        ctk.CTkButton(buttons_frame, text="Cancelar", fg_color="#6B7280", hover_color="#4B5563",
                      command=close_picker, width=120).pack(side="left", padx=(0, 6))
        ctk.CTkButton(buttons_frame, text="OK", fg_color="#3B82F6", hover_color="#2563EB",
                      command=lambda: (self._select_color(self.current_color), close_picker()), width=120).pack(side="right")

        def register_tab(key, widget):
            tab_frames[key] = widget
            widget.pack_forget()

        def show_tab(key):
            for k, frame in tab_frames.items():
                frame.pack_forget()
            tab_frames[key].pack(fill="both", expand=True)
            for k, btn in tab_buttons.items():
                btn.configure(fg_color="#3B82F6" if k == key else "#2A2A2A",
                               hover_color="#353535" if k == key else "#3A3A3A")

        for key, icon, _tooltip in tabs:
            btn = ctk.CTkButton(
                tabs_bar,
                text=icon,
                width=40,
                height=34,
                corner_radius=8,
                fg_color="#2A2A2A",
                hover_color="#3A3A3A",
                command=lambda k=key: show_tab(k),
            )
            btn.pack(side="left", padx=4)
            tab_buttons[key] = btn

        wheel_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("wheel", wheel_tab)

        wheel_size = 260
        wheel_radius = wheel_size / 2 - 6
        wheel_center = wheel_size / 2

        wheel_image = build_wheel_image(wheel_size, wheel_radius, oversample=4)
        self._wheel_photo = ImageTk.PhotoImage(wheel_image)

        wheel_canvas = Canvas(wheel_tab, width=wheel_size, height=wheel_size, bg="#1F1F1F",
                              highlightthickness=0)
        wheel_canvas.pack(pady=(6, 12))
        wheel_canvas.create_image(0, 0, image=self._wheel_photo, anchor="nw")

        def update_marker():
            wheel_canvas.delete("marker")
            cx = wheel_center + (wheel_radius * current_hsv["s"] * math.cos(current_hsv["h"] * 2 * math.pi))
            cy = wheel_center - (wheel_radius * current_hsv["s"] * math.sin(current_hsv["h"] * 2 * math.pi))
            wheel_canvas.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, outline="#000000", width=2, tags="marker")
            wheel_canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, outline="#FFFFFF", width=2, tags="marker")

        def update_from_hsv():
            color_hex = hsv_to_hex(current_hsv["h"], current_hsv["s"], current_hsv["v"])
            set_current_color(color_hex)

        def on_wheel_click(event):
            dx = event.x - wheel_center
            dy = event.y - wheel_center
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > wheel_radius:
                return
            hue = (math.atan2(-dy, dx) % (2 * math.pi)) / (2 * math.pi)
            sat = min(1.0, dist / wheel_radius)
            current_hsv["h"] = hue
            current_hsv["s"] = sat
            update_from_hsv()

        wheel_canvas.bind("<Button-1>", on_wheel_click)
        wheel_canvas.bind("<B1-Motion>", on_wheel_click)

        slider_frame = ctk.CTkFrame(wheel_tab, fg_color="transparent")
        slider_frame.pack(fill="x", pady=(0, 10), padx=4)
        ctk.CTkLabel(slider_frame, text="Brilho:").pack(side="left")
        brightness_slider = ctk.CTkSlider(slider_frame, from_=0, to=1, number_of_steps=100,
                                          command=lambda val: (current_hsv.__setitem__('v', float(val)), update_from_hsv()))
        brightness_slider.pack(side="left", fill="x", expand=True, padx=10)
        brightness_slider.set(v)

        quick_palette = ctk.CTkFrame(wheel_tab, fg_color="transparent")
        quick_palette.pack(pady=(0, 8))
        palette_colors = [c for row in self.basic_colors for c in row][:24]
        quick_palette_cols = 12
        for idx, color in enumerate(palette_colors):
            btn = ctk.CTkButton(quick_palette, width=24, height=22, text="", fg_color=color,
                                hover_color=color, corner_radius=4,
                                command=lambda c=color: set_current_color(c))
            row = idx // quick_palette_cols
            col = idx % quick_palette_cols
            btn.grid(row=row, column=col, padx=3, pady=3)

        grays_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("grays", grays_tab)

        grayscale_colors = ["#FFFFFF", "#F2F2F2", "#E5E5E5", "#CCCCCC", "#B3B3B3", "#999999", "#808080",
                             "#666666", "#4D4D4D", "#333333", "#1A1A1A", "#000000"]
        gray_frame = ctk.CTkFrame(grays_tab, fg_color="#151515", corner_radius=8, border_width=1,
                                  border_color="#303030")
        gray_frame.pack(fill="both", expand=True, pady=6)

        search_gray = ctk.CTkEntry(gray_frame, placeholder_text="Buscar", height=32)
        search_gray.pack(fill="x", padx=10, pady=(10, 6))

        list_holder = ctk.CTkScrollableFrame(gray_frame, fg_color="#151515")
        list_holder.pack(fill="both", expand=True, padx=6, pady=(0, 10))

        def render_gray_list(filter_text=""):
            for child in list_holder.winfo_children():
                child.destroy()
            for color_hex in grayscale_colors:
                if filter_text and filter_text.lower() not in color_hex.lower():
                    continue
                row = ctk.CTkFrame(list_holder, fg_color="transparent")
                row.pack(fill="x", pady=3, padx=4)
                swatch = ctk.CTkButton(row, text="", width=32, height=28, fg_color=color_hex,
                                        hover_color=color_hex, corner_radius=6,
                                        command=lambda c=color_hex: set_current_color(c))
                swatch.pack(side="left", padx=(0, 10))
                ctk.CTkLabel(row, text=color_hex, font=("Arial", 12)).pack(side="left")

        search_gray.bind("<KeyRelease>", lambda e: render_gray_list(search_gray.get()))
        render_gray_list()

        lists_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("lists", lists_tab)

        list_top = ctk.CTkFrame(lists_tab, fg_color="transparent")
        list_top.pack(fill="x", pady=(6, 6))

        palettes_named = {
            "Web": [
                ("Lima", "#BFFF00"), ("Turquesa", "#30D5C8"), ("Aqua", "#00FFFF"), ("Violeta", "#8F00FF"),
                ("Orquídea", "#DA70D6"), ("Céu", "#00BFFF"), ("Espuma", "#AFE1AF"), ("Prata", "#C0C0C0"),
            ],
            "Desenvolvedor": [
                ("controlAccentColor", "#0A84FF"), ("systemBlue", "#0A84FF"), ("findHighlight", "#FFD60A"),
                ("windowBackgroundColor", "#1E1E1E"), ("labelColor", "#FFFFFF"), ("separatorColor", "#2C2C2E"),
            ],
            "Apple": [
                ("Azul", "#0A84FF"), ("Marrom", "#AC8E68"), ("Ciano", "#32ADE6"), ("Verde", "#30D158"),
                ("Magenta", "#FF2D55"), ("Laranja", "#FF9500"), ("Amarelo", "#FFD60A"), ("Roxo", "#BF5AF2"),
                ("Vermelho", "#FF3B30"), ("Branco", "#FFFFFF"),
            ],
        }

        palette_selector = ctk.CTkComboBox(list_top, values=list(palettes_named.keys()), state="readonly", width=150)
        palette_selector.set("Web")
        palette_selector.pack(side="left", padx=(0, 8))

        search_list = ctk.CTkEntry(list_top, placeholder_text="Buscar", width=160)
        search_list.pack(side="left")

        list_area = ctk.CTkScrollableFrame(lists_tab, fg_color="#151515")
        list_area.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        def render_named():
            for child in list_area.winfo_children():
                child.destroy()
            palette = palette_selector.get()
            search_text = search_list.get().lower()
            for name, color_hex in palettes_named.get(palette, []):
                if search_text and search_text not in name.lower() and search_text not in color_hex.lower():
                    continue
                row = ctk.CTkFrame(list_area, fg_color="transparent")
                row.pack(fill="x", pady=4, padx=6)
                swatch = ctk.CTkButton(row, text="", width=32, height=28, fg_color=color_hex,
                                        hover_color=color_hex, corner_radius=6,
                                        command=lambda c=color_hex: set_current_color(c))
                swatch.pack(side="left", padx=(0, 10))
                ctk.CTkLabel(row, text=name, font=("Arial", 12)).pack(side="left")
                ctk.CTkLabel(row, text=color_hex, font=("Arial", 11), text_color="#9CA3AF").pack(side="right")

        palette_selector.configure(command=lambda _: render_named())
        search_list.bind("<KeyRelease>", lambda e: render_named())
        render_named()

        pencils_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("pencils", pencils_tab)

        pencil_sets = {
            "Prata": ["#F7F7F7", "#E2E2E2", "#C5C5C5", "#AAAAAA", "#919191", "#777777", "#5E5E5E"],
            "Clássico": ["#FF3B30", "#FF9500", "#FFD60A", "#34C759", "#0A84FF", "#5856D6", "#AF52DE"],
            "Neon": ["#FF2D55", "#FF6B81", "#FF9500", "#FFD60A", "#64D2FF", "#30DB5B", "#AC8E68"],
        }

        combo_pencil = ctk.CTkComboBox(pencils_tab, values=list(pencil_sets.keys()), state="readonly", width=150)
        combo_pencil.set("Prata")
        combo_pencil.pack(pady=(8, 4))

        pencils_canvas = Canvas(pencils_tab, width=330, height=170, bg="#151515", highlightthickness=0)
        pencils_canvas.pack(pady=(0, 8))

        def draw_pencils():
            pencils_canvas.delete("all")
            colors = pencil_sets.get(combo_pencil.get(), [])
            cols = 7
            rows = 4
            spacing_x = 48
            spacing_y = 42
            start_x = 16
            start_y = 10
            idx = 0
            for r in range(rows):
                for c in range(cols):
                    if idx >= len(colors):
                        break
                    x = start_x + c * spacing_x
                    y = start_y + r * spacing_y
                    color_hex = colors[idx % len(colors)]
                    pencils_canvas.create_polygon(
                        x, y + 10, x + 18, y, x + 36, y + 10, x + 36, y + 44, x, y + 44,
                        fill=color_hex, outline="#2E2E2E", width=1, tags=("pencil", color_hex)
                    )
                    pencils_canvas.create_polygon(
                        x + 12, y - 4, x + 18, y + 10, x + 24, y - 4,
                        fill="#D8D2C4", outline="#2E2E2E", width=1, tags=("pencil", color_hex)
                    )
                    pencils_canvas.create_rectangle(
                        x + 4, y + 10, x + 32, y + 40, fill=color_hex, outline="", tags=("pencil", color_hex)
                    )
                    idx += 1

        def on_pencil_click(event):
            items = pencils_canvas.find_withtag("current")
            if not items:
                return
            tags = pencils_canvas.gettags(items[0])
            for t in tags:
                if t.startswith("#"):
                    set_current_color(t)
                    break

        pencils_canvas.bind("<Button-1>", on_pencil_click)
        combo_pencil.configure(command=lambda _: draw_pencils())
        draw_pencils()

        palette_tab = ctk.CTkFrame(content_area, fg_color="transparent")
        register_tab("palettes", palette_tab)

        palettes_grid = [c for row in self.basic_colors for c in row]
        grid_frame = ctk.CTkScrollableFrame(palette_tab, fg_color="#151515")
        grid_frame.pack(fill="both", expand=True, padx=4, pady=6)

        def render_grid():
            for child in grid_frame.winfo_children():
                child.destroy()
            cols = 12
            for idx, color_hex in enumerate(palettes_grid):
                btn = ctk.CTkButton(grid_frame, text="", width=32, height=28, fg_color=color_hex,
                                    hover_color=color_hex, corner_radius=6,
                                    command=lambda c=color_hex: set_current_color(c))
                row = idx // cols
                col = idx % cols
                btn.grid(row=row, column=col, padx=4, pady=4)

        render_grid()

        set_current_color(self.current_color)
        show_tab("wheel")

    def set_color(self, color):
        self._select_color(color)

    def get_color(self):
        return self.current_color

    def _get_contrast_color(self, hex_color):
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#000000" if luminance > 0.5 else "#FFFFFF"
        except:
            return "#FFFFFF"




class _Chip(ctk.CTkButton):
    def __init__(self, master, text, command, is_active=False, **kw):
        self.label_text = text
        self.is_active = is_active
        display_text = f"● {text}" if is_active else text
        font_style = ("Arial", 10, "normal")

        super().__init__(
            master,
            text=display_text,
            command=command,
            height=22,
            corner_radius=8,
            font=font_style,
            **kw
        )

    def set_active(self, active: bool):
        self.is_active = active
        display_text = f"● {self.label_text}" if active else self.label_text
        font_style = ("Arial", 10, "normal")
        self.configure(text=display_text, font=font_style)


# =================== FUNÇÕES UTILITÁRIAS DE COR ===================

HEX_RE = re.compile(r"^#([0-9a-fA-F]{6})$")


def _valida_hex(s):
    return bool(HEX_RE.match(s or ""))


def get_contraste_texto(cor_fundo):
    """Calcula a cor do texto com melhor contraste para um fundo"""
    try:
        if not cor_fundo or not isinstance(cor_fundo, str):
            return "#000000"

        hex_color = cor_fundo.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#000000" if luminance > 0.5 else "#FFFFFF"
    except Exception:
        return "#000000"

def is_dark_color(cor_hex: str) -> bool:
    """
    Retorna True se a cor for considerada ESCURA, False se for CLARA.

    Usado pelo MENU_PRINCIPAL / ThemeManager para decidir ajustes de contraste
    (ex.: ícones claros em fundo escuro, bordas, etc.).
    """
    try:
        if not cor_hex or not isinstance(cor_hex, str):
            return False  # assume clara se inválida

        hex_color = cor_hex.lstrip("#")
        if len(hex_color) != 6:
            return False

        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # mesma base da get_contraste_texto: luminância aproximada
        luminancia = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

        # se a luminância for baixa, consideramos "dark"
        return luminancia < 0.5
    except Exception:
        return False



def ajustar_hover(cor_base, fator=0.8):
    """Ajusta a cor para efeito hover"""
    try:
        if not cor_base or not isinstance(cor_base, str):
            return cor_base

        hex_color = cor_base.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        r = int(r * fator)
        g = int(g * fator)
        b = int(b * fator)

        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))

        return f"#{r:02x}{g:02x}{b:02x}".upper()
    except Exception:
        return cor_base


def _normalizar_texto_botao(texto: str) -> str:
    """Normaliza texto do botão para comparação."""
    try:
        import unicodedata

        texto_limpo = (texto or "").strip().lower()
        texto_limpo = unicodedata.normalize("NFKD", texto_limpo)
        texto_limpo = "".join(ch for ch in texto_limpo if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", texto_limpo)
    except Exception:
        return (texto or "").strip().lower()


def _estilo_botao_por_texto(texto: str) -> dict:
    """Define estilo de botão por texto (referência padrão do sistema)."""
    texto_norm = _normalizar_texto_botao(texto)

    negativos = ("excluir", "deletar", "remover", "apagar", "inativar", "cancelar")
    positivos = ("salvar", "adicionar", "buscar", "cadastrar", "importar", "confirmar")
    destaques = (
        "exportar",
        "imprimir",
        "pdf",
        "gerar pdf",
        "comprovante",
        "visualizar pdf",
        "editar",
    )

    if any(chave in texto_norm for chave in negativos):
        return {
            "fg_color": "#FA0000",
            "hover_color": "#7A0101",
            "text_color": "#000000",
            "text_color_hover": "#FFFFFF",
        }

    if any(chave in texto_norm for chave in positivos):
        return {
            "fg_color": "#1B8305",
            "hover_color": "#2A671F",
            "text_color": "#000000",
            "text_color_hover": "#FFFFFF",
        }

    if any(chave in texto_norm for chave in destaques):
        return {
            "fg_color": "#FF5C00",
            "hover_color": "#6E2800",
            "text_color": "#000000",
            "text_color_hover": "#FFFFFF",
        }

    return {
        "fg_color": "#7AB8F5",
        "hover_color": "#5A9BDF",
        "text_color": "#000000",
        "text_color_hover": "#FFFFFF",
    }


def _aplicar_hover_texto_botao(widget: ctk.CTkButton, normal: str, hover: str):
    """Configura mudança de cor do texto no hover (CTkButton)."""
    if getattr(widget, "_opera_hover_texto", None):
        return

    def on_enter(_event=None):
        try:
            widget.configure(text_color=hover)
        except Exception:
            pass

    def on_leave(_event=None):
        try:
            widget.configure(text_color=normal)
        except Exception:
            pass

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)
    widget._opera_hover_texto = True


def padronizar_botao(widget: ctk.CTkButton):
    """Aplica padrão de cores a um CTkButton baseado no texto."""
    try:
        texto = widget.cget("text")
    except Exception:
        texto = ""

    if not texto:
        return

    estilo = _estilo_botao_por_texto(texto)
    widget.configure(
        fg_color=estilo["fg_color"],
        hover_color=estilo["hover_color"],
        text_color=estilo["text_color"],
        border_width=0,
    )
    _aplicar_hover_texto_botao(widget, estilo["text_color"], estilo["text_color_hover"])


def padronizar_botoes_container(widget):
    """Padroniza todos os CTkButton de um container recursivamente."""
    try:
        if isinstance(widget, ctk.CTkButton):
            padronizar_botao(widget)

        for child in widget.winfo_children():
            padronizar_botoes_container(child)
    except Exception as e:
        print(f"[Temas] Erro ao padronizar botões: {e}")


def _blend(base_hex: str, target_hex: str, t: float) -> str:
    """Mistura duas cores hex com fator t (0-1)."""
    try:
        base = (base_hex or "").strip().lstrip("#")
        target = (target_hex or "").strip().lstrip("#")
        if len(base) != 6 or len(target) != 6:
            return base_hex
        br, bg, bb = (int(base[0:2], 16), int(base[2:4], 16), int(base[4:6], 16))
        tr, tg, tb = (int(target[0:2], 16), int(target[2:4], 16), int(target[4:6], 16))
        r = int(br + (tr - br) * t)
        g = int(bg + (tg - bg) * t)
        b = int(bb + (tb - bb) * t)
        return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}".upper()
    except Exception:
        return base_hex


def aplicar_estilo_treeview(
    *,
    style: "ttk.Style" | None = None,
    prefixo: str = "Treeview",
    cor_fundo: str = "#FFFFFF",
    cor_linhas: str = "#F5F5F5",
    cor_cabecalho: str = "#0D6EFD",
    cor_texto: str | None = None,
    cor_borda: str = "#CED4DA",
    cor_selecao: str = "#0D6EFD",
    altura_linha: int = 25,
):
    """Aplica o estilo padrão de Treeview usado no *Cadastro de Modelo*.

    Esse padrão garante contraste dinâmico para texto e efeito de hover
    em cabeçalhos e linhas selecionadas.
    """

    try:
        style = style or ttk.Style()

        try:
            style.theme_use("clam")
        except Exception:
            pass

        tema_escuro = is_dark_color(cor_fundo)

        if tema_escuro:
            tree_bg = cor_linhas
            tree_fg = cor_texto or get_contraste_texto(cor_linhas)
            field_bg = cor_linhas
            heading_bg = cor_cabecalho
            heading_fg = get_contraste_texto(heading_bg)
            zebra_even = cor_fundo
            zebra_odd = cor_linhas
            select_bg = _blend(heading_bg, "#FFFFFF", 0.18)
            select_fg = get_contraste_texto(select_bg)
            border = cor_borda
        else:
            tree_bg = "#FFFFFF"
            tree_fg = "#000000"
            field_bg = "#FFFFFF"
            heading_bg = "#EEEEEE"
            heading_fg = "#000000"
            zebra_even = "#FFFFFF"
            zebra_odd = "#D9D9D9"
            select_bg = "#B7D7FF"
            select_fg = "#000000"
            border = "#C7C7C7"

        style.configure(
            prefixo,
            background=tree_bg,
            fieldbackground=field_bg,
            foreground=tree_fg,
            rowheight=26,
            bordercolor=border,
            borderwidth=1,
            font=("Arial", 10),
            relief="solid",
        )

        style.configure(
            f"{prefixo}.Heading",
            background=heading_bg,
            foreground=heading_fg,
            relief="flat",
            font=("Arial", 10, "bold"),
            borderwidth=0,
            padding=(8, 6),
        )

        style.map(
            prefixo,
            background=[("selected", select_bg)],
            foreground=[("selected", select_fg)],
        )

        if (heading_fg or "").lower() in ("#000", "#000000", "black"):
            heading_hover_bg = _blend(heading_bg, "#000000", 0.14)
            heading_pressed_bg = _blend(heading_bg, "#000000", 0.24)
        else:
            heading_hover_bg = _blend(heading_bg, "#FFFFFF", 0.14)
            heading_pressed_bg = _blend(heading_bg, "#FFFFFF", 0.24)

        style.map(
            f"{prefixo}.Heading",
            background=[("active", heading_hover_bg), ("pressed", heading_pressed_bg)],
            foreground=[("active", heading_fg), ("pressed", heading_fg)],
            relief=[("active", "flat"), ("pressed", "flat")],
        )

        return style, (zebra_even, zebra_odd)
    except Exception as e:
        print(f"[Temas] Erro ao aplicar estilo Treeview: {e}")
        return None, None


def aplicar_tags_alternadas(tree: ttk.Treeview, cor_par: str, cor_impar: str):
    """Configura tags de linhas alternadas com contraste automático."""

    try:
        tree.tag_configure("evenrow", background=cor_par, foreground=get_contraste_texto(cor_par))
        tree.tag_configure("oddrow", background=cor_impar, foreground=get_contraste_texto(cor_impar))

        for i, item in enumerate(tree.get_children()):
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            tree.item(item, tags=(tag,))
    except Exception as e:
        print(f"[Temas] Erro ao aplicar tags alternadas: {e}")


def padronizar_treeview(tree: ttk.Treeview, prefixo: str | None = None):
    """Aplica o padrão visual oficial de Treeview usando as cores do tema atual."""

    try:
        app = tree.winfo_toplevel()

        cor_fundo = getattr(app, "cor_fundo", "#FFFFFF")
        cor_secundaria = getattr(app, "cor_secundaria", "#F5F5F5")
        cor_primaria = getattr(app, "cor_primaria", "#0D6EFD")
        cor_texto = getattr(app, "cor_texto", get_contraste_texto(cor_fundo))
        cor_borda = getattr(app, "cor_borda", "#CED4DA")

        nome_prefixo = prefixo or tree.cget("style") or "Treeview"

        estilo, zebra = aplicar_estilo_treeview(
            prefixo=nome_prefixo,
            cor_fundo=cor_fundo,
            cor_linhas=cor_secundaria,
            cor_cabecalho=cor_primaria,
            cor_texto=cor_texto,
            cor_borda=cor_borda,
            cor_selecao=cor_primaria,
        )

        if estilo:
            tree.configure(style=nome_prefixo)
            if zebra:
                aplicar_tags_alternadas(tree, zebra[0], zebra[1])
            else:
                aplicar_tags_alternadas(tree, cor_secundaria, cor_fundo)
    except Exception as e:
        print(f"[Temas] Erro ao padronizar Treeview: {e}")


def padronizar_treeviews_container(widget):
    """Padroniza todas as Treeviews de um container recursivamente."""

    try:
        if isinstance(widget, ttk.Treeview):
            padronizar_treeview(widget)

        for child in widget.winfo_children():
            padronizar_treeviews_container(child)
    except Exception as e:
        print(f"[Temas] Erro ao padronizar Treeviews do container: {e}")


# Aplicar padronização automática a toda Treeview criada após importar este módulo
try:
    _ORIGINAL_TREEVIEW_INIT
except NameError:
    _ORIGINAL_TREEVIEW_INIT = ttk.Treeview.__init__

    def _treeview_init_padrao(self, *args, **kwargs):
        _ORIGINAL_TREEVIEW_INIT(self, *args, **kwargs)
        try:
            padronizar_treeview(self, kwargs.get("style"))
        except Exception:
            pass

    ttk.Treeview.__init__ = _treeview_init_padrao


def remover_bordas_botoes_tema(widget):
    """
    Remove bordas, contornos, relieves e outlines de TODOS os botões
    pertencentes ao widget informado (menu, topbar, páginas etc.)
    """

    # Tipos de widgets CTk aceitos
    botoes = (
        ctk.CTkButton,
        ctk.CTkOptionMenu,
        ctk.CTkComboBox,
        ctk.CTkSegmentedButton,
        ctk.CTkSwitch,
    )
    estilo_ttk = None
    try:
        estilo_ttk = ttk.Style()
        estilo_ttk.configure(
            "TButton",
            relief=tk.FLAT,
            borderwidth=0,
            focusthickness=0,
            highlightthickness=0,
            padding=6,
        )
        estilo_ttk.configure(
            "Opera.TButton",
            relief=tk.FLAT,
            borderwidth=0,
            focusthickness=0,
            highlightthickness=0,
            padding=6,
        )
        estilo_ttk.map(
            "TButton",
            relief=[("pressed", tk.FLAT), ("active", tk.FLAT)],
            bordercolor=[("pressed", ""), ("active", "")],
        )
        estilo_ttk.map(
            "Opera.TButton",
            relief=[("pressed", tk.FLAT), ("active", tk.FLAT)],
            bordercolor=[("pressed", ""), ("active", "")],
        )
    except Exception:
        estilo_ttk = None

    try:
        # Se for um botão diretamente
        if isinstance(widget, botoes):
            try:
                fg = widget.cget("fg_color") if hasattr(widget, "cget") else None
                hover = widget.cget("hover_color") if hasattr(widget, "cget") else None
                texto = widget.cget("text_color") if hasattr(widget, "cget") else None

                widget.configure(
                    border_width=0,
                    corner_radius=getattr(widget, "corner_radius", 8),
                    fg_color=fg or "transparent",
                    hover_color=hover or fg or "transparent",
                    text_color=texto if texto not in (None, "") else None,
                )
                try:
                    widget.configure(highlightthickness=0)
                except Exception:
                    pass
            except Exception:
                pass

        if isinstance(widget, tk.Button):
            try:
                widget.configure(
                    borderwidth=0,
                    highlightthickness=0,
                    relief=tk.FLAT,
                )
            except Exception:
                pass

        if isinstance(widget, ttk.Button):
            try:
                widget.configure(style="Opera.TButton")
                widget.state(["!focus"])
            except Exception:
                pass

        # Se possuir filhos, aplicar recursivamente
        if hasattr(widget, "winfo_children"):
            for child in widget.winfo_children():
                remover_bordas_botoes_tema(child)

    except Exception as e:
        print(f"[Temas] Erro ao remover bordas: {e}")


# =================== MÓDULO DE PALETAS ===================

class ModuloPaletas:
    """Gerencia todas as paletas de cores (padrão e personalizadas)"""

    CAMPOS_PADRAO = [
        "primaria", "secundaria", "terciaria", "fundo", "texto", "destaque",
        "sucesso", "alerta", "borda", "hover", "selecao",
        "botao_salvar", "botao_excluir", "botao_novo", "botao_imprimir",
        "botao_pdf", "botao_editar", "botao_visualizar", "botao_confirmar",
        "botao_cancelar", "botao_exportar", "botao_importar", "botao_configurar",
        "botao_ajuda", "botao_filtrar", "botao_limpar", "botao_voltar", "botao_avancar",
        "botao_adiantamento", "botao_comprovante", "botao_buscar", "botao_export_csv", "botao_export_pdf"
    ]

    LABELS_CAMPOS_PADRAO = {
        "primaria": "Primária", "secundaria": "Secundária", "terciaria": "Terciária",
        "fundo": "Fundo", "texto": "Texto", "destaque": "Destaque", "sucesso": "Sucesso",
        "alerta": "Alerta", "borda": "Borda", "hover": "Hover", "selecao": "Seleção",
        "botao_salvar": "Botão Salvar", "botao_excluir": "Botão Excluir", "botao_novo": "Botão Novo",
        "botao_imprimir": "Botão Imprimir", "botao_pdf": "Botão PDF", "botao_editar": "Botão Editar",
        "botao_visualizar": "Botão Visualizar", "botao_confirmar": "Botão Confirmar",
        "botao_cancelar": "Botão Cancelar", "botao_exportar": "Botão Exportar",
        "botao_importar": "Botão Importar", "botao_configurar": "Botão Configurar",
        "botao_ajuda": "Botão Ajuda", "botao_filtrar": "Botão Filtrar", "botao_limpar": "Botão Limpar",
        "botao_voltar": "Botão Voltar", "botao_avancar": "Botão Avançar",
        "botao_adiantamento": "Botão Registrar Adiantamento",
        "botao_comprovante": "Botão Imprimir Comprovante", "botao_buscar": "Botão Buscar",
        "botao_export_csv": "Botão Exportar CSV", "botao_export_pdf": "Botão Exportar PDF"
    }

    def __init__(self):
        self.PADROES = copy.deepcopy(self._carregar_temas_padrao())
        self.temas_originais = copy.deepcopy(self.PADROES)
        self.custom = {}
        self.padrao_universal = BotaoPadronizado.CORES_BOTOES_PADRAO

    def _carregar_temas_padrao(self):
        """Carrega todos os temas padrão do sistema, padronizados e sem duplicações."""

        temas = {

            # ==========================================================
            #  TEMA: AZUL OCEANO
            # ==========================================================
            "Azul Oceano": {
                "primaria": "#0D1B2A", "secundaria": "#1B263B", "terciaria": "#415A77", "fundo": "#0B1320",
                "texto": "#E0E1DD", "destaque": "#3A86FF", "sucesso": "#3BCF8E", "alerta": "#EF476F",
                "borda": "#2E4057", "hover": "#253041", "selecao": "#3A86FF",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            #  TEMA CLÁSSICO CLARO
            # ==========================================================
            "CLÁSSICO CLARO": {
                "primaria": "#F4F4F5", "secundaria": "#D4D4D8", "terciaria": "#A1A1AA", "fundo": "#FFFFFF",
                "texto": "#111827", "destaque": "#4B5563", "selecao": "#AFAFAF",
                "sucesso": "#2E7D32", "alerta": "#C62828", "borda": "#9CA3AF", "hover": "#E4E4E7",

                **BotaoPadronizado.CORES_BOTOES_PADRAO,

                "botao_salvar": "#10B981", "botao_excluir": "#EF4444", "botao_novo": "#3B82F6",
                "botao_imprimir": "#8B5CF6", "botao_pdf": "#F59E0B", "botao_editar": "#06B6D4",
                "botao_visualizar": "#6366F1", "botao_confirmar": "#22C55E", "botao_cancelar": "#6B7280",
                "botao_exportar": "#8B5CF6", "botao_importar": "#06B6D4", "botao_configurar": "#6B7280",
                "botao_ajuda": "#3B82F6", "botao_filtrar": "#6366F1", "botao_limpar": "#F59E0B",
                "botao_voltar": "#6B7280", "botao_avancar": "#10B981",
                "botao_adiantamento": "#10B981", "botao_comprovante": "#8B5CF6",
                "botao_buscar": "#3B82F6", "botao_export_csv": "#06B6D4",
                "botao_export_pdf": "#F59E0B"
            },

            # ==========================================================
            #  CINZA OCEANO ESCURO
            # ==========================================================
            "Cinza Oceano Escuro": {
                "primaria": "#1A1A1A", "secundaria": "#242424", "terciaria": "#3E3E3E", "fundo": "#141414",
                "texto": "#E0E1DD", "destaque": "#6B6B6B", "sucesso": "#3BCF8E", "alerta": "#EF476F",
                "borda": "#353535", "hover": "#2A2A2A", "selecao": "#6B6B6B",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Grafite Oceano": {
                "primaria": "#0F0F0F", "secundaria": "#1C1C1C", "terciaria": "#333333", "fundo": "#0A0A0A",
                "texto": "#E0E1DD", "destaque": "#5A5A5A", "sucesso": "#3BCF8E", "alerta": "#EF476F",
                "borda": "#2B2B2B", "hover": "#1F1F1F", "selecao": "#5A5A5A",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Carvão Oceano": {
                "primaria": "#121212", "secundaria": "#1F1F1F", "terciaria": "#3A3A3A", "fundo": "#0D0D0D",
                "texto": "#E0E1DD", "destaque": "#4D4D4D", "sucesso": "#3BCF8E", "alerta": "#EF476F",
                "borda": "#2E2E2E", "hover": "#232323", "selecao": "#4D4D4D",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Cinza Oceano Claro": {
                "primaria": "#D5D5D5", "secundaria": "#C2C2C2", "terciaria": "#9E9E9E", "fundo": "#E8E8E8",
                "texto": "#1A1A1A", "destaque": "#6B6B6B", "sucesso": "#2E9E6E", "alerta": "#D63854",
                "borda": "#ABABAB", "hover": "#CFCFCF", "selecao": "#6B6B6B",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Prata Oceano": {
                "primaria": "#BEBEBE", "secundaria": "#ABABAB", "terciaria": "#8A8A8A", "fundo": "#D4D4D4",
                "texto": "#1A1A1A", "destaque": "#5A5A5A", "sucesso": "#2E9E6E", "alerta": "#D63854",
                "borda": "#999999", "hover": "#B5B5B5", "selecao": "#5A5A5A",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Névoa Oceano": {
                "primaria": "#C9C9C9", "secundaria": "#B6B6B6", "terciaria": "#949494", "fundo": "#DEDEDE",
                "texto": "#1A1A1A", "destaque": "#636363", "sucesso": "#2E9E6E", "alerta": "#D63854",
                "borda": "#A3A3A3", "hover": "#808080", "selecao": "#008000",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Rosé Elegante": {
                "primaria": "#2B2233", "secundaria": "#3A2A45", "terciaria": "#5E3C58", "fundo": "#241C2B",
                "texto": "#FFE9F3", "destaque": "#FF5C8A", "sucesso": "#72E5C1", "alerta": "#FF7B7B",
                "borda": "#4B3B55", "hover": "#34283F", "selecao": "#FF5C8A",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Terra Natural": {
                "primaria": "#2E241A", "secundaria": "#3B2F22", "terciaria": "#6B4E3D", "fundo": "#221A12",
                "texto": "#F0E7DD", "destaque": "#D9A441", "sucesso": "#7FB069", "alerta": "#CE6A46",
                "borda": "#4A3A2C", "hover": "#3A2D22", "selecao": "#D9A441",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Noite Urbana": {
                "primaria": "#121212", "secundaria": "#1F1F1F", "terciaria": "#3E3E3E", "fundo": "#181818",
                "texto": "#EEEEEE", "destaque": "#BB86FC", "sucesso": "#03DAC6", "alerta": "#CF6679",
                "borda": "#3A3A3A", "hover": "#2C2C2C", "selecao": "#BB86FC",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Minimal": {
                "primaria": "#F5F5F5", "secundaria": "#E0E0E0", "terciaria": "#C2C2C2", "fundo": "#FFFFFF",
                "texto": "#212121", "destaque": "#9E9E9E", "sucesso": "#66BB6A", "alerta": "#EF5350",
                "borda": "#BDBDBD", "hover": "#EEEEEE", "selecao": "#9E9E9E",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Roxo Elegante": {
                "primaria": "#1E1327", "secundaria": "#291A36", "terciaria": "#432C56", "fundo": "#180F22",
                "texto": "#EDE7F6", "destaque": "#7C4DFF", "sucesso": "#00E5FF", "alerta": "#F06292",
                "borda": "#352443", "hover": "#241633", "selecao": "#7C4DFF",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Verde Corporativo": {
                "primaria": "#0F241D", "secundaria": "#15342A", "terciaria": "#1F4D3D", "fundo": "#0B1A15",
                "texto": "#E8F5E9", "destaque": "#26A69A", "sucesso": "#66BB6A", "alerta": "#FF7043",
                "borda": "#1A3A2F", "hover": "#17362D", "selecao": "#26A69A",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Preto e Ouro": {
                "primaria": "#121212", "secundaria": "#1A1A1A", "terciaria": "#333333", "fundo": "#0B0B0B",
                "texto": "#F6F3E7", "destaque": "#D4AF37", "sucesso": "#7CB342", "alerta": "#F4511E",
                "borda": "#2E2E2E", "hover": "#222222", "selecao": "#D4AF37",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Clássico": {
                "primaria": "#20232A", "secundaria": "#2C313C", "terciaria": "#3B4252", "fundo": "#1B1E24",
                "texto": "#ECEFF4", "destaque": "#61AFEF", "sucesso": "#98C379", "alerta": "#E06C75",
                "borda": "#2E3440", "hover": "#262B36", "selecao": "#61AFEF",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "NOTURNO": {
                "primaria": "#0C0F14", "secundaria": "#141824", "terciaria": "#1E2635", "fundo": "#0B0E13",
                "texto": "#DDE2E9", "destaque": "#4CC9F0", "sucesso": "#2DE2A6", "alerta": "#FF477E",
                "borda": "#1A2030", "hover": "#171C28", "selecao": "#4CC9F0",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Slate Pro": {
                "primaria": "#1F2937", "secundaria": "#273246", "terciaria": "#3B4B63", "fundo": "#151A24",
                "texto": "#E5E7EB", "destaque": "#60A5FA", "sucesso": "#34D399", "alerta": "#F87171",
                "borda": "#2C3647", "hover": "#232C3B", "selecao": "#60A5FA",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Grafite Clean": {
                "primaria": "#222222", "secundaria": "#2C2C2C", "terciaria": "#3A3A3A", "fundo": "#1A1A1A",
                "texto": "#EDEDED", "destaque": "#8AB4F8", "sucesso": "#57D38C", "alerta": "#FF6B6B",
                "borda": "#333333", "hover": "#2A2A2A", "selecao": "#8AB4F8",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Aço Azul": {
                "primaria": "#16212F", "secundaria": "#1E2B3C", "terciaria": "#2C3E55", "fundo": "#111925",
                "texto": "#E6EDF5", "destaque": "#4EA8DE", "sucesso": "#2DD4BF", "alerta": "#FB7185",
                "borda": "#233247", "hover": "#1B2738", "selecao": "#4EA8DE",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Oliva Urbano": {
                "primaria": "#172017", "secundaria": "#1F2A1F", "terciaria": "#2C3A2C", "fundo": "#121A12",
                "texto": "#E9F5EA", "destaque": "#7FB069", "sucesso": "#86EFAC", "alerta": "#F59E0B",
                "borda": "#223123", "hover": "#1A241A", "selecao": "#7FB069",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Cobalto Pro": {
                "primaria": "#0F1626", "secundaria": "#172035", "terciaria": "#22314F", "fundo": "#0B1120",
                "texto": "#E2E8F0", "destaque": "#3B82F6", "sucesso": "#10B981", "alerta": "#EF4444",
                "borda": "#1B2740", "hover": "#132037", "selecao": "#3B82F6",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Petróleo": {
                "primaria": "#102022", "secundaria": "#173034", "terciaria": "#22464C", "fundo": "#0B1719",
                "texto": "#E3F2F4", "destaque": "#22D3EE", "sucesso": "#34D399", "alerta": "#F59E0B",
                "borda": "#1A3236", "hover": "#13282C", "selecao": "#22D3EE",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Chumbo & Laranja": {
                "primaria": "#1A1E24", "secundaria": "#232833", "terciaria": "#2E3542", "fundo": "#141821",
                "texto": "#EDEFF3", "destaque": "#FB923C", "sucesso": "#22C55E", "alerta": "#EF4444",
                "borda": "#2A303C", "hover": "#1D2230", "selecao": "#FB923C",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Neve Azul": {
                "primaria": "#E9EEF5", "secundaria": "#DDE6F1", "terciaria": "#C9D4E6", "fundo": "#F6FAFF",
                "texto": "#1F2937", "destaque": "#2563EB", "sucesso": "#059669", "alerta": "#DC2626",
                "borda": "#CBD5E1", "hover": "#E2EAF6", "selecao": "#2563EB",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },

            # ==========================================================
            "Titanium": {
                "primaria": "#1C1F26", "secundaria": "#262A33", "terciaria": "#313643", "fundo": "#171A21",
                "texto": "#E6E8EB", "destaque": "#9AA4FF", "sucesso": "#5EEAD4", "alerta": "#F87171",
                "borda": "#2A2E38", "hover": "#1F2330", "selecao": "#9AA4FF",
                **BotaoPadronizado.CORES_BOTOES_PADRAO
            },
        }

        return temas

    def carregar_temas_do_banco(self, app):
        """Carrega temas personalizados do banco de dados"""
        import json
        try:
            usuario_id = getattr(app, "usuario_id", None)
            if not usuario_id:
                print("⚠️ Nenhum usuário definido para carregar temas personalizados.")
                return False

            from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema
            conn = get_conn()
            if not conn:
                print("⚠️ Conexão com banco não disponível para carregar temas personalizados.")
                return False

            schema = get_schema()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT nome_tema, cores_tema
                        FROM {schema}.usuario_temas_personalizados
                        WHERE usuario_id = %s
                        ORDER BY nome_tema
                        """,
                        (usuario_id,),
                    )
                    rows = cur.fetchall() or []

            carregados = 0
            for nome_tema, cores_tema in rows:
                try:
                    if isinstance(cores_tema, dict):
                        tema_data = cores_tema
                    else:
                        tema_data = json.loads(cores_tema) if cores_tema else {}

                    if isinstance(tema_data, dict):
                        self.custom[nome_tema] = tema_data
                        carregados += 1
                except Exception as erro_tema:
                    print(f"⚠️ Erro ao processar tema '{nome_tema}' do banco: {erro_tema}")

            print(f"🎨 Temas personalizados carregados do banco: {carregados}")
            return True

        except Exception as erro:
            print(f"❌ Erro ao carregar temas personalizados do banco: {erro}")
            return False

    def garantir_padrao_botoes(self):
        """Garante que todos os temas tenham o padrão completo de cores dos botões"""
        # Aplica para todos os temas padrão
        for tema_nome, tema_cores in self.PADROES.items():
            for botao, cor_padrao in self.padrao_universal.items():
                if botao not in tema_cores or not tema_cores[botao]:
                    tema_cores[botao] = cor_padrao

        # Aplica para todos os temas personalizados
        for tema_nome, tema_cores in self.custom.items():
            for botao, cor_padrao in self.padrao_universal.items():
                if botao not in tema_cores or not tema_cores[botao]:
                    tema_cores[botao] = cor_padrao

        print("🎨 Padrão de botões aplicado a todos os temas")

    def obter_tema(self, nome_tema):
        """Obtém um tema seja ele padrão ou personalizado"""
        if nome_tema in self.custom:
            return self.custom[nome_tema]
        elif nome_tema in self.PADROES:
            return self.PADROES[nome_tema]
        return None


# =================== PAINEL DE PREVIEW ===================

class PreviewPanel(ctk.CTkFrame):
    """Painel de preview de temas"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.highlighted_element = None
        self.original_border_widths = {}
        self._build_preview()

    def _build_preview(self):
        """Constrói a interface do painel de preview"""
        self.title_label = ctk.CTkLabel(self, text="Preview do Tema", font=("Arial", 14, "bold"))
        self.title_label.pack(pady=(10, 5))

        self.preview_container = ctk.CTkFrame(self, corner_radius=8, border_width=2)
        self.preview_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Elementos de exemplo
        self._criar_elementos_preview()
        self._criar_botoes_referencia()

    def _criar_elementos_preview(self):
        """Cria os elementos de exemplo no preview"""
        # Texto de exemplo
        self.sample_label = ctk.CTkLabel(self.preview_container, text="Texto de Exemplo", font=("Arial", 12))
        self.sample_label.pack(pady=10, padx=10)

        # Botão de exemplo
        self.sample_button = ctk.CTkButton(self.preview_container, text="Botão Secundário", font=("Arial", 11))
        self.sample_button.pack(pady=5, padx=10)

        # Campo de entrada
        self.sample_entry = ctk.CTkEntry(self.preview_container, placeholder_text="Campo de entrada",
                                         font=("Arial", 11))
        self.sample_entry.pack(pady=5, padx=10, fill="x")

        # Frame terciário
        self.tertiary_frame = ctk.CTkFrame(self.preview_container, corner_radius=6, border_width=2)
        self.tertiary_frame.pack(pady=10, padx=10, fill="x")
        self.tertiary_label = ctk.CTkLabel(self.tertiary_frame, text="Frame Terciário", font=("Arial", 10))
        self.tertiary_label.pack(pady=8)

        # Exemplo de borda
        self.border_frame = ctk.CTkFrame(self.preview_container, corner_radius=6, border_width=3)
        self.border_frame.pack(pady=5, padx=10, fill="x")
        self.border_label = ctk.CTkLabel(self.border_frame, text="Exemplo de Borda", font=("Arial", 9))
        self.border_label.pack(pady=6)

        # Botões de status
        self._criar_botoes_status()

        # Elementos interativos
        self.hover_demo_btn = ctk.CTkButton(self.preview_container, text="Passe o mouse aqui (Hover)",
                                            font=("Arial", 10), height=32)
        self.hover_demo_btn.pack(pady=5, padx=10, fill="x")

        self.selecao_demo_btn = ctk.CTkButton(self.preview_container, text="Item Selecionado/Ativo",
                                              font=("Arial", 10, "bold"), height=32)
        self.selecao_demo_btn.pack(pady=5, padx=10, fill="x")

    def _criar_botoes_status(self):
        """Cria botões de status (sucesso, alerta, destaque)"""
        btn_frame = ctk.CTkFrame(self.preview_container, fg_color="transparent")
        btn_frame.pack(pady=5, padx=10, fill="x")

        self.success_btn = ctk.CTkButton(btn_frame, text="Sucesso", width=80, height=28, font=("Arial", 10))
        self.success_btn.pack(side="left", padx=5)

        self.alert_btn = ctk.CTkButton(btn_frame, text="Alerta", width=80, height=28, font=("Arial", 10))
        self.alert_btn.pack(side="left", padx=5)

        self.highlight_btn = ctk.CTkButton(btn_frame, text="Destaque", width=80, height=28, font=("Arial", 10))
        self.highlight_btn.pack(side="left", padx=5)

    def _criar_botoes_referencia(self):
        """Cria a grade de botões de referência"""
        botoes_referencia_frame = ctk.CTkFrame(self.preview_container, fg_color="transparent")
        botoes_referencia_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(botoes_referencia_frame, text="Botões de Referência:",
                     font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 8))

        botoes_grid = ctk.CTkFrame(botoes_referencia_frame, fg_color="transparent")
        botoes_grid.pack(fill="x")

        # Configuração dos botões por linha
        linhas_botoes = [
            ["botao_salvar", "botao_excluir", "botao_novo", "botao_imprimir"],
            ["botao_pdf", "botao_editar", "botao_visualizar", "botao_confirmar"],
            ["botao_cancelar", "botao_exportar", "botao_importar", "botao_configurar"],
            ["botao_ajuda", "botao_filtrar", "botao_limpar", "botao_voltar"],
            ["botao_avancar", "botao_adiantamento", "botao_comprovante", "botao_buscar"],
            ["botao_export_csv", "botao_export_pdf"]
        ]

        # Textos dos botões
        textos_botoes = {
            "botao_salvar": "Salvar", "botao_excluir": "Excluir", "botao_novo": "Novo",
            "botao_imprimir": "Imprimir", "botao_pdf": "PDF", "botao_editar": "Editar",
            "botao_visualizar": "Visualizar", "botao_confirmar": "Confirmar",
            "botao_cancelar": "Cancelar", "botao_exportar": "Exportar",
            "botao_importar": "Importar", "botao_configurar": "Configurar",
            "botao_ajuda": "Ajuda", "botao_filtrar": "Filtrar", "botao_limpar": "Limpar",
            "botao_voltar": "Voltar", "botao_avancar": "Avançar",
            "botao_adiantamento": "Adiantamento", "botao_comprovante": "Comprovante",
            "botao_buscar": "Buscar", "botao_export_csv": "Export CSV",
            "botao_export_pdf": "Export PDF"
        }

        # Cria os botões de referência dinamicamente
        self.botoes_ref = {}
        for linha_campos in linhas_botoes:
            linha_frame = ctk.CTkFrame(botoes_grid, fg_color="transparent")
            linha_frame.pack(fill="x", pady=2)

            for campo in linha_campos:
                if campo in textos_botoes:
                    btn = ctk.CTkButton(linha_frame, text=textos_botoes[campo], width=80, height=28)
                    btn.pack(side="left", padx=2)
                    self.botoes_ref[campo] = btn

    def update_preview(self, colors):
        """Atualiza o preview com as cores fornecidas"""
        try:
            # Cores básicas
            primaria = colors.get("primaria", "#1F1F1F")
            secundaria = colors.get("secundaria", "#2C2C2C")
            terciaria = colors.get("terciaria", "#3A3A3A")
            fundo = colors.get("fundo", "#181818")
            texto = colors.get("texto", "#EEEEEE")
            destaque = colors.get("destaque", "#3A86FF")
            sucesso = colors.get("sucesso", "#3BCF8E")
            alerta = colors.get("alerta", "#EF476F")
            borda = colors.get("borda", "#333333")
            hover = colors.get("hover", "#2C2C2C")
            selecao = colors.get("selecao", destaque)

            # Atualiza elementos básicos
            self.configure(fg_color=fundo)
            self.preview_container.configure(fg_color=primaria, border_color=borda)
            self.title_label.configure(text_color=texto)
            self.sample_label.configure(text_color=texto)

            # Atualiza elementos interativos
            self._atualizar_elementos_interativos(secundaria, hover, texto, borda, selecao)

            # Atualiza botões de status
            self._atualizar_botoes_status(sucesso, alerta, destaque)

            # Atualiza botões de referência
            self._atualizar_botoes_referencia(colors)

        except Exception as e:
            print(f"Erro ao atualizar preview: {e}")

    def _atualizar_elementos_interativos(self, secundaria, hover, texto, borda, selecao):
        """Atualiza elementos interativos do preview"""
        elementos = [
            (self.sample_button, secundaria, hover, texto, borda),
            (self.sample_entry, secundaria, None, texto, borda),
            (self.tertiary_frame, None, None, None, borda),
            (self.border_frame, None, None, None, borda),
            (self.hover_demo_btn, secundaria, hover, texto, borda),
        ]

        for elemento, fg_color, hover_color, text_color, border_color in elementos:
            if elemento:
                config = {}
                if fg_color and hasattr(elemento, 'configure'):
                    config['fg_color'] = fg_color
                if hover_color and hasattr(elemento, 'configure'):
                    config['hover_color'] = hover_color
                if text_color and hasattr(elemento, 'configure'):
                    config['text_color'] = text_color
                if border_color and hasattr(elemento, 'configure'):
                    config['border_color'] = border_color

                if config:
                    elemento.configure(**config)

        # Configuração especial para o botão de seleção
        self.selecao_demo_btn.configure(
            fg_color=selecao,
            hover_color=selecao,
            text_color=self._get_contrast_color(selecao),
            border_color=borda
        )

    def _atualizar_botoes_status(self, sucesso, alerta, destaque):
        """Atualiza os botões de status"""
        self.success_btn.configure(
            fg_color=sucesso,
            hover_color=sucesso,
            text_color=self._get_contrast_color(sucesso)
        )
        self.alert_btn.configure(
            fg_color=alerta,
            hover_color=alerta,
            text_color=self._get_contrast_color(alerta)
        )
        self.highlight_btn.configure(
            fg_color=destaque,
            hover_color=destaque,
            text_color=self._get_contrast_color(destaque)
        )

    def _atualizar_botoes_referencia(self, colors):
        """Atualiza todos os botões de referência"""
        for campo, botao in self.botoes_ref.items():
            cor = colors.get(campo)
            if cor:
                botao.configure(
                    fg_color=cor,
                    hover_color=ajustar_hover(cor),
                    text_color=get_contraste_texto(cor),
                    border_color=ajustar_hover(cor, 0.7)
                )

    def _get_contrast_color(self, hex_color):
        """Calcula cor de contraste para texto"""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#000000" if luminance > 0.5 else "#FFFFFF"
        except:
            return "#FFFFFF"

    def highlight_element(self, campo):
        """Destaca um elemento específico no preview"""
        self.clear_highlight()

        element_map = {
            "primaria": [self.preview_container],
            "secundaria": [self.sample_button, self.sample_entry],
            "terciaria": [self.tertiary_frame],
            "fundo": [self],
            "texto": [self.title_label, self.sample_label, self.tertiary_label, self.border_label],
            "destaque": [self.highlight_btn],
            "sucesso": [self.success_btn],
            "alerta": [self.alert_btn],
            "borda": [self.border_frame],
            "hover": [self.hover_demo_btn],
            "selecao": [self.selecao_demo_btn],
        }

        # Adiciona mapeamento para botões de referência
        for btn_campo, botao in self.botoes_ref.items():
            element_map[btn_campo] = [botao]

        elements = element_map.get(campo)
        if not elements:
            return

        if not isinstance(elements, list):
            elements = [elements]

        for element in elements:
            try:
                if hasattr(element, 'cget'):
                    try:
                        original_border = element.cget('border_width')
                        self.original_border_widths[element] = original_border
                    except:
                        self.original_border_widths[element] = 2

                if hasattr(element, 'configure'):
                    element.configure(border_width=4, border_color="#FFD700")
            except Exception as e:
                print(f"Erro ao destacar elemento: {e}")

        self.highlighted_element = elements

    def clear_highlight(self):
        """Limpa todos os destaques"""
        if self.highlighted_element:
            for element in self.highlighted_element:
                try:
                    original_border = self.original_border_widths.get(element, 2)
                    if hasattr(element, 'configure'):
                        element.configure(border_width=original_border)
                except Exception as e:
                    print(f"Erro ao limpar destaque: {e}")

            self.highlighted_element = None
            self.original_border_widths.clear()


# =================== PÁGINA PRINCIPAL DE TEMAS (REFATORADA) ===================

class TemasPage(ctk.CTkFrame):
    """Página principal de gerenciamento de temas"""

    MAX_COLS = 3
    PADROES = ModuloPaletas()._carregar_temas_padrao()

    def __init__(self, master=None, *args, **kwargs):
        # Obtém referência da aplicação principal
        self.app = self._obter_referencia_app(kwargs)
        super().__init__(master, *args, **kwargs)

        # Inicializa módulos
        self.paletas = ModuloPaletas()
        self._inicializar_configuracoes()

        # Configura interface
        self.configure(fg_color=self.app.cor_fundo)
        self._inicializar_interface()

    def _obter_referencia_app(self, kwargs):
        """Obtém a referência da aplicação principal"""
        for key in ["sistema", "app", "controller", "ctx", "root", "main"]:
            if key in kwargs:
                return kwargs.pop(key)
        return self.winfo_toplevel()

    def _inicializar_configuracoes(self):
        """Inicializa configurações e temas"""
        # Configurações locais
        self.settings = self._carregar_settings()

        # Carrega temas personalizados
        self.paletas.carregar_temas_do_banco(self.app)
        self.paletas.garantir_padrao_botoes()

        # Remove temas excluídos
        self._remover_temas_excluidos()

        # Tema atual
        self.tema_atual = self._determinar_tema_atual()

        # Variáveis de estado
        self.campo_selecionado = None
        self.vars = {}

    def _carregar_settings(self):
        """Carrega configurações do aplicativo"""
        if hasattr(self.app, "_settings"):
            return self.app._settings
        elif hasattr(self.app, "settings"):
            return self.app.settings
        else:
            return {"theme": "Noite Urbana", "custom_themes": {}, "excluded_default_themes": []}

    def _remover_temas_excluidos(self):
        """Remove temas marcados como excluídos"""
        excluded_themes = self.settings.get("excluded_default_themes", [])
        for tema_excluido in excluded_themes:
            if tema_excluido in self.paletas.PADROES:
                del self.paletas.PADROES[tema_excluido]

    def _determinar_tema_atual(self):
        """Determina qual tema está atualmente aplicado"""
        # Tenta várias fontes para determinar o tema atual
        tema_preferencia = self._carregar_preferencia_tema_atual()
        if tema_preferencia:
            return tema_preferencia[0]

        tema_menu = getattr(self.app, "tema_atual_global", None)
        if tema_menu:
            return tema_menu

        tema_manager = getattr(self.app, "theme_manager", None)
        if tema_manager and hasattr(tema_manager, "current_theme_name"):
            return tema_manager.current_theme_name

        return "Noite Urbana"

    def _inicializar_interface(self):
        """Inicializa toda a interface da página"""
        self._build_header()

        # Layout principal
        main_layout = ctk.CTkFrame(self, fg_color="transparent")
        main_layout.pack(fill="both", expand=True, padx=5, pady=5)

        # Painéis
        left_panel = ctk.CTkFrame(main_layout, fg_color="transparent")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))

        center_panel = ctk.CTkFrame(
            main_layout,
            fg_color=self.app.cor_secundaria,
            corner_radius=10,
            border_width=2,
            border_color=self.app.cor_borda,
        )
        center_panel.pack(side="left", fill="both", padx=(0, 5))
        center_panel.configure(width=260)

        right_panel = ctk.CTkFrame(
            main_layout,
            fg_color=self.app.cor_secundaria,
            corner_radius=10,
            border_width=2,
            border_color=self.app.cor_borda,
        )
        right_panel.pack(side="left", fill="both", padx=(5, 0))
        right_panel.configure(width=360)

        # Constrói os painéis
        self._build_left_panel(left_panel)
        self._build_center_panel(center_panel)
        self._build_right_panel(right_panel)

        # Aplica tema inicial
        self._sincronizar_tema_inicial()
        self._carregar_tema_no_editor(self.tema_atual)

    def _build_header(self):
        """Constrói o cabeçalho da página"""
        header = ctk.CTkFrame(
            self,
            fg_color=self.app.cor_secundaria,
            corner_radius=12,
            border_width=1,
            border_color=self.app.cor_borda,
        )
        header.pack(fill="x", padx=5, pady=(0, 8))

        info_frame = ctk.CTkFrame(header, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="Estúdio de Temas Personalizados",
            font=("Arial", 20, "bold"),
            text_color=self.app.cor_texto,
        ).pack(anchor="w")

        resumo_temas = f"Tema atual: {self.tema_atual} • {len(self.paletas.custom)} tema(s) salvo(s)"
        ctk.CTkLabel(
            info_frame,
            text=resumo_temas,
            font=("Arial", 13),
            text_color=self.app.cor_destaque,
        ).pack(anchor="w", pady=(4, 0))

        action_frame = ctk.CTkFrame(header, fg_color="transparent")
        action_frame.pack(side="right", padx=12, pady=10)

        BotaoPadronizado.criar_botao(
            action_frame,
            text="Aplicar tema atual",
            tipo="confirmar",
            command=lambda: self._aplicar_tema_completo(self.tema_atual),
            height=36,
            corner_radius=10,
            font=("Arial", 12, "bold"),
        ).pack(side="left", padx=4)

        BotaoPadronizado.criar_botao(
            action_frame,
            text="Novo tema personalizado",
            tipo="novo",
            command=self._reset_editor_com_defaults,
            height=36,
            corner_radius=10,
            font=("Arial", 12, "bold"),
        ).pack(side="left", padx=4)

    def _build_left_panel(self, parent):
        """Constrói o painel esquerdo com lista de temas"""
        scroll_container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True)

        # Título
        title_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(title_frame, text="Gerenciar Temas", font=("Arial", 20, "bold"),
                     text_color=self.app.cor_texto).pack(side="left")

        ctk.CTkLabel(title_frame, text=f"Atual: {self.tema_atual}", font=("Arial", 14),
                     text_color=self.app.cor_destaque).pack(side="right")

        # Botão para criar novo tema
        BotaoPadronizado.criar_botao(
            title_frame,
            text="+ Novo do Atual",
            tipo="novo",
            command=self._criar_tema_da_base,
            width=120,
            height=28,
        ).pack(side="right", padx=(10, 0))

        # Bloco de Temas Padrão
        self._criar_bloco_temas(
            scroll_container,
            "Temas Padrão",
            list(self.paletas.PADROES.keys()),
            mostrar_botao_base=True
        )

        # Bloco de Temas Personalizados
        self._criar_bloco_temas(
            scroll_container,
            "Temas Personalizados",
            list(self.paletas.custom.keys()),
            mostrar_botoes_acao=True,
            is_personalizado=True
        )

    def _criar_bloco_temas(self, parent, titulo, temas, mostrar_botao_base=False,
                           mostrar_botoes_acao=False, is_personalizado=False):
        """Cria um bloco de temas (padrão ou personalizados)"""
        if not temas and is_personalizado:
            return

        bloc = ctk.CTkFrame(parent, fg_color=self.app.cor_secundaria, corner_radius=10)
        bloc.pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(bloc, text=titulo, font=("Arial", 14, "bold"),
                     text_color=self.app.cor_texto).pack(anchor="w", padx=10, pady=(10, 6))

        # Container com 3 colunas
        themes_container = ctk.CTkFrame(bloc, fg_color="transparent")
        themes_container.pack(fill="x", padx=10, pady=(0, 10))

        # Criar 3 colunas
        col_frames = []
        for i in range(3):
            col_frame = ctk.CTkFrame(themes_container, fg_color="transparent")
            col_frame.pack(side="left", fill="both", expand=True, padx=(0 if i == 0 else 5, 5 if i == 2 else 0))
            col_frames.append(col_frame)

        # Distribuir temas pelas colunas
        items_per_col = (len(temas) + 2) // 3

        for col_idx, col_frame in enumerate(col_frames):
            start_idx = col_idx * items_per_col
            end_idx = min(start_idx + items_per_col, len(temas))
            col_themes = temas[start_idx:end_idx]

            for nome in col_themes:
                self._criar_linha_tema(col_frame, nome, mostrar_botao_base,
                                       mostrar_botoes_acao, is_personalizado)

        # Botão de ação específica
        if not is_personalizado:
            BotaoPadronizado.criar_botao(
                bloc,
                text="⏱ Restaurar Temas Padrão",
                tipo="exportar",
                command=self._restaurar_temas_padrao,
                height=35,
                font=("Arial", 12, "bold"),
            ).pack(fill="x", padx=10, pady=(0, 10))

    def _criar_linha_tema(self, parent, nome, mostrar_botao_base=False,
                          mostrar_botoes_acao=False, is_personalizado=False):
        """Cria uma linha com chip e botões de ação para um tema"""
        is_active = (nome == self.tema_atual)
        fg_color = self.app.cor_destaque if is_active else self.app.cor_terciaria

        # Frame para a linha
        linha_frame = ctk.CTkFrame(parent, fg_color="transparent")
        linha_frame.pack(fill="x", pady=2)

        # Chip do tema
        chip = _Chip(
            linha_frame,
            text=nome,
            command=lambda n=nome: self._aplicar_e_carregar_tema(n),
            is_active=is_active,
            fg_color=fg_color,
            hover_color=self.app.cor_hover,
            text_color=self.app.cor_texto,
        )
        chip.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Botões de ação
        if mostrar_botao_base:
            BotaoPadronizado.criar_botao(
                linha_frame,
                text="📋",
                tipo="editar",
                command=lambda n=nome: self._carregar_tema_para_edicao(n),
                width=35,
                height=30,
                font=("Arial", 14),
            ).pack(side="right")

        if mostrar_botoes_acao:
            btn_frame = ctk.CTkFrame(linha_frame, fg_color="transparent")
            btn_frame.pack(side="right")

            # Botão Duplicar
            BotaoPadronizado.criar_botao(
                btn_frame,
                text="📋",
                tipo="editar",
                command=lambda n=nome: self._duplicar_tema_personalizado(n),
                width=30,
                height=28,
                font=("Arial", 12),
            ).pack(side="left", padx=1)

            # Botão Editar
            BotaoPadronizado.criar_botao(
                btn_frame,
                text="✏️",
                tipo="editar",
                command=lambda n=nome: self._editar_tema_personalizado(n),
                width=30,
                height=28,
                font=("Arial", 12),
            ).pack(side="left", padx=1)

            # Botão Excluir
            BotaoPadronizado.criar_botao(
                btn_frame,
                text="🗑️",
                tipo="excluir",
                command=lambda n=nome: self._excluir_tema_personalizado(n),
                width=30,
                height=28,
                font=("Arial", 12),
            ).pack(side="left", padx=1)

    def _build_center_panel(self, parent):
        """Constrói o painel central de preview"""
        self.preview_panel = PreviewPanel(parent, fg_color="transparent")
        self.preview_panel.pack(fill="both", expand=True, padx=10, pady=10)

    def _carregar_tema_para_edicao(self, nome_tema):
        """Carrega um tema para edição sem aplicá-lo"""
        print(f"📋 Carregando tema '{nome_tema}' para edição...")

        # Buscar dados do tema (padrão ou personalizado) via ModuloPaletas
        tema_data = self.paletas.obter_tema(nome_tema)

        if not tema_data:
            print(f"❌ Tema '{nome_tema}' não encontrado!")
            messagebox.showerror("Erro", f"Tema '{nome_tema}' não encontrado!")
            return

        # Carrega no editor
        self._carregar_tema_no_editor(nome_tema)

        # Sugere nome para edição
        nome_sugerido = f"{nome_tema} (Editado)"
        if hasattr(self, 'var_nome'):
            self.var_nome.set(nome_sugerido)

        # Mostra mensagem
        messagebox.showinfo(
            "Tema Carregado para Edição",
            f"O tema '{nome_tema}' foi carregado no editor à direita.\n"
            f"Agora você pode modificar as cores e salvar como um novo tema personalizado."
        )

    def _editar_tema_personalizado(self, nome_tema):
        """Edita um tema personalizado existente"""
        print(f"✏️ Editando tema personalizado '{nome_tema}'...")

        # CORREÇÃO: Usar self.paletas.custom em vez de self.custom
        if nome_tema in self.paletas.custom:
            # Carrega no editor
            self._carregar_tema_no_editor(nome_tema)

            # Define o nome atual
            if hasattr(self, 'var_nome'):
                self.var_nome.set(nome_tema)

            print(f"✅ Tema '{nome_tema}' carregado para edição")
        else:
            print(f"❌ Tema personalizado '{nome_tema}' não encontrado!")

    def _salvar_tema_personalizado_no_banco(self, nome_tema, paleta, excluir=False):
        """Salva ou exclui um tema personalizado no banco"""
        import json
        from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema

        try:
            usuario_id = getattr(self.app, "usuario_id", None)
            if not usuario_id:
                print("⚠️ Usuário sem ID, não é possível salvar/excluir tema personalizado.")
                return False

            conn = get_conn()
            if not conn:
                print("⚠️ Conexão com banco não disponível para salvar/excluir tema personalizado.")
                return False

            schema = get_schema()

            if excluir:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        DELETE FROM {schema}.usuario_temas_personalizados
                        WHERE usuario_id = %s AND nome_tema = %s
                        """,
                        (usuario_id, nome_tema),
                    )
                conn.commit()
                print(f"🗑️ Tema '{nome_tema}' excluído do banco.")
                return True
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        INSERT INTO {schema}.usuario_temas_personalizados
                            (usuario_id, nome_tema, cores_tema, atualizado_em)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (usuario_id, nome_tema)
                        DO UPDATE SET
                            cores_tema = EXCLUDED.cores_tema,
                            atualizado_em = NOW();
                        """,
                        (usuario_id, nome_tema, json.dumps(paleta, ensure_ascii=False)),
                    )
                conn.commit()
                print(f"💾 Tema '{nome_tema}' salvo no banco.")
                return True

        except Exception as e:
            print(f"❌ Erro ao {'excluir' if excluir else 'salvar'} tema '{nome_tema}': {e}")
            return False

    def _excluir_tema_personalizado(self, nome_tema):
        """Exclui um tema personalizado (da memória e do banco) e atualiza a interface"""
        print(f"🗑️ Excluindo tema personalizado '{nome_tema}'...")

        resposta = messagebox.askyesno(
            "Confirmar Exclusão",
            f"Deseja realmente excluir o tema '{nome_tema}'?\nEsta ação não pode ser desfeita."
        )

        if not resposta:
            return

        if nome_tema not in self.paletas.custom:
            self._mostrar_aviso(f"Tema personalizado '{nome_tema}' não encontrado.")
            return

        excluiu_banco = self._salvar_tema_personalizado_no_banco(
            nome_tema,
            paleta=None,
            excluir=True
        )

        if not excluiu_banco:
            messagebox.showerror(
                "Erro",
                f"Não foi possível excluir o tema '{nome_tema}' no banco de dados.\n"
                f"Verifique a conexão com o PostgreSQL."
            )
            return

        # Remove da memória
        if nome_tema in self.paletas.custom:
            del self.paletas.custom[nome_tema]

        # ATUALIZAÇÃO DIRETA DA INTERFACE
        # Busca em toda a hierarquia de widgets
        encontrado = False

        # Função auxiliar interna para busca recursiva
        def buscar_e_remover(widget):
            nonlocal encontrado
            if encontrado:
                return

            try:
                # Verifica todos os filhos diretos
                for child in widget.winfo_children():
                    try:
                        # Se é um Chip com o nome correto
                        if hasattr(child, 'label_text') and child.label_text == nome_tema:
                            # Destrói o pai (linha_frame) que contém o chip
                            if child.master and child.master.winfo_exists():
                                child.master.destroy()
                                encontrado = True
                                print(f"✅ Tema '{nome_tema}' removido da interface")
                                return

                        # Busca recursivamente nos filhos
                        if child.winfo_children():
                            buscar_e_remover(child)

                    except:
                        continue
            except:
                pass

        # Começa a busca a partir do widget principal
        buscar_e_remover(self)

        # Se não encontrou, força recarga do painel esquerdo
        if not encontrado:
            print(f"⚠️ Não encontrou widget, reconstruindo painel...")
            # Encontra e reconstrói apenas o painel esquerdo
            for widget in self.winfo_children():
                if isinstance(widget, ctk.CTkFrame) and len(widget.winfo_children()) > 0:
                    left_panel = None
                    for child in widget.winfo_children():
                        if isinstance(child, ctk.CTkFrame) and "transparent" in str(child.cget("fg_color")):
                            left_panel = child
                            break

                    if left_panel:
                        # Salva o tema atual no editor
                        tema_editor = None
                        if hasattr(self, 'var_nome'):
                            tema_editor = self.var_nome.get()

                        # Destrói e reconstrói o painel esquerdo
                        left_panel.destroy()
                        self._build_left_panel(widget)

                        # Restaura o tema no editor se necessário
                        if tema_editor and hasattr(self, 'var_nome'):
                            self.var_nome.set(tema_editor)
                        break

        # Se estava editando o tema excluído, reseta o editor
        if hasattr(self, 'var_nome') and self.var_nome.get() == nome_tema:
            self._reset_editor_com_defaults()

        print(f"✅ Tema '{nome_tema}' excluído com sucesso!")
        messagebox.showinfo("Sucesso", f"Tema '{nome_tema}' excluído!")

    def _criar_tema_da_base(self):
        """Cria novo tema baseado no tema atualmente aplicado"""
        print("➕ Criando novo tema a partir do atual...")

        if hasattr(self.app, 'tema_atual'):
            tema_atual_nome = self.app.tema_atual
            self._carregar_tema_no_editor(tema_atual_nome)
            nome_sugerido = f"{tema_atual_nome} (Cópia)"
            if hasattr(self, 'var_nome'):
                self.var_nome.set(nome_sugerido)
        else:
            print("⚠️ Nenhum tema está aplicado no momento.")
            messagebox.showinfo("Informação", "Nenhum tema está aplicado no momento.")

    def _restaurar_temas_padrao(self):
        """Versão simples sem erro de chips_padrao"""
        resposta = messagebox.askyesno(
            "Restaurar Temas Padrão",
            "Esta ação irá recarregar os temas padrão. Continuar?"
        )

        if resposta:
            # Simplesmente recarregar a página
            if hasattr(self.app, 'abrir_pagina'):
                self.app.abrir_pagina("Temas")
            messagebox.showinfo("Sucesso", "Temas padrão restaurados!")

    def _aplicar_e_carregar_tema(self, nome):
        """Aplica um tema e o carrega no editor"""
        if hasattr(self, '_aplicar_tema_completo'):
            self._aplicar_tema_completo(nome)
        if hasattr(self, '_carregar_tema_no_editor'):
            self._carregar_tema_no_editor(nome)

    def _criar_bloco_temas_padrao(self, parent):
        """Cria o bloco de temas padrão"""
        bloc1 = ctk.CTkFrame(parent, fg_color=self.app.cor_secundaria, corner_radius=10)
        bloc1.pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(bloc1, text="Temas Padrão", font=("Arial", 14, "bold"),
                     text_color=self.app.cor_texto).pack(anchor="w", padx=10, pady=(10, 6))

        # Container com 3 colunas
        themes_container = ctk.CTkFrame(bloc1, fg_color="transparent")
        themes_container.pack(fill="x", padx=10, pady=(0, 10))

        # Criar 3 colunas
        col_frames = []
        for i in range(3):
            padx_left = 0 if i == 0 else 5
            padx_right = 5 if i == 2 else 0
            col_frame = ctk.CTkFrame(themes_container, fg_color="transparent")
            col_frame.pack(side="left", fill="both", expand=True, padx=(padx_left, padx_right))
            col_frames.append(col_frame)

        # Obter TODOS os temas padrão
        theme_names = list(self.PADROES.keys())
        items_per_col = (len(theme_names) + 2) // 3  # Dividir em 3 colunas

        # Distribuir temas pelas colunas
        for col_idx, col_frame in enumerate(col_frames):
            start_idx = col_idx * items_per_col
            end_idx = min(start_idx + items_per_col, len(theme_names))
            col_themes = theme_names[start_idx:end_idx]

            for nome in col_themes:
                self._criar_linha_tema_padrao(col_frame, nome)

        # Botão para restaurar temas padrão
        restore_btn = ctk.CTkButton(bloc1, text="⏱ Restaurar Temas Padrão",
                                    fg_color="#3498db", hover_color="#2980b9",
                                    font=("Arial", 12, "bold"), height=35,
                                    command=self._restaurar_temas_padrao)
        restore_btn.pack(fill="x", padx=10, pady=(0, 10))

    def _criar_bloco_temas_personalizados(self, parent):
        """Cria o bloco de temas personalizados"""
        bloc2 = ctk.CTkFrame(parent, fg_color=self.app.cor_secundaria, corner_radius=10)
        bloc2.pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(bloc2, text="Temas Personalizados", font=("Arial", 14, "bold"),
                     text_color=self.app.cor_texto).pack(anchor="w", padx=10, pady=(10, 6))

        custom_container = ctk.CTkFrame(bloc2, fg_color="transparent")
        custom_container.pack(fill="x", padx=10, pady=(0, 10))

        # Verificar temas personalizados
        custom_names = list(self.custom.keys()) if hasattr(self, 'custom') else []

        if custom_names:
            # Criar 3 colunas para personalizados também
            custom_col1 = ctk.CTkFrame(custom_container, fg_color="transparent")
            custom_col1.pack(side="left", fill="both", expand=True, padx=(0, 5))

            custom_col2 = ctk.CTkFrame(custom_container, fg_color="transparent")
            custom_col2.pack(side="left", fill="both", expand=True, padx=5)

            custom_col3 = ctk.CTkFrame(custom_container, fg_color="transparent")
            custom_col3.pack(side="left", fill="both", expand=True, padx=(5, 0))

            items_per_custom_col = (len(custom_names) + 2) // 3

            for col_idx, col_frame in enumerate([custom_col1, custom_col2, custom_col3]):
                start_idx = col_idx * items_per_custom_col
                end_idx = min(start_idx + items_per_custom_col, len(custom_names))
                col_custom_themes = custom_names[start_idx:end_idx]

                for nome in col_custom_themes:
                    self._criar_linha_tema_personalizado(col_frame, nome)
        else:
            ctk.CTkLabel(
                custom_container,
                text="Nenhum tema personalizado criado ainda.",
                font=("Arial", 11, "italic"),
                text_color=self.app.cor_texto
            ).pack(pady=20)

    def _criar_linha_tema_padrao(self, parent, nome_tema):
        """Cria uma linha para tema padrão"""
        is_active = (nome_tema == self.tema_atual)
        fg_color = self.app.cor_destaque if is_active else self.app.cor_terciaria

        # Frame para a linha
        linha_frame = ctk.CTkFrame(parent, fg_color="transparent")
        linha_frame.pack(fill="x", pady=2)

        # Chip do tema
        chip = _Chip(
            linha_frame,
            text=nome_tema,
            command=lambda n=nome_tema: self._aplicar_e_carregar_tema(n),
            is_active=is_active,
            fg_color=fg_color,
            hover_color=self.app.cor_hover,
            text_color=self.app.cor_texto,
        )
        chip.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Botão "Usar como base" - FUNCIONAL
        base_btn = ctk.CTkButton(
            linha_frame,
            text="📋",
            width=35,
            height=30,
            fg_color="#f39c12",
            hover_color="#e67e22",
            font=("Arial", 14),
            corner_radius=6,
            command=lambda n=nome_tema: self._carregar_tema_para_edicao(n)
        )
        base_btn.pack(side="right")

    def _criar_linha_tema_personalizado(self, parent, nome_tema):
        """Cria uma linha para tema personalizado"""
        is_active = (nome_tema == self.tema_atual)
        fg_color = self.app.cor_destaque if is_active else self.app.cor_terciaria

        linha_frame = ctk.CTkFrame(parent, fg_color="transparent")
        linha_frame.pack(fill="x", pady=2)

        # Chip
        chip = _Chip(
            linha_frame,
            text=nome_tema,
            command=lambda n=nome_tema: self._aplicar_e_carregar_tema(n),
            is_active=is_active,
            fg_color=fg_color,
            hover_color=self.app.cor_hover,
            text_color=self.app.cor_texto,
        )
        chip.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Botões à direita
        btn_frame = ctk.CTkFrame(linha_frame, fg_color="transparent")
        btn_frame.pack(side="right")

        # Botão Duplicar
        dup_btn = ctk.CTkButton(
            btn_frame,
            text="📋",
            width=30,
            height=28,
            fg_color="#3498db",
            hover_color="#2980b9",
            font=("Arial", 12),
            corner_radius=6,
            command=lambda n=nome_tema: self._duplicar_tema_personalizado(n)
        )
        dup_btn.pack(side="left", padx=1)

        # Botão Editar
        edit_btn = ctk.CTkButton(
            btn_frame,
            text="✏️",
            width=30,
            height=28,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            font=("Arial", 12),
            corner_radius=6,
            command=lambda n=nome_tema: self._editar_tema_personalizado(n)
        )
        edit_btn.pack(side="left", padx=1)

        # Botão Excluir
        del_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️",
            width=30,
            height=28,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            font=("Arial", 12),
            corner_radius=6,
            command=lambda n=nome_tema: self._excluir_tema_personalizado(n)
        )
        del_btn.pack(side="left", padx=1)

    # =================== FUNÇÕES AUXILIARES PARA OS BOTÕES ===================



    def _build_right_panel(self, parent):
        """Constrói o painel direito de edição"""
        # Título
        ctk.CTkLabel(parent, text="Editor de Tema", font=("Arial", 16, "bold"),
                     text_color=self.app.cor_texto).pack(pady=(15, 10), padx=10)

        # Área de rolagem para campos
        scroll_editor = ctk.CTkScrollableFrame(parent, fg_color="transparent", height=300)
        scroll_editor.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Cria campos de edição
        self._criar_campos_edicao(scroll_editor)

        # Separador
        separator = ctk.CTkFrame(parent, fg_color=self.app.cor_borda, height=2)
        separator.pack(fill="x", padx=10, pady=8)

        # Seletor de cores
        ctk.CTkLabel(parent, text="Seletor de Cores", font=("Arial", 13, "bold"),
                     text_color=self.app.cor_texto).pack(pady=(5, 5))

        self.color_picker = ColorPickerWidget(parent, fg_color=self.app.cor_fundo, corner_radius=6,
                                              callback=self._on_color_selected)
        self.color_picker.pack(fill="x", padx=10, pady=(0, 10))

        # Campo de nome do tema
        self._criar_campo_nome(parent)

        # Botões de ação
        self._criar_botoes_acao(parent)

    def _criar_campos_edicao(self, parent):
        """Cria os campos de edição de cores"""
        for campo in self.paletas.CAMPOS_PADRAO:
            campo_frame = ctk.CTkFrame(parent, fg_color=self.app.cor_terciaria,
                                       corner_radius=6, border_width=1,
                                       border_color=self.app.cor_borda)
            campo_frame.pack(fill="x", pady=5)

            # Label
            label = ctk.CTkLabel(campo_frame, text=self.paletas.LABELS_CAMPOS_PADRAO[campo],
                                 font=("Arial", 11, "bold"), text_color=self.app.cor_texto, anchor="w")
            label.pack(fill="x", padx=10, pady=(8, 4))

            # Controles
            controls_frame = ctk.CTkFrame(campo_frame, fg_color="transparent")
            controls_frame.pack(fill="x", padx=10, pady=(0, 8))

            # Campo de entrada
            var = tk.StringVar(value="#FFFFFF")
            self.vars[campo] = var
            var.trace_add("write", lambda *args: self._update_live_preview())

            entry = ctk.CTkEntry(controls_frame, textvariable=var, font=("Arial", 11), height=32)
            entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

            # Botão de cor
            self._criar_botao_cor(controls_frame, campo, var)

            # Bind para highlight
            self._configurar_bind_highlight(campo_frame, label, entry, campo)

    def _criar_botao_cor(self, parent, campo, var):
        """Cria botão de seleção de cor"""

        def criar_btn():
            return BotaoPadronizado.criar_botao(
                parent,
                text="🎨",
                tipo="editar",
                command=lambda: self._abrir_seletor_cor(campo),
                width=100,
                height=32,
                corner_radius=6,
                font=("Arial", 14),
            )

        color_btn = criar_btn()
        color_btn.pack(side="left")

        # Atualiza cor do botão quando a variável muda
        def update_btn(*args, btn=color_btn):
            color = var.get()
            if not _valida_hex(color):
                return

            try:
                if hasattr(btn, "winfo_exists") and btn.winfo_exists():
                    btn.configure(
                        fg_color=color,
                        hover_color=color,
                        text_color=get_contraste_texto(color),
                    )
            except (tk.TclError, Exception):
                pass

        var.trace_add("write", update_btn)

        # Bind para highlight
        color_btn.bind("<Enter>", lambda e, c=campo: self._safe_preview_highlight(c))
        color_btn.bind("<Leave>", lambda e: self._safe_preview_leave())

    def _configurar_bind_highlight(self, frame, label, entry, campo):
        """Configura binds para highlight no preview"""

        def on_enter(event):
            self.preview_panel.highlight_element(campo)

        def on_leave(event):
            self.preview_panel.clear_highlight()
            self._update_live_preview()

        for widget in [frame, label, entry]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def _criar_campo_nome(self, parent):
        """Cria campo para nome do tema"""
        nome_frame = ctk.CTkFrame(parent, fg_color="transparent")
        nome_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(nome_frame, text="Nome do Tema:", font=("Arial", 11, "bold"),
                     text_color=self.app.cor_texto).pack(anchor="w")

        self.var_nome = tk.StringVar(value="")
        ctk.CTkEntry(nome_frame, textvariable=self.var_nome, font=("Arial", 11),
                     height=32).pack(fill="x", pady=(4, 0))

    def _criar_botoes_acao(self, parent):
        """Cria botões de ação principais"""
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(5, 15))

        BotaoPadronizado.criar_botao(
            btn_frame,
            text="💾 Salvar Tema",
            tipo="salvar",
            command=self._salvar_custom_completo,
            height=38,
            font=("Arial", 12, "bold"),
        ).pack(fill="x", pady=3)

        BotaoPadronizado.criar_botao(
            btn_frame,
            text="🔄 Restaurar Original",
            tipo="excluir",
            command=self._restaurar_tema,
            height=38,
            font=("Arial", 12, "bold"),
        ).pack(fill="x", pady=3)

    # =================== MÉTODOS DE AÇÃO ===================

    def _reset_editor_com_defaults(self):
        """Prepara o editor com valores padrão"""
        base_tema = self.tema_atual if self.tema_atual in self.paletas.PADROES else "Noite Urbana"
        nome_sugestao = f"{base_tema} Personalizado"
        self.var_nome.set(nome_sugestao)
        self._carregar_tema_no_editor(base_tema)

    def _restaurar_tema(self):
        """Restaura um tema para suas configurações originais"""
        nome = (self.var_nome.get() or "").strip()
        if not nome:
            self._mostrar_aviso("Informe o nome do tema no campo 'Nome do Tema'.")
            return

        if nome not in self.paletas.temas_originais:
            self._mostrar_aviso(f"'{nome}' não é um tema padrão.")
            return

        # Restaura tema original
        tema_original = self.paletas.temas_originais[nome]
        self.paletas.PADROES[nome] = dict(tema_original)
        self._carregar_tema_no_editor(nome)
        self._aplicar_tema_completo(nome)
        self._mostrar_info("Sucesso", f"Tema '{nome}' restaurado para as configurações originais.")

    def _salvar_custom_completo(self):
        """Salva um tema personalizado completo"""
        nome = (self.var_nome.get() or "").strip()
        if not nome:
            self._mostrar_aviso("Informe um nome para o tema.")
            return

        # Monta paleta
        pal = {}
        for campo, var in self.vars.items():
            val = (var.get() or "").strip()
            if not _valida_hex(val):
                self._mostrar_aviso(f"Cor inválida: {val}")
                return
            pal[campo] = val.upper()

        # Salva localmente
        self.paletas.custom[nome] = pal

        # Salva no banco
        salvou_no_banco = self._salvar_tema_personalizado_no_banco(nome, pal)

        # Mensagem de sucesso
        if salvou_no_banco:
            self._mostrar_info("Sucesso", f"Tema '{nome}' salvo no banco e localmente!")
        else:
            self._mostrar_aviso(f"Tema '{nome}' salvo localmente, mas não foi possível salvar no banco.")

        # Aplica o tema
        self._aplicar_tema_completo(nome)

    def carregar_temas_do_banco(self, app):
        """Carrega temas personalizados do banco de dados"""
        import json
        try:
            usuario_id = getattr(app, "usuario_id", None)
            if not usuario_id:
                print("⚠️ Nenhum usuário definido para carregar temas personalizados.")
                return False

            from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema
            conn = get_conn()
            if not conn:
                print("⚠️ Conexão com banco não disponível para carregar temas personalizados.")
                return False

            schema = get_schema()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT nome_tema, cores_tema
                        FROM {schema}.usuario_temas_personalizados
                        WHERE usuario_id = %s
                        ORDER BY nome_tema
                        """,
                        (usuario_id,),
                    )
                    rows = cur.fetchall() or []

            carregados = 0
            for nome_tema, cores_tema in rows:
                try:
                    if isinstance(cores_tema, dict):
                        tema_data = cores_tema
                    else:
                        tema_data = json.loads(cores_tema) if cores_tema else {}

                    if isinstance(tema_data, dict):
                        # CORREÇÃO: Garantir que está salvando em self.custom
                        self.custom[nome_tema] = tema_data
                        carregados += 1
                except Exception as erro_tema:
                    print(f"⚠️ Erro ao processar tema '{nome_tema}' do banco: {erro_tema}")

            print(f"🎨 Temas personalizados carregados do banco: {carregados}")
            return True

        except Exception as erro:
            print(f"❌ Erro ao carregar temas personalizados do banco: {erro}")
            return False

    def _duplicar_tema_personalizado(self, nome_tema):
        """Duplica um tema personalizado existente"""
        print(f"📋 Duplicando tema personalizado '{nome_tema}'...")

        # CORREÇÃO: Usar self.paletas.custom em vez de self.custom
        if nome_tema in self.paletas.custom:
            # Carrega no editor
            self._carregar_tema_no_editor(nome_tema)

            # Sugere nome
            nome_sugerido = f"{nome_tema} (Cópia)"
            if hasattr(self, 'var_nome'):
                self.var_nome.set(nome_sugerido)

            print(f"✅ Tema '{nome_tema}' duplicado para edição")
        else:
            print(f"❌ Tema personalizado '{nome_tema}' não encontrado!")
            self._mostrar_aviso(f"Tema personalizado '{nome_tema}' não encontrado.")

    # ---------------------------------------------------------
    # CORREÇÃO GLOBAL DE BORDAS NO SISTEMA OPERA
    # ---------------------------------------------------------

    def _aplicar_tema_completo(self, nome_tema):
        """
        Aplica um tema em toda a aplicação, usando o ThemeManager se existir,
        e depois limpa bordas/fundos indesejados em labels e botões de tema.
        """
        try:
            tema = self.paletas.obter_tema(nome_tema)
            if not tema:
                print(f"⚠️ Tema '{nome_tema}' não encontrado.")
                return False

            # Atualiza o preview da própria página de temas
            try:
                self._update_live_preview()
            except Exception as e:
                print(f"[AVISO] Falha ao atualizar preview: {e}")

            # Aplica via ThemeManager, se disponível
            theme_manager = getattr(self.app, "theme_manager", None)
            if theme_manager:
                theme_manager.apply_theme(nome_tema, tema)
                print(f"✅ Tema aplicado via ThemeManager: {nome_tema}")
            else:
                # Fallback: apenas registra as cores no objeto app
                for campo, valor in tema.items():
                    setattr(self.app, f"cor_{campo}", valor)

            # 🔧 LIMPEZA VISUAL: remove contorno de textos e botões de tema
            try:
                corrigir_bordas_labels(self.app)
            except Exception as e:
                print(f"[AVISO] Erro ao corrigir bordas de labels: {e}")

            try:
                remover_bordas_botoes_tema(self.app)
            except Exception as e:
                print(f"[AVISO] Erro ao ajustar botões de tema: {e}")

            # Atualiza estado interno
            self.tema_atual = nome_tema
            self.app.tema_atual = nome_tema

            # Salva preferência (padrão ou personalizado)
            is_custom = nome_tema in self.paletas.custom
            paleta_custom = self.paletas.custom.get(nome_tema) if is_custom else None
            self._persistir_preferencia_usuario(
                nome_tema,
                paleta_custom
            )

            print(f"🎉 Tema '{nome_tema}' aplicado completamente")
            return True

        except Exception as e:
            print(f"❌ Erro ao aplicar tema '{nome_tema}': {e}")
            return False

            # 🔧 ADICIONE ESTAS LINHAS NO FINAL DO MÉTODO:
            # Aplica correção imediatamente após trocar tema
            self.after(100, lambda: corrigir_labels_pagina_temas(self))

            # Atualiza estado interno
            self.tema_atual = nome_tema
            self.app.tema_atual = nome_tema

            print(f"🎉 Tema '{nome_tema}' aplicado completamente")
            return True

        except Exception as e:
            print(f"❌ Erro ao aplicar tema '{nome_tema}': {e}")
            return False

    def corrigir_bordas_labels(widget):
        """
        Remove qualquer borda, raio ou cor de fundo que possa deixar os textos
        com um quadrado em volta (para CTkLabel).
        """
        import customtkinter as ctk

        try:
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(
                    fg_color="transparent",
                    border_width=0,
                    corner_radius=0
                )

            for child in widget.winfo_children():
                corrigir_bordas_labels(child)

        except Exception as e:
            print(f"[ERRO corrigir_bordas_labels] {e}")

    def atualizar_cores_widgets(self, widget, tema):
        import customtkinter as ctk

        try:
            # LABEL
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(
                    text_color=tema["texto"],
                    fg_color="transparent",
                    border_width=0,
                    corner_radius=0
                )

            # BOTÃO
            elif isinstance(widget, ctk.CTkButton):
                widget.configure(
                    fg_color=tema["secundaria"],
                    hover_color=tema["hover"],
                    text_color=tema["texto"],
                    border_color=tema["borda"],
                    border_width=1
                )

            # ENTRADA
            elif isinstance(widget, ctk.CTkEntry):
                widget.configure(
                    fg_color=tema["primaria"],
                    text_color=tema["texto"],
                    border_color=tema["borda"]
                )

            # FRAME
            elif isinstance(widget, ctk.CTkFrame):
                widget.configure(
                    fg_color=tema["primaria"],
                    border_color=tema["borda"]
                )

            # RECURSÃO
            for child in widget.winfo_children():
                self.atualizar_cores_widgets(child, tema)

        except Exception as e:
            print(f"[ERRO atualizar_cores_widgets] {e}")

    def _criar_elementos_preview(self):
        """Cria os elementos de exemplo no preview SEM bordas indesejadas."""
        self.sample_label = ctk.CTkLabel(self.preview_container, text="Texto de Exemplo",
                                         font=("Arial", 12), border_width=0,
                                         corner_radius=0, fg_color="transparent")
        self.sample_label.pack(pady=10, padx=10)

        self.sample_button = ctk.CTkButton(self.preview_container, text="Botão Secundário",
                                           font=("Arial", 11))
        self.sample_button.pack(pady=5, padx=10)

        self.sample_entry = ctk.CTkEntry(self.preview_container,
                                         placeholder_text="Campo de entrada",
                                         font=("Arial", 11))
        self.sample_entry.pack(pady=5, padx=10, fill="x")

        self.tertiary_frame = ctk.CTkFrame(self.preview_container,
                                           corner_radius=6, border_width=2)
        self.tertiary_frame.pack(pady=10, padx=10, fill="x")

        self.tertiary_label = ctk.CTkLabel(self.tertiary_frame, text="Frame Terciário",
                                           font=("Arial", 10),
                                           border_width=0, corner_radius=0,
                                           fg_color="transparent")
        self.tertiary_label.pack(pady=8)

        self.border_frame = ctk.CTkFrame(self.preview_container,
                                         corner_radius=6, border_width=3)
        self.border_frame.pack(pady=5, padx=10, fill="x")

        self.border_label = ctk.CTkLabel(self.border_frame, text="Exemplo de Borda",
                                         font=("Arial", 9),
                                         border_width=0, corner_radius=0,
                                         fg_color="transparent")
        self.border_label.pack(pady=6)

        self._criar_botoes_status()

    def _abrir_seletor_cor(self, campo):
        """Abre seletor de cor para um campo específico"""
        self.campo_selecionado = campo
        cor_atual = self.vars[campo].get()
        if _valida_hex(cor_atual) and hasattr(self, "color_picker"):
            self.color_picker.set_color(cor_atual)

    def _on_color_selected(self, color):
        if self.campo_selecionado:
            self.vars[self.campo_selecionado].set(color)

    def _update_live_preview(self):
        """Atualiza o preview em tempo real"""
        if hasattr(self, 'preview_panel') and self.preview_panel.winfo_exists():
            colors = {}
            for campo, var in self.vars.items():
                val = var.get()
                if _valida_hex(val):
                    colors[campo] = val
                else:
                    colors[campo] = "#FFFFFF"

            try:
                self.preview_panel.update_preview(colors)
            except Exception as e:
                print(f"Erro ao atualizar preview: {e}")

    def _safe_preview_highlight(self, campo):
        """Destaca elemento no preview de forma segura"""
        if hasattr(self, 'preview_panel') and self.preview_panel.winfo_exists():
            try:
                self.preview_panel.highlight_element(campo)
            except Exception:
                pass

    def _safe_preview_leave(self):
        """Limpa destaque do preview de forma segura"""
        if hasattr(self, 'preview_panel') and self.preview_panel.winfo_exists():
            try:
                self.preview_panel.clear_highlight()
                self._update_live_preview()
            except Exception:
                pass

    def _sincronizar_tema_inicial(self):
        """Sincroniza com o tema atual do sistema"""
        tema_atual = getattr(self.app, "tema_atual", None)
        if tema_atual:
            self.tema_atual = tema_atual

    def _carregar_tema_no_editor(self, nome_tema):
        """Carrega as cores de um tema (padrão ou personalizado) nos campos do editor e no preview"""
        try:
            tema = self.paletas.obter_tema(nome_tema)
            if not tema:
                self._mostrar_aviso(f"Tema '{nome_tema}' não encontrado.")
                return

            # Atualiza os campos de texto do editor
            for campo in self.paletas.CAMPOS_PADRAO:
                valor = tema.get(campo, "#FFFFFF")
                if campo in self.vars:
                    try:
                        self.vars[campo].set(valor.upper())
                    except Exception:
                        self.vars[campo].set(valor)

            # Atualiza o nome do tema no campo de nome, se existir
            if hasattr(self, "var_nome") and self.var_nome is not None:
                # Quando estiver editando um tema existente, deixo o nome igual ao tema
                if not self.var_nome.get().strip():
                    self.var_nome.set(nome_tema)

            # Atualiza o preview
            if hasattr(self, "preview_panel") and self.preview_panel.winfo_exists():
                try:
                    self.preview_panel.update_preview(tema)
                except Exception as e:
                    print(f"Erro ao atualizar preview para o tema '{nome_tema}': {e}")

            # Atualiza referência de tema atual carregado no editor
            self.tema_atual = nome_tema

        except Exception as e:
            print(f"❌ Erro ao carregar tema no editor: {e}")
            self._mostrar_erro(f"Falha ao carregar o tema '{nome_tema}' no editor.\n\n{e}")

            # Atualiza referência de tema atual carregado no editor
            self.tema_atual = nome_tema

            # 🔧 ADICIONE ESTAS LINHAS:
            # Aplica correção após carregar tema no editor
            self.after(100, lambda: corrigir_labels_pagina_temas(self))

            # Correção específica para o preview
            if hasattr(self, 'preview_panel') and self.preview_panel.winfo_exists():
                corrigir_labels_pagina_temas(self.preview_panel)

        except Exception as e:
            print(f"❌ Erro ao carregar tema no editor: {e}")
            self._mostrar_erro(f"Falha ao carregar o tema '{nome_tema}' no editor.\n\n{e}")


    def _carregar_preferencia_tema_atual(self):
        """Carrega preferência de tema do banco"""
        try:
            from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema

            usuario_id = getattr(self.app, 'usuario_id', None)
            if not usuario_id:
                print("[Tema][DEBUG] Usuário não definido ao carregar preferência; retornando None")
                return None

            schema = get_schema()
            conn = get_conn()

            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT tema_nome, COALESCE(usar_tema_personalizado, FALSE)
                    FROM {schema}.usuario_preferencias
                    WHERE usuario_id = %s
                    """,
                    (usuario_id,)
                )
                resultado = cur.fetchone()

                if resultado:
                    tema_nome, usar_personalizado = resultado
                    tipo_tema = "personalizado" if usar_personalizado else "padrao"
                    print(f"[Tema][DEBUG] Preferência encontrada para usuário {usuario_id}: {tema_nome} (tipo: {tipo_tema})")
                    return tema_nome, tipo_tema

                print(f"[Tema][DEBUG] Nenhuma preferência encontrada para usuário {usuario_id}; usando padrão")

            return None

        except Exception as e:
            print(f"❌ Erro ao carregar preferência de tema: {e}")
            return None

    def _salvar_preferencia_tema_atual(self, nome_tema, tipo_tema, paleta_custom=None):
        """Salva preferência de tema no banco"""
        try:
            from PAGINAS_DO_SISTEMA.BANCO_DE_DADOS_PG import get_conn, get_schema

            usuario_id = getattr(self.app, 'usuario_id', None)
            if not usuario_id:
                return False

            usar_tema_personalizado = tipo_tema == "personalizado"
            paleta_json = None
            if usar_tema_personalizado and paleta_custom:
                try:
                    paleta_json = json.dumps(paleta_custom)
                except Exception:
                    paleta_json = None
            print(
                f"[Tema][DEBUG] Salvando preferência (user={usuario_id}, tipo={tipo_tema}, tema={nome_tema}, "
                f"paleta={'sim' if paleta_json else 'não'}) no schema {schema}"
            )
            schema = get_schema()
            conn = get_conn()

            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {schema}.usuario_preferencias
                        (usuario_id, tema_nome, usar_tema_personalizado, tema_personalizado, atualizado_em)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (usuario_id) DO UPDATE SET
                        tema_nome = EXCLUDED.tema_nome,
                        usar_tema_personalizado = EXCLUDED.usar_tema_personalizado,
                        tema_personalizado = EXCLUDED.tema_personalizado,
                        atualizado_em = NOW()
                    """,
                    (usuario_id, nome_tema, usar_tema_personalizado, paleta_json)
                )
            conn.commit()

            print(
                f"✅ Preferência de tema salva: {nome_tema} | usuario_id={usuario_id} | "
                f"personalizado={'sim' if usar_tema_personalizado else 'não'}"
            )
            return True

        except Exception as e:
            print(f"❌ Erro ao salvar preferência de tema: {e}")
            return False

    def _persistir_preferencia_usuario(self, nome_tema, paleta_custom=None):
        """Garante que o tema aplicado seja gravado na preferência do usuário."""
        try:
            usuario_id = getattr(self.app, "usuario_id", None)
            if not usuario_id:
                print("[Temas][DEBUG] Nenhum usuário ativo ao persistir preferência; abortando")
                return False

            # Tenta salvar via UserManager (preferido)
            try:
                user_manager = getattr(self.app, "user_manager", None)
                if user_manager:
                    print(
                        f"[Temas][DEBUG] Persistindo preferência via UserManager para usuario_id={usuario_id} | "
                        f"tema={nome_tema} | paleta_custom={'sim' if paleta_custom else 'não'}"
                    )
                    if paleta_custom:
                        import json
                        user_manager.save_user_theme_personalizado(nome_tema, json.dumps(paleta_custom))
                    else:
                        user_manager.save_user_theme(nome_tema)

                    # Atualiza fallbacks locais para futuros logins
                    if hasattr(self.app, "tema_preferido_inicial"):
                        self.app.tema_preferido_inicial = nome_tema
                    if hasattr(self.app, "current_theme_name"):
                        self.app.current_theme_name = nome_tema
                    print(f"[Temas][DEBUG] Preferência registrada via UserManager para usuario_id={usuario_id}")
                    return True
                else:
                    print("[Temas][DEBUG] UserManager não disponível; usando fallback direto no banco")
            except Exception as e_user_manager:
                print(f"[Temas] Aviso: não foi possível salvar via UserManager ({e_user_manager}).")

            # Fallback direto no banco (mantém comportamento anterior)
            tipo = "personalizado" if paleta_custom else "padrao"
            sucesso = self._salvar_preferencia_tema_atual(nome_tema, tipo, paleta_custom)

            # Atualiza fallbacks locais mesmo quando usa o caminho direto
            if sucesso and hasattr(self.app, "tema_preferido_inicial"):
                self.app.tema_preferido_inicial = nome_tema
            if sucesso and hasattr(self.app, "current_theme_name"):
                self.app.current_theme_name = nome_tema
            print(
                f"[Temas][DEBUG] Persistência direta no banco {'ok' if sucesso else 'falhou'} para usuario_id={usuario_id}"
            )
            return sucesso

        except Exception as e:
            print(f"[Temas] Erro ao persistir preferência do usuário: {e}")
            return False

    def _mostrar_info(self, titulo, mensagem):
        """Mostra mensagem informativa"""
        if MESSAGEBOX_AVAILABLE:
            CTkMessagebox(title=titulo, message=mensagem, icon="info")
        else:
            messagebox.showinfo(titulo, mensagem)

    def _mostrar_aviso(self, mensagem):
        """Mostra mensagem de aviso"""
        if MESSAGEBOX_AVAILABLE:
            CTkMessagebox(title="Atenção", message=mensagem, icon="warning")
        else:
            messagebox.showwarning("Atenção", mensagem)

    def _mostrar_erro(self, mensagem):
        """Mostra mensagem de erro"""
        if MESSAGEBOX_AVAILABLE:
            CTkMessagebox(title="Erro", message=mensagem, icon="cancel")
        else:
            messagebox.showerror("Erro", mensagem)


# =================== PONTO DE ENTRADA ===================

# =================== PONTO DE ENTRADA ===================

if __name__ == '__main__':
    """
    MODO DEMONSTRAÇÃO - Executa a página de temas como aplicação standalone
    """
    print("🚀 INICIANDO SISTEMA DE TEMAS...")

    # Configuração básica
    ctk.set_appearance_mode('dark')
    app = ctk.CTk()
    app.title('Sistema de Temas - Opera')

    # Configurações de demonstração
    app._settings = {
        "theme": "Noite Urbana",
        "custom_themes": {},
        "excluded_default_themes": []
    }

    # Usa a própria classe ModuloPaletas definida neste arquivo
    paletas = ModuloPaletas()

    # Tenta usar "Noite Urbana"; se não existir, usa o primeiro tema disponível
    tema_base = paletas.PADROES.get("Noite Urbana")
    if tema_base is None:
        # Garante que sempre tenha alguma coisa pra usar
        tema_base = next(iter(paletas.PADROES.values()))

    # Injeta as cores como atributos da app (cor_primaria, cor_secundaria, etc.)
    for k, v in tema_base.items():
        setattr(app, f'cor_{k}', v)

    # Simula usuário/logado
    app.usuario_id = 1
    app.tema_atual = "Noite Urbana"

    # Se tiver um theme_manager no seu sistema real, aqui no demo ele não existe
    app.theme_manager = None

    # Cria e exibe a página
    try:
        # IMPORTANTE: passar app=app para TemasPage pegar a referência certa
        page = TemasPage(app, app=app)
        page.pack(fill='both', expand=True, padx=20, pady=20)

        # Configura janela
        app.geometry('1400x800')
        app.minsize(1200, 700)

        # Informações de status
        status_frame = ctk.CTkFrame(app, fg_color="transparent")
        status_frame.pack(side="bottom", fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            status_frame,
            text="🔧 Modo Demonstração - Sistema de Temas Opera",
            font=("Arial", 10),
            text_color="#888888"
        ).pack(side="left")

        print("\n" + "=" * 60)
        print("🎭 SISTEMA DE TEMAS OPERA - MODO DEMONSTRAÇÃO")
        print("=" * 60)
        print("📋 Este é um arquivo de APLICAÇÃO GUI, não de testes.")
        print("🎮 Controles disponíveis na interface.")
        print("=" * 60)
        print("🚀 Interface carregada com sucesso!")

        # Loop principal
        app.mainloop()

    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n👋 Demonstração finalizada")

else:
    # Quando importado como módulo
    print("📦 Módulo de Temas carregado para o sistema Opera")

#03/02/2025
