"""uiao.cli.tenant — Typer sub-app for tenant lifecycle commands (UIAO_119).

Currently exposes a single subcommand:

    uiao tenant promote-preview --tenant-id <id> --from <env> --to <env>

which previews what changes about a tenant's substrate behavior when its
``TenantContext.environment`` is promoted (typically dev → stage, stage →
prod, or prod canary → prod standard for a tenant_class change).

The preview uses :class:`uiao.governance.migration_sandbox.MigrationSandbox`
to diff the set of feature flags that evaluate to ``True`` for the
"before" and "after" :class:`TenantContext` instances. Operators read the
diff before flipping canon — see the
[`UIAO_119 canary rollout runbook`](docs/programs/ops-runbook/2026-04-26-uiao_119-canary-rollout.qmd)
for the procedure shape.

Permission gate
---------------
The subcommand calls
:func:`uiao.governance.feature_flags.FeatureFlagRegistry.is_enabled` against
the ``tenancy.environment.prod-promote`` flag with the calling actor's
context. The default canon enables the flag for ``internal`` tenants in
``dev`` / ``stage``; agency operators see a denial unless their canon
overlay enables them explicitly. Denials exit non-zero so a CI gate can
fail-closed on unauthorized promotions.
"""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer
from rich.console import Console

from uiao.governance.feature_flags import (
    FeatureFlagRegistry,
    load_canonical_flags,
)
from uiao.governance.migration_sandbox import MigrationSandbox
from uiao.governance.tenancy import (
    Environment,
    Tenant,
    TenantClass,
    TenantContext,
)

PROD_PROMOTE_FLAG = "tenancy.environment.prod-promote"

tenant_app = typer.Typer(
    name="tenant",
    help="UIAO_119 tenant lifecycle — promote-preview, etc.",
    add_completion=False,
)

_console = Console()


def _list_enabled_flags(
    registry: FeatureFlagRegistry,
    ctx: TenantContext,
    tenant: Optional[Tenant],
) -> list[str]:
    """Return the names of every flag that evaluates to True for ctx.

    Used as the runner for the migration sandbox: the diff between
    "before" and "after" enabled-flag sets is exactly the operator-
    visible behavior change.
    """
    return sorted(name for name, flag in registry.flags.items() if flag.is_enabled(ctx, tenant))


@tenant_app.command("promote-preview")
def promote_preview(
    tenant_id: str = typer.Option(..., "--tenant-id", help="Tenant id (matches src/uiao/canon/tenants.yaml)."),
    from_env: str = typer.Option(..., "--from", help="Current environment: dev / stage / prod."),
    to_env: str = typer.Option(..., "--to", help="Target environment: dev / stage / prod."),
    tenant_class: str = typer.Option(
        "standard",
        "--tenant-class",
        help="Tenant class for the gate evaluation: internal / canary / standard / regulated.",
    ),
    actor: str = typer.Option(
        "cli",
        "--actor",
        help="Actor identifier for the permission gate. Default 'cli'.",
    ),
    output: str = typer.Option(
        "human",
        "--output",
        help="Output format: human (rich) or json.",
    ),
    allow_no_change: bool = typer.Option(
        False,
        "--allow-no-change",
        help=(
            "When the diff is empty, exit 0 anyway. Default behavior is "
            "exit 1 to flag operator typos like --from prod --to prod."
        ),
    ),
) -> None:
    """Preview the substrate-behavior diff for promoting a tenant
    between environments. Gated on the ``tenancy.environment.prod-promote``
    feature flag.
    """
    flags = load_canonical_flags()

    # Permission gate — uses the calling actor's context, not the
    # tenant being previewed. Operators in dev/stage with the
    # `tenancy.environment.prod-promote` flag enabled may run the
    # subcommand; agency operators (standard / regulated tenants)
    # can't preview a promotion they aren't authorized to schedule.
    operator_ctx = TenantContext(
        tenant_id=tenant_id,
        actor=actor,
        environment=Environment.parse(from_env),
    )
    if not flags.is_enabled(PROD_PROMOTE_FLAG, operator_ctx):
        _console.print(
            f"[red]Permission denied:[/red] flag {PROD_PROMOTE_FLAG!r} "
            f"is disabled for environment={operator_ctx.environment.value} "
            f"actor={actor!r}. Enable in src/uiao/canon/feature-flags.yaml "
            f"or run from a permitted env (dev / stage by default)."
        )
        raise typer.Exit(code=2)

    tenant_class_parsed = TenantClass.parse(tenant_class)
    tenant_obj = Tenant(id=tenant_id, tenant_class=tenant_class_parsed)

    before = TenantContext(
        tenant_id=tenant_id,
        actor=actor,
        environment=Environment.parse(from_env),
    )
    after = TenantContext(
        tenant_id=tenant_id,
        actor=actor,
        environment=Environment.parse(to_env),
    )

    def runner(ctx: TenantContext) -> list[str]:
        return _list_enabled_flags(flags, ctx, tenant_obj)

    sandbox = MigrationSandbox(runner=runner, serialize=str)
    diff = sandbox.run(
        before=before,
        after=after,
        before_label=f"{tenant_id}@{from_env}",
        after_label=f"{tenant_id}@{to_env}",
    )

    if output == "json":
        sys.stdout.write(json.dumps(diff.as_dict(), indent=2, sort_keys=True) + "\n")
    else:
        _console.print(f"[bold]promote-preview[/bold] {tenant_id}: {from_env} → {to_env}")
        _console.print(f"  tenant_class: {tenant_class_parsed.value}")
        _console.print(f"  actor:        {actor}")
        if diff.is_clean:
            _console.print("[yellow]No flag-evaluation changes.[/yellow]")
        else:
            if diff.added:
                _console.print(f"[green]+{len(diff.added)} flags newly enabled[/green]")
                for flag_name in diff.added:
                    _console.print(f"  + {flag_name}")
            if diff.removed:
                _console.print(f"[red]-{len(diff.removed)} flags newly disabled[/red]")
                for flag_name in diff.removed:
                    _console.print(f"  - {flag_name}")

    if diff.is_clean and not allow_no_change:
        # No-op promotion is usually a typo (--from prod --to prod) —
        # exit 1 unless the caller explicitly opts in.
        raise typer.Exit(code=1)


__all__ = [
    "PROD_PROMOTE_FLAG",
    "promote_preview",
    "tenant_app",
]
