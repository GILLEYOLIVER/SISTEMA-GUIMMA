import os
import sys
import traceback
from pathlib import Path


# =========================
# Helpers de caminho
# =========================
def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """
    Diretório do app:
    - em modo empacotado: pasta onde está o .exe
    - em modo source: pasta do arquivo .py
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundled_base_dir() -> Path:
    """
    Base do conteúdo embutido:
    - onefile: sys._MEIPASS (pasta temporária)
    - caso não exista: app_dir()
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base).resolve()
    return app_dir()


def pick_scripts_dir() -> Path:
    """
    1) Prioriza scripts externos ao lado do EXE (atualizável)
    2) Fallback: scripts embutidos no onefile (sys._MEIPASS)
    """
    external = app_dir() / "scripts"
    if external.exists() and external.is_dir():
        return external
    return bundled_base_dir() / "scripts"


def resource_path(name: str) -> str:
    """
    Prioriza arquivo externo ao lado do EXE (atualizável),
    fallback para embutido.
    """
    ext = app_dir() / name
    if ext.exists():
        return str(ext)
    return str(bundled_base_dir() / name)


# =========================
# UX/Erros (sem input)
# =========================
def safe_pause(_msg: str = "") -> None:
    # Nunca usa input() em app GUI (--windowed)
    return


def show_fatal_error(title: str, text: str) -> None:
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        QMessageBox.critical(None, title, text)
    except Exception:
        print(f"[{title}] {text}", file=sys.stderr)


# =========================
# Validação de ambiente
# =========================
REQUIRED_SQL_FILES = (
    "1_CRIAR_BANCO.sql",
    "2_CRIAR_SCHEMA.sql",
    "3_CRIAR_TABELAS.sql",
    "APAGAR_TUDO.sql",
)


def check_environment(scripts_dir: Path) -> bool:
    if not scripts_dir.exists() or not scripts_dir.is_dir():
        return False
    for f in REQUIRED_SQL_FILES:
        if not (scripts_dir / f).exists():
            return False
    return True


def main() -> int:
    try:
        print("🚀 INICIANDO INSTALADOR OPERA FASHION...")
        print(f"📁 Diretório atual: {os.getcwd()}")
        print(f"📦 Modo empacotado: {is_frozen()}")

        # Garantir que imports locais funcionem
        cur = str(bundled_base_dir())
        if cur not in sys.path:
            sys.path.insert(0, cur)

        scripts_dir = pick_scripts_dir()
        print(f"📁 Scripts escolhidos: {scripts_dir}")

        if not check_environment(scripts_dir):
            msg = (
                "Pasta 'scripts' ou arquivos .sql não encontrados.\n\n"
                "O instalador procura primeiro por:\n"
                f"  1) {app_dir() / 'scripts'} (scripts externos ao lado do EXE)\n"
                "e se não existir, usa fallback embutido.\n\n"
                "Arquivos esperados em scripts/:\n"
                " - 1_CRIAR_BANCO.sql\n"
                " - 2_CRIAR_SCHEMA.sql\n"
                " - 3_CRIAR_TABELAS.sql\n"
                " - APAGAR_TUDO.sql\n"
            )
            show_fatal_error("Ambiente inválido", msg)
            return 1

        # Imports após validar scripts
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer
        from interface import InstallerApp
        from database_manager import DatabaseManager

        # Inicializa manager apontando para scripts escolhidos
        db_manager = DatabaseManager(str(scripts_dir))

        # Inicia UI
        app = QApplication(sys.argv)
        app.setApplicationName("Instalador Opera Fashion")
        app.setApplicationVersion("1.0")
        app.setStyle("Fusion")

        window = InstallerApp(db_manager)
        window.show()

        print("✅ Interface iniciada com sucesso!")

        # Timer leve (opcional)
        timer = QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(1000)

        code = app.exec()
        print(f"📝 Aplicação finalizada com código: {code}")
        return int(code)

    except Exception:
        err = traceback.format_exc()
        show_fatal_error("Erro inesperado", err)
        return 1


if __name__ == "__main__":
    sys.exit(main())
