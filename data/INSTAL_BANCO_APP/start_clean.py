import os
import sys
import shutil
import subprocess
from pathlib import Path


REQUIRED_SQL_FILES = (
    "1_CRIAR_BANCO.sql",
    "2_CRIAR_SCHEMA.sql",
    "3_CRIAR_TABELAS.sql",
    "APAGAR_TUDO.sql",
)


def log(msg: str) -> None:
    print(msg, flush=True)


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def base_dir() -> Path:
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def app_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def clean_caches(project_dir: Path) -> None:
    log("🧹 LIMPANDO CACHES...")
    if is_frozen():
        log("ℹ️ Modo empacotado — não limpa build/dist.")
        return

    for folder in ("build", "dist"):
        p = project_dir / folder
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)

    for p in project_dir.rglob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)

    log("✅ Caches limpos!")


def check_scripts_folder(preferred_scripts: Path) -> None:
    log("🔍 Verificando ambiente...")

    if not preferred_scripts.exists() or not preferred_scripts.is_dir():
        raise RuntimeError(f"Pasta scripts não encontrada: {preferred_scripts}")

    missing = [f for f in REQUIRED_SQL_FILES if not (preferred_scripts / f).exists()]
    if missing:
        raise RuntimeError("Arquivos SQL faltando em scripts/: " + ", ".join(missing))

    log("✅ Ambiente verificado com sucesso!")


def run_main(project_dir: Path) -> int:
    log("🟢 Iniciando o processo de instalação...")

    main_py = project_dir / "main.py"
    if not main_py.exists():
        raise RuntimeError(f"main.py não encontrado: {main_py}")

    # IMPORTANTÍSSIMO: sys.executable (não usa 'python' do PATH)
    proc = subprocess.run(
        [sys.executable, str(main_py)],
        cwd=str(project_dir),
        check=False,
    )
    return int(proc.returncode)


def main() -> int:
    proj = app_dir()
    try:
        os.chdir(str(proj))
    except Exception:
        pass

    try:
        clean_caches(proj)

        # Checa scripts externos no modo dev
        scripts = proj / "scripts"
        check_scripts_folder(scripts)

        code = run_main(proj)
        log(f"📝 Instalador finalizado com código: {code}")
        return code
    except Exception as e:
        log("❌ ERRO:")
        log(str(e))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
