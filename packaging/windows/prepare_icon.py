# packaging/windows/prepare_icon.py
"""
Converte o ícone PNG para ICO para uso no Windows
"""
import os
import sys
from pathlib import Path

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠️  PIL/Pillow não instalado. Tentando instalar...")
    try:
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
        from PIL import Image

        HAS_PIL = True
        print("✅ PIL/Pillow instalado com sucesso")
    except Exception as e:
        print(f"❌ Falha ao instalar PIL: {e}")
        HAS_PIL = False


def convert_png_to_ico(png_path: str, ico_path: str) -> bool:
    """Converte PNG para ICO com múltiplos tamanhos"""
    if not HAS_PIL:
        print("❌ PIL não disponível. Não é possível converter ícone.")
        return False

    try:
        # Carregar imagem
        img = Image.open(png_path)

        # Garantir que tenha canal alpha (transparência)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Criar lista de tamanhos para o ICO
        sizes = [
            (256, 256),
            (128, 128),
            (96, 96),
            (64, 64),
            (48, 48),
            (32, 32),
            (24, 24),
            (16, 16)
        ]

        # Salvar como ICO
        img.save(ico_path, format='ICO', sizes=sizes, append_images=[
            img.resize(size, Image.Resampling.LANCZOS) for size in sizes
        ])

        print(f"✅ Ícone convertido: {png_path} -> {ico_path}")
        print(f"   Tamanhos incluídos: {', '.join(f'{w}x{h}' for w, h in sizes)}")
        return True

    except Exception as e:
        print(f"❌ Erro ao converter ícone: {e}")
        return False


def create_default_ico(ico_path: str) -> bool:
    """Cria um ícone padrão se o PNG não existir"""
    try:
        # Criar um ícone simples com "OP" usando PIL
        from PIL import Image, ImageDraw, ImageFont

        # Criar imagem 256x256
        img = Image.new('RGBA', (256, 256), (30, 60, 114))  # Azul escuro
        draw = ImageDraw.Draw(img)

        try:
            # Tentar carregar fonte
            font = ImageFont.truetype("arial.ttf", 100)
        except:
            font = ImageFont.load_default()

        # Desenhar "OP" no centro
        text = "OP"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((256 - text_width) // 2, (256 - text_height) // 2)

        draw.text(position, text, fill=(255, 255, 255), font=font)

        # Salvar como ICO
        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        img.save(ico_path, format='ICO', sizes=sizes)

        print(f"✅ Ícone padrão criado: {ico_path}")
        return True

    except Exception as e:
        print(f"❌ Falha ao criar ícone padrão: {e}")
        return False


def main():
    print("=" * 60)
    print("🔄 PREPARANDO ÍCONE PARA WINDOWS")
    print("=" * 60)

    # Caminhos
    base_dir = Path(__file__).parent.parent.parent
    icons_dir = base_dir / "icons"

    # Garantir que a pasta icons existe
    icons_dir.mkdir(exist_ok=True)

    # Caminhos dos arquivos
    png_path = icons_dir / "ICONE_SISTEMA.png"
    ico_path = icons_dir / "ICONE_SISTEMA.ico"

    print(f"📁 Pasta base: {base_dir}")
    print(f"📁 Pasta de ícones: {icons_dir}")
    print(f"🔍 Procurando: {png_path}")

    # Verificar se o PNG existe
    if png_path.exists():
        print(f"✅ PNG encontrado: {png_path}")

        # Converter PNG para ICO
        if convert_png_to_ico(str(png_path), str(ico_path)):
            # Verificar se o ICO foi criado
            if ico_path.exists():
                print(f"✅ ICO criado com sucesso: {ico_path}")
                print(f"   Tamanho: {ico_path.stat().st_size} bytes")
                return True
    else:
        print(f"⚠️  PNG não encontrado: {png_path}")
        print("📋 Procurando em locais alternativos...")

        # Procurar em locais alternativos
        alt_paths = [
            base_dir / "PAGINAS_DO_SISTEMA" / "ICONE_SISTEMA.png",
            base_dir / "ICONE_SISTEMA.png",
            base_dir / "src" / "ICONE_SISTEMA.png",
        ]

        for alt_path in alt_paths:
            if alt_path.exists():
                print(f"✅ PNG encontrado em local alternativo: {alt_path}")
                if convert_png_to_ico(str(alt_path), str(ico_path)):
                    return True
                break

    # Se chegou aqui, não conseguiu converter
    print("⚠️  Criando ícone padrão...")
    if create_default_ico(str(ico_path)):
        return True

    print("❌ Não foi possível criar o ícone ICO")
    return False


if __name__ == "__main__":
    success = main()
    if not success:
        print("\n💡 DICA: Coloque o arquivo 'ICONE_SISTEMA.png' na pasta 'icons/'")
        print("   Ou execute: python -m pip install pillow")
        sys.exit(1)
    else:
        print("\n✅ Preparação do ícone concluída com sucesso!")