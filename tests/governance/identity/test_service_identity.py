"""Tests for governance/identity/service_identity.py — non-human identity lifecycle."""

from __future__ import annotations

import json
import tempfile
from datetime import date, timedelta


from uiao.governance.identity.service_identity import (
    CREDENTIAL_EXPIRY_WARNING_DAYS,
    ServiceIdentityRecord,
    ServiceIdentityEventType,
    detect_service_events,
    detect_orphans_from_leavers,
    write_evidence_artifacts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_svc(**kwargs) -> ServiceIdentityRecord:
    defaults = dict(
        principal_id="svc-sentinel-ingest",
        display_name="svc-sentinel-ingest",
        account_class="ServicePrincipal",
        department="IT",
        division="CyberOps",
        cost_center="CC-4200",
        owner_employee_id="E001",
        owner_display_name="Alice Smith",
        credential_expiry_date=None,
        last_rotation_date=None,
        purpose="Sentinel log ingestion",
        orgpath="NCR.IT.CyberOps",
        extracted_at="2026-06-22T00:00:00Z",
        is_active=True,
    )
    defaults.update(kwargs)
    return ServiceIdentityRecord(**defaults)


# Fixed reference date for all expiry math. Anchoring the relative helpers to
# REF_DATE (rather than date.today()) keeps these tests deterministic: a
# today-relative expiry date paired with a fixed reference_date is a time bomb
# that flips P1<->P2 as the wall clock advances past REF_DATE.
REF_DATE = date(2026, 6, 22)


def _future(days: int) -> str:
    return (REF_DATE + timedelta(days=days)).isoformat()


def _past(days: int) -> str:
    return (REF_DATE - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# CREATED events
# ---------------------------------------------------------------------------


class TestCreated:
    def test_new_account_is_created(self):
        current = [_make_svc()]
        es = detect_service_events(current)
        assert len(es.created) == 1
        assert es.created[0].event_type == ServiceIdentityEventType.CREATED

    def test_created_with_owner_no_findings(self):
        current = [_make_svc(owner_employee_id="E001")]
        es = detect_service_events(current)
        assert len(es.created[0].findings) == 0

    def test_created_without_owner_emits_finding(self):
        current = [_make_svc(owner_employee_id=None)]
        es = detect_service_events(current)
        assert len(es.created[0].findings) == 1
        assert "no-owner" in es.created[0].findings[0].name

    def test_created_actions_present(self):
        current = [_make_svc()]
        es = detect_service_events(current)
        steps = [a.step for a in es.created[0].actions]
        assert "SC-1" in steps
        assert "SC-2" in steps

    def test_existing_account_not_created_again(self):
        prior = [_make_svc()]
        current = [_make_svc()]
        es = detect_service_events(current, prior)
        assert len(es.created) == 0

    def test_inactive_record_skipped(self):
        current = [_make_svc(is_active=False)]
        es = detect_service_events(current)
        assert len(es.created) == 0


# ---------------------------------------------------------------------------
# ORPHANED events (the load-bearing test)
# ---------------------------------------------------------------------------


class TestOrphaned:
    def test_leaver_triggers_orphan_on_owned_account(self):
        current = [_make_svc(owner_employee_id="E001")]
        es = detect_service_events(current, leaver_employee_ids={"E001"})
        assert len(es.orphaned) == 1
        assert es.orphaned[0].event_type == ServiceIdentityEventType.ORPHANED

    def test_orphan_finding_is_p1(self):
        current = [_make_svc(owner_employee_id="E001")]
        es = detect_service_events(current, leaver_employee_ids={"E001"})
        finding = es.orphaned[0].findings[0]
        assert finding.severity.value == "P1"
        assert finding.drift_class == "DRIFT-ORPHAN-NHAM"

    def test_orphan_carries_leaver_employee_id(self):
        current = [_make_svc(owner_employee_id="E001")]
        es = detect_service_events(current, leaver_employee_ids={"E001"})
        assert es.orphaned[0].orphaned_by_employee_id == "E001"

    def test_non_owned_account_not_orphaned_by_other_leaver(self):
        current = [_make_svc(owner_employee_id="E002")]
        es = detect_service_events(current, leaver_employee_ids={"E001"})
        assert len(es.orphaned) == 0

    def test_multiple_accounts_same_leaver(self):
        current = [
            _make_svc(principal_id="svc-a", owner_employee_id="E001"),
            _make_svc(principal_id="svc-b", owner_employee_id="E001"),
            _make_svc(principal_id="svc-c", owner_employee_id="E002"),
        ]
        es = detect_service_events(current, leaver_employee_ids={"E001"})
        assert len(es.orphaned) == 2

    def test_orphan_actions_include_immediate_rotation(self):
        current = [_make_svc(owner_employee_id="E001")]
        es = detect_service_events(current, leaver_employee_ids={"E001"})
        steps = [a.step for a in es.orphaned[0].actions]
        assert "OR-1" in steps
        assert "OR-2" in steps
        assert "OR-3" in steps

    def test_detect_orphans_from_leavers_convenience(self):
        current = [_make_svc(owner_employee_id="E001")]
        es = detect_orphans_from_leavers(current, {"E001"})
        assert len(es.orphaned) == 1

    def test_orphan_prevents_other_events_for_same_account(self):
        """An orphaned account should not also appear as CREATED in the same run."""
        current = [_make_svc(owner_employee_id="E001")]
        es = detect_service_events(current, leaver_employee_ids={"E001"})
        assert len(es.orphaned) == 1
        assert len(es.created) == 0


# ---------------------------------------------------------------------------
# OWNER_CHANGED events
# ---------------------------------------------------------------------------


class TestOwnerChanged:
    def test_owner_change_detected(self):
        prior = [_make_svc(owner_employee_id="E001")]
        current = [_make_svc(owner_employee_id="E002")]
        es = detect_service_events(current, prior)
        assert len(es.owner_changed) == 1
        assert es.owner_changed[0].event_type == ServiceIdentityEventType.OWNER_CHANGED

    def test_owner_change_actions_include_rotation(self):
        prior = [_make_svc(owner_employee_id="E001")]
        current = [_make_svc(owner_employee_id="E002")]
        es = detect_service_events(current, prior)
        steps = [a.step for a in es.owner_changed[0].actions]
        assert "OC-2" in steps  # credential rotation after owner change

    def test_same_owner_no_event(self):
        prior = [_make_svc(owner_employee_id="E001")]
        current = [_make_svc(owner_employee_id="E001")]
        es = detect_service_events(current, prior)
        assert len(es.owner_changed) == 0


# ---------------------------------------------------------------------------
# CREDENTIAL_EXPIRY events
# ---------------------------------------------------------------------------


class TestCredentialExpiry:
    def test_expired_credential_is_p1(self):
        current = [_make_svc(credential_expiry_date=_past(5))]
        es = detect_service_events(current, reference_date=REF_DATE)
        assert len(es.expiring) == 1
        assert es.expiring[0].findings[0].severity.value == "P1"

    def test_near_expiry_is_p2(self):
        current = [_make_svc(credential_expiry_date=_future(CREDENTIAL_EXPIRY_WARNING_DAYS - 1))]
        es = detect_service_events(current, reference_date=REF_DATE)
        assert len(es.expiring) == 1
        assert es.expiring[0].findings[0].severity.value == "P2"

    def test_far_future_expiry_no_event(self):
        current = [_make_svc(credential_expiry_date=_future(CREDENTIAL_EXPIRY_WARNING_DAYS + 1))]
        es = detect_service_events(current, reference_date=REF_DATE)
        assert len(es.expiring) == 0

    def test_no_expiry_date_no_event(self):
        current = [_make_svc(credential_expiry_date=None)]
        es = detect_service_events(current)
        assert len(es.expiring) == 0

    def test_expiry_actions_include_rotation(self):
        current = [_make_svc(credential_expiry_date=_past(1))]
        es = detect_service_events(current, reference_date=REF_DATE)
        steps = [a.step for a in es.expiring[0].actions]
        assert "CE-1" in steps

    def test_malformed_expiry_date_skipped(self):
        current = [_make_svc(credential_expiry_date="not-a-date")]
        es = detect_service_events(current)
        assert len(es.expiring) == 0


# ---------------------------------------------------------------------------
# Integration with AGD fixture principals
# ---------------------------------------------------------------------------


class TestAGDFixtureIntegration:
    """Verify the two service principals from the AGD fixture trigger correct events."""

    def _fixture_accounts(self) -> list[ServiceIdentityRecord]:
        return [
            ServiceIdentityRecord(
                principal_id="svc-ai-web-scanner",
                display_name="svc-ai-web-scanner",
                account_class="ServicePrincipal",
                department="IT",
                division="CyberOps",
                cost_center="CC-4200",
                owner_employee_id="j.chen",
                owner_display_name="J. Chen",
                credential_expiry_date=None,
                last_rotation_date=None,
                purpose="AI-assisted web vulnerability scanner",
                orgpath="NCR.IT.CyberOps",
                extracted_at="2026-06-22T00:00:00Z",
            ),
            ServiceIdentityRecord(
                principal_id="svc-sentinel-ingest",
                display_name="svc-sentinel-ingest",
                account_class="ServicePrincipal",
                department="IT",
                division="CyberOps",
                cost_center="CC-4200",
                owner_employee_id="j.chen",
                owner_display_name="J. Chen",
                credential_expiry_date=None,
                last_rotation_date=None,
                purpose="Sentinel SIEM log ingestion",
                orgpath="NCR.IT.CyberOps",
                extracted_at="2026-06-22T00:00:00Z",
            ),
        ]

    def test_both_appear_as_created_on_first_run(self):
        accounts = self._fixture_accounts()
        es = detect_service_events(accounts)
        assert len(es.created) == 2

    def test_j_chen_departure_orphans_both_accounts(self):
        """j.chen leaving MUST immediately orphan both CyberOps service accounts."""
        accounts = self._fixture_accounts()
        es = detect_orphans_from_leavers(accounts, {"j.chen"})
        assert len(es.orphaned) == 2
        orphan_ids = {ev.record.principal_id for ev in es.orphaned}
        assert "svc-ai-web-scanner" in orphan_ids
        assert "svc-sentinel-ingest" in orphan_ids

    def test_orphan_findings_are_p1(self):
        accounts = self._fixture_accounts()
        es = detect_orphans_from_leavers(accounts, {"j.chen"})
        for ev in es.orphaned:
            assert ev.findings[0].severity.value == "P1"


# ---------------------------------------------------------------------------
# Evidence artifacts
# ---------------------------------------------------------------------------


class TestEvidenceArtifacts:
    def test_writes_two_files(self):
        current = [_make_svc()]
        es = detect_service_events(current)
        with tempfile.TemporaryDirectory() as d:
            paths = write_evidence_artifacts(es, d)
            assert len(paths) == 2
            names = {p.name for p in paths}
            assert "service-identity-event-log.json" in names
            assert "service-identity-action-log.json" in names

    def test_event_log_is_valid_json(self):
        current = [_make_svc()]
        es = detect_service_events(current)
        with tempfile.TemporaryDirectory() as d:
            paths = write_evidence_artifacts(es, d)
            event_log = next(p for p in paths if "event-log" in p.name)
            data = json.loads(event_log.read_text(encoding="utf-8"))
            assert "events" in data

    def test_summary_string(self):
        current = [_make_svc(owner_employee_id="E001")]
        es = detect_service_events(current, leaver_employee_ids={"E001"})
        s = es.summary()
        assert "orphaned" in s
        assert "1" in s
