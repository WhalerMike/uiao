"""Write-path actuation seam tests (ADR-109 §3 / ADR-092 §3)."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from uiao.directory.actuation import ActuationDisabled, ActuationError, FacetActuator
from uiao.directory.protocol import Modification, ModifyOp, ModifyRequest
from uiao.directory.writes import WriteRouter
from uiao.modernization.orgtree.types import ApplyResult, FacetOperation


class _FakeAdapter:
    """A Phase-5-shaped adapter that records what it was asked to apply."""

    def __init__(self, *, review_ops: frozenset[str] = frozenset(), fail: bool = False) -> None:
        self._review = review_ops
        self._fail = fail
        self.applied: list[FacetOperation] = []

    @property
    def governance_review_ops(self) -> frozenset[str]:
        return self._review

    def apply(self, operations: Iterable[FacetOperation], *, dry_run: bool = True) -> ApplyResult:
        ops = tuple(operations)
        if dry_run:
            return ApplyResult.dry(ops)
        sent = tuple(o for o in ops if o.op not in self._review)
        held = tuple(o for o in ops if o.op in self._review)
        errors = tuple((o, "boom") for o in sent) if self._fail else ()
        self.applied.extend(o for o in sent if not self._fail)
        return ApplyResult(operations=ops, sent=sent, skipped=held, errors=errors, dry_run=False)


def _op(op: str = "write") -> FacetOperation:
    return FacetOperation(facet="department", attribute="extensionAttribute2", op=op, value="IT", target="cn=alice")


def test_disabled_actuator_refuses_to_apply() -> None:
    actuator = FacetActuator(adapter=_FakeAdapter())  # enabled defaults False
    with pytest.raises(ActuationDisabled):
        actuator.apply((_op(),))


def test_enabled_actuator_applies_through_adapter() -> None:
    adapter = _FakeAdapter()
    actuator = FacetActuator(adapter=adapter, enabled=True)
    result = actuator.apply((_op(),))
    assert result.sent_count == 1
    assert adapter.applied[0].facet == "department"
    assert len(actuator.audit) == 1  # auditable


def test_governance_review_ops_are_held_not_applied() -> None:
    adapter = _FakeAdapter(review_ops=frozenset({"write"}))
    actuator = FacetActuator(adapter=adapter, enabled=True)
    result = actuator.apply((_op("write"),))
    assert result.sent_count == 0
    assert result.skipped_count == 1  # held for review, never auto-fired
    assert adapter.applied == []


def test_adapter_errors_raise_actuation_error() -> None:
    actuator = FacetActuator(adapter=_FakeAdapter(fail=True), enabled=True)
    with pytest.raises(ActuationError):
        actuator.apply((_op(),))


def test_router_with_actuator_applies_end_to_end() -> None:
    # The full ADR-109 path: modify -> translate -> route(dry_run=False) ->
    # actuator.as_apply_fn() -> adapter.apply. Uses a real governed facet.
    adapter = _FakeAdapter()
    actuator = FacetActuator(adapter=adapter, enabled=True)
    router = WriteRouter(dry_run=False, apply_fn=actuator.as_apply_fn())
    req = ModifyRequest(
        message_id=1,
        object="cn=alice,ou=people,dc=agd,dc=uiao,dc=gov",
        changes=(Modification(ModifyOp.REPLACE, "uiaoOrgPathDepartment", ("IT",)),),
    )
    result = router.route(req)
    assert result.applied and not result.refused
    assert adapter.applied[0].facet == "department"
    assert adapter.applied[0].value == "IT"


def test_router_with_disabled_actuator_stays_plan_only() -> None:
    # A WriteRouter wired to a disabled actuator surfaces the gate: routing in
    # apply-mode raises ActuationDisabled (no silent application).
    actuator = FacetActuator(adapter=_FakeAdapter())  # disabled
    router = WriteRouter(dry_run=False, apply_fn=actuator.as_apply_fn())
    req = ModifyRequest(
        message_id=1,
        object="cn=alice,dc=x",
        changes=(Modification(ModifyOp.REPLACE, "uiaoOrgPathRegion", ("NCR",)),),
    )
    with pytest.raises(ActuationDisabled):
        router.route(req)
