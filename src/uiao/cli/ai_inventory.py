"""AI Inventory CLI: ``uiao ai-inventory ...`` subcommands.

Operator-reachable surface for the federal AI system identity governance
scanner (UIAO_196 / UIAO_197 / ADR-112 / ADR-114).  Ingests the annual
OMB Federal AI Use Case Inventory CSV and emits drift findings for every
system that violates M-25-21 identity governance obligations.

All commands are read-only (L1 observe per ADR-112 §3).  No writes are
made to any system.

Commands:

- ``scan``   — run the drift scanner against one OMB inventory CSV
- ``diff``   — diff two vintage CSVs into JML lifecycle events
- ``sample`` — print the path to the bundled sample inventory fixture

Examples::

    uiao ai-inventory scan omb-2025.csv
    uiao ai-inventory scan omb-2025.csv --registry uiao-registry.txt --out findings/
    uiao ai-inventory diff --current omb-2025.csv --prior omb-2024.csv
    uiao ai-inventory sample

Canon: UIAO_196, UIAO_197, ADR-112, ADR-114
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from uiao.governance.ai_inventory import detect_events, scan_inventory
from uiao.governance.ai_inventory.schema import AISystemRecord

ai_inventory_app = typer.Typer(
    name="ai-inventory",
    help=(
        "Federal AI system identity governance scanner (M-25-21 / UIAO_196 / ADR-112). "
        "Read-only — no writes to any system."
    ),
    no_args_is_help=True,
)

console = Console()

_SEVERITY_COLOR = {"P1": "red", "P2": "yellow", "P3": "cyan"}

# Path to the bundled sample fixture (installed with the package)
_SAMPLE_CSV = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "sample-ai-inventory-2025.csv"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _fail(message: str) -> None:
    console.print(f"[red]ERROR:[/red] {message}")
    raise typer.Exit(code=1)


def _load_records(csv_path: Path, label: str = "CSV") -> list[AISystemRecord]:
    if not csv_path.exists():
        _fail(f"{label} not found: {csv_path}")
    import csv as _csv

    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(_csv.DictReader(fh))
    if not rows:
        _fail(f"{label} is empty or has no data rows.")
    return [AISystemRecord.from_csv_row(r) for r in rows]


def _print_findings_table(findings: list) -> None:
    if not findings:
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("Sev", width=4)
    table.add_column("Class")
    table.add_column("System")
    table.add_column("Observed", overflow="fold")
    for f in sorted(findings, key=lambda x: x.severity.value):
        color = _SEVERITY_COLOR.get(f.severity.value, "white")
        table.add_row(
            f"[{color}]{f.severity.value}[/{color}]",
            f.drift_class,
            f.name,
            f.observed,
        )
    console.print(table)


def _write_json(out_dir: Path, filename: str, payload: object) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"[green]Written:[/green] {path}")


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


@ai_inventory_app.command("scan")
def scan(
    csv_path: Path = typer.Argument(
        ...,
        help="OMB Federal AI Use Case Inventory CSV (e.g. 2025_individually_reported_AI_use_cases.csv).",
    ),
    registry: Path | None = typer.Option(
        None,
        "--registry",
        "-r",
        help=(
            "Path to a plain-text file listing UIAO machine-identity registry IDs (one per line). "
            "When supplied, systems in the registry that are absent from the OMB CSV emit P1 "
            "DRIFT-IDENTITY::ai-shadow findings."
        ),
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        "-o",
        help="Directory to write per-finding JSON and summary report. Created if absent.",
    ),
    vintage: str | None = typer.Option(
        None,
        "--vintage",
        help="Four-digit inventory year (inferred from filename when omitted).",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Exit 1 if any P1 finding is emitted (CI / BOD gate). Default exits 0.",
    ),
) -> None:
    """Scan an OMB AI inventory CSV for M-25-21 identity governance gaps.

    Emits findings for all six drift classes:

    \\b
    P1  ai-agentic-ungoverned — agentic system deployed without ATO + governance mode
    P1  ai-shadow             — registry entry absent from OMB inventory
    P2  ai-ato-gap            — deployed/pilot system without ATO
    P2  ai-no-orgpath         — system with no organizational placement
    P2  ai-unowned            — system with no named owner (contact email)
    P2  ai-pii-no-pia         — system handling PII without a Privacy Impact Assessment

    Examples::

        uiao ai-inventory scan omb-2025.csv
        uiao ai-inventory scan omb-2025.csv --registry uiao-registry.txt --out findings/
        uiao ai-inventory scan omb-2025.csv --strict
    """
    known_ids: set[str] | None = None
    if registry is not None:
        if not registry.exists():
            _fail(f"Registry file not found: {registry}")
        known_ids = {line.strip() for line in registry.read_text(encoding="utf-8").splitlines() if line.strip()}
        console.print(f"[dim]Registry:[/dim] {len(known_ids)} known system ID(s) loaded from {registry}")

    result = scan_inventory(csv_path, known_registry_ids=known_ids, vintage=vintage)

    console.print(f"\n[bold]AI Inventory Scan[/bold]  {result.scanned_at}")
    console.print(f"  Source  : {result.source_path}")
    console.print(f"  Vintage : {result.inventory_vintage}")
    console.print(
        f"  Records : {len(result.records)} total  [cyan]{len(result.live_records)} live[/cyan] (deployed + pilot)"
    )

    p1 = len(result.p1_findings)
    p2 = len(result.p2_findings)
    total = len(result.findings)
    gate = result.gate_result.get("decision", "UNKNOWN").upper()
    gate_color = "green" if gate == "PASS" else "red"

    console.print(f"  Findings: {total} total  [red]P1={p1}[/red]  [yellow]P2={p2}[/yellow]")
    console.print(f"  Gate    : [{gate_color}]{gate}[/{gate_color}]")

    if result.findings:
        console.print()
        _print_findings_table(result.findings)

    if out is not None:
        data = json.loads(result.to_json())
        _write_json(out, "scan-result.json", data)
        # Per-agency split
        by_agency: dict[str, list] = {}
        for f in data["findings"]:
            agency = (f.get("name") or "").split("::")[0]
            by_agency.setdefault(agency, []).append(f)
        for agency, agency_findings in by_agency.items():
            safe = agency.replace("/", "-").replace(":", "-") or "UNKNOWN"
            _write_json(out, f"findings-{safe}.json", {"agency": agency, "findings": agency_findings})

    if strict and p1 > 0:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# diff (JML vintage comparison)
# ---------------------------------------------------------------------------


@ai_inventory_app.command("diff")
def diff(
    current: Path = typer.Option(..., "--current", "-c", help="Current-year OMB inventory CSV."),
    prior: Path = typer.Option(..., "--prior", "-p", help="Prior-year OMB inventory CSV."),
    out: Path | None = typer.Option(
        None,
        "--out",
        "-o",
        help="Directory to write jml-event-log.json and jml-action-log.json evidence artifacts.",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Exit 1 if any joiner or leaver event is detected (CI gate).",
    ),
) -> None:
    """Diff two vintage inventory CSVs into JML lifecycle events (UIAO_197 / ADR-114).

    Detects three event types:

    \\b
    ai-system.joiner          — system enters pilot/deployed in the current vintage
    ai-system.mover           — governance field(s) changed between vintages
    ai-system.leaver          — system moved to retired stage in current vintage
    ai-system.candidate-leaver — system absent from current vintage (pending confirmation)

    When --out is supplied, writes the UIAO_197 §7 evidence artifacts:
    jml-event-log.json and jml-action-log.json.

    Examples::

        uiao ai-inventory diff --current omb-2025.csv --prior omb-2024.csv
        uiao ai-inventory diff --current omb-2025.csv --prior omb-2024.csv --out evidence/
    """
    current_records = _load_records(current, "current vintage")
    prior_records = _load_records(prior, "prior vintage")

    events = detect_events(current_records, prior_records)

    console.print("\n[bold]AI System JML Lifecycle Diff[/bold]")
    console.print(f"  Current vintage : {current}  ({len(current_records)} records)")
    console.print(f"  Prior vintage   : {prior}  ({len(prior_records)} records)")
    console.print(
        f"  Events: "
        f"[green]joiners={len(events.joiners)}[/green]  "
        f"[cyan]movers={len(events.movers)}[/cyan]  "
        f"[yellow]leavers={len(events.leavers)}[/yellow]  "
        f"[dim]candidate-leavers={len(events.candidate_leavers)}[/dim]"
    )

    if events.staleness_findings:
        console.print(f"  Staleness (P3)  : {len(events.staleness_findings)} finding(s)")

    def _event_table(event_list: list, label: str, color: str) -> None:
        if not event_list:
            return
        console.print(f"\n[bold {color}]{label}[/bold {color}]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("System")
        table.add_column("Agency")
        table.add_column("Stage")
        table.add_column("Changed fields", overflow="fold")
        for ev in event_list:
            table.add_row(
                ev.record.identity_label,
                ev.record.agency,
                ev.record.development_stage.value,
                ", ".join(ev.changed_fields) if ev.changed_fields else "—",
            )
        console.print(table)

    _event_table(events.joiners, "Joiners", "green")
    _event_table(events.movers, "Movers", "cyan")
    _event_table(events.leavers, "Leavers", "yellow")
    _event_table(events.candidate_leavers, "Candidate leavers (confirmation required)", "dim")

    if out is not None:
        from uiao.governance.ai_inventory.jml import write_evidence_artifacts

        written = write_evidence_artifacts(events, out)
        for path in written:
            console.print(f"[green]Written:[/green] {path}")

    if strict and (events.joiners or events.leavers):
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# sample
# ---------------------------------------------------------------------------


@ai_inventory_app.command("sample")
def sample() -> None:
    """Print the path to the bundled sample OMB inventory fixture.

    The sample CSV contains 10 rows covering every finding class:
    clean, ATO gap, unowned, no-orgpath, PII/no-PIA, agentic-ungoverned,
    pre-deployment (excluded), and retired (excluded).

    Example::

        uiao ai-inventory scan $(uiao ai-inventory sample)
    """
    # Resolve relative to installed package; fall back to dev-tree path
    pkg_fixture = Path(__file__).parent / "fixtures" / "sample-ai-inventory-2025.csv"
    dev_fixture = _SAMPLE_CSV

    for candidate in (pkg_fixture, dev_fixture):
        if candidate.exists():
            console.print(str(candidate.resolve()))
            return

    _fail(
        "Sample fixture not found. Re-install the package or locate "
        "tests/fixtures/sample-ai-inventory-2025.csv in the source tree."
    )
