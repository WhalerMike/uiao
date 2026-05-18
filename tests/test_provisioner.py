"""Tests for src/uiao/orchestrator/provisioner.py (UIAO_178)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pytest

from uiao.governance.drift_output import DriftRecord
from uiao.orchestrator.provisioner import (
    STEP_ORDER,
    DeterministicProvisioner,
    ProvisioningRequest,
    ProvisioningStepRecord,
    StepBinding,
)


def _noop_handler(_: ProvisioningRequest, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[DriftRecord]]:
    return ({}, [])


def _change_handler(
    _: ProvisioningRequest, payload: Dict[str, Any]
) -> Tuple[Dict[str, Any], List[DriftRecord]]:
    # Echo payload as the delta -> outcome=applied
    return (dict(payload), [])


def _failing_handler(_: ProvisioningRequest, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[DriftRecord]]:
    raise RuntimeError("simulated failure")


def test_step_order_is_canonical_eight_steps():
    assert list(STEP_ORDER) == [
        "identity_create",
        "orgtree_place",
        "tag_assign",
        "access_assign",
        "resource_identity_create",
        "rbac_assign",
        "device_bind",
        "boundary_enforce",
    ]


def test_request_with_no_steps_produces_eight_skipped_records():
    provisioner = DeterministicProvisioner()
    req = ProvisioningRequest(request_id="r1", object_id="u-1")
    records = provisioner.run(req)
    assert len(records) == 8
    assert all(r.outcome == "skipped" for r in records)
    assert [r.step for r in records] == list(STEP_ORDER)


def test_request_with_payload_runs_handler_and_emits_applied():
    provisioner = DeterministicProvisioner()
    provisioner.register("identity_create", _change_handler)
    req = ProvisioningRequest(
        request_id="r1", object_id="u-1", steps={"identity_create": {"upn": "alice@a"}}
    )
    records = provisioner.run(req)
    by_step = {r.step: r for r in records}
    assert by_step["identity_create"].outcome == "applied"
    assert by_step["identity_create"].delta == {"upn": "alice@a"}
    # Other seven steps are skipped (no payload)
    for step in STEP_ORDER:
        if step != "identity_create":
            assert by_step[step].outcome == "skipped"


def test_handler_returning_empty_delta_is_noop():
    provisioner = DeterministicProvisioner()
    provisioner.register("identity_create", _noop_handler)
    req = ProvisioningRequest(
        request_id="r1", object_id="u-1", steps={"identity_create": {"upn": "alice"}}
    )
    records = provisioner.run(req)
    by_step = {r.step: r for r in records}
    assert by_step["identity_create"].outcome == "noop"


def test_missing_handler_for_requested_step_fails():
    provisioner = DeterministicProvisioner()
    req = ProvisioningRequest(
        request_id="r1", object_id="u-1", steps={"identity_create": {"upn": "alice"}}
    )
    records = provisioner.run(req)
    failed = [r for r in records if r.outcome == "failed"]
    assert len(failed) == 1
    assert failed[0].step == "identity_create"
    assert "no handler registered" in (failed[0].error or "")


def test_failure_halts_pipeline_and_runs_rollback_in_reverse():
    rollbacks: List[str] = []

    def rb_step1(_: ProvisioningRequest, payload: Dict[str, Any], delta: Dict[str, Any]) -> None:
        rollbacks.append("identity_create")

    def rb_step2(_: ProvisioningRequest, payload: Dict[str, Any], delta: Dict[str, Any]) -> None:
        rollbacks.append("orgtree_place")

    provisioner = DeterministicProvisioner()
    provisioner.register("identity_create", _change_handler, rollback=rb_step1)
    provisioner.register("orgtree_place", _change_handler, rollback=rb_step2)
    provisioner.register("tag_assign", _failing_handler)

    req = ProvisioningRequest(
        request_id="r1",
        object_id="u-1",
        steps={
            "identity_create": {"upn": "alice"},
            "orgtree_place": {"org_path": "ORG-A"},
            "tag_assign": {"uiao.org.path": "ORG-A"},
        },
    )
    records = provisioner.run(req)
    outcomes = [(r.step, r.outcome) for r in records]
    # First two applied, third failed, then rollbacks in reverse order
    assert ("identity_create", "applied") in outcomes
    assert ("orgtree_place", "applied") in outcomes
    assert ("tag_assign", "failed") in outcomes
    rolled_back = [r.step for r in records if r.outcome == "rolled_back"]
    assert rolled_back == ["orgtree_place", "identity_create"]
    assert rollbacks == ["orgtree_place", "identity_create"]


def test_idempotency_second_run_with_converged_handler_is_noop():
    """Re-invoking with a handler that returns no delta produces all-noop."""
    provisioner = DeterministicProvisioner()
    provisioner.register("identity_create", _noop_handler)
    provisioner.register("orgtree_place", _noop_handler)
    req = ProvisioningRequest(
        request_id="r1",
        object_id="u-1",
        steps={"identity_create": {"upn": "alice"}, "orgtree_place": {"org": "X"}},
    )
    first = provisioner.run(req)
    second = provisioner.run(req)
    first_outcomes = [(r.step, r.outcome) for r in first]
    second_outcomes = [(r.step, r.outcome) for r in second]
    assert first_outcomes == second_outcomes


def test_step_record_to_dict_serialises_drift_records():
    rec = ProvisioningStepRecord(
        request_id="r",
        step="tag_assign",
        object_id="u",
        outcome="applied",
        delta={"uiao.org.path": "ORG-A"},
        drift_records=[
            DriftRecord(
                object_id="u",
                drift_class="DRIFT-SCHEMA",
                object_facet="tag",
                expected_value="ORG-A",
                actual_value=None,
                severity="medium",
                recommended_action="overwrite-canonical-tag",
                source_adapter="provisioner",
            )
        ],
    )
    d = rec.to_dict()
    assert d["step"] == "tag_assign"
    assert d["outcome"] == "applied"
    assert len(d["drift_records"]) == 1
    assert d["drift_records"][0]["drift_class"] == "DRIFT-SCHEMA"
