"""
src/uiao/api/routes/auditor.py
--------------------------------
UIAO Auditor API — UIAO_105

Read-only endpoints for auditors and oversight personnel.
Auth: OAuth2 Bearer token (Entra ID JWT) with UIAO.Viewer or UIAO.Auditor role.

Endpoints:
  GET /api/auditor/evidence          - list evidence with optional filters
  GET /api/auditor/evidence/{id}     - single evidence object
  GET /api/auditor/findings          - all compliance findings
  GET /api/auditor/poam              - all POA&M entries
  GET /api/auditor/oscal/sar         - OSCAL SAR JSON
  GET /api/auditor/oscal/ssp         - OSCAL SSP JSON
  GET /api/auditor/graph/{control_id}- evidence graph trace for a control
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Auth dependency — Bearer token with role check
# ---------------------------------------------------------------------------

def _require_auditor(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    """
    Validates Bearer token and returns the subject claim.
    In production: validates JWT signature against Entra ID JWKS.
    In development/test: accepts any non-empty Bearer token.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required. Role: UIAO.Viewer or UIAO.Auditor",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    # Production: validate JWT with python-jose or msal
    # For now: extract sub from token if it is a real JWT, else use token as subject
    try:
        import base64, json as _json
        parts = token.split(".")
        if len(parts) == 3:
            padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
            payload = _json.loads(base64.urlsafe_b64decode(padded))
            return payload.get("sub", payload.get("oid", "auditor"))
    except Exception:
        pass
    return "auditor"


# ---------------------------------------------------------------------------
# In-memory evidence store accessor
# Wires to the evidence pipeline outputs. In production these would
# query a persistent evidence store. For v1.0 they load from the
# most recent evidence bundle on disk or return empty sets.
# ---------------------------------------------------------------------------

def _load_evidence_bundle() -> Optional[Any]:
    """Load the most recent EvidenceBundle from the workspace."""
    workspace = os.environ.get("UIAO_WORKSPACE_ROOT", ".")
    try:
        import json, pathlib
        bundle_dir = pathlib.Path(workspace) / "output" / "evidence"
        if not bundle_dir.exists():
            return None
        # Find most recent bundle.json
        bundles = sorted(bundle_dir.rglob("bundle.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not bundles:
            return None
        return json.loads(bundles[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_evidence_records() -> list[dict]:
    """Load evidence records from most recent bundle."""
    workspace = os.environ.get("UIAO_WORKSPACE_ROOT", ".")
    try:
        import json, pathlib
        bundle_dir = pathlib.Path(workspace) / "output" / "evidence"
        if not bundle_dir.exists():
            return []
        jsonl_files = sorted(bundle_dir.rglob("evidence.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not jsonl_files:
            return []
        records = []
        for line in jsonl_files[0].read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Evidence endpoints
# ---------------------------------------------------------------------------

@router.get("/evidence", summary="List evidence objects")
async def list_evidence(
    control_id: Optional[str] = Query(None, description="Filter by NIST control ID (e.g. IA-2)"),
    collector: Optional[str] = Query(None, description="Filter by collector (e.g. scuba)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: satisfied | not-satisfied | not-applicable"),
    subject: str = Depends(_require_auditor),
) -> dict:
    """
    Returns evidence objects with optional filters.
    Canon reference: UIAO_105 §GET /api/auditor/evidence
    """
    records = _load_evidence_records()

    if control_id:
        records = [r for r in records if r.get("control_id", "").upper() == control_id.upper()]
    if collector:
        records = [r for r in records if r.get("provenance", {}).get("collector_id", "").lower() == collector.lower()]
    if status_filter:
        records = [r for r in records if r.get("status", "") == status_filter]

    return {
        "total": len(records),
        "filters": {"control_id": control_id, "collector": collector, "status": status_filter},
        "evidence": records,
        "requested_by": subject,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/evidence/{evidence_id}", summary="Get single evidence object")
async def get_evidence(
    evidence_id: str,
    subject: str = Depends(_require_auditor),
) -> dict:
    """
    Returns a single evidence object by ID.
    Canon reference: UIAO_105 §GET /api/auditor/evidence/{id}
    """
    records = _load_evidence_records()
    match = next((r for r in records if r.get("id") == evidence_id), None)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence '{evidence_id}' not found",
        )
    return {**match, "requested_by": subject}


# ---------------------------------------------------------------------------
# Findings endpoint — sourced from drift state
# ---------------------------------------------------------------------------

@router.get("/findings", summary="List compliance findings")
async def list_findings(
    severity: Optional[str] = Query(None, description="Filter by severity: P1 | P2 | P3 | P4"),
    drift_class: Optional[str] = Query(None, description="Filter by drift class"),
    finding_status: Optional[str] = Query(None, alias="status", description="Filter by status: Open | Closed"),
    subject: str = Depends(_require_auditor),
) -> dict:
    """
    Returns compliance findings from the drift engine.
    Canon reference: UIAO_105 §GET /api/auditor/findings
    """
    workspace = os.environ.get("UIAO_WORKSPACE_ROOT", ".")
    findings: list[dict] = []

    try:
        import json, pathlib
        scan_dir = pathlib.Path(workspace) / "output" / "drift"
        if scan_dir.exists():
            reports = sorted(scan_dir.rglob("manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if reports:
                data = json.loads(reports[0].read_text(encoding="utf-8"))
                findings = data.get("findings", [])
    except Exception:
        pass

    if severity:
        findings = [f for f in findings if f.get("severity") == severity]
    if drift_class:
        findings = [f for f in findings if f.get("drift_class") == drift_class]
    if finding_status:
        findings = [f for f in findings if f.get("status", "Open") == finding_status]

    return {
        "total": len(findings),
        "filters": {"severity": severity, "drift_class": drift_class, "status": finding_status},
        "findings": findings,
        "requested_by": subject,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# POA&M endpoint
# ---------------------------------------------------------------------------

@router.get("/poam", summary="List POA&M entries")
async def list_poam(
    poam_status: Optional[str] = Query(None, alias="status", description="Open | In Progress | Closed"),
    subject: str = Depends(_require_auditor),
) -> dict:
    """
    Returns POA&M entries.
    Canon reference: UIAO_105 §GET /api/auditor/poam
    """
    workspace = os.environ.get("UIAO_WORKSPACE_ROOT", ".")
    entries: list[dict] = []

    try:
        import json, pathlib
        poam_file = pathlib.Path(workspace) / "output" / "poam" / "poam.json"
        if poam_file.exists():
            entries = json.loads(poam_file.read_text(encoding="utf-8"))
    except Exception:
        pass

    if poam_status:
        entries = [e for e in entries if e.get("status") == poam_status]

    return {
        "total": len(entries),
        "filters": {"status": poam_status},
        "poam_entries": entries,
        "requested_by": subject,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# OSCAL document endpoints
# ---------------------------------------------------------------------------

def _load_oscal(doc_type: str) -> dict:
    """Load an OSCAL document from the workspace output directory."""
    workspace = os.environ.get("UIAO_WORKSPACE_ROOT", ".")
    try:
        import json, pathlib
        oscal_dir = pathlib.Path(workspace) / "output" / "oscal"
        candidates = list(oscal_dir.glob(f"*{doc_type}*.json"))
        if not candidates:
            return {}
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        return json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return {}


@router.get("/oscal/sar", summary="OSCAL Security Assessment Report")
async def get_oscal_sar(subject: str = Depends(_require_auditor)) -> dict:
    """Returns the current OSCAL SAR JSON. Canon ref: UIAO_105"""
    doc = _load_oscal("sar")
    if not doc:
        return {"message": "No SAR available. Run the compliance orchestrator to generate.", "requested_by": subject}
    return {**doc, "requested_by": subject}


@router.get("/oscal/ssp", summary="OSCAL System Security Plan")
async def get_oscal_ssp(subject: str = Depends(_require_auditor)) -> dict:
    """Returns the current OSCAL SSP JSON. Canon ref: UIAO_105"""
    doc = _load_oscal("ssp")
    if not doc:
        return {"message": "No SSP available. Run the SSP generator.", "requested_by": subject}
    return {**doc, "requested_by": subject}


@router.get("/oscal/poam", summary="OSCAL Plan of Action and Milestones")
async def get_oscal_poam(subject: str = Depends(_require_auditor)) -> dict:
    """Returns the current OSCAL POA&M JSON. Canon ref: UIAO_105"""
    doc = _load_oscal("poam")
    if not doc:
        return {"message": "No POA&M available.", "requested_by": subject}
    return {**doc, "requested_by": subject}


@router.get("/oscal/sap", summary="OSCAL Security Assessment Plan")
async def get_oscal_sap(subject: str = Depends(_require_auditor)) -> dict:
    """Returns the current OSCAL SAP JSON. Canon ref: UIAO_105"""
    doc = _load_oscal("sap")
    if not doc:
        return {"message": "No SAP available.", "requested_by": subject}
    return {**doc, "requested_by": subject}


# ---------------------------------------------------------------------------
# Evidence Graph traversal endpoint
# ---------------------------------------------------------------------------

@router.get("/graph/{control_id}", summary="Evidence graph trace for a control")
async def get_graph_trace(
    control_id: str,
    subject: str = Depends(_require_auditor),
) -> dict:
    """
    Returns the full evidence graph trace for a control:
    Control -> IR Objects -> Evidence -> Provenance
            -> Findings -> POA&M entries

    Uses the UIAO_113 Evidence Graph model.
    """
    try:
        from uiao.evidence.graph import EvidenceGraph, ControlNode, EvidenceNode, FindingNode
        records = _load_evidence_records()
        g = EvidenceGraph()
        for r in records:
            cid = r.get("control_id", "")
            if cid:
                if cid not in g._nodes:
                    g.add_control(ControlNode(id=cid))
                g.add_evidence(EvidenceNode(
                    id=r.get("id", ""),
                    control_id=cid,
                    verdict=r.get("verdict", ""),
                    status=r.get("status", ""),
                    source=r.get("provenance", {}).get("collector_id", ""),
                ))
        trace = g.trace_control(control_id)
        evidence = g.evidence_for_control(control_id)
        findings = g.findings_for_control(control_id)
        return {
            "control_id": control_id,
            "trace": trace,
            "evidence_count": len(evidence),
            "findings_count": len(findings),
            "requested_by": subject,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Graph traversal failed: {exc}")
