"""Drift engine configuration — Model C (ADR-084 §C5, §C9 Phase 5 #6).

Per-facet ``auto_remediate`` flags + ``halt_on_critical`` threshold.
Mirrors the retired Model A config shape so existing consumers'
deployment manifests stay structurally familiar; the *contents* are
per-facet rather than per-phase.

Per ADR-084 §C5, governance-review categories (Slot, cross-surface
device equality) are **never** auto-remediated regardless of this
config. The config controls only the Value / Format / Phantom
categories on a per-facet basis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

# Severity ordering used for ``halt_on_critical`` (lower rank = higher severity).
_SEVERITY_RANK = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}


def _at_or_above(severity: str, threshold: str) -> bool:
    """True when ``severity`` is at or above ``threshold`` (lower rank = more severe)."""
    return _SEVERITY_RANK.get(severity, 5) <= _SEVERITY_RANK.get(threshold, 5)


@dataclass(frozen=True)
class FacetRemediationPolicy:
    """Per-facet auto-remediation knobs.

    All default to ``False`` (manual review required). Operators flip
    individually for facets whose source is trusted as authoritative
    (e.g., HR-driven enumerated facets where Value Drift can safely be
    auto-fixed by writing the HR value back).
    """

    auto_remediate_value_drift: bool = False
    auto_remediate_phantom_drift: bool = False
    # Format Drift is never auto-fixed (per UIAO_163 v2.0 §Format Drift):
    # typed-pattern failures usually indicate upstream script bugs and
    # need human investigation rather than silent reformatting.


@dataclass(frozen=True)
class DriftEngineConfig:
    """Engine-wide drift remediation config.

    Attributes
    ----------
    dry_run
        Default for ``DriftEngine.run()``; True means no writes are
        applied even when auto-remediation policies allow them.
    halt_on_critical
        Severity threshold (e.g., ``"P1"``). If any finding at or
        above this severity fires during Classify, Remediate is
        skipped even when ``dry_run=False``. Stop-the-line for
        codebook-integrity / governance issues.
    facet_policies
        Per-facet remediation knobs. Facets without an explicit entry
        default to :py:class:`FacetRemediationPolicy` (all False).
    """

    dry_run: bool = True
    halt_on_critical: str = "P1"
    facet_policies: Mapping[str, FacetRemediationPolicy] = field(default_factory=dict)

    def policy_for(self, facet_name: str) -> FacetRemediationPolicy:
        return self.facet_policies.get(facet_name, FacetRemediationPolicy())

    def critical_fires(self, severities: list[str]) -> bool:
        """True if any severity in ``severities`` is at or above ``halt_on_critical``."""
        return any(_at_or_above(s, self.halt_on_critical) for s in severities)


def default_drift_engine_config() -> DriftEngineConfig:
    """Return the safe-by-default config: dry-run, halt on any P1, no auto-remediation."""
    return DriftEngineConfig(dry_run=True, halt_on_critical="P1")
