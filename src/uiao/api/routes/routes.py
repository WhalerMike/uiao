"""
impl/src/uiao/impl/api/routes/health.py
impl/src/uiao/impl/api/routes/survey.py
impl/src/uiao/impl/api/routes/orgpath.py

Consolidated into one file for clarity — split into separate files
when placing into the repo (each class/router goes to its own file).
"""

# ======================================================================
# health.py
# ======================================================================
from __future__ import annotations

import os
import platform
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..auth.entra_token import EntraTokenProvider

health_router = APIRouter()  # rename to `router` in health.py


class HealthResponse(BaseModel):
    status: str
    server: str
    python_version: str
    ad_reachable: bool
    entra_reachable: bool
    workspace_root_exists: bool
    detail: str = ""


@health_router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """
    Health check — no auth required.
    Verifies: AD LDAP reachable, Entra token acquirable, workspace root present.
    """
    workspace = os.environ.get("UIAO_WORKSPACE_ROOT", "")
    workspace_ok = Path(workspace).is_dir() if workspace else False

    # Try LDAP ping — just open a socket to port 389
    ad_server = os.environ.get("UIAO_AD_DEFAULT_SERVER", "")
    ad_ok = False
    if ad_server:
        import socket

        try:
            socket.setdefaulttimeout(3)
            with socket.create_connection((ad_server, 389)):
                ad_ok = True
        except (TimeoutError, OSError):
            ad_ok = False

    # Try Entra token
    entra_ok = False
    entra_detail = ""
    token_provider: EntraTokenProvider = request.app.state.token_provider
    try:
        token_provider.get_token()
        entra_ok = True
    except RuntimeError as e:
        entra_detail = str(e)

    overall = "healthy" if (ad_ok and entra_ok and workspace_ok) else "degraded"

    return HealthResponse(
        status=overall,
        server=platform.node(),
        python_version=platform.python_version(),
        ad_reachable=ad_ok,
        entra_reachable=entra_ok,
        workspace_root_exists=workspace_ok,
        detail=entra_detail,
    )


# ======================================================================
# survey.py
# ======================================================================
from typing import Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

from ...adapters.modernization.active_directory.survey import (
    ADSurveyReport,
    run_discovery,
)
from ..auth.kerberos import WindowsIdentity, require_windows_auth

survey_router = APIRouter()  # rename to `router` in survey.py


class SurveyRequest(BaseModel):
    ldap_server: str = Field(..., description="DC hostname or IP")
    base_dn: str = Field(..., description="Forest root DN: DC=corp,DC=contoso,DC=com")
    codebook_path: Optional[str] = Field(
        None, description="Server-side path to OrgPath codebook JSON (Appendix A). If omitted, format validation only."
    )
    hr_export_path: Optional[str] = Field(
        None, description="Server-side path to HR export CSV (employeeId,orgPath). If omitted, OU derivation only."
    )
    include_computers: bool = Field(False, description="Include computer object survey (slower on large forests).")


class SurveyResponse(BaseModel):
    forest_root: str
    ok: bool
    blocker_count: int
    ou_total: int
    ou_functional: int
    ou_geographic_active: int
    ou_geographic_orphan: int
    ou_technical: int
    ou_delegation_artifact: int
    user_total: int
    user_hr_resolvable: int
    user_orgpath_derived: int
    user_unresolvable: int
    sa_total: int
    sa_adcs_dependent: int
    site_total: int
    site_stale: int
    findings_count: int
    findings_p1: int
    findings_p2: int
    requested_by: str


@survey_router.post("/run", response_model=SurveyResponse)
async def run_survey(
    body: SurveyRequest,
    identity: WindowsIdentity = Depends(require_windows_auth),
) -> SurveyResponse:
    """
    Phase F.1: Run read-only forest archaeological survey.

    Always read-only — no AD writes.
    Requires Windows Authentication (domain user or service account).
    Returns summary + finding counts. Use /survey/findings for full detail.
    """
    cb_path = Path(body.codebook_path) if body.codebook_path else None
    hr_path = Path(body.hr_export_path) if body.hr_export_path else None

    try:
        report: ADSurveyReport = run_discovery(
            ldap_server=body.ldap_server,
            base_dn=body.base_dn,
            username="",  # empty = use GSSAPI/Kerberos (Windows)
            password="",
            hr_export_path=hr_path,
            codebook_path=cb_path,
            dry_run=True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Survey failed: {exc}",
        ) from exc

    p1 = sum(1 for f in report.findings if f.severity == "P1")
    p2 = sum(1 for f in report.findings if f.severity == "P2")

    return SurveyResponse(
        forest_root=report.forest_root,
        ok=report.ok,
        blocker_count=len(report.blockers),
        ou_total=report.ou_total,
        ou_functional=report.ou_functional,
        ou_geographic_active=report.ou_geographic_active,
        ou_geographic_orphan=report.ou_geographic_orphan,
        ou_technical=report.ou_technical,
        ou_delegation_artifact=report.ou_delegation_artifact,
        user_total=report.user_total,
        user_hr_resolvable=report.user_hr_resolvable,
        user_orgpath_derived=report.user_orgpath_derived,
        user_unresolvable=report.user_unresolvable,
        sa_total=report.sa_total,
        sa_adcs_dependent=report.sa_adcs_dependent,
        site_total=report.site_total,
        site_stale=report.site_stale,
        findings_count=len(report.findings),
        findings_p1=p1,
        findings_p2=p2,
        requested_by=identity.username,
    )


@survey_router.post("/findings")
async def get_findings(
    body: SurveyRequest,
    identity: WindowsIdentity = Depends(require_windows_auth),
) -> dict:
    """
    Run survey and return full findings list (JSON).
    Use when you need the complete DriftFinding detail for governance review.
    """
    cb_path = Path(body.codebook_path) if body.codebook_path else None
    hr_path = Path(body.hr_export_path) if body.hr_export_path else None

    try:
        report = run_discovery(
            ldap_server=body.ldap_server,
            base_dn=body.base_dn,
            username="",
            password="",
            hr_export_path=hr_path,
            codebook_path=cb_path,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "requested_by": identity.username,
        "report": report.as_dict(),
    }


# ======================================================================
# orgpath.py
# ======================================================================
from fastapi import APIRouter as _APIRouter

from ...adapters.modernization.active_directory.orgpath import (
    export_assignment_report,
    resolve_user_assignments,
    write_orgpath_to_ad,
)

orgpath_router = _APIRouter()  # rename to `router` in orgpath.py


class OrgPathAssignRequest(BaseModel):
    ldap_server: str
    base_dn: str
    codebook_path: Optional[str] = None
    hr_export_path: Optional[str] = None
    output_dir: Optional[str] = Field(
        None,
        description="Server-side directory to write CSV/JSON artefacts (Appendix F). "
        "If omitted, artefacts are returned in response body only.",
    )
    dry_run: bool = Field(
        True,
        description="MUST be explicitly set to false to write extensionAttributes to AD. "
        "Default true — validates and reports without any AD changes.",
    )


@orgpath_router.post("/assign")
async def assign_orgpaths(
    body: OrgPathAssignRequest,
    identity: WindowsIdentity = Depends(require_windows_auth),
) -> dict:
    """
    Phase F.2 + F.3: OrgPath assignment and optional AD write-back.

    dry_run=true (default): resolves assignments, writes artefacts, NO AD changes.
    dry_run=false: writes extensionAttribute1-4 to AD.
                   Entra Connect picks up on next sync cycle.

    GOVERNANCE NOTE: dry_run=false should only be executed after:
      1. dry_run=true report reviewed and approved by Governance Steward.
      2. unresolved-queue.csv reduced to acceptable count.
      3. Pre-write snapshot taken (run /survey/run first).
    """
    # First run a survey to get OU classifications
    from ...adapters.modernization.active_directory.survey import run_discovery

    cb_path = Path(body.codebook_path) if body.codebook_path else None
    hr_path = Path(body.hr_export_path) if body.hr_export_path else None

    run_discovery(
        ldap_server=body.ldap_server,
        base_dn=body.base_dn,
        username="",
        password="",
        hr_export_path=hr_path,
        codebook_path=cb_path,
    )

    # Load codebook
    codebook: set[str] = set()
    if cb_path and cb_path.exists():
        import json

        raw = json.loads(cb_path.read_text())
        codebook = {e["code"] for e in raw.get("entries", []) if e.get("status") == "active"}

    # Load HR map
    hr_map: dict[str, str] = {}
    if hr_path and hr_path.exists():
        import csv

        with hr_path.open(newline="") as fh:
            for row in csv.DictReader(fh):
                eid = row.get("employeeId", "").strip()
                op = row.get("orgPath", "").strip()
                if eid and op:
                    hr_map[eid] = op

    # Build OU mapping — we need the raw survey data
    # In production this would be wired through the survey report
    ou_mapping: dict = {}  # placeholder — wire from survey.ou_intent_map

    # Resolve assignments
    assignment_report = resolve_user_assignments(
        users=[],  # wire from survey user list
        hr_map=hr_map,
        ou_mapping=ou_mapping,
        codebook=codebook,
    )

    # Write artefacts if output_dir specified
    if body.output_dir:
        out = Path(body.output_dir)
        export_assignment_report(assignment_report, out)

    # Write-back if not dry_run
    if not body.dry_run:
        write_report = write_orgpath_to_ad(
            assignments=assignment_report.assignments,
            ldap_server=body.ldap_server,
            base_dn=body.base_dn,
            username="",
            password="",
            dry_run=False,
        )
        return {
            "requested_by": identity.username,
            "dry_run": False,
            "assignment_report": assignment_report.as_dict(),
            "write_report": write_report.as_dict(),
        }

    return {
        "requested_by": identity.username,
        "dry_run": True,
        "assignment_report": assignment_report.as_dict(),
    }
