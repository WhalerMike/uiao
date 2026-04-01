"""UIAO Adapter Registry - auto-discovery of all installed adapters."""
from __future__ import annotations
import importlib
import pkgutil
from typing import Dict, Type

_REGISTRY: Dict[str, Type] = {}

def register(adapter_id: str):
    def decorator(cls):
        _REGISTRY[adapter_id] = cls
        return cls
    return decorator

def get_adapter(adapter_id: str):
    return _REGISTRY[adapter_id]

ADAPTER_REGISTRY = _REGISTRY

for _loader, _name, _ispkg in pkgutil.walk_packages(
    __path__, prefix=__name__ + "."
):
    importlib.import_module(_name)
