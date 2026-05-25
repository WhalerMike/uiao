"""Dual-transport device-plane adapter — Model C (ADR-084 §C9 Phase 5 #5).

Wraps the
:py:class:`uiao.modernization.orgtree.device_orgpath.DeviceOrgPathPlanner`
plan/apply cycle. Per-facet writes route to **two** transports based on
the operation's ``metadata["plane"]``:

* ``plane == "entra"`` → Microsoft Graph
  ``PATCH /devices/{device_id}`` with
  ``onPremisesExtensionAttributes.extensionAttribute*: <value>``
* ``plane == "arm"`` → Azure Resource Manager
  ``PATCH {arm_resource_id}?api-version=2023-03-15-preview`` with
  ``tags.<FacetName>: <value>``

Per ADR-078 / ADR-038, this dual-transport pattern is preserved from
the retired single-string adapter — only the write surface changes
(single composite write → 10 per-facet writes).

Per ADR-084 §C5 the deferred cross-surface per-facet equality check
(device with both planes carrying the same facet values) is not
implemented here; it's runtime-detected in the future cross-surface
ADR.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable

from uiao.modernization.orgtree.device_orgpath import DeviceOrgPathPlanner
from uiao.modernization.orgtree.types import ApplyResult, FacetOperation

# Two transports: graph_transport for Entra (Graph), arm_transport for
# Arc (ARM). Either may be None for tests that exercise only one
# plane.
Transport = Callable[[str, str, dict | None], dict]


class EntraDeviceOrgPathAdapter:
    """Plan/apply adapter for per-facet device-plane OrgPath writes.

    The adapter batches per-facet writes for the same ``(device_id,
    plane)`` into a single PATCH — Graph and ARM both accept multi-
    attribute body updates, so 10 per-facet writes for one device =
    one transport call.
    """

    def __init__(
        self,
        planner: DeviceOrgPathPlanner,
        graph_transport: Transport | None = None,
        arm_transport: Transport | None = None,
        arm_api_version: str = "2023-03-15-preview",
    ) -> None:
        self.planner = planner
        self.graph_transport = graph_transport
        self.arm_transport = arm_transport
        self.arm_api_version = arm_api_version

    @property
    def governance_review_ops(self) -> frozenset[str]:
        """Device writes have no governance-review category — all autonomously remediable."""
        return frozenset()

    def plan(self, assignments: Iterable) -> list[FacetOperation]:
        return self.planner.plan(assignments)

    def apply(
        self,
        operations: Iterable[FacetOperation],
        *,
        dry_run: bool = True,
    ) -> ApplyResult:
        ops = tuple(operations)
        sent: list[FacetOperation] = []
        skipped: list[FacetOperation] = []
        errors: list[tuple[FacetOperation, str]] = []

        if dry_run:
            return ApplyResult(
                operations=ops,
                sent=(),
                skipped=ops,
                errors=(),
                dry_run=True,
            )

        # Batch per (device_id, plane) — one PATCH per device per plane.
        batches: dict[tuple[str, str], list[FacetOperation]] = defaultdict(list)
        for op in ops:
            plane = op.metadata.get("plane")
            if plane not in ("entra", "arm"):
                errors.append((op, f"unknown plane '{plane}'"))
                continue
            batches[(op.target, plane)].append(op)

        for (device_id, plane), batch_ops in batches.items():
            transport = self.graph_transport if plane == "entra" else self.arm_transport
            if transport is None:
                for op in batch_ops:
                    errors.append((op, f"no {plane} transport configured"))
                continue
            try:
                self._dispatch_batch(transport, device_id, plane, batch_ops)
                sent.extend(batch_ops)
            except Exception as exc:  # pragma: no cover
                for op in batch_ops:
                    errors.append((op, str(exc)))

        return ApplyResult(
            operations=ops,
            sent=tuple(sent),
            skipped=tuple(skipped),
            errors=tuple(errors),
            dry_run=False,
        )

    def _dispatch_batch(
        self,
        transport: Transport,
        device_id: str,
        plane: str,
        ops: list[FacetOperation],
    ) -> None:
        if plane == "entra":
            body = {"onPremisesExtensionAttributes": {op.attribute: op.value for op in ops}}
            transport("PATCH", f"/devices/{device_id}", body)
        elif plane == "arm":
            body = {"tags": {op.attribute.removeprefix("tags."): op.value for op in ops}}
            transport(
                "PATCH",
                f"{device_id}?api-version={self.arm_api_version}",
                body,
            )
