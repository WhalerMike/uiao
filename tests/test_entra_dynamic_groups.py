"""Behavioral + contract tests for the entra-dynamic-groups adapter (ADR-036)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from uiao.adapters.entra_dynamic_groups import (
    OP_CREATE,
    OP_DELETE_PHANTOM,
    OP_UPDATE,
    EntraDynamicGroupsAdapter,
)
from uiao.modernization.orgtree import (
    DynamicGroupValidationError,
    load_codebook,
    load_dynamic_group_library,
)
from uiao.modernization.orgtree.dynamic_groups import default_dynamic_group_library


TENANT_FIXTURE = Path(__file__).parent / "fixtures" / "contract" / "entra-id" / "dynamic-groups" / "tenant-state.json"


@pytest.fixture
def tenant_state() -> list[dict]:
    return json.loads(TENANT_FIXTURE.read_text())["value"]


@pytest.fixture
def adapter() -> EntraDynamicGroupsAdapter:
    return EntraDynamicGroupsAdapter(config={"tenant_id": "contoso.onmicrosoft.com"})


class TestLibraryIntegrity:
    """Every canonical group must round-trip through schema + integrity."""

    def test_default_library_loads(self) -> None:
        lib = default_dynamic_group_library()
        assert lib.document_id == "MOD_B"
        assert len(lib.groups) == 32
        assert lib.naming_regex.startswith("^OrgTree-")

    def test_every_group_name_matches_naming_regex(self) -> None:
        lib = default_dynamic_group_library()
        for name in lib.names:
            assert lib.matches_naming(name), f"{name} violates naming regex"

    def test_every_orgpath_ref_is_active_in_codebook(self) -> None:
        lib = default_dynamic_group_library()
        codebook = load_codebook()
        for code in lib.referenced_codes():
            assert codebook.is_active(code), f"{code} not in active codebook"

    def test_every_ref_appears_verbatim_in_rule(self) -> None:
        lib = default_dynamic_group_library()
        for spec in lib.groups.values():
            for code in spec.orgpath_refs:
                assert f'"{code}"' in spec.rule, f"{spec.name} references {code} but rule does not quote it"

    def test_every_spec_renders_valid_graph_body(self) -> None:
        lib = default_dynamic_group_library()
        for spec in lib.groups.values():
            body = spec.to_graph_body()
            assert body["displayName"] == spec.name
            assert body["mailEnabled"] is False
            assert body["securityEnabled"] is True
            assert body["groupTypes"] == ["DynamicMembership"]
            assert body["membershipRule"] == spec.rule
            assert body["membershipRuleProcessingState"] == "On"


class TestLibraryValidation:
    def test_rejects_unknown_orgpath_reference(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text(
            textwrap.dedent("""\
            schema_version: "1.0.0"
            document_id: MOD_B
            parent_canon: UIAO_007
            naming:
              prefix: "OrgTree-"
              regex: "^OrgTree-[A-Za-z0-9]+(-[A-Za-z0-9]+)*-(Users|Licensed|CA|Admins)$"
              purpose_suffixes: [Users]
            groups:
              - name: OrgTree-GHOST-Users
                category: level-1-division
                rule: '(user.extensionAttribute1 -startsWith "ORG-GHOST")'
                orgpath_refs: [ORG-GHOST]
                description: Ghost group
        """)
        )
        with pytest.raises(DynamicGroupValidationError, match="unknown OrgPath"):
            load_dynamic_group_library(bad)

    def test_rejects_rule_that_does_not_quote_ref(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text(
            textwrap.dedent("""\
            schema_version: "1.0.0"
            document_id: MOD_B
            parent_canon: UIAO_007
            naming:
              prefix: "OrgTree-"
              regex: "^OrgTree-[A-Za-z0-9]+(-[A-Za-z0-9]+)*-(Users|Licensed|CA|Admins)$"
              purpose_suffixes: [Users]
            groups:
              - name: OrgTree-IT-Users
                category: level-1-division
                rule: '(user.extensionAttribute1 -startsWith "ORG-FIN")'
                orgpath_refs: [ORG-IT]
                description: IT users (but rule points at Finance)
        """)
        )
        with pytest.raises(DynamicGroupValidationError, match="does not quote"):
            load_dynamic_group_library(bad)

    def test_rejects_duplicate_group_name(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text(
            textwrap.dedent("""\
            schema_version: "1.0.0"
            document_id: MOD_B
            parent_canon: UIAO_007
            naming:
              prefix: "OrgTree-"
              regex: "^OrgTree-[A-Za-z0-9]+(-[A-Za-z0-9]+)*-(Users|Licensed|CA|Admins)$"
              purpose_suffixes: [Users]
            groups:
              - name: OrgTree-IT-Users
                category: level-1-division
                rule: '(user.extensionAttribute1 -startsWith "ORG-IT")'
                orgpath_refs: [ORG-IT]
                description: IT users
              - name: OrgTree-IT-Users
                category: level-1-division
                rule: '(user.extensionAttribute1 -startsWith "ORG-IT")'
                orgpath_refs: [ORG-IT]
                description: duplicate
        """)
        )
        # Schema uniqueItems catches structural dup; loader's _validate_integrity
        # catches semantic dup (same name, different body). Either raises.
        with pytest.raises(DynamicGroupValidationError):
            load_dynamic_group_library(bad)


class TestPlan:
    def test_empty_tenant_plans_full_create(self, adapter: EntraDynamicGroupsAdapter) -> None:
        plan = adapter.plan(current_tenant_state=[])
        assert plan.total_canonical == 32
        assert plan.total_tenant == 0
        assert len(plan.by_op(OP_CREATE)) == 32
        assert len(plan.by_op(OP_UPDATE)) == 0
        assert len(plan.by_op(OP_DELETE_PHANTOM)) == 0

    def test_fixture_tenant_state_produces_expected_operations(
        self,
        adapter: EntraDynamicGroupsAdapter,
        tenant_state: list[dict],
    ) -> None:
        plan = adapter.plan(current_tenant_state=tenant_state)
        # Fixture: 2 aligned (FIN, IT), 1 drifted (IT-SEC), 1 phantom.
        assert plan.total_tenant == 4
        creates = plan.by_op(OP_CREATE)
        updates = plan.by_op(OP_UPDATE)
        phantoms = plan.by_op(OP_DELETE_PHANTOM)
        # 32 canonical - 3 already present (FIN, IT, IT-SEC) = 29 creates
        assert len(creates) == 29
        assert len(updates) == 1
        assert updates[0].group_name == "OrgTree-IT-SEC-Users"
        assert "Rule drift" in updates[0].reason
        assert len(phantoms) == 1
        assert phantoms[0].group_name == "OrgTree-LegacyContractors-Users"

    def test_non_orgtree_groups_are_ignored(self, adapter: EntraDynamicGroupsAdapter) -> None:
        tenant = [
            {"id": "x", "displayName": "Some-Other-Group", "membershipRule": "..."},
        ]
        plan = adapter.plan(current_tenant_state=tenant)
        assert plan.total_tenant == 0  # non-OrgTree- names don't count


class TestApply:
    def test_dry_run_never_writes(
        self,
        adapter: EntraDynamicGroupsAdapter,
        tenant_state: list[dict],
    ) -> None:
        plan = adapter.plan(current_tenant_state=tenant_state)
        report = adapter.apply(plan, dry_run=True)
        assert report.dry_run is True
        assert report.succeeded == 0
        assert report.failed == 0
        # 29 create + 1 update = 30 skipped-dry-run; 1 phantom = skipped-manual
        dry = [r for r in report.results if r.status == "skipped-dry-run"]
        manual = [r for r in report.results if r.status == "skipped-manual"]
        assert len(dry) == 30
        assert len(manual) == 1

    def test_phantom_never_auto_applied_even_without_dry_run(
        self,
        adapter: EntraDynamicGroupsAdapter,
        tenant_state: list[dict],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        plan = adapter.plan(current_tenant_state=tenant_state)
        # Replace _execute with a sentinel so we can assert it is never
        # called for phantom operations.
        called_ops: list[str] = []
        monkeypatch.setattr(adapter, "_execute", lambda op: called_ops.append(op.op))
        report = adapter.apply(plan, dry_run=False)
        assert OP_DELETE_PHANTOM not in called_ops
        # Every create + update was dispatched to _execute.
        assert called_ops.count(OP_CREATE) == 29
        assert called_ops.count(OP_UPDATE) == 1
        phantom_results = [r for r in report.results if r.op == OP_DELETE_PHANTOM]
        assert len(phantom_results) == 1
        assert phantom_results[0].status == "skipped-manual"


class TestReconcile:
    def test_reconcile_dry_run_returns_artefact(
        self,
        adapter: EntraDynamicGroupsAdapter,
        tenant_state: list[dict],
    ) -> None:
        artefact = adapter.reconcile(current_tenant_state=tenant_state, dry_run=True)
        assert "plan" in artefact and "report" in artefact
        assert artefact["report"]["dry_run"] is True
        assert artefact["plan"]["total_tenant"] == 4
