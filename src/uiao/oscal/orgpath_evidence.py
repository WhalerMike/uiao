"""OrgPath → FedRAMP MAS scope bridge.

Derives Minimum Assessment Scope (RFC-0005) classifications from OrgPath
organisational context.  OrgPath knows *who owns what*; FedRAMP 20x needs to
know *what is in scope*.  This module connects the two surfaces.

The core question it answers: given an OrgPath unit path, which substrate
components that unit *owns or depends on* are ``in-scope`` under RFC-0005?

Design:
- OrgPath provides ``unit_path`` (e.g. ``/agency/it/cloud-services``),
  ``unit_type`` (division, bureau, team, …), and optional ``systems``
  (a list of UIAO system labels the unit operates).
- This module classifies each system against the MAS rubric from UIAO_138 §3.2
  and returns a list of ``MasScopeClassification`` records.
- No live OrgPath API call is made here; callers pass an ``OrgPathContext``
  dict (from ``uiao.adapters.entra_adapter`` or loaded from a file).

Usage::

    from uiao.oscal.orgpath_evidence import classify_orgpath_scope

    ctx = {
        "unit_path": "/agency/it/cloud-services",
        "unit_type": "team",
        "systems": ["entra-adapter", "drift-engine", "provenance-recorder"],
    }
    classifications = classify_orgpath_scope(ctx)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models.fedramp import MasScopeClassification, MasScopeValue

# ---------------------------------------------------------------------------
# MAS rubric — maps substrate system labels to their default scope value.
# Derived from UIAO_138 §3.2.
# ---------------------------------------------------------------------------

_SYSTEM_SCOPE_DEFAULTS: dict[str, tuple[MasScopeValue, str]] = {
    # Canonical baselines
    "canonical-baselines": (
        MasScopeValue.IN_SCOPE,
        "Baselines directly enforce CIA of federal information (UIAO_138 §3.2).",
    ),
    # Drift engines
    "drift-engine": (
        MasScopeValue.IN_SCOPE,
        "Drift events identify CIA-impacting deviations (UIAO_138 §3.2).",
    ),
    "drift.engine.realtime": (
        MasScopeValue.IN_SCOPE,
        "Real-time drift emitter identifies CIA-impacting deviations.",
    ),
    "drift.engine.scheduled": (
        MasScopeValue.IN_SCOPE,
        "Scheduled drift emitter identifies CIA-impacting deviations.",
    ),
    # Remediation workflows
    "enforcement-workflows": (
        MasScopeValue.IN_SCOPE,
        "Remediation workflows modify systems handling federal information (UIAO_138 §3.2).",
    ),
    "enforcement.workflows.opener": (
        MasScopeValue.IN_SCOPE,
        "Workflow opener modifies systems handling federal information.",
    ),
    "enforcement.workflows.closer": (
        MasScopeValue.IN_SCOPE,
        "Workflow closer modifies systems handling federal information.",
    ),
    # Provenance
    "provenance-recorder": (
        MasScopeValue.METADATA_OUT,
        "Records who-changed-what-when about governance actions; "
        "provenance records are metadata about operations, not federal data "
        "(RFC-0005 metadata exclusion; UIAO_138 §3.2).",
    ),
    "provenance.recorder": (
        MasScopeValue.METADATA_OUT,
        "Records governance operation metadata; does not handle federal data.",
    ),
    # Adapter registry
    "adapter-registry": (
        MasScopeValue.METADATA_OUT,
        "Catalogs adapters; does not handle the federal information adapters touch (UIAO_138 §3.2).",
    ),
    "adapters.registry.health": (
        MasScopeValue.METADATA_OUT,
        "Health observations measure substrate operations, not federal data.",
    ),
    # OSCAL generator
    "oscal-generator": (
        MasScopeValue.METADATA_OUT,
        "Emits compliance posture metadata, not underlying federal information (UIAO_138 §3.2).",
    ),
    "cato.package.aggregator": (
        MasScopeValue.METADATA_OUT,
        "Aggregates compliance posture metadata for the quarterly cATO package.",
    ),
    # Telemetry / health
    "telemetry-health": (
        MasScopeValue.METADATA_OUT,
        "Measures substrate operations, not federal data (UIAO_138 §3.2).",
    ),
    "telemetry.sentinel.health": (
        MasScopeValue.METADATA_OUT,
        "Ingestion completeness check measures operational health, not federal data.",
    ),
    # CLI surface
    "cli": (
        MasScopeValue.AGENCY_SIDE_OUT,
        "Runs on agency information systems per RFC-0005 §D (UIAO_138 §3.2).",
    ),
    "uiao-cli": (
        MasScopeValue.AGENCY_SIDE_OUT,
        "CLI runs on agency information systems per RFC-0005 §D.",
    ),
    # Entra / M365 adapters — federal data
    "entra-adapter": (
        MasScopeValue.IN_SCOPE,
        "Reads and acts on federal identity information in Entra ID (UIAO_138 §3.2).",
    ),
    "adapters.entra.ca-evaluator": (
        MasScopeValue.IN_SCOPE,
        "Evaluates Conditional Access policies against federal identity data.",
    ),
    "intune-adapter": (
        MasScopeValue.IN_SCOPE,
        "Reads device compliance data for federal endpoints.",
    ),
    "m365-adapter": (
        MasScopeValue.IN_SCOPE,
        "Reads M365 service configuration affecting federal information.",
    ),
    "scuba.conformance.reporter": (
        MasScopeValue.IN_SCOPE,
        "SCuBA conformance report evaluates federal tenant configuration.",
    ),
}

# Default for unknown systems — conservative in-scope
_DEFAULT_SCOPE = (
    MasScopeValue.IN_SCOPE,
    "Unknown system — classified in-scope by default pending explicit review (ADR-106 D2 conservative default).",
)


def classify_system(system_label: str, component_path: str = "") -> MasScopeClassification:
    """Classify a single system label against the MAS rubric.

    Args:
        system_label: Lowercase hyphen-delimited system identifier
            (e.g. ``entra-adapter``, ``drift-engine``).
        component_path: Optional path to the canon document for this component.

    Returns:
        A ``MasScopeClassification`` with justification.
    """
    scope_value, justification = _SYSTEM_SCOPE_DEFAULTS.get(system_label.lower(), _DEFAULT_SCOPE)
    return MasScopeClassification(
        component_path=component_path or f"(derived from system label '{system_label}')",
        component_id="",
        mas_scope=scope_value,
        justification=justification,
        classified_at=datetime.now(timezone.utc),
        classified_by="orgpath-evidence-bridge",
    )


def classify_orgpath_scope(ctx: dict[str, Any]) -> list[MasScopeClassification]:
    """Derive MAS scope classifications from an OrgPath unit context dict.

    Args:
        ctx: OrgPath context with at least:
            - ``unit_path`` (str) — e.g. ``/agency/it/cloud-services``
            - ``systems`` (list[str]) — substrate system labels the unit owns

    Returns:
        List of ``MasScopeClassification`` records, one per system.
    """
    systems: list[str] = ctx.get("systems", [])
    unit_path: str = ctx.get("unit_path", "(unknown)")

    if not systems:
        return []

    classifications = []
    for system in systems:
        canon_path = f"orgpath:{unit_path}/{system}"
        classification = classify_system(system, component_path=canon_path)
        classifications.append(classification)
    return classifications


def in_scope_systems(classifications: list[MasScopeClassification]) -> list[str]:
    """Return component paths for all in-scope classifications."""
    return [c.component_path for c in classifications if c.mas_scope == MasScopeValue.IN_SCOPE]


def out_of_scope_systems(classifications: list[MasScopeClassification]) -> list[str]:
    """Return component paths for all out-of-scope classifications."""
    return [c.component_path for c in classifications if c.mas_scope != MasScopeValue.IN_SCOPE]


def scope_summary(classifications: list[MasScopeClassification]) -> dict[str, Any]:
    """Return a summary dict of scope classification counts and lists."""
    return {
        "total": len(classifications),
        "in_scope": sum(1 for c in classifications if c.mas_scope == MasScopeValue.IN_SCOPE),
        "metadata_out_of_scope": sum(1 for c in classifications if c.mas_scope == MasScopeValue.METADATA_OUT),
        "agency_side_out_of_scope": sum(1 for c in classifications if c.mas_scope == MasScopeValue.AGENCY_SIDE_OUT),
        "dispute_open": sum(1 for c in classifications if c.dispute_open),
        "in_scope_paths": in_scope_systems(classifications),
        "out_of_scope_paths": out_of_scope_systems(classifications),
    }
