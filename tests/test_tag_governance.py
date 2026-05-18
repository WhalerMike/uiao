"""Tests for src/uiao/governance/tag_governance.py (UIAO_177)."""

from __future__ import annotations


from uiao.governance.tag_governance import (
    CANONICAL_KEYS,
    FORBIDDEN_KEYS,
    CanonicalTagKey,
    compute_tag_drift,
    is_canonical_key,
    is_forbidden_key,
    is_non_canonical_key,
    split_tags,
    validate_canonical_value,
)


def test_canonical_keys_are_the_four_from_uiao_177():
    assert {
        "uiao.org.path",
        "uiao.identity.lifecycle",
        "uiao.owner",
        "uiao.boundary",
    } == CANONICAL_KEYS


def test_bare_uiao_lifecycle_is_forbidden():
    assert "uiao.lifecycle" in FORBIDDEN_KEYS
    assert is_forbidden_key("uiao.lifecycle")
    assert not is_canonical_key("uiao.lifecycle")


def test_key_classification_three_partition():
    for key in ("uiao.org.path", "uiao.boundary"):
        assert is_canonical_key(key)
        assert not is_forbidden_key(key)
        assert not is_non_canonical_key(key)
    for key in ("cost-center", "team", "env"):
        assert is_non_canonical_key(key)
        assert not is_canonical_key(key)
        assert not is_forbidden_key(key)


def test_validate_canonical_value_lifecycle_enum():
    assert validate_canonical_value("uiao.identity.lifecycle", "active") is None
    assert validate_canonical_value("uiao.identity.lifecycle", "leave") is None
    assert validate_canonical_value("uiao.identity.lifecycle", "disabled") is None
    err = validate_canonical_value("uiao.identity.lifecycle", "retired")
    assert err is not None and "active" in err


def test_validate_canonical_value_boundary_enum():
    assert validate_canonical_value("uiao.boundary", "GCC-Moderate") is None
    err = validate_canonical_value("uiao.boundary", "Commercial")
    assert err is not None


def test_validate_canonical_value_string_keys():
    assert validate_canonical_value("uiao.org.path", "ORG-FIN-PAY-AR") is None
    assert validate_canonical_value("uiao.owner", "alice@example.gov") is None
    assert validate_canonical_value("uiao.org.path", "") is not None
    assert validate_canonical_value("uiao.owner", 42) is not None


def test_split_tags_partitions_three_buckets():
    tags = {
        "uiao.org.path": "ORG-A",
        "uiao.lifecycle": "active",  # forbidden
        "cost-center": "cc-123",
    }
    buckets = split_tags(tags)
    assert buckets["canonical"] == {"uiao.org.path": "ORG-A"}
    assert buckets["forbidden"] == {"uiao.lifecycle": "active"}
    assert buckets["non_canonical"] == {"cost-center": "cc-123"}


def test_compute_tag_drift_returns_empty_when_converged():
    desired = {"uiao.org.path": "ORG-A", "uiao.owner": "alice"}
    actual = {"uiao.org.path": "ORG-A", "uiao.owner": "alice"}
    records = compute_tag_drift(
        "obj-1", desired=desired, actual=actual, source_adapter="test"
    )
    assert records == []


def test_compute_tag_drift_flags_missing_canonical_key():
    desired = {"uiao.org.path": "ORG-A"}
    actual = {}
    records = compute_tag_drift(
        "obj-1", desired=desired, actual=actual, source_adapter="test"
    )
    assert len(records) == 1
    r = records[0]
    assert r.drift_class == "DRIFT-SCHEMA"
    assert r.object_facet == "tag"
    assert r.expected_value == "ORG-A"
    assert r.actual_value is None
    assert r.recommended_action == "overwrite-canonical-tag"


def test_compute_tag_drift_flags_value_mismatch_as_semantic():
    desired = {"uiao.org.path": "ORG-A"}
    actual = {"uiao.org.path": "ORG-B"}
    records = compute_tag_drift(
        "obj-1", desired=desired, actual=actual, source_adapter="test"
    )
    assert len(records) == 1
    assert records[0].drift_class == "DRIFT-SEMANTIC"


def test_compute_tag_drift_boundary_mismatch_is_critical():
    desired = {"uiao.boundary": "GCC-Moderate"}
    actual = {"uiao.boundary": "GCC-Moderate-Exception:AmazonConnect"}
    records = compute_tag_drift(
        "obj-1", desired=desired, actual=actual, source_adapter="test"
    )
    assert len(records) == 1
    assert records[0].drift_class == "DRIFT-BOUNDARY"
    assert records[0].severity == "critical"


def test_compute_tag_drift_emits_finding_for_forbidden_key():
    desired = {}
    actual = {"uiao.lifecycle": "active"}
    records = compute_tag_drift(
        "obj-1", desired=desired, actual=actual, source_adapter="test"
    )
    assert len(records) == 1
    assert records[0].drift_class == "DRIFT-SCHEMA"
    assert records[0].recommended_action == "remove-forbidden-key"


def test_compute_tag_drift_invalid_desired_value_flagged():
    desired = {"uiao.identity.lifecycle": "retired"}
    actual = {"uiao.identity.lifecycle": "retired"}
    records = compute_tag_drift(
        "obj-1", desired=desired, actual=actual, source_adapter="test"
    )
    assert len(records) == 1
    assert records[0].severity == "high"
    assert "fix-desired-state" in records[0].recommended_action


def test_canonical_tag_key_enum_values_match_keys_set():
    assert {k.value for k in CanonicalTagKey} == CANONICAL_KEYS
