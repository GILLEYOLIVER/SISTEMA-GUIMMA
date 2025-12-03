import os
import customtkinter as ctk
from PIL import Image, ImageEnhance
import tkinter as tk
import platform

# ===================== ESQUEMAS DE CORES =====================

COLOR_SCHEMES = {
    "profissional": {
        "accent_primary": "#00D4AA",
        "accent_secondary": "#1A1A1A",
        "text_primary": "#FFFFFF",
        "text_secondary": "#CCCCCC",
    },
    "azul_oceano": {
        "accent_primary": "#00D4AA",
        "accent_secondary": "#1A1A1A",
        "text_primary": "#FFFFFF",
        "text_secondary": "#CCCCCC",
    },
    "verde_moderno": {
        "accent_primary": "#00D4AA",
        "accent_secondary": "#1A1A1A",
        "text_primary": "#FFFFFF",
        "text_secondary": "#CCCCCC",
    }
}


class SplashScreenHD(ctk.CTkToplevel):
    """
    Splash screen em tela cheia
    """

    def __init__(self, parent, usuario_nome="Usuário", tema_preferido="profissional", on_complete=None):
        super().__init__(parent)

        self.on_complete = on_complete
        self.usuario_nome = usuario_nome
        self.tema_preferido = tema_preferido

        # Estado do progresso
        self.progress = 0
        self._progress_fraction = 0.0
        self.angle = 0
        self._auto_mode = False
        self._auto_job = None

        # Aplicar tema
        self._aplicar_tema(tema_preferido)

        # Configurar janela
        self.title("SISTEMA ÓPERA")
        self.configure(fg_color=self.accent_secondary)

        # Obter dimensões da tela
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Ajustar para não cobrir dock/barra de tarefas
        system = platform.system().lower()
        if system == "darwin":  # macOS
            screen_height -= 80  # Espaço para dock
        elif system == "windows":
            screen_height -= 40  # Espaço para barra de tarefas

        self.geometry(f"{screen_width}x{screen_height}+0+0")
        self.overrideredirect(True)

        try:
            self.attributes("-topmost", True)
        except Exception:
            pass

        # Bind ESC para fechar
        self.bind("<Escape>", lambda e: self._finish())

        # Carregar fundo
        self.bg_image_ctk = self._load_background_hd(screen_width, screen_height)

        # Criar interface
        self._create_widgets()

        # Iniciar animações
        self._animate_spinner()

        self.lift()
        self.focus_force()

    def _aplicar_tema(self, tema_preferido):
        """Aplicar esquema de cores"""
        colors = COLOR_SCHEMES.get("profissional")
        self.accent_primary = colors["accent_primary"]
        self.accent_secondary = colors["accent_secondary"]
        self.text_primary = colors["text_primary"]
        self.text_secondary = colors["text_secondary"]

    def _load_background_hd(self, width, height):
        """Carregar imagem de fundo"""
        base_path = os.path.dirname(__file__)
        for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
            path = os.path.join(base_path, "FUNDO_SPLASH" + ext)
            if os.path.exists(path):
                try:
                    img = Image.open(path)
                    img = img.resize((width, height), Image.Resampling.LANCZOS)

                    # Escurecer imagem
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(0.35)

                    return ctk.CTkImage(
                        light_image=img,
                        dark_image=img,
                        size=(width, height),
                    )
                except Exception as e:
                    print(f"[SPLASH] Erro ao carregar fundo: {e}")
        return None

    def _create_widgets(self):
        """Criar interface do usuário"""
        # Frame principal
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)

        # Fundo
        if self.bg_image_ctk is not None:
            bg_label = ctk.CTkLabel(main_frame, image=self.bg_image_ctk, text="")
            bg_label.pack(fill="both", expand=True)

        # Container central
        center_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        center_container.place(relx=0.5, rely=0.5, anchor="center")

        # Ícone do sistema
        self._create_icon(center_container)

        # Título
        self._create_title(center_container)

        # Mensagem de boas-vindas
        self._create_welcome(center_container)

        # Barra de progresso
        self._create_progress(center_container)

        # Status e spinner
        self._create_status(center_container)

        # Rodapé
        self._create_footer(center_container)

    def _create_icon(self, parent):
        """Criar ícone do sistema"""
        icon_frame = ctk.CTkFrame(parent, fg_color="transparent")
        icon_frame.pack(pady=(0, 20))

        icon_path = os.path.join(os.path.dirname(__file__), "ICONE_SISTEMA.png")
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                self.icon_ctk = ctk.CTkImage(
                    light_image=img,
                    dark_image=img,
                    size=(200, 200),
                )
                lbl_icon = ctk.CTkLabel(icon_frame, image=self.icon_ctk, text="", fg_color="transparent")
                lbl_icon.pack()
            except Exception as e:
                print(f"[SPLASH] Erro ao carregar ícone: {e}")
                self._create_fallback_icon(icon_frame)
        else:
            self._create_fallback_icon(icon_frame)

    def _create_fallback_icon(self, parent):
        """Ícone fallback"""
        lbl = ctk.CTkLabel(parent, text="⚙️", font=("Arial", 120), fg_color="transparent")
        lbl.pack()

    def _create_title(self, parent):
        """Criar título e subtítulo"""
        title_frame = ctk.CTkFrame(parent, fg_color="transparent")
        title_frame.pack(pady=(0, 15))

        # Título principal
        lbl_title = ctk.CTkLabel(
            title_frame,
            text="SISTEMA ÓPERA",
            font=("Montserrat", 48, "bold"),
            text_color=self.accent_primary,
            fg_color="transparent",
        )
        lbl_title.pack()

        # Subtítulo
        lbl_sub = ctk.CTkLabel(
            title_frame,
            text="GESTÃO DE PRODUÇÃO TÊXTIL",
            font=("Montserrat", 14, "bold"),
            text_color=self.text_secondary,
            fg_color="transparent",
        )
        lbl_sub.pack(pady=(5, 0))

        # Linha decorativa
        line = ctk.CTkFrame(
            title_frame,
            fg_color=self.accent_primary,
            height=2,
            width=350,
            corner_radius=0,
        )
        line.pack(pady=10)

    def _create_welcome(self, parent):
        """Criar área de boas-vindas"""
        welcome_frame = ctk.CTkFrame(
            parent,
            fg_color="transparent",
            border_width=2,
            border_color=self.accent_primary,
            corner_radius=8,
            width=400,
            height=90,
        )
        welcome_frame.pack(pady=15)
        welcome_frame.pack_propagate(False)

        # Emoji
        lbl_emoji = ctk.CTkLabel(welcome_frame, text="👋", font=("Arial", 24), fg_color="transparent")
        lbl_emoji.pack(pady=(8, 0))

        # Mensagem de boas-vindas
        self.lbl_welcome = ctk.CTkLabel(
            welcome_frame,
            text=f"Bem-vindo, {self.usuario_nome}!",
            font=("Arial", 16, "bold"),
            text_color=self.text_primary,
            fg_color="transparent",
        )
        self.lbl_welcome.pack()

        # Mensagem de carregamento
        lbl_loading = ctk.CTkLabel(
            welcome_frame,
            text="Preparando seu ambiente de trabalho...",
            font=("Arial", 11),
            text_color=self.text_secondary,
            fg_color="transparent",
        )
        lbl_loading.pack(pady=(0, 8))

    def _create_progress(self, parent):
        """Criar barra de progresso"""
        progress_container = ctk.CTkFrame(parent, fg_color="transparent")
        progress_container.pack(pady=20)

        # Container da barra
        self.progress_bg = ctk.CTkFrame(
            progress_container,
            fg_color="transparent",
            corner_radius=0,
            height=30,
            width=500,
            border_width=2,
            border_color=self.accent_primary,
        )
        self.progress_bg.pack()
        self.progress_bg.pack_propagate(False)

        # Barra de progresso interna
        self.progress_bar = ctk.CTkFrame(
            self.progress_bg,
            fg_color=self.accent_primary,
            corner_radius=0,
            height=24,
            width=0,  # Começa com 0
        )
        self.progress_bar.place(x=2, y=2)

        # Porcentagem
        self.lbl_percent = ctk.CTkLabel(
            progress_container,
            text="0%",
            font=("Montserrat", 18, "bold"),
            text_color=self.accent_primary,
            fg_color="transparent",
        )
        self.lbl_percent.pack(pady=8)

    def _create_status(self, parent):
        """Criar área de status e spinner"""
        status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        status_frame.pack(pady=10)

        # Mensagem de status
        self.lbl_status = ctk.CTkLabel(
            status_frame,
            text="Inicializando módulos do sistema...",
            font=("Arial", 12),
            text_color=self.text_secondary,
            fg_color="transparent",
        )
        self.lbl_status.pack()

        # Spinner
        self.spinner_frame = ctk.CTkFrame(status_frame, fg_color="transparent", width=40, height=40)
        self.spinner_frame.pack(pady=8)

        self.spinner_canvas = tk.Canvas(
            self.spinner_frame,
            width=40,
            height=40,
            bg=self.accent_secondary,
            highlightthickness=0,
        )
        self.spinner_canvas.pack()

    def _create_footer(self, parent):
        """Criar rodapé"""
        footer = ctk.CTkFrame(parent, fg_color="transparent")
        footer.pack(pady=15)

        # Versão
        lbl_version = ctk.CTkLabel(
            footer,
            text="Versão 1.0",
            font=("Arial", 11),
            text_color=self.text_secondary,
            fg_color="transparent",
        )
        lbl_version.pack()

        # Copyright
        lbl_copyright = ctk.CTkLabel(
            footer,
            text="© 2025 SISTEMA ÓPERA • Todos os direitos reservados",
            font=("Arial", 10),
            text_color=self.text_secondary,
            fg_color="transparent",
        )
        lbl_copyright.pack(pady=(2, 0))

    def _draw_spinner(self):
        """Desenhar spinner"""
        self.spinner_canvas.delete("all")
        cx, cy, r = 20, 20, 15
        extent = 80
        self.spinner_canvas.create_arc(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            start=self.angle,
            extent=extent,
            style="arc",
            outline=self.accent_primary,
            width=3,
        )

    def _animate_spinner(self):
        """Animar spinner"""
        if not self.winfo_exists():
            return
        self.angle = (self.angle + 10) % 360
        self._draw_spinner()
        self.after(50, self._animate_spinner)

    def update_progress(self, fraction: float, message: str = None):
        """Atualizar progresso"""
        if not self.winfo_exists():
            return

        # Validar fração
        try:
            f = float(fraction)
        except Exception:
            f = 0.0

        f = max(0.0, min(1.0, f))
        self._progress_fraction = f
        self.progress = int(round(f * 100))

        # Atualizar barra
        max_width = 500 - 4  # Largura máxima da barra
        bar_width = int(max_width * f)

        try:
            self.progress_bar.configure(width=bar_width)
            self.lbl_percent.configure(text=f"{self.progress}%")
            if message:
                self.lbl_status.configure(text=message)
        except Exception:
            pass

        try:
            self.update_idletasks()
        except Exception:
            pass

    def set_status_message(self, message: str):
        """Definir mensagem de status"""
        if not self.winfo_exists():
            return
        try:
            self.lbl_status.configure(text=message)
            self.update_idletasks()
        except Exception:
            pass

    def complete(self, message: str = None, delay_ms: int = 600):
        """Completar carregamento"""
        if message:
            self.set_status_message(message)
        self.update_progress(1.0)
        self.after(delay_ms, self._finish)

    def _finish(self):
        """Finalizar splash"""
        self._auto_mode = False
        try:
            if self.on_complete is not None:
                self.on_complete()
        except Exception as e:
            print(f"[SPLASH] Erro em on_complete: {e}")
        try:
            self.destroy()
        except Exception:
            pass


def rodar_menu_com_splash(usuario_id, usuario_nome, hierarquia, tema_preferido="Noite Urbana"):
    """
    Função principal para integrar login com menu via splash
    """
    try:
        print(f"[SPLASH] Iniciando sistema para: {usuario_nome}")
        print(f"[SPLASH] Tema preferido: {tema_preferido}")

        # Criar janela raiz
        root = ctk.CTk()
        root.title("SISTEMA ÓPERA")
        root.withdraw()

        def quando_splash_terminar():
            """Callback quando o splash terminar"""
            print("[SPLASH] Abrindo menu principal...")

            # Fechar splash e root
            try:
                splash.destroy()
            except:
                pass
            try:
                root.destroy()
            except:
                pass

            # Abrir menu principal
            try:
                from MENU_PRINCIPAL import OperaMenuApp

                app = OperaMenuApp(
                    usuario_id=usuario_id,
                    usuario_nome=usuario_nome,
                    usuario_hierarquia=hierarquia,
                    tema_preferido=tema_preferido
                )
                app.mainloop()

            except Exception as e:
                print(f"[SPLASH] Erro ao abrir menu: {e}")
                import traceback
                traceback.print_exc()

        # Criar splash
        splash = SplashScreenHD(
            parent=root,
            usuario_nome=usuario_nome,
            tema_preferido=tema_preferido,
            on_complete=quando_splash_terminar
        )

        # Simular carregamento
        def simular_carregamento():
            if splash.winfo_exists():
                messages = [
                    ("🔧 Inicializando módulos do sistema...", 0.2),
                    ("📦 Carregando bibliotecas essenciais...", 0.4),
                    ("🔌 Conectando ao banco de dados...", 0.6),
                    ("🎨 Preparando interface gráfica...", 0.8),
                    ("✨ Finalizando preparação...", 0.95)
                ]

                def next_step(index=0):
                    if index < len(messages):
                        msg, progress = messages[index]
                        splash.update_progress(progress, msg)
                        root.after(800, lambda: next_step(index + 1))
                    else:
                        splash.complete("✅ Sistema pronto! Abrindo...", 800)

                next_step()

        root.after(500, simular_carregamento)
        root.mainloop()

    except Exception as e:
        print(f"[SPLASH] Erro crítico: {e}")
        import traceback
        traceback.print_exc()

        # Fallback direto
        try:
            from MENU_PRINCIPAL import OperaMenuApp
            app = OperaMenuApp(
                usuario_id=usuario_id,
                usuario_nome=usuario_nome,
                usuario_hierarquia=hierarquia,
                tema_preferido=tema_preferido
            )
            app.mainloop()
        except Exception as fallback_error:
            print(f"[SPLASH] Erro no fallback: {fallback_error}")


if __name__ == "__main__":
    # Teste do splash
    ctk.set_appearance_mode("dark")

    root = ctk.CTk()
    root.withdraw()


    def teste_finalizar():
        print("✅ Splash teste finalizado")
        root.destroy()


    splash = SplashScreenHD(
        parent=root,
        usuario_nome="Usuário Teste",
        tema_preferido="Azul Oceano",
        on_complete=teste_finalizar
    )


    # Simular progresso no teste
    def teste_progresso():
        if splash.winfo_exists():
            splash.update_progress(0.3, "Testando módulos...")
            root.after(1000, lambda: splash.update_progress(0.7, "Carregando dados..."))
            root.after(2000, lambda: splash.complete("Teste concluído!", 500))


    root.after(500, teste_progresso)
    root.mainloop()