"""UIAO drift-core: plane-agnostic primitives.

Shared by OrgPath drift, addressing-plane drift, and any future plane
(LocPath, AppRef, …). Defines the Finding tuple, severity tiers,
remediation posture, the ODR telemetry event shape, and the
halt-on-critical gate.

No plane-specific logic lives here. Each plane's collector imports
this module and returns plain Finding objects; the gate and event
serialiser are called at the orchestration layer.

Canon reference: UIAO_195, ADR-108
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

SCHEMA_VERSION = "drift-core/1.0"


class Severity(str, Enum):
    P1 = "P1"  # integrity / security / auth-breaking → halts the gate
    P2 = "P2"  # binding divergence → per-policy remediation
    P3 = "P3"  # hygiene / informational


class Posture(str, Enum):
    NEVER_AUTOFIX = "never-autofix"  # governance review only
    PER_POLICY = "per-policy"  # may auto-remediate where policy allows
    INFORMATIONAL = "informational"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Finding:
    plane: str  # "addressing" | "orgpath" | "locpath" | …
    name: str  # asset the finding is about (FQDN, principal, …)
    drift_class: str  # e.g. "DRIFT-BINDING"
    severity: Severity
    posture: Posture
    intended: str  # SSOT expectation, human-readable
    observed: str  # live state, human-readable
    evidence_ref: str  # pointer to the observation that produced this
    detected_at: str = field(default_factory=_now)

    @property
    def finding_id(self) -> str:
        """Deterministic SHA-256 ID — same inputs always produce the same ID."""
        h = hashlib.sha256(
            f"{self.plane}|{self.name}|{self.drift_class}|{self.intended}|{self.observed}".encode()
        ).hexdigest()
        return f"DF-{h[:16]}"

    def to_event(self) -> dict:
        """ODR-style telemetry event. Provenance fields kept explicit so the
        event is verifiable downstream (Telemetry Integrity Standard)."""
        return {
            "schema": SCHEMA_VERSION,
            "finding_id": self.finding_id,
            "plane": self.plane,
            "drift_class": self.drift_class,
            "severity": self.severity.value,
            "posture": self.posture.value,
            "name": self.name,
            "intended": self.intended,
            "observed": self.observed,
            "evidence_ref": self.evidence_ref,
            "detected_at": self.detected_at,
            "provenance": {
                "emitter": "uiao.drift_core",
                "deterministic_id": True,
            },
        }


def gate(findings: list[Finding]) -> dict:
    """Halt-on-critical: any P1 blocks a live pass. Mirrors OrgPath drift gate."""
    p1 = [f for f in findings if f.severity is Severity.P1]
    p2 = [f for f in findings if f.severity is Severity.P2]
    p3 = [f for f in findings if f.severity is Severity.P3]
    return {
        "decision": "HALT" if p1 else "PASS",
        "counts": {"P1": len(p1), "P2": len(p2), "P3": len(p3)},
        "blocking": [f.finding_id for f in p1],
    }


def events_json(findings: list[Finding]) -> str:
    """Serialize all findings as a JSON array of ODR telemetry events."""
    return json.dumps([f.to_event() for f in findings], indent=2)
