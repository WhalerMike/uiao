"""Entra/Graph facet-writer tests — the AGD --apply Entra target (ADR-109)."""

from __future__ import annotations

from typing import Any

from uiao.adapters.entra_facet_writer import EntraFacetWriter
from uiao.directory.actuation import FacetActuator
from uiao.directory.protocol import Modification, ModifyOp, ModifyRequest
from uiao.directory.writes import WriteRouter
from uiao.modernization.orgtree.types import FacetOperation


class _RecordingGraph:
    """A fake GraphTransport callable that records (method, path, body)."""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []
        self._fail = fail

    def __call__(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        if self._fail:
            raise RuntimeError("graph 403")
        self.calls.append((method, path, body))
        return {}


def _op(
    *, op: str = "write", value: str | None = "NCR", pid: str | None = "alice@uiao.gov", ptype: str | None = "user"
) -> FacetOperation:
    meta = {}
    if pid is not None:
        meta["principal_id"] = pid
    if ptype is not None:
        meta["principal_type"] = ptype
    return FacetOperation(
        facet="region", attribute="extensionAttribute1", op=op, value=value, target="cn=alice,dc=x", metadata=meta
    )


def test_user_write_patches_onprem_extension_attributes() -> None:
    graph = _RecordingGraph()
    result = EntraFacetWriter(graph).apply((_op(),), dry_run=False)
    assert result.sent_count == 1
    assert graph.calls == [
        ("PATCH", "/users/alice@uiao.gov", {"onPremisesExtensionAttributes": {"extensionAttribute1": "NCR"}})
    ]


def test_device_write_targets_devices_collection() -> None:
    graph = _RecordingGraph()
    EntraFacetWriter(graph).apply((_op(pid="dev-123", ptype="device"),), dry_run=False)
    assert graph.calls[0][1] == "/devices/dev-123"


def test_remove_sends_null_to_clear_the_slot() -> None:
    graph = _RecordingGraph()
    EntraFacetWriter(graph).apply((_op(op="remove", value=None),), dry_run=False)
    assert graph.calls[0][2] == {"onPremisesExtensionAttributes": {"extensionAttribute1": None}}


def test_dry_run_touches_nothing() -> None:
    graph = _RecordingGraph()
    result = EntraFacetWriter(graph).apply((_op(),), dry_run=True)
    assert result.dry_run and result.sent_count == 0
    assert graph.calls == []


def test_unresolved_principal_is_an_error_not_a_write() -> None:
    graph = _RecordingGraph()
    result = EntraFacetWriter(graph).apply((_op(pid=None),), dry_run=False)
    assert result.error_count == 1 and result.sent_count == 0
    assert graph.calls == []  # never dispatched


def test_servicePrincipal_is_unsupported() -> None:
    graph = _RecordingGraph()
    result = EntraFacetWriter(graph).apply((_op(ptype="servicePrincipal"),), dry_run=False)
    assert result.error_count == 1 and graph.calls == []


def test_governance_review_ops_are_held() -> None:
    graph = _RecordingGraph()
    writer = EntraFacetWriter(graph, review_ops=frozenset({"remove"}))
    result = writer.apply((_op(op="write"), _op(op="remove", value=None)), dry_run=False)
    assert result.sent_count == 1 and result.skipped_count == 1
    assert len(graph.calls) == 1


def test_transport_errors_captured_per_op() -> None:
    result = EntraFacetWriter(_RecordingGraph(fail=True)).apply((_op(),), dry_run=False)
    assert result.error_count == 1 and "graph 403" in result.errors[0][1]


def test_router_resolver_to_entra_end_to_end() -> None:
    # modify → router(resolver stamps id+type) → actuator → EntraFacetWriter → PATCH.
    graph = _RecordingGraph()
    actuator = FacetActuator(EntraFacetWriter(graph), enabled=True)

    def resolver(dn: str) -> tuple[str, str] | None:
        return ("bob@uiao.gov", "user") if dn.startswith("cn=bob") else None

    router = WriteRouter(dry_run=False, apply_fn=actuator.as_apply_fn(), principal_resolver=resolver)
    req = ModifyRequest(
        message_id=1,
        object="cn=bob,ou=people,dc=agd,dc=uiao,dc=gov",
        changes=(Modification(ModifyOp.REPLACE, "uiaoOrgPathRegion", ("NCR",)),),
    )
    result = router.route(req)
    assert result.applied
    assert graph.calls == [
        ("PATCH", "/users/bob@uiao.gov", {"onPremisesExtensionAttributes": {"extensionAttribute1": "NCR"}})
    ]
