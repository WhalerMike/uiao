"""Tests for scripts/conmon/redact.py (RFC-0026 E7 / ADR-045).

Guards the scan-finding redaction pipeline stage. Every assertion in
this module is the enforcement surface of ADR-045 D1–D7:

- D1: tier_1_ref sha256 links Tier-2 back to Tier-1
- D2: retain / strip field lists behave deny-by-default
- D3: remediation_summary truncation
- D4: redactor is a standalone pipeline stage (no adapter coupling)
- D5: profile lives in canon and is loaded by default (guard test)
- D6: inconsistent profile (same field in retain and strip) hard-fails

Roadmap reference: docs/docs/uiao-rfc-0026-roadmap.md § E7.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
from typing import Any, Dict

import pytest

# ---------------------------------------------------------------------------
# Dynamic import of scripts/conmon/redact.py (same pattern as
# tests/test_migration_readiness.py — keeps scripts/ free of src-layout).
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_MODULE_PATH = _REPO_ROOT / "scripts" / "conmon" / "redact.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("redact", _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["redact"] = mod
    spec.loader.exec_module(mod)
    return mod


redact_mod = _load_module()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _minimal_profile() -> Dict[str, Any]:
    """A profile small enough to reason about in tests, but with the
    full shape the ADR prescribes."""
    return {
        "schema-version": "1.0.0",
        "profile-version": "test-1.0",
        "adr-ref": "ADR-045",
        "retain_fields": [
            "tracking_id",
            "risk_level",
            "finding_state",
            "control_family",
            "remediation_summary",
            "tier_1_ref",
        ],
        "strip_fields": [
            "plugin_id",
            "cve_ids",
            "asset_ip",
            "raw_output",
            "exploit_available",
        ],
        "remediation_summary_max_chars": 280,
        "remediation_summary_truncation_suffix": "… [truncated — see tier_1_ref]",
        "tier_1_reference": {
            "field_name": "tier_1_ref",
            "algorithm": "sha256",
        },
    }


@pytest.fixture
def profile() -> Dict[str, Any]:
    return _minimal_profile()


@pytest.fixture
def sample_raw_finding() -> Dict[str, Any]:
    return {
        "tracking_id": "UIAO-VLN-2027-00042",
        "risk_level": "high",
        "finding_state": "open",
        "control_family": "SC",
        "remediation_summary": "Apply vendor patch 12.3.4 on affected hosts; verify with scanner rerun.",
        "finding_category": "missing security patch",
        # Fields that must be stripped:
        "plugin_id": "nessus-plugin-58742",
        "cve_ids": ["CVE-2026-12345", "CVE-2026-67890"],
        "asset_ip": "10.0.0.17",
        "asset_fqdn": "db-prod-07.example.gov",
        "raw_output": "payload: <bytes>",
        "exploit_available": True,
    }


# ---------------------------------------------------------------------------
# Unit tests — redact_finding() deny-by-default behavior (ADR-045 D2)
# ---------------------------------------------------------------------------


class TestRedactFieldPolicy:
    def test_strip_fields_are_absent_from_output(
        self, profile: Dict[str, Any], sample_raw_finding: Dict[str, Any]
    ) -> None:
        redacted = redact_mod.redact_finding(sample_raw_finding, profile)
        for deny in ("plugin_id", "cve_ids", "asset_ip", "asset_fqdn", "raw_output", "exploit_available"):
            assert deny not in redacted, f"deny-list field {deny!r} leaked into Tier-2 output"

    def test_retain_fields_pass_through_unchanged(
        self, profile: Dict[str, Any], sample_raw_finding: Dict[str, Any]
    ) -> None:
        redacted = redact_mod.redact_finding(sample_raw_finding, profile)
        for allow in ("tracking_id", "risk_level", "finding_state", "control_family"):
            assert redacted[allow] == sample_raw_finding[allow]

    def test_field_not_named_anywhere_is_stripped_by_default(self, profile: Dict[str, Any]) -> None:
        """Deny-by-default: a wild field that's in neither list still gets stripped."""
        finding = {
            "tracking_id": "UIAO-VLN-X",
            "completely_novel_field": "sensitive?",
        }
        redacted = redact_mod.redact_finding(finding, profile)
        assert "completely_novel_field" not in redacted

    def test_retain_field_absent_from_input_is_not_emitted_as_null(self, profile: Dict[str, Any]) -> None:
        finding = {"tracking_id": "UIAO-VLN-Y"}
        redacted = redact_mod.redact_finding(finding, profile)
        # Other retain-list fields should not appear as None
        for field in ("risk_level", "finding_state", "control_family", "remediation_summary"):
            assert field not in redacted


# ---------------------------------------------------------------------------
# D1: tier_1_ref sha256 back-reference
# ---------------------------------------------------------------------------


class TestTier1Reference:
    def test_tier_1_ref_is_present_and_sha256_shaped(
        self, profile: Dict[str, Any], sample_raw_finding: Dict[str, Any]
    ) -> None:
        redacted = redact_mod.redact_finding(sample_raw_finding, profile)
        assert "tier_1_ref" in redacted
        assert len(redacted["tier_1_ref"]) == 64  # sha256 hex
        assert all(c in "0123456789abcdef" for c in redacted["tier_1_ref"])

    def test_different_inputs_produce_different_tier_1_refs(self, profile: Dict[str, Any]) -> None:
        a = redact_mod.redact_finding({"tracking_id": "A"}, profile)
        b = redact_mod.redact_finding({"tracking_id": "B"}, profile)
        assert a["tier_1_ref"] != b["tier_1_ref"]

    def test_same_input_produces_stable_tier_1_ref(
        self, profile: Dict[str, Any], sample_raw_finding: Dict[str, Any]
    ) -> None:
        """Canonicalization (sort_keys, compact separators) must be deterministic."""
        a = redact_mod.redact_finding(sample_raw_finding, profile)
        b = redact_mod.redact_finding(sample_raw_finding, profile)
        assert a["tier_1_ref"] == b["tier_1_ref"]

    def test_tier_1_ref_matches_canonical_hash_helper(
        self, profile: Dict[str, Any], sample_raw_finding: Dict[str, Any]
    ) -> None:
        redacted = redact_mod.redact_finding(sample_raw_finding, profile)
        canonical = json.dumps(sample_raw_finding, sort_keys=True, separators=(",", ":"))
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert redacted["tier_1_ref"] == expected

    def test_caller_cannot_override_tier_1_ref_by_naming_it_in_input(self, profile: Dict[str, Any]) -> None:
        finding = {"tracking_id": "X", "tier_1_ref": "bogus-precomputed-value"}
        redacted = redact_mod.redact_finding(finding, profile)
        assert redacted["tier_1_ref"] != "bogus-precomputed-value"


# ---------------------------------------------------------------------------
# D3: remediation_summary truncation
# ---------------------------------------------------------------------------


class TestRemediationSummaryTruncation:
    def test_short_summary_passes_through(self, profile: Dict[str, Any]) -> None:
        finding = {"tracking_id": "X", "remediation_summary": "Apply patch."}
        redacted = redact_mod.redact_finding(finding, profile)
        assert redacted["remediation_summary"] == "Apply patch."

    def test_long_summary_is_truncated_with_suffix(self, profile: Dict[str, Any]) -> None:
        long_text = "A" * 400
        finding = {"tracking_id": "X", "remediation_summary": long_text}
        redacted = redact_mod.redact_finding(finding, profile)
        out = redacted["remediation_summary"]
        assert len(out) <= profile["remediation_summary_max_chars"]
        assert out.endswith(profile["remediation_summary_truncation_suffix"])

    def test_truncation_preserves_leading_content(self, profile: Dict[str, Any]) -> None:
        finding = {"tracking_id": "X", "remediation_summary": "LEAD" + "_" * 500}
        redacted = redact_mod.redact_finding(finding, profile)
        assert redacted["remediation_summary"].startswith("LEAD")

    def test_none_summary_becomes_empty(self, profile: Dict[str, Any]) -> None:
        finding = {"tracking_id": "X", "remediation_summary": None}
        redacted = redact_mod.redact_finding(finding, profile)
        # Because the retain-list includes remediation_summary *and* the
        # input provides the key, we preserve it (truncate turns None → "").
        assert redacted["remediation_summary"] == ""


# ---------------------------------------------------------------------------
# D6: profile integrity — inconsistent profile hard-fails
# ---------------------------------------------------------------------------


class TestProfileIntegrity:
    def test_field_in_both_retain_and_strip_raises(self, profile: Dict[str, Any]) -> None:
        profile["retain_fields"].append("plugin_id")  # now in both lists
        with pytest.raises(ValueError, match="plugin_id"):
            redact_mod.redact_finding({"tracking_id": "X"}, profile)

    def test_non_list_retain_fields_raises(self, profile: Dict[str, Any]) -> None:
        profile["retain_fields"] = "not-a-list"
        with pytest.raises(ValueError, match="retain_fields"):
            redact_mod.redact_finding({"tracking_id": "X"}, profile)


# ---------------------------------------------------------------------------
# Immutability — redactor must not mutate its input (D4)
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_input_finding_is_unchanged(self, profile: Dict[str, Any], sample_raw_finding: Dict[str, Any]) -> None:
        snapshot = json.dumps(sample_raw_finding, sort_keys=True)
        redact_mod.redact_finding(sample_raw_finding, profile)
        assert json.dumps(sample_raw_finding, sort_keys=True) == snapshot


# ---------------------------------------------------------------------------
# D5: canon profile is discoverable at the default path
# ---------------------------------------------------------------------------


class TestCanonProfileDiscovery:
    def test_load_profile_finds_canon_file_at_default_path(self) -> None:
        """The real canon profile must load without an override; this
        guards against silent deletion or path drift of
        src/uiao/canon/redaction-profile.yaml."""
        profile = redact_mod.load_profile()
        assert profile.get("adr-ref") == "ADR-045"
        assert isinstance(profile.get("retain_fields"), list)
        assert isinstance(profile.get("strip_fields"), list)
        assert profile.get("remediation_summary_max_chars") == 280

    def test_load_profile_raises_on_missing_file(self, tmp_path: pathlib.Path) -> None:
        with pytest.raises(FileNotFoundError, match="Redaction profile not found"):
            redact_mod.load_profile(
                profile_path="does-not-exist.yaml",
                repo_root=tmp_path,
            )


# ---------------------------------------------------------------------------
# Bulk API
# ---------------------------------------------------------------------------


class TestRedactFindingsBulk:
    def test_returns_one_record_per_input(self, profile: Dict[str, Any]) -> None:
        inputs = [
            {"tracking_id": "A", "risk_level": "high"},
            {"tracking_id": "B", "risk_level": "moderate"},
            {"tracking_id": "C", "risk_level": "low"},
        ]
        out = redact_mod.redact_findings(inputs, profile)
        assert len(out) == 3
        assert [r["tracking_id"] for r in out] == ["A", "B", "C"]

    def test_empty_input_returns_empty_list(self, profile: Dict[str, Any]) -> None:
        assert redact_mod.redact_findings([], profile) == []


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------


class TestCli:
    def test_main_reads_input_and_writes_redacted_output(self, tmp_path: pathlib.Path) -> None:
        # Using the real canon profile so this also validates end-to-end.
        raw = [
            {
                "tracking_id": "UIAO-VLN-CLI-001",
                "risk_level": "high",
                "plugin_id": "should-not-appear",
                "cve_ids": ["CVE-XXXX-YYYY"],
            }
        ]
        in_file = tmp_path / "raw.json"
        out_file = tmp_path / "tier2.json"
        in_file.write_text(json.dumps(raw), encoding="utf-8")

        rc = redact_mod.main(
            [
                "--input",
                str(in_file),
                "--output",
                str(out_file),
            ]
        )
        assert rc == 0

        written = json.loads(out_file.read_text(encoding="utf-8"))
        assert len(written) == 1
        assert written[0]["tracking_id"] == "UIAO-VLN-CLI-001"
        assert "plugin_id" not in written[0]
        assert "cve_ids" not in written[0]
        assert "tier_1_ref" in written[0]
