"""Runtime drift validators — Phase 2 implementation of the four checks
that ADR-070 lists as sync (signature, identity, authz) and
non-blocking (semantic) at adapter emit time.

Each validator is a callable conforming to the `Validator` protocol:
it accepts an `Envelope` plus the originating claim and adapter_id and
returns an `Optional[DriftFinding]`. A `None` return means the check
passed; a `DriftFinding` return means the check failed and the sink
should incorporate it into the emission decision.

Per ADR-072 §6, the sink's accept rule is P1-only: a P2 DRIFT-SEMANTIC
finding is logged but does not block emission. The validator pipeline
runs in declared order; the sink does not short-circuit on the first
finding because all findings are useful for the event log.

This file is a DRAFT skeleton. Promotion to
`src/uiao/telemetry/validators.py` happens when ADR-072 is ACCEPTED.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

# Imports resolve once Phase 0 / Phase 1 promote to canon paths.
from uiao.models.provenance import Envelope
from uiao.models.consent import ConsentEnvelope
from uiao.identity.resolver import IdentityPlaneResolver, load_resolver
from uiao.telemetry.provenance import DriftFinding
from uiao.freshness.drift_semantic import (
    AdapterFreshnessPolicy,
    DRIFT_TYPE as SEMANTIC_DRIFT_TYPE,
    _classify,
    _parse_iso,
    _severity_for_status,
    load_adapter_windows,
    resolve_policy,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validator protocol
# ---------------------------------------------------------------------------


class Validator(Protocol):
    """Common shape for every runtime drift validator.

    Validators are stateless w.r.t. emissions but may hold cached state
    derived from canon (e.g., the trust-anchor map for an adapter, the
    freshness window for an adapter). Cached state is loaded at sink
    init time and refreshed on a manual reload signal — not per emit.
    """

    drift_class: str
    severity: str

    def check(
        self,
        envelope: Envelope,
        *,
        claim: dict[str, Any],
        adapter_id: str,
    ) -> Optional[DriftFinding]:
        ...


# ---------------------------------------------------------------------------
# Signature validator — DRIFT-PROVENANCE P1
# ---------------------------------------------------------------------------


@dataclass
class SignatureValidator:
    """Verify the envelope signature resolves to a registered trust anchor.

    Per ADR-072 §2, this is the cheap registry-lookup check that runs
    first. The adapter's manifest carries a `trust-anchor:` declaration
    (validated at canon-hygiene level by the substrate walker); the
    runtime check verifies the envelope's `signature` (mTLS thumbprint)
    matches one of those anchors.

    Phase 2 ships a stub that accepts any non-empty signature; the
    real trust-anchor map loading is wired alongside the AD survey
    adapter retrofit in Phase 1b. The pipeline placement and emission
    decision are correct now — only the lookup function needs to
    populate.
    """

    drift_class = "DRIFT-PROVENANCE"
    severity = "P1"

    def check(
        self,
        envelope: Envelope,
        *,
        claim: dict[str, Any],
        adapter_id: str,
    ) -> Optional[DriftFinding]:
        if not envelope.signature:
            return DriftFinding(
                drift_class=self.drift_class,
                severity=self.severity,
                path=envelope.claim_id,
                detail=f"envelope from adapter '{adapter_id}' carries no signature",
            )
        # Phase 2 STUB — wire to trust-anchor map in Phase 1b retrofit cycle.
        # if envelope.signature not in trust_anchors_for(adapter_id):
        #     return DriftFinding(...)
        return None


# ---------------------------------------------------------------------------
# Identity validator — DRIFT-IDENTITY P1
# ---------------------------------------------------------------------------


@dataclass
class IdentityValidator:
    """Verify `envelope.issuer_identity` resolves against the identity plane.

    Delegates to a pluggable `IdentityPlaneResolver` per ADR-072 §3.
    Default resolver is `EntraIDResolver`; adapter manifests can
    declare alternative resolvers (Login.gov, PIV/USAccess, federal IdP).
    """

    drift_class = "DRIFT-IDENTITY"
    severity = "P1"

    resolver: IdentityPlaneResolver

    @classmethod
    def from_manifest(cls, manifest: dict[str, Any]) -> "IdentityValidator":
        """Construct an IdentityValidator from an adapter manifest.

        Reads `identity_resolver:` (default empty → EntraIDResolver) and
        caches the resolver instance. The sink calls this once per
        adapter at init time.
        """
        return cls(resolver=load_resolver(manifest.get("identity_resolver", "")))

    def check(
        self,
        envelope: Envelope,
        *,
        claim: dict[str, Any],
        adapter_id: str,
    ) -> Optional[DriftFinding]:
        if not envelope.issuer_identity:
            return DriftFinding(
                drift_class=self.drift_class,
                severity=self.severity,
                path=envelope.claim_id,
                detail=f"envelope from adapter '{adapter_id}' has empty issuer_identity",
            )
        result = self.resolver.resolve(envelope.issuer_identity)
        if not result.resolved:
            return DriftFinding(
                drift_class=self.drift_class,
                severity=self.severity,
                path=envelope.claim_id,
                detail=(
                    f"issuer_identity {envelope.issuer_identity} did not resolve "
                    f"via {self.resolver.RESOLVER_ID}: {result.reason or 'no detail'}"
                ),
            )
        return None


# ---------------------------------------------------------------------------
# Authz validator — DRIFT-AUTHZ P1
# ---------------------------------------------------------------------------


@dataclass
class AuthzValidator:
    """Verify the envelope's consent envelope (if present) is active and permits the claim destination.

    Per ADR-072 §4, the §3/§5 enforcement rules from
    `17_ConsentEnvelope.qmd` live on the `ConsentEnvelope` model
    (`is_active`, `permits`, `requires_canon_steward_countersignature`).
    The validator wires those methods into the emission decision; it
    does not re-implement the rules.

    Claims without a `consent_envelope` are accepted — not every claim
    is under consent governance. The canon-hygiene
    `_scan_consent_envelope` in the substrate walker handles the
    "adapter has no scope declaration" case at PR time.
    """

    drift_class = "DRIFT-AUTHZ"
    severity = "P1"

    def check(
        self,
        envelope: Envelope,
        *,
        claim: dict[str, Any],
        adapter_id: str,
    ) -> Optional[DriftFinding]:
        if envelope.consent_envelope is None:
            return None

        # The runtime consent envelope on the wire is the full
        # 15-field ConsentEnvelope from 17_ConsentEnvelope §3. The
        # provenance Envelope carries a thin ConsentEnvelopeRef
        # (consent_id + scope); the full object is materialized from
        # the consent registry. Phase 2 wires the registry; the
        # validator's contract is to operate on a full ConsentEnvelope.
        consent = _materialize_consent_envelope(envelope.consent_envelope.consent_id)
        if consent is None:
            return DriftFinding(
                drift_class=self.drift_class,
                severity=self.severity,
                path=envelope.claim_id,
                detail=(
                    f"envelope references consent {envelope.consent_envelope.consent_id} "
                    "which could not be loaded from the consent registry"
                ),
            )

        if not consent.is_active():
            return DriftFinding(
                drift_class=self.drift_class,
                severity=self.severity,
                path=envelope.claim_id,
                detail=(
                    f"consent envelope {consent.envelope_id} has expired "
                    f"(consent_expiry={consent.consent_expiry})"
                ),
            )

        destination = _extract_claim_destination(claim)
        if destination is not None and not consent.permits(use_code=destination):
            return DriftFinding(
                drift_class=self.drift_class,
                severity=self.severity,
                path=envelope.claim_id,
                detail=(
                    f"claim destination {destination!r} is not in permitted_uses "
                    f"of consent envelope {consent.envelope_id}"
                ),
            )

        if consent.requires_canon_steward_countersignature and not consent.mou_reference:
            return DriftFinding(
                drift_class=self.drift_class,
                severity=self.severity,
                path=envelope.claim_id,
                detail=(
                    f"consent envelope {consent.envelope_id} has cross_boundary_flag=true "
                    "but no mou_reference; Canon Steward countersignature required per "
                    "17_ConsentEnvelope §5"
                ),
            )

        return None


# ---------------------------------------------------------------------------
# Semantic validator — DRIFT-SEMANTIC P2 (non-blocking)
# ---------------------------------------------------------------------------


@dataclass
class SemanticValidator:
    """Verify the envelope's extraction_timestamp is within the adapter's freshness window.

    Per ADR-072 §5, this validator is a thin shim over
    `src/uiao/freshness/drift_semantic.py`. The shim resolves the
    adapter's freshness window once at init time and re-uses the
    existing `_classify` and `_severity_for_status` functions so the
    inline runtime check and the scheduler-time evaluator can never
    drift apart.

    Per ADR-072 §1, this validator emits P2 findings that do NOT block
    emission — the claim is accepted, but the staleness is logged
    alongside the `accept` event.
    """

    drift_class = SEMANTIC_DRIFT_TYPE  # "DRIFT-SEMANTIC"
    severity = "P2"

    policy: AdapterFreshnessPolicy

    @classmethod
    def for_adapter(
        cls,
        *,
        adapter_id: str,
        registries: list[Path],
        ksi_id: Optional[str] = None,
    ) -> "SemanticValidator":
        """Resolve the adapter's freshness policy and cache it on the validator."""
        windows = load_adapter_windows(registries)
        policy = resolve_policy(adapter_id, windows=windows, ksi_id=ksi_id)
        return cls(policy=policy)

    def check(
        self,
        envelope: Envelope,
        *,
        claim: dict[str, Any],
        adapter_id: str,
    ) -> Optional[DriftFinding]:
        ts = envelope.extraction_timestamp
        if not ts:
            # Missing timestamp is P1 in drift_semantic's severity mapping
            # but our envelope schema makes extraction_timestamp required,
            # so this branch should never fire in practice. Defensive.
            return DriftFinding(
                drift_class=self.drift_class,
                severity=_severity_for_status("missing-timestamp"),
                path=envelope.claim_id,
                detail="envelope has empty extraction_timestamp",
            )
        now = datetime.now(timezone.utc)
        age_hours = (now - _parse_iso(ts)).total_seconds() / 3600.0
        if age_hours < 0:
            # Future-dated timestamp is suspicious but not stale.
            return None

        status = _classify(age_hours, self.policy.window_hours)
        if status == "fresh":
            return None

        return DriftFinding(
            drift_class=self.drift_class,
            severity=_severity_for_status(status),
            path=envelope.claim_id,
            detail=(
                f"envelope is {status} (age={age_hours:.2f}h, "
                f"window={self.policy.window_hours}h, "
                f"policy_source={self.policy.source})"
            ),
        )


# ---------------------------------------------------------------------------
# Pipeline composition
# ---------------------------------------------------------------------------


def build_pipeline(
    *,
    adapter_id: str,
    manifest: dict[str, Any],
    registries: list[Path],
) -> list[Validator]:
    """Construct the four-validator pipeline for a given adapter.

    Called once per adapter at sink init time; the returned list is
    the input to `provenance_sink.emit()` for every emission from that
    adapter. The order is fixed per ADR-072 §2:

      1. SignatureValidator  — cheap; fail fast
      2. IdentityValidator   — network-bound; cached
      3. AuthzValidator      — registry lookup + envelope inspection
      4. SemanticValidator   — in-process; always runs last

    The sink does NOT short-circuit on the first finding because every
    finding is useful in the event log. The accept rule is "no P1
    findings" per ADR-072 §6.
    """
    return [
        SignatureValidator(),
        IdentityValidator.from_manifest(manifest),
        AuthzValidator(),
        SemanticValidator.for_adapter(adapter_id=adapter_id, registries=registries),
    ]


# ---------------------------------------------------------------------------
# Helpers (private)
# ---------------------------------------------------------------------------


def _materialize_consent_envelope(consent_id: str) -> Optional[ConsentEnvelope]:
    """Load the full ConsentEnvelope by consent_id from the consent registry.

    Phase 2 STUB — returns None for unknown IDs. The consent registry
    binding lands in PR-2b alongside the HRIT adapter retrofit (the
    first adapter that emits citizen-PII claims under consent).
    """
    return None


def _extract_claim_destination(claim: dict[str, Any]) -> Optional[str]:
    """Extract the use_code that the AUTHZ validator checks against `permitted_uses`.

    The canonical claim schema (adr-005) doesn't yet pin a destination
    field. Phase 2 STUB — returns None, which causes the validator to
    skip the `permits` check. The claim schema extension that adds a
    `destination` or `use_code` field is a follow-on ADR.
    """
    return claim.get("use_code") or claim.get("destination")
