"""Reporting-egress actuator (ADR-128).

Gated outward submission of already-generated ConMon evidence to external
federal destinations (CDM, CyberScope, FedRAMP repository, CISA SBOM inbox,
CISA incident portal).

Invariants (see ADR-128):
    * Dry-run is the default; nothing transmits without an explicit live flag.
    * Every live submission is L3-gated — it requires a human ``Approval`` token.
    * No autonomous (L4) path: there is no code path that transmits without both
      ``live=True`` and a valid ``Approval``.
    * Drivers ship ``configured=False``; a live+approved submission against an
      unconfigured driver is *blocked*, never simulated as sent.

The public surface is :func:`uiao.reporting_egress.engine.submit`.
"""

from __future__ import annotations

from uiao.reporting_egress.drivers import EgressDriver, get_driver, list_destinations
from uiao.reporting_egress.engine import submit
from uiao.reporting_egress.models import (
    Approval,
    Destination,
    Disposition,
    Submission,
    SubmissionResult,
)

__all__ = [
    "Approval",
    "Destination",
    "Disposition",
    "EgressDriver",
    "Submission",
    "SubmissionResult",
    "get_driver",
    "list_destinations",
    "submit",
]
