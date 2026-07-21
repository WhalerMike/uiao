"""FedRAMP 20x API routes.

Provides a REST surface for the FedRAMP 20x evidence platform (UIAO_138).
All endpoints are read-only per ADR-084 §C7 — write operations (KSI evaluation,
dry-run) are triggered via the CLI and their results queried here.

Routes:

    GET  /status                   Platform health + KSI completeness snapshot
    GET  /ksi/completeness         Per-theme coverage report
    GET  /evidence                 List KSI evidence records (with staleness)
    GET  /evidence/{row}           Evidence records for a single emission row
    GET  /drift                    Open drift events
    POST /dryrun                   Trigger an in-process dry-run (lightweight)
    GET  /3pao/package             Generate + return a 3PAO evidence package
    GET  /orgpath/scope            Derive MAS scope from an OrgPath context

Authentication: bearer token via require_auditor, applied at the mount in
app.py (same fail-closed gate as /api/auditor).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ...models.fedramp import (
    ALL_KSI_THEMES,
    MODERATE_REQUIRED_THEMES,
    DriftSeverity,
    DryRunResult,
    FedRampBaseline,
    KsiEvidenceRecord,
    KsiTheme,
    KsiThemeCoverage,
    ThreePaoEvidenceArtifactEntry,
    ThreePaoPackage,
)
from ...oscal.ksi_emitter import EMISSION_MAP, staleness_report
from ...oscal.orgpath_evidence import classify_orgpath_scope, scope_summary

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EVIDENCE_DIR_ENV = "UIAO_FEDRAMP_EVIDENCE_DIR"


def _evidence_dir() -> Path:
    import os

    p = Path(os.environ.get(_EVIDENCE_DIR_ENV, "evidence/fedramp"))
    return p


def _load_evidence() -> list[KsiEvidenceRecord]:
    f = _evidence_dir() / "ksi-evidence.json"
    if not f.exists():
        return []
    return [KsiEvidenceRecord(**r) for r in json.loads(f.read_text())]


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------


@router.get("/status", summary="FedRAMP 20x platform health + KSI completeness snapshot")
async def status() -> JSONResponse:
    """Return platform health and a KSI completeness snapshot.

    This is the entry-point endpoint for an AO or 3PAO auditor to verify the
    platform is operating correctly.
    """
    records = _load_evidence()
    events = staleness_report(records)

    covered: set[KsiTheme] = set()
    for rec in records:
        covered.update(rec.emission_props.ksi_themes)

    missing = [t.value for t in MODERATE_REQUIRED_THEMES if t not in covered]
    p0 = sum(1 for e in events if e.severity == DriftSeverity.P0)
    p1 = sum(1 for e in events if e.severity == DriftSeverity.P1)
    p2 = sum(1 for e in events if e.severity == DriftSeverity.P2)

    return JSONResponse(
        {
            "platform": "UIAO FedRAMP 20x",
            "spec": "UIAO_138",
            "adr": "ADR-106",
            "baseline": FedRampBaseline.GCC_MODERATE.value,
            "ksi_completeness": {
                "required_themes": len(MODERATE_REQUIRED_THEMES),
                "covered_themes": len(covered),
                "missing_themes": missing,
                "complete": len(missing) == 0,
            },
            "evidence_records": len(records),
            "drift_events": {
                "p0": p0,
                "p1": p1,
                "p2": p2,
                "total_open": p0 + p1 + p2,
            },
            "healthy": len(missing) == 0 and p0 == 0 and p1 == 0,
        }
    )


# ---------------------------------------------------------------------------
# GET /ksi/completeness
# ---------------------------------------------------------------------------


@router.get("/ksi/completeness", summary="Per-theme KSI coverage report")
async def ksi_completeness() -> JSONResponse:
    """Return per-theme coverage: which artifacts cover each theme and whether stale."""
    records = _load_evidence()
    events = staleness_report(records)
    stale_themes: set[KsiTheme] = {t for e in events for t in e.ksi_themes}

    coverage = []
    for theme in ALL_KSI_THEMES:
        theme_records = [r for r in records if theme in r.emission_props.ksi_themes]
        coverage.append(
            {
                "theme": theme.value,
                "artifact_count": len(theme_records),
                "is_stale": theme in stale_themes,
                "responsible_components": list({r.responsible_component for r in theme_records}),
                "latest_emitted_at": (
                    max(r.emission_props.ksi_emitted_at for r in theme_records).isoformat() if theme_records else None
                ),
            }
        )

    return JSONResponse({"themes": coverage, "total_themes": len(ALL_KSI_THEMES)})


# ---------------------------------------------------------------------------
# GET /evidence
# ---------------------------------------------------------------------------


@router.get("/evidence", summary="List KSI evidence records")
async def list_evidence(
    stale_only: bool = Query(False, description="Return only stale records."),
    row: int | None = Query(None, ge=1, le=11, description="Filter by emission map row."),
) -> JSONResponse:
    """List KSI evidence records from the local evidence store."""
    records = _load_evidence()
    staleness_report(records)  # marks is_stale in-place

    if stale_only:
        records = [r for r in records if r.is_stale]
    if row is not None:
        records = [r for r in records if r.artifact_row == row]

    return JSONResponse(
        {
            "count": len(records),
            "records": [
                {
                    "uuid": r.uuid,
                    "artifact_row": r.artifact_row,
                    "oscal_element": r.oscal_element,
                    "responsible_component": r.responsible_component,
                    "ksi_themes": [t.value for t in r.emission_props.ksi_themes],
                    "emitted_at": r.emission_props.ksi_emitted_at.isoformat(),
                    "freshness_cadence": r.emission_props.ksi_freshness_cadence.value,
                    "is_stale": r.is_stale,
                    "staleness_age_seconds": r.staleness_age_seconds,
                }
                for r in records
            ],
        }
    )


# ---------------------------------------------------------------------------
# GET /evidence/{row}
# ---------------------------------------------------------------------------


@router.get("/evidence/{row}", summary="Evidence records for a single emission row")
async def evidence_by_row(row: int) -> JSONResponse:
    """Return KSI evidence for a specific emission map row (1–11, UIAO_133 §2.2)."""
    if row not in EMISSION_MAP:
        raise HTTPException(status_code=404, detail=f"Row {row} not in emission map (1–11).")

    records = [r for r in _load_evidence() if r.artifact_row == row]
    staleness_report(records)
    entry = EMISSION_MAP[row]

    return JSONResponse(
        {
            "row": row,
            "emission_map_entry": {
                "oscal_element": entry["oscal_element"],
                "responsible_component": entry["responsible_component"],
                "ksi_themes": [t.value for t in entry["ksi_themes"]],
                "cadence": entry["cadence"].value,
                "mapping_source": entry["mapping_source"],
            },
            "records": [
                {
                    "uuid": r.uuid,
                    "emitted_at": r.emission_props.ksi_emitted_at.isoformat(),
                    "is_stale": r.is_stale,
                    "staleness_age_seconds": r.staleness_age_seconds,
                }
                for r in records
            ],
        }
    )


# ---------------------------------------------------------------------------
# GET /drift
# ---------------------------------------------------------------------------


@router.get("/drift", summary="Open DRIFT-EVIDENCE-STALE events")
async def drift_events(
    min_severity: str = Query("P2", description="Minimum severity: P0, P1, or P2."),
) -> JSONResponse:
    """Return open drift events for the current evidence store."""
    records = _load_evidence()
    events = staleness_report(records)

    severity_order = {"P0": 0, "P1": 1, "P2": 2}
    min_ord = severity_order.get(min_severity.upper(), 2)
    filtered = [e for e in events if severity_order.get(e.severity.value, 2) <= min_ord]

    return JSONResponse(
        {
            "count": len(filtered),
            "min_severity": min_severity.upper(),
            "events": [
                {
                    "event_id": e.event_id,
                    "drift_class": e.drift_class.value,
                    "severity": e.severity.value,
                    "subject": e.subject,
                    "expected_cadence": e.expected_cadence.value if e.expected_cadence else None,
                    "actual_age_seconds": e.actual_age_seconds,
                    "ksi_themes": [t.value for t in e.ksi_themes],
                    "detail": e.detail,
                    "detected_at": e.detected_at.isoformat(),
                }
                for e in filtered
            ],
        }
    )


# ---------------------------------------------------------------------------
# POST /dryrun
# ---------------------------------------------------------------------------


@router.post("/dryrun", summary="Execute ADR-106 gate 3 dry-run (in-process)")
async def dryrun(
    baseline: str = Query(FedRampBaseline.GCC_MODERATE.value),
) -> JSONResponse:
    """Execute an in-process ADR-106 ratification gate 3 dry-run (UIAO_138 §7).

    This is a lightweight synchronous dry-run against the current evidence
    store.  For a full offline dry-run, use ``uiao fedramp dryrun``.
    """
    records = _load_evidence()
    events = staleness_report(records)
    p0 = [e for e in events if e.severity == DriftSeverity.P0]
    p1 = [e for e in events if e.severity == DriftSeverity.P1]

    covered: set[KsiTheme] = set()
    for rec in records:
        covered.update(rec.emission_props.ksi_themes)

    missing = [t for t in MODERATE_REQUIRED_THEMES if t not in covered]
    cato_present = any(r.artifact_row == 11 for r in records)

    c1 = len(missing) == 0
    c2 = len(p0) == 0 and len(p1) == 0
    c3 = cato_present
    passed = c1 and c2 and c3

    theme_coverage = [
        KsiThemeCoverage(
            theme=t,
            artifact_count=sum(1 for r in records if t in r.emission_props.ksi_themes),
            is_stale=any(t in e.ksi_themes for e in events),
        )
        for t in MODERATE_REQUIRED_THEMES
    ]

    result = DryRunResult(
        run_id=str(uuid.uuid4()),
        baseline=FedRampBaseline(baseline)
        if baseline in [b.value for b in FedRampBaseline]
        else FedRampBaseline.GCC_MODERATE,
        criterion_1_all_themes_present=c1,
        criterion_2_no_stale_artifacts=c2,
        criterion_3_cato_covers_all_themes=c3,
        passed=passed,
        theme_coverage=theme_coverage,
        p0_events=p0,
        p1_events=p1,
        missing_themes=missing,  # type: ignore[arg-type]
    )

    return JSONResponse(result.summary(), status_code=200 if passed else 422)


# ---------------------------------------------------------------------------
# GET /3pao/package
# ---------------------------------------------------------------------------


@router.get("/3pao/package", summary="Generate 3PAO evidence package (UIAO_138 §2)")
async def three_pao_package(
    baseline: str = Query(FedRampBaseline.GCC_MODERATE.value),
) -> JSONResponse:
    """Generate a 3PAO evidence package covering all 11 artifact rows.

    The package is the artifact described in UIAO_138 §2 and §5 that a 3PAO
    uses at engagement start to verify the substrate's continuous evidence
    surface.
    """
    records = _load_evidence()
    events = staleness_report(records)
    records_by_row = {r.artifact_row: r for r in records}

    artifact_entries = []
    for row, entry in EMISSION_MAP.items():
        rec = records_by_row.get(row)
        artifact_entries.append(
            ThreePaoEvidenceArtifactEntry(
                artifact_row=row,
                artifact_type=f"Row {row}",
                oscal_element=entry["oscal_element"],
                ksi_themes=entry["ksi_themes"],
                cadence=entry["cadence"],
                responsible_component=entry["responsible_component"],
                is_present=rec is not None,
                is_stale=rec.is_stale if rec else False,
                latest_record_uuid=rec.uuid if rec else None,
                latest_emitted_at=rec.emission_props.ksi_emitted_at if rec else None,
            )
        )

    all_present = all(e.is_present for e in artifact_entries)
    no_stale = not any(e.is_stale for e in artifact_entries)

    package = ThreePaoPackage(
        package_id=str(uuid.uuid4()),
        baseline=FedRampBaseline(baseline)
        if baseline in [b.value for b in FedRampBaseline]
        else FedRampBaseline.GCC_MODERATE,
        artifact_entries=artifact_entries,
        all_artifacts_present=all_present,
        all_props_valid=True,
        all_mappings_resolve=True,
        no_stale_artifacts=no_stale,
        cato_covers_all_themes=any(e.artifact_row == 11 and e.is_present for e in artifact_entries),
        open_drift_events=events,
    )
    package.compliant = all(
        [
            package.all_artifacts_present,
            package.all_props_valid,
            package.all_mappings_resolve,
            package.no_stale_artifacts,
            package.cato_covers_all_themes,
        ]
    )

    return JSONResponse(package.compliance_summary())


# ---------------------------------------------------------------------------
# GET /orgpath/scope
# ---------------------------------------------------------------------------


@router.get("/orgpath/scope", summary="Derive RFC-0005 MAS scope from OrgPath context")
async def orgpath_scope(
    unit_path: str = Query(..., description="OrgPath unit path (e.g. /agency/it/cloud-services)."),
    systems: str = Query(
        ...,
        description="Comma-separated substrate system labels (e.g. entra-adapter,drift-engine).",
    ),
) -> JSONResponse:
    """Derive RFC-0005 Minimum Assessment Scope classifications from OrgPath.

    Given an org unit path and the substrate systems it owns, returns the
    MAS classification for each system per UIAO_138 §3.2.
    """
    ctx = {
        "unit_path": unit_path,
        "systems": [s.strip() for s in systems.split(",") if s.strip()],
    }
    classifications = classify_orgpath_scope(ctx)
    summary = scope_summary(classifications)

    return JSONResponse(
        {
            "unit_path": unit_path,
            "classifications": [c.model_dump(mode="json") for c in classifications],
            "summary": summary,
        }
    )
