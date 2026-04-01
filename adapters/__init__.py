"""
UIAO Adapter Registry

Scope constraint:
- UIAO Canon is frozen (no schema/governance changes here).
- This module provides a simple, explicit registry for UIAO adapters.
- Vendor-specific adapters (e.g., uiao-adapter-entra) live in separate repos
  and import/extend BaseAdapter from uiao-core.

Usage patterns:
- Runtimes can use this registry to discover available adapters.
- Vendor adapter packages can register themselves at import time or via
  explicit registration calls in deployment code.
"""

from __future__ import annotations
from typing import Dict, Type

from .base_adapter import BaseAdapter

# Canonical in-process registry of adapter classes.
# Key: adapter_id (string, e.g., "uiao.adapter.microsoft.entra.v1")
# Value: adapter class (subclass of BaseAdapter)
_ADAPTER_REGISTRY: Dict[str, Type[BaseAdapter]] = {}


def register_adapter(adapter_cls: Type[BaseAdapter]) -> None:
    """
    Register an adapter class in the UIAO adapter registry.

    Adapter classes MUST:
    - Subclass BaseAdapter
    - Expose a stable, unique adapter_id property

    This function is idempotent: re-registering the same adapter_id
    with the same class is a no-op; re-registering with a different
    class raises ValueError.
    """
    if not issubclass(adapter_cls, BaseAdapter):
        raise TypeError("Adapter must subclass BaseAdapter")

    probe = adapter_cls.__new__(adapter_cls)
    adapter_id = adapter_cls.adapter_id.fget(probe)  # type: ignore[attr-defined]

    if adapter_id in _ADAPTER_REGISTRY and _ADAPTER_REGISTRY[adapter_id] is not adapter_cls:
        raise ValueError(
            f"Adapter ID '{adapter_id}' is already registered "
            f"with {_ADAPTER_REGISTRY[adapter_id]!r}; cannot re-register "
            f"with {adapter_cls!r}."
        )

    _ADAPTER_REGISTRY[adapter_id] = adapter_cls


def get_adapter_class(adapter_id: str) -> Type[BaseAdapter]:
    """
    Retrieve a registered adapter class by its canonical adapter_id.
    Raises KeyError if the adapter_id is not registered.
    """
    return _ADAPTER_REGISTRY[adapter_id]


def list_adapters() -> Dict[str, Type[BaseAdapter]]:
    """
    Return a shallow copy of the current adapter registry.

    This is useful for:
    - Runtime discovery
    - Diagnostics
    - Governance inspection
    """
    return dict(_ADAPTER_REGISTRY)
