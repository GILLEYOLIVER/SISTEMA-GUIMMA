#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar o configurador do banco separadamente
"""
import sys
import os

# Adicionar o caminho do configurador ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packaging", "windows"))

# Importar e executar o configurador
from db_config_window import main

if __name__ == "__main__":
    print("=" * 60)
    print("TESTANDO CONFIGURADOR DO BANCO")
    print("=" * 60)
    sys.exit(main())