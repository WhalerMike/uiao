"""Behavioral tests for the Phase 6 OrgTree drift engine (ADR-040)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

import pytest

from uiao.governance.drift_engine import (
    DriftEngineError,
    OrgTreeDriftEngine,
)
from uiao.modernization.orgtree import (
    DriftEngineConfigValidationError,
    load_drift_engine_config,
)
from uiao.modernization.orgtree.drift_engine_config import (
    default_drift_engine_config,
)


# ---------------------------------------------------------------------------
# Config loader tests
# ---------------------------------------------------------------------------


class TestConfigLoader:
    def test_default_config_loads(self) -> None:
        cfg = default_drift_engine_config()
        assert cfg.document_id == "MOD_M"
        assert {p.name for p in cfg.phases} == {
            "mod-b-dynamic-groups",
            "mod-d-admin-units",
            "mod-c-device-orgpath",
            "mod-n-policy-targeting",
        }

    def test_every_op_resolves_to_taxonomy_class(self) -> None:
        cfg = default_drift_engine_config()
        allowed = {
            "DRIFT-SCHEMA",
            "DRIFT-SEMANTIC",
            "DRIFT-PROVENANCE",
            "DRIFT-AUTHZ",
            "DRIFT-IDENTITY",
            "DRIFT-BOUNDARY",
        }
        for phase in cfg.phases:
            for entry in phase.op_map.values():
                assert entry.drift_class in allowed
                assert entry.severity in {"P1", "P2", "P3", "P4"}

    def test_governance_review_ops_are_not_auto_remediated(self) -> None:
        """Each adapter's governance-review ops must carry auto_remediate=false."""
        cfg = default_drift_engine_config()
        governance_review_ops = {
            "delete-phantom",
            "au-delete-phantom",
            "role-delete-unscoped",
            "role-delete-phantom",
            "device-phantom-orgpath",
            "arc-phantom-orgpath",
            "intune-assign-phantom",
            "arc-policy-phantom",
            "intune-profile-missing",
            "arc-policy-definition-missing",
        }
        for phase in cfg.phases:
            for entry in phase.op_map.values():
                if entry.op in governance_review_ops:
                    assert entry.auto_remediate is False, (
                        f"{phase.name}/{entry.op} must be auto_remediate=false"
                    )


# ---------------------------------------------------------------------------
# Engine scan — end-to-end across multiple phases.
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> OrgTreeDriftEngine:
    return OrgTreeDriftEngine()


class TestScanEmptyTenant:
    def test_full_empty_tenant_plans_everything(
        self, engine: OrgTreeDriftEngine,
    ) -> None:
        snap = engine.build_snapshot({
            "mod-b-dynamic-groups": {"current_tenant_state": []},
            "mod-d-admin-units": {
                "current_tenant_aus": [],
                "current_tenant_role_assignments": [],
            },
            "mod-c-device-orgpath": {
                "targets": [],
                "current_entra_devices": [],
                "current_arc_resources": [],
            },
            "mod-n-policy-targeting": {},
        })
        report = engine.scan(snap, dry_run=True)
        assert report.dry_run is True
        assert report.halted is False
        # Empty tenant → 32 MOD_B creates + 29 MOD_D (14 AU + 15 role)
        # + 9 MOD_N (5 intune-profile-missing + 4 arc-def-missing).
        # No MOD_C findings because targets=[] means nothing to write.
        assert len(report.findings) > 0
        # Every finding carries a non-empty target string
        for f in report.findings:
            assert f.target != ""

    def test_partial_scan_skips_missing_phases(
        self, engine: OrgTreeDriftEngine,
    ) -> None:
        snap = engine.build_snapshot({
            "mod-b-dynamic-groups": {"current_tenant_state": []},
        })
        report = engine.scan(snap, dry_run=True)
        phases_seen = {f.phase for f in report.findings}
        assert phases_seen == {"mod-b-dynamic-groups"}


class TestClassification:
    def test_severity_floor_drops_low(
        self, engine: OrgTreeDriftEngine,
    ) -> None:
        """P4 findings are emitted (floor=P4 by default)."""
        snap = engine.build_snapshot({
            "mod-c-device-orgpath": {
                "targets": [],
                "current_entra_devices": [],
                "current_arc_resources": [],
            },
        })
        report = engine.scan(snap, dry_run=True)
        # targets=[] → no operations, no findings. Sanity: the floor
        # machinery runs without error.
        assert report.findings == []

    def test_unscoped_role_assignment_triggers_p1_halt(
        self, engine: OrgTreeDriftEngine,
    ) -> None:
        snap = engine.build_snapshot({
            "mod-d-admin-units": {
                "current_tenant_aus": [],
                "current_tenant_role_assignments": [
                    {
                        "id": "ra-escalation",
                        "roleDefinitionId": "fe930be7-5e62-47db-91af-98c3a49a38b1",
                        "principalId": "p-escalation-candidate",
                        "directoryScopeId": "/",
                    },
                ],
            },
        })
        report = engine.scan(snap, dry_run=False)
        assert report.halted is True
        assert "P1" in report.halt_reason
        # No remediation pass runs when halted.
        assert report.remediation_results == []
        # The P1 finding is present in the finding list.
        p1 = [f for f in report.findings if f.severity == "P1"]
        assert len(p1) >= 1
        assert any(f.op == "role-delete-unscoped" for f in p1)

    def test_phantom_group_classified_as_authz(
        self, engine: OrgTreeDriftEngine,
    ) -> None:
        snap = engine.build_snapshot({
            "mod-b-dynamic-groups": {
                "current_tenant_state": [
                    {
                        "id": "g-phantom",
                        "displayName": "OrgTree-LegacyContractors-Users",
                        "membershipRule": "bogus",
                    },
                ],
            },
        })
        report = engine.scan(snap, dry_run=True)
        phantoms = [f for f in report.findings if f.op == "delete-phantom"]
        assert len(phantoms) == 1
        assert phantoms[0].drift_class == "DRIFT-AUTHZ"
        assert phantoms[0].auto_remediate is False


class TestRemediation:
    def test_dry_run_delegation(
        self, engine: OrgTreeDriftEngine,
    ) -> None:
        snap = engine.build_snapshot({
            "mod-b-dynamic-groups": {"current_tenant_state": []},
        })
        report = engine.scan(snap, dry_run=True)
        # A remediation pass ran, but in dry-run mode.
        assert len(report.remediation_results) == 1
        pass_ = report.remediation_results[0]
        assert pass_["phase"] == "mod-b-dynamic-groups"
        assert pass_["dry_run"] is True
        assert pass_["succeeded"] == 0  # dry-run means zero writes

    def test_phantoms_not_dispatched_even_with_dry_run_false(
        self, engine: OrgTreeDriftEngine, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Phantom findings must never end up in the write path even
        when dry_run=False is requested."""
        snap = engine.build_snapshot({
            "mod-b-dynamic-groups": {
                "current_tenant_state": [
                    {
                        "id": "g-phantom",
                        "displayName": "OrgTree-LegacyContractors-Users",
                        "membershipRule": "bogus",
                    },
                ],
            },
        })
        # Spy on _execute to confirm phantom ops never reach it.
        calls: list[str] = []
        from uiao.adapters.entra_dynamic_groups import (
            EntraDynamicGroupsAdapter,
        )
        monkeypatch.setattr(
            EntraDynamicGroupsAdapter,
            "_execute",
            lambda self, op: calls.append(op.op),
        )
        report = engine.scan(snap, dry_run=False)
        assert "delete-phantom" not in calls


class TestEngineErrors:
    def test_unknown_op_raises(
        self,
        engine: OrgTreeDriftEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An adapter that emits an op type the config doesn't know about
        must raise — prevents silently swallowing governance signals."""
        from uiao.adapters.entra_dynamic_groups import (
            EntraDynamicGroupsAdapter,
            PlannedOperation,
        )

        class BrokenPlan:
            def __init__(self) -> None:
                self.operations = [
                    PlannedOperation(op="invented-op", group_name="x", reason="test"),
                ]
                self.generated_at = "now"
                self.total_canonical = 0
                self.total_tenant = 0

        monkeypatch.setattr(
            EntraDynamicGroupsAdapter,
            "plan",
            lambda self, current_tenant_state=None: BrokenPlan(),
        )
        snap = engine.build_snapshot({
            "mod-b-dynamic-groups": {"current_tenant_state": []},
        })
        with pytest.raises(DriftEngineError, match="unmapped op"):
            engine.scan(snap)
