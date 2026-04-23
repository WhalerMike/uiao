"""AD forest survey endpoints.

Read-only against Active Directory. Requires Windows Authentication
(domain user or service account via Kerberos/GSSAPI).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...adapters.modernization.active_directory.survey import (
    ADSurveyReport,
    run_discovery,
)
from ..auth.kerberos import WindowsIdentity, require_windows_auth

router = APIRouter()


class SurveyRequest(BaseModel):
    ldap_server: str = Field(..., description="DC hostname or IP")
    base_dn: str = Field(..., description="Forest root DN: DC=corp,DC=contoso,DC=com")
    codebook_path: Optional[str] = Field(
        None,
        description=("Server-side path to OrgPath codebook JSON (Appendix A). If omitted, format validation only."),
    )
    hr_export_path: Optional[str] = Field(
        None,
        description=("Server-side path to HR export CSV (employeeId,orgPath). If omitted, OU derivation only."),
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


@router.post("/run", response_model=SurveyResponse)
async def run_survey(
    body: SurveyRequest,
    identity: WindowsIdentity = Depends(require_windows_auth),
) -> SurveyResponse:
    """Phase F.1: Run read-only forest archaeological survey.

    Always read-only — no AD writes.
    Returns summary + finding counts. Use /findings for full detail.
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


@router.post("/findings")
async def get_findings(
    body: SurveyRequest,
    identity: WindowsIdentity = Depends(require_windows_auth),
) -> dict:
    """Run survey and return full findings list (JSON)."""
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
