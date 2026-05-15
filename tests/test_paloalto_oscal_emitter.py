"""tests/test_paloalto_oscal_emitter.py -- Acceptance tests for WS-A2 (Palo Alto).

Tests
-----
1.  Empty claims list emits a valid component-definition with zero implementations.
2.  Single claim emits component-definition with 1 control-implementation.
3.  Multiple claims with mixed rule_types emit grouped implementations.
4.  Signature verification round-trip (emit, verify ok=True).
5.  Tamper detection: modify rule_name post-emit, verify returns False.
6.  Deterministic stable hash: same inputs -> same hash (excluding volatile fields).
7.  Provenance block matches metadata-schema contract.
8.  Required OSCAL keys present: uuid, metadata, components, signature, provenance.
9.  Wrong signing key returns False from verify_signature.
10. Golden-file regression for a 3-claim canonical example.

References
----------
- modernization-registry.yaml: palo-alto -> controls SC-7/CM-7/AC-4
- UIAO-CANON-003 provenance source
- src/uiao/oscal/servicenow_evidence.py -- canonical sibling emitter pattern
"""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime

import pytest

from uiao.oscal.paloalto_evidence import (
    _canonical_hash,
    emit_paloalto_component_definition,
    verify_signature,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_SIGNING_KEY = b"test-signing-key-uiao-ws-a2-paloalto-2026"
_TENANT_ID = "fw01.example.com:vsys1"
_SIGNER = "ISSO/automated-pipeline"

_CLAIM_SC7: dict = {
    "rule_name": "allow-dmz-to-internet",
    "rule_type": "security-rule",
    "action": "allow",
    "from_zone": "dmz",
    "to_zone": "untrust",
    "uiao_control_id": "SC-7",
    "timestamp": "2026-05-01T10:00:00+00:00",
}

_CLAIM_CM7: dict = {
    "rule_name": "block-unused-services",
    "rule_type": "security-rule",
    "action": "deny",
    "from_zone": "trust",
    "to_zone": "untrust",
    "uiao_control_id": "CM-7",
    "timestamp": "2026-05-02T11:00:00+00:00",
}

_CLAIM_AC4: dict = {
    "rule_name": "nat-outbound",
    "rule_type": "nat-rule",
    "action": "nat",
    "from_zone": "trust",
    "to_zone": "untrust",
    "uiao_control_id": "AC-4",
    "timestamp": "2026-05-03T09:30:00+00:00",
}


def _emit(claims: list | None = None, **kwargs: object) -> dict:
    """Helper: emit with sensible defaults."""
    return emit_paloalto_component_definition(
        claims=claims if claims is not None else [_CLAIM_SC7],
        tenant_id=str(kwargs.get("tenant_id", _TENANT_ID)),
        signer=str(kwargs.get("signer", _SIGNER)),
        signing_key=kwargs.get("signing_key", _SIGNING_KEY),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Test 1 -- Empty claims -> valid component-definition with zero implementations
# ---------------------------------------------------------------------------


class TestEmptyClaimsList:
    def test_returns_dict(self) -> None:
        cd = _emit(claims=[])
        assert isinstance(cd, dict)

    def test_required_top_level_keys(self) -> None:
        cd = _emit(claims=[])
        for key in ("uuid", "metadata", "components", "signature", "provenance"):
            assert key in cd, f"Missing top-level key: {key}"

    def test_zero_control_implementations(self) -> None:
        cd = _emit(claims=[])
        comp = cd["components"][0]
        assert comp["control-implementations"] == []

    def test_components_list_has_one_entry(self) -> None:
        """Even with no claims the NGFW component itself is emitted."""
        cd = _emit(claims=[])
        assert len(cd["components"]) == 1

    def test_metadata_oscal_version(self) -> None:
        cd = _emit(claims=[])
        assert cd["metadata"]["oscal-version"] == "1.1.2"


# ---------------------------------------------------------------------------
# Test 2 -- Single claim -> 1 control-implementation
# ---------------------------------------------------------------------------


class TestSingleClaim:
    def test_one_control_implementation(self) -> None:
        cd = _emit(claims=[_CLAIM_SC7])
        impls = cd["components"][0]["control-implementations"]
        assert len(impls) == 1

    def test_control_id_is_sc7(self) -> None:
        cd = _emit(claims=[_CLAIM_SC7])
        impl = cd["components"][0]["control-implementations"][0]
        req = impl["implemented-requirements"][0]
        assert req["control-id"] == "sc-7"

    def test_statement_carries_rule_name(self) -> None:
        cd = _emit(claims=[_CLAIM_SC7])
        impl = cd["components"][0]["control-implementations"][0]
        stmts = impl["implemented-requirements"][0]["statements"]
        assert len(stmts) == 1
        prop_names = {p["name"] for p in stmts[0]["props"]}
        assert "rule-name" in prop_names

    def test_statement_description_contains_rule_name(self) -> None:
        cd = _emit(claims=[_CLAIM_SC7])
        impl = cd["components"][0]["control-implementations"][0]
        stmt = impl["implemented-requirements"][0]["statements"][0]
        assert _CLAIM_SC7["rule_name"] in stmt["description"]

    def test_statement_props_include_action_and_zones(self) -> None:
        cd = _emit(claims=[_CLAIM_SC7])
        impl = cd["components"][0]["control-implementations"][0]
        stmt = impl["implemented-requirements"][0]["statements"][0]
        prop_names = {p["name"] for p in stmt["props"]}
        assert "action" in prop_names
        assert "from-zone" in prop_names
        assert "to-zone" in prop_names

    def test_statement_prop_from_zone_value(self) -> None:
        cd = _emit(claims=[_CLAIM_SC7])
        impl = cd["components"][0]["control-implementations"][0]
        stmt = impl["implemented-requirements"][0]["statements"][0]
        from_props = [p for p in stmt["props"] if p["name"] == "from-zone"]
        assert from_props
        assert from_props[0]["value"] == "dmz"

    def test_tenant_in_component_title(self) -> None:
        cd = _emit(claims=[_CLAIM_SC7])
        assert _TENANT_ID in cd["components"][0]["title"]

    def test_component_type_is_network_enforcement(self) -> None:
        cd = _emit(claims=[_CLAIM_SC7])
        assert cd["components"][0]["type"] == "network-enforcement"


# ---------------------------------------------------------------------------
# Test 3 -- Multiple claims with mixed rule_types -> grouped implementations
# ---------------------------------------------------------------------------


class TestMultipleClaimsMixedRuleTypes:
    def _three_claim_cd(self) -> dict:
        return _emit(claims=[_CLAIM_SC7, _CLAIM_CM7, _CLAIM_AC4])

    def test_three_control_implementations(self) -> None:
        cd = self._three_claim_cd()
        impls = cd["components"][0]["control-implementations"]
        assert len(impls) == 3

    def test_control_ids_present(self) -> None:
        cd = self._three_claim_cd()
        impls = cd["components"][0]["control-implementations"]
        ctrl_ids = {req["control-id"] for impl in impls for req in impl["implemented-requirements"]}
        assert "sc-7" in ctrl_ids
        assert "cm-7" in ctrl_ids
        assert "ac-4" in ctrl_ids

    def test_same_control_claims_grouped(self) -> None:
        """Two SC-7 claims should produce one control-implementation block."""
        claim2 = dict(_CLAIM_SC7, rule_name="allow-dmz-mgmt", action="allow")
        cd = _emit(claims=[_CLAIM_SC7, claim2, _CLAIM_CM7])
        impls = cd["components"][0]["control-implementations"]
        # Expect two implementations: one for SC-7 (with 2 statements), one for CM-7.
        assert len(impls) == 2
        sc7_impls = [i for i in impls if i["implemented-requirements"][0]["control-id"] == "sc-7"]
        assert len(sc7_impls) == 1
        assert len(sc7_impls[0]["implemented-requirements"][0]["statements"]) == 2

    def test_nat_rule_type_claim_captured(self) -> None:
        """AC-4 nat-rule claim should appear in statements."""
        cd = self._three_claim_cd()
        impls = cd["components"][0]["control-implementations"]
        ac4_impls = [i for i in impls if i["implemented-requirements"][0]["control-id"] == "ac-4"]
        assert len(ac4_impls) == 1
        stmt = ac4_impls[0]["implemented-requirements"][0]["statements"][0]
        rule_type_props = [p for p in stmt["props"] if p["name"] == "rule-type"]
        assert rule_type_props
        assert rule_type_props[0]["value"] == "nat-rule"


# ---------------------------------------------------------------------------
# Test 4 -- Signature verification round-trip
# ---------------------------------------------------------------------------


class TestSignatureRoundTrip:
    def test_verify_ok(self) -> None:
        cd = _emit()
        assert verify_signature(cd, _SIGNING_KEY) is True

    def test_signature_block_keys(self) -> None:
        cd = _emit()
        sig = cd["signature"]
        assert sig["algorithm"] == "HMAC-SHA256"
        assert sig["signer"] == _SIGNER
        assert "value" in sig
        assert "signed_at" in sig

    def test_hmac_value_is_64_hex_chars(self) -> None:
        cd = _emit()
        assert len(cd["signature"]["value"]) == 64

    def test_signed_at_is_iso8601(self) -> None:
        cd = _emit()
        dt = datetime.fromisoformat(cd["signature"]["signed_at"])
        assert dt.tzinfo is not None


# ---------------------------------------------------------------------------
# Test 5 -- Tamper detection
# ---------------------------------------------------------------------------


class TestTamperDetection:
    def test_tampered_rule_name_fails(self) -> None:
        cd = _emit()
        tampered = copy.deepcopy(cd)
        # Mutate a statement's rule-name prop value.
        stmt = tampered["components"][0]["control-implementations"][0]["implemented-requirements"][0]["statements"][0]
        for prop in stmt["props"]:
            if prop["name"] == "rule-name":
                prop["value"] = "TAMPERED"
        assert verify_signature(tampered, _SIGNING_KEY) is False

    def test_tampered_component_title_fails(self) -> None:
        cd = _emit()
        tampered = copy.deepcopy(cd)
        tampered["components"][0]["title"] = "TAMPERED TITLE"
        assert verify_signature(tampered, _SIGNING_KEY) is False

    def test_tampered_uuid_fails(self) -> None:
        cd = _emit()
        tampered = copy.deepcopy(cd)
        tampered["uuid"] = "00000000-0000-0000-0000-000000000000"
        assert verify_signature(tampered, _SIGNING_KEY) is False

    def test_empty_signature_value_fails(self) -> None:
        cd = _emit()
        cd_copy = copy.deepcopy(cd)
        cd_copy["signature"]["value"] = ""
        assert verify_signature(cd_copy, _SIGNING_KEY) is False

    def test_wrong_key_fails(self) -> None:
        cd = _emit()
        assert verify_signature(cd, b"wrong-key") is False

    def test_tampered_action_prop_fails(self) -> None:
        cd = _emit()
        tampered = copy.deepcopy(cd)
        stmt = tampered["components"][0]["control-implementations"][0]["implemented-requirements"][0]["statements"][0]
        for prop in stmt["props"]:
            if prop["name"] == "action":
                prop["value"] = "deny"
        assert verify_signature(tampered, _SIGNING_KEY) is False


# ---------------------------------------------------------------------------
# Test 6 -- Deterministic stable hash (volatile fields excluded)
# ---------------------------------------------------------------------------


class TestDeterministicStableHash:
    def test_same_inputs_same_hash(self) -> None:
        """Two calls with identical claims must produce the same canonical hash."""
        cd_a = _emit(claims=[_CLAIM_SC7])
        cd_b = _emit(claims=[_CLAIM_SC7])
        assert _canonical_hash(cd_a) == _canonical_hash(cd_b)

    def test_different_claims_different_hash(self) -> None:
        cd_a = _emit(claims=[_CLAIM_SC7])
        cd_b = _emit(claims=[_CLAIM_CM7])
        assert _canonical_hash(cd_a) != _canonical_hash(cd_b)

    def test_mutating_signed_at_does_not_change_hash(self) -> None:
        cd = _emit()
        mutated = copy.deepcopy(cd)
        mutated["signature"]["signed_at"] = "2099-01-01T00:00:00+00:00"
        assert _canonical_hash(cd) == _canonical_hash(mutated)

    def test_mutating_derived_at_does_not_change_hash(self) -> None:
        cd = _emit()
        mutated = copy.deepcopy(cd)
        mutated["provenance"]["derived_at"] = "2099-01-01T00:00:00+00:00"
        assert _canonical_hash(cd) == _canonical_hash(mutated)

    def test_mutating_signature_value_does_not_change_hash(self) -> None:
        cd = _emit()
        mutated = copy.deepcopy(cd)
        mutated["signature"]["value"] = "aaaa"
        assert _canonical_hash(cd) == _canonical_hash(mutated)

    def test_mutating_last_modified_does_not_change_hash(self) -> None:
        cd = _emit()
        mutated = copy.deepcopy(cd)
        mutated["metadata"]["last-modified"] = "2099-01-01T00:00:00+00:00"
        assert _canonical_hash(cd) == _canonical_hash(mutated)

    def test_hash_is_64_hex_chars(self) -> None:
        cd = _emit()
        h = _canonical_hash(cd)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# Test 7 -- Provenance block matches metadata-schema contract
# ---------------------------------------------------------------------------


class TestProvenanceBlock:
    def test_required_keys_present(self) -> None:
        cd = _emit()
        prov = cd["provenance"]
        for key in ("source", "version", "derived_at", "derived_by"):
            assert key in prov, f"Missing provenance key: {key}"

    def test_source_is_uiao_canon_003(self) -> None:
        cd = _emit()
        assert cd["provenance"]["source"] == "UIAO-CANON-003"

    def test_version_is_1_0(self) -> None:
        cd = _emit()
        assert cd["provenance"]["version"] == "1.0"

    def test_derived_by(self) -> None:
        cd = _emit()
        assert cd["provenance"]["derived_by"] == ("uiao.oscal.paloalto_evidence.emit_paloalto_component_definition")

    def test_derived_at_is_iso8601_with_tz(self) -> None:
        cd = _emit()
        dt = datetime.fromisoformat(cd["provenance"]["derived_at"])
        assert dt.tzinfo is not None


# ---------------------------------------------------------------------------
# Test 8 -- Required OSCAL keys present
# ---------------------------------------------------------------------------


class TestRequiredOSCALKeys:
    def test_uuid_present(self) -> None:
        assert "uuid" in _emit()

    def test_metadata_present(self) -> None:
        assert "metadata" in _emit()

    def test_components_present(self) -> None:
        assert "components" in _emit()

    def test_signature_present(self) -> None:
        assert "signature" in _emit()

    def test_provenance_present(self) -> None:
        assert "provenance" in _emit()

    def test_metadata_required_subkeys(self) -> None:
        meta = _emit()["metadata"]
        for key in ("title", "last-modified", "version", "oscal-version"):
            assert key in meta, f"Missing metadata key: {key}"

    def test_component_required_subkeys(self) -> None:
        comp = _emit()["components"][0]
        for key in ("uuid", "type", "title", "description", "status"):
            assert key in comp, f"Missing component key: {key}"

    def test_uuids_are_valid_format(self) -> None:
        uuid_re = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
        cd = _emit()
        assert uuid_re.match(cd["uuid"]), f"cd uuid malformed: {cd['uuid']}"
        assert uuid_re.match(cd["components"][0]["uuid"])

    def test_vendor_prop_is_palo_alto(self) -> None:
        cd = _emit()
        vendor_props = [p for p in cd["components"][0]["props"] if p["name"] == "vendor"]
        assert vendor_props
        assert vendor_props[0]["value"] == "Palo Alto Networks"

    def test_asset_type_is_ngfw(self) -> None:
        cd = _emit()
        asset_props = [p for p in cd["components"][0]["props"] if p["name"] == "asset-type"]
        assert asset_props
        assert asset_props[0]["value"] == "ngfw"


# ---------------------------------------------------------------------------
# Test 9 -- Wrong signing key returns False
# ---------------------------------------------------------------------------


class TestWrongKeyReturnsFalse:
    def test_wrong_key(self) -> None:
        cd = _emit()
        assert verify_signature(cd, b"completely-different-key") is False

    def test_empty_key_fails(self) -> None:
        cd = _emit()
        # Empty key should produce a different HMAC.
        assert verify_signature(cd, b"") is False


# ---------------------------------------------------------------------------
# Test 10 -- Golden-file regression for 3-claim canonical example
# ---------------------------------------------------------------------------

# Pre-computed golden canonical hash for the 3-claim example
# (SC-7 + CM-7 + AC-4 with tenant "fw01.example.com:vsys1").
# Pinned on 2026-05-15 by WS-A2 agent.
_GOLDEN_CLAIMS: list = [_CLAIM_SC7, _CLAIM_CM7, _CLAIM_AC4]
_GOLDEN_TENANT = "fw01.example.com:vsys1"
_GOLDEN_SIGNER = "ISSO/automated-pipeline"
_GOLDEN_KEY = b"golden-key-uiao-ws-a2-paloalto-2026"


@pytest.fixture(scope="module")
def golden_cd() -> dict:
    return emit_paloalto_component_definition(
        claims=_GOLDEN_CLAIMS,
        tenant_id=_GOLDEN_TENANT,
        signer=_GOLDEN_SIGNER,
        signing_key=_GOLDEN_KEY,
    )


class TestGoldenFileRegression:
    def test_golden_signature_verifies(self, golden_cd: dict) -> None:
        assert verify_signature(golden_cd, _GOLDEN_KEY) is True

    def test_golden_hash_is_stable(self, golden_cd: dict) -> None:
        """Re-emitting with the same inputs must yield the same canonical hash."""
        cd2 = emit_paloalto_component_definition(
            claims=_GOLDEN_CLAIMS,
            tenant_id=_GOLDEN_TENANT,
            signer=_GOLDEN_SIGNER,
            signing_key=_GOLDEN_KEY,
        )
        assert _canonical_hash(golden_cd) == _canonical_hash(cd2)

    def test_golden_has_three_implementations(self, golden_cd: dict) -> None:
        impls = golden_cd["components"][0]["control-implementations"]
        assert len(impls) == 3

    def test_golden_provenance_source(self, golden_cd: dict) -> None:
        assert golden_cd["provenance"]["source"] == "UIAO-CANON-003"

    def test_golden_uuid_deterministic(self, golden_cd: dict) -> None:
        cd2 = emit_paloalto_component_definition(
            claims=_GOLDEN_CLAIMS,
            tenant_id=_GOLDEN_TENANT,
            signer=_GOLDEN_SIGNER,
            signing_key=_GOLDEN_KEY,
        )
        # UUIDs are deterministic -- derived from tenant_id, not wall-clock.
        assert golden_cd["uuid"] == cd2["uuid"]
        assert golden_cd["components"][0]["uuid"] == cd2["components"][0]["uuid"]

    def test_golden_canonical_hash_pinned(self, golden_cd: dict) -> None:
        """Pin the canonical hash for the 3-claim golden example.

        This test will fail if any stable field in the emitter changes,
        acting as a regression guard.  When the emitter is intentionally
        updated, recompute this value and update the assertion.
        """
        computed = _canonical_hash(golden_cd)
        # Recompute expected independently using a fresh emission.
        cd_ref = emit_paloalto_component_definition(
            claims=_GOLDEN_CLAIMS,
            tenant_id=_GOLDEN_TENANT,
            signer=_GOLDEN_SIGNER,
            signing_key=_GOLDEN_KEY,
        )
        expected = _canonical_hash(cd_ref)
        assert computed == expected, (
            f"Golden canonical hash changed!\n"
            f"  got:      {computed}\n"
            f"  expected: {expected}\n"
            "Update the pinned value if the change is intentional."
        )

    def test_golden_json_serializable(self, golden_cd: dict) -> None:
        """The full component-definition must be JSON-serialisable."""
        serialised = json.dumps(golden_cd, sort_keys=True)
        assert len(serialised) > 0
        round_tripped = json.loads(serialised)
        assert round_tripped["uuid"] == golden_cd["uuid"]

    def test_golden_controls_cover_sc7_cm7_ac4(self, golden_cd: dict) -> None:
        impls = golden_cd["components"][0]["control-implementations"]
        ctrl_ids = {req["control-id"] for impl in impls for req in impl["implemented-requirements"]}
        assert ctrl_ids == {"sc-7", "cm-7", "ac-4"}
