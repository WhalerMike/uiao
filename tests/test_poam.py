"""Tests for uiao_core.models.poam and uiao_core.generators.poam_rules."""

from __future__ import annotations

import uuid

from uiao_core.generators.poam_rules import (
    _evaluate_low_maturity,
    _evaluate_missing_control,
    _evaluate_missing_evidence,
    evaluate_rules,
    load_rules,
)
from uiao_core.models.poam import (
    POAMEntry,
    POAMRule,
    RemediationStatus,
    RiskRating,
)

# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestRiskRating:
    def test_values(self) -> None:
        assert RiskRating.CRITICAL.value == "Critical"
        assert RiskRating.HIGH.value == "High"
        assert RiskRating.MODERATE.value == "Moderate"
        assert RiskRating.LOW.value == "Low"


class TestRemediationStatus:
    """FedRAMP PMO enum values must match the POA&M template exactly."""

    def test_open_value(self) -> None:
        assert RemediationStatus.OPEN.value == "Open"

    def test_in_progress_value_has_hyphen(self) -> None:
        assert RemediationStatus.IN_PROGRESS.value == "In-Progress"

    def test_closed_value(self) -> None:
        assert RemediationStatus.CLOSED.value == "Closed"

    def test_delayed_value(self) -> None:
        assert RemediationStatus.DELAYED.value == "Delayed"


class TestPOAMEntry:
    def test_defaults(self) -> None:
        entry = POAMEntry()
        assert entry.uuid == ""
        assert entry.finding_id == ""
        assert entry.risk_rating == RiskRating.MODERATE
        assert entry.remediation_status == RemediationStatus.OPEN
        assert entry.related_controls == []

    def test_to_oscal_item_contains_props_with_uuid(self) -> None:
        entry = POAMEntry(
            uuid=str(uuid.uuid4()),
            finding_id="POAM-UIAO-0001",
            title="Test finding",
            description="Test",
            risk_rating=RiskRating.HIGH,
        )
        item = entry.to_oscal_item()
        assert item["uuid"] == entry.uuid
        assert item["title"] == "Test finding"
        # Every prop must have a uuid field (OSCAL 1.3.0 + MEMORY rule)
        for prop in item["props"]:
            assert "uuid" in prop, f"Prop missing uuid: {prop}"
            assert "name" in prop
            assert "value" in prop

    def test_to_oscal_item_prop_names(self) -> None:
        entry = POAMEntry(
            uuid=str(uuid.uuid4()),
            finding_id="POAM-UIAO-0002",
            risk_rating=RiskRating.CRITICAL,
            remediation_status=RemediationStatus.OPEN,
            responsible_party="ISSO",
        )
        item = entry.to_oscal_item()
        prop_names = [p["name"] for p in item["props"]]
        assert "risk-rating" in prop_names
        assert "finding-id" in prop_names
        assert "remediation-status" in prop_names
        assert "responsible-party" in prop_names

    def test_to_csv_row_keys(self) -> None:
        entry = POAMEntry(
            finding_id="POAM-UIAO-0003",
            title="CSV test",
            risk_rating=RiskRating.LOW,
            related_controls=["AC-2"],
        )
        row = entry.to_csv_row()
        required_keys = [
            "POA&M ID",
            "Controls",
            "Weakness Name",
            "Risk Rating",
            "Remediation Status",
        ]
        for key in required_keys:
            assert key in row, f"Missing CSV column: {key}"
        assert row["POA&M ID"] == "POAM-UIAO-0003"
        assert row["Controls"] == "AC-2"

    def test_to_csv_row_remediation_status_fedramp_enum(self) -> None:
        entry = POAMEntry(remediation_status=RemediationStatus.IN_PROGRESS)
        row = entry.to_csv_row()
        assert row["Remediation Status"] == "In-Progress"


class TestPOAMRule:
    def test_model_validate(self) -> None:
        raw = {
            "id": "RULE-001",
            "name": "Test rule",
            "condition_type": "low_maturity",
            "condition_value": "Initial",
            "risk_rating": "High",
            "recommendation": "Fix it",
            "responsible_party": "ISSO",
        }
        rule = POAMRule.model_validate(raw)
        assert rule.id == "RULE-001"
        assert rule.risk_rating == RiskRating.HIGH
        assert rule.responsible_party == "ISSO"


# ---------------------------------------------------------------------------
# Rule engine tests
# ---------------------------------------------------------------------------


class TestLoadRules:
    def test_load_rules_missing_path_returns_empty(self, tmp_path) -> None:
        rules = load_rules(tmp_path / "nonexistent.yaml")
        assert rules == []

    def test_load_rules_from_yaml(self, tmp_path) -> None:
        rules_yaml = tmp_path / "test_rules.yaml"
        rules_yaml.write_text(
            "rules:\n"
            "  - id: TEST-001\n"
            "    name: Test\n"
            "    condition_type: missing_control\n"
            "    condition_value: AC-2\n"
            "    risk_rating: High\n"
        )
        rules = load_rules(rules_yaml)
        assert len(rules) == 1
        assert rules[0].id == "TEST-001"
        assert rules[0].risk_rating == RiskRating.HIGH


class TestEvaluateLowMaturity:
    def _make_rule(self, value: str) -> POAMRule:
        return POAMRule(
            id="R1", name="test", condition_type="low_maturity", condition_value=value, risk_rating=RiskRating.HIGH
        )

    def test_no_matrix_returns_empty(self) -> None:
        rule = self._make_rule("Initial")
        gaps = _evaluate_low_maturity(rule, {})
        assert gaps == []

    def test_matching_maturity_detected(self) -> None:
        rule = self._make_rule("Initial")
        context = {
            "unified_compliance_matrix": [
                {"category": "Identity", "cisa_maturity": "Initial", "nist_controls": ["IA-2"]},
            ]
        }
        gaps = _evaluate_low_maturity(rule, context)
        assert len(gaps) == 1
        assert gaps[0]["category"] == "Identity"

    def test_non_matching_maturity_ignored(self) -> None:
        rule = self._make_rule("Initial")
        context = {
            "unified_compliance_matrix": [
                {"category": "Identity", "cisa_maturity": "Optimized", "nist_controls": ["IA-2"]},
            ]
        }
        gaps = _evaluate_low_maturity(rule, context)
        assert gaps == []


class TestEvaluateMissingEvidence:
    def _make_rule(self) -> POAMRule:
        return POAMRule(
            id="R2", name="test", condition_type="missing_evidence", condition_value="", risk_rating=RiskRating.MODERATE
        )

    def test_no_fedramp_config_returns_empty(self) -> None:
        rule = self._make_rule()
        gaps = _evaluate_missing_evidence(rule, {})
        assert gaps == []

    def test_empty_evidence_source_detected(self) -> None:
        rule = self._make_rule()
        context = {
            "fedramp_20x_config": {
                "core_mappings": [
                    {"concept": "MFA", "nist_rev5_control": "IA-5(1)", "evidence_source": ""},
                ]
            }
        }
        gaps = _evaluate_missing_evidence(rule, context)
        assert len(gaps) == 1
        assert gaps[0]["concept"] == "MFA"

    def test_present_evidence_not_flagged(self) -> None:
        rule = self._make_rule()
        context = {
            "fedramp_20x_config": {
                "core_mappings": [
                    {"concept": "MFA", "nist_rev5_control": "IA-5(1)", "evidence_source": "Azure AD logs"},
                ]
            }
        }
        gaps = _evaluate_missing_evidence(rule, context)
        assert gaps == []


class TestEvaluateMissingControl:
    def _make_rule(self, control: str) -> POAMRule:
        return POAMRule(
            id="R3",
            name="test",
            condition_type="missing_control",
            condition_value=control,
            risk_rating=RiskRating.CRITICAL,
        )

    def test_control_absent_from_context(self) -> None:
        rule = self._make_rule("IA-5(1)")
        gaps = _evaluate_missing_control(rule, {})
        assert len(gaps) == 1
        assert gaps[0]["control"] == "IA-5(1)"

    def test_control_present_in_matrix(self) -> None:
        rule = self._make_rule("IA-5(1)")
        context = {"unified_compliance_matrix": [{"nist_controls": ["IA-5(1)", "AC-2"]}]}
        gaps = _evaluate_missing_control(rule, context)
        assert gaps == []

    def test_control_present_in_fedramp_mappings(self) -> None:
        rule = self._make_rule("CA-7")
        context = {"fedramp_20x_config": {"core_mappings": [{"nist_rev5_control": "CA-7"}]}}
        gaps = _evaluate_missing_control(rule, context)
        assert gaps == []

    def test_empty_condition_value_returns_empty(self) -> None:
        rule = self._make_rule("")
        gaps = _evaluate_missing_control(rule, {})
        assert gaps == []


class TestEvaluateRules:
    @staticmethod
    def _missing_mfa_rule() -> POAMRule:
        return POAMRule(
            id="RULE-004",
            name="Missing MFA",
            condition_type="missing_control",
            condition_value="IA-5(1)",
            risk_rating=RiskRating.CRITICAL,
        )

    def test_empty_rules_returns_empty(self) -> None:
        entries = evaluate_rules({}, rules=[])
        assert entries == []

    def test_finding_id_uses_poam_uiao_prefix(self) -> None:
        entries = evaluate_rules({}, rules=[self._missing_mfa_rule()])
        assert len(entries) == 1
        assert entries[0].finding_id.startswith("POAM-UIAO-")

    def test_finding_id_sequential(self) -> None:
        rules = [
            POAMRule(
                id="R1",
                name="R1",
                condition_type="missing_control",
                condition_value="IA-5(1)",
                risk_rating=RiskRating.HIGH,
            ),
            POAMRule(
                id="R2",
                name="R2",
                condition_type="missing_control",
                condition_value="CA-7",
                risk_rating=RiskRating.HIGH,
            ),
        ]
        entries = evaluate_rules({}, rules=rules)
        assert len(entries) == 2
        assert entries[0].finding_id == "POAM-UIAO-0001"
        assert entries[1].finding_id == "POAM-UIAO-0002"

    def test_uuid_is_valid_uuidv4(self) -> None:
        entries = evaluate_rules({}, rules=[self._missing_mfa_rule()])
        assert len(entries) == 1
        # Should not raise
        parsed = uuid.UUID(entries[0].uuid)
        assert parsed.version == 4

    def test_unknown_condition_type_produces_no_entries(self) -> None:
        rule = POAMRule(
            id="RULE-999", name="Custom", condition_type="custom", condition_value="foo", risk_rating=RiskRating.LOW
        )
        entries = evaluate_rules({}, rules=[rule])
        assert entries == []

    def test_low_maturity_entry_source_is_rule_engine(self) -> None:
        rule = POAMRule(
            id="R1", name="R1", condition_type="low_maturity", condition_value="Initial", risk_rating=RiskRating.HIGH
        )
        context = {
            "unified_compliance_matrix": [
                {"category": "Access Control", "cisa_maturity": "Initial", "nist_controls": ["AC-2"]}
            ]
        }
        entries = evaluate_rules(context, rules=[rule])
        assert len(entries) == 1
        assert entries[0].source == "rule_engine"
        assert entries[0].source_finding_id == "R1"
