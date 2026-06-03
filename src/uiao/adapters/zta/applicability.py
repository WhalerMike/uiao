"""Derive a boundary-applicability signal for a Zero Trust Assessment check.

Under a GCC / FedRAMP Moderate boundary a low pass-rate is frequently
"feature not in boundary", not "control broken". The Zero Trust Assessment
already encodes enough to tell these apart **without a hand-authored map**:

* ``TestStatus == "Skipped"`` plus a ``SkippedReason`` of "not applicable to the
  current environment" / "requires … license" / "requires connection to the
  service(s) … currently disconnected", and
* ``TestMinimumLicense`` naming a premium / P2-class SKU.

This module turns those fields into an :class:`Applicability` tag plus a short
rationale. It deliberately does **not** attempt the ``required`` vs
``above-baseline`` split — that needs the FedRAMP-Moderate 800-53 crosswalk,
which is authored in canon (a separate work item; see the draft ADR).
"""

from __future__ import annotations

from enum import Enum

from uiao.adapters.zta.model import STATUS_SKIPPED, ZtTest

#: Substrings that mark a premium / P2-class SKU. Presence is a *proxy* for
#: "may not be available or authorized in GCC-Moderate" — verify per SKU.
PREMIUM_MARKERS: tuple[str, ...] = (
    "PREMIUM",
    "P2",
    "AAD_PREMIUM",
    "Entra_Premium",
    "Governance",
    "RMS_S_PREMIUM",
    "Azure_Firewall",
    "Azure_FrontDoor",
    "DDoS",
    "WAF",
)


class Applicability(str, Enum):
    """Why a check may or may not bear on the current boundary."""

    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not-applicable"
    LICENSE_GATED = "license-gated"
    SERVICE_DISCONNECTED = "service-disconnected"
    SKIPPED_OTHER = "skipped-other"


def license_str(test: ZtTest) -> str:
    """Flatten ``TestMinimumLicense`` to a single comparable string."""
    return ", ".join(test.test_minimum_license)


def is_premium_gated(test: ZtTest) -> bool:
    """True when the check requires a premium / P2-class SKU."""
    licenses = license_str(test).lower()
    return any(marker.lower() in licenses for marker in PREMIUM_MARKERS)


def derive_applicability(test: ZtTest) -> Applicability:
    """Classify a check's applicability to the current boundary from its fields."""
    if test.test_status == STATUS_SKIPPED:
        reason = (test.skipped_reason or "").lower()
        if "not applicable" in reason:
            return Applicability.NOT_APPLICABLE
        if "license" in reason:
            return Applicability.LICENSE_GATED
        if "disconnected" in reason or "connection to the service" in reason:
            return Applicability.SERVICE_DISCONNECTED
        return Applicability.SKIPPED_OTHER
    if is_premium_gated(test):
        return Applicability.LICENSE_GATED
    return Applicability.APPLICABLE


def applicability_rationale(test: ZtTest) -> str:
    """Human-readable explanation for the derived tag."""
    if test.skipped_reason:
        return test.skipped_reason.strip()
    if is_premium_gated(test):
        return f"requires premium SKU: {license_str(test)}"
    return "runs against the current environment"
