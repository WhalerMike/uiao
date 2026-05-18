"""tests/test_cyberark_oscal_emitter.py -- CyberArk OSCAL component-definition tests."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from uiao.oscal.cyberark_evidence import (
    _canonical_hash,
    emit_cyberark_component_definition,
    verify_signature,
)

_FIXED_NOW = datetime(2026, 5, 18, 11, 0, 0, tzinfo=timezone.utc)
_SIGNING_KEY = b"uiao-cyberark-oscal-test-key"
_VAULT_ID = "vault-lab-01"
_SIGNER = "uiao-conformance-test"

_ROTATIONS: list[dict[str, Any]] = [
    {
        "account_id": "svc_sql_prod",
        "safe_name": "uiao-privileged-safe",
        "control_id": "IA-5",
        "rotation_cause": "scheduled-30-day-rotation",
        "verification_passed": True,
        "rotated_at": "2026-05-18T10:00:00Z",
    },
    {
        "account_id": "svc_api_gateway",
        "safe_name": "uiao-privileged-safe",
        "control_id": "IA-5(1)",
        "rotation_cause": "post-incident-reset",
        "verification_passed": True,
        "rotated_at": "2026-05-18T10:10:00Z",
    },
    {
        "account_id": "breakglass_admin",
        "safe_name": "uiao-breakglass-safe",
        "control_id": "AC-2",
        "rotation_cause": "owner-transfer",
        "verification_passed": False,
        "rotated_at": "2026-05-18T10:15:00Z",
    },
]

_GOLDEN_PATH = Path(__file__).parent / "fixtures" / "oscal" / "cyberark-component-definition-golden.json"


def _emit() -> dict[str, Any]:
    return emit_cyberark_component_definition(
        _ROTATIONS,
        vault_id=_VAULT_ID,
        signer=_SIGNER,
        signing_key=_SIGNING_KEY,
        now_dt=_FIXED_NOW,
    )


def _normalized(doc: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(doc)
    normalized["metadata"]["last-modified"] = "__TIMESTAMP__"
    normalized["signature"]["signed_at"] = "__TIMESTAMP__"
    normalized["signature"]["value"] = "__SIGNATURE__"
    normalized["provenance"]["derived_at"] = "__TIMESTAMP__"
    return normalized


def test_component_definition_shape() -> None:
    doc = _emit()
    for key in ("uuid", "metadata", "components", "signature", "provenance"):
        assert key in doc
    assert doc["metadata"]["oscal-version"] == "1.1.2"


def test_rotation_props_include_cause_and_verification() -> None:
    doc = _emit()
    statements = doc["components"][0]["control-implementations"][0]["implemented-requirements"][0]["statements"]
    prop_names = {prop["name"] for prop in statements[0]["props"]}
    assert "rotation-cause" in prop_names
    assert "verification-passed" in prop_names


def test_signature_verification_round_trip() -> None:
    doc = _emit()
    assert verify_signature(doc, _SIGNING_KEY) is True


def test_signature_detects_tampering() -> None:
    doc = _emit()
    tampered = copy.deepcopy(doc)
    tampered["components"][0]["title"] = "tampered-title"
    assert verify_signature(tampered, _SIGNING_KEY) is False


def test_canonical_hash_is_stable() -> None:
    a = _emit()
    b = _emit()
    assert _canonical_hash(a) == _canonical_hash(b)


def test_golden_file_regression() -> None:
    emitted = _normalized(_emit())
    golden = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    assert emitted == golden
