"""Tests for UIAO_119 v2 migration sandbox (action 119.3 c)."""

from __future__ import annotations

from uiao.governance.feature_flags import FeatureFlag, FeatureFlagRegistry
from uiao.governance.migration_sandbox import (
    MigrationSandbox,
    SandboxDiff,
    SandboxRun,
)
from uiao.governance.tenancy import (
    Environment,
    Tenant,
    TenantClass,
    TenantContext,
)


# ---------------------------------------------------------------------------
# Core diff semantics
# ---------------------------------------------------------------------------


class TestMigrationSandboxBasic:
    def test_identical_runner_is_clean(self):
        sandbox = MigrationSandbox(runner=lambda ctx: [ctx.tenant_id])
        diff = sandbox.run(
            before=TenantContext(tenant_id="acme"),
            after=TenantContext(tenant_id="acme"),
        )
        assert diff.is_clean
        assert diff.added == ()
        assert diff.removed == ()
        assert diff.unchanged == ("'acme'",)

    def test_runner_branching_on_environment(self):
        # Runner produces "block" only in dev; in prod it skips.
        def runner(ctx: TenantContext) -> list[str]:
            if ctx.environment is Environment.DEV:
                return ["block:rogue-adapter"]
            return ["skip:rogue-adapter"]

        sandbox = MigrationSandbox(runner=runner)
        diff = sandbox.run(
            before=TenantContext(tenant_id="acme", environment=Environment.DEV),
            after=TenantContext(tenant_id="acme", environment=Environment.PROD),
        )
        assert not diff.is_clean
        assert diff.added == ("'skip:rogue-adapter'",)
        assert diff.removed == ("'block:rogue-adapter'",)
        assert diff.unchanged == ()

    def test_added_and_removed_sorted(self):
        # Verify deterministic order.
        def runner(ctx: TenantContext) -> list[str]:
            if ctx.tenant_id == "before":
                return ["zeta", "alpha", "gamma"]
            return ["beta", "alpha", "delta"]

        sandbox = MigrationSandbox(runner=runner)
        diff = sandbox.run(
            before=TenantContext(tenant_id="before"),
            after=TenantContext(tenant_id="after"),
        )
        # added = after \ before = {"beta", "delta"}
        assert diff.added == ("'beta'", "'delta'")
        # removed = before \ after = {"zeta", "gamma"}
        assert diff.removed == ("'gamma'", "'zeta'")
        # unchanged = both = {"alpha"}
        assert diff.unchanged == ("'alpha'",)

    def test_custom_serialize(self):
        # Default serialize is repr — quotes the string. A custom
        # serialize lets callers normalize structured output.
        def runner(ctx: TenantContext) -> list[dict]:
            return [{"target": ctx.tenant_id}]

        sandbox = MigrationSandbox(
            runner=runner,
            serialize=lambda o: f"target={o['target']}",
        )
        diff = sandbox.run(
            before=TenantContext(tenant_id="acme"),
            after=TenantContext(tenant_id="umbrella"),
        )
        assert diff.added == ("target=umbrella",)
        assert diff.removed == ("target=acme",)

    def test_explain_clean_returns_empty(self):
        sandbox = MigrationSandbox(runner=lambda ctx: [ctx.tenant_id])
        diff = sandbox.run(
            before=TenantContext(tenant_id="acme"),
            after=TenantContext(tenant_id="acme"),
        )
        assert sandbox.explain(diff) == ""

    def test_explain_with_changes(self):
        sandbox = MigrationSandbox(runner=lambda ctx: [ctx.environment.value])
        diff = sandbox.run(
            before=TenantContext(tenant_id="acme", environment=Environment.DEV),
            after=TenantContext(tenant_id="acme", environment=Environment.STAGE),
        )
        msg = sandbox.explain(diff)
        assert "before → after" in msg
        assert "+1 added" in msg
        assert "-1 removed" in msg

    def test_custom_labels(self):
        sandbox = MigrationSandbox(runner=lambda ctx: [ctx.environment.value])
        diff = sandbox.run(
            before=TenantContext(environment=Environment.DEV),
            after=TenantContext(environment=Environment.STAGE),
            before_label="dev-baseline",
            after_label="stage-canary",
        )
        assert diff.before.label == "dev-baseline"
        assert diff.after.label == "stage-canary"
        msg = sandbox.explain(diff)
        assert "dev-baseline → stage-canary" in msg


# ---------------------------------------------------------------------------
# SandboxRun + SandboxDiff data shapes
# ---------------------------------------------------------------------------


class TestSandboxDataShapes:
    def test_sandbox_run_as_dict(self):
        run = SandboxRun(
            label="dev",
            context=TenantContext(tenant_id="acme", actor="oid:42", environment=Environment.DEV),
            outputs=("a", "b"),
        )
        d = run.as_dict()
        assert d == {
            "label": "dev",
            "tenant_id": "acme",
            "actor": "oid:42",
            "environment": "dev",
            "outputs": ["a", "b"],
        }

    def test_sandbox_diff_as_dict_round_trips(self):
        before = SandboxRun(
            label="dev",
            context=TenantContext(environment=Environment.DEV),
            outputs=("x",),
        )
        after = SandboxRun(
            label="prod",
            context=TenantContext(environment=Environment.PROD),
            outputs=("y",),
        )
        diff = SandboxDiff(
            before=before,
            after=after,
            added=("y",),
            removed=("x",),
            unchanged=(),
        )
        d = diff.as_dict()
        assert d["added"] == ["y"]
        assert d["removed"] == ["x"]
        assert d["is_clean"] is False
        assert d["before"]["environment"] == "dev"
        assert d["after"]["environment"] == "prod"


# ---------------------------------------------------------------------------
# Integration: enforcement runtime feature-flag rollout preview
# ---------------------------------------------------------------------------


class TestEnforcementIntegration:
    def test_block_action_dev_vs_prod_diff(self):
        # Real use case: operator wants to know what changes about
        # block dispatch when promoting a tenant from dev → prod under
        # the existing canon flag (epl.action.block.enabled enabled
        # only in dev/stage internal/canary).
        from uiao.governance.enforcement import (
            BlockHandler,
            EnforcementJournal,
            EnforcementRuntime,
        )
        from uiao.governance.epl import (
            EPLAction,
            EPLContext,
            EPLEvaluator,
            EPLPolicy,
        )

        flags = FeatureFlagRegistry(
            flags={
                "epl.action.block.enabled": FeatureFlag(
                    name="epl.action.block.enabled",
                    enabled_environments=frozenset({Environment.DEV}),
                    enabled_tenant_classes=frozenset({TenantClass.INTERNAL, TenantClass.CANARY}),
                )
            }
        )
        tenant = Tenant(id="acme", tenant_class=TenantClass.CANARY)
        block_policy = EPLPolicy(
            id="epl:block-out-of-scope",
            action=EPLAction.BLOCK,
            actor="walker",
            sla_hours=0,
        )
        evaluator = EPLEvaluator(policies=[block_policy])

        def runner(ctx: TenantContext) -> list[str]:
            handler = BlockHandler(
                flags=flags,
                tenant_context=ctx,
                tenant=tenant,
            )
            runtime = EnforcementRuntime(
                evaluator=evaluator,
                handlers={EPLAction.BLOCK: handler},
                journal=EnforcementJournal(),
                tenant_context=ctx,
                tenant=tenant,
            )
            actions = runtime.dispatch_context(
                EPLContext(adapter_id="rogue-adapter"),
                target="rogue-adapter",
            )
            return [f"{a.policy_id}:{a.status}" for a in actions]

        sandbox = MigrationSandbox(runner=runner)
        diff = sandbox.run(
            before=TenantContext(tenant_id="acme", environment=Environment.DEV),
            after=TenantContext(tenant_id="acme", environment=Environment.PROD),
        )
        # In DEV the block dispatches; in PROD the flag is disabled
        # for prod, so the action is "skipped".
        assert "'epl:block-out-of-scope:dispatched'" in diff.removed
        assert "'epl:block-out-of-scope:skipped'" in diff.added
        assert not diff.is_clean
