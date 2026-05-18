"""uiao.cli.enforcement — Typer sub-app for the `uiao enforcement` command group.

Exposes the UIAO Enforcement Runtime (UIAO_111) at the CLI so operators
can dry-run policy evaluations against IR object lists without writing
Python.

Per ADR-046 every command lives under a sub-app; this sub-app closes
the M5 audit's F1 gap (Enforcement Runtime was import-only on v0.4.x).

Mount point
-----------
    # in src/uiao/cli/app.py
    from uiao.cli.enforcement import enforcement_app
    app.add_typer(enforcement_app, name="enforcement")

Built-in demo policies
----------------------
The CLI ships demo policies for sandbox use. Production policies are
registered via Python (the runtime accepts arbitrary callables for
`EPLPolicy.condition`, which YAML cannot serialize) — see
`tests/test_enforcement_runtime.py` for the integration shape.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from uiao.enforcement import EnforcementRuntime, EPLPolicy, RuntimeState

enforcement_app = typer.Typer(
    name="enforcement",
    help="UIAO Enforcement Runtime (UIAO_111) — dry-run policy evaluations against IR objects.",
    add_completion=False,
)

_console = Console()


# Built-in demo policies. Keyed by `--policy` argument value.
# Each value is a function that returns an EPLPolicy so the lambda
# closures stay private and the dict is safe to expose.
def _mfa_demo_policy() -> EPLPolicy:
    return EPLPolicy(
        policy_id="POL-MFA-DEMO",
        control_id="IA-2",
        description="Demo: MFA must be enabled (IR object's mfa_enabled key)",
        adapter_id="noop",
        condition=lambda ir: not ir.get("mfa_enabled", True),
        severity="High",
        auto_enforce=False,
    )


def _violation_demo_policy() -> EPLPolicy:
    return EPLPolicy(
        policy_id="POL-STATUS-DEMO",
        control_id="AC-2",
        description="Demo: IR object must not be in 'VIOLATED' status",
        adapter_id="noop",
        condition=lambda ir: ir.get("status") == "VIOLATED",
        severity="Medium",
        auto_enforce=False,
    )


_DEMO_POLICIES = {
    "mfa-demo": _mfa_demo_policy,
    "violation-demo": _violation_demo_policy,
}


@enforcement_app.command("list-policies")
def list_policies() -> None:
    """List built-in demo policies the CLI can run.

    Production policies use callable conditions and are wired in Python;
    this command surfaces only the demo set safe to invoke from the CLI.

    Example::

        uiao enforcement list-policies
    """
    _console.print("[bold]Built-in demo policies:[/bold]")
    for name, factory in _DEMO_POLICIES.items():
        policy = factory()
        _console.print(
            f"  [cyan]{name}[/cyan]  [{policy.severity}]  [dim]{policy.control_id}[/dim]  {policy.description}"
        )


@enforcement_app.command("run")
def run(
    ir_objects_path: Path = typer.Argument(
        ...,
        help="Path to a JSON file containing a list of IR objects. Each object is a dict.",
    ),
    policy: str = typer.Option(
        "mfa-demo",
        "--policy",
        "-p",
        help="Demo policy id. Run `uiao enforcement list-policies` for choices.",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="Skip adapter enforcement (default: dry-run). Live runs require auto_enforce=True on the policy.",
    ),
    out: str = typer.Option(
        "",
        "--out",
        "-o",
        help="Optional path to write the EnforcementResult JSON list.",
    ),
) -> None:
    """Run an enforcement policy against a list of IR objects.

    Loads IR_OBJECTS_PATH (JSON list of dicts), evaluates the named
    --policy against each object, and prints a summary with per-state
    counts (COMPLIANT / VIOLATED / REMEDIATED / FAILED). Use --out to
    write the full per-object result list to disk for downstream
    pipeline integration.

    The shipped policies are demos — production deployments register
    their own policies via Python. This command exists to verify the
    runtime is wired and reachable, and to give operators a sandbox.

    Example::

        uiao enforcement run examples/quickstart/scuba-normalized.json --policy mfa-demo
    """
    if policy not in _DEMO_POLICIES:
        _console.print(f"[red]Unknown policy: {policy}[/red]")
        _console.print("[dim]Run `uiao enforcement list-policies` for choices.[/dim]")
        raise typer.Exit(code=1)

    if not ir_objects_path.exists():
        _console.print(f"[red]IR objects file not found: {ir_objects_path}[/red]")
        raise typer.Exit(code=1)

    payload = json.loads(ir_objects_path.read_text(encoding="utf-8"))
    # Accept either a top-level list or a dict containing a known list
    # field ('ksi_results' for the quickstart fixture, 'ir_objects' for
    # custom inputs).
    ir_objects: list[dict] = []
    if isinstance(payload, list):
        ir_objects = payload
    elif isinstance(payload, dict):
        for key in ("ksi_results", "ir_objects", "objects"):
            if key in payload and isinstance(payload[key], list):
                ir_objects = payload[key]
                break
    if not ir_objects:
        _console.print(f"[red]No IR object list found in {ir_objects_path}[/red]")
        _console.print(
            "[dim]Expected a top-level list, or a dict containing 'ksi_results' / 'ir_objects' / 'objects'.[/dim]"
        )
        raise typer.Exit(code=1)

    runtime = EnforcementRuntime(dry_run=dry_run)
    epl = _DEMO_POLICIES[policy]()
    results = runtime.run_batch(epl, ir_objects)

    counts: dict[str, int] = {}
    for r in results:
        counts[r.state] = counts.get(r.state, 0) + 1

    _console.print(f"[bold]Enforcement run: policy={policy}, dry_run={dry_run}[/bold]")
    _console.print(f"  IR objects evaluated : {len(results)}")
    for state in (
        RuntimeState.COMPLIANT,
        RuntimeState.VIOLATED,
        RuntimeState.REMEDIATED,
        RuntimeState.FAILED,
    ):
        count = counts.get(state, 0)
        if count:
            color = {"COMPLIANT": "green", "VIOLATED": "yellow", "REMEDIATED": "cyan", "FAILED": "red"}[state]
            _console.print(f"  {state:<11} : [{color}]{count}[/{color}]")

    if out:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _console.print(f"[green]Results written to {out}[/green]")
