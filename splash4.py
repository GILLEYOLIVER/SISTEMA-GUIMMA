import os
import math
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageEnhance, ImageFilter

# Se você tiver o guard, ele entra. Se não tiver, roda normal.
try:
    from ui_after_guard import cancel_all_afters, initialize_after_guard
except Exception:
    def initialize_after_guard(_):  # fallback
        pass

    def cancel_all_afters(_):  # fallback
        pass


# ===================== ESQUEMAS DE CORES =====================

COLOR_SCHEMES = {
    "profissional": {
        "accent_primary": "#4F8CFF",
        "accent_secondary": "#0B1220",
        "text_primary": "#F8FAFC",
        "text_secondary": "#CBD5E1",
        "glass_bg": "#0B1220",
        "glass_border": "#243246",
        "track_bg": "#101B2E",
        "muted": "#94A3B8",
    },
    "azul_oceano": {
        "accent_primary": "#38BDF8",
        "accent_secondary": "#07101F",
        "text_primary": "#F8FAFC",
        "text_secondary": "#CBD5E1",
        "glass_bg": "#0B1220",
        "glass_border": "#243246",
        "track_bg": "#0E2230",
        "muted": "#94A3B8",
    },
    "verde_moderno": {
        "accent_primary": "#22C55E",
        "accent_secondary": "#071A12",
        "text_primary": "#F8FAFC",
        "text_secondary": "#D1FAE5",
        "glass_bg": "#071A12",
        "glass_border": "#1F3A2E",
        "track_bg": "#0B2A1C",
        "muted": "#A7F3D0",
    },
}

DEFAULT_STEPS = [
    "Carregando módulos essenciais",
    "Verificando configurações do ambiente",
    "Inicializando tema e componentes visuais",
    "Conectando serviços e auditoria",
    "Preparando interface principal",
]


class SplashScreenModern(ctk.CTkToplevel):
    """
    Splash screen moderna e profissional (sem opção de pular).
    Recursos:
      - Fade-in / Fade-out
      - Spinner premium em Canvas (suave e estável)
      - Progresso automático com etapas
      - Barra de progresso + porcentagem
      - Fundo/ícone opcionais (FUNDO_SPLASH.* / contabilidade.* / ICONE_SISTEMA.*)
      - Melhor compatibilidade com macOS (lift/focus com after)
    """

    def __init__(
        self,
        parent,
        usuario_nome="Usuário",
        tema_preferido="profissional",
        on_complete=None,
        steps=None,
        duration_ms=2800,
        allow_skip=False,  # <- mantido por compatibilidade, mas padrão é NÃO permitir
        block_close=True,  # <- bloqueia fechar no X
    ):
        super().__init__(parent)

        # parâmetros
        self.on_complete = on_complete
        self.usuario_nome = usuario_nome
        self.tema_preferido = tema_preferido
        self.steps = list(steps) if steps else list(DEFAULT_STEPS)
        self.duration_ms = max(800, int(duration_ms))
        self.allow_skip = False if allow_skip is not True else False  # força OFF
        self.block_close = bool(block_close)

        # estado
        self._finished = False
        self._auto_mode = False
        self._auto_job = None
        self._spinner_job = None
        self._fade_job = None
        self._alpha = 0.0
        self._supports_alpha = True
        self._progress = 0.0
        self._angle = 0.0
        self._step_index = 0

        initialize_after_guard(self)
        self._aplicar_tema(self.tema_preferido)

        # janela
        self.title("SISTEMA ÓPERA")
        self.configure(fg_color=self.accent_secondary)
        self.overrideredirect(True)

        screen_w = self.winfo_screenwidth()
        try:
            screen_h = self.winfo_vrootheight()
        except Exception:
            screen_h = self.winfo_screenheight()

        self.geometry(f"{screen_w}x{screen_h}+0+0")

        # topmost
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        # alpha (fade)
        try:
            self.attributes("-alpha", 0.0)
        except Exception:
            self._supports_alpha = False

        # bloquear fechar no X (se o sistema precisa desse tempo)
        if self.block_close:
            try:
                self.protocol("WM_DELETE_WINDOW", lambda: None)
            except Exception:
                pass

        # assets
        self.bg_image_ctk = self._load_background_hd(screen_w, screen_h)
        self.icon_ctk = self._load_icon_any(size=(138, 138))

        # UI
        self._build_ui()

        # foco/ordem (macOS friendly)
        self.after(40, self.lift)
        self.after(80, self._try_focus)

        # start
        self._fade_to(1.0, ms=220)
        self._start_spinner()
        self.start_auto_progress(self.duration_ms)

    # ----------------------------- Tema / Assets -----------------------------

    def _aplicar_tema(self, tema_preferido):
        colors = COLOR_SCHEMES.get(tema_preferido, COLOR_SCHEMES["profissional"])
        self.accent_primary = colors["accent_primary"]
        self.accent_secondary = colors["accent_secondary"]
        self.text_primary = colors["text_primary"]
        self.text_secondary = colors["text_secondary"]
        self.glass_bg = colors["glass_bg"]
        self.glass_border = colors["glass_border"]
        self.track_bg = colors["track_bg"]
        self.muted = colors["muted"]

    def _base_path(self):
        return os.path.dirname(__file__)

    def _load_background_hd(self, width, height):
        base = self._base_path()
        for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
            path = os.path.join(base, "FUNDO_SPLASH" + ext)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGB")
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                    img = ImageEnhance.Brightness(img).enhance(0.28)
                    img = img.filter(ImageFilter.GaussianBlur(radius=1.2))

                    # leve “escurecimento” (blend)
                    overlay = Image.new("RGB", (width, height), (0, 0, 0))
                    img = Image.blend(img, overlay, alpha=0.22)

                    return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))
                except Exception as e:
                    print(f"[SPLASH] Erro fundo: {e}")
                    return None
        return None

    def _load_icon_any(self, size=(140, 140)):
        base = self._base_path()

        # prioridade: "contabilidade" (padrão), depois "ICONE_SISTEMA"
        base_names = ["contabilidade", "ICONE_SISTEMA"]

        for name in base_names:
            for ext in (".png", ".PNG", ".jpg", ".JPG", ".jpeg", ".JPEG"):
                path = os.path.join(base, name + ext)
                if os.path.exists(path):
                    try:
                        img = Image.open(path).convert("RGBA")
                        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
                    except Exception as e:
                        print(f"[SPLASH] Erro ícone: {e}")
        return None

    # ----------------------------- UI -----------------------------

    def _font(self, family, size, weight=None):
        # fallback seguro (Montserrat pode não existir)
        try:
            return (family, size, weight) if weight else (family, size)
        except Exception:
            family = "Arial"
            return (family, size, weight) if weight else (family, size)

    def _tk_bg(self, hexcolor: str):
        # tk.Canvas precisa de cor sólida (sem "transparent")
        return hexcolor

    def _build_ui(self):
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.pack(fill="both", expand=True)

        # fundo (guarda referência!)
        if self.bg_image_ctk is not None:
            self.bg_label = ctk.CTkLabel(self.main, image=self.bg_image_ctk, text="")
            self.bg_label.pack(fill="both", expand=True)
        else:
            self.bg_label = None

        # container central
        self.center = ctk.CTkFrame(self.main, fg_color="transparent")
        self.center.place(relx=0.5, rely=0.5, anchor="center")

        # card “glass”
        self.card = ctk.CTkFrame(
            self.center,
            fg_color=self.glass_bg,
            border_color=self.glass_border,
            border_width=1,
            corner_radius=26,
        )
        self.card.pack(padx=22, pady=22)

        # HEADER
        header = ctk.CTkFrame(self.card, fg_color="transparent")
        header.pack(padx=44, pady=(34, 10))

        icon_wrap = ctk.CTkFrame(header, fg_color="transparent")
        icon_wrap.pack(pady=(0, 16))

        if self.icon_ctk is not None:
            ctk.CTkLabel(icon_wrap, image=self.icon_ctk, text="", fg_color="transparent").pack()
        else:
            ctk.CTkLabel(
                icon_wrap,
                text="⚙️",
                font=self._font("Arial", 92, "bold"),
                text_color=self.accent_primary,
                fg_color="transparent",
            ).pack()

        ctk.CTkLabel(
            header,
            text="ÓPERA FASHION",
            font=self._font("Montserrat", 44, "bold"),
            text_color=self.text_primary,
        ).pack()

        ctk.CTkLabel(
            header,
            text="GESTÃO INTELIGENTE DE PRODUÇÃO",
            font=self._font("Montserrat", 12, "bold"),
            text_color=self.text_secondary,
        ).pack(pady=(8, 0))

        ctk.CTkLabel(
            header,
            text=f"Bem-vindo, {self.usuario_nome}",
            font=self._font("Montserrat", 12),
            text_color=self.muted,
        ).pack(pady=(12, 0))

        # BODY
        body = ctk.CTkFrame(self.card, fg_color="transparent")
        body.pack(fill="x", padx=44, pady=(8, 8))

        # status row + spinner
        status_row = ctk.CTkFrame(body, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            status_row,
            text=self.steps[0] if self.steps else "Preparando ambiente...",
            font=self._font("Montserrat", 13, "bold"),
            text_color=self.text_primary,
        )
        self.status_label.pack(side="left")

        self.spinner_canvas = tk.Canvas(
            status_row,
            width=26,
            height=26,
            highlightthickness=0,
            bd=0,
            bg=self._tk_bg(self.glass_bg),
        )
        self.spinner_canvas.pack(side="right", padx=(10, 0))

        # progress bar
        self.progress_bar = ctk.CTkProgressBar(
            body,
            height=12,
            corner_radius=10,
            fg_color=self.track_bg,
            progress_color=self.accent_primary,
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

        pr_row = ctk.CTkFrame(body, fg_color="transparent")
        pr_row.pack(fill="x", pady=(8, 0))

        self.progress_text = ctk.CTkLabel(
            pr_row,
            text="Inicializando ambiente...",
            font=self._font("Montserrat", 11),
            text_color=self.text_secondary,
        )
        self.progress_text.pack(side="left")

        self.percent_label = ctk.CTkLabel(
            pr_row,
            text="0%",
            font=self._font("Montserrat", 11, "bold"),
            text_color=self.text_secondary,
        )
        self.percent_label.pack(side="right")

        # FOOTER (melhorado e sem opção de pular)
        footer = ctk.CTkFrame(self.card, fg_color="transparent")
        footer.pack(fill="x", padx=44, pady=(14, 26))

        line = ctk.CTkFrame(footer, fg_color=self.glass_border, height=1, corner_radius=0)
        line.pack(fill="x", pady=(0, 10))

        self.footer_label = ctk.CTkLabel(
            footer,
            text="Inicializando ambiente • Segurança, Performance e Confiabilidade",
            font=self._font("Montserrat", 10, "bold"),
            text_color=self.text_secondary,
        )
        self.footer_label.pack()

        self.footer_sub = ctk.CTkLabel(
            footer,
            text="Processo automático — aguarde a conclusão.",
            font=self._font("Montserrat", 10),
            text_color=self.muted,
        )
        self.footer_sub.pack(pady=(6, 0))

    # ----------------------------- Controle Externo -----------------------------

    def update_status(self, message=None, progress=None):
        """Atualiza status e/ou progresso manualmente."""
        if self._finished:
            return

        if message:
            try:
                self.status_label.configure(text=message)
                self.progress_text.configure(text=message)
            except Exception:
                pass

        if progress is not None:
            self._progress = float(max(0.0, min(progress, 1.0)))
            try:
                self.progress_bar.set(self._progress)
            except Exception:
                pass
            self._update_percent()

    def start_auto_progress(self, duration_ms=2800):
        """Progresso automático (com etapas)."""
        if self._finished or self._auto_mode:
            return
        self._auto_mode = True
        self._elapsed_ms = 0
        self._total_ms = max(800, int(duration_ms))
        self._tick_ms = 35
        self._step_index = 0
        self._auto_progress_loop()

    # ----------------------------- Spinner Premium -----------------------------

    def _start_spinner(self):
        self._angle = 0.0
        self._draw_spinner()
        self._spinner_loop()

    def _spinner_loop(self):
        if self._finished:
            return
        self._angle = (self._angle + 10.0) % 360.0
        self._draw_spinner()
        self._spinner_job = self.after(38, self._spinner_loop)

    def _draw_spinner(self):
        c = self.spinner_canvas
        c.delete("all")

        cx, cy = 13, 13
        r = 11
        r2 = 9

        # track base
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=self.glass_border, width=2)

        # arc principal
        start = self._angle
        extent = 80
        c.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=start, extent=extent,
            style="arc",
            outline=self.accent_primary,
            width=3
        )

        # ponto interno
        px = cx + int(r2 * math.cos(math.radians(-self._angle)))
        py = cy + int(r2 * math.sin(math.radians(-self._angle)))
        c.create_oval(px - 2, py - 2, px + 2, py + 2, outline="", fill=self.accent_primary)

    # ----------------------------- Fade / Focus -----------------------------

    def _try_focus(self):
        try:
            self.focus_force()
        except Exception:
            try:
                self.focus_set()
            except Exception:
                pass

    def _fade_to(self, target_alpha=1.0, ms=220):
        if not self._supports_alpha:
            return

        target_alpha = float(max(0.0, min(target_alpha, 1.0)))
        steps = max(1, int(ms / 18))
        delta = (target_alpha - self._alpha) / steps

        def tick(i=0):
            if self._finished:
                return
            self._alpha = max(0.0, min(self._alpha + delta, 1.0))
            try:
                self.attributes("-alpha", self._alpha)
            except Exception:
                return
            if i >= steps - 1:
                try:
                    self.attributes("-alpha", target_alpha)
                except Exception:
                    pass
                self._alpha = target_alpha
                return
            self._fade_job = self.after(18, lambda: tick(i + 1))

        tick(0)

    # ----------------------------- Auto Progress -----------------------------

    def _auto_progress_loop(self):
        if self._finished or not self._auto_mode:
            return

        self._elapsed_ms += self._tick_ms
        frac = min(self._elapsed_ms / self._total_ms, 1.0)
        self._progress = frac

        if self.steps:
            idx = min(int(frac * len(self.steps)), len(self.steps) - 1)
            if idx != self._step_index:
                self._step_index = idx
                msg = self.steps[self._step_index]
                self.update_status(msg, progress=self._progress)
            else:
                self.update_status(None, progress=self._progress)
        else:
            self.update_status("Inicializando ambiente...", progress=self._progress)

        if frac >= 1.0:
            self.safe_finish()
            return

        self._auto_job = self.after(self._tick_ms, self._auto_progress_loop)

    def _update_percent(self):
        try:
            pct = int(round(self._progress * 100))
            self.percent_label.configure(text=f"{pct}%")
        except Exception:
            pass

    # ----------------------------- Finalização -----------------------------

    def safe_finish(self):
        if self._finished:
            return
        self._finish()

    def _finish(self):
        self._finished = True

        # cancela afters do guard (se existir)
        try:
            cancel_all_afters(self)
        except Exception:
            pass

        # cancela jobs locais
        for job_name in ("_auto_job", "_spinner_job", "_fade_job"):
            job = getattr(self, job_name, None)
            if job:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
                setattr(self, job_name, None)

        # fade-out rápido e finaliza
        try:
            self.attributes("-topmost", False)
        except Exception:
            pass

        if self._supports_alpha:
            # garante que está visível antes de sair
            self._alpha = 1.0
            try:
                self.attributes("-alpha", 1.0)
            except Exception:
                pass
            self._fade_to(0.0, ms=160)
            self.after(175, self._destroy_and_callback)
        else:
            self._destroy_and_callback()

    def _destroy_and_callback(self):
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_complete:
            try:
                self.on_complete()
            except Exception:
                pass


# ===================== TESTE DIRETO =====================
if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")

    root = ctk.CTk()
    root.withdraw()

    def on_complete():
        # Troque aqui para abrir seu Login/Menu real
        root.deiconify()
        root.title("Ópera - Teste")
        root.geometry("560x260")
        ctk.CTkLabel(root, text="Inicialização concluída ✅", font=("Arial", 18, "bold")).pack(pady=28)
        ctk.CTkLabel(root, text="Aqui você chamaria o Login/Menu do sistema.", font=("Arial", 13)).pack(pady=6)
        ctk.CTkButton(root, text="Fechar", command=root.destroy).pack(pady=18)

    splash = SplashScreenModern(
        parent=root,
        usuario_nome="Gilley",
        tema_preferido="profissional",
        on_complete=on_complete,
        duration_ms=8000,
        allow_skip=False,   # sem pular
        block_close=True,   # bloqueia fechar no X
    )

    root.mainloop()
