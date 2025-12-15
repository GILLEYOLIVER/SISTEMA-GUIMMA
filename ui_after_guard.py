"""Utilitários para gerenciar chamadas Tkinter ``after`` com segurança.

Este módulo centraliza a lógica de agendamento e cancelamento de timers
``after`` usados em diferentes janelas do sistema. Em alguns ambientes
(especialmente no Windows), callbacks pendentes que sobrevivem ao fechamento
da janela geram erros do tipo "invalid command name". Essas funções mantém
os IDs agendados e os cancelam de forma segura durante o encerramento,
evitando mensagens ruidosas e comportamentos inconsistentes entre macOS e
Windows.
"""

from __future__ import annotations

from typing import Callable, Optional


def _resolve_root(owner, root_attr: Optional[str]):
    """Obtém o widget raiz para operações de ``after``.

    Se ``root_attr`` for informado e existir no ``owner``, ele será usado.
    Caso contrário, o próprio ``owner`` é retornado, permitindo uso em
    ``Tk`` ou ``Toplevel`` diretamente.
    """

    if root_attr:
        return getattr(owner, root_attr, None)
    return owner


def initialize_after_guard(owner, root_attr: Optional[str] = None):
    """Inicializa controles de ``after`` no objeto informado.

    - Cria o conjunto ``_after_ids`` para armazenar IDs agendados.
    - Expõe o método ``_agendar_after`` que valida a janela antes de
      disparar novos timers.
    - Garante a flag ``_fechando`` para impedir novos agendamentos durante
      o fechamento.
    """

    if not hasattr(owner, "_after_ids"):
        owner._after_ids = set()

    if not hasattr(owner, "_fechando"):
        owner._fechando = False

    def _agendar_after(milissegundos: int, callback: Callable):
        try:
            root = _resolve_root(owner, root_attr)
            if root is None or not root.winfo_exists() or getattr(owner, "_fechando", False):
                return None
            after_id = root.after(milissegundos, callback)
            owner._after_ids.add(after_id)
            return after_id
        except Exception:
            return None

    owner._agendar_after = _agendar_after


def cancel_all_afters(owner, root_attr: Optional[str] = None):
    """Cancela todos os timers ``after`` registrados para o objeto."""

    root = _resolve_root(owner, root_attr)
    for after_id in list(getattr(owner, "_after_ids", set())):
        try:
            if root and root.winfo_exists():
                root.after_cancel(after_id)
        except Exception:
            # Silencia cancelamentos inválidos para manter compatibilidade cross-platform
            pass

    if hasattr(owner, "_after_ids"):
        owner._after_ids.clear()
