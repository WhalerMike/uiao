"""Brownfield OrgPath inventory — capture already-enrolled devices that
carry no (or partial) OrgPath, across the Entra (Graph) and Arc (ARM) planes.

Net-new devices get OrgPath at procurement (Intune-First Asset Onboarding);
the existing AD fleet gets it derived during the AD→Entra migration. This
module covers the third population: devices **already enrolled** in Intune /
Entra and/or Azure Arc whose OrgPath slots were never stamped.

What it does (read-only):

1. **Normalize** raw Entra device objects (Graph ``onPremisesExtensionAttributes``)
   and Arc machine resources (ARM ``tags``) into a plane-agnostic
   :class:`DeviceRecord`, reading each object's *current* OrgPath slot values.
2. **Classify** each device's capture status against the Codebook (UIAO_151):
   ``complete`` / ``partial`` / ``absent`` — i.e. which named facets are missing.
   Missing facets are exactly what the engine flags as ``DRIFT-IDENTITY``.
3. **Propose** an OrgPath for the missing facets via the canonical
   source-precedence chain (asset/CMDB record → primary-user/owner derivation),
   validated against the Codebook; anything unresolved is bucketed for review —
   never auto-guessed.
4. **Emit** a ``govern``-compatible snapshot (current state, so the drift loop
   re-confirms the gaps as ``DRIFT-IDENTITY``) plus a backfill worklist (current
   vs proposed per device, with the resolution source or the unresolved reason).

This module is **pure** (no network I/O); the live Graph/ARM read helpers at the
bottom take an injected transport so they are unit-testable with a fake. Nothing
here writes — backfill goes through the existing ``assess --write`` /
``EntraDeviceOrgPathAdapter`` path.

Canon: UIAO_151 (Codebook), UIAO_163 (drift), ADR-038 / ADR-084 (device plane).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from uiao.modernization.orgtree.codebook import Codebook
from uiao.modernization.orgtree.device_orgpath import _arm_tag_name

# Plane identifiers — match the device-plane writer's routing.
PLANE_ENTRA = "entra"
PLANE_ARM = "arm"

# Capture status of one device's OrgPath.
CAPTURE_COMPLETE = "complete"  # every named facet has a value
CAPTURE_PARTIAL = "partial"  # some named facets present, some missing
CAPTURE_ABSENT = "absent"  # no named facet has a value

# Resolution sources, in precedence order (highest first).
SOURCE_ASSET = "asset-map"  # procurement / CMDB record keyed by serial/name
SOURCE_OWNER = "owner-map"  # primary-user / registered-owner derivation

# Default ARM API version for hybrid-compute machines (matches the writer).
ARM_MACHINES_API_VERSION = "2023-03-15-preview"

# Graph $select for the device read — only what inventory needs.
ENTRA_DEVICE_SELECT = "id,deviceId,displayName,onPremisesExtensionAttributes,registeredOwners"


# ---------------------------------------------------------------------------
# Normalized input record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeviceRecord:
    """A plane-agnostic view of one already-enrolled device.

    ``current_slots`` maps an ``extensionAttribute*`` slot to its current
    value, restricted to the slots bound to *named* Codebook facets and to
    non-empty values. ``correlation_keys`` carries the identifiers used to
    resolve a proposed OrgPath (e.g. ``serial``, ``hostname``, ``owner_id``).
    """

    target_id: str
    plane: str
    display_name: str
    current_slots: Mapping[str, str]
    correlation_keys: Mapping[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Per-device capture result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaptureResult:
    """The capture + proposed-backfill verdict for one device."""

    target_id: str
    plane: str
    display_name: str
    status: str
    current_facets: Mapping[str, str]
    missing_facets: tuple[str, ...]
    proposed_facets: Mapping[str, str]
    source: str | None
    unresolved_reason: str | None
    findings: tuple[str, ...]

    @property
    def needs_backfill(self) -> bool:
        return self.status != CAPTURE_COMPLETE

    @property
    def resolved(self) -> bool:
        """True when a proposal covers every missing facet."""
        return self.needs_backfill and not self.missing_after_proposal

    @property
    def missing_after_proposal(self) -> tuple[str, ...]:
        """Missing facets the proposal does not (validly) cover."""
        return tuple(f for f in self.missing_facets if f not in self.proposed_facets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "plane": self.plane,
            "display_name": self.display_name,
            "status": self.status,
            "current_facets": dict(self.current_facets),
            "missing_facets": list(self.missing_facets),
            "proposed_facets": dict(self.proposed_facets),
            "source": self.source,
            "unresolved_reason": self.unresolved_reason,
            "findings": list(self.findings),
        }


# ---------------------------------------------------------------------------
# Normalizers — raw Graph / ARM objects -> DeviceRecord
# ---------------------------------------------------------------------------


def _named_facets(codebook: Codebook) -> list[tuple[str, Any]]:
    """Return ``(facet_name, Facet)`` for every non-reserved (named) facet.

    Excludes the ADR-127 derived org_path (inheritance layer): the survey
    measures which governance facets need backfilling from source data,
    and the derived path is recomputed by the writers, never backfilled.
    """
    derived = codebook.derived_path_facet_name()
    return [(name, f) for name, f in codebook.facets.items() if f.kind != "reserved" and name != derived]


def device_from_entra(raw: Mapping[str, Any], codebook: Codebook) -> DeviceRecord:
    """Normalize one Entra device object (Graph) into a :class:`DeviceRecord`.

    Reads the OrgPath slots from ``onPremisesExtensionAttributes`` (only the
    slots bound to named facets, and only non-empty values). Correlation keys:
    the device display name (hostname) and the first registered owner's id
    (for primary-user derivation).
    """
    ext = raw.get("onPremisesExtensionAttributes") or {}
    current: dict[str, str] = {}
    for _name, facet in _named_facets(codebook):
        value = ext.get(facet.attribute)
        if value:
            current[facet.attribute] = str(value)

    correlation: dict[str, str] = {}
    name = raw.get("displayName") or ""
    if name:
        correlation["hostname"] = name
    owners = raw.get("registeredOwners") or []
    if owners and isinstance(owners[0], Mapping) and owners[0].get("id"):
        correlation["owner_id"] = str(owners[0]["id"])

    return DeviceRecord(
        target_id=str(raw.get("id") or raw.get("deviceId") or name),
        plane=PLANE_ENTRA,
        display_name=name,
        current_slots=current,
        correlation_keys=correlation,
    )


def machine_from_arm(raw: Mapping[str, Any], codebook: Codebook) -> DeviceRecord:
    """Normalize one Arc machine resource (ARM) into a :class:`DeviceRecord`.

    Reads the OrgPath facets from the resource ``tags`` (PascalCase facet keys
    per the device-plane writer) and maps each back to its slot. The ARM
    ``target_id`` is the full resource id — exactly what the writeback needs.
    """
    tags = raw.get("tags") or {}
    current: dict[str, str] = {}
    for facet_name, facet in _named_facets(codebook):
        value = tags.get(_arm_tag_name(facet_name))
        if value:
            current[facet.attribute] = str(value)

    name = raw.get("name") or ""
    correlation: dict[str, str] = {}
    if name:
        correlation["hostname"] = name

    return DeviceRecord(
        target_id=str(raw.get("id") or name),
        plane=PLANE_ARM,
        display_name=name,
        current_slots=current,
        correlation_keys=correlation,
    )


# ---------------------------------------------------------------------------
# Source resolution + classification
# ---------------------------------------------------------------------------

# A source map is keyed by a correlation value (serial / hostname / owner id)
# and yields a partial OrgPath: facet name -> proposed value.
SourceMap = Mapping[str, Mapping[str, str]]


def _resolve_proposed(
    record: DeviceRecord,
    *,
    asset_map: SourceMap | None,
    owner_map: SourceMap | None,
) -> tuple[Mapping[str, str] | None, str | None]:
    """Resolve a proposed OrgPath via the source-precedence chain.

    Precedence: asset/CMDB record (matched on any correlation key, then the
    target id) → primary-user/owner derivation (matched on ``owner_id``). The
    first hit wins. Returns ``(proposal, source)`` or ``(None, None)``.
    """
    if asset_map:
        for key in (*record.correlation_keys.values(), record.target_id):
            if key in asset_map:
                return asset_map[key], SOURCE_ASSET
    if owner_map:
        owner_id = record.correlation_keys.get("owner_id")
        if owner_id and owner_id in owner_map:
            return owner_map[owner_id], SOURCE_OWNER
    return None, None


def classify_device(
    record: DeviceRecord,
    codebook: Codebook,
    *,
    asset_map: SourceMap | None = None,
    owner_map: SourceMap | None = None,
) -> CaptureResult:
    """Classify one device's capture status and propose a backfill."""
    named = _named_facets(codebook)
    named_names = {name for name, _ in named}

    current_facets = {
        name: record.current_slots[f.attribute] for name, f in named if f.attribute in record.current_slots
    }
    # Optional facets (allow_empty) never count as missing: an unpopulated
    # slot is a legitimate state for them, so a device lacking one is still
    # "complete" for backfill purposes (ADR-137).
    missing = tuple(name for name, f in named if f.attribute not in record.current_slots and not f.allow_empty)

    if not missing:
        status = CAPTURE_COMPLETE
    elif not current_facets:
        status = CAPTURE_ABSENT
    else:
        status = CAPTURE_PARTIAL

    proposed: dict[str, str] = {}
    findings: list[str] = []
    source: str | None = None
    unresolved_reason: str | None = None

    if missing:
        raw_proposed, source = _resolve_proposed(record, asset_map=asset_map, owner_map=owner_map)
        if raw_proposed is None:
            keys = ", ".join(f"{k}={v}" for k, v in record.correlation_keys.items()) or "(none)"
            unresolved_reason = f"no asset-map/owner-map match for correlation keys: {keys}"
        else:
            for fname, value in raw_proposed.items():
                if fname not in named_names or fname not in missing:
                    continue  # ignore non-facets and facets already set
                facet = codebook.facet(fname)
                if facet.is_active(str(value)):
                    proposed[fname] = str(value)
                else:
                    findings.append(f"{fname}={value!r} not a valid {facet.kind} value in the codebook")

    return CaptureResult(
        target_id=record.target_id,
        plane=record.plane,
        display_name=record.display_name,
        status=status,
        current_facets=current_facets,
        missing_facets=missing,
        proposed_facets=proposed,
        source=source,
        unresolved_reason=unresolved_reason,
        findings=tuple(findings),
    )


# ---------------------------------------------------------------------------
# Inventory report — snapshot + worklist emitters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InventoryReport:
    """The result of an inventory pass: the normalized records + verdicts."""

    records: tuple[DeviceRecord, ...]
    results: tuple[CaptureResult, ...]

    @property
    def summary(self) -> dict[str, int]:
        needs = [r for r in self.results if r.needs_backfill]
        return {
            "total": len(self.results),
            "complete": sum(1 for r in self.results if r.status == CAPTURE_COMPLETE),
            "partial": sum(1 for r in self.results if r.status == CAPTURE_PARTIAL),
            "absent": sum(1 for r in self.results if r.status == CAPTURE_ABSENT),
            "needs_backfill": len(needs),
            "resolved": sum(1 for r in needs if r.resolved),
            "unresolved": sum(1 for r in needs if not r.resolved),
            "with_findings": sum(1 for r in self.results if r.findings),
            "entra": sum(1 for r in self.results if r.plane == PLANE_ENTRA),
            "arm": sum(1 for r in self.results if r.plane == PLANE_ARM),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        """A ``govern``-compatible snapshot of the **current** tenant state.

        Principals carry their current slot values only; missing OrgPath slots
        are simply absent, so a governance pass re-confirms each gap as a
        ``DRIFT-IDENTITY`` finding.
        """
        return {
            "principals": [
                {
                    "principal_id": rec.target_id,
                    "principal_type": "device",
                    "attributes": dict(rec.current_slots),
                }
                for rec in self.records
            ],
        }

    def to_worklist_dict(self) -> dict[str, Any]:
        """The backfill worklist: summary + per-device current/proposed verdict."""
        return {
            "summary": self.summary,
            "devices": [r.to_dict() for r in self.results],
        }


def build_inventory(
    records: Iterable[DeviceRecord],
    codebook: Codebook,
    *,
    asset_map: SourceMap | None = None,
    owner_map: SourceMap | None = None,
) -> InventoryReport:
    """Classify every device and bundle the snapshot + worklist into a report."""
    recs = tuple(records)
    results = tuple(classify_device(r, codebook, asset_map=asset_map, owner_map=owner_map) for r in recs)
    return InventoryReport(records=recs, results=results)


# ---------------------------------------------------------------------------
# Live read helpers (thin) — page Graph devices / ARM machines via a transport
# ---------------------------------------------------------------------------

Transport = Callable[[str, str, dict | None], dict]


def read_entra_devices(
    transport: Transport,
    *,
    select: str = ENTRA_DEVICE_SELECT,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    """Page ``GET /devices`` via an injected Graph transport.

    Follows ``@odata.nextLink`` until exhausted. The transport is responsible
    for auth + base resolution (see :class:`uiao.adapters.graph_transport`).
    """
    out: list[dict[str, Any]] = []
    path: str | None = f"/devices?$select={select}&$top={page_size}"
    while path:
        resp = transport("GET", path, None)
        out.extend(resp.get("value", []))
        path = resp.get("@odata.nextLink")
    return out


def read_arm_machines(
    transport: Transport,
    subscription: str,
    *,
    api_version: str = ARM_MACHINES_API_VERSION,
) -> list[dict[str, Any]]:
    """Page ``GET .../Microsoft.HybridCompute/machines`` via an ARM transport.

    Follows ARM ``nextLink`` until exhausted. The transport is responsible for
    auth + base resolution (see :class:`uiao.adapters.arm_transport`).
    """
    out: list[dict[str, Any]] = []
    path: str | None = (
        f"/subscriptions/{subscription}/providers/Microsoft.HybridCompute/machines?api-version={api_version}"
    )
    while path:
        resp = transport("GET", path, None)
        out.extend(resp.get("value", []))
        path = resp.get("nextLink")
    return out


__all__ = [
    "ARM_MACHINES_API_VERSION",
    "CAPTURE_ABSENT",
    "CAPTURE_COMPLETE",
    "CAPTURE_PARTIAL",
    "ENTRA_DEVICE_SELECT",
    "PLANE_ARM",
    "PLANE_ENTRA",
    "SOURCE_ASSET",
    "SOURCE_OWNER",
    "CaptureResult",
    "DeviceRecord",
    "InventoryReport",
    "build_inventory",
    "classify_device",
    "device_from_entra",
    "machine_from_arm",
    "read_arm_machines",
    "read_entra_devices",
]
