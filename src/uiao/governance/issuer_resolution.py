"""IssuerResolver — DRIFT-IDENTITY runtime issuer-chain validation (UIAO_110, ADR-012).

This module implements the **runtime issuer-chain** angle of DRIFT-IDENTITY.
The sibling :mod:`uiao.governance.drift` module's
:func:`classify_identity_drift` covers the **state-diff** angle (OrgPath
format, lifecycle consistency, sentinel field changes between snapshots).
Together they answer two distinct identity-trust questions:

============================  =========================================
detector                       what it catches
============================  =========================================
classify_identity_drift        OrgPath / lifecycle / required-field
                               *changes* between two snapshots
IssuerResolver                 leaf certificate's issuer chain does
                               not resolve to the declared trust
                               anchor, or no anchor declared at all
============================  =========================================

Both produce ``drift_class="DRIFT-IDENTITY"`` findings; this module is
the substrate's runtime answer to "is this identity claim actually
anchored to a trust root we recognize?".

Pipeline:

    canon registries (modernization-registry.yaml + adapter-registry.yaml)
            │
            ▼
    load_trust_anchors(registries) → {adapter_id: TrustAnchor}
            │
            ▼
    IssuerResolver.validate(adapter_id, observed_chain)
            │
            ▼
    IssuerChainReport(chain_reaches_anchor, broken_at, ...)
            │
            ▼
    .as_drift_state(...) → DriftState(drift_class="DRIFT-IDENTITY", severity="P1")

Trust-anchor declaration shape (canon convention introduced by this module):

    - id: entra-id
      certificate-anchored: true
      trust-anchor:
        subject: "CN=Microsoft Identity Verification Root Certificate Authority 2020"
        fingerprint_sha256: "8a4ca3...b9"
        # optional — fingerprint OR subject is required; fingerprint preferred

The fingerprint is the canonical identifier for the anchor; subject is
human-readable but not authoritative under cross-signing scenarios.

Severity policy:
    - Chain doesn't reach declared anchor:        P1 (always)
    - Chain has unrecognized issuer mid-link:     P1
    - Adapter claims certificate-anchored=true
      but declares no trust-anchor:               P2 (registry hygiene;
                                                  cannot validate)
    - Adapter declares certificate-anchored=false: skipped
    - Empty observed chain (no certificate
      surfaced this dispatch):                    no finding (in-scope)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Optional

import yaml

from uiao.ir.models.core import DriftState, ProvenanceRecord, canonical_hash

DRIFT_IDENTITY: Literal["DRIFT-IDENTITY"] = "DRIFT-IDENTITY"


# ---------------------------------------------------------------------------
# Trust anchor model + registry loader
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrustAnchor:
    """A canonical trust-anchor declaration for one adapter.

    Either ``fingerprint_sha256`` or ``subject`` is required; ``fingerprint``
    is preferred because it survives cross-signing. Both may be present.
    """

    subject: str = ""
    fingerprint_sha256: str = ""

    @property
    def declared(self) -> bool:
        return bool(self.subject or self.fingerprint_sha256)


def _adapter_entries(doc: Optional[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Pluck ``adapters: [...]`` out of a loaded registry doc."""
    if not doc:
        return []
    if isinstance(doc, list):
        return [a for a in doc if isinstance(a, Mapping)]
    candidates = doc.get("adapters") or doc.get("modernization_adapters")
    if isinstance(candidates, list):
        return [a for a in candidates if isinstance(a, Mapping)]
    return []


def _coerce_anchor(value: Any) -> TrustAnchor:
    """Normalize a YAML ``trust-anchor:`` value to a TrustAnchor.

    Accepts either a mapping with ``subject`` / ``fingerprint_sha256``
    keys, or a bare string interpreted as the subject DN.
    """
    if isinstance(value, Mapping):
        return TrustAnchor(
            subject=str(value.get("subject", "")).strip(),
            fingerprint_sha256=str(value.get("fingerprint_sha256", "")).strip().lower(),
        )
    if isinstance(value, str):
        return TrustAnchor(subject=value.strip())
    return TrustAnchor()


def load_trust_anchors(
    registries: Iterable[str | Path],
) -> dict[str, TrustAnchor]:
    """Read registry YAMLs and return ``{adapter_id: TrustAnchor}``.

    Adapters without a ``trust-anchor:`` key are absent from the result —
    distinct from an empty TrustAnchor, which would mean an explicit
    declaration with no fields. Later registries override earlier.
    """
    out: dict[str, TrustAnchor] = {}
    for path in registries:
        p = Path(path)
        if not p.is_file():
            continue
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        for entry in _adapter_entries(doc):
            adapter_id = str(entry.get("id", "")).strip()
            if not adapter_id:
                continue
            if "trust-anchor" in entry:
                out[adapter_id] = _coerce_anchor(entry.get("trust-anchor"))
    return out


# ---------------------------------------------------------------------------
# Certificate-link model (input to the resolver)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CertificateLink:
    """One link in an observed certificate chain.

    Adapters serializing their chain into ``evidence.json`` should emit a
    list of these (as plain dicts; the resolver coerces). The leaf is the
    first entry, each subsequent entry the issuer of the previous.
    """

    subject: str
    issuer: str
    fingerprint_sha256: str = ""

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CertificateLink:
        return cls(
            subject=str(raw.get("subject", "")).strip(),
            issuer=str(raw.get("issuer", "")).strip(),
            fingerprint_sha256=str(raw.get("fingerprint_sha256", "")).strip().lower(),
        )


def _coerce_chain(items: Iterable[Any]) -> tuple[CertificateLink, ...]:
    out: list[CertificateLink] = []
    for raw in items:
        if isinstance(raw, Mapping):
            link = CertificateLink.from_dict(raw)
            if link.subject or link.issuer or link.fingerprint_sha256:
                out.append(link)
    return tuple(out)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IssuerChainReport:
    """Outcome of validating one adapter's observed certificate chain."""

    adapter_id: str
    declared_anchor: TrustAnchor
    chain: tuple[CertificateLink, ...]
    chain_reaches_anchor: bool
    broken_at: int = -1
    """Index of the first chain link whose issuer doesn't appear as a
    subsequent subject. ``-1`` when no break is detected (either the
    chain is well-linked or there's no chain to inspect)."""
    missing_declaration: bool = False
    unanchored_chain: bool = False
    """True when the chain is well-linked but its terminal issuer does
    not match the declared trust anchor (subject DN nor fingerprint)."""

    @property
    def has_violation(self) -> bool:
        if self.missing_declaration:
            return True
        if not self.chain:
            return False  # nothing to validate
        return self.broken_at >= 0 or self.unanchored_chain

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "declared_anchor": {
                "subject": self.declared_anchor.subject,
                "fingerprint_sha256": self.declared_anchor.fingerprint_sha256,
            },
            "chain": [
                {
                    "subject": link.subject,
                    "issuer": link.issuer,
                    "fingerprint_sha256": link.fingerprint_sha256,
                }
                for link in self.chain
            ],
            "chain_reaches_anchor": self.chain_reaches_anchor,
            "broken_at": self.broken_at,
            "missing_declaration": self.missing_declaration,
            "unanchored_chain": self.unanchored_chain,
            "has_violation": self.has_violation,
        }

    def as_drift_state(
        self,
        *,
        provenance: ProvenanceRecord,
        policy_ref: str = "issuer-chain",
        drift_id: Optional[str] = None,
    ) -> Optional[DriftState]:
        """Project the report into a DriftState when there's a violation."""
        if not self.has_violation:
            return None
        if self.missing_declaration:
            reasons = [
                f"adapter '{self.adapter_id}' declares certificate-anchored=true "
                "but has no trust-anchor: declaration in canon registry"
            ]
        elif self.broken_at >= 0:
            link = self.chain[self.broken_at]
            reasons = [
                f"chain link {self.broken_at} (subject='{link.subject}') has "
                f"issuer='{link.issuer}' which does not appear as the subject "
                "of any subsequent link"
            ]
        else:
            terminal = self.chain[-1]
            reasons = [
                f"chain terminal issuer '{terminal.issuer}' "
                f"(subject='{terminal.subject}') does not match declared "
                f"trust anchor "
                f"(subject='{self.declared_anchor.subject}', "
                f"fingerprint='{self.declared_anchor.fingerprint_sha256}')"
            ]
        expected_state = {
            "anchor_subject": self.declared_anchor.subject,
            "anchor_fingerprint_sha256": self.declared_anchor.fingerprint_sha256,
        }
        actual_state: dict[str, Any] = {
            "chain_subjects": [link.subject for link in self.chain],
            "chain_issuers": [link.issuer for link in self.chain],
            "chain_fingerprints": [link.fingerprint_sha256 for link in self.chain],
        }
        delta = {
            "added": [],
            "removed": [],
            "changed": [],
            "issuer_chain_reasons": reasons,
        }
        return DriftState(
            id=drift_id or f"drift-identity:issuer-chain:{self.adapter_id}",
            resource_id=f"adapter:{self.adapter_id}",
            policy_ref=policy_ref,
            expected_hash=canonical_hash(expected_state),
            actual_hash=canonical_hash(actual_state),
            drift_detected=True,
            classification="unauthorized",
            delta=delta,
            provenance=provenance,
            drift_class=DRIFT_IDENTITY,
        )


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


@dataclass
class IssuerResolver:
    """Validates observed adapter certificate chains against canon trust
    anchors.

    Construction is cheap: store a precomputed ``{adapter_id: TrustAnchor}``
    mapping. Pre-load anchors once via :func:`load_trust_anchors` and reuse
    the resolver across many adapter dispatches.
    """

    anchors: Mapping[str, TrustAnchor] = field(default_factory=dict)

    def validate(
        self,
        adapter_id: str,
        observed_chain: Iterable[Any],
    ) -> IssuerChainReport:
        """Compute a report for one (adapter, chain) pair.

        ``observed_chain`` is an iterable of dicts with at least
        ``subject`` and ``issuer`` keys; ``fingerprint_sha256`` is
        recommended when available. Empty chain is allowed (the adapter
        dispatched but didn't surface a certificate). Coerced to
        :class:`CertificateLink` internally.
        """
        chain = _coerce_chain(observed_chain)
        anchor = self.anchors.get(adapter_id, TrustAnchor())
        missing = adapter_id not in self.anchors

        # Detect well-linked vs broken chain. Each link[i].issuer should
        # match link[i+1].subject (chain order: leaf → ... → root).
        broken_at = -1
        for i in range(len(chain) - 1):
            if chain[i].issuer != chain[i + 1].subject:
                broken_at = i
                break

        # Anchor match: terminal issuer/fingerprint matches declared
        # anchor. Fingerprint match is preferred when both are declared.
        chain_reaches_anchor = False
        unanchored_chain = False
        if chain and not missing and broken_at < 0 and anchor.declared:
            terminal = chain[-1]
            fingerprint_match = bool(anchor.fingerprint_sha256) and (
                terminal.fingerprint_sha256 == anchor.fingerprint_sha256
            )
            subject_match = bool(anchor.subject) and (
                terminal.issuer == anchor.subject or terminal.subject == anchor.subject
            )
            chain_reaches_anchor = fingerprint_match or subject_match
            unanchored_chain = not chain_reaches_anchor

        return IssuerChainReport(
            adapter_id=adapter_id,
            declared_anchor=anchor,
            chain=chain,
            chain_reaches_anchor=chain_reaches_anchor,
            broken_at=broken_at,
            missing_declaration=missing,
            unanchored_chain=unanchored_chain,
        )

    def validate_many(
        self,
        observations: Mapping[str, Iterable[Any]],
    ) -> list[IssuerChainReport]:
        """Validate many adapters at once. Order: input iteration order."""
        return [self.validate(aid, chain) for aid, chain in observations.items()]


# ---------------------------------------------------------------------------
# Scheduler-run helper
# ---------------------------------------------------------------------------


_OBSERVED_CHAIN_KEYS = (
    "certificate_chain",
    "issuer_chain",
)


def observed_chain_for_run(run_dir: Path | str) -> dict[str, list[dict[str, Any]]]:
    """Walk a UIAO_100 scheduler-run directory and extract per-adapter
    observed certificate chains.

    Looks under ``schedrun-*/adapters/<id>/evidence.json`` for any of:

        normalized_data.certificate_chain
        normalized_data.issuer_chain
        raw_data.certificate_chain (fallback)
        raw_data.issuer_chain (fallback)

    Each chain entry is a dict ``{subject, issuer, fingerprint_sha256}``.
    Adapters that emit no chain hint contribute an empty list — the
    resolver treats that as "no observable chain" (no violation).
    """
    import json as _json

    root = Path(run_dir)
    out: dict[str, list[dict[str, Any]]] = {}
    adapters_dir = root / "adapters"
    if not adapters_dir.is_dir():
        return out
    for adapter_dir in sorted(adapters_dir.iterdir()):
        if not adapter_dir.is_dir():
            continue
        evidence_path = adapter_dir / "evidence.json"
        if not evidence_path.is_file():
            continue
        try:
            payload = _json.loads(evidence_path.read_text(encoding="utf-8"))
        except (OSError, _json.JSONDecodeError):
            continue
        chain: list[dict[str, Any]] = []
        for container_key in ("normalized_data", "raw_data"):
            container = payload.get(container_key) or {}
            if not isinstance(container, dict):
                continue
            for key in _OBSERVED_CHAIN_KEYS:
                value = container.get(key)
                if isinstance(value, list):
                    chain = [v for v in value if isinstance(v, dict)]
                    break
            if chain:
                break
        out[adapter_dir.name] = chain
    return out


__all__ = [
    "DRIFT_IDENTITY",
    "CertificateLink",
    "IssuerChainReport",
    "IssuerResolver",
    "TrustAnchor",
    "load_trust_anchors",
    "observed_chain_for_run",
]
