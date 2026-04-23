"""Device-plane OrgPath provisioning adapter (Phase 4, MOD_C / ADR-038).

Closes the gap the session notes flagged as the *critical extension* of
the OrgTree model: device objects need OrgPath just like user objects, but
their storage plane differs by disposition. Clients land on Entra device
``onPremisesExtensionAttributes.extensionAttribute1``; Arc-enrolled
servers land on an ARM tag ``OrgPath=<value>`` on the
``Microsoft.HybridCompute/machines`` resource. Domain controllers and
EOL hosts get no OrgPath at all.

This adapter consumes:

* ``ComputerDisposition`` objects from
  :mod:`uiao.adapters.modernization.active_directory.disposition`
* The MOD_A codebook (ADR-035) for OrgPath value validation
* The device-plane registry (MOD_C / this ADR) for write dispatch

And emits a plan of six operation types across two transport planes
(Graph and ARM). ``apply()`` is dry-run by default; write mode is a single
flag flip, and writes are dispatched per-plane using the endpoint
templates declared in the registry.

MOD_C §Governance:

* **Phantom OrgPath is never auto-remediated.** A device with an OrgPath
  value that fails format validation *or* is not in MOD_A codebook
  becomes a ``device-phantom-orgpath`` / ``arc-phantom-orgpath`` finding
  that surfaces as ``skipped-manual`` — governance review (MOD_E) owns
  the decision to rewrite or retire.
* **Skipped dispositions emit no operation** — the plan still records a
  ``skip-no-plane`` entry so operators see every device in the report.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from uiao.modernization.orgtree import (
    Codebook,
    DevicePlane,
    DevicePlaneRegistry,
)
from uiao.modernization.orgtree.codebook import default_codebook
from uiao.modernization.orgtree.device_planes import (
    default_device_plane_registry,
)

logger = logging.getLogger(__name__)


# Operation vocabulary. Two planes × {create, update, phantom}, plus
# an explicit skip op for dispositions with no plane (DC, EOL).
OP_DEVICE_EXT_CREATE = "device-ext-create"
OP_DEVICE_EXT_UPDATE = "device-ext-update"
OP_DEVICE_PHANTOM = "device-phantom-orgpath"
OP_ARC_TAG_CREATE = "arc-tag-create"
OP_ARC_TAG_UPDATE = "arc-tag-update"
OP_ARC_PHANTOM = "arc-phantom-orgpath"
OP_SKIP_NO_PLANE = "skip-no-plane"

OPS_AUTO_APPLIED = frozenset(
    {
        OP_DEVICE_EXT_CREATE,
        OP_DEVICE_EXT_UPDATE,
        OP_ARC_TAG_CREATE,
        OP_ARC_TAG_UPDATE,
    }
)
OPS_GOVERNANCE_REVIEW = frozenset(
    {
        OP_DEVICE_PHANTOM,
        OP_ARC_PHANTOM,
    }
)
OPS_SKIP = frozenset({OP_SKIP_NO_PLANE})


@dataclass(frozen=True)
class DeviceOrgPathTarget:
    """Input to planning: what a single device should look like.

    Callers assemble these by running the AD survey + disposition
    classifier + :func:`derive_orgpath_from_dn` for each computer record.
    Keeping it as a plain dataclass makes the planner deterministic and
    easy to test without network.
    """

    computer_name: str
    distinguished_name: str
    disposition: str
    orgpath: Optional[str]
    # Graph device object id (may be None if not yet joined to Entra).
    entra_device_id: Optional[str] = None
    # ARM resource id for Arc machines (may be None if not yet enrolled).
    arc_resource_id: Optional[str] = None


@dataclass
class PlannedOperation:
    op: str
    target: str
    reason: str
    plane: Optional[str] = None
    canonical_orgpath: Optional[str] = None
    current_value: Optional[str] = None
    target_object_id: Optional[str] = None
    endpoint: Optional[str] = None
    body: Optional[Dict[str, Any]] = None


@dataclass
class DeviceOrgPathPlan:
    generated_at: str
    total_targets: int
    total_entra_devices: int
    total_arc_resources: int
    operations: List[PlannedOperation] = field(default_factory=list)

    def by_op(self, op: str) -> List[PlannedOperation]:
        return [o for o in self.operations if o.op == op]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_targets": self.total_targets,
            "total_entra_devices": self.total_entra_devices,
            "total_arc_resources": self.total_arc_resources,
            "operations": [
                {
                    "op": o.op,
                    "target": o.target,
                    "reason": o.reason,
                    "plane": o.plane,
                    "canonical_orgpath": o.canonical_orgpath,
                    "current_value": o.current_value,
                    "endpoint": o.endpoint,
                }
                for o in self.operations
            ],
        }


@dataclass
class OperationResult:
    op: str
    target: str
    status: str  # skipped-dry-run | written | failed | skipped-manual | skipped-no-plane
    detail: str = ""


@dataclass
class DeviceOrgPathReport:
    generated_at: str
    dry_run: bool
    results: List[OperationResult] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.status == "written")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "dry_run": self.dry_run,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "results": [r.__dict__ for r in self.results],
        }


class EntraDeviceOrgPathAdapter:
    """Modernization adapter: write OrgPath to Entra devices + Arc resources."""

    ADAPTER_ID = "entra-device-orgpath"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        codebook: Optional[Codebook] = None,
        registry: Optional[DevicePlaneRegistry] = None,
    ) -> None:
        self._config = config or {}
        self._codebook = codebook or default_codebook()
        self._registry = registry or default_device_plane_registry()

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------
    def plan(
        self,
        targets: List[DeviceOrgPathTarget],
        current_entra_devices: Optional[List[Dict[str, Any]]] = None,
        current_arc_resources: Optional[List[Dict[str, Any]]] = None,
    ) -> DeviceOrgPathPlan:
        """Diff canonical targets vs observed device state.

        Tenant shapes:

        * ``current_entra_devices[*]`` — Graph device objects with
          ``id``, ``displayName``, and optionally
          ``onPremisesExtensionAttributes.extensionAttribute1``.
        * ``current_arc_resources[*]`` — ARM resources with ``id``,
          ``name``, and optional ``tags`` dict.
        """
        devices_by_name = {d.get("displayName", ""): d for d in (current_entra_devices or [])}
        arc_by_name = {r.get("name", ""): r for r in (current_arc_resources or [])}

        plan = DeviceOrgPathPlan(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_targets=len(targets),
            total_entra_devices=len(devices_by_name),
            total_arc_resources=len(arc_by_name),
        )

        for target in targets:
            disposition = target.disposition
            if self._registry.is_skip(disposition):
                plan.operations.append(
                    PlannedOperation(
                        op=OP_SKIP_NO_PLANE,
                        target=target.computer_name,
                        reason=(f"Disposition '{disposition}': {self._registry.skip_dispositions[disposition].reason}"),
                    )
                )
                continue

            plane = self._registry.plane_for_disposition(disposition)
            if plane is None:
                plan.operations.append(
                    PlannedOperation(
                        op=OP_SKIP_NO_PLANE,
                        target=target.computer_name,
                        reason=(
                            f"Disposition '{disposition}' is not mapped to any "
                            "plane in the device-plane registry — governance gap"
                        ),
                    )
                )
                continue

            # Nothing to plan if canon says there's no OrgPath target
            if target.orgpath is None:
                plan.operations.append(
                    PlannedOperation(
                        op=OP_SKIP_NO_PLANE,
                        target=target.computer_name,
                        reason=(
                            f"No canonical OrgPath derived for "
                            f"{target.distinguished_name} — "
                            "enqueue for governance review (unresolved)"
                        ),
                        plane=plane.name,
                    )
                )
                continue

            if plane.name == "extensionAttribute1":
                self._plan_device_extension(target, plane, devices_by_name, plan)
            elif plane.name == "ARM-tag":
                self._plan_arc_tag(target, plane, arc_by_name, plan)
            # app-tag deferred to Phase 5 (see MOD_C §Phase 5 note)

        return plan

    def _plan_device_extension(
        self,
        target: DeviceOrgPathTarget,
        plane: DevicePlane,
        devices_by_name: Mapping[str, Dict[str, Any]],
        plan: DeviceOrgPathPlan,
    ) -> None:
        assert target.orgpath is not None
        device = devices_by_name.get(target.computer_name)
        if device is None:
            plan.operations.append(
                PlannedOperation(
                    op=OP_DEVICE_EXT_CREATE,
                    target=target.computer_name,
                    reason=(
                        "Entra device present per canon but no matching "
                        "displayName found in tenant — device may not be "
                        "joined yet. Plan the extensionAttribute1 write for "
                        "when it joins."
                    ),
                    plane=plane.name,
                    canonical_orgpath=target.orgpath,
                    target_object_id=target.entra_device_id,
                    body=self._render_graph_body(plane, target.orgpath),
                    endpoint=self._render_endpoint(
                        plane.endpoint_template,
                        object_id=target.entra_device_id or "{unresolved}",
                    ),
                )
            )
            return

        current = (device.get("onPremisesExtensionAttributes") or {}).get("extensionAttribute1")
        if current == target.orgpath:
            return  # Aligned, no operation.

        # Current value is non-canonical — validate before planning a
        # write. An invalid or out-of-codebook value becomes a phantom
        # finding, never auto-remediated.
        if current is not None and not self._is_canonical_orgpath(current):
            plan.operations.append(
                PlannedOperation(
                    op=OP_DEVICE_PHANTOM,
                    target=target.computer_name,
                    reason=(
                        f"Entra device extensionAttribute1={current!r} fails "
                        "format or codebook check. Governance review required; "
                        "NOT auto-applied."
                    ),
                    plane=plane.name,
                    canonical_orgpath=target.orgpath,
                    current_value=current,
                    target_object_id=device.get("id"),
                )
            )
            return

        plan.operations.append(
            PlannedOperation(
                op=OP_DEVICE_EXT_CREATE if current is None else OP_DEVICE_EXT_UPDATE,
                target=target.computer_name,
                reason=(
                    "extensionAttribute1 missing"
                    if current is None
                    else f"extensionAttribute1 drift: canonical='{target.orgpath}' tenant='{current}'"
                ),
                plane=plane.name,
                canonical_orgpath=target.orgpath,
                current_value=current,
                target_object_id=device.get("id"),
                body=self._render_graph_body(plane, target.orgpath),
                endpoint=self._render_endpoint(
                    plane.endpoint_template,
                    object_id=device.get("id", "{unresolved}"),
                ),
            )
        )

    def _plan_arc_tag(
        self,
        target: DeviceOrgPathTarget,
        plane: DevicePlane,
        arc_by_name: Mapping[str, Dict[str, Any]],
        plan: DeviceOrgPathPlan,
    ) -> None:
        assert target.orgpath is not None
        arc = arc_by_name.get(target.computer_name)
        if arc is None:
            plan.operations.append(
                PlannedOperation(
                    op=OP_ARC_TAG_CREATE,
                    target=target.computer_name,
                    reason=(
                        "Arc resource expected per canon but not found in "
                        "subscription — plan the ARM tag write for when the "
                        "server enrolls."
                    ),
                    plane=plane.name,
                    canonical_orgpath=target.orgpath,
                    target_object_id=target.arc_resource_id,
                    body=self._render_arm_tag_body(plane, target.orgpath),
                    endpoint=self._render_endpoint(
                        plane.endpoint_template,
                        arm_resource_id=target.arc_resource_id or "{unresolved}",
                    ),
                )
            )
            return

        current = (arc.get("tags") or {}).get(self._registry.arm_tag.key)
        if current == target.orgpath:
            return

        if current is not None and not self._is_canonical_orgpath(current):
            plan.operations.append(
                PlannedOperation(
                    op=OP_ARC_PHANTOM,
                    target=target.computer_name,
                    reason=(
                        f"Arc tag OrgPath={current!r} fails format or codebook "
                        "check. Governance review required; NOT auto-applied."
                    ),
                    plane=plane.name,
                    canonical_orgpath=target.orgpath,
                    current_value=current,
                    target_object_id=arc.get("id"),
                )
            )
            return

        plan.operations.append(
            PlannedOperation(
                op=OP_ARC_TAG_CREATE if current is None else OP_ARC_TAG_UPDATE,
                target=target.computer_name,
                reason=(
                    "OrgPath tag missing"
                    if current is None
                    else f"OrgPath tag drift: canonical='{target.orgpath}' tenant='{current}'"
                ),
                plane=plane.name,
                canonical_orgpath=target.orgpath,
                current_value=current,
                target_object_id=arc.get("id"),
                body=self._render_arm_tag_body(plane, target.orgpath),
                endpoint=self._render_endpoint(
                    plane.endpoint_template,
                    arm_resource_id=arc.get("id", "{unresolved}"),
                ),
            )
        )

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------
    def apply(
        self,
        plan: DeviceOrgPathPlan,
        dry_run: bool = True,
    ) -> DeviceOrgPathReport:
        report = DeviceOrgPathReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            dry_run=dry_run,
        )
        for op in plan.operations:
            if op.op in OPS_GOVERNANCE_REVIEW:
                report.results.append(
                    OperationResult(
                        op=op.op,
                        target=op.target,
                        status="skipped-manual",
                        detail=("MOD_C §Phantom OrgPath: governance review required; never auto-applied."),
                    )
                )
                continue
            if op.op in OPS_SKIP:
                report.results.append(
                    OperationResult(
                        op=op.op,
                        target=op.target,
                        status="skipped-no-plane",
                        detail=op.reason,
                    )
                )
                continue
            if dry_run:
                report.results.append(
                    OperationResult(
                        op=op.op,
                        target=op.target,
                        status="skipped-dry-run",
                        detail=f"Dry run — would call {op.endpoint}.",
                    )
                )
                continue
            try:
                self._execute(op)
                report.results.append(
                    OperationResult(
                        op=op.op,
                        target=op.target,
                        status="written",
                    )
                )
            except Exception as exc:  # pragma: no cover - network path
                logger.exception("Apply failed for %s", op.target)
                report.results.append(
                    OperationResult(
                        op=op.op,
                        target=op.target,
                        status="failed",
                        detail=str(exc),
                    )
                )
        return report

    def reconcile(
        self,
        targets: List[DeviceOrgPathTarget],
        current_entra_devices: Optional[List[Dict[str, Any]]] = None,
        current_arc_resources: Optional[List[Dict[str, Any]]] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        plan = self.plan(
            targets=targets,
            current_entra_devices=current_entra_devices,
            current_arc_resources=current_arc_resources,
        )
        report = self.apply(plan, dry_run=dry_run)
        return {"plan": plan.to_dict(), "report": report.to_dict()}

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def _render_graph_body(
        self,
        plane: DevicePlane,
        orgpath: str,
    ) -> Dict[str, Any]:
        return {
            "onPremisesExtensionAttributes": {
                "extensionAttribute1": orgpath,
            }
        }

    def _render_arm_tag_body(
        self,
        plane: DevicePlane,
        orgpath: str,
    ) -> Dict[str, Any]:
        return {"tags": {self._registry.arm_tag.key: orgpath}}

    def _render_endpoint(self, template: str, **kwargs: str) -> str:
        return template.format(**kwargs)

    def _is_canonical_orgpath(self, value: str) -> bool:
        return self._codebook.has_format(value) and self._codebook.is_active(value)

    # ------------------------------------------------------------------
    # Graph / ARM I/O (only exercised with dry_run=False)
    # ------------------------------------------------------------------
    def _execute(self, op: PlannedOperation) -> None:
        """Issue the write for an approved operation.

        Kept thin and dependency-injectable — callers with their own HTTP
        client or retry policy subclass the adapter and override this
        method. Default implementation is a placeholder: it raises rather
        than issuing a request, because the two write planes (Graph vs
        ARM) need different credentials, and mixing them into a single
        convenience implementation would hide the real operational
        requirement (two scoped tokens).
        """
        raise RuntimeError(
            f"{op.op} requires subclass override of _execute — Phase 4 "
            "ships the planning + dispatch surface; wiring Graph and ARM "
            "token acquisition is deliberately deferred so operators "
            "choose the credential story that fits their tenant."
        )
