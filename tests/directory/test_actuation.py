"""Write-path actuation seam tests (ADR-109 §3 / ADR-092 §3)."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from uiao.directory.actuation import (
    ActuationDisabled,
    ActuationError,
    FacetActuator,
    FacetWriteAdapter,
)
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


# ---------------------------------------------------------------------------
# FacetWriteAdapter — adapts a per-principal transport into the apply protocol
# ---------------------------------------------------------------------------


def test_write_adapter_dry_run_dispatches_nothing() -> None:
    calls: list[tuple[str, str, str]] = []
    adapter = FacetWriteAdapter(write_fn=lambda dn, a, v: calls.append((dn, a, v)))
    result = adapter.apply((_op(),), dry_run=True)
    assert result.dry_run and result.sent_count == 0
    assert calls == []  # dry-run never touches the transport


def test_write_adapter_applies_via_write_fn() -> None:
    calls: list[tuple[str, str, str]] = []
    adapter = FacetWriteAdapter(write_fn=lambda dn, a, v: calls.append((dn, a, v)))
    result = adapter.apply((_op(),), dry_run=False)
    assert result.sent_count == 1
    assert calls == [("cn=alice", "extensionAttribute2", "IT")]


def test_write_adapter_remove_passes_empty_value() -> None:
    calls: list[tuple[str, str, str]] = []
    adapter = FacetWriteAdapter(write_fn=lambda dn, a, v: calls.append((dn, a, v)))
    remove = FacetOperation(
        facet="department", attribute="extensionAttribute2", op="remove", value=None, target="cn=alice"
    )
    adapter.apply((remove,), dry_run=False)
    assert calls == [("cn=alice", "extensionAttribute2", "")]  # remove (value=None) → empty value


def test_write_adapter_holds_governance_review_ops() -> None:
    calls: list[tuple[str, str, str]] = []
    adapter = FacetWriteAdapter(write_fn=lambda dn, a, v: calls.append((dn, a, v)), review_ops=frozenset({"remove"}))
    result = adapter.apply((_op("write"), _op("remove")), dry_run=False)
    assert result.sent_count == 1 and result.skipped_count == 1
    assert calls == [("cn=alice", "extensionAttribute2", "IT")]  # remove held for review


def test_write_adapter_captures_transport_errors() -> None:
    def _boom(dn: str, a: str, v: str) -> None:
        raise RuntimeError("connection reset")

    adapter = FacetWriteAdapter(write_fn=_boom)
    result = adapter.apply((_op(),), dry_run=False)
    assert result.error_count == 1 and result.sent_count == 0
    assert "connection reset" in result.errors[0][1]


def test_router_resolver_stamps_principal_metadata() -> None:
    # With a principal_resolver, the routed FacetOperation carries the real
    # (principal_id, principal_type) in metadata — the LDAP target DN is unchanged.
    def resolver(dn: str) -> tuple[str, str] | None:
        return ("alice@uiao.gov", "user")

    router = WriteRouter(dry_run=True, principal_resolver=resolver)
    req = ModifyRequest(
        message_id=1,
        object="cn=alice,ou=people,dc=agd,dc=uiao,dc=gov",
        changes=(Modification(ModifyOp.REPLACE, "uiaoOrgPathRegion", ("NCR",)),),
    )
    result = router.route(req)
    op = result.plan.operations[0]
    assert op.metadata["principal_id"] == "alice@uiao.gov"
    assert op.metadata["principal_type"] == "user"
    assert op.target == "cn=alice,ou=people,dc=agd,dc=uiao,dc=gov"  # DN target preserved


def test_router_without_resolver_leaves_metadata_empty() -> None:
    router = WriteRouter(dry_run=True)
    req = ModifyRequest(
        message_id=1,
        object="cn=alice,dc=x",
        changes=(Modification(ModifyOp.REPLACE, "uiaoOrgPathRegion", ("NCR",)),),
    )
    op = router.route(req).plan.operations[0]
    assert dict(op.metadata) == {}


def test_write_adapter_drives_actuator_end_to_end() -> None:
    # The provider-write seam the CLI --apply path wires: transport.modify →
    # FacetWriteAdapter → FacetActuator(enabled) → WriteRouter(apply).
    calls: list[tuple[str, str, str]] = []
    actuator = FacetActuator(FacetWriteAdapter(write_fn=lambda dn, a, v: calls.append((dn, a, v))), enabled=True)
    router = WriteRouter(dry_run=False, apply_fn=actuator.as_apply_fn())
    req = ModifyRequest(
        message_id=1,
        object="cn=bob,ou=people,dc=agd,dc=uiao,dc=gov",
        changes=(Modification(ModifyOp.REPLACE, "uiaoOrgPathDepartment", ("IT",)),),
    )
    result = router.route(req)
    assert result.applied and not result.refused
    assert calls == [("cn=bob,ou=people,dc=agd,dc=uiao,dc=gov", "extensionAttribute2", "IT")]
