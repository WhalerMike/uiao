"""OrgPath assignment endpoints.

Phase F.2 + F.3: resolve user OrgPath assignments and (optionally) write
extensionAttributes back to Active Directory. Write-back is gated by
`dry_run: false` and should only run after governance review of the
dry-run artefacts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ...adapters.modernization.active_directory.orgpath import (
    export_assignment_report,
    resolve_user_assignments,
    write_orgpath_to_ad,
)
from ..auth.kerberos import WindowsIdentity, require_windows_auth

router = APIRouter()


class OrgPathAssignRequest(BaseModel):
    ldap_server: str
    base_dn: str
    codebook_path: Optional[str] = None
    hr_export_path: Optional[str] = None
    output_dir: Optional[str] = Field(
        None,
        description=(
            "Server-side directory to write CSV/JSON artefacts (Appendix F). "
            "If omitted, artefacts are returned in response body only."
        ),
    )
    dry_run: bool = Field(
        True,
        description=(
            "MUST be explicitly set to false to write extensionAttributes to AD. "
            "Default true — validates and reports without any AD changes."
        ),
    )


@router.post("/assign")
async def assign_orgpaths(
    body: OrgPathAssignRequest,
    identity: WindowsIdentity = Depends(require_windows_auth),
) -> dict:
    """Phase F.2 + F.3: OrgPath assignment and optional AD write-back.

    dry_run=true (default): resolves assignments, writes artefacts, NO AD changes.
    dry_run=false: writes extensionAttribute1-4 to AD. Entra Connect picks up on
    the next sync cycle.

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
