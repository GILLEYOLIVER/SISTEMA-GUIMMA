 # PAGINAS_DO_SISTEMA/MAIN.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path


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


def _is_valid_config_file(path: Path) -> bool:
    try:
        if not path.exists() or not path.is_file():
            return False
        data = json.loads(path.read_text(encoding="utf-8"))
        return isinstance(data, dict) and bool(data)
    except Exception:
        return False


def _ensure_db_config_before_app() -> None:
    """
    Na primeira execução (sem config.json), abre o SETUP_BANCO para configurar
    e salvar o arquivo, incluindo PAGINAS_DO_SISTEMA/config.json.
    """
    pages_dir = Path(__file__).resolve().parent
    project_root = pages_dir.parent
    app_cfg = get_app_data_dir() / "config.json"

    candidates = [
        pages_dir / "config.json",
        project_root / "config.json",
        app_cfg,
    ]

    if any(_is_valid_config_file(cfg) for cfg in candidates):
        return

    setup_script = pages_dir / "SETUP_BANCO.py"
    if not setup_script.exists():
        raise SystemExit("PAGINAS_DO_SISTEMA/SETUP_BANCO.py não encontrado para configuração inicial do banco.")

    result = subprocess.run([sys.executable, str(setup_script)], check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    if not _is_valid_config_file(pages_dir / "config.json"):
        raise SystemExit("Configuração inicial não gerou PAGINAS_DO_SISTEMA/config.json.")

# ✅ Pastas graváveis (resolve "Read-only file system" no .app)
from PAGINAS_DO_SISTEMA.OPERA_PATHS import ensure_default_tree, get_app_data_dir

os.environ.setdefault("GUIMMA_DATA_DIR", str(get_app_data_dir()))
ensure_default_tree()
if getattr(sys, "_MEIPASS", None):
    os.chdir(get_app_data_dir())

_ensure_db_config_before_app()


def _start_license_monitor(root):
    """Consulta o servidor periodicamente para aplicar bloqueios remotos."""
    if getattr(root, "_guimma_license_monitor_started", False):
        return
    setattr(root, "_guimma_license_monitor_started", True)

    try:
        from licenciamento.client import load_config
        from licenciamento.runtime import check_application_access, open_license_app
    except Exception as exc:
        print(f"[LICENCA] Monitor indisponivel: {exc}")
        return

    try:
        cfg = load_config()
        interval_minutes = int(cfg.get("poll_interval_minutes") or 10)
    except Exception:
        interval_minutes = 10
    interval_ms = max(interval_minutes, 5) * 60 * 1000
    running = {"value": False}

    def schedule_next():
        try:
            root.after(interval_ms, run_check)
        except Exception:
            pass

    def run_check():
        if running["value"]:
            schedule_next()
            return
        running["value"] = True

        def worker():
            try:
                decision = check_application_access(try_online=True)
                error_message = ""
            except Exception as exc:
                decision = None
                error_message = str(exc)

            def finish():
                running["value"] = False
                if decision is not None and decision.allowed:
                    schedule_next()
                    return

                try:
                    from tkinter import messagebox

                    if decision is None:
                        messagebox.showerror(
                            "Licenca nao validada",
                            "Nao foi possivel validar a licenca:\n" + error_message,
                            parent=root,
                        )
                    else:
                        messagebox.showerror(decision.title, decision.message, parent=root)
                except Exception:
                    pass

                try:
                    open_license_app()
                except Exception:
                    pass
                try:
                    root.destroy()
                except Exception:
                    pass

            try:
                root.after(0, finish)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    schedule_next()


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
    # Blindagem anti-flash: mantém a janela principal invisível e fora da tela
    # até o splash terminar e o login estar pronto.
    root.withdraw()
    try:
        root.attributes("-alpha", 0.0)
    except Exception:
        pass
    try:
        root.geometry("1x1+30000+30000")
    except Exception:
        pass

    holder = {"login": None}

    def preparar_login_em_background():
        """Monta a interface de login enquanto o splash ainda está visível."""
        if holder["login"] is not None:
            return
        try:
            holder["login"] = SistemaLoginModerno(root, iniciar_oculto=True)
            root.protocol("WM_DELETE_WINDOW", holder["login"].ao_fechar)
            # Evita mostrar a janela raiz (fundo preto) antes do login
            # terminar de montar toda a interface.
            root.update_idletasks()
            root.deiconify()
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
            try:
                root.attributes("-alpha", 1.0)
            except Exception:
                pass
            root.deiconify()
            root.lift()
            root.focus_force()
            _start_license_monitor(root)
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
        duration_ms=3000,
        allow_skip=False,
        block_close=True,
    )

    root.mainloop()


if __name__ == "__main__":
    main()
