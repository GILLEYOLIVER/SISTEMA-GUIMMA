# -*- coding: utf-8 -*-
"""
OPERA_PATHS.py — Pastas graváveis (macOS .app / Windows / Linux)

✅ Resolve:
- Read-only file system no .app (PyInstaller)
- Páginas tentando criar pastas em "/" ou dentro do bundle

Como usar nas páginas:
    from PAGINAS_DO_SISTEMA.OPERA_PATHS import ensure_dir, path_in_data, ensure_default_tree

    pasta = ensure_dir("BANCO_DE_DADOS", "IMAGENS")
    arquivo = path_in_data("BANCO_DE_DADOS", "meu_arquivo.json")

Recomendado:
- Chamar ensure_default_tree() no início do MAIN.py
"""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Optional, Tuple

APP_NAME = "SistemaOpera"


# =============================================================================
# Diretório base gravável (Application Support / AppData / ~/.config)
# =============================================================================
def get_app_data_dir() -> Path:
    """
    Retorna uma pasta SEMPRE gravável para dados do sistema.

    macOS:   ~/Library/Application Support/SistemaOpera
    Windows: %APPDATA%\\SistemaOpera
    Linux:   ~/.config/SistemaOpera
    """

    # Se você quiser sobrescrever manualmente:
    override = os.environ.get("OPERA_DATA_DIR")
    if override:
        p = Path(override).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    system = platform.system()

    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
        p = base / APP_NAME
    elif system == "Windows":
        base = os.environ.get("APPDATA")
        if base:
            p = Path(base) / APP_NAME
        else:
            p = Path.home() / "AppData" / "Roaming" / APP_NAME
    else:
        p = Path.home() / ".config" / APP_NAME

    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_dir(*parts: str) -> Path:
    """
    Cria (se não existir) e retorna uma subpasta dentro do app_data_dir.
    """
    p = get_app_data_dir().joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


def path_in_data(*parts: str) -> str:
    """
    Retorna caminho (string) para um arquivo/pasta dentro do diretório gravável.
    Não cria o arquivo (somente resolve o caminho).
    """
    return str(get_app_data_dir().joinpath(*parts))


# =============================================================================
# Árvores padrão (pastas que o sistema costuma precisar)
# =============================================================================
def ensure_default_tree() -> None:
    """
    Cria a estrutura mínima que seu sistema costuma precisar.
    Chame 1x no start do MAIN.py.
    """
    # Ajuste estas pastas conforme o seu sistema
    ensure_dir("BANCO_DE_DADOS")
    ensure_dir("BANCO_DE_DADOS", "IMAGENS")
    ensure_dir("BANCO_DE_DADOS", "IMAGENS_FRENTE_COSTAS")
    ensure_dir("BANCO_DE_DADOS", "IMAGENS_MODELOS")

    ensure_dir("RECIBOS_DE_PAGAMENTOS")
    ensure_dir("EXPORTS")
    ensure_dir("RELATORIOS")
    ensure_dir("BACKUPS")
    ensure_dir("LOGS")


# =============================================================================
# Utilitários (bom para migrar páginas antigas)
# =============================================================================
def sanitize_absolute_path(path_str: str) -> str:
    """
    Se algum código antigo gerar paths absolutos perigosos (ex: "/BANCO DE DADOS"),
    esta função converte para dentro da pasta do app.

    Ex:
        "/BANCO DE DADOS" -> "<AppData>/BANCO DE DADOS"
    """
    if not path_str:
        return path_str

    p = Path(path_str)

    # Se for absoluto (começa com / no mac/linux ou "C:\\" no windows), jogamos para dentro do data_dir
    if p.is_absolute():
        # remove a raiz e usa os componentes como subpastas
        parts = [x for x in p.parts if x not in (p.anchor, os.sep)]
        if not parts:
            return str(get_app_data_dir())
        return path_in_data(*parts)

    # Se for relativo, deixa como está (mas você pode optar por colocar tudo no data_dir)
    return path_str


def safe_makedirs(path_str: str) -> Tuple[bool, str]:
    """
    Cria diretório com segurança:
    - Se for absoluto e perigoso, redireciona para dentro do app_data_dir.
    Retorna (ok, path_final).
    """
    final_path = sanitize_absolute_path(path_str)
    try:
        Path(final_path).mkdir(parents=True, exist_ok=True)
        return True, final_path
    except Exception:
        return False, final_path

if __name__ == "__main__":
    try:
        print(f"[TESTE_ISOLADO] Módulo carregado: {__file__}")
    except Exception as e:
        print(f"[TESTE_ISOLADO] Falha ao iniciar módulo: {e}")
