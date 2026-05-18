"""Tests for src/uiao/identity/canonical_functions.py (UIAO_180)."""

from __future__ import annotations

from typing import Any, Dict, List


from uiao.identity import (
    GroupSpec,
    UserSpec,
    add_to_group,
    apply_tags,
    assign_rbac,
    assign_role,
    correct_tag_drift,
    create_group,
    create_user,
    delete_user,
    detect_tag_drift,
    disable_user,
    read_tags,
    remove_from_group,
    remove_role,
)


class FakeAdapter:
    """In-memory adapter implementing the thin-adapter contract."""

    ADAPTER_ID = "fake-adapter"

    def __init__(self, initial: Dict[str, Dict[str, Any]] | None = None) -> None:
        self.store: Dict[str, Dict[str, Any]] = dict(initial or {})
        self.writes: List[Dict[str, Any]] = []

    def get_state(self, object_id: str) -> Dict[str, Any]:
        return dict(self.store.get(object_id, {}))

    def set_state(self, object_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.store.setdefault(object_id, {})
        delta = {k: v for k, v in payload.items() if existing.get(k) != v}
        existing.update(payload)
        self.writes.append({"op": "set", "id": object_id, "payload": payload})
        return delta

    def apply_change(self, object_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.store.setdefault(object_id, {})
        delta = {k: v for k, v in payload.items() if existing.get(k) != v}
        # Naive merge for the test: nested `tags` dicts merge, others replace.
        for k, v in payload.items():
            if k == "tags" and isinstance(v, dict):
                existing.setdefault("tags", {}).update(v)
            else:
                existing[k] = v
        self.writes.append({"op": "apply", "id": object_id, "payload": payload})
        return delta


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------


def test_create_user_writes_when_object_absent():
    adapter = FakeAdapter()
    spec = UserSpec(
        object_id="u-1",
        user_principal_name="alice@example.gov",
        display_name="Alice",
        org_path="ORG-FIN-PAY",
        owner="alice@example.gov",
    )
    result = create_user(adapter, spec)
    assert result.outcome == "created"
    assert result.delta["userPrincipalName"] == "alice@example.gov"


def test_create_user_is_idempotent_on_second_invocation():
    adapter = FakeAdapter()
    spec = UserSpec(
        object_id="u-1",
        user_principal_name="alice@example.gov",
        display_name="Alice",
        org_path="ORG-FIN-PAY",
        owner="alice@example.gov",
    )
    first = create_user(adapter, spec)
    second = create_user(adapter, spec)
    assert first.outcome == "created"
    assert second.outcome == "noop"
    assert second.delta == {}


# ---------------------------------------------------------------------------
# disable_user / delete_user / role / group / rbac
# ---------------------------------------------------------------------------


def test_disable_user_writes_lifecycle_tag():
    adapter = FakeAdapter({"u-1": {"accountEnabled": True}})
    result = disable_user(adapter, "u-1")
    assert result.outcome == "updated"
    assert adapter.store["u-1"]["accountEnabled"] is False
    assert adapter.store["u-1"]["uiao.identity.lifecycle"] == "disabled"


def test_disable_user_idempotent_when_already_disabled():
    adapter = FakeAdapter(
        {
            "u-1": {
                "accountEnabled": False,
                "uiao.identity.lifecycle": "disabled",
            }
        }
    )
    result = disable_user(adapter, "u-1")
    assert result.outcome == "noop"
    assert result.delta == {}


def test_assign_role_carries_role_in_result():
    adapter = FakeAdapter()
    result = assign_role(adapter, "u-1", "Global Reader")
    assert result.outcome == "updated"
    assert result.role == "Global Reader"


def test_remove_role_emits_payload_with_remove_role_key():
    adapter = FakeAdapter()
    remove_role(adapter, "u-1", "Global Reader")
    assert adapter.writes[-1]["payload"] == {"remove_role": "Global Reader"}


def test_add_and_remove_from_group_target_group_id_not_user_id():
    adapter = FakeAdapter()
    add_to_group(adapter, "u-1", "g-1")
    assert adapter.writes[-1]["id"] == "g-1"
    assert adapter.writes[-1]["payload"] == {"add_member": "u-1"}
    remove_from_group(adapter, "u-1", "g-1")
    assert adapter.writes[-1]["payload"] == {"remove_member": "u-1"}


def test_create_group_idempotent_on_converged_state():
    spec = GroupSpec(object_id="g-1", display_name="Finance", membership_type="assigned")
    adapter = FakeAdapter({"g-1": {"displayName": "Finance", "membershipType": "assigned"}})
    result = create_group(adapter, spec)
    assert result.outcome == "noop"


def test_assign_rbac_carries_role_and_scope():
    adapter = FakeAdapter()
    result = assign_rbac(adapter, "mi-1", "/subscriptions/X", "Reader")
    assert result.role == "Reader"
    assert result.scope == "/subscriptions/X"


def test_delete_user_marks_deleted_flag():
    adapter = FakeAdapter({"u-1": {"accountEnabled": False}})
    result = delete_user(adapter, "u-1")
    assert result.outcome == "updated"
    assert adapter.store["u-1"]["__deleted__"] is True


# ---------------------------------------------------------------------------
# apply_tags / read_tags / detect_tag_drift / correct_tag_drift
# ---------------------------------------------------------------------------


def test_apply_tags_rejects_non_canonical_keys():
    adapter = FakeAdapter()
    result = apply_tags(adapter, "u-1", {"uiao.org.path": "ORG-A", "cost-center": "cc"})
    assert result.outcome == "failed"
    assert "cost-center" in result.delta["rejected_non_canonical_keys"]
    # And nothing was written
    assert adapter.writes == []


def test_apply_tags_writes_canonical_set():
    adapter = FakeAdapter()
    result = apply_tags(adapter, "u-1", {"uiao.org.path": "ORG-A"})
    assert result.outcome == "updated"
    assert result.written == {"uiao.org.path": "ORG-A"}


def test_read_tags_partitions_three_buckets():
    adapter = FakeAdapter(
        {
            "u-1": {
                "tags": {
                    "uiao.org.path": "ORG-A",
                    "uiao.lifecycle": "active",  # forbidden
                    "cost-center": "cc",
                }
            }
        }
    )
    result = read_tags(adapter, "u-1")
    assert result.canonical == {"uiao.org.path": "ORG-A"}
    assert result.forbidden == {"uiao.lifecycle": "active"}
    assert result.non_canonical == {"cost-center": "cc"}


def test_detect_tag_drift_returns_empty_on_converged_state():
    adapter = FakeAdapter({"u-1": {"tags": {"uiao.org.path": "ORG-A"}}})
    records = detect_tag_drift(adapter, "u-1", desired={"uiao.org.path": "ORG-A"})
    assert records == []


def test_detect_tag_drift_finds_missing_canonical_key():
    adapter = FakeAdapter({"u-1": {"tags": {}}})
    records = detect_tag_drift(adapter, "u-1", desired={"uiao.org.path": "ORG-A"})
    assert len(records) == 1
    assert records[0].source_adapter == "fake-adapter"


def test_correct_tag_drift_applies_canonical_state():
    adapter = FakeAdapter({"u-1": {"tags": {}}})
    result = correct_tag_drift(adapter, "u-1", desired={"uiao.org.path": "ORG-A"})
    assert result.outcome == "updated"
    assert result.written == {"uiao.org.path": "ORG-A"}
    assert len(result.drift_records) == 1


def test_correct_tag_drift_is_noop_when_already_converged():
    adapter = FakeAdapter({"u-1": {"tags": {"uiao.org.path": "ORG-A"}}})
    result = correct_tag_drift(adapter, "u-1", desired={"uiao.org.path": "ORG-A"})
    assert result.outcome == "noop"
    assert result.drift_records == []
