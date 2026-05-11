"""Tests for uiao.governance.application_identity (UIAO_129).

Coverage targets:

1. ApplicationIdentity construction + id-pattern enforcement.
2. Binding parsing from canon-shape mappings (incl. unknown-binding drop).
3. Lifecycle transition graph: every legal transition + every illegal one.
4. Quarantine-requires-drift-finding-id constraint (UIAO_129 §4).
5. Registry load (happy path + parse-fail tolerance).
6. Each of the three drift-detection helpers:
   - detect_schema_drift: missing required bindings -> DRIFT-SCHEMA P2.
   - detect_authz_drift: subnet/IP targets -> DRIFT-AUTHZ P2.
   - detect_provenance_drift: missing grouping key -> DRIFT-PROVENANCE P3.
7. Binding.is_stale: time-window logic incl. tz-naive verified_at.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from uiao.governance.application_identity import (
    APP_ID_PATTERN,
    REQUIRED_BINDING_KINDS,
    ApplicationIdentity,
    ApplicationIdentityRegistry,
    Binding,
    BindingKind,
    DriftFinding,
    LifecycleState,
    detect_authz_drift,
    detect_provenance_drift,
    detect_schema_drift,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _full_bindings() -> dict[BindingKind, Binding]:
    """Return a complete six-binding set so tests can drop one to exercise
    the missing-binding path."""
    return {
        BindingKind.DNS: Binding(BindingKind.DNS, "infoblox", "payroll.agency.gov"),
        BindingKind.ADDRESS: Binding(BindingKind.ADDRESS, "infoblox", "10.42.0.0/24"),
        BindingKind.IAM: Binding(BindingKind.IAM, "entra-id", "spiffe://agency/payroll"),
        BindingKind.TRUST: Binding(BindingKind.TRUST, "entra-id", "thumbprint:ABC123"),
        BindingKind.SEGMENTATION: Binding(BindingKind.SEGMENTATION, "palo-alto", "seg:payroll-prod"),
        BindingKind.LOCATION: Binding(BindingKind.LOCATION, "azure-arc", "us-gov-virginia"),
    }


def _new_app(state: LifecycleState = LifecycleState.PROPOSED) -> ApplicationIdentity:
    return ApplicationIdentity(
        id="app:payroll",
        name="Payroll",
        tenant_id="agency",
        lifecycle_state=state,
        bindings=_full_bindings(),
    )


# ---------------------------------------------------------------------------
# Construction + id pattern
# ---------------------------------------------------------------------------


def test_app_id_pattern_accepts_kebab_slug() -> None:
    assert APP_ID_PATTERN.match("app:payroll")
    assert APP_ID_PATTERN.match("app:payroll-svc-2")
    assert APP_ID_PATTERN.match("app:p1")


def test_app_id_pattern_rejects_bad_shapes() -> None:
    bad = ["payroll", "app:", "app:Payroll", "app:-leading-hyphen", "app:trailing-", "app:has_underscore"]
    for value in bad:
        assert not APP_ID_PATTERN.match(value), f"{value!r} should be rejected"


def test_application_identity_rejects_invalid_id() -> None:
    with pytest.raises(ValueError, match="does not match required pattern"):
        ApplicationIdentity(
            id="not-an-app-urn",
            name="x",
            tenant_id="t",
            lifecycle_state=LifecycleState.PROPOSED,
        )


# ---------------------------------------------------------------------------
# from_mapping parsing
# ---------------------------------------------------------------------------


def test_from_mapping_round_trips_bindings() -> None:
    raw = {
        "id": "app:payroll",
        "name": "Payroll",
        "tenant_id": "agency",
        "lifecycle_state": "active",
        "bindings": {
            "dns": {"authority_adapter": "infoblox", "value": "payroll.agency.gov"},
            "address": {"authority_adapter": "infoblox", "value": "10.42.0.0/24"},
            "iam": {"authority_adapter": "entra-id", "value": "spiffe://agency/payroll"},
            "trust": {"authority_adapter": "entra-id", "value": "thumbprint:ABC"},
            "segmentation": {"authority_adapter": "palo-alto", "value": "seg:payroll"},
            "location": {"authority_adapter": "azure-arc", "value": "us-gov-virginia"},
        },
    }
    app = ApplicationIdentity.from_mapping(raw)
    assert app.id == "app:payroll"
    assert app.lifecycle_state is LifecycleState.ACTIVE
    assert set(app.bindings.keys()) == {BindingKind(k) for k in REQUIRED_BINDING_KINDS}


def test_from_mapping_drops_unknown_binding_kinds() -> None:
    """Schema gate normally catches this; the runtime is defensive too."""
    raw = {
        "id": "app:payroll",
        "name": "Payroll",
        "tenant_id": "agency",
        "lifecycle_state": "proposed",
        "bindings": {
            "dns": {"authority_adapter": "infoblox", "value": "payroll.agency.gov"},
            "bogus_kind": {"authority_adapter": "x", "value": "y"},
        },
    }
    app = ApplicationIdentity.from_mapping(raw)
    assert "bogus_kind" not in {b.kind.value for b in app.bindings.values()}
    assert BindingKind.DNS in app.bindings


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------


def test_legal_transition_proposed_to_provisioned() -> None:
    app = _new_app()
    t = app.transition_to(new_state=LifecycleState.PROVISIONED, at=datetime(2026, 5, 10, tzinfo=timezone.utc))
    assert t.from_state is LifecycleState.PROPOSED
    assert t.to_state is LifecycleState.PROVISIONED
    assert app.lifecycle_state is LifecycleState.PROVISIONED
    assert len(app.transition_history) == 1


def test_illegal_transition_proposed_to_active_raises() -> None:
    app = _new_app()
    with pytest.raises(ValueError, match="Disallowed transition"):
        app.transition_to(new_state=LifecycleState.ACTIVE, at=datetime(2026, 5, 10, tzinfo=timezone.utc))


def test_quarantine_without_finding_id_raises() -> None:
    app = _new_app(state=LifecycleState.ACTIVE)
    with pytest.raises(ValueError, match="requires a drift_finding_id"):
        app.transition_to(new_state=LifecycleState.QUARANTINED, at=datetime.now(timezone.utc))


def test_quarantine_with_finding_id_succeeds() -> None:
    app = _new_app(state=LifecycleState.ACTIVE)
    t = app.transition_to(
        new_state=LifecycleState.QUARANTINED,
        at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        drift_finding_id="DRIFT-IDENTITY-2026-05-10-001",
        reason="cert chain not bound to canonical DNS",
    )
    assert app.lifecycle_state is LifecycleState.QUARANTINED
    assert t.drift_finding_id == "DRIFT-IDENTITY-2026-05-10-001"


def test_retired_is_terminal() -> None:
    app = _new_app(state=LifecycleState.RETIRED)
    for target in (
        LifecycleState.PROPOSED,
        LifecycleState.PROVISIONED,
        LifecycleState.ACTIVE,
        LifecycleState.QUARANTINED,
    ):
        with pytest.raises(ValueError, match="Disallowed transition"):
            app.transition_to(new_state=target, at=datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_loads_yaml_files(tmp_path: Path) -> None:
    canon_dir = tmp_path / "applications"
    canon_dir.mkdir()
    (canon_dir / "payroll.yaml").write_text(
        """
id: app:payroll
name: Payroll
tenant_id: agency
lifecycle_state: active
bindings:
  dns: {authority_adapter: infoblox, value: payroll.agency.gov}
  address: {authority_adapter: infoblox, value: 10.42.0.0/24}
  iam: {authority_adapter: entra-id, value: spiffe://agency/payroll}
  trust: {authority_adapter: entra-id, value: thumbprint:ABC}
  segmentation: {authority_adapter: palo-alto, value: seg:payroll}
  location: {authority_adapter: azure-arc, value: us-gov-virginia}
""",
        encoding="utf-8",
    )
    registry = ApplicationIdentityRegistry.from_yaml(canon_dir)
    app = registry.get("app:payroll")
    assert app is not None
    assert app.tenant_id == "agency"


def test_registry_skips_malformed_files(tmp_path: Path) -> None:
    canon_dir = tmp_path / "applications"
    canon_dir.mkdir()
    (canon_dir / "broken.yaml").write_text("this: is: not valid yaml: [", encoding="utf-8")
    (canon_dir / "wrong-shape.yaml").write_text("- just a list\n- not a mapping\n", encoding="utf-8")
    (canon_dir / "missing-fields.yaml").write_text("id: app:nope\n", encoding="utf-8")
    registry = ApplicationIdentityRegistry.from_yaml(canon_dir)
    assert registry.applications == {}


def test_registry_for_tenant_filters() -> None:
    a1 = _new_app()
    a2 = ApplicationIdentity(
        id="app:other",
        name="Other",
        tenant_id="other-agency",
        lifecycle_state=LifecycleState.PROPOSED,
        bindings=_full_bindings(),
    )
    registry = ApplicationIdentityRegistry(applications={a1.id: a1, a2.id: a2})
    assert [a.id for a in registry.for_tenant("agency")] == ["app:payroll"]
    assert [a.id for a in registry.for_tenant("other-agency")] == ["app:other"]


# ---------------------------------------------------------------------------
# Drift detection helpers
# ---------------------------------------------------------------------------


def test_detect_schema_drift_full_app_emits_nothing() -> None:
    assert detect_schema_drift(_new_app()) == []


def test_detect_schema_drift_lists_missing_bindings() -> None:
    bindings = _full_bindings()
    del bindings[BindingKind.TRUST]
    del bindings[BindingKind.LOCATION]
    app = ApplicationIdentity(
        id="app:partial",
        name="Partial",
        tenant_id="agency",
        lifecycle_state=LifecycleState.PROPOSED,
        bindings=bindings,
    )
    findings = detect_schema_drift(app)
    assert {f.drift_class for f in findings} == {"DRIFT-SCHEMA"}
    assert {f.severity for f in findings} == {"P2"}
    missing = sorted(f.detail for f in findings)
    assert "missing required binding: 'location'" in missing[0]
    assert "missing required binding: 'trust'" in missing[1]


def test_detect_authz_drift_flags_subnet_targets() -> None:
    findings = detect_authz_drift(
        policy_rule_targets=["app:payroll", "10.42.0.0/24", "app:billing"],
        known_application_ids={"app:payroll", "app:billing"},
    )
    assert len(findings) == 1
    assert findings[0].drift_class == "DRIFT-AUTHZ"
    assert findings[0].severity == "P2"
    assert "10.42.0.0/24" in findings[0].detail


def test_detect_authz_drift_clean_when_all_targets_known() -> None:
    findings = detect_authz_drift(
        policy_rule_targets=["app:payroll", "app:billing"],
        known_application_ids={"app:payroll", "app:billing"},
    )
    assert findings == []


def test_detect_provenance_drift_flags_event_without_grouping_key() -> None:
    findings = detect_provenance_drift(telemetry_event={"event_type": "flow_record"})
    assert len(findings) == 1
    assert findings[0].drift_class == "DRIFT-PROVENANCE"
    assert findings[0].severity == "P3"
    assert "application_identity" in findings[0].detail


def test_detect_provenance_drift_passes_event_with_grouping_key() -> None:
    findings = detect_provenance_drift(
        telemetry_event={"event_type": "flow_record", "application_identity": "app:payroll"}
    )
    assert findings == []


def test_detect_provenance_drift_empty_grouping_key_is_drift() -> None:
    findings = detect_provenance_drift(telemetry_event={"event_type": "flow_record", "application_identity": ""})
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# Binding freshness
# ---------------------------------------------------------------------------


def test_binding_is_stale_with_no_verified_at() -> None:
    binding = Binding(BindingKind.DNS, "infoblox", "payroll.agency.gov")
    assert binding.is_stale(freshness_window_hours=24) is True


def test_binding_is_stale_outside_window() -> None:
    now = datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc)
    verified = now - timedelta(hours=48)
    binding = Binding(BindingKind.DNS, "infoblox", "payroll.agency.gov", verified_at=verified)
    assert binding.is_stale(freshness_window_hours=24, now=now) is True


def test_binding_is_fresh_inside_window() -> None:
    now = datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc)
    verified = now - timedelta(hours=12)
    binding = Binding(BindingKind.DNS, "infoblox", "payroll.agency.gov", verified_at=verified)
    assert binding.is_stale(freshness_window_hours=24, now=now) is False


def test_binding_is_stale_handles_naive_verified_at() -> None:
    now = datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc)
    naive_verified = datetime(2026, 5, 10, 6, 0)  # naive, treated as UTC
    binding = Binding(BindingKind.DNS, "infoblox", "payroll.agency.gov", verified_at=naive_verified)
    assert binding.is_stale(freshness_window_hours=12, now=now) is False
    assert binding.is_stale(freshness_window_hours=4, now=now) is True


# ---------------------------------------------------------------------------
# DriftFinding stringification (smoke-level coverage)
# ---------------------------------------------------------------------------


def test_drift_finding_str_includes_class_and_target() -> None:
    f = DriftFinding(
        drift_class="DRIFT-SCHEMA",
        severity="P2",
        application_id="app:payroll",
        detail="missing required binding: 'iam'",
    )
    s = str(f)
    assert "DRIFT-SCHEMA" in s and "P2" in s and "app:payroll" in s and "iam" in s


def test_drift_finding_str_uses_global_for_no_app() -> None:
    f = DriftFinding(
        drift_class="DRIFT-AUTHZ",
        severity="P2",
        application_id=None,
        detail="subnet target",
    )
    assert "<global>" in str(f)
