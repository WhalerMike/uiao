"""Tests for the Patch State Adapter (conformance / telemetry)."""

from __future__ import annotations
import pytest
from uiao_impl.adapters.patchstate_adapter import PatchStateAdapter
from uiao_impl.adapters.database_base import (
    ClaimSet, ConnectionProvenance, DriftReport, EvidenceObject, SchemaMappingObject,
)


@pytest.fixture
def adapter() -> PatchStateAdapter:
    return PatchStateAdapter({"source": "intune", "endpoint": "https://graph.microsoft.com/beta/deviceManagement"})


class TestBasics:
    def test_adapter_id(self, adapter: PatchStateAdapter) -> None:
        assert adapter.ADAPTER_ID == "patch-state"

    def test_connect(self, adapter: PatchStateAdapter) -> None:
        r = adapter.connect()
        assert isinstance(r, ConnectionProvenance)
        assert "intune" in r.identity

    def test_schema(self, adapter: PatchStateAdapter) -> None:
        assert isinstance(adapter.discover_schema(), SchemaMappingObject)
        assert "missing_patches" in adapter.discover_schema().vendor_schema

    def test_query(self, adapter: PatchStateAdapter) -> None:
        r = adapter.execute_query({"from": "windows-servers"})
        assert "windows-servers" in r.vendor_query

    def test_normalize_empty(self, adapter: PatchStateAdapter) -> None:
        assert len(adapter.normalize([]).claims) == 0

    def test_normalize_device(self, adapter: PatchStateAdapter) -> None:
        raw = [{"device_id": "D-001", "os": "Windows Server 2022", "missing_patches": ["KB123", "KB456"]}]
        r = adapter.normalize(raw)
        assert len(r.claims) == 1
        assert r.claims[0].fields["missing_count"] == 2

    def test_drift(self, adapter: PatchStateAdapter) -> None:
        assert adapter.detect_drift().drift_type == "patch-state-posture"

    def test_evidence(self, adapter: PatchStateAdapter) -> None:
        assert isinstance(adapter.collect_evidence("KSI-SI-02"), EvidenceObject)

    def test_extension_raises(self, adapter: PatchStateAdapter) -> None:
        with pytest.raises(NotImplementedError):
            adapter.get_patch_status()
        with pytest.raises(NotImplementedError):
            adapter.generate_patch_evidence()

    def test_collect_and_align(self, adapter: PatchStateAdapter) -> None:
        r = adapter.collect_and_align()
        assert r["adapter_id"] == "patch-state"
        assert r["metadata"]["source"] == "intune"
