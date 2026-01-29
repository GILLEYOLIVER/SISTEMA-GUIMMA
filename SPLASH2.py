import os
import platform
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageEnhance, ImageFilter

from ui_after_guard import cancel_all_afters, initialize_after_guard

# ===================== ESQUEMAS DE CORES =====================

COLOR_SCHEMES = {
    "profissional": {
        "accent_primary": "#4F8CFF",
        "accent_secondary": "#0F172A",
        "text_primary": "#F8FAFC",
        "text_secondary": "#CBD5E1",
        "glass_bg": "#0B1220",
        "glass_border": "#243246",
    },
    "azul_oceano": {
        "accent_primary": "#38BDF8",
        "accent_secondary": "#0F172A",
        "text_primary": "#F8FAFC",
        "text_secondary": "#CBD5E1",
        "glass_bg": "#0B1220",
        "glass_border": "#243246",
    },
    "verde_moderno": {
        "accent_primary": "#22C55E",
        "accent_secondary": "#0F172A",
        "text_primary": "#F8FAFC",
        "text_secondary": "#CBD5E1",
        "glass_bg": "#0B1220",
        "glass_border": "#243246",
    },
}


class SplashScreenModern(ctk.CTkToplevel):
    """
    Splash screen moderna em tela cheia, com card central e foco em identidade visual.
    """

    def __init__(self, parent, usuario_nome="Usuário", tema_preferido="profissional", on_complete=None):
        super().__init__(parent)

        self.on_complete = on_complete
        self.usuario_nome = usuario_nome
        self.tema_preferido = tema_preferido

        self.progress = 0
        self._progress_fraction = 0.0
        self.angle = 0
        self._auto_mode = False
        self._auto_job = None

        initialize_after_guard(self)

        self._aplicar_tema(tema_preferido)

        self.title("SISTEMA ÓPERA")
        self.configure(fg_color=self.accent_secondary)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        system = platform.system().lower()
        if system == "darwin":
            screen_height -= 80
        elif system == "windows":
            screen_height -= 40

        self.geometry(f"{screen_width}x{screen_height}+0+0")
        self.overrideredirect(True)

        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        self.bind("<Escape>", lambda e: self._finish())

        self.bg_image_ctk = self._load_background_hd(screen_width, screen_height)

        self._create_widgets()

        self._animate_spinner()

        self.lift()
        self.focus_force()

    def _aplicar_tema(self, tema_preferido):
        colors = COLOR_SCHEMES.get(tema_preferido, COLOR_SCHEMES["profissional"])
        self.accent_primary = colors["accent_primary"]
        self.accent_secondary = colors["accent_secondary"]
        self.text_primary = colors["text_primary"]
        self.text_secondary = colors["text_secondary"]
        self.glass_bg = colors["glass_bg"]
        self.glass_border = colors["glass_border"]

    def _load_background_hd(self, width, height):
        base_path = os.path.dirname(__file__)
        for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
            path = os.path.join(base_path, "FUNDO_SPLASH" + ext)
            if os.path.exists(path):
                try:
                    img = Image.open(path).resize((width, height), Image.Resampling.LANCZOS)
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(0.25)
                    img = img.filter(ImageFilter.GaussianBlur(radius=1))
                    return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))
                except Exception as e:
                    print(f"[SPLASH2] Erro ao carregar fundo: {e}")
        return None

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)

        if self.bg_image_ctk is not None:
            bg_label = ctk.CTkLabel(main_frame, image=self.bg_image_ctk, text="")
            bg_label.pack(fill="both", expand=True)

        center_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        center_container.place(relx=0.5, rely=0.5, anchor="center")

        card = ctk.CTkFrame(
            center_container,
            fg_color=self.glass_bg,
            border_color=self.glass_border,
            border_width=1,
            corner_radius=24,
        )
        card.pack(padx=20, pady=20)

        self._create_header(card)
        self._create_progress(card)
        self._create_status(card)
        self._create_footer(card)

    def _create_header(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(padx=40, pady=(32, 12))

        icon_frame = ctk.CTkFrame(header, fg_color="transparent")
        icon_frame.pack(pady=(0, 16))

        icon_path = os.path.join(os.path.dirname(__file__), "ICONE_SISTEMA.png")
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                self.icon_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(140, 140))
                ctk.CTkLabel(icon_frame, image=self.icon_ctk, text="", fg_color="transparent").pack()
            except Exception as e:
                print(f"[SPLASH2] Erro ao carregar ícone: {e}")
                ctk.CTkLabel(icon_frame, text="⚙️", font=("Arial", 90), fg_color="transparent").pack()
        else:
            ctk.CTkLabel(icon_frame, text="⚙️", font=("Arial", 90), fg_color="transparent").pack()

        title = ctk.CTkLabel(
            header,
            text="ÓPERA FASHION",
            font=("Montserrat", 42, "bold"),
            text_color=self.text_primary,
        )
        title.pack()

        subtitle = ctk.CTkLabel(
            header,
            text="GESTÃO INTELIGENTE DE PRODUÇÃO",
            font=("Montserrat", 12, "bold"),
            text_color=self.text_secondary,
        )
        subtitle.pack(pady=(6, 0))

        welcome = ctk.CTkLabel(
            header,
            text=f"Bem-vindo, {self.usuario_nome}",
            font=("Montserrat", 12),
            text_color=self.text_secondary,
        )
        welcome.pack(pady=(12, 0))

    def _create_progress(self, parent):
        progress_frame = ctk.CTkFrame(parent, fg_color="transparent")
        progress_frame.pack(fill="x", padx=40, pady=(6, 12))

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            width=420,
            height=12,
            corner_radius=10,
            fg_color="#1E293B",
            progress_color=self.accent_primary,
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Preparando ambiente...",
            font=("Montserrat", 11),
            text_color=self.text_secondary,
        )
        self.progress_label.pack(anchor="w", pady=(10, 0))

    def _create_status(self, parent):
        status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        status_frame.pack(fill="x", padx=40, pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Carregando módulos essenciais",
            font=("Montserrat", 12, "bold"),
            text_color=self.text_primary,
        )
        self.status_label.pack(side="left")

        self.spinner_label = ctk.CTkLabel(
            status_frame,
            text="⟳",
            font=("Montserrat", 18, "bold"),
            text_color=self.accent_primary,
        )
        self.spinner_label.pack(side="right")

    def _create_footer(self, parent):
        footer = ctk.CTkFrame(parent, fg_color="transparent")
        footer.pack(fill="x", padx=40, pady=(8, 24))

        line = ctk.CTkFrame(
            footer,
            fg_color=self.glass_border,
            height=1,
            corner_radius=0,
        )
        line.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            footer,
            text="Versão Profissional • Segurança & Performance",
            font=("Montserrat", 10),
            text_color=self.text_secondary,
        ).pack()

    def update_status(self, message, progress=None):
        if message:
            self.status_label.configure(text=message)
        if progress is not None:
            self.progress_bar.set(max(0, min(progress, 1)))

    def _animate_spinner(self):
        self.angle = (self.angle + 20) % 360
        symbols = ["⟳", "⟲", "⟲", "⟳"]
        idx = (self.angle // 90) % len(symbols)
        try:
            self.spinner_label.configure(text=symbols[idx])
        except Exception:
            return
        self.after(120, self._animate_spinner)

    def start_auto_progress(self, duration_ms=3000):
        if self._auto_mode:
            return
        self._auto_mode = True
        steps = max(int(duration_ms / 50), 1)
        self._auto_step = 0
        self._auto_steps = steps
        self._auto_progress()

    def _auto_progress(self):
        if not self._auto_mode:
            return
        self._auto_step += 1
        frac = min(self._auto_step / self._auto_steps, 1.0)
        self.progress_bar.set(frac)
        if frac >= 1.0:
            self._finish()
            return
        self._auto_job = self.after(50, self._auto_progress)

    def _finish(self):
        cancel_all_afters(self)
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_complete:
            try:
                self.on_complete()
            except Exception:
                pass
