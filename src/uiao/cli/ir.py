"""uiao.cli.ir — Typer sub-app for the `uiao ir` command group.

Mount point
-----------
    # in uiao/cli/app.py
    from uiao.cli.ir import ir_app
    app.add_typer(ir_app, name="ir")

Usage (after `pip install -e .`)
---------------------------------
    uiao ir scuba-transform exports/scuba/normalized.json
    uiao ir evidence-bundle exports/scuba/normalized.json --out exports/ir/bundle.json
    uiao ir governance-report exports/scuba/normalized.json
    uiao ir validate exports/scuba/normalized.json --strict

Or via module invocation:
    python -m uiao.cli ir scuba-transform exports/scuba/normalized.json
"""

from __future__ import annotations

import typer
from rich.console import Console

ir_app = typer.Typer(
    name="ir",
    help="Intermediate Representation operations (SCuBA -> IR -> Evidence/Bundle/POA&M).",
    add_completion=False,
)

_console = Console()


@ir_app.command("scuba-transform")
def ir_scuba_transform(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write full evidence JSON to file."),
) -> None:
    """Transform normalized SCuBA JSON -> IR Evidence objects and print summary.

    Example::

        uiao ir scuba-transform examples/quickstart/scuba-normalized.json
    """
    import json as _json

    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir

    _console.print(f"[bold]Transforming SCuBA JSON: {normalized_json}...[/bold]")
    result = transform_scuba_to_ir(normalized_json)
    _console.print(result.summary())
    if out:
        from pathlib import Path as _Path

        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(_json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        _console.print(f"[green]Evidence JSON written to {out}[/green]")


@ir_app.command("evidence-bundle")
def ir_evidence_bundle(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write canonical bundle JSON to file."),
) -> None:
    """Build a canonical EvidenceBundle from a SCuBA transform and print summary.

    Example::

        uiao ir evidence-bundle examples/quickstart/scuba-normalized.json --out /tmp/bundle.json
    """
    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.evidence.bundle import build_bundle_from_transform_result

    _console.print(f"[bold]Building EvidenceBundle from: {normalized_json}...[/bold]")
    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    _console.print(bundle.summary())
    if out:
        from pathlib import Path as _Path

        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(bundle.to_canonical(), encoding="utf-8")
        _console.print(f"[green]Bundle JSON written to {out}[/green]")


@ir_app.command("poam-export")
def ir_poam_export(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write POA&M JSON to file."),
) -> None:
    """Export POA&M rows (FAIL + WARN only) from a SCuBA run and print summary.

    Example::

        uiao ir poam-export examples/quickstart/scuba-normalized.json --out /tmp/poam.json
    """
    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.evidence.bundle import build_bundle_from_transform_result
    from uiao.evidence.poam import build_poam, poam_summary, poam_to_json

    _console.print(f"[bold]Generating POA&M from: {normalized_json}...[/bold]")
    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    rows = build_poam(bundle)
    _console.print(poam_summary(rows))
    if out:
        from pathlib import Path as _Path

        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(poam_to_json(rows), encoding="utf-8")
        _console.print(f"[green]POA&M JSON written to {out}[/green]")


@ir_app.command("drift-detect")
def ir_drift_detect(
    expected: str = typer.Argument(..., help="Path to expected-state JSON file."),
    actual: str = typer.Argument(..., help="Path to actual-state JSON file."),
    resource_id: str = typer.Option("resource", "--resource-id", "-r", help="Resource identifier."),
    policy_ref: str = typer.Option("policy", "--policy-ref", "-p", help="Policy reference."),
    out: str = typer.Option("", "--out", "-o", help="Write DriftState JSON to file."),
) -> None:
    """Detect drift between two IR state JSON files and print classification.

    Example::

        uiao ir drift-detect expected.json actual.json
    """
    import json as _json
    from datetime import datetime, timezone
    from pathlib import Path as _Path

    from uiao.governance.drift import build_drift_state
    from uiao.ir.models.core import ProvenanceRecord

    expected_state = _json.loads(_Path(expected).read_text(encoding="utf-8"))
    actual_state = _json.loads(_Path(actual).read_text(encoding="utf-8"))
    prov = ProvenanceRecord(
        source="cli:drift-detect",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="cli",
        content_hash=None,
        actor="cli",
    )
    drift = build_drift_state(
        resource_id=resource_id,
        policy_ref=policy_ref,
        expected_state=expected_state,
        actual_state=actual_state,
        provenance=prov,
    )
    status = "[red]DRIFT DETECTED[/red]" if drift.drift_detected else "[green]NO DRIFT[/green]"
    _console.print(f"Resource  : {drift.resource_id}")
    _console.print(f"Policy    : {drift.policy_ref}")
    _console.print(f"Status    : {status}")
    _console.print(f"Class     : {drift.classification}")
    _console.print(
        f"Delta     : added={drift.delta.get('added', [])} removed={drift.delta.get('removed', [])} changed={drift.delta.get('changed', [])}"
    )
    if out:
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(drift.to_canonical(), encoding="utf-8")
        _console.print(f"[green]DriftState JSON written to {out}[/green]")


@ir_app.command("governance-report")
def ir_governance_report(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write governance actions JSON to file."),
) -> None:
    """Run full governance pipeline: SCuBA -> IR -> Evidence -> Actions -> Report.

    Example::

        uiao ir governance-report examples/quickstart/scuba-normalized.json
    """
    import json as _json
    from pathlib import Path as _Path

    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.evidence.bundle import build_bundle_from_transform_result
    from uiao.governance.actions import build_governance_actions
    from uiao.governance.report import format_governance_report

    _console.print(f"[bold]Running governance pipeline for: {normalized_json}...[/bold]")
    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    actions = build_governance_actions(bundle.evidence, bundle.drift_states)
    report = format_governance_report(actions)
    _console.print(report)
    _console.print(f"\nTotal actions: {len(actions)}")
    if out:
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "ksi_id": a.ksi_id,
                "control_id": a.control_id,
                "policy_id": a.policy_id,
                "severity": a.severity,
                "drift_classification": a.drift_classification,
                "owner": a.owner,
                "sla_days": a.sla_days,
                "action_type": a.action_type,
                "description": a.description,
                "evidence_id": a.evidence_id,
            }
            for a in actions
        ]
        _Path(out).write_text(_json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        _console.print(f"[green]Governance report JSON written to {out}[/green]")


@ir_app.command("ssp-report")
def ir_ssp_report(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown | json"),
    out: str = typer.Option("", "--out", "-o", help="Write output to file."),
) -> None:
    """Generate SSP narrative + lineage from SCuBA -> IR -> Evidence -> Governance.

    Example::

        uiao ir ssp-report examples/quickstart/scuba-normalized.json --format markdown
    """
    import json as _json
    from pathlib import Path as _Path

    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.coverage.coverage import build_coverage_links
    from uiao.evidence.bundle import build_bundle_from_transform_result
    from uiao.governance.actions import build_governance_actions
    from uiao.ssp.lineage import build_lineage_index
    from uiao.ssp.narrative import build_control_narratives, format_ssp_markdown

    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    actions = build_governance_actions(bundle.evidence, bundle.drift_states)
    links = build_coverage_links(bundle.evidence)
    narratives = build_control_narratives(links, actions)
    if fmt.lower() == "json":
        lineage = build_lineage_index(links, actions)
        output_text = _json.dumps(lineage, indent=2)
    else:
        output_text = format_ssp_markdown(narratives)
    typer.echo(output_text)
    if out:
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(output_text, encoding="utf-8")
        _console.print("[green]SSP report written to " + out + "[/green]")


@ir_app.command("auditor-bundle")
def ir_auditor_bundle(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out_dir: str = typer.Option("exports/auditor-bundle", "--out-dir", "-o", help="Output directory for artifacts."),
) -> None:
    """Run full pipeline and write all auditor artifacts to a directory.

    Example::

        uiao ir auditor-bundle examples/quickstart/scuba-normalized.json --out-dir /tmp/uiao-quickstart
    """
    from uiao.auditor.bundle import build_auditor_bundle

    _console.print(f"[bold]Building auditor bundle from: {normalized_json}...[/bold]")
    manifest = build_auditor_bundle(normalized_json, out_dir)
    _console.print(f"[green]Bundle written to {out_dir}[/green]")
    s = manifest["summary"]
    _console.print(f"  Evidence : {s['evidence_total']}")
    _console.print(f"  Actions  : {s['governance_actions']}")
    _console.print(f"  POA&M    : {s['poam_items']}")


@ir_app.command("diff")
def ir_diff(
    run_a: str = typer.Argument(..., help="Path to first normalized SCuBA JSON file."),
    run_b: str = typer.Argument(..., help="Path to second normalized SCuBA JSON file."),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Output format: markdown | json"),
    out: str = typer.Option("", "--out", "-o", help="Write output to file."),
) -> None:
    """Diff two SCuBA runs: KSI changes, evidence hash deltas, status changes.

    Example::

        uiao ir diff run-a.json run-b.json
    """
    from pathlib import Path as _Path

    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.diff.engine import diff_runs, format_diff_json, format_diff_markdown

    result_a = transform_scuba_to_ir(run_a)
    result_b = transform_scuba_to_ir(run_b)
    diff = diff_runs(result_a, result_b)
    output_text = format_diff_json(diff) if fmt.lower() == "json" else format_diff_markdown(diff)
    typer.echo(output_text)
    if out:
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(output_text, encoding="utf-8")
        _console.print("[green]Diff written to " + out + "[/green]")


@ir_app.command("validate")
def ir_validate(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file to validate."),
    strict: bool = typer.Option(False, "--strict", help="Exit non-zero on warnings."),
) -> None:
    """Validate a normalized SCuBA JSON file for IR pipeline conformance.

    Example::

        uiao ir validate examples/quickstart/scuba-normalized.json --strict
    """
    from uiao.validators.ir_validator import validate_normalized_json

    result = validate_normalized_json(normalized_json)
    for err in result.errors:
        _console.print(f"[red]ERROR: {err}[/red]")
    for warn in result.warnings:
        _console.print(f"[yellow]WARN:  {warn}[/yellow]")
    if result.valid:
        _console.print("[green]VALID[/green]")
        if result.warnings and strict:
            raise typer.Exit(code=1)
    else:
        _console.print(f"[red]INVALID — {len(result.errors)} error(s)[/red]")
        raise typer.Exit(code=1)


@ir_app.command("freshness")
def ir_freshness(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write freshness JSON to file."),
    threshold_days: int = typer.Option(30, "--threshold-days", "-t", help="Default freshness threshold in days."),
) -> None:
    """Compute evidence freshness and generate refresh actions for stale evidence.

    Example::

        uiao ir freshness examples/quickstart/scuba-normalized.json --threshold-days 30
    """
    import json as _json
    from pathlib import Path as _Path

    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.evidence.bundle import build_bundle_from_transform_result
    from uiao.freshness.engine import build_freshness_records, generate_refresh_actions
    from uiao.governance.actions import build_governance_actions

    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    existing_actions = build_governance_actions(bundle.evidence, bundle.drift_states)
    thresholds = {"default": threshold_days}
    records = build_freshness_records(bundle.evidence, thresholds=thresholds)
    fresh = sum(1 for r in records if r.status == "fresh")
    stale_soon = sum(1 for r in records if r.status == "stale-soon")
    stale = sum(1 for r in records if r.status == "stale")
    _console.print(f"[bold]Freshness report for: {normalized_json}[/bold]")
    _console.print(f"  Fresh      : [green]{fresh}[/green]")
    _console.print(f"  Stale-soon : [yellow]{stale_soon}[/yellow]")
    _console.print(f"  Stale      : [red]{stale}[/red]")
    refresh_actions = generate_refresh_actions(records, existing_actions=existing_actions)
    _console.print(f"  Refresh actions generated: {len(refresh_actions)}")
    if out:
        import dataclasses as _dc

        payload = {
            "freshness_records": [_dc.asdict(r) for r in records],
            "refresh_actions": [
                {
                    "ksi_id": a.ksi_id,
                    "control_id": a.control_id,
                    "policy_id": a.policy_id,
                    "severity": a.severity,
                    "drift_classification": a.drift_classification,
                    "owner": a.owner,
                    "sla_days": a.sla_days,
                    "action_type": a.action_type,
                    "description": a.description,
                    "evidence_id": a.evidence_id,
                }
                for a in refresh_actions
            ],
        }
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(_json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        _console.print("[green]Freshness report written to " + out + "[/green]")


@ir_app.command("dashboard")
def ir_dashboard(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write dashboard JSON to file."),
    threshold_days: int = typer.Option(30, "--threshold-days", "-t", help="Default freshness threshold in days."),
) -> None:
    """Build IR governance dashboard: evidence freshness + governance action summary.

    Example::

        uiao ir dashboard examples/quickstart/scuba-normalized.json --out /tmp/dashboard.json
    """
    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.dashboard.ir_dashboard import export_ir_dashboard
    from uiao.evidence.bundle import build_bundle_from_transform_result
    from uiao.governance.actions import build_governance_actions

    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    actions = build_governance_actions(bundle.evidence, bundle.drift_states)
    thresholds = {"default": threshold_days}
    _console.print(f"[bold]Building IR dashboard for: {normalized_json}...[/bold]")
    if out:
        path = export_ir_dashboard(bundle.evidence, actions, out, thresholds=thresholds)
        _console.print("[green]Dashboard written to " + path + "[/green]")
    else:
        from uiao.dashboard.ir_dashboard import build_ir_dashboard

        dashboard = build_ir_dashboard(bundle.evidence, actions, thresholds=thresholds)
        _console.print(f"  Evidence total : {dashboard['evidence_total']}")
        fs = dashboard["freshness_summary"]
        _console.print(f"  Fresh          : [green]{fs['fresh']}[/green]")
        _console.print(f"  Stale-soon     : [yellow]{fs['stale_soon']}[/yellow]")
        _console.print(f"  Stale          : [red]{fs['stale']}[/red]")
        gs = dashboard["governance_summary"]
        _console.print(f"  Total actions  : {gs['total_actions']}")


@ir_app.command("freshness-schedule")
def ir_freshness_schedule(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write schedule JSON to file."),
    threshold_days: int = typer.Option(30, "--threshold-days", "-t", help="Default freshness threshold in days."),
) -> None:
    """Build a refresh job schedule from stale evidence and print the schedule summary.

    Example::

        uiao ir freshness-schedule examples/quickstart/scuba-normalized.json
    """
    import dataclasses as _dc
    import json as _json
    from pathlib import Path as _Path

    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.evidence.bundle import build_bundle_from_transform_result
    from uiao.freshness.engine import build_freshness_records, generate_refresh_actions
    from uiao.freshness.scheduler import build_refresh_schedule, schedule_summary
    from uiao.governance.actions import build_governance_actions

    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    existing_actions = build_governance_actions(bundle.evidence, bundle.drift_states)
    thresholds = {"default": threshold_days}
    records = build_freshness_records(bundle.evidence, thresholds=thresholds)
    refresh_actions = generate_refresh_actions(records, existing_actions=existing_actions)
    jobs = build_refresh_schedule(records, refresh_actions)
    _console.print(schedule_summary(jobs))
    if out:
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        payload = [_dc.asdict(j) for j in jobs]
        _Path(out).write_text(_json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        _console.print("[green]Schedule written to " + out + "[/green]")


@ir_app.command("generate-sar")
def ir_generate_sar(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("", "--out", "-o", help="Write OSCAL SAR JSON to file."),
    system_name: str = typer.Option(
        "UIAO SCuBA Assessment System", "--system-name", "-s", help="System name for SAR metadata."
    ),
    ap_href: str = typer.Option("", "--ap-href", help="Optional href to Assessment Plan document."),
) -> None:
    """Generate an OSCAL Assessment Results (SAR) document from a SCuBA run.

    Example::

        uiao ir generate-sar examples/quickstart/scuba-normalized.json --out /tmp/sar.json
    """
    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.evidence.bundle import build_bundle_from_transform_result
    from uiao.generators.sar import build_sar, build_sar_summary, export_sar

    result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(result)
    tenant_id = result.evidence[0].data.get("tenant_id", "") if result.evidence else ""
    _console.print("[bold]Generating OSCAL SAR...[/bold]")
    if out:
        path = export_sar(bundle, out, system_name=system_name, tenant_id=tenant_id, ap_href=ap_href)
        _console.print("[green]SAR written to " + path + "[/green]")
    else:
        sar_doc = build_sar(bundle, system_name=system_name, tenant_id=tenant_id, ap_href=ap_href)
        _console.print(build_sar_summary(sar_doc))


@ir_app.command("orgtree-readiness-bundle")
def ir_orgtree_readiness_bundle(
    survey_json: str = typer.Argument(..., help="Path to survey JSON input file (AD forest survey output)."),
    out_dir: str = typer.Option(
        "exports/orgtree-readiness",
        "--out-dir",
        "-o",
        help=(
            "Output directory. Three files are written: bundle.json, bundle.hash, bundle.sig. "
            "HMAC key is read from env var UIAO_BUNDLE_HMAC_KEY. "
            "If the key is unset, the command exits non-zero unless --insecure-dev-key is passed."
        ),
    ),
    insecure_dev_key: bool = typer.Option(
        False,
        "--insecure-dev-key",
        help=(
            "Use the built-in development HMAC key when UIAO_BUNDLE_HMAC_KEY is not set. "
            "NEVER use in production — signatures produced with this key offer no security."
        ),
    ),
    oscal_out: str = typer.Option(
        "",
        "--oscal-out",
        help=(
            "If set, also emit OSCAL Assessment Results evidence via WS-A6 "
            "(uiao.oscal.orgtree_evidence.emit_orgtree_evidence) into this directory. "
            "Writes orgtree-evidence.json alongside the bundle artifacts."
        ),
    ),
) -> None:
    """Build a signed OrgTree Readiness evidence bundle from a survey JSON input.

    Reads ``survey_json``, assembles a bundle dict, validates it against the
    orgtree-readiness JSON Schema, computes a stable SHA-256 content hash and
    HMAC-SHA256 signature, then writes three artifacts to ``--out-dir``:

    * ``bundle.json``  — the full validated bundle (canonical JSON)
    * ``bundle.hash``  — hex SHA-256 of the canonical bundle
    * ``bundle.sig``   — hex HMAC-SHA256 of the canonical bundle

    When ``--oscal-out`` is given, the WS-A6 OSCAL emitter is also invoked and
    writes ``orgtree-evidence.json`` into the specified directory.

    The HMAC key is read from the ``UIAO_BUNDLE_HMAC_KEY`` environment variable.
    If the variable is not set and ``--insecure-dev-key`` is NOT passed, the
    command exits with code 1. Pass ``--insecure-dev-key`` for local dev/tests.

    Example::

        uiao ir orgtree-readiness-bundle survey.json --out-dir /tmp/orgtree-bundle
        uiao ir orgtree-readiness-bundle survey.json --out-dir /tmp/b --oscal-out /tmp/oscal
    """
    import hashlib as _hashlib
    import hmac as _hmac
    import json as _json
    import os as _os
    from datetime import datetime, timezone
    from importlib.resources import files as _res_files
    from pathlib import Path as _Path

    try:
        import jsonschema as _jsonschema

        _HAS_JSONSCHEMA = True
    except ImportError:
        _HAS_JSONSCHEMA = False

    # ------------------------------------------------------------------
    # 1. Load survey input
    # ------------------------------------------------------------------
    survey_path = _Path(survey_json)
    if not survey_path.exists():
        _console.print(f"[red]Survey file not found: {survey_json}[/red]")
        raise typer.Exit(code=1)

    raw_survey = survey_path.read_text(encoding="utf-8")
    try:
        survey_data = _json.loads(raw_survey)
    except _json.JSONDecodeError as exc:
        _console.print(f"[red]Failed to parse survey JSON: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    # Stable hash of survey input
    survey_canonical = _json.dumps(survey_data, sort_keys=True, separators=(",", ":"))
    source_hash = _hashlib.sha256(survey_canonical.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # 2. Extract survey sections (graceful fallback when absent)
    # ------------------------------------------------------------------
    users = survey_data.get("users", [])
    groups = survey_data.get("groups", [])
    computers = survey_data.get("computers", [])
    servers = survey_data.get("servers", [])
    findings_raw = survey_data.get("findings", [])

    # ------------------------------------------------------------------
    # 3. Build readiness plans (lazy import; stub on ImportError)
    # ------------------------------------------------------------------
    orgpath_plan: dict = {}
    intune_plan: dict = {}
    arc_plan: dict = {}

    try:
        from uiao.adapters.modernization.active_directory.orgpath import (  # type: ignore[attr-defined]
            build_orgpath_plan,
        )

        orgpath_plan = build_orgpath_plan(survey_data)  # type: ignore[no-untyped-call]
    except (ImportError, AttributeError):
        # orgpath plan helper not yet available — stub
        orgpath_plan = {
            "total_users": len(users),
            "resolved_count": 0,
            "unresolved_count": len(users),
            "coverage_pct": 0.0,
        }

    try:
        from uiao.adapters.modernization.active_directory.intune_readiness import (  # type: ignore[attr-defined]
            build_intune_plan,
        )

        intune_plan = build_intune_plan(survey_data)  # type: ignore[no-untyped-call]
    except (ImportError, AttributeError):
        intune_plan = {
            "total_computers": len(computers),
            "enroll_ready_count": 0,
            "enroll_blocked_count": len(computers),
            "readiness_pct": 0.0,
        }

    try:
        from uiao.adapters.modernization.active_directory.arc_readiness import (  # type: ignore[attr-defined]
            build_arc_plan,
        )

        arc_plan = build_arc_plan(survey_data)  # type: ignore[no-untyped-call]
    except (ImportError, AttributeError):
        arc_plan = {
            "total_servers": len(servers),
            "onboard_ready_count": 0,
            "onboard_blocked_count": len(servers),
            "readiness_pct": 0.0,
        }

    # ------------------------------------------------------------------
    # 4. HMAC key from env var — fail closed (Phase 1.5 fix #3)
    # ------------------------------------------------------------------
    _HMAC_DEFAULT = "uiao-dev-hmac-key-not-for-production"  # noqa: S105
    hmac_key_raw = _os.environ.get("UIAO_BUNDLE_HMAC_KEY", "")
    if not hmac_key_raw:
        if insecure_dev_key:
            # Explicit opt-in for local dev / CI tests.
            _console.print(
                "[yellow]WARNING: --insecure-dev-key is set — using built-in dev HMAC key. "
                "Do NOT use this in production.[/yellow]"
            )
            hmac_key_raw = _HMAC_DEFAULT
        else:
            _console.print(
                "[red]ERROR: UIAO_BUNDLE_HMAC_KEY environment variable is not set. "
                "Set the variable or pass --insecure-dev-key for local/test use.[/red]"
            )
            raise typer.Exit(code=1)
    hmac_key = hmac_key_raw.encode("utf-8")

    # ------------------------------------------------------------------
    # 5. Assemble bundle (without signature — sign content only)
    # ------------------------------------------------------------------
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    bundle: dict = {
        "version": "0.6.0",
        "generated_at": generated_at,
        "users": users,
        "groups": groups,
        "computers": computers,
        "servers": servers,
        "orgpath_plan": orgpath_plan,
        "intune_plan": intune_plan,
        "arc_plan": arc_plan,
        "findings": findings_raw,
        "provenance": {
            "schema_id": "https://uiao.gov/schemas/orgtree-readiness/orgtree-readiness.schema.json",
            "schema_version": "0.6.0",
            "canon_refs": ["UIAO_AD_001"],
            "source_hash": source_hash,
            "signature": "0" * 64,  # placeholder; replaced below
            "hmac_alg": "hmac-sha256",
        },
    }

    # Compute content hash over bundle without final signature
    canonical_bundle = _json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    content_hash = _hashlib.sha256(canonical_bundle.encode("utf-8")).hexdigest()

    # Compute HMAC-SHA256 over canonical bundle bytes
    sig = _hmac.new(hmac_key, canonical_bundle.encode("utf-8"), _hashlib.sha256).hexdigest()

    # Stamp real signature into provenance
    bundle["provenance"]["signature"] = sig

    # ------------------------------------------------------------------
    # 6. Schema validation
    # ------------------------------------------------------------------
    schema_bytes = (
        _res_files("uiao.schemas")
        .joinpath("orgtree-readiness")
        .joinpath("orgtree-readiness.schema.json")
        .read_text()
    )
    schema = _json.loads(schema_bytes)

    if _HAS_JSONSCHEMA:
        try:
            _jsonschema.validate(instance=bundle, schema=schema)
        except _jsonschema.ValidationError as exc:
            _console.print(f"[red]Bundle failed schema validation: {exc.message}[/red]")
            raise typer.Exit(code=1) from exc
    else:
        _console.print("[yellow]jsonschema not installed — skipping schema validation[/yellow]")

    # ------------------------------------------------------------------
    # 7. Write artifacts
    # ------------------------------------------------------------------
    out_path = _Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    final_json = _json.dumps(bundle, indent=2, ensure_ascii=False)
    (out_path / "bundle.json").write_text(final_json, encoding="utf-8")
    (out_path / "bundle.hash").write_text(content_hash, encoding="utf-8")
    (out_path / "bundle.sig").write_text(sig, encoding="utf-8")

    _console.print(f"[bold]OrgTree Readiness bundle written to {out_dir}[/bold]")
    _console.print(f"  Users      : {len(users)}")
    _console.print(f"  Groups     : {len(groups)}")
    _console.print(f"  Computers  : {len(computers)}")
    _console.print(f"  Servers    : {len(servers)}")
    _console.print(f"  Findings   : {len(findings_raw)}")
    _console.print(f"  Hash       : {content_hash[:16]}...")
    _console.print(f"  Sig        : {sig[:16]}...")

    # ------------------------------------------------------------------
    # 8. Optionally emit OSCAL evidence (WS-A6 integration — Phase 2 task 4)
    # ------------------------------------------------------------------
    if oscal_out:
        try:
            from uiao.oscal.orgtree_evidence import emit_orgtree_evidence  # noqa: PLC0415

            oscal_path = emit_orgtree_evidence(bundle, oscal_out)
            _console.print(f"[green]OSCAL evidence written to {oscal_path}[/green]")
        except Exception as exc:  # noqa: BLE001
            _console.print(f"[red]OSCAL emission failed: {exc}[/red]")
            raise typer.Exit(code=1) from exc


@ir_app.command("ssp-inject")
def ir_ssp_inject(
    normalized_json: str = typer.Argument(..., help="Path to normalized SCuBA JSON file."),
    out: str = typer.Option("exports/oscal/uiao-ssp-live.json", "--out", "-o", help="Output SSP JSON path."),
    canon_path: str = typer.Option("", "--canon", "-c", help="Canon YAML path (default: settings)."),
    data_dir: str = typer.Option("", "--data-dir", "-d", help="Data YAML directory (default: settings)."),
    enhanced: bool = typer.Option(False, "--enhanced/--no-enhanced", help="Also inject control-library narratives."),
) -> None:
    """Inject live SCuBA evidence into OSCAL SSP, writing uiao-ssp-live.json.

    Combines the canon SSP baseline with real SCuBA assessment evidence,
    producing an OSCAL SSP whose implemented-requirements carry live
    implementation-status props and evidence-hash annotations.

    Example::

        uiao ir ssp-inject examples/quickstart/scuba-normalized.json --out /tmp/uiao-ssp-live.json
    """
    import json as _json
    from pathlib import Path as _Path

    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir
    from uiao.evidence.bundle import build_bundle_from_transform_result
    from uiao.generators.ssp_inject import build_live_ssp, live_ssp_summary

    kw = {}
    if canon_path:
        kw["canon_path"] = canon_path
    if data_dir:
        kw["data_dir"] = data_dir
    _console.print(f"[bold]Injecting SCuBA evidence into SSP: {normalized_json}...[/bold]")
    path = build_live_ssp(normalized_json_path=normalized_json, output_path=out, enhanced=enhanced, **kw)
    ssp_doc = _json.loads(_Path(out).read_text(encoding="utf-8"))
    ir_result = transform_scuba_to_ir(normalized_json)
    bundle = build_bundle_from_transform_result(ir_result)
    _console.print(live_ssp_summary(ssp_doc, bundle))
    _console.print(f"[green]Live SSP written to {path}[/green]")
