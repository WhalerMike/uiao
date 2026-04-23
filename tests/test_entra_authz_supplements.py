"""Tests for the supplemental Entra authorization classifiers (RFC-0026 E4).

Covers :func:`detect_pim_groups_password_reset_escalation` — the
compensating control for GAP-ENT-001 in
``src/uiao/canon/gcc-boundary-gap-registry.yaml``. The classifier must
flag exactly the groups that are both PIM-for-Groups-enrolled *and*
carry a password-reset-capable directory role, while staying silent on
groups that have only one of those properties.

Roadmap reference: ``docs/docs/uiao-rfc-0026-roadmap.md`` (E4.2 / E4.3).
Upstream SCuBA gap: ``cisagov/ScubaGear#2072``.
"""

from __future__ import annotations

import pytest

from uiao.governance.drift import DRIFT_AUTHZ
from uiao.governance.entra_authz_supplements import (
    POLICY_REF_PIM_GROUPS_ESCALATION,
    _PASSWORD_RESET_ESCALATION_ROLES,
    detect_pim_groups_password_reset_escalation,
)
from uiao.ir.models.core import ProvenanceRecord


PROV = ProvenanceRecord(source="test-entra-authz", timestamp="2026-04-23T12:00:00Z", version="0.1.0")


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _state(
    *,
    pim_groups=None,
    assignments=None,
):
    return {
        "pim_for_groups": pim_groups or [],
        "group_role_assignments": assignments or {},
    }


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestDetectPimGroupsPasswordResetEscalation:
    def test_empty_state_returns_empty_list(self) -> None:
        findings = detect_pim_groups_password_reset_escalation({}, provenance=PROV)
        assert findings == []

    def test_pim_enrolled_group_without_risky_role_is_silent(self) -> None:
        findings = detect_pim_groups_password_reset_escalation(
            _state(
                pim_groups=["grp-it-inf"],
                assignments={"grp-it-inf": ["Reports Reader", "Directory Readers"]},
            ),
            provenance=PROV,
        )
        assert findings == []

    def test_risky_role_without_pim_is_silent(self) -> None:
        findings = detect_pim_groups_password_reset_escalation(
            _state(
                pim_groups=[],
                assignments={"grp-helpdesk": ["Helpdesk Administrator"]},
            ),
            provenance=PROV,
        )
        assert findings == []

    @pytest.mark.parametrize("role_name", sorted(_PASSWORD_RESET_ESCALATION_ROLES))
    def test_every_default_risky_role_is_flagged(self, role_name: str) -> None:
        findings = detect_pim_groups_password_reset_escalation(
            _state(
                pim_groups=["grp-escalation"],
                assignments={"grp-escalation": [role_name]},
            ),
            provenance=PROV,
        )
        assert len(findings) == 1
        drift = findings[0]
        assert drift.drift_class == DRIFT_AUTHZ
        assert drift.classification == "unauthorized"
        assert drift.policy_ref == POLICY_REF_PIM_GROUPS_ESCALATION
        assert drift.resource_id == "entra:group:grp-escalation"

    def test_graph_style_role_dict_is_accepted(self) -> None:
        # Entra Graph responses carry role names in roleDefinitionDisplayName
        findings = detect_pim_groups_password_reset_escalation(
            _state(
                pim_groups=["grp-admin"],
                assignments={
                    "grp-admin": [
                        {
                            "roleDefinitionDisplayName": "User Administrator",
                            "principalId": "user-42",
                            "assignmentType": "Eligible",
                        },
                    ],
                },
            ),
            provenance=PROV,
        )
        assert len(findings) == 1
        assert "User Administrator" in findings[0].delta["escalating_roles"]

    def test_multiple_at_risk_groups_produce_multiple_findings(self) -> None:
        findings = detect_pim_groups_password_reset_escalation(
            _state(
                pim_groups=["grp-a", "grp-b", "grp-safe"],
                assignments={
                    "grp-a": ["Password Administrator"],
                    "grp-b": ["Helpdesk Administrator", "Global Reader"],
                    "grp-safe": ["Reports Reader"],
                },
            ),
            provenance=PROV,
        )
        assert {d.resource_id for d in findings} == {
            "entra:group:grp-a",
            "entra:group:grp-b",
        }
        for drift in findings:
            assert drift.classification == "unauthorized"
            assert drift.drift_class == DRIFT_AUTHZ

    def test_pim_groups_as_dict_is_accepted(self) -> None:
        # Upstream adapters may emit pim_for_groups as a dict keyed by group ID
        findings = detect_pim_groups_password_reset_escalation(
            _state(
                pim_groups={
                    "grp-escalation": {"eligible_assignments": [{"principal_id": "u1"}]},
                    "grp-safe": {"eligible_assignments": []},
                },
                assignments={
                    "grp-escalation": ["Global Administrator"],
                    "grp-safe": ["Reports Reader"],
                },
            ),
            provenance=PROV,
        )
        assert [d.resource_id for d in findings] == ["entra:group:grp-escalation"]

    def test_additional_risky_roles_extend_default_set(self) -> None:
        # Agencies can register custom roles that also grant password reset
        findings = detect_pim_groups_password_reset_escalation(
            _state(
                pim_groups=["grp-custom"],
                assignments={"grp-custom": ["Agency Custom Pwd Admin"]},
            ),
            provenance=PROV,
            additional_risky_roles=["Agency Custom Pwd Admin"],
        )
        assert len(findings) == 1
        assert findings[0].resource_id == "entra:group:grp-custom"

    def test_delta_records_all_roles_and_escalating_subset(self) -> None:
        findings = detect_pim_groups_password_reset_escalation(
            _state(
                pim_groups=["grp-mixed"],
                assignments={
                    "grp-mixed": [
                        "Reports Reader",
                        "Password Administrator",
                        "Directory Readers",
                    ],
                },
            ),
            provenance=PROV,
        )
        assert len(findings) == 1
        delta = findings[0].delta
        # Escalating subset contains only the risky role
        assert delta["escalating_roles"] == ["Password Administrator"]
        # all_roles surface keeps the full assignment for forensic review
        assert set(delta["all_roles"]) == {
            "Reports Reader",
            "Password Administrator",
            "Directory Readers",
        }

    def test_drift_records_hashes_and_is_detected(self) -> None:
        findings = detect_pim_groups_password_reset_escalation(
            _state(
                pim_groups=["grp-x"],
                assignments={"grp-x": ["Password Administrator"]},
            ),
            provenance=PROV,
        )
        drift = findings[0]
        # Hashes must differ since the observed state diverges from the baseline
        assert drift.expected_hash != drift.actual_hash
        assert drift.drift_detected is True

    def test_provenance_is_propagated(self) -> None:
        findings = detect_pim_groups_password_reset_escalation(
            _state(
                pim_groups=["grp-x"],
                assignments={"grp-x": ["Global Administrator"]},
            ),
            provenance=PROV,
        )
        assert findings[0].provenance is PROV


class TestPolicyRefStability:
    def test_policy_ref_matches_gap_registry_compensating_control(self) -> None:
        """The policy_ref must match the compensating_control ID in
        gcc-boundary-gap-registry.yaml (GAP-ENT-001) so the finding is
        traceable back to the canon entry during ConMon review."""
        assert POLICY_REF_PIM_GROUPS_ESCALATION == "UIAO-AUTHZ-001"
