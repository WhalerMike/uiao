"""Smoke tests for the adapter registry and base contracts."""
import pytest
import asyncio
from adapters import ADAPTER_REGISTRY
from adapters.base_adapter import BaseAdapter


def test_registry_not_empty():
    """At least one adapter must be registered."""
    assert len(ADAPTER_REGISTRY) > 0, "Adapter registry is empty"


def test_all_registered_are_base_adapter_subclasses():
    """Every registered adapter must extend BaseAdapter."""
    for name, cls in ADAPTER_REGISTRY.items():
        assert issubclass(cls, BaseAdapter), f"{name} is not a BaseAdapter subclass"


@pytest.mark.parametrize("adapter_id", list(ADAPTER_REGISTRY.keys()))
def test_adapter_metadata(adapter_id):
    """Each adapter must return valid metadata."""
    cls = ADAPTER_REGISTRY[adapter_id]
    instance = cls()
    meta = instance.get_metadata()
    assert meta.adapter_id == adapter_id
    assert meta.version
    assert meta.certification_level >= 1


@pytest.mark.parametrize("adapter_id", list(ADAPTER_REGISTRY.keys()))
def test_adapter_connect(adapter_id):
    """Each adapter connect() must return bool."""
    cls = ADAPTER_REGISTRY[adapter_id]
    instance = cls()
    result = asyncio.get_event_loop().run_until_complete(instance.connect({}))
    assert isinstance(result, bool)
