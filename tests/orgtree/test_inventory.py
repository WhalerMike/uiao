"""Tests for the brownfield OrgPath inventory core
(``uiao.modernization.orgtree.inventory``).

Covers normalization of Entra device / Arc machine objects, capture-status
classification (complete / partial / absent), the source-precedence proposal
chain with codebook validation, snapshot/worklist emission, and the paged live
read helpers (with a fake transport). All pure — no network.
"""

from __future__ import annotations

from uiao.modernization.orgtree.codebook import load_codebook
from uiao.modernization.orgtree.inventory import (
    CAPTURE_ABSENT,
    CAPTURE_COMPLETE,
    CAPTURE_PARTIAL,
    PLANE_ARM,
    PLANE_ENTRA,
    SOURCE_ASSET,
    SOURCE_OWNER,
    build_inventory,
    classify_device,
    device_from_entra,
    machine_from_arm,
    read_arm_machines,
    read_entra_devices,
)

CB = load_codebook()

_ALL_SLOTS = {f"extensionAttribute{i}": "x" for i in range(1, 11)}
_NINE_SLOTS = {f"extensionAttribute{i}": "x" for i in range(2, 11)}  # region (slot 1) missing


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_entra_device_reads_orgpath_slots_and_owner() -> None:
    raw = {
        "id": "dev-1",
        "displayName": "WS-1",
        "onPremisesExtensionAttributes": {"extensionAttribute1": "NCR", "extensionAttribute99": "ignored"},
        "registeredOwners": [{"id": "user-9"}],
    }
    rec = device_from_entra(raw, CB)
    assert rec.target_id == "dev-1"
    assert rec.plane == PLANE_ENTRA
    assert rec.current_slots == {"extensionAttribute1": "NCR"}  # only OrgPath slots, non-empty
    assert rec.correlation_keys["hostname"] == "WS-1"
    assert rec.correlation_keys["owner_id"] == "user-9"


def test_arc_machine_reads_tags_to_slots() -> None:
    raw = {
        "id": "/subscriptions/s/resourceGroups/rg/providers/Microsoft.HybridCompute/machines/srv1",
        "name": "srv1",
        "tags": {"Region": "EASTUS", "Department": "IT", "Unrelated": "keep-out"},
    }
    rec = machine_from_arm(raw, CB)
    assert rec.plane == PLANE_ARM
    assert rec.target_id.endswith("/machines/srv1")  # full ARM resource id preserved
    # Region -> slot1, Department -> slot2; unrelated tag ignored.
    assert rec.current_slots == {"extensionAttribute1": "EASTUS", "extensionAttribute2": "IT"}


# ---------------------------------------------------------------------------
# Capture-status classification
# ---------------------------------------------------------------------------


def test_absent_when_no_orgpath() -> None:
    rec = device_from_entra({"id": "d", "displayName": "n", "onPremisesExtensionAttributes": {}}, CB)
    res = classify_device(rec, CB)
    assert res.status == CAPTURE_ABSENT
    # Nine required facets. Optional (allow_empty) facets never count as
    # missing: the ADR-137 extension facets, and term_date, which is empty by
    # design for anyone still employed — the survey used to demand one.
    assert len(res.missing_facets) == 9
    assert "term_date" not in res.missing_facets
    assert "admin_tier" not in res.missing_facets
    assert res.needs_backfill is True


def test_complete_when_all_slots_set() -> None:
    rec = device_from_entra({"id": "d", "displayName": "n", "onPremisesExtensionAttributes": _ALL_SLOTS}, CB)
    res = classify_device(rec, CB)
    assert res.status == CAPTURE_COMPLETE
    assert res.missing_facets == ()
    assert res.needs_backfill is False


def test_partial_when_some_slots_missing() -> None:
    rec = device_from_entra({"id": "d", "displayName": "n", "onPremisesExtensionAttributes": _NINE_SLOTS}, CB)
    res = classify_device(rec, CB)
    assert res.status == CAPTURE_PARTIAL
    assert res.missing_facets == ("region",)  # slot1 == region


# ---------------------------------------------------------------------------
# Proposal resolution + codebook validation
# ---------------------------------------------------------------------------


def _partial_device(host: str = "WS-1", owner: str = "user-9"):
    return device_from_entra(
        {
            "id": "dev-1",
            "displayName": host,
            "onPremisesExtensionAttributes": _NINE_SLOTS,  # only region missing
            "registeredOwners": [{"id": owner}],
        },
        CB,
    )


def test_asset_map_resolves_and_validates() -> None:
    res = classify_device(_partial_device(), CB, asset_map={"WS-1": {"region": "NCR"}})
    assert res.source == SOURCE_ASSET
    assert res.proposed_facets == {"region": "NCR"}
    assert res.resolved is True  # the one missing facet is now covered
    assert res.missing_after_proposal == ()


def test_owner_map_used_as_fallback() -> None:
    res = classify_device(_partial_device(), CB, owner_map={"user-9": {"region": "EASTUS"}})
    assert res.source == SOURCE_OWNER
    assert res.proposed_facets == {"region": "EASTUS"}


def test_asset_map_wins_over_owner_map() -> None:
    res = classify_device(
        _partial_device(),
        CB,
        asset_map={"WS-1": {"region": "NCR"}},
        owner_map={"user-9": {"region": "EASTUS"}},
    )
    assert res.source == SOURCE_ASSET
    assert res.proposed_facets == {"region": "NCR"}


def test_invalid_proposed_value_becomes_a_finding() -> None:
    res = classify_device(_partial_device(), CB, asset_map={"WS-1": {"region": "NOT-A-REGION"}})
    assert res.proposed_facets == {}  # rejected
    assert res.findings and "region" in res.findings[0]
    assert res.resolved is False


def test_unresolved_when_no_source_matches() -> None:
    res = classify_device(_partial_device(), CB)
    assert res.source is None
    assert res.proposed_facets == {}
    assert res.unresolved_reason and "no asset-map/owner-map match" in res.unresolved_reason


# ---------------------------------------------------------------------------
# Report: snapshot + worklist
# ---------------------------------------------------------------------------


def test_report_snapshot_and_worklist() -> None:
    absent = device_from_entra({"id": "a", "displayName": "A", "onPremisesExtensionAttributes": {}}, CB)
    complete = device_from_entra({"id": "c", "displayName": "C", "onPremisesExtensionAttributes": _ALL_SLOTS}, CB)
    arc = machine_from_arm({"id": "/x/machines/s", "name": "s", "tags": {"Region": "NCR"}}, CB)

    report = build_inventory([absent, complete, arc], CB, asset_map={"A": {"region": "NCR"}})
    s = report.summary
    assert s["total"] == 3
    assert s["complete"] == 1 and s["absent"] == 1 and s["partial"] == 1
    assert s["entra"] == 2 and s["arm"] == 1
    assert s["needs_backfill"] == 2

    snap = report.to_snapshot_dict()
    assert {p["principal_id"] for p in snap["principals"]} == {"a", "c", arc.target_id}
    assert all(p["principal_type"] == "device" for p in snap["principals"])
    # current state only: the absent device carries no attributes.
    absent_principal = next(p for p in snap["principals"] if p["principal_id"] == "a")
    assert absent_principal["attributes"] == {}

    wl = report.to_worklist_dict()
    assert wl["summary"]["total"] == 3
    assert len(wl["devices"]) == 3


# ---------------------------------------------------------------------------
# Live read helpers (paging) with a fake transport
# ---------------------------------------------------------------------------


def test_read_entra_devices_follows_odata_nextlink() -> None:
    pages = [
        {"value": [{"id": "d1"}], "@odata.nextLink": "https://graph/next"},
        {"value": [{"id": "d2"}]},
    ]
    calls: list[str] = []

    def transport(method: str, path: str, body):  # noqa: ANN001
        calls.append(path)
        return pages[len(calls) - 1]

    out = read_entra_devices(transport)
    assert [d["id"] for d in out] == ["d1", "d2"]
    assert calls[0].startswith("/devices?$select=")
    assert calls[1] == "https://graph/next"  # absolute nextLink followed verbatim


def test_read_arm_machines_follows_nextlink() -> None:
    pages = [
        {"value": [{"name": "m1"}], "nextLink": "https://arm/next"},
        {"value": [{"name": "m2"}]},
    ]
    calls: list[str] = []

    def transport(method: str, path: str, body):  # noqa: ANN001
        calls.append(path)
        return pages[len(calls) - 1]

    out = read_arm_machines(transport, "sub-123")
    assert [m["name"] for m in out] == ["m1", "m2"]
    assert "sub-123" in calls[0] and "Microsoft.HybridCompute/machines" in calls[0]
    assert calls[1] == "https://arm/next"
