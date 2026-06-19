"""Tests for uiao.governance.ai_inventory.scanner and schema.

Covers:
- AISystemRecord.from_csv_row field parsing (DevStage, AgentClass, ATOStatus, bools, optionals)
- OrgPath derivation from agency/bureau combinations
- scan_inventory() — all 6 finding classes, gate escalation, shadow detection
- ScanResult convenience views and serialisation
- Pre-deployment / retired systems excluded from live population
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
from pathlib import Path


from uiao.governance.ai_inventory import scan_inventory, ScanResult
from uiao.governance.ai_inventory.drift import (
    DRIFT_AI_AGENTIC_UNGOVERNED,
    DRIFT_AI_ATO_GAP,
    DRIFT_AI_NO_ORGPATH,
    DRIFT_AI_PII_NO_PIA,
    DRIFT_AI_SHADOW,
    DRIFT_AI_UNOWNED,
)
from uiao.governance.ai_inventory.schema import (
    AgentClass,
    AISystemRecord,
    ATOStatus,
    DevStage,
)
from uiao.governance.drift_core import Severity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CSV_HEADERS = [
    "id",
    "use_case_name",
    "agency",
    "agency_name",
    "agency_bureau",
    "development_stage",
    "classification",
    "operational_date",
    "have_ato",
    "system_name_ato",
    "vendor_name",
    "contact_email",
    "has_pii",
    "pia_url",
    "is_high_impact",
    "hi_testing_conducted",
    "hi_assessment_completed",
    "hi_independent_review",
    "hi_ongoing_monitoring",
    "hi_failsafe_presence",
    "hi_appeal_process",
]

_DEFAULTS: dict[str, str] = {
    "id": "TEST-001",
    "use_case_name": "Test System",
    "agency": "DOD",
    "agency_name": "Department of Defense",
    "agency_bureau": "DISA",
    "development_stage": "deployed",
    "classification": "classical ml",
    "operational_date": "",
    "have_ato": "yes",
    "system_name_ato": "TEST-SYS-ATO",
    "vendor_name": "",
    "contact_email": "owner@dod.gov",
    "has_pii": "no",
    "pia_url": "",
    "is_high_impact": "no",
    "hi_testing_conducted": "",
    "hi_assessment_completed": "",
    "hi_independent_review": "",
    "hi_ongoing_monitoring": "",
    "hi_failsafe_presence": "",
    "hi_appeal_process": "",
}


def _row(**overrides: str) -> dict[str, str]:
    return {**_DEFAULTS, **overrides}


def _csv_file(*rows: dict[str, str]) -> Path:
    """Write rows to a temp CSV and return its path."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_HEADERS, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({h: r.get(h, "") for h in _CSV_HEADERS})
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix="_2025_individually_reported_AI_use_cases.csv",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(buf.getvalue())
        return Path(tmp.name)


# ---------------------------------------------------------------------------
# AISystemRecord.from_csv_row — field parsing
# ---------------------------------------------------------------------------


class TestFromCsvRow:
    def test_deployed_stage(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(development_stage="deployed"))
        assert rec.development_stage is DevStage.DEPLOYED

    def test_pilot_stage(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(development_stage="pilot"))
        assert rec.development_stage is DevStage.PILOT

    def test_pre_deployment_stage(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(development_stage="pre-deployment"))
        assert rec.development_stage is DevStage.PRE_DEPLOYMENT

    def test_retired_stage(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(development_stage="retired"))
        assert rec.development_stage is DevStage.RETIRED

    def test_unknown_stage_fallback(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(development_stage="future"))
        assert rec.development_stage is DevStage.UNKNOWN

    def test_agentic_classification(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(classification="Agentic AI"))
        assert rec.agent_class is AgentClass.AGENTIC

    def test_generative_classification(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(classification="generative AI"))
        assert rec.agent_class is AgentClass.GENERATIVE

    def test_nlp_classification(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(classification="natural language processing"))
        assert rec.agent_class is AgentClass.NLP

    def test_computer_vision_classification(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(classification="computer vision"))
        assert rec.agent_class is AgentClass.COMPUTER_VISION

    def test_classical_ml_classification(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(classification="classical ml"))
        assert rec.agent_class is AgentClass.ML

    def test_predictive_maps_to_ml(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(classification="predictive analytics"))
        assert rec.agent_class is AgentClass.ML

    def test_unknown_classification_fallback(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(classification="quantum neural net"))
        assert rec.agent_class is AgentClass.OTHER

    def test_ato_yes(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(have_ato="yes"))
        assert rec.ato_status is ATOStatus.YES

    def test_ato_no(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(have_ato="no"))
        assert rec.ato_status is ATOStatus.NO

    def test_ato_not_applicable(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(have_ato="not applicable"))
        assert rec.ato_status is ATOStatus.NOT_APPLICABLE

    def test_ato_unknown_fallback(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(have_ato="pending"))
        assert rec.ato_status is ATOStatus.UNKNOWN

    def test_has_pii_yes(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(has_pii="yes"))
        assert rec.has_pii is True

    def test_has_pii_no(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(has_pii="no"))
        assert rec.has_pii is False

    def test_has_pii_high_impact_prefix(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(has_pii="High-impact"))
        assert rec.has_pii is True

    def test_contact_email_blank_is_none(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(contact_email=""))
        assert rec.contact_email is None

    def test_contact_email_whitespace_is_none(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(contact_email="   "))
        assert rec.contact_email is None

    def test_contact_email_present(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(contact_email="ciso@agency.gov"))
        assert rec.contact_email == "ciso@agency.gov"

    def test_pia_url_blank_is_none(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(pia_url=""))
        assert rec.pia_url is None

    def test_pia_url_present(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(pia_url="https://agency.gov/pia"))
        assert rec.pia_url == "https://agency.gov/pia"


# ---------------------------------------------------------------------------
# OrgPath derivation
# ---------------------------------------------------------------------------


class TestOrgPath:
    def test_agency_and_bureau_produce_orgpath(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(agency="DOD", agency_bureau="DISA"))
        assert rec.orgpath == "DOD:DISA"

    def test_agency_only_when_bureau_blank(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(agency="HHS", agency_bureau=""))
        assert rec.orgpath == "HHS"

    def test_bureau_same_as_agency_collapses(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(agency="NASA", agency_bureau="NASA"))
        assert rec.orgpath == "NASA"

    def test_blank_agency_yields_none(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(agency="", agency_bureau="DISA"))
        assert rec.orgpath is None

    def test_orgpath_is_uppercase_agency(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(agency="dod", agency_bureau="disa"))
        assert rec.orgpath is not None
        assert rec.orgpath.startswith("DOD")


# ---------------------------------------------------------------------------
# is_live property
# ---------------------------------------------------------------------------


class TestIsLive:
    def test_deployed_is_live(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(development_stage="deployed"))
        assert rec.is_live is True

    def test_pilot_is_live(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(development_stage="pilot"))
        assert rec.is_live is True

    def test_pre_deployment_is_not_live(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(development_stage="pre-deployment"))
        assert rec.is_live is False

    def test_retired_is_not_live(self) -> None:
        rec = AISystemRecord.from_csv_row(_row(development_stage="retired"))
        assert rec.is_live is False


# ---------------------------------------------------------------------------
# scan_inventory — finding classes
# ---------------------------------------------------------------------------


class TestScanInventoryFindings:
    def test_clean_record_produces_no_findings(self) -> None:
        path = _csv_file(_row())
        result = scan_inventory(path)
        assert result.findings == []

    def test_ato_gap_emitted_for_deployed_no_ato(self) -> None:
        path = _csv_file(_row(have_ato="no"))
        result = scan_inventory(path)
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_ATO_GAP in classes

    def test_no_ato_gap_for_pre_deployment(self) -> None:
        path = _csv_file(_row(development_stage="pre-deployment", have_ato="no"))
        result = scan_inventory(path)
        assert result.findings == []

    def test_no_orgpath_emitted_when_agency_blank(self) -> None:
        path = _csv_file(_row(agency="", agency_bureau=""))
        result = scan_inventory(path)
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_NO_ORGPATH in classes

    def test_unowned_emitted_when_no_contact_email(self) -> None:
        path = _csv_file(_row(contact_email=""))
        result = scan_inventory(path)
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_UNOWNED in classes

    def test_pii_no_pia_emitted_when_pii_and_no_pia_url(self) -> None:
        path = _csv_file(_row(has_pii="yes", pia_url=""))
        result = scan_inventory(path)
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_PII_NO_PIA in classes

    def test_no_pii_no_pia_when_no_pii(self) -> None:
        path = _csv_file(_row(has_pii="no", pia_url=""))
        result = scan_inventory(path)
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_PII_NO_PIA not in classes

    def test_no_pii_no_pia_when_pia_url_present(self) -> None:
        path = _csv_file(_row(has_pii="yes", pia_url="https://agency.gov/pia"))
        result = scan_inventory(path)
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_PII_NO_PIA not in classes

    def test_agentic_ungoverned_p1_emitted(self) -> None:
        path = _csv_file(_row(classification="Agentic AI", have_ato="no"))
        result = scan_inventory(path)
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_AGENTIC_UNGOVERNED in classes

    def test_agentic_ungoverned_is_p1(self) -> None:
        path = _csv_file(_row(classification="Agentic AI", have_ato="no"))
        result = scan_inventory(path)
        p1s = [f for f in result.findings if f.drift_class == DRIFT_AI_AGENTIC_UNGOVERNED]
        assert p1s[0].severity is Severity.P1

    def test_agentic_with_ato_no_ungoverned_finding(self) -> None:
        path = _csv_file(_row(classification="Agentic AI", have_ato="yes"))
        result = scan_inventory(path)
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_AGENTIC_UNGOVERNED not in classes

    def test_agentic_without_ato_also_emits_ato_gap(self) -> None:
        path = _csv_file(_row(classification="Agentic AI", have_ato="no"))
        result = scan_inventory(path)
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_ATO_GAP in classes
        assert DRIFT_AI_AGENTIC_UNGOVERNED in classes

    def test_retired_record_excluded_from_scan(self) -> None:
        path = _csv_file(_row(development_stage="retired", have_ato="no", contact_email=""))
        result = scan_inventory(path)
        assert result.findings == []
        assert result.live_records == []

    def test_multiple_records_multiple_findings(self) -> None:
        path = _csv_file(
            _row(id="A", have_ato="no"),
            _row(id="B", contact_email=""),
            _row(id="C"),
        )
        result = scan_inventory(path)
        assert len(result.records) == 3
        assert len(result.live_records) == 3
        assert len(result.findings) == 2


# ---------------------------------------------------------------------------
# scan_inventory — shadow detection
# ---------------------------------------------------------------------------


class TestShadowDetection:
    def test_registry_id_absent_from_inventory_emits_shadow(self) -> None:
        path = _csv_file(_row(system_name_ato="KNOWN-SYS"))
        result = scan_inventory(path, known_registry_ids={"GHOST-SYS"})
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_SHADOW in classes

    def test_shadow_finding_is_p1(self) -> None:
        path = _csv_file(_row(system_name_ato="KNOWN-SYS"))
        result = scan_inventory(path, known_registry_ids={"GHOST-SYS"})
        shadows = [f for f in result.findings if f.drift_class == DRIFT_AI_SHADOW]
        assert shadows[0].severity is Severity.P1

    def test_registry_id_present_in_inventory_no_shadow(self) -> None:
        path = _csv_file(_row(system_name_ato="KNOWN-SYS"))
        result = scan_inventory(path, known_registry_ids={"KNOWN-SYS"})
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_SHADOW not in classes

    def test_no_registry_ids_skips_shadow_detection(self) -> None:
        path = _csv_file(_row())
        result = scan_inventory(path, known_registry_ids=None)
        classes = [f.drift_class for f in result.findings]
        assert DRIFT_AI_SHADOW not in classes

    def test_multiple_shadow_systems(self) -> None:
        path = _csv_file(_row(system_name_ato="LEGIT"))
        result = scan_inventory(path, known_registry_ids={"GHOST-A", "GHOST-B"})
        shadows = [f for f in result.findings if f.drift_class == DRIFT_AI_SHADOW]
        assert len(shadows) == 2


# ---------------------------------------------------------------------------
# scan_inventory — gate escalation
# ---------------------------------------------------------------------------


class TestGateEscalation:
    def test_no_findings_gate_is_pass(self) -> None:
        path = _csv_file(_row())
        result = scan_inventory(path)
        assert result.gate_result["decision"] in {"PASS", "pass"}

    def test_p1_finding_escalates_gate(self) -> None:
        path = _csv_file(_row(classification="Agentic AI", have_ato="no"))
        result = scan_inventory(path)
        assert result.gate_result["decision"] not in {"PASS", "pass"}


# ---------------------------------------------------------------------------
# scan_inventory — vintage inference
# ---------------------------------------------------------------------------


class TestVintageInference:
    def test_vintage_inferred_from_filename(self) -> None:
        path = _csv_file(_row())
        result = scan_inventory(path)
        # The temp file suffix contains "2025"
        assert result.inventory_vintage == "2025"

    def test_vintage_override(self) -> None:
        path = _csv_file(_row())
        result = scan_inventory(path, vintage="2024")
        assert result.inventory_vintage == "2024"


# ---------------------------------------------------------------------------
# ScanResult convenience views
# ---------------------------------------------------------------------------


class TestScanResultViews:
    def _result_with_all_findings(self) -> ScanResult:
        path = _csv_file(
            _row(
                classification="Agentic AI",
                have_ato="no",
                agency="",
                contact_email="",
                has_pii="yes",
                pia_url="",
            )
        )
        return scan_inventory(path, known_registry_ids={"GHOST"})

    def test_p1_findings_filters_correctly(self) -> None:
        result = self._result_with_all_findings()
        assert all(f.severity is Severity.P1 for f in result.p1_findings)
        assert len(result.p1_findings) >= 1

    def test_p2_findings_filters_correctly(self) -> None:
        result = self._result_with_all_findings()
        assert all(f.severity is Severity.P2 for f in result.p2_findings)

    def test_ato_gaps_property(self) -> None:
        path = _csv_file(_row(have_ato="no"))
        result = scan_inventory(path)
        assert len(result.ato_gaps) == 1
        assert result.ato_gaps[0].drift_class == DRIFT_AI_ATO_GAP

    def test_shadow_systems_property(self) -> None:
        path = _csv_file(_row(system_name_ato="LEGIT"))
        result = scan_inventory(path, known_registry_ids={"GHOST"})
        assert len(result.shadow_systems) == 1

    def test_agentic_ungoverned_property(self) -> None:
        path = _csv_file(_row(classification="Agentic AI", have_ato="no"))
        result = scan_inventory(path)
        assert len(result.agentic_ungoverned) == 1

    def test_summary_returns_string(self) -> None:
        path = _csv_file(_row())
        result = scan_inventory(path)
        s = result.summary()
        assert isinstance(s, str)
        assert "Vintage" in s
        assert "Findings" in s

    def test_to_json_is_valid_json(self) -> None:
        path = _csv_file(_row())
        result = scan_inventory(path)
        data = json.loads(result.to_json())
        assert "findings" in data
        assert "counts" in data
        assert data["counts"]["total_records"] == 1

    def test_to_json_counts_match_properties(self) -> None:
        path = _csv_file(_row(have_ato="no", contact_email=""))
        result = scan_inventory(path)
        data = json.loads(result.to_json())
        assert data["counts"]["findings"] == len(result.findings)
        assert data["counts"]["p1"] == len(result.p1_findings)
        assert data["counts"]["p2"] == len(result.p2_findings)
