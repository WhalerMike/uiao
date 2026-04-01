from __future__ import annotations

"""
Collector registry and auto-discovery for UIAO-Core evidence collectors.

This module:
- Imports the BaseCollector
- Walks the collectors package to discover concrete collector implementations
- Registers them in a global REGISTRY keyed by collector_id
- Exposes helper functions to retrieve and list collectors
"""

import importlib
import inspect
import pkgutil
from typing import Dict, List, Type

from .base_collector import BaseCollector

# Global registry of collector_id -> collector class
REGISTRY: Dict[str, Type[BaseCollector]] = {}


def _is_concrete_collector(obj: object) -> bool:
    """
    Determine whether the given object is a concrete subclass of BaseCollector.
    """
    return (
        inspect.isclass(obj)
        and issubclass(obj, BaseCollector)
        and obj is not BaseCollector
        and getattr(obj, "COLLECTOR_ID", None) not in (None, "", "base")
    )


def _discover_collectors() -> None:
    """
    Auto-discover and register all collectors under this package.

    This will import all submodules and subpackages, then scan for subclasses
    of BaseCollector that define a non-default COLLECTOR_ID.
    """
    global REGISTRY

    # Walk all submodules under the current package
    for module_info in pkgutil.walk_packages(__path__, prefix=__name__ + "."):
        module_name = module_info.name

        # Skip the base collector module to avoid circular imports
        if module_name.endswith(".base_collector"):
            continue

        try:
            module = importlib.import_module(module_name)
        except Exception:
            # Intentionally swallow import errors to avoid breaking the registry
            # due to optional dependencies. These should be logged by callers.
            continue

        # Inspect module members for concrete collector classes
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if _is_concrete_collector(obj):
                collector_cls: Type[BaseCollector] = obj
                collector_id = getattr(collector_cls, "COLLECTOR_ID", None)
                if not collector_id:
                    continue

                # Avoid accidental overwrites; last one wins if duplicates exist
                REGISTRY[collector_id] = collector_cls


# Perform discovery at import time
_discover_collectors()


def get_collector_class(collector_id: str) -> Type[BaseCollector]:
    """
    Retrieve a collector class by its collector_id.

    Parameters
    ----------
    collector_id:
        Stable identifier of the collector (e.g., 'entra', 'sdwan', 'infoblox').

    Returns
    -------
    Type[BaseCollector]
        The collector class associated with the given ID.

    Raises
    ------
    KeyError
        If no collector is registered under the given ID.
    """
    return REGISTRY[collector_id]


def create_collector(collector_id: str, config: dict) -> BaseCollector:
    """
    Instantiate a collector by ID with the provided configuration.

    Parameters
    ----------
    collector_id:
        Stable identifier of the collector.
    config:
        Configuration dictionary passed to the collector's constructor.

    Returns
    -------
    BaseCollector
        An instance of the requested collector.
    """
    cls = get_collector_class(collector_id)
    return cls(config=config)


def list_collectors() -> List[str]:
    """
    List all registered collector IDs.

    Returns
    -------
    List[str]
        Sorted list of collector identifiers.
    """
    return sorted(REGISTRY.keys())
