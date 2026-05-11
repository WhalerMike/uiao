"""HRIT Reference Fixture Conformance Tests (WS-B4).

Exercises the full reciprocity lifecycle against the WS-A8 OPM/TREAS/IRS
reference fixture. All Batch A modules must be importable for this class
to run; otherwise the entire class is skipped gracefully.

Lifecycle scenarios covered
---------------------------
1. Emit reciprocity records for TREAS and IRS using controlling-ato.json data.
2. Verify each record's HMAC signature.
3. Aggregate per-agency bundles (TREAS + IRS) into tmp_path.
4. Bundle verification — both must report ok=True.
5. Configuration-latitude drift on TREAS config → zero findings.
6. Configuration-latitude drift on IRS config → exactly 1 DRIFT-SCHEMA P2
   finding on password_minimum_length, verdict OUT_OF_LATITUDE.
7. ATO cadence check with synthetic dates that PASS overall.
8. ATO cadence with SSP-Draft-30 FAIL (draft submitted on day 35).
9. ATO cadence with SSP-Final-45 FAIL (final submitted on day 50).
10. ATO cadence with Reauthorization-30 FAIL (ATO already lapsed).

References
----------
- inbox/v0.6.0-hrit-productization/03-batch-plan.md §WS-B4
- src/uiao/canon/specs/single-ato-reciprocity-model.md (UIAO_140) §4–7
- src/uiao/canon/adr/adr-058-hrit-productization-mission.md §Verification
"""

from __future__ import annotations

import importlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Module-level availability guard — skip everything if Batch A is missing
# ---------------------------------------------------------------------------

_BATCH_A_MODULES: list[tuple[str, str]] = [
    ("uiao.oscal.reciprocity_record", "emit_reciprocity_record"),
    ("uiao.oscal.reciprocity_bundle", "aggregate_per_agency_bundle"),
    ("uiao.monitoring.ato_cadence", "evaluate_ato_cadence"),
    ("uiao.governance.config_latitude", "detect_latitude_drift"),
]


def _all_batch_a_available() -> bool:
    for module_path, attr in _BATCH_A_MODULES:
        try:
            mod = importlib.import_module(module_path)
            if not hasattr(mod, attr):
                return False
        except ImportError:
            return False
    return True


_BATCH_A_MISSING = not _all_batch_a_available()


# ---------------------------------------------------------------------------
# Helpers — build domain objects from raw fixture dicts
# ---------------------------------------------------------------------------


def _build_ssp_table(raw: dict[str, Any]) -> Any:
    from uiao.governance.config_latitude import (  # noqa: PLC0415
        LatitudeTableEntry,
        SspLatitudeTable,
    )

    entries = []
    for item in raw.get("latitude_settings", []):
        entries.append(
            LatitudeTableEntry(
                setting_key=item["key"],
                allowed_values=item.get("allowed_values"),
                allowed_pattern=item.get("allowed_pattern"),
                notes=item.get("description"),
            )
        )
    return SspLatitudeTable(
        controlling_ato_id=raw["controlling_ato_id"],
        entries=entries,
    )


def _build_tenant(raw: dict[str, Any]) -> Any:
    from uiao.governance.config_latitude import TenantConfig, TenantConfigEntry  # noqa: PLC0415

    entries = [TenantConfigEntry(setting_key=k, observed_value=str(v)) for k, v in raw.get("configuration", {}).items()]
    return TenantConfig(
        consuming_agency_code=raw["consuming_agency_code"],
        entries=entries,
    )


def _emit_record(
    *,
    controlling_ato_id: str,
    consuming_agency_code: str,
    signing_key: bytes,
    now: datetime | None = None,
) -> dict[str, Any]:
    from uiao.oscal.reciprocity_record import emit_reciprocity_record  # noqa: PLC0415

    _now = now or datetime.now(tz=timezone.utc)
    result: dict[str, Any] = emit_reciprocity_record(
        controlling_ato_id=controlling_ato_id,
        consuming_agency_code=consuming_agency_code,
        legal_basis="interagency-mou",
        reciprocity_basis=(
            f"{consuming_agency_code} consumes the OPM HRIT platform under "
            "the single controlling ATO issued by OPM CIO per PWS §5.1.1 #5 "
            "(WS-B4 conformance test)."
        ),
        effective_at=_now,
        expires_at=_now + timedelta(days=365),
        configuration_latitude_ref=(f"{controlling_ato_id}#latitude/{consuming_agency_code.lower()}-tier-1"),
        signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
        signing_key=signing_key,
    )
    return result


# ---------------------------------------------------------------------------
# Conformance test class
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    _BATCH_A_MISSING,
    reason="One or more Batch A modules not available — skipping conformance class",
)
class TestHritReferenceFixtureConformance:
    """Full lifecycle conformance against the WS-A8 OPM/TREAS/IRS fixture."""

    # --- 1 & 2: Emit records + verify signatures ----------------------------

    def test_emit_treas_record_from_fixture(
        self,
        controlling_ato_data: dict[str, Any],
        hmac_signing_key: bytes,
    ) -> None:
        """Emit a TREAS reciprocity record using fixture controlling-ato data."""
        record = _emit_record(
            controlling_ato_id=controlling_ato_data["controlling_ato_id"],
            consuming_agency_code="TREAS",
            signing_key=hmac_signing_key,
        )
        assert record["controlling_ato_id"] == controlling_ato_data["controlling_ato_id"]
        assert record["consuming_agency_code"] == "TREAS"
        assert record["legal_basis"] == "interagency-mou"
        assert "signature" in record
        assert record["signature"]["algorithm"] == "HMAC-SHA256"

    def test_emit_irs_record_from_fixture(
        self,
        controlling_ato_data: dict[str, Any],
        hmac_signing_key: bytes,
    ) -> None:
        """Emit an IRS reciprocity record using fixture controlling-ato data."""
        record = _emit_record(
            controlling_ato_id=controlling_ato_data["controlling_ato_id"],
            consuming_agency_code="IRS",
            signing_key=hmac_signing_key,
        )
        assert record["consuming_agency_code"] == "IRS"
        assert record["signature"]["algorithm"] == "HMAC-SHA256"

    def test_treas_signature_verifies(
        self,
        controlling_ato_data: dict[str, Any],
        hmac_signing_key: bytes,
    ) -> None:
        """TREAS reciprocity record HMAC signature verifies with the same key."""
        from uiao.oscal.reciprocity_record import verify_signature  # noqa: PLC0415

        record = _emit_record(
            controlling_ato_id=controlling_ato_data["controlling_ato_id"],
            consuming_agency_code="TREAS",
            signing_key=hmac_signing_key,
        )
        assert verify_signature(record, hmac_signing_key) is True

    def test_irs_signature_verifies(
        self,
        controlling_ato_data: dict[str, Any],
        hmac_signing_key: bytes,
    ) -> None:
        """IRS reciprocity record HMAC signature verifies with the same key."""
        from uiao.oscal.reciprocity_record import verify_signature  # noqa: PLC0415

        record = _emit_record(
            controlling_ato_id=controlling_ato_data["controlling_ato_id"],
            consuming_agency_code="IRS",
            signing_key=hmac_signing_key,
        )
        assert verify_signature(record, hmac_signing_key) is True

    # --- 3 & 4: Bundle aggregation + verification ---------------------------

    def test_aggregate_and_verify_treas_bundle(
        self,
        controlling_ato_data: dict[str, Any],
        hmac_signing_key: bytes,
        tmp_path: Path,
    ) -> None:
        """TREAS bundle aggregates to disk and verifies ok=True."""
        from uiao.oscal.reciprocity_bundle import (  # noqa: PLC0415
            aggregate_per_agency_bundle,
            verify_bundle,
        )
        from uiao.oscal.reciprocity_record import (  # noqa: PLC0415
            emit_reciprocity_record,
            emit_scoped_component_definition,
        )

        now = datetime.now(tz=timezone.utc)
        record: dict[str, Any] = emit_reciprocity_record(
            controlling_ato_id=controlling_ato_data["controlling_ato_id"],
            consuming_agency_code="TREAS",
            legal_basis="interagency-mou",
            reciprocity_basis="Treasury conformance test record.",
            effective_at=now,
            expires_at=now + timedelta(days=365),
            configuration_latitude_ref=(f"{controlling_ato_data['controlling_ato_id']}#latitude/treas-tier-1"),
            signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
            signing_key=hmac_signing_key,
        )
        component_def = emit_scoped_component_definition(record)
        assessment_results: dict[str, Any] = {
            "assessment-results": {
                "uuid": "00000000-0000-0000-0000-000000000002",
                "metadata": {
                    "title": "TREAS Assessment Results (WS-B4 conformance)",
                    "version": "1.0.0",
                },
                "import-ap": {"href": "#"},
                "results": [],
            }
        }

        bundle_dir = aggregate_per_agency_bundle(
            controlling_ato_id=controlling_ato_data["controlling_ato_id"],
            consuming_agency_code="TREAS",
            reciprocity_record=record,
            component_definition=component_def,
            assessment_results=assessment_results,
            output_dir=tmp_path,
        )

        assert bundle_dir.is_dir()
        result = verify_bundle(bundle_dir)
        assert result["ok"] is True, f"TREAS bundle verification failed: {result['errors']}"

    def test_aggregate_and_verify_irs_bundle(
        self,
        controlling_ato_data: dict[str, Any],
        hmac_signing_key: bytes,
        tmp_path: Path,
    ) -> None:
        """IRS bundle aggregates to disk and verifies ok=True."""
        from uiao.oscal.reciprocity_bundle import (  # noqa: PLC0415
            aggregate_per_agency_bundle,
            verify_bundle,
        )
        from uiao.oscal.reciprocity_record import (  # noqa: PLC0415
            emit_reciprocity_record,
            emit_scoped_component_definition,
        )

        now = datetime.now(tz=timezone.utc)
        record: dict[str, Any] = emit_reciprocity_record(
            controlling_ato_id=controlling_ato_data["controlling_ato_id"],
            consuming_agency_code="IRS",
            legal_basis="interagency-mou",
            reciprocity_basis="IRS conformance test record.",
            effective_at=now,
            expires_at=now + timedelta(days=365),
            configuration_latitude_ref=(f"{controlling_ato_data['controlling_ato_id']}#latitude/irs-tier-1"),
            signer="CN=opm-reciprocity-svc,OU=HRIT,O=OPM,C=US",
            signing_key=hmac_signing_key,
        )
        component_def = emit_scoped_component_definition(record)
        assessment_results: dict[str, Any] = {
            "assessment-results": {
                "uuid": "00000000-0000-0000-0000-000000000003",
                "metadata": {
                    "title": "IRS Assessment Results (WS-B4 conformance)",
                    "version": "1.0.0",
                },
                "import-ap": {"href": "#"},
                "results": [],
            }
        }

        bundle_dir = aggregate_per_agency_bundle(
            controlling_ato_id=controlling_ato_data["controlling_ato_id"],
            consuming_agency_code="IRS",
            reciprocity_record=record,
            component_definition=component_def,
            assessment_results=assessment_results,
            output_dir=tmp_path,
        )

        assert bundle_dir.is_dir()
        result = verify_bundle(bundle_dir)
        assert result["ok"] is True, f"IRS bundle verification failed: {result['errors']}"

    # --- 5: TREAS config drift — zero findings ------------------------------

    def test_treas_config_zero_drift_findings(
        self,
        ssp_latitude_table: dict[str, Any],
        treas_tenant_config: dict[str, Any],
    ) -> None:
        """Treasury config (fully conforming) produces zero latitude-drift findings."""
        from uiao.governance.config_latitude import detect_latitude_drift  # noqa: PLC0415

        ssp_table = _build_ssp_table(ssp_latitude_table)
        tenant = _build_tenant(treas_tenant_config)

        findings = detect_latitude_drift(ssp_table, tenant)
        assert findings == [], (
            f"Expected zero findings for TREAS; got {len(findings)}: {[f.model_dump() for f in findings]}"
        )

    # --- 6: IRS config drift — exactly 1 P2 finding -------------------------

    def test_irs_config_exactly_one_drift_finding(
        self,
        ssp_latitude_table: dict[str, Any],
        irs_tenant_config: dict[str, Any],
    ) -> None:
        """IRS config (one intentional violation) produces exactly 1 DRIFT-SCHEMA P2 finding."""
        from uiao.governance.config_latitude import detect_latitude_drift  # noqa: PLC0415

        ssp_table = _build_ssp_table(ssp_latitude_table)
        tenant = _build_tenant(irs_tenant_config)

        findings = detect_latitude_drift(ssp_table, tenant)
        assert len(findings) == 1, (
            f"Expected exactly 1 finding for IRS; got {len(findings)}: {[f.model_dump() for f in findings]}"
        )
        f = findings[0]
        assert f.verdict == "OUT_OF_LATITUDE", f"Expected OUT_OF_LATITUDE; got {f.verdict}"
        assert f.severity == "P2", f"Expected P2; got {f.severity}"
        assert f.setting_key == "password_minimum_length", f"Expected password_minimum_length; got {f.setting_key}"
        assert f.drift_class == "DRIFT-SCHEMA", f"Expected DRIFT-SCHEMA; got {f.drift_class}"

    # --- 7: ATO cadence — all PASS ------------------------------------------

    def test_ato_cadence_all_pass(self) -> None:
        """ATO cadence with synthetic dates where all three SLAs pass."""
        from uiao.monitoring.ato_cadence import AtoCadenceInput, evaluate_ato_cadence  # noqa: PLC0415

        award = date(2026, 1, 1)
        inp = AtoCadenceInput(
            award_date=award,
            # Draft submitted on day 20 (< 30-day threshold) — PASS
            ssp_draft_submitted_at=datetime(2026, 1, 21, tzinfo=timezone.utc),
            # Final submitted on day 40 (< 45-day threshold) — PASS
            ssp_final_submitted_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
            # ATO expires 2027-04-15; now is 2026-05-11 — >30 days before expiry — PASS
            current_ato_expires_at=date(2027, 4, 15),
            now=datetime(2026, 5, 11, tzinfo=timezone.utc),
        )
        report = evaluate_ato_cadence(inp)

        assert report.overall == "PASS", (
            f"Expected overall PASS; got {report.overall}: {[(v.name, v.verdict, v.message) for v in report.verdicts]}"
        )
        for verdict in report.verdicts:
            assert verdict.verdict in ("PASS", "N/A"), (
                f"SLA {verdict.name} should PASS but got {verdict.verdict}: {verdict.message}"
            )

    # --- 8: ATO cadence — SSP-Draft-30 FAIL ---------------------------------

    def test_ato_cadence_ssp_draft_fail(self) -> None:
        """ATO cadence FAIL when draft SSP submitted on day 35 (past 30-day threshold)."""
        from uiao.monitoring.ato_cadence import AtoCadenceInput, evaluate_ato_cadence  # noqa: PLC0415

        award = date(2026, 1, 1)
        inp = AtoCadenceInput(
            award_date=award,
            # Draft submitted on day 35 — FAIL (threshold is 30)
            ssp_draft_submitted_at=datetime(2026, 2, 5, tzinfo=timezone.utc),
            # Final submitted on day 40 — PASS (threshold is 45)
            ssp_final_submitted_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
            current_ato_expires_at=date(2027, 4, 15),
            now=datetime(2026, 5, 11, tzinfo=timezone.utc),
        )
        report = evaluate_ato_cadence(inp)

        draft_verdict = next(v for v in report.verdicts if v.name == "SSP-Draft-30")
        assert draft_verdict.verdict == "FAIL", (
            f"Expected SSP-Draft-30 FAIL; got {draft_verdict.verdict}: {draft_verdict.message}"
        )
        assert report.overall == "FAIL", f"Expected overall FAIL; got {report.overall}"

    # --- 9: ATO cadence — SSP-Final-45 FAIL ---------------------------------

    def test_ato_cadence_ssp_final_fail(self) -> None:
        """ATO cadence FAIL when final SSP submitted on day 50 (past 45-day threshold)."""
        from uiao.monitoring.ato_cadence import AtoCadenceInput, evaluate_ato_cadence  # noqa: PLC0415

        award = date(2026, 1, 1)
        inp = AtoCadenceInput(
            award_date=award,
            # Draft submitted on day 20 — PASS
            ssp_draft_submitted_at=datetime(2026, 1, 21, tzinfo=timezone.utc),
            # Final submitted on day 50 — FAIL (threshold is 45)
            ssp_final_submitted_at=datetime(2026, 2, 20, tzinfo=timezone.utc),
            current_ato_expires_at=date(2027, 4, 15),
            now=datetime(2026, 5, 11, tzinfo=timezone.utc),
        )
        report = evaluate_ato_cadence(inp)

        final_verdict = next(v for v in report.verdicts if v.name == "SSP-Final-45")
        assert final_verdict.verdict == "FAIL", (
            f"Expected SSP-Final-45 FAIL; got {final_verdict.verdict}: {final_verdict.message}"
        )
        assert report.overall == "FAIL", f"Expected overall FAIL; got {report.overall}"

    # --- 10: ATO cadence — Reauthorization-30 FAIL --------------------------

    def test_ato_cadence_reauth_fail(self) -> None:
        """ATO cadence FAIL when ATO has already lapsed (Reauthorization-30)."""
        from uiao.monitoring.ato_cadence import AtoCadenceInput, evaluate_ato_cadence  # noqa: PLC0415

        award = date(2026, 1, 1)
        inp = AtoCadenceInput(
            award_date=award,
            # Draft and final submitted within threshold
            ssp_draft_submitted_at=datetime(2026, 1, 21, tzinfo=timezone.utc),
            ssp_final_submitted_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
            # ATO expired on 2026-03-01 — well in the past
            current_ato_expires_at=date(2026, 3, 1),
            now=datetime(2026, 5, 11, tzinfo=timezone.utc),
        )
        report = evaluate_ato_cadence(inp)

        reauth_verdict = next(v for v in report.verdicts if v.name == "Reauthorization-30")
        assert reauth_verdict.verdict == "FAIL", (
            f"Expected Reauthorization-30 FAIL; got {reauth_verdict.verdict}: {reauth_verdict.message}"
        )
        assert report.overall == "FAIL", f"Expected overall FAIL; got {report.overall}"
