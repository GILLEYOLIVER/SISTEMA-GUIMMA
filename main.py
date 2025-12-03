#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import traceback

# =============================================================================
# 🔥 LIMPEZA TOTAL DE CACHE - EXECUTAR ANTES DE TUDO
# =============================================================================
def clear_all_caches():
    """Limpa todos os caches do Python e módulos"""
    print("🧹 LIMPANDO CACHES...")

    # Limpa cache de imports do Python
    for module in list(sys.modules.keys()):
        if any(x in module for x in ['interface', 'database_manager', 'scripts']):
            del sys.modules[module]

    # Limpa cache do filesystem se existir
    import importlib
    importlib.invalidate_caches()

    print("✅ Caches limpos!")


# Executa limpeza IMEDIATA
clear_all_caches()

# ==============================
# 🔧 Importações principais
# ==============================
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

def handle_exception(exc_type, exc_value, exc_traceback):
    """Captura exceções não tratadas"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    print("❌ ERRO NÃO TRATADO:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)

    # Tenta mostrar uma mensagem de erro
    try:
        from PyQt5.QtWidgets import QMessageBox
        app = QApplication.instance()
        if app:
            error_msg = f"Erro crítico:\n{str(exc_value)}\n\nVerifique o console para detalhes."
            QMessageBox.critical(None, "Erro Crítico", error_msg)
    except:
        pass

# Configura handler global de exceções
sys.excepthook = handle_exception


def check_environment():
    """Verifica se o ambiente está configurado corretamente"""
    print("🔍 Verificando ambiente...")

    # Verifica se a pasta scripts existe
    scripts_path = os.path.join(os.getcwd(), "scripts")
    if not os.path.exists(scripts_path):
        print("❌ Pasta 'scripts' não encontrada!")
        return False

    # Verifica se existem scripts SQL
    sql_files = [f for f in os.listdir(scripts_path) if f.endswith('.sql')]
    if not sql_files:
        print("❌ Nenhum script SQL encontrado na pasta 'scripts'!")
        return False

    print(f"✅ {len(sql_files)} scripts SQL encontrados")
    return True


def main():
    try:
        print("🚀 INICIANDO INSTALADOR OPERA FASHION...")
        print(f"📁 Diretório atual: {os.getcwd()}")

        # Adiciona o diretório atual ao path
        current_dir = os.getcwd()
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)

        # Verifica ambiente
        if not check_environment():
            print("❌ Ambiente não configurado corretamente.")
            input("Pressione Enter para sair...")
            return

        # Importa após verificar o ambiente
        try:
            from interface import InstallerApp
            from database_manager import DatabaseManager
        except ImportError as e:
            print(f"❌ Erro ao importar módulos: {e}")
            input("Pressione Enter para sair...")
            return

        # Caminho dos scripts SQL
        scripts_path = os.path.join(os.getcwd(), "scripts")
        db_manager = DatabaseManager(scripts_path)

        # Inicia interface
        app = QApplication(sys.argv)
        app.setApplicationName("Instalador Opera Fashion")
        app.setApplicationVersion("1.0")

        # Define estilo fusion para maior estabilidade
        app.setStyle('Fusion')

        window = InstallerApp(db_manager)
        window.show()

        print("✅ Interface iniciada com sucesso!")

        # Timer para verificar se a aplicação ainda está responsiva
        timer = QTimer()
        timer.timeout.connect(lambda: None)  # Callback vazio apenas para manter ativo
        timer.start(1000)

        # Garante que a aplicação feche completamente
        result = app.exec_()
        print(f"📝 Aplicação finalizada com código: {result}")
        sys.exit(result)

    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO MAIN: {e}")
        traceback.print_exc()
        input("Pressione Enter para sair...")


if __name__ == "__main__":
    main()