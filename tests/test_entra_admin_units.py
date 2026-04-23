"""Behavioral + contract tests for the entra-admin-units adapter (ADR-037)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from uiao.adapters.entra_admin_units import (
    OP_AU_CREATE,
    OP_AU_DELETE_PHANTOM,
    OP_AU_UPDATE,
    OP_ROLE_CREATE,
    OP_ROLE_DELETE_PHANTOM,
    OP_ROLE_DELETE_UNSCOPED,
    EntraAdminUnitsAdapter,
)
from uiao.modernization.orgtree import (
    DelegationMatrixValidationError,
    load_delegation_matrix,
)
from uiao.modernization.orgtree.admin_units import default_delegation_matrix


TENANT_FIXTURE = Path(__file__).parent / "fixtures" / "contract" / "entra-id" / "admin-units" / "tenant-state.json"


@pytest.fixture
def tenant_state() -> dict:
    return json.loads(TENANT_FIXTURE.read_text())


@pytest.fixture
def adapter() -> EntraAdminUnitsAdapter:
    return EntraAdminUnitsAdapter(config={"tenant_id": "contoso.onmicrosoft.com"})


class TestMatrixIntegrity:
    def test_default_matrix_loads(self) -> None:
        m = default_delegation_matrix()
        assert m.document_id == "MOD_D"
        # 1 enterprise + 6 division + 7 department = 14
        assert len(m.administrative_units) == 14
        assert len(m.roles) == 8
        assert len(m.admin_groups) == 8
        assert len(m.role_assignments) == 15

    def test_every_au_renders_restricted_graph_body(self) -> None:
        m = default_delegation_matrix()
        for au in m.administrative_units.values():
            body = au.to_graph_body()
            assert body["displayName"] == au.name
            assert body["isMemberManagementRestricted"] is True
            assert body["membershipType"] == "Dynamic"
            assert body["membershipRuleProcessingState"] == "On"
            assert body["membershipRule"] == au.membership_rule

    def test_every_au_orgpath_ref_quoted_in_rule(self) -> None:
        m = default_delegation_matrix()
        for au in m.administrative_units.values():
            for code in au.orgpath_refs:
                assert f'"{code}"' in au.membership_rule

    def test_every_role_assignment_principal_resolves(self) -> None:
        from uiao.modernization.orgtree.dynamic_groups import (
            default_dynamic_group_library,
        )

        m = default_delegation_matrix()
        dg = default_dynamic_group_library()
        for ra in m.role_assignments:
            principal = ra.principal_group
            assert principal in dg.names or principal in m.admin_group_names, (
                f"assignment {ra.key()} principal_group {principal} not in MOD_B dynamic groups OR MOD_D admin_groups"
            )

    def test_every_role_assignment_au_exists(self) -> None:
        m = default_delegation_matrix()
        for ra in m.role_assignments:
            assert ra.au_scope in m.au_names

    def test_every_role_assignment_role_exists(self) -> None:
        m = default_delegation_matrix()
        for ra in m.role_assignments:
            assert ra.role in {r.display_name for r in m.roles.values()}


class TestMatrixValidation:
    def _good_yaml(self) -> str:
        # Minimal valid YAML for boundary tests. Uses real codebook +
        # real MOD_B group name so cross-canon references resolve.
        return textwrap.dedent("""\
            schema_version: "1.0.0"
            document_id: MOD_D
            parent_canon: UIAO_007
            naming:
              au_prefix: "AU-ORG"
              au_regex: "^AU-ORG(-[A-Za-z0-9]+)*$"
              admin_group_regex: "^OrgTree-[A-Za-z0-9]+(-[A-Za-z0-9]+)*-Admins$"
            administrative_units:
              - name: AU-ORG-IT
                tier: division
                membership_rule: '(user.extensionAttribute1 -startsWith "ORG-IT")'
                orgpath_refs: [ORG-IT]
                restricted: true
                description: IT division
            roles:
              - display_name: Global Reader
                template_id: f2ef992c-3afb-46b9-b7cf-a126ee74c451
            admin_groups: []
            role_assignments:
              - role: Global Reader
                principal_group: OrgTree-IT-Users
                au_scope: AU-ORG-IT
                tier: tier-2
                purpose: IT read-all
        """)

    def test_baseline_fixture_is_valid(self, tmp_path: Path) -> None:
        p = tmp_path / "ok.yaml"
        p.write_text(self._good_yaml())
        m = load_delegation_matrix(p)
        assert "AU-ORG-IT" in m.au_names

    def test_rejects_unknown_orgpath_ref(self, tmp_path: Path) -> None:
        bad = (
            self._good_yaml()
            .replace("orgpath_refs: [ORG-IT]", "orgpath_refs: [ORG-GHOST]")
            .replace('-startsWith "ORG-IT"', '-startsWith "ORG-GHOST"')
        )
        p = tmp_path / "bad.yaml"
        p.write_text(bad)
        with pytest.raises(DelegationMatrixValidationError, match="unknown OrgPath"):
            load_delegation_matrix(p)

    def test_rejects_rule_not_quoting_ref(self, tmp_path: Path) -> None:
        bad = self._good_yaml().replace(
            '(user.extensionAttribute1 -startsWith "ORG-IT")',
            '(user.extensionAttribute1 -startsWith "ORG-FIN")',
        )
        p = tmp_path / "bad.yaml"
        p.write_text(bad)
        with pytest.raises(DelegationMatrixValidationError, match="does not quote"):
            load_delegation_matrix(p)

    def test_rejects_assignment_to_unknown_au(self, tmp_path: Path) -> None:
        bad = self._good_yaml().replace("au_scope: AU-ORG-IT", "au_scope: AU-ORG-NOWHERE", 1)
        # Keep the AU definition itself untouched so only the assignment
        # points at a non-existent AU.
        p = tmp_path / "bad.yaml"
        p.write_text(bad)
        with pytest.raises(DelegationMatrixValidationError, match="unknown AU"):
            load_delegation_matrix(p)

    def test_rejects_assignment_to_unknown_principal(self, tmp_path: Path) -> None:
        bad = self._good_yaml().replace(
            "principal_group: OrgTree-IT-Users",
            "principal_group: OrgTree-Ghost-Admins",
        )
        p = tmp_path / "bad.yaml"
        p.write_text(bad)
        with pytest.raises(DelegationMatrixValidationError, match="principal_group"):
            load_delegation_matrix(p)


class TestPlan:
    def test_empty_tenant_plans_full_create(self, adapter: EntraAdminUnitsAdapter) -> None:
        plan = adapter.plan(
            current_tenant_aus=[],
            current_tenant_role_assignments=[],
        )
        assert plan.total_canonical_aus == 14
        assert plan.total_canonical_assignments == 15
        assert len(plan.by_op(OP_AU_CREATE)) == 14
        assert len(plan.by_op(OP_AU_UPDATE)) == 0
        assert len(plan.by_op(OP_AU_DELETE_PHANTOM)) == 0
        assert len(plan.by_op(OP_ROLE_CREATE)) == 15

    def test_fixture_produces_expected_ops(
        self,
        adapter: EntraAdminUnitsAdapter,
        tenant_state: dict,
    ) -> None:
        plan = adapter.plan(
            current_tenant_aus=tenant_state["administrativeUnits"],
            current_tenant_role_assignments=tenant_state["roleAssignments"],
        )
        # Fixture tenant: 1 aligned (FIN), 1 rule-drift (IT), 1 unrestricted (HR), 1 phantom
        assert plan.total_tenant_aus == 4
        assert len(plan.by_op(OP_AU_UPDATE)) == 2  # IT (rule), HR (restricted)
        assert len(plan.by_op(OP_AU_DELETE_PHANTOM)) == 1  # LegacyOffshore
        creates = plan.by_op(OP_AU_CREATE)
        create_names = {o.target for o in creates}
        assert "AU-ORG-FIN" not in create_names  # already aligned
        assert "AU-ORG-IT" not in create_names  # exists, needs update
        assert "AU-ORG-HR" not in create_names  # exists, needs restriction fix
        # 14 canonical - 3 already present = 11 creates
        assert len(creates) == 11

        unscoped = plan.by_op(OP_ROLE_DELETE_UNSCOPED)
        phantoms = plan.by_op(OP_ROLE_DELETE_PHANTOM)
        assert len(unscoped) == 1
        assert len(phantoms) == 1

    def test_non_aurg_tenant_aus_are_ignored(self, adapter: EntraAdminUnitsAdapter) -> None:
        plan = adapter.plan(
            current_tenant_aus=[
                {"id": "x", "displayName": "LegalOps-AU", "membershipRule": ""},
            ],
            current_tenant_role_assignments=[],
        )
        assert plan.total_tenant_aus == 0


class TestApply:
    def test_dry_run_never_writes(
        self,
        adapter: EntraAdminUnitsAdapter,
        tenant_state: dict,
    ) -> None:
        plan = adapter.plan(
            current_tenant_aus=tenant_state["administrativeUnits"],
            current_tenant_role_assignments=tenant_state["roleAssignments"],
        )
        report = adapter.apply(plan, dry_run=True)
        assert report.dry_run is True
        assert report.succeeded == 0
        assert report.failed == 0
        statuses = {r.status for r in report.results}
        assert statuses == {"skipped-dry-run", "skipped-manual"}

    def test_governance_review_ops_never_auto_applied(
        self,
        adapter: EntraAdminUnitsAdapter,
        tenant_state: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        plan = adapter.plan(
            current_tenant_aus=tenant_state["administrativeUnits"],
            current_tenant_role_assignments=tenant_state["roleAssignments"],
        )
        executed: list[str] = []
        monkeypatch.setattr(adapter, "_execute", lambda op: executed.append(op.op))
        report = adapter.apply(plan, dry_run=False)
        # None of the governance-review ops were dispatched.
        assert OP_AU_DELETE_PHANTOM not in executed
        assert OP_ROLE_DELETE_UNSCOPED not in executed
        assert OP_ROLE_DELETE_PHANTOM not in executed
        # But create / update did get dispatched.
        assert OP_AU_CREATE in executed
        assert OP_AU_UPDATE in executed
        # The governance-review ops show as skipped-manual in results.
        manual = [r for r in report.results if r.status == "skipped-manual"]
        assert len(manual) == 3  # 1 au-phantom + 1 unscoped + 1 phantom role


class TestReconcile:
    def test_reconcile_returns_plan_and_report(
        self,
        adapter: EntraAdminUnitsAdapter,
        tenant_state: dict,
    ) -> None:
        artefact = adapter.reconcile(
            current_tenant_aus=tenant_state["administrativeUnits"],
            current_tenant_role_assignments=tenant_state["roleAssignments"],
            dry_run=True,
        )
        assert "plan" in artefact and "report" in artefact
        assert artefact["report"]["dry_run"] is True
        assert artefact["plan"]["total_canonical_aus"] == 14
