# packaging/build.py
# !/usr/bin/env python3
"""
Script principal de build para Sistema Opera
Suporta Windows e macOS
"""
import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path


def print_header(title):
    """Imprime cabeçalho formatado"""
    print("\n" + "=" * 60)
    print(f"🔨 {title}")
    print("=" * 60)


def check_dependencies():
    """Verifica dependências necessárias"""
    print_header("VERIFICANDO DEPENDÊNCIAS")

    required = ['psycopg2', 'pillow']
    missing = []

    for dep in required:
        try:
            __import__(dep.replace('-', '_'))
            print(f"✅ {dep}")
        except ImportError:
            missing.append(dep)
            print(f"❌ {dep}")

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


def prepare_resources(platform):
    """Prepara recursos antes do build"""
    print_header("PREPARANDO RECURSOS")

    # Criar pasta dist se não existir
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)

    # Verificar pasta PAGINAS_DO_SISTEMA
    pages_dir = Path("PAGINAS_DO_SISTEMA")
    if not pages_dir.exists():
        print(f"❌ Pasta PAGINAS_DO_SISTEMA não encontrada")
        return False

    print(f"✅ PAGINAS_DO_SISTEMA: {pages_dir} ({len(list(pages_dir.glob('*.py')))} arquivos Python)")

    # Verificar pasta icons
    icons_dir = Path("icons")
    if not icons_dir.exists():
        print(f"⚠️  Pasta icons não encontrada. Criando...")
        icons_dir.mkdir(exist_ok=True)

    print(f"✅ Icons: {icons_dir}")

    # Verificar pasta data
    data_dir = Path("data")
    if not data_dir.exists():
        print(f"⚠️  Pasta data não encontrada. Criando...")
        data_dir.mkdir(exist_ok=True)

    print(f"✅ Data: {data_dir}")

    return True


def build_windows():
    """Build para Windows"""
    print_header("BUILD PARA WINDOWS")

    # Converter ícone primeiro
    icon_script = Path("packaging/windows/prepare_icon.py")
    if icon_script.exists():
        print("🎨 Convertendo ícone PNG para ICO...")
        result = subprocess.run([sys.executable, str(icon_script)],
                                capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(f"⚠️  Aviso na conversão do ícone: {result.stderr}")
    else:
        print("⚠️  Script de conversão de ícone não encontrado")

    # Caminhos
    icon_path = Path("icons/ICONE_SISTEMA.ico")
    main_script = Path("PAGINAS_DO_SISTEMA/MAIN.py")

    if not main_script.exists():
        print(f"❌ Arquivo principal não encontrado: {main_script}")
        return False

    # Construir comando PyInstaller
    cmd = [
        "pyinstaller",
        "--clean",
        "--onefile",
        "--windowed",
        "--noconsole",
        f"--name=SistemaOpera",
        "--distpath=dist/windows",
        "--workpath=build/windows",
        "--specpath=build"
    ]

    # Adicionar ícone se existir
    if icon_path.exists():
        cmd.append(f"--icon={icon_path}")
        print(f"✅ Usando ícone: {icon_path}")
    else:
        print("⚠️  Ícone não encontrado, usando padrão")

    # Adicionar dados
    cmd.extend([
        "--add-data", f"PAGINAS_DO_SISTEMA{os.pathsep}PAGINAS_DO_SISTEMA",
        "--add-data", f"icons{os.pathsep}icons",
        "--add-data", f"data{os.pathsep}data",
    ])

    # Hidden imports
    hidden_imports = [
        "psycopg2",
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
        "json",
        "datetime",
        "pathlib",
        "sys",
        "os",
        "io",
        "socket",
        "platform",
        "contextlib",
        "typing",
        "functools",
        "inspect",
    ]

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Adicionar script principal
    cmd.append(str(main_script))

    print(f"\n📋 Comando PyInstaller:")
    print(" ".join(cmd))

    # Executar
    try:
        print("\n🚀 Executando PyInstaller...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build concluído com sucesso!")

        # Verificar se executável foi criado
        exe_path = Path("dist/windows/SistemaOpera.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n📦 Executável criado: {exe_path}")
            print(f"📏 Tamanho: {size_mb:.2f} MB")

            # Copiar ícone para pasta do executável
            if icon_path.exists():
                shutil.copy2(icon_path, Path("dist/windows/ICONE_SISTEMA.ico"))
                print(f"✅ Ícone copiado para pasta do executável")

            return True
        else:
            print(f"❌ Executável não foi criado em: {exe_path}")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Erro no PyInstaller: {e}")
        print(f"Stderr: {e.stderr}")
        return False


def build_macos():
    """Build para macOS"""
    print_header("BUILD PARA macOS")

    # Caminhos
    icon_path = Path("PAGINAS_DO_SISTEMA/ICONE_SISTEMA.icns")
    main_script = Path("PAGINAS_DO_SISTEMA/MAIN.py")

    if not main_script.exists():
        print(f"❌ Arquivo principal não encontrado: {main_script}")
        return False

    # Construir comando PyInstaller
    cmd = [
        "pyinstaller",
        "--clean",
        "--windowed",
        "--noconsole",
        f"--name=SistemaOpera",
        "--distpath=dist/macos",
        "--workpath=build/macos",
        "--specpath=build"
    ]

    # Adicionar ícone se existir
    if icon_path.exists():
        cmd.append(f"--icon={icon_path}")
        print(f"✅ Usando ícone: {icon_path}")
    else:
        # Verificar se tem PNG e converter
        png_path = Path("icons/ICONE_SISTEMA.png")
        if png_path.exists():
            print("⚠️  Convertendo PNG para ICNS...")
            # Em macOS, pode usar sips para conversão
            icns_path = Path("icons/ICONE_SISTEMA.icns")
            try:
                subprocess.run(["sips", "-s", "format", "icns", str(png_path),
                                "--out", str(icns_path)], check=True)
                if icns_path.exists():
                    cmd.append(f"--icon={icns_path}")
            except:
                print("⚠️  Não foi possível converter ícone, usando padrão")
        else:
            print("⚠️  Ícone não encontrado, usando padrão")

    # Adicionar dados
    cmd.extend([
        "--add-data", f"PAGINAS_DO_SISTEMA{os.pathsep}PAGINAS_DO_SISTEMA",
        "--add-data", f"icons{os.pathsep}icons",
        "--add-data", f"data{os.pathsep}data",
    ])

    # Hidden imports (mesmo do Windows)
    hidden_imports = [
        "psycopg2",
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
    ]

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Adicionar script principal
    cmd.append(str(main_script))

    print(f"\n📋 Comando PyInstaller:")
    print(" ".join(cmd))

    # Executar
    try:
        print("\n🚀 Executando PyInstaller...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build concluído com sucesso!")

        # Verificar se app foi criado
        app_path = Path("dist/macos/SistemaOpera.app")
        if app_path.exists():
            print(f"\n📦 Aplicativo criado: {app_path}")

            # Criar DMG se solicitado
            create_dmg = input("\n📀 Criar arquivo DMG? (s/n): ").lower().strip()
            if create_dmg in ['s', 'sim', 'y', 'yes']:
                create_dmg_installer()

            return True
        else:
            print(f"❌ Aplicativo não foi criado em: {app_path}")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Erro no PyInstaller: {e}")
        print(f"Stderr: {e.stderr}")
        return False


def create_dmg_installer():
    """Cria instalador DMG para macOS"""
    print_header("CRIANDO INSTALADOR DMG")

    dmg_script = Path("packaging/macos/dmg_settings.py")
    if dmg_script.exists():
        print("📦 Criando DMG...")
        try:
            subprocess.run([sys.executable, str(dmg_script)], check=True)
            print("✅ DMG criado com sucesso!")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Erro ao criar DMG: {e}")
    else:
        print("⚠️  Script de criação de DMG não encontrado")


def main():
    parser = argparse.ArgumentParser(description="Build do Sistema Opera")
    parser.add_argument("--platform", choices=["windows", "macos", "all"],
                        default="windows", help="Plataforma de build")
    parser.add_argument("--skip-deps", action="store_true",
                        help="Pular verificação de dependências")

    args = parser.parse_args()

    print_header("SISTEMA OPERA - BUILD SYSTEM")
    print(f"📋 Plataforma: {args.platform}")
    print(f"📋 Python: {sys.version}")
    print(f"📋 Diretório: {os.getcwd()}")

    # Verificar dependências
    if not args.skip_deps:
        if not check_dependencies():
            print("❌ Falha nas dependências")
            return 1

    # Preparar recursos
    if not prepare_resources(args.platform):
        print("❌ Falha na preparação de recursos")
        return 1

    # Executar build
    success = True

    if args.platform in ["windows", "all"]:
        success = success and build_windows()

    if args.platform in ["macos", "all"]:
        success = success and build_macos()

    if success:
        print_header("✅ BUILD CONCLUÍDO COM SUCESSO!")
        print("\n📁 Conteúdo criado:")
        dist_dir = Path("dist")
        for item in dist_dir.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(dist_dir)
                size_mb = item.stat().st_size / (1024 * 1024)
                print(f"  📄 {rel_path} ({size_mb:.1f} MB)")

        print("\n🎯 Próximos passos:")
        print("   1. Para Windows: Execute packaging/windows/build_installer.ps1")
        print("   2. Para macOS: Execute packaging/macos/build_installer.sh")
        return 0
    else:
        print_header("❌ BUILD FALHOU")
        return 1


if __name__ == "__main__":
    sys.exit(main())