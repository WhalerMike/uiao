"""CyberArk adapter conformance tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from uiao.adapters.cyberark_adapter import CyberArkAdapter
from uiao.oscal.cyberark_evidence import emit_cyberark_component_definition

_TIER2_ROOT = Path(__file__).parent.parent / "fixtures" / "tier-2" / "cyberark"

_F_ACCOUNT_CREATE = _TIER2_ROOT / "account-create.json"
_F_ROTATE_SUCCESS = _TIER2_ROOT / "account-rotate-success.json"
_F_ROTATE_FAILURE = _TIER2_ROOT / "account-rotate-failure.json"
_F_VERIFY = _TIER2_ROOT / "account-verify.json"
_F_ACTIVITY = _TIER2_ROOT / "activity-audit.json"

_KSI_DIR = Path(__file__).parent.parent.parent / "src" / "uiao" / "rules" / "ksi" / "cyberark"
_MAPPING_PATH = (
    Path(__file__).parent.parent.parent / "src" / "uiao" / "rules" / "ksi" / "uiao-control-to-ksi-mapping.yaml"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _adapter() -> CyberArkAdapter:
    return CyberArkAdapter(
        {
            "vault_url": "https://vault.lab.local",
            "safe": "uiao-privileged-safe",
            "auth_token": "test-token",
            "timeout_seconds": 5,
        }
    )


def _synthetic_vault_accounts() -> list[dict[str, Any]]:
    return [
        {
            "account_id": "svc_sql_prod",
            "account_type": "service",
            "owner": "dba-team",
            "rotation_window_days": 15,
            "last_rotation_age_days": 10,
        },
        {
            "account_id": "svc_api_gateway",
            "account_type": "service",
            "owner": "platform-team",
            "rotation_window_days": 10,
            "last_rotation_age_days": 5,
        },
        {
            "account_id": "admin_alice",
            "account_type": "human",
            "owner": "alice",
            "rotation_window_days": 30,
            "last_rotation_age_days": 20,
        },
        {
            "account_id": "admin_bob",
            "account_type": "human",
            "owner": "bob",
            "rotation_window_days": 30,
            "last_rotation_age_days": 29,
        },
        {
            "account_id": "breakglass_admin",
            "account_type": "human",
            "owner": "",
            "rotation_window_days": 45,
            "last_rotation_age_days": 44,
        },
    ]


def _evaluate_ksi_cark(
    accounts: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    rotations: list[dict[str, Any]],
) -> dict[str, bool]:
    has_over_window = any(a["last_rotation_age_days"] > a["rotation_window_days"] for a in accounts)
    unresolved_failures = any(f["hours_since_failure"] > 24 and not f.get("governance_ticket_id") for f in failures)
    service_windows = [a["rotation_window_days"] for a in accounts if a["account_type"] == "service"]
    human_windows = [a["rotation_window_days"] for a in accounts if a["account_type"] == "human"]
    service_shorter = bool(service_windows and human_windows and max(service_windows) < min(human_windows))
    has_orphan = any(not str(a.get("owner", "")).strip() for a in accounts)
    verification_gaps = any(not r.get("verification_passed", False) for r in rotations)
    return {
        "KSI-CARK-001": not has_over_window,
        "KSI-CARK-002": not unresolved_failures,
        "KSI-CARK-003": service_shorter,
        "KSI-CARK-004": not has_orphan,
        "KSI-CARK-005": not verification_gaps,
    }


def test_tier2_fixture_scope_complete() -> None:
    for fixture in (_F_ACCOUNT_CREATE, _F_ROTATE_SUCCESS, _F_ROTATE_FAILURE, _F_VERIFY, _F_ACTIVITY):
        assert fixture.exists(), f"Missing fixture: {fixture.name}"


def test_ksi_rules_and_mapping_entries_present() -> None:
    for idx in range(1, 6):
        ksi_file = _KSI_DIR / f"KSI-CARK-{idx:03d}.yaml"
        assert ksi_file.exists(), f"Missing KSI file: {ksi_file.name}"
    mapping_text = _MAPPING_PATH.read_text(encoding="utf-8")
    for idx in range(1, 6):
        assert f"KSI-CARK-{idx:03d}:" in mapping_text


def test_rotate_credential_round_trip_with_mocked_vault() -> None:
    rotate_success = _load(_F_ROTATE_SUCCESS)
    verify = _load(_F_VERIFY)
    activity = _load(_F_ACTIVITY)

    adapter = _adapter()

    def fake_request(method: str, path: str, **_: Any) -> dict[str, Any]:
        if path.endswith("/Change"):
            return rotate_success["response"]["body"]
        if path.endswith("/Verify"):
            return verify["response"]["body"]
        if path.endswith("/Activities"):
            return activity["response"]["body"]
        raise AssertionError(f"Unexpected path: {path}")

    adapter._request = fake_request  # type: ignore[method-assign]

    report = adapter.rotate_credential("12_34", rotation_cause="scheduled-30-day-rotation")
    assert report.severity == "info"
    assert report.details["verification_passed"] is True
    assert report.details["rotation_cause"] == "scheduled-30-day-rotation"
    assert report.details["activity_count"] == 2


def test_rotate_failure_fixture_maps_to_high_severity() -> None:
    rotate_failure = _load(_F_ROTATE_FAILURE)
    adapter = _adapter()

    def fake_request(method: str, path: str, **_: Any) -> dict[str, Any]:
        if path.endswith("/Change"):
            raise RuntimeError(rotate_failure["response"]["body"]["errorMessage"])
        return {"success": False}

    adapter._request = fake_request  # type: ignore[method-assign]

    report = adapter.rotate_credential("77_99", rotation_cause="manual-emergency-rotation")
    assert report.severity == "high"
    assert report.details["verification_passed"] is False
    assert "Policy denied" in report.details["error"]


def test_rotation_evidence_to_oscal_component_definition() -> None:
    adapter = _adapter()
    adapter._request = lambda *args, **kwargs: {"success": True, "value": []}  # type: ignore[method-assign]
    report = adapter.rotate_credential("12_34", rotation_cause="manual-emergency-rotation")

    component_def = emit_cyberark_component_definition(
        [
            {
                "account_id": report.details["account_id"],
                "safe_name": report.details["safe"],
                "control_id": "IA-5",
                "rotation_cause": report.details["rotation_cause"],
                "verification_passed": report.details["verification_passed"],
                "rotated_at": report.last_observed.isoformat(),
            }
        ],
        vault_id="vault-lab-01",
        signer="conformance-test",
        signing_key=b"conformance-signing-key",
    )

    assert component_def["components"][0]["control-implementations"]
    statement_props = component_def["components"][0]["control-implementations"][0]["implemented-requirements"][0][
        "statements"
    ][0]["props"]
    names = {p["name"] for p in statement_props}
    assert {"rotation-cause", "verification-passed"} <= names


def test_ksi_evaluator_expected_verdicts_for_synthetic_vault() -> None:
    accounts = _synthetic_vault_accounts()
    failures = [{"account_id": "legacy_svc", "hours_since_failure": 30, "governance_ticket_id": "GOV-1234"}]
    rotations = [
        {"account_id": "svc_sql_prod", "verification_passed": True},
        {"account_id": "svc_api_gateway", "verification_passed": True},
        {"account_id": "admin_alice", "verification_passed": True},
    ]
    verdicts = _evaluate_ksi_cark(accounts, failures, rotations)
    assert verdicts == {
        "KSI-CARK-001": True,
        "KSI-CARK-002": True,
        "KSI-CARK-003": True,
        "KSI-CARK-004": False,
        "KSI-CARK-005": True,
    }
