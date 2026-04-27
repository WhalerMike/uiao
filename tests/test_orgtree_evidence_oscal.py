"""tests/test_orgtree_evidence_oscal.py — OrgTree OSCAL evidence emitter test suite.

Test layers
-----------
1. Unit: auth-method derivation, disabled/stale detection, privileged-group detection.
2. Unit: inventory-item builders (CM-8, IA-2, IA-3).
3. Unit: AC-2 observation/finding builders.
4. Unit: AC-6 observation/finding builders.
5. Integration: emit_orgtree_evidence() end-to-end on synthetic bundle.
6. Golden-file regression: output must match tests/fixtures/oscal/orgtree-evidence-golden.json.

Golden-file regeneration
------------------------
Run::

    pytest tests/test_orgtree_evidence_oscal.py --update-golden -s

This will overwrite the committed golden file with the current emitter output.
After regeneration, review the diff and commit if the change is intentional.

The synthetic bundle is declared in ``_SYNTHETIC_BUNDLE`` below; it is also
persisted as the fixture ``tests/fixtures/oscal/orgtree-evidence-golden.json``
so the golden can be inspected offline without running pytest.

All tests are deterministic and hermetic (no network, no filesystem side-effects
except the golden-file overwrite when ``--update-golden`` is passed).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------
from uiao.oscal.orgtree_evidence import (
    _derive_auth_method,
    _is_disabled,
    _is_privileged_group,
    _is_stale,
    emit_orgtree_evidence,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "oscal"
_GOLDEN_PATH = _FIXTURES_DIR / "orgtree-evidence-golden.json"

# ---------------------------------------------------------------------------
# pytest fixture: --update-golden flag (option declared in conftest.py)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def update_golden(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--update-golden", default=False))


# ---------------------------------------------------------------------------
# Synthetic bundle — fixed epoch timestamps for full determinism
# ---------------------------------------------------------------------------

# 2026-04-27T00:00:00Z ≈ 1745712000 (used as mock "now" anchor in golden tests)
# We use lastLogonTimestamp relative to this to create fresh/stale conditions.
_FIXED_NOW_TS: float = 1745712000.0
_FRESH_TS: float = _FIXED_NOW_TS - (5 * 86400)  # 5 days ago
_STALE_TS: float = _FIXED_NOW_TS - (95 * 86400)  # 95 days ago (> 90-day threshold)

_SYNTHETIC_BUNDLE: dict[str, Any] = {
    "run_id": "orgtree-golden-001",
    "tenant": "test.contoso.com",
    "users": [
        {
            "samAccountName": "alice",
            "distinguishedName": "CN=alice,OU=Users,DC=test,DC=contoso,DC=com",
            "objectSid": "S-1-5-21-1234567890-1234567890-1234567890-1001",
            "userAccountControl": 512,
            "displayName": "Alice Smith",
            "mail": "alice@test.contoso.com",
            "enabled": True,
            "lastLogonTimestamp": _FRESH_TS,
        },
        {
            "samAccountName": "bob",
            "distinguishedName": "CN=bob,OU=Users,DC=test,DC=contoso,DC=com",
            "objectSid": "S-1-5-21-1234567890-1234567890-1234567890-1002",
            # UAC 0x40200 = SMARTCARD_REQUIRED | NORMAL_ACCOUNT
            "userAccountControl": 0x40200,
            "displayName": "Bob Jones",
            "mail": "bob@test.contoso.com",
            "enabled": True,
            "lastLogonTimestamp": _FRESH_TS,
        },
        {
            "samAccountName": "charlie",
            "distinguishedName": "CN=charlie,OU=Users,DC=test,DC=contoso,DC=com",
            "objectSid": "S-1-5-21-1234567890-1234567890-1234567890-1003",
            "userAccountControl": 514,  # disabled (ADS_UF_ACCOUNTDISABLE)
            "displayName": "Charlie Brown",
            "mail": "charlie@test.contoso.com",
            "enabled": False,
            "lastLogonTimestamp": _STALE_TS,
        },
        {
            "samAccountName": "diana",
            "distinguishedName": "CN=diana,OU=Users,DC=test,DC=contoso,DC=com",
            "objectSid": "S-1-5-21-1234567890-1234567890-1234567890-1004",
            "userAccountControl": 512,
            "displayName": "Diana Prince",
            "mail": "diana@test.contoso.com",
            "enabled": True,
            "lastLogonTimestamp": _STALE_TS,  # stale — triggers AC-2 finding
            "extensionAttribute1": "fido2",
        },
    ],
    "groups": [
        {
            "samAccountName": "Domain Admins",
            "distinguishedName": "CN=Domain Admins,CN=Users,DC=test,DC=contoso,DC=com",
            "objectSid": "S-1-5-21-1234567890-1234567890-1234567890-512",
            "primaryGroupToken": 512,
            "description": "Domain Administrators",
            "members": ["alice"],
        },
        {
            "samAccountName": "AllStaff",
            "distinguishedName": "CN=AllStaff,OU=Groups,DC=test,DC=contoso,DC=com",
            "objectSid": "S-1-5-21-1234567890-1234567890-1234567890-2000",
            "description": "All staff distribution list",
            "members": ["alice", "bob", "charlie", "diana"],
        },
    ],
    "computers": [
        {
            "name": "LAPTOP-001",
            "distinguishedName": "CN=LAPTOP-001,OU=Workstations,DC=test,DC=contoso,DC=com",
            "objectSid": "S-1-5-21-1234567890-1234567890-1234567890-3001",
            "dNSHostName": "LAPTOP-001.test.contoso.com",
            "operatingSystem": "Windows 11 Enterprise",
            "enabled": True,
            "lastLogonTimestamp": _FRESH_TS,
        },
    ],
    "servers": [
        {
            "name": "DC-001",
            "distinguishedName": "CN=DC-001,OU=Domain Controllers,DC=test,DC=contoso,DC=com",
            "objectSid": "S-1-5-21-1234567890-1234567890-1234567890-1000",
            "dNSHostName": "DC-001.test.contoso.com",
            "operatingSystem": "Windows Server 2022 Standard",
            "enabled": True,
            "lastLogonTimestamp": _FRESH_TS,
        },
    ],
}

# ---------------------------------------------------------------------------
# 1. Auth-method derivation
# ---------------------------------------------------------------------------


class TestDeriveAuthMethod:
    def test_default_password(self) -> None:
        assert _derive_auth_method({"userAccountControl": 512}) == "password"

    def test_smartcard_from_uac_bit(self) -> None:
        assert _derive_auth_method({"userAccountControl": 0x40200}) == "smartcard"

    def test_fido2_from_extension_attribute(self) -> None:
        assert _derive_auth_method({"extensionAttribute1": "FIDO2", "userAccountControl": 512}) == "fido2"

    def test_smartcard_from_extension_attribute(self) -> None:
        assert _derive_auth_method({"extensionAttribute2": "smartcard-required"}) == "smartcard"

    def test_piv_maps_to_smartcard(self) -> None:
        assert _derive_auth_method({"extensionAttribute1": "PIV"}) == "smartcard"

    def test_cac_maps_to_smartcard(self) -> None:
        assert _derive_auth_method({"extensionAttribute1": "CAC"}) == "smartcard"

    def test_extension_attribute_wins_over_uac(self) -> None:
        # extension attribute fido2 takes priority over UAC smartcard bit
        assert _derive_auth_method({"extensionAttribute1": "fido2", "userAccountControl": 0x40200}) == "fido2"

    def test_password_explicit_in_extension_attribute(self) -> None:
        assert _derive_auth_method({"extensionAttribute3": "password-auth"}) == "password"

    def test_empty_user_dict(self) -> None:
        assert _derive_auth_method({}) == "password"


# ---------------------------------------------------------------------------
# 2. Disabled detection
# ---------------------------------------------------------------------------


class TestIsDisabled:
    def test_enabled_true(self) -> None:
        assert not _is_disabled({"enabled": True})

    def test_enabled_false(self) -> None:
        assert _is_disabled({"enabled": False})

    def test_uac_disabled_bit(self) -> None:
        assert _is_disabled({"userAccountControl": 514})  # 512 | 2

    def test_uac_enabled(self) -> None:
        assert not _is_disabled({"userAccountControl": 512})

    def test_no_fields(self) -> None:
        # No UAC, no enabled -> defaults to not-disabled
        assert not _is_disabled({})


# ---------------------------------------------------------------------------
# 3. Stale detection
# ---------------------------------------------------------------------------


class TestIsStale:
    def test_fresh_account(self) -> None:
        now = _FIXED_NOW_TS
        assert not _is_stale({"lastLogonTimestamp": now - 5 * 86400, "enabled": True}, now)

    def test_stale_account(self) -> None:
        now = _FIXED_NOW_TS
        assert _is_stale({"lastLogonTimestamp": now - 95 * 86400, "enabled": True}, now)

    def test_exactly_90_days_is_not_stale(self) -> None:
        now = _FIXED_NOW_TS
        assert not _is_stale({"lastLogonTimestamp": now - 90 * 86400, "enabled": True}, now)

    def test_91_days_is_stale(self) -> None:
        now = _FIXED_NOW_TS
        assert _is_stale({"lastLogonTimestamp": now - 91 * 86400, "enabled": True}, now)

    def test_none_logon_not_stale(self) -> None:
        assert not _is_stale({"lastLogonTimestamp": None}, _FIXED_NOW_TS)

    def test_missing_logon_not_stale(self) -> None:
        assert not _is_stale({}, _FIXED_NOW_TS)


# ---------------------------------------------------------------------------
# 4. Privileged-group detection
# ---------------------------------------------------------------------------


class TestIsPrivilegedGroup:
    def test_domain_admins_by_rid(self) -> None:
        assert _is_privileged_group({"primaryGroupToken": 512})

    def test_enterprise_admins_by_rid(self) -> None:
        assert _is_privileged_group({"primaryGroupToken": 519})

    def test_schema_admins_by_rid(self) -> None:
        assert _is_privileged_group({"primaryGroupToken": 518})

    def test_account_operators_by_rid(self) -> None:
        assert _is_privileged_group({"primaryGroupToken": 548})

    def test_backup_operators_by_rid(self) -> None:
        assert _is_privileged_group({"primaryGroupToken": 551})

    def test_server_operators_by_rid(self) -> None:
        assert _is_privileged_group({"primaryGroupToken": 549})

    def test_print_operators_by_rid(self) -> None:
        assert _is_privileged_group({"primaryGroupToken": 550})

    def test_domain_admins_by_name(self) -> None:
        assert _is_privileged_group({"samAccountName": "Domain Admins"})

    def test_enterprise_admins_by_name(self) -> None:
        assert _is_privileged_group({"samAccountName": "Enterprise Admins"})

    def test_regular_group_not_privileged(self) -> None:
        assert not _is_privileged_group({"samAccountName": "AllStaff", "primaryGroupToken": 1200})

    def test_no_rid_no_name_not_privileged(self) -> None:
        assert not _is_privileged_group({})

    def test_non_privileged_rid(self) -> None:
        assert not _is_privileged_group({"primaryGroupToken": 513})  # Domain Users


# ---------------------------------------------------------------------------
# 5. Integration: emit_orgtree_evidence() end-to-end
# ---------------------------------------------------------------------------


class TestEmitOrgTreeEvidence:
    def test_output_file_created(self, tmp_path: Path) -> None:
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        assert path.exists()
        assert path.name == "orgtree-evidence.json"

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_root_key_is_assessment_results(self, tmp_path: Path) -> None:
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "assessment-results" in data

    def test_uuid_present(self, tmp_path: Path) -> None:
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        assert "uuid" in ar

    def test_metadata_fields(self, tmp_path: Path) -> None:
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        meta = ar["metadata"]
        assert meta["oscal-version"] == "1.0.4"
        assert "last-modified" in meta
        assert "title" in meta

    def test_inventory_items_count(self, tmp_path: Path) -> None:
        """CM-8: 4 users + 2 groups + 1 computer + 1 server = 8 inventory items."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        result = ar["results"][0]
        items = result.get("local-definitions", {}).get("inventory-items", [])
        assert len(items) == 8  # 4 users + 2 groups + 1 computer + 1 server

    def test_user_inventory_item_has_auth_method(self, tmp_path: Path) -> None:
        """IA-2: each user inventory item has an auth-method prop."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        items = ar["results"][0].get("local-definitions", {}).get("inventory-items", [])
        user_items = [
            i for i in items if any(p["name"] == "asset-type" and p["value"] == "user" for p in i.get("props", []))
        ]
        assert len(user_items) == 4
        for item in user_items:
            prop_names = {p["name"] for p in item.get("props", [])}
            assert "auth-method" in prop_names, f"Missing auth-method in {item['uuid']}"

    def test_bob_has_smartcard_auth(self, tmp_path: Path) -> None:
        """IA-2: bob has UAC smartcard bit set -> auth-method=smartcard."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        items = ar["results"][0].get("local-definitions", {}).get("inventory-items", [])
        bob_items = [
            i for i in items if any(p["name"] == "sam-account-name" and p["value"] == "bob" for p in i.get("props", []))
        ]
        assert len(bob_items) == 1
        auth_props = [p["value"] for p in bob_items[0]["props"] if p["name"] == "auth-method"]
        assert auth_props == ["smartcard"]

    def test_diana_has_fido2_auth(self, tmp_path: Path) -> None:
        """IA-2: diana has extensionAttribute1=fido2 -> auth-method=fido2."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        items = ar["results"][0].get("local-definitions", {}).get("inventory-items", [])
        diana_items = [
            i
            for i in items
            if any(p["name"] == "sam-account-name" and p["value"] == "diana" for p in i.get("props", []))
        ]
        assert len(diana_items) == 1
        auth_props = [p["value"] for p in diana_items[0]["props"] if p["name"] == "auth-method"]
        assert auth_props == ["fido2"]

    def test_computer_has_ia3_props(self, tmp_path: Path) -> None:
        """IA-3: computer inventory item has object-sid and dns-name props."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        items = ar["results"][0].get("local-definitions", {}).get("inventory-items", [])
        computer_items = [
            i for i in items if any(p["name"] == "asset-type" and p["value"] == "computer" for p in i.get("props", []))
        ]
        assert len(computer_items) >= 1
        for item in computer_items:
            prop_names = {p["name"] for p in item.get("props", [])}
            assert "object-sid" in prop_names
            assert "dns-name" in prop_names

    def test_server_has_ia3_props(self, tmp_path: Path) -> None:
        """IA-3: server inventory item has object-sid and dns-name props."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        items = ar["results"][0].get("local-definitions", {}).get("inventory-items", [])
        server_items = [
            i for i in items if any(p["name"] == "asset-type" and p["value"] == "server" for p in i.get("props", []))
        ]
        assert len(server_items) >= 1
        for item in server_items:
            prop_names = {p["name"] for p in item.get("props", [])}
            assert "object-sid" in prop_names
            assert "dns-name" in prop_names

    def test_ac2_disabled_finding_present(self, tmp_path: Path) -> None:
        """AC-2: charlie (disabled) generates a finding."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        result = ar["results"][0]
        findings = result.get("findings", [])
        disabled_findings = [f for f in findings if "charlie" in f["title"] and "Disabled" in f["title"]]
        assert len(disabled_findings) == 1

    def test_ac2_stale_finding_present(self, tmp_path: Path) -> None:
        """AC-2: diana (stale, enabled) generates a stale finding."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        result = ar["results"][0]
        findings = result.get("findings", [])
        stale_findings = [f for f in findings if "diana" in f["title"] and "Stale" in f["title"]]
        assert len(stale_findings) == 1

    def test_ac2_observations_match_findings(self, tmp_path: Path) -> None:
        """AC-2: each finding references an observation UUID."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        result = ar["results"][0]
        obs_uuids = {o["uuid"] for o in result.get("observations", [])}
        for finding in result.get("findings", []):
            for rel_obs in finding.get("related-observations", []):
                assert rel_obs["observation-uuid"] in obs_uuids

    def test_ac6_privileged_group_finding_present(self, tmp_path: Path) -> None:
        """AC-6: Domain Admins generates an AC-6 finding."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        result = ar["results"][0]
        findings = result.get("findings", [])
        ac6_findings = [f for f in findings if "Domain Admins" in f["title"]]
        assert len(ac6_findings) == 1

    def test_ac6_non_privileged_group_no_finding(self, tmp_path: Path) -> None:
        """AC-6: AllStaff (non-privileged) does NOT generate a finding."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        result = ar["results"][0]
        findings = result.get("findings", [])
        allstaff_findings = [f for f in findings if "AllStaff" in f["title"]]
        assert len(allstaff_findings) == 0

    def test_domain_admins_inventory_item_has_privileged_prop(self, tmp_path: Path) -> None:
        """AC-6: Domain Admins group inventory item has privileged-group=true prop."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        items = ar["results"][0].get("local-definitions", {}).get("inventory-items", [])
        da_items = [
            i
            for i in items
            if any(p["name"] == "sam-account-name" and p["value"] == "Domain Admins" for p in i.get("props", []))
        ]
        assert len(da_items) == 1
        priv_props = [p["value"] for p in da_items[0]["props"] if p["name"] == "privileged-group"]
        assert priv_props == ["true"]

    def test_reviewed_controls_present(self, tmp_path: Path) -> None:
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        ar = json.loads(path.read_text(encoding="utf-8"))["assessment-results"]
        reviewed = ar["results"][0]["reviewed-controls"]
        assert "control-selections" in reviewed

    def test_output_is_deterministic_on_uuid(self, tmp_path: Path) -> None:
        """Same run_id must always produce the same result UUID."""
        p1 = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path / "run1")
        p2 = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path / "run2")
        ar1 = json.loads(p1.read_text())["assessment-results"]
        ar2 = json.loads(p2.read_text())["assessment-results"]
        assert ar1["uuid"] == ar2["uuid"]
        assert ar1["results"][0]["uuid"] == ar2["results"][0]["uuid"]

    def test_empty_bundle_does_not_crash(self, tmp_path: Path) -> None:
        """Graceful degradation on minimal bundle."""
        path = emit_orgtree_evidence({"run_id": "empty-001", "tenant": "empty"}, tmp_path)
        ar = json.loads(path.read_text())["assessment-results"]
        assert "results" in ar

    def test_out_dir_is_created(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c"
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, deep)
        assert path.exists()

    def test_trestle_schema_compliance(self, tmp_path: Path) -> None:
        """Validate output against compliance-trestle 1.1.2 Pydantic model."""
        from trestle.oscal.assessment_results import AssessmentResults

        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        ar_data = data.get("assessment-results", data)
        # This will raise if schema validation fails
        ar_obj = AssessmentResults(**ar_data)
        assert ar_obj.uuid is not None


# ---------------------------------------------------------------------------
# 6. Golden-file regression
# ---------------------------------------------------------------------------


def _canonicalize(data: dict[str, Any]) -> str:
    """Return a stable canonical string form of *data* for golden comparison.

    Transformations applied:
    - Recursively sorts all dict keys so key-ordering changes don't break the
      golden.
    - Replaces ``metadata.last-modified``, ``results[*].start``, and
      ``observations[*].collected`` with the sentinel ``"__TIMESTAMP__"`` so
      re-runs at different wall-clock times produce identical output.
    - Drops ``metadata.version`` because it is bumped independently of the
      evidence content and would require golden regeneration on every release.
    - Returns ``json.dumps(..., indent=2, sort_keys=True)`` so the diff is
      human-readable on failure.
    """
    import copy

    def _sort_keys(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _sort_keys(v) for k in sorted(obj.keys()) for v in [obj[k]]}
        if isinstance(obj, list):
            return [_sort_keys(item) for item in obj]
        return obj

    d = copy.deepcopy(data)
    ar = d.get("assessment-results", {})

    meta = ar.get("metadata", {})
    if "last-modified" in meta:
        meta["last-modified"] = "__TIMESTAMP__"
    meta.pop("version", None)

    for result in ar.get("results", []):
        if "start" in result:
            result["start"] = "__TIMESTAMP__"
        for obs in result.get("observations", []):
            if "collected" in obs:
                obs["collected"] = "__TIMESTAMP__"

    return json.dumps(_sort_keys(d), indent=2, ensure_ascii=False)


class TestGoldenFile:
    def test_golden_file_exists(self) -> None:
        assert _GOLDEN_PATH.exists(), (
            f"Golden file not found: {_GOLDEN_PATH}. Run: pytest tests/test_orgtree_evidence_oscal.py --update-golden"
        )

    def test_golden_matches_emitter_output(self, tmp_path: Path, update_golden: bool) -> None:
        """Fail closed: emitter output must match the committed golden file."""
        path = emit_orgtree_evidence(_SYNTHETIC_BUNDLE, tmp_path)
        actual_raw = json.loads(path.read_text(encoding="utf-8"))
        actual_str = _canonicalize(actual_raw)

        if update_golden:
            _GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            _GOLDEN_PATH.write_text(actual_str, encoding="utf-8")
            pytest.skip("Golden file updated — re-run without --update-golden to verify.")
            return

        if not _GOLDEN_PATH.exists():
            pytest.fail(
                f"Golden file missing: {_GOLDEN_PATH}\nRun: pytest tests/test_orgtree_evidence_oscal.py --update-golden"
            )

        golden_str = _GOLDEN_PATH.read_text(encoding="utf-8")

        if actual_str != golden_str:
            # Produce a readable diff for the failure message
            import difflib

            diff = "\n".join(
                difflib.unified_diff(
                    golden_str.splitlines(),
                    actual_str.splitlines(),
                    fromfile="golden",
                    tofile="actual",
                    lineterm="",
                )
            )
            pytest.fail(
                f"Emitter output does not match golden file.\n"
                f"To update the golden: pytest tests/test_orgtree_evidence_oscal.py --update-golden\n\n"
                f"Diff (golden → actual):\n{diff[:4000]}"
            )
