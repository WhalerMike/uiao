"""Behavioral + contract tests for the entra-device-orgpath adapter (ADR-038)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from uiao.adapters.entra_device_orgpath import (
    OP_ARC_PHANTOM,
    OP_ARC_TAG_CREATE,
    OP_ARC_TAG_UPDATE,
    OP_DEVICE_EXT_CREATE,
    OP_DEVICE_EXT_UPDATE,
    OP_DEVICE_PHANTOM,
    OP_SKIP_NO_PLANE,
    DeviceOrgPathTarget,
    EntraDeviceOrgPathAdapter,
)
from uiao.modernization.orgtree import (
    DevicePlaneValidationError,
    load_device_plane_registry,
)
from uiao.modernization.orgtree.device_planes import default_device_plane_registry


TENANT_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "contract"
    / "entra-id"
    / "device-orgpath"
    / "tenant-state.json"
)


@pytest.fixture
def tenant_state() -> dict:
    return json.loads(TENANT_FIXTURE.read_text())


@pytest.fixture
def adapter() -> EntraDeviceOrgPathAdapter:
    return EntraDeviceOrgPathAdapter(config={"tenant_id": "contoso.onmicrosoft.com"})


# ---------------------------------------------------------------------------
# Registry integrity
# ---------------------------------------------------------------------------


class TestRegistryIntegrity:
    def test_default_registry_loads(self) -> None:
        reg = default_device_plane_registry()
        assert reg.document_id == "MOD_C"
        # Phase 4 ships extensionAttribute1 and ARM-tag only; app-tag is
        # deferred to Phase 5 per ADR-038.
        assert reg.plane_names == {"extensionAttribute1", "ARM-tag"}
        assert set(reg.skip_dispositions.keys()) == {
            "STAY-AD-DC",
            "DECOMMISSION",
        }

    def test_every_known_disposition_is_covered(self) -> None:
        reg = default_device_plane_registry()
        covered = set(reg.skip_dispositions.keys()) | {
            d for p in reg.planes.values() for d in p.dispositions
        }
        assert {
            "ENTRA-DEVICE",
            "ARC-SERVER",
            "MANAGED-IDENTITY-CANDIDATE",
            "STAY-AD-DEPENDENCY",
            "STAY-AD-DC",
            "DECOMMISSION",
        } <= covered

    def test_arm_tag_regex_tracks_codebook(self) -> None:
        from uiao.modernization.orgtree import load_codebook
        reg = default_device_plane_registry()
        cb = load_codebook()
        assert reg.arm_tag.value_regex == cb.regex


class TestRegistryValidation:
    def _good_yaml(self) -> str:
        return textwrap.dedent("""\
            schema_version: "1.0.0"
            document_id: MOD_C
            parent_canon: UIAO_007
            planes:
              - name: extensionAttribute1
                transport: microsoft-graph
                target_object: directoryObject/device
                http_method: PATCH
                endpoint_template: "/devices/{object_id}"
                body_template:
                  onPremisesExtensionAttributes:
                    extensionAttribute1: "{orgpath}"
                read_endpoint_template: "/devices"
                read_value_path: "onPremisesExtensionAttributes.extensionAttribute1"
                dispositions: [ENTRA-DEVICE]
                description: Client devices
              - name: ARM-tag
                transport: azure-resource-manager
                target_object: Microsoft.HybridCompute/machines
                http_method: PATCH
                endpoint_template: "{arm_resource_id}"
                body_template:
                  tags:
                    OrgPath: "{orgpath}"
                read_endpoint_template: "/subscriptions/{subscription_id}/resources"
                read_value_path: "tags.OrgPath"
                dispositions: [ARC-SERVER, STAY-AD-DEPENDENCY, MANAGED-IDENTITY-CANDIDATE]
                description: Arc resources
            skip_dispositions:
              - { name: STAY-AD-DC, reason: DCs do not migrate }
              - { name: DECOMMISSION, reason: EOL or stale }
            arm_tag:
              key: OrgPath
              key_regex: "^OrgPath$"
              value_regex: "^ORG(-[A-Z0-9]{2,6}){0,4}$"
        """)

    def test_baseline_loads(self, tmp_path: Path) -> None:
        p = tmp_path / "ok.yaml"
        p.write_text(self._good_yaml())
        assert load_device_plane_registry(p) is not None

    def test_rejects_disposition_claimed_twice(self, tmp_path: Path) -> None:
        # Make ARM-tag also claim ENTRA-DEVICE — cross-plane overlap.
        bad = self._good_yaml().replace(
            "dispositions: [ARC-SERVER, STAY-AD-DEPENDENCY, MANAGED-IDENTITY-CANDIDATE]",
            "dispositions: [ENTRA-DEVICE, ARC-SERVER, STAY-AD-DEPENDENCY, MANAGED-IDENTITY-CANDIDATE]",
        )
        p = tmp_path / "bad.yaml"
        p.write_text(bad)
        with pytest.raises(DevicePlaneValidationError, match="claimed by two planes"):
            load_device_plane_registry(p)

    def test_rejects_missing_disposition_coverage(self, tmp_path: Path) -> None:
        bad = self._good_yaml().replace(
            "dispositions: [ARC-SERVER, STAY-AD-DEPENDENCY, MANAGED-IDENTITY-CANDIDATE]",
            "dispositions: [ARC-SERVER]",
        )
        p = tmp_path / "bad.yaml"
        p.write_text(bad)
        with pytest.raises(DevicePlaneValidationError, match="missing coverage"):
            load_device_plane_registry(p)

    def test_rejects_arm_regex_divergent_from_codebook(self, tmp_path: Path) -> None:
        bad = self._good_yaml().replace(
            'value_regex: "^ORG(-[A-Z0-9]{2,6}){0,4}$"',
            'value_regex: "^ORG.*$"',
        )
        p = tmp_path / "bad.yaml"
        p.write_text(bad)
        with pytest.raises(DevicePlaneValidationError, match="canonical MOD_A regex"):
            load_device_plane_registry(p)


# ---------------------------------------------------------------------------
# Adapter planning
# ---------------------------------------------------------------------------


def _target(
    name: str,
    disposition: str,
    orgpath=None,
    entra_device_id=None,
    arc_resource_id=None,
) -> DeviceOrgPathTarget:
    return DeviceOrgPathTarget(
        computer_name=name,
        distinguished_name=f"CN={name},OU=Stuff,DC=contoso,DC=com",
        disposition=disposition,
        orgpath=orgpath,
        entra_device_id=entra_device_id,
        arc_resource_id=arc_resource_id,
    )


class TestPlan:
    def test_empty_tenant_plans_creates(
        self,
        adapter: EntraDeviceOrgPathAdapter,
    ) -> None:
        targets = [
            _target("WKST-IT-01", "ENTRA-DEVICE", "ORG-IT-SEC"),
            _target("SRV-IT-01", "ARC-SERVER", "ORG-IT-INF"),
        ]
        plan = adapter.plan(targets)
        assert plan.total_targets == 2
        assert len(plan.by_op(OP_DEVICE_EXT_CREATE)) == 1
        assert len(plan.by_op(OP_ARC_TAG_CREATE)) == 1

    def test_skip_dispositions_emit_skip_op(
        self,
        adapter: EntraDeviceOrgPathAdapter,
    ) -> None:
        targets = [
            _target("DC-01", "STAY-AD-DC"),
            _target("EOL-01", "DECOMMISSION"),
        ]
        plan = adapter.plan(targets)
        assert len(plan.by_op(OP_SKIP_NO_PLANE)) == 2

    def test_aligned_tenant_produces_no_ops(
        self,
        adapter: EntraDeviceOrgPathAdapter,
    ) -> None:
        targets = [_target("WKST-IT-01", "ENTRA-DEVICE", "ORG-IT-SEC")]
        tenant_devices = [{
            "id": "dev-1",
            "displayName": "WKST-IT-01",
            "onPremisesExtensionAttributes": {"extensionAttribute1": "ORG-IT-SEC"},
        }]
        plan = adapter.plan(targets, current_entra_devices=tenant_devices)
        assert plan.operations == []

    def test_drifted_ext_attr_plans_update(
        self,
        adapter: EntraDeviceOrgPathAdapter,
    ) -> None:
        targets = [_target("WKST-IT-01", "ENTRA-DEVICE", "ORG-IT-SEC")]
        tenant_devices = [{
            "id": "dev-1",
            "displayName": "WKST-IT-01",
            "onPremisesExtensionAttributes": {"extensionAttribute1": "ORG-FIN"},
        }]
        plan = adapter.plan(targets, current_entra_devices=tenant_devices)
        updates = plan.by_op(OP_DEVICE_EXT_UPDATE)
        assert len(updates) == 1
        assert updates[0].canonical_orgpath == "ORG-IT-SEC"
        assert updates[0].current_value == "ORG-FIN"

    def test_phantom_device_never_auto_remediated(
        self,
        adapter: EntraDeviceOrgPathAdapter,
    ) -> None:
        targets = [_target("WKST-BROKEN-01", "ENTRA-DEVICE", "ORG-FIN-AP")]
        tenant_devices = [{
            "id": "dev-broken",
            "displayName": "WKST-BROKEN-01",
            "onPremisesExtensionAttributes": {"extensionAttribute1": "org-fin-ap"},
        }]
        plan = adapter.plan(targets, current_entra_devices=tenant_devices)
        phantoms = plan.by_op(OP_DEVICE_PHANTOM)
        assert len(phantoms) == 1
        assert phantoms[0].current_value == "org-fin-ap"

    def test_fixture_produces_expected_mix(
        self,
        adapter: EntraDeviceOrgPathAdapter,
        tenant_state: dict,
    ) -> None:
        targets = [
            _target("WKST-IT-01", "ENTRA-DEVICE", "ORG-IT-SEC"),
            _target("WKST-FIN-01", "ENTRA-DEVICE", "ORG-FIN-AP"),
            _target("WKST-BROKEN-01", "ENTRA-DEVICE", "ORG-FIN-AP"),
            _target("SRV-IT-01", "ARC-SERVER", "ORG-IT-INF"),
            _target("SRV-FIN-01", "ARC-SERVER", "ORG-FIN-AP"),
            _target("SRV-GHOST-01", "ARC-SERVER", "ORG-IT-INF"),
            _target("DC-01", "STAY-AD-DC"),
        ]
        plan = adapter.plan(
            targets,
            current_entra_devices=tenant_state["entraDevices"],
            current_arc_resources=tenant_state["arcResources"],
        )
        # IT-01 aligned; FIN-01 empty ext; BROKEN-01 phantom.
        # SRV-IT-01 aligned; SRV-FIN-01 empty tag; SRV-GHOST-01 phantom.
        # DC-01 skipped.
        assert len(plan.by_op(OP_DEVICE_EXT_CREATE)) == 1  # WKST-FIN-01
        assert len(plan.by_op(OP_DEVICE_PHANTOM)) == 1     # WKST-BROKEN-01
        assert len(plan.by_op(OP_ARC_TAG_CREATE)) == 1     # SRV-FIN-01
        assert len(plan.by_op(OP_ARC_PHANTOM)) == 1        # SRV-GHOST-01
        assert len(plan.by_op(OP_SKIP_NO_PLANE)) == 1      # DC-01


class TestApply:
    def test_dry_run_never_writes(
        self,
        adapter: EntraDeviceOrgPathAdapter,
        tenant_state: dict,
    ) -> None:
        targets = [
            _target("WKST-FIN-01", "ENTRA-DEVICE", "ORG-FIN-AP"),
            _target("SRV-FIN-01", "ARC-SERVER", "ORG-FIN-AP"),
        ]
        plan = adapter.plan(
            targets,
            current_entra_devices=tenant_state["entraDevices"],
            current_arc_resources=tenant_state["arcResources"],
        )
        report = adapter.apply(plan, dry_run=True)
        assert report.dry_run is True
        assert report.succeeded == 0
        statuses = {r.status for r in report.results}
        assert "skipped-dry-run" in statuses
        assert "failed" not in statuses

    def test_governance_review_and_skip_ops_never_auto_applied(
        self,
        adapter: EntraDeviceOrgPathAdapter,
        tenant_state: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        targets = [
            _target("WKST-FIN-01", "ENTRA-DEVICE", "ORG-FIN-AP"),
            _target("WKST-BROKEN-01", "ENTRA-DEVICE", "ORG-FIN-AP"),
            _target("DC-01", "STAY-AD-DC"),
        ]
        plan = adapter.plan(
            targets,
            current_entra_devices=tenant_state["entraDevices"],
        )
        executed: list[str] = []
        monkeypatch.setattr(adapter, "_execute", lambda op: executed.append(op.op))
        report = adapter.apply(plan, dry_run=False)
        # Phantom + skip never dispatched.
        assert OP_DEVICE_PHANTOM not in executed
        assert OP_SKIP_NO_PLANE not in executed
        # Create was dispatched for WKST-FIN-01.
        assert OP_DEVICE_EXT_CREATE in executed
        # Report surfaces the governance/skip ops explicitly.
        statuses = {r.status for r in report.results}
        assert "skipped-manual" in statuses
        assert "skipped-no-plane" in statuses


class TestReconcile:
    def test_reconcile_returns_plan_and_report(
        self,
        adapter: EntraDeviceOrgPathAdapter,
        tenant_state: dict,
    ) -> None:
        targets = [_target("WKST-FIN-01", "ENTRA-DEVICE", "ORG-FIN-AP")]
        artefact = adapter.reconcile(
            targets,
            current_entra_devices=tenant_state["entraDevices"],
            dry_run=True,
        )
        assert "plan" in artefact and "report" in artefact
        assert artefact["report"]["dry_run"] is True
