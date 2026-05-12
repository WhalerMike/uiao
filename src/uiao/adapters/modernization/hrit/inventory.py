"""
hrit/inventory.py
-----------------
UIAO Modernization Adapter: HRIT Record Inventory.

Interface-stub implementation of the federal HRIT inbound-provisioning
survey shape. Companion to:

  - ``active_directory.survey.extract_spn_inventory`` (PR #395) — SPN
    inventory for AD service accounts
  - ``pki.inventory.extract_certificate_inventory`` (PR #429) —
    certificate inventory for ADCS / DigiCert / Entrust / Entra-CBA

The HRIT shape differs from those two in one important way: HR records
are the **upstream authoritative source** that feeds Entra ID, not a
directory state being migrated. The substrate's role is to govern the
inbound-provisioning pipeline — surveying records emitted by the HR
system of record, attributing each to a canonical OrgPath, and emitting
drift findings when an HR record cannot be bound to a verified
organizational position.

Pattern parity with PR #395 + PR #429
-------------------------------------
Phase enum strings are identical so a future Evidence Bundle assembly
can cross-walk phase-tagged artifacts across modernization adapters
without per-adapter translation. The discovery-method enum names the
federal HR sources catalogued in Spec2-D6.1 §2 (NFC EmpowHR, Treasury
HR Connect, DCPDS, DOI IBC, USA Staffing).

Canonical HR record shape
-------------------------
Input records conform to the Spec2-D1.1 canonical HR schema. Required
fields per that schema:

    employeeId, firstName, lastName, department,
    hireDate, workerType, locationCode, country,
    employmentStatus, extracted_at

Optional fields used for OrgPath resolution:

    division, organizationCode, costCenter, jobTitle, managerEmployeeId

Drift class mapping
-------------------
Per ``docs/docs/16_DriftDetectionStandard.qmd`` and Spec2-D5.5
Provisioning Drift Detection Rules:

  - ``DRIFT-IDENTITY`` — HR record cannot be resolved to an OrgPath
    via department / division / organizationCode lookup
  - ``DRIFT-PROVENANCE`` — record emitted without complete
    ``extracted_at`` + ``adapter_metadata`` provenance (deferred;
    requires a live-loader pass that verifies metadata completeness)
  - ``DRIFT-AUTHZ`` — workerType / employmentStatus mismatch versus
    COR-recorded principal state (deferred; requires correlation
    against a post-provisioning Entra state)
  - ``DRIFT-SCHEMA`` — record violates the Spec2-D1.1 schema
    (deferred; emitted by an explicit schema-validation pass)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Canonical phase values — exact parity with the SPN and PKI inventories.
HRIT_PHASE_PRE_MIGRATION: str = "pre_migration"
HRIT_PHASE_POST_MIGRATION: str = "post_migration"
HRIT_PHASE_UNSPECIFIED: str = "unspecified"
_VALID_HRIT_PHASES: tuple[str, ...] = (
    HRIT_PHASE_PRE_MIGRATION,
    HRIT_PHASE_POST_MIGRATION,
    HRIT_PHASE_UNSPECIFIED,
)

# Discovery-method enum naming the federal HR systems catalogued in
# Spec2-D6.1 §2. Pattern A native HR adapters (HR systems of record):
HRIT_DISCOVERY_NFC_EMPOWHR: str = "NFC-EMPOWHR"
HRIT_DISCOVERY_TREASURY_HR_CONNECT: str = "TREASURY-HR-CONNECT"
HRIT_DISCOVERY_DCPDS: str = "DCPDS"
HRIT_DISCOVERY_DOI_IBC: str = "DOI-IBC"
# Pattern B OPM lifecycle service (Joiner trigger source):
HRIT_DISCOVERY_USA_STAFFING: str = "USA-STAFFING"
_VALID_HRIT_DISCOVERY_METHODS: tuple[str, ...] = (
    HRIT_DISCOVERY_NFC_EMPOWHR,
    HRIT_DISCOVERY_TREASURY_HR_CONNECT,
    HRIT_DISCOVERY_DCPDS,
    HRIT_DISCOVERY_DOI_IBC,
    HRIT_DISCOVERY_USA_STAFFING,
)


# ------------------------------------------------------------------
# DriftFinding — same shape as active_directory.survey.DriftFinding
# so findings merge into a single substrate report.
# ------------------------------------------------------------------
@dataclass
class DriftFinding:
    """Drift finding shape compatible with active_directory.survey.DriftFinding."""

    drift_class: str  # DRIFT-IDENTITY | DRIFT-AUTHZ | DRIFT-PROVENANCE | DRIFT-SCHEMA | DRIFT-SEMANTIC
    severity: str  # P1 | P2 | P3 | P4
    path: str  # canonical employeeId or correlation anchor
    detail: str
    error_code: str = ""  # GOV-HRIT-NNN
    object_type: str = ""  # HRRecord | HRSystem


# ------------------------------------------------------------------
# HR record + inventory dataclasses
# ------------------------------------------------------------------
@dataclass
class HRRecord:
    """One row of the HRIT inventory.

    Matches the load-bearing subset of the Spec2-D1.1 canonical HR
    schema — the fields the substrate's OrgPath resolution and
    DRIFT-IDENTITY emission depend on. The full canonical-schema
    payload is not duplicated here; deployments that need it pass it
    via ``adapter_metadata``.
    """

    # Spec2-D1.1 required fields
    employee_id: str  # immutable correlation anchor (Spec2-D1.1 §3.1)
    first_name: str
    last_name: str
    department: str
    hire_date: str  # ISO-8601 date
    worker_type: (
        str  # FullTimeEmployee | PartTimeEmployee | Contractor | Intern | Vendor | Volunteer | ExternalCollaborator
    )
    location_code: str
    country: str  # ISO-3166 alpha-2
    employment_status: str  # Active | OnLeave | PreHire | Terminated | Rescinded
    extracted_at: str  # ISO-8601 UTC

    # Spec2-D1.1 optional fields used for OrgPath resolution
    division: Optional[str] = None
    organization_code: Optional[str] = None
    cost_center: Optional[str] = None
    job_title: Optional[str] = None
    manager_employee_id: Optional[str] = None
    termination_date: Optional[str] = None

    # Cross-domain attributes filled in by the extractor
    resolved_orgpath: Optional[str] = None
    drift_finding_ref: Optional[str] = None

    # Per-source provenance — adapter_metadata is the canonical bag for
    # source-specific keys per Spec2-D1.1
    adapter_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "employee_id": self.employee_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "department": self.department,
            "hire_date": self.hire_date,
            "worker_type": self.worker_type,
            "location_code": self.location_code,
            "country": self.country,
            "employment_status": self.employment_status,
            "extracted_at": self.extracted_at,
            "division": self.division,
            "organization_code": self.organization_code,
            "cost_center": self.cost_center,
            "job_title": self.job_title,
            "manager_employee_id": self.manager_employee_id,
            "termination_date": self.termination_date,
            "resolved_orgpath": self.resolved_orgpath,
            "drift_finding_ref": self.drift_finding_ref,
            "adapter_metadata": dict(self.adapter_metadata),
        }


@dataclass
class HRRecordInventory:
    """HRIT record inventory bundle artifact."""

    phase: str
    discovery_timestamp: str
    discovery_method: str = HRIT_DISCOVERY_NFC_EMPOWHR
    discovery_scope: str = ""
    records: list[HRRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "discovery_timestamp": self.discovery_timestamp,
            "discovery_method": self.discovery_method,
            "discovery_scope": self.discovery_scope,
            "records": [r.to_dict() for r in self.records],
        }


# ------------------------------------------------------------------
# OrgPath resolution helper
# ------------------------------------------------------------------
def _resolve_record_orgpath(
    department: str,
    division: Optional[str],
    organization_code: Optional[str],
    cost_center: Optional[str],
    orgpath_index: Optional[dict[str, str]],
) -> Optional[str]:
    """Look up an OrgPath for an HR record using D1.1 organizational fields.

    Index keys may be any of: organization_code (Spec2-D1.1 preferred —
    explicit top-level org tag), division, department, cost_center.
    First hit wins. Returns None when no resolution found.

    Resolution-order rationale (per Spec2-D1.3 / D3.5):

      1. organization_code — explicit canonical anchor when the HR
         system populates it (NFC EmpowHR and Treasury HR Connect do;
         DCPDS uses a different code structure)
      2. division — second-tier organizational unit
      3. department — first-tier required field; fallback when neither
         organization_code nor division resolves
      4. cost_center — last resort; some agencies key their OrgPath
         codebook by cost center for finance-driven OrgTree models
    """
    if not orgpath_index:
        return None
    for key in (organization_code, division, department, cost_center):
        if key and key in orgpath_index:
            return orgpath_index[key]
    return None


# ------------------------------------------------------------------
# Extraction entry point
# ------------------------------------------------------------------
def extract_hrit_record_inventory(
    *,
    records: list[dict],
    phase: str,
    discovery_timestamp: str,
    discovery_method: str = HRIT_DISCOVERY_NFC_EMPOWHR,
    discovery_scope: str = "",
    orgpath_index: Optional[dict[str, str]] = None,
) -> tuple[HRRecordInventory, list[DriftFinding]]:
    """Build an HRRecordInventory artifact from a list of canonical HR records.

    Parameters
    ----------
    records : list[dict]
        Each record must carry the Spec2-D1.1 required fields:
        ``employee_id``, ``first_name``, ``last_name``, ``department``,
        ``hire_date``, ``worker_type``, ``location_code``, ``country``,
        ``employment_status``, ``extracted_at``. Optional fields used
        for OrgPath resolution: ``division``, ``organization_code``,
        ``cost_center``, ``job_title``, ``manager_employee_id``,
        ``termination_date``, ``adapter_metadata``.
    phase : str
        One of ``pre_migration | post_migration | unspecified``.
    discovery_method : str
        One of ``NFC-EMPOWHR | TREASURY-HR-CONNECT | DCPDS | DOI-IBC |
        USA-STAFFING``.
    orgpath_index : dict[str, str] | None
        OrgPath lookup index keyed by organization_code / division /
        department / cost_center (first hit wins per Spec2-D1.3).

    Returns
    -------
    (HRRecordInventory, list[DriftFinding])
        The inventory artifact and a list of DRIFT-IDENTITY findings
        for records whose OrgPath resolution fails. Findings should be
        merged into the parent report's ``findings`` array.
    """
    if phase not in _VALID_HRIT_PHASES:
        raise ValueError(f"phase must be one of {_VALID_HRIT_PHASES}; got {phase!r}")
    if discovery_method not in _VALID_HRIT_DISCOVERY_METHODS:
        raise ValueError(f"discovery_method must be one of {_VALID_HRIT_DISCOVERY_METHODS}; got {discovery_method!r}")

    inventory = HRRecordInventory(
        phase=phase,
        discovery_timestamp=discovery_timestamp,
        discovery_method=discovery_method,
        discovery_scope=discovery_scope,
    )
    findings: list[DriftFinding] = []
    unattributed_idx = 0

    for raw in records:
        # Required fields — explicit KeyError on miss surfaces misshaped
        # synthetic inputs early (same pattern as PR #395, PR #429).
        employee_id = raw["employee_id"]
        first_name = raw["first_name"]
        last_name = raw["last_name"]
        department = raw["department"]
        hire_date = raw["hire_date"]
        worker_type = raw["worker_type"]
        location_code = raw["location_code"]
        country = raw["country"]
        employment_status = raw["employment_status"]
        extracted_at = raw["extracted_at"]

        division = raw.get("division")
        organization_code = raw.get("organization_code")
        cost_center = raw.get("cost_center")

        resolved_orgpath = _resolve_record_orgpath(
            department=department,
            division=division,
            organization_code=organization_code,
            cost_center=cost_center,
            orgpath_index=orgpath_index,
        )

        drift_ref: Optional[str] = None
        if resolved_orgpath is None:
            unattributed_idx += 1
            error_code = f"GOV-HRIT-{unattributed_idx:03d}"
            drift_ref = error_code
            findings.append(
                DriftFinding(
                    drift_class="DRIFT-IDENTITY",
                    severity="P2",
                    path=employee_id,
                    detail=(
                        f"HR record (employee_id '{employee_id}', "
                        f"department '{department}') cannot be resolved "
                        "to a verified OrgPath via organization_code, "
                        "division, department, or cost_center lookup. "
                        "Provisioning into Entra ID requires explicit "
                        "OrgTree codebook assignment before the record "
                        "passes through Spec2-D3.2 middleware."
                    ),
                    error_code=error_code,
                    object_type="HRRecord",
                )
            )

        inventory.records.append(
            HRRecord(
                employee_id=employee_id,
                first_name=first_name,
                last_name=last_name,
                department=department,
                hire_date=hire_date,
                worker_type=worker_type,
                location_code=location_code,
                country=country,
                employment_status=employment_status,
                extracted_at=extracted_at,
                division=division,
                organization_code=organization_code,
                cost_center=cost_center,
                job_title=raw.get("job_title"),
                manager_employee_id=raw.get("manager_employee_id"),
                termination_date=raw.get("termination_date"),
                resolved_orgpath=resolved_orgpath,
                drift_finding_ref=drift_ref,
                adapter_metadata=dict(raw.get("adapter_metadata") or {}),
            )
        )

    return inventory, findings
