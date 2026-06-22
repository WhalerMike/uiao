"""UIAO_204 — overlay-fabric.schema.json guard tests.

The overlay fabric schema is executable canon (ADR-066 / ADR-123, UIAO_204):
it constrains the in-boundary token-issuer config whose fields UIAO_203
references, the registry of overlay / SD-WAN / SASE / service-mesh fabric
entries, and the typed OverlayTunnel runtime record.

These tests assert the schema is itself a valid Draft 2020-12 schema, accepts
a conforming fabric document, and rejects the four failure modes the spec
calls out: bad token format, over-ceiling lifetime, Path-B placement without
an exception reference, and a fabric entry on the wrong mission class.

References
----------
- UIAO_204 §3 — issuer config, fabric entries, OverlayTunnel definition
- UIAO_203 §2.2/§3.1/§4 — token format, lifetime ceiling, Path A selection
- ADR-066 §"Adapter registry implications"; ADR-123 §D1 (overlay naming)
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")
from jsonschema import Draft202012Validator  # noqa: E402

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "src/uiao/schemas/overlay-fabric/overlay-fabric.schema.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator(schema: dict) -> Draft202012Validator:
    return Draft202012Validator(schema)


@pytest.fixture
def valid_doc() -> dict:
    return {
        "schema-version": "1.0.0",
        "updated": "2026-06-22",
        "issuer": {
            "token_format": "spiffe-svid-jwt",
            "max_token_lifetime_seconds": 300,
            "signing_key_rotation_days": 90,
            "placement": "in-boundary",
            "posture_source_ref": "posture-telemetry",
        },
        "fabrics": [
            {
                "id": "sdwan-fabric",
                "kind": "sd-wan",
                "mission-class": "overlay",
                "token_issuer_ref": "token-issuer",
                "posture_source_ref": "posture-telemetry",
                "status": "reserved",
            }
        ],
    }


def test_schema_is_well_formed(schema: dict) -> None:
    """The schema itself is a valid Draft 2020-12 schema."""
    Draft202012Validator.check_schema(schema)


def test_happy_path_validates(validator: Draft202012Validator, valid_doc: dict) -> None:
    assert list(validator.iter_errors(valid_doc)) == []


def test_token_format_enum_enforced(validator: Draft202012Validator, valid_doc: dict) -> None:
    """Symmetric-secret / unknown token formats are non-conforming (UIAO_203 §2.2)."""
    doc = copy.deepcopy(valid_doc)
    doc["issuer"]["token_format"] = "hmac"
    assert list(validator.iter_errors(doc))


def test_lifetime_ceiling_enforced(validator: Draft202012Validator, valid_doc: dict) -> None:
    """Token lifetime above the 300s canon ceiling is rejected (UIAO_203 §3.1)."""
    doc = copy.deepcopy(valid_doc)
    doc["issuer"]["max_token_lifetime_seconds"] = 3600
    assert list(validator.iter_errors(doc))


def test_path_b_requires_exception_ref(validator: Draft202012Validator, valid_doc: dict) -> None:
    """declared-exception (Path B) without exception_ref is rejected (UIAO_203 §4)."""
    doc = copy.deepcopy(valid_doc)
    doc["issuer"]["placement"] = "declared-exception"
    assert list(validator.iter_errors(doc))

    doc["issuer"]["exception_ref"] = "gcc-boundary-gap-registry.yaml#overlay-issuer"
    assert list(validator.iter_errors(doc)) == []


def test_fabric_mission_class_is_overlay(validator: Draft202012Validator, valid_doc: dict) -> None:
    """A fabric entry must declare mission-class: overlay, not transport (ADR-123)."""
    doc = copy.deepcopy(valid_doc)
    doc["fabrics"][0]["mission-class"] = "transport"
    assert list(validator.iter_errors(doc))


def test_overlay_tunnel_definition_round_trips(schema: dict) -> None:
    """The $defs/overlayTunnel record validates a conforming tunnel."""
    tunnel_schema = schema["$defs"]["overlayTunnel"]
    Draft202012Validator.check_schema(tunnel_schema)
    validator = Draft202012Validator(tunnel_schema)
    tunnel = {
        "identity": "spiffe://uiao/svc/api",
        "application": "uiao-api",
        "posture": "compliant:abc123",
        "location": "org=uiao/loc=dc-east",
        "token": {"jti": "t-0001", "exp": "2026-06-22T00:05:00Z"},
        "lease": {
            "leased_at": "2026-06-22T00:00:00Z",
            "expires_at": "2026-06-22T00:05:00Z",
        },
    }
    assert list(validator.iter_errors(tunnel)) == []
    # Missing the authorizing token is a structural violation.
    del tunnel["token"]
    assert list(validator.iter_errors(tunnel))
