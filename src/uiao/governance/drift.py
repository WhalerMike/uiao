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

from typing import Any, Dict, List, Literal, Optional, Set, Union

from uiao.ir.models.core import DriftState, ProvenanceRecord, canonical_hash

# Typing alias for the codebook parameter. Callers may pass either:
#   - a flat ``set[str]`` of active OrgPath codes (legacy contract), or
#   - a ``uiao.modernization.orgtree.codebook.Codebook`` instance, which
#     additionally lets the classifier emit Phantom Drift against deprecated
#     codes (MOD_A §Drift). Duck-typed to avoid a circular import.
OrgPathCodebook = Union[Set[str], "Any"]

# ---------------------------------------------------------------------------
# Canonical drift class strings (mirrors DriftClassType in core.py)
# Imported here as plain strings to avoid circular imports if core.py is
# patched later.
# ---------------------------------------------------------------------------
DriftClassLiteral = Literal[
    "DRIFT-SCHEMA",
    "DRIFT-SEMANTIC",
    "DRIFT-PROVENANCE",
    "DRIFT-AUTHZ",
    "DRIFT-IDENTITY",
    "DRIFT-BOUNDARY",
]
DRIFT_SCHEMA: DriftClassLiteral = "DRIFT-SCHEMA"
DRIFT_SEMANTIC: DriftClassLiteral = "DRIFT-SEMANTIC"
DRIFT_PROVENANCE: DriftClassLiteral = "DRIFT-PROVENANCE"
DRIFT_AUTHZ: DriftClassLiteral = "DRIFT-AUTHZ"
DRIFT_IDENTITY: DriftClassLiteral = "DRIFT-IDENTITY"
DRIFT_BOUNDARY: DriftClassLiteral = "DRIFT-BOUNDARY"


# ---------------------------------------------------------------------------
# Internal helpers (unchanged)
# ---------------------------------------------------------------------------


def _classify_drift(
    expected_hash: str,
    actual_hash: str,
    delta: Dict[str, List[str]],
) -> Literal["benign", "risky", "unauthorized"]:
    if expected_hash == actual_hash:
        return "benign"
    changed_fields = set(delta.get("changed", [])) | set(delta.get("added", [])) | set(delta.get("removed", []))
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
    drift_class: Optional[DriftClassLiteral] = None,
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
_AUTHZ_SENTINEL_FIELDS = frozenset(
    {
        # AD / on-prem
        "kerberos_delegation",  # any change to unconstrained → always DRIFT-AUTHZ
        "trusted_for_delegation",
        "allowed_to_delegate_to",
        "admin_count",  # AD adminCount attribute — shadow group membership
        # Entra / cloud
        "role_assignments",
        "scope",  # role assignment scope change
        "privileged_role",
        "pim_assignment",
        "au_scope",  # Administrative Unit scope
        "directory_role",
        # Service principal
        "app_roles_assigned",
        "oauth2_permission_grants",
        "api_permissions",
        "resource_access",
        # Group membership affecting auth
        "is_privileged_group_member",
        "group_membership_changes",
    }
)

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
    all_changed = set(delta.get("changed", [])) | set(delta.get("added", [])) | set(delta.get("removed", []))

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
            elif val in pattern:  # type: ignore[operator]  # pattern is Set when reached (callable branch handled above)
                escalation_hit = True
                break

    # Check 3: role count grew
    exp_roles = expected_state.get("role_assignments", [])
    act_roles = actual_state.get("role_assignments", [])
    role_growth = isinstance(act_roles, list) and isinstance(exp_roles, list) and len(act_roles) > len(exp_roles)

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
_IDENTITY_REQUIRED_FIELDS = frozenset(
    {
        "orgpath",
        "org_path",
        "extension_attribute_1",  # Entra extensionAttribute1
        "employee_id",
        "lifecycle_state",
        "account_enabled",
    }
)

_IDENTITY_SENTINEL_FIELDS = frozenset(
    {
        "orgpath",
        "org_path",
        "extension_attribute_1",
        "employee_id",
        "upn",
        "user_principal_name",
        "lifecycle_state",
        "manager",
        "sam_account_name",
        "entra_device_id",  # Entra device object ID
        "arc_machine_id",  # Azure Arc resource ID
        "disposition",  # Computer disposition from survey
    }
)

# Lifecycle state consistency rules
_LIFECYCLE_ACCOUNT_RULES = {
    "ACTIVE": True,  # ACTIVE → accountEnabled must be True
    "SUSPENDED": False,  # SUSPENDED → accountEnabled must be False
    "OFFBOARDING": False,
    "ONBOARDING": True,
}


def _resolve_codebook(
    codebook: Optional[OrgPathCodebook],
) -> tuple[Optional[set], Optional[set]]:
    """Return ``(active_codes, deprecated_codes)`` for a codebook argument.

    Accepts either a bare ``set[str]`` of active codes (legacy contract used
    by ``test_drift_classifiers``) or any object exposing ``.codes`` and
    ``.deprecated_codes`` — e.g. a
    :class:`uiao.modernization.orgtree.codebook.Codebook`. Duck-typed to
    avoid a circular import.
    """
    if codebook is None:
        return None, None
    if isinstance(codebook, set):
        return codebook, None
    active = getattr(codebook, "codes", None)
    deprecated = getattr(codebook, "deprecated_codes", None)
    if active is None:
        # Fall back to iterating — supports any Iterable[str].
        return set(codebook), None
    return set(active), set(deprecated) if deprecated else None


def classify_identity_drift(
    *,
    resource_id: str,
    policy_ref: str,
    expected_state: Dict[str, Any],
    actual_state: Dict[str, Any],
    provenance: ProvenanceRecord,
    drift_id: Optional[str] = None,
    orgpath_codebook: Optional[OrgPathCodebook] = None,
) -> Optional[DriftState]:
    """
    Classify identity drift (DRIFT-IDENTITY).

    Returns a DriftState with drift_class=DRIFT-IDENTITY if identity
    drift is detected, or None if no identity drift is present.

    Identity drift is detected when:
      1. Any sentinel identity field has changed, OR
      2. OrgPath is missing, malformed, not in codebook, or deprecated, OR
      3. Lifecycle state is inconsistent with accountEnabled, OR
      4. Required identity fields are absent from actual_state

    ``orgpath_codebook`` accepts either a ``set[str]`` of active codes
    (legacy contract — only Value Drift is emitted) or a
    :class:`uiao.modernization.orgtree.codebook.Codebook`, in which case
    the classifier additionally recognises Phantom Drift (value landed in
    the deprecated list). If omitted, only format validation is applied.
    """
    active_codes, deprecated_codes = _resolve_codebook(orgpath_codebook)
    delta = _dict_delta(expected_state, actual_state)
    all_changed = set(delta.get("changed", [])) | set(delta.get("added", [])) | set(delta.get("removed", []))

    reasons: List[str] = []

    # Check 1: sentinel field changed
    if all_changed & _IDENTITY_SENTINEL_FIELDS:
        reasons.append(f"sentinel fields changed: {sorted(all_changed & _IDENTITY_SENTINEL_FIELDS)}")

    # Check 2: OrgPath validation
    orgpath_value = (
        actual_state.get("orgpath") or actual_state.get("org_path") or actual_state.get("extension_attribute_1")
    )
    if orgpath_value is None:
        reasons.append("OrgPath missing from identity object")
    elif not _ORGPATH_REGEX.match(str(orgpath_value)):
        reasons.append(f"OrgPath '{orgpath_value}' fails format validation ^ORG(-[A-Z]{{2,6}}){{0,4}}$")
    elif deprecated_codes is not None and str(orgpath_value) in deprecated_codes:
        reasons.append(f"OrgPath '{orgpath_value}' is deprecated in the codebook (Phantom Drift)")
    elif active_codes is not None and str(orgpath_value) not in active_codes:
        reasons.append(f"OrgPath '{orgpath_value}' not in canonical codebook")

    # Check 3: lifecycle consistency
    lifecycle = actual_state.get("lifecycle_state") or actual_state.get("extensionAttribute3")
    account_enabled = actual_state.get("account_enabled") or actual_state.get("accountEnabled")
    if lifecycle and account_enabled is not None:
        expected_enabled = _LIFECYCLE_ACCOUNT_RULES.get(str(lifecycle).upper())
        if expected_enabled is not None and bool(account_enabled) != expected_enabled:
            reasons.append(f"Lifecycle '{lifecycle}' inconsistent with accountEnabled={account_enabled}")

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


# ---------------------------------------------------------------------------
# DRIFT-SEMANTIC Classifier  (ADR-012 DT-02)
# ---------------------------------------------------------------------------

_SEMANTIC_WEAKENING_FIELDS = {
    "mfa_enabled": (False, "MFA must be enabled"),
    "legacy_auth_enabled": (True, "Legacy auth must be disabled"),
    "modern_auth_enabled": (False, "Modern auth must be enabled"),
    "password_never_expires": (True, "Passwords must expire"),
    "external_sharing_enabled": (True, "External sharing must be disabled"),
    "anonymous_sharing_enabled": (True, "Anonymous sharing must be disabled"),
    "public_access_enabled": (True, "Public access must be disabled"),
    "audit_log_enabled": (False, "Audit logging must be enabled"),
    "unified_audit_log_enabled": (False, "Unified audit log must be enabled"),
    "encryption_at_rest": (False, "Encryption at rest must be enabled"),
    "tls_enforcement": (False, "TLS enforcement must be enabled"),
    "ca_scope_tenant_wide": (True, "CA policy must not be tenant-wide"),
    "safe_links_enabled": (False, "Safe Links must be enabled"),
    "safe_attachments_enabled": (False, "Safe Attachments must be enabled"),
}
_SEMANTIC_UPPER_BOUND = {
    "max_inactive_days": 90,
    "patch_sla_days": 30,
    "session_timeout_minutes": 480,
    "sign_in_frequency_hours": 24,
}
_SEMANTIC_LOWER_BOUND = {"audit_retention_days": 90}


def classify_semantic_drift(*, resource_id, policy_ref, expected_state, actual_state, provenance, drift_id=None):  # type: ignore[no-untyped-def]
    delta = _dict_delta(expected_state, actual_state)
    reasons = []
    for field, (bad_val, msg) in _SEMANTIC_WEAKENING_FIELDS.items():
        if field in actual_state:
            val = actual_state[field]
            if (val == bad_val or str(val).lower() == str(bad_val).lower()) and expected_state.get(field) != val:
                reasons.append(f"{field}={val!r}: {msg}")
    for field, max_val in _SEMANTIC_UPPER_BOUND.items():
        n = actual_state.get(field)
        if n is not None:
            try:
                if float(n) > max_val:
                    reasons.append(f"{field}={n} exceeds policy maximum {max_val}")
            except (TypeError, ValueError):
                pass
    for field, min_val in _SEMANTIC_LOWER_BOUND.items():
        n = actual_state.get(field)
        if n is not None:
            try:
                if float(n) < min_val:
                    reasons.append(f"{field}={n} below policy minimum {min_val}")
            except (TypeError, ValueError):
                pass
    if not reasons:
        return None
    expected_hash = canonical_hash(expected_state)
    actual_hash = canonical_hash(actual_state)
    security_critical = any(kw in r for r in reasons for kw in ("mfa_enabled", "audit_log", "encryption", "tls"))
    risk = "unauthorized" if security_critical else _classify_drift(expected_hash, actual_hash, delta)
    return DriftState(
        id=drift_id or f"drift-semantic:{resource_id}:{policy_ref}",
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        drift_detected=True,
        classification=risk,
        delta={**delta, "semantic_reasons": reasons},
        provenance=provenance,
        drift_class=DRIFT_SEMANTIC,
    )


def classify_drift(
    *,
    resource_id: str,
    policy_ref: str,
    expected_state: Dict[str, Any],
    actual_state: Dict[str, Any],
    provenance: ProvenanceRecord,
    drift_id: Optional[str] = None,
    orgpath_codebook: Optional[OrgPathCodebook] = None,
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

    # DRIFT-SEMANTIC second
    semantic = classify_semantic_drift(
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_state=expected_state,
        actual_state=actual_state,
        provenance=provenance,
        drift_id=drift_id,
    )
    if semantic is not None:
        return semantic  # type: ignore[no-any-return]

    # DRIFT-IDENTITY third
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
