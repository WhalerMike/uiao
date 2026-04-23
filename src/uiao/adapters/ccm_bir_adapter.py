"""Collaborative Continuous Monitoring (CCM) Balance Improvement Release adapter.

STATUS: RESERVED — CCM BIR not yet published by FedRAMP.

This module is a forward-looking placeholder for the Pathway-1
(modernized) adapter that will implement the CCM Balance Improvement
Release once FedRAMP publishes it. FedRAMP Notice 0009 sets mandatory
CCM BIR adoption by **2027-04-01** — the earlier of the two Notice 0009
dates (VDR follows on 2027-06-01). Until the BIR publishes, callers
must use the Pathway-2 traditional cadence (monthly ConMon meeting +
OSCAL drop) per ADR-043 D1 / D3.

The module exists now (rather than later) so that
:mod:`scripts.conmon.migration_readiness` can observe the `status:
reserved` state in the adapter registry and fire a 90-day pre-deadline
readiness alert — closing the enforcement-clock blind spot flagged in
`docs/docs/uiao-rfc-0026-roadmap.md` E8.

Canon references:
    - ADR-043 D1 / D3 / N2 — pathway posture + unpublished-BIR risk
    - UIAO_132 §2.4 / §3.4 — Pathway-1 migration commitments
    - `src/uiao/canon/adapter-registry.yaml` id: ccm-bir

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
    "CcmBirAdapterNotYetAvailable",
    "CcmBirAdapter",
]

# -----------------------------------------------------------------------
# Module-level constants — consumed by the migration-readiness check.
# -----------------------------------------------------------------------

ADAPTER_ID: str = "ccm-bir"
STATUS: str = "reserved"

# FedRAMP Notice 0009 mandatory adoption date. CCM comes first because
# the collaborative-ConMon pathway is easier to bring up than VDR (it
# re-uses the monthly cadence) and upstream prioritized the BIR shape.
MANDATORY_ADOPTION_DATE: str = "2027-04-01"

# How many days before MANDATORY_ADOPTION_DATE the readiness check
# should start firing issues if status is still "reserved".
READINESS_LEAD_DAYS: int = 90


class CcmBirAdapterNotYetAvailable(NotImplementedError):
    """Raised on any attempt to instantiate the CCM BIR adapter before publication.

    The CCM Balance Improvement Release has not been published by
    FedRAMP as of the pin date recorded in
    ``src/uiao/canon/adapter-registry.yaml`` (id: ``ccm-bir``).
    """


class CcmBirAdapter:
    """CCM BIR conformance adapter — reserved stub.

    Any attempt to instantiate raises
    :class:`CcmBirAdapterNotYetAvailable` so misconfigured pipelines
    fail fast rather than silently running against an absent
    implementation. The class exists only to make the status surface
    introspectable via :mod:`scripts.conmon.migration_readiness`.
    """

    ADAPTER_ID: str = ADAPTER_ID
    STATUS: str = STATUS
    MANDATORY_ADOPTION_DATE: str = MANDATORY_ADOPTION_DATE

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise CcmBirAdapterNotYetAvailable(
            "Collaborative Continuous Monitoring (CCM) Balance Improvement "
            "Release has not been published by FedRAMP. "
            f"Mandatory adoption per Notice 0009: {MANDATORY_ADOPTION_DATE}. "
            "Use the Pathway-2 monthly ConMon meeting + OSCAL drop cadence "
            "until the BIR ships; see ADR-043 D1 / D3 and "
            "docs/docs/uiao-rfc-0026-roadmap.md (E8)."
        )
