"""OrgTree CLI: ``uiao orgtree ...`` subcommands.

Thin verbs over the loader/validator classes in
:mod:`uiao.modernization.orgtree`.

Per ADR-078, the OrgTree corpus was reset to Model C (15-facet multi-
attribute). Commands:

- ``validate codebook`` — validate the UIAO_151 OrgPath codebook (Model C)
- ``govern`` — run one OrgPath governance pass over a tenant snapshot
  (the operator-reachable surface of the OrgPath Governance Runtime;
  see :mod:`uiao.governance.orgpath_runtime`, UIAO_163 / UIAO_174)

Per-facet show/list/export commands and the broader corpus validators
will land alongside the rebuilt consumer modules in a follow-up
Phase 5 PR.

Canon: UIAO_151, UIAO_163, UIAO_174.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from uiao.governance.orgpath_runtime import (
    OrgPathGovernanceRuntime,
    SnapshotError,
    snapshot_from_dict,
)
from uiao.modernization.orgtree.codebook import (
    Codebook,
    CodebookValidationError,
    load_codebook,
)

orgtree_app = typer.Typer(
    name="orgtree",
    help=("OrgTree corpus operations (validate codebook, govern). Canon: UIAO_151. Model C per ADR-078."),
    no_args_is_help=True,
)

validate_app = typer.Typer(
    name="validate",
    help="Validate an OrgTree corpus file against its schema and integrity rules.",
    no_args_is_help=True,
)
orgtree_app.add_typer(validate_app, name="validate")

console = Console()


_DATA_OPT = typer.Option(
    None,
    "--data",
    "-d",
    help=("Path to an alternate YAML file. Defaults to the canonical artifact under uiao.canon.data.orgpath."),
)


def _summarize_codebook(c: Codebook) -> str:
    named = sum(1 for f in c.facets.values() if f.kind != "reserved")
    reserved = sum(1 for f in c.facets.values() if f.kind == "reserved")
    enum_values = sum(len(f.enumeration) for f in c.facets.values() if f.kind == "enumerated")
    return (
        f"{named} named facets + {reserved} reserved slots; "
        f"{enum_values} enumerated values; model={c.model}; "
        f"adoption_tier_min={c.adoption_tier_min}"
    )


@validate_app.command("codebook")
def validate_codebook(data: Path | None = _DATA_OPT) -> None:
    """Validate the OrgPath codebook (UIAO_151, Model C per ADR-078)."""
    try:
        artifact = load_codebook(path=data) if data is not None else load_codebook()
    except CodebookValidationError as exc:
        console.print(f"[red]FAIL[/red] codebook (UIAO_151): {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]PASS[/green] codebook (UIAO_151) — {_summarize_codebook(artifact)}")


@orgtree_app.command("govern")
def govern(
    snapshot_path: Path = typer.Argument(
        ...,
        help="Path to a JSON tenant snapshot (keys: principals, groups, admin_units, policy_targets).",
    ),
    detection_only: bool = typer.Option(
        False,
        "--detection-only",
        help="Skip the canonical Phase 5 adapters — classify drift + emit telemetry without planning writes.",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="Suppress all writes (default). --no-dry-run still honours halt-on-critical and governance-review ops.",
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        "-o",
        help="Optional path to write the full GovernanceReport JSON (scan + telemetry + summary).",
    ),
) -> None:
    """Run one OrgPath governance pass over a tenant snapshot (UIAO_163 / UIAO_174).

    Loads SNAPSHOT_PATH, runs the drift loop against the canonical codebook
    (and, unless --detection-only, the Phase 5 adapter set), and prints a
    rollup: drift findings by severity, planned vs. remediated operations, and
    whether the run halted on a critical finding. Use --out to persist the full
    report (including the UIAO_174 telemetry events) for downstream pipelines.

    The shipped adapters are transport-free, so --no-dry-run plans operations
    but dispatches nothing until a transport is wired in Python. This command
    is the operator-reachable surface of the OrgPath Governance Runtime.

    Example::

        uiao orgtree govern snapshot.json --out report.json
    """
    if not snapshot_path.exists():
        console.print(f"[red]Snapshot file not found: {snapshot_path}[/red]")
        raise typer.Exit(code=1)

    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        snapshot = snapshot_from_dict(payload)
    except (json.JSONDecodeError, SnapshotError) as exc:
        console.print(f"[red]Invalid snapshot: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    runtime = OrgPathGovernanceRuntime() if detection_only else OrgPathGovernanceRuntime.with_canon_adapters()
    report = runtime.govern(snapshot, dry_run=dry_run)

    mode = "detection-only" if detection_only else "full"
    console.print(
        f"[bold]OrgPath governance pass[/bold] — mode={mode}, dry_run={dry_run}, snapshot={report.snapshot_id}"
    )
    console.print(f"  Drift findings : {report.drift_count}")
    for severity in ("P1", "P2", "P3", "P4"):
        count = report.severity_counts.get(severity, 0)
        if count:
            color = {"P1": "red", "P2": "yellow", "P3": "cyan", "P4": "dim"}[severity]
            console.print(f"    {severity} : [{color}]{count}[/{color}]")
    console.print(f"  Planned ops    : {report.planned_count}")
    console.print(f"  Remediated ops : {report.remediated_count}")
    console.print(f"  Telemetry      : {len(report.events)} events")
    if report.halted:
        console.print("  [red]HALTED[/red] — critical finding present; remediation suppressed.")

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Report written to {out}[/green]")
