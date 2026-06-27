# packaging/macos/dmg_settings.py
# !/usr/bin/env python3
"""
Configurações e criação de DMG para macOS
"""
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path


def print_header(title):
    print("\n" + "=" * 60)
    print(f"📀 {title}")
    print("=" * 60)


def create_dmg():
    """Cria um DMG para distribuição no macOS"""
    print_header("CRIANDO INSTALADOR DMG")

    # Caminhos
    app_path = Path("dist/Sistema Guimma.app")
    dmg_path = Path("dist/Sistema Guimma.dmg")

    if not app_path.exists():
        print(f"❌ Aplicativo não encontrado: {app_path}")
        return False

    print(f"📦 Aplicativo: {app_path}")

    # Criar diretório temporário para DMG
    temp_dir = Path("dist/dmg_contents")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    try:
        # Copiar aplicativo
        print("📋 Copiando aplicativo...")
        shutil.copytree(app_path, temp_dir / "Sistema Guimma.app")

        # Criar link para Applications
        print("🔗 Criando link para Applications...")
        os.symlink("/Applications", temp_dir / "Applications")

        # Adicionar arquivo de boas-vindas
        welcome_text = """Bem-vindo ao Sistema Guimma!

Para instalar:
1. Arraste o ícone 'Sistema Guimma.app' para a pasta 'Applications'
2. Execute o aplicativo a partir do Launchpad ou Applications

Requisitos:
• macOS 10.15 ou superior
• PostgreSQL (opcional, pode ser configurado após instalação)

Suporte: Sistema Guimma
"""

        welcome_file = temp_dir / "LEIA-ME.txt"
        welcome_file.write_text(welcome_text, encoding="utf-8")

        # Configurações do DMG
        volume_name = "Sistema Guimma"
        print(f"📀 Criando DMG: {volume_name}")

        # Comando para criar DMG
        cmd = [
            "hdiutil", "create",
            "-volname", volume_name,
            "-srcfolder", str(temp_dir),
            "-ov",
            "-format", "UDZO",
            "-imagekey", "zlib-level=9",
            str(dmg_path)
        ]

        print(f"🚀 Executando: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Erro ao criar DMG: {result.stderr}")
            return False

        # Verificar DMG criado
        if dmg_path.exists():
            size_mb = dmg_path.stat().st_size / (1024 * 1024)
            print(f"✅ DMG criado com sucesso: {dmg_path}")
            print(f"📏 Tamanho: {size_mb:.2f} MB")

            # Verificar integridade do DMG
            print("🔍 Verificando integridade do DMG...")
            verify_cmd = ["hdiutil", "verify", str(dmg_path)]
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)

            if verify_result.returncode == 0:
                print("✅ DMG verificado com sucesso")
            else:
                print(f"⚠️  Aviso na verificação: {verify_result.stderr}")

            # Criar checksum
            print("🔢 Criando checksum...")
            checksum_cmd = ["shasum", "-a", "256", str(dmg_path)]
            checksum_result = subprocess.run(checksum_cmd, capture_output=True, text=True)

            if checksum_result.returncode == 0:
                checksum = checksum_result.stdout.split()[0]
                checksum_file = Path("dist/Sistema Guimma.dmg.sha256")
                checksum_file.write_text(f"{checksum}  Sistema Guimma.dmg\n")
                print(f"✅ Checksum: {checksum}")
                print(f"📄 Salvo em: {checksum_file}")

            return True
        else:
            print("❌ DMG não foi criado")
            return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False
    finally:
        # Limpar diretório temporário
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        print("🧹 Diretório temporário limpo")


def customize_dmg_background():
    """Personaliza o fundo do DMG (opcional)"""
    print_header("PERSONALIZANDO FUNDO DO DMG")

    # Esta função requer mais configuração e pode ser expandida
    print("🎨 Personalização de fundo do DMG")
    print("💡 Dica: Use o 'DropDMG' para personalização avançada")

    background_image = Path("icons/FUNDO_INSTALADOR.jpg")
    if background_image.exists():
        print(f"✅ Imagem de fundo encontrada: {background_image}")
        # Aqui você poderia usar o
