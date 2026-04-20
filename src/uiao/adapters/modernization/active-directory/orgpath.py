"""
active_directory/orgpath.py
---------------------------
UIAO Modernization Adapter: OrgPath Assignment Engine

Canon reference: Appendix F Phases 2–3, Appendix C (Attribute Mapping Table),
                 Appendix A (OrgPath Codebook).
Adapter class:   modernization
Mission class:   identity

Purpose
-------
Takes the ADSurveyReport from survey.py and:
  1. Builds the canonical OU→OrgPath mapping table (Phase F.2).
  2. Resolves each user's OrgPath using priority:
       HR export (authoritative) > functional OU derivation > manual queue
  3. In write mode, writes OrgPath to extensionAttribute1 in AD.
     (extensionAttribute1 is then picked up by Entra Connect on next sync cycle.)
  4. Populates extensionAttribute2 (regional dimension) if REG-* mapping provided.
  5. Sets extensionAttribute3 = ACTIVE (lifecycle state, Appendix C).
  6. Sets extensionAttribute4 = IN-PROGRESS (migration tracking, Appendix C).

This module never writes directly to Entra ID. It writes to AD and relies on
Entra Connect to propagate. This is intentional — it preserves the no-rip-and-
replace principle and allows the Governance OS drift engine to validate the
round-trip.

Output artefacts
----------------
  - ou-orgpath-mapping.csv   (Appendix F Phase 2 artefact)
  - user-orgpath-assignments.csv
  - unresolved-queue.csv     (requires manual governance review)
  - orgpath-assignment-report.json  (machine-readable, feeds walker.py)
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .survey import ADSurveyReport, DriftFinding, derive_orgpath_from_dn

ORGPATH_REGEX = re.compile(r"^ORG(-[A-Z]{2,6}){0,4}$")
REGIONAL_REGEX = re.compile(r"^REG-[A-Z]{2,8}$")


@dataclass
class UserOrgPathAssignment:
    """One resolved assignment ready for AD write-back."""
    user_dn: str
    employee_id: str
    sam_account_name: str
    orgpath: str            # extensionAttribute1 value
    region: str = ""        # extensionAttribute2 value (REG-EAST etc.) — optional
    source: str = ""        # hr | ou-derived | manual
    status: str = "pending" # pending | written | failed | skipped


@dataclass
class OrgPathAssignmentReport:
    run_timestamp: str = ""
    forest_root: str = ""
    total_users: int = 0
    assigned_from_hr: int = 0
    assigned_from_ou: int = 0
    unresolved: int = 0
    write_attempted: int = 0
    write_succeeded: int = 0
    write_failed: int = 0
    assignments: list[UserOrgPathAssignment] = field(default_factory=list)
    unresolved_queue: list[dict] = field(default_factory=list)
    findings: list[DriftFinding] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items()
             if k not in ("assignments", "unresolved_queue", "findings")}
        d["assignments"] = [a.__dict__ for a in self.assignments]
        d["unresolved_queue"] = self.unresolved_queue
        d["findings"] = [f.__dict__ for f in self.findings]
        return d


def build_ou_mapping(
    ou_classifications: dict[str, str],  # DN → intent from survey
    codebook: set[str],
    manual_overrides: Optional[dict[str, str]] = None,
) -> dict[str, Optional[str]]:
    """
    Phase F.2: Build OU DN → OrgPath mapping table.

    Parameters
    ----------
    ou_classifications : output of survey OU classification
    codebook           : set of active OrgPath codes
    manual_overrides   : explicit DN→OrgPath assignments from governance team
                         These take precedence over derivation.

    Returns
    -------
    Dict mapping each OU DN to its canonical OrgPath (or None if unresolvable).
    """
    overrides = manual_overrides or {}
    mapping: dict[str, Optional[str]] = {}

    for dn, intent in ou_classifications.items():
        if dn in overrides:
            mapping[dn] = overrides[dn]
            continue

        if intent == "functional":
            derived = derive_orgpath_from_dn(dn, codebook)
            mapping[dn] = derived
        elif intent == "geographic-active":
            # Best-effort derivation — may still yield None
            derived = derive_orgpath_from_dn(dn, codebook)
            mapping[dn] = derived
        else:
            # geographic-orphan, technical, delegation-artifact → not mappable
            mapping[dn] = None

    return mapping


def resolve_user_assignments(
    users: list[dict],   # raw AD user records: dn, employeeId, samAccountName
    hr_map: dict[str, str],         # employeeId → orgPath (HR is authoritative)
    ou_mapping: dict[str, Optional[str]],  # DN → OrgPath from build_ou_mapping
    region_map: Optional[dict[str, str]] = None,  # OU DN → REG-* value
    codebook: Optional[set[str]] = None,
) -> OrgPathAssignmentReport:
    """
    Resolve OrgPath for every user using priority:
      1. HR export (authoritative)
      2. Functional OU derivation (confirmed by ou_mapping)
      3. Unresolved queue (manual governance review required)

    Also resolves regional dimension (extensionAttribute2) from region_map
    if provided.

    Returns OrgPathAssignmentReport with full assignment list and unresolved queue.
    """
    report = OrgPathAssignmentReport(
        run_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    for user in users:
        dn: str = user.get("distinguishedName", "")
        emp_id: str = user.get("employeeId", "")
        sam: str = user.get("samAccountName", "")
        report.total_users += 1

        # Determine parent OU DN
        ou_dn = ",".join(dn.split(",")[1:]) if "," in dn else dn
        region = ""
        if region_map:
            region = region_map.get(ou_dn, "")

        # Priority 1: HR
        if emp_id and emp_id in hr_map:
            orgpath = hr_map[emp_id]
            if not ORGPATH_REGEX.match(orgpath):
                report.findings.append(DriftFinding(
                    drift_class="DRIFT-SCHEMA",
                    severity="P1",
                    path=dn,
                    detail=f"HR export provides invalid OrgPath '{orgpath}' for user {sam}. "
                           "HR data quality issue — correct at source before migration.",
                    error_code="GOV-SCH-001",
                    object_type="User",
                ))
                _add_to_unresolved(report, dn, emp_id, sam, "hr-invalid", orgpath)
                continue
            report.assigned_from_hr += 1
            report.assignments.append(UserOrgPathAssignment(
                user_dn=dn,
                employee_id=emp_id,
                sam_account_name=sam,
                orgpath=orgpath,
                region=region,
                source="hr",
            ))
            continue

        # Priority 2: OU derivation
        derived = ou_mapping.get(ou_dn)
        if derived and ORGPATH_REGEX.match(derived):
            # Validate against codebook if available
            if codebook and derived not in codebook:
                # Valid format but not in codebook — soft finding, still assign
                report.findings.append(DriftFinding(
                    drift_class="DRIFT-PROVENANCE",
                    severity="P3",
                    path=dn,
                    detail=f"Derived OrgPath '{derived}' for user {sam} is not in codebook. "
                           "Codebook may need update via Workflow 1 (OrgPath Registration).",
                    error_code="GOV-MIG-003",
                    object_type="User",
                ))
            report.assigned_from_ou += 1
            report.assignments.append(UserOrgPathAssignment(
                user_dn=dn,
                employee_id=emp_id,
                sam_account_name=sam,
                orgpath=derived,
                region=region,
                source="ou-derived",
            ))
            continue

        # Priority 3: Unresolved
        _add_to_unresolved(report, dn, emp_id, sam, "unresolvable", "")
        report.unresolved += 1
        report.findings.append(DriftFinding(
            drift_class="DRIFT-IDENTITY",
            severity="P1",
            path=dn,
            detail=f"User '{sam}' ({dn}) cannot be assigned an OrgPath from HR or OU. "
                   "Added to unresolved queue for governance review. GOV-DRF-003.",
            error_code="GOV-DRF-003",
            object_type="User",
        ))

    return report


def _add_to_unresolved(
    report: OrgPathAssignmentReport,
    dn: str, emp_id: str, sam: str,
    reason: str, partial_orgpath: str,
) -> None:
    report.unresolved_queue.append({
        "distinguishedName": dn,
        "employeeId": emp_id,
        "samAccountName": sam,
        "reason": reason,
        "partialOrgPath": partial_orgpath,
        "action": "MANUAL_REVIEW_REQUIRED",
    })


def write_orgpath_to_ad(
    assignments: list[UserOrgPathAssignment],
    ldap_server: str,
    base_dn: str,
    username: str,
    password: str,
    dry_run: bool = True,
) -> OrgPathAssignmentReport:
    """
    Phase F.3: Write OrgPath attributes back to AD extensionAttributes.

    Writes:
      extensionAttribute1 = orgpath        (OrgPath — Appendix C)
      extensionAttribute2 = region         (Regional dimension — if set)
      extensionAttribute3 = ACTIVE         (Lifecycle state — Appendix C)
      extensionAttribute4 = IN-PROGRESS    (Migration tracking — Appendix C)

    These are then picked up by Entra Connect on the next sync cycle.
    No Entra ID API calls are made here. The round-trip is:
      AD write → Entra Connect sync → Entra ID extensionAttributes populated
      → Dynamic groups compute membership → Governance OS validates.

    dry_run=True (default): validates assignments, logs what would be written,
    no AD modifications made.
    """
    report = OrgPathAssignmentReport(
        run_timestamp=datetime.now(timezone.utc).isoformat(),
        total_users=len(assignments),
    )

    if dry_run:
        report.findings.append(DriftFinding(
            drift_class="DRIFT-PROVENANCE",
            severity="P4",
            path="orgpath.py::write_orgpath_to_ad",
            detail=f"DRY RUN: {len(assignments)} assignments validated, no AD writes performed. "
                   "Set dry_run=False to execute write-back.",
            error_code="",
            object_type="adapter",
        ))
        for a in assignments:
            a.status = "skipped"
            report.assignments.append(a)
        return report

    try:
        from ldap3 import Server, Connection, ALL, MODIFY_REPLACE  # type: ignore
        srv = Server(ldap_server, get_info=ALL)
        conn = Connection(srv, user=username, password=password, auto_bind=True)

        for assignment in assignments:
            attrs: dict = {
                "extensionAttribute1": [(MODIFY_REPLACE, [assignment.orgpath])],
                "extensionAttribute3": [(MODIFY_REPLACE, ["ACTIVE"])],
                "extensionAttribute4": [(MODIFY_REPLACE, ["IN-PROGRESS"])],
            }
            if assignment.region and REGIONAL_REGEX.match(assignment.region):
                attrs["extensionAttribute2"] = [(MODIFY_REPLACE, [assignment.region])]

            try:
                conn.modify(assignment.user_dn, attrs)
                if conn.result["result"] == 0:
                    assignment.status = "written"
                    report.write_succeeded += 1
                else:
                    assignment.status = "failed"
                    report.write_failed += 1
                    report.findings.append(DriftFinding(
                        drift_class="DRIFT-PROVENANCE",
                        severity="P2",
                        path=assignment.user_dn,
                        detail=f"AD write failed for {assignment.sam_account_name}: "
                               f"{conn.result['description']}",
                        error_code="GOV-MIG-002",
                        object_type="User",
                    ))
            except Exception as e:
                assignment.status = "failed"
                report.write_failed += 1
                report.findings.append(DriftFinding(
                    drift_class="DRIFT-PROVENANCE",
                    severity="P1",
                    path=assignment.user_dn,
                    detail=f"Exception writing OrgPath for {assignment.sam_account_name}: {e}",
                    error_code="GOV-MIG-002",
                    object_type="User",
                ))
            report.write_attempted += 1
            report.assignments.append(assignment)

        conn.unbind()

    except ImportError:
        # Fall back to PowerShell
        _write_via_powershell(report, assignments, ldap_server, base_dn, username, password)

    return report


def _write_via_powershell(
    report: OrgPathAssignmentReport,
    assignments: list[UserOrgPathAssignment],
    server: str,
    base_dn: str,
    username: str,
    password: str,
) -> None:
    """
    Write OrgPath via PowerShell Set-ADUser when ldap3 is unavailable.
    Requires RSAT ActiveDirectory module on the calling machine.
    """
    ps_lines = [
        "$ErrorActionPreference = 'Stop'",
        f"$Server = '{server}'",
        "Import-Module ActiveDirectory -ErrorAction Stop",
        "$results = @()",
    ]

    for a in assignments:
        safe_dn = a.user_dn.replace("'", "''")
        safe_op = a.orgpath.replace("'", "''")
        region_line = f"extensionAttribute2 = '{a.region}'; " if a.region else ""
        ps_lines.append(
            f"try {{ Set-ADUser -Server $Server -Identity '{safe_dn}' "
            f"-Replace @{{ extensionAttribute1='{safe_op}'; "
            f"{region_line}"
            f"extensionAttribute3='ACTIVE'; extensionAttribute4='IN-PROGRESS' }}; "
            f"$results += [PSCustomObject]@{{ DN='{safe_dn}'; Status='written' }} }}"
            f" catch {{ $results += [PSCustomObject]@{{ DN='{safe_dn}'; Status='failed'; "
            f"Error=$_.Exception.Message }} }}"
        )

    ps_lines.append("$results | ConvertTo-Json -Depth 2")
    ps_script = "\n".join(ps_lines)

    try:
        result = subprocess.run(
            ["pwsh", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            report.findings.append(DriftFinding(
                drift_class="DRIFT-PROVENANCE",
                severity="P1",
                path="orgpath.py::_write_via_powershell",
                detail=f"PowerShell write-back failed: {result.stderr[:500]}",
                error_code="GOV-MIG-002",
                object_type="adapter",
            ))
            return
        raw = json.loads(result.stdout)
        if isinstance(raw, dict):
            raw = [raw]
        dn_to_assignment = {a.user_dn: a for a in assignments}
        for item in raw:
            dn = item.get("DN", "")
            status = item.get("Status", "failed")
            if dn in dn_to_assignment:
                dn_to_assignment[dn].status = status
                if status == "written":
                    report.write_succeeded += 1
                else:
                    report.write_failed += 1
            report.write_attempted += 1
        report.assignments.extend(assignments)
    except subprocess.TimeoutExpired:
        report.findings.append(DriftFinding(
            drift_class="DRIFT-PROVENANCE",
            severity="P1",
            path="orgpath.py::_write_via_powershell",
            detail="PowerShell write-back timed out. Split into smaller batches.",
            error_code="GOV-MIG-002",
            object_type="adapter",
        ))


# ------------------------------------------------------------------
# Export helpers (Appendix F artefact generation)
# ------------------------------------------------------------------

def export_ou_mapping(
    mapping: dict[str, Optional[str]],
    output_path: Path,
) -> None:
    """Export Phase F.2 artefact: ou-orgpath-mapping.csv"""
    with output_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["LegacyOU", "OrgPath", "Resolvable"])
        writer.writeheader()
        for dn, orgpath in mapping.items():
            writer.writerow({
                "LegacyOU": dn,
                "OrgPath": orgpath or "",
                "Resolvable": "Y" if orgpath else "N",
            })


def export_assignment_report(
    report: OrgPathAssignmentReport,
    output_dir: Path,
) -> None:
    """
    Export Phase F.2/F.3 artefacts:
      - user-orgpath-assignments.csv
      - unresolved-queue.csv
      - orgpath-assignment-report.json
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Assignments CSV
    with (output_dir / "user-orgpath-assignments.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "user_dn", "employee_id", "sam_account_name",
            "orgpath", "region", "source", "status",
        ])
        writer.writeheader()
        for a in report.assignments:
            writer.writerow(a.__dict__)

    # Unresolved queue CSV
    if report.unresolved_queue:
        with (output_dir / "unresolved-queue.csv").open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=[
                "distinguishedName", "employeeId", "samAccountName",
                "reason", "partialOrgPath", "action",
            ])
            writer.writeheader()
            for item in report.unresolved_queue:
                writer.writerow(item)

    # JSON report
    (output_dir / "orgpath-assignment-report.json").write_text(
        json.dumps(report.as_dict(), indent=2, default=str)
    )
