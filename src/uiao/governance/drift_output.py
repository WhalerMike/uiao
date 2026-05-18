"""
src/uiao/governance/drift_output.py
-----------------------------------
Canonical `DriftRecord` shape per UIAO_179.

Unifies the per-adapter `DriftReport` (src/uiao/adapters/database_base.py)
with the system-level taxonomy defined by ADR-012 (`DRIFT-SCHEMA`,
`DRIFT-SEMANTIC`, `DRIFT-PROVENANCE`, `DRIFT-AUTHZ`, `DRIFT-IDENTITY`,
`DRIFT-BOUNDARY`) and the object-level facet labels introduced by
UIAO_177 (tag governance) and UIAO_178 (provisioning order).

The two axes are independent:
  - `drift_class`  -- system-level taxonomy (ADR-012)
  - `object_facet` -- object surface grouping for operator UX
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

DriftClass = Literal[
    "DRIFT-SCHEMA",
    "DRIFT-SEMANTIC",
    "DRIFT-PROVENANCE",
    "DRIFT-AUTHZ",
    "DRIFT-IDENTITY",
    "DRIFT-BOUNDARY",
]

ObjectFacet = Literal[
    "identity",
    "access",
    "resource",
    "tag",
    "device",
    "boundary",
    "semantic",
]

Severity = Literal["low", "medium", "high", "critical"]

# Typical mapping from object_facet -> drift_class, per UIAO_179 §Facet
# mapping. Used by `facet_to_drift_class()`; emitters MAY override.
FACET_DEFAULT_CLASS: Dict[ObjectFacet, DriftClass] = {
    "identity": "DRIFT-IDENTITY",
    "access": "DRIFT-AUTHZ",
    "resource": "DRIFT-SCHEMA",
    "tag": "DRIFT-SCHEMA",
    "device": "DRIFT-IDENTITY",
    "boundary": "DRIFT-BOUNDARY",
    "semantic": "DRIFT-SEMANTIC",
}


def facet_to_drift_class(facet: ObjectFacet) -> DriftClass:
    """Return the canonical default `drift_class` for an `object_facet`."""
    return FACET_DEFAULT_CLASS[facet]


@dataclass
class DriftRecord:
    """Canonical drift record (UIAO_179).

    Every adapter, classifier, and orchestrator that detects drift
    SHOULD emit instances of this dataclass. Consumers (Evidence Graph,
    CLI, REST API) MAY assume the field set defined here.
    """

    object_id: str
    drift_class: DriftClass
    object_facet: ObjectFacet
    expected_value: Any
    actual_value: Any
    severity: Severity
    recommended_action: str
    source_adapter: str
    first_observed: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_observed: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "drift_class": self.drift_class,
            "object_facet": self.object_facet,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "severity": self.severity,
            "recommended_action": self.recommended_action,
            "source_adapter": self.source_adapter,
            "first_observed": self.first_observed.isoformat(),
            "last_observed": self.last_observed.isoformat(),
            "correlation_id": self.correlation_id,
        }


def drift_record_from_report(
    report: Any,
    *,
    object_id: str,
    object_facet: ObjectFacet,
    source_adapter: str,
    expected_value: Any = None,
    actual_value: Any = None,
    recommended_action: str = "review",
    correlation_id: Optional[str] = None,
) -> DriftRecord:
    """Convert a legacy `DriftReport` (database_base.py) to a `DriftRecord`.

    `DriftReport` carries `drift_type`, `severity`, `details`, and
    timestamps; this helper maps those onto the canonical UIAO_179
    shape. The classifier-axis `drift_class` is derived from
    `object_facet` if `report.drift_type` is not already a canonical
    DRIFT-* string.
    """
    raw_type = getattr(report, "drift_type", None) or ""
    if raw_type.startswith("DRIFT-"):
        drift_class: DriftClass = raw_type  # type: ignore[assignment]
    else:
        drift_class = facet_to_drift_class(object_facet)

    severity = (getattr(report, "severity", "") or "low").lower()
    if severity not in ("low", "medium", "high", "critical"):
        severity = "medium"

    return DriftRecord(
        object_id=object_id,
        drift_class=drift_class,
        object_facet=object_facet,
        expected_value=expected_value,
        actual_value=actual_value if actual_value is not None else getattr(report, "details", None),
        severity=severity,  # type: ignore[arg-type]
        recommended_action=getattr(report, "remediation", None) or recommended_action,
        source_adapter=source_adapter,
        first_observed=getattr(report, "first_observed", datetime.now(timezone.utc)),
        last_observed=getattr(report, "last_observed", datetime.now(timezone.utc)),
        correlation_id=correlation_id,
    )


def records_to_dicts(records: List[DriftRecord]) -> List[Dict[str, Any]]:
    """Serialize a list of records for transport (Evidence Graph, REST)."""
    return [r.to_dict() for r in records]
