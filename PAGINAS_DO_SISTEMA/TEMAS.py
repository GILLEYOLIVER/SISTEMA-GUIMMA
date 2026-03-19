# -*- coding: utf-8 -*-
"""Compatibilidade: encaminha para TEMAS_usa-es-pt.py."""

import importlib.util
import sys
from pathlib import Path

_target = Path(__file__).with_name("TEMAS_usa-es-pt.py")
_spec = importlib.util.spec_from_file_location("compat_temas", str(_target))
if _spec is None or _spec.loader is None:
    raise ImportError(f"Não foi possível carregar {_target}")
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

for _name in dir(_mod):
    if _name.startswith("__") and _name not in {"__all__", "__doc__"}:
        continue
    globals()[_name] = getattr(_mod, _name)

__all__ = getattr(_mod, "__all__", [n for n in globals() if not n.startswith("_")])
