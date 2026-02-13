#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cria executável da janela de configuração do banco com ícone incorporado
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path


def create_ico_from_png(png_path: Path, ico_path: Path) -> bool:
    """Converte PNG para ICO com múltiplos tamanhos"""
    try:
        from PIL import Image

        print(f"Convertendo {png_path.name} para ICO...")

        # Abrir imagem PNG
        img = Image.open(png_path)

        # Converter para RGBA se necessário
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Tamanhos para ícone do Windows
        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]

        # Salvar como ICO
        img.save(ico_path, format='ICO', sizes=sizes)

        if ico_path.exists():
            size_kb = ico_path.stat().st_size / 1024
            print(f"✅ ICO criado: {ico_path} ({size_kb:.1f} KB)")
            return True
        return False
    except Exception as e:
        print(f"Erro ao converter: {e}")
        return False


def create_default_ico(ico_path: Path) -> bool:
    """Cria um ícone padrão"""
    try:
        from PIL import Image, ImageDraw, ImageFont

        print("Criando ícone padrão...")

        img = Image.new('RGBA', (256, 256), (0, 102, 204))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 120)
        except:
            font = ImageFont.load_default()

        text = "DB"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (256 - text_width) // 2
        y = (256 - text_height) // 2

        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        draw.rectangle([(0, 0), (255, 255)], outline=(255, 255, 255), width=3)

        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        img.save(ico_path, format='ICO', sizes=sizes)

        if ico_path.exists():
            print(f"✅ Ícone padrão criado")
            return True
        return False
    except Exception as e:
        print(f"Erro ao criar ícone: {e}")
        return False


def main():
    print("=" * 60)
    print("CONSTRUINDO CONFIGURADOR DO BANCO")
    print("=" * 60)

    base_dir = Path(__file__).parent.parent.parent
    script_path = base_dir / "packaging" / "windows" / "db_config_window.py"
    icons_dir = base_dir / "icons"
    build_dir = base_dir / "build"
    output_dir = base_dir / "dist" / "SistemaOpera"

    build_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not script_path.exists():
        print(f"Script não encontrado: {script_path}")
        return False

    # Procurar ícone
    icon_candidates = [
        icons_dir / "icon_config.png",
        icons_dir / "ICONE_SISTEMA.png",
        base_dir / "icon_config.png",
    ]

    icon_source = None
    for candidate in icon_candidates:
        if candidate.exists():
            icon_source = candidate
            print(f"Ícone encontrado: {icon_source}")
            break

    ico_path = build_dir / "configurador.ico"

    if icon_source and icon_source.suffix.lower() == '.png':
        if not create_ico_from_png(icon_source, ico_path):
            create_default_ico(ico_path)
    else:
        create_default_ico(ico_path)

    if not ico_path.exists():
        print("ERRO: Ícone não foi criado")
        return False

    # Limpar builds anteriores
    old_exe = output_dir / "CONFIGURAR_BANCO.exe"
    if old_exe.exists():
        old_exe.unlink()

    # Comando PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "CONFIGURAR_BANCO",
        "--distpath", str(output_dir),
        "--workpath", str(build_dir / "pyi_config"),
        "--specpath", str(build_dir),
        "--icon", str(ico_path),
        "--hidden-import", "tkinter",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL._imaging",
        "--hidden-import", "PIL.Image",
        "--hidden-import", "PIL.ImageTk",
        "--collect-all", "PIL",
        "--clean",
        "--noconfirm",
        str(script_path)
    ]

    print("\nExecutando PyInstaller...")

    try:
        subprocess.run(cmd, check=True)

        exe_path = output_dir / "CONFIGURAR_BANCO.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n✅ Configurador criado: {exe_path}")
            print(f"Tamanho: {size_mb:.2f} MB")

            # Copiar ícones para pasta de saída
            if icon_source and icon_source.exists():
                shutil.copy2(icon_source, output_dir / icon_source.name)
            if ico_path.exists():
                shutil.copy2(ico_path, output_dir / "configurador.ico")

            return True
        else:
            print("Executável não encontrado")
            return False
    except Exception as e:
        print(f"Erro: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)