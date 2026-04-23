"""Behavioral + contract tests for the entra-policy-targeting adapter (ADR-039)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from uiao.adapters.entra_policy_targeting import (
    OP_ARC_POLICY_CREATE,
    OP_ARC_POLICY_DEF_MISSING,
    OP_ARC_POLICY_UPDATE,
    OP_INTUNE_ASSIGN_CREATE,
    OP_INTUNE_ASSIGN_UPDATE,
    OP_INTUNE_PROFILE_MISSING,
    EntraPolicyTargetingAdapter,
)
from uiao.modernization.orgtree import (
    PolicyTargetingValidationError,
    load_policy_targeting_canon,
)
from uiao.modernization.orgtree.policy_targets import (
    default_policy_targeting_canon,
)


TENANT_FIXTURE = Path(__file__).parent / "fixtures" / "contract" / "entra-id" / "policy-targeting" / "tenant-state.json"


@pytest.fixture
def tenant() -> dict:
    return json.loads(TENANT_FIXTURE.read_text())


@pytest.fixture
def adapter() -> EntraPolicyTargetingAdapter:
    return EntraPolicyTargetingAdapter(config={"tenant_id": "contoso.onmicrosoft.com"})


class TestCanonIntegrity:
    def test_default_canon_loads(self) -> None:
        c = default_policy_targeting_canon()
        assert c.document_id == "MOD_N"
        assert len(c.intune_assignments) == 5
        assert len(c.arc_policy_assignments) == 4

    def test_every_intune_target_group_resolves_to_mod_b(self) -> None:
        from uiao.modernization.orgtree.dynamic_groups import (
            default_dynamic_group_library,
        )

        canon = default_policy_targeting_canon()
        groups = default_dynamic_group_library()
        for a in canon.intune_assignments:
            assert a.target_group in groups.names

    def test_every_arc_selector_prefix_is_codebook_recognised(self) -> None:
        from uiao.modernization.orgtree import load_codebook

        canon = default_policy_targeting_canon()
        codebook = load_codebook()
        for name, a in canon.arc_policy_assignments.items():
            prefix = a.orgpath_selector.prefix
            assert prefix == "ORG" or codebook.is_active(prefix), f"{name} prefix {prefix} not in codebook"


class TestCanonValidation:
    def _good_yaml(self) -> str:
        return textwrap.dedent("""\
            schema_version: "1.0.0"
            document_id: MOD_N
            parent_canon: UIAO_007
            intune_assignments:
              - profile_ref:
                  kind: configurationPolicy
                  match_by: displayName
                  value: Intune-Something
                target_group: OrgTree-IT-Users
                intent: include
                purpose: Baseline for IT
            arc_policy_assignments:
              - assignment_name: OrgTree-IT-Baseline
                policy_definition:
                  match_by: displayName
                  value: Azure-Arc-Baseline
                orgpath_selector:
                  prefix: ORG-IT
                  match_mode: startsWith
                purpose: baseline for IT Arc machines
        """)

    def test_baseline_valid(self, tmp_path: Path) -> None:
        p = tmp_path / "ok.yaml"
        p.write_text(self._good_yaml())
        load_policy_targeting_canon(p)

    def test_rejects_intune_target_group_not_in_mod_b(self, tmp_path: Path) -> None:
        bad = self._good_yaml().replace(
            "target_group: OrgTree-IT-Users",
            "target_group: OrgTree-Ghost-Admins",
        )
        p = tmp_path / "bad.yaml"
        p.write_text(bad)
        with pytest.raises(PolicyTargetingValidationError, match="MOD_B"):
            load_policy_targeting_canon(p)

    def test_rejects_arc_prefix_not_in_codebook(self, tmp_path: Path) -> None:
        bad = self._good_yaml().replace(
            "prefix: ORG-IT",
            "prefix: ORG-GHOST",
        )
        p = tmp_path / "bad.yaml"
        p.write_text(bad)
        with pytest.raises(PolicyTargetingValidationError, match="not an active OrgPath"):
            load_policy_targeting_canon(p)

    def test_rejects_duplicate_arc_assignment_name(self, tmp_path: Path) -> None:
        # Build a file with two arc entries sharing the same assignment_name.
        bad = textwrap.dedent("""\
            schema_version: "1.0.0"
            document_id: MOD_N
            parent_canon: UIAO_007
            intune_assignments: []
            arc_policy_assignments:
              - assignment_name: OrgTree-IT-Baseline
                policy_definition:
                  match_by: displayName
                  value: Azure-Arc-Baseline
                orgpath_selector:
                  prefix: ORG-IT
                  match_mode: startsWith
                purpose: first
              - assignment_name: OrgTree-IT-Baseline
                policy_definition:
                  match_by: displayName
                  value: Azure-Arc-Other
                orgpath_selector:
                  prefix: ORG-IT
                  match_mode: equals
                purpose: duplicate
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(bad)
        with pytest.raises(PolicyTargetingValidationError, match="Duplicate"):
            load_policy_targeting_canon(p)


class TestPlan:
    def test_empty_tenant_plans_everything_as_missing(
        self,
        adapter: EntraPolicyTargetingAdapter,
    ) -> None:
        plan = adapter.plan()
        # 5 Intune profiles all missing + 4 Arc definitions all unresolvable
        assert len(plan.by_op(OP_INTUNE_PROFILE_MISSING)) == 5
        assert len(plan.by_op(OP_ARC_POLICY_DEF_MISSING)) == 4

    def test_fixture_produces_expected_mix(
        self,
        adapter: EntraPolicyTargetingAdapter,
        tenant: dict,
    ) -> None:
        plan = adapter.plan(
            current_intune_profiles=tenant["intuneProfiles"],
            current_intune_assignments=tenant["intuneAssignmentsByProfileId"],
            current_arc_assignments=tenant["arcAssignments"],
            group_id_resolver=tenant["groupIdResolver"],
            arc_definition_id_resolver=tenant["arcDefinitionIdResolver"],
        )
        # Intune: baseline aligned; unmanaged has intent drift (canon exclude,
        # tenant include); 3 others need create.
        assert len(plan.by_op(OP_INTUNE_ASSIGN_CREATE)) == 3
        assert len(plan.by_op(OP_INTUNE_ASSIGN_UPDATE)) == 1
        assert len(plan.by_op(OP_INTUNE_PROFILE_MISSING)) == 0

        # Arc: IT-Infra-Baseline aligned; FIN has parameter drift; two missing.
        assert len(plan.by_op(OP_ARC_POLICY_CREATE)) == 2
        assert len(plan.by_op(OP_ARC_POLICY_UPDATE)) == 1
        assert len(plan.by_op(OP_ARC_POLICY_DEF_MISSING)) == 0

    def test_unmanaged_intent_drift_detected(
        self,
        adapter: EntraPolicyTargetingAdapter,
        tenant: dict,
    ) -> None:
        plan = adapter.plan(
            current_intune_profiles=tenant["intuneProfiles"],
            current_intune_assignments=tenant["intuneAssignmentsByProfileId"],
            group_id_resolver=tenant["groupIdResolver"],
            arc_definition_id_resolver=tenant["arcDefinitionIdResolver"],
        )
        updates = plan.by_op(OP_INTUNE_ASSIGN_UPDATE)
        assert len(updates) == 1
        assert "Intune-Unmanaged-Exclusion" in updates[0].target
        assert "Intent drift" in updates[0].reason

    def test_arc_parameter_drift_detected(
        self,
        adapter: EntraPolicyTargetingAdapter,
        tenant: dict,
    ) -> None:
        plan = adapter.plan(
            current_arc_assignments=tenant["arcAssignments"],
            arc_definition_id_resolver=tenant["arcDefinitionIdResolver"],
        )
        updates = plan.by_op(OP_ARC_POLICY_UPDATE)
        assert len(updates) == 1
        assert updates[0].target == "OrgTree-FIN-Data-Residency"
        assert "orgPathPrefix drift" in updates[0].reason


class TestApply:
    def test_dry_run_never_writes(
        self,
        adapter: EntraPolicyTargetingAdapter,
        tenant: dict,
    ) -> None:
        plan = adapter.plan(
            current_intune_profiles=tenant["intuneProfiles"],
            current_intune_assignments=tenant["intuneAssignmentsByProfileId"],
            current_arc_assignments=tenant["arcAssignments"],
            group_id_resolver=tenant["groupIdResolver"],
            arc_definition_id_resolver=tenant["arcDefinitionIdResolver"],
        )
        report = adapter.apply(plan, dry_run=True)
        assert report.dry_run is True
        assert report.succeeded == 0
        assert report.failed == 0
        statuses = {r.status for r in report.results}
        assert statuses == {"skipped-dry-run"}

    def test_governance_review_never_auto_applied(
        self,
        adapter: EntraPolicyTargetingAdapter,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Empty tenant: all canonical profiles/definitions missing —
        # pure governance-review surface.
        plan = adapter.plan()
        executed: list[str] = []
        monkeypatch.setattr(adapter, "_execute", lambda op: executed.append(op.op))
        report = adapter.apply(plan, dry_run=False)
        assert executed == []
        statuses = {r.status for r in report.results}
        assert statuses == {"skipped-manual"}


class TestReconcile:
    def test_reconcile_returns_plan_and_report(
        self,
        adapter: EntraPolicyTargetingAdapter,
        tenant: dict,
    ) -> None:
        artefact = adapter.reconcile(
            current_intune_profiles=tenant["intuneProfiles"],
            current_intune_assignments=tenant["intuneAssignmentsByProfileId"],
            current_arc_assignments=tenant["arcAssignments"],
            group_id_resolver=tenant["groupIdResolver"],
            arc_definition_id_resolver=tenant["arcDefinitionIdResolver"],
            dry_run=True,
        )
        assert "plan" in artefact and "report" in artefact
        assert artefact["plan"]["total_canonical_intune"] == 5
        assert artefact["plan"]["total_canonical_arc"] == 4
