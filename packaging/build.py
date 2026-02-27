# packaging/build.py
# !/usr/bin/env python3
"""\
Script principal de build para Sistema Opera.
Suporta Windows e macOS.

Atenção (Windows): usamos --onedir para gerar a pasta _internal (python312.dll),
necessária para instalar e rodar a partir de Program Files.
"""

from __future__ import annotations

import os
import sys
import argparse
import subprocess
import shutil
import importlib.util
from pathlib import Path


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"🔨 {title}")
    print("=" * 60)


def _has_module(module_name: str) -> bool:
    """Retorna True se o módulo/submódulo existir no ambiente."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def check_dependencies() -> bool:
    """Verifica/instala dependências mínimas para o build."""
    print_header("VERIFICANDO DEPENDÊNCIAS")

    # (pip_package, import_name)
    required = [
        ("pyinstaller", "PyInstaller"),
        ("psycopg2-binary", "psycopg2"),
        ("pillow", "PIL"),
        ("customtkinter", "customtkinter"),
        # libs usadas no sistema (relatórios/gráficos/PDF)
        ("fpdf2", "fpdf"),
        ("reportlab", "reportlab"),
        ("matplotlib", "matplotlib"),
        ("numpy", "numpy"),
        ("pymupdf", "fitz"),
    ]

    missing: list[str] = []

    for pip_pkg, import_name in required:
        try:
            __import__(import_name)
            print(f"✅ {pip_pkg}")
        except ImportError:
            print(f"❌ {pip_pkg}")
            missing.append(pip_pkg)

    if missing:
        print(f"\n⚠️  Dependências faltando: {', '.join(missing)}")
        print("Instalando...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("✅ Dependências instaladas com sucesso")
        except subprocess.CalledProcessError as e:
            print(f"❌ Falha ao instalar dependências: {e}")
            return False

    return True


def prepare_resources(platform: str) -> bool:
    """Prepara e valida pastas básicas usadas pelo build."""
    print_header("PREPARANDO RECURSOS")

    Path("dist").mkdir(exist_ok=True)

    pages_dir = Path("PAGINAS_DO_SISTEMA")
    if not pages_dir.exists():
        print("❌ Pasta PAGINAS_DO_SISTEMA não encontrada")
        return False
    print(f"✅ PAGINAS_DO_SISTEMA: {pages_dir} ({len(list(pages_dir.glob('*.py')))} arquivos Python)")

    icons_dir = Path("icons")
    if not icons_dir.exists():
        print("⚠️  Pasta icons não encontrada. Criando...")
        icons_dir.mkdir(exist_ok=True)
    print(f"✅ Icons: {icons_dir}")

    data_dir = Path("data")
    if not data_dir.exists():
        print("⚠️  Pasta data não encontrada. Criando...")
        data_dir.mkdir(exist_ok=True)
    print(f"✅ Data: {data_dir}")

    return True


def build_windows() -> bool:
    """Build para Windows (onedir com _internal)."""
    print_header("BUILD PARA WINDOWS")

    # Converter ícone primeiro
    icon_script = Path("packaging/windows/prepare_icon.py")
    if icon_script.exists():
        print("🎨 Convertendo ícone PNG para ICO...")
        result = subprocess.run([sys.executable, str(icon_script)], capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.returncode != 0:
            print(f"⚠️  Aviso na conversão do ícone: {result.stderr}")
    else:
        print("⚠️  Script de conversão de ícone não encontrado")

    project_root = Path.cwd().resolve()
    icon_path = project_root / "icons" / "ICONE_SISTEMA.ico"
    main_script = project_root / "PAGINAS_DO_SISTEMA" / "MAIN.py"

    if not main_script.exists():
        print(f"❌ Arquivo principal não encontrado: {main_script}")
        return False

    # Se existir um .spec, usa ele. (mas o esperado é gerar onedir com _internal)
    spec_file = Path("SistemaOpera.spec")
    if spec_file.exists():
        print(f"📄 Usando arquivo .spec existente: {spec_file}")
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)]
    else:
        print("📄 Criando build sem arquivo .spec")
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--onedir",
            "--windowed",
            "--noconsole",
            "--name=SistemaOpera",
            "--distpath=dist",
            "--workpath=build/windows",
            "--specpath=build",
        ]

        if icon_path.exists():
            cmd.append(f"--icon={icon_path}")
            print(f"✅ Usando ícone: {icon_path}")
        else:
            print("⚠️  Ícone não encontrado, usando padrão")

        # Add-data (caminhos absolutos evitam erro com specpath no Windows)
        pages_src = project_root / "PAGINAS_DO_SISTEMA"
        icons_src = project_root / "icons"
        data_src = project_root / "data"
        cmd.extend([
            "--add-data",
            f"{pages_src};PAGINAS_DO_SISTEMA",
            "--add-data",
            f"{icons_src};icons",
            "--add-data",
            f"{data_src};data",
        ])

        # Hidden imports (somente os que existirem)
        hidden_imports = [
            "psycopg2",
            "customtkinter",
            "PIL",
            "PIL._imaging",
            "PIL.Image",
            "PIL.ImageFile",
            "PIL.ImageOps",
            "PIL.ImageDraw",
            "PIL.ImageFont",
            "PIL.ImageTk",
            "tkinter",
            "tkinter.ttk",
            "fpdf",
            "fpdf.enums",
            "reportlab",
            "reportlab.pdfgen",
            "reportlab.pdfbase",
            "reportlab.lib",
            "reportlab.graphics",
            "matplotlib",
            "matplotlib.pyplot",
            "matplotlib.backends.backend_tkagg",
            "numpy",
            "fitz",  # PyMuPDF
        ]

        for imp in hidden_imports:
            if _has_module(imp):
                cmd.extend(["--hidden-import", imp])

        # Collect-all apenas para pacotes que existirem
        for pkg in ["fpdf", "reportlab", "fitz"]:
            if _has_module(pkg):
                cmd.extend(["--collect-all", pkg])

        # Evita coletar suíte de testes pesada/instável no Windows
        cmd.extend(["--exclude-module", "matplotlib.tests"])
        cmd.extend(["--exclude-module", "PIL.tests"])

        cmd.append(str(main_script))

    print("\n📋 Comando PyInstaller:")
    print(" ".join(cmd))

    try:
        print("\n🚀 Executando PyInstaller...")
        subprocess.run(cmd, check=True, capture_output=True, text=True, shell=False)
        print("✅ Build concluído com sucesso!")

        # onedir esperado
        exe_path = Path("dist/SistemaOpera/SistemaOpera.exe")
        if not exe_path.exists():
            # fallback caso alguém use outro distpath
            exe_path = Path("dist/windows/SistemaOpera/SistemaOpera.exe")

        if not exe_path.exists():
            print("❌ Executável não foi criado (esperado: dist/SistemaOpera/SistemaOpera.exe)")
            return False

        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n📦 Executável criado: {exe_path}")
        print(f"📏 Tamanho: {size_mb:.2f} MB")

        # Garantir o ícone dentro da pasta do app (útil para instalador)
        try:
            app_dir = exe_path.parent
            if icon_path.exists():
                shutil.copy2(icon_path, app_dir / "ICONE_SISTEMA.ico")
                print("✅ Ícone copiado para a pasta do app")
        except Exception:
            pass

        # Verificar runtime
        dll_path = exe_path.parent / "_internal" / "python312.dll"
        if dll_path.exists():
            print(f"✅ Runtime OK: {dll_path}")
        else:
            print("⚠️  Runtime não encontrado em _internal\\python312.dll (layout inesperado).")

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Erro no PyInstaller: {e}")
        err_dir = Path("build")
        err_dir.mkdir(parents=True, exist_ok=True)
        err_log = err_dir / "pyinstaller_windows_error.log"
        try:
            err_log.write_text((e.stdout or "") + "\n\n--- STDERR ---\n" + (e.stderr or ""), encoding="utf-8", errors="replace")
            print(f"📄 Log completo salvo em: {err_log}")
        except Exception:
            pass

        stderr_text = (e.stderr or "").strip()
        if stderr_text:
            print("Stderr (últimas linhas):")
            print("\n".join(stderr_text.splitlines()[-60:]))
        return False


def build_macos() -> bool:
    """Build para macOS"""
    print_header("BUILD PARA macOS")

    project_root = Path.cwd().resolve()
    icon_path = project_root / "PAGINAS_DO_SISTEMA" / "ICONE_SISTEMA.icns"
    main_script = project_root / "PAGINAS_DO_SISTEMA" / "MAIN.py"

    if not main_script.exists():
        print(f"❌ Arquivo principal não encontrado: {main_script}")
        return False

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--windowed",
        "--noconsole",
        "--name=SistemaOpera",
        "--distpath=dist/macos",
        "--workpath=build/macos",
        "--specpath=build",
    ]

    if icon_path.exists():
        cmd.append(f"--icon={icon_path}")
        print(f"✅ Usando ícone: {icon_path}")
    else:
        png_path = Path("icons/ICONE_SISTEMA.png")
        if png_path.exists():
            print("⚠️  Convertendo PNG para ICNS...")
            icns_path = Path("icons/ICONE_SISTEMA.icns")
            try:
                subprocess.run(["sips", "-s", "format", "icns", str(png_path), "--out", str(icns_path)], check=True)
                if icns_path.exists():
                    cmd.append(f"--icon={icns_path}")
            except Exception:
                print("⚠️  Não foi possível converter ícone, usando padrão")
        else:
            print("⚠️  Ícone não encontrado, usando padrão")

    pages_src = project_root / "PAGINAS_DO_SISTEMA"
    icons_src = project_root / "icons"
    data_src = project_root / "data"
    cmd.extend([
        "--add-data",
        f"{pages_src}:PAGINAS_DO_SISTEMA",
        "--add-data",
        f"{icons_src}:icons",
        "--add-data",
        f"{data_src}:data",
    ])

    hidden_imports = [
        "psycopg2",
        "customtkinter",
        "PIL",
        "PIL._imaging",
        "PIL.Image",
        "PIL.ImageFile",
        "PIL.ImageOps",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "PIL.ImageTk",
        "tkinter",
        "tkinter.ttk",
        "fpdf",
        "fpdf.enums",
        "reportlab",
        "reportlab.pdfgen",
        "reportlab.pdfbase",
        "reportlab.lib",
        "reportlab.graphics",
        "matplotlib",
        "matplotlib.pyplot",
        "matplotlib.backends.backend_tkagg",
        "numpy",
        "fitz",
    ]

    for imp in hidden_imports:
        if _has_module(imp):
            cmd.extend(["--hidden-import", imp])

    for pkg in ["fpdf", "reportlab", "matplotlib", "fitz"]:
        if _has_module(pkg):
            cmd.extend(["--collect-all", pkg])

    cmd.append(str(main_script))

    print("\n📋 Comando PyInstaller:")
    print(" ".join(cmd))

    try:
        print("\n🚀 Executando PyInstaller...")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build concluído com sucesso!")

        app_path = Path("dist/macos/SistemaOpera.app")
        if app_path.exists():
            print(f"\n📦 Aplicativo criado: {app_path}")
            return True

        print(f"❌ Aplicativo não foi criado em: {app_path}")
        return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Erro no PyInstaller: {e}")
        err_dir = Path("build")
        err_dir.mkdir(parents=True, exist_ok=True)
        err_log = err_dir / "pyinstaller_macos_error.log"
        try:
            err_log.write_text((e.stdout or "") + "\n\n--- STDERR ---\n" + (e.stderr or ""), encoding="utf-8", errors="replace")
            print(f"📄 Log completo salvo em: {err_log}")
        except Exception:
            pass

        stderr_text = (e.stderr or "").strip()
        if stderr_text:
            print("Stderr (últimas linhas):")
            print("\n".join(stderr_text.splitlines()[-60:]))
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Build do Sistema Opera")
    parser.add_argument("--platform", choices=["windows", "macos", "all"], default="windows", help="Plataforma de build")
    parser.add_argument("--skip-deps", action="store_true", help="Pular verificação de dependências")

    args = parser.parse_args()

    print_header("SISTEMA OPERA - BUILD SYSTEM")
    print(f"📋 Plataforma: {args.platform}")
    print(f"📋 Python: {sys.version}")
    print(f"📋 Diretório: {os.getcwd()}")

    if not args.skip_deps:
        if not check_dependencies():
            print("❌ Falha nas dependências")
            return 1

    if not prepare_resources(args.platform):
        print("❌ Falha na preparação de recursos")
        return 1

    success = True
    if args.platform in ["windows", "all"]:
        success = success and build_windows()
    if args.platform in ["macos", "all"]:
        success = success and build_macos()

    if success:
        print_header("✅ BUILD CONCLUÍDO COM SUCESSO!")
        print("\n📁 Conteúdo criado (dist/):")
        dist_dir = Path("dist")
        for item in dist_dir.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(dist_dir)
                size_mb = item.stat().st_size / (1024 * 1024)
                print(f"  📄 {rel_path} ({size_mb:.1f} MB)")
        return 0

    print_header("❌ BUILD FALHOU")
    print("Dica: veja build/pyinstaller_windows_error.log (Windows) ou build/pyinstaller_macos_error.log (macOS)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
