"""tests/test_enforcement_runtime.py — UIAO_111 tests."""
from __future__ import annotations
import pytest
from uiao.enforcement import EnforcementRuntime, EnforcementResult, RuntimeState, EPLPolicy, EnforcementAdapter
from uiao.enforcement.runtime import AdapterResult, NoOpAdapter

MFA_POLICY = EPLPolicy(
    policy_id="POL-MFA-001",
    control_id="IA-2",
    description="MFA must be enabled for all users",
    adapter_id="noop",
    condition=lambda ir: not ir.get("mfa_enabled", True),
    severity="High",
    auto_enforce=False,
)

AUTO_POLICY = EPLPolicy(
    policy_id="POL-AUTO-001",
    control_id="AC-2",
    description="Auto-enforce test policy",
    adapter_id="noop",
    condition=lambda ir: ir.get("status") == "VIOLATED",
    severity="Medium",
    auto_enforce=True,
)

class TestPolicyEvaluation:
    def test_compliant_returns_compliant_state(self):
        rt = EnforcementRuntime()
        result = rt.run(MFA_POLICY, {"id": "user-001", "mfa_enabled": True})
        assert result.state == RuntimeState.COMPLIANT
        assert result.violation_detected is False

    def test_violation_returns_violated_state(self):
        rt = EnforcementRuntime()
        result = rt.run(MFA_POLICY, {"id": "user-002", "mfa_enabled": False})
        assert result.state == RuntimeState.VIOLATED
        assert result.violation_detected is True

    def test_compliant_has_no_evidence(self):
        rt = EnforcementRuntime()
        result = rt.run(MFA_POLICY, {"id": "user-001", "mfa_enabled": True})
        assert result.evidence is None

class TestEnforcementExecution:
    def test_dry_run_skips_enforcement(self):
        rt = EnforcementRuntime(dry_run=True)
        result = rt.run(AUTO_POLICY, {"id": "ir-001", "status": "VIOLATED"})
        assert result.state == RuntimeState.VIOLATED
        assert result.adapter_result.output.get("skipped") is True

    def test_auto_enforce_with_dry_run_false(self):
        rt = EnforcementRuntime(dry_run=False)
        result = rt.run(AUTO_POLICY, {"id": "ir-001", "status": "VIOLATED"})
        assert result.state == RuntimeState.REMEDIATED
        assert result.adapter_result.success is True

    def test_custom_adapter_called(self):
        class CountingAdapter(EnforcementAdapter):
            ADAPTER_ID = "counter"
            calls = 0
            def enforce(self, ir, policy, dry_run=True):
                CountingAdapter.calls += 1
                return AdapterResult(adapter_id=self.ADAPTER_ID, success=True, output={"count": CountingAdapter.calls})

        policy = EPLPolicy("P1", "AC-2", "test", "counter", lambda ir: True, auto_enforce=True)
        rt = EnforcementRuntime(adapters={"counter": CountingAdapter()}, dry_run=False)
        rt.run(policy, {"id": "obj-1"})
        assert CountingAdapter.calls == 1

class TestEvidenceCollection:
    def test_violated_result_has_evidence(self):
        rt = EnforcementRuntime(dry_run=True)
        result = rt.run(MFA_POLICY, {"id": "user-002", "mfa_enabled": False})
        assert result.evidence is not None
        assert "hash" in result.evidence
        assert result.evidence["control_id"] == "IA-2"

    def test_evidence_hash_is_deterministic_structure(self):
        rt = EnforcementRuntime(dry_run=True)
        r1 = rt.run(MFA_POLICY, {"id": "user-002", "mfa_enabled": False})
        assert len(r1.evidence["hash"]) == 64  # SHA-256 hex

class TestPOAMUpdate:
    def test_violation_opens_poam(self):
        poam_store = []
        rt = EnforcementRuntime(poam_store=poam_store, dry_run=True)
        result = rt.run(MFA_POLICY, {"id": "user-002", "mfa_enabled": False})
        assert result.poam_action == "opened"
        assert len(poam_store) == 1
        assert poam_store[0]["status"] == "Open"

    def test_compliant_closes_existing_poam(self):
        poam_store = [{"id": "POAM-POL-MFA-001-user-003", "status": "Open"}]
        rt = EnforcementRuntime(poam_store=poam_store, dry_run=True)
        result = rt.run(MFA_POLICY, {"id": "user-003", "mfa_enabled": True})
        assert result.poam_action == "closed"
        assert poam_store[0]["status"] == "Closed"

    def test_compliant_no_existing_poam_unchanged(self):
        rt = EnforcementRuntime(dry_run=True)
        result = rt.run(MFA_POLICY, {"id": "user-new", "mfa_enabled": True})
        assert result.poam_action == "unchanged"

class TestSARUpdate:
    def test_violation_updates_sar(self):
        sar_store = {}
        rt = EnforcementRuntime(sar_store=sar_store, dry_run=True)
        rt.run(MFA_POLICY, {"id": "user-002", "mfa_enabled": False})
        assert "findings" in sar_store
        assert len(sar_store["findings"]) == 1
        assert sar_store["findings"][0]["control_id"] == "IA-2"

    def test_repeated_run_updates_existing_finding(self):
        sar_store = {}
        rt = EnforcementRuntime(sar_store=sar_store, dry_run=True)
        rt.run(MFA_POLICY, {"id": "user-002", "mfa_enabled": False})
        rt.run(MFA_POLICY, {"id": "user-002", "mfa_enabled": False})
        assert len(sar_store["findings"]) == 1

class TestBatchRun:
    def test_batch_processes_all_objects(self):
        rt = EnforcementRuntime(dry_run=True)
        objects = [
            {"id": f"user-{i}", "mfa_enabled": i % 2 == 0}
            for i in range(4)
        ]
        results = rt.run_batch(MFA_POLICY, objects)
        assert len(results) == 4
        violated = [r for r in results if r.violation_detected]
        compliant = [r for r in results if not r.violation_detected]
        assert len(violated) == 2
        assert len(compliant) == 2

class TestResultSerialization:
    def test_to_dict_has_required_keys(self):
        rt = EnforcementRuntime(dry_run=True)
        result = rt.run(MFA_POLICY, {"id": "user-002", "mfa_enabled": False})
        d = result.to_dict()
        for key in ("policy_id", "control_id", "ir_object_id", "state", "violation_detected", "executed_at"):
            assert key in d
