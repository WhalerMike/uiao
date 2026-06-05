"""
src/uiao/governance/drift.py
-----------------------------
UIAO Drift Engine — canonical drift taxonomy classifiers.

Implements:
  - Generic DriftState builder (existing, unchanged)
  - DRIFT-AUTHZ classifier  (ADR-012 DT-04)
  - DRIFT-IDENTITY classifier (ADR-012 DT-05)
  - DRIFT-PROVENANCE classifier (ADR-012 DT-03) — in-memory evidence-envelope
    integrity, complementing the substrate walker's structural provenance check

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

from typing import Any, Dict, List, Literal, Set, Union

from uiao.ir.models.core import DriftState, ProvenanceRecord, canonical_hash

# Typing alias for the codebook parameter. Callers may pass either:
#   - a flat ``set[str]`` of active OrgPath codes (legacy contract), or
#   - a ``uiao.modernization.orgtree.codebook.Codebook`` instance, which
#     additionally lets the classifier emit Phantom Drift against deprecated
#     codes (UIAO_151 §Drift). Duck-typed to avoid a circular import.
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
    "DRIFT-SSOT-CONTENTION",
]
DRIFT_SCHEMA: DriftClassLiteral = "DRIFT-SCHEMA"
DRIFT_SEMANTIC: DriftClassLiteral = "DRIFT-SEMANTIC"
DRIFT_PROVENANCE: DriftClassLiteral = "DRIFT-PROVENANCE"
DRIFT_AUTHZ: DriftClassLiteral = "DRIFT-AUTHZ"
DRIFT_IDENTITY: DriftClassLiteral = "DRIFT-IDENTITY"
DRIFT_BOUNDARY: DriftClassLiteral = "DRIFT-BOUNDARY"
DRIFT_SSOT_CONTENTION: DriftClassLiteral = "DRIFT-SSOT-CONTENTION"


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
    drift_id: str | None = None,
    drift_class: DriftClassLiteral | None = None,
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
    drift_id: str | None = None,
) -> DriftState | None:
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

# _ORGPATH_REGEX (Model A composite-string format) removed per ADR-078;
# Model C OrgPath has no single composite regex (one regex per typed
# facet). Per-facet validation is performed by _classify_facet_drift
# (below), which delegates format/membership checks to each Facet.

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


# Model A's _resolve_codebook (composite-string .codes / .deprecated_codes)
# was removed per ADR-078. Its Model C replacement is _classify_facet_drift
# below: a per-facet classifier over the rebuilt 15-facet Codebook
# (ADR-084 Phase 5 consumers are now in place), restoring DRIFT-IDENTITY's
# OrgPath-validation arm that ADR-078 Phase 1 had temporarily disabled.


def _is_model_c_codebook(codebook: object) -> bool:
    """True for a Model C per-facet ``Codebook`` (duck-typed).

    ``orgpath_codebook`` is historically typed ``Set[str] | Any`` for the
    Model A composite-string set; a Model C ``Codebook`` is distinguished by
    exposing a ``facets`` mapping whose members carry ``is_active`` /
    ``is_deprecated``. Anything else (None, a bare set) is treated as "no
    per-facet codebook supplied" and skips per-facet validation.
    """
    facets = getattr(codebook, "facets", None)
    if not facets:
        return False
    return hasattr(next(iter(facets.values())), "is_active")


def _classify_facet_drift(codebook: Any, actual_state: Dict[str, Any]) -> tuple[List[str], List[Dict[str, Any]]]:
    """Per-facet OrgPath validation for DRIFT-IDENTITY (Model C).

    Iterates every facet the Codebook declares (no hard-coded slot map) and
    reads the principal's value for that facet from ``actual_state`` by the
    facet's ``extensionAttribute`` slot, falling back to the facet name.
    Each value is classified per UIAO_163 Format / Value / Phantom semantics:

      * ``deprecated``           — value retired; carries its ``replacement``
      * ``phantom``              — non-empty value unknown to the codebook
      * ``reserved_violation``   — a reserved slot carries a value
      * ``active`` / ``empty`` / ``reserved_empty`` — not drift

    Returns ``(reasons, per_facet)`` where ``reasons`` lists the human-readable
    drift findings (deprecated / phantom / reserved violations) and
    ``per_facet`` is the structured per-slot result set for every facet; the
    caller emits the drifting subset into the DriftState delta.
    """
    reasons: List[str] = []
    per_facet: List[Dict[str, Any]] = []
    for name, facet in codebook.facets.items():
        slot = facet.attribute
        raw = actual_state.get(slot)
        if raw is None:
            raw = actual_state.get(name)
        value = "" if raw is None else str(raw)

        entry: Dict[str, Any] = {"facet": name, "slot": slot, "value": value}

        if facet.kind == "reserved":
            if value != "":
                entry["status"] = "reserved_violation"
                reasons.append(f"reserved facet '{name}' ({slot}) is populated with '{value}'")
            else:
                entry["status"] = "reserved_empty"
            per_facet.append(entry)
            continue

        if value == "":
            # Empty typed (allow_empty) or unset enumerated slot. Absence of a
            # *required* field is handled separately by the required-field check.
            entry["status"] = "empty"
            per_facet.append(entry)
            continue

        if facet.is_deprecated(value):
            replacement = facet.replacement_for(value)
            entry["status"] = "deprecated"
            entry["replacement"] = replacement
            reasons.append(f"facet '{name}' value '{value}' is deprecated (replaced_by '{replacement}')")
            per_facet.append(entry)
            continue

        if facet.is_active(value):
            entry["status"] = "active"
            per_facet.append(entry)
            continue

        entry["status"] = "phantom"
        reasons.append(f"facet '{name}' value '{value}' is not in the codebook (phantom)")
        per_facet.append(entry)

    return reasons, per_facet


def classify_identity_drift(
    *,
    resource_id: str,
    policy_ref: str,
    expected_state: Dict[str, Any],
    actual_state: Dict[str, Any],
    provenance: ProvenanceRecord,
    drift_id: str | None = None,
    orgpath_codebook: OrgPathCodebook | None = None,
) -> DriftState | None:
    """
    Classify identity drift (DRIFT-IDENTITY).

    Returns a DriftState with drift_class=DRIFT-IDENTITY if identity
    drift is detected, or None if no identity drift is present.

    Identity drift is detected when:
      1. Any sentinel identity field has changed, OR
      2. A per-facet OrgPath value is deprecated, phantom (unknown to the
         codebook), or a reserved slot is populated — when a Model C
         ``orgpath_codebook`` is supplied, OR
      3. Lifecycle state is inconsistent with accountEnabled, OR
      4. Required identity fields are absent from actual_state

    When a Model C per-facet ``orgpath_codebook`` (15-facet, ADR-078) is
    supplied, OrgPath validation runs per facet via ``_classify_facet_drift``
    and the drifting facets (deprecated / phantom / reserved violations) are
    attached to the DriftState delta as ``per_facet`` — pipe-delimited
    ``facet|slot|value|status[|replacement]`` strings. A phantom value or a
    populated reserved slot elevates the finding to ``unauthorized`` (governance
    cannot determine what policy applies to an out-of-codebook facet value).
    With no codebook supplied the
    classifier behaves as before (sentinel / lifecycle / required-field arms
    only), preserving the legacy ``Set[str]`` caller contract.
    """
    delta = _dict_delta(expected_state, actual_state)
    all_changed = set(delta.get("changed", [])) | set(delta.get("added", [])) | set(delta.get("removed", []))

    reasons: List[str] = []
    per_facet: List[Dict[str, Any]] = []

    # Check 1: sentinel field changed
    if all_changed & _IDENTITY_SENTINEL_FIELDS:
        reasons.append(f"sentinel fields changed: {sorted(all_changed & _IDENTITY_SENTINEL_FIELDS)}")

    # Check 2: per-facet OrgPath validation against the Model C Codebook
    # (reintroduced post ADR-078 / ADR-084 Phase 5 — see _classify_facet_drift).
    if _is_model_c_codebook(orgpath_codebook):
        facet_reasons, per_facet = _classify_facet_drift(orgpath_codebook, actual_state)
        reasons.extend(facet_reasons)

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

    # A phantom (out-of-codebook) facet value or a populated reserved slot is
    # also unauthorized: governance cannot determine what policy applies to it.
    if any(p["status"] in ("phantom", "reserved_violation") for p in per_facet):
        risk = "unauthorized"

    delta_out: Dict[str, List[str]] = {**delta, "identity_reasons": reasons}
    # Emit the drifting facets as pipe-delimited `facet|slot|value|status[|replacement]`
    # strings (DriftState.delta is Dict[str, List[str]]); clean facets are omitted.
    drifting = [
        "|".join(
            [p["facet"], p["slot"], p["value"], p["status"]] + ([p["replacement"]] if p.get("replacement") else [])
        )
        for p in per_facet
        if p["status"] in ("deprecated", "phantom", "reserved_violation")
    ]
    if drifting:
        delta_out["per_facet"] = drifting

    drift_state_id = drift_id or f"drift-identity:{resource_id}:{policy_ref}"
    return DriftState(
        id=drift_state_id,
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        drift_detected=True,
        classification=risk,
        delta=delta_out,  # type: ignore[arg-type]
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


# ---------------------------------------------------------------------------
# DRIFT-PROVENANCE Classifier
# ADR-012 DT-03: Provenance drift
#
# Detects a broken or incomplete provenance envelope on a state/evidence
# record. This operates at the in-memory IR comparison layer and is the
# complement to the substrate walker's *structural* provenance check
# (`src/uiao/substrate/walker.py`), which catches dangling registry paths and
# code-citation references on disk. Together they cover the canonical
# DRIFT-PROVENANCE definition:
#   - UIAO_150 §Principle 2 — "Unsigned, unattributed changes are drift by
#     definition."
#   - UIAO_010 §Drift baseline — data referencing a source that no longer
#     resolves is a DRIFT-PROVENANCE finding by definition.
#
# Fires when:
#   1. INCOMPLETE envelope — a required attribution field (source / version /
#      timestamp) is missing or empty: the change is unattributed.
#   2. BROKEN envelope — content_hash is present but does not match
#      canonical_hash(actual_state): the record's claimed integrity hash
#      disagrees with the data it envelopes (tamper or stale seal).
#   3. CITATION drift — an expected_provenance is supplied and the actual
#      record's source or version no longer matches it: the evidence now
#      cites a re-pointed / different source than the baseline declared.
# ---------------------------------------------------------------------------

# Attribution fields that must be present and non-empty for a provenance
# envelope to be considered complete. (actor is intentionally excluded:
# ProvenanceRecord.actor is optional and many legitimate records omit it;
# a missing actor alone is not treated as drift here.)
_PROVENANCE_REQUIRED_FIELDS = ("source", "version", "timestamp")


def classify_provenance_drift(
    *,
    resource_id: str,
    policy_ref: str,
    expected_state: Dict[str, Any],
    actual_state: Dict[str, Any],
    provenance: ProvenanceRecord,
    drift_id: str | None = None,
    expected_provenance: ProvenanceRecord | None = None,
) -> DriftState | None:
    """
    Classify provenance drift (DRIFT-PROVENANCE).

    Returns a DriftState with drift_class=DRIFT-PROVENANCE if the provenance
    envelope around ``actual_state`` is incomplete, broken, or re-pointed, or
    None if the envelope is intact.

    Provenance drift is detected when:
      1. A required attribution field (source / version / timestamp) is
         missing or empty on ``provenance`` (incomplete envelope), OR
      2. ``provenance.content_hash`` is present but does not match the
         recomputed canonical hash of ``actual_state`` (broken seal), OR
      3. ``expected_provenance`` is supplied and the actual record's source
         or version no longer matches it (citation drift).

    A broken seal is always elevated to "unauthorized" — evidence whose
    integrity hash disagrees with its data cannot be trusted to support any
    downstream classification.
    """
    reasons: List[str] = []

    # Check 1: envelope completeness — unattributed changes are drift
    for field in _PROVENANCE_REQUIRED_FIELDS:
        val = getattr(provenance, field, None)
        if not val or (isinstance(val, str) and not val.strip()):
            reasons.append(f"provenance envelope incomplete: '{field}' missing or empty")

    # Check 2: envelope integrity — claimed seal vs recomputed actual hash
    claimed_hash = getattr(provenance, "content_hash", None)
    integrity_break = False
    if claimed_hash:
        recomputed = canonical_hash(actual_state)
        if claimed_hash != recomputed:
            integrity_break = True
            reasons.append(f"provenance content_hash {claimed_hash!r} does not match actual state hash {recomputed!r}")

    # Check 3: citation drift vs an expected provenance baseline
    if expected_provenance is not None:
        if expected_provenance.source != provenance.source:
            reasons.append(f"provenance source re-pointed: {expected_provenance.source!r} -> {provenance.source!r}")
        if expected_provenance.version != provenance.version:
            reasons.append(f"provenance version changed: {expected_provenance.version!r} -> {provenance.version!r}")

    if not reasons:
        return None  # Intact provenance envelope

    expected_hash = canonical_hash(expected_state)
    actual_hash = canonical_hash(actual_state)
    delta = _dict_delta(expected_state, actual_state)

    # A broken seal cannot be trusted — always unauthorized.
    risk = "unauthorized" if integrity_break else _classify_drift(expected_hash, actual_hash, delta)

    drift_state_id = drift_id or f"drift-provenance:{resource_id}:{policy_ref}"
    return DriftState(
        id=drift_state_id,
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        drift_detected=True,
        classification=risk,
        delta={**delta, "provenance_reasons": reasons},  # type: ignore[arg-type]
        provenance=provenance,
        drift_class=DRIFT_PROVENANCE,
    )


def classify_drift(
    *,
    resource_id: str,
    policy_ref: str,
    expected_state: Dict[str, Any],
    actual_state: Dict[str, Any],
    provenance: ProvenanceRecord,
    drift_id: str | None = None,
    orgpath_codebook: OrgPathCodebook | None = None,
) -> DriftState:
    """
    Run all drift classifiers in priority order and return the first match.

    Priority order (highest to lowest specificity):
      1. DRIFT-AUTHZ      — authorization escalation is highest priority
      2. DRIFT-PROVENANCE — a broken/unattributed evidence envelope undermines
                            trust in every other classification, so it is
                            checked before the state-delta classifiers
      3. DRIFT-SEMANTIC   — security-weakening value changes
      4. DRIFT-IDENTITY   — identity plane gaps block policy decisions
      5. Generic (DRIFT-SCHEMA / risky / unauthorized) — fallback

    If no specific classifier fires, falls back to the generic build_drift_state
    with drift_class=None (unclassified).

    The composite calls classify_provenance_drift without an
    ``expected_provenance`` baseline, so only the envelope-completeness and
    integrity checks apply here; citation-drift detection is available to
    callers that invoke classify_provenance_drift directly with a baseline.

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

    # DRIFT-PROVENANCE second — a broken evidence envelope is checked before
    # the state-delta classifiers because it undermines trust in all of them.
    provenance_drift = classify_provenance_drift(
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_state=expected_state,
        actual_state=actual_state,
        provenance=provenance,
        drift_id=drift_id,
    )
    if provenance_drift is not None:
        return provenance_drift

    # DRIFT-SEMANTIC third
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
