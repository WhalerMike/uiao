"""Drift Detection Engine — Model C (ADR-084 §C5, §C9 Phase 5 #6).

Per-facet orchestrator over the 4 Phase 5 adapters
(:py:mod:`uiao.adapters.entra_dynamic_groups`,
:py:mod:`uiao.adapters.entra_admin_units`,
:py:mod:`uiao.adapters.entra_policy_targeting`,
:py:mod:`uiao.adapters.entra_device_orgpath`).

Implements the six-phase loop from UIAO_163 v2.0 — Snapshot → Compare
→ Classify → Alert → Remediate → Verify — with per-facet operations
as the unit of work (ADR-084 §C2). The engine never talks to Graph or
ARM directly; it delegates planning to each adapter and dispatches
remediation through each adapter's ``apply()``.

Design invariants (per ADR-084 §C5):

* Governance-review op verbs (each adapter's ``governance_review_ops``
  set) are **never** auto-remediated, even when ``dry_run=False``.
* ``halt_on_critical`` — if any per-facet finding at or above the
  configured halt severity fires during Classify, Remediate is
  skipped even when ``dry_run=False`` (stop-the-line for codebook
  integrity / governance issues).
* ``dry_run=True`` is the default everywhere. Promotion to write-mode
  is an operator decision per scan.

Per-facet drift classification per UIAO_163 v2.0 §"The Five Drift
Categories":

* **Format** (P1) — typed-facet ``value_pattern`` violation; never auto-fixed
* **Value** (P2) — enumerated-facet value not in ``enumeration``;
  optionally auto-fixed per facet policy
* **Slot** (P1) — codebook integrity issue (cross-facet slot collision);
  never auto-fixed
* **Orphan** (P3) — enumeration value with zero matching principals; flag only
* **Phantom** (P3) — principal carries a deprecated value; optionally
  auto-reassigned per facet policy when ``replaced_by`` is set
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from uiao.modernization.orgtree.codebook import Codebook, Facet
from uiao.modernization.orgtree.drift_engine_config import (
    DriftEngineConfig,
    default_drift_engine_config,
)
from uiao.modernization.orgtree.types import (
    ApplyResult,
    FacetOperation,
    PrincipalSnapshot,
    Snapshot,
)

# ---------------------------------------------------------------------------
# DriftFinding — per-facet payload (UIAO_163 v2.0)
# ---------------------------------------------------------------------------


# Category → (drift_class, severity, default_auto_remediate)
_CATEGORY_META: Mapping[str, tuple[str, str, bool]] = {
    "Format": ("DRIFT-SCHEMA", "P1", False),
    "Value": ("DRIFT-SEMANTIC", "P2", False),  # config can opt-in to auto
    "Slot": ("DRIFT-SCHEMA::slot-occupied", "P1", False),
    "Orphan": ("DRIFT-SEMANTIC::orphan", "P3", False),
    "Phantom": ("DRIFT-SEMANTIC::phantom", "P3", False),  # config can opt-in
}


@dataclass(frozen=True)
class DriftFinding:
    """One per-facet drift finding emitted by Compare/Classify."""

    phase: str
    op: str
    target: str
    facet: str
    attribute: str
    observed_value: str | None
    reason: str
    drift_class: str
    drift_category: str
    severity: str
    auto_remediate: bool
    snapshot_id: str
    timestamp: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Adapter Protocol — the engine's view of every Phase 5 adapter
# ---------------------------------------------------------------------------


@runtime_checkable
class Adapter(Protocol):
    """Structural protocol every Phase 5 adapter satisfies.

    Used by the engine to orchestrate without coupling to any
    individual adapter class. Each adapter exposes ``plan(snapshot) →
    operations``, ``apply(operations, dry_run) → ApplyResult``, and
    ``governance_review_ops`` (verbs the engine must never auto-fire).
    """

    @property
    def governance_review_ops(self) -> frozenset[str]: ...

    def plan(self, observed: Iterable) -> list[FacetOperation]: ...

    def apply(
        self,
        operations: Iterable[FacetOperation],
        *,
        dry_run: bool = True,
    ) -> ApplyResult: ...


# ---------------------------------------------------------------------------
# DriftScanReport — full output of one DriftEngine.run() invocation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriftScanReport:
    """Result of one full Snapshot→...→Verify pass."""

    snapshot_id: str
    generated_at: str
    dry_run: bool
    halted: bool
    findings: tuple[DriftFinding, ...]
    apply_results: Mapping[str, ApplyResult]  # keyed by adapter name

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def severity_counts(self) -> Mapping[str, int]:
        from collections import Counter

        return dict(Counter(f.severity for f in self.findings))

    def findings_by_category(self, category: str) -> tuple[DriftFinding, ...]:
        return tuple(f for f in self.findings if f.drift_category == category)


# ---------------------------------------------------------------------------
# DriftEngine — the orchestrator
# ---------------------------------------------------------------------------


class DriftEngine:
    """Per-facet drift orchestrator over the Phase 5 adapters.

    Construct with a :py:class:`Codebook`, a mapping of adapter name →
    adapter, and an optional :py:class:`DriftEngineConfig`. Call
    :py:meth:`run` with a :py:class:`Snapshot` to execute one full
    Snapshot→Verify pass.
    """

    def __init__(
        self,
        codebook: Codebook,
        adapters: Mapping[str, Adapter],
        config: DriftEngineConfig | None = None,
    ) -> None:
        self.codebook = codebook
        self.adapters = dict(adapters)
        self.config = config or default_drift_engine_config()

    def run(
        self,
        snapshot: Snapshot,
        *,
        dry_run: bool | None = None,
    ) -> DriftScanReport:
        """Execute one full drift scan.

        Parameters
        ----------
        snapshot
            Pre-fetched tenant state (offline-testable per ADR-084 §C5).
        dry_run
            Optional per-call override of ``config.dry_run``. When
            ``None`` (default), uses the engine config.
        """
        effective_dry_run = self.config.dry_run if dry_run is None else dry_run
        snapshot_id = f"snap-{snapshot.generated_at}"

        # Compare + Classify per-facet findings (over principals).
        findings = list(self._compare_and_classify(snapshot, snapshot_id))

        # Slot Drift — codebook integrity (cross-facet slot collision).
        # In v2 the loader catches this at load time, but if a runtime
        # mutation introduces a collision after load, the engine emits
        # it here.
        findings.extend(self._classify_slot_drift(snapshot_id))

        # Orphan Drift — per-facet enumeration value with zero matching principals.
        findings.extend(self._classify_orphan_drift(snapshot, snapshot_id))

        # Halt-on-critical check.
        halted = self.config.critical_fires([f.severity for f in findings])

        # Remediate per adapter (plan + optionally apply).
        apply_results: dict[str, ApplyResult] = {}
        if not halted:
            for name, adapter in self.adapters.items():
                ops = self._plan_for_adapter(adapter, snapshot)
                # Per-adapter dry_run: when engine dry_run=False but
                # halt fired, ALL writes are suppressed (handled above
                # via halted skip).
                apply_results[name] = adapter.apply(ops, dry_run=effective_dry_run)
        else:
            # Halt: still record what WOULD have been planned, but apply
            # nothing.
            for name, adapter in self.adapters.items():
                ops = self._plan_for_adapter(adapter, snapshot)
                apply_results[name] = ApplyResult.dry(ops)

        return DriftScanReport(
            snapshot_id=snapshot_id,
            generated_at=snapshot.generated_at,
            dry_run=effective_dry_run,
            halted=halted,
            findings=tuple(findings),
            apply_results=apply_results,
        )

    # ------------------------------------------------------------------
    # Compare + Classify
    # ------------------------------------------------------------------
    def _compare_and_classify(
        self,
        snapshot: Snapshot,
        snapshot_id: str,
    ) -> Iterable[DriftFinding]:
        for principal in snapshot.principals:
            yield from self._classify_principal(principal, snapshot_id)

    def _classify_principal(
        self,
        principal: PrincipalSnapshot,
        snapshot_id: str,
    ) -> Iterable[DriftFinding]:
        ts = _now_iso()
        for facet_name, facet in self.codebook.facets.items():
            value = principal.attributes.get(facet.attribute, "")
            if facet.kind == "reserved":
                # Reserved facets must be null/empty.
                if value:
                    yield self._finding(
                        principal=principal,
                        facet=facet,
                        observed_value=value,
                        category="Value",
                        reason=(
                            f"{facet.attribute} has value '{value}' on a "
                            f"reserved facet '{facet_name}'. Promote the "
                            "facet via governed PR before populating."
                        ),
                        snapshot_id=snapshot_id,
                        timestamp=ts,
                    )
                continue

            if facet.kind == "typed":
                # Format Drift: typed-facet pattern violation.
                if value == "" and facet.allow_empty:
                    continue
                if not facet.is_active(value):
                    yield self._finding(
                        principal=principal,
                        facet=facet,
                        observed_value=value,
                        category="Format",
                        reason=(
                            f"{facet.attribute} '{value}' fails {facet_name} value_pattern '{facet.value_pattern}'."
                        ),
                        snapshot_id=snapshot_id,
                        timestamp=ts,
                    )
                continue

            # Enumerated facet.
            if facet.is_active(value):
                continue
            if facet.is_deprecated(value):
                replacement = facet.replacement_for(value)
                yield self._finding(
                    principal=principal,
                    facet=facet,
                    observed_value=value,
                    category="Phantom",
                    reason=(
                        f"{facet.attribute} '{value}' is a deprecated "
                        f"value in facet '{facet_name}'. "
                        f"Replacement: '{replacement}'."
                    ),
                    snapshot_id=snapshot_id,
                    timestamp=ts,
                    metadata={"replaced_by": replacement},
                )
                continue
            # Unknown value → Value Drift.
            yield self._finding(
                principal=principal,
                facet=facet,
                observed_value=value,
                category="Value",
                reason=(f"{facet.attribute} '{value}' not in {facet_name} enumeration."),
                snapshot_id=snapshot_id,
                timestamp=ts,
            )

    def _classify_orphan_drift(
        self,
        snapshot: Snapshot,
        snapshot_id: str,
    ) -> Iterable[DriftFinding]:
        ts = _now_iso()
        for facet_name, facet in self.codebook.facets.items():
            if facet.kind != "enumerated":
                continue
            for value in facet.enumeration:
                if not any(p.attributes.get(facet.attribute) == value for p in snapshot.principals):
                    drift_class, severity, _ = _CATEGORY_META["Orphan"]
                    yield DriftFinding(
                        phase="orphan-scan",
                        op="orphan-detect",
                        target=f"facet-value:{facet_name}:{value}",
                        facet=facet_name,
                        attribute=facet.attribute,
                        observed_value=value,
                        reason=(f"Enumeration value '{value}' in facet '{facet_name}' has zero matching principals."),
                        drift_class=drift_class,
                        drift_category="Orphan",
                        severity=severity,
                        auto_remediate=False,
                        snapshot_id=snapshot_id,
                        timestamp=ts,
                    )

    def _classify_slot_drift(self, snapshot_id: str) -> Iterable[DriftFinding]:
        """Detect cross-facet slot collisions in the loaded codebook."""
        ts = _now_iso()
        seen: dict[str, str] = {}
        drift_class, severity, _ = _CATEGORY_META["Slot"]
        for facet_name, facet in self.codebook.facets.items():
            if facet.attribute in seen:
                yield DriftFinding(
                    phase="codebook-integrity",
                    op="slot-collision",
                    target=f"slot:{facet.attribute}",
                    facet=facet_name,
                    attribute=facet.attribute,
                    observed_value=None,
                    reason=(
                        f"Facets '{seen[facet.attribute]}' and "
                        f"'{facet_name}' both bind to '{facet.attribute}'. "
                        "Each extensionAttribute slot must be claimed by "
                        "at most one facet."
                    ),
                    drift_class=drift_class,
                    drift_category="Slot",
                    severity=severity,
                    auto_remediate=False,
                    snapshot_id=snapshot_id,
                    timestamp=ts,
                )
                continue
            seen[facet.attribute] = facet_name

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _finding(
        self,
        *,
        principal: PrincipalSnapshot,
        facet: Facet,
        observed_value: str,
        category: str,
        reason: str,
        snapshot_id: str,
        timestamp: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> DriftFinding:
        drift_class, severity, _ = _CATEGORY_META[category]
        # Per-facet remediation policy may opt-in to auto-fix for Value/Phantom.
        policy = self.config.policy_for(facet.name)
        auto = False
        if category == "Value" and policy.auto_remediate_value_drift:
            auto = True
        if category == "Phantom" and policy.auto_remediate_phantom_drift:
            auto = True
        return DriftFinding(
            phase="facet-validate",
            op="facet-value-validate",
            target=f"{principal.principal_type}|{principal.principal_id}",
            facet=facet.name,
            attribute=facet.attribute,
            observed_value=observed_value,
            reason=reason,
            drift_class=drift_class,
            drift_category=category,
            severity=severity,
            auto_remediate=auto,
            snapshot_id=snapshot_id,
            timestamp=timestamp,
            metadata=dict(metadata or {}),
        )

    def _plan_for_adapter(self, adapter: Adapter, snapshot: Snapshot) -> list[FacetOperation]:
        """Dispatch the right portion of the snapshot to each adapter's plan().

        The engine matches adapter class names to snapshot slices (groups
        → dynamic_groups adapter, admin_units → admin_units adapter,
        etc.). Adapters that don't recognize the input safely return [].
        """
        # Each adapter consumes a different slice; we try the most likely
        # one for each adapter type by attribute introspection.
        adapter_name = type(adapter).__name__
        if "DynamicGroup" in adapter_name:
            return list(adapter.plan(snapshot.groups))
        if "AdminUnit" in adapter_name:
            return list(adapter.plan(snapshot.admin_units))
        if "PolicyTarget" in adapter_name:
            return list(adapter.plan(snapshot.policy_targets))
        if "DeviceOrgPath" in adapter_name:
            # Device adapter consumes DeviceFacetAssignment, not snapshots.
            # The engine doesn't synthesise assignments from device-plane
            # snapshots in v1; operators feed assignments directly.
            return []
        # Unknown adapter — return [] rather than crash.
        return []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
