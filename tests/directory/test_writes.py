"""Write-translation tests (ADR-109) — modify -> governed FacetOperation intent."""

from __future__ import annotations

from uiao.directory.protocol import Modification, ModifyOp, ModifyRequest
from uiao.directory.writes import RouteResult, WriteRouter, translate_modify

DN = "cn=alice,ou=people,dc=agd,dc=uiao,dc=gov"


def _modify(*changes: Modification) -> ModifyRequest:
    return ModifyRequest(message_id=1, object=DN, changes=tuple(changes))


def test_replace_governed_facet_translates_to_write_op() -> None:
    plan = translate_modify(_modify(Modification(ModifyOp.REPLACE, "uiaoOrgPathDepartment", ("IT",))))
    assert not plan.refused
    assert len(plan.operations) == 1
    op = plan.operations[0]
    assert (op.facet, op.op, op.value, op.target) == ("department", "write", "IT", DN)
    assert op.attribute == "extensionAttribute2"  # the bound slot


def test_delete_translates_to_remove_op() -> None:
    plan = translate_modify(_modify(Modification(ModifyOp.DELETE, "uiaoOrgPathDepartment", ())))
    assert not plan.refused
    assert plan.operations[0].op == "remove"
    assert plan.operations[0].value is None


def test_case_insensitive_attribute_resolves() -> None:
    plan = translate_modify(_modify(Modification(ModifyOp.REPLACE, "uiaoorgpathdepartment", ("HR",))))
    assert not plan.refused
    assert plan.operations[0].facet == "department"


def test_non_governed_attribute_is_refused() -> None:
    plan = translate_modify(_modify(Modification(ModifyOp.REPLACE, "cn", ("bob",))))
    assert plan.refused
    assert "not a governed OrgPath facet" in (plan.refusal or "")


def test_ad_veneer_attribute_is_not_writable() -> None:
    # ADR-110 §4: synthesized AD attributes are read-only / non-governed, so a
    # write to one is refused (they are not OrgPath facets).
    plan = translate_modify(_modify(Modification(ModifyOp.REPLACE, "sAMAccountName", ("x",))))
    assert plan.refused
    plan_sid = translate_modify(_modify(Modification(ModifyOp.REPLACE, "objectSid", ("S-1-5-21-1-2-3-4",))))
    assert plan_sid.refused


def test_invalid_facet_value_is_refused() -> None:
    plan = translate_modify(_modify(Modification(ModifyOp.REPLACE, "uiaoOrgPathDepartment", ("NOTAREALDEPT",))))
    assert plan.refused
    assert "not valid for facet" in (plan.refusal or "")


def test_multi_valued_change_is_refused() -> None:
    plan = translate_modify(_modify(Modification(ModifyOp.REPLACE, "uiaoOrgPathDepartment", ("IT", "HR"))))
    assert plan.refused
    assert "single-valued" in (plan.refusal or "")


def test_router_dry_run_does_not_apply() -> None:
    applied: list = []
    router = WriteRouter(dry_run=True, apply_fn=applied.extend)
    result = router.route(_modify(Modification(ModifyOp.REPLACE, "uiaoOrgPathDepartment", ("IT",))))
    assert isinstance(result, RouteResult)
    assert not result.applied and not result.refused
    assert "dry-run" in result.message
    assert applied == []  # apply_fn never called in dry-run


def test_router_apply_mode_calls_apply_fn() -> None:
    applied: list = []
    router = WriteRouter(dry_run=False, apply_fn=applied.extend)
    result = router.route(_modify(Modification(ModifyOp.REPLACE, "uiaoOrgPathRegion", ("NCR",))))
    assert result.applied and not result.refused
    assert len(applied) == 1 and applied[0].facet == "region"


def test_router_refuses_without_translating() -> None:
    applied: list = []
    router = WriteRouter(dry_run=False, apply_fn=applied.extend)
    result = router.route(_modify(Modification(ModifyOp.REPLACE, "cn", ("x",))))
    assert result.refused and not result.applied
    assert applied == []  # refusal short-circuits before apply
