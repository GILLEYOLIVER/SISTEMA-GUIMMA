# PAGINAS_DO_SISTEMA/MAIN.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys


def _add_runtime_paths():
    """
    Garante imports funcionando em:
    - Rodando pelo Python (projeto aberto)
    - PyInstaller (dist/.app) -> sys._MEIPASS
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        p_meipass = meipass
        p_pages = os.path.join(meipass, "PAGINAS_DO_SISTEMA")
        if p_pages not in sys.path:
            sys.path.insert(0, p_pages)
        if p_meipass not in sys.path:
            sys.path.insert(0, p_meipass)

    here = os.path.dirname(os.path.abspath(__file__))  # .../src/PAGINAS_DO_SISTEMA
    if here not in sys.path:
        sys.path.insert(0, here)

    src_root = os.path.dirname(here)  # .../src
    if src_root not in sys.path:
        sys.path.insert(0, src_root)

    project_root = os.path.dirname(src_root)  # raiz do projeto
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


_add_runtime_paths()

# ✅ Pastas graváveis (resolve "Read-only file system" no .app)
from PAGINAS_DO_SISTEMA.OPERA_PATHS import ensure_default_tree, get_app_data_dir

os.environ.setdefault("OPERA_DATA_DIR", str(get_app_data_dir()))
ensure_default_tree()
if getattr(sys, "_MEIPASS", None):
    os.chdir(get_app_data_dir())


# ==============================================================================
# APP
# ==============================================================================
import customtkinter as ctk

from PAGINAS_DO_SISTEMA.SPLASH import SplashScreenModern
from PAGINAS_DO_SISTEMA.LOGUIN import SistemaLoginModerno


def main():
    # Aparência (ajuste se quiser)
    try:
        ctk.set_appearance_mode("Dark")
    except Exception:
        pass

    root = ctk.CTk()
    root.withdraw()  # esconde enquanto o splash roda

    holder = {"login": None}

    def preparar_login_em_background():
        """Monta a interface de login enquanto o splash ainda está visível."""
        if holder["login"] is not None:
            return
        try:
            holder["login"] = SistemaLoginModerno(root, iniciar_oculto=True)
            root.protocol("WM_DELETE_WINDOW", holder["login"].ao_fechar)
        except Exception as e:
            print(f"[BOOT] Erro ao preparar LOGIN: {e}")
            try:
                root.destroy()
            except Exception:
                pass

    def exibir_login_pronto():
        try:
            if holder["login"] is None:
                preparar_login_em_background()
            holder["login"].exibir_janela()
            root.update_idletasks()
            root.deiconify()
        except Exception as e:
            print(f"[BOOT] Erro ao exibir LOGIN: {e}")
            try:
                root.destroy()
            except Exception:
                pass

    # inicia a montagem do login enquanto o splash anima
    root.after(120, preparar_login_em_background)

    # Splash -> Login pronto
    SplashScreenModern(
        parent=root,
        usuario_nome="Usuário",
        tema_preferido="profissional",
        on_complete=lambda: root.after(0, exibir_login_pronto),
        duration_ms=6000,
        allow_skip=False,
        block_close=True,
    )

    root.mainloop()


if __name__ == "__main__":
    main()
