"""
pki/inventory.py
----------------
UIAO Modernization Adapter: PKI Certificate Inventory.

Interface-stub implementation of the canon PKI adapter contract at
``src/uiao/modernization/directory-migration/adapters/pki/pki-adapter-interface.md``
(DM_020). Surveys the certificate estate during AD → Entra ID migration
and emits a phase-tagged ``CertificateInventory`` artifact with drift
findings for certificates that cannot be bound to a verified
organizational position.

Why an interface stub
---------------------
The canon contract lists 9 required capabilities (full certificate
inventory, identity binding, expiry timeline, CA hierarchy mapping,
template inventory, smart-card/PIV/CAC inventory, CRL/OCSP migration,
auto-enrollment policy migration, side-by-side operation). Building
those against live ADCS / DigiCert / Entrust / Entra-CBA endpoints is
a multi-week effort.

This stub ships **the contract** today: typed dataclasses, an
extraction function that operates on synthetic records, and tests that
exercise the contract end-to-end without any external dependency.
A future PR adds the live-endpoint loaders behind the same contract.

Pattern parity with PR #395
---------------------------
The shape exactly mirrors
``active_directory/survey.py::extract_spn_inventory`` introduced in
PR #395:

  - Phase enum (``pre_migration | post_migration | unspecified``)
  - Discovery-method enum (here: AD-OBJECTS / OCSP / TEMPLATES)
  - Typed record + bundle dataclasses
  - Extraction function that takes records + OrgPath indices, returns
    the inventory + drift findings
  - ``DRIFT-IDENTITY`` finding emission when neither the certificate's
    subject principal nor its hosting computer resolves to an OrgPath

Drift class mapping
-------------------
Per ``docs/docs/16_DriftDetectionStandard.qmd``:

  - ``DRIFT-IDENTITY`` — cert subject can't be resolved to an OrgPath
  - ``DRIFT-PROVENANCE`` — cert exists but has no recorded issuance event
    (deferred; emitted by a future live-loader pass)
  - ``DRIFT-AUTHZ`` — cert authorization state diverges from COR-recorded
    AAL (deferred)
  - ``DRIFT-SCHEMA`` — cert serial format diverges from canonical schema
    (deferred; ADCS / Entra-CBA serials follow different conventions)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Canonical phase values — exact parity with spn_inventory.phase enum
# (active_directory/survey.py). Keeping the strings identical lets a
# future Evidence Bundle assembly cross-walk phase-tagged artifacts
# across modernization adapters without per-adapter translation.
PKI_PHASE_PRE_MIGRATION: str = "pre_migration"
PKI_PHASE_POST_MIGRATION: str = "post_migration"
PKI_PHASE_UNSPECIFIED: str = "unspecified"
_VALID_PKI_PHASES: tuple[str, ...] = (
    PKI_PHASE_PRE_MIGRATION,
    PKI_PHASE_POST_MIGRATION,
    PKI_PHASE_UNSPECIFIED,
)

# Discovery-method enum. ADCS exports certificate state through three
# distinct surfaces: AD objects (the published-CA cache; reliable for
# issuance metadata), OCSP responder queries (reliable for current
# validity), and template enumeration (the catalogue of certificate
# profiles).
PKI_DISCOVERY_AD_OBJECTS: str = "ADCS-AD-OBJECTS"
PKI_DISCOVERY_OCSP: str = "ADCS-OCSP"
PKI_DISCOVERY_TEMPLATES: str = "ADCS-TEMPLATES"
_VALID_PKI_DISCOVERY_METHODS: tuple[str, ...] = (
    PKI_DISCOVERY_AD_OBJECTS,
    PKI_DISCOVERY_OCSP,
    PKI_DISCOVERY_TEMPLATES,
)

# Days-until-expiry thresholds matching the canon contract:
# "Expiry timeline export — identify certs expiring within 90/180/365 days."
EXPIRY_WINDOW_CRITICAL_DAYS: int = 90
EXPIRY_WINDOW_HIGH_DAYS: int = 180
EXPIRY_WINDOW_MEDIUM_DAYS: int = 365


# ------------------------------------------------------------------
# DriftFinding — re-declared with the same shape as the AD survey
# adapter so findings can merge into a single substrate report
# without per-adapter translation.
# ------------------------------------------------------------------
@dataclass
class DriftFinding:
    """Drift finding shape compatible with active_directory.survey.DriftFinding."""

    drift_class: str  # DRIFT-IDENTITY | DRIFT-AUTHZ | DRIFT-PROVENANCE | DRIFT-SCHEMA | DRIFT-SEMANTIC
    severity: str  # P1 | P2 | P3 | P4
    path: str  # canonical path or object DN
    detail: str
    error_code: str = ""  # GOV-PKI-NNN
    object_type: str = ""  # Certificate | Template | CA


# ------------------------------------------------------------------
# Certificate inventory record + bundle dataclasses
# ------------------------------------------------------------------
@dataclass
class CertificateRecord:
    """One row of the certificate inventory.

    Matches the canon contract's "Full certificate inventory" + "Certificate-
    to-identity binding" + "Expiry timeline" + "Template inventory"
    capabilities (see pki-adapter-interface.md §Required Capabilities).
    """

    # Identity of the certificate
    serial_number: str
    subject_dn: str
    issuer_dn: str

    # Lifecycle
    not_before: str  # ISO-8601 UTC
    not_after: str  # ISO-8601 UTC; drives the expiry-window classification
    status: str  # issued | revoked | expired | pending

    # Template (ADCS-specific; empty for non-ADCS issuers)
    template_name: Optional[str] = None
    template_oid: Optional[str] = None

    # Identity binding — preferred attribution hooks (parity with SPN inventory)
    bound_principal_name: Optional[str] = None
    bound_principal_sam: Optional[str] = None
    bound_principal_dn: Optional[str] = None
    bound_hosting_computer: Optional[str] = None

    # Cross-domain attributes filled in by the extractor
    principal_orgpath: Optional[str] = None
    hosting_computer_orgpath: Optional[str] = None
    drift_finding_ref: Optional[str] = None

    # Smart-card / PIV / CAC flag — federal-critical per the canon contract
    is_piv_or_cac: bool = False

    # CRL / OCSP discoverability — populated by a future live-loader pass
    crl_endpoint: Optional[str] = None
    ocsp_endpoint: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "serial_number": self.serial_number,
            "subject_dn": self.subject_dn,
            "issuer_dn": self.issuer_dn,
            "not_before": self.not_before,
            "not_after": self.not_after,
            "status": self.status,
            "template_name": self.template_name,
            "template_oid": self.template_oid,
            "bound_principal_name": self.bound_principal_name,
            "bound_principal_sam": self.bound_principal_sam,
            "bound_principal_dn": self.bound_principal_dn,
            "bound_hosting_computer": self.bound_hosting_computer,
            "principal_orgpath": self.principal_orgpath,
            "hosting_computer_orgpath": self.hosting_computer_orgpath,
            "drift_finding_ref": self.drift_finding_ref,
            "is_piv_or_cac": self.is_piv_or_cac,
            "crl_endpoint": self.crl_endpoint,
            "ocsp_endpoint": self.ocsp_endpoint,
        }


@dataclass
class CertificateInventory:
    """PKI certificate inventory bundle artifact."""

    phase: str
    discovery_timestamp: str
    discovery_method: str = PKI_DISCOVERY_AD_OBJECTS
    discovery_scope: str = ""
    records: list[CertificateRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "discovery_timestamp": self.discovery_timestamp,
            "discovery_method": self.discovery_method,
            "discovery_scope": self.discovery_scope,
            "records": [r.to_dict() for r in self.records],
        }


# ------------------------------------------------------------------
# OrgPath resolution helpers (parity with survey.py SPN logic)
# ------------------------------------------------------------------
def _resolve_principal_orgpath(
    principal_name: Optional[str],
    sam_account_name: Optional[str],
    distinguished_name: Optional[str],
    principal_orgpath_index: Optional[dict[str, str]],
) -> Optional[str]:
    """Look up an OrgPath for the certificate's bound principal.

    Index keys may be any of: DN, sAMAccountName, principal common name.
    First hit wins. Returns None when no resolution is found (or no
    index supplied). DN wins over sAMAccountName.
    """
    if not principal_orgpath_index:
        return None
    for key in (distinguished_name, sam_account_name, principal_name):
        if key and key in principal_orgpath_index:
            return principal_orgpath_index[key]
    return None


def _resolve_hosting_computer_orgpath(
    hosting_computer: Optional[str],
    computer_orgpath_index: Optional[dict[str, str]],
) -> Optional[str]:
    """Fallback attribution via the hosting-computer hook."""
    if not computer_orgpath_index or not hosting_computer:
        return None
    if hosting_computer in computer_orgpath_index:
        return computer_orgpath_index[hosting_computer]
    short = hosting_computer.split(".", 1)[0]
    if short and short in computer_orgpath_index:
        return computer_orgpath_index[short]
    return None


# ------------------------------------------------------------------
# Extraction entry point
# ------------------------------------------------------------------
def extract_certificate_inventory(
    *,
    records: list[dict],
    phase: str,
    discovery_timestamp: str,
    discovery_method: str = PKI_DISCOVERY_AD_OBJECTS,
    discovery_scope: str = "",
    principal_orgpath_index: Optional[dict[str, str]] = None,
    computer_orgpath_index: Optional[dict[str, str]] = None,
) -> tuple[CertificateInventory, list[DriftFinding]]:
    """Build a CertificateInventory artifact from a list of synthetic records.

    Parameters
    ----------
    records : list[dict]
        Each record must carry at minimum: ``serial_number``, ``subject_dn``,
        ``issuer_dn``, ``not_before``, ``not_after``, ``status``. Optional
        keys: ``template_name``, ``template_oid``, ``bound_principal_name``,
        ``bound_principal_sam``, ``bound_principal_dn``,
        ``bound_hosting_computer``, ``is_piv_or_cac``, ``crl_endpoint``,
        ``ocsp_endpoint``.
    phase : str
        One of ``pre_migration | post_migration | unspecified``.
    discovery_method : str
        One of ``ADCS-AD-OBJECTS | ADCS-OCSP | ADCS-TEMPLATES``.
    principal_orgpath_index, computer_orgpath_index : dict[str, str] | None
        OrgPath lookup indices (parity with spn_inventory).

    Returns
    -------
    (CertificateInventory, list[DriftFinding])
        The inventory artifact and a list of DRIFT-IDENTITY findings for
        certificates whose subject + hosting-computer attribution both
        fail. Findings should be merged into the parent report's
        ``findings`` array.
    """
    if phase not in _VALID_PKI_PHASES:
        raise ValueError(f"phase must be one of {_VALID_PKI_PHASES}; got {phase!r}")
    if discovery_method not in _VALID_PKI_DISCOVERY_METHODS:
        raise ValueError(f"discovery_method must be one of {_VALID_PKI_DISCOVERY_METHODS}; got {discovery_method!r}")

    inventory = CertificateInventory(
        phase=phase,
        discovery_timestamp=discovery_timestamp,
        discovery_method=discovery_method,
        discovery_scope=discovery_scope,
    )
    findings: list[DriftFinding] = []
    unattributed_idx = 0

    for raw in records:
        # Required fields — explicit KeyError on miss is preferred over
        # silent omission so misshaped synthetic inputs surface early.
        serial = raw["serial_number"]
        subject_dn = raw["subject_dn"]
        issuer_dn = raw["issuer_dn"]
        not_before = raw["not_before"]
        not_after = raw["not_after"]
        status = raw["status"]

        principal_name = raw.get("bound_principal_name")
        principal_sam = raw.get("bound_principal_sam")
        principal_dn = raw.get("bound_principal_dn")
        hosting_computer = raw.get("bound_hosting_computer")

        principal_orgpath = _resolve_principal_orgpath(
            principal_name,
            principal_sam,
            principal_dn,
            principal_orgpath_index,
        )
        hosting_orgpath = _resolve_hosting_computer_orgpath(hosting_computer, computer_orgpath_index)

        drift_ref: Optional[str] = None
        if principal_orgpath is None and hosting_orgpath is None:
            unattributed_idx += 1
            error_code = f"GOV-PKI-{unattributed_idx:03d}"
            drift_ref = error_code
            findings.append(
                DriftFinding(
                    drift_class="DRIFT-IDENTITY",
                    severity="P2",
                    path=subject_dn or serial,
                    detail=(
                        f"Certificate (serial '{serial}', subject '{subject_dn}') "
                        "cannot be attributed to a verified OrgPath. Neither the "
                        "bound principal nor the hosting computer resolves. "
                        "Owner reassignment required before CA migration."
                    ),
                    error_code=error_code,
                    object_type="Certificate",
                )
            )

        inventory.records.append(
            CertificateRecord(
                serial_number=serial,
                subject_dn=subject_dn,
                issuer_dn=issuer_dn,
                not_before=not_before,
                not_after=not_after,
                status=status,
                template_name=raw.get("template_name"),
                template_oid=raw.get("template_oid"),
                bound_principal_name=principal_name,
                bound_principal_sam=principal_sam,
                bound_principal_dn=principal_dn,
                bound_hosting_computer=hosting_computer,
                principal_orgpath=principal_orgpath,
                hosting_computer_orgpath=hosting_orgpath,
                drift_finding_ref=drift_ref,
                is_piv_or_cac=bool(raw.get("is_piv_or_cac", False)),
                crl_endpoint=raw.get("crl_endpoint"),
                ocsp_endpoint=raw.get("ocsp_endpoint"),
            )
        )

    return inventory, findings
