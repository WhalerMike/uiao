"""LocPath CLI: ``uiao locpath ...`` subcommands.

Operator-reachable surface for the LocPath substrate (ADR-102 / UIAO_194)
— the physical-place counterpart to ``uiao orgtree``. Thin Typer verbs
over the loader/assignment/drift/exposure functions in
:mod:`uiao.modernization.locpath`; every command is **read-only and
dry-run by nature** (ADR-102 §D6/§D7 — UIAO governs and reconciles
location data, it never writes to facilities, network, or 911 systems).

Commands, mapped to the ADR-102 §D6 implementation phases:

- ``validate registry`` / ``validate duty-station-map`` — phase 1: load +
  schema/integrity-validate the executable canon (or an agency file).
- ``assign`` — phase 2: resolve an HR-record export through the
  duty-station map into Primary-LocPath assignments + drift findings.
- ``mover`` — phase 3: diff two HR snapshots (previous vs current) into
  join/leave/move events with their stale impact surfaces.
- ``policy-drift`` — phase 3: classify an observed-site-state export
  against governed site classification (DIA / SD-WAN / telemetry).
- ``e911-check`` — ADR-104: find governed locations whose dispatchable
  location is incomplete (47 CFR § 9.16).
- ``expose groups`` / ``expose admin-units`` — phase 4: plan one Entra
  group / Administrative Unit per governed Site from an assignment pass.

Canon: ADR-102, ADR-104, UIAO_194. Boundary: Moderate/Commercial only.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from uiao.adapters.modernization.hrit.inventory import DriftFinding, HRRecord
from uiao.modernization.locpath.drift import ObservedSiteState, detect_location_policy_drift
from uiao.modernization.locpath.e911_compliance import detect_e911_completeness_gaps
from uiao.modernization.locpath.entra_exposure import (
    LocPathExposureError,
    plan_locpath_admin_units,
    plan_locpath_site_groups,
)
from uiao.modernization.locpath.hr_assign import (
    DutyStationMapValidationError,
    LocPathAssignmentPlan,
    assign_locpaths,
    load_duty_station_map,
    load_duty_station_map_from_path,
)
from uiao.modernization.locpath.mover import plan_location_moves
from uiao.modernization.locpath.registry import (
    LocationRegistry,
    LocationRegistryValidationError,
    load_location_registry,
    load_location_registry_from_path,
)

locpath_app = typer.Typer(
    name="locpath",
    help=(
        "LocPath physical-location governance (validate, assign, mover, "
        "policy-drift, e911-check, expose). Read-only. Canon: ADR-102 / "
        "UIAO_194. Boundary: Moderate/Commercial only."
    ),
    no_args_is_help=True,
)

validate_app = typer.Typer(
    name="validate",
    help="Validate a LocPath canon artifact against its schema and integrity rules.",
    no_args_is_help=True,
)
locpath_app.add_typer(validate_app, name="validate")

expose_app = typer.Typer(
    name="expose",
    help="Plan Entra exposure (site groups / Administrative Units) from an assignment pass. Plan-only — no Graph I/O.",
    no_args_is_help=True,
)
locpath_app.add_typer(expose_app, name="expose")

console = Console()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_SEVERITY_COLOR = {"P1": "red", "P2": "yellow", "P3": "cyan", "P4": "dim"}


def _fail(message: str) -> typer.Exit:
    """Print a red error and return an Exit(1) the caller raises."""
    console.print(f"[red]{message}[/red]")
    return typer.Exit(code=1)


def _load_json(path: Path, label: str) -> object:
    """Read + parse a JSON export, exiting 1 with a clear message on failure."""
    if not path.exists():
        raise _fail(f"{label} not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise _fail(f"Invalid {label} JSON: {exc}") from exc


def _rows(payload: object, label: str) -> list[dict]:
    """Normalize a JSON export into a list of dict rows.

    Accepts a bare list, or an object wrapping the rows under ``records``
    / ``value`` / ``assignments`` (the Graph/ARM ``{"value": [...]}``
    convention and the shapes this CLI itself writes).
    """
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        wrapped = payload.get("records") or payload.get("value") or payload.get("assignments") or []
        rows = wrapped if isinstance(wrapped, list) else []
    else:
        raise _fail(f"{label} must be a JSON list or an object wrapping a list.")
    if not all(isinstance(r, dict) for r in rows):
        raise _fail(f"{label} must contain JSON objects.")
    return list(rows)


def _get(raw: dict, *keys: str, default: str = "") -> str:
    """First non-null value among ``keys`` (snake_case or camelCase), as str."""
    for key in keys:
        value = raw.get(key)
        if value is not None:
            return str(value)
    return default


def _hr_record_from_dict(raw: dict) -> HRRecord:
    """Build an HRRecord from a canonical (camelCase) or snake_case row.

    Only ``employee_id`` / ``location_code`` (+ provenance) are
    load-bearing for assignment; the remaining Spec2-D1.1 required fields
    default to empty so partial HR exports still resolve a Primary LocPath.
    """
    return HRRecord(
        employee_id=_get(raw, "employee_id", "employeeId"),
        first_name=_get(raw, "first_name", "firstName"),
        last_name=_get(raw, "last_name", "lastName"),
        department=_get(raw, "department"),
        hire_date=_get(raw, "hire_date", "hireDate"),
        worker_type=_get(raw, "worker_type", "workerType"),
        location_code=_get(raw, "location_code", "locationCode"),
        country=_get(raw, "country"),
        employment_status=_get(raw, "employment_status", "employmentStatus"),
        extracted_at=_get(raw, "extracted_at", "extractedAt"),
        division=raw.get("division"),
        organization_code=raw.get("organization_code") or raw.get("organizationCode"),
        cost_center=raw.get("cost_center") or raw.get("costCenter"),
        job_title=raw.get("job_title") or raw.get("jobTitle"),
        manager_employee_id=raw.get("manager_employee_id") or raw.get("managerEmployeeId"),
        adapter_metadata=dict(raw.get("adapter_metadata") or raw.get("adapterMetadata") or {}),
    )


def _hr_records_from_export(path: Path, label: str = "HR export") -> list[HRRecord]:
    """Load HR records from a JSON export into HRRecord objects."""
    records = [_hr_record_from_dict(row) for row in _rows(_load_json(path, label), label)]
    if not records:
        raise _fail(f"{label} contained no HR records.")
    return records


def _load_registry(registry_path: Path | None) -> LocationRegistry:
    """The canonical reference registry, or an agency registry from a path."""
    try:
        if registry_path is not None:
            return load_location_registry_from_path(registry_path)
        return load_location_registry()
    except LocationRegistryValidationError as exc:
        raise _fail(f"Location registry invalid: {exc}") from exc


def _write_out(out: Path | None, payload: object, label: str) -> None:
    """Write ``payload`` as pretty JSON to ``out`` (mkdir -p), if requested."""
    if out is None:
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"[green]{label} written to {out}[/green]")


def _print_findings(findings: tuple[DriftFinding, ...]) -> dict[str, int]:
    """Render findings as a table; return a severity -> count rollup."""
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    if not findings:
        return counts
    table = Table(show_header=True, header_style="bold")
    table.add_column("Class")
    table.add_column("Sev")
    table.add_column("Code")
    table.add_column("Path")
    table.add_column("Detail", overflow="fold")
    for finding in findings:
        color = _SEVERITY_COLOR.get(finding.severity, "white")
        table.add_row(
            finding.drift_class,
            f"[{color}]{finding.severity}[/{color}]",
            finding.error_code,
            finding.path,
            finding.detail,
        )
    console.print(table)
    return counts


def _finding_dicts(findings: tuple[DriftFinding, ...]) -> list[dict]:
    return [asdict(f) for f in findings]


# ---------------------------------------------------------------------------
# Phase 1 — validate executable canon
# ---------------------------------------------------------------------------

_REGISTRY_OPT = typer.Option(
    None,
    "--registry",
    "-r",
    help="Path to an agency location registry YAML. Defaults to the canonical reference registry (UIAO_194).",
)
_MAP_OPT = typer.Option(
    None,
    "--map",
    "-m",
    help="Path to an agency duty-station map YAML. Defaults to the canonical reference map (UIAO_194).",
)


@validate_app.command("registry")
def validate_registry(registry: Path | None = _REGISTRY_OPT) -> None:
    """Validate a LocPath location registry (UIAO_194, ADR-102 §D6 phase 1).

    Loads the registry (canonical reference, or an agency file via
    --registry), validating the envelope + every node against the JSON
    Schemas and the integrity rules schema cannot express (level/depth
    consistency, case-insensitive path uniqueness, parent existence,
    UUID/timestamp parseability).

    Example::

        uiao locpath validate registry
        uiao locpath validate registry --registry agency-locations.yaml
    """
    reg = _load_registry(registry)
    console.print(
        f"[green]PASS[/green] location registry '{reg.registry_id}' (schema {reg.schema_version}) — "
        f"{len(reg.nodes)} node(s), {len(reg.sites())} Site(s); status={reg.status}"
    )


@validate_app.command("duty-station-map")
def validate_duty_station_map(
    duty_station_map: Path | None = _MAP_OPT,
    registry: Path | None = _REGISTRY_OPT,
) -> None:
    """Validate a duty-station map against its paired registry (phase 1/2).

    The map's every ``locationCode`` must resolve in the registry at Site
    level or deeper (ADR-102 §D1). With --registry the map is validated
    against an agency registry instead of the canonical reference.

    Example::

        uiao locpath validate duty-station-map
        uiao locpath validate duty-station-map --map agency-map.yaml --registry agency-locations.yaml
    """
    reg = _load_registry(registry)
    try:
        if duty_station_map is not None:
            dmap = load_duty_station_map_from_path(duty_station_map, reg)
        else:
            # The canonical map pairs with the canonical registry; --registry
            # only takes effect when an agency --map is supplied alongside it.
            dmap = load_duty_station_map()
    except DutyStationMapValidationError as exc:
        raise _fail(f"Duty-station map invalid: {exc}") from exc
    console.print(
        f"[green]PASS[/green] duty-station map '{dmap.map_id}' (schema {dmap.schema_version}) — "
        f"{len(dmap.entries)} entry(ies) against registry '{reg.registry_id}'; status={dmap.status}"
    )


# ---------------------------------------------------------------------------
# Phase 2 — HR duty-station -> Primary LocPath assignment
# ---------------------------------------------------------------------------


def _build_plan(
    export: Path,
    registry: Path | None,
    duty_station_map: Path | None,
    label: str,
) -> LocPathAssignmentPlan:
    """Run one assignment pass over an HR export, with optional canon overrides."""
    records = _hr_records_from_export(export, label)
    reg = _load_registry(registry)
    try:
        dmap = load_duty_station_map_from_path(duty_station_map, reg) if duty_station_map is not None else None
    except DutyStationMapValidationError as exc:
        raise _fail(f"Duty-station map invalid: {exc}") from exc
    # When no agency map is given, fall back to canon (which pairs with the
    # canonical registry); pass the resolved registry through either way.
    return assign_locpaths(records, duty_station_map=dmap, registry=reg if registry is not None else None)


def _plan_dict(plan: LocPathAssignmentPlan) -> dict:
    return {
        "map_id": plan.map_id,
        "registry_id": plan.registry_id,
        "assignments": [asdict(a) for a in plan.assignments],
        "findings": _finding_dicts(plan.findings),
    }


@locpath_app.command("assign")
def assign(
    hr_export: Path = typer.Argument(
        ...,
        help="HR-record export (JSON list, or an object wrapping a 'records'/'value' array).",
    ),
    registry: Path | None = _REGISTRY_OPT,
    duty_station_map: Path | None = _MAP_OPT,
    out: Path | None = typer.Option(
        None, "--out", "-o", help="Write the full assignment plan (assignments + findings) as JSON."
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Exit 1 if any assignment-drift finding is emitted (CI gate). Default exits 0."
    ),
) -> None:
    """Resolve an HR export to Primary-LocPath assignments (ADR-102 §D6 phase 2).

    Each HR record's locationCode is resolved through the governed
    duty-station map into a Primary LocPath + its governing Site, with
    provenance. Records that don't resolve (empty / unmapped /
    unregistered / inactive code, or duplicate employee) emit
    DRIFT-IDENTITY::location-assignment findings instead. Read-only —
    nothing is written to any system. Use --out to persist the plan.

    Examples::

        uiao locpath assign hr-records.json --out plan.json
        uiao locpath assign hr-records.json --registry agency.yaml --map agency-map.yaml --strict
    """
    plan = _build_plan(hr_export, registry, duty_station_map, "HR export")

    console.print(f"[bold]LocPath assignment[/bold] — map='{plan.map_id}', registry='{plan.registry_id}'")
    console.print(f"  Assignments : {len(plan.assignments)}")
    console.print(f"  Findings    : {len(plan.findings)}")
    unmapped = plan.unmapped_codes()
    if unmapped:
        console.print(f"  Unmapped codes : [yellow]{', '.join(unmapped)}[/yellow]")
    _print_findings(plan.findings)

    _write_out(out, _plan_dict(plan), "Assignment plan")

    if strict and plan.findings:
        raise typer.Exit(code=1)


@locpath_app.command("mover")
def mover(
    previous: Path = typer.Option(..., "--previous", "-p", help="Earlier HR export (recorded/last-snapshot state)."),
    current: Path = typer.Option(..., "--current", "-c", help="Later HR export (fresh derivation)."),
    registry: Path | None = _REGISTRY_OPT,
    duty_station_map: Path | None = _MAP_OPT,
    out: Path | None = typer.Option(None, "--out", "-o", help="Write the Mover plan (events + findings) as JSON."),
    strict: bool = typer.Option(False, "--strict", help="Exit 1 if any Mover event is detected (CI gate)."),
) -> None:
    """Diff two HR snapshots into Mover events + impact surfaces (phase 3).

    Both exports are run through the assignment pass, then diffed:
    identities that appeared (join), disappeared (leave), or changed
    Primary LocPath (move) produce a MoverEvent carrying the stale impact
    surfaces (e911 dispatchable location; dynamic-groups + admin-units on
    cross-site moves; telemetry/service/DIA boundary transitions) and one
    assignment-drift finding each. Read-only — phase 4 owns the writes.

    Example::

        uiao locpath mover --previous q1-hr.json --current q2-hr.json --out moves.json
    """
    prev_plan = _build_plan(previous, registry, duty_station_map, "previous HR export")
    cur_plan = _build_plan(current, registry, duty_station_map, "current HR export")
    reg = _load_registry(registry) if registry is not None else None
    move_plan = plan_location_moves(prev_plan, cur_plan, registry=reg)

    console.print(
        f"[bold]LocPath Mover[/bold] — {len(move_plan.events)} event(s): "
        f"joiners={len(move_plan.joiners())}, movers={len(move_plan.movers())}, leavers={len(move_plan.leavers())}"
    )
    if move_plan.events:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Employee")
        table.add_column("Kind")
        table.add_column("From")
        table.add_column("To")
        table.add_column("Site changed")
        table.add_column("Stale surfaces", overflow="fold")
        for event in move_plan.events:
            table.add_row(
                event.employee_id,
                event.kind,
                event.previous_loc_path or "—",
                event.new_loc_path or "—",
                "yes" if event.site_changed else "no",
                ", ".join(event.impacts),
            )
        console.print(table)

    _write_out(
        out,
        {
            "events": [asdict(e) for e in move_plan.events],
            "findings": _finding_dicts(move_plan.findings),
        },
        "Mover plan",
    )

    if strict and move_plan.events:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Phase 3 — site policy/boundary drift ; ADR-104 — E911 completeness
# ---------------------------------------------------------------------------


def _observed_state_from_dict(raw: dict) -> ObservedSiteState:
    dests = raw.get("telemetry_destinations") or raw.get("telemetryDestinations") or []
    return ObservedSiteState(
        loc_path=_get(raw, "loc_path", "locPath"),
        breakout_observed=raw.get("breakout_observed") or raw.get("breakoutObserved"),
        internet_egress_observed=raw.get("internet_egress_observed", raw.get("internetEgressObserved")),
        telemetry_destinations=tuple(str(d) for d in dests),
    )


@locpath_app.command("policy-drift")
def policy_drift(
    observed: Path = typer.Argument(
        ...,
        help="Observed-site-state export (JSON list of {loc_path, breakout_observed, internet_egress_observed, telemetry_destinations}).",
    ),
    registry: Path | None = _REGISTRY_OPT,
    out: Path | None = typer.Option(None, "--out", "-o", help="Write the findings as JSON."),
    strict: bool = typer.Option(False, "--strict", help="Exit 1 if any drift finding is emitted (CI gate)."),
) -> None:
    """Classify observed site state against governed classification (phase 3).

    Compares each observed site's network/telemetry behavior against the
    registry's governed ``network`` / ``boundaries`` blocks, emitting
    DRIFT-AUTHZ::location-policy (e.g. local breakout at a diaApproved:false
    site) and DRIFT-BOUNDARY::location-boundary (telemetry egress outside
    the declared boundary). What *produces* the observations (SD-WAN /
    M365 telemetry / boundary probes) is a collector concern outside this
    command. Read-only.

    Example::

        uiao locpath policy-drift observed-sites.json --out drift.json
    """
    states = [
        _observed_state_from_dict(row)
        for row in _rows(_load_json(observed, "observed-state export"), "observed-state export")
    ]
    reg = _load_registry(registry) if registry is not None else None
    findings = detect_location_policy_drift(states, registry=reg)

    console.print(f"[bold]LocPath policy drift[/bold] — {len(states)} observed site(s), {len(findings)} finding(s)")
    _print_findings(findings)
    _write_out(out, _finding_dicts(findings), "Policy-drift findings")

    if strict and findings:
        raise typer.Exit(code=1)


@locpath_app.command("e911-check")
def e911_check(
    registry: Path | None = _REGISTRY_OPT,
    out: Path | None = typer.Option(None, "--out", "-o", help="Write the completeness findings as JSON."),
    strict: bool = typer.Option(False, "--strict", help="Exit 1 if any completeness gap is found (CI gate)."),
) -> None:
    """Find governed locations with an incomplete dispatchable location (ADR-104).

    For every node flagged ``dispatchableLocationRequired: true`` this
    resolves the effective (own + inherited) E911 payload and emits
    DRIFT-SEMANTIC::e911-completeness findings when the § 9.16 floor is
    unmet (no civic address) or sub-address precision is missing at
    Building/Floor/Space. Governs the location of record only; never
    consults Dynamic Location Context, never sits in the call path. Read-only.

    Example::

        uiao locpath e911-check
        uiao locpath e911-check --registry agency-locations.yaml --strict
    """
    reg = _load_registry(registry) if registry is not None else None
    findings = detect_e911_completeness_gaps(registry=reg)

    console.print(f"[bold]E911 dispatchable-location completeness[/bold] — {len(findings)} gap(s)")
    counts = _print_findings(findings)
    if not findings:
        console.print("[green]PASS[/green] — every obligated location resolves a complete dispatchable location.")
    elif counts.get("P1"):
        console.print(f"[red]{counts['P1']} P1 gap(s)[/red] — no civic address resolvable (§ 9.16 floor unmet).")
    _write_out(out, _finding_dicts(findings), "E911 findings")

    if strict and findings:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Phase 4 — Entra exposure planning (plan-only, no Graph I/O)
# ---------------------------------------------------------------------------

_LOCATOR_OPT = typer.Option(
    None,
    "--locator",
    help="Storage-locator attribute path (e.g. a directory-extension name). Supplied = dynamic-rule mode; omitted = assigned-membership mode (ADR-102 §D5).",
)
_PREFIX_OPT = typer.Option(
    None,
    "--prefix",
    help="Restrict exposure to these LocPath prefixes (repeatable). Default: every governed Site with an assignment.",
)


@expose_app.command("groups")
def expose_groups(
    hr_export: Path = typer.Argument(..., help="HR-record export to run the assignment pass over."),
    registry: Path | None = _REGISTRY_OPT,
    duty_station_map: Path | None = _MAP_OPT,
    locator: str | None = _LOCATOR_OPT,
    prefix: list[str] | None = _PREFIX_OPT,
    out: Path | None = typer.Option(None, "--out", "-o", help="Write the group specs (with Graph bodies) as JSON."),
) -> None:
    """Plan one Entra security group per governed Site (ADR-102 §D6 phase 4).

    Runs the assignment pass over HR_EXPORT, then derives one
    ``LocPath-Site-<SEG>-Users`` group per Site that has an assignment.
    With --locator the groups carry an Entra dynamic-membership rule
    ``(<locator> -startsWith "/SITE/PATH")``; without it they use assigned
    membership sourced from the governed substrate (ADR-102 §D5 — LocPath
    claims no extensionAttribute slot). Planning is pure — no Graph I/O;
    transport/apply stays with the existing Entra adapters.

    Example::

        uiao locpath expose groups hr-records.json --out groups.json
        uiao locpath expose groups hr-records.json --locator extension_xxx_locPath
    """
    plan = _build_plan(hr_export, registry, duty_station_map, "HR export")
    reg = _load_registry(registry) if registry is not None else None
    try:
        specs = plan_locpath_site_groups(plan, registry=reg, locator=locator, prefixes=prefix or None)
    except LocPathExposureError as exc:
        raise _fail(f"Exposure planning failed: {exc}") from exc

    mode = "dynamic-rule" if locator else "assigned-membership"
    console.print(f"[bold]LocPath site groups[/bold] — {len(specs)} group(s), mode={mode}")
    for spec in specs:
        console.print(f"  [cyan]{spec.name}[/cyan] — {len(spec.member_employee_ids)} member(s) under {spec.loc_path}")
    _write_out(
        out,
        [
            {
                **asdict(spec),
                "graph_body": spec.to_graph_body() if spec.membership_rule is not None else None,
            }
            for spec in specs
        ],
        "Group specs",
    )


@expose_app.command("admin-units")
def expose_admin_units(
    hr_export: Path = typer.Argument(..., help="HR-record export to run the assignment pass over."),
    registry: Path | None = _REGISTRY_OPT,
    duty_station_map: Path | None = _MAP_OPT,
    locator: str | None = _LOCATOR_OPT,
    prefix: list[str] | None = _PREFIX_OPT,
    unrestricted: bool = typer.Option(
        False, "--unrestricted", help="Plan non-restricted-management AUs (default is restricted, per UIAO_154)."
    ),
    out: Path | None = typer.Option(None, "--out", "-o", help="Write the AU specs (with Graph bodies) as JSON."),
) -> None:
    """Plan one Entra Administrative Unit per governed Site (phase 4).

    Same scoping and membership modes as ``expose groups``; AUs default to
    restricted management per UIAO_154 doctrine (``--unrestricted`` opts
    out). Plan-only — members are added per-AU after creation by the Entra
    adapter; no Graph I/O here.

    Example::

        uiao locpath expose admin-units hr-records.json --out aus.json
    """
    plan = _build_plan(hr_export, registry, duty_station_map, "HR export")
    reg = _load_registry(registry) if registry is not None else None
    try:
        specs = plan_locpath_admin_units(
            plan,
            registry=reg,
            locator=locator,
            prefixes=prefix or None,
            restricted_management=not unrestricted,
        )
    except LocPathExposureError as exc:
        raise _fail(f"Exposure planning failed: {exc}") from exc

    mode = "dynamic-rule" if locator else "assigned-membership"
    console.print(
        f"[bold]LocPath Administrative Units[/bold] — {len(specs)} AU(s), mode={mode}, "
        f"restricted={'no' if unrestricted else 'yes'}"
    )
    for spec in specs:
        console.print(f"  [cyan]{spec.name}[/cyan] — {len(spec.member_employee_ids)} member(s) under {spec.loc_path}")
    _write_out(
        out,
        [{**asdict(spec), "graph_body": spec.to_graph_body()} for spec in specs],
        "AU specs",
    )
