"""
src/uiao/governance/drift.py
-----------------------------
UIAO Drift Engine — canonical drift taxonomy classifiers.

Implements:
  - Generic DriftState builder (existing, unchanged)
  - DRIFT-AUTHZ classifier  (ADR-012 DT-04, new)
  - DRIFT-IDENTITY classifier (ADR-012 DT-05, new)

Drift taxonomy reference: src/uiao/canon/adr/adr-012-canonical-drift-taxonomy.md
DRIFT-BOUNDARY extension:  src/uiao/canon/adr/adr-033-gcc-boundary-drift-class.md

Classification axes
-------------------
DriftState.classification  — risk signal: benign | risky | unauthorized
                             Drives automation (unchanged existing behaviour)

DriftState.drift_class     — taxonomy type: DRIFT-SCHEMA | DRIFT-SEMANTIC |
                             DRIFT-PROVENANCE | DRIFT-AUTHZ | DRIFT-IDENTITY |
                             DRIFT-BOUNDARY
                             Drives reporting, aggregation, and finding routing

The two axes are independent. A finding may be "unauthorized" (risk) and
"DRIFT-AUTHZ" (type) simultaneously.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from uiao.ir.models.core import DriftState, ProvenanceRecord, canonical_hash

# ---------------------------------------------------------------------------
# Canonical drift class strings (mirrors DriftClassType in core.py)
# Imported here as plain strings to avoid circular imports if core.py is
# patched later.
# ---------------------------------------------------------------------------
DRIFT_SCHEMA    = "DRIFT-SCHEMA"
DRIFT_SEMANTIC  = "DRIFT-SEMANTIC"
DRIFT_PROVENANCE = "DRIFT-PROVENANCE"
DRIFT_AUTHZ     = "DRIFT-AUTHZ"
DRIFT_IDENTITY  = "DRIFT-IDENTITY"
DRIFT_BOUNDARY  = "DRIFT-BOUNDARY"


# ---------------------------------------------------------------------------
# Internal helpers (unchanged)
# ---------------------------------------------------------------------------

def _classify_drift(
    expected_hash: str,
    actual_hash: str,
    delta: Dict[str, List[str]],
) -> str:
    if expected_hash == actual_hash:
        return "benign"
    changed_fields = (
        set(delta.get("changed", []))
        | set(delta.get("added", []))
        | set(delta.get("removed", []))
    )
    if len(changed_fields) <= 3:
        return "risky"
    return "unauthorized"


def _dict_delta(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
) -> Dict[str, List[str]]:
    expected_keys = set(expected.keys())
    actual_keys = set(actual.keys())
    added = sorted(actual_keys - expected_keys)
    removed = sorted(expected_keys - actual_keys)
    changed: List[str] = []
    for key in sorted(expected_keys & actual_keys):
        if expected[key] != actual[key]:
            changed.append(key)
    return {"added": added, "removed": removed, "changed": changed}


# ---------------------------------------------------------------------------
# Generic DriftState builder (unchanged signature, adds drift_class param)
# ---------------------------------------------------------------------------

def build_drift_state(
    *,
    resource_id: str,
    policy_ref: str,
    expected_state: Dict[str, Any],
    actual_state: Dict[str, Any],
    provenance: ProvenanceRecord,
    drift_id: Optional[str] = None,
    drift_class: Optional[str] = None,
) -> DriftState:
    """
    Deterministically compute a DriftState from expected vs actual state.

    drift_class is optional — callers that do not supply it get None,
    which is valid and backward-compatible. Prefer the typed classifiers
    below (classify_authz_drift, classify_identity_drift) which set
    drift_class automatically.
    """
    expected_hash = canonical_hash(expected_state)
    actual_hash = canonical_hash(actual_state)
    delta = _dict_delta(expected_state, actual_state)
    classification = _classify_drift(expected_hash, actual_hash, delta)
    drift_state_id = drift_id or f"drift:{resource_id}:{policy_ref}"
    return DriftState(
        id=drift_state_id,
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        drift_detected=expected_hash != actual_hash,
        classification=classification,
        delta=delta,
        provenance=provenance,
        drift_class=drift_class,
    )


# ---------------------------------------------------------------------------
# DRIFT-AUTHZ Classifier
# ADR-012 DT-04: Authorization drift
#
# Detects deviations in:
#   - Role assignments outside the canonical delegation matrix
#   - Privilege scope broader than authorized
#   - Unconstrained Kerberos delegation on service accounts
#   - Administrative unit scope violations
#   - RBAC assignments with no AU scope (tenant-wide unscoped admins)
#   - Service principal permissions exceeding declared API scope
# ---------------------------------------------------------------------------

# Fields whose change always constitutes authorization drift regardless of count
_AUTHZ_SENTINEL_FIELDS = frozenset({
    # AD / on-prem
    "kerberos_delegation",          # any change to unconstrained → always DRIFT-AUTHZ
    "trusted_for_delegation",
    "allowed_to_delegate_to",
    "admin_count",                  # AD adminCount attribute — shadow group membership
    # Entra / cloud
    "role_assignments",
    "scope",                        # role assignment scope change
    "privileged_role",
    "pim_assignment",
    "au_scope",                     # Administrative Unit scope
    "directory_role",
    # Service principal
    "app_roles_assigned",
    "oauth2_permission_grants",
    "api_permissions",
    "resource_access",
    # Group membership affecting auth
    "is_privileged_group_member",
    "group_membership_changes",
})

# Values that indicate privilege escalation when present in actual_state
_AUTHZ_ESCALATION_PATTERNS = {
    "kerberos_delegation": {"unconstrained", "true", True},
    "trusted_for_delegation": {True, "true"},
    "admin_count": lambda v: isinstance(v, int) and v > 0,
}


def classify_authz_drift(
    *,
    resource_id: str,
    policy_ref: str,
    expected_state: Dict[str, Any],
    actual_state: Dict[str, Any],
    provenance: ProvenanceRecord,
    drift_id: Optional[str] = None,
) -> Optional[DriftState]:
    """
    Classify authorization drift (DRIFT-AUTHZ).

    Returns a DriftState with drift_class=DRIFT-AUTHZ if authorization
    drift is detected, or None if no authorization drift is present.

    Authorization drift is detected when:
      1. Any sentinel authorization field has changed, OR
      2. A privilege escalation pattern is present in actual_state, OR
      3. actual_state has more role assignments than expected_state

    This is additive over the generic build_drift_state — it narrows
    classification to DRIFT-AUTHZ when the conditions are met.
    """
    delta = _dict_delta(expected_state, actual_state)
    all_changed = (
        set(delta.get("changed", []))
        | set(delta.get("added", []))
        | set(delta.get("removed", []))
    )

    # Check 1: sentinel field changed
    sentinel_hit = bool(all_changed & _AUTHZ_SENTINEL_FIELDS)

    # Check 2: escalation pattern in actual state
    escalation_hit = False
    for field, pattern in _AUTHZ_ESCALATION_PATTERNS.items():
        if field in actual_state:
            val = actual_state[field]
            if callable(pattern):
                if pattern(val):
                    escalation_hit = True
                    break
            elif val in pattern:
                escalation_hit = True
                break

    # Check 3: role count grew
    exp_roles = expected_state.get("role_assignments", [])
    act_roles = actual_state.get("role_assignments", [])
    role_growth = (
        isinstance(act_roles, list)
        and isinstance(exp_roles, list)
        and len(act_roles) > len(exp_roles)
    )

    if not (sentinel_hit or escalation_hit or role_growth):
        return None  # No authorization drift

    # Build the DriftState with DRIFT-AUTHZ classification
    expected_hash = canonical_hash(expected_state)
    actual_hash = canonical_hash(actual_state)
    risk = _classify_drift(expected_hash, actual_hash, delta)

    # Escalation patterns always elevate to "unauthorized"
    if escalation_hit:
        risk = "unauthorized"

    drift_state_id = drift_id or f"drift-authz:{resource_id}:{policy_ref}"
    return DriftState(
        id=drift_state_id,
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        drift_detected=True,
        classification=risk,
        delta=delta,
        provenance=provenance,
        drift_class=DRIFT_AUTHZ,
    )


# ---------------------------------------------------------------------------
# DRIFT-IDENTITY Classifier
# ADR-012 DT-05: Identity drift
#
# Detects deviations in identity object state:
#   - OrgPath missing, malformed, or not in codebook
#   - Identity exists in one plane but not another (AD vs Entra vs Arc)
#   - Attribute inconsistency across planes (department vs OrgPath Level 1)
#   - Lifecycle state inconsistency (ACTIVE + accountEnabled=False)
#   - Employee ID missing or duplicate
#   - Manager reference broken (null or points to disabled user)
#   - Device OrgPath missing (no ARM tag on Arc machine)
#   - Entra device without OrgPath extensionAttribute1
# ---------------------------------------------------------------------------

import re as _re

_ORGPATH_REGEX = _re.compile(r"^ORG(-[A-Z]{2,6}){0,4}$")

# Identity fields whose absence or change constitutes identity drift
_IDENTITY_REQUIRED_FIELDS = frozenset({
    "orgpath",
    "org_path",
    "extension_attribute_1",    # Entra extensionAttribute1
    "employee_id",
    "lifecycle_state",
    "account_enabled",
})

_IDENTITY_SENTINEL_FIELDS = frozenset({
    "orgpath",
    "org_path",
    "extension_attribute_1",
    "employee_id",
    "upn",
    "user_principal_name",
    "lifecycle_state",
    "manager",
    "sam_account_name",
    "entra_device_id",          # Entra device object ID
    "arc_machine_id",           # Azure Arc resource ID
    "disposition",              # Computer disposition from survey
})

# Lifecycle state consistency rules
_LIFECYCLE_ACCOUNT_RULES = {
    "ACTIVE": True,             # ACTIVE → accountEnabled must be True
    "SUSPENDED": False,         # SUSPENDED → accountEnabled must be False
    "OFFBOARDING": False,
    "ONBOARDING": True,
}


def classify_identity_drift(
    *,
    resource_id: str,
    policy_ref: str,
    expected_state: Dict[str, Any],
    actual_state: Dict[str, Any],
    provenance: ProvenanceRecord,
    drift_id: Optional[str] = None,
    orgpath_codebook: Optional[set] = None,
) -> Optional[DriftState]:
    """
    Classify identity drift (DRIFT-IDENTITY).

    Returns a DriftState with drift_class=DRIFT-IDENTITY if identity
    drift is detected, or None if no identity drift is present.

    Identity drift is detected when:
      1. Any sentinel identity field has changed, OR
      2. OrgPath is missing, malformed, or not in codebook, OR
      3. Lifecycle state is inconsistent with accountEnabled, OR
      4. Required identity fields are absent from actual_state

    orgpath_codebook: optional set of valid OrgPath codes (Appendix A).
    If provided, OrgPaths not in the codebook are flagged as drift.
    If omitted, only format validation is applied.
    """
    delta = _dict_delta(expected_state, actual_state)
    all_changed = (
        set(delta.get("changed", []))
        | set(delta.get("added", []))
        | set(delta.get("removed", []))
    )

    reasons: List[str] = []

    # Check 1: sentinel field changed
    if all_changed & _IDENTITY_SENTINEL_FIELDS:
        reasons.append(f"sentinel fields changed: {sorted(all_changed & _IDENTITY_SENTINEL_FIELDS)}")

    # Check 2: OrgPath validation
    orgpath_value = (
        actual_state.get("orgpath")
        or actual_state.get("org_path")
        or actual_state.get("extension_attribute_1")
    )
    if orgpath_value is None:
        reasons.append("OrgPath missing from identity object")
    elif not _ORGPATH_REGEX.match(str(orgpath_value)):
        reasons.append(f"OrgPath '{orgpath_value}' fails format validation ^ORG(-[A-Z]{{2,6}}){{0,4}}$")
    elif orgpath_codebook is not None and str(orgpath_value) not in orgpath_codebook:
        reasons.append(f"OrgPath '{orgpath_value}' not in canonical codebook")

    # Check 3: lifecycle consistency
    lifecycle = actual_state.get("lifecycle_state") or actual_state.get("extensionAttribute3")
    account_enabled = actual_state.get("account_enabled") or actual_state.get("accountEnabled")
    if lifecycle and account_enabled is not None:
        expected_enabled = _LIFECYCLE_ACCOUNT_RULES.get(str(lifecycle).upper())
        if expected_enabled is not None and bool(account_enabled) != expected_enabled:
            reasons.append(
                f"Lifecycle '{lifecycle}' inconsistent with accountEnabled={account_enabled}"
            )

    # Check 4: required fields absent in actual_state
    # Only flag fields that ARE present in expected but absent in actual
    for field in _IDENTITY_REQUIRED_FIELDS:
        if field in expected_state and field not in actual_state:
            reasons.append(f"Required field '{field}' absent from actual state")

    if not reasons:
        return None  # No identity drift

    expected_hash = canonical_hash(expected_state)
    actual_hash = canonical_hash(actual_state)
    risk = _classify_drift(expected_hash, actual_hash, delta)

    # Missing OrgPath is always "unauthorized" — it means governance
    # cannot determine what policies apply to this identity
    if any("OrgPath missing" in r or "OrgPath" in r for r in reasons):
        risk = "unauthorized"

    drift_state_id = drift_id or f"drift-identity:{resource_id}:{policy_ref}"
    return DriftState(
        id=drift_state_id,
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        drift_detected=True,
        classification=risk,
        delta={**delta, "identity_reasons": reasons},  # type: ignore[arg-type]
        provenance=provenance,
        drift_class=DRIFT_IDENTITY,
    )


# ---------------------------------------------------------------------------
# Composite classifier — runs all taxonomy classifiers in priority order
# ---------------------------------------------------------------------------

def classify_drift(
    *,
    resource_id: str,
    policy_ref: str,
    expected_state: Dict[str, Any],
    actual_state: Dict[str, Any],
    provenance: ProvenanceRecord,
    drift_id: Optional[str] = None,
    orgpath_codebook: Optional[set] = None,
) -> DriftState:
    """
    Run all drift classifiers in priority order and return the first match.

    Priority order (highest to lowest specificity):
      1. DRIFT-AUTHZ   — authorization escalation is highest priority
      2. DRIFT-IDENTITY — identity plane gaps block all policy decisions
      3. Generic (DRIFT-SCHEMA / risky / unauthorized) — fallback

    If no specific classifier fires, falls back to the generic build_drift_state
    with drift_class=None (unclassified).

    This is the preferred entry point for adapter code. Use the specific
    classifiers directly only when you know the type in advance.
    """
    # DRIFT-AUTHZ first
    authz = classify_authz_drift(
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_state=expected_state,
        actual_state=actual_state,
        provenance=provenance,
        drift_id=drift_id,
    )
    if authz is not None:
        return authz

    # DRIFT-IDENTITY second
    identity = classify_identity_drift(
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_state=expected_state,
        actual_state=actual_state,
        provenance=provenance,
        drift_id=drift_id,
        orgpath_codebook=orgpath_codebook,
    )
    if identity is not None:
        return identity

    # Fallback — generic classification, drift_class unset
    return build_drift_state(
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_state=expected_state,
        actual_state=actual_state,
        provenance=provenance,
        drift_id=drift_id,
    )
