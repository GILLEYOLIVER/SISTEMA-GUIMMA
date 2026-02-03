# main.py
import customtkinter as ctk

from SPLASH import SplashScreenModern
from LOGUIN import SistemaLoginModerno




def main():
    ctk.set_appearance_mode("Dark")

    root = ctk.CTk()
    root.withdraw()  # esconde enquanto o splash roda

    app_holder = {"login": None}  # evita GC e mantém referência

    def abrir_login():
        # splash já vai se destruir sozinho e chamar esse callback
        try:
            root.deiconify()
            app_holder["login"] = SistemaLoginModerno(root)
            root.protocol("WM_DELETE_WINDOW", app_holder["login"].ao_fechar)
        except Exception as e:
            print(f"[BOOT] Erro ao abrir LOGIN: {e}")
            try:
                root.destroy()
            except Exception:
                pass

    SplashScreenModern(
        parent=root,
        usuario_nome="Usuário",
        tema_preferido="profissional",
        on_complete=lambda: root.after(0, abrir_login),  # importante: after(0)
        duration_ms=6000,
        allow_skip=False,
        block_close=True,
    )

    root.mainloop()


if __name__ == "__main__":
    main()
#30/01/2026