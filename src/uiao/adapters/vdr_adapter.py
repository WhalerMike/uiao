"""Vulnerability Detection and Response (VDR) Balance Improvement Release adapter.

STATUS: RESERVED — VDR BIR not yet published by FedRAMP.

This module is a forward-looking placeholder for the Pathway-1
(modernized) adapter that will implement the VDR Balance Improvement
Release once FedRAMP publishes it. FedRAMP Notice 0009 sets mandatory
VDR adoption by **2027-06-01**. Until the BIR publishes, callers must
use the Pathway-2 traditional `vuln-scan` adapter per ADR-043 D1 / D2.

The module exists now (rather than later) so that
:mod:`scripts.conmon.migration_readiness` can observe the `status:
reserved` state in the adapter registry and fire a 90-day pre-deadline
readiness alert — closing the enforcement-clock blind spot flagged in
`docs/docs/uiao-rfc-0026-roadmap.md` E8.

Canon references:
    - ADR-043 D1 / D2 / N2 — pathway posture + unpublished-BIR risk
    - UIAO_132 §2.4 / §3.4 — Pathway-1 migration commitments
    - `src/uiao/canon/adapter-registry.yaml` id: vdr-bir

Upstream references:
    - https://github.com/FedRAMP/community/discussions/130 (RFC-0026)
    - https://www.fedramp.gov/20x/notice-0009/                 (Notice 0009)
"""

from __future__ import annotations

__all__ = [
    "ADAPTER_ID",
    "STATUS",
    "MANDATORY_ADOPTION_DATE",
    "READINESS_LEAD_DAYS",
    "VdrAdapterNotYetAvailable",
    "VdrAdapter",
]

# -----------------------------------------------------------------------
# Module-level constants — consumed by the migration-readiness check.
# -----------------------------------------------------------------------

ADAPTER_ID: str = "vdr-bir"
STATUS: str = "reserved"

# FedRAMP Notice 0009 mandatory adoption date. Promoted to the adapter
# registry `mandatory-by` field so that
# scripts/conmon/migration_readiness.py can raise a 90-day alert.
MANDATORY_ADOPTION_DATE: str = "2027-06-01"

# How many days before MANDATORY_ADOPTION_DATE the readiness check
# should start firing issues if status is still "reserved".
READINESS_LEAD_DAYS: int = 90


class VdrAdapterNotYetAvailable(NotImplementedError):
    """Raised on any attempt to instantiate the VDR adapter before publication.

    The VDR Balance Improvement Release has not been published by
    FedRAMP as of the pin date recorded in
    ``src/uiao/canon/adapter-registry.yaml`` (id: ``vdr-bir``).
    """


class VdrAdapter:
    """VDR BIR conformance adapter — reserved stub.

    Any attempt to instantiate raises :class:`VdrAdapterNotYetAvailable`
    so misconfigured pipelines fail fast rather than silently running
    against an absent implementation. The class exists only to make the
    status surface introspectable via
    :mod:`scripts.conmon.migration_readiness`.
    """

    ADAPTER_ID: str = ADAPTER_ID
    STATUS: str = STATUS
    MANDATORY_ADOPTION_DATE: str = MANDATORY_ADOPTION_DATE

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise VdrAdapterNotYetAvailable(
            "Vulnerability Detection and Response (VDR) Balance Improvement "
            "Release has not been published by FedRAMP. "
            f"Mandatory adoption per Notice 0009: {MANDATORY_ADOPTION_DATE}. "
            "Use the Pathway-2 `vuln-scan` adapter until the BIR ships; see "
            "ADR-043 D1 / D2 and docs/docs/uiao-rfc-0026-roadmap.md (E8)."
        )
