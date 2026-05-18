"""
src/uiao/orchestrator/provisioner.py
------------------------------------
Deterministic Provisioner per UIAO_178.

Canonical eight-step pipeline for change-making (modernization-class)
flows over Entra and Azure. The provisioner does not implement the
side effects itself; it orchestrates the canonical functions
(UIAO_180) in the canonical order, computes per-step deltas, and
emits structured `ProvisioningStepRecord`s.

The eight steps are fixed (UIAO_178 §Eight-step pipeline). Each step
is optional per request but never reordered. Step preconditions are
enforced at runtime; postconditions are reported via the record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Literal, Optional, Sequence

from uiao.governance.drift_output import DriftRecord

StepName = Literal[
    "identity_create",
    "orgtree_place",
    "tag_assign",
    "access_assign",
    "resource_identity_create",
    "rbac_assign",
    "device_bind",
    "boundary_enforce",
]

STEP_ORDER: Sequence[StepName] = (
    "identity_create",
    "orgtree_place",
    "tag_assign",
    "access_assign",
    "resource_identity_create",
    "rbac_assign",
    "device_bind",
    "boundary_enforce",
)

StepOutcome = Literal["applied", "noop", "skipped", "rolled_back", "failed"]


@dataclass
class ProvisioningRequest:
    """Desired-state input for one principal-or-resource provisioning run."""

    request_id: str
    object_id: str
    # Per-step payloads. A missing entry means the step is skipped.
    steps: Dict[StepName, Dict[str, Any]] = field(default_factory=dict)
    correlation_id: Optional[str] = None


@dataclass
class ProvisioningStepRecord:
    """Per-step record emitted by the provisioner (UIAO_178 §Logging)."""

    request_id: str
    step: StepName
    object_id: str
    outcome: StepOutcome
    delta: Dict[str, Any] = field(default_factory=dict)
    drift_records: List[DriftRecord] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "step": self.step,
            "object_id": self.object_id,
            "outcome": self.outcome,
            "delta": self.delta,
            "drift_records": [r.to_dict() for r in self.drift_records],
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
        }


# A step handler accepts the request and its per-step payload, and
# returns (delta, drift_records). It MUST be idempotent on the supplied
# payload. Raising any exception triggers rollback.
StepHandler = Callable[
    [ProvisioningRequest, Dict[str, Any]],
    "tuple[Dict[str, Any], List[DriftRecord]]",
]

RollbackHandler = Callable[
    [ProvisioningRequest, Dict[str, Any], Dict[str, Any]],
    None,
]


@dataclass
class StepBinding:
    """A handler + optional rollback for one canonical step."""

    handler: StepHandler
    rollback: Optional[RollbackHandler] = None


class DeterministicProvisioner:
    """Runs the eight canonical provisioning steps in fixed order.

    Steps are pluggable: callers register handlers per step. A step
    with no registered handler and no payload is silently skipped; a
    step with a payload but no handler raises at run time.
    """

    def __init__(self, bindings: Optional[Dict[StepName, StepBinding]] = None) -> None:
        self._bindings: Dict[StepName, StepBinding] = dict(bindings or {})

    def register(
        self,
        step: StepName,
        handler: StepHandler,
        rollback: Optional[RollbackHandler] = None,
    ) -> None:
        self._bindings[step] = StepBinding(handler=handler, rollback=rollback)

    def run(self, request: ProvisioningRequest) -> List[ProvisioningStepRecord]:
        """Execute the pipeline. Returns one record per step touched."""
        records: List[ProvisioningStepRecord] = []
        rollback_stack: List[ProvisioningStepRecord] = []

        for step in STEP_ORDER:
            payload = request.steps.get(step)
            binding = self._bindings.get(step)

            if payload is None:
                records.append(
                    ProvisioningStepRecord(
                        request_id=request.request_id,
                        step=step,
                        object_id=request.object_id,
                        outcome="skipped",
                    )
                )
                continue

            if binding is None:
                record = ProvisioningStepRecord(
                    request_id=request.request_id,
                    step=step,
                    object_id=request.object_id,
                    outcome="failed",
                    error=f"no handler registered for step {step!r}",
                )
                records.append(record)
                self._rollback(records, rollback_stack, request)
                return records

            try:
                delta, drift = binding.handler(request, payload)
            except Exception as exc:  # noqa: BLE001 — boundary point
                records.append(
                    ProvisioningStepRecord(
                        request_id=request.request_id,
                        step=step,
                        object_id=request.object_id,
                        outcome="failed",
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                self._rollback(records, rollback_stack, request)
                return records

            outcome: StepOutcome = "noop" if not delta else "applied"
            record = ProvisioningStepRecord(
                request_id=request.request_id,
                step=step,
                object_id=request.object_id,
                outcome=outcome,
                delta=delta,
                drift_records=list(drift),
            )
            records.append(record)
            if outcome == "applied":
                rollback_stack.append(record)

        return records

    def _rollback(
        self,
        records: List[ProvisioningStepRecord],
        rollback_stack: List[ProvisioningStepRecord],
        request: ProvisioningRequest,
    ) -> None:
        """Best-effort rollback in reverse order."""
        while rollback_stack:
            forward = rollback_stack.pop()
            binding = self._bindings.get(forward.step)
            if binding is None or binding.rollback is None:
                records.append(
                    ProvisioningStepRecord(
                        request_id=request.request_id,
                        step=forward.step,
                        object_id=request.object_id,
                        outcome="rolled_back",
                        delta={},
                        error="no rollback registered",
                    )
                )
                continue
            try:
                payload = request.steps.get(forward.step, {})
                binding.rollback(request, payload, forward.delta)
                records.append(
                    ProvisioningStepRecord(
                        request_id=request.request_id,
                        step=forward.step,
                        object_id=request.object_id,
                        outcome="rolled_back",
                        delta=forward.delta,
                    )
                )
            except Exception as exc:  # noqa: BLE001 — rollback is best-effort
                records.append(
                    ProvisioningStepRecord(
                        request_id=request.request_id,
                        step=forward.step,
                        object_id=request.object_id,
                        outcome="failed",
                        delta=forward.delta,
                        error=f"rollback failure: {type(exc).__name__}: {exc}",
                    )
                )
