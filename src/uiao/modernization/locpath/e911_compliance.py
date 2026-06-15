"""E911 Compliance Layer — dispatchable-location completeness — ADR-104.

The E911 Compliance Layer is the regulatory-completeness surface over the
LocPath substrate established by ADR-102 / UIAO_194. It makes the
codebook's standing "E911 completeness" rule (UIAO_194 §Governance rule 5)
executable: a governed location that has Multi-Line Telephone System /
UCaaS presence — i.e., 911 can be dialed from it — must carry a
**dispatchable location** sufficient for responders to find the caller,
per [47 CFR § 9.16](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-9)
(RAY BAUM'S Act § 506: civic address plus floor / room-level detail).

A node declares the obligation with the governed ``e911`` flag
``dispatchableLocationRequired: true`` (added to the node schema by
ADR-104). :func:`detect_e911_completeness_gaps` is the read-only
Compare/Classify pass: for every obligated node it resolves the
**effective dispatchable location** — the node's own ``e911`` block plus
any attribute inherited from its registered ancestors (a Floor inherits
the Site's civic address; the Site need not repeat the floor) — and emits
a finding when that effective payload is incomplete at the node's level.

This layer governs only the *location of record*. Real-time positioning
(the Dynamic Location Context — GPS / Wi-Fi / BLE / UWB / RFID / network,
UIAO_194 §Two-layer model) may *enhance* dispatchable location at call
time on platforms that support it, but it never substitutes for the
governed payload and is out of scope here. UIAO never sits in the 911
call path (ADR-102 §D7); it governs the completeness of the source the
UCaaS/MLTS platform consumes.

Findings reuse the HRIT :class:`DriftFinding` shape so they merge into the
substrate report, classed ``DRIFT-SEMANTIC::e911-completeness`` — a
content-completeness gap (the governed model is missing data a real-world
regulatory obligation requires), sub-classed off the canonical ADR-012
``DRIFT-SEMANTIC`` top level, the same extension mechanism the phase-3
location drift classes use. Error codes continue the ``GOV-LOCPATH-NNN``
series from :mod:`~uiao.modernization.locpath.drift` (006-011).
"""

from __future__ import annotations

from typing import Mapping

from uiao.adapters.modernization.hrit.inventory import DriftFinding
from uiao.modernization.locpath.registry import (
    LocationNode,
    LocationRegistry,
    load_location_registry,
)

#: E911-completeness drift class — a content-completeness sub-class of the
#: canonical ADR-012 ``DRIFT-SEMANTIC`` top level (ADR-104; same mechanism
#: as the phase-3 ``DRIFT-*::location-*`` classes).
DRIFT_E911_COMPLETENESS = "DRIFT-SEMANTIC::e911-completeness"

# Error codes — continuing the GOV-LOCPATH series from drift.py (006-011).
ERROR_NO_DISPATCHABLE_LOCATION = "GOV-LOCPATH-012"
ERROR_INSUFFICIENT_PRECISION = "GOV-LOCPATH-013"
ERROR_OBLIGATION_NOT_LOCATABLE = "GOV-LOCPATH-014"

#: The governed flag that turns the dispatchable-location obligation on.
OBLIGATION_FLAG = "dispatchableLocationRequired"

#: Levels that name a physically dispatchable place. Country/Region are
#: organizational/geographic abstractions — MLTS presence cannot attach
#: there, so an obligation declared at those levels is a modeling fault.
LOCATABLE_LEVELS: frozenset[str] = frozenset({"Site", "Building", "Floor", "Space"})

#: Levels at which § 9.16 sub-address precision (floor / room / location
#: description) is expected. A single-structure Site may carry a complete
#: dispatchable location with civic address alone; below the Site, a bare
#: street address cannot locate a caller to the responder's satisfaction.
PRECISION_REQUIRED_LEVELS: frozenset[str] = frozenset({"Building", "Floor", "Space"})

#: Sub-address attributes that satisfy the § 9.16 "sufficient to locate"
#: precision requirement.
_PRECISION_KEYS: tuple[str, ...] = ("floor", "room", "locationDescription")


def _is_required(node: LocationNode) -> bool:
    """True when the node carries the governed dispatchable-location obligation."""
    return node.e911.get(OBLIGATION_FLAG) is True


def _nonempty(value: object) -> bool:
    """A dispatchable-location attribute counts only when it is a non-blank string."""
    return isinstance(value, str) and value.strip() != ""


def _effective_e911(registry: LocationRegistry, node: LocationNode) -> Mapping[str, object]:
    """Merge the node's ``e911`` block with values inherited from its ancestors.

    Nearest node wins: the node's own attributes take precedence, and each
    ancestor (Site outward to the node's parent) fills only the gaps left
    by closer nodes. This is how a Floor inherits the Site's civic address
    without the Site having to repeat the floor.
    """
    effective: dict[str, object] = {}
    # Ancestors are returned outermost (Country) first; apply them first so
    # closer ancestors and finally the node itself overwrite outer values.
    for ancestor in registry.ancestors_of(node.loc_path):
        for key, value in ancestor.e911.items():
            if _nonempty(value):
                effective[key] = value
    for key, value in node.e911.items():
        if _nonempty(value):
            effective[key] = value
    return effective


def detect_e911_completeness_gaps(
    registry: LocationRegistry | None = None,
) -> tuple[DriftFinding, ...]:
    """Find governed locations whose dispatchable location is incomplete — read-only.

    For every node flagged ``dispatchableLocationRequired: true`` this
    Compare/Classify pass emits, against the node's effective (own +
    inherited) ``e911`` payload:

    * ``GOV-LOCPATH-014`` (P3) — the obligation is declared at a level that
      does not name a dispatchable place (Country/Region); a modeling
      fault that is reported and then skipped.
    * ``GOV-LOCPATH-012`` (P1) — no civic address is resolvable; responders
      have no street address. The § 9.16 floor of compliance is unmet.
    * ``GOV-LOCPATH-013`` (P2) — a civic address resolves but no sub-address
      precision (floor / room / location description) does, at a level
      (Building/Floor/Space) where § 9.16 expects it.

    The pass never writes and never consults Dynamic Location Context — it
    classifies the governed location of record only. Returns findings in
    node-declaration order.
    """
    reg = registry or load_location_registry()
    findings: list[DriftFinding] = []

    for node in reg.nodes:
        if not _is_required(node):
            continue

        if node.level not in LOCATABLE_LEVELS:
            findings.append(
                DriftFinding(
                    drift_class=DRIFT_E911_COMPLETENESS,
                    severity="P3",
                    path=node.loc_path,
                    detail=f"node declares {OBLIGATION_FLAG} at level '{node.level}', which does "
                    "not name a dispatchable place — MLTS/UCaaS presence attaches at Site or "
                    "deeper (47 CFR § 9.16)",
                    error_code=ERROR_OBLIGATION_NOT_LOCATABLE,
                    object_type="LocationNode",
                )
            )
            continue

        effective = _effective_e911(reg, node)

        if not _nonempty(effective.get("civicAddress")):
            findings.append(
                DriftFinding(
                    drift_class=DRIFT_E911_COMPLETENESS,
                    severity="P1",
                    path=node.loc_path,
                    detail="node has MLTS/UCaaS presence but no civic address is resolvable on it "
                    "or any registered ancestor — no dispatchable location of record exists "
                    "(47 CFR § 9.16)",
                    error_code=ERROR_NO_DISPATCHABLE_LOCATION,
                    object_type="LocationNode",
                )
            )
            continue

        if node.level in PRECISION_REQUIRED_LEVELS and not any(
            _nonempty(effective.get(key)) for key in _PRECISION_KEYS
        ):
            findings.append(
                DriftFinding(
                    drift_class=DRIFT_E911_COMPLETENESS,
                    severity="P2",
                    path=node.loc_path,
                    detail="dispatchable location resolves a civic address but no floor, room, or "
                    f"location description at level '{node.level}' — insufficient to locate the "
                    "caller (47 CFR § 9.16)",
                    error_code=ERROR_INSUFFICIENT_PRECISION,
                    object_type="LocationNode",
                )
            )

    return tuple(findings)
