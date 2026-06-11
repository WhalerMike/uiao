"""Location drift classes + site policy/boundary detection — ADR-102 §D6 phase 3.

Defines the three location drift classes reserved by UIAO_194
§Governance and authorized by ADR-102 §D6, expressed as **sub-classes**
of the canonical taxonomy — the same extension mechanism as
``DRIFT-SCHEMA::slot-occupied`` (ADR-063) and ``DRIFT-SEMANTIC::orphan``
/ ``::phantom`` (UIAO_163 v2.0). The five ADR-012 top-level classes and
the ADR-033 ``DRIFT-BOUNDARY`` class are unchanged; location drift
buckets under them:

* ``DRIFT-IDENTITY::location-assignment`` — an identity's recorded
  Primary LocPath disagrees with what the HR system of record derives
  (stale assignment, unresolvable duty station, mover not yet
  reconciled). Emitted by :mod:`~uiao.modernization.locpath.hr_assign`
  and :mod:`~uiao.modernization.locpath.mover`.
* ``DRIFT-AUTHZ::location-policy`` — a site's observed network behavior
  disagrees with its governed classification (e.g., local internet
  breakout at a ``diaApproved: false`` site).
* ``DRIFT-BOUNDARY::location-boundary`` — telemetry observed leaving a
  location outside its declared ``telemetryBoundary`` /
  ``allowedTelemetryDestinations``.

:func:`detect_location_policy_drift` is the read-only Compare/Classify
pass for the policy and boundary classes. It consumes
:class:`ObservedSiteState` — the minimal observational contract for
per-site network/telemetry state. What *produces* observations (SD-WAN
exports, M365 connectivity telemetry, boundary probes) is a collector
concern outside this module; the gcc_boundary_probe adapter is the
existing precedent for the boundary signal.

Findings reuse the HRIT ``DriftFinding`` shape so they merge into the
substrate report. Error codes continue the ``GOV-LOCPATH-NNN`` series
started by ``hr_assign``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from uiao.adapters.modernization.hrit.inventory import DriftFinding
from uiao.modernization.locpath.registry import (
    LocationNode,
    LocationRegistry,
    load_location_registry,
)

#: Location drift classes (UIAO_194 §Governance / ADR-102 §D6 phase 3),
#: as sub-classes of the ADR-012 + ADR-033 canonical taxonomy.
DRIFT_LOCATION_ASSIGNMENT = "DRIFT-IDENTITY::location-assignment"
DRIFT_LOCATION_POLICY = "DRIFT-AUTHZ::location-policy"
DRIFT_LOCATION_BOUNDARY = "DRIFT-BOUNDARY::location-boundary"

# Error codes — continuing the GOV-LOCPATH series from hr_assign (001-005).
ERROR_STALE_ASSIGNMENT = "GOV-LOCPATH-006"
ERROR_UNREGISTERED_OBSERVED_SITE = "GOV-LOCPATH-007"
ERROR_UNAPPROVED_DIA_BREAKOUT = "GOV-LOCPATH-008"
ERROR_BREAKOUT_CLASS_MISMATCH = "GOV-LOCPATH-009"
ERROR_DISALLOWED_TELEMETRY_DESTINATION = "GOV-LOCPATH-010"
ERROR_INTERNAL_ONLY_EGRESS = "GOV-LOCPATH-011"


@dataclass(frozen=True)
class ObservedSiteState:
    """One site's observed network/telemetry state — the phase-3 observational contract.

    Collectors fill what they can see and leave the rest ``None``/empty;
    the detector only compares what is actually observed against what
    the location registry governs.
    """

    loc_path: str
    breakout_observed: str | None = None  # Local | Centralized | Hybrid, as observed
    internet_egress_observed: bool | None = None
    telemetry_destinations: tuple[str, ...] = ()


def _site_node(registry: LocationRegistry, loc_path: str) -> LocationNode | None:
    node = registry.node_for(loc_path)
    if node is not None and node.level == "Site":
        return node
    return None


def detect_location_policy_drift(
    observed: Iterable[ObservedSiteState],
    registry: LocationRegistry | None = None,
) -> tuple[DriftFinding, ...]:
    """Compare observed site state against governed classification — read-only.

    Emits ``DRIFT-AUTHZ::location-policy`` when observed network behavior
    contradicts the site's ``network`` block, and
    ``DRIFT-BOUNDARY::location-boundary`` when observed telemetry egress
    contradicts the site's ``boundaries`` block. Sites the registry does
    not govern at Site level emit a plain ``DRIFT-SEMANTIC`` finding —
    an observation against an unregistered subject is a registry gap,
    not a policy verdict.
    """
    reg = registry or load_location_registry()
    findings: list[DriftFinding] = []

    for state in observed:
        site = _site_node(reg, state.loc_path)
        if site is None:
            findings.append(
                DriftFinding(
                    drift_class="DRIFT-SEMANTIC",
                    severity="P2",
                    path=state.loc_path,
                    detail=f"observed site '{state.loc_path}' is not a registered Site in "
                    f"location registry '{reg.registry_id}' — observations cannot be "
                    "classified against an ungoverned subject",
                    error_code=ERROR_UNREGISTERED_OBSERVED_SITE,
                    object_type="LocationNode",
                )
            )
            continue

        network = site.network
        boundaries = site.boundaries

        # --- DRIFT-AUTHZ::location-policy -----------------------------------
        dia_approved = network.get("diaApproved")
        local_breakout_observed = state.breakout_observed == "Local" or state.internet_egress_observed is True
        if dia_approved is False and local_breakout_observed:
            findings.append(
                DriftFinding(
                    drift_class=DRIFT_LOCATION_POLICY,
                    severity="P1",
                    path=site.loc_path,
                    detail="local internet breakout observed at a site whose governed "
                    "classification is diaApproved: false (TIC 3.0 DIA not approved)",
                    error_code=ERROR_UNAPPROVED_DIA_BREAKOUT,
                    object_type="LocationNode",
                )
            )
        declared_breakout = network.get("sdwanBreakoutType")
        if (
            isinstance(declared_breakout, str)
            and state.breakout_observed is not None
            and state.breakout_observed != declared_breakout
        ):
            findings.append(
                DriftFinding(
                    drift_class=DRIFT_LOCATION_POLICY,
                    severity="P2",
                    path=site.loc_path,
                    detail=f"observed SD-WAN breakout '{state.breakout_observed}' disagrees "
                    f"with governed sdwanBreakoutType '{declared_breakout}'",
                    error_code=ERROR_BREAKOUT_CLASS_MISMATCH,
                    object_type="LocationNode",
                )
            )

        # --- DRIFT-BOUNDARY::location-boundary -------------------------------
        telemetry_boundary = boundaries.get("telemetryBoundary")
        if telemetry_boundary == "InternalOnly" and state.telemetry_destinations:
            findings.append(
                DriftFinding(
                    drift_class=DRIFT_LOCATION_BOUNDARY,
                    severity="P1",
                    path=site.loc_path,
                    detail=f"telemetry egress observed ({', '.join(state.telemetry_destinations)}) "
                    "from a site whose governed telemetryBoundary is InternalOnly",
                    error_code=ERROR_INTERNAL_ONLY_EGRESS,
                    object_type="LocationNode",
                )
            )
        else:
            allowed_raw = boundaries.get("allowedTelemetryDestinations")
            if isinstance(allowed_raw, list | tuple) and allowed_raw:
                allowed = {str(dest).lower() for dest in allowed_raw}
                for dest in state.telemetry_destinations:
                    if dest.lower() not in allowed:
                        findings.append(
                            DriftFinding(
                                drift_class=DRIFT_LOCATION_BOUNDARY,
                                severity="P1",
                                path=site.loc_path,
                                detail=f"telemetry destination '{dest}' is not in the site's "
                                "governed allowedTelemetryDestinations",
                                error_code=ERROR_DISALLOWED_TELEMETRY_DESTINATION,
                                object_type="LocationNode",
                            )
                        )

    return tuple(findings)
