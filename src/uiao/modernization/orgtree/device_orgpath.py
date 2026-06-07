"""Device-plane OrgPath writer — Model C (ADR-084 §C9 Phase 5 #5).

**Different pattern from dynamic-groups / admin-units / policy-targeting.**
Those three consumers emit *boolean composition rule strings*. This
consumer emits *per-facet PATCH writes* — 10 attribute writes per
device, dispatched to one of two transports based on the device's
disposition.

Per ADR-078 / ADR-038, the dual-transport routing is preserved from
the retired Model A device-plane adapter:

* ``ENTRA-DEVICE`` disposition → Microsoft Graph PATCH on the device's
  ``onPremisesExtensionAttributes`` (10 facet writes in one body)
* ``ARC-SERVER`` / ``STAY-AD-DEPENDENCY`` /
  ``MANAGED-IDENTITY-CANDIDATE`` → ARM PATCH on the resource's
  ``tags`` (10 facet-named tags in one body)
* ``STAY-AD-DC`` / ``DECOMMISSION`` → skip; no write attempted

The consumer plans the per-facet writes; the
:py:class:`uiao.adapters.entra_device_orgpath.EntraDeviceOrgPathAdapter`
dispatches them through the correct transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from ._yaml_loaders import (
    read_schema_resource,
    read_yaml_path,
    read_yaml_resource,
    validate_against_schema,
)
from .codebook import Codebook
from .types import FacetOperation

# Dispositions that write to the Microsoft Graph plane (Entra device).
_ENTRA_DISPOSITIONS = frozenset({"ENTRA-DEVICE"})

# Dispositions that write to the ARM plane (Arc machine).
_ARM_DISPOSITIONS = frozenset({"ARC-SERVER", "STAY-AD-DEPENDENCY", "MANAGED-IDENTITY-CANDIDATE"})

# Dispositions that explicitly do not write.
_SKIP_DISPOSITIONS = frozenset({"STAY-AD-DC", "DECOMMISSION"})


@dataclass(frozen=True)
class DeviceFacetAssignment:
    """The 10-facet OrgPath assignment for one device.

    ``facet_values`` is a mapping of facet name → value (e.g.
    ``{"region": "EASTUS", "department": "IT", ...}``). The consumer
    resolves each facet name to its slot via the Codebook and validates
    the value before emitting the write.
    """

    device_id: str
    disposition: str
    facet_values: Mapping[str, str]


@dataclass(frozen=True)
class DeviceOrgPathPlan:
    """A single device's planned per-facet writes.

    ``plane`` is ``"entra"`` (Graph) or ``"arm"`` (ARM tags) or
    ``"skip"`` (no write). ``writes`` is a tuple of per-facet
    :py:class:`FacetOperation` records — one per facet — empty when
    ``plane == "skip"``.
    """

    device_id: str
    disposition: str
    plane: str
    writes: tuple[FacetOperation, ...]


class DeviceOrgPathPlanner:
    """Plan per-facet device-plane writes from disposition + facet values.

    Per ADR-038 / ADR-078, one device → 10 per-facet writes routed to
    one of two transports based on disposition (or skipped entirely).

    Routing defaults to the canonical disposition set hardcoded in this
    module. Deployments that declare additional dispositions in
    ``device-planes.yaml`` can pass the mapping from
    :func:`load_disposition_routing` as ``routing`` to override it; the
    hardcoded set is used when ``routing`` is ``None``.
    """

    def __init__(self, codebook: Codebook, routing: Mapping[str, str] | None = None) -> None:
        self.codebook = codebook
        self._routing: dict[str, str] | None = dict(routing) if routing is not None else None

    def plan_device(self, assignment: DeviceFacetAssignment) -> DeviceOrgPathPlan:
        """Plan one device's writes — returns the full per-facet operation set."""
        plane = self._plane_for_disposition(assignment.disposition)
        if plane == "skip":
            return DeviceOrgPathPlan(
                device_id=assignment.device_id,
                disposition=assignment.disposition,
                plane="skip",
                writes=(),
            )

        writes: list[FacetOperation] = []
        for facet_name, value in assignment.facet_values.items():
            facet = self.codebook.facet(facet_name)
            if facet.kind == "reserved":
                # Reserved facets cannot be written until promoted.
                continue
            if not facet.is_active(value):
                # Skip writes that would create per-facet drift on landing.
                # Engine surfaces these as Value Drift (P2) on the input.
                continue
            attribute = (
                facet.attribute  # Graph: extensionAttribute1..10
                if plane == "entra"
                else f"tags.{_arm_tag_name(facet_name)}"  # ARM: tags.Region, tags.Department, ...
            )
            writes.append(
                FacetOperation(
                    facet=facet_name,
                    attribute=attribute,
                    op="write",
                    value=value,
                    target=assignment.device_id,
                    metadata={
                        "disposition": assignment.disposition,
                        "plane": plane,
                    },
                )
            )
        return DeviceOrgPathPlan(
            device_id=assignment.device_id,
            disposition=assignment.disposition,
            plane=plane,
            writes=tuple(writes),
        )

    def plan(self, assignments: Iterable[DeviceFacetAssignment]) -> list[FacetOperation]:
        """Plan many devices — returns the flat list of all per-facet writes."""
        all_ops: list[FacetOperation] = []
        for assignment in assignments:
            plan = self.plan_device(assignment)
            all_ops.extend(plan.writes)
        return all_ops

    def _plane_for_disposition(self, disposition: str) -> str:
        # Deployment-supplied routing (from load_disposition_routing) takes
        # precedence over the hardcoded canonical set when provided.
        if self._routing is not None:
            try:
                return self._routing[disposition]
            except KeyError:
                raise ValueError(
                    f"Unknown disposition '{disposition}'. Expected one of: {sorted(self._routing)}"
                ) from None
        if disposition in _ENTRA_DISPOSITIONS:
            return "entra"
        if disposition in _ARM_DISPOSITIONS:
            return "arm"
        if disposition in _SKIP_DISPOSITIONS:
            return "skip"
        raise ValueError(
            f"Unknown disposition '{disposition}'. "
            f"Expected one of: {sorted(_ENTRA_DISPOSITIONS | _ARM_DISPOSITIONS | _SKIP_DISPOSITIONS)}"
        )


def _arm_tag_name(facet_name: str) -> str:
    """Convert facet name to ARM tag name (PascalCase from snake_case)."""
    return "".join(part.capitalize() for part in facet_name.split("_"))


__all__ = [
    "DeviceFacetAssignment",
    "DeviceOrgPathPlan",
    "DeviceOrgPathPlanner",
]


# ---------------------------------------------------------------------------
# YAML loader for disposition routing (ADR-084 §C1)
# ---------------------------------------------------------------------------

_YAML_PACKAGE = "uiao.canon.data.orgpath"
_YAML_RESOURCE = "device-planes.yaml"
_SCHEMA_PACKAGE = "uiao.schemas.orgpath"
_SCHEMA_RESOURCE = "device-planes.schema.json"


def load_disposition_routing(
    *,
    yaml_path: Path | str | None = None,
) -> dict[str, str]:
    """Load the disposition→plane routing from the canonical YAML.

    Returns a mapping like ``{"ENTRA-DEVICE": "entra", "ARC-SERVER": "arm", "STAY-AD-DC": "skip", ...}``
    suitable for passing to :py:class:`DeviceOrgPathPlanner` as its
    ``routing`` argument, which overrides the module's hardcoded routing
    in deployments that declare additional dispositions. The hardcoded
    routing in :py:class:`DeviceOrgPathPlanner` matches this YAML 1:1 for
    the canonical disposition set; the YAML is the audit-friendly source
    of truth.
    """
    document = read_yaml_resource(_YAML_PACKAGE, _YAML_RESOURCE) if yaml_path is None else read_yaml_path(yaml_path)
    schema = read_schema_resource(_SCHEMA_PACKAGE, _SCHEMA_RESOURCE)
    validate_against_schema(document, schema, "device-planes")
    return {d["name"]: d["plane"] for d in document["dispositions"]}
