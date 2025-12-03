import os
import sys
import shutil

def limpar_caches():
    print("🧹 LIMPANDO CACHES...")
    for pasta in ["__pycache__", "build", "dist"]:
        if os.path.exists(pasta):
            shutil.rmtree(pasta, ignore_errors=True)
    print("✅ Caches limpos!")

def detectar_diretorio_base():
    """
    Garante que, mesmo se o app for aberto via duplo clique (Finder),
    ele entre no diretório correto do .app.
    """
    if getattr(sys, 'frozen', False):
        # Caminho interno do .app
        base_path = os.path.dirname(sys.executable)
        # Se o app foi iniciado fora, força mudança para o diretório interno
        if not os.path.exists(os.path.join(base_path, "scripts")):
            possible_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))),
                "Contents", "MacOS"
            )
            if os.path.exists(os.path.join(possible_path, "scripts")):
                os.chdir(possible_path)
                base_path = possible_path
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(base_path)

    return base_path

def verificar_ambiente(base_path):
    print("🚀 INICIANDO INSTALADOR OPERA FASHION...")
    print(f"📁 Diretório atual: {base_path}")
    print("🔍 Verificando ambiente...")

    scripts_path = os.path.join(base_path, "scripts")
    if not os.path.exists(scripts_path):
        print("❌ Pasta 'scripts' não encontrada!")
        print("❌ Ambiente não configurado corretamente.")
        input("Pressione Enter para sair...")
        sys.exit(1)

    print("✅ Ambiente verificado com sucesso!")
    return scripts_path

def iniciar_instalador(scripts_path):
    print("🟢 Iniciando o processo de instalação...")
    main_script = os.path.join(os.path.dirname(scripts_path), "main.py")

    if not os.path.exists(main_script):
        print("⚠️ Arquivo principal não encontrado, usando executável embutido.")
        main_exe = os.path.join(os.path.dirname(scripts_path), "InstaladorOperaFashion")
        if os.path.exists(main_exe):
            os.system(f'"{main_exe}"')
        else:
            print("❌ Nenhum arquivo executável encontrado!")
        return

    os.system(f'python3 "{main_script}"')

if __name__ == "__main__":
    limpar_caches()
    base = detectar_diretorio_base()
    scripts = verificar_ambiente(base)
    iniciar_instalador(scripts)
    input("Pressione Enter para sair...")
