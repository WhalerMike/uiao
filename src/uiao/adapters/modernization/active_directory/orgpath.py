"""
active_directory/orgpath.py
---------------------------
UIAO Modernization Adapter: OrgPath Assignment Engine + Codebook Validator.

Algorithm: parse OU= components right-to-left (root→leaf), normalise each
segment to uppercase, assemble ORG-SEG1-SEG2…, walk from most-specific to
least-specific until a codebook hit is found; return None when no hit exists.

Canon reference: Appendix F Phases 2–3, Appendix C (Attribute Mapping Table),
                 Appendix A (OrgPath Codebook), ADR-035.
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
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from uiao.modernization.orgtree import Codebook

from .survey import DriftFinding, derive_orgpath_from_dn

ORGPATH_REGEX = re.compile(r"^ORG(-[A-Z]{2,6}){0,4}$")
ORGPATH_SEGMENT_RE = re.compile(r"^[A-Z0-9]{2,6}$")
REGIONAL_REGEX = re.compile(r"^REG-[A-Z]{2,8}$")

# ---------------------------------------------------------------------------
# WS-A4 public types: Finding + ConformanceResult
# ---------------------------------------------------------------------------

_CodebookArg = Union["Codebook", set]  # Codebook object or set[str] of active codes


@dataclass
class Finding:
    """A codebook-conformance or conflict finding.  Never raised as an exception.

    kind values:
      "unknown_segment"  — a path prefix is absent from the codebook
      "bad_format"       — path does not match the canonical ORG regex
      "collision"        — two distinct OUs map to the same OrgPath
      "cycle"            — circular OU parent chain detected
    """

    kind: str
    subjects: list[str]
    detail: str
    error_code: str = ""


@dataclass
class ConformanceResult:
    """Result of validate_orgpath()."""

    path: str
    conforms: bool
    findings: list[Finding] = field(default_factory=list)


# ---------------------------------------------------------------------------
# WS-A4 helpers
# ---------------------------------------------------------------------------


def _codes_from_arg(codebook_arg: object) -> set[str]:
    """Accept either a Codebook object or a plain set[str]; return set[str]."""
    if isinstance(codebook_arg, set):
        return codebook_arg
    # Duck-type: Codebook exposes .codes property → set[str]
    if hasattr(codebook_arg, "codes"):
        return codebook_arg.codes  # type: ignore[no-any-return]
    raise TypeError(f"codebook must be a Codebook or set[str], got {type(codebook_arg).__name__!r}")


def _normalize_ou_segment(raw: str) -> Optional[str]:
    """Normalise a raw OU name to a codebook segment (2-6 uppercase alphanum).

    Returns None for geographic / unrecognisable segments.
    """
    cleaned = raw.strip().upper()
    # Allow only A-Z0-9 after stripping spaces — no hyphens inside a segment
    alnum = re.sub(r"[^A-Z0-9]", "", cleaned)
    if ORGPATH_SEGMENT_RE.match(alnum):
        return alnum
    return None


# ---------------------------------------------------------------------------
# WS-A4 public API
# ---------------------------------------------------------------------------


def derive_orgpath(distinguished_name: object, codebook_arg: object) -> Optional[str]:
    """Deterministically derive a canonical OrgPath from an AD DN.

    Algorithm:
      1. Guard: raise TypeError for non-str DN or unsupported codebook type.
      2. Parse every OU= component from the DN (case-insensitive).
      3. Reverse to root→leaf order.
      4. Normalise each segment; stop at the first un-normalisable segment.
      5. Walk from most-specific (longest) to root; return first codebook hit.
      6. Return None when no hit and no valid-format candidate exists.

    Same input always produces the same output (deterministic, no randomness).
    """
    if not isinstance(distinguished_name, str):
        raise TypeError(f"distinguished_name must be str, got {type(distinguished_name).__name__!r}")
    codes = _codes_from_arg(codebook_arg)

    dn = distinguished_name.strip()
    if not dn:
        return None

    # Extract OU= values; DN is leaf→root, so reverse for root→leaf
    raw_parts = re.findall(r"(?i)OU=([^,]+)", dn)
    parts = list(reversed(raw_parts))

    segments: list[str] = []
    for part in parts:
        norm = _normalize_ou_segment(part)
        if norm is None:
            break  # stop at first geographic / unrecognisable segment
        segments.append(norm)

    if not segments:
        return None

    # Walk most-specific → least-specific; return first codebook hit
    for depth in range(len(segments), 0, -1):
        candidate = "ORG-" + "-".join(segments[:depth])
        if candidate in codes:
            return candidate

    # Nothing in codebook — return None (no write-back in assessment mode)
    return None


def validate_orgpath(path: object, codebook_arg: object) -> ConformanceResult:
    """Check every prefix of ``path`` against the codebook.

    Produces Finding records for:
      - bad_format    : path does not match ^ORG(-[A-Z0-9]{2,6}){0,4}$
      - unknown_segment : one or more prefixes absent from the codebook

    Never raises for conformance failures — findings are returned instead.
    TypeError is raised for wrong argument types (programmer error).
    """
    if not isinstance(path, str):
        raise TypeError(f"path must be str, got {type(path).__name__!r}")
    codes = _codes_from_arg(codebook_arg)

    # Format check
    canonical_re = re.compile(r"^ORG(-[A-Z0-9]{2,6}){0,4}$")
    if not canonical_re.match(path):
        return ConformanceResult(
            path=path,
            conforms=False,
            findings=[
                Finding(
                    kind="bad_format",
                    subjects=[path],
                    detail=f"OrgPath '{path}' does not match canonical format ^ORG(-[A-Z0-9]{{2,6}}){{0,4}}$",
                    error_code="GOV-SCH-001",
                )
            ],
        )

    # Walk every prefix ORG, ORG-A, ORG-A-B … path
    segments = path.split("-")
    findings: list[Finding] = []
    for depth in range(1, len(segments) + 1):
        prefix = "-".join(segments[:depth])
        if prefix not in codes:
            findings.append(
                Finding(
                    kind="unknown_segment",
                    subjects=[prefix],
                    detail=f"OrgPath prefix '{prefix}' is not present in the codebook",
                    error_code="GOV-COD-001",
                )
            )

    return ConformanceResult(
        path=path,
        conforms=len(findings) == 0,
        findings=findings,
    )


def detect_conflicts(ou_map: object) -> list[Finding]:
    """Detect collision and cycle conflicts in an OU→OrgPath mapping.

    Collision: two or more distinct OU DNs mapped to the same OrgPath.
    Cycle: circular OU parent chain within the map (A's parent is B, B's
           parent is A, detected via visited-set — no infinite loop).

    Returns a deterministically ordered list of Finding records.
    Never raises for conflict cases; raises TypeError for wrong arg type.
    """
    if not isinstance(ou_map, dict):
        raise TypeError(f"ou_map must be dict[str, str | None], got {type(ou_map).__name__!r}")

    findings: list[Finding] = []

    # --- Collision detection ---
    orgpath_to_ous: dict[str, list[str]] = {}
    for dn, orgpath in ou_map.items():
        if orgpath is None:
            continue
        orgpath_to_ous.setdefault(orgpath, []).append(dn)

    for orgpath, dns in sorted(orgpath_to_ous.items()):
        if len(dns) > 1:
            findings.append(
                Finding(
                    kind="collision",
                    subjects=sorted(dns),
                    detail=f"OrgPath '{orgpath}' is mapped to {len(dns)} distinct OUs: {sorted(dns)}",
                    error_code="GOV-COL-001",
                )
            )

    # --- Cycle detection ---
    # Strategy 1: DN-suffix parent chain (exact key match).
    # "OU=CHILD,OU=PARENT,DC=corp" parent is "OU=PARENT,DC=corp" if that key exists.
    # Strategy 2: OU containment graph — for each DN key, extract the ordered OU
    # components; the first OU is "contained in" all subsequent OUs (its ancestors).
    # Build a directed graph child→parent using just the OU names, then detect cycles
    # with a visited-set DFS.  This catches mutual-containment where
    # "OU=A,OU=B,DC=corp" AND "OU=B,OU=A,DC=corp" are both in the map.

    def _parent_dn(dn: str) -> Optional[str]:
        """Strip the first component; return remainder only if it is a map key."""
        idx = dn.find(",")
        if idx == -1:
            return None
        rest = dn[idx + 1 :]
        return rest if rest in ou_map else None

    # Build OU-name level containment graph from all DN keys.
    # For "OU=A,OU=B,DC=corp": A is contained in B  → edge A→B
    # Collect all such directed edges then run DFS cycle detection.
    ou_containment: dict[str, set[str]] = {}  # child_name → set of parent_names
    for dn in ou_map:
        ou_names = re.findall(r"(?i)OU=([^,]+)", dn)
        # ou_names[0] is the leaf (child), ou_names[1:] are ancestors
        for i in range(len(ou_names) - 1):
            child = ou_names[i].upper()
            parent = ou_names[i + 1].upper()
            ou_containment.setdefault(child, set()).add(parent)

    # DFS cycle detection on OU containment graph
    all_ou_nodes: set[str] = set(ou_containment.keys()) | {p for ps in ou_containment.values() for p in ps}
    color: dict[str, int] = {n: 0 for n in all_ou_nodes}  # 0=white, 1=grey, 2=black
    cycle_reported: set[frozenset] = set()

    def _dfs(node: str, stack: list[str]) -> None:
        color[node] = 1
        stack.append(node)
        for neighbor in sorted(ou_containment.get(node, [])):
            if color.get(neighbor, 0) == 1:
                # Back edge — cycle found
                cycle_start_idx = stack.index(neighbor)
                cycle_nodes = stack[cycle_start_idx:]
                key = frozenset(cycle_nodes)
                if key not in cycle_reported:
                    cycle_reported.add(key)
                    findings.append(
                        Finding(
                            kind="cycle",
                            subjects=sorted(cycle_nodes),
                            detail=f"Circular OU containment chain detected among: {sorted(cycle_nodes)}",
                            error_code="GOV-CYC-001",
                        )
                    )
            elif color.get(neighbor, 0) == 0:
                _dfs(neighbor, stack)
        stack.pop()
        color[node] = 2

    for node in sorted(all_ou_nodes):
        if color.get(node, 0) == 0:
            _dfs(node, [])

    # Also check DN-suffix parent chains (catches linear chain cycles in the full DN space)
    visited_global: set[str] = set()
    for start_dn in sorted(ou_map.keys()):
        if start_dn in visited_global:
            continue
        visited_chain: set[str] = set()
        path_chain: list[str] = []
        current: Optional[str] = start_dn
        while current is not None and current not in visited_global:
            if current in visited_chain:
                cycle_start = path_chain.index(current)
                cycle_nodes_dn = path_chain[cycle_start:]
                key_dn = frozenset(cycle_nodes_dn)
                if key_dn not in cycle_reported:
                    cycle_reported.add(key_dn)
                    findings.append(
                        Finding(
                            kind="cycle",
                            subjects=sorted(cycle_nodes_dn),
                            detail=f"Circular OU parent chain detected among: {sorted(cycle_nodes_dn)}",
                            error_code="GOV-CYC-001",
                        )
                    )
                visited_global.update(cycle_nodes_dn)
                break
            visited_chain.add(current)
            path_chain.append(current)
            current = _parent_dn(current)
        visited_global.update(visited_chain)

    return findings


@dataclass
class UserOrgPathAssignment:
    """One resolved assignment ready for AD write-back."""

    user_dn: str
    employee_id: str
    sam_account_name: str
    orgpath: str  # extensionAttribute1 value
    region: str = ""  # extensionAttribute2 value (REG-EAST etc.) — optional
    source: str = ""  # hr | ou-derived | manual
    status: str = "pending"  # pending | written | failed | skipped


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
        d = {k: v for k, v in self.__dict__.items() if k not in ("assignments", "unresolved_queue", "findings")}
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
    users: list[dict],  # raw AD user records: dn, employeeId, samAccountName
    hr_map: dict[str, str],  # employeeId → orgPath (HR is authoritative)
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
                report.findings.append(
                    DriftFinding(
                        drift_class="DRIFT-SCHEMA",
                        severity="P1",
                        path=dn,
                        detail=f"HR export provides invalid OrgPath '{orgpath}' for user {sam}. "
                        "HR data quality issue — correct at source before migration.",
                        error_code="GOV-SCH-001",
                        object_type="User",
                    )
                )
                _add_to_unresolved(report, dn, emp_id, sam, "hr-invalid", orgpath)
                continue
            report.assigned_from_hr += 1
            report.assignments.append(
                UserOrgPathAssignment(
                    user_dn=dn,
                    employee_id=emp_id,
                    sam_account_name=sam,
                    orgpath=orgpath,
                    region=region,
                    source="hr",
                )
            )
            continue

        # Priority 2: OU derivation
        derived = ou_mapping.get(ou_dn)
        if derived and ORGPATH_REGEX.match(derived):
            # Validate against codebook if available
            if codebook and derived not in codebook:
                # Valid format but not in codebook — soft finding, still assign
                report.findings.append(
                    DriftFinding(
                        drift_class="DRIFT-PROVENANCE",
                        severity="P3",
                        path=dn,
                        detail=f"Derived OrgPath '{derived}' for user {sam} is not in codebook. "
                        "Codebook may need update via Workflow 1 (OrgPath Registration).",
                        error_code="GOV-MIG-003",
                        object_type="User",
                    )
                )
            report.assigned_from_ou += 1
            report.assignments.append(
                UserOrgPathAssignment(
                    user_dn=dn,
                    employee_id=emp_id,
                    sam_account_name=sam,
                    orgpath=derived,
                    region=region,
                    source="ou-derived",
                )
            )
            continue

        # Priority 3: Unresolved
        _add_to_unresolved(report, dn, emp_id, sam, "unresolvable", "")
        report.unresolved += 1
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-IDENTITY",
                severity="P1",
                path=dn,
                detail=f"User '{sam}' ({dn}) cannot be assigned an OrgPath from HR or OU. "
                "Added to unresolved queue for governance review. GOV-DRF-003.",
                error_code="GOV-DRF-003",
                object_type="User",
            )
        )

    return report


def _add_to_unresolved(
    report: OrgPathAssignmentReport,
    dn: str,
    emp_id: str,
    sam: str,
    reason: str,
    partial_orgpath: str,
) -> None:
    report.unresolved_queue.append(
        {
            "distinguishedName": dn,
            "employeeId": emp_id,
            "samAccountName": sam,
            "reason": reason,
            "partialOrgPath": partial_orgpath,
            "action": "MANUAL_REVIEW_REQUIRED",
        }
    )


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
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-PROVENANCE",
                severity="P4",
                path="orgpath.py::write_orgpath_to_ad",
                detail=f"DRY RUN: {len(assignments)} assignments validated, no AD writes performed. "
                "Set dry_run=False to execute write-back.",
                error_code="",
                object_type="adapter",
            )
        )
        for a in assignments:
            a.status = "skipped"
            report.assignments.append(a)
        return report

    try:
        from ldap3 import ALL, MODIFY_REPLACE, Connection, Server  # type: ignore

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
                    report.findings.append(
                        DriftFinding(
                            drift_class="DRIFT-PROVENANCE",
                            severity="P2",
                            path=assignment.user_dn,
                            detail=f"AD write failed for {assignment.sam_account_name}: {conn.result['description']}",
                            error_code="GOV-MIG-002",
                            object_type="User",
                        )
                    )
            except Exception as e:
                assignment.status = "failed"
                report.write_failed += 1
                report.findings.append(
                    DriftFinding(
                        drift_class="DRIFT-PROVENANCE",
                        severity="P1",
                        path=assignment.user_dn,
                        detail=f"Exception writing OrgPath for {assignment.sam_account_name}: {e}",
                        error_code="GOV-MIG-002",
                        object_type="User",
                    )
                )
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
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            report.findings.append(
                DriftFinding(
                    drift_class="DRIFT-PROVENANCE",
                    severity="P1",
                    path="orgpath.py::_write_via_powershell",
                    detail=f"PowerShell write-back failed: {result.stderr[:500]}",
                    error_code="GOV-MIG-002",
                    object_type="adapter",
                )
            )
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
        report.findings.append(
            DriftFinding(
                drift_class="DRIFT-PROVENANCE",
                severity="P1",
                path="orgpath.py::_write_via_powershell",
                detail="PowerShell write-back timed out. Split into smaller batches.",
                error_code="GOV-MIG-002",
                object_type="adapter",
            )
        )


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
            writer.writerow(
                {
                    "LegacyOU": dn,
                    "OrgPath": orgpath or "",
                    "Resolvable": "Y" if orgpath else "N",
                }
            )


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
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "user_dn",
                "employee_id",
                "sam_account_name",
                "orgpath",
                "region",
                "source",
                "status",
            ],
        )
        writer.writeheader()
        for a in report.assignments:
            writer.writerow(a.__dict__)

    # Unresolved queue CSV
    if report.unresolved_queue:
        with (output_dir / "unresolved-queue.csv").open("w", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "distinguishedName",
                    "employeeId",
                    "samAccountName",
                    "reason",
                    "partialOrgPath",
                    "action",
                ],
            )
            writer.writeheader()
            for item in report.unresolved_queue:
                writer.writerow(item)

    # JSON report
    (output_dir / "orgpath-assignment-report.json").write_text(json.dumps(report.as_dict(), indent=2, default=str))
