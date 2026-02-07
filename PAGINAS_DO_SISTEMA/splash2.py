import os
import platform
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageEnhance, ImageFilter

from PAGINAS_DO_SISTEMA.ui_after_guard import cancel_all_afters, initialize_after_guard

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
    Ajustes principais:
      - mantém referência do label de fundo (evita sumir no Mac/GC)
      - controla/cancela afters (spinner + auto progress) de forma robusta
      - reduz problemas de foco/topmost no macOS
      - garante chamada do on_complete 1x
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
        self._spinner_job = None
        self._finished = False

        initialize_after_guard(self)

        self._aplicar_tema(tema_preferido)

        self.title("SISTEMA ÓPERA")
        self.configure(fg_color=self.accent_secondary)

        # Tamanho full-screen mais estável (macOS incluso)
        screen_width = self.winfo_screenwidth()
        try:
            screen_height = self.winfo_vrootheight()
        except Exception:
            screen_height = self.winfo_screenheight()

        self.geometry(f"{screen_width}x{screen_height}+0+0")
        self.overrideredirect(True)

        # No macOS, topmost + focus_force pode causar “travas”/focus estranho.
        # Ainda assim, manter topmost ajuda, mas vamos fazer lift/focus com after.
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        # Fecha com ESC
        self.bind("<Escape>", lambda e: self.safe_finish())
        # Se alguma lib mandar WM_DELETE_WINDOW
        try:
            self.protocol("WM_DELETE_WINDOW", self.safe_finish)
        except Exception:
            pass

        self.bg_image_ctk = self._load_background_hd(screen_width, screen_height)

        self._create_widgets()

        # animações e foco (com after para melhorar compatibilidade)
        self._animate_spinner()
        self.after(50, self.lift)
        self.after(80, self._try_focus)

    # --------------------- util ---------------------

    def _try_focus(self):
        try:
            self.focus_force()
        except Exception:
            try:
                self.focus_set()
            except Exception:
                pass

    def _font(self, family, size, weight=None):
        # fallback simples caso Montserrat não exista no sistema
        fam = family
        try:
            # testar criando (tk aceita tupla mesmo sem fonte, mas alguns ambientes bugam)
            _ = (fam, size, weight) if weight else (fam, size)
            return _
        except Exception:
            fam = "Arial"
            return (fam, size, weight) if weight else (fam, size)

    def safe_finish(self):
        # garante finalização única
        if self._finished:
            return
        try:
            self._finish()
        except Exception:
            # fallback (não deixa travar se algo der errado)
            try:
                self.destroy()
            except Exception:
                pass
            if self.on_complete:
                try:
                    self.on_complete()
                except Exception:
                    pass

    # --------------------- tema/imagens ---------------------

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

    # --------------------- UI ---------------------

    def _create_widgets(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)

        # IMPORTANTE: manter referência do label para evitar sumir em alguns casos
        if self.bg_image_ctk is not None:
            self.bg_label = ctk.CTkLabel(self.main_frame, image=self.bg_image_ctk, text="")
            self.bg_label.pack(fill="both", expand=True)
        else:
            self.bg_label = None

        self.center_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.center_container.place(relx=0.5, rely=0.5, anchor="center")

        self.card = ctk.CTkFrame(
            self.center_container,
            fg_color=self.glass_bg,
            border_color=self.glass_border,
            border_width=1,
            corner_radius=24,
        )
        self.card.pack(padx=20, pady=20)

        self._create_header(self.card)
        self._create_progress(self.card)
        self._create_status(self.card)
        self._create_footer(self.card)

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
                ctk.CTkLabel(icon_frame, text="⚙️", font=self._font("Arial", 90, "bold"),
                             fg_color="transparent").pack()
        else:
            ctk.CTkLabel(icon_frame, text="⚙️", font=self._font("Arial", 90, "bold"),
                         fg_color="transparent").pack()

        title = ctk.CTkLabel(
            header,
            text="ÓPERA FASHION",
            font=self._font("Montserrat", 42, "bold"),
            text_color=self.text_primary,
        )
        title.pack()

        subtitle = ctk.CTkLabel(
            header,
            text="GESTÃO INTELIGENTE DE PRODUÇÃO",
            font=self._font("Montserrat", 12, "bold"),
            text_color=self.text_secondary,
        )
        subtitle.pack(pady=(6, 0))

        welcome = ctk.CTkLabel(
            header,
            text=f"Bem-vindo, {self.usuario_nome}",
            font=self._font("Montserrat", 12),
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
            font=self._font("Montserrat", 11),
            text_color=self.text_secondary,
        )
        self.progress_label.pack(anchor="w", pady=(10, 0))

    def _create_status(self, parent):
        status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        status_frame.pack(fill="x", padx=40, pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Carregando módulos essenciais",
            font=self._font("Montserrat", 12, "bold"),
            text_color=self.text_primary,
        )
        self.status_label.pack(side="left")

        self.spinner_label = ctk.CTkLabel(
            status_frame,
            text="⟳",
            font=self._font("Montserrat", 18, "bold"),
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
            font=self._font("Montserrat", 10),
            text_color=self.text_secondary,
        ).pack()

    # --------------------- API externa ---------------------

    def update_status(self, message, progress=None):
        if self._finished:
            return
        if message:
            try:
                self.status_label.configure(text=message)
            except Exception:
                pass
        if progress is not None:
            try:
                self.progress_bar.set(max(0, min(progress, 1)))
            except Exception:
                pass

    def start_auto_progress(self, duration_ms=3000):
        if self._finished or self._auto_mode:
            return
        self._auto_mode = True
        steps = max(int(duration_ms / 50), 1)
        self._auto_step = 0
        self._auto_steps = steps
        self._auto_progress()

    # --------------------- animações ---------------------

    def _animate_spinner(self):
        if self._finished:
            return
        self.angle = (self.angle + 20) % 360
        symbols = ["⟳", "⟲", "⟲", "⟳"]
        idx = (self.angle // 90) % len(symbols)
        try:
            self.spinner_label.configure(text=symbols[idx])
        except Exception:
            return
        self._spinner_job = self.after(120, self._animate_spinner)

    def _auto_progress(self):
        if self._finished or not self._auto_mode:
            return
        self._auto_step += 1
        frac = min(self._auto_step / self._auto_steps, 1.0)
        try:
            self.progress_bar.set(frac)
        except Exception:
            pass

        if frac >= 1.0:
            self.safe_finish()
            return
        self._auto_job = self.after(50, self._auto_progress)

    # --------------------- finalização ---------------------

    def _finish(self):
        if self._finished:
            return
        self._finished = True

        # cancela afters
        try:
            cancel_all_afters(self)
        except Exception:
            pass

        if self._spinner_job:
            try:
                self.after_cancel(self._spinner_job)
            except Exception:
                pass
            self._spinner_job = None

        if self._auto_job:
            try:
                self.after_cancel(self._auto_job)
            except Exception:
                pass
            self._auto_job = None

        # solta topmost antes de destruir (melhor no macOS)
        try:
            self.attributes("-topmost", False)
        except Exception:
            pass

        # destruir
        try:
            self.destroy()
        except Exception:
            pass

        # callback (uma vez)
        if self.on_complete:
            try:
                self.on_complete()
            except Exception:
                pass
if __name__ == "__main__":
    import customtkinter as ctk

    # aparência (opcional)
    ctk.set_appearance_mode("Dark")

    # root escondido (o splash é um Toplevel, precisa de um root)
    root = ctk.CTk()
    root.withdraw()

    def on_complete():
        # só pra confirmar que finalizou (pode trocar pra abrir seu login/menu)
        root.deiconify()
        root.title("OK")
        root.geometry("420x180")
        ctk.CTkLabel(root, text="Splash finalizou ✅", font=("Arial", 16)).pack(pady=40)
        ctk.CTkButton(root, text="Fechar", command=root.destroy).pack()

    splash = SplashScreenModern(
        parent=root,
        usuario_nome="Teste",
        tema_preferido="profissional",
        on_complete=on_complete
    )

    # fecha sozinho em 3s (ou remova essa linha e feche no ESC)
    splash.start_auto_progress(duration_ms=9000)

    root.mainloop()
