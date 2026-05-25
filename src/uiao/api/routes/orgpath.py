"""Per-facet OrgPath API — Model C (ADR-084 §C7, §C9 Phase 5 #7).

Read-only HTTP surface over the in-process per-facet
:py:class:`uiao.modernization.orgtree.codebook.Codebook`. Per ADR-084
§C7 the route is **observability-only** — remediation flows via the
drift engine's ``apply()`` so the Evidence Fabric records every write.
There is no POST/PATCH/DELETE on this surface (POST ``/validate`` is
the one exception: it's a read-only validity probe, not a write).

Endpoints:

* ``GET /api/v1/orgpath/codebook`` — return the loaded Codebook as JSON
* ``GET /api/v1/orgpath/principals/{id}/facets`` — return one
  principal's 10 facet values (requires a snapshot supplier; see
  ``set_snapshot_supplier()``)
* ``GET /api/v1/orgpath/drift`` — return the most recent
  ``DriftFinding`` array (requires a report supplier; see
  ``set_report_supplier()``)
* ``POST /api/v1/orgpath/validate`` — accept ``{facet, value}``,
  return ``{is_active, is_deprecated, replacement_for}``

The route depends only on the per-facet Codebook; snapshot and report
data are injected via supplier callables to keep the route offline-
testable (no Graph mock, no scheduled job).
"""

from __future__ import annotations

from typing import Callable, Mapping

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from uiao.governance.drift_engine import DriftScanReport
from uiao.modernization.orgtree.codebook import Codebook, Facet, default_codebook
from uiao.modernization.orgtree.types import PrincipalSnapshot

router = APIRouter()


# ---------------------------------------------------------------------------
# Supplier registry — injected at app startup so the route stays pure
# ---------------------------------------------------------------------------

_codebook_supplier: Callable[[], Codebook] = default_codebook
_principal_supplier: Callable[[str], PrincipalSnapshot | None] | None = None
_report_supplier: Callable[[], DriftScanReport | None] | None = None


def set_codebook_supplier(supplier: Callable[[], Codebook]) -> None:
    """Override the default Codebook supplier (used in tests / non-default deployments)."""
    global _codebook_supplier
    _codebook_supplier = supplier


def set_principal_supplier(
    supplier: Callable[[str], PrincipalSnapshot | None] | None,
) -> None:
    """Inject the per-principal snapshot lookup (called by the engine's snapshot job)."""
    global _principal_supplier
    _principal_supplier = supplier


def set_report_supplier(
    supplier: Callable[[], DriftScanReport | None] | None,
) -> None:
    """Inject the most-recent-report supplier (called by the engine's scan job)."""
    global _report_supplier
    _report_supplier = supplier


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class FacetValueResponse(BaseModel):
    value: str
    description: str
    status: str = "active"


class DeprecatedValueResponse(BaseModel):
    value: str
    replaced_by: str
    reason: str | None = None


class FacetResponse(BaseModel):
    name: str
    attribute: str
    kind: str
    description: str
    enumeration: list[FacetValueResponse] = []
    deprecated: list[DeprecatedValueResponse] = []
    value_type: str | None = None
    value_pattern: str | None = None
    allow_empty: bool = False


class CodebookResponse(BaseModel):
    schema_version: str
    document_id: str
    model: str
    facets: list[FacetResponse]


class PrincipalFacetsResponse(BaseModel):
    principal_id: str
    principal_type: str
    facets: Mapping[str, str]


class ValidateRequest(BaseModel):
    facet: str
    value: str


class ValidateResponse(BaseModel):
    facet: str
    value: str
    is_active: bool
    is_deprecated: bool
    replacement_for: str | None = None


class DriftFindingResponse(BaseModel):
    facet: str
    attribute: str
    observed_value: str | None
    drift_category: str
    severity: str
    reason: str
    target: str
    auto_remediate: bool
    timestamp: str


class DriftReportResponse(BaseModel):
    snapshot_id: str
    generated_at: str
    dry_run: bool
    halted: bool
    finding_count: int
    severity_counts: Mapping[str, int]
    findings: list[DriftFindingResponse]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/codebook", response_model=CodebookResponse)
def get_codebook() -> CodebookResponse:
    """Return the loaded per-facet Codebook."""
    cb = _codebook_supplier()
    facets = [_serialize_facet(f) for f in cb.facets.values()]
    return CodebookResponse(
        schema_version=cb.schema_version,
        document_id=cb.document_id,
        model=cb.model,
        facets=facets,
    )


@router.get(
    "/principals/{principal_id}/facets",
    response_model=PrincipalFacetsResponse,
)
def get_principal_facets(principal_id: str) -> PrincipalFacetsResponse:
    """Return one principal's 10 facet values."""
    if _principal_supplier is None:
        raise HTTPException(
            status_code=503,
            detail="No principal supplier configured. Engine snapshot job must register one via set_principal_supplier().",
        )
    snap = _principal_supplier(principal_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Principal '{principal_id}' not found")
    return PrincipalFacetsResponse(
        principal_id=snap.principal_id,
        principal_type=snap.principal_type,
        facets=snap.attributes,
    )


@router.get("/drift", response_model=DriftReportResponse)
def get_drift() -> DriftReportResponse:
    """Return the most recent per-facet DriftScanReport."""
    if _report_supplier is None:
        raise HTTPException(
            status_code=503,
            detail="No drift report supplier configured. Engine scan job must register one via set_report_supplier().",
        )
    report = _report_supplier()
    if report is None:
        raise HTTPException(status_code=404, detail="No drift report available yet")
    return DriftReportResponse(
        snapshot_id=report.snapshot_id,
        generated_at=report.generated_at,
        dry_run=report.dry_run,
        halted=report.halted,
        finding_count=report.finding_count,
        severity_counts=report.severity_counts,
        findings=[
            DriftFindingResponse(
                facet=f.facet,
                attribute=f.attribute,
                observed_value=f.observed_value,
                drift_category=f.drift_category,
                severity=f.severity,
                reason=f.reason,
                target=f.target,
                auto_remediate=f.auto_remediate,
                timestamp=f.timestamp,
            )
            for f in report.findings
        ],
    )


@router.post("/validate", response_model=ValidateResponse)
def validate(body: ValidateRequest) -> ValidateResponse:
    """Validate one facet value against the codebook (read-only probe)."""
    cb = _codebook_supplier()
    try:
        facet = cb.facet(body.facet)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown facet '{body.facet}'") from exc
    return ValidateResponse(
        facet=body.facet,
        value=body.value,
        is_active=facet.is_active(body.value),
        is_deprecated=facet.is_deprecated(body.value),
        replacement_for=facet.replacement_for(body.value),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_facet(facet: Facet) -> FacetResponse:
    return FacetResponse(
        name=facet.name,
        attribute=facet.attribute,
        kind=facet.kind,
        description=facet.description,
        enumeration=[FacetValueResponse(value=v.value, description=v.description) for v in facet.enumeration.values()],
        deprecated=[
            DeprecatedValueResponse(value=d.value, replaced_by=d.replaced_by, reason=d.reason)
            for d in facet.deprecated.values()
        ],
        value_type=facet.value_type,
        value_pattern=facet.value_pattern,
        allow_empty=facet.allow_empty,
    )
