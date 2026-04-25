"""ConsentEnvelopeValidator — DRIFT-AUTHZ at registry level (UIAO_110, ADR-012).

This module implements the **scope-envelope** angle of DRIFT-AUTHZ. The
sibling :mod:`uiao.governance.drift` module implements the **state-diff**
angle (sentinel field changes, role count growth, escalation patterns).
Both produce ``drift_class="DRIFT-AUTHZ"`` findings; they detect different
classes of authorization violation:

============================  =========================================
detector                       what it catches
============================  =========================================
classify_authz_drift           role assignments, delegation, scope
                               *changes* between two snapshots
ConsentEnvelopeValidator       adapter API calls hitting object types
                               *outside its declared registry scope*
============================  =========================================

The consent-envelope angle answers "did the adapter touch something it
was never granted access to?" — distinct from "did the *value* of an
already-permitted attribute change?".

Pipeline:

    canon registry (modernization-registry.yaml + adapter-registry.yaml)
            │
            ▼
    load_adapter_envelopes(registries)  →  {adapter_id: declared_scope}
            │
            ▼
    ConsentEnvelopeValidator.validate(adapter_id, observed_scope)
            │
            ▼
    ConsentEnvelopeReport(in_scope, out_of_scope, missing_declaration)
            │
            ▼
    .as_drift_state(...) → DriftState(drift_class="DRIFT-AUTHZ", severity="P1")

Severity policy:
    - Out-of-scope access:      P1 (always — substrate trust contract)
    - Missing scope declaration: P1 (registry hygiene; cannot validate)
    - All-in-scope:             no finding
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Optional

import yaml

from uiao.ir.models.core import DriftState, ProvenanceRecord, canonical_hash

DRIFT_AUTHZ: Literal["DRIFT-AUTHZ"] = "DRIFT-AUTHZ"


# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------


def _adapter_entries(doc: Optional[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Pluck ``adapters: [...]`` out of a loaded registry doc.

    Tolerates both top-level ``adapters:`` key and bare list documents.
    Returns ``[]`` for missing / malformed input.
    """
    if not doc:
        return []
    if isinstance(doc, list):
        return [a for a in doc if isinstance(a, Mapping)]
    candidates = doc.get("adapters") or doc.get("modernization_adapters")
    if isinstance(candidates, list):
        return [a for a in candidates if isinstance(a, Mapping)]
    return []


def load_adapter_envelopes(
    registries: Iterable[str | Path],
) -> dict[str, set[str]]:
    """Read registry YAMLs and return ``{adapter_id: declared_scope_set}``.

    Later registries override earlier ones for the same ``id``. Adapters
    with an explicit empty list (``scope: []``) are preserved as an empty
    set — that is meaningfully distinct from "no declaration" (missing
    key), which the validator treats as a registry-hygiene finding.
    """
    out: dict[str, set[str]] = {}
    declared_keys: set[str] = set()
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
            if "scope" in entry:
                raw = entry.get("scope") or []
                if isinstance(raw, list):
                    out[adapter_id] = {str(s).strip() for s in raw if str(s).strip()}
                else:
                    out[adapter_id] = set()
                declared_keys.add(adapter_id)
    return out


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsentEnvelopeReport:
    """Outcome of validating one adapter's observed scope."""

    adapter_id: str
    declared_scope: frozenset[str]
    observed_scope: frozenset[str]
    out_of_scope: frozenset[str]
    in_scope: frozenset[str]
    missing_declaration: bool
    """True when the adapter has no ``scope:`` key in any loaded registry.

    Distinct from ``declared_scope=frozenset()``, which means the adapter
    declared an explicit empty envelope (also a finding, but for different
    remediation: review the declaration vs. populate it).
    """

    @property
    def has_violation(self) -> bool:
        return bool(self.out_of_scope) or self.missing_declaration

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "declared_scope": sorted(self.declared_scope),
            "observed_scope": sorted(self.observed_scope),
            "out_of_scope": sorted(self.out_of_scope),
            "in_scope": sorted(self.in_scope),
            "missing_declaration": self.missing_declaration,
            "has_violation": self.has_violation,
        }

    def as_drift_state(
        self,
        *,
        provenance: ProvenanceRecord,
        policy_ref: str = "consent-envelope",
        drift_id: Optional[str] = None,
    ) -> Optional[DriftState]:
        """Project the report into a :class:`DriftState` when there's a
        violation; ``None`` when the adapter stayed within its envelope.

        The DriftState carries ``drift_class="DRIFT-AUTHZ"``, severity
        "unauthorized" (the substrate's strongest classification), and a
        delta dict listing the offending object types so OSCAL emitters
        can surface a precise reason on the finding.
        """
        if not self.has_violation:
            return None
        expected_state = {"scope": sorted(self.declared_scope)}
        actual_state = {"scope": sorted(self.observed_scope)}
        delta = {
            "added": sorted(self.out_of_scope),
            "removed": [],
            "changed": [],
            "consent_envelope_reasons": (
                ["adapter has no scope: declaration in canon registry"]
                if self.missing_declaration
                else [f"adapter accessed '{t}' which is outside its declared scope" for t in sorted(self.out_of_scope)]
            ),
        }
        return DriftState(
            id=drift_id or f"drift-authz:consent-envelope:{self.adapter_id}",
            resource_id=f"adapter:{self.adapter_id}",
            policy_ref=policy_ref,
            expected_hash=canonical_hash(expected_state),
            actual_hash=canonical_hash(actual_state),
            drift_detected=True,
            classification="unauthorized",
            delta=delta,
            provenance=provenance,
            drift_class=DRIFT_AUTHZ,
        )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


@dataclass
class ConsentEnvelopeValidator:
    """Validates observed adapter scopes against canon-registry declarations.

    Construction is cheap: the validator just stores a precomputed
    ``{adapter_id: scope_set}`` mapping. Pre-load envelopes once via
    :func:`load_adapter_envelopes` and reuse the validator across many
    adapter dispatches.
    """

    envelopes: Mapping[str, set[str]] = field(default_factory=dict)

    def validate(
        self,
        adapter_id: str,
        observed_scope: Iterable[str],
    ) -> ConsentEnvelopeReport:
        """Compute a report for one (adapter, observed-scope) pair.

        ``observed_scope`` is the set of canonical object-type strings the
        adapter actually touched on this dispatch. Empty set is allowed
        (the adapter dispatched but accessed nothing observable).
        """
        observed = frozenset(s for s in (str(x).strip() for x in observed_scope) if s)
        missing = adapter_id not in self.envelopes
        declared_set = self.envelopes.get(adapter_id, set())
        declared = frozenset(declared_set)
        out_of = observed - declared
        in_scope = observed & declared
        return ConsentEnvelopeReport(
            adapter_id=adapter_id,
            declared_scope=declared,
            observed_scope=observed,
            out_of_scope=out_of,
            in_scope=in_scope,
            missing_declaration=missing,
        )

    def validate_many(
        self,
        observations: Mapping[str, Iterable[str]],
    ) -> list[ConsentEnvelopeReport]:
        """Validate many adapters at once. Order: input iteration order."""
        return [self.validate(aid, scope) for aid, scope in observations.items()]


# ---------------------------------------------------------------------------
# Scheduler-run helper
# ---------------------------------------------------------------------------


_OBSERVED_SCOPE_KEYS = (
    "accessed_scope",
    "observed_scope",
    "scope",
)


def observed_scope_for_run(run_dir: Path | str) -> dict[str, list[str]]:
    """Walk a UIAO_100 scheduler-run directory and extract per-adapter
    observed scope.

    Looks under ``schedrun-*/adapters/<id>/evidence.json`` for any of:

        normalized_data.accessed_scope
        normalized_data.observed_scope
        normalized_data.scope
        raw_data.accessed_scope (fallback)

    Adapters that emit no scope hint contribute an empty list — the
    validator treats that as "no observable access" (no violation).

    Adapters can populate this convention by writing the list of object
    types they touched into ``normalized_data.accessed_scope`` in their
    evidence payload. Existing adapters that don't yet emit it produce
    no false positives — empty observed scope is in-scope by definition.
    """
    import json as _json

    root = Path(run_dir)
    out: dict[str, list[str]] = {}
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
        scope: list[str] = []
        for container_key in ("normalized_data", "raw_data"):
            container = payload.get(container_key) or {}
            if not isinstance(container, dict):
                continue
            for key in _OBSERVED_SCOPE_KEYS:
                value = container.get(key)
                if isinstance(value, list):
                    scope = [str(v).strip() for v in value if str(v).strip()]
                    break
            if scope:
                break
        out[adapter_dir.name] = scope
    return out


__all__ = [
    "DRIFT_AUTHZ",
    "ConsentEnvelopeReport",
    "ConsentEnvelopeValidator",
    "load_adapter_envelopes",
    "observed_scope_for_run",
]
