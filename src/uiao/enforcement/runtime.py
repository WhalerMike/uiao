"""UIAO Enforcement Runtime — UIAO_111."""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional


class RuntimeState:
    EVALUATING = "EVALUATING"
    COMPLIANT  = "COMPLIANT"
    VIOLATED   = "VIOLATED"
    ENFORCING  = "ENFORCING"
    REMEDIATED = "REMEDIATED"
    FAILED     = "FAILED"


@dataclass
class EPLPolicy:
    policy_id: str
    control_id: str
    description: str
    adapter_id: str
    condition: Callable[[dict], bool]
    severity: str = "Medium"
    auto_enforce: bool = False


@dataclass
class AdapterResult:
    adapter_id: str
    success: bool
    output: dict = field(default_factory=dict)
    error: Optional[str] = None


class EnforcementAdapter:
    ADAPTER_ID: str = "base"
    def enforce(self, ir_object: dict, policy: EPLPolicy, dry_run: bool = True) -> AdapterResult:
        raise NotImplementedError(f"{self.__class__.__name__}.enforce() not implemented")


class NoOpAdapter(EnforcementAdapter):
    ADAPTER_ID = "noop"
    def enforce(self, ir_object: dict, policy: EPLPolicy, dry_run: bool = True) -> AdapterResult:
        return AdapterResult(adapter_id=self.ADAPTER_ID, success=True,
                             output={"action": "noop", "dry_run": dry_run, "ir_object_id": ir_object.get("id", "")})


@dataclass
class EnforcementResult:
    policy_id: str
    control_id: str
    ir_object_id: str
    state: str
    violation_detected: bool
    adapter_result: Optional[AdapterResult] = None
    evidence: Optional[dict] = None
    poam_action: Optional[str] = None
    sar_updated: bool = False
    error: Optional[str] = None
    executed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {"policy_id": self.policy_id, "control_id": self.control_id,
                "ir_object_id": self.ir_object_id, "state": self.state,
                "violation_detected": self.violation_detected,
                "adapter_result": self.adapter_result.__dict__ if self.adapter_result else None,
                "evidence": self.evidence, "poam_action": self.poam_action,
                "sar_updated": self.sar_updated, "error": self.error, "executed_at": self.executed_at}


class EnforcementRuntime:
    def __init__(self, adapters=None, poam_store=None, sar_store=None, dry_run=True):
        self._adapters: dict = adapters or {}
        self._poam_store: list = poam_store if poam_store is not None else []
        self._sar_store: dict = sar_store if sar_store is not None else {}
        self._dry_run = dry_run

    def _get_adapter(self, adapter_id: str) -> EnforcementAdapter:
        return self._adapters.get(adapter_id, NoOpAdapter())

    def _hash(self, data: dict) -> str:
        return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _evaluate(self, policy: EPLPolicy, ir_object: dict) -> bool:
        try:
            return bool(policy.condition(ir_object))
        except Exception:
            return False

    def _enforce(self, policy: EPLPolicy, ir_object: dict, dry_run: bool) -> AdapterResult:
        try:
            return self._get_adapter(policy.adapter_id).enforce(ir_object, policy, dry_run=dry_run)
        except Exception as exc:
            return AdapterResult(adapter_id=policy.adapter_id, success=False, error=str(exc))

    def _collect_evidence(self, policy: EPLPolicy, ir_object: dict, adapter_result: AdapterResult) -> dict:
        ev = {"policy_id": policy.policy_id, "control_id": policy.control_id,
              "ir_object_id": ir_object.get("id", ""), "adapter_id": adapter_result.adapter_id,
              "adapter_success": adapter_result.success, "adapter_output": adapter_result.output,
              "collected_at": datetime.now(timezone.utc).isoformat(), "provenance_source": "enforcement-runtime"}
        ev["hash"] = self._hash(ev)
        return ev

    def _update_poam(self, policy: EPLPolicy, ir_object: dict, resolved: bool) -> str:
        ir_id = ir_object.get("id", "")
        poam_id = f"POAM-{policy.policy_id}-{ir_id}"
        existing = next((p for p in self._poam_store if p.get("id") == poam_id), None)
        if resolved:
            if existing:
                existing["status"] = "Closed"
                existing["resolved_at"] = datetime.now(timezone.utc).isoformat()
                return "closed"
            return "unchanged"
        if existing:
            existing["status"] = "Open"
            return "unchanged"
        self._poam_store.append({"id": poam_id, "policy_id": policy.policy_id,
                                  "control_id": policy.control_id, "ir_object_id": ir_id,
                                  "status": "Open", "severity": policy.severity,
                                  "opened_at": datetime.now(timezone.utc).isoformat()})
        return "opened"

    def _update_sar(self, policy: EPLPolicy, ir_object: dict, evidence: dict) -> bool:
        findings = self._sar_store.setdefault("findings", [])
        fid = f"FIND-{policy.policy_id}-{ir_object.get('id','')}"
        existing = next((f for f in findings if f.get("id") == fid), None)
        if existing:
            existing["evidence_hash"] = evidence.get("hash", "")
            existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            findings.append({"id": fid, "control_id": policy.control_id, "policy_id": policy.policy_id,
                              "severity": policy.severity, "evidence_hash": evidence.get("hash", ""),
                              "created_at": datetime.now(timezone.utc).isoformat()})
        return True

    def run(self, policy: EPLPolicy, ir_object: dict, dry_run=None) -> EnforcementResult:
        effective_dry_run = self._dry_run if dry_run is None else dry_run
        ir_id = ir_object.get("id", "unknown")
        violated = self._evaluate(policy, ir_object)
        if not violated:
            return EnforcementResult(policy_id=policy.policy_id, control_id=policy.control_id,
                                     ir_object_id=ir_id, state=RuntimeState.COMPLIANT,
                                     violation_detected=False,
                                     poam_action=self._update_poam(policy, ir_object, resolved=True))
        if not policy.auto_enforce or effective_dry_run:
            adapter_result = AdapterResult(adapter_id=policy.adapter_id, success=True,
                                           output={"skipped": True, "reason": "dry_run or auto_enforce=False"})
            state = RuntimeState.VIOLATED
        else:
            adapter_result = self._enforce(policy, ir_object, dry_run=effective_dry_run)
            state = RuntimeState.REMEDIATED if adapter_result.success else RuntimeState.FAILED
        if not adapter_result.success:
            return EnforcementResult(policy_id=policy.policy_id, control_id=policy.control_id,
                                     ir_object_id=ir_id, state=RuntimeState.FAILED,
                                     violation_detected=True, adapter_result=adapter_result,
                                     error=adapter_result.error)
        evidence = self._collect_evidence(policy, ir_object, adapter_result)
        resolved = (state == RuntimeState.REMEDIATED)
        poam_action = self._update_poam(policy, ir_object, resolved=resolved)
        sar_updated = self._update_sar(policy, ir_object, evidence)
        return EnforcementResult(policy_id=policy.policy_id, control_id=policy.control_id,
                                 ir_object_id=ir_id, state=state, violation_detected=True,
                                 adapter_result=adapter_result, evidence=evidence,
                                 poam_action=poam_action, sar_updated=sar_updated)

    def run_batch(self, policy: EPLPolicy, ir_objects: list, dry_run=None) -> list:
        return [self.run(policy, obj, dry_run=dry_run) for obj in ir_objects]
