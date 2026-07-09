"""Data models for the reporting-egress actuator (ADR-128)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Destination(str, Enum):
    """External federal ConMon reporting destinations.

    ``CLAW`` telemetry is deliberately absent — raw telemetry stays on the
    native cloud pipe (ADR-128 §5 / ADR-066 lane discipline).
    """

    CDM = "cdm"
    CYBERSCOPE = "cyberscope"
    FEDRAMP_REPO = "fedramp-repo"
    CISA_SBOM = "cisa-sbom"
    CISA_INCIDENT = "cisa-incident"


class Disposition(str, Enum):
    """Outcome of a submission attempt."""

    PLANNED = "planned"  # dry-run: validated, not transmitted
    BLOCKED = "blocked"  # gate/config failure: not transmitted
    SUBMITTED = "submitted"  # transmitted to a configured, live endpoint


@dataclass(frozen=True)
class Approval:
    """An L3 human-approval token for a single live submission.

    Presence of a valid ``Approval`` is the *only* thing that lets the engine
    transmit outward (and only then against a configured driver). It is never
    minted autonomously — the CLI/API requires a named human approver.
    """

    approver: str
    approved_at: str  # ISO-8601 timestamp, supplied by the caller
    operation: str  # e.g. "submit:cisa-sbom"

    def is_valid(self) -> bool:
        return bool(self.approver.strip()) and bool(self.approved_at.strip())


@dataclass(frozen=True)
class Submission:
    """A request to submit one artifact to one destination."""

    destination: Destination
    artifact_path: Path
    artifact_type: str  # e.g. "oscal-ar", "cyclonedx-sbom", "openvex", "fisma-metrics"
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SubmissionResult:
    """The record of a submission attempt — always returned, never raised."""

    destination: Destination
    disposition: Disposition
    reason: str
    artifact_path: Path
    problems: tuple[str, ...] = ()
    receipt: dict | None = None
    approver: str | None = None

    @property
    def transmitted(self) -> bool:
        return self.disposition is Disposition.SUBMITTED
