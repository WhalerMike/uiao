"""Canonical DriftFinding — promotes `16_DriftDetectionStandard.qmd` §4
remediation contract into typed inline fields per ADR-073.

Subsumes two of the substrate's three previous DriftFinding classes
(substrate walker, runtime sink). The OrgTree engine's DriftFinding
stays peer per ADR-073 §4; Phase 5 unifies all three.

This file is a DRAFT skeleton. Promotion to
`src/uiao/models/drift_finding.py` happens when ADR-073 is ACCEPTED.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace, asdict
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Valid drift_class values — matches `adr-012-canonical-drift-taxonomy`
# plus the GCC-Moderate boundary class from ADR-033.
VALID_DRIFT_CLASSES: frozenset[str] = frozenset({
    "DRIFT-SCHEMA",
    "DRIFT-SEMANTIC",
    "DRIFT-PROVENANCE",
    "DRIFT-AUTHZ",
    "DRIFT-IDENTITY",
    "DRIFT-BOUNDARY",   # ADR-033 — kept as a valid value even though Phase 2 doesn't emit it
})

# Valid severity values — matches `16_DriftDetectionStandard.qmd` §3.
VALID_SEVERITIES: frozenset[str] = frozenset({"P1", "P2", "P3", "P4"})

# Valid remediation_action values — per `16_DriftDetectionStandard.qmd` §4.
VALID_REMEDIATION_ACTIONS: frozenset[str] = frozenset({"halt", "fix", "flag", "log"})

# Valid subkind values — distinguishes hygiene findings (substrate walker)
# from runtime findings (provenance sink). Per ADR-070 §3.
VALID_SUBKINDS: frozenset[str] = frozenset({"hygiene", "runtime", "retired-slug"})

# Valid escalation paths — defaults; agencies may override per deployment.
DEFAULT_ESCALATION_PATHS: dict[str, str] = {
    "DRIFT-PROVENANCE": "CISO",
    "DRIFT-AUTHZ": "CISO",
    "DRIFT-IDENTITY": "Architecture Lead",
    "DRIFT-SCHEMA": "Architecture Lead",
    "DRIFT-SEMANTIC": "Canon Steward",
    "DRIFT-BOUNDARY": "Architecture Lead",
}


# ---------------------------------------------------------------------------
# DriftFinding
# ---------------------------------------------------------------------------


@dataclass
class DriftFinding:
    """One drift finding plus its §4 remediation contract.

    The first five fields preserve the substrate walker's existing
    contract — callers that build `DriftFinding(drift_class=..., severity=...,
    path=..., detail=...)` continue to work unchanged. The new §4
    fields default to empty/unset and are populated by the
    `RemediationRouter` when the finding is routed.

    Two emission paths populate the `subkind` differently:

    - `subkind="hygiene"` — emitted by the substrate walker against
      canon registries at PR time. Findings here are caught before
      any code runs against them.
    - `subkind="runtime"` — emitted by the provenance sink at adapter
      emit time. Findings here describe live drift, not registry
      hygiene.

    Both kinds use the same DriftFinding class, the same drift_class
    codes, the same severity model, and the same remediation contract.
    The taxonomy is one; the emission surface is two.
    """

    # --- Core finding fields (preserved from substrate walker) ---
    drift_class: str
    severity: str
    path: str
    detail: str
    subkind: Optional[str] = None

    # --- §4 remediation contract (NEW in Phase 3) ---
    detection_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    detected_by: str = ""
    auto_remediated: bool = False
    remediation_action: str = ""
    remediation_timestamp: Optional[str] = None
    remediation_evidence: Optional[str] = None
    escalation_path: Optional[str] = None

    def __post_init__(self) -> None:
        # Cheap structural validation — keeps malformed findings out of
        # the event log without forcing pydantic on what is otherwise a
        # plain dataclass.
        if self.drift_class not in VALID_DRIFT_CLASSES:
            raise ValueError(
                f"drift_class {self.drift_class!r} is not in the canonical taxonomy "
                f"(adr-012); expected one of {sorted(VALID_DRIFT_CLASSES)}"
            )
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"severity {self.severity!r} is not in the canonical severity model "
                f"(16_DriftDetectionStandard §3); expected one of {sorted(VALID_SEVERITIES)}"
            )
        if self.subkind is not None and self.subkind not in VALID_SUBKINDS:
            raise ValueError(
                f"subkind {self.subkind!r} is not in the canonical set; expected one of "
                f"{sorted(VALID_SUBKINDS)} or None"
            )
        if self.remediation_action and self.remediation_action not in VALID_REMEDIATION_ACTIONS:
            raise ValueError(
                f"remediation_action {self.remediation_action!r} is not canonical "
                f"(16_DriftDetectionStandard §4); expected one of {sorted(VALID_REMEDIATION_ACTIONS)}"
            )

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def with_routing(
        self,
        *,
        action: str,
        escalation: str,
        detected_by: str,
    ) -> "DriftFinding":
        """Return a new finding with routing metadata populated.

        Called by the `RemediationRouter` after rule-table lookup.
        Does not set `remediation_timestamp` / `remediation_evidence`
        / `auto_remediated` — those are populated by the handler if
        and when remediation completes.
        """
        return replace(
            self,
            remediation_action=action,
            escalation_path=escalation,
            detected_by=detected_by or self.detected_by,
        )

    def with_remediation_evidence(
        self,
        *,
        evidence: str,
        auto_remediated: bool,
    ) -> "DriftFinding":
        """Return a new finding marking remediation as complete.

        `evidence` is a commit_sha (when the fix handler runs) or a
        POA&M UUID (when the flag handler runs). `auto_remediated` is
        True iff the fix handler succeeded; flag/log handlers always
        set False.
        """
        return replace(
            self,
            auto_remediated=auto_remediated,
            remediation_timestamp=datetime.now(timezone.utc).isoformat(),
            remediation_evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Flat JSON-friendly serialization.

        Compatible with the substrate walker's existing report shape;
        callers reading older walker reports see the same keys plus
        the new §4 contract keys (defaulted on legacy findings).
        """
        return asdict(self)


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def hygiene_finding(
    *,
    drift_class: str,
    severity: str,
    path: str,
    detail: str,
) -> DriftFinding:
    """Construct a substrate-walker-style hygiene finding.

    Equivalent to `DriftFinding(..., subkind="hygiene")`. Provided as a
    named constructor so the walker call sites don't carry the magic
    string and so a future refactor can swap the subkind without
    touching every call.
    """
    return DriftFinding(
        drift_class=drift_class,
        severity=severity,
        path=path,
        detail=detail,
        subkind="hygiene",
    )


def runtime_finding(
    *,
    drift_class: str,
    severity: str,
    path: str,
    detail: str,
    detected_by: str,
) -> DriftFinding:
    """Construct a runtime-sink-style finding from an adapter emission.

    Pre-populates `detected_by` because the runtime sink always knows
    which adapter emitted the envelope that produced the finding.
    """
    return DriftFinding(
        drift_class=drift_class,
        severity=severity,
        path=path,
        detail=detail,
        subkind="runtime",
        detected_by=detected_by,
    )
