"""uiao.cli.oscal — Typer sub-app for the `uiao oscal` command group.

Mount point
-----------
    # in uiao/impl/cli/app.py
    from uiao.cli.oscal import oscal_app
    app.add_typer(oscal_app, name="oscal")

Usage (after `pip install -e .`)
---------------------------------
    uiao oscal generate \\
        --evidence ./output/evidence/tenant-a/ \\
        --output   ./output/artifacts/tenant-a/ \\
        --config   ./config/oscal-generate.json

Or via module invocation:
    python -m uiao.cli oscal generate \\
        --evidence ./output/evidence/tenant-a/ \\
        --output   ./output/artifacts/tenant-a/
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

oscal_app = typer.Typer(
    name="oscal",
    help="OSCAL artifact generation operations.",
    add_completion=False,
)

_console = Console()


@oscal_app.command("generate")
def generate_command(
    evidence: str = typer.Option(  # noqa: B008
        ...,
        "--evidence",
        help=(
            "Path to the evidence bundle directory produced by Plane 3 (must contain bundle.json and evidence.jsonl)."
        ),
        show_default=False,
    ),
    output: str = typer.Option(  # noqa: B008
        ...,
        "--output",
        help=("Destination directory for OSCAL artifacts (e.g. ./output/artifacts/tenant-a/).  Created automatically."),
        show_default=False,
    ),
    config: str | None = typer.Option(  # noqa: B008
        None,
        "--config",
        help="Optional path to oscal-generate.json config file.",
        show_default=False,
    ),
) -> None:
    """Generate OSCAL artifacts (POA&M + SSP) from a Plane 3 evidence bundle.

    This command is the CLI surface for Plane 4 of the UIAO pipeline.
    It is a thin wrapper around
    `uiao.oscal.generator.generate_oscal`, which is kept
    intentionally pure (no CLI, no side-effects beyond artifact I/O).

    \\b
    Output layout
    -------------
    The artifact directory will contain:

        <output>/poam.json            — OSCAL-aligned POA&M (not-satisfied controls)
        <output>/ssp.json             — OSCAL-aligned SSP implemented-requirements
        <output>/artifact-index.json  — machine-readable manifest + hashes

    \\b
    Examples
    --------
    Minimal (no config):

        uiao oscal generate \\
            --evidence ./output/evidence/tenant-a/ \\
            --output   ./output/artifacts/tenant-a/

    With config:

        uiao oscal generate \\
            --evidence ./output/evidence/tenant-a/ \\
            --output   ./output/artifacts/tenant-a/ \\
            --config   ./config/oscal-generate.json
    """
    from uiao.oscal.generator import generate_oscal

    try:
        generate_oscal(
            evidence_dir=evidence,
            output_dir=output,
            config_path=config,
        )
    except FileNotFoundError as exc:
        _console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        _console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@oscal_app.command("ksi-ar")
def ksi_ar_command(
    output: str = typer.Option(  # noqa: B008
        "output/artifacts/ksi-ar.json",
        "--output",
        "-o",
        help="Destination path for the KSI OSCAL Assessment Results JSON.",
    ),
    system_name: str = typer.Option(  # noqa: B008
        "UIAO Federal AAN Assessment System",
        "--system-name",
        help="Human-readable name for the assessed system.",
    ),
    ap_href: str = typer.Option(  # noqa: B008
        "",
        "--ap-href",
        help="Optional href to an existing Assessment Plan (OSCAL import-ap).",
    ),
    slots_dir: str | None = typer.Option(  # noqa: B008
        None,
        "--slots-dir",
        help=("Path to the AAN slot evidence YAML directory. Defaults to the bundled fedramp_aan_catalog/mappings/."),
    ),
    scuba_verdicts: str | None = typer.Option(  # noqa: B008
        None,
        "--scuba-verdicts",
        help=(
            "Path to the ScubaDrift verdicts artifact backing ScuBA-sourced rules "
            "(KSI-001..010). Defaults to output/artifacts/ksi-bundle/scubadrift-verdicts.json; "
            "when absent those rules are reported not-evaluated."
        ),
    ),
) -> None:
    """Generate an OSCAL Assessment Results document from KSI slot evidence.

    Reads ksi-mapping.yaml and all AAN slot evidence YAML files (slot-01..06)
    and emits an OSCAL AR with per-KSI satisfied / not-satisfied / not-evaluated
    verdicts based on mapping confidence and slot binding coverage.

    \\b
    Output
    ------
    A single OSCAL 1.0.4 Assessment Results JSON file at --output.

    \\b
    Examples
    --------
        uiao oscal ksi-ar

        uiao oscal ksi-ar --output exports/oscal/ksi-ar.json

        uiao oscal ksi-ar \\
            --output exports/oscal/ksi-ar.json \\
            --system-name "SSA GCC Moderate" \\
            --ap-href "#assessment-plan-uuid"
    """
    from pathlib import Path as _Path

    from uiao.oscal.ksi_ar import build_ksi_ar_summary, export_ksi_ar

    try:
        resolved_slots = _Path(slots_dir) if slots_dir else None
        path = export_ksi_ar(
            output_path=output,
            system_name=system_name,
            ap_href=ap_href,
            slots_dir=resolved_slots,
            scuba_verdicts_path=_Path(scuba_verdicts) if scuba_verdicts else None,
        )
        import json

        ar_doc = json.loads(_Path(path).read_text(encoding="utf-8"))
        _console.print(f"[green]Wrote KSI Assessment Results to {path}[/green]")
        _console.print(build_ksi_ar_summary(ar_doc))
    except FileNotFoundError as exc:
        _console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        _console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@oscal_app.command("ksi-ap")
def ksi_ap_command(
    output: str = typer.Option(  # noqa: B008
        "output/artifacts/ksi-ap.json",
        "--output",
        "-o",
        help="Destination path for the KSI OSCAL Assessment Plan JSON.",
    ),
    system_name: str = typer.Option(  # noqa: B008
        "UIAO Federal AAN Assessment System",
        "--system-name",
        help="Human-readable name for the assessed system.",
    ),
    ssp_href: str = typer.Option(  # noqa: B008
        "",
        "--ssp-href",
        help="Optional href to an existing System Security Plan (OSCAL import-ssp).",
    ),
) -> None:
    """Generate an OSCAL Assessment Plan document for the KSI corpus.

    Reads ksi-mapping.yaml and produces an OSCAL AP describing what will be
    assessed, how, and when for all KSI themes.  The AP UUID in the output
    file can be passed as --ap-href to uiao oscal ksi-ar.

    \\b
    Output
    ------
    A single OSCAL 1.0.4 Assessment Plan JSON file at --output.

    \\b
    Examples
    --------
        uiao oscal ksi-ap

        uiao oscal ksi-ap --output exports/oscal/ksi-ap.json
    """
    from uiao.oscal.ksi_ap import build_ksi_ap_summary, export_ksi_ap

    try:
        path = export_ksi_ap(
            output_path=output,
            system_name=system_name,
            ssp_href=ssp_href,
        )
        import json

        ap_doc = json.loads(Path(path).read_text(encoding="utf-8"))
        _console.print(f"[green]Wrote KSI Assessment Plan to {path}[/green]")
        _console.print(build_ksi_ap_summary(ap_doc))
    except FileNotFoundError as exc:
        _console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        _console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@oscal_app.command("ksi-poam")
def ksi_poam_command(
    output: str = typer.Option(  # noqa: B008
        "output/artifacts/ksi-poam.json",
        "--output",
        "-o",
        help="Destination path for the KSI OSCAL POA&M JSON.",
    ),
    system_name: str = typer.Option(  # noqa: B008
        "UIAO Federal AAN Assessment System",
        "--system-name",
        help="Human-readable name for the assessed system.",
    ),
    ap_href: str = typer.Option(  # noqa: B008
        "",
        "--ap-href",
        help="Optional href to an existing Assessment Plan (OSCAL import-ap).",
    ),
    ar_href: str = typer.Option(  # noqa: B008
        "",
        "--ar-href",
        help="Optional href to the Assessment Results document (back-matter reference).",
    ),
    ar_path: str | None = typer.Option(  # noqa: B008
        None,
        "--ar-path",
        help="Path to an existing KSI AR JSON file to read gaps from. Defaults to regenerating the AR from bundled data.",
    ),
    slots_dir: str | None = typer.Option(  # noqa: B008
        None,
        "--slots-dir",
        help="Path to the AAN slot evidence YAML directory.",
    ),
) -> None:
    """Generate an OSCAL POA&M from KSI Assessment Results gap findings.

    Reads the AR (either from --ar-path or regenerated from bundled data) and
    produces an OSCAL POA&M with one item per not-satisfied or not-evaluated
    KSI finding.  BOD 26-04 deadline (2026-12-07) is set as the milestone for
    KSI-CMT and KSI-SCR items.

    \\b
    Output
    ------
    A single OSCAL 1.0.4 POA&M JSON file at --output.

    \\b
    Examples
    --------
        uiao oscal ksi-poam

        uiao oscal ksi-poam --ar-path exports/oscal/ksi-ar.json \\
            --output exports/oscal/ksi-poam.json
    """
    from uiao.oscal.ksi_poam import build_ksi_poam_summary, export_ksi_poam

    try:
        ar_doc = None
        if ar_path:
            import json

            ar_doc = json.loads(Path(ar_path).read_text(encoding="utf-8"))
        resolved_slots = Path(slots_dir) if slots_dir else None
        path = export_ksi_poam(
            output_path=output,
            system_name=system_name,
            ap_href=ap_href,
            ar_href=ar_href,
            ar_doc=ar_doc,
            slots_dir=resolved_slots,
        )
        import json

        poam_doc = json.loads(Path(path).read_text(encoding="utf-8"))
        _console.print(f"[green]Wrote KSI POA&M to {path}[/green]")
        _console.print(build_ksi_poam_summary(poam_doc))
    except FileNotFoundError as exc:
        _console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        _console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@oscal_app.command("scuba-verdicts")
def scuba_verdicts_command(
    results: str = typer.Option(  # noqa: B008
        ...,
        "--results",
        help="ScubaGear results JSON (flat or full ScubaResults.json shape).",
    ),
    triage: str = typer.Option(  # noqa: B008
        ...,
        "--triage",
        help="Output of 'scubadrift triage --json' for the same ScubaGear run.",
    ),
    output: str = typer.Option(  # noqa: B008
        "output/artifacts/ksi-bundle/scubadrift-verdicts.json",
        "--output",
        "-o",
        help="Destination path for the verdicts artifact.",
    ),
    provenance_source: str = typer.Option(  # noqa: B008
        "tenant",
        "--provenance-source",
        help="'tenant' for a real ScubaGear run, 'sample-fixture' for demonstration data.",
    ),
    provenance_note: str = typer.Option(  # noqa: B008
        "",
        "--provenance-note",
        help="Free-text provenance detail recorded in the artifact.",
    ),
) -> None:
    """Build the ScubaDrift verdicts artifact backing KSI-001..010.

    Merges a ScubaGear results file with the ScubaDrift triage report for the
    same run into a single per-policy verdict artifact. The KSI OSCAL AR
    (ksi-ar / bundle) consumes it to evaluate the ScuBA-sourced rules:
    pass or governed exception -> satisfied; new drift or lapsed
    risk-acceptance -> not-satisfied.

    \\b
    Examples
    --------
        scubadrift triage --results ScubaResults.json \\
            --exceptions exceptions.yaml --json > triage.json

        uiao oscal scuba-verdicts \\
            --results ScubaResults.json --triage triage.json
    """
    import json

    from uiao.ksi.scuba_verdicts import export_scuba_verdicts

    try:
        path = export_scuba_verdicts(
            output_path=output,
            results_path=results,
            triage_path=triage,
            provenance_source=provenance_source,
            provenance_note=provenance_note,
        )
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        _console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    policies = doc.get("policies", {})
    failing = {p: r for p, r in policies.items() if r.get("result") != "pass"}
    _console.print(f"[green]Wrote ScubaDrift verdicts artifact to {path}[/green]")
    _console.print(
        f"  policies: {len(policies)} | failing: {len(failing)} | "
        f"as-of: {doc.get('as_of', '?')} | provenance: {doc.get('provenance', {}).get('source', '?')}"
    )


@oscal_app.command("bundle")
def bundle_command(
    output_dir: str = typer.Option(  # noqa: B008
        "output/artifacts/ksi-bundle",
        "--output-dir",
        "-o",
        help="Directory to write the AP, AR, POA&M, and artifact index.",
    ),
    system_name: str = typer.Option(  # noqa: B008
        "UIAO Federal AAN Assessment System",
        "--system-name",
        help="Human-readable name for the assessed system.",
    ),
    ssp_href: str = typer.Option(  # noqa: B008
        "",
        "--ssp-href",
        help="Optional href to an existing System Security Plan.",
    ),
    slots_dir: str | None = typer.Option(  # noqa: B008
        None,
        "--slots-dir",
        help="Path to the AAN slot evidence YAML directory.",
    ),
) -> None:
    """Generate the full OSCAL AP+AR+POA&M bundle in one command.

    Produces an OSCAL Assessment Plan, Assessment Results, and POA&M as a
    linked package, plus an artifact-index.json manifest.  The AP href is
    wired into the AR import-ap; the AR href is wired into the POA&M
    back-matter.

    \\b
    Output layout
    -------------
    <output-dir>/
        ksi-ap.json          — OSCAL Assessment Plan
        ksi-ar.json          — OSCAL Assessment Results
        ksi-poam.json        — OSCAL Plan of Action & Milestones
        artifact-index.json  — machine-readable manifest

    \\b
    Examples
    --------
        uiao oscal bundle

        uiao oscal bundle \\
            --output-dir exports/oscal \\
            --system-name "SSA GCC Moderate"
    """
    import hashlib
    import json
    from datetime import datetime, timezone

    from uiao.oscal.ksi_ap import build_ksi_ap, build_ksi_ap_summary
    from uiao.oscal.ksi_ar import build_ksi_ar, build_ksi_ar_summary
    from uiao.oscal.ksi_poam import build_ksi_poam, build_ksi_poam_summary

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    resolved_slots = Path(slots_dir) if slots_dir else None

    # 1. Build AP.
    _console.print("[bold]Step 1/4:[/bold] Generating Assessment Plan…")
    ap_path = out / "ksi-ap.json"
    ap_doc = build_ksi_ap(system_name=system_name, ssp_href=ssp_href, now=now)
    ap_path.write_text(json.dumps(ap_doc, indent=2), encoding="utf-8")
    ap_uuid = ap_doc["assessment-plan"]["uuid"]
    _console.print(f"  [green]✓[/green] {ap_path}")
    _console.print(f"  {build_ksi_ap_summary(ap_doc)}")

    # 2. Build AR, linking import-ap to the AP UUID. The ScubaDrift verdicts
    # artifact (if present in the bundle dir) backs the ScuBA-sourced rules.
    _console.print("[bold]Step 2/4:[/bold] Generating Assessment Results…")
    ar_path = out / "ksi-ar.json"
    scuba_verdicts_path = out / "scubadrift-verdicts.json"
    ar_doc = build_ksi_ar(
        system_name=system_name,
        ap_href=f"#{ap_uuid}",
        now=now,
        slots_dir=resolved_slots,
        scuba_verdicts_path=scuba_verdicts_path,
    )
    ar_path.write_text(json.dumps(ar_doc, indent=2), encoding="utf-8")
    _console.print(f"  [green]✓[/green] {ar_path}")
    _console.print(f"  {build_ksi_ar_summary(ar_doc)}")

    # 3. Build POA&M from the AR.
    _console.print("[bold]Step 3/4:[/bold] Generating POA&M…")
    poam_path = out / "ksi-poam.json"
    poam_doc = build_ksi_poam(
        ar_doc=ar_doc,
        system_name=system_name,
        ap_href=f"#{ap_uuid}",
        ar_href=ar_path.as_posix(),
        now=now,
    )
    poam_path.write_text(json.dumps(poam_doc, indent=2), encoding="utf-8")
    _console.print(f"  [green]✓[/green] {poam_path}")
    _console.print(f"  {build_ksi_poam_summary(poam_doc)}")

    # 4. Write artifact index.
    _console.print("[bold]Step 4/4:[/bold] Writing artifact index…")
    index_path = out / "artifact-index.json"
    artifacts = []
    indexed: list[tuple[Path, str]] = [
        (ap_path, "assessment-plan"),
        (ar_path, "assessment-results"),
        (poam_path, "plan-of-action-and-milestones"),
    ]
    if scuba_verdicts_path.is_file():
        indexed.append((scuba_verdicts_path, "scuba-verdicts"))
    for artifact_path, doc_type in indexed:
        content = artifact_path.read_bytes()
        artifacts.append(
            {
                "path": artifact_path.as_posix(),
                "type": doc_type,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
                "generated_at": now,
            }
        )
    index = {
        "bundle_version": "0.1.0",
        "system_name": system_name,
        "generated_at": now,
        "artifacts": artifacts,
    }
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    _console.print(f"  [green]✓[/green] {index_path}")

    _console.print(f"[green bold]Bundle complete:[/green bold] {output_dir} ({len(artifacts)} artifacts)")


@oscal_app.command("validate")
def validate(
    path: str = typer.Argument(..., help="Path to OSCAL JSON file."),
) -> None:
    """Validate an OSCAL document against its schema.

    Example::

        uiao oscal validate exports/oscal/uiao-ssp.json
    """
    _console.print(f"[bold]Validating {path}...[/bold]")
    _console.print("[red]OSCAL validate is not implemented yet.[/red]")
    raise typer.Exit(code=2)


@oscal_app.command("validate-ssp")
def validate_ssp(
    oscal_dir: str = typer.Option(
        "exports/oscal",
        "--oscal-dir",
        "-d",
        help="Directory containing OSCAL JSON artifacts.",
    ),
) -> None:
    """Validate OSCAL artifacts with compliance-trestle Pydantic models.

    Example::

        uiao oscal validate-ssp --oscal-dir exports/oscal
    """
    from uiao.generators.trestle import validate_oscal_artifacts

    _console.print(f"[bold]Validating OSCAL artifacts in {oscal_dir}...[/bold]")
    failures = validate_oscal_artifacts(Path(oscal_dir))
    if failures:
        _console.print(f"[red]{failures} validation failure(s)[/red]")
        raise typer.Exit(code=1)
    _console.print("[green]All artifacts passed validation.[/green]")
