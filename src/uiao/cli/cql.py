"""uiao.cli.cql — Typer sub-app for the `uiao cql` command group.

Exposes the Compliance Query Language (CQL) engine (UIAO_108) at the CLI
so operators can interrogate compliance data without writing Python.

Note on control IDs
-------------------
SCuBA → IR bundles use KSI IDs as control identifiers (e.g. ``KSI-IA-01``,
``KSI-IA-02``), not NIST-style control IDs (e.g. ``AC-2``).  Use KSI IDs in
your queries unless you have a bundle produced by a NIST-mapped adapter.

Usage
-----
    uiao cql query "SHOW CONTROLS WHERE status = 'FAIL'" --bundle bundle.json
    uiao cql query "SHOW EVIDENCE FOR CONTROL 'KSI-IA-02'" --bundle bundle.json --format json
    uiao cql query "SHOW DRIFT WHERE drift_class = 'DRIFT-SEMANTIC'" --bundle bundle.json

    # Note: SHOW DRIFT requires a bundle that contains drift states.
    # Bundles produced by ``uiao ir-evidence-bundle`` include drift states
    # when the underlying SCuBA run detected drift.

CQL syntax
----------
    SHOW CONTROLS [WHERE field = 'value' [AND ...]] [SINCE 'ISO-date'] [ORDER BY field [ASC|DESC]]
    SHOW EVIDENCE [FOR CONTROL 'ksi-id'] [WHERE ...] [SINCE 'ISO-date'] [ORDER BY ...]
    SHOW DRIFT [WHERE ...] [SINCE 'ISO-date'] [ORDER BY ...]
    SHOW POAM [WHERE ...] [SINCE 'ISO-date'] [ORDER BY ...]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

from uiao.cql import CQLEngine, CQLExecutionError, CQLParseError

cql_app = typer.Typer(
    name="cql",
    help="Compliance Query Language (CQL) — SQL-like queries over evidence bundles (UIAO_108).",
    no_args_is_help=True,
)

_console = Console()


# ---------------------------------------------------------------------------
# Bundle → CQL data adapters
# ---------------------------------------------------------------------------


def _verdict(evaluation: dict) -> str:
    if evaluation.get("passed"):
        return "pass"
    if evaluation.get("failed"):
        return "fail"
    if evaluation.get("warning"):
        return "warn"
    return "inconclusive"


def _status(evaluation: dict) -> str:
    if evaluation.get("passed"):
        return "satisfied"
    if evaluation.get("failed"):
        return "not-satisfied"
    if evaluation.get("warning"):
        return "partially-satisfied"
    return "unknown"


def _bundle_to_cql_data(bundle: dict) -> dict:
    """Convert an evidence-bundle dict (from ir-evidence-bundle --out) to CQL engine inputs.

    The bundle format is produced by ``build_bundle_from_transform_result`` and
    serialised via ``EvidenceBundle.to_dict()``.  CQL engine expects plain list-of-dicts
    for each data domain.
    """
    raw_evidence: list = bundle.get("evidence", [])
    raw_drift: list = bundle.get("drift_states", [])
    raw_controls: list = bundle.get("controls", [])
    raw_poam: list = bundle.get("poam", [])

    # ── Evidence ─────────────────────────────────────────────────────────────
    evidence_rows: list[dict[str, Any]] = []
    for ev in raw_evidence:
        evaluation = ev.get("evaluation", {})
        evidence_rows.append(
            {
                "id": ev.get("id", ""),
                "control_id": ev.get("control_id") or ev.get("data", {}).get("control_id", ""),
                "ksi_id": ev.get("data", {}).get("ksi_id", ""),
                "verdict": _verdict(evaluation),
                "status": _status(evaluation),
                "source": ev.get("source", ""),
                "generated_at": ev.get("timestamp", ""),
            }
        )

    # ── Controls ──────────────────────────────────────────────────────────────
    # Build control status from evidence when raw_controls are sparse.
    _ctrl_status: dict[str, str] = {}
    _ctrl_severity: dict[str, str] = {}
    for ev in evidence_rows:
        cid = ev.get("control_id", "")
        if not cid:
            continue
        if ev["verdict"] == "fail":
            _ctrl_status[cid] = "FAIL"
        elif ev["verdict"] == "warn" and _ctrl_status.get(cid) != "FAIL":
            _ctrl_status[cid] = "WARN"
        elif cid not in _ctrl_status:
            _ctrl_status[cid] = "PASS"

    control_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ctrl in raw_controls:
        cid = ctrl.get("id", "")
        if not cid:
            continue
        seen.add(cid)
        control_rows.append(
            {
                "id": cid,
                "status": _ctrl_status.get(cid, "UNKNOWN"),
                "severity": _ctrl_severity.get(cid, ctrl.get("severity", "Medium")),
                "last_assessed": bundle.get("provenance", {}).get("timestamp", ""),
                "description": ctrl.get("description", ""),
                "source": ctrl.get("source", ""),
            }
        )
    # Synthetic controls derived from evidence (for bundles with sparse controls list)
    for cid, status in _ctrl_status.items():
        if cid not in seen:
            control_rows.append(
                {
                    "id": cid,
                    "status": status,
                    "severity": _ctrl_severity.get(cid, "Medium"),
                    "last_assessed": bundle.get("provenance", {}).get("timestamp", ""),
                }
            )

    # ── Drift ─────────────────────────────────────────────────────────────────
    drift_rows: list[dict[str, Any]] = []
    for ds in raw_drift:
        if not ds.get("drift_detected"):
            continue
        drift_rows.append(
            {
                "id": ds.get("id", ""),
                "tenant": ds.get("resource_id", ""),
                "control": ds.get("policy_ref", ""),
                "drift_class": ds.get("drift_class") or "DRIFT-SEMANTIC",
                "classification": ds.get("classification", "risky"),
                "generated_at": ds.get("provenance", {}).get("timestamp", ""),
            }
        )

    # ── POAM (explicit or synthesised from FAIL evidence) ────────────────────
    poam_rows: list[dict[str, Any]] = raw_poam if raw_poam else []
    if not poam_rows:
        for ev in evidence_rows:
            if ev["verdict"] in ("fail", "warn"):
                poam_rows.append(
                    {
                        "id": f"POAM-{ev['id']}",
                        "status": "Open",
                        "severity": "High" if ev["verdict"] == "fail" else "Medium",
                        "control_id": ev.get("control_id", ""),
                        "ksi_id": ev.get("ksi_id", ""),
                        "detected_at": ev.get("generated_at", ""),
                    }
                )

    return {
        "controls": control_rows,
        "evidence": evidence_rows,
        "drift": drift_rows,
        "poam": poam_rows,
    }


# ---------------------------------------------------------------------------
# Rich table rendering
# ---------------------------------------------------------------------------

_TABLE_COLUMNS: dict[str, list[str]] = {
    "CONTROLS": ["id", "status", "severity", "last_assessed"],
    "EVIDENCE": ["id", "control_id", "verdict", "status", "source"],
    "DRIFT": ["id", "control", "drift_class", "classification"],
    "POAM": ["id", "status", "severity", "control_id"],
}

_STATUS_STYLES: dict[str, str] = {
    "FAIL": "red",
    "fail": "red",
    "not-satisfied": "red",
    "PASS": "green",
    "pass": "green",
    "satisfied": "green",
    "WARN": "yellow",
    "warn": "yellow",
    "partially-satisfied": "yellow",
    "Open": "red",
    "Closed": "green",
}


def _render_table(records: list[dict], query_type: str) -> None:
    fallback_cols = list(records[0].keys()) if records else []
    cols = _TABLE_COLUMNS.get(query_type.upper(), fallback_cols)
    table = Table(show_header=True, header_style="bold blue")
    for col in cols:
        table.add_column(col)
    for rec in records:
        row_vals: list[str] = []
        for col in cols:
            val = str(rec.get(col, ""))
            style = _STATUS_STYLES.get(val, "")
            row_vals.append(f"[{style}]{val}[/{style}]" if style else val)
        table.add_row(*row_vals)
    _console.print(table)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@cql_app.command("query")
def query_cmd(
    cql_string: str = typer.Argument(  # noqa: B008
        ...,
        help=("CQL query string. Example: \"SHOW CONTROLS WHERE status = 'FAIL'\""),
    ),
    bundle: str = typer.Option(  # noqa: B008
        ...,
        "--bundle",
        "-b",
        help=(
            "Path to an evidence bundle JSON file produced by "
            "``uiao ir-evidence-bundle --out bundle.json``. "
            "SHOW DRIFT queries require a bundle that contains drift states "
            "(drift_states is non-empty); bundles from SCuBA runs without "
            "detected drift will return 0 DRIFT rows."
        ),
    ),
    output: Optional[str] = typer.Option(  # noqa: B008
        None,
        "--output",
        "-o",
        help="Write JSON results to this file (default: stdout).",
    ),
    fmt: str = typer.Option(  # noqa: B008
        "table",
        "--format",
        "-f",
        help="Output format: table | json",
    ),
) -> None:
    """Execute a CQL (Compliance Query Language) query against an evidence bundle.

    CQL is an SQL-like language for querying compliance data domains:

    \\b
    Supported query types
    ---------------------
        SHOW CONTROLS  [WHERE field = 'value'] [SINCE 'ISO-date'] [ORDER BY field [ASC|DESC]]
        SHOW EVIDENCE  [FOR CONTROL 'id'] [WHERE ...] [SINCE '...'] [ORDER BY ...]
        SHOW DRIFT     [WHERE ...] [SINCE '...'] [ORDER BY ...]
        SHOW POAM      [WHERE ...] [SINCE '...'] [ORDER BY ...]

    \\b
    Supported operators
    -------------------
        =, !=, >=, <=, >, <, LIKE   (LIKE uses substring match)

    \\b
    Examples
    --------
        uiao cql query "SHOW CONTROLS WHERE status = 'FAIL'" --bundle bundle.json

        uiao cql query "SHOW EVIDENCE FOR CONTROL 'KSI-IA-02'" --bundle bundle.json --format json

        uiao cql query "SHOW DRIFT WHERE drift_class = 'DRIFT-SEMANTIC'" --bundle bundle.json

        uiao cql query "SHOW POAM WHERE severity >= 'High' ORDER BY severity DESC" \\
            --bundle bundle.json --output poam.json
    """
    # ── Load bundle ──────────────────────────────────────────────────────────
    bundle_path = Path(bundle)
    if not bundle_path.exists():
        _console.print(f"[red]Bundle file not found: {bundle_path}[/red]")
        raise typer.Exit(code=1)

    try:
        bundle_data = json.loads(bundle_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _console.print(f"[red]Invalid JSON in bundle file: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    cql_data = _bundle_to_cql_data(bundle_data)
    engine = CQLEngine(
        controls=cql_data["controls"],
        evidence=cql_data["evidence"],
        drift=cql_data["drift"],
        poam=cql_data["poam"],
    )

    # ── Execute query ─────────────────────────────────────────────────────────
    try:
        result = engine.execute(cql_string)
    except CQLParseError as exc:
        _console.print(f"[red]CQL parse error: {exc}[/red]")
        raise typer.Exit(code=1) from exc
    except CQLExecutionError as exc:
        _console.print(f"[red]CQL execution error: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    result_dict = result.to_dict()

    # ── Output ─────────────────────────────────────────────────────────────────
    if fmt.lower() == "json":
        out_text = json.dumps(result_dict, indent=2, ensure_ascii=False)
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(out_text, encoding="utf-8")
            _console.print(f"[green]Results written to {output}[/green]")
        else:
            typer.echo(out_text)
    else:
        _console.print(
            f"[bold]Query:[/bold] {cql_string}  "
            f"[bold]Total:[/bold] {result.total}  "
            f"[bold]Type:[/bold] {result.query_type}"
        )
        if result.records:
            _render_table(result.records, result.query_type)
        else:
            _console.print("[dim]No records matched.[/dim]")
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(json.dumps(result_dict, indent=2, ensure_ascii=False), encoding="utf-8")
            _console.print(f"[green]Results written to {output}[/green]")
