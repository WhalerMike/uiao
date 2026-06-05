from __future__ import annotations
from uiao.governance.drift import (
    DRIFT_AUTHZ,
    DRIFT_IDENTITY,
    DRIFT_PROVENANCE,
    build_drift_state,
    classify_authz_drift,
    classify_drift,
    classify_identity_drift,
    classify_provenance_drift,
)
from uiao.ir.models.core import ProvenanceRecord, canonical_hash

PROV = ProvenanceRecord(source="test", timestamp="2026-04-20T00:00:00Z", version="0.1.0")
# CODEBOOK constant removed per ADR-078 — classify_identity_drift no longer
# performs codebook lookups.


class TestBuildDriftState:
    def test_benign_when_identical(self):
        state = {"key": "value"}
        ds = build_drift_state(
            resource_id="r1", policy_ref="p1", expected_state=state, actual_state=state, provenance=PROV
        )
        assert not ds.drift_detected
        assert ds.classification == "benign"
        assert ds.drift_class is None

    def test_risky_on_small_delta(self):
        ds = build_drift_state(
            resource_id="r1", policy_ref="p1", expected_state={"a": 1}, actual_state={"a": 2}, provenance=PROV
        )
        assert ds.drift_detected
        assert ds.classification == "risky"

    def test_drift_class_passthrough(self):
        ds = build_drift_state(
            resource_id="r1",
            policy_ref="p1",
            expected_state={"a": 1},
            actual_state={"a": 2},
            provenance=PROV,
            drift_class="DRIFT-SCHEMA",
        )
        assert ds.drift_class == "DRIFT-SCHEMA"


class TestClassifyAuthzDrift:
    def test_returns_none_when_no_authz_change(self):
        result = classify_authz_drift(
            resource_id="u1",
            policy_ref="p1",
            expected_state={"display_name": "Alice"},
            actual_state={"display_name": "Alice B"},
            provenance=PROV,
        )
        assert result is None

    def test_detects_role_assignment_change(self):
        result = classify_authz_drift(
            resource_id="u1",
            policy_ref="p1",
            expected_state={"role_assignments": ["Reader"]},
            actual_state={"role_assignments": ["Reader", "Owner"]},
            provenance=PROV,
        )
        assert result is not None
        assert result.drift_class == DRIFT_AUTHZ

    def test_unconstrained_delegation_unauthorized(self):
        result = classify_authz_drift(
            resource_id="svc1",
            policy_ref="p1",
            expected_state={"kerberos_delegation": "constrained"},
            actual_state={"kerberos_delegation": "unconstrained"},
            provenance=PROV,
        )
        assert result is not None
        assert result.drift_class == DRIFT_AUTHZ
        assert result.classification == "unauthorized"

    def test_no_drift_identical(self):
        state = {"role_assignments": ["Reader"], "kerberos_delegation": "constrained"}
        assert (
            classify_authz_drift(
                resource_id="r1", policy_ref="p1", expected_state=state, actual_state=state, provenance=PROV
            )
            is None
        )


class TestClassifyIdentityDrift:
    def test_returns_none_when_valid(self):
        result = classify_identity_drift(
            resource_id="u1",
            policy_ref="p1",
            expected_state={"orgpath": "ORG-IT"},
            actual_state={"orgpath": "ORG-IT"},
            provenance=PROV,
        )
        assert result is None

    # OrgPath-specific identity-drift tests removed per ADR-078: the
    # classifier no longer performs composite-string codebook lookups,
    # format-regex validation, or "not in codebook" detection. Per-facet
    # DRIFT-IDENTITY classification returns with the Phase 5 consumer
    # rebuild.

    def test_lifecycle_sentinel_change_fires_drift(self):
        """A change to lifecycle_state (an identity sentinel field) fires
        DRIFT-IDENTITY. The lifecycle-vs-account_enabled consistency
        check at the bottom of classify_identity_drift is also exercised
        when lifecycle_state and account_enabled disagree."""
        result = classify_identity_drift(
            resource_id="u1",
            policy_ref="p1",
            expected_state={"lifecycle_state": "ACTIVE"},
            actual_state={"lifecycle_state": "SUSPENDED"},
            provenance=PROV,
        )
        assert result is not None
        assert result.drift_class == DRIFT_IDENTITY

    def test_no_drift_identical(self):
        state = {"orgpath": "ORG-IT", "employee_id": "EMP001", "lifecycle_state": "ACTIVE"}
        assert (
            classify_identity_drift(
                resource_id="r1", policy_ref="p1", expected_state=state, actual_state=state, provenance=PROV
            )
            is None
        )


class TestClassifyDrift:
    def test_authz_takes_priority(self):
        result = classify_drift(
            resource_id="u1",
            policy_ref="p1",
            expected_state={"orgpath": "ORG-IT", "role_assignments": ["Reader"]},
            actual_state={"orgpath": None, "role_assignments": ["Reader", "Owner"]},
            provenance=PROV,
        )
        assert result.drift_class == DRIFT_AUTHZ

    def test_identity_fires_when_no_authz(self):
        result = classify_drift(
            resource_id="u1",
            policy_ref="p1",
            expected_state={"orgpath": "ORG-IT"},
            actual_state={"orgpath": None},
            provenance=PROV,
        )
        assert result.drift_class == DRIFT_IDENTITY

    def test_fallback_unclassified(self):
        # States with valid orgpath and no authz signals — only display_name changes
        result = classify_drift(
            resource_id="u1",
            policy_ref="p1",
            expected_state={"orgpath": "ORG-IT", "display_name": "Alice"},
            actual_state={"orgpath": "ORG-IT", "display_name": "Alice B"},
            provenance=PROV,
        )
        assert result.drift_class is None

    def test_provenance_break_routes_before_state_classifiers(self):
        # A broken seal must be classified as DRIFT-PROVENANCE even though the
        # display_name delta would otherwise fall through to the generic path.
        sealed = ProvenanceRecord(
            source="test", timestamp="2026-04-20T00:00:00Z", version="0.1.0", content_hash="sha256:wrong"
        )
        result = classify_drift(
            resource_id="u1",
            policy_ref="p1",
            expected_state={"orgpath": "ORG-IT", "display_name": "Alice"},
            actual_state={"orgpath": "ORG-IT", "display_name": "Alice B"},
            provenance=sealed,
        )
        assert result.drift_class == DRIFT_PROVENANCE
        assert result.classification == "unauthorized"


class TestClassifyProvenanceDrift:
    def test_returns_none_for_intact_envelope(self):
        result = classify_provenance_drift(
            resource_id="r1",
            policy_ref="p1",
            expected_state={"a": 1},
            actual_state={"a": 1},
            provenance=PROV,
        )
        assert result is None

    def test_detects_incomplete_envelope(self):
        incomplete = ProvenanceRecord(source="", timestamp="2026-04-20T00:00:00Z", version="")
        result = classify_provenance_drift(
            resource_id="r1",
            policy_ref="p1",
            expected_state={"a": 1},
            actual_state={"a": 2},
            provenance=incomplete,
        )
        assert result is not None
        assert result.drift_class == DRIFT_PROVENANCE
        reasons = result.delta["provenance_reasons"]
        assert any("'source'" in r for r in reasons)
        assert any("'version'" in r for r in reasons)

    def test_intact_seal_is_not_drift(self):
        state = {"a": 1, "b": 2}
        good = ProvenanceRecord(
            source="adapter", timestamp="2026-04-20T00:00:00Z", version="1.0.0", content_hash=canonical_hash(state)
        )
        result = classify_provenance_drift(
            resource_id="r1", policy_ref="p1", expected_state=state, actual_state=state, provenance=good
        )
        assert result is None

    def test_detects_broken_seal_as_unauthorized(self):
        sealed = ProvenanceRecord(
            source="adapter", timestamp="2026-04-20T00:00:00Z", version="1.0.0", content_hash="sha256:stale"
        )
        result = classify_provenance_drift(
            resource_id="r1",
            policy_ref="p1",
            expected_state={"a": 1},
            actual_state={"a": 1},
            provenance=sealed,
        )
        assert result is not None
        assert result.drift_class == DRIFT_PROVENANCE
        assert result.classification == "unauthorized"

    def test_detects_citation_drift_against_baseline(self):
        baseline = ProvenanceRecord(source="canon:UIAO_010", timestamp="2026-04-20T00:00:00Z", version="1.0.0")
        repointed = ProvenanceRecord(source="canon:UIAO_999", timestamp="2026-04-20T00:00:00Z", version="2.0.0")
        result = classify_provenance_drift(
            resource_id="r1",
            policy_ref="p1",
            expected_state={"a": 1},
            actual_state={"a": 1},
            provenance=repointed,
            expected_provenance=baseline,
        )
        assert result is not None
        assert result.drift_class == DRIFT_PROVENANCE
        reasons = result.delta["provenance_reasons"]
        assert any("re-pointed" in r for r in reasons)
        assert any("version changed" in r for r in reasons)
