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
from uiao.modernization.orgtree.ad_assign import OrgPathAssigner
from uiao.modernization.orgtree.ad_mapping import MappingError, OrgPathMapping
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


def _load_ad_records(
    from_export: Path | None,
    ldap_server: str,
    base_dn: str,
    username: str,
    password: str,
    target_type: str,
    mapping: OrgPathMapping | None,
) -> list[dict]:
    """Resolve AD object records from an export file or a live LDAP read."""
    from uiao.adapters.modernization.active_directory.directory_reader import (
        LdapDirectoryReader,
        read_records_from_export,
    )

    if from_export is not None:
        if not from_export.exists():
            console.print(f"[red]Export file not found: {from_export}[/red]")
            raise typer.Exit(code=1)
        return read_records_from_export(from_export)

    if not ldap_server or not base_dn:
        console.print("[red]Provide either --from-export, or --ldap-server and --base-dn for a live read.[/red]")
        raise typer.Exit(code=1)

    reader = LdapDirectoryReader(ldap_server, base_dn, username, password)
    try:
        if target_type == "device":
            return reader.read_computers(mapping)
        return reader.read_users(mapping)
    except ImportError as exc:  # ldap3 missing
        console.print(f"[red]Live LDAP read requires ldap3: {exc}[/red]")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # connection / bind failure
        console.print(f"[red]LDAP read failed: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@orgtree_app.command("assess")
def assess(
    from_export: Path | None = typer.Option(
        None,
        "--from-export",
        help="Read AD object records from a JSON export instead of live LDAP (repeatable / offline).",
    ),
    ldap_server: str = typer.Option("", "--ldap-server", help="LDAP server for a live read, e.g. dc01.contoso.com."),
    base_dn: str = typer.Option("", "--base-dn", help="Search base DN, e.g. DC=contoso,DC=com."),
    username: str = typer.Option("", "--username", help="Bind user (empty = Kerberos/GSSAPI on a domain host)."),
    password: str = typer.Option("", "--password", help="Bind password (omit when using GSSAPI)."),
    target_type: str = typer.Option("user", "--target-type", help="user | device — which AD plane to read/assess."),
    mapping_path: Path | None = typer.Option(
        None, "--mapping", help="Tenant AD→facet mapping YAML override (defaults to the shipped mapping)."
    ),
    out: Path | None = typer.Option(None, "--out", "-o", help="Write the facet assignments + findings as JSON."),
    write: bool = typer.Option(
        False, "--write", help="Plan/apply device facet writes to Entra/ARM (target-type=device only)."
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="With --write: suppress dispatch (default). --no-dry-run needs UIAO_ENTRA_* creds.",
    ),
    cloud: str = typer.Option(
        "commercial", "--cloud", help="Graph cloud for --no-dry-run writes: commercial | gcc-high | dod."
    ),
) -> None:
    """Read/assess Active Directory and derive OrgPath facet values (UIAO_151).

    Reads AD object records (live LDAP or --from-export), derives each object's
    OrgPath facets via the AD→facet mapping, validates every derived value
    against the codebook, and reports the per-target assignments + any findings
    (AD values that don't map to a codebook value).

    With --write (target-type=device) it plans the per-facet writes through the
    Entra device adapter — Graph extensionAttributes for Entra-joined devices,
    ARM tags for Arc servers — dry-run by default. --no-dry-run dispatches live
    writes using UIAO_ENTRA_* client-credentials.

    Examples::

        uiao orgtree assess --from-export ad-users.json --out assignments.json
        uiao orgtree assess --ldap-server dc01 --base-dn DC=contoso,DC=com
        uiao orgtree assess --from-export ad-devices.json --target-type device --write
    """
    if target_type not in ("user", "device"):
        console.print(f"[red]--target-type must be 'user' or 'device', got '{target_type}'.[/red]")
        raise typer.Exit(code=1)

    mapping: OrgPathMapping | None = None
    if mapping_path is not None:
        try:
            mapping = OrgPathMapping.from_yaml(mapping_path)
        except (MappingError, OSError) as exc:
            console.print(f"[red]Invalid mapping: {exc}[/red]")
            raise typer.Exit(code=1) from exc

    records = _load_ad_records(from_export, ldap_server, base_dn, username, password, target_type, mapping)
    assigner = OrgPathAssigner(mapping=mapping)
    results = assigner.assign_all(records, target_type=target_type)

    total_facets = sum(r.assigned_count for r in results)
    total_findings = sum(len(r.findings) for r in results)
    console.print(f"[bold]OrgPath assessment[/bold] — {len(results)} {target_type}(s) from AD")
    console.print(f"  Facets derived : {total_facets}")
    console.print(f"  Findings       : {total_findings}")

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Assignments written to {out}[/green]")

    if write:
        if target_type != "device":
            console.print("[red]--write applies only to device assignments (use --target-type device).[/red]")
            raise typer.Exit(code=1)
        _apply_device_writes(results, records, dry_run=dry_run, cloud=cloud)


def _apply_device_writes(results: list, records: list[dict], *, dry_run: bool, cloud: str) -> None:
    """Plan (and optionally dispatch) device facet writes via the Entra adapter."""
    from uiao.adapters.entra_device_orgpath import EntraDeviceOrgPathAdapter
    from uiao.modernization.orgtree.device_orgpath import DeviceFacetAssignment, DeviceOrgPathPlanner

    disposition_by_id = {
        (r.get("id") or r.get("objectGUID") or r.get("distinguishedName") or r.get("sAMAccountName") or ""): r.get(
            "disposition", "ENTRA-DEVICE"
        )
        for r in records
    }
    assignments = [
        DeviceFacetAssignment(
            device_id=res.target_id,
            disposition=disposition_by_id.get(res.target_id, "ENTRA-DEVICE"),
            facet_values=dict(res.facet_values),
        )
        for res in results
    ]

    graph_transport = None
    arm_transport = None
    if not dry_run:
        from uiao.adapters.graph_transport import GraphTransport

        try:
            graph_transport = GraphTransport.from_environment(cloud=cloud)
            arm_transport = graph_transport  # ARM writes share the credential path
        except Exception as exc:
            console.print(f"[red]--no-dry-run requires UIAO_ENTRA_* credentials: {exc}[/red]")
            raise typer.Exit(code=1) from exc

    planner = DeviceOrgPathPlanner(load_codebook())
    adapter = EntraDeviceOrgPathAdapter(planner, graph_transport=graph_transport, arm_transport=arm_transport)
    ops = adapter.plan(assignments)
    result = adapter.apply(ops, dry_run=dry_run)

    console.print(f"[bold]Device writes[/bold] — dry_run={dry_run}, cloud={cloud}")
    console.print(f"  Planned : {result.planned_count}")
    console.print(f"  Sent    : {result.sent_count}")
    console.print(f"  Skipped : {result.skipped_count}")
    if result.error_count:
        console.print(f"  [red]Errors  : {result.error_count}[/red]")
