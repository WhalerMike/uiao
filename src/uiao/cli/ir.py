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
    """Transform normalized SCuBA JSON -> IR Evidence objects and print summary."""
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
    """Build a canonical EvidenceBundle from a SCuBA transform and print summary."""
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
    """Export POA&M rows (FAIL + WARN only) from a SCuBA run and print summary."""
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
    """Detect drift between two IR state JSON files and print classification."""
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
    """Run full governance pipeline: SCuBA -> IR -> Evidence -> Actions -> Report."""
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
    """Generate SSP narrative + lineage from SCuBA -> IR -> Evidence -> Governance."""
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
    """Run full pipeline and write all auditor artifacts to a directory."""
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
    """Diff two SCuBA runs: KSI changes, evidence hash deltas, status changes."""
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
    """Validate a normalized SCuBA JSON file for IR pipeline conformance."""
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
    """Compute evidence freshness and generate refresh actions for stale evidence."""
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
    """Build IR governance dashboard: evidence freshness + governance action summary."""
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
    """Build a refresh job schedule from stale evidence and print the schedule summary."""
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
    """Generate an OSCAL Assessment Results (SAR) document from a SCuBA run."""
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
