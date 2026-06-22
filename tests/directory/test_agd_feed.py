"""Tests for the AGD assessment feed (Step 1B — from-assessment wiring).

Verifies that ``principals_from_assessment`` correctly converts
``uiao orgtree assess --out`` JSON into the principal-snapshot shape, and
that the resulting DIT projection is equivalent to one built from the
hand-authored snapshot fixture.

Run with:
    pytest tests/directory/test_agd_feed.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.directory import build_directory
from uiao.directory.feed import FeedError, principals_from_assessment

SNAPSHOT_FIXTURE = Path(__file__).parent.parent / "fixtures" / "agd" / "federal-agency-snapshot.json"
ASSESSMENT_FIXTURE = Path(__file__).parent.parent / "fixtures" / "agd" / "federal-agency-assessment.json"
BASE_DN = "dc=agd,dc=uiao,dc=gov"


# ---------------------------------------------------------------------------
# Feed conversion — unit tests
# ---------------------------------------------------------------------------


class TestPrincipalsFromAssessment:
    def _assessment(self) -> list[dict]:
        return json.loads(ASSESSMENT_FIXTURE.read_text(encoding="utf-8"))

    def test_all_13_principals_converted(self):
        result = principals_from_assessment(self._assessment())
        assert len(result) == 13

    def test_accepts_wrapped_results_key(self):
        """Feed accepts both a bare list and {"results": [...]}."""
        raw = self._assessment()
        principals_bare = principals_from_assessment(raw["results"])
        principals_wrapped = principals_from_assessment(raw)
        assert len(principals_bare) == len(principals_wrapped) == 13

    def test_facet_names_converted_to_extension_attributes(self):
        """Feed translates facet names to extensionAttributeN slots."""
        result = principals_from_assessment(self._assessment())
        stratton = next(p for p in result if p["principal_id"] == "m.stratton@agency.gov")
        attrs = stratton["attributes"]
        assert attrs["extensionAttribute1"] == "NCR"  # region
        assert attrs["extensionAttribute2"] == "IT"  # department
        assert attrs["extensionAttribute3"] == "Identity"  # division
        assert attrs["extensionAttribute4"] == "Architect"  # role
        assert attrs["extensionAttribute9"] == "TS_SCI"  # clearance_level

    def test_term_date_carried_through(self):
        result = principals_from_assessment(self._assessment())
        contractor = next(p for p in result if "nguyen" in p["principal_id"])
        assert contractor["attributes"].get("extensionAttribute8") == "2026-12-31"

    def test_service_principal_type_preserved(self):
        result = principals_from_assessment(self._assessment())
        svcs = [p for p in result if p["principal_type"] == "servicePrincipal"]
        assert len(svcs) == 2

    def test_device_type_preserved(self):
        result = principals_from_assessment(self._assessment())
        devices = [p for p in result if p["principal_type"] == "device"]
        assert len(devices) == 2

    def test_unknown_facet_names_dropped(self):
        """Facets not in the codebook are silently dropped — no error."""
        payload = [
            {"target_id": "x@y.gov", "target_type": "user", "facet_values": {"region": "NCR", "not_a_facet": "ignored"}}
        ]
        result = principals_from_assessment(payload)
        assert len(result) == 1
        assert "not_a_facet" not in str(result[0]["attributes"])

    def test_empty_target_id_skipped(self):
        payload = [
            {"target_id": "", "target_type": "user", "facet_values": {"region": "NCR"}},
            {"target_id": "real@agency.gov", "target_type": "user", "facet_values": {"region": "NCR"}},
        ]
        result = principals_from_assessment(payload)
        assert len(result) == 1
        assert result[0]["principal_id"] == "real@agency.gov"

    def test_empty_facet_values_dropped(self):
        payload = [
            {
                "target_id": "x@y.gov",
                "target_type": "user",
                "facet_values": {"region": "NCR", "department": "", "division": None},
            }
        ]
        result = principals_from_assessment(payload)
        attrs = result[0]["attributes"]
        assert "extensionAttribute2" not in attrs  # department was ""
        assert "extensionAttribute3" not in attrs  # division was None

    def test_non_list_payload_raises(self):
        with pytest.raises(FeedError, match="must be a JSON list"):
            principals_from_assessment("not a list")

    def test_non_object_record_raises(self):
        with pytest.raises(FeedError, match="must be an object"):
            principals_from_assessment(["not", "objects"])


# ---------------------------------------------------------------------------
# DIT equivalence — assessment feed produces the same projection as snapshot
# ---------------------------------------------------------------------------


class TestAssessmentEquivalentToSnapshot:
    """The key Step-1B guarantee: --from-assessment and --snapshot produce
    identical Directory Information Trees for the same population."""

    def _snapshot_directory(self):
        snapshot = json.loads(SNAPSHOT_FIXTURE.read_text(encoding="utf-8"))
        return build_directory(snapshot["principals"], base_dn=BASE_DN)

    def _assessment_directory(self):
        assessment = json.loads(ASSESSMENT_FIXTURE.read_text(encoding="utf-8"))
        principals = principals_from_assessment(assessment)
        return build_directory(principals, base_dn=BASE_DN)

    def test_same_entry_count(self):
        snap_dir = self._snapshot_directory()
        assess_dir = self._assessment_directory()
        assert len(snap_dir.entries) == len(assess_dir.entries)

    def test_same_dns(self):
        snap_dns = {e.dn for e in self._snapshot_directory().entries}
        assess_dns = {e.dn for e in self._assessment_directory().entries}
        assert snap_dns == assess_dns

    def test_same_orgpath_facets_for_each_principal(self):
        """For every principal, the OrgPath attribute set must be identical."""
        snap_map = {e.dn: e.attributes for e in self._snapshot_directory().entries}
        assess_map = {e.dn: e.attributes for e in self._assessment_directory().entries}

        orgpath_attrs = {k for attrs in snap_map.values() for k in attrs if k.startswith("uiaoOrgPath")}

        mismatches = []
        for dn in snap_map:
            for attr in orgpath_attrs:
                snap_val = set(snap_map[dn].get(attr, []))
                assess_val = set(assess_map.get(dn, {}).get(attr, []))
                if snap_val != assess_val:
                    mismatches.append(f"{dn} {attr}: snapshot={snap_val} assess={assess_val}")

        assert not mismatches, "DIT mismatch between snapshot and assessment feed:\n" + "\n".join(mismatches)
