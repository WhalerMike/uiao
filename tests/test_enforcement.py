"""Tests for UIAO_111 / §3.3 Enforcement Runtime."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from uiao.governance.enforcement import (
    AlertHandler,
    BlockHandler,
    EnforcementAction,
    EnforcementJournal,
    EnforcementRuntime,
    EscalateHandler,
    LoggingHandler,
    RemediateHandler,
)
from uiao.governance.epl import (
    EPLAction,
    EPLContext,
    EPLEvaluator,
    EPLMatch,
    EPLPolicy,
    EPLTrigger,
    load_canonical_policies,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _match(policy: EPLPolicy, ctx: EPLContext | None = None) -> EPLMatch:
    return EPLMatch(policy=policy, context=ctx or EPLContext())


def _alert_policy(pid: str = "epl:t-alert") -> EPLPolicy:
    return EPLPolicy(
        id=pid,
        action=EPLAction.ALERT,
        actor="soc",
        sla_hours=4,
    )


def _now_fixed() -> datetime:
    return datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


class TestLoggingHandler:
    def test_dispatch_returns_dispatched_action(self):
        handler = LoggingHandler()
        match = _match(EPLPolicy(id="epl:t", action=EPLAction.LOG))
        action = handler.dispatch(match, target="entra-id", now=_now_fixed())
        assert action.status == "dispatched"
        assert action.action == EPLAction.LOG
        assert action.target == "entra-id"
        assert action.dispatched_at.startswith("2026-04-26")


class TestAlertHandler:
    def test_dispatch_records_alert_intent(self):
        handler = AlertHandler()
        action = handler.dispatch(_match(_alert_policy()), target="AC-2")
        assert action.status == "dispatched"
        assert action.action == EPLAction.ALERT
        assert "alert fired" in action.details


class TestEscalateHandler:
    def test_dispatch_tags_priority_high(self):
        handler = EscalateHandler()
        policy = EPLPolicy(id="epl:e", action=EPLAction.ESCALATE, actor="soc", sla_hours=1)
        action = handler.dispatch(_match(policy), target="r1")
        assert action.extra.get("priority") == "high"


class TestBlockHandler:
    def test_dispatch_appends_to_block_list(self):
        handler = BlockHandler()
        policy = EPLPolicy(id="epl:b", action=EPLAction.BLOCK, actor="walker", sla_hours=0)
        handler.dispatch(_match(policy), target="entra-id")
        handler.dispatch(_match(policy), target="m365")
        assert handler.blocked == {"entra-id", "m365"}

    def test_dispatch_dedupes(self):
        handler = BlockHandler()
        policy = EPLPolicy(id="epl:b", action=EPLAction.BLOCK, actor="walker", sla_hours=0)
        handler.dispatch(_match(policy), target="entra-id")
        handler.dispatch(_match(policy), target="entra-id")
        assert handler.blocked == {"entra-id"}

    def test_disabled_flag_skips_block(self):
        from uiao.governance.feature_flags import FeatureFlag, FeatureFlagRegistry
        from uiao.governance.tenancy import Environment, TenantContext

        ctx = TenantContext(tenant_id="acme", environment=Environment.PROD)
        flags = FeatureFlagRegistry(
            flags={
                "epl.action.block.enabled": FeatureFlag(
                    name="epl.action.block.enabled",
                    enabled_environments=frozenset({Environment.DEV}),
                )
            }
        )
        handler = BlockHandler(flags=flags, tenant_context=ctx)
        policy = EPLPolicy(id="epl:b", action=EPLAction.BLOCK, actor="walker", sla_hours=0)
        action = handler.dispatch(_match(policy), target="entra-id")
        assert action.status == "skipped"
        assert "epl.action.block.enabled" in action.details
        assert handler.blocked == set()

    def test_enabled_flag_dispatches_block(self):
        from uiao.governance.feature_flags import FeatureFlag, FeatureFlagRegistry
        from uiao.governance.tenancy import Environment, TenantContext

        ctx = TenantContext(tenant_id="acme", environment=Environment.DEV)
        flags = FeatureFlagRegistry(
            flags={
                "epl.action.block.enabled": FeatureFlag(
                    name="epl.action.block.enabled",
                    enabled_environments=frozenset({Environment.DEV}),
                )
            }
        )
        handler = BlockHandler(flags=flags, tenant_context=ctx)
        policy = EPLPolicy(id="epl:b", action=EPLAction.BLOCK, actor="walker", sla_hours=0)
        action = handler.dispatch(_match(policy), target="entra-id")
        assert action.status == "dispatched"
        assert handler.blocked == {"entra-id"}

    def test_no_context_dispatches_unconditionally(self):
        # Back-compat: handler without flags+context still dispatches.
        from uiao.governance.feature_flags import FeatureFlag, FeatureFlagRegistry

        flags = FeatureFlagRegistry(
            flags={
                "epl.action.block.enabled": FeatureFlag(
                    name="epl.action.block.enabled",
                    enabled_environments=frozenset(),  # deny all
                )
            }
        )
        # flags supplied but no tenant_context → gate not consulted
        handler = BlockHandler(flags=flags)
        policy = EPLPolicy(id="epl:b", action=EPLAction.BLOCK, actor="walker", sla_hours=0)
        action = handler.dispatch(_match(policy), target="entra-id")
        assert action.status == "dispatched"


class TestRemediateHandler:
    def test_no_wired_remediation_skips(self):
        handler = RemediateHandler(adapter_remediations={})
        ctx = EPLContext(adapter_id="phantom", drift_class="DRIFT-AUTHZ")
        match = EPLMatch(
            policy=EPLPolicy(id="epl:r", action=EPLAction.REMEDIATE, actor="orch", sla_hours=8),
            context=ctx,
        )
        action = handler.dispatch(match, target="phantom")
        assert action.status == "skipped"
        assert "no remediation wired" in action.details

    def test_wired_remediation_dispatched(self):
        calls: list[tuple[str, str]] = []

        def fake(match: EPLMatch, target: str) -> tuple[bool, str]:
            calls.append((match.policy.id, target))
            return True, "rotated MFA secret"

        handler = RemediateHandler(adapter_remediations={"entra-id": fake})
        ctx = EPLContext(adapter_id="entra-id", drift_class="DRIFT-SEMANTIC")
        match = EPLMatch(
            policy=EPLPolicy(id="epl:r", action=EPLAction.REMEDIATE, actor="orch", sla_hours=8),
            context=ctx,
        )
        action = handler.dispatch(match, target="entra-id")
        assert action.status == "dispatched"
        assert calls == [("epl:r", "entra-id")]
        assert "rotated MFA secret" in action.details

    def test_wired_remediation_failure_recorded(self):
        def fake(match, target):
            return False, "vault unreachable"

        handler = RemediateHandler(adapter_remediations={"entra-id": fake})
        ctx = EPLContext(adapter_id="entra-id")
        match = EPLMatch(
            policy=EPLPolicy(id="epl:r", action=EPLAction.REMEDIATE, actor="orch", sla_hours=8),
            context=ctx,
        )
        action = handler.dispatch(match, target="entra-id")
        assert action.status == "failed"

    def test_wired_remediation_exception_recorded(self):
        def fake(match, target):
            raise RuntimeError("kaboom")

        handler = RemediateHandler(adapter_remediations={"entra-id": fake})
        ctx = EPLContext(adapter_id="entra-id")
        match = EPLMatch(
            policy=EPLPolicy(id="epl:r", action=EPLAction.REMEDIATE, actor="orch", sla_hours=8),
            context=ctx,
        )
        action = handler.dispatch(match, target="entra-id")
        assert action.status == "failed"
        assert "kaboom" in action.details


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------


class TestEnforcementJournal:
    def test_in_memory_record(self):
        journal = EnforcementJournal()
        action = EnforcementAction(
            policy_id="epl:a",
            action=EPLAction.LOG,
            actor="x",
            sla_hours=0,
            target="t",
            dispatched_at="2026-04-26T00:00:00+00:00",
            status="dispatched",
        )
        journal.record(action)
        assert journal.read_all() == [action]

    def test_disk_persistence(self, tmp_path):
        path = tmp_path / "journal.jsonl"
        journal = EnforcementJournal(path=path)
        for i in range(3):
            journal.record(
                EnforcementAction(
                    policy_id=f"epl:a{i}",
                    action=EPLAction.LOG,
                    actor="x",
                    sla_hours=0,
                    target=f"t{i}",
                    dispatched_at="2026-04-26T00:00:00+00:00",
                    status="dispatched",
                )
            )
        # File contents = three JSON lines.
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        for line in lines:
            json.loads(line)  # parses

    def test_disk_read_round_trip(self, tmp_path):
        path = tmp_path / "j.jsonl"
        journal = EnforcementJournal(path=path)
        action = EnforcementAction(
            policy_id="epl:a",
            action=EPLAction.ALERT,
            actor="soc",
            sla_hours=4,
            target="AC-2",
            dispatched_at="2026-04-26T00:00:00+00:00",
            status="dispatched",
            details="hello",
        )
        journal.record(action)
        # Fresh journal pointing at same path reads back the record.
        fresh = EnforcementJournal(path=path)
        records = fresh.read_all()
        assert len(records) == 1
        assert records[0].policy_id == "epl:a"
        assert records[0].details == "hello"

    def test_corrupt_line_skipped(self, tmp_path):
        path = tmp_path / "j.jsonl"
        path.write_text("not-json\n", encoding="utf-8")
        journal = EnforcementJournal(path=path)
        assert journal.read_all() == []


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------


class TestEnforcementRuntime:
    def test_dispatch_context_with_match(self):
        evaluator = EPLEvaluator(
            policies=[
                EPLPolicy(
                    id="epl:t-authz",
                    action=EPLAction.BLOCK,
                    actor="walker",
                    sla_hours=0,
                    when=EPLTrigger(drift_class=frozenset({"DRIFT-AUTHZ"})),
                )
            ]
        )
        runtime = EnforcementRuntime(evaluator=evaluator)
        actions = runtime.dispatch_context(EPLContext(drift_class="DRIFT-AUTHZ", adapter_id="entra-id"))
        assert len(actions) == 1
        assert actions[0].policy_id == "epl:t-authz"
        assert actions[0].action == EPLAction.BLOCK
        assert actions[0].target == "entra-id"

    def test_dispatch_context_no_match_returns_empty(self):
        runtime = EnforcementRuntime(evaluator=EPLEvaluator(policies=[]))
        assert runtime.dispatch_context(EPLContext(drift_class="DRIFT-AUTHZ")) == []

    def test_dispatch_context_target_falls_back_to_control(self):
        evaluator = EPLEvaluator(
            policies=[
                EPLPolicy(
                    id="epl:t",
                    action=EPLAction.LOG,
                    actor="x",
                    sla_hours=0,
                )
            ]
        )
        runtime = EnforcementRuntime(evaluator=evaluator)
        ctx = EPLContext(controls=frozenset({"AC-2"}))
        actions = runtime.dispatch_context(ctx)
        assert actions[0].target == "AC-2"

    def test_dispatch_context_target_unknown_fallback(self):
        evaluator = EPLEvaluator(policies=[EPLPolicy(id="epl:t", action=EPLAction.LOG)])
        runtime = EnforcementRuntime(evaluator=evaluator)
        # Empty context — no adapter_id, no controls.
        actions = runtime.dispatch_context(EPLContext(drift_class="DRIFT-AUTHZ"))
        assert actions[0].target == "unknown"

    def test_dispatch_finding_round_trip(self):
        class F:
            drift_class = "DRIFT-IDENTITY"
            control_id = "IA-2"
            severity = "High"
            extra = {"adapter_id": "entra-id"}

        evaluator = EPLEvaluator(
            policies=[
                EPLPolicy(
                    id="epl:t-id",
                    action=EPLAction.ESCALATE,
                    actor="soc",
                    sla_hours=4,
                    when=EPLTrigger(drift_class=frozenset({"DRIFT-IDENTITY"})),
                )
            ]
        )
        runtime = EnforcementRuntime(evaluator=evaluator)
        actions = runtime.dispatch_finding(F())
        assert len(actions) == 1
        assert actions[0].action == EPLAction.ESCALATE
        # Adapter id from finding.extra became target.
        assert actions[0].target == "entra-id"

    def test_dispatch_drift_state_round_trip(self):
        class DS:
            drift_class = "DRIFT-AUTHZ"
            policy_ref = "AC-2"
            classification = "unauthorized"

        evaluator = EPLEvaluator(
            policies=[
                EPLPolicy(
                    id="epl:t-authz",
                    action=EPLAction.BLOCK,
                    actor="walker",
                    sla_hours=0,
                    when=EPLTrigger(drift_class=frozenset({"DRIFT-AUTHZ"})),
                )
            ]
        )
        runtime = EnforcementRuntime(evaluator=evaluator)
        actions = runtime.dispatch_drift_state(DS())
        assert len(actions) == 1
        assert actions[0].action == EPLAction.BLOCK

    def test_dispatch_records_to_journal(self):
        journal = EnforcementJournal()
        evaluator = EPLEvaluator(policies=[EPLPolicy(id="epl:t", action=EPLAction.LOG)])
        runtime = EnforcementRuntime(evaluator=evaluator, journal=journal)
        runtime.dispatch_context(EPLContext(drift_class="DRIFT-SEMANTIC"))
        assert len(journal.records) == 1

    def test_unknown_action_handler_skips(self):
        evaluator = EPLEvaluator(policies=[EPLPolicy(id="epl:t", action=EPLAction.LOG)])
        runtime = EnforcementRuntime(evaluator=evaluator, handlers={})
        actions = runtime.dispatch_context(EPLContext(drift_class="DRIFT-SEMANTIC"))
        assert actions[0].status == "skipped"
        assert "no handler registered" in actions[0].details

    def test_remediate_through_runtime_with_handler(self):
        calls: list[str] = []

        def fake(match, target):
            calls.append(target)
            return True, "ok"

        evaluator = EPLEvaluator(
            policies=[
                EPLPolicy(
                    id="epl:r",
                    action=EPLAction.REMEDIATE,
                    actor="orch",
                    sla_hours=8,
                    when=EPLTrigger(drift_class=frozenset({"DRIFT-SEMANTIC"})),
                )
            ]
        )
        runtime = EnforcementRuntime(
            evaluator=evaluator,
            handlers={
                EPLAction.REMEDIATE: RemediateHandler(adapter_remediations={"entra-id": fake}),
            },
        )
        actions = runtime.dispatch_context(EPLContext(drift_class="DRIFT-SEMANTIC", adapter_id="entra-id"))
        assert actions[0].status == "dispatched"
        assert calls == ["entra-id"]


# ---------------------------------------------------------------------------
# Integration: canonical policies + runtime + journal on disk
# ---------------------------------------------------------------------------


class TestRuntimeWithCanonicalPolicies:
    def test_drift_authz_finding_dispatches_block(self, tmp_path):
        journal = EnforcementJournal(path=tmp_path / "j.jsonl")
        evaluator = EPLEvaluator(policies=load_canonical_policies())
        runtime = EnforcementRuntime(evaluator=evaluator, journal=journal)

        class F:
            drift_class = "DRIFT-AUTHZ"
            control_id = "AC-2"
            severity = "High"
            extra = {"adapter_id": "rogue-adapter"}

        actions = runtime.dispatch_finding(F())
        ids = {a.policy_id for a in actions}
        assert "epl:block-out-of-scope" in ids
        # And the block landed in the journal on disk.
        fresh = EnforcementJournal(path=tmp_path / "j.jsonl")
        assert any(r.policy_id == "epl:block-out-of-scope" for r in fresh.read_all())

    def test_drift_semantic_high_severity_alerts_and_escalates(self, tmp_path):
        journal = EnforcementJournal(path=tmp_path / "j.jsonl")
        evaluator = EPLEvaluator(policies=load_canonical_policies())
        runtime = EnforcementRuntime(evaluator=evaluator, journal=journal)

        class F:
            drift_class = "DRIFT-SEMANTIC"
            control_id = "IA-2"
            severity = "High"
            extra = {"adapter_id": "entra-id"}

        actions = runtime.dispatch_finding(F())
        ids = {a.policy_id for a in actions}
        # Both the MFA-enforce remediation and stale-evidence escalation
        # match an IA-2 / High DRIFT-SEMANTIC finding.
        assert "epl:enforce-mfa" in ids
        assert "epl:escalate-stale-evidence" in ids

    def test_journal_persists_across_runtime_recreation(self, tmp_path):
        path = tmp_path / "j.jsonl"
        evaluator = EPLEvaluator(policies=load_canonical_policies())

        # First runtime instance: dispatches a finding.
        class F:
            drift_class = "DRIFT-AUTHZ"
            control_id = "AC-2"
            severity = "High"
            extra = {"adapter_id": "rogue"}

        runtime1 = EnforcementRuntime(evaluator=evaluator, journal=EnforcementJournal(path=path))
        runtime1.dispatch_finding(F())

        # Second runtime instance reads the same on-disk journal.
        runtime2 = EnforcementRuntime(evaluator=evaluator, journal=EnforcementJournal(path=path))
        records = runtime2.journal.read_all()
        assert len(records) >= 1


# ---------------------------------------------------------------------------
# UIAO_119 v2 — tenant tagging on journal records
# ---------------------------------------------------------------------------


class TestRuntimeTenantTagging:
    def _setup_runtime(self, journal_path, *, tenant_context=None, tenant=None, flags=None):
        from uiao.governance.feature_flags import FeatureFlag, FeatureFlagRegistry

        # Local imports to keep the rest of the module import-light.
        del FeatureFlag, FeatureFlagRegistry  # noqa: F401 (re-imported below)
        evaluator = EPLEvaluator(policies=[_alert_policy()])
        return EnforcementRuntime(
            evaluator=evaluator,
            journal=EnforcementJournal(path=journal_path),
            tenant_context=tenant_context,
            tenant=tenant,
            flags=flags,
        )

    def test_no_tenant_context_no_tags(self, tmp_path):
        runtime = self._setup_runtime(tmp_path / "j.jsonl")
        actions = runtime.dispatch_matches([_match(_alert_policy())], target="x")
        assert all("tenant_id" not in a.extra for a in actions)

    def test_tenant_context_unconditional_tags(self, tmp_path):
        from uiao.governance.tenancy import Environment, TenantContext

        ctx = TenantContext(tenant_id="acme", actor="oid:42", environment=Environment.STAGE)
        runtime = self._setup_runtime(tmp_path / "j.jsonl", tenant_context=ctx)
        actions = runtime.dispatch_matches([_match(_alert_policy())], target="x")
        assert len(actions) == 1
        assert actions[0].extra["tenant_id"] == "acme"
        assert actions[0].extra["actor"] == "oid:42"
        assert actions[0].extra["environment"] == "stage"

    def test_tenant_context_with_tenant_carries_class(self, tmp_path):
        from uiao.governance.tenancy import (
            Environment,
            Tenant,
            TenantClass,
            TenantContext,
        )

        ctx = TenantContext(tenant_id="acme", actor="oid:42", environment=Environment.PROD)
        tenant = Tenant(id="acme", tenant_class=TenantClass.REGULATED)
        runtime = self._setup_runtime(tmp_path / "j.jsonl", tenant_context=ctx, tenant=tenant)
        actions = runtime.dispatch_matches([_match(_alert_policy())], target="x")
        assert actions[0].extra["tenant_class"] == "regulated"

    def test_disabled_flag_skips_tagging(self, tmp_path):
        from uiao.governance.feature_flags import FeatureFlag, FeatureFlagRegistry
        from uiao.governance.tenancy import Environment, TenantContext

        ctx = TenantContext(tenant_id="acme", environment=Environment.DEV)
        flags = FeatureFlagRegistry(
            flags={
                "enforcement.journal.tenant-tagging": FeatureFlag(
                    name="enforcement.journal.tenant-tagging",
                    enabled_environments=frozenset(),  # deny all
                )
            }
        )
        runtime = self._setup_runtime(tmp_path / "j.jsonl", tenant_context=ctx, flags=flags)
        actions = runtime.dispatch_matches([_match(_alert_policy())], target="x")
        assert "tenant_id" not in actions[0].extra

    def test_enabled_flag_applies_tagging(self, tmp_path):
        from uiao.governance.feature_flags import FeatureFlag, FeatureFlagRegistry
        from uiao.governance.tenancy import Environment, TenantContext

        ctx = TenantContext(tenant_id="acme", environment=Environment.DEV)
        flags = FeatureFlagRegistry(
            flags={
                "enforcement.journal.tenant-tagging": FeatureFlag(
                    name="enforcement.journal.tenant-tagging",
                    enabled_environments=frozenset({Environment.DEV}),
                )
            }
        )
        runtime = self._setup_runtime(tmp_path / "j.jsonl", tenant_context=ctx, flags=flags)
        actions = runtime.dispatch_matches([_match(_alert_policy())], target="x")
        assert actions[0].extra["tenant_id"] == "acme"

    def test_tags_round_trip_through_disk(self, tmp_path):
        from uiao.governance.tenancy import Environment, TenantContext

        ctx = TenantContext(tenant_id="acme", environment=Environment.STAGE)
        path = tmp_path / "j.jsonl"
        runtime = self._setup_runtime(path, tenant_context=ctx)
        runtime.dispatch_matches([_match(_alert_policy())], target="x")

        fresh = EnforcementJournal(path=path)
        records = fresh.read_all()
        assert len(records) == 1
        assert records[0].extra["tenant_id"] == "acme"
        assert records[0].extra["environment"] == "stage"
