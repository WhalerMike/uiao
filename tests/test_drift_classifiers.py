from __future__ import annotations
import pytest
from uiao.governance.drift import DRIFT_AUTHZ, DRIFT_IDENTITY, build_drift_state, classify_authz_drift, classify_drift, classify_identity_drift
from uiao.ir.models.core import ProvenanceRecord

PROV = ProvenanceRecord(source="test", timestamp="2026-04-20T00:00:00Z", version="0.1.0")
CODEBOOK = {"ORG", "ORG-IT", "ORG-IT-SEC", "ORG-IT-SEC-SOC", "ORG-FIN", "ORG-HR"}

class TestBuildDriftState:
    def test_benign_when_identical(self):
        state = {"key": "value"}
        ds = build_drift_state(resource_id="r1", policy_ref="p1", expected_state=state, actual_state=state, provenance=PROV)
        assert not ds.drift_detected
        assert ds.classification == "benign"
        assert ds.drift_class is None

    def test_risky_on_small_delta(self):
        ds = build_drift_state(resource_id="r1", policy_ref="p1", expected_state={"a": 1}, actual_state={"a": 2}, provenance=PROV)
        assert ds.drift_detected
        assert ds.classification == "risky"

    def test_drift_class_passthrough(self):
        ds = build_drift_state(resource_id="r1", policy_ref="p1", expected_state={"a": 1}, actual_state={"a": 2}, provenance=PROV, drift_class="DRIFT-SCHEMA")
        assert ds.drift_class == "DRIFT-SCHEMA"

class TestClassifyAuthzDrift:
    def test_returns_none_when_no_authz_change(self):
        result = classify_authz_drift(resource_id="u1", policy_ref="p1", expected_state={"display_name": "Alice"}, actual_state={"display_name": "Alice B"}, provenance=PROV)
        assert result is None

    def test_detects_role_assignment_change(self):
        result = classify_authz_drift(resource_id="u1", policy_ref="p1", expected_state={"role_assignments": ["Reader"]}, actual_state={"role_assignments": ["Reader", "Owner"]}, provenance=PROV)
        assert result is not None
        assert result.drift_class == DRIFT_AUTHZ

    def test_unconstrained_delegation_unauthorized(self):
        result = classify_authz_drift(resource_id="svc1", policy_ref="p1", expected_state={"kerberos_delegation": "constrained"}, actual_state={"kerberos_delegation": "unconstrained"}, provenance=PROV)
        assert result is not None
        assert result.drift_class == DRIFT_AUTHZ
        assert result.classification == "unauthorized"

    def test_no_drift_identical(self):
        state = {"role_assignments": ["Reader"], "kerberos_delegation": "constrained"}
        assert classify_authz_drift(resource_id="r1", policy_ref="p1", expected_state=state, actual_state=state, provenance=PROV) is None

class TestClassifyIdentityDrift:
    def test_returns_none_when_valid(self):
        result = classify_identity_drift(resource_id="u1", policy_ref="p1", expected_state={"orgpath": "ORG-IT"}, actual_state={"orgpath": "ORG-IT"}, provenance=PROV)
        assert result is None

    def test_detects_missing_orgpath(self):
        result = classify_identity_drift(resource_id="u1", policy_ref="p1", expected_state={"orgpath": "ORG-IT"}, actual_state={"display_name": "Alice"}, provenance=PROV)
        assert result is not None
        assert result.drift_class == DRIFT_IDENTITY
        assert result.classification == "unauthorized"

    def test_detects_malformed_orgpath(self):
        result = classify_identity_drift(resource_id="u1", policy_ref="p1", expected_state={"orgpath": "ORG-IT"}, actual_state={"orgpath": "org-it"}, provenance=PROV)
        assert result is not None
        assert result.drift_class == DRIFT_IDENTITY

    def test_detects_orgpath_not_in_codebook(self):
        result = classify_identity_drift(resource_id="u1", policy_ref="p1", expected_state={"orgpath": "ORG-IT"}, actual_state={"orgpath": "ORG-GHOST"}, provenance=PROV, orgpath_codebook=CODEBOOK)
        assert result is not None
        assert result.drift_class == DRIFT_IDENTITY

    def test_lifecycle_inconsistency(self):
        result = classify_identity_drift(resource_id="u1", policy_ref="p1", expected_state={"lifecycle_state": "ACTIVE", "account_enabled": True}, actual_state={"lifecycle_state": "ACTIVE", "account_enabled": False}, provenance=PROV)
        assert result is not None
        assert result.drift_class == DRIFT_IDENTITY

    def test_no_drift_identical(self):
        state = {"orgpath": "ORG-IT", "employee_id": "EMP001", "lifecycle_state": "ACTIVE"}
        assert classify_identity_drift(resource_id="r1", policy_ref="p1", expected_state=state, actual_state=state, provenance=PROV) is None

class TestClassifyDrift:
    def test_authz_takes_priority(self):
        result = classify_drift(resource_id="u1", policy_ref="p1", expected_state={"orgpath": "ORG-IT", "role_assignments": ["Reader"]}, actual_state={"orgpath": None, "role_assignments": ["Reader", "Owner"]}, provenance=PROV)
        assert result.drift_class == DRIFT_AUTHZ

    def test_identity_fires_when_no_authz(self):
        result = classify_drift(resource_id="u1", policy_ref="p1", expected_state={"orgpath": "ORG-IT"}, actual_state={"orgpath": None}, provenance=PROV)
        assert result.drift_class == DRIFT_IDENTITY

    def test_fallback_unclassified(self):
        # States with valid orgpath and no authz signals — only display_name changes
        result = classify_drift(resource_id="u1", policy_ref="p1", expected_state={"orgpath": "ORG-IT", "display_name": "Alice"}, actual_state={"orgpath": "ORG-IT", "display_name": "Alice B"}, provenance=PROV)
        assert result.drift_class is None
