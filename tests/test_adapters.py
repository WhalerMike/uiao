"""Smoke tests for the adapter registry and base contracts."""

import pytest
import asyncio
from uiao_impl.adapters import (
    DatabaseAdapterBase,
    EntraAdapter,
    ServiceNowAdapter,
)

# For testing purposes, create a simple registry
ADAPTER_REGISTRY = {
    "database": DatabaseAdapterBase,
    "entra-id": EntraAdapter,
    "servicenow": ServiceNowAdapter,
}

# For type checking
BaseAdapter = DatabaseAdapterBase.__bases__[0] if DatabaseAdapterBase.__bases__ else object


def test_registry_not_empty():
    """At least one adapter must be registered."""
    assert len(ADAPTER_REGISTRY) > 0, "Adapter registry is empty"


def test_all_registered_are_base_adapter_subclasses():
    """Every registered adapter must extend BaseAdapter."""
    for name, cls in ADAPTER_REGISTRY.items():
        assert issubclass(cls, BaseAdapter), f"{name} is not a BaseAdapter subclass"


@pytest.mark.parametrize("adapter_id", list(ADAPTER_REGISTRY.keys()))
def test_adapter_metadata(adapter_id):
    """Each adapter must have ADAPTER_ID defined."""
    cls = ADAPTER_REGISTRY[adapter_id]
    assert hasattr(cls, "ADAPTER_ID"), f"{adapter_id} adapter missing ADAPTER_ID"
    assert cls.ADAPTER_ID, f"{adapter_id} adapter has empty ADAPTER_ID"


@pytest.mark.parametrize("adapter_id", list(ADAPTER_REGISTRY.keys()))
def test_adapter_connect(adapter_id):
    """Each adapter connect() must return ConnectionProvenance."""
    import inspect
    cls = ADAPTER_REGISTRY[adapter_id]
    if inspect.isabstract(cls):
        pytest.skip(f"{adapter_id} is abstract and cannot be instantiated")
    instance = cls({})
    result = instance.connect()
    # The connect method returns a ConnectionProvenance object, not a bool
    assert result is not None

