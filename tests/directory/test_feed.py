"""Snapshot-feed conversion tests (ADR-100): assessment → AGD principals."""

from __future__ import annotations

import pytest

from uiao.directory.dit import build_directory
from uiao.directory.feed import FeedError, principals_from_assessment


def _assessment(**facet_values: str) -> dict:
    return {
        "target_id": "alice@uiao.gov",
        "target_type": "user",
        "facet_values": dict(facet_values),
        "findings": [],
    }


def test_facet_names_rekey_onto_extension_slots() -> None:
    # region → extensionAttribute1, department → extensionAttribute2 (codebook).
    principals = principals_from_assessment([_assessment(region="NCR", department="IT")])
    assert len(principals) == 1
    attrs = principals[0]["attributes"]
    assert attrs["extensionAttribute1"] == "NCR"
    assert attrs["extensionAttribute2"] == "IT"
    assert principals[0]["principal_id"] == "alice@uiao.gov"
    assert principals[0]["principal_type"] == "user"


def test_feed_projects_through_the_dit() -> None:
    # End-to-end: assessment → principals → DIT carries the ldap-profile locator.
    principals = principals_from_assessment([_assessment(region="NCR")])
    directory = build_directory(principals)
    entry = next(e for e in directory.entries if e.dn.startswith("cn=alice"))
    assert entry.attributes["uiaoOrgPathRegion"] == ["NCR"]


def test_blank_values_and_unknown_facets_are_dropped() -> None:
    principals = principals_from_assessment([_assessment(region="", department="IT", not_a_facet="x")])
    attrs = principals[0]["attributes"]
    assert "extensionAttribute1" not in attrs  # blank dropped
    assert attrs["extensionAttribute2"] == "IT"
    assert all("not_a_facet" not in v for v in attrs)  # unknown facet dropped


def test_records_without_target_id_are_skipped() -> None:
    payload = [{"target_id": "", "target_type": "user", "facet_values": {"region": "NCR"}}]
    assert principals_from_assessment(payload) == []


def test_accepts_wrapped_results_object() -> None:
    payload = {"results": [_assessment(region="NCR")]}
    assert len(principals_from_assessment(payload)) == 1


def test_non_list_payload_raises_feed_error() -> None:
    with pytest.raises(FeedError):
        principals_from_assessment("not a list")


def test_malformed_record_raises_feed_error() -> None:
    with pytest.raises(FeedError):
        principals_from_assessment([{"target_id": "x", "facet_values": "should-be-an-object"}])
