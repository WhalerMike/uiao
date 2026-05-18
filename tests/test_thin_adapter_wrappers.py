"""Tests for the thin-adapter convenience surface on DatabaseAdapterBase.

UIAO_180 §Adapter delegation specifies that adapters expose
`get_state / set_state / list_changes / apply_change`. The default
implementations raise NotImplementedError; adapters opt in by
overriding.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

from uiao.adapters.database_base import (
    ClaimSet,
    ConnectionProvenance,
    DatabaseAdapterBase,
    DriftReport,
    QueryProvenance,
    SchemaMappingObject,
)


class _MinimalAdapter(DatabaseAdapterBase):
    """The smallest possible adapter that satisfies the abstract base."""

    ADAPTER_ID = "minimal-test-adapter"

    def connect(self) -> ConnectionProvenance:
        return ConnectionProvenance(
            identity="ci",
            auth_method="none",
            endpoint="local",
            tls_version=None,
            mtls_enabled=False,
            timestamp=datetime.now(timezone.utc),
        )

    def discover_schema(self) -> SchemaMappingObject:
        return SchemaMappingObject({}, {}, {}, [], "x")

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        return QueryProvenance({}, "", "h", 0, datetime.now(timezone.utc))

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        return ClaimSet([], "test")

    def detect_drift(self) -> DriftReport:
        return DriftReport(
            "noop",
            "low",
            datetime.now(timezone.utc),
            datetime.now(timezone.utc),
            {},
        )


def test_default_get_state_raises_not_implemented():
    adapter = _MinimalAdapter({})
    with pytest.raises(NotImplementedError, match="minimal-test-adapter"):
        adapter.get_state("u-1")


def test_default_set_state_raises_not_implemented():
    adapter = _MinimalAdapter({})
    with pytest.raises(NotImplementedError):
        adapter.set_state("u-1", {})


def test_default_list_changes_raises_not_implemented():
    adapter = _MinimalAdapter({})
    with pytest.raises(NotImplementedError):
        adapter.list_changes(datetime.now(timezone.utc))


def test_default_apply_change_raises_not_implemented():
    adapter = _MinimalAdapter({})
    with pytest.raises(NotImplementedError):
        adapter.apply_change("u-1", {})


class _OptInAdapter(_MinimalAdapter):
    """Adapter that opts into the thin-adapter surface."""

    ADAPTER_ID = "optin-test-adapter"

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.store: Dict[str, Dict[str, Any]] = {}

    def get_state(self, object_id: str) -> Dict[str, Any]:
        return dict(self.store.get(object_id, {}))

    def set_state(self, object_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.store.setdefault(object_id, {})
        delta = {k: v for k, v in payload.items() if existing.get(k) != v}
        existing.update(payload)
        return delta

    def apply_change(self, object_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_state(object_id, payload)

    def list_changes(self, since_timestamp: datetime) -> List[Dict[str, Any]]:
        return []


def test_opt_in_adapter_satisfies_thin_contract():
    adapter = _OptInAdapter({})
    delta = adapter.set_state("u-1", {"upn": "alice"})
    assert delta == {"upn": "alice"}
    # Idempotency: second set_state with same payload returns empty delta
    delta2 = adapter.set_state("u-1", {"upn": "alice"})
    assert delta2 == {}
    state = adapter.get_state("u-1")
    assert state == {"upn": "alice"}
    assert adapter.list_changes(datetime.now(timezone.utc)) == []
