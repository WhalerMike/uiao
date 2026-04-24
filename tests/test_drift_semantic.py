from __future__ import annotations
from uiao.governance.drift import DRIFT_SEMANTIC, classify_semantic_drift, classify_drift
from uiao.ir.models.core import ProvenanceRecord

PROV = ProvenanceRecord(source="test", timestamp="2026-04-20T00:00:00Z", version="0.1.0")


class TestClassifySemanticDrift:
    def test_returns_none_when_no_weakening(self):
        result = classify_semantic_drift(
            resource_id="tenant",
            policy_ref="mfa-policy",
            expected_state={"mfa_enabled": True},
            actual_state={"mfa_enabled": True},
            provenance=PROV,
        )
        assert result is None

    def test_detects_mfa_disabled(self):
        result = classify_semantic_drift(
            resource_id="tenant",
            policy_ref="mfa-policy",
            expected_state={"mfa_enabled": True},
            actual_state={"mfa_enabled": False},
            provenance=PROV,
        )
        assert result is not None
        assert result.drift_class == DRIFT_SEMANTIC
        assert result.classification == "unauthorized"

    def test_detects_legacy_auth_enabled(self):
        result = classify_semantic_drift(
            resource_id="tenant",
            policy_ref="auth-policy",
            expected_state={"legacy_auth_enabled": False},
            actual_state={"legacy_auth_enabled": True},
            provenance=PROV,
        )
        assert result is not None
        assert result.drift_class == DRIFT_SEMANTIC

    def test_detects_external_sharing(self):
        result = classify_semantic_drift(
            resource_id="site-001",
            policy_ref="sharing-policy",
            expected_state={"external_sharing_enabled": False},
            actual_state={"external_sharing_enabled": True},
            provenance=PROV,
        )
        assert result is not None
        assert result.drift_class == DRIFT_SEMANTIC

    def test_detects_audit_log_disabled(self):
        result = classify_semantic_drift(
            resource_id="tenant",
            policy_ref="audit-policy",
            expected_state={"audit_log_enabled": True},
            actual_state={"audit_log_enabled": False},
            provenance=PROV,
        )
        assert result is not None
        assert result.drift_class == DRIFT_SEMANTIC
        assert result.classification == "unauthorized"

    def test_detects_threshold_exceeded(self):
        result = classify_semantic_drift(
            resource_id="tenant",
            policy_ref="patch-policy",
            expected_state={"patch_sla_days": 30},
            actual_state={"patch_sla_days": 45},
            provenance=PROV,
        )
        assert result is not None
        assert result.drift_class == DRIFT_SEMANTIC

    def test_detects_retention_below_minimum(self):
        result = classify_semantic_drift(
            resource_id="tenant",
            policy_ref="audit-retention",
            expected_state={"audit_retention_days": 90},
            actual_state={"audit_retention_days": 30},
            provenance=PROV,
        )
        assert result is not None
        assert result.drift_class == DRIFT_SEMANTIC

    def test_no_drift_threshold_at_limit(self):
        result = classify_semantic_drift(
            resource_id="tenant",
            policy_ref="patch-policy",
            expected_state={"patch_sla_days": 30},
            actual_state={"patch_sla_days": 30},
            provenance=PROV,
        )
        assert result is None

    def test_no_drift_identical(self):
        state = {"mfa_enabled": True, "external_sharing_enabled": False}
        assert (
            classify_semantic_drift(
                resource_id="r1",
                policy_ref="p1",
                expected_state=state,
                actual_state=state,
                provenance=PROV,
            )
            is None
        )


class TestClassifyDriftSemanticPriority:
    def test_semantic_fires_after_authz(self):
        # AUTHZ takes priority over SEMANTIC
        result = classify_drift(
            resource_id="u1",
            policy_ref="p1",
            expected_state={"role_assignments": ["Reader"], "mfa_enabled": True},
            actual_state={"role_assignments": ["Reader", "Owner"], "mfa_enabled": False},
            provenance=PROV,
        )
        from uiao.governance.drift import DRIFT_AUTHZ

        assert result.drift_class == DRIFT_AUTHZ

    def test_semantic_fires_before_identity(self):
        # SEMANTIC before IDENTITY when no authz signal
        result = classify_drift(
            resource_id="u1",
            policy_ref="p1",
            expected_state={"orgpath": "ORG-IT", "mfa_enabled": True},
            actual_state={"orgpath": "ORG-IT", "mfa_enabled": False},
            provenance=PROV,
        )
        assert result.drift_class == DRIFT_SEMANTIC
